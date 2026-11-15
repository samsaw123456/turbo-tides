# Turbo Tides contributor notes

This is a separate Kotlin/libGDX 3D racing game. Keep the existing Emberwood
project untouched. Follow applicable parent contributor instructions.

- Keep track geometry authoritative in `Track.kt`; rendering, AI and minimap use it.
- Race rules stay independent of graphics and run with the fixed timestep in `Race.kt`.
- Run `./gradlew ktlintFormat`, then `./gradlew check fatJar` after Kotlin edits.
- Run Python lint and `python3 -m py_compile tools/*.py` after tooling edits.
- Installer changes also require `python3 -m unittest discover -s tools -p 'test_*.py'`,
  shell lint, an isolated installation and actual desktop activation. Keep the
  checkout, standalone and bundled installers on the shared implementation in
  `tools/install_linux.py`; preserve saves and reject updates to a running app.
- Run the native game and verify changed interactions. The telemetry mode and
  `tools/playtest.py` drive real keyboard events on X11/XWayland/Xvfb; telemetry
  must not alter race rules or user records.
- Check directional controls against the visible result: a positive lane value
  is not evidence of screen-right movement. Exercise both key bindings and
  inspect road-relative motion, car yaw, camera orientation and recovery.
- Keep verification claims tied to recorded assertions and inspected frames.
  A complete automated race does not prove that each individual control works.
- Follow `docs/CONTROLS.md` and `docs/AUDIO-AUDIT.md` for native proof. Keep each
  run's JAR immutable, acknowledge injected input, and tie evidence to its SHA-256.
  Native library upgrades require fullscreen restoration and focus/release checks.
- Revisit the game checklist in `docs/DESIGN.md` and record evidence in `docs/PLAYTEST.md`.
- Preserve the orange/cream/teal visual identity, original editable SVG icon,
  legible UI, keyboard focus, alternative controls, mute and reduced motion.
- Keep `turbo-tides`, the Zed task, app icon, credits and README accurate.
- Repackage with `python3 tools/package_linux.py --install` after verified changes
  when updating the installed app. Never replace unmarked app directories.
- No accounts, telemetry uploads, ads, paid services or dependencies without a
  concrete project need. The game must work offline.
