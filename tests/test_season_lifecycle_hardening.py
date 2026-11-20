"""Regression tests for the season-lifecycle hardening fixes.

Covers:
  1. No bulk rollover is queued during Season 1.
  2. An expired/terminated deal cannot serve its old branded kit while the
     forced clean rebuild is still in flight.
  3. A scheduled opponent with only some matchday slots still gets a JIT build.
  4. The watcher does not skip a "force" clean just because the old file exists.
"""
import inspect
import shutil
import sys
import tempfile
from pathlib import Path

from lupa import LuaRuntime

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT / "generator") not in sys.path:
    sys.path.insert(0, str(ROOT / "generator"))

import build_all_clubs  # noqa: E402
import watch_signed  # noqa: E402


SETUP_LUA = '''function(M, dir)
  local calls, ui = {}, {}
  setmetatable(ui, { __index = function(t, k) return function(self, ...) calls[#calls+1] = k end end })
  local reg, menu = {}, { add = function(d) calls.page = d end }
  local ctx = { sider_dir = dir, menu = menu, register = function(ev, fn) reg[ev] = fn end, tournament_id = 19 }
  M.init(ctx)
  return ctx, ui, calls, reg
end'''


def _load_module(tmp):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('log=function(s) LOGS=(LOGS or "")..s.."\\n" end; ffi=nil')
    M = lua.eval('function(src) return load(src)() end')(
        (ROOT / "modules/KitGenerator.lua").read_text())
    ctx, ui, calls, reg = lua.eval(SETUP_LUA)(M, str(tmp) + "/")
    return lua, M, ctx


def _prepare(tmp):
    content = tmp / "content"
    (content / "KitGenerator" / "active").mkdir(parents=True, exist_ok=True)
    (content / "kits").mkdir(parents=True, exist_ok=True)
    return content / "KitGenerator" / "kit_request.txt"


def test_season_1_never_queues_bulk_rollover():
    tmp = Path(tempfile.mkdtemp())
    try:
        _prepare(tmp)
        _lua, M, _ctx = _load_module(tmp)
        # Season 1 (SEASON 2027): the old code queued a bogus season-2027
        # rollover whenever the calendar moved inside the first season.
        assert M.debug_should_queue_rollover(2027, 2026) is False
        assert M.debug_should_queue_rollover(2027, 2028) is False
        # Season 2 (SEASON 2028) must still roll over normally.
        assert M.debug_should_queue_rollover(2028, 2027) is True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_expired_deal_never_serves_stale_branded_kit():
    tmp = Path(tempfile.mkdtemp())
    try:
        req_file = _prepare(tmp)
        active = tmp / "content" / "KitGenerator" / "active"
        (active / "u0108p1.ftex").write_bytes(b"BRANDED_OLD_SPONSOR")
        lua, M, ctx = _load_module(tmp)
        ml_ctx = lua.table_from({"tournament_id": 19, "sider_dir": str(tmp) + "/"})

        M.debug_set_club(108)
        M.debug_set_date(2027, 8, 1)          # Season 2028
        M.debug_set_deal("spotify", 108, 2028, 60000000, 2, 0)
        M.make_key(ctx, "common\\script\\flow\\ML\\MLMainMenu.json")
        assert M.make_key(ml_ctx, "k108p1.ftex") == \
            "content/KitGenerator/active/u0108p1.ftex"

        # Deal ends: a forced clean request is queued and the old branded file
        # is still physically present.
        M.debug_terminate()
        clean_lines = [line for line in req_file.read_text().splitlines()
                       if line.startswith("clean-108-2028-t")]
        assert clean_lines and "|force|" in clean_lines[-1], clean_lines
        req_id = clean_lines[-1].split("|")[0]

        # Until the watcher records the request, authentic kit must be served.
        assert M.make_key(ml_ctx, "k108p1.ftex") is None

        # Once the watcher has rebuilt the kit, the dynamic pool is used again.
        state_file = tmp / "content" / "KitGenerator" / "watcher_state.txt"
        state_file.write_text(req_id + "\n")
        assert M.debug_reset_clean_check(108, 2028)
        assert M.make_key(ml_ctx, "k108p1.ftex") == \
            "content/KitGenerator/active/u0108p1.ftex"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_partial_matchday_set_still_triggers_jit():
    tmp = Path(tempfile.mkdtemp())
    try:
        req_file = _prepare(tmp)
        active = tmp / "content" / "KitGenerator" / "active"
        (active / "u0105p2.ftex").write_bytes(b"OLD_P2_ONLY")  # p3/g2 missing
        lua, M, ctx = _load_module(tmp)
        ml_ctx = lua.table_from({"tournament_id": 19, "sider_dir": str(tmp) + "/"})
        M.debug_set_club(102)
        M.debug_set_date(2027, 8, 1)
        M.make_key(ctx, "common\\script\\flow\\ML\\MLMainMenu.json")
        M.debug_reset_jit_cache()
        if req_file.is_file():
            req_file.unlink()

        M.set_teams(ml_ctx, 102, 105)
        lines = req_file.read_text().splitlines()
        assert [line for line in lines if "jit-105-2028" in line], lines
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_watcher_forces_clean_when_branded_file_exists(tmp_path, monkeypatch):
    sider = tmp_path / "SiderAddons"
    active = sider / "content" / "KitGenerator" / "active"
    active.mkdir(parents=True)
    (active / "u0102p1.ftex").write_bytes(b"BRANDED_OLD_SPONSOR")

    req_file = tmp_path / "kit_request.txt"
    state_file = tmp_path / "watcher_state.txt"
    log_file = tmp_path / "watcher.log"
    calls = []
    monkeypatch.setattr(watch_signed, "rebuild",
                        lambda *a, **kw: calls.append((a, kw)) or [])

    # The request is already in watcher_state and the file exists: a normal
    # clean would be skipped, but a forced clean must still rebuild.
    req_file.write_text("clean-normal-102-2028|102|2028|||2026-11-20 10:00:00\n")
    state_file.write_text("clean-normal-102-2028\n\n")
    assert watch_signed.process_pending(req_file, state_file, sider, tmp_path, log_file) == 0
    assert not calls

    req_file.write_text("clean-force-102-2028|102|2028||force|2026-11-20 10:00:01\n")
    state_file.write_text("some-older-request\n\n")
    assert watch_signed.process_pending(req_file, state_file, sider, tmp_path, log_file) == 1
    assert len(calls) == 1
    assert calls[0][0][2] is None                  # brand -> sponsorless rebuild

    # A forced clean must be deduplicated like any other processed request.
    # Otherwise it rebuilds forever and overwrites a newly signed sponsor.
    assert watch_signed.process_pending(req_file, state_file, sider, tmp_path, log_file) == 0
    assert len(calls) == 1


