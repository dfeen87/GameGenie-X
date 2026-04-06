"""Load and validate platform profiles from TOML files."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from gamegenie_x.models import Flags, Patch, PatchType, Platform

PROFILES_DIR: Path = Path(__file__).resolve().parent.parent.parent / "profiles"

@dataclass(frozen=True, slots=True)
class PlatformProfile:
    """Platform-specific constraints and defaults."""
    platform: Platform
    name: str                          # Human-readable name
    short_name: str                    # e.g. "NES"
    address_bits: int                  # Usable address bits
    max_address: int                   # Derived: (1 << address_bits) - 1
    data_bits: int                     # Typically 8
    compare_supported: bool            # Whether compare byte is meaningful
    default_patch_type: PatchType      # Default if not specified
    default_flags: Flags               # Default flags for this platform


def load_profile(platform: Platform) -> PlatformProfile:
    """Loads and parses the TOML file for the given platform.

    Args:
        platform: The Platform enum value to load.

    Returns:
        The loaded PlatformProfile.

    Raises:
        FileNotFoundError: If the corresponding TOML file is missing.
        ValueError: If the TOML file is malformed or invalid.
    """
    file_name = f"{platform.name.lower()}.toml"
    if platform == Platform.UNIVERSAL:
        raise ValueError("Cannot load profile for UNIVERSAL platform")

    profile_path = PROFILES_DIR / file_name
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile file not found: {profile_path}")

    try:
        with open(profile_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse profile {profile_path}: {e}") from e

    try:
        plat_data = data["platform"]
        addr_data = data["address"]
        data_data = data["data"]
        comp_data = data["compare"]
        def_data = data["defaults"]

        flags_dict = def_data["flags"]
        default_flags = Flags(
            compare_enabled=flags_dict.get("compare_enabled", False),
            wide_data=flags_dict.get("wide_data", False),
            read_only=flags_dict.get("read_only", False),
            persistent=flags_dict.get("persistent", False),
        )

        return PlatformProfile(
            platform=Platform(plat_data["id"]),
            name=plat_data["name"],
            short_name=plat_data["short_name"],
            address_bits=addr_data["bits"],
            max_address=addr_data["max"],
            data_bits=data_data["bits"],
            compare_supported=comp_data["supported"],
            default_patch_type=PatchType[def_data["patch_type"]],
            default_flags=default_flags,
        )
    except KeyError as e:
        raise ValueError(f"Malformed profile {profile_path}: missing key {e}") from e
    except ValueError as e:
        raise ValueError(f"Malformed profile {profile_path}: invalid value ({e})") from e


# TODO(don): doc says Game profiles in JSON but Platform profiles in TOML seem intended — clarify
def load_all_profiles() -> dict[Platform, PlatformProfile]:
    """Loads all .toml files from PROFILES_DIR.

    Returns:
        A dict mapping Platform enums to PlatformProfiles.
    """
    profiles: dict[Platform, PlatformProfile] = {}
    if not PROFILES_DIR.exists():
        return profiles

    for toml_file in PROFILES_DIR.glob("*.toml"):
        try:
            with open(toml_file, "rb") as f:
                data = tomllib.load(f)
            plat_id = data["platform"]["id"]
            platform = Platform(plat_id)
            profiles[platform] = load_profile(platform)
        except Exception:
            # Ignore files that fail to load during bulk load,
            # or maybe just raise? The contract doesn't say. Let's pass over them
            # or actually it's better to log or just raise.
            # Let's be strict.
            raise
    return profiles


def validate_patch(patch: Patch, profile: PlatformProfile) -> list[str]:
    """Validates a Patch against its platform profile.

    Args:
        patch: The Patch object to validate.
        profile: The PlatformProfile to validate against.

    Returns:
        A list of warning/error strings. Empty list means valid.
    """
    errors = []

    if patch.platform != profile.platform:
        errors.append(
            f"Platform mismatch: patch has {patch.platform.name}, "
            f"profile is {profile.platform.name}"
        )

    if patch.address > profile.max_address:
        errors.append(
            f"Address 0x{patch.address:X} exceeds maximum 0x{profile.max_address:X} "
            f"for {profile.name}"
        )

    max_value = (1 << profile.data_bits) - 1
    if patch.value > max_value:
        errors.append(
            f"Value 0x{patch.value:X} exceeds {profile.data_bits}-bit maximum 0x{max_value:X}"
        )

    if patch.compare > 0 and not profile.compare_supported:
        errors.append(f"Compare byte is set but not supported by {profile.name}")
    elif patch.compare > max_value:
        errors.append(
            f"Compare value 0x{patch.compare:X} exceeds {profile.data_bits}-bit "
            f"maximum 0x{max_value:X}"
        )

    if patch.flags.compare_enabled and not profile.compare_supported:
        errors.append(f"Compare flag enabled but not supported by {profile.name}")

    return errors
