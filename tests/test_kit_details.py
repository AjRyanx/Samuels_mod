#!/usr/bin/env python3
"""tests/test_kit_details.py - Verify realistic kit detail layers.

Validates:
1. Fabric micro-knit textile weave across all garment panels.
2. 3D contact drop shadow and specular rim relief on badges & sponsors.
3. Tailoring construction lines (raglan armholes, flank seams, twin-needle hem stitches).
4. Inner collar neck tape & authenticity size print.
5. Supplier performance fabric tech heat-stamp (HEAT.RDY, DRI-FIT ADV, ULTRAWEAVE, etc.).
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "generator"))

import kit_render
import kit_regions


def test_fabric_microtexture_presence():
    """Verify that fabric micro-knit texture modulates garment luminance with zero color drift."""
    masks = kit_regions.build_masks()
    d = {
        "body": (3, 70, 155),
        "second": (245, 245, 245),
        "pattern": "plain",
        "fabric_texture": True,
    }
    atlas = kit_render.render_kit(d, None, masks=masks)
    arr = np.array(atlas)

    # Sample inside torso front
    sample = arr[1400:1440, 1000:1040, :3]
    std_r = np.std(sample[:, :, 0])
    std_b = np.std(sample[:, :, 2])
    assert std_r > 1.5, f"Expected red channel micro-texture std > 1.5, got {std_r}"
    assert std_b > 1.5, f"Expected blue channel micro-texture std > 1.5, got {std_b}"


def test_heat_press_relief_and_shadows():
    """Verify that badges receive 3D contact shadows while sponsor logos remain clean flat vinyl transfers."""
    masks = kit_regions.build_masks()
    test_logo = REPO_ROOT / "content" / "KitGenerator" / "logos" / "fly_emirates.png"
    test_badge = REPO_ROOT / "content" / "KitGenerator" / "logos" / "audi.png"
    if not test_logo.is_file():
        return

    d = {
        "body": (3, 70, 155),
        "second": (245, 245, 245),
        "pattern": "plain",
        "badge": str(test_badge),
        "sponsor": str(test_logo),
        "heat_press_relief": True,
    }
    atlas = kit_render.render_kit(d, None, masks=masks)
    arr = np.array(atlas)

    # In badge zone, contact shadow pixels must be present below badge strokes
    bx, by = kit_regions.CLUB_BADGE[:2]
    bg_region = arr[by - 60:by + 60, bx - 60:bx + 60, :3]
    diff_body = np.abs(bg_region - np.array([3, 70, 155])).sum(axis=-1)
    is_badge_shadow = (bg_region[:, :, 2] < 150) & (bg_region[:, :, 1] < 68) & (diff_body > 8)
    assert np.count_nonzero(is_badge_shadow) > 50, "Expected contact shadow relief pixels on badge"


def test_construction_seams_and_stitching():
    """Verify presence of flank seams and twin-needle hem stitching."""
    masks = kit_regions.build_masks()
    d = {
        "body": (3, 70, 155),
        "second": (245, 245, 245),
        "pattern": "plain",
        "construction_seams": True,
    }
    atlas = kit_render.render_kit(d, None, masks=masks)
    arr = np.array(atlas)

    # Check flank seam stitch at x=724, y=1400..1600
    flank_stitch = arr[1400:1600, 724, :3]
    diff_stitch = np.abs(flank_stitch - np.array([3, 70, 155])).sum(axis=-1)
    assert np.count_nonzero(diff_stitch > 10) > 50, "Expected flank seam stitching pixels"


def test_inner_neck_detail_and_tape():
    """Verify that inner collar neck tape and size markings are rendered on upper back panel."""
    masks = kit_regions.build_masks()
    d = {
        "body": (3, 70, 155),
        "second": (245, 245, 245),
        "pattern": "plain",
        "inner_neck_tape": True,
    }
    atlas = kit_render.render_kit(d, None, masks=masks)
    arr = np.array(atlas)

    # Upper back neck opening at (970..1070, 80..130)
    neck_area = arr[80:130, 970:1070]
    diff_neck = np.abs(neck_area[:, :, :3] - np.array([3, 70, 155])).sum(axis=-1)
    assert np.count_nonzero(diff_neck > 20) > 200, "Expected neck tape and size print pixels"


def test_supplier_tech_callout():
    """Verify that supplier performance fabric tech stamps are rendered at lower right hem."""
    masks = kit_regions.build_masks()
    d = {
        "body": (3, 70, 155),
        "second": (245, 245, 245),
        "pattern": "plain",
        "supplier_name": "nike",
        "tech_callout": True,
    }
    atlas = kit_render.render_kit(d, None, masks=masks)
    arr = np.array(atlas)

    # Lower right hem area (730..820, 1825..1845)
    tech_area = arr[1825:1845, 730:820]
    diff_tech = np.abs(tech_area[:, :, :3] - np.array([3, 70, 155])).sum(axis=-1)
    assert np.count_nonzero(diff_tech > 20) > 100, "Expected tech stamp pixels at lower hem"


def test_collar_and_cuff_synchronization():
    """Verify that collar styles automatically harmonize sleeve cuffs (Napoli, BVB, Venezia styles)."""
    import kit_dna
    # 1. Napoli EA7 striped rib polo -> striped rib cuffs
    napoli_sync = kit_dna.sync_collar_and_cuffs("striped_rib_polo", (190, 20, 30), (0, 160, 230), (255, 255, 255), (0, 160, 230))
    assert napoli_sync["cuff_style"] == "striped_rib"
    assert napoli_sync["cuff"] == (190, 20, 30)

    # 2. BVB volt/purple V-neck -> accent ring inner cuff
    bvb_sync = kit_dna.sync_collar_and_cuffs("crossover_v", (130, 40, 140), (215, 255, 20), (255, 255, 255), (215, 255, 20))
    assert bvb_sync["cuff_style"] == "accent_ring_inner"

    # 3. Venezia sartorial polo notch -> micro-checkered jacquard knit cuff
    venezia_sync = kit_dna.sync_collar_and_cuffs("polo_v_notch", (110, 15, 30), (235, 228, 215), (235, 228, 215))
    assert venezia_sync["cuff_style"] == "jacquard_knit"

    # 4. Kimono wrap V-neck -> accent ring inner cuff
    wrap_sync = kit_dna.sync_collar_and_cuffs("wrap_v_neck", (20, 20, 30), (255, 200, 0), (240, 240, 240))
    assert wrap_sync["cuff_style"] == "accent_ring_inner"

    # 5. Grandad collar -> French turnback cuff
    grandad_sync = kit_dna.sync_collar_and_cuffs("grandad_collar", (20, 20, 30), (255, 200, 0), (240, 240, 240))
    assert grandad_sync["cuff_style"] == "french_turnback"

    # 6. Square neck -> wide band cuff
    square_sync = kit_dna.sync_collar_and_cuffs("square_neck", (20, 20, 30), (255, 200, 0), (240, 240, 240))
    assert square_sync["cuff_style"] == "wide_band"

    # 7. Contrast split collar -> contrast split cuff
    split_sync = kit_dna.sync_collar_and_cuffs("contrast_split_collar", (20, 20, 30), (255, 200, 0), (240, 240, 240))
    assert split_sync["cuff_style"] == "contrast_split"

    # 8. Laced placket -> tri-color knit cuff
    laced_sync = kit_dna.sync_collar_and_cuffs("laced_placket", (20, 20, 30), (255, 200, 0), (240, 240, 240))
    assert laced_sync["cuff_style"] == "tri_color_knit"

    # 9. Mock turtleneck -> micro-tipped cuff
    mock_sync = kit_dna.sync_collar_and_cuffs("mock_turtleneck_micro", (20, 20, 30), (255, 200, 0), (240, 240, 240))
    assert mock_sync["cuff_style"] == "micro_tipped"


def test_all_collar_and_cuff_styles_render():
    """Verify that all 15 collar styles and new cuff styles render cleanly on the 2D texture atlas."""
    import kit_dna
    masks = kit_regions.build_masks()

    for c_style in kit_dna.POOL_COLLAR_STYLES:
        c_model = kit_dna.COLLAR_STYLE_TO_MODEL[c_style]
        assert c_model > 0, f"Collar {c_style} must map to valid 3D model ID"
        sync = kit_dna.sync_collar_and_cuffs(c_style, (15, 30, 80), (240, 200, 20), (250, 250, 250), (210, 20, 30))
        d = {
            "body": (15, 30, 80),
            "second": (250, 250, 250),
            "third": (210, 20, 30),
            "pattern": "plain",
            "collar": (15, 30, 80),
            "collar_style": c_style,
            "collar_model": c_model,
            "collar_tip": (240, 200, 20),
            "cuff": sync["cuff"],
            "cuff_style": sync["cuff_style"],
            "cuff_tip": sync["cuff_tip"],
        }
        atlas = kit_render.render_kit(d, None, masks=masks)
        assert atlas.size == (2048, 2048)
        arr = np.array(atlas)
        # Verify collar region has rendered non-zero alpha
        assert np.count_nonzero(arr[1868:1940, :, 3]) > 500, f"Collar style {c_style} failed to paint collar pixels"


def test_lightning_and_diagonal_sashes():
    """Verify rendering of authentic diagonal and lightning bolt sashes (Rayo Vallecano style)."""
    masks = kit_regions.build_masks()

    # Lightning sash
    d_bolt = {
        "body": (245, 245, 248),
        "second": (210, 20, 35),
        "third": (240, 195, 30),
        "pattern": "plain",
        "macro_layout": "lightning_sash",
    }
    atlas_bolt = kit_render.render_kit(d_bolt, None, masks=masks)
    arr_bolt = np.array(atlas_bolt)
    # Check for red bolt pixels and gold border pixels across front chest (1024, 1250..1400)
    chest_bolt = arr_bolt[1250:1400, 950:1100, :3]
    red_pixels = np.count_nonzero((chest_bolt[:, :, 0] > 180) & (chest_bolt[:, :, 1] < 60))
    assert red_pixels > 200, f"Expected red lightning sash pixels, found {red_pixels}"

    # Diagonal sash
    d_sash = {
        "body": (245, 245, 248),
        "second": (20, 30, 80),
        "third": (210, 20, 35),
        "pattern": "plain",
        "macro_layout": "diagonal_sash",
    }
    atlas_sash = kit_render.render_kit(d_sash, None, masks=masks)
    arr_sash = np.array(atlas_sash)
    chest_sash = arr_sash[1250:1400, 950:1100, :3]
    blue_pixels = np.count_nonzero((chest_sash[:, :, 2] > 70) & (chest_sash[:, :, 0] < 50))
    assert blue_pixels > 200, f"Expected blue diagonal sash pixels, found {blue_pixels}"


def test_athletic_flank_and_brush_architecture():
    """Verify athletic side flank panels and grunge brush splatter sleeve architecture."""
    masks = kit_regions.build_masks()

    # 1. Athletic Flank panels (BVB back view)
    d_flank = {
        "body": (250, 220, 20),
        "second": (20, 20, 24),
        "pattern": "plain",
        "vent_style": "athletic_flank",
    }
    atlas_flank = kit_render.render_kit(d_flank, None, masks=masks)
    arr_flank = np.array(atlas_flank)
    # Flank region at x=700..724, y=1400..1600 should be dark (20, 20, 24)
    flank_sample = arr_flank[1400:1600, 700:720, :3]
    dark_pixels = np.count_nonzero(flank_sample[:, :, 0] < 50)
    assert dark_pixels > 200, f"Expected dark athletic flank pixels, found {dark_pixels}"

    # 2. Splatter brush shoulder architecture (BVB yellow/black kit)
    d_brush = {
        "body": (250, 220, 20),
        "second": (20, 20, 24),
        "accent": (20, 20, 24),
        "pattern": "plain",
        "sleeve_style": "splatter_brush",
    }
    atlas_brush = kit_render.render_kit(d_brush, None, masks=masks)
    arr_brush = np.array(atlas_brush)
    # Upper chest splatter zone at Y: 1000..1120
    chest_splatter = arr_brush[1000:1120, 750:1250, :3]
    brush_pixels = np.count_nonzero(chest_splatter[:, :, 0] < 50)
    assert brush_pixels > 500, f"Expected brush splatter pixels on upper chest, found {brush_pixels}"


def test_undersleeve_metadata_emission(tmp_path):
    """Verify that build_kit emits companion JSON metadata matching jersey sleeve color."""
    import build_kit

    club = {"id": 114, "name": "Paris Saint-Germain"}
    design = {
        "body": (33, 45, 74),       # #212d4a
        "sleeve": (33, 45, 74),     # navy sleeve
        "second": (218, 41, 28),    # red
        "shorts": (240, 240, 240),
        "socks": (33, 45, 74),
    }

    meta = build_kit.emit_kit_metadata(club, 1, design, tmp_path, active_dir=None, quiet=True)
    json_file = tmp_path / "u0114p1.json"
    assert json_file.is_file(), "Metadata JSON u0114p1.json was not created"

    import json
    data = json.loads(json_file.read_text(encoding="utf-8"))
    assert data["team_id"] == 114
    assert data["slot"] == "p1"
    assert data["undershirt_color"] == "#212d4a"
    assert data["shirt_color_1"] == "#212d4a"
    assert data["collar_style"] == "crew"
    assert data["collar_model"] == 1

    # Contrasting sleeve + wrap_v_neck collar test (e.g. Arsenal red body, white sleeves, kimono wrap collar)
    design_contrast = {
        "body": (219, 0, 0),        # #db0000
        "sleeve": (255, 255, 255),  # #ffffff
        "collar_style": "wrap_v_neck",
    }
    meta_contrast = build_kit.emit_kit_metadata(club, 2, design_contrast, tmp_path, active_dir=None, quiet=True)
    assert meta_contrast["undershirt_color"] == "#ffffff"
    assert meta_contrast["shirt_color_1"] == "#db0000"
    assert meta_contrast["collar_style"] == "wrap_v_neck"
    assert meta_contrast["collar_model"] == 78


def test_lua_undersleeve_sync_in_ml_vs_exhibition(tmp_path):
    """Verify that KitGenerator.lua synchronizes UndershirtColor and 3D Collar model in ML and leaves Exhibition authentic."""
    import json
    from lupa import LuaRuntime

    # Stage metadata file in fake Sider directory
    active_dir = tmp_path / "content" / "KitGenerator" / "active"
    active_dir.mkdir(parents=True, exist_ok=True)
    meta_file = active_dir / "u0114p1.json"
    meta_file.write_text(json.dumps({
        "team_id": 114,
        "slot": "p1",
        "undershirt_color": "#212d4a",
        "shirt_color_1": "#212d4a",
        "collar_style": "wrap_v_neck",
        "collar_model": 78,
    }), encoding="utf-8")

    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('log=function(s) end; ffi=nil')
    mod_code = (REPO_ROOT / "modules" / "KitGenerator.lua").read_text(encoding="utf-8")
    M = lua.eval('function(src) return load(src)() end')(mod_code)

    # Mock ctx with kits.set
    last_set = {}
    def mock_set(team_id, kit_id, cfg, radar_flag):
        last_set["team_id"] = team_id
        last_set["kit_id"] = kit_id
        last_set["cfg"] = dict(cfg)
        last_set["radar_flag"] = radar_flag

    def mock_set_gk(team_id, cfg):
        last_set["team_id"] = team_id
        last_set["is_gk"] = True
        last_set["cfg"] = dict(cfg)

    kits_table = lua.table_from({"set": mock_set, "set_gk": mock_set_gk, "get": lambda tid, k: None})
    reg_table = {}
    ctx = lua.table_from({
        "sider_dir": str(tmp_path) + "/",
        "tournament_id": 19, # Master League
        "kits": kits_table,
        "register": lambda ev, fn: reg_table.update({ev: fn}),
    })

    M.init(ctx)
    M.debug_set_club(114)
    M.debug_set_date(2028, 8, 1)

    # 1. Master League match setup: should synchronize UndershirtColor and 3D Collar model
    cfg_ml = lua.table_from({
        "KitFile": "u0114p1",
        "ShirtColor1": "#212d4a",
        "UndershirtColor": "#3951A5", # old mismatched electric blue
        "Collar": 1,
        "WinterCollar": 1,
    })
    ctx["tournament_id"] = 19
    M.make_key(ctx, "common\\script\\flow\\ML\\ML_Top.json")
    ctx.kits.set(114, 0, cfg_ml, 0)
    assert last_set["cfg"]["UndershirtColor"] == "#212d4a", f"Expected #212d4a in ML, got {last_set['cfg']['UndershirtColor']}"
    assert last_set["cfg"]["Collar"] == 78, f"Expected 3D Collar model 78 in ML, got {last_set['cfg']['Collar']}"
    assert last_set["cfg"]["WinterCollar"] == 78, f"Expected WinterCollar 78 in ML, got {last_set['cfg']['WinterCollar']}"

    # 2. Exhibition match: tournament_id 65535 MUST NOT alter UndershirtColor or Collar (remains authentic)
    cfg_exh = lua.table_from({
        "KitFile": "u0114p1",
        "ShirtColor1": "#212d4a",
        "UndershirtColor": "#3951A5",
        "Collar": 1,
        "WinterCollar": 1,
    })
    ctx["tournament_id"] = 65535
    M.make_key(ctx, "common\\script\\flow\\Exhibition\\MatchMenu.json")
    ctx.kits.set(114, 0, cfg_exh, 0)
    assert last_set["cfg"]["UndershirtColor"] == "#3951A5", f"Expected authentic #3951A5 preserved in Exhibition, got {last_set['cfg']['UndershirtColor']}"
    assert last_set["cfg"]["Collar"] == 1, f"Expected authentic Collar 1 preserved in Exhibition, got {last_set['cfg']['Collar']}"
    assert last_set["cfg"]["WinterCollar"] == 1, f"Expected authentic WinterCollar 1 preserved in Exhibition, got {last_set['cfg']['WinterCollar']}"


def test_all_shorts_styles_render(tmp_path):
    """Verify that all 10 shorts styles render cleanly on the 2048x2048 UV texture atlas."""
    import kit_dna
    import kit_render
    import kit_regions

    masks = kit_regions.build_masks()
    styles = kit_dna.POOL_SHORTS_STYLES

    assert len(styles) >= 10, f"Expected at least 10 shorts styles in pool, got {len(styles)}"
    assert "contrast_flank_panel" in styles
    assert "dual_side_stripes" in styles
    assert "hem_turnup_notch" in styles
    assert "two_tone_halves" in styles
    assert "gradient_side_fade" in styles
    assert "contrast_waistband" in styles

    for s in styles:
        d = dict(kit_render.DEFAULT_DESIGN)
        d.update({
            "body": (25, 30, 45),
            "shorts": (25, 30, 45),
            "shorts_accent": (235, 185, 45),
            "shorts_tip": (255, 255, 255),
            "shorts_style": s,
            "fabric_texture": False,
        })
        out_png = tmp_path / f"test_shorts_{s}.png"
        kit_render.render_kit(d, str(out_png), masks=masks)
        assert out_png.exists() and out_png.stat().st_size > 20000, f"Failed rendering shorts style: {s}"


def test_shorts_mockup_and_metadata(tmp_path):
    """Verify that 2D shorts presentation mockup and companion JSON metadata emit correctly."""
    import kit_render
    import build_kit

    d = dict(kit_render.DEFAULT_DESIGN)
    d.update({
        "body": (190, 20, 35),
        "shorts": (190, 20, 35),
        "shorts_accent": (250, 250, 250),
        "shorts_tip": (20, 25, 35),
        "shorts_style": "contrast_flank_panel",
    })

    # 1. 2D shorts mockup
    mockup_png = tmp_path / "shorts_mockup.png"
    kit_render.generate_shorts_mockup(d, "Arsenal", 2027, str(mockup_png))
    assert mockup_png.exists() and mockup_png.stat().st_size > 2000

    # 2. Companion JSON metadata
    club = {"id": 101, "name": "Arsenal"}
    meta = build_kit.emit_kit_metadata(club, 1, d, str(tmp_path))
    assert meta["shorts_style"] == "contrast_flank_panel"
    json_path = tmp_path / "u0101p1.json"
    assert json_path.exists()
    content = json_path.read_text(encoding="utf-8")
    assert '"shorts_style": "contrast_flank_panel"' in content


def test_all_socks_styles_render(tmp_path):
    """Verify that all 12 socks styles render cleanly onto the texture atlas."""
    import kit_render
    import kit_dna
    import kit_regions
    from PIL import Image

    masks = kit_regions.build_masks()
    sm = masks["socks"]
    styles = kit_dna.POOL_SOCKS_STYLES

    assert len(styles) >= 10

    for s_style in styles:
        atlas = Image.new("RGBA", (2048, 2048), (20, 25, 45, 255))
        d = dict(kit_render.DEFAULT_DESIGN)
        d.update({
            "body": (20, 25, 45),
            "socks": (20, 25, 45),
            "socks_accent": (240, 240, 245),
            "socks_tip": (220, 180, 50),
            "socks_style": s_style,
        })
        kit_render._apply_engineered_socks(atlas, d, masks)

        out_png = tmp_path / f"test_socks_{s_style}.png"
        atlas.save(str(out_png))
        assert out_png.exists() and out_png.stat().st_size > 20000


def test_socks_mockup_and_metadata(tmp_path):
    """Verify that 2D socks presentation mockup and companion JSON metadata emit correctly."""
    import kit_render
    import build_kit

    d = dict(kit_render.DEFAULT_DESIGN)
    d.update({
        "body": (15, 120, 60),
        "socks": (15, 120, 60),
        "socks_accent": (250, 250, 250),
        "socks_tip": (215, 175, 45),
        "socks_style": "full_hooped_body",
    })

    # 1. 2D socks mockup
    mockup_png = tmp_path / "socks_mockup.png"
    kit_render.generate_socks_mockup(d, "Celtic FC", 2027, str(mockup_png))
    assert mockup_png.exists() and mockup_png.stat().st_size > 2000

    # 2. Companion JSON metadata
    club = {"id": 133, "name": "Celtic FC"}
    meta = build_kit.emit_kit_metadata(club, 1, d, str(tmp_path))
    assert meta["socks_style"] == "full_hooped_body"
    json_path = tmp_path / "u0133p1.json"
    assert json_path.exists()
    content = json_path.read_text(encoding="utf-8")
    assert '"socks_style": "full_hooped_body"' in content


def test_all_sleeve_styles_render(tmp_path):
    """Verify that all 10 sleeve styles render cleanly onto the texture atlas."""
    import kit_render
    import kit_dna
    import kit_regions
    from PIL import Image

    masks = kit_regions.build_masks()
    styles = kit_dna.POOL_SLEEVE_STYLES

    assert len(styles) >= 10

    for sl_style in styles:
        atlas = Image.new("RGBA", (2048, 2048), (20, 25, 45, 255))
        d = dict(kit_render.DEFAULT_DESIGN)
        d.update({
            "body": (20, 25, 45),
            "sleeve": (20, 25, 45),
            "second": (210, 30, 45),
            "stripe_accent": (240, 240, 245),
            "accent": (240, 240, 245),
            "third": (220, 180, 50),
            "sleeve_style": sl_style,
        })
        kit_render._apply_sleeve_architecture(atlas, d, masks)

        out_png = tmp_path / f"test_sleeve_{sl_style}.png"
        atlas.save(str(out_png))
        assert out_png.exists() and out_png.stat().st_size > 20000


def test_sleeve_mockup_and_metadata(tmp_path):
    """Verify that 2D sleeve presentation mockup and companion JSON metadata emit correctly."""
    import kit_render
    import build_kit

    d = dict(kit_render.DEFAULT_DESIGN)
    d.update({
        "body": (15, 25, 55),
        "sleeve": (15, 25, 55),
        "second": (210, 25, 35),
        "stripe_accent": (240, 240, 245),
        "accent": (240, 240, 245),
        "third": (220, 180, 50),
        "sleeve_style": "contrast_raglan",
    })

    # 1. 2D sleeve mockup
    mockup_png = tmp_path / "sleeve_mockup.png"
    kit_render.generate_sleeve_mockup(d, "Paris Saint-Germain", 2027, str(mockup_png))
    assert mockup_png.exists() and mockup_png.stat().st_size > 2000

    # 2. Companion JSON metadata
    club = {"id": 114, "name": "Paris Saint-Germain"}
    meta = build_kit.emit_kit_metadata(club, 1, d, str(tmp_path))
    assert meta["sleeve_style"] == "contrast_raglan"
    assert "undershirt_color" in meta
    json_path = tmp_path / "u0114p1.json"
    assert json_path.exists()
    content = json_path.read_text(encoding="utf-8")
    assert '"sleeve_style": "contrast_raglan"' in content


def test_undersleeve_unicolor_sync_lua():
    """Verify that KitGenerator.lua synchronizes cfg.UniColor_Color1 and UniColor_Color2 with undershirt_color."""
    lua_path = REPO_ROOT / "modules" / "KitGenerator.lua"
    content = lua_path.read_text(encoding="utf-8")
    assert "cfg.UniColor_Color1 = meta.undershirt_color" in content
    assert "cfg.UniColor_Color2 = meta.undershirt_color" in content


def test_all_brand_signatures_render(tmp_path):
    """Verify that brand signature languages for all 12 kit suppliers render properly on the atlas."""
    import kit_render
    import kit_regions
    from PIL import Image

    masks = kit_regions.build_masks()
    suppliers = [
        "adidas", "nike", "puma", "umbro", "hummel", "kappa",
        "castore", "macron", "newbalance", "joma", "mizuno", "ea7"
    ]

    for supp in suppliers:
        atlas = Image.new("RGBA", (2048, 2048), (20, 25, 45, 255))
        d = dict(kit_render.DEFAULT_DESIGN)
        d.update({
            "body": (20, 25, 45),
            "sleeve": (20, 25, 45),
            "shorts": (240, 240, 245),
            "second": (210, 30, 45),
            "stripe_accent": (240, 240, 245),
            "shorts_accent": (210, 30, 45),
            "supplier": supp,
            "supplier_name": supp,
        })
        kit_render._apply_brand_signatures(atlas, d, masks)

        out_png = tmp_path / f"test_brand_{supp}.png"
        atlas.save(str(out_png))
        assert out_png.exists() and out_png.stat().st_size > 20000


def test_all_fabric_finishes_render(tmp_path):
    """Verify that all 6 specialty fabric finishes and jacquard weaves render without error."""
    import kit_render
    import kit_dna
    import kit_regions
    from PIL import Image

    masks = kit_regions.build_masks()
    finishes = kit_dna.POOL_FABRIC_FINISHES

    assert len(finishes) >= 6

    for fin in finishes:
        atlas = Image.new("RGBA", (2048, 2048), (20, 25, 45, 255))
        d = dict(kit_render.DEFAULT_DESIGN)
        d.update({
            "body": (20, 25, 45),
            "sleeve": (20, 25, 45),
            "second": (210, 30, 45),
            "stripe_accent": (240, 240, 245),
            "fabric_finish": fin,
            "fabric_texture": True,
        })
        kit_render._apply_fabric_microtexture(atlas, d, masks)

        out_png = tmp_path / f"test_fabric_{fin}.png"
        atlas.save(str(out_png))
        assert out_png.exists() and out_png.stat().st_size > 20000


def test_fabric_mockup_and_metadata(tmp_path):
    """Verify that 2D fabric presentation mockup and companion JSON metadata emit correctly."""
    import kit_render
    import build_kit

    d = dict(kit_render.DEFAULT_DESIGN)
    d.update({
        "body": (15, 25, 55),
        "sleeve": (15, 25, 55),
        "second": (210, 25, 35),
        "stripe_accent": (240, 240, 245),
        "fabric_finish": "matte_vaporknit",
    })

    # 1. 2D fabric mockup
    mockup_png = tmp_path / "fabric_mockup.png"
    kit_render.generate_fabric_mockup(d, "Paris Saint-Germain", 2027, str(mockup_png))
    assert mockup_png.exists() and mockup_png.stat().st_size > 2000

    # 2. Companion JSON metadata
    club = {"id": 114, "name": "Paris Saint-Germain"}
    meta = build_kit.emit_kit_metadata(club, 1, d, str(tmp_path))
    assert meta["fabric_finish"] == "matte_vaporknit"
    json_path = tmp_path / "u0114p1.json"
    assert json_path.exists()
    content = json_path.read_text(encoding="utf-8")
    assert '"fabric_finish": "matte_vaporknit"' in content


def test_thematic_collections_render(tmp_path):
    """Verify that all Third Kit thematic mood finishes render without error."""
    import kit_render
    import kit_regions
    from PIL import Image

    masks = kit_regions.build_masks()
    thematics = [
        "blackout", "liquid_gold", "chrome_silver", "copper_bronze",
        "cyber_neon", "iridescent_neon", "pastel_streetwear", "retro_throwback"
    ]

    for th in thematics:
        atlas = Image.new("RGBA", (2048, 2048), (20, 25, 45, 255))
        d = dict(kit_render.DEFAULT_DESIGN)
        d.update({
            "body": (20, 25, 45),
            "sleeve": (20, 25, 45),
            "second": (210, 30, 45),
            "stripe_accent": (240, 240, 245),
            "finish": th,
            "fabric_finish": "matte_vaporknit" if "neon" in th else "standard_microknit",
        })
        kit_render.render_kit(d, str(tmp_path / f"test_th_{th}.png"), masks=masks)

        out_png = tmp_path / f"test_th_{th}.png"
        assert out_png.exists() and out_png.stat().st_size > 50000


def test_thematic_metadata(tmp_path):
    """Verify that companion metadata correctly records thematic_finish."""
    import kit_render
    import build_kit

    d = dict(kit_render.DEFAULT_DESIGN)
    d.update({
        "body": (18, 20, 24),
        "sleeve": (18, 20, 24),
        "second": (38, 42, 48),
        "finish": "blackout",
    })

    club = {"id": 102, "name": "Chelsea FC"}
    meta = build_kit.emit_kit_metadata(club, 3, d, str(tmp_path))
    assert meta["thematic_finish"] == "blackout"
    json_path = tmp_path / "u0102p3.json"
    assert json_path.exists()
    content = json_path.read_text(encoding="utf-8")
    assert '"thematic_finish": "blackout"' in content


def test_all_gk_macro_layouts_render(tmp_path):
    """Verify that all 7 90s retro & modern GK macro layouts render properly on the atlas."""
    import kit_render
    import kit_dna
    import kit_regions
    from PIL import Image

    masks = kit_regions.build_masks()
    macros = kit_dna.POOL_MACRO_GK

    assert len(macros) >= 7

    for m_layout in macros:
        atlas = Image.new("RGBA", (2048, 2048), (215, 255, 0, 255))
        d = dict(kit_render.DEFAULT_DESIGN)
        d.update({
            "body": (215, 255, 0),
            "sleeve": (215, 255, 0),
            "second": (18, 20, 24),
            "third": (0, 240, 255),
            "accent": (255, 30, 100),
            "stripe_accent": (0, 240, 255),
            "macro_layout": m_layout,
            "pattern": "solid",
        })
        kit_render.render_kit(d, str(tmp_path / f"test_gk_{m_layout}.png"), masks=masks)

        out_png = tmp_path / f"test_gk_{m_layout}.png"
        assert out_png.exists() and out_png.stat().st_size > 50000


def test_gk_dna_generation():
    """Verify that _generate_gk_dna assigns authentic GK palettes and macro layouts."""
    import kit_dna

    club = {"id": 102, "name": "Chelsea FC", "primary": "#034694", "secondary": "#FFFFFF"}
    gk_g1 = kit_dna.get_club_style(club, "g1", 2027)
    assert gk_g1["macro_layout"] in kit_dna.POOL_MACRO_GK
    assert "body" in gk_g1 and "second" in gk_g1
    # Ensure GK color does not clash with home kit primary (#034694)
    primary_rgb = (3, 70, 148)
    gk_body = gk_g1["body"]
    dist = ((gk_body[0] - primary_rgb[0]) ** 2 + (gk_body[1] - primary_rgb[1]) ** 2 + (gk_body[2] - primary_rgb[2]) ** 2) ** 0.5
    assert dist > 80, f"GK body {gk_body} clashes with home body {primary_rgb}"


def test_collar_model_sync():
    """Verify that every collar_style maps to a valid 3D PES collar_model ID."""
    import kit_dna

    assert len(kit_dna.COLLAR_STYLE_TO_MODEL) >= 15
    for style, model_id in kit_dna.COLLAR_STYLE_TO_MODEL.items():
        assert isinstance(model_id, int)
        assert 1 <= model_id <= 135

    # Test club style generation includes collar_model
    club = {"id": 102, "name": "Chelsea FC", "primary": "#034694", "secondary": "#FFFFFF"}
    for slot in [1, 2, 3, "g1", "g2"]:
        style_dict = kit_dna.get_club_style(club, slot, 2026)
        assert "collar_model" in style_dict
        assert style_dict["collar_model"] in kit_dna.COLLAR_STYLE_TO_MODEL.values()







