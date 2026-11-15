# Native first-place verification

All **24 combinations** — six circuits × four rival levels — have a verified
first-place finish in the installed Linux app. Each run began at the starting
grid, completed all three laps, and showed **Victory / 1 of 6** on screen.
The selected menu, all three lap frames and the result were captured and inspected
for every combination. The complete recorded attempts are retained below.

| Circuit | Easy | Medium | Hard | Super Hard |
| --- | ---: | ---: | ---: | ---: |
| Sunset Run | 41.53 s | 40.74 s | 35.89 s | 35.90 s |
| Cinder Ring | 39.26 s | 38.75 s | 34.27 s | 34.92 s |
| San Francisco | 55.02 s | 54.82 s | 46.38 s | 47.28 s |
| Silicon Valley | 45.86 s | 45.66 s | 39.21 s | 39.39 s |
| New York City | 46.71 s | 45.46 s | 39.36 s | 39.62 s |
| Chicago | 45.96 s | 45.38 s | 39.27 s | 40.00 s |

Times are seconds, truncated to hundredths as in the HUD. Easy and Medium use
pads and boost; Hard and Super Hard add controlled drifts, so those player times
can be faster. These demonstrate achievable wins with the normal game mechanics;
they do not predict an individual player's time.

Result screenshots: [Sunset Run](screenshots/wins-sunset.png), [Cinder Ring](screenshots/wins-cinder.png), [San Francisco](screenshots/wins-san_francisco.png), [Silicon Valley](screenshots/wins-silicon_valley.png), [New York City](screenshots/wins-new_york.png), [Chicago](screenshots/wins-chicago.png).

## Interrupted run

The first driver command ended with SIGTERM (exit 143) during San Francisco
Super Hard. The game stayed running with the last held inputs; its paused
recovery frame shows sixth place. That unfinished attempt is retained in the
evidence and is not counted as a win. A separate background driver restarted
that combination from the grid, then completed the remaining circuits.

## Method and identity

The installed app uses its bundled runtime and the same game JAR as release 1.3.0:
`cfd8fd13e4f2625b053914a289c7ed5d397594f8ce8b463fca038d8d0cc3d882`.
The game rules and difficulty tuning were unchanged for this verification.
Real XTest events drive the native keyboard/mouse handlers. Read-only diagnostics
provide feedback for steering and test assertions; all progress, fuel, collisions,
drift rewards, rival movement and lap completion come from normal gameplay.

A separate Java user.home stores test records; all 24 saved times were checked
against the race results, and the normal player preferences remained unchanged.
The 1280×800 game window renders
on an isolated X11 display using software rendering. The run proves native-app
wins; it is automated driving rather than a human playtest or hardware benchmark.
The existing [49-row control audit](CONTROLS.md) covers individual bindings on
the identical runnable JAR.

## Reproduce

Launch the installed app with an isolated Java user.home and
`--telemetry /absolute/path/state.json`. Point `TURBO_TEST_TELEMETRY` there and
set `TURBO_TEST_OUTPUT` to a new evidence directory on each run, then use:

```sh
python3 tools/difficulty_playtest.py matrix
# A focused run, also in a new output directory:
python3 tools/difficulty_playtest.py matrix --circuit CHICAGO --difficulty SUPER_HARD
```

The matrix preserves unsuccessful finishes and continues other combinations;
its exit status fails if any selected combination was not won. Reusing an output
directory containing matrix results is rejected to preserve earlier evidence.
It records the starting state, complete finish state, strategy and wall time.

[Machine-readable evidence](evidence/native-win-matrix.json) includes all attempts
and SHA-256 hashes for every inspected capture. Raw captures remain in
`build/native-win-matrix/` and are also attached to the 1.3.0 GitHub release.
