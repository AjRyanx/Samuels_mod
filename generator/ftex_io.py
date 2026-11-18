#!/usr/bin/env python3
"""ftex_io.py - FTEX texture container I/O for SP Football Life 2027 (PES 2021 engine).

This is no longer a sketch. The layout below was reverse-engineered from real
FL27 kit textures (SiderAddons/content/kits/TheGaffer_Chelsea_FC/p1/u0102p1.ftex)
and round-trips exactly: every mip of every real kit decompresses to its declared
size, and rebuilds parse back byte-for-byte.

Container layout
----------------
0x00  header, 64 bytes, struct '<4sfHHHHBBHIIIBB14x8s8s':
        magic        'FTEX'
        version      float  (2.03 for pixel_format <= 4, else 2.04)
        pixel_format u16    (see FORMAT_* tables)
        width        u16
        height       u16
        depth        u16    (0 for 2D)
        mip_count    u8
        nrt          u8     (0x02 normally)
        flags        u16    (0x11 normally)
        unk1         u32    (always 1)
        unk2         u32    (always 0)
        texture_type u32    (0x1 linear, 0x3 sRGB, 0x9 normal; |0x4 cube)
        ftexs_count  u8     (0 = all data in this file)
        unk3         u8
        pad[14]
        hash1[8], hash2[8]  (name hashes; tools may zero them)

0x40  mip table, mip_count entries of 16 bytes, struct '<IIIBBH':
        data_offset        u32  absolute file offset of the mip payload
        uncompressed_size  u32  size of the decoded mip image
        compressed_size    u32  size of the whole payload (chunk table + data)
        mip_index          u8
        ftexs_number       u8
        chunk_count        u16

Mip payload
-----------
chunk_count chunk headers, struct '<HHI': comp_size(u16), uncomp_size(u16), offset(u32).
Then the chunk bytes. `offset` is relative to the start of the mip payload and has
bit 31 set when the chunk is stored raw. A chunk is raw when bit 31 is set OR
comp_size == uncomp_size; otherwise it is a plain zlib stream. Concatenating the
decoded chunks yields the mip image (compressed block data, e.g. BC3).

Confirmed on real files
-----------------------
  * 2048x2048 kits: pixel_format 4 (BC3/DXT5), 12 mips, texture_type 3.
  * chunk size is 16384 bytes (chunk_count == ceil(uncompressed_size / 16384)).
  * compression is plain zlib -- NOT Oodle.
"""

import io
import math
import struct
import sys
import zlib
from pathlib import Path

FTEX_HEADER = "<4sfHHHHBBHIIIBB14x8s8s"
MIP_ENTRY = "<IIIBBH"
CHUNK_HEADER = "<HHI"
CHUNK_SIZE = 1 << 14  # 16384 - value known not to crash PES
HEADER_SIZE = struct.calcsize(FTEX_HEADER)  # 64
MIP_ENTRY_SIZE = struct.calcsize(MIP_ENTRY)  # 16

