#!/usr/bin/env python3
"""generate_supplier_assets.py - Generate crisp, supersampled supplier logos with transparent alpha."""

import math
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

DEST_DIRS = [
    Path("SiderAddons/content/KitGenerator/suppliers"),
    Path("mods/Dynamic_Kit_and_Sponsor_mod_pes21/content/KitGenerator/suppliers"),
]

def make_variants(im, name):
    """Save default, white, and dark variants to all destination dirs."""
    bbox = im.getbbox()
    if bbox:
        # Add 4px padding
        pad = 4
        crop_box = (max(0, bbox[0] - pad), max(0, bbox[1] - pad),
                     min(im.width, bbox[2] + pad), min(im.height, bbox[3] + pad))
        im = im.crop(crop_box)
    
    # White variant (for dark shirts)
    arr_w = np.array(im)
    arr_w[:, :, :3] = 255
    im_white = Image.fromarray(arr_w)

    # Dark variant (for light/white shirts)
    arr_d = np.array(im)
    arr_d[:, :, :3] = [20, 24, 30]
    im_dark = Image.fromarray(arr_d)

    for d in DEST_DIRS:
        d.mkdir(parents=True, exist_ok=True)
        im_white.save(d / f"{name}_white.png")
        im_dark.save(d / f"{name}_dark.png")
        im_white.save(d / f"{name}.png") # default to white silhouette for high contrast

# --- VECTOR LOGO GENERATORS (4x supersampled for perfect antialiasing) ---

def draw_umbro(w=240, h=120):
    """Umbro iconic double diamond."""
    SCALE = 4
    W, H = w * SCALE, h * SCALE
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    cx, cy = W // 2, H // 2
    # Outer diamond
    rx_out, ry_out = int(W * 0.44), int(H * 0.44)
    rx_cut, ry_cut = int(W * 0.30), int(H * 0.30)
    rx_in, ry_in = int(W * 0.18), int(H * 0.18)

    # Draw outer diamond
    outer = [(cx, cy - ry_out), (cx + rx_out, cy), (cx, cy + ry_out), (cx - rx_out, cy)]
    draw.polygon(outer, fill=(255, 255, 255, 255))

    # Erase cutout
    cut = [(cx, cy - ry_cut), (cx + rx_cut, cy), (cx, cy + ry_cut), (cx - rx_cut, cy)]
    draw.polygon(cut, fill=(0, 0, 0, 0))

    # Draw inner solid diamond
    inner = [(cx, cy - ry_in), (cx + rx_in, cy), (cx, cy + ry_in), (cx - rx_in, cy)]
    draw.polygon(inner, fill=(255, 255, 255, 255))

    return im.resize((w, h), Image.LANCZOS)

def draw_hummel(w=200, h=140):
    """Hummel iconic double chevron."""
    SCALE = 4
    W, H = w * SCALE, h * SCALE
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    cx = W // 2
    # Two stacked chevrons pointing up
    # Chevron 1 (Top)
    thickness = int(32 * SCALE)
    top_y = int(20 * SCALE)
    mid_y = int(58 * SCALE)
    
    # Top chevron
    pts1 = [
        (cx, top_y),
        (cx + int(70 * SCALE), mid_y),
        (cx + int(50 * SCALE), mid_y),
        (cx, top_y + thickness),
        (cx - int(50 * SCALE), mid_y),
        (cx - int(70 * SCALE), mid_y),
    ]
    draw.polygon(pts1, fill=(255, 255, 255, 255))

    # Chevron 2 (Bottom)
    offset_y = int(45 * SCALE)
    pts2 = [(x, y + offset_y) for x, y in pts1]
    draw.polygon(pts2, fill=(255, 255, 255, 255))

    return im.resize((w, h), Image.LANCZOS)

def draw_castore(w=240, h=110):
    """Castore stylized soaring wings."""
    SCALE = 4
    W, H = w * SCALE, h * SCALE
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    cx, cy = W // 2, int(H * 0.45)
    
    # Left wing
    left_wing = [
        (cx - int(10 * SCALE), cy + int(35 * SCALE)),
        (cx - int(95 * SCALE), cy - int(25 * SCALE)),
        (cx - int(80 * SCALE), cy - int(20 * SCALE)),
        (cx - int(65 * SCALE), cy - int(32 * SCALE)),
        (cx - int(52 * SCALE), cy - int(18 * SCALE)),
        (cx - int(40 * SCALE), cy - int(30 * SCALE)),
        (cx - int(25 * SCALE), cy - int(10 * SCALE)),
        (cx - int(6 * SCALE), cy + int(15 * SCALE)),
    ]
    draw.polygon(left_wing, fill=(255, 255, 255, 255))

    # Right wing (mirrored)
    right_wing = [(2 * cx - x, y) for x, y in left_wing]
    draw.polygon(right_wing, fill=(255, 255, 255, 255))

    return im.resize((w, h), Image.LANCZOS)

