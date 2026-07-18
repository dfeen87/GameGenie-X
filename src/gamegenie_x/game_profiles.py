"""Module B: Profile System v2 - Game Profile Schema and Loader."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class InvalidProfileError(ValueError):
    """Raised when a game profile is malformed, missing fields, or has invalid types."""


@dataclass(frozen=True, slots=True)
class GameProfile:
    """A fully typed, validated schema for a specific game's profile."""

    game_id: str
    display_name: str
    save_structure: dict[str, int | dict[str, Any]]
    value_ranges: dict[str, tuple[int, int]]
    flags: dict[str, bool]
    signature: bytes | list[int]
    file_size_range: tuple[int, int] | None = None
    format: str | None = None
    magic_number: bytes | None = None

    def __post_init__(self) -> None:
        """Validate fields at load time to ensure deterministic correctness."""
        # 1. Validate game_id
        if not isinstance(self.game_id, str) or not self.game_id:
            raise InvalidProfileError("game_id must be a non-empty string.")

        # 2. Validate display_name
        if not isinstance(self.display_name, str) or not self.display_name:
            raise InvalidProfileError("display_name must be a non-empty string.")

        # 3. Validate save_structure recursively
        self._validate_save_structure(self.save_structure)

        # 4. Validate value_ranges
        if not isinstance(self.value_ranges, dict):
            raise InvalidProfileError("value_ranges must be a dictionary.")
        for k, v in self.value_ranges.items():
            if not isinstance(k, str):
                raise InvalidProfileError(f"value_ranges key '{k}' must be a string.")
            if not isinstance(v, tuple) or len(v) != 2 or not all(isinstance(x, int) for x in v):
                raise InvalidProfileError(
                    f"value_ranges value for '{k}' must be a tuple of two integers (min, max)."
                )
            if v[0] > v[1]:
                raise InvalidProfileError(
                    f"Invalid value range for '{k}': min ({v[0]}) "
                    f"cannot be greater than max ({v[1]})."
                )

        # 5. Validate flags
        if not isinstance(self.flags, dict):
            raise InvalidProfileError("flags must be a dictionary.")
        for fk, fv in self.flags.items():
            if not isinstance(fk, str):
                raise InvalidProfileError(f"flags key '{fk}' must be a string.")
            if not isinstance(fv, bool):
                raise InvalidProfileError(f"flags value for '{fk}' must be a boolean.")

        # 6. Validate signature
        if not isinstance(self.signature, (bytes, list)):
            raise InvalidProfileError("signature must be bytes or a list of integers.")
        if isinstance(self.signature, list):
            for idx, item in enumerate(self.signature):
                if not isinstance(item, int) or not (0 <= item <= 255):
                    raise InvalidProfileError(
                        f"signature element at index {idx} must be an integer between 0 and 255."
                    )

        # 7. Validate file_size_range
        if self.file_size_range is not None:
            if (
                not isinstance(self.file_size_range, tuple)
                or len(self.file_size_range) != 2
                or not all(isinstance(sz_val, int) for sz_val in self.file_size_range)
            ):
                raise InvalidProfileError(
                    "file_size_range must be a tuple of two integers (min, max)."
                )
            if self.file_size_range[0] > self.file_size_range[1]:
                raise InvalidProfileError(
                    f"Invalid file_size_range: min ({self.file_size_range[0]}) "
                    f"cannot be greater than max ({self.file_size_range[1]})."
                )

        # 8. Validate format
        if self.format is not None and not isinstance(self.format, str):
            raise InvalidProfileError("format must be a string.")

        # 9. Validate magic_number
        if self.magic_number is not None and not isinstance(self.magic_number, bytes):
            raise InvalidProfileError("magic_number must be bytes.")

    def _validate_save_structure(self, struct: Any) -> None:
        """Recursively validate save structure entries."""
        if not isinstance(struct, dict):
            raise InvalidProfileError("save_structure must be a dictionary.")
        for k, v in struct.items():
            if not isinstance(k, str):
                raise InvalidProfileError(f"save_structure key '{k}' must be a string.")
            if isinstance(v, dict):
                self._validate_save_structure(v)
            elif isinstance(v, int):
                if v < 0:
                    raise InvalidProfileError(
                        f"save_structure offset for '{k}' cannot be negative."
                    )
            else:
                raise InvalidProfileError(
                    f"save_structure value for '{k}' must be an integer (offset) "
                    "or nested dictionary."
                )

    def get_offset(self, field_path: str) -> int | None:
        """Traverses the save_structure using dot-separated keys to find the offset.

        Args:
            field_path: A dot-separated string representing the path to the field.

        Returns:
            The offset integer if found, or None.
        """
        keys = field_path.split(".")
        current: Any = self.save_structure
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        if isinstance(current, int):
            return current
        return None


