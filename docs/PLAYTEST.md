# Verification

## Automated checks

`./gradlew check` passes Kotlin formatting/lint checks, compilation and 13 tests:
countdown input gating, pause and resume, 30/144 FPS equivalence, braking and
grass drag, barrier/contact recovery, moving drift rewards, pad cooldown and
nitro consumption, the 87 m/s boost limit, complete wins on both circuits,
sixth-place completion and clean restart, continuous track geometry, wrapping,
and road width.

Python tools pass `ruff check tools`, `ruff format --check tools` and
`python3 -m py_compile tools/*.py`. Launch scripts pass `bash -n`.
Two standard-library unittest regressions also pass: reject an incomplete
explicit JDK, and preserve an existing unmarked installation directory.

## Native playtests

The actual LWJGL window was driven with native XTest keyboard and mouse events
on an isolated Xvfb display. The diagnostic JSON was only read; test input did
not teleport cars, skip laps, edit fuel, or change the game rules. Preferences
were isolated using the documented `--telemetry` mode.

Verified interactions:

- Start from garage, countdown, accelerate, brake/steer, and complete three laps.
- First place on Sunset Run and Cinder Ring. The Cinder run finished in 38.69 s
  with nine turbo pads and no collisions after restart.
- Hold Space and steer to drift; release it and receive a nitro bonus.
- Drive into the barrier, slow on the shoulder, then steer back onto the road.
- Nitro acceleration and visible exhaust; pad collection, lap changes and rank.
- Pause freezes elapsed time and car positions. Pausing during countdown also
  freezes the countdown. Focus loss pauses the real native window.
- Restart resets elapsed time, position, collisions, drift rewards and fuel.
- Keyboard menu navigation, mouse circuit/start selection, paint changes,
  difficulty selection, mute and reduced-motion settings.
- 960x640 and 1280x800 windows, fullscreen and return, rear-view camera.
- Wait for rivals to finish, then drive to a sixth-place finish in 124.69 s.
  Retry that result and return to the garage. The earlier 38.69 s record survived.
- Settings and best time persisted between game processes.

Screenshots were inspected for the garage, both circuits, drifting, turbo pads,
pause at 960x640, fullscreen, and finish/retry states. These checks found and
fixed terrain winding, fogged-out water, clipped small-window help text, missing
overlay blending, the boost acceleration cap, and camera lag at high speed.

Reproduce after launching with `--telemetry /tmp/turbo-tides-playtest.json`:

```sh
python3 tools/playtest.py explore  # start, drive, pause
python3 tools/playtest.py win      # a complete first-place race
python3 tools/playtest.py checks   # garage, mechanics, resize, Cinder win
python3 tools/playtest.py loss     # sixth place, retry, garage
```

The native helper needs X11/Xvfb, libX11, libXtst, xwininfo and ImageMagick.
The `checks` scenario starts in the garage; `loss` starts after a finished race.
Diagnostics and screenshots are written beneath ignored `build/playtest/`.

## Desktop package

The Linux app was built with a complete Eclipse Temurin 21.0.13+9 JDK after the
system's partial JDK proved to lack desktop modules. The downloaded JDK archive
was verified against its upstream SHA-256 file. `jpackage` produced a portable
app with its own runtime and the original logo.

- Installed into `~/.local/opt/turbo-tides` with a desktop-menu entry and icon.
- `desktop-file-validate` accepted the actual installed entry.
- Launched through `gtk-launch turbo-tides`; visually inspected the garage,
  countdown, driving and pause, then returned to the garage and quit with keys.
- Launched the installed binary from `/tmp`. Its process mapped `libjvm.so`
  from the app's bundled runtime. It loaded the prior record and completed a
  three-lap, first-place Cinder race in 38.59 s, collecting nine turbo pads.
- Verified the portable archive's SHA-256, extracted it into another directory,
  then launched **Play Turbo Tides** from `/tmp`. Its garage and saved record
  loaded successfully; it exited through the UI.

Screenshots: [garage](screenshots/garage.png), [race](screenshots/racing.png),
[finish](screenshots/victory.png).

## Limits

Only Linux desktop has been exercised. No Android APK, touch input, gamepad,
Windows or macOS playtest is claimed. Software rendering on the isolated
display ran around 33–40 FPS at 1280x800 with 4x antialiasing; fixed-step tests
cover 30 and 144 FPS. Audio resources loaded without engine errors and mute was
exercised; no subjective listening review is claimed. GitHub CI is configured,
but its execution requires publishing the repository.