def draw_macron(w=200, h=140):
    """Macron heroic human dynamic silhouette."""
    SCALE = 4
    W, H = w * SCALE, h * SCALE
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    cx = W // 2
    # Head
    head_r = int(14 * SCALE)
    head_cy = int(24 * SCALE)
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=(255, 255, 255, 255))

    # Dynamic crescent body / outstretched limbs
    body_pts = [
        (cx, int(42 * SCALE)),
        (cx + int(50 * SCALE), int(48 * SCALE)),
        (cx + int(82 * SCALE), int(68 * SCALE)),
        (cx + int(55 * SCALE), int(76 * SCALE)),
        (cx + int(35 * SCALE), int(64 * SCALE)),
        (cx + int(30 * SCALE), int(105 * SCALE)),
        (cx + int(12 * SCALE), int(125 * SCALE)),
        (cx, int(85 * SCALE)),
        (cx - int(12 * SCALE), int(125 * SCALE)),
        (cx - int(30 * SCALE), int(105 * SCALE)),
        (cx - int(35 * SCALE), int(64 * SCALE)),
        (cx - int(55 * SCALE), int(76 * SCALE)),
        (cx - int(82 * SCALE), int(68 * SCALE)),
        (cx - int(50 * SCALE), int(48 * SCALE)),
    ]
    draw.polygon(body_pts, fill=(255, 255, 255, 255))

    return im.resize((w, h), Image.LANCZOS)

def draw_kappa(w=180, h=150):
    """Kappa classic Omini silhouette (two figures sitting back-to-back)."""
    SCALE = 4
    W, H = w * SCALE, h * SCALE
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    cx = W // 2
    # Heads touching
    head_r = int(12 * SCALE)
    draw.ellipse([cx - int(18*SCALE), int(15*SCALE), cx - int(2*SCALE), int(39*SCALE)], fill=(255, 255, 255, 255))
    draw.ellipse([cx + int(2*SCALE), int(15*SCALE), cx + int(18*SCALE), int(39*SCALE)], fill=(255, 255, 255, 255))

    # Right figure body + knees
    r_body = [
        (cx + int(2 * SCALE), int(42 * SCALE)),
        (cx + int(18 * SCALE), int(50 * SCALE)),
        (cx + int(32 * SCALE), int(72 * SCALE)),
        (cx + int(58 * SCALE), int(95 * SCALE)),
        (cx + int(64 * SCALE), int(120 * SCALE)),
        (cx + int(48 * SCALE), int(130 * SCALE)),
        (cx + int(35 * SCALE), int(105 * SCALE)),
        (cx + int(18 * SCALE), int(125 * SCALE)),
        (cx + int(2 * SCALE), int(125 * SCALE)),
    ]
    draw.polygon(r_body, fill=(255, 255, 255, 255))

    # Left figure (mirrored)
    l_body = [(2 * cx - x, y) for x, y in r_body]
    draw.polygon(l_body, fill=(255, 255, 255, 255))

    return im.resize((w, h), Image.LANCZOS)

def draw_joma(w=200, h=130):
    """Joma stylized dynamic J-eagle."""
    SCALE = 4
    W, H = w * SCALE, h * SCALE
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    pts = [
        (int(20 * SCALE), int(35 * SCALE)),
        (int(100 * SCALE), int(25 * SCALE)),
        (int(175 * SCALE), int(55 * SCALE)),
        (int(185 * SCALE), int(72 * SCALE)),
        (int(135 * SCALE), int(65 * SCALE)),
        (int(85 * SCALE), int(55 * SCALE)),
        (int(58 * SCALE), int(68 * SCALE)),
        (int(70 * SCALE), int(88 * SCALE)),
        (int(110 * SCALE), int(88 * SCALE)),
        (int(145 * SCALE), int(105 * SCALE)),
        (int(95 * SCALE), int(118 * SCALE)),
        (int(45 * SCALE), int(112 * SCALE)),
        (int(28 * SCALE), int(88 * SCALE)),
        (int(32 * SCALE), int(55 * SCALE)),
    ]
    draw.polygon(pts, fill=(255, 255, 255, 255))

    return im.resize((w, h), Image.LANCZOS)

