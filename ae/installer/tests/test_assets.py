from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from ae.installer.build_installer import verify_public_archive
from ae.installer.core import InstallError, verify_payload
from ae.installer.velo_installer import resource_path
from ae.installer.verify_assets import verify_assets


class AssetTests(unittest.TestCase):
    def test_frozen_icon_assets_are_valid(self):
        manifest = verify_assets()
        self.assertGreaterEqual(len(manifest['files']), 11)

    def test_standard_pyinstaller_payload_link_is_accepted_only_exactly(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            payload = base / 'Contents' / 'Resources' / 'payload'
            payload.mkdir(parents=True)
            linked = base / 'Contents' / 'Frameworks' / 'payload'
            linked.parent.mkdir()
            linked.symlink_to('../Resources/payload', target_is_directory=True)
            with patch.object(sys, '_MEIPASS', str(linked.parent), create=True):
                self.assertEqual(resource_path('payload'), payload.resolve())
                self.assertEqual(resource_path('payload').is_symlink(), False)
            other = base / 'Contents' / 'Elsewhere' / 'other'
            other.parent.mkdir(parents=True)
            other.symlink_to('../Resources/other-payload', target_is_directory=True)
            with patch.object(sys, '_MEIPASS', str(other.parent), create=True):
                self.assertEqual(resource_path('payload'), other.parent / 'payload')
                with self.assertRaises(InstallError):
                    verify_payload(other)

    def test_privacy_scan_rejects_real_private_paths_not_standard_examples(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / 'sample.zip'
            with zipfile.ZipFile(archive, 'w') as bundle:
                bundle.writestr('example.txt', b'/Users/Barney')
            verify_public_archive(archive)
            with zipfile.ZipFile(archive, 'a') as bundle:
                bundle.writestr('private.txt', b'/Users/user/example')
            with self.assertRaises(RuntimeError):
                verify_public_archive(archive)

    def test_mac_bundle_version_is_synchronized(self):
        import plistlib
        from ae.installer.build_installer import set_mac_version
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary) / 'VeloInstaller.app'
            info = app / 'Contents' / 'Info.plist'
            info.parent.mkdir(parents=True)
            info.write_bytes(plistlib.dumps({'CFBundleIdentifier': 'com.velo.installer', 'CFBundleShortVersionString': '0.0.0'}))
            set_mac_version(app)
            metadata = plistlib.loads(info.read_bytes())
            self.assertEqual(metadata['CFBundleShortVersionString'], '1.2.1')
            self.assertEqual(metadata['CFBundleVersion'], '1.2.1')
            self.assertEqual(metadata['CFBundleIdentifier'], 'com.velo.installer')

    def test_windows_version_resource_is_synchronized(self):
        from ae.installer.build_installer import windows_version_text
        text = windows_version_text()
        for field in ('filevers', 'prodvers'):
            self.assertIn(f'{field}=(1, 2, 1, 0)', text)
        self.assertIn("StringStruct('FileVersion', '1.2.1')", text)
        self.assertIn("StringStruct('ProductVersion', '1.2.1')", text)
        self.assertIn("StringStruct('OriginalFilename', 'VeloInstaller.exe')", text)


if __name__ == '__main__':
    unittest.main()
