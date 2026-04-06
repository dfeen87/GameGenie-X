"""Pack and unpack Patch objects to/from 75-bit integers."""

from __future__ import annotations

from gamegenie_x.models import Flags, Patch, PatchType, Platform

TOTAL_BITS: int = 75
PAYLOAD_BITS: int = 64  # bits 74–11 (everything except checksum)
CHECKSUM_BITS: int = 11  # bits 10–0

# Field widths and shifts (MSB-first packing)
FIELD_SPECS: dict[str, tuple[int, int]] = {
    # field_name: (width, shift_from_bit_0)
    "address":    (32, 43),
    "value":      (8,  35),
    "compare":    (8,  27),
    "platform":   (4,  23),
    "patch_type": (4,  19),
    "flags":      (8,  11),
    "checksum":   (11, 0),
}


def pack_payload(patch: Patch) -> int:
    """Packs a Patch object into a 64-bit payload integer.

    Does NOT include checksum. The returned integer represents the upper 64 bits
    of the final 75-bit code, shifted down to start at bit 0 (i.e. bits 63-0).

    Args:
        patch: The Patch object to pack.

    Returns:
        The 64-bit payload integer.
    """
    payload = 0
    # The payload excludes the 11-bit checksum, so we shift down by 11.
    payload |= (patch.address & ((1 << 32) - 1)) << (FIELD_SPECS["address"][1] - 11)
    payload |= (patch.value & ((1 << 8) - 1)) << (FIELD_SPECS["value"][1] - 11)
    payload |= (patch.compare & ((1 << 8) - 1)) << (FIELD_SPECS["compare"][1] - 11)
    payload |= (patch.platform & ((1 << 4) - 1)) << (FIELD_SPECS["platform"][1] - 11)
    payload |= (patch.patch_type & ((1 << 4) - 1)) << (FIELD_SPECS["patch_type"][1] - 11)
    payload |= (patch.flags.to_byte() & ((1 << 8) - 1)) << (FIELD_SPECS["flags"][1] - 11)
    return payload


def unpack_payload(payload: int) -> Patch:
    """Reverses pack_payload. Extracts fields from the 64-bit payload.

    Args:
        payload: The 64-bit payload integer.

    Returns:
        The unpacked Patch object.
    """
    address = (payload >> (FIELD_SPECS["address"][1] - 11)) & ((1 << 32) - 1)
    value = (payload >> (FIELD_SPECS["value"][1] - 11)) & ((1 << 8) - 1)
    compare = (payload >> (FIELD_SPECS["compare"][1] - 11)) & ((1 << 8) - 1)
    platform_val = (payload >> (FIELD_SPECS["platform"][1] - 11)) & ((1 << 4) - 1)
    patch_type_val = (payload >> (FIELD_SPECS["patch_type"][1] - 11)) & ((1 << 4) - 1)
    flags_val = (payload >> (FIELD_SPECS["flags"][1] - 11)) & ((1 << 8) - 1)

    return Patch(
        address=address,
        value=value,
        compare=compare,
        platform=Platform(platform_val),
        patch_type=PatchType(patch_type_val),
        flags=Flags.from_byte(flags_val),
    )


def pack_full(patch: Patch, checksum: int) -> int:
    """Combines the 64-bit payload with the 11-bit checksum.

    Args:
        patch: The Patch object to pack.
        checksum: The 11-bit checksum.

    Returns:
        The final 75-bit integer.

    Raises:
        OverflowError: If the resulting integer doesn't fit in 75 bits.
    """
    payload = pack_payload(patch)
    packed = (payload << 11) | (checksum & ((1 << 11) - 1))
    if packed >= (1 << TOTAL_BITS) or packed < 0:
        raise OverflowError("Packed integer exceeds 75 bits.")
    return packed


def unpack_full(packed: int) -> tuple[Patch, int]:
    """Extracts the Patch and the 11-bit checksum from a 75-bit integer.

    Args:
        packed: The 75-bit integer.

    Returns:
        A tuple containing the Patch object and the 11-bit checksum.

    Raises:
        OverflowError: If the integer is too large for 75 bits.
    """
    if packed >= (1 << TOTAL_BITS) or packed < 0:
        raise OverflowError("Packed integer exceeds 75 bits.")

    checksum = packed & ((1 << 11) - 1)
    payload = packed >> 11
    patch = unpack_payload(payload)
    return patch, checksum
