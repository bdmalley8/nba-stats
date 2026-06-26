#!/usr/bin/env python3
"""Generate basketball app icons (PNG) with no third-party deps.
Draws an orange basketball with seams on a navy tile, supersampled for smooth edges."""
import struct, zlib, math

def lerp(a, b, t): return a + (b - a) * t
def mix(c1, c2, t): return tuple(int(round(lerp(c1[i], c2[i], t))) for i in range(3))

def render(size, ss=3):
    """Return list of (r,g,b) rows at `size`, supersampled by `ss`."""
    S = size * ss
    cx = cy = S / 2.0
    R = S * 0.46           # ball radius
    lw = S * 0.012         # seam half-width
    bg_top = (20, 27, 52)  # #141b34
    bg_bot = (8, 13, 26)   # #080d1a
    seam = (38, 24, 12)    # dark seam
    # seam arc geometry (see notes): circles centered at (cx ± 0.75R, cy), radius 1.25R
    arc_h = 0.75 * R
    arc_r = 1.25 * R
    px = []
    for y in range(S):
        row = bytearray()
        for x in range(S):
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy)
            if d <= R:
                # base ball color: radial highlight upper-left -> deep orange edge
                hx, hy = cx - R * 0.32, cy - R * 0.42
                hl = min(1.0, math.hypot(x - hx, y - hy) / (R * 1.5))
                col = mix((255, 165, 80), (191, 82, 15), hl)
                # seams
                on_seam = False
                if abs(dx) <= lw: on_seam = True                       # vertical
                if abs(dy) <= lw: on_seam = True                       # horizontal
                dl = abs(math.hypot(x - (cx + arc_h), y - cy) - arc_r)  # left-bowing arc
                if dl <= lw and dx < 0: on_seam = True
                dr = abs(math.hypot(x - (cx - arc_h), y - cy) - arc_r)  # right-bowing arc
                if dr <= lw and dx > 0: on_seam = True
                if on_seam:
                    col = seam
                # subtle dark rim
                if d > R - lw * 1.6:
                    col = mix(col, seam, 0.6)
            else:
                col = mix(bg_top, bg_bot, y / S)
            row += bytes(col)
        px.append(row)
    # downsample by ss (box filter)
    out = []
    for oy in range(size):
        orow = bytearray()
        for ox in range(size):
            r = g = b = 0
            for j in range(ss):
                base = px[oy * ss + j]
                for i in range(ss):
                    p = (ox * ss + i) * 3
                    r += base[p]; g += base[p + 1]; b += base[p + 2]
            n = ss * ss
            orow += bytes((r // n, g // n, b // n))
        out.append(bytes(orow))
    return out

def write_png(path, rows, size):
    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)  # 8-bit RGB
    raw = bytearray()
    for r in rows:
        raw.append(0)      # filter type none
        raw += r
    idat = zlib.compress(bytes(raw), 9)
    with open(path, "wb") as f:
        f.write(sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b""))

for sz in (180, 192, 512):
    write_png(f"icon-{sz}.png", render(sz), sz)
    print("wrote", f"icon-{sz}.png")
