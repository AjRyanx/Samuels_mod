"""Content-signature no-op skip tests for JIT and career rebuilds."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GEN = ROOT / "generator"
if str(GEN) not in sys.path:
    sys.path.insert(0, str(GEN))

import activate_season
import build_all_clubs
import build_kit
import kit_signature
import watch_signed


def _tree(tmp_path):
    gen = tmp_path / "generator"
    gen.mkdir()
    for name in kit_signature.SIGNATURE_SOURCES:
        (gen / name).write_text(name, encoding="utf-8")
    base = tmp_path / "base.ftex"
    base.write_bytes(b"FTEX" + b"base" * 32)
    logos = tmp_path / "logos"
    badges = tmp_path / "badges"
    sleeve = tmp_path / "sleeve_logos"
    for folder in (logos, badges, sleeve):
        folder.mkdir()
    (logos / "mansion.png").write_bytes(b"logo")
    (badges / "crest.png").write_bytes(b"badge")
    (sleeve / "cygames.png").write_bytes(b"sleeve")
    content = tmp_path / "content" / "KitGenerator"
    (content / "active").mkdir(parents=True)
    return gen, base, logos, badges, sleeve, content


def _signature_kwargs(gen, base, logos, badges, sleeve, **overrides):
    kwargs = dict(
        club_id=114,
        season=2030,
        sponsor="kucoin",
        slot="p1",
        generator_dir=gen,
        base_ftex=base,
        logo_dir=logos,
        badge_dir=badges,
        sleeve_dir=sleeve,
    )
    kwargs.update(overrides)
    return kwargs


def test_signature_tracks_visual_inputs(tmp_path):
    gen, base, logos, badges, sleeve, _ = _tree(tmp_path)
    sig = kit_signature.build_signature(**_signature_kwargs(gen, base, logos, badges, sleeve))

    assert kit_signature.build_signature(
        **_signature_kwargs(gen, base, logos, badges, sleeve, sponsor="1xbet")) != sig
    assert kit_signature.build_signature(
        **_signature_kwargs(gen, base, logos, badges, sleeve, slot="g1")) != sig
    assert kit_signature.build_signature(
        **_signature_kwargs(gen, base, logos, badges, sleeve, season=2031)) != sig

    (logos / "kucoin.png").write_bytes(b"new sponsor art")
    assert kit_signature.build_signature(
        **_signature_kwargs(gen, base, logos, badges, sleeve)) != sig

    sig_before_code = kit_signature.build_signature(
        **_signature_kwargs(gen, base, logos, badges, sleeve))
    (gen / "kit_render.py").write_text("changed renderer", encoding="utf-8")
    assert kit_signature.build_signature(
        **_signature_kwargs(gen, base, logos, badges, sleeve)) != sig_before_code


def test_recorded_signature_verifies_output_bytes(tmp_path):
    gen, base, logos, badges, sleeve, content = _tree(tmp_path)
    active = content / "active"
    paths = kit_signature.target_files(active, 114, "p1")
    for path in paths:
        path.write_bytes(b"FTEX" + path.name.encode("utf-8"))

    sig = kit_signature.build_signature(**_signature_kwargs(gen, base, logos, badges, sleeve))
    key = kit_signature.key_for(active, 114, 2030, "p1")
    kit_signature.record(content, key, sig, paths)
    assert kit_signature.matches(content, key, sig, paths)

    paths[0].write_bytes(b"FTEX externally modified")
    assert not kit_signature.matches(content, key, sig, paths)

    paths[0].write_bytes(b"FTEX" + paths[0].name.encode("utf-8"))
    assert kit_signature.matches(content, key, sig, paths)

    paths[-1].unlink()
    assert not kit_signature.matches(content, key, sig, paths)


def test_generate_club_kits_skips_identical_repeat(tmp_path, monkeypatch):
    sider = tmp_path / "SiderAddons"
    content = sider / "content" / "KitGenerator"
    active = content / "active"
    for folder in (active, content / "logos", content / "badges", content / "sleeve_logos"):
        folder.mkdir(parents=True, exist_ok=True)
    (content / "logos" / "mansion.png").write_bytes(b"logo")

    monkeypatch.setattr(build_kit, "_load_club",
                        lambda cid, root: {"id": cid, "name": "Test Club"})
    monkeypatch.setattr(build_all_clubs, "load_user_club_info",
                        lambda _root: (None, None, False))
    monkeypatch.setattr(kit_signature, "build_signature",
                        lambda **kw: f"{kw['club_id']}|{kw['season']}|{kw['sponsor']}|{kw['slot']}")

    calls = []

    def fake_build_set(club, season, outdir, **kwargs):
        calls.append(kwargs["sponsor"])
        sponsor = kwargs["sponsor"]
        results = []
        for slot in kwargs["slots"]:
            code = f"p{slot}" if isinstance(slot, int) else str(slot)
            stem = f"u{club['id']:04d}{code}"
            for suffix in ("", "_back", "_leg", "_name"):
                data = b"FTEX" + f"{stem}{suffix}".encode("utf-8")
                (Path(outdir) / f"{stem}{suffix}.ftex").write_bytes(data)
                (active / f"{stem}{suffix}.ftex").write_bytes(data)
            main = active / f"{stem}.ftex"
            results.append((slot, "", str(main), {"pattern": 1, "_brand": sponsor}))
        return results

    monkeypatch.setattr(build_kit, "build_set", fake_build_set)

    first = build_all_clubs.generate_club_kits(
        100, 2030, sider_dir=sider, slots="1", sponsor="mansion")
    second = build_all_clubs.generate_club_kits(
        100, 2030, sider_dir=sider, slots="1", sponsor="mansion")
    changed = build_all_clubs.generate_club_kits(
        100, 2030, sider_dir=sider, slots="1", sponsor="1xbet")

    assert first["skipped"] is False
    assert second["skipped"] is True
    assert second["reason"] == "signature_match"
    assert changed["skipped"] is False
    assert calls == ["mansion", "1xbet"]


def test_rebuild_skips_identical_repeat(tmp_path, monkeypatch):
    sider = tmp_path / "SiderAddons"
    game_root = tmp_path
    content = sider / "content" / "KitGenerator"
    active = content / "active"
    for folder in (active, content / "logos", content / "badges",
                   content / "sleeve_logos", content / "staging"):
        folder.mkdir(parents=True, exist_ok=True)
    logfile = content / "watcher.log"

    monkeypatch.setattr(build_kit, "_load_club",
                        lambda cid, root: {"id": cid, "name": "Test Club"})
    monkeypatch.setattr(activate_season, "cleanup_old_staging",
                        lambda *_a, **_kw: 0)
    monkeypatch.setattr(kit_signature, "build_signature",
                        lambda **kw: f"{kw['club_id']}|{kw['season']}|{kw['sponsor']}|{kw['slot']}")

    calls = []

    def fake_build_set(club, season, outdir, **kwargs):
        calls.append(kwargs["sponsor"])
        Path(outdir).mkdir(parents=True, exist_ok=True)
        results = []
        for slot in (1, 2, 3, "g1", "g2"):
            code = f"p{slot}" if isinstance(slot, int) else str(slot)
            stem = f"u{club['id']:04d}{code}"
            for suffix in ("", "_back", "_leg", "_name"):
                data = b"FTEX" + f"{stem}{suffix}".encode("utf-8")
                (Path(outdir) / f"{stem}{suffix}.ftex").write_bytes(data)
                (active / f"{stem}{suffix}.ftex").write_bytes(data)
            main = active / f"{stem}.ftex"
            results.append((slot, "", str(main),
                            {"pattern": 1, "_brand": kwargs["sponsor"]}))
        return results

    monkeypatch.setattr(build_kit, "build_set", fake_build_set)

    watch_signed.rebuild(114, 2030, "kucoin", sider, game_root, logfile)
    watch_signed.rebuild(114, 2030, "kucoin", sider, game_root, logfile)

    assert calls == ["kucoin"]
    assert "skipped 5 slot render(s)" in logfile.read_text(encoding="utf-8")
