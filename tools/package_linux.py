"""Build a relocatable Linux desktop app with its own Java runtime and an installer."""

import argparse
import hashlib
import os
import platform
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

from install_linux import InstallError, ensure_dependencies, install_app, launcher_text

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
NAME = "TurboTides"
MARKER = ".turbo-tides-managed"
VERSION = (ROOT / "VERSION").read_text().strip()


def complete_jdk(packager):
    java = packager.parent / "java"
    linker = packager.parent / "jlink"
    if not all(path.is_file() for path in (packager, java, linker)):
        return False
    modules = subprocess.run(
        [str(java), "--list-modules"], capture_output=True, text=True, check=False
    )
    major = re.search(r"^java.base@(\d+)", modules.stdout, re.MULTILINE)
    if (
        modules.returncode
        or not major
        or int(major.group(1)) < 25
        or "java.desktop@" not in modules.stdout
    ):
        return False
    if (packager.resolve().parents[1] / "jmods/java.desktop.jmod").is_file():
        return True
    # JEP 493 lets complete JDK 25 distributions link directly from their image.
    # Stabilize this textual capability probe independently of the user's locale.
    help_result = subprocess.run(
        [str(linker), "-J-Duser.language=en", "-J-Duser.country=US", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    return (
        help_result.returncode == 0
        and "Linking from run-time image enabled" in help_result.stdout
    )


def jpackage():
    configured = os.environ.get("TURBO_JAVA_HOME") or os.environ.get("JAVA_HOME")
    if configured:
        candidate = Path(configured) / "bin/jpackage"
        if not complete_jdk(candidate):
            raise SystemExit(
                "The selected JDK lacks desktop modules, jlink/jpackage, or Java 25. Select a complete JDK 25+ with TURBO_JAVA_HOME."
            )
        return candidate
    candidates = sorted(Path("/usr/lib/jvm").glob("*/bin/jpackage"), reverse=True)
    available = shutil.which("jpackage")
    if available:
        candidates.append(Path(available))
    for candidate in candidates:
        if complete_jdk(candidate):
            return candidate
    raise SystemExit(
        "A complete JDK 25+ with jpackage and desktop-capable jlink is required."
    )


def install(app):
    try:
        ensure_dependencies()
        return install_app(app)
    except InstallError as exception:
        raise SystemExit(str(exception)) from exception


def standalone_installer():
    bootstrap = (ROOT / "tools/bootstrap_installer.sh").read_text()
    payload = (ROOT / "tools/install_linux.py").read_text()
    return (
        bootstrap
        + """
ensure_installer_python
installer_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
if [ "$#" -eq 0 ] && [ -f "$installer_dir/.turbo-tides-managed" ]; then
    set -- --app "$installer_dir"
fi
python3 - "$@" <<'TURBO_TIDES_PYTHON_INSTALLER'
"""
        + payload
        + "\nTURBO_TIDES_PYTHON_INSTALLER\n"
    )


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
            VERSION,
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
            "--java-options",
            "--enable-native-access=ALL-UNNAMED",
            "--java-options",
            "--add-exports=java.base/jdk.internal.misc=ALL-UNNAMED",
        ],
        check=True,
    )
    for name in ("README.md", "LICENSE", "THIRD_PARTY.md", "VERSION"):
        shutil.copy2(ROOT / name, app / name)
    shutil.copytree(ROOT / "src/main/resources", app / "src/main/resources")
    shutil.copytree(ROOT / "docs", app / "docs")
    (app / MARKER).write_text("Managed by Turbo Tides installer\n")
    # The short launcher works from a file manager and from any working directory.
    play = app / "Play Turbo Tides"
    play.write_text(launcher_text())
    play.chmod(0o755)
    (app / "launch.sh").write_text(launcher_text())
    (app / "launch.sh").chmod(0o755)
    installer = standalone_installer()
    for path in (app / "Install Turbo Tides.sh", DIST / "install.sh"):
        path.write_text(installer)
        path.chmod(0o755)
    archive = DIST / f"turbo-tides-{VERSION}-linux-{platform.machine()}.tar.gz"
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
