#!/usr/bin/env python3
r"""watch_signed.py - background watcher: a signed sponsor deal rebuilds the kits.

It runs alongside the game (started by KitGenerator.lua when Sider loads) and
polls

    <sider>\content\KitGenerator\kit_request.txt

which the Lua module appends to the moment you sign an offer:

    offer_id|club_id|season|brand|tier|timestamp

For every request it has not seen before it regenerates that club's
home/away/third kits with the signed sponsor (new design + sponsor logo) and
installs them into

    <game>\SiderAddons\content\KitGenerator\active\u<team>p<slot>.ftex

The static licensed kits under content/kits are never touched, so Exhibition
and all other non-career modes keep their authentic kits.  Processed offer ids
are remembered in watcher_state.txt, so a request is only ever built once.

Only one watcher may run at a time: it holds a loopback TCP port and a second
copy exits immediately.

Usage
-----
    pythonw watch_signed.py                       # normal, background
    python watch_signed.py --once                 # process pending, then exit
    python watch_signed.py --sider "C:\...\SiderAddons"
"""
import argparse
import contextlib
import os
import shutil
import socket
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

DEFAULT_GAME_ROOT = Path(r"C:\Games\SP Football Life 2027")
LOCK_PORT = 51517
POLL_SECONDS = 2.0

# Club-level rebuilds stay at 2 workers so the game is never starved.  Bulk
# rollovers are low-priority and get one extra pair once the optimized renderer
# made each club ~4x cheaper; 8 workers previously exhausted memory.
ROLLOVER_WORKERS = max(2, min(os.cpu_count() or 4, 4))

# region the active .ftex files are installed into, relative to the game root
ACTIVE_SUBDIR = Path("SiderAddons/content/KitGenerator/active")


# --------------------------------------------------------------------------- #
#  Atomic file locking and concurrent read/write helpers
# --------------------------------------------------------------------------- #
@contextmanager
def file_lock(lock_path, timeout=3.0, poll_delay=0.03):
    """Cross-process lock using lockfile with retry, preventing torn reads/writes."""
    lock_file = Path(str(lock_path) + ".lock")
    start = time.time()
    fd = None
    while True:
        try:
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            # Check for stale lock (> 30s)
            try:
                if time.time() - lock_file.stat().st_mtime > 30.0:
                    lock_file.unlink()
                    continue
            except OSError:
                pass
            if time.time() - start > timeout:
                break
            time.sleep(poll_delay)
        except OSError:
            break
    try:
        yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
                lock_file.unlink()
            except OSError:
                pass


def safe_read_lines(path, lock=True, retries=5, delay=0.04):
    """Safely read lines from a file subject to concurrent writes."""
    path = Path(path)
    if not path.is_file():
        return []

    ctx = file_lock(path, timeout=2.0) if lock else contextlib.nullcontext()
    with ctx:
        for _ in range(retries):
            try:
                raw = path.read_bytes()
                if not raw:
                    return []
                # Only take up to the last complete newline to guard against torn writes
                last_nl = raw.rfind(b"\n")
                if last_nl == -1:
                    return []
                complete_raw = raw[:last_nl]
                text = complete_raw.decode("utf-8-sig", errors="replace")
                return [ln.strip() for ln in text.splitlines() if ln.strip()]
            except (OSError, PermissionError):
                time.sleep(delay)
    return []


def safe_append_line(path, text, lock=True, retries=5, delay=0.04):
    """Safely append a line to a file subject to concurrent writes."""
    path = Path(path)
    ctx = file_lock(path, timeout=2.0) if lock else contextlib.nullcontext()
    with ctx:
        for _ in range(retries):
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(text.strip() + "\n")
                    f.flush()
                return True
            except (OSError, PermissionError):
                time.sleep(delay)
    return False


