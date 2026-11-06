#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ae.installer.build_payload import build_payload
from ae.installer.core import VERSION, verify_payload
from ae.installer.verify_assets import verify_assets

INSTALLER = ROOT / 'ae' / 'installer'
DIST = ROOT / 'dist'


def source_dirty() -> bool:
    result = subprocess.run(['git', 'status', '--porcelain', '--', 'ae/VeloAE', 'ae/packaging', 'ae/installer'], cwd=ROOT, check=True, capture_output=True, text=True)
    return bool(result.stdout.strip())


def set_mac_version(app: Path) -> None:
    path = app / 'Contents' / 'Info.plist'
    metadata = plistlib.loads(path.read_bytes())
    metadata['CFBundleShortVersionString'] = VERSION
    metadata['CFBundleVersion'] = VERSION
    path.write_bytes(plistlib.dumps(metadata, sort_keys=False))


def windows_version_text() -> str:
    version = tuple(int(part) for part in VERSION.split('.')) + (0,)
    return f'''VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version}, prodvers={version}, mask=0x3f, flags=0x0,
    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)
  ),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('FileDescription', 'Velo AE Offline Installer'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', 'VeloInstaller'),
      StringStruct('OriginalFilename', 'VeloInstaller.exe'),
      StringStruct('ProductName', 'Velo Installer'),
      StringStruct('ProductVersion', '{VERSION}')
    ])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
'''


def verify_windows_version(executable: Path) -> None:
    import pefile
    pe = pefile.PE(str(executable))
    expected = tuple(int(part) for part in VERSION.split('.')) + (0,)
    fixed = pe.VS_FIXEDFILEINFO[0]
    file_version = (fixed.FileVersionMS >> 16, fixed.FileVersionMS & 0xffff, fixed.FileVersionLS >> 16, fixed.FileVersionLS & 0xffff)
    product_version = (fixed.ProductVersionMS >> 16, fixed.ProductVersionMS & 0xffff, fixed.ProductVersionLS >> 16, fixed.ProductVersionLS & 0xffff)
    if file_version != expected or product_version != expected:
        raise RuntimeError(f'Windows binary version differs: {file_version} / {product_version}')
    strings = {}
    for group in pe.FileInfo:
        for info in group:
            if getattr(info, 'name', None) in (b'StringFileInfo', 'StringFileInfo'):
                for table in info.StringTable:
                    strings.update({key.decode('utf-8'): value.decode('utf-8') for key, value in table.entries.items()})
    if strings.get('FileVersion') != VERSION or strings.get('ProductVersion') != VERSION:
        raise RuntimeError('Windows version strings differ from the release')


def verify_public_archive(path: Path) -> None:
    forbidden = (b'/Users/user/', b'/Users/vibecoding_prj/', b'private/verification', b'.kimi-code', b'ghp_', b'github_pat_', b'BEGIN PRIVATE KEY', b'BEGIN RSA PRIVATE KEY', b'BEGIN OPENSSH PRIVATE KEY')
    if path.suffix == '.zip':
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                data = archive.read(name)
                if any(marker in data for marker in forbidden):
                    raise RuntimeError(f'Private path or credential-like content in {name}')
    elif any(marker in path.read_bytes() for marker in forbidden):
        raise RuntimeError('Private path or credential-like content in executable')


