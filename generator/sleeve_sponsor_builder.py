"""sleeve_sponsor_builder.py - High-resolution, vector-inspired modern sleeve sponsor logos.

Generates premier football sleeve sponsor marks (Visit Rwanda, HP, DXC, OKX, Expedia, Kraken, etc.)
as transparent PNG pairs (color + monochrome white) supersampled at SS=4.
"""

from pathlib import Path
import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SS = 4

def get_font(size, style='sans_heavy'):
    candidates = {
        'sans_heavy': [
            '/System/Library/Fonts/Supplemental/Arial Black.ttf',
            '/System/Library/Fonts/Supplemental/Impact.ttf',
            '/System/Library/Fonts/Supplemental/Helvetica.ttc',
            r'C:\Windows\Fonts\ariblk.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
        ],
        'sans_bold': [
            '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
            '/System/Library/Fonts/Supplemental/Helvetica.ttc',
            r'C:\Windows\Fonts\arialbd.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
        ],
        'modern': [
            '/System/Library/Fonts/Supplemental/Futura.ttc',
            '/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf',
            r'C:\Windows\Fonts\bahnschrift.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
        ],
        'tech': [
            '/System/Library/Fonts/Supplemental/Trebuchet MS Bold.ttf',
            '/System/Library/Fonts/Supplemental/Verdana Bold.ttf',
            r'C:\Windows\Fonts\trebucbd.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
        ],
        'serif': [
            '/System/Library/Fonts/Supplemental/Georgia Bold.ttf',
            '/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf',
            r'C:\Windows\Fonts\georgiab.ttf'
        ],
        'script': [
            '/System/Library/Fonts/Supplemental/Brush Script.ttf',
            r'C:\Windows\Fonts\BRUSHSCI.TTF'
        ]
    }
    for p in candidates.get(style, candidates['sans_heavy']):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def finalize_logo(im, padding=12):
    """Downsample SS=4 with Lanczos, crop tightly, add subtle padding."""
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
    """Crisp white monochrome silhouette preserving exact alpha transparency."""
    arr = np.array(img).copy()
    arr[:, :, :3] = 255
    return Image.fromarray(arr)

SLEEVE_BUILDERS = {}

# 1. Visit Rwanda (Arsenal, PSG iconic sleeve sponsor)
def build_visit_rwanda():
    W, H = 540 * SS, 200 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (18, 18, 22, 255)
    f_visit = get_font(52 * SS, style='modern')
    f_rwanda = get_font(78 * SS, style='sans_heavy')
    
    # "VISIT" tracked
    x_v = 40 * SS
    for ch in 'VISIT':
        d.text((x_v, 20 * SS), ch, font=f_visit, fill=col)
        x_v += int(d.textlength(ch, font=f_visit) + 18 * SS)
        
    # Dividing clean rule line
    d.rectangle([40 * SS, 82 * SS, x_v - 18 * SS, 86 * SS], fill=col)
    
    # "RWANDA" bold tracked
    x_r = 40 * SS
    for ch in 'RWANDA':
        d.text((x_r, 96 * SS), ch, font=f_rwanda, fill=col)
        x_r += int(d.textlength(ch, font=f_rwanda) + 8 * SS)
        
    return finalize_logo(im)
SLEEVE_BUILDERS['visit_rwanda'] = build_visit_rwanda

