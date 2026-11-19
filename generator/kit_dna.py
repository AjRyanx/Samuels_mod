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


def _sponsor_hash(s: Optional[str]) -> int:
    """Deterministic hash of sponsor string independent of Python's siphash randomization."""
    if not s:
        return 0
    return sum((i + 1) * ord(c) for i, c in enumerate(s))

# Keyed by team_id (PES 2021 / Football Life IDs).
# Slot 1 = Home, Slot 2 = Away, Slot 3 = Third.
BESPOKE_DNA: Dict[int, Dict[int, Dict[str, Any]]] = {
    # Manchester United
    100: {
        1: {  # Home: Iconic Manchester Red, white shorts, black socks, red/black collar trim
            "body": (195, 20, 30), "second": (250, 250, 250), "third": (20, 20, 25),
            "patterns": ["plain", "185-E", "041-E", "171-E", "067-E", "153-E"],
            "sleeve": (195, 20, 30), "shorts": (250, 250, 250),
            "socks": (20, 20, 25), "collar": (20, 20, 25), "cuff": (250, 250, 250),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: Iconic European Navy Blue heritage (1968/1993/2024) - clean, NO stripes
            "body": (28, 55, 115), "second": (250, 250, 250), "third": (195, 20, 30),
            "patterns": ["plain", "041-E", "171-E", "185-E", "141-E", "067-E"],
            "sleeve": (28, 55, 115), "shorts": (250, 250, 250),
            "socks": (28, 55, 115), "collar": (250, 250, 250), "cuff": (195, 20, 30),
            "gradient": 0, "supplier": "adidas",
        },
        3: {  # Third: Noir Luxury - matte black/charcoal with iridescent gold & crimson accents
            "body": (22, 24, 28), "second": (212, 175, 55), "third": (195, 20, 30),
            "patterns": ["plain", "141-E", "041-E", "171-E", "185-E", "044-B"],
            "sleeve": (22, 24, 28), "shorts": (22, 24, 28),
            "socks": (22, 24, 28), "collar": (212, 175, 55), "cuff": (212, 175, 55),
            "gradient": 1, "supplier": "adidas",
        },
    },

    # Arsenal
    101: {
        1: {  # Home: Canonical deep red body with crisp pure white sleeves + collar
            "body": (190, 22, 34), "second": (250, 250, 252), "third": (15, 32, 67),
            "patterns": ["plain", "171-E", "067-E", "041-E", "185-E"],
            "sleeve": (250, 250, 252), "shorts": (250, 250, 252),
            "socks": (250, 250, 252), "collar": (250, 250, 252),
            "cuff": (190, 22, 34),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: London Underground / Soundwave streetwear - blackout with electric volt
            "body": (18, 20, 22), "second": (205, 255, 0), "third": (30, 80, 180),
            "patterns": ["126-B", "001-B", "131", "044-B", "003-B", "082"],
            "sleeve": (18, 20, 22), "shorts": (18, 20, 22),
            "socks": (205, 255, 0), "collar": (205, 255, 0),
            "gradient": 1, "supplier": "adidas",
        },
        3: {  # Third: Modern high-fashion pastel lilac / sand couture
            "body": (215, 210, 230), "second": (15, 32, 67), "third": (190, 22, 34),
            "patterns": ["041-E", "044-B", "168-E", "046-E", "171-E"],
            "sleeve": (215, 210, 230), "shorts": (15, 32, 67),
            "socks": (215, 210, 230), "collar": (15, 32, 67),
            "gradient": 0, "supplier": "adidas",
        },
    },

    # Chelsea
    102: {
        1: {  # Home: Iconic Chelsea Royal Blue body & sleeves, blue/white shorts/socks, white/gold trim (strictly NO red, NO white sleeves, NO stripes)
            "body": (3, 70, 155), "second": (250, 250, 252), "third": (212, 175, 55),
            "patterns": ["plain", "185-E", "041-E", "067-E", "153-E", "171-E"],
            "sleeve": (3, 70, 155), "shorts": (3, 70, 155),
            "socks": (250, 250, 252), "collar": (3, 70, 155),
            "cuff": (250, 250, 252),
            "gradient": 0, "supplier": "nike",
        },
        2: {  # Away: Iconic Chelsea Canary Yellow heritage with royal blue trim (strictly NO stripes)
            "body": (252, 222, 0), "second": (3, 70, 155), "third": (18, 20, 24),
            "patterns": ["plain", "041-E", "141-E", "067-E", "185-E"],
            "sleeve": (252, 222, 0), "shorts": (3, 70, 155),
            "socks": (252, 222, 0), "collar": (3, 70, 155),
            "cuff": (3, 70, 155),
            "gradient": 0, "supplier": "nike",
        },
        3: {  # Third: Noir Luxury / Ice Mint couture with royal blue and liquid chrome
            "body": (20, 24, 32), "second": (30, 185, 170), "third": (3, 70, 155),
            "patterns": ["plain", "041-E", "044-B", "171-E", "185-E", "141-E"],
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
            "patterns": ["plain", "041-E", "067-E", "185-E", "171-E", "085-E"],
            "sleeve": (190, 18, 30), "shorts": (190, 18, 30),
            "socks": (190, 18, 30), "collar": (190, 18, 30),
            "cuff": (250, 250, 252),
            "gradient": 0, "supplier": "nike",
        },
        2: {  # Away: Heritage off-white & forest green / teal accents
            "body": (245, 245, 242), "second": (15, 65, 45), "third": (20, 20, 25),
            "patterns": ["plain", "041-E", "081", "088", "171-E"],
            "sleeve": (245, 245, 242), "shorts": (15, 65, 45),
            "socks": (245, 245, 242), "collar": (15, 65, 45),
            "cuff": (15, 65, 45),
            "gradient": 0, "supplier": "nike",
        },
        3: {  # Third: Noir Luxury / Royal Purple couture with iridescent gold
            "body": (32, 22, 42), "second": (212, 175, 55), "third": (190, 18, 30),
            "patterns": ["plain", "041-E", "171-E", "185-E", "044-B"],
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
            "patterns": ["plain", "167-E", "131-E", "067-E", "041-E", "085-E"],
            "sleeve": (108, 171, 221), "shorts": (250, 250, 250),
            "socks": (108, 171, 221), "collar": (250, 250, 250),
            "cuff": (250, 250, 250),
            "gradient": 0, "supplier": "puma",
            "sponsor_dark": (15, 30, 60),
        },
        2: {  # Away: Dark charcoal with neon yellow-green cyber accents
            "body": (25, 28, 35), "second": (215, 255, 0), "third": (108, 171, 221),
            "patterns": ["041-E", "003-B", "083", "082", "127-B", "044-B"],
            "sleeve": (25, 28, 35), "shorts": (25, 28, 35),
            "socks": (215, 255, 0), "collar": (215, 255, 0),
            "gradient": 1, "supplier": "puma",
        },
        3: {  # Third: Electric gradient / street art urban architecture
            "body": (18, 35, 65), "second": (255, 100, 180), "third": (0, 230, 215),
            "patterns": ["042", "044-B", "126-B", "043", "167-B"],
            "sleeve": (18, 35, 65), "shorts": (18, 35, 65),
            "socks": (255, 100, 180), "collar": (0, 230, 215),
            "gradient": 1, "supplier": "puma",
        },
    },

    # Aston Villa
    107: {
        1: {  # Home: Canonical claret body with sky blue sleeves (strictly preserved!)
            "body": (120, 24, 52), "second": (149, 191, 229), "third": (245, 245, 245),
            "patterns": ["plain", "085-E", "067-E", "171-E"],
            "sleeve": (149, 191, 229), "shorts": (245, 245, 245),
            "socks": (149, 191, 229), "collar": (149, 191, 229),
            "cuff": (120, 24, 52),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: Clean white with claret micro-stripes
            "body": (248, 248, 250), "second": (120, 24, 52), "third": (149, 191, 229),
            "patterns": ["083", "085", "088", "097"],
            "sleeve": (248, 248, 250), "shorts": (120, 24, 52),
            "socks": (248, 248, 250), "collar": (120, 24, 52),
            "gradient": 0, "supplier": "adidas",
        },
        3: {  # Third: Navy & gold streetwear
            "body": (18, 28, 48), "second": (210, 175, 75), "third": (149, 191, 229),
            "patterns": ["041-E", "044-B", "168-E", "006-E"],
            "sleeve": (18, 28, 48), "shorts": (18, 28, 48),
            "socks": (210, 175, 75), "collar": (210, 175, 75),
            "gradient": 0, "supplier": "adidas",
        },
    },

    # Tottenham Hotspur
    179: {
        1: {  # Home: Lilywhite body & sleeves with midnight navy shorts and socks
            "body": (250, 250, 252), "second": (19, 34, 64), "third": (250, 250, 252),
            "patterns": ["plain", "041-E", "067-E", "171-E", "185-E"],
            "sleeve": (250, 250, 252), "shorts": (19, 34, 64),
            "socks": (250, 250, 252), "collar": (19, 34, 64),
            "cuff": (19, 34, 64),
            "gradient": 0, "supplier": "nike",
            "sponsor_dark": (19, 34, 64),
        },
        2: {  # Away: Marine navy / iridescent purple streetwear
            "body": (22, 28, 60), "second": (130, 160, 220), "third": (250, 250, 252),
            "patterns": ["041-E", "044-B", "171-E"],
            "sleeve": (22, 28, 60), "shorts": (22, 28, 60),
            "socks": (22, 28, 60), "collar": (130, 160, 220),
            "gradient": 0, "supplier": "nike",
        },
        3: {  # Third: High-fashion mint / aqua couture with navy trim
            "body": (140, 220, 200), "second": (19, 34, 64), "third": (250, 250, 252),
            "patterns": ["042", "044-B", "126-B"],
            "sleeve": (140, 220, 200), "shorts": (19, 34, 64),
            "socks": (140, 220, 200), "collar": (19, 34, 64),
            "gradient": 1, "supplier": "nike",
        },
    },

    # Crystal Palace
    382: {
        1: {  # Home: Iconic Selhurst Red & Blue vertical stripes with gold eagle trim
            "body": (27, 69, 143), "second": (196, 18, 46), "third": (255, 204, 0),
            "patterns": ["081", "082", "088", "093", "083"],
            "sleeve": (27, 69, 143), "shorts": (27, 69, 143),
            "socks": (27, 69, 143), "collar": (255, 204, 0),
            "cuff": (196, 18, 46),
            "gradient": 0, "supplier": "macron",
        },
        2: {  # Away: Pristine Eagle White with dual red & blue sash
            "body": (250, 250, 252), "second": (27, 69, 143), "third": (196, 18, 46),
            "patterns": ["plain", "087", "036", "041-E"],
            "sleeve": (250, 250, 252), "shorts": (27, 69, 143),
            "socks": (250, 250, 252), "collar": (27, 69, 143),
            "cuff": (196, 18, 46),
            "gradient": 0, "supplier": "macron",
        },
        3: {  # Third: South London Gold / Electric Volt Streetwear
            "body": (245, 200, 30), "second": (27, 69, 143), "third": (196, 18, 46),
            "patterns": ["plain", "002-C", "067-E", "041-E"],
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
            "patterns": ["081", "082", "083", "088", "093"],
            "sleeve": (20, 20, 24), "shorts": (20, 20, 24),
            "socks": (20, 20, 24), "collar": (250, 250, 252),
            "cuff": (250, 250, 252),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: Heritage claret & navy hoops with gold accents
            "body": (90, 20, 35), "second": (15, 30, 60), "third": (210, 175, 75),
            "patterns": ["084", "091", "102"],
            "sleeve": (90, 20, 35), "shorts": (15, 30, 60),
            "socks": (90, 20, 35), "collar": (15, 30, 60),
            "gradient": 0, "supplier": "adidas",
        },
        3: {  # Third: Minimalist sand / forest green luxury
            "body": (246, 244, 235), "second": (15, 115, 75), "third": (20, 20, 24),
            "patterns": ["plain", "041-E", "171-E"],
            "sleeve": (246, 244, 235), "shorts": (246, 244, 235),
            "socks": (246, 244, 235), "collar": (15, 115, 75),
            "gradient": 0, "supplier": "adidas",
        },
    },

    # Real Madrid
    109: {
        1: {  # Home: Pristine all-white luxury with royal gold & navy trim, Carrara marble jacquard
            "body": (250, 250, 252), "second": (205, 168, 75), "third": (15, 25, 55),
            "patterns": ["plain", "041-E", "171-E", "168-E", "067-E", "085-E"],
            "sleeve": (250, 250, 252), "shorts": (250, 250, 252),
            "socks": (250, 250, 252), "collar": (250, 250, 252),
            "cuff": (205, 168, 75),
            "gradient": 0, "supplier": "adidas",
            "sponsor_dark": (15, 25, 55),
        },
        2: {  # Away: Vibrant royal purple / navy with refined luxury tonal patterns
            "body": (45, 15, 80), "second": (250, 250, 252), "third": (205, 168, 75),
            "patterns": ["plain", "002-C", "040-C", "067-E", "041-E", "168-E"],
            "sleeve": (45, 15, 80), "shorts": (45, 15, 80),
            "socks": (45, 15, 80), "collar": (250, 250, 252),
            "cuff": (205, 168, 75),
            "gradient": 0, "supplier": "adidas",
        },
        3: {  # Third: Haute Couture Noir - matte charcoal with metallic gold filigree
            "body": (20, 22, 26), "second": (215, 180, 80), "third": (250, 250, 252),
            "patterns": ["plain", "041-E", "170-E", "168-E", "067-E"],
            "sleeve": (20, 22, 26), "shorts": (20, 22, 26),
            "socks": (215, 180, 80), "collar": (215, 180, 80),
            "cuff": (215, 180, 80),
            "gradient": 0, "supplier": "adidas",
        },
    },

    # Barcelona
    108: {
        1: {  # Home: Iconic Blaugrana vertical stripes with Catalan micro-weave
            "body": (155, 15, 45), "second": (0, 75, 140), "third": (245, 195, 0),
            "patterns": ["081", "082", "088", "093", "083", "097", "118"],
            "sleeve": (0, 75, 140), "shorts": (0, 75, 140),
            "socks": (155, 15, 45), "collar": (245, 195, 0),
            "cuff": (245, 195, 0),
            "gradient": 0, "supplier": "nike",
        },
        2: {  # Away: Iconic Catalan Gold / Volt Senyera graphic
            "body": (245, 200, 30), "second": (155, 15, 45), "third": (0, 75, 140),
            "patterns": ["005", "022", "087", "095"],
            "sleeve": (245, 200, 30), "shorts": (0, 75, 140),
            "socks": (245, 200, 30), "collar": (155, 15, 45),
            "gradient": 0, "supplier": "nike",
        },
        3: {  # Third: High-fashion Mediterranean mint / aqua streetwear
            "body": (130, 225, 205), "second": (0, 75, 140), "third": (155, 15, 45),
            "patterns": ["041-E", "044-B", "043", "046-B", "171-E"],
            "sleeve": (130, 225, 205), "shorts": (0, 75, 140),
            "socks": (130, 225, 205), "collar": (0, 75, 140),
            "gradient": 0, "supplier": "nike",
        },
    },

    # Atletico Madrid
    172: {
        1: {  # Home: Iconic red & white vertical stripes with royal blue shorts
            "body": (205, 25, 35), "second": (250, 250, 250), "third": (15, 40, 100),
            "patterns": ["081", "082", "088", "093", "097", "118"],
            "sleeve": (205, 25, 35), "shorts": (15, 40, 100),
            "socks": (205, 25, 35), "collar": (15, 40, 100),
            "cuff": (15, 40, 100),
            "gradient": 0, "supplier": "nike",
        },
        2: {  # Away: Deep navy with neon turquoise / infrared trim
            "body": (15, 25, 55), "second": (0, 225, 210), "third": (205, 25, 35),
            "patterns": ["001-B", "003-B", "020", "044-B", "082"],
            "sleeve": (15, 25, 55), "shorts": (15, 25, 55),
            "socks": (0, 225, 210), "collar": (0, 225, 210),
            "gradient": 1, "supplier": "nike",
        },
        3: {  # Third: Vibrant volt & camouflage streetwear
            "body": (210, 245, 45), "second": (15, 25, 55), "third": (205, 25, 35),
            "patterns": ["004", "044-B", "008", "024"],
            "sleeve": (210, 245, 45), "shorts": (15, 25, 55),
            "socks": (210, 245, 45), "collar": (15, 25, 55),
            "gradient": 0, "supplier": "nike",
        },
    },

    # Juventus
    120: {
        1: {  # Home: Iconic black & white vertical stripes (brushstroke / modern zebra)
            "body": (20, 20, 22), "second": (250, 250, 252), "third": (210, 175, 75),
            "patterns": ["082", "083", "088", "093", "081", "097"],
            "sleeve": (20, 20, 22), "shorts": (250, 250, 252),
            "socks": (250, 250, 252), "collar": (210, 175, 75),
            "cuff": (210, 175, 75),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: Soft luxury pastel pink / cream with charcoal trim
            "body": (245, 205, 215), "second": (20, 20, 22), "third": (250, 250, 252),
            "patterns": ["041-E", "171-E", "085-E", "044-B"],
            "sleeve": (245, 205, 215), "shorts": (20, 20, 22),
            "socks": (245, 205, 215), "collar": (20, 20, 22),
            "gradient": 0, "supplier": "adidas",
        },
        3: {  # Third: Futuristic all-black with electric neon volt
            "body": (15, 16, 18), "second": (215, 255, 20), "third": (250, 250, 252),
            "patterns": ["042", "044-B", "126-B", "003-B", "127-B"],
            "sleeve": (15, 16, 18), "shorts": (15, 16, 18),
            "socks": (215, 255, 20), "collar": (215, 255, 20),
            "gradient": 1, "supplier": "adidas",
        },
    },

    # AC Milan
    121: {
        1: {  # Home: Rossoneri vertical red & black stripes with black shorts
            "body": (195, 20, 30), "second": (18, 18, 20), "third": (245, 245, 245),
            "patterns": ["082", "083", "088", "093", "081", "097"],
            "sleeve": (18, 18, 20), "shorts": (18, 18, 20),
            "socks": (18, 18, 20), "collar": (195, 20, 30),
            "cuff": (195, 20, 30),
            "gradient": 0, "supplier": "puma",
        },
        2: {  # Away: Crisp pure white with dual red/black trim
            "body": (250, 250, 252), "second": (195, 20, 30), "third": (18, 18, 20),
            "patterns": ["085", "083", "088", "041-E", "171-E"],
            "sleeve": (250, 250, 252), "shorts": (250, 250, 252),
            "socks": (250, 250, 252), "collar": (195, 20, 30),
            "gradient": 0, "supplier": "puma",
        },
        3: {  # Third: Milan Fashion Week streetwear - olive green / sand camouflage
            "body": (75, 85, 65), "second": (215, 185, 120), "third": (195, 20, 30),
            "patterns": ["044-B", "004", "041-E", "168-E", "008"],
            "sleeve": (75, 85, 65), "shorts": (75, 85, 65),
            "socks": (215, 185, 120), "collar": (215, 185, 120),
            "gradient": 1, "supplier": "puma",
        },
    },

    # Inter Milan
    119: {
        1: {  # Home: Nerazzurri royal blue & black stripes with Biscione scale texture
            "body": (10, 50, 145), "second": (16, 18, 22), "third": (210, 175, 65),
            "patterns": ["082", "083", "093", "088", "081"],
            "sleeve": (16, 18, 22), "shorts": (16, 18, 22),
            "socks": (10, 50, 145), "collar": (10, 50, 145),
            "cuff": (210, 175, 65),
            "gradient": 0, "supplier": "nike",
        },
        2: {  # Away: Pure white with undulating Biscione serpent wave graphic
            "body": (250, 250, 252), "second": (10, 50, 145), "third": (16, 18, 22),
            "patterns": ["043-B", "046-B", "044-B", "005-B", "085"],
            "sleeve": (250, 250, 252), "shorts": (250, 250, 252),
            "socks": (250, 250, 252), "collar": (10, 50, 145),
            "gradient": 0, "supplier": "nike",
        },
        3: {  # Third: High-fashion safety orange / cyber yellow
            "body": (245, 110, 20), "second": (10, 50, 145), "third": (16, 18, 22),
            "patterns": ["001-B", "020", "038", "042", "126-B"],
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
            "patterns": ["plain", "041-E", "170-E", "085-E", "067-E", "168-E"],
            "sleeve": (145, 20, 35), "shorts": (245, 175, 20),
            "socks": (145, 20, 35), "collar": (245, 175, 20),
            "cuff": (245, 175, 20),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: Roman marble white with subtle carmine/gold filigree
            "body": (248, 246, 242), "second": (145, 20, 35), "third": (245, 175, 20),
            "patterns": ["plain", "041-E", "170-E", "044-B", "168-E"],
            "sleeve": (248, 246, 242), "shorts": (145, 20, 35),
            "socks": (248, 246, 242), "collar": (145, 20, 35),
            "gradient": 0, "supplier": "adidas",
        },
        3: {  # Third: Blackout with vibrant neon infrared accents
            "body": (18, 18, 20), "second": (245, 175, 20), "third": (145, 20, 35),
            "patterns": ["042", "044-B", "003-B", "126-B"],
            "sleeve": (18, 18, 20), "shorts": (18, 18, 20),
            "socks": (245, 175, 20), "collar": (245, 175, 20),
            "gradient": 1, "supplier": "adidas",
        },
    },

    # Bayern Munich
    127: {
        1: {  # Home: Rot-Weiß crimson red with Bavarian diamond micro-jacquard
            "body": (210, 15, 35), "second": (250, 250, 252), "third": (15, 25, 55),
            "patterns": ["plain", "027-E", "033-E", "067-E", "085-E"],
            "sleeve": (210, 15, 35), "shorts": (210, 15, 35),
            "socks": (210, 15, 35), "collar": (250, 250, 252),
            "cuff": (250, 250, 252),
            "gradient": 0, "supplier": "adidas",
        },
        2: {  # Away: World map / digital geometric in deep black & ultraviolet
            "body": (18, 18, 24), "second": (160, 60, 230), "third": (0, 220, 200),
            "patterns": ["004", "044-B", "127-B", "001", "131"],
            "sleeve": (18, 18, 24), "shorts": (18, 18, 24),
            "socks": (160, 60, 230), "collar": (160, 60, 230),
            "gradient": 1, "supplier": "adidas",
        },
        3: {  # Third: Off-white / cream heritage luxury with burgundy/gold trim
            "body": (246, 244, 238), "second": (130, 20, 35), "third": (205, 168, 75),
            "patterns": ["plain", "041-E", "168-E", "171-E", "085-E"],
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
            "patterns": ["041-E", "044-B", "127-B", "171-E"],
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
            "patterns": ["042", "044-B", "126-B"],
            "sleeve": (20, 95, 160), "shorts": (20, 95, 160),
            "socks": (20, 95, 160), "collar": (250, 250, 252),
            "gradient": 1, "supplier": "puma",
        },
    },

    # PSG
    114: {
        1: {  # Home: Iconic Hechter central vertical red stripe framed by white on midnight navy
            "body": (15, 25, 55), "second": (210, 20, 35), "third": (250, 250, 252),
            "patterns": ["094", "086", "098", "085-E", "041-E"],
            "sleeve": (15, 25, 55), "shorts": (15, 25, 55),
            "socks": (15, 25, 55), "collar": (210, 20, 35),
            "cuff": (250, 250, 252),
            "gradient": 0, "supplier": "nike",
        },
        2: {  # Away: Crisp pure white with gradient Hechter stripe
            "body": (250, 250, 252), "second": (15, 25, 55), "third": (210, 20, 35),
            "patterns": ["094", "086", "082", "041-E"],
            "sleeve": (250, 250, 252), "shorts": (250, 250, 252),
            "socks": (250, 250, 252), "collar": (15, 25, 55),
            "gradient": 0, "supplier": "nike",
        },
        3: {  # Third: Jordan Collab streetwear - elephant print / earth tones / soft pink
            "body": (45, 42, 40), "second": (235, 170, 180), "third": (250, 250, 252),
            "patterns": ["044-B", "041-E", "004", "168-E", "042"],
            "sleeve": (45, 42, 40), "shorts": (45, 42, 40),
            "socks": (235, 170, 180), "collar": (235, 170, 180),
            "gradient": 1, "supplier": "nike",
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
            "patterns": ["041-E", "027-B", "033", "044-B", "131"],
            "sleeve": (22, 28, 42), "shorts": (22, 28, 42),
            "socks": (100, 215, 210), "collar": (100, 215, 210),
            "gradient": 1, "supplier": "adidas",
        },
        3: {  # Third: Bob Marley reggae tribute / Amsterdam street culture
            "body": (18, 18, 20), "second": (245, 205, 30), "third": (20, 160, 60),
            "patterns": ["083", "085", "005-B", "041-E", "044-B"],
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
            "patterns": ["041-E", "169-E", "044-B", "171-E"],
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
            "patterns": ["041-E", "169-E", "044-B", "171-E"],
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
            "patterns": ["001-B", "044-B", "042", "127-B"],
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
            "patterns": ["001-B", "044-B", "042", "127-B"],
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
            "patterns": ["005-B", "022-B", "041-E", "044-B"],
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
            "patterns": ["005-B", "022-B", "041-E", "044-B"],
            "sleeve": (18, 18, 20), "shorts": (18, 18, 20),
            "socks": (210, 20, 30), "collar": (210, 20, 30),
            "gradient": 1, "supplier": "adidas",
        },
    },
}


