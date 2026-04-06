"""Tests for the alphabet module."""

import pytest

from gamegenie_x.alphabet import (
    ALPHABET,
    decode_symbols,
    encode_symbols,
    format_code,
    strip_code,
)


def test_alphabet_length_is_32() -> None:
    """Ensure the alphabet has exactly 32 distinct symbols."""
    assert len(ALPHABET) == 32
    assert len(set(ALPHABET)) == 32


@pytest.mark.parametrize(
    "char,expected",
    [
        ("0", 0),
        ("1", 1),
        ("9", 9),
        ("A", 10),
        ("B", 11),
        ("Z", 31),
    ],
)
def test_alphabet_char_to_value_mapping(char: str, expected: int) -> None:
    """Verify specific character mappings against expected values."""
    from gamegenie_x.alphabet import CHAR_TO_VALUE
    assert CHAR_TO_VALUE[char] == expected


def test_alphabet_encode_decode_roundtrip() -> None:
    """Test that a random 75-bit integer can be encoded and decoded successfully."""
    # Example 75-bit integer
    packed = (1 << 75) - 1
    encoded = encode_symbols(packed)
    decoded = decode_symbols(encoded)
    assert decoded == packed


def test_alphabet_encode_out_of_bounds_raises() -> None:
    """Test that encoding an integer >= 2^75 raises ValueError."""
    with pytest.raises(ValueError):
        encode_symbols(1 << 75)
    with pytest.raises(ValueError):
        encode_symbols(-1)


def test_alphabet_decode_invalid_char_raises() -> None:
    """Test that decoding a code with invalid characters raises ValueError."""
    with pytest.raises(ValueError, match="Invalid character"):
        decode_symbols("A" * 14 + "I")  # 'I' is not in ALPHABET


def test_alphabet_decode_wrong_length_raises() -> None:
    """Test that decoding a code with incorrect length raises ValueError."""
    with pytest.raises(ValueError, match="Code must be exactly 15 valid chars"):
        decode_symbols("A" * 14)


def test_alphabet_strip_code_removes_separators_and_uppercases() -> None:
    """Test that strip_code normalizes the string correctly."""
    assert strip_code("aBcDe-fGhJk-mNpQr ") == "ABCDEFGHJKMNPQR"


def test_alphabet_format_code_inserts_separators() -> None:
    """Test that format_code correctly inserts separators into a raw code."""
    raw = "ABCDEFGHJKMNPQR"
    assert format_code(raw) == "ABCDE-FGHJK-MNPQR"
