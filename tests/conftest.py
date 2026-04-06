"""Shared test fixtures for GameGenie-X."""

import pytest

from gamegenie_x.models import Flags, Patch, PatchType, Platform


@pytest.fixture
def nes_patch() -> Patch:
    """Standard NES test patch."""
    return Patch(address=0x7E00, value=0x09, compare=0x03,
                 platform=Platform.NES, patch_type=PatchType.REPLACE,
                 flags=Flags(compare_enabled=True))

@pytest.fixture
def snes_patch() -> Patch:
    """Standard SNES test patch."""
    return Patch(address=0xC0FFEE, value=0x42,
                 platform=Platform.SNES, patch_type=PatchType.REPLACE)

@pytest.fixture
def genesis_patch() -> Patch:
    """Standard Genesis test patch."""
    return Patch(address=0xFF0000, value=0x63,
                 platform=Platform.GENESIS, patch_type=PatchType.REPLACE)


@pytest.fixture
def nds_patch() -> Patch:
    """Standard NDS test patch."""
    return Patch(address=0x02000000, value=0xFF, compare=0x00,
                 platform=Platform.NDS, patch_type=PatchType.REPLACE)

@pytest.fixture
def n3ds_patch() -> Patch:
    """Standard 3DS test patch."""
    return Patch(address=0x10000000, value=0x42, compare=0x01,
                 platform=Platform.N3DS, patch_type=PatchType.REPLACE)

@pytest.fixture
def psp_patch() -> Patch:
    """Standard PSP test patch."""
    return Patch(address=0x08800000, value=0x99,
                 platform=Platform.PSP, patch_type=PatchType.REPLACE)

@pytest.fixture
def psvita_patch() -> Patch:
    """Standard PS Vita test patch."""
    return Patch(address=0x81000000, value=0x77,
                 platform=Platform.PSVITA, patch_type=PatchType.REPLACE)

@pytest.fixture
def switch_patch() -> Patch:
    """Standard Switch test patch."""
    return Patch(address=0x10000000, value=0xAA,
                 platform=Platform.SWITCH, patch_type=PatchType.REPLACE)

@pytest.fixture
def dolphin_patch() -> Patch:
    """Standard Dolphin test patch."""
    return Patch(address=0x80000000, value=0x55,
                 platform=Platform.DOLPHIN, patch_type=PatchType.REPLACE)

@pytest.fixture
def citra_patch() -> Patch:
    """Standard Citra test patch."""
    return Patch(address=0x14000000, value=0x33,
                 platform=Platform.CITRA, patch_type=PatchType.REPLACE)

@pytest.fixture
def rpcs3_patch() -> Patch:
    """Standard RPCS3 test patch."""
    return Patch(address=0x20000000, value=0x22,
                 platform=Platform.RPCS3, patch_type=PatchType.REPLACE)

@pytest.fixture
def yuzu_patch() -> Patch:
    """Standard Yuzu test patch."""
    return Patch(address=0x30000000, value=0x11,
                 platform=Platform.YUZU, patch_type=PatchType.REPLACE)

@pytest.fixture
def pc_patch() -> Patch:
    """Standard PC test patch."""
    return Patch(address=0x00000000, value=0x01,
                 platform=Platform.PC, patch_type=PatchType.REPLACE)
