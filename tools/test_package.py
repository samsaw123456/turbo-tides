"""Regression checks for the installer's two non-destructive failure paths."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import package_linux


class PackageSafetyTest(unittest.TestCase):
    def test_incomplete_explicit_jdk_is_rejected(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict(os.environ, {"TURBO_JAVA_HOME": folder}),
            self.assertRaisesRegex(SystemExit, "lacks desktop modules"),
        ):
            package_linux.jpackage()

    def test_existing_unmanaged_install_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            home_fixture = Path(folder)
            destination = home_fixture / ".local/opt/turbo-tides"
            destination.mkdir(parents=True)
            sentinel = destination / "keep.txt"
            sentinel.write_text("Unrelated existing files")
            with (
                patch.object(package_linux.Path, "home", return_value=home_fixture),
                self.assertRaisesRegex(SystemExit, "unmanaged directory"),
            ):
                package_linux.install(home_fixture / "unused-input")
            self.assertEqual(sentinel.read_text(), "Unrelated existing files")


if __name__ == "__main__":
    unittest.main()