def app_members(app: Path) -> dict:
    members = {}
    for directory, directories, files in os.walk(app, followlinks=False):
        for name in sorted(directories + files):
            path = Path(directory) / name
            relative = path.relative_to(app.parent).as_posix()
            if path.is_symlink():
                members[relative] = ('link', os.readlink(path), 0o777)
            elif path.is_file():
                members[relative] = ('file', path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
            elif path.is_dir():
                continue
            else:
                raise RuntimeError(f'Unsupported app member: {relative}')
    return members


def verify_mac_archive(app: Path, archive_path: Path) -> None:
    expected = app_members(app)
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('macOS app ZIP failed its CRC check')
        if set(archive.namelist()) != set(expected):
            raise RuntimeError('App ZIP members differ from the native bundle, including directory links')
        for name, (kind, content, mode) in expected.items():
            if name.startswith('/') or '..' in Path(name).parts or '._' in name or '.DS_Store' in name:
                raise RuntimeError(f'Unsafe or unexpected archive member: {name}')
            info = archive.getinfo(name)
            if kind == 'link':
                if stat.S_IFMT(info.external_attr >> 16) != stat.S_IFLNK or archive.read(name).decode('utf-8') != content:
                    raise RuntimeError(f'App link differs: {name}')
            elif archive.read(name) != content or stat.S_IMODE(info.external_attr >> 16) != mode:
                raise RuntimeError(f'App file bytes or permissions differ: {name}')
    extraction = Path(tempfile.mkdtemp(prefix='.velo-app-verify-', dir=archive_path.parent))
    try:
        subprocess.run(['/usr/bin/unzip', '-q', str(archive_path), '-d', str(extraction)], check=True, timeout=120)
        bundle_root = extraction / app.name
        for name, (kind, content, mode) in expected.items():
            if kind == 'link' and os.readlink(extraction / name) != content:
                raise RuntimeError(f'Extracted link target differs: {name}')
        verify_payload(bundle_root / 'Contents' / 'Resources' / 'payload')
        metadata = plistlib.loads((bundle_root / 'Contents' / 'Info.plist').read_bytes())
        if metadata.get('CFBundleShortVersionString') != VERSION or metadata.get('CFBundleVersion') != VERSION:
            raise RuntimeError('Extracted app bundle version differs from the release')
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(bundle_root)], check=True, timeout=120)
        if not (bundle_root / 'Contents' / 'MacOS' / 'VeloInstaller').stat().st_mode & stat.S_IXUSR:
            raise RuntimeError('Extracted app launcher is not executable')
    finally:
        shutil.rmtree(extraction, ignore_errors=True)


