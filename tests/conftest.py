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
