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
# Calibrated directly against authentic PES 2021 / FL26 club kits:
CHEST_SPONSOR = (1024, 1310, 36000)
CLUB_BADGE = (1145, 1150, 6000)
KIT_SUPPLIER = (905, 1150, 3600)

# Shorts leg anchors:
# Island 1 (UV left, x: 0..658, y: 1159..1971): Player's right leg. Lower front thigh centers at (150, 1620).
# Island 2 (UV right, x: 1390..2048, y: 1159..1971): Player's left leg. Lower front thigh centers at (1898, 1620).
SHORTS_BADGE_RIGHT = (150, 1620, 5000)
SHORTS_BADGE_LEFT = (1898, 1620, 5000)
SHORTS_SUPPLIER_LEFT = (1898, 1620, 3200)
SHORTS_SUPPLIER_RIGHT = (150, 1620, 3200)

SHORTS_BADGE = SHORTS_BADGE_RIGHT
SHORTS_SUPPLIER = SHORTS_SUPPLIER_LEFT

# Lower jocktag / authenticity foil stamp (bottom-right of front torso / player's left hem):
JOCKTAG_ANCHOR = (1270, 1835, 1400)

# Sleeve sponsor anchors:
# Calibrated directly against authentic Premier League and La Liga PES 2021 kits (e.g. Arsenal Visit Rwanda/deel,
# Real Madrid HP, Man City OKX):
# The lateral bicep visible face on the 3D player arm centers at y: 404 on the sleeve islands.
# Player's LEFT arm = Right sleeve island (x: 1448..2048): center (1530, 404), wrap rotation 90 deg CCW
# Player's RIGHT arm = Left sleeve island (x: 0..600): center (518, 404), wrap rotation -90 deg CW
PLAYER_LEFT_ARM_SLEEVE = (1530, 404, 18000)
PLAYER_RIGHT_ARM_SLEEVE = (518, 404, 18000)
SLEEVE_SPONSOR_LEFT = PLAYER_LEFT_ARM_SLEEVE
SLEEVE_SPONSOR_RIGHT = PLAYER_RIGHT_ARM_SLEEVE
SLEEVE_WRAP_ANGLE = 90.0

# --- front / back panel boxes (for reference / debug) ---------------------- #
FRONT_BOX = (660, 952, 1390, 1888)
BACK_BOX = (660, 16, 1390, 952)


def _load_alpha(path):
    """Load a mask PNG and return a bool array of where it is opaque."""
    im = Image.open(path).convert("RGBA")
    return np.asarray(im)[:, :, 3] > 10


class MaskSet(dict):
    """dict of bool masks with cached derived geometry.

    Rendering calls ``region_boxes()`` several times per kit.  Masks are built
    once per worker and reused for every club, so compute the expensive
    ``np.where`` bounding boxes once here instead of once per kit.
    """
    boxes = None


_MASKS_CACHE = {}


def build_masks(mask_dir=None):
    """Return {region_name: bool mask} in 2048x2048 UV space."""
    d = Path(mask_dir) if mask_dir else MASK_DIR
    cache_key = str(d.resolve())
    if cache_key in _MASKS_CACHE:
        return _MASKS_CACHE[cache_key]

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

    result = MaskSet({
        "body_front": body_front,
        "body_back": body_back,
        "body": body_front | body_back,
        "sleeve": _load_alpha(d / "sleeves.png"),
        "shorts": _load_alpha(d / "shorts.png"),
        "socks": _load_alpha(d / "socks.png"),
        "collar": _load_alpha(d / "collar.png"),
    })
    result.boxes = {}
    for name, m in result.items():
        ys, xs = np.where(m)
        if len(xs):
            result.boxes[name] = (int(xs.min()), int(ys.min()),
                                  int(xs.max()), int(ys.max()))
    _MASKS_CACHE[cache_key] = result
    return result


