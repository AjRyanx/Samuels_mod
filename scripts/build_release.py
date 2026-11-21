#!/usr/bin/env python3
"""Build a clean, hash-manifested alpha/beta release ZIP.

Run from anywhere:

    python scripts/build_release.py

The script stages only distributable source/runtime files from this repository,
writes MANIFEST.sha256, and produces:

    dist/DynamicKitSponsorMod_v<version>.zip
    dist/DynamicKitSponsorMod_v<version>.zip.sha256

Live game state, generated kits, logs, personal career IDs, backups and caches
are deliberately excluded.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_JSON = ROOT / "release.json"
DIST = ROOT / "dist"

ROOT_FILES = (
    ".gitattributes",
    ".gitignore",
    "AGENTS.md",
    "LICENSE",
    "README.md",
    "RELEASE_NOTES.md",
    "release.json",
    "requirements.txt",
    "install.bat",
    "install.ps1",
    "setup.py",
)

# Top-level directory -> (file globs, subdirectories copied recursively).
TREE_RULES = {
    "modules": (("*.lua",), ()),
    "generator": (("*.py", "*.csv"), ("uv_masks", "sleeve_logos")),
    "content/KitGenerator": (
        ("deals.txt",),
        ("logos", "badges", "sleeve_logos", "suppliers"),
    ),
    "livecpk/KitGenerator": (("*.txt",), ()),
    "docs": (("*",), ()),
    "tests": (("*.py",), ()),
    "scripts": (("*.py",), ()),
}

SCAFFOLD_FILES = ("content/KitGenerator/staging/.gitkeep",)

REQUIRED_FILES = (
    "install.bat",
    "install.ps1",
    "setup.py",
    "modules/KitGenerator.lua",
    "generator/setup_watcher.py",
    "generator/watch_signed.py",
    "generator/build_all_clubs.py",
    "generator/kit_signature.py",
    "generator/build_kit.py",
    "generator/kit_render.py",
    "generator/uv_masks/body_erase.png",
    "content/KitGenerator/deals.txt",
    "content/KitGenerator/logos/spotify.png",
    "content/KitGenerator/badges/101.png",
    "content/KitGenerator/sleeve_logos/visit_rwanda.png",
    "content/KitGenerator/suppliers/nike.png",
    "livecpk/KitGenerator/PLACEHOLDER.txt",
    "RELEASE_NOTES.md",
    "release.json",
)

LIVE_STATE_NAMES = {
    "club.txt",
    "active_deal.txt",
    "paid.txt",
    "signed.txt",
    "ledger.txt",
    "watcher_state.txt",
    "kit_request.txt",
    "game.pid",
    "watcher.cmd",
    "watcher.log",
    "career.txt",
    "kgprobe.log",
}


def rel_str(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def is_excluded(rel: str) -> bool:
    """Return True for anything that must never appear in a release ZIP."""
    parts = rel.split("/")
    if any(p in {".git", ".pytest_cache", "__pycache__", "visual_audit", "showcase_renders"} for p in parts):
        return True
    if rel.endswith((".pyc", ".pyo", ".bak", ".orig", ".ftex", ".dds", ".log", ".pid")):
        return True
    if parts[-1] in LIVE_STATE_NAMES:
        return True
    if parts[-1] in {"clubs.csv.bak", "ftex_probe_report.json", "logos_sheet.png"}:
        return True
    if len(parts) >= 2 and parts[0] == "content" and parts[1] == "KitGenerator":
        if "active" in parts:
            return True
        if "staging" in parts and rel != "content/KitGenerator/staging/.gitkeep":
            return True
    return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stage_file(src: Path, dst: Path, rel: str) -> None:
    if is_excluded(rel):
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def stage_tree(stage: Path) -> None:
    for name in ROOT_FILES:
        src = ROOT / name
        if not src.is_file():
            raise FileNotFoundError(f"Required release root file missing: {src}")
        stage_file(src, stage / name, name)

    for tree_rel, (globs, subdirs) in TREE_RULES.items():
        src_root = ROOT / tree_rel
        if not src_root.is_dir():
            raise FileNotFoundError(f"Required release directory missing: {src_root}")
        for pattern in globs:
            for src in sorted(src_root.glob(pattern)):
                if not src.is_file():
                    continue
                rel = f"{tree_rel}/{src.name}"
                stage_file(src, stage / rel, rel)
        for subdir in subdirs:
            src_dir = src_root / subdir
            if not src_dir.is_dir():
                raise FileNotFoundError(f"Required release subdirectory missing: {src_dir}")
            for src in sorted(src_dir.rglob("*")):
                if not src.is_file():
                    continue
                rel = f"{tree_rel}/{subdir}/{rel_str(src, src_dir)}"
                stage_file(src, stage / rel, rel)

    for rel in SCAFFOLD_FILES:
        src = ROOT / rel
        if not src.is_file():
            raise FileNotFoundError(f"Required scaffold file missing: {src}")
        stage_file(src, stage / rel, rel)

    missing = [rel for rel in REQUIRED_FILES if not (stage / rel).is_file()]
    if missing:
        raise RuntimeError("Release stage is missing required files:\n  " + "\n  ".join(missing))

    forbidden = [rel_str(p, stage) for p in stage.rglob("*") if p.is_file() and is_excluded(rel_str(p, stage))]
    if forbidden:
        raise RuntimeError("Release stage contains excluded files:\n  " + "\n  ".join(sorted(forbidden)))


def write_manifest(stage: Path) -> int:
    files = sorted((p for p in stage.rglob("*") if p.is_file()), key=lambda p: rel_str(p, stage))
    lines = [
        "# SHA-256 manifest for Dynamic Kit & Sponsor Mod release package",
        "# Format: <hex digest>  <path relative to package root>",
        "",
    ]
    for path in files:
        if path.name == "MANIFEST.sha256":
            continue
        lines.append(f"{sha256_file(path)}  {rel_str(path, stage)}")
    (stage / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return len(files)


def build_zip(stage: Path, version: str) -> tuple[Path, Path, int]:
    DIST.mkdir(parents=True, exist_ok=True)
    package_name = f"DynamicKitSponsorMod_v{version}"
    zip_path = DIST / f"{package_name}.zip"
    sidecar = DIST / f"{package_name}.zip.sha256"
    if zip_path.exists():
        zip_path.unlink()
    if sidecar.exists():
        sidecar.unlink()

    count = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted((p for p in stage.rglob("*") if p.is_file()), key=lambda p: rel_str(p, stage)):
            zf.write(path, rel_str(path, stage))
            count += 1

    sidecar.write_text(f"{sha256_file(zip_path)}  {zip_path.name}\n", encoding="utf-8", newline="\n")
    return zip_path, sidecar, count


def main() -> int:
    release = json.loads(RELEASE_JSON.read_text(encoding="utf-8"))
    version = str(release["version"])
    temp_root = Path(os.environ.get("TEMP") or tempfile.gettempdir())
    stage = Path(tempfile.mkdtemp(prefix="kg-release-", dir=str(temp_root)))
    try:
        stage_tree(stage)
        file_count = write_manifest(stage)
        zip_path, sidecar, zipped_count = build_zip(stage, version)
        uncompressed = sum(p.stat().st_size for p in stage.rglob("*") if p.is_file())
        print(f"Release       : {release['name']} v{version} ({release['channel']})")
        print(f"Package       : {zip_path}")
        print(f"Hash sidecar  : {sidecar}")
        print(f"Files         : {zipped_count} (manifest entries: {file_count})")
        print(f"Uncompressed  : {uncompressed / (1024 * 1024):.2f} MiB")
        print(f"ZIP size      : {zip_path.stat().st_size / (1024 * 1024):.2f} MiB")
        return 0
    finally:
        shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