# pixel_format -> (block_size_pixels, block_size_bytes)
FORMAT_BLOCK = {
    0: (1, 4),   # A8R8G8B8
    1: (1, 1),   # R8_UNORM
    2: (4, 8),   # BC1 / DXT1
    3: (4, 16),  # BC2 / DXT3
    4: (4, 16),  # BC3 / DXT5
    8: (4, 8),   # BC4
    9: (4, 16),  # BC5
    10: (4, 16), # BC6H
    11: (4, 16), # BC7
    12: (1, 8),  # R16G16B16A16_FLOAT
    13: (1, 16), # R32G32B32A32_FLOAT
    14: (1, 4),  # R10G10B10A2_UNORM
    15: (1, 4),  # R11G11B10_FLOAT
}
FORMAT_NAME = {
    0: "A8R8G8B8", 1: "R8_UNORM", 2: "BC1/DXT1", 3: "BC2/DXT3", 4: "BC3/DXT5",
    8: "BC4", 9: "BC5", 10: "BC6H", 11: "BC7", 12: "RGBA16F", 13: "RGBA32F",
    14: "R10G10B10A2", 15: "R11G11B10F",
}
# Pillow pixel_format keyword for each ftex format we can encode from an image
PIL_FORMAT = {2: "DXT1", 3: "DXT3", 4: "DXT5", 9: "BC5"}
# ftex format -> DDS fourcc (legacy, no DX10 extension header needed)
DDS_FOURCC = {2: b"DXT1", 3: b"DXT3", 4: b"DXT5"}
# ftex format -> DXGI format for the DX10 extension header
DDS_DXGI = {
    1: 61, 8: 80, 9: 83, 10: 95, 11: 98, 12: 10, 13: 2, 14: 24, 15: 26,
}
DXGI_TO_FTEX = {v: k for k, v in DDS_DXGI.items()}
DXGI_TO_FTEX.update({71: 2, 74: 3, 77: 4})
FOURCC_TO_FTEX = {b"DXT1": 2, b"DXT3": 3, b"DXT5": 4, b"8888": 0}


class FtexError(Exception):
    pass


# --------------------------------------------------------------------------- #
#  reading
# --------------------------------------------------------------------------- #
def _decode_frame(data, offset, uncompressed_size, compressed_size, chunk_count):
    """Decode one mip payload into its raw image bytes."""
    if chunk_count == 0:
        blob = data[offset:offset + (compressed_size or uncompressed_size)]
        if compressed_size == 0:
            return blob  # stored raw
        return zlib.decompress(blob)

    out = bytearray()
    for c in range(chunk_count):
        csz, usz, rel = struct.unpack_from(CHUNK_HEADER, data, offset + c * 8)
        raw = bool(rel & 0x80000000) or csz == usz
        rel &= 0x7FFFFFFF
        blob = data[offset + rel:offset + rel + csz]
        if len(blob) != csz:
            raise FtexError(f"truncated chunk {c} at 0x{offset + rel:x}")
        out += blob if raw else zlib.decompress(blob)
    if len(out) != uncompressed_size:
        raise FtexError(f"mip decoded to {len(out)} bytes, expected {uncompressed_size}")
    return bytes(out)


def parse_ftex(data):
    """Parse a whole .ftex into a dict with header fields and decoded frames."""
    if data[:4] != b"FTEX":
        raise FtexError("not an FTEX file")
    (magic, version, fmt, width, height, depth, mip_count, nrt, flags,
     unk1, unk2, texture_type, ftexs_count, unk3, hash1, hash2) = \
        struct.unpack_from(FTEX_HEADER, data, 0)
    if ftexs_count:
        raise FtexError("external .ftexs variants are not supported")

    frames = []
    for i in range(mip_count):
        off, unc, comp, idx, fsn, cc = struct.unpack_from(
            MIP_ENTRY, data, HEADER_SIZE + i * MIP_ENTRY_SIZE)
        frames.append(_decode_frame(data, off, unc, comp, cc))

    return {
        "magic": magic, "version": version, "pixel_format": fmt,
        "width": width, "height": height, "depth": depth,
        "mip_count": mip_count, "nrt": nrt, "flags": flags,
        "texture_type": texture_type, "hashes": hash1 + hash2,
        "frames": frames,
    }


def read_ftex(path):
    with open(path, "rb") as fh:
        return parse_ftex(fh.read())


