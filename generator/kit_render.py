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
from collections import OrderedDict
import math
import re
import numpy as np

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter

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
    "sleeve_style": "solid",      # "solid", "raglan", "shoulder_stripe", "tipped", "grunge_yoke", "brand_track_tape", "seam_piping"
    "cuff": None,                 # None = same as sleeve
    "cuff_style": "solid",        # "solid", "wide_band", "micro_tipped", "dual_stripe", "jacquard_knit"
    "cuff_tip": None,             # contrast tipping on sleeve cuff
    "shorts": None,               # None = same as body
    "shorts_style": "solid",      # "solid", "side_stripe", "hem_tape", "split_leg"
    "shorts_accent": None,        # contrast stripe/tape colour on shorts
    "socks": None,                # None = same as body
    "socks_style": "solid",       # "solid", "turnover_hoop", "calf_band", "gradient_fade"
    "socks_accent": None,         # contrast hoop/band colour on socks
    "socks_tip": None,            # contrast tipping on socks turnover
    "collar": None,               # None = same as body
    "collar_style": "crew",       # "crew", "retro_crew", "v_neck", "crossover_v", "polo", "polo_v_notch", "striped_rib_polo", "dual_tipped", "mandarin_button", "wrap_v_neck", "grandad_collar", "square_neck", "contrast_split_collar", "laced_placket", "mock_turtleneck_micro"
    "collar_model": 1,            # 3D Kitserver collar model: 1=crew, 2=dual_tipped, 3=v_neck, 4=crossover_v, 13=polo, 14=laced, 38=mock, 46=striped_polo, 64=grandad/mandarin, 78=wrap_v, 105=polo_v_notch, 118=square_neck
    "collar_tip": None,           # contrast tipping on collar ribbing
    "cuff": None,                 # contrast sleeve cuff color (None = auto)
    "cuff_style": "solid",        # "solid", "wide_band", "micro_tipped", "dual_stripe", "dual_tipped", "jacquard_knit", "striped_rib", "accent_ring_inner", "tri_color_knit", "contrast_split", "french_turnback"
    "cuff_tip": None,             # contrast stripe on cuff (None = accent/secondary)
    "sleeve_style": "solid",      # "solid", "tipped", "shoulder_stripe", "brand_track_tape", "seam_piping", "raglan_piping", "grunge_yoke", "splatter_brush", "contrast_raglan"
    "sponsor": None,              # path to a PNG logo (chest)
    "badge": None,                # path to a PNG logo (club badge)
    "supplier": None,             # path to a PNG logo (kit maker)
    "sponsor_white": False,       # True = flatten the logo to white
    "badge_white": False,
    "supplier_white": False,
    "sponsor_plate": False,       # draw a body-coloured plate behind the sponsor (False = seamless logo with no background)
    "vent_style": "none",         # "none", "laser_cut", "contrast_panel", "stealth_rib", "athletic_flank"
    "vent_color": None,           # None = auto breathable tone
    "macro_layout": "solid",      # "solid", "ombre_fade", "half_half", "chestband", "diagonal_sash", "lightning_sash", "fade_geo"
    "micro_jacquard": None,       # secondary subtle luxury jacquard overlay (e.g. "041-E", "171-E")
    "pattern_mask": "full",       # "full", "front_only", "chest_only", "sash_only", "sleeves_only"
    "tile_scale": 1.0,            # 0.5 (micro-weave 2x2), 1.0 (standard), 2.0 (macro streetwear art)
    "finish": "standard",         # "standard", "liquid_gold", "chrome_silver", "copper_bronze", "blackout", "whiteout", "cyber_neon"
    "jocktag": True,              # True = render authentic engineered jocktag at lower shirt hem
    "shorts_badge": True,         # True = render club crest on right shorts leg
    "shorts_supplier": True,      # True = render supplier logo on left shorts leg
    "sleeve_sponsor": None,       # path to a PNG logo or key (player's left sleeve)
    "sleeve_sponsor_side": "left",# "left" (authentic default), "right", or "both"
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


# The worker reuses the same six UV masks for every club.  Keep their PIL
# equivalents (and short-lived cropped masks) alive briefly so we do not
# rebuild a 2048x2048 uint8 array on every paste.
_MASK_IMG_CACHE = OrderedDict()


def _mask_img(mask):
    """numpy bool mask -> single-channel PIL mask (255 where True)."""
    if isinstance(mask, Image.Image):
        return mask                       # already cropped/derived from a cached mask
    key = id(mask)
    hit = _MASK_IMG_CACHE.get(key)
    if hit is not None and hit[0] is mask:
        _MASK_IMG_CACHE.move_to_end(key)
        return hit[1]
    img = Image.fromarray((mask * 255).astype("uint8"))
    _MASK_IMG_CACHE[key] = (mask, img)
    if len(_MASK_IMG_CACHE) > 96:
        _MASK_IMG_CACHE.popitem(last=False)
    return img


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


def _resolve_badge_color(badge_path, base_color, design):
    """Determine if a badge is a monochrome silhouette or has low contrast against base_color.
    Returns (badge_color, is_white) where badge_color is an RGB tuple or None."""
    if not badge_path or not Path(badge_path).is_file():
        return None, False

    explicit_col = design.get("badge_color")
    if explicit_col:
        # If explicit badge color has sufficient contrast with base_color (e.g. white on shirt), use it
        if _wcag_contrast(base_color, tuple(explicit_col)) >= 3.0:
            return tuple(explicit_col), False
        # Otherwise (e.g. white badge on white shorts), adapt below

    if design.get("badge_white"):
        if _wcag_contrast(base_color, (250, 250, 252)) >= 3.0:
            return None, True

    try:
        im = Image.open(badge_path).convert("RGBA")
        arr = np.asarray(im)
        vis = arr[arr[:, :, 3] > 80][:, :3]
        if len(vis) == 0:
            return None, False

        unique_q = len(np.unique(vis // 24, axis=0))
        std = float(np.std(vis, axis=0).mean())

        # Adapt monochrome or low-diversity silhouette badges (e.g. Liverpool Liverbird, Forest Tree)
        if unique_q <= 4 or std < 15.0 or explicit_col:
            b_mean = tuple(int(x) for x in vis.mean(axis=0)) if not explicit_col else tuple(explicit_col)
            ratio = _wcag_contrast(base_color, b_mean)
            if ratio < 3.5:
                # Need contrast resolution!
                body_c = tuple(design.get("body", (20, 20, 24)))
                second_c = tuple(design.get("second", (250, 250, 252)))
                third_c = tuple(design.get("third")) if design.get("third") else None
                # If primary shirt color has good contrast (e.g. red badge on white shorts), prioritize it!
                if _wcag_contrast(base_color, body_c) >= 3.5:
                    return body_c, False
                cands = [second_c]
                if third_c:
                    cands.append(third_c)
                cands.extend([(250, 250, 252), (20, 20, 24)])
                best_c = max(cands, key=lambda c: _wcag_contrast(base_color, c))
                return best_c, False
    except Exception:
        pass

    return None, False


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
    elif macro == "diagonal_sash":
        sash_img = Image.new("RGBA", (kit_gen.W, kit_gen.H), (0, 0, 0, 0))
        draw_s = ImageDraw.Draw(sash_img)
        sw = int(kit_gen.W * 0.22)
        p1 = (int(kit_gen.W * 0.72), 0)
        p2 = (int(kit_gen.W * 0.72) + sw, 0)
        p3 = (int(kit_gen.W * 0.08) + sw, kit_gen.H)
        p4 = (int(kit_gen.W * 0.08), kit_gen.H)
        poly = [p1, p2, p3, p4]
        draw_s.polygon(poly, fill=second + (255,))
        tip_c = d.get("third") or d.get("accent") or body
        draw_s.line([p1, p4], fill=tuple(tip_c) + (255,), width=3)
        draw_s.line([p2, p3], fill=tuple(tip_c) + (255,), width=3)
        canvas.alpha_composite(sash_img)
    elif macro == "lightning_sash":
        # Bold authentic lightning bolt diagonal sash (Rayo Vallecano style)
        bolt_img = Image.new("RGBA", (kit_gen.W, kit_gen.H), (0, 0, 0, 0))
        draw_bolt = ImageDraw.Draw(bolt_img)
        W, H = kit_gen.W, kit_gen.H
        poly = [
            (int(W * 0.72), 0),
            (int(W * 0.94), 0),
            (int(W * 0.42), int(H * 0.48)),
            (int(W * 0.64), int(H * 0.46)),
            (int(W * 0.20), H),
            (0, H),
            (0, int(H * 0.88)),
            (int(W * 0.32), int(H * 0.54)),
            (int(W * 0.12), int(H * 0.56)),
        ]
        s_fill = second if second != body else (d.get("third") or (220, 30, 40))
        draw_bolt.polygon(poly, fill=tuple(s_fill) + (255,))
        tip_c = d.get("third") or d.get("accent") or (235, 195, 30)
        draw_bolt.line(poly + [poly[0]], fill=tuple(tip_c) + (255,), width=4)
        canvas.alpha_composite(bolt_img)
    elif macro == "prismatic_shards":
        # 90s Jorge Campos / Schmeichel iconic angular faceted geometric shards
        shard_img = Image.new("RGBA", (kit_gen.W, kit_gen.H), (0, 0, 0, 0))
        draw_sh = ImageDraw.Draw(shard_img)
        W, H = kit_gen.W, kit_gen.H
        s_fill1 = tuple(second) + (240,)
        s_fill2 = tuple(d.get("third") or d.get("accent") or (255, 230, 40)) + (240,)
        s_fill3 = tuple(d.get("accent") or (255, 30, 100)) + (230,)
        draw_sh.polygon([(0, 0), (int(W * 0.35), 0), (int(W * 0.20), int(H * 0.40)), (0, int(H * 0.25))], fill=s_fill1)
        draw_sh.polygon([(int(W * 0.35), 0), (int(W * 0.65), 0), (int(W * 0.50), int(H * 0.45)), (int(W * 0.20), int(H * 0.40))], fill=s_fill2)
        draw_sh.polygon([(int(W * 0.65), 0), (W, 0), (W, int(H * 0.25)), (int(W * 0.80), int(H * 0.40))], fill=s_fill3)
        draw_sh.polygon([(int(W * 0.50), int(H * 0.45)), (W, int(H * 0.25)), (int(W * 0.80), int(H * 0.40)), (int(W * 0.65), int(H * 0.65))], fill=s_fill1)
        draw_sh.polygon([(0, int(H * 0.25)), (int(W * 0.20), int(H * 0.40)), (int(W * 0.35), int(H * 0.65)), (0, int(H * 0.55))], fill=s_fill2)
        draw_sh.polygon([(int(W * 0.20), int(H * 0.40)), (int(W * 0.50), int(H * 0.45)), (int(W * 0.50), int(H * 0.75)), (int(W * 0.35), int(H * 0.65))], fill=s_fill3)
        draw_sh.polygon([(int(W * 0.50), int(H * 0.45)), (int(W * 0.80), int(H * 0.40)), (int(W * 0.65), int(H * 0.65)), (int(W * 0.50), int(H * 0.75))], fill=s_fill2)
        canvas.alpha_composite(shard_img)
    elif macro == "optical_warp":
        # 90s hypnotic kaleidoscopic wave warp across upper torso
        warp_img = Image.new("RGBA", (kit_gen.W, kit_gen.H), (0, 0, 0, 0))
        draw_w = ImageDraw.Draw(warp_img)
        W, H = kit_gen.W, kit_gen.H
        s_fill = tuple(second) + (220,)
        t_fill = tuple(d.get("third") or d.get("accent") or (255, 230, 40)) + (200,)
        for y_step in range(0, int(H * 0.75), 24):
            pts = []
            for x in range(0, W + 10, 20):
                y_offset = int(18 * math.sin(x / 35.0 + y_step / 20.0))
                pts.append((x, y_step + y_offset))
            c = s_fill if (y_step // 24) % 2 == 0 else t_fill
            draw_w.line(pts, fill=c, width=12)
        canvas.alpha_composite(warp_img)
    elif macro == "dual_contrast_split":
        # High-contrast diagonal chevron color blocking split
        split_img = Image.new("RGBA", (kit_gen.W, kit_gen.H), (0, 0, 0, 0))
        draw_sp = ImageDraw.Draw(split_img)
        W, H = kit_gen.W, kit_gen.H
        s_fill = tuple(second) + (255,)
        draw_sp.polygon([(0, 0), (W, 0), (W, int(H * 0.35)), (int(W * 0.5), int(H * 0.58)), (0, int(H * 0.35))], fill=s_fill)
        tip_c = tuple(d.get("third") or d.get("accent") or body) + (255,)
        draw_sp.line([(0, int(H * 0.35)), (int(W * 0.5), int(H * 0.58)), (W, int(H * 0.35))], fill=tip_c, width=6)
        canvas.alpha_composite(split_img)
    elif macro == "graffiti_splatter":
        # Urban 90s streetwear spray/splatter graphics bursting across torso
        sp_img = Image.new("RGBA", (kit_gen.W, kit_gen.H), (0, 0, 0, 0))
        draw_gp = ImageDraw.Draw(sp_img)
        W, H = kit_gen.W, kit_gen.H
        rng = np.random.default_rng(42)
        s_fill = tuple(second) + (240,)
        t_fill = tuple(d.get("third") or d.get("accent") or (255, 230, 40)) + (240,)
        for _ in range(70):
            cx = int(rng.integers(int(W * 0.1), int(W * 0.9)))
            cy = int(rng.integers(int(H * 0.05), int(H * 0.70)))
            rad = int(rng.integers(12, 38))
            c = s_fill if rng.random() > 0.4 else t_fill
            draw_gp.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=c)
            for _ in range(6):
                ox = int(rng.integers(-40, 40))
                oy = int(rng.integers(-40, 40))
                dr = int(rng.integers(2, 6))
                draw_gp.ellipse([cx + ox - dr, cy + oy - dr, cx + ox + dr, cy + oy + dr], fill=c)
        canvas.alpha_composite(sp_img)
    elif macro == "flame_sunburst":
        # Iconic 90s flame starburst / sunburst spikes radiating outward from chest
        flame_img = Image.new("RGBA", (kit_gen.W, kit_gen.H), (0, 0, 0, 0))
        draw_fl = ImageDraw.Draw(flame_img)
        W, H = kit_gen.W, kit_gen.H
        cx, cy = int(W * 0.5), int(H * 0.42)
        s_fill = tuple(second) + (240,)
        t_fill = tuple(d.get("third") or d.get("accent") or (255, 230, 40)) + (240,)
        num_spikes = 14
        for i in range(num_spikes):
            angle = i * (2 * math.pi / num_spikes)
            r_outer = int(H * 0.38)
            r_inner = int(H * 0.14)
            p1 = (int(cx + r_inner * math.cos(angle - 0.15)), int(cy + r_inner * math.sin(angle - 0.15)))
            p2 = (int(cx + r_outer * math.cos(angle)), int(cy + r_outer * math.sin(angle)))
            p3 = (int(cx + r_inner * math.cos(angle + 0.15)), int(cy + r_inner * math.sin(angle + 0.15)))
            c = s_fill if i % 2 == 0 else t_fill
            draw_fl.polygon([p1, p2, p3], fill=c)
        canvas.alpha_composite(flame_img)

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
        if vent_style in ("contrast_panel", "athletic_flank", "contrast_flank"):
            vent_col = d.get("second") or d.get("third") or ((22, 22, 28) if _col_lum(body) > 130 else (245, 245, 248))
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
    elif vent_style in ("athletic_flank", "contrast_flank"):
        # Modern ergonomic contrast side flank panel with athletic seam piping (BVB style)
        pipe_rgba = tuple(d.get("third") or d.get("accent") or vent_col) + (255,)
        flank_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_fl = ImageDraw.Draw(flank_layer)
        draw_fl.line([(725, 1100), (725, 1850)], fill=pipe_rgba, width=2)
        draw_fl.line([(1323, 1100), (1323, 1850)], fill=pipe_rgba, width=2)
        draw_fl.line([(746, 100), (746, 850)], fill=pipe_rgba, width=2)
        draw_fl.line([(1302, 100), (1302, 850)], fill=pipe_rgba, width=2)
        _composite_layer(atlas, flank_layer, masks["body_front"] | masks["body_back"])


def _composite_layer(atlas, layer, mask=None, dest=(0, 0)):
    """Safely alpha-composite a transparent RGBA layer onto atlas, optionally clipped by mask.

    Only the bounding box of the *effective* alpha is composited.  Pixels outside
    that box have zero source alpha, so omitting them is pixel-for-pixel
    equivalent to compositing a full 2048x2048 layer, while avoiding a large
    Pillow blend on every badge, seam and supplier mark.  `dest` lets callers
    composite a small local canvas at its true atlas position.
    """
    if layer.mode != "RGBA":
        layer = layer.convert("RGBA")

    if mask is None:
        bbox = layer.getchannel("A").getbbox()
    else:
        mask_img = _mask_img(mask)
        if mask_img.size != layer.size:
            raise ValueError("mask and layer must be the same size")
        bbox = ImageChops.multiply(mask_img, layer.getchannel("A")).getbbox()

    if not bbox:
        return

    if mask is not None:
        effective = ImageChops.multiply(
            _mask_img(mask).crop(bbox), layer.getchannel("A").crop(bbox))
        layer = layer.crop(bbox)
        layer.putalpha(effective)
    else:
        layer = layer.crop(bbox)

    atlas.alpha_composite(layer, (dest[0] + bbox[0], dest[1] + bbox[1]))


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

    # Shorts contrast calculation: must contrast against shorts base color, NOT sleeve!
    shorts_base = d.get("shorts") or d["body"]
    sh_acc = d.get("shorts_accent") or d.get("stripe_accent") or d.get("second") or d["body"]
    dist_sh = math.sqrt(sum((a - b) ** 2 for a, b in zip(shorts_base[:3], sh_acc[:3])))
    if dist_sh < 40:
        l_sh = _col_lum(shorts_base)
        if l_sh >= 128:
            # White/light shorts: contrast with shirt body or rich dark tone
            sh_acc = d["body"] if _col_lum(d["body"]) < 130 else (d.get("second") if _col_lum(d.get("second", (20, 25, 35))) < 130 else (20, 25, 35))
        else:
            sh_acc = (245, 245, 245)
    sh_acc_rgba = tuple(sh_acc) + (255,)

    # 1. ADIDAS: Three iconic parallel stripes running down outer shoulders/sleeves and shorts
    is_adidas = "adidas" in supp or d.get("sleeve_style") in ("shoulder_stripe", "adidas_stripes", "three_stripes") or d.get("shorts_style") == "three_stripes"
    if is_adidas:
        stripe_mask = np.zeros((ATLAS, ATLAS), dtype=bool)
        # Three iconic parallel stripes running across outer shoulders/sleeves (horizontal bands on PES 2021 UV atlas)
        # Measured directly from authentic PES 2021 kits (Real Madrid rm_auth, Arsenal arsenal_auth):
        # 3 parallel stripes at y: 366..384, 395..413, 424..442 across sleeve tops and chest raglans!
        for y0, y1 in [(366, 384), (395, 413), (424, 442)]:
            # Left sleeve island (player's left arm)
            stripe_mask[y0:y1, 43:450] = True
            # Front chest left shoulder raglan
            stripe_mask[y0:y1, 632:690] = True
            # Front chest right shoulder raglan
            stripe_mask[y0:y1, 1358:1416] = True
            # Right sleeve island (player's right arm)
            stripe_mask[y0:y1, 1599:2006] = True

        # Raglan shoulder seam continuation onto back panel top edges:
        for y0, y1 in [(926, 944), (955, 973), (984, 1002)]:
            stripe_mask[y0:y1, 695:970] = True
            stripe_mask[y0:y1, 1078:1354] = True

        if np.any(stripe_mask):
            stripe_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
            stripe_layer.paste(Image.new("RGBA", (ATLAS, ATLAS), acc_rgba), (0, 0), _mask_img(stripe_mask))
            _composite_layer(atlas, stripe_layer)

        # Shorts 3-stripes down outer leg seams (horizontal bands on PES 2021 UV atlas)
        # Measured directly from authentic PES 2021 kits:
        # y: 1508..1526, 1537..1555, 1566..1584 across left (68..595) and right (1452..1980) shorts islands!
        sh_stripe = np.zeros_like(shorts_mask)
        for y0, y1 in [(1508, 1526), (1537, 1555), (1566, 1584)]:
            sh_stripe[y0:y1, 68:595] = True
            sh_stripe[y0:y1, 1452:1980] = True
        sh_stripe = sh_stripe & shorts_mask
        if np.any(sh_stripe):
            sh_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
            sh_layer.paste(Image.new("RGBA", (ATLAS, ATLAS), sh_acc_rgba), (0, 0), _mask_img(sh_stripe))
            _composite_layer(atlas, sh_layer)

        # Contrast shorts hem tape / cuff band (matching authentic modern elite Adidas cuts like Mbappé/Bellingham)
        hem_m = np.zeros_like(shorts_mask)
        hem_m[1942:1968, :] = True
        hem_m = hem_m & shorts_mask
        if np.any(hem_m):
            hem_col = d.get("shorts_hem") or d.get("third") or d.get("second") or sh_acc
            if math.sqrt(sum((a - b) ** 2 for a, b in zip(shorts_base[:3], hem_col[:3]))) < 40:
                hem_col = sh_acc
            hem_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
            hem_layer.paste(Image.new("RGBA", (ATLAS, ATLAS), tuple(hem_col) + (255,)), (0, 0), _mask_img(hem_m))
            _composite_layer(atlas, hem_layer)

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

    # 7. CASTORE: Precision dual sonic wings, back-neck laser bars, and angled shorts vent
    elif "castore" in supp:
        castore_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_c = ImageDraw.Draw(castore_layer)
        # Dual sonic wing chevrons along sleeve tops / shoulder ridges
        for cx in range(120, 420, 48):
            draw_c.polygon([(cx - 12, 404), (cx, 412), (cx + 12, 404),
                            (cx + 8, 404), (cx, 409), (cx - 8, 404)], fill=acc_rgba)
            draw_c.polygon([(cx - 12, 416), (cx, 424), (cx + 12, 416),
                            (cx + 8, 416), (cx, 421), (cx - 8, 416)], fill=acc_rgba)
        for cx in range(1620, 1920, 48):
            draw_c.polygon([(cx - 12, 404), (cx, 412), (cx + 12, 404),
                            (cx + 8, 404), (cx, 409), (cx - 8, 404)], fill=acc_rgba)
            draw_c.polygon([(cx - 12, 416), (cx, 424), (cx + 12, 416),
                            (cx + 8, 416), (cx, 421), (cx - 8, 416)], fill=acc_rgba)
        # Precision back-neck laser ventilation bars (upper back)
        for by in range(230, 275, 12):
            draw_c.rounded_rectangle([985, by, 1063, by + 4], radius=2, fill=acc_rgba)
        # Shorts angular geometric vent inserts at outer lower hem
        draw_c.polygon([(40, 1900), (95, 1955), (40, 1955)], fill=sh_acc_rgba)
        draw_c.polygon([(2008, 1900), (1953, 1955), (2008, 1955)], fill=sh_acc_rgba)
        _composite_layer(atlas, castore_layer, sleeve_mask | body_back | shorts_mask)

    # 8. MACRON: Iconic "Hero" shoulder stamps and breathable flank panels
    elif "macron" in supp:
        macron_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_m = ImageDraw.Draw(macron_layer)
        # Repeating stylized Macron Hero stamps on sleeve ridges
        for cx in range(120, 410, 44):
            draw_m.ellipse([cx - 4, 402, cx + 4, 410], fill=acc_rgba)
            draw_m.polygon([(cx - 10, 414), (cx, 411), (cx + 10, 414),
                            (cx + 8, 424), (cx, 421), (cx - 8, 424)], fill=acc_rgba)
        for cx in range(1630, 1920, 44):
            draw_m.ellipse([cx - 4, 402, cx + 4, 410], fill=acc_rgba)
            draw_m.polygon([(cx - 10, 414), (cx, 411), (cx + 10, 414),
                            (cx + 8, 424), (cx, 421), (cx - 8, 424)], fill=acc_rgba)
        # Torso flank inset panels
        draw_m.rectangle([664, 1140, 688, 1820], fill=acc_rgba)
        draw_m.rectangle([1360, 1140, 1384, 1820], fill=acc_rgba)
        # Shorts lateral accent stripe
        draw_m.rectangle([40, 1240, 52, 1920], fill=sh_acc_rgba)
        draw_m.rectangle([1996, 1240, 2008, 1920], fill=sh_acc_rgba)
        _composite_layer(atlas, macron_layer, sleeve_mask | masks["body_front"] | shorts_mask)

    # 9. NEW BALANCE: Dynamic speed cuffs and aerodynamic shoulder darts
    elif "newbalance" in supp or "new balance" in supp or "nb" in supp:
        nb_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_nb = ImageDraw.Draw(nb_layer)
        # Asymmetric angled speed cuffs (signature NB angled flash)
        draw_nb.polygon([(50, 642), (430, 642), (430, 668), (180, 668), (140, 655), (50, 655)], fill=acc_rgba)
        draw_nb.polygon([(1618, 642), (1998, 642), (1998, 655), (1908, 655), (1868, 668), (1618, 668)], fill=acc_rgba)
        # Aerodynamic collarbone speed dart lines
        draw_nb.line([(760, 1000), (840, 1050)], fill=acc_rgba, width=3)
        draw_nb.line([(1288, 1000), (1208, 1050)], fill=acc_rgba, width=3)
        # Shorts vertical speed flash on outer hem
        draw_nb.polygon([(40, 1820), (60, 1820), (52, 1950), (40, 1950)], fill=sh_acc_rgba)
        draw_nb.polygon([(2008, 1820), (1988, 1820), (1996, 1950), (2008, 1950)], fill=sh_acc_rgba)
        _composite_layer(atlas, nb_layer, sleeve_mask | masks["body_front"] | shorts_mask)

    # 10. JOMA: Signature running "J" ribbon tape and twin-stripe shorts flank
    elif "joma" in supp:
        joma_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_j = ImageDraw.Draw(joma_layer)
        # Geometric Joma repeating ribbon tape
        for cx in range(110, 420, 36):
            draw_j.polygon([(cx - 8, 405), (cx + 8, 405), (cx + 8, 411), (cx, 411), (cx, 421), (cx - 8, 421)], fill=acc_rgba)
        for cx in range(1620, 1930, 36):
            draw_j.polygon([(cx - 8, 405), (cx + 8, 405), (cx + 8, 411), (cx, 411), (cx, 421), (cx - 8, 421)], fill=acc_rgba)
        # Twin parallel pinstripes down shorts sides
        draw_j.rectangle([40, 1240, 44, 1920], fill=sh_acc_rgba)
        draw_j.rectangle([48, 1240, 52, 1920], fill=sh_acc_rgba)
        draw_j.rectangle([1996, 1240, 2000, 1920], fill=sh_acc_rgba)
        draw_j.rectangle([2004, 1240, 2008, 1920], fill=sh_acc_rgba)
        _composite_layer(atlas, joma_layer, sleeve_mask | shorts_mask)

    # 11. MIZUNO: Iconic Runbird wing chevrons and asymmetric hem notch
    elif "mizuno" in supp:
        mizuno_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_mz = ImageDraw.Draw(mizuno_layer)
        # Mizuno Runbird aerodynamic feather chevron accents
        for cx in range(130, 400, 48):
            draw_mz.polygon([(cx - 14, 418), (cx - 2, 406), (cx + 14, 406), (cx + 4, 414), (cx - 4, 414), (cx - 10, 422)], fill=acc_rgba)
        for cx in range(1640, 1910, 48):
            draw_mz.polygon([(cx + 14, 418), (cx + 2, 406), (cx - 14, 406), (cx - 4, 414), (cx + 4, 414), (cx + 10, 422)], fill=acc_rgba)
        # Asymmetric shorts thigh hem notch
        draw_mz.polygon([(38, 1920), (78, 1960), (38, 1960)], fill=sh_acc_rgba)
        draw_mz.polygon([(2010, 1920), (1970, 1960), (2010, 1960)], fill=sh_acc_rgba)
        _composite_layer(atlas, mizuno_layer, sleeve_mask | shorts_mask)

    # 12. EA7: Minimalist luxury 7-slash flank cluster and refined trim
    elif "ea7" in supp:
        ea7_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_ea = ImageDraw.Draw(ea7_layer)
        # 7 crisp parallel laser micro-slashes on lower left flank
        for i, dy in enumerate(range(0, 70, 10)):
            draw_ea.line([(680 + i * 2, 1680 + dy), (715 + i * 2, 1700 + dy)], fill=acc_rgba, width=3)
        # Minimalist single pinstripe down shorts side
        draw_ea.rectangle([44, 1260, 48, 1900], fill=sh_acc_rgba)
        draw_ea.rectangle([2000, 1260, 2004, 1900], fill=sh_acc_rgba)
        _composite_layer(atlas, ea7_layer, masks["body_front"] | shorts_mask)


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
    if (max(l_sh, l_acc) + 12.5) / (min(l_sh, l_acc) + 12.5) < 2.0:
        shorts_accent = (245, 245, 245) if l_sh < 128 else (20, 25, 35)

    sh_col = tuple(shorts_accent) + (255,)
    tip_col = d.get("shorts_tip") or d.get("third") or ((255, 255, 255) if l_sh < 128 else (10, 15, 20))
    tip_rgba = tuple(tip_col) + (255,)

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

    elif shorts_style == "dual_side_stripes":
        dual_m = np.zeros_like(shorts_mask)
        dual_m[:, 22:38] = True
        dual_m[:, 48:64] = True
        dual_m[:, 1984:2000] = True
        dual_m[:, 2010:2026] = True
        dual_m = dual_m & shorts_mask
        if np.any(dual_m):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), sh_col), (0, 0), _mask_img(dual_m))

    elif shorts_style == "hem_tape":
        hem_mask = np.zeros_like(shorts_mask)
        hem_mask[1935:1968, :] = True
        hem_mask = hem_mask & shorts_mask
        if np.any(hem_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), sh_col), (0, 0), _mask_img(hem_mask))

    elif shorts_style == "contrast_flank_panel":
        panel_m = np.zeros_like(shorts_mask)
        piping_m = np.zeros_like(shorts_mask)
        for y in range(1159, 1970):
            t = (y - 1159) / float(1970 - 1159)
            w = int(45 + 75 * (t ** 1.3))
            panel_m[y, 22:22 + w] = True
            piping_m[y, 22 + w - 3:22 + w] = True
            panel_m[y, 2026 - w:2026] = True
            piping_m[y, 2026 - w:2026 - w + 3] = True
        panel_m = panel_m & shorts_mask
        piping_m = piping_m & shorts_mask
        if np.any(panel_m):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), sh_col), (0, 0), _mask_img(panel_m))
        if np.any(piping_m):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_rgba), (0, 0), _mask_img(piping_m))

    elif shorts_style == "hem_turnup_notch":
        hem_m = np.zeros_like(shorts_mask)
        hem_m[1940:1968, :] = True
        notch_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_n = ImageDraw.Draw(notch_layer)
        draw_n.polygon([(20, 1940), (45, 1895), (70, 1940)], fill=sh_col)
        draw_n.polygon([(1978, 1940), (2003, 1895), (2028, 1940)], fill=sh_col)
        draw_n.line([(20, 1940), (45, 1895), (70, 1940)], fill=tip_rgba, width=2)
        draw_n.line([(1978, 1940), (2003, 1895), (2028, 1940)], fill=tip_rgba, width=2)
        hem_m = hem_m & shorts_mask
        if np.any(hem_m):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), sh_col), (0, 0), _mask_img(hem_m))
        atlas.paste(notch_layer, (0, 0), _mask_img(shorts_mask))

    elif shorts_style == "two_tone_halves":
        right_m = np.zeros_like(shorts_mask)
        right_m[:, 1300:2048] = True
        right_m = right_m & shorts_mask
        if np.any(right_m):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), sh_col), (0, 0), _mask_img(right_m))
        hem_left = np.zeros_like(shorts_mask)
        hem_left[1942:1968, 0:1000] = True
        hem_left = hem_left & shorts_mask
        if np.any(hem_left):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), sh_col), (0, 0), _mask_img(hem_left))
        hem_right = np.zeros_like(shorts_mask)
        hem_right[1942:1968, 1300:2048] = True
        hem_right = hem_right & shorts_mask
        if np.any(hem_right):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tuple(shorts_base) + (255,)), (0, 0), _mask_img(hem_right))

    elif shorts_style == "gradient_side_fade":
        grad_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_g = ImageDraw.Draw(grad_layer)
        y_top = 1320
        y_bot = 1968
        for y in range(y_top, y_bot):
            alpha_frac = ((y - y_top) / float(y_bot - y_top)) ** 1.5
            col = tuple(shorts_accent) + (int(255 * alpha_frac),)
            draw_g.line([(18, y), (110, y)], fill=col)
            draw_g.line([(1938, y), (2030, y)], fill=col)
        atlas.paste(grad_layer, (0, 0), _mask_img(shorts_mask))

    elif shorts_style == "contrast_waistband":
        wb_m = np.zeros_like(shorts_mask)
        wb_m[1159:1235, :] = True
        wb_m = wb_m & shorts_mask
        if np.any(wb_m):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), sh_col), (0, 0), _mask_img(wb_m))
            groove_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
            draw_w = ImageDraw.Draw(groove_layer)
            groove_dark = (max(0, shorts_accent[0] - 40), max(0, shorts_accent[1] - 40), max(0, shorts_accent[2] - 40), 200)
            groove_light = (min(255, shorts_accent[0] + 40), min(255, shorts_accent[1] + 40), min(255, shorts_accent[2] + 40), 160)
            for yg in [1182, 1208]:
                draw_w.line([(0, yg), (2047, yg)], fill=groove_dark, width=1)
                draw_w.line([(0, yg + 1), (2047, yg + 1)], fill=groove_light, width=1)
            draw_w.rectangle([(292, 1192), (298, 1198)], fill=(15, 20, 25, 255))
            draw_w.rectangle([(308, 1192), (314, 1198)], fill=(15, 20, 25, 255))
            draw_w.line([(295, 1198), (292, 1218)], fill=tip_rgba, width=2)
            draw_w.line([(311, 1198), (314, 1218)], fill=tip_rgba, width=2)
            atlas.paste(groove_layer, (0, 0), _mask_img(wb_m))


