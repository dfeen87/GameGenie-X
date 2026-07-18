"""Apply GameGenie-X patches to physical files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from gamegenie_x.models import Patch, PatchType

if TYPE_CHECKING:
    from gamegenie_x.game_profiles import GameProfile
    from gamegenie_x.profiles import PlatformProfile


def apply_patch_to_file(
    patch: Patch,
    filepath: str | Path,
    profile: PlatformProfile,
    game_profile: GameProfile | None = None,
    safe_mode: bool = True,
) -> bool:
    """Applies a decoded GameGenie-X patch to a target file.

    Handles different IO strategies (binary, json, container) based on the profile.
    Returns True if the patch was applied (i.e., changed the file or condition met).
    Returns False if compare failed or file would remain unchanged.

    Args:
        patch: The decoded GameGenie-X code.
        filepath: Path to the target save file or metadata block.
        profile: The platform profile defining IO strategy and constraints.
        game_profile: Optional GameProfile for safety rules enforcement.
        safe_mode: If True, rejects unsafe patches and raises UnsafePatchError.

    Returns:
        bool indicating if the file was modified.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format or strategy is unsupported or malformed.
        UnsafePatchError: If safety validation fails and safe_mode is True.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Target file not found: {path}")

    # Safety rules check
    if game_profile is not None:
        with open(path, "rb") as f:
            save_bytes = f.read()
        from gamegenie_x.safety import SafetyRulesEngine
        SafetyRulesEngine().validate_patch(patch, game_profile, save_bytes, safe_mode=safe_mode)

    strategy = "binary"
    if profile.io_strategy:
        strategy = profile.io_strategy.strategy

    if strategy == "binary":
        return _apply_binary(patch, path, profile)
    elif strategy == "json":
        return _apply_json(patch, path, profile)
    elif strategy == "container":
        return _apply_binary(patch, path, profile)
    else:
        raise ValueError(f"Unknown IO strategy: {strategy}")


def _calculate_new_value(current_value: int, patch: Patch) -> int:
    """Helper to calculate new value based on patch type."""
    patch_val = patch.value
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


def _apply_binary(patch: Patch, path: Path, profile: PlatformProfile) -> bool:
    """Applies patch to a raw binary file."""
    with open(path, "rb") as f:
        data = bytearray(f.read())

    offset = patch.address
    if offset >= len(data):
        raise ValueError(
            f"Patch offset 0x{offset:X} is out of bounds for file of size {len(data)}"
        )

    current_value = data[offset]

    if (patch.flags.compare_enabled or (profile.compare_supported and patch.compare > 0)) and (
        current_value != patch.compare
    ):
        return False

    new_value = _calculate_new_value(current_value, patch)

    if current_value == new_value:
        return False

    data[offset] = new_value

    with open(path, "wb") as f:
        f.write(data)

    return True


def _apply_json(patch: Patch, path: Path, profile: PlatformProfile) -> bool:
    """Applies patch to a JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    field_path = str(patch.address)
    if profile.fields:
        for k, v in profile.fields.items():
            if v.offset == patch.address:
                field_path = k
                break

    keys = field_path.split(".")
    target = data
    for key in keys[:-1]:
        if key not in target:
            target[key] = {}
        target = target[key]

    final_key = keys[-1]

    current_value = target.get(final_key, 0)
    if not isinstance(current_value, int):
        # We can only patch integers or booleans mapped to integers
        raise ValueError(f"Cannot patch non-integer JSON value at {field_path}")

    if (patch.flags.compare_enabled or (profile.compare_supported and patch.compare > 0)) and (
        current_value != patch.compare
    ):
        return False

    new_value = _calculate_new_value(current_value, patch)

    if current_value == new_value:
        return False

    target[final_key] = new_value

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return True
