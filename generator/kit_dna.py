#!/usr/bin/env python3
"""kit_dna.py - 2026 Modern Football Kit DNA & Fashion Styling Engine.

Bridges real-world club heritage, iconic tailoring constraints (e.g. Arsenal's
white sleeves, Ajax's red center, Milan's Rossoneri stripes, Celtic's hoops),
and 2026 fashion-forward streetwear aesthetics (Carrara marble tonal jacquards,
houndstooth luxury, liquid chrome, topographic elevation, noir blackout third kits).

Key Capabilities:
-----------------
1. BESPOKE_DNA: Curated styling profiles for iconic world football clubs.
2. infer_dna: Intelligent classification for all 580+ teams in the game
   (Striped, Hooped, Sash, Split-Sleeve, Luxury Solid).
3. get_club_style: Returns the slot (1/2/3) configuration for any club, season,
   and sponsor deal, pulling from the 205-pattern modern taxonomy.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

# Helper to parse hex
def _hexc(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in range(0, 6, 2))


def _lum(c: Tuple[int, int, int]) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _shift(c: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    return tuple(max(0, min(255, int(v * factor))) for v in c)


def _dist(c1: Tuple[int, int, int], c2: Tuple[int, int, int]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1[:3], c2[:3])))


def _sponsor_hash(s: Optional[str]) -> int:
    """Deterministic hash of sponsor string independent of Python's siphash randomization."""
    if not s:
        return 0
    return sum((i + 1) * ord(c) for i, c in enumerate(s))


def _club_seed(cid: int, slot: int | str, season: int, sponsor: Optional[str] = None) -> int:
    """32-bit Murmur-style avalanche hash providing high entropy across clubs, slots, seasons, and sponsors."""
    s_off = season - 2026
    slot_code = 1 if slot in (1, "p1") else (2 if slot in (2, "p2") else (3 if slot in (3, "p3") else (4 if slot == "g1" else 5)))
    sp_val = _sponsor_hash(sponsor) if sponsor else 0
    h = (cid * 0x9E3779B1) ^ (slot_code * 0x85EBCA6B) ^ (s_off * 0xC2B2AE35) ^ (sp_val * 0x1B873593)
    h = ((h ^ (h >> 16)) * 0x45D9F3B) & 0x7FFFFFFF
    h = ((h ^ (h >> 16)) * 0x45D9F3B) & 0x7FFFFFFF
    h = (h ^ (h >> 16)) & 0x7FFFFFFF
    return h

