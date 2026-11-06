from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from ae.installer.build_payload import build_payload
from ae.installer.core import (
    BUNDLE_ID,
    InstallError,
    default_extensions_dir,
    file_hashes,
    install_panel,
    list_backups,
    restore_backup,
    verify_backup,
    verify_payload,
)

ROOT = Path(__file__).resolve().parents[3]


class InstallerCoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='velo-installer-test-')
        self.root = Path(self.temporary.name) / 'extensions'
        self.payload = Path(self.temporary.name) / 'payload'
        build_payload(self.payload)
        self.target = self.root / BUNDLE_ID

    def tearDown(self):
        self.temporary.cleanup()

    def test_reviewed_payload_is_valid(self):
        manifest = verify_payload(self.payload)
        self.assertEqual(manifest['version'], '1.2.1')
        self.assertEqual(len(manifest['files']), 9)
        self.assertEqual(len(manifest['documents']), 3)

    def test_first_install(self):
        report = install_panel(self.payload, self.root)
        self.assertTrue(report['ok'] if 'ok' in report else True)
        self.assertEqual(report['version'], '1.2.1')
        self.assertIsNone(report['backup'])
        self.assertTrue((self.target / 'index.html').is_file())
        self.assertFalse((self.target / '.debug').exists())
        self.assertTrue(report['settingsPreserved'])

    def test_upgrade_has_complete_backup_and_preserves_external_preferences(self):
        install_panel(self.payload, self.root)
        custom = self.target / 'legacy-custom.txt'
        custom.write_text('keep this legacy file', encoding='utf-8')
        preferences = self.root / 'preferences.json'
        preferences.write_text('{"theme":"amber"}', encoding='utf-8')
        before = file_hashes(self.target)
        report = install_panel(self.payload, self.root)
        backup = Path(report['backup'])
        self.assertEqual(file_hashes(backup / BUNDLE_ID), before)
        self.assertEqual(verify_backup(self.root, backup)['sourceVersion'], '1.2.1')
        self.assertEqual(preferences.read_text(encoding='utf-8'), '{"theme":"amber"}')
        self.assertEqual(len(list_backups(self.root)), 1)

    def test_tampered_payload_does_not_touch_existing_installation(self):
        install_panel(self.payload, self.root)
        before = file_hashes(self.target)
        (self.payload / BUNDLE_ID / 'index.html').write_text('<html>tampered</html>', encoding='utf-8')
        with self.assertRaises(InstallError):
            install_panel(self.payload, self.root)
        self.assertEqual(file_hashes(self.target), before)

    def test_unexpected_payload_member_is_rejected(self):
        (self.payload / BUNDLE_ID / 'unexpected.txt').write_text('unexpected', encoding='utf-8')
        with self.assertRaises(InstallError):
            verify_payload(self.payload)

    def test_debug_file_is_rejected(self):
        (self.payload / BUNDLE_ID / '.debug').write_text('<ExtensionList/>', encoding='utf-8')
        with self.assertRaises(InstallError):
            verify_payload(self.payload)

    def test_replace_failure_rolls_back_and_cleans_staging(self):
        install_panel(self.payload, self.root)
        before = file_hashes(self.target)
        original_replace = os.replace
        failed = False

        def fail_candidate(source, destination):
            nonlocal failed
            if '.velo-install-' in str(source) and not failed:
                failed = True
                raise OSError('simulated locked destination')
            return original_replace(source, destination)

        with patch('ae.installer.core.os.replace', side_effect=fail_candidate):
            with self.assertRaises(OSError):
                install_panel(self.payload, self.root)
        self.assertTrue(failed)
        self.assertEqual(file_hashes(self.target), before)
        self.assertFalse(list(self.root.glob('.velo-install-*')))

    def test_first_install_failure_leaves_no_partial_panel(self):
        original_replace = os.replace

        def fail_candidate(source, destination):
            if '.velo-install-' in str(source):
                raise OSError('simulated first-install failure')
            return original_replace(source, destination)

        with patch('ae.installer.core.os.replace', side_effect=fail_candidate):
            with self.assertRaises(OSError):
                install_panel(self.payload, self.root)
        self.assertFalse(self.target.exists())
        self.assertFalse(list(self.root.glob('.velo-install-*')))

    def test_restore_valid_backup_and_retain_original(self):
        install_panel(self.payload, self.root)
        report = install_panel(self.payload, self.root)
        backup = Path(report['backup'])
        original = file_hashes(backup / BUNDLE_ID)
        (self.target / 'js' / 'main.js').write_text('changed by a later edit', encoding='utf-8')
        restored = restore_backup(self.root, backup)
        self.assertEqual(restored['version'], '1.2.1')
        self.assertEqual(file_hashes(self.target), original)
        self.assertEqual(file_hashes(backup / BUNDLE_ID), original)
        self.assertIsNotNone(restored['backup'])

    def test_changed_backup_is_rejected_without_replacing_current(self):
        install_panel(self.payload, self.root)
        report = install_panel(self.payload, self.root)
        before = file_hashes(self.target)
        backup = Path(report['backup'])
        (backup / BUNDLE_ID / 'index.html').write_text('changed backup', encoding='utf-8')
        with self.assertRaises(InstallError):
            restore_backup(self.root, backup)
        self.assertEqual(file_hashes(self.target), before)

    def test_backup_outside_the_owned_directory_is_rejected(self):
        outside = Path(self.temporary.name) / 'outside'
        with self.assertRaises(InstallError):
            verify_backup(self.root, outside)

    def test_symlinked_target_is_rejected(self):
        self.root.mkdir(parents=True)
        try:
            os.symlink(self.payload / BUNDLE_ID, self.target, target_is_directory=True)
        except OSError as error:
            self.skipTest(f'Symlinks unavailable: {error}')
        with self.assertRaises(InstallError):
            install_panel(self.payload, self.root)

    def test_symlinked_backup_is_rejected(self):
        install_panel(self.payload, self.root)
        report = install_panel(self.payload, self.root)
        backup = Path(report['backup'])
        link = backup.parent / 'linked-backup'
        try:
            os.symlink(backup, link, target_is_directory=True)
        except OSError as error:
            self.skipTest(f'Symlinks unavailable: {error}')
        with self.assertRaises(InstallError):
            verify_backup(self.root, link)

    def test_default_windows_path_uses_roaming_appdata(self):
        with patch.dict(os.environ, {'APPDATA': r'C:\\Users\\Example\\AppData\\Roaming'}):
            path = default_extensions_dir('nt', Path('C:/Users/Example'))
            self.assertTrue(str(path).endswith('Adobe/CEP/extensions') or str(path).endswith(r'Adobe\CEP\extensions'))
            self.assertIn('Roaming', str(path))

    def test_cli_install_writes_a_real_report(self):
        report_path = Path(self.temporary.name) / 'report.json'
        command = [
            sys.executable, '-m', 'ae.installer.velo_installer', '--cli',
            '--payload', str(self.payload), '--target', str(self.root), '--report', str(report_path),
        ]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(report_path.read_text(encoding='utf-8'))
        self.assertTrue(report['ok'])
        self.assertEqual(report['version'], '1.2.1')
        self.assertTrue((self.target / 'CSXS' / 'manifest.xml').is_file())

    def test_restore_requires_explicit_cli_confirmation(self):
        install_panel(self.payload, self.root)
        report = install_panel(self.payload, self.root)
        command = [sys.executable, '-m', 'ae.installer.velo_installer', '--cli', '--payload', str(self.payload), '--target', str(self.root), '--restore', report['backup']]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--yes', result.stderr)

    def test_backup_detail_keeps_footer_reachable(self):
        from ae.installer.ui import backup_detail
        backup = self.root / 'Velo-backup' / '20261106-090125-c446f48d'
        for language in ('zh', 'en'):
            detail = backup_detail(backup, language)
            self.assertIn('Velo-backup/20261106-090125-c446f48d', detail)
            self.assertNotIn(str(self.root), detail)
            self.assertLessEqual(len(detail), 80)


if __name__ == '__main__':
    unittest.main()
