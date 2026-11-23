"""Season high-water marks must be scoped per Master League career."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GEN = ROOT / "generator"
if str(GEN) not in sys.path:
    sys.path.insert(0, str(GEN))

import watch_signed


def test_season_high_water_is_per_career():
    lines = [
        "season-ml_old-2033|0|2033|all|balanced|2026-01-01 00:00:00|ml_old",
        "season-ml_new-2028|0|2028|all|balanced|2026-01-01 00:00:00|ml_new",
        "rebuild-4180-bridgestone-2028-t20260101000000|4180|2028|bridgestone|big|2026-01-01 00:00:00|ml_new",
        "jit-104-2028|104|2028|all|jit|2026-01-01 00:00:00|ml_new",
    ]
    seen = {"season-ml_old-2033", "season-ml_new-2028"}

    high = watch_signed._season_high_water(lines, seen)

    assert high == {"ml_old": 2033, "ml_new": 2028}
    # An old career's 2033 must not retire this career's 2028 rebuild.
    assert high.get("ml_new", 0) == 2028


def test_unfinished_rollover_does_not_set_high_water():
    lines = [
        "season-ml_new-2029|0|2029|all|balanced|2026-01-01 00:00:00|ml_new",
    ]

    assert watch_signed._season_high_water(lines, set()) == {}


def test_state_cache_reloads_when_file_changes(tmp_path):
    state = tmp_path / "watcher_state.txt"
    state.write_text("first\n", encoding="utf-8")
    os.utime(state, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))
    assert watch_signed._read_state_cached(state) == {"first"}

    state.write_text("first\nsecond\n", encoding="utf-8")
    os.utime(state, ns=(1_700_000_001_000_000_000, 1_700_000_001_000_000_000))
    assert watch_signed._read_state_cached(state) == {"first", "second"}
