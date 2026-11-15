# Verification for 1.2.0

The final native audit used the unchanged JAR at
`build/playtest/final-audit.jar`, SHA-256
`62ce617d3d4484c1f6fa37c268cb5b9a3c23f19644b070a84a281c0608267443`.
The installed app's JAR was checked against that same hash.

The original 1.0 verification missed reversed visible steering because it
checked lane values and completed races without proving each key's rendered
effect. That was a verification failure. Regression tests now independently
check screen projection at 24 positions on every circuit; the native audit
presses A, Left, D and Right separately and inspects their actual motion.

## Checks and corrections

`./gradlew check fatJar` passes Kotlin lint, compilation and **30 tests**.
Coverage includes all six circuits at both rival paces, complete wins and a
losing finish/retry, steering authority, drift rewards, pad latching, pause,
contact recovery, track continuity, bridge geometry and camera direction.
Fixed-step outcomes agree at 10/240 FPS as well as 30/144 FPS.

Python passes Ruff lint/format checks, `python3 -m py_compile tools/*.py`, and
**31 installer/packaging tests**. Installer fixtures exercise missing Python,
shared libraries and `flock`, offline installation, checksum/archive rejection,
failed downloads, interrupted upgrades, rollback, running-app protection,
paths containing spaces and special characters, and save preservation.
The shell entry points pass syntax checks.

Review found and fixed undersized car contacts, angled-car barrier clipping,
collision cooldown allowing overlap, rivals driving through each other, and
rivals queuing indefinitely behind a parked player. Contacts now cover the
visible chassis/wheels and their angle, with clearance maintained during the
feedback cooldown. Rivals choose passing lanes. All opponents finish around a
parked player on all six circuits at both paces. An independent 48-scenario
contact probe found no meaningful overlap or backwards corrections; its
largest residual overlap was 0.000087 m, within floating-point tolerance.

Other fixes include duplicated/missed audio cues, GO replay on resume,
transient sounds surviving pause/retry, fullscreen restoration, straight and
level SF bridge geometry, roadside gantry clearance, shadows on slopes and
exhaust that follows the car's transform. The changed SF route uses new record
keys while preserving old saved values.

## Native controls and presentation

The real GLFW/libGDX interface was exercised on Mesa Intel UHD Graphics
(CML GT2) through XWayland, with isolated test preferences. Keyboard events use
XTest with X-server acknowledgement of press/release; hardware pointer tests
use native X11 window events where XWayland drops synthetic pointer input.
Telemetry is read-only: the scripts do not teleport cars, set fuel or skip laps.

The main audit passed **32 evidence groups**, followed by held-key,
presentation, per-state and focus-release audits. The
[49-row control inventory](CONTROLS.md) covers alternate keys, opposing chords,
menu actions, disabled inputs, focus loss, restart and camera recovery.
An independent reviewer inspected all 72 requested moving-control frames:
normal-view left/right directions, documented mirrored rear-view steering,
boost/drift appearance and release, braking, stopped inputs and opposing keys.
W and Up visibly accelerated from 0 to 141/146 km/h, then coasted to 70/75 km/h;
S and Down stopped at 0. All four drift bindings showed a release bonus.

All six circuit previews and grids, paint/pace controls and menus were inspected
at 1280×800 and 960×640. Fullscreen reached 4096×2304 and returned to the
previous window size. City landmarks remain stylized miniature race circuits,
not geographic street-map replicas.

## Complete races

Every circuit finished first in the final native sweep, alternating rival paces:

| Circuit | Pace | Measured time | Pads | Contacts |
| --- | --- | ---: | ---: | ---: |
| Sunset Run | Cruise | 41.29 s | 9 | 1 |
| Cinder Ring | Race | 38.87 s | 9 | 1 |
| San Francisco | Cruise | 55.16 s | 9 | 1 |
| Silicon Valley | Race | 45.19 s | 9 | 0 |
| New York City | Cruise | 45.92 s | 9 | 1 |
| Chicago | Race | 45.69 s | 9 | 1 |

New York used 960×640 with reduced motion; the other races used 1280×800.
Chicago retained reduced motion. All six result screens and the available lap
frames were visually inspected. The later loss run replaced Chicago's three
lap captures; those are now explicitly named `loss-chicago-lap-*`, while
`finish-chicago.png` and `city-races.json` retain its winning result.

The deliberate Chicago loss waited for opponents, then completed three laps
in sixth place in **131.82 s**, collected nine pads, retried with R and returned
to the garage. Its 960×640 result screen showed the correct rank, time and retry
controls. During the six-race sweep, 1,086 racing samples measured **120–121 FPS,
median 121**, on this machine. The nominal cap is 120; libGDX's reporting window
can read 121. These measurements do not predict other hardware's performance.

## Audio and installed entry

Game-only PipeWire PCM confirmed sound→silence→sound for menu and race mute
controls. Mute, pause and mute-through-resume produced zero samples. A separate
Xvfb run on the same final JAR matched the actual GO waveform with correlation
0.9990, found no GO replay on resume, and matched three consecutive pad cues at
0.9994, 0.9997 and 0.9671. A labelled generated duplicate-cue fixture checks that
the detector rejects the earlier bug. No microphone or system mix was captured;
this is output verification, not subjective speaker/headphone listening.
See [audio reproduction and detector limits](AUDIO-AUDIT.md).

After installed-app relaunch, settings and all 12 circuit/pace record slots
(including empty slots) matched exactly. The bundled runtime was confirmed in
the running process, and Esc closed the app normally. GIO loaded the installed
desktop entry in normal mode, launched the game and exited successfully without
changing production preferences. GTK's icon theme loaded the actual installed
64-pixel game icon. Published-download validation is not claimed by these checks.

The installed app also ran inside a separate network namespace using
`bwrap --unshare-net`. A connection probe in that same namespace failed with
`ENETUNREACH`; the game then completed Chicago/Race first in **45.50 s**, collected
nine pads, returned to the garage and exited normally. All three lap frames,
the result and garage were inspected. Evidence is in `build/offline-playtest/`.

## Reproduction and evidence

Launch the game with `--telemetry /absolute/path/state.json`, isolated
preferences, and an X display. Set `TURBO_TEST_TELEMETRY` to that file and
`TURBO_TEST_OUTPUT` to a separate evidence directory. Use
`TURBO_TEST_NATIVE_POINTER=1` for the XWayland pointer fallback.

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

Native input tools require X11/XTest, libX11, libXtst, xwininfo and xprop;
frame capture uses Pillow or ImageMagick. Audio capture requires PipeWire tools.
Raw logs, frames and measurements are retained in ignored `build/playtest/`,
including `city-races.json`, `loss.json`, `fps-samples.json`, control-audit JSON,
and `review-final/{physics-review,races-review}.json` with reviewed image hashes.
Final audio evidence is in `build/audio-review-native/`. Earlier failed
regressions and the corrected silence-normalization detector trace were retained.

Only Linux desktop was exercised. No Android, touch, gamepad, Windows or macOS
playtest is claimed. Software rendering was also exercised, but its frame rate
varied with shared host load; stalled frames are clamped instead of advancing
physics through unobserved time.
