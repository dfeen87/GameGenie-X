# GameGenie‑X Code Alphabet

The GameGenie‑X alphabet is a custom 32‑symbol character set used to encode the 75‑bit payload of every GameGenie‑X code.  
It is designed for clarity, compactness, and a retro‑inspired aesthetic that echoes the original Game Genie while remaining fully modern.

---

## Alphabet

GameGenie‑X uses the following 32‑symbol alphabet:

```
A B C D E F G H J K L M N P R S T V W X Y Z 2 3 4 5 6 7 8 9
```

This alphabet intentionally excludes ambiguous characters such as:

- `0` (zero)  
- `1` (one)  
- `O` (letter O)  
- `I` (capital i)

This ensures codes are easy to read, type, and share without confusion.

---

## Symbol Mapping

Each symbol corresponds to a **5‑bit value** (0–31).  
This mapping is deterministic and defined in the core encoder.

Example mapping (conceptual):

| Symbol | Value |
|--------|--------|
| A | 0 |
| B | 1 |
| C | 2 |
| ... | ... |
| 9 | 31 |

The exact mapping table is implemented in `src/core/encoder.*` and must remain stable to preserve code compatibility.

---

## Why 32 Symbols?

Using 32 symbols gives each character a 5‑bit capacity:

- 2⁵ = 32  
- 15 characters × 5 bits = **75 bits**

This aligns perfectly with the GameGenie‑X encoding scheme:

- 4 bits — target type  
- 20 bits — offset / key‑path hash  
- 16 bits — new value  
- 16 bits — compare value  
- 15 bits — checksum  

The alphabet is the backbone of this compact representation.

---

## Design Principles

The alphabet was chosen to satisfy several constraints:

### **1. Readability**
Characters must be visually distinct to avoid mis‑typing.

### **2. Retro Aesthetic**
The alphabet evokes the feel of classic cheat devices and cartridge‑era tooling.

### **3. Encoding Efficiency**
32 symbols → 5 bits per character → compact 75‑bit payload.

### **4. Stability**
Once defined, the alphabet does not change.  
This ensures all GameGenie‑X codes remain valid indefinitely.

---

## Example Usage

A GameGenie‑X code such as:

```
GX7LW-9A2QF-M4VZ8
```

is simply a human‑friendly representation of a 75‑bit binary payload encoded using this alphabet.

---

## Future Extensions

The alphabet is intentionally fixed and will not change.  
However, future versions of GameGenie‑X may introduce:

- alternate alphabets for stylistic variants  
- themed alphabets for specific games  
- visual encodings (QR‑style) for sharing codes  

These will always remain optional and backward‑compatible.

---

The GameGenie‑X alphabet is simple, stable, and expressive — the foundation of every code in the system.

