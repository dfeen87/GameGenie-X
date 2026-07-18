"""Deterministic, multi-field, multi-patch engine with conditional logic."""

from __future__ import annotations

import enum
import json
from collections.abc import Callable  # noqa: TC003
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from gamegenie_x.models import Patch as LegacyPatch
from gamegenie_x.models import PatchType

if TYPE_CHECKING:
    from gamegenie_x.game_profiles import GameProfile
    from gamegenie_x.profiles import PlatformProfile


class TargetType(enum.Enum):
    """Target types for patch application."""

    SAVE = "SAVE"
    CONFIG = "CONFIG"
    MEMORY = "MEMORY"


@dataclass(frozen=True, slots=True)
class Patch:
    """An upgraded patch representation supporting conditional logic."""

    target_type: TargetType
    new_value: Any
    offset: int | None = None
    key_path: str | None = None
    compare_value: Any = None
    conditions: list[Callable[[Any], bool]] = field(default_factory=list)
    patch_type: PatchType = PatchType.REPLACE


@dataclass(frozen=True, slots=True)
class PatchSequence:
    """An ordered list of Patch objects applied deterministically in sequence."""

    patches: list[Patch] = field(default_factory=list)

    def apply(
        self,
        filepath: str | Path,
        profile: PlatformProfile,
        game_profile: GameProfile | None = None,
        safe_mode: bool = True,
    ) -> bool:
        """Applies the sequence of patches to the target file.

        Returns:
            True if at least one patch was applied successfully.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Target file not found: {path}")

        # Safety validation before any writes
        if game_profile is not None:
            with open(path, "rb") as f:
                save_bytes = f.read()
            from gamegenie_x.safety import SafetyRulesEngine
            engine = SafetyRulesEngine()
            for patch in self.patches:
                engine.validate_patch(patch, game_profile, save_bytes, safe_mode=safe_mode)

        strategy = "binary"
        if profile.io_strategy:
            strategy = profile.io_strategy.strategy

        if strategy == "binary" or strategy == "container":
            return self._apply_binary(path, profile)
        elif strategy == "json":
            return self._apply_json(path, profile)
        else:
            raise ValueError(f"Unknown IO strategy: {strategy}")

    def _apply_binary(self, path: Path, profile: PlatformProfile) -> bool:
        """Applies binary patches sequentially on an in-memory bytearray."""
        with open(path, "rb") as f:
            data = bytearray(f.read())

        modified = False
        for patch in self.patches:
            if patch.target_type != TargetType.SAVE:
                continue

            offset = patch.offset
            if offset is None:
                continue

            if offset >= len(data):
                raise ValueError(
                    f"Patch offset 0x{offset:X} is out of bounds for file of size {len(data)}"
                )

            current_value = data[offset]

            # 1. Evaluate conditions
            if patch.conditions and not all(cond(current_value) for cond in patch.conditions):
                continue

            # 2. Compare value
            if patch.compare_value is not None and current_value != patch.compare_value:
                continue

            # Calculate new value
            new_val = _calculate_new_value_v2(current_value, patch)

            if current_value != new_val:
                data[offset] = new_val
                modified = True

        if modified:
            with open(path, "wb") as f:
                f.write(data)

        return modified

    def _apply_json(self, path: Path, profile: PlatformProfile) -> bool:
        """Applies json patches sequentially on a mutable parsed dictionary."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        modified = False
        for patch in self.patches:
            if patch.target_type != TargetType.CONFIG:
                continue

            key_path = patch.key_path
            if key_path is None:
                # Fallback to offset if key_path not set
                if patch.offset is not None:
                    key_path = str(patch.offset)
                    if profile.fields:
                        for k, v in profile.fields.items():
                            if v.offset == patch.offset:
                                key_path = k
                                break
                else:
                    continue

            # Traversal
            keys = key_path.split(".")
            target = data
            for key in keys[:-1]:
                if key not in target:
                    target[key] = {}
                target = target[key]

            final_key = keys[-1]
            current_value = target.get(final_key, 0)
            if (
                not isinstance(current_value, (int, float, bool, str))
                and current_value is not None
            ):
                raise ValueError(f"Cannot patch complex JSON value at {key_path}")

            # 1. Evaluate conditions
            if patch.conditions and not all(cond(current_value) for cond in patch.conditions):
                continue

            # 2. Compare value
            if patch.compare_value is not None and current_value != patch.compare_value:
                continue

            # Calculate new value (handle both numeric and non-numeric)
            if isinstance(current_value, int) and isinstance(patch.new_value, int):
                new_val = _calculate_new_value_v2(current_value, patch)
            else:
                new_val = patch.new_value

            if current_value != new_val:
                target[final_key] = new_val
                modified = True

        if modified:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        return modified