# Keyed by team_id (PES 2021 / Football Life IDs).
# Slot 1 = Home, Slot 2 = Away, Slot 3 = Third.
BESPOKE_DNA: Dict[int, Dict[int, Dict[str, Any]]] = {
    # Manchester United
    100: {
        1: {  # Home: Iconic Manchester Red, white shorts, black socks, red/black collar trim
            "body": (195, 20, 30), "second": (250, 250, 250), "third": (20, 20, 25),
            "patterns": ["141-E", "095-E", "153-E"],
            "sleeve": (195, 20, 30), "shorts": (250, 250, 250),
            "socks": (20, 20, 25), "collar": (20, 20, 25), "cuff": (250, 250, 250),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: Iconic European Navy Blue heritage (1968/1993/2024) - clean, NO stripes
            "body": (28, 55, 115), "second": (250, 250, 250), "third": (195, 20, 30),
            "patterns": ["088", "166-B"],
            "sleeve": (28, 55, 115), "shorts": (250, 250, 250),
            "socks": (28, 55, 115), "collar": (250, 250, 250), "cuff": (195, 20, 30),
            "gradient": 0, "supplier": "adidas",
        },
        3: {  # Third: Noir Luxury - matte black/charcoal with iridescent gold & crimson accents
            "body": (22, 24, 28), "second": (212, 175, 55), "third": (195, 20, 30),
            "patterns": ["219-B", "219-E"],
            "sleeve": (22, 24, 28), "shorts": (22, 24, 28),
            "socks": (22, 24, 28), "collar": (212, 175, 55), "cuff": (212, 175, 55),
            "gradient": 1, "supplier": "adidas",
        },
    },

    # Arsenal
    101: {
        1: {  # Home: Canonical deep red body with crisp pure white sleeves + collar
            "body": (190, 22, 34), "second": (250, 250, 252), "third": (15, 32, 67),
            "patterns": ["090-E", "170-E", "046-E"],
            "sleeve": (250, 250, 252), "shorts": (250, 250, 252),
            "socks": (250, 250, 252), "collar": (250, 250, 252),
            "cuff": (190, 22, 34),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: London Underground / Soundwave streetwear - blackout with electric volt
            "body": (18, 20, 22), "second": (205, 255, 0), "third": (30, 80, 180),
            "patterns": ["217-B", "085-E"],
            "sleeve": (18, 20, 22), "shorts": (18, 20, 22),
            "socks": (205, 255, 0), "collar": (205, 255, 0),
            "gradient": 1, "supplier": "adidas",
        },
        3: {  # Third: Modern high-fashion pastel lilac / sand couture
            "body": (215, 210, 230), "second": (15, 32, 67), "third": (190, 22, 34),
            "patterns": ["168-E", "220-B"],
            "sleeve": (215, 210, 230), "shorts": (15, 32, 67),
            "socks": (215, 210, 230), "collar": (15, 32, 67),
            "gradient": 0, "supplier": "adidas",
        },
    },

    # Chelsea
    102: {
        1: {  # Home: Iconic Chelsea Royal Blue body & sleeves, blue/white shorts/socks, white/gold trim (strictly NO red, NO white sleeves, NO stripes)
            "body": (3, 70, 155), "second": (250, 250, 252), "third": (212, 175, 55),
            "patterns": ["168-E", "042-E", "153-E"],
            "sleeve": (3, 70, 155), "shorts": (3, 70, 155),
            "socks": (250, 250, 252), "collar": (3, 70, 155),
            "cuff": (250, 250, 252),
            "gradient": 0, "supplier": "nike",
        },
        2: {  # Away: Iconic Chelsea Canary Yellow heritage with royal blue trim (strictly NO stripes)
            "body": (252, 222, 0), "second": (3, 70, 155), "third": (18, 20, 24),
            "patterns": ["097", "083-C"],
            "sleeve": (252, 222, 0), "shorts": (3, 70, 155),
            "socks": (252, 222, 0), "collar": (3, 70, 155),
            "cuff": (3, 70, 155),
            "gradient": 0, "supplier": "nike",
        },
        3: {  # Third: Noir Luxury / Ice Mint couture with royal blue and liquid chrome
            "body": (20, 24, 32), "second": (30, 185, 170), "third": (3, 70, 155),
            "patterns": ["216-B", "220-E"],
            "sleeve": (20, 24, 32), "shorts": (20, 24, 32),
            "socks": (20, 24, 32), "collar": (30, 185, 170),
            "cuff": (30, 185, 170),
            "gradient": 1, "supplier": "nike",
        },
    },

    # Liverpool
    103: {
        1: {  # Home: Iconic all-red crimson with pure white/gold accents, tonal luxury jacquard
            "body": (190, 18, 30), "second": (250, 250, 252), "third": (212, 175, 55),
            "patterns": ["145-E", "177-E", "067-E"],
            "sleeve": (190, 18, 30), "shorts": (190, 18, 30),
            "socks": (190, 18, 30), "collar": (190, 18, 30),
            "cuff": (250, 250, 252),
            "gradient": 0, "supplier": "nike",
        },
        2: {  # Away: Heritage off-white & forest green / teal accents
            "body": (245, 245, 242), "second": (15, 65, 45), "third": (20, 20, 25),
            "patterns": ["093", "088"],
            "sleeve": (245, 245, 242), "shorts": (15, 65, 45),
            "socks": (245, 245, 242), "collar": (15, 65, 45),
            "cuff": (15, 65, 45),
            "gradient": 0, "supplier": "nike",
        },
        3: {  # Third: Noir Luxury / Royal Purple couture with iridescent gold
            "body": (32, 22, 42), "second": (212, 175, 55), "third": (190, 18, 30),
            "patterns": ["216", "185-E"],
            "sleeve": (32, 22, 42), "shorts": (32, 22, 42),
            "socks": (32, 22, 42), "collar": (212, 175, 55),
            "cuff": (212, 175, 55),
            "gradient": 1, "supplier": "nike",
        },
    },

    # Manchester City
    173: {
        1: {  # Home: Sky blue body with white shorts, stadium roof truss micro-jacquard
            "body": (108, 171, 221), "second": (250, 250, 250), "third": (15, 30, 60),
            "patterns": ["167-E", "126-E"],
            "sleeve": (108, 171, 221), "shorts": (250, 250, 250),
            "socks": (108, 171, 221), "collar": (250, 250, 250),
            "cuff": (250, 250, 250),
            "gradient": 0, "supplier": "puma",
            "sponsor_dark": (15, 30, 60),
        },
        2: {  # Away: Dark charcoal with neon yellow-green cyber accents
            "body": (25, 28, 35), "second": (215, 255, 0), "third": (108, 171, 221),
            "patterns": ["083-C", "003-B"],
            "sleeve": (25, 28, 35), "shorts": (25, 28, 35),
            "socks": (215, 255, 0), "collar": (215, 255, 0),
            "gradient": 1, "supplier": "puma",
        },
        3: {  # Third: Electric gradient / street art urban architecture
            "body": (18, 35, 65), "second": (255, 100, 180), "third": (0, 230, 215),
            "patterns": ["042", "212"],
            "sleeve": (18, 35, 65), "shorts": (18, 35, 65),
            "socks": (255, 100, 180), "collar": (0, 230, 215),
            "gradient": 1, "supplier": "puma",
        },
    },

    # Aston Villa
    107: {
        1: {  # Home: Canonical claret body with sky blue sleeves (strictly preserved!)
            "body": (120, 24, 52), "second": (149, 191, 229), "third": (245, 245, 245),
            "patterns": ["081-C", "046-E"],
            "sleeve": (149, 191, 229), "shorts": (245, 245, 245),
            "socks": (149, 191, 229), "collar": (149, 191, 229),
            "cuff": (120, 24, 52),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: Clean white with claret micro-stripes
            "body": (248, 248, 250), "second": (120, 24, 52), "third": (149, 191, 229),
            "patterns": ["085", "219"],
            "sleeve": (248, 248, 250), "shorts": (120, 24, 52),
            "socks": (248, 248, 250), "collar": (120, 24, 52),
            "gradient": 0, "supplier": "adidas",
        },
        3: {  # Third: Navy & gold streetwear
            "body": (18, 28, 48), "second": (210, 175, 75), "third": (149, 191, 229),
            "patterns": ["041-E", "006-E"],
            "sleeve": (18, 28, 48), "shorts": (18, 28, 48),
            "socks": (210, 175, 75), "collar": (210, 175, 75),
            "gradient": 0, "supplier": "adidas",
        },
    },

    # Tottenham Hotspur
    179: {
        1: {  # Home: Lilywhite body & sleeves with midnight navy shorts and socks
            "body": (252, 252, 254), "second": (19, 34, 64), "third": (252, 252, 254),
            "patterns": ["085-E", "090-E", "171-E", "046-E"],
            "sleeve": (252, 252, 254), "shorts": (19, 34, 64),
            "socks": (252, 252, 254), "collar": (19, 34, 64),
            "collar_tip": (252, 252, 254),
            "cuff": (19, 34, 64),
            "cuff_tip": (252, 252, 254),
            "stripe_accent": (19, 34, 64),
            "gradient": 0, "supplier": "nike",
            "sponsor_dark": (19, 34, 64),
        },
        2: {  # Away: Marine navy / iridescent purple streetwear
            "body": (22, 28, 60), "second": (130, 160, 220), "third": (250, 250, 252),
            "patterns": ["220-E", "167-B"],
            "sleeve": (22, 28, 60), "shorts": (22, 28, 60),
            "socks": (22, 28, 60), "collar": (130, 160, 220),
            "gradient": 0, "supplier": "nike",
        },
        3: {  # Third: High-fashion mint / aqua couture with navy trim
            "body": (140, 220, 200), "second": (19, 34, 64), "third": (250, 250, 252),
            "patterns": ["218-B", "029-E"],
            "sleeve": (140, 220, 200), "shorts": (19, 34, 64),
            "socks": (140, 220, 200), "collar": (19, 34, 64),
            "gradient": 1, "supplier": "nike",
        },
    },

    # Crystal Palace
    382: {
        1: {  # Home: Iconic Selhurst Red & Blue vertical stripes with gold eagle trim
            "body": (27, 69, 143), "second": (196, 18, 46), "third": (255, 204, 0),
            "patterns": ["093", "081"],
            "sleeve": (27, 69, 143), "shorts": (27, 69, 143),
            "socks": (27, 69, 143), "collar": (255, 204, 0),
            "cuff": (196, 18, 46),
            "gradient": 0, "supplier": "macron",
        },
        2: {  # Away: Pristine Eagle White with dual red & blue sash
            "body": (250, 250, 252), "second": (27, 69, 143), "third": (196, 18, 46),
            "patterns": ["087", "036"],
            "sleeve": (250, 250, 252), "shorts": (27, 69, 143),
            "socks": (250, 250, 252), "collar": (27, 69, 143),
            "cuff": (196, 18, 46),
            "gradient": 0, "supplier": "macron",
        },
        3: {  # Third: South London Gold / Electric Volt Streetwear
            "body": (245, 200, 30), "second": (27, 69, 143), "third": (196, 18, 46),
            "patterns": ["067-E", "052"],
            "sleeve": (245, 200, 30), "shorts": (27, 69, 143),
            "socks": (245, 200, 30), "collar": (27, 69, 143),
            "cuff": (27, 69, 143),
            "gradient": 0, "supplier": "macron",
        },
    },

    # Newcastle United
    106: {
        1: {  # Home: Iconic black & white vertical stripes with black shorts
            "body": (20, 20, 24), "second": (250, 250, 252), "third": (180, 215, 245),
            "patterns": ["083", "081-E"],
            "sleeve": (20, 20, 24), "shorts": (20, 20, 24),
            "socks": (20, 20, 24), "collar": (250, 250, 252),
            "cuff": (250, 250, 252),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: Heritage claret & navy hoops with gold accents
            "body": (90, 20, 35), "second": (15, 30, 60), "third": (210, 175, 75),
            "patterns": ["084", "091"],
            "sleeve": (90, 20, 35), "shorts": (15, 30, 60),
            "socks": (90, 20, 35), "collar": (15, 30, 60),
            "gradient": 0, "supplier": "adidas",
        },
        3: {  # Third: Minimalist sand / forest green luxury
            "body": (246, 244, 235), "second": (15, 115, 75), "third": (20, 20, 24),
            "patterns": ["215", "218"],
            "sleeve": (246, 244, 235), "shorts": (246, 244, 235),
            "socks": (246, 244, 235), "collar": (15, 115, 75),
            "gradient": 0, "supplier": "adidas",
        },
    },

    # Real Madrid
    109: {
        1: {  # Home: Pristine Royal White with majestic Gold, Castilian Violet & Midnight Navy rotations
            "body": (252, 252, 254), "second": (212, 175, 55), "third": (15, 25, 55),
            "patterns": ["171-E", "170-E", "085-E", "219-E", "046-E"],
            "sleeve": (252, 252, 254), "shorts": (252, 252, 254),
            "socks": (252, 252, 254), "collar": (252, 252, 254),
            "collar_tip": (212, 175, 55),
            "cuff": (212, 175, 55),
            "cuff_tip": (15, 25, 55),
            "stripe_accent": (212, 175, 55),
            "supplier_color": (212, 175, 55),
            "gradient": 0, "supplier": "adidas",
            "sponsor_dark": (15, 25, 55),
        },
        2: {  # Away: Royal Castilian Violet / Deep Purple with metallic gold & white accents
            "body": (65, 25, 115), "second": (252, 252, 254), "third": (212, 175, 55),
            "patterns": ["085-E", "185-E", "040-C", "067-E"],
            "sleeve": (65, 25, 115), "shorts": (65, 25, 115),
            "socks": (65, 25, 115), "collar": (252, 252, 254),
            "collar_tip": (212, 175, 55),
            "cuff": (212, 175, 55),
            "cuff_tip": (252, 252, 254),
            "stripe_accent": (212, 175, 55),
            "supplier_color": (212, 175, 55),
            "gradient": 0, "supplier": "adidas",
        },
        3: {  # Third: Haute Couture Carbon Noir - matte black with liquid gold heraldry
            "body": (20, 22, 26), "second": (212, 175, 55), "third": (252, 252, 254),
            "patterns": ["141-E", "170-E", "216-B", "220-B"],
            "sleeve": (20, 22, 26), "shorts": (20, 22, 26),
            "socks": (20, 22, 26), "collar": (212, 175, 55),
            "collar_tip": (252, 252, 254),
            "cuff": (212, 175, 55),
            "cuff_tip": (252, 252, 254),
            "stripe_accent": (212, 175, 55),
            "supplier_color": (212, 175, 55),
            "gradient": 1, "supplier": "adidas",
        },
    },

    # Barcelona
    108: {
        1: {  # Home: Iconic Blaugrana vertical stripes with Catalan micro-weave
            "body": (155, 15, 45), "second": (0, 75, 140), "third": (245, 195, 0),
            "patterns": ["stripes", "081", "088", "093", "083", "097", "118"],
            "sleeve": (0, 75, 140), "shorts": (0, 75, 140),
            "socks": (155, 15, 45), "collar": (245, 195, 0),
            "collar_style": "crew",
            "cuff": (245, 195, 0),
            "gradient": 0, "supplier": "nike",
        },
        2: {  # Away: Iconic Catalan Gold / Volt Senyera graphic
            "body": (245, 200, 30), "second": (155, 15, 45), "third": (0, 75, 140),
            "patterns": ["005", "022", "087", "095"],
            "sleeve": (245, 200, 30), "shorts": (0, 75, 140),
            "socks": (245, 200, 30), "collar": (155, 15, 45),
            "collar_style": "polo",
            "gradient": 0, "supplier": "nike",
        },
        3: {  # Third: High-fashion Mediterranean mint / aqua streetwear
            "body": (130, 225, 205), "second": (0, 75, 140), "third": (155, 15, 45),
            "patterns": ["041-E", "067-E", "220-E", "046-B", "171-E"],
            "sleeve": (130, 225, 205), "shorts": (0, 75, 140),
            "socks": (130, 225, 205), "collar": (0, 75, 140),
            "collar_style": "v_neck",
            "gradient": 0, "supplier": "nike",
        },
    },

    # Atletico Madrid
    172: {
        1: {  # Home: Iconic red & white vertical stripes with royal blue shorts
            "body": (205, 25, 35), "second": (250, 250, 250), "third": (15, 40, 100),
            "patterns": ["stripes", "081", "088", "093", "097", "118"],
            "sleeve": (205, 25, 35), "shorts": (15, 40, 100),
            "socks": (205, 25, 35), "collar": (15, 40, 100),
            "collar_style": "v_neck",
            "cuff": (15, 40, 100),
            "gradient": 0, "supplier": "nike",
        },
        2: {  # Away: Deep navy with neon turquoise / infrared trim
            "body": (15, 25, 55), "second": (0, 225, 210), "third": (205, 25, 35),
            "patterns": ["185-E", "171-E", "020", "041-E", "214"],
            "sleeve": (15, 25, 55), "shorts": (15, 25, 55),
            "socks": (0, 225, 210), "collar": (0, 225, 210),
            "collar_style": "crew",
            "gradient": 1, "supplier": "nike",
        },
        3: {  # Third: Vibrant volt & camouflage streetwear
            "body": (210, 245, 45), "second": (15, 25, 55), "third": (205, 25, 35),
            "patterns": ["004", "171-E", "008", "024"],
            "sleeve": (210, 245, 45), "shorts": (15, 25, 55),
            "socks": (210, 245, 45), "collar": (15, 25, 55),
            "gradient": 0, "supplier": "nike",
        },
    },

    # Juventus
    120: {
        1: {  # Home: Iconic black & white vertical stripes (brushstroke / modern zebra)
            "body": (20, 20, 22), "second": (250, 250, 252), "third": (210, 175, 75),
            "patterns": ["083", "081-E"],
            "sleeve": (20, 20, 22), "shorts": (250, 250, 252),
            "socks": (250, 250, 252), "collar": (210, 175, 75),
            "cuff": (210, 175, 75),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: Soft luxury pastel pink / cream with charcoal trim
            "body": (245, 205, 215), "second": (20, 20, 22), "third": (250, 250, 252),
            "patterns": ["041-E", "171-E"],
            "sleeve": (245, 205, 215), "shorts": (20, 20, 22),
            "socks": (245, 205, 215), "collar": (20, 20, 22),
            "gradient": 0, "supplier": "adidas",
        },
        3: {  # Third: Futuristic all-black with electric neon volt
            "body": (15, 16, 18), "second": (215, 255, 20), "third": (250, 250, 252),
            "patterns": ["042", "141-E"],
            "sleeve": (15, 16, 18), "shorts": (15, 16, 18),
            "socks": (215, 255, 20), "collar": (215, 255, 20),
            "gradient": 1, "supplier": "adidas",
        },
    },

    # AC Milan
    121: {
        1: {  # Home: Rossoneri vertical red & black stripes with black shorts
            "body": (195, 20, 30), "second": (18, 18, 20), "third": (245, 245, 245),
            "patterns": ["081", "088"],
            "sleeve": (18, 18, 20), "shorts": (18, 18, 20),
            "socks": (18, 18, 20), "collar": (195, 20, 30),
            "cuff": (195, 20, 30),
            "gradient": 0, "supplier": "puma",
        },
        2: {  # Away: Crisp pure white with dual red/black trim
            "body": (250, 250, 252), "second": (195, 20, 30), "third": (18, 18, 20),
            "patterns": ["085", "083-C"],
            "sleeve": (250, 250, 252), "shorts": (250, 250, 252),
            "socks": (250, 250, 252), "collar": (195, 20, 30),
            "gradient": 0, "supplier": "puma",
        },
        3: {  # Third: Milan Fashion Week streetwear - olive green / sand camouflage
            "body": (75, 85, 65), "second": (215, 185, 120), "third": (195, 20, 30),
            "patterns": ["185-E", "020-B"],
            "sleeve": (75, 85, 65), "shorts": (75, 85, 65),
            "socks": (215, 185, 120), "collar": (215, 185, 120),
            "gradient": 1, "supplier": "puma",
        },
    },

    # Inter Milan
    119: {
        1: {  # Home: Nerazzurri royal blue & black stripes with Biscione scale texture
            "body": (10, 50, 145), "second": (16, 18, 22), "third": (210, 175, 65),
            "patterns": ["093", "097"],
            "sleeve": (16, 18, 22), "shorts": (16, 18, 22),
            "socks": (10, 50, 145), "collar": (10, 50, 145),
            "cuff": (210, 175, 65),
            "gradient": 0, "supplier": "nike",
        },
        2: {  # Away: Pure white with undulating Biscione serpent wave graphic
            "body": (250, 250, 252), "second": (10, 50, 145), "third": (16, 18, 22),
            "patterns": ["043-B", "046-B"],
            "sleeve": (250, 250, 252), "shorts": (250, 250, 252),
            "socks": (250, 250, 252), "collar": (10, 50, 145),
            "gradient": 0, "supplier": "nike",
        },
        3: {  # Third: High-fashion safety orange / cyber yellow
            "body": (245, 110, 20), "second": (10, 50, 145), "third": (16, 18, 22),
            "patterns": ["168-E", "004"],
            "sleeve": (245, 110, 20), "shorts": (16, 18, 22),
            "socks": (245, 110, 20), "collar": (10, 50, 145),
            "gradient": 1, "supplier": "nike",
            "sponsor_dark": (16, 18, 22),
        },
    },

    # AS Roma
    125: {
        1: {  # Home: Imperial Giallorossi carmine & warm amber/gold, Lupetto micro-jacquard
            "body": (145, 20, 35), "second": (245, 175, 20), "third": (250, 250, 252),
            "patterns": ["170-E", "041-E"],
            "sleeve": (145, 20, 35), "shorts": (245, 175, 20),
            "socks": (145, 20, 35), "collar": (245, 175, 20),
            "cuff": (245, 175, 20),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: Roman marble white with subtle carmine/gold filigree
            "body": (248, 246, 242), "second": (145, 20, 35), "third": (245, 175, 20),
            "patterns": ["214-E", "067-E"],
            "sleeve": (248, 246, 242), "shorts": (145, 20, 35),
            "socks": (248, 246, 242), "collar": (145, 20, 35),
            "gradient": 0, "supplier": "adidas",
        },
        3: {  # Third: Blackout with vibrant neon infrared accents
            "body": (18, 18, 20), "second": (245, 175, 20), "third": (145, 20, 35),
            "patterns": ["215-E", "003-B"],
            "sleeve": (18, 18, 20), "shorts": (18, 18, 20),
            "socks": (245, 175, 20), "collar": (245, 175, 20),
            "gradient": 1, "supplier": "adidas",
        },
    },

    # Bayern Munich
    127: {
        1: {  # Home: Rot-Weiß crimson red with Bavarian diamond micro-jacquard
            "body": (210, 15, 35), "second": (250, 250, 252), "third": (15, 25, 55),
            "patterns": ["027-E", "033-E"],
            "sleeve": (210, 15, 35), "shorts": (210, 15, 35),
            "socks": (210, 15, 35), "collar": (250, 250, 252),
            "cuff": (250, 250, 252),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: World map / digital geometric in deep black & ultraviolet
            "body": (18, 18, 24), "second": (160, 60, 230), "third": (0, 220, 200),
            "patterns": ["004", "219-E"],
            "sleeve": (18, 18, 24), "shorts": (18, 18, 24),
            "socks": (160, 60, 230), "collar": (160, 60, 230),
            "gradient": 1, "supplier": "adidas",
        },
        3: {  # Third: Off-white / cream heritage luxury with burgundy/gold trim
            "body": (246, 244, 238), "second": (130, 20, 35), "third": (205, 168, 75),
            "patterns": ["041-E", "168-E"],
            "sleeve": (246, 244, 238), "shorts": (130, 20, 35),
            "socks": (246, 244, 238), "collar": (130, 20, 35),
            "gradient": 0, "supplier": "adidas",
        },
    },

    # Borussia Dortmund
    126: {
        1: {  # Home: Cyber yellow with Signal Iduna Park roof truss geometry
            "body": (250, 220, 0), "second": (18, 18, 20), "third": (250, 250, 250),
            "patterns": ["plain", "167-E", "041-E", "067-E", "185-E"],
            "sleeve": (250, 220, 0), "shorts": (18, 18, 20),
            "socks": (250, 220, 0), "collar": (18, 18, 20),
            "cuff": (18, 18, 20),
            "gradient": 0, "supplier": "puma",
            "sponsor_dark": (18, 18, 20),
        },
        2: {  # Away: Blackout coal & steel aesthetic
            "body": (22, 22, 24), "second": (250, 220, 0), "third": (80, 85, 95),
            "patterns": ["041-E", "220-E", "166-B", "171-E"],
            "sleeve": (22, 22, 24), "shorts": (22, 22, 24),
            "socks": (250, 220, 0), "collar": (250, 220, 0),
            "gradient": 1, "supplier": "puma",
        },
        3: {  # Third: Retro white & neon yellow cup kit
            "body": (250, 250, 252), "second": (250, 220, 0), "third": (18, 18, 20),
            "patterns": ["083", "085", "003-B", "024"],
            "sleeve": (250, 250, 252), "shorts": (18, 18, 20),
            "socks": (250, 250, 252), "collar": (18, 18, 20),
            "gradient": 0, "supplier": "puma",
        },
    },

    # Bayer Leverkusen
    128: {
        1: {  # Home: Deep charcoal/black with red cross accents
            "body": (25, 25, 28), "second": (214, 0, 33), "third": (250, 250, 252),
            "patterns": ["plain", "041-E", "067-E", "171-E"],
            "sleeve": (25, 25, 28), "shorts": (25, 25, 28),
            "socks": (25, 25, 28), "collar": (214, 0, 33),
            "cuff": (214, 0, 33),
            "gradient": 0, "supplier": "puma",
        },
        2: {  # Away: Pure white with red/black diagonal accents
            "body": (250, 250, 252), "second": (214, 0, 33), "third": (25, 25, 28),
            "patterns": ["005", "022", "095"],
            "sleeve": (250, 250, 252), "shorts": (250, 250, 252),
            "socks": (250, 250, 252), "collar": (214, 0, 33),
            "gradient": 0, "supplier": "puma",
        },
        3: {  # Third: Cyan / electric blue
            "body": (20, 95, 160), "second": (250, 250, 252), "third": (25, 25, 28),
            "patterns": ["042", "029-E", "126-B"],
            "sleeve": (20, 95, 160), "shorts": (20, 95, 160),
            "socks": (20, 95, 160), "collar": (250, 250, 252),
            "gradient": 1, "supplier": "puma",
        },
    },

    # PSG (Paris Saint-Germain)
    114: {
        1: {  # Home: Multi-Year Identity Evolution (Daniel Hechter -> Asymmetric -> Fine Pinstripes -> Clean Tonal Luxury)
            "body": (15, 25, 55), "second": (210, 20, 35), "third": (250, 250, 252),
            "patterns": ["206", "207", "208", "209"],  # Classic & Modern Daniel Hechter variations
            "sleeve": (15, 25, 55), "shorts": (15, 25, 55),
            "socks": (15, 25, 55), "collar": (15, 25, 55),
            "cuff": (210, 20, 35),
            "alt_shorts": [(15, 25, 55), (250, 250, 252), (15, 25, 55), (250, 250, 252)],  # Navy vs Classic 1990s White shorts alternating
            "alt_socks": [(15, 25, 55), (15, 25, 55), (210, 20, 35), (15, 25, 55)],
            "gradient": 0, "supplier": "nike",
        },
        2: {  # Away: 4 Completely Distinct Fashion & Heritage Colorways (Zero Center-Stripe Clones)
            "palettes": [
                {  # Palette 0: Parisian Pure White Hechter
                    "body": (250, 250, 252), "second": (15, 25, 55), "third": (210, 20, 35),
                    "patterns": ["206", "207", "208", "209"],
                    "sleeve": (250, 250, 252), "shorts": (250, 250, 252),
                    "socks": (250, 250, 252), "collar": (15, 25, 55), "cuff": (210, 20, 35),
                    "gradient": 0, "supplier": "nike",
                },
                {  # Palette 1: Brazilian Canary Yellow (PSG Club Heritage Gold)
                    "body": (248, 215, 30), "second": (15, 25, 55), "third": (250, 250, 252),
                    "patterns": ["208", "168-E", "219-E", "180"],
                    "sleeve": (248, 215, 30), "shorts": (15, 25, 55),
                    "socks": (248, 215, 30), "collar": (15, 25, 55), "cuff": (15, 25, 55),
                    "gradient": 0, "supplier": "nike",
                },
                {  # Palette 2: Jordan Desert Sand / Warm Champagne Haute Couture
                    "body": (235, 228, 215), "second": (15, 25, 55), "third": (210, 175, 75),
                    "patterns": ["145-E", "170-E", "020", "220-B"],
                    "sleeve": (235, 228, 215), "shorts": (235, 228, 215),
                    "socks": (235, 228, 215), "collar": (15, 25, 55), "cuff": (210, 175, 75),
                    "gradient": 0, "supplier": "nike",
                },
                {  # Palette 3: French University Crimson (Solid Tonal with Navy Raglan Sleeves, NO center stripe)
                    "body": (195, 20, 35), "second": (15, 25, 55), "third": (250, 250, 252),
                    "patterns": ["088", "153-E", "168-E", "216-B"],
                    "sleeve": (15, 25, 55), "shorts": (15, 25, 55),
                    "socks": (195, 20, 35), "collar": (15, 25, 55), "cuff": (250, 250, 252),
                    "gradient": 0, "supplier": "nike",
                },
            ],
        },
        3: {  # Third: Jordan Collection Multi-Year Streetwear Rotations
            "palettes": [
                {  # Palette 0: Jordan Paris Nocturne (Obsidian & Metallic Gold)
                    "body": (18, 20, 26), "second": (220, 180, 70), "third": (215, 30, 45),
                    "patterns": ["090", "124", "110", "042"],
                    "sleeve": (18, 20, 26), "shorts": (18, 20, 26),
                    "socks": (18, 20, 26), "collar": (18, 20, 26), "cuff": (220, 180, 70),
                    "gradient": 0, "supplier": "nike",
                },
                {  # Palette 1: Jordan Bordeaux Wine / Haute Couture
                    "body": (75, 20, 42), "second": (220, 180, 70), "third": (250, 250, 252),
                    "patterns": ["079-E", "126-B", "218-B", "216-B"],
                    "sleeve": (75, 20, 42), "shorts": (75, 20, 42),
                    "socks": (75, 20, 42), "collar": (220, 180, 70), "cuff": (220, 180, 70),
                    "gradient": 0, "supplier": "nike",
                },
                {  # Palette 2: Jordan Arctic Platinum / Light Bone
                    "body": (232, 236, 242), "second": (18, 20, 26), "third": (215, 30, 45),
                    "patterns": ["041-E", "168-B", "219-B", "215-E"],
                    "sleeve": (232, 236, 242), "shorts": (18, 20, 26),
                    "socks": (232, 236, 242), "collar": (18, 20, 26), "cuff": (215, 30, 45),
                    "gradient": 0, "supplier": "nike",
                },
                {  # Palette 3: Jordan Infrared 23 Streetwear
                    "body": (205, 20, 50), "second": (18, 20, 26), "third": (250, 250, 252),
                    "patterns": ["126-B", "204-B", "003-B", "216-B"],
                    "sleeve": (18, 20, 26), "shorts": (18, 20, 26),
                    "socks": (205, 20, 50), "collar": (18, 20, 26), "cuff": (18, 20, 26),
                    "gradient": 0, "supplier": "nike",
                },
            ],
        },
    },

    # Ajax
    116: {
        1: {  # Home: Sacred wide central red panel with pure white body and sleeves
            "body": (250, 250, 252), "second": (210, 20, 35), "third": (250, 250, 252),
            "patterns": ["101", "086", "094"],
            "sleeve": (250, 250, 252), "shorts": (250, 250, 252),
            "socks": (250, 250, 252), "collar": (210, 20, 35),
            "cuff": (210, 20, 35),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: Amsterdam canal / Saint Andrew cross geometric streetwear
            "body": (22, 28, 42), "second": (100, 215, 210), "third": (210, 20, 35),
            "patterns": ["041-E", "027-B", "033", "041-E", "131"],
            "sleeve": (22, 28, 42), "shorts": (22, 28, 42),
            "socks": (100, 215, 210), "collar": (100, 215, 210),
            "gradient": 1, "supplier": "adidas",
        },
        3: {  # Third: Bob Marley reggae tribute / Amsterdam street culture
            "body": (18, 18, 20), "second": (245, 205, 30), "third": (20, 160, 60),
            "patterns": ["083", "085", "005-B", "041-E", "171-E"],
            "sleeve": (18, 18, 20), "shorts": (18, 18, 20),
            "socks": (245, 205, 30), "collar": (20, 160, 60),
            "gradient": 0, "supplier": "adidas",
        },
    },

    # Celtic
    131: {
        1: {  # Home: Iconic green & white horizontal hoops
            "body": (250, 250, 252), "second": (15, 145, 65), "third": (210, 175, 65),
            "patterns": ["084", "091", "102", "114"],
            "sleeve": (250, 250, 252), "shorts": (250, 250, 252),
            "socks": (250, 250, 252), "collar": (15, 145, 65),
            "cuff": (15, 145, 65),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: All-black with neon green / gold Celtic knotwork
            "body": (18, 20, 22), "second": (15, 145, 65), "third": (210, 175, 65),
            "patterns": ["041-E", "169-E", "185-E", "171-E"],
            "sleeve": (18, 20, 22), "shorts": (18, 20, 22),
            "socks": (15, 145, 65), "collar": (210, 175, 65),
            "gradient": 0, "supplier": "adidas",
        },
        3: {  # Third: Soft heritage cream & forest green
            "body": (246, 244, 235), "second": (15, 85, 45), "third": (210, 175, 65),
            "patterns": ["085", "088", "041-E", "083"],
            "sleeve": (246, 244, 235), "shorts": (15, 85, 45),
            "socks": (246, 244, 235), "collar": (15, 85, 45),
            "gradient": 0, "supplier": "adidas",
        },
    },
    398: {  # Celtic FL alias
        1: {
            "body": (250, 250, 252), "second": (15, 145, 65), "third": (210, 175, 65),
            "patterns": ["084", "091", "102", "114"],
            "sleeve": (250, 250, 252), "shorts": (250, 250, 252),
            "socks": (250, 250, 252), "collar": (15, 145, 65),
            "cuff": (15, 145, 65),
            "gradient": 0, "supplier": "adidas",
        },
        2: {
            "body": (18, 20, 22), "second": (15, 145, 65), "third": (210, 175, 65),
            "patterns": ["041-E", "169-E", "141-E", "171-E"],
            "sleeve": (18, 20, 22), "shorts": (18, 20, 22),
            "socks": (15, 145, 65), "collar": (210, 175, 65),
            "gradient": 0, "supplier": "adidas",
        },
        3: {
            "body": (246, 244, 235), "second": (15, 85, 45), "third": (210, 175, 65),
            "patterns": ["085", "088", "041-E", "083"],
            "sleeve": (246, 244, 235), "shorts": (15, 85, 45),
            "socks": (246, 244, 235), "collar": (15, 85, 45),
            "gradient": 0, "supplier": "adidas",
        },
    },

    # Boca Juniors
    139: {
        1: {  # Home: Iconic deep royal blue with central gold horizontal chestband
            "body": (15, 45, 120), "second": (250, 195, 20), "third": (250, 250, 252),
            "patterns": ["chestband", "086", "095", "113"],
            "sleeve": (15, 45, 120), "shorts": (15, 45, 120),
            "socks": (15, 45, 120), "collar": (250, 195, 20),
            "cuff": (250, 195, 20),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: Pure white with blue and gold chestband
            "body": (250, 250, 252), "second": (15, 45, 120), "third": (250, 195, 20),
            "patterns": ["chestband", "086", "095", "113"],
            "sleeve": (250, 250, 252), "shorts": (15, 45, 120),
            "socks": (250, 250, 252), "collar": (15, 45, 120),
            "gradient": 0, "supplier": "adidas",
        },
        3: {  # Third: Buenos Aires street art / La Bombonera architectural geometry
            "body": (20, 24, 35), "second": (250, 195, 20), "third": (15, 45, 120),
            "patterns": ["185-E", "168-E", "042", "219-E"],
            "sleeve": (20, 24, 35), "shorts": (20, 24, 35),
            "socks": (250, 195, 20), "collar": (250, 195, 20),
            "gradient": 1, "supplier": "adidas",
        },
    },
    1241: {  # Boca Juniors alias
        1: {
            "body": (15, 45, 120), "second": (250, 195, 20), "third": (250, 250, 252),
            "patterns": ["chestband", "086", "095", "113"],
            "sleeve": (15, 45, 120), "shorts": (15, 45, 120),
            "socks": (15, 45, 120), "collar": (250, 195, 20),
            "cuff": (250, 195, 20),
            "gradient": 0, "supplier": "adidas",
        },
        2: {
            "body": (250, 250, 252), "second": (15, 45, 120), "third": (250, 195, 20),
            "patterns": ["chestband", "086", "095", "113"],
            "sleeve": (250, 250, 252), "shorts": (15, 45, 120),
            "socks": (250, 250, 252), "collar": (15, 45, 120),
            "gradient": 0, "supplier": "adidas",
        },
        3: {
            "body": (20, 24, 35), "second": (250, 195, 20), "third": (15, 45, 120),
            "patterns": ["185-E", "153-E", "042", "219-E"],
            "sleeve": (20, 24, 35), "shorts": (20, 24, 35),
            "socks": (250, 195, 20), "collar": (250, 195, 20),
            "gradient": 1, "supplier": "adidas",
        },
    },

    # River Plate
    138: {
        1: {  # Home: Iconic pure white with diagonal red sash
            "body": (250, 250, 252), "second": (210, 20, 30), "third": (20, 20, 25),
            "patterns": ["sash", "005", "022", "095", "103", "119"],
            "sleeve": (250, 250, 252), "shorts": (20, 20, 25),
            "socks": (250, 250, 252), "collar": (210, 20, 30),
            "cuff": (210, 20, 30),
            "gradient": 0, "supplier": "adidas",
            "sponsor_dark": (20, 20, 25),
        },
        2: {  # Away: Carmine red with dark charcoal stripes
            "body": (195, 20, 30), "second": (20, 20, 25), "third": (250, 250, 252),
            "patterns": ["081", "082", "088", "083"],
            "sleeve": (195, 20, 30), "shorts": (20, 20, 25),
            "socks": (195, 20, 30), "collar": (250, 250, 252),
            "gradient": 0, "supplier": "adidas",
        },
        3: {  # Third: Noir with diagonal radiant red sash
            "body": (18, 18, 20), "second": (210, 20, 30), "third": (210, 175, 65),
            "patterns": ["005-B", "022-B", "041-E", "214-E"],
            "sleeve": (18, 18, 20), "shorts": (18, 18, 20),
            "socks": (210, 20, 30), "collar": (210, 20, 30),
            "gradient": 1, "supplier": "adidas",
        },
    },
    1240: {  # River Plate alias
        1: {
            "body": (250, 250, 252), "second": (210, 20, 30), "third": (20, 20, 25),
            "patterns": ["sash", "005", "022", "095", "103", "119"],
            "sleeve": (250, 250, 252), "shorts": (20, 20, 25),
            "socks": (250, 250, 252), "collar": (210, 20, 30),
            "cuff": (210, 20, 30),
            "gradient": 0, "supplier": "adidas",
            "sponsor_dark": (20, 20, 25),
        },
        2: {
            "body": (195, 20, 30), "second": (20, 20, 25), "third": (250, 250, 252),
            "patterns": ["081", "082", "088", "083"],
            "sleeve": (195, 20, 30), "shorts": (20, 20, 25),
            "socks": (195, 20, 30), "collar": (250, 250, 252),
            "gradient": 0, "supplier": "adidas",
        },
        3: {
            "body": (18, 18, 20), "second": (210, 20, 30), "third": (210, 175, 65),
            "patterns": ["005-B", "022-B", "041-E", "215-E"],
            "sleeve": (18, 18, 20), "shorts": (18, 18, 20),
            "socks": (210, 20, 30), "collar": (210, 20, 30),
            "gradient": 1, "supplier": "adidas",
        },
    },

    # Everton FC
    177: {
        1: {  # Home: Royal Blue body, clean white shorts, white socks, architectural micro-jacquards
            "body": (24, 64, 119), "second": (245, 245, 248), "third": (151, 169, 193),
            "patterns": ["174-E", "145-E"],
            "sleeve": (24, 64, 119), "shorts": (245, 245, 248),
            "socks": (245, 245, 248), "collar": (245, 245, 248), "cuff": (245, 245, 248),
            "gradient": 0, "supplier": "castore",
        },
        2: {  # Away: Iconic Amber & Royal Blue heritage or Anthracite
            "body": (248, 205, 30), "second": (24, 64, 119), "third": (245, 245, 248),
            "patterns": ["166-B", "014-B"],
            "sleeve": (248, 205, 30), "shorts": (24, 64, 119),
            "socks": (248, 205, 30), "collar": (24, 64, 119), "cuff": (24, 64, 119),
            "gradient": 0, "supplier": "castore",
        },
        3: {  # Third: Vintage Ecru & Forest Green with Gold or Charcoal
            "body": (238, 235, 224), "second": (20, 60, 45), "third": (212, 175, 55),
            "patterns": ["215-E", "211-B"],
            "sleeve": (238, 235, 224), "shorts": (20, 60, 45),
            "socks": (238, 235, 224), "collar": (20, 60, 45), "cuff": (212, 175, 55),
            "gradient": 0, "supplier": "castore",
        },
    },

    # AFC Bournemouth
    4071: {
        1: {  # Home: Iconic Cherry & Black vertical stripes, black shorts, black socks
            "body": (195, 20, 30), "second": (20, 22, 28), "third": (245, 245, 248),
            "patterns": ["081-E", "083"],
            "sleeve": (20, 22, 28), "shorts": (20, 22, 28),
            "socks": (20, 22, 28), "collar": (20, 22, 28), "cuff": (195, 20, 30),
            "gradient": 0, "supplier": "umbro",
        },
        2: {  # Away: Coastal Aqua / Mint / Sky streetwear
            "body": (160, 230, 220), "second": (20, 35, 45), "third": (245, 245, 248),
            "patterns": ["171-E", "215-B"],
            "sleeve": (160, 230, 220), "shorts": (20, 35, 45),
            "socks": (160, 230, 220), "collar": (20, 35, 45), "cuff": (20, 35, 45),
            "gradient": 0, "supplier": "umbro",
        },
        3: {  # Third: Night Purple / Neon Coral luxury streetwear
            "body": (45, 25, 55), "second": (255, 90, 95), "third": (245, 245, 248),
            "patterns": ["191", "204-B"],
            "sleeve": (45, 25, 55), "shorts": (45, 25, 55),
            "socks": (45, 25, 55), "collar": (255, 90, 95), "cuff": (255, 90, 95),
            "gradient": 0, "supplier": "umbro",
        },
    },

    # Brentford FC
    4180: {
        1: {  # Home: Iconic Red & White vertical stripes, black shorts, black/red socks
            "body": (210, 25, 35), "second": (245, 245, 248), "third": (20, 22, 28),
            "patterns": ["118-E", "105"],
            "sleeve": (210, 25, 35), "shorts": (20, 22, 28),
            "socks": (20, 22, 28), "collar": (20, 22, 28), "cuff": (245, 245, 248),
            "gradient": 0, "supplier": "umbro",
        },
        2: {  # Away: Stealth Anthracite / Gold streetwear
            "body": (32, 34, 38), "second": (214, 175, 65), "third": (245, 245, 248),
            "patterns": ["plain", "145-E", "014-B", "067-E", "219-B"],
            "sleeve": (32, 34, 38), "shorts": (32, 34, 38),
            "socks": (32, 34, 38), "collar": (214, 175, 65), "cuff": (214, 175, 65),
            "gradient": 0, "supplier": "umbro",
        },
        3: {  # Third: Raw Earth Olive / Bright Orange streetwear
            "body": (85, 95, 75), "second": (255, 110, 30), "third": (245, 245, 248),
            "patterns": ["081-B", "185-E", "168-B", "214-E", "131-B"],
            "sleeve": (85, 95, 75), "shorts": (85, 95, 75),
            "socks": (85, 95, 75), "collar": (255, 110, 30), "cuff": (255, 110, 30),
            "gradient": 0, "supplier": "umbro",
        },
    },

    # Coventry City
    4183: {
        1: {  # Home: Iconic Sky Blue body, crisp white shorts, sky blue socks
            "body": (105, 175, 225), "second": (245, 245, 248), "third": (18, 32, 60),
            "patterns": ["plain", "041-E", "141-E", "168-E", "171-E", "185-E", "214-E", "215-E"],
            "sleeve": (105, 175, 225), "shorts": (245, 245, 248),
            "socks": (105, 175, 225), "collar": (18, 32, 60), "cuff": (245, 245, 248),
            "gradient": 0, "supplier": "nike",
        },
        2: {  # Away: Pitch Black & Sky Blue neon kinetic
            "body": (22, 24, 28), "second": (105, 175, 225), "third": (245, 245, 248),
            "patterns": ["plain", "008-B", "014-B", "082-B", "166-B"],
            "sleeve": (22, 24, 28), "shorts": (22, 24, 28),
            "socks": (22, 24, 28), "collar": (105, 175, 225), "cuff": (105, 175, 225),
            "gradient": 0, "supplier": "nike",
        },
        3: {  # Third: Vintage Burgundy & Old Gold luxury
            "body": (120, 25, 45), "second": (214, 175, 65), "third": (245, 245, 248),
            "patterns": ["215-E", "168-E", "171-E", "126-B"],
            "sleeve": (120, 25, 45), "shorts": (120, 25, 45),
            "socks": (120, 25, 45), "collar": (214, 175, 65), "cuff": (214, 175, 65),
            "gradient": 0, "supplier": "nike",
        },
    },
}

