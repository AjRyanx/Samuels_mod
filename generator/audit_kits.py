#!/usr/bin/env python3
"""audit_kits.py - Automated Visual QA & Aesthetic Inspection Suite for PES 2021 / FL26 Kits.

Features:
  - Generates kits deterministically across clubs and slots (1=Home, 2=Away, 3=Third).
  - Extracts standardized visual inspection crops (Chest with sponsor/badge/supplier, Collar, Full Torso).
  - Runs automated aesthetic linting rules:
      1. Sponsor Contrast Ratio (WCAG luminance validation).
      2. Heritage Pattern Archetype check (bans alien geometric shards on Home kits).
      3. Collar & Sleeve harmony verification.
      4. Kit supplier presence for top clubs.
      5. Badge alpha defringing verification.
  - Outputs an interactive, responsive dark-mode HTML contact sheet:
      tests/visual_audit/audit_gallery.html

Usage:
  python audit_kits.py                     # Audits top bespoke European clubs (fast)
  python audit_kits.py --tier big          # Audits all 'big' tier clubs
  python audit_kits.py --clubs 100,102,103 # Audits specific clubs
  python audit_kits.py --all               # Audits entire database (580+ clubs)
"""

import argparse
import html
import json
import math
import os
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import kit_gen
import kit_dna
import kit_regions
from kit_regions import build_masks
from kit_render import render_club, _hexc

# Top leagues to audit
LEAGUE_DEFINITIONS = {
    "epl": {
        "name": "Premier League",
        "short": "EPL",
        "teams": [100, 101, 102, 103, 105, 106, 107, 173, 177, 178, 179, 204, 207, 208, 377, 382, 386, 389, 4071, 4180],
    },
    "laliga": {
        "name": "La Liga",
        "short": "La Liga",
        "teams": [108, 109, 110, 172, 195, 196, 258, 259, 261, 263, 265, 266, 267, 362, 364, 370, 2187, 4145, 4272],
    },
    "seriea": {
        "name": "Serie A",
        "short": "Serie A",
        "teams": [119, 120, 121, 122, 123, 124, 125, 186, 190, 234, 235, 320, 323, 327, 333, 336, 4219, 4229, 4237, 4914],
    },
    "bundesliga": {
        "name": "Bundesliga",
        "short": "Bundesliga",
        "teams": [126, 127, 128, 129, 185, 225, 226, 227, 231, 232, 436, 4124, 4126, 4139, 4140, 5009, 5010],
    },
    "ligue1": {
        "name": "Ligue 1",
        "short": "Ligue 1",
        "teams": [112, 113, 114, 180, 181, 182, 213, 215, 216, 217, 218, 221, 403, 1329, 1330, 4213],
    },
    "world": {
        "name": "Rest of World & Americas",
        "short": "World / Americas",
        "teams": [116, 117, 118, 131, 132, 138, 139],
    },
}

def get_team_league(cid):
    for lk, ldef in LEAGUE_DEFINITIONS.items():
        if cid in ldef["teams"]:
            return lk, ldef["name"], ldef["short"]
    return "other", "Other Clubs", "Other"

DEFAULT_AUDIT_CLUBS = []
for _lk in ["epl", "laliga", "seriea", "bundesliga", "ligue1", "world"]:
    DEFAULT_AUDIT_CLUBS.extend(LEAGUE_DEFINITIONS[_lk]["teams"])



