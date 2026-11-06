#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import zlib

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)
AMBER = (242, 179, 93)
GREEN = (114, 201, 154)
WHITE = (238, 238, 232)


def cubic(a, b, c, d, t):
    return (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d


def distance_to_segment(x, y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    t = 0 if not length else max(0, min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / length))
    return math.hypot(x - a[0] - t * dx, y - a[1] - t * dy)


def draw(size: int) -> bytes:
    points = []
    for index in range(65):
        t = index / 64
        points.append((0.18 + 0.64 * cubic(0, 0.42, 0.58, 1, t), 0.79 - 0.57 * cubic(0, 0, 1, 1, t)))
    segments = list(zip(points, points[1:]))
    samples = 3 if size <= 128 else 2
    stroke = 0.052 if size < 48 else 0.041
    radius = 0.18
    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            coverage = [0.0, 0.0, 0.0, 0.0]
            for sy in range(samples):
                for sx in range(samples):
                    px = (x + (sx + 0.5) / samples) / size
                    py = (y + (sy + 0.5) / samples) / size
                    qx = max(abs(px - 0.5) - (0.5 - radius), 0)
                    qy = max(abs(py - 0.5) - (0.5 - radius), 0)
                    inside = qx * qx + qy * qy <= radius * radius
                    curve = min(distance_to_segment(px, py, a, b) for a, b in segments) < stroke / 2
                    endpoint = min(math.hypot(px - points[0][0], py - points[0][1]), math.hypot(px - points[-1][0], py - points[-1][1])) < 0.029
                    status = math.hypot(px - 0.78, py - 0.78) < 0.07
                    for channel, color in enumerate(((43, 45, 48), AMBER, WHITE, GREEN)):
                        if (channel == 0 and inside) or (channel == 1 and curve) or (channel == 2 and endpoint) or (channel == 3 and status):
                            coverage[channel] += 1
            alpha = coverage[0] / (samples * samples)
            if not alpha:
                row.extend((0, 0, 0, 0))
                continue
            channel_values = [43, 45, 48]
            for channel, color in ((1, AMBER), (2, WHITE), (3, GREEN)):
                amount = coverage[channel] / (samples * samples)
                for component in range(3):
                    channel_values[component] = round(channel_values[component] * (1 - amount) + color[component] * amount)
            row.extend((*channel_values, round(alpha * 255)))
        rows.append(b'\x00' + bytes(row))
    return rows


def png(size: int) -> bytes:
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    body = b''.join(draw(size))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(body, 9)) + chunk(b'IEND', b'')


def ppm(size: int) -> bytes:
    pixels = bytearray()
    for row in draw(size):
        for index in range(1, len(row), 4):
            pixels.extend(row[index:index + 3])
    return f'P6\n{size} {size}\n255\n'.encode('ascii') + pixels


def make_ico(images: dict[int, bytes]) -> bytes:
    entries = []
    frames = []
    offset = 6 + 16 * len(images)
    for size, data in images.items():
        entries.append(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        frames.append(data)
        offset += len(data)
    return struct.pack('<HHH', 0, 1, len(images)) + b''.join(entries) + b''.join(frames)


def main():
    ASSETS.mkdir(exist_ok=True)
    images = {size: png(size) for size in SIZES}
    manifest = {'format': 'velo-icon-assets', 'files': {}}
    for size, data in images.items():
        path = ASSETS / f'icon{size}.png'
        path.write_bytes(data)
        manifest['files'][path.name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    ppm_data = ppm(32)
    (ASSETS / 'icon32.ppm').write_bytes(ppm_data)
    manifest['files']['icon32.ppm'] = {'bytes': len(ppm_data), 'sha256': hashlib.sha256(ppm_data).hexdigest()}
    ico_sizes = (16, 24, 32, 48, 64, 128, 256)
    ico = make_ico({size: images[size] for size in ico_sizes})
    (ASSETS / 'Velo.ico').write_bytes(ico)
    manifest['files']['Velo.ico'] = {'bytes': len(ico), 'sha256': hashlib.sha256(ico).hexdigest()}
    iconset = ASSETS / 'Velo.iconset'
    iconset.mkdir(exist_ok=True)
    mapping = {
        'icon_16x16.png': 16, 'icon_16x16@2x.png': 32,
        'icon_32x32.png': 32, 'icon_32x32@2x.png': 64,
        'icon_128x128.png': 128, 'icon_128x128@2x.png': 256,
        'icon_256x256.png': 256, 'icon_256x256@2x.png': 512,
        'icon_512x512.png': 512, 'icon_512x512@2x.png': 1024,
    }
    for name, size in mapping.items():
        (iconset / name).write_bytes(images[size])
    if sys.platform == 'darwin':
        subprocess.run(['iconutil', '-c', 'icns', str(iconset), '-o', str(ASSETS / 'Velo.icns')], check=True)
        data = (ASSETS / 'Velo.icns').read_bytes()
        manifest['files']['Velo.icns'] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    (ASSETS / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'sizes': len(images), 'icoBytes': len(ico), 'icns': (ASSETS / 'Velo.icns').exists()}))


if __name__ == '__main__':
    main()