# --------------------------------------------------------------------------- #
#  Enrich Bespoke DNA with 2026/2027 Streetwear, Cultural & Kinetic Patterns
# --------------------------------------------------------------------------- #
_NEW_STREETWEAR_AWAY = [
    "171-E", "211-B", "185-E", "216-B", "217-B",
    "218-B", "219-B", "220-B", "167-E", "085-E"
]
_NEW_STREETWEAR_THIRD = [
    "126", "166", "167", "168", "171", "177", "180", "184", "191", "197",
    "204", "212", "211", "216", "217", "218",
    "219", "220", "126-B", "131-B", "166-B", "167-B", "168-B",
    "171-E", "204-B", "215-E", "211-B", "041-E",
    "216-B", "217-B", "218-B", "219-B", "220-B", "067-E", "141-E", "153-E"
]
_NEW_HOME_SOLID = ["215-E", "219-E", "220-E", "212-E", "041-E"]
_NEW_HOME_STRIPES = ["081", "082", "083", "088", "093", "105", "124"]

def _enrich_bespoke_dna(dna: Dict[int, Any]) -> None:
    # Retained for backward-compatibility but disabled by default to preserve
    # unique handcrafted per-club DNA without pigeonhole collisions.
    pass

# _enrich_bespoke_dna(BESPOKE_DNA)


