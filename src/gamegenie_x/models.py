"""Core data models for GameGenie-X patch encoding."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class Platform(enum.IntEnum):
    """Supported platform identifiers (4-bit, 0–15)."""
    NES       = 0x0
    SNES      = 0x1
    GENESIS   = 0x2
    GAMEBOY   = 0x3
    GAMEGEAR  = 0x4
    NDS       = 0x5
    N3DS      = 0x6
    PSP       = 0x7
    PSVITA    = 0x8
    SWITCH    = 0x9
    DOLPHIN   = 0xA
    CITRA     = 0xB
    RPCS3     = 0xC
    YUZU      = 0xD
    PC        = 0xE
    UNIVERSAL = 0xF


class PatchType(enum.IntEnum):
    """Patch operation type (4-bit, 0–15)."""
    REPLACE   = 0x0  # Replace byte at address with value
    INCREMENT = 0x1  # Add value to byte at address
    DECREMENT = 0x2  # Subtract value from byte at address
    BITSET    = 0x3  # OR value into byte at address
    BITCLEAR  = 0x4  # AND ~value into byte at address
    XOR       = 0x5  # XOR value into byte at address
    # 0x6–0xF reserved for future types


@dataclass(frozen=True, slots=True)
class Flags:
    """Decoded flags byte."""
    compare_enabled: bool = False
    wide_data: bool = False
    read_only: bool = False
    persistent: bool = False
    reserved: int = 0  # Must be 0 for v1.0.0

    def to_byte(self) -> int:
        """Packs the flags into an 8-bit integer."""
        return (
            (int(self.compare_enabled) << 7)
            | (int(self.wide_data) << 6)
            | (int(self.read_only) << 5)
            | (int(self.persistent) << 4)
            | (self.reserved & 0x0F)
        )

    @classmethod
    def from_byte(cls, byte: int) -> Flags:
        """Unpacks an 8-bit integer into a Flags object."""
        return cls(
            compare_enabled=bool(byte & 0x80),
            wide_data=bool(byte & 0x40),
            read_only=bool(byte & 0x20),
            persistent=bool(byte & 0x10),
            reserved=byte & 0x0F,
        )


@dataclass(frozen=True, slots=True)
class Patch:
    """A single GameGenie-X patch descriptor."""
    address: int       # 0x00000000–0xFFFFFFFF (32-bit)
    value: int         # 0x00–0xFF (8-bit)
    compare: int = 0   # 0x00–0xFF (8-bit), 0 if unused
    platform: Platform = Platform.NES
    patch_type: PatchType = PatchType.REPLACE
    flags: Flags = field(default_factory=Flags)

    def __post_init__(self) -> None:
        """Validate all fields are within their bit-width ranges."""
        if not (0 <= self.address <= 0xFFFFFFFF):
            raise ValueError(f"Address {self.address} out of 32-bit range.")
        if not (0 <= self.value <= 0xFF):
            raise ValueError(f"Value {self.value} out of 8-bit range.")
        if not (0 <= self.compare <= 0xFF):
            raise ValueError(f"Compare value {self.compare} out of 8-bit range.")
        if not (0 <= self.platform <= 0xF):
            raise ValueError(f"Platform {self.platform} out of 4-bit range.")
        if not (0 <= self.patch_type <= 0xF):
            raise ValueError(f"Patch type {self.patch_type} out of 4-bit range.")
        if not (0 <= self.flags.reserved <= 0xF):
            raise ValueError(f"Flags reserved bits {self.flags.reserved} out of 4-bit range.")
