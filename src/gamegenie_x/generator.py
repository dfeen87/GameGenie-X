"""Module E1: Code Generator for GameGenie-X."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gamegenie_x.encoder import encode
from gamegenie_x.models import Flags, Patch, PatchType, Platform

if TYPE_CHECKING:
    from gamegenie_x.game_profiles import GameProfile


class InvalidFieldError(ValueError):
    """Raised when a specified field name does not exist in the game profile."""


class OutOfRangeValueError(ValueError):
    """Raised when the provided value is outside the allowed range for the field."""


class CodeGenerator:
    """Generates valid GameGenie-X codes from human-readable inputs."""

    def validate_field(self, field_name: str, profile: GameProfile) -> None:
        """Validates that a field exists within the profile save structure.

        Args:
            field_name: The dot-separated path of the field.
            profile: The GameProfile to check against.

        Raises:
            InvalidFieldError: If the field is not found in the profile's save structure.
        """
        offset = profile.get_offset(field_name)
        if offset is None:
            raise InvalidFieldError(
                f"Field '{field_name}' not found in the profile's save structure."
            )

    def generate_code(self, field_name: str, value: int, profile: GameProfile) -> str:
        """Generates a valid GameGenie-X code for the specified field and value.

        Args:
            field_name: The dot-separated path of the field.
            value: The integer value to set.
            profile: The GameProfile mapping fields to offsets and ranges.

        Returns:
            The generated 15-character GameGenie-X code.

        Raises:
            InvalidFieldError: If the field does not exist.
            OutOfRangeValueError: If the value is out of range.
        """
        self.validate_field(field_name, profile)

        # Retrieve and enforce value ranges if defined
        val_range = self._get_value_range(field_name, profile)
        if val_range is not None:
            min_val, max_val = val_range
            if value < min_val or value > max_val:
                raise OutOfRangeValueError(
                    f"Value {value} is out of the profile's allowed range [{min_val}, {max_val}]."
                )

        # Also enforce 8-bit limits since code encodes 8-bit values
        if not (0 <= value <= 0xFF):
            raise OutOfRangeValueError(
                f"Value {value} exceeds the 8-bit limit of [0, 255]."
            )

        offset = profile.get_offset(field_name)
        assert offset is not None  # Guaranteed by validate_field

        return self.encode_payload(offset, value)

    def encode_payload(self, offset: int, value: int) -> str:
        """Encodes an offset and value directly into a GameGenie-X code string.

        Args:
            offset: The target memory offset/address.
            value: The 8-bit replacement value.

        Returns:
            The formatted 15-character GameGenie-X code.

        Raises:
            OutOfRangeValueError: If offset or value are outside their respective bit-width limits.
        """
        if not (0 <= offset <= 0xFFFFFFFF):
            raise OutOfRangeValueError(f"Offset {offset} is out of 32-bit range.")
        if not (0 <= value <= 0xFF):
            raise OutOfRangeValueError(f"Value {value} is out of 8-bit range.")

        patch = Patch(
            address=offset,
            value=value,
            platform=Platform.UNIVERSAL,
            patch_type=PatchType.REPLACE,
            flags=Flags(),
        )
        try:
            return encode(patch, validate=False)
        except Exception as e:
            raise ValueError(f"Failed to encode patch payload: {e}") from e

    def _get_value_range(self, field_path: str, profile: GameProfile) -> tuple[int, int] | None:
        """Finds the value range for a given field path, supporting exact and suffix matches."""
        if field_path in profile.value_ranges:
            return profile.value_ranges[field_path]

        parts = field_path.split(".")
        if len(parts) > 1:
            last_part = parts[-1]
            if last_part in profile.value_ranges:
                return profile.value_ranges[last_part]

        return None
