#!/usr/bin/env python3
"""test_concurrency_and_cleanup.py - Test concurrent file writes and staging auto-cleanup."""
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GEN = ROOT / "generator"
if str(GEN) not in sys.path:
    sys.path.insert(0, str(GEN))

import activate_season
import watch_signed

def test_concurrent_writes():
    with tempfile.TemporaryDirectory() as tmpdir:
        req_file = Path(tmpdir) / "kit_request.txt"
        state_file = Path(tmpdir) / "watcher_state.txt"

        n_threads = 8
        writes_per_thread = 25
        total_expected = n_threads * writes_per_thread

        def worker(tid):
            for i in range(writes_per_thread):
                line = f"offer-{tid}-{i}|103|2027|brand_{tid}|tier1|2026-11-19 08:00:00"
                ok = watch_signed.safe_append_line(req_file, line)
                assert ok, f"Worker {tid} append failed"
                time.sleep(0.005)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Read back lines safely
        lines = watch_signed.safe_read_lines(req_file)
        assert len(lines) == total_expected, f"Expected {total_expected} lines, got {len(lines)}"

        # Verify all lines parse correctly (no torn reads or corrupted fields)
        parsed = [watch_signed._parse_request(ln) for ln in lines]
        assert all(p is not None for p in parsed), "All concurrent lines must parse without corruption"
        assert len({p["offer"] for p in parsed}) == total_expected, "All offers must be uniquely preserved"
        print(f"PASS: Concurrent write test passed ({total_expected} concurrent writes without loss/corruption).")


def test_staging_cleanup():
    with tempfile.TemporaryDirectory() as tmpdir:
        stg = Path(tmpdir) / "staging"
        stg.mkdir()

        # Create seasons 2024, 2025, 2026, 2027, 2028
        for yr in [2024, 2025, 2026, 2027, 2028]:
            s_dir = stg / f"season_{yr}"
            s_dir.mkdir()
            (s_dir / f"u0103p1.ftex").write_bytes(b"dummy ftex content")
            (s_dir / f"u0103p1_atlas.png").write_bytes(b"dummy png content")

        # Create loose scratch files in root
        (stg / "u0103p1.ftex").write_bytes(b"scratch")
        (stg / "u0103p1_atlas.png").write_bytes(b"scratch")
        (stg / "temp_render.tmp").write_bytes(b"scratch")

        # Run cleanup keeping 2 seasons (current=2028)
        cleaned = activate_season.cleanup_old_staging(stg, keep_seasons=2, current_season=2028)
        assert cleaned > 0, "Cleanup should remove old items"

        remaining_dirs = {d.name for d in stg.iterdir() if d.is_dir()}
        # Should keep season_2027 and season_2028, and delete 2024, 2025, 2026
        assert remaining_dirs == {"season_2027", "season_2028"}, f"Expected 2027, 2028, got {remaining_dirs}"

        # Loose scratch files should also be purged
        loose_files = [f.name for f in stg.iterdir() if f.is_file()]
        assert len(loose_files) == 0, f"Expected loose scratch files to be removed, got {loose_files}"

        print(f"PASS: Staging cleanup test passed (purged {cleaned} old seasons & scratch files).")


if __name__ == "__main__":
    test_concurrent_writes()
    test_staging_cleanup()
    print("ALL CONCURRENCY & CLEANUP TESTS PASSED!")
