import pytest
import random
from gamegenie_x.models import Patch, Platform, Flags, PatchType
from gamegenie_x.encoder import encode
from gamegenie_x.decoder import decode

# Fuzz tests for modern platforms
MODERN_PLATFORMS = [
    Platform.NDS, Platform.N3DS, Platform.PSP, Platform.PSVITA,
    Platform.SWITCH, Platform.DOLPHIN, Platform.CITRA,
    Platform.RPCS3, Platform.YUZU, Platform.PC
]

@pytest.mark.parametrize("platform", MODERN_PLATFORMS)
def test_boundary_max_values_modern_platforms(platform: Platform) -> None:
    """Test boundary condition: maximum possible values for address, value, compare."""
    patch = Patch(
        address=0xFFFFFFFF,
        value=0xFF,
        compare=0xFF,
        platform=platform,
        patch_type=PatchType.XOR,
        flags=Flags(compare_enabled=True, wide_data=True, read_only=True, persistent=True)
    )
    code = encode(patch, validate=False)
    decoded = decode(code)
    assert decoded == patch

@pytest.mark.parametrize("platform", MODERN_PLATFORMS)
def test_boundary_zero_values_modern_platforms(platform: Platform) -> None:
    """Test boundary condition: zero values for address, value, compare."""
    patch = Patch(
        address=0x00000000,
        value=0x00,
        compare=0x00,
        platform=platform,
        patch_type=PatchType.REPLACE,
        flags=Flags()
    )
    code = encode(patch, validate=False)
    decoded = decode(code)
    assert decoded == patch

@pytest.mark.parametrize("platform", MODERN_PLATFORMS)
def test_fuzz_random_patches(platform: Platform) -> None:
    """Fuzz test with 10 random valid patches per platform."""
    random.seed(int(platform.value)) # deterministic fuzzing
    for _ in range(10):
        address = random.randint(0, 0xFFFFFFFF)
        value = random.randint(0, 0xFF)
        compare = random.randint(0, 0xFF)
        patch_type = random.choice(list(PatchType)[:6])
        flags = Flags(
            compare_enabled=random.choice([True, False]),
            wide_data=random.choice([True, False]),
            read_only=random.choice([True, False]),
            persistent=random.choice([True, False])
        )
        patch = Patch(
            address=address,
            value=value,
            compare=compare,
            platform=platform,
            patch_type=patch_type,
            flags=flags
        )
        code = encode(patch, validate=False)
        decoded = decode(code)
        assert decoded == patch
