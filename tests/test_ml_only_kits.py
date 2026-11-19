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

# 9. CPU Opponents: Original authentic kits in Season 1, dynamic kits kick in from Season 2 onwards
(tmp / "content" / "KitGenerator" / "active" / "u0102p1.ftex").write_bytes(b"dummy_chelsea_ftex")
# In Season 1 (2026/27, SEASON=2027): AI opponents wear authentic kits (yields nil)
key_cpu_s1 = M.make_key(ml_ctx, "k102p1.ftex")
assert key_cpu_s1 is None, f"Expected authentic kit for AI team in Season 1, got {key_cpu_s1}"
print("PASS 9A: CPU opponent in Season 1 (2026/27) wears original authentic kit")

# In Season 2 (2027/28, SEASON=2028): dynamic kits kick in for AI clubs!
M.debug_set_date(2027, 8, 1) # Aug 2027 -> Season 2028
key_cpu_s2 = M.make_key(ml_ctx, "k102p1.ftex")
assert key_cpu_s2 == "content/KitGenerator/active/u0102p1.ftex", f"Expected dynamic kit for CPU team in Season 2, got {key_cpu_s2}"
print("PASS 9B: CPU opponent in Season 2 (2027/28) dynamic kit kicks in:", key_cpu_s2)

# Reset date back to Season 1 for font tests
M.debug_set_date(2026, 8, 1)

# 10. CPU Opponent in Exhibition Match still receives authentic kit (yields nil)
key_cpu_exh = M.make_key(exh_ctx, "k102p1.ftex")
assert key_cpu_exh is None, f"Expected authentic kit for CPU team in Exhibition, got {key_cpu_exh}"
print("PASS 10: CPU opponent in Exhibition correctly wears authentic licensed kit")

# 11. Dynamic contrasting squad numbers & font files in Master League
M.debug_set_deal("aneno", 108, 2027, 60000000, 1, 0)
(tmp / "content" / "KitGenerator" / "active" / "u0108p1_back.ftex").write_bytes(b"dummy_back_font")
(tmp / "content" / "KitGenerator" / "active" / "u0108p1_leg.ftex").write_bytes(b"dummy_leg_font")
(tmp / "content" / "KitGenerator" / "active" / "u0108p1_name.ftex").write_bytes(b"dummy_name_font")

key_font_b = M.make_key(ml_ctx, "k108p1_b.ftex")
assert key_font_b == "content/KitGenerator/active/u0108p1_back.ftex", f"Expected active back number, got {key_font_b}"
key_font_back = M.make_key(ml_ctx, "u0108p1_back.ftex")
assert key_font_back == "content/KitGenerator/active/u0108p1_back.ftex", f"Expected active back number (u* format), got {key_font_back}"
key_font_l = M.make_key(ml_ctx, "k108p1_l.ftex")
assert key_font_l == "content/KitGenerator/active/u0108p1_leg.ftex", f"Expected active leg number, got {key_font_l}"
key_font_n = M.make_key(ml_ctx, "k108p1_n.ftex")
assert key_font_n == "content/KitGenerator/active/u0108p1_name.ftex", f"Expected active name font, got {key_font_n}"
print("PASS 11: Dynamic contrasting font textures intercepted and served in Master League (back, leg, name)")

# 12. Non-font textures like _srm and missing active files yield nil (fall back to authentic/kitserver)
key_srm = M.make_key(ml_ctx, "k108p1_srm.ftex")
assert key_srm is None, f"Expected nil for _srm texture, got {key_srm}"
key_chest_missing = M.make_key(ml_ctx, "k108p1_c.ftex")
assert key_chest_missing is None, f"Expected nil when chest number file not in active folder, got {key_chest_missing}"
print("PASS 12: Specular maps (_srm) and missing active font files yield nil (fall back to kitserver)")

# 13. Dynamic fonts NEVER served in Exhibition match or Edit Mode (authentic fonts preserved!)
key_font_exh = M.make_key(exh_ctx, "k108p1_b.ftex")
assert key_font_exh is None, f"Expected authentic font in Exhibition match, got {key_font_exh}"
M.set_home_team_for_kits(ctx, 108, 1) # Edit mode
key_font_edit = M.make_key(ctx, "k108p1_b.ftex")
assert key_font_edit is None, f"Expected authentic font in Edit mode, got {key_font_edit}"
print("PASS 13: Authentic fonts preserved untouched in Exhibition and Edit mode")

# 14. Dynamic Goalkeeper kits (g1 / g2) intercepted in Master League
M.set_home_team_for_kits(ctx, 108, 0) # Exit edit mode
(tmp / "content" / "KitGenerator" / "active" / "u0108g1.ftex").write_bytes(b"dummy_gk1_ftex")
(tmp / "content" / "KitGenerator" / "active" / "u0108g2.ftex").write_bytes(b"dummy_gk2_ftex")
(tmp / "content" / "KitGenerator" / "active" / "u0108g1_back.ftex").write_bytes(b"dummy_gk1_back_font")

key_gk1 = M.make_key(ml_ctx, "k108g1.ftex")
assert key_gk1 == "content/KitGenerator/active/u0108g1.ftex", f"Expected dynamic GK1 kit, got {key_gk1}"
key_gk1_u = M.make_key(ml_ctx, "u0108g1.ftex")
assert key_gk1_u == "content/KitGenerator/active/u0108g1.ftex", f"Expected dynamic GK1 kit (u* format), got {key_gk1_u}"
key_gk2 = M.make_key(ml_ctx, "k108g2.ftex")
assert key_gk2 == "content/KitGenerator/active/u0108g2.ftex", f"Expected dynamic GK2 kit, got {key_gk2}"
key_gk1_font = M.make_key(ml_ctx, "k108g1_b.ftex")
assert key_gk1_font == "content/KitGenerator/active/u0108g1_back.ftex", f"Expected dynamic GK1 font, got {key_gk1_font}"
print("PASS 14: Dynamic Goalkeeper kits (g1, g2) and GK fonts intercepted and served in Master League")

# 15. Goalkeeper kits in Exhibition and Edit mode strictly wear authentic licensed kits (yield nil)
key_gk1_exh = M.make_key(exh_ctx, "k108g1.ftex")
assert key_gk1_exh is None, f"Expected authentic GK kit in Exhibition, got {key_gk1_exh}"
key_gk2_exh = M.make_key(exh_ctx, "u0108g2.ftex")
assert key_gk2_exh is None, f"Expected authentic GK2 kit in Exhibition, got {key_gk2_exh}"
M.set_home_team_for_kits(ctx, 108, 1) # Edit mode
key_gk1_edit = M.make_key(ctx, "k108g1.ftex")
assert key_gk1_edit is None, f"Expected authentic GK kit in Edit mode, got {key_gk1_edit}"
print("PASS 15: Authentic Goalkeeper kits strictly preserved in Exhibition and Edit mode")

shutil.rmtree(tmp, ignore_errors=True)
print("ALL MASTER LEAGUE-ONLY SCOPE TESTS PASSED!")
