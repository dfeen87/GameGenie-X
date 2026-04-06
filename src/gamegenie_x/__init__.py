"""GameGenie-X: A modern, platform-unified Game Genie patch encoding engine."""

__version__ = "1.0.0"

from gamegenie_x.decoder import ChecksumError, decode
from gamegenie_x.encoder import encode
from gamegenie_x.models import Flags, Patch, PatchType, Platform

__all__ = [
    "__version__",
    "Patch",
    "Platform",
    "PatchType",
    "Flags",
    "encode",
    "decode",
    "ChecksumError",
]
