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
    "collar_style": "crew",       # "crew", "retro_crew", "v_neck", "crossover_v", "polo", "polo_v_notch", "dual_tipped", "mandarin_button"
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
    """Paste the shirt-local tile into front/back islands with selective pattern masking and sponsor calm zone."""
    boxes = kit_regions.region_boxes(masks)
    mask_mode = (d.get("pattern_mask") if d else "full") or "full"

    fx0, fy0, fx1, fy1 = boxes["body_front"]
    fw, fh = fx1 - fx0 + 1, fy1 - fy0 + 1
    front = tile.resize((fw, fh), Image.LANCZOS)
    fmask_raw = masks["body_front"][fy0:fy1 + 1, fx0:fx1 + 1].copy()

    # UEFA/FIFA Article 19 authentic calm chest zone for high-contrast patterns
    # Attenuate bold pattern strokes under the chest sponsor footprint so typography never clashes
    if d and d.get("sponsor") and d.get("pattern", "plain") != "plain" and d.get("macro_layout") != "chestband":
        # Sponsor center in front-box local coordinates (atlas 1024, 1310):
        scx = 1024 - fx0
        scy = 1310 - fy0
        calm_local = Image.new("L", (fw, fh), 0)
        c_draw = ImageDraw.Draw(calm_local)
        # Footprint: width 520, height 230 centered at (scx, scy)
        c_x0 = max(0, scx - 260)
        c_x1 = min(fw, scx + 260)
        c_y0 = max(0, scy - 115)
        c_y1 = min(fh, scy + 115)
        # Fill calm area with attenuation strength ~215 (leaving ~15% subtle pattern hint)
        c_draw.rounded_rectangle([c_x0, c_y0, c_x1, c_y1], radius=45, fill=215)
        calm_local = calm_local.filter(ImageFilter.GaussianBlur(radius=32))
        
        # Solid body base tile
        body_col = tuple(d["body"]) + (255,)
        body_solid_local = Image.new("RGBA", (fw, fh), body_col)
        front = Image.composite(body_solid_local, front, calm_local)

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


