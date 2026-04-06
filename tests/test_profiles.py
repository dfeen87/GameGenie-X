"""Tests for the profiles module."""

import pytest

from gamegenie_x.models import Patch, Platform
from gamegenie_x.profiles import load_all_profiles, load_profile, validate_patch


def test_profiles_load_existing_profile() -> None:
    """Test loading a known existing profile (NES)."""
    profile = load_profile(Platform.NES)
    assert profile.name == "Nintendo Entertainment System"
    assert profile.short_name == "NES"
    assert profile.address_bits == 15
    assert profile.data_bits == 8
    assert profile.compare_supported is True


def test_profiles_load_missing_profile_raises() -> None:
    """Test that loading a non-existent profile raises FileNotFoundError or ValueError."""
    with pytest.raises((FileNotFoundError, ValueError)):
        load_profile(Platform.UNIVERSAL)


def test_profiles_load_all_profiles() -> None:
    """Test loading all available profiles."""
    profiles = load_all_profiles()
    assert Platform.NES in profiles
    assert Platform.SNES in profiles
    assert Platform.GENESIS in profiles
    assert Platform.GAMEBOY in profiles
    assert Platform.GAMEGEAR in profiles
    assert Platform.NDS in profiles
    assert Platform.N3DS in profiles
    assert Platform.PSP in profiles
    assert Platform.PSVITA in profiles
    assert Platform.SWITCH in profiles
    assert Platform.DOLPHIN in profiles
    assert Platform.CITRA in profiles
    assert Platform.RPCS3 in profiles
    assert Platform.YUZU in profiles
    assert Platform.PC in profiles


def test_profiles_validate_good_patch(nes_patch: Patch) -> None:
    """Test validation of a well-formed patch."""
    profile = load_profile(Platform.NES)
    errors = validate_patch(nes_patch, profile)
    assert not errors


def test_profiles_validate_bad_patch_address_too_large() -> None:
    """Test validation fails when address exceeds platform max."""
    patch = Patch(address=0xFFFFFF, value=0x09, platform=Platform.NES)
    profile = load_profile(Platform.NES)
    errors = validate_patch(patch, profile)
    assert len(errors) > 0
    assert any("exceeds maximum" in e for e in errors)


def test_profiles_validate_bad_patch_platform_mismatch(snes_patch: Patch) -> None:
    """Test validation fails when patch platform doesn't match profile."""
    profile = load_profile(Platform.NES)
    errors = validate_patch(snes_patch, profile)
    assert len(errors) > 0
    assert any("Platform mismatch" in e for e in errors)
