# Technical Architecture & System Design

This document details the internal architecture, memory interception mechanisms, texture encoding pipeline, and runtime state management of the **Dynamic Kit & Sponsor Mod**.

---

## 1. System Architecture Overview

The mod operates as a hybrid architecture between a **C/Lua JIT Sider runtime module** and an **asynchronous Python graphics pipeline**.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PES 2021 / Football Life                        │
│                                                                        │
│   Kitserver (common\kits.lua) ◄──── Sider Hook (KitGenerator.lua)     │
│             │                                    │                     │
│   Loads authentic GDB kits                       │ Intercepts ML match │
│   (content/kits/...)                             │ texture requests    │
└──────────────────────────────────────────────────┼─────────────────────┘
                                                   │
                                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    KitGenerator.lua Interception Logic                 │
│                                                                        │
│   is_in_ml(ctx) == false  ────────► return nil (falls back to GDB)     │
│   tournament_id == 65535  ────────► return nil (Exhibition friendly)   │
│   in_edit_mode == true    ────────► return nil (Edit mode)             │
│   SEASON < 2028 & AI club ────────► return nil (Season 1 authentic)    │
│   tid == cid & !opted_in  ────────► return nil (Player storyline rule) │
│                                                                        │
│   Otherwise:                                                           │
│   content/KitGenerator/active/u<id>p<slot>.ftex ──► return rel_path    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Sider Interception Hooks

`KitGenerator.lua` hooks two core Sider events:
- `livecpk_make_key(ctx, filename)`
- `livecpk_get_filepath(ctx, filename, key)`

