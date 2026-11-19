"""test_ml_only_kits.py - Verify that dynamic kits are strictly Master League-only.

Asserts:
  1. Exhibition matches (tournament_id == 65535) yield nil -> authentic kit.
  2. Edit mode yields nil -> authentic kit.
  3. Non-ML flow (Top, Exhibition menu) yields nil -> authentic kit.
  4. Master League fixture (tournament_id == 19) and ML flow returns the dynamic kit key!
"""
import tempfile, shutil
from pathlib import Path
from lupa import LuaRuntime

root = Path(__file__).resolve().parent.parent
tmp = Path(tempfile.mkdtemp())
shutil.copytree(root / "content", tmp / "content")

# Create fake active kit in staging
active_dir = tmp / "content" / "KitGenerator" / "active"
active_dir.mkdir(parents=True, exist_ok=True)
fake_kit = active_dir / "u0108p1.ftex"
fake_kit.write_bytes(b"FTEX_DYNAMIC_KIT_CONTENT")

lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute('log=function(s) LOGS=(LOGS or "")..s.."\\n" end; ffi=nil')
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
M.debug_set_club(108) # Barcelona
M.debug_set_date(2026, 8, 1) # Season 2026/27 (Aug 2026 -> season 2027)

# Sign a deal
M.debug_set_deal("aneno", 108, 2027, 60000000, 1, 0)

# 1. Non-ML flow: user is on Top screen
M.make_key(ctx, "common\\script\\flow\\Top\\TopMenu.json")
key = M.make_key(ctx, "u0108p1.ftex")
assert key is None, f"Expected nil in Top flow, got {key}"
print("PASS 1: Non-ML flow (Top menu) yields nil (authentic kit)")

# 2. Exhibition match: tournament_id == 65535
exh_ctx = lua.table_from({"tournament_id": 65535, "sider_dir": str(tmp) + "/"})
key = M.make_key(exh_ctx, "u0108p1.ftex")
assert key is None, f"Expected nil in Exhibition match, got {key}"
key_k = M.make_key(exh_ctx, "k108p1.ftex")
assert key_k is None, f"Expected nil for Kitserver key in Exhibition match, got {key_k}"
print("PASS 2: Exhibition matches (tournament_id 65535) yield nil for both u* and k* keys")

# 3. Edit mode
M.set_home_team_for_kits(ctx, 108, 1) # edit_mode = 1
key = M.make_key(ctx, "u0108p1.ftex")
assert key is None, f"Expected nil in Edit mode, got {key}"
print("PASS 3: Edit mode yields nil (authentic kit)")

# 4. Master League match: ML flow active and tournament_id == 19 (LaLiga)
M.set_home_team_for_kits(ctx, 108, 0) # exit edit mode
M.debug_set_deal("aneno", 108, 2027, 60000000, 1, 0)
M.make_key(ctx, "common\\script\\flow\\ML\\MLMainMenu.json")
ml_ctx = lua.table_from({"tournament_id": 19, "sider_dir": str(tmp) + "/"})
M.set_teams(ml_ctx, 108, 109) # Career fixture
print("club_id:", M.debug_club_id(), "deal:", M.status().deal)
key = M.make_key(ml_ctx, "k108p1.ftex") # Kitserver request in ML match
assert key == "content/KitGenerator/active/u0108p1.ftex", f"Expected dynamic kit key, got {key}"
print("PASS 4: Master League match intercepts and serves dynamic kit:", key)

# 5. Master League menu: Squad list player texture
key_menu = M.make_key(ml_ctx, "Asset\\model\\character\\uniform\\texture\\#windx11\\u0108p1.ftex")
assert key_menu == "content/KitGenerator/active/u0108p1.ftex", f"Expected dynamic kit key in ML menu, got {key_menu}"
print("PASS 5: Master League menu serves dynamic kit to 3D player:", key_menu)

# 6. Verify get_filepath resolves the absolute disk path
fp = M.get_filepath(ml_ctx, "k108p1.ftex", key)
expected_fp = str(tmp / "content" / "KitGenerator" / "active" / "u0108p1.ftex").replace("/", "\\")
assert fp == expected_fp, f"Expected {expected_fp}, got {fp}"
print("PASS 6: get_filepath resolves absolute disk path correctly:", fp)

# 7. Sponsorless kit at new season (expired deal, opted-in): serves clean dynamic kit in ML, authentic in Exhibition
M.debug_clear_deal()
key_clean_ml = M.make_key(ml_ctx, "k108p1.ftex")
assert key_clean_ml == "content/KitGenerator/active/u0108p1.ftex", f"Expected clean dynamic kit in ML, got {key_clean_ml}"
key_clean_exh = M.make_key(exh_ctx, "k108p1.ftex")
assert key_clean_exh is None, f"Expected authentic kit in Exhibition even without deal, got {key_clean_exh}"
print("PASS 7: Sponsorless new-season dynamic kit active in ML, authentic kit preserved in Exhibition")

# 8. Un-opted club in Season 1 (never signed a sponsor): yields nil even in ML -> authentic kit preserved!
M.debug_clear_opted_in()
key_unopted_ml = M.make_key(ml_ctx, "k108p1.ftex")
assert key_unopted_ml is None, f"Expected authentic kit in ML for un-opted club, got {key_unopted_ml}"
print("PASS 8: Un-opted club in ML correctly wears authentic kit until sponsor is signed")

shutil.rmtree(tmp, ignore_errors=True)
print("ALL MASTER LEAGUE-ONLY SCOPE TESTS PASSED!")