def _apply_sleeve_architecture(atlas, d, masks):
    """Render distinctive shoulder, sleeve, and yoke architecture:
    - 'grunge_yoke': Aggressive urban brushstroke splatter across chest/shoulder saddle and sleeves (BVB Cup kit style)
    - 'brand_track_tape': Continuous branded geometric track running down the sleeve outer ridge (LOSC Lille / Kappa style)
    - 'seam_piping': Modern ergonomic contrast piping along the raglan diagonal seams
    """
    style = d.get("sleeve_style", "solid")
    if style in ("solid", "raglan", "tipped"):
        return

    body_front = masks["body_front"]
    body_back = masks["body_back"]
    sleeve_mask = masks["sleeve"]

    accent = d.get("stripe_accent") or d.get("second") or d.get("accent") or (240, 240, 245)
    acc_rgba = tuple(accent) + (255,)
    tip = d.get("third") or d.get("accent") or accent
    tip_rgba = tuple(tip) + (255,)

    if style in ("grunge_yoke", "brush_splatter"):
        cid = int(d.get("team_id") or d.get("cid") or 126)
        season = int(d.get("season", 2026))
        slot = str(d.get("slot", 1))
        seed_val = ((cid * 1000003) ^ (season * 999983) ^ (hash(slot) & 0xFFFFFFFF)) & 0xFFFFFFFF
        rng = np.random.default_rng(seed_val)

        yoke_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_y = ImageDraw.Draw(yoke_layer)

        # 1. Front chest & clavicle splatter (stops above chest sponsor Y: 1220)
        for _ in range(110):
            x = int(rng.integers(680, 1370))
            y = int(rng.integers(955, 1140))
            w = int(rng.integers(10, 36))
            h = int(rng.integers(25, 90))
            draw_y.polygon([(x, y), (x + w, y + 8), (x + w // 2, y + h), (x - w // 3, y + h - 12)], fill=acc_rgba)
            if rng.random() > 0.6:
                fx, fy = int(rng.integers(x - 15, x + 35)), int(rng.integers(y + h, y + h + 30))
                draw_y.ellipse([fx, fy, fx + 6, fy + 6], fill=tip_rgba)

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

    elif style in ("seam_piping", "piping"):
        pipe_layer = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))
        draw_p = ImageDraw.Draw(pipe_layer)
        draw_p.line([(740, 970), (840, 1020), (910, 1100)], fill=acc_rgba, width=4)
        draw_p.line([(1308, 970), (1208, 1020), (1138, 1100)], fill=acc_rgba, width=4)
        draw_p.line([(740, 970), (840, 1020), (910, 1100)], fill=tip_rgba, width=1)
        draw_p.line([(1308, 970), (1208, 1020), (1138, 1100)], fill=tip_rgba, width=1)
        _composite_layer(atlas, pipe_layer, body_front | sleeve_mask)



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
    """Apply authentic multi-zone micro-knit textile weave across garment fabric panels.

    Subtly modulates fabric luminance by +/- 2.5% to +/- 4.5%, producing a rich, tactile,
    matte athletic cloth appearance in 3D replays and close-ups without altering team colors.
    Zones:
    - Torso front & back: Micro-honeycomb / jacquard piqué knit grain
    - Collar & Cuffs: High-density vertical elastic ribbing
    - Flanks & Underarms: Laser-perforated breathable mesh grain
    - Shorts: Athletic micro-twill weave
    - Socks: Compression ribbed turnover knit
    - Sleeves: Fine athletic polyester knit grain
    """
    if not d.get("fabric_texture", True):
        return

    fabric_mask, _delta, fabric_idx, delta_flat = _fabric_texture_data(masks)
    if not len(fabric_idx):
        return

    # Only touch fabric pixels.  The old full-atlas float32 conversion allocated
    # a 64 MB temporary for every kit; precomputed flat indices keep this to a
    # small scoped copy with no repeated boolean-mask scans.
    arr = np.array(atlas)                      # uint8 RGBA copy
    rgb_flat = arr.reshape(-1, 4)[:, :3]
    patch = rgb_flat[fabric_idx].astype(np.float32)
    patch += delta_flat
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

        if d.get("heat_press_relief", True):
            sh_op = 145 if key == "sponsor" else 65
            _composite_with_relief(atlas, img, x, y, relief_depth=2, shadow_opacity=sh_op, highlight_opacity=35)
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
        shorts_c = d.get("shorts") or d["body"]
        b_col, b_white = _resolve_badge_color(d["badge"], shorts_c, d)
        bg_item = _prepare_stamp_item(
            d["badge"], *kit_regions.SHORTS_BADGE,
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
    side_mode = d.get("sleeve_sponsor_side", "both")
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
        else:
            bg_lum = 128.0

        logo_path = p
        if bg_lum < 130 or d.get("sleeve_sponsor_white"):
            # Dark sleeve fabric: pick white variant
            if not logo_path.stem.endswith("_white"):
                cand_w = logo_path.parent / f"{logo_path.stem}_white.png"
                if cand_w.is_file():
                    logo_path = cand_w
        else:
            # Light sleeve fabric: pick color variant
            if logo_path.stem.endswith("_white"):
                cand_c = logo_path.parent / f"{logo_path.stem[:-6]}.png"
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

        # Rotate along sleeve wrap orientation:
        rot_img = raw_scaled.rotate(wrap_angle, resample=Image.BICUBIC, expand=True)
        fw, fh = rot_img.size

        rx = int(cx - fw / 2)
        ry = int(cy - fh / 2)

        if d.get("heat_press_relief", True):
            _composite_with_relief(atlas, rot_img, rx, ry, relief_depth=2, shadow_opacity=135, highlight_opacity=40, mask=None)
        else:
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
