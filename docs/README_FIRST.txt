KIT GENERATOR MOD for Football Life 2027  -  version 0.7
========================================================

WHAT THIS PACKAGE IS
  The sponsor / kit mod for Master League: the Sponsor Office (Sider Mod Menu page, or a
  classic text overlay fallback) offers sponsorship deals in the pre-season, and signing one
  rebuilds your club's home/away/third kits with the sponsor's logo through a background
  Python watcher.  The club you manage is detected automatically, so a career can be started
  with ANY team (see "YOUR CLUB IS AUTO-DETECTED" below).

WHAT WORKS NOW
  - kit_gen.py        seeded kit designs + colour-recognisable check, preview sheet (PNG only)
  - ftex_io.py        real FL27 .ftex read/write. Verified against TheGaffer_Chelsea_FC:
                      2048x2048 BC3/DXT5, 12 mips, zlib chunks (NOT Oodle). Commands:
                      inspect, extract (-> dds/png), build (png -> ftex), repack (replace a kit).
  - kit_regions.py    the real PES 2021 UV atlas islands (shirt front/back, sleeves, shorts,
                      socks, collar) + logo anchors. Taken from the PES Master Kit Creator's
                      own mask images (generator/uv_masks/), which is the tool that emits
                      game-valid kit textures - not guessed.
  - kit_render.py     generated design -> 2048x2048 UV atlas PNG. Draws the same 2D design as
                      the preview into a shirt-local tile, then maps it onto the front island
                      (upright) and back island (rotated 180 degrees, which is what the game
                      does), and stamps the sponsor logo on the chest.
  - club_resolver.py  team id -> club row (name, colours, tier) for ANY club, from the live
                      game colours in club.txt, the game's own kit map/config.txt, or a
                      deterministic palette. This is what lets the generator build a kit for a
                      club that is not in clubs.csv.
  - kit_diag.py       diagnostic region-map kit (each body part a flat colour + label), used to
                      verify the UV mapping in one in-game screenshot.
  - logomaker.py      the invented sponsor logos (colour + white versions)  -> content/KitGenerator/logos
  - deals.py          5 offers per club per season -> deals.txt, career.txt (stopgap career ID)
  - watch_signed.py   background watcher: a signed deal -> regenerate that season's kits with the
                      sponsor's logo and install them into livecpk (see below)
  - setup_watcher.py  one-time deploy: copies the generator into the game, writes watcher.cmd and
                      generates content/KitGenerator/brands.txt (the brand pool)
  - KitGenerator.lua  Sponsor Office page (Sider Mod Menu, or classic text overlay fallback),
                      auto-detected club, sign, counter-offers (same answer every reload),
                      PENDING/DONE ledger; starts the watcher automatically at load
  - KGProbe.lua       read-only probe: mode IDs, custom-club kit file requests, sandbox facts
  - activate_season.py   swaps a staged season into livecpk (deletes only our own folder)

WHAT IS LOCKED (needs your in-game results)
  - budget payments            (needs both addresses confirmed by read-only logging)
  - Master League / Become a Legend detection (F8 manual toggle for now)


REAL KIT INJECTION (working pipeline)
  generated design -> atlas PNG -> game .ftex -> livecpk override:
      python generator/kit_render.py 102 2027 <outdir>          # club 102, season 2027
      python generator/ftex_io.py repack <real_kit.ftex> <atlas.png> <out.ftex>
      copy <out.ftex> over
        SiderAddons/livecpk/KitGenerator/Asset/model/character/uniform/texture/#windx11/u0102p1.ftex
  The game asks for exactly u0102p1.ftex (+ u0102p1_srm.ftex, u0102g1.ftex) for team 102, so
  u0102p1.ftex is the only file that needs overriding for the outfield kit.

SPONSOR DEALS -> AUTO KIT REBUILD (the watcher)
  Sign a deal in the pre-season (Jun-Aug) and the mod regenerates that season's home/away/third
  kits with the sponsor's logo and a fresh design, then installs them, so they show at your next
  match.  How it fits together:

    KitGenerator.lua (sign_offer)   appends one line to content/KitGenerator/kit_request.txt
                                    offer_id|club_id|season|brand|tier|timestamp
    watch_signed.py (watcher)       polls that file, builds the kits, installs into livecpk
    KitGenerator.lua (init)         launches the watcher at game load, and records the game's
                                    pid so the watcher shuts itself down when the game closes

  ONE-TIME SETUP (do this once, and again after moving the mod or changing Python):
      python generator/setup_watcher.py
    This copies the generator into the game (SiderAddons/KitGenerator/generator) and writes
    SiderAddons/content/KitGenerator/watcher.cmd, which KitGenerator.lua runs at load.  It uses
    pythonw, so no console window appears.  Only ONE watcher runs at a time (loopback port lock).

  To try it without the game:
      python generator/watch_signed.py --sider "<SiderAddons>" --once
  Watch what it did in content/KitGenerator/watcher.log; processed offers are remembered in
  watcher_state.txt so a deal is only ever built once.

  January is deliberately NOT a signing month: a season's kits can only be generated in the
  pre-season, so a mid-season deal can never silently swap the kits you are already wearing.

