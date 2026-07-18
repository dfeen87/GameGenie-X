"""Unit tests for the SandboxEmulator (Module C)."""

import json
import pytest

from gamegenie_x.game_profiles import GameProfile
from gamegenie_x.patch_v2 import Patch, PatchSequence, TargetType
from gamegenie_x.sandbox import SandboxEmulator
from gamegenie_x.safety import UnsafePatchError


@pytest.fixture
def binary_game_profile() -> GameProfile:
    return GameProfile(
        game_id="rpg_sandbox",
        display_name="RPG Sandbox Game",
        save_structure={
            "player": {
                "stats": {
                    "hp": 5,
                    "mp": 10,
                },
                "level": 15,
            },
            "gold": 20,
        },
        value_ranges={
            "player.stats.hp": (10, 999),
            "player.stats.mp": (5, 99),
            "player.level": (1, 99),
            "gold": (0, 999999),
        },
        flags={
            "gold_unsafe": True,
        },
        signature=b"RPGS",
        file_size_range=(100, 200),
        format="binary",
    )


@pytest.fixture
def json_game_profile() -> GameProfile:
    return GameProfile(
        game_id="json_sandbox",
        display_name="JSON Sandbox Game",
        save_structure={
            "energy": 5,
            "ship": {
                "shield": 10,
                "is_active": 15,
            }
        },
        value_ranges={
            "energy": (0, 100),
            "ship.shield": (50, 500),
        },
        flags={
            "ship.is_active": True,
        },
        signature=b"",
        format="json",
    )


def test_sandbox_binary_loading(binary_game_profile: GameProfile) -> None:
    emu = SandboxEmulator()
    emu.load_virtual_save(binary_game_profile)

    state = emu.dump_state()
    assert len(state) == 100  # min of file_size_range

    # Verify defaults are populated at offsets
    # player.stats.hp (offset 5) -> min value is 10
    assert state[5] == 10

    # player.stats.mp (offset 10) -> min value is 5
    assert state[10] == 5

    # player.level (offset 15) -> min value is 1
    assert state[15] == 1

    # gold (offset 20) -> min value is 0
    assert state[20] == 0


def test_sandbox_json_loading(json_game_profile: GameProfile) -> None:
    emu = SandboxEmulator()
    emu.load_virtual_save(json_game_profile)

    state = emu.dump_state()
    assert isinstance(state, dict)

    # Verify nested synthetic structure and defaults
    assert state["energy"] == 0
    assert state["ship"]["shield"] == 50
    assert state["ship"]["is_active"] is False


def test_sandbox_apply_patches_binary(binary_game_profile: GameProfile) -> None:
    emu = SandboxEmulator()
    emu.load_virtual_save(binary_game_profile)

    # Apply some valid patches
    p1 = Patch(target_type=TargetType.SAVE, offset=5, new_value=100) # HP -> 100
    p2 = Patch(target_type=TargetType.SAVE, offset=10, new_value=50) # MP -> 50

    seq = PatchSequence([p1, p2])
    modified = emu.apply_patch_sequence(seq, safe_mode=True)

    assert modified is True
    state = emu.dump_state()
    assert state[5] == 100
    assert state[10] == 50


def test_sandbox_apply_patches_json(json_game_profile: GameProfile) -> None:
    emu = SandboxEmulator()
    emu.load_virtual_save(json_game_profile)

    p1 = Patch(target_type=TargetType.CONFIG, key_path="ship.shield", new_value=350)
    p2 = Patch(target_type=TargetType.CONFIG, key_path="ship.is_active", new_value=True)

    seq = PatchSequence([p1, p2])
    modified = emu.apply_patch_sequence(seq, safe_mode=True)

    assert modified is True
    state = emu.dump_state()
    assert state["ship"]["shield"] == 350
    assert state["ship"]["is_active"] is True


def test_sandbox_safety_validation(binary_game_profile: GameProfile) -> None:
    emu = SandboxEmulator()
    emu.load_virtual_save(binary_game_profile)

    # Attempt to patch gold (which is gold_unsafe marked as True -> Forbidden field!)
    p_unsafe = Patch(target_type=TargetType.SAVE, offset=20, new_value=1000)
    seq = PatchSequence([p_unsafe])

    with pytest.raises(UnsafePatchError, match="Forbidden field access"):
        emu.apply_patch_sequence(seq, safe_mode=True)

    # Verify state was NOT modified due to transactional safety
    assert emu.dump_state()[20] == 0
