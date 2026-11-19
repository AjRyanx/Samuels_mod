"""build_all_clubs.py - Global Pre-Generation Suite for Master League

Generates authentic high-fashion dynamic kits with realistic multi-year AI sponsor
contracts for all 580+ clubs in clubs.csv.

Uses multi-processing across all CPU cores to render and pack .ftex files directly
into SiderAddons/content/KitGenerator/active/ in minutes.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ftex_io
import kit_dna
import kit_gen
import kit_regions
import kit_render
from kg_core import season_rng

DEFAULT_GAME_ROOT = Path(r"C:\Games\SP Football Life 2027")
DEFAULT_BASE = (
    DEFAULT_GAME_ROOT
    / "SiderAddons"
    / "content"
    / "kits"
    / "Premier League"
    / "Chelsea"
    / "p1"
    / "u0102p1.ftex"
)
DEFAULT_ACTIVE = DEFAULT_GAME_ROOT / "SiderAddons" / "content" / "KitGenerator" / "active"


# Worker globals initialized once per process to avoid re-reading masks and templates
_WORKER_MASKS: Optional[Dict[str, Any]] = None
_WORKER_TEMPLATE: Optional[Dict[str, Any]] = None
_WORKER_LOGO_DIR: Optional[Path] = None
_WORKER_BADGE_DIR: Optional[Path] = None


def _init_worker(base_ftex_path: str, logo_dir_path: str, badge_dir_path: str) -> None:
    global _WORKER_MASKS, _WORKER_TEMPLATE, _WORKER_LOGO_DIR, _WORKER_BADGE_DIR
    _WORKER_MASKS = kit_regions.build_masks()
    _WORKER_TEMPLATE = ftex_io.read_ftex(Path(base_ftex_path))
    _WORKER_LOGO_DIR = Path(logo_dir_path)
    _WORKER_BADGE_DIR = Path(badge_dir_path)


def _render_club_task(
    club: Dict[str, Any],
    season: int,
    sponsor: Optional[str],
    outdir_path: str,
    skip_existing: bool,
) -> Dict[str, Any]:
    global _WORKER_MASKS, _WORKER_TEMPLATE, _WORKER_LOGO_DIR, _WORKER_BADGE_DIR
    cid = club["id"]
    cname = club.get("name", f"Club #{cid}")
    outdir = Path(outdir_path)

    slots_to_generate = []
    for slot in (1, 2, 3):
        target = outdir / f"u{cid:04d}p{slot}.ftex"
        if skip_existing and target.is_file() and target.stat().st_size > 1000:
            continue
        slots_to_generate.append(slot)

    if not slots_to_generate:
        return {"id": cid, "name": cname, "sponsor": sponsor, "skipped": True, "count": 0}

    t0 = time.time()
    generated = 0
    designs = []
    for slot in slots_to_generate:
        atlas, design = kit_render.render_club(
            club,
            season,
            None,
            _WORKER_LOGO_DIR,
            masks=_WORKER_MASKS,
            slot=slot,
            sponsor=sponsor,
            badge_dir=_WORKER_BADGE_DIR,
        )
        ftex_data = ftex_io.image_to_ftex(atlas, fmt=4, template=_WORKER_TEMPLATE)
        target = outdir / f"u{cid:04d}p{slot}.ftex"
        ftex_io.write_ftex(target, ftex_data)
        generated += 1
        designs.append(design)

    dt = time.time() - t0
    return {
        "id": cid,
        "name": cname,
        "sponsor": sponsor,
        "skipped": False,
        "count": generated,
        "time": dt,
    }


def load_user_club_info(sider_dir: Path) -> tuple[Optional[int], Optional[str], bool]:
    """Read club.txt, active_deal.txt, and opted_in.txt to protect the player's storyline save."""
    kg_dir = sider_dir / "content" / "KitGenerator"
    user_cid: Optional[int] = None
    user_sponsor: Optional[str] = None
    is_opted_in = False

    club_file = kg_dir / "club.txt"
    if club_file.is_file():
        try:
            line = club_file.read_text(encoding="utf-8").strip()
            if line:
                parts = line.split("|")
                if parts[0].isdigit():
                    user_cid = int(parts[0])
        except Exception:
            pass

    opted_file = kg_dir / "opted_in.txt"
    if opted_file.is_file() and user_cid:
        try:
            for l in opted_file.read_text(encoding="utf-8").splitlines():
                if l.strip() == str(user_cid):
                    is_opted_in = True
                    break
        except Exception:
            pass

    deal_file = kg_dir / "active_deal.txt"
    if deal_file.is_file():
        try:
            line = deal_file.read_text(encoding="utf-8").strip()
            if line:
                parts = line.split("|")
                if len(parts) >= 3:
                    deal_cid = int(parts[1]) if parts[1].isdigit() else 0
                    if user_cid is None and deal_cid > 0:
                        user_cid = deal_cid
                    if deal_cid == user_cid:
                        user_sponsor = parts[2]
                        is_opted_in = True
        except Exception:
            pass

    return user_cid, user_sponsor, is_opted_in


