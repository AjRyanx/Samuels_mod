# Release notes — Dynamic Kit & Sponsor Mod

## v0.8.0-beta.1 — “Baseline + JIT” (20 Nov 2026)

Closed beta build for PES 2021 / SP Football Life 2026 / SP Football Life 2027 with Sider 7.3.3+.

### What is in this build

- **Master League-only dynamic kits.** Exhibition, Friendlies, Kick-off, Database and Edit Mode
  continue to use the game’s original licensed kits. `KitGenerator.lua` yields to Kitserver
  outside Master League and only intercepts kit texture requests inside a verified career.
- **Baseline + JIT generation.** Season rollover generates only the lightweight `p1/g1` baseline
  for every club. Secondary slots (`p2/p3/g2`) for AI clubs are generated on demand when that
  club is scheduled in a Master League fixture. League-wide five-slot pre-generation is retired.
- **Correct work priority.** Signed deals and forced cleans run first, then baseline, then the
  user club’s seasonal rebuild, then opponent JIT. Duplicate request IDs are skipped during the
  same poll, and stale `league-*` requests are marked done on sight.
- **Renderer optimisation with identical output.** Cropped alpha compositing, scoped relief
  canvases and a fast runtime path that skips atlas/preview/mockup PNG generation. Verified
  pixel-identical atlas output and byte-identical FTEX output against pre-optimisation references.
- **Fresh-install completeness.** The installer now deploys sponsor logos, club badges, sleeve
  logos and supplier marks, regenerates `brands.txt`, and writes the background watcher launcher.
  Bulk generation is opt-in and, when used, is baseline-only (`1,g1`).
- **Regression coverage.** 45 tests pass, including Master League-only scope, season lifecycle,
  priority/JIT behaviour, duplicate requests and renderer/FTEX parity.

### Install / upgrade

1. Back up your save folder and your existing `SiderAddons` folder.
2. Extract the package and run `install.bat` (or `powershell -ExecutionPolicy Bypass -File install.ps1`).
3. Start the game through Sider and load a Master League career.
4. Optional baseline pre-cache: `python setup.py pregen` or `install.ps1 -PreGen`.

`setup.py install` and `install.ps1` both register `KitGenerator.lua` before `common\kits.lua` and
add the `livecpk\KitGenerator` root before other kit roots.

### What is intentionally excluded

The distributable ZIP does **not** contain live watcher state, logs, personal career IDs, active
generated `.ftex` kits, staging output, `.orig` backups, `__pycache__`, `.pytest_cache`, visual
audit crops or development-only pattern-lab files. These are generated locally or are specific to
the developer’s machine.

### Known beta limitations

- The first JIT generation for an opponent’s secondary slots can take a few seconds; the baseline
  cache is deliberately small.
- Python 3.10+ with Pillow and NumPy must be available for the watcher. The installer checks and
  can install the requirements from `requirements.txt`.
- Always verify in a copied career before updating a long-running Master League save.

### Integrity

Every packaged file is listed with its SHA-256 hash in `MANIFEST.sha256` inside the ZIP. The ZIP
itself has a sibling `.sha256` sidecar in the `dist/` folder.
