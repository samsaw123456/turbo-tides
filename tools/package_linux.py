"""Build a relocatable Linux desktop app with its own Java runtime and an installer."""

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
NAME = "TurboTides"
MARKER = ".turbo-tides-managed"


def jpackage():
    configured = os.environ.get("TURBO_JAVA_HOME") or os.environ.get("JAVA_HOME")
    candidates = [Path(configured) / "bin/jpackage"] if configured else []
    if configured and not (Path(configured) / "jmods/java.desktop.jmod").is_file():
        raise SystemExit(
            "The selected JDK lacks desktop modules. Select a complete JDK with TURBO_JAVA_HOME."
        )
    candidates.extend(
        sorted(Path("/usr/lib/jvm").glob("java-*-openjdk-*/bin/jpackage"), reverse=True)
    )
    available = shutil.which("jpackage")
    if available:
        candidates.append(Path(available))
    for candidate in candidates:
        if (
            candidate.is_file()
            and (candidate.resolve().parents[1] / "jmods/java.desktop.jmod").is_file()
        ):
            return candidate
    raise SystemExit("A JDK with jpackage is required (OpenJDK 17 or later).")


def quoted(path):
    return (
        '"'
        + str(path)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("`", "\\`")
        .replace("$", "\\$")
        + '"'
    )


def install(app):
    destination = Path.home() / ".local/opt/turbo-tides"
    if destination.exists():
        if not (destination / MARKER).exists():
            raise SystemExit(
                f"Refusing to replace an unmanaged directory: {destination}"
            )
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(app, destination, symlinks=True)
    (destination / MARKER).write_text("Managed by Turbo Tides installer\n")
    applications = Path.home() / ".local/share/applications"
    icons = Path.home() / ".local/share/icons/hicolor/512x512/apps"
    applications.mkdir(parents=True, exist_ok=True)
    icons.mkdir(parents=True, exist_ok=True)
    icon = icons / "turbo-tides.png"
    shutil.copy2(ROOT / "src/main/resources/art/icon-512.png", icon)
    entry = applications / "turbo-tides.desktop"
    entry.write_text(
        "[Desktop Entry]\nType=Application\nName=Turbo Tides\n"
        "Comment=Drift, boost and race across two sunlit islands\n"
        f"Exec={quoted(destination / 'bin/TurboTides')}\n"
        f"Icon={icon}\nTerminal=false\nCategories=Game;SportsGame;\n"
        "StartupWMClass=Turbo Tides\nStartupNotify=true\n"
    )
    for command in (
        ["desktop-file-validate", str(entry)],
        ["update-desktop-database", str(applications)],
    ):
        if shutil.which(command[0]):
            subprocess.run(command, check=True)
    print(f"Installed: {destination}\nApp menu entry: {entry}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--install",
        action="store_true",
        help="also add the app to this user's application menu",
    )
    parser.add_argument(
        "--skip-build", action="store_true", help="use an already checked fat JAR"
    )
    args = parser.parse_args()
    if platform.system() != "Linux":
        raise SystemExit(
            "This packager targets Linux. The source and fat JAR also support other desktop platforms."
        )
    packager = jpackage()
    if not args.skip_build:
        subprocess.run([str(ROOT / "gradlew"), "check", "fatJar"], cwd=ROOT, check=True)
    staging = ROOT / "build/package-input"
    staging.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "build/libs/turbo-tides.jar", staging / "turbo-tides.jar")
    app = DIST / NAME
    if app.exists():
        shutil.rmtree(app)
    DIST.mkdir(exist_ok=True)
    subprocess.run(
        [
            str(packager),
            "--type",
            "app-image",
            "--name",
            NAME,
            "--app-version",
            "1.0.0",
            "--description",
            "Turbo Tides 3D arcade racing",
            "--vendor",
            "Turbo Tides contributors",
            "--input",
            str(staging),
            "--main-jar",
            "turbo-tides.jar",
            "--main-class",
            "turbotides.DesktopKt",
            "--dest",
            str(DIST),
            "--icon",
            str(ROOT / "src/main/resources/art/icon-512.png"),
            "--add-modules",
            "java.base,java.desktop,java.logging,java.xml,jdk.unsupported",
            "--java-options",
            "-Xmx768m",
        ],
        check=True,
    )
    for name in ("README.md", "LICENSE", "THIRD_PARTY.md"):
        shutil.copy2(ROOT / name, app / name)
    shutil.copytree(ROOT / "src/main/resources", app / "src/main/resources")
    shutil.copytree(ROOT / "docs", app / "docs")
    (app / MARKER).write_text("Managed by Turbo Tides installer\n")
    # The short launcher works from a file manager and from any working directory.
    play = app / "Play Turbo Tides"
    play.write_text(
        '#!/bin/sh\nset -eu\napp_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec "$app_dir/bin/TurboTides" "$@"\n'
    )
    play.chmod(0o755)
    archive = DIST / f"turbo-tides-1.0.0-linux-{platform.machine()}.tar.gz"
    with tarfile.open(archive, "w:gz") as output:
        output.add(app, arcname=NAME)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(archive.suffix + ".sha256").write_text(
        f"{checksum}  {archive.name}\n"
    )
    print(f"Packaged {archive} ({archive.stat().st_size / 1024**2:.1f} MiB)")
    if args.install:
        install(app)


if __name__ == "__main__":
    main()
