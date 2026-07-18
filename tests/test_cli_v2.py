"""Unit tests for the CLI v2 and Interactive Shell (Module C)."""

import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from gamegenie_x.cli import main, handle_decode, handle_preview, handle_apply, handle_sandbox, get_parser
from gamegenie_x.encoder import encode
from gamegenie_x.models import Patch as LegacyPatch, Platform, Flags


@pytest.fixture
def dummy_binary_file(tmp_path: Path) -> Path:
    p = tmp_path / "save.bin"
    p.write_bytes(bytearray([0x10, 0x20, 0x30, 0x40, 0x50] + [0] * 150))
    return p


@pytest.fixture
def dummy_profile_file(tmp_path: Path) -> Path:
    p = tmp_path / "profile.json"
    profile_data = {
        "game_id": "cli_game",
        "display_name": "CLI Game Profile",
        "save_structure": {
            "hp": 1,
            "gold": 4
        },
        "value_ranges": {
            "hp": (0, 255),
            "gold": (0, 100)
        },
        "flags": {
            "gold_unsafe": True
        },
        "signature": [0x10, 0x20, 0x30],
        "format": "binary"
    }
    p.write_text(json.dumps(profile_data), encoding="utf-8")
    return p


def test_cli_decode_command(capsys: pytest.CaptureFixture[str]) -> None:
    # Encode a simple patch
    legacy = LegacyPatch(address=0x10, value=0xAB, platform=Platform.NES)
    code = encode(legacy)

    # Run handle_decode
    handle_decode(code)

    captured = capsys.readouterr()
    assert "=== Code Explanation Output ===" in captured.out
    assert f"Code String:        {code}" in captured.out
    assert "Checksum Validity:  VALID" in captured.out
    assert "Address:          0x00000010" in captured.out
    assert "Value:            0xAB" in captured.out


def test_cli_apply_command(dummy_binary_file: Path, dummy_profile_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Address 1 is HP. Set HP to 99.
    legacy = LegacyPatch(address=1, value=99, platform=Platform.UNIVERSAL)
    code = encode(legacy, validate=False)

    # Apply with profile
    handle_apply(code, str(dummy_binary_file), profile_path=str(dummy_profile_file))

    captured = capsys.readouterr()
    assert "Successfully applied patches" in captured.out or "Error" in captured.err

    # Verify state modification
    data = dummy_binary_file.read_bytes()
    assert data[1] == 99


def test_cli_apply_safety_violation(dummy_binary_file: Path, dummy_profile_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Address 4 is gold (marked gold_unsafe=True). Set gold to 50.
    legacy = LegacyPatch(address=4, value=50, platform=Platform.UNIVERSAL)
    code = encode(legacy, validate=False)

    handle_apply(code, str(dummy_binary_file), profile_path=str(dummy_profile_file), safe_mode=True)

    captured = capsys.readouterr()
    assert "Forbidden field access" in captured.out or "Forbidden field access" in captured.err


def test_cli_preview_command(dummy_binary_file: Path, dummy_profile_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Address 1 is HP. Set HP to 150. Compare with 0x20 (matches!).
    legacy = LegacyPatch(
        address=1,
        value=150,
        platform=Platform.UNIVERSAL,
        compare=0x20,
        flags=Flags(compare_enabled=True)
    )
    code = encode(legacy, validate=False)

    handle_preview(code, str(dummy_binary_file), profile_path=str(dummy_profile_file))

    captured = capsys.readouterr()
    assert "=== Patch Preview Results ===" in captured.out
    assert "hp" in captured.out
    assert "0x20" in captured.out
    assert "0x96" in captured.out  # 150 in hex is 0x96


def test_cli_sandbox_command(dummy_profile_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Set HP to 120.
    legacy = LegacyPatch(address=1, value=120, platform=Platform.UNIVERSAL)
    code = encode(legacy, validate=False)

    handle_sandbox(code, profile_path=str(dummy_profile_file))

    captured = capsys.readouterr()
    assert "Initial Virtual State" in captured.out
    assert "Resulting Virtual State" in captured.out
    # The virtual state binary hex dump should show HP offset (1) set to 120 (0x78)
    assert "0078" in captured.out


def test_interactive_shell_repl(capsys: pytest.CaptureFixture[str]) -> None:
    # We will feed "help", then "exit" into input to test REPL loop terminates nicely
    inputs = ["help", "exit"]

    with patch("builtins.input", side_effect=inputs):
        from gamegenie_x.cli import run_shell
        run_shell()

    captured = capsys.readouterr()
    assert "=== GameGenie-X Interactive Shell v2 ===" in captured.out
    assert "Commands: decode, apply, preview, sandbox, exit" in captured.out
    assert "Interactive Commands Syntax" in captured.out