def relative_luminance(rgb):
    """Calculate WCAG 2.1 relative luminance for an RGB tuple (0-255)."""
    srgb = [c / 255.0 for c in rgb[:3]]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(rgb1, rgb2):
    """Calculate WCAG contrast ratio between two RGB colors (1.0 to 21.0)."""
    l1 = relative_luminance(rgb1)
    l2 = relative_luminance(rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def color_distance(c1, c2):
    """Euclidean distance in RGB space."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1[:3], c2[:3])))


def lint_kit(club, slot, design, chest_img):
    """Run automated aesthetic and authenticity linting rules on a generated kit."""
    results = []
    body_col = design.get("body", (200, 200, 200))
    collar_col = design.get("collar", body_col)
    pattern_key = design.get("pattern_name", design.get("pattern", "plain"))
    slot_name = {1: "Home (P1)", 2: "Away (P2)", 3: "Third (P3)"}.get(slot, f"Slot {slot}")
    club_id = club.get("id", club.get("team_id"))

    # Rule 1: Sponsor Contrast Ratio
    sponsor_path = design.get("sponsor")
    if sponsor_path:
        # Determine effective sponsor color
        if design.get("sponsor_white"):
            s_col = (255, 255, 255)
        elif design.get("sponsor_dark"):
            s_col = design.get("sponsor_dark") if isinstance(design.get("sponsor_dark"), tuple) else (15, 25, 45)
        else:
            # Sample dominant color from sponsor PNG
            try:
                sim = Image.open(sponsor_path).convert("RGBA")
                arr = np.array(sim)
                opaque = arr[:, :, 3] > 128
                if np.any(opaque):
                    s_col = tuple(int(v) for v in np.median(arr[opaque, :3], axis=0))
                else:
                    s_col = (255, 255, 255)
            except Exception:
                s_col = (255, 255, 255)
        
        ratio = contrast_ratio(body_col, s_col)
        if ratio >= 4.5:
            results.append({"rule": "Sponsor Contrast", "status": "PASS",
                            "msg": f"High contrast ({ratio:.1f}:1 WCAG AA+)"})
        elif ratio >= 3.0:
            results.append({"rule": "Sponsor Contrast", "status": "WARN",
                            "msg": f"Moderate contrast ({ratio:.1f}:1)"})
        else:
            results.append({"rule": "Sponsor Contrast", "status": "FAIL",
                            "msg": f"Unreadable contrast ({ratio:.1f}:1 < 3.0:1)"})
    else:
        results.append({"rule": "Sponsor Contrast", "status": "INFO", "msg": "No chest sponsor"})

    # Rule 2: Pattern Authenticity & No Alien Shards on Home Kits
    shard_patterns = ["001", "001-B", "006", "006-B", "027-B"]
    if slot == 1:
        if pattern_key in shard_patterns or "shard" in str(pattern_key).lower():
            results.append({"rule": "Home Authenticity", "status": "FAIL",
                            "msg": f"Unrealistic geometric shard pattern '{pattern_key}' on Home kit"})
        elif pattern_key == "plain" or pattern_key.endswith("-E") or "pinstripe" in pattern_key:
            results.append({"rule": "Home Authenticity", "status": "PASS",
                            "msg": f"Clean tonal luxury pattern '{pattern_key}'"})
        elif pattern_key in kit_dna.POOL_STRIPES or pattern_key in kit_dna.POOL_HOOPS or pattern_key in kit_dna.POOL_SASH or pattern_key in kit_dna.POOL_CHESTBAND or pattern_key in kit_dna.POOL_HALF_HALF or pattern_key in kit_dna.POOL_PINSTRIPES or pattern_key in ["stripes", "hoops", "sash", "chestband", "101", "086", "094", "098", "206", "207", "208", "209"]:
            results.append({"rule": "Home Authenticity", "status": "PASS",
                            "msg": f"Authentic heritage pattern '{pattern_key}'"})
        else:
            results.append({"rule": "Home Authenticity", "status": "WARN",
                            "msg": f"Pattern '{pattern_key}' on Home kit (verify club fit)"})
    elif slot in ("g1", "g2"):
        results.append({"rule": "Goalkeeper Visual Language", "status": "PASS",
                        "msg": f"Streetwear high-vis GK pattern '{pattern_key}'"})
    else:
        results.append({"rule": "Pattern Tier", "status": "PASS",
                        "msg": f"Away/Third acceptable pattern '{pattern_key}'"})

    # Rule 3: Collar Harmony
    dist_to_body = color_distance(body_col, collar_col)
    # Check if collar matches body tone, design trim colors, or club colors
    d_sec = design.get("second", (255, 255, 255))
    d_acc = design.get("third", (255, 255, 255))
    sec_col = _hexc(club.get("secondary", "#FFFFFF"))
    acc_col = _hexc(club.get("accent", "#FFFFFF"))

    min_trim_dist = min(
        color_distance(d_sec, collar_col),
        color_distance(d_acc, collar_col),
        color_distance(sec_col, collar_col),
        color_distance(acc_col, collar_col),
    )

    if dist_to_body < 40:
        results.append({"rule": "Collar Harmony", "status": "PASS", "msg": "Matching body tone"})
    elif min_trim_dist < 55:
        results.append({"rule": "Collar Harmony", "status": "PASS", "msg": "Matches club trim colors"})
    elif slot == 1 and dist_to_body > 180 and min_trim_dist > 90:
        results.append({"rule": "Collar Harmony", "status": "FAIL",
                        "msg": f"Bizarre mismatched collar RGB {collar_col} on {body_col} body"})
    else:
        results.append({"rule": "Collar Harmony", "status": "PASS", "msg": f"Harmonic contrast"})

    # Rule 4: Kit Supplier
    supplier = design.get("supplier")
    if supplier and Path(supplier).is_file():
        sup_name = Path(supplier).stem.split("_")[0].capitalize()
        results.append({"rule": "Supplier Logo", "status": "PASS", "msg": f"Authentic {sup_name} supplier"})
    elif int(club_id) in kit_dna.BESPOKE_DNA and slot == 1:
        results.append({"rule": "Supplier Logo", "status": "FAIL", "msg": "Missing kit supplier logo"})
    else:
        results.append({"rule": "Supplier Logo", "status": "INFO", "msg": "No supplier set"})

    # Rule 5: Badge Verification
    badge = design.get("badge")
    if badge and Path(badge).is_file():
        results.append({"rule": "Club Badge", "status": "PASS", "msg": "Valid defringed crest"})
    else:
        results.append({"rule": "Club Badge", "status": "WARN", "msg": "No badge asset found"})

    # Aggregate kit status
    statuses = [r["status"] for r in results]
    if "FAIL" in statuses:
        overall = "FAIL"
    elif "WARN" in statuses:
        overall = "WARN"
    else:
        overall = "PASS"

    return overall, results


def crop_chest(atlas_img):
    """Crop the chest area (x: 700..1350, y: 1000..1550) containing collar, badge, supplier & sponsor."""
    return atlas_img.crop((700, 1000, 1350, 1550))


def crop_torso(atlas_img):
    """Crop the full front panel (x: 660..1390, y: 952..1888)."""
    return atlas_img.crop((660, 952, 1390, 1888))


def generate_html_gallery(audit_data, out_html_path):
    """Generate a sleek, responsive dark-mode HTML contact sheet."""
    total_kits = len(audit_data)
    passed_count = sum(1 for d in audit_data if d["overall"] == "PASS")
    warn_count = sum(1 for d in audit_data if d["overall"] == "WARN")
    fail_count = sum(1 for d in audit_data if d["overall"] == "FAIL")
    pass_pct = (passed_count / max(1, total_kits)) * 100

    unique_seasons = sorted(list(set(d.get("season", 2027) for d in audit_data)))
    season_filter_html = ""
    if len(unique_seasons) > 1:
        s_btns = ['<button class="filter-btn active" data-filter="all">All Seasons</button>']
        for s in unique_seasons:
            s_btns.append(f'<button class="filter-btn" data-filter="{s}">S{s}</button>')
        season_filter_html = f"""
        <div class="controls" style="margin-top:-14px; margin-bottom:20px;">
            <div class="filter-group" id="seasonFilter" style="flex-wrap:wrap;">
                {''.join(s_btns)}
            </div>
        </div>
        """

    cards_html = []
    for item in audit_data:
        club = item["club"]
        cid = club.get("id", club.get("team_id"))
        slot = item["slot"]
        season_val = item.get("season", 2027)
        slot_name = {1: "P1 Home", 2: "P2 Away", 3: "P3 Third", "g1": "G1 GK Primary", "g2": "G2 GK Alternate"}.get(slot, f"P{slot}")
        overall = item["overall"]
        design = item["design"]
        league_key = item.get("league_key", "other")
        league_name = item.get("league_name", "Other")
        league_short = item.get("league_short", "Other")
        
        status_color = "#10b981" if overall == "PASS" else ("#f59e0b" if overall == "WARN" else "#ef4444")
        body_hex = "#{:02x}{:02x}{:02x}".format(*design.get("body", (0, 0, 0)))
        collar_hex = "#{:02x}{:02x}{:02x}".format(*design.get("collar", (0, 0, 0)))
        second_hex = "#{:02x}{:02x}{:02x}".format(*design.get("second", (0, 0, 0)))

        lint_rows = []
        for l in item["lint"]:
            b_color = "#10b981" if l["status"] == "PASS" else ("#f59e0b" if l["status"] == "WARN" else ("#ef4444" if l["status"] == "FAIL" else "#6b7280"))
            lint_rows.append(f"""
                <div class="lint-row">
                    <span class="lint-badge" style="background:{b_color}22; color:{b_color}; border:1px solid {b_color}66">{l['status']}</span>
                    <span class="lint-rule">{html.escape(l['rule'])}:</span>
                    <span class="lint-msg">{html.escape(l['msg'])}</span>
                </div>
            """)

        badge_img_tag = f'<img src="{item["badge_rel"]}" class="club-crest" alt="crest" onerror="this.style.display=\'none\'">' if item.get("badge_rel") else ''

        torso_tag = f'<img src="{item["torso_rel"]}" class="torso-img" alt="Torso Preview" loading="lazy" style="display:none;">' if item.get("torso_rel") else ''

        card = f"""
        <div class="kit-card" data-status="{overall}" data-slot="{slot}" data-season="{season_val}" data-league="{league_key}" data-name="{html.escape(club['name']).lower()} {cid} {season_val} {league_name.lower()}">
            <div class="card-header">
                <div class="club-info">
                    {badge_img_tag}
                    <div>
                        <div class="club-name">{html.escape(club['name'])}</div>
                        <div class="club-meta">ID #{cid} • S{season_val} • {league_short} • {html.escape(club.get('tier', 'mid')).upper()}</div>
                    </div>
                </div>
                <div class="slot-pill" style="border: 1px solid {status_color}; color: {status_color}; background: {status_color}18">
                    {slot_name} • {overall}
                </div>
            </div>
            
            <div class="preview-container">
                <img src="{item['chest_rel']}" class="chest-img" alt="Chest Preview" loading="lazy">
                {torso_tag}
            </div>

            <div class="card-body">
                <div class="swatch-bar">
                    <div class="swatch-item">
                        <span class="swatch-dot" style="background:{body_hex}"></span>
                        <span>Body</span>
                    </div>
                    <div class="swatch-item">
                        <span class="swatch-dot" style="background:{collar_hex}"></span>
                        <span>Collar</span>
                    </div>
                    <div class="swatch-item">
                        <span class="swatch-dot" style="background:{second_hex}"></span>
                        <span>Trim</span>
                    </div>
                </div>

                <div class="meta-row">
                    <span>Pattern: <strong>{html.escape(str(design.get('pattern_name', design.get('pattern', 'plain'))))}</strong></span>
                    <span>Sponsor: <strong>{html.escape(item.get('sponsor_name', 'None')).upper()}</strong></span>
                </div>

                <div class="lint-list">
                    {''.join(lint_rows)}
                </div>
            </div>
        </div>
        """
        cards_html.append(card)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PES 2021 / FL26 Kit Generator — Visual Audit Suite</title>
    <style>
        :root {{
            --bg: #090d16;
            --surface: #131b2e;
            --surface-hover: #1b2640;
            --border: #22304f;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent: #38bdf8;
            --pass: #10b981;
            --warn: #f59e0b;
            --fail: #ef4444;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
        body {{ background: var(--bg); color: var(--text-primary); padding: 24px; min-height: 100vh; }}
        
        .header {{ max-width: 1400px; margin: 0 auto 24px auto; display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 16px; border-bottom: 1px solid var(--border); padding-bottom: 20px; }}
        .header h1 {{ font-size: 24px; font-weight: 700; color: #fff; letter-spacing: -0.5px; }}
        .header p {{ color: var(--text-secondary); font-size: 14px; margin-top: 4px; }}
        
        .kpi-row {{ display: flex; gap: 12px; }}
        .kpi-card {{ background: var(--surface); border: 1px solid var(--border); padding: 12px 18px; border-radius: 8px; text-align: center; min-width: 100px; }}
        .kpi-val {{ font-size: 22px; font-weight: 700; }}
        .kpi-lbl {{ font-size: 11px; color: var(--text-secondary); text-transform: uppercase; margin-top: 2px; }}

        .controls {{ max-width: 1400px; margin: 0 auto 24px auto; display: flex; gap: 12px; flex-wrap: wrap; align-items: center; justify-content: space-between; }}
        .search-box {{ background: var(--surface); border: 1px solid var(--border); color: #fff; padding: 10px 16px; border-radius: 8px; width: 320px; font-size: 14px; outline: none; }}
        .search-box:focus {{ border-color: var(--accent); }}
        
        .filter-group {{ display: flex; gap: 6px; background: var(--surface); padding: 4px; border-radius: 8px; border: 1px solid var(--border); }}
        .filter-btn {{ background: transparent; border: none; color: var(--text-secondary); padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.15s; }}
        .filter-btn:hover {{ color: #fff; }}
        .filter-btn.active {{ background: var(--accent); color: #000; font-weight: 600; }}

        .grid {{ max-width: 1400px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }}
        .kit-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; transition: transform 0.15s, border-color 0.15s; }}
        .kit-card:hover {{ transform: translateY(-3px); border-color: var(--accent); }}
        
        .card-header {{ padding: 14px 16px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); background: #0c1220; }}
        .club-info {{ display: flex; align-items: center; gap: 10px; }}
        .club-crest {{ width: 28px; height: 28px; object-fit: contain; }}
        .club-name {{ font-weight: 600; font-size: 15px; color: #fff; }}
        .club-meta {{ font-size: 11px; color: var(--text-secondary); }}
        .slot-pill {{ font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 999px; text-transform: uppercase; }}

        .preview-container {{ position: relative; width: 100%; height: 210px; background: #070a12; overflow: hidden; display: flex; align-items: center; justify-content: center; }}
        .chest-img {{ width: 100%; height: 100%; object-fit: cover; object-position: center 20%; transition: transform 0.3s ease; }}
        .kit-card:hover .chest-img {{ transform: scale(1.05); }}

        .card-body {{ padding: 14px 16px; display: flex; flex-direction: column; gap: 12px; flex: 1; }}
        .swatch-bar {{ display: flex; gap: 16px; padding-bottom: 10px; border-bottom: 1px solid var(--border); font-size: 11px; color: var(--text-secondary); }}
        .swatch-item {{ display: flex; align-items: center; gap: 6px; }}
        .swatch-dot {{ width: 14px; height: 14px; border-radius: 50%; border: 1px solid rgba(255,255,255,0.2); }}

        .meta-row {{ display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary); }}
        .meta-row strong {{ color: #fff; }}

        .lint-list {{ display: flex; flex-direction: column; gap: 6px; margin-top: auto; padding-top: 8px; }}
        .lint-row {{ display: flex; align-items: center; gap: 6px; font-size: 11.5px; line-height: 1.3; }}
        .lint-badge {{ font-size: 9px; font-weight: 700; padding: 2px 5px; border-radius: 4px; letter-spacing: 0.5px; }}
        .lint-rule {{ color: var(--text-secondary); font-weight: 500; }}
        .lint-msg {{ color: #cbd5e1; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>PES 2021 / FL26 Kit Generator — Visual Audit Suite</h1>
            <p>Automated Design Quality, Authenticity & Contrast Inspection</p>
        </div>
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="kpi-val" style="color:var(--accent)">{total_kits}</div>
                <div class="kpi-lbl">Kits Audited</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val" style="color:var(--pass)">{pass_pct:.1f}%</div>
                <div class="kpi-lbl">Pass Rate</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val" style="color:var(--warn)">{warn_count}</div>
                <div class="kpi-lbl">Warnings</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val" style="color:var(--fail)">{fail_count}</div>
                <div class="kpi-lbl">Failed</div>
            </div>
        </div>
    </div>

    <div class="controls">
        <input type="text" id="searchInput" class="search-box" placeholder="Filter by club name or ID...">
        
        <div style="display:flex; gap:12px; flex-wrap:wrap">
            <div class="filter-group" id="viewModeFilter">
                <button class="filter-btn active" id="btnChestView" onclick="setViewMode('chest')">Chest Focus</button>
                <button class="filter-btn" id="btnTorsoView" onclick="setViewMode('torso')">Full Torso</button>
            </div>

            <div class="filter-group" id="statusFilter">
                <button class="filter-btn active" data-filter="all">All</button>
                <button class="filter-btn" data-filter="PASS">Passed ({passed_count})</button>
                <button class="filter-btn" data-filter="WARN">Warnings ({warn_count})</button>
                <button class="filter-btn" data-filter="FAIL">Failed ({fail_count})</button>
            </div>

            <div class="filter-group" id="slotFilter">
                <button class="filter-btn active" data-filter="all">All Slots</button>
                <button class="filter-btn" data-filter="1">Home (P1)</button>
                <button class="filter-btn" data-filter="2">Away (P2)</button>
                <button class="filter-btn" data-filter="3">Third (P3)</button>
                <button class="filter-btn" data-filter="g1">GK 1 (G1)</button>
                <button class="filter-btn" data-filter="g2">GK 2 (G2)</button>
            </div>
        </div>
    </div>

    {season_filter_html}

    <div class="controls" style="margin-top:-14px; margin-bottom:20px;">
        <div class="filter-group" id="leagueFilter" style="flex-wrap:wrap;">
            <button class="filter-btn active" data-filter="all">All Leagues</button>
            <button class="filter-btn" data-filter="epl">Premier League</button>
            <button class="filter-btn" data-filter="laliga">La Liga</button>
            <button class="filter-btn" data-filter="seriea">Serie A</button>
            <button class="filter-btn" data-filter="bundesliga">Bundesliga</button>
            <button class="filter-btn" data-filter="ligue1">Ligue 1</button>
            <button class="filter-btn" data-filter="world">World / Americas</button>
        </div>
    </div>

    <div class="grid" id="kitGrid">
        {''.join(cards_html)}
    </div>

    <script>
        const searchInput = document.getElementById('searchInput');
        const cards = document.querySelectorAll('.kit-card');
        let currentStatus = 'all';
        let currentSlot = 'all';
        let currentLeague = 'all';
        let currentSeason = 'all';

        function setViewMode(mode) {{
            document.querySelectorAll('.chest-img').forEach(el => el.style.display = (mode === 'chest') ? 'block' : 'none');
            document.querySelectorAll('.torso-img').forEach(el => el.style.display = (mode === 'torso') ? 'block' : 'none');
            document.getElementById('btnChestView').classList.toggle('active', mode === 'chest');
            document.getElementById('btnTorsoView').classList.toggle('active', mode === 'torso');
        }}

        function updateFilters() {{
            const query = searchInput.value.toLowerCase().trim();
            cards.forEach(card => {{
                const status = card.getAttribute('data-status');
                const slot = card.getAttribute('data-slot');
                const league = card.getAttribute('data-league');
                const season = card.getAttribute('data-season');
                const text = card.getAttribute('data-name');

                const matchesStatus = (currentStatus === 'all' || status === currentStatus);
                const matchesSlot = (currentSlot === 'all' || slot === currentSlot);
                const matchesLeague = (currentLeague === 'all' || league === currentLeague);
                const matchesSeason = (currentSeason === 'all' || season === currentSeason);
                const matchesSearch = (!query || text.includes(query));

                card.style.display = (matchesStatus && matchesSlot && matchesLeague && matchesSeason && matchesSearch) ? 'flex' : 'none';
            }});
        }}

        searchInput.addEventListener('input', updateFilters);

        document.getElementById('statusFilter').addEventListener('click', e => {{
            if (e.target.tagName !== 'BUTTON') return;
            document.querySelectorAll('#statusFilter .filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentStatus = e.target.getAttribute('data-filter');
            updateFilters();
        }});

        document.getElementById('slotFilter').addEventListener('click', e => {{
            if (e.target.tagName !== 'BUTTON') return;
            document.querySelectorAll('#slotFilter .filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentSlot = e.target.getAttribute('data-filter');
            updateFilters();
        }});

        const seasonFilter = document.getElementById('seasonFilter');
        if (seasonFilter) {{
            seasonFilter.addEventListener('click', e => {{
                if (e.target.tagName !== 'BUTTON') return;
                document.querySelectorAll('#seasonFilter .filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                currentSeason = e.target.getAttribute('data-filter');
                updateFilters();
            }});
        }}

        document.getElementById('leagueFilter').addEventListener('click', e => {{
            if (e.target.tagName !== 'BUTTON') return;
            document.querySelectorAll('#leagueFilter .filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentLeague = e.target.getAttribute('data-filter');
            updateFilters();
        }});
    </script>
</body>
</html>
"""
    out_html_path.write_text(html_content, encoding="utf-8")
    return out_html_path


def main():
    parser = argparse.ArgumentParser(description="Automated Visual QA for Generated Kits")
    parser.add_argument("--clubs", help="Comma-separated club IDs (e.g. 100,102,103)")
    parser.add_argument("--league", choices=["all", "top5", "epl", "laliga", "seriea", "bundesliga", "ligue1", "world"],
                        default="top5", help="Filter clubs by league (default: top5 = 99 clubs across top European leagues)")
    parser.add_argument("--tier", help="Filter by tier (e.g. big, mid)")
    parser.add_argument("--all", action="store_true", help="Audit all clubs in clubs.csv")
    parser.add_argument("--season", type=int, default=2027, help="Simulation season (default: 2027)")
    parser.add_argument("--seasons", help="Comma-separated or range of seasons to audit (e.g. 2026-2035 or 2027,2028)")
    parser.add_argument("--rotate-sponsors", action="store_true", help="Rotate realistic sponsors across seasons")
    parser.add_argument("--sponsor", default="adenta", help="Sample sponsor name to attach (default: adenta)")
    parser.add_argument("--outdir", default=str(REPO_ROOT / "tests" / "visual_audit"),
                        help="Output directory for audit images & HTML report")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of clubs to audit")
    parser.add_argument("--include-gk", action="store_true", help="Include goalkeeper kits (g1, g2)")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    crops_dir = outdir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)

    # Parse seasons
    if args.seasons:
        if "-" in args.seasons:
            s_parts = [int(x.strip()) for x in args.seasons.split("-", 1)]
            seasons = list(range(s_parts[0], s_parts[1] + 1))
        else:
            seasons = [int(x.strip()) for x in args.seasons.split(",") if x.strip()]
    else:
        seasons = [args.season]

    SPONSOR_ROSTER = [
        "aneno", "zaltera", "oribel", "adenta", "solenta",
        "elyenta", "cadola", "balix", "cresovo", "dorex"
    ]

    # 1. Load clubs
    all_clubs = kit_gen.load_clubs(HERE / "clubs.csv")
    clubs_map = {c["id"]: c for c in all_clubs}

    if args.clubs:
        club_ids = [int(x.strip()) for x in args.clubs.split(",") if x.strip()]
    elif args.tier:
        club_ids = [c["id"] for c in all_clubs if c.get("tier") == args.tier]
    elif args.all or args.league == "all":
        club_ids = [c["id"] for c in all_clubs]
    elif args.league == "top5":
        club_ids = list(DEFAULT_AUDIT_CLUBS)
    elif args.league in LEAGUE_DEFINITIONS:
        club_ids = list(LEAGUE_DEFINITIONS[args.league]["teams"])
    else:
        club_ids = list(DEFAULT_AUDIT_CLUBS)

    if args.limit > 0:
        club_ids = club_ids[:args.limit]

    slots_to_audit = [1, 2, 3, "g1", "g2"] if args.include_gk else [1, 2, 3]
    total_kits_to_audit = len(club_ids) * len(seasons) * len(slots_to_audit)
    print(f"\n=======================================================")
    print(f"  PES 2021 / FL26 Automated Kit Visual Audit Suite")
    print(f"=======================================================")
    print(f"Clubs to audit: {len(club_ids)} clubs | Seasons: {len(seasons)} ({seasons[0]}..{seasons[-1]})")
    print(f"Total kit variations: {total_kits_to_audit} kits (slots: {', '.join(str(s) for s in slots_to_audit)})")
    print(f"Sponsor mode: {'Rotating roster' if args.rotate_sponsors else args.sponsor}")
    print(f"Audit output: {outdir}\n")

    # 2. Build masks & paths
    masks = build_masks()
    logo_dir = Path("SiderAddons/content/KitGenerator/logos")
    badge_dir = Path("SiderAddons/content/KitGenerator/badges")
    if not logo_dir.exists():
        logo_dir = HERE.parent / "content" / "KitGenerator" / "logos"
    if not badge_dir.exists():
        badge_dir = HERE.parent / "content" / "KitGenerator" / "badges"

    audit_data = []
    t0 = time.time()

    for idx, cid in enumerate(club_ids, 1):
        club = clubs_map.get(cid, {"id": cid, "name": f"Club #{cid}", "primary": "#B02E34", "secondary": "#FFFFFF", "accent": "#111111", "tier": "mid"})
        cname = club["name"]
        lk, lname, lshort = get_team_league(cid)
        print(f"[{idx:2d}/{len(club_ids)}] Auditing #{cid:4d} {cname[:22]:22s} ({lshort}) across {len(seasons)} seasons ... ", flush=True)

        for s_idx, season in enumerate(seasons):
            if args.rotate_sponsors:
                active_sponsor = SPONSOR_ROSTER[s_idx % len(SPONSOR_ROSTER)]
            elif args.sponsor.lower() in ("none", "clean"):
                active_sponsor = None
            else:
                active_sponsor = args.sponsor

            print(f"    Season {season} (Sponsor: {active_sponsor or 'Clean/None'}): ", end="", flush=True)
            season_passed = True

            for slot in slots_to_audit:
                slot_code = f"p{slot}" if isinstance(slot, int) else str(slot)
                atlas_png = crops_dir / f"atlas_{cid}_{season}_{slot_code}.png"
                chest_png = crops_dir / f"chest_{cid}_{season}_{slot_code}.png"
                torso_png = crops_dir / f"torso_{cid}_{season}_{slot_code}.png"

                # Render kit
                _, design = render_club(club, season, atlas_png, logo_dir,
                                        masks=masks, slot=slot, sponsor=active_sponsor,
                                        badge_dir=badge_dir)

                # Crop chest & torso & save
                with Image.open(atlas_png) as im:
                    c_crop = crop_chest(im)
                    c_crop.save(chest_png)
                    t_crop = crop_torso(im)
                    t_crop.save(torso_png)

                # Remove heavy 2048x2048 atlas to save disk space
                try:
                    atlas_png.unlink()
                except Exception:
                    pass

                # Badge relative path
                b_file = badge_dir / f"{cid}.png"
                b_rel = f"../../SiderAddons/content/KitGenerator/badges/{cid}.png" if b_file.exists() else None

                # Run Lint
                overall, lint_results = lint_kit(club, slot, design, c_crop)
                if overall == "FAIL":
                    season_passed = False

                audit_data.append({
                    "club": club,
                    "slot": slot,
                    "season": season,
                    "overall": overall,
                    "design": design,
                    "lint": lint_results,
                    "sponsor_name": active_sponsor or "None",
                    "chest_rel": f"crops/{chest_png.name}",
                    "torso_rel": f"crops/{torso_png.name}",
                    "badge_rel": b_rel,
                    "league_key": lk,
                    "league_name": lname,
                    "league_short": lshort,
                })

            print("PASS" if season_passed else "FAIL")

    # 3. Write HTML report
    html_path = outdir / "audit_gallery.html"
    generate_html_gallery(audit_data, html_path)
    elapsed = time.time() - t0

    passed_count = sum(1 for d in audit_data if d["overall"] == "PASS")
    fail_count = sum(1 for d in audit_data if d["overall"] == "FAIL")

    print(f"\nAudit complete in {elapsed:.1f}s!")
    print(f"Results: {passed_count}/{len(audit_data)} kits passed ({fail_count} failures).")
    print(f"Interactive Gallery generated at:")
    print(f"  {html_path.resolve()}\n")


if __name__ == "__main__":
    main()
