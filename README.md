# **GameGenie‑X**  
*A modern, MIT‑licensed reinterpretation of the classic Game Genie — rebuilt for single‑player game enhancement, save‑file patching, and sandbox modifiers.*

---

## **Overview**
GameGenie‑X brings the spirit of the original Game Genie into the modern era.  
Instead of patching ROM bytes on a cartridge bus, GameGenie‑X applies **safe, offline, single‑player modifications** to:

- save files  
- configuration files  
- memory snapshots (optional)  
- sandbox parameters  

Users enter short **GameGenie‑X Codes**, which decode into deterministic patches applied to supported games.

No cheating in online modes.  
No exploits.  
Just fun.

MIT license — just like the old days.

---

## **Core Concept**
GameGenie‑X uses a compact, custom alphabet to encode:

- **target** (save file, config block, memory region)  
- **offset / key path**  
- **new value**  
- **optional compare value**  
- **checksum**  

A code like:

```
GX7L-9A2Q-M4VZ
```

decodes into a structured patch that GameGenie‑X applies safely and predictably.

---

## **Code Alphabet**
GameGenie‑X uses a 32‑symbol alphabet designed for readability and compactness:

```
A B C D E F G H J K L M N P R S T V W X Y Z 2 3 4 5 6 7 8 9
```

- No 0, 1, O, I (to avoid confusion)  
- Each symbol = **5 bits**  
- Codes pack dense binary data into short, fun sequences  

---

## **Encoding Scheme**
A standard GameGenie‑X code is **15 characters**, grouped for readability:

```
XXXXX-XXXXX-XXXXX
```

Internally, this encodes **75 bits**:

| Bits | Purpose |
|------|---------|
| 4    | Target type (save, config, memory) |
| 20   | Offset or hashed key‑path |
| 16   | New value |
| 16   | Compare value (optional; 0xFFFF = unused) |
| 15   | Checksum / validation |

This mirrors the original Game Genie’s philosophy:

> “Short code → deterministic patch → fun gameplay change.”

---

## **Example Code (Conceptual)**
**Code:**  
```
F2X9W-7K3PZ-9A4TM
```

**Decodes to:**  
- Target: Save file  
- Offset: `0x001A4C`  
- Compare: `0x0005` (only patch if current value is 5)  
- New value: `0x03E7` (999 decimal)  
- Checksum: valid  

**Effect:**  
> Sets player’s potion count to 999 (if current count is 5).

---

## **Game Profiles**
Each supported game includes a profile describing:

- save‑file structure  
- known offsets  
- named fields (HP, XP, gold, etc.)  
- code templates  
- safety rules  

Profiles live in:

```
profiles/<game_name>.json
```

---

## **Project Goals**
- Bring back the magic of Game Genie in a modern, ethical way  
- Keep everything offline and single‑player  
- Make codes fun, shareable, and nostalgic  
- Provide a clean, MIT‑licensed toolkit for modders and tinkerers  
- Build a modular patch engine that can grow over time  

---

## **License**
This project is licensed under the **MIT License**, honoring the spirit of the original Game Genie era of open tinkering and creativity.

---

## **Status**
Early prototype.  
Encoding engine + patch engine under active development.