### 2.1 Mode Detection (`is_in_ml(ctx)`)
To guarantee that kits never bleed outside of career mode, `is_in_ml(ctx)` evaluates four independent barriers:
1. `STATE.in_edit_mode == false`: Set by `set_home_team_for_kits(ctx, team, edit_mode)` when the game enters Edit Mode.
2. `ctx.tournament_id ~= 65535`: The engine's universal Exhibition match friendly flag.
3. Flow Script Tracking: Monitors UI flow transitions from game JSON script events (`common\script\flow\ML\...` vs `\Exhibition\`, `\Top\`, `\Edit\`, `\BL\`).
4. Live Calendar Memory: Validates that an active Master League date pointer is populated in memory (`game_date()`).

### 2.2 Texture Key Resolution
When the game requests kit textures:
- Pattern: `[ku]0*([0-9]+)([pg])([1-3])([_%a%d]*)%.ftex`
- Match target:
  - `p1, p2, p3`: Outfield Home, Away, and Third kits.
  - `g1, g2`: Goalkeeper Home and Away kits.
  - Suffixes: `_b` / `_back` (shirt back number), `_l` / `_leg` (shorts number), `_n` / `_name` (player name font).
- Target location: `content/KitGenerator/active/u<tid><slot_type><slot><suffix>.ftex`.
- If the file exists on disk and passes the seasonal and storyline gates, Sider returns the relative path, causing the PES 2021 engine to bind the dynamic texture instead of the static disk texture.

---

## 3. Asynchronous Graphics Pipeline

### 3.1 The Fast FTEX Direct Encoder (`ftex_io.py`)
PES 2021 kit textures use Konami's proprietary `.ftex` container format:
- **Pixel Format**: BC3 / DXT5 (Format 4).
- **Dimensions**: $2048 \times 2048$ pixels.
- **Mipmap Chain**: 12 levels ($2048 \times 2048$ down to $1 \times 1$).
- **Chunk Compression**: Zlib payload chunks with 32-byte headers.

Earlier versions decoded `.ftex` into DDS and converted via disk round-trips. The current engine encodes frames in memory:
1. Generates 12 mip levels in Pillow using `Image.BILINEAR`.
2. Encodes each level directly to BC3 block byte payloads.
3. Packages the FTEX header, mip table, and chunk headers with `zlib.compress(chunk, 1)` directly into bytes.
4. Achieves throughput of ~0.4s per kit with 100% byte-identical PES engine compatibility.

### 3.2 Dynamic Pattern & Tailoring Synthesis (`kit_render.py`)
1. **Island Masks**: Uses high-precision binary masks for body front, body back, sleeves, cuffs, shorts, socks, and collar.
2. **Crest Calibration**: Resizes harvested crests to a maximum bound of $85 \times 85$ px and target area of $6,000\text{ px}^2$, applying an alpha unmatted defringing algorithm to remove halo artifacts.
3. **Supplier Positioning**: Resizes manufacturer logos (Nike, Adidas, Puma, etc.) to a maximum bound of $90 \times 48$ px and target area of $3,600\text{ px}^2$.
4. **Collision Avoidance**: Coordinates between crest, supplier, and chest sponsor are UV-validated to prevent overlap.
5. **Dynamic Typography**: Reads the shirt body and back striping colors to calculate luminance and assigns high-contrast typography satisfying WCAG AA standards.

---

## 4. Memory Pointers & Budget Crediting

When a user signs a deal in the Sponsor Office:
1. The deal terms (yearly value, duration, bonus) are written to `active_deal.txt`.
2. The game process reads the manager's transfer budget through an instruction pointer hooked in `KitGenerator.lua`.
3. The budget value (stored as an unsigned 32-bit integer in units of EUR 100) is updated in memory:
   $$\text{Transfer Budget} \mathrel{+}= \lfloor (\text{Deal Value} \times 0.70) / 100 \rfloor$$
   $$\text{Salary Budget} \mathrel{+}= \lfloor (\text{Deal Value} \times 0.30) / 100 \rfloor$$
4. Payments are recorded in `paid.txt` to prevent duplicate crediting within the same season.

---

## 5. Career Identity & Saturated Offers Engine

### 5.1 Memory-Synchronized Career Identity
Rather than relying on a static machine UUID in `career.txt`, `KitGenerator.lua` dynamically reads the active Master League manager context block at runtime:
- Extracts human-managed team ID `tid`, calendar year `y`, and context header bytes `raw`.
- Hashes context metadata to form a deterministic, persistent save identifier:
  $$\text{CAREER} = \text{ml\_}\langle\text{tid}\rangle\text{\_}\langle\text{hash}(raw)\rangle$$
- Automatically detects save switches and club changes, isolating negotiation states, contract counter-offers, and deal histories per career slot without disk contamination.

### 5.2 Saturated 26,000+ Sponsor Deal Database
- Pre-calculated commercial sponsorship database across **all 587 clubs** for 9 full seasons (2027–2035), containing **26,415 curated offers**.
- Enforces multi-year brand diversity constraints (clubs never see the same sponsor consecutive seasons).
- **O(1) Indexed Lookups**: `load_offers()` indexes entries by club ID (`OFFERS[cid]`), reducing UI frame search time from $O(N)$ linear scans across 26,000 records to an instant microsecond lookup.

---

## 6. Goalkeeper Synthesis & Pre-Generation

### 6.1 Expanded High-Vis Streetwear Aesthetics
- Goalkeeper slots (`g1`, `g2`) utilize an expanded 28-pattern streetwear & 90s heritage pool (`POOL_GK_STREETWEAR`).
- Evaluates Euclidean RGB color distance against outfield primary, secondary, and alternate kits to prevent visual clash:
  $$\Delta C(\text{GK}, \text{Outfield}) \ge 130$$
- Color palettes feature vibrant volt, hyper crimson, emerald teal, electric blue, and obsidian contrast trims.

### 6.2 Full 5-Slot World Caching
- `build_all_clubs.py` operates across all 5 slots (`1, 2, 3, g1, g2`), compiling **2,935 textures** directly into `content/KitGenerator/active/`.
- Eliminates all in-match synthesis latency for goalkeepers and outfield squads across all 580+ clubs in the world.

---

## 7. 1-Click Installer Architecture (`install.ps1` / `setup.py`)

- Automated pre-flight checks: Python 3.8+, Pillow, NumPy, Sider directories.
- Automated `sider.ini` AST inspection & hook placement (strictly positioned before `common\kits.lua`).
- Directory scaffolding and atomic asset synchronization.
- Built-in verification CLI (`python setup.py verify`) providing real-time health checks on textures, deals, and memory modules.
