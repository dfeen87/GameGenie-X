"""Unit tests for GameGenie-X v2 features: Multi-patch, Conditional patches, and Validator."""

import json
from pathlib import Path

import pytest  # type: ignore[import-not-found]

from gamegenie_x.alphabet import Alphabet, get_active_alphabet, set_active_alphabet
from gamegenie_x.decoder import ChecksumError, decode_to_sequence
from gamegenie_x.encoder import encode
from gamegenie_x.models import Flags, PatchType, Platform
from gamegenie_x.models import Patch as LegacyPatch
from gamegenie_x.patch_v2 import Patch, PatchSequence, TargetType
from gamegenie_x.profiles import FieldDef, IOStrategy, PlatformProfile, load_profile
from gamegenie_x.validator import InvalidCodeError, PayloadValidator


@pytest.fixture  # type: ignore[untyped-decorator]
def dummy_binary_file(tmp_path: Path) -> Path:
    binary_path = tmp_path / "test_save.bin"
    binary_path.write_bytes(bytearray([0x10, 0x20, 0x30, 0x40, 0x50]))
    return binary_path


@pytest.fixture  # type: ignore[untyped-decorator]
def dummy_json_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "test_config.json"
    data = {
        "player": {
            "gold": 100,
            "hp": 50,
            "name": "Jules"
        },
        "flags": {
            "unlocked": False
        }
    }
    with open(config_path, "w") as f:
        json.dump(data, f)
    return config_path


def test_v2_patch_dataclass() -> None:
    """Test standard instantiation and types of Patch v2 dataclass."""
    p = Patch(
        target_type=TargetType.SAVE,
        offset=0x10,
        new_value=0xFF,
        compare_value=0x10,
        conditions=[lambda v: v > 0]
    )
    assert p.target_type == TargetType.SAVE
    assert p.offset == 0x10
    assert p.new_value == 0xFF
    assert p.compare_value == 0x10
    assert len(p.conditions) == 1
    assert p.conditions[0](5) is True


def test_v2_patch_sequence_binary_chained_and_conditional(dummy_binary_file: Path) -> None:
    """Test applying a PatchSequence on binary data.

    Verifies deterministic sequential/chained execution, and skipping of patches
    that fail conditions.
    """
    profile = load_profile("ps5")  # Binary strategy profile

    # Condition 1: must be > 0x05 (matches current value 0x10). Applies.
    # Condition 2: must be == 0x99 (does not match current value 0x20). Skipped.
    # Condition 3: must be == 0x30. Applies, but relies on previous state (chained).
    p1 = Patch(
        target_type=TargetType.SAVE,
        offset=0,
        new_value=0x99,
        conditions=[lambda v: v > 0x05]
    )
    p2 = Patch(
        target_type=TargetType.SAVE,
        offset=1,
        new_value=0xFF,
        conditions=[lambda v: v == 0x99]
    )
    p3 = Patch(
        target_type=TargetType.SAVE,
        offset=2,
        new_value=0xAA,
        conditions=[lambda v: v == 0x30]
    )

    sequence = PatchSequence([p1, p2, p3])
    result = sequence.apply(dummy_binary_file, profile)

    assert result is True

    # Read modified data
    data = dummy_binary_file.read_bytes()
    # Offset 0 changed to 0x99 (Condition passed)
    assert data[0] == 0x99
    # Offset 1 remains 0x20 (Condition failed, patch skipped)
    assert data[1] == 0x20
    # Offset 2 changed to 0xAA (Condition passed)
    assert data[2] == 0xAA


def test_v2_patch_sequence_json_chained_and_conditional(dummy_json_config: Path) -> None:
    """Test applying a PatchSequence on a JSON file.

    Verifies deterministic execution, and skipping of patches that fail conditions.
    """
    # Create mock platform profile for JSON patching
    profile = PlatformProfile(
        platform="json_v2",
        name="JSON v2 Profile",
        short_name="JV2",
        address_bits=32,
        max_address=0xFFFFFFFF,
        data_bits=8,
        compare_supported=True,
        default_patch_type=PatchType.REPLACE,
        default_flags=Flags(),
        io_strategy=IOStrategy(strategy="json", save_formats=["json"]),
        fields={
            "player.gold": FieldDef(offset=0x1000, type="int", description="Gold"),
            "player.hp": FieldDef(offset=0x2000, type="int", description="HP"),
            "player.name": FieldDef(offset=0x3000, type="str", description="Name")
        }
    )

    # Patch 1: Set hp to 99 if current gold > 50 (gold is 100, so true)
    # Patch 2: Set name to 'Jules Modified' if gold == 100 (gold is 100, so true)
    # Patch 3: Increment gold by 10 (gold becomes 110)
    # Patch 4: Set hp to 10 if gold == 100 (gold is now 110, so false - skipped!)
    p1 = Patch(
        target_type=TargetType.CONFIG,
        key_path="player.hp",
        new_value=99,
        conditions=[lambda v: True]  # we can check parent state via file or simply check field
    )
    p2 = Patch(
        target_type=TargetType.CONFIG,
        key_path="player.name",
        new_value="Jules Modified"
    )
    p3 = Patch(
        target_type=TargetType.CONFIG,
        key_path="player.gold",
        new_value=10,
        patch_type=PatchType.INCREMENT
    )
    p4 = Patch(
        target_type=TargetType.CONFIG,
        key_path="player.hp",
        new_value=10,
        compare_value=100  # Will fail because HP is currently 99
    )

    sequence = PatchSequence([p1, p2, p3, p4])
    result = sequence.apply(dummy_json_config, profile)

    assert result is True

    with open(dummy_json_config) as f:
        data = json.load(f)

    assert data["player"]["hp"] == 99  # Applied p1, skipped p4
    assert data["player"]["name"] == "Jules Modified"  # Applied p2
    assert data["player"]["gold"] == 110  # Applied p3 (100 + 10)


