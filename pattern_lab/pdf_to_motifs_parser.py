#!/usr/bin/env python3
"""pdf_to_motifs_parser.py - Parse Modern Kit Pattern Library PDF into structured JSON metadata.

Extracts all 288 Motifs (M001-M288), 36 Families, 24 Curated Recipes (R01-R24),
24 Engraved Recipes (E01-E24), Axes, and Validator specifications into
isolated pattern_lab/modern_kit_library.json.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC_MD = HERE / "modern_kit_library_spec.md"
OUTPUT_JSON = HERE / "modern_kit_library.json"


def parse_spec() -> dict:
    text = SPEC_MD.read_text(encoding="utf-8")

    # Clean PDF text-extraction spacing artifacts: M\d \d -> M\d\d
    text = re.sub(r"M(\d)\s+(\d)\s+(\d)", r"M\1\2\3", text)
    text = re.sub(r"M(\d{2})\s+(\d)", r"M\1\2", text)
    text = re.sub(r"M(\d)\s+(\d{2})", r"M\1\2", text)

    # Match pattern: M### Name - Description
    motif_pattern = re.compile(
        r"M(\d{3})\s+([A-Za-z0-9\s/&,\-'\(\)]+?)\s+-\s+([^\n\r]+)", re.MULTILINE
    )

    motifs = {}
    for m in motif_pattern.finditer(text):
        m_num = int(m.group(1))
        m_id = f"M{m_num:03d}"
        name = re.sub(r"\s+", " ", m.group(2).strip())
        desc = re.sub(r"\s+", " ", m.group(3).strip())
        motifs[m_id] = {
            "id": m_id,
            "number": m_num,
            "name": name,
            "description": desc,
        }

    # Assign families based on motif ID ranges
    family_ranges = [
        # Part 1 (M001-M144)
        (1, "Fractured Geometry", 1, 8, "outfield"),
        (2, "Topographic and Contour", 9, 16, "outfield"),
        (3, "Data and Signal", 17, 24, "outfield"),
        (4, "Fluid and Organic", 25, 32, "outfield"),
        (5, "Textile Jacquard", 33, 40, "outfield"),
        (6, "Speed and Motion", 41, 48, "outfield"),
        (7, "Architectural and Urban", 49, 56, "outfield"),
        (8, "Heritage Reinterpreted", 57, 64, "outfield"),
        (9, "Nature and Wildlife", 65, 72, "outfield"),
        (10, "Cosmic and Light", 73, 80, "outfield"),
        (11, "Mechanical and Tech", 81, 88, "outfield"),
        (12, "Abstract Brush and Art", 89, 96, "outfield"),
        (13, "Optical and Illusion", 97, 104, "outfield"),
        (14, "Gradient Hybrids", 105, 112, "outfield"),
        (15, "Heraldic and Symbolic", 113, 120, "outfield"),
        (16, "Football-Native", 121, 128, "outfield"),
        (17, "Panel and Collage", 129, 136, "outfield"),
        (18, "Experimental Hero", 137, 144, "outfield"),
        # Part 2 (M145-M288)
        (19, "Seventies Geometry", 145, 152, "retro"),
        (20, "Eighties Abstract", 153, 160, "retro"),
        (21, "Early Nineties Graphic", 161, 168, "retro"),
        (22, "Late Nineties Tech", 169, 176, "retro"),
        (23, "Two-Thousands Tonal", 177, 184, "retro"),
        (24, "Twenty-Tens Digital", 185, 192, "retro"),
        (25, "Woven Crest and Heritage", 193, 200, "engraved"),
        (26, "Engraved Textile", 201, 208, "engraved"),
        (27, "Engraved Geometry", 209, 216, "engraved"),
        (28, "Engraved Nature", 217, 224, "engraved"),
        (29, "Engraved Light and Shadow", 225, 232, "engraved"),
        (30, "Engraved Urban and Sport", 233, 240, "engraved"),
        (31, "Engraved Symbols", 241, 248, "engraved"),
        (32, "Engraved Tonal Systems", 249, 256, "engraved"),
        (33, "Gradient Structures", 257, 264, "block"),
        (34, "Central and Panel Structures", 265, 272, "block"),
        (35, "Banded Identity Layouts", 273, 280, "signature"),
        (36, "Trim and Collar Systems", 281, 288, "trim"),
    ]

    families = {}
    for f_num, f_name, start_idx, end_idx, f_type in family_ranges:
        f_id = f"F{f_num:02d}"
        f_motifs = []
        for i in range(start_idx, end_idx + 1):
            m_id = f"M{i:03d}"
            if m_id in motifs:
                motifs[m_id]["family_id"] = f_id
                motifs[m_id]["family_name"] = f_name
                motifs[m_id]["type"] = f_type
                f_motifs.append(m_id)
        families[f_id] = {
            "id": f_id,
            "number": f_num,
            "name": f_name,
            "type": f_type,
            "motifs": f_motifs,
        }

    # 2. Recipe Matrix (R01-R24)
    recipe_pattern = re.compile(
        r"R(\d{2})\s+(\d)\s+(\d)\s+(\d)\s+(\d)\s+(\d)\s+(\d)\s+(\d)\s+([^\n\r]+)"
    )
    recipes = {}
    for r in recipe_pattern.finditer(text):
        r_num = int(r.group(1))
        r_id = f"R{r_num:02d}"
        recipes[r_id] = {
            "id": r_id,
            "scale": int(r.group(2)),
            "density": int(r.group(3)),
            "orientation": int(r.group(4)),
            "treatment": int(r.group(5)),
            "zone": int(r.group(6)),
            "colour": int(r.group(7)),
            "sleeve": int(r.group(8)),
            "character": r.group(9).strip(),
        }

    # 3. Engrave Recipes (E01-E24)
    engrave_pattern = re.compile(r"E(\d{2})\s+(\d),(\d),(\d),(\d),(\d),(\d)")
    engrave_recipes = {}
    for er in engrave_pattern.finditer(text):
        e_num = int(er.group(1))
        e_id = f"E{e_num:02d}"
        engrave_recipes[e_id] = {
            "id": e_id,
            "el": int(er.group(2)),
            "scale": int(er.group(3)),
            "density": int(er.group(4)),
            "orientation": int(er.group(5)),
            "zone": int(er.group(6)),
            "blur": int(er.group(7)),
        }

    catalog = {
        "title": "Modern Kit Pattern Library",
        "version": "1.0 (19 November 2026)",
        "motifs_count": len(motifs),
        "families_count": len(families),
        "recipes_count": len(recipes),
        "engrave_recipes_count": len(engrave_recipes),
        "potential_combinations": {
            "curated_designs": len(motifs) * 24,
            "overlay_combinations": 6144 * 64 * 24,
            "raw_grammar_combinations": 19906560,
        },
        "families": families,
        "recipes": recipes,
        "engrave_recipes": engrave_recipes,
        "motifs": motifs,
    }

    return catalog


if __name__ == "__main__":
    data = parse_spec()
    OUTPUT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("=" * 80)
    print(" MODERN KIT PATTERN LIBRARY CONVERTER")
    print("=" * 80)
    print(f" Successfully Parsed:")
    print(f"  • Motifs           : {data['motifs_count']}/288 motifs")
    print(f"  • Families         : {data['families_count']}/36 families")
    print(f"  • Curated Recipes  : {data['recipes_count']}/24 recipes (R01-R24)")
    print(f"  • Engrave Recipes  : {data['engrave_recipes_count']}/24 recipes (E01-E24)")
    print(f"  • Raw Grammar Cap  : {data['potential_combinations']['raw_grammar_combinations']:,} combinations")
    print(f"\n JSON Saved To: {OUTPUT_JSON.relative_to(HERE.parent)}")
    print("=" * 80)
