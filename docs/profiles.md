# GameGenie‑X Game Profiles

GameGenie‑X uses **Game Profiles** to understand how to safely modify a specific game's save files, configuration files, or memory snapshots. Profiles provide structure, metadata, and field definitions that allow encoded patches to be applied deterministically.

Profiles live in the `profiles/` directory and are written in JSON for clarity and portability.

---

## Purpose of Profiles

Profiles define:

- where a game's save or config files are located  
- how those files are structured  
- which fields can be safely modified  
- the data types of those fields  
- the offsets or key‑paths associated with each field  
- optional constraints or safety rules  

This allows GameGenie‑X to apply patches **without guessing**, ensuring safe and predictable behavior.

---

## Profile Format

A profile is a JSON document with the following structure:

```json
{
  "game": "Example Game",
  "version": "1.0",
  "save_path": "saves/save1.dat",
  "format": "binary",
  "fields": {
    "potions": {
      "offset": 67852,
      "type": "u16",
      "description": "Number of healing potions"
    },
    "xp": {
      "offset": 112940,
      "type": "u32",
      "description": "Player experience points"
    }
  }
}
```

### Required Fields

| Field | Description |
|-------|-------------|
| `game` | Human‑readable game name |
| `version` | Game version the profile applies to |
| `save_path` | Relative or absolute path to the save file |
| `format` | `"binary"`, `"json"`, `"yaml"`, `"ini"` |
| `fields` | Dictionary of patchable fields |

### Field Entry Structure

Each field entry contains:

- `offset` — byte offset or hashed key‑path index  
- `type` — data type (`u8`, `u16`, `u32`, `i32`, `float`, etc.)  
- `description` — optional human‑readable explanation  

---

## Supported File Formats

### **Binary Saves**
- Direct byte‑level patching  
- Offsets must be accurate  
- Types determine how many bytes to read/write  

### **JSON / YAML Configs**
- Offsets may represent hashed key‑paths  
- Engine resolves the actual path via profile metadata  

### **INI / Key‑Value Files**
- Fields map to specific keys  
- Engine updates values directly  

---

## Adding a New Game Profile

To add support for a new game:

1. Create a new JSON file in `profiles/`  
   Example: `profiles/skyrim.json`

2. Document:
   - save file path  
   - file format  
   - known offsets or key‑paths  
   - field types  
   - optional descriptions  

3. Add at least one example code to `examples/demo_codes.md`

4. Test the profile using the patch engine once implemented

5. Update the README if the game becomes a flagship example

---

## Example: Minimal Profile

```json
{
  "game": "Retro Quest",
  "version": "1.0",
  "save_path": "saves/slot1.bin",
  "format": "binary",
  "fields": {
    "health": { "offset": 1024, "type": "u16" },
    "gold": { "offset": 2048, "type": "u32" }
  }
}
```

This is enough for GameGenie‑X to:

- decode a code  
- map it to a field  
- apply a patch safely  

---

## Safety Considerations

Profiles must:

- never reference online or multiplayer data  
- avoid modifying DRM‑protected regions  
- only target user‑owned files  
- include accurate offsets to prevent corruption  
- specify types to avoid misaligned writes  

GameGenie‑X enforces these rules automatically.

---

## Future Extensions

- Profile versioning  
- Auto‑generated profiles via save‑file scanning  
- Community‑maintained profile registry  
- Field constraints (min/max values)  
- Multi‑file profiles for complex games  

---

Game Profiles are the backbone of GameGenie‑X — they make patches safe, predictable, and fun.