def mac_archive(app: Path, destination: Path) -> None:
    temporary = destination.with_suffix('.candidate')
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative, (kind, content, mode) in app_members(app).items():
                info = zipfile.ZipInfo(relative)
                info.create_system = 3
                if kind == 'link':
                    info.external_attr = (stat.S_IFLNK | mode) << 16
                    info.compress_type = zipfile.ZIP_STORED
                    archive.writestr(info, content)
                else:
                    info.external_attr = (stat.S_IFREG | mode) << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(info, content)
        verify_mac_archive(app, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def build(platform: str, python: str) -> dict:
    verify_assets()
    build_payload(INSTALLER / 'payload')
    if platform not in {'macos', 'windows'}:
        raise ValueError('Native installer packages must be built on macOS or Windows')
    expected = 'darwin' if platform == 'macos' else 'nt'
    if (sys.platform == 'darwin') != (expected == 'darwin'):
        raise RuntimeError(f'{platform} installer must be built on its native platform, not cross-compiled')
    build_root = DIST / 'installer-build'
    build_root.mkdir(parents=True, exist_ok=True)
    candidate = Path(tempfile.mkdtemp(prefix='.velo-installer-build-', dir=build_root))
    dist = candidate / 'dist'
    work = candidate / 'work'
    spec = candidate / 'spec'
    for directory in (dist, work, spec):
        directory.mkdir(parents=True, exist_ok=True)
    command = [
        python, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir' if platform == 'macos' else '--onefile', '--windowed',
        '--name', 'VeloInstaller', '--distpath', str(dist), '--workpath', str(work), '--specpath', str(spec),
        '--paths', str(ROOT),
        '--add-data', f'{INSTALLER / "payload"}{os.pathsep}payload',
        '--add-data', f'{INSTALLER / "assets"}{os.pathsep}assets',
        '--icon', str(INSTALLER / 'assets' / ('Velo.icns' if platform == 'macos' else 'Velo.ico')),
    ]
    if platform == 'macos':
        command += ['--osx-bundle-identifier', 'com.velo.installer']
    else:
        version_path = work / 'version.txt'
        version_path.write_text(windows_version_text(), encoding='utf-8')
        command += ['--version-file', str(version_path)]
    command.append(str(INSTALLER / 'velo_installer.py'))
    environment = os.environ.copy()
    environment['PYTHONPATH'] = str(ROOT)
    subprocess.run(command, cwd=ROOT, env=environment, check=True, timeout=600)
    executable = dist / ('VeloInstaller.exe' if platform == 'windows' else 'VeloInstaller/VeloInstaller')
    app = dist / 'VeloInstaller.app'
    if not executable.is_file():
        raise RuntimeError('Native executable was not generated')
    if platform == 'macos':
        if not app.is_dir():
            raise RuntimeError('macOS app bundle was not generated')
        set_mac_version(app)
        subprocess.run(['codesign', '--deep', '--force', '--sign', '-', str(app)], check=True, timeout=120)
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True, timeout=120)
        verify_payload(app / 'Contents' / 'Resources' / 'payload')
    else:
        verify_windows_version(executable)
    smoke = candidate / 'smoke'
    smoke.mkdir()
    report_path = smoke / 'report.json'
    subprocess.run([
        str(executable), '--cli', '--target', str(smoke / 'extensions'), '--report', str(report_path),
    ], cwd=smoke, check=True, timeout=120)
    smoke_report = json.loads(report_path.read_text(encoding='utf-8'))
    if not smoke_report.get('ok') or smoke_report.get('version') != VERSION:
        raise RuntimeError(f'Native installer smoke test failed: {smoke_report}')
    if not (smoke / 'extensions' / 'com.velo.curveeditor' / 'index.html').is_file():
        raise RuntimeError('Native installer did not install its embedded panel')
    if platform == 'windows':
        artifact = DIST / f'VeloInstaller_v{VERSION}_Windows.exe'
        candidate_artifact = artifact.with_suffix('.candidate')
        try:
            shutil.copyfile(executable, candidate_artifact)
            os.replace(candidate_artifact, artifact)
        finally:
            candidate_artifact.unlink(missing_ok=True)
    else:
        artifact = DIST / f'VeloInstaller_v{VERSION}_macOS.zip'
        mac_archive(app, artifact)
    verify_public_archive(artifact)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    report = {
        'product': 'Velo Installer',
        'version': VERSION,
        'platform': platform,
        'artifact': artifact.name,
        'bytes': artifact.stat().st_size,
        'sha256': digest,
        'sourceDirty': source_dirty(),
        'python': sys.version.split()[0],
        'packager': 'PyInstaller==6.16.0',
        'nativeExecutableSmoke': {key: smoke_report[key] for key in ('action', 'version', 'ok', 'settingsPreserved', 'requiresRestart')},
        'validation': ['icon-manifest', 'payload-hash', 'platform-version-metadata', 'native-build', 'native-cli-install', 'bundle-signature'] if platform == 'macos' else ['icon-manifest', 'payload-hash', 'platform-version-metadata', 'native-build', 'native-cli-install'],
        'nativeUiVerified': False,
    }
    (DIST / f'VeloInstaller_v{VERSION}_{platform}.manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (DIST / f'VeloInstaller_v{VERSION}_{platform}_SHA256SUMS.txt').write_text(f'{digest}  {artifact.name}\n', encoding='utf-8')
    shutil.rmtree(candidate, ignore_errors=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description='Build a native Velo installer on its target platform')
    parser.add_argument('--platform', choices=['macos', 'windows'], default='macos' if sys.platform == 'darwin' else 'windows')
    parser.add_argument('--python', default=sys.executable)
    args = parser.parse_args()
    print(json.dumps(build(args.platform, args.python), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
