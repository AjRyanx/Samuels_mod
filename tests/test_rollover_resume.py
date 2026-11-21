"""Resumable season-rollover and stage-timing tests."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GEN = ROOT / "generator"
if str(GEN) not in sys.path:
    sys.path.insert(0, str(GEN))

import build_all_clubs as b

MARKER = b.ROLLOVER_RESUME_MARKER


def _sider(tmp_path):
    kg = tmp_path / "content" / "KitGenerator"
    (kg / "active").mkdir(parents=True, exist_ok=True)
    return tmp_path, kg


def _staging(kg, season):
    return kg / "staging" / f"season_{season}" / "refresh_baseline"


def test_fresh_rollover_clears_staging_and_forces_rebuild(tmp_path, monkeypatch):
    sider, kg = _sider(tmp_path)
    staging = _staging(kg, 2033)
    staging.mkdir(parents=True)
    stale = staging / "u0100p1.ftex"
    stale.write_bytes(b"old")

    seen = {}

    def fake_generate(**kwargs):
        seen.update(kwargs)
        assert kwargs["skip_existing"] is False
        (kwargs["outdir"] / "u0100p1.ftex").write_bytes(b"FTEX" + b"x" * 100)
        return {"generated": 2, "skipped": 0, "elapsed": 1.25, "aborted": False}

    monkeypatch.setattr(b, "generate_all_kits", fake_generate)
    monkeypatch.setattr(b, "load_user_club_info", lambda _s: (None, None, False))
    monkeypatch.setattr(b, "_copy_staged_kits", lambda *_a: 2)
    monkeypatch.setattr(b, "_prune_secondary_kits", lambda *_a: 3)

    result = b.refresh_season_kits(2033, sider, prune_secondary=True)

    assert stale.read_bytes().startswith(b"FTEX")
    assert seen["skip_existing"] is False
    assert result["resumed"] is False
    assert result["copied"] == 2
    assert result["pruned"] == 3
    assert result["timings"]["render_s"] == 1.25
    assert result["timings"]["copy_s"] >= 0.0
    assert result["timings"]["prune_s"] >= 0.0
    assert not (staging / MARKER).exists()


def test_interrupted_rollover_resumes_and_discards_invalid_files(tmp_path, monkeypatch):
    sider, kg = _sider(tmp_path)
    staging = _staging(kg, 2034)
    staging.mkdir(parents=True)
    valid = staging / "u0100p1.ftex"
    valid.write_bytes(b"FTEX" + b"y" * 100)
    bad = staging / "u0101p1.ftex"
    bad.write_bytes(b"bad")
    marker = staging / MARKER
    marker.write_text("season=2034\nscope=baseline\nslots=1,g1\n", encoding="utf-8")

    seen = {}

    def fake_generate(**kwargs):
        seen.update(kwargs)
        assert kwargs["skip_existing"] is True
        assert valid.exists()
        assert not bad.exists()
        return {"generated": 0, "skipped": 2, "elapsed": 0.1, "aborted": False}

    monkeypatch.setattr(b, "generate_all_kits", fake_generate)
    monkeypatch.setattr(b, "load_user_club_info", lambda _s: (None, None, False))
    monkeypatch.setattr(b, "_copy_staged_kits", lambda *_a: 2)
    monkeypatch.setattr(b, "_prune_secondary_kits", lambda *_a: 0)

    result = b.refresh_season_kits(2034, sider, prune_secondary=True)

    assert seen["skip_existing"] is True
    assert result["resumed"] is True
    assert result["invalid_removed"] == 1
    assert result["skipped"] == 2
    assert result["timings"]["render_s"] == 0.1
    assert not marker.exists()


def test_aborted_rollover_keeps_resume_marker(tmp_path, monkeypatch):
    sider, kg = _sider(tmp_path)
    staging = _staging(kg, 2035)
    staging.mkdir(parents=True)
    marker = staging / MARKER
    marker.write_text("season=2035\nscope=baseline\nslots=1,g1\n", encoding="utf-8")

    def fake_generate(**kwargs):
        assert kwargs["skip_existing"] is True
        return {"generated": 1, "skipped": 0, "elapsed": 0.5, "aborted": True}

    monkeypatch.setattr(b, "generate_all_kits", fake_generate)
    monkeypatch.setattr(b, "load_user_club_info", lambda _s: (None, None, False))
    monkeypatch.setattr(b, "_copy_staged_kits", lambda *_a: (_ for _ in ()).throw(
        AssertionError("copy must not run after abort")))
    monkeypatch.setattr(b, "_prune_secondary_kits", lambda *_a: (_ for _ in ()).throw(
        AssertionError("prune must not run after abort")))

    result = b.refresh_season_kits(2035, sider, prune_secondary=True)

    assert result["aborted"] is True
    assert result["timings"]["render_s"] == 0.5
    assert marker.exists()


if __name__ == "__main__":
    print("Run with: python -m pytest -q tests/test_rollover_resume.py")
