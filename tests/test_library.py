"""Unit tests for the Patch Library module (E2)."""

from __future__ import annotations

import pytest

from gamegenie_x import SafetyRulesEngine
from gamegenie_x.game_profiles import load_game_profile_by_id
from gamegenie_x.library import PatchLibrary


def test_library_loading() -> None:
    """Test that standard games and category structure loads correctly."""
    lib = PatchLibrary(profiles_dir="profiles")

    games = lib.list_games()
    assert "rpg_hero" in games
    assert "scifi_space" in games

    rpg_categories = lib.list_categories("rpg_hero")
    assert "Stats" in rpg_categories
    assert "Inventory" in rpg_categories

    scifi_categories = lib.list_categories("scifi_space")
    assert "Difficulty" in scifi_categories


def test_library_get_patches_and_decode() -> None:
    """Test that retrieved library patches decode successfully to PatchSequences."""
    lib = PatchLibrary(profiles_dir="profiles")

    patches = lib.get_patches("rpg_hero", "Stats")
    assert len(patches) >= 2

    infinite_hp = patches[0]
    assert infinite_hp.name == "Infinite HP"

    # Decoding must succeed and match expected offsets
    seq = infinite_hp.get_sequence(profiles_dir="profiles")
    assert len(seq.patches) == 1
    assert seq.patches[0].offset == 10  # HP offset is 10


def test_library_invalid_queries_raises() -> None:
    """Test library throws KeyError on non-existent game or category."""
    lib = PatchLibrary(profiles_dir="profiles")

    with pytest.raises(KeyError, match="not found"):
        lib.list_categories("invalid_game_id")

    with pytest.raises(KeyError, match="not found"):
        lib.get_patches("rpg_hero", "InvalidCategory")


def test_library_patch_safety_validation() -> None:
    """Test validating library patches against profiles and safety rule metadata."""
    lib = PatchLibrary(profiles_dir="profiles")
    rpg_profile = load_game_profile_by_id("rpg_hero", profiles_dir="profiles")
    engine = SafetyRulesEngine()

    hp_patch = lib.get_patches("rpg_hero", "Stats")[0]
    seq = hp_patch.get_sequence(profiles_dir="profiles")
    p = seq.patches[0]

    # Valid HP
    save_bytes = b"\x00" * 200
    res = engine.validate_patch(p, rpg_profile, save_bytes, safe_mode=False)
    assert res.is_safe is True