# --------------------------------------------------------------------------- #
#  writing
# --------------------------------------------------------------------------- #
def _encode_frame(frame):
    """Encode raw mip bytes into a chunked payload. Returns (payload, chunk_count)."""
    chunk_count = max(1, (len(frame) + CHUNK_SIZE - 1) // CHUNK_SIZE)
    base = chunk_count * 8
    headers = bytearray()
    body = bytearray()
    for i in range(chunk_count):
        chunk = frame[i * CHUNK_SIZE:(i + 1) * CHUNK_SIZE]
        comp = zlib.compress(chunk, 9)
        if len(comp) >= len(chunk):
            comp, flag = chunk, 1 << 31  # incompressible -> store raw
        else:
            flag = 0
        headers += struct.pack(CHUNK_HEADER, len(comp), len(chunk), base + len(body) + flag)
        body += comp
    return bytes(headers + body), chunk_count


def build_ftex(frames, width, height, fmt=4, version=None, texture_type=3,
               nrt=2, flags=0x11, hashes=b"\x00" * 16):
    """Assemble a .ftex from decoded frames (frames[0] is the largest mip)."""
    if not frames:
        raise FtexError("need at least one mip frame")
    if version is None:
        version = 2.03 if fmt <= 4 else 2.04
    hashes = (hashes + b"\x00" * 16)[:16]
    mip_count = len(frames)

    data_start = HEADER_SIZE + mip_count * MIP_ENTRY_SIZE
    table = bytearray()
    payload = bytearray()
    for i, frame in enumerate(frames):
        blob, cc = _encode_frame(frame)
        table += struct.pack(MIP_ENTRY, data_start + len(payload), len(frame),
                             len(blob), i, 0, cc)
        payload += blob

    header = struct.pack(
        FTEX_HEADER, b"FTEX", float(version), fmt, width, height, 0, mip_count,
        nrt, flags, 1, 0, texture_type, 0, 0, hashes[:8], hashes[8:])
    return bytes(header + table + payload)


def write_ftex(path, data):
    Path(path).write_bytes(data)
    return path


# --------------------------------------------------------------------------- #
#  DDS bridge
# --------------------------------------------------------------------------- #
def _mip_size(fmt, width, height, level, depth=1):
    bpx, bbytes = FORMAT_BLOCK[fmt]
    s = 1 << level
    w = max(1, (width + s - 1) // s)
    h = max(1, (height + s - 1) // s)
    d = max(1, (depth + s - 1) // s)
    return ((w + bpx - 1) // bpx) * ((h + bpx - 1) // bpx) * d * bbytes


def ftex_to_dds(data):
    """Convert .ftex bytes to a .dds byte string (legacy fourcc or DX10 ext)."""
    info = parse_ftex(data)
    fmt, w, h, frames = info["pixel_format"], info["width"], info["height"], info["frames"]
    mips = len(frames)

    flags = 0x1 | 0x2 | 0x4 | 0x1000  # caps | height | width | pixelformat
    caps1 = 0x1000
    caps2 = 0
    if mips > 1:
        flags |= 0x20000
        caps1 |= 0x8 | 0x400000
    if (info["texture_type"] & 0x4):
        caps2 |= 0x200

    if fmt == 0:
        flags |= 0x8  # pitch
        pitch = 4 * w
        pfflags, fourcc, bits = 0x41, b"\x00\x00\x00\x00", 32
        masks = (0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
        use_dx10 = False
    else:
        flags |= 0x80000  # linearsize
        pitch = len(frames[0])
        pfflags, bits, masks = 0x4, 0, (0, 0, 0, 0)
        if fmt in DDS_FOURCC:
            fourcc, use_dx10 = DDS_FOURCC[fmt], False
        elif fmt in DDS_DXGI:
            fourcc, use_dx10 = b"DX10", True
        else:
            raise FtexError(f"unsupported pixel format {fmt} for DDS")

    out = bytearray()
    out += struct.pack("<4s7I44x2I4s5I2I12x", b"DDS ", 124, flags, h, w, pitch, 0,
                       mips, 32, pfflags, fourcc, bits, *masks, caps1, caps2)
    if use_dx10:
        out += struct.pack("<5I", DDS_DXGI[fmt], 3, 0, 1, 0)
    for frame in frames:
        out += frame
    return bytes(out)


def dds_to_ftex(data, color_space="SRGB"):
    """Convert .dds bytes to .ftex bytes."""
    if data[:4] != b"DDS ":
        raise FtexError("not a DDS file")
    (dds_magic, hdr_size, flags, h, w, pitch, depth, mip_count,
     pf_size, pf_flags, fourcc, bits, *rest) = \
        struct.unpack_from("<4s7I44x2I4s5I2I12x", data, 0)
    if hdr_size != 124:
        raise FtexError("bad DDS header size")
    caps1, caps2 = rest[-2], rest[-1]

    pos = 128
    if fourcc == b"DX10":
        (dxgi,) = struct.unpack_from("<I", data, pos)
        pos += 20
        if dxgi in DXGI_TO_FTEX:
            fmt = DXGI_TO_FTEX[dxgi]
        else:
            raise FtexError(f"unsupported DXGI format {dxgi}")
    elif fourcc in FOURCC_TO_FTEX:
        fmt = FOURCC_TO_FTEX[fourcc]
    elif (pf_flags & 0x40) and (pf_flags & 0x1) and rest[0] == 0x00FF0000:
        fmt = 0
    else:
        raise FtexError(f"unsupported DDS codec {fourcc!r}")

    if not (caps1 & 0x400000) or mip_count <= 1:
        mip_count = 1

    frames = []
    for i in range(mip_count):
        n = _mip_size(fmt, w, h, i)
        frame = data[pos:pos + n]
        if len(frame) != n:
            raise FtexError("unexpected end of DDS stream")
        pos += n
        frames.append(frame)

    ttype = {"LINEAR": 0x1, "SRGB": 0x3, "NORMAL": 0x9}.get(color_space, 0x9)
    return build_ftex(frames, w, h, fmt=fmt, texture_type=ttype)


# --------------------------------------------------------------------------- #
#  image bridge (PNG <-> ftex), using Pillow's BCn encoder
# --------------------------------------------------------------------------- #
def image_to_dds(img, fmt=4, mip_count=None):
    """Encode a PIL image to a full-mip-chain DDS using Pillow's BCn encoder."""
    from PIL import Image  # local import so the container code has no hard dep

    if fmt not in PIL_FORMAT:
        raise FtexError(f"cannot encode pixel format {fmt} from an image "
                        f"(supported: {sorted(PIL_FORMAT)})")
    img = img.convert("RGBA" if fmt != 9 else "RGB")
    w, h = img.size
    if mip_count is None:
        mip_count = int(math.log2(max(w, h))) + 1

    frames = []
    for i in range(mip_count):
        lw, lh = max(1, w >> i), max(1, h >> i)
        level = img if (lw, lh) == (w, h) else img.resize((lw, lh), Image.LANCZOS)
        buf = io.BytesIO()
        level.save(buf, format="DDS", pixel_format=PIL_FORMAT[fmt])
        frames.append(buf.getvalue()[128:])
    return ftex_to_dds(build_ftex(frames, w, h, fmt=fmt))


def image_to_ftex(img, fmt=4, mip_count=None, template=None):
    """Encode a PIL image directly to .ftex bytes, optionally inheriting a
    template's version / texture_type / hashes (use the kit you are replacing)."""
    dds = image_to_dds(img, fmt=fmt, mip_count=mip_count)
    info = parse_ftex(dds_to_ftex(dds, color_space="SRGB"))
    version = template["version"] if template else None
    ttype = template["texture_type"] if template else 3
    hashes = template["hashes"] if template else b"\x00" * 16
    return build_ftex(info["frames"], info["width"], info["height"], fmt=fmt,
                      version=version, texture_type=ttype, hashes=hashes)


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def _inspect(path):
    info = read_ftex(path)
    print(f"file={path}")
    print(f"  version={info['version']:.3f} pixel_format={info['pixel_format']} "
          f"({FORMAT_NAME.get(info['pixel_format'], '?')}) "
          f"size={info['width']}x{info['height']} mips={info['mip_count']} "
          f"texture_type={info['texture_type']:#x} bytes={Path(path).stat().st_size}")
    for i, frame in enumerate(info["frames"]):
        print(f"    mip{i:2d} decoded={len(frame)} bytes")


def _extract(src, dst=None):
    from PIL import Image
    info = read_ftex(src)
    dds = ftex_to_dds(Path(src).read_bytes())
    if dst is None:
        dst = str(Path(src).with_suffix(".dds"))
    Path(dst).write_bytes(dds)
    if str(dst).lower().endswith(".png"):
        Image.open(io.BytesIO(dds)).save(dst)
    print("wrote", dst)


def _build(src_png, dst, fmt=4, mips=None, size=None):
    from PIL import Image
    img = Image.open(src_png)
    if size:
        img = img.resize((size, size), Image.LANCZOS)
    data = image_to_ftex(img, fmt=fmt, mip_count=mips)
    write_ftex(dst, data)
    print(f"wrote {dst} ({len(data)} bytes, {img.size[0]}x{img.size[1]}, "
          f"{FORMAT_NAME.get(fmt)}, {len(parse_ftex(data)['frames'])} mips)")


def _repack(base_ftex, src_png, dst, fmt=None, mips=None):
    from PIL import Image
    tpl = read_ftex(base_ftex)
    img = Image.open(src_png).resize((tpl["width"], tpl["height"]), Image.LANCZOS)
    fmt = fmt or tpl["pixel_format"]
    data = image_to_ftex(img, fmt=fmt, mip_count=mips, template=tpl)
    write_ftex(dst, data)
    print(f"wrote {dst} ({len(data)} bytes) from {base_ftex} + {src_png}")


def _selftest(path):
    """Decode a real file, rebuild it, and confirm it parses back identically."""
    raw = Path(path).read_bytes()
    info = read_ftex(path)
    rebuilt = build_ftex(info["frames"], info["width"], info["height"],
                         fmt=info["pixel_format"], version=info["version"],
                         texture_type=info["texture_type"], hashes=info["hashes"])
    again = parse_ftex(rebuilt)
    ok = (again["frames"] == info["frames"]
          and again["width"] == info["width"] and again["height"] == info["height"]
          and again["pixel_format"] == info["pixel_format"]
          and again["mip_count"] == info["mip_count"])
    print(f"selftest {path}: {info['width']}x{info['height']} "
          f"{FORMAT_NAME.get(info['pixel_format'])} mips={info['mip_count']} "
          f"orig={len(raw)}B rebuilt={len(rebuilt)}B -> {'OK' if ok else 'FAIL'}")
    return ok


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("usage:\n"
              "  python ftex_io.py <file.ftex>                      inspect\n"
              "  python ftex_io.py extract <file.ftex> [out.dds|png]\n"
              "  python ftex_io.py build <in.png> <out.ftex> [--dxt5] [--mips N] [--size N]\n"
              "  python ftex_io.py repack <base.ftex> <in.png> <out.ftex> [--mips N]\n"
              "  python ftex_io.py selftest <file.ftex>")
        return 0

    cmd, args = argv[0], argv[1:]
    if cmd == "extract":
        _extract(args[0], args[1] if len(args) > 1 else None)
    elif cmd == "build":
        mips = int(args[args.index("--mips") + 1]) if "--mips" in args else None
        size = int(args[args.index("--size") + 1]) if "--size" in args else None
        _build(args[0], args[1], mips=mips, size=size)
    elif cmd == "repack":
        mips = int(args[args.index("--mips") + 1]) if "--mips" in args else None
        _repack(args[0], args[1], args[2], mips=mips)
    elif cmd == "selftest":
        return 0 if _selftest(args[0]) else 1
    else:
        _inspect(cmd)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