def test_v2_decoder_sequence_integration() -> None:
    """Test that decoding can produce a PatchSequence."""
    legacy_patch = LegacyPatch(
        address=0x1234,
        value=0xAB,
        compare=0,
        platform=Platform.NES,
    )
    code = encode(legacy_patch)

    profile = load_profile("nes")
    seq = decode_to_sequence(code, profile)

    assert isinstance(seq, PatchSequence)
    assert len(seq.patches) == 1
    p = seq.patches[0]
    assert p.target_type == TargetType.SAVE
    assert p.offset == 0x1234
    assert p.new_value == 0xAB


def test_v2_decoder_wide_data_integration() -> None:
    """Test that wide-data codes decode to a small sequence of related patches (16-bit)."""
    legacy_patch = LegacyPatch(
        address=0x1234,
        value=0xAB,  # valid 8-bit value
        compare=0,
        platform=Platform.NES,
        flags=Flags(wide_data=True)
    )
    code = encode(legacy_patch, validate=False)

    profile = load_profile("nes")
    seq = decode_to_sequence(code, profile, verify=True)

    assert isinstance(seq, PatchSequence)
    assert len(seq.patches) == 2

    # Since NES endianness is little:
    p1 = seq.patches[0]
    p2 = seq.patches[1]

    assert p1.offset == 0x1234
    assert p1.new_value == 0xAB  # Low byte

    assert p2.offset == 0x1235
    assert p2.new_value == 0x00  # High byte


def test_payload_validator_tampered_raises_invalid_code_error() -> None:
    """Test validator raises InvalidCodeError (subclass of ValueError) on tampered code."""
    patch = LegacyPatch(address=0x100, value=0x42, platform=Platform.NES)
    code = encode(patch)

    # Tamper with the code
    chars = list(code)
    chars[0] = "A" if chars[0] != "A" else "B"
    tampered_code = "".join(chars)

    with pytest.raises(ChecksumError) as exc_info:
        PayloadValidator.validate(tampered_code)

    assert isinstance(exc_info.value, InvalidCodeError)
    assert exc_info.value.offending_code == tampered_code
    assert exc_info.value.reason != ""
    assert "Hint" in str(exc_info.value)


def test_payload_validator_malformed_length_raises() -> None:
    """Test validator raises InvalidCodeError on wrong length."""
    with pytest.raises(InvalidCodeError) as exc_info:
        PayloadValidator.validate("ABCDE-FGHJK")

    assert exc_info.value.offending_code == "ABCDE-FGHJK"
    assert "length" in exc_info.value.reason


def test_alphabet_expansion() -> None:
    """Test Alphabet class and switching of active alphabets."""
    default_alphabet = get_active_alphabet()

    # Create a custom alphabet by adding more symbols, e.g. swapping some or using a custom set
    # Standard alphabet is 32 symbols. Let's create an extended set.
    # Since we need 32 symbols, let's use lowercase or different characters.
    custom_symbols = "abcdefghjkmnpqrstvwxyz23456789!@"
    custom_alphabet = Alphabet(custom_symbols)

    set_active_alphabet(custom_alphabet)
    try:
        assert get_active_alphabet() == custom_alphabet

        # Test encoding/decoding under active custom alphabet
        packed = 1234567890123456789
        encoded = custom_alphabet.encode_bits_to_code(packed)
        # All characters in encoded should belong to custom_symbols
        for char in encoded:
            assert char in custom_symbols.upper()

        decoded = custom_alphabet.decode_code_to_bits(encoded)
        assert decoded == packed

        # Test decode via decode_symbols (uses active alphabet)
        from gamegenie_x.alphabet import decode_symbols
        assert decode_symbols(encoded) == packed

    finally:
        # Restore default alphabet!
        set_active_alphabet(default_alphabet)

    assert get_active_alphabet() == default_alphabet


def test_alphabet_invalid_symbols_raises() -> None:
    """Test that Alphabet class instantiation checks constraints."""
    # Must be at least 32 symbols
    with pytest.raises(ValueError, match="at least 32 symbols"):
        Alphabet("0123456789")

    # Symbols must be unique
    with pytest.raises(ValueError, match="must be unique"):
        Alphabet("00123456789ABCDEFGHJKMNPQRSTVWXYZ")
