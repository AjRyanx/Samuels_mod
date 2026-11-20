#!/usr/bin/env python3
"""kit_render.py - paint a generated kit design into the PES 2021 UV atlas.

Pipeline
--------
    club + season  ->  kg_core.season_rng / pick_design   (same roll as the Lua mod)
                   ->  kit_gen.draw_pattern               (same 2D design as the preview)
                   ->  shirt-local tile  ->  front + back panels   (UV atlas)
                   ->  2048x2048 RGBA atlas PNG
                   ->  ftex_io.py repack  ->  u<team>p1.ftex  ->  livecpk override

Why a shirt-local tile?
-----------------------
The game texture is a 2048x2048 "UV atlas": the shirt front, shirt back, both
sleeves, both shorts legs, both socks and the collar are packed into fixed
islands and the model wraps them on (see kit_regions.py for the provenance of
those islands).

The front and back shirt islands are NOT the same shape - the front island
tapers at its *top* (the neck) and the back island tapers at its *bottom*.  That
is because the game (and the PES Master Kit Creator that produces valid PES 2021
textures) draws the back by rotating the design 180 degrees:

    ApplyDesigntoShirt:  translate(1024,952); draw front going down;
                         rotate(180); draw back

So we build ONE square "shirt-local" tile - u across the shirt, v from the
shoulder (0) down to the hem (1) - and paste it upright into the front island
and rotated 180 degrees into the back island.  The design therefore looks
identical to the 2D preview, just wrapped onto the 3D shirt.

Nothing is copied from a real club kit: the flat-colour template only tells us
*where* the islands are, never *what* they look like.
"""
from pathlib import Path
import math
import re
import numpy as np

from PIL import Image, ImageDraw, ImageFont

import kit_gen
import kit_regions
import kit_dna

ATLAS = 2048
TILE = 1024                      # shirt-local tile resolution (u, v)

# kit_gen's preview draws the shirt inside a 480x500 canvas; this is the body
# bounding box of that preview shirt (see kit_gen.shirt_masks()).
_PREVIEW_SHIRT_BOX = (108, 40, 372, 470)

DEFAULT_DESIGN = {
    "body": (3, 70, 148),         # main shirt colour
    "second": (255, 255, 255),    # pattern colour
    "accent": (200, 168, 75),     # accent colour
    "third": None,                # optional 3rd colour for pattern hairlines
    "pattern": "plain",
    "var": 0,                     # pattern variant (0..2)
    "width_step": 0,              # stripe width step (0..7)
    "gradient": 0,                # 0..3 vertical shading strength
    "sleeve": None,               # None = same as body
    "sleeve_style": "solid",      # "solid", "raglan", "shoulder_stripe", "tipped"
    "cuff": None,                 # None = same as sleeve
    "cuff_tip": None,             # contrast tipping on sleeve cuff
    "shorts": None,               # None = same as body
    "shorts_style": "solid",      # "solid", "side_stripe", "hem_tape", "split_leg"
    "shorts_accent": None,        # contrast stripe/tape colour on shorts
    "socks": None,                # None = same as body
    "socks_style": "solid",       # "solid", "turnover_hoop", "calf_band", "gradient_fade"
    "socks_accent": None,         # contrast hoop/band colour on socks
    "socks_tip": None,            # contrast tipping on socks turnover
    "collar": None,               # None = same as body
    "collar_style": "crew",       # "crew", "v_neck", "polo", "dual_tipped"
    "collar_model": 1,            # 3D Kitserver collar model: 1=crew, 2=dual_tipped, 3=v_neck, 13=polo
    "collar_tip": None,           # contrast tipping on collar ribbing
    "sponsor": None,              # path to a PNG logo (chest)
    "badge": None,                # path to a PNG logo (club badge)
    "supplier": None,             # path to a PNG logo (kit maker)
    "sponsor_white": False,       # True = flatten the logo to white
    "badge_white": False,
    "supplier_white": False,
    "sponsor_plate": False,       # draw a body-coloured plate behind the sponsor (False = seamless logo with no background)
    "vent_style": "none",         # "none", "laser_cut", "contrast_panel", "stealth_rib"
    "vent_color": None,           # None = auto breathable tone
    "macro_layout": "solid",      # "solid", "ombre_fade", "half_half", "chestband", "diagonal_sash", "fade_geo"
    "micro_jacquard": None,       # secondary subtle luxury jacquard overlay (e.g. "041-E", "171-E")
    "pattern_mask": "full",       # "full", "front_only", "chest_only", "sash_only", "sleeves_only"
    "tile_scale": 1.0,            # 0.5 (micro-weave 2x2), 1.0 (standard), 2.0 (macro streetwear art)
    "finish": "standard",         # "standard", "liquid_gold", "chrome_silver", "copper_bronze", "blackout", "whiteout", "cyber_neon"
    "jocktag": True,              # True = render authentic engineered jocktag at lower shirt hem
    "shorts_badge": True,         # True = render club crest on right shorts leg
    "shorts_supplier": True,      # True = render supplier logo on left shorts leg
    "sleeve_sponsor": None,       # path to a PNG logo or key (player's left sleeve)
    "sleeve_sponsor_angle": 0.0,  # wrap angle slope along sleeve (default: 0.0 degrees / upright)
    "sleeve_sponsor_white": False,# True = flatten sleeve logo to white
    "fabric_texture": True,       # True = render micro-knit textile weave across all garment panels
    "heat_press_relief": True,    # True = render 3D contact shadow and specular rim on crests & logos
    "construction_seams": True,   # True = render athletic raglan, flank, and twin-needle hem stitching
    "tech_callout": True,         # True = render supplier fabric tech stamp (HEAT.RDY, DRI-FIT ADV, etc.)
    "inner_neck_tape": True,      # True = render authentic collar neck tape and size print on back panel
}


def _hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in range(0, 6, 2))


def _mask_img(mask):
    """numpy bool mask -> single-channel PIL mask (255 where True)."""
    import numpy as np
    return Image.fromarray((mask * 255).astype("uint8"), "L")


def _col_lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _wcag_contrast(c1, c2):
    """Compute exact WCAG relative luminance contrast ratio between two RGB colors."""
    def _rel(c):
        srgb = [v / 255.0 for v in c]
        lin = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in srgb]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    l1, l2 = _rel(c1), _rel(c2)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


