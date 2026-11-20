"""Sponsor Logo Builder for PES 2021 / SP Football Life KitGenerator.

Generates 140+ premier, authentic, real-world football kit sponsor logos
spanning Airlines, Betting companies, Banks & Financial institutions, Tech,
Telecom, Automotive, Crypto, Energy, Insurance, and Beverages.

All logos are rendered with 4x supersampling (SS=4) for ultra-sharp vector-grade
anti-aliasing, and produce both `<brand>.png` (full colour) and `<brand>_white.png`
(crisp white silhouette with matching alpha).

Crucially, all logos are designed for football shirts:
- Clean, transparent-background wordmarks and emblems (no clunky solid filled
  colored rectangular stickers that blot out jersey stripes and turn into white bricks).
- Emblems with internal symbols/letters use TRANSPARENT ALPHA CUTOUTS (negative space)
  so that the jersey fabric shows through in color, and dark kits show through in white!
"""

import math
import os
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

SS = 4  # 4x supersampling

def get_font(size, bold=True, style='sans'):
    """Cross-platform font loader (macOS, Windows, Linux)."""
    candidates = {
        'sans_bold': [
            '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
            '/System/Library/Fonts/HelveticaNeue.ttc',
            r'C:\Windows\Fonts\arialbd.ttf',
            r'C:\Windows\Fonts\segoeuib.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
        ],
        'sans_heavy': [
            '/System/Library/Fonts/Supplemental/Arial Black.ttf',
            '/System/Library/Fonts/Supplemental/Impact.ttf',
            r'C:\Windows\Fonts\ariblk.ttf',
            r'C:\Windows\Fonts\impact.ttf',
            r'C:\Windows\Fonts\bahnschrift.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
        ],
        'condensed': [
            '/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf',
            '/System/Library/Fonts/Supplemental/Impact.ttf',
            r'C:\Windows\Fonts\impact.ttf',
            r'C:\Windows\Fonts\bahnschrift.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
        ],
        'modern': [
            '/System/Library/Fonts/Supplemental/Futura.ttc',
            '/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf',
            r'C:\Windows\Fonts\bahnschrift.ttf',
            r'C:\Windows\Fonts\segoeuib.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
        ],
        'tech': [
            '/System/Library/Fonts/Supplemental/Trebuchet MS Bold.ttf',
            '/System/Library/Fonts/Supplemental/Verdana Bold.ttf',
            r'C:\Windows\Fonts\trebucbd.ttf',
            r'C:\Windows\Fonts\verdana.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
        ],
        'serif': [
            '/System/Library/Fonts/Supplemental/Georgia Bold.ttf',
            '/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf',
            r'C:\Windows\Fonts\georgiab.ttf',
            r'C:\Windows\Fonts\timesbd.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf'
        ],
        'script': [
            '/System/Library/Fonts/Supplemental/Brush Script.ttf',
            '/System/Library/Fonts/Supplemental/Zapfino.ttf',
            r'C:\Windows\Fonts\BRUSHSCI.TTF',
            '/System/Library/Fonts/Supplemental/Georgia Bold.ttf'
        ]
    }
    for p in candidates.get(style, candidates['sans_bold']):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    # Fallback to standard bold
    for p in candidates['sans_bold']:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def finalize_logo(im, max_w=900, max_h=260, padding=14):
    """Downsample from SS=4 using Lanczos, trim to content bounding box, and pad slightly."""
    res = im.resize((im.width // SS, im.height // SS), Image.LANCZOS)
    bbox = res.getbbox()
    if not bbox:
        return res
    cropped = res.crop(bbox)
    pw, ph = cropped.width + padding * 2, cropped.height + padding * 2
    out = Image.new('RGBA', (pw, ph), (0, 0, 0, 0))
    out.alpha_composite(cropped, (padding, padding))
    return out

def make_white_silhouette(img):
    """Return crisp white silhouette preserving the exact alpha transparency channel."""
    arr = np.array(img).copy()
    arr[:, :, :3] = 255
    return Image.fromarray(arr)

def hexc(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def P(x, y):
    return (int(x * SS), int(y * SS))

# ==============================================================================
# Helper Drawing Primitives
# ==============================================================================

def make_cutout_emblem(draw_base, draw_cutout, w, h, col):
    """Create an emblem where internal shapes are transparent alpha cutouts."""
    mask = Image.new('L', (w, h), 0)
    d_m = ImageDraw.Draw(mask)
    draw_base(d_m)
    draw_cutout(d_m)
    
    col_rgba = col if len(col) == 4 else col + (255,)
    emblem = Image.new('RGBA', (w, h), col_rgba)
    emblem.putalpha(mask)
    return emblem

def draw_wordmark(text, text_col, style='sans_heavy', size=115, tracking=2, italic_slant=0,
                  underline=None, accent_dot=None, prefix_fn=None):
    W, H = 1000 * SS, 260 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(size * SS, style=style)
    
    start_x = 40 * SS
    if prefix_fn:
        pw = prefix_fn(d, start_x, 130 * SS)
        start_x += pw + 25 * SS
        
    x = start_x
    y = int((260 - size * 1.05) / 2 * SS)
    col = text_col if len(text_col) == 4 else text_col + (255,)
    
    for ch in text:
        d.text((x, y), ch, font=f, fill=col)
        x += int(d.textlength(ch, font=f) + tracking * SS)
        
    if underline:
        ucol, uy, uh = underline
        d.rectangle([start_x, int(uy * SS), x - int(tracking * SS), int((uy + uh) * SS)], fill=ucol)
        
    if accent_dot:
        ax, ay, ar, acol = accent_dot
        d.ellipse([P(ax - ar, ay - ar), P(ax + ar, ay + ar)], fill=acol)
        
    if italic_slant != 0:
        # Affine transform for italic slant
        m = 1.0, math.tan(math.radians(-italic_slant)), 0.0, 0.0, 1.0, 0.0
        im = im.transform(im.size, Image.AFFINE, m, Image.BILINEAR)
        
    return finalize_logo(im)

def draw_lockup(emblem_fn_or_img, text, text_col, subtitle=None, sub_col=None, style='sans_bold',
                sub_style='modern', size=95, sub_size=36, spacing=35, emblem_w=160, emblem_h=160):
    W, H = 1100 * SS, 260 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    
    ey = int((260 - emblem_h) / 2 * SS)
    if isinstance(emblem_fn_or_img, Image.Image):
        im.alpha_composite(emblem_fn_or_img, (40 * SS, ey))
    else:
        emblem_fn_or_img(d, 40 * SS, ey, emblem_w * SS, emblem_h * SS)
    
    tx = int((40 + emblem_w + spacing) * SS)
    f_title = get_font(size * SS, style=style)
    tcol = text_col if len(text_col) == 4 else text_col + (255,)
    
    if subtitle:
        ty = int((260 - (size + sub_size + 15)) / 2 * SS)
        d.text((tx, ty), text, font=f_title, fill=tcol)
        f_sub = get_font(sub_size * SS, style=sub_style)
        scol = (sub_col or text_col)
        scol = scol if len(scol) == 4 else scol + (255,)
        sy = ty + int((size + 15) * SS)
        sx = tx
        for ch in subtitle.upper():
            d.text((sx, sy), ch, font=f_sub, fill=scol)
            sx += int(d.textlength(ch, font=f_sub) + 4 * SS)
    else:
        ty = int((260 - size * 1.05) / 2 * SS)
        d.text((tx, ty), text, font=f_title, fill=tcol)
        
    return finalize_logo(im)

# ==============================================================================
# CATALOG OF 140+ BESPOKE / REALISTIC FOOTBALL SPONSORS
# ==============================================================================

BUILDERS = {}

# ------------------------------------------------------------------------------
# 1. AIRLINES & TOURISM
# ------------------------------------------------------------------------------

def build_fly_emirates():
    W, H = 900 * SS, 260 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (215, 25, 32, 255) # Emirates Red
    f_fly = get_font(52 * SS, style='serif')
    f_em = get_font(98 * SS, style='modern')
    d.text((70 * SS, 25 * SS), 'Fly', font=f_fly, fill=col)
    d.text((70 * SS, 88 * SS), 'Emirates', font=f_em, fill=col)
    # Sweeping calligraphic curved flourish
    d.arc([50 * SS, 195 * SS, 720 * SS, 235 * SS], start=10, end=170, fill=col, width=8 * SS)
    return finalize_logo(im)
BUILDERS['fly_emirates'] = build_fly_emirates

def build_etihad():
    def emblem(d, x, y, w, h):
        col = (189, 155, 96, 255) # Etihad Gold
        cx, cy = x + w // 2, y + h // 2
        r = w // 2 - 10 * SS
        pts1 = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        d.polygon(pts1, outline=col, width=8 * SS)
        pts2 = [(cx, cy - r // 2), (cx + r // 2, cy), (cx, cy + r // 2), (cx - r // 2, cy)]
        d.polygon(pts2, fill=col)
    return draw_lockup(emblem, 'ETIHAD', (189, 155, 96), subtitle='AIRWAYS', sub_col=(189, 155, 96),
                       style='modern', size=96, sub_size=36, emblem_w=140, emblem_h=140)
BUILDERS['etihad'] = build_etihad

def build_qatar_air():
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        d.polygon([(cx - 15 * SS, cy + 30 * SS), (cx - 25 * SS, cy - 40 * SS),
                   (cx, cy - 20 * SS), (cx + 25 * SS, cy - 40 * SS), (cx + 15 * SS, cy + 30 * SS)], fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (92, 6, 50, 255))
    return draw_lockup(em, 'QATAR', (92, 6, 50), subtitle='AIRWAYS', sub_col=(92, 6, 50),
                       style='serif', size=92, sub_size=34, emblem_w=140, emblem_h=140)
BUILDERS['qatar_air'] = build_qatar_air

def build_singapore_air():
    def emblem(d, x, y, w, h):
        col = (204, 160, 59, 255) # Singapore Gold
        cx, cy = x + w // 2, y + h // 2
        d.polygon([(x + 10 * SS, cy + 40 * SS), (cx, y + 10 * SS), (x + w - 10 * SS, cy - 20 * SS),
                   (cx + 20 * SS, cy + 10 * SS), (cx, cy + 50 * SS)], fill=col)
    return draw_lockup(emblem, 'SINGAPORE', (0, 32, 91), subtitle='AIRLINES', sub_col=(204, 160, 59),
                       style='modern', size=88, sub_size=32, emblem_w=150, emblem_h=150)
BUILDERS['singapore_air'] = build_singapore_air

def build_turkish_air():
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        d.arc([cx - 45 * SS, cy - 35 * SS, cx + 45 * SS, cy + 35 * SS], start=180, end=360, fill=0, width=12 * SS)
        d.polygon([(cx - 40 * SS, cy - 20 * SS), (cx + 30 * SS, cy + 20 * SS), (cx, cy)], fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (200, 16, 46, 255))
    return draw_lockup(em, 'TURKISH', (200, 16, 46), subtitle='AIRLINES', sub_col=(200, 16, 46),
                       style='modern', size=88, sub_size=32, emblem_w=140, emblem_h=140)
BUILDERS['turkish_air'] = build_turkish_air

def build_lufthansa():
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        d.polygon([(cx - 45 * SS, cy + 25 * SS), (cx + 40 * SS, cy - 35 * SS), (cx + 10 * SS, cy + 5 * SS)], fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (5, 22, 77, 255))
    return draw_lockup(em, 'Lufthansa', (5, 22, 77), style='sans_bold', size=95, emblem_w=140, emblem_h=140)
BUILDERS['lufthansa'] = build_lufthansa

def build_riyadh_air():
    def emblem(d, x, y, w, h):
        col = (72, 45, 92, 255) # Riyadh Lavender
        cx, cy = x + w // 2, y + h // 2
        for i in range(3):
            d.arc([cx - (50 - i * 15) * SS, cy - (50 - i * 15) * SS, cx + (50 - i * 15) * SS, cy + (50 - i * 15) * SS],
                  start=200, end=340, fill=col, width=10 * SS)
    return draw_lockup(emblem, 'RIYADH AIR', (72, 45, 92), style='modern', size=94, emblem_w=140, emblem_h=140)
BUILDERS['riyadh_air'] = build_riyadh_air

def build_saudia():
    def emblem(d, x, y, w, h):
        col = (0, 104, 56, 255) # Saudia Green
        cx, cy = x + w // 2, y + h // 2
        d.polygon([(cx - 15 * SS, cy + 30 * SS), (cx + 15 * SS, cy + 30 * SS), (cx, cy - 20 * SS)], fill=col)
        d.arc([cx - 40 * SS, cy - 60 * SS, cx + 40 * SS, cy - 10 * SS], start=160, end=380, fill=col, width=8 * SS)
    return draw_lockup(emblem, 'SAUDIA', (0, 104, 56), style='sans_bold', size=96, emblem_w=140, emblem_h=140)
BUILDERS['saudia'] = build_saudia

def build_virgin_atl():
    W, H = 900 * SS, 260 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (200, 16, 46, 255)
    f = get_font(95 * SS, style='script')
    d.text((60 * SS, 45 * SS), 'virgin atlantic', font=f, fill=col)
    return finalize_logo(im)
BUILDERS['virgin_atl'] = build_virgin_atl

def build_british_air():
    W, H = 950 * SS, 240 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(80 * SS, style='modern')
    d.text((50 * SS, 65 * SS), 'BRITISH AIRWAYS', font=f, fill=(7, 90, 170, 255))
    d.polygon([(780 * SS, 60 * SS), (890 * SS, 40 * SS), (830 * SS, 70 * SS)], fill=(235, 34, 38, 255))
    return finalize_logo(im)
BUILDERS['british_air'] = build_british_air

def build_air_france():
    W, H = 850 * SS, 240 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(85 * SS, style='modern')
    d.text((50 * SS, 65 * SS), 'AIRFRANCE', font=f, fill=(0, 33, 87, 255))
    d.rectangle([680 * SS, 75 * SS, 750 * SS, 135 * SS], fill=(237, 27, 45, 255))
    return finalize_logo(im)
BUILDERS['air_france'] = build_air_france

def build_qantas():
    def emblem(d, x, y, w, h):
        col = (224, 0, 27, 255)
        d.polygon([(x + 20 * SS, y + h - 10 * SS), (x + w - 10 * SS, y + 20 * SS), (x + w - 40 * SS, y + h - 10 * SS)], fill=col)
    return draw_lockup(emblem, 'QANTAS', (224, 0, 27), style='sans_heavy', size=96, emblem_w=140, emblem_h=140)
BUILDERS['qantas'] = build_qantas

def build_delta():
    def emblem(d, x, y, w, h):
        cx, cy = x + w // 2, y + h // 2
        d.polygon([(cx, y + 15 * SS), (x + w - 15 * SS, y + h - 15 * SS), (x + 15 * SS, y + h - 15 * SS)], fill=(224, 25, 51, 255))
        d.polygon([(cx, cy), (x + w - 35 * SS, y + h - 15 * SS), (x + 35 * SS, y + h - 15 * SS)], fill=(0, 51, 102, 255))
    return draw_lockup(emblem, 'DELTA', (0, 51, 102), style='sans_heavy', size=96, emblem_w=140, emblem_h=140)
BUILDERS['delta'] = build_delta

def build_visit_rwanda():
    W, H = 800 * SS, 260 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (18, 18, 18, 255)
    f = get_font(72 * SS, style='condensed')
    x1 = 70 * SS
    for ch in 'VISIT':
        d.text((x1, 35 * SS), ch, font=f, fill=col)
        x1 += int(d.textlength(ch, font=f) + 26 * SS)
    x2 = 70 * SS
    for ch in 'RWANDA':
        d.text((x2, 125 * SS), ch, font=f, fill=col)
        x2 += int(d.textlength(ch, font=f) + 22 * SS)
    return finalize_logo(im)
BUILDERS['visit_rwanda'] = build_visit_rwanda

def build_visit_saudi():
    W, H = 850 * SS, 240 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f_visit = get_font(65 * SS, style='modern')
    f_saudi = get_font(105 * SS, style='script')
    d.text((60 * SS, 60 * SS), 'visit', font=f_visit, fill=(0, 122, 135, 255))
    d.text((220 * SS, 45 * SS), 'Saudi', font=f_saudi, fill=(197, 155, 39, 255))
    return finalize_logo(im)
BUILDERS['visit_saudi'] = build_visit_saudi

def build_visit_dubai():
    W, H = 800 * SS, 240 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(110 * SS, style='modern')
    colors = [(0, 159, 227, 255), (230, 0, 126, 255), (140, 198, 63, 255), (243, 146, 0, 255), (105, 44, 145, 255)]
    x = 60 * SS
    for i, ch in enumerate('DUBAI'):
        d.text((x, 50 * SS), ch, font=f, fill=colors[i % len(colors)])
        x += int(d.textlength(ch, font=f) + 8 * SS)
    return finalize_logo(im)
BUILDERS['visit_dubai'] = build_visit_dubai

# ------------------------------------------------------------------------------
# 2. BETTING & GAMING
# ------------------------------------------------------------------------------

def build_betway():
    W, H = 700 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(110 * SS, style='sans_heavy')
    d.text((40 * SS, 35 * SS), 'betway', font=f, fill=(18, 18, 18, 255))
    d.ellipse([575 * SS, 130 * SS, 602 * SS, 157 * SS], fill=(0, 200, 83, 255))
    return finalize_logo(im)
BUILDERS['betway'] = build_betway

def build_stake():
    return draw_wordmark('stake', (15, 33, 46), style='sans_heavy', size=115, italic_slant=14)
BUILDERS['stake'] = build_stake

def build_1xbet():
    # Dynamic italic sports betting wordmark 1XBET (no solid background block!)
    W, H = 750 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(115 * SS, style='sans_heavy')
    d.text((50 * SS, 35 * SS), '1X', font=f, fill=(0, 229, 255, 255)) # Cyan
    x_bet = 50 * SS + int(d.textlength('1X', font=f)) + 10 * SS
    d.text((x_bet, 35 * SS), 'BET', font=f, fill=(30, 136, 229, 255)) # Blue
    m = 1.0, math.tan(math.radians(-14)), 0.0, 0.0, 1.0, 0.0
    im = im.transform(im.size, Image.AFFINE, m, Image.BILINEAR)
    return finalize_logo(im)
BUILDERS['1xbet'] = build_1xbet

def build_bet365():
    # Stadium capsule OUTLINE enclosing yellow bet and white 365 (not a solid green block!)
    W, H = 750 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col_outline = (18, 84, 56, 255) # Forest green
    f = get_font(90 * SS, style='sans_heavy')
    bx, by = 40 * SS, 35 * SS
    bw, bh = 600 * SS, 140 * SS
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=35 * SS, outline=col_outline, width=14 * SS)
    d.text((bx + 40 * SS, by + 20 * SS), 'bet', font=f, fill=(255, 230, 0, 255))
    x_365 = bx + 40 * SS + int(d.textlength('bet', font=f)) + 15 * SS
    d.text((x_365, by + 20 * SS), '365', font=f, fill=(18, 84, 56, 255))
    return finalize_logo(im)
BUILDERS['bet365'] = build_bet365

def build_bwin():
    W, H = 650 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(115 * SS, style='sans_heavy')
    d.text((40 * SS, 35 * SS), 'bw', font=f, fill=(24, 24, 24, 255))
    x_i = 40 * SS + int(d.textlength('bw', font=f))
    d.text((x_i, 35 * SS), 'i', font=f, fill=(24, 24, 24, 255))
    d.text((x_i + int(d.textlength('i', font=f)), 35 * SS), 'n', font=f, fill=(24, 24, 24, 255))
    d.ellipse([x_i + 8 * SS, 42 * SS, x_i + 28 * SS, 62 * SS], fill=(255, 204, 0, 255))
    return finalize_logo(im)
BUILDERS['bwin'] = build_bwin

def build_unibet():
    # Green circle with transparent cutout U (never collapses in white silhouette!)
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        f_u = get_font(100 * SS, style='serif')
        d.text((36 * SS, 10 * SS), 'U', font=f_u, fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (0, 89, 56, 255))
    return draw_lockup(em, 'UNIBET', (0, 89, 56), style='modern', size=96, emblem_w=140, emblem_h=140)
BUILDERS['unibet'] = build_unibet

def build_dafabet():
    # Crimson dafabet wordmark with golden crescent star crest (Celtic style, no solid block!)
    def emblem(d, x, y, w, h):
        cx, cy = x + w // 2, y + h // 2
        d.arc([cx - 40 * SS, cy - 40 * SS, cx + 40 * SS, cy + 40 * SS], start=45, end=315, fill=(255, 215, 0, 255), width=12 * SS)
        d.ellipse([cx + 5 * SS, cy - 10 * SS, cx + 25 * SS, cy + 10 * SS], fill=(255, 215, 0, 255))
    return draw_lockup(emblem, 'dafabet', (183, 28, 28), style='sans_heavy', size=105, emblem_w=120, emblem_h=120)
BUILDERS['dafabet'] = build_dafabet

def build_parimatch():
    # Electric neon yellow bold italic wordmark PARIMATCH (Chelsea style, no solid yellow block!)
    return draw_wordmark('PARIMATCH', (245, 255, 0), style='sans_heavy', size=105, italic_slant=14)
BUILDERS['parimatch'] = build_parimatch

def build_888sport():
    W, H = 750 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f_8 = get_font(105 * SS, style='modern')
    f_sp = get_font(75 * SS, style='modern')
    d.text((50 * SS, 35 * SS), '888', font=f_8, fill=(255, 90, 0, 255))
    d.text((360 * SS, 55 * SS), 'sport', font=f_sp, fill=(18, 18, 18, 255))
    return finalize_logo(im)
BUILDERS['888sport'] = build_888sport

def build_w88():
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        f = get_font(80 * SS, style='sans_heavy')
        d.text((28 * SS, 18 * SS), 'W', font=f, fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (229, 168, 35, 255))
    return draw_lockup(em, 'W88', (0, 43, 73), style='sans_heavy', size=96, emblem_w=140, emblem_h=140)
BUILDERS['w88'] = build_w88

def build_mansion():
    ew, eh = 140 * SS, 140 * SS
    def base(d):
        cx, cy = ew // 2, eh // 2
        d.polygon([(cx, 0), (ew, cy - 20 * SS), (ew - 20 * SS, eh), (cx, eh + 10 * SS), (20 * SS, eh), (0, cy - 20 * SS)], fill=255)
    def cutout(d):
        f_m = get_font(85 * SS, style='serif')
        d.text((ew // 2 - 38 * SS, 15 * SS), 'M', font=f_m, fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (158, 0, 0, 255))
    return draw_lockup(em, 'MANSION', (158, 0, 0), style='serif', size=92, emblem_w=140, emblem_h=140)
BUILDERS['mansion'] = build_mansion

def build_betsson():
    return draw_wordmark('betsson', (255, 89, 0), style='modern', size=115)
BUILDERS['betsson'] = build_betsson

def build_hollywoodbets():
    def emblem(d, x, y, w, h):
        cx, cy = x + w // 2, y + h // 2
        pts = []
        for k in range(10):
            r = (w // 2 - 10 * SS) if k % 2 == 0 else (w // 4)
            a = math.radians(k * 36 - 90)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        d.polygon(pts, fill=(255, 184, 0, 255))
    return draw_lockup(emblem, 'hollywoodbets', (74, 21, 75), style='modern', size=80, emblem_w=140, emblem_h=140)
BUILDERS['hollywoodbets'] = build_hollywoodbets

def build_bk8():
    # Bold navy & orange BK8 with athletic underline slash (no solid block!)
    W, H = 600 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(110 * SS, style='sans_heavy')
    d.text((50 * SS, 35 * SS), 'BK', font=f, fill=(12, 35, 64, 255))
    x_8 = 50 * SS + int(d.textlength('BK', font=f)) + 10 * SS
    d.text((x_8, 35 * SS), '8', font=f, fill=(255, 103, 31, 255))
    w_8 = int(d.textlength('8', font=f))
    d.polygon([(50 * SS, 160 * SS), (x_8 + w_8, 160 * SS), (x_8 + w_8 - 15 * SS, 175 * SS), (35 * SS, 175 * SS)], fill=(255, 103, 31, 255))
    return finalize_logo(im)
BUILDERS['bk8'] = build_bk8

def build_betano():
    # Circle with transparent cutout B + BETANO wordmark (Aston Villa / Porto style)
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        f_b = get_font(85 * SS, style='sans_heavy')
        d.text((36 * SS, 12 * SS), 'B', font=f_b, fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (255, 82, 0, 255))
    return draw_lockup(em, 'BETANO', (255, 82, 0), style='sans_heavy', size=96, emblem_w=140, emblem_h=140)
BUILDERS['betano'] = build_betano

def build_sportingbet():
    W, H = 850 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(95 * SS, style='modern')
    d.text((50 * SS, 45 * SS), 'sporting', font=f, fill=(0, 56, 130, 255))
    x_b = 50 * SS + int(d.textlength('sporting', font=f))
    d.text((x_b, 45 * SS), 'bet', font=f, fill=(213, 0, 0, 255))
    return finalize_logo(im)
BUILDERS['sportingbet'] = build_sportingbet

def build_leovegas():
    def emblem(d, x, y, w, h):
        col = (255, 90, 0, 255)
        cx, cy = x + w // 2, y + h // 2
        d.ellipse([cx - 30 * SS, cy - 10 * SS, cx + 30 * SS, cy + 40 * SS], fill=col)
        for dx in (-35, -12, 12, 35):
            d.ellipse([cx + (dx - 8) * SS, cy - 35 * SS, cx + (dx + 8) * SS, cy - 15 * SS], fill=col)
    return draw_lockup(emblem, 'LeoVegas', (255, 90, 0), style='sans_heavy', size=92, emblem_w=140, emblem_h=140)
BUILDERS['leovegas'] = build_leovegas

def build_betvictor():
    return draw_wordmark('BETVICTOR', (5, 28, 44), style='modern', size=100, tracking=4)
BUILDERS['betvictor'] = build_betvictor

def build_betfred():
    # Royal blue bold athletic wordmark BETFRED with red accent bar (no solid block!)
    W, H = 750 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(105 * SS, style='sans_heavy')
    d.text((50 * SS, 35 * SS), 'BETFRED', font=f, fill=(0, 75, 135, 255))
    d.rectangle([50 * SS, 155 * SS, 600 * SS, 170 * SS], fill=(218, 41, 28, 255))
    return finalize_logo(im)
BUILDERS['betfred'] = build_betfred

def build_draftkings():
    def emblem(d, x, y, w, h):
        col = (255, 179, 0, 255)
        cx, cy = x + w // 2, y + h // 2
        pts = [(x + 10 * SS, cy + 30 * SS), (x + 10 * SS, cy - 20 * SS), (cx - 25 * SS, cy),
               (cx, cy - 40 * SS), (cx + 25 * SS, cy), (x + w - 10 * SS, cy - 20 * SS), (x + w - 10 * SS, cy + 30 * SS)]
        d.polygon(pts, fill=col)
    return draw_lockup(emblem, 'DRAFTKINGS', (27, 94, 32), style='sans_heavy', size=88, emblem_w=140, emblem_h=140)
BUILDERS['draftkings'] = build_draftkings

# ------------------------------------------------------------------------------
# 3. BANKS & FINANCIAL INSTITUTIONS
# ------------------------------------------------------------------------------

def build_barclays():
    ew, eh = 140 * SS, 140 * SS
    def base(d):
        cx, cy = ew // 2, eh // 2
        d.polygon([(cx - 60 * SS, cy + 10 * SS), (cx - 30 * SS, cy - 50 * SS), (cx, cy - 30 * SS),
                   (cx + 30 * SS, cy - 50 * SS), (cx + 60 * SS, cy + 10 * SS), (cx + 20 * SS, cy + 30 * SS),
                   (cx, cy + 55 * SS), (cx - 20 * SS, cy + 30 * SS)], fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        d.polygon([(cx - 20 * SS, cy - 25 * SS), (cx, cy - 60 * SS), (cx + 20 * SS, cy - 25 * SS), (cx, cy - 15 * SS)], fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (0, 174, 239, 255))
    return draw_lockup(em, 'BARCLAYS', (0, 45, 98), style='modern', size=96, emblem_w=140, emblem_h=140)
BUILDERS['barclays'] = build_barclays

def build_santander():
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        d.polygon([(cx, cy - 45 * SS), (cx + 25 * SS, cy), (cx + 10 * SS, cy + 40 * SS),
                   (cx - 10 * SS, cy + 40 * SS), (cx - 25 * SS, cy)], fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (236, 0, 0, 255))
    return draw_lockup(em, 'santander', (236, 0, 0), style='sans_bold', size=96, emblem_w=140, emblem_h=140)
BUILDERS['santander'] = build_santander

def build_std_chartered():
    W, H = 900 * SS, 240 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = 90 * SS, 110 * SS
    d.arc([cx - 50 * SS, cy - 60 * SS, cx + 10 * SS, cy + 60 * SS], start=120, end=340, fill=(0, 160, 221, 255), width=18 * SS)
    d.arc([cx - 10 * SS, cy - 60 * SS, cx + 50 * SS, cy + 60 * SS], start=300, end=140, fill=(0, 154, 68, 255), width=18 * SS)
    f = get_font(65 * SS, style='sans_bold')
    d.text((170 * SS, 45 * SS), 'Standard', font=f, fill=(0, 45, 98, 255))
    d.text((170 * SS, 115 * SS), 'Chartered', font=f, fill=(0, 154, 68, 255))
    return finalize_logo(im)
BUILDERS['std_chartered'] = build_std_chartered

def build_hsbc():
    def emblem(d, x, y, w, h):
        col = (219, 0, 17, 255)
        cx, cy = x + w // 2, y + h // 2
        d.polygon([(cx - 50 * SS, cy - 50 * SS), (cx, cy), (cx - 50 * SS, cy + 50 * SS)], fill=col)
        d.polygon([(cx + 50 * SS, cy - 50 * SS), (cx, cy), (cx + 50 * SS, cy + 50 * SS)], fill=col)
    return draw_lockup(emblem, 'HSBC', (18, 18, 18), style='modern', size=100, emblem_w=140, emblem_h=140)
BUILDERS['hsbc'] = build_hsbc

def build_ubs():
    def emblem(d, x, y, w, h):
        col = (230, 0, 0, 255)
        cx, cy = x + w // 2, y + h // 2
        d.line([cx - 40 * SS, cy - 40 * SS, cx + 40 * SS, cy + 40 * SS], fill=col, width=10 * SS)
        d.line([cx + 40 * SS, cy - 40 * SS, cx - 40 * SS, cy + 40 * SS], fill=col, width=10 * SS)
        d.line([cx, cy - 50 * SS, cx, cy + 50 * SS], fill=col, width=10 * SS)
    return draw_lockup(emblem, 'UBS', (18, 18, 18), style='sans_heavy', size=105, emblem_w=140, emblem_h=140)
BUILDERS['ubs'] = build_ubs

def build_revolut():
    return draw_wordmark('Revolut', (0, 0, 0), style='modern', size=115, tracking=3)
BUILDERS['revolut'] = build_revolut

def build_chase():
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.regular_polygon((ew // 2, eh // 2, ew // 2 - 5 * SS), n_sides=8, fill=255)
    def cutout(d): d.ellipse([35 * SS, 35 * SS, ew - 35 * SS, eh - 35 * SS], fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (17, 122, 202, 255))
    return draw_lockup(em, 'CHASE', (17, 122, 202), style='modern', size=96, emblem_w=140, emblem_h=140)
BUILDERS['chase'] = build_chase

def build_bnp_paribas():
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.rounded_rectangle([0, 0, ew, eh], radius=15 * SS, fill=255)
    def cutout(d):
        for i in range(4):
            sx = (30 + i * 25) * SS
            sy = (70 - i * 15) * SS
            d.ellipse([sx - 10 * SS, sy - 10 * SS, sx + 10 * SS, sy + 10 * SS], fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (0, 145, 90, 255))
    return draw_lockup(em, 'BNP PARIBAS', (0, 145, 90), style='modern', size=88, emblem_w=140, emblem_h=140)
BUILDERS['bnp_paribas'] = build_bnp_paribas

def build_deutsche_bank():
    def emblem(d, x, y, w, h):
        col = (0, 24, 168, 255)
        d.rectangle([x, y, x + w, y + h], outline=col, width=16 * SS)
        d.line([x + 25 * SS, y + h - 25 * SS, x + w - 25 * SS, y + 25 * SS], fill=col, width=16 * SS)
    return draw_lockup(emblem, 'Deutsche Bank', (0, 24, 168), style='sans_bold', size=86, emblem_w=140, emblem_h=140)
BUILDERS['deutsche_bank'] = build_deutsche_bank

def build_caixabank():
    def emblem(d, x, y, w, h):
        col = (0, 122, 174, 255)
        cx, cy = x + w // 2, y + h // 2
        d.ellipse([cx - 40 * SS, cy - 40 * SS, cx + 40 * SS, cy + 40 * SS], fill=col)
        d.ellipse([cx + 10 * SS, cy - 25 * SS, cx + 30 * SS, cy - 5 * SS], fill=(255, 204, 0, 255))
    return draw_lockup(emblem, 'CaixaBank', (0, 122, 174), style='sans_bold', size=92, emblem_w=140, emblem_h=140)
BUILDERS['caixabank'] = build_caixabank

def build_intesa():
    return draw_wordmark('INTESA SANPAOLO', (0, 89, 59), style='modern', size=82, tracking=4)
BUILDERS['intesa'] = build_intesa

def build_ing():
    def emblem(d, x, y, w, h):
        col = (255, 98, 0, 255)
        cx, cy = x + w // 2, y + h // 2
        d.polygon([(cx - 40 * SS, cy + 40 * SS), (cx - 20 * SS, cy - 40 * SS), (cx + 20 * SS, cy - 20 * SS),
                   (cx + 40 * SS, cy + 40 * SS)], fill=col)
    return draw_lockup(emblem, 'ING', (255, 98, 0), style='sans_heavy', size=105, emblem_w=140, emblem_h=140)
BUILDERS['ing'] = build_ing

def build_bbva():
    return draw_wordmark('BBVA', (0, 68, 129), style='modern', size=115, tracking=6)
BUILDERS['bbva'] = build_bbva

def build_soc_gen():
    def emblem(d, x, y, w, h):
        d.rectangle([x, y, x + w, y + h // 2], fill=(226, 0, 26, 255))
        d.rectangle([x, y + h // 2, x + w, y + h], fill=(0, 0, 0, 255))
    return draw_lockup(emblem, 'SOCIETE GENERALE', (0, 0, 0), style='modern', size=78, emblem_w=140, emblem_h=140)
BUILDERS['soc_gen'] = build_soc_gen

def build_klarna():
    # Clean modern lowercase wordmark klarna. (no solid pink pill!)
    return draw_wordmark('klarna.', (255, 168, 205), style='sans_heavy', size=115)
BUILDERS['klarna'] = build_klarna

def build_paypal():
    def emblem(d, x, y, w, h):
        f = get_font(120 * SS, style='sans_heavy')
        d.text((x + 10 * SS, y - 5 * SS), 'P', font=f, fill=(0, 48, 135, 255))
        d.text((x + 35 * SS, y + 10 * SS), 'P', font=f, fill=(0, 121, 193, 255))
    return draw_lockup(emblem, 'PayPal', (0, 48, 135), style='sans_heavy', size=96, emblem_w=140, emblem_h=140)
BUILDERS['paypal'] = build_paypal

def build_stripe():
    return draw_wordmark('stripe', (99, 91, 255), style='sans_heavy', size=115)
BUILDERS['stripe'] = build_stripe

def build_wise():
    return draw_wordmark('WISE', (22, 51, 0), style='sans_heavy', size=115, tracking=4)
BUILDERS['wise'] = build_wise

def build_mastercard():
    def emblem(d, x, y, w, h):
        r = w // 3
        cy = y + h // 2
        d.ellipse([x + 10 * SS, cy - r, x + 10 * SS + 2 * r, cy + r], fill=(235, 0, 27, 255))
        d.ellipse([x + w - 10 * SS - 2 * r, cy - r, x + w - 10 * SS, cy + r], fill=(247, 158, 27, 255))
    return draw_lockup(emblem, 'mastercard', (24, 24, 24), style='modern', size=92, emblem_w=160, emblem_h=140)
BUILDERS['mastercard'] = build_mastercard

def build_visa():
    W, H = 650 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(110 * SS, style='sans_heavy')
    d.text((50 * SS, 40 * SS), 'VISA', font=f, fill=(26, 31, 113, 255))
    d.polygon([(50 * SS, 45 * SS), (80 * SS, 45 * SS), (50 * SS, 85 * SS)], fill=(247, 182, 0, 255))
    m = 1.0, math.tan(math.radians(-12)), 0.0, 0.0, 1.0, 0.0
    im = im.transform(im.size, Image.AFFINE, m, Image.BILINEAR)
    return finalize_logo(im)
BUILDERS['visa'] = build_visa

# ------------------------------------------------------------------------------
# 4. TECH, STREAMING, GAMING & ELECTRONICS
# ------------------------------------------------------------------------------

def build_spotify():
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        for i, rad in enumerate((45, 30, 15)):
            d.arc([cx - rad * SS, cy - (rad - 10) * SS, cx + rad * SS, cy + (rad + 10) * SS],
                  start=205, end=335, fill=0, width=8 * SS)
    em = make_cutout_emblem(base, cutout, ew, eh, (29, 185, 84, 255))
    return draw_lockup(em, 'Spotify', (18, 18, 18), style='sans_bold', size=98, emblem_w=140, emblem_h=140)
BUILDERS['spotify'] = build_spotify

def build_teamviewer():
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        d.polygon([(cx - 30 * SS, cy), (cx - 10 * SS, cy - 20 * SS), (cx - 10 * SS, cy - 8 * SS),
                   (cx + 25 * SS, cy - 8 * SS), (cx + 25 * SS, cy + 8 * SS), (cx - 10 * SS, cy + 8 * SS),
                   (cx - 10 * SS, cy + 20 * SS)], fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (14, 126, 228, 255))
    return draw_lockup(em, 'TeamViewer', (14, 126, 228), style='sans_bold', size=90, emblem_w=140, emblem_h=140)
BUILDERS['teamviewer'] = build_teamviewer

def build_rakuten():
    W, H = 750 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(105 * SS, style='modern')
    col = (191, 0, 0, 255)
    d.text((50 * SS, 35 * SS), 'Rakuten', font=f, fill=col)
    d.polygon([(60 * SS, 160 * SS), (450 * SS, 160 * SS), (480 * SS, 175 * SS), (450 * SS, 190 * SS), (60 * SS, 190 * SS)], fill=col)
    return finalize_logo(im)
BUILDERS['rakuten'] = build_rakuten

def build_samsung():
    return draw_wordmark('SAMSUNG', (20, 40, 160), style='modern', size=115, tracking=6)
BUILDERS['samsung'] = build_samsung

def build_sony():
    return draw_wordmark('SONY', (18, 18, 18), style='serif', size=115, tracking=8)
BUILDERS['sony'] = build_sony

def build_nintendo():
    # Iconic rounded pill outline with Nintendo inside (Fiorentina style, no solid red block!)
    W, H = 800 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (230, 0, 18, 255)
    f = get_font(95 * SS, style='sans_heavy')
    tw = sum(d.textlength(c, font=f) for c in 'Nintendo')
    bx, by = 40 * SS, 35 * SS
    bw, bh = int(tw + 70 * SS), 140 * SS
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=45 * SS, outline=col, width=14 * SS)
    d.text((bx + 35 * SS, by + 18 * SS), 'Nintendo', font=f, fill=col)
    return finalize_logo(im)
BUILDERS['nintendo'] = build_nintendo

def build_google_pixel():
    def emblem(d, x, y, w, h):
        cx, cy = x + w // 2, y + h // 2
        d.arc([x + 10 * SS, y + 10 * SS, x + w - 10 * SS, y + h - 10 * SS], start=45, end=315, fill=(66, 133, 244, 255), width=18 * SS)
        d.rectangle([cx, cy - 9 * SS, x + w - 10 * SS, cy + 9 * SS], fill=(66, 133, 244, 255))
    return draw_lockup(emblem, 'Google Pixel', (66, 133, 244), style='modern', size=88, emblem_w=140, emblem_h=140)
BUILDERS['google_pixel'] = build_google_pixel

def build_apple_tv():
    def emblem(d, x, y, w, h):
        col = (18, 18, 18, 255)
        cx, cy = x + w // 2, y + h // 2
        d.ellipse([cx - 40 * SS, cy - 35 * SS, cx + 40 * SS, cy + 45 * SS], fill=col)
        d.ellipse([cx, cy - 55 * SS, cx + 30 * SS, cy - 35 * SS], fill=col)
    return draw_lockup(emblem, 'tv+', (18, 18, 18), style='modern', size=110, emblem_w=140, emblem_h=140)
BUILDERS['apple_tv'] = build_apple_tv

def build_amazon_prime():
    W, H = 650 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(110 * SS, style='modern')
    d.text((50 * SS, 35 * SS), 'prime', font=f, fill=(0, 168, 225, 255))
    d.arc([60 * SS, 110 * SS, 360 * SS, 175 * SS], start=20, end=160, fill=(255, 153, 0, 255), width=10 * SS)
    return finalize_logo(im)
BUILDERS['amazon_prime'] = build_amazon_prime

def build_snapdragon():
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        d.polygon([(cx, cy - 40 * SS), (cx + 30 * SS, cy + 20 * SS), (cx - 30 * SS, cy + 20 * SS)], fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (255, 45, 32, 255))
    return draw_lockup(em, 'Snapdragon', (255, 45, 32), style='sans_heavy', size=88, emblem_w=140, emblem_h=140)
BUILDERS['snapdragon'] = build_snapdragon

def build_sharp():
    return draw_wordmark('SHARP', (230, 0, 18), style='serif', size=115, tracking=6)
BUILDERS['sharp'] = build_sharp

def build_jvc():
    return draw_wordmark('JVC', (228, 0, 43), style='condensed', size=130, tracking=8)
BUILDERS['jvc'] = build_jvc

def build_philips():
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.rounded_rectangle([0, 0, ew, eh], radius=20 * SS, fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        d.arc([cx - 40 * SS, cy - 25 * SS, cx + 40 * SS, cy + 25 * SS], start=0, end=180, fill=0, width=10 * SS)
    em = make_cutout_emblem(base, cutout, ew, eh, (11, 94, 215, 255))
    return draw_lockup(em, 'PHILIPS', (11, 94, 215), style='modern', size=96, emblem_w=140, emblem_h=140)
BUILDERS['philips'] = build_philips

def build_panasonic():
    return draw_wordmark('Panasonic', (0, 64, 152), style='modern', size=105, tracking=3)
BUILDERS['panasonic'] = build_panasonic

def build_tcl():
    return draw_wordmark('TCL', (237, 28, 36), style='sans_heavy', size=125, italic_slant=15)
BUILDERS['tcl'] = build_tcl

def build_hisense():
    return draw_wordmark('Hisense', (0, 163, 166), style='modern', size=110, tracking=2)
BUILDERS['hisense'] = build_hisense

def build_xbox():
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        d.line([cx - 35 * SS, cy - 35 * SS, cx + 35 * SS, cy + 35 * SS], fill=0, width=18 * SS)
        d.line([cx + 35 * SS, cy - 35 * SS, cx - 35 * SS, cy + 35 * SS], fill=0, width=18 * SS)
    em = make_cutout_emblem(base, cutout, ew, eh, (16, 124, 16, 255))
    return draw_lockup(em, 'XBOX', (16, 124, 16), style='sans_heavy', size=100, emblem_w=140, emblem_h=140)
BUILDERS['xbox'] = build_xbox

def build_playstation():
    def emblem(d, x, y, w, h):
        col = (0, 55, 145, 255)
        f = get_font(120 * SS, style='sans_heavy')
        d.text((x + 10 * SS, y - 10 * SS), 'P', font=f, fill=col)
        d.text((x + 35 * SS, y + 15 * SS), 'S', font=f, fill=(245, 166, 35, 255))
    return draw_lockup(emblem, 'PlayStation', (0, 55, 145), style='modern', size=88, emblem_w=140, emblem_h=140)
BUILDERS['playstation'] = build_playstation

def build_paramount():
    return draw_wordmark('Paramount+', (0, 100, 255), style='serif', size=105, tracking=3)
BUILDERS['paramount'] = build_paramount

def build_dazn():
    return draw_wordmark('DAZN', (18, 18, 18), style='sans_heavy', size=125, tracking=4)
BUILDERS['dazn'] = build_dazn

def build_intel():
    return draw_wordmark('intel', (0, 104, 181), style='modern', size=120)
BUILDERS['intel'] = build_intel

def build_lenovo():
    # Clean cyber red modern wordmark Lenovo (Inter Milan style, no solid red block!)
    return draw_wordmark('Lenovo', (226, 35, 26), style='modern', size=115, tracking=3)
BUILDERS['lenovo'] = build_lenovo

# ------------------------------------------------------------------------------
# 5. TELECOM & MOBILE
# ------------------------------------------------------------------------------

def build_vodafone():
    # Red circle with transparent quotation droplet cutout (never collapses!)
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        d.ellipse([cx - 25 * SS, cy - 35 * SS, cx + 25 * SS, cy + 20 * SS], fill=0)
        d.polygon([(cx - 25 * SS, cy), (cx, cy + 35 * SS), (cx + 15 * SS, cy + 10 * SS)], fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (230, 0, 0, 255))
    return draw_lockup(em, 'vodafone', (230, 0, 0), style='sans_bold', size=96, emblem_w=140, emblem_h=140)
BUILDERS['vodafone'] = build_vodafone

def build_t_mobile():
    W, H = 850 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (226, 0, 116, 255) # T-Mobile Magenta
    f = get_font(105 * SS, style='sans_heavy')
    d.text((50 * SS, 40 * SS), 'T-Mobile', font=f, fill=col)
    for dx in (540, 570, 600):
        d.rectangle([dx * SS, 110 * SS, (dx + 16) * SS, 126 * SS], fill=col)
    return finalize_logo(im)
BUILDERS['t_mobile'] = build_t_mobile

def build_o2():
    def emblem(d, x, y, w, h):
        col = (0, 25, 165, 255)
        for bx, by, br in ((30, 30, 25), (80, 50, 35), (50, 90, 20)):
            d.ellipse([x + (bx - br) * SS, y + (by - br) * SS, x + (bx + br) * SS, y + (by + br) * SS], outline=(0, 160, 233, 255), width=8 * SS)
    return draw_lockup(emblem, 'O2', (0, 25, 165), style='modern', size=115, emblem_w=140, emblem_h=140)
BUILDERS['o2'] = build_o2

def build_orange():
    def emblem(d, x, y, w, h):
        d.rectangle([x + 10 * SS, y + 10 * SS, x + w - 10 * SS, y + h - 10 * SS], fill=(255, 102, 0, 255))
    return draw_lockup(emblem, 'orange', (255, 102, 0), style='modern', size=96, emblem_w=140, emblem_h=140)
BUILDERS['orange'] = build_orange

def build_ee():
    # Two circles with transparent cutout E (fabric shows through E in both color and white!)
    W, H = 550 * SS, 220 * SS
    m = Image.new('L', (W, H), 0)
    d_m = ImageDraw.Draw(m)
    d_m.ellipse([50 * SS, 45 * SS, 170 * SS, 165 * SS], fill=255)
    d_m.ellipse([200 * SS, 45 * SS, 320 * SS, 165 * SS], fill=255)
    f = get_font(85 * SS, style='sans_heavy')
    d_m.text((85 * SS, 55 * SS), 'E', font=f, fill=0)
    d_m.text((235 * SS, 55 * SS), 'E', font=f, fill=0)
    
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 185 * SS, H], fill=(0, 122, 135, 255)) # Aqua
    d.rectangle([185 * SS, 0, W, H], fill=(255, 230, 0, 255)) # Yellow
    im.putalpha(m)
    return finalize_logo(im)
BUILDERS['ee'] = build_ee

def build_movistar():
    def emblem(d, x, y, w, h):
        col = (91, 197, 0, 255)
        cx, cy = x + w // 2, y + h // 2
        d.arc([cx - 45 * SS, cy - 40 * SS, cx, cy + 40 * SS], start=180, end=360, fill=col, width=16 * SS)
        d.arc([cx, cy - 40 * SS, cx + 45 * SS, cy + 40 * SS], start=180, end=360, fill=col, width=16 * SS)
    return draw_lockup(emblem, 'movistar', (0, 43, 73), style='modern', size=96, emblem_w=140, emblem_h=140)
BUILDERS['movistar'] = build_movistar

def build_telekom():
    return draw_wordmark('Telekom', (226, 0, 116), style='sans_heavy', size=110)
BUILDERS['telekom'] = build_telekom

def build_three():
    # Authentic Chelsea Three UK geometric stencil '3'
    W, H = 260 * SS, 260 * SS
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = W // 2, H // 2
    # Upper horizontal bar
    d.polygon([
        (cx - 75 * SS, cy - 105 * SS),
        (cx + 65 * SS, cy - 105 * SS),
        (cx + 65 * SS, cy - 65 * SS),
        (cx - 20 * SS, cy - 65 * SS),
        (cx - 50 * SS, cy - 105 * SS)
    ], fill=255)
    # Diagonal connector
    d.polygon([
        (cx + 15 * SS, cy - 65 * SS),
        (cx + 65 * SS, cy - 65 * SS),
        (cx + 5 * SS, cy + 10 * SS),
        (cx - 35 * SS, cy + 10 * SS)
    ], fill=255)
    # Bottom bowl (thick curve with inner cutout)
    d.pieslice([cx - 75 * SS, cy - 35 * SS, cx + 75 * SS, cy + 105 * SS], start=280, end=190, fill=255)
    # Inner cutout
    d.pieslice([cx - 35 * SS, cy + 5 * SS, cx + 35 * SS, cy + 70 * SS], start=280, end=190, fill=0)
    # Angled stencil slash
    d.line([(cx - 45 * SS, cy + 5 * SS), (cx + 15 * SS, cy + 5 * SS)], fill=0, width=12 * SS)
    col_img = Image.new('RGBA', (W, H), (18, 18, 22, 255))
    col_img.putalpha(mask)
    return finalize_logo(col_img)
BUILDERS['three'] = build_three

def build_zain():
    return draw_wordmark('Zain', (0, 133, 124), style='modern', size=115, tracking=3)
BUILDERS['zain'] = build_zain

def build_stc():
    return draw_wordmark('stc', (79, 0, 140), style='modern', size=120)
BUILDERS['stc'] = build_stc

def build_claro():
    # Bold red Claro wordmark with speech pebble circle accent (no solid red block!)
    W, H = 700 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(115 * SS, style='sans_heavy')
    d.text((50 * SS, 35 * SS), 'Claro', font=f, fill=(218, 41, 28, 255))
    cx = 50 * SS + int(d.textlength('Claro', font=f)) + 15 * SS
    d.ellipse([cx, 55 * SS, cx + 28 * SS, 83 * SS], fill=(218, 41, 28, 255))
    return finalize_logo(im)
BUILDERS['claro'] = build_claro

def build_rogers():
    def emblem(d, x, y, w, h):
        col = (218, 41, 28, 255)
        d.arc([x + 10 * SS, y + 10 * SS, x + w - 10 * SS, y + h - 10 * SS], start=45, end=315, fill=col, width=16 * SS)
    return draw_lockup(emblem, 'ROGERS', (218, 41, 28), style='modern', size=96, emblem_w=140, emblem_h=140)
BUILDERS['rogers'] = build_rogers

# ------------------------------------------------------------------------------
# 6. AUTOMOTIVE, TIRES & LUBRICANTS
# ------------------------------------------------------------------------------

def build_jeep():
    return draw_wordmark('Jeep', (24, 24, 24), style='condensed', size=135, tracking=8)
BUILDERS['jeep'] = build_jeep

def build_chevrolet():
    def emblem(d, x, y, w, h):
        col = (205, 152, 52, 255)
        cx, cy = x + w // 2, y + h // 2
        d.rectangle([x + 10 * SS, cy - 18 * SS, x + w - 10 * SS, cy + 18 * SS], fill=col)
        d.polygon([(cx - 25 * SS, y + 10 * SS), (cx + 25 * SS, y + 10 * SS), (cx + 15 * SS, y + h - 10 * SS), (cx - 35 * SS, y + h - 10 * SS)], fill=col)
    return draw_lockup(emblem, 'CHEVROLET', (18, 18, 18), style='modern', size=88, emblem_w=150, emblem_h=140)
BUILDERS['chevrolet'] = build_chevrolet

def build_audi():
    W, H = 850 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (45, 52, 54, 255)
    r = 35 * SS
    for i in range(4):
        cx = (100 + i * 45) * SS
        d.ellipse([cx - r, 110 * SS - r, cx + r, 110 * SS + r], outline=col, width=10 * SS)
    f = get_font(88 * SS, style='modern')
    d.text((360 * SS, 65 * SS), 'Audi', font=f, fill=col)
    return finalize_logo(im)
BUILDERS['audi'] = build_audi

def build_mercedes():
    def emblem(d, x, y, w, h):
        col = (45, 52, 54, 255)
        d.ellipse([x, y, x + w, y + h], outline=col, width=10 * SS)
        cx, cy = x + w // 2, y + h // 2
        d.line([cx, cy, cx, y + 10 * SS], fill=col, width=10 * SS)
        d.line([cx, cy, cx - 40 * SS, cy + 40 * SS], fill=col, width=10 * SS)
        d.line([cx, cy, cx + 40 * SS, cy + 40 * SS], fill=col, width=10 * SS)
    return draw_lockup(emblem, 'Mercedes-Benz', (45, 52, 54), style='serif', size=82, emblem_w=140, emblem_h=140)
BUILDERS['mercedes'] = build_mercedes

def build_bmw():
    def emblem(d, x, y, w, h):
        d.ellipse([x, y, x + w, y + h], outline=(18, 18, 18, 255), width=12 * SS)
        d.pieslice([x + 10 * SS, y + 10 * SS, x + w - 10 * SS, y + h - 10 * SS], 0, 90, fill=(0, 102, 177, 255))
        d.pieslice([x + 10 * SS, y + 10 * SS, x + w - 10 * SS, y + h - 10 * SS], 180, 270, fill=(0, 102, 177, 255))
    return draw_lockup(emblem, 'BMW', (18, 18, 18), style='sans_heavy', size=105, emblem_w=140, emblem_h=140)
BUILDERS['bmw'] = build_bmw

def build_hyundai():
    def emblem(d, x, y, w, h):
        col = (0, 44, 108, 255)
        d.ellipse([x, y + 10 * SS, x + w, y + h - 10 * SS], outline=col, width=12 * SS)
        cx, cy = x + w // 2, y + h // 2
        d.line([cx - 20 * SS, y + 25 * SS, cx - 10 * SS, y + h - 25 * SS], fill=col, width=14 * SS)
        d.line([cx + 10 * SS, y + 25 * SS, cx + 20 * SS, y + h - 25 * SS], fill=col, width=14 * SS)
        d.line([cx - 15 * SS, cy, cx + 15 * SS, cy], fill=col, width=12 * SS)
    return draw_lockup(emblem, 'HYUNDAI', (0, 44, 108), style='modern', size=92, emblem_w=150, emblem_h=140)
BUILDERS['hyundai'] = build_hyundai

def build_pirelli():
    W, H = 850 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (213, 43, 30, 255)
    f = get_font(105 * SS, style='sans_heavy')
    d.text((50 * SS, 35 * SS), 'IRELLI', font=f, fill=col)
    d.rectangle([45 * SS, 35 * SS, 600 * SS, 55 * SS], fill=col)
    d.rectangle([45 * SS, 35 * SS, 70 * SS, 150 * SS], fill=col)
    d.arc([30 * SS, 35 * SS, 110 * SS, 105 * SS], start=270, end=90, fill=col, width=18 * SS)
    return finalize_logo(im)
BUILDERS['pirelli'] = build_pirelli

def build_yokohama():
    def emblem(d, x, y, w, h):
        col = (230, 0, 18, 255)
        cx, cy = x + w // 2, y + h // 2
        d.polygon([(x + 10 * SS, y + 15 * SS), (cx - 10 * SS, cy), (cx - 10 * SS, y + h - 15 * SS),
                   (cx + 10 * SS, y + h - 15 * SS), (cx + 10 * SS, cy), (x + w - 10 * SS, y + 15 * SS)], fill=col)
    return draw_lockup(emblem, 'YOKOHAMA', (18, 18, 18), style='sans_heavy', size=90, emblem_w=140, emblem_h=140)
BUILDERS['yokohama'] = build_yokohama

def build_bridgestone():
    return draw_wordmark('BRIDGESTONE', (18, 18, 18), style='sans_heavy', size=96, tracking=4)
BUILDERS['bridgestone'] = build_bridgestone

def build_continental():
    return draw_wordmark('Continental', (255, 165, 0), style='sans_bold', size=98, tracking=3)
BUILDERS['continental'] = build_continental

def build_michelin():
    return draw_wordmark('MICHELIN', (33, 64, 154), style='sans_heavy', size=105, italic_slant=12)
BUILDERS['michelin'] = build_michelin

def build_honda():
    def emblem(d, x, y, w, h):
        col = (204, 0, 0, 255)
        d.rounded_rectangle([x, y, x + w, y + h], radius=15 * SS, outline=col, width=12 * SS)
        f_h = get_font(105 * SS, style='serif')
        d.text((x + 30 * SS, y + 10 * SS), 'H', font=f_h, fill=col)
    return draw_lockup(emblem, 'HONDA', (204, 0, 0), style='serif', size=96, emblem_w=140, emblem_h=140)
BUILDERS['honda'] = build_honda

def build_kia():
    return draw_wordmark('KIA', (187, 22, 43), style='modern', size=120, tracking=6)
BUILDERS['kia'] = build_kia

def build_nissan():
    def emblem(d, x, y, w, h):
        col = (195, 0, 47, 255)
        d.ellipse([x, y, x + w, y + h], outline=col, width=12 * SS)
        d.rectangle([x + 10 * SS, y + h // 2 - 15 * SS, x + w - 10 * SS, y + h // 2 + 15 * SS], fill=col)
    return draw_lockup(emblem, 'NISSAN', (195, 0, 47), style='modern', size=92, emblem_w=140, emblem_h=140)
BUILDERS['nissan'] = build_nissan

def build_alfa_romeo():
    return draw_wordmark('Alfa Romeo', (143, 29, 44), style='script', size=115)
BUILDERS['alfa_romeo'] = build_alfa_romeo

def build_castrol():
    def emblem(d, x, y, w, h):
        col = (237, 27, 45, 255)
        d.arc([x, y, x + w, y + h], start=45, end=315, fill=col, width=16 * SS)
        d.arc([x + 15 * SS, y + 15 * SS, x + w - 15 * SS, y + h - 15 * SS], start=200, end=40, fill=(0, 122, 51, 255), width=14 * SS)
    return draw_lockup(emblem, 'Castrol', (237, 27, 45), style='sans_heavy', size=96, emblem_w=140, emblem_h=140)
BUILDERS['castrol'] = build_castrol

def build_mobil1():
    W, H = 650 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f_mob = get_font(105 * SS, style='sans_heavy')
    d.text((50 * SS, 35 * SS), 'Mobil', font=f_mob, fill=(0, 51, 153, 255))
    x_1 = 50 * SS + int(d.textlength('Mobil', font=f_mob)) + 15 * SS
    d.text((x_1, 35 * SS), '1', font=f_mob, fill=(238, 28, 37, 255))
    return finalize_logo(im)
BUILDERS['mobil1'] = build_mobil1

def build_shell_helix():
    def emblem(d, x, y, w, h):
        col = (255, 209, 0, 255)
        d.polygon([(x + 20 * SS, y + h - 10 * SS), (x + w - 20 * SS, y + h - 10 * SS), (x + w, y + 30 * SS), (x + w // 2, y + 10 * SS), (x, y + 30 * SS)], fill=col)
    return draw_lockup(emblem, 'Shell HELIX', (221, 29, 33), style='sans_heavy', size=86, emblem_w=140, emblem_h=140)
BUILDERS['shell_helix'] = build_shell_helix

# ------------------------------------------------------------------------------
# 7. CRYPTO, WEB3 & DIGITAL ASSETS
# ------------------------------------------------------------------------------

def build_crypto_com():
    def emblem(d, x, y, w, h):
        col = (17, 153, 250, 255)
        cx, cy = x + w // 2, y + h // 2
        d.regular_polygon((cx, cy, w // 2 - 5 * SS), n_sides=6, fill=(11, 20, 38, 255))
        d.regular_polygon((cx, cy, w // 2 - 15 * SS), n_sides=6, outline=col, width=8 * SS)
    return draw_lockup(emblem, 'crypto.com', (11, 20, 38), style='modern', size=92, emblem_w=140, emblem_h=140)
BUILDERS['crypto_com'] = build_crypto_com

def build_binance():
    def emblem(d, x, y, w, h):
        col = (243, 186, 47, 255)
        cx, cy = x + w // 2, y + h // 2
        r = w // 2 - 10 * SS
        d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], outline=col, width=12 * SS)
        d.polygon([(cx, cy - r // 2), (cx + r // 2, cy), (cx, cy + r // 2), (cx - r // 2, cy)], fill=col)
    return draw_lockup(emblem, 'BINANCE', (243, 186, 47), style='modern', size=96, emblem_w=140, emblem_h=140)
BUILDERS['binance'] = build_binance

def build_okx():
    def emblem(d, x, y, w, h):
        for r in range(3):
            for c in range(3):
                if (r + c) % 2 == 0:
                    d.rectangle([x + (15 + c * 35) * SS, y + (15 + r * 35) * SS,
                                 x + (15 + c * 35 + 24) * SS, y + (15 + r * 35 + 24) * SS], fill=(18, 18, 18, 255))
    return draw_lockup(emblem, 'OKX', (18, 18, 18), style='sans_heavy', size=110, emblem_w=140, emblem_h=140)
BUILDERS['okx'] = build_okx

def build_bybit():
    W, H = 650 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(110 * SS, style='sans_heavy')
    d.text((50 * SS, 35 * SS), 'BYB', font=f, fill=(18, 18, 18, 255))
    x_it = 50 * SS + int(d.textlength('BYB', font=f))
    d.text((x_it, 35 * SS), 'IT', font=f, fill=(247, 166, 0, 255))
    return finalize_logo(im)
BUILDERS['bybit'] = build_bybit

def build_coinbase():
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        d.arc([cx - 30 * SS, cy - 30 * SS, cx + 30 * SS, cy + 30 * SS], start=45, end=315, fill=0, width=16 * SS)
    em = make_cutout_emblem(base, cutout, ew, eh, (0, 82, 255, 255))
    return draw_lockup(em, 'coinbase', (0, 82, 255), style='modern', size=96, emblem_w=140, emblem_h=140)
BUILDERS['coinbase'] = build_coinbase

def build_etoro():
    def emblem(d, x, y, w, h):
        col = (19, 194, 104, 255)
        cx, cy = x + w // 2, y + h // 2
        d.ellipse([cx - 30 * SS, cy - 10 * SS, cx + 30 * SS, cy + 35 * SS], fill=col)
        d.arc([cx - 40 * SS, cy - 40 * SS, cx - 10 * SS, cy], start=180, end=360, fill=col, width=10 * SS)
        d.arc([cx + 10 * SS, cy - 40 * SS, cx + 40 * SS, cy], start=180, end=360, fill=col, width=10 * SS)
    return draw_lockup(emblem, 'eToro', (19, 194, 104), style='modern', size=98, emblem_w=140, emblem_h=140)
BUILDERS['etoro'] = build_etoro

def build_kraken():
    return draw_wordmark('KRAKEN', (87, 65, 217), style='sans_heavy', size=105, tracking=6)
BUILDERS['kraken'] = build_kraken

def build_bitget():
    return draw_wordmark('Bitget', (0, 240, 255), style='modern', size=115, tracking=2)
BUILDERS['bitget'] = build_bitget

def build_kucoin():
    return draw_wordmark('KUCOIN', (36, 174, 143), style='modern', size=105, tracking=4)
BUILDERS['kucoin'] = build_kucoin

def build_tezos():
    return draw_wordmark('tezos', (44, 125, 247), style='modern', size=115)
BUILDERS['tezos'] = build_tezos

def build_polkadot():
    return draw_wordmark('Polkadot', (230, 0, 122), style='modern', size=105, tracking=2)
BUILDERS['polkadot'] = build_polkadot

# ------------------------------------------------------------------------------
# 8. ENERGY, INDUSTRY & CONGLOMERATES
# ------------------------------------------------------------------------------

def build_petronas():
    ew, eh = 140 * SS, 140 * SS
    def base(d):
        cx, cy = ew // 2, eh // 2
        d.polygon([(cx, 10 * SS), (ew - 15 * SS, cy + 15 * SS), (cx, eh - 10 * SS), (15 * SS, cy + 15 * SS)], fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        d.ellipse([cx - 20 * SS, cy - 5 * SS, cx + 20 * SS, cy + 35 * SS], fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (0, 161, 156, 255))
    return draw_lockup(em, 'PETRONAS', (0, 161, 156), style='sans_heavy', size=92, emblem_w=140, emblem_h=140)
BUILDERS['petronas'] = build_petronas

def build_shell():
    def emblem(d, x, y, w, h):
        d.polygon([(x + 20 * SS, y + h - 15 * SS), (x + w - 20 * SS, y + h - 15 * SS), (x + w, y + 35 * SS),
                   (x + w // 2, y + 10 * SS), (x, y + 35 * SS)], fill=(255, 209, 0, 255), outline=(221, 29, 33, 255), width=10 * SS)
    return draw_lockup(emblem, 'Shell', (221, 29, 33), style='sans_bold', size=100, emblem_w=140, emblem_h=140)
BUILDERS['shell'] = build_shell

def build_total_energies():
    def emblem(d, x, y, w, h):
        col = (237, 28, 36, 255)
        for i in range(3):
            d.arc([x + (10 + i * 15) * SS, y + (10 + i * 15) * SS, x + w - (10 + i * 15) * SS, y + h - (10 + i * 15) * SS],
                  start=i * 120, end=i * 120 + 200, fill=col, width=12 * SS)
    return draw_lockup(emblem, 'TotalEnergies', (237, 28, 36), style='modern', size=86, emblem_w=140, emblem_h=140)
BUILDERS['total_energies'] = build_total_energies

def build_aramco():
    def emblem(d, x, y, w, h):
        col = (0, 163, 224, 255)
        cx, cy = x + w // 2, y + h // 2
        for k in range(8):
            a = math.radians(k * 45)
            d.line([cx, cy, cx + 50 * SS * math.cos(a), cy + 50 * SS * math.sin(a)], fill=col, width=8 * SS)
    return draw_lockup(emblem, 'aramco', (0, 163, 224), style='modern', size=98, emblem_w=140, emblem_h=140)
BUILDERS['aramco'] = build_aramco

def build_red_bull():
    W, H = 850 * SS, 240 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([50 * SS, 45 * SS, 170 * SS, 165 * SS], fill=(255, 204, 0, 255))
    d.polygon([(60 * SS, 130 * SS), (120 * SS, 90 * SS), (180 * SS, 140 * SS)], fill=(204, 0, 0, 255))
    f = get_font(95 * SS, style='sans_heavy')
    d.text((210 * SS, 50 * SS), 'Red Bull', font=f, fill=(204, 0, 0, 255))
    return finalize_logo(im)
BUILDERS['red_bull'] = build_red_bull

def build_monster():
    def emblem(d, x, y, w, h):
        col = (118, 185, 0, 255)
        cx, cy = x + w // 2, y + h // 2
        d.line([cx - 30 * SS, y + 15 * SS, cx - 25 * SS, y + h - 15 * SS], fill=col, width=12 * SS)
        d.line([cx, y + 10 * SS, cx, y + h - 10 * SS], fill=col, width=14 * SS)
        d.line([cx + 30 * SS, y + 15 * SS, cx + 25 * SS, y + h - 15 * SS], fill=col, width=12 * SS)
    return draw_lockup(emblem, 'MONSTER', (118, 185, 0), subtitle='ENERGY', sub_col=(118, 185, 0),
                       style='sans_heavy', size=88, sub_size=32, emblem_w=140, emblem_h=140)
BUILDERS['monster'] = build_monster

def build_enel():
    return draw_wordmark('enel', (0, 159, 227), style='modern', size=115)
BUILDERS['enel'] = build_enel

def build_repsol():
    def emblem(d, x, y, w, h):
        d.pieslice([x, y, x + w, y + h], 180, 360, fill=(230, 0, 18, 255))
        d.pieslice([x + 15 * SS, y + 15 * SS, x + w - 15 * SS, y + h - 15 * SS], 180, 360, fill=(255, 130, 0, 255))
    return draw_lockup(emblem, 'REPSOL', (0, 43, 73), style='sans_heavy', size=96, emblem_w=140, emblem_h=140)
BUILDERS['repsol'] = build_repsol

def build_ineos():
    return draw_wordmark('INEOS', (0, 30, 98), style='modern', size=115, tracking=8)
BUILDERS['ineos'] = build_ineos

def build_siemens():
    return draw_wordmark('SIEMENS', (0, 100, 110), style='modern', size=110, tracking=6)
BUILDERS['siemens'] = build_siemens

def build_eni():
    # Six-legged fire-breathing dog silhouette + eni wordmark (no solid yellow block!)
    def emblem(d, x, y, w, h):
        cx, cy = x + w // 2, y + h // 2
        d.ellipse([cx - 30 * SS, cy - 20 * SS, cx + 30 * SS, cy + 20 * SS], fill=(18, 18, 18, 255))
        for dx in (-35, -20, -5, 10, 25, 40):
            d.line([cx + dx * SS, cy + 15 * SS, cx + dx * SS, cy + 50 * SS], fill=(18, 18, 18, 255), width=6 * SS)
    return draw_lockup(emblem, 'eni', (18, 18, 18), style='sans_heavy', size=105, emblem_w=140, emblem_h=140)
BUILDERS['eni'] = build_eni

def build_qatar_energy():
    return draw_wordmark('QatarEnergy', (0, 75, 135), style='modern', size=96, tracking=2)
BUILDERS['qatar_energy'] = build_qatar_energy

def build_bp():
    def emblem(d, x, y, w, h):
        cx, cy = x + w // 2, y + h // 2
        for k in range(12):
            a = math.radians(k * 30)
            col = (0, 135, 81, 255) if k % 2 == 0 else (255, 209, 0, 255)
            d.line([cx, cy, cx + 45 * SS * math.cos(a), cy + 45 * SS * math.sin(a)], fill=col, width=10 * SS)
    return draw_lockup(emblem, 'bp', (0, 135, 81), style='sans_heavy', size=110, emblem_w=140, emblem_h=140)
BUILDERS['bp'] = build_bp

# ------------------------------------------------------------------------------
# 9. INSURANCE & HEALTHCARE
# ------------------------------------------------------------------------------

def build_allianz():
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        for dx in (-25, 0, 25):
            d.line([cx + dx * SS, cy - 35 * SS, cx + dx * SS, cy + 35 * SS], fill=0, width=12 * SS)
    em = make_cutout_emblem(base, cutout, ew, eh, (0, 43, 73, 255))
    return draw_lockup(em, 'Allianz', (0, 43, 73), style='modern', size=96, emblem_w=140, emblem_h=140)
BUILDERS['allianz'] = build_allianz

def build_aia():
    ew, eh = 140 * SS, 140 * SS
    def base(d):
        cx = ew // 2
        d.polygon([(cx, 10 * SS), (ew - 10 * SS, eh - 10 * SS), (10 * SS, eh - 10 * SS)], fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        d.polygon([(cx, cy), (cx + 25 * SS, eh - 10 * SS), (cx - 25 * SS, eh - 10 * SS)], fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (211, 17, 69, 255))
    return draw_lockup(em, 'AIA', (211, 17, 69), style='sans_heavy', size=105, emblem_w=140, emblem_h=140)
BUILDERS['aia'] = build_aia

def build_axa():
    W, H = 650 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (0, 0, 143, 255)
    f = get_font(115 * SS, style='sans_heavy')
    d.text((50 * SS, 35 * SS), 'AXA', font=f, fill=col)
    d.line([280 * SS, 45 * SS, 340 * SS, 150 * SS], fill=(225, 26, 39, 255), width=14 * SS)
    return finalize_logo(im)
BUILDERS['axa'] = build_axa

def build_zurich():
    ew, eh = 140 * SS, 140 * SS
    def base(d): d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        f_z = get_font(95 * SS, style='sans_heavy')
        d.text((36 * SS, 12 * SS), 'Z', font=f_z, fill=0)
    em = make_cutout_emblem(base, cutout, ew, eh, (33, 103, 174, 255))
    return draw_lockup(em, 'ZURICH', (33, 103, 174), style='modern', size=96, emblem_w=140, emblem_h=140)
BUILDERS['zurich'] = build_zurich

def build_aviva():
    return draw_wordmark('AVIVA', (64, 152, 53), style='sans_heavy', size=115, tracking=6)
BUILDERS['aviva'] = build_aviva

def build_aig():
    # Rounded rectangular outline with AIG inside (Manchester United style, no solid blue block!)
    W, H = 650 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (0, 114, 206, 255)
    f = get_font(105 * SS, style='sans_heavy')
    tw = sum(d.textlength(c, font=f) for c in 'AIG')
    bx, by = 40 * SS, 35 * SS
    bw, bh = int(tw + 70 * SS), 140 * SS
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=25 * SS, outline=col, width=14 * SS)
    d.text((bx + 35 * SS, by + 12 * SS), 'AIG', font=f, fill=col)
    return finalize_logo(im)
BUILDERS['aig'] = build_aig

def build_generali():
    return draw_wordmark('GENERALI', (192, 0, 0), style='serif', size=96, tracking=6)
BUILDERS['generali'] = build_generali

def build_sanitas():
    def emblem(d, x, y, w, h):
        col = (0, 163, 224, 255)
        cx, cy = x + w // 2, y + h // 2
        d.rectangle([cx - 15 * SS, y + 15 * SS, cx + 15 * SS, y + h - 15 * SS], fill=col)
        d.rectangle([x + 15 * SS, cy - 15 * SS, x + w - 15 * SS, cy + 15 * SS], fill=col)
    return draw_lockup(emblem, 'Sanitas', (0, 43, 73), style='modern', size=96, emblem_w=140, emblem_h=140)
BUILDERS['sanitas'] = build_sanitas

# ------------------------------------------------------------------------------
# 10. BEVERAGES & LIFESTYLE
# ------------------------------------------------------------------------------

def build_carlsberg():
    W, H = 850 * SS, 240 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (0, 98, 59, 255)
    f = get_font(110 * SS, style='script')
    d.text((50 * SS, 35 * SS), 'Carlsberg', font=f, fill=col)
    d.arc([60 * SS, 150 * SS, 620 * SS, 195 * SS], start=10, end=170, fill=col, width=10 * SS)
    return finalize_logo(im)
BUILDERS['carlsberg'] = build_carlsberg

def build_heineken():
    def emblem(d, x, y, w, h):
        cx, cy = x + w // 2, y + h // 2
        pts = []
        for k in range(10):
            r = (w // 2 - 10 * SS) if k % 2 == 0 else (w // 4)
            a = math.radians(k * 36 - 90)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        d.polygon(pts, fill=(255, 0, 0, 255))
    return draw_lockup(emblem, 'Heineken', (0, 130, 0), style='sans_heavy', size=96, emblem_w=140, emblem_h=140)
BUILDERS['heineken'] = build_heineken

def build_estrella():
    return draw_wordmark('Estrella Galicia', (213, 43, 30), style='serif', size=88, tracking=3)
BUILDERS['estrella'] = build_estrella

def build_mahou():
    return draw_wordmark('Mahou', (163, 0, 21), style='script', size=115)
BUILDERS['mahou'] = build_mahou

def build_peroni():
    return draw_wordmark('PERONI', (0, 40, 85), style='serif', size=110, tracking=6)
BUILDERS['peroni'] = build_peroni

def build_budweiser():
    # Iconic cursive script Budweiser (no solid red block!)
    return draw_wordmark('Budweiser', (200, 16, 46), style='script', size=120)
BUILDERS['budweiser'] = build_budweiser

def build_pepsi():
    ew, eh = 140 * SS, 140 * SS
    def base(d):
        d.ellipse([0, 0, ew, eh], fill=255)
    def cutout(d):
        cx, cy = ew // 2, eh // 2
        d.polygon([(0, cy - 14 * SS), (cx, cy + 18 * SS), (ew, cy - 14 * SS),
                   (ew, cy + 14 * SS), (cx, cy + 46 * SS), (0, cy + 14 * SS)], fill=0)
    # Draw blue base and red top
    mask = Image.new('L', (ew, eh), 0)
    d_m = ImageDraw.Draw(mask)
    base(d_m)
    cutout(d_m)
    
    col_img = Image.new('RGBA', (ew, eh), (0, 75, 147, 255)) # Blue
    d_c = ImageDraw.Draw(col_img)
    d_c.pieslice([0, 0, ew, eh], 180, 360, fill=(227, 41, 52, 255)) # Red top
    col_img.putalpha(mask)
    
    return draw_lockup(col_img, 'pepsi', (0, 75, 147), style='sans_heavy', size=96, emblem_w=140, emblem_h=140)
BUILDERS['pepsi'] = build_pepsi

# ------------------------------------------------------------------------------
# 11. ICONIC EMBLEMS & ARTIST TAKEOVERS (BARCA SPOTIFY / CHELSEA 3 VIBE)
# ------------------------------------------------------------------------------

def build_spotify_icon():
    # Pure Spotify 3-wave sound circle (Barcelona El Clásico style)
    W, H = 260 * SS, 260 * SS
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy, r = W // 2, H // 2, 115 * SS
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    d.arc([cx - 85 * SS, cy - 70 * SS, cx + 85 * SS, cy + 50 * SS], start=210, end=330, fill=0, width=19 * SS)
    d.arc([cx - 70 * SS, cy - 45 * SS, cx + 70 * SS, cy + 60 * SS], start=210, end=330, fill=0, width=17 * SS)
    d.arc([cx - 55 * SS, cy - 20 * SS, cx + 55 * SS, cy + 70 * SS], start=210, end=330, fill=0, width=15 * SS)
    col_img = Image.new('RGBA', (W, H), (30, 215, 96, 255))
    col_img.putalpha(mask)
    return finalize_logo(col_img)
BUILDERS['spotify_icon'] = build_spotify_icon

def build_drake_owl():
    # Drake OVO Owl silhouette (Barcelona El Clásico takeover)
    W, H = 280 * SS, 280 * SS
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = W // 2, H // 2
    d.polygon([
        (cx, cy - 110 * SS), (cx + 35 * SS, cy - 110 * SS), (cx + 50 * SS, cy - 90 * SS),
        (cx + 70 * SS, cy - 30 * SS), (cx + 65 * SS, cy + 60 * SS),
        (cx + 35 * SS, cy + 110 * SS), (cx, cy + 115 * SS),
        (cx - 35 * SS, cy + 110 * SS), (cx - 65 * SS, cy + 60 * SS),
        (cx - 70 * SS, cy - 30 * SS), (cx - 50 * SS, cy - 90 * SS), (cx - 35 * SS, cy - 110 * SS)
    ], fill=255)
    d.ellipse([cx - 45 * SS, cy - 65 * SS, cx - 5 * SS, cy - 25 * SS], fill=0)
    d.ellipse([cx + 5 * SS, cy - 65 * SS, cx + 45 * SS, cy - 25 * SS], fill=0)
    d.ellipse([cx - 30 * SS, cy - 50 * SS, cx - 20 * SS, cy - 40 * SS], fill=255)
    d.ellipse([cx + 20 * SS, cy - 50 * SS, cx + 30 * SS, cy - 40 * SS], fill=255)
    d.polygon([(cx, cy - 35 * SS), (cx - 8 * SS, cy - 18 * SS), (cx + 8 * SS, cy - 18 * SS)], fill=0)
    d.arc([cx - 80 * SS, cy - 10 * SS, cx - 15 * SS, cy + 85 * SS], start=280, end=70, fill=0, width=7 * SS)
    d.arc([cx + 15 * SS, cy - 10 * SS, cx + 80 * SS, cy + 85 * SS], start=110, end=260, fill=0, width=7 * SS)
    for y in [cy + 10 * SS, cy + 40 * SS, cy + 70 * SS]:
        d.arc([cx - 30 * SS, y - 10 * SS, cx + 30 * SS, y + 15 * SS], start=20, end=160, fill=0, width=7 * SS)
    col_img = Image.new('RGBA', (W, H), (218, 165, 32, 255))
    col_img.putalpha(mask)
    return finalize_logo(col_img)
BUILDERS['drake_owl'] = build_drake_owl

def build_rolling_stones():
    # Rolling Stones Tongue & Lips (Barcelona El Clásico takeover)
    W, H = 260 * SS, 260 * SS
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = W // 2, H // 2
    d.ellipse([cx - 85 * SS, cy - 75 * SS, cx + 85 * SS, cy + 15 * SS], fill=255)
    d.ellipse([cx - 70 * SS, cy - 15 * SS, cx + 70 * SS, cy + 85 * SS], fill=255)
    d.pieslice([cx - 45 * SS, cy - 20 * SS, cx + 45 * SS, cy + 115 * SS], start=0, end=180, fill=255)
    d.ellipse([cx - 65 * SS, cy - 45 * SS, cx + 65 * SS, cy + 25 * SS], fill=0)
    d.line([(cx, cy + 10 * SS), (cx, cy + 90 * SS)], fill=0, width=6 * SS)
    d.polygon([(cx - 15 * SS, cy - 80 * SS), (cx + 15 * SS, cy - 80 * SS), (cx, cy - 55 * SS)], fill=0)
    col_img = Image.new('RGBA', (W, H), (227, 6, 19, 255))
    col_img.putalpha(mask)
    return finalize_logo(col_img)
BUILDERS['rolling_stones'] = build_rolling_stones

def build_rosalia_motomami():
    # Rosalia Motomami butterfly-M (Barcelona El Clásico takeover)
    W, H = 340 * SS, 240 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, H // 2
    col = (229, 27, 36, 255)
    d.polygon([(cx, cy - 20 * SS), (cx - 140 * SS, cy - 85 * SS), (cx - 85 * SS, cy + 80 * SS), (cx - 30 * SS, cy + 10 * SS)], fill=col)
    d.polygon([(cx, cy - 20 * SS), (cx + 140 * SS, cy - 85 * SS), (cx + 85 * SS, cy + 80 * SS), (cx + 30 * SS, cy + 10 * SS)], fill=col)
    d.polygon([(cx - 15 * SS, cy - 75 * SS), (cx + 15 * SS, cy - 75 * SS), (cx, cy + 95 * SS)], fill=col)
    return finalize_logo(im)
BUILDERS['rosalia_motomami'] = build_rosalia_motomami

def build_karol_g_heart():
    # Karol G Barbed-Wire Heart (Barcelona El Clásico takeover)
    W, H = 260 * SS, 260 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, H // 2
    col = (255, 51, 102, 255)
    d.ellipse([cx - 80 * SS, cy - 75 * SS, cx - 5 * SS, cy], outline=col, width=14 * SS)
    d.ellipse([cx + 5 * SS, cy - 75 * SS, cx + 80 * SS, cy], outline=col, width=14 * SS)
    d.line([(cx - 80 * SS, cy - 35 * SS), (cx, cy + 90 * SS)], fill=col, width=14 * SS)
    d.line([(cx + 80 * SS, cy - 35 * SS), (cx, cy + 90 * SS)], fill=col, width=14 * SS)
    spikes = [
        (cx - 65 * SS, cy - 50 * SS), (cx - 80 * SS, cy + 10 * SS), (cx - 40 * SS, cy + 55 * SS),
        (cx + 65 * SS, cy - 50 * SS), (cx + 80 * SS, cy + 10 * SS), (cx + 40 * SS, cy + 55 * SS)
    ]
    for sx, sy in spikes:
        d.line([(sx - 15 * SS, sy - 15 * SS), (sx + 15 * SS, sy + 15 * SS)], fill=col, width=8 * SS)
        d.line([(sx - 15 * SS, sy + 15 * SS), (sx + 15 * SS, sy - 15 * SS)], fill=col, width=8 * SS)
    return finalize_logo(im)
BUILDERS['karol_g_heart'] = build_karol_g_heart

def build_coldplay_moon():
    # Coldplay Moon Music celestial orbit (Barcelona El Clásico takeover)
    W, H = 260 * SS, 260 * SS
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = W // 2, H // 2
    d.ellipse([cx - 90 * SS, cy - 90 * SS, cx + 90 * SS, cy + 90 * SS], fill=255)
    d.ellipse([cx - 50 * SS, cy - 85 * SS, cx + 115 * SS, cy + 85 * SS], fill=0)
    d.ellipse([cx - 110 * SS, cy - 40 * SS, cx + 110 * SS, cy + 40 * SS], outline=255, width=8 * SS)
    col_img = Image.new('RGBA', (W, H), (157, 114, 255, 255))
    col_img.putalpha(mask)
    return finalize_logo(col_img)
BUILDERS['coldplay_moon'] = build_coldplay_moon

def build_playstation_shapes():
    # Sony PlayStation Iconic 4 Controller Shapes (△ ◯ ✕ □)
    W, H = 760 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cy = H // 2
    size, sw = 48 * SS, 12 * SS
    c1x = 120 * SS
    d.polygon([(c1x, cy - size), (c1x + size, cy + size - 8 * SS), (c1x - size, cy + size - 8 * SS)], outline=(0, 175, 155, 255), width=sw)
    c2x = 290 * SS
    d.ellipse([c2x - size + 4 * SS, cy - size + 4 * SS, c2x + size - 4 * SS, cy + size - 4 * SS], outline=(235, 60, 90, 255), width=sw)
    c3x = 460 * SS
    d.line([(c3x - size + 6 * SS, cy - size + 6 * SS), (c3x + size - 6 * SS, cy + size - 6 * SS)], fill=(90, 140, 250, 255), width=sw)
    d.line([(c3x - size + 6 * SS, cy + size - 6 * SS), (c3x + size - 6 * SS, cy - size + 6 * SS)], fill=(90, 140, 250, 255), width=sw)
    c4x = 630 * SS
    d.rectangle([c4x - size + 6 * SS, cy - size + 6 * SS, c4x + size - 6 * SS, cy + size - 6 * SS], outline=(230, 95, 170, 255), width=sw)
    return finalize_logo(im)
BUILDERS['playstation_shapes'] = build_playstation_shapes

def build_apple_logo():
    # Minimalist Apple emblem with leaf and bite
    W, H = 240 * SS, 260 * SS
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = W // 2, H // 2 + 10 * SS
    d.ellipse([cx - 75 * SS, cy - 65 * SS, cx + 5 * SS, cy + 65 * SS], fill=255)
    d.ellipse([cx - 5 * SS, cy - 65 * SS, cx + 75 * SS, cy + 65 * SS], fill=255)
    d.ellipse([cx - 55 * SS, cy + 20 * SS, cx + 55 * SS, cy + 85 * SS], fill=255)
    d.ellipse([cx + 25 * SS, cy - 35 * SS, cx + 105 * SS, cy + 45 * SS], fill=0)
    d.ellipse([cx - 20 * SS, cy + 70 * SS, cx + 20 * SS, cy + 95 * SS], fill=0)
    d.pieslice([cx - 10 * SS, cy - 110 * SS, cx + 50 * SS, cy - 50 * SS], start=180, end=270, fill=255)
    d.pieslice([cx - 30 * SS, cy - 90 * SS, cx + 30 * SS, cy - 30 * SS], start=0, end=90, fill=255)
    col_img = Image.new('RGBA', (W, H), (24, 24, 28, 255))
    col_img.putalpha(mask)
    return finalize_logo(col_img)
BUILDERS['apple_logo'] = build_apple_logo

def build_mastercard_circles():
    # Mastercard interlocking dual circles with vertical grill center
    W, H = 340 * SS, 240 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cy, r = H // 2, 75 * SS
    c1x, c2x = 115 * SS, 225 * SS
    d.ellipse([c1x - r, cy - r, c1x + r, cy + r], outline=(235, 0, 27, 255), width=16 * SS)
    d.ellipse([c2x - r, cy - r, c2x + r, cy + r], outline=(247, 158, 27, 255), width=16 * SS)
    for x in range(c1x + int(r * 0.4), c2x - int(r * 0.4) + 1, 16 * SS):
        d.line([(x, cy - 45 * SS), (x, cy + 45 * SS)], fill=(255, 95, 0, 255), width=8 * SS)
    return finalize_logo(im)
BUILDERS['mastercard_circles'] = build_mastercard_circles

def build_jumpman():
    # Air Jordan Flight silhouette (PSG kit aesthetic)
    W, H = 260 * SS, 260 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, H // 2
    col = (209, 38, 64, 255)
    d.ellipse([cx - 65 * SS, cy - 105 * SS, cx - 40 * SS, cy - 80 * SS], fill=col)
    d.ellipse([cx - 15 * SS, cy - 75 * SS, cx + 10 * SS, cy - 50 * SS], fill=col)
    d.line([(cx - 5 * SS, cy - 55 * SS), (cx - 50 * SS, cy - 85 * SS)], fill=col, width=11 * SS)
    d.line([(cx + 10 * SS, cy - 50 * SS), (cx + 65 * SS, cy - 35 * SS)], fill=col, width=10 * SS)
    d.polygon([(cx - 12 * SS, cy - 50 * SS), (cx + 12 * SS, cy - 50 * SS), (cx + 8 * SS, cy + 10 * SS), (cx - 8 * SS, cy + 10 * SS)], fill=col)
    d.line([(cx - 5 * SS, cy + 10 * SS), (cx - 85 * SS, cy + 70 * SS), (cx - 95 * SS, cy + 65 * SS)], fill=col, width=13 * SS)
    d.line([(cx + 5 * SS, cy + 10 * SS), (cx + 85 * SS, cy + 75 * SS), (cx + 95 * SS, cy + 85 * SS)], fill=col, width=13 * SS)
    return finalize_logo(im)
BUILDERS['jumpman'] = build_jumpman

def build_redbull_emblem():
    # Pure Red Bull twin charging bulls colliding with sun
    W, H = 360 * SS, 240 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, H // 2
    d.ellipse([cx - 65 * SS, cy - 65 * SS, cx + 65 * SS, cy + 65 * SS], fill=(245, 168, 0, 255))
    d.polygon([
        (cx - 140 * SS, cy + 25 * SS), (cx - 80 * SS, cy - 25 * SS), (cx - 15 * SS, cy + 5 * SS),
        (cx - 30 * SS, cy + 45 * SS), (cx - 95 * SS, cy + 50 * SS)
    ], fill=(219, 10, 64, 255))
    d.polygon([
        (cx + 140 * SS, cy + 25 * SS), (cx + 80 * SS, cy - 25 * SS), (cx + 15 * SS, cy + 5 * SS),
        (cx + 30 * SS, cy + 45 * SS), (cx + 95 * SS, cy + 50 * SS)
    ], fill=(219, 10, 64, 255))
    d.line([(cx - 45 * SS, cy - 10 * SS), (cx - 10 * SS, cy - 40 * SS)], fill=(245, 168, 0, 255), width=6 * SS)
    d.line([(cx + 45 * SS, cy - 10 * SS), (cx + 10 * SS, cy - 40 * SS)], fill=(245, 168, 0, 255), width=6 * SS)
    return finalize_logo(im)
BUILDERS['redbull_emblem'] = build_redbull_emblem

def build_autobot_crest():
    # Transformers Autobot crest (Inter Milan Paramount+ special)
    W, H = 260 * SS, 260 * SS
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = W // 2, H // 2
    d.polygon([
        (cx, cy - 105 * SS), (cx + 45 * SS, cy - 105 * SS), (cx + 45 * SS, cy - 75 * SS),
        (cx + 85 * SS, cy - 45 * SS), (cx + 85 * SS, cy + 30 * SS), (cx + 50 * SS, cy + 65 * SS),
        (cx + 25 * SS, cy + 105 * SS), (cx, cy + 105 * SS),
        (cx - 25 * SS, cy + 105 * SS), (cx - 50 * SS, cy + 65 * SS), (cx - 85 * SS, cy + 30 * SS),
        (cx - 85 * SS, cy - 45 * SS), (cx - 45 * SS, cy - 75 * SS), (cx - 45 * SS, cy - 105 * SS)
    ], fill=255)
    d.polygon([(cx - 45 * SS, cy - 15 * SS), (cx - 15 * SS, cy - 15 * SS), (cx - 30 * SS, cy + 5 * SS)], fill=0)
    d.polygon([(cx + 15 * SS, cy - 15 * SS), (cx + 45 * SS, cy - 15 * SS), (cx + 30 * SS, cy + 5 * SS)], fill=0)
    d.rectangle([cx - 8 * SS, cy - 65 * SS, cx + 8 * SS, cy + 20 * SS], fill=0)
    d.rectangle([cx - 35 * SS, cy + 40 * SS, cx - 12 * SS, cy + 70 * SS], fill=0)
    d.rectangle([cx + 12 * SS, cy + 40 * SS, cx + 35 * SS, cy + 70 * SS], fill=0)
    col_img = Image.new('RGBA', (W, H), (215, 25, 32, 255))
    col_img.putalpha(mask)
    return finalize_logo(col_img)
BUILDERS['autobot_crest'] = build_autobot_crest

def build_paramount_peak():
    # Paramount mountain peak ringed with stars (Inter Milan special)
    W, H = 280 * SS, 260 * SS
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = W // 2, H // 2 + 10 * SS
    d.polygon([(cx, cy - 75 * SS), (cx + 80 * SS, cy + 65 * SS), (cx - 80 * SS, cy + 65 * SS)], fill=255)
    d.polygon([(cx, cy - 75 * SS), (cx + 30 * SS, cy - 25 * SS), (cx + 10 * SS, cy - 35 * SS), (cx - 10 * SS, cy - 25 * SS), (cx - 30 * SS, cy - 25 * SS)], fill=0)
    for i in range(11):
        angle = math.radians(200 + i * 14)
        sx = cx + int(105 * SS * math.cos(angle))
        sy = cy + int(105 * SS * math.sin(angle))
        d.ellipse([sx - 7 * SS, sy - 7 * SS, sx + 7 * SS, sy + 7 * SS], fill=255)
    col_img = Image.new('RGBA', (W, H), (0, 100, 255, 255))
    col_img.putalpha(mask)
    return finalize_logo(col_img)
BUILDERS['paramount_peak'] = build_paramount_peak

def build_target_bullseye():
    # Target concentric bullseye rings (Minnesota United / streetwear)
    W, H = 260 * SS, 260 * SS
    cx, cy, r = W // 2, H // 2, 110 * SS
    col = (204, 0, 0, 255)
    mask = Image.new('L', (W, H), 0)
    dm = ImageDraw.Draw(mask)
    dm.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    dm.ellipse([cx - int(r * 0.65), cy - int(r * 0.65), cx + int(r * 0.65), cy + int(r * 0.65)], fill=0)
    dm.ellipse([cx - int(r * 0.35), cy - int(r * 0.35), cx + int(r * 0.35), cy + int(r * 0.35)], fill=255)
    col_img = Image.new('RGBA', (W, H), col)
    col_img.putalpha(mask)
    return finalize_logo(col_img)
BUILDERS['target_bullseye'] = build_target_bullseye

def build_one_and_one():
    # Dortmund 1&1 square logo outline with bold typography
    W, H = 260 * SS, 260 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy, s = W // 2, H // 2, 95 * SS
    col = (0, 32, 91, 255)
    d.rounded_rectangle([cx - s, cy - s, cx + s, cy + s], radius=24 * SS, outline=col, width=14 * SS)
    f = get_font(72 * SS, style='sans_heavy')
    tw = d.textlength('1&1', font=f)
    d.text((cx - int(tw // 2), cy - 42 * SS), '1&1', font=f, fill=col)
    return finalize_logo(im)
BUILDERS['one_and_one'] = build_one_and_one

def build_o2_bubbles():
    # Arsenal historic O2 with rising bubbles
    W, H = 320 * SS, 220 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (0, 85, 165, 255)
    f = get_font(120 * SS, style='modern')
    d.text((45 * SS, 35 * SS), 'O', font=f, fill=col)
    f2 = get_font(70 * SS, style='modern')
    d.text((165 * SS, 95 * SS), '2', font=f2, fill=col)
    d.ellipse([215 * SS, 45 * SS, 275 * SS, 105 * SS], outline=col, width=9 * SS)
    d.ellipse([255 * SS, 25 * SS, 285 * SS, 55 * SS], outline=col, width=6 * SS)
    return finalize_logo(im)
BUILDERS['o2_bubbles'] = build_o2_bubbles

def build_mercedes_star():
    # Mercedes-Benz 3-pointed star in precision ring
    W, H = 260 * SS, 260 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy, r = W // 2, H // 2, 105 * SS
    col = (0, 163, 224, 255)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=11 * SS)
    for deg in [270, 30, 150]:
        rad = math.radians(deg)
        tx = cx + int(r * 0.95 * math.cos(rad))
        ty = cy + int(r * 0.95 * math.sin(rad))
        l_rad = math.radians(deg + 120)
        lx = cx + int(14 * SS * math.cos(l_rad))
        ly = cy + int(14 * SS * math.sin(l_rad))
        d.polygon([(cx, cy), (lx, ly), (tx, ty)], fill=col)
    return finalize_logo(im)
BUILDERS['mercedes_star'] = build_mercedes_star

def build_audi_rings():
    # Audi 4 horizontally interlocking precision rings
    W, H = 540 * SS, 200 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cy, r = H // 2, 58 * SS
    col = (187, 10, 48, 255)
    sw = 10 * SS
    xs = [110 * SS, 195 * SS, 280 * SS, 365 * SS]
    for x in xs:
        d.ellipse([x - r, cy - r, x + r, cy + r], outline=col, width=sw)
    return finalize_logo(im)
BUILDERS['audi_rings'] = build_audi_rings

def build_mitsubishi_diamonds():
    # Mitsubishi 3 red rhombuses
    W, H = 280 * SS, 260 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, H // 2 - 10 * SS
    col = (230, 0, 18, 255)
    s = 48 * SS
    d.polygon([(cx, cy), (cx - s, cy - int(s * 1.73)), (cx, cy - int(s * 3.46)), (cx + s, cy - int(s * 1.73))], fill=col)
    d.polygon([(cx, cy), (cx - int(s * 2), cy), (cx - int(s * 3), cy + int(s * 1.73)), (cx - s, cy + int(s * 1.73))], fill=col)
    d.polygon([(cx, cy), (cx + s, cy + int(s * 1.73)), (cx + int(s * 3), cy + int(s * 1.73)), (cx + int(s * 2), cy)], fill=col)
    return finalize_logo(im)
BUILDERS['mitsubishi_diamonds'] = build_mitsubishi_diamonds

def build_tesla_crest():
    # Tesla T-sword futuristic shield
    W, H = 260 * SS, 260 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, H // 2
    col = (232, 33, 39, 255)
    d.chord([cx - 95 * SS, cy - 105 * SS, cx + 95 * SS, cy - 25 * SS], start=210, end=330, fill=col)
    d.polygon([
        (cx - 75 * SS, cy - 50 * SS), (cx + 75 * SS, cy - 50 * SS),
        (cx + 65 * SS, cy - 35 * SS), (cx + 18 * SS, cy - 30 * SS),
        (cx + 12 * SS, cy + 95 * SS), (cx, cy + 105 * SS), (cx - 12 * SS, cy + 95 * SS),
        (cx - 18 * SS, cy - 30 * SS), (cx - 65 * SS, cy - 35 * SS)
    ], fill=col)
    return finalize_logo(im)
BUILDERS['tesla_crest'] = build_tesla_crest

def build_ethereum_prism():
    # Ethereum 3D crystal diamond octahedron
    W, H = 220 * SS, 280 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, H // 2
    col_light = (140, 160, 245, 255)
    col_dark = (75, 95, 205, 255)
    d.polygon([(cx, cy - 110 * SS), (cx - 65 * SS, cy - 10 * SS), (cx, cy + 25 * SS)], fill=col_light)
    d.polygon([(cx, cy - 110 * SS), (cx + 65 * SS, cy - 10 * SS), (cx, cy + 25 * SS)], fill=col_dark)
    d.polygon([(cx, cy + 45 * SS), (cx - 65 * SS, cy + 10 * SS), (cx, cy + 115 * SS)], fill=col_light)
    d.polygon([(cx, cy + 45 * SS), (cx + 65 * SS, cy + 10 * SS), (cx, cy + 115 * SS)], fill=col_dark)
    return finalize_logo(im)
BUILDERS['ethereum_prism'] = build_ethereum_prism

def build_bitcoin_symbol():
    # Bitcoin coin ring with double-stroke ₿ cutout
    W, H = 260 * SS, 260 * SS
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy, r = W // 2, H // 2, 105 * SS
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    f = get_font(125 * SS, style='sans_heavy')
    tw = d.textlength('B', font=f)
    d.text((cx - int(tw // 2) - 5 * SS, cy - 72 * SS), 'B', font=f, fill=0)
    d.rectangle([cx - 15 * SS, cy - 85 * SS, cx - 5 * SS, cy + 85 * SS], fill=0)
    d.rectangle([cx + 10 * SS, cy - 85 * SS, cx + 20 * SS, cy + 85 * SS], fill=0)
    col_img = Image.new('RGBA', (W, H), (247, 147, 26, 255))
    col_img.putalpha(mask)
    return finalize_logo(col_img)
BUILDERS['bitcoin_symbol'] = build_bitcoin_symbol

def build_xbox_sphere():
    # Xbox 3D sculpted X sphere
    W, H = 260 * SS, 260 * SS
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy, r = W // 2, H // 2, 110 * SS
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    d.polygon([(cx - 75 * SS, cy - 90 * SS), (cx, cy + 10 * SS), (cx - 95 * SS, cy + 55 * SS)], fill=0)
    d.polygon([(cx + 75 * SS, cy - 90 * SS), (cx, cy + 10 * SS), (cx + 95 * SS, cy + 55 * SS)], fill=0)
    d.polygon([(cx, cy - 85 * SS), (cx - 20 * SS, cy - 95 * SS), (cx + 20 * SS, cy - 95 * SS)], fill=0)
    col_img = Image.new('RGBA', (W, H), (16, 124, 16, 255))
    col_img.putalpha(mask)
    return finalize_logo(col_img)
BUILDERS['xbox_sphere'] = build_xbox_sphere

def build_unicef_emblem():
    # UNICEF mother and child silhouette with laurel branches
    W, H = 280 * SS, 260 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, H // 2
    col = (0, 174, 239, 255)
    d.ellipse([cx - 65 * SS, cy - 65 * SS, cx + 65 * SS, cy + 65 * SS], outline=col, width=8 * SS)
    d.ellipse([cx - 28 * SS, cy - 65 * SS, cx + 28 * SS, cy + 65 * SS], outline=col, width=6 * SS)
    d.line([(cx - 65 * SS, cy), (cx + 65 * SS, cy)], fill=col, width=6 * SS)
    d.ellipse([cx - 15 * SS, cy - 40 * SS, cx + 5 * SS, cy - 20 * SS], fill=col)
    d.ellipse([cx + 10 * SS, cy - 25 * SS, cx + 25 * SS, cy - 10 * SS], fill=col)
    d.polygon([(cx - 22 * SS, cy - 15 * SS), (cx + 12 * SS, cy - 15 * SS), (cx - 5 * SS, cy + 30 * SS)], fill=col)
    d.arc([cx - 95 * SS, cy - 65 * SS, cx - 45 * SS, cy + 85 * SS], start=45, end=270, fill=col, width=9 * SS)
    d.arc([cx + 45 * SS, cy - 65 * SS, cx + 95 * SS, cy + 85 * SS], start=-90, end=135, fill=col, width=9 * SS)
    return finalize_logo(im)
BUILDERS['unicef_emblem'] = build_unicef_emblem

def build_volkswagen_roundel():
    # Volkswagen circular badge with stacked V and W
    W, H = 260 * SS, 260 * SS
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy, r = W // 2, H // 2, 105 * SS
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    d.ellipse([cx - r + 14 * SS, cy - r + 14 * SS, cx + r - 14 * SS, cy + r - 14 * SS], fill=0)
    d.polygon([(cx - 55 * SS, cy - 70 * SS), (cx - 30 * SS, cy - 70 * SS), (cx, cy - 5 * SS), (cx + 30 * SS, cy - 70 * SS), (cx + 55 * SS, cy - 70 * SS), (cx, cy + 35 * SS)], fill=255)
    d.polygon([(cx - 65 * SS, cy - 10 * SS), (cx - 45 * SS, cy - 10 * SS), (cx - 20 * SS, cy + 65 * SS), (cx, cy + 20 * SS), (cx + 20 * SS, cy + 65 * SS), (cx + 45 * SS, cy - 10 * SS), (cx + 65 * SS, cy - 10 * SS), (cx + 25 * SS, cy + 85 * SS), (cx - 25 * SS, cy + 85 * SS)], fill=255)
    col_img = Image.new('RGBA', (W, H), (0, 30, 80, 255))
    col_img.putalpha(mask)
    return finalize_logo(col_img)
BUILDERS['volkswagen_roundel'] = build_volkswagen_roundel

def build_shell_pecten():
    # Shell scallop pecten with radiating fluted ridges
    W, H = 260 * SS, 260 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, H // 2 + 5 * SS
    col_yel = (251, 206, 7, 255)
    col_red = (218, 41, 28, 255)
    d.pieslice([cx - 95 * SS, cy - 95 * SS, cx + 95 * SS, cy + 95 * SS], start=190, end=350, fill=col_yel, outline=col_red, width=9 * SS)
    d.polygon([(cx - 45 * SS, cy + 35 * SS), (cx + 45 * SS, cy + 35 * SS), (cx + 65 * SS, cy + 85 * SS), (cx - 65 * SS, cy + 85 * SS)], fill=col_red)
    for deg in [215, 240, 270, 300, 325]:
        rad = math.radians(deg)
        tx = cx + int(90 * SS * math.cos(rad))
        ty = cy + int(90 * SS * math.sin(rad))
        d.line([(cx, cy + 35 * SS), (tx, ty)], fill=col_red, width=7 * SS)
    return finalize_logo(im)
BUILDERS['shell_pecten'] = build_shell_pecten

def build_bayer_cross():
    # Bayer cross emblem inside circle
    W, H = 260 * SS, 260 * SS
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy, r = W // 2, H // 2, 105 * SS
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    d.rectangle([cx - r + 15 * SS, cy - 22 * SS, cx + r - 15 * SS, cy + 22 * SS], fill=0)
    d.rectangle([cx - 22 * SS, cy - r + 15 * SS, cx + 22 * SS, cy + r - 15 * SS], fill=0)
    col_img = Image.new('RGBA', (W, H), (0, 145, 223, 255))
    col_img.putalpha(mask)
    return finalize_logo(col_img)
BUILDERS['bayer_cross'] = build_bayer_cross

def build_snapdragon_icon():
    # Snapdragon pure cyber dragon ball fireball icon
    W, H = 260 * SS, 260 * SS
    cx, cy, r = W // 2, H // 2, 105 * SS
    col = (224, 26, 34, 255)
    mask = Image.new('L', (W, H), 0)
    dm = ImageDraw.Draw(mask)
    dm.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    dm.arc([cx - 75 * SS, cy - 75 * SS, cx + 75 * SS, cy + 75 * SS], start=180, end=270, fill=0, width=15 * SS)
    dm.arc([cx - 45 * SS, cy - 75 * SS, cx + 105 * SS, cy + 75 * SS], start=270, end=360, fill=0, width=15 * SS)
    dm.ellipse([cx - 35 * SS, cy - 10 * SS, cx - 15 * SS, cy + 10 * SS], fill=0)
    dm.ellipse([cx + 15 * SS, cy - 10 * SS, cx + 35 * SS, cy + 10 * SS], fill=0)
    col_img = Image.new('RGBA', (W, H), col)
    col_img.putalpha(mask)
    return finalize_logo(col_img)
BUILDERS['snapdragon_icon'] = build_snapdragon_icon

def build_atari_fuji():
    # Atari Fuji retro tri-line crest
    W, H = 260 * SS, 260 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, H // 2
    col = (228, 27, 19, 255)
    d.rectangle([cx - 10 * SS, cy - 95 * SS, cx + 10 * SS, cy + 95 * SS], fill=col)
    d.arc([cx - 95 * SS, cy - 95 * SS, cx + 25 * SS, cy + 95 * SS], start=90, end=270, fill=col, width=22 * SS)
    d.arc([cx - 25 * SS, cy - 95 * SS, cx + 95 * SS, cy + 95 * SS], start=-90, end=90, fill=col, width=22 * SS)
    return finalize_logo(im)
BUILDERS['atari_fuji'] = build_atari_fuji

def build_nasa_worm():
    # NASA supersonic vector planet orbit
    W, H = 320 * SS, 240 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, H // 2
    d.ellipse([cx - 85 * SS, cy - 85 * SS, cx + 85 * SS, cy + 85 * SS], fill=(11, 61, 145, 255))
    d.polygon([(cx - 110 * SS, cy + 30 * SS), (cx + 35 * SS, cy - 65 * SS), (cx + 105 * SS, cy - 75 * SS), (cx - 15 * SS, cy + 10 * SS)], fill=(252, 61, 33, 255))
    d.ellipse([cx - 120 * SS, cy - 35 * SS, cx + 120 * SS, cy + 35 * SS], outline=(255, 255, 255, 255), width=7 * SS)
    return finalize_logo(im)
BUILDERS['nasa_worm'] = build_nasa_worm


# ==============================================================================
# MAIN ENTRYPOINT & GENERATOR
# ==============================================================================

def generate_all_sponsors(dest_dir):
    """Generate all sponsors into dest_dir, producing both colour and _white.png files."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    generated = []
    
    print(f"Generating {len(BUILDERS)} premier sponsors into {dest}...")
    for brand, builder in sorted(BUILDERS.items()):
        try:
            col_img = builder()
            white_img = make_white_silhouette(col_img)
            
            p_col = dest / f"{brand}.png"
            p_white = dest / f"{brand}_white.png"
            
            col_img.save(p_col)
            white_img.save(p_white)
            generated.append(brand)
        except Exception as e:
            print(f"Error generating {brand}: {e}")
            raise
            
    print(f"Successfully generated {len(generated)} sponsor logos (colour + white pairs).")
    return generated

if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent
    logo_dir = root / 'content' / 'KitGenerator' / 'logos'
    generate_all_sponsors(logo_dir)
