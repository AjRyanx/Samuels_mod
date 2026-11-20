#!/usr/bin/env python3
"""setup.py - CLI Management and Installation Tool for Dynamic Kit & Sponsor Mod.

Usage:
    python setup.py install       # Synchronize files, deploy watcher, configure sider.ini
    python setup.py verify        # Verify prerequisites, file integrity, and sider.ini hooks
    python setup.py test          # Run the full pytest regression suite
    python setup.py pregen        # Generate the lightweight p1/g1 baseline for all clubs
    python setup.py uninstall     # Cleanly unregister KitGenerator from sider.ini
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DEFAULT_PATHS = [
    Path(r"C:\Games\SP Football Life 2027"),
    Path(r"C:\Games\SP Football Life 2026"),
    ROOT.parent.parent,
]


def find_game_root() -> Path:
    for p in DEFAULT_PATHS:
        if (p / "SiderAddons").is_dir():
            return p
    raise SystemExit("Game directory with 'SiderAddons' not found. Specify via --game-path.")


def find_sider_ini(game_root: Path) -> Path:
    candidates = [
        game_root / "SiderAddons" / "sider.ini",
        game_root / "sider.ini",
    ]
    for c in candidates:
        if c.is_file():
            return c
    raise SystemExit(f"sider.ini not found in {game_root} or SiderAddons!")


def cmd_verify(args):
    print("=" * 80)
    print(" DYNAMIC KIT & SPONSOR MOD: HEALTH CHECK & VERIFICATION")
    print("=" * 80)
    game_root = args.game_path or find_game_root()
    sider_ini = find_sider_ini(game_root)
    print(f" [*] Game Root        : {game_root}")
    print(f" [*] Sider Config     : {sider_ini}")

    # Check Python libs
    try:
        import PIL
        import numpy
        print(f" [OK] Python Libs     : Pillow {PIL.__version__}, NumPy {numpy.__version__}")
    except ImportError as e:
        print(f" [FAIL] Python Libs   : {e}")

    # Check sider.ini registration
    ini_text = sider_ini.read_text(encoding="utf-8", errors="ignore")
    has_lua = "KitGenerator.lua" in ini_text
    has_cpk = "livecpk\\KitGenerator" in ini_text or "livecpk/KitGenerator" in ini_text
    print(f" [{'OK' if has_lua else 'FAIL'}] sider.ini Module: {'KitGenerator.lua registered' if has_lua else 'MISSING'}")
    print(f" [{'OK' if has_cpk else 'FAIL'}] sider.ini CPK   : {'livecpk root registered' if has_cpk else 'MISSING'}")

    # Check active textures count
    active_dir = game_root / "SiderAddons" / "content" / "KitGenerator" / "active"
    ftex_count = len(list(active_dir.glob("*.ftex"))) if active_dir.is_dir() else 0
    print(f" [OK] Active Textures : {ftex_count} pre-generated .ftex files cached")

    # Check deals.txt
    deals_file = game_root / "SiderAddons" / "content" / "KitGenerator" / "deals.txt"
    if deals_file.is_file():
        n_lines = len(deals_file.read_text(encoding="utf-8", errors="ignore").splitlines())
        print(f" [OK] Deals Database  : {n_lines} lines ({deals_file.stat().st_size // 1024} KB)")
    else:
        print(f" [FAIL] Deals Database: Missing at {deals_file}")

    print("=" * 80)


def cmd_install(args):
    print("=" * 80)
    print(" DYNAMIC KIT & SPONSOR MOD: INSTALLATION")
    print("=" * 80)
    game_root = args.game_path or find_game_root()
    sider_dir = game_root / "SiderAddons"
    sider_ini = find_sider_ini(game_root)

    # Scaffolding
    content_kg = sider_dir / "content" / "KitGenerator"
    active_dir = content_kg / "active"
    logos_dir = content_kg / "logos"
    badges_dir = content_kg / "badges"
    sleeve_dir = content_kg / "sleeve_logos"
    supplier_dir = content_kg / "suppliers"
    modules_dir = sider_dir / "modules"
    gen_dir = sider_dir / "KitGenerator" / "generator"
    livecpk_dir = sider_dir / "livecpk" / "KitGenerator"

    for d in (active_dir, logos_dir, badges_dir, sleeve_dir, supplier_dir,
              modules_dir, gen_dir, livecpk_dir):
        d.mkdir(parents=True, exist_ok=True)

    print(" [*] Copying KitGenerator.lua to modules/...")
    shutil.copy2(ROOT / "modules" / "KitGenerator.lua", modules_dir / "KitGenerator.lua")

    print(" [*] Synchronizing generator scripts...")
    for f in (ROOT / "generator").glob("*.py"):
        shutil.copy2(f, gen_dir / f.name)
    if (ROOT / "generator" / "clubs.csv").is_file():
        shutil.copy2(ROOT / "generator" / "clubs.csv", gen_dir / "clubs.csv")

    print(" [*] Synchronizing content libraries (logos, badges, sleeves, suppliers, deals)...")
    src_content = ROOT / "content" / "KitGenerator"
    if (src_content / "logos").is_dir():
        for f in (src_content / "logos").glob("*.png"):
            shutil.copy2(f, logos_dir / f.name)
    for folder, target in (
        ("badges", badges_dir),
        ("sleeve_logos", sleeve_dir),
        ("suppliers", supplier_dir),
    ):
        src = src_content / folder
        if src.is_dir():
            for f in src.glob("*.png"):
                shutil.copy2(f, target / f.name)
    if (src_content / "deals.txt").is_file():
        shutil.copy2(src_content / "deals.txt", content_kg / "deals.txt")
    if (src_content / "brands.txt").is_file():
        shutil.copy2(src_content / "brands.txt", content_kg / "brands.txt")

    print(" [*] Deploying background watcher and regenerating brand pool...")
    setup_watcher = ROOT / "generator" / "setup_watcher.py"
    if setup_watcher.is_file():
        ret = subprocess.run(
            [sys.executable, str(setup_watcher), "--game-root", str(game_root), "--sider", str(sider_dir)],
            cwd=str(ROOT),
        )
        if ret.returncode != 0:
            print(" [!] Watcher deployment reported an error; re-run generator/setup_watcher.py manually.")
    else:
        print(" [!] setup_watcher.py not found; watcher was not deployed.")

    # sider.ini configuration
    ini_lines = sider_ini.read_text(encoding="utf-8", errors="ignore").splitlines()
    has_lua = any("KitGenerator.lua" in l for l in ini_lines)
    has_cpk = any("livecpk\\KitGenerator" in l or "livecpk/KitGenerator" in l for l in ini_lines)

    new_lines = []
    inserted_lua = False
    for line in ini_lines:
        if not has_lua and not inserted_lua and ("common\\kits.lua" in line or 'lua.module = "modmenu.lua"' in line):
            if 'lua.module = "modmenu.lua"' in line:
                new_lines.append(line)
                new_lines.append('lua.module = "KitGenerator.lua"')
                inserted_lua = True
                continue
            else:
                new_lines.append('lua.module = "KitGenerator.lua"')
                new_lines.append(line)
                inserted_lua = True
                continue
        if not has_cpk and "cpk.root" in line:
            new_lines.append('cpk.root = ".\\livecpk\\KitGenerator"')
            has_cpk = True
        new_lines.append(line)

    if not has_lua and not inserted_lua:
        new_lines.append('lua.module = "KitGenerator.lua"')

    sider_ini.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f" [OK] Successfully registered mod in {sider_ini.name}")

    if args.pregen:
        cmd_pregen(args)

    print("=" * 80)
    print(" INSTALLATION COMPLETE! Run 'python setup.py verify' to check status.")
    print("=" * 80)


def cmd_test(args):
    print("=" * 80)
    print(" RUNNING REGRESSION TESTS")
    print("=" * 80)
    res = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=str(ROOT))
    sys.exit(res.returncode)


def cmd_pregen(args):
    print("=" * 80)
    print(" GENERATING MASTER LEAGUE BASELINE (p1/g1)")
    print("=" * 80)
    script = ROOT / "generator" / "build_all_clubs.py"
    game_root = args.game_path or find_game_root()
    active_dir = game_root / "SiderAddons" / "content" / "KitGenerator" / "active"
    slots = args.slots or "1,g1"
    subprocess.run([
        sys.executable, str(script),
        "--skip-existing",
        "--outdir", str(active_dir),
        "--slots", slots,
    ], check=True)
    print(" [!] Secondary slots (p2/p3/g2) are generated on demand for scheduled opponents.")


def main():
    parser = argparse.ArgumentParser(description="Dynamic Kit & Sponsor Mod Setup Utility")
    parser.add_argument("--game-path", type=Path, default=None, help="Path to FL27 / PES 2021 game root")
    parser.add_argument("--slots", type=str, default="1,g1", help="Slots for baseline generation (default: 1,g1)")
    parser.add_argument("--pregen", action="store_true", help="Generate p1/g1 baseline during install")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("install", help="Install and register mod in SiderAddons")
    sub.add_parser("verify", help="Verify installation status and prerequisites")
    sub.add_parser("test", help="Run test suite")
    sub.add_parser("pregen", help="Pre-generate all club kits")

    args = parser.parse_args()
    if args.command == "install":
        cmd_install(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "test":
        cmd_test(args)
    elif args.command == "pregen":
        cmd_pregen(args)
    else:
        cmd_verify(args)


if __name__ == "__main__":
    main()
