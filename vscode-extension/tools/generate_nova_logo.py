"""Generate the Marketplace PNG from the existing nova-file.svg branding."""
import struct
import zlib
from pathlib import Path

SIZE = 128
pixels = [(16, 24, 38, 255)] * (SIZE * SIZE)


def set_pixel(x, y, color):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        pixels[y * SIZE + x] = (*color, 255)


def polygon(points, color):
    min_y = max(0, min(y for _, y in points))
    max_y = min(SIZE - 1, max(y for _, y in points))
    for y in range(min_y, max_y + 1):
        intersections = []
        for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
            if y1 == y2:
                continue
            if min(y1, y2) <= y < max(y1, y2):
                intersections.append(round(x1 + (y - y1) * (x2 - x1) / (y2 - y1)))
        intersections.sort()
        for x1, x2 in zip(intersections[::2], intersections[1::2]):
            for x in range(max(0, x1), min(SIZE, x2 + 1)):
                set_pixel(x, y, color)


def circle(cx, cy, radius, color):
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2:
                set_pixel(x, y, color)


# Same shapes/colors as icons/nova-file.svg, scaled from 64 to 128 pixels.
polygon([(26, 6), (78, 6), (102, 30), (102, 120), (18, 120), (18, 14), (26, 6)], (24, 34, 53))
polygon([(78, 6), (78, 30), (102, 30)], (125, 211, 252))
polygon([(64, 36), (72, 56), (92, 64), (72, 72), (64, 92), (56, 72), (36, 64), (56, 56)], (167, 139, 250))
circle(92, 36, 6, (251, 191, 36))


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)


raw = b"".join(b"\0" + bytes(channel for pixel in pixels for channel in pixel) for _ in range(SIZE))
png = (
    b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
    + chunk(b"IDAT", zlib.compress(raw, 9))
    + chunk(b"IEND", b"")
)
Path(__file__).parent.parent.joinpath("icons", "nova-logo.png").write_bytes(png)