# --------------------------------------------------------------------------- #
#  Dynamic DNA Archetype Classification for ANY of the 580+ other clubs
# --------------------------------------------------------------------------- #
# High-Fashion Pattern Pools for General Clubs:
# Modern Stripe Archetypes
POOL_STRIPES = ["081", "082", "083", "088", "092", "093", "097", "105", "118", "124"]
# Modern Hoops Archetypes
POOL_HOOPS = ["084", "091", "102", "114"]
# Modern Sash / Band Archetypes
POOL_SASH = ["005", "022", "095", "103", "113", "119"]
# 2026 High-End Luxury Tonal Jacquards (Elevates solid shirts to $150 authentic fashion pieces!)
POOL_LUXURY_JACQUARD = [
    "plain",  # Iconic Solid Clean
    "041-E",  # Carrara Marble
    "171-E",  # Houndstooth Luxury Weave
    "044-E",  # Topographic Contour
    "168-E",  # Art Deco Fan
    "067-E",  # Woven Diamond Lattice
    "006-E",  # Obsidian Splinter Micro-Facet
    "001-E",  # Apex Shatter Tonal Jacquard
    "185-E",  # Luxury Micro-Weave
    "170-E",  # Rose Window Micro-Filigree
    "046-E",  # Silk Wave
]
# Modern Angular & Kinetic Away Patterns
POOL_AWAY_GEOMETRIC = [
    "001", "002", "003", "008", "010", "017", "020", "024", "029",
    "082", "083", "085", "041-E"
]
# High-Fashion Streetwear / Lifestyle Third Kit Patterns
POOL_THIRD_STREETWEAR = [
    "041", "042", "043", "044-B", "046-B",
    "126-B", "127-B", "131",
    "166-B", "167-B", "169-E", "171-E", "204-B"
]

