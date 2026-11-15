# City circuits working checklist

The 1.1 update adds four fictional circuits inspired by San Francisco, Silicon
Valley, New York City and Chicago. Their real 3D scenery is the menu background;
the selector should be useful before the player starts a race. Keep the existing
cream, tangerine and dark-teal interface and licensed Lato/Barlow typography.

Acceptance criteria verified for 1.1.0. See [control coverage](CONTROLS.md) and
[commands, observed results and limits](PLAYTEST.md).

- [x] Six distinct, continuous routes; existing saved circuit indices preserved.
- [x] A/Left moves screen-left, D/Right screen-right at speed and during boost.
- [x] Brake, coast, drift/release, nitro, pads, boundaries and contacts recover.
- [x] Pads cannot be farmed while stopped; each is available again next lap.
- [x] Race, countdown, pause, focus loss, retry and finish reset/freeze correctly.
- [x] All six circuits can be completed and won; a losing race can be retried.
- [x] Mouse and keyboard select every circuit; scene and map match immediately.
- [x] Previews show city-specific landmarks; tour/grid toggle and reduced motion work.
- [x] Menu and HUD are readable at 1280×800 and 960×640; maps fit every circuit.
- [x] Settings and per-circuit/per-pace best times persist across relaunch.
- [x] Kotlin/Python lint, regression tests, build and packaging pass.
- [x] Installed app launches; portable archive matches its checksum.

Physics remains an arcade racing-line model: forward travel follows the road,
with acceleration, lateral momentum and outward corner force. No reverse,
jumping, route branches, items or collisions with scenery beyond the barriers.
No controller support is claimed. Check the rendered sign of steering, rather
than inferring it from a lane number alone.
