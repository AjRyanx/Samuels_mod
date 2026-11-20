#!/usr/bin/env python3
"""generate_user_showcase.py - Generate the 5 requested authentic styles side-by-side with user references."""
import base64
from io import BytesIO
from pathlib import Path
from PIL import Image
import numpy as np

import kit_render
import kit_regions

ROOT = Path(__file__).resolve().parent.parent
UPLOADED = Path("/Users/mac/.gemini/antigravity/brain/6467c797-2ab2-4191-abb5-8bdfc2ba4135/.user_uploaded")
OUT_DIR = ROOT / "content" / "KitGenerator" / "showcase_renders"
OUT_DIR.mkdir(parents=True, exist_ok=True)

masks = kit_regions.build_masks()

SHOWCASE_CONFIGS = [
    {
        "id": "arsenal_2425",
        "title": "Arsenal 2024/25 Home (Raglan & Ergonomic Flank Swoop)",
        "ref_image": UPLOADED / "media_1795178351338_02a34492.jpg",
        "description": "Scarlet red body, white raglan sleeves, deep navy curved flank panels, Adidas 3-stripes, white Emirates sponsor, Visit Rwanda sleeve logo, dual-tipped collar.",
        "design": {
            "body": (218, 2, 29),
            "second": (255, 255, 255),
            "accent": (15, 25, 60),
            "sleeve": (255, 255, 255),
            "pattern": "plain",
            "supplier_name": "adidas",
            "supplier": str(ROOT / "content" / "KitGenerator" / "suppliers" / "adidas_white.png"),
            "badge": str(ROOT / "content" / "KitGenerator" / "badges" / "101.png"),
            "sponsor": str(ROOT / "content" / "KitGenerator" / "logos" / "fly_emirates_white.png"),
            "sleeve_sponsor": str(ROOT / "generator" / "sleeve_logos" / "visit_rwanda_white.png"),
            "vent_style": "contrast_panel",
            "vent_color": (15, 25, 60),
            "collar_style": "crew",
            "collar_tip": (15, 25, 60),
            "cuff": (255, 255, 255),
            "cuff_tip": (15, 25, 60),
            "shorts": (255, 255, 255),
            "shorts_style": "side_stripe",
            "shorts_accent": (218, 2, 29),
            "socks": (218, 2, 29),
            "socks_style": "turnover_hoop",
            "socks_accent": (255, 255, 255),
        }
    },
    {
        "id": "bayern_oktoberfest",
        "title": "Bayern Munich Festival / Streetwear (All-Over Floral Camo)",
        "ref_image": UPLOADED / "media_1795178362545_b8cde36e.png",
        "description": "Rich dark kaleidoscopic botanical camo graphic across torso and sleeves, ecru/off-white T-Mobile sponsor, silver crest, dark ribbed collar & cuffs.",
        "design": {
            "body": (22, 26, 30),
            "second": (210, 110, 50),
            "third": (55, 135, 115),
            "pattern": "172",
            "var": 1,
            "pattern_mask": "full",
            "supplier_name": "adidas",
            "supplier": str(ROOT / "content" / "KitGenerator" / "suppliers" / "adidas_white.png"),
            "badge": str(ROOT / "content" / "KitGenerator" / "badges" / "127.png"),
            "sponsor": str(ROOT / "content" / "KitGenerator" / "logos" / "telekom_white.png"),
            "sleeve_sponsor": str(ROOT / "generator" / "sleeve_logos" / "okx_white.png"),
            "collar_style": "crew",
            "collar": (20, 22, 26),
            "cuff": (20, 22, 26),
            "cuff_tip": (230, 225, 210),
            "shorts": (22, 26, 30),
            "shorts_style": "side_stripe",
            "shorts_accent": (230, 225, 210),
            "socks": (22, 26, 30),
        }
    },
    {
        "id": "mancity_lightning",
        "title": "Manchester City 2023/24 Third (Electric Cyan Lightning on Obsidian)",
        "ref_image": UPLOADED / "media_1795178379083_081301cb.jpg",
        "description": "Obsidian dark navy shell with kinetic cyan fracture lightning streaks, neon coral Puma Cat and Etihad sponsor, Puma ULTRAWEAVE callout and jocktag.",
        "design": {
            "body": (16, 22, 34),
            "second": (0, 210, 255),
            "accent": (255, 55, 95),
            "pattern": "165",
            "var": 0,
            "finish": "cyber_neon",
            "supplier_name": "puma",
            "supplier": str(ROOT / "content" / "KitGenerator" / "suppliers" / "puma_white.png"),
            "badge": str(ROOT / "content" / "KitGenerator" / "badges" / "173.png"),
            "sponsor": str(ROOT / "content" / "KitGenerator" / "logos" / "etihad_white.png"),
            "sleeve_sponsor": str(ROOT / "generator" / "sleeve_logos" / "okx.png"),
            "collar_style": "crew",
            "collar_tip": (0, 210, 255),
            "cuff": (16, 22, 34),
            "cuff_tip": (0, 210, 255),
            "shorts": (16, 22, 34),
            "shorts_style": "side_stripe",
            "shorts_accent": (0, 210, 255),
            "socks": (16, 22, 34),
            "socks_style": "calf_band",
            "socks_accent": (0, 210, 255),
        }
    },
    {
        "id": "luxury_streetwear",
        "title": "Minimalist Luxury Streetwear (Y-3 / Ushuaïa Clean Architecture)",
        "ref_image": UPLOADED / "media_1795178406464_26758f88.jpg",
        "description": "Stark architectural white base, deep V-neck, black shoulder racing stripes, monochromatic silicone badges, heavy luxury piqué micro-weave.",
        "design": {
            "body": (248, 248, 250),
            "second": (18, 20, 24),
            "accent": (18, 20, 24),
            "pattern": "plain",
            "finish": "blackout",
            "sleeve_style": "shoulder_stripe",
            "stripe_accent": (18, 20, 24),
            "supplier_name": "adidas",
            "supplier": str(ROOT / "content" / "KitGenerator" / "suppliers" / "adidas.png"),
            "badge": str(ROOT / "content" / "KitGenerator" / "badges" / "1.png"),
            "sponsor": str(ROOT / "content" / "KitGenerator" / "logos" / "revolut.png"),
            "collar_style": "v_neck",
            "collar_tip": (18, 20, 24),
            "cuff": (248, 248, 250),
            "cuff_tip": (18, 20, 24),
            "shorts": (18, 20, 24),
            "shorts_style": "solid",
            "socks": (248, 248, 250),
            "socks_style": "turnover_hoop",
            "socks_accent": (18, 20, 24),
        }
    },
    {
        "id": "barcelona_gold",
        "title": "Barcelona Special Edition (Tonal Jacquard & Liquid Gold)",
        "ref_image": UPLOADED / "media_1795178420916_83435529.jpg",
        "description": "Blaugrana vertical stripes with tonal wave micro-jacquard overlay, champagne liquid gold Nike swoosh, Spotify circular medallion, and golden Ambilight logo.",
        "design": {
            "body": (160, 11, 66),
            "second": (0, 77, 152),
            "accent": (220, 185, 80),
            "pattern": "031",
            "micro_jacquard": "041-E",
            "finish": "liquid_gold",
            "supplier_name": "nike",
            "supplier": str(ROOT / "content" / "KitGenerator" / "suppliers" / "nike_white.png"),
            "badge": str(ROOT / "content" / "KitGenerator" / "badges" / "108.png"),
            "sponsor": str(ROOT / "content" / "KitGenerator" / "logos" / "spotify_white.png"),
            "sleeve_sponsor": str(ROOT / "generator" / "sleeve_logos" / "ambilight_white.png"),
            "collar_style": "crew",
            "collar_tip": (0, 77, 152),
            "cuff": (0, 77, 152),
            "cuff_tip": (220, 185, 80),
            "shorts": (0, 77, 152),
            "shorts_style": "side_stripe",
            "shorts_accent": (160, 11, 66),
            "socks": (0, 77, 152),
        }
    }
]

