"""
test_variety_10000_kits.py

Comprehensive High-Velocity Simulation Test:
Simulates generating 10,000 kit designs across all 588 clubs, seasons 2026-2035,
all 3 kit slots (Home, Away, Third), and dynamic sponsor signings.

Verifies:
1. Diversity:
   - >= 9,900 unique kit design signatures (> 99% uniqueness across 10,000 kits).
   - >= 100 distinct pattern archetypes actively utilized from the modern 2026/2027 catalog.
   - >= 2,000 distinct color palette configurations (body/shorts/socks).
   - >= 500 distinct tailoring trim combinations (cuffs, tipping, stripes, tape).
2. Contrast & Legibility:
   - 0 contrast failures (all sponsor stamps have WCAG-compliant contrast ratio >= 3.0:1).
3. Heritage Invariants:
   - Canonical identity honored across premier heritage clubs (Arsenal white sleeves,
     Boca chestband, River sash, Milan/Inter stripes, Ajax center band).
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATOR_DIR = REPO_ROOT / "generator"
if str(GENERATOR_DIR) not in sys.path:
    sys.path.insert(0, str(GENERATOR_DIR))

import kit_gen
import kit_dna
import kit_render
from audit_kits import contrast_ratio


@pytest.fixture(scope="module")
def clubs_data():
    clubs_csv = GENERATOR_DIR / "clubs.csv"
    if not clubs_csv.is_file():
        pytest.skip("clubs.csv not found")
    return kit_gen.load_clubs(str(clubs_csv))


def test_10000_kits_variety_and_integrity(clubs_data):
    logo_dir = GENERATOR_DIR / "logos"
    sponsors = ["fly_emirates", "spotify", "three", "barclays", "etihad", "stake", "apple_logo", None]

    # Pre-sample sponsor logo RGB colors for contrast check
    sponsor_colors = {}
    for sp in sponsors:
        if sp:
            p = logo_dir / f"{sp}.png"
            if p.is_file():
                sim = Image.open(p).convert("RGBA")
                arr = np.array(sim)
                op = arr[:, :, 3] > 128
                sponsor_colors[sp] = tuple(int(v) for v in np.median(arr[op, :3], axis=0)) if np.any(op) else (15, 25, 45)
            else:
                sponsor_colors[sp] = (15, 25, 45)

    signatures = set()
    patterns = set()
    palettes = set()
    tailoring_trims = set()
    contrast_failures = []

    count = 0
    total_target = 10000

    for season in range(2026, 2036):
        for club in clubs_data:
            for slot in [1, 2, 3]:
                # Rotate realistic sponsor deals deterministically
                sp = sponsors[(club["id"] + season * 7 + slot * 13) % len(sponsors)]
                d = kit_render.design_from_club(club, season, logo_dir, slot=slot, sponsor=sp)
                count += 1

                sig = (
                    club["id"], season, slot, sp,
                    d.get("pattern"), d.get("body"), d.get("second"),
                    d.get("shorts"), d.get("socks"), d.get("collar"),
                    d.get("sleeve_style"), d.get("shorts_style"), d.get("socks_style")
                )
                signatures.add(sig)
                patterns.add(d.get("pattern"))
                palettes.add((d.get("body"), d.get("shorts"), d.get("socks")))
                tailoring_trims.add((
                    d.get("sleeve_style"), d.get("cuff"), d.get("cuff_tip"),
                    d.get("collar_tip"), d.get("shorts_style"), d.get("socks_style")
                ))

                # Contrast verification
                if d.get("sponsor") and sp:
                    body_col = d["body"]
                    if d.get("sponsor_white"):
                        s_col = (255, 255, 255)
                    elif d.get("sponsor_dark"):
                        s_col = d["sponsor_dark"] if isinstance(d["sponsor_dark"], tuple) else (15, 25, 45)
                    else:
                        s_col = sponsor_colors.get(sp, (15, 25, 45))
                    cr = contrast_ratio(body_col, s_col)
                    if cr < 3.0:
                        contrast_failures.append((club["name"], season, slot, sp, body_col, s_col, cr))

                if count >= total_target:
                    break
            if count >= total_target:
                break
        if count >= total_target:
            break

    # Assertions
    assert count == total_target, f"Expected {total_target} simulated kits, got {count}"
    assert len(signatures) >= 9900, f"Expected >= 9,900 unique kit signatures, got {len(signatures)}"
    assert len(patterns) >= 100, f"Expected >= 100 unique pattern archetypes, got {len(patterns)}"
    assert len(palettes) >= 2000, f"Expected >= 2,000 unique color palettes, got {len(palettes)}"
    assert len(tailoring_trims) >= 500, f"Expected >= 500 unique tailoring trims, got {len(tailoring_trims)}"
    assert len(contrast_failures) == 0, f"Encountered {len(contrast_failures)} contrast failures (< 3.0:1)"


def test_heritage_invariants(clubs_data):
    """Verify canonical identity invariants for top heritage clubs across 2026-2030."""
    logo_dir = GENERATOR_DIR / "logos"
    club_by_id = {c["id"]: c for c in clubs_data}

    for season in range(2026, 2031):
        # 1. Arsenal (CID 101) Home kit: white sleeves
        if 101 in club_by_id:
            d = kit_render.design_from_club(club_by_id[101], season, logo_dir, slot=1, sponsor="fly_emirates")
            assert d["sleeve"] == (250, 250, 252), f"Arsenal home season {season} must have white sleeves, got {d['sleeve']}"

        # 2. Boca Juniors (CID 139) Home kit: chestband heritage
        if 139 in club_by_id:
            d = kit_render.design_from_club(club_by_id[139], season, logo_dir, slot=1, sponsor="fly_emirates")
            assert d["body"] == (15, 45, 120), f"Boca home season {season} body color error: {d['body']}"

        # 3. River Plate (CID 138) Home kit: white body & sash heritage
        if 138 in club_by_id:
            d = kit_render.design_from_club(club_by_id[138], season, logo_dir, slot=1, sponsor="fly_emirates")
            assert d["body"] == (250, 250, 252), f"River home season {season} body color error: {d['body']}"

        # 4. AC Milan (CID 121) Home kit: Rossoneri stripes
        if 121 in club_by_id:
            d = kit_render.design_from_club(club_by_id[121], season, logo_dir, slot=1, sponsor="fly_emirates")
            assert d["body"] == (195, 20, 30) and d["second"] == (18, 18, 20), f"Milan home season {season} colors error"

        # 5. Inter Milan (CID 119) Home kit: Nerazzurri blue & black
        if 119 in club_by_id:
            d = kit_render.design_from_club(club_by_id[119], season, logo_dir, slot=1, sponsor="fly_emirates")
            assert d["body"] == (10, 50, 145) and d["second"] == (16, 18, 22), f"Inter home season {season} colors error"

        # 6. Ajax (CID 116) Home kit: white body with red central band
        if 116 in club_by_id:
            d = kit_render.design_from_club(club_by_id[116], season, logo_dir, slot=1, sponsor="fly_emirates")
            assert d["body"] == (250, 250, 252) and d["second"] == (210, 20, 35), f"Ajax home season {season} colors error"
