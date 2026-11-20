# AGENTS.md - Development & Architecture Guidelines

## Project Overview
This repository contains the **Dynamic Kit & Sponsor Mod** for **PES 2021 / SP Football Life 2027 (FL26/FL27)** running under **Sider 7.3.3+**.
The mod allows Master League careers to sign real-world dynamic sponsors (Spotify, Fly Emirates, etc.), earn sponsorship budget income, and generate custom branded kit sets dynamically.

---

## CRITICAL ARCHITECTURAL RULE: Master League-Only Scope

> [!IMPORTANT]
> **Dynamic kits MUST ONLY apply within Master League (Career Mode).**
> **They MUST NEVER be displayed or active in Exhibition (Friendlies), Database, Kick-off, or Edit Mode.**
> In Exhibition and all non-career modes, teams MUST wear their **original, authentic licensed kits** (e.g., Spotify for Barcelona, Emirates for Arsenal).
> **DO NOT UNDO THIS DESIGN.**

---

### How the Mode Separation Works

1. **Static Kitserver GDB Files (`SiderAddons/content/kits/...`):**
   - The `.ftex` files in `SiderAddons/content/kits/<League>/<Team>/p<slot>/u<id>p<slot>.ftex` **MUST REMAIN AUTHENTIC**.
   - Original backups are preserved in `u<id>p<slot>.ftex.orig.bak`.
   - **DO NOT** have `build_kit.py` or any watcher script overwrite these files on disk. Doing so corrupts Exhibition and offline friendlies with dynamic sponsor logos.

2. **Dynamic Runtime Interception via Sider (`KitGenerator.lua`):**
   - In `sider.ini`, `KitGenerator.lua` is loaded **before** `common\kits.lua`.
   - `KitGenerator.lua` hooks `livecpk_make_key` and `livecpk_get_filepath`.
   - When the game requests kit textures (`k<id>p<slot>.ftex` or `u<id>p<slot>.ftex`):
     - **In Exhibition / Friendly (`ctx.tournament_id == 65535` or `not is_in_ml(ctx)`):**
       `KitGenerator.lua` yields (`return nil`). Sider falls through to Kitserver (`kits.lua`), which loads the authentic licensed kit from `content/kits/...`.
     - **In Master League (`ctx.tournament_id ~= 65535` and `is_in_ml(ctx)`):**
       `KitGenerator.lua` intercepts the request and returns the dynamic kit texture from `content/KitGenerator/active/u<id>p<slot>.ftex`.

3. **Master League State Detection:**
   - `is_in_ml(ctx)` verifies:
     - `STATE.in_edit_mode == false`
     - `ctx.tournament_id ~= 65535` (Exhibition match friendly flag)
     - UI flow state (`common\script\flow\ML\...` vs `\Exhibition\`, `\Top\`, `\Edit\`)
     - Active Master League calendar date in memory (`game_date()`).

4. **Kit Deployment Target:**
   - Generated kits are deployed strictly to:
     `SiderAddons/content/KitGenerator/active/u<id>p<slot>.ftex`
   - Mod menu previews and 2D textures read from this folder.
   - Sider serves this active folder during Master League matches and Master League squad menus.

5. **User Team Dynamic Kits (Master League):**
   - The user's managed team in Master League receives a dynamic kit regardless of whether they have a sponsor or not.
   - If no sponsor deal is signed (or an existing deal has expired), the club wears a **fresh sponsorless dynamic kit** until a new sponsor is signed.
   - Once a sponsor deal is signed in the Sponsor Office, their dynamic kit is generated with that sponsor's logo and branding.
   - In Exhibition (Friendlies), Database, Kick-off, and Edit Mode, teams MUST ALWAYS wear their **original, authentic licensed kits** (e.g. Spotify for Barcelona, Emirates for Arsenal). Dynamic kits must NEVER be active outside Master League.

---

## File Locations & Sync
- Master mod source: `mods/Dynamic_Kit_and_Sponsor_mod_pes21/`
- Game runtime modules: `SiderAddons/modules/KitGenerator.lua`
- Generator runtime: `SiderAddons/KitGenerator/generator/`
- Deployed content: `SiderAddons/content/KitGenerator/`
- Always keep `mods/Dynamic_Kit_and_Sponsor_mod_pes21/` and `SiderAddons/` in strict sync when updating code.