# --------------------------------------------------------------------------- #
#  shirt-local design tile
# --------------------------------------------------------------------------- #
def build_tile(design):
    """Return a TILE x TILE RGBA tile: u across the shirt, v shoulder -> hem.

    Supports dual-layer composition:
    - Layer A (Macro): ombre_fade, half_half, chestband, diagonal_sash, fade_geo, solid
    - Layer B (Micro): subtle luxury jacquard overlay with soft alpha blending
    - Scale: 0.5 (micro weave 2x2), 1.0 (standard), 2.0 (macro streetwear graphic)
    """
    d = dict(DEFAULT_DESIGN)
    d.update(design)
    body = tuple(d["body"])
    second = tuple(d["second"])
    macro = d.get("macro_layout", "solid")
    micro = d.get("micro_jacquard")
    scale = float(d.get("tile_scale", 1.0))

    canvas = Image.new("RGBA", (kit_gen.W, kit_gen.H), (0, 0, 0, 0))

    # Always render the authentic curated pattern
    kit_gen.draw_pattern(canvas, d["pattern"], body, second, d["var"],
                         d["width_step"], third=d.get("third"))

    # Optional authentic macro overlay
    if macro == "ombre_fade":
        grad = Image.new("RGBA", (kit_gen.W, kit_gen.H))
        draw_g = ImageDraw.Draw(grad)
        for y in range(kit_gen.H):
            t = y / float(max(1, kit_gen.H - 1))
            alpha = int(140 * t)
            draw_g.line([(0, y), (kit_gen.W, y)], fill=second + (alpha,))
        canvas.alpha_composite(grad)
    elif macro == "half_half":
        half_img = Image.new("RGBA", (kit_gen.W, kit_gen.H), (0, 0, 0, 0))
        draw_h = ImageDraw.Draw(half_img)
        draw_h.rectangle([kit_gen.W // 2, 0, kit_gen.W, kit_gen.H], fill=second + (160,))
        canvas.alpha_composite(half_img)
    elif macro == "chestband":
        band_img = Image.new("RGBA", (kit_gen.W, kit_gen.H), (0, 0, 0, 0))
        draw_b = ImageDraw.Draw(band_img)
        y_b0, y_b1 = int(kit_gen.H * 0.38), int(kit_gen.H * 0.54)
        draw_b.rectangle([0, y_b0, kit_gen.W, y_b1], fill=second + (255,))
        tip_c = d.get("third") or body
        draw_b.line([(0, y_b0 - 2), (kit_gen.W, y_b0 - 2)], fill=tuple(tip_c) + (255,), width=3)
        draw_b.line([(0, y_b1 + 2), (kit_gen.W, y_b1 + 2)], fill=tuple(tip_c) + (255,), width=3)
        canvas.alpha_composite(band_img)

    # Optional Micro Jacquard Layer overlay
    if micro:
        j_canvas = Image.new("RGBA", (kit_gen.W, kit_gen.H), (0, 0, 0, 0))
        kit_gen.draw_pattern(j_canvas, micro, body, second, d.get("var", 0),
                             d.get("width_step", 0), third=d.get("third"))
        j_arr = np.array(j_canvas, dtype=np.float32)
        j_arr[:, :, 3] = j_arr[:, :, 3] * 0.32
        canvas.alpha_composite(Image.fromarray(j_arr.astype(np.uint8), "RGBA"))

    # Vertical shading gradient
    strength = [0.0, 0.15, 0.28, 0.40][d["gradient"] % 4]
    canvas = kit_gen.apply_gradient(canvas, strength)

    x0, y0, x1, y1 = _PREVIEW_SHIRT_BOX
    shirt = canvas.crop((x0, y0, x1, y1))

    # Procedural multi-scale UV tile
    if abs(scale - 0.5) < 0.1:
        half = shirt.resize((TILE // 2, TILE // 2), Image.LANCZOS)
        tiled = Image.new("RGBA", (TILE, TILE))
        tiled.paste(half, (0, 0))
        tiled.paste(half, (TILE // 2, 0))
        tiled.paste(half, (0, TILE // 2))
        tiled.paste(half, (TILE // 2, TILE // 2))
        return tiled

    return shirt.resize((TILE, TILE), Image.LANCZOS)


def _paint_shirt(atlas, tile, masks, d=None):
    """Paste the shirt-local tile into front/back islands with selective pattern masking."""
    boxes = kit_regions.region_boxes(masks)
    mask_mode = (d.get("pattern_mask") if d else "full") or "full"

    fx0, fy0, fx1, fy1 = boxes["body_front"]
    fw, fh = fx1 - fx0 + 1, fy1 - fy0 + 1
    front = tile.resize((fw, fh), Image.LANCZOS)
    fmask_raw = masks["body_front"][fy0:fy1 + 1, fx0:fx1 + 1].copy()

    if mask_mode == "chest_only":
        y_c0, y_c1 = int(fh * 0.28), int(fh * 0.56)
        chest_m = np.zeros_like(fmask_raw)
        chest_m[y_c0:y_c1, :] = fmask_raw[y_c0:y_c1, :]
        atlas.paste(front, (fx0, fy0), _mask_img(chest_m))
    elif mask_mode == "sash_only":
        sash_m = np.zeros_like(fmask_raw)
        for y in range(fh):
            cx = int(y * (fw / float(max(1, fh))))
            w_sash = int(fw * 0.22)
            sash_m[y, max(0, cx - w_sash):min(fw, cx + w_sash)] = True
        sash_m = sash_m & fmask_raw
        atlas.paste(front, (fx0, fy0), _mask_img(sash_m))
    elif mask_mode == "sleeves_only":
        s_box = kit_regions.region_boxes(masks)["sleeve"]
        sx0, sy0, sx1, sy1 = s_box
        sw, sh = sx1 - sx0 + 1, sy1 - sy0 + 1
        sleeve_tile = tile.resize((sw, sh), Image.LANCZOS)
        smask = _mask_img(masks["sleeve"][sy0:sy1 + 1, sx0:sx1 + 1])
        atlas.paste(sleeve_tile, (sx0, sy0), smask)
    else:
        atlas.paste(front, (fx0, fy0), _mask_img(fmask_raw))

    # Back island (always 100% clean/solid when selective masking is active for number legibility)
    if mask_mode == "full":
        bx0, by0, bx1, by1 = boxes["body_back"]
        bw, bh = bx1 - bx0 + 1, by1 - by0 + 1
        back = tile.rotate(180).resize((bw, bh), Image.LANCZOS)
        bmask = _mask_img(masks["body_back"][by0:by1 + 1, bx0:bx1 + 1])
        atlas.paste(back, (bx0, by0), bmask)


def _apply_vent_panels(atlas, d, masks):
    """Render laser-cut perforated mesh, contrast panels, or breathable stealth ribs."""
    vent_style = d.get("vent_style", "none")
    if not vent_style or vent_style == "none":
        return

    body = tuple(d["body"])
    vent_col = d.get("vent_color")
    if not vent_col:
        if vent_style == "contrast_panel":
            vent_col = d.get("second") or d.get("third")
            l_b = _col_lum(body)
            l_v = _col_lum(vent_col)
            if (max(l_b, l_v) + 12.5) / (min(l_b, l_v) + 12.5) < 2.0:
                vent_col = (int(body[0] * 0.72), int(body[1] * 0.72), int(body[2] * 0.72))
        else:
            vent_col = (max(10, int(body[0] * 0.78)),
                        max(10, int(body[1] * 0.78)),
                        max(10, int(body[2] * 0.78)))

    v_rgba = tuple(vent_col) + (255,)

    vent_mask = np.zeros((ATLAS, ATLAS), dtype=bool)
    vent_mask[1100:1850, 674:725] = masks["body_front"][1100:1850, 674:725]
    vent_mask[1100:1850, 1323:1374] = masks["body_front"][1100:1850, 1323:1374]
    vent_mask[100:850, 699:746] = masks["body_back"][100:850, 699:746]
    vent_mask[100:850, 1302:1349] = masks["body_back"][100:850, 1302:1349]
    # Torso flank and underarm ventilation only - sleeves remain clean & tailored

    if not np.any(vent_mask):
        return

    atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), v_rgba), (0, 0), _mask_img(vent_mask))

    if vent_style == "laser_cut":
        dot_rgba = (max(0, int(vent_col[0] * 0.65)),
                    max(0, int(vent_col[1] * 0.65)),
                    max(0, int(vent_col[2] * 0.65)), 255)
        y_c, x_c = np.where(vent_mask)
        dots = ((y_c % 12 < 4) & (x_c % 10 < 4))
        if np.any(dots):
            arr = np.array(atlas)
            arr[y_c[dots], x_c[dots]] = dot_rgba
            atlas.paste(Image.fromarray(arr, "RGBA"), (0, 0))
    elif vent_style == "stealth_rib":
        rib_rgba = (max(0, int(vent_col[0] * 0.75)),
                    max(0, int(vent_col[1] * 0.75)),
                    max(0, int(vent_col[2] * 0.75)), 255)
        y_c, x_c = np.where(vent_mask)
        ribs = (y_c % 8 < 3)
        if np.any(ribs):
            arr = np.array(atlas)
            arr[y_c[ribs], x_c[ribs]] = rib_rgba
            atlas.paste(Image.fromarray(arr, "RGBA"), (0, 0))


def _composite_layer(atlas, layer, mask=None):
    """Safely alpha-composite a transparent RGBA layer onto atlas, optionally clipped by mask."""
    if mask is not None:
        arr = np.array(layer)
        arr[~mask] = 0
        layer = Image.fromarray(arr, "RGBA")
    atlas.alpha_composite(layer)


def _apply_brand_signatures(atlas, d, masks):
    """Apply iconic kit supplier trademark languages across shoulders, sleeves, and shorts."""
    supp = str(d.get("supplier_name") or d.get("supplier") or "").lower()
    sleeve_mask = masks["sleeve"]
    body_back = masks["body_back"]
    shorts_mask = masks["shorts"]

    base_col = d.get("sleeve") or d["body"]
    acc = d.get("stripe_accent") or d.get("second") or (245, 245, 245)
    dist_acc = math.sqrt(sum((a - b) ** 2 for a, b in zip(base_col[:3], acc[:3])))
    # Preserve intentional metallic gold, royal purple, and pastel trims on white/light kits
    # Only override to contrast tone if accent is practically invisible (< 40 RGB distance)
    if dist_acc < 40:
        l_b = _col_lum(base_col)
        acc = (245, 245, 245) if l_b < 128 else (20, 25, 35)
    acc_rgba = tuple(acc) + (255,)

    # 1. ADIDAS: Three iconic parallel stripes running down outer shoulders/sleeves and shorts
    is_adidas = "adidas" in supp or d.get("sleeve_style") in ("shoulder_stripe", "adidas_stripes", "three_stripes")
    if is_adidas:
        stripe_mask = np.zeros_like(sleeve_mask)
        # Left sleeve outer shoulder 3-stripes (y: 215..570)
        # Calibrated directly against authentic PES 2021 UV atlas layout
        for x0, x1 in [(8, 15), (20, 27), (32, 39)]:
            stripe_mask[215:570, x0:x1] = sleeve_mask[215:570, x0:x1]

        # Right sleeve outer shoulder 3-stripes (y: 215..570)
        for x0, x1 in [(2008, 2015), (2020, 2027), (2032, 2039)]:
            stripe_mask[215:570, x0:x1] = sleeve_mask[215:570, x0:x1]

        # Raglan shoulder seam continuation onto back panel top edges
        for x0, x1 in [(700, 707), (712, 719), (724, 731)]:
            stripe_mask[60:130, x0:x1] = body_back[60:130, x0:x1]
        for x0, x1 in [(1316, 1323), (1328, 1335), (1340, 1347)]:
            stripe_mask[60:130, x0:x1] = body_back[60:130, x0:x1]

        if np.any(stripe_mask):
            stripe_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
            stripe_layer.paste(Image.new("RGBA", (ATLAS, ATLAS), acc_rgba), (0, 0), _mask_img(stripe_mask))
            _composite_layer(atlas, stripe_layer)

        # Shorts 3-stripes down outer leg seams
        sh_stripe = np.zeros_like(shorts_mask)
        sh_stripe[:, 32:38] = True
        sh_stripe[:, 42:48] = True
        sh_stripe[:, 52:58] = True
        sh_stripe[:, 1980:1986] = True
        sh_stripe[:, 1993:1999] = True
        sh_stripe[:, 2006:2012] = True
        sh_stripe = sh_stripe & shorts_mask
        if np.any(sh_stripe):
            sh_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
            sh_layer.paste(Image.new("RGBA", (ATLAS, ATLAS), acc_rgba), (0, 0), _mask_img(sh_stripe))
            _composite_layer(atlas, sh_layer)

    # 2. HUMMEL: Iconic repeating V-Chevrons
    elif "hummel" in supp:
        chevron_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_ch = ImageDraw.Draw(chevron_layer)
        for cx in range(110, 410, 36):
            draw_ch.polygon([(cx - 10, 404), (cx + 4, 413), (cx - 10, 422),
                             (cx - 3, 422), (cx + 11, 413), (cx - 3, 404)], fill=acc_rgba)
        for cx in range(1630, 1930, 36):
            draw_ch.polygon([(cx + 10, 404), (cx - 4, 413), (cx + 10, 422),
                             (cx + 3, 422), (cx - 11, 413), (cx + 3, 404)], fill=acc_rgba)
        for cy in range(1250, 1900, 42):
            draw_ch.polygon([(40, cy - 8), (48, cy), (40, cy + 8),
                             (45, cy + 8), (53, cy), (45, cy - 8)], fill=acc_rgba)
            draw_ch.polygon([(1998, cy - 8), (2006, cy), (1998, cy + 8),
                             (2003, cy + 8), (2011, cy), (2003, cy - 8)], fill=acc_rgba)
        _composite_layer(atlas, chevron_layer, sleeve_mask | shorts_mask)

    # 3. KAPPA: Iconic Banda tape
    elif "kappa" in supp:
        banda_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_b = ImageDraw.Draw(banda_layer)
        draw_b.rectangle([80, 402, 420, 424], fill=acc_rgba)
        draw_b.rectangle([1620, 402, 1960, 424], fill=acc_rgba)
        bg_col = tuple(base_col) + (255,)
        for cx in range(95, 410, 32):
            draw_b.rectangle([cx, 407, cx + 12, 419], fill=bg_col)
        for cx in range(1635, 1950, 32):
            draw_b.rectangle([cx, 407, cx + 12, 419], fill=bg_col)
        draw_b.rectangle([34, 1220, 56, 1920], fill=acc_rgba)
        draw_b.rectangle([1992, 1220, 2014, 1920], fill=acc_rgba)
        sh_base_col = tuple(d.get("shorts") or d["body"]) + (255,)
        for cy in range(1240, 1900, 36):
            draw_b.rectangle([39, cy, 51, cy + 12], fill=sh_base_col)
            draw_b.rectangle([1997, cy, 2009, cy + 12], fill=sh_base_col)
        _composite_layer(atlas, banda_layer, sleeve_mask | shorts_mask)

    # 4. UMBRO: Double Diamond repeat tape
    elif "umbro" in supp:
        umbro_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_u = ImageDraw.Draw(umbro_layer)
        for cx in range(60, 440, 32):
            draw_u.polygon([(cx, 650), (cx + 10, 660), (cx, 670), (cx - 10, 660)], outline=acc_rgba, width=2)
            draw_u.polygon([(cx, 656), (cx + 4, 660), (cx, 664), (cx - 4, 660)], fill=acc_rgba)
        for cx in range(1620, 2000, 32):
            draw_u.polygon([(cx, 650), (cx + 10, 660), (cx, 670), (cx - 10, 660)], outline=acc_rgba, width=2)
            draw_u.polygon([(cx, 656), (cx + 4, 660), (cx, 664), (cx - 4, 660)], fill=acc_rgba)
        for cx in range(100, 950, 48):
            draw_u.polygon([(cx, 1942), (cx + 10, 1952), (cx, 1962), (cx - 10, 1952)], outline=acc_rgba, width=2)
            draw_u.polygon([(cx, 1947), (cx + 4, 1952), (cx, 1957), (cx - 4, 1952)], fill=acc_rgba)
        for cx in range(1120, 1950, 48):
            draw_u.polygon([(cx, 1942), (cx + 10, 1952), (cx, 1962), (cx - 10, 1952)], outline=acc_rgba, width=2)
            draw_u.polygon([(cx, 1947), (cx + 4, 1952), (cx, 1957), (cx - 4, 1952)], fill=acc_rgba)
        _composite_layer(atlas, umbro_layer, sleeve_mask | shorts_mask)

    # 5. PUMA: T7 Formstrip broad ergonomic panel
    elif "puma" in supp:
        puma_m = np.zeros_like(sleeve_mask)
        puma_m[388:424, 39:447] = sleeve_mask[388:424, 39:447]
        puma_m[388:424, 610:692] = body_back[388:424, 610:692]
        puma_m[388:424, 1356:1438] = body_back[388:424, 1356:1438]
        puma_m[388:424, 1601:2009] = sleeve_mask[388:424, 1601:2009]
        if np.any(puma_m):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), acc_rgba), (0, 0), _mask_img(puma_m))
        sh_puma = np.zeros_like(shorts_mask)
        sh_puma[:, 28:64] = True
        sh_puma[:, 1984:2020] = True
        sh_puma = sh_puma & shorts_mask
        if np.any(sh_puma):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), acc_rgba), (0, 0), _mask_img(sh_puma))

    # 6. NIKE: Aeroswift flank ribbing (torso underarm only, sleeves stay clean)
    elif "nike" in supp:
        nike_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_n = ImageDraw.Draw(nike_layer)
        for y in range(1120, 1820, 16):
            draw_n.line([(678, y), (718, y + 6)], fill=acc_rgba, width=3)
            draw_n.line([(1328, y), (1368, y + 6)], fill=acc_rgba, width=3)
        _composite_layer(atlas, nike_layer, masks["body_front"])


def _apply_engineered_shorts(atlas, d, masks):
    """Render split-leg tailoring, lateral side stripes, or hem tape on shorts."""
    shorts_style = d.get("shorts_style", "solid")
    if not shorts_style or shorts_style in ("solid", "three_stripes"):
        return

    shorts_mask = masks["shorts"]
    shorts_base = d.get("shorts") or d["body"]
    shorts_accent = d.get("shorts_accent") or d.get("second") or (245, 245, 245)
    l_sh = _col_lum(shorts_base)
    l_acc = _col_lum(shorts_accent)
    if (max(l_sh, l_acc) + 12.5) / (min(l_sh, l_acc) + 12.5) < 2.2:
        shorts_accent = (245, 245, 245) if l_sh < 128 else (20, 25, 35)

    sh_col = tuple(shorts_accent) + (255,)

    if shorts_style == "split_leg":
        split_m = np.zeros_like(shorts_mask)
        split_m[:, 24:52] = True
        for x in range(1040, 2030):
            y_slash = int(1910 + (x - 1040) * 0.04)
            split_m[y_slash:y_slash + 20, x] = True
        split_m = split_m & shorts_mask
        if np.any(split_m):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), sh_col), (0, 0), _mask_img(split_m))
    elif shorts_style == "side_stripe":
        side_mask = np.zeros_like(shorts_mask)
        side_mask[:, 24:58] = True
        side_mask[:, 1990:2024] = True
        side_mask = side_mask & shorts_mask
        if np.any(side_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), sh_col), (0, 0), _mask_img(side_mask))
    elif shorts_style == "hem_tape":
        hem_mask = np.zeros_like(shorts_mask)
        hem_mask[1935:1968, :] = True
        hem_mask = hem_mask & shorts_mask
        if np.any(hem_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), sh_col), (0, 0), _mask_img(hem_mask))