# --------------------------------------------------------------------------- #
#  Dynamic DNA Archetype Classification for ANY of the 580+ other clubs
# --------------------------------------------------------------------------- #
# High-Fashion Pattern Pools for General Clubs (2026/2027 Streetwear & Heritage):
# Modern Stripe Archetypes
POOL_STRIPES = [
    "stripes", "081", "082", "083", "088", "093", "097", "105", "118", "124",
    "081-B", "083-C", "088-B", "097-E", "105-B", "118-E", "124-B",
    "081-E", "082-E", "083-E", "088-C", "093-B", "097-B",
    "081-C", "083-B", "093-E", "105-E", "124-E"
]
# Modern Hoops Archetypes
POOL_HOOPS = [
    "084", "091", "102", "114", "084-B", "091-B", "102-E", "114-B", "084-C", "091-C", "102-B"
]
# Modern Sash / Band Archetypes
POOL_SASH = [
    "sash", "005", "022", "095", "103", "113", "119",
    "005-B", "022-B", "095-B", "103-B", "119-B", "005-C"
]
# Modern Chestband Archetypes (Boca / Sampdoria / Parma style)
POOL_CHESTBAND = [
    "chestband", "086", "095", "101", "113", "206", "207", "208", "209",
    "086-B", "206-B", "207-B", "208-B", "209-B"
]
# Modern Half-and-Half Archetypes (Feyenoord / Blackburn / Young Boys style)
POOL_HALF_HALF = [
    "halves", "089", "094", "099", "104", "089-B", "094-E", "099-B", "104-B"
]
# Modern Pinstripes Archetypes
POOL_PINSTRIPES = [
    "pinstripe", "085", "085-E", "090", "096", "110", "118",
    "090-E", "096-E", "110-E"
]
# 2026/2027 High-End Luxury Tonal Jacquards (Elevates solid shirts to luxury streetwear - subtle micro-motifs)
POOL_LUXURY_JACQUARD = [
    "plain", "001-E", "002-E", "003-E", "006-E", "010-E", "014-E", "017-E", "020-E",
    "022-E", "024-E", "027-E", "029-E", "041-E", "042-E", "043-E", "046-E",
    "050-E", "055-E", "060-E", "067-E", "070-E", "075-E", "085-E", "090-E", "096-E",
    "110-E", "118-E", "122-E", "126-E", "131-E", "141-E", "145-E", "150-E", "153-E",
    "166-E", "167-E", "168-E", "170-E", "171-E", "172-E", "174-E",
    "176-E", "177-E", "179-E", "183-E", "185-E", "186-E", "194-E", "198-E",
    "200-E", "204-E", "205-E", "212-E", "215-E", "219-E",
    "220-E"
]
# Modern Angular & Kinetic Away Patterns (50+ curated high-end streetwear graphics)
# Air-gapped from outfield heritage stripes (082/083) and stadium roof trusses (167-E)
POOL_AWAY_GEOMETRIC = [
    "002", "003", "004", "005", "008", "010", "012", "014", "018", "020",
    "022", "026", "029", "032", "036", "084", "085", "087", "090", "093",
    "097", "098", "100", "108", "115", "118", "126", "131", "141", "145",
    "166", "167", "168", "171", "174", "175", "176", "182", "188", "195",
    "201", "204", "211", "212", "214", "215", "216", "217", "218", "219", "220",
    "002-B", "003-B", "005-B", "008-B", "010-B", "014-B", "020-B", "029-B",
    "083-C", "126-B", "166-B", "167-B", "204-B", "216-B", "217-B", "218-B",
    "219-B", "220-B", "041-E", "171-E", "214-E", "215-E", "168-E"
]
# High-Fashion Streetwear / Lifestyle Third Kit Patterns (60+ runway & couture motifs)
# Strictly zero transit maps, zero MS Paint geometric blocks, zero crude dots
POOL_THIRD_STREETWEAR = [
    "041", "042", "044", "045", "046", "048", "052", "054", "058", "064", "072",
    "126", "131", "136", "141", "145", "166", "167", "168", "171", "174", "177",
    "184", "191", "197", "201", "204", "211", "212", "214", "215", "216", "217",
    "218", "219", "220",
    "041-B", "042-B", "044-B", "046-B",
    "126-B", "131-B", "166-B", "167-B", "168-B", "171-E", "204-B",
    "211-B", "212-B", "214-E", "215-E", "216-B", "217-B", "218-B",
    "219-B", "219-E", "220-B", "067-E", "141-E", "153-E"
]

