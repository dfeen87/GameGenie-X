# GameGenie‑X Encoding Scheme

GameGenie‑X uses a compact 75‑bit encoding format inspired by the original Game Genie, adapted for modern save‑file and configuration patching.

## Code Structure

A standard code is 15 characters, grouped for readability:

XXXXX-XXXXX-XXXXX


Each character encodes 5 bits using the GameGenie‑X alphabet.

Total: **15 chars × 5 bits = 75 bits**

## Bit Layout

| Bits | Field | Description |
|------|--------|-------------|
| 4    | Target Type | save, config, memory |
| 20   | Offset / Key Path Hash | location to patch |
| 16   | New Value | value to write |
| 16   | Compare Value | optional; 0xFFFF = unused |
| 15   | Checksum | validation and tamper detection |

## Philosophy

Short code → deterministic patch → fun, safe gameplay changes.

This mirrors the original Game Genie’s spirit while remaining fully modern and ethical.
