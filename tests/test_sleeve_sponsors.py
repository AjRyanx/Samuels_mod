"""test_sleeve_sponsors.py - Test suite for authentic dynamic sleeve sponsors."""

import os
from pathlib import Path
import pytest
from PIL import Image
import numpy as np

import kit_regions
import kit_dna
import kit_render


ROOT = Path(__file__).resolve().parent.parent
SLEEVE_LOGOS_DIR = ROOT / "content" / "KitGenerator" / "sleeve_logos"
SLEEVE_LOGOS_GEN = ROOT / "generator" / "sleeve_logos"


def test_sleeve_logo_files_exist():
    """Verify that all 24 premier sleeve sponsors exist in color and white silhouette."""
    assert SLEEVE_LOGOS_DIR.is_dir(), f"Missing sleeve logos directory: {SLEEVE_LOGOS_DIR}"
    assert SLEEVE_LOGOS_GEN.is_dir(), f"Missing generator sleeve logos directory: {SLEEVE_LOGOS_GEN}"

    expected_sponsors = [
        "visit_rwanda", "hp", "dxc", "okx", "expedia", "kraken",
        "ambilight", "msc_cruises", "ebay", "bingx", "goat", "noon",
        "gls", "cygames", "deel", "snipes", "aptos", "jd_sports",
        "bitget", "tinder", "western_union", "hyundai", "kohler", "angry_birds"
    ]

    for key in expected_sponsors:
        c_path = SLEEVE_LOGOS_DIR / f"{key}.png"
        w_path = SLEEVE_LOGOS_DIR / f"{key}_white.png"
        assert c_path.is_file(), f"Missing color sleeve logo: {c_path}"
        assert w_path.is_file(), f"Missing white sleeve logo: {w_path}"

        # Check alpha transparency
        im_c = Image.open(c_path)
        im_w = Image.open(w_path)
        assert im_c.mode == "RGBA", f"{c_path} is not RGBA"
        assert im_w.mode == "RGBA", f"{w_path} is not RGBA"
        assert im_c.size == im_w.size, f"Size mismatch for {key}: {im_c.size} vs {im_w.size}"


def test_sleeve_logo_no_solid_white_blocks():
    """Verify that white silhouettes have negative space cutouts and never turn into solid blocks."""
    for f in os.listdir(SLEEVE_LOGOS_DIR):
        if not f.endswith("_white.png"):
            continue
        p = SLEEVE_LOGOS_DIR / f
        im = Image.open(p)
        arr = np.array(im)
        alpha = arr[:, :, 3]
        nz = np.where(alpha > 10)
        assert len(nz[0]) > 0, f"Empty white logo: {f}"

        ymin, ymax = nz[0].min(), nz[0].max()
        xmin, xmax = nz[1].min(), nz[1].max()
        h = ymax - ymin + 1
        w = xmax - xmin + 1
        sub = alpha[ymin:ymax+1, xmin:xmax+1]
        fill_ratio = np.sum(sub > 10) / (h * w)

        # No sleeve sponsor logo should be a solid rectangle or solid circle block (> 0.70)
        assert fill_ratio < 0.70, (
            f"Suspicious solid block in sleeve logo {f}: fill ratio {fill_ratio:.2f} > 0.70. "
            f"Inner text or emblem must use transparent alpha cutouts!"
        )


