"""Pixel-parity tests for the cropped compositor and fast runtime build path."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GEN = ROOT / "generator"
if str(GEN) not in sys.path:
    sys.path.insert(0, str(GEN))

import build_kit
import kit_render


def _full_canvas_composite(atlas, layer, mask=None):
    """The original full-atlas compositing behaviour used as the oracle."""
    if layer.mode != "RGBA":
        layer = layer.convert("RGBA")
    if mask is not None:
        effective = ImageChops.multiply(kit_render._mask_img(mask), layer.getchannel("A"))
        layer = layer.copy()
        layer.putalpha(effective)
    expected = atlas.copy()
    expected.alpha_composite(layer)
    return expected


def _old_relief_composite(atlas, img, x, y, relief_depth=2,
                          shadow_opacity=65, highlight_opacity=35, mask=None):
    """The original `_composite_with_relief` full-atlas implementation."""
    w, h = img.size
    alpha = np.array(img.split()[-1], dtype=np.float32)
    if not np.any(alpha > 10):
        return _full_canvas_composite(
            atlas, _pasted_layer(atlas, img, x, y), mask)

    layer = Image.new("RGBA", atlas.size, (0, 0, 0, 0))

    amb_alpha = (alpha * (shadow_opacity * 0.45 / 255.0)).astype(np.uint8)
    amb_arr = np.zeros((h, w, 4), dtype=np.uint8)
    amb_arr[:, :, :3] = (10, 12, 16)
    amb_arr[:, :, 3] = amb_alpha
    amb_img = Image.fromarray(amb_arr)
    layer.paste(amb_img, (x + 2, y + relief_depth + 1), amb_img)

    sh_alpha = (alpha * (shadow_opacity / 255.0)).astype(np.uint8)
    shadow_arr = np.zeros((h, w, 4), dtype=np.uint8)
    shadow_arr[:, :, :3] = (12, 14, 20)
    shadow_arr[:, :, 3] = sh_alpha
    shadow_img = Image.fromarray(shadow_arr)
    layer.paste(shadow_img, (x + 1, y + relief_depth), shadow_img)

    hl_alpha = (alpha * (highlight_opacity / 255.0)).astype(np.uint8)
    hl_arr = np.zeros((h, w, 4), dtype=np.uint8)
    hl_arr[:, :, :3] = (255, 255, 255)
    hl_arr[:, :, 3] = hl_alpha
    hl_img = Image.fromarray(hl_arr)
    layer.paste(hl_img, (x - 1, y - 1), hl_img)

    top_alpha = (alpha * (highlight_opacity * 0.55 / 255.0)).astype(np.uint8)
    top_arr = np.zeros((h, w, 4), dtype=np.uint8)
    top_arr[:, :, :3] = (245, 250, 255)
    top_arr[:, :, 3] = top_alpha
    top_img = Image.fromarray(top_arr)
    layer.paste(top_img, (x, y - 1), top_img)

    layer.paste(img, (x, y), img)
    return _full_canvas_composite(atlas, layer, mask)


def _pasted_layer(atlas, img, x, y):
    layer = Image.new("RGBA", atlas.size, (0, 0, 0, 0))
    layer.paste(img, (x, y), img)
    return layer


def test_cropped_composite_is_pixel_identical():
    atlas = Image.new("RGBA", (96, 96), (20, 40, 60, 255))
    layer = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse((18, 12, 70, 60), fill=(220, 30, 40, 170))
    mask = np.zeros((96, 96), dtype=bool)
    mask[10:80, 10:80] = True
    mask[25:45, :] = False

    for selected_mask in (None, mask):
        expected = _full_canvas_composite(atlas, layer, selected_mask)
        actual = atlas.copy()
        kit_render._composite_layer(actual, layer, selected_mask)
        assert ImageChops.difference(expected, actual).getbbox() is None


def test_cropped_relief_is_pixel_identical(monkeypatch):
    monkeypatch.setattr(kit_render, "ATLAS", 96)

    yy, xx = np.mgrid[0:28, 0:38]
    arr = np.zeros((28, 38, 4), dtype=np.uint8)
    arr[:, :, :3] = (200, 155, 45)
    arr[:, :, 3] = np.clip(
        255 - ((xx - 19) ** 2 + (yy - 14) ** 2) * 3, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGBA")
    mask = np.zeros((96, 96), dtype=bool)
    mask[5:90, 5:90] = True
    mask[40:55, :] = False

    for selected_mask in (None, mask):
        atlas = Image.new("RGBA", (96, 96), (12, 50, 90, 255))
        expected = _old_relief_composite(atlas, img, 29, 25, mask=selected_mask)

        actual = atlas.copy()
        kit_render._composite_with_relief(actual, img, 29, 25, mask=selected_mask)
        assert ImageChops.difference(expected, actual).getbbox() is None


def test_fast_build_set_produces_identical_ftex(tmp_path):
    club = build_kit._load_club(100)
    logos = ROOT / "content" / "KitGenerator" / "logos"
    badges = ROOT / "content" / "KitGenerator" / "badges"
    common = dict(
        base_ftex=build_kit.DEFAULT_BASE,
        install=False, game_root=ROOT.parent, quiet=True,
        sponsor="mansion", logo_dir=logos, badge_dir=badges,
        slots=(1,),
    )

    full_dir = tmp_path / "full"
    fast_dir = tmp_path / "fast"
    full = build_kit.build_set(club, 2030, full_dir, previews=True, **common)
    fast = build_kit.build_set(club, 2030, fast_dir, previews=False, **common)

    assert full[0][2].endswith("u0100p1.ftex")
    assert fast[0][2].endswith("u0100p1.ftex")
    assert Path(full[0][2]).read_bytes() == Path(fast[0][2]).read_bytes()
    assert not list(fast_dir.glob("*_atlas.png"))
    assert not list(fast_dir.glob("*_preview.png"))
    assert not list(fast_dir.glob("*_mockup.png"))


if __name__ == "__main__":
    test_cropped_composite_is_pixel_identical()
    print("kit optimization tests passed")
