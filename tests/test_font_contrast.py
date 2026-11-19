#!/usr/bin/env python3
"""test_font_contrast.py - Unit test suite for kit font auto-contrasting and FTEX tinting.

Verifies:
1. WCAG 2.1 relative luminance and contrast ratio formulas.
2. Automatic selection of contrasting colors (ensures CR >= 4.5:1 for both dark and light kits).
3. Smooth tinting of dual-tone font textures while preserving alpha channel and anti-aliased edges.
4. FTEX format round-trip encoding and byte-header validity.
5. End-to-end kit font processing across multiple club kit scenarios.
"""
import io
import shutil
import sys
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "generator"))

import ftex_io
import kit_fonts


def test_wcag_formulas():
    # 1. Pure black vs pure white
    cr_bw = kit_fonts.contrast_ratio((0, 0, 0), (255, 255, 255))
    assert abs(cr_bw - 21.0) < 0.1, f"Expected 21:1 for black vs white, got {cr_bw}"

    # 2. Identical colors
    cr_same = kit_fonts.contrast_ratio((120, 120, 120), (120, 120, 120))
    assert abs(cr_same - 1.0) < 0.01, f"Expected 1:1 for identical colors, got {cr_same}"

    # 3. Known football kit color clashes
    # Dark red (Arsenal / Milan 195, 20, 30) vs Black (20, 20, 20)
    cr_dark_clash = kit_fonts.contrast_ratio((195, 20, 30), (20, 20, 20))
    assert cr_dark_clash < 3.5, f"Expected clash < 3.5:1 for red on black, got {cr_dark_clash}"
    assert not kit_fonts.is_contrasting((195, 20, 30), (20, 20, 20))

    # White on dark red
    cr_white_on_red = kit_fonts.contrast_ratio((252, 252, 254), (195, 20, 30))
    assert cr_white_on_red >= 4.5, f"Expected >= 4.5:1 for white on red, got {cr_white_on_red}"
    assert kit_fonts.is_contrasting((252, 252, 254), (195, 20, 30))
    print("PASS: WCAG 2.1 formulas and contrast calculations verified.")


def test_color_selection():
    # Dark kit background (e.g. Navy (15, 20, 45))
    dark_bg = (15, 20, 45)
    fill, outline = kit_fonts.choose_contrasting_colors(dark_bg)
    cr_fill = kit_fonts.contrast_ratio(fill, dark_bg)
    assert cr_fill >= 10.0, f"Expected CR >= 10 for dark bg, got {cr_fill:.2f} ({fill})"
    print(f"PASS: Dark kit (15, 20, 45) -> fill {fill} with CR={cr_fill:.1f}:1 (WCAG AAA)")

    # Light kit background (e.g. White (245, 245, 245))
    light_bg = (245, 245, 245)
    fill_l, outline_l = kit_fonts.choose_contrasting_colors(light_bg)
    cr_fill_l = kit_fonts.contrast_ratio(fill_l, light_bg)
    assert cr_fill_l >= 10.0, f"Expected CR >= 10 for light bg, got {cr_fill_l:.2f} ({fill_l})"
    print(f"PASS: Light kit (245, 245, 245) -> fill {fill_l} with CR={cr_fill_l:.1f}:1 (WCAG AAA)")

    # Kit with club gold accent (245, 215, 60) on dark navy
    design_gold = {"trim": (245, 215, 60)}
    fill_g, _ = kit_fonts.choose_contrasting_colors(dark_bg, design=design_gold)
    cr_gold = kit_fonts.contrast_ratio(fill_g, dark_bg)
    assert cr_gold >= 4.5, f"Expected CR >= 4.5 for gold on navy, got {cr_gold:.2f}"
    print(f"PASS: Kit with gold accent on navy -> selected {fill_g} with CR={cr_gold:.1f}:1")


def test_real_font_texture_tinting():
    arsenal_p1 = Path(r"C:\Games\SP Football Life 2027\SiderAddons\content\kits\Premier League\Arsenal\p1\u0101p1_back.ftex")
    if not arsenal_p1.is_file():
        print("SKIP: Real game kit textures not found for live tint test.")
        return

    # Scenario A: White kit with Arsenal p1 font (original is white -> clashes!)
    white_shirt = (245, 245, 245)
    raw = arsenal_p1.read_bytes()
    tmpl = ftex_io.parse_ftex(raw)
    dds = ftex_io.ftex_to_dds(raw)
    img = Image.open(io.BytesIO(dds))

    orig_rgb, is_light = kit_fonts.detect_font_color(img)
    orig_cr = kit_fonts.contrast_ratio(orig_rgb, white_shirt)
    assert orig_cr < 2.0, f"Expected clash with white shirt, got {orig_cr}"

    target_fill, target_outline = kit_fonts.choose_contrasting_colors(white_shirt)
    tinted = kit_fonts.tint_font_image(img, target_fill, target_outline)
    new_rgb, _ = kit_fonts.detect_font_color(tinted)
    new_cr = kit_fonts.contrast_ratio(new_rgb, white_shirt)
    assert new_cr >= 8.0, f"Expected high contrast after tinting, got {new_cr}"

    # Verify alpha channel unchanged
    arr_orig = np.array(img)
    arr_tint = np.array(tinted)
    np.testing.assert_array_equal(arr_orig[:, :, 3], arr_tint[:, :, 3])
    print(f"PASS: Arsenal p1 font on white shirt tinted: CR improved from {orig_cr:.1f}:1 to {new_cr:.1f}:1.")

    # Scenario B: FTEX round-trip encoding
    out_ftex = ftex_io.image_to_ftex(tinted, template=tmpl)
    assert len(out_ftex) > 50000
    parsed = ftex_io.parse_ftex(out_ftex)
    assert parsed["width"] == 4096
    assert parsed["height"] == 512
    assert parsed["pixel_format"] == 4
    assert parsed["mip_count"] == 13
    print("PASS: FTEX round-trip encoding verified (BC3/DXT5 4096x512, 13 mips).")


def test_end_to_end_process_kit_fonts():
    tmp_out = Path(tempfile.mkdtemp())
    try:
        club = {"id": 101, "name": "Arsenal"}
        # Dark black dynamic kit
        design_dark = {"body": (18, 18, 22), "shorts": (18, 18, 22)}
        res_dark = kit_fonts.process_kit_fonts(club, 1, design_dark, tmp_out, install=False)
        assert len(res_dark) >= 3
        for ftype, p, cr, tinted in res_dark:
            assert cr >= 4.0, f"Expected CR >= 4.0 for {ftype}, got {cr}"
            assert Path(p).is_file()
        print("PASS: Dark kit font generation passed with all CR >= 4.0:1.")

        # Light silver dynamic kit
        design_light = {"body": (230, 230, 235), "shorts": (230, 230, 235)}
        res_light = kit_fonts.process_kit_fonts(club, 1, design_light, tmp_out, install=False)
        assert len(res_light) >= 3
        for ftype, p, cr, tinted in res_light:
            assert cr >= 4.0, f"Expected CR >= 4.0 for {ftype}, got {cr}"
            assert Path(p).is_file()
        print("PASS: Light kit font generation passed with all CR >= 4.0:1.")
    finally:
        shutil.rmtree(tmp_out, ignore_errors=True)


if __name__ == "__main__":
    test_wcag_formulas()
    test_color_selection()
    test_real_font_texture_tinting()
    test_end_to_end_process_kit_fonts()
    print("\nALL FONT CONTRAST TESTS PASSED!")
