#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / 'ae' / 'VeloAE'
GUIDES = ROOT / 'ae' / 'packaging'
PANEL_FILES = (
    'CSXS/manifest.xml',
    'css/style.css',
    'index.html',
    'js/CSInterface.js',
    'js/curve-model.js',
    'js/i18n.js',
    'js/main.js',
    'js/theme.js',
    'jsx/hostscript.jsx',
)
GUIDE_FILES = ('README.md', 'README.en.md', 'THIRD_PARTY_NOTICES.md')
LINK = re.compile(r'!?\[[^\]]*\]\(([^)]+)\)')
FORBIDDEN = re.compile(r'/Users/|/home/|private/verification|\.kimi-code|BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]|github_pat_')


def version_info():
    root = ET.parse(PANEL / 'CSXS' / 'manifest.xml').getroot()
    bundle = root.attrib['ExtensionBundleVersion']
    extension = root.find('./ExtensionList/Extension').attrib['Version']
    host = re.search(r'var VERSION = "([^"]+)"', (PANEL / 'jsx' / 'hostscript.jsx').read_text(encoding='utf-8'))
    if not host or bundle != extension or bundle != host.group(1):
        raise ValueError(f'Version mismatch: bundle={bundle}, extension={extension}, host={host.group(1) if host else None}')
    if not re.fullmatch(r'\d+\.\d+\.\d+', bundle):
        raise ValueError(f'Invalid release version: {bundle}')
    return bundle


def dirty_source():
    paths = ['ae/VeloAE', 'ae/packaging', 'ae/tools/build_release.py']
    result = subprocess.run(['git', 'status', '--porcelain', '--', *paths], cwd=ROOT, check=True, capture_output=True, text=True)
    return bool(result.stdout.strip())


def commit_epoch():
    result = subprocess.run(['git', 'log', '-1', '--format=%ct'], cwd=ROOT, check=True, capture_output=True, text=True)
    return int(result.stdout.strip())


def validate_guide(path):
    text = path.read_text(encoding='utf-8')
    for target in LINK.findall(text):
        if target.startswith(('https://', 'http://', 'mailto:', '#')):
            continue
        relative = unquote(target.split('#', 1)[0])
        if not relative or PurePosixPath(relative).is_absolute() or '..' in PurePosixPath(relative).parts:
            raise ValueError(f'Non-local guide link in {path.name}: {target}')
        if not (path.parent / relative).is_file():
            raise ValueError(f'Missing guide link target in {path.name}: {target}')


def payload(version):
    entries = {}
    for relative in PANEL_FILES:
        path = PANEL / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f'Missing or linked panel file: {relative}')
        entries[f'com.velo.curveeditor/{relative}'] = path.read_bytes()
    for name in GUIDE_FILES:
        path = GUIDES / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f'Missing or linked guide: {name}')
        validate_guide(path)
        text = path.read_text(encoding='utf-8')
        if name != 'THIRD_PARTY_NOTICES.md' and f'Velo {version}' not in text:
            raise ValueError(f'Guide version differs from manifest: {name}')
        entries[name] = path.read_bytes()
    for name, data in entries.items():
        if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or '\\' in name:
            raise ValueError(f'Unsafe archive path: {name}')
        if FORBIDDEN.search(data.decode('utf-8', errors='ignore')):
            raise ValueError(f'Private or credential-like content in {name}')
    return entries


def zip_info(name, epoch):
    info = zipfile.ZipInfo(name, time.gmtime(max(315532800, min(epoch, 4354819198)))[:6])
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 0
    info.external_attr = 0o100644 << 16
    return info


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build_release(output, allow_dirty=False, source_date_epoch=None):
    version = version_info()
    dirty = dirty_source()
    if dirty and not allow_dirty:
        raise RuntimeError('Release sources are modified or untracked; commit the reviewed sources before building')
    if source_date_epoch is not None:
        epoch = source_date_epoch
    elif os.environ.get('SOURCE_DATE_EPOCH'):
        epoch = int(os.environ['SOURCE_DATE_EPOCH'])
    else:
        epoch = commit_epoch()
    entries = payload(version)
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f'.{output.name}.', suffix='.candidate', dir=output.parent)
    os.close(descriptor)
    candidate = Path(temporary)
    try:
        with zipfile.ZipFile(candidate, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in sorted(entries):
                archive.writestr(zip_info(name, epoch), entries[name])
        with zipfile.ZipFile(candidate) as archive:
            if archive.testzip() is not None:
                raise ValueError('ZIP CRC validation failed')
            if archive.namelist() != sorted(entries):
                raise ValueError('Archive members differ from the whitelist')
            for name, expected in entries.items():
                if archive.read(name) != expected:
                    raise ValueError(f'Archive payload differs: {name}')
            bundled = ET.fromstring(archive.read('com.velo.curveeditor/CSXS/manifest.xml'))
            if bundled.attrib['ExtensionBundleVersion'] != version or bundled.find('./ExtensionList/Extension').attrib['Version'] != version:
                raise ValueError('Bundled manifest version differs')
        archive_bytes = candidate.read_bytes()
        digest = sha(archive_bytes)
        candidate.replace(output)
        report = {
            'version': version,
            'archive': output.name,
            'bytes': len(archive_bytes),
            'sha256': digest,
            'sourceDateEpoch': epoch,
            'sourceDirty': dirty,
            'compression': 'ZIP_DEFLATED level 9',
            'validation': ['whitelist', 'payload-bytes', 'crc', 'manifest-version', 'offline-links', 'portable-paths', 'content-scan'],
            'files': [{'path': name, 'bytes': len(entries[name]), 'sha256': sha(entries[name])} for name in sorted(entries)],
        }
        report_path = output.with_suffix('.manifest.json')
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        checksums_path = output.parent / f'VeloAE_v{version}_SHA256SUMS.txt'
        checksums_path.write_text(f'{digest}  {output.name}\n', encoding='utf-8')
        return report
    except Exception:
        candidate.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description='Build and validate the portable Velo AE release ZIP')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--allow-dirty', action='store_true')
    parser.add_argument('--source-date-epoch', type=int)
    args = parser.parse_args()
    version = version_info()
    output = args.output or ROOT / 'dist' / f'VeloAE_v{version}_macOS_Windows.zip'
    report = build_release(output, allow_dirty=args.allow_dirty, source_date_epoch=args.source_date_epoch)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