def to_b64(im):
    buf = BytesIO()
    im.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

def to_b64_file(path):
    if not path or not Path(path).is_file():
        return ""
    with open(path, "rb") as f:
        data = f.read()
    fmt = "jpeg" if str(path).lower().endswith((".jpg", ".jpeg")) else "png"
    return f"data:image/{fmt};base64," + base64.b64encode(data).decode("ascii")

html_sections = []

for cfg in SHOWCASE_CONFIGS:
    print(f"Rendering: {cfg['title']}...")
    d = cfg["design"]
    png_out = OUT_DIR / f"{cfg['id']}_atlas.png"
    atlas = kit_render.render_kit(d, None, masks=masks)
    atlas.save(png_out)

    # High-res Detail Crops:
    crop_chest = atlas.crop((750, 1080, 1300, 1420))
    crop_flank = atlas.crop((680, 1150, 820, 1600))
    crop_neck = atlas.crop((940, 70, 1100, 160))
    crop_tech = atlas.crop((720, 1805, 840, 1865)).resize((360, 180), Image.NEAREST)
    crop_sleeve = atlas.crop((1650, 320, 1850, 480))
    crop_jock = atlas.crop((1230, 1805, 1315, 1865)).resize((340, 240), Image.NEAREST)
    crop_weave = atlas.crop((960, 1460, 1080, 1580)).resize((360, 360), Image.NEAREST)

    ref_b64_src = to_b64_file(cfg["ref_image"])
    full_atlas_b64 = to_b64(atlas.resize((600, 600), Image.LANCZOS))
    chest_b64 = to_b64(crop_chest)
    flank_b64 = to_b64(crop_flank)
    neck_b64 = to_b64(crop_neck)
    tech_b64 = to_b64(crop_tech)
    sleeve_b64 = to_b64(crop_sleeve)
    jock_b64 = to_b64(crop_jock)
    weave_b64 = to_b64(crop_weave)

    html_sections.append(f"""
    <div class="comparison-card">
        <div class="card-header">
            <h2>{cfg['title']}</h2>
            <p class="desc">{cfg['description']}</p>
        </div>
        <div class="side-by-side">
            <div class="ref-col">
                <div class="col-tag">Real-World Photo Reference</div>
                <img src="{ref_b64_src}" class="ref-photo" alt="Photo reference">
            </div>
            <div class="gen-col">
                <div class="col-tag">Our Generated 2048x2048 UV Atlas</div>
                <img src="data:image/png;base64,{full_atlas_b64}" class="atlas-photo" alt="Generated UV Atlas">
            </div>
        </div>
        <div class="crops-header">Zoomed Detail Audits (Physical Texture & Relief)</div>
        <div class="crops-grid">
            <div class="crop-box">
                <span class="crop-label">3D Silicone Crest & Sponsor Relief</span>
                <img src="data:image/png;base64,{chest_b64}">
                <span class="crop-desc">Contact drop shadow + specular edge highlight</span>
            </div>
            <div class="crop-box">
                <span class="crop-label">Tailored Flank Panels & Seams</span>
                <img src="data:image/png;base64,{flank_b64}">
                <span class="crop-desc">Ergonomic underarm insert & dual-tone stitching</span>
            </div>
            <div class="crop-box">
                <span class="crop-label">Collar Inner Neck Tape & Size M</span>
                <img src="data:image/png;base64,{neck_b64}">
                <span class="crop-desc">Ribbon tape + sizing stamp visible in collar opening</span>
            </div>
            <div class="crop-box">
                <span class="crop-label">Sleeve Sponsor & Wrap Angle</span>
                <img src="data:image/png;base64,{sleeve_b64}">
                <span class="crop-desc">Rotated along ergonomic sleeve drape</span>
            </div>
            <div class="crop-box">
                <span class="crop-label">Supplier Tech Stamp</span>
                <img src="data:image/png;base64,{tech_b64}">
                <span class="crop-desc">Authentic lower right hem performance stamp</span>
            </div>
            <div class="crop-box">
                <span class="crop-label">Fabric Micro-Knit Weave (Zoomed)</span>
                <img src="data:image/png;base64,{weave_b64}">
                <span class="crop-desc">Tactile 4x4 athletic piqué matte weave</span>
            </div>
        </div>
    </div>
    """)

