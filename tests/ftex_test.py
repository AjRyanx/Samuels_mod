#!/usr/bin/env python3
"""FTEX container test.

With no argument it runs an in-memory round-trip on synthetic mip data (no game
files needed, so it is safe in CI). Point it at a real .ftex to verify the
container against an actual FL27 kit:

    python tests/ftex_test.py "C:\\...\\SiderAddons\\content\\kits\\...\\u0102p1.ftex"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "generator"))
import ftex_io  # noqa: E402


def synthetic_roundtrip():
    # a fake BC3 mip chain: sizes must follow the BC3 block maths
    import math
    frames = []
    for lvl in range(12):
        n = max(1, 2048 >> lvl)
        frames.append(bytes(n * n) if n >= 4 else bytes(16))
    data = ftex_io.build_ftex(frames, 2048, 2048, fmt=4, texture_type=3)
    info = ftex_io.parse_ftex(data)
    assert info["frames"] == frames, "mip frames did not survive the round-trip"
    assert info["mip_count"] == 12 and info["width"] == 2048
    # DDS bridge
    dds = ftex_io.ftex_to_dds(data)
    assert dds[:4] == b"DDS "
    back = ftex_io.dds_to_ftex(dds)
    assert ftex_io.parse_ftex(back)["frames"] == frames
    print("synthetic round-trip OK")


def real_file(path):
    info = ftex_io.read_ftex(path)
    raw = Path(path).read_bytes()
    rebuilt = ftex_io.build_ftex(info["frames"], info["width"], info["height"],
                                 fmt=info["pixel_format"], version=info["version"],
                                 texture_type=info["texture_type"], hashes=info["hashes"])
    again = ftex_io.parse_ftex(rebuilt)
    assert again["frames"] == info["frames"]
    print(f"{path}: {info['width']}x{info['height']} "
          f"{ftex_io.FORMAT_NAME.get(info['pixel_format'])} mips={info['mip_count']} "
          f"orig={len(raw)}B rebuilt={len(rebuilt)}B OK")


if __name__ == "__main__":
    synthetic_roundtrip()
    if len(sys.argv) > 1:
        real_file(sys.argv[1])
    print("FTEX TEST OK")
