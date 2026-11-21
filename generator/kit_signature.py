"""Content signatures for safe no-op kit skips.

A signature is only considered reusable when the visual inputs, renderer code,
source art, and the installed output file bytes all match the stored record.
This lets duplicate JIT/rebuild requests retire instantly without ever serving
stale kits.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional

MANIFEST_FILENAME = "kit_signatures.json"

SIGNATURE_SOURCES = (
    "kit_render.py",
    "build_kit.py",
    "kit_regions.py",
    "kit_patterns.py",
    "kit_dna.py",
    "kit_fonts.py",
    "ftex_io.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dir_fingerprint(path: Path) -> str:
    folder = Path(path)
    if not folder.is_dir():
        return ""
    rows = []
    for item in sorted(folder.rglob("*")):
        if not item.is_file():
            continue
        rows.append([
            item.relative_to(folder).as_posix(),
            item.stat().st_size,
            sha256_file(item),
        ])
    return hashlib.sha256(
        json.dumps(rows, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def build_signature(
    *,
    club_id: int,
    season: int,
    sponsor: Optional[str],
    slot,
    generator_dir: Path,
    base_ftex: Path,
    logo_dir: Path,
    badge_dir: Path,
    sleeve_dir: Optional[Path] = None,
) -> str:
    """Hash every input that can change the rendered pixels or FTEX bytes."""
    parts = [
        ["club", int(club_id)],
        ["season", int(season)],
        ["sponsor", str(sponsor or "")],
        ["slot", str(slot)],
    ]
    gen = Path(generator_dir)
    for name in SIGNATURE_SOURCES:
        source = gen / name
        parts.append([name, sha256_file(source) if source.is_file() else "missing"])
    base = Path(base_ftex)
    parts.append(["base", sha256_file(base) if base.is_file() else "missing"])
    parts.append(["logos", _dir_fingerprint(logo_dir)])
    parts.append(["badges", _dir_fingerprint(badge_dir)])
    if sleeve_dir is not None:
        parts.append(["sleeve", _dir_fingerprint(sleeve_dir)])
    return hashlib.sha256(
        json.dumps(parts, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def target_files(directory: Path, club_id: int, slot) -> List[Path]:
    """Main FTEX plus the three font-layer FTEX files for one kit slot."""
    code = f"p{slot}" if isinstance(slot, int) else str(slot)
    stem = f"u{club_id:04d}{code}"
    folder = Path(directory)
    return [
        folder / f"{stem}.ftex",
        folder / f"{stem}_back.ftex",
        folder / f"{stem}_leg.ftex",
        folder / f"{stem}_name.ftex",
    ]


def key_for(directory: Path, club_id: int, season: int, slot) -> str:
    return f"{Path(directory).resolve()}|{club_id}|{season}|{slot}"


def manifest_path(content_dir: Path) -> Path:
    return Path(content_dir) / MANIFEST_FILENAME


def load_manifest(content_dir: Path) -> Dict[str, dict]:
    path = manifest_path(content_dir)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_manifest(content_dir: Path, data: Dict[str, dict]) -> None:
    path = manifest_path(content_dir)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    tmp.replace(path)


def file_hashes(paths: List[Path]) -> Dict[str, str]:
    return {path.name: sha256_file(path) for path in paths if path.is_file()}


def matches(content_dir: Path, key: str, signature: str, paths: List[Path]) -> bool:
    """Return True only when the stored signature and all output bytes match."""
    entry = load_manifest(content_dir).get(key)
    if not entry or entry.get("signature") != signature:
        return False
    expected = entry.get("files")
    if not isinstance(expected, dict) or not expected:
        return False
    for path in paths:
        if not path.is_file():
            return False
        if expected.get(path.name) != sha256_file(path):
            return False
    return True


def record(content_dir: Path, key: str, signature: str, paths: List[Path]) -> None:
    data = load_manifest(content_dir)
    data[key] = {"signature": signature, "files": file_hashes(paths)}
    save_manifest(content_dir, data)
