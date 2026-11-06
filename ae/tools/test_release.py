#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('velo_release', ROOT / 'tools' / 'build_release.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
checks = 0


def check(condition, message):
    global checks
    assert condition, message
    checks += 1
    print(f'ok {checks} - {message}')


with tempfile.TemporaryDirectory(prefix='velo-release-test-') as temporary:
    directory = Path(temporary)
    first = directory / 'VeloAE_test_macOS_Windows.zip'
    second = directory / 'VeloAE_test_rebuilt.zip'
    report = builder.build_release(first, allow_dirty=True, source_date_epoch=1767225600)
    rebuilt = builder.build_release(second, allow_dirty=True, source_date_epoch=1767225600)
    expected = sorted([f'com.velo.curveeditor/{name}' for name in builder.PANEL_FILES] + list(builder.GUIDE_FILES))
    check(report['version'] == '1.2.1', 'release version is synchronized across the manifest and host')
    check(report['sha256'] == rebuilt['sha256'] and first.read_bytes() == second.read_bytes(), 'identical source and timestamp produce an identical ZIP')
    check(report['sourceDirty'] == rebuilt['sourceDirty'], 'build reports the actual reviewed-source state')
    with zipfile.ZipFile(first) as archive:
        check(archive.testzip() is None, 'ZIP CRC validation passes')
        check(archive.namelist() == expected, 'archive contains only the explicit panel and offline-guide whitelist')
        check(all('\\' not in name and not name.startswith('/') and '..' not in Path(name).parts for name in archive.namelist()), 'archive paths are portable and cannot escape the destination')
        manifest = archive.read('com.velo.curveeditor/CSXS/manifest.xml').decode('utf-8')
        check(manifest.count('1.2.1') == 2, 'both bundled manifest versions are correct')
        check(archive.read('README.md') == (ROOT / 'packaging' / 'README.md').read_bytes(), 'offline Chinese guide matches the reviewed bytes')
        check(archive.read('README.en.md') == (ROOT / 'packaging' / 'README.en.md').read_bytes(), 'offline English guide matches the reviewed bytes')
        check(all(not name.endswith(('.debug', '.pyc', '.log')) and 'private/' not in name for name in archive.namelist()), 'debug files, private verification and logs are excluded')
    check(hashlib.sha256(first.read_bytes()).hexdigest() == report['sha256'], 'SHA-256 is calculated from the actual final ZIP')
    manifest_path = first.with_suffix('.manifest.json')
    recorded = json.loads(manifest_path.read_text(encoding='utf-8'))
    check(recorded['bytes'] == first.stat().st_size and recorded['files'], 'final size and per-file hashes are recorded')
    checksums = first.parent / 'VeloAE_v1.2.1_SHA256SUMS.txt'
    check(checksums.read_text(encoding='utf-8').strip() == f'{rebuilt["sha256"]}  {second.name}', 'external checksum points to the latest validated ZIP filename')
    for guide in ('README.md', 'README.en.md'):
        builder.validate_guide(ROOT / 'packaging' / guide)
    check(True, 'offline cross-language and third-party links resolve')
    previous = first.read_bytes()
    with patch.object(builder, 'GUIDES', directory / 'missing-guides'):
        try:
            builder.build_release(first, allow_dirty=True, source_date_epoch=1767225600)
        except ValueError:
            pass
        else:
            raise AssertionError('Missing guides must reject the candidate')
    check(first.read_bytes() == previous and not list(directory.glob('*.candidate')), 'a failed candidate preserves the previous valid ZIP and leaves no candidate')

print(f'1..{checks}')
