"""Runs KitGenerator.lua's init, club auto-detection, Mod Menu page build, sign
and counter with fake sider objects.  Not a game test.

Run:  python tests/smoke_test.py
"""
import tempfile, shutil, sys
from pathlib import Path
from lupa import LuaRuntime

root = Path(__file__).resolve().parent.parent
tmp = Path(tempfile.mkdtemp()); shutil.copytree(root / "content", tmp / "content")
lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute('log=function(s) LOGS=(LOGS or "")..s.."\\n" end; ffi=nil')
lua.execute('local _orig_open=io.open; io.open=function(p, m) return _orig_open(p:gsub("\\\\", "/"), m) end')
M = lua.eval('function(src) return load(src)() end')((root / "modules/KitGenerator.lua").read_text())

setup = lua.eval('''function(M, dir)
  local calls, ui, btns = {}, {}, {}
  setmetatable(ui, { __index = function(t, k) return function(self, ...) calls[#calls+1] = k; local a = {...}; if k=='button' then btns[a[1]] = a[3] end return nil end end })
  local reg, menu = {}, { add = function(d) calls.page = d end }
  local ctx = { sider_dir = dir, menu = menu, register = function(ev, fn) reg[ev] = fn end, tournament_id = 100 }
  M.init(ctx)
  return ctx, ui, calls, reg, btns
end''')
ctx, ui, calls, reg, btns = setup(M, str(tmp) + "/")
assert calls.page and calls.page.id == "sponsors"
build = calls.page.build

# ---- 1. nothing detected yet ------------------------------------------------
assert M.debug_club_id() is None, "club should start undetected"
build(ui, ctx)                                   # mode off -> club card only
reg["key_down"](ctx, 0x77)                       # F8: manual Master League on

# a friendly (tournament_id 65535) must NOT feed the learner
exh = lua.table_from({"tournament_id": 65535})
reg["set_teams"](exh, 999, 888)
assert M.debug_club_id() is None, "an exhibition must not teach the club"

# ---- 2. auto-detect from career matches -------------------------------------
career = lua.table_from({"tournament_id": 1027})  # a career fixture (not 65535)
for opp in (101, 101, 127, 4183):                 # our club 71579 plays them all
    reg["set_teams"](career, 71579, opp)
M.debug_set_date(2027, 8, 1)                      # a real in-game date
print("auto-detected club:", M.debug_club_id(), "source:", M.status()["club_source"])
assert M.debug_club_id() == 71579, M.debug_club_id()
assert M.status()["club_source"] == "career"
reg["set_teams"](exh, 999, 888)                   # friendly: club must not change
assert M.debug_club_id() == 71579

# ---- 2b. a stale saved club is replaced ------------------------------------
M.debug_set_club(102)                             # pretend an old career saved Chelsea
M.debug_reset_votes()                             # fresh session: no votes yet
for _opp in (301, 302):                           # ...but the club playing is 205
    reg["set_teams"](career, 205, _opp)
assert M.debug_club_id() == 205, M.debug_club_id()
M.debug_set_club(71579)
M.debug_reset_votes()

# ---- 3. offers for the detected club ----------------------------------------
M.debug_set_club(71579)
M.debug_set_date(2027, 8, 1)
for k in list(calls):
    if isinstance(k, int): del calls[k]
build(ui, ctx)
n_img = sum(1 for k in calls.values() if k == "image")
n_off = M.debug_visible_count()
print("curated offers:", n_off, "image calls:", n_img)
assert n_off >= 1 and n_img == min(4, n_off), (n_off, n_img)

# ---- 4. synthesised offers for a club deals.txt does not cover --------------
M.debug_set_club(6001)
assert M.debug_visible_count() >= 1, "a club outside deals.txt must still get offers"
print("synthesised offers for club 6001:", M.debug_visible_count())
M.debug_set_club(71579)

# ---- 5. counter + sign ------------------------------------------------------
btns["ctr1"](); build(ui, ctx); btns["send"](); build(ui, ctx)
print("counter ran without error")
btns["sign1"](); assert (tmp / "content/KitGenerator/signed.txt").exists()
assert M.status()["deal"], "a deal should be active after signing"
print("signed; active deal:", M.status()["deal"])
print("LOGS:", lua.globals().LOGS.strip().splitlines()[:3])
print("SMOKE OK")
