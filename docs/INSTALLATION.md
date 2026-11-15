# Installing Turbo Tides

The packaged app supports **Linux x86-64 with glibc 2.28 or newer**, an OpenGL 2.0
desktop and X11 or XWayland. Java 25 is included. Playing the release does not
require a JDK, Git, Gradle or Kotlin. macOS, Windows, ARM and musl-based Linux
distributions are not packaged or validated by this installer.

Use a distribution whose `python3` package provides Python 3.9 or newer; the
bootstrap installs that package but does not add third-party Python repositories.
The native audio library also needs the standard GCC/C++ runtimes
(`libgcc_s.so.1` and `libstdc++.so.6`, including `GLIBCXX_3.4.22` and
`CXXABI_1.3.11`). The installer checks for these libraries and installs the
distribution's runtime packages if they are missing. They are runtime libraries,
not a compiler or developer toolchain.

## Install and open

Run this as your ordinary user:

```sh
(installer=$(mktemp) && trap 'rm -f -- "$installer"' EXIT && curl -fL https://github.com/samsaw123456/turbo-tides/releases/latest/download/install.sh -o "$installer" && sh "$installer")
```

If curl is unavailable, download **install.sh** from the
[latest release](https://github.com/samsaw123456/turbo-tides/releases/latest)
in your browser, then run `sh install.sh` from its download directory.

The standalone script installs missing Python 3.9+ and HTTPS certificates, checks
desktop and GCC/C++ runtime libraries plus `flock`, and downloads the release archive and its SHA-256
file over HTTPS. It verifies the checksum and validates the archive before
replacing an installed app. It uses apt, dnf, pacman or zypper for missing system
packages, with normal sudo, doas or pkexec authentication when needed. It never
asks you to run the whole app installer with sudo. Unsupported distributions get
a specific missing-dependency error rather than an unverified download.

Open **Turbo Tides** from your application menu, or run:

```sh
~/.local/bin/turbo-tides
```

The app and bundled runtime live at `~/.local/opt/turbo-tides`. The menu entry
uses your `XDG_DATA_HOME` (or `~/.local/share`), with the racing-wave icon installed
as SVG and at 32, 64, 128 and 512 pixel sizes. The game works offline after
installation. No telemetry or launch logs are uploaded.

## Updates, repairs and removal

Close the game, then run the same installer again. This also repairs missing or
damaged files in a managed installation. Download, validation and staging happen
before the app is replaced; failed updates restore the previous app and launch
entries. Player records and options are outside the app directory and survive
updates, repair and uninstall.

An update or uninstall while the app is running fails with a clear request to
close it and retry. Installed launchers hold a shared lock for the entire native
process, so an installer cannot delete a running runtime. The installer also
checks for old releases or native executables launched directly. It does not
terminate your game. A launch attempted while replacement is in progress asks
you to wait for the installer to finish.

Remove the app, menu entry, command and unmodified installed icons with:

```sh
sh install.sh --uninstall
```

Or use the installer bundled with the installed 1.3.0 app:

```sh
sh "$HOME/.local/opt/turbo-tides/Install Turbo Tides.sh" --uninstall
```

Uninstall preserves player saves, launch logs and unrelated or modified desktop
entries/icons. It refuses unmanaged directories and symlink installation roots.
If removal fails while updating launch entries, it restores the app and entries.
If the filesystem prevents rollback itself, the installer retains and reports
the backup path instead of deleting the last app copy.

## Offline and portable installation

On a machine with the installer dependencies already available, download
`install.sh`, the release archive and the matching `.sha256` file, then run:

```sh
sh install.sh \
  --archive turbo-tides-1.3.0-linux-x86_64.tar.gz \
  --checksum turbo-tides-1.3.0-linux-x86_64.tar.gz.sha256 \
  --no-system-deps
```

`--no-system-deps` checks native desktop dependencies and refuses missing ones
without invoking their package manager. The shell bootstrap still needs Python
and trusted HTTPS certificates; install these beforehand for a fully offline
machine. No release download is attempted with `--archive` or `--app`.

Alternatively, extract the verified archive to a directory you own and can
write to. Run **Play Turbo Tides** inside `TurboTides` for portable play. Run
`sh "Install Turbo Tides.sh"` from that folder to install it with the menu icon;
this uses the adjacent bundle without downloading it again. The installer can
check and install any missing native desktop dependencies. A relocated or
read-only bundle should be installed into a writable user location before use.

## Installer options

All paths may contain spaces, percent signs and Unicode. Paths supplied for
installation must be absolute and contain no control characters.

| Option | Effect |
| --- | --- |
| `--version 1.3.0` | Download that release instead of the latest one. |
| `--app /absolute/path/TurboTides` | Install a built or extracted local bundle. |
| `--archive FILE --checksum FILE.sha256` | Verify and install a local release archive. |
| `--prefix /absolute/app/path` | Choose a dedicated managed app directory. |
| `--bin-dir /absolute/command/path` | Choose where the `turbo-tides` command is installed. |
| `--no-desktop` | Install/remove the command without touching menu entries and icons. |
| `--no-system-deps` | Check native desktop dependencies without installing missing packages. |
| `--uninstall` | Remove the managed app and its owned launch entries; preserve saves and logs. |
| `--help` | Display all options. |

Keep the same `--prefix`, `--bin-dir` and XDG environment when updating or
uninstalling a custom installation. Relative XDG environment values are ignored
in favor of the standard user defaults. Unrelated files at the intended command,
menu or icon paths are preserved; installation reports the conflict instead of
overwriting them.

## Launch diagnostics

The launcher records native output in
`${XDG_STATE_HOME:-$HOME/.local/state}/turbo-tides/launch.log`, retaining the
previous log as `launch.log.previous`. A failed launch prints the error and log
path, returns the native exit status, and uses an available desktop dialog or
notification tool to show the failure. To inspect the version, installed path
and most recent log:

```sh
~/.local/bin/turbo-tides --diagnose
```

A working OpenGL-capable desktop session is required. Installation can add
missing shared libraries; it cannot supply GPU hardware or repair a broken
display/driver configuration. `--diagnose` works without opening a game window.

## Building from the checkout

The checkout's `./install.sh` uses the same release installer. To develop the
current source, use `./turbo-tides` or `./gradlew run` as described in the
[README](../README.md#build-and-develop). The source launcher runs the configured
Java 25 toolchain and preserves argument boundaries; it does not silently launch
an older app in `dist` or use an incompatible system Java to run new bytecode.

`tools/package_linux.py` uses the same installation and launcher implementation.
It emits the self-contained archive, SHA-256 file and standalone `dist/install.sh`.
Packaging requires a complete Java 25+ JDK with `jpackage` and desktop-capable
`jlink`; JDKs supporting runtime-image linking are accepted without a `jmods`
directory. Set `TURBO_JAVA_HOME` to select one explicitly.

## Verification scope

Installer tests perform actual filesystem installs, updates, launches and removals
in isolated HOME/XDG trees, including spaces, percent signs, shell metacharacters
and Unicode. They load a generated desktop entry with GIO, exercise failed
downloads/checksums/archives, reject escaping links and unmanaged paths, repair a
damaged managed app, preserve saves, recover from failed entry writes/removals,
refuse updates during a running fixture game, and install from an offline archive.
Generated standalone installers are run from outside the checkout.

Missing Python/certificate, desktop-library and `flock` installation branches use
controlled package-manager fixtures; they do not change the host's system
packages or prove every supported distribution. Actual dependency installation
on clean apt/dnf/pacman/zypper systems remains unverified; this Linux host already
had the required libraries. A public 1.1.0 release was downloaded, verified,
installed into an isolated HOME/XDG tree and launched with its bundled runtime.
Its rendered menu was inspected, and an update attempt correctly refused while
that real game kept running. macOS and other architectures remain untested.
The game and physical-input audit is recorded separately in
[the quality review](QUALITY-REVIEW.md).

An ELF ABI audit inspected all 36 Linux x86-64 executables/libraries in the final
app and its JAR. The highest required glibc version is 2.28, in LWJGL and OpenAL;
the bundled Java runtime needs at most 2.17. With the bundled JVM library paths,
all native dependencies resolved on this host. This checks the declared ABI
minimum; it does not replace running on each supported distribution.

Run the installer suite and diagnostics with:

```sh
python3 -m unittest discover -s tools -p 'test_*.py'
python3 -m py_compile tools/install_linux.py tools/package_linux.py tools/test_install.py
sh -n install.sh tools/bootstrap_installer.sh turbo-tides
```
