"""Payload validator for GameGenie-X codes."""

from __future__ import annotations

from gamegenie_x import alphabet, checksum
from gamegenie_x.bitpack import FIELD_SPECS


class InvalidCodeError(ValueError):
    """Raised when a GameGenie-X code is malformed, corrupted, or has an invalid checksum."""

    def __init__(self, reason: str, offending_code: str, hint: str | None = None) -> None:
        """Initializes the InvalidCodeError.

        Args:
            reason: The error description.
            offending_code: The original/raw code that caused the failure.
            hint: An optional helpful hint for fixing the issue.
        """
        message = f"Invalid code '{offending_code}': {reason}"
        if hint:
            message += f" (Hint: {hint})"
        super().__init__(message)
        self.reason = reason
        self.offending_code = offending_code
        self.hint = hint


class PayloadValidator:
    """Strengthens checksum validation and structural checks for decoded codes."""

    @staticmethod
    def validate(code: str, *, verify: bool = True) -> None:
        """Validates the 75-bit payload structure and checksum without creating a Patch object.

        Raises:
            InvalidCodeError: If any validation check fails.
        """
        # 1. Normalize and basic format checks
        try:
            stripped = alphabet.strip_code(code)
        except Exception as e:
            raise InvalidCodeError(
                reason=f"Failed to normalize code: {e}",
                offending_code=code,
                hint="Make sure the code consists of valid symbols and separators."
            ) from e

        if len(stripped) != alphabet.CODE_LENGTH:
            raise InvalidCodeError(
                reason=(
                    f"Code length must be exactly {alphabet.CODE_LENGTH} valid characters, "
                    f"got {len(stripped)}."
                ),
                offending_code=code,
                hint="Check for missing or extra characters in the code."
            )

        # 2. Character validation against active/default alphabet
        active_alphabet = alphabet.get_active_alphabet()
        for idx, char in enumerate(stripped):
            if char not in active_alphabet.char_to_value:
                raise InvalidCodeError(
                    reason=(
                        f"Character '{char}' at position {idx + 1} "
                        f"is not in the active alphabet."
                    ),
                    offending_code=code,
                    hint="Ensure you are only using characters from the supported alphabet."
                )

        # 3. Decode code to 75-bit integer
        try:
            packed = active_alphabet.decode_code_to_bits(stripped)
        except Exception as e:
            raise InvalidCodeError(
                reason=f"Failed to decode symbols to bits: {e}",
                offending_code=code
            ) from e

        if packed < 0 or packed >= (1 << (alphabet.CODE_LENGTH * 5)):
            raise InvalidCodeError(
                reason="Decoded value is out of 75-bit range.",
                offending_code=code
            )

        # 4. Validate Checksum
        if verify:
            crc_mask = (1 << checksum.CRC_WIDTH) - 1
            embedded_checksum = packed & crc_mask
            payload = packed >> checksum.CRC_WIDTH
            computed = checksum.compute(payload)
            if computed != embedded_checksum:
                from gamegenie_x.decoder import ChecksumError
                raise ChecksumError(
                    reason=(
                        f"Checksum verification failed. Embedded: {embedded_checksum}, "
                        f"Computed: {computed}."
                    ),
                    offending_code=code,
                    hint="The code might have a typo or has been corrupted."
                )

        # 5. Extract fields directly to validate their structures before Patch creation
        payload = packed >> checksum.CRC_WIDTH
        platform_val = (payload >> (FIELD_SPECS["platform"][1] - 11)) & ((1 << 4) - 1)
        patch_type_val = (payload >> (FIELD_SPECS["patch_type"][1] - 11)) & ((1 << 4) - 1)
        flags_val = (payload >> (FIELD_SPECS["flags"][1] - 11)) & ((1 << 8) - 1)

        # Check platform enum range (0-15)
        if not (0 <= platform_val <= 15):
            raise InvalidCodeError(
                reason=f"Invalid platform value {platform_val} (must be 0-15).",
                offending_code=code
            )

        # Check patch type range (0-15)
        if not (0 <= patch_type_val <= 15):
            raise InvalidCodeError(
                reason=f"Invalid patch type value {patch_type_val} (must be 0-15).",
                offending_code=code
            )

        # Check flags reserved bits (must fit in 4-bit range 0-15)
        reserved_bits = flags_val & 0x0F
        if not (0 <= reserved_bits <= 15):
            raise InvalidCodeError(
                reason=f"Invalid reserved flags bits {reserved_bits} (must fit in 4 bits).",
                offending_code=code
            )