def _apply_engineered_socks(atlas, d, masks):
    """Render turnover cuff hoops, mid-calf pro bands, or ombre gradient fades on socks."""
    socks_style = d.get("socks_style", "solid")
    if not socks_style or socks_style == "solid":
        return

    socks_mask = masks["socks"]
    socks_base = d.get("socks") or d["body"]
    socks_accent = d.get("socks_accent") or d.get("second") or (245, 245, 245)
    l_so = _col_lum(socks_base)
    l_acc = _col_lum(socks_accent)
    if (max(l_so, l_acc) + 12.5) / (min(l_so, l_acc) + 12.5) < 2.2:
        socks_accent = (245, 245, 245) if l_so < 128 else (20, 25, 35)

    so_col = tuple(socks_accent) + (255,)

    if socks_style == "turnover_hoop":
        cuff_so = np.zeros_like(socks_mask)
        cuff_so[630:695, :] = True
        cuff_so = cuff_so & socks_mask
        if np.any(cuff_so):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), so_col), (0, 0), _mask_img(cuff_so))
            so_tip = d.get("socks_tip") or d["body"]
            so_tip_mask = np.zeros_like(socks_mask)
            so_tip_mask[690:696, :] = True
            so_tip_mask = so_tip_mask & socks_mask
            if np.any(so_tip_mask):
                atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tuple(so_tip) + (255,)), (0, 0), _mask_img(so_tip_mask))
    elif socks_style == "calf_band":
        band_so = np.zeros_like(socks_mask)
        band_so[830:875, :] = True
        band_so = band_so & socks_mask
        if np.any(band_so):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), so_col), (0, 0), _mask_img(band_so))
    elif socks_style == "gradient_fade":
        fade_so = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_f = ImageDraw.Draw(fade_so)
        for y in range(630, 1150):
            t = (y - 630) / float(max(1, 1150 - 630))
            c = (int(socks_base[0] * (1 - t) + socks_accent[0] * t),
                 int(socks_base[1] * (1 - t) + socks_accent[1] * t),
                 int(socks_base[2] * (1 - t) + socks_accent[2] * t), 255)
            draw_f.line([(0, y), (ATLAS, y)], fill=c)
        _composite_layer(atlas, fade_so, masks["socks"])


def _apply_engineered_collar(atlas, d, masks):
    """Render authentic collar styling: crew, v_neck, polo (with placket), or dual_tipped."""
    style = d.get("collar_style", "crew")
    collar_mask = masks["collar"]
    body_front = masks["body_front"]

    collar = tuple(d.get("collar") or d["body"])
    tip1 = tuple(d.get("collar_tip") or d.get("second") or collar)
    tip2 = tuple(d.get("third") or d.get("second") or tip1)

    c_rgba = collar + (255,)
    t1_rgba = tip1 + (255,)
    t2_rgba = tip2 + (255,)

    if style == "dual_tipped":
        # Two-tone engineered tipping band along outer ribbing edge (y: 1868..1884)
        t1_mask = np.zeros_like(collar_mask)
        t1_mask[1868:1874, :] = collar_mask[1868:1874, :]
        if np.any(t1_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(t1_mask))

        t2_mask = np.zeros_like(collar_mask)
        t2_mask[1878:1884, :] = collar_mask[1878:1884, :]
        if np.any(t2_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t2_rgba), (0, 0), _mask_img(t2_mask))

    elif style == "v_neck":
        # Tipped outer ribbing edge
        t_mask = np.zeros_like(collar_mask)
        t_mask[1868:1880, :] = collar_mask[1868:1880, :]
        if np.any(t_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(t_mask))

        # Sharp triangular crossover wedge / insert at chest apex of body_front (centered at x=1024, y=1000..1058)
        v_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_v = ImageDraw.Draw(v_layer)
        draw_v.polygon([(994, 1000), (1054, 1000), (1024, 1058)], fill=c_rgba)
        draw_v.line([(994, 1000), (1024, 1058)], fill=t1_rgba, width=3)
        draw_v.line([(1054, 1000), (1024, 1058)], fill=t1_rgba, width=3)
        _composite_layer(atlas, v_layer, body_front)

    elif style == "polo":
        # Shaded fold crease on collar island
        crease_mask = np.zeros_like(collar_mask)
        crease_mask[1945:1950, :] = collar_mask[1945:1950, :]
        if np.any(crease_mask):
            crease_col = (max(0, int(collar[0] * 0.75)),
                          max(0, int(collar[1] * 0.75)),
                          max(0, int(collar[2] * 0.75)), 220)
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), crease_col), (0, 0), _mask_img(crease_mask))

        # Outer tipping on the folded wings edge
        t_mask = np.zeros_like(collar_mask)
        t_mask[1868:1878, :] = collar_mask[1868:1878, :]
        if np.any(t_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(t_mask))

        # Engineered button placket down chest center (X: 1008..1040, Y: 1000..1095)
        placket_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_p = ImageDraw.Draw(placket_layer)
        draw_p.rectangle([1008, 1000, 1040, 1095], fill=c_rgba)
        draw_p.rectangle([1008, 1000, 1040, 1095], outline=t1_rgba, width=2)
        draw_p.line([(1024, 1000), (1024, 1092)], fill=t1_rgba, width=1)
        btn_col = (245, 245, 248, 255) if _col_lum(collar) < 160 else (25, 25, 30, 255)
        thread_col = (40, 40, 45, 255) if _col_lum(collar) < 160 else (240, 240, 245, 255)
        for by in (1030, 1070):
            draw_p.ellipse([1020, by - 4, 1028, by + 4], fill=btn_col, outline=t1_rgba, width=1)
            draw_p.line([(1022, by), (1026, by)], fill=thread_col, width=1)
            draw_p.line([(1024, by - 2), (1024, by + 2)], fill=thread_col, width=1)

        _composite_layer(atlas, placket_layer, body_front)

    else:
        # Classic Crew / Round Neck: outer ribbing tipping band + subtle elastic ribbing
        if tip1 != collar:
            t_mask = np.zeros_like(collar_mask)
            t_mask[1868:1882, :] = collar_mask[1868:1882, :]
            if np.any(t_mask):
                atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(t_mask))

        y_c, x_c = np.where(collar_mask)
        ribs = (x_c % 6 < 2)
        if np.any(ribs):
            rib_col = (max(0, int(collar[0] * 0.88)),
                       max(0, int(collar[1] * 0.88)),
                       max(0, int(collar[2] * 0.88)), 160)
            arr = np.array(atlas)
            arr[y_c[ribs], x_c[ribs]] = rib_col
            atlas.paste(Image.fromarray(arr, "RGBA"), (0, 0))



# --------------------------------------------------------------------------- #
#  Authentic Garment Details, Seams, Micro-Textures & 3D Relief
# --------------------------------------------------------------------------- #
def _composite_with_relief(atlas, img, x, y, relief_depth=2, shadow_opacity=65, highlight_opacity=35, mask=None):
    """Composite logo with subtle 3D contact shadow and specular rim light (silicone heat-press relief)."""
    if img is None:
        return
    w, h = img.size
    alpha = np.array(img.split()[-1], dtype=np.float32)
    if not np.any(alpha > 10):
        if mask is not None:
            layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
            layer.paste(img, (x, y), img)
            _composite_layer(atlas, layer, mask)
        else:
            atlas.alpha_composite(img, (x, y))
        return

    # 1. Contact drop shadow (offset +1, +relief_depth)
    sh_alpha = (alpha * (shadow_opacity / 255.0)).astype(np.uint8)
    shadow_arr = np.zeros((h, w, 4), dtype=np.uint8)
    shadow_arr[:, :, :3] = (15, 15, 20)
    shadow_arr[:, :, 3] = sh_alpha
    shadow_img = Image.fromarray(shadow_arr, "RGBA")

    # 2. Specular top-edge rim highlight (offset -1, -1)
    hl_alpha = (alpha * (highlight_opacity / 255.0)).astype(np.uint8)
    hl_arr = np.zeros((h, w, 4), dtype=np.uint8)
    hl_arr[:, :, :3] = (255, 255, 255)
    hl_arr[:, :, 3] = hl_alpha
    hl_img = Image.fromarray(hl_arr, "RGBA")

    layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
    layer.paste(shadow_img, (x + 1, y + relief_depth), shadow_img)
    layer.paste(hl_img, (x - 1, y - 1), hl_img)
    layer.paste(img, (x, y), img)

    if mask is not None:
        _composite_layer(atlas, layer, mask)
    else:
        atlas.alpha_composite(layer)


