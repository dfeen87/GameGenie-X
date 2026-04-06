"""Encode a Patch into a GameGenie-X code string."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gamegenie_x import alphabet, bitpack, checksum, profiles

if TYPE_CHECKING:
    from gamegenie_x.models import Patch


def encode(patch: Patch, *, validate: bool = True) -> str:
    """Encodes a Patch into a formatted GameGenie-X code string.

    Args:
        patch: The Patch object to encode.
        validate: Whether to validate the patch against its platform profile.

    Returns:
        The formatted 15-character GameGenie-X code string.

    Raises:
        ValueError: If validation fails or encoding encounters invalid data.
    """
    if validate:
        try:
            profile = profiles.load_profile(patch.platform)
        except (FileNotFoundError, ValueError) as e:
            raise ValueError(f"Failed to load profile for validation: {e}") from e

        errors = profiles.validate_patch(patch, profile)
        if errors:
            raise ValueError("Patch validation failed: " + "; ".join(errors))

    payload = bitpack.pack_payload(patch)
    crc = checksum.compute(payload)
    packed = bitpack.pack_full(patch, crc)
    raw_symbols = alphabet.encode_symbols(packed)
    return alphabet.format_code(raw_symbols)
