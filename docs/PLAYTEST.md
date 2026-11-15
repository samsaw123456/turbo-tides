# Verification for 1.3.0

The tested JAR SHA-256 is
`cfd8fd13e4f2625b053914a289c7ed5d397594f8ce8b463fca038d8d0cc3d882`.
The source build, immutable audit copy and installed app must match that hash.
Earlier 1.2 evidence is retained in [verification-1.2.0.json](evidence/verification-1.2.0.json).

## Difficulty and gameplay

Four named levels now change rival pace, corner confidence and acceleration
response. The [difficulty guide](DIFFICULTY.md) contains measured times for all
24 circuit/level combinations. Every position in the AI field finishes at least
5% sooner at each step. Digital steering tests win Easy without boost and Medium
with pads. Skilled digital driving adds controlled drifts to win all six
circuits on both harder settings. Player physics is unchanged.

The same native keyboard driving strategy collected pads and used boost on
San Francisco at every level:

| Level | Finish | Time | Pads |
| --- | ---: | ---: | ---: |
| Easy | 1 / 6 | 55.47 s | 9 |
| Medium | 1 / 6 | 54.84 s | 9 |
| Hard | 3 / 6 | 55.30 s | 9 |
| Super Hard | 6 / 6 | 54.90 s | 9 |

A separate Super Hard run used real W/A/D/Space/Shift events and finished first
in 47.28 s, with 43 drift bonuses and 8 pads. The
three lap frames, drift/boost effects, rival positions and result screen were
captured and inspected. The scripts read diagnostics but never modify simulation
state, grant fuel or skip laps.

A six-circuit sweep also completed the full race loop:

| Circuit | Level | Time | Finish |
| --- | --- | ---: | ---: |
| Sunset | Easy | 41.57 s | 1 / 6 |
| Cinder | Medium | 38.69 s | 1 / 6 |
| San Francisco | Easy | 55.30 s | 1 / 6 |
| Silicon Valley | Medium | 45.04 s | 1 / 6 |
| New York | Easy | 46.22 s | 1 / 6 |
| Chicago | Medium | 45.84 s | 1 / 6 |

A deliberate loss finished sixth in 131.69 s, then retried and returned
to the garage. Result-menu keyboard, shortcut and mouse actions were exercised.

## Controls, UI and saved records

All 49 rows in [CONTROLS.md](CONTROLS.md) passed again on this build, including
every alternate steering/throttle/brake/boost binding, press/hold/release,
opposing inputs, each menu state, pause, restart, focus loss and camera recovery.
Left and A visibly move screen-left; Right and D move screen-right. Rear view
retains the documented car-relative convention. Game-only PCM verifies mute,
unmute, pause and mute-through-resume; a flag alone is not accepted as audio proof.

Difficulty selection was checked with Left, Right, Enter and clicks through all
four options and wraparound at 1280×800 and 960×640. Holding Right advances once.
The level remains legible in the garage, race HUD, pause and result screen.
Each level's retry preserves that setting. Old Cruise/Race records load as
Easy/Medium; the new levels begin with separate empty records. All 24 record
slots and settings match after relaunch with the installed bundled runtime,
including a saved Super Hard selection. The original SF route record remains
untouched, and Esc closes the actual window from the garage.

## Checks and reproduction

`./gradlew ktlintFormat check fatJar` passes Kotlin lint and **34 tests**.
Ruff check/format, Python compilation and **31 installer/package tests** pass.
The existing collision, stopped-car overtaking, 10/240 and 30/144 FPS physics,
track continuity, pad/drift, audio and projection regressions also pass.

Launch with `--telemetry /absolute/path/state.json`, isolated Java user.home,
and an X display. Set `TURBO_TEST_TELEMETRY` to that path and
`TURBO_TEST_OUTPUT` to a separate evidence directory, then run:

```sh
python3 tools/city_playtest.py menu
python3 tools/difficulty_playtest.py menu
python3 tools/control_audit.py
python3 tools/control_audit.py --holds-only
python3 tools/control_audit.py --presentation-only
python3 tools/control_audit.py --states-only
python3 tools/control_audit.py --focus-only
python3 tools/city_playtest.py circuits
python3 tools/playtest.py loss
python3 tools/difficulty_playtest.py races
python3 tools/difficulty_playtest.py skill
```

Native tools require X11/XTest, libX11, libXtst, xwininfo, xprop and Pillow or
ImageMagick. Audio capture requires PipeWire tools and connects only the game's
output ports. The [audio guide](AUDIO-AUDIT.md) describes the separate cue audit.
Committed [measurements](evidence/verification.json) include the final JAR hash,
per-control outcomes, race states, audio measurements and inspected frame hashes.
Raw evidence is retained under `build/difficulty-playtest/` and
`build/difficulty-review/`; failed desktop injection is retained separately.

## Audit correction

The first isolated drift capture kept steering for additional render-settling
frames after Space was released; on the slow software renderer it reached a
barrier after successfully awarding the bonus. The driver now captures the
first acknowledged bonus frame promptly, with no extra settling delay. All four
drift bindings passed again with the original no-contact/no-pad assertions. The
failed capture is retained under `build/difficulty-review/presentation-before-timing/`.
Game physics was unchanged by this test-driver correction.

## Limits

The initial saved-record migration rendered on Intel hardware through XWayland.
That desktop subsequently rejected injected key acknowledgements, so the complete
native control/gameplay audit used an isolated Xvfb display with the real
GLFW/libGDX interface and software rendering. Captured frames were inspected;
this is not a new hardware-performance benchmark. Host load affects software FPS.
Linux x86-64 is verified; no Windows, macOS, touch or gamepad test is claimed.
Captured PCM verifies output, not subjective speaker/headphone sound quality.
Missing-dependency package-manager paths are fixture-tested; this host already
had the required system libraries. The city routes are stylized fictional
circuits, not street maps.