def _apply_fabric_microtexture(atlas, d, masks):
    """Apply authentic micro-knit textile weave across all garment fabric panels.

    Subtly modulates fabric luminance by +/- 2.5%, producing a rich, tactile,
    matte athletic cloth appearance in 3D replays and close-ups without altering team colors.
    """
    if not d.get("fabric_texture", True):
        return

    fabric_mask = np.zeros((ATLAS, ATLAS), dtype=bool)
    for key in ("body_front", "body_back", "sleeve", "shorts", "socks", "collar"):
        m = masks.get(key)
        if m is not None:
            fabric_mask |= m

    if not np.any(fabric_mask):
        return

    kernel_4x4 = np.array([
        [ 3.0, -3.0,  2.0, -2.0],
        [-2.0,  3.0, -3.0,  2.0],
        [ 2.0, -2.0,  3.0, -3.0],
        [-3.0,  2.0, -2.0,  3.0],
    ], dtype=np.float32)

    weave_tile = np.tile(kernel_4x4, (ATLAS // 4, ATLAS // 4))

    arr = np.array(atlas, dtype=np.float32)
    rgb = arr[:, :, :3]
    rgb[fabric_mask] = np.clip(rgb[fabric_mask] + weave_tile[fabric_mask, None], 0, 255)
    arr[:, :, :3] = rgb

    atlas.paste(Image.fromarray(arr.astype(np.uint8), "RGBA"), (0, 0))


def _apply_construction_seams(atlas, d, masks):
    """Render athletic panel construction lines, raglan seams, and twin-needle hem stitching."""
    if not d.get("construction_seams", True):
        return

    body = tuple(d["body"])
    dark_stitch = (max(0, int(body[0] * 0.74)), max(0, int(body[1] * 0.74)), max(0, int(body[2] * 0.74)), 180)
    light_stitch = (min(255, int(body[0] * 1.15) + 15), min(255, int(body[1] * 1.15) + 15), min(255, int(body[2] * 1.15) + 15), 120)

    seam_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(seam_layer)

    bf = masks.get("body_front")
    bb = masks.get("body_back")
    sleeve_m = masks.get("sleeve")
    shorts_m = masks.get("shorts")

    # 1. Torso flank side seams (front: y: 1180..1845, back: y: 280..900)
    for sx in (724, 1324):
        draw.line([(sx, 1180), (sx, 1845)], fill=dark_stitch, width=1)
        draw.line([(sx + 1, 1180), (sx + 1, 1845)], fill=light_stitch, width=1)
        draw.line([(sx, 280), (sx, 900)], fill=dark_stitch, width=1)
        draw.line([(sx + 1, 280), (sx + 1, 900)], fill=light_stitch, width=1)

    # 2. Raglan shoulder/armhole seams
    draw.line([(870, 1020), (724, 1180)], fill=dark_stitch, width=1)
    draw.line([(871, 1021), (725, 1181)], fill=light_stitch, width=1)
    draw.line([(1178, 1020), (1324, 1180)], fill=dark_stitch, width=1)
    draw.line([(1177, 1021), (1323, 1181)], fill=light_stitch, width=1)

    draw.line([(870, 120), (724, 280)], fill=dark_stitch, width=1)
    draw.line([(871, 121), (725, 281)], fill=light_stitch, width=1)
    draw.line([(1178, 120), (1324, 280)], fill=dark_stitch, width=1)
    draw.line([(1177, 121), (1323, 281)], fill=light_stitch, width=1)

    # 3. Twin-needle lower hem stitching
    draw.line([(724, 1838), (1324, 1838)], fill=dark_stitch, width=1)
    draw.line([(724, 1844), (1324, 1844)], fill=dark_stitch, width=1)
    draw.line([(724, 896), (1324, 896)], fill=dark_stitch, width=1)
    draw.line([(724, 902), (1324, 902)], fill=dark_stitch, width=1)

    # 4. Sleeve cuff twin-needle hem stitching
    if sleeve_m is not None:
        draw.line([(40, 658), (640, 658)], fill=dark_stitch, width=1)
        draw.line([(40, 663), (640, 663)], fill=dark_stitch, width=1)
        draw.line([(1400, 658), (2000, 658)], fill=dark_stitch, width=1)
        draw.line([(1400, 663), (2000, 663)], fill=dark_stitch, width=1)

    # 5. Shorts bottom leg hem stitching
    if shorts_m is not None:
        draw.line([(45, 1932), (590, 1932)], fill=dark_stitch, width=1)
        draw.line([(45, 1938), (590, 1938)], fill=dark_stitch, width=1)
        draw.line([(1455, 1932), (2000, 1932)], fill=dark_stitch, width=1)
        draw.line([(1455, 1938), (2000, 1938)], fill=dark_stitch, width=1)

    garment_mask = (bf | bb | sleeve_m | shorts_m) if bf is not None else None
    _composite_layer(atlas, seam_layer, garment_mask)


def _render_inner_neck_detail(atlas, d, masks):
    """Render authentic collar inner neck tape ribbon and size/authenticity print on upper back panel."""
    if not d.get("inner_neck_tape", True):
        return

    bb = masks.get("body_back")
    if bb is None:
        return

    tape_col = tuple(d.get("second") or d.get("accent") or (240, 240, 245)) + (235,)
    tip_col = tuple(d.get("accent") or d.get("third") or d["body"]) + (255,)

    tape_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tape_layer)

    tape_y = 80
    draw.rectangle([964, tape_y, 1084, tape_y + 10], fill=tape_col)
    draw.line([(964, tape_y), (1084, tape_y)], fill=tip_col, width=2)
    draw.line([(964, tape_y + 9), (1084, tape_y + 9)], fill=tip_col, width=2)

    body = tuple(d["body"])
    l_b = _col_lum(body)
    label_col = (235, 235, 240, 190) if l_b < 128 else (30, 35, 45, 190)

    try:
        font = ImageFont.load_default()
        draw.text((1002, 98), "AUTHENTIC", fill=label_col, font=font)
        draw.rectangle([1016, 114, 1032, 126], outline=label_col, width=1)
        draw.text((1021, 115), "M", fill=label_col, font=font)
    except Exception:
        draw.rectangle([1004, 102, 1044, 116], outline=label_col, width=1)

    _composite_layer(atlas, tape_layer, bb)


def _render_tech_callout(atlas, d, masks):
    """Render authentic supplier fabric performance technology heat-stamp at lower right hem."""
    if not d.get("tech_callout", True):
        return

    bf = masks.get("body_front")
    if bf is None:
        return

    supp = str(d.get("supplier_name") or d.get("supplier") or "").lower()
    if "nike" in supp:
        tech_text = "DRI-FIT ADV"
    elif "adidas" in supp:
        tech_text = "HEAT.RDY"
    elif "puma" in supp:
        tech_text = "ULTRAWEAVE"
    elif "hummel" in supp:
        tech_text = "BEECOOL"
    elif "umbro" in supp:
        tech_text = "PRO WEAVE"
    elif "kappa" in supp:
        tech_text = "KOMBAT PRO"
    elif "macron" in supp:
        tech_text = "M-PERFORMANCE"
    elif "castore" in supp:
        tech_text = "PRO PRECISION"
    else:
        tech_text = "PRO ATHLETIC"

    cx, cy = 775, 1835
    w, h = 90, 20
    x0, y0 = int(cx - w / 2), int(cy - h / 2)

    body = tuple(d["body"])
    l_b = _col_lum(body)
    text_col = (220, 225, 235, 210) if l_b < 128 else (35, 40, 48, 210)
    accent_dot = (212, 175, 55, 230) if l_b < 128 else (180, 140, 40, 230)

    tech_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tech_img)

    draw.rectangle([2, 8, 8, 12], fill=accent_dot)
    try:
        font = ImageFont.load_default()
        draw.text((12, 4), tech_text, fill=text_col, font=font)
    except Exception:
        draw.line([(12, 10), (w - 4, 10)], fill=text_col, width=2)

    tech_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
    tech_layer.paste(tech_img, (x0, y0), tech_img)
    _composite_layer(atlas, tech_layer, bf)


# --------------------------------------------------------------------------- #
#  main painter
# --------------------------------------------------------------------------- #
def render_kit(design, out_png, masks=None):
    """Paint `design` into the UV atlas and save a 2048x2048 RGBA PNG."""
    masks = masks if masks is not None else kit_regions.build_masks()

    d = dict(DEFAULT_DESIGN)
    d.update(design)

    # Special metallic & finish overrides
    finish = d.get("finish", "standard")
    if finish == "liquid_gold":
        d["accent"] = (220, 185, 80)
        d["stripe_accent"] = (220, 185, 80)
    elif finish == "chrome_silver":
        d["accent"] = (205, 215, 225)
        d["stripe_accent"] = (205, 215, 225)
    elif finish == "copper_bronze":
        d["accent"] = (205, 125, 75)
        d["stripe_accent"] = (205, 125, 75)
    elif finish == "cyber_neon":
        d["accent"] = (215, 255, 30) if _col_lum(d["body"]) < 100 else (255, 20, 140)
        d["stripe_accent"] = d["accent"]

    body = tuple(d["body"])
    sleeve = tuple(d["sleeve"] or d["body"])
    shorts = tuple(d["shorts"] or d["body"])
    socks = tuple(d["socks"] or d["body"])
    collar = tuple(d["collar"] or d["body"])

    atlas = Image.new("RGBA", (ATLAS, ATLAS), body + (255,))

    # Shirt front + back (with selective masking support)
    _paint_shirt(atlas, build_tile(d), masks, d)

    # Sleeves / shorts / socks / collar base
    # (Skip solid sleeves paste if pattern_mask == "sleeves_only" so graphic remains visible)
    regions_to_fill = [("shorts", shorts), ("socks", socks), ("collar", collar)]
    if d.get("pattern_mask") != "sleeves_only":
        regions_to_fill.insert(0, ("sleeve", sleeve))

    for region, colour in regions_to_fill:
        atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), colour + (255,)),
                    (0, 0), _mask_img(masks[region]))

    # ----------------------------------------------------------------------- #
    #  Modern 2026/2027 Streetwear Tailoring & Trim Layers
    # ----------------------------------------------------------------------- #
    # 1. Breathable underarm & side flank vent panels
    _apply_vent_panels(atlas, d, masks)

    # 2. Supplier signature languages (Adidas, Hummel, Kappa, Umbro, Puma, Nike)
    _apply_brand_signatures(atlas, d, masks)

    # 3. Contrast sleeve cuff bands + engineered tipping line (slim, modern athletic cut)
    cuff = d.get("cuff")
    if cuff:
        cuff_col = tuple(cuff) + (255,)
        sleeve_mask = masks["sleeve"]
        cuff_mask = np.zeros_like(sleeve_mask)
        # Reduced slim cuff height: 16px (664..680) instead of bulky 40px band
        cuff_mask[664:680, :] = sleeve_mask[664:680, :]
        if np.any(cuff_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), cuff_col),
                        (0, 0), _mask_img(cuff_mask))
        cuff_tip = d.get("cuff_tip")
        if cuff_tip and cuff_tip != cuff:
            tip_col = tuple(cuff_tip) + (255,)
            tip_mask = np.zeros_like(sleeve_mask)
            # Engineered 4px micro-tipping along cuff hem edge
            tip_mask[676:680, :] = sleeve_mask[676:680, :]
            if np.any(tip_mask):
                atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col),
                            (0, 0), _mask_img(tip_mask))

    # 4. Tailored collar architecture (crew, v_neck, polo, dual_tipped)
    _apply_engineered_collar(atlas, d, masks)

    # 5. Tailored shorts & socks
    _apply_engineered_shorts(atlas, d, masks)
    _apply_engineered_socks(atlas, d, masks)

    # ----------------------------------------------------------------------- #
    #  Authentic Garment Construction, Seams & Micro-Texture
    # ----------------------------------------------------------------------- #
    # 6. Athletic panel construction lines & twin-needle hem stitching
    _apply_construction_seams(atlas, d, masks)

    # 7. Collar inner neck tape ribbon & match sizing print
    _render_inner_neck_detail(atlas, d, masks)

    # 8. Procedural micro-knit textile weave across all garment panels
    _apply_fabric_microtexture(atlas, d, masks)

    # logos with runtime UV validation & collision adjustment
    sp_item = None
    if d.get("sponsor"):
        # Sample actual rendered canvas background under chest sponsor to guarantee high contrast
        if not d.get("sponsor_plate"):
            sample_arr = np.array(atlas)[1250:1370, 880:1168, :3]
            sample_lums = 0.2126 * sample_arr[:, :, 0] + 0.7152 * sample_arr[:, :, 1] + 0.0722 * sample_arr[:, :, 2]
            bg_lum = float(np.mean(sample_lums))
            if bg_lum < 130:
                d["sponsor_white"] = True
                d.pop("sponsor_dark", None)
                p_obj = Path(d["sponsor"])
                if not p_obj.stem.endswith("_white"):
                    cand_w = p_obj.parent / f"{p_obj.stem}_white.png"
                    if cand_w.is_file():
                        d["sponsor"] = str(cand_w)
            else:
                d["sponsor_white"] = False
                p_obj = Path(d["sponsor"])
                if p_obj.stem.endswith("_white"):
                    orig_stem = p_obj.stem[:-6]
                    cand_d = p_obj.parent / f"{orig_stem}.png"
                    if cand_d.is_file():
                        d["sponsor"] = str(cand_d)
                    else:
                        d["sponsor_dark"] = (15, 25, 45)

        sp_item = _prepare_stamp_item(d["sponsor"], *kit_regions.CHEST_SPONSOR,
                                      white=d.get("sponsor_white"),
                                      dark=d.get("sponsor_dark"),
                                      plate=body if d.get("sponsor_plate") else None,
                                      max_w=340, max_h=140)
    bg_item = None
    if d.get("badge"):
        bg_item = _prepare_stamp_item(d["badge"], *kit_regions.CLUB_BADGE,
                                      white=d.get("badge_white"),
                                      max_w=85, max_h=85, defringe=False)
    sup_item = None
    if d.get("supplier"):
        sup_col = d.get("supplier_color")
        sup_item = _prepare_stamp_item(d["supplier"], *kit_regions.KIT_SUPPLIER,
                                       white=d.get("supplier_white") if not sup_col else False,
                                       dark=sup_col,
                                       max_w=90, max_h=48, defringe=True)

    # Validate against masks["body_front"] UV region and prevent inter-stamp collisions
    stamps_adj = kit_regions.validate_and_adjust_stamps(
        masks, sponsor=sp_item, badge=bg_item, supplier=sup_item
    )

    for key, item in (("supplier", sup_item), ("badge", bg_item), ("sponsor", sp_item)):
        if not item:
            continue
        adj = stamps_adj.get(key)
        if not adj:
            continue
        cur_w, cur_h = adj["w"], adj["h"]
        x, y = adj["x"], adj["y"]
        img = item["img"]
        if (cur_w, cur_h) != img.size:
            img = img.resize((cur_w, cur_h), Image.LANCZOS)

        if item.get("plate") is not None:
            pad_x, pad_y = adj.get("plate_pad") or (int(cur_w * 0.10), int(cur_h * 0.35))
            draw = ImageDraw.Draw(atlas)
            draw.rectangle([x - pad_x, y - pad_y, x + cur_w + pad_x, y + cur_h + pad_y],
                           fill=tuple(item["plate"]) + (255,))

        if d.get("heat_press_relief", True):
            _composite_with_relief(atlas, img, x, y, relief_depth=2, shadow_opacity=65, highlight_opacity=35)
        else:
            atlas.alpha_composite(img, (x, y))

    # 9. Shorts branding (Right leg club badge, Left leg supplier mark)
    _render_shorts_branding(atlas, d, masks)

    # 10. Lower shirt hem authenticity jocktag
    _render_jocktag(atlas, d, masks)

    # 11. Supplier performance fabric tech stamp (HEAT.RDY, DRI-FIT ADV, etc.)
    _render_tech_callout(atlas, d, masks)

    # 12. Sleeve secondary sponsor (Left sleeve UV island: Component 2)
    _render_sleeve_sponsor(atlas, d, masks)

    if out_png:
        atlas.save(out_png)
        return out_png
    return atlas