html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>PES 2021 / FL27 Dynamic Kits - Real Reference Comparison Showcase</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            background: #090c10;
            color: #e6edf3;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 30px;
        }}
        .header {{
            text-align: center;
            max-width: 900px;
            margin: 0 auto 40px auto;
        }}
        h1 {{
            font-size: 2.4rem;
            margin-bottom: 10px;
            color: #58a6ff;
            letter-spacing: -0.5px;
        }}
        .header p {{
            color: #8b949e;
            font-size: 1.1rem;
            line-height: 1.5;
        }}
        .comparison-card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 14px;
            padding: 28px;
            margin-bottom: 50px;
            box-shadow: 0 12px 32px rgba(0,0,0,0.5);
        }}
        .card-header h2 {{
            margin: 0 0 8px 0;
            color: #f0f6fc;
            font-size: 1.6rem;
        }}
        .desc {{
            color: #8b949e;
            margin: 0 0 24px 0;
            font-size: 0.95rem;
        }}
        .side-by-side {{
            display: flex;
            gap: 24px;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }}
        .ref-col, .gen-col {{
            flex: 1;
            min-width: 320px;
            background: #0d1117;
            border-radius: 10px;
            border: 1px solid #21262d;
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .col-tag {{
            font-size: 0.85rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
            color: #58a6ff;
        }}
        .ref-photo {{
            max-width: 100%;
            max-height: 480px;
            object-fit: contain;
            border-radius: 8px;
            border: 1px solid #30363d;
        }}
        .atlas-photo {{
            width: 100%;
            max-width: 480px;
            border-radius: 8px;
            border: 1px solid #30363d;
            background: #000;
        }}
        .crops-header {{
            font-size: 1.05rem;
            font-weight: 600;
            color: #f0f6fc;
            margin-bottom: 16px;
            border-top: 1px solid #21262d;
            padding-top: 20px;
        }}
        .crops-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
        }}
        .crop-box {{
            background: #0d1117;
            border: 1px solid #21262d;
            border-radius: 8px;
            padding: 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
        }}
        .crop-box img {{
            max-width: 100%;
            border-radius: 6px;
            margin: 10px 0;
            border: 1px solid #30363d;
            background: #05070a;
        }}
        .crop-label {{
            font-size: 0.8rem;
            font-weight: 600;
            color: #79c0ff;
        }}
        .crop-desc {{
            font-size: 0.75rem;
            color: #8b949e;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Dynamic Kits Match Engine: Side-by-Side Showcase</h1>
        <p>Comparing real-world modern, streetwear & special edition kits against our in-engine generated 2048x2048 textures, including 3D silicone heat-press relief, micro-knit fabric weave, ergonomic panels, and authentic manufacturer signatures.</p>
    </div>
    {''.join(html_sections)}
</body>
</html>
"""

showcase_path = ROOT / "user_requested_kits_showcase.html"
showcase_path.write_text(html_doc, encoding="utf-8")
print(f"User showcase generated successfully at: {showcase_path}")
