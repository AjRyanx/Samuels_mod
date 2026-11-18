#!/usr/bin/env python3
"""kit_regions.py - PES 2021 / Football Life 2027 kit UV atlas regions.

Where the numbers come from
---------------------------
The in-game kit texture is a 2048x2048 "UV atlas": the shirt, both sleeves,
both shorts legs, both socks and the collar are packed into fixed islands and
the 3D model wraps them on.  To put OUR design on the kit we must paint into
those islands.

This module does not guess the islands.  The masks in ``uv_masks/`` are the
per-region mask images used by the PES Master Kit Creator (pesmaster.com /
kit-creator), which is the tool that produces in-game-valid PES 2021 kit
textures (and is where the flat-colour template ``kit.png`` came from).  They
are the ground truth for the layout:

    uv_masks/body_erase.png   the SHIRT panels are the *holes* in this mask
                              (upper hole = back panel, lower hole = front panel)
    uv_masks/sleeves.png      both sleeves (shoulder corners + raglan side panels)
    uv_masks/shorts.png       both shorts legs
    uv_masks/socks.png        both socks
    uv_masks/collar.png       the collar

Cross-check against the real Chelsea textures (TheGaffer_Chelsea_FC):
    away-kit yellow socks  (0,640)-(370,1151) / (1678,640)-(2037,1151) -> socks.png
    away-kit yellow shorts (31,1535)-(602,1696) / (1446,1535)-(2015,1695) -> shorts.png
    third-kit vertical stripes spanning y 48..1855 -> front + back panels stacked
so the mask layout and the game's layout agree.

Logo anchor points (taken from the Kit Creator's own constants, default
positions, i.e. sponsor_pos_x = sponsor_pos_y = 0):

    chest sponsor   centre (1024, 1225), area 40000 px^2
    club badge      centre (1130, 1140), area  7225 px^2   (player's left chest)
    kit supplier    centre ( 918, 1140), area  7225 px^2   (player's right chest)

Front / back panels (Basic raglan template):
    front   x 660..1390, y  952..1888   (top edge = shoulder, bottom = hem)
    back    x 660..1390, y   16.. 952
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

MASK_DIR = Path(__file__).resolve().parent / "uv_masks"

# --- logo anchors (uv-space centre x, centre y, target area in px^2) -------- #
CHEST_SPONSOR = (1024, 1225, 40000)
CLUB_BADGE = (1130, 1140, 7225)
KIT_SUPPLIER = (918, 1140, 7225)

# --- front / back panel boxes (for reference / debug) ---------------------- #
FRONT_BOX = (660, 952, 1390, 1888)
BACK_BOX = (660, 16, 1390, 952)


def _load_alpha(path):
    """Load a mask PNG and return a bool array of where it is opaque."""
    im = Image.open(path).convert("RGBA")
    return np.asarray(im)[:, :, 3] > 10


def build_masks(mask_dir=None):
    """Return {region_name: bool mask} in 2048x2048 UV space."""
    d = Path(mask_dir) if mask_dir else MASK_DIR

    erase = _load_alpha(d / "body_erase.png")
    body = ~erase
    lbl, n = ndimage.label(body)
    comps = []
    for i in range(1, n + 1):
        m = lbl == i
        if m.sum() < 10000:
            continue
        ys, _ = np.where(m)
        comps.append((float(ys.mean()), m))
    if len(comps) < 2:
        raise RuntimeError("body_erase.png did not yield two shirt panels")
    comps.sort(key=lambda t: t[0])          # top first
    body_back = comps[0][1]                 # upper hole  = back panel
    body_front = comps[-1][1]               # lower hole  = front panel

    return {
        "body_front": body_front,
        "body_back": body_back,
        "body": body_front | body_back,
        "sleeve": _load_alpha(d / "sleeves.png"),
        "shorts": _load_alpha(d / "shorts.png"),
        "socks": _load_alpha(d / "socks.png"),
        "collar": _load_alpha(d / "collar.png"),
    }


def region_boxes(masks):
    """Return {region: (x0, y0, x1, y1)} for the given masks."""
    out = {}
    for name, m in masks.items():
        ys, xs = np.where(m)
        if len(xs):
            out[name] = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    return out


# --------------------------------------------------------------------------- #
#  debug helpers (optional - only used when you want to eyeball the layout)
# --------------------------------------------------------------------------- #
DEBUG_COLOURS = {
    "body_front": (230, 40, 40),
    "body_back": (40, 80, 230),
    "sleeve": (40, 200, 60),
    "shorts": (240, 220, 40),
    "socks": (230, 40, 230),
    "collar": (40, 210, 210),
}


def debug_map(masks, out_path):
    """Render a flat, labelled region map for visual inspection."""
    from PIL import ImageDraw, ImageFont

    h, w = next(iter(masks.values())).shape
    img = Image.new("RGB", (w, h), (20, 20, 20))
    px = img.load()
    for name, m in masks.items():
        col = DEBUG_COLOURS.get(name)
        if col is None:
            continue
        ys, xs = np.where(m)
        for y, x in zip(ys.tolist(), xs.tolist()):
            px[x, y] = col

    dr = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 80)
    except Exception:  # pragma: no cover
        font = ImageFont.load_default()
    for name, m in masks.items():
        ys, xs = np.where(m)
        if len(xs) == 0:
            continue
        dr.text((int(xs.mean()) - 10, int(ys.mean()) - 10), name,
                fill=(0, 0, 0), font=font, stroke_width=6, stroke_fill=(255, 255, 255))
    img.save(out_path)
    return out_path


if __name__ == "__main__":
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "region_debug.png"
    masks = build_masks()
    print("regions (2048x2048 UV space):")
    for name, box in region_boxes(masks).items():
        print(f"  {name:10s} px={int(masks[name].sum()):8d} bbox={box}")
    print("  front panel:", FRONT_BOX)
    print("  back  panel:", BACK_BOX)
    print("  sponsor anchor:", CHEST_SPONSOR, " badge:", CLUB_BADGE, " supplier:", KIT_SUPPLIER)
    debug_map(masks, out)
    print("wrote", out)