def _defringe_white(logo):
    """Clean un-matted white fringe on semi-transparent edges of harvested badges."""
    import numpy as np
    arr = np.array(logo, dtype=np.float32)
    a = arr[:, :, 3]
    faint = (a > 0) & (a < 45)
    arr[faint, 3] = 0
    semi = (arr[:, :, 3] >= 45) & (arr[:, :, 3] < 250)
    if np.any(semi):
        alpha_frac = arr[semi, 3:4] / 255.0
        rgb = arr[semi, :3]
        unmatted = (rgb - 255.0 * (1.0 - alpha_frac)) / np.maximum(0.01, alpha_frac)
        arr[semi, :3] = np.clip(unmatted, 0, 255)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _prepare_stamp_item(logo_path, cx, cy, area, white=False, dark=None, plate=None, max_w=None, max_h=None, defringe=True):
    """Load, defringe, tint and measure a logo before validation and placement."""
    if not logo_path or not Path(logo_path).is_file():
        return None
    logo = Image.open(logo_path).convert("RGBA")
    bbox = logo.getbbox()
    if bbox:
        logo = logo.crop(bbox)
    if defringe:
        logo = _defringe_white(logo)
    if white:
        logo = _flatten_white(logo)
    elif dark:
        col = dark if isinstance(dark, (tuple, list)) else (15, 25, 45)
        logo = _flatten_color(logo, col)
    w, h = logo.size
    scale = (float(area) / max(1, w * h)) ** 0.5
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))

    if max_w and nw > max_w:
        s = max_w / float(nw)
        nw = max_w
        nh = max(1, int(round(nh * s)))
    if max_h and nh > max_h:
        s = max_h / float(nh)
        nh = max_h
        nw = max(1, int(round(nw * s)))

    logo = logo.resize((nw, nh), Image.LANCZOS)
    arr = np.asarray(logo)
    alpha = arr[:, :, 3] if (arr.ndim == 3 and arr.shape[2] == 4) else None
    pad = (int(nw * 0.10), int(nh * 0.35)) if plate is not None else None
    return {
        "img": logo, "cx": cx, "cy": cy, "w": nw, "h": nh,
        "alpha": alpha, "plate": plate, "plate_pad": pad
    }


def _stamp_area(atlas, logo_path, cx, cy, area, white=False, dark=None, plate=None, max_w=None, max_h=None):
    """Fallback helper to place a logo centred on (cx, cy)."""
    item = _prepare_stamp_item(logo_path, cx, cy, area, white=white, dark=dark, plate=plate, max_w=max_w, max_h=max_h)
    if not item:
        return
    x, y = int(cx - item["w"] / 2), int(cy - item["h"] / 2)
    if plate is not None:
        pad_x, pad_y = item["plate_pad"]
        draw = ImageDraw.Draw(atlas)
        draw.rectangle([x - pad_x, y - pad_y, x + item["w"] + pad_x, y + item["h"] + pad_y],
                       fill=tuple(plate) + (255,))
    atlas.alpha_composite(item["img"], (x, y))


def _flatten_white(logo):
    """Return a white silhouette keeping the logo's alpha."""
    import numpy as np
    a = np.asarray(logo).copy()
    a[:, :, 0] = 255
    a[:, :, 1] = 255
    a[:, :, 2] = 255
    return Image.fromarray(a, "RGBA")


def _flatten_color(logo, color):
    """Return a monochrome silhouette in the specified RGB color keeping the logo's alpha."""
    import numpy as np
    a = np.asarray(logo).copy()
    a[:, :, 0] = color[0]
    a[:, :, 1] = color[1]
    a[:, :, 2] = color[2]
    return Image.fromarray(a, "RGBA")


def _render_jocktag(atlas, d, masks):
    """Render authentic engineered hologram / woven metallic jocktag at lower shirt hem."""
    if not d.get("jocktag", True):
        return

    bf = masks.get("body_front")
    if bf is None:
        return

    w, h = 50, 26
    cx, cy = kit_regions.JOCKTAG_ANCHOR[0], kit_regions.JOCKTAG_ANCHOR[1]

    # Validate against body_front
    tag_item = {"cx": cx, "cy": cy, "w": w, "h": h}
    adj = kit_regions.validate_and_adjust_stamps(masks, jocktag=tag_item).get("jocktag")
    if adj:
        cx, cy = adj["cx"], adj["cy"]
        w, h = adj["w"], adj["h"]
    x0, y0 = int(cx - w / 2), int(cy - h / 2)

    finish = d.get("finish", "standard")

    if finish == "liquid_gold":
        bg_col = (42, 36, 20, 245)
        border_col = (212, 175, 55, 255)
        holo_col = (245, 215, 110, 220)
        text_col = (220, 190, 80, 240)
    elif finish == "chrome_silver":
        bg_col = (30, 32, 38, 245)
        border_col = (195, 205, 215, 255)
        holo_col = (230, 240, 250, 220)
        text_col = (210, 220, 230, 240)
    elif finish == "copper_bronze":
        bg_col = (40, 28, 22, 245)
        border_col = (190, 120, 60, 255)
        holo_col = (235, 160, 100, 220)
        text_col = (215, 140, 80, 240)
    else:
        bg_col = (20, 22, 26, 240)
        border_col = (160, 165, 175, 230)
        holo_col = (210, 215, 225, 200)
        text_col = (175, 180, 190, 230)

    tag_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tag_img)

    # 1. Rounded rectangle outer body
    draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=3, fill=bg_col, outline=border_col, width=1)

    # 2. Vertical holographic security strip on left side (x: 4..10)
    for hy in range(3, h - 3):
        lum_mod = int(25 * math.sin(hy * 1.5))
        strip_c = (
            min(255, max(0, holo_col[0] + lum_mod)),
            min(255, max(0, holo_col[1] + lum_mod)),
            min(255, max(0, holo_col[2] + lum_mod)),
            holo_col[3]
        )
        draw.line([(4, hy), (10, hy)], fill=strip_c, width=1)

    # 3. Geometric micro-lines simulating authenticity chip
    draw.line([(15, 7), (w - 6, 7)], fill=text_col, width=1)
    draw.line([(15, 12), (w - 12, 12)], fill=(text_col[0], text_col[1], text_col[2], int(text_col[3] * 0.7)), width=1)
    draw.line([(15, 17), (w - 8, 17)], fill=(text_col[0], text_col[1], text_col[2], int(text_col[3] * 0.5)), width=1)

    # 4. Tiny metallic authentic dot watermark in bottom-right corner
    draw.ellipse([w - 9, h - 9, w - 5, h - 5], fill=border_col)

    # Composite onto atlas strictly within body_front
    tag_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
    tag_layer.paste(tag_img, (x0, y0), tag_img)
    _composite_layer(atlas, tag_layer, bf)


