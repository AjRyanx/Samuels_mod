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
    "shorts_style": "solid",      # "solid", "side_stripe", "hem_tape"
    "shorts_accent": None,        # contrast stripe/tape colour on shorts
    "socks": None,                # None = same as body
    "socks_style": "solid",       # "solid", "turnover_hoop", "calf_band"
    "socks_accent": None,         # contrast hoop/band colour on socks
    "socks_tip": None,            # contrast tipping on socks turnover
    "collar": None,               # None = same as body
    "collar_tip": None,           # contrast tipping on collar ribbing
    "sponsor": None,              # path to a PNG logo (chest)
    "badge": None,                # path to a PNG logo (club badge)
    "supplier": None,             # path to a PNG logo (kit maker)
    "sponsor_white": False,       # True = flatten the logo to white
    "badge_white": False,
    "supplier_white": False,
    "sponsor_plate": False,       # draw a body-coloured plate behind the sponsor (False = seamless logo with no background)
}


def _hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in range(0, 6, 2))


def _mask_img(mask):
    """numpy bool mask -> single-channel PIL mask (255 where True)."""
    import numpy as np
    return Image.fromarray((mask * 255).astype("uint8"), "L")


# --------------------------------------------------------------------------- #
#  shirt-local design tile
# --------------------------------------------------------------------------- #
def build_tile(design):
    """Return a TILE x TILE RGBA tile: u across the shirt, v shoulder -> hem.

    The pattern is drawn with kit_gen's own 2D engine, so the wrapped kit is
    exactly the design the preview sheet shows.
    """
    d = dict(DEFAULT_DESIGN)
    d.update(design)
    body = tuple(d["body"])
    second = tuple(d["second"])

    canvas = Image.new("RGBA", (kit_gen.W, kit_gen.H), (0, 0, 0, 0))
    kit_gen.draw_pattern(canvas, d["pattern"], body, second, d["var"],
                         d["width_step"], third=d.get("third"))
    strength = [0.0, 0.15, 0.28, 0.40][d["gradient"] % 4]
    canvas = kit_gen.apply_gradient(canvas, strength)

    x0, y0, x1, y1 = _PREVIEW_SHIRT_BOX
    shirt = canvas.crop((x0, y0, x1, y1))
    return shirt.resize((TILE, TILE), Image.LANCZOS)


def _paint_shirt(atlas, tile, masks):
    """Paste the shirt-local tile into the front (upright) and back (180deg) islands."""
    boxes = kit_regions.region_boxes(masks)

    fx0, fy0, fx1, fy1 = boxes["body_front"]
    fw, fh = fx1 - fx0 + 1, fy1 - fy0 + 1
    front = tile.resize((fw, fh), Image.LANCZOS)
    fmask = _mask_img(masks["body_front"][fy0:fy1 + 1, fx0:fx1 + 1])
    atlas.paste(front, (fx0, fy0), fmask)

    bx0, by0, bx1, by1 = boxes["body_back"]
    bw, bh = bx1 - bx0 + 1, by1 - by0 + 1
    back = tile.rotate(180).resize((bw, bh), Image.LANCZOS)
    bmask = _mask_img(masks["body_back"][by0:by1 + 1, bx0:bx1 + 1])
    atlas.paste(back, (bx0, by0), bmask)


