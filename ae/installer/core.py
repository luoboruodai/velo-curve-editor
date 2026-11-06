from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from datetime import datetime, timezone
import uuid
import xml.etree.ElementTree as ET

BUNDLE_ID = 'com.velo.curveeditor'
VERSION = '1.2.1'
BACKUP_DIR = 'Velo-backup'


class InstallError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def file_hashes(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise InstallError(f'Links are not accepted: {path}')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = sha256(path)
        elif not path.is_dir():
            raise InstallError(f'Unsupported file type: {path}')
    return result


def default_extensions_dir(platform: str | None = None, home: Path | None = None) -> Path:
    home = home or Path.home()
    platform = platform or os.name
    if platform == 'nt':
        return Path(os.environ.get('APPDATA', home / 'AppData' / 'Roaming')) / 'Adobe' / 'CEP' / 'extensions'
    return home / 'Library' / 'Application Support' / 'Adobe' / 'CEP' / 'extensions'


def safe_destination(root: Path) -> Path:
    root = Path(root).expanduser()
    if root.is_symlink():
        raise InstallError(f'Installation path cannot be a link: {root}')
    root = root.resolve()
    target = root / BUNDLE_ID
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise InstallError(f'Invalid extension destination: {target}')
    return target


def verify_payload(root: Path) -> dict:
    root = Path(root)
    if root.is_symlink():
        raise InstallError('Payload cannot be a link.')
    try:
        manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise InstallError(f'Cannot read the payload manifest: {error}') from error
    if manifest.get('format') != 'velo-installer-payload' or manifest.get('version') != VERSION:
        raise InstallError('The payload version or format is not supported.')
    expected = manifest.get('files')
    documents = manifest.get('documents')
    if not isinstance(expected, dict) or not expected or not isinstance(documents, dict):
        raise InstallError('Payload file or document declarations are missing.')
    panel = root / BUNDLE_ID
    if not panel.is_dir() or panel.is_symlink():
        raise InstallError('The bundled panel is missing or linked.')
    for relative, checksum in expected.items():
        validate_relative(relative)
        path = panel / PurePosixPath(relative)
        if not path.is_file() or path.is_symlink() or sha256(path) != checksum:
            raise InstallError(f'Payload checksum failed: {relative}')
    for relative, checksum in documents.items():
        validate_relative(relative)
        path = root / 'guides' / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != checksum:
            raise InstallError(f'Guide checksum failed: {relative}')
    actual = file_hashes(panel)
    if actual != expected:
        raise InstallError('The payload contains missing or unexpected panel files.')
    guide_actual = file_hashes(root / 'guides')
    if guide_actual != documents:
        raise InstallError('The payload contains missing or unexpected guide files.')
    try:
        bundled = ET.parse(panel / 'CSXS' / 'manifest.xml').getroot()
    except (OSError, ET.ParseError) as error:
        raise InstallError(f'Invalid panel manifest: {error}') from error
    if bundled.attrib.get('ExtensionBundleId') != BUNDLE_ID or bundled.attrib.get('ExtensionBundleVersion') != VERSION:
        raise InstallError('The bundled CEP identity does not match this installer.')
    if bundled.find('./ExtensionList/Extension').attrib.get('Version') != VERSION:
        raise InstallError('The bundled extension version does not match.')
    if (panel / '.debug').exists():
        raise InstallError('Debug configuration must not be distributed.')
    return manifest


def validate_relative(relative: str) -> None:
    path = PurePosixPath(relative)
    if not isinstance(relative, str) or path.is_absolute() or '..' in path.parts or '\\' in relative:
        raise InstallError(f'Unsafe payload path: {relative}')


def installed_version(target: Path) -> str | None:
    try:
        return ET.parse(target / 'CSXS' / 'manifest.xml').getroot().attrib.get('ExtensionBundleVersion')
    except (OSError, ET.ParseError):
        return None


def backup_manifest(target: Path) -> dict:
    return {
        'format': 'velo-installer-backup',
        'backupFormat': 1,
        'bundle': BUNDLE_ID,
        'sourceVersion': installed_version(target),
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'files': file_hashes(target),
    }


def new_backup_dir(root: Path) -> Path:
    if (root / BACKUP_DIR).is_symlink():
        raise InstallError('Backup directory cannot be a link.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    return root / BACKUP_DIR / f'{stamp}-{uuid.uuid4().hex[:8]}'


def replace_panel(candidate: Path, root: Path, backup: bool) -> Path | None:
    target = safe_destination(root)
    previous = None
    backup_dir = None
    if target.exists():
        if backup:
            backup_dir = new_backup_dir(root)
            backup_dir.mkdir(parents=True, exist_ok=False)
            manifest = backup_manifest(target)
            os.replace(target, backup_dir / BUNDLE_ID)
            (backup_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            previous = backup_dir / BUNDLE_ID
        else:
            previous = target.parent / f'.{BUNDLE_ID}.previous-{uuid.uuid4().hex}'
            os.replace(target, previous)
    try:
        os.replace(candidate, target)
        if installed_version(target) != VERSION:
            raise InstallError('Installed version differs from the payload.')
        if (target / '.debug').exists():
            raise InstallError('A debug file was found after installation.')
    except Exception:
        if target.exists():
            shutil.rmtree(target)
        if previous and previous.exists():
            os.replace(previous, target)
        raise
    if previous and not backup and previous.exists():
        shutil.rmtree(previous)
    return backup_dir


def install_panel(payload: Path, root: Path, backup: bool = True) -> dict:
    verify_payload(Path(payload))
    root = Path(root).expanduser()
    target = safe_destination(root)
    root.mkdir(parents=True, exist_ok=True)
    transaction = Path(tempfile.mkdtemp(prefix='.velo-install-', dir=root))
    try:
        candidate = transaction / BUNDLE_ID
        shutil.copytree(Path(payload) / BUNDLE_ID, candidate)
        if file_hashes(candidate) != file_hashes(Path(payload) / BUNDLE_ID):
            raise InstallError('Staged panel files differ from the payload.')
        backup_dir = replace_panel(candidate, root, backup)
        return {
            'action': 'install',
            'version': VERSION,
            'target': str(target),
            'backup': str(backup_dir) if backup_dir else None,
            'files': file_hashes(target),
            'settingsPreserved': True,
            'requiresRestart': True,
        }
    finally:
        shutil.rmtree(transaction, ignore_errors=True)


def list_backups(root: Path) -> list[dict]:
    backup_root = Path(root) / BACKUP_DIR
    if not backup_root.is_dir() or backup_root.is_symlink():
        return []
    result = []
    for directory in backup_root.iterdir():
        if directory.is_symlink() or not directory.is_dir():
            continue
        try:
            manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
            if manifest.get('format') == 'velo-installer-backup' and manifest.get('bundle') == BUNDLE_ID:
                result.append({'path': str(directory), **manifest})
        except (OSError, ValueError):
            continue
    return sorted(result, key=lambda item: item['createdAt'], reverse=True)


def verify_backup(root: Path, directory: Path) -> dict:
    backup_root = Path(root) / BACKUP_DIR
    directory = Path(directory)
    if backup_root.is_symlink() or directory.is_symlink():
        raise InstallError('Backup paths cannot be links.')
    backup_root = backup_root.resolve()
    directory = directory.resolve()
    if directory.parent != backup_root:
        raise InstallError('Select a backup inside this installation’s Velo-backup directory.')
    try:
        manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise InstallError(f'Cannot read backup metadata: {error}') from error
    if manifest.get('format') != 'velo-installer-backup' or manifest.get('bundle') != BUNDLE_ID:
        raise InstallError('This is not a Velo backup.')
    expected = manifest.get('files')
    if not isinstance(expected, dict) or not expected:
        raise InstallError('The backup has no file manifest.')
    panel = directory / BUNDLE_ID
    if file_hashes(panel) != expected:
        raise InstallError('The backup is incomplete or its contents have changed.')
    return manifest


def restore_backup(root: Path, directory: Path, backup: bool = True) -> dict:
    root = Path(root).expanduser()
    manifest = verify_backup(root, Path(directory))
    safe_destination(root)
    transaction = Path(tempfile.mkdtemp(prefix='.velo-restore-', dir=root))
    try:
        candidate = transaction / BUNDLE_ID
        shutil.copytree(Path(directory) / BUNDLE_ID, candidate)
        if file_hashes(candidate) != manifest['files']:
            raise InstallError('Staged backup files differ from the backup manifest.')
        current_backup = replace_panel(candidate, root, backup)
        return {
            'action': 'restore',
            'version': installed_version(root / BUNDLE_ID),
            'target': str(root / BUNDLE_ID),
            'backup': str(current_backup) if current_backup else None,
            'restoredFrom': str(directory),
            'files': file_hashes(root / BUNDLE_ID),
            'settingsPreserved': True,
            'requiresRestart': True,
        }
    finally:
        shutil.rmtree(transaction, ignore_errors=True)
