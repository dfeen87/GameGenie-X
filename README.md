# **GameGenie‑X**  
*A modern, MIT‑licensed reinterpretation of the classic Game Genie — rebuilt for single‑player game enhancement, save‑file patching, and sandbox modifiers.*

[![CI](https://github.com/dfeen87/GameGenie-X/actions/workflows/ci.yml/badge.svg)](https://github.com/dfeen87/GameGenie-X/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-tracked-brightgreen)](https://github.com/dfeen87/GameGenie-X/actions/workflows/ci.yml) [![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/) [![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE) 

---

## **Overview**
GameGenie‑X brings the spirit of the original Game Genie into the modern era — but instead of modifying ROM bytes on a cartridge bus, GameGenie‑X applies **safe, offline, single‑player patches** to:

- save files  
- configuration files  
- memory snapshots  
- sandbox environments  

Users enter short **GameGenie‑X Codes**, which decode into deterministic patches applied through a typed, safety‑checked patch engine.

No cheating in online modes.  
No exploits.  
Just fun.

MIT license — just like the old days.

---

# **✨ What’s New in v2.0.0**
GameGenie‑X v2 is a complete architectural upgrade.  
It introduces a typed patch engine, profile system, CLI, preview mode, sandbox emulator, fuzz testing, and cross‑platform CI.

### **Major Modules**
- **Patch Engine v2** — typed patches, safety rules, deterministic decoding  
- **Profile System v2** — JSON‑based game schemas with offsets, fields, and constraints  
- **Developer Experience v2** — full CLI, interactive shell, preview mode, sandbox emulator  
- **CI & Quality v2** — cross‑platform matrix, fuzzing, strict linting, 100% docstring coverage  

Explore the modules:  
- Patch Engine v2  
- Profile System v2  
- CLI v2  
- CI & Quality v2

---

# **Core Concept**
GameGenie‑X uses a compact, custom `[Looks like the result wasn't safe to show. Let's switch things up and try something else!]` to encode a **75‑bit payload**:

- **target type** (save, config, memory)  
- **offset** or key‑path  
- **new value**  
- **optional compare value**  
- **checksum**  

A code like:

```
GX7L-9A2Q-M4VZ
```

decodes into a structured patch object that GameGenie‑X applies safely and predictably.

---

# **Code Alphabet**
```
A B C D E F G H J K L M N P R S T V W X Y Z 2 3 4 5 6 7 8 9
```

- No 0, 1, O, I (to avoid confusion)  
- Each symbol = **5 bits**  
- Dense, compact, nostalgic  

---

# **Encoding Scheme**
A standard GameGenie‑X code is **15 characters**, grouped for readability:

```
XXXXX-XXXXX-XXXXX
```

Internally, this encodes:

| Bits | Purpose |
|------|---------|
| 4    | Target type |
| 20   | Offset / key‑path |
| 16   | New value |
| 16   | Compare value |
| 15   | Checksum |

---

# **Example Code**
```
F2X9W-7K3PZ-9A4TM
```

Decodes to:

- Target: Save file  
- Offset: `0x001A4C`  
- Compare: `0x0005`  
- New value: `999`  
- Checksum: valid  

Effect:  
> Sets player’s potion count to 999 (if current count is 5).

---

# **Game Profiles**
Each supported game includes a JSON profile describing:

- save‑file structure  
- offsets  
- named fields (HP, XP, gold, etc.)  
- safety rules  
- patch templates  

Profiles live in:

```
profiles/<game>.json
```

Profiles are validated at load time and used by the patch engine and CLI.

---

# **CLI v2**
GameGenie‑X includes a full command‑line interface:

```
gamegeniex decode <code>
gamegeniex apply <code> <savefile>
gamegeniex preview <code> <profile>
gamegeniex sandbox
```

### **Interactive Mode**
```
gamegeniex shell
```

Features:
- decode  
- apply  
- preview  
- sandbox  
- exit  

---

# **Patch Preview Mode**
Preview exactly what a code will do:

- field name  
- old → new value  
- offset  
- compare value  
- safety rule results  

Perfect for modders and tinkerers.

---

# **Sandbox Emulator**
A virtual save‑file environment for safe testing:

- no risk to real data  
- deterministic patch application  
- ideal for experimentation  

---

# **Quality & CI**
GameGenie‑X v2 includes a fully modern CI pipeline:

### **Cross‑Platform**
- Linux  
- macOS  
- Windows  

### **Python Versions**
- 3.10  
- 3.11  
- 3.12  

### **Quality Gates**
- ruff strict mode  
- mypy  
- bandit  
- interrogate (100% docstring coverage)  
- fuzz testing (Hypothesis)  
- 171 passing tests  

---

# **Project Goals**
- Bring back the magic of Game Genie  
- Keep everything offline and single‑player  
- Make codes fun, shareable, nostalgic  
- Provide a clean, typed, MIT‑licensed toolkit  
- Build a modular patch engine that grows over time  

---

# **License**
MIT License — honoring the spirit of open tinkering.

---

# **Status**
**v2.0.0 — July 18, 2026**  
Patch Engine v2, Profile System v2, CLI v2, and CI v2 are production‑ready.

---

# **Acknowledgements**
Built with architectural guidance from Microsoft Copilot, coding support from Google Jules, and review assistance from ChatGPT Codex.
