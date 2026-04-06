"""Round-trip encoding and decoding tests for GameGenie-X."""

import pytest

from gamegenie_x.decoder import decode
from gamegenie_x.encoder import encode
from gamegenie_x.models import Flags, Patch, PatchType, Platform


@pytest.mark.parametrize(
    "platform",
    [
        Platform.NES,
        Platform.SNES,
        Platform.GENESIS,
        Platform.GAMEBOY,
        Platform.GAMEGEAR,
        Platform.NDS,
        Platform.N3DS,
        Platform.PSP,
        Platform.PSVITA,
        Platform.SWITCH,
        Platform.DOLPHIN,
        Platform.CITRA,
        Platform.RPCS3,
        Platform.YUZU,
        Platform.PC,
    ],
)
def test_roundtrip_all_platforms(platform: Platform) -> None:
    """Test encode and decode round-trip for standard patches on all supported platforms."""
    patch = Patch(
        address=0x1234,
        value=0xAB,
        compare=0xCD if platform in (
            Platform.NES, Platform.GAMEBOY, Platform.GAMEGEAR, Platform.NDS,
            Platform.N3DS, Platform.PSP, Platform.PSVITA, Platform.SWITCH,
            Platform.DOLPHIN, Platform.CITRA, Platform.RPCS3, Platform.YUZU, Platform.PC
        ) else 0,
        platform=platform,
    )
    code = encode(patch)
    decoded = decode(code)
    assert decoded == patch


def test_roundtrip_all_zeros() -> None:
    """Test round-trip with a patch of all zero values."""
    patch = Patch(address=0, value=0, platform=Platform.NES)
    code = encode(patch)
    decoded = decode(code)
    assert decoded == patch


def test_roundtrip_max_values_universal() -> None:
    """Test round-trip with maximum possible values for all fields (ignoring platform limits)."""
    patch = Patch(
        address=0xFFFFFFFF,
        value=0xFF,
        compare=0xFF,
        platform=Platform.UNIVERSAL,
        patch_type=PatchType.XOR,
        flags=Flags(
            compare_enabled=True,
            wide_data=True,
            read_only=True,
            persistent=True,
            reserved=0xF,
        ),
    )
    code = encode(patch, validate=False)
    decoded = decode(code, verify=True)
    assert decoded == patch


@pytest.mark.parametrize(
    "address,value,compare",
    [
        (0x00000001, 0x01, 0x01),
        (0x7FFFFFFF, 0x7F, 0x7F),
        (0xAAAAAAAA, 0xAA, 0xAA),
        (0x55555555, 0x55, 0x55),
    ],
)
def test_roundtrip_fuzz_boundaries(address: int, value: int, compare: int) -> None:
    """Fuzz bit boundaries with various patterns."""
    patch = Patch(
        address=address,
        value=value,
        compare=compare,
        platform=Platform.NES,
        flags=Flags(compare_enabled=True),
    )
    code = encode(patch, validate=False)
    decoded = decode(code)
    assert decoded == patch


def test_roundtrip_flags_combinations() -> None:
    """Test round-trip with various flag combinations."""
    flags = Flags(compare_enabled=True, persistent=True)
    patch = Patch(address=0x100, value=0x10, flags=flags, platform=Platform.NES)
    code = encode(patch)
    decoded = decode(code)
    assert decoded.flags == flags


def test_roundtrip_patch_types() -> None:
    """Test round-trip with different patch types."""
    for p_type in list(PatchType)[:6]:  # Test first 6 types
        patch = Patch(address=0x100, value=0x10, patch_type=p_type, platform=Platform.NES)
        code = encode(patch)
        decoded = decode(code)
        assert decoded.patch_type == p_type
