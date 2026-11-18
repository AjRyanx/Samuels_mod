"""Copies one staged season into the live livecpk folder. Only ever deletes our own folder."""
import shutil, sys
from pathlib import Path
ACTIVE_NAME = 'KitGenerator'

def activate_season(staging, livecpk_root, season):
    active = Path(livecpk_root) / ACTIVE_NAME
    src = Path(staging) / f'season_{season}'
    if active.name != ACTIVE_NAME or not src.is_dir():
        raise SystemExit('refusing: unexpected folder')
    if active.exists():
        shutil.rmtree(active)
    shutil.copytree(src, active)
    print('activated season', season)

if __name__ == '__main__':
    activate_season(*sys.argv[1:3], int(sys.argv[3]))
