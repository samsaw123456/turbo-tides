# Native audio cue audit

`tools/audio_audit.py` drives the real game with X11 keyboard and mouse input
and records only that game process's stereo PipeWire output ports. It does not
capture a microphone, the system mix, or another game's output. It verifies
output PCM; it does not establish subjective speaker/headphone sound quality.

The audit covers one GO cue at countdown completion, no simultaneous bonus
cue, pause/resume without another GO, and three consecutive turbo-pad bonus
cues. Read-only telemetry identifies the corresponding race events; WAV
correlation proves that the original sounds reached the output. Rendered frames
show the race and each pad event. The script records the running JAR's SHA-256
and checks its GO/bonus WAVs against the reference assets.

## Requirements and execution

Use Linux with PipeWire, `pw-dump`, `pw-record`, `pw-link`, `xprop`, `xwininfo`,
X11/XTest libraries, Python 3, NumPy, SciPy and Pillow. These are audit tools,
not dependencies needed to play the packaged game. If needed, install the
Python tools in an isolated environment with
`python3 -m venv build/audio-audit-env`, then
`build/audio-audit-env/bin/pip install numpy scipy pillow`.

Launch a verified, unchanged JAR with `java -jar`, on a dedicated display with
fresh preferences. Do not share a display with another active input audit.
For example, after starting Xvfb on an unused display such as `:104`:

```sh
audit_dir="$PWD/build/audio-review-native"
mkdir -p "$audit_dir/home"
DISPLAY=:104 java --enable-native-access=ALL-UNNAMED \
  -Duser.home="$audit_dir/home" \
  -jar "$PWD/build/playtest/final-audit.jar" \
  --telemetry "$audit_dir/state.json"
```

Run the audit in another terminal while the game is in its garage, using the
same display and diagnostic file:

```sh
DISPLAY=:104 \
TURBO_TEST_TELEMETRY="$PWD/build/audio-review-native/state.json" \
TURBO_TEST_OUTPUT="$PWD/build/audio-review-native" \
python3 tools/audio_audit.py
```

The audit leaves its own game paused. Return that window to the garage and
quit, then stop only the Xvfb process created for this audit. Keep other games,
displays and user preferences untouched. Inspect `audio-*.png`,
`audio-cue-audit.json` and the three `cue-*.wav` recordings in the output folder.
All input is physical X11 input; the script does not alter race state.

## Detector and evidence limits

The detector resamples reference WAVs to 48 kHz, removes low-frequency engine
and bass output, then computes normalized correlation over each complete cue.
An onset requires correlation at least 0.65. Windows below one 16-bit PCM unit
RMS are excluded: normalizing FFT round-off at digital silence can otherwise
produce invalid peaks. Peaks are separated by at least 80% of the cue length.

A separately labelled `detector-fixture-double-cue.wav` adds a reference bonus
at the measured GO onset. This generated counterexample checks that the same
detector would reject the previous duplicate-cue bug. It is not recorded game
output. The native recordings and event timestamps remain unchanged.

To repeat only the analysis of retained recordings:

```sh
TURBO_TEST_OUTPUT="$PWD/build/audio-review-native" \
python3 tools/audio_audit.py --analyze-existing
```

The broader control audit separately verifies mute/unmute and silence while
paused. This cue audit does not replace the complete game control inventory.
