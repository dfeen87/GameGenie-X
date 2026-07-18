"""Unit tests for the PreviewEngine (Module C)."""

import json

import pytest

from gamegenie_x.game_profiles import GameProfile
from gamegenie_x.models import Flags, PatchType
from gamegenie_x.patch_v2 import Patch, PatchSequence, TargetType
from gamegenie_x.preview import PreviewEngine
from gamegenie_x.profiles import FieldDef, PlatformProfile


@pytest.fixture
def binary_save_data() -> bytes:
    return bytes([0x10, 0x20, 0x30, 0x40, 0x50])


@pytest.fixture
def json_save_data() -> bytes:
    data = {
        "player": {
            "gold": 100,
            "hp": 50,
        },
        "system": {
            "unlocked": False
        }
    }
    return json.dumps(data).encode("utf-8")


def test_preview_binary_basic(binary_save_data: bytes) -> None:
    # Set up mock PlatformProfile
    profile = PlatformProfile(
        platform="mock_bin",
        name="Mock Binary Profile",
        short_name="MBIN",
        address_bits=8,
        max_address=0xFF,
        data_bits=8,
        compare_supported=True,
        default_patch_type=PatchType.REPLACE,
        default_flags=Flags(),
        fields={
            "player_hp": FieldDef(offset=1, type="int", description="HP"),
            "player_mp": FieldDef(offset=2, type="int", description="MP"),
        }
    )

    # Patch 1: Replace HP with 99
    # Patch 2: MP replace with 88 with compare=0x30 (matches)
    # Patch 3: MP replace with 77 with compare=0x99 (does not match)
    p1 = Patch(target_type=TargetType.SAVE, offset=1, new_value=99)
    p2 = Patch(target_type=TargetType.SAVE, offset=2, new_value=88, compare_value=0x30)
    p3 = Patch(target_type=TargetType.SAVE, offset=2, new_value=77, compare_value=0x99)

    seq = PatchSequence([p1, p2, p3])
    engine = PreviewEngine()
    results = engine.preview(seq, binary_save_data, profile)

    assert len(results) == 3

    # Check P1 (HP)
    r1 = results[0]
    assert r1.field_name == "player_hp"
    assert r1.offset_or_key_path == "0x1"
    assert r1.old_value == 0x20
    assert r1.new_value == 99
    assert r1.compare_matched is None
    assert r1.applied is True

    # Check P2 (MP, compare matches)
    r2 = results[1]
    assert r2.field_name == "player_mp"
    assert r2.offset_or_key_path == "0x2"
    assert r2.old_value == 0x30
    assert r2.new_value == 88
    assert r2.compare_matched is True
    assert r2.applied is True

    # Check P3 (MP, compare fails because state was updated to 88 by P2!)
    r3 = results[2]
    assert r3.field_name == "player_mp"
    assert r3.offset_or_key_path == "0x2"
    assert r3.old_value == 88  # Chained sequence state!
    assert r3.new_value == 77
    assert r3.compare_matched is False
    assert r3.applied is False

    # Ensure source was not mutated
    assert binary_save_data == bytes([0x10, 0x20, 0x30, 0x40, 0x50])


def test_preview_json_basic(json_save_data: bytes) -> None:
    # Mock GameProfile
    game_profile = GameProfile(
        game_id="mock_json_game",
        display_name="Mock JSON Game",
        save_structure={
            "player": {
                "gold": 100,
                "hp": 50,
            }
        },
        value_ranges={
            "player.hp": (1, 999),
            "player.gold": (0, 9999)
        },
        flags={},
        signature=b"",
        format="json",
    )

    p1 = Patch(target_type=TargetType.CONFIG, key_path="player.hp", new_value=250)
    p2 = Patch(
        target_type=TargetType.CONFIG,
        key_path="player.gold",
        new_value=50,
        patch_type=PatchType.INCREMENT,
    )

    seq = PatchSequence([p1, p2])
    engine = PreviewEngine()
    results = engine.preview(seq, json_save_data, game_profile)

    assert len(results) == 2

    r1 = results[0]
    assert r1.field_name == "player.hp"
    assert r1.old_value == 50
    assert r1.new_value == 250
    assert r1.applied is True

    r2 = results[1]
    assert r2.field_name == "player.gold"
    assert r2.old_value == 100
    assert r2.new_value == 150
    assert r2.applied is True

    # Verify original JSON data is completely unchanged
    original = json.loads(json_save_data.decode("utf-8"))
    assert original["player"]["hp"] == 50
    assert original["player"]["gold"] == 100


def test_preview_safety_rules_integration(binary_save_data: bytes) -> None:
    # RPG Hero hp range is [1, 999]. Let's create game profile
    game_profile = GameProfile(
        game_id="mock_rpg_hero",
        display_name="Mock RPG Hero",
        save_structure={
            "player": {
                "hp": 1,
            },
            "gold": 4
        },
        value_ranges={
            "player.hp": (1, 999),
            "gold": (0, 100)
        },
        flags={
            "gold_unsafe": True
        },
        signature=b"",
        format="binary",
    )

    # Valid HP replace
    p_valid = Patch(target_type=TargetType.SAVE, offset=1, new_value=150)
    # Value range violation (HP = 5000 is outside [1, 999])
    p_unsafe_val = Patch(target_type=TargetType.SAVE, offset=1, new_value=5000)
    # Forbidden field violation
    p_forbidden = Patch(target_type=TargetType.SAVE, offset=4, new_value=50)

    seq = PatchSequence([p_valid, p_unsafe_val, p_forbidden])
    engine = PreviewEngine()
    results = engine.preview(seq, binary_save_data, game_profile)

    assert len(results) == 3

    assert results[0].safety_passed is True
    assert not results[0].safety_errors

    assert results[1].safety_passed is False
    assert any("Value range violation" in err for err in results[1].safety_errors)

    assert results[2].safety_passed is False
    assert any("Forbidden field access" in err for err in results[2].safety_errors)