# Keywords that indicate traditional kit identity
RE_STRIPES = re.compile(
    r"\b(albion|athletic|atletico|crystal palace|palace|sunderland|southampton|stoke|porto|espanyol|"
    r"betis|malaga|huesca|alaves|girona|granada|almeria|rayo|sparta|feyenoord|"
    r"psv|olympiacos|fenerbahce|besiktas|trabzonspor|gremio|fluminense|botafogo|"
    r"atletico mineiro|chivas|necaxa|monterrey)\b",
    re.IGNORECASE,
)
RE_HOOPS = re.compile(
    r"\b(celtic|sporting|qpr|reading|doncaster|flamengo|sport recife)\b",
    re.IGNORECASE,
)
RE_SASH = re.compile(
    r"\b(rayo|vallecano|vasco|river|bordeaux|puebla)\b",
    re.IGNORECASE,
)


def classify_club_dna(club: Dict[str, Any]) -> str:
    """Classify a club's canonical design archetype based on name and profile."""
    name = str(club.get("name", ""))
    if RE_HOOPS.search(name):
        return "HOOPS"
    if RE_SASH.search(name):
        return "SASH"
    if RE_STRIPES.search(name):
        return "STRIPES"
    return "LUXURY_SOLID"


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


def get_club_style(club: Dict[str, Any], slot: int, season: int, sponsor: Optional[str] = None) -> Dict[str, Any]:
    """Return a complete, fashion-forward 2026 styling dict for club + slot + season."""
    cid = int(club.get("id") or club.get("team_id", 0))
    cname = str(club.get("name", ""))
    supplier = get_club_supplier(cid, cname)

    # Check bespoke curated DNA first
    if cid in BESPOKE_DNA and slot in BESPOKE_DNA[cid]:
        base_style = dict(BESPOKE_DNA[cid][slot])
        if "supplier" not in base_style:
            base_style["supplier"] = supplier
        pool = base_style.pop("patterns", None)
        if pool:
            if not sponsor:
                base_style["pattern"] = pool[0]
            else:
                choices = [x for x in pool if x != pool[0]] or pool
                # Deterministic pick per season
                idx = (season + _sponsor_hash(sponsor)) % len(choices)
                base_style["pattern"] = choices[idx]
        return base_style

    # Dynamic Classification for any of the other 580+ clubs
    archetype = classify_club_dna(club)
    primary = _hexc(club.get("primary", "#034694"))
    secondary = _hexc(club.get("secondary", "#FFFFFF"))
    accent = _hexc(club.get("accent", "#C8102E"))

    salt_val = (cid * 31 + season * 7 + _sponsor_hash(sponsor))

    if slot == 1:
        # HOME KIT: Respect iconic identity, elevate with luxury tailoring
        if archetype == "STRIPES":
            pool = POOL_STRIPES
            pattern = pool[salt_val % len(pool)]
        elif archetype == "HOOPS":
            pool = POOL_HOOPS
            pattern = pool[salt_val % len(pool)]
        elif archetype == "SASH":
            pool = POOL_SASH
            pattern = pool[salt_val % len(pool)]
        else:
            # Luxury Solid: High-end tonal micro-jacquards
            pool = POOL_LUXURY_JACQUARD
            pattern = pool[salt_val % len(pool)]

        return {
            "body": primary,
            "second": secondary,
            "third": accent,
            "pattern": pattern,
            "sleeve": primary,
            "shorts": secondary if _lum(primary) < 140 else primary,
            "socks": primary,
            "collar": secondary,
            "cuff": secondary,
            "gradient": 0,
            "supplier": supplier,
        }

    elif slot == 2:
        # AWAY KIT: Modern kinetic geometry with contrasting / inverted palette
        pool = POOL_AWAY_GEOMETRIC
        pattern = pool[salt_val % len(pool)]
        # Away body usually secondary or clean off-white
        away_body = secondary if _lum(secondary) > 180 or _lum(primary) < 100 else _shift(secondary, 0.95)
        away_second = primary

        return {
            "body": away_body,
            "second": away_second,
            "third": accent,
            "pattern": pattern,
            "sleeve": away_body,
            "shorts": away_second if _lum(away_body) > 150 else away_body,
            "socks": away_body,
            "collar": away_second,
            "cuff": away_second,
            "gradient": 1 if salt_val % 2 else 0,
            "supplier": supplier,
        }

    else:
        # THIRD KIT: High-Fashion Streetwear / Lifestyle Culture
        pool = POOL_THIRD_STREETWEAR
        pattern = pool[salt_val % len(pool)]

        # Lifestyle palette variations: Noir blackout, Sand/Sage, or Cyber Neon
        mood = salt_val % 3
        if mood == 0:
            # Noir Luxury: Obsidian/Charcoal with Metallic Gold/Accent
            third_body = (20, 22, 26)
            third_second = accent if _lum(accent) > 100 else (210, 175, 75)
            third_third = primary
        elif mood == 1:
            # Earthy / Sand Dune / Sage Couture
            third_body = (235, 230, 220) if _lum(primary) < 140 else (60, 70, 65)
            third_second = primary
            third_third = accent
        else:
            # Cyber / Electric Radiant Streetwear
            third_body = (18, 25, 45)
            third_second = (0, 225, 210) if salt_val % 2 else (255, 90, 160)
            third_third = secondary

        return {
            "body": third_body,
            "second": third_second,
            "third": third_third,
            "pattern": pattern,
            "sleeve": third_body,
            "shorts": third_body,
            "socks": third_second,
            "collar": third_second,
            "cuff": third_second,
            "gradient": 1,
            "supplier": supplier,
        }
