from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent


def verify_assets() -> dict:
    root = ROOT / 'assets'
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('format') != 'velo-icon-assets':
        raise ValueError('Invalid icon asset manifest')
    for name, record in manifest['files'].items():
        data = (root / name).read_bytes()
        if len(data) != record['bytes'] or hashlib.sha256(data).hexdigest() != record['sha256']:
            raise ValueError(f'Icon asset changed: {name}')
        if name.endswith('.png'):
            width, height = struct.unpack('>II', data[16:24])
            if width != height or width != int(name.removeprefix('icon').removesuffix('.png')):
                raise ValueError(f'Unexpected icon dimensions: {name}')
    ico = (root / 'Velo.ico').read_bytes()
    if ico[:4] != b'\x00\x00\x01\x00' or struct.unpack('<H', ico[4:6])[0] != 7:
        raise ValueError('Windows ICO must contain seven independently generated PNG frames')
    expected_offset = 6 + 16 * 7
    for index in range(7):
        width, height, _, _, _, _, size, offset = struct.unpack_from('<BBBBHHII', ico, 6 + index * 16)
        if offset != expected_offset or offset + size > len(ico) or ico[offset:offset + 8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError(f'Invalid Windows ICO frame offset: {index}')
        if struct.unpack('>II', ico[offset + 16:offset + 24]) != (width or 256, height or 256):
            raise ValueError(f'Windows ICO frame dimensions differ: {index}')
        expected_offset += size
    if expected_offset != len(ico):
        raise ValueError('Windows ICO frame data has an invalid length')
    if sys.platform == 'darwin' and (root / 'Velo.icns').read_bytes()[:4] != b'icns':
        raise ValueError('Invalid macOS ICNS resource')
    return manifest
