"""Install a verified, self-contained Turbo Tides release for the current user."""

import argparse
import ctypes
import fcntl
import hashlib
import json
import os
import platform
import posixpath
import re
import shlex
import shutil
import stat
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

REPOSITORY = "samsaw123456/turbo-tides"
MARKER = ".turbo-tides-managed"
DESKTOP_MARKER = "X-Turbo-Tides-Managed=true"
COMMAND_MARKER = "# Managed by Turbo Tides installer"
MAX_DOWNLOAD = 256 * 1024 * 1024
LIBRARIES = {
    "libX11.so.6": ("libx11-6", "libX11", "libx11", "libX11-6"),
    "libXext.so.6": ("libxext6", "libXext", "libxext", "libXext6"),
    "libXi.so.6": ("libxi6", "libXi", "libxi", "libXi6"),
    "libXtst.so.6": ("libxtst6", "libXtst", "libxtst", "libXtst6"),
    "libXrender.so.1": ("libxrender1", "libXrender", "libxrender", "libXrender1"),
    "libXrandr.so.2": ("libxrandr2", "libXrandr", "libxrandr", "libXrandr2"),
    "libXcursor.so.1": ("libxcursor1", "libXcursor", "libxcursor", "libXcursor1"),
    "libXinerama.so.1": ("libxinerama1", "libXinerama", "libxinerama", "libXinerama1"),
    "libGL.so.1": ("libgl1", "libglvnd-glx", "libglvnd", "libGL1"),
    "libstdc++.so.6": ("libstdc++6", "libstdc++", "libstdc++", "libstdc++6"),
    "libgcc_s.so.1": ("libgcc1", "libgcc", "libgcc", "libgcc_s1"),
    "libasound.so.2": ("libasound2", "alsa-lib", "alsa-lib", "libasound2"),
    "libfontconfig.so.1": (
        "libfontconfig1",
        "fontconfig",
        "fontconfig",
        "libfontconfig1",
    ),
    "libfreetype.so.6": ("libfreetype6", "freetype", "freetype2", "libfreetype6"),
}


class InstallError(RuntimeError):
    pass


def run(command):
    subprocess.run(command, check=True)


def missing_libraries():
    missing = []
    for library in LIBRARIES:
        try:
            ctypes.CDLL(library)
        except OSError:
            missing.append(library)
    return missing


def missing_dependencies():
    return missing_libraries() + ([] if shutil.which("flock") else ["flock"])


