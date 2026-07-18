"""Module B: Profile System v2 - Profile Auto-Discovery."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gamegenie_x.game_profiles import GameProfile, load_game_profile


@dataclass(frozen=True, slots=True)
class DetectionDiagnostic:
    """Diagnostic details explaining why auto-discovery failed for each candidate profile."""

    failures: dict[str, str] = field(default_factory=dict)


class ProfileDetector:
    """Automatically detects the correct GameProfile for a given save file."""

    def __init__(
        self,
        profiles: list[GameProfile] | None = None,
        profiles_dir: str | Path | None = "profiles",
    ) -> None:
        """Initializes the ProfileDetector with loaded profiles or a directory of profiles.

        Args:
            profiles: An optional explicit list of GameProfile objects.
            profiles_dir: An optional path to a directory of JSON profiles to load automatically.
        """
        self.profiles: list[GameProfile] = []
        self.last_diagnostic: DetectionDiagnostic | None = None

        if profiles is not None:
            self.profiles.extend(profiles)
        elif profiles_dir is not None:
            dir_path = Path(profiles_dir)
            if dir_path.exists() and dir_path.is_dir():
                for file_path in dir_path.glob("*.json"):
                    if file_path.stat().st_size == 0:
                        continue
                    try:
                        profile = load_game_profile(file_path)
                        self.profiles.append(profile)
                    except Exception:
                        pass

    def detect(self, save_bytes: bytes) -> GameProfile | None:
        """Detects the correct GameProfile for the given save file.

        Args:
            save_bytes: The raw content of the save file.

        Returns:
            The detected GameProfile, or None if detection failed.
        """
        self.last_diagnostic = None
        failures: dict[str, str] = {}

        if not self.profiles:
            self.last_diagnostic = DetectionDiagnostic({"all": "No profiles loaded in detector."})
            return None

        # 1. First-pass: Check signature matching
        sig_matches: list[GameProfile] = []
        for profile in self.profiles:
            sig = (
                profile.signature
                if isinstance(profile.signature, bytes)
                else bytes(profile.signature)
            )
            if not sig:
                failures[profile.game_id] = "No signature defined."
                continue

            if len(save_bytes) < len(sig):
                failures[profile.game_id] = (
                    f"Save file too small ({len(save_bytes)} bytes) for signature "
                    f"({len(sig)} bytes)."
                )
                continue

            if save_bytes[: len(sig)] == sig:
                sig_matches.append(profile)
            else:
                failures[profile.game_id] = "Signature prefix mismatch."

        # Case A: Exactly one signature match
        if len(sig_matches) == 1:
            return sig_matches[0]

        # Case B: Multiple signature matches -> Disambiguate using fallback heuristics
        if len(sig_matches) > 1:
            heuristic_matches: list[tuple[GameProfile, int]] = []
            for profile in sig_matches:
                score = self._compute_heuristics_score(profile, save_bytes)
                if score > 0:
                    heuristic_matches.append((profile, score))

            if len(heuristic_matches) == 1:
                return heuristic_matches[0][0]
            elif len(heuristic_matches) > 1:
                heuristic_matches.sort(key=lambda x: x[1], reverse=True)
                if heuristic_matches[0][1] > heuristic_matches[1][1]:
                    return heuristic_matches[0][0]
                else:
                    self.last_diagnostic = DetectionDiagnostic(
                        {
                            p.game_id: "Ambiguous match with multiple signature-matching profiles."
                            for p, _ in heuristic_matches
                        }
                    )
                    return None
            else:
                self.last_diagnostic = DetectionDiagnostic(
                    {
                        p.game_id: "Multiple signature matches but all failed heuristics."
                        for p in sig_matches
                    }
                )
                return None

        # Case C: No signature match -> Try fallback heuristics on all profiles
        fallback_matches: list[tuple[GameProfile, int]] = []
        for profile in self.profiles:
            score = self._compute_heuristics_score(profile, save_bytes)
            if score >= 2:  # confidence threshold
                fallback_matches.append((profile, score))
            else:
                if profile.game_id not in failures:
                    failures[profile.game_id] = "Failed fallback heuristics (score too low)."

        if len(fallback_matches) == 1:
            return fallback_matches[0][0]
        elif len(fallback_matches) > 1:
            fallback_matches.sort(key=lambda x: x[1], reverse=True)
            if fallback_matches[0][1] > fallback_matches[1][1]:
                return fallback_matches[0][0]
            else:
                self.last_diagnostic = DetectionDiagnostic(
                    {
                        p.game_id: (
                            f"Ambiguous fallback matches (scores: "
                            f"{[m[1] for m in fallback_matches]})."
                        )
                        for p, _ in fallback_matches
                    }
                )
                return None

        self.last_diagnostic = DetectionDiagnostic(failures)
        return None

    def _compute_heuristics_score(self, profile: GameProfile, save_bytes: bytes) -> int:
        """Computes a heuristic score for how well the save file fits the given profile."""
        score = 0

        # Heuristic 1: File size range
        if profile.file_size_range is not None:
            min_size, max_size = profile.file_size_range
            if min_size <= len(save_bytes) <= max_size:
                score += 3
            else:
                return 0

        # Heuristic 2: Magic number
        if profile.magic_number is not None:
            magic = profile.magic_number
            if len(save_bytes) >= len(magic) and save_bytes[: len(magic)] == magic:
                score += 4
            else:
                return 0

        # Heuristic 3: Structural hint (JSON vs Binary)
        is_json = False
        parsed_json: Any = None
        # Reasonable size limit to avoid hanging on large files
        if (
            (save_bytes.strip().startswith(b"{") or save_bytes.strip().startswith(b"["))
            and len(save_bytes) < 10 * 1024 * 1024
        ):
            try:
                parsed_json = json.loads(save_bytes.decode("utf-8"))
                is_json = True
            except Exception:
                pass

        if profile.format == "json":
            if is_json:
                score += 2
            else:
                return 0
        elif profile.format == "binary" and is_json:
            return 0

        # Heuristic 4: Scan known field offsets and value ranges
        if profile.value_ranges and profile.save_structure:
            matched_fields = 0
            total_checked = 0

            for field_path, val_range in profile.value_ranges.items():
                offset = profile.get_offset(field_path)
                if offset is None:
                    continue

                total_checked += 1

                if not is_json:
                    if 0 <= offset < len(save_bytes):
                        val = save_bytes[offset]
                        if val_range[0] <= val <= val_range[1]:
                            matched_fields += 1
                else:
                    keys = field_path.split(".")
                    curr: Any = parsed_json
                    found = True
                    for k in keys:
                        if isinstance(curr, dict) and k in curr:
                            curr = curr[k]
                        else:
                            found = False
                            break
                    if (
                        found
                        and isinstance(curr, (int, float))
                        and (val_range[0] <= curr <= val_range[1])
                    ):
                        matched_fields += 1

            if total_checked > 0:
                match_ratio = matched_fields / total_checked
                if match_ratio == 1.0:
                    score += 5
                elif match_ratio >= 0.5:
                    score += 2
                else:
                    return 0

        return score
