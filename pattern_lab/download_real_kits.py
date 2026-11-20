#!/usr/bin/env python3
"""download_real_kits.py - Harvest authentic real-world football kit patterns from online archives.

Downloads authentic kit patterns, templates, and goalkeeper graphics into
isolated pattern_lab/reference_downloads folders for design analysis.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_DOWNLOAD_DIR = HERE / "reference_downloads"

CATEGORIES = {
    "goalkeeper": [
        "Category:Football_kit_body/Adidas_specific_patterns/Goalkeeper",
        "Category:Football_kit_body/Nike_specific_patterns/Goalkeeper",
        "Category:Football_kit_body/Puma_specific_patterns/Goalkeeper",
        "Category:Football_kit_body/goalkeeper",
    ],
    "third_streetwear": [
        "Category:Football_kit_body/third_jersey",
        "Category:Football_kit_body/camouflage",
    ],
    "gradients": [
        "Category:Football_kit_body/gradients",
        "Category:Football_kit_body/curved",
    ],
    "outfield_modern": [
        "Category:Football_kit_body/Adidas_specific_patterns",
        "Category:Football_kit_body/Nike_specific_patterns",
        "Category:Football_kit_body/Puma_specific_patterns",
        "Category:Football_kit_body/Kappa_specific_patterns",
    ],
    "heritage": [
        "Category:Football_kit_body/halves",
        "Category:Football_kit_body/diagonal",
        "Category:Football_kit_body/horizontal",
        "Category:Football_kit_body/vertical",
    ],
}

# Wikimedia compliant User-Agent format: AppName/Version (URL; ContactEmail)
HEADERS = {
    "User-Agent": "SamuelsModKitResearch/1.0 (https://github.com/AjRyanx/Samuels_mod; contact@pesmod.org) Python-urllib"
}


def query_category_files(cat_name: str, limit: int = 15) -> list[str]:
    """Retrieve file titles from a category."""
    encoded_cat = urllib.parse.quote(cat_name)
    url = (
        f"https://commons.wikimedia.org/w/api.php?action=query"
        f"&list=categorymembers&cmtitle={encoded_cat}&cmtype=file&cmlimit={limit}&format=json"
    )
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            members = data.get("query", {}).get("categorymembers", [])
            return [m["title"] for m in members if m["title"].startswith("File:")]
    except Exception as e:
        print(f"  [warn] Failed to query {cat_name}: {e}")
        return []


def resolve_image_urls(titles: list[str]) -> dict[str, str]:
    """Batch resolve file titles to direct CDN image URLs."""
    if not titles:
        return {}
    results = {}
    chunk_size = 20
    for i in range(0, len(titles), chunk_size):
        chunk = titles[i : i + chunk_size]
        pipe_titles = "|".join(urllib.parse.quote(t) for t in chunk)
        url = (
            f"https://commons.wikimedia.org/w/api.php?action=query"
            f"&titles={pipe_titles}&prop=imageinfo&iiprop=url&format=json"
        )
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_info in pages.items():
                    title = page_info.get("title")
                    infos = page_info.get("imageinfo", [])
                    if title and infos and "url" in infos[0]:
                        results[title] = infos[0]["url"]
        except Exception as e:
            print(f"  [warn] Failed to resolve chunk: {e}")
        time.sleep(0.3)
    return results


def download_file(url: str, dest_path: Path) -> bool:
    """Download a file with timeout and error handling."""
    if dest_path.is_file() and dest_path.stat().st_size > 100:
        return True
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            if len(data) > 100:
                dest_path.write_bytes(data)
                return True
    except Exception as e:
        print(f"  [download error] {dest_path.name}: {e}")
    return False


def run_harvest(max_per_category: int = 15):
    print("=" * 80)
    print(" HARVESTING AUTHENTIC FOOTBALL KIT PATTERNS FROM ONLINE ARCHIVES")
    print("=" * 80)
    manifest = {}

    for cat_group, subcats in CATEGORIES.items():
        group_dir = BASE_DOWNLOAD_DIR / cat_group
        group_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n[*] Harvesting group: {cat_group.upper()} -> {group_dir.relative_to(HERE.parent)}")

        all_titles = []
        for sc in subcats:
            titles = query_category_files(sc, limit=max(5, max_per_category // len(subcats) + 2))
            all_titles.extend(titles)
            time.sleep(0.2)

        unique_titles = list(dict.fromkeys(all_titles))[:max_per_category]
        print(f"  Found {len(unique_titles)} pattern references. Resolving URLs...")
        url_map = resolve_image_urls(unique_titles)

        saved = 0
        group_manifest = []
        for title, url in url_map.items():
            clean_name = title.replace("File:", "").replace(" ", "_")
            out_file = group_dir / clean_name
            if download_file(url, out_file):
                saved += 1
                group_manifest.append({
                    "title": title,
                    "filename": clean_name,
                    "url": url,
                    "path": str(out_file.relative_to(HERE.parent)),
                })
            time.sleep(0.25)

        print(f"  Successfully downloaded {saved}/{len(url_map)} patterns for {cat_group}.")
        manifest[cat_group] = group_manifest

    manifest_file = BASE_DOWNLOAD_DIR / "harvest_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("\n" + "=" * 80)
    print(f" HARVEST COMPLETE: Manifest saved to {manifest_file.relative_to(HERE.parent)}")
    print("=" * 80)


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    run_harvest(max_per_category=count)