def _render_shorts_branding(atlas, d, masks):
    """Render authentic club crest on right leg and supplier mark on left leg of shorts."""
    shorts_mask = masks.get("shorts")
    if shorts_mask is None:
        return

    # 1. Shorts Club Badge (Right leg)
    if d.get("shorts_badge", True) and d.get("badge"):
        badge_white = d.get("badge_white", False)
        bg_item = _prepare_stamp_item(
            d["badge"], *kit_regions.SHORTS_BADGE,
            white=badge_white,
            max_w=68, max_h=68, defringe=False
        )
        if bg_item:
            adj = kit_regions.validate_and_adjust_stamps(
                masks, shorts_badge=bg_item
            ).get("shorts_badge")
            if adj:
                cur_w, cur_h = adj["w"], adj["h"]
                img = bg_item["img"]
                if (cur_w, cur_h) != img.size:
                    img = img.resize((cur_w, cur_h), Image.LANCZOS)

                if d.get("heat_press_relief", True):
                    _composite_with_relief(atlas, img, adj["x"], adj["y"], relief_depth=1, shadow_opacity=55, highlight_opacity=30, mask=shorts_mask)
                else:
                    stamp_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
                    stamp_layer.paste(img, (adj["x"], adj["y"]), img)
                    _composite_layer(atlas, stamp_layer, shorts_mask)

    # 2. Shorts Supplier Logo (Left leg)
    if d.get("shorts_supplier", True) and d.get("supplier"):
        shorts_base = d.get("shorts") or d["body"]
        l_sh = _col_lum(shorts_base)

        sup_col = d.get("supplier_color")
        if sup_col:
            l_sc = _col_lum(sup_col)
            if (max(l_sh, l_sc) + 12.5) / (min(l_sh, l_sc) + 12.5) < 2.0:
                sup_col = (245, 245, 245) if l_sh < 128 else (20, 25, 35)
        else:
            cand_acc = d.get("shorts_accent") or d.get("second")
            if cand_acc:
                l_acc = _col_lum(cand_acc)
                if (max(l_sh, l_acc) + 12.5) / (min(l_sh, l_acc) + 12.5) >= 2.2:
                    sup_col = cand_acc
                else:
                    sup_col = (245, 245, 245) if l_sh < 128 else (20, 25, 35)
            else:
                sup_col = (245, 245, 245) if l_sh < 128 else (20, 25, 35)

        sup_white = (sup_col == (245, 245, 245) or d.get("supplier_white", False))
        sup_item = _prepare_stamp_item(
            d["supplier"], *kit_regions.SHORTS_SUPPLIER,
            white=sup_white if not sup_col or sup_col == (245, 245, 245) else False,
            dark=sup_col if not sup_white else None,
            max_w=68, max_h=38, defringe=True
        )
        if sup_item:
            adj = kit_regions.validate_and_adjust_stamps(
                masks, shorts_supplier=sup_item
            ).get("shorts_supplier")
            if adj:
                cur_w, cur_h = adj["w"], adj["h"]
                img = sup_item["img"]
                if (cur_w, cur_h) != img.size:
                    img = img.resize((cur_w, cur_h), Image.LANCZOS)

                if d.get("heat_press_relief", True):
                    _composite_with_relief(atlas, img, adj["x"], adj["y"], relief_depth=1, shadow_opacity=55, highlight_opacity=30, mask=shorts_mask)
                else:
                    stamp_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
                    stamp_layer.paste(img, (adj["x"], adj["y"]), img)
                    _composite_layer(atlas, stamp_layer, shorts_mask)


def _render_sleeve_sponsor(atlas, d, masks):
    """Anchor secondary sponsor logo on Left Sleeve UV island oriented along sleeve wrap angle."""
    sleeve_sp = d.get("sleeve_sponsor")
    if not sleeve_sp:
        return

    # Resolve logo file path
    p = Path(sleeve_sp)
    if not p.is_file():
        # Check standard sleeve logos directories
        candidates = [
            Path(__file__).resolve().parent / "sleeve_logos" / f"{sleeve_sp}.png",
            Path(__file__).resolve().parent.parent / "content" / "KitGenerator" / "sleeve_logos" / f"{sleeve_sp}.png",
            Path(__file__).resolve().parent / "sleeve_logos" / f"{sleeve_sp}_white.png",
            Path(__file__).resolve().parent.parent / "content" / "KitGenerator" / "sleeve_logos" / f"{sleeve_sp}_white.png",
        ]
        found = False
        for cand in candidates:
            if cand.is_file():
                p = cand
                found = True
                break
        if not found:
            return

    # Sample canvas background under sleeve sponsor region to guarantee WCAG high contrast
    # Left sleeve anchor center: (1515, 405)
    sample_arr = np.array(atlas)[350:460, 1450:1580, :3]
    sample_lums = 0.2126 * sample_arr[:, :, 0] + 0.7152 * sample_arr[:, :, 1] + 0.0722 * sample_arr[:, :, 2]
    bg_lum = float(np.mean(sample_lums))

    if bg_lum < 130 or d.get("sleeve_sponsor_white"):
        # Dark sleeve fabric: pick white variant
        if not p.stem.endswith("_white"):
            cand_w = p.parent / f"{p.stem}_white.png"
            if cand_w.is_file():
                p = cand_w
    else:
        # Light sleeve fabric: pick color variant
        if p.stem.endswith("_white"):
            cand_c = p.parent / f"{p.stem[:-6]}.png"
            if cand_c.is_file():
                p = cand_c

    # Prepare stamp item
    cx, cy, area = kit_regions.SLEEVE_SPONSOR_LEFT
    wrap_angle = float(d.get("sleeve_sponsor_angle", kit_regions.SLEEVE_WRAP_ANGLE))
    item = _prepare_stamp_item(str(p), cx, cy, area, max_w=180, max_h=80, defringe=True)
    if not item:
        return

    # Validate against masks['sleeve']
    item["angle"] = wrap_angle
    adj = kit_regions.validate_and_adjust_stamps(masks, sleeve_sponsor=item).get("sleeve_sponsor")
    if not adj:
        return

    cur_w, cur_h = adj["w"], adj["h"]
    cx, cy = adj["cx"], adj["cy"]
    img = item["img"]
    if (cur_w, cur_h) != img.size:
        img = img.resize((cur_w, cur_h), Image.LANCZOS)

    # Rotate along sleeve wrap angle (positive degrees = clockwise for arm drape)
    if abs(wrap_angle) > 0.01:
        img_rot = img.rotate(-wrap_angle, resample=Image.BICUBIC, expand=True)
    else:
        img_rot = img

    rw, rh = img_rot.size
    rx = int(cx - rw / 2)
    ry = int(cy - rh / 2)

    # Stamp layer composite with sleeve mask clipping
    stamp_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
    stamp_layer.paste(img_rot, (rx, ry), img_rot)

    sleeve_mask = masks.get("sleeve") if masks else None
    if d.get("heat_press_relief", True):
        _composite_with_relief(atlas, img_rot, rx, ry, relief_depth=1, shadow_opacity=55, highlight_opacity=30, mask=sleeve_mask)
    elif sleeve_mask is not None:
        _composite_layer(atlas, stamp_layer, sleeve_mask)
    else:
        atlas.alpha_composite(stamp_layer)


# --------------------------------------------------------------------------- #
#  generator -> design
# --------------------------------------------------------------------------- #
# Home / away / third ("p1/p2/p3") and goalkeeper ("g1/g2") each get an independent roll.
_SLOT_SALT = {
    1: "kitgen-v1",
    2: "kitgen-v1-away",
    3: "kitgen-v1-third",
    "g1": "kitgen-v1-gk1",
    "g2": "kitgen-v1-gk2",
    4: "kitgen-v1-gk1",
    5: "kitgen-v1-gk2",
}

# Which of the club's three colours leads each kit: (body, pattern, accent).
_SLOT_ROLES = {
    1: ("primary", "secondary", "accent"),      # home   - club colour dominant
    2: ("secondary", "primary", "accent"),      # away   - the second colour leads
    3: ("accent", "primary", "secondary"),      # third  - the accent colour leads
    "g1": ("primary", "secondary", "accent"),   # gk1    - vibrant high-vis
    "g2": ("secondary", "primary", "accent"),   # gk2    - vibrant secondary high-vis
    4: ("primary", "secondary", "accent"),      # gk1 alias
    5: ("secondary", "primary", "accent"),      # gk2 alias
}

# Explicit per-club styling, keyed by team id then slot.  It pins the palette
# per kit and gives a POOL of on-brand, non-basic patterns to choose from: with
# no sponsor the first pattern (the approved look) is used, and a signed sponsor
# picks a DIFFERENT one, so every deal gives a fresh but still recognisable kit.
# Pool entries are either a legacy named pattern or a kit_patterns catalog code
# ("127", "127-B", ...) - see generator/kit_patterns.py.
#
# Explicit per-club styling and dynamic fashion DNA from kit_dna.
# Preserves iconic heritage (Arsenal white sleeves, Ajax red center, Milan/Inter/Juve stripes,
# Celtic hoops, Boca chestband, River sash) while providing modern 2026 luxury micro-jacquards,
# Carrara marble, houndstooth, and kinetic geometry for all clubs.
KIT_STYLE = kit_dna.BESPOKE_DNA