def load_game_profile(filepath: str | Path) -> GameProfile:
    """Loads and validates a GameProfile from a JSON file.

    Args:
        filepath: The path to the JSON file.

    Returns:
        The validated GameProfile object.

    Raises:
        FileNotFoundError: If the profile file does not exist.
        InvalidProfileError: If the profile is malformed, has invalid types, or missing fields.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Profile file not found: {path}")

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise InvalidProfileError(f"Failed to parse JSON profile {path}: {e}") from e

    if not isinstance(data, dict):
        raise InvalidProfileError(f"JSON profile {path} must represent a dictionary.")

    # Extract fields with type-validation and conversion where appropriate
    try:
        game_id = data["game_id"]
        display_name = data["display_name"]
        save_structure = data["save_structure"]
        raw_value_ranges = data["value_ranges"]
        flags = data["flags"]
        signature = data["signature"]
    except KeyError as e:
        raise InvalidProfileError(f"Profile {path} is missing required field: {e}") from e

    # Convert value_ranges lists to tuples
    if not isinstance(raw_value_ranges, dict):
        raise InvalidProfileError(f"value_ranges must be a dictionary in profile {path}.")
    value_ranges: dict[str, tuple[int, int]] = {}
    for k, v in raw_value_ranges.items():
        if isinstance(v, list) and len(v) == 2:
            value_ranges[k] = (v[0], v[1])
        elif isinstance(v, tuple) and len(v) == 2:
            value_ranges[k] = v
        else:
            raise InvalidProfileError(
                f"value_ranges value for '{k}' must be a list/tuple of two integers."
            )

    # Optional fields
    file_size_range_raw = data.get("file_size_range")
    file_size_range: tuple[int, int] | None = None
    if file_size_range_raw is not None:
        if isinstance(file_size_range_raw, list) and len(file_size_range_raw) == 2:
            file_size_range = (file_size_range_raw[0], file_size_range_raw[1])
        elif isinstance(file_size_range_raw, tuple) and len(file_size_range_raw) == 2:
            file_size_range = file_size_range_raw
        else:
            raise InvalidProfileError("file_size_range must be a list/tuple of two integers.")

    format_str = data.get("format")

    magic_number_raw = data.get("magic_number")
    magic_number: bytes | None = None
    if magic_number_raw is not None:
        if isinstance(magic_number_raw, str):
            # Parse hex string or similar
            try:
                magic_number = bytes.fromhex(magic_number_raw)
            except ValueError as e:
                raise InvalidProfileError(
                    f"magic_number must be a valid hex string: {e}"
                ) from e
        elif isinstance(magic_number_raw, list):
            try:
                magic_number = bytes(magic_number_raw)
            except ValueError as e:
                raise InvalidProfileError(f"magic_number has invalid bytes: {e}") from e
        elif isinstance(magic_number_raw, bytes):
            magic_number = magic_number_raw
        else:
            raise InvalidProfileError("magic_number must be a hex string or list of bytes.")

    # Support list of ints to bytes conversion for signature at loader level if desired,
    # but GameProfile constructor supports both. We can preserve list/bytes or normalize it.
    if isinstance(signature, list):
        try:
            signature_bytes: bytes | list[int] = bytes(signature)
        except ValueError:
            # Let __post_init__ raise specific error
            signature_bytes = signature
    else:
        signature_bytes = signature

    try:
        return GameProfile(
            game_id=game_id,
            display_name=display_name,
            save_structure=save_structure,
            value_ranges=value_ranges,
            flags=flags,
            signature=signature_bytes,
            file_size_range=file_size_range,
            format=format_str,
            magic_number=magic_number,
        )
    except InvalidProfileError:
        raise
    except Exception as e:
        raise InvalidProfileError(f"Profile validation failed: {e}") from e


def load_game_profile_by_id(game_id: str, profiles_dir: str | Path = "profiles") -> GameProfile:
    """Loads a GameProfile from the profiles directory by its game_id.

    Args:
        game_id: The game's ID (which matches the filename <game_id>.json).
        profiles_dir: The directory containing the profile JSON files.

    Returns:
        The validated GameProfile object.
    """
    path = Path(profiles_dir) / f"{game_id}.json"
    return load_game_profile(path)