# 2. HP (Real Madrid iconic sleeve sponsor)
def build_hp():
    W, H = 240 * SS, 240 * SS
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy, r = W // 2, H // 2, 105 * SS
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    
    # Italicized modern 'hp' cutouts extending through the circle boundary
    # 'h' stem and arch cutouts
    d.polygon([(cx - 75 * SS, cy - 90 * SS), (cx - 45 * SS, cy - 90 * SS), (cx - 65 * SS, cy + 90 * SS), (cx - 95 * SS, cy + 90 * SS)], fill=0)
    d.polygon([(cx - 45 * SS, cy - 10 * SS), (cx - 15 * SS, cy - 10 * SS), (cx - 30 * SS, cy + 90 * SS), (cx - 60 * SS, cy + 90 * SS)], fill=0)
    # 'p' stem and bowl cutouts
    d.polygon([(cx - 10 * SS, cy - 10 * SS), (cx + 20 * SS, cy - 10 * SS), (cx - 5 * SS, cy + 90 * SS), (cx - 35 * SS, cy + 90 * SS)], fill=0)
    d.polygon([(cx + 20 * SS, cy - 10 * SS), (cx + 60 * SS, cy - 10 * SS), (cx + 45 * SS, cy + 50 * SS), (cx + 5 * SS, cy + 50 * SS)], fill=0)
    
    col_img = Image.new('RGBA', (W, H), (0, 150, 214, 255)) # HP Blue
    col_img.putalpha(mask)
    return finalize_logo(col_img)
SLEEVE_BUILDERS['hp'] = build_hp

# 3. DXC Technology (Manchester United sleeve sponsor)
def build_dxc():
    W, H = 540 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (18, 18, 22, 255)
    f_dxc = get_font(95 * SS, style='sans_heavy')
    f_tech = get_font(38 * SS, style='modern')
    
    # "DXC" bold
    d.text((30 * SS, 20 * SS), 'DXC', font=f_dxc, fill=col)
    tw = d.textlength('DXC', font=f_dxc)
    
    # Dot accent
    d.ellipse([30 * SS + tw + 6 * SS, 90 * SS, 30 * SS + tw + 18 * SS, 102 * SS], fill=(95, 37, 159, 255)) # DXC Purple
    
    # "technology"
    d.text((30 * SS + tw + 28 * SS, 68 * SS), 'technology', font=f_tech, fill=col)
    return finalize_logo(im)
SLEEVE_BUILDERS['dxc'] = build_dxc

# 4. OKX (Manchester City sleeve sponsor)
def build_okx():
    W, H = 460 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (18, 18, 22, 255)
    f = get_font(105 * SS, style='sans_heavy')
    
    # "OKX" with bold geometric tech matrix
    d.text((35 * SS, 25 * SS), 'OKX', font=f, fill=col)
    
    # 4 micro square matrix accents
    bx = 35 * SS + int(d.textlength('OKX', font=f)) + 18 * SS
    for r in range(2):
        for c in range(2):
            d.rectangle([bx + c * 16 * SS, 45 * SS + r * 16 * SS, bx + c * 16 * SS + 10 * SS, 45 * SS + r * 16 * SS + 10 * SS], fill=col)
    return finalize_logo(im)
SLEEVE_BUILDERS['okx'] = build_okx

# 5. Expedia (Liverpool sleeve sponsor)
def build_expedia():
    W, H = 500 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col_navy = (0, 53, 94, 255)
    col_yel = (255, 209, 0, 255)
    
    # Yellow flight airplane arc
    cx = 55 * SS
    d.arc([cx - 35 * SS, 35 * SS, cx + 35 * SS, 105 * SS], start=180, end=360, fill=col_yel, width=12 * SS)
    d.polygon([(cx + 25 * SS, 60 * SS), (cx + 45 * SS, 70 * SS), (cx + 25 * SS, 80 * SS)], fill=col_yel)
    
    # "Expedia" wordmark
    f = get_font(88 * SS, style='modern')
    d.text((120 * SS, 32 * SS), 'Expedia', font=f, fill=col_navy)
    return finalize_logo(im)
SLEEVE_BUILDERS['expedia'] = build_expedia

