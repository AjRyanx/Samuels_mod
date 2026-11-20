"""Regression tests for the season-lifecycle hardening fixes.

Covers:
  1. No bulk rollover is queued during Season 1.
  2. An expired/terminated deal cannot serve its old branded kit while the
     forced clean rebuild is still in flight.
  3. A scheduled opponent with only some matchday slots still gets a JIT build.
  4. The watcher does not skip a "force" clean just because the old file exists.
"""
import shutil
import sys
import tempfile
from pathlib import Path

from lupa import LuaRuntime

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT / "generator") not in sys.path:
    sys.path.insert(0, str(ROOT / "generator"))

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
    state_file.write_text("clean-force-102-2028\n\n")
    assert watch_signed.process_pending(req_file, state_file, sider, tmp_path, log_file) == 1
    assert len(calls) == 1
    assert calls[0][0][2] is None                  # brand -> sponsorless rebuild
