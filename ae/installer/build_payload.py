#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ae.installer.core import BUNDLE_ID, VERSION, verify_payload
from ae.tools import build_release


def build_payload(destination: Path) -> dict:
    version = build_release.version_info()
    if version != VERSION:
        raise ValueError(f'Installer version {VERSION} does not match panel {version}')
    entries = build_release.payload(version)
    files = {
        name.removeprefix(f'{BUNDLE_ID}/'): hashlib.sha256(data).hexdigest()
        for name, data in entries.items() if name.startswith(f'{BUNDLE_ID}/')
    }
    documents = {
        name: hashlib.sha256(entries[name]).hexdigest()
        for name in build_release.GUIDE_FILES
    }
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    candidate = Path(tempfile.mkdtemp(prefix='.velo-payload-', dir=destination.parent))
    previous = None
    try:
        for name, data in entries.items():
            path = candidate / name if name.startswith(f'{BUNDLE_ID}/') else candidate / 'guides' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        manifest = {
            'format': 'velo-installer-payload',
            'product': 'Velo AE',
            'version': version,
            'files': files,
            'documents': documents,
        }
        (candidate / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        verify_payload(candidate)
        if destination.exists():
            previous = Path(tempfile.mkdtemp(prefix='.velo-payload-previous-', dir=destination.parent)) / 'payload'
            os.replace(destination, previous)
        os.replace(candidate, destination)
        if previous:
            shutil.rmtree(previous.parent)
        return manifest
    finally:
        shutil.rmtree(candidate, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description='Embed the reviewed Velo AE panel in the offline installer')
    parser.add_argument('--output', type=Path, default=ROOT / 'ae' / 'installer' / 'payload')
    args = parser.parse_args()
    manifest = build_payload(args.output)
    print(json.dumps({'version': manifest['version'], 'files': len(manifest['files']), 'documents': len(manifest['documents'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
