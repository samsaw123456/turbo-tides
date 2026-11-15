# Quality review — 1.2.0

This review applies the recurring requirements from the user's recent local
Codex sessions: literal control coverage, independent adversarial review,
physics and state consistency, visible/audible feedback, current JVM tooling,
easy installation, app-menu integration, offline play, safe updates, clear
README instructions and honest platform limits. Unrelated projects and private
session transcripts are not included here.

## Findings and corrections

| Finding | Change | Verification |
| --- | --- | --- |
| Small collision bounds let visible cars overlap | Shared car dimensions, yaw-aware projected bounds, separation independent of feedback cooldown | Regressions reproduced the original defect before the fix; final native race audit |
| Solid cars could leave rivals queued behind a parked player | Rivals choose a clear passing lane and wait for rear clearance before returning | All six circuits, both paces, parked-player and complete-race tests |
| Pause/resume replayed GO; identical consecutive messages lost their sound cue | Explicit audio event identity and countdown-to-GO transition | Four audio regressions plus [native cue waveform correlation](AUDIO-AUDIT.md) |
| Shadows and exhaust ignored road/car orientation | Rendered effects use road pitch and the complete car transform | Slope, drift and boost frame review |
| San Francisco's suspension bridge followed a bend | Straight, level span with continuous cables, stepped portals and separate hill district | Span/grade/join regressions and bridge drive-through |
| Cities shared generic island surroundings | Bay channel, inland campus, river edges and east-side lakefront; distinct architectural massing | All six previews and races, 960×640 and 1280×800 UI checks |
| Installer required developer tools | Standalone installer, bundled Java 25, automatic missing system dependencies | Isolated-home install and actual desktop activation |
| Fullscreen restoration lost the title-bar height on XWayland | Reconcile saved client bounds after the asynchronous decoration change | Repeated native toggles restore exact size and position |
| New LWJGL defaults changed the Linux window backend | Select X11 when DISPLAY is available, including XWayland | Native app/control audit and CI software-rendered smoke |
| Native test injection lost immediately repeated key edges on this XWayland desktop | Wait for X11 key-state acknowledgement before sending the next edge; clean up attempted presses | Both Shift+W re-press probes and the complete native audit; no game-state injection |
| Localized JDK help could reject a valid packaging toolchain | Use English only for the capability probe | Actual Japanese-locale Temurin25 probe and regression |
| Desktop log setup could fail without a visible error | Share the launch error notifier with log creation/rotation failures | Failure-path fixtures verify both the exit status and notifier |
| Source launcher could use an old package or incompatible system Java | Run the current checkout through the configured Java 25 Gradle toolchain | Source launcher and packaged runtime checks |

The complete physical-binding inventory and per-state results are in
[CONTROLS.md](CONTROLS.md). Commands, measurements, screenshots and limitations
are in [PLAYTEST.md](PLAYTEST.md) and [verification.json](evidence/verification.json).
Installation behavior is documented in [INSTALLATION.md](INSTALLATION.md).

## Installation verification

All 31 installer/package tests passed on Linux, including actual isolated
HOME/XDG installs, repeated updates, damaged-app repair, offline archive use,
uninstall with save preservation, failed downloads/checksums/archives,
unmanaged-path protection and filesystem rollback. A rollback-failure regression
also proves that the previous app remains in a reported recovery directory.
The tests execute generated standalone installers outside the checkout and load
a generated desktop entry through GIO with spaces, percent signs, shell
metacharacters and Unicode in its paths. Running fixture games block both update
and uninstall without being stopped. Ruff, Python compilation, shell syntax and
ShellCheck pass for the installer, bootstrap and generated launch scripts.

The public 1.1.0 archive and checksum were downloaded over HTTPS and installed
into an isolated user tree. Its bundled native runtime launched successfully on
a separate Xvfb display; the rendered garage was captured and inspected. While
that real game ran, an update attempt failed safely, leaving the 1.1.0 app and
running process intact. After closing it, the actual Java 25 archive built for
1.2.0 was installed offline, diagnosed and uninstalled; the saved record remained.
This proves the installer flow and earlier-release compatibility. Publication verification is recorded separately in the release notes.

