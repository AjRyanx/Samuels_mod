#!/usr/bin/env python3
"""kit_diag.py - build a DIAGNOSTIC region-map kit texture.

Every UV island is painted a different flat colour and labelled, so a single
in-game screenshot tells us unambiguously whether the game is reading our
override and whether each island maps to the body part we think it does.

    python kit_diag.py <outdir> [--name u0102p1]

Colours:
    body_front  red      body_back  blue
    sleeve      green    shorts     yellow
    socks       magenta  collar     cyan
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import kit_regions

ATLAS = 2048

REGION_COLOURS = {
    "body_front": (220, 40, 40),
    "body_back": (40, 80, 220),
    "sleeve": (40, 200, 60),
    "shorts": (240, 220, 40),
    "socks": (230, 40, 230),
    "collar": (40, 210, 210),
}

LABELS = {
    "body_front": "FRONT",
    "body_back": "BACK",
    "sleeve": "SLEEVE",
    "shorts": "SHORTS",
    "socks": "SOCKS",
    "collar": "COLLAR",
}


def build(out_png):
    import numpy as np

    masks = kit_regions.build_masks()
    atlas = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 255))

    for name, col in REGION_COLOURS.items():
        m = Image.fromarray((masks[name] * 255).astype("uint8"), "L")
        atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), col + (255,)), (0, 0), m)

    draw = ImageDraw.Draw(atlas)
    try:
        font = ImageFont.truetype("arialbd.ttf", 90)
    except Exception:  # pragma: no cover
        font = ImageFont.load_default()

    for name, m in masks.items():
        if name not in LABELS:
            continue
        ys, xs = np.where(m)
        cx, cy = int(xs.mean()), int(ys.mean())
        draw.text((cx, cy), LABELS[name], fill=(0, 0, 0), font=font,
                  anchor="mm", stroke_width=4, stroke_fill=(255, 255, 255))

    atlas.save(out_png)
    return out_png


if __name__ == "__main__":
    import sys

    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    name = "u0102p1"
    if "--name" in sys.argv:
        name = sys.argv[sys.argv.index("--name") + 1]
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{name}_diag_atlas.png"
    build(str(out))
    print("wrote", out)
