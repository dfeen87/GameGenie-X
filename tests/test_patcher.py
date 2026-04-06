import json
import random
from pathlib import Path

import pytest

from gamegenie_x.models import Flags, Patch, PatchType, Platform
from gamegenie_x.patcher import apply_patch_to_file
from gamegenie_x.profiles import load_profile


@pytest.fixture
def dummy_save_file(tmp_path: Path) -> Path:
    save_path = tmp_path / "save.bin"
    # Create 10KB dummy save file
    save_path.write_bytes(bytearray([0] * 10240))
    return save_path

@pytest.fixture
def dummy_json_save(tmp_path: Path) -> Path:
    save_path = tmp_path / "save.json"
    data = {
        "player": {
            "currency": 100,
            "level": 5
        },
        "flags": {
            "unlocked": 0
        }
    }
    with open(save_path, "w") as f:
        json.dump(data, f)
    return save_path

def test_apply_patch_replace(dummy_save_file: Path) -> None:
    patch = Patch(
        address=0x1000, value=0x42, compare=0x00,
        platform=Platform.UNIVERSAL, patch_type=PatchType.REPLACE,
        flags=Flags(compare_enabled=True)
    )
    profile = load_profile("xboxone")

    # Should apply since current value is 0 (matches compare)
    result = apply_patch_to_file(patch, dummy_save_file, profile)
    assert result is True

    data = dummy_save_file.read_bytes()
    assert data[0x1000] == 0x42

def test_apply_patch_compare_fails(dummy_save_file: Path) -> None:
    patch = Patch(
        address=0x1000, value=0x42, compare=0x01,
        platform=Platform.UNIVERSAL, patch_type=PatchType.REPLACE,
        flags=Flags(compare_enabled=True)
    )
    profile = load_profile("ps5")

    # Should fail since current value is 0 (doesn't match compare=0x01)
    result = apply_patch_to_file(patch, dummy_save_file, profile)
    assert result is False

    data = dummy_save_file.read_bytes()
    assert data[0x1000] == 0x00

def test_apply_patch_increment(dummy_save_file: Path) -> None:
    # Setup initial value
    data = bytearray(dummy_save_file.read_bytes())
    data[0x2000] = 0x10
    dummy_save_file.write_bytes(data)

    patch = Patch(
        address=0x2000, value=0x05,
        platform=Platform.UNIVERSAL, patch_type=PatchType.INCREMENT
    )
    profile = load_profile("xboxseries")

    result = apply_patch_to_file(patch, dummy_save_file, profile)
    assert result is True

    data = dummy_save_file.read_bytes()
    assert data[0x2000] == 0x15

def test_apply_patch_out_of_bounds(dummy_save_file: Path) -> None:
    patch = Patch(
        address=0x50000, value=0xFF,
        platform=Platform.UNIVERSAL, patch_type=PatchType.REPLACE
    )
    profile = load_profile("ps4")

    with pytest.raises(ValueError, match="out of bounds"):
        apply_patch_to_file(patch, dummy_save_file, profile)

def test_apply_json_patch(dummy_json_save: Path) -> None:
    # Need to load a profile with JSON io strategy
    # "xboxone" strategy is "binary" but formats has json
    # Let's mock a profile or adjust the json file to match xboxone fields
    load_profile("xboxone")
    # Actually xboxone has io strategy "binary" so let's mock it
    from gamegenie_x.profiles import FieldDef, IOStrategy, PlatformProfile

    json_profile = PlatformProfile(
        platform="json_plat",
        name="JSON Plat",
        short_name="JSN",
        address_bits=32,
        max_address=0xFFFFFFFF,
        data_bits=8,
        compare_supported=True,
        default_patch_type=PatchType.REPLACE,
        default_flags=Flags(),
        io_strategy=IOStrategy(strategy="json", save_formats=["json"]),
        fields={
            "player.currency": FieldDef(offset=0x1000, type="int", description="Currency"),
            "player.level": FieldDef(offset=0x2000, type="int", description="Level")
        }
    )

    # Apply replace patch on currency
    patch1 = Patch(address=0x1000, value=0xFF, platform=Platform.UNIVERSAL)
    assert apply_patch_to_file(patch1, dummy_json_save, json_profile) is True

    with open(dummy_json_save) as f:
        data = json.load(f)
    assert data["player"]["currency"] == 0xFF

    # Apply increment patch on level
    patch2 = Patch(
        address=0x2000, value=0x01, patch_type=PatchType.INCREMENT, platform=Platform.UNIVERSAL
    )
    assert apply_patch_to_file(patch2, dummy_json_save, json_profile) is True

    with open(dummy_json_save) as f:
        data = json.load(f)
    assert data["player"]["level"] == 6

def test_apply_json_patch_compare_fail(dummy_json_save: Path) -> None:
    from gamegenie_x.profiles import FieldDef, IOStrategy, PlatformProfile

    json_profile = PlatformProfile(
        platform="json_plat",
        name="JSON Plat",
        short_name="JSN",
        address_bits=32,
        max_address=0xFFFFFFFF,
        data_bits=8,
        compare_supported=True,
        default_patch_type=PatchType.REPLACE,
        default_flags=Flags(),
        io_strategy=IOStrategy(strategy="json", save_formats=["json"]),
        fields={
            "player.currency": FieldDef(offset=0x1000, type="int", description="Currency")
        }
    )

    # Patch with compare that fails (current is 100, compare is 99)
    patch = Patch(
        address=0x1000,
        value=0xFF,
        compare=99,
        platform=Platform.UNIVERSAL,
        flags=Flags(compare_enabled=True),
    )
    assert apply_patch_to_file(patch, dummy_json_save, json_profile) is False

def test_fuzz_binary_patching(dummy_save_file: Path) -> None:
    """Fuzz file patching to ensure safe boundaries on file application."""
    random.seed(42)
    profile = load_profile("ps4")

    for _ in range(50):
        addr = random.randint(0, 10239)
        val = random.randint(0, 255)
        ptype = random.choice([
            PatchType.REPLACE, PatchType.INCREMENT, PatchType.DECREMENT,
            PatchType.XOR, PatchType.BITSET, PatchType.BITCLEAR,
        ])

        patch = Patch(address=addr, value=val, patch_type=ptype, platform=Platform.UNIVERSAL)

        # Read old
        data = bytearray(dummy_save_file.read_bytes())
        old_val = data[addr]

        # Apply
        apply_patch_to_file(patch, dummy_save_file, profile)

        # Verify
        new_data = dummy_save_file.read_bytes()
        new_val = new_data[addr]

        if ptype == PatchType.REPLACE:
            assert new_val == val
        elif ptype == PatchType.INCREMENT:
            assert new_val == (old_val + val) & 0xFF
        elif ptype == PatchType.DECREMENT:
            assert new_val == (old_val - val) & 0xFF