# Keywords that indicate traditional kit identity
RE_CHESTBAND = re.compile(r"\b(boca|boca juniors|sampdoria|parma|wolfsburg|velez|velez sarsfield|gimnasia)\b", re.IGNORECASE)
RE_HALF_HALF = re.compile(r"\b(feyenoord|blackburn|young boys|basel|genoa|nice)\b", re.IGNORECASE)
RE_PINSTRIPES = re.compile(r"\b(olympiacos|besiktas|penarol|inter miami)\b", re.IGNORECASE)
RE_HOOPS = re.compile(r"\b(celtic|sporting|qpr|queens park rangers|reading|doncaster|flamengo|sport recife|shamrock|bristol rovers)\b", re.IGNORECASE)
RE_SASH = re.compile(r"\b(rayo|vallecano|vasco|river|river plate|bordeaux|puebla|curico|peru)\b", re.IGNORECASE)
RE_STRIPES = re.compile(
    r"\b(albion|athletic|atletico|bournemouth|brentford|brighton|southampton|sunderland|stoke|"
    r"sheffield united|sheffield utd|west brom|huddersfield|newcastle|notts county|lincoln|"
    r"grimsby|exeter|crystal palace|palace|porto|espanyol|betis|real society|malaga|huesca|"
    r"alaves|girona|granada|almeria|sparta|sporting gijon|psv|fenerbahce|trabzonspor|gremio|"
    r"fluminense|botafogo|santos|atletico mineiro|chivas|necaxa|monterrey|juventus|milan|"
    r"barcelona|inter|internazionale|atalanta|bologna|udinese|sassuolo|cagliari|hertha|freiburg|"
    r"estudiantes|racing club|san lorenzo)\b",
    re.IGNORECASE,
)


# Intra-League Zero-Collision League Registry
LEAGUE_TEAMS: Dict[str, List[int]] = {
    "epl": [100, 101, 102, 103, 105, 106, 107, 173, 177, 178, 179, 204, 207, 208, 377, 382, 386, 389, 4071, 4180],
    "laliga": [108, 109, 110, 172, 195, 196, 258, 259, 261, 263, 265, 266, 267, 362, 364, 370, 2187, 4145, 4272],
    "seriea": [119, 120, 121, 122, 123, 124, 125, 186, 190, 234, 235, 320, 323, 327, 333, 336, 4219, 4229, 4237, 4914],
    "bundesliga": [126, 127, 128, 129, 185, 225, 226, 227, 231, 232, 436, 4124, 4126, 4139, 4140, 5009, 5010],
    "ligue1": [112, 113, 114, 180, 181, 182, 213, 215, 216, 217, 218, 221, 403, 1329, 1330, 4213],
    "world": [116, 117, 118, 131, 132, 138, 139],
}

CLUB_LEAGUE_MAP: Dict[int, Tuple[str, int]] = {}
for _lkey, _tlist in LEAGUE_TEAMS.items():
    for _idx, _cid in enumerate(_tlist):
        CLUB_LEAGUE_MAP[_cid] = (_lkey, _idx)

# Flat mapping backward compatibility
LEAGUE_ROSTERS: Dict[int, int] = {cid: rank for cid, (_, rank) in CLUB_LEAGUE_MAP.items()}

_LEAGUE_PATTERN_CACHE: Dict[Tuple[str, str, int], Dict[int, str]] = {}

def get_league_assigned_pattern(cid: int, slot: Any, season: int, default_pattern: str, pool: Optional[List[str]] = None) -> str:
    """Guarantee 0.0% pattern collision across all clubs in the same league in the same season."""
    league_info = CLUB_LEAGUE_MAP.get(cid)
    if not league_info:
        return default_pattern
    league_name, rank = league_info
    slot_key = str(slot).lower()
    cache_key = (league_name, slot_key, season)

    if cache_key not in _LEAGUE_PATTERN_CACHE:
        teams = LEAGUE_TEAMS[league_name]
        schedule: Dict[int, str] = {}
        used_patterns: Set[str] = set()
        s_off = season - 2026

        if slot_key in ("g1", "g2", "4", "5"):
            master_pool = POOL_GK_STREETWEAR
            slot_offset = 17 if slot_key in ("g2", "5") else 0
        elif slot_key in ("2", "p2"):
            master_pool = POOL_AWAY_GEOMETRIC
            slot_offset = 0
        elif slot_key in ("3", "p3"):
            master_pool = POOL_THIRD_STREETWEAR
            slot_offset = 0
        else:
            master_pool = POOL_LUXURY_JACQUARD
            slot_offset = 0

        # Pass 1: Assign bespoke clubs first (their curated signature patterns)
        for t_id in teams:
            slot_int = int(slot) if isinstance(slot, int) or (isinstance(slot, str) and slot.isdigit()) else slot
            if t_id in BESPOKE_DNA and slot_int in BESPOKE_DNA[t_id]:
                b_slot = BESPOKE_DNA[t_id][slot_int]
                b_pats = b_slot.get("patterns") or ([b_slot["pattern"]] if "pattern" in b_slot else None)
                if b_pats:
                    cand = b_pats[s_off % len(b_pats)]
                    if cand not in used_patterns:
                        schedule[t_id] = cand
                        used_patterns.add(cand)
                    else:
                        for alt in b_pats:
                            if alt not in used_patterns:
                                schedule[t_id] = alt
                                used_patterns.add(alt)
                                break

        # Pass 2: Assign all remaining clubs from master_pool with zero collision
        for t_idx, t_id in enumerate(teams):
            if t_id in schedule:
                continue
            base_idx = (t_idx * 3 + s_off * 11 + slot_offset) % len(master_pool)
            chosen = master_pool[base_idx]
            step = 0
            while chosen in used_patterns and step < len(master_pool):
                base_idx = (base_idx + 1) % len(master_pool)
                chosen = master_pool[base_idx]
                step += 1
            schedule[t_id] = chosen
            used_patterns.add(chosen)

        _LEAGUE_PATTERN_CACHE[cache_key] = schedule

    return _LEAGUE_PATTERN_CACHE[cache_key].get(cid, default_pattern)


def classify_club_dna(club: Dict[str, Any]) -> str:
    """Classify a club's canonical design archetype based on name and profile."""
    name = str(club.get("name", ""))
    if RE_CHESTBAND.search(name):
        return "CHESTBAND"
    if RE_HALF_HALF.search(name):
        return "HALF_AND_HALF"
    if RE_HOOPS.search(name):
        return "HOOPS"
    if RE_SASH.search(name):
        return "SASH"
    if RE_PINSTRIPES.search(name):
        return "PINSTRIPES"
    if RE_STRIPES.search(name):
        return "STRIPES"

    # Default canonical identity for non-patterned clubs is luxury solid with tonal jacquards
    return "LUXURY_SOLID"