def _calculate_new_value_v2(current_value: int, patch: Patch) -> int:
    """Helper to calculate new value based on patch type."""
    patch_val = patch.new_value
    # Ensure patch_val is int for bitwise/numeric ops
    if not isinstance(patch_val, int):
        raise ValueError("Binary/Numeric patch requires an integer value.")

    if patch.patch_type == PatchType.REPLACE:
        return patch_val
    elif patch.patch_type == PatchType.INCREMENT:
        return (current_value + patch_val) & 0xFF
    elif patch.patch_type == PatchType.DECREMENT:
        return (current_value - patch_val) & 0xFF
    elif patch.patch_type == PatchType.BITSET:
        return current_value | patch_val
    elif patch.patch_type == PatchType.BITCLEAR:
        return current_value & (~patch_val & 0xFF)
    elif patch.patch_type == PatchType.XOR:
        return current_value ^ patch_val
    else:
        raise ValueError(f"Unsupported patch type: {patch.patch_type}")


def from_legacy_patch(legacy: LegacyPatch, profile: PlatformProfile) -> PatchSequence:
    """Converts a legacy Patch object to a new PatchSequence."""
    strategy = "binary"
    if profile.io_strategy:
        strategy = profile.io_strategy.strategy

    if strategy == "json":
        target_type = TargetType.CONFIG
    elif strategy == "container":
        target_type = TargetType.SAVE
    else:
        target_type = TargetType.SAVE

    offset: int | None = None
    key_path: str | None = None

    if strategy == "json":
        field_path = str(legacy.address)
        if profile.fields:
            for k, v in profile.fields.items():
                if v.offset == legacy.address:
                    field_path = k
        key_path = field_path
    else:
        offset = legacy.address

    compare_val = None
    if legacy.flags.compare_enabled or (profile.compare_supported and legacy.compare > 0):
        compare_val = legacy.compare

    if legacy.flags.wide_data:
        # A small sequence of related patches (chained, 16-bit)
        endianness = getattr(profile, "endianness", "little")
        val_low = legacy.value & 0xFF
        val_high = (legacy.value >> 8) & 0xFF

        if endianness == "big":
            p1_val = val_high
            p2_val = val_low
        else:
            p1_val = val_low
            p2_val = val_high

        p1 = Patch(
            target_type=target_type,
            offset=offset,
            key_path=key_path,
            new_value=p1_val,
            compare_value=compare_val,
            patch_type=legacy.patch_type,
        )

        p2_offset = offset + 1 if offset is not None else None
        p2_key_path = None
        if key_path is not None:
            p2_key_path = key_path + "_high"

        # High byte usually doesn't have same compare_value or it is 0
        p2 = Patch(
            target_type=target_type,
            offset=p2_offset,
            key_path=p2_key_path,
            new_value=p2_val,
            compare_value=0 if compare_val is not None else None,
            patch_type=legacy.patch_type,
        )
        return PatchSequence([p1, p2])
    else:
        p1 = Patch(
            target_type=target_type,
            offset=offset,
            key_path=key_path,
            new_value=legacy.value,
            compare_value=compare_val,
            patch_type=legacy.patch_type,
        )
        return PatchSequence([p1])
