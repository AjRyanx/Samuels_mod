"""generate_sleeve_showcase_html.py - Interactive showcase for all 24 Sleeve Sponsors."""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent

SLEEVE_SPONSORS_META = [
    ("visit_rwanda", "Visit Rwanda", "Tourism & Airlines", "High-fashion tracked condensed sans stacked lockup", "Arsenal FC, PSG"),
    ("hp", "HP", "Tech & Computing", "Real Madrid iconic circular mark with precision negative space cutouts", "Real Madrid"),
    ("dxc", "DXC Technology", "Enterprise Tech", "Clean bold modern wordmark + purple tech dot accent", "Manchester United"),
    ("okx", "OKX", "Crypto & Web3", "Geometric tri-cube tech mark + clean modern sans", "Manchester City"),
    ("expedia", "Expedia", "Travel & Tourism", "Aerodynamic jet loop + clean modern lowercase sans", "Liverpool FC"),
    ("kraken", "Kraken", "Crypto & Web3", "Multi-tentacle crypto emblem + modern typography", "Tottenham Hotspur, Atlético Madrid"),
    ("ambilight", "Ambilight TV", "Electronics & Media", "Philips Ambilight sleek modern lowercase typography", "FC Barcelona"),
    ("msc_cruises", "MSC Cruises", "Maritime & Tourism", "Maritime compass rose star inside deep navy ring", "AC Milan"),
    ("ebay", "eBay", "E-Commerce", "Iconic overlapping four-color lettermark (red/blue/yellow/green)", "Inter Milan"),
    ("bingx", "BingX", "Crypto & Web3", "Dual-wing diamond crypto mark + modern typography", "Chelsea FC"),
    ("goat", "GOAT", "Fashion & Streetwear", "Ultra-heavy tracked high-fashion uppercase typography", "Paris Saint-Germain"),
    ("noon", "noon", "E-Commerce & Digital", "Vibrant yellow circular emblem with negative space typography", "Newcastle United"),
    ("gls", "GLS", "Logistics & Transport", "Heavy navy wordmark with fast logistics arrow chevron", "Borussia Dortmund"),
    ("cygames", "Cygames", "Gaming & Entertainment", "Dragon wing crest + athletic modern typography", "Juventus"),
    ("deel", "Deel", "Fintech & HR Tech", "Vibrant turquoise rounded geometric wordmark", "Aston Villa"),
    ("snipes", "Snipes", "Streetwear & Culture", "Athletic script flourish streetwear brand", "AS Monaco"),
    ("aptos", "Aptos", "Layer 1 Blockchain", "Multi-line horizontal bar tech wordmark", "Atlético Madrid"),
    ("jd_sports", "JD Sports", "Sports Retail", "King of Trainers circular badge with negative space JD cutout", "Sevilla FC"),
    ("bitget", "Bitget", "Fintech & Crypto", "Dual cyan/blue directional speed arrows + typography", "Juventus"),
    ("tinder", "Tinder", "Social Media", "Fiery flame gradient droplet + modern wordmark", "Manchester City Classic"),
    ("western_union", "Western Union", "Financial Services", "Diagonal dynamic slant stripes + corporate typography", "Liverpool Classic"),
    ("hyundai", "Hyundai", "Automotive", "Slanted oval 'H' emblem + corporate sans", "Chelsea & Atlético Classic"),
    ("kohler", "Kohler", "Manufacturing & Luxury", "Bold heavyweight industrial typography", "Manchester United Classic"),
    ("angry_birds", "Angry Birds", "Gaming & Entertainment", "Iconic red bird silhouette with eyebrow and crest", "Everton FC Classic"),
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PES 2021 / FL27 - Sleeve Sponsors Showcase</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-page: #0a0c10;
            --bg-card: #12151d;
            --bg-card-hover: #171b26;
            --border-card: #202636;
            --border-subtle: #191f2d;
            --text-main: #f0f3fa;
            --text-muted: #8b96ad;
            --text-dim: #54607b;
            --accent-cyan: #00d4ff;
            --accent-glow: rgba(0, 212, 255, 0.15);
            --accent-blue: #2563eb;
            --jersey-light: #f5f6fa;
            --jersey-dark: #12141a;
            --font-display: 'Space Grotesk', -apple-system, sans-serif;
            --font-body: 'Inter', -apple-system, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-page);
            color: var(--text-main);
            font-family: var(--font-body);
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
            padding-bottom: 80px;
        }

        .container {
            max-width: 1440px;
            margin: 0 auto;
            padding: 0 28px;
        }

        /* Top Nav */
        .top-nav {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px 0;
            border-bottom: 1px solid var(--border-subtle);
            margin-bottom: 36px;
        }

        .nav-brand {
            font-family: var(--font-display);
            font-weight: 700;
            font-size: 1.15rem;
            color: var(--text-main);
            letter-spacing: -0.02em;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .nav-badge {
            background: rgba(0, 212, 255, 0.12);
            color: var(--accent-cyan);
            border: 1px solid rgba(0, 212, 255, 0.3);
            font-family: var(--font-mono);
            font-size: 0.72rem;
            padding: 2px 8px;
            border-radius: 999px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .nav-links {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .nav-link {
            color: var(--text-muted);
            text-decoration: none;
            font-size: 0.88rem;
            font-weight: 500;
            padding: 6px 14px;
            border-radius: 8px;
            transition: all 0.15s ease;
            border: 1px solid transparent;
        }

        .nav-link:hover {
            color: var(--text-main);
            background: var(--bg-card);
            border-color: var(--border-card);
        }

        .nav-link.active {
            color: var(--accent-cyan);
            background: rgba(0, 212, 255, 0.08);
            border-color: rgba(0, 212, 255, 0.25);
        }

        /* Header */
        header {
            margin-bottom: 36px;
        }

        .title-row {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 16px;
            margin-bottom: 12px;
        }

        h1 {
            font-family: var(--font-display);
            font-size: 2.4rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #ffffff 40%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            color: var(--text-muted);
            font-size: 1.05rem;
            max-width: 820px;
        }

        .spec-pills {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 18px;
        }

        .spec-pill {
            background: #141923;
            border: 1px solid var(--border-card);
            color: var(--text-muted);
            font-size: 0.76rem;
            font-family: var(--font-mono);
            padding: 4px 10px;
            border-radius: 6px;
        }
        .spec-pill strong {
            color: var(--accent-cyan);
        }

        /* Controls Toolbar */
        .toolbar {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 14px;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 16px;
            margin-bottom: 32px;
        }

        .search-box {
            position: relative;
            flex: 1;
            min-width: 260px;
        }

        .search-input {
            width: 100%;
            background: #0d1017;
            border: 1px solid var(--border-card);
            border-radius: 8px;
            padding: 9px 14px 9px 38px;
            color: var(--text-main);
            font-family: var(--font-body);
            font-size: 0.9rem;
            outline: none;
            transition: border-color 0.15s ease;
        }

        .search-input:focus {
            border-color: var(--accent-cyan);
        }

        .search-icon {
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-dim);
            pointer-events: none;
        }

        .mode-toggle {
            display: flex;
            background: #0d1017;
            border: 1px solid var(--border-card);
            border-radius: 8px;
            padding: 3px;
            gap: 2px;
        }

        .mode-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 6px 14px;
            font-size: 0.82rem;
            font-weight: 600;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .mode-btn:hover {
            color: var(--text-main);
        }

        .mode-btn.active {
            background: var(--bg-card);
            color: var(--accent-cyan);
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }

        /* Sponsors Grid */
        .sponsors-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 22px;
        }

        .sponsor-card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 14px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.18s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.18s ease;
        }

        .sponsor-card:hover {
            transform: translateY(-3px);
            border-color: rgba(0, 212, 255, 0.35);
        }

        .preview-box {
            position: relative;
            height: 170px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            border-bottom: 1px solid var(--border-card);
        }

        .preview-box.view-split {
            display: grid;
            grid-template-columns: 1fr 1fr;
        }

        .split-pane {
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            padding: 16px;
        }

        .split-pane.light {
            background: var(--jersey-light);
            border-right: 1px solid rgba(0,0,0,0.1);
        }

        .split-pane.dark {
            background: var(--jersey-dark);
        }

        .pane-label {
            position: absolute;
            top: 8px;
            font-size: 0.65rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 2px 6px;
            border-radius: 4px;
        }

        .split-pane.light .pane-label {
            left: 8px;
            background: rgba(0, 0, 0, 0.08);
            color: #4b5563;
        }

        .split-pane.dark .pane-label {
            right: 8px;
            background: rgba(255, 255, 255, 0.1);
            color: #94a3b8;
        }

        .logo-img {
            max-width: 82%;
            max-height: 80px;
            object-fit: contain;
            filter: drop-shadow(0 2px 8px rgba(0,0,0,0.15));
            transition: transform 0.2s ease;
        }

        .sponsor-card:hover .logo-img {
            transform: scale(1.04);
        }

        .card-info {
            padding: 18px 20px 20px;
            display: flex;
            flex-direction: column;
            flex: 1;
        }

        .card-title-row {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            margin-bottom: 6px;
            gap: 8px;
        }

        .brand-name {
            font-family: var(--font-display);
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: -0.01em;
        }

        .brand-key {
            font-family: var(--font-mono);
            font-size: 0.72rem;
            color: var(--text-dim);
            background: #0d1017;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid var(--border-subtle);
        }

        .club-tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 0.76rem;
            color: var(--accent-cyan);
            background: rgba(0, 212, 255, 0.08);
            border: 1px solid rgba(0, 212, 255, 0.2);
            padding: 2px 8px;
            border-radius: 6px;
            margin-bottom: 10px;
            width: fit-content;
            font-weight: 600;
        }

        .category-tag {
            font-size: 0.72rem;
            font-weight: 600;
            color: #a0aec0;
            margin-bottom: 6px;
        }

        .brand-desc {
            font-size: 0.82rem;
            color: var(--text-muted);
            line-height: 1.45;
            flex: 1;
        }

        /* Footer */
        footer {
            margin-top: 60px;
            text-align: center;
            color: var(--text-dim);
            font-size: 0.82rem;
            border-top: 1px solid var(--border-subtle);
            padding-top: 30px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Top Nav -->
        <nav class="top-nav">
            <div class="nav-brand">
                <span>PES 2021 Kit Mod</span>
                <span class="nav-badge">Master League</span>
            </div>
            <div class="nav-links">
                <a href="sponsors_showcase.html" class="nav-link">Chest Sponsors (177)</a>
                <a href="sleeve_sponsors_showcase.html" class="nav-link active">Sleeve Sponsors (24)</a>
            </div>
        </nav>

        <header>
            <div class="title-row">
                <h1>Sleeve Sponsors Showcase</h1>
            </div>
            <p class="subtitle">
                Authentic modern football sleeve sponsorships anchored dynamically to the Left Sleeve UV island (Component 2: X=1750, Y=385) with calibrated anatomical wrap angle (+6.5°). Automatic WCAG contrast inversion pairs full-color branding with clean monochrome white silhouettes.
            </p>
            <div class="spec-pills">
                <span class="spec-pill">UV Anchor: <strong>Left Sleeve (1750, 385)</strong></span>
                <span class="spec-pill">Target Area: <strong>12,000 px²</strong></span>
                <span class="spec-pill">Wrap Rotation: <strong>+6.5° Clockwise</strong></span>
                <span class="spec-pill">Max Dimensions: <strong>180w × 80h</strong></span>
                <span class="spec-pill">Seam Margin: <strong>>180 px to Seams & Cuffs</strong></span>
                <span class="spec-pill">Scope: <strong>Master League Only (Exhibition Authentic)</strong></span>
            </div>
        </header>

        <!-- Controls Toolbar -->
        <div class="toolbar">
            <div class="search-box">
                <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <input type="text" id="searchInput" class="search-input" placeholder="Search sleeve brand, club (e.g. Arsenal, Real Madrid, Chelsea), or category...">
            </div>

            <div class="mode-toggle">
                <button class="mode-btn active" data-mode="split">Split View</button>
                <button class="mode-btn" data-mode="light">Light Kit</button>
                <button class="mode-btn" data-mode="dark">Dark Kit</button>
            </div>
        </div>

        <!-- Grid of Sponsors -->
        <div class="sponsors-grid" id="sponsorsGrid"></div>

        <footer>
            <p>Master League Dynamic Kit & Sponsor Mod for PES 2021 / SP Football Life 2027 (FL26/FL27). All sleeve sponsor logos conform strictly to PES left sleeve UV specifications with automatic WCAG contrast inversion.</p>
        </footer>
    </div>

    <script>
        const sponsors = __SLEEVE_JSON__;
        let currentMode = 'split';
        let searchKeyword = '';

        const grid = document.getElementById('sponsorsGrid');
        const searchInput = document.getElementById('searchInput');
        const modeButtons = document.querySelectorAll('.mode-btn');

        function renderCards() {
            const filtered = sponsors.filter(s => {
                const matchesSearch = !searchKeyword || 
                    s.name.toLowerCase().includes(searchKeyword) ||
                    s.key.toLowerCase().includes(searchKeyword) ||
                    s.category.toLowerCase().includes(searchKeyword) ||
                    s.desc.toLowerCase().includes(searchKeyword) ||
                    s.clubs.toLowerCase().includes(searchKeyword);
                return matchesSearch;
            });

            grid.innerHTML = filtered.map(s => {
                let previewHtml = '';
                if (currentMode === 'split') {
                    previewHtml = `
                        <div class="preview-box view-split">
                            <div class="split-pane light">
                                <span class="pane-label">Light Kit</span>
                                <img src="content/KitGenerator/sleeve_logos/${s.key}.png" alt="${s.name}" class="logo-img" loading="lazy">
                            </div>
                            <div class="split-pane dark">
                                <span class="pane-label">Dark Kit</span>
                                <img src="content/KitGenerator/sleeve_logos/${s.key}_white.png" alt="${s.name} White" class="logo-img" loading="lazy">
                            </div>
                        </div>
                    `;
                } else if (currentMode === 'light') {
                    previewHtml = `
                        <div class="preview-box" style="background: var(--jersey-light);">
                            <img src="content/KitGenerator/sleeve_logos/${s.key}.png" alt="${s.name}" class="logo-img" loading="lazy">
                        </div>
                    `;
                } else {
                    previewHtml = `
                        <div class="preview-box" style="background: var(--jersey-dark);">
                            <img src="content/KitGenerator/sleeve_logos/${s.key}_white.png" alt="${s.name} White" class="logo-img" loading="lazy">
                        </div>
                    `;
                }

                return `
                    <div class="sponsor-card">
                        ${previewHtml}
                        <div class="card-info">
                            <div class="card-title-row">
                                <span class="brand-name">${s.name}</span>
                                <span class="brand-key">${s.key}</span>
                            </div>
                            <span class="club-tag">${s.clubs}</span>
                            <span class="category-tag">${s.category}</span>
                            <p class="brand-desc">${s.desc}</p>
                        </div>
                    </div>
                `;
            }).join('');
        }

        searchInput.addEventListener('input', e => {
            searchKeyword = e.target.value.trim().toLowerCase();
            renderCards();
        });

        modeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                modeButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentMode = btn.getAttribute('data-mode');
                renderCards();
            });
        });

        renderCards();
    </script>
</body>
</html>
"""

def generate_sleeve_showcase():
    sponsors_data = [
        {"key": s[0], "name": s[1], "category": s[2], "desc": s[3], "clubs": s[4]}
        for s in SLEEVE_SPONSORS_META
    ]
    html = HTML_TEMPLATE.replace("__SLEEVE_JSON__", json.dumps(sponsors_data))
    out_file = ROOT / "sleeve_sponsors_showcase.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"Generated sleeve showcase HTML for {len(sponsors_data)} sponsors -> {out_file}")

if __name__ == '__main__':
    generate_sleeve_showcase()