def dependency_command(missing, manager):
    column = {"apt-get": 0, "dnf": 1, "pacman": 2, "zypper": 3}[manager]
    packages = sorted(
        {
            "util-linux" if name == "flock" else LIBRARIES[name][column]
            for name in missing
        }
    )
    if manager == "apt-get":
        # Debian/Ubuntu renamed the GCC runtime and, later, ALSA's time ABI.
        for older, newer in (("libgcc1", "libgcc-s1"), ("libasound2", "libasound2t64")):
            if older not in packages:
                continue
            available = subprocess.run(
                ["apt-cache", "show", newer],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if available.returncode == 0:
                packages[packages.index(older)] = newer
    return {
        "apt-get": [manager, "install", "-y", "--no-install-recommends"],
        "dnf": [manager, "install", "-y"],
        "pacman": [manager, "-S", "--needed", "--noconfirm"],
        "zypper": [manager, "--non-interactive", "install"],
    }[manager] + packages


def ensure_dependencies(automatic=True):
    missing = missing_dependencies()
    if not missing:
        return
    detail = ", ".join(missing)
    if not automatic:
        raise InstallError(
            f"Missing desktop libraries or launcher tools: {detail}. Rerun without --no-system-deps to install them."
        )
    manager = next(
        (name for name in ("apt-get", "dnf", "pacman", "zypper") if shutil.which(name)),
        None,
    )
    if manager is None:
        raise InstallError(
            f"Missing desktop libraries or launcher tools: {detail}. No supported package manager found (apt, dnf, pacman, zypper)."
        )
    elevation = next(
        (name for name in ("sudo", "doas", "pkexec") if shutil.which(name)), None
    )
    if os.geteuid() == 0:
        prefix = []
    elif elevation:
        prefix = [elevation]
    else:
        raise InstallError(
            f"Installing {detail} requires sudo, doas, or pkexec. The game itself installs per-user."
        )
    print(
        "Installing missing desktop dependencies; your system may request administrator authentication.",
        flush=True,
    )
    if manager == "apt-get":
        run(prefix + [manager, "update"])
    command = dependency_command(missing, manager)
    print(" ".join(command), flush=True)
    run(prefix + command)
    remaining = missing_dependencies()
    if remaining:
        raise InstallError(
            "Dependencies still unavailable after installation: " + ", ".join(remaining)
        )


def fetch(url, destination, maximum=MAX_DOWNLOAD):
    if urllib.parse.urlparse(url).scheme != "https":
        raise InstallError("Downloads require HTTPS; verification cannot be disabled.")
    request = urllib.request.Request(
        url, headers={"User-Agent": "TurboTidesInstaller/1"}
    )
    total = 0
    try:
        with (
            urllib.request.urlopen(request, timeout=45) as response,
            destination.open("wb") as output,
        ):
            if urllib.parse.urlparse(response.url).scheme != "https":
                raise InstallError("Download redirected away from HTTPS.")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > maximum:
                    raise InstallError("Download exceeds the expected release size.")
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def download_release(folder, version=None):
    suffix = "latest" if version is None else f"tags/v{version}"
    metadata = folder / "release.json"
    fetch(
        f"https://api.github.com/repos/{REPOSITORY}/releases/{suffix}",
        metadata,
        2 * 1024 * 1024,
    )
    release = json.loads(metadata.read_text())
    assets = {
        entry["name"]: entry["browser_download_url"]
        for entry in release.get("assets", [])
    }
    archives = [
        name
        for name in assets
        if re.fullmatch(r"turbo-tides-[0-9][0-9A-Za-z.+-]*-linux-x86_64\.tar\.gz", name)
    ]
    if len(archives) != 1:
        raise InstallError(
            "The requested release does not contain one Linux x86-64 app archive."
        )
    name = archives[0]
    for asset in (name, name + ".sha256"):
        url = assets.get(asset, "")
        parsed = urllib.parse.urlparse(url)
        if parsed.hostname != "github.com" or not parsed.path.startswith(
            f"/{REPOSITORY}/releases/download/"
        ):
            raise InstallError(
                "Release archive or checksum URL is missing or outside the project release."
            )
        print(f"Downloading {asset}", flush=True)
        fetch(url, folder / asset, MAX_DOWNLOAD if asset == name else 4096)
    return folder / name, folder / (name + ".sha256")


def verify_archive(archive, checksum):
    fields = checksum.read_text().strip().split()
    if (
        len(fields) != 2
        or not re.fullmatch(r"[0-9a-fA-F]{64}", fields[0])
        or fields[1].lstrip("*") != archive.name
    ):
        raise InstallError(
            "Checksum must contain the SHA-256 and exact archive filename."
        )
    digest = hashlib.sha256()
    with archive.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != fields[0].lower():
        raise InstallError(
            "Release checksum mismatch. The existing app was not changed."
        )


def extract_archive(archive, folder):
    # Validate the complete tree before creating anything. Symlinks are written
    # last; no archive member may write through a symlink parent.
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        if len(members) > 20000 or sum(member.size for member in members) > 1024**3:
            raise InstallError("Release archive is unexpectedly large.")
        seen = set()
        links = set()
        for member in members:
            path = PurePosixPath(member.name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or not path.parts
                or path.parts[0] != "TurboTides"
                or str(path) != member.name.rstrip("/")
                or member.name in seen
            ):
                raise InstallError("Unsafe or duplicate path in release archive.")
            seen.add(member.name)
            if not (member.isfile() or member.isdir() or member.issym()):
                raise InstallError("Unsupported special file in release archive.")
            if member.issym():
                target = posixpath.normpath(
                    posixpath.join(posixpath.dirname(member.name), member.linkname)
                )
                if member.linkname.startswith("/") or not target.startswith(
                    "TurboTides/"
                ):
                    raise InstallError("Release symlink escapes the app directory.")
                links.add(member.name)
        for member in members:
            if any(
                str(parent) in links for parent in PurePosixPath(member.name).parents
            ):
                raise InstallError("Release member uses a symlink as its parent.")
        for member in members:
            destination = folder / member.name
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                destination.parent.mkdir(parents=True, exist_ok=True)
                with (
                    bundle.extractfile(member) as source,
                    destination.open("wb") as output,
                ):
                    shutil.copyfileobj(source, output)
                destination.chmod(0o755 if member.mode & 0o111 else 0o644)
        for member in members:
            if member.issym():
                target = folder / member.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(member.linkname)
    return folder / "TurboTides"


def validate_app(app):
    required = [
        MARKER,
        "VERSION",
        "bin/TurboTides",
        "lib/app/turbo-tides.jar",
        "lib/runtime/lib/server/libjvm.so",
        "src/main/resources/art/icon.svg",
    ]
    required += [
        f"src/main/resources/art/icon-{size}.png" for size in (32, 64, 128, 512)
    ]
    for name in required:
        if not (app / name).is_file():
            raise InstallError(f"Incomplete app: missing {name}.")
    if not os.access(app / "bin/TurboTides", os.X_OK):
        raise InstallError("The game executable is not executable.")
    version = (app / "VERSION").read_text().strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", version):
        raise InstallError("The app has an invalid version.")
    with zipfile.ZipFile(app / "lib/app/turbo-tides.jar") as jar:
        if jar.testzip() is not None:
            raise InstallError("The game JAR failed its integrity check.")
    root = app.resolve()
    for path in app.rglob("*"):
        if path.is_symlink():
            try:
                contained = path.resolve().is_relative_to(root)
            except RuntimeError as exception:
                raise InstallError("App contains a cyclic symlink.") from exception
            if not contained:
                raise InstallError(
                    f"App symlink escapes its directory: {path.relative_to(app)}"
                )
    return version


def xdg_path(name, fallback):
    value = os.environ.get(name, "")
    return Path(value) if value.startswith("/") else fallback


def safe_path(path):
    path = Path(path).expanduser()
    if not path.is_absolute() or any(ord(char) < 32 for char in str(path)):
        raise InstallError(
            "Install paths must be absolute and contain no control characters."
        )
    if path == Path("/") or path == Path.home():
        raise InstallError("Choose a dedicated game directory.")
    return path


def desktop_quote(path):
    # Exec has both desktop-string escaping and argument quoting. A literal %
    # must survive desktop field-code expansion as well.
    return (
        '"'
        + str(path)
        .replace("\\", "\\\\\\\\")
        .replace('"', '\\\\"')
        .replace("`", "\\\\`")
        .replace("$", "\\\\$")
        .replace("%", "%%")
        + '"'
    )


def launcher_text():
    return """#!/bin/sh
# Managed by Turbo Tides installer
set -u
show_error() {
    failure_message=$1
    printf '%s\\n' "$failure_message" >&2
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title='Turbo Tides' --text="$failure_message" 2>/dev/null || :
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --error "$failure_message" --title 'Turbo Tides' 2>/dev/null || :
    elif command -v notify-send >/dev/null 2>&1; then
        notify-send --urgency=critical 'Turbo Tides could not start' "$failure_message" 2>/dev/null || :
    fi
}
app_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || { show_error 'Turbo Tides: cannot locate the app directory.'; exit 1; }
case ${XDG_STATE_HOME:-} in /*) state_dir=$XDG_STATE_HOME ;; *) state_dir=$HOME/.local/state ;; esac
log_dir=$state_dir/turbo-tides
mkdir -p -- "$log_dir" || { show_error "Turbo Tides: cannot create launch log at $log_dir. Check XDG_STATE_HOME and directory permissions."; exit 1; }
log=$log_dir/launch.log
if [ "${1:-}" = --diagnose ]; then
    printf 'Turbo Tides %s\\nApp: %s\\nLaunch log: %s\\n' "$(cat "$app_dir/VERSION")" "$app_dir" "$log"
    if [ -f "$log" ]; then cat -- "$log"; fi
    exit 0
fi
if [ -f "$log" ]; then
    mv -f -- "$log" "$log.previous" || { show_error "Turbo Tides: cannot rotate launch log at $log. Check directory permissions."; exit 1; }
fi
lock=${app_dir%/*}/.${app_dir##*/}-install.lock
# Shared for the entire native process lifetime; installers take an exclusive lock.
flock --shared --nonblock --conflict-exit-code 75 "$lock" "$app_dir/bin/TurboTides" "$@" >"$log" 2>&1
status=$?
if [ "$status" -ne 0 ]; then
    message="Turbo Tides could not start (exit $status). Details: $log"
    if [ "$status" -eq 75 ]; then
        message="Turbo Tides is being updated. Let the installer finish, then open the game again. Details: $log"
    fi
    show_error "$message"
    cat -- "$log" >&2
fi
exit "$status"
"""


def install_app(app, destination=None, bin_dir=None, desktop=True):
    destination = safe_path(destination or Path.home() / ".local/opt/turbo-tides")
    if destination.resolve() != app.resolve() and destination.resolve().is_relative_to(
        app.resolve()
    ):
        raise InstallError(
            "The installation directory must not be inside the source app."
        )
    with app_lock(destination):
        return install_locked(app, destination, bin_dir, desktop)


@contextmanager
def app_lock(destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    lock_path = destination.parent / ("." + destination.name + "-install.lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exception:
            raise InstallError(
                "The game is running or another installer is updating this app. Close the game and let any installer finish, then retry."
            ) from exception
        reject_running_legacy_app(destination)
        yield
    finally:
        os.close(descriptor)


def reject_running_legacy_app(destination):
    # Old releases and people opening bin/TurboTides directly do not take our
    # shared lock. Do not replace their mapped JVM files while they are running.
    executable = str(destination.resolve() / "bin/TurboTides")
    runtime = str(destination.resolve() / "lib/runtime") + "/"
    for process in Path("/proc").glob("[0-9]*"):
        try:
            if process.stat().st_uid != os.getuid():
                continue
            arguments = (process / "cmdline").read_bytes().split(b"\0")[:2]
            running = executable.encode() in arguments
            if not running:
                running = runtime in (process / "maps").read_text()
            if running:
                raise InstallError(
                    "This app is running. Close Turbo Tides, then retry; the current app is unchanged."
                )
        except (OSError, UnicodeError):
            # Processes can exit between enumeration and inspection.
            continue


def require_managed(destination):
    marker = destination / MARKER
    if destination.is_symlink() or (
        destination.exists() and (not marker.is_file() or marker.is_symlink())
    ):
        raise InstallError(f"Refusing to replace an unmanaged directory: {destination}")


def integration_paths(bin_dir, data, desktop):
    paths = [bin_dir / "turbo-tides"]
    if desktop:
        paths.append(data / "applications/turbo-tides.desktop")
        paths.extend(
            data / f"icons/hicolor/{size}x{size}/apps/turbo-tides.png"
            for size in (32, 64, 128, 512)
        )
        paths.append(data / "icons/hicolor/scalable/apps/turbo-tides.svg")
    return paths


def owned_entry(path, content, destination, replacement=None):
    if path.name == "turbo-tides":
        launch = f"exec {shlex.quote(str(destination / 'launch.sh'))} ".encode()
        return COMMAND_MARKER.encode() in content and launch in content
    if path.suffix == ".desktop":
        launch = f"Exec=/bin/sh {desktop_quote(destination / 'launch.sh')}".encode()
        legacy = f'Exec="{destination}/bin/TurboTides"'.encode()
        return (
            DESKTOP_MARKER.encode() in content
            and launch in content
            or (destination / MARKER).is_file()
            and legacy in content
        )
    name = (
        "icon.svg"
        if path.suffix == ".svg"
        else f"icon-{path.parts[-3].split('x')[0]}.png"
    )
    original = destination / "src/main/resources/art" / name
    return (
        content == replacement
        or original.is_file()
        and content == original.read_bytes()
    )


@contextmanager
def transaction_directory(parent):
    work = Path(tempfile.mkdtemp(prefix=".turbo-tides-install-", dir=parent))
    try:
        yield work
    finally:
        if (work / "previous").exists():
            # Never let temporary-directory cleanup erase a backup if rollback
            # itself failed (for example, the disk became read-only).
            print(f"Previous app retained for recovery: {work / 'previous'}")
        else:
            shutil.rmtree(work)


def refresh_desktop(data):
    for command_line in (
        ["update-desktop-database", str(data / "applications")],
        ["gtk-update-icon-cache", "-f", "-t", str(data / "icons/hicolor")],
    ):
        if shutil.which(command_line[0]):
            result = subprocess.run(
                command_line,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode:
                print(
                    f"Icon/menu cache refresh was unavailable: {result.stderr.strip()}"
                )


def install_locked(app, destination, bin_dir, desktop):
    home = Path.home()
    bin_dir = safe_path(bin_dir or home / ".local/bin")
    data = safe_path(xdg_path("XDG_DATA_HOME", home / ".local/share"))
    require_managed(destination)
    version = validate_app(app)
    command = bin_dir / "turbo-tides"
    files = {
        command: (
            f'#!/bin/sh\n{COMMAND_MARKER}\nexec {shlex.quote(str(destination / "launch.sh"))} "$@"\n'.encode(),
            0o755,
        )
    }
    entry = data / "applications/turbo-tides.desktop"
    if desktop:
        content = (
            "[Desktop Entry]\nType=Application\nName=Turbo Tides\n"
            "Comment=Race six coastal and city circuits. Play offline.\n"
            f"Exec=/bin/sh {desktop_quote(destination / 'launch.sh')}\n"
            "Icon=turbo-tides\nTerminal=false\nCategories=Game;SportsGame;\n"
            "StartupWMClass=Turbo Tides\nStartupNotify=true\n"
            f"{DESKTOP_MARKER}\n"
        )
        files[entry] = (content.encode(), 0o644)
        for size in (32, 64, 128, 512):
            path = data / f"icons/hicolor/{size}x{size}/apps/turbo-tides.png"
            files[path] = (
                (app / f"src/main/resources/art/icon-{size}.png").read_bytes(),
                0o644,
            )
        files[data / "icons/hicolor/scalable/apps/turbo-tides.svg"] = (
            (app / "src/main/resources/art/icon.svg").read_bytes(),
            0o644,
        )
    previous_files = {}
    for path in files:
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise InstallError(f"Refusing to replace an unrelated entry: {path}")
        if not path.exists():
            previous_files[path] = None
            continue
        old = path.read_bytes()
        if not owned_entry(path, old, destination, files[path][0]):
            raise InstallError(f"Refusing to replace an unrelated entry: {path}")
        previous_files[path] = (old, stat.S_IMODE(path.stat().st_mode))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with transaction_directory(destination.parent) as work:
        staged = work / "app"
        shutil.copytree(app, staged, symlinks=True)
        (staged / "launch.sh").write_text(launcher_text())
        (staged / "launch.sh").chmod(0o755)
        (staged / MARKER).write_text("Managed by Turbo Tides installer\n")
        validate_app(staged)
        if desktop and shutil.which("desktop-file-validate"):
            candidate = work / "turbo-tides.desktop"
            candidate.write_bytes(files[entry][0])
            run(["desktop-file-validate", str(candidate)])
        for path in files:
            path.parent.mkdir(parents=True, exist_ok=True)
        backup = work / "previous"
        changed = []
        installed = False
        try:
            if destination.exists():
                destination.rename(backup)
            staged.rename(destination)
            installed = True
            for path, (content, mode) in files.items():
                write_atomic(path, content, mode)
                changed.append(path)
        except BaseException:
            try:
                for path in reversed(changed):
                    old = previous_files[path]
                    if old is None:
                        path.unlink(missing_ok=True)
                    else:
                        write_atomic(path, *old)
            finally:
                # Even a failed metadata rollback must restore the working app.
                if installed:
                    shutil.rmtree(destination)
                if backup.exists():
                    backup.rename(destination)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    if desktop:
        refresh_desktop(data)
    print(f"Installed Turbo Tides {version}: {destination}")
    print(f"Launch command: {command}")
    if desktop:
        print("Open your application menu and choose Turbo Tides.")
    if str(bin_dir) not in os.environ.get("PATH", "").split(os.pathsep):
        print(
            f"For a short terminal command, add {shlex.quote(str(bin_dir))} to PATH. The app-menu icon works now."
        )
    return destination


def uninstall_app(destination=None, bin_dir=None, desktop=True):
    home = Path.home()
    destination = safe_path(destination or home / ".local/opt/turbo-tides")
    bin_dir = safe_path(bin_dir or home / ".local/bin")
    data = safe_path(xdg_path("XDG_DATA_HOME", home / ".local/share"))
    with app_lock(destination):
        require_managed(destination)
        if not destination.exists():
            raise InstallError(f"No managed app is installed at {destination}.")
        files = {}
        for path in integration_paths(bin_dir, data, desktop):
            if not path.exists() and not path.is_symlink():
                continue
            if path.is_file() and not path.is_symlink():
                content = path.read_bytes()
                if owned_entry(path, content, destination):
                    files[path] = (content, stat.S_IMODE(path.stat().st_mode))
                    continue
            print(f"Preserving an unrelated or modified entry: {path}")
        with transaction_directory(destination.parent) as work:
            backup = work / "previous"
            changed = []
            destination.rename(backup)
            try:
                for path in files:
                    path.unlink()
                    changed.append(path)
            except BaseException:
                try:
                    for path in reversed(changed):
                        write_atomic(path, *files[path])
                finally:
                    backup.rename(destination)
                raise
            shutil.rmtree(backup)
    if desktop:
        refresh_desktop(data)
    print(
        f"Removed Turbo Tides from {destination}. Player saves and launch logs are preserved."
    )


def write_atomic(path, content, mode):
    descriptor, name = tempfile.mkstemp(prefix=".turbo-tides-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--app", type=Path, help="install an already-built/extracted app directory"
    )
    source.add_argument(
        "--archive",
        type=Path,
        help="install a local release archive (requires --checksum)",
    )
    source.add_argument(
        "--uninstall",
        action="store_true",
        help="remove this managed app; keep player saves and logs",
    )
    parser.add_argument("--checksum", type=Path, help="SHA-256 file for --archive")
    parser.add_argument(
        "--version", help="download a particular release, e.g. 1.2.0; default: latest"
    )
    parser.add_argument("--prefix", type=Path, help="dedicated absolute app directory")
    parser.add_argument("--bin-dir", type=Path, help="absolute command directory")
    parser.add_argument(
        "--no-desktop",
        action="store_true",
        help="install the command without menu/icon integration",
    )
    parser.add_argument(
        "--no-system-deps",
        action="store_true",
        help="check native desktop dependencies without installing missing packages",
    )
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        parser.error(
            "This release installer supports Linux x86-64. macOS and other architectures are not yet packaged."
        )
    libc, libc_version = platform.libc_ver()
    if libc != "glibc" or tuple(map(int, libc_version.split(".")[:2])) < (2, 28):
        parser.error(
            "The Linux runtime requires glibc 2.28 or newer (a supported desktop distribution)."
        )
    if os.geteuid() == 0 and os.environ.get("SUDO_USER"):
        parser.error(
            "Run the installer as your ordinary user, without sudo. Only missing system dependencies request elevation."
        )
    if args.version and (
        args.app
        or args.archive
        or args.uninstall
        or not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", args.version)
    ):
        parser.error(
            "--version must be a release version and cannot accompany --app/--archive/--uninstall"
        )
    if bool(args.archive) != bool(args.checksum):
        parser.error("--archive and --checksum must be supplied together")
    try:
        # Resolve dangerous destination choices before any downloads/system work.
        if args.prefix:
            safe_path(args.prefix)
        if args.bin_dir:
            safe_path(args.bin_dir)
        if args.uninstall:
            uninstall_app(args.prefix, args.bin_dir, not args.no_desktop)
            return
        ensure_dependencies(not args.no_system_deps)
        with tempfile.TemporaryDirectory(prefix="turbo-tides-download-") as temporary:
            folder = Path(temporary)
            if args.app:
                app = args.app.resolve()
            else:
                archive, checksum = (
                    (args.archive, args.checksum)
                    if args.archive
                    else download_release(folder, args.version)
                )
                verify_archive(archive, checksum)
                app = extract_archive(archive, folder / "extracted")
            install_app(app, args.prefix, args.bin_dir, not args.no_desktop)
    except (
        InstallError,
        OSError,
        ValueError,
        tarfile.TarError,
        zipfile.BadZipFile,
        subprocess.CalledProcessError,
    ) as exception:
        parser.exit(
            1,
            f"Turbo Tides installation failed: {exception}\nExisting saves are preserved.\n",
        )


if __name__ == "__main__":
    main()