# 6. Kraken (Tottenham, Atletico Madrid sleeve sponsor)
def build_kraken():
    W, H = 480 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col_purp = (87, 65, 217, 255)
    
    # Stylized geometric tentacle K crest
    kx = 65 * SS
    d.rectangle([kx - 30 * SS, 35 * SS, kx - 12 * SS, 135 * SS], fill=col_purp)
    d.polygon([(kx - 12 * SS, 85 * SS), (kx + 25 * SS, 35 * SS), (kx + 45 * SS, 35 * SS), (kx + 5 * SS, 85 * SS)], fill=col_purp)
    d.polygon([(kx - 2 * SS, 85 * SS), (kx + 45 * SS, 135 * SS), (kx + 25 * SS, 135 * SS), (kx - 12 * SS, 95 * SS)], fill=col_purp)
    
    # "kraken"
    f = get_font(84 * SS, style='modern')
    d.text((145 * SS, 35 * SS), 'kraken', font=f, fill=col_purp)
    return finalize_logo(im)
SLEEVE_BUILDERS['kraken'] = build_kraken

# 7. Ambilight TV (Barcelona sleeve sponsor)
def build_ambilight():
    W, H = 520 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (0, 180, 220, 255) # Cyan
    f_amb = get_font(72 * SS, style='sans_heavy')
    f_tv = get_font(42 * SS, style='modern')
    
    d.text((35 * SS, 38 * SS), 'AMBILIGHT', font=f_amb, fill=col)
    tw = d.textlength('AMBILIGHT', font=f_amb)
    d.text((35 * SS + tw + 14 * SS, 62 * SS), 'tv', font=f_tv, fill=(230, 40, 120, 255))
    return finalize_logo(im)
SLEEVE_BUILDERS['ambilight'] = build_ambilight

# 8. MSC Cruises (AC Milan sleeve sponsor)
def build_msc_cruises():
    W, H = 500 * SS, 190 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (0, 36, 100, 255) # MSC Navy
    
    # Windrose compass star
    cx, cy = 65 * SS, 85 * SS
    r = 40 * SS
    d.polygon([(cx, cy - r), (cx + 8 * SS, cy - 8 * SS), (cx + r, cy), (cx + 8 * SS, cy + 8 * SS),
               (cx, cy + r), (cx - 8 * SS, cy + 8 * SS), (cx - r, cy), (cx - 8 * SS, cy - 8 * SS)], fill=col)
    
    f_msc = get_font(78 * SS, style='sans_heavy')
    f_cruises = get_font(32 * SS, style='modern')
    d.text((130 * SS, 25 * SS), 'MSC', font=f_msc, fill=col)
    d.text((130 * SS, 98 * SS), 'CRUISES', font=f_cruises, fill=col)
    return finalize_logo(im)
SLEEVE_BUILDERS['msc_cruises'] = build_msc_cruises

# 9. eBay (Inter Milan sleeve sponsor)
def build_ebay():
    W, H = 400 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = get_font(105 * SS, style='sans_heavy')
    
    # 4 signature eBay colors
    colors = [(229, 50, 56, 255), (0, 100, 210, 255), (245, 175, 0, 255), (134, 184, 23, 255)]
    x = 40 * SS
    for ch, col in zip('ebay', colors):
        d.text((x, 25 * SS), ch, font=f, fill=col)
        x += int(d.textlength(ch, font=f) - 6 * SS)
    return finalize_logo(im)
SLEEVE_BUILDERS['ebay'] = build_ebay