def _apply_engineered_socks(atlas, d, masks):
    """Render authentic engineered football socks styling across 11 distinctive styles."""
    socks_style = d.get("socks_style", "solid")
    if not socks_style or socks_style == "solid":
        return

    socks_mask = masks["socks"]
    socks_base = tuple(d.get("socks") or d["body"])
    socks_accent = tuple(d.get("socks_accent") or d.get("second") or (245, 245, 245))
    socks_tip = tuple(d.get("socks_tip") or d.get("third") or socks_accent)

    l_so = _col_lum(socks_base)
    l_acc = _col_lum(socks_accent)
    if (max(l_so, l_acc) + 12.5) / (min(l_so, l_acc) + 12.5) < 2.0:
        socks_accent = (245, 245, 245) if l_so < 128 else (20, 25, 35)

    so_col = tuple(socks_accent) + (255,)
    tip_col = tuple(socks_tip) + (255,)

    if socks_style == "turnover_hoop":
        cuff_so = np.zeros_like(socks_mask)
        cuff_so[630:692, :] = True
        cuff_so = cuff_so & socks_mask
        if np.any(cuff_so):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), so_col), (0, 0), _mask_img(cuff_so))
            tip_m = np.zeros_like(socks_mask)
            tip_m[690:696, :] = True
            tip_m = tip_m & socks_mask
            if np.any(tip_m):
                atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col), (0, 0), _mask_img(tip_m))

    elif socks_style == "dual_hoop_turnover":
        hoop_m = np.zeros_like(socks_mask)
        hoop_m[632:654, :] = True
        hoop_m[666:688, :] = True
        hoop_m = hoop_m & socks_mask
        if np.any(hoop_m):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), so_col), (0, 0), _mask_img(hoop_m))
            tip_m = np.zeros_like(socks_mask)
            tip_m[688:694, :] = True
            tip_m = tip_m & socks_mask
            if np.any(tip_m):
                atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col), (0, 0), _mask_img(tip_m))

    elif socks_style == "triple_hoop_turnover":
        hoop_m = np.zeros_like(socks_mask)
        hoop_m[630:644, :] = True
        hoop_m[652:666, :] = True
        hoop_m[674:688, :] = True
        hoop_m = hoop_m & socks_mask
        if np.any(hoop_m):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), so_col), (0, 0), _mask_img(hoop_m))
            tip_m = np.zeros_like(socks_mask)
            tip_m[688:694, :] = True
            tip_m = tip_m & socks_mask
            if np.any(tip_m):
                atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col), (0, 0), _mask_img(tip_m))

    elif socks_style == "full_hooped_body":
        hoop_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_h = ImageDraw.Draw(hoop_layer)
        for y_top in range(630, 1020, 36):
            draw_h.rectangle([(0, y_top), (ATLAS - 1, y_top + 20)], fill=so_col)
            draw_h.line([(0, y_top), (ATLAS - 1, y_top)], fill=tip_col, width=1)
            draw_h.line([(0, y_top + 20), (ATLAS - 1, y_top + 20)], fill=tip_col, width=1)
        atlas.paste(hoop_layer, (0, 0), _mask_img(socks_mask))

    elif socks_style == "calf_band":
        band_so = np.zeros_like(socks_mask)
        band_so[825:885, :] = True
        band_so = band_so & socks_mask
        if np.any(band_so):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), so_col), (0, 0), _mask_img(band_so))
            border_m = np.zeros_like(socks_mask)
            border_m[822:825, :] = True
            border_m[885:888, :] = True
            border_m = border_m & socks_mask
            if np.any(border_m):
                atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col), (0, 0), _mask_img(border_m))

    elif socks_style == "triple_calf_hoops":
        hoop_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_th = ImageDraw.Draw(hoop_layer)
        for y_top in [770, 806, 842]:
            draw_th.rectangle([(0, y_top), (ATLAS - 1, y_top + 18)], fill=so_col)
            draw_th.line([(0, y_top + 9), (ATLAS - 1, y_top + 9)], fill=tip_col, width=2)
        atlas.paste(hoop_layer, (0, 0), _mask_img(socks_mask))

    elif socks_style == "vertical_back_spine":
        spine_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_sp = ImageDraw.Draw(spine_layer)
        draw_sp.rectangle([(177, 630), (201, 1060)], fill=so_col)
        draw_sp.line([(175, 630), (175, 1060)], fill=tip_col, width=2)
        draw_sp.line([(203, 630), (203, 1060)], fill=tip_col, width=2)

        draw_sp.rectangle([(1846, 630), (1870, 1060)], fill=so_col)
        draw_sp.line([(1844, 630), (1844, 1060)], fill=tip_col, width=2)
        draw_sp.line([(1872, 630), (1872, 1060)], fill=tip_col, width=2)

        draw_sp.rectangle([(0, 630), (ATLAS - 1, 646)], fill=so_col)
        atlas.paste(spine_layer, (0, 0), _mask_img(socks_mask))

    elif socks_style == "gradient_dip":
        dip_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_dp = ImageDraw.Draw(dip_layer)
        draw_dp.rectangle([(0, 920), (ATLAS - 1, 1159)], fill=so_col)
        draw_dp.rectangle([(0, 902), (ATLAS - 1, 908)], fill=tip_col)
        draw_dp.rectangle([(0, 912), (ATLAS - 1, 916)], fill=tip_col)
        atlas.paste(dip_layer, (0, 0), _mask_img(socks_mask))

    elif socks_style == "gradient_fade":
        fade_so = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_f = ImageDraw.Draw(fade_so)
        for y in range(630, 1080):
            t = ((y - 630) / float(max(1, 1080 - 630))) ** 1.3
            c = (int(socks_base[0] * (1 - t) + socks_accent[0] * t),
                 int(socks_base[1] * (1 - t) + socks_accent[1] * t),
                 int(socks_base[2] * (1 - t) + socks_accent[2] * t), 255)
            draw_f.line([(0, y), (ATLAS - 1, y)], fill=c)
        atlas.paste(fade_so, (0, 0), _mask_img(socks_mask))

    elif socks_style == "ankle_bracket_cuff":
        br_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_br = ImageDraw.Draw(br_layer)
        draw_br.rectangle([(0, 630), (ATLAS - 1, 644)], fill=so_col)
        draw_br.rectangle([(0, 955), (ATLAS - 1, 980)], fill=so_col)
        draw_br.line([(0, 955), (ATLAS - 1, 955)], fill=tip_col, width=2)
        draw_br.line([(0, 980), (ATLAS - 1, 980)], fill=tip_col, width=2)
        draw_br.rectangle([(0, 995), (ATLAS - 1, 1015)], fill=so_col)
        atlas.paste(br_layer, (0, 0), _mask_img(socks_mask))

    elif socks_style == "chevron_stack":
        ch_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_ch = ImageDraw.Draw(ch_layer)
        for y_ch in [740, 775, 810, 845]:
            draw_ch.polygon([(189, y_ch + 22), (189 - 36, y_ch), (189 - 22, y_ch), (189, y_ch + 14), (189 + 22, y_ch), (189 + 36, y_ch)], fill=so_col)
            draw_ch.polygon([(1858, y_ch + 22), (1858 - 36, y_ch), (1858 - 22, y_ch), (1858, y_ch + 14), (1858 + 22, y_ch), (1858 + 36, y_ch)], fill=so_col)
        atlas.paste(ch_layer, (0, 0), _mask_img(socks_mask))


