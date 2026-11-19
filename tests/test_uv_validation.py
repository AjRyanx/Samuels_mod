#!/usr/bin/env python3
"""test_uv_validation.py - Unit tests for Runtime UV validation and collision adjustment."""
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GEN = ROOT / "generator"
if str(GEN) not in sys.path:
    sys.path.insert(0, str(GEN))

import kit_regions

def test_uv_containment_and_adjustment():
    masks = kit_regions.build_masks()
    bf = masks["body_front"]

    # 1. Standard placement should be valid and require 0 adjustments
    sponsor_std = {"cx": 1024, "cy": 1310, "w": 340, "h": 140}
    badge_std = {"cx": 1148, "cy": 1155, "w": 82, "h": 85}
    supplier_std = {"cx": 900, "cy": 1155, "w": 92, "h": 48}

    res = kit_regions.validate_and_adjust_stamps(
        masks, sponsor=sponsor_std, badge=badge_std, supplier=supplier_std
    )
    assert res["valid"] is True
    assert not res["sponsor"]["adjusted"], "Standard sponsor should not require adjustment"
    assert not res["badge"]["adjusted"], "Standard badge should not require adjustment"
    assert not res["supplier"]["adjusted"], "Standard supplier should not require adjustment"
    print("PASS: Standard stamp placement verified (0 adjustments needed).")

    # 2. Collision Test: Sponsor placed too high (e.g. cy=1180, overlapping badge/supplier)
    sponsor_colliding = {"cx": 1024, "cy": 1180, "w": 340, "h": 140}
    res_col = kit_regions.validate_and_adjust_stamps(
        masks, sponsor=sponsor_colliding, badge=badge_std, supplier=supplier_std, min_gap=12
    )
    assert res_col["sponsor"]["adjusted"] is True
    # Verify sponsor was nudged down so sponsor.y >= badge.y + badge.h + min_gap
    badge_bottom = res_col["badge"]["y"] + res_col["badge"]["h"]
    assert res_col["sponsor"]["y"] >= badge_bottom + 12
    print(f"PASS: Collision resolution verified (sponsor nudged down to y={res_col['sponsor']['y']}).")

    # 3. Boundary / Seam Bleed Test: Oversized sponsor extending past side seams
    sponsor_oversized = {"cx": 1024, "cy": 1310, "w": 850, "h": 300}
    res_bleed = kit_regions.validate_and_adjust_stamps(
        masks, sponsor=sponsor_oversized, badge=badge_std, supplier=supplier_std, margin=8
    )
    assert res_bleed["sponsor"]["adjusted"] is True
    sp_adj = res_bleed["sponsor"]
    # Check that adjusted box fits strictly within body_front
    box_inside = kit_regions.check_stamp_containment(
        bf, sp_adj["x"], sp_adj["y"], sp_adj["x"] + sp_adj["w"], sp_adj["y"] + sp_adj["h"], margin=8
    )
    assert box_inside is True
    print(f"PASS: Oversized sponsor scaled down from 850x300 to {sp_adj['w']}x{sp_adj['h']} within body_front.")

    # 4. Badge/Supplier Collision Test: Both abnormally wide, colliding horizontally
    badge_huge = {"cx": 1148, "cy": 1155, "w": 250, "h": 85}
    supplier_huge = {"cx": 900, "cy": 1155, "w": 280, "h": 48}
    res_bs = kit_regions.validate_and_adjust_stamps(
        masks, sponsor=None, badge=badge_huge, supplier=supplier_huge, min_gap=12
    )
    assert res_bs["badge"]["adjusted"] or res_bs["supplier"]["adjusted"]
    # Verify they no longer intersect
    b_box = (res_bs["badge"]["x"], res_bs["badge"]["y"],
             res_bs["badge"]["x"] + res_bs["badge"]["w"], res_bs["badge"]["y"] + res_bs["badge"]["h"])
    s_box = (res_bs["supplier"]["x"], res_bs["supplier"]["y"],
             res_bs["supplier"]["x"] + res_bs["supplier"]["w"], res_bs["supplier"]["y"] + res_bs["supplier"]["h"])
    assert not kit_regions.boxes_intersect(b_box, s_box, margin=12)
    print("PASS: Badge and supplier collision resolved.")

if __name__ == "__main__":
    test_uv_containment_and_adjustment()
    print("ALL UV VALIDATION TESTS PASSED!")