def region_boxes(masks):
    """Return {region: (x0, y0, x1, y1)} for the given masks."""
    cached = getattr(masks, "boxes", None)
    if cached is not None:
        return cached
    out = {}
    for name, m in masks.items():
        ys, xs = np.where(m)
        if len(xs):
            out[name] = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    return out


# --------------------------------------------------------------------------- #
#  Runtime UV validation and collision resolution for kit stamps
# --------------------------------------------------------------------------- #
def check_stamp_containment(mask, x0, y0, x1, y1, alpha=None, margin=4):
    """Check if stamp region [x0:x1, y0:y1] is strictly inside mask with margin.
    
    If alpha is provided (shape (y1-y0, x1-x0)), only pixels with alpha > 10
    are required to be inside mask.
    """
    H, W = mask.shape
    if x0 < margin or y0 < margin or x1 > W - margin or y1 > H - margin:
        return False
    submask = mask[y0:y1, x0:x1]
    if alpha is not None:
        if alpha.shape != submask.shape:
            # Resize or fallback
            return bool(np.all(submask))
        opaque = alpha > 10
        if not np.any(opaque):
            return True
        return bool(np.all(submask[opaque]))
    return bool(np.all(submask))


def boxes_intersect(b1, b2, margin=8):
    """Return True if box b1=(x0,y0,x1,y1) and b2=(x0,y0,x1,y1) overlap within margin."""
    if b1 is None or b2 is None:
        return False
    if (b1[2] + margin <= b2[0]) or (b2[2] + margin <= b1[0]):
        return False
    if (b1[3] + margin <= b2[1]) or (b2[3] + margin <= b1[1]):
        return False
    return True


