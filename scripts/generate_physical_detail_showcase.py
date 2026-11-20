#!/usr/bin/env python3
"""Generate macro-crops and an interactive HTML report showcasing physical garment detailing."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "generator"))

import kit_render
import kit_regions

OUTPUT_DIR = REPO_ROOT / "showcase_details"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CROPS_DIR = OUTPUT_DIR / "crops"
CROPS_DIR.mkdir(parents=True, exist_ok=True)

masks = kit_regions.build_masks()

# 1. Arsenal 24/25 Style (Adidas, Red/White, HEAT.RDY, Raglan seams)
fly_emirates = REPO_ROOT / "content" / "KitGenerator" / "logos" / "fly_emirates.png"
d_arsenal = {
    "body": (215, 25, 32),
    "second": (250, 250, 250),
    "third": (15, 25, 60),
    "accent": (15, 25, 60),
    "pattern": "plain",
    "sleeve_style": "raglan",
    "sleeve_color": (250, 250, 250),
    "collar_style": "crew",
    "collar_color": (215, 25, 32),
    "supplier_name": "adidas",
    "sponsor": str(fly_emirates) if fly_emirates.is_file() else None,
    "sponsor_white": True,
    "tech_callout": True,
    "inner_neck_tape": True,
    "construction_seams": True,
    "fabric_texture": True,
    "heat_press_relief": True,
    "vent_style": "contrast_panel",
    "vent_color": (15, 25, 60),
}

# 2. Man City 23/24 Third Style (Puma, Navy/Cyan/Coral, ULTRAWEAVE)
d_mancity = {
    "body": (15, 24, 38),
    "second": (0, 210, 255),
    "third": (255, 75, 75),
    "accent": (255, 75, 75),
    "pattern": "127-B",
    "collar_style": "dual_tipped",
    "collar_color": (15, 24, 38),
    "supplier_name": "puma",
    "supplier_color": (255, 75, 75),
    "sponsor": str(fly_emirates) if fly_emirates.is_file() else None,
    "sponsor_dark": (255, 75, 75),
    "tech_callout": True,
    "inner_neck_tape": True,
    "construction_seams": True,
    "fabric_texture": True,
    "heat_press_relief": True,
    "finish": "liquid_gold",
}

# 3. Barcelona 24/25 125th Style (Nike, Blaugrana Halves, DRI-FIT ADV)
spotify_logo = REPO_ROOT / "content" / "KitGenerator" / "logos" / "spotify.png"
d_barca = {
    "body": (15, 32, 99),
    "second": (165, 0, 40),
    "third": (218, 165, 32),
    "accent": (218, 165, 32),
    "pattern": "halves",
    "collar_style": "v_neck",
    "collar_color": (15, 32, 99),
    "supplier_name": "nike",
    "supplier_color": (218, 165, 32),
    "sponsor": str(spotify_logo) if spotify_logo.is_file() else str(fly_emirates),
    "sponsor_dark": (218, 165, 32),
    "tech_callout": True,
    "inner_neck_tape": True,
    "construction_seams": True,
    "fabric_texture": True,
    "heat_press_relief": True,
}

KITS = [
    ("arsenal", "Arsenal 24/25 Aesthetic (HEAT.RDY + Raglan Seams)", d_arsenal),
    ("mancity", "Man City 23/24 Aesthetic (ULTRAWEAVE + Lightning)", d_mancity),
    ("barca", "Barcelona 125th Aesthetic (DRI-FIT ADV + Blaugrana)", d_barca),
]

cards_html = []

for kid, title, spec in KITS:
    atlas = kit_render.render_kit(spec, None, masks=masks)
    full_path = OUTPUT_DIR / f"{kid}_full.png"
    atlas.save(full_path)

    # Generate Macro Crops
    # Crop 1: Fabric Micro-Texture Weave (Torso piqué honeycomb)
    c1 = atlas.crop((950, 1400, 1150, 1600)).resize((400, 400), Image.NEAREST)
    c1_path = CROPS_DIR / f"{kid}_crop_texture.png"
    c1.save(c1_path)

    # Crop 2: 3D Silicone Relief & Contact Shadow (Chest Sponsor / Badge)
    c2 = atlas.crop((880, 1260, 1160, 1420)).resize((480, 274), Image.NEAREST)
    c2_path = CROPS_DIR / f"{kid}_crop_relief.png"
    c2.save(c2_path)

    # Crop 3: Athletic Seam & Flatlock Stitching (Flank seam + waist taper)
    c3 = atlas.crop((680, 1400, 780, 1600)).resize((300, 600), Image.NEAREST)
    c3_path = CROPS_DIR / f"{kid}_crop_seam.png"
    c3.save(c3_path)

    # Crop 4: Tech Stamp & Lower Hem (DRI-FIT ADV / HEAT.RDY / ULTRAWEAVE)
    c4 = atlas.crop((715, 1805, 835, 1855)).resize((480, 200), Image.NEAREST)
    c4_path = CROPS_DIR / f"{kid}_crop_tech.png"
    c4.save(c4_path)

    # Crop 5: Collar Ribbon & Inner Neck Tape
    c5 = atlas.crop((940, 70, 1108, 140)).resize((480, 200), Image.NEAREST)
    c5_path = CROPS_DIR / f"{kid}_crop_neck.png"
    c5.save(c5_path)

    cards_html.append(f"""
    <div class="kit-card">
      <h2>{title}</h2>
      <div class="crop-grid">
        <div class="crop-box">
          <span class="crop-tag">1. Micro-Knit Weave (Zoom x2)</span>
          <img src="crops/{kid}_crop_texture.png" alt="Fabric Weave">
          <p class="crop-desc">Diamond piqué knit grain with zero color drift.</p>
        </div>
        <div class="crop-box">
          <span class="crop-tag">2. 3D Silicone Relief & Contact Shadow</span>
          <img src="crops/{kid}_crop_relief.png" alt="3D Relief">
          <p class="crop-desc">Dual-pass ambient occlusion + specular rim light.</p>
        </div>
        <div class="crop-box">
          <span class="crop-tag">3. Flatlock Twin-Needle Seams</span>
          <img src="crops/{kid}_crop_seam.png" alt="Flatlock Seams">
          <p class="crop-desc">Interlocking thread loops along flank & raglan seams.</p>
        </div>
        <div class="crop-box">
          <span class="crop-tag">4. Supplier Tech Mark</span>
          <img src="crops/{kid}_crop_tech.png" alt="Tech Stamp">
          <p class="crop-desc">Official player-issue stamp ({spec.get("supplier_name", "").upper()} tech).</p>
        </div>
        <div class="crop-box">
          <span class="crop-tag">5. Collar Inner Neck Tape</span>
          <img src="crops/{kid}_crop_neck.png" alt="Inner Neck Tape">
          <p class="crop-desc">Woven ribbon & authentic match issue sizing print.</p>
        </div>
      </div>
    </div>
    """)

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Physical Garment Detailing Engine - Visual Proof</title>
<style>
  body {{
    background: #0d1117;
    color: #e6edf3;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    margin: 0;
    padding: 24px;
  }}
  h1 {{
    font-size: 28px;
    font-weight: 800;
    margin-bottom: 8px;
    color: #58a6ff;
  }}
  .subtitle {{
    font-size: 16px;
    color: #8b949e;
    margin-bottom: 28px;
  }}
  .kit-card {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 32px;
  }}
  .kit-card h2 {{
    margin-top: 0;
    font-size: 20px;
    color: #f0f6fc;
    border-bottom: 1px solid #21262d;
    padding-bottom: 12px;
  }}
  .crop-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    align-items: start;
  }}
  .crop-box {{
    background: #090d13;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 12px;
    text-align: center;
  }}
  .crop-tag {{
    display: block;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    color: #79c0ff;
    margin-bottom: 8px;
    letter-spacing: 0.5px;
  }}
  .crop-box img {{
    max-width: 100%;
    height: auto;
    border-radius: 4px;
    border: 1px solid #30363d;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  }}
  .crop-desc {{
    font-size: 13px;
    color: #8b949e;
    margin-top: 8px;
    margin-bottom: 0;
  }}
</style>
</head>
<body>
  <h1>Garment Physical Detailing & 3D Tactile Engine</h1>
  <div class="subtitle">Inspecting micro-knit textures, 3D silicone heat-press relief, flatlock stitching, inner neck tape, and supplier tech stamps across generated kits.</div>
  {"".join(cards_html)}
</body>
</html>
"""

report_file = OUTPUT_DIR / "physical_details_report.html"
report_file.write_text(html_content, encoding="utf-8")
print(f"Showcase generated at: {report_file}")
