# Verification for the city update

## Steering failure and regression

The initial 1.0 playtests drove complete races but did not establish the visible
direction of each steering key. Their lane-value checks missed a reversed road
basis. That was a verification failure, not evidence that steering worked.

The new perspective-camera regression was run against the old implementation
and failed: positive lane projected left of the road center. The corrected
basis is forward crossed with world-up. Camera projection is checked at 24
positions on each of six circuits. Corner force, car yaw, surface winding and
pad rendering now use the same convention.

The native audit separately presses A, D, Left and Right and captures the actual
rendered result. It reads diagnostic output but does not teleport cars, modify
fuel, skip laps or write simulation state. The complete coverage inventory is
[CONTROLS.md](CONTROLS.md). Both key bindings must work; a successful race alone
does not establish that.

Other corrections found during this work:

- Pads require movement and trigger once per pad per lap; parking on a pad
  cannot repeatedly award boosts.
- Finished opponents leave the course and cannot collide with later finishers.
- Corner force is bounded so full steering remains effective during nitro.
- Rear view returns immediately on release, avoiding a camera sweep through the
  car. The temporary view explicitly explains car-relative steering.
- Only primary mouse clicks activate menus.
- Hovering one route and pressing Enter now starts that focused route. The
  native regression reproduced the previous behavior: San Francisco had focus,
  but Enter started the previously selected Sunset Run. Left/Right browsing
  now uses that same focus, including after pointer movement.
- Native buffer synchronization stalled at 1–2 FPS on the tested desktop.
  Disabling that wait restored responsive rendering; the app retains its
  120 FPS render cap and independent fixed-step physics.
- Bridge cable segments share correctly oriented endpoint transforms; a
  regression checks uphill, downhill and vertical anchors.
- Circuit maps fit their actual bounds, and menu labels clear focus indicators.

## Automated checks

`./gradlew ktlintFormat`, followed by `./gradlew check fatJar`, passes lint,
compilation and 20 tests. Coverage includes countdown gating, pause/resume,
30/144 FPS equivalence, braking and grass drag, barrier/contact recovery, moving
drift rewards, pad latching and nitro consumption, boost speed limits, complete
wins on all six circuits at both rival paces, a losing finish and clean restart,
continuous/wrapped track geometry, road widths, grades and separated road
sections, steering at boost speed, screen-space direction, and cable anchors.

Python tools pass `ruff check tools`, `ruff format --check tools`,
`python3 -m py_compile tools/*.py`, and two packaging unittests.
The launcher passes `bash -n turbo-tides`.

## Native runs

The final source JAR and the installed app share SHA-256
`2d4325bcfff4bd4a2ed0430d7afe69c4657f4ba0fa59225c151d386895bc01fe`.
The actual LWJGL window is driven with XTest on an isolated Xvfb display,
then tested on Intel UHD hardware graphics through XWayland. Keyboard events
use XTest in both. The hardware mouse pass uses native X11 window events because
XTest pointer events did not reach GLFW on this desktop. Both exercise real input
handlers, menus, simulation and rendering.
Telemetry uses separate `turbo-tides-playtest` preferences and local JSON.
No game data leaves the computer. Rendering is inspected at 1280×800,
960×640 and fullscreen.

The final six-race sweep on the installed app finished first on every circuit.
It alternated rival paces and exercised every result-menu action (keyboard,
shortcut and mouse):

| Circuit | Pace | Three-lap time | Pads | Contacts |
| --- | --- | ---: | ---: | ---: |
| Sunset Run | Cruise | 40.81 s | 9 | 0 |
| Cinder Ring | Race | 38.68 s | 9 | 0 |
| San Francisco | Cruise | 43.41 s | 9 | 0 |
| Silicon Valley | Race | 45.14 s | 9 | 0 |
| New York City | Cruise | 45.25 s | 9 | 0 |
| Chicago | Race | 45.09 s | 9 | 0 |

New York ran at 960×640 with reduced motion; the other final races used 1280×800.
The test scripts drove complete races using real held keys and read-only
diagnostics. The losing-race and packaged-app results are recorded below.

A separate Chicago run deliberately waited for the rivals, then finished
sixth in 131.92 seconds with nine pads. R reset the completed race to a fresh
countdown; pause-menu navigation returned to the garage. The 960×640 result
screen was inspected. Esc from the garage closed the actual native window.

