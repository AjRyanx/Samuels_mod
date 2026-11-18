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

from PIL import Image, ImageDraw, ImageFont

import kit_gen
import kit_regions

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
    "shorts": None,               # None = same as body
    "socks": None,                # None = same as body
    "collar": None,               # None = same as body
    "sponsor": None,              # path to a PNG logo (chest)
    "badge": None,                # path to a PNG logo (club badge)
    "supplier": None,             # path to a PNG logo (kit maker)
    "sponsor_white": False,       # True = flatten the logo to white
    "badge_white": False,
    "supplier_white": False,
    "sponsor_plate": True,        # draw a body-coloured plate behind the sponsor
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

    # logos
    if d.get("sponsor"):
        _stamp_area(atlas, d["sponsor"], *kit_regions.CHEST_SPONSOR,
                    white=d.get("sponsor_white"),
                    plate=body if d.get("sponsor_plate") else None)
    if d.get("badge"):
        _stamp_area(atlas, d["badge"], *kit_regions.CLUB_BADGE,
                    white=d.get("badge_white"))
    if d.get("supplier"):
        _stamp_area(atlas, d["supplier"], *kit_regions.KIT_SUPPLIER,
                    white=d.get("supplier_white"))

    atlas.save(out_png)
    return out_png


def _stamp_area(atlas, logo_path, cx, cy, area, white=False, plate=None):
    """Place a logo centred on (cx, cy) scaled so w*h ~= area (like the tool).

    `plate` optionally paints a flat rectangle of that colour behind the logo
    (the Kit Creator reserves a flat zone behind the sponsor so stripes and
    overlays never run through the logo).
    """
    logo = Image.open(logo_path).convert("RGBA")
    if white:
        logo = _flatten_white(logo)
    w, h = logo.size
    scale = (float(area) / max(1, w * h)) ** 0.5
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    logo = logo.resize((nw, nh), Image.LANCZOS)
    x, y = int(cx - nw / 2), int(cy - nh / 2)

    if plate is not None:
        pad_x, pad_y = int(nw * 0.10), int(nh * 0.35)
        draw = ImageDraw.Draw(atlas)
        draw.rectangle([x - pad_x, y - pad_y, x + nw + pad_x, y + nh + pad_y],
                       fill=tuple(plate) + (255,))

    atlas.alpha_composite(logo, (x, y))


def _flatten_white(logo):
    """Return a white silhouette keeping the logo's alpha."""
    import numpy as np
    a = np.asarray(logo).copy()
    a[:, :, 0] = 255
    a[:, :, 1] = 255
    a[:, :, 2] = 255
    return Image.fromarray(a, "RGBA")


# --------------------------------------------------------------------------- #
#  generator -> design
# --------------------------------------------------------------------------- #
# Home / away / third ("p1/p2/p3") each get an independent, deterministic roll.
# Slot 1 keeps the original salt, so the already-verified home kit is unchanged.
_SLOT_SALT = {1: "kitgen-v1", 2: "kitgen-v1-away", 3: "kitgen-v1-third"}

# Which of the club's three colours leads each kit: (body, pattern, accent).
_SLOT_ROLES = {
    1: ("primary", "secondary", "accent"),      # home   - club colour dominant
    2: ("secondary", "primary", "accent"),      # away   - the second colour leads
    3: ("accent", "primary", "secondary"),      # third  - the accent colour leads
}

# Explicit per-club styling, keyed by team id then slot.  It pins the palette
# per kit and gives a POOL of on-brand, non-basic patterns to choose from: with
# no sponsor the first pattern (the approved look) is used, and a signed sponsor
# picks a DIFFERENT one, so every deal gives a fresh but still recognisable kit.
# Pool entries are either a legacy named pattern or a kit_patterns catalog code
# ("127", "127-B", ...) - see generator/kit_patterns.py.
#
# The three pools are deliberately drawn from DIFFERENT visual families so the
# home, away and third kits never look like each other:
#   home  = linear (stripes, pinstripes, sashes, bands, hoops)
#   away  = angular (shards, polygons, chevrons, diamonds, hex, bricks)
#   third = organic / cultural (marble, fluid, waves, tiles, knotwork)
KIT_STYLE = {
    102: {  # Chelsea
        # home: mainly blue with a touch of white and a tiny red
        1: {
            "body": (0, 76, 165), "second": (245, 245, 245), "third": (200, 32, 48),
            "patterns": [
                "pinstripe",                                    # approved default
                # stripes / pinstripes
                "093", "085", "097", "105", "118", "124",
                # sashes / bands
                "005", "022", "087", "090", "095", "098", "103", "113", "119",
                # woven / checks / hoops
                "067", "102", "114", "084", "091",
            ],
            "sleeve": (245, 245, 245), "shorts": (0, 76, 165),
            "socks": (245, 245, 245), "collar": (200, 32, 48),
            "gradient": 0,
        },
        # away: black with a touch of blue, bold angular geometry
        2: {
            "body": (16, 17, 21), "second": (10, 63, 133), "third": (0, 76, 165),
            "patterns": [
                "chevron",                                      # approved default
                # shards / prisms / poly
                "001", "002", "003", "004", "008", "020", "021", "023", "029", "038",
                # chevrons / zigzags / peaks / wedges
                "010", "011", "017", "024", "030", "039",
                # lattice / stars / bricks / shield
                "013", "019", "027", "033", "037", "040",
            ],
            "sleeve": (16, 17, 21), "shorts": (16, 17, 21),
            "socks": (10, 63, 133), "collar": (10, 63, 133),
            "gradient": 1,
        },
        # third: mainly white with a touch of blue and a tiny red
        3: {
            "body": (245, 246, 248), "second": (10, 63, 133), "third": (200, 32, 48),
            "patterns": [
                "fadegeo",                                      # approved default
                # fluid / organic
                "041", "043", "044", "047", "052", "064", "074", "195", "204", "205",
                # tech / grid
                "127", "131", "142", "153",
                # cultural / architectural
                "168", "169", "170", "176", "177", "178", "179", "189", "197",
            ],
            "sleeve": (10, 63, 133), "shorts": (245, 246, 248),
            "socks": (245, 246, 248), "collar": (200, 32, 48),
            "gradient": 0,
        },
    },
}


