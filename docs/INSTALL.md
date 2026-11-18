# Install & first-run guide

> Back up your **save folder** and your **Sider folder** before you start.
> The mod never edits the game's own files, your save, or your Mod Studio project. It only
> writes inside `content/KitGenerator` (deals, ledgers, requests) and `kgprobe.log`.

## 1. What you need

- Football Life 2027 (PES 2021 engine) with **Sider** installed.
- **Python 3** (3.10+) on `PATH`, with `pillow` and `numpy`:
  ```
  pip install pillow numpy
  ```
  (`lupa` is only needed to run the test suite.)

## 2. Copy the files

From this repository copy:

| From            | To                                |
|-----------------|-----------------------------------|
| `modules/`      | `SiderAddons/modules/`            |
| `content/`      | `SiderAddons/content/`            |
| `livecpk/`      | `SiderAddons/livecpk/`            |

## 3. Deploy the watcher (one-time)

The background watcher rebuilds the kits when you sign a deal. Deploy it once (re-run after
moving the mod or changing your Python install):

```
python generator/setup_watcher.py
```

This copies the generator into the game (`SiderAddons/KitGenerator/generator`), writes
`SiderAddons/content/KitGenerator/watcher.cmd`, and generates `brands.txt` (the brand pool)
from the shipped logos. It uses `pythonw`, so no console window appears. Only **one**
watcher runs at a time (it holds a loopback port).

To try the watcher without the game:

```
python generator/watch_signed.py --sider "<SiderAddons>" --once
```

Watch what it did in `content/KitGenerator/watcher.log`; processed offers are remembered in
`watcher_state.txt`, so a deal is only ever built once.

## 4. Enable the module

In `SiderAddons/sider.ini`:

```ini
luajit.ext.enabled = 1
lua.module = "KitGenerator.lua"
```

The **Sider Mod Menu**, if you use it, must be the **first** `lua.module`. Only add
`overlay.*` lines if you use the classic text overlay instead of the Mod Menu.

The `livecpk` order matters — the mod's root must be listed **before** any other root that
also ships a kit for the same team:

```ini
cpk.root = ".\livecpk\KitGenerator"
cpk.root = ".\livecpk\SoundtrackServer"
...
```

## 5. First run

1. Start the game through Sider and begin a **Master League with any team**.
2. Press **F8** to switch the office on (Master League detection is manual for now).
3. Open the **Sponsor Office** — Mod Menu **F1**, or **F7** for the classic overlay.
4. The **Club** card shows the club that was auto-detected (name, team id, how it was
   detected, matches seen). It may read *"not detected yet"* until you have played a couple
   of league matches — that is expected. You can also type a team id by hand and use
   **Back to auto-detect**.

## 6. Optional: verify the probe first

If something looks wrong, install the read-only probe on its own to collect diagnostics:

1. Copy `modules/KGProbe.lua` into `SiderAddons/modules/`.
2. Add `lua.module = "KGProbe.lua"` as the **last** line of `sider.ini`.
3. Start the game and open `kgprobe.log` in the Sider folder. It records the Lua sandbox
   facts, game-mode / tournament ids, and the kit files the game requests.

## Uninstall

Delete the `lua.module` lines you added and the copied `modules/`, `content/KitGenerator/`,
`livecpk/KitGenerator/` and `SiderAddons/KitGenerator/` folders. Nothing outside those paths
is touched.

## Troubleshooting

| Symptom | Check |
|---|---|
| No offers appear | You are in the pre-season (Jun–Aug) and Master League is toggled on (F8). A running multi-year deal blocks new offers until it ends. |
| Club shows *"not detected yet"* | Play ~2 league matches; the career learner needs the club to appear in more than one fixture. Or type the team id by hand on the Club card. |
| Kit does not change after signing | `content/KitGenerator/watcher.log` — it should log `signed: offer=...` then `built p1/p2/p3 ... installed`. If the watcher never started, re-run `setup_watcher.py`. |
| Money not credited | Budget crediting needs the in-game addresses; see the load line in `sider.log` (`budget crediting ON`). |
| Wrong kit colours | The club's id is colliding with a wrong row in `generator/clubs.csv`. Fix the row (or remove it) and re-run `setup_watcher.py`. |