def pick_ai_sponsor(club: Dict[str, Any], season: int, brands: List[str]) -> str:
    """Deterministically assign a multi-year AI sponsorship contract from the brand pool."""
    cid = club["id"]
    duration = 2 if (cid % 2 == 0) else 3
    cycle_start = 2026 + ((season - 2026) // duration) * duration
    rng = season_rng(cid, cycle_start, salt="ai-sponsor-deal")
    return rng.choice(brands)


def main():
    parser = argparse.ArgumentParser(description="Pre-generate Master League kits for all clubs.")
    parser.add_argument("--season", type=int, default=2027, help="Master League season year (e.g. 2027)")
    parser.add_argument("--workers", type=int, default=min(os.cpu_count() or 4, 8), help="CPU worker processes")
    parser.add_argument("--skip-existing", action="store_true", help="Skip clubs whose 3 kit .ftex files already exist")
    parser.add_argument("--clubs", type=Path, default=ROOT / "generator" / "clubs.csv", help="Path to clubs.csv")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_ACTIVE, help="Target active kit directory")
    parser.add_argument("--base-ftex", type=Path, default=DEFAULT_BASE, help="Template .ftex with valid PES kit header")
    parser.add_argument("--logo-dir", type=Path, default=None, help="Directory containing sponsor brand logos")
    parser.add_argument("--badge-dir", type=Path, default=None, help="Directory containing club crest badges")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N clubs")
    parser.add_argument("--team", type=int, default=None, help="Process only a single club ID")
    args = parser.parse_args()

    sider_dir = args.outdir.parent.parent.parent
    if not args.base_ftex.is_file():
        # Fallback search if DEFAULT_BASE does not exist
        candidates = list(sider_dir.glob("content/kits/**/p1/*.ftex"))
        if candidates:
            args.base_ftex = candidates[0]
        else:
            sys.exit(f"Base .ftex template not found: {args.base_ftex}")

    if args.logo_dir is None:
        cand1 = sider_dir / "content" / "KitGenerator" / "logos"
        cand2 = ROOT / "content" / "KitGenerator" / "logos"
        args.logo_dir = cand1 if cand1.is_dir() else cand2

    if args.badge_dir is None:
        args.badge_dir = args.logo_dir.parent / "badges"

    brands = sorted({
        p.stem.replace("_white", "")
        for p in args.logo_dir.glob("*.png")
        if not p.stem.startswith("_")
    })
    if not brands:
        sys.exit(f"No sponsor brand logos found in {args.logo_dir}")

    clubs = kit_gen.load_clubs(args.clubs)
    if args.team is not None:
        clubs = [c for c in clubs if c["id"] == args.team]
    if args.limit is not None:
        clubs = clubs[:args.limit]

    args.outdir.mkdir(parents=True, exist_ok=True)
    user_cid, user_sponsor, is_opted_in = load_user_club_info(sider_dir)

    print(f"================================================================================")
    print(f" GLOBAL PRE-GENERATION: MASTER LEAGUE WORLD (Season {args.season})")
    print(f"================================================================================")
    print(f" Total Clubs In Scope   : {len(clubs)}")
    print(f" CPU Worker Processes   : {args.workers}")
    print(f" Sponsor Brand Library  : {len(brands)} brands")
    print(f" Target Output Directory: {args.outdir}")
    print(f" Base Header Template   : {args.base_ftex.name}")
    print(f" Skip Existing Files    : {'YES' if args.skip_existing else 'NO'}")
    if user_cid:
        print(f" Human Managed Club     : #{user_cid} (Opted-in: {is_opted_in}, Sponsor: {user_sponsor or 'None'})")
    print(f"================================================================================")

    # Prepare task list with sponsor assignment
    tasks = []
    skipped_user_club = False
    for club in clubs:
        cid = club["id"]
        if cid == user_cid:
            if not is_opted_in:
                # Human player has not opted into mod sponsors yet: protect authentic kits!
                skipped_user_club = True
                continue
            sponsor = user_sponsor
        else:
            sponsor = pick_ai_sponsor(club, args.season, brands)

        tasks.append((club, args.season, sponsor, str(args.outdir), args.skip_existing))

    if skipped_user_club:
        print(f" [*] Human club #{user_cid} is preserved authentic (storyline opt-in not triggered).")

    t_start = time.time()
    total_generated = 0
    total_skipped = 0
    completed = 0
    total_tasks = len(tasks)

    init_args = (str(args.base_ftex), str(args.logo_dir), str(args.badge_dir))
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_worker, initargs=init_args) as executor:
        futures = {
            executor.submit(_render_club_task, c, s, sp, out, skip): c["id"]
            for (c, s, sp, out, skip) in tasks
        }

        for fut in as_completed(futures):
            completed += 1
            res = fut.result()
            cid = res["id"]
            name = res["name"]
            sp = res["sponsor"] or "Clean"
            cnt = res["count"]

            if res["skipped"]:
                total_skipped += 1
                if completed % 25 == 0 or completed == total_tasks:
                    print(f" [{completed:3d}/{total_tasks}] #{cid:04d} {name:<24} | Existing kits verified (cached)")
            else:
                total_generated += cnt
                dur = res.get("time", 0.0)
                print(f" [{completed:3d}/{total_tasks}] #{cid:04d} {name:<24} | Sponsor: {sp:<12} | {cnt} kits ({dur:.2f}s)")

    elapsed = time.time() - t_start
    print(f"================================================================================")
    print(f" COMPLETED IN {elapsed:.1f}s ({elapsed/60:.2f} mins)")
    print(f" Total Kits Generated : {total_generated}")
    print(f" Total Clubs Cached   : {total_skipped}")
    print(f" Active Files in Dir  : {len(list(args.outdir.glob('*.ftex')))}")
    print(f"================================================================================")


if __name__ == "__main__":
    main()
