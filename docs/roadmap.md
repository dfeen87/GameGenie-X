# GameGenie‑X Roadmap

This roadmap outlines the planned evolution of GameGenie‑X.  
It is intentionally high‑level, exploratory, and subject to refinement as the project matures.

GameGenie‑X is a modern, MIT‑licensed reinterpretation of the classic Game Genie, focused on safe, offline, single‑player game enhancement through encoded patch codes.

---

## Phase 1 — Foundation

**Goal:** Establish the core identity, documentation, and scaffolding.

- Repository structure created
- MIT license applied
- Initial documentation drafted:
  - Encoding scheme
  - Alphabet
  - Patch model
  - Profiles
- Example profile added
- Example codes documented
- Early design of the encoding/decoding engine

This phase defines the conceptual backbone of the project.

---

## Phase 2 — Core Engine

**Goal:** Implement the essential logic that makes GameGenie‑X functional.

- Encoder stub → full implementation
- Decoder stub → full implementation
- Checksum algorithm
- [patch object](patch_model.md) validation
- Patch application for binary save files
- Profile loader and type‑aware field handling
- Automatic save‑file backups
- Error handling and safety checks

This phase brings the code system to life.

---

## Phase 3 — Tooling & CLI

**Goal:** Provide a usable interface for players and modders.

- Command‑line interface (CLI)
- Code validator (`ggx validate CODE`)
- Code generator (`ggx generate FIELD VALUE`)
- Save‑file inspector
- Profile inspector
- Human‑readable patch logs

This phase makes GameGenie‑X practical and accessible.

---

## Phase 4 — Expansion

**Goal:** Broaden the system’s capabilities and game support.

- Memory snapshot support (offline only)
- JSON/YAML/INI config patching
- Multi‑field patches
- Patch bundles
- Community [profile](profiles.md) format
- Profile versioning
- Auto‑generated profiles via save‑file scanning

This phase expands the ecosystem around the core engine.

---

## Phase 5 — Frontend & UX

**Goal:** Build a friendly interface for non‑technical users.

- GUI frontend (desktop app)
- Drag‑and‑drop save‑file patching
- Code entry UI
- Profile browser
- Patch preview and diff view

This phase makes GameGenie‑X approachable for everyone.

---

## Phase 6 — Polishing & Stability

**Goal:** Mature the project into a stable, well‑documented toolkit.

- Extensive testing
- Documentation expansion
- Example videos and demos
- Performance tuning
- Optional plugin system
- Community contributions

This phase focuses on refinement and long‑term maintainability.

---

## Guiding Principles

- Offline only  
- Single‑player only  
- No DRM bypass  
- No online cheating  
- User‑owned data only  
- MIT‑licensed openness  
- Nostalgia with modern engineering discipline  

These principles guide every phase of development.

---

GameGenie‑X is a long‑term, exploratory project.  
This roadmap will evolve as the engine, community, and ideas grow.
