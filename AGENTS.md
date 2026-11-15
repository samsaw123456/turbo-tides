# Turbo Tides contributor notes

This is a separate Kotlin/libGDX 3D racing game. Keep the existing Emberwood
project untouched. Follow applicable parent contributor instructions.

- Keep track geometry authoritative in `Track.kt`; rendering, AI and minimap use it.
- Race rules stay independent of graphics and run with the fixed timestep in `Race.kt`.
- Run `./gradlew ktlintFormat`, then `./gradlew check fatJar` after Kotlin edits.
- Run Python lint and `python3 -m py_compile tools/*.py` after tooling edits.
- Run the native game and verify changed interactions. The telemetry mode and
  `tools/playtest.py` drive real keyboard events on X11/XWayland/Xvfb; telemetry
  must not alter race rules or user records.
- Check directional controls against the visible result: a positive lane value
  is not evidence of screen-right movement. Exercise both key bindings and
  inspect road-relative motion, car yaw, camera orientation and recovery.
- Keep verification claims tied to recorded assertions and inspected frames.
  A complete automated race does not prove that each individual control works.
- Revisit the game checklist in `docs/DESIGN.md` and record evidence in `docs/PLAYTEST.md`.
- Preserve the orange/cream/teal visual identity, original editable SVG icon,
  legible UI, keyboard focus, alternative controls, mute and reduced motion.
- Keep `turbo-tides`, the Zed task, app icon, credits and README accurate.
- Repackage with `python3 tools/package_linux.py --install` after verified changes
  when updating the installed app. Never replace unmarked app directories.
- No accounts, telemetry uploads, ads, paid services or dependencies without a
  concrete project need. The game must work offline.
