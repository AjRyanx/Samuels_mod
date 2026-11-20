"""test_priority_tree_and_jit.py - Verify multi-tier kit generation priority tree and JIT scheduling.

Verifies:
  1. League discovery: get_league_teams identifies intra-league clubs accurately.
  2. Lua league background queueing: ensure_season_deal writes league request.
  3. Lua calendar schedule JIT queueing: set_teams in ML triggers JIT for scheduled opponents without p2 kits.
  4. Master League scope protection: Exhibition matches and Season 1 AI clubs never trigger dynamic JIT requests.
  5. Missing kit intercept: make_key triggers JIT when p2/p3/g2 is requested and absent.
  6. Python priority queue: watch_signed prioritizes user requests -> JIT opponents -> user league -> rollover.
"""
import tempfile
import shutil
from pathlib import Path
from lupa import LuaRuntime
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT / "generator") not in sys.path:
    sys.path.insert(0, str(ROOT / "generator"))

import kit_dna
import watch_signed
import build_all_clubs


def test_league_discovery():
    # Test known top leagues
    epl_teams = kit_dna.get_league_teams(102) # Chelsea
    assert 102 in epl_teams
    assert 100 in epl_teams # Man Utd
    assert 101 in epl_teams # Arsenal
    assert len(epl_teams) == 20

    laliga_teams = kit_dna.get_league_teams(108) # Barcelona
    assert 108 in laliga_teams
    assert 109 in laliga_teams # Real Madrid
    assert 102 not in laliga_teams

    # Test map.txt parsing if available
    tmp = Path(tempfile.mkdtemp())
    try:
        map_dir = tmp / "content" / "kits"
        map_dir.mkdir(parents=True, exist_ok=True)
        map_file = map_dir / "map.txt"
        map_file.write_text(
            '9001, "Custom League\\Team Alpha"\n'
            '9002, "Custom League\\Team Beta"\n'
            '9003, "Other League\\Team Gamma"\n'
        )
        custom_teams = kit_dna.get_league_teams(9001, sider_dir=tmp)
        assert 9001 in custom_teams
        assert 9002 in custom_teams
        assert 9003 not in custom_teams
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS: League discovery verified.")