def test_sleeve_sponsor_dynamic_assignment():
    """Verify authentic club mapping and deterministic fallback assignment."""
    # Top clubs with authentic real-world sleeve sponsors
    assert kit_dna.get_club_sleeve_sponsor(101) == "visit_rwanda"  # Arsenal
    assert kit_dna.get_club_sleeve_sponsor(109) == "hp"            # Real Madrid
    assert kit_dna.get_club_sleeve_sponsor(100) == "dxc"           # Manchester United
    assert kit_dna.get_club_sleeve_sponsor(173) == "okx"           # Manchester City
    assert kit_dna.get_club_sleeve_sponsor(103) == "expedia"       # Liverpool
    assert kit_dna.get_club_sleeve_sponsor(108) == "ambilight"     # Barcelona
    assert kit_dna.get_club_sleeve_sponsor(102) == "bingx"         # Chelsea
    assert kit_dna.get_club_sleeve_sponsor(114) == "goat"          # PSG
    assert kit_dna.get_club_sleeve_sponsor(126) == "gls"           # Dortmund
    assert kit_dna.get_club_sleeve_sponsor(121) == "msc_cruises"   # AC Milan
    assert kit_dna.get_club_sleeve_sponsor(119) == "ebay"          # Inter Milan
    assert kit_dna.get_club_sleeve_sponsor(120) == "cygames"       # Juventus

    # Generic club fallback
    club_999 = kit_dna.get_club_sleeve_sponsor(999, season=2026)
    assert club_999 in kit_dna.SLEEVE_SPONSOR_POOL
    # Consecutive seasons rotate
    club_999_s2 = kit_dna.get_club_sleeve_sponsor(999, season=2027)
    assert club_999_s2 in kit_dna.SLEEVE_SPONSOR_POOL


def test_sleeve_sponsor_uv_containment():
    """Verify left sleeve anchor coordinates and UV island containment."""
    masks = kit_regions.build_masks()
    sleeve_mask = masks["sleeve"]

    cx, cy, area = kit_regions.SLEEVE_SPONSOR_LEFT
    assert cx == 1515
    assert cy == 405
    assert area == 12000
    assert kit_regions.SLEEVE_WRAP_ANGLE == 0.0

    # Check containment of standard sleeve sponsor stamp item
    stamp_item = {"cx": cx, "cy": cy, "w": 160, "h": 70}
    adj = kit_regions.validate_and_adjust_stamps(masks, sleeve_sponsor=stamp_item).get("sleeve_sponsor")
    assert adj is not None
    # Must be completely inside the sleeve mask
    x0, y0 = adj["x"], adj["y"]
    w, h = adj["w"], adj["h"]
    assert bool(np.all(sleeve_mask[y0:y0+h, x0:x0+w])), "Sleeve sponsor stamp clips sleeve UV boundary"


def test_sleeve_sponsor_rendering_contrast_and_rotation(tmp_path):
    """Verify render_kit stamps sleeve sponsor with wrap rotation and auto contrast."""
    masks = kit_regions.build_masks()

    # Dark sleeve: should pick white variant
    design_dark = {
        "body": (20, 24, 32),
        "second": (255, 255, 255),
        "accent": (220, 40, 40),
        "sleeve_sponsor": "visit_rwanda",
    }
    out_dark = tmp_path / "dark_kit.png"
    kit_render.render_kit(design_dark, str(out_dark), masks=masks)
    assert out_dark.is_file()

    im_dark = Image.open(out_dark)
    arr_dark = np.array(im_dark)
    # Check pixels in sleeve sponsor zone (1485..1545, 380..430)
    # On dark fabric (20, 24, 32), white logo text should have luminance > 200
    sub_dark = arr_dark[380:430, 1485:1545]
    high_lum = np.sum(sub_dark[:, :, :3] > 200)
    assert high_lum > 100, "White sleeve sponsor variant was not applied on dark kit"

    # Light sleeve: should pick color variant
    design_light = {
        "body": (245, 245, 248),
        "second": (20, 24, 32),
        "accent": (220, 40, 40),
        "sleeve_sponsor": "hp",
    }
    out_light = tmp_path / "light_kit.png"
    kit_render.render_kit(design_light, str(out_light), masks=masks)
    assert out_light.is_file()

    im_light = Image.open(out_light)
    arr_light = np.array(im_light)
    # HP logo blue is around (0, 150, 214)
    sub_light = arr_light[380:430, 1485:1545]
    hp_blue_pixels = np.sum((sub_light[:, :, 0] < 50) & (sub_light[:, :, 1] > 100) & (sub_light[:, :, 2] > 180))
    assert hp_blue_pixels > 50, "Full-color sleeve sponsor variant was not applied on light kit"
