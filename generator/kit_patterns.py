#!/usr/bin/env python3
"""kit_patterns.py - the "Modern Football Kit Pattern & Style Taxonomy".

Implements the 205 base archetypes from
``modern_football_kit_pattern_catalog_taxonomy.md`` (codes ``001``..``205``)
plus the 5 structural placement/rendering modifiers (``-A``..``-E``).  A pattern
spec is a code optionally suffixed with a modifier::

    "001"      Apex Shatter, plain
    "001-C"    Apex Shatter, hem-up fade
    "083-D"    Barcode Stripes, diagonal sash mask

Every archetype is registered in :data:`CATALOG` (code -> name/category/fn), so
the catalog is fully addressable.  Drawing happens on the same ``W x H`` canvas
the rest of the generator uses (``kit_gen.W`` / ``kit_gen.H``), so the output
plugs straight into the existing UV pipeline.

A renderer paints onto a *transparent* overlay using only the three kit colours
(body / second / third) and shades of them, so a pattern is always on-club and
the modifiers (fade / mask / tonal) can post-process its alpha.

Public API
----------
    draw(img, spec, body, second, third=None, var=0, ws=0, rng=None) -> img
        Paint ``spec`` (e.g. "127-B") onto ``img`` (RGBA).
    is_code(spec) -> bool
    list_catalog() -> [(code, name, category), ...]
    codes() -> [code, ...]
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

W, H = 480, 500

# --------------------------------------------------------------------------- #
#  colour helpers
# --------------------------------------------------------------------------- #
def _shade(c, f):
    return tuple(max(0, min(255, int(round(v * f)))) for v in c)


def _mix(a, b, t):
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3))


def _lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _is_dark(c):
    return _lum(c) < 128


def _alpha(col, a):
    return tuple(col) + (int(max(0, min(255, a))),)


# --------------------------------------------------------------------------- #
#  draw primitives
# --------------------------------------------------------------------------- #
def _poly(d, pts, col, a=255):
    pts = [(float(x), float(y)) for x, y in pts]
    if len(pts) >= 3:
        d.polygon(pts, fill=_alpha(col, a))


def _rect(d, box, col, a=255):
    d.rectangle([float(v) for v in box], fill=_alpha(col, a))


def _line(d, pts, col, w=1, a=255):
    pts = [(float(x), float(y)) for x, y in pts]
    if len(pts) == 1:
        pts = pts * 2
    d.line(pts, fill=_alpha(col, a), width=max(1, int(round(w))), joint="curve")


def _ell(d, box, col, a=255):
    d.ellipse([float(v) for v in box], fill=_alpha(col, a))


def _ring(d, cx, cy, r, col, w=2, a=255):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=_alpha(col, a),
              width=max(1, int(round(w))))


def _dot(d, cx, cy, r, col, a=255):
    if r > 0.3:
        _ell(d, [cx - r, cy - r, cx + r, cy + r], col, a)


def _star(d, cx, cy, r, col, points=4, inner=0.32, rot=0.0, a=255):
    pts = []
    for k in range(points * 2):
        rr = r if k % 2 == 0 else r * inner
        ang = rot + math.pi * k / points
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    _poly(d, pts, col, a)


# --------------------------------------------------------------------------- #
#  parameter bundle passed to every renderer
# --------------------------------------------------------------------------- #
class P:
    __slots__ = ("body", "second", "third", "var", "ws", "w", "h", "rng",
                 "lo", "hi", "mid")

    def __init__(self, body, second, third, var, ws, rng):
        self.body = tuple(body)
        self.second = tuple(second)
        self.third = tuple(third) if third else _shade(tuple(second), 0.70)
        self.var = int(var or 0)
        self.ws = int(ws or 0)
        self.w, self.h = W, H
        self.rng = rng if rng is not None else random.Random(1000 + self.var)
        self.lo = _shade(self.body, 0.78)
        self.hi = _shade(self.body, 1.20)
        self.mid = _mix(self.body, self.second, 0.5)


# --------------------------------------------------------------------------- #
#  generic helpers used by many renderers
# --------------------------------------------------------------------------- #
def _tiles(p, cw, ch, fn, gap=0.0, stagger=False):
    """Call fn(x, y, ix, iy) over a tiling that overflows every edge."""
    iy = 0
    y = -ch
    while y < p.h + ch:
        off = (cw + gap) / 2.0 if (stagger and iy % 2) else 0.0
        x = -cw + off
        ix = 0
        while x < p.w + cw:
            fn(x, y, ix, iy)
            x += cw + gap
            ix += 1
        y += ch + gap
        iy += 1


def _stipple(d, p, n, rmin, rmax, col, a=200, alt=None):
    r = p.rng
    for _ in range(int(n)):
        c = alt if (alt and r.random() < 0.5) else col
        _dot(d, r.uniform(0, p.w), r.uniform(0, p.h), r.uniform(rmin, rmax),
             c, r.randint(max(40, a - 80), a))


def _grad_strip(d, p, col, vertical, steps=None, a=120):
    steps = steps or (p.h if not vertical else p.w)
    n = max(2, int(steps))
    for i in range(n):
        t = i / (n - 1)
        c = _mix(col, p.third, t)
        if vertical:
            _rect(d, [i * p.w / n, 0, (i + 1) * p.w / n + 1, p.h], c, a)
        else:
            _rect(d, [0, i * p.h / n, p.w, (i + 1) * p.h / n + 1], c, a)


# =========================================================================== #
#  Category 1 - Geometric & Angular Shards (001-045)
# =========================================================================== #
def f_shards(p, d, img, n=24, from_hem=True, asym=False):
    """Refined architectural micro-facet geometric structure with calm chest sponsor zone."""
    r = p.rng
    step_y = p.h / 14.0
    step_x = p.w / 10.0
    for row in range(14):
        y = row * step_y
        # Keep chest sponsor zone calm (y between 30% and 55% of height)
        if 0.30 * p.h < y < 0.55 * p.h:
            continue
        shift = (step_x * 0.5) if (row % 2 == 1) else 0.0
        for col in range(-1, 11):
            x = col * step_x + shift + r.uniform(-2, 2)
            w = step_x * 0.85
            h = step_y * 0.70
            col_tone = p.second if r.random() < 0.75 else p.third
            alpha = int(r.uniform(40, 110))
            _poly(d, [(x, y), (x + w * 0.6, y), (x + w, y + h), (x + w * 0.4, y + h)], col_tone, alpha)


def f_prism(p, d, img, n=18, w=90, gap=30, slant=120, a1=105, a2=80):
    for i in range(-4, n):
        x = i * (w + gap)
        _poly(d, [(x, 0), (x + w, 0), (x + w + slant, p.h), (x + slant, p.h)], p.second, a1)
        _poly(d, [(x + w * 0.45, 0), (x + w * 0.75, 0),
                  (x + w * 0.75 + slant, p.h), (x + w * 0.45 + slant, p.h)], p.third, a2)


def f_vshards(p, d, img, n=7, width=0.6, thick=26):
    for i in range(n):
        y = p.h * 0.10 + i * p.h * 0.11
        w = p.w * width * (0.6 + 0.06 * i)
        _poly(d, [(p.w / 2 - w / 2, y), (p.w / 2, y + p.h * 0.09),
                  (p.w / 2 + w / 2, y), (p.w / 2 + w / 2 - thick, y),
                  (p.w / 2, y + p.h * 0.09 - thick), (p.w / 2 - w / 2 + thick, y)],
              p.second)


def f_lowpoly(p, d, img, cell=76, spread=0.16, mono=False):
    r = p.rng
    def tri(x, y, ix, iy):
        f = 1.0 + r.uniform(-spread, spread)
        c = p.body if mono else _shade(p.second, f)
        c2 = _shade(p.body, f) if mono else _shade(p.second, f * 0.86)
        _poly(d, [(x, y), (x + cell, y), (x + cell / 2, y + cell)], c)
        _poly(d, [(x, y), (x + cell / 2, y + cell), (x, y + cell)], c2)
    _tiles(p, cell, cell, tri)


def f_slashes(p, d, img, step=70, thick=16, angles=(35, 55), a=255):
    for i in range(-6, 16):
        x = i * step
        t = math.radians(angles[i % len(angles)])
        _line(d, [(x, 0), (x + p.h / math.tan(t), p.h)], p.second, thick, a)


def f_bauhaus(p, d, img):
    """Refined modernist architectural geometric framing with calm chest sponsor zone."""
    w, h = p.w, p.h
    # Tonal modernist diagonal accents outside sponsor zone
    _poly(d, [(0, 0), (w * 0.35, 0), (0, h * 0.26)], p.second, 50)
    _poly(d, [(w, 0), (w * 0.65, 0), (w, h * 0.26)], p.third, 45)
    _poly(d, [(0, h), (w * 0.45, h), (0, h * 0.62)], p.third, 50)
    _poly(d, [(w, h), (w * 0.55, h), (w, h * 0.62)], p.second, 50)
    # Sleek 1px architectural alignment lines
    _line(d, [(0, h * 0.26), (w, h * 0.26)], p.second, 1.0, 65)
    _line(d, [(0, h * 0.62), (w, h * 0.62)], p.third, 1.0, 65)


def f_diamonds(p, d, img, cw=96, ch=66, gap=16, compress=True):
    iy = 0
    y = 0
    while y < p.h + ch:
        c = cw * (1 - 0.35 * (y / p.h)) if compress else cw
        x = -c
        while x < p.w + c:
            _poly(d, [(x, y), (x + c / 2, y + ch / 2), (x, y + ch), (x - c / 2, y + ch / 2)],
                  p.second)
            x += c + gap
        y += ch + gap
        iy += 1


def f_creases(p, d, img, n=6, a=255):
    for i in range(n):
        y = i * p.h / n
        _poly(d, [(0, y), (p.w, y), (p.w, y + p.h / (2 * n)), (0, y + p.h / (2 * n))],
              p.second if i % 2 else p.hi, a)
        _line(d, [(0, y), (p.w, y)], p.third, 2, 200)


def f_isocubes(p, d, img, s=78):
    def cube(x, y, ix, iy):
        off = (s // 2) if iy % 2 else 0
        cx, cy = x + off, y
        _poly(d, [(cx, cy - s / 2), (cx + s / 2, cy - s / 4), (cx, cy), (cx - s / 2, cy - s / 4)], p.second)
        _poly(d, [(cx - s / 2, cy - s / 4), (cx, cy), (cx, cy + s / 2), (cx - s / 2, cy + s / 4)], _shade(p.second, 0.8))
        _poly(d, [(cx + s / 2, cy - s / 4), (cx, cy), (cx, cy + s / 2), (cx + s / 2, cy + s / 4)], _shade(p.second, 1.15))
    _tiles(p, s, s, cube)


def f_chevfrac(p, d, img, rows=6, cw=120, ch=76, gap=30):
    for i in range(rows):
        y = 40 + i * ch
        for k in range(-1, 5):
            x = k * cw + (gap if i % 2 else 0)
            _poly(d, [(x, y), (x + cw / 2, y + 34), (x + cw, y), (x + cw, y + 18),
                      (x + cw / 2, y + 52), (x, y + 18)], p.second)


def f_hexgrid(p, d, img, rad=30, gap=6, octa=False, a=225, solid=0):
    if octa:
        def oct_(x, y, ix, iy):
            off = (rad * 1.5) if iy % 2 else 0
            cx, cy = x + off, y
            rr = rad * 1.2
            pts = [(cx - rr, cy - rr * 0.42), (cx - rr * 0.42, cy - rr), (cx + rr * 0.42, cy - rr),
                   (cx + rr, cy - rr * 0.42), (cx + rr, cy + rr * 0.42), (cx + rr * 0.42, cy + rr),
                   (cx - rr * 0.42, cy + rr), (cx - rr, cy + rr * 0.42)]
            _line(d, pts + [pts[0]], p.second, 3, a)
        _tiles(p, rad * 3, rad * 3, oct_)
        return
    vstep = math.sqrt(3) * rad
    hstep = rad * 1.5
    iy = 0
    y = -vstep
    while y < p.h + vstep:
        x = -vstep
        ix = 0
        while x < p.w + vstep:
            off = vstep / 2 if ix % 2 else 0
            cx, cy = x + off, y
            pts = [(cx + rad * math.cos(math.radians(60 * k)),
                    cy + rad * math.sin(math.radians(60 * k))) for k in range(6)]
            if solid and (ix + iy) % solid == 0:
                _poly(d, pts, p.second, a)
            else:
                _line(d, pts + [pts[0]], p.second, 2, a)
            x += hstep + gap
            ix += 1
        y += vstep + gap
        iy += 1


def f_mosaic(p, d, img, n=46, a=235):
    r = p.rng
    pts = [(r.uniform(0, p.w), r.uniform(0, p.h)) for _ in range(n)]
    for x, y in pts:
        near = sorted(pts, key=lambda q: (q[0] - x) ** 2 + (q[1] - y) ** 2)[1:4]
        for nx, ny in near:
            _poly(d, [(x, y), (nx, ny), ((x + nx) / 2, (y + ny) / 2)],
                  _shade(p.second, r.uniform(0.7, 1.25)), a)
    for x, y in pts:
        near = sorted(pts, key=lambda q: (q[0] - x) ** 2 + (q[1] - y) ** 2)[1:4]
        for nx, ny in near:
            _line(d, [(x, y), (nx, ny)], p.third, 1, 150)


def f_arrows(p, d, img, bands=6, s=64, lean=0.5):
    for b in range(bands):
        y = p.h * (b + 0.5) / bands
        x = -20
        while x < p.w:
            _poly(d, [(x, y - 15), (x + s * lean, y), (x, y + 15), (x + s * 0.3, y)], p.second)
            x += s


def f_pillars(p, d, img, jitter=0.4, angle=14):
    """Architectural vertical fluted columns with tonal gradient and calm chest zone."""
    step = p.w / 9.0
    for i in range(9):
        x = i * step + step * 0.2
        w = step * 0.6
        # Top segment (shoulders/collar)
        _rect(d, [x, 0, x + w, p.h * 0.26], p.second, 55)
        _line(d, [(x, 0), (x, p.h * 0.26)], p.third, 1.5, 80)
        _line(d, [(x + w, 0), (x + w, p.h * 0.26)], p.third, 1.5, 80)
        # Bottom segment (torso hem)
        _rect(d, [x, p.h * 0.60, x + w, p.h], p.second, 55)
        _line(d, [(x, p.h * 0.60), (x, p.h)], p.third, 1.5, 80)
        _line(d, [(x + w, p.h * 0.60), (x + w, p.h)], p.third, 1.5, 80)


def f_radial(p, d, img, arms=20, r0=30, r1=260, spread=7, cx=0.5, cy=0.42):
    cx, cy = p.w * cx, p.h * cy
    for k in range(arms):
        a = math.radians(k * 360 / arms)
        w = math.radians(spread)
        rr = r1 + (k % 3) * 0.28 * r1
        _poly(d, [(cx + r0 * math.cos(a), cy + r0 * math.sin(a)),
                  (cx + rr * math.cos(a - w), cy + rr * math.sin(a - w)),
                  (cx + rr * math.cos(a + w), cy + rr * math.sin(a + w))], p.second)


def f_zigzag(p, d, img, x0=20, amp=22, period=60, thick=14, step=60):
    for x in range(int(x0), p.w, int(step)):
        pts = []
        y = -period
        while y < p.h + period:
            pts.append((x, y))
            pts.append((x + amp, y + period / 2))
            y += period
        _line(d, pts, p.second, thick)


def f_cubist(p, d, img, n=22):
    """Refined tonal architectural low-poly facets with calm chest sponsor zone."""
    r = p.rng
    for _ in range(n):
        cx, cy = r.uniform(0, p.w), r.uniform(0, p.h)
        if 0.28 * p.h < cy < 0.58 * p.h:
            continue
        s = r.uniform(0.06, 0.16) * p.w
        _poly(d, [(cx, cy), (cx + s, cy + r.uniform(-15, 15)),
                  (cx + r.uniform(-15, 30), cy + s)],
              _shade(p.second, r.uniform(0.85, 1.15)), 45)


def f_stars4(p, d, img, s=48, r=12, a=45):
    """Delicate geometric micro-diamond lattice with calm chest sponsor zone."""
    def st(x, y, ix, iy):
        cx = x + (s / 2 if iy % 2 else 0)
        cy = y
        if 0.28 * p.h < cy < 0.56 * p.h:
            return
        # Subtle micro-diamond accent
        _poly(d, [(cx, cy - 3), (cx + 3, cy), (cx, cy + 3), (cx - 3, cy)], p.second, a)
        _dot(d, cx, cy, 1.0, p.third, max(20, a - 15))
    _tiles(p, s, s, st)


def f_facets(p, d, img, n=30, mono=True, spread=0.22):
    r = p.rng
    for _ in range(n):
        cx, cy = r.uniform(0, p.w), r.uniform(0, p.h)
        s = r.uniform(0.12, 0.32) * p.w
        base = p.body if mono else p.second
        _poly(d, [(cx, cy), (cx + s, cy), (cx + s * 0.7, cy + s)],
              _shade(base, r.uniform(1 - spread, 1 + spread)), 200)


def f_rhombus(p, d, img, s=58):
    def rh(x, y, ix, iy):
        off = s / 2 if iy % 2 else 0
        _poly(d, [(x + off + s / 2, y), (x + off + s, y + s / 2),
                  (x + off + s / 2, y + s), (x + off, y + s / 2)], p.lo)
        _poly(d, [(x + off + s / 2, y + 3), (x + off + s - 3, y + s / 2),
                  (x + off + s / 2, y + s - 3), (x + off + 3, y + s / 2)], p.second)
    _tiles(p, s, s, rh)


def f_beams(p, d, img, step=80, thick=3):
    for i in range(-6, 16):
        x = i * step
        _line(d, [(x, 0), (x + p.h, p.h)], p.third, thick)
        _line(d, [(x, 0), (x - p.h, p.h)], p.second, max(2, thick - 1))


def f_tangram(p, d, img):
    """Modern angular geometric interlocking tessellation."""
    step = min(p.w, p.h) * 0.10
    for y in range(0, int(p.h), int(step)):
        for x in range(0, int(p.w), int(step)):
            if (x // int(step) + y // int(step)) % 2 == 0:
                _poly(d, [(x, y), (x + step, y), (x, y + step)], p.second, 70)
            else:
                _poly(d, [(x + step, y), (x + step, y + step), (x, y + step)], p.third, 70)


def f_peaks(p, d, img, bands=4):
    """Subtle tonal horizon chevron layers with calm sponsor zone."""
    for b in range(bands):
        y = p.h * (0.62 + b * 0.10)
        pts = [(0, y), (p.w * 0.5, y - 25), (p.w, y), (p.w, p.h), (0, p.h)]
        _poly(d, pts, p.second if b % 2 else _shade(p.second, 0.9), 45)


def f_sash_slices(p, d, img, n=15, width=0.32, off=10):
    for i in range(n):
        y = i * p.h / n
        x = i * off
        _poly(d, [(x, y), (x + width * p.w, y),
                  (x + width * p.w - 40, y + p.h / n), (x - 40, y + p.h / n)], p.second)


def f_dust(p, d, img, n=340, s0=4, s1=12, fade=True):
    r = p.rng
    for _ in range(n):
        y = (r.random() ** 0.6) * p.h if fade else r.uniform(0, p.h)
        x = r.uniform(0, p.w)
        s = r.uniform(s0, s1) * (1 - y / p.h + 0.25)
        a = int(200 * (1 - y / p.h) + 40) if fade else 210
        _poly(d, [(x, y), (x + s, y), (x + s / 2, y + s)], p.second, a)


def f_lightning(p, d, img, rows=(80, 300), thick=12, amp=34, seg=46):
    for k, y0 in enumerate(rows):
        pts = []
        x, y = -20, y0
        i = 0
        while x < p.w + 20:
            pts.append((x, y))
            x += seg
            y += amp if (i % 2) else -amp
            i += 1
        _line(d, pts, p.second if k % 2 == 0 else p.third, thick)


def f_penrose(p, d, img, s=60, r=34):
    rng = p.rng
    def rh(x, y, ix, iy):
        off = s / 2 if iy % 2 else 0
        a = rng.uniform(0, 360)
        cx, cy = x + off, y
        pts = [(cx + r * math.cos(math.radians(a + k * 72)),
                cy + r * math.sin(math.radians(a + k * 72))) for k in range(4)]
        _poly(d, pts, _shade(p.second, rng.uniform(0.7, 1.25)))
    _tiles(p, s, s, rh)


def f_wedge(p, d, img, size=0.5, corners=("tl", "br")):
    s = min(p.w, p.h) * size
    if "tl" in corners:
        _poly(d, [(0, 0), (s, 0), (0, s)], p.second)
    if "tr" in corners:
        _poly(d, [(p.w, 0), (p.w - s, 0), (p.w, s)], p.third)
    if "bl" in corners:
        _poly(d, [(0, p.h), (s, p.h), (0, p.h - s)], p.third)
    if "br" in corners:
        _poly(d, [(p.w, p.h), (p.w - s, p.h), (p.w, p.h - s)], p.second)


def f_spiral_tri(p, d, img, n=24, cx=0.5, cy=0.45):
    cx, cy = p.w * cx, p.h * cy
    for k in range(n):
        a = math.radians(k * 360 / n)
        rr = 20 + k * 7
        s = 10 + k * 0.8
        _poly(d, [(cx + rr * math.cos(a), cy + rr * math.sin(a)),
                  (cx + (rr + s) * math.cos(a + 0.3), cy + (rr + s) * math.sin(a + 0.3)),
                  (cx + (rr + s) * math.cos(a - 0.3), cy + (rr + s) * math.sin(a - 0.3))],
              _shade(p.second, 0.7 + (k % 4) * 0.12))


def f_bricks(p, d, img, hmin=40, hmax=90, wmin=50, wmax=130, mono=True):
    r = p.rng
    y = 0
    while y < p.h:
        h = r.randint(hmin, hmax)
        x = 0
        while x < p.w:
            w = r.randint(wmin, wmax)
            c = _shade(p.body, r.uniform(0.80, 1.12)) if mono else _shade(p.second, r.uniform(0.80, 1.12))
            _rect(d, [x, y, x + w - 4, y + h - 4], c)
            x += w
        y += h


def f_geode(p, d, img, rings=9, cx=0.62, cy=0.5, jag=12):
    cx, cy = p.w * cx, p.h * cy
    r = p.rng
    for k in range(rings):
        rad = 30 + k * 26
        pts = [(cx + (rad + r.uniform(-jag, jag)) * math.cos(math.radians(a)),
                cy + (rad + r.uniform(-jag, jag)) * math.sin(math.radians(a)))
               for a in range(0, 360, 30)]
        _line(d, pts + [pts[0]], _shade(p.second, 0.7 + k * 0.05), 4, 230)


def f_rain(p, d, img, n=40, s0=12, s1=34, down=True):
    r = p.rng
    for _ in range(n):
        x, y = r.uniform(0, p.w), r.uniform(0, p.h)
        s = r.uniform(s0, s1)
        if down:
            _poly(d, [(x, y), (x + s, y), (x + s / 2, y + s)], p.second, r.randint(120, 235))
        else:
            _poly(d, [(x, y + s), (x + s, y + s), (x + s / 2, y)], p.second, r.randint(120, 235))


def f_split(p, d, img, mode="v"):
    if mode == "v":
        _rect(d, [p.w / 2, 0, p.w, p.h], p.second)
    elif mode == "diag":
        _poly(d, [(0, 0), (p.w, 0), (p.w, p.h * 0.55), (0, p.h * 0.15)], p.second)
    elif mode == "quarters":
        _rect(d, [0, 0, p.w / 2, p.h / 2], p.second)
        _rect(d, [p.w / 2, p.h / 2, p.w, p.h], p.third)
    elif mode == "zig":
        pts = [(p.w / 2, 0)]
        y = 0
        while y < p.h:
            y += p.h / 8
            pts.append((p.w / 2 + (20 if (y // (p.h / 8)) % 2 else -20), y))
        _poly(d, pts + [(p.w, p.h), (p.w, 0)], p.second)


def f_weave(p, d, img, step=44, thick=18, a1=150, a2=130):
    for i in range(-10, 18):
        x = i * step
        _poly(d, [(x, 0), (x + thick, 0), (x + thick - p.h, p.h), (x - p.h, p.h)], p.second, a1)
        _poly(d, [(x, 0), (x + thick * 0.45, 0), (x + thick * 0.45 + p.h, p.h), (x + p.h, p.h)], p.third, a2)


def f_pixelpoly(p, d, img, cell=30, split=0.5):
    def px(x, y, ix, iy):
        if y / p.h < split or ix % 2 == 0:
            _rect(d, [x, y, x + cell - 3, y + cell - 3], p.second)
        else:
            _poly(d, [(x, y), (x + cell, y), (x + cell / 2, y + cell)], p.second)
    _tiles(p, cell, cell, px)


def f_horizon(p, d, img, n=12, step=46):
    for i, y in enumerate(range(40, int(p.h), step)):
        w = p.w - i * 22
        if w <= 0:
            break
        _poly(d, [(p.w / 2 - w / 2, y), (p.w / 2 + w / 2, y), (p.w / 2, y + 16)], p.second)


def f_shield(p, d, img, scales=(0.9, 0.62, 0.36), thick=4):
    for k, s in enumerate(scales):
        w = p.w * s
        h = p.h * s * 0.8
        x0, y0 = p.w / 2 - w / 2, p.h * 0.35 - h / 2
        pts = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h * 0.6),
               (x0 + w / 2, y0 + h), (x0, y0 + h * 0.6)]
        _line(d, pts + [pts[0]], p.second if k % 2 == 0 else p.third, thick, 200)


# =========================================================================== #
#  Category 2 - Fluid, Marble & Liquid Distortion (041-080)
# =========================================================================== #
def f_marble(p, d, img, veins=16, thick=6, tone=0.55, banded=False):
    r = p.rng
    if banded:
        for i in range(veins * 2):
            y0 = r.uniform(-0.1, 1.1) * p.h
            pts = []
            x = -20
            while x < p.w + 20:
                pts.append((x, y0 + math.sin(x / p.w * math.pi * 3 + i) * p.h * 0.06))
                x += 40
            _line(d, pts, _shade(p.second, r.uniform(0.7, 1.15)), thick * r.uniform(0.5, 1.3),
                  int(180 * tone + 50))
        return
    for i in range(veins):
        y0 = r.uniform(-0.1, 1.1) * p.h
        pts = []
        x = -20
        while x < p.w + 20:
            pts.append((x, y0 + r.uniform(-0.12, 0.12) * p.h))
            x += r.uniform(40, 90)
        col = _mix(p.body, p.second, r.uniform(0.3, 0.9)) if i % 2 else _shade(p.second, r.uniform(0.7, 1.15))
        _line(d, pts, col, thick * r.uniform(0.4, 1.4), int(200 * tone + 40))


def f_chrome(p, d, img, arms=7, turns=2.6, r1=560, thick=14):
    cx, cy = p.w * 0.5, p.h * 0.45
    for k in range(arms):
        pts = []
        a0 = 2 * math.pi * k / arms
        n = 100
        for i in range(n):
            t = i / (n - 1)
            ang = a0 + t * turns * 2 * math.pi
            rad = 14 + (r1 - 14) * t
            pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        col = _shade(p.second, 0.75 + 0.5 * (k % 3) / 2)
        _line(d, pts, col, thick * (0.6 + 0.4 * (k % 2)), 210)


def f_bloom(p, d, img, n=8, rmin=0.08, rmax=0.20, cols=2, a=45, seed=0):
    """Subtle atmospheric watercolor haze with calm chest sponsor zone."""
    r = p.rng
    palette = [p.second, p.third, p.mid, p.lo]
    for i in range(n):
        cx, cy = r.uniform(0, p.w), r.uniform(0, p.h)
        if 0.28 * p.h < cy < 0.56 * p.h:
            continue
        rad = r.uniform(rmin, rmax) * p.w
        col = palette[(i + seed) % max(1, cols)]
        # Soft feathered rings rather than giant solid discs
        for st in range(3):
            rr = rad * (1.0 - st * 0.25)
            _ring(d, cx, cy, rr, col, w=1.5, a=max(15, int(a * (0.8 - st * 0.2))))


def f_topo(p, d, img, levels=18, step=26, thick=2, a=200, cx=0.55, cy=0.5):
    cx, cy = p.w * cx, p.h * cy
    for i in range(levels):
        rad = 20 + i * step
        pts = []
        for k in range(72):
            ang = 2 * math.pi * k / 72
            rr = rad * (1 + 0.18 * math.sin(ang * 3 + i * 0.6))
            pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang) * 0.8))
        _line(d, pts + [pts[0]], _shade(p.second, 0.75 + 0.02 * i), thick, a)


def f_veins(p, d, img, n=12, branch=3, thick=3, from_hem=True, a=210):
    r = p.rng
    for _ in range(n):
        x = r.uniform(0, p.w)
        y = p.h if from_hem else 0
        pts = [(x, y)]
        while (y > 0) if from_hem else (y < p.h):
            x += r.uniform(-18, 18)
            y += -r.uniform(14, 34) if from_hem else r.uniform(14, 34)
            pts.append((x, y))
            if r.random() < 0.25:
                bx, by = x, y
                bpts = [(bx, by)]
                for _ in range(branch):
                    bx += r.uniform(-30, 30)
                    by += -r.uniform(8, 22) if from_hem else r.uniform(8, 22)
                    bpts.append((bx, by))
                _line(d, bpts, p.third, max(1, thick - 1), max(0, a - 40))
        _line(d, pts, p.second, thick, a)


def f_silk(p, d, img, folds=7, strength=0.5, twist=0.0):
    for x in range(p.w):
        t = x / p.w
        v = math.sin(t * math.pi * 2 * folds + twist * math.sin(t * math.pi))
        col = _mix(p.body, p.second, v * strength) if v > 0 else _mix(p.body, p.lo, -v * strength)
        _rect(d, [x, 0, x + 1, p.h], col, 255)


def f_swirl(p, d, img, arms=7, turns=2.6, thick=12, dots=False, cx=0.5, cy=0.45):
    cx, cy = p.w * cx, p.h * cy
    for k in range(arms):
        pts = []
        a0 = 2 * math.pi * k / arms
        n = 90
        for i in range(n):
            t = i / (n - 1)
            ang = a0 + t * turns * 2 * math.pi
            rad = 14 + (p.w * 1.1 - 14) * t
            pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        col = p.second if k % 2 == 0 else p.third
        if dots:
            for j in range(0, len(pts), 3):
                _dot(d, pts[j][0], pts[j][1], thick * 0.35, col, 200)
        else:
            _line(d, pts, col, thick, 210)


def f_flow(p, d, img, lines=30, curve=1.4, thick=2, a=190):
    for i in range(lines):
        y = p.h * (i + 0.5) / lines
        pts = []
        for k in range(41):
            x = p.w * k / 40
            pts.append((x, y + math.sin(k / 40 * math.pi * curve + i * 0.3) * p.h * 0.03))
        _line(d, pts, p.second if i % 2 else p.third, thick, a)


def f_bands(p, d, img, count=12, vertical=False, wavy=0.0, a=120, tones=3, glow=False):
    for i in range(count):
        f = i / max(1, count - 1)
        col = _mix(p.second, p.third, f) if tones > 1 else p.second
        if vertical:
            x = i * p.w / count
            if wavy > 0:
                pts = [(x + math.sin(k / p.h * math.pi * 4 + i) * p.w * wavy, k)
                       for k in range(0, p.h + 1, 8)]
                _line(d, pts, col, max(4, int(p.w / count * 0.7)), a)
            else:
                _rect(d, [x, 0, x + p.w / count * 0.9, p.h], col, a)
        else:
            y = i * p.h / count
            if wavy > 0:
                pts = [(k, y + math.sin(k / p.w * math.pi * 4 + i) * p.h * wavy)
                       for k in range(0, p.w + 1, 8)]
                _line(d, pts, col, max(4, int(p.h / count * 0.7)), a)
            else:
                _rect(d, [0, y, p.w, y + p.h / count * 0.85], col, a)


def f_waves(p, d, img, count=16, amp=0.025, period=3.0, thick=3, a=200, fill=False):
    for i in range(count):
        y = p.h * (i + 0.5) / count
        pts = [(x, y + math.sin(x / p.w * math.pi * period) * p.h * amp)
               for x in range(0, p.w + 1, 6)]
        if fill:
            _poly(d, pts + [(p.w, p.h), (0, p.h)], p.second if i % 2 else p.third, a)
        else:
            _line(d, pts, p.second if i % 2 else p.third, thick, a)


def f_plume(p, d, img, n=10, spread=0.5, side="both"):
    r = p.rng
    for i in range(n):
        base = (r.uniform(0, 1) * p.h)
        x0 = 0 if side != "right" else p.w
        for k in range(1, 9):
            t = k / 8
            x = x0 + (p.w * spread) * t * (1 if side != "right" else -1)
            y = base + math.sin(t * math.pi) * p.h * 0.06 * (1 if i % 2 else -1)
            _line(d, [(x0, base), (x, y)], p.second if i % 2 else p.third, max(1, int(4 * (1 - t))), 190)


def f_dots(p, d, img, n=900, rmin=1, rmax=4, a=200, cols=1, clump=0.0):
    r = p.rng
    for _ in range(int(n)):
        x, y = r.uniform(0, p.w), r.uniform(0, p.h)
        if clump:
            x = min(p.w, max(0, x + r.uniform(-clump, clump) * p.w))
        rad = r.uniform(rmin, rmax)
        c = p.second if cols <= 1 or r.random() < 0.5 else p.third
        _dot(d, x, y, rad, c, r.randint(max(40, a - 80), a))


# =========================================================================== #
#  Category 3 - Reimagined Classics: Stripes, Hoops & Sashes (081-125)
# =========================================================================== #
def f_vstripes(p, d, img, count=9, width=0.5, mode="plain", color=None, fade=0.0):
    color = color or p.second
    r = p.rng
    step = p.w / count
    for i in range(count):
        x = i * step
        w = width * step
        if mode == "barcode":
            w = step * r.uniform(0.12, 0.95)
        if mode == "halftone":
            # Elegant athletic vertical stripe with smooth gradient fade into the chest zone
            for k in range(0, int(p.h), 4):
                if 0.28 * p.h < k < 0.56 * p.h:
                    continue
                # Smooth alpha falloff toward chest sponsor area (clean vertical borders, no spiky cones)
                dist_to_center = abs(k - 0.42 * p.h) / (0.42 * p.h)
                alpha = int(220 * max(0.20, min(1.0, dist_to_center ** 1.4)))
                _rect(d, [x + w * 0.2, k, x + w * 0.8, k + 4], color, alpha)
            continue
        if mode == "brush":
            # Continuous artistic painted vertical stripe with soft feathered edges & calm sponsor zone
            for y0, y1 in [(0, int(p.h * 0.28)), (int(p.h * 0.58), int(p.h))]:
                # Main continuous vertical stroke band (never 12px stacked rectangles)
                _rect(d, [x + w * 0.15, y0, x + w * 0.85, y1], color, 220)
                # Delicate fine vertical brush bristle hairlines along outer edges
                _line(d, [(x + w * 0.10, y0), (x + w * 0.10, y1)], color, w=1.5, a=140)
                _line(d, [(x + w * 0.90, y0), (x + w * 0.90, y1)], color, w=1.5, a=140)
            continue
        if mode == "taper":
            # Elegant athletic vertical pinstripe with subtle variable width
            _line(d, [(x + w * 0.5, 0), (x + w * 0.5, p.h * 0.28)], color, max(1, int(w * 0.6)), 180)
            _line(d, [(x + w * 0.5, p.h * 0.58), (x + w * 0.5, p.h)], color, max(1, int(w * 0.6)), 180)
            continue
        if mode == "glitch":
            # Modern barcode / rhythm pinstripe (straight, elegant pinstripes with varied widths)
            pw = max(1.5, (1.0 + (i % 3) * 1.5))
            _line(d, [(x + w * 0.5, 0), (x + w * 0.5, p.h * 0.28)], color, int(pw), 160)
            _line(d, [(x + w * 0.5, p.h * 0.58), (x + w * 0.5, p.h)], color, int(pw), 160)
            continue
        if mode == "wavy":
            pts = [(x + math.sin(k / p.h * math.pi * 4 + i * 0.5) * w * 1.2, k)
                   for k in range(0, int(p.h) + 1, 6)]
            _line(d, pts, color, max(3, int(w)), 255)
            continue
        if mode == "dotted":
            for k in range(0, int(p.h), int(max(4, w))):
                _dot(d, x + w * 0.5, k, w * 0.42, color, 255)
            continue
        if mode == "neon":
            _rect(d, [x, 0, x + w, p.h], _shade(p.body, 0.72))
            _line(d, [(x, 0), (x, p.h)], p.third, 2)
            _line(d, [(x + w, 0), (x + w, p.h)], p.third, 2)
            continue
        if mode == "chalk":
            for k in range(0, int(p.h), 3):
                jx = r.uniform(-1.5, 1.5)
                _rect(d, [x + jx, k, x + jx + w, k + 2], color, r.randint(120, 200))
            continue
        if mode == "torn":
            pts = [(x + r.uniform(-4, 4), k) for k in range(0, int(p.h) + 1, 10)]
            _line(d, pts, color, max(3, int(w)), 255)
            _line(d, [(px + 6, py) for px, py in pts], p.third, 2, 150)
            continue
        if mode == "chevronfill":
            _rect(d, [x, 0, x + w, p.h], color, 120)
            for k in range(0, int(p.h), 16):
                _line(d, [(x, k), (x + w * 0.5, k + 8), (x + w, k)], color, 3, 255)
            continue
        if mode == "sidepanel":
            if x < p.w * 0.22 or x > p.w * 0.78:
                _rect(d, [x, 0, x + w, p.h], color)
            continue
        if mode == "gradient":
            _rect(d, [x, 0, x + w, p.h], color, int(255 * (0.25 + 0.75 * i / max(1, count - 1))))
            continue
        if mode == "mono":
            # tonal = same hue, clearly different lightness (1.10/0.90 reads as a
            # flat colour at kit scale, so push the contrast while staying tonal).
            _rect(d, [x, 0, x + w, p.h], _shade(p.body, 1.38 if i % 2 else 0.62))
            continue
        if mode == "metallic":
            for k in range(0, int(p.h), 4):
                f = 0.6 + 0.5 * abs(math.sin(k / p.h * math.pi * 3))
                _rect(d, [x, k, x + w, k + 4], _mix(p.second, p.third, f), 255)
            continue
        if mode == "invert":
            _rect(d, [x, 0, x + w, p.h * 0.5], color)
            _rect(d, [x, p.h * 0.5, x + w, p.h], p.body)
            continue
        if mode == "crestframe":
            _rect(d, [x, 0, x + w, p.h], color)
            continue
        if mode == "cluster":
            for c in range(5):
                _rect(d, [x + c * w * 0.22, 0, x + c * w * 0.22 + max(1, w * 0.06), p.h], color)
            continue
        _rect(d, [x, 0, x + w, p.h], color)
    if fade:
        _alpha_ramp(img, 0.0, 1.0, 1.0 - fade, 0.0)


def f_hoops(p, d, img, count=8, height=0.5, mode="plain", color=None):
    color = color or p.second
    r = p.rng
    step = p.h / count
    for i in range(count):
        y = i * step
        hh = height * step
        if mode == "gradient":
            _rect(d, [0, y, p.w, y + hh], _mix(p.second, p.third, i / max(1, count - 1)))
        elif mode == "shadow":
            _rect(d, [0, y, p.w, y + hh], color)
            _rect(d, [0, y + hh, p.w, y + hh + 3], (0, 0, 0), 80)
        elif mode == "broken":
            x = 0
            while x < p.w:
                seg = r.uniform(0.05, 0.20) * p.w
                _rect(d, [x, y, x + seg, y + hh], color)
                x += seg + r.uniform(0.03, 0.12) * p.w
        elif mode == "pixel":
            _rect(d, [0, y, p.w, y + hh], color)
            for x in range(0, int(p.w), 10):
                if r.random() < 0.5:
                    _rect(d, [x, y - 4, x + 8, y], color, 180)
                if r.random() < 0.5:
                    _rect(d, [x, y + hh, x + 8, y + hh + 4], color, 180)
        elif mode == "watercolor":
            for k in range(int(y), int(y + hh) + 1):
                f = (k - y) / max(1.0, hh)
                a = int(210 * (1 - abs(f - 0.5) * 1.3))
                _rect(d, [0, k, p.w, k + 1], color, max(0, a))
        elif mode == "segmented":
            _rect(d, [0, y, p.w, y + hh], color)
            for x in range(0, int(p.w), 26):
                _rect(d, [x, y, x + 2, y + hh], p.body)
        elif mode == "asym":
            _rect(d, [0, y, p.w * 0.5, y + hh], color)
        elif mode == "blocked":
            _rect(d, [0, y, p.w, y + hh], color)
            _rect(d, [0, y + hh, p.w, y + hh * 1.4], p.third, 180)
        else:
            _rect(d, [0, y, p.w, y + hh], color)


def f_sash(p, d, img, width=0.28, count=1, angle=45, lines=0, stitch=0, brush=0, glow=False):
    t = math.radians(angle)
    dx, dy = math.cos(t), math.sin(t)
    span = (p.w + p.h)
    if count > 1:
        step = width * p.w / count
    else:
        step = width * p.w
    x = -p.h
    idx = 0
    while x < p.w + p.h:
        x0, y0 = x, -p.h
        x1, y1 = x + span * dx, -p.h + span * dy
        if lines:
            for k in range(lines):
                off = (k - lines / 2) * 3
                _line(d, [(x0 + off, y0), (x1 + off, y1)], p.second, 2, 200)
        elif stitch:
            # a faint band + bold cross-stitches, so the sash reads as a sash
            # (crosses alone are too sparse to register at kit scale).
            _line(d, [(x0, y0), (x1, y1)], p.second, max(6, int(step * 0.9)), 95)
            n = 40
            for k in range(n):
                ta = k / n
                px, py = x0 + (x1 - x0) * ta, y0 + (y1 - y0) * ta
                _line(d, [(px - 5, py - 5), (px + 5, py + 5)], p.second, 3, 235)
                _line(d, [(px - 5, py + 5), (px + 5, py - 5)], p.second, 3, 235)
        elif brush:
            for k in range(0, int(step), 6):
                _line(d, [(x0 + k, y0), (x1 + k, y1)], p.second, 5, 150)
        else:
            _line(d, [(x0, y0), (x1, y1)], p.second, max(6, int(step * 0.9)), 255)
            if glow:
                _line(d, [(x0, y0), (x1, y1)], p.third, max(2, int(step * 0.15)), 220)
        x += max(8, step)
        idx += 1


def f_check(p, d, img, cell=44, mode="plain", fade=0.0, diag=0):
    def ch(x, y, ix, iy):
        on = (ix + iy) % 2 == 0
        c = p.second if on else p.third
        if mode == "fade":
            a = int(255 * max(0.0, 1 - (y / p.h)))
            _rect(d, [x, y, x + cell, y + cell], c, a)
        elif mode == "glitch":
            off = math.sin(y / p.h * math.pi * 6) * 8
            _rect(d, [x + off, y, x + cell, y + cell], c)
        else:
            _rect(d, [x, y, x + cell, y + cell], c)
    _tiles(p, cell, cell, ch)


def f_plaid(p, d, img, cell=64, band=0.5):
    step = cell
    for x in range(-step, int(p.w) + step, step):
        _rect(d, [x, 0, x + step * band, p.h], p.second, 120)
    for y in range(-step, int(p.h) + step, step):
        _rect(d, [0, y, p.w, y + step * band], p.third, 120)


def f_argyle(p, d, img, cell=90, cross=True):
    def dia(x, y, ix, iy):
        off = cell / 2 if iy % 2 else 0
        _poly(d, [(x + off + cell / 2, y), (x + off + cell, y + cell / 2),
                  (x + off + cell / 2, y + cell), (x + off, y + cell / 2)], p.second, 210)
    _tiles(p, cell, cell, dia)
    if cross:
        for y in range(0, int(p.h), 24):
            _line(d, [(0, y), (p.w, y)], p.third, 1, 90)


def f_pinstripe(p, d, img, gap=28, thick=3, mode="plain", count=1, start=8):
    x = start
    while x < p.w:
        if mode == "dots":
            for k in range(0, int(p.h), 8):
                _dot(d, x, k, thick * 0.7, p.second, 255)
        elif mode == "grad":
            a = int(60 + 195 * (x / p.w))
            _rect(d, [x, 0, x + thick, p.h], p.second, a)
        elif mode == "sub":
            _rect(d, [x, 0, x + thick, p.h], p.second)
            for k in range(0, int(p.h), 10):
                _dot(d, x + thick / 2, k, 1, p.third, 200)
        elif mode == "cluster":
            for c in range(5):
                _rect(d, [x + c * 5, 0, x + c * 5 + max(1, thick - 1), p.h], p.second)
        else:
            _rect(d, [x, 0, x + thick, p.h], p.second)
        x += gap


def f_centerband(p, d, img, mode="plain", band=0.14, vband=0.0):
    if mode == "interrupted":
        x = 0
        while x < p.w:
            if not (p.w * 0.35 < x < p.w * 0.65):
                _rect(d, [x, 0, x + 20, p.h], p.second, 200)
            x += 40
        _rect(d, [p.w * 0.35, p.h * 0.28, p.w * 0.65, p.h * 0.5], p.body)
    elif mode == "blocked":
        y0 = p.h * 0.40
        _rect(d, [0, y0, p.w, y0 + band * p.h], p.second)
        for x in range(0, int(p.w), 26):
            _rect(d, [x, 0, x + 2, y0], p.third, 180)
            _rect(d, [x, y0 + band * p.h, x + 2, p.h], p.third, 180)
    elif mode == "doublev":
        _line(d, [(0, p.h * 0.30), (p.w / 2, p.h * 0.46), (p.w, p.h * 0.30)], p.second, 8)
        _line(d, [(0, p.h * 0.40), (p.w / 2, p.h * 0.56), (p.w, p.h * 0.40)], p.second, 8)
    elif mode == "chestband":
        y0 = p.h * 0.30
        _rect(d, [0, y0, p.w, y0 + band * p.h], p.second)
        for k in range(6):
            _line(d, [(0, y0 + k * 3), (p.w, y0 + k * 3)], p.third, 1, 120)
    elif mode == "vband":
        _rect(d, [p.w * 0.5 - 0.08 * p.w, 0, p.w * 0.5 + 0.08 * p.w, p.h], p.second)
    elif mode == "hechter":
        cx = p.w * 0.5
        hw = p.w * 0.12
        pw = max(3, int(p.w * 0.018))
        _rect(d, [cx - hw, 0, cx + hw, p.h], p.second)
        _rect(d, [cx - hw - pw, 0, cx - hw, p.h], p.third)
        _rect(d, [cx + hw, 0, cx + hw + pw, p.h], p.third)
    elif mode == "hechter_offset":
        # Asymmetric stripe running under the club crest (left chest)
        cx = p.w * 0.668
        hw = p.w * 0.075
        pw = max(3, int(p.w * 0.014))
        _rect(d, [cx - hw, 0, cx + hw, p.h], p.second)
        _rect(d, [cx - hw - pw, 0, cx - hw, p.h], p.third)
        _rect(d, [cx + hw, 0, cx + hw + pw, p.h], p.third)
    elif mode == "hechter_slim":
        cx = p.w * 0.5
        hw = p.w * 0.075
        pw = max(3, int(p.w * 0.014))
        _rect(d, [cx - hw, 0, cx + hw, p.h], p.second)
        _rect(d, [cx - hw - pw, 0, cx - hw, p.h], p.third)
        _rect(d, [cx + hw, 0, cx + hw + pw, p.h], p.third)
    elif mode == "hechter_brush":
        cx = p.w * 0.5
        hw = p.w * 0.11
        pw = max(3, int(p.w * 0.016))
        _rect(d, [cx - hw, 0, cx + hw, p.h], p.second)
        _rect(d, [cx - hw - pw, 0, cx - hw, p.h], p.third)
        _rect(d, [cx + hw, 0, cx + hw + pw, p.h], p.third)
        for y in range(0, int(p.h), 12):
            if (y // 12) % 3 == 0:
                _rect(d, [cx - hw, y, cx + hw, y + 2], p.body, a=60)
    elif mode == "hechter_gradient":
        cx = p.w * 0.5
        hw = p.w * 0.11
        pw = max(3, int(p.w * 0.016))
        for y in range(0, int(p.h), 4):
            alpha = int(255 * (1.0 - 0.35 * (y / p.h)))
            _rect(d, [cx - hw, y, cx + hw, y + 4], p.second, a=alpha)
            _rect(d, [cx - hw - pw, y, cx - hw, y + 4], p.third, a=alpha)
            _rect(d, [cx + hw, y, cx + hw + pw, y + 4], p.third, a=alpha)
    else:
        y0 = p.h * (0.30 + 0.05 * (p.var % 3))
        _rect(d, [0, y0, p.w, y0 + band * p.h], p.second)


def f_ribbonfold(p, d, img, count=8, width=0.5):
    step = p.w / count
    for i in range(count):
        x = i * step
        w = width * step
        _rect(d, [x, p.h * 0.5, x + w, p.h], p.second)
        _poly(d, [(x, 0), (x + w, 0), (x + w + p.w * 0.15, p.h * 0.5), (x + p.w * 0.15, p.h * 0.5)],
              p.second)


def f_woven(p, d, img, step=40, thick=16):
    for i in range(-10, 18):
        x = i * step
        for y in range(-10, int(p.h) + 10, step):
            on = (i + (y // step)) % 2 == 0
            if on:
                _rect(d, [x, y, x + thick, y + step - 4], p.second, 200)
            else:
                _rect(d, [x, y, x + step - 4, y + thick], p.third, 200)


# =========================================================================== #
#  Category 4 - Digital, Glitch & Tech-Futurism (126-165)
# =========================================================================== #
def f_glitch(p, d, img, mode="vhs", bars=10):
    r = p.rng
    if mode == "vhs":
        y = 0
        while y < p.h:
            h = r.uniform(0.01, 0.05) * p.h
            a = r.randint(60, 190)
            col = p.second if r.random() < 0.7 else p.third
            _rect(d, [0, y, p.w, y + h], col, a)
            y += h + r.uniform(0.01, 0.05) * p.h
    elif mode == "datamosh":
        for _ in range(120):
            x, y = r.uniform(0, p.w), r.uniform(0, p.h)
            w = r.uniform(10, 80)
            h = r.uniform(6, 26)
            _rect(d, [x, y, x + w, y + h], p.second if r.random() < 0.6 else p.third, r.randint(90, 220))
    elif mode == "static":
        for _ in range(2600):
            x, y = r.randrange(int(p.w)), r.randrange(int(p.h))
            v = r.randint(0, 60)
            _dot(d, x, y, 1.4, _shade(p.second, 0.6 + v / 100), 120)
    elif mode == "anaglyph":
        for i in range(-4, 10):
            x = i * 60
            _line(d, [(x, 0), (x + p.h, p.h)], p.second, 4, 180)
            _line(d, [(x + 5, 0), (x + 5 + p.h, p.h)], p.third, 4, 180)
    elif mode == "stripes":
        for i in range(10):
            x = i * (p.w / 10)
            y = 0
            while y < p.h:
                seg = r.uniform(0.04, 0.16) * p.h
                sh = r.uniform(-0.7, 0.7) * (p.w / 10)
                _rect(d, [x + sh, y, x + sh + p.w / 20, y + seg], p.second)
                y += seg


def f_circuit(p, d, img, mode="pcb", nodes=40):
    """Architectural diagonal micro-lattice knit texture with calm chest sponsor zone (no motherboard traces/dots)."""
    step = 36.0
    for y in range(0, int(p.h), int(step)):
        if 0.28 * p.h < y < 0.56 * p.h:
            continue
        # Refined diagonal tonal weave
        _line(d, [(0, y), (p.w, y + p.w * 0.35)], p.second, 1.5, a=65)
        _line(d, [(0, y + p.w * 0.35), (p.w, y)], p.second, 1.5, a=45)


def f_rain2(p, d, img, mode="matrix", cols=24, a=210):
    r = p.rng
    step = p.w / cols
    for c in range(cols):
        x = c * step + step / 2
        if mode == "matrix":
            y = r.uniform(-0.3, 1.0) * p.h
            while y < p.h:
                if not (0.28 * p.h < y < 0.56 * p.h):
                    _rect(d, [x - 1, y, x + 1, y + 5], p.second, a=55)
                    _dot(d, x, y, 1.0, p.third, a=45)
                y += r.uniform(14, 28)
        elif mode == "binary":
            # Engineered breathable micro-mesh pinpoint jacquard
            for k in range(0, int(p.h), 14):
                if not (0.28 * p.h < k < 0.56 * p.h):
                    _dot(d, x, k, 1.2, p.second if (c + k // 14) % 2 else p.third, a=45)
        elif mode == "chevron":
            for k in range(0, int(p.h), 16):
                if not (0.28 * p.h < k < 0.56 * p.h):
                    _rect(d, [x - 1, k, x + 1, k + 4], p.second, a=50)


def f_pixel(p, d, img, mode="dissolve", cell=24):
    """Modern tonal digital pixel knit with calm chest sponsor zone (no QR codes/blocks)."""
    r = p.rng
    for iy, y in enumerate(range(0, int(p.h), cell)):
        if 0.28 * p.h < y < 0.56 * p.h:
            continue
        for ix, x in enumerate(range(0, int(p.w), cell)):
            if (ix + iy) % 2 == 0 and r.random() < 0.35:
                col = p.second if (ix + iy) % 4 == 0 else p.third
                _rect(d, [x + 2, y + 2, x + cell - 4, y + cell - 4], col, a=40)


def f_scan(p, d, img, mode="crt", step=12):
    """Refined engineered horizontal micro-rib knit texture with calm chest sponsor zone."""
    for y in range(0, int(p.h), step):
        if 0.28 * p.h < y < 0.56 * p.h:
            continue
        _line(d, [(0, y), (p.w, y)], p.second, 1.0, a=45)


def f_grid(p, d, img, mode="wireframe", step=48):
    r = p.rng
    if mode == "wireframe":
        for x in range(0, int(p.w), step):
            _line(d, [(x, 0), (x, p.h)], p.second, 2, 170)
        for y in range(0, int(p.h), step):
            _line(d, [(0, y), (p.w, y)], p.second, 2, 170)
    elif mode == "void":
        cx, cy = p.w / 2, p.h * 0.45
        for k in range(1, 30):
            s = k * k * 0.9
            _poly(d, [(cx - s, cy - s * 0.8), (cx + s, cy - s * 0.8),
                      (cx + s, cy + s * 0.8), (cx - s, cy + s * 0.8)], None) if False else None
            _line(d, [(cx - s, cy - s * 0.8), (cx + s, cy - s * 0.8),
                      (cx + s, cy + s * 0.8), (cx - s, cy + s * 0.8), (cx - s, cy - s * 0.8)],
                  p.second, 1, 150)
    elif mode == "synth":
        horizon = p.h * 0.55
        for k in range(1, 20):
            y = horizon + (p.h - horizon) * (k / 20) ** 2
            _line(d, [(0, y), (p.w, y)], p.second, 2, 190)
        for k in range(-10, 11):
            _line(d, [(p.w / 2 + k * 20, p.h), (p.w / 2 + k * 4, horizon)], p.second, 1, 190)
        _rect(d, [0, 0, p.w, horizon], p.third, 60)
    elif mode == "holo":
        for _ in range(60):
            x, y = r.uniform(0, p.w), r.uniform(0, p.h)
            s = r.uniform(20, 60)
            _poly(d, [(x, y), (x + s, y), (x + s, y + s), (x, y + s)],
                  p.second if r.random() < 0.5 else p.third, 70)
    elif mode == "moire":
        for k in range(40):
            _ring(d, p.w / 2, p.h / 2, k * 9, p.second, 2, 150)
    elif mode == "halftone":
        r = p.rng
        for y in range(0, int(p.h), 16):
            for x in range(0, int(p.w), 16):
                rad = 6 * (1 - y / p.h)
                _dot(d, x + 8, y + 8, rad, p.second, 200)


def f_radar(p, d, img, mode="sonar", cx=0.5, cy=0.42):
    """Subtle aerodynamic curved contour ribs with calm chest sponsor zone."""
    cx, cy = p.w * cx, p.h * cy
    for k in range(1, 6):
        rad = k * 42
        pts = []
        for a_deg in range(210, 331, 10):
            rad_a = math.radians(a_deg)
            pts.append((cx + rad * math.cos(rad_a), cy + rad * 0.6 * math.sin(rad_a)))
        _line(d, pts, p.second, 1.5, a=55)


def f_plate(p, d, img, mode="armor", step=42):
    """Refined carbon fiber and technical fabric micro-weave with calm sponsor zone."""
    for iy, y in enumerate(range(0, int(p.h), step)):
        if 0.28 * p.h < y < 0.56 * p.h:
            continue
        off = step / 2 if iy % 2 else 0
        for ix, x in enumerate(range(0, int(p.w), step)):
            cx, cy = x + off, y
            _poly(d, [(cx, cy - 8), (cx + 18, cy), (cx, cy + 8), (cx - 18, cy)], p.second, a=45)


def f_bars(p, d, img, mode="spectrum", bars=26):
    """Subtle rhythm pin-stripes with calm chest zone."""
    step = p.w / float(bars)
    for i in range(bars):
        x = i * step
        _line(d, [(x, 0), (x, p.h * 0.28)], p.second, 1.5, a=70)
        _line(d, [(x, p.h * 0.58), (x, p.h)], p.second, 1.5, a=70)


def f_streak(p, d, img, mode="velocity", lines=40):
    r = p.rng
    if mode == "velocity":
        for _ in range(lines):
            y = r.uniform(0, p.h)
            x0 = r.uniform(-0.2, 0.6) * p.w
            ln = r.uniform(0.1, 0.5) * p.w
            _line(d, [(x0, y), (x0 + ln, y)], p.second, r.randint(1, 3), r.randint(100, 200))
    elif mode == "fiber":
        for k in range(lines):
            t = k / lines
            pts = []
            for j in range(31):
                s = j / 30
                x = p.w * s
                y = p.h * t + math.sin(s * math.pi * 2 + k) * p.h * 0.05
                pts.append((x, y))
            _line(d, pts, p.second if k % 2 else p.third, 1, 200)


def f_mesh(p, d, img, step=26):
    r = p.rng
    for y in range(0, int(p.h), step):
        for x in range(0, int(p.w), step):
            if r.random() < 0.7:
                _dot(d, x + step / 2, y + step / 2, 3, p.second, 160)
    for y in range(0, int(p.h), step):
        _line(d, [(0, y), (p.w, y)], p.third, 1, 70)


# =========================================================================== #
#  Category 5 - Architectural, Cultural & Bespoke Motifs (166-205)
# =========================================================================== #
def f_citymap(p, d, img, mode="streets"):
    """Authentic urban cartography and diagonal transit routes with calm sponsor zone (no dots/clutter)."""
    r = p.rng
    if mode == "streets":
        for _ in range(18):
            x, y = r.uniform(0, p.w), r.uniform(0, p.h)
            pts = [(x, y)]
            for _ in range(r.randint(2, 4)):
                if r.random() < 0.5:
                    x += r.choice([-1, 1]) * r.uniform(25, 60)
                else:
                    y += r.choice([-1, 1]) * r.uniform(25, 60)
                if not (0.28 * p.h < y < 0.58 * p.h):
                    pts.append((x, y))
            if len(pts) > 1:
                _line(d, pts, p.second, 1.2, 50)
    elif mode == "transit":
        cols = [p.second, p.third, p.second]
        for k in range(4):
            y = p.h * (0.12 + k * 0.22)
            if 0.26 * p.h < y < 0.60 * p.h:
                continue
            pts = [(0, y)]
            x = 0
            while x < p.w:
                x += r.uniform(60, 110)
                y_next = y + r.choice([-1, 1]) * r.uniform(15, 35)
                pts.append((x, y))
                pts.append((x, y_next))
                y = y_next
            _line(d, pts, cols[k % 3], 1.5, 60)
    elif mode == "skyline":
        # Subtle architectural pinstripe contour along bottom hem only
        y0 = p.h * 0.82
        x = 0
        while x < p.w:
            w = r.uniform(20, 45)
            h = r.uniform(0.04, 0.12) * p.h
            _rect(d, [x, y0 - h, x + w, p.h], p.second, 50)
            _line(d, [(x, y0 - h), (x + w, y0 - h)], p.third, 1.0, 75)
            x += w + r.uniform(2, 6)


def f_truss(p, d, img, mode="roof", step=70):
    """Sleek architectural stadium roof truss & cathedral ribs with calm chest sponsor zone."""
    r = p.rng
    if mode == "roof":
        for iy, y in enumerate(range(0, int(p.h) + step, step)):
            if 0.28 * p.h < y < 0.58 * p.h:
                continue
            for ix, x in enumerate(range(0, int(p.w) + step, step)):
                _line(d, [(x, y), (x + step, y + step)], p.second, 1.2, 55)
                _line(d, [(x + step, y), (x, y + step)], p.second, 1.2, 55)
                _line(d, [(x, y + step), (x + step, y + step)], p.third, 1.0, 45)
    elif mode == "vault":
        for k in range(-3, 7):
            x = k * step
            _line(d, [(x, p.h), (p.w / 2, 0)], p.second, 1.2, 50)
            _line(d, [(x, p.h), (p.w / 2, 0)], p.third, 1.0, 40)
    elif mode == "cables":
        top = p.h * 0.15
        for k in range(14):
            x = k * (p.w / 13)
            _line(d, [(x, p.h), (p.w * 0.5, top)], p.second, 1.0, 50)
        _line(d, [(0, top), (p.w, top)], p.third, 1.5, 60)


def f_artdeco(p, d, img, mode="fan", step=60):
    if mode == "fan":
        for i in range(-1, int(p.w / step) + 2):
            cx = i * step
            for k in range(1, 6):
                _ring(d, cx, p.h, k * 26, p.second, 3, 200)
    elif mode == "archways":
        for i in range(0, int(p.w) + 80, 80):
            _line(d, [(i, p.h), (i, p.h * 0.5), (i + 40, p.h * 0.35),
                      (i + 80, p.h * 0.5), (i + 80, p.h)], p.second, 4, 200)
    elif mode == "ironwork":
        for y in range(0, int(p.h), 60):
            for x in range(0, int(p.w), 60):
                _ring(d, x + 30, y + 30, 18, p.second, 3, 200)
                _line(d, [(x, y + 30), (x + 60, y + 30)], p.third, 2, 170)
                _line(d, [(x + 30, y), (x + 30, y + 60)], p.third, 2, 170)


def f_tile(p, d, img, s=48, shape="star"):
    def one(x, y, ix, iy):
        cx, cy = x + s / 2, y + s / 2
        # Keep chest sponsor zone calm
        if 0.28 * p.h < cy < 0.56 * p.h:
            return
        if shape == "star":
            # Delicate Portuguese Azulejo geometric micro-lattice (fine lines, no starburst wrapping paper)
            _ring(d, cx, cy, s * 0.28, p.second, w=1.0, a=60)
            _line(d, [(cx - s * 0.25, cy), (cx + s * 0.25, cy)], p.second, 1.0, 50)
            _line(d, [(cx, cy - s * 0.25), (cx, cy + s * 0.25)], p.second, 1.0, 50)
            _poly(d, [(cx - 2, cy), (cx, cy - 2), (cx + 2, cy), (cx, cy + 2)], p.third, 50)
        elif shape == "hex":
            pts = [(cx + s * 0.32 * math.cos(math.radians(60 * k)),
                    cy + s * 0.32 * math.sin(math.radians(60 * k))) for k in range(6)]
            _poly(d, pts, p.second, 90)
        elif shape == "square":
            _rect(d, [x + 4, y + 4, x + s - 4, y + s - 4], p.second, 90)
        elif shape == "snow":
            _line(d, [(cx - s * 0.25, cy), (cx + s * 0.25, cy)], p.third, 1.0, 60)
            _line(d, [(cx, cy - s * 0.25), (cx, cy + s * 0.25)], p.third, 1.0, 60)
    _tiles(p, s, s, one)


def f_rosewin(p, d, img, mode="rose", cx=0.5, cy=0.4):
    """Refined Gothic rosette and circular geometric guilloche jacquard with calm chest zone."""
    step = 72.0
    for y in range(0, int(p.h), int(step)):
        if 0.26 * p.h < y < 0.60 * p.h:
            continue
        for x in range(0, int(p.w), int(step)):
            cx_tile, cy_tile = x + step * 0.5, y + step * 0.5
            _ring(d, cx_tile, cy_tile, step * 0.38, p.second, 1.2, 55)
            _ring(d, cx_tile, cy_tile, step * 0.20, p.third, 1.0, 45)
            for j in range(8):
                a = math.radians(j * 45)
                _line(d, [(cx_tile, cy_tile),
                          (cx_tile + step * 0.38 * math.cos(a), cy_tile + step * 0.38 * math.sin(a))],
                      p.second, 1.0, 45)


def f_hound(p, d, img, s=64):
    def one(x, y, ix, iy):
        on = (ix + iy) % 2 == 0
        c = p.second if on else p.third
        _poly(d, [(x, y), (x + s * 0.5, y), (x + s * 0.5, y + s * 0.35),
                  (x + s, y + s * 0.35), (x + s, y + s), (x + s * 0.5, y + s),
                  (x + s * 0.5, y + s * 0.65), (x, y + s * 0.65)], c, 220)
    _tiles(p, s, s, one)


def f_floral(p, d, img, mode="leaf", s=90):
    if mode == "paisley":
        def one(x, y, ix, iy):
            cx, cy = x + s / 2, y + s / 2
            _ell(d, [cx - s * 0.28, cy - s * 0.34, cx + s * 0.28, cy + s * 0.34], p.second, 200)
            _poly(d, [(cx, cy - s * 0.5), (cx + s * 0.2, cy - s * 0.2),
                      (cx, cy - s * 0.1), (cx - s * 0.2, cy - s * 0.2)], p.third, 210)
            _dot(d, cx, cy, s * 0.10, p.body, 200)
        _tiles(p, s, s, one)
    elif mode == "crane":
        def one(x, y, ix, iy):
            off = s / 2 if iy % 2 else 0
            cx, cy = x + off + s / 2, y + s / 2
            _poly(d, [(cx, cy - s * 0.4), (cx + s * 0.4, cy), (cx, cy + s * 0.4),
                      (cx - s * 0.4, cy)], p.second, 200)
            _line(d, [(cx - s * 0.4, cy), (cx + s * 0.4, cy)], p.third, 2, 190)
        _tiles(p, s, s, one)
    else:
        for _ in range(30):
            r = p.rng
            cx, cy = r.uniform(0, p.w), r.uniform(0, p.h)
            ln = r.uniform(0.10, 0.22) * p.w
            a = r.uniform(0, math.pi * 2)
            _poly(d, [(cx, cy), (cx + ln * math.cos(a), cy + ln * math.sin(a)),
                      (cx + ln * 0.6 * math.cos(a + 0.5), cy + ln * 0.6 * math.sin(a + 0.5))],
                  p.second if r.random() < 0.6 else p.third, 190)


def f_monogram(p, d, img, s=80, mode="letters"):
    def one(x, y, ix, iy):
        cx, cy = x + s / 2, y + s / 2
        if mode == "letters":
            _line(d, [(cx - s * 0.3, cy - s * 0.3), (cx - s * 0.3, cy + s * 0.3),
                      (cx + s * 0.3, cy + s * 0.3), (cx + s * 0.3, cy - s * 0.3)], p.second, 6, 200)
            _line(d, [(cx - s * 0.3, cy), (cx + s * 0.3, cy)], p.second, 6, 200)
        else:
            _ring(d, cx, cy, s * 0.3, p.second, 5, 200)
    _tiles(p, s, s, one)


def f_celtic(p, d, img, mode="knot"):
    """Refined Celtic interlaced knotwork and Greek key meander jacquard with calm chest zone."""
    if mode == "knot":
        step = 64.0
        for y in range(0, int(p.h), int(step)):
            if 0.26 * p.h < y < 0.60 * p.h:
                continue
            for x in range(0, int(p.w), int(step)):
                cx, cy = x + step * 0.5, y + step * 0.5
                _ring(d, cx, cy, step * 0.35, p.second, 1.2, 55)
                _ring(d, cx, cy, step * 0.20, p.third, 1.0, 45)
                _line(d, [(cx - step * 0.35, cy), (cx + step * 0.35, cy)], p.third, 1.0, 45)
                _line(d, [(cx, cy - step * 0.35), (cx, cy + step * 0.35)], p.third, 1.0, 45)
    elif mode == "greekkey":
        step = 56
        for y in range(0, int(p.h), step):
            if 0.26 * p.h < y < 0.60 * p.h:
                continue
            for x in range(0, int(p.w), step):
                pts = [(x, y + 44), (x, y + 12), (x + 44, y + 12), (x + 44, y + 32),
                       (x + 16, y + 32), (x + 16, y + 24)]
                _line(d, pts, p.second, 1.5, 60)


def f_seigaiha(p, d, img, rad=44):
    def one(x, y, ix, iy):
        off = rad if iy % 2 else 0
        cx, cy = x + off, y
        for k in range(1, 5):
            d.arc([cx - k * rad * 0.25, cy - k * rad * 0.25,
                   cx + k * rad * 0.25, cy + k * rad * 0.25], 180, 360,
                  fill=_alpha(p.second, 190), width=3)
    _tiles(p, rad, rad, one)


def f_stepfret(p, d, img, mode="aztec", s=70):
    def one(x, y, ix, iy):
        if mode == "aztec":
            _rect(d, [x + 8, y + 20, x + s - 8, y + 28], p.second, 220)
            _rect(d, [x + 8, y + 40, x + s - 8, y + 48], p.third, 200)
            _poly(d, [(x + s * 0.5, y + 4), (x + s * 0.72, y + 18),
                      (x + s * 0.5, y + 32), (x + s * 0.28, y + 18)], p.second, 220)
        else:
            _rect(d, [x, y, x + s * 0.5, y + s * 0.5], p.second, 220)
            _rect(d, [x + s * 0.5, y + s * 0.5, x + s, y + s], p.third, 220)
            _rect(d, [x + s * 0.2, y + s * 0.2, x + s * 0.8, y + s * 0.8], p.body, 255)
    _tiles(p, s, s, one)


def f_guilloche(p, d, img, mode="spiro", rings=26):
    cx, cy = p.w * 0.5, p.h * 0.5
    if mode == "spiro":
        for k in range(rings):
            rad = 20 + k * 14
            pts = []
            for j in range(120):
                a = 2 * math.pi * j / 120
                rr = rad * (1 + 0.10 * math.sin(a * 7 + k * 0.4))
                pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.85))
            _line(d, pts + [pts[0]], p.second, 1, 170)
    else:
        for y in range(0, int(p.h), 20):
            _line(d, [(0, y), (p.w, y)], p.second, 1, 150)
        _rect(d, [10, 10, p.w - 10, 40], p.third, 120)
        _rect(d, [10, p.h - 40, p.w - 10, p.h - 10], p.third, 120)


def f_camo2(p, d, img, n=26, soft=True):
    """Subtle atmospheric streetwear tonal camouflage with calm chest sponsor zone."""
    r = p.rng
    cols = [p.second, p.third, p.mid]
    for i in range(n):
        cx, cy = r.uniform(0, p.w), r.uniform(0, p.h)
        if 0.28 * p.h < cy < 0.58 * p.h:
            continue
        rad = r.uniform(0.06, 0.15) * p.w
        pts = [(cx + rad * math.cos(2 * math.pi * k / 12) * r.uniform(0.7, 1.2),
                cy + rad * math.sin(2 * math.pi * k / 12) * r.uniform(0.7, 1.2))
               for k in range(12)]
        _poly(d, pts, cols[i % 3], 45)


def f_animal(p, d, img, mode="tiger", n=18):
    """Subtle modern tonal animal print streetwear jacquard with calm chest sponsor zone."""
    r = p.rng
    if mode == "tiger":
        for _ in range(n):
            x = r.uniform(0, p.w)
            y0 = r.uniform(0, p.h)
            pts = []
            y = y0
            while y < p.h:
                if not (0.28 * p.h < y < 0.58 * p.h):
                    pts.append((x + math.sin(y / p.h * math.pi * 2 + x) * 12, y))
                y += 18
            if len(pts) > 1:
                _line(d, pts, p.second, 2.0, 50)
    else:
        for _ in range(n * 2):
            cx, cy = r.uniform(0, p.w), r.uniform(0, p.h)
            if not (0.28 * p.h < cy < 0.58 * p.h):
                _ring(d, cx, cy, r.uniform(4, 9), p.second, 1.2, 50)
                _dot(d, cx, cy, 1.2, p.third, 40)


def f_scales(p, d, img, s=46):
    def one(x, y, ix, iy):
        off = s / 2 if iy % 2 else 0
        cx, cy = x + off, y
        d.arc([cx - s * 0.5, cy - s * 0.5, cx + s * 0.5, cy + s * 0.5], 0, 180,
              fill=_alpha(p.second, 200), width=4)
        d.arc([cx - s * 0.5, cy, cx + s * 0.5, cy + s], 180, 360,
              fill=_alpha(p.third, 160), width=3)
    _tiles(p, s, s, one)


def f_feathers(p, d, img, n=40):
    r = p.rng
    for _ in range(n):
        cx, cy = r.uniform(0, p.w), r.uniform(0, p.h)
        ln = r.uniform(0.06, 0.16) * p.w
        a = r.uniform(0, math.pi * 2)
        tip = (cx + ln * math.cos(a), cy + ln * math.sin(a))
        base = (cx - ln * math.cos(a), cy - ln * math.sin(a))
        _line(d, [base, tip], p.second, 2, 200)
        for t in (0.3, 0.5, 0.7):
            bx = base[0] + (tip[0] - base[0]) * t
            by = base[1] + (tip[1] - base[1]) * t
            w = ln * 0.3 * (1 - t)
            _line(d, [(bx - w, by - w), (bx + w, by + w)], p.third, 1, 170)


# =========================================================================== #
#  catalog registry  (code -> name / category / renderer / kwargs)
# =========================================================================== #
CATALOG = {}


def _reg(code, name, cat, fn, **kw):
    CATALOG[code] = {"name": name, "cat": cat, "fn": fn, "kw": kw}


# ---- Category 1: Geometric & Angular Shards (001-045) --------------------- #
_reg("001", "Apex Shatter", "Geometric", f_shards, n=16)
_reg("002", "Prism Refraction", "Geometric", f_prism)
_reg("003", "Kinetic V-Shards", "Geometric", f_vshards)
_reg("004", "Low-Poly Topography", "Geometric", f_lowpoly)
_reg("005", "Diagonal Guillotine", "Geometric", f_slashes)
_reg("006", "Obsidian Splinter", "Geometric", f_shards, n=14, asym=True)
_reg("007", "Bauhaus Blocks", "Geometric", f_bauhaus)
_reg("008", "Diamond Matrix", "Geometric", f_diamonds)
_reg("009", "Origami Fold", "Geometric", f_creases)
_reg("010", "Isometric Cubes", "Geometric", f_isocubes)
_reg("011", "Chevron Fracture", "Geometric", f_chevfrac)
_reg("012", "Cyber Hex-Grid", "Geometric", f_hexgrid, solid=5)
_reg("013", "Stained Glass Mosaic", "Geometric", f_mosaic)
_reg("014", "Velocity Arrows", "Geometric", f_arrows)
_reg("015", "Monolith Pillars", "Geometric", f_pillars)
_reg("016", "Kaleidoscope Burst", "Geometric", f_radial)
_reg("017", "Sawtooth Ribbons", "Geometric", f_zigzag)
_reg("018", "Cubist Portrait", "Geometric", f_cubist)
_reg("019", "Tessellated Stars", "Geometric", f_stars4)
_reg("020", "Stealth Facets", "Geometric", f_facets)
_reg("021", "Offset Rhombus", "Geometric", f_rhombus)
_reg("022", "Laser Beam Cross", "Geometric", f_beams)
_reg("023", "Tangram Puzzle", "Geometric", f_tangram)
_reg("024", "Alpine Peaks", "Geometric", f_peaks)
_reg("025", "Fractured Sash", "Geometric", f_sash_slices)
_reg("026", "Micro-Triangle Dust", "Geometric", f_dust)
_reg("027", "Octagon Lattice", "Geometric", f_hexgrid, octa=True)
_reg("028", "Twin Bolt Slash", "Geometric", f_lightning)
_reg("029", "Penrose Tiles", "Geometric", f_penrose)
_reg("030", "Corner Wedge", "Geometric", f_wedge)
_reg("031", "Serrated Stripes", "Geometric", f_vstripes, count=11, width=0.42, mode="chevronfill")
_reg("032", "Vortex Triangles", "Geometric", f_spiral_tri)
_reg("033", "Brutalist Concrete Grid", "Geometric", f_bricks)
_reg("034", "Crystal Geode", "Geometric", f_geode)
_reg("035", "Arrowhead Rain", "Geometric", f_rain)
_reg("036", "Split-Angle Duo", "Geometric", f_split, mode="diag")
_reg("037", "Ribbon Weave", "Geometric", f_weave)
_reg("038", "Digital Pixel-Poly", "Geometric", f_pixelpoly)
_reg("039", "Horizon Wedges", "Geometric", f_horizon)
_reg("040", "Crest Shield Echo", "Geometric", f_shield)
_reg("041", "Carrara Marble", "Fluid", f_marble)
_reg("042", "Liquid Chrome", "Fluid", f_chrome)
_reg("043", "Ink Diffusion", "Fluid", f_bloom)
_reg("044", "Topographic Elevation", "Fluid", f_topo)
_reg("045", "Magma Flow", "Fluid", f_veins)

# ---- Category 2: Fluid, Marble & Liquid Distortion (041-080) -------------- #
_reg("046", "Silk Ripple", "Fluid", f_silk)
_reg("047", "Tie-Dye Modern", "Fluid", f_swirl)
_reg("048", "Ocean Current", "Fluid", f_flow)
_reg("049", "Oil Slick Iridescence", "Fluid", f_bands, count=14, a=110)
_reg("050", "Smoke Plume", "Fluid", f_veins, n=8, thick=8)
_reg("051", "Agate Slice", "Fluid", f_geode, rings=14)
_reg("052", "Soundwave Pulse", "Fluid", f_waves)
_reg("053", "Fingerprint Whirl", "Fluid", f_swirl, arms=1, turns=6, thick=4)
_reg("054", "Aurora Borealis", "Fluid", f_bands, vertical=True, count=16, wavy=0.02)
_reg("055", "Sand Dune Ripples", "Fluid", f_waves, count=22, amp=0.02, period=1.2)
_reg("056", "Marbled Paper", "Fluid", f_swirl, arms=10, turns=4, thick=3)
_reg("057", "Lava Lamp Blobs", "Fluid", f_bloom, cols=3, n=8)
_reg("058", "Malachite Swirl", "Fluid", f_marble, banded=True)
_reg("059", "Tsunami Crest", "Fluid", f_waves, count=6, amp=0.06, fill=True)
_reg("060", "Cellular Mitosis", "Fluid", f_bloom, cols=1, n=14, rmin=0.04, rmax=0.12)
_reg("061", "Acrylic Pour", "Fluid", f_flow, lines=18, curve=3)
_reg("062", "Thermal Heat-Map", "Fluid", f_topo, levels=14, step=30)
_reg("063", "Woodgrain Burl", "Fluid", f_marble, veins=30, thick=3, banded=True)
_reg("064", "Nebula Cloud", "Fluid", f_dots, n=700, cols=2)
_reg("065", "Acid Wash Denim", "Fluid", f_dots, n=2200, rmin=1, rmax=2.2, a=120)
_reg("066", "Melting Stripes", "Fluid", f_vstripes, mode="wavy", count=10)
_reg("067", "Wind Tunnel Streamlines", "Fluid", f_flow, lines=40, thick=1)
_reg("068", "Damask Fluid", "Fluid", f_bloom, cols=2, n=20, rmin=0.05, rmax=0.15)
_reg("069", "Plasma Arc", "Fluid", f_veins, n=16, branch=5)
_reg("070", "Pebble Bed", "Fluid", f_bloom, cols=1, n=40, rmin=0.03, rmax=0.07, a=210)
_reg("071", "Mirage Shimmer", "Fluid", f_waves, count=30, amp=0.012, thick=2)
_reg("072", "Batik Wax Crack", "Fluid", f_veins, n=30, branch=4, thick=2)
_reg("073", "Vortex Whirlpool", "Fluid", f_swirl, arms=5, turns=4)
_reg("074", "Feather Plume", "Fluid", f_plume)
_reg("075", "Coral Reef", "Fluid", f_veins, n=20, branch=6, thick=2, from_hem=False)
_reg("076", "Vaporwave Sunset", "Fluid", f_waves, count=12, fill=True)
_reg("077", "Glacial Melt", "Fluid", f_veins, n=14, thick=4)
_reg("078", "Silk Ribbon Twist", "Fluid", f_bands, count=3, vertical=True, wavy=0.05, a=160)
_reg("079", "Mudcrack Earth", "Fluid", f_mosaic, n=80)
_reg("080", "Nebula Vortex", "Fluid", f_swirl, arms=9, turns=3, dots=True)

# ---- Category 3: Reimagined Classics (081-125) ---------------------------- #
_reg("081", "Halftone Fade Stripes", "Classics", f_vstripes, mode="halftone")
_reg("082", "Brushstroke Stripes", "Classics", f_vstripes, mode="brush")
_reg("083", "Barcode Stripes", "Classics", f_vstripes, mode="barcode")
_reg("084", "Gradient-Shift Hoops", "Classics", f_hoops, mode="gradient")
_reg("085", "Pinstripe Sub-Pattern", "Classics", f_pinstripe, mode="sub")
_reg("086", "Interrupted Sponsor Band", "Classics", f_centerband, mode="interrupted")
_reg("087", "Diagonal Brush Sash", "Classics", f_sash, brush=1)
_reg("088", "Split-Center Half-and-Half", "Classics", f_split, mode="zig")
_reg("089", "Double-Helix Stripes", "Classics", f_bands, count=2, vertical=True, wavy=0.06, a=200)
_reg("090", "Offset Center Stripe", "Classics", f_centerband, mode="vband")
_reg("091", "Shadowed Hoops", "Classics", f_hoops, mode="shadow")
_reg("092", "Glitch Stripes", "Classics", f_vstripes, mode="glitch")
_reg("093", "Tapering Stripes", "Classics", f_vstripes, mode="taper")
_reg("094", "Checkerboard Fade", "Classics", f_check, mode="fade")
_reg("095", "Chevron Chest Band", "Classics", f_centerband, mode="chestband")
_reg("096", "Spray-Paint Stencil Stripes", "Classics", f_vstripes, mode="chalk")
_reg("097", "Multi-Line Pinstripe Clusters", "Classics", f_pinstripe, mode="cluster")
_reg("098", "Cross-Stitch Sash", "Classics", f_sash, stitch=1)
_reg("099", "Inverted Gradient Stripes", "Classics", f_vstripes, mode="invert")
_reg("100", "Broken Hoops", "Classics", f_hoops, mode="broken")
_reg("101", "Wavy Psychedelic Stripes", "Classics", f_vstripes, mode="wavy")
_reg("102", "Tartan / Plaid Modern", "Classics", f_plaid)
_reg("103", "Triple-Tone Sash", "Classics", f_sash, count=3, width=0.5)
_reg("104", "Neon Edge Stripes", "Classics", f_vstripes, mode="neon")
_reg("105", "Dotted Pinstripes", "Classics", f_pinstripe, mode="dots")
_reg("106", "Asymmetric Shoulder Hoops", "Classics", f_hoops, mode="asym")
_reg("107", "Ribbon Fold Stripes", "Classics", f_ribbonfold)
_reg("108", "Chalk-Line Stripes", "Classics", f_vstripes, mode="chalk")
_reg("109", "Pixel-Edge Hoops", "Classics", f_hoops, mode="pixel")
_reg("110", "Monochrome Tonal Stripes", "Classics", f_vstripes, mode="mono")
_reg("111", "Chevron-Filled Stripes", "Classics", f_vstripes, mode="chevronfill")
_reg("112", "Split-Diagonal Quarters", "Classics", f_split, mode="quarters")
_reg("113", "Speed-Line Sash", "Classics", f_sash, lines=20)
_reg("114", "Woven Basket Stripes", "Classics", f_woven)
_reg("115", "Watercolor Bleed Hoops", "Classics", f_hoops, mode="watercolor")
_reg("116", "Crest-Framed Stripes", "Classics", f_vstripes, mode="crestframe")
_reg("117", "Torn-Paper Stripes", "Classics", f_vstripes, mode="torn")
_reg("118", "Gradient Pinstripe Matrix", "Classics", f_pinstripe, mode="grad")
_reg("119", "Double-V Chest", "Classics", f_centerband, mode="doublev")
_reg("120", "Heritage Argyle", "Classics", f_argyle)
_reg("121", "Diagonal Pinstripe Fade", "Classics", f_vstripes, mode="gradient")
_reg("122", "Blocked Center Band", "Classics", f_centerband, mode="blocked")
_reg("123", "Segmented Hoops", "Classics", f_hoops, mode="segmented")
_reg("124", "Metallic Foil Stripes", "Classics", f_vstripes, mode="metallic")
_reg("125", "Minimalist Side-Panel Stripes", "Classics", f_vstripes, mode="sidepanel")

# ---- Category 4: Digital, Glitch & Tech-Futurism (126-165) ---------------- #
_reg("126", "VHS Tracking Glitch", "Digital", f_glitch, mode="vhs")
_reg("127", "PCB Circuit Board", "Digital", f_circuit, mode="pcb")
_reg("128", "Matrix Code Rain", "Digital", f_rain2, mode="matrix")
_reg("129", "Pixel Dissolve", "Digital", f_pixel, mode="dissolve")
_reg("130", "Scanline CRT", "Digital", f_scan, mode="crt")
_reg("131", "Wireframe 3D Mesh", "Digital", f_grid, mode="wireframe")
_reg("132", "QR / Data Matrix", "Digital", f_pixel, mode="qr")
_reg("133", "Sonar Radar Sweep", "Digital", f_radar, mode="sonar")
_reg("134", "Binary Pulse", "Digital", f_rain2, mode="binary")
_reg("135", "Cybernetic Armor Plates", "Digital", f_plate, mode="armor")
_reg("136", "Holographic Foil", "Digital", f_grid, mode="holo")
_reg("137", "Datamosh Smear", "Digital", f_glitch, mode="datamosh")
_reg("138", "Laser Lidar Scan", "Digital", f_scan, mode="lidar")
_reg("139", "HUD Target Reticles", "Digital", f_radar, mode="hud")
_reg("140", "Frequency Spectrum", "Digital", f_bars, mode="spectrum")
_reg("141", "Carbon Fiber Weave", "Digital", f_plate, mode="carbon")
_reg("142", "Neural Network Nodes", "Digital", f_circuit, mode="neural")
_reg("143", "Anaglyph 3D Shift", "Digital", f_glitch, mode="anaglyph")
_reg("144", "Hex-Code Camo", "Digital", f_pixel, mode="hexcamo")
_reg("145", "Fiber Optic Bundles", "Digital", f_streak, mode="fiber")
_reg("146", "Glitch Checkerboard", "Digital", f_check, mode="glitch")
_reg("147", "Micro-Dot Halftone Grid", "Digital", f_grid, mode="halftone")
_reg("148", "Synthwave Grid", "Digital", f_grid, mode="synth")
_reg("149", "Biometric ECG Line", "Digital", f_radar, mode="ecg")
_reg("150", "Fragmented QR Camo", "Digital", f_pixel, mode="camo")
_reg("151", "Optical Moire Interference", "Digital", f_grid, mode="moire")
_reg("152", "Neon Wire Contour", "Digital", f_topo, thick=3)
_reg("153", "Tech-Knit Ventilation Map", "Digital", f_mesh)
_reg("154", "Static TV Snow", "Digital", f_glitch, mode="static")
_reg("155", "Isometric Circuit City", "Digital", f_circuit, mode="isometric")
_reg("156", "Velocity Streaking", "Digital", f_streak, mode="velocity")
_reg("157", "Crypto Hash Blocks", "Digital", f_pixel, mode="crypto")
_reg("158", "Quantum Wavefunction", "Digital", f_waves, count=24, amp=0.05, period=6, thick=2)
_reg("159", "Sub-Pixel RGB Stripe", "Digital", f_scan, mode="subpixel")
_reg("160", "Laser-Etched Topology", "Digital", f_topo, a=120, thick=1)
_reg("161", "Digital Rain Chevron", "Digital", f_rain2, mode="chevron")
_reg("162", "Cyber Camo Splinter", "Digital", f_pixel, mode="camo")
_reg("163", "Telemetry Graph", "Digital", f_bars, mode="telemetry")
_reg("164", "Void Grid", "Digital", f_grid, mode="void")
_reg("165", "Electro-Static Arcs", "Digital", f_lightning, rows=(60, 180, 300, 420), thick=4)

# ---- Category 5: Architectural, Cultural & Bespoke Motifs (166-205) ------- #
_reg("166", "City Street Map", "Cultural", f_citymap, mode="streets")
_reg("167", "Stadium Roof Truss", "Cultural", f_truss, mode="roof")
_reg("168", "Art Deco Fan", "Cultural", f_artdeco, mode="fan")
_reg("169", "Azulejo / Zellige Tile", "Cultural", f_tile, shape="star")
_reg("170", "Gothic Rose Window", "Cultural", f_rosewin, mode="rose")
_reg("171", "Houndstooth Oversized", "Cultural", f_hound)
_reg("172", "Jacquard Floral", "Cultural", f_floral, mode="leaf")
_reg("173", "Heraldic Watermark", "Cultural", f_shield, scales=(1.1, 0.8, 0.5), thick=8)
_reg("174", "Brutalist Archways", "Cultural", f_artdeco, mode="archways")
_reg("175", "Crest Monogram Repeater", "Cultural", f_monogram, mode="letters")
_reg("176", "Celtic Knotwork", "Cultural", f_celtic, mode="knot")
_reg("177", "Japanese Seigaiha Waves", "Cultural", f_seigaiha)
_reg("178", "Aztec / Mayan Step-Fret", "Cultural", f_stepfret, mode="aztec")
_reg("179", "Guilloche Banknote Engraving", "Cultural", f_guilloche, mode="spiro")
_reg("180", "Subway Transit Map", "Cultural", f_citymap, mode="transit")
_reg("181", "Roman Mosaic Tesserae", "Cultural", f_tile, shape="square")
_reg("182", "Kente / Mudcloth Geometric", "Cultural", f_stepfret, mode="kente")
_reg("183", "Victorian Ironwork", "Cultural", f_artdeco, mode="ironwork")
_reg("184", "Bauhaus Grid Typography", "Cultural", f_monogram, mode="letters")
_reg("185", "Herringbone Tweed", "Cultural", f_woven)
_reg("186", "Compass Rose", "Cultural", f_rosewin, mode="compass")
_reg("187", "Skyline Silhouette", "Cultural", f_citymap, mode="skyline")
_reg("188", "Greek Key (Meander)", "Cultural", f_celtic, mode="greekkey")
_reg("189", "Paisley Modern", "Cultural", f_floral, mode="paisley")
_reg("190", "Cathedral Vault Ribs", "Cultural", f_truss, mode="vault")
_reg("191", "Tartan Heritage Check", "Cultural", f_plaid, cell=48, band=0.35)
_reg("192", "Origami Crane Tessellation", "Cultural", f_floral, mode="crane")
_reg("193", "Industrial Diamond Plate", "Cultural", f_plate, mode="diamond")
_reg("194", "Clockwork Gears", "Cultural", f_rosewin, mode="gears")
_reg("195", "Botanical Fern Fronds", "Cultural", f_plume, n=16)
_reg("196", "Nordic Knit Sweater", "Cultural", f_tile, shape="snow")
_reg("197", "Venetian Terrazzo", "Cultural", f_dots, n=1600, rmin=2, rmax=5, cols=2)
_reg("198", "Moorish Star Lattice", "Cultural", f_tile, shape="star")
_reg("199", "Bridge Suspension Cables", "Cultural", f_truss, mode="cables")
_reg("200", "Vintage Ticket Guilloche", "Cultural", f_guilloche, mode="ticket")
_reg("201", "Camo Woodland Modern", "Cultural", f_camo2)
_reg("202", "Tiger / Zebra Organic Stripes", "Cultural", f_animal, mode="tiger")
_reg("203", "Leopard Rosette Tonal", "Cultural", f_animal, mode="leopard")
_reg("204", "Snake / Dragon Scale", "Cultural", f_scales)
_reg("205", "Feather Camouflage", "Cultural", f_feathers)
_reg("206", "Iconic Daniel Hechter Center Stripe", "Classics", f_centerband, mode="hechter")
_reg("207", "Asymmetric Crest-Aligned Hechter Stripe", "Classics", f_centerband, mode="hechter_offset")
_reg("208", "Contemporary Brush Hechter Stripe", "Classics", f_centerband, mode="hechter_brush")
_reg("209", "Gradient Fade Hechter Stripe", "Classics", f_centerband, mode="hechter_gradient")

# =========================================================================== #
#  Category: 2026/2027 Modern Football & Streetwear Culture (210-220)
# =========================================================================== #
def f_acid_wash(p, d, img, n=800, rmin=1.5, rmax=4.5, a=45):
    """Organic cloudy mineral wash with soft vapor sweeps and fine micro-motes (no round pea blobs)."""
    r = p.rng
    # Layer 1: Soft broad tonal cloud sweeps (using low alpha broad ellipses)
    for _ in range(14):
        cy = r.uniform(0.1, 0.9) * p.h
        cx = r.uniform(0.1, 0.9) * p.w
        bw = r.uniform(0.25, 0.55) * p.w
        bh = r.uniform(0.06, 0.18) * p.h
        col = p.second if r.random() < 0.6 else p.third
        _ell(d, [cx - bw, cy - bh, cx + bw, cy + bh], col, a=18)
    # Layer 2: High-density micro-grain texture
    for _ in range(n):
        cx = r.uniform(0, p.w)
        cy = r.uniform(0, p.h)
        rad = r.uniform(rmin, rmax)
        col = p.second if r.random() < 0.65 else p.third
        alpha_val = r.randint(15, a)
        _dot(d, cx, cy, rad, col, a=alpha_val)


def f_warped_checks(p, d, img, cell=36, amp=14.0):
    """Op-Art wavy distorted checkerboard popular in Tokyo/London rave/streetwear."""
    ny = int(p.h / cell) + 2
    nx = int(p.w / cell) + 2
    for iy in range(ny):
        for ix in range(nx):
            if (ix + iy) % 2 == 1:
                y0 = iy * cell + math.sin(ix * 0.8 + p.var) * amp
                y1 = (iy + 1) * cell + math.sin(ix * 0.8 + p.var) * amp
                x0 = ix * cell + math.cos(iy * 0.8 + p.var) * amp
                x1 = (ix + 1) * cell + math.cos(iy * 0.8 + p.var) * amp
                _poly(d, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], p.second, a=175)


def f_halftone_dither(p, d, img, spacing=20, max_r=9.0):
    """Modern performance engineered micro-dither dot matrix."""
    ny = int(p.h / spacing) + 2
    nx = int(p.w / spacing) + 2
    for iy in range(ny):
        y = iy * spacing
        for ix in range(nx):
            x = ix * spacing
            diag = (x / p.w + y / p.h) * 0.5
            rad = max_r * (0.2 + 0.8 * math.sin(diag * math.pi + p.var * 0.5))
            if rad > 0.8:
                _dot(d, x, y, rad, p.second if (ix + iy) % 3 != 0 else p.third, a=190)


def f_soundwaves(p, d, img, bars=32, max_h=0.35):
    """Aerodynamic velocity micro-streaks with clean chest sponsor zone (no crude bar charts)."""
    step = p.w / float(bars)
    for i in range(bars):
        x = i * step
        # Keep chest sponsor zone calm
        _line(d, [(x, 0), (x, p.h * 0.26)], p.second, 2, a=80)
        _line(d, [(x, p.h * 0.58), (x, p.h)], p.second, 2, a=80)


def f_couture_monogram(p, d, img, step=28):
    """Subtle luxury micro-jacquard weave with delicate tonal threads and calm sponsor zone."""
    ny = int(p.h / step) + 2
    nx = int(p.w / step) + 2
    for iy in range(ny):
        y = iy * step
        # Keep chest sponsor zone calm (y between 28% and 56% of height)
        if 0.28 * p.h < y < 0.56 * p.h:
            continue
        off = (step / 2.0) if (iy % 2 == 1) else 0.0
        for ix in range(nx):
            x = ix * step + off
            # Delicate micro-diamond pin-weave (tiny, subtle luxury texture - no chunky wallpaper stars)
            _poly(d, [(x, y - 3), (x + 3, y), (x, y + 3), (x - 3, y)], p.second, a=35)
            _dot(d, x + step * 0.5, y + step * 0.5, 1.2, p.third, a=30)


def f_sashiko_stitch(p, d, img, step=32):
    """Refined tonal pique micro-stitch texture with calm chest sponsor zone."""
    ny = int(p.h / step) + 2
    nx = int(p.w / step) + 2
    for iy in range(ny):
        y = iy * step
        if 0.28 * p.h < y < 0.56 * p.h:
            continue
        off = (step * 0.5) if (iy % 2 == 1) else 0.0
        for ix in range(nx):
            x = ix * step + off
            # Delicate micro-dash stitches (tonal woven feel, no crude tablecloth crosses)
            _line(d, [(x - 3, y), (x + 3, y)], p.second, w=1.0, a=45)
            _dot(d, x, y, 0.8, p.third, a=35)


def f_velocity_warp(p, d, img, n=24, angle=0.45):
    """High-speed aerodynamic streaks with gradient feathering and tapered terminals."""
    r = p.rng
    for i in range(n):
        y = (i / float(n)) * p.h + r.uniform(-15, 15)
        x = r.uniform(0.1, 0.9) * p.w
        length = r.uniform(70, 240)
        thick = r.uniform(3, 10)
        dx = length * math.cos(angle)
        dy = length * math.sin(angle)
        col = p.second if r.random() < 0.7 else p.third
        _line(d, [(x, y), (x + dx, y + dy)], col, w=thick, a=195)
        if thick > 6:
            _line(d, [(x - 6, y + 6), (x + dx * 0.8 - 6, y + dy * 0.8 + 6)],
                  p.third, w=2, a=160)


def f_thermal_topo(p, d, img, rings=16, step=28):
    """Gorpcore / outdoor elevation terrain contour map with altitude layers."""
    cx, cy = p.w * 0.5, p.h * 0.48
    for i in range(rings, 0, -1):
        rad = i * step
        col = p.second if i % 2 == 0 else p.third
        alpha = int(90 + 130 * (1.0 - i / float(rings)))
        pts = []
        for a in range(0, 360, 10):
            rad_ang = math.radians(a)
            perturb = 1.0 + 0.22 * math.sin(rad_ang * 3 + i * 0.4 + p.var) + 0.12 * math.cos(rad_ang * 5)
            pts.append((cx + rad * perturb * math.cos(rad_ang),
                        cy + rad * perturb * math.sin(rad_ang) * 0.9))
        _poly(d, pts, col, a=alpha)
        _line(d, pts + [pts[0]], p.second, w=2, a=230)


def f_glitch_aurora(p, d, img, bands=18):
    """Cyberpunk chromatic scanline glitch interference with offset laser slashes."""
    r = p.rng
    for i in range(bands):
        y = r.uniform(0, p.h)
        bh = r.uniform(4, 22)
        shift = r.uniform(-35, 35)
        _rect(d, [0, y, p.w, y + bh], p.second, a=110)
        _rect(d, [p.w * 0.15 + shift, y, p.w * 0.85 + shift, y + bh * 0.6], p.third, a=175)
        _line(d, [(0, y + bh), (p.w, y + bh)], p.second, w=1.5, a=220)


def f_blueprint_truss(p, d, img, grid=45):
    """Technical architectural blueprint grid, stadium truss diagonals, and coordinate marks."""
    for x in range(0, p.w, grid):
        _line(d, [(x, 0), (x, p.h)], p.second, w=1, a=120)
    for y in range(0, p.h, grid):
        _line(d, [(0, y), (p.w, y)], p.second, w=1, a=120)
    for x in range(-p.h, p.w + p.h, grid * 2):
        _line(d, [(x, 0), (x + p.h, p.h)], p.third, w=1.5, a=140)
    for x in range(grid, p.w, grid * 2):
        for y in range(grid, p.h, grid * 2):
            _line(d, [(x - 6, y), (x + 6, y)], p.second, w=2, a=210)
            _line(d, [(x, y - 6), (x, y + 6)], p.second, w=2, a=210)


def f_liquid_wave(p, d, img, waves=14, amp=38.0):
    """Venezia FC / luxury high-fashion undulating silk waves with smooth ripple curves."""
    step = p.h / float(waves)
    for i in range(waves + 2):
        y_base = (i - 1) * step
        pts_top = []
        pts_bot = []
        for x in range(0, p.w + 10, 10):
            phase = (x / float(p.w)) * 4.0 * math.pi + p.var * 0.8
            y = y_base + math.sin(phase) * amp + math.cos(phase * 0.5) * (amp * 0.4)
            pts_top.append((x, y))
            pts_bot.append((x, y + step * 0.65))
        poly = pts_top + list(reversed(pts_bot))
        col = p.second if i % 2 == 0 else p.third
        _poly(d, poly, col, a=150)
        _line(d, pts_top, p.second, w=2, a=220)


_reg("210", "Acid Mineral Wash Streetwear", "Fluid", f_acid_wash)
_reg("211", "Warped Checkerboard Op-Art", "Cultural", f_warped_checks)
_reg("212", "Cyber Halftone Dither Matrix", "Digital", f_halftone_dither)
_reg("213", "Audio Spectrum Soundwave", "Digital", f_soundwaves)
_reg("214", "Couture Monogram Quatrefoil", "Cultural", f_couture_monogram)
_reg("215", "Japanese Sashiko Cross-Stitch", "Cultural", f_sashiko_stitch)
_reg("216", "Velocity Streaks Aerodynamic", "Geometric", f_velocity_warp)
_reg("217", "Thermal Elevation Topo", "Fluid", f_thermal_topo)
_reg("218", "Cyber Glitch Aurora", "Digital", f_glitch_aurora)
_reg("219", "Architectural Blueprint Grid", "Cultural", f_blueprint_truss)
_reg("220", "Liquid Metallic Silk Waves", "Fluid", f_liquid_wave)


# =========================================================================== #
#  modifiers (A-E) and the public draw() API
# =========================================================================== #
def _alpha_ramp(img, y_top=0.0, y_bot=1.0, a_top=1.0, a_bot=0.0):
    import numpy as np
    arr = np.asarray(img).astype(np.float32)
    h = img.height
    yy = np.arange(h, dtype=np.float32)[:, None]
    denom = max(1.0, (y_bot - y_top) * h)
    t = np.clip((yy - y_top * h) / denom, 0.0, 1.0)
    ramp = a_top * (1.0 - t) + a_bot * t
    arr[:, :, 3] *= ramp
    img.paste(Image.fromarray(arr.astype("uint8"), "RGBA"), (0, 0))
    return img


def apply_modifier(overlay, mod, p):
    """Apply structural modifier A..E to a pattern overlay (returns a new image).

    A  Full Sublimation   - unchanged (pattern covers the whole torso tile)
    B  Torso-Only Focus   - fade the pattern out over the shoulder band
    C  Hem-Up Fade        - bold at the hem, 0% at the chest
    D  Diagonal Sash Mask - clip the pattern inside a shoulder->hip sash
    E  Tonal Jacquard     - recolor to a body shade + soft highlight edge
    """
    import numpy as np
    mod = (mod or "").upper()
    if mod in ("", "A"):
        return overlay
    arr = np.asarray(overlay).astype(np.float32)
    h, w = arr.shape[:2]
    alpha = arr[:, :, 3].copy()
    if mod == "B":
        yy = np.arange(h, dtype=np.float32)[:, None]
        keep = np.clip((yy - 0.10 * h) / (0.12 * h), 0.0, 1.0)
        arr[:, :, 3] = alpha * keep
    elif mod == "C":
        yy = np.arange(h, dtype=np.float32)[:, None]
        ramp = np.clip((yy - 0.30 * h) / (0.70 * h), 0.0, 1.0)
        arr[:, :, 3] = alpha * ramp
    elif mod == "D":
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        dd = (xx / w) + (yy / h)
        m = np.clip(1.0 - np.abs(dd - 1.0) / 0.22, 0.0, 1.0)
        arr[:, :, 3] = alpha * m
    elif mod == "E":
        rgb = arr[:, :, :3]
        lum = (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]) / 255.0
        # Rich engineered jacquard depth: deep woven shadow (0.74) to crisp light reflection (1.26)
        f = 0.74 + 0.52 * lum
        body = np.array(p.body, dtype=np.float32)
        second = np.array(p.second, dtype=np.float32) if (hasattr(p, "second") and p.second) else body
        hl_weight = np.clip((lum - 0.48) / 0.52, 0.0, 1.0) * 0.14
        for i in range(3):
            val = body[i] * f
            val = val * (1.0 - hl_weight) + second[i] * hl_weight
            arr[:, :, i] = np.clip(val, 0, 255)
        arr[:, :, 3] = alpha * 0.95
    out = Image.fromarray(arr.astype("uint8"), "RGBA")
    if mod == "E":
        from PIL import ImageChops, ImageFilter
        al = out.getchannel("A")
        edge = ImageChops.subtract(al, al.filter(ImageFilter.MinFilter(3)))
        body_col = tuple(int(v) for v in p.body[:3])
        # Visible woven jacquard highlight ridge: 22-28% brighter than body color
        hl_rgb = tuple(min(255, int(c * 1.25 + 14)) for c in body_col)
        hl = Image.new("RGBA", out.size, hl_rgb + (0,))
        hl.putalpha(edge.point(lambda v: int(v * 0.45)))
        out = Image.alpha_composite(out, hl)
    return out


def _split_spec(spec):
    s = str(spec).strip().upper()
    if "-" in s:
        code, mod = s.rsplit("-", 1)
        if mod in ("A", "B", "C", "D", "E"):
            return code, mod
        return s, None
    return s, None


def is_code(spec):
    if not spec:
        return False
    if str(spec).lower() in ("plain", "solid", "none"):
        return True
    try:
        return _split_spec(spec)[0] in CATALOG
    except Exception:                                     # noqa: BLE001
        return False


def codes():
    return sorted(CATALOG)


def list_catalog():
    return [(c, CATALOG[c]["name"], CATALOG[c]["cat"]) for c in sorted(CATALOG)]


def draw(img, spec, body, second, third=None, var=0, ws=0, rng=None):
    """Paint catalog `spec` (e.g. "127-B") onto `img` (an RGBA canvas)."""
    if not spec or str(spec).lower() in ("plain", "solid", "none"):
        base = Image.new("RGBA", img.size, tuple(body) + (255,))
        img.paste(base, (0, 0))
        return img

    code, mod = _split_spec(spec)
    entry = CATALOG.get(code)
    if entry is None:
        raise KeyError("unknown pattern code: %r" % (spec,))
    p = P(body, second, third, var, ws, rng)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay, "RGBA")
    entry["fn"](p, d, overlay, **entry.get("kw", {}))
    if mod:
        overlay = apply_modifier(overlay, mod, p)
    base = Image.new("RGBA", img.size, tuple(body) + (255,))
    base.alpha_composite(overlay)
    img.paste(base, (0, 0))
    return img


# =========================================================================== #
#  self-test / CLI
# =========================================================================== #
if __name__ == "__main__":
    import sys
    from collections import Counter

    import numpy as np

    # `python kit_patterns.py sheet <out.png>` -> labelled contact sheet of all
    # 205 archetypes (body/second/third = Chelsea home palette), for eyeballing.
    if len(sys.argv) > 2 and sys.argv[1] == "sheet":
        from PIL import ImageDraw, ImageFont
        cols, cell, pad, lab = 10, 150, 6, 18
        items = list_catalog()
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (cell + pad) + pad,
                                  rows * (cell + lab + pad) + pad), (24, 26, 30))
        sd = ImageDraw.Draw(sheet)
        try:
            font = ImageFont.truetype("arialbd.ttf", 12)
        except Exception:                                 # noqa: BLE001
            font = ImageFont.load_default()
        b, s2, t3 = (0, 76, 165), (245, 245, 245), (200, 32, 48)
        for i, (code, name, cat) in enumerate(items):
            im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            draw(im, code, b, s2, t3, var=int(code) % 3, ws=int(code) % 8)
            im = im.convert("RGB").crop((108, 40, 372, 470)).resize((cell, cell))
            x = pad + (i % cols) * (cell + pad)
            y = pad + (i // cols) * (cell + lab + pad)
            sd.text((x, y), "%s %s" % (code, name[:14]), fill=(225, 228, 235), font=font)
            sheet.paste(im, (x, y + lab))
        sheet.save(sys.argv[2])
        print("wrote", sys.argv[2], "(%d patterns)" % len(items))
        sys.exit(0)

    only = sys.argv[1] if len(sys.argv) > 1 else None
    body, second, third = (0, 76, 165), (245, 245, 245), (200, 32, 48)
    bad = []
    cats = Counter()
    mods = ("", "-A", "-B", "-C", "-D", "-E")
    for code in codes():
        cats[CATALOG[code]["cat"]] += 1
        if only and not code.startswith(only):
            continue
        for mod in mods:
            spec = code + mod
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            try:
                draw(img, spec, body, second, third, var=int(code) % 3, ws=int(code) % 8)
            except Exception as exc:                      # noqa: BLE001
                bad.append((spec, repr(exc)))
                continue
            a = np.asarray(img.convert("RGB")).astype(np.float32)
            if float(a.std()) < 6:
                bad.append((spec, "blank/low-variance std=%.2f" % float(a.std())))
    print("catalog: %d codes x %d modifiers" % (len(CATALOG), len(mods)))
    for k, v in sorted(cats.items()):
        print("  %-9s %d" % (k, v))
    if bad:
        print("PROBLEMS (%d):" % len(bad))
        for spec, msg in bad[:40]:
            print("  %s: %s" % (spec, msg))
        sys.exit(1)
    print("all %d specs render OK" % (len(CATALOG) * len(mods) if not only else 0))