The menu audit covers all six city/natural scenes and grid views, mouse and
keyboard selection, wraparound, paint and pace changes, sound/motion toggles,
rapid repeated selection, resizing, and fullscreen. The mechanics audit covers
steering in both directions through both bindings, opposing inputs, braking,
moving drift/release, nitro, shoulder/wall recovery, rear view, freeze/resume,
focus loss, and reset during countdown.

The main control audit passed 32 evidence groups, followed by held-key,
presentation, per-state and extended focus-release passes. All 49 rows in the
control inventory passed; their observed outcomes and evidence are recorded. Every W/Up, S/Down, A/Left, D/Right and Shift alternative is
exercised separately. The [steering frames](screenshots/steering-check.png) show
left/right road-relative movement; [rear-view frames](screenshots/rear-view-check.png)
show the documented mirrored convention and restoration of forward chase view.
W and Up release frames show visible speeds falling from 138 to 86 km/h and
146 to 92 km/h respectively.

The isolated [drift-release frames](screenshots/drift-release-check.png) show
Space+A, Space+D, Space+Left and Space+Right each displaying the release bonus.
Each run had zero bonuses while held and exactly one after release. Nitro rose
61.65→82.84, 61.29→81.43, 60.39→81.64 and 62.34→81.58 respectively, with no pad
or contact during the measured sequence. Earlier captures that let a drift run
off-road or showed a delayed framebuffer were rejected and recaptured; passing
an internal assertion was not accepted as sufficient visual evidence.

Audio was captured directly from the game's two output ports, in 48,000-frame
PCM segments. Menu sound had RMS 200.69, mute had RMS/peak 0, and restoration
had RMS 173.60. Racing measured RMS 302.74→0→310.39. Pause and mute-through-resume
also produced zero samples. Held M/N/P/F11, R, Esc, Enter, navigation and both
Shift+Tab bindings were checked for repeated activation.

Reproduce with the app running using
`--telemetry /tmp/turbo-tides-playtest.json` and DISPLAY pointing to its X server:

```sh
python3 tools/city_playtest.py menu
python3 tools/control_audit.py
python3 tools/control_audit.py --holds-only
python3 tools/control_audit.py --presentation-only
python3 tools/control_audit.py --states-only
python3 tools/control_audit.py --focus-only
python3 tools/city_playtest.py circuits
python3 tools/playtest.py loss
```

For the XWayland pointer fallback, set `TURBO_TEST_NATIVE_POINTER=1`.
Set `TURBO_TEST_TELEMETRY` if the app writes diagnostics to a non-default path.

Native scripts require X11/XTest, libX11, libXtst, xwininfo and xprop; screenshots
use Pillow or ImageMagick.
The complete control audit also uses Pillow and PipeWire’s pw-dump, pw-record
and pw-link to compare
rendered pixels and capture only the game's output ports. It never connects to
a microphone or records the system-wide mix. Screenshots, PCM and measurements
are retained under ignored `build/playtest/`.

## Packaging and limits

The Linux package includes a runtime built using a complete Eclipse Temurin
21.0.13+9 JDK whose download was checked against its upstream SHA-256.
The installed 1.1.0 app was relaunched and every circuit/pace best-time slot
was compared, along with paint, sound, reduced motion, selected route and pace.
The bundled runtime was confirmed in the running process's mapped libraries.
`gtk-launch turbo-tides` loaded the actual desktop entry in normal mode, showed
the six-route menu and exited through Esc. Production preferences retained their
original SHA-256 throughout testing.

A final hardware run with all six scenes cached completed New York/Race in
44.98 seconds and Sunset/Race in 40.86 seconds, both first with nine pads and
zero contacts. Sampled FPS was 120–121 (median 121) on Mesa Intel UHD Graphics
(CML GT2); wall times including countdown were 48.28 and 44.15 seconds.
The nominal render cap is 120; libGDX's once-per-second counter can read 121.
This is one machine's measurement, not a guarantee for other hardware.

The relocatable package is also exercised from a directory containing spaces,
with a different working directory. Release archives include a SHA-256 file.
Selected screenshots and [measurements](evidence/verification.json) are committed;
raw JSON, PCM, screenshots and run logs remain in ignored `build/playtest/`.

Only Linux desktop is exercised. No Android, touch, gamepad, Windows or macOS
playtest is claimed. The isolated software renderer shares CPU with other work;
observed frame rates vary with host load, so physical input durations are
measured against simulation time. The game clamps stalled frames rather than
fast-forwarding physics. Hardware rendering and package launch are checked
separately. Audio mute is assessed through captured PCM levels; this does not
constitute a subjective sound-quality review.
