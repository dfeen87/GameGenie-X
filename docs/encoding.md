# GameGenie‑X Encoding Scheme

The GameGenie‑X encoding system transforms short, human‑friendly codes into structured [patch objects](patch_model.md). This design mirrors the spirit of the original Game Genie while adapting it for modern save‑file and configuration patching.

GameGenie‑X codes are compact, deterministic, and fully self‑contained.

---

## Code Structure

A standard GameGenie‑X code is **15 characters**, grouped for readability:

```
XXXXX-XXXXX-XXXXX
```

Each character encodes **5 bits** using the [GameGenie‑X alphabet](alphabet.md).

Total size:  
**15 characters × 5 bits = 75 bits**

These 75 bits are mapped into a structured patch format.

---

## Bit Layout

The 75‑bit payload is divided into the following fields:

| Bits | Field | Description |
|------|--------|-------------|
| 4    | Target type | save, config, or memory |
| 20   | Offset / key path hash | location to patch |
| 16   | New value | value to write |
| 16   | Compare value | optional; 0xFFFF = unused |
| 15   | Checksum | validation and tamper detection |

### Why this layout?

- Compact enough to feel retro  
- Large enough to encode meaningful patches  
- Mirrors the original Game Genie’s “address + value + optional compare” pattern  
- Adds modern safety via checksum and structured target types  

---

## Encoding Process

The encoding process converts a structured [patch object](patch_model.md) into a 75‑bit binary payload, then maps that payload into the 32‑symbol [GameGenie‑X alphabet](alphabet.md).

### Steps

1. **Start with a [patch object](patch_model.md)**
   (target type, offset, new value, compare value)

2. **Pack fields into a 75‑bit buffer**  
   - bit‑pack each field according to the layout  
   - compute checksum  
   - append checksum bits

3. **Split into 5‑bit chunks**  
   75 bits → 15 chunks

4. **Map each chunk to a symbol**  
   using the GameGenie‑X alphabet

5. **Format into groups**  
   `XXXXX-XXXXX-XXXXX`

This produces a shareable, deterministic GameGenie‑X code.

---

## Decoding Process

Decoding reverses the encoding steps:

1. **Strip formatting**  
2. **Convert each symbol → 5‑bit value**  
3. **Reassemble the 75‑bit payload**  
4. **Extract fields**  
5. **Validate checksum**  
6. **Construct [patch object](patch_model.md)**

If the checksum fails, the code is rejected.

---

## Target Types

Target types are encoded in the first 4 bits:

| Value | Target |
|--------|---------|
| 0x0 | Save file |
| 0x1 | Config file |
| 0x2 | Memory snapshot |
| 0xF | Reserved |

This allows future expansion without breaking compatibility.

---

## Compare Value

The compare value is optional.

- If `compare == 0xFFFF`:  
  → No comparison required; patch always applies.

- Otherwise:  
  → Patch applies only if the current value matches.

This mirrors the original Game Genie’s optional compare byte and adds safety for modern patching.

---

## Checksum

The final 15 bits store a checksum used to:

- detect corrupted codes  
- prevent accidental modifications  
- ensure deterministic decoding  

Checksum algorithm is defined in the core engine and may evolve as the project matures.

---

## Example Encoding

**Patch Object:**

```json
{
  "target": "save",
  "offset": 67852,
  "compare": 5,
  "value": 999
}
```

**Encodes to:**

```
F2X9W-7K3PZ-9A4TM
```

(This example is conceptual. See [Demo Codes](../examples/demo_codes.md) for more.)

---

## Design Philosophy

- Short codes  
- Deterministic behavior  
- Retro aesthetic  
- Modern safety  
- MIT‑licensed openness  

The encoding scheme is the heart of GameGenie‑X — compact, expressive, and fun.
