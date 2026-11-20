"""generate_showcase_html.py - Generates an interactive, premium HTML showcase for all 177 sponsor logos."""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent

SPONSORS_META = [
    # Airlines & Tourism
    ("fly_emirates", "Fly Emirates", "Airlines & Tourism", "Arabic-inspired English calligraphy with curved flourish"),
    ("etihad", "Etihad Airways", "Airlines & Tourism", "Faceted champagne diamond crest + tracked typography"),
    ("qatar_air", "Qatar Airways", "Airlines & Tourism", "Burgundy oryx horn crest + modern clean serif"),
    ("singapore_air", "Singapore Airlines", "Airlines & Tourism", "Golden bird crest + bold navy wordmark"),
    ("turkish_air", "Turkish Airlines", "Airlines & Tourism", "Red circle flying goose emblem + modern sans"),
    ("lufthansa", "Lufthansa", "Airlines & Tourism", "Deep blue circle crane emblem + classic modern sans"),
    ("riyadh_air", "Riyadh Air", "Airlines & Tourism", "Lavender purple modern iridescent wing crest"),
    ("saudia", "Saudia", "Airlines & Tourism", "Emerald green palm tree & dual crossed swords"),
    ("virgin_atl", "Virgin Atlantic", "Airlines & Tourism", "Ruby red iconic cursive script flourish"),
    ("british_air", "British Airways", "Airlines & Tourism", "Royal blue & red speedmarque ribbon"),
    ("air_france", "Air France", "Airlines & Tourism", "Navy with sleek red accent bar"),
    ("qantas", "Qantas", "Airlines & Tourism", "Red flying kangaroo tail fin crest"),
    ("delta", "Delta Air Lines", "Airlines & Tourism", "Navy & red geometric widget triangle"),
    ("visit_rwanda", "Visit Rwanda", "Airlines & Tourism", "High-fashion tracked condensed sans stacked lockup"),
    ("visit_saudi", "Visit Saudi", "Airlines & Tourism", "Flowing turquoise & gold script lockup"),
    ("visit_dubai", "Visit Dubai", "Airlines & Tourism", "Multi-color fluid modern geometric lockup"),

    # Betting & Gaming
    ("betway", "Betway", "Betting & Gaming", "Clean geometric heavy lowercase with vibrant lime dot"),
    ("stake", "Stake", "Betting & Gaming", "Sleek ultra-modern geometric italic font"),
    ("1xbet", "1xBet", "Betting & Gaming", "Dynamic sports betting angled slant container"),
    ("bet365", "Bet365", "Betting & Gaming", "Signature dark green stadium capsule with yellow/white type"),
    ("bwin", "Bwin", "Betting & Gaming", "Heavy bold lowercase with yellow dot on the 'i'"),
    ("unibet", "Unibet", "Betting & Gaming", "Deep forest green circle with white U crest"),
    ("dafabet", "Dafabet", "Betting & Gaming", "Crimson rounded shield badge + gold/white typography"),
    ("parimatch", "Parimatch", "Betting & Gaming", "Electric neon yellow dynamic parallelogram slant box"),
    ("888sport", "888sport", "Betting & Gaming", "Interlocking triple 8s in vibrant orange"),
    ("w88", "W88", "Betting & Gaming", "Golden coin crest with white W + bold navy typography"),
    ("mansion", "Mansion", "Betting & Gaming", "Crimson casino shield crest + gold typography"),
    ("betsson", "Betsson", "Betting & Gaming", "Clean Nordic geometric orange lowercase"),
    ("hollywoodbets", "Hollywoodbets", "Betting & Gaming", "Purple star emblem with gold trail"),
    ("bk8", "BK8", "Betting & Gaming", "Navy & orange sports shield crest"),
    ("betano", "Betano", "Betting & Gaming", "Fiery orange rounded athletic container"),
    ("sportingbet", "Sportingbet", "Betting & Gaming", "Royal blue & scarlet red dual-tone wordmark"),
    ("leovegas", "LeoVegas", "Betting & Gaming", "Stylized orange lion paw crest + modern typography"),
    ("betvictor", "BetVictor", "Betting & Gaming", "Sleek minimalist dark navy athletic lettering"),
    ("betfred", "Betfred", "Betting & Gaming", "Royal blue rounded athletic block with red accent"),
    ("draftkings", "DraftKings", "Betting & Gaming", "Forest green with golden crown crest"),

    # Banking & Finance
    ("barclays", "Barclays", "Banking & Finance", "Cyan spread-eagle heraldic crest + dark navy wordmark"),
    ("santander", "Santander", "Banking & Finance", "Bright red flame spark mark + modern clean rounded sans"),
    ("std_chartered", "Standard Chartered", "Banking & Finance", "Interlocking dual-helix ribbons (cyan & green)"),
    ("hsbc", "HSBC", "Banking & Finance", "Red & white tessellated geometric triangles"),
    ("ubs", "UBS", "Banking & Finance", "Three crossed keys crest + bold corporate lettering"),
    ("revolut", "Revolut", "Banking & Finance", "Ultra-clean modern minimalist fintech typography"),
    ("chase", "Chase", "Banking & Finance", "Chase blue octagonal geometric ring badge"),
    ("bnp_paribas", "BNP Paribas", "Banking & Finance", "Emerald green square star swirl + corporate typography"),
    ("deutsche_bank", "Deutsche Bank", "Banking & Finance", "Blue square with diagonal slash emblem"),
    ("caixabank", "CaixaBank", "Banking & Finance", "Blue & yellow Miró star figure crest"),
    ("intesa", "Intesa Sanpaolo", "Banking & Finance", "Deep green & orange interlocking arch bank crest"),
    ("ing", "ING", "Banking & Finance", "Vibrant orange lion silhouette crest"),
    ("bbva", "BBVA", "Banking & Finance", "Navy blue ascending modern letterforms"),
    ("soc_gen", "Société Générale", "Banking & Finance", "Scarlet & black split corporate square"),
    ("klarna", "Klarna", "Banking & Finance", "Soft rose pill badge container + lowercase modern sans"),
    ("paypal", "PayPal", "Banking & Finance", "Dual-blue overlapping double P monogram"),
    ("stripe", "Stripe", "Banking & Finance", "Violet slate sleek diagonal-cut modern fintech typography"),
    ("wise", "Wise", "Banking & Finance", "Forest green & neon lime fast-flag accent"),
    ("mastercard", "Mastercard", "Banking & Finance", "Interlocking scarlet & orange circles"),
    ("visa", "Visa", "Banking & Finance", "Dark navy with golden winged V italic lettering"),

    # Tech & Streaming
    ("spotify", "Spotify", "Tech & Streaming", "Circular soundwaves icon + sleek modern sans"),
    ("teamviewer", "TeamViewer", "Tech & Streaming", "Electric blue circle with opposing arrows"),
    ("rakuten", "Rakuten", "Tech & Streaming", "Bold red wordmark + red underline chevron"),
    ("samsung", "Samsung", "Tech & Streaming", "Bold corporate navy sans"),
    ("sony", "Sony", "Tech & Streaming", "Iconic wide-tracked tech slab-serif"),
    ("nintendo", "Nintendo", "Tech & Streaming", "Red pill capsule container enclosing iconic rounded font"),
    ("google_pixel", "Google Pixel", "Tech & Streaming", "Multi-color G emblem + clean modern sans"),
    ("apple_tv", "Apple TV+", "Tech & Streaming", "Apple silhouette + minimalist modern typography"),
    ("amazon_prime", "Amazon Prime", "Tech & Streaming", "Electric blue lettering + curved yellow smile arrow"),
    ("snapdragon", "Snapdragon", "Tech & Streaming", "Glowing red/orange dragon flame sphere"),
    ("sharp", "Sharp", "Tech & Streaming", "Iconic bold red industrial serif"),
    ("jvc", "JVC", "Tech & Streaming", "Heavy bold condensed red geometric font"),
    ("philips", "Philips", "Tech & Streaming", "Royal blue shield stars-and-waves emblem"),
    ("panasonic", "Panasonic", "Tech & Streaming", "Classic blue industrial electronics sans"),
    ("tcl", "TCL", "Tech & Streaming", "Bright red dynamic angled typography"),
    ("hisense", "Hisense", "Tech & Streaming", "Modern cyan consumer electronics wordmark"),
    ("xbox", "XBOX", "Tech & Streaming", "Luminous green sphere X emblem + bold geometric font"),
    ("playstation", "PlayStation", "Tech & Streaming", "Iconic PS geometric lockup + bold modern text"),
    ("paramount", "Paramount+", "Tech & Streaming", "Mountain peak stars arc + bold modern typography"),
    ("dazn", "DAZN", "Tech & Streaming", "High-contrast heavy geometric sports streaming block"),
    ("intel", "Intel", "Tech & Streaming", "Electric blue modern tech dot-matrix font"),
    ("lenovo", "Lenovo", "Tech & Streaming", "Cyber red modern tech block"),

    # Telecom & Mobile
    ("vodafone", "Vodafone", "Telecom & Mobile", "Iconic red speech mark quotation droplet circle"),
    ("t_mobile", "T-Mobile", "Telecom & Mobile", "Magenta square dots ·T··· + modern bold font"),
    ("o2", "O2", "Telecom & Mobile", "Deep blue floating glass oxygen bubbles"),
    ("orange", "Orange", "Telecom & Mobile", "Iconic vivid orange square + clean lowercase"),
    ("ee", "EE", "Telecom & Mobile", "Vibrant aqua & yellow dual circle tech dots"),
    ("movistar", "Movistar", "Telecom & Mobile", "Bright green ribbon M emblem + modern navy text"),
    ("telekom", "Telekom", "Telecom & Mobile", "Magenta digital grid square"),
    ("three", "Three (3)", "Telecom & Mobile", "Massive stylized iconic digit 3"),
    ("zain", "Zain", "Telecom & Mobile", "Teal & purple swirling ribbon crest"),
    ("stc", "stc", "Telecom & Mobile", "Deep purple & coral high-tech modern lowercase"),
    ("claro", "Claro", "Telecom & Mobile", "Red speech circle + modern white typography"),
    ("rogers", "Rogers", "Telecom & Mobile", "Crimson red mobius ribbon ring"),

    # Automotive & Tires
    ("jeep", "Jeep", "Automotive & Tires", "Iconic heavy condensed bold rugged sans"),
    ("chevrolet", "Chevrolet", "Automotive & Tires", "Iconic golden bowtie crest + bold corporate lettering"),
    ("audi", "Audi", "Automotive & Tires", "Four interlocking slate/chrome rings"),
    ("mercedes", "Mercedes-Benz", "Automotive & Tires", "Three-pointed silver star in circle + elegant serif"),
    ("bmw", "BMW", "Automotive & Tires", "Royal blue & black roundel propeller emblem"),
    ("hyundai", "Hyundai", "Automotive & Tires", "Slanted oval H badge + modern bold wordmark"),
    ("pirelli", "Pirelli", "Automotive & Tires", "Iconic red long-roof P stretching across wordmark"),
    ("yokohama", "Yokohama", "Automotive & Tires", "Red angular Y crest + heavy bold black typography"),
    ("bridgestone", "Bridgestone", "Automotive & Tires", "Black & red keystone B emblem"),
    ("continental", "Continental", "Automotive & Tires", "Gold/orange galloping horse crest"),
    ("michelin", "Michelin", "Automotive & Tires", "Royal blue & yellow road crest + italic font"),
    ("honda", "Honda", "Automotive & Tires", "Pure red trapezoid H emblem + bold serif"),
    ("kia", "Kia", "Automotive & Tires", "Futuristic connected stroke modern wordmark"),
    ("nissan", "Nissan", "Automotive & Tires", "Chrome slate circle badge + bold modern sans"),
    ("alfa_romeo", "Alfa Romeo", "Automotive & Tires", "Red cross & green serpent heraldic crest"),
    ("castrol", "Castrol", "Automotive & Tires", "Forest green & red circular swoosh"),
    ("mobil1", "Mobil 1", "Automotive & Tires", "Royal blue Mobil + iconic red digit 1"),
    ("shell_helix", "Shell Helix", "Automotive & Tires", "Scallop yellow & red seashell + modern bold font"),

    # Crypto & Web3
    ("crypto_com", "Crypto.com", "Crypto & Web3", "Deep navy hexagon shield with futuristic crest"),
    ("binance", "Binance", "Crypto & Web3", "Iconic golden geometric diamond mark with center rhombuses"),
    ("okx", "OKX", "Crypto & Web3", "Cyber-modern black/white square pixel matrix"),
    ("bybit", "Bybit", "Crypto & Web3", "Vivid orange & black diagonal slash wordmark"),
    ("coinbase", "Coinbase", "Crypto & Web3", "Coinbase blue roundel C glyph"),
    ("etoro", "eToro", "Crypto & Web3", "Vibrant green bull horns emblem"),
    ("kraken", "Kraken", "Crypto & Web3", "Deep purple tentacle geometry + bold modern wordmark"),
    ("bitget", "Bitget", "Crypto & Web3", "Cyan teal speed arrows + modern fintech sans"),
    ("kucoin", "KuCoin", "Crypto & Web3", "Jade teal geometric interlocking K"),
    ("tezos", "Tezos", "Crypto & Web3", "Classic blue mathematical fractal t monogram"),
    ("polkadot", "Polkadot", "Crypto & Web3", "Bright magenta multi-dot network glyph"),

    # Energy & Industry
    ("petronas", "Petronas", "Energy & Industry", "Emerald cyan faceted teardrop crest"),
    ("shell", "Shell", "Energy & Industry", "Scallop yellow & red seashell emblem"),
    ("total_energies", "TotalEnergies", "Energy & Industry", "Multi-color rainbow spiral ribbon"),
    ("aramco", "Aramco", "Energy & Industry", "Vivid cyan & green solar energy burst"),
    ("red_bull", "Red Bull", "Energy & Industry", "Golden sun with dual red charging bulls"),
    ("monster", "Monster Energy", "Energy & Industry", "Triple neon green claw scratch mark"),
    ("enel", "Enel", "Energy & Industry", "Rainbow gradient light wave"),
    ("repsol", "Repsol", "Energy & Industry", "Solar red & orange segmented horizon sun"),
    ("ineos", "INEOS", "Energy & Industry", "Dark navy minimalist industrial uppercase"),
    ("siemens", "Siemens", "Energy & Industry", "Petrol teal heavy corporate modern sans"),
    ("eni", "Eni", "Energy & Industry", "Black six-legged fire-breathing dog on yellow badge"),
    ("qatar_energy", "QatarEnergy", "Energy & Industry", "Dual teardrop gas/oil crest in blue/cyan"),
    ("bp", "BP", "Energy & Industry", "Green & yellow helios sunburst rosette"),

    # Insurance & Healthcare
    ("allianz", "Allianz", "Insurance & Healthcare", "Navy blue circle containing three silver vertical bars"),
    ("aia", "AIA", "Insurance & Healthcare", "Crimson red sharp triple-peak mountain monogram"),
    ("axa", "AXA", "Insurance & Healthcare", "Dark navy with bright red slash accent"),
    ("zurich", "Zurich", "Insurance & Healthcare", "Zurich blue circle Z crest"),
    ("aviva", "Aviva", "Insurance & Healthcare", "Leaf green & yellow triangular prism monogram"),
    ("aig", "AIG", "Insurance & Healthcare", "Royal blue rounded square container + white letters"),
    ("generali", "Generali", "Insurance & Healthcare", "Venetian red winged lion crest"),
    ("sanitas", "Sanitas", "Insurance & Healthcare", "Medical cyan cross-plus crest"),

    # Beverages & Lifestyle
    ("carlsberg", "Carlsberg", "Beverages & Lifestyle", "Danish brewer green cursive script + hop leaf flourish"),
    ("heineken", "Heineken", "Beverages & Lifestyle", "Iconic red five-pointed star + brewer wordmark"),
    ("estrella", "Estrella Galicia", "Beverages & Lifestyle", "Spanish red & gold crowned star badge"),
    ("mahou", "Mahou", "Beverages & Lifestyle", "Crimson heraldic crown crest + vintage athletic script"),
    ("peroni", "Peroni", "Beverages & Lifestyle", "Italian ribbon crest + elegant modern serif"),
    ("budweiser", "Budweiser", "Beverages & Lifestyle", "Iconic red bowtie banner + classic script/sans"),
    ("pepsi", "Pepsi", "Beverages & Lifestyle", "Red/white/blue wave globe + modern rounded lowercase"),

    # Iconic Emblems & Specials (Logo-Only / Artist Takeovers)
    ("spotify_icon", "Spotify Icon", "Iconic Emblems & Specials", "Barcelona-style pure circular 3-wave soundmark"),
    ("drake_owl", "OVO Owl", "Iconic Emblems & Specials", "Barcelona El Clásico Drake gold owl silhouette"),
    ("rolling_stones", "Rolling Stones Tongue", "Iconic Emblems & Specials", "Barcelona El Clásico hot red tongue & lips"),
    ("rosalia_motomami", "Motomami Butterfly", "Iconic Emblems & Specials", "Barcelona El Clásico Rosalia butterfly-M wings"),
    ("karol_g_heart", "Karol G Heart", "Iconic Emblems & Specials", "Barcelona El Clásico thorny barbed-wire heart"),
    ("coldplay_moon", "Coldplay Moon Music", "Iconic Emblems & Specials", "Barcelona El Clásico celestial crescent orbit"),
    ("playstation_shapes", "PlayStation Shapes", "Iconic Emblems & Specials", "Sony iconic controller symbols (△ ◯ ✕ □)"),
    ("apple_logo", "Apple", "Iconic Emblems & Specials", "Ultra-minimalist monochrome silhouette with bite & leaf"),
    ("mastercard_circles", "Mastercard Circles", "Iconic Emblems & Specials", "Interlocking scarlet & amber dual circles"),
    ("jumpman", "Air Jordan Jumpman", "Iconic Emblems & Specials", "Michael Jordan flight silhouette (PSG kit style)"),
    ("redbull_emblem", "Red Bull Pure Emblem", "Iconic Emblems & Specials", "Twin charging muscular bulls colliding at sunrise"),
    ("autobot_crest", "Autobots Crest", "Iconic Emblems & Specials", "Transformers mechanical crest (Inter Milan kit)"),
    ("paramount_peak", "Paramount Mountain", "Iconic Emblems & Specials", "Snow-capped peak ringed by 11 stars (Inter kit)"),
    ("target_bullseye", "Target Bullseye", "Iconic Emblems & Specials", "Bold concentric circular rings (Minnesota/streetwear)"),
    ("one_and_one", "1&1 Square", "Iconic Emblems & Specials", "Borussia Dortmund minimalist blue cube mark"),
    ("o2_bubbles", "O2 Bubbles", "Iconic Emblems & Specials", "Arsenal historic era O2 with luminous bubble rings"),
    ("mercedes_star", "Mercedes Star", "Iconic Emblems & Specials", "Three-pointed star inside precision ring"),
    ("audi_rings", "Audi Rings", "Iconic Emblems & Specials", "Four horizontally interlocking luxury rings"),
    ("mitsubishi_diamonds", "Mitsubishi 3 Diamonds", "Iconic Emblems & Specials", "Three red faceted rhombuses (classic 90s kit)"),
    ("tesla_crest", "Tesla Crest", "Iconic Emblems & Specials", "Minimalist futuristic T-sword shield"),
    ("ethereum_prism", "Ethereum Crystal", "Iconic Emblems & Specials", "Geometric 3D diamond crystal octahedron"),
    ("bitcoin_symbol", "Bitcoin Coin", "Iconic Emblems & Specials", "Golden coin ring with double-stroke ₿ cutout"),
    ("xbox_sphere", "Xbox Sphere", "Iconic Emblems & Specials", "3D sphere with sculpted diagonal X channels"),
    ("unicef_emblem", "UNICEF Emblem", "Iconic Emblems & Specials", "Barcelona classic humanitarian laurel & globe mark"),
    ("volkswagen_roundel", "Volkswagen Roundel", "Iconic Emblems & Specials", "Wolfsburg classic interlocking V & W badge"),
    ("shell_pecten", "Shell Pecten", "Iconic Emblems & Specials", "Fluted scallop seashell with red trim"),
    ("bayer_cross", "Bayer Cross", "Iconic Emblems & Specials", "Bayer Leverkusen intersecting cross in ring"),
    ("snapdragon_icon", "Snapdragon Ball", "Iconic Emblems & Specials", "Fiery cyber dragon ball fireball mark"),
    ("atari_fuji", "Atari Fuji Crest", "Iconic Emblems & Specials", "Iconic retro gaming tri-line wing crest"),
    ("nasa_worm", "NASA Vector Orbit", "Iconic Emblems & Specials", "Supersonic red chevron & planetary orbit")
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dynamic Kit & Sponsor Mod — 177 Premier Sponsor Logos</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090B10;
            --surface: #111520;
            --surface-hover: #181F2F;
            --border: #1F2839;
            --accent: #38BDF8;
            --accent-glow: rgba(56, 189, 248, 0.15);
            --gold: #F59E0B;
            --text-main: #F3F4F6;
            --text-muted: #94A3B8;
            --jersey-light: #F4F4F6;
            --jersey-dark: #12151D;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg);
            color: var(--text-main);
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            padding: 32px 24px;
            line-height: 1.5;
            min-height: 100vh;
        }
        .container {
            max-width: 1480px;
            margin: 0 auto;
        }
        /* Header */
        .header {
            border-bottom: 1px solid var(--border);
            padding-bottom: 24px;
            margin-bottom: 28px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            flex-wrap: wrap;
            gap: 20px;
        }
        .header-left h1 {
            font-size: 32px;
            font-weight: 800;
            letter-spacing: -0.8px;
            background: linear-gradient(135deg, #FFFFFF 30%, #94A3B8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header-left p {
            color: var(--text-muted);
            font-size: 15px;
            margin-top: 6px;
        }
        .stats-pill {
            display: inline-flex;
            align-items: center;
            gap: 12px;
            background: var(--surface);
            border: 1px solid var(--border);
            padding: 8px 16px;
            border-radius: 999px;
            font-size: 13px;
        }
        .stats-pill strong {
            color: var(--accent);
            font-weight: 700;
        }
        .badge-verified {
            background: rgba(34, 197, 94, 0.15);
            color: #22C55E;
            border: 1px solid rgba(34, 197, 94, 0.3);
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }

        /* Controls */
        .controls-bar {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 16px 20px;
            margin-bottom: 28px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .search-row {
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
        }
        .search-input {
            flex: 1;
            min-width: 260px;
            background: #090B10;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px 16px;
            color: var(--text-main);
            font-size: 14px;
            outline: none;
            transition: all 0.2s;
        }
        .search-input:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-glow);
        }
        .mode-toggles {
            display: flex;
            background: #090B10;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 3px;
            gap: 4px;
        }
        .mode-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 6px 14px;
            border-radius: 7px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .mode-btn.active {
            background: var(--accent);
            color: #090B10;
        }
        .category-filters {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .filter-btn {
            background: #090B10;
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .filter-btn:hover {
            border-color: var(--text-muted);
            color: var(--text-main);
        }
        .filter-btn.active {
            background: rgba(56, 189, 248, 0.12);
            border-color: var(--accent);
            color: var(--accent);
        }

        /* Grid */
        .sponsors-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 20px;
        }
        .sponsor-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s, border-color 0.2s;
        }
        .sponsor-card:hover {
            transform: translateY(-2px);
            border-color: rgba(56, 189, 248, 0.4);
        }

        /* Previews */
        .preview-box {
            position: relative;
            height: 160px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px 20px;
            transition: background 0.25s;
        }
        .preview-box.view-split {
            display: grid;
            grid-template-columns: 1fr 1fr;
            padding: 0;
            height: 170px;
        }
        .split-pane {
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 16px 12px;
            position: relative;
        }
        .split-pane.light {
            background: var(--jersey-light);
            border-right: 1px solid rgba(0, 0, 0, 0.12);
        }
        .split-pane.dark {
            background: var(--jersey-dark);
        }
        .pane-label {
            position: absolute;
            top: 8px;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            padding: 2px 6px;
            border-radius: 4px;
        }
        .split-pane.light .pane-label {
            left: 8px;
            background: rgba(0, 0, 0, 0.08);
            color: #555;
        }
        .split-pane.dark .pane-label {
            right: 8px;
            background: rgba(255, 255, 255, 0.08);
            color: #aaa;
        }
        .logo-img {
            max-width: 90%;
            max-height: 85px;
            object-fit: contain;
            filter: drop-shadow(0 2px 6px rgba(0,0,0,0.15));
            transition: transform 0.2s;
        }
        .logo-img:hover {
            transform: scale(1.05);
        }

        /* Info Section */
        .card-info {
            padding: 16px 18px;
            border-top: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            gap: 10px;
            background: #0E121A;
            flex: 1;
        }
        .card-title-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .brand-name {
            font-size: 16px;
            font-weight: 700;
            color: #FFFFFF;
        }
        .brand-key {
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            padding: 2px 6px;
            border-radius: 5px;
        }
        .category-tag {
            align-self: flex-start;
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 6px;
            background: rgba(56, 189, 248, 0.1);
            color: var(--accent);
            border: 1px solid rgba(56, 189, 248, 0.2);
        }
        .brand-desc {
            font-size: 12px;
            color: #8E9BAE;
            line-height: 1.4;
        }

        /* Footer */
        .footer {
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid var(--border);
            text-align: center;
            color: var(--text-muted);
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <div class="header-left">
                <h1>Dynamic Kit & Sponsor Mod</h1>
                <p>Premier Real-World Sponsor Logo Library — Authentic Master League Sponsorships</p>
            </div>
            <div class="stats-pill">
                <span><strong>177</strong> Sponsors</span>
                <span>•</span>
                <span><strong>354</strong> Logos (Color + White Silhouettes)</span>
                <span>•</span>
                <span class="badge-verified">4x Supersampled</span>
            </div>
        </header>

        <!-- Controls -->
        <div class="controls-bar">
            <div class="search-row">
                <input type="text" id="searchInput" class="search-input" placeholder="Search sponsor, industry, or key (e.g. Spotify, Chelsea, Drake, Apple, Emirates)...">
                <div class="mode-toggles">
                    <button class="mode-btn active" data-mode="split">Split View (Both)</button>
                    <button class="mode-btn" data-mode="light">Light Kits (Color)</button>
                    <button class="mode-btn" data-mode="dark">Dark Kits (White)</button>
                </div>
            </div>
            <div class="category-filters" id="categoryFilters">
                <button class="filter-btn active" data-category="all">All Categories (177)</button>
                <button class="filter-btn" data-category="Iconic Emblems & Specials">Iconic Emblems & Specials (30)</button>
                <button class="filter-btn" data-category="Airlines & Tourism">Airlines & Tourism (16)</button>
                <button class="filter-btn" data-category="Betting & Gaming">Betting & Gaming (20)</button>
                <button class="filter-btn" data-category="Banking & Finance">Banking & Finance (20)</button>
                <button class="filter-btn" data-category="Tech & Streaming">Tech & Streaming (22)</button>
                <button class="filter-btn" data-category="Telecom & Mobile">Telecom & Mobile (12)</button>
                <button class="filter-btn" data-category="Automotive & Tires">Automotive & Tires (18)</button>
                <button class="filter-btn" data-category="Crypto & Web3">Crypto & Web3 (11)</button>
                <button class="filter-btn" data-category="Energy & Industry">Energy & Industry (13)</button>
                <button class="filter-btn" data-category="Insurance & Healthcare">Insurance & Healthcare (8)</button>
                <button class="filter-btn" data-category="Beverages & Lifestyle">Beverages & Lifestyle (7)</button>
            </div>
        </div>

        <!-- Sponsors Grid -->
        <div class="sponsors-grid" id="sponsorsGrid">
            <!-- Cards rendered dynamically -->
        </div>

        <!-- Footer -->
        <footer class="footer">
            <p>Master League Dynamic Kit & Sponsor Mod for PES 2021 / SP Football Life 2027 (FL26/FL27). All sponsor logos conform strictly to PES chest printing UV specifications with automatic WCAG contrast inversion.</p>
        </footer>
    </div>

    <script>
        const sponsors = __SPONSORS_JSON__;
        let currentMode = 'split';
        let currentCategory = 'all';
        let searchKeyword = '';

        const grid = document.getElementById('sponsorsGrid');
        const searchInput = document.getElementById('searchInput');
        const categoryButtons = document.querySelectorAll('.filter-btn');
        const modeButtons = document.querySelectorAll('.mode-btn');

        function renderCards() {
            const filtered = sponsors.filter(s => {
                const matchesCat = currentCategory === 'all' || s.category === currentCategory;
                const matchesSearch = !searchKeyword || 
                    s.name.toLowerCase().includes(searchKeyword) ||
                    s.key.toLowerCase().includes(searchKeyword) ||
                    s.category.toLowerCase().includes(searchKeyword) ||
                    s.desc.toLowerCase().includes(searchKeyword);
                return matchesCat && matchesSearch;
            });

            grid.innerHTML = filtered.map(s => {
                let previewHtml = '';
                if (currentMode === 'split') {
                    previewHtml = `
                        <div class="preview-box view-split">
                            <div class="split-pane light">
                                <span class="pane-label">Light Kit</span>
                                <img src="content/KitGenerator/logos/${s.key}.png" alt="${s.name}" class="logo-img" loading="lazy">
                            </div>
                            <div class="split-pane dark">
                                <span class="pane-label">Dark Kit</span>
                                <img src="content/KitGenerator/logos/${s.key}_white.png" alt="${s.name} White" class="logo-img" loading="lazy">
                            </div>
                        </div>
                    `;
                } else if (currentMode === 'light') {
                    previewHtml = `
                        <div class="preview-box" style="background: var(--jersey-light);">
                            <img src="content/KitGenerator/logos/${s.key}.png" alt="${s.name}" class="logo-img" loading="lazy">
                        </div>
                    `;
                } else {
                    previewHtml = `
                        <div class="preview-box" style="background: var(--jersey-dark);">
                            <img src="content/KitGenerator/logos/${s.key}_white.png" alt="${s.name} White" class="logo-img" loading="lazy">
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
                            <span class="category-tag">${s.category}</span>
                            <p class="brand-desc">${s.desc}</p>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Search listener
        searchInput.addEventListener('input', e => {
            searchKeyword = e.target.value.trim().toLowerCase();
            renderCards();
        });

        // Category filter listeners
        categoryButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                categoryButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentCategory = btn.getAttribute('data-category');
                renderCards();
            });
        });

        // Mode toggle listeners
        modeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                modeButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentMode = btn.getAttribute('data-mode');
                renderCards();
            });
        });

        // Initial render
        renderCards();
    </script>
</body>
</html>
"""

def generate_showcase():
    sponsors_data = [
        {"key": s[0], "name": s[1], "category": s[2], "desc": s[3]}
        for s in SPONSORS_META
    ]
    html = HTML_TEMPLATE.replace("__SPONSORS_JSON__", json.dumps(sponsors_data))
    out_file = ROOT / "sponsors_showcase.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"Generated showcase HTML for {len(sponsors_data)} sponsors -> {out_file}")

if __name__ == '__main__':
    generate_showcase()