# 10. BingX (Chelsea sleeve sponsor)
def build_bingx():
    W, H = 460 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (0, 102, 255, 255) # Electric Blue
    
    # Isometric tech ribbon cube
    cx, cy = 60 * SS, 85 * SS
    s = 32 * SS
    d.polygon([(cx, cy - s), (cx + s, cy - s // 2), (cx, cy), (cx - s, cy - s // 2)], fill=col)
    d.polygon([(cx, cy), (cx + s, cy - s // 2), (cx + s, cy + s // 2), (cx, cy + s)], fill=(0, 75, 200, 255))
    d.polygon([(cx, cy), (cx - s, cy - s // 2), (cx - s, cy + s // 2), (cx, cy + s)], fill=(0, 50, 150, 255))
    
    f = get_font(88 * SS, style='modern')
    d.text((120 * SS, 35 * SS), 'BingX', font=f, fill=(18, 18, 24, 255))
    return finalize_logo(im)
SLEEVE_BUILDERS['bingx'] = build_bingx

# 11. GOAT (Paris Saint-Germain sleeve sponsor)
def build_goat():
    W, H = 400 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (18, 18, 22, 255)
    f = get_font(105 * SS, style='sans_heavy')
    
    # Ultra-heavy tracked uppercase "GOAT"
    x = 40 * SS
    for ch in 'GOAT':
        d.text((x, 25 * SS), ch, font=f, fill=col)
        x += int(d.textlength(ch, font=f) + 12 * SS)
    return finalize_logo(im)
SLEEVE_BUILDERS['goat'] = build_goat

# 12. noon (Newcastle United sleeve sponsor)
def build_noon():
    W, H = 240 * SS, 240 * SS
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy, r = W // 2, H // 2, 105 * SS
    
    # Outer circle
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    # Negative space transparent cutout for "noon" text (stays crisp on light and dark kits!)
    f = get_font(84 * SS, style='sans_heavy')
    tw = d.textlength('noon', font=f)
    d.text((cx - int(tw // 2), cy - 55 * SS), 'noon', font=f, fill=0)
    
    col_img = Image.new('RGBA', (W, H), (254, 225, 0, 255)) # Signature Noon Yellow
    col_img.putalpha(mask)
    return finalize_logo(col_img)
SLEEVE_BUILDERS['noon'] = build_noon

# 13. GLS (Borussia Dortmund sleeve sponsor)
def build_gls():
    W, H = 380 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col_navy = (0, 42, 116, 255)
    col_yel = (255, 204, 0, 255)
    
    f = get_font(98 * SS, style='sans_heavy')
    d.text((35 * SS, 25 * SS), 'GLS', font=f, fill=col_navy)
    
    # Fast logistics arrow chevron accent
    tw = d.textlength('GLS', font=f)
    ax = 35 * SS + int(tw) + 12 * SS
    d.polygon([(ax, 40 * SS), (ax + 24 * SS, 75 * SS), (ax, 110 * SS), (ax + 14 * SS, 110 * SS), (ax + 38 * SS, 75 * SS), (ax + 14 * SS, 40 * SS)], fill=col_yel)
    return finalize_logo(im)
SLEEVE_BUILDERS['gls'] = build_gls

# 14. Cygames (Juventus sleeve sponsor)
def build_cygames():
    W, H = 460 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col_gold = (212, 175, 55, 255)
    
    f = get_font(82 * SS, style='modern')
    d.text((40 * SS, 35 * SS), 'Cygames', font=f, fill=(18, 18, 22, 255))
    
    # Gold wing flourish underline
    tw = d.textlength('Cygames', font=f)
    d.polygon([(40 * SS, 125 * SS), (40 * SS + tw, 125 * SS), (40 * SS + tw - 20 * SS, 133 * SS), (40 * SS, 133 * SS)], fill=col_gold)
    return finalize_logo(im)
SLEEVE_BUILDERS['cygames'] = build_cygames

# 15. Deel (Aston Villa sleeve sponsor)
def build_deel():
    W, H = 380 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (255, 110, 74, 255) # Deel Coral
    f = get_font(105 * SS, style='modern')
    d.text((40 * SS, 25 * SS), 'deel', font=f, fill=col)
    # Smile arc underline
    d.arc([40 * SS, 90 * SS, 160 * SS, 140 * SS], start=10, end=170, fill=col, width=10 * SS)
    return finalize_logo(im)
SLEEVE_BUILDERS['deel'] = build_deel

# 16. Snipes (PSG, Monaco streetwear sleeve sponsor)
def build_snipes():
    W, H = 440 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (230, 35, 30, 255) # Snipes Red
    f = get_font(96 * SS, style='sans_heavy')
    d.text((35 * SS, 28 * SS), 'snipes', font=f, fill=col)
    return finalize_logo(im)
SLEEVE_BUILDERS['snipes'] = build_snipes

# 17. Aptos (Atletico Madrid tech sleeve sponsor)
def build_aptos():
    W, H = 420 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (18, 18, 22, 255)
    f = get_font(94 * SS, style='sans_heavy')
    
    # 3 horizontal layered bars through 'A'
    d.text((35 * SS, 25 * SS), 'APTOS', font=f, fill=col)
    return finalize_logo(im)
SLEEVE_BUILDERS['aptos'] = build_aptos

# 18. JD Sports (Sevilla sleeve sponsor)
def build_jd_sports():
    W, H = 240 * SS, 240 * SS
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy, r = W // 2, H // 2, 105 * SS
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    
    f = get_font(115 * SS, style='sans_heavy')
    tw = d.textlength('JD', font=f)
    d.text((cx - int(tw // 2), cy - 68 * SS), 'JD', font=f, fill=0)
    
    col_img = Image.new('RGBA', (W, H), (18, 18, 22, 255))
    col_img.putalpha(mask)
    return finalize_logo(col_img)
SLEEVE_BUILDERS['jd_sports'] = build_jd_sports

# 19. Bitget (Juventus sleeve sponsor)
def build_bitget():
    W, H = 440 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col_cyan = (0, 242, 254, 255)
    col_blue = (0, 114, 255, 255)
    
    # Dual angled arrows
    ax = 55 * SS
    d.polygon([(ax - 20 * SS, 45 * SS), (ax + 10 * SS, 85 * SS), (ax - 20 * SS, 125 * SS), (ax - 5 * SS, 125 * SS), (ax + 25 * SS, 85 * SS), (ax - 5 * SS, 45 * SS)], fill=col_cyan)
    d.polygon([(ax + 5 * SS, 45 * SS), (ax + 35 * SS, 85 * SS), (ax + 5 * SS, 125 * SS), (ax + 20 * SS, 125 * SS), (ax + 50 * SS, 85 * SS), (ax + 20 * SS, 45 * SS)], fill=col_blue)
    
    f = get_font(84 * SS, style='modern')
    d.text((135 * SS, 38 * SS), 'Bitget', font=f, fill=(18, 18, 22, 255))
    return finalize_logo(im)
SLEEVE_BUILDERS['bitget'] = build_bitget

# 20. Tinder (Manchester City classic sleeve sponsor)
def build_tinder():
    W, H = 420 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (254, 60, 114, 255) # Tinder Flame Pink/Orange
    
    # Flame silhouette
    cx = 55 * SS
    d.pieslice([cx - 30 * SS, 45 * SS, cx + 30 * SS, 135 * SS], 0, 180, fill=col)
    d.polygon([(cx - 30 * SS, 90 * SS), (cx - 15 * SS, 35 * SS), (cx, 60 * SS), (cx + 25 * SS, 30 * SS), (cx + 30 * SS, 90 * SS)], fill=col)
    
    f = get_font(88 * SS, style='modern')
    d.text((115 * SS, 35 * SS), 'tinder', font=f, fill=col)
    return finalize_logo(im)
SLEEVE_BUILDERS['tinder'] = build_tinder

# 21. Western Union (Liverpool classic sleeve sponsor)
def build_western_union():
    W, H = 500 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col_yel = (255, 221, 0, 255)
    col_dark = (18, 18, 22, 255)
    
    # "WU" monogram block
    d.polygon([(35 * SS, 35 * SS), (80 * SS, 35 * SS), (105 * SS, 135 * SS), (60 * SS, 135 * SS)], fill=col_yel)
    f_wu = get_font(72 * SS, style='sans_heavy')
    d.text((45 * SS, 40 * SS), 'WU', font=f_wu, fill=col_dark)
    
    f_w = get_font(52 * SS, style='modern')
    f_u = get_font(42 * SS, style='modern')
    d.text((125 * SS, 35 * SS), 'Western', font=f_w, fill=col_dark)
    d.text((125 * SS, 88 * SS), 'Union', font=f_u, fill=col_dark)
    return finalize_logo(im)
SLEEVE_BUILDERS['western_union'] = build_western_union

# 22. Hyundai (Chelsea / Atletico classic sleeve sponsor)
def build_hyundai():
    W, H = 480 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (0, 44, 95, 255) # Hyundai Navy
    
    # Ellipse with tilted H
    cx = 65 * SS
    d.ellipse([cx - 45 * SS, 45 * SS, cx + 45 * SS, 125 * SS], outline=col, width=10 * SS)
    d.line([(cx - 20 * SS, 55 * SS), (cx - 10 * SS, 115 * SS)], fill=col, width=10 * SS)
    d.line([(cx + 10 * SS, 55 * SS), (cx + 20 * SS, 115 * SS)], fill=col, width=10 * SS)
    d.line([(cx - 16 * SS, 85 * SS), (cx + 16 * SS, 85 * SS)], fill=col, width=10 * SS)
    
    f = get_font(76 * SS, style='modern')
    d.text((135 * SS, 42 * SS), 'HYUNDAI', font=f, fill=col)
    return finalize_logo(im)
SLEEVE_BUILDERS['hyundai'] = build_hyundai

# 23. Kohler (Manchester United classic sleeve sponsor)
def build_kohler():
    W, H = 460 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (18, 18, 22, 255)
    f = get_font(95 * SS, style='sans_heavy')
    d.text((35 * SS, 28 * SS), 'KOHLER', font=f, fill=col)
    return finalize_logo(im)
SLEEVE_BUILDERS['kohler'] = build_kohler

# 24. Angry Birds (Everton classic sleeve sponsor)
def build_angry_birds():
    W, H = 480 * SS, 180 * SS
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (225, 25, 30, 255)
    
    # Red bird circular head + crest
    cx = 60 * SS
    d.ellipse([cx - 35 * SS, 45 * SS, cx + 35 * SS, 125 * SS], fill=col)
    d.polygon([(cx - 10 * SS, 45 * SS), (cx - 25 * SS, 20 * SS), (cx, 40 * SS)], fill=col)
    d.polygon([(cx + 5 * SS, 45 * SS), (cx + 20 * SS, 25 * SS), (cx + 15 * SS, 45 * SS)], fill=col)
    d.polygon([(cx + 15 * SS, 75 * SS), (cx + 40 * SS, 85 * SS), (cx + 15 * SS, 95 * SS)], fill=(255, 204, 0, 255)) # Beak
    
    f_ab = get_font(52 * SS, style='sans_heavy')
    f_b = get_font(52 * SS, style='sans_heavy')
    d.text((120 * SS, 35 * SS), 'ANGRY', font=f_ab, fill=(18, 18, 22, 255))
    d.text((120 * SS, 88 * SS), 'BIRDS', font=f_b, fill=col)
    return finalize_logo(im)
SLEEVE_BUILDERS['angry_birds'] = build_angry_birds


def generate_all_sleeve_sponsors(dest_dirs):
    """Generate all sleeve sponsor logos into target directories."""
    dirs = [Path(d) for d in (dest_dirs if isinstance(dest_dirs, (list, tuple)) else [dest_dirs])]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        
    print(f"Generating {len(SLEEVE_BUILDERS)} premier sleeve sponsor marks into {dirs}...")
    generated = []
    for brand, builder in sorted(SLEEVE_BUILDERS.items()):
        col_img = builder()
        white_img = make_white_silhouette(col_img)
        
        for d in dirs:
            p_col = d / f"{brand}.png"
            p_white = d / f"{brand}_white.png"
            col_img.save(p_col)
            white_img.save(p_white)
        generated.append(brand)
        
    print(f"Successfully generated {len(generated)} sleeve sponsor logos across target directories.")
    return generated


if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent
    targets = [
        root / 'content' / 'KitGenerator' / 'sleeve_logos',
        root / 'generator' / 'sleeve_logos'
    ]
    generate_all_sleeve_sponsors(targets)