YOUR CLUB IS AUTO-DETECTED (v0.7)
  You no longer set CFG.MANAGED_CLUB.  Start a Master League with any team and the mod works
  out which club is yours.  The layers, most authoritative first:
    1. CFG.MANAGED_CLUB (a number)  a manual override in KitGenerator.lua always wins
    2. club.txt                     the club detected in an earlier session
    3. the career learner           the team that turns up in EVERY career match (your club
                                    plays them all; no other club does).  Exhibition games
                                    (tournament id 65535) are ignored so friendlies cannot
                                    muddy the vote.  A stale club.txt is replaced after a
                                    couple of matches.
    4. edit mode                    the team being edited, only when nothing else is found
  The club's real kit colours are read live from the game (ctx.kits.get) and written to
  content/KitGenerator/club.txt, which the Python generator reads to paint the kits in the
  club's own colours.  If a club is not in clubs.csv, offers are synthesised in Lua from the
  brand pool (content/KitGenerator/brands.txt, written by setup_watcher.py) and the generator
  resolves the club through club_resolver.py (club.txt -> the game's kit map/config.txt -> a
  deterministic palette).
  The Sponsor Office shows a "Club" card (name, team id, how it was detected, matches seen) and
  lets you type a team id by hand, plus "Back to auto-detect".

BONUSES, TERMINATION AND USING ONE HALF ON ITS OWN
  * Signing bonus.  An offer's bonus % is a one-off payment on top of the yearly value, paid at
    signing and recorded under its own ledger key so it is never paid twice.  The office shows
    the exact amount (e.g. "Signing bonus: 10% (EUR 10.0M)").
  * Termination clause.  While a deal runs, "Terminate contract" (office button, or [T] in the
    classic overlay, pressed twice to confirm) ends it at once: a buyout of CFG.TERMINATION_PCT
    (default 50%) of the value still to run is taken from your budget, the contract is released
    (offers reopen) and the logo comes off the kit immediately.  When a deal simply runs out, the
    same release + clean kit happens automatically.
  * Two independent halves.  In KitGenerator.lua:
        CFG.ENABLE_KITS        = true   -- the kit half (rebuilds kits via the Python watcher)
        CFG.ENABLE_SPONSORSHIP = true   -- the deal half (offers, signing, budget money)
    Kits only        -> fresh kit each season, no office and no money; no offers appear.
    Sponsorship only -> the office and the money, but the kits are left exactly as they are
                        (no watcher, no Python, no livecpk needed).
    Both (default)   -> the full mod.
    The load line in sider.log states which halves are on, e.g.
        loaded v0.7 (kits ON, sponsorship ON, budget crediting ON)
    Truly standalone use also works: the generator (build_kit.py / setup_watcher.py) rebuilds
    kits with no Lua module at all, and the Lua module credits money with no Python at all.

