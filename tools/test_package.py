"""Regression checks for runtime detection and safe installation failures."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import package_linux


class PackageSafetyTest(unittest.TestCase):
    def test_runtime_image_jdk_is_detected_in_non_english_locale(self):
        with tempfile.TemporaryDirectory() as folder:
            binary = Path(folder) / "bin"
            binary.mkdir()
            scripts = {
                "java": "#!/bin/sh\nprintf 'java.base@25.0.5\\njava.desktop@25.0.5\\n'\n",
                "jpackage": "#!/bin/sh\nexit 0\n",
                "jlink": (
                    "#!/bin/sh\n"
                    'case "$*" in\n'
                    "  *-J-Duser.language=en*-J-Duser.country=US*) printf 'Linking from run-time image enabled\\n' ;;\n"
                    "  *) printf '実行時イメージからのリンクが有効です\\n' ;;\n"
                    "esac\n"
                ),
            }
            for name, source in scripts.items():
                path = binary / name
                path.write_text(source)
                path.chmod(0o755)
            localized = subprocess.run(
                [str(binary / "jlink"), "--help"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertNotIn("Linking from run-time image enabled", localized.stdout)
            with patch.dict(os.environ, {"JAVA_TOOL_OPTIONS": "-Duser.language=ja"}):
                self.assertTrue(package_linux.complete_jdk(binary / "jpackage"))

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
