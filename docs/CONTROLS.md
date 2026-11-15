# Control coverage for 1.3

Inventory checked against `Game.keys`, `Game.controls`, `Hud.menuInput`,
the garage help and README. The game supports a desktop keyboard and primary
mouse button. Controller and touch input are not implemented or advertised.

The final-build audit uses actual native input handlers, screenshots, read-only
diagnostics and direct capture of the game's PipeWire output. It never writes
race state. All 49 rows below passed their assertions and visual/audio evidence
review on the final 1.3.0 JAR; no inventory row remains failed or unverified.
The tested JAR SHA-256 is recorded in [verification.json](evidence/verification.json).
Screenshots and JSON live in `build/difficulty-playtest`; scripts reproduce them.

The complete 1.3 audit uses XTest on an isolated Xvfb display, with
XQueryKeymap acknowledgement of every physical press/release before the next
edge. This exercises the real GLFW/libGDX input handlers and rendered UI.
The initial migration rendered on hardware through XWayland, but desktop key
injection later failed acknowledgement; the full audit therefore used software
rendering. The tools also support native X11 mouse events as an XWayland fallback.
Set `TURBO_TEST_NATIVE_POINTER=1` for that fallback and `TURBO_TEST_TELEMETRY`
to the app's diagnostic JSON path when using a non-default path. `control_audit.py` also requires Pillow, xprop and PipeWire’s
`pw-dump`/`pw-record`/`pw-link`.
Its `--holds-only` pass verifies that held toggles, pause, restart, Enter and
menu navigation do not repeatedly activate through native key repeat.
`--presentation-only` checks coasting, moving opposed inputs, isolated drift
rewards and camera release. `--states-only` captures each disabled binding
separately and verifies focus recovery and restart. `--focus-only` also releases all driving keys off-window, then accelerates and
steers again without Space/Shift to detect latent modifier latches.
Audio ports are selected
using the actual game window’s process ID, including the packaged app.

