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

def test_master_league_only_scope():
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
    M.debug_set_deal("spotify", 108, 2027, 60000000, 1, 0)

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
    M.debug_set_deal("spotify", 108, 2027, 60000000, 1, 0)
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

    # 7. Season 1 without active sponsor: user club wears authentic default licensed kit!
    M.debug_clear_deal()
    key_clean_s1 = M.make_key(ml_ctx, "k108p1.ftex")
    assert key_clean_s1 is None, f"Expected authentic kit in Season 1 for user club without deal, got {key_clean_s1}"
    key_clean_exh = M.make_key(exh_ctx, "k108p1.ftex")
    assert key_clean_exh is None, f"Expected authentic kit in Exhibition, got {key_clean_exh}"
    print("PASS 7: Season 1 without active sponsor: user club wears authentic default kit in ML and Exhibition")

    # 8. Season 2 onwards: user club automatically changes kits and wears sponsorless dynamic kit until signing a deal!
    M.debug_set_date(2027, 8, 1) # Aug 2027 -> Season 2028 (Season 2)
    key_s2_ml = M.make_key(ml_ctx, "k108p1.ftex")
    assert key_s2_ml == "content/KitGenerator/active/u0108p1.ftex", f"Expected dynamic sponsorless kit in Season 2 ML, got {key_s2_ml}"
    key_s2_exh = M.make_key(exh_ctx, "k108p1.ftex")
    assert key_s2_exh is None, f"Expected authentic kit in Exhibition even in Season 2, got {key_s2_exh}"
    print("PASS 8: Season 2: User club receives dynamic sponsorless kit in ML, authentic kit strictly preserved in Exhibition")

    # 9. CPU Opponents: Original authentic kits in Season 1, dynamic kits kick in from Season 2 onwards
    (tmp / "content" / "KitGenerator" / "active" / "u0102p1.ftex").write_bytes(b"dummy_chelsea_ftex")
    # In Season 1 (2026/27, SEASON=2027): AI opponents wear authentic kits (yields nil)
    M.debug_set_date(2026, 8, 1) # Back to Season 1
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
    M.debug_set_deal("spotify", 108, 2027, 60000000, 1, 0)
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

    # 16. Multi-Career Isolation for the same club (e.g. Chelsea #102)
    M.set_home_team_for_kits(ctx, 102, 0)
    M.debug_set_club(102)

    # Set up Career A profile folder for Chelsea
    career_a_dir = tmp / "content" / "KitGenerator" / "careers" / "ml_0102_saveA"
    career_a_dir.mkdir(parents=True, exist_ok=True)
    (career_a_dir / "u0102p1.ftex").write_bytes(b"CHELSEA_SAVE_A_THREE")
    (career_a_dir / "active_deal.txt").write_text("102-2027-1|102|three|2027|3|120000000|big|2026-11-19 12:00:00|0\n")

    # Set up Career B profile folder for Chelsea
    career_b_dir = tmp / "content" / "KitGenerator" / "careers" / "ml_0102_saveB"
    career_b_dir.mkdir(parents=True, exist_ok=True)
    (career_b_dir / "u0102p1.ftex").write_bytes(b"CHELSEA_SAVE_B_YOKOHAMA")
    (career_b_dir / "active_deal.txt").write_text("102-2027-2|102|yokohama|2027|1|90000000|mid|2026-11-19 12:00:00|0\n")

    # Global fallback for Chelsea in active/
    (tmp / "content" / "KitGenerator" / "active" / "u0102p1.ftex").write_bytes(b"CHELSEA_GLOBAL_PREGEN")

    # In Career A: serves Career A kit
    M.debug_set_career("ml_0102_saveA")
    key_save_a = M.make_key(ml_ctx, "u0102p1.ftex")
    assert key_save_a == "content/KitGenerator/careers/ml_0102_saveA/u0102p1.ftex", f"Expected Save A kit, got {key_save_a}"
    st_a = M.status()
    assert st_a["deal"] == "three", f"Expected Three deal in Save A, got {st_a['deal']}"
    print("PASS 16A: Multi-Career Chelsea Save A serves Save A's isolated Three kit")

    # Hot-switch to Career B: serves Career B kit
    M.debug_set_career("ml_0102_saveB")
    key_save_b = M.make_key(ml_ctx, "u0102p1.ftex")
    assert key_save_b == "content/KitGenerator/careers/ml_0102_saveB/u0102p1.ftex", f"Expected Save B kit, got {key_save_b}"
    st_b = M.status()
    assert st_b["deal"] == "yokohama", f"Expected Yokohama deal in Save B, got {st_b['deal']}"
    print("PASS 16B: Hot-switching to Chelsea Save B instantly serves Save B's isolated Yokohama kit")

    # New Career C with Chelsea (no deal signed, no profile folder yet):
    # In Season 1: wears authentic default kit
    M.debug_set_career("ml_0102_saveC")
    key_save_c_s1 = M.make_key(ml_ctx, "u0102p1.ftex")
    assert key_save_c_s1 is None, f"Expected authentic kit in Save C Season 1, got {key_save_c_s1}"
    st_c = M.status()
    assert st_c["deal"] is None, f"Expected no deal in Save C, got {st_c['deal']}"
    print("PASS 16C-1: New Chelsea Save C in Season 1 wears authentic default kit without deal")

    # In Season 2: falls back to active/ pool as sponsorless dynamic kit
    M.debug_set_date(2027, 8, 1) # Season 2
    key_save_c_s2 = M.make_key(ml_ctx, "u0102p1.ftex")
    assert key_save_c_s2 == "content/KitGenerator/active/u0102p1.ftex", f"Expected active kit in Save C Season 2, got {key_save_c_s2}"
    print("PASS 16C-2: Chelsea Save C in Season 2 receives dynamic sponsorless kit from active/ pool")
    M.debug_set_date(2026, 8, 1) # Reset to Season 1

    # In Exhibition: Chelsea always wears authentic kit regardless of which save is active
    key_chelsea_exh = M.make_key(exh_ctx, "u0102p1.ftex")
    assert key_chelsea_exh is None, f"Expected authentic kit in Exhibition for Chelsea, got {key_chelsea_exh}"
    print("PASS 16D: Exhibition match strictly preserves authentic kit for Chelsea across all saves")

    # 17. Authentic GDB Fallback Resolver for Cold-Boot Master League Menus
    # When entering ML on cold boot (before playing a match or visiting Edit Mode),
    # PES requests u<tid>p<slot>.ftex.
    # Previously, returning nil caused the game to fall back to default CPK kits.
    # With the GDB fallback resolver, KitGenerator maps the team via content/kits/map.txt
    # and directly serves the authentic GDB texture!
    gdb_dir = tmp / "content" / "kits"
    gdb_dir.mkdir(parents=True, exist_ok=True)
    map_content = """# VirtuaRED kits map
    101, "Premier League\\Arsenal"
    108, "LaLiga EA SPORTS\\Barcelona"
    """
    (gdb_dir / "map.txt").write_text(map_content)

    arsenal_p1 = gdb_dir / "Premier League" / "Arsenal" / "p1"
    arsenal_p1.mkdir(parents=True, exist_ok=True)
    (arsenal_p1 / "u0101p1.ftex").write_bytes(b"AUTHENTIC_GDB_ARSENAL_P1")
    (arsenal_p1 / "u0101p1_back.ftex").write_bytes(b"AUTHENTIC_GDB_ARSENAL_P1_BACK")

    arsenal_g1 = gdb_dir / "Premier League" / "Arsenal" / "g1"
    arsenal_g1.mkdir(parents=True, exist_ok=True)
    (arsenal_g1 / "u0101g1.ftex").write_bytes(b"AUTHENTIC_GDB_ARSENAL_G1")

    M.debug_reload_gdb_map()

    # 17A: Club without existing dynamic kit in ML cold-boot menu resolves authentic GDB fallback kit
    M.set_home_team_for_kits(ctx, 101, 0)
    M.debug_set_club(101) # Manage Arsenal
    M.debug_set_date(2026, 8, 1)

    key_arsenal_ml = M.make_key(ml_ctx, "u0101p1.ftex")
    expected_gdb_key = "content/kits/Premier League/Arsenal/p1/u0101p1.ftex"
    assert key_arsenal_ml == expected_gdb_key, f"Expected authentic GDB kit key {expected_gdb_key}, got {key_arsenal_ml}"
    print("PASS 17A: Cold boot ML menu resolves authentic GDB fallback kit when dynamic kit not on disk yet:", key_arsenal_ml)

    # 17B: Authentic GDB back number font resolved in ML cold-boot menu
    key_arsenal_font = M.make_key(ml_ctx, "u0101p1_back.ftex")
    expected_gdb_font = "content/kits/Premier League/Arsenal/p1/u0101p1_back.ftex"
    assert key_arsenal_font == expected_gdb_font, f"Expected authentic GDB font {expected_gdb_font}, got {key_arsenal_font}"
    print("PASS 17B: Cold boot ML menu resolves authentic GDB font:", key_arsenal_font)

    # 17C: Authentic GDB GK kit resolved in ML cold-boot menu
    key_arsenal_gk = M.make_key(ml_ctx, "u0101g1.ftex")
    expected_gdb_gk = "content/kits/Premier League/Arsenal/g1/u0101g1.ftex"
    assert key_arsenal_gk == expected_gdb_gk, f"Expected authentic GDB GK kit {expected_gdb_gk}, got {key_arsenal_gk}"
    print("PASS 17C: Cold boot ML menu resolves authentic GDB GK kit:", key_arsenal_gk)

    # 17D: In Exhibition matches, authentic GDB resolver strictly yields nil (Kitserver handles exhibition)
    key_arsenal_exh = M.make_key(exh_ctx, "u0101p1.ftex")
    assert key_arsenal_exh is None, f"Expected nil in Exhibition match, got {key_arsenal_exh}"
    print("PASS 17D: Exhibition matches strictly yield nil (authentic Kitserver unaffected)")

    # 17E: In Edit mode, authentic GDB resolver strictly yields nil (Edit mode unaffected)
    M.set_home_team_for_kits(ctx, 101, 1) # Edit mode
    key_arsenal_edit = M.make_key(ctx, "u0101p1.ftex")
    assert key_arsenal_edit is None, f"Expected nil in Edit mode, got {key_arsenal_edit}"
    print("PASS 17E: Edit mode strictly yields nil (authentic Kitserver unaffected)")
    M.set_home_team_for_kits(ctx, 101, 0) # Exit edit mode

    # 17F: get_filepath resolves GDB authentic kit path to exact disk location
    fp_gdb = M.get_filepath(ml_ctx, "u0101p1.ftex", key_arsenal_ml)
    expected_fp_gdb = str(arsenal_p1 / "u0101p1.ftex").replace("/", "\\")
    assert fp_gdb == expected_fp_gdb, f"Expected {expected_fp_gdb}, got {fp_gdb}"
    print("PASS 17F: get_filepath resolves authentic GDB kit path on disk correctly:", fp_gdb)

    # 17G: Missing dynamic kit fallback in ML serves authentic GDB kit instead of CPK defaults
    M.debug_set_deal("fly_emirates", 101, 2027, 60000000, 1, 0) # Opt-in Arsenal
    # Active dynamic kit for Arsenal is NOT in active/, so it falls back to authentic GDB
    key_arsenal_missing_dyn = M.make_key(ml_ctx, "u0101p1.ftex")
    assert key_arsenal_missing_dyn == expected_gdb_key, f"Expected authentic GDB fallback when dynamic kit missing, got {key_arsenal_missing_dyn}"
    print("PASS 17G: Missing dynamic kit gracefully falls back to authentic GDB kit:", key_arsenal_missing_dyn)

    shutil.rmtree(tmp, ignore_errors=True)
    print("ALL MASTER LEAGUE-ONLY SCOPE TESTS PASSED!")

if __name__ == '__main__':
    test_master_league_only_scope()
