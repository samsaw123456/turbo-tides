"""Exercise installer filesystem transactions, archive validation and launch entry points."""

import fcntl
import hashlib
import io
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import install_linux as installer
import package_linux


class InstallerTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="Turbo Tides install tests "
        )
        self.root = Path(self.temporary.name)
        self.home = self.root / 'home space % $ ` " café'
        self.home.mkdir()
        self.data = self.root / 'data space % $ ` " café'
        self.environment = patch.dict(
            os.environ,
            {
                "HOME": str(self.home),
                "XDG_DATA_HOME": str(self.data),
                "XDG_STATE_HOME": str(self.root / "state space"),
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.addCleanup(self.temporary.cleanup)
        self.app = self.root / "bundle"
        self.make_app(self.app)
        self.destination = self.home / ".local/opt/turbo-tides"
        self.command = self.home / ".local/bin/turbo-tides"

    def make_app(self, app, version="1.2.0", exit_status=0):
        for folder in (
            "bin",
            "lib/app",
            "lib/runtime/lib/server",
            "src/main/resources/art",
        ):
            (app / folder).mkdir(parents=True, exist_ok=True)
        (app / installer.MARKER).write_text("Managed test fixture\n")
        (app / "VERSION").write_text(version + "\n")
        executable = app / "bin/TurboTides"
        executable.write_text(
            "#!/bin/sh\n"
            "printf 'fixture started\\n'\n"
            'printf \'%s\\n\' "$@" > "$HOME/received-arguments"\n'
            f"exit {exit_status}\n"
        )
        executable.chmod(0o755)
        (app / "lib/runtime/lib/server/libjvm.so").write_bytes(b"fixture runtime")
        with zipfile.ZipFile(app / "lib/app/turbo-tides.jar", "w") as jar:
            jar.writestr("META-INF/MANIFEST.MF", "Main-Class: turbotides.DesktopKt\n")
        source = Path(__file__).resolve().parents[1] / "src/main/resources/art"
        for name in [
            "icon.svg",
            "icon-32.png",
            "icon-64.png",
            "icon-128.png",
            "icon-512.png",
        ]:
            shutil.copy2(source / name, app / "src/main/resources/art" / name)

    def install(self):
        return installer.install_app(self.app)

    def test_install_repeat_launch_and_save_preservation(self):
        preferences = self.home / ".prefs/turbo-tides"
        preferences.parent.mkdir()
        preferences.write_text("untouched player save")
        self.install()
        self.install()
        self.assertEqual(preferences.read_text(), "untouched player save")
        result = subprocess.run(
            [str(self.command), "a space", "$(literal)", "%test"],
            cwd="/tmp",
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            (self.home / "received-arguments").read_text(),
            "a space\n$(literal)\n%test\n",
        )
        self.assertIn(
            "fixture started",
            (self.root / "state space/turbo-tides/launch.log").read_text(),
        )
        for size in (32, 64, 128, 512):
            self.assertTrue(
                (
                    self.data / f"icons/hicolor/{size}x{size}/apps/turbo-tides.png"
                ).is_file()
            )
        self.assertTrue(
            (self.data / "icons/hicolor/scalable/apps/turbo-tides.svg").is_file()
        )
        entry = self.data / "applications/turbo-tides.desktop"
        self.assertIn("%%", entry.read_text())
        if shutil.which("desktop-file-validate"):
            subprocess.run(["desktop-file-validate", str(entry)], check=True)

    def test_update_keeps_saves_and_replaces_app(self):
        self.install()
        (self.destination / "old-only").write_text("old app file")
        self.make_app(self.app, "1.2.1")
        self.install()
        self.assertEqual((self.destination / "VERSION").read_text().strip(), "1.2.1")
        self.assertFalse((self.destination / "old-only").exists())

    @unittest.skipUnless(shutil.which("gio"), "GIO desktop launcher unavailable")
    def test_desktop_entry_is_actually_loaded_with_special_paths(self):
        self.install()
        entry = self.data / "applications/turbo-tides.desktop"
        subprocess.run(["gio", "launch", str(entry)], cwd="/tmp", check=True)
        target = self.home / "received-arguments"
        for _ in range(50):
            if target.exists():
                break
            time.sleep(0.1)
        self.assertTrue(
            target.is_file(), "Desktop entry did not execute the installed launcher"
        )

    def test_concurrent_install_is_rejected(self):
        self.destination.parent.mkdir(parents=True)
        lock = self.destination.parent / ".turbo-tides-install.lock"
        with lock.open("w") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            with self.assertRaisesRegex(installer.InstallError, "another installer"):
                self.install()
        self.assertFalse(self.destination.exists())

    def start_fixture_game(self, direct=False):
        native = self.app / "bin/TurboTides"
        native.write_text(
            '#!/bin/sh\nprintf ready > "$HOME/game-ready"\nwhile :; do sleep 1; done\n'
        )
        self.install()
        command = self.destination / "bin/TurboTides" if direct else self.command
        process = subprocess.Popen(
            [str(command)],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        def stop():
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)

        self.addCleanup(stop)
        for _ in range(50):
            if (self.home / "game-ready").exists():
                return process
            time.sleep(0.02)
        self.fail("Fixture game did not start")

    def test_running_game_blocks_update_and_uninstall_without_stopping_game(self):
        process = self.start_fixture_game()
        self.make_app(self.app, "1.2.1")
        for action in (self.install, installer.uninstall_app):
            with self.assertRaisesRegex(installer.InstallError, "game is running"):
                action()
            self.assertIsNone(process.poll())
            self.assertEqual(
                (self.destination / "VERSION").read_text().strip(), "1.2.0"
            )

    def test_direct_native_game_is_also_protected(self):
        process = self.start_fixture_game(direct=True)
        with self.assertRaisesRegex(installer.InstallError, "app is running"):
            self.install()
        self.assertIsNone(process.poll())

    def test_managed_damaged_app_can_be_repaired(self):
        self.install()
        (self.destination / "lib/app/turbo-tides.jar").unlink()
        (self.destination / "src/main/resources/art/icon.svg").unlink()
        self.install()
        self.assertEqual(installer.validate_app(self.destination), "1.2.0")
        subprocess.run([str(self.command)], check=True)

    def test_uninstall_preserves_saves_and_modified_or_unrelated_entries(self):
        self.install()
        preferences = self.home / ".prefs/turbo-tides"
        preferences.parent.mkdir()
        preferences.write_text("player records and options")
        icon = self.data / "icons/hicolor/32x32/apps/turbo-tides.png"
        icon.write_bytes(b"user custom icon")
        other = self.data / "applications/another-game.desktop"
        other.write_text("unrelated")
        installer.uninstall_app()
        self.assertFalse(self.destination.exists())
        self.assertFalse(self.command.exists())
        self.assertFalse((self.data / "applications/turbo-tides.desktop").exists())
        self.assertFalse(
            (self.data / "icons/hicolor/scalable/apps/turbo-tides.svg").exists()
        )
        self.assertEqual(preferences.read_text(), "player records and options")
        self.assertEqual(icon.read_bytes(), b"user custom icon")
        self.assertEqual(other.read_text(), "unrelated")

    def test_uninstall_refuses_unmanaged_directory_and_symlink(self):
        self.destination.mkdir(parents=True)
        personal = self.destination / "personal.txt"
        personal.write_text("unrelated")
        with self.assertRaisesRegex(installer.InstallError, "unmanaged directory"):
            installer.uninstall_app()
        self.assertEqual(personal.read_text(), "unrelated")
        personal.unlink()
        self.destination.rmdir()
        self.destination.symlink_to(self.app, target_is_directory=True)
        with self.assertRaisesRegex(installer.InstallError, "unmanaged directory"):
            installer.uninstall_app()
        self.assertTrue((self.app / "bin/TurboTides").exists())

    def test_uninstall_failure_restores_app_and_entries(self):
        self.install()
        entry = self.data / "applications/turbo-tides.desktop"
        original = Path.unlink

        def fail_entry(path, *args, **kwargs):
            if path == entry:
                raise OSError("entry removal denied")
            return original(path, *args, **kwargs)

        with (
            patch.object(Path, "unlink", fail_entry),
            self.assertRaisesRegex(OSError, "entry removal denied"),
        ):
            installer.uninstall_app()
        self.assertTrue(self.command.is_file())
        self.assertTrue(entry.is_file())
        self.assertEqual(installer.validate_app(self.destination), "1.2.0")

    def test_copy_failure_preserves_old_app(self):
        self.install()
        with (
            patch.object(
                installer.shutil, "copytree", side_effect=OSError("full disk")
            ),
            self.assertRaisesRegex(OSError, "full disk"),
        ):
            self.install()
        self.assertTrue((self.destination / "bin/TurboTides").is_file())
        self.assertTrue(self.command.is_file())

    def test_rename_failure_does_not_delete_original(self):
        self.install()
        original = Path.rename

        def fail_old(path, target):
            if path == self.destination:
                raise OSError("rename denied")
            return original(path, target)

        with (
            patch.object(Path, "rename", fail_old),
            self.assertRaisesRegex(OSError, "rename denied"),
        ):
            self.install()
        self.assertTrue((self.destination / "bin/TurboTides").is_file())

    def test_failed_entry_update_restores_previous_app_and_entries(self):
        self.install()
        original_command = self.command.read_bytes()
        self.make_app(self.app, "1.2.1")
        original_write = installer.write_atomic
        entry = self.data / "applications/turbo-tides.desktop"

        def fail_entry(path, content, mode):
            if path == entry:
                raise OSError("entry write denied")
            return original_write(path, content, mode)

        with (
            patch.object(installer, "write_atomic", fail_entry),
            self.assertRaisesRegex(OSError, "entry write denied"),
        ):
            self.install()
        self.assertEqual((self.destination / "VERSION").read_text().strip(), "1.2.0")
        self.assertEqual(self.command.read_bytes(), original_command)

    def test_failed_rollback_keeps_recoverable_previous_app(self):
        self.install()
        self.make_app(self.app, "1.2.1")
        original_rename = Path.rename

        def fail_restore(path, target):
            if path.name == "previous":
                raise OSError("restore denied")
            return original_rename(path, target)

        with (
            patch.object(
                installer, "write_atomic", side_effect=OSError("write denied")
            ),
            patch.object(Path, "rename", fail_restore),
            self.assertRaisesRegex(OSError, "restore denied"),
        ):
            self.install()
        backups = list(self.destination.parent.glob(".turbo-tides-install-*/previous"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(installer.validate_app(backups[0]), "1.2.0")

    def test_unmanaged_command_and_app_are_preserved(self):
        self.command.parent.mkdir(parents=True)
        self.command.write_text("unrelated command")
        with self.assertRaisesRegex(installer.InstallError, "unrelated entry"):
            self.install()
        self.assertEqual(self.command.read_text(), "unrelated command")
        self.command.unlink()
        self.destination.mkdir(parents=True)
        (self.destination / "personal.txt").write_text("personal")
        with self.assertRaisesRegex(installer.InstallError, "unmanaged directory"):
            self.install()
        self.assertEqual((self.destination / "personal.txt").read_text(), "personal")

    def test_symlink_destination_is_never_replaced(self):
        self.destination.parent.mkdir(parents=True)
        self.destination.symlink_to(self.app, target_is_directory=True)
        with self.assertRaisesRegex(installer.InstallError, "unmanaged directory"):
            self.install()
        self.assertTrue(self.destination.is_symlink())
        self.assertTrue((self.app / "bin/TurboTides").is_file())

    def test_launch_failure_returns_status_and_writes_log(self):
        self.make_app(self.app, exit_status=17)
        self.install()
        # Keep the test independent of a desktop notification service.
        env = dict(os.environ, PATH=str(self.root / "commands"))
        commands = Path(env["PATH"])
        commands.mkdir()
        for name in ("dirname", "mkdir", "mv", "cat", "flock"):
            (commands / name).symlink_to(shutil.which(name))
        result = subprocess.run(
            [str(self.command)], env=env, capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 17)
        self.assertIn("could not start (exit 17)", result.stderr)
        diagnose = subprocess.run(
            [str(self.command), "--diagnose"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("fixture started", diagnose.stdout)
        notifier = commands / "zenity"
        notifier.write_text(
            '#!/bin/sh\nprintf \'%s\\n\' "$*" > "$HOME/launch-error-notification"\n'
        )
        notifier.chmod(0o755)
        invalid_state = self.home / "invalid-state"
        invalid_state.write_text("A file where a state directory should be")
        result = subprocess.run(
            [str(self.command)],
            env=dict(env, XDG_STATE_HOME=str(invalid_state)),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        notification = self.home / "launch-error-notification"
        self.assertIn("cannot create launch log", notification.read_text())
        self.assertIn("XDG_STATE_HOME", result.stderr)
        (commands / "mv").unlink()
        (commands / "mv").write_text("#!/bin/sh\nexit 13\n")
        (commands / "mv").chmod(0o755)
        result = subprocess.run(
            [str(self.command)], env=env, capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot rotate launch log", notification.read_text())
        self.assertIn(
            "fixture started",
            (self.root / "state space/turbo-tides/launch.log").read_text(),
        )

    def tar(self, members):
        path = self.root / "release.tar.gz"
        with tarfile.open(path, "w:gz") as bundle:
            for name, kind, value in members:
                member = tarfile.TarInfo(name)
                if kind == "link":
                    member.type = tarfile.SYMTYPE
                    member.linkname = value
                    bundle.addfile(member)
                else:
                    content = value.encode()
                    member.size = len(content)
                    bundle.addfile(member, io.BytesIO(content))
        return path

    def test_archive_paths_symlinks_and_duplicates_are_rejected(self):
        for members in (
            [("../escape", "file", "bad")],
            [("TurboTides/escape", "link", "/tmp/escape")],
            [
                ("TurboTides/link", "link", "safe"),
                ("TurboTides/link/file", "file", "bad"),
            ],
            [("TurboTides/file", "file", "one"), ("TurboTides/file", "file", "two")],
        ):
            with (
                self.subTest(members=members),
                self.assertRaises(installer.InstallError),
            ):
                installer.extract_archive(self.tar(members), self.root / "extracted")
        self.assertFalse((self.root / "escape").exists())

    def test_valid_archive_and_legal_relative_symlink(self):
        archive = self.tar(
            [
                ("TurboTides/legal/base/LICENSE", "file", "license"),
                ("TurboTides/legal/desktop/LICENSE", "link", "../base/LICENSE"),
            ]
        )
        app = installer.extract_archive(archive, self.root / "extracted")
        self.assertEqual((app / "legal/desktop/LICENSE").read_text(), "license")

    def test_wrong_checksum_and_filename_are_rejected(self):
        archive = self.tar([("TurboTides/file", "file", "fixture")])
        checksum = archive.with_suffix(".sha256")
        checksum.write_text("0" * 64 + "  " + archive.name + "\n")
        with self.assertRaisesRegex(installer.InstallError, "checksum mismatch"):
            installer.verify_archive(archive, checksum)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        checksum.write_text(digest + "  another-archive.tar.gz\n")
        with self.assertRaisesRegex(installer.InstallError, "exact archive filename"):
            installer.verify_archive(archive, checksum)
        checksum.write_text(digest + "  " + archive.name + "\n")
        installer.verify_archive(archive, checksum)

    def test_failed_download_removes_partial_file(self):
        destination = self.root / "download"
        destination.write_text("partial")
        with (
            patch.object(
                installer.urllib.request, "urlopen", side_effect=OSError("offline")
            ),
            self.assertRaisesRegex(OSError, "offline"),
        ):
            installer.fetch("https://github.com/example", destination)
        self.assertFalse(destination.exists())
        with self.assertRaisesRegex(installer.InstallError, "HTTPS"):
            installer.fetch("http://example.com/unsafe", destination)

    def test_missing_library_check_can_disable_system_mutations(self):
        with (
            patch.object(installer, "missing_libraries", return_value=["libGL.so.1"]),
            self.assertRaisesRegex(installer.InstallError, "Missing desktop libraries"),
        ):
            installer.ensure_dependencies(False)

    def test_standalone_script_has_no_checkout_dependency(self):
        script = self.root / "downloaded installer.sh"
        script.write_text(package_linux.standalone_installer())
        result = subprocess.run(
            ["sh", str(script), "--app", str(self.app), "--no-system-deps"],
            cwd="/tmp",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.command.exists())
        subprocess.run([str(self.command)], check=True)

    def test_missing_python_bootstrap_runs_package_manager_then_installs(self):
        commands = self.root / "bootstrap commands"
        commands.mkdir()
        for name in ("uname", "id", "dirname", "flock"):
            (commands / name).symlink_to(shutil.which(name))
        sudo = commands / "sudo"
        sudo.write_text('#!/bin/sh\nexec "$@"\n')
        sudo.chmod(0o755)
        manager = commands / "apt-get"
        manager.write_text(
            '#!/bin/sh\nprintf "%s\\n" "$*" >> "$HOME/package-calls"\n'
            f'/bin/ln -sf {sys.executable} "$TEST_COMMANDS/python3"\n'
        )
        manager.chmod(0o755)
        script = self.root / "standalone.sh"
        script.write_text(package_linux.standalone_installer())
        env = dict(os.environ, PATH=str(commands), TEST_COMMANDS=str(commands))
        result = subprocess.run(
            ["/bin/sh", str(script), "--app", str(self.app), "--no-system-deps"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = (self.home / "package-calls").read_text()
        self.assertIn("update", calls)
        self.assertIn(
            "install -y --no-install-recommends python3 ca-certificates", calls
        )
        self.assertTrue(self.command.is_file())

    def test_missing_desktop_library_is_installed_then_rechecked(self):
        commands = self.root / "library commands"
        commands.mkdir()
        (commands / "flock").symlink_to(shutil.which("flock"))
        for name, text in {
            "sudo": '#!/bin/sh\nexec "$@"\n',
            "apt-get": '#!/bin/sh\nprintf "%s\\n" "$*" >> "$HOME/library-calls"\n',
            "apt-cache": '#!/bin/sh\n[ "$1 $2" = "show libgcc-s1" ]\n',
        }.items():
            file = commands / name
            file.write_text(text)
            file.chmod(0o755)
        with (
            patch.dict(os.environ, {"PATH": str(commands)}),
            patch.object(
                installer,
                "missing_libraries",
                side_effect=[["libGL.so.1", "libstdc++.so.6", "libgcc_s.so.1"], []],
            ) as check,
        ):
            installer.ensure_dependencies()
        self.assertEqual(check.call_count, 2)
        self.assertEqual(
            (self.home / "library-calls").read_text(),
            "update\ninstall -y --no-install-recommends libgcc-s1 libgl1 libstdc++6\n",
        )
        runtime = ["libstdc++.so.6", "libgcc_s.so.1"]
        for manager, expected in {
            "dnf": ["libgcc", "libstdc++"],
            "pacman": ["libgcc", "libstdc++"],
            "zypper": ["libgcc_s1", "libstdc++6"],
        }.items():
            with self.subTest(manager=manager):
                self.assertEqual(
                    installer.dependency_command(runtime, manager)[-len(expected) :],
                    expected,
                )
        with patch.object(
            installer.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)
        ):
            self.assertEqual(
                installer.dependency_command(runtime, "apt-get")[-2:],
                ["libgcc1", "libstdc++6"],
            )

    def test_missing_flock_is_installed_then_rechecked(self):
        commands = self.root / "flock commands"
        commands.mkdir()
        manager = commands / "apt-get"
        manager.write_text(
            '#!/bin/sh\nprintf "%s\\n" "$*" >> "$HOME/flock-calls"\n'
            f'/bin/ln -sf {shutil.which("flock")} "$TEST_COMMANDS/flock"\n'
        )
        manager.chmod(0o755)
        elevation = commands / "sudo"
        elevation.write_text('#!/bin/sh\nexec "$@"\n')
        elevation.chmod(0o755)
        with (
            patch.dict(
                os.environ, {"PATH": str(commands), "TEST_COMMANDS": str(commands)}
            ),
            patch.object(installer, "missing_libraries", return_value=[]),
        ):
            installer.ensure_dependencies()
            self.assertEqual(installer.missing_dependencies(), [])
        self.assertEqual(
            (self.home / "flock-calls").read_text(),
            "update\ninstall -y --no-install-recommends util-linux\n",
        )

    def test_failed_download_checksum_and_archive_preserve_previous_install(self):
        self.install()
        script = self.root / "failing-installer.sh"
        script.write_text(package_linux.standalone_installer())
        env = dict(os.environ, HTTPS_PROXY="http://127.0.0.1:1", NO_PROXY="")
        archive = self.tar([("../escape", "file", "unsafe")])
        checksum = self.root / "release.sha256"
        checksum.write_text("0" * 64 + "  " + archive.name + "\n")
        archive_args = ["--archive", str(archive), "--checksum", str(checksum)]
        for kind, arguments in (
            ("download", ["--version", "9.9.9"]),
            ("checksum", archive_args),
            ("archive", archive_args),
        ):
            if kind == "archive":
                checksum.write_text(
                    hashlib.sha256(archive.read_bytes()).hexdigest()
                    + "  "
                    + archive.name
                    + "\n"
                )
            with self.subTest(kind=kind):
                result = subprocess.run(
                    ["sh", str(script), *arguments, "--no-system-deps"],
                    env=env,
                    cwd="/tmp",
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("installation failed", result.stderr)
                self.assertEqual(installer.validate_app(self.destination), "1.2.0")
                subprocess.run([str(self.command)], env=env, check=True)
        self.assertFalse((self.root / "escape").exists())

    def test_local_archive_installs_and_uninstalls_with_network_unavailable(self):
        archive = self.root / "offline-release.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(self.app, arcname="TurboTides")
        checksum = self.root / "offline-release.tar.gz.sha256"
        checksum.write_text(
            hashlib.sha256(archive.read_bytes()).hexdigest()
            + "  "
            + archive.name
            + "\n"
        )
        script = self.root / "offline-installer.sh"
        script.write_text(package_linux.standalone_installer())
        env = dict(
            os.environ,
            HTTPS_PROXY="http://127.0.0.1:1",
            HTTP_PROXY="http://127.0.0.1:1",
        )
        result = subprocess.run(
            [
                "sh",
                str(script),
                "--archive",
                str(archive),
                "--checksum",
                str(checksum),
                "--no-system-deps",
            ],
            cwd="/tmp",
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        subprocess.run([str(self.command)], env=env, check=True)
        result = subprocess.run(
            ["sh", str(script), "--uninstall"],
            cwd="/tmp",
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.destination.exists())


if __name__ == "__main__":
    unittest.main()