def test_season_refresh_forces_regeneration_and_protects_user(tmp_path, monkeypatch):
    sider = tmp_path / "SiderAddons"
    active = sider / "content" / "KitGenerator" / "active"
    active.mkdir(parents=True)
    (active / "u0102p1.ftex").write_bytes(b"OLD_2028")
    (active / "u0102p2.ftex").write_bytes(b"OLD_2028_SECONDARY")
    (active / "u0105p1.ftex").write_bytes(b"USER_SIGNED_BRAND")
    (active / "u0105p2.ftex").write_bytes(b"USER_SECONDARY")

    monkeypatch.setattr(build_all_clubs, "load_user_club_info",
                        lambda _s: (105, "sharp", True))

    def fake_all(**kwargs):
        assert kwargs["skip_existing"] is False, kwargs
        out = kwargs["outdir"]
        (out / "u0102p1.ftex").write_bytes(b"NEW_2029")
        (out / "u0105p1.ftex").write_bytes(b"MUST_NOT_OVERWRITE_USER")
        return {"generated": 2}

    monkeypatch.setattr(build_all_clubs, "generate_all_kits", fake_all)
    stats = build_all_clubs.refresh_season_kits(
        2029, sider, slots="1,g1", scope="baseline", prune_secondary=True)

    assert (active / "u0102p1.ftex").read_bytes() == b"NEW_2029"
    assert (active / "u0105p1.ftex").read_bytes() == b"USER_SIGNED_BRAND"
    assert not (active / "u0102p2.ftex").exists()
    assert (active / "u0105p2.ftex").exists()
    assert stats["copied"] == 1
    assert stats["pruned"] == 1


