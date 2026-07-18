# type: ignore
"""Hypothesis-based fuzz tests for GameGenie-X decoder and validator stability."""

from __future__ import annotations

import random
import sys

from hypothesis import given, settings
from hypothesis import strategies as st

from gamegenie_x.decoder import decode
from gamegenie_x.encoder import encode
from gamegenie_x.models import Flags, Patch, PatchType, Platform
from gamegenie_x.validator import InvalidCodeError, PayloadValidator

# Platform-dependent settings to run extensive checks on Linux,
# but fast, deterministic checks on Windows and macOS.
if sys.platform == "linux":
    hypothesis_settings = settings(max_examples=2000, deadline=None)
else:
    random.seed(42)
    hypothesis_settings = settings(max_examples=100, derandomize=True, deadline=None)

# Hypothesis Strategies
flags_strategy = st.builds(
    Flags,
    compare_enabled=st.booleans(),
    wide_data=st.booleans(),
    read_only=st.booleans(),
    persistent=st.booleans()
)

patch_strategy = st.builds(
    Patch,
    address=st.integers(min_value=0, max_value=0xFFFFFFFF),
    value=st.integers(min_value=0, max_value=0xFF),
    compare=st.integers(min_value=0, max_value=0xFF),
    platform=st.sampled_from(list(Platform)),
    patch_type=st.sampled_from(list(PatchType)),
    flags=flags_strategy
)


@hypothesis_settings
@given(patch=patch_strategy)
def test_fuzz_code_generation_roundtrip(patch: Patch) -> None:
    """Fuzz test for encoding and decoding valid random patches.

    Ensures that every generated Patch can be successfully encoded
    into a GameGenie-X code, and then decoded back to an identical Patch object
    without any data loss or crash.
    """
    try:
        code = encode(patch, validate=False)
        decoded = decode(code)
        assert decoded == patch
    except Exception as e:
        raise AssertionError(f"Roundtrip failed for patch: {patch}") from e


@hypothesis_settings
@given(
    patch=patch_strategy,
    index=st.integers(0, 14),
    replacement_char=st.sampled_from("0123456789ABCDEFGHJKMNPQRSTVWXYZ!@#$-_ ")
)
def test_fuzz_payload_mutation(patch: Patch, index: int, replacement_char: str) -> None:
    """Fuzz test for payload mutations under randomized conditions.

    Takes a valid code, replaces one symbol with a random valid or invalid character,
    and asserts that the decoder never crashes with an unhandled exception. It
    must either succeed (if the mutation is by chance valid) or raise an InvalidCodeError.
    """
    code = encode(patch, validate=False)
    # Remove separators to perform mutation on 15-char string
    stripped = code.replace("-", "")
    mutated_list = list(stripped)
    mutated_list[index] = replacement_char
    mutated_stripped = "".join(mutated_list)

    # Reconstruct with original spacing
    mutated_code = f"{mutated_stripped[:5]}-{mutated_stripped[5:10]}-{mutated_stripped[10:]}"

    try:
        decode(mutated_code)
    except InvalidCodeError:
        pass
    except Exception as e:
        raise AssertionError(f"Unhandled exception during payload mutation: {e}") from e


@hypothesis_settings
@given(injected_str=st.text())
def test_fuzz_symbol_injection(injected_str: str) -> None:
    """Fuzz test for random/malformed alphabet symbol injection.

    Injects arbitrary string inputs into the decoder and validator, ensuring
    they always reject invalid structures cleanly with an InvalidCodeError or ChecksumError
    and never throw unhandled core exceptions.
    """
    try:
        PayloadValidator.validate(injected_str)
        # If it validates, check decode also doesn't crash
        decode(injected_str)
    except InvalidCodeError:
        pass
    except Exception as e:
        raise AssertionError(f"Unhandled exception during symbol injection: {e}") from e
