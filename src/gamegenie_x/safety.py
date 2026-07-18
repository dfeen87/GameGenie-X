"""Module B: Profile System v2 - Profile Safety Rules Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from gamegenie_x.models import Patch as LegacyPatch
from gamegenie_x.patch_v2 import Patch as ModernPatch

if TYPE_CHECKING:
    from gamegenie_x.game_profiles import GameProfile


class UnsafePatchError(ValueError):
    """Raised when a patch is determined to be unsafe and safe mode is enabled."""


@dataclass(frozen=True, slots=True)
class SafetyResult:
    """The result of a patch safety validation."""

    is_safe: bool
    errors: list[str] = field(default_factory=list)


class SafetyRulesEngine:
    """Enforces safety rules on patches before they are applied to save files."""

    def validate_patch(
        self,
        patch: LegacyPatch | ModernPatch,
        profile: GameProfile,
        save_bytes: bytes,
        safe_mode: bool = True,
    ) -> SafetyResult:
        """Validates a patch against a game profile and save file.

        Args:
            patch: The Patch object (legacy or modern) to validate.
            profile: The GameProfile to validate against.
            save_bytes: The raw content of the save file.
            safe_mode: If True, raises UnsafePatchError on any violation.

        Returns:
            A SafetyResult indicating safety status and any error messages.

        Raises:
            UnsafePatchError: If safe_mode is True and any validation rule is violated.
        """
        errors: list[str] = []

        # 1. Extract common attributes depending on patch type (legacy vs modern)
        offset: int | None = None
        key_path: str | None = None
        value: Any = None

        if isinstance(patch, LegacyPatch):
            offset = patch.address
            value = patch.value
        elif isinstance(patch, ModernPatch):
            offset = patch.offset
            key_path = patch.key_path
            value = patch.new_value
        else:
            errors.append(f"Unknown patch type: {type(patch)}")
            if safe_mode:
                raise UnsafePatchError(errors[-1])
            return SafetyResult(is_safe=False, errors=errors)

        # 2. Determine the field path (dot-separated string, e.g., "player.stats.hp")
        field_path = key_path
        if field_path is None and offset is not None:
            field_path = self._find_field_by_offset(profile.save_structure, offset)

        # 3. Structural Integrity Checks
        is_json = profile.format == "json"
        if not is_json and offset is not None:
            # Binary structural check
            if offset < 0 or offset >= len(save_bytes):
                errors.append(
                    f"Structural integrity violation: Patch offset 0x{offset:X} is out of "
                    f"bounds for binary save of size {len(save_bytes)}."
                )
            # Check for wide data if specified or if the value exceeds 8-bit
            is_wide = False
            if isinstance(patch, LegacyPatch) and patch.flags.wide_data:
                is_wide = True
            if is_wide and (offset + 1 < 0 or offset + 1 >= len(save_bytes)):
                errors.append(
                    f"Structural integrity violation: Patch high-byte offset 0x{offset+1:X} "
                    f"is out of bounds for binary save of size {len(save_bytes)}."
                )

        # 4. Check for forbidden/unsafe fields
        if field_path is not None and self._is_field_forbidden(field_path, profile):
            errors.append(
                f"Forbidden field access: Modifying '{field_path}' is blocked for safety "
                f"(anti-cheat/unsafe flag)."
            )

        # 5. Field Type Correctness
        if (
            field_path is not None
            and self._is_boolean_field(field_path, profile)
            and not isinstance(value, bool)
        ):
            errors.append(
                f"Field type mismatch: Field '{field_path}' is expected to be a boolean, "
                f"but received {type(value).__name__} ({value})."
            )

        # 6. Value Range Enforcement
        if field_path is not None and value is not None:
            val_range = self._get_value_range(field_path, profile)
            if val_range is not None:
                min_val, max_val = val_range
                # Make sure we only validate numeric ranges if value is numeric or comparable
                if (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and (value < min_val or value > max_val)
                ):
                    errors.append(
                        f"Value range violation: Attempted to set '{field_path}' to {value}, "
                        f"which is outside the allowed range [{min_val}, {max_val}]."
                    )

        # 7. Final Safety Result and Action
        is_safe = len(errors) == 0
        if not is_safe and safe_mode:
            raise UnsafePatchError("; ".join(errors))

        return SafetyResult(is_safe=is_safe, errors=errors)

    def _find_field_by_offset(
        self, structure: Any, offset: int, current_path: str = ""
    ) -> str | None:
        """Recursively searches the save_structure for the given offset to return its path."""
        if isinstance(structure, dict):
            for k, v in structure.items():
                next_path = f"{current_path}.{k}" if current_path else k
                if isinstance(v, int) and v == offset:
                    return next_path
                elif isinstance(v, dict):
                    res = self._find_field_by_offset(v, offset, next_path)
                    if res is not None:
                        return res
        return None

    def _is_field_forbidden(self, field_path: str, profile: GameProfile) -> bool:
        """Determines if a field path is forbidden/unsafe."""
        lowered_path = field_path.lower()
        if "anti_cheat" in lowered_path or "anticheat" in lowered_path or "unsafe" in lowered_path:
            return True

        forbidden_keys = [
            f"{field_path}.unsafe",
            f"{field_path}_unsafe",
            f"{field_path}.forbidden",
            f"{field_path}_forbidden",
        ]
        for key in forbidden_keys:
            if profile.flags.get(key) is True:
                return True

        return (
            profile.flags.get(f"{field_path}.safe") is False
            or profile.flags.get(f"{field_path}_safe") is False
        )

    def _is_boolean_field(self, field_path: str, profile: GameProfile) -> bool:
        """Determines if a field path is mapped to a boolean field."""
        return (
            profile.flags.get(field_path) is True
            or field_path.endswith(".is_active")
            or field_path.endswith(".enabled")
        )

    def _get_value_range(self, field_path: str, profile: GameProfile) -> tuple[int, int] | None:
        """Finds the value range for a given field path, supporting exact and suffix matches."""
        if field_path in profile.value_ranges:
            return profile.value_ranges[field_path]

        parts = field_path.split(".")
        if len(parts) > 1:
            last_part = parts[-1]
            if last_part in profile.value_ranges:
                return profile.value_ranges[last_part]

        return None