EXECUTIVE UI (v0.6)
  The Sponsor Office page and the Sider Mod Menu chrome were restyled to a clean, monochrome
  "executive" dark theme.
  * Sponsor Office (KitGenerator.lua).  The page is now card based:
        - Mode card: Master League + transfer-window switches side by side.
        - Active Sponsorship card: sponsor badge, brand, tier label
          ("Tier 1 - MAIN KIT SPONSOR"), a 3-column financial summary, an ASCII contract
          progress bar ("[====      ]  40%"), a status line, a primary
          "Credit this season's money now" button and an outlined "Terminate contract".
        - Sponsor Offers cards: badge, brand, tier, per-year value, length, bonus, with
          "Sign deal" (primary) and "Counter offer" (outlined) buttons.
      Text styles are monochrome (white / #cbd5e1) with no colour accents.  The page
      description reads "ACTIVE SPONSORSHIP CONTRACT & MANAGEMENT - MODULE V2.1".
  * Sider Mod Menu (modules\modmenu.lua + modules\modmenu\modmenu.dll).
        - The window chrome (title bar, sidebar, panels, buttons) is drawn by the compiled
          modmenu.dll; it has NO theme/config surface.  Its colours are float constants in
          .rdata, so they were retargeted directly to the monochrome set:
              accent / primary button fill  #e63946 -> #cbd5e1
              primary button label          #ffffff -> #0f1115
              button / panel fills          blue-grey -> charcoal (#12151b / #171a21 / #1f232c)
          Body text (#eceef4) and the semantic warn/err colours were left untouched, so
          nothing becomes unreadable.
        - modmenu.lua footer is now "F1  Toggle  .  Esc  Close" and the module icon map was
          widened (sponsor/badge/sleeve -> tag, kit/shirt -> palette, etc.).
        - modmenu.ini opacity = 1.0 gives solid, opaque panels (no game bleed-through).
  HOW TO REVERT THE MODMENU PALETTE
        The DLL was backed up as  modules\modmenu\modmenu.dll.bak-<timestamp>.
        Either restore that file, or run
            python "%LOCALAPPDATA%\Temp\opencode\patch_modmenu_palette.py" --revert
        The lua/ini tweaks revert from  modmenu.lua.bak-<stamp> / modmenu.ini.bak-<stamp>.

BEFORE ANYTHING: back up your save folder and your Sider folder.

TEST SESSION (do in this order; stop at the first failure and send me the log)
  A. Install the PROBE only
     1. Copy modules/KGProbe.lua into your Sider "modules" folder.
     2. Add as the LAST line in sider.ini:   lua.module = "KGProbe.lua"
     3. Start through Sider. Open sider.log; look for errors. Open kgprobe.log in the Sider folder.
        It must contain a SANDBOX line: send me it (tells us if pcall, require, os.execute exist).
  B. Label and play (press F9 to cycle the label before each match: ML, BAL, EXH, CUSTOM_ML)
     - 2 matches in Master League with a normal club, 2 in Become a Legend, 2 in Exhibition,
       2 in Master League with ONE OF YOUR MOD STUDIO CLUB (label CUSTOM_ML).
     - Quit to the menu between the two matches of each pair.
     - Send me kgprobe.log. It shows team IDs, tournament IDs, and whether kit files are
       requested again each match. For a custom club it shows whether ANY kit file is requested.
  C. Two-career test: start two Master League careers with the same club, load each once,
     send me the probe log from both.
  D. Real kit file (DONE - format cracked):   python generator/ftex_io.py "path\to\kit.ftex"
     prints the decoded header and every mip. Round-trip a kit texture:
       python generator/ftex_io.py extract "kit.ftex" out.png
       python generator/ftex_io.py repack  "kit.ftex" out.png new.ftex   # PNG -> game-ready .ftex
  E. Sider Mod Menu test (only if you use it): press F1 in a Master League menu. In modmenu.log
     look for "captured swapchain" and "game-thread hooks".

THEN INSTALL THE SPONSOR OFFICE (only after A and B worked)
  1. Copy modules/KitGenerator.lua and the content/KitGenerator folder into your Sider folder.
  2. Run  python generator/setup_watcher.py  once (deploys the generator + brands.txt + watcher.cmd).
     The club is auto-detected - no CFG.MANAGED_CLUB edit needed.  (Set CFG.MANAGED_CLUB = <team id>
     only if you want to pin it by hand.)
  3. sider.ini (the Mod Menu, if used, must be the FIRST lua.module):
        luajit.ext.enabled = 1
        lua.module = "KitGenerator.lua"
     Only add overlay.* lines if you use the classic text overlay, and check your other modules first.
  4. Press F8 in Master League to switch the office on by hand, then open the Sponsor Office
     page (Mod Menu F1) or press F7 (classic overlay).
  Payments remain OFF. Do not turn them on until addresses are confirmed (see the plan doc).

UNINSTALL: delete the lua.module lines you added. The mod never edits the game's own files,
your save, or your Mod Studio project. It only writes inside content/KitGenerator
(deals, signed.txt, ledger.txt) and kgprobe.log.

EDIT YOUR CLUBS: generator/clubs.csv  (team_id,name,primary,secondary,accent,tier)
REGENERATE:  python generator/kit_gen.py 2027 2028 2029   (preview sheet)
             python generator/deals.py 2027               (offers)
RUN TESTS:   pip install lupa pillow ; python tests/parity_test.py ; python tests/smoke_test.py ;
             python tests/resolver_test.py