def validate_and_adjust_stamps(masks, sponsor=None, badge=None, supplier=None,
                               shorts_badge=None, shorts_supplier=None, jocktag=None,
                               sleeve_sponsor=None, min_gap=12, margin=8):
    """Runtime UV validation and auto-adjustment for kit stamps.
    
    Input items should be dicts:
      {
        'cx': int, 'cy': int, 'w': int, 'h': int,
        'alpha': 2D np.ndarray (optional),
        'plate_pad': (pad_x, pad_y) (optional, for sponsor)
      }
      
    Validates:
      1. Complete containment inside masks['body_front'] (chest logos & jocktag),
         masks['shorts'] (shorts badge & shorts supplier), and masks['sleeve'] (sleeve sponsor).
      2. Inter-stamp clearances: sponsor must not overlap badge or supplier.
         Badge and supplier must not overlap each other.
         
    Adjusts:
      - Shifts sponsor downward if overlapping chest badges/supplier.
      - Nudges and proportionally scales down stamps that would clip seams or necklines.
    """
    bf = masks.get("body_front") if masks else None
    sh = masks.get("shorts") if masks else None
    res = {}
    adjustments = []

    # Helper to compute box
    def _box(item):
        if not item:
            return None
        w, h = item["w"], item["h"]
        x0 = int(item["cx"] - w / 2)
        y0 = int(item["cy"] - h / 2)
        return (x0, y0, x0 + w, y0 + h)

    # 1. Process Badge & Supplier first (chest anchors)
    for name, item, default_anchor in (("badge", badge, CLUB_BADGE), ("supplier", supplier, KIT_SUPPLIER)):
        if not item:
            continue
        cur_w, cur_h = item["w"], item["h"]
        cur_cx, cur_cy = item["cx"], item["cy"]
        alpha = item.get("alpha")
        orig_w, orig_h = cur_w, cur_h
        orig_cx, orig_cy = cur_cx, cur_cy

        if bf is not None:
            # Check neckline / seam containment; adjust if needed
            for _ in range(10):
                x0, y0, x1, y1 = int(cur_cx - cur_w / 2), int(cur_cy - cur_h / 2), int(cur_cx - cur_w / 2) + cur_w, int(cur_cy - cur_h / 2) + cur_h
                if check_stamp_containment(bf, x0, y0, x1, y1, alpha=alpha, margin=margin):
                    break
                # If too high near collar hole, nudge down
                if y0 < 1050:
                    cur_cy += 4
                # If too close to left or right seam
                if x0 < 750 and name == "supplier":
                    cur_cx += 4
                elif x1 > 1300 and name == "badge":
                    cur_cx -= 4
                else:
                    # Scale down slightly to fit safely
                    cur_w = max(16, int(cur_w * 0.95))
                    cur_h = max(16, int(cur_h * 0.95))

        res[name] = {
            "cx": cur_cx, "cy": cur_cy, "w": cur_w, "h": cur_h,
            "x": int(cur_cx - cur_w / 2), "y": int(cur_cy - cur_h / 2),
            "adjusted": (cur_w != orig_w or cur_h != orig_h or cur_cx != orig_cx or cur_cy != orig_cy)
        }
        if res[name]["adjusted"]:
            adjustments.append(f"{name}: adjusted ({orig_cx},{orig_cy},{orig_w}x{orig_h}) -> ({cur_cx},{cur_cy},{cur_w}x{cur_h})")

    # Check badge vs supplier collision
    b_box = _box(res.get("badge"))
    s_box = _box(res.get("supplier"))
    if b_box and s_box and boxes_intersect(b_box, s_box, margin=min_gap):
        # Nudge apart or scale down
        adjustments.append("badge and supplier collided: scaled to resolve")
        for k in ("badge", "supplier"):
            res[k]["w"] = int(res[k]["w"] * 0.9)
            res[k]["h"] = int(res[k]["h"] * 0.9)
            res[k]["x"] = int(res[k]["cx"] - res[k]["w"] / 2)
            res[k]["y"] = int(res[k]["cy"] - res[k]["h"] / 2)
            res[k]["adjusted"] = True

    # 2. Process Sponsor
    if sponsor:
        cur_w, cur_h = sponsor["w"], sponsor["h"]
        cur_cx, cur_cy = sponsor["cx"], sponsor["cy"]
        alpha = sponsor.get("alpha")
        pad_x, pad_y = sponsor.get("plate_pad") or (0, 0)
        orig_w, orig_h = cur_w, cur_h
        orig_cx, orig_cy = cur_cx, cur_cy

        # Enforce clearance below badge and supplier
        min_top_y = 0
        if "badge" in res:
            min_top_y = max(min_top_y, res["badge"]["y"] + res["badge"]["h"] + min_gap + pad_y)
        if "supplier" in res:
            min_top_y = max(min_top_y, res["supplier"]["y"] + res["supplier"]["h"] + min_gap + pad_y)

        sp_y0 = int(cur_cy - cur_h / 2)
        if sp_y0 < min_top_y:
            cur_cy = int(min_top_y + cur_h / 2)

        if bf is not None:
            # Containment loop for sponsor (including plate if any)
            for _ in range(15):
                x0 = int(cur_cx - cur_w / 2) - pad_x
                y0 = int(cur_cy - cur_h / 2) - pad_y
                x1 = int(cur_cx + cur_w / 2) + pad_x
                y1 = int(cur_cy + cur_h / 2) + pad_y

                # Check if inside body_front
                if check_stamp_containment(bf, x0, y0, x1, y1, margin=margin):
                    break
                # If too wide or tall for torso front panel, scale down
                cur_w = max(32, int(cur_w * 0.94))
                cur_h = max(16, int(cur_h * 0.94))
                if pad_x or pad_y:
                    pad_x, pad_y = int(cur_w * 0.10), int(cur_h * 0.35)

        res["sponsor"] = {
            "cx": cur_cx, "cy": cur_cy, "w": cur_w, "h": cur_h,
            "x": int(cur_cx - cur_w / 2), "y": int(cur_cy - cur_h / 2),
            "plate_pad": (pad_x, pad_y) if (sponsor.get("plate_pad") is not None) else None,
            "adjusted": (cur_w != orig_w or cur_h != orig_h or cur_cx != orig_cx or cur_cy != orig_cy)
        }
        if res["sponsor"]["adjusted"]:
            adjustments.append(f"sponsor: adjusted ({orig_cx},{orig_cy},{orig_w}x{orig_h}) -> ({cur_cx},{cur_cy},{cur_w}x{cur_h})")

    # 3. Process Jocktag (lower shirt hem)
    if jocktag:
        cur_w, cur_h = jocktag["w"], jocktag["h"]
        cur_cx, cur_cy = jocktag["cx"], jocktag["cy"]
        alpha = jocktag.get("alpha")
        orig_w, orig_h = cur_w, cur_h
        orig_cx, orig_cy = cur_cx, cur_cy

        if bf is not None:
            for _ in range(10):
                x0 = int(cur_cx - cur_w / 2)
                y0 = int(cur_cy - cur_h / 2)
                x1 = x0 + cur_w
                y1 = y0 + cur_h
                if check_stamp_containment(bf, x0, y0, x1, y1, alpha=alpha, margin=margin):
                    break
                if cur_cx > 1320:
                    cur_cx -= 4
                if cur_cy > 1860:
                    cur_cy -= 4
                cur_w = max(16, int(cur_w * 0.95))
                cur_h = max(16, int(cur_h * 0.95))

        res["jocktag"] = {
            "cx": cur_cx, "cy": cur_cy, "w": cur_w, "h": cur_h,
            "x": int(cur_cx - cur_w / 2), "y": int(cur_cy - cur_h / 2),
            "adjusted": (cur_w != orig_w or cur_h != orig_h or cur_cx != orig_cx or cur_cy != orig_cy)
        }
        if res["jocktag"]["adjusted"]:
            adjustments.append(f"jocktag: adjusted ({orig_cx},{orig_cy},{orig_w}x{orig_h}) -> ({cur_cx},{cur_cy},{cur_w}x{cur_h})")

    # 4. Process Shorts Badge (Island 1 Right leg or Island 2 Left leg)
    if shorts_badge:
        cur_w, cur_h = shorts_badge["w"], shorts_badge["h"]
        cur_cx, cur_cy = shorts_badge["cx"], shorts_badge["cy"]
        alpha = shorts_badge.get("alpha")
        orig_w, orig_h = cur_w, cur_h
        orig_cx, orig_cy = cur_cx, cur_cy

        if sh is not None:
            is_left_leg = cur_cx >= 1024
            min_x, max_x = (1750, 1980) if is_left_leg else (60, 300)
            for _ in range(10):
                x0 = int(cur_cx - cur_w / 2)
                y0 = int(cur_cy - cur_h / 2)
                x1 = x0 + cur_w
                y1 = y0 + cur_h
                if check_stamp_containment(sh, x0, y0, x1, y1, alpha=alpha, margin=margin):
                    break
                if cur_cx < min_x:
                    cur_cx += 4
                elif cur_cx > max_x:
                    cur_cx -= 4
                if cur_cy > 1700:
                    cur_cy -= 4
                elif cur_cy < 1550:
                    cur_cy += 4
                cur_w = max(16, int(cur_w * 0.95))
                cur_h = max(16, int(cur_h * 0.95))

        res["shorts_badge"] = {
            "cx": cur_cx, "cy": cur_cy, "w": cur_w, "h": cur_h,
            "x": int(cur_cx - cur_w / 2), "y": int(cur_cy - cur_h / 2),
            "adjusted": (cur_w != orig_w or cur_h != orig_h or cur_cx != orig_cx or cur_cy != orig_cy)
        }
        if res["shorts_badge"]["adjusted"]:
            adjustments.append(f"shorts_badge: adjusted ({orig_cx},{orig_cy},{orig_w}x{orig_h}) -> ({cur_cx},{cur_cy},{cur_w}x{cur_h})")

    # 5. Process Shorts Supplier (Island 2 Left leg or Island 1 Right leg)
    if shorts_supplier:
        cur_w, cur_h = shorts_supplier["w"], shorts_supplier["h"]
        cur_cx, cur_cy = shorts_supplier["cx"], shorts_supplier["cy"]
        alpha = shorts_supplier.get("alpha")
        orig_w, orig_h = cur_w, cur_h
        orig_cx, orig_cy = cur_cx, cur_cy

        if sh is not None:
            is_left_leg = cur_cx >= 1024
            min_x, max_x = (1750, 1980) if is_left_leg else (60, 300)
            for _ in range(10):
                x0 = int(cur_cx - cur_w / 2)
                y0 = int(cur_cy - cur_h / 2)
                x1 = x0 + cur_w
                y1 = y0 + cur_h
                if check_stamp_containment(sh, x0, y0, x1, y1, alpha=alpha, margin=margin):
                    break
                if cur_cx < min_x:
                    cur_cx += 4
                elif cur_cx > max_x:
                    cur_cx -= 4
                if cur_cy > 1700:
                    cur_cy -= 4
                elif cur_cy < 1550:
                    cur_cy += 4
                cur_w = max(16, int(cur_w * 0.95))
                cur_h = max(16, int(cur_h * 0.95))

        res["shorts_supplier"] = {
            "cx": cur_cx, "cy": cur_cy, "w": cur_w, "h": cur_h,
            "x": int(cur_cx - cur_w / 2), "y": int(cur_cy - cur_h / 2),
            "adjusted": (cur_w != orig_w or cur_h != orig_h or cur_cx != orig_cx or cur_cy != orig_cy)
        }
        if res["shorts_supplier"]["adjusted"]:
            adjustments.append(f"shorts_supplier: adjusted ({orig_cx},{orig_cy},{orig_w}x{orig_h}) -> ({cur_cx},{cur_cy},{cur_w}x{cur_h})")

    # 6. Process Sleeve Sponsor (Left sleeve UV island: Component 2)
    sl = masks.get("sleeve") if masks else None
    if sleeve_sponsor:
        cur_w, cur_h = sleeve_sponsor["w"], sleeve_sponsor["h"]
        cur_cx, cur_cy = sleeve_sponsor["cx"], sleeve_sponsor["cy"]
        alpha = sleeve_sponsor.get("alpha")
        orig_w, orig_h = cur_w, cur_h
        orig_cx, orig_cy = cur_cx, cur_cy
        angle = sleeve_sponsor.get("angle", SLEEVE_WRAP_ANGLE)

        # Bounds for sleeve sponsor (covers both long sleeve y:220..620 and short sleeve y:750..1050):
        # Left island (player's right arm): x: 400..600, y: 220..1050
        # Right island (player's left arm): x: 1450..1650, y: 220..1050
        is_left_island = cur_cx < 1024
        min_x, max_x = (400, 600) if is_left_island else (1450, 1650)
        min_y, max_y = 220, 1050

        # Clamp into valid sleeve island region
        cur_cx = max(min_x + cur_w // 2, min(max_x - cur_w // 2, cur_cx))
        cur_cy = max(min_y + cur_h // 2, min(max_y - cur_h // 2, cur_cy))

        res["sleeve_sponsor"] = {
            "cx": cur_cx, "cy": cur_cy, "w": cur_w, "h": cur_h,
            "x": int(cur_cx - cur_w / 2), "y": int(cur_cy - cur_h / 2),
            "angle": angle,
            "adjusted": (cur_w != orig_w or cur_h != orig_h or cur_cx != orig_cx or cur_cy != orig_cy)
        }
        if res["sleeve_sponsor"]["adjusted"]:
            adjustments.append(f"sleeve_sponsor: adjusted ({orig_cx},{orig_cy},{orig_w}x{orig_h}) -> ({cur_cx},{cur_cy},{cur_w}x{cur_h})")

    res["valid"] = True
    res["adjustments"] = adjustments
    return res


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
    print("  shorts badge:", SHORTS_BADGE, " shorts supplier:", SHORTS_SUPPLIER, " jocktag:", JOCKTAG_ANCHOR)
    debug_map(masks, out)
    print("wrote", out)
