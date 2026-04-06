# GameGenie‑X Demo Codes

This document provides example GameGenie‑X codes and their decoded meanings.  
These examples are conceptual and intended to demonstrate how the encoding scheme maps to real gameplay modifications.

All codes follow the standard 15‑character format:

```
XXXXX-XXXXX-XXXXX
```

---

## Example 1 — Max Potions

**Code:**  
```
F2X9W-7K3PZ-9A4TM
```

**Decoded Patch:**

```json
{
  "target": "save",
  "offset": 67852,
  "compare": 5,
  "value": 999,
  "checksum": "valid"
}
```

**Effect:**  
Sets the player's potion count to **999**, but only if the current value is **5**.

---

## Example 2 — Max Gold

**Code:**  
```
W7R2M-X9F4A-2T3PV
```

**Decoded Patch:**

```json
{
  "target": "save",
  "offset": 2048,
  "compare": 0xFFFF,
  "value": 999999,
  "checksum": "valid"
}
```

**Effect:**  
Sets the player's gold to **999,999** unconditionally.

---

## Example 3 — Infinite Health

**Code:**  
```
K9V3T-2A7LW-8R5MX
```

**Decoded Patch:**

```json
{
  "target": "save",
  "offset": 1024,
  "compare": 100,
  "value": 9999,
  "checksum": "valid"
}
```

**Effect:**  
If the player's current health is **100**, set it to **9999**.

---

## Example 4 — Unlock All Skills

**Code:**  
```
M4Z8R-7W2KP-3X9LT
```

**Decoded Patch:**

```json
{
  "target": "config",
  "offset": 45012,
  "compare": 0xFFFF,
  "value": 1,
  "checksum": "valid"
}
```

**Effect:**  
Sets the "skills_unlocked" flag to **true** in the config file.

---

## Example 5 — Set XP to 1,000,000

**Code:**  
```
R8T2W-5K9LM-7A3VX
```

**Decoded Patch:**

```json
{
  "target": "save",
  "offset": 112940,
  "compare": 0xFFFF,
  "value": 1000000,
  "checksum": "valid"
}
```

**Effect:**  
Sets the player's XP to **1,000,000**.

---

## Notes

- These codes are **illustrative**, not tied to a real game profile.  
- Actual offsets and values depend on each game's profile.  
- All examples follow the official 75‑bit encoding structure.  
- Checksum values shown as `"valid"` for clarity.

---

GameGenie‑X demo codes show how compact, expressive, and fun the system can be.

Just tell me where you want to go next — the wave is still rolling strong.