def draw_newbalance(w=220, h=110):
    """New Balance iconic NB emblem."""
    SCALE = 4
    W, H = w * SCALE, h * SCALE
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    # Draw bold italic stylized N and B
    # Left 'N' slanted block
    n_pts = [
        (int(25 * SCALE), int(95 * SCALE)),
        (int(52 * SCALE), int(20 * SCALE)),
        (int(80 * SCALE), int(20 * SCALE)),
        (int(115 * SCALE), int(75 * SCALE)),
        (int(135 * SCALE), int(20 * SCALE)),
        (int(160 * SCALE), int(20 * SCALE)),
        (int(132 * SCALE), int(95 * SCALE)),
        (int(105 * SCALE), int(95 * SCALE)),
        (int(72 * SCALE), int(42 * SCALE)),
        (int(52 * SCALE), int(95 * SCALE)),
    ]
    draw.polygon(n_pts, fill=(255, 255, 255, 255))

    # Horizontal speed cuts across N
    for cut_y in [42, 60, 78]:
        draw.rectangle([int(15 * SCALE), int(cut_y * SCALE), int(140 * SCALE), int((cut_y + 6) * SCALE)],
                       fill=(0, 0, 0, 0))

    # Right 'B' loops
    b_pts = [
        (int(142 * SCALE), int(20 * SCALE)),
        (int(185 * SCALE), int(20 * SCALE)),
        (int(205 * SCALE), int(35 * SCALE)),
        (int(195 * SCALE), int(55 * SCALE)),
        (int(212 * SCALE), int(75 * SCALE)),
        (int(195 * SCALE), int(95 * SCALE)),
        (int(125 * SCALE), int(95 * SCALE)),
        (int(135 * SCALE), int(75 * SCALE)),
        (int(165 * SCALE), int(75 * SCALE)),
        (int(180 * SCALE), int(65 * SCALE)),
        (int(165 * SCALE), int(55 * SCALE)),
        (int(145 * SCALE), int(55 * SCALE)),
        (int(155 * SCALE), int(38 * SCALE)),
        (int(172 * SCALE), int(38 * SCALE)),
        (int(165 * SCALE), int(32 * SCALE)),
    ]
    draw.polygon(b_pts, fill=(255, 255, 255, 255))

    return im.resize((w, h), Image.LANCZOS)

def draw_mizuno(w=230, h=110):
    """Mizuno dynamic RunBird."""
    SCALE = 4
    W, H = w * SCALE, h * SCALE
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    pts = [
        (int(25 * SCALE), int(75 * SCALE)),
        (int(85 * SCALE), int(30 * SCALE)),
        (int(165 * SCALE), int(22 * SCALE)),
        (int(210 * SCALE), int(42 * SCALE)),
        (int(155 * SCALE), int(45 * SCALE)),
        (int(115 * SCALE), int(55 * SCALE)),
        (int(155 * SCALE), int(72 * SCALE)),
        (int(195 * SCALE), int(85 * SCALE)),
        (int(145 * SCALE), int(95 * SCALE)),
        (int(95 * SCALE), int(82 * SCALE)),
        (int(65 * SCALE), int(85 * SCALE)),
    ]
    draw.polygon(pts, fill=(255, 255, 255, 255))

    return im.resize((w, h), Image.LANCZOS)

def draw_ea7(w=210, h=90):
    """EA7 Emporio Armani typographic mark."""
    SCALE = 4
    W, H = w * SCALE, h * SCALE
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    # Letter 'E'
    draw.rectangle([int(20*SCALE), int(20*SCALE), int(42*SCALE), int(75*SCALE)], fill=(255, 255, 255, 255))
    draw.rectangle([int(42*SCALE), int(20*SCALE), int(70*SCALE), int(34*SCALE)], fill=(255, 255, 255, 255))
    draw.rectangle([int(42*SCALE), int(41*SCALE), int(64*SCALE), int(53*SCALE)], fill=(255, 255, 255, 255))
    draw.rectangle([int(42*SCALE), int(61*SCALE), int(70*SCALE), int(75*SCALE)], fill=(255, 255, 255, 255))

    # Letter 'A'
    a_pts = [
        (int(98 * SCALE), int(20 * SCALE)),
        (int(115 * SCALE), int(20 * SCALE)),
        (int(135 * SCALE), int(75 * SCALE)),
        (int(118 * SCALE), int(75 * SCALE)),
        (int(112 * SCALE), int(58 * SCALE)),
        (int(98 * SCALE), int(58 * SCALE)),
        (int(92 * SCALE), int(75 * SCALE)),
        (int(76 * SCALE), int(75 * SCALE)),
    ]
    draw.polygon(a_pts, fill=(255, 255, 255, 255))
    draw.polygon([(int(102*SCALE), int(35*SCALE)), (int(109*SCALE), int(35*SCALE)), (int(106*SCALE), int(48*SCALE))], fill=(0, 0, 0, 0))

    # Number '7'
    seven_pts = [
        (int(145 * SCALE), int(20 * SCALE)),
        (int(192 * SCALE), int(20 * SCALE)),
        (int(168 * SCALE), int(75 * SCALE)),
        (int(150 * SCALE), int(75 * SCALE)),
        (int(170 * SCALE), int(34 * SCALE)),
        (int(145 * SCALE), int(34 * SCALE)),
    ]
    draw.polygon(seven_pts, fill=(255, 255, 255, 255))

    return im.resize((w, h), Image.LANCZOS)


def main():
    generators = {
        "umbro": draw_umbro,
        "castore": draw_castore,
        "macron": draw_macron,
        "kappa": draw_kappa,
        "joma": draw_joma,
        "hummel": draw_hummel,
        "newbalance": draw_newbalance,
        "mizuno": draw_mizuno,
        "ea7": draw_ea7,
    }

    for name, gen in generators.items():
        print(f"Generating {name} supplier assets...")
        im = gen()
        make_variants(im, name)
    print("All supplier assets generated successfully!")

if __name__ == "__main__":
    main()
