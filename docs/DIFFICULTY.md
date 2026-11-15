# Four rival levels

Choose **Easy**, **Medium**, **Hard**, or **Super Hard** in the garage's Rivals
setting. Click or press Enter to advance; Left and Right move backward and
forward with wraparound. The chosen level appears in the garage, race HUD,
pause menu and result screen, and remains selected when restarting or reopening
the game.

| Level | Driving challenge |
| --- | --- |
| Easy | Forgiving rival pace; careful driving can win without nitro. |
| Medium | Rivals can beat an unboosted run; clean lines and turbo pads are enough to compete. |
| Hard | Faster starts and confident corners; combine pads, drifting and nitro. |
| Super Hard | The fastest field; repeated clean drifts and timely boosts are needed to win. |

Only the rivals change. Player acceleration, grip, steering, braking, nitro,
collision rules and race length stay the same. Rivals do not get faster when
behind or slower when ahead. Their speed stays within the player's boosted
87 m/s limit. They still make solid contact and must overtake other cars.

The first two saved indices and record identities remain compatible: Cruise
becomes Easy and Race becomes Medium. Hard and Super Hard have their own best
times. San Francisco's older route records remain untouched.

## Balance checks

The fixed-step test lets each rival field complete the same three-lap race while
the player remains parked. These are measured fastest-rival times in seconds,
not target constants or an estimate from configured speed:

| Circuit | Easy | Medium | Hard | Super Hard |
| --- | ---: | ---: | ---: | ---: |
| Sunset Run | 56.91 | 47.44 | 41.10 | 37.77 |
| Cinder Ring | 54.10 | 45.08 | 39.16 | 35.89 |
| San Francisco | 73.54 | 61.39 | 53.59 | 49.13 |
| Silicon Valley | 62.31 | 51.97 | 45.32 | 41.45 |
| New York City | 62.52 | 52.15 | 45.48 | 41.59 |
| Chicago | 62.45 | 52.06 | 45.41 | 41.54 |

Every finishing position in the AI field improves by at least 5% at each step
on every circuit. Digital driving tests, refreshed at 20 Hz, win Easy without
boost and Medium with pads and boost. That same pad-only strategy loses on Hard
and Super Hard; adding controlled drifts wins both on all six tracks. Tests
never teleport cars, award fuel, skip laps or alter the race state to win.
These deterministic drivers check the tuning; they do not predict every player's
experience. Native-input results and inspected frames are recorded in
[the playtest report](PLAYTEST.md).

Run the focused regressions with:

```sh
./gradlew test --tests turbotides.DifficultyTest
```

With the native game running in diagnostic mode, use:

```sh
python3 tools/difficulty_playtest.py menu
python3 tools/difficulty_playtest.py races
python3 tools/difficulty_playtest.py skill
```

The menu pass covers both directions, Enter, clicks, wraparound and a held key
at 1280×800 and 960×640. The race pass uses the same ordinary driving strategy
at every level, then checks retry and pause preserve the setting. The skill pass
uses only real W/A/D/Space/Shift events to attempt a Super Hard win.