def generate_streetwear_palette(club: Dict[str, Any], salt: int) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]:
    """Generate high-fashion 2026/2027 streetwear palette (body, second, third)."""
    primary = _hexc(club.get("primary", "#034694"))
    secondary = _hexc(club.get("secondary", "#FFFFFF"))
    accent = _hexc(club.get("accent", "#C8102E"))

    mood = salt % 8
    if mood == 0:
        # NOIR & METALLIC LUXURY (Venezia FC / Y-3)
        body = (18, 20, 24)
        metals = [(214, 175, 65), (225, 228, 235), (200, 140, 70), (195, 205, 215)]
        second = metals[(salt // 8) % len(metals)]
        third = primary if _lum(primary) > 70 else accent
    elif mood == 1:
        # RAW BOTANICAL & EARTHY ECRU (Aimé Leon Dore / Wales Bonner)
        ecrus = [(244, 241, 234), (238, 233, 222), (232, 225, 212)]
        body = ecrus[(salt // 8) % len(ecrus)]
        earths = [(25, 65, 45), (75, 88, 72), (180, 50, 45), (42, 32, 28), (145, 95, 65)]
        second = earths[(salt // 8) % len(earths)]
        third = (212, 175, 55) if (salt % 2) else primary
    elif mood == 2:
        # CYBER DUSK & NEON AURORA (Tokyo / London Rave Underground)
        body = (14, 18, 30) if (salt % 2) else (20, 14, 32)
        neons = [(210, 255, 0), (255, 35, 90), (0, 235, 230), (165, 255, 40), (240, 90, 220)]
        second = neons[(salt // 8) % len(neons)]
        third = (245, 245, 250) if _lum(second) < 180 else primary
    elif mood == 3:
        # PASTEL COUTURE & WASHED MINERALS (Paris Runway)
        pastels = [(218, 212, 230), (205, 226, 232), (226, 175, 160), (228, 192, 190), (195, 215, 205)]
        body = pastels[(salt // 8) % len(pastels)]
        second = (18, 20, 24)
        third = primary if _lum(primary) < 100 else accent
    elif mood == 4:
        # GORPCORE TECHWEAR & TACTICAL UTILITY (Arc'teryx / Corteiz)
        stealths = [(95, 102, 110), (45, 50, 58), (125, 120, 110), (60, 68, 62)]
        body = stealths[(salt // 8) % len(stealths)]
        hi_vis = [(255, 85, 0), (225, 255, 20), (0, 230, 180), (255, 40, 40)]
        second = hi_vis[(salt // 8) % len(hi_vis)]
        third = (240, 242, 245)
    elif mood == 5:
        # MONOCHROME OP-ART ARCHIVE (Yohji Yamamoto / Minimalist)
        body = (16, 17, 20) if (salt % 2 == 0) else (248, 248, 250)
        second = (248, 248, 250) if body[0] < 50 else (16, 17, 20)
        third = primary if _lum(primary) > 60 else (214, 175, 65)
    elif mood == 6:
        # TWILIGHT HORIZON & SUNSET GRADIENT
        body = (24, 20, 45) if (salt % 2) else (18, 32, 60)
        sunsets = [(255, 120, 80), (255, 75, 130), (0, 220, 210), (245, 185, 55)]
        second = sunsets[(salt // 8) % len(sunsets)]
        third = secondary if _lum(secondary) > 160 else (245, 245, 250)
    else:
        # INVERTED CLUB ARCHIVE STREETWEAR
        body = secondary if (_lum(secondary) > 180 or _lum(primary) < 100) else accent
        second = primary
        third = (212, 175, 55) if (salt % 2) else accent

    return body, second, third


# --------------------------------------------------------------------------- #
#  High-Visibility 2026/2027 Goalkeeper Streetwear Palettes & Generator
# --------------------------------------------------------------------------- #
GK_STREETWEAR_PALETTES: List[Dict[str, Any]] = [
    # 0. Cyber Volt (Electric High-Vis Lime)
    {
        "name": "Cyber Volt",
        "body": (215, 255, 0),
        "second": (18, 20, 24),
        "third": (0, 240, 255),
        "collar": (18, 20, 24),
        "cuff": (18, 20, 24),
        "shorts": (18, 20, 24),
        "socks": (215, 255, 0),
        "sponsor_dark": (18, 20, 24),
    },
    # 1. Glacier Cyan (Luminous Laser Turquoise)
    {
        "name": "Glacier Cyan",
        "body": (0, 235, 230),
        "second": (12, 25, 48),
        "third": (250, 250, 252),
        "collar": (12, 25, 48),
        "cuff": (12, 25, 48),
        "shorts": (0, 235, 230),
        "socks": (0, 235, 230),
        "sponsor_dark": (12, 25, 48),
    },
    # 2. Hyper Infrared (Blaze Safety Orange)
    {
        "name": "Hyper Infrared",
        "body": (255, 95, 20),
        "second": (18, 20, 25),
        "third": (255, 255, 255),
        "collar": (18, 20, 25),
        "cuff": (18, 20, 25),
        "shorts": (18, 20, 25),
        "socks": (255, 95, 20),
        "sponsor_dark": (18, 20, 25),
    },
    # 3. Laser Berry (Shocking Neon Pink)
    {
        "name": "Laser Berry",
        "body": (250, 30, 130),
        "second": (15, 15, 25),
        "third": (255, 255, 0),
        "collar": (15, 15, 25),
        "cuff": (15, 15, 25),
        "shorts": (250, 30, 130),
        "socks": (250, 30, 130),
        "sponsor_dark": (15, 15, 25),
    },
    # 4. Acid Toxic (Flash Hyper Mint)
    {
        "name": "Acid Toxic",
        "body": (50, 240, 90),
        "second": (10, 35, 20),
        "third": (250, 250, 252),
        "collar": (10, 35, 20),
        "cuff": (10, 35, 20),
        "shorts": (10, 35, 20),
        "socks": (50, 240, 90),
        "sponsor_dark": (10, 35, 20),
    },
    # 5. Solar Gold (Radiant Neon Amber)
    {
        "name": "Solar Gold",
        "body": (255, 205, 10),
        "second": (20, 20, 32),
        "third": (240, 60, 30),
        "collar": (20, 20, 32),
        "cuff": (20, 20, 32),
        "shorts": (255, 205, 10),
        "socks": (255, 205, 10),
        "sponsor_dark": (20, 20, 32),
    },
    # 6. Cyber Violet (Deep Neon Purple with Turquoise)
    {
        "name": "Cyber Violet",
        "body": (120, 40, 220),
        "second": (20, 240, 220),
        "third": (250, 250, 252),
        "collar": (20, 240, 220),
        "cuff": (20, 240, 220),
        "shorts": (20, 20, 32),
        "socks": (120, 40, 220),
        "sponsor_white": True,
    },
    # 7. Solar Volt Blaze (Ultra High-Vis Electric Lime-Yellow)
    {
        "name": "Solar Volt Blaze",
        "body": (225, 255, 20),
        "second": (15, 20, 28),
        "third": (0, 220, 255),
        "collar": (15, 20, 28),
        "cuff": (15, 20, 28),
        "shorts": (15, 20, 28),
        "socks": (225, 255, 20),
        "sponsor_dark": (15, 20, 28),
    },
    # 8. Emerald Pulse (Luminous Electric Green)
    {
        "name": "Emerald Pulse",
        "body": (10, 230, 130),
        "second": (12, 36, 24),
        "third": (255, 255, 255),
        "collar": (12, 36, 24),
        "cuff": (12, 36, 24),
        "shorts": (10, 230, 130),
        "socks": (10, 230, 130),
        "sponsor_dark": (12, 36, 24),
    },
    # 9. Sunset Coral (Blazing Electric Peach)
    {
        "name": "Sunset Coral",
        "body": (255, 110, 75),
        "second": (18, 22, 45),
        "third": (255, 255, 255),
        "collar": (18, 22, 45),
        "cuff": (18, 22, 45),
        "shorts": (18, 22, 45),
        "socks": (255, 110, 75),
        "sponsor_dark": (18, 22, 45),
    },
    # 10. Electric Ice (Arctic High-Vis White/Silver Cyan)
    {
        "name": "Electric Ice",
        "body": (210, 240, 255),
        "second": (15, 30, 65),
        "third": (0, 180, 255),
        "collar": (15, 30, 65),
        "cuff": (15, 30, 65),
        "shorts": (15, 30, 65),
        "socks": (210, 240, 255),
        "sponsor_dark": (15, 30, 65),
    },
    # 11. Cyber Lavender (Futuristic Soft Violet with Volt)
    {
        "name": "Cyber Lavender",
        "body": (195, 180, 245),
        "second": (20, 18, 35),
        "third": (215, 255, 0),
        "collar": (20, 18, 35),
        "cuff": (20, 18, 35),
        "shorts": (20, 18, 35),
        "socks": (195, 180, 245),
        "sponsor_dark": (20, 18, 35),
    },
    # 12. Vivid Orange Tech (Radiant Safety Orange)
    {
        "name": "Vivid Orange Tech",
        "body": (255, 130, 10),
        "second": (22, 25, 30),
        "third": (255, 255, 255),
        "collar": (22, 25, 30),
        "cuff": (22, 25, 30),
        "shorts": (255, 130, 10),
        "socks": (255, 130, 10),
        "sponsor_dark": (22, 25, 30),
    },
    # 13. Hyper Lime Teal (High-Vis Acid Lime with Teal)
    {
        "name": "Hyper Lime Teal",
        "body": (165, 255, 110),
        "second": (10, 48, 52),
        "third": (255, 255, 255),
        "collar": (10, 48, 52),
        "cuff": (10, 48, 52),
        "shorts": (10, 48, 52),
        "socks": (165, 255, 110),
        "sponsor_dark": (10, 48, 52),
    },
    # 14. Neon Punch Pink (Shocking Magenta with Neon Cyan)
    {
        "name": "Neon Punch Pink",
        "body": (255, 55, 160),
        "second": (15, 15, 20),
        "third": (0, 240, 255),
        "collar": (15, 15, 20),
        "cuff": (15, 15, 20),
        "shorts": (15, 15, 20),
        "socks": (255, 55, 160),
        "sponsor_dark": (15, 15, 20),
    },
    # 15. Desert Tech (Tactical Sand Dune with Solar Orange)
    {
        "name": "Desert Tech",
        "body": (230, 215, 185),
        "second": (255, 95, 20),
        "third": (30, 32, 38),
        "collar": (30, 32, 38),
        "cuff": (30, 32, 38),
        "shorts": (30, 32, 38),
        "socks": (230, 215, 185),
        "sponsor_dark": (30, 32, 38),
    },
]

POOL_GK_STREETWEAR = [
    # Air-gapped authentic goalkeeper patterns (aerodynamic streaks, hex-mesh, subtle modern camo, waves)
    # Strictly zero overlap with outfield club heritage stripes, stadium roof trusses, or tweed checks!
    "011", "014", "018", "022", "027", "030", "033", "036", "048", "054",
    "074", "112", "126", "131", "136", "145", "151", "165", "172",
    "178", "182", "201", "202", "205", "212", "216", "218", "220",
    "126-B", "022-B", "131-B", "204-B", "216-B", "217-B", "218-B", "220-B"
]


def pick_gk_palette(club: Dict[str, Any], season: int, slot: str = "g1", sponsor: Optional[str] = None) -> Dict[str, Any]:
    """Pick an iconic high-vis GK streetwear palette that is guaranteed NOT to clash
    with ANY of the club's outfield kits (P1, P2, P3) and g2 contrasts sharply with g1."""
    primary = _hexc(club.get("primary", "#034694"))
    secondary = _hexc(club.get("secondary", "#FFFFFF"))
    cid = int(club.get("id") or club.get("team_id", 0))
    s_off = season - 2026

    # Gather all outfield kit body colors (P1, P2, P3) to prevent GK vs Outfield clashing
    outfield_colors = [primary, secondary]
    if cid in BESPOKE_DNA:
        for s in (1, 2, 3):
            if s in BESPOKE_DNA[cid]:
                sdef = BESPOKE_DNA[cid][s]
                if "body" in sdef:
                    outfield_colors.append(sdef["body"])
                if "palettes" in sdef:
                    for pal in sdef["palettes"]:
                        if "body" in pal:
                            outfield_colors.append(pal["body"])

    def _no_outfield_clash(cand_body, min_dist=112):
        return all(_dist(cand_body, c) >= min_dist for c in outfield_colors)

    n_pal = len(GK_STREETWEAR_PALETTES)

    # High-entropy seed incorporates club ID, season, slot, and sponsor
    g1_seed = _club_seed(cid, "g1", season, sponsor)
    g1_idx = (g1_seed + s_off * 5) % n_pal
    g1_palette = None
    for offset in range(n_pal):
        candidate = GK_STREETWEAR_PALETTES[(g1_idx + offset) % n_pal]
        if _no_outfield_clash(candidate["body"], min_dist=112):
            g1_palette = candidate
            break
    if g1_palette is None:
        # Fallback: choose the candidate with maximum minimum distance from any outfield color
        g1_palette = max(GK_STREETWEAR_PALETTES,
                         key=lambda p: min(_dist(p["body"], c) for c in outfield_colors))

    if slot == "g1":
        return dict(g1_palette)

    # For g2, must avoid both g1 (distance >= 130) and ALL club outfield kits
    g2_seed = _club_seed(cid, "g2", season, sponsor)
    g2_idx = (g2_seed + s_off * 7) % n_pal
    for offset in range(n_pal):
        candidate = GK_STREETWEAR_PALETTES[(g2_idx + offset) % n_pal]
        if (_dist(candidate["body"], g1_palette["body"]) >= 130 and
            _no_outfield_clash(candidate["body"], min_dist=90)):
            return dict(candidate)

    # Fallback for g2 if constraints are tight: choose palette maximizing contrast with g1 and outfield
    furthest = max(GK_STREETWEAR_PALETTES,
                   key=lambda p: min(_dist(p["body"], g1_palette["body"]),
                                     min(_dist(p["body"], c) for c in outfield_colors)))
    return dict(furthest)


def _generate_gk_dna(club: Dict[str, Any], season: int, slot: str = "g1", sponsor: Optional[str] = None) -> Dict[str, Any]:
    cid = int(club.get("id") or club.get("team_id", 0))
    cname = str(club.get("name", ""))
    supplier = get_club_supplier(cid, cname)
    s_off = season - 2026
    seed = _club_seed(cid, slot, season, sponsor)

    pal = pick_gk_palette(club, season, slot=slot, sponsor=sponsor)
    choices = POOL_GK_STREETWEAR
    slot_num = 1 if slot == "g1" else 2
    default_idx = (seed + s_off * 13 + slot_num * 17) % len(choices)
    pattern = get_league_assigned_pattern(cid, slot, season, choices[default_idx], choices)

    gk_body = pal["body"]
    gk_second = pal["second"]
    gk_third = pal.get("third", gk_second)

    shorts_col = pal.get("shorts", gk_body)
    socks_col = pal.get("socks", gk_body)
    collar_col = pal.get("collar", gk_second)
    cuff_col = pal.get("cuff", gk_second)

    style: Dict[str, Any] = {
        "body": gk_body,
        "second": gk_second,
        "third": gk_third,
        "pattern": pattern,
        "var": (seed >> 8) % 3,
        "width_step": (seed >> 11) % 8,
        "sleeve": gk_body,
        "sleeve_style": "shoulder_stripe" if supplier == "adidas" else ["raglan", "tipped", "shoulder_stripe", "solid"][(seed >> 5) % 4],
        "shorts": shorts_col,
        "shorts_style": "three_stripes" if supplier == "adidas" else ["split_leg", "side_stripe", "hem_tape", "solid"][(seed >> 7) % 4],
        "shorts_accent": gk_second if shorts_col == gk_body else gk_body,
        "socks": socks_col,
        "socks_style": ["turnover_hoop", "calf_band", "gradient_fade", "solid"][(seed >> 11) % 4],
        "socks_accent": gk_second if socks_col == gk_body else gk_body,
        "socks_tip": gk_third,
        "collar": collar_col,
        "collar_tip": gk_third if ((seed >> 2) % 2) else collar_col,
        "cuff": cuff_col,
        "cuff_tip": gk_third if ((seed >> 3) % 3 == 0) else cuff_col,
        "gradient": 1 if (seed % 2) else 0,
        "supplier": supplier,
        "vent_style": ["laser_cut", "stealth_rib", "contrast_panel"][(seed >> 2) % 3],
        "macro_layout": ["solid", "ombre_fade", "solid"][(seed >> 5) % 3],
        "pattern_mask": ["front_only", "full", "front_only"][(seed >> 7) % 3],
        "tile_scale": 1.0,
    }
    if pal.get("sponsor_dark"):
        style["sponsor_dark"] = pal["sponsor_dark"]
    if pal.get("sponsor_white"):
        style["sponsor_white"] = True

    return style


# Comprehensive authentic supplier mappings
CLUB_SUPPLIERS: Dict[int, str] = {
    # Premier League
    100: "adidas",      # Manchester United
    101: "adidas",      # Arsenal
    102: "nike",        # Chelsea
    103: "nike",        # Liverpool
    105: "umbro",       # West Ham
    106: "adidas",      # Newcastle
    107: "adidas",      # Aston Villa
    173: "puma",        # Manchester City
    177: "castore",     # Everton
    178: "adidas",      # Fulham
    179: "nike",        # Tottenham
    204: "adidas",      # Leicester
    207: "puma",        # Southampton
    208: "castore",     # Wolverhampton
    377: "nike",        # Brighton & Hove Albion
    382: "macron",      # Crystal Palace
    386: "umbro",       # Ipswich
    389: "adidas",      # Nottingham Forest
    4071: "umbro",      # Bournemouth
    4180: "umbro",      # Brentford
    4183: "nike",       # Coventry City
    387: "macron",      # Millwall

    # La Liga
    108: "nike",        # Barcelona
    109: "adidas",      # Real Madrid
    110: "puma",        # Valencia
    172: "nike",        # Atletico Madrid
    195: "hummel",      # Celta Vigo
    196: "macron",      # Real Sociedad
    258: "castore",     # Athletic Club
    259: "joma",        # Espanyol
    261: "nike",        # Mallorca
    263: "macron",      # Osasuna
    265: "castore",     # Sevilla
    266: "kappa",       # Real Valladolid
    267: "joma",        # Villarreal
    362: "joma",        # Getafe
    364: "hummel",      # Las Palmas
    370: "umbro",       # Rayo Vallecano
    2187: "puma",       # Girona
    4145: "puma",       # Alaves
    4272: "joma",       # Leganes

    # Serie A
    119: "nike",        # Internazionale
    120: "adidas",      # Juventus
    121: "puma",        # Milan
    122: "mizuno",      # Lazio
    123: "puma",        # Parma
    124: "kappa",       # Fiorentina
    125: "adidas",      # Roma
    186: "macron",      # Bologna
    190: "macron",      # Udinese
    234: "joma",        # Atalanta
    235: "kappa",       # Empoli
    320: "macron",      # Cagliari
    323: "kappa",       # Genoa
    327: "ea7",         # Napoli
    333: "joma",        # Torino
    336: "joma",        # Hellas Verona
    4219: "adidas",     # Como
    4229: "kappa",      # Venezia
    4237: "macron",     # Lecce
    4914: "joma",       # Monza

    # Bundesliga
    126: "puma",        # Dortmund
    127: "adidas",      # Bayern Munchen
    128: "castore",     # Leverkusen
    129: "adidas",      # HSV
    185: "hummel",      # Bremen
    225: "puma",        # Gladbach
    226: "nike",        # Frankfurt
    227: "nike",        # Freiburg
    231: "puma",        # Stuttgart
    232: "nike",        # Wolfsburg
    436: "kappa",       # Mainz
    4124: "mizuno",     # Augsburg
    4126: "joma",       # Hoffenheim
    4139: "puma",       # St Pauli
    4140: "adidas",     # Union Berlin
    5009: "puma",       # Heidenheim
    5010: "puma",       # Leipzig

    # Ligue 1
    112: "kappa",       # Monaco
    113: "puma",        # Marseille
    114: "nike",        # PSG
    180: "macron",      # Auxerre
    181: "adidas",      # Lyon
    182: "puma",        # Lens
    213: "newbalance",  # Lille
    215: "nike",        # Montpellier
    216: "macron",      # Nantes
    217: "macron",      # Nice
    218: "puma",        # Rennes
    221: "nike",        # Toulouse
    403: "nike",        # Angers
    1329: "adidas",     # Brest
    1330: "puma",       # Reims
    4213: "adidas",     # Strasbourg

    # World / Americas
    116: "adidas",      # Ajax
    117: "castore",     # Feyenoord
    118: "puma",        # PSV
    131: "adidas",      # Celtic
    132: "castore",     # Rangers
    138: "adidas",      # River Plate
    139: "adidas",      # Boca Juniors
}

GENERIC_SUPPLIERS = ["adidas", "nike", "puma", "umbro", "macron", "kappa", "joma", "hummel", "castore"]

def get_club_supplier(cid: int, name: str = "") -> str:
    """Return authentic supplier for club, or a deterministic premier brand."""
    if cid in CLUB_SUPPLIERS:
        return CLUB_SUPPLIERS[cid]
    if cid in BESPOKE_DNA and 1 in BESPOKE_DNA[cid] and "supplier" in BESPOKE_DNA[cid][1]:
        return BESPOKE_DNA[cid][1]["supplier"]
    idx = (cid * 17 + len(name)) % len(GENERIC_SUPPLIERS)
    return GENERIC_SUPPLIERS[idx]


def get_club_style(club: Dict[str, Any], slot: int | str, season: int, sponsor: Optional[str] = None) -> Dict[str, Any]:
    """Return a complete, fashion-forward 2026/2027 styling dict for club + slot + season with dynamic multi-decade evolution."""
    cid = int(club.get("id") or club.get("team_id", 0))
    cname = str(club.get("name", ""))
    supplier = get_club_supplier(cid, cname)

    # Goalkeeper kit slots
    if slot in ("g1", 4, "4"):
        if cid in BESPOKE_DNA and "g1" in BESPOKE_DNA[cid]:
            return dict(BESPOKE_DNA[cid]["g1"])
        return _generate_gk_dna(club, season, slot="g1", sponsor=sponsor)
    elif slot in ("g2", 5, "5"):
        if cid in BESPOKE_DNA and "g2" in BESPOKE_DNA[cid]:
            return dict(BESPOKE_DNA[cid]["g2"])
        return _generate_gk_dna(club, season, slot="g2", sponsor=sponsor)

    if isinstance(slot, str):
        slot = int(slot.replace("p", ""))

    primary = _hexc(club.get("primary", "#034694"))
    secondary = _hexc(club.get("secondary", "#FFFFFF"))
    accent = _hexc(club.get("accent", "#C8102E"))
    s_off = season - 2026

    # 32-bit Murmur-style avalanche seed per club, slot, season, and sponsor
    seed = _club_seed(cid, slot, season, sponsor)
    salt_val = seed

    # 1. Check bespoke curated DNA first
    if cid in BESPOKE_DNA and slot in BESPOKE_DNA[cid]:
        slot_def = BESPOKE_DNA[cid][slot]
        if "palettes" in slot_def:
            p_choices = slot_def["palettes"]
            # Strict linear progression guarantees consecutive seasons never duplicate
            p_idx = s_off % len(p_choices)
            base_style = dict(p_choices[p_idx])
        else:
            base_style = dict(slot_def)
            if slot == 2:
                away_cycle = s_off % 4
                if away_cycle == 1:
                    if _lum(base_style.get("body", (250, 250, 252))) > 180:
                        base_style["body"] = (22, 26, 36)
                        base_style["shorts"] = (22, 26, 36)
                        base_style["socks"] = (22, 26, 36)
                        base_style["collar"] = primary
                    else:
                        base_style["body"] = (250, 250, 252)
                        base_style["shorts"] = primary if _lum(primary) < 130 else (250, 250, 252)
                        base_style["socks"] = (250, 250, 252)
                        base_style["collar"] = primary
                elif away_cycle == 2:
                    base_style["body"] = (235, 228, 215) if _lum(primary) < 140 else (55, 62, 68)
                    base_style["shorts"] = base_style["body"]
                    base_style["socks"] = base_style["body"]
                    base_style["collar"] = primary
                elif away_cycle == 3:
                    if _dist(accent, primary) > 80 and _lum(accent) > 40:
                        base_style["body"] = accent
                        base_style["shorts"] = primary
                        base_style["socks"] = accent
                        base_style["collar"] = primary
                    else:
                        base_style["body"] = (24, 28, 38)
                        base_style["shorts"] = (24, 28, 38)
                        base_style["socks"] = (24, 28, 38)
                        base_style["collar"] = secondary
            elif slot == 3:
                # Retain curated bespoke third kit identity, rotate subtle accents per season
                third_cycle = s_off % 3
                if third_cycle == 1 and "third" in base_style and base_style["third"]:
                    # Seasonal accent swap on collar/cuff while keeping signature body
                    base_style["collar"] = base_style["third"]
                    base_style["cuff"] = base_style["third"]
                elif third_cycle == 2:
                    # Alternate shorts option if defined
                    if "alt_shorts" in base_style:
                        base_style["shorts"] = base_style["alt_shorts"][(salt_val) % len(base_style["alt_shorts"])]

        if _lum(base_style.get("body", primary)) < 128:
            base_style.pop("sponsor_dark", None)

        if "supplier" not in base_style:
            base_style["supplier"] = supplier

        # Dynamic variation for Home Kit
        if slot == 1:
            if "alt_shorts" in base_style:
                sh_choices = base_style["alt_shorts"]
                sh_idx = s_off % len(sh_choices)
                base_style["shorts"] = sh_choices[sh_idx]
            elif _lum(base_style.get("body", primary)) < 140 and _lum(base_style.get("second", secondary)) > 150:
                if s_off % 2 == 1:
                    base_style["shorts"] = base_style.get("second", secondary)
            if "alt_socks" in base_style:
                so_choices = base_style["alt_socks"]
                so_idx = s_off % len(so_choices)
                base_style["socks"] = so_choices[so_idx]

        # Real Madrid iconic heritage aura seasonal rotation
        if cid == 109 and slot == 1:
            aura_cycle = s_off % 3
            if aura_cycle == 0:
                # Galácticos Pure Gold Era (2011/12, 2019/20, 2023/24)
                base_style["second"] = (212, 175, 55)
                base_style["third"] = (15, 25, 55)
                base_style["collar"] = (252, 252, 254)
                base_style["collar_tip"] = (212, 175, 55)
                base_style["cuff"] = (212, 175, 55)
                base_style["cuff_tip"] = (15, 25, 55)
                base_style["stripe_accent"] = (212, 175, 55)
                base_style["supplier_color"] = (212, 175, 55)
            elif aura_cycle == 1:
                # Castilian Violet / Royal Purple Heritage (La Séptima, La Duodécima, 2022/23)
                base_style["second"] = (75, 40, 130)
                base_style["third"] = (212, 175, 55)
                base_style["collar"] = (252, 252, 254)
                base_style["collar_tip"] = (75, 40, 130)
                base_style["cuff"] = (75, 40, 130)
                base_style["cuff_tip"] = (212, 175, 55)
                base_style["stripe_accent"] = (75, 40, 130)
                base_style["supplier_color"] = (75, 40, 130)
            elif aura_cycle == 2:
                # Sovereign Midnight Navy & Gold (2023/24)
                base_style["second"] = (15, 25, 55)
                base_style["third"] = (212, 175, 55)
                base_style["collar"] = (15, 25, 55)
                base_style["collar_tip"] = (212, 175, 55)
                base_style["cuff"] = (15, 25, 55)
                base_style["cuff_tip"] = (212, 175, 55)
                base_style["stripe_accent"] = (212, 175, 55)
                base_style["supplier_color"] = (15, 25, 55)

        pool = base_style.pop("patterns", None)
        if pool:
            # Deterministic progression with sponsor and club entropy with intra-league zero collision
            p_idx = ((seed ^ (cid * 0x45D9F3B)) + s_off * 37) % len(pool)
            base_style["pattern"] = get_league_assigned_pattern(cid, slot, season, pool[p_idx], pool)

        # Tailoring trims for bespoke clubs
        if "cuff_tip" not in base_style:
            base_style["cuff_tip"] = base_style.get("third") or base_style.get("second")
        if "collar_tip" not in base_style:
            base_style["collar_tip"] = base_style.get("third") if (salt_val % 2) else base_style.get("collar")
        if "shorts_style" not in base_style:
            if supplier == "adidas":
                base_style["shorts_style"] = "three_stripes"
            else:
                base_style["shorts_style"] = ["split_leg", "solid", "hem_tape", "side_stripe"][(salt_val // 7) % 4]
            base_style["shorts_accent"] = base_style.get("second")
        if "socks_style" not in base_style:
            base_style["socks_style"] = ["turnover_hoop", "calf_band", "gradient_fade", "solid"][(salt_val // 11) % 4]
            base_style["socks_accent"] = base_style.get("second")
            base_style["socks_tip"] = base_style.get("third")
        if "sleeve_style" not in base_style:
            if supplier == "adidas":
                base_style["sleeve_style"] = "shoulder_stripe"
            elif cid == 101 and slot == 1:
                base_style["sleeve_style"] = "raglan"
            else:
                base_style["sleeve_style"] = ["solid", "tipped", "shoulder_stripe", "tipped"][(salt_val // 13) % 4]
        if "vent_style" not in base_style:
            base_style["vent_style"] = ["laser_cut", "stealth_rib", "contrast_panel", "none"][(salt_val // 17) % 4]
        if "macro_layout" not in base_style:
            base_style["macro_layout"] = "solid"
        if "pattern_mask" not in base_style:
            base_style["pattern_mask"] = "full"
        if "tile_scale" not in base_style:
            base_style["tile_scale"] = 1.0
        if "finish" not in base_style:
            base_style["finish"] = "standard"
        base_style["var"] = salt_val % 3
        base_style["width_step"] = (salt_val // 3) % 8
        return base_style

    # 2. Dynamic Classification & Procedural Multi-Season Evolution for all other 550+ clubs
    archetype = classify_club_dna(club)

    if slot == 1:
        # HOME KIT: Respect iconic identity, elevate with luxury tailoring & seasonal rotation
        if archetype == "STRIPES":
            pool = POOL_STRIPES
        elif archetype == "HOOPS":
            pool = POOL_HOOPS
        elif archetype == "SASH":
            pool = POOL_SASH
        elif archetype == "CHESTBAND":
            pool = POOL_CHESTBAND
        elif archetype == "HALF_AND_HALF":
            pool = POOL_HALF_HALF
        elif archetype == "PINSTRIPES":
            pool = POOL_PINSTRIPES
        else:
            pool = POOL_LUXURY_JACQUARD

        # Advance pattern with full per-club and per-season entropy so clubs NEVER repeat or match each other
        p_idx = ((seed ^ (cid * 0x45D9F3B)) + s_off * 37) % len(pool)
        pattern = get_league_assigned_pattern(cid, 1, season, pool[p_idx], pool)

        # White kit design enhancement: never flat plain, always rich tonal jacquard
        if _lum(primary) > 220 and pattern in ("plain", "solid"):
            p_jacq = POOL_LUXURY_JACQUARD[(seed + s_off * 17) % len(POOL_LUXURY_JACQUARD)]
            pattern = get_league_assigned_pattern(cid, 1, season, p_jacq, POOL_LUXURY_JACQUARD)

        # Alternating shorts: Contrast vs Monochrome
        cycle = (seed + s_off) % 4
        if _lum(primary) < 140 and _lum(secondary) > 150:
            shorts_col = secondary if (cycle % 2 == 1) else primary
        else:
            shorts_col = secondary if _lum(primary) < 140 else primary

        socks_col = primary if (cycle % 3 != 1) else secondary
        collar_col = secondary if (cycle % 3 != 2) else (accent if _dist(accent, primary) > 70 else secondary)
        if _lum(primary) > 220 and _lum(collar_col) > 220:
            collar_col = secondary if _dist(secondary, primary) > 60 else (19, 34, 64)

        macro_cand = ["solid", "solid", "chestband", "ombre_fade", "solid"][(seed >> 6) % 5] if archetype == "SOLID" else "solid"
        micro_cand = POOL_LUXURY_JACQUARD[(seed + s_off * 13) % len(POOL_LUXURY_JACQUARD)] if archetype == "SOLID" and macro_cand != "solid" else None
        mask_cand = ["full", "front_only", "front_only", "chest_only"][(seed >> 8) % 4] if archetype == "SOLID" else "full"

        return {
            "body": primary,
            "second": secondary,
            "third": accent,
            "pattern": pattern,
            "var": (seed >> 8) % 3,
            "width_step": (seed >> 11) % 8,
            "sleeve": primary,
            "sleeve_style": "shoulder_stripe" if supplier == "adidas" else ["solid", "tipped", "shoulder_stripe", "tipped"][(seed >> 5) % 4],
            "shorts": shorts_col,
            "shorts_style": "three_stripes" if supplier == "adidas" else ["split_leg", "side_stripe", "hem_tape", "solid"][(seed >> 7) % 4],
            "shorts_accent": secondary if shorts_col == primary else primary,
            "socks": socks_col,
            "socks_style": ["turnover_hoop", "calf_band", "gradient_fade", "solid"][(seed >> 11) % 4],
            "socks_accent": secondary,
            "socks_tip": accent,
            "collar": collar_col,
            "collar_tip": accent if ((seed >> 2) % 2) else collar_col,
            "cuff": secondary,
            "cuff_tip": accent if ((seed >> 3) % 3 == 0) else secondary,
            "gradient": 0,
            "supplier": supplier,
            "vent_style": ["laser_cut", "contrast_panel", "stealth_rib", "none"][(seed >> 4) % 4],
            "macro_layout": macro_cand,
            "micro_jacquard": micro_cand,
            "pattern_mask": mask_cand,
            "tile_scale": 1.0,
            "finish": "standard",
        }

    elif slot == 2:
        # AWAY KIT: Modern kinetic geometry & 4-year distinct colorway cycle
        cycle = (s_off + (seed % 4)) % 4
        choices = POOL_AWAY_GEOMETRIC
        default_idx = (seed + s_off * 19) % len(choices)
        pattern = get_league_assigned_pattern(cid, 2, season, choices[default_idx], choices)

        if cycle == 0:
            away_body = (250, 250, 252) if _lum(primary) < 160 else (20, 24, 32)
            away_second = primary
            away_third = accent
            away_shorts = primary if _lum(primary) < 130 else (250, 250, 252)
            away_socks = (250, 250, 252)
            away_collar = primary
        elif cycle == 1:
            if _dist(accent, primary) > 80 and _dist(accent, secondary) > 60 and _lum(accent) > 40:
                away_body = accent
                away_second = primary
            elif _lum(secondary) > 160:
                away_body = (248, 218, 36) if _lum(primary) < 120 else secondary
                away_second = primary
            else:
                away_body = _shift(secondary, 0.95)
                away_second = primary
            away_third = secondary
            away_shorts = primary if _lum(away_body) > 140 else secondary
            away_socks = away_body
            away_collar = away_second
        elif cycle == 2:
            away_body = (235, 228, 215) if _lum(primary) < 140 else (55, 62, 68)
            away_second = primary
            away_third = (210, 175, 75)
            away_shorts = away_body
            away_socks = away_body
            away_collar = primary
        else:
            away_body = (22, 26, 36)
            away_second = primary if _lum(primary) > 70 else accent
            away_third = secondary
            away_shorts = (22, 26, 36)
            away_socks = (22, 26, 36)
            away_collar = away_second

        macro_cand = ["solid", "ombre_fade", "half_half", "diagonal_sash", "solid"][(seed >> 5) % 5]
        micro_cand = POOL_LUXURY_JACQUARD[(seed + s_off * 11) % len(POOL_LUXURY_JACQUARD)] if macro_cand != "solid" else None
        mask_cand = ["full", "front_only", "sash_only", "sleeves_only"][(seed >> 7) % 4]

        return {
            "body": away_body,
            "second": away_second,
            "third": away_third,
            "pattern": pattern,
            "var": (seed >> 8) % 3,
            "width_step": (seed >> 11) % 8,
            "sleeve": away_body,
            "sleeve_style": "shoulder_stripe" if supplier == "adidas" else ["tipped", "raglan", "shoulder_stripe", "solid"][(seed >> 9) % 4],
            "shorts": away_shorts,
            "shorts_style": "three_stripes" if supplier == "adidas" else ["split_leg", "side_stripe", "hem_tape", "solid"][(seed >> 5) % 4],
            "shorts_accent": away_second,
            "socks": away_socks,
            "socks_style": ["calf_band", "turnover_hoop", "gradient_fade", "solid"][(seed >> 7) % 4],
            "socks_accent": away_second,
            "socks_tip": away_third,
            "collar": away_collar,
            "collar_tip": away_third,
            "cuff": away_second,
            "cuff_tip": away_third,
            "gradient": 1 if (seed % 2) else 0,
            "supplier": supplier,
            "vent_style": ["contrast_panel", "laser_cut", "stealth_rib", "none"][(seed >> 3) % 4],
            "macro_layout": macro_cand,
            "micro_jacquard": micro_cand,
            "pattern_mask": mask_cand,
            "tile_scale": 1.0,
            "finish": "standard",
        }

    else:
        # THIRD KIT: High-Fashion Streetwear & Lifestyle Culture (8 Mood Collections)
        cycle = (s_off + (seed % 8)) % 8
        third_body, third_second, third_third = generate_streetwear_palette(club, cycle + cid * 3 + seed)
        choices = POOL_THIRD_STREETWEAR
        default_idx = ((seed ^ (cid * 0x45D9F3B)) + s_off * 23) % len(choices)
        pattern = get_league_assigned_pattern(cid, 3, season, choices[default_idx], choices)

        third_shorts = third_body if ((seed >> 2) % 4 != 0) else third_second
        third_socks = third_body if ((seed >> 3) % 2 == 0) else third_second
        third_collar = third_second
        third_cuff = third_second

        macro_cand = ["solid", "ombre_fade", "chestband", "diagonal_sash", "solid"][(seed >> 7) % 5]
        micro_cand = POOL_LUXURY_JACQUARD[(seed + s_off * 7) % len(POOL_LUXURY_JACQUARD)] if macro_cand != "solid" else None
        mask_cand = ["sleeves_only", "front_only", "full", "sash_only"][(seed >> 9) % 4]
        finish_cand = ["standard", "liquid_gold", "chrome_silver", "copper_bronze", "blackout", "cyber_neon"][(seed >> 10) % 6]

        return {
            "body": third_body,
            "second": third_second,
            "third": third_third,
            "pattern": pattern,
            "var": (seed >> 8) % 3,
            "width_step": (seed >> 11) % 8,
            "sleeve": third_body,
            "sleeve_style": "shoulder_stripe" if supplier == "adidas" else ["tipped", "shoulder_stripe", "tipped", "raglan"][(seed >> 5) % 4],
            "shorts": third_shorts,
            "shorts_style": "three_stripes" if supplier == "adidas" else ["split_leg", "side_stripe", "hem_tape", "solid"][(seed >> 3) % 4],
            "shorts_accent": third_second if third_shorts == third_body else third_third,
            "socks": third_socks,
            "socks_style": ["turnover_hoop", "calf_band", "gradient_fade", "solid"][(seed >> 7) % 4],
            "socks_accent": third_second if third_socks == third_body else third_third,
            "socks_tip": third_third,
            "collar": third_collar,
            "collar_tip": third_third,
            "cuff": third_cuff,
            "cuff_tip": third_third,
            "gradient": [0, 1, 2, 3][(seed >> 2) % 4],
            "supplier": supplier,
            "vent_style": ["laser_cut", "contrast_panel", "stealth_rib"][(seed >> 5) % 3],
            "macro_layout": macro_cand,
            "micro_jacquard": micro_cand,
            "pattern_mask": mask_cand,
            "tile_scale": 1.0,
            "finish": finish_cand,
        }
