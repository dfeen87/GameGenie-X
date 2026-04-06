"""Decode a GameGenie-X code string into a Patch."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gamegenie_x import alphabet, bitpack, checksum

if TYPE_CHECKING:
    from gamegenie_x.models import Patch


class ChecksumError(ValueError):
    """Raised when the CRC-11 checksum verification fails."""


def decode(code: str, *, verify: bool = True) -> Patch:
    """Decodes a GameGenie-X code string into a Patch object.

    Args:
        code: The GameGenie-X code string.
        verify: Whether to verify the integrity of the code using its checksum.

    Returns:
        The decoded Patch object.

    Raises:
        ChecksumError: If verification is enabled and the checksum is invalid.
        ValueError: If the code format or characters are invalid.
    """
    stripped = alphabet.strip_code(code)
    packed = alphabet.decode_symbols(stripped)
    patch, crc = bitpack.unpack_full(packed)

    if verify and not checksum.verify(packed):
        raise ChecksumError("Checksum verification failed.")

    return patch
