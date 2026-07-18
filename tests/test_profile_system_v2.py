"""Unit tests for the Profile System v2 (Module B)."""

import json
from pathlib import Path

import pytest

from gamegenie_x import (
    GameProfile,
    InvalidProfileError,
    Platform,
    ProfileDetector,
    SafetyRulesEngine,
    UnsafePatchError,
    load_game_profile,
    load_game_profile_by_id,
)
from gamegenie_x import (
    Patch as LegacyPatch,
)
from gamegenie_x.patch_v2 import Patch as ModernPatch
from gamegenie_x.patch_v2 import PatchSequence, TargetType
from gamegenie_x.profiles import load_profile


@pytest.fixture
def temp_profiles_dir(tmp_path: Path) -> Path:
    """Fixture to create a temporary profiles directory with test JSON profiles."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()

    # 1. Valid RPG Game Profile (Binary format)
    rpg_profile = {
        "game_id": "rpg_hero",
        "display_name": "RPG Hero v2",
        "save_structure": {
            "player": {
                "stats": {
                    "hp": 10,
                    "mp": 12,
                    "is_alive": 16,
                },
                "level": 14,
            },
            "gold": 20,
        },
        "value_ranges": {
            "player.stats.hp": [1, 999],
            "player.stats.mp": [1, 99],
            "player.level": [1, 99],
            "gold": [0, 999999],
        },
        "flags": {
            "player.stats.is_alive": True,  # boolean field check example
            "anti_cheat": True,             # general anti-cheat check
            "gold_unsafe": True,            # forbidden field example
        },
        "signature": [0x52, 0x50, 0x47, 0x48],  # "RPGH"
        "file_size_range": [100, 200],
        "format": "binary",
        "magic_number": "52504748",  # "RPGH"
    }

    # 2. Valid Sci-Fi Game Profile (JSON format)
    scifi_profile = {
        "game_id": "scifi_space",
        "display_name": "Sci-Fi Space Adventure",
        "save_structure": {
            "energy": 5,
            "ship": {
                "shield": 25,
                "is_active": 30,
            }
        },
        "value_ranges": {
            "energy": [0, 100],
            "ship.shield": [0, 500],
        },
        "flags": {
            "ship.is_active": True,  # is boolean
        },
        "signature": [0x7B, 0x22, 0x73, 0x63],  # '{"sc'
        "file_size_range": [10, 500],
        "format": "json",
    }

    with open(profiles_dir / "rpg_hero.json", "w", encoding="utf-8") as f:
        json.dump(rpg_profile, f)

    with open(profiles_dir / "scifi_space.json", "w", encoding="utf-8") as f:
        json.dump(scifi_profile, f)

    return profiles_dir


# ==========================================
# 1. Profile Schema & Loader Tests
# ==========================================

def test_load_valid_game_profile(temp_profiles_dir: Path) -> None:
    """Test loading a fully valid game profile JSON."""
    profile = load_game_profile_by_id("rpg_hero", profiles_dir=temp_profiles_dir)
    assert profile.game_id == "rpg_hero"
    assert profile.display_name == "RPG Hero v2"
    assert profile.format == "binary"
    assert profile.signature == b"RPGH"
    assert profile.magic_number == b"RPGH"
    assert profile.file_size_range == (100, 200)


def test_load_profile_missing_field(temp_profiles_dir: Path) -> None:
    """Test that missing required fields raises InvalidProfileError."""
    bad_profile = {
        "game_id": "broken",
        "display_name": "Broken Game",
        # missing save_structure, value_ranges, flags, signature
    }
    bad_file = temp_profiles_dir / "broken.json"
    with open(bad_file, "w", encoding="utf-8") as f:
        json.dump(bad_profile, f)

    with pytest.raises(InvalidProfileError, match="missing required field"):
        load_game_profile(bad_file)


def test_load_profile_invalid_types(temp_profiles_dir: Path) -> None:
    """Test that invalid field types raise InvalidProfileError."""
    bad_profile = {
        "game_id": 123,  # should be str
        "display_name": "Broken Game",
        "save_structure": {},
        "value_ranges": {},
        "flags": {},
        "signature": "not-a-list-or-bytes",
    }
    bad_file = temp_profiles_dir / "broken_types.json"
    with open(bad_file, "w", encoding="utf-8") as f:
        json.dump(bad_profile, f)

    with pytest.raises(InvalidProfileError):
        load_game_profile(bad_file)


def test_load_profile_invalid_range(temp_profiles_dir: Path) -> None:
    """Test that range verification rejects min > max."""
    bad_profile = {
        "game_id": "broken_range",
        "display_name": "Broken Range Game",
        "save_structure": {"hp": 10},
        "value_ranges": {"hp": [100, 50]},  # min 100 > max 50
        "flags": {},
        "signature": [0x01],
    }
    bad_file = temp_profiles_dir / "broken_range.json"
    with open(bad_file, "w", encoding="utf-8") as f:
        json.dump(bad_profile, f)

    with pytest.raises(InvalidProfileError, match="min.*cannot be greater than max"):
        load_game_profile(bad_file)


def test_load_profile_negative_offset(temp_profiles_dir: Path) -> None:
    """Test that negative offsets are rejected in save_structure."""
    bad_profile = {
        "game_id": "neg_offset",
        "display_name": "Negative Offset Game",
        "save_structure": {"hp": -10},  # negative offset
        "value_ranges": {},
        "flags": {},
        "signature": [0x01],
    }
    bad_file = temp_profiles_dir / "neg_offset.json"
    with open(bad_file, "w", encoding="utf-8") as f:
        json.dump(bad_profile, f)

    with pytest.raises(InvalidProfileError, match="cannot be negative"):
        load_game_profile(bad_file)


def test_load_profile_invalid_save_structure(temp_profiles_dir: Path) -> None:
    """Test that invalid types in save_structure are rejected."""
    bad_profile = {
        "game_id": "invalid_struct",
        "display_name": "Invalid Struct Game",
        "save_structure": {"hp": "not-an-offset-or-dict"},
        "value_ranges": {},
        "flags": {},
        "signature": [0x01],
    }
    bad_file = temp_profiles_dir / "invalid_struct.json"
    with open(bad_file, "w", encoding="utf-8") as f:
        json.dump(bad_profile, f)

    with pytest.raises(InvalidProfileError, match="must be an integer.*or nested dictionary"):
        load_game_profile(bad_file)


def test_game_profile_get_offset(temp_profiles_dir: Path) -> None:
    """Test GameProfile.get_offset with nested and flat field paths."""
    profile = load_game_profile_by_id("rpg_hero", profiles_dir=temp_profiles_dir)

    # Flat key
    assert profile.get_offset("gold") == 20

    # Nested keys
    assert profile.get_offset("player.stats.hp") == 10
    assert profile.get_offset("player.stats.mp") == 12
    assert profile.get_offset("player.level") == 14

    # Non-existent keys
    assert profile.get_offset("player.stats.invalid") is None
    assert profile.get_offset("invalid_key") is None
    assert profile.get_offset("player.invalid.hp") is None


# ==========================================
# 2. Auto-Discovery Tests
# ==========================================

def test_detector_signature_match(temp_profiles_dir: Path) -> None:
    """Test auto-discovery of a profile based on a signature match."""
    detector = ProfileDetector(profiles_dir=temp_profiles_dir)

    # Save bytes starts with "RPGH"
    save_bytes = b"RPGH" + b"\x00" * 150
    detected = detector.detect(save_bytes)
    assert detected is not None
    assert detected.game_id == "rpg_hero"


def test_detector_no_match_diagnostics(temp_profiles_dir: Path) -> None:
    """Test auto-discovery returns None and provides failure diagnostics when no match."""
    detector = ProfileDetector(profiles_dir=temp_profiles_dir)

    # Save bytes with completely random prefix
    save_bytes = b"WXYZ" + b"\x00" * 150
    detected = detector.detect(save_bytes)
    assert detected is None
    assert detector.last_diagnostic is not None
    assert "rpg_hero" in detector.last_diagnostic.failures
    assert detector.last_diagnostic.failures["rpg_hero"] == "Signature prefix mismatch."


def test_detector_fallback_heuristics(temp_profiles_dir: Path) -> None:
    """Test detector fallback heuristics when signature match fails or is ambiguous."""
    # Create two profiles with same signature but different file size ranges
    p1 = GameProfile(
        game_id="game_a",
        display_name="Game A",
        save_structure={"hp": 10},
        value_ranges={"hp": (1, 100)},
        flags={},
        signature=b"SAME",
        file_size_range=(100, 200),
        format="binary",
    )
    p2 = GameProfile(
        game_id="game_b",
        display_name="Game B",
        save_structure={"hp": 10},
        value_ranges={"hp": (1, 100)},
        flags={},
        signature=b"SAME",
        file_size_range=(500, 600),
        format="binary",
    )

    detector = ProfileDetector(profiles=[p1, p2])

    # Save bytes has signature "SAME" and size 150 (matches p1's file_size_range)
    # We set index 10 to 50 so that value_range check for "hp" passes
    save_bytes = bytearray(b"SAME" + b"\x00" * 146)
    save_bytes[10] = 50
    detected = detector.detect(bytes(save_bytes))
    assert detected is not None
    assert detected.game_id == "game_a"

    # Save bytes has signature "SAME" and size 550 (matches p2's file_size_range)
    save_bytes2 = bytearray(b"SAME" + b"\x00" * 546)
    save_bytes2[10] = 50
    detected = detector.detect(bytes(save_bytes2))
    assert detected is not None
    assert detected.game_id == "game_b"


def test_detector_field_and_range_heuristics(temp_profiles_dir: Path) -> None:
    """Test heuristics fallback by scanning for known field offsets and value ranges."""
    # Profile with NO signature, but has file_size_range and value_ranges
    p_no_sig = GameProfile(
        game_id="no_sig_rpg",
        display_name="No Signature RPG",
        save_structure={"hp": 5, "mp": 8},
        value_ranges={"hp": (10, 50), "mp": (100, 200)},
        flags={},
        signature=b"",  # Empty signature
        file_size_range=(10, 20),
        format="binary",
    )

    detector = ProfileDetector(profiles=[p_no_sig])

    # Save bytes has size 15. hp at 5 is 25 (valid), mp at 8 is 150 (valid)
    save_bytes = bytearray([0] * 15)
    save_bytes[5] = 25
    save_bytes[8] = 150

    detected = detector.detect(bytes(save_bytes))
    assert detected is not None
    assert detected.game_id == "no_sig_rpg"


# ==========================================
# 3. Safety Rules Engine Tests
# ==========================================

def test_safety_engine_value_range_enforcement(temp_profiles_dir: Path) -> None:
    """Test safety engine rejects values outside the allowed value ranges."""
    profile = load_game_profile_by_id("rpg_hero", profiles_dir=temp_profiles_dir)
    engine = SafetyRulesEngine()

    # RPG Hero hp range is [1, 999]
    # Legacy patch address 10 is hp offset
    valid_patch = LegacyPatch(address=10, value=200, platform=Platform.UNIVERSAL)
    save_bytes = b"\x00" * 100

    # Under safe_mode=False
    res_valid = engine.validate_patch(valid_patch, profile, save_bytes, safe_mode=False)
    assert res_valid.is_safe is True
    assert not res_valid.errors

    # Invalid value (out of range, HP can't be 1500)
    invalid_modern = ModernPatch(target_type=TargetType.SAVE, offset=10, new_value=1500)

    # Should raise UnsafePatchError under safe_mode=True
    with pytest.raises(UnsafePatchError, match="Value range violation"):
        engine.validate_patch(invalid_modern, profile, save_bytes, safe_mode=True)

    # Should return safety result under safe_mode=False
    res_invalid = engine.validate_patch(invalid_modern, profile, save_bytes, safe_mode=False)
    assert res_invalid.is_safe is False
    assert any("Value range violation" in err for err in res_invalid.errors)


def test_safety_engine_structural_integrity(temp_profiles_dir: Path) -> None:
    """Test safety engine rejects patches that fall out of file bounds."""
    profile = load_game_profile_by_id("rpg_hero", profiles_dir=temp_profiles_dir)
    engine = SafetyRulesEngine()

    # File size is 50 bytes. HP offset is 10, which is fine.
    # But let's patch gold at offset 20. If save_bytes is only 15 bytes, it's out of bounds!
    save_bytes_short = b"\x00" * 15
    patch_gold = ModernPatch(target_type=TargetType.SAVE, offset=20, new_value=100)

    with pytest.raises(UnsafePatchError, match="Structural integrity violation"):
        engine.validate_patch(patch_gold, profile, save_bytes_short, safe_mode=True)


def test_safety_engine_field_type_correctness(temp_profiles_dir: Path) -> None:
    """Test safety engine rejects non-boolean values for boolean-typed fields."""
    profile = load_game_profile_by_id("scifi_space", profiles_dir=temp_profiles_dir)
    engine = SafetyRulesEngine()

    # 'ship.is_active' at offset 30 is boolean-typed.
    valid_patch = ModernPatch(target_type=TargetType.SAVE, offset=30, new_value=True)
    save_bytes = b"\x00" * 100

    res = engine.validate_patch(valid_patch, profile, save_bytes, safe_mode=False)
    assert res.is_safe is True

    # Non-boolean value like 42
    invalid_patch = ModernPatch(target_type=TargetType.SAVE, offset=30, new_value=42)
    with pytest.raises(UnsafePatchError, match="Field type mismatch"):
        engine.validate_patch(invalid_patch, profile, save_bytes, safe_mode=True)


def test_safety_engine_forbidden_fields(temp_profiles_dir: Path) -> None:
    """Test safety engine blocks forbidden or anti-cheat marked fields."""
    profile = load_game_profile_by_id("rpg_hero", profiles_dir=temp_profiles_dir)
    engine = SafetyRulesEngine()

    # gold_unsafe is marked in flags. Let's lookup offset of gold (20).
    patch_gold = ModernPatch(target_type=TargetType.SAVE, offset=20, new_value=50000)
    save_bytes = b"\x00" * 100

    with pytest.raises(UnsafePatchError, match="Forbidden field access"):
        engine.validate_patch(patch_gold, profile, save_bytes, safe_mode=True)

    # Let's check anti_cheat block
    patch_ac = ModernPatch(
        target_type=TargetType.SAVE, offset=0, key_path="anti_cheat", new_value=True
    )
    with pytest.raises(UnsafePatchError, match="Forbidden field access"):
        engine.validate_patch(patch_ac, profile, save_bytes, safe_mode=True)


# ==========================================
# 4. Patch Engine Integration Tests
# ==========================================

def test_legacy_patch_application_with_safety_check(
    temp_profiles_dir: Path, tmp_path: Path
) -> None:
    """Test applying legacy patch via apply_patch_to_file with safety integration."""
    game_profile = load_game_profile_by_id("rpg_hero", profiles_dir=temp_profiles_dir)
    platform_profile = load_profile(Platform.NES)  # Using NES as dummy platform profile

    # Create dummy save file
    save_file = tmp_path / "save.bin"
    save_file.write_bytes(b"\x00" * 150)

    # Patch with valid HP value
    valid_patch = LegacyPatch(address=10, value=200, platform=Platform.NES)

    from gamegenie_x.patcher import apply_patch_to_file
    modified = apply_patch_to_file(
        valid_patch, save_file, platform_profile, game_profile=game_profile, safe_mode=True
    )
    assert modified is True
    assert save_file.read_bytes()[10] == 200

    # Patch with invalid (out of bounds) address
    invalid_patch = LegacyPatch(address=300, value=200, platform=Platform.NES)
    with pytest.raises(UnsafePatchError, match="Structural integrity violation"):
        apply_patch_to_file(
            invalid_patch, save_file, platform_profile, game_profile=game_profile, safe_mode=True
        )


def test_modern_patch_sequence_with_safety_check(temp_profiles_dir: Path, tmp_path: Path) -> None:
    """Test applying modern PatchSequence with integrated safety check."""
    game_profile = load_game_profile_by_id("rpg_hero", profiles_dir=temp_profiles_dir)
    platform_profile = load_profile(Platform.NES)

    # Create dummy save file
    save_file = tmp_path / "save.bin"
    save_file.write_bytes(b"\x00" * 150)

    # Sequence of valid HP and MP modifications
    patch_hp = ModernPatch(target_type=TargetType.SAVE, offset=10, new_value=150)
    patch_mp = ModernPatch(target_type=TargetType.SAVE, offset=12, new_value=50)
    seq = PatchSequence([patch_hp, patch_mp])

    modified = seq.apply(save_file, platform_profile, game_profile=game_profile, safe_mode=True)
    assert modified is True

    # Sequence with one invalid HP (out of range, e.g. 50000)
    patch_invalid_hp = ModernPatch(target_type=TargetType.SAVE, offset=10, new_value=50000)
    seq_invalid = PatchSequence([patch_invalid_hp])

    with pytest.raises(UnsafePatchError, match="Value range violation"):
        seq_invalid.apply(save_file, platform_profile, game_profile=game_profile, safe_mode=True)
