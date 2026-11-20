#!/usr/bin/env python3
"""generate_archetypes_showcase.py - Generate all 8 Modern Football Kit Archetypes into an interactive showcase."""
import base64
from io import BytesIO
from pathlib import Path
from PIL import Image
import numpy as np

import kit_render
import kit_regions

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "content" / "KitGenerator" / "showcase_renders" / "archetypes"
OUT_DIR.mkdir(parents=True, exist_ok=True)

masks = kit_regions.build_masks()

ARCHETYPES = [
    {
        "id": "arch_1_athletic",
        "num": 1,
        "name": "The Athletic Color-Block",
        "club_name": "Arsenal FC (Home)",
        "subtitle": "Ergonomic Panel Architecture & Modern Raglan Cuts",
        "philosophy": "Emphasizes the athletic human silhouette through high-contrast raglan sleeves, curved underarm flank inserts, and precision dual-tipped collar ribbing. Anchors the club's canonical identity while updating it with modern panel cuts.",
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
        "id": "arch_2_heritage_stripe",
        "num": 2,
        "name": "The Heritage Stripe & Hoop Evolution",
        "club_name": "Inter Milan (Home Nerazzurri)",
        "subtitle": "Sacred Traditional Identity with Micro-Jacquard Weave",
        "philosophy": "Guarantees 100% fidelity to historic stripes/hoops (Inter, Milan, Celtic, Barça, Juve). The modern evolution comes from subtle tonal micro-jacquards embedded at 30% alpha inside the stripes, paired with champagne liquid gold trims.",
        "design": {
            "body": (0, 85, 170),
            "second": (18, 20, 24),
            "accent": (220, 185, 80),
            "pattern": "031",
            "micro_jacquard": "171-E",
            "finish": "liquid_gold",
            "supplier_name": "nike",
            "supplier": str(ROOT / "content" / "KitGenerator" / "suppliers" / "nike_white.png"),
            "badge": str(ROOT / "content" / "KitGenerator" / "badges" / "119.png"),
            "sponsor": str(ROOT / "content" / "KitGenerator" / "logos" / "paramount_white.png"),
            "sleeve_sponsor": str(ROOT / "generator" / "sleeve_logos" / "ebay_white.png"),
            "collar_style": "crew",
            "collar_tip": (0, 85, 170),
            "cuff": (18, 20, 24),
            "cuff_tip": (220, 185, 80),
            "shorts": (18, 20, 24),
            "shorts_style": "side_stripe",
            "shorts_accent": (0, 85, 170),
            "socks": (18, 20, 24),
            "socks_style": "turnover_hoop",
            "socks_accent": (220, 185, 80),
        }
    },
    {
        "id": "arch_3_diagonal_sash",
        "num": 3,
        "name": "The Diagonal Sash & Cross",
        "club_name": "River Plate (Home Canonical Sash)",
        "subtitle": "45° Dynamic Geometry & Calmed Sponsor Integration",
        "philosophy": "Dedicated architecture for sash and cross clubs (River Plate, Rayo Vallecano, Vasco da Gama, Lyon). Renders an authoritative 45° diagonal sash across a pristine clean chassis, with automated contrast calming under the chest sponsor.",
        "design": {
            "body": (252, 252, 255),
            "second": (215, 22, 35),
            "accent": (18, 20, 24),
            "pattern": "sash",
            "supplier_name": "adidas",
            "supplier": str(ROOT / "content" / "KitGenerator" / "suppliers" / "adidas.png"),
            "badge": str(ROOT / "content" / "KitGenerator" / "badges" / "138.png"),
            "sponsor": str(ROOT / "content" / "KitGenerator" / "logos" / "bbva.png"),
            "sleeve_sponsor": str(ROOT / "generator" / "sleeve_logos" / "western_union.png"),
            "collar_style": "crew",
            "collar_tip": (215, 22, 35),
            "cuff": (252, 252, 255),
            "cuff_tip": (215, 22, 35),
            "shorts": (18, 20, 24),
            "shorts_style": "three_stripes",
            "shorts_accent": (252, 252, 255),
            "socks": (252, 252, 255),
            "socks_style": "turnover_hoop",
            "socks_accent": (215, 22, 35),
        }
    },
    {
        "id": "arch_4_kinetic_streetwear",
        "num": 4,
        "name": "The Kinetic Streetwear",
        "club_name": "Manchester City (Third Kit)",
        "subtitle": "Obsidian Deep Shell with Electric High-Voltage Fractures",
        "philosophy": "Transforms football kits into lifestyle streetwear. High-energy mathematical fractals, electric lightning, or soundwaves streak across a pitch-black shell, unified by cyber-neon fluorescent branding.",
        "design": {
            "body": (16, 22, 34),
            "second": (0, 210, 255),
            "accent": (255, 55, 95),
            "pattern": "165",
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
        "id": "arch_5_art_camo",
        "num": 5,
        "name": "The Organic / Art Camo",
        "club_name": "Bayern Munich (Festival Special Edition)",
        "subtitle": "Intricate Botanical Graphics Balanced by Strict Trimming",
        "philosophy": "Masterclass in artistic restraint: 'The louder the torso, the calmer the trims.' Complex watercolor floral camo spans the torso, but collar ribbing, cuffs, shorts, and sponsors are strictly solid monochrome so the design never looks chaotic.",
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
        "id": "arch_6_luxury_couture",
        "num": 6,
        "name": "The Luxury Couture",
        "club_name": "Real Madrid (Y-3 Lifestyle Edition)",
        "subtitle": "Architectural Neutral Minimalism & Metallic Relief",
        "philosophy": "Couture fashion-house collaboration aesthetic (Y-3, Jordan, Balenciaga). Stark architectural bone/cream chassis, sharp crossover V-neck, shoulder racing tape, and heavy 3D silicone liquid gold or chrome badges.",
        "design": {
            "body": (246, 243, 236),
            "second": (20, 22, 26),
            "accent": (215, 180, 75),
            "pattern": "plain",
            "finish": "liquid_gold",
            "sleeve_style": "shoulder_stripe",
            "stripe_accent": (20, 22, 26),
            "supplier_name": "adidas",
            "supplier": str(ROOT / "content" / "KitGenerator" / "suppliers" / "adidas_dark.png"),
            "badge": str(ROOT / "content" / "KitGenerator" / "badges" / "109.png"),
            "sponsor": str(ROOT / "content" / "KitGenerator" / "logos" / "fly_emirates.png"),
            "sleeve_sponsor": str(ROOT / "generator" / "sleeve_logos" / "hp.png"),
            "collar_style": "v_neck",
            "collar_tip": (20, 22, 26),
            "cuff": (246, 243, 236),
            "cuff_tip": (20, 22, 26),
            "shorts": (20, 22, 26),
            "shorts_style": "solid",
            "socks": (246, 243, 236),
            "socks_style": "turnover_hoop",
            "socks_accent": (20, 22, 26),
        }
    },
    {
        "id": "arch_7_retro_revival",
        "num": 7,
        "name": "The 90s Retro Revival",
        "club_name": "Arsenal ('Bruised Banana' Cult Heritage)",
        "subtitle": "Nostalgic 1990s Geometric Chevrons & Tailored Polo Placket",
        "philosophy": "Celebrates the golden era of 1990s football kits. Features bold repeating geometric chevron graphics, a tailored fold-down polo collar with dual buttons and cross-stitching thread, and classic athletic trims.",
        "design": {
            "body": (252, 212, 20),
            "second": (16, 28, 62),
            "accent": (218, 2, 29),
            "pattern": "111",
            "var": 0,
            "width_step": 3,
            "supplier_name": "adidas",
            "supplier": str(ROOT / "content" / "KitGenerator" / "suppliers" / "adidas_dark.png"),
            "badge": str(ROOT / "content" / "KitGenerator" / "badges" / "101.png"),
            "sponsor": str(ROOT / "content" / "KitGenerator" / "logos" / "fly_emirates.png"),
            "sleeve_sponsor": str(ROOT / "generator" / "sleeve_logos" / "visit_rwanda.png"),
            "collar_style": "polo",
            "collar": (16, 28, 62),
            "collar_tip": (252, 212, 20),
            "cuff": (16, 28, 62),
            "cuff_tip": (252, 212, 20),
            "shorts": (16, 28, 62),
            "shorts_style": "three_stripes",
            "shorts_accent": (252, 212, 20),
            "socks": (252, 212, 20),
            "socks_style": "turnover_hoop",
            "socks_accent": (16, 28, 62),
        }
    },
    {
        "id": "arch_8_tech_utility",
        "num": 8,
        "name": "The Tech-Utility Glitch",
        "club_name": "Chelsea FC (Third Kit / Digital Topography)",
        "subtitle": "Digital Cyber Aesthetics & Real Elevation Contours",
        "philosophy": "High-tech performance utility blending outdoor technical gear with digital culture. Features real topographic elevation contour lines in holographic mint against deep carbon shells, with liquid chrome branding and laser-cut vents.",
        "design": {
            "body": (14, 20, 32),
            "second": (25, 215, 185),
            "accent": (205, 215, 225),
            "pattern": "044",
            "finish": "chrome_silver",
            "supplier_name": "nike",
            "supplier": str(ROOT / "content" / "KitGenerator" / "suppliers" / "nike_white.png"),
            "badge": str(ROOT / "content" / "KitGenerator" / "badges" / "102.png"),
            "sponsor": str(ROOT / "content" / "KitGenerator" / "logos" / "bingx_white.png"),
            "sleeve_sponsor": str(ROOT / "generator" / "sleeve_logos" / "bingx_white.png"),
            "vent_style": "laser_cut",
            "collar_style": "crew",
            "collar_tip": (25, 215, 185),
            "cuff": (14, 20, 32),
            "cuff_tip": (25, 215, 185),
            "shorts": (14, 20, 32),
            "shorts_style": "side_stripe",
            "shorts_accent": (25, 215, 185),
            "socks": (14, 20, 32),
            "socks_style": "calf_band",
            "socks_accent": (25, 215, 185),
        }
    }
]

def to_b64(im):
    buf = BytesIO()
    im.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

html_cards = []

for arch in ARCHETYPES:
    print(f"Rendering Archetype {arch['num']}: {arch['name']} ({arch['club_name']})...")
    d = arch["design"]
    png_out = OUT_DIR / f"{arch['id']}.png"
    atlas = kit_render.render_kit(d, None, masks=masks)
    atlas.save(png_out)

    # Crops for detail showcase:
    crop_chest = atlas.crop((750, 1080, 1300, 1420))
    crop_flank = atlas.crop((680, 1150, 820, 1600))
    crop_neck = atlas.crop((940, 70, 1100, 160))
    crop_tech = atlas.crop((720, 1805, 840, 1865)).resize((360, 180), Image.NEAREST)
    crop_weave = atlas.crop((960, 1460, 1080, 1580)).resize((360, 360), Image.NEAREST)

    atlas_b64 = to_b64(atlas.resize((600, 600), Image.LANCZOS))
    chest_b64 = to_b64(crop_chest)
    flank_b64 = to_b64(crop_flank)
    neck_b64 = to_b64(crop_neck)
    tech_b64 = to_b64(crop_tech)
    weave_b64 = to_b64(crop_weave)

    html_cards.append(f"""
    <div class="archetype-card" id="{arch['id']}">
        <div class="card-header">
            <div class="badge-num">Archetype {arch['num']} of 8</div>
            <h2>{arch['name']} <span class="club-tag">{arch['club_name']}</span></h2>
            <div class="subtitle">{arch['subtitle']}</div>
            <p class="philosophy"><strong>Design Philosophy:</strong> {arch['philosophy']}</p>
        </div>
        
        <div class="card-body">
            <div class="atlas-view">
                <div class="view-tag">2048x2048 UV Atlas (Master Texture)</div>
                <img src="data:image/png;base64,{atlas_b64}" class="atlas-img" alt="{arch['name']}">
            </div>
            
            <div class="crops-view">
                <div class="view-tag">High-Resolution Physical Detail Crops</div>
                <div class="crops-grid">
                    <div class="crop-box">
                        <span class="crop-title">3D Silicone Crest & Sponsor</span>
                        <img src="data:image/png;base64,{chest_b64}">
                        <span class="crop-caption">Contact shadow (+1,+2px) & specular highlight</span>
                    </div>
                    <div class="crop-box">
                        <span class="crop-title">Tailored Seams & Flank Panel</span>
                        <img src="data:image/png;base64,{flank_b64}">
                        <span class="crop-caption">Dual-tone recessed seam threads & underarm venting</span>
                    </div>
                    <div class="crop-box">
                        <span class="crop-title">Inner Neck Tape & Match Sizing</span>
                        <img src="data:image/png;base64,{neck_b64}">
                        <span class="crop-caption">Upper back ribbon tape visible in collar opening</span>
                    </div>
                    <div class="crop-box">
                        <span class="crop-title">Fabric Micro-Knit Weave</span>
                        <img src="data:image/png;base64,{weave_b64}">
                        <span class="crop-caption">Tactile 4x4 piqué matte grain (0% plastic sheen)</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """)

html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>PES 2021 / FL27 - The 8 Modern Kit Archetypes Showcase</title>
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
            max-width: 950px;
            margin: 0 auto 40px auto;
        }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 12px;
            color: #58a6ff;
            letter-spacing: -0.5px;
        }}
        .header p {{
            color: #8b949e;
            font-size: 1.15rem;
            line-height: 1.6;
        }}
        .nav-pills {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: center;
            margin-bottom: 40px;
            max-width: 1100px;
            margin-left: auto;
            margin-right: auto;
        }}
        .nav-pill {{
            background: #161b22;
            color: #8b949e;
            border: 1px solid #30363d;
            padding: 8px 16px;
            border-radius: 20px;
            text-decoration: none;
            font-size: 0.85rem;
            font-weight: 600;
            transition: all 0.2s ease;
        }}
        .nav-pill:hover {{
            color: #58a6ff;
            border-color: #58a6ff;
            background: #21262d;
        }}
        .archetype-card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 14px;
            padding: 30px;
            margin-bottom: 50px;
            box-shadow: 0 12px 36px rgba(0,0,0,0.5);
        }}
        .card-header {{
            margin-bottom: 24px;
            border-bottom: 1px solid #21262d;
            padding-bottom: 16px;
        }}
        .badge-num {{
            display: inline-block;
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            padding: 4px 10px;
            border-radius: 12px;
            margin-bottom: 8px;
        }}
        .card-header h2 {{
            margin: 0 0 6px 0;
            color: #f0f6fc;
            font-size: 1.8rem;
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .club-tag {{
            font-size: 1.05rem;
            color: #8b949e;
            font-weight: 400;
        }}
        .subtitle {{
            color: #58a6ff;
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 12px;
        }}
        .philosophy {{
            color: #c9d1d9;
            font-size: 0.95rem;
            line-height: 1.5;
            margin: 0;
        }}
        .card-body {{
            display: flex;
            gap: 28px;
            flex-wrap: wrap;
        }}
        .atlas-view {{
            flex: 0 0 460px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .crops-view {{
            flex: 1;
            min-width: 380px;
        }}
        .view-tag {{
            font-size: 0.85rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
            color: #8b949e;
            width: 100%;
        }}
        .atlas-img {{
            width: 100%;
            max-width: 460px;
            border-radius: 8px;
            border: 1px solid #30363d;
            background: #000;
            box-shadow: 0 4px 16px rgba(0,0,0,0.4);
        }}
        .crops-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
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
            margin: 8px 0;
            border: 1px solid #30363d;
            background: #05070a;
        }}
        .crop-title {{
            font-size: 0.8rem;
            font-weight: 600;
            color: #79c0ff;
        }}
        .crop-caption {{
            font-size: 0.72rem;
            color: #8b949e;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>The 8 World Football Kit Archetypes</h1>
        <p>A comprehensive architectural grammar for PES 2021 & SP Football Life 2027. Demonstrating how strict aesthetic rules eliminate AI randomness, preserve iconic club identities, and guarantee infinite seasonal uniqueness without clashing.</p>
    </div>
    
    <div class="nav-pills">
        <a href="#arch_1_athletic" class="nav-pill">1. Athletic Color-Block</a>
        <a href="#arch_2_heritage_stripe" class="nav-pill">2. Heritage Stripe</a>
        <a href="#arch_3_diagonal_sash" class="nav-pill">3. Diagonal Sash</a>
        <a href="#arch_4_kinetic_streetwear" class="nav-pill">4. Kinetic Streetwear</a>
        <a href="#arch_5_art_camo" class="nav-pill">5. Art / Floral Camo</a>
        <a href="#arch_6_luxury_couture" class="nav-pill">6. Luxury Couture</a>
        <a href="#arch_7_retro_revival" class="nav-pill">7. 90s Retro Revival</a>
        <a href="#arch_8_tech_utility" class="nav-pill">8. Tech-Utility Glitch</a>
    </div>

    {''.join(html_cards)}
</body>
</html>
"""

showcase_file = ROOT / "archetypes_showcase.html"
showcase_file.write_text(html_doc, encoding="utf-8")
print(f"8 Archetypes showcase generated successfully at: {showcase_file}")
