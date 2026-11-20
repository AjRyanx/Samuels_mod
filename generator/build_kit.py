#!/usr/bin/env python3
r"""build_kit.py - render a club's home/away/third kits and pack them to .ftex.

Pipeline
--------
    club + season + slot  ->  kit_render.render_kit_set   (2048x2048 atlas PNGs)
                          ->  ftex_io.image_to_ftex        (BC3/DXT5, 12 mips)
                          ->  u<team>p<slot>.ftex
                          ->  (optional) SiderAddons/content/KitGenerator/active override

The .ftex header (version / texture_type / hashes / size / format) is inherited
from a real PES kit ("base"), so the output is byte-for-byte the same *kind* of
file the game already loads.  Any real kit works as the base: the three Chelsea
slots share an identical 64-byte header.

Usage
-----
    python build_kit.py <club_id> <season> <outdir> [--slots 1,2,3] [--install]
    python build_kit.py <club_id> <season> <outdir> --install --game-root "C:\\...\\SP Football Life 2027"

Notes
-----
* Installing writes ONLY to
      <game>\\SiderAddons\\content\\KitGenerator\\active\\
  Sider's KitGenerator.lua serves that folder during Master League.  The static
  licensed kits under content/kits are never overwritten, so Exhibition and
  every other non-career mode keep their authentic kits.
* Nothing is overwritten without a timestamped .bak next to it.
"""
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

import ftex_io
import kit_gen
import kit_render

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

DEFAULT_GAME_ROOT = Path(r"C:\Games\SP Football Life 2027")
# Any real PES kit works as a header template; the three Chelsea slots share one.
DEFAULT_BASE = Path(
    r"C:\Games\SP Football Life 2027\SiderAddons\content\kits"
    r"\Premier League\Chelsea\p1\u0102p1.ftex")

ACTIVE_SUBDIR = Path("SiderAddons/content/KitGenerator/active")


def _find_kitserver_folder(club_id, game_root):
    """Find the GDB folder for club_id if managed by Sider's Kitserver."""
    map_txt = Path(game_root) / "SiderAddons/content/kits/map.txt"
    if not map_txt.exists():
        return None
    try:
        with open(map_txt, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split(",", 1)]
                if len(parts) == 2 and parts[0].isdigit() and int(parts[0]) == club_id:
                    rel_dir = parts[1].strip().strip('"').strip("'")
                    target = Path(game_root) / "SiderAddons/content/kits" / rel_dir
                    if target.exists():
                        return target
    except Exception:
        pass
    return None


def _load_club(club_id, sider=None):
    """A club row for `club_id`: the curated clubs.csv row if there is one, else
    a row resolved from the game's own kit data (see club_resolver.py)."""
    clubs = kit_gen.load_clubs(ROOT / "generator" / "clubs.csv")
    for c in clubs:
        if c["id"] == club_id:
            return c
    import club_resolver
    return club_resolver.resolve(club_id, sider)


def pack_atlas(atlas_png, out_ftex, template):
    """Encode a 2048x2048 atlas (path or live PIL image) into a .ftex.

    The JIT/rebuild fast path passes the in-memory atlas so it never writes,
    reopens and downsamples a 16 MB PNG just to feed the FTEX encoder.
    """
    if isinstance(atlas_png, Image.Image):
        img = atlas_png.convert("RGBA")
    else:
        img = Image.open(atlas_png).convert("RGBA")
    if img.size != (template["width"], template["height"]):
        img = img.resize((template["width"], template["height"]), Image.LANCZOS)
    fmt = template["pixel_format"]
    if fmt not in (2, 3, 4, 9):
        fmt = 4  # BC3/DXT5 (Pillow supports DXT1/DXT3/DXT5/BC5; standard PES kit format is BC3)
    data = ftex_io.image_to_ftex(img, fmt=fmt, template=template)
    ftex_io.write_ftex(out_ftex, data)
    return out_ftex


