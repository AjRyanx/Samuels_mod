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


def _init_worker(base_ftex_path: str, logo_dir_path: str, badge_dir_path: str, low_priority: bool = False) -> None:
    global _WORKER_MASKS, _WORKER_TEMPLATE, _WORKER_LOGO_DIR, _WORKER_BADGE_DIR
    if low_priority:
        try:
            import ctypes
            from ctypes import wintypes
            k32 = ctypes.windll.kernel32
            k32.GetCurrentProcess.restype = wintypes.HANDLE
            k32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            k32.SetPriorityClass.restype = wintypes.BOOL
            k32.SetPriorityClass(k32.GetCurrentProcess(), 0x00004000)  # BELOW_NORMAL_PRIORITY_CLASS
        except Exception:
            pass
    _WORKER_MASKS = kit_regions.build_masks()
    _WORKER_TEMPLATE = ftex_io.read_ftex(Path(base_ftex_path))
    _WORKER_LOGO_DIR = Path(logo_dir_path)
    _WORKER_BADGE_DIR = Path(badge_dir_path)


def parse_slots(text: str) -> tuple:
    slots = []
    for x in text.replace(" ", "").split(","):
        x = x.strip()
        if not x:
            continue
        if x.isdigit():
            slots.append(int(x))
        elif x.lower() in ("g1", "g2"):
            slots.append(x.lower())
        else:
            raise ValueError(f"Invalid slot: {x} (must be 1, 2, 3, g1, or g2)")
    return tuple(slots)


def _render_club_task(
    club: Dict[str, Any],
    season: int,
    sponsor: Optional[str],
    outdir_path: str,
    skip_existing: bool,
    slots: tuple = (1, 2, 3, "g1", "g2"),
) -> Dict[str, Any]:
    global _WORKER_MASKS, _WORKER_TEMPLATE, _WORKER_LOGO_DIR, _WORKER_BADGE_DIR
    cid = club["id"]
    cname = club.get("name", f"Club #{cid}")
    outdir = Path(outdir_path)

    slots_to_generate = []
    for slot in slots:
        slot_code = f"p{slot}" if isinstance(slot, int) else str(slot)
        target = outdir / f"u{cid:04d}{slot_code}.ftex"
        if skip_existing and target.is_file() and target.stat().st_size > 1000:
            continue
        slots_to_generate.append(slot)

    if not slots_to_generate:
        return {"id": cid, "name": cname, "sponsor": sponsor, "skipped": True, "count": 0}

    t0 = time.time()
    generated = 0
    designs = []
    for slot in slots_to_generate:
        slot_code = f"p{slot}" if isinstance(slot, int) else str(slot)
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
        target = outdir / f"u{cid:04d}{slot_code}.ftex"
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


