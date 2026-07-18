"""Module C: Developer Experience v2 - Sandbox Emulator."""

from __future__ import annotations

import copy
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gamegenie_x.game_profiles import GameProfile

from gamegenie_x.patch_v2 import PatchSequence, _calculate_new_value_v2
from gamegenie_x.safety import SafetyRulesEngine


class SandboxEmulator:
    """Simulates a game save environment in-memory for patch testing."""

    def __init__(self) -> None:
        self.profile: GameProfile | None = None
        self.state: Any = None  # dict[str, Any] for json, bytearray for binary

    def load_virtual_save(self, profile: GameProfile) -> None:
        """Loads a virtual save structure with deterministic defaults from the game profile."""
        self.profile = profile
        if profile.format == "json":
            self.state = self._build_synthetic_json(profile.save_structure, profile)
        else:
            max_offset = self._get_max_offset(profile.save_structure)
            min_size = profile.file_size_range[0] if profile.file_size_range else 256
            size = max(min_size, max_offset + 1)
            self.state = bytearray(size)
            self._populate_binary_defaults(profile.save_structure, profile, self.state)

    def apply_patch_sequence(self, patch_sequence: PatchSequence, safe_mode: bool = True) -> bool:
        """Applies a PatchSequence to the in-memory save, running safety rules first.

        Args:
            patch_sequence: The PatchSequence to apply.
            safe_mode: If True, raises UnsafePatchError on safety violations.

        Returns:
            True if any patch modified the state.
        """
        if self.profile is None:
            raise ValueError("No game profile loaded in SandboxEmulator.")

        safety_engine = SafetyRulesEngine()

        # Serialize current state for safety validation
        if self.profile.format == "json":
            save_bytes = json.dumps(self.state).encode("utf-8")
        else:
            save_bytes = bytes(self.state)

        # Validate all patches BEFORE applying any (transactional safety)
        for patch in patch_sequence.patches:
            safety_engine.validate_patch(patch, self.profile, save_bytes, safe_mode=safe_mode)

        modified = False
        if self.profile.format == "json":
            for patch in patch_sequence.patches:
                key_path = patch.key_path
                if key_path is None and patch.offset is not None:
                    key_path = safety_engine._find_field_by_offset(
                        self.profile.save_structure, patch.offset
                    )
                    if key_path is None:
                        key_path = str(patch.offset)

                if key_path is None:
                    continue

                # Traversal
                keys = key_path.split(".")
                target = self.state
                for key in keys[:-1]:
                    if key not in target:
                        target[key] = {}
                    target = target[key]

                final_key = keys[-1] if keys else ""
                if not final_key:
                    continue

                current_value = target.get(final_key, 0)

                # 1. Evaluate conditions
                if patch.conditions and not all(cond(current_value) for cond in patch.conditions):
                    continue

                # 2. Compare value
                if patch.compare_value is not None and current_value != patch.compare_value:
                    continue

                # Calculate new value
                is_int = isinstance(current_value, int) and isinstance(patch.new_value, int)
                is_bool = isinstance(current_value, bool)
                if is_int and not is_bool:
                    new_val = _calculate_new_value_v2(current_value, patch)
                else:
                    new_val = patch.new_value

                if current_value != new_val:
                    target[final_key] = new_val
                    modified = True
        else:
            # Binary format
            for patch in patch_sequence.patches:
                offset = patch.offset
                if offset is None:
                    continue

                if offset >= len(self.state):
                    msg = (
                        f"Patch offset 0x{offset:X} is out of bounds "
                        f"for virtual save of size {len(self.state)}"
                    )
                    raise ValueError(msg)

                current_value = self.state[offset]

                # 1. Evaluate conditions
                if patch.conditions and not all(cond(current_value) for cond in patch.conditions):
                    continue

                # 2. Compare value
                if patch.compare_value is not None and current_value != patch.compare_value:
                    continue

                if isinstance(current_value, int) and isinstance(patch.new_value, int):
                    new_val = _calculate_new_value_v2(current_value, patch)
                else:
                    new_val = patch.new_value

                if current_value != new_val:
                    self.state[offset] = new_val
                    modified = True

        return modified

    def dump_state(self) -> Any:
        """Returns the current virtual save state (copied dict for JSON, bytes for binary)."""
        if self.state is None:
            return None
        if self.profile is not None and self.profile.format == "json":
            return copy.deepcopy(self.state)
        return bytes(self.state)

    def _get_max_offset(self, struct: dict[str, Any]) -> int:
        max_val = 0
        for v in struct.values():
            if isinstance(v, dict):
                max_val = max(max_val, self._get_max_offset(v))
            elif isinstance(v, int):
                max_val = max(max_val, v)
        return max_val

    def _build_synthetic_json(
        self, struct: dict[str, Any], profile: GameProfile, path: str = ""
    ) -> dict[str, Any]:
        res = {}
        for k, v in struct.items():
            next_path = f"{path}.{k}" if path else k
            if isinstance(v, dict):
                res[k] = self._build_synthetic_json(v, profile, next_path)
            else:
                default_val: Any = 0
                is_flag_bool = (
                    next_path in profile.flags
                    and isinstance(profile.flags[next_path], bool)
                )
                is_flag_active = (
                    next_path.endswith(".is_active") or next_path.endswith(".enabled")
                )
                if is_flag_bool or is_flag_active:
                    default_val = False

                val_range = profile.value_ranges.get(next_path)
                if val_range is None:
                    parts = next_path.split(".")
                    if parts and parts[-1] in profile.value_ranges:
                        val_range = profile.value_ranges[parts[-1]]

                if val_range is not None:
                    default_val = val_range[0]

                res[k] = default_val
        return res

    def _populate_binary_defaults(
        self, struct: dict[str, Any], profile: GameProfile, state: bytearray, path: str = ""
    ) -> None:
        for k, v in struct.items():
            next_path = f"{path}.{k}" if path else k
            if isinstance(v, dict):
                self._populate_binary_defaults(v, profile, state, next_path)
            else:
                offset = v
                default_val = 0
                is_flag_bool = (
                    next_path in profile.flags
                    and isinstance(profile.flags[next_path], bool)
                )
                is_flag_active = (
                    next_path.endswith(".is_active") or next_path.endswith(".enabled")
                )
                if is_flag_bool or is_flag_active:
                    default_val = 0

                val_range = profile.value_ranges.get(next_path)
                if val_range is None:
                    parts = next_path.split(".")
                    if parts and parts[-1] in profile.value_ranges:
                        val_range = profile.value_ranges[parts[-1]]

                if val_range is not None:
                    default_val = val_range[0]

                if default_val > 0xFFFF:
                    for i in range(4):
                        if offset + i < len(state):
                            state[offset + i] = (default_val >> (8 * i)) & 0xFF
                elif default_val > 0xFF:
                    for i in range(2):
                        if offset + i < len(state):
                            state[offset + i] = (default_val >> (8 * i)) & 0xFF
                else:
                    if offset < len(state):
                        state[offset] = default_val & 0xFF
