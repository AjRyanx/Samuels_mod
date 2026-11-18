"""Shared logic: seeded choices, colour check, counter-offer rule.
UNTESTED IN GAME. The hash/roll here must stay bit-identical to KitGenerator.lua."""
import hashlib, random

def season_rng(club_id, season, salt='kitgen-v1'):
    d = hashlib.sha256(f'{salt}:{season}:{club_id}'.encode()).digest()
    return random.Random(int.from_bytes(d[:8], 'little'))

def pick_design(rng):
    return {'layout': rng.randrange(24), 'stripe_width': rng.randrange(8),
            'overlay': rng.randrange(12), 'trim': rng.randrange(6),
            'gradient': rng.randrange(4)}

def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def oklab(rgb):
    r, g, b = (_lin(v) for v in rgb)
    l = (0.4122214708*r + 0.5363325363*g + 0.0514459929*b) ** (1/3)
    m = (0.2119034982*r + 0.6806995451*g + 0.1073969566*b) ** (1/3)
    s = (0.0883024619*r + 0.2817188376*g + 0.6299787005*b) ** (1/3)
    return (0.2104542553*l + 0.7936177850*m - 0.0040720468*s,
            1.9779984951*l - 2.4285922050*m + 0.4505937099*s,
            0.0259040371*l + 0.7827717662*m - 0.8086757660*s)

def color_dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(oklab(a), oklab(b))) ** 0.5

def near_anchor(body, anchor, max_dist=0.06):
    return color_dist(body, anchor) <= max_dist

def jitter_body(rng, anchor, max_dist=0.06):
    """small colour variation that stays recognisably the club's colour"""
    for _ in range(12):
        c = tuple(max(0, min(255, v + rng.randint(-18, 18))) for v in anchor)
        if near_anchor(c, anchor, max_dist):
            return c
    return tuple(anchor)

# ---- deterministic roll shared with Lua (plain arithmetic, no bit ops) ----
def h32(s):
    h = 5381
    for ch in s.encode():
        h = (h * 33 + ch) % 4294967296
    return h

def roll(career, season, offer_id, step):
    return (h32(f'{career}:{season}:{offer_id}:{step}') % 10000) / 10000

TIER = {'small': 0.8, 'mid': 1.0, 'big': 1.2}
ASK_PCT = {'value': 0.15, 'years': 0.08, 'bonus': 0.20, 'split': 0.0}   # tuning guesses

def counter_reply(career, season, offer_id, tier, ask_pct, step):
    p = (0.70 - 2.0 * ask_pct - 0.15 * (step - 1)) * TIER[tier]
    p = max(0.05, min(0.90, p))
    r = roll(career, season, offer_id, step)
    if r < p:
        return 'accept'
    if r < p + 0.30:
        return 'halfway'
    return 'withdraw'
