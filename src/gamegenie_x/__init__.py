"""GameGenie-X: A modern, platform-unified Game Genie patch encoding engine."""

__version__ = "1.0.0"

from gamegenie_x.decoder import ChecksumError, decode
from gamegenie_x.detector import DetectionDiagnostic, ProfileDetector
from gamegenie_x.encoder import encode
from gamegenie_x.game_profiles import (
    GameProfile,
    InvalidProfileError,
    load_game_profile,
    load_game_profile_by_id,
)
from gamegenie_x.models import Flags, Patch, PatchType, Platform
from gamegenie_x.safety import SafetyResult, SafetyRulesEngine, UnsafePatchError

__all__ = [
    "ChecksumError",
    "DetectionDiagnostic",
    "Flags",
    "GameProfile",
    "InvalidProfileError",
    "Patch",
    "PatchType",
    "Platform",
    "ProfileDetector",
    "SafetyResult",
    "SafetyRulesEngine",
    "UnsafePatchError",
    "__version__",
    "decode",
    "encode",
    "load_game_profile",
    "load_game_profile_by_id",
]
