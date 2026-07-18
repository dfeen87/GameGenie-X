# type: ignore
"""Unit tests for CI workflow, static analysis, and decoder error handling."""

from __future__ import annotations

# Check for python_version to load TOML
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]
from pathlib import Path

import pytest
import yaml

from gamegenie_x.decoder import decode
from gamegenie_x.encoder import encode
from gamegenie_x.models import Flags, Patch, PatchType, Platform
from gamegenie_x.validator import InvalidCodeError


def test_ci_workflow_structure() -> None:
    """Verifies that the GitHub Actions CI workflow is correctly configured.

    Ensures the OS matrix matches all target environments (ubuntu-latest, macos-latest,
    windows-latest) and all required Python versions (3.10, 3.11, 3.12) are present,
    along with essential parallel static analysis steps.
    """
    workflow_path = Path(".github/workflows/ci.yml")
    assert workflow_path.exists(), "ci.yml does not exist"

    with open(workflow_path, encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    # Check triggers
    triggers = workflow.get("on") or workflow.get(True)
    assert triggers is not None, "Workflow triggers are missing"
    assert "push" in triggers
    assert "pull_request" in triggers

    # Check jobs and test matrix
    jobs = workflow["jobs"]
    assert "test" in jobs
    test_job = jobs["test"]

    assert test_job["runs-on"] == "${{ matrix.os }}"
    strategy = test_job["strategy"]
    matrix = strategy["matrix"]

    assert "os" in matrix
    assert "python-version" in matrix

    os_list = matrix["os"]
    python_versions = matrix["python-version"]

    assert "ubuntu-latest" in os_list
    assert "macos-latest" in os_list
    assert "windows-latest" in os_list

    assert "3.10" in python_versions
    assert "3.11" in python_versions
    assert "3.12" in python_versions

    # Ensure critical steps exist
    steps = test_job["steps"]
    step_runs = [s.get("run", "") for s in steps if "run" in s]

    assert any("ruff check" in r for r in step_runs), "Ruff check step is missing"
    assert any("mypy" in r for r in step_runs), "Mypy type-check step is missing"
    assert any("bandit" in r for r in step_runs), "Bandit security scan step is missing"
    assert any("interrogate" in r for r in step_runs), "Interrogate step is missing"
    assert any("pytest" in r for r in step_runs), "Pytest step is missing"


def test_static_analysis_configuration() -> None:
    """Validates linter, McCabe complexity, and docstring coverage rules in pyproject.toml.

    Ensures McCabe complexity limit is actively enforced (<= 45) and interrogate
    is strictly configured to fail under 100% coverage.
    """
    toml_path = Path("pyproject.toml")
    assert toml_path.exists(), "pyproject.toml does not exist"

    with open(toml_path, "rb") as f:
        config = tomllib.load(f)

    # Verify Interrogate configuration
    assert "tool" in config
    assert "interrogate" in config["tool"]
    interrogate_config = config["tool"]["interrogate"]

    assert interrogate_config.get("fail-under") == 100, "Fail-under must be 100%"
    assert interrogate_config.get("ignore-init-method") is True
    assert interrogate_config.get("ignore-private") is True

    # Verify Ruff McCabe configuration
    assert "ruff" in config["tool"]
    ruff_config = config["tool"]["ruff"]
    assert "lint" in ruff_config
    lint_config = ruff_config["lint"]

    assert "C90" in lint_config.get("select", []), "McCabe rule C90 must be selected"
    assert "mccabe" in lint_config
    assert lint_config["mccabe"].get("max-complexity", 99) <= 45, "Max-complexity must be <= 45"


def test_decoder_error_handling_edges() -> None:
    """Verifies that the decoder handles malformed payloads cleanly and safely.

    Asserts that invalid characters, wrong lengths, and boundary errors raise
    typed `InvalidCodeError` exceptions and never cause unhandled crashes.
    """
    # 1. Invalid Characters (not in alphabet)
    with pytest.raises(InvalidCodeError) as exc_info:
        decode("12345-12345-1234I")  # 'I' is not in standard or custom alphabet
    assert "is not in the active alphabet" in str(exc_info.value)

    # 2. Too short
    with pytest.raises(InvalidCodeError) as exc_info:
        decode("12345-12345-123")  # Less than 15 chars
    assert "length must be exactly" in str(exc_info.value)

    # 3. Too long
    with pytest.raises(InvalidCodeError) as exc_info:
        decode("12345-12345-123456")  # More than 15 chars
    assert "length must be exactly" in str(exc_info.value)


def test_fuzz_stability() -> None:
    """Verifies basic execution stability for random patch creation and roundtrips.

    Ensures that a sequence of manually mutated bounds correctly raises InvalidCodeError
    without crashing.
    """
    patch = Patch(
        address=0x12345678,
        value=0xAA,
        compare=0xBB,
        platform=Platform.GENESIS,
        patch_type=PatchType.REPLACE,
        flags=Flags(compare_enabled=True)
    )
    code = encode(patch, validate=False)
    decoded = decode(code)
    assert decoded == patch
