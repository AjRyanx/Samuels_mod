"""Copies one staged season into the live livecpk folder and cleans up old staging files."""
import re
import shutil
import sys
from pathlib import Path

ACTIVE_NAME = 'KitGenerator'


def cleanup_old_staging(staging, keep_seasons=2, current_season=None):
    """Purge old season renders and loose scratch files from staging directory.
    
    Keeps at most `keep_seasons` latest season folders (including current_season),
    and removes older season folders and orphaned scratch files (*.tmp, loose *.ftex/*.png)
    to recover disk space and prevent staging bloat.
    """
    staging = Path(staging)
    if not staging.is_dir():
        return 0

    cleaned_count = 0
    # 1. Discover all season directories
    season_dirs = []
    for item in staging.iterdir():
        if item.is_dir():
            m = re.match(r"^season_(\d+)$", item.name)
            if m:
                season_num = int(m.group(1))
                season_dirs.append((season_num, item))

    season_dirs.sort(key=lambda x: x[0])

    # Decide which seasons to keep
    target_seasons = [s for s, _ in season_dirs]
    if current_season is not None and current_season not in target_seasons:
        target_seasons.append(current_season)
        target_seasons.sort()

    kept_seasons = set(target_seasons[-keep_seasons:]) if len(target_seasons) > keep_seasons else set(target_seasons)
    if current_season is not None:
        kept_seasons.add(current_season)

    for s_num, s_dir in season_dirs:
        if s_num not in kept_seasons:
            try:
                shutil.rmtree(s_dir)
                cleaned_count += 1
                print(f"[cleanup] purged old staging folder: {s_dir.name}")
            except OSError as e:
                print(f"[cleanup] failed to remove {s_dir.name}: {e}")

    # 2. Clean loose scratch files in staging root (e.g. *.tmp, loose u*.ftex / u*.png)
    for f in staging.iterdir():
        if f.is_file():
            if f.name.endswith(".tmp") or f.name.endswith(".bak"):
                try:
                    f.unlink()
                    cleaned_count += 1
                except OSError:
                    pass
            elif re.match(r"^u\d{4}p\d(_(atlas|preview|mockup))?\.(ftex|png)$", f.name):
                try:
                    f.unlink()
                    cleaned_count += 1
                    print(f"[cleanup] removed loose scratch file: {f.name}")
                except OSError:
                    pass

    return cleaned_count


def activate_season(staging, livecpk_root, season, keep_seasons=2):
    active = Path(livecpk_root) / ACTIVE_NAME
    src = Path(staging) / f'season_{season}'
    if active.name != ACTIVE_NAME or not src.is_dir():
        raise ValueError('refusing: unexpected folder')
    if active.exists():
        shutil.rmtree(active)
    shutil.copytree(src, active)
    print('activated season', season)
    cleaned = cleanup_old_staging(staging, keep_seasons=keep_seasons, current_season=season)
    if cleaned:
        print(f'cleaned {cleaned} old staging items')


if __name__ == '__main__':
    if '--cleanup' in sys.argv:
        idx = sys.argv.index('--cleanup')
        args = [a for i, a in enumerate(sys.argv) if i != idx and i > 0]
        stg = args[0] if len(args) > 0 else 'content/KitGenerator/staging'
        cur = int(args[1]) if len(args) > 1 else None
        n = cleanup_old_staging(stg, current_season=cur)
        print(f'purged {n} staging items')
    elif len(sys.argv) >= 4:
        activate_season(sys.argv[1], sys.argv[2], int(sys.argv[3]))
