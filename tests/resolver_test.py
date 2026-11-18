"""Unit tests for club_resolver.py - no game install needed.

Run:  python tests/resolver_test.py
"""
import sys, tempfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "generator"))
import club_resolver as cr

# ---- colour normalisation ---------------------------------------------------
assert cr._norm_hex("#034694") == "#034694"
assert cr._norm_hex("034694") == "#034694"
assert cr._norm_hex("#034694FF") == "#034694"
assert cr._norm_hex("0x034694") == "#034694"
assert cr._norm_hex(0x034694) == "#034694"
assert cr._norm_hex("nope") is None
assert cr._norm_hex(None) is None

# ---- deterministic fallback -------------------------------------------------
missing = "C:/does/not/exist"
a = cr.resolve(4242, missing)
b = cr.resolve(4242, missing)
assert a == b, "resolve must be deterministic"
assert (a["primary"], a["secondary"], a["accent"]) in cr.FALLBACK_PALETTES
assert a["tier"] in ("small", "mid", "big")

# every fallback club must get three visibly different colours
for cid in range(1, 400):
    row = cr.resolve(cid, missing)
    p, s, ac = (cr._hexc(row[k]) for k in ("primary", "secondary", "accent"))
    assert cr.color_dist(p, s) > 0.05, (cid, row)
    assert cr.color_dist(p, ac) > 0.05, (cid, row)

# the tier roll must match the Lua synth (hash('tier:<id>') % 3)
assert cr.tier_from_id(102) == "small"
assert cr.tier_from_id(71579) == "big"

# ---- a fake sider tree ------------------------------------------------------
sider = Path(tempfile.mkdtemp())
cg = sider / "content" / "KitGenerator"; cg.mkdir(parents=True)
kits = sider / "content" / "kits"
(kits / "England" / "Testville" / "p1").mkdir(parents=True)
(kits / "map.txt").write_text(
    "# header\n"
    '777, "England\\Testville"\n'
    '#888, "Nope\\Off"\n', encoding="utf-8")
(kits / "England" / "Testville" / "p1" / "config.txt").write_text(
    "ShirtColor1=#FF0000\nShortsColor=#00FF00\n", encoding="utf-8")
assert 888 not in cr.read_map(sider), "commented map lines must be ignored"

# the live club.txt (written by the Lua mod) wins over config.txt
(cg / "club.txt").write_text(
    "# managed club\n777|Testville|#112233|#FFFFFF|#112233|#FFFFFF|#112233|#EE0000\n",
    encoding="utf-8")
row = cr.resolve(777, sider)
assert row["name"] == "Testville", row
assert row["primary"] == "#112233", row        # live game colour beats config
assert row["accent"] == "#EE0000", row

# no name in club.txt -> the map folder supplies it
(cg / "club.txt").write_text("777||#112233|||||\n", encoding="utf-8")
row = cr.resolve(777, sider)
assert row["name"] == "Testville", row
assert row["primary"] == "#112233"
assert row["secondary"] == "#00FF00", row      # filled in from config.txt

# a club.txt for a DIFFERENT club must not leak its colours
(cg / "club.txt").write_text("999|Other|#ABCDEF|||||\n", encoding="utf-8")
row = cr.resolve(777, sider)
assert row["primary"] == "#FF0000", row        # falls back to config.txt

# a csv row short-circuits everything
row = cr.resolve(102, sider, csv_row={"name": "Chelsea", "primary": "#034694",
                                      "secondary": "#FFFFFF", "accent": "#C8A84B",
                                      "tier": "mid"})
assert row["name"] == "Chelsea" and row["primary"] == "#034694" and row["tier"] == "mid"

print("RESOLVER OK")
