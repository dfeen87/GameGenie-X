"""Unit tests for the Code Generator module (E1)."""

from __future__ import annotations

import pytest

from gamegenie_x.decoder import decode
from gamegenie_x.game_profiles import load_game_profile_by_id
from gamegenie_x.generator import CodeGenerator, InvalidFieldError, OutOfRangeValueError


def test_generator_validate_field() -> None:
    """Test field validation for binary and nested profiles."""
    profile = load_game_profile_by_id("rpg_hero", profiles_dir="profiles")
    generator = CodeGenerator()

    # Valid fields
    generator.validate_field("player.stats.hp", profile)
    generator.validate_field("gold", profile)

    # Invalid fields
    with pytest.raises(InvalidFieldError, match="not found"):
        generator.validate_field("player.stats.invalid_stat", profile)

    with pytest.raises(InvalidFieldError, match="not found"):
        generator.validate_field("non_existent", profile)


def test_generator_generate_code_roundtrip() -> None:
    """Test generating a code and decoding it back, matching original inputs."""
    profile = load_game_profile_by_id("rpg_hero", profiles_dir="profiles")
    generator = CodeGenerator()

    # RPG Hero hp is offset 10 (0x0A). Value 200 (0xC8).
    code = generator.generate_code("player.stats.hp", 200, profile)
    assert len(code) == 17  # formatted includes dashes: XXXXX-XXXXX-XXXXX

    # Decode using the legacy decoder
    patch = decode(code)
    assert patch.address == 10
    assert patch.value == 200


def test_generator_out_of_range_value() -> None:
    """Test that out-of-range value inputs raise OutOfRangeValueError."""
    profile = load_game_profile_by_id("rpg_hero", profiles_dir="profiles")
    generator = CodeGenerator()

    # RPG Hero HP range is [1, 999] but 8-bit limit of Code is 255.
    # Out of range of 8-bit
    with pytest.raises(OutOfRangeValueError, match="exceeds the 8-bit limit"):
        generator.generate_code("player.stats.hp", 300, profile)

    # Out of range of profile minimum (0 is invalid since min is 1)
    with pytest.raises(OutOfRangeValueError, match="allowed range"):
        generator.generate_code("player.stats.hp", 0, profile)


def test_generator_encode_payload_direct() -> None:
    """Test direct bit-packing payload validation boundaries."""
    generator = CodeGenerator()

    # 32-bit limit for offset
    with pytest.raises(OutOfRangeValueError, match="32-bit range"):
        generator.encode_payload(0x100000000, 100)

    # 8-bit limit for value
    with pytest.raises(OutOfRangeValueError, match="8-bit range"):
        generator.encode_payload(100, 256)