def _apply_engineered_collar(atlas, d, masks):
    """Render authentic collar styling: crew, retro_crew, v_neck, crossover_v, polo, polo_v_notch, dual_tipped, mandarin_button."""
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

    elif style == "retro_crew":
        # Broad 32px contrast crew rib band with concentric double-tipping (LOSC Lille style)
        rib_mask = np.zeros_like(collar_mask)
        rib_mask[1868:1900, :] = collar_mask[1868:1900, :]
        if np.any(rib_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), c_rgba), (0, 0), _mask_img(rib_mask))

        t1_mask = np.zeros_like(collar_mask)
        t1_mask[1868:1873, :] = collar_mask[1868:1873, :]
        t1_mask[1895:1899, :] = collar_mask[1895:1899, :]
        if np.any(t1_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(t1_mask))

        # Drop-stitch contour line on chest front neckline (X: 970..1078, Y: 998..1024)
        crew_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_c = ImageDraw.Draw(crew_layer)
        draw_c.arc([970, 990, 1078, 1032], start=20, end=160, fill=t1_rgba, width=2)
        _composite_layer(atlas, crew_layer, body_front)

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

    elif style == "crossover_v":
        # Layered athletic 2-color V-neck (BVB purple/volt & yellow/black style)
        t1_mask = np.zeros_like(collar_mask)
        t1_mask[1868:1874, :] = collar_mask[1868:1874, :]
        if np.any(t1_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(t1_mask))

        # Chest apex: inner electric/contrast triangular wedge + overlapping crossover flaps
        v_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_v = ImageDraw.Draw(v_layer)
        draw_v.polygon([(992, 996), (1056, 996), (1024, 1066)], fill=t1_rgba)
        draw_v.polygon([(990, 996), (1014, 996), (1032, 1060), (1018, 1064)], fill=c_rgba)
        draw_v.line([(1014, 996), (1032, 1060)], fill=t2_rgba, width=2)
        draw_v.polygon([(1034, 996), (1058, 996), (1030, 1064), (1016, 1060)], fill=c_rgba)
        draw_v.line([(1034, 996), (1016, 1060)], fill=t2_rgba, width=2)
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

    elif style == "polo_v_notch":
        # Sartorial open-wing polo with V-notch placket & jacquard knit tipping (Venezia Nocta style)
        crease_mask = np.zeros_like(collar_mask)
        crease_mask[1945:1950, :] = collar_mask[1945:1950, :]
        if np.any(crease_mask):
            crease_col = (max(0, int(collar[0] * 0.75)),
                          max(0, int(collar[1] * 0.75)),
                          max(0, int(collar[2] * 0.75)), 220)
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), crease_col), (0, 0), _mask_img(crease_mask))

        # Micro-checkered jacquard knit edge tipping on collar wings
        t_base = np.zeros_like(collar_mask)
        t_base[1868:1882, :] = collar_mask[1868:1882, :]
        if np.any(t_base):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(t_base))
            y_w, x_w = np.where(t_base)
            checks = ((x_w // 4) + (y_w // 4)) % 2 == 0
            if np.any(checks):
                c_chk = np.zeros_like(collar_mask)
                c_chk[y_w[checks], x_w[checks]] = True
                atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t2_rgba), (0, 0), _mask_img(c_chk))

        # Chest apex open V-notch placket
        notch_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_n = ImageDraw.Draw(notch_layer)
        # Recessed inner shadow cutout
        draw_n.polygon([(1008, 996), (1040, 996), (1024, 1046)], fill=(18, 18, 22, 255))
        # Folded wing lapels framing the V notch
        draw_n.polygon([(988, 996), (1008, 996), (1024, 1046), (1016, 1048), (992, 1004)], fill=c_rgba)
        draw_n.polygon([(1060, 996), (1040, 996), (1024, 1046), (1032, 1048), (1056, 1004)], fill=c_rgba)
        # Micro-stitch borders
        draw_n.line([(988, 996), (1024, 1046)], fill=t1_rgba, width=2)
        draw_n.line([(1060, 996), (1024, 1046)], fill=t2_rgba, width=2)
        draw_n.line([(1024, 1046), (1024, 1085)], fill=t1_rgba, width=2)
        _composite_layer(atlas, notch_layer, body_front)

    elif style == "mandarin_button":
        # Minimalist stand-up band collar with button slit placket
        band_mask = np.zeros_like(collar_mask)
        band_mask[1868:1886, :] = collar_mask[1868:1886, :]
        if np.any(band_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), c_rgba), (0, 0), _mask_img(band_mask))
        t_mask = np.zeros_like(collar_mask)
        t_mask[1868:1872, :] = collar_mask[1868:1872, :]
        if np.any(t_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(t_mask))

        m_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_m = ImageDraw.Draw(m_layer)
        draw_m.line([(1024, 996), (1024, 1060)], fill=t1_rgba, width=2)
        draw_m.ellipse([1020, 1030, 1028, 1038], fill=(245, 245, 248, 255), outline=t1_rgba, width=1)
        _composite_layer(atlas, m_layer, body_front)

    elif style == "striped_rib_polo":
        # Athletic multi-striped polo with spread wings & inset ribbed triangular gusset (Napoli EA7 style)
        crease_mask = np.zeros_like(collar_mask)
        crease_mask[1945:1950, :] = collar_mask[1945:1950, :]
        if np.any(crease_mask):
            crease_col = (max(0, int(collar[0] * 0.75)),
                          max(0, int(collar[1] * 0.75)),
                          max(0, int(collar[2] * 0.75)), 220)
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), crease_col), (0, 0), _mask_img(crease_mask))

        base_polo = np.zeros_like(collar_mask)
        base_polo[1868:1945, :] = collar_mask[1868:1945, :]
        if np.any(base_polo):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), c_rgba), (0, 0), _mask_img(base_polo))

        # 3 athletic micro-stripes along the outer folded collar edge
        s1 = np.zeros_like(collar_mask)
        s1[1868:1871, :] = collar_mask[1868:1871, :]
        if np.any(s1):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(s1))

        s2 = np.zeros_like(collar_mask)
        s2[1873:1876, :] = collar_mask[1873:1876, :]
        if np.any(s2):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t2_rgba), (0, 0), _mask_img(s2))

        s3 = np.zeros_like(collar_mask)
        s3[1878:1881, :] = collar_mask[1878:1881, :]
        if np.any(s3):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(s3))

        # Inset triangular ribbed gusset at the chest apex of body_front (X: 1004..1044, Y: 996..1048)
        gusset_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_g = ImageDraw.Draw(gusset_layer)
        draw_g.polygon([(1004, 996), (1044, 996), (1024, 1048)], fill=c_rgba)
        for rx in range(1010, 1039, 4):
            draw_g.line([(rx, 998), (rx, max(1000, 1044 - int(abs(rx - 1024) * 2.2)))], fill=t1_rgba, width=1)
        draw_g.line([(1004, 996), (1024, 1048)], fill=t1_rgba, width=2)
        draw_g.line([(1044, 996), (1024, 1048)], fill=t1_rgba, width=2)
        _composite_layer(atlas, gusset_layer, body_front)

    elif style == "wrap_v_neck":
        # Overlapping kimono / crossover wrap collar with asymmetric angled lapel
        rib_mask = np.zeros_like(collar_mask)
        rib_mask[1868:1892, :] = collar_mask[1868:1892, :]
        if np.any(rib_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), c_rgba), (0, 0), _mask_img(rib_mask))
        t_mask = np.zeros_like(collar_mask)
        t_mask[1868:1874, :] = collar_mask[1868:1874, :]
        if np.any(t_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(t_mask))

        # Asymmetric overlapping wrap lapels on body_front apex
        wrap_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_w = ImageDraw.Draw(wrap_layer)
        draw_w.polygon([(986, 996), (1014, 996), (1042, 1060), (1022, 1066)], fill=c_rgba)
        draw_w.line([(1014, 996), (1042, 1060)], fill=t1_rgba, width=2)
        draw_w.polygon([(1062, 996), (1034, 996), (1012, 1052), (1026, 1058)], fill=c_rgba)
        draw_w.line([(1034, 996), (1012, 1052)], fill=t2_rgba, width=2)
        draw_w.line([(986, 996), (1022, 1066)], fill=t1_rgba, width=2)
        draw_w.line([(1062, 996), (1026, 1058)], fill=t1_rgba, width=2)
        _composite_layer(atlas, wrap_layer, body_front)

    elif style == "grandad_collar":
        # Modern stand-up band collar with 2-button vertical Henley placket
        band_mask = np.zeros_like(collar_mask)
        band_mask[1868:1890, :] = collar_mask[1868:1890, :]
        if np.any(band_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), c_rgba), (0, 0), _mask_img(band_mask))
        t_mask = np.zeros_like(collar_mask)
        t_mask[1868:1873, :] = collar_mask[1868:1873, :]
        if np.any(t_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(t_mask))

        henley_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_h = ImageDraw.Draw(henley_layer)
        draw_h.rectangle([1014, 996, 1034, 1082], fill=c_rgba)
        draw_h.rectangle([1014, 996, 1034, 1082], outline=t1_rgba, width=2)
        draw_h.line([(1024, 996), (1024, 1080)], fill=t1_rgba, width=1)
        btn_col = (245, 245, 248, 255) if _col_lum(collar) < 160 else (25, 25, 30, 255)
        for by in (1026, 1062):
            draw_h.ellipse([1020, by - 4, 1028, by + 4], fill=btn_col, outline=t1_rgba, width=1)
            draw_h.line([(1022, by), (1026, by)], fill=t1_rgba, width=1)
        _composite_layer(atlas, henley_layer, body_front)

    elif style == "square_neck":
        # Athletic square / trapezoidal neckline with mitered corners
        rib_mask = np.zeros_like(collar_mask)
        rib_mask[1868:1888, :] = collar_mask[1868:1888, :]
        if np.any(rib_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), c_rgba), (0, 0), _mask_img(rib_mask))
        t_mask = np.zeros_like(collar_mask)
        t_mask[1868:1873, :] = collar_mask[1868:1873, :]
        if np.any(t_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(t_mask))

        sq_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_sq = ImageDraw.Draw(sq_layer)
        draw_sq.polygon([(984, 996), (1064, 996), (1052, 1042), (996, 1042)], fill=c_rgba)
        draw_sq.line([(984, 996), (996, 1042), (1052, 1042), (1064, 996)], fill=t1_rgba, width=3)
        draw_sq.line([(996, 1042), (1004, 1032)], fill=t2_rgba, width=2)
        draw_sq.line([(1052, 1042), (1044, 1032)], fill=t2_rgba, width=2)
        _composite_layer(atlas, sq_layer, body_front)

    elif style == "contrast_split_collar":
        # Two-tone split collar: left half primary/collar_col, right half secondary/t1_rgba
        c_left = np.zeros_like(collar_mask)
        c_left[:, :1024] = collar_mask[:, :1024]
        if np.any(c_left):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), c_rgba), (0, 0), _mask_img(c_left))

        c_right = np.zeros_like(collar_mask)
        c_right[:, 1024:] = collar_mask[:, 1024:]
        if np.any(c_right):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(c_right))

        split_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_sp = ImageDraw.Draw(split_layer)
        draw_sp.line([(1024, 996), (1024, 1048)], fill=t2_rgba, width=2)
        _composite_layer(atlas, split_layer, body_front)

    elif style == "laced_placket":
        # Heritage lace-up placket with cross-lacing and eyelets
        crease_mask = np.zeros_like(collar_mask)
        crease_mask[1945:1950, :] = collar_mask[1945:1950, :]
        if np.any(crease_mask):
            crease_col = (max(0, int(collar[0] * 0.75)),
                          max(0, int(collar[1] * 0.75)),
                          max(0, int(collar[2] * 0.75)), 220)
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), crease_col), (0, 0), _mask_img(crease_mask))

        t_mask = np.zeros_like(collar_mask)
        t_mask[1868:1878, :] = collar_mask[1868:1878, :]
        if np.any(t_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(t_mask))

        lace_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_l = ImageDraw.Draw(lace_layer)
        draw_l.polygon([(1008, 996), (1040, 996), (1024, 1072)], fill=(20, 20, 24, 255))
        draw_l.line([(1008, 996), (1024, 1072), (1040, 996)], fill=t1_rgba, width=2)

        cord_col = (248, 246, 240, 255) if _col_lum(collar) < 170 else (30, 30, 35, 255)
        eyelets = [(1012, 1012, 1036, 1012), (1014, 1032, 1034, 1032), (1017, 1052, 1031, 1052)]
        for lx, ly, rx, ry in eyelets:
            draw_l.ellipse([lx - 2, ly - 2, lx + 2, ly + 2], fill=t1_rgba)
            draw_l.ellipse([rx - 2, ry - 2, rx + 2, ry + 2], fill=t1_rgba)
        draw_l.line([(1012, 1012), (1034, 1032)], fill=cord_col, width=2)
        draw_l.line([(1036, 1012), (1014, 1032)], fill=cord_col, width=2)
        draw_l.line([(1014, 1032), (1031, 1052)], fill=cord_col, width=2)
        draw_l.line([(1034, 1032), (1017, 1052)], fill=cord_col, width=2)
        draw_l.line([(1024, 1052), (1020, 1078)], fill=cord_col, width=2)
        draw_l.line([(1024, 1052), (1028, 1076)], fill=cord_col, width=2)
        _composite_layer(atlas, lace_layer, body_front)

    elif style == "mock_turtleneck_micro":
        # Modern high compression athletic collar with center micro-slit
        rib_mask = np.zeros_like(collar_mask)
        rib_mask[1868:1915, :] = collar_mask[1868:1915, :]
        if np.any(rib_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), c_rgba), (0, 0), _mask_img(rib_mask))

        t_mask = np.zeros_like(collar_mask)
        t_mask[1868:1874, :] = collar_mask[1868:1874, :]
        if np.any(t_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), t1_rgba), (0, 0), _mask_img(t_mask))

        y_c, x_c = np.where(rib_mask)
        ribs = (x_c % 4 < 2)
        if np.any(ribs):
            rib_col = (max(0, int(collar[0] * 0.86)),
                       max(0, int(collar[1] * 0.86)),
                       max(0, int(collar[2] * 0.86)), 180)
            arr = np.array(atlas)
            arr[y_c[ribs], x_c[ribs]] = rib_col
            atlas.paste(Image.fromarray(arr), (0, 0))

        mock_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_m = ImageDraw.Draw(mock_layer)
        draw_m.line([(1024, 996), (1024, 1036)], fill=t1_rgba, width=2)
        draw_m.line([(1020, 1036), (1028, 1036)], fill=t2_rgba, width=2)
        _composite_layer(atlas, mock_layer, body_front)

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
            atlas.paste(Image.fromarray(arr), (0, 0))


def _apply_engineered_cuffs(atlas, d, masks):
    """Render authentic dual-anchored sleeve cuffs across short sleeves and long sleeves.

    Supports:
    - 'solid' / 'wide_band': Bold contrast band across short & long sleeve hems
    - 'micro_tipped': Slim 6-8px contrast edge (e.g. BVB volt tip on purple)
    - 'dual_stripe': Base cuff band with two crisp micro-stripes (retro Fred Perry / Adidas)
    - 'jacquard_knit': Luxury alternating 4px micro-check knit border (Venezia style)
    """
    cuff = d.get("cuff")
    if not cuff:
        return

    sleeve_mask = masks["sleeve"]
    style = d.get("cuff_style", "solid")
    cuff_col = tuple(cuff) + (255,)
    cuff_tip = d.get("cuff_tip") or d.get("accent") or cuff
    tip_col = tuple(cuff_tip) + (255,)
    tip2 = d.get("third") or d.get("second") or cuff_tip
    tip2_col = tuple(tip2) + (255,)

    # Short sleeve cuffs: front hem (Y: 710..732) and rear hem (Y: 1130..1155)
    # Long sleeve cuffs: wrist hem (Y: 658..680)
    if style in ("solid", "wide_band", "dual_stripe", "dual_tipped"):
        cuff_mask = np.zeros_like(sleeve_mask)
        cuff_mask[658:680, :] = sleeve_mask[658:680, :]
        cuff_mask[710:732, :] = sleeve_mask[710:732, :]
        cuff_mask[1130:1155, :] = sleeve_mask[1130:1155, :]
        if np.any(cuff_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), cuff_col), (0, 0), _mask_img(cuff_mask))

        if style in ("dual_stripe", "dual_tipped"):
            stripe_mask = np.zeros_like(sleeve_mask)
            stripe_mask[662:665, :] = sleeve_mask[662:665, :]
            stripe_mask[671:674, :] = sleeve_mask[671:674, :]
            stripe_mask[714:717, :] = sleeve_mask[714:717, :]
            stripe_mask[723:726, :] = sleeve_mask[723:726, :]
            stripe_mask[1135:1138, :] = sleeve_mask[1135:1138, :]
            stripe_mask[1144:1147, :] = sleeve_mask[1144:1147, :]
            if np.any(stripe_mask):
                atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col), (0, 0), _mask_img(stripe_mask))
        elif cuff_tip and cuff_tip != cuff:
            tip_mask = np.zeros_like(sleeve_mask)
            tip_mask[676:680, :] = sleeve_mask[676:680, :]
            tip_mask[710:714, :] = sleeve_mask[710:714, :]
            tip_mask[1151:1155, :] = sleeve_mask[1151:1155, :]
            if np.any(tip_mask):
                atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col), (0, 0), _mask_img(tip_mask))

    elif style == "micro_tipped":
        tip_mask = np.zeros_like(sleeve_mask)
        tip_mask[674:680, :] = sleeve_mask[674:680, :]
        tip_mask[710:716, :] = sleeve_mask[710:716, :]
        tip_mask[1149:1155, :] = sleeve_mask[1149:1155, :]
        if np.any(tip_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col), (0, 0), _mask_img(tip_mask))

    elif style == "jacquard_knit":
        base_mask = np.zeros_like(sleeve_mask)
        base_mask[664:680, :] = sleeve_mask[664:680, :]
        base_mask[710:728, :] = sleeve_mask[710:728, :]
        base_mask[1135:1155, :] = sleeve_mask[1135:1155, :]
        if np.any(base_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), cuff_col), (0, 0), _mask_img(base_mask))

        y_s, x_s = np.where(base_mask)
        checks = ((x_s // 4) + (y_s // 4)) % 2 == 0
        if np.any(checks):
            check_mask = np.zeros_like(sleeve_mask)
            check_mask[y_s[checks], x_s[checks]] = True
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col), (0, 0), _mask_img(check_mask))

    elif style == "striped_rib":
        # Multi-stripe ribbed athletic cuff (3 micro-stripes matching striped_rib_polo)
        cuff_mask = np.zeros_like(sleeve_mask)
        cuff_mask[658:680, :] = sleeve_mask[658:680, :]
        cuff_mask[710:732, :] = sleeve_mask[710:732, :]
        cuff_mask[1130:1155, :] = sleeve_mask[1130:1155, :]
        if np.any(cuff_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), cuff_col), (0, 0), _mask_img(cuff_mask))

        stripe_m1 = np.zeros_like(sleeve_mask)
        stripe_m2 = np.zeros_like(sleeve_mask)
        stripe_m3 = np.zeros_like(sleeve_mask)

        # Long sleeve wrist
        stripe_m1[660:663, :] = sleeve_mask[660:663, :]
        stripe_m2[666:669, :] = sleeve_mask[666:669, :]
        stripe_m3[672:675, :] = sleeve_mask[672:675, :]

        # Short sleeve front hem
        stripe_m1[712:715, :] = sleeve_mask[712:715, :]
        stripe_m2[718:721, :] = sleeve_mask[718:721, :]
        stripe_m3[724:727, :] = sleeve_mask[724:727, :]

        # Short sleeve rear hem
        stripe_m1[1133:1136, :] = sleeve_mask[1133:1136, :]
        stripe_m2[1139:1142, :] = sleeve_mask[1139:1142, :]
        stripe_m3[1145:1148, :] = sleeve_mask[1145:1148, :]

        if np.any(stripe_m1):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col), (0, 0), _mask_img(stripe_m1))
        if np.any(stripe_m2):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip2_col), (0, 0), _mask_img(stripe_m2))
        if np.any(stripe_m3):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col), (0, 0), _mask_img(stripe_m3))

    elif style in ("accent_ring_inner", "ring_inner"):
        # Fluo/vibrant accent cuff band with a thin dark inner contrast stripe (BVB purple kit style)
        cuff_mask = np.zeros_like(sleeve_mask)
        cuff_mask[658:680, :] = sleeve_mask[658:680, :]
        cuff_mask[710:732, :] = sleeve_mask[710:732, :]
        cuff_mask[1130:1155, :] = sleeve_mask[1130:1155, :]
        if np.any(cuff_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), cuff_col), (0, 0), _mask_img(cuff_mask))

        inner_mask = np.zeros_like(sleeve_mask)
        inner_mask[667:671, :] = sleeve_mask[667:671, :]
        inner_mask[719:723, :] = sleeve_mask[719:723, :]
        inner_mask[1140:1144, :] = sleeve_mask[1140:1144, :]
        if np.any(inner_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col), (0, 0), _mask_img(inner_mask))

    elif style == "tri_color_knit":
        # 3-color heritage athletic cuff band
        cuff_mask = np.zeros_like(sleeve_mask)
        cuff_mask[658:680, :] = sleeve_mask[658:680, :]
        cuff_mask[710:732, :] = sleeve_mask[710:732, :]
        cuff_mask[1130:1155, :] = sleeve_mask[1130:1155, :]
        if np.any(cuff_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), cuff_col), (0, 0), _mask_img(cuff_mask))

        s1 = np.zeros_like(sleeve_mask)
        s2 = np.zeros_like(sleeve_mask)
        s3 = np.zeros_like(sleeve_mask)

        # Long sleeve wrist
        s1[658:665, :] = sleeve_mask[658:665, :]
        s2[665:672, :] = sleeve_mask[665:672, :]
        s3[672:680, :] = sleeve_mask[672:680, :]

        # Short sleeve front hem
        s1[710:717, :] = sleeve_mask[710:717, :]
        s2[717:724, :] = sleeve_mask[717:724, :]
        s3[724:732, :] = sleeve_mask[724:732, :]

        # Short sleeve rear hem
        s1[1130:1138, :] = sleeve_mask[1130:1138, :]
        s2[1138:1146, :] = sleeve_mask[1138:1146, :]
        s3[1146:1155, :] = sleeve_mask[1146:1155, :]

        if np.any(s1):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), cuff_col), (0, 0), _mask_img(s1))
        if np.any(s2):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col), (0, 0), _mask_img(s2))
        if np.any(s3):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip2_col), (0, 0), _mask_img(s3))

    elif style == "contrast_split":
        # Two-tone split sleeve cuff
        cuff_mask = np.zeros_like(sleeve_mask)
        cuff_mask[658:680, :] = sleeve_mask[658:680, :]
        cuff_mask[710:732, :] = sleeve_mask[710:732, :]
        cuff_mask[1130:1155, :] = sleeve_mask[1130:1155, :]

        left_half = np.zeros_like(sleeve_mask)
        right_half = np.zeros_like(sleeve_mask)
        left_half[:, :1024] = cuff_mask[:, :1024]
        right_half[:, 1024:] = cuff_mask[:, 1024:]

        if np.any(left_half):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), cuff_col), (0, 0), _mask_img(left_half))
        if np.any(right_half):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col), (0, 0), _mask_img(right_half))

    elif style == "french_turnback":
        # Luxury folded turnback cuff with contrast ridge piping
        cuff_mask = np.zeros_like(sleeve_mask)
        cuff_mask[658:680, :] = sleeve_mask[658:680, :]
        cuff_mask[710:732, :] = sleeve_mask[710:732, :]
        cuff_mask[1130:1155, :] = sleeve_mask[1130:1155, :]
        if np.any(cuff_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), cuff_col), (0, 0), _mask_img(cuff_mask))

        ridge_mask = np.zeros_like(sleeve_mask)
        ridge_mask[658:662, :] = sleeve_mask[658:662, :]
        ridge_mask[710:714, :] = sleeve_mask[710:714, :]
        ridge_mask[1130:1134, :] = sleeve_mask[1130:1134, :]
        if np.any(ridge_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col), (0, 0), _mask_img(ridge_mask))


