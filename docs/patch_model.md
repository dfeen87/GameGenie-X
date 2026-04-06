# GameGenie‑X Patch Model

The GameGenie‑X Patch Model defines how decoded codes are transformed into actionable modifications for save files, configuration files, or memory snapshots. This model is intentionally simple, deterministic, and safe, mirroring the spirit of the original Game Genie while adapting it for modern systems.

---

## Overview

A GameGenie‑X code is a compact [75‑bit payload](encoding.md) instruction.
Once decoded, it becomes a structured **patch object** that the engine applies to a specific target.

Patches are:

- deterministic  
- validated  
- reversible (via backups)  
- strictly offline and single‑player  

---

## Patch Object Schema

A decoded patch object is represented internally as:

```json
{
  "target": "save",
  "offset": 67852,
  "compare": 5,
  "value": 999,
  "checksum": "valid"
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `target` | string | target type (`"save"`, `"config"`, or `"memory"`) |
| `offset` | integer | Byte offset or hashed key‑path index |
| `compare` | integer | Expected current compare value (optional) |
| `value` | integer | New value to write |
| `checksum` | string | `"valid"` or `"invalid"` |

---

## Target Types

### **1. Save Files**
Binary or structured save files (e.g., `.dat`, `.sav`, `.bin`).

- Direct byte‑level patching  
- Type‑aware patching via [profile](profiles.md) metadata
- Automatic backup before modification  

### **2. Config Files**
Structured formats such as:

- JSON  
- YAML  
- INI  

Offsets may represent:

- key‑path hashes  
- index positions  
- mapped fields from the game [profile](profiles.md)

### **3. Memory Snapshots (Optional)**
Offline, single‑player memory regions captured from a paused process.

- No live process injection  
- No online play  
- No DRM bypass  

---

## Compare Logic

The `compare` field provides a safety check.

### Behavior

- If `compare == 0xFFFF`:  
  → No comparison required; patch always applies.

- If `compare != 0xFFFF`:  
  → Patch applies **only if** the current value matches `compare`.

### Purpose

- Prevents unintended modifications  
- Ensures patch correctness  
- Mirrors the original Game Genie’s optional compare byte  

---

## Patch Application Flow

1. **Decode code → patch object**
2. **Validate checksum**  
3. **Load target file or memory snapshot**  
4. **Check compare value (if present)**  
5. **Apply new value**  
6. **Write updated file**  
7. **Return success/failure result**

This flow is deterministic and reproducible.

---

## Safety Principles

GameGenie‑X is designed with strict ethical boundaries:

- Offline only  
- Single‑player only  
- No online cheating  
- No DRM bypass  
- No distribution of copyrighted assets  
- User‑owned data only  
- Automatic backups before patching  

These principles ensure the project remains fun, safe, and legally clean.

---

## Example Patch

**Code:**  
```
F2X9W-7K3PZ-9A4TM
```

**Decoded patch object:**

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
Sets the player’s potion count to **999**, but only if the current value is **5**.

---

## Future Extensions

- Multi‑field patches  
- Conditional patches  
- Patch bundles  
- Reversible patch logs  
- Profile‑driven type coercion  

These will be added as the engine evolves.

---

GameGenie‑X Patch Model — simple, safe, deterministic, and fun.
