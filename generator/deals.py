"""Writes deals.txt (offers) and career.txt for the Lua module. UNTESTED IN GAME.

Money is stored in EUROS (integers), 50M-150M per year, and is credited to the
in-game transfer budget when a deal is signed (see KitGenerator.lua).

Offer sets are generated so that a club never sees the same brand two seasons
in a row: each season's set is drawn from the brands NOT offered to that club in
the previous season.
"""
import sys, uuid
from pathlib import Path
from kg_core import season_rng
from kit_gen import load_clubs

# yearly value per club tier, in EUROS (before +/-15% jitter)
BASE_EUR = {'small': 60_000_000, 'mid': 88_000_000, 'big': 135_000_000}


def make_offers(club, season, brands, count=5, exclude=None):
    rng = season_rng(club['id'], season, salt='deals-v3')
    exclude = set(exclude or ())
    pool = [b for b in brands if b not in exclude]
    if len(pool) < count:
        pool = list(brands)                       # fall back: never return < count
    picks = rng.sample(pool, min(count, len(pool)))
    out = []
    for i, b in enumerate(picks, 1):
        value = int(BASE_EUR[club['tier']] * rng.uniform(0.85, 1.15) / 100000) * 100000
        out.append({'offer': f"{club['id']}-{season}-{i}", 'brand': b, 'value': value,
                    'years': rng.choice([1, 2, 2, 3]), 'bonus': rng.choice([0, 5, 10]),
                    'tier': club['tier']})
    return out


def write(root, seasons):
    if isinstance(seasons, int):
        seasons = [seasons]
    seasons = list(seasons)
    clubs = load_clubs(root / 'generator' / 'clubs.csv')
    logo_dir = root / 'content' / 'KitGenerator' / 'logos'
    brands = sorted({p.stem for p in logo_dir.glob('*.png')
                     if not p.stem.endswith('_white') and not p.stem.startswith('_')})
    lines = ['# offer|season|club_id|brand|logo_file|value_per_year|years|bonus_pct|tier']
    n = 0
    prev = {c['id']: None for c in clubs}
    for season in seasons:
        for c in clubs:
            offers = make_offers(c, season, brands, exclude=prev.get(c['id']))
            for o in offers:
                lines.append('|'.join(str(x) for x in (o['offer'], season, c['id'], o['brand'],
                             f"logos/{o['brand']}.png", o['value'], o['years'], o['bonus'], o['tier'])))
                n += 1
            prev[c['id']] = {o['brand'] for o in offers}
    d = root / 'content' / 'KitGenerator'
    (d / 'deals.txt').write_text('\n'.join(lines) + '\n')
    cp = d / 'career.txt'
    if not cp.exists():
        # Initial offline placeholder; KitGenerator.lua automatically syncs this from live ML memory
        cp.write_text('ml_offline_init\n')
    print('wrote', d / 'deals.txt', n, 'offers across', len(seasons), 'season(s)')
    return brands


if __name__ == '__main__':
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 2027
    end = int(sys.argv[2]) if len(sys.argv) > 2 else start + 8
    write(Path(__file__).resolve().parent.parent, range(start, end + 1))
