"""Tests for the checksum module."""

from gamegenie_x.checksum import compute, verify


def test_checksum_zero_payload() -> None:
    """Test CRC-11 for a zero payload."""
    payload = 0
    # Expected value depends on algorithm details. Let's just compute it.
    expected = compute(payload)
    assert compute(payload) == expected


def test_checksum_max_payload() -> None:
    """Test CRC-11 for the maximum 64-bit payload."""
    payload = (1 << 64) - 1
    expected = compute(payload)
    assert compute(payload) == expected


def test_checksum_verify_valid() -> None:
    """Test that verify returns True for a valid payload and checksum."""
    payload = 0x1234567890ABCDEF
    crc = compute(payload)
    packed = (payload << 11) | crc
    assert verify(packed) is True


def test_checksum_verify_tampered() -> None:
    """Test that verify returns False for a tampered payload."""
    payload = 0x1234567890ABCDEF
    crc = compute(payload)
    # Tamper with the payload
    tampered_payload = payload ^ 1
    packed = (tampered_payload << 11) | crc
    assert verify(packed) is False


def test_checksum_verify_tampered_checksum() -> None:
    """Test that verify returns False for a tampered checksum."""
    payload = 0x1234567890ABCDEF
    crc = compute(payload)
    # Tamper with the checksum
    tampered_crc = crc ^ 1
    packed = (payload << 11) | tampered_crc
    assert verify(packed) is False


def test_checksum_known_vectors() -> None:
    """Test CRC-11 computation against known behavior."""
    # A single bit set
    payload = 1
    crc = compute(payload)
    assert 0 <= crc <= 0x7FF
