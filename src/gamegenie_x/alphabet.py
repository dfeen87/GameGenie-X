"""GameGenie-X 32-symbol alphabet for 5-bit encoding."""

from __future__ import annotations

# Canonical alphabet — index is the 5-bit value (0–31)
ALPHABET: str = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Reverse lookup: character -> 5-bit integer
CHAR_TO_VALUE: dict[str, int] = {c: i for i, c in enumerate(ALPHABET)}
VALUE_TO_CHAR: dict[int, str] = {i: c for i, c in enumerate(ALPHABET)}

# Separator used in display format
SEPARATOR: str = "-"
GROUP_SIZE: int = 5
CODE_LENGTH: int = 15


class Alphabet:
    """Encapsulates the symbol set for GameGenie-X encoding and decoding."""

    def __init__(self, symbols: str = ALPHABET) -> None:
        """Initializes the Alphabet with a symbol set.

        Args:
            symbols: A string of unique characters. Must have at least 32 characters
                for 5-bit encoding.
        """
        if len(symbols) < 32:
            raise ValueError("Alphabet must contain at least 32 symbols.")
        if len(set(symbols.upper())) != len(symbols):
            raise ValueError("Alphabet symbols must be unique and case-insensitive.")

        self.symbols = symbols
        self.normalized_symbols = symbols.upper()
        self.char_to_value = {c: i for i, c in enumerate(self.normalized_symbols)}
        self.value_to_char = {i: c for i, c in enumerate(self.normalized_symbols)}

    def encode_bits_to_code(self, packed: int) -> str:
        """Takes a 75-bit integer, returns a 15-character raw symbol string.

        Extracts symbols from MSB to LSB in 5-bit chunks.

        Args:
            packed: A 75-bit integer to encode.

        Returns:
            A 15-character string of symbols.

        Raises:
            ValueError: If the input integer is negative or too large to fit in 75 bits.
        """
        if packed < 0 or packed >= (1 << 75):
            raise ValueError("Input must be a 75-bit non-negative integer.")

        symbols = []
        # Extract from MSB to LSB: index 0 is bits 74-70, index 14 is bits 4-0.
        for i in range(CODE_LENGTH - 1, -1, -1):
            shift = i * 5
            chunk = (packed >> shift) & 0x1F
            symbols.append(self.value_to_char[chunk])
        return "".join(symbols)

    def decode_code_to_bits(self, code: str) -> int:
        """Takes a raw or formatted code string, returns a 75-bit integer.

        Args:
            code: A string containing exactly 15 valid characters (separators ignored).

        Returns:
            The decoded 75-bit integer.

        Raises:
            ValueError: For invalid characters or wrong length.
        """
        stripped = strip_code(code)
        if len(stripped) != CODE_LENGTH:
            raise ValueError(
                f"Code must be exactly {CODE_LENGTH} valid chars, got {len(stripped)}."
            )

        packed = 0
        # Process from left to right (MSB to LSB)
        for idx, char in enumerate(stripped):
            if char not in self.char_to_value:
                raise ValueError(f"Invalid character in code: '{char}' at position {idx + 1}")
            packed = (packed << 5) | self.char_to_value[char]

        return packed


# Default active alphabet
_DEFAULT_INSTANCE = Alphabet(ALPHABET)
_ACTIVE_INSTANCE = _DEFAULT_INSTANCE


def get_active_alphabet() -> Alphabet:
    """Returns the currently active Alphabet instance."""
    return _ACTIVE_INSTANCE


def set_active_alphabet(alphabet_obj: Alphabet) -> None:
    """Sets the active Alphabet instance.

    Args:
        alphabet_obj: The Alphabet instance to set as active.
    """
    global _ACTIVE_INSTANCE
    _ACTIVE_INSTANCE = alphabet_obj


def encode_symbols(packed: int) -> str:
    """Takes a 75-bit integer, returns a 15-character raw symbol string.

    Extracts symbols from MSB to LSB in 5-bit chunks.

    Args:
        packed: A 75-bit integer to encode.

    Returns:
        A 15-character string of symbols.

    Raises:
        ValueError: If the input integer is negative or too large to fit in 75 bits.
    """
    return _ACTIVE_INSTANCE.encode_bits_to_code(packed)


def decode_symbols(code: str) -> int:
    """Takes a raw or formatted code string, returns a 75-bit integer.

    Args:
        code: A string containing exactly 15 valid characters (separators ignored).

    Returns:
        The decoded 75-bit integer.

    Raises:
        ValueError: For invalid characters or wrong length.
    """
    return _ACTIVE_INSTANCE.decode_code_to_bits(code)


def format_code(raw: str) -> str:
    """Inserts separators to produce XXXXX-XXXXX-XXXXX format.

    Args:
        raw: A 15-character raw symbol string.

    Returns:
        The formatted string with separators.

    Raises:
        ValueError: If the raw code is not exactly 15 characters long.
    """
    stripped = strip_code(raw)
    if len(stripped) != CODE_LENGTH:
        raise ValueError(f"Raw code must be exactly {CODE_LENGTH} chars, got {len(stripped)}.")

    groups = [
        stripped[i : i + GROUP_SIZE]
        for i in range(0, len(stripped), GROUP_SIZE)
    ]
    return SEPARATOR.join(groups)


def strip_code(code: str) -> str:
    """Removes separators and whitespace, uppercases, returns raw 15-char string.

    Args:
        code: The code string to normalize.

    Returns:
        A normalized, raw symbol string.
    """
    return code.replace(SEPARATOR, "").replace(" ", "").strip().upper()
