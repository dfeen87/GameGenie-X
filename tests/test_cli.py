import subprocess
import sys
from pathlib import Path

from gamegenie_x.encoder import encode
from gamegenie_x.models import Patch, Platform


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Helper to run the CLI as a subprocess."""
    # We run the cli module directly
    return subprocess.run(
        [sys.executable, "-m", "gamegenie_x.cli", *args],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src"}
    )

def test_cli_info_external_profile() -> None:
    res = run_cli("info", "--platform", "xboxone")
    assert res.returncode == 0
    assert "Xbox One (XB1)" in res.stdout
    assert "Platform ID: xboxone (External)" in res.stdout
    assert "IO Strategy:" in res.stdout

def test_cli_list_shows_external_profiles() -> None:
    res = run_cli("list")
    assert res.returncode == 0
    assert "xboxone" in res.stdout
    assert "ps5" in res.stdout
    assert "NES" in res.stdout

def test_cli_validate_external_profile() -> None:
    # Encode a code targeted for UNIVERSAL since external profiles map onto it for 75-bit structure
    patch = Patch(address=0x1000, value=0x99, platform=Platform.UNIVERSAL)
    code = encode(patch, validate=False)

    # Validation against xboxone profile should pass
    res = run_cli("validate", "--platform", "xboxone", code)
    assert res.returncode == 0
    assert "VALID" in res.stdout

def test_cli_patch_file(tmp_path: Path) -> None:
    save_path = tmp_path / "save.bin"
    save_path.write_bytes(bytearray([0] * 8192))

    patch = Patch(address=0x1000, value=0x99, platform=Platform.UNIVERSAL)
    code = encode(patch, validate=False)

    res = run_cli("patch", "--platform", "ps5", code, str(save_path))
    assert res.returncode == 0
    assert "Successfully applied patch" in res.stdout

    data = save_path.read_bytes()
    assert data[0x1000] == 0x99
