import math, hashlib, os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops
import numpy as np

SS = 4           # supersampling
E = 256          # emblem size in final px
# The original font paths are Linux ones; on Windows we fall back to metric /
# visual look-alikes so the same script runs anywhere.
_FONT_FILES = {
    'poppins': ['/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf',
                r'C:\Windows\Fonts\GOTHICB.TTF', r'C:\Windows\Fonts\ariblk.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'],
    'inter':   ['/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf',
                r'C:\Windows\Fonts\segoeuib.ttf', r'C:\Windows\Fonts\arialbd.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'],
    'advent':  ['/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf',
                '/System/Library/Fonts/Supplemental/Futura.ttc',
                '/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreadventor-bold.otf',
                r'C:\Windows\Fonts\bahnschrift.ttf', r'C:\Windows\Fonts\GOTHICB.TTF',
                '/System/Library/Fonts/Supplemental/Arial Bold.ttf'],
    'carlito': ['/System/Library/Fonts/Supplemental/Arial.ttf',
                '/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf',
                r'C:\Windows\Fonts\calibrib.ttf', r'C:\Windows\Fonts\arialbd.ttf'],
}


def _font_path(name):
    for p in _FONT_FILES.get(name, []):
        if os.path.isfile(p):
            return p
    for fallback in ['/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                     r'C:\Windows\Fonts\arialbd.ttf',
                     '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
        if os.path.isfile(fallback):
            return fallback
    raise FileNotFoundError('no font file for %r' % name)


F = {k: _font_path(k) for k in _FONT_FILES}

def hexc(h): h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def new_mask(): return Image.new('L', (E*SS, E*SS), 0)
def P(x, y): return (x*SS, y*SS)

# ---- emblem shapes (coordinates in a 256 box) -------------------------
def wing(d):
    for i in range(3):
        y = 60 + i*52
        d.polygon([P(30+i*14, y+34), P(70+i*14, y), P(226, y+8), P(120+i*14, y+34+8)], fill=255)
def ring(d):
    d.ellipse([P(20,20), P(236,236)], fill=255); d.ellipse([P(58,58), P(198,198)], fill=0)
    d.pieslice([P(70,70), P(186,186)], 200, 340, fill=255)
def hexa(d):
    pts = [P(128+108*math.cos(math.radians(a)), 128+108*math.sin(math.radians(a))) for a in range(30, 390, 60)]
    d.polygon(pts, fill=255)
    d.polygon([P(128,70), P(180,160), P(76,160)], fill=0)
def chev(d):
    for i in range(3):
        y = 40 + i*64
        d.polygon([P(24,y+60), P(128,y), P(232,y+60), P(232,y+92), P(128,y+32), P(24,y+92)], fill=255)
def sun(d):
    d.pieslice([P(28,28), P(228,228)], 180, 360, fill=255)
    for i in range(4):
        d.rectangle([P(28+i*52, 140), P(28+i*52+38, 150+ (3-i)*18+30)], fill=255)
def leaf(d):
    a = Image.new('L', (E*SS, E*SS), 0); b = Image.new('L', (E*SS, E*SS), 0)
    ImageDraw.Draw(a).ellipse([P(-60,-10), P(196,246)], fill=255)
    ImageDraw.Draw(b).ellipse([P(60,10), P(316,266)], fill=255)
    lens = ImageChops.multiply(a, b).rotate(-35, resample=Image.BICUBIC, center=(128*SS, 128*SS))
    d._image.paste(255, mask=lens)
    d.line([P(70,190), P(190,66)], fill=0, width=8*SS)
def bars(d):
    for i, h in enumerate((70, 120, 170, 220)):
        x = 24 + i*56
        d.rounded_rectangle([P(x,236-h), P(x+40,236)], radius=18*SS, fill=255)
def diamond(d):
    d.polygon([P(128,16), P(240,128), P(128,240), P(16,128)], fill=255)
    d.polygon([P(128,78), P(178,128), P(128,178), P(78,128)], fill=0)
def burst(d):
    pts = []
    for k in range(16):
        r = 116 if k % 2 == 0 else 62; a = math.radians(k*22.5 - 90)
        pts.append(P(128+r*math.cos(a), 128+r*math.sin(a)))
    d.polygon(pts, fill=255); d.ellipse([P(100,100), P(156,156)], fill=0)
def shield(d):
    d.polygon([P(32,30), P(224,30), P(224,130), P(128,236), P(32,130)], fill=255)
    d.polygon([P(76,74), P(180,74), P(180,120), P(128,176), P(76,120)], fill=0)
def orbit(d):
    for ang in (35, -35):
        m = Image.new('L', (E*SS, E*SS), 0); md = ImageDraw.Draw(m)
        md.ellipse([P(16,70), P(240,186)], outline=255, width=22*SS)
        m = m.rotate(ang, resample=Image.BICUBIC, center=(128*SS, 128*SS))
        d._image.paste(255, mask=m)
    d.ellipse([P(104,104), P(152,152)], fill=255)
def drop(d):
    d.ellipse([P(40,92), P(216,236)], fill=255)
    d.polygon([P(128,10), P(206,150), P(50,150)], fill=255)
    d.ellipse([P(88,138), P(122,172)], fill=0)

SHAPES = [wing, ring, hexa, chev, sun, leaf, bars, diamond, burst, shield, orbit, drop]

def gradient(c1, c2):
    """Vertical c1 -> c2 ramp (vectorised: this is the hot path for 100+ brands)."""
    n = E * SS
    t = np.linspace(0.0, 1.0, n, dtype=np.float32)[:, None]        # (n, 1)
    a = np.asarray(c1, dtype=np.float32)[None, :]                  # (1, 3)
    b = np.asarray(c2, dtype=np.float32)[None, :]                  # (1, 3)
    row = a * (1.0 - t) + b * t                                    # (n, 3)
    arr = np.repeat(row[:, None, :], n, axis=1).astype(np.uint8)   # (n, n, 3)
    return Image.fromarray(arr, 'RGB')

def emblem(shape, c1, c2, mono=None):
    m = new_mask(); d = ImageDraw.Draw(m); shape(d)
    fill = Image.new('RGB', m.size, mono) if mono else gradient(c1, c2)
    out = Image.new('RGBA', m.size, (0,0,0,0)); out.paste(fill, mask=m)
    return out.resize((E, E), Image.LANCZOS)

def spaced(draw, xy, text, font, fill, track):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + track
    return x

def lockup(brand, mono=None):
    """horizontal logo: emblem + wordmark (+ small descriptor); transparent PNG"""
    name, desc, shape, c1, c2, font, upper, track = brand
    word = name.upper() if upper else name
    f = ImageFont.truetype(F[font], 118 if upper else 132)
    fs = ImageFont.truetype(F['inter'], 38)
    tmp = ImageDraw.Draw(Image.new('RGBA', (10, 10)))
    w = int(sum(tmp.textlength(c, font=f) + track for c in word))
    ws = int(sum(tmp.textlength(c, font=fs) + 9 for c in desc.upper()))
    W = E + 40 + max(w, ws) + 20
    img = Image.new('RGBA', (W, E + 20), (0, 0, 0, 0))
    img.alpha_composite(emblem(shape, hexc(c1), hexc(c2), mono), (10, 10))
    d = ImageDraw.Draw(img)
    col = mono or hexc(c1)
    ty = 28 if desc else 62
    spaced(d, (E + 40, ty), word, f, col + (255,), track)
    if desc: spaced(d, (E + 44, ty + (150 if upper else 168)), desc.upper(), fs, (mono or (90, 96, 108)) + (255,), 9)
    return img.crop(img.getbbox())

BRANDS = [  # invented names: check each for resemblance before shipping
 ('Velmora', 'Airways',   wing,    '#0B3C8F', '#2E86DE', 'poppins', False, 2),
 ('Norquist', 'Bank',     shield,  '#0C5E4A', '#27A98B', 'inter',   True,  6),
 ('Qelvio',  'Mobile',    orbit,   '#6A1FB8', '#C04BE0', 'poppins', False, 1),
 ('Brisano', 'Energy',    sun,     '#E4572E', '#FFB020', 'advent',  False, 1),
 ('Altrava', 'Motors',    chev,    '#B3121F', '#F0523D', 'inter',   True,  8),
 ('Kyrenta', 'Foods',     leaf,    '#2E8B2E', '#9BD13F', 'carlito', False, 2),
 ('Dovrin',  'Telecom',   ring,    '#0A7EA4', '#3CCBE0', 'poppins', False, 1),
 ('Samuro',  'Electronics', hexa,  '#1B1F3B', '#4A56C9', 'inter',   True,  5),
 ('Pelorin', 'Insurance', diamond, '#7A1F3D', '#D1486E', 'advent',  False, 2),
 ('Trevanta','Logistics', bars,    '#F08A00', '#FFC24A', 'inter',   True,  4),
 ('Ixora',   'Pay',       burst,   '#14B8A6', '#0E7490', 'poppins', False, 2),
 ('Halvoro', 'Beverages', drop,    '#D61F69', '#FF7A59', 'carlito', False, 2),
 # ---- second wave ----
 ('Zaltera', 'Airways',   wing,    '#123A6B', '#3E7CB1', 'poppins', False, 2),
 ('Nordvane','Group',     shield,  '#14524E', '#2FA79B', 'inter',   True,  6),
 ('Pravano', 'Media',     orbit,   '#6D1FA8', '#B84BE0', 'poppins', False, 1),
 ('Novexa',  'Chemicals', hexa,    '#B45309', '#F59E0B', 'advent',  True,  4),
 ('Marrowby','Retail',    chev,    '#9E1230', '#E8455F', 'inter',   True,  7),
 ('Quillex', 'Pharma',    drop,    '#0E7C6B', '#34D3B4', 'carlito', False, 2),
 ('Ferrona', 'Steel',     bars,    '#374151', '#7C8798', 'inter',   True,  3),
 ('Halyx',   'Hotels',    sun,     '#B45309', '#FBBF24', 'advent',  False, 1),
 ('Vantrix', 'Systems',   burst,   '#5B21B6', '#8B5CF6', 'poppins', False, 2),
 ('Oribel',  'Cosmetics', leaf,    '#BE185D', '#F472B6', 'carlito', False, 2),
 ('Dravent', 'Motors',    diamond, '#0C4A6E', '#0EA5E9', 'inter',   True,  6),
 ('Kemprow', 'Brewing',   ring,    '#7C2D12', '#EA580C', 'poppins', False, 1),
]

# ---- 100+ extra brands ---------------------------------------------------
# Deterministic, invented names built from a curated onset list so every name
# is unique and reads like a company.  The first 24 brands above are the
# hand-approved ones and keep their file names; these are additive.
_EXTRA_ONSET = [
    'Ad', 'Alder', 'Am', 'An', 'Ar', 'Ard', 'As', 'Aven', 'Bal', 'Bar',
    'Bel', 'Bev', 'Bran', 'Bri', 'Cad', 'Cal', 'Cam', 'Car', 'Cas', 'Cor',
    'Cres', 'Dal', 'Dan', 'Dar', 'Del', 'Der', 'Dor', 'Dun', 'El', 'Eld',
    'Ely', 'Fal', 'Fen', 'Fer', 'Fyr', 'Gal', 'Gan', 'Gar', 'Glen', 'Graf',
    'Hal', 'Har', 'Hel', 'Hes', 'Hol', 'Ib', 'Il', 'Jar', 'Kal', 'Kar',
    'Kel', 'Ken', 'Kin', 'Kor', 'Lar', 'Lom', 'Lum', 'Lyn', 'Mal', 'Mar',
    'Mel', 'Mer', 'Mor', 'Nal', 'Nav', 'Nel', 'Nor', 'Nov', 'Oak', 'Or',
    'Os', 'Pal', 'Par', 'Pel', 'Per', 'Pyr', 'Quen', 'Rad', 'Ran', 'Rav',
    'Ren', 'Rho', 'Ril', 'Ros', 'Sal', 'Sam', 'Sar', 'Sel', 'Ser', 'Sil',
    'Sol', 'Syl', 'Tam', 'Tar', 'Tel', 'Ter', 'Thal', 'Tor', 'Trav', 'Ul',
    'Ur', 'Val', 'Var', 'Vas', 'Vel', 'Ven', 'Ver', 'Ves', 'Vor', 'Wal',
    'Wen', 'Wil', 'Xan', 'Yar', 'Zan', 'Zel',
]
_EXTRA_SUFFIX = ['ara', 'avo', 'elix', 'enta', 'era', 'ex', 'ia', 'ika', 'ino',
                 'ira', 'is', 'ola', 'ora', 'oro', 'ova', 'ton', 'tro', 'ura',
                 'via', 'vion', 'ano', 'aro', 'enti', 'ovo', 'eno', 'ilo',
                 'amo', 'yne', 'eon', 'ix']
_EXTRA_DESC = ['Airways', 'Bank', 'Mobile', 'Energy', 'Motors', 'Foods', 'Telecom',
               'Electronics', 'Insurance', 'Logistics', 'Pay', 'Beverages', 'Group',
               'Media', 'Chemicals', 'Retail', 'Pharma', 'Steel', 'Hotels', 'Systems',
               'Cosmetics', 'Brewing', 'Software', 'Cloud', 'Digital', 'Airlines',
               'Rail', 'Capital', 'Ventures', 'Holding', 'Textiles', 'Cement',
               'Aero', 'Robotics', 'Games', 'Studios', 'Fitness', 'Coffee', 'Dairy',
               'Farms', 'Mining', 'Oil', 'Gas', 'Power', 'Solar', 'Wind', 'Water',
               'Ports', 'Shipping', 'Cargo', 'Courier', 'Trust', 'Invest', 'Assets',
               'Fintech', 'Networks', 'Wireless', 'Chips', 'Data', 'Analytics',
               'Labs', 'Bio', 'Health', 'Care', 'Optics', 'Audio', 'Vision', 'Print',
               'Paper', 'Glass', 'Ceramics', 'Living', 'Home', 'Tools', 'Auto',
               'Tyres', 'Bikes', 'Boats', 'Jets', 'Space', 'Security', 'Build',
               'Realty', 'Estate', 'Travel', 'Tours', 'Resorts', 'Dining', 'Bakery',
               'Snacks', 'Drinks', 'Wines', 'Sports', 'Outdoor', 'Racing', 'Apparel',
               'Shoes', 'Fashion', 'Beauty', 'Spa', 'Jewels', 'Watches', 'Gifts',
               'Pets', 'Green', 'Eco', 'Clean', 'Fresh', 'Vital', 'Prime', 'Elite',
               'Nova', 'Zen', 'Orbit', 'Vertex', 'Apex', 'Summit', 'Core', 'Nexus',
               'Grid', 'Loop', 'Sphere', 'Globe', 'Atlas', 'Compass', 'Anchor',
               'Beacon', 'Signal', 'Pulse', 'Wave', 'Spark', 'Flare', 'Beam', 'Ray',
               'Star', 'Comet', 'Galaxy', 'Cosmos', 'Titan', 'Onyx', 'Opal', 'Jade',
               'Amber', 'Coral', 'Pearl']
_EXTRA_PALETTES = [
    ('#0B3C8F', '#2E86DE'), ('#0C5E4A', '#27A98B'), ('#6A1FB8', '#C04BE0'),
    ('#E4572E', '#FFB020'), ('#B3121F', '#F0523D'), ('#2E8B2E', '#9BD13F'),
    ('#0A7EA4', '#3CCBE0'), ('#1B1F3B', '#4A56C9'), ('#7A1F3D', '#D1486E'),
    ('#F08A00', '#FFC24A'), ('#14B8A6', '#0E7490'), ('#D61F69', '#FF7A59'),
    ('#123A6B', '#3E7CB1'), ('#14524E', '#2FA79B'), ('#6D1FA8', '#B84BE0'),
    ('#B45309', '#F59E0B'), ('#9E1230', '#E8455F'), ('#0E7C6B', '#34D3B4'),
    ('#374151', '#7C8798'), ('#B45309', '#FBBF24'), ('#5B21B6', '#8B5CF6'),
    ('#BE185D', '#F472B6'), ('#0C4A6E', '#0EA5E9'), ('#7C2D12', '#EA580C'),
    ('#1F2937', '#6B7280'), ('#065F46', '#10B981'), ('#7F1D1D', '#EF4444'),
    ('#1E3A8A', '#60A5FA'), ('#4C1D95', '#A78BFA'), ('#831843', '#EC4899'),
    ('#134E4A', '#2DD4BF'), ('#713F12', '#FACC15'), ('#3F6212', '#84CC16'),
    ('#0C4A6E', '#38BDF8'), ('#701A75', '#E879F9'), ('#78350F', '#FBBF24'),
    ('#052E16', '#22C55E'), ('#0F172A', '#38BDF8'), ('#4A044E', '#D946EF'),
    ('#7C2D12', '#FB923C'),
]


def _extra_brands(n=116):
    """n extra (name, descriptor, shape, c1, c2, font, upper, track) rows."""
    fonts = ('poppins', 'inter', 'advent', 'carlito')
    used = {b[0] for b in BRANDS}
    out = []
    for i in range(n):
        name = _EXTRA_ONSET[i % len(_EXTRA_ONSET)] + \
            _EXTRA_SUFFIX[(i * 7 + 3) % len(_EXTRA_SUFFIX)]
        while name in used:
            name += 'a'
        used.add(name)
        pal = _EXTRA_PALETTES[(i * 3 + 1) % len(_EXTRA_PALETTES)]
        out.append((name,
                    _EXTRA_DESC[(i * 13 + 5) % len(_EXTRA_DESC)],
                    SHAPES[(i * 5 + 1) % len(SHAPES)],
                    pal[0], pal[1],
                    fonts[(i * 7) % 4],
                    (i % 3 == 0),
                    1 + (i % 8)))
    return out


BRANDS = BRANDS + _extra_brands(116)

if __name__ == '__main__':
    import sys
    try:
        from sponsor_builder import BUILDERS, generate_all_sponsors
    except ImportError:
        from generator.sponsor_builder import BUILDERS, generate_all_sponsors

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('content/KitGenerator/logos')
    target.mkdir(parents=True, exist_ok=True)
    
    # 1. Generate all premier realistic sponsors
    added = generate_all_sponsors(target)
    
    # 2. Generate contact sheet of all modern brand logos
    all_brands = sorted(BUILDERS.keys())
    cols, tw, th = 4, 620, 200
    rows = (len(all_brands) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * tw, rows * th), (30, 30, 34))
    
    for i, brand in enumerate(all_brands):
        r, c = divmod(i, cols)
        dark = (i % 2 == 1)
        bg = (20, 24, 33) if dark else (244, 244, 241)
        tile = Image.new('RGBA', (tw, th), bg + (255,))
        
        logo_path = target / (f"{brand}_white.png" if dark else f"{brand}.png")
        if logo_path.is_file():
            lg = Image.open(logo_path).convert('RGBA')
            s = min((tw - 60) / max(1, lg.width), (th - 50) / max(1, lg.height))
            lg = lg.resize((max(1, int(lg.width * s)), max(1, int(lg.height * s))), Image.BILINEAR)
            tile.alpha_composite(lg, ((tw - lg.width) // 2, (th - lg.height) // 2))
            
        sheet.paste(tile.convert('RGB'), (c * tw, r * th))
        
    sheet_path = target.parent / 'logos_sheet.png'
    sheet.save(sheet_path)
    print(f'Wrote contact sheet with {len(all_brands)} sponsors -> {sheet_path}')
