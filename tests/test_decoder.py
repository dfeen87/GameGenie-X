"""Tests for the decoder module."""

import pytest

from gamegenie_x.decoder import ChecksumError, decode
from gamegenie_x.encoder import encode
from gamegenie_x.models import Patch


def test_decoder_decode_known_code(nes_patch: Patch) -> None:
    """Test decoding a known valid code string."""
    code = encode(nes_patch)
    decoded = decode(code)
    assert decoded == nes_patch


def test_decoder_checksum_failure_raises(nes_patch: Patch) -> None:
    """Test that decoding a tampered code string raises ChecksumError."""
    code = encode(nes_patch)
    # Tamper with the code by replacing the first character with a different valid one
    chars = list(code)
    chars[0] = "A" if chars[0] != "A" else "B"
    tampered_code = "".join(chars)

    with pytest.raises(ChecksumError):
        decode(tampered_code, verify=True)


def test_decoder_decode_invalid_format_raises() -> None:
    """Test that decoding a malformed code string raises ValueError."""
    with pytest.raises(ValueError):
        decode("INVALID-FORMAT")


def test_decoder_decode_without_verification(nes_patch: Patch) -> None:
    """Test decoding a tampered code string without checksum verification."""
    code = encode(nes_patch)
    chars = list(code)
    chars[0] = "A" if chars[0] != "A" else "B"
    tampered_code = "".join(chars)

    # Should not raise ChecksumError
    patch = decode(tampered_code, verify=False)
    # The patch won't match nes_patch due to tampering, but it should decode
    assert patch != nes_patch


def test_decoder_decode_case_insensitive(nes_patch: Patch) -> None:
    """Test that decoding is case insensitive."""
    code = encode(nes_patch)
    decoded = decode(code.lower())
    assert decoded == nes_patch


def test_decoder_decode_ignores_whitespace(nes_patch: Patch) -> None:
    """Test that decoding ignores extra whitespace."""
    code = encode(nes_patch)
    spaced_code = f"  {code[:5]}   {code[5:11]}  {code[11:]} "
    decoded = decode(spaced_code)
    assert decoded == nes_patch