def generate_all_kits(
    season: int = 2027,
    sider_dir: Optional[Path] = None,
    workers: Optional[int] = None,
    slots: str = "1,g1",
    skip_existing: bool = False,
    team: Optional[int] = None,
    team_ids: Optional[List[int]] = None,
    limit: Optional[int] = None,
    outdir: Optional[Path] = None,
    clubs_path: Optional[Path] = None,
    base_ftex_path: Optional[Path] = None,
    logo_dir_path: Optional[Path] = None,
    badge_dir_path: Optional[Path] = None,
    low_priority: Optional[bool] = None,
) -> Dict[str, Any]:
    outdir = Path(outdir or DEFAULT_ACTIVE)
    sider_dir = Path(sider_dir or outdir.parent.parent.parent)
    base_ftex = Path(base_ftex_path or DEFAULT_BASE)
    clubs_file = Path(clubs_path or ROOT / "generator" / "clubs.csv")
    workers = workers or min(os.cpu_count() or 4, 8)

    if not base_ftex.is_file():
        candidates = list(sider_dir.glob("content/kits/**/p1/*.ftex"))
        if candidates:
            base_ftex = candidates[0]
        else:
            raise FileNotFoundError(f"Base .ftex template not found: {base_ftex}")

    if logo_dir_path is None:
        cand1 = sider_dir / "content" / "KitGenerator" / "logos"
        cand2 = ROOT / "content" / "KitGenerator" / "logos"
        logo_dir_path = cand1 if cand1.is_dir() else cand2

    if badge_dir_path is None:
        badge_dir_path = logo_dir_path.parent / "badges"

    brands = sorted({
        p.stem.replace("_white", "")
        for p in logo_dir_path.glob("*.png")
        if not p.stem.startswith("_")
    })
    if not brands:
        raise RuntimeError(f"No sponsor brand logos found in {logo_dir_path}")

    clubs = kit_gen.load_clubs(clubs_file)
    if team is not None:
        clubs = [c for c in clubs if c["id"] == team]
    if team_ids is not None:
        target_ids = set(team_ids)
        existing_cids = {c["id"] for c in clubs}
        # If any requested IDs are not in clubs.csv, load them via build_kit._load_club
        for tid in target_ids:
            if tid not in existing_cids:
                try:
                    import build_kit
                    loaded = build_kit._load_club(tid, sider_dir)
                    if loaded:
                        clubs.append(loaded)
                except Exception:
                    pass
        clubs = [c for c in clubs if c["id"] in target_ids]
    if limit is not None:
        clubs = clubs[:limit]

    outdir.mkdir(parents=True, exist_ok=True)
    user_cid, user_sponsor, is_opted_in = load_user_club_info(sider_dir)

    print(f"================================================================================")
    print(f" GLOBAL PRE-GENERATION: MASTER LEAGUE WORLD (Season {season})")
    print(f"================================================================================")
    print(f" Total Clubs In Scope   : {len(clubs)}")
    print(f" CPU Worker Processes   : {workers}")
    print(f" Sponsor Brand Library  : {len(brands)} brands")
    selected_slots = parse_slots(slots)
    print(f" Target Output Directory: {outdir}")
    print(f" Kit Slots in Scope     : {', '.join(str(s) for s in selected_slots)}")
    print(f" Base Header Template   : {base_ftex.name}")
    print(f" Skip Existing Files    : {'YES' if skip_existing else 'NO'}")
    if user_cid:
        print(f" Human Managed Club     : #{user_cid} (Opted-in: {is_opted_in}, Sponsor: {user_sponsor or 'None'})")
    print(f"================================================================================")

    tasks = []
    skipped_user_club = False
    for club in clubs:
        cid = club["id"]
        # Human club is handled independently by the career watcher - preserve if kit already exists
        if user_cid and cid == user_cid:
            p1_exists = (outdir / f"u{cid:04d}p1.ftex").is_file()
            if p1_exists or skip_existing:
                skipped_user_club = True
                continue
            tasks.append((club, season, user_sponsor, str(outdir), skip_existing, selected_slots))
            continue
        sponsor = pick_ai_sponsor(club, season, brands)
        tasks.append((club, season, sponsor, str(outdir), skip_existing, selected_slots))

    if skipped_user_club:
        print(f" [*] Human club #{user_cid} is preserved (isolated career profile protected).")

    if low_priority is None:
        low_priority = (selected_slots == (1, "g1") or selected_slots == (1,))

    t_start = time.time()
    total_generated = 0
    total_skipped = 0
    completed = 0
    total_tasks = len(tasks)

    init_args = (str(base_ftex), str(logo_dir_path), str(badge_dir_path), low_priority)
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=init_args) as executor:
        futures = {
            executor.submit(_render_club_task, c, s, sp, out, skip, sl): c["id"]
            for (c, s, sp, out, skip, sl) in tasks
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
                if completed % 10 == 0 or completed == total_tasks:
                    print(f" [{completed:3d}/{total_tasks}] #{cid:04d} {name:<24} | Sponsor: {sp:<12} | {cnt} kits ({dur:.2f}s)")

    elapsed = time.time() - t_start
    print(f"================================================================================")
    print(f" COMPLETED IN {elapsed:.1f}s ({elapsed/60:.2f} mins)")
    print(f" Total Kits Generated : {total_generated}")
    print(f" Total Clubs Cached   : {total_skipped}")
    print(f" Active Files in Dir  : {len(list(outdir.glob('*.ftex')))}")
    print(f"================================================================================")
    return {
        "season": season,
        "generated": total_generated,
        "skipped": total_skipped,
        "elapsed": elapsed
    }


def generate_club_kits(
    club_id: int,
    season: int = 2027,
    sider_dir: Optional[Path] = None,
    slots: str = "1,2,3,g1,g2",
    skip_existing: bool = False,
    sponsor: Optional[str] = None,
    outdir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Generate all or missing kit slots for a single club (e.g. JIT scheduled opponent)."""
    import build_kit
    sider_dir = Path(sider_dir or DEFAULT_GAME_ROOT / "SiderAddons")
    active_dir = Path(outdir or sider_dir / "content" / "KitGenerator" / "active")
    active_dir.mkdir(parents=True, exist_ok=True)
    club = build_kit._load_club(club_id, sider_dir)
    logos = sider_dir / "content" / "KitGenerator" / "logos"
    if not logos.is_dir():
        logos = ROOT / "content" / "KitGenerator" / "logos"
    badges = sider_dir / "content" / "KitGenerator" / "badges"
    if not badges.is_dir():
        badges = ROOT / "content" / "KitGenerator" / "badges"

    if not sponsor or sponsor == "all":
        brands = sorted({
            p.stem.replace("_white", "")
            for p in logos.glob("*.png")
            if not p.stem.startswith("_")
        })
        sponsor = pick_ai_sponsor(club, season, brands) if brands else None

    staging_dir = sider_dir / "content" / "KitGenerator" / "staging"
    out_staging = staging_dir / f"season_{season}"
    out_staging.mkdir(parents=True, exist_ok=True)

    selected_slots = parse_slots(slots)
    if skip_existing:
        needed_slots = []
        for s in selected_slots:
            scode = f"p{s}" if isinstance(s, int) else str(s)
            tf = active_dir / f"u{club_id:04d}{scode}.ftex"
            if not tf.is_file() or tf.stat().st_size <= 1000:
                needed_slots.append(s)
        selected_slots = tuple(needed_slots)

    if not selected_slots:
        return {"id": club_id, "sponsor": sponsor, "count": 0, "skipped": True}

    base_ftex = DEFAULT_BASE
    if not base_ftex.is_file():
        candidates = list(sider_dir.glob("content/kits/**/p1/*.ftex"))
        if candidates:
            base_ftex = candidates[0]

    results = build_kit.build_set(
        club,
        season,
        out_staging,
        base_ftex=base_ftex,
        install=True,
        game_root=sider_dir.parent,
        quiet=True,
        sponsor=sponsor,
        logo_dir=logos,
        badge_dir=badges,
        slots=selected_slots,
    )
    return {"id": club_id, "sponsor": sponsor, "count": len(results), "skipped": False}


def main():
    parser = argparse.ArgumentParser(description="Pre-generate Master League kits for all clubs.")
    parser.add_argument("--season", type=int, default=2027, help="Master League season year (e.g. 2027)")
    parser.add_argument("--workers", type=int, default=min(os.cpu_count() or 4, 8), help="CPU worker processes")
    parser.add_argument("--slots", type=str, default="1,g1", help="Kit slots to build (default: 1,g1 - scoutable roster)")
    parser.add_argument("--power", action="store_true", help="Power PC mode: generate all 5 slots (1,2,3,g1,g2) upfront")
    parser.add_argument("--low-priority", action="store_true", default=None, help="Set background worker CPU priority below normal")
    parser.add_argument("--skip-existing", action="store_true", help="Skip clubs whose kit .ftex files already exist")
    parser.add_argument("--clubs", type=Path, default=ROOT / "generator" / "clubs.csv", help="Path to clubs.csv")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_ACTIVE, help="Target active kit directory")
    parser.add_argument("--base-ftex", type=Path, default=DEFAULT_BASE, help="Template .ftex with valid PES kit header")
    parser.add_argument("--logo-dir", type=Path, default=None, help="Directory containing sponsor brand logos")
    parser.add_argument("--badge-dir", type=Path, default=None, help="Directory containing club crest badges")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N clubs")
    parser.add_argument("--team", type=int, default=None, help="Process only a single club ID")
    parser.add_argument("--team-ids", type=str, default=None, help="Comma-separated list of team IDs to generate")
    parser.add_argument("--league-of", type=int, default=None, help="Generate kits for all clubs in the league of this club ID")
    args = parser.parse_args()

    slots_to_build = "1,2,3,g1,g2" if args.power else args.slots
    team_ids = None
    if args.team_ids:
        team_ids = [int(x.strip()) for x in args.team_ids.split(",") if x.strip().isdigit()]
    elif args.league_of:
        sider_dir = args.outdir.parent.parent.parent if args.outdir else DEFAULT_GAME_ROOT / "SiderAddons"
        team_ids = kit_dna.get_league_teams(args.league_of, sider_dir=sider_dir)

    generate_all_kits(
        season=args.season,
        workers=args.workers,
        slots=slots_to_build,
        skip_existing=args.skip_existing,
        team=args.team,
        team_ids=team_ids,
        limit=args.limit,
        outdir=args.outdir,
        clubs_path=args.clubs,
        base_ftex_path=args.base_ftex,
        logo_dir_path=args.logo_dir,
        badge_dir_path=args.badge_dir,
        low_priority=args.low_priority,
    )


if __name__ == "__main__":
    main()
