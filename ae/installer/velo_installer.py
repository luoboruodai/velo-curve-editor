#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from ae.installer.core import (
    InstallError,
    default_extensions_dir,
    install_panel,
    list_backups,
    restore_backup,
    verify_payload,
)


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    candidate = base / relative
    if relative == 'payload' and candidate.is_symlink() and os.readlink(candidate) == '../Resources/payload':
        return candidate.resolve()
    return candidate


def write_report(path: Path | None, report: dict) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.candidate')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def enable_debug_preference(version: str) -> None:
    if version not in {'7', '8', '9', '10', '11', '12'}:
        raise InstallError('Unsupported CSXS major version.')
    if os.name == 'nt':
        command = ['reg', 'add', rf'HKCU\Software\Adobe\CSXS.{version}', '/v', 'PlayerDebugMode', '/t', 'REG_SZ', '/d', '1', '/f']
    else:
        command = ['defaults', 'write', f'com.adobe.CSXS.{version}', 'PlayerDebugMode', '1']
    result = subprocess.run(command, capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise InstallError(f'Could not enable the local CEP panel preference: {result.stderr.strip()}')


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description='Velo AE offline installer with verified backup and rollback')
    result.add_argument('--cli', action='store_true', help='Run without starting the native UI')
    result.add_argument('--payload', type=Path, default=resource_path('payload'))
    result.add_argument('--target', type=Path, default=None, help='CEP extensions directory, not the panel directory itself')
    result.add_argument('--no-backup', action='store_true', help='Replace the old panel without keeping a backup')
    result.add_argument('--restore', type=Path, default=None, help='Restore a named backup from Velo-backup')
    result.add_argument('--yes', action='store_true', help='Confirm replacement during command-line restore')
    result.add_argument('--list-backups', action='store_true')
    result.add_argument('--check', action='store_true', help='Verify the embedded payload without installing')
    result.add_argument('--debug-csxs', choices=['7', '8', '9', '10', '11', '12'], default=None)
    result.add_argument('--report', type=Path, default=None)
    return result


def main() -> int:
    args = parser().parse_args()
    root = args.target or default_extensions_dir()
    try:
        if args.list_backups:
            report = {'action': 'list', 'backups': list_backups(root)}
        elif args.check:
            manifest = verify_payload(args.payload)
            report = {'action': 'check', 'version': manifest['version'], 'valid': True}
        elif args.restore:
            if not args.yes:
                raise InstallError('Restoring replaces the current panel. Add --yes to confirm.')
            report = restore_backup(root, args.restore, backup=not args.no_backup)
        else:
            report = install_panel(args.payload, root, backup=not args.no_backup)
        if args.debug_csxs:
            enable_debug_preference(args.debug_csxs)
            report['debugCsxs'] = args.debug_csxs
        report['ok'] = True
        write_report(args.report, report)
        if args.cli:
            print(json.dumps(report, ensure_ascii=False))
        else:
            from ae.installer.ui import launch
            launch(args.payload, root, not args.no_backup)
        return 0
    except (InstallError, OSError, ValueError) as error:
        report = {'ok': False, 'error': str(error), 'target': str(root)}
        write_report(args.report, report)
        if args.cli:
            print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        else:
            from ae.installer.ui import show_error
            show_error(str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