Local evidence is retained in `build/installer-tests.log` and
`build/installer-smoke/`: `network-install.log`, `installed-v1.1-menu.png`,
`running-update.log` and `offline-update-uninstall.log`. System packages were
already present on the host. Missing Python/certificate, native-library and
`flock` branches use controlled package-manager fixtures, so dependency
installation on fresh apt/dnf/pacman/zypper systems remains unverified. No macOS,
Windows, ARM or musl-based installation is claimed.

The final app's 36 Linux x86-64 ELF files were checked with `readelf` dynamic
symbols and version requirements. LWJGL and OpenAL require at most
`GLIBC_2.28`; the bundled Java runtime requires at most `GLIBC_2.17`. No hidden
`GLIBC_PRIVATE` or newer RELR requirement was present. OpenAL additionally needs
`GLIBCXX_3.4.22`, `CXXABI_1.3.11` and `GCC_4.3.0`, so the installer now explicitly
checks and provisions the C++ and GCC runtime libraries. Every `DT_NEEDED`
dependency resolves on this host when using the bundled JVM's library paths.
Per-library requirements and hashes are recorded in
`build/abi-review/abi-report.json`. This validates the ABI floor, not execution
on every older distribution.

The installed final game also completed a Chicago race with networking disabled
in a separate network namespace, then returned to the garage and exited normally.
A network probe in that same namespace confirmed that the internet was unreachable.
See `build/offline-playtest/` and the committed verification summary.

## City design references

These are original low-poly interpretations with compressed, fictional race
routes. They are designed for readable arcade racing, not geographic navigation
or architectural measurement. No photographs or third-party models are copied.

- San Francisco: International Orange, stepped Art Deco tower portals and vertical
  details follow the [Golden Gate Bridge district's design history](https://www.goldengate.org/bridge/history-research/bridge-features/color-art-deco-styling/).
  Hillside houses have bay windows and porches. The tapered skyline landmark draws
  on the [Transamerica Pyramid's history](https://transamericapyramid.com/transamerica-pyramid).
- Silicon Valley: low campus buildings, a circular courtyard, solar roofs,
  planted grounds and surrounding hills; no company logos or claimed exact campus map.
- New York: stepped tower setbacks and a slender spire refer to the
  [Empire State Building's architecture](https://www.esbnyc.com/about/architecture-design),
  alongside a layered metallic crown, taxis and an urban park.
- Chicago: nine bundled towers at varying heights refer to the
  [Willis Tower structure](https://www.architecture.org/online-resources/buildings-of-chicago/willis-tower).
  Round twin towers refer to Marina City, described by the
  [Chicago Architecture Center](https://www.architecture.org/online-resources/architecture-encyclopedia/massing).
  The elevated train and eastern lakefront distinguish the route from New York.

All solid scenery sits outside the drivable corridor, or overhead with clearance.
The start gantry's posts are outside the barriers. The arcade physics keeps cars
on a closed road and does not simulate suspension, jumps or off-course shortcuts.
The changed San Francisco route uses a new best-time key; old records are retained.

## Toolchain and scope

Java 25, Kotlin 2.4.21, Gradle 9.9.1, libGDX 1.14.2 and LWJGL 3.4.3 are pinned.
Gradle downloads are checksum-verified. Runtime downloads used for packaging are
verified against their publisher's checksums. The package contains its own JVM.
Kotlin's [documented fully tested Gradle range](https://kotlinlang.org/docs/gradle-configure-project.html)
ends at 9.7; this project's newer pinned combination is tested locally and in CI.

Linux x86-64 is the packaged platform. Windows, macOS, Android, touch and
controllers are not verified or advertised as supported app targets.
Captured game-only PCM establishes audio output and mute behavior; it does not
establish physical speaker audibility or subjective sound quality.
