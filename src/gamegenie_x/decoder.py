"""Decode a GameGenie-X code string into a Patch."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gamegenie_x import alphabet, bitpack
from gamegenie_x.validator import InvalidCodeError, PayloadValidator

if TYPE_CHECKING:
    from gamegenie_x.models import Patch
    from gamegenie_x.patch_v2 import PatchSequence
    from gamegenie_x.profiles import PlatformProfile


class ChecksumError(InvalidCodeError):
    """Raised when the CRC-11 checksum verification fails."""


def decode(code: str, *, verify: bool = True) -> Patch:
    """Decodes a GameGenie-X code string into a Patch object.

    Args:
        code: The GameGenie-X code string.
        verify: Whether to verify the integrity of the code using its checksum.

    Returns:
        The decoded Patch object.

    Raises:
        InvalidCodeError: If verification is enabled and the checksum or code is invalid.
    """
    # 1. Run validation before any Patch object is created.
    # If validation or checksum verification fails, an InvalidCodeError/ChecksumError is raised.
    PayloadValidator.validate(code, verify=verify)

    # 2. Once validated, decode and unpack safely.
    stripped = alphabet.strip_code(code)
    packed = alphabet.decode_symbols(stripped)
    patch, _ = bitpack.unpack_full(packed)

    return patch


def decode_to_sequence(
    code: str, profile: PlatformProfile, *, verify: bool = True
) -> PatchSequence:
    """Decodes a GameGenie-X code string directly into a PatchSequence.

    Args:
        code: The GameGenie-X code string.
        profile: The PlatformProfile for target specific mappings.
        verify: Whether to verify the integrity of the code using its checksum.

    Returns:
        The decoded PatchSequence object.

    Raises:
        InvalidCodeError: If verification is enabled and the checksum or code is invalid.
    """
    from gamegenie_x.patch_v2 import from_legacy_patch

    patch = decode(code, verify=verify)
    return from_legacy_patch(patch, profile)