def _apply_sleeve_architecture(atlas, d, masks):
    """Render distinctive shoulder, sleeve, and yoke architecture:
    - 'solid': Classic clean authentic sleeve matching the base body or sleeve tone
    - 'contrast_raglan': Contrast sleeve extending into raglan cut with seam piping
    - 'shoulder_saddle_panel': Athletic yoke / saddle panel across clavicle & shoulder caps
    - 'speed_chevrons': Racing speed chevrons repeating down outer lateral sleeve ridge
    - 'gradient_sleeve_fade': Smooth vertical ombre fade from shoulder down to the cuff
    - 'brand_track_tape': Continuous branded geometric track running down sleeve ridge
    - 'split_dual_block': Half-and-half upper/lower dual color block split on sleeve
    - 'sublimated_camo_sleeve': Subtle tonal digital/organic camo micro-pattern on sleeves
    - 'seam_piping': Modern ergonomic contrast piping along raglan diagonal seams
    - 'grunge_yoke': Urban brushstroke splatter across chest/shoulder saddle and sleeves
    """
    style = d.get("sleeve_style", "solid")
    if style in ("solid", "tipped"):
        return

    body_front = masks["body_front"]
    body_back = masks["body_back"]
    sleeve_mask = masks["sleeve"]

    accent = d.get("stripe_accent") or d.get("second") or d.get("accent") or (240, 240, 245)
    acc_rgba = tuple(accent) + (255,)
    tip = d.get("third") or d.get("accent") or accent
    tip_rgba = tuple(tip) + (255,)
    sleeve_col = tuple(d.get("sleeve") or d["body"])

    if style in ("contrast_raglan", "raglan_contrast", "raglan"):
        raglan_col = tuple(d.get("sleeve") or d.get("second") or d["body"]) + (255,)
        atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), raglan_col), (0, 0), _mask_img(sleeve_mask))
        pipe_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_p = ImageDraw.Draw(pipe_layer)
        draw_p.line([(730, 960), (830, 1010), (915, 1110)], fill=acc_rgba, width=4)
        draw_p.line([(730, 960), (830, 1010), (915, 1110)], fill=tip_rgba, width=1)
        draw_p.line([(1318, 960), (1218, 1010), (1133, 1110)], fill=acc_rgba, width=4)
        draw_p.line([(1318, 960), (1218, 1010), (1133, 1110)], fill=tip_rgba, width=1)
        _composite_layer(atlas, pipe_layer, body_front | sleeve_mask)

    elif style in ("shoulder_saddle_panel", "saddle_panel", "shoulder_yoke"):
        saddle_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_s = ImageDraw.Draw(saddle_layer)
        # 1. Front chest clavicle saddle (Y: 955..1035, X: 680..1368)
        draw_s.rectangle([(680, 955), (1368, 1035)], fill=acc_rgba)
        draw_s.rectangle([(680, 1035), (1368, 1038)], fill=tip_rgba)
        # 2. Upper sleeve crown (Y: 105..260)
        draw_s.rectangle([(0, 105), (2048, 260)], fill=acc_rgba)
        draw_s.rectangle([(0, 260), (2048, 263)], fill=tip_rgba)
        _composite_layer(atlas, saddle_layer, body_front | sleeve_mask)

    elif style in ("speed_chevrons", "chevrons", "chevron_sleeve"):
        chev_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_c = ImageDraw.Draw(chev_layer)
        # Long sleeves: outer lateral lines
        for y in range(200, 580, 32):
            draw_c.polygon([(320, y), (340, y + 16), (360, y), (360, y - 8), (340, y + 8), (320, y - 8)], fill=acc_rgba)
            draw_c.polygon([(1688, y), (1708, y + 16), (1728, y), (1728, y - 8), (1708, y + 8), (1688, y - 8)], fill=acc_rgba)
        # Short sleeves: outer lateral lines
        for y in range(820, 1060, 28):
            draw_c.polygon([(522, y), (536, y + 12), (550, y), (550, y - 6), (536, y + 6), (522, y - 6)], fill=acc_rgba)
            draw_c.polygon([(1498, y), (1512, y + 12), (1526, y), (1526, y - 6), (1512, y + 6), (1498, y - 6)], fill=acc_rgba)
        _composite_layer(atlas, chev_layer, sleeve_mask)

    elif style in ("gradient_sleeve_fade", "gradient_fade", "sleeve_fade"):
        arr = np.array(atlas)
        sl_y, sl_x = np.where(sleeve_mask)
        col_top = np.array(sleeve_col, dtype=np.float32)
        col_bot = np.array(accent, dtype=np.float32)

        long_idx = (sl_y >= 105) & (sl_y < 650)
        t_long = np.clip((sl_y[long_idx] - 105) / 545.0, 0.0, 1.0) ** 1.2
        c_long = (1.0 - t_long[:, None]) * col_top + t_long[:, None] * col_bot
        arr[sl_y[long_idx], sl_x[long_idx], :3] = np.clip(c_long, 0, 255).astype(np.uint8)

        short_idx = (sl_y >= 650) & (sl_y <= 1217)
        t_short = np.clip((sl_y[short_idx] - 650) / 550.0, 0.0, 1.0) ** 1.2
        c_short = (1.0 - t_short[:, None]) * col_top + t_short[:, None] * col_bot
        arr[sl_y[short_idx], sl_x[short_idx], :3] = np.clip(c_short, 0, 255).astype(np.uint8)

        atlas.paste(Image.fromarray(arr), (0, 0))

    elif style in ("split_dual_block", "split_sleeve", "dual_block"):
        split_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_sp = ImageDraw.Draw(split_layer)
        draw_sp.rectangle([(0, 370), (2048, 650)], fill=acc_rgba)
        draw_sp.rectangle([(0, 366), (2048, 370)], fill=tip_rgba)
        draw_sp.rectangle([(0, 880), (2048, 1217)], fill=acc_rgba)
        draw_sp.rectangle([(0, 876), (2048, 880)], fill=tip_rgba)
        _composite_layer(atlas, split_layer, sleeve_mask)

    elif style in ("sublimated_camo_sleeve", "camo_sleeve", "camo"):
        cid = int(d.get("team_id") or d.get("cid") or 100)
        season = int(d.get("season", 2026))
        slot = str(d.get("slot", 1))
        seed_val = ((cid * 1000003) ^ (season * 999983) ^ (hash(slot) & 0xFFFFFFFF)) & 0xFFFFFFFF
        rng = np.random.default_rng(seed_val)

        camo_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_cm = ImageDraw.Draw(camo_layer)
        for _ in range(450):
            cx = int(rng.integers(0, ATLAS))
            cy = int(rng.integers(105, 1217))
            cw = int(rng.integers(14, 45))
            ch = int(rng.integers(10, 35))
            poly = [(cx, cy), (cx + cw, cy + 4), (cx + cw - 6, cy + ch), (cx - 4, cy + ch - 4)]
            c_fill = acc_rgba if rng.random() > 0.5 else (max(0, sleeve_col[0] - 25), max(0, sleeve_col[1] - 25), max(0, sleeve_col[2] - 25), 200)
            draw_cm.polygon(poly, fill=c_fill)
        _composite_layer(atlas, camo_layer, sleeve_mask)

    elif style in ("brand_track_tape", "track_tape"):
        tape_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_t = ImageDraw.Draw(tape_layer)

        # Long sleeve: Y: 396..420
        draw_t.rectangle([60, 396, 440, 420], fill=acc_rgba)
        draw_t.rectangle([1600, 396, 1980, 420], fill=acc_rgba)
        # Short sleeve: Y: 820..1060
        draw_t.rectangle([520, 820, 552, 1060], fill=acc_rgba)
        draw_t.rectangle([1496, 820, 1528, 1060], fill=acc_rgba)

        bg_col = tuple(d.get("sleeve") or d["body"]) + (255,)
        for cx in range(80, 430, 28):
            draw_t.polygon([(cx, 399), (cx + 10, 408), (cx, 417), (cx - 6, 417), (cx + 4, 408), (cx - 6, 399)], fill=bg_col)
        for cx in range(1620, 1970, 28):
            draw_t.polygon([(cx, 399), (cx + 10, 408), (cx, 417), (cx - 6, 417), (cx + 4, 408), (cx - 6, 399)], fill=bg_col)

        for cy in range(830, 1050, 28):
            draw_t.polygon([(524, cy), (536, cy + 10), (548, cy), (548, cy - 6), (536, cy + 4), (524, cy - 6)], fill=bg_col)
            draw_t.polygon([(1500, cy), (1512, cy + 10), (1524, cy), (1524, cy - 6), (1512, cy + 4), (1500, cy - 6)], fill=bg_col)

        _composite_layer(atlas, tape_layer, sleeve_mask)

    elif style in ("seam_piping", "piping", "raglan_piping"):
        pipe_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_p = ImageDraw.Draw(pipe_layer)
        draw_p.line([(740, 970), (840, 1020), (910, 1100)], fill=acc_rgba, width=4)
        draw_p.line([(1308, 970), (1208, 1020), (1138, 1100)], fill=acc_rgba, width=4)
        draw_p.line([(740, 970), (840, 1020), (910, 1100)], fill=tip_rgba, width=1)
        draw_p.line([(1308, 970), (1208, 1020), (1138, 1100)], fill=tip_rgba, width=1)
        _composite_layer(atlas, pipe_layer, body_front | sleeve_mask)

    elif style in ("grunge_yoke", "brush_splatter", "splatter_brush"):
        cid = int(d.get("team_id") or d.get("cid") or 126)
        season = int(d.get("season", 2026))
        slot = str(d.get("slot", 1))
        seed_val = ((cid * 1000003) ^ (season * 999983) ^ (hash(slot) & 0xFFFFFFFF)) & 0xFFFFFFFF
        rng = np.random.default_rng(seed_val)

        yoke_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_y = ImageDraw.Draw(yoke_layer)

        sleeve_acc = tuple(accent) + (255,)
        atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), sleeve_acc), (0, 0), _mask_img(sleeve_mask))

        # 1. Front chest & clavicle splatter: vertical striated brush strokes tapering down
        for _ in range(160):
            x = int(rng.integers(680, 1370))
            y = int(rng.integers(955, 1145))
            w = int(rng.integers(4, 18))
            h = int(rng.integers(30, 110))
            draw_y.polygon([(x, y), (x + w, y + 6), (x + w // 2, y + h), (x - w // 3, y + h - 10)], fill=acc_rgba)
            if rng.random() > 0.45:
                fx, fy = int(rng.integers(x - 12, x + 24)), int(rng.integers(y + h - 10, y + h + 35))
                rad = int(rng.integers(2, 6))
                draw_y.ellipse([fx, fy, fx + rad, fy + rad], fill=acc_rgba)

        # 2. Back upper saddle (Y: 720..952)
        for _ in range(90):
            x = int(rng.integers(680, 1370))
            y = int(rng.integers(740, 948))
            w = int(rng.integers(10, 34))
            h = int(rng.integers(25, 85))
            draw_y.polygon([(x, y), (x + w, y + 8), (x + w // 2, y + h), (x - w // 3, y + h - 12)], fill=acc_rgba)

        # 3. Sleeve deltoid tops (Y: 0..250)
        for _ in range(120):
            isle = 1450 if rng.random() > 0.5 else 0
            x = int(rng.integers(isle + 30, isle + 550))
            y = int(rng.integers(5, 230))
            w = int(rng.integers(8, 28))
            h = int(rng.integers(20, 65))
            draw_y.polygon([(x, y), (x + w, y + 6), (x + w // 2, y + h), (x - w // 3, y + h - 8)], fill=acc_rgba)

        _composite_layer(atlas, yoke_layer, body_front | body_back | sleeve_mask)



# --------------------------------------------------------------------------- #
#  Authentic Garment Details, Seams, Micro-Textures & 3D Relief
# --------------------------------------------------------------------------- #
def _composite_with_relief(atlas, img, x, y, relief_depth=2, shadow_opacity=65, highlight_opacity=35, mask=None):
    """Composite logo with authentic 3D silicone heat-press relief:
    - Soft ambient occlusion shadow (+2, +relief_depth + 1)
    - Crisp contact drop shadow (+1, +relief_depth)
    - Top-left specular rim highlight (-1, -1)
    - Top edge ambient specular reflection (0, -1)

    The relief is painted into a small canvas covering only the logo plus its
    shadow/highlight offsets.  That canvas is then composited at its original
    atlas position, producing byte-identical pixels without allocating a full
    2048x2042 layer for every crest/sponsor mark.
    """
    if img is None:
        return
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    w, h = img.size
    alpha = np.array(img.getchannel("A"), dtype=np.float32)
    alpha_bbox = Image.fromarray(alpha.astype(np.uint8)).getbbox()
    if not alpha_bbox:
        return
    bx0, by0, bx1, by1 = alpha_bbox

    use_relief = bool(np.any(alpha > 10))
    if use_relief:
        gx0 = max(0, x + bx0 - 1)
        gy0 = max(0, y + by0 - 1)
        gx1 = min(ATLAS, x + bx1 + 2)
        gy1 = min(ATLAS, y + by1 + relief_depth + 1)
    else:
        gx0 = max(0, x + bx0)
        gy0 = max(0, y + by0)
        gx1 = min(ATLAS, x + bx1)
        gy1 = min(ATLAS, y + by1)
    if gx0 >= gx1 or gy0 >= gy1:
        return

    layer = Image.new("RGBA", (gx1 - gx0, gy1 - gy0), (0, 0, 0, 0))

    if use_relief:
        # 1. Soft ambient occlusion shadow (+2, +relief_depth + 1)
        amb_alpha = (alpha * (shadow_opacity * 0.45 / 255.0)).astype(np.uint8)
        amb_arr = np.zeros((h, w, 4), dtype=np.uint8)
        amb_arr[:, :, :3] = (10, 12, 16)
        amb_arr[:, :, 3] = amb_alpha
        amb_img = Image.fromarray(amb_arr)
        layer.paste(amb_img, (x + 2 - gx0, y + relief_depth + 1 - gy0), amb_img)

        # 2. Crisp contact drop shadow (+1, +relief_depth)
        sh_alpha = (alpha * (shadow_opacity / 255.0)).astype(np.uint8)
        shadow_arr = np.zeros((h, w, 4), dtype=np.uint8)
        shadow_arr[:, :, :3] = (12, 14, 20)
        shadow_arr[:, :, 3] = sh_alpha
        shadow_img = Image.fromarray(shadow_arr)
        layer.paste(shadow_img, (x + 1 - gx0, y + relief_depth - gy0), shadow_img)

        # 3. Specular top-edge rim highlight (-1, -1)
        hl_alpha = (alpha * (highlight_opacity / 255.0)).astype(np.uint8)
        hl_arr = np.zeros((h, w, 4), dtype=np.uint8)
        hl_arr[:, :, :3] = (255, 255, 255)
        hl_arr[:, :, 3] = hl_alpha
        hl_img = Image.fromarray(hl_arr)
        layer.paste(hl_img, (x - 1 - gx0, y - 1 - gy0), hl_img)

        # 4. Ambient top edge specular reflection (0, -1)
        top_alpha = (alpha * (highlight_opacity * 0.55 / 255.0)).astype(np.uint8)
        top_arr = np.zeros((h, w, 4), dtype=np.uint8)
        top_arr[:, :, :3] = (245, 250, 255)
        top_arr[:, :, 3] = top_alpha
        top_img = Image.fromarray(top_arr)
        layer.paste(top_img, (x - gx0, y - 1 - gy0), top_img)

    # 5. Primary emblem
    layer.paste(img, (x - gx0, y - gy0), img)

    local_mask = None
    if mask is not None:
        local_mask = _mask_img(mask).crop((gx0, gy0, gx1, gy1))
    _composite_layer(atlas, layer, local_mask, dest=(gx0, gy0))


_FABRIC_CACHE = OrderedDict()


def _fabric_texture_data(masks):
    """Build (and cache per worker) the static fabric mask / delta tiles."""
    key = id(masks)
    hit = _FABRIC_CACHE.get(key)
    if hit is not None and hit[0] is masks:
        _FABRIC_CACHE.move_to_end(key)
        return hit[1]

    fabric_mask = np.zeros((ATLAS, ATLAS), dtype=bool)
    for key_name in ("body_front", "body_back", "sleeve", "shorts", "socks", "collar"):
        m = masks.get(key_name)
        if m is not None:
            fabric_mask |= m

    if np.any(fabric_mask):
        delta = np.zeros((ATLAS, ATLAS), dtype=np.float32)

        # 1. Torso: Engineered micro-honeycomb / jacquard piqué knit grain (6x6)
        torso_m = np.zeros((ATLAS, ATLAS), dtype=bool)
        for key_name in ("body_front", "body_back"):
            m = masks.get(key_name)
            if m is not None:
                torso_m |= m
        if np.any(torso_m):
            k_torso = np.array([
                [ 3.5, -2.5,  2.0, -3.5,  2.5, -2.0],
                [-2.5,  3.5, -3.5,  2.0, -2.0,  2.5],
                [ 2.0, -3.5,  3.5, -2.5,  2.5, -2.0],
                [-3.5,  2.0, -2.5,  3.5, -2.0,  2.5],
                [ 2.5, -2.0,  2.5, -2.0,  3.5, -3.5],
                [-2.0,  2.5, -2.0,  2.5, -3.5,  3.5],
            ], dtype=np.float32)
            tile_torso = np.tile(k_torso, (ATLAS // 6 + 1, ATLAS // 6 + 1))[:ATLAS, :ATLAS]
            delta[torso_m] = tile_torso[torso_m]

        # 2. Collar & Cuffs: High-density vertical elastic ribbing (2x2)
        collar_m = masks.get("collar")
        if collar_m is not None and np.any(collar_m):
            k_rib = np.array([
                [ 4.5, -4.5],
                [ 4.5, -4.5],
            ], dtype=np.float32)
            tile_rib = np.tile(k_rib, (ATLAS // 2, ATLAS // 2))
            delta[collar_m] = tile_rib[collar_m]

        # 3. Flanks & Underarms: Laser-perforated breathable mesh
        flank_m = np.zeros((ATLAS, ATLAS), dtype=bool)
        bf = masks.get("body_front")
        if bf is not None:
            flank_m[1100:1850, 674:725] = bf[1100:1850, 674:725]
            flank_m[1100:1850, 1323:1374] = bf[1100:1850, 1323:1374]
        if np.any(flank_m):
            y_f, x_f = np.where(flank_m)
            holes = ((y_f % 6 < 2) & (x_f % 6 < 2))
            delta[y_f[holes], x_f[holes]] = -5.0

        # 4. Shorts: Athletic micro-twill weave (4x4 diagonal)
        shorts_m = masks.get("shorts")
        if shorts_m is not None and np.any(shorts_m):
            k_twill = np.array([
                [ 3.0,  1.0, -2.5, -1.0],
                [-1.0,  3.0,  1.0, -2.5],
                [-2.5, -1.0,  3.0,  1.0],
                [ 1.0, -2.5, -1.0,  3.0],
            ], dtype=np.float32)
            tile_twill = np.tile(k_twill, (ATLAS // 4, ATLAS // 4))
            delta[shorts_m] = tile_twill[shorts_m]

        # 5. Socks: Ribbed compression knit (4x2 horizontal ribs)
        socks_m = masks.get("socks")
        if socks_m is not None and np.any(socks_m):
            k_socks = np.array([
                [ 3.5,  3.5],
                [ 3.5,  3.5],
                [-3.5, -3.5],
                [-3.5, -3.5],
            ], dtype=np.float32)
            tile_socks = np.tile(k_socks, (ATLAS // 4, ATLAS // 2))
            delta[socks_m] = tile_socks[socks_m]

        # 6. Sleeves: Fine athletic polyester knit grain (4x4)
        sleeve_m = masks.get("sleeve")
        if sleeve_m is not None and np.any(sleeve_m):
            k_sleeve = np.array([
                [ 2.8, -2.8,  2.0, -2.0],
                [-2.0,  2.8, -2.8,  2.0],
                [ 2.0, -2.0,  2.8, -2.8],
                [-2.8,  2.0, -2.0,  2.8],
            ], dtype=np.float32)
            tile_sleeve = np.tile(k_sleeve, (ATLAS // 4, ATLAS // 4))
            delta[sleeve_m] = tile_sleeve[sleeve_m]
    else:
        delta = np.zeros((ATLAS, ATLAS), dtype=np.float32)

    fabric_idx = np.flatnonzero(fabric_mask)
    delta_flat = delta[fabric_mask][:, None]
    data = (fabric_mask, delta, fabric_idx, delta_flat)
    _FABRIC_CACHE[key] = (masks, data)
    if len(_FABRIC_CACHE) > 4:
        _FABRIC_CACHE.popitem(last=False)
    return data


def _apply_fabric_microtexture(atlas, d, masks):
    """Apply authentic multi-zone micro-knit textile weave and specialty fabric finishes.

    Subtly modulates fabric luminance by +/- 2.5% to +/- 6.0%, producing a rich, tactile,
    matte athletic cloth appearance in 3D replays and close-ups without altering team colors.
    Specialty Finishes (d["fabric_finish"]):
    - standard_microknit: High-density micro-honeycomb / jacquard piqué grain
    - matte_vaporknit: Undulating aerowave engineered breathability channels (Nike Dri-Fit ADV / Adidas HEAT.RDY)
    - embossed_damask: Subtle tonal heraldic crest / fleur-de-lis watermark tessellation
    - heather_melange: Organic cross-hatch marl textile weave simulating performance streetwear
    - geometric_jacquard: 3D optical isometric cube / diamond houndstooth jacquard weave
    - corduroy_rib: Vintage vertical micro-needlecord ribs running continuously
    """
    if not d.get("fabric_texture", True):
        return

    fabric_mask, _delta, fabric_idx, delta_flat = _fabric_texture_data(masks)
    if not len(fabric_idx):
        return

    finish = str(d.get("fabric_finish", "standard_microknit")).lower()

    # Only touch fabric pixels. Precomputed flat indices keep this to a small scoped copy.
    arr = np.array(atlas)                      # uint8 RGBA copy
    rgb_flat = arr.reshape(-1, 4)[:, :3]
    patch = rgb_flat[fabric_idx].astype(np.float32)
    patch += delta_flat

    # Specialty finish modulation across torso (body_front & body_back)
    if finish != "standard_microknit":
        torso_m = np.zeros((ATLAS, ATLAS), dtype=bool)
        for key_name in ("body_front", "body_back"):
            m = masks.get(key_name)
            if m is not None:
                torso_m |= m

        if np.any(torso_m):
            y_coords, x_coords = np.where(torso_m)
            specialty_delta = np.zeros_like(y_coords, dtype=np.float32)

            if finish in ("matte_vaporknit", "aero_knit", "vaporknit"):
                # Engineered horizontal undulating breathability aerowaves with micro-perforations
                waves = 5.5 * np.sin(y_coords / 4.0 + np.cos(x_coords / 12.0))
                perfs = np.where((y_coords % 8 < 2) & (x_coords % 8 < 2), -4.0, 0.0)
                specialty_delta = (waves + perfs).astype(np.float32)

            elif finish in ("embossed_damask", "damask", "watermark"):
                # Regal heraldic fleur-de-lis / diamond crest watermark tessellation (24x24 tile)
                ty = y_coords % 24
                tx = x_coords % 24
                # Diamond border ridge
                is_diag = (np.abs((tx - 12) + (ty - 12)) == 11) | (np.abs((tx - 12) - (ty - 12)) == 11)
                # Center heraldic fleur icon
                is_fleur = ((tx >= 10) & (tx <= 14) & (ty >= 6) & (ty <= 14)) | ((tx >= 7) & (tx <= 17) & (ty == 11))
                specialty_delta = np.where(is_diag | is_fleur, 6.0, -2.5).astype(np.float32)

            elif finish in ("heather_melange", "melange", "heather"):
                # Organic stochastic cross-hatch marl textile weave
                hash_val = (x_coords * 37 + y_coords * 73) % 11
                specialty_delta = np.where(hash_val < 3, 5.0, np.where(hash_val > 7, -5.0, 0.0)).astype(np.float32)

            elif finish in ("geometric_jacquard", "jacquard", "isometric"):
                # 3D isometric diamond cube tessellation (16x16 tile)
                ty = y_coords % 16
                tx = x_coords % 16
                # Top facet (light), left facet (shadow), right facet (neutral)
                top_facet = (ty < 8) & ((tx >= (7 - ty)) & (tx <= (8 + ty)))
                left_facet = (ty >= 8) & (tx < 8)
                specialty_delta = np.where(top_facet, 5.5, np.where(left_facet, -4.5, 0.5)).astype(np.float32)

            elif finish in ("corduroy_rib", "ribbed_fabric", "needle_cord"):
                # High-density vertical micro-needlecord ribs
                specialty_delta = np.where((x_coords % 6) < 3, 5.0, -5.0).astype(np.float32)

            # Map torso coordinates into the flattened fabric patch
            torso_flat_indices = np.ravel_multi_index((y_coords, x_coords), (ATLAS, ATLAS))
            locs = np.searchsorted(fabric_idx, torso_flat_indices)
            patch[locs] += specialty_delta[:, None]

    np.clip(patch, 0, 255, out=patch)
    rgb_flat[fabric_idx] = patch.astype(np.uint8)
    atlas.paste(Image.fromarray(arr), (0, 0))


def _draw_flatlock_seam(draw, pts, dark_stitch, light_stitch, stitch_len=4, gap_len=1):
    """Draw authentic twin-needle flatlock chain stitching with thread loops and needle micro-holes."""
    draw.line(pts, fill=dark_stitch, width=1)
    if len(pts) == 2 and pts[0][0] == pts[1][0]:
        x = pts[0][0]
        y0, y1 = min(pts[0][1], pts[1][1]), max(pts[0][1], pts[1][1])
        cycle = max(2, stitch_len + gap_len)
        for y in range(y0, y1, cycle):
            draw.line([(x, y), (x, min(y + stitch_len - 1, y1))], fill=light_stitch, width=1)
            draw.line([(x + 1, y), (x + 1, min(y + stitch_len - 1, y1))], fill=light_stitch, width=1)
    elif len(pts) == 2 and pts[0][1] == pts[1][1]:
        y = pts[0][1]
        x0, x1 = min(pts[0][0], pts[1][0]), max(pts[0][0], pts[1][0])
        cycle = max(2, stitch_len + gap_len)
        for x in range(x0, x1, cycle):
            draw.line([(x, y), (min(x + stitch_len - 1, x1), y)], fill=light_stitch, width=1)
            draw.line([(x, y + 1), (min(x + stitch_len - 1, x1), y + 1)], fill=light_stitch, width=1)
    else:
        draw.line(pts, fill=light_stitch, width=1)


def _apply_construction_seams(atlas, d, masks):
    """Render athletic panel construction lines, raglan seams, and twin-needle hem stitching."""
    if not d.get("construction_seams", True):
        return

    body = tuple(d["body"])
    dark_stitch = (max(0, int(body[0] * 0.74)), max(0, int(body[1] * 0.74)), max(0, int(body[2] * 0.74)), 180)
    light_stitch = (min(255, int(body[0] * 1.15) + 15), min(255, int(body[1] * 1.15) + 15), min(255, int(body[2] * 1.15) + 15), 130)

    seam_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(seam_layer)

    bf = masks.get("body_front")
    bb = masks.get("body_back")
    sleeve_m = masks.get("sleeve")
    shorts_m = masks.get("shorts")

    # 1. Torso flank side seams (front: y: 1180..1845, back: y: 280..900)
    for sx in (724, 1324):
        _draw_flatlock_seam(draw, [(sx, 1180), (sx, 1845)], dark_stitch, light_stitch)
        _draw_flatlock_seam(draw, [(sx, 280), (sx, 900)], dark_stitch, light_stitch)

    # 2. Raglan shoulder/armhole seams
    _draw_flatlock_seam(draw, [(870, 1020), (724, 1180)], dark_stitch, light_stitch)
    _draw_flatlock_seam(draw, [(1178, 1020), (1324, 1180)], dark_stitch, light_stitch)

    _draw_flatlock_seam(draw, [(870, 120), (724, 280)], dark_stitch, light_stitch)
    _draw_flatlock_seam(draw, [(1178, 120), (1324, 280)], dark_stitch, light_stitch)

    # 3. Twin-needle lower hem stitching
    _draw_flatlock_seam(draw, [(724, 1838), (1324, 1838)], dark_stitch, light_stitch)
    _draw_flatlock_seam(draw, [(724, 1844), (1324, 1844)], dark_stitch, light_stitch)
    _draw_flatlock_seam(draw, [(724, 896), (1324, 896)], dark_stitch, light_stitch)
    _draw_flatlock_seam(draw, [(724, 902), (1324, 902)], dark_stitch, light_stitch)

    # 4. Sleeve cuff twin-needle hem stitching
    if sleeve_m is not None:
        _draw_flatlock_seam(draw, [(40, 658), (640, 658)], dark_stitch, light_stitch)
        _draw_flatlock_seam(draw, [(40, 663), (640, 663)], dark_stitch, light_stitch)
        _draw_flatlock_seam(draw, [(1400, 658), (2000, 658)], dark_stitch, light_stitch)
        _draw_flatlock_seam(draw, [(1400, 663), (2000, 663)], dark_stitch, light_stitch)

    # 5. Shorts bottom leg hem stitching
    if shorts_m is not None:
        _draw_flatlock_seam(draw, [(45, 1932), (590, 1932)], dark_stitch, light_stitch)
        _draw_flatlock_seam(draw, [(45, 1938), (590, 1938)], dark_stitch, light_stitch)
        _draw_flatlock_seam(draw, [(1455, 1932), (2000, 1932)], dark_stitch, light_stitch)
        _draw_flatlock_seam(draw, [(1455, 1938), (2000, 1938)], dark_stitch, light_stitch)

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
        draw.text((994, 98), "AUTHENTIC MATCH", fill=label_col, font=font)
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
    elif finish in ("blackout", "blackout_stealth"):
        d["body"] = (18, 20, 24)
        d["sleeve"] = (18, 20, 24)
        d["shorts"] = (18, 20, 24)
        d["socks"] = (18, 20, 24)
        d["second"] = (38, 42, 48)
        d["accent"] = (55, 60, 68)
        d["stripe_accent"] = (55, 60, 68)
        d["shorts_accent"] = (38, 42, 48)
        d["socks_accent"] = (38, 42, 48)
    elif finish in ("whiteout", "pure_whiteout"):
        d["body"] = (250, 250, 252)
        d["sleeve"] = (250, 250, 252)
        d["shorts"] = (250, 250, 252)
        d["socks"] = (250, 250, 252)
        d["second"] = (228, 230, 235)
        d["accent"] = (210, 214, 220)
        d["stripe_accent"] = (210, 214, 220)
        d["shorts_accent"] = (228, 230, 235)
        d["socks_accent"] = (228, 230, 235)
    elif finish in ("iridescent_neon", "neon_aurora"):
        d["accent"] = (0, 240, 255)
        d["stripe_accent"] = (255, 30, 140)
        d["third"] = (215, 255, 30)
    elif finish in ("pastel_streetwear", "pastel_couture"):
        d["accent"] = (218, 212, 230)
        d["stripe_accent"] = (226, 175, 160)
        d["third"] = (205, 226, 232)
    elif finish in ("retro_throwback", "vintage_archive"):
        d["second"] = (244, 240, 228)
        d["stripe_accent"] = (244, 240, 228)

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

    # 3. Sleeve architecture (grunge_yoke, brand_track_tape, seam_piping)
    _apply_sleeve_architecture(atlas, d, masks)

    # 4. Contrast sleeve cuff bands + engineered tipping line (dual short & long sleeve anchoring)
    _apply_engineered_cuffs(atlas, d, masks)

    # 5. Tailored collar architecture (crew, retro_crew, v_neck, crossover_v, polo, polo_v_notch, mandarin_button, dual_tipped)
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
        sample_arr = np.array(atlas)[1250:1370, 880:1168, :3]
        sample_lums = 0.2126 * sample_arr[:, :, 0] + 0.7152 * sample_arr[:, :, 1] + 0.0722 * sample_arr[:, :, 2]
        bg_lum = float(np.mean(sample_lums))
        bg_std = float(np.std(sample_lums))

        p_obj = Path(d["sponsor"])
        base_stem = p_obj.stem
        if base_stem.endswith("_white"):
            base_stem = base_stem[:-6]
        elif base_stem.endswith("_dark"):
            base_stem = base_stem[:-5]

        # Determine if we should use Light Mode or Dark Mode logo based on background luminance
        if not d.get("sponsor_plate"):
            if bg_lum < 130:
                # Dark shirt fabric -> use Light Mode (_white.png)
                d["sponsor_white"] = True
                d.pop("sponsor_dark", None)
                cand_w = p_obj.parent / f"{base_stem}_white.png"
                if cand_w.is_file():
                    d["sponsor"] = str(cand_w)
            else:
                # Light shirt fabric -> prefer authentic full-color logo if available, otherwise Dark Mode (_dark.png)
                d["sponsor_white"] = False
                cand_c = p_obj.parent / f"{base_stem}.png"
                cand_d = p_obj.parent / f"{base_stem}_dark.png"
                if cand_c.is_file() and not d.get("sponsor_dark"):
                    d["sponsor"] = str(cand_c)
                    d.pop("sponsor_dark", None)
                elif cand_d.is_file():
                    d["sponsor"] = str(cand_d)
                    d.pop("sponsor_dark", None)
                else:
                    d["sponsor_dark"] = (18, 22, 28)

        # Contrast stroke handling for striped / multi-tone patterned shirts:
        # If standard deviation of background luminance is high (e.g. black and white vertical stripes like Newcastle),
        # letters will blend into matching stripes without a keyline stroke.
        stroke_col = None
        stroke_px = 0
        if bg_std >= 32.0 and not d.get("sponsor_plate"):
            if d.get("sponsor_white") or Path(d["sponsor"]).stem.endswith("_white"):
                stroke_col = (18, 22, 28)  # Razor-sharp deep dark contrast stroke
                stroke_px = 3
            else:
                stroke_col = (255, 255, 255)  # Crisp white contrast stroke for dark logos
                stroke_px = 3

        sp_item = _prepare_stamp_item(d["sponsor"], *kit_regions.CHEST_SPONSOR,
                                      white=d.get("sponsor_white"),
                                      dark=d.get("sponsor_dark"),
                                      plate=body if d.get("sponsor_plate") else None,
                                      max_w=340, max_h=140,
                                      stroke_color=stroke_col, stroke_px=stroke_px)
    bg_item = None
    if d.get("badge"):
        b_col, b_white = _resolve_badge_color(d["badge"], d["body"], d)
        bg_item = _prepare_stamp_item(d["badge"], *kit_regions.CLUB_BADGE,
                                      white=b_white,
                                      dark=b_col,
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

        if key == "sponsor":
            # Clean flat composite for sponsor logo - no artificial drop shadows, halos, or relief effects
            atlas.alpha_composite(img, (x, y))
        elif d.get("heat_press_relief", True):
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


def _prepare_stamp_item(logo_path, cx, cy, area, white=False, dark=None, plate=None, max_w=None, max_h=None, defringe=True, stroke_color=None, stroke_px=0):
    """Load, defringe, tint and measure a logo before validation and placement."""
    if not logo_path or not Path(logo_path).is_file():
        return None
    logo = Image.open(logo_path).convert("RGBA")
    # Clean any low-alpha background noise/halo (< 35 alpha) across the canvas
    l_arr = np.array(logo)
    if np.any((l_arr[:, :, 3] > 0) & (l_arr[:, :, 3] < 35)):
        l_arr[l_arr[:, :, 3] < 35] = 0
        logo = Image.fromarray(l_arr)
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

    # Razor-sharp contrast keyline stroke for patterned / striped fabrics
    if stroke_px and stroke_px > 0 and stroke_color is not None:
        from PIL import ImageFilter
        radius = int(stroke_px)
        alpha_channel = logo.split()[3]
        stroke_alpha = alpha_channel.filter(ImageFilter.MaxFilter(radius * 2 + 1))
        sc = tuple(stroke_color[:3])
        stroke_layer = Image.new("RGBA", logo.size, sc + (0,))
        stroke_layer.putalpha(stroke_alpha)
        stroke_layer.alpha_composite(logo, (0, 0))
        logo = stroke_layer

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
    return Image.fromarray(a)


def _flatten_color(logo, color):
    """Return a monochrome silhouette in the specified RGB color keeping the logo's alpha."""
    import numpy as np
    a = np.asarray(logo).copy()
    a[:, :, 0] = color[0]
    a[:, :, 1] = color[1]
    a[:, :, 2] = color[2]
    return Image.fromarray(a)


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
    elif finish in ("blackout", "blackout_stealth"):
        bg_col = (12, 14, 16, 245)
        border_col = (45, 48, 55, 255)
        holo_col = (65, 70, 80, 220)
        text_col = (55, 60, 70, 240)
    elif finish in ("cyber_neon", "iridescent_neon", "neon_aurora"):
        bg_col = (10, 14, 26, 245)
        border_col = (0, 240, 255, 255)
        holo_col = (255, 30, 140, 220)
        text_col = (0, 240, 255, 240)
    elif finish in ("pastel_streetwear", "pastel_couture"):
        bg_col = (30, 28, 36, 245)
        border_col = (226, 175, 160, 255)
        holo_col = (218, 212, 230, 220)
        text_col = (226, 175, 160, 240)
    elif finish in ("retro_throwback", "vintage_archive"):
        bg_col = (40, 36, 28, 245)
        border_col = (214, 195, 150, 255)
        holo_col = (244, 240, 228, 220)
        text_col = (214, 195, 150, 240)
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
    """Render authentic club crest and supplier mark on shorts, dynamically opposing ShortsNumberSide."""
    shorts_mask = masks.get("shorts")
    if shorts_mask is None:
        return

    # Check which leg the squad number appears on (0=Left leg, 1=Right leg)
    num_side = int(d.get("shorts_number_side", 0))
    if num_side == 1:
        # Number is on right leg -> Place badge on LEFT leg, supplier on RIGHT leg
        badge_anchor = getattr(kit_regions, "SHORTS_BADGE_LEFT", (1898, 1620, 5000))
        sup_anchor = getattr(kit_regions, "SHORTS_SUPPLIER_RIGHT", (150, 1620, 3200))
    else:
        # Number is on left leg (default) -> Place badge on RIGHT leg, supplier on LEFT leg
        badge_anchor = getattr(kit_regions, "SHORTS_BADGE_RIGHT", (150, 1620, 5000))
        sup_anchor = getattr(kit_regions, "SHORTS_SUPPLIER_LEFT", (1898, 1620, 3200))

    # 1. Shorts Club Badge
    if d.get("shorts_badge", True) and d.get("badge"):
        shorts_c = d.get("shorts") or d["body"]
        b_col, b_white = _resolve_badge_color(d["badge"], shorts_c, d)
        bg_item = _prepare_stamp_item(
            d["badge"], *badge_anchor,
            white=b_white,
            dark=b_col,
            max_w=95, max_h=95, defringe=False
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

    # 2. Shorts Supplier Logo
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
            d["supplier"], *sup_anchor,
            white=sup_white if not sup_col or sup_col == (245, 245, 245) else False,
            dark=sup_col if not sup_white else None,
            max_w=85, max_h=55, defringe=True
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
    """Anchor secondary sponsor logo on player's visible sleeve bicep (Left arm = Right UV island, Right arm = Left UV island)."""
    sleeve_sp = d.get("sleeve_sponsor")
    if not sleeve_sp:
        return

    # Resolve logo file path
    p = Path(sleeve_sp)
    if not p.is_file():
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

    # In PES 2021 UV atlas:
    # Player's LEFT arm (Right UV island):
    #   - Short sleeve bicep (active in-game on short sleeve shirts): (cx = 1485, cy = 935), rotated 90 deg CCW
    #   - Long sleeve forearm (active in-game on long sleeve shirts): (cx = 1507, cy = 403), rotated 90 deg CCW
    # Player's RIGHT arm (Left UV island):
    #   - Short sleeve bicep: (cx = 563, cy = 935), rotated 90 deg CW (-90)
    #   - Long sleeve forearm: (cx = 541, cy = 403), rotated 90 deg CW (-90)
    # Stamping on BOTH short sleeve and long sleeve islands guarantees the sponsor
    # is visible whether the player wears short sleeves (summer/standard) or long sleeves (winter/rain).
    side_mode = d.get("sleeve_sponsor_side", "left")
    anchors = []
    if side_mode in ("both", "left"):
        anchors.append((1485, 935, 90.0))    # Player's Left arm SHORT sleeve
        anchors.append((1507, 403, 90.0))    # Player's Left arm LONG sleeve
    if side_mode in ("both", "right"):
        anchors.append((563, 935, -90.0))    # Player's Right arm SHORT sleeve
        anchors.append((541, 403, -90.0))    # Player's Right arm LONG sleeve

    for cx, cy, wrap_angle in anchors:
        # Sample canvas background under sleeve sponsor region to guarantee WCAG high contrast
        sample_arr = np.array(atlas)[max(0, cy - 60):min(ATLAS, cy + 60), max(0, cx - 60):min(ATLAS, cx + 60), :3]
        if sample_arr.size > 0:
            sample_lums = 0.2126 * sample_arr[:, :, 0] + 0.7152 * sample_arr[:, :, 1] + 0.0722 * sample_arr[:, :, 2]
            bg_lum = float(np.mean(sample_lums))
            bg_std = float(np.std(sample_lums))
        else:
            bg_lum = 128.0
            bg_std = 0.0

        logo_path = p
        base_stem = logo_path.stem
        if base_stem.endswith("_white"):
            base_stem = base_stem[:-6]
        elif base_stem.endswith("_dark"):
            base_stem = base_stem[:-5]

        is_white_variant = False
        if bg_lum < 130 or d.get("sleeve_sponsor_white"):
            # Dark sleeve fabric: pick white variant
            cand_w = logo_path.parent / f"{base_stem}_white.png"
            if cand_w.is_file():
                logo_path = cand_w
            is_white_variant = True
        else:
            # Light sleeve fabric: pick dark variant or color
            cand_d = logo_path.parent / f"{base_stem}_dark.png"
            if cand_d.is_file():
                logo_path = cand_d
            else:
                cand_c = logo_path.parent / f"{base_stem}.png"
                if cand_c.is_file():
                    logo_path = cand_c

        raw_img = Image.open(logo_path).convert("RGBA")
        rw, rh = raw_img.size
        aspect = rw / float(max(1, rh))

        # Size logo in unrotated horizontal space before applying sleeve orientation:
        # Square / round crests (e.g. HP, Angry Birds): 138x138
        # Wide wordmarks (e.g. BingX, Visit Rwanda, OKX, Deel, Expedia): ~230x75
        if 0.75 <= aspect <= 1.33:
            target_w, target_h = 138, 138
        elif aspect > 1.33:
            target_w = 230
            target_h = max(35, min(80, int(target_w / aspect)))
        else:
            target_h = 138
            target_w = max(35, int(target_h * aspect))

        raw_scaled = raw_img.resize((target_w, target_h), Image.LANCZOS)

        # Apply keyline contrast stroke if striped / multi-tone sleeve pattern
        if bg_std >= 32.0:
            from PIL import ImageFilter
            radius = 3
            alpha_ch = raw_scaled.split()[3]
            stroke_alpha = alpha_ch.filter(ImageFilter.MaxFilter(radius * 2 + 1))
            sc = (18, 22, 28) if is_white_variant else (255, 255, 255)
            stroke_layer = Image.new("RGBA", raw_scaled.size, sc + (0,))
            stroke_layer.putalpha(stroke_alpha)
            stroke_layer.alpha_composite(raw_scaled, (0, 0))
            raw_scaled = stroke_layer

        # Rotate along sleeve wrap orientation:
        rot_img = raw_scaled.rotate(wrap_angle, resample=Image.BICUBIC, expand=True)
        fw, fh = rot_img.size

        rx = int(cx - fw / 2)
        ry = int(cy - fh / 2)

        # Clean flat composite for sleeve sponsor - no artificial drop shadows or relief effects
        atlas.alpha_composite(rot_img, (rx, ry))


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

        cand_white = Path(logo_dir) / f"{brand}_white.png"
        cand_dark = Path(logo_dir) / f"{brand}_dark.png"
        cand_std = Path(logo_dir) / f"{brand}.png"

        if white:
            if cand_white.is_file():
                cand_logo = cand_white
            elif cand_std.is_file():
                cand_logo = cand_std
            else:
                cand_logo = cand_white
        else:
            if cand_dark.is_file():
                cand_logo = cand_dark
            elif cand_std.is_file():
                cand_logo = cand_std
            else:
                cand_logo = cand_dark
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
                            if cand_white.is_file():
                                design["sponsor"] = str(cand_white)
                        else:
                            if cand_dark.is_file():
                                design["sponsor"] = str(cand_dark)
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

    # Shorts squad number placement detection (0=Left leg, 1=Right leg)
    cid = club.get("id") or club.get("team_id")
    if "shorts_number_side" in club:
        design["shorts_number_side"] = int(club["shorts_number_side"])
    elif cid is not None:
        try:
            import club_resolver
            slot_str = f"p{slot}" if isinstance(slot, int) else str(slot)
            design["shorts_number_side"] = club_resolver.get_shorts_number_side(cid, slot=slot_str)
        except Exception:
            design["shorts_number_side"] = 0
    else:
        design["shorts_number_side"] = 0

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
                   sleeve_sponsor=None, previews=True):
    """Render the full outfield and goalkeeper kit set for a club + season.

    Returns a list of (slot, atlas_png_or_image, preview_png, design).  With
    `previews=False` the atlas is returned as a live PIL image and the preview
    and mockup PNGs are skipped; the FTEX bytes are unchanged.
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
        if previews:
            atlas = outdir / f"u{team:04d}{slot_code}_atlas.png"
            atlas_path = str(atlas)
        else:
            atlas = None
            atlas_path = None

        atlas_img, design = render_club(
            club, season, atlas_path, logo_dir, masks=masks,
            brand_files=brand_files, slot=slot, sponsor=sponsor,
            badge_dir=badge_dir, badge=badge, sleeve_sponsor=sleeve_sponsor)

        if previews:
            preview = uv_contact_sheet(atlas, outdir / f"u{team:04d}{slot_code}_preview.png",
                                       masks=masks)
            mockup(design, club["name"], season,
                   outdir / f"u{team:04d}{slot_code}_mockup.png")
            atlas_ref = str(atlas)
            preview_ref = str(preview)
        else:
            atlas_ref = atlas_img
            preview_ref = None
        out.append((slot, atlas_ref, preview_ref, design))
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
        style_cuff = design.get("cuff_style", "solid")
        cuff_col = tuple(cuff) + (255,)
        cuff_tip = design.get("cuff_tip") or design.get("accent") or cuff
        tip_col = tuple(cuff_tip) + (255,)

        if style_cuff in ("solid", "wide_band", "dual_stripe", "dual_tipped"):
            band_top = 265 if style_cuff == "wide_band" else 273
            cm = np.zeros_like(sm)
            cm[band_top:283, :] = sm[band_top:283, :]
            if np.any(cm):
                canvas.paste(Image.new("RGBA", (W, H), cuff_col), (0, 0), Image.fromarray((cm * 255).astype("uint8"), "L"))
            if style_cuff in ("dual_stripe", "dual_tipped"):
                stripe_m = np.zeros_like(sm)
                stripe_m[band_top + 2:band_top + 4, :] = sm[band_top + 2:band_top + 4, :]
                stripe_m[band_top + 6:band_top + 8, :] = sm[band_top + 6:band_top + 8, :]
                if np.any(stripe_m):
                    canvas.paste(Image.new("RGBA", (W, H), tip_col), (0, 0), Image.fromarray((stripe_m * 255).astype("uint8"), "L"))
            elif cuff_tip and cuff_tip != cuff:
                tip_m = np.zeros_like(sm)
                tip_m[280:283, :] = sm[280:283, :]
                if np.any(tip_m):
                    canvas.paste(Image.new("RGBA", (W, H), tip_col), (0, 0), Image.fromarray((tip_m * 255).astype("uint8"), "L"))
        elif style_cuff == "micro_tipped":
            tip_m = np.zeros_like(sm)
            tip_m[279:283, :] = sm[279:283, :]
            if np.any(tip_m):
                canvas.paste(Image.new("RGBA", (W, H), tip_col), (0, 0), Image.fromarray((tip_m * 255).astype("uint8"), "L"))
        elif style_cuff == "jacquard_knit":
            cm = np.zeros_like(sm)
            cm[271:283, :] = sm[271:283, :]
            if np.any(cm):
                canvas.paste(Image.new("RGBA", (W, H), cuff_col), (0, 0), Image.fromarray((cm * 255).astype("uint8"), "L"))
            y_s, x_s = np.where(cm)
            checks = ((x_s // 3) + (y_s // 3)) % 2 == 0
            if np.any(checks):
                chk_m = np.zeros_like(sm)
                chk_m[y_s[checks], x_s[checks]] = True
                canvas.paste(Image.new("RGBA", (W, H), tip_col), (0, 0), Image.fromarray((chk_m * 255).astype("uint8"), "L"))
        elif style_cuff == "striped_rib":
            band_top = 268
            cm = np.zeros_like(sm)
            cm[band_top:283, :] = sm[band_top:283, :]
            if np.any(cm):
                canvas.paste(Image.new("RGBA", (W, H), cuff_col), (0, 0), Image.fromarray((cm * 255).astype("uint8"), "L"))
            s1 = np.zeros_like(sm)
            s2 = np.zeros_like(sm)
            s3 = np.zeros_like(sm)
            s1[band_top + 2:band_top + 4, :] = sm[band_top + 2:band_top + 4, :]
            s2[band_top + 6:band_top + 8, :] = sm[band_top + 6:band_top + 8, :]
            s3[band_top + 10:band_top + 12, :] = sm[band_top + 10:band_top + 12, :]
            tip2_c = tuple(design.get("third") or design.get("second") or cuff_tip) + (255,)
            if np.any(s1):
                canvas.paste(Image.new("RGBA", (W, H), tip_col), (0, 0), Image.fromarray((s1 * 255).astype("uint8"), "L"))
            if np.any(s2):
                canvas.paste(Image.new("RGBA", (W, H), tip2_c), (0, 0), Image.fromarray((s2 * 255).astype("uint8"), "L"))
            if np.any(s3):
                canvas.paste(Image.new("RGBA", (W, H), tip_col), (0, 0), Image.fromarray((s3 * 255).astype("uint8"), "L"))
        elif style_cuff == "tri_color_knit":
            band_top = 265
            cm = np.zeros_like(sm)
            cm[band_top:283, :] = sm[band_top:283, :]
            s1 = np.zeros_like(sm)
            s2 = np.zeros_like(sm)
            s3 = np.zeros_like(sm)
            s1[band_top:band_top + 6, :] = sm[band_top:band_top + 6, :]
            s2[band_top + 6:band_top + 12, :] = sm[band_top + 6:band_top + 12, :]
            s3[band_top + 12:283, :] = sm[band_top + 12:283, :]
            tip2_c = tuple(design.get("third") or design.get("second") or cuff_tip) + (255,)
            if np.any(s1):
                canvas.paste(Image.new("RGBA", (W, H), cuff_col), (0, 0), Image.fromarray((s1 * 255).astype("uint8"), "L"))
            if np.any(s2):
                canvas.paste(Image.new("RGBA", (W, H), tip_col), (0, 0), Image.fromarray((s2 * 255).astype("uint8"), "L"))
            if np.any(s3):
                canvas.paste(Image.new("RGBA", (W, H), tip2_c), (0, 0), Image.fromarray((s3 * 255).astype("uint8"), "L"))
        elif style_cuff == "contrast_split":
            band_top = 270
            cm = np.zeros_like(sm)
            cm[band_top:283, :] = sm[band_top:283, :]
            s_left = np.zeros_like(sm)
            s_right = np.zeros_like(sm)
            s_left[:, :240] = cm[:, :240]
            s_right[:, 240:] = cm[:, 240:]
            if np.any(s_left):
                canvas.paste(Image.new("RGBA", (W, H), cuff_col), (0, 0), Image.fromarray((s_left * 255).astype("uint8"), "L"))
            if np.any(s_right):
                canvas.paste(Image.new("RGBA", (W, H), tip_col), (0, 0), Image.fromarray((s_right * 255).astype("uint8"), "L"))
        elif style_cuff == "french_turnback":
            band_top = 268
            cm = np.zeros_like(sm)
            cm[band_top:283, :] = sm[band_top:283, :]
            ridge_m = np.zeros_like(sm)
            ridge_m[band_top:band_top + 3, :] = sm[band_top:band_top + 3, :]
            if np.any(cm):
                canvas.paste(Image.new("RGBA", (W, H), cuff_col), (0, 0), Image.fromarray((cm * 255).astype("uint8"), "L"))
            if np.any(ridge_m):
                canvas.paste(Image.new("RGBA", (W, H), tip_col), (0, 0), Image.fromarray((ridge_m * 255).astype("uint8"), "L"))

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
        for offset in (-5, 0, 5):
            d.line([(200 + offset, 46 - abs(offset) // 2), (120 + offset, 88 - abs(offset) // 2)], fill=str_col, width=3)
            d.line([(280 - offset, 46 - abs(offset) // 2), (360 - offset, 88 - abs(offset) // 2)], fill=str_col, width=3)
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

    # Distinctive sleeve architecture & shoulder styling on 2D mockup
    s_arch = design.get("sleeve_style", "solid")
    if s_arch in ("grunge_yoke", "brush_splatter"):
        import numpy as np
        rng_mock = np.random.default_rng(design.get("team_id", 126) * 101 + int(season))
        yoke_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d_yoke = ImageDraw.Draw(yoke_layer)
        for _ in range(45):
            x = int(rng_mock.integers(140, 340))
            y = int(rng_mock.integers(40, 130))
            w_b = int(rng_mock.integers(4, 14))
            h_b = int(rng_mock.integers(10, 35))
            d_yoke.polygon([(x, y), (x + w_b, y + 2), (x + w_b // 2, y + h_b), (x - 2, y + h_b - 4)], fill=str_col)
        for _ in range(35):
            x_l = int(rng_mock.integers(40, 130))
            y_l = int(rng_mock.integers(50, 140))
            d_yoke.polygon([(x_l, y_l), (x_l + 8, y_l + 2), (x_l + 4, y_l + 18), (x_l - 2, y_l + 14)], fill=str_col)
            x_r = int(rng_mock.integers(350, 440))
            y_r = int(rng_mock.integers(50, 140))
            d_yoke.polygon([(x_r, y_r), (x_r + 8, y_r + 2), (x_r + 4, y_r + 18), (x_r - 2, y_r + 14)], fill=str_col)
        total_m = np.asarray(bmask) | np.asarray(smask)
        canvas.paste(yoke_layer, (0, 0), Image.fromarray(total_m))

    elif s_arch in ("brand_track_tape", "track_tape"):
        d.line([(135, 42), (72, 130), (28, 250)], fill=str_col, width=8)
        d.line([(345, 42), (408, 130), (452, 250)], fill=str_col, width=8)
        bg_col = tuple(design.get("sleeve") or body) + (255,)
        for t in (0.2, 0.4, 0.6, 0.8):
            lx = int(72 + (28 - 72) * (t - 0.5) * 2) if t > 0.5 else int(135 + (72 - 135) * t * 2)
            ly = int(130 + (250 - 130) * (t - 0.5) * 2) if t > 0.5 else int(42 + (130 - 42) * t * 2)
            d.polygon([(lx, ly - 3), (lx + 3, ly), (lx, ly + 3), (lx - 3, ly)], fill=bg_col)
            rx = int(408 + (452 - 408) * (t - 0.5) * 2) if t > 0.5 else int(345 + (408 - 345) * t * 2)
            ry = int(130 + (250 - 130) * (t - 0.5) * 2) if t > 0.5 else int(42 + (130 - 42) * t * 2)
            d.polygon([(rx, ry - 3), (rx + 3, ry), (rx, ry + 3), (rx - 3, ry)], fill=bg_col)

    elif s_arch in ("seam_piping", "piping"):
        d.line([(200, 40), (108, 150)], fill=str_col, width=3)
        d.line([(280, 40), (372, 150)], fill=str_col, width=3)

    elif s_arch in ("raglan_piping", "contrast_raglan_piped"):
        tip2_c = tuple(design.get("third") or design.get("accent") or acc_cand) + (255,)
        d.line([(200, 40), (108, 150)], fill=str_col, width=5)
        d.line([(200, 40), (108, 150)], fill=tip2_c, width=2)
        d.line([(280, 40), (372, 150)], fill=str_col, width=5)
        d.line([(280, 40), (372, 150)], fill=tip2_c, width=2)
        # Shoulder ridge stripes
        d.line([(195, 42), (120, 84)], fill=tip2_c, width=2)
        d.line([(285, 42), (360, 84)], fill=tip2_c, width=2)

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

    # Fill torso fabric behind high and square neckline collars
    if c_style in ("crew", "retro_crew", "dual_tipped", "grandad_collar", "square_neck", "wrap_v_neck", "contrast_split_collar", "mock_turtleneck_micro"):
        d.polygon([(192, 40), (288, 40), (240, 86)], fill=body + (255,))

    if c_style == "polo":
        # Folded wings contour
        d.polygon([(194, 40), (216, 68), (236, 52), (244, 52), (264, 68), (286, 40), (272, 38), (240, 44), (208, 38)],
                  fill=trim + (255,), outline=tip_col)
        # Button placket down chest
        d.rectangle([236, 50, 244, 94], fill=trim + (255,), outline=tip_col, width=1)
        btn_c = (245, 245, 248, 255) if _col_lum(trim) < 160 else (25, 25, 30, 255)
        d.ellipse([238, 62, 242, 66], fill=btn_c)
        d.ellipse([238, 80, 242, 84], fill=btn_c)
    elif c_style == "polo_v_notch":
        # Luxury tailored open-notch polo (Venezia style)
        d.polygon([(192, 40), (214, 68), (234, 52), (246, 52), (266, 68), (288, 40), (272, 38), (240, 44), (208, 38)],
                  fill=trim + (255,), outline=tip_col)
        # Open V-notch recess
        d.polygon([(234, 50), (246, 50), (240, 78)], fill=(15, 16, 18, 255))
        d.line([(234, 50), (240, 78), (246, 50)], fill=tip_col, width=2)
    elif c_style == "retro_crew":
        # Thick 12px ribbed crew neck
        d.arc([196, 22, 284, 82], 15, 165, fill=trim + (255,), width=12)
        if collar_tip and collar_tip != trim:
            d.arc([196, 22, 284, 82], 15, 165, fill=tuple(collar_tip) + (255,), width=2)
    elif c_style == "crossover_v":
        # Overlapping crossover asymmetric V-neck (BVB purple volt style)
        d.polygon([(198, 40), (242, 88), (252, 84), (212, 40)], fill=tip_col)
        d.polygon([(282, 40), (236, 88), (226, 84), (268, 40)], fill=trim + (255,))
        d.line([(282, 40), (236, 88)], fill=tip_col, width=2)
    elif c_style == "mandarin_button":
        # Short standing collar with single button
        d.arc([198, 30, 282, 74], 25, 155, fill=trim + (255,), width=8)
        d.rectangle([237, 54, 243, 68], fill=trim + (255,))
        btn_c = (245, 245, 248, 255) if _col_lum(trim) < 160 else (25, 25, 30, 255)
        d.ellipse([238, 58, 242, 62], fill=btn_c)
    elif c_style == "striped_rib_polo":
        # Spread polo wings with 3 athletic micro-stripes and inset ribbed triangular gusset (Napoli EA7 style)
        d.polygon([(192, 40), (214, 68), (234, 52), (246, 52), (266, 68), (288, 40), (272, 38), (240, 44), (208, 38)],
                  fill=trim + (255,), outline=tip_col)
        tip2_c = tuple(design.get("third") or design.get("second") or trim) + (255,)
        d.line([(194, 43), (212, 65)], fill=tip_col, width=1)
        d.line([(196, 45), (210, 63)], fill=tip2_c, width=1)
        d.line([(286, 43), (268, 65)], fill=tip_col, width=1)
        d.line([(284, 45), (270, 63)], fill=tip2_c, width=1)
        # Inset triangular ribbed gusset
        d.polygon([(234, 52), (246, 52), (240, 78)], fill=trim + (255,))
        for rx in (236, 238, 240, 242, 244):
            d.line([(rx, 53), (rx, max(54, 74 - abs(rx - 240) * 3))], fill=tip_col, width=1)
        d.line([(234, 52), (240, 78), (246, 52)], fill=tip_col, width=2)
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
    elif c_style == "wrap_v_neck":
        d.polygon([(194, 38), (246, 88), (254, 84), (210, 38)], fill=trim + (255,))
        d.line([(194, 38), (246, 88)], fill=tip_col, width=2)
        d.polygon([(286, 38), (234, 82), (226, 78), (270, 38)], fill=trim + (255,))
        d.line([(286, 38), (234, 82)], fill=tip_col, width=2)
    elif c_style == "grandad_collar":
        d.arc([198, 30, 282, 74], 25, 155, fill=trim + (255,), width=8)
        d.rectangle([236, 52, 244, 86], fill=trim + (255,), outline=tip_col, width=1)
        btn_c = (245, 245, 248, 255) if _col_lum(trim) < 160 else (25, 25, 30, 255)
        d.ellipse([238, 60, 242, 64], fill=btn_c)
        d.ellipse([238, 74, 242, 78], fill=btn_c)
    elif c_style == "square_neck":
        d.polygon([(206, 40), (274, 40), (266, 70), (214, 70)], fill=trim + (255,), outline=tip_col, width=2)
        d.line([(214, 70), (218, 64)], fill=tip_col, width=2)
        d.line([(266, 70), (262, 64)], fill=tip_col, width=2)
    elif c_style == "contrast_split_collar":
        d.arc([198, 26, 282, 78], 90, 165, fill=trim + (255,), width=8)
        d.arc([198, 26, 282, 78], 15, 90, fill=tip_col, width=8)
        d.line([(240, 52), (240, 78)], fill=tip_col, width=2)
    elif c_style == "laced_placket":
        d.polygon([(194, 40), (216, 68), (236, 52), (244, 52), (264, 68), (286, 40), (272, 38), (240, 44), (208, 38)],
                  fill=trim + (255,), outline=tip_col)
        d.polygon([(234, 50), (246, 50), (240, 86)], fill=(20, 20, 25, 255))
        d.line([(235, 56), (245, 68)], fill=(245, 245, 245, 255), width=1)
        d.line([(245, 56), (235, 68)], fill=(245, 245, 245, 255), width=1)
        d.line([(236, 68), (244, 80)], fill=(245, 245, 245, 255), width=1)
        d.line([(244, 68), (236, 80)], fill=(245, 245, 245, 255), width=1)
    elif c_style == "mock_turtleneck_micro":
        d.arc([198, 22, 282, 74], 15, 165, fill=trim + (255,), width=10)
        d.arc([198, 22, 282, 74], 15, 165, fill=tip_col, width=2)
        d.line([(240, 48), (240, 68)], fill=tip_col, width=2)
        d.line([(238, 68), (242, 68)], fill=tip_col, width=2)
    else:  # crew
        d.arc([198, 26, 282, 78], 15, 165, fill=trim + (255,), width=8)
        if collar_tip and collar_tip != trim:
            d.arc([198, 26, 282, 78], 15, 165, fill=tuple(collar_tip) + (255,), width=2)

    if design.get("badge"):
        try:
            b_logo = Image.open(design["badge"]).convert("RGBA")
            b_col, b_white = _resolve_badge_color(design["badge"], design.get("body", (200, 200, 200)), design)
            if b_col:
                b_logo = _flatten_color(b_logo, b_col)
            elif b_white:
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
        sp_p = Path(design["sponsor"])
        base_stem = sp_p.stem
        if base_stem.endswith("_white"):
            base_stem = base_stem[:-6]
        elif base_stem.endswith("_dark"):
            base_stem = base_stem[:-5]

        # Measure canvas under chest sponsor on preview card
        c_arr = np.array(canvas)[160:230, 145:335, :3]
        if c_arr.size > 0:
            c_lums = 0.2126 * c_arr[:, :, 0] + 0.7152 * c_arr[:, :, 1] + 0.0722 * c_arr[:, :, 2]
            c_lum = float(np.mean(c_lums))
            c_std = float(np.std(c_lums))
        else:
            c_lum = 128.0
            c_std = 0.0

        is_white_logo = False
        if not design.get("sponsor_plate"):
            if c_lum < 130 or design.get("sponsor_white"):
                cand_w = sp_p.parent / f"{base_stem}_white.png"
                if cand_w.is_file():
                    sp_p = cand_w
                is_white_logo = True
            else:
                cand_c = sp_p.parent / f"{base_stem}.png"
                cand_d = sp_p.parent / f"{base_stem}_dark.png"
                if cand_c.is_file() and not design.get("sponsor_dark"):
                    sp_p = cand_c
                elif cand_d.is_file():
                    sp_p = cand_d
                is_white_logo = False
        else:
            is_white_logo = design.get("sponsor_white", False)

        logo = Image.open(sp_p).convert("RGBA")
        if design.get("sponsor_white") and not sp_p.stem.endswith("_white"):
            logo = _flatten_white(logo)
        elif design.get("sponsor_dark") and not sp_p.stem.endswith("_dark"):
            col = design["sponsor_dark"] if isinstance(design["sponsor_dark"], (tuple, list)) else (18, 22, 28)
            logo = _flatten_color(logo, col)
        s = min(190 / logo.width, 60 / logo.height)
        logo = logo.resize((max(1, int(logo.width * s)), max(1, int(logo.height * s))), Image.LANCZOS)

        if design.get("sponsor_plate", False):
            d.rounded_rectangle([118, 160, 362, 236], radius=10, fill=body + (255,))
        elif c_std >= 32.0:
            from PIL import ImageFilter
            alpha_ch = logo.split()[3]
            stroke_alpha = alpha_ch.filter(ImageFilter.MaxFilter(5))  # ~2px radius in preview card scale
            sc = (18, 22, 28) if is_white_logo else (255, 255, 255)
            stroke_layer = Image.new("RGBA", logo.size, sc + (0,))
            stroke_layer.putalpha(stroke_alpha)
            stroke_layer.alpha_composite(logo, (0, 0))
            logo = stroke_layer

        canvas.alpha_composite(logo, (240 - logo.width // 2, 170))

    if design.get("sleeve_sponsor"):
        try:
            sl_path = Path(design["sleeve_sponsor"])
            base_sl = sl_path.stem
            if base_sl.endswith("_white"):
                base_sl = base_sl[:-6]
            elif base_sl.endswith("_dark"):
                base_sl = base_sl[:-5]

            if not sl_path.is_file():
                cand = Path(__file__).resolve().parent / "sleeve_logos" / f"{base_sl}.png"
                if cand.is_file():
                    sl_path = cand
            if sl_path.is_file():
                canvas_arr = np.array(canvas)
                sl_patch = canvas_arr[160:190, 375:415, :3]
                if sl_patch.size > 0:
                    sl_lums = 0.2126 * sl_patch[:, :, 0] + 0.7152 * sl_patch[:, :, 1] + 0.0722 * sl_patch[:, :, 2]
                    sl_lum = float(np.mean(sl_lums))
                    sl_std = float(np.std(sl_lums))
                else:
                    sl_lum = _col_lum(canvas_arr[175, 395, :3])
                    sl_std = 0.0

                is_white_sl = False
                if sl_lum < 130 or design.get("sleeve_sponsor_white"):
                    cand_w = sl_path.parent / f"{base_sl}_white.png"
                    if cand_w.is_file():
                        sl_path = cand_w
                    is_white_sl = True
                else:
                    cand_d = sl_path.parent / f"{base_sl}_dark.png"
                    if cand_d.is_file():
                        sl_path = cand_d
                    else:
                        cand_c = sl_path.parent / f"{base_sl}.png"
                        if cand_c.is_file():
                            sl_path = cand_c

                sl_logo = Image.open(sl_path).convert("RGBA")
                if design.get("sleeve_sponsor_white") and not sl_path.stem.endswith("_white"):
                    sl_logo = _flatten_white(sl_logo)
                sl_scale = min(36 / max(1, sl_logo.width), 20 / max(1, sl_logo.height))
                sl_logo = sl_logo.resize((max(1, int(sl_logo.width * sl_scale)), max(1, int(sl_logo.height * sl_scale))), Image.LANCZOS)

                if sl_std >= 32.0:
                    from PIL import ImageFilter
                    alpha_ch = sl_logo.split()[3]
                    stroke_alpha = alpha_ch.filter(ImageFilter.MaxFilter(5))
                    sc = (18, 22, 28) if is_white_sl else (255, 255, 255)
                    stroke_layer = Image.new("RGBA", sl_logo.size, sc + (0,))
                    stroke_layer.putalpha(stroke_alpha)
                    stroke_layer.alpha_composite(sl_logo, (0, 0))
                    sl_logo = stroke_layer

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


def generate_shorts_mockup(design, club_name, season, out_png, badge_path=None, supplier_path=None):
    """Render a dedicated 2D athletic shorts presentation mockup."""
    W, H = 480, 480
    canvas = Image.new("RGBA", (W, H), (28, 30, 36, 255))
    draw = ImageDraw.Draw(canvas)

    base = tuple(design.get("shorts") or design["body"])
    acc = tuple(design.get("shorts_accent") or design.get("second") or (245, 245, 245))
    tip = tuple(design.get("shorts_tip") or design.get("third") or acc)
    style = design.get("shorts_style", "solid")

    s_mask = Image.new("L", (W, H), 0)
    d_mask = ImageDraw.Draw(s_mask)

    shorts_poly = [
        (120, 80), (360, 80),   # Waistband top
        (368, 120),             # Hip right
        (395, 380),             # Hem outer right
        (258, 380),             # Inseam hem right
        (240, 260),             # Crotch center
        (222, 380),             # Inseam hem left
        (85, 380),              # Hem outer left
        (112, 120),             # Hip left
    ]
    d_mask.polygon(shorts_poly, fill=255)

    body_layer = Image.new("RGBA", (W, H), base + (255,))
    if style == "two_tone_halves":
        d_body = ImageDraw.Draw(body_layer)
        d_body.rectangle([(240, 0), (W, H)], fill=acc + (255,))

    canvas.paste(body_layer, (0, 0), s_mask)

    fx_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d_fx = ImageDraw.Draw(fx_layer)

    if style == "contrast_flank_panel":
        d_fx.polygon([(112, 120), (145, 120), (160, 380), (85, 380)], fill=acc + (255,))
        d_fx.line([(145, 120), (160, 380)], fill=tip + (255,), width=2)
        d_fx.polygon([(368, 120), (335, 120), (320, 380), (395, 380)], fill=acc + (255,))
        d_fx.line([(335, 120), (320, 380)], fill=tip + (255,), width=2)

    elif style == "side_stripe":
        d_fx.polygon([(112, 120), (128, 120), (110, 380), (94, 380)], fill=acc + (255,))
        d_fx.polygon([(368, 120), (352, 120), (370, 380), (386, 380)], fill=acc + (255,))

    elif style == "dual_side_stripes":
        d_fx.polygon([(112, 120), (120, 120), (98, 380), (90, 380)], fill=acc + (255,))
        d_fx.polygon([(124, 120), (132, 120), (110, 380), (102, 380)], fill=acc + (255,))
        d_fx.polygon([(368, 120), (360, 120), (390, 380), (382, 380)], fill=acc + (255,))
        d_fx.polygon([(356, 120), (348, 120), (378, 380), (370, 380)], fill=acc + (255,))

    elif style == "hem_tape":
        d_fx.polygon([(85, 360), (222, 360), (222, 380), (85, 380)], fill=acc + (255,))
        d_fx.polygon([(258, 360), (395, 360), (395, 380), (258, 380)], fill=acc + (255,))

    elif style == "hem_turnup_notch":
        d_fx.polygon([(85, 362), (222, 362), (222, 380), (85, 380)], fill=acc + (255,))
        d_fx.polygon([(258, 362), (395, 362), (395, 380), (258, 380)], fill=acc + (255,))
        d_fx.polygon([(87, 362), (100, 335), (113, 362)], fill=acc + (255,))
        d_fx.line([(87, 362), (100, 335), (113, 362)], fill=tip + (255,), width=2)
        d_fx.polygon([(393, 362), (380, 335), (367, 362)], fill=acc + (255,))
        d_fx.line([(393, 362), (380, 335), (367, 362)], fill=tip + (255,), width=2)

    elif style == "gradient_side_fade":
        for y in range(160, 380):
            t = (y - 160) / float(380 - 160)
            a = int(255 * (t ** 1.4))
            col = acc + (a,)
            xl = int(112 + (85 - 112) * t)
            xr = int(368 + (395 - 368) * t)
            d_fx.line([(xl, y), (xl + 32, y)], fill=col)
            d_fx.line([(xr - 32, y), (xr, y)], fill=col)

    elif style == "contrast_waistband":
        d_fx.polygon([(120, 80), (360, 80), (368, 120), (112, 120)], fill=acc + (255,))
        d_fx.line([(116, 95), (364, 95)], fill=(0, 0, 0, 70), width=2)
        d_fx.line([(114, 108), (366, 108)], fill=(255, 255, 255, 60), width=2)
        d_fx.rectangle([(236, 96), (239, 100)], fill=(20, 20, 20, 255))
        d_fx.rectangle([(243, 96), (246, 100)], fill=(20, 20, 20, 255))
        d_fx.line([(237, 100), (235, 116)], fill=tip + (255,), width=2)
        d_fx.line([(244, 100), (246, 116)], fill=tip + (255,), width=2)

    elif style == "split_leg":
        d_fx.polygon([(85, 360), (222, 375), (222, 380), (85, 380)], fill=acc + (255,))
        d_fx.polygon([(258, 375), (395, 360), (395, 380), (258, 380)], fill=acc + (255,))

    canvas.paste(fx_layer, (0, 0), fx_layer)

    if style != "contrast_waistband":
        draw.line([(112, 120), (368, 120)], fill=(0, 0, 0, 90), width=2)

    draw.line([(240, 120), (240, 260)], fill=(0, 0, 0, 90), width=2)

    if badge_path:
        try:
            b_img = Image.open(badge_path).convert("RGBA")
            b_img.thumbnail((48, 48), Image.LANCZOS)
            canvas.paste(b_img, (145, 305), b_img)
        except Exception:
            pass

    if supplier_path:
        try:
            s_img = Image.open(supplier_path).convert("RGBA")
            s_img.thumbnail((42, 28), Image.LANCZOS)
            canvas.paste(s_img, (295, 315), s_img)
        except Exception:
            pass

    try:
        font = ImageFont.truetype("arialbd.ttf", 16)
        subfont = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font = ImageFont.load_default()
        subfont = font

    draw.text((16, 16), f"{club_name} {season} • Shorts", fill=(240, 240, 245, 255), font=font)
    draw.text((16, 38), f"Style: {style}", fill=(180, 185, 195, 255), font=subfont)

    canvas.save(out_png)
    return out_png


def generate_socks_mockup(design, club_name, season, out_png, supplier_path=None):
    """Render a dedicated 2D athletic socks presentation mockup showcasing matched pair styling."""
    W, H = 480, 480
    canvas = Image.new("RGBA", (W, H), (28, 30, 36, 255))
    draw = ImageDraw.Draw(canvas)

    base = tuple(design.get("socks") or design["body"])
    acc = tuple(design.get("socks_accent") or design.get("second") or (245, 245, 245))
    tip = tuple(design.get("socks_tip") or design.get("third") or acc)
    style = design.get("socks_style", "solid")

    def make_sock_polygon(x_c, y_top=75, flip=False):
        w_cuff = 46
        w_calf = 42
        w_ank = 34
        poly = [
            (x_c - w_cuff, y_top),
            (x_c + w_cuff, y_top),
            (x_c + w_cuff, y_top + 48),  # Turnover bottom
            (x_c + w_calf, y_top + 160), # Mid calf
            (x_c + w_ank, y_top + 245),  # Ankle
            (x_c + (w_ank + 14 if flip else w_ank + 4), y_top + 300), # Foot lateral
            (x_c + (14 if flip else 6), y_top + 322), # Toe tip
            (x_c - (6 if flip else 14), y_top + 322),
            (x_c - (w_ank + 4 if flip else w_ank + 14), y_top + 300), # Foot medial
            (x_c - w_ank, y_top + 245),
            (x_c - w_calf, y_top + 160),
            (x_c - w_cuff, y_top + 48),
        ]
        return poly

    poly_l = make_sock_polygon(165, 75, flip=False)
    poly_r = make_sock_polygon(315, 75, flip=True)

    s_mask = Image.new("L", (W, H), 0)
    d_m = ImageDraw.Draw(s_mask)
    d_m.polygon(poly_l, fill=255)
    d_m.polygon(poly_r, fill=255)

    # Base garment fill
    body_layer = Image.new("RGBA", (W, H), base + (255,))

    # FX Layer
    fx_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d_fx = ImageDraw.Draw(fx_layer)

    centers = [165, 315]

    if style == "turnover_hoop":
        d_fx.rectangle([(0, 75), (W, 123)], fill=acc + (255,))
        d_fx.rectangle([(0, 119), (W, 125)], fill=tip + (255,))

    elif style == "dual_hoop_turnover":
        d_fx.rectangle([(0, 77), (W, 95)], fill=acc + (255,))
        d_fx.rectangle([(0, 103), (W, 121)], fill=acc + (255,))
        d_fx.rectangle([(0, 121), (W, 125)], fill=tip + (255,))

    elif style == "triple_hoop_turnover":
        d_fx.rectangle([(0, 77), (W, 89)], fill=acc + (255,))
        d_fx.rectangle([(0, 93), (W, 105)], fill=acc + (255,))
        d_fx.rectangle([(0, 109), (W, 121)], fill=acc + (255,))
        d_fx.rectangle([(0, 121), (W, 125)], fill=tip + (255,))

    elif style == "full_hooped_body":
        for y in range(75, 330, 28):
            d_fx.rectangle([(0, y), (W, y + 15)], fill=acc + (255,))
            d_fx.line([(0, y), (W, y)], fill=tip + (255,), width=1)
            d_fx.line([(0, y + 15), (W, y + 15)], fill=tip + (255,), width=1)

    elif style == "calf_band":
        d_fx.rectangle([(0, 205), (W, 252)], fill=acc + (255,))
        d_fx.rectangle([(0, 202), (W, 205)], fill=tip + (255,))
        d_fx.rectangle([(0, 252), (W, 255)], fill=tip + (255,))

    elif style == "triple_calf_hoops":
        for y in [185, 212, 239]:
            d_fx.rectangle([(0, y), (W, y + 14)], fill=acc + (255,))
            d_fx.line([(0, y + 7), (W, y + 7)], fill=tip + (255,), width=2)

    elif style == "vertical_back_spine":
        for xc in centers:
            d_fx.rectangle([(xc - 9, 75), (xc + 9, 320)], fill=acc + (255,))
            d_fx.line([(xc - 11, 75), (xc - 11, 320)], fill=tip + (255,), width=2)
            d_fx.line([(xc + 11, 75), (xc + 11, 320)], fill=tip + (255,), width=2)
        d_fx.rectangle([(0, 75), (W, 87)], fill=acc + (255,))

    elif style == "gradient_dip":
        d_fx.rectangle([(0, 270), (W, H)], fill=acc + (255,))
        d_fx.rectangle([(0, 258), (W, 262)], fill=tip + (255,))
        d_fx.rectangle([(0, 264), (W, 268)], fill=tip + (255,))

    elif style == "gradient_fade":
        for y in range(75, 340):
            t = ((y - 75) / float(340 - 75)) ** 1.3
            c = (int(base[0] * (1 - t) + acc[0] * t),
                 int(base[1] * (1 - t) + acc[1] * t),
                 int(base[2] * (1 - t) + acc[2] * t), 255)
            d_fx.line([(0, y), (W, y)], fill=c)

    elif style == "ankle_bracket_cuff":
        d_fx.rectangle([(0, 75), (W, 85)], fill=acc + (255,))
        d_fx.rectangle([(0, 275), (W, 295)], fill=acc + (255,))
        d_fx.line([(0, 275), (W, 275)], fill=tip + (255,), width=2)
        d_fx.line([(0, 295), (W, 295)], fill=tip + (255,), width=2)
        d_fx.rectangle([(0, 305), (W, 318)], fill=acc + (255,))

    elif style == "chevron_stack":
        for xc in centers:
            for y in [170, 195, 220, 245]:
                d_fx.polygon([(xc, y + 14), (xc - 22, y), (xc - 13, y), (xc, y + 9), (xc + 13, y), (xc + 22, y)], fill=acc + (255,))

    body_layer.paste(fx_layer, (0, 0), fx_layer)
    canvas.paste(body_layer, (0, 0), s_mask)

    # Outline & turnover seam definition
    draw.polygon(poly_l, outline=(85, 95, 110, 255), width=2)
    draw.polygon(poly_r, outline=(85, 95, 110, 255), width=2)
    draw.line([(165 - 46, 123), (165 + 46, 123)], fill=(140, 150, 165, 200), width=2)
    draw.line([(315 - 46, 123), (315 + 46, 123)], fill=(140, 150, 165, 200), width=2)

    # Supplier stamp on shin (between y=140 and 165)
    if supplier_path and os.path.exists(supplier_path):
        try:
            s_img = Image.open(supplier_path).convert("RGBA")
            s_img.thumbnail((32, 20), Image.LANCZOS)
            canvas.paste(s_img, (165 - s_img.width // 2, 145), s_img)
            canvas.paste(s_img, (315 - s_img.width // 2, 145), s_img)
        except Exception:
            pass

    try:
        font = ImageFont.truetype("arialbd.ttf", 16)
        subfont = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font = ImageFont.load_default()
        subfont = font

    draw.text((16, 16), f"{club_name} {season} • Socks", fill=(240, 240, 245, 255), font=font)
    draw.text((16, 38), f"Style: {style}", fill=(180, 185, 195, 255), font=subfont)

    canvas.save(out_png)
    return out_png


def generate_sleeve_mockup(design, club_name, season, out_png, badge_path=None, sleeve_sponsor_path=None, supplier_path=None):
    """Render a dedicated 2D athletic sleeve presentation mockup showcasing sleeve construction,
    raglan/saddle tailoring, sleeve sponsor & badge placement, and coordinated undersleeves."""
    import os
    W, H = 540, 520
    canvas = Image.new("RGBA", (W, H), (14, 18, 26, 255))
    draw = ImageDraw.Draw(canvas)

    body = tuple(design.get("body") or (20, 20, 20))
    sleeve = tuple(design.get("sleeve") or body)
    accent = tuple(design.get("stripe_accent") or design.get("second") or design.get("accent") or (240, 240, 245))
    tip = tuple(design.get("third") or design.get("accent") or accent)
    style = design.get("sleeve_style", "solid")
    undershirt_col = tuple(design.get("undershirt_color_rgb") or sleeve)

    # 1. Torso silhouette backdrop (subtle chest/clavicle context)
    t_poly = [(40, 160), (95, 70), (140, 75), (95, 290), (40, 280)]
    draw.polygon(t_poly, fill=body + (255,), outline=(45, 52, 65, 255))

    # 2. Base layer undersleeve (long compression arm extending below short sleeve cuff)
    u_mask = Image.new("L", (W, H), 0)
    u_draw = ImageDraw.Draw(u_mask)
    u_poly = [(138, 255), (235, 240), (218, 435), (148, 442)]
    u_draw.polygon(u_poly, fill=255)

    u_layer = Image.new("RGBA", (W, H), undershirt_col + (255,))
    u_d = ImageDraw.Draw(u_layer)
    for wy in range(426, 442, 3):
        u_d.line([(140, wy), (225, wy)], fill=(max(0, undershirt_col[0] - 25), max(0, undershirt_col[1] - 25), max(0, undershirt_col[2] - 25), 255), width=1)
    canvas.paste(u_layer, (0, 0), u_mask)
    draw.polygon(u_poly, outline=(60, 70, 85, 255), width=2)

    # 3. Main Jersey Short Sleeve & Shoulder Assembly
    s_mask = Image.new("L", (W, H), 0)
    s_draw = ImageDraw.Draw(s_mask)
    s_poly = [(95, 70), (225, 115), (242, 250), (135, 270), (110, 175), (95, 70)]
    s_draw.polygon(s_poly, fill=255)

    s_base_col = accent if style in ("contrast_raglan", "raglan_contrast", "raglan") else sleeve
    s_body = Image.new("RGBA", (W, H), s_base_col + (255,))
    s_fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d_fx = ImageDraw.Draw(s_fx)

    if style in ("shoulder_saddle_panel", "saddle_panel", "shoulder_yoke"):
        d_fx.polygon([(95, 70), (225, 115), (215, 150), (100, 115)], fill=accent + (255,))
        d_fx.line([(100, 115), (215, 150)], fill=tip + (255,), width=3)

    elif style in ("speed_chevrons", "chevrons", "chevron_sleeve"):
        for cy in range(125, 240, 26):
            d_fx.polygon([(185, cy), (198, cy + 12), (211, cy), (211, cy - 6), (198, cy + 6), (185, cy - 6)], fill=accent + (255,))

    elif style in ("gradient_sleeve_fade", "gradient_fade", "sleeve_fade"):
        for gy in range(70, 270):
            t = ((gy - 70) / 200.0) ** 1.2
            c_fade = (
                int(sleeve[0] * (1 - t) + accent[0] * t),
                int(sleeve[1] * (1 - t) + accent[1] * t),
                int(sleeve[2] * (1 - t) + accent[2] * t),
                255
            )
            d_fx.line([(90, gy), (250, gy)], fill=c_fade, width=1)

    elif style in ("split_dual_block", "split_sleeve", "dual_block"):
        d_fx.polygon([(115, 185), (236, 175), (242, 250), (135, 270)], fill=accent + (255,))
        d_fx.line([(115, 185), (236, 175)], fill=tip + (255,), width=3)

    elif style in ("brand_track_tape", "track_tape"):
        d_fx.polygon([(188, 110), (202, 110), (216, 248), (202, 248)], fill=accent + (255,))
        for cy in range(118, 242, 18):
            d_fx.polygon([(195, cy), (202, cy + 6), (209, cy), (202, cy - 6)], fill=sleeve + (255,))

    elif style in ("sublimated_camo_sleeve", "camo_sleeve", "camo"):
        import numpy as np
        rng = np.random.default_rng(season * 10007 + hash(club_name) & 0xFFFFFFFF)
        for _ in range(35):
            cx = int(rng.integers(100, 235))
            cy = int(rng.integers(80, 245))
            cw = int(rng.integers(12, 32))
            ch = int(rng.integers(8, 22))
            c_fill = accent + (180,) if rng.random() > 0.5 else (max(0, sleeve[0] - 25), max(0, sleeve[1] - 25), max(0, sleeve[2] - 25), 180)
            d_fx.polygon([(cx, cy), (cx + cw, cy + 3), (cx + cw - 4, cy + ch), (cx - 3, cy + ch - 3)], fill=c_fill)

    elif style in ("grunge_yoke", "brush_splatter", "splatter_brush"):
        import numpy as np
        rng = np.random.default_rng(season * 10007 + hash(club_name) & 0xFFFFFFFF)
        for _ in range(40):
            cx = int(rng.integers(95, 230))
            cy = int(rng.integers(70, 160))
            cw = int(rng.integers(4, 14))
            ch = int(rng.integers(15, 45))
            d_fx.polygon([(cx, cy), (cx + cw, cy + 4), (cx + cw // 2, cy + ch), (cx - 2, cy + ch - 4)], fill=accent + (255,))

    s_body.paste(s_fx, (0, 0), s_fx)
    canvas.paste(s_body, (0, 0), s_mask)

    # 4. Sleeve Cuff Band (at y=252..270)
    cuff_mask = Image.new("L", (W, H), 0)
    c_draw = ImageDraw.Draw(cuff_mask)
    c_poly = [(135, 270), (242, 250), (240, 236), (133, 256)]
    c_draw.polygon(c_poly, fill=255)
    cuff_col = tuple(design.get("cuff") or accent)
    canvas.paste(Image.new("RGBA", (W, H), cuff_col + (255,)), (0, 0), cuff_mask)
    draw.polygon(c_poly, outline=tip + (255,), width=1)

    # 5. Seam Outline & Raglan Piping
    draw.polygon(s_poly, outline=(60, 70, 85, 255), width=2)
    if style in ("contrast_raglan", "raglan_contrast", "raglan", "seam_piping", "piping", "raglan_piping"):
        draw.line([(95, 70), (110, 175)], fill=accent + (255,), width=4)
        draw.line([(95, 70), (110, 175)], fill=tip + (255,), width=1)
    else:
        draw.line([(95, 70), (110, 175)], fill=(75, 85, 105, 255), width=2)

    # 6. Sleeve Sponsor Stamp (on bicep y=165..215)
    if sleeve_sponsor_path and os.path.exists(sleeve_sponsor_path):
        try:
            sp_img = Image.open(sleeve_sponsor_path).convert("RGBA")
            sp_img.thumbnail((72, 38), Image.LANCZOS)
            canvas.paste(sp_img, (175 - sp_img.width // 2, 195 - sp_img.height // 2), sp_img)
        except Exception:
            pass

    # 7. Sleeve Badge Stamp (outer sleeve y=140..175)
    if badge_path and os.path.exists(badge_path):
        try:
            bd_img = Image.open(badge_path).convert("RGBA")
            bd_img.thumbnail((34, 34), Image.LANCZOS)
            canvas.paste(bd_img, (205, 140), bd_img)
        except Exception:
            pass

    # 8. Right side info panel & swatches
    try:
        font = ImageFont.truetype("arialbd.ttf", 16)
        subfont = ImageFont.truetype("arial.ttf", 12)
        boldfont = ImageFont.truetype("arialbd.ttf", 12)
    except Exception:
        font = ImageFont.load_default()
        subfont = font
        boldfont = font

    draw.text((20, 18), f"{club_name} {season} • Sleeve & Construction", fill=(240, 240, 245, 255), font=font)
    draw.text((20, 40), f"Active Style: {style.upper()}", fill=(180, 185, 195, 255), font=subfont)

    rx, ry = 280, 75
    draw.rectangle([(rx, ry), (rx + 235, ry + 395)], fill=(20, 24, 34, 255), outline=(45, 55, 70, 255), width=1)
    draw.text((rx + 14, ry + 14), "CONSTRUCTION SPECS", fill=(220, 225, 235, 255), font=boldfont)

    y_off = ry + 42
    specs = [
        ("Sleeve Style", style),
        ("Cuff Style", design.get("cuff_style", "solid")),
        ("Collar Model", str(design.get("collar_model", 1))),
        ("Supplier", str(design.get("supplier", "generic")).upper()),
    ]
    for k, v in specs:
        draw.text((rx + 14, y_off), k, fill=(140, 145, 160, 255), font=subfont)
        draw.text((rx + 130, y_off), str(v), fill=(235, 235, 245, 255), font=boldfont)
        y_off += 24

    draw.line([(rx + 14, y_off + 8), (rx + 221, y_off + 8)], fill=(45, 55, 70, 255), width=1)
    y_off += 18
    draw.text((rx + 14, y_off), "BASE LAYER UNDERSLEEVE", fill=(220, 225, 235, 255), font=boldfont)
    y_off += 20
    hex_u = f"#{undershirt_col[0]:02x}{undershirt_col[1]:02x}{undershirt_col[2]:02x}"
    draw.rectangle([(rx + 14, y_off), (rx + 48, y_off + 32)], fill=undershirt_col + (255,), outline=(90, 100, 120, 255), width=1)
    draw.text((rx + 58, y_off + 2), hex_u.upper(), fill=(240, 240, 245, 255), font=boldfont)
    draw.text((rx + 58, y_off + 18), "Sider UniColor_Color1 Synced", fill=(100, 200, 120, 255), font=subfont)

    y_off += 45
    draw.rectangle([(rx + 14, y_off), (rx + 221, y_off + 54)], fill=(15, 20, 28, 255), outline=(35, 45, 60, 255), width=1)
    draw.text((rx + 22, y_off + 8), "PES 2021 / FL27 Engine", fill=(140, 150, 170, 255), font=subfont)
    draw.text((rx + 22, y_off + 24), "100% In-Game Compression Sync", fill=(100, 220, 140, 255), font=boldfont)

    canvas.save(out_png)
    return out_png


def generate_fabric_mockup(design, club_name, season, out_png):
    """Render a standalone 2D presentation card showcasing garment fabric finish & weave structure.

    Dimensions: 540 x 520 px.
    Shows:
    - Realistic draped textile swatch with active club body color and finish weave
    - High-magnification 8x circular macro loupe displaying individual knit/damask/perforation details
    - Twin-needle chainstitch hem construction
    - Technical fabric specifications and Master League runtime status
    """
    W, H = 540, 520
    canvas = Image.new("RGBA", (W, H), (18, 22, 28, 255))
    draw = ImageDraw.Draw(canvas)

    subfont = ImageFont.load_default()
    boldfont = ImageFont.load_default()
    titlefont = ImageFont.load_default()

    # Outer border
    draw.rectangle([0, 0, W - 1, H - 1], outline=(40, 48, 62, 255), width=1)

    finish = str(design.get("fabric_finish", "standard_microknit")).lower()
    body_col = tuple(design.get("body", (20, 25, 45)))
    sec_col = tuple(design.get("second", (220, 35, 45)))
    acc_col = tuple(design.get("stripe_accent", (245, 245, 250)))

    # Header
    draw.rectangle([1, 1, W - 2, 54], fill=(14, 18, 24, 255))
    draw.text((24, 12), f"{club_name} {season} • Fabric Architecture", fill=(245, 248, 252, 255), font=titlefont)
    draw.text((24, 30), f"Active Weave: {finish.upper()}", fill=(140, 160, 185, 255), font=subfont)

    # 1. Base draped fabric swatch (220 x 390 px)
    sw_x, sw_y = 28, 75
    sw_w, sw_h = 220, 390

    swatch = Image.new("RGBA", (sw_w, sw_h), body_col + (255,))
    sw_arr = np.array(swatch).astype(np.float32)

    # Shading drape waves across swatch (simulating cloth fold lighting)
    xx, yy = np.meshgrid(np.arange(sw_w), np.arange(sw_h))
    drape = 12.0 * np.sin(xx / 28.0) * np.cos(yy / 120.0)

    # Finish microtexture modulation
    f_mod = np.zeros((sw_h, sw_w), dtype=np.float32)
    if finish in ("matte_vaporknit", "aero_knit", "vaporknit"):
        waves = 7.0 * np.sin(yy / 4.0 + np.cos(xx / 12.0))
        perfs = np.where((yy % 8 < 2) & (xx % 8 < 2), -6.0, 0.0)
        f_mod = waves + perfs
    elif finish in ("embossed_damask", "damask", "watermark"):
        ty = yy % 24
        tx = xx % 24
        is_diag = (np.abs((tx - 12) + (ty - 12)) == 11) | (np.abs((tx - 12) - (ty - 12)) == 11)
        is_fleur = ((tx >= 10) & (tx <= 14) & (ty >= 6) & (ty <= 14)) | ((tx >= 7) & (tx <= 17) & (ty == 11))
        f_mod = np.where(is_diag | is_fleur, 8.0, -3.5)
    elif finish in ("heather_melange", "melange", "heather"):
        hash_val = (xx * 37 + yy * 73) % 11
        f_mod = np.where(hash_val < 3, 7.0, np.where(hash_val > 7, -7.0, 0.0))
    elif finish in ("geometric_jacquard", "jacquard", "isometric"):
        ty = yy % 16
        tx = xx % 16
        top_facet = (ty < 8) & ((tx >= (7 - ty)) & (tx <= (8 + ty)))
        left_facet = (ty >= 8) & (tx < 8)
        f_mod = np.where(top_facet, 7.5, np.where(left_facet, -6.5, 0.5))
    elif finish in ("corduroy_rib", "ribbed_fabric", "needle_cord"):
        f_mod = np.where((xx % 6) < 3, 7.0, -7.0)
    else:  # standard_microknit
        k_piq = np.array([[4.0, -3.0], [-3.0, 4.0]], dtype=np.float32)
        f_mod = np.tile(k_piq, (sw_h // 2 + 1, sw_w // 2 + 1))[:sw_h, :sw_w]

    total_delta = drape + f_mod
    sw_arr[:, :, :3] += total_delta[:, :, None]
    np.clip(sw_arr, 0, 255, out=sw_arr)
    swatch = Image.fromarray(sw_arr.astype(np.uint8))

    canvas.paste(swatch, (sw_x, sw_y))
    draw.rectangle([sw_x, sw_y, sw_x + sw_w, sw_y + sw_h], outline=(55, 65, 80, 255), width=1)

    # Twin-needle flatlock chainstitch along bottom hem
    stitch_y = sw_y + sw_h - 18
    draw.line([(sw_x + 5, stitch_y), (sw_x + sw_w - 5, stitch_y)], fill=sec_col + (220,), width=2)
    draw.line([(sw_x + 5, stitch_y + 4), (sw_x + sw_w - 5, stitch_y + 4)], fill=sec_col + (220,), width=2)
    for sx in range(sw_x + 8, sw_x + sw_w - 8, 8):
        draw.line([(sx, stitch_y - 1), (sx + 3, stitch_y + 5)], fill=acc_col + (255,), width=1)

    # 2. High-Magnification Macro Loupe (Radius 62 px)
    cx, cy, r = sw_x + sw_w // 2, sw_y + 160, 62
    crop_size = 28
    crop_x0 = max(0, min(sw_w - crop_size, sw_w // 2 - crop_size // 2))
    crop_y0 = max(0, min(sw_h - crop_size, 160 - crop_size // 2))
    macro_crop = swatch.crop((crop_x0, crop_y0, crop_x0 + crop_size, crop_y0 + crop_size))
    macro_zoom = macro_crop.resize((r * 2, r * 2), Image.Resampling.BOX)

    # Circular mask for loupe
    loupe_mask = Image.new("L", (r * 2, r * 2), 0)
    ImageDraw.Draw(loupe_mask).ellipse([0, 0, r * 2, r * 2], fill=255)
    canvas.paste(macro_zoom, (cx - r, cy - r), loupe_mask)

    # Reticle and lens frame
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(220, 180, 50, 255), width=3)
    draw.ellipse([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2], outline=(15, 20, 28, 255), width=1)
    draw.line([(cx - r + 8, cy), (cx - 15, cy)], fill=(220, 180, 50, 200), width=1)
    draw.line([(cx + 15, cy), (cx + r - 8, cy)], fill=(220, 180, 50, 200), width=1)
    draw.line([(cx, cy - r + 8), (cx, cy - 15)], fill=(220, 180, 50, 200), width=1)
    draw.line([(cx, cy + 15), (cx, cy + r - 8)], fill=(220, 180, 50, 200), width=1)

    # Loupe badge
    draw.rectangle([cx - 45, cy + r - 12, cx + 45, cy + r + 6], fill=(12, 16, 22, 240), outline=(220, 180, 50, 255))
    draw.text((cx - 36, cy + r - 9), "8x MACRO ZOOM", fill=(250, 250, 250, 255), font=subfont)

    # Swatch caption
    draw.text((sw_x + 10, sw_y + sw_h + 12), "ENGINEERED JERSEY SWATCH", fill=(140, 155, 175, 255), font=subfont)

    # 3. Technical Specifications Card (Right side)
    rx = 270
    draw.rectangle([rx, 75, W - 24, 480], fill=(14, 18, 24, 255), outline=(40, 48, 62, 255), width=1)
    draw.text((rx + 16, 92), "FABRIC SPECIFICATIONS", fill=(245, 248, 252, 255), font=boldfont)
    draw.line([(rx + 16, 112), (W - 40, 112)], fill=(45, 55, 70, 255), width=1)

    desc_map = {
        "matte_vaporknit": ("Matte VaporKnit Aerowave", "Undulating Aeration Channels", "140 g/m² Ultralight", "Elite Match Pro"),
        "embossed_damask": ("Regal Embossed Damask", "Tonal Heraldic Watermark", "155 g/m² Heritage Knit", "Luxury Collector Tier"),
        "heather_melange": ("Streetwear Marl Melange", "Organic Cross-Hatch Slub", "160 g/m² Cotton-Poly", "Modern Lifestyle Tier"),
        "geometric_jacquard": ("3D Optical Jacquard", "Isometric Cube Tessellation", "150 g/m² Engineered Weave", "High-Tech Dynamic"),
        "corduroy_rib": ("Vintage Corduroy Rib", "Micro-Needlecord Channels", "165 g/m² Heritage Weave", "Retro Classic Tier"),
        "standard_microknit": ("Elite Micro-Honeycomb", "High-Density Piqué Grain", "145 g/m² Technical Poly", "Authentic Standard"),
    }
    f_info = desc_map.get(finish, desc_map["standard_microknit"])

    specs = [
        ("Weave Profile:", f_info[0]),
        ("Knit Structure:", f_info[1]),
        ("Fabric Weight:", f_info[2]),
        ("Performance Tier:", f_info[3]),
        ("3D Mesh Shading:", "Luminance Mod +/- 6.0%"),
        ("Sider Runtime:", "Master League Dynamic ML"),
        ("Exhibition Mode:", "Original Licensed Kits"),
    ]

    y_cur = 126
    for lbl, val in specs:
        draw.text((rx + 16, y_cur), lbl, fill=(120, 135, 155, 255), font=subfont)
        draw.text((rx + 16, y_cur + 16), val, fill=(235, 240, 248, 255), font=boldfont)
        y_cur += 38

    # Bottom status banner
    draw.rectangle([rx + 14, 420, W - 38, 465], fill=(18, 24, 32, 255), outline=(55, 130, 85, 255), width=1)
    draw.ellipse([rx + 24, 437, rx + 34, 447], fill=(50, 220, 110, 255))
    draw.text((rx + 42, 429), "PES 2021 / FL27 Engine Verified", fill=(210, 245, 220, 255), font=subfont)
    draw.text((rx + 42, 444), "Tactile Microtexture In-Game Active", fill=(100, 220, 140, 255), font=boldfont)

    canvas.save(out_png)
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