def test_league_refresh_uses_staging_and_full_slot_set(tmp_path, monkeypatch):
    params = inspect.signature(build_all_clubs.generate_club_kits).parameters
    assert "staging_dir" in params          # refresh passes staging_dir explicitly
    assert "install" in params              # and keeps output out of active until copy

    sider = tmp_path / "SiderAddons"
    active = sider / "content" / "KitGenerator" / "active"
    active.mkdir(parents=True)
    (active / "u0105p1.ftex").write_bytes(b"USER_SIGNED_BRAND")

    monkeypatch.setattr(build_all_clubs, "load_user_club_info",
                        lambda _s: (105, "sharp", True))

    def fake_club(**kwargs):
        assert kwargs["install"] is False, kwargs
        assert kwargs["skip_existing"] is False, kwargs
        out = kwargs["staging_dir"]
        cid = kwargs["club_id"]
        (out / f"u{cid:04d}p1.ftex").write_bytes(b"NEW")
        (out / f"u{cid:04d}p1_back.ftex").write_bytes(b"NEW_FONT")

    monkeypatch.setattr(build_all_clubs, "generate_club_kits", fake_club)
    stats = build_all_clubs.refresh_season_kits(
        2029, sider, slots="1,2,3,g1,g2", team_ids=[105, 103], scope="league")

    assert (active / "u0103p1.ftex").read_bytes() == b"NEW"
    assert (active / "u0103p1_back.ftex").read_bytes() == b"NEW_FONT"
    assert (active / "u0105p1.ftex").read_bytes() == b"USER_SIGNED_BRAND"
    assert stats["clubs"] == 1
    assert stats["copied"] == 2


def test_pruned_marker_does_not_replay_old_season_jit(tmp_path, monkeypatch):
    sider = tmp_path / "SiderAddons"
    active = sider / "content" / "KitGenerator" / "active"
    active.mkdir(parents=True)                       # deliberately no p2 file
    for i in range(100):                             # completed rollover has a baseline
        (active / f"u{i:04d}p1.ftex").write_bytes(b"BASELINE")
    req_file = tmp_path / "kit_request.txt"
    state_file = tmp_path / "watcher_state.txt"
    log_file = tmp_path / "watcher.log"

    req_file.write_text(
        "season-ml-2029|0|2029|all|balanced|2026-11-20 13:40:00|ml_0105\n"
        "jit-4194-2028|4194|2028|all|jit|2026-11-20 12:00:00|ml_0105\n")
    state_file.write_text("season-ml-2029\n\n")

    calls = []
    monkeypatch.setattr(build_all_clubs, "generate_club_kits",
                        lambda **kw: calls.append(kw) or {})

    assert watch_signed.process_pending(req_file, state_file, sider,
                                        tmp_path, log_file) == 0
    assert calls == []                                # stale 2028 JIT stays retired
    assert "jit-4194-2028" in state_file.read_text()


def test_retired_deal_regenerates_sponsorless_next_season():
    tmp = Path(tempfile.mkdtemp())
    try:
        req_file = _prepare(tmp)
        _lua, M, _ctx = _load_module(tmp)
        M.debug_set_club(108)
        M.debug_set_date(2027, 8, 1)                  # Season 2028
        M.debug_set_deal("spotify", 108, 2028, 60000000, 1, 0)  # ends after 2028
        req_file.write_text("")                       # isolate the next transition

        M.debug_set_date(2028, 8, 1)                  # Season 2029 - deal retired
        lines = req_file.read_text().splitlines()
        assert any(l.startswith("clean-108-2029-") and "|force|" in l for l in lines), lines
        assert not any(l.startswith("rebuild-108-spotify-2029") for l in lines), lines
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_active_multiyear_deal_rebuilds_branded_kit_each_season():
    tmp = Path(tempfile.mkdtemp())
    try:
        req_file = _prepare(tmp)
        _lua, M, _ctx = _load_module(tmp)
        M.debug_set_club(108)
        M.debug_set_deal("spotify", 108, 2028, 60000000, 3, 0)
        M.debug_set_date(2027, 8, 1)                  # Season 2028
        assert any(l.startswith("rebuild-108-spotify-2028") for l in
                   req_file.read_text().splitlines())

        req_file.write_text("")
        M.debug_set_date(2028, 8, 1)                  # Season 2029 - still under contract
        lines = req_file.read_text().splitlines()
        assert any(l.startswith("rebuild-108-spotify-2029") for l in lines), lines
        assert not any(l.startswith("clean-108-2029") for l in lines), lines
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_ai_sponsors_hold_for_contract_then_rotate():
    brands = ["a", "b", "c", "d"]
    club = {"id": 100}
    first = build_all_clubs.pick_ai_sponsor(club, 2028, brands)
    assert build_all_clubs.pick_ai_sponsor(club, 2029, brands) == first  # 2-year deal
    rotated = build_all_clubs.pick_ai_sponsor(club, 2030, brands)
    expected = build_all_clubs.season_rng(100, 2030, salt="ai-sponsor-deal").choice(brands)
    assert rotated == expected                     # new contract cycle from 2030
