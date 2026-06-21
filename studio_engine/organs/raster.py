"""Native PNG rasterizer for phyllotaxis geometry. Stdlib only.

Compositor organ. Matures the shipped phyllotaxis/SVG work into a raster channel:
hand-built 8-bit RGB PNGs (IHDR + IDAT + IEND, CRC32-checked, zlib-deflated) with
no external imaging dependency. The complement to organs/geometry.py's vector to_svg.
"""
from __future__ import annotations

import base64
import math
import struct
import zlib

from studio_engine.model import Artifact

_PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _chunk(tag: bytes, data: bytes) -> bytes:
    """One PNG chunk: 4-byte big-endian length, type tag, payload, CRC32 of tag+payload."""
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_png(width: int, height: int, rgb: bytes) -> bytes:
    """Build a valid 8-bit RGB PNG from raw `width*height*3` bytes. Deterministic.

    Scanlines are each prefixed with filter byte 0x00 (no filtering), then deflated
    into a single IDAT. Signature + IHDR + IDAT + IEND.
    """
    stride = width * 3
    expected = stride * height
    if len(rgb) != expected:
        raise ValueError(f"rgb has {len(rgb)} bytes, expected {expected} ({width}x{height}x3)")
    # IHDR: width, height, bit depth 8, color type 2 (truecolor RGB), default filt/interlace.
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    # Prefix each scanline with filter-type byte 0x00.
    raw = bytearray()
    for y in range(height):
        raw.append(0x00)
        raw.extend(rgb[y * stride:(y + 1) * stride])
    idat = zlib.compress(bytes(raw), 9)
    return (_PNG_SIG + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", idat) + _chunk(b"IEND", b""))


def _parse_hex(s: str) -> tuple[int, int, int]:
    """'#rrggbb' (or 'rrggbb') -> (r, g, b) clamped 0..255."""
    h = s.lstrip("#")
    if len(h) != 6:
        return (232, 232, 240)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def render_phyllotaxis_png(pts, palette: list[str], size: int = 720,
                           bg: tuple[int, int, int] = (14, 17, 22)) -> Artifact:
    """Rasterize centered `(x, y, i)` points as filled discs onto a `size`x`size` RGB PNG.

    Color per point = palette[int(i/len(pts)*len(palette))] (hex), centered at (size/2, size/2).
    Returns a finalized PNG Artifact whose content is the base64 of the PNG bytes.
    """
    br, bgc, bb = bg
    fb = bytearray(size * size * 3)
    for off in range(0, len(fb), 3):
        fb[off] = br
        fb[off + 1] = bgc
        fb[off + 2] = bb

    n = max(1, len(pts))
    np_ = max(1, len(palette))
    cx = cy = size / 2.0
    radius = max(1, size // 240)          # small disc, scales gently with canvas
    r2 = radius * radius

    for (x, y, i) in pts:
        col = palette[int((i / n) * np_) % np_] if palette else "#e8e8f0"
        pr, pg, pb = _parse_hex(col)
        px = int(round(cx + x))
        py = int(round(cy + y))
        for dy in range(-radius, radius + 1):
            yy = py + dy
            if yy < 0 or yy >= size:
                continue
            row = yy * size * 3
            dy2 = dy * dy
            for dx in range(-radius, radius + 1):
                if dx * dx + dy2 > r2:
                    continue
                xx = px + dx
                if xx < 0 or xx >= size:
                    continue
                o = row + xx * 3
                fb[o] = pr
                fb[o + 1] = pg
                fb[o + 2] = pb

    png = write_png(size, size, bytes(fb))
    b64 = base64.b64encode(png).decode("ascii")
    return Artifact("png", b64, size, size, label="phyllotaxis-raster").finalize()