def design_from_club(club, season, logo_dir, slot=1, brand_files=None, style=None,
                     sponsor=None):
    """Turn a club row + season + kit slot (1=home, 2=away, 3=third) into a design.

    The rolls are taken in the same order as kit_gen.preview() so the wrapped
    kit matches the preview sheet exactly: pick_design, jitter_body, brand.
    Shorts/socks/collar colours are derived from the already-rolled fields (no
    extra RNG draws), so the Lua side stays bit-compatible.

    `sponsor` is the signed sponsor's brand name.  When given it (a) forces the
    chest logo to that brand and (b) shifts the design seed, so a new deal gives
    a fresh design from the club's on-brand pattern pool.

    `style` (or KIT_STYLE[club_id][slot]) may override any of body/second/third/
    patterns/sleeve/shorts/socks/collar/gradient/var/width_step.
    """
    if slot not in _SLOT_ROLES:
        raise ValueError("slot must be 1 (home), 2 (away) or 3 (third)")

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
        "sleeve": sleeve, "shorts": shorts, "socks": socks, "collar": collar,
        "sponsor": None, "sponsor_white": False,
        "slot": slot, "_brand": brand, "_roll": roll, "_sponsor": sponsor,
    }

    st = KIT_STYLE.get(club["id"], {}).get(slot) if style is None else style
    if st:
        st = dict(st)                       # never mutate the module table
        pool = st.pop("patterns", None)
        if pool:
            # no sponsor -> the approved first pattern; a signed sponsor -> a
            # DIFFERENT pattern that is guaranteed to change again every season
            # of the deal (so a 2-year deal still gives a new kit next season),
            # and never falls back to the no-sponsor look.
            if not sponsor:
                st["pattern"] = pool[0]
            else:
                choices = [x for x in pool if x != pool[0]] or pool
                brng = kit_gen.season_rng(club["id"], 0, salt="brandpick|" + sponsor)
                base = brng.randrange(len(choices))
                st["pattern"] = choices[(base + season) % len(choices)]
        design.update(st)

    # the chest logo is stamped only for a signed sponsor, and chosen from the
    # FINAL body colour so a dark kit gets the white logo variant
    if brand:
        white = kit_gen.lum(design["body"]) < 120
        design["sponsor"] = str(Path(logo_dir) / (brand + ("_white" if white else "") + ".png"))
    else:
        design["sponsor"] = None
    return design


def render_club(club, season, out_png, logo_dir, masks=None, brand_files=None, slot=1,
                style=None, sponsor=None):
    """Render one club's generated kit for a season; returns (path, design)."""
    design = design_from_club(club, season, logo_dir, slot=slot,
                              brand_files=brand_files, style=style, sponsor=sponsor)
    render_kit(design, str(out_png), masks=masks)
    return str(out_png), design


def render_kit_set(club, season, outdir, logo_dir, masks=None, brand_files=None,
                   sponsor=None):
    """Render the full home/away/third set for a club + season.

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
    for slot in (1, 2, 3):
        atlas = outdir / f"u{team:04d}p{slot}_atlas.png"
        _, design = render_club(club, season, atlas, logo_dir, masks=masks,
                                brand_files=brand_files, slot=slot, sponsor=sponsor)
        preview = uv_contact_sheet(atlas, outdir / f"u{team:04d}p{slot}_preview.png",
                                   masks=masks)
        mockup(design, club["name"], season,
               outdir / f"u{team:04d}p{slot}_mockup.png")
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

    d = ImageDraw.Draw(canvas)
    trim = tuple(design.get("collar") or body)
    d.polygon([(200, 40), (240, 86), (280, 40), (268, 40), (240, 70), (212, 40)],
              fill=trim + (255,))

    if design.get("sponsor"):
        logo = Image.open(design["sponsor"]).convert("RGBA")
        if design.get("sponsor_white"):
            logo = _flatten_white(logo)
        s = min(190 / logo.width, 60 / logo.height)
        logo = logo.resize((max(1, int(logo.width * s)), max(1, int(logo.height * s))))
        d.rounded_rectangle([118, 160, 362, 236], radius=10, fill=body + (255,))
        canvas.alpha_composite(logo, (240 - logo.width // 2, 170))

    # shorts / socks swatches along the bottom strip
    def swatch(x, colour, label):
        d.rectangle([x, H + 6, x + 44, H + 38], fill=tuple(colour) + (255,))
        d.text((x + 50, H + 14), label, fill=(210, 212, 218, 255))

    swatch(10, design.get("shorts") or body, "shorts")
    swatch(150, design.get("socks") or body, "socks")
    swatch(290, design.get("collar") or body, "collar")
    d.text((10, 10), f"{club_name} S{season} p{design.get('slot', 1)} {design['pattern']}",
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
        _, design = render_club(club, season, out, logo_dir, masks=masks, slot=slot)
        sheet = uv_contact_sheet(out, outdir / f"{name}_preview.png", masks=masks)
        print(f"wrote {out}")
        print(f"wrote {sheet}")
        print(_describe(design, season, club))
        sys.exit(0)

    for slot, atlas, preview, design in render_kit_set(club, season, outdir,
                                                       logo_dir, masks=masks):
        print(f"wrote {atlas}")
        print(f"wrote {preview}")
        print(_describe(design, season, club))
