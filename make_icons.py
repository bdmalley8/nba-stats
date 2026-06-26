#!/usr/bin/env python3
"""Generate basketball app icons (PNG), no third-party deps.
Replicates the header SVG basketball: radial-gradient orange ball, dark rim,
vertical + horizontal seams and two curved Bezier seams with round caps,
on a navy tile. Supersampled for smooth edges."""
import struct, zlib, math

def lerp(a, b, t): return a + (b - a) * t
def mix(c1, c2, t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return tuple(int(round(lerp(c1[i], c2[i], t))) for i in range(3))

# Ball gradient stops (match header: #ff9b4a -> #e8731f @58% -> #bf520f)
def grad(t):
    if t <= 0.58: return mix((255, 155, 74), (232, 115, 31), t / 0.58)
    return mix((232, 115, 31), (191, 82, 15), (t - 0.58) / 0.42)

SEAM = (38, 24, 12)        # #2a1a0a
BG_TOP, BG_BOT = (20, 27, 52), (8, 13, 26)

def render(size, ss=3):
    S = size * ss
    sc = S / 100.0                 # SVG (0-100) units -> pixels
    cx = cy = 50 * sc; R = 47 * sc
    fx, fy, gr = 38.7 * sc, 33.0 * sc, 70.5 * sc  # radial-gradient focal + radius
    sw = 1.5 * sc                  # seam half-width
    ow = 1.4 * sc                  # rim half-width

    buf = []
    for y in range(S):
        row = bytearray()
        for x in range(S):
            d = math.hypot(x - cx, y - cy)
            if d <= R - ow:                       # ball interior
                col = grad(math.hypot(x - fx, y - fy) / gr)
                if abs(x - cx) <= sw or abs(y - cy) <= sw:  # straight seams
                    col = SEAM
            elif d <= R + ow:                     # dark rim outline
                col = SEAM
            else:                                 # navy tile
                col = mix(BG_TOP, BG_BOT, y / S)
            row += bytes(col)
        buf.append(row)

    # Curved seams: stamp round-capped strokes along two quadratic Beziers
    arcs = [((18, 11), (41, 50), (18, 89)), ((82, 11), (59, 50), (82, 89))]
    rad = sw
    for p0, p1, p2 in arcs:
        N = 260
        for i in range(N + 1):
            t = i / N; mt = 1 - t
            bx = (mt*mt*p0[0] + 2*mt*t*p1[0] + t*t*p2[0]) * sc
            by = (mt*mt*p0[1] + 2*mt*t*p1[1] + t*t*p2[1]) * sc
            for yy in range(max(0, int(by - rad)), min(S, int(by + rad) + 1)):
                base = buf[yy]
                for xx in range(max(0, int(bx - rad)), min(S, int(bx + rad) + 1)):
                    if (xx - bx)**2 + (yy - by)**2 <= rad*rad and math.hypot(xx - cx, yy - cy) <= R:
                        p = xx * 3
                        base[p], base[p+1], base[p+2] = SEAM
    return downsample(buf, size, ss)

def downsample(buf, size, ss):
    out = []
    n = ss * ss
    for oy in range(size):
        orow = bytearray()
        for ox in range(size):
            r = g = b = 0
            for j in range(ss):
                base = buf[oy * ss + j]
                for i in range(ss):
                    p = (ox * ss + i) * 3
                    r += base[p]; g += base[p+1]; b += base[p+2]
            orow += bytes((r // n, g // n, b // n))
        out.append(bytes(orow))
    return out

def write_png(path, rows, size):
    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    raw = bytearray()
    for r in rows:
        raw.append(0); raw += r
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))

for sz in (180, 192, 512):
    write_png(f"icon-{sz}.png", render(sz), sz)
    print("wrote", f"icon-{sz}.png")