def design_from_club(club, season, logo_dir, slot=1, brand_files=None, style=None,
                     sponsor=None, badge_dir=None, badge=None, sleeve_sponsor=None):
    """Turn a club row + season + kit slot (1=home, 2=away, 3=third) into a design.

    The rolls are taken in the same order as kit_gen.preview() so the wrapped
    kit matches the preview sheet exactly: pick_design, jitter_body, brand.
    Shorts/socks/collar colours are derived from the already-rolled fields (no
    extra RNG draws), so the Lua side stays bit-compatible.

    `sponsor` is the signed sponsor's brand name.  When given it (a) forces the
    chest logo to that brand and (b) shifts the design seed, so a new deal gives
    a fresh design from the club's on-brand pattern pool.

    `style` (or KIT_STYLE[club_id][slot]) may override any of body/second/third/
    patterns/sleeve/cuff/shorts/socks/collar/gradient/var/width_step.
    """
    if slot in (4, "4"):
        slot = "g1"
    elif slot in (5, "5"):
        slot = "g2"
    elif slot in ("p1", "1"):
        slot = 1
    elif slot in ("p2", "2"):
        slot = 2
    elif slot in ("p3", "3"):
        slot = 3

    if slot not in _SLOT_ROLES:
        raise ValueError(f"slot must be 1, 2, 3, 'g1', or 'g2' (got {slot})")

    salt = _SLOT_SALT[slot] + (("|" + sponsor) if sponsor else "")
    rng = kit_gen.season_rng(club["id"], season, salt=salt)
    roll = kit_gen.pick_design(rng)

    palette = {"primary": _hexc(club["primary"]),
               "secondary": _hexc(club["secondary"]),
               "accent": _hexc(club["accent"])}
    lead, pattern_role, accent_role = _SLOT_ROLES[slot]
    anchor = palette[lead]
    second = palette[pattern_role]
    accent = palette[accent_role]
    body = kit_gen.jitter_body(rng, anchor)

    logo_dir = Path(logo_dir)
    # A signed sponsor is the ONLY thing that puts a logo on the chest.  With no
    # deal there is no chest logo, so the pre-signing kit is a clean design and
    # every signed deal is an unmistakable change.
    brand = sponsor if sponsor else None

    pattern = kit_gen.PATTERNS[roll["layout"] % 8]
    var = roll["layout"] // 8
    overlay = roll["overlay"]
    trim = roll["trim"]

    sleeve = [body, second, accent, anchor][overlay % 4]
    shorts = [body, second][(overlay // 4) % 2]
    socks = [second, body][(overlay // 3) % 2]
    collar = [second, accent, (20, 20, 24), (245, 245, 245), body, accent][trim % 6]

    design = {
        "body": body, "second": second, "accent": accent, "third": None,
        "pattern": pattern, "var": var,
        "width_step": roll["stripe_width"], "gradient": roll["gradient"],
        "sleeve": sleeve, "cuff": None, "shorts": shorts, "socks": socks, "collar": collar,
        "sponsor": None, "sponsor_white": False,
        "slot": slot, "_brand": brand, "_roll": roll, "_sponsor": sponsor,
    }

    # High-fashion 2026 DNA styling: bespoke heritage or dynamic modern classification
    if style is not None:
        st = dict(style)
        pool = st.pop("patterns", None)
        if pool:
            if not sponsor:
                st["pattern"] = pool[0]
            else:
                choices = [x for x in pool if x != pool[0]] or pool
                cid = int(club.get("id") or club.get("team_id", 0))
                slot_num = slot if isinstance(slot, int) else (4 if "g" in str(slot) else int(str(slot).replace("p", "") or 1))
                entropy = ((cid * 0x45D9F3B) ^ (season * 0x119DE1F) ^ kit_dna._sponsor_hash(sponsor) ^ (slot_num * 0x27D4EB2D)) & 0x7FFFFFFF
                idx = entropy % len(choices)
                st["pattern"] = choices[idx]
    else:
        st = kit_dna.get_club_style(club, slot, season, sponsor=sponsor)

    if st:
        design.update(st)

    if sleeve_sponsor:
        design["sleeve_sponsor"] = sleeve_sponsor

    # the chest logo is stamped only for a signed sponsor, and chosen from the
    # FINAL body colour so a dark kit gets the white logo variant
    if brand:
        body_col = tuple(design["body"])
        body_lum = kit_gen.lum(body_col)
        # If shirt body is dark (< 130), white logo is mandatory to guarantee legibility
        if body_lum < 130:
            white = True
            design["sponsor_white"] = True
            design.pop("sponsor_dark", None)
        else:
            white = False
            design["sponsor_white"] = False
            # If sponsor_dark was explicitly set, check that it still has strict WCAG AA contrast (>= 4.5:1)
            if design.get("sponsor_dark"):
                dark_col = design["sponsor_dark"] if isinstance(design["sponsor_dark"], (tuple, list)) else (12, 14, 18)
                ratio = _wcag_contrast(body_col, dark_col)
                if ratio < 4.5:
                    white_ratio = _wcag_contrast(body_col, (255, 255, 255))
                    noir_ratio = _wcag_contrast(body_col, (12, 14, 18))
                    if white_ratio >= noir_ratio:
                        design.pop("sponsor_dark", None)
                        design["sponsor_white"] = True
                        white = True
                    else:
                        design["sponsor_dark"] = (12, 14, 18)

        cand_logo = Path(logo_dir) / (brand + ("_white" if white else "") + ".png")
        if not cand_logo.is_file():
            cand_logo = Path(logo_dir) / (brand + ".png")
        design["sponsor"] = str(cand_logo)

        if not white and not design.get("sponsor_dark"):
            # Check if regular logo has sufficient WCAG AA contrast (>= 4.5:1)
            try:
                sim = Image.open(design["sponsor"]).convert("RGBA")
                arr = np.array(sim)
                opaque = arr[:, :, 3] > 128
                if np.any(opaque):
                    s_col = tuple(int(v) for v in np.median(arr[opaque, :3], axis=0))
                    ratio = _wcag_contrast(body_col, s_col)
                    if ratio < 4.5:
                        white_ratio = _wcag_contrast(body_col, (255, 255, 255))
                        noir_ratio = _wcag_contrast(body_col, (12, 14, 18))
                        if white_ratio >= noir_ratio:
                            design["sponsor_white"] = True
                            white = True
                            cand_w = Path(logo_dir) / (brand + "_white.png")
                            if cand_w.is_file():
                                design["sponsor"] = str(cand_w)
                        else:
                            design["sponsor_dark"] = (12, 14, 18)
            except Exception:
                pass
    else:
        design["sponsor"] = None

    # club badge on the player's left chest
    if badge:
        design["badge"] = str(badge)
    else:
        bdir = Path(badge_dir) if badge_dir else (Path(logo_dir).parent / "badges")
        cid = club.get("id") or club.get("team_id")
        candidate = bdir / f"{cid}.png"
        if candidate.is_file():
            design["badge"] = str(candidate)
        else:
            name_slug = re.sub(r"[^a-z0-9_]+", "_", str(club.get("name", "")).lower()).strip("_")
            candidate_slug = bdir / f"{name_slug}.png"
            if candidate_slug.is_file():
                design["badge"] = str(candidate_slug)
            else:
                design["badge"] = None

    # Kit supplier on the player's right chest (e.g. adidas, nike, puma)
    sup = design.get("supplier")
    if sup:
        design["supplier_name"] = str(sup).lower()
        sdir = Path(badge_dir).parent / "suppliers" if badge_dir else (Path(logo_dir).parent / "suppliers")
        is_dark_shirt = kit_gen.lum(design["body"]) < 120
        cand_white = sdir / f"{sup}_white.png"
        cand_dark = sdir / f"{sup}_dark.png"
        cand_std = sdir / f"{sup}.png"
        if is_dark_shirt and cand_white.is_file():
            design["supplier"] = str(cand_white)
        elif not is_dark_shirt and cand_dark.is_file():
            design["supplier"] = str(cand_dark)
        elif cand_std.is_file():
            design["supplier"] = str(cand_std)
        else:
            design["supplier"] = None

        # Auto-tint supplier logo for light/white kits with distinct accent trims (e.g. Real Madrid gold)
        if not design.get("supplier_color") and not is_dark_shirt:
            str_acc = design.get("stripe_accent") or design.get("second")
            if str_acc and kit_gen.lum(design["body"]) > 180:
                d_dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(design["body"][:3], str_acc[:3])))
                if d_dist > 50:
                    design["supplier_color"] = str_acc

    # Secondary sleeve sponsor on player's left sleeve (e.g. visit_rwanda, hp, dxc, okx)
    sleeve_sp = design.get("sleeve_sponsor")
    if sleeve_sp:
        sdir = Path(logo_dir).parent / "sleeve_logos" if logo_dir else (Path(__file__).resolve().parent / "sleeve_logos")
        cand_sp = sdir / f"{sleeve_sp}.png"
        cand_sp_w = sdir / f"{sleeve_sp}_white.png"
        if cand_sp.is_file():
            design["sleeve_sponsor"] = str(cand_sp)
        elif cand_sp_w.is_file():
            design["sleeve_sponsor"] = str(cand_sp_w)
        elif (Path(__file__).resolve().parent / "sleeve_logos" / f"{sleeve_sp}.png").is_file():
            design["sleeve_sponsor"] = str(Path(__file__).resolve().parent / "sleeve_logos" / f"{sleeve_sp}.png")
    return design


def render_club(club, season, out_png, logo_dir, masks=None, brand_files=None, slot=1,
                style=None, sponsor=None, badge_dir=None, badge=None, sleeve_sponsor=None):
    """Render one club's generated kit for a season; returns (path_or_image, design)."""
    design = design_from_club(club, season, logo_dir, slot=slot,
                              brand_files=brand_files, style=style, sponsor=sponsor,
                              badge_dir=badge_dir, badge=badge, sleeve_sponsor=sleeve_sponsor)
    res = render_kit(design, str(out_png) if out_png else None, masks=masks)
    return res, design


def render_kit_set(club, season, outdir, logo_dir, masks=None, brand_files=None,
                   sponsor=None, badge_dir=None, badge=None, slots=(1, 2, 3, "g1", "g2"),
                   sleeve_sponsor=None):
    """Render the full outfield and goalkeeper kit set for a club + season.

    Returns a list of (slot, atlas_png, preview_png, design).
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    masks = masks if masks is not None else kit_regions.build_masks()
    if brand_files is None:
        logo_dir = Path(logo_dir)
        brand_files = sorted(p.stem for p in logo_dir.glob("*.png")
                             if not p.stem.endswith("_white")
                             and not p.stem.startswith("_"))

    team = club["id"]
    out = []
    for slot in slots:
        slot_code = f"p{slot}" if isinstance(slot, int) else str(slot)
        atlas = outdir / f"u{team:04d}{slot_code}_atlas.png"
        _, design = render_club(club, season, atlas, logo_dir, masks=masks,
                                brand_files=brand_files, slot=slot, sponsor=sponsor,
                                badge_dir=badge_dir, badge=badge, sleeve_sponsor=sleeve_sponsor)
        preview = uv_contact_sheet(atlas, outdir / f"u{team:04d}{slot_code}_preview.png",
                                   masks=masks)
        mockup(design, club["name"], season,
               outdir / f"u{team:04d}{slot_code}_mockup.png")
        out.append((slot, str(atlas), str(preview), design))
    return out


def mockup(design, club_name, season, out_png):
    """A flat 'on the shirt' mockup of a design (front), for eyeballing."""
    W, H = kit_gen.W, kit_gen.H
    bmask, smask = kit_gen.shirt_masks()
    body = tuple(design["body"])
    second = tuple(design["second"])
    canvas = Image.new("RGBA", (W, H + 44), (28, 30, 36, 255))

    pat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    kit_gen.draw_pattern(pat, design["pattern"], body, second,
                         design.get("var", 0), design.get("width_step", 0),
                         third=design.get("third"))
    pat = kit_gen.apply_gradient(
        pat, [0.0, 0.15, 0.28, 0.40][design.get("gradient", 0) % 4])
    canvas.paste(pat, (0, 0), bmask)

    sleeve = tuple(design.get("sleeve") or body)
    canvas.paste(Image.new("RGBA", (W, H), sleeve + (255,)), (0, 0), smask)

    cuff = design.get("cuff")
    if cuff:
        import numpy as np
        sm = np.asarray(smask) > 10
        cm = np.zeros_like(sm)
        # Reduced slim cuff height: 10px (273..283)
        cm[273:283, :] = sm[273:283, :]
        if np.any(cm):
            cuff_col = tuple(cuff) + (255,)
            cimg = Image.fromarray((cm * 255).astype("uint8"), "L")
            canvas.paste(Image.new("RGBA", (W, H), cuff_col), (0, 0), cimg)
        cuff_tip = design.get("cuff_tip")
        if cuff_tip and cuff_tip != cuff:
            tip_mask = np.zeros_like(sm)
            tip_mask[280:283, :] = sm[280:283, :]
            if np.any(tip_mask):
                timg = Image.fromarray((tip_mask * 255).astype("uint8"), "L")
                canvas.paste(Image.new("RGBA", (W, H), tuple(cuff_tip) + (255,)), (0, 0), timg)

    d = ImageDraw.Draw(canvas)

    # Brand signature languages on 2D mockup
    supp_m = str(design.get("supplier_name") or design.get("supplier") or "").lower()
    acc_cand = design.get("stripe_accent") or design.get("second") or design["body"]
    dist_c = math.sqrt(sum((a - b) ** 2 for a, b in zip(body[:3], acc_cand[:3])))
    if dist_c < 40:
        l_b = 0.2126 * body[0] + 0.7152 * body[1] + 0.0722 * body[2]
        acc_cand = (245, 245, 245) if l_b < 128 else (20, 25, 35)
    str_col = tuple(acc_cand) + (255,)

    if "adidas" in supp_m or design.get("sleeve_style") in ("shoulder_stripe", "adidas_stripes", "three_stripes"):
        for offset in (-4, 0, 4):
            d.line([(200 + offset, 46 - abs(offset) // 2), (120 + offset, 88 - abs(offset) // 2)], fill=str_col, width=2)
            d.line([(280 - offset, 46 - abs(offset) // 2), (360 - offset, 88 - abs(offset) // 2)], fill=str_col, width=2)
    elif "hummel" in supp_m:
        for cx, cy in [(180, 56), (155, 70), (130, 84)]:
            d.polygon([(cx - 4, cy - 4), (cx + 2, cy), (cx - 4, cy + 4)], fill=str_col)
        for cx, cy in [(300, 56), (325, 70), (350, 84)]:
            d.polygon([(cx + 4, cy - 4), (cx - 2, cy), (cx + 4, cy + 4)], fill=str_col)
    elif "kappa" in supp_m:
        d.line([(200, 48), (120, 90)], fill=str_col, width=4)
        d.line([(280, 48), (360, 90)], fill=str_col, width=4)
    elif "umbro" in supp_m:
        for cx, cy in [(175, 58), (145, 74)]:
            d.polygon([(cx, cy - 4), (cx + 4, cy), (cx, cy + 4), (cx - 4, cy)], fill=str_col)
        for cx, cy in [(305, 58), (335, 74)]:
            d.polygon([(cx, cy - 4), (cx + 4, cy), (cx, cy + 4), (cx - 4, cy)], fill=str_col)
    elif "puma" in supp_m:
        d.line([(200, 46), (120, 88)], fill=str_col, width=6)
        d.line([(280, 46), (360, 88)], fill=str_col, width=6)
    elif "nike" in supp_m:
        d.line([(108, 140), (108, 430)], fill=str_col, width=3)
        d.line([(372, 140), (372, 430)], fill=str_col, width=3)

    # Vent panels on 2D mockup flanks
    v_style = design.get("vent_style", "none")
    if v_style and v_style != "none":
        v_col = design.get("vent_color") or (max(10, int(body[0] * 0.78)), max(10, int(body[1] * 0.78)), max(10, int(body[2] * 0.78)))
        v_rgba = tuple(v_col) + (255,)
        d.rectangle([108, 150, 118, 440], fill=v_rgba)
        d.rectangle([362, 150, 372, 440], fill=v_rgba)
    trim = tuple(design.get("collar") or body)
    c_style = design.get("collar_style", "crew")
    collar_tip = design.get("collar_tip")
    tip_col = tuple(collar_tip) + (255,) if (collar_tip and collar_tip != trim) else (tuple(trim) + (255,))

    if c_style == "polo":
        # Folded wings contour
        d.polygon([(194, 40), (216, 68), (236, 52), (244, 52), (264, 68), (286, 40), (272, 38), (240, 44), (208, 38)],
                  fill=trim + (255,), outline=tip_col)
        # Button placket down chest
        d.rectangle([236, 50, 244, 94], fill=trim + (255,), outline=tip_col, width=1)
        btn_c = (245, 245, 248, 255) if _col_lum(trim) < 160 else (25, 25, 30, 255)
        d.ellipse([238, 62, 242, 66], fill=btn_c)
        d.ellipse([238, 80, 242, 84], fill=btn_c)
    elif c_style == "v_neck":
        d.polygon([(200, 40), (240, 86), (280, 40), (268, 40), (240, 70), (212, 40)],
                  fill=trim + (255,))
        if collar_tip and collar_tip != trim:
            d.line([(200, 40), (240, 86), (280, 40)], fill=tuple(collar_tip) + (255,), width=2)
    elif c_style == "dual_tipped":
        d.arc([198, 26, 282, 78], 15, 165, fill=trim + (255,), width=8)
        d.arc([198, 26, 282, 78], 15, 165, fill=tip_col, width=2)
        tip2_c = tuple(design.get("third") or design.get("second") or trim) + (255,)
        d.arc([204, 32, 276, 72], 15, 165, fill=tip2_c, width=2)
    else:  # crew
        d.arc([198, 26, 282, 78], 15, 165, fill=trim + (255,), width=8)
        if collar_tip and collar_tip != trim:
            d.arc([198, 26, 282, 78], 15, 165, fill=tuple(collar_tip) + (255,), width=2)

    if design.get("badge"):
        try:
            b_logo = Image.open(design["badge"]).convert("RGBA")
            if design.get("badge_white"):
                b_logo = _flatten_white(b_logo)
            bs = min(44 / max(1, b_logo.width), 44 / max(1, b_logo.height))
            b_logo = b_logo.resize((max(1, int(b_logo.width * bs)), max(1, int(b_logo.height * bs))), Image.LANCZOS)
            canvas.alpha_composite(b_logo, (300 - b_logo.width // 2, 110 - b_logo.height // 2))
        except Exception:
            pass

    if design.get("supplier"):
        try:
            s_logo = Image.open(design["supplier"]).convert("RGBA")
            if design.get("supplier_color"):
                s_logo = _flatten_color(s_logo, design["supplier_color"])
            elif design.get("supplier_white"):
                s_logo = _flatten_white(s_logo)
            ss = min(38 / max(1, s_logo.width), 26 / max(1, s_logo.height))
            s_logo = s_logo.resize((max(1, int(s_logo.width * ss)), max(1, int(s_logo.height * ss))), Image.LANCZOS)
            canvas.alpha_composite(s_logo, (180 - s_logo.width // 2, 110 - s_logo.height // 2))
        except Exception:
            pass

    if design.get("sponsor"):
        logo = Image.open(design["sponsor"]).convert("RGBA")
        if design.get("sponsor_white"):
            logo = _flatten_white(logo)
        elif design.get("sponsor_dark"):
            col = design["sponsor_dark"] if isinstance(design["sponsor_dark"], (tuple, list)) else (15, 25, 45)
            logo = _flatten_color(logo, col)
        s = min(190 / logo.width, 60 / logo.height)
        logo = logo.resize((max(1, int(logo.width * s)), max(1, int(logo.height * s))))
        if design.get("sponsor_plate", False):
            d.rounded_rectangle([118, 160, 362, 236], radius=10, fill=body + (255,))
        canvas.alpha_composite(logo, (240 - logo.width // 2, 170))

    if design.get("sleeve_sponsor"):
        try:
            sl_path = Path(design["sleeve_sponsor"])
            if not sl_path.is_file():
                cand = Path(__file__).resolve().parent / "sleeve_logos" / f"{sl_path.stem}.png"
                if cand.is_file():
                    sl_path = cand
            if sl_path.is_file():
                sl_logo = Image.open(sl_path).convert("RGBA")
                canvas_arr = np.array(canvas)
                sl_lum = _col_lum(canvas_arr[175, 395, :3])
                if sl_lum < 130 or design.get("sleeve_sponsor_white"):
                    cand_w = sl_path.parent / f"{sl_path.stem.replace('_white', '')}_white.png"
                    if cand_w.is_file():
                        sl_logo = Image.open(cand_w).convert("RGBA")
                    else:
                        sl_logo = _flatten_white(sl_logo)
                sl_scale = min(36 / max(1, sl_logo.width), 20 / max(1, sl_logo.height))
                sl_logo = sl_logo.resize((max(1, int(sl_logo.width * sl_scale)), max(1, int(sl_logo.height * sl_scale))), Image.LANCZOS)
                canvas.alpha_composite(sl_logo, (395 - sl_logo.width // 2, 175 - sl_logo.height // 2))
        except Exception:
            pass

    # shorts / socks swatches along the bottom strip
    def swatch(x, colour, label, accent=None):
        d.rectangle([x, H + 6, x + 44, H + 38], fill=tuple(colour) + (255,))
        if accent and accent != colour:
            d.rectangle([x + 34, H + 6, x + 44, H + 38], fill=tuple(accent) + (255,))
        d.text((x + 50, H + 14), label, fill=(210, 212, 218, 255))

    swatch(10, design.get("shorts") or body, "shorts", design.get("shorts_accent"))
    swatch(150, design.get("socks") or body, "socks", design.get("socks_accent"))
    swatch(290, design.get("collar") or body, "collar", design.get("collar_tip"))
    slot_val = design.get('slot', 1)
    slot_label = f"p{slot_val}" if isinstance(slot_val, int) else str(slot_val)
    d.text((10, 10), f"{club_name} S{season} {slot_label} {design['pattern']}",
           fill=(240, 240, 245, 255))

    canvas.convert("RGB").save(out_png)
    return out_png


def uv_contact_sheet(atlas_png, out_png, masks=None, cell=460):
    """Save a labelled contact sheet of the UV islands, for eyeballing."""
    masks = masks if masks is not None else kit_regions.build_masks()
    boxes = kit_regions.region_boxes(masks)
    atlas = Image.open(atlas_png).convert("RGB")

    order = ["body_front", "body_back", "sleeve", "shorts", "socks", "collar"]
    cols = 3
    rows = (len(order) + cols - 1) // cols
    pad, label_h = 16, 34
    sheet = Image.new("RGB", (cols * (cell + pad) + pad,
                              rows * (cell + label_h + pad) + pad), (28, 30, 36))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arialbd.ttf", 22)
    except Exception:  # pragma: no cover
        font = ImageFont.load_default()

    for i, name in enumerate(order):
        x0, y0, x1, y1 = boxes[name]
        crop = atlas.crop((x0, y0, x1 + 1, y1 + 1))
        crop.thumbnail((cell, cell), Image.LANCZOS)
        cx = pad + (i % cols) * (cell + pad)
        cy = pad + (i // cols) * (cell + label_h + pad)
        draw.text((cx, cy), name, fill=(230, 230, 235), font=font)
        sheet.paste(crop, (cx + (cell - crop.width) // 2, cy + label_h))

    sheet.save(out_png)
    return out_png



# --------------------------------------------------------------------------- #
#  demo / CLI
# --------------------------------------------------------------------------- #
def _chelsea_demo():
    """The three seasons the mod would generate for Chelsea, as a demo set."""
    root = Path(__file__).resolve().parent.parent
    clubs = kit_gen.load_clubs(root / "generator" / "clubs.csv")
    chelsea = next(c for c in clubs if c["id"] == 102)
    return chelsea


def _describe(design, season, club):
    return (f"  {club['name']} S{season} p{design['slot']}: pattern={design['pattern']} "
            f"var={design['var']} body={design['body']} sleeve={design['sleeve']} "
            f"shorts={design['shorts']} socks={design['socks']} collar={design['collar']} "
            f"sponsor={design['_brand']}")


if __name__ == "__main__":
    import sys

    root = Path(__file__).resolve().parent.parent
    logo_dir = root / "content" / "KitGenerator" / "logos"
    badge_dir = root / "content" / "KitGenerator" / "badges"
    if not logo_dir.exists():
        logo_dir = Path(r"c:\Games\SP Football Life 2027\SiderAddons\content\KitGenerator\logos")
        badge_dir = Path(r"c:\Games\SP Football Life 2027\SiderAddons\content\KitGenerator\badges")
    masks = kit_regions.build_masks()

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args and args[0] == "demo":
        outdir = Path(args[1]) if len(args) > 1 else Path(".")
        club = _chelsea_demo()
        for season in (2027, 2028, 2029):
            out = outdir / f"chelsea_{season}_atlas.png"
            _, design = render_club(club, season, out, logo_dir, masks=masks)
            uv_contact_sheet(out, outdir / f"chelsea_{season}_preview.png", masks=masks)
            print(f"wrote {out}  pattern={design['pattern']} body={design['body']} "
                  f"sponsor={design['_brand']}")
        sys.exit(0)

    if len(args) < 3:
        print("usage:")
        print("  python kit_render.py <club_id> <season> <outdir>            # full p1/p2/p3 set")
        print("  python kit_render.py <club_id> <season> <outdir> --slot N   # just one slot")
        print("  python kit_render.py demo <outdir>")
        sys.exit(1)

    club_id, season, outdir = int(args[0]), int(args[1]), Path(args[2])
    outdir.mkdir(parents=True, exist_ok=True)

    clubs = kit_gen.load_clubs(root / "generator" / "clubs.csv")
    club = next(c for c in clubs if c["id"] == club_id)

    if "--slot" in sys.argv:
        slot = int(sys.argv[sys.argv.index("--slot") + 1])
        name = "u%04dp%d" % (club_id, slot)
        out = outdir / f"{name}_atlas.png"
        _, design = render_club(club, season, out, logo_dir, masks=masks, slot=slot, badge_dir=badge_dir)
        sheet = uv_contact_sheet(out, outdir / f"{name}_preview.png", masks=masks)
        print(f"wrote {out}")
        print(f"wrote {sheet}")
        print(_describe(design, season, club))
        sys.exit(0)

    for slot, atlas, preview, design in render_kit_set(club, season, outdir,
                                                       logo_dir, masks=masks, badge_dir=badge_dir):
        print(f"wrote {atlas}")
        print(f"wrote {preview}")
        print(_describe(design, season, club))