# --------------------------------------------------------------------------- #
#  small helpers
# --------------------------------------------------------------------------- #
def _log(msg, logfile=None):
    line = "%s  %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        print(line, flush=True)
    except UnicodeEncodeError:                    # a console without the glyphs
        print(line.encode("ascii", "replace").decode("ascii"), flush=True)
    if logfile:
        try:
            with open(logfile, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


def _acquire_lock():
    """Return a listening socket that marks this process as the only watcher."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", LOCK_PORT))
        s.listen(1)
    except OSError:
        s.close()
        return None
    return s


def _read_state(state_file):
    lines = safe_read_lines(state_file, lock=False)
    return set(lines)


def _read_pid(pid_file):
    """Return the game's pid from pid_file, or None if it is missing/unreadable."""
    try:
        return int(pid_file.read_text(encoding="utf-8", errors="replace").strip())
    except (OSError, ValueError):
        return None


def _game_alive(pid):
    """True/False if we can tell whether `pid` is running, else None (unknown).

    False is only returned when Windows explicitly says there is no such
    process; anything ambiguous (access denied, API failure) returns None so we
    keep watching rather than shut down by mistake.
    """
    try:
        import ctypes
        ERROR_INVALID_PARAMETER = 87
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not h:
            if ctypes.get_last_error() == ERROR_INVALID_PARAMETER:
                return False                     # no process with that id
            return None                          # access denied etc: don't guess
        try:
            code = ctypes.c_ulong()
            if k.GetExitCodeProcess(h, ctypes.byref(code)):
                return code.value == STILL_ACTIVE
            return None
        finally:
            k.CloseHandle(h)
    except Exception:                            # noqa: BLE001
        return None


def _mark_done(state_file, offer_id):
    safe_append_line(state_file, offer_id, lock=True)


def _parse_request(line):
    """offer_id|club_id|season|brand|tier|timestamp|career_id -> dict (or None)."""
    line = line.strip().lstrip("\ufeff")           # tolerate a Notepad BOM
    if not line or line.startswith("#"):
        return None
    parts = [p.strip() for p in line.split("|")]
    if len(parts) < 4:
        return None
    try:
        club_id = int(parts[1])
        season = int(parts[2])
    except (ValueError, IndexError):
        return None
    tier = parts[4] if len(parts) >= 5 and parts[4] else None
    career_id = parts[6] if len(parts) >= 7 and parts[6] else None
    return {
        "offer": parts[0],
        "club_id": club_id,
        "season": season,
        "brand": parts[3] or None,
        "tier": tier,
        "career_id": career_id,
    }


def _is_force_clean(req):
    return (req["offer"].startswith("clean-")
            and (req.get("tier") or "").lower() == "force")


def _is_signed_rebuild(req):
    """Signed-deal rebuilds carry a -t<stamp> suffix; seasonal ones do not."""
    offer = req["offer"]
    if not offer.startswith("rebuild-") or "-t" not in offer:
        return False
    return offer.rsplit("-t", 1)[1].isdigit()


def _is_urgent_user(req):
    """Only user-driven work may interrupt the season baseline."""
    return _is_force_clean(req) or _is_signed_rebuild(req)


def _missing_jit_slots(active_dir: Path, club_id: int) -> str:
    """Slot tokens still missing for a scheduled opponent.

    p1/g1 normally arrive from the season baseline; p2/p3/g2 are generated
    on demand.  Returning only the missing tokens keeps JIT work minimal while
    still recovering a club that was missed by the baseline pass.
    """
    tokens = (("p1", "1"), ("g1", "g1"), ("p2", "2"), ("p3", "3"), ("g2", "g2"))
    missing = []
    for code, token in tokens:
        path = active_dir / f"u{club_id:04d}{code}.ftex"
        if not path.is_file() or path.stat().st_size <= 1000:
            missing.append(token)
    return ",".join(missing)


def _urgent_requests_pending(req_file, state_file, exclude=None):
    """True if signed-deal/force-clean work arrived during the baseline.

    Opponent JIT and the user club's seasonal rebuild now run *after* the
    baseline, so they must not abort it.  Only an actual user action does.
    """
    seen = _read_state(state_file)
    for line in safe_read_lines(req_file, lock=False):
        req = _parse_request(line)
        if not req or req["offer"] == exclude or req["offer"] in seen:
            continue
        if _is_urgent_user(req):
            return True
    return False


# --------------------------------------------------------------------------- #
#  the actual rebuild
# --------------------------------------------------------------------------- #
def rebuild(club_id, season, brand, sider, game_root, logfile,
            career_id=None, force_signature=False):
    """Regenerate one club's kit set with `brand` and install it.

    Returns the list of (slot, atlas, ftex, design) build_set produced.  An
    identical repeat request is retired without rendering when the stored
    signature and installed output bytes still match.
    """
    import activate_season
    import build_kit
    import kit_signature

    club = build_kit._load_club(club_id, sider)
    logos = Path(sider) / "content" / "KitGenerator" / "logos"
    badges = Path(sider) / "content" / "KitGenerator" / "badges"
    content_dir = Path(sider) / "content" / "KitGenerator"
    sleeve_dir = content_dir / "sleeve_logos"
    staging_dir = content_dir / "staging"
    outdir = staging_dir / f"season_{season}"
    active_dir = Path(game_root) / "SiderAddons" / "content" / "KitGenerator" / "active"

    base_ftex = build_kit.DEFAULT_BASE
    if not base_ftex.is_file():
        candidates = list(Path(sider).glob("content/kits/**/p1/*.ftex"))
        if candidates:
            base_ftex = candidates[0]

    all_slots = (1, 2, 3, "g1", "g2")
    signature_for = lambda slot: kit_signature.build_signature(
        club_id=club_id,
        season=season,
        sponsor=brand,
        slot=slot,
        generator_dir=Path(__file__).resolve().parent,
        base_ftex=base_ftex,
        logo_dir=logos,
        badge_dir=badges,
        sleeve_dir=sleeve_dir,
    )
    signatures = {}
    cached_slots = []
    if not force_signature:
        for slot in all_slots:
            sig = signature_for(slot)
            signatures[slot] = sig
            key = kit_signature.key_for(active_dir, club_id, season, slot)
            paths = kit_signature.target_files(active_dir, club_id, slot)
            if kit_signature.matches(content_dir, key, sig, paths):
                cached_slots.append(slot)

    skipped = len(cached_slots) == len(all_slots)
    if skipped:
        _log("  kit set unchanged for club #%d (season %d, sponsor=%s); skipped %d slot render(s)"
             % (club_id, season, brand or "none", len(all_slots)), logfile)
        results = []
        for slot in all_slots:
            code = f"p{slot}" if isinstance(slot, int) else str(slot)
            results.append((slot, "", str(active_dir / f"u{club_id:04d}{code}.ftex"), {}))
    else:
        results = build_kit.build_set(
            club, season, outdir,
            base_ftex=base_ftex,
            install=True, game_root=game_root, quiet=True,
            sponsor=brand, logo_dir=logos, badge_dir=badges,
            previews=False,                # runtime only needs the .ftex files
        )
        for slot, _atlas, _ftex, _design in results:
            sig = signatures.get(slot) or signature_for(slot)
            key = kit_signature.key_for(active_dir, club_id, season, slot)
            paths = kit_signature.target_files(active_dir, club_id, slot)
            if all(path.is_file() for path in paths):
                kit_signature.record(content_dir, key, sig, paths)
        for slot, _atlas, ftex, design in results:
            slot_code = f"p{slot}" if isinstance(slot, int) else str(slot)
            _log("  built %s -> %s (pattern=%s sponsor=%s)"
                 % (slot_code, Path(ftex).name, design.get("pattern"), design.get("_brand")),
                 logfile)

    # If tagged with a specific career profile, mirror to isolated career folder
    if career_id and career_id != "unknown":
        career_dir = content_dir / "careers" / career_id
        career_dir.mkdir(parents=True, exist_ok=True)
        for slot, _atlas, _ftex, _design in results:
            slot_code = f"p{slot}" if isinstance(slot, int) else str(slot)
            name = f"u{club_id:04d}{slot_code}"
            src_ftex = active_dir / f"{name}.ftex"
            if src_ftex.is_file():
                shutil.copy2(src_ftex, career_dir / f"{name}.ftex")
            for ftype in ("back", "leg", "name"):
                src_font = active_dir / f"{name}_{ftype}.ftex"
                if src_font.is_file():
                    shutil.copy2(src_font, career_dir / f"{name}_{ftype}.ftex")
        _log("  profile isolation: mirrored kit set to careers/%s/" % career_id, logfile)

    # Auto-cleanup old staging folders (recovers disk space, keeps current & recent season)
    try:
        cleaned = activate_season.cleanup_old_staging(staging_dir, keep_seasons=2, current_season=season)
        if cleaned:
            _log("  staging cleanup: purged %d old staging item(s)" % cleaned, logfile)
    except Exception as exc:
        _log("  staging cleanup warning: %s" % exc, logfile)

    return results


def process_pending(req_file, state_file, sider, game_root, logfile):
    """Build every request in req_file that we have not built yet. Returns count."""
    if not req_file.is_file():
        return 0
    seen = _read_state(state_file)
    lines = safe_read_lines(req_file, lock=True)
    if not lines:
        return 0

    # Priority: signed deals / forced cleans > season baseline > seasonal club
    # rebuilds > scheduled-opponent JIT.  League pre-generation is retired.
    urgent_user_requests = []
    user_requests = []
    jit_requests = []
    rollover_requests = []
    active_dir = Path(game_root) / "SiderAddons" / "content" / "KitGenerator" / "active"

    # A completed rollover is the season high-water mark.  Previous-season JIT
    # and rebuild requests must stay retired even when a refresh prunes their
    # on-disk "already built" marker (p2/p3/g2) - otherwise they regenerate
    # last season's kits over the new season's baseline.
    current_season = 0
    for line in lines:
        prior = _parse_request(line)
        if (prior and prior["club_id"] == 0 and prior["offer"] in seen
                and prior["season"] > current_season):
            current_season = prior["season"]

    for line in lines:
        req = _parse_request(line)
        if not req:
            continue
        is_jit = req["offer"].startswith("jit-") or req.get("tier") == "jit"
        is_league = req["offer"].startswith("league-") or req.get("tier") == "league"
        is_rollover = req["club_id"] == 0 or (req["brand"] == "all" and not is_jit and not is_league) or req["offer"].startswith("season-")

        # Obsolete league pre-generation requests are retired on sight.  The
        # baseline + JIT model replaces them completely.
        if is_league:
            _mark_done(state_file, req["offer"])
            seen.add(req["offer"])
            continue

        if current_season and req["season"] < current_season and not is_rollover:
            _mark_done(state_file, req["offer"])   # retire stale-season work permanently
            seen.add(req["offer"])
            continue

        # A "force" clean comes from deal expiry/termination.  The branded file
        # still exists on disk, so the normal "already installed" shortcut must
        # not skip it -- otherwise the expired sponsor's logo would stay on.
        force_clean = _is_force_clean(req)

        if req["offer"].startswith("clean-") and req["club_id"] > 0 and not force_clean:
            target_ftex = active_dir / f"u{req['club_id']:04d}p1.ftex"
            career_id = req.get("career_id")
            career_ftex = (Path(sider) / "content" / "KitGenerator" / "careers" / career_id / f"u{req['club_id']:04d}p1.ftex") if (career_id and career_id != "unknown") else None
            if target_ftex.is_file() and (career_ftex is None or career_ftex.is_file()):
                _mark_done(state_file, req["offer"])
                seen.add(req["offer"])
                continue

        if req["offer"] in seen:
            if req["club_id"] > 0:
                if is_jit:
                    if not _missing_jit_slots(active_dir, req["club_id"]):
                        continue
                else:
                    target_ftex = active_dir / f"u{req['club_id']:04d}p1.ftex"
                    career_id = req.get("career_id")
                    career_ftex = (Path(sider) / "content" / "KitGenerator" / "careers" / career_id / f"u{req['club_id']:04d}p1.ftex") if (career_id and career_id != "unknown") else None
                    if target_ftex.is_file() and (career_ftex is None or career_ftex.is_file()):
                        continue
            elif is_rollover:
                # If active directory does not have baseline kits (< 100 clubs), do not skip
                if len(list(active_dir.glob("*p1.ftex"))) >= 100:
                    continue
            else:
                continue

        if _is_urgent_user(req):
            urgent_user_requests.append(req)
        elif is_jit:
            jit_requests.append(req)
        elif is_rollover:
            rollover_requests.append(req)
        else:
            user_requests.append(req)

    # An urgent user action gets its own poll.  Starting the multi-minute
    # baseline immediately afterwards would just waste work if another deal is
    # signed moments later.  Normal seasonal/JIT work still queues behind it.
    if urgent_user_requests and rollover_requests:
        _log("season rollover deferred: %d urgent user request(s) processed first"
             % len(urgent_user_requests), logfile)
        rollover_requests = []

    # The baseline is the foundation for every later dynamic kit, so it runs
    # before opponent JIT and the user club's seasonal (non-urgent) rebuild.
    pending_queue = (urgent_user_requests + rollover_requests
                     + user_requests + jit_requests)

    def _arrived(current_offer):
        return _urgent_requests_pending(req_file, state_file, exclude=current_offer)

    done = 0
    for req in pending_queue:
        # Duplicate request IDs are classified from the same snapshot.  Once the
        # first copy completes, its ID is in `seen`; never build the same job a
        # second time in this poll (this used to rerun a 17-minute baseline).
        if req["offer"] in seen:
            continue
        _log("processing request: offer=%s club=%d season=%d sponsor=%s"
             % (req["offer"], req["club_id"], req["season"], req["brand"]), logfile)
        try:
            is_jit = req["offer"].startswith("jit-") or req.get("tier") == "jit"
            is_league = req["offer"].startswith("league-") or req.get("tier") == "league"
            is_rollover = req["club_id"] == 0 or (req["brand"] == "all" and not is_jit and not is_league) or req["offer"].startswith("season-")
            is_force_clean = (req["offer"].startswith("clean-")
                              and (req.get("tier") or "").lower() == "force")
            if is_force_clean:
                _log("forced clean rebuild: replacing old branded kit files for club #%d"
                     % req["club_id"], logfile)

            if is_jit:
                import build_all_clubs
                user_cid, user_sponsor, _ = build_all_clubs.load_user_club_info(Path(sider))
                if req["club_id"] == user_cid:
                    # Legacy JIT request for the human club (queued before the
                    # Lua guard).  Route it through the career rebuild so the
                    # signed sponsor - or no sponsor - is used and the isolated
                    # career profile is refreshed too.
                    _log("JIT request for human club #%d routed to career rebuild (sponsor=%s)"
                         % (req["club_id"], user_sponsor or "none"), logfile)
                    rebuild(req["club_id"], req["season"], user_sponsor,
                            sider, game_root, logfile, career_id=req.get("career_id"))
                else:
                    missing_slots = _missing_jit_slots(active_dir, req["club_id"])
                    if not missing_slots:
                        _log("JIT opponent request: club #%d already has a complete kit set; retiring"
                             % req["club_id"], logfile)
                    else:
                        _log("JIT opponent request: building missing slots %s for scheduled club #%d (season %d)"
                             % (missing_slots, req["club_id"], req["season"]), logfile)
                        stats = build_all_clubs.generate_club_kits(
                            club_id=req["club_id"],
                            season=req["season"],
                            sider_dir=Path(sider),
                            slots=missing_slots,
                            skip_existing=True,
                        )
                        if stats.get("skipped"):
                            _log("JIT opponent request: club #%d signature-matched cached kit files; skipped render"
                                 % req["club_id"], logfile)
            elif is_league:
                continue                              # defensive: already retired above
            elif is_rollover:
                mode = (req.get("tier") or "balanced").lower()
                import build_all_clubs
                if mode == "power":
                    _log("season rollover: FORCED full 5-slot refresh for all clubs (mode=power)", logfile)
                    stats = build_all_clubs.refresh_season_kits(
                        season=req["season"], sider_dir=Path(sider),
                        slots="1,2,3,g1,g2", scope="power", prune_secondary=False,
                        workers=ROLLOVER_WORKERS,
                        abort_check=lambda: _arrived(req["offer"]))
                    if stats.get("aborted"):
                        _log("  power rollover interrupted by a higher-priority request; retrying later", logfile)
                        continue
                    _log("  power rollover: %d clubs, %d kit files copied into active"
                         % (stats["clubs"], stats["copied"]), logfile)
                    tm = stats.get("timings", {})
                    _log("  power rollover timings: setup=%.1fs render=%.1fs copy=%.1fs prune=%.1fs total=%.1fs"
                         % (tm.get("setup_s", 0.0), tm.get("render_s", 0.0),
                            tm.get("copy_s", 0.0), tm.get("prune_s", 0.0),
                            tm.get("total_s", 0.0)), logfile)
                else:
                    _log("season rollover: FORCED scoutable baseline refresh (mode=balanced, slots=1,g1)", logfile)
                    stats = build_all_clubs.refresh_season_kits(
                        season=req["season"], sider_dir=Path(sider),
                        slots="1,g1", scope="baseline", prune_secondary=True,
                        low_priority=True, workers=ROLLOVER_WORKERS,
                        abort_check=lambda: _arrived(req["offer"]))
                    if stats.get("aborted"):
                        _log("  baseline refresh interrupted by a higher-priority request; retrying later", logfile)
                        continue
                    if stats.get("resumed"):
                        _log("  baseline refresh resumed from staging: %d cached club(s), %d invalid file(s) discarded"
                             % (stats.get("skipped", 0), stats.get("invalid_removed", 0)), logfile)
                    _log("  baseline refresh: %d clubs, %d kit files copied, %d stale secondary files pruned"
                         % (stats["clubs"], stats["copied"], stats["pruned"]), logfile)
                    tm = stats.get("timings", {})
                    _log("  baseline timings: setup=%.1fs render=%.1fs copy=%.1fs prune=%.1fs total=%.1fs"
                         % (tm.get("setup_s", 0.0), tm.get("render_s", 0.0),
                            tm.get("copy_s", 0.0), tm.get("prune_s", 0.0),
                            tm.get("total_s", 0.0)), logfile)
                    # No league pre-generation follows the baseline.  Secondary
                    # kits for AI clubs are built only when they are scheduled.
            else:
                rebuild(req["club_id"], req["season"], req["brand"], sider, game_root,
                        logfile, career_id=req.get("career_id"),
                        force_signature=is_force_clean)
        except Exception as exc:                      # noqa: BLE001 - keep watching
            _log("  ERROR building %s: %s: %s"
                 % (req["offer"], type(exc).__name__, exc), logfile)
            continue
        _mark_done(state_file, req["offer"])
        seen.add(req["offer"])
        done += 1
    if done:
        _log("installed %d new kit set(s) - they appear at the next match" % done, logfile)
    return done


# --------------------------------------------------------------------------- #
#  main
# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sider", default=str(DEFAULT_GAME_ROOT / "SiderAddons"),
                    help="the game's SiderAddons folder (holds content/ and livecpk/)")
    ap.add_argument("--game-root", default=str(DEFAULT_GAME_ROOT),
                    help="the game install root (for the livecpk install path)")
    ap.add_argument("--poll", type=float, default=POLL_SECONDS,
                    help="seconds between checks (default 2)")
    ap.add_argument("--once", action="store_true",
                    help="process any pending requests, then exit")
    ap.add_argument("--keep-running", action="store_true",
                    help="do not exit when the game process closes (for manual runs)")
    args = ap.parse_args(argv)

    sider = Path(args.sider)
    game_root = Path(args.game_root)
    content = sider / "content" / "KitGenerator"
    req_file = content / "kit_request.txt"
    state_file = content / "watcher_state.txt"
    pid_file = content / "game.pid"
    logfile = content / "watcher.log"

    lock = _acquire_lock()
    if lock is None and not args.once:
        _log("another watcher is already running (port %d) - exiting" % LOCK_PORT,
             logfile)
        return 0

    watch_pid = not (args.once or args.keep_running)
    _log("watcher started (sider=%s, once=%s, watch_pid=%s)"
         % (sider, args.once, watch_pid), logfile)
    dead = 0
    try:
        while True:
            try:
                process_pending(req_file, state_file, sider, game_root, logfile)
            except Exception as exc:                  # noqa: BLE001 - never die
                _log("poll error: %s: %s" % (type(exc).__name__, exc), logfile)
            if args.once:
                break
            if watch_pid:
                pid = _read_pid(pid_file)
                if pid is not None:
                    alive = _game_alive(pid)
                    if alive is False:
                        dead += 1
                        if dead >= 3:                 # ~6 s grace
                            _log("game process %d has closed - watcher exiting" % pid,
                                 logfile)
                            break
                    elif alive is True:
                        dead = 0
            time.sleep(max(0.25, args.poll))
    except KeyboardInterrupt:
        pass
    finally:
        if lock is not None:
            lock.close()
    _log("watcher stopped", logfile)
    return 0


if __name__ == "__main__":
    sys.exit(main())
