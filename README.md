# Dynamic Kit & Sponsor Mod for PES 2021 / SP Football Life

[![Tests](https://img.shields.io/badge/tests-15%20passed-brightgreen.svg)](tests/test_ml_only_kits.py)
[![Compatibility](https://img.shields.io/badge/FL27%20%7C%20FL26%20%7C%20PES2021-Compatible-blue.svg)](AGENTS.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An immersive **Master League kit & sponsorship ecosystem** for **PES 2021** and **SP Football Life (FL26 / FL27)** running under **Sider 7.3.3+**.

In the pre-season, an executive **Sponsor Office** mod menu presents real-world commercial sponsorship offers for your club. Signing a contract dynamically rebuilds your club's **Home, Away, and Third kits** with the sponsor's chest logo, authentic kit supplier branding, and luxury streetwear fashion tailoring, while crediting the contract income directly into your in-game transfer and salary budgets.

---

```
                       ┌────────────────────────────────────────────────────────┐
                       │              IN-GAME SIDER MOD MENU (F1 / F7)          │
                       │   Sponsor Office: View Offers, Negotiate, Sign Deal   │
                       └───────────────────────────┬────────────────────────────┘
                                                   │ (writes active_deal.txt)
                                                   ▼
┌─────────────────────────────────┐       ┌────────────────────────────────────────────────────────┐
│      BUDGET INJECTION ENGINE    │       │             BACKGROUND PYTHON WATCHER                  │
│ Direct memory pointer hook adds │◄──────┤  Detects signed deals, renders 2048x2048 UV atlases,   │
│ money to ML transfer & salary   │       │  compiles direct .ftex textures to content/KitGen/     │
└─────────────────────────────────┘       └───────────────────────────┬────────────────────────────┘
                                                                      │ (serves .ftex)
                                                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                             SIDER RUNTIME INTERCEPTION (KitGenerator.lua)                        │
│                                                                                                  │
│  • Exhibition / Friendly / Edit Mode ──► Serves authentic licensed kits (Spotify Barca, etc.)    │
│  • Master League Season 1 (2026/27)  ──► User on Storyline opt-in; all AI clubs authentic       │
│  • Master League Season 2+ (2027/28+) ──► Dynamic kits & sponsors active for all 580+ clubs      │
│  • Dynamic Typography & Fonts        ──► Contrast-calibrated numbers & player names (WCAG AA)   │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Features

### 1. Master League-Only Scope & Pure Exhibition Isolation
- **Strict Mode Separation**: Dynamic kits and fictional sponsors **never** bleed into Exhibition matches, offline friendlies, Edit mode, or Database previews. 
- **Original Kits Preserved**: In Exhibition and friendly matches (`tournament_id == 65535`), every team in the world wears their original authentic licensed kits (e.g. Spotify for Barcelona, Fly Emirates for Real Madrid and Arsenal).
- Backups and authentic Kitserver GDB assets remain 100% untouched.

### 2. Authentic Storyline Mode (Player Opt-In)
- When starting a new career, your managed club wears its **authentic licensed kits** by default.
- No generic or sponsorless kit is forced upon you until you explicitly choose to sign a sponsorship agreement in the Sponsor Office.
- Once signed, your dynamic kits are activated. When your multi-year contract expires in future seasons, a clean, sponsorless dynamic kit is served during off-season / pre-season until you sign your next sponsor.

### 3. Season 1 Authentic AI Clubs & Season 2 Dynamic Immersion
- **Season 1 (2026/27)**: All 580+ CPU opponent clubs wear their original authentic licensed kits across league fixtures and continental tournaments.
- **Season 2+ (2027/28 onwards)**: Dynamic kits and multi-year AI sponsorship contracts automatically kick in across the entire football world.

### 4. Global Pre-Generation Engine (`build_all_clubs.py`)
- High-throughput parallel compiler using all CPU cores (`ProcessPoolExecutor`).
- In-memory `.ftex` encoding (BC3/DXT5 with full 12-level mipmaps) capable of generating all **587 clubs (1,761 kit textures)** in ~12 minutes.
- Simulates realistic multi-year contracts (2–3 seasons per deal) drawn from a 140-brand commercial pool.
- `--skip-existing` flag makes subsequent seasons and updates instantaneous (~1 second).

### 5. Authentic Crest & Supplier Proportions
- **Calibrated Crest Sizing**: Club badges are dynamically sized and defringed, capping area to an authentic ~77×77 px footprint over the left chest rather than ballooning across the torso.
- **Official Kit Suppliers**: Authentic supplier placement (Nike, Adidas, Puma, Umbro, Kappa, Mizuno, Macron, Hummel, Castore) with authentic dimensions (~90×48 px) over the right chest.

### 6. Linear Seasonal Progression Engine (Zero Repetition)
- Deterministic seasonal progression ensures clubs never wear consecutive duplicate designs across 10+ seasons.
- High-fashion pattern library includes:
  - **Pattern 207**: Asymmetric Crest-Aligned Hechter Stripe.
  - Bespoke Heritage: Arsenal white sleeves, Ajax center panel, Celtic hoops, Boca chestband, River sash, Milan/Inter/Juve stripes.
  - Modern Streetwear: Carrara marble jacquards, houndstooth, kinetic geometry, engineered cuff/collar tipping, and contrast shorts/socks.

### 7. High-Contrast Typography & Dynamic Squad Numbers
- Dynamic shirt back numbers, shorts leg numbers, and player names automatically calibrated against the kit body and back stripes.
- Guarantees WCAG AA/AAA contrast ratios (> 4.5:1) for maximum on-pitch legibility under all stadium lighting conditions.
- Full support for Goalkeeper kits (P1, P2, P3, G1, G2).

### 8. Sponsor Office (Sider Mod Menu)
- Executive dark-mode dashboard inside Sider Mod Menu (press **F1**, or **F7** for classic overlay).
- View multi-year offers, negotiation options, signing bonuses, and early contract termination clauses.
- Instant budget crediting: contracts add real transfer and salary budget into your career save.

---

## Repository Structure

```
├── modules/
│   ├── KitGenerator.lua        # Sider runtime interception & Sponsor Office UI
│   └── KGProbe.lua             # Read-only memory & flow diagnostic probe
├── generator/
│   ├── build_all_clubs.py      # High-speed multi-core bulk compiler for all 587 clubs
│   ├── build_kit.py            # Single-club render & pack CLI
│   ├── kit_dna.py              # Seasonal progression engine & bespoke heritage patterns
│   ├── kit_patterns.py         # Vector pattern library (Hechter, jacquards, stripes)
│   ├── kit_regions.py          # UV coordinate mapping & crest/supplier validation
│   ├── kit_render.py           # 2048x2048 RGBA kit atlas painter
│   ├── kit_fonts.py            # Dynamic contrast typography & squad number generator
│   ├── ftex_io.py              # In-memory BC3/DXT5 FTEX texture encoder
│   ├── watch_signed.py         # Background service rebuilding kits on contract signing
│   ├── setup_watcher.py        # Automated deployment script for Sider
│   └── clubs.csv               # 587-club database with hex colors, names, and tiers
├── content/
│   └── KitGenerator/
│       ├── logos/              # 140 commercial sponsor brand logos (colour + white)
│       ├── badges/             # Club crest assets
│       ├── suppliers/          # Kit manufacturer logos (Nike, Adidas, Puma, etc.)
│       └── brands.txt          # Brand registry
├── tests/
│   ├── test_ml_only_kits.py    # 15 integration tests for ML isolation & season rules
│   ├── test_font_contrast.py   # WCAG typography contrast verification
│   └── test_variety_10000_kits.py # 10,000-kit Monte Carlo test for zero duplicates
├── docs/
│   ├── INSTALL.md              # Detailed step-by-step installation guide
│   ├── ARCHITECTURE.md         # Technical architecture & Sider memory hook specs
│   └── SEASON_LIFECYCLE.md     # Career progression & AI contract lifecycle
└── AGENTS.md                   # Strict development & architecture guidelines
```

---

## Quick Start: 1-Click Automated Installation

We provide an automated installer that checks all prerequisites, scaffolds runtime directories, configures `sider.ini`, and synchronizes assets automatically:

### Option A: Windows 1-Click (Double-Click)
Simply double-click **`install.bat`** in the mod directory.

### Option B: PowerShell
```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

### Option C: Python CLI Setup
```bash
python setup.py install      # Syncs files & registers sider.ini hooks
python setup.py verify       # Verifies Python, Sider hooks, textures & deals
python setup.py test         # Runs full regression test suite
python setup.py pregen       # Runs world kit pre-generation
```

---

## Manual Installation

---

## How It Works In-Game

1. **Launch Game**: Start your game via `FL_2027 start.exe` (or `sider.exe`).
2. **Start Master League**: Start or load a Master League career with any team.
3. **Open Sponsor Office**: Press **F1** to open the Sider Mod Menu and navigate to **Sponsor Office** (or press **F7** for the classic overlay).
4. **Sign a Sponsor**: Browse offers, negotiate terms, and sign a contract.
5. **Dynamic Kit Deployed**: The background watcher instantly compiles your new Home, Away, and Third kits with the sponsor's logo and credits your transfer budget!
6. **AI Opponents**: In Season 1, your opponents wear their authentic licensed kits. From Season 2 onwards, their dynamic kits activate automatically.

---

## Running the Automated Test Suite

To verify system integrity and Master League isolation:

```bash
pip install lupa pillow numpy
python tests/test_ml_only_kits.py
python tests/test_font_contrast.py
python tests/test_variety_10000_kits.py
```

All 15 integration tests run against an isolated virtual Sider environment, confirming:
- Exhibition friendlies (`tournament_id == 65535`) strictly yield `nil` (authentic kits).
- Edit mode strictly yields `nil` (authentic kits).
- Season 1 AI opponents strictly wear authentic kits.
- Season 2+ AI opponents serve dynamic kits.
- Player storyline opt-in correctly gates dynamic kits.
- Dynamic contrasting squad numbers & goalkeeper kits function seamlessly.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
