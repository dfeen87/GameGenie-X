import pytest
from gamegenie_x.models import Patch

def test_nds_patch_fixture(nds_patch: Patch) -> None:
    assert nds_patch.address == 0x02000000
    assert nds_patch.value == 0xFF
    assert nds_patch.compare == 0x00

def test_n3ds_patch_fixture(n3ds_patch: Patch) -> None:
    assert n3ds_patch.address == 0x10000000

def test_psp_patch_fixture(psp_patch: Patch) -> None:
    assert psp_patch.address == 0x08800000

def test_psvita_patch_fixture(psvita_patch: Patch) -> None:
    assert psvita_patch.address == 0x81000000

def test_switch_patch_fixture(switch_patch: Patch) -> None:
    assert switch_patch.address == 0x10000000

def test_dolphin_patch_fixture(dolphin_patch: Patch) -> None:
    assert dolphin_patch.address == 0x80000000

def test_citra_patch_fixture(citra_patch: Patch) -> None:
    assert citra_patch.address == 0x14000000

def test_rpcs3_patch_fixture(rpcs3_patch: Patch) -> None:
    assert rpcs3_patch.address == 0x20000000

def test_yuzu_patch_fixture(yuzu_patch: Patch) -> None:
    assert yuzu_patch.address == 0x30000000

def test_pc_patch_fixture(pc_patch: Patch) -> None:
    assert pc_patch.address == 0x00000000
