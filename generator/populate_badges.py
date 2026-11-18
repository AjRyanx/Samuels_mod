#!/usr/bin/env python3
"""populate_badges.py - Auto-harvest club emblems from game files and save to badges/.

Collects high-resolution transparent PNG crests for teams from Scoreboard-Server,
menu-server, scoreboards, and livecpk/logos, standardizes them to RGBA, and saves
them to:
    SiderAddons/content/KitGenerator/badges/<team_id>.png
"""

import os
import re
import sys
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # SiderAddons/KitGenerator
SIDER = ROOT.parent  # C:\Games\SP Football Life 2027\SiderAddons
REPO_ROOT = SIDER.parent / "mods" / "Dynamic_Kit_and_Sponsor_mod_pes21"

DEST_DIRS = [
    SIDER / "content" / "KitGenerator" / "badges",
    REPO_ROOT / "content" / "KitGenerator" / "badges",
]

# Patterns for emblem files
P1 = re.compile(r"^e_0*(\d+)(?:_[a-z0-9_]+)?\.png$", re.IGNORECASE)
P2 = re.compile(r"^emb_0*(\d+)(?:_[a-z0-9_]+)?\.png$", re.IGNORECASE)

SEARCH_SUBS = [
    "livecpk/logos",
    "content/Scoreboard-Server",
    "content/menu-server",
    "content/scoreboards",
]


def score_candidate(path):
    fn = os.path.basename(path).lower()
    score = 0
    if "_ll.png" in fn:
        score += 500
    elif "_l.png" in fn:
        score += 200
    elif "_r.png" in fn:
        score += 50

    # Penalize monochrome black/white variants if color exists
    if "_w.png" in fn or "_w_ll.png" in fn or "_w_l.png" in fn:
        score -= 200
    if "_b.png" in fn or "_b_ll.png" in fn or "_b_l.png" in fn:
        score -= 150

    # Prioritize livecpk/logos and Official Premier League / official competition folders
    p_lower = path.lower()
    if "livecpk\\logos" in p_lower or "livecpk/logos" in p_lower:
        score += 150
    if "official premier league" in p_lower:
        score += 100

    try:
        with Image.open(path) as img:
            rgba = img.convert("RGBA")
            bbox = rgba.getbbox()
            if not bbox:
                return -999999
            bw = bbox[2] - bbox[0]
            bh = bbox[3] - bbox[1]
            ratio = bw / float(max(1, bh))

            # Club crests are square/shield (ratio 0.70 .. 1.35).
            # Sliced scoreboard banners/ribbons have ratios like 3.94 or < 0.5 - reject!
            if ratio < 0.70 or ratio > 1.35:
                return -999999

            # Bonus for near-square ratio (0.85 .. 1.15)
            ratio_dev = abs(ratio - 1.0)
            score += int((0.30 - min(0.30, ratio_dev)) * 1000)

            # Bonus for resolution (larger is sharper)
            score += min(bw, bh)
    except Exception:
        return -999999
    return score


def harvest_badges():
    for d in DEST_DIRS:
        d.mkdir(parents=True, exist_ok=True)

    candidates = {}
    for sub in SEARCH_SUBS:
        base = SIDER / sub
        if not base.exists():
            continue
        for root, _, files in os.walk(base):
            for f in files:
                m = P1.match(f) or P2.match(f)
                if m:
                    cid = int(m.group(1))
                    full = os.path.join(root, f)
                    if cid not in candidates:
                        candidates[cid] = []
                    candidates[cid].append(full)

    print(f"Discovered badge candidates for {len(candidates)} teams.")

    saved_count = 0
    for cid, plist in candidates.items():
        scored = []
        for p in plist:
            s = score_candidate(p)
            if s > 0:
                scored.append((s, p))

        if not scored:
            continue

        best_score, best_path = max(scored, key=lambda x: x[0])

        try:
            with Image.open(best_path) as img:
                rgba = img.convert("RGBA")
                for d in DEST_DIRS:
                    out_path = d / f"{cid}.png"
                    rgba.save(out_path, format="PNG")
            saved_count += 1
        except Exception as e:
            print(f"Error converting {best_path} for team {cid}: {e}")

    print(f"Successfully populated {saved_count} club badges into:")
    for d in DEST_DIRS:
        print(f"  {d}")


if __name__ == "__main__":
    harvest_badges()
