"""Command-line interface for GameGenie-X."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gamegenie_x.game_profiles import GameProfile
    from gamegenie_x.profiles import PlatformProfile

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
    decode_parser = subparsers.add_parser("decode", help="Decode a GameGenie-X code")
    decode_parser.add_argument("code", type=str, help="The GameGenie-X code string")
    decode_parser.add_argument("--platform", type=str, help="Override platform profile")

    # Validate subcommand
    validate_parser = subparsers.add_parser("validate", help="Validate a code string")
    validate_parser.add_argument("code", type=str, help="The GameGenie-X code string")
    validate_parser.add_argument(
        "--platform", type=str, help="External platform ID (e.g. xboxone) for validation"
    )

    # Info subcommand
    info_parser = subparsers.add_parser("info", help="Print platform profile details")
    info_parser.add_argument(
        "--platform",
        required=True,
        type=str,
        help="Platform name or external ID (e.g., NES or xboxone)",
    )

    # List subcommand
    subparsers.add_parser("list", help="List all supported platform profiles")

    # Patch subcommand (legacy)
    patch_parser = subparsers.add_parser("patch", help="Apply a patch code to a file")
    patch_parser.add_argument("code", type=str, help="The GameGenie-X code string")
    patch_parser.add_argument("file", type=str, help="Path to the save file or config to patch")
    patch_parser.add_argument(
        "--platform", required=True, type=str, help="Platform name or external ID"
    )

    # Apply subcommand (v2)
    apply_parser = subparsers.add_parser(
        "apply", help="Apply decoded patches to a real save file"
    )
    apply_parser.add_argument("code", type=str, help="The GameGenie-X code string")
    apply_parser.add_argument("savefile", type=str, help="Path to the save file to patch")
    apply_parser.add_argument("--platform", type=str, help="Platform override name")
    apply_parser.add_argument("--profile", type=str, help="Path to JSON game profile")
    apply_parser.add_argument(
        "--no-safety", action="store_true", help="Disable safety rules engine"
    )

    # Preview subcommand (v2)
    preview_parser = subparsers.add_parser("preview", help="Show what fields will change")
    preview_parser.add_argument("code", type=str, help="The GameGenie-X code string")
    preview_parser.add_argument("savefile", type=str, help="Path to the save file")
    preview_parser.add_argument("--platform", type=str, help="Platform override name")
    preview_parser.add_argument("--profile", type=str, help="Path to JSON game profile")

    # Sandbox subcommand (v2)
    sandbox_parser = subparsers.add_parser(
        "sandbox", help="Apply patches to a virtual save in-memory"
    )
    sandbox_parser.add_argument("code", type=str, help="The GameGenie-X code string")
    sandbox_parser.add_argument("--profile", type=str, help="Path to JSON game profile")
    sandbox_parser.add_argument("--platform", type=str, help="Platform override name")

    # Shell subcommand (REPL)
    subparsers.add_parser("shell", help="Start the interactive shell REPL")

    return parser


def parse_platform(name: str) -> Platform | str:
    """Parses a platform name string to a Platform enum or string ID."""
    try:
        return Platform[name.upper()]
    except KeyError:
        return name.lower()


def parse_patch_type(name: str) -> PatchType:
    """Parses a patch type name string to a PatchType enum."""
    try:
        return PatchType[name.upper()]
    except KeyError as e:
        raise ValueError(f"Unknown patch type: {name}") from e


def load_profiles_for_patch(
    patch_platform: Platform | str,
    platform_override: str | None = None,
    profile_path: str | None = None,
    save_bytes: bytes | None = None,
) -> tuple[PlatformProfile, GameProfile | None]:
    """Resolves platform and game profiles based on context and defaults."""
    plat = patch_platform
    if platform_override:
        plat = parse_platform(platform_override)

    game_profile: GameProfile | None = None
    if profile_path:
        from gamegenie_x.game_profiles import load_game_profile
        try:
            game_profile = load_game_profile(profile_path)
        except Exception as e:
            msg = f"Warning: Failed to load specified profile {profile_path}: {e}"
            print(msg, file=sys.stderr)
    elif save_bytes is not None:
        from gamegenie_x.detector import ProfileDetector
        detector = ProfileDetector(profiles_dir="profiles")
        game_profile = detector.detect(save_bytes)

    if plat == Platform.UNIVERSAL and game_profile is not None:
        # Maps internally to universal platform-compatible default
        plat = "ps5"

    if plat == Platform.UNIVERSAL:
        plat = "ps5"

    try:
        platform_profile = profiles.load_profile(plat)
    except Exception:
        platform_profile = profiles.load_profile("ps5")

    return platform_profile, game_profile


def handle_decode(code_str: str, platform_override: str | None = None) -> None:
    """Decodes code and displays comprehensive structured breakdown."""
    from gamegenie_x.decoder import ChecksumError, decode
    from gamegenie_x.patch_v2 import from_legacy_patch
    from gamegenie_x.validator import PayloadValidator

    try:
        PayloadValidator.validate(code_str, verify=True)
        checksum_valid = True
    except ChecksumError:
        checksum_valid = False
    except Exception:
        checksum_valid = False

    try:
        legacy_patch = decode(code_str, verify=False)
    except Exception as e:
        print(f"Decoding Error: {e}", file=sys.stderr)
        return

    platform_profile, _ = load_profiles_for_patch(
        legacy_patch.platform, platform_override=platform_override
    )

    patch_seq = from_legacy_patch(legacy_patch, platform_profile)

    print("=== Code Explanation Output ===")
    print(f"Code String:        {code_str}")
    print(f"Checksum Validity:  {'VALID' if checksum_valid else 'INVALID'}")
    print("-" * 55)
    print("Legacy Patch Details:")
    print(f"  Address:          0x{legacy_patch.address:08X}")
    print(f"  Value:            0x{legacy_patch.value:02X}")
    print(f"  Compare:          0x{legacy_patch.compare:02X}")
    print(f"  Platform:         {legacy_patch.platform.name}")
    print(f"  Patch Type:       {legacy_patch.patch_type.name}")
    flags_str = (
        f"compare_enabled={legacy_patch.flags.compare_enabled}, "
        f"wide_data={legacy_patch.flags.wide_data}, "
        f"read_only={legacy_patch.flags.read_only}, "
        f"persistent={legacy_patch.flags.persistent}"
    )
    print(f"  Flags:            {flags_str}")
    print("-" * 55)
    print(f"Modern Patch Sequence Details ({len(patch_seq.patches)} patches):")
    for idx, p in enumerate(patch_seq.patches):
        print(f"  Patch {idx + 1}:")
        print(f"    Target Type:    {p.target_type.name}")
        offset_str = f"0x{p.offset:08X}" if p.offset is not None else "None"
        print(f"    Offset:         {offset_str}")
        print(f"    Key Path:       {p.key_path or 'None'}")
        print(f"    New Value:      {p.new_value}")
        print(f"    Compare Value:  {p.compare_value}")
        print(f"    Patch Type:     {p.patch_type.name}")


def handle_apply(
    code_str: str,
    savefile: str,
    platform_override: str | None = None,
    profile_path: str | None = None,
    safe_mode: bool = True,
) -> None:
    """Applies code to a real save file enforcing safety rules."""
    from gamegenie_x.patch_v2 import from_legacy_patch

    save_path = Path(savefile)
    if not save_path.exists():
        print(f"Error: Save file '{savefile}' not found.", file=sys.stderr)
        return

    try:
        save_bytes = save_path.read_bytes()
    except Exception as e:
        print(f"Error reading save file: {e}", file=sys.stderr)
        return

    try:
        legacy_patch = decoder.decode(code_str, verify=False)
    except Exception as e:
        print(f"Error decoding: {e}", file=sys.stderr)
        return

    platform_profile, game_profile = load_profiles_for_patch(
        legacy_patch.platform,
        platform_override=platform_override,
        profile_path=profile_path,
        save_bytes=save_bytes,
    )

    patch_seq = from_legacy_patch(legacy_patch, platform_profile)

    try:
        applied = patch_seq.apply(
            save_path,
            platform_profile,
            game_profile=game_profile,
            safe_mode=safe_mode,
        )
        if applied:
            print(f"Successfully applied patches to {savefile}.")
        else:
            print("Patches evaluated but did not modify state (conditions mismatch/unchanged).")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


def handle_preview(
    code_str: str,
    savefile: str,
    platform_override: str | None = None,
    profile_path: str | None = None,
) -> None:
    """Previews changes to save file without modifying it."""
    from gamegenie_x.patch_v2 import from_legacy_patch
    from gamegenie_x.preview import PreviewEngine

    save_path = Path(savefile)
    if not save_path.exists():
        print(f"Error: Save file '{savefile}' not found.", file=sys.stderr)
        return

    try:
        save_bytes = save_path.read_bytes()
    except Exception as e:
        print(f"Error reading save file: {e}", file=sys.stderr)
        return

    try:
        legacy_patch = decoder.decode(code_str, verify=False)
    except Exception as e:
        print(f"Error decoding: {e}", file=sys.stderr)
        return

    platform_profile, game_profile = load_profiles_for_patch(
        legacy_patch.platform,
        platform_override=platform_override,
        profile_path=profile_path,
        save_bytes=save_bytes,
    )

    patch_seq = from_legacy_patch(legacy_patch, platform_profile)

    engine = PreviewEngine()
    results = engine.preview(patch_seq, save_bytes, game_profile or platform_profile)

    print("=== Patch Preview Results ===")
    if game_profile:
        print(f"Game Profile:      {game_profile.display_name} ({game_profile.game_id})")
    print(f"Platform Profile:  {platform_profile.name}")
    print("-" * 90)
    header_fields = (
        f"{'Field Name':<25} | {'Path/Offset':<15} | {'Old':<6} | "
        f"{'New':<6} | {'Compare':<8} | {'Safety':<6} | {'Applied'}"
    )
    print(header_fields)
    print("-" * 90)
    for r in results:
        field_name = r.field_name or "N/A"
        comp_match = (
            "N/A"
            if r.compare_matched is None
            else ("YES" if r.compare_matched else "NO")
        )
        safety = "PASS" if r.safety_passed else f"FAIL ({', '.join(r.safety_errors)})"
        applied = "YES" if r.applied else "NO"

        is_old_int = isinstance(r.old_value, int) and not isinstance(r.old_value, bool)
        is_new_int = isinstance(r.new_value, int) and not isinstance(r.new_value, bool)

        old_val_str = f"0x{r.old_value:02X}" if is_old_int else str(r.old_value)
        new_val_str = f"0x{r.new_value:02X}" if is_new_int else str(r.new_value)

        row_fields = (
            f"{field_name[:25]:<25} | {r.offset_or_key_path:<15} | "
            f"{old_val_str:<6} | {new_val_str:<6} | {comp_match:<8} | "
            f"{safety:<6} | {applied}"
        )
        print(row_fields)


def handle_sandbox(
    code_str: str,
    profile_path: str | None = None,
    platform_override: str | None = None,
) -> None:
    """Applies patches in-memory to virtual save and dumps state."""
    from gamegenie_x.game_profiles import GameProfile, load_game_profile
    from gamegenie_x.patch_v2 import from_legacy_patch
    from gamegenie_x.sandbox import SandboxEmulator

    game_profile = None
    if profile_path:
        try:
            game_profile = load_game_profile(profile_path)
        except Exception as e:
            print(f"Error loading profile {profile_path}: {e}", file=sys.stderr)
            return
    else:
        # Search profiles/ for JSON profiles
        profiles_dir = Path("profiles")
        json_files = list(profiles_dir.glob("*.json"))
        if json_files:
            try:
                game_profile = load_game_profile(json_files[0])
                print(f"Using auto-selected profile: {game_profile.display_name}")
            except Exception:
                pass

        if game_profile is None:
            # Create a mock default RPG profile
            game_profile = GameProfile(
                game_id="default_sandbox_rpg",
                display_name="Default Sandbox RPG",
                save_structure={
                    "player": {
                        "stats": {
                            "hp": 10,
                            "mp": 12,
                        },
                        "level": 14,
                    },
                    "gold": 20,
                },
                value_ranges={
                    "player.stats.hp": (1, 999),
                    "player.stats.mp": (1, 99),
                    "player.level": (1, 99),
                    "gold": (0, 999999),
                },
                flags={},
                signature=b"SAND",
                format="binary",
            )
            msg = f"No profiles found. Initialized '{game_profile.display_name}' fallback."
            print(msg)

    try:
        legacy_patch = decoder.decode(code_str, verify=False)
    except Exception as e:
        print(f"Error decoding: {e}", file=sys.stderr)
        return

    platform_profile, _ = load_profiles_for_patch(
        legacy_patch.platform, platform_override=platform_override, profile_path=profile_path
    )

    patch_seq = from_legacy_patch(legacy_patch, platform_profile)

    emu = SandboxEmulator()
    emu.load_virtual_save(game_profile)

    print("Initial Virtual State:")
    _print_state(emu.dump_state(), game_profile.format or "binary")

    try:
        modified = emu.apply_patch_sequence(patch_seq, safe_mode=True)
        print("-" * 55)
        if modified:
            print("Successfully applied patches to the virtual save.")
        else:
            print("Patches evaluated but virtual save was not modified.")
    except Exception as e:
        print(f"Error in Sandbox: {e}", file=sys.stderr)
        return

    print("-" * 55)
    print("Resulting Virtual State:")
    _print_state(emu.dump_state(), game_profile.format or "binary")


def _print_state(state: Any, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(state, indent=2))
    else:
        if isinstance(state, (bytes, bytearray)):
            print(state.hex())


def run_shell() -> None:
    """REPL interactive shell loop."""
    import shlex
    print("=== GameGenie-X Interactive Shell v2 ===")
    print("Commands: decode, apply, preview, sandbox, exit")
    print("Type 'help' or '?' for syntax details.")

    while True:
        try:
            line = input("gamegeniex> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not line:
            continue
        if line.lower() == "exit":
            break

        try:
            parts = shlex.split(line)
        except ValueError as e:
            print(f"Error parsing command: {e}", file=sys.stderr)
            continue

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in ("help", "?"):
            print("Interactive Commands Syntax:")
            print("  decode <code> [--platform <p>]")
            print("  apply <code> <savefile> [--platform <p>] [--profile <prof>] [--no-safety]")
            print("  preview <code> <savefile> [--platform <p>] [--profile <prof>]")
            print("  sandbox <code> [--profile <prof>] [--platform <p>]")
            print("  exit")
            continue

        if cmd == "decode":
            if not args:
                print("Usage: decode <code> [--platform <p>]", file=sys.stderr)
                continue
            code_str = args[0]
            override = None
            if "--platform" in args:
                idx = args.index("--platform")
                if idx + 1 < len(args):
                    override = args[idx + 1]
            handle_decode(code_str, platform_override=override)

        elif cmd == "apply":
            if len(args) < 2:
                msg = (
                    "Usage: apply <code> <savefile> [--platform <p>] "
                    "[--profile <prof>] [--no-safety]"
                )
                print(msg, file=sys.stderr)
                continue
            code_str = args[0]
            savefile = args[1]
            override = None
            prof = None
            safe_mode = True
            if "--platform" in args:
                idx = args.index("--platform")
                if idx + 1 < len(args):
                    override = args[idx + 1]
            if "--profile" in args:
                idx = args.index("--profile")
                if idx + 1 < len(args):
                    prof = args[idx + 1]
            if "--no-safety" in args:
                safe_mode = False
            handle_apply(
                code_str,
                savefile,
                platform_override=override,
                profile_path=prof,
                safe_mode=safe_mode,
            )

        elif cmd == "preview":
            if len(args) < 2:
                msg = "Usage: preview <code> <savefile> [--platform <p>] [--profile <prof>]"
                print(msg, file=sys.stderr)
                continue
            code_str = args[0]
            savefile = args[1]
            override = None
            prof = None
            if "--platform" in args:
                idx = args.index("--platform")
                if idx + 1 < len(args):
                    override = args[idx + 1]
            if "--profile" in args:
                idx = args.index("--profile")
                if idx + 1 < len(args):
                    prof = args[idx + 1]
            handle_preview(code_str, savefile, platform_override=override, profile_path=prof)

        elif cmd == "sandbox":
            if not args:
                print("Usage: sandbox <code> [--profile <prof>] [--platform <p>]", file=sys.stderr)
                continue
            code_str = args[0]
            prof = None
            override = None
            if "--profile" in args:
                idx = args.index("--profile")
                if idx + 1 < len(args):
                    prof = args[idx + 1]
            if "--platform" in args:
                idx = args.index("--platform")
                if idx + 1 < len(args):
                    override = args[idx + 1]
            handle_sandbox(code_str, profile_path=prof, platform_override=override)

        else:
            print(f"Unknown command: '{cmd}'. Type 'help' for details.", file=sys.stderr)


def main() -> None:
    """Entry point for the command-line interface."""
    parser = get_parser()
    args = parser.parse_args()

    try:
        if args.command == "encode":
            platform_parsed = parse_platform(args.platform)
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
                platform=(
                    platform_parsed
                    if isinstance(platform_parsed, Platform)
                    else Platform.UNIVERSAL
                ),
                patch_type=patch_type,
                flags=flags,
            )
            code = encoder.encode(patch)
            print(code)

        elif args.command == "decode":
            handle_decode(args.code, platform_override=args.platform)

        elif args.command == "validate":
            try:
                patch = decoder.decode(args.code)
                if getattr(args, "platform", None):
                    target_plat = parse_platform(args.platform)
                    profile = profiles.load_profile(target_plat)
                else:
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
            platform_info = parse_platform(args.platform)
            profile = profiles.load_profile(platform_info)
            print(f"Profile: {profile.name} ({profile.short_name})")
            if isinstance(profile.platform, Platform):
                print(f"Platform ID: {profile.platform.value} (Internal)")
            else:
                print(f"Platform ID: {profile.platform} (External)")
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
            if profile.io_strategy:
                print("IO Strategy:")
                print(f"  Format: {profile.io_strategy.strategy}")
                print(f"  Save Formats: {', '.join(profile.io_strategy.save_formats)}")
            if profile.fields:
                print("Example Fields:")
                for k, v in profile.fields.items():
                    print(f"  {k}: offset=0x{v.offset:X}, type={v.type}")
                    print(f"    {v.description}")

        elif args.command == "list":
            all_profiles = profiles.load_all_profiles()
            print(f"{'ID':<10} | {'Short Name':<12} | {'Name'}")
            print("-" * 55)

            # Separate internal and external profiles
            internal_profiles: list[PlatformProfile] = []
            external_profiles: list[PlatformProfile] = []
            for k, p in all_profiles.items():  # type: ignore[assignment]
                if isinstance(k, Platform):
                    internal_profiles.append(p)
                else:
                    external_profiles.append(p)

            internal_profiles.sort(key=lambda p: getattr(p.platform, "value", 0))
            external_profiles.sort(key=lambda p: str(p.platform))

            for prof in internal_profiles:
                val = getattr(prof.platform, "value", 0)
                print(f"0x{val:<8X} | {prof.short_name:<12} | {prof.name}")

            for prof in external_profiles:
                print(f"{prof.platform!s:<10} | {prof.short_name:<12} | {prof.name}")

        elif args.command == "patch":
            from gamegenie_x.patcher import apply_patch_to_file

            plat = parse_platform(args.platform)
            profile = profiles.load_profile(plat)

            try:
                patch = decoder.decode(args.code)
            except decoder.ChecksumError as e:
                print(f"Checksum Error: {e}", file=sys.stderr)
                sys.exit(2)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

            errors = profiles.validate_patch(patch, profile)
            if errors:
                print("Error: Invalid patch for platform:", file=sys.stderr)
                for err in errors:
                    print(f"- {err}", file=sys.stderr)
                sys.exit(2)

            try:
                applied = apply_patch_to_file(patch, args.file, profile)
                if applied:
                    print(f"Successfully applied patch to {args.file}")
                else:
                    print("Patch conditions not met (compare failed or unchanged).")
            except Exception as e:
                print(f"Failed to apply patch: {e}", file=sys.stderr)
                sys.exit(1)

        elif args.command == "apply":
            handle_apply(
                args.code,
                args.savefile,
                platform_override=args.platform,
                profile_path=args.profile,
                safe_mode=not args.no_safety,
            )

        elif args.command == "preview":
            handle_preview(
                args.code,
                args.savefile,
                platform_override=args.platform,
                profile_path=args.profile,
            )

        elif args.command == "sandbox":
            handle_sandbox(
                args.code,
                profile_path=args.profile,
                platform_override=args.platform,
            )

        elif args.command == "shell":
            run_shell()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