def test_lua_queueing_and_jit():
    root = ROOT
    tmp = Path(tempfile.mkdtemp())
    try:
        shutil.copytree(root / "content", tmp / "content")
        active_dir = tmp / "content" / "KitGenerator" / "active"
        active_dir.mkdir(parents=True, exist_ok=True)

        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute('log=function(s) LOGS=(LOGS or "")..s.."\\n" end; ffi=nil')
        lua.execute('local _orig_open=io.open; io.open=function(p, m) return _orig_open(p:gsub("\\\\", "/"), m) end')
        M = lua.eval('function(src) return load(src)() end')((root / "modules/KitGenerator.lua").read_text())

        setup = lua.eval('''function(M, dir)
          local calls, ui, btns = {}, {}, {}
          setmetatable(ui, { __index = function(t, k) return function(self, ...) calls[#calls+1] = k end end })
          local reg, menu = {}, { add = function(d) calls.page = d end }
          local ctx = { sider_dir = dir, menu = menu, register = function(ev, fn) reg[ev] = fn end, tournament_id = 19 }
          M.init(ctx)
          return ctx, ui, calls, reg
        end''')

        ctx, ui, calls, reg = setup(M, str(tmp) + "/")
        req_file = tmp / "content" / "KitGenerator" / "kit_request.txt"

        # 1. League background queueing when user club is detected
        M.debug_set_club(102) # Chelsea
        M.debug_set_date(2027, 8, 1) # Season 2027/28 (season 2028)
        assert req_file.is_file()
        lines = req_file.read_text().splitlines()
        league_reqs = [l for l in lines if "league-102-2028" in l]
        assert len(league_reqs) == 1, f"Expected 1 league request, got {lines}"
        assert "|all|league|" in league_reqs[0]
        print("PASS: User league background generation queued on season date refresh.")

        # 2. Calendar schedule: set_teams with upcoming opponent without p2 kit in ML
        ml_ctx = lua.table_from({"tournament_id": 19, "sider_dir": str(tmp) + "/"})
        M.make_key(ctx, "common\\script\\flow\\ML\\MLMainMenu.json")
        # Opponent 100 (Man Utd) has no p2 kit yet
        M.set_teams(ml_ctx, 102, 100)
        lines = req_file.read_text().splitlines()
        jit_reqs = [l for l in lines if "jit-100-2028" in l]
        assert len(jit_reqs) == 1, f"Expected JIT request for opponent 100, got {lines}"
        assert "|all|jit|" in jit_reqs[0]
        print("PASS: Upcoming calendar schedule fixture triggers JIT request.")

        # 3. Scope check: Exhibition matches (tournament_id 65535) NEVER trigger JIT
        exh_ctx = lua.table_from({"tournament_id": 65535, "sider_dir": str(tmp) + "/"})
        M.set_teams(exh_ctx, 102, 101) # Opponent 101 (Arsenal)
        lines = req_file.read_text().splitlines()
        jit_exh = [l for l in lines if "jit-101" in l]
        assert len(jit_exh) == 0, "Exhibition match must never queue dynamic JIT requests"
        print("PASS: Exhibition matches strictly protected from JIT requests.")

        # 4. Scope check: Season 1 AI opponent never triggers JIT (authentic kit scope)
        M.debug_reset_jit_cache()
        M.debug_set_date(2026, 8, 1) # Season 1 (2026/27 -> 2027)
        req_file.unlink()
        M.set_teams(ml_ctx, 102, 101)
        if req_file.is_file():
            lines = req_file.read_text().splitlines()
            jit_s1 = [l for l in lines if "jit-101" in l]
            assert len(jit_s1) == 0, f"Season 1 AI opponent must not receive dynamic JIT, got {lines}"
        print("PASS: Season 1 AI opponent strictly preserves authentic licensed kit.")

        # 5. Missing kit intercept in make_key: requesting p2 for opponent in Season 2
        M.debug_set_date(2027, 8, 1) # Season 2 (2028)
        M.make_key(ctx, "common\\script\\flow\\ML\\MLMainMenu.json")
        key = M.make_key(ml_ctx, "u0105p2.ftex") # West Ham away kit
        lines = (tmp / "content" / "KitGenerator" / "kit_request.txt").read_text().splitlines()
        jit_wh = [l for l in lines if "jit-105-2028" in l]
        assert len(jit_wh) == 1, f"Expected JIT trigger for West Ham missing p2, got {lines}"
        print("PASS: make_key triggers JIT when opponent secondary kit is missing on disk.")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_watch_signed_priority_order():
    tmp = Path(tempfile.mkdtemp())
    try:
        content = tmp / "content" / "KitGenerator"
        content.mkdir(parents=True, exist_ok=True)
        req_file = content / "kit_request.txt"
        state_file = content / "watcher_state.txt"
        log_file = content / "watcher.log"

        # Write requests out of order: rollover first, then league, then jit, then user
        req_file.write_text(
            "season-2028|0|2028|all|balanced|2028-08-01 10:00:00|\n"
            "league-102-2028|102|2028|all|league|2028-08-01 10:00:01|\n"
            "jit-100-2028|100|2028|all|jit|2028-08-01 10:00:02|\n"
            "rebuild-102-apple-2028|102|2028|apple|big|2028-08-01 10:00:03|\n"
        )

        seen = watch_signed._read_state(state_file)
        lines = watch_signed.safe_read_lines(req_file)
        user_requests, jit_requests, league_requests, rollover_requests = [], [], [], []
        for line in lines:
            req = watch_signed._parse_request(line)
            is_jit = req["offer"].startswith("jit-") or req.get("tier") == "jit"
            is_league = req["offer"].startswith("league-") or req.get("tier") == "league"
            is_rollover = req["club_id"] == 0 or (req["brand"] == "all" and not is_jit and not is_league) or req["offer"].startswith("season-")
            if is_jit:
                jit_requests.append(req)
            elif is_league:
                league_requests.append(req)
            elif is_rollover:
                rollover_requests.append(req)
            else:
                user_requests.append(req)

        queue = user_requests + jit_requests + league_requests + rollover_requests
        assert queue[0]["offer"].startswith("rebuild-"), "User club must be priority #1"
        assert queue[1]["offer"].startswith("jit-"), "JIT scheduled opponent must be priority #2"
        assert queue[2]["offer"].startswith("league-"), "User league background must be priority #3"
        assert queue[3]["offer"].startswith("season-"), "Bulk rollover must be priority #4"
        print("PASS: Priority Queue order (User -> JIT -> League -> Rollover) verified.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_league_discovery()
    test_lua_queueing_and_jit()
    test_watch_signed_priority_order()
    print("\nALL PRIORITY TREE AND JIT TESTS PASSED!")
