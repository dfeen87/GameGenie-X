"""Tests for the bitpack module."""

import pytest

from gamegenie_x.bitpack import (
    pack_full,
    pack_payload,
    unpack_full,
    unpack_payload,
)
from gamegenie_x.models import Flags, Patch, PatchType, Platform


def test_bitpack_payload_roundtrip_all_zeros() -> None:
    """Test packing and unpacking a payload with all zero fields."""
    patch = Patch(address=0, value=0, platform=Platform.NES, patch_type=PatchType.REPLACE)
    payload = pack_payload(patch)
    assert payload == 0
    unpacked = unpack_payload(payload)
    assert unpacked == patch


def test_bitpack_payload_roundtrip_all_ones() -> None:
    """Test packing and unpacking a payload with maximum possible values."""
    patch = Patch(
        address=0xFFFFFFFF,
        value=0xFF,
        compare=0xFF,
        platform=Platform.UNIVERSAL,
        # Cannot construct enum for 0xF if it's reserved/not defined. Use highest.
        # But pack_payload just masks to 4 bits. Let's use XOR which is 5.
        patch_type=PatchType.XOR,
        flags=Flags(
            compare_enabled=True,
            wide_data=True,
            read_only=True,
            persistent=True,
            reserved=0xF,
        ),
    )
    payload = pack_payload(patch)
    unpacked = unpack_payload(payload)
    assert unpacked == patch


def test_bitpack_full_roundtrip() -> None:
    """Test packing and unpacking a full 75-bit integer."""
    patch = Patch(address=0x12345678, value=0xAB, compare=0xCD, platform=Platform.SNES)
    checksum = 0x5A5
    packed = pack_full(patch, checksum)
    unpacked_patch, unpacked_checksum = unpack_full(packed)
    assert unpacked_patch == patch
    assert unpacked_checksum == checksum


def test_bitpack_pack_full_overflow_raises() -> None:
    """Test that pack_full raises OverflowError for too large checksum."""
    patch = Patch(address=0, value=0)
    # We can trigger OverflowError by injecting an invalid value in the object
    # to force pack_full to produce an integer >= (1 << 75).
    # address is shifted by 32 in the 64-bit payload, then 11 in pack_full.
    # Total shift = 43. We need value >= 1 << (75 - 43) = 1 << 32 to overflow,
    # but the packing function masks the address with ((1 << 32) - 1).
    # Wait, the pack_payload function masks EVERYTHING.
    # `payload |= (patch.address & ((1 << 32) - 1)) << ...`
    # So `pack_payload` CANNOT return anything that overflows when shifted.
    # How could it possibly exceed 75 bits if we mask every field strictly?
    # Oh! `packed < 0` is possible if we bypass mask and inject a negative,
    # but again, everything is masked.
    # So the only way `packed` could exceed 75 bits or be < 0 is if we pass a
    # checksum that is huge, but wait... `checksum & ((1 << 11) - 1)`
    # This also masks the checksum!
    # Let me check if `TOTAL_BITS` check can ever hit.
    pass

    # Since all fields are strictly masked, the bounds check in pack_full
    # is actually unreachable with current pack_payload behavior unless
    # we mock pack_payload. Let's mock it to test the boundary check.
    import gamegenie_x.bitpack
    original_pack_payload = gamegenie_x.bitpack.pack_payload
    try:
        gamegenie_x.bitpack.pack_payload = lambda p: (1 << 64)  # Over 64 bits
        with pytest.raises(OverflowError):
            pack_full(patch, 0)
    finally:
        gamegenie_x.bitpack.pack_payload = original_pack_payload

def test_bitpack_unpack_full_overflow_raises() -> None:
    """Test that unpack_full raises OverflowError if integer > 75 bits."""
    with pytest.raises(OverflowError):
        unpack_full(1 << 76)


def test_bitpack_individual_field_extraction(nes_patch: Patch) -> None:
    """Test that individual fields are correctly extracted after packing."""
    payload = pack_payload(nes_patch)
    unpacked = unpack_payload(payload)
    assert unpacked.address == nes_patch.address
    assert unpacked.value == nes_patch.value
    assert unpacked.compare == nes_patch.compare
    assert unpacked.platform == nes_patch.platform
    assert unpacked.patch_type == nes_patch.patch_type
    assert unpacked.flags == nes_patch.flags


def test_bitpack_flags_extraction() -> None:
    """Test specific flag bit extraction."""
    patch = Patch(address=0, value=0, flags=Flags(wide_data=True, persistent=True))
    payload = pack_payload(patch)
    unpacked = unpack_payload(payload)
    assert unpacked.flags.wide_data is True
    assert unpacked.flags.persistent is True
    assert unpacked.flags.compare_enabled is False


def test_bitpack_pack_full_combines_correctly(nes_patch: Patch) -> None:
    """Verify pack_full combines payload and checksum correctly."""
    checksum = 0x3FF
    packed = pack_full(nes_patch, checksum)
    assert (packed & 0x7FF) == checksum
    payload = pack_payload(nes_patch)
    assert (packed >> 11) == payload


def test_bitpack_unpack_full_extracts_correctly(nes_patch: Patch) -> None:
    """Verify unpack_full separates payload and checksum correctly."""
    checksum = 0x3FF
    packed = pack_full(nes_patch, checksum)
    patch, extracted_checksum = unpack_full(packed)
    assert patch == nes_patch
    assert extracted_checksum == checksum


def test_bitpack_unpack_full_negative_raises() -> None:
    """Test that unpack_full raises OverflowError if integer is negative."""
    with pytest.raises(OverflowError):
        unpack_full(-1)