# --------------------------------------------------------------------------- #
#  main painter
# --------------------------------------------------------------------------- #
def render_kit(design, out_png, masks=None):
    """Paint `design` into the UV atlas and save a 2048x2048 RGBA PNG."""
    masks = masks if masks is not None else kit_regions.build_masks()

    d = dict(DEFAULT_DESIGN)
    d.update(design)
    body = tuple(d["body"])
    sleeve = tuple(d["sleeve"] or d["body"])
    shorts = tuple(d["shorts"] or d["body"])
    socks = tuple(d["socks"] or d["body"])
    collar = tuple(d["collar"] or d["body"])

    # fill everything with body colour first so mip bleeding at island edges
    # stays on-colour (the real kits are fully opaque too)
    atlas = Image.new("RGBA", (ATLAS, ATLAS), body + (255,))

    # shirt front + back
    _paint_shirt(atlas, build_tile(d), masks)

    # sleeves / shorts / socks / collar
    for region, colour in (("sleeve", sleeve), ("shorts", shorts),
                           ("socks", socks), ("collar", collar)):
        atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), colour + (255,)),
                    (0, 0), _mask_img(masks[region]))

    # ----------------------------------------------------------------------- #
    #  Modern 2026/2027 Streetwear Tailoring & Trim Layers
    # ----------------------------------------------------------------------- #
    import numpy as np

    # 1. Shoulder athletic racing stripes / raglan accents
    if d.get("sleeve_style") == "shoulder_stripe":
        sleeve_mask = masks["sleeve"]
        stripe_mask = np.zeros_like(sleeve_mask)
        acc_col = tuple(d.get("second") or d["body"]) + (255,)
        for x_off in (210, 240, 270):
            stripe_mask[120:320, x_off:x_off + 12] = True
        for x_off in (1766, 1796, 1826):
            stripe_mask[120:320, x_off:x_off + 12] = True
        stripe_mask = stripe_mask & sleeve_mask
        if np.any(stripe_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), acc_col),
                        (0, 0), _mask_img(stripe_mask))

    # 2. Contrast sleeve cuff bands + engineered tipping line (y=640..679 on short sleeve hem)
    cuff = d.get("cuff")
    if cuff:
        cuff_col = tuple(cuff) + (255,)
        sleeve_mask = masks["sleeve"]
        cuff_mask = np.zeros_like(sleeve_mask)
        cuff_mask[640:680, :] = sleeve_mask[640:680, :]
        if np.any(cuff_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), cuff_col),
                        (0, 0), _mask_img(cuff_mask))
        cuff_tip = d.get("cuff_tip")
        if cuff_tip and cuff_tip != cuff:
            tip_col = tuple(cuff_tip) + (255,)
            tip_mask = np.zeros_like(sleeve_mask)
            tip_mask[674:680, :] = sleeve_mask[674:680, :]
            if np.any(tip_mask):
                atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tip_col),
                            (0, 0), _mask_img(tip_mask))

    # 3. Collar tipping / engineered two-tone ribbing (y=1868..1882)
    collar_tip = d.get("collar_tip")
    if collar_tip and collar_tip != collar:
        col_tip_col = tuple(collar_tip) + (255,)
        collar_mask = masks["collar"]
        col_tip_mask = np.zeros_like(collar_mask)
        col_tip_mask[1868:1882, :] = collar_mask[1868:1882, :]
        if np.any(col_tip_mask):
            atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), col_tip_col),
                        (0, 0), _mask_img(col_tip_mask))

    # 4. Shorts lateral side stripes & hem tape
    shorts_style = d.get("shorts_style")
    shorts_accent = d.get("shorts_accent") or d.get("second")
    if shorts_accent and shorts_style in ("side_stripe", "hem_tape"):
        shorts_mask = masks["shorts"]
        sh_col = tuple(shorts_accent) + (255,)
        if shorts_style == "side_stripe":
            side_mask = np.zeros_like(shorts_mask)
            side_mask[:, 0:36] = True
            side_mask[:, 2012:2048] = True
            side_mask = side_mask & shorts_mask
            if np.any(side_mask):
                atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), sh_col),
                            (0, 0), _mask_img(side_mask))
        elif shorts_style == "hem_tape":
            hem_mask = np.zeros_like(shorts_mask)
            hem_mask[1935:1968, :] = True
            hem_mask = hem_mask & shorts_mask
            if np.any(hem_mask):
                atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), sh_col),
                            (0, 0), _mask_img(hem_mask))

    # 5. Socks turnover cuff & mid-calf athletic hoops
    socks_style = d.get("socks_style")
    socks_accent = d.get("socks_accent") or d.get("second")
    if socks_accent and socks_style in ("turnover_hoop", "calf_band"):
        socks_mask = masks["socks"]
        so_col = tuple(socks_accent) + (255,)
        if socks_style == "turnover_hoop":
            cuff_so = np.zeros_like(socks_mask)
            cuff_so[630:695, :] = True
            cuff_so = cuff_so & socks_mask
            if np.any(cuff_so):
                atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), so_col),
                            (0, 0), _mask_img(cuff_so))
                so_tip = d.get("socks_tip") or body
                so_tip_mask = np.zeros_like(socks_mask)
                so_tip_mask[690:696, :] = True
                so_tip_mask = so_tip_mask & socks_mask
                if np.any(so_tip_mask):
                    atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), tuple(so_tip) + (255,)),
                                (0, 0), _mask_img(so_tip_mask))
        elif socks_style == "calf_band":
            band_so = np.zeros_like(socks_mask)
            band_so[830:875, :] = True
            band_so = band_so & socks_mask
            if np.any(band_so):
                atlas.paste(Image.new("RGBA", (ATLAS, ATLAS), so_col),
                            (0, 0), _mask_img(band_so))

    # logos with runtime UV validation & collision adjustment
    sp_item = None
    if d.get("sponsor"):
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
        sup_item = _prepare_stamp_item(d["supplier"], *kit_regions.KIT_SUPPLIER,
                                       white=d.get("supplier_white"),
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

        atlas.alpha_composite(img, (x, y))

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
                     sponsor=None, badge_dir=None, badge=None):
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
                idx = (season + kit_dna._sponsor_hash(sponsor)) % len(choices)
                st["pattern"] = choices[idx]
    else:
        st = kit_dna.get_club_style(club, slot, season, sponsor=sponsor)

    if st:
        design.update(st)

    # the chest logo is stamped only for a signed sponsor, and chosen from the
    # FINAL body colour so a dark kit gets the white logo variant
    if brand:
        white = kit_gen.lum(design["body"]) < 120
        if white:
            design["sponsor_white"] = True
            design.pop("sponsor_dark", None)
        else:
            design["sponsor_white"] = False
            # If sponsor_dark was explicitly set, check that it still has good contrast (> 3.0:1) with body
            if design.get("sponsor_dark"):
                dark_col = design["sponsor_dark"] if isinstance(design["sponsor_dark"], (tuple, list)) else (15, 25, 45)
                l1 = 0.2126 * design["body"][0] + 0.7152 * design["body"][1] + 0.0722 * design["body"][2]
                l2 = 0.2126 * dark_col[0] + 0.7152 * dark_col[1] + 0.0722 * dark_col[2]
                ratio = (max(l1, l2) + 12.5) / (min(l1, l2) + 12.5)
                if ratio < 3.0:
                    design.pop("sponsor_dark", None)
                    design["sponsor_white"] = True
                    white = True

        design["sponsor"] = str(Path(logo_dir) / (brand + ("_white" if white else "") + ".png"))
        if not white and not design.get("sponsor_dark"):
            # Check if regular logo has sufficient contrast (> 3.2:1)
            try:
                sim = Image.open(design["sponsor"]).convert("RGBA")
                arr = np.array(sim)
                opaque = arr[:, :, 3] > 128
                if np.any(opaque):
                    s_col = tuple(int(v) for v in np.median(arr[opaque, :3], axis=0))
                    l1 = 0.2126 * design["body"][0] + 0.7152 * design["body"][1] + 0.0722 * design["body"][2]
                    l2 = 0.2126 * s_col[0] + 0.7152 * s_col[1] + 0.0722 * s_col[2]
                    ratio = (max(l1, l2) + 12.5) / (min(l1, l2) + 12.5)
                    if ratio < 3.2:
                        design["sponsor_dark"] = (15, 25, 45)
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
    return design