| Physical binding | Context and expected cause/effect | Observed result | Status | Evidence |
| --- | --- | --- | --- | --- |
| W | Racing: speed and travel rise; release coasts; disabled before GO/after finish | Car accelerated from rest; visible speed fell 146→75 km/h after release; countdown/result gating passed. | Passed | `control-w-*` |
| Up | Racing: accelerate; menus: focus moves up; countdown gates driving | Accelerated from rest and coasted 159→89 km/h; menu focus moved upward. | Passed | `control-Up-*`, menu/result focus frames |
| S | Racing: brake to zero without reversing; wins over W | Speed reached 0 km/h despite W held; car stayed stopped without reversing. | Passed | `control-s-stopped`, opposing-inputs |
| Down | Racing: brake; menus: focus moves down; countdown gates driving | Speed reached 0 km/h; menu focus advanced downward. | Passed | `control-Down-stopped`, menu/result focus frames |
| A | Racing: move screen-left; release removes steering; stopped input cannot move car | Car moved to the visible left edge; neutral steering recovered; stopped car stayed still. | Passed | steering-a, city-mechanics JSON |
| Left | Racing: move screen-left; garage: previous track/setting; pause/results: previous action | Same visible left motion; previous route/setting/action received focus. | Passed | steering-left, city-menu, focus frames |
| D | Racing: move screen-right; release removes steering | Car moved right across the road center; release removed steering. | Passed | steering-d, city-mechanics JSON |
| Right | Racing: move screen-right; garage: next track/setting; pause/results: next action | Same visible right motion; next route/setting/action received focus. | Passed | steering-right, city-menu, focus frames |
| W + S | Racing: brake takes priority over throttle | Car stopped while both were held. | Passed | opposing-inputs, control-s-stopped |
| Up + Down + Left Shift | Racing: brake stops the car and prevents boost | Car stopped at 0 km/h with no boost exhaust or nitro consumption. | Passed | control-up-down-brake-priority |
| A + D | Racing: opposing steering cancels | Car continued its line without a commanded turn; release remained neutral. | Passed | control-opposed-a-d-* |
| Left + Right | Racing: opposing steering cancels | Car continued its line without a commanded turn; release remained neutral. | Passed | control-opposed-Left-Right-* |
| A + Right | Racing: mixed alternate bindings cancel | Car continued its line without a commanded turn; release remained neutral. | Passed | control-opposed-a-Right-* |
| Left + D | Racing: mixed alternate bindings cancel | Car continued its line without a commanded turn; release remained neutral. | Passed | control-opposed-Left-d-* |
| Space alone | Racing: no drift without moving steering | No drift yaw, drift feedback or bonus without moving steering. | Passed | drift preconditions |
| Space + A | Moving left drift, visible yaw/feedback; release banks one bonus | Visible left drift; releasing Space while A stayed held showed one bonus and increased nitro. | Passed | control-drift-a-* |
| Space + Left | Moving left drift using alternate key; release banks bonus | Visible left drift; Space release alone showed one bonus and increased nitro. | Passed | control-drift-Left-* |
| Space + D | Moving right drift; release banks bonus | Visible right drift; Space release alone showed one bonus and increased nitro. | Passed | control-drift-d-* |
| Space + Right | Moving right drift using alternate key; release banks bonus | Visible right drift; Space release alone showed one bonus and increased nitro. | Passed | control-drift-Right-* |
| Left Shift | With throttle: faster travel, exhaust, nitro use; release ends boost | Exhaust flames and speed rose to 313 km/h; nitro fell; release removed flames and slowed the car. | Passed | control-Shift_L-* |
| Right Shift | Same boost action through separate binding | Exhaust flames and increased speed appeared; release removed flames and ended nitro use. | Passed | control-Shift_R-* |
| C | Hold to look behind; release or pause restores forward chase view | Camera showed the car front and road behind; release and pause both restored the forward view. | Passed | control-rear-*-released |
| C + A | Rear view retains car-relative steering: apparent screen direction mirrors, as documented and shown in HUD | Car moved toward the rear view’s right side; release restored forward view at the road’s left edge. | Passed | control-rear-a-before/held/released |
| C + Left | Rear view retains car-relative steering: apparent screen direction mirrors, as documented and shown in HUD | Same mirrored left-steer effect and forward-view recovery. | Passed | control-rear-Left-before/held/released |
| C + D | Rear view retains car-relative steering: apparent screen direction mirrors, as documented and shown in HUD | Car moved toward the rear view’s left side; release restored forward view on the right. | Passed | control-rear-d-before/held/released |
| C + Right | Rear view retains car-relative steering: apparent screen direction mirrors, as documented and shown in HUD | Same mirrored right-steer effect and forward-view recovery. | Passed | control-rear-Right-before/held/released |
| P | Garage: toggle actual circuit/grid views; ignored during race/countdown/pause/finish | All six scenes switched between whole-circuit and car/grid views; other states stayed unchanged. | Passed | preview/grid frames, disabled-state checks |
| M | Menu/race: captured sound → silence → sound; mute survives pause/resume | Game-only PCM became all-zero when muted and audible-level PCM returned when unmuted; pause/resume preserved mute. | Passed | audio-*.wav and RMS/peak measurements |
| N | Garage orbit stops; racing nitro zoom reduces while boost remains active; toggle restores behavior | Preview pixels stopped changing; reduced-motion boost retained flames/speed without zoom; toggling back restored motion. | Passed | identical/different scene crops, FOV and boost frames |
| F11 | Window expands to fullscreen and returns to original dimensions | Native window dimensions expanded and returned; held key caused only one transition. | Passed | fullscreen/window-restored frames and sizes |
| Esc during countdown | Pause/resume freezes/restores countdown without moving cars | Countdown and cars froze under pause; countdown continued after resume. | Passed | city-mechanics and countdown-disabled |
| Esc during racing/paused | Pause freezes state; resume continues the same race | Pause overlay appeared, race state froze, and the same race resumed. | Passed | city-mechanics, pause/recovery frames |
| Esc after finish | Return to garage | Result screen returned to the circuit selector. | Passed | final circuit result actions |
| Esc in garage | Exit actual application | Actual native window closed and application exited normally. | Passed | process/window disappearance |
| R during countdown/racing/paused/finished | Fresh countdown; reset time, distance, fuel, contacts and rewards | New countdown showed lap 1, time/distance/rewards 0 and nitro 65; held R did not repeatedly reset. | Passed | city-mechanics, result action checks |
| R in garage | No action | Selector remained open with no race started. | Passed | garage-disabled |
| Enter in garage | Start focused circuit; focused setting instead activates its action | Focused San Francisco launched after hovering from Sunset; focused settings activated correctly. | Passed | city-menu and selected-track launch |
| Enter in pause | Activate focused Resume/Restart/Garage | Focused Resume, Restart and Garage each reached their intended screen/state. | Passed | pause focus pairs and activation |
| Enter in results | Activate focused Race again or Garage | Race again started a fresh countdown; Garage returned to the selector. | Passed | final circuit result actions |
| Enter during countdown/racing | No menu action or unintended transition | Countdown/race continued without menu activation. | Passed | control-state-countdown-Return, control-state-racing-Return |
| Tab during countdown/racing | No focus action or unintended transition | Countdown/race continued without changing screens or driving. | Passed | control-state-countdown-Tab, control-state-racing-Tab |
| Tab | Move menu focus forward, including wraparound | Visible focus advanced and wrapped through menu actions. | Passed | garage/pause/result focus sequences |
| Left Shift + Tab | Move menu focus backward | Visible focus moved backward in garage, pause and results. | Passed | pause/result focus sequences |
| Right Shift + Tab | Same reverse-focus action through separate Shift binding | The alternate Shift produced the same backward focus movement. | Passed | pause/result focus sequences |
| Mouse movement | Menus: move focus without activation; arrows and Enter follow the focused item | Hover underlined the target without activating it; arrows and Enter then used that focused route. | Passed | control-hover-route-before-enter/after-enter, control-hover-route-Left/Right |
| Primary mouse click | Select each circuit, all paints, all four difficulty levels, preview; start/resume/retry/garage buttons | Each named route changed the scene/map; all five paints changed the car; all four difficulty levels, preview and race/pause/result buttons worked. | Passed | city-menu, all paint frames, result/pause actions |
| Middle mouse click | No menu activation | Menu action stayed unactivated. | Passed | nonprimary click assertions |
| Right mouse click | No menu activation | Menu action stayed unactivated. | Passed | nonprimary click assertions |
| Release while unfocused | Entire driving chord clears; automatic pause; resume has no stuck throttle, steering, drift, boost or rear view | All 12 driving keys cleared; normal acceleration/steering after resume showed no latent brake, drift, boost or rear view. | Passed | control-focus-all-recovered, control-focus-normal-driving; focus-release-audit.json |

Driving-only bindings are also held separately in the garage, countdown, pause
and results states, with screenshots named `control-state-<state>-<binding>`.
They do not move the car or activate a menu. Arrows retain their documented
menu-navigation function; Enter and Tab are separately checked while racing
and counting down. There is no separate interactive loading screen.

Rear-view steering is intentionally relative to the forward-facing car, as in
a rear-view mirror. The temporary view explains this on screen. Normal chase
view always maps A/Left to screen-left and D/Right to screen-right. Positive lane
is also checked independently using a real perspective camera at 24 positions
around every track. Steering through every bend at boost speed is regression
tested separately from camera projection.
