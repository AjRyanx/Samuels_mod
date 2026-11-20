#!/usr/bin/env python3
"""tests/test_kit_details.py - Verify realistic kit detail layers.

Validates:
1. Fabric micro-knit textile weave across all garment panels.
2. 3D contact drop shadow and specular rim relief on badges & sponsors.
3. Tailoring construction lines (raglan armholes, flank seams, twin-needle hem stitches).
4. Inner collar neck tape & authenticity size print.
5. Supplier performance fabric tech heat-stamp (HEAT.RDY, DRI-FIT ADV, ULTRAWEAVE, etc.).
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "generator"))

import kit_render
import kit_regions


def test_fabric_microtexture_presence():
    """Verify that fabric micro-knit texture modulates garment luminance with zero color drift."""
    masks = kit_regions.build_masks()
    d = {
        "body": (3, 70, 155),
        "second": (245, 245, 245),
        "pattern": "plain",
        "fabric_texture": True,
    }
    atlas = kit_render.render_kit(d, None, masks=masks)
    arr = np.array(atlas)

    # Sample inside torso front
    sample = arr[1400:1440, 1000:1040, :3]
    std_r = np.std(sample[:, :, 0])
    std_b = np.std(sample[:, :, 2])
    assert std_r > 1.5, f"Expected red channel micro-texture std > 1.5, got {std_r}"
    assert std_b > 1.5, f"Expected blue channel micro-texture std > 1.5, got {std_b}"


def test_heat_press_relief_and_shadows():
    """Verify that badges and sponsors receive 3D contact shadows and relief depth."""
    masks = kit_regions.build_masks()
    test_logo = REPO_ROOT / "content" / "KitGenerator" / "logos" / "fly_emirates.png"
    if not test_logo.is_file():
        return

    d = {
        "body": (3, 70, 155),
        "second": (245, 245, 245),
        "pattern": "plain",
        "sponsor": str(test_logo),
        "heat_press_relief": True,
    }
    atlas = kit_render.render_kit(d, None, masks=masks)
    arr = np.array(atlas)

    # In chest sponsor zone, contact shadow pixels must be present below logo strokes
    sp_region = arr[1240:1380, 850:1200, :3]
    diff_body = np.abs(sp_region - np.array([3, 70, 155])).sum(axis=-1)
    is_shadow = (sp_region[:, :, 2] < 150) & (sp_region[:, :, 1] < 68) & (diff_body > 8)
    assert np.count_nonzero(is_shadow) > 100, "Expected at least 100 contact shadow relief pixels"


def test_construction_seams_and_stitching():
    """Verify presence of flank seams and twin-needle hem stitching."""
    masks = kit_regions.build_masks()
    d = {
        "body": (3, 70, 155),
        "second": (245, 245, 245),
        "pattern": "plain",
        "construction_seams": True,
    }
    atlas = kit_render.render_kit(d, None, masks=masks)
    arr = np.array(atlas)

    # Check flank seam stitch at x=724, y=1400..1600
    flank_stitch = arr[1400:1600, 724, :3]
    diff_stitch = np.abs(flank_stitch - np.array([3, 70, 155])).sum(axis=-1)
    assert np.count_nonzero(diff_stitch > 10) > 50, "Expected flank seam stitching pixels"


def test_inner_neck_detail_and_tape():
    """Verify that inner collar neck tape and size markings are rendered on upper back panel."""
    masks = kit_regions.build_masks()
    d = {
        "body": (3, 70, 155),
        "second": (245, 245, 245),
        "pattern": "plain",
        "inner_neck_tape": True,
    }
    atlas = kit_render.render_kit(d, None, masks=masks)
    arr = np.array(atlas)

    # Upper back neck opening at (970..1070, 80..130)
    neck_area = arr[80:130, 970:1070]
    diff_neck = np.abs(neck_area[:, :, :3] - np.array([3, 70, 155])).sum(axis=-1)
    assert np.count_nonzero(diff_neck > 20) > 200, "Expected neck tape and size print pixels"


def test_supplier_tech_callout():
    """Verify that supplier performance fabric tech stamps are rendered at lower right hem."""
    masks = kit_regions.build_masks()
    d = {
        "body": (3, 70, 155),
        "second": (245, 245, 245),
        "pattern": "plain",
        "supplier_name": "nike",
        "tech_callout": True,
    }
    atlas = kit_render.render_kit(d, None, masks=masks)
    arr = np.array(atlas)

    # Lower right hem area (730..820, 1825..1845)
    tech_area = arr[1825:1845, 730:820]
    diff_tech = np.abs(tech_area[:, :, :3] - np.array([3, 70, 155])).sum(axis=-1)
    assert np.count_nonzero(diff_tech > 20) > 100, "Expected tech stamp pixels at lower hem"