def render_club(club, season, out_png, logo_dir, masks=None, brand_files=None, slot=1,
                style=None, sponsor=None, badge_dir=None, badge=None):
    """Render one club's generated kit for a season; returns (path_or_image, design)."""
    design = design_from_club(club, season, logo_dir, slot=slot,
                              brand_files=brand_files, style=style, sponsor=sponsor,
                              badge_dir=badge_dir, badge=badge)
    res = render_kit(design, str(out_png) if out_png else None, masks=masks)
    return res, design


def render_kit_set(club, season, outdir, logo_dir, masks=None, brand_files=None,
                   sponsor=None, badge_dir=None, badge=None, slots=(1, 2, 3, "g1", "g2")):
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
                                badge_dir=badge_dir, badge=badge)
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
        cm[264:283, :] = sm[264:283, :]
        if np.any(cm):
            cuff_col = tuple(cuff) + (255,)
            cimg = Image.fromarray((cm * 255).astype("uint8"), "L")
            canvas.paste(Image.new("RGBA", (W, H), cuff_col), (0, 0), cimg)
        cuff_tip = design.get("cuff_tip")
        if cuff_tip and cuff_tip != cuff:
            tip_mask = np.zeros_like(sm)
            tip_mask[279:283, :] = sm[279:283, :]
            if np.any(tip_mask):
                timg = Image.fromarray((tip_mask * 255).astype("uint8"), "L")
                canvas.paste(Image.new("RGBA", (W, H), tuple(cuff_tip) + (255,)), (0, 0), timg)

    d = ImageDraw.Draw(canvas)
    trim = tuple(design.get("collar") or body)
    d.polygon([(200, 40), (240, 86), (280, 40), (268, 40), (240, 70), (212, 40)],
              fill=trim + (255,))
    collar_tip = design.get("collar_tip")
    if collar_tip and collar_tip != trim:
        d.line([(200, 40), (240, 86), (280, 40)], fill=tuple(collar_tip) + (255,), width=2)

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
            if design.get("supplier_white"):
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
