"""Module C: Developer Experience v2 - Patch Preview Mode."""

from __future__ import annotations

import contextlib
import copy
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gamegenie_x.game_profiles import GameProfile
    from gamegenie_x.profiles import PlatformProfile

from gamegenie_x.patch_v2 import PatchSequence, _calculate_new_value_v2
from gamegenie_x.safety import SafetyRulesEngine


@dataclass(frozen=True, slots=True)
class PreviewResult:
    """The detailed result of a single patch preview."""

    field_name: str | None
    offset_or_key_path: str
    old_value: Any
    new_value: Any
    compare_matched: bool | None
    safety_passed: bool
    safety_errors: list[str]
    applied: bool


class PreviewEngine:
    """Provides a safe, non-destructive simulation of applying patches."""

    def preview(
        self,
        patch_sequence: PatchSequence,
        save_bytes: bytes,
        profile: GameProfile | PlatformProfile | None = None,
    ) -> list[PreviewResult]:
        """Previews a sequence of patches against a save file without modifying it.

        Args:
            patch_sequence: The PatchSequence to preview.
            save_bytes: The raw content of the save file.
            profile: The GameProfile or PlatformProfile to validate against and resolve names.

        Returns:
            A list of PreviewResult objects for each patch in the sequence.
        """
        is_json = False
        game_profile: GameProfile | None = None
        platform_profile: PlatformProfile | None = None

        # Determine type of profile using local importing or late imports
        from gamegenie_x.game_profiles import GameProfile as GameProfileSchema
        from gamegenie_x.profiles import PlatformProfile as PlatformProfileSchema

        if isinstance(profile, GameProfileSchema):
            game_profile = profile
            is_json = profile.format == "json"
        elif isinstance(profile, PlatformProfileSchema):
            platform_profile = profile
            is_json = (
                profile.io_strategy is not None
                and profile.io_strategy.strategy == "json"
            )

        # Set up current state to mutate during sequential preview
        if is_json:
            try:
                current_state = json.loads(save_bytes.decode("utf-8"))
            except Exception:
                current_state = {}
        else:
            current_state = bytearray(save_bytes)

        results: list[PreviewResult] = []
        safety_engine = SafetyRulesEngine()

        for patch in patch_sequence.patches:
            field_name: str | None = None
            offset_or_key_path: str = ""
            old_val: Any = None
            new_val: Any = None
            compare_matched: bool | None = None
            conditions_passed = True
            safety_passed = True
            safety_errors: list[str] = []

            # 1. Resolve field_name and offset_or_key_path
            if patch.key_path is not None:
                offset_or_key_path = patch.key_path
                field_name = patch.key_path
            elif patch.offset is not None:
                offset_or_key_path = f"0x{patch.offset:X}"
                if game_profile is not None:
                    field_name = safety_engine._find_field_by_offset(
                        game_profile.save_structure, patch.offset
                    )
                elif platform_profile is not None and platform_profile.fields:
                    for k, v in platform_profile.fields.items():
                        if v.offset == patch.offset:
                            field_name = k
                            break

            # 2. Get old value and compute target new value
            if is_json:
                key_path = patch.key_path
                if key_path is None and patch.offset is not None:
                    key_path = str(patch.offset)
                    if platform_profile and platform_profile.fields:
                        for k, v in platform_profile.fields.items():
                            if v.offset == patch.offset:
                                key_path = k
                                break

                if key_path is not None:
                    keys = key_path.split(".")
                    target = current_state
                    for key in keys[:-1]:
                        if isinstance(target, dict) and key in target:
                            target = target[key]
                        else:
                            break

                    final_key = keys[-1] if keys else ""
                    if isinstance(target, dict) and final_key in target:
                        old_val = target[final_key]
                    else:
                        old_val = None

                    # Check compare value
                    if patch.compare_value is not None:
                        compare_matched = old_val == patch.compare_value

                    # Check conditions
                    if patch.conditions:
                        conditions_passed = all(cond(old_val) for cond in patch.conditions)

                    # Compute new value
                    if old_val is not None:
                        is_int = isinstance(old_val, int) and isinstance(patch.new_value, int)
                        is_bool = isinstance(old_val, bool)
                        if is_int and not is_bool:
                            try:
                                new_val = _calculate_new_value_v2(old_val, patch)
                            except Exception:
                                new_val = patch.new_value
                        else:
                            new_val = patch.new_value
                    else:
                        new_val = patch.new_value

                    # Update mutable state if patch is applied
                    applied = conditions_passed and (
                        compare_matched is None or compare_matched
                    )
                    if applied and isinstance(target, dict) and final_key:
                        target[final_key] = new_val
                else:
                    applied = False
            else:
                # Binary profile
                if patch.offset is not None:
                    if 0 <= patch.offset < len(current_state):
                        old_val = current_state[patch.offset]

                        # Check compare value
                        if patch.compare_value is not None:
                            compare_matched = old_val == patch.compare_value

                        # Check conditions
                        if patch.conditions:
                            conditions_passed = all(cond(old_val) for cond in patch.conditions)

                        # Compute new value
                        if isinstance(old_val, int) and isinstance(patch.new_value, int):
                            try:
                                new_val = _calculate_new_value_v2(old_val, patch)
                            except Exception:
                                new_val = patch.new_value
                        else:
                            new_val = patch.new_value

                        # Update mutable state if patch is applied
                        applied = conditions_passed and (
                            compare_matched is None or compare_matched
                        )
                        if applied:
                            with contextlib.suppress(Exception):
                                current_state[patch.offset] = new_val & 0xFF
                    else:
                        old_val = None
                        new_val = patch.new_value
                        compare_matched = False
                        applied = False
                else:
                    applied = False

            # 3. Validate with safety engine on the state BEFORE this patch was applied
            # Prepare state representation before application
            if game_profile is not None:
                # To be absolutely sure, serialize current_state BEFORE this patch's application.
                # Let's recreate/serialize the pre-patch state.
                if is_json:
                    # Let's construct pre-patch json dict
                    pre_patch_dict = copy.deepcopy(current_state)
                    if applied and key_path is not None:
                        # Revert key
                        keys = key_path.split(".")
                        t = pre_patch_dict
                        for key in keys[:-1]:
                            if isinstance(t, dict) and key in t:
                                t = t[key]
                        final_key = keys[-1] if keys else ""
                        if isinstance(t, dict) and final_key in t:
                            t[final_key] = old_val
                    bytes_to_validate = json.dumps(pre_patch_dict).encode("utf-8")
                else:
                    pre_patch_bytes = bytearray(current_state)
                    in_bounds = (
                        patch.offset is not None
                        and 0 <= patch.offset < len(pre_patch_bytes)
                    )
                    if applied and in_bounds and patch.offset is not None:
                        pre_patch_bytes[patch.offset] = old_val
                    bytes_to_validate = bytes(pre_patch_bytes)

                try:
                    safety_res = safety_engine.validate_patch(
                        patch, game_profile, bytes_to_validate, safe_mode=False
                    )
                    safety_passed = safety_res.is_safe
                    safety_errors = safety_res.errors
                except Exception as e:
                    safety_passed = False
                    safety_errors = [str(e)]

            results.append(
                PreviewResult(
                    field_name=field_name,
                    offset_or_key_path=offset_or_key_path,
                    old_value=old_val,
                    new_value=new_val,
                    compare_matched=compare_matched,
                    safety_passed=safety_passed,
                    safety_errors=safety_errors,
                    applied=applied,
                )
            )

        return results
