"""Command-line interface for GameGenie-X."""

from __future__ import annotations

import argparse
import sys

from gamegenie_x import decoder, encoder, profiles
from gamegenie_x.models import Flags, Patch, PatchType, Platform


def get_parser() -> argparse.ArgumentParser:
    """Returns the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="gamegenie-x",
        description="A modern, platform-unified Game Genie patch encoding engine.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Encode subcommand
    encode_parser = subparsers.add_parser("encode", help="Encode a Patch into a code string")
    encode_parser.add_argument(
        "--address", required=True, type=lambda x: int(x, 0), help="Target memory address"
    )
    encode_parser.add_argument(
        "--value", required=True, type=lambda x: int(x, 0), help="Replacement byte value"
    )
    encode_parser.add_argument(
        "--compare", type=lambda x: int(x, 0), default=0, help="Compare/check byte"
    )
    encode_parser.add_argument(
        "--platform", required=True, type=str, help="Platform name (e.g., NES)"
    )
    encode_parser.add_argument(
        "--type", type=str, default="REPLACE", help="Patch operation type"
    )
    encode_parser.add_argument(
        "--compare-enabled", action="store_true", help="Enable compare check"
    )
    encode_parser.add_argument(
        "--wide-data", action="store_true", help="16-bit data mode"
    )
    encode_parser.add_argument(
        "--read-only", action="store_true", help="Intercept reads only"
    )
    encode_parser.add_argument(
        "--persistent", action="store_true", help="Patch survives soft reset"
    )

    # Decode subcommand
    decode_parser = subparsers.add_parser("decode", help="Decode a code string into a Patch")
    decode_parser.add_argument("code", type=str, help="The GameGenie-X code string")

    # Validate subcommand
    validate_parser = subparsers.add_parser("validate", help="Validate a code string")
    validate_parser.add_argument("code", type=str, help="The GameGenie-X code string")

    # Info subcommand
    info_parser = subparsers.add_parser("info", help="Print platform profile details")
    info_parser.add_argument(
        "--platform", required=True, type=str, help="Platform name (e.g., NES)"
    )

    return parser


def parse_platform(name: str) -> Platform:
    """Parses a platform name string to a Platform enum."""
    try:
        return Platform[name.upper()]
    except KeyError as e:
        raise ValueError(f"Unknown platform: {name}") from e


def parse_patch_type(name: str) -> PatchType:
    """Parses a patch type name string to a PatchType enum."""
    try:
        return PatchType[name.upper()]
    except KeyError as e:
        raise ValueError(f"Unknown patch type: {name}") from e


def main() -> None:
    """Entry point for the command-line interface."""
    parser = get_parser()
    args = parser.parse_args()

    try:
        if args.command == "encode":
            platform = parse_platform(args.platform)
            patch_type = parse_patch_type(args.type)
            flags = Flags(
                compare_enabled=args.compare_enabled,
                wide_data=args.wide_data,
                read_only=args.read_only,
                persistent=args.persistent,
            )
            patch = Patch(
                address=args.address,
                value=args.value,
                compare=args.compare,
                platform=platform,
                patch_type=patch_type,
                flags=flags,
            )
            code = encoder.encode(patch)
            print(code)

        elif args.command == "decode":
            try:
                patch = decoder.decode(args.code)
            except decoder.ChecksumError as e:
                print(f"Checksum Error: {e}", file=sys.stderr)
                sys.exit(2)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

            print(f"{'Field':<15} | {'Value'}")
            print("-" * 35)
            print(f"{'Address':<15} | 0x{patch.address:04X}")
            print(f"{'Value':<15} | 0x{patch.value:02X}")
            print(f"{'Compare':<15} | 0x{patch.compare:02X}")
            print(f"{'Platform':<15} | {patch.platform.name}")
            print(f"{'Patch Type':<15} | {patch.patch_type.name}")
            flags_str = (
                f"compare_enabled={patch.flags.compare_enabled}, "
                f"wide_data={patch.flags.wide_data}, "
                f"read_only={patch.flags.read_only}, "
                f"persistent={patch.flags.persistent}"
            )
            print(f"{'Flags':<15} | {flags_str}")

        elif args.command == "validate":
            try:
                patch = decoder.decode(args.code)
                profile = profiles.load_profile(patch.platform)
                errors = profiles.validate_patch(patch, profile)
                if errors:
                    print("INVALID")
                    for err in errors:
                        print(f"- {err}")
                    sys.exit(2)
                print("VALID")
            except decoder.ChecksumError as e:
                print("INVALID")
                print(f"- Checksum verification failed: {e}")
                sys.exit(2)
            except ValueError as e:
                print("INVALID")
                print(f"- Decoding error: {e}")
                sys.exit(2)

        elif args.command == "info":
            platform = parse_platform(args.platform)
            profile = profiles.load_profile(platform)
            print(f"Profile: {profile.name} ({profile.short_name})")
            print(f"Platform ID: {profile.platform.value}")
            print(f"Address Bits: {profile.address_bits} (Max: 0x{profile.max_address:X})")
            print(f"Data Bits: {profile.data_bits}")
            print(f"Compare Supported: {profile.compare_supported}")
            print(f"Default Patch Type: {profile.default_patch_type.name}")
            flags_str = (
                f"compare_enabled={profile.default_flags.compare_enabled}, "
                f"wide_data={profile.default_flags.wide_data}, "
                f"read_only={profile.default_flags.read_only}, "
                f"persistent={profile.default_flags.persistent}"
            )
            print(f"Default Flags: {flags_str}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