def build_set(club, season, outdir, base_ftex=DEFAULT_BASE, slots=(1, 2, 3, "g1", "g2"),
              install=False, game_root=DEFAULT_GAME_ROOT, quiet=False, sponsor=None,
              logo_dir=None, badge_dir=None, badge=None, sleeve_sponsor=None,
              previews=True):
    """Render + pack a club's kit set (outfield and goalkeeper). Returns [(slot, atlas, ftex, design)].

    When `sponsor` is given (a brand name from content/KitGenerator/logos), the
    kits are regenerated with that sponsor's logo on the chest and a fresh design
    drawn from the club's on-brand pattern pool.

    `sleeve_sponsor` overrides the left sleeve secondary sponsor mark
    (e.g. visit_rwanda, hp, dxc, okx). If omitted, an authentic or premier sleeve
    sponsor is dynamically assigned based on club DNA.

    `logo_dir` overrides where the sponsor logos live (defaults to this mod's
    own content/KitGenerator/logos).  A deployed watcher points it at the game's
    SiderAddons/content/KitGenerator/logos instead.
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    base_ftex = Path(base_ftex)
    if not base_ftex.is_file():
        raise SystemExit(f"base .ftex not found: {base_ftex}")
    template = ftex_io.read_ftex(base_ftex)

    if logo_dir is None:
        cand1 = Path(game_root) / "SiderAddons" / "content" / "KitGenerator" / "logos"
        cand2 = ROOT.parent / "content" / "KitGenerator" / "logos"
        cand3 = ROOT / "content" / "KitGenerator" / "logos"
        logo_dir = cand1 if cand1.is_dir() else (cand2 if cand2.is_dir() else cand3)
    logo_dir = Path(logo_dir)
    if badge_dir is None:
        badge_dir = logo_dir.parent / "badges"
    badge_dir = Path(badge_dir)
    masks = kit_regions_build()

    norm_slots = []
    for s in slots:
        if isinstance(s, str) and s.isdigit():
            norm_slots.append(int(s))
        elif s in ("4", 4):
            norm_slots.append("g1")
        elif s in ("5", 5):
            norm_slots.append("g2")
        else:
            norm_slots.append(s)

    rendered = kit_render.render_kit_set(club, season, outdir, logo_dir,
                                         masks=masks, sponsor=sponsor,
                                         badge_dir=badge_dir, badge=badge,
                                         slots=norm_slots,
                                         sleeve_sponsor=sleeve_sponsor,
                                         previews=previews)
    active_dir = Path(game_root) / ACTIVE_SUBDIR if install else None
    if active_dir:
        active_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for slot, atlas, _preview, design in rendered:
        if slot not in norm_slots:
            continue
        slot_code = f"p{slot}" if isinstance(slot, int) else str(slot)
        name = f"u{club['id']:04d}{slot_code}"
        out_ftex = outdir / f"{name}.ftex"
        pack_atlas(atlas, out_ftex, template)
        if not quiet:
            print(f"packed {out_ftex.name}  ({out_ftex.stat().st_size} bytes)  "
                  f"<- {Path(atlas).name}")

        if active_dir:
            dst = active_dir / f"{name}.ftex"
            if dst.resolve() != out_ftex.resolve():
                shutil.copy2(out_ftex, dst)
            if not quiet:
                print(f"  active deployed -> {dst}")

        # Auto-contrasting squad numbers and player name fonts
        try:
            import kit_fonts
            kit_fonts.process_kit_fonts(
                club=club,
                slot=slot,
                design=design,
                outdir=outdir,
                game_root=game_root,
                install=install,
                active_dir=active_dir,
                quiet=quiet,
            )
        except Exception as e:
            if not quiet:
                print(f"  [font warning] failed to process fonts for {slot_code}: {e}")

        atlas_ref = str(atlas) if isinstance(atlas, (str, Path)) else ""
        results.append((slot, atlas_ref, str(out_ftex), design))
    return results


def kit_regions_build():
    import kit_regions
    return kit_regions.build_masks()


def _parse_slots(text):
    slots = []
    for x in text.replace(" ", "").split(","):
        if not x:
            continue
        if x.isdigit():
            slots.append(int(x))
        elif x.lower() in ("g1", "g2"):
            slots.append(x.lower())
        elif x.lower() in ("p1", "p2", "p3"):
            slots.append(int(x.lower().replace("p", "")))
        else:
            raise SystemExit(f"slot must be 1, 2, 3, g1, or g2 (got {x})")
    return tuple(slots)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("club_id", type=int)
    p.add_argument("season", type=int)
    p.add_argument("outdir")
    p.add_argument("--slots", default="1,2,3,g1,g2",
                   help="which kits to build, e.g. 1,2,3 or 1,2,3,g1,g2 (default: 1,2,3,g1,g2)")
    p.add_argument("--install", action="store_true",
                   help="copy the .ftex files into the livecpk override folder")
    p.add_argument("--base", default=str(DEFAULT_BASE),
                   help="a real .ftex used as the header template")
    p.add_argument("--game-root", default=str(DEFAULT_GAME_ROOT),
                   help="game install root (for --install)")
    p.add_argument("--sponsor", default=None,
                   help="signed sponsor brand (logo file stem, e.g. spotify, fly_emirates); "
                        "regenerates the kits with that sponsor and a fresh design")
    p.add_argument("--sleeve-sponsor", default=None,
                   help="sleeve sponsor brand (e.g. visit_rwanda, hp, dxc, okx); "
                        "if omitted, dynamically assigned based on club DNA")
    p.add_argument("--logos", default=None,
                   help="folder holding the sponsor logo PNGs (default: this mod's "
                        "content/KitGenerator/logos)")
    p.add_argument("--badges", default=None,
                   help="folder holding club badge PNGs (default: this mod's "
                        "content/KitGenerator/badges)")
    p.add_argument("--badge", default=None,
                   help="path to a specific badge PNG for this club")
    p.add_argument("--sider", default=None,
                   help="the game's SiderAddons folder, used to resolve a club that "
                        "is not in clubs.csv (default: <game-root>\\SiderAddons)")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)

    sider = args.sider or (Path(args.game_root) / "SiderAddons")
    club = _load_club(args.club_id, sider)
    results = build_set(club, args.season, args.outdir,
                        base_ftex=args.base, slots=_parse_slots(args.slots),
                        install=args.install, game_root=args.game_root,
                        quiet=args.quiet, sponsor=args.sponsor,
                        logo_dir=args.logos, badge_dir=args.badges, badge=args.badge,
                        sleeve_sponsor=args.sleeve_sponsor)

    print()
    for slot, atlas, ftex, d in results:
        label = {1: "home (p1)", 2: "away (p2)", 3: "third (p3)", "g1": "gk1 (g1)", "g2": "gk2 (g2)"}.get(slot, f"slot {slot}")
        print(f"{label:12s}: {Path(ftex).name}  pattern={d['pattern']} "
              f"body={d['body']} sleeve={d['sleeve']} shorts={d['shorts']} "
              f"socks={d['socks']} collar={d['collar']} sponsor={d['_brand']} "
              f"sleeve_sponsor={Path(str(d.get('sleeve_sponsor', 'none'))).stem}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
