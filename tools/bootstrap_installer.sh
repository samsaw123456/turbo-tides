#!/bin/sh
# Shared by the checkout wrapper and the generated standalone release installer.
set -eu
ensure_installer_python() {
    case $(uname -s):$(uname -m) in
        Linux:x86_64|Linux:amd64) ;;
        *) printf '%s\n' 'Turbo Tides installer: Linux x86-64 is supported; macOS/other architectures are not packaged yet.' >&2; exit 1 ;;
    esac
    if [ "$(id -u)" = 0 ] && [ -n "${SUDO_USER:-}" ]; then
        printf '%s\n' 'Run this installer as your ordinary user, without sudo. Only missing system packages request elevation.' >&2
        exit 1
    fi
    if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys, ssl, pathlib; assert sys.version_info >= (3, 9); p=ssl.get_default_verify_paths(); assert (p.cafile and pathlib.Path(p.cafile).is_file()) or (p.capath and any(pathlib.Path(p.capath).glob("*.0")))' 2>/dev/null; then return; fi
    printf '%s\n' 'Installing Python 3 and HTTPS certificates for the installer; the game includes Java and needs no developer tools.'
    elevation=
    if [ "$(id -u)" != 0 ]; then
        for candidate in sudo doas pkexec; do
            if command -v "$candidate" >/dev/null 2>&1; then elevation=$candidate; break; fi
        done
        [ -n "$elevation" ] || { printf '%s\n' 'Python 3.9+ is missing. Installing it requires sudo, doas or pkexec.' >&2; exit 1; }
    fi
    if command -v apt-get >/dev/null 2>&1; then
        $elevation apt-get update
        $elevation apt-get install -y --no-install-recommends python3 ca-certificates
    elif command -v dnf >/dev/null 2>&1; then
        $elevation dnf install -y python3 ca-certificates
    elif command -v pacman >/dev/null 2>&1; then
        $elevation pacman -S --needed --noconfirm python ca-certificates
    elif command -v zypper >/dev/null 2>&1; then
        $elevation zypper --non-interactive install python3 ca-certificates
    else
        printf '%s\n' 'Python 3.9+ is missing and no supported package manager was found (apt, dnf, pacman, zypper).' >&2
        exit 1
    fi
    python3 -c 'import sys; assert sys.version_info >= (3, 9)' || { printf '%s\n' 'The system package manager did not provide Python 3.9 or newer.' >&2; exit 1; }
}
