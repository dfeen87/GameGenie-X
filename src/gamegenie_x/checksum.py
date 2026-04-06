"""CRC-11 checksum for GameGenie-X code integrity.

The CRC-11 algorithm detects transmission and transcription errors.
Polynomial: x^11 + x^8 + x^6 + x^5 + x^4 + 1
"""

from __future__ import annotations

# CRC-11 polynomial: x^11 + x^8 + x^6 + x^5 + x^4 + 1
CRC_POLY: int = 0x571
CRC_INIT: int = 0x7FF       # All 1s initialization
CRC_WIDTH: int = 11
CRC_MASK: int = (1 << CRC_WIDTH) - 1  # 0x7FF


def compute(payload: int) -> int:
    """Takes the 64-bit payload, computes CRC-11.

    Uses bitwise polynomial division with CRC_POLY and CRC_INIT.
    Processes the 64-bit payload from MSB to LSB, one bit at a time.

    Args:
        payload: The 64-bit integer payload.

    Returns:
        The 11-bit CRC checksum.
    """
    crc = CRC_INIT
    # Process the 64-bit payload from MSB (bit 63) to LSB (bit 0)
    for i in range(63, -1, -1):
        bit = (payload >> i) & 1
        # Shift left by 1 and OR in the current bit
        crc = (crc << 1) | bit

        # If the shifted-out bit (bit 11) is 1, XOR with the polynomial
        if crc & (1 << CRC_WIDTH):
            crc ^= CRC_POLY

    # After processing all 64 bits, mask crc to 11 bits
    return crc & CRC_MASK


def verify(packed: int) -> bool:
    """Takes a full 75-bit integer, extracts payload and checksum, recomputes CRC, and compares.

    Args:
        packed: The full 75-bit integer.

    Returns:
        True if the embedded checksum matches the computed CRC-11 of the payload.
    """
    checksum = packed & CRC_MASK
    payload = packed >> CRC_WIDTH
    computed = compute(payload)
    return computed == checksum
