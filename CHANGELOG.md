# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-04-06

### Added
- 75-bit unified encoding scheme with 15-symbol code strings
- 32-symbol Crockford-inspired alphabet (ambiguity-free)
- CRC-11 checksum for transcription error detection
- Platform profiles: NES, SNES, Genesis, Game Boy, Game Gear
- Encoder: Patch to code string with optional validation
- Decoder: Code string to Patch with optional checksum verification
- CLI with encode, decode, validate, and info subcommands
- Comprehensive test suite with round-trip coverage for all platforms
- PEP 561 typed package with strict mypy configuration
