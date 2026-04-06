"""Tests for the encoder module."""

import pytest

from gamegenie_x.encoder import encode
from gamegenie_x.models import Patch, Platform


def test_encoder_encode_known_patch(nes_patch: Patch) -> None:
    """Test encoding a valid NES patch."""
    code = encode(nes_patch)
    assert len(code) == 17  # 15 chars + 2 separators
    assert "-" in code


def test_encoder_encode_validation_bypass() -> None:
    """Test encoding with validation disabled allows out-of-bounds address."""
    patch = Patch(address=0xFFFFFFFF, value=0x00, platform=Platform.NES)
    code = encode(patch, validate=False)
    assert len(code) == 17


def test_encoder_encode_validation_failure_raises() -> None:
    """Test encoding with validation enabled raises ValueError for out-of-bounds address."""
    patch = Patch(address=0xFFFFFFFF, value=0x00, platform=Platform.NES)
    with pytest.raises(ValueError, match="Patch validation failed"):
        encode(patch, validate=True)


def test_encoder_encode_snes_patch(snes_patch: Patch) -> None:
    """Test encoding a valid SNES patch."""
    code = encode(snes_patch)
    assert len(code) == 17


def test_encoder_encode_genesis_patch(genesis_patch: Patch) -> None:
    """Test encoding a valid Genesis patch."""
    code = encode(genesis_patch)
    assert len(code) == 17


def test_encoder_encode_invalid_platform_raises() -> None:
    """Test encoding a patch for a platform with no profile raises ValueError."""
    patch = Patch(address=0, value=0, platform=Platform.UNIVERSAL)
    with pytest.raises(ValueError, match="Failed to load profile for validation"):
        encode(patch, validate=True)
