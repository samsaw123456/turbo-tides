# Turbo Tides

A standalone Kotlin / libGDX 3D arcade racer made from the Phippy Gaming
Workshop prompt. The existing Emberwood project is untouched.

## Direction

Toy-like rally cars, coral cliffs, teal water, cream road markings, warm sunlight,
and angular palms. Modelled geometry, perspective projection, lighting, hills and
a following camera make this a real 3D scene. The logo combines a racing apex,
a lightning bolt, and two waves; its editable source is SVG. Barlow Condensed is
used for large racing numbers and headings, Lato for readable instructions.
Menus sit alongside the actual live circuit. No marketing landing screen.

## Loop

Pick one of two circuits, a paint colour, and a difficulty. Race five opponents
for three laps. Steer, brake into corners, drift to earn nitro, and use nitro on
the straights. Boost pads reward driving the racing line. Off-road slows the car;
barriers and cars cause recoverable bumps. Finish in any place, see your result,
then retry or choose another circuit. Best race times are stored per circuit and
difficulty. Workshop characters appear as the pit crew, with MIT attribution.

## Architecture

- `Track.kt`: closed, arc-length sampled 3D circuits and surface geometry.
- `Race.kt`: deterministic fixed-step racing rules, independent of rendering.
- `World.kt`: meshes, cars, scenery, camera and rendering resources.
- `Game.kt` / `Hud.kt`: state transitions, keyboard/mouse UI and persistence.
- `Audio.kt`: locally generated sounds, engine and mute controls.
- `Desktop.kt`: native window and optional diagnostic output.

The physics is intentionally arcade-style: cars follow the road longitudinally,
and steering controls lateral velocity with grip and corner forces. There is no
reverse gear, shortcut, falling off the island, or simulation of suspension.
The road path is the single source for physics, rendering, minimap and AI.

## Acceptance and playtest checklist

- [x] Core loop: garage, countdown, three laps, finish, retry, circuit change.
- [x] Physics: fixed 120 Hz, corner grip, grass drag, drift, boost, boundaries.
- [x] Interaction: keyboard/mouse menu, held steering, boost, pads and car contact.
- [x] Navigation/camera: continuous reachable loop, no seam jump, camera visibility.
- [x] State: pause/resume, focus loss, restart and countdown reset; records persist.
- [x] Feel/accessibility: readable at 960x640; mute, reduced motion, focus, remapped alternative keys.
- [x] Polish: title/icon, correct lap/rank displays, sound feedback, useful finish screen.
- [x] Robustness: resize/fullscreen, repeated races, low/high timestep tests, disposal.
- [x] Evidence: lint, tests, build, native input driving, win and loss/retry, screenshots.

Jumping, enemies, combat, inventory, online services and account login are not
part of the game. The app runs offline. Android packaging is out of scope for
this Linux desktop build.
