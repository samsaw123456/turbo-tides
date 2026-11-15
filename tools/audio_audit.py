"""Match actual game-only PCM cues to bundled WAVs through native input.

Launch the immutable game with isolated telemetry/preferences on a dedicated
X display. Set TURBO_TEST_TELEMETRY and TURBO_TEST_OUTPUT before running.
Requires the existing native audit tools plus NumPy and SciPy; it never records
microphones or the system mix and never writes race state.
"""

import argparse
import hashlib
import json
import os
import time
import wave
import zipfile
from pathlib import Path

import numpy as np
from city_playtest import launch
from control_audit import record_game_audio
from playtest import OUTPUT, Driver
from scipy import signal

ROOT = Path(__file__).resolve().parents[1]
RATE = 48000


def mono(path):
    with wave.open(str(path)) as wav:
        assert wav.getsampwidth() == 2
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
        samples = samples.reshape(-1, wav.getnchannels()).mean(axis=1)
        source_rate = wav.getframerate()
    divisor = np.gcd(source_rate, RATE)
    return signal.resample_poly(samples, RATE // divisor, source_rate // divisor)


def matches(path, cue):
    """Normalized matched filter, retaining timing and distinct onset peaks."""
    sound = mono(path)
    template = mono(ROOT / "src/main/resources/audio" / f"{cue}.wav")
    # Remove engine/bass while retaining all three notes of either cue.
    highpass = signal.butter(4, 400, "highpass", fs=RATE, output="sos")
    sound = signal.sosfiltfilt(highpass, sound)
    template = signal.sosfiltfilt(highpass, template)
    correlation = signal.fftconvolve(sound, template[::-1], mode="valid")
    energy = signal.fftconvolve(sound * sound, np.ones(len(template)), mode="valid")
    denominator = np.sqrt(np.maximum(energy, 0) * np.dot(template, template))
    # FFT cancellation near digital silence is not an audible cue. Require
    # at least one 16-bit PCM unit of RMS before normalizing a window.
    score = np.divide(
        np.abs(correlation),
        denominator,
        out=np.zeros_like(correlation),
        where=energy > len(template),
    )
    peaks, _ = signal.find_peaks(score, height=0.65, distance=len(template) * 0.8)
    return {
        "maximumCorrelation": float(score.max()),
        "cueMatches": [
            {"seconds": float(index / RATE), "correlation": float(score[index])}
            for index in peaks
        ],
    }


def capture(driver, name, seconds, action):
    result = record_game_audio(
        driver,
        name,
        seconds=seconds,
        action=action,
        node_name=f"TurboTidesCueAudit{os.getpid()}",
    )
    result["go"] = matches(OUTPUT / f"{name}.wav", "go")
    result["bonus"] = matches(OUTPUT / f"{name}.wav", "bonus")
    print(name, json.dumps(result), flush=True)
    return result


def validate(evidence):
    assert len(evidence["countdown"]["go"]["cueMatches"]) == 1
    assert not evidence["countdown"]["bonus"]["cueMatches"]
    assert not evidence["resume"]["go"]["cueMatches"]
    assert not evidence["resume"]["bonus"]["cueMatches"]
    assert len(evidence["events"]) >= 3, evidence["events"]
    assert len(evidence["pads"]["bonus"]["cueMatches"]) >= 3

    # Check that the same detector rejects the original duplicate-cue defect.
    # This explicitly labelled fixture is generated, never native evidence.
    sound = mono(OUTPUT / "cue-countdown.wav")
    go = mono(ROOT / "src/main/resources/audio/go.wav")
    bonus = mono(ROOT / "src/main/resources/audio/bonus.wav")
    start = round(evidence["countdown"]["go"]["cueMatches"][0]["seconds"] * RATE)
    gain = np.dot(sound[start : start + len(go)], go) / np.dot(go, go)
    sound[start : start + len(bonus)] += gain * bonus
    path = OUTPUT / "detector-fixture-double-cue.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(np.rint(sound).clip(-32768, 32767).astype("<i2").tobytes())
    evidence["injectedDuplicateCueDetectorCheck"] = matches(path, "bonus")
    assert evidence["injectedDuplicateCueDetectorCheck"]["cueMatches"]
    (OUTPUT / "audio-cue-audit.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("Native output matched one GO, no resume GO, and three pad cues.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analyze-existing", action="store_true")
    args = parser.parse_args()
    if args.analyze_existing:
        evidence = json.loads((OUTPUT / "audio-cue-audit.json").read_text())
        for key, name in (
            ("countdown", "cue-countdown"),
            ("resume", "cue-resume"),
            ("pads", "cue-repeated-pads"),
        ):
            for cue in ("go", "bonus"):
                evidence[key][cue] = matches(OUTPUT / f"{name}.wav", cue)
            print(name, json.dumps(evidence[key]), flush=True)
        validate(evidence)
        return
    driver = Driver()
    evidence = {"display": os.environ.get("DISPLAY"), "events": []}
    try:
        assert driver.state()["phase"] == "GARAGE"
        if driver.state()["muted"]:
            driver.tap("m")

        def countdown():
            launch(driver)
            driver.wait_phase("RACING", timeout=30)
            time.sleep(0.75)
            driver.screenshot("audio-go-racing")
            driver.tap("Escape")
            assert driver.state()["phase"] == "PAUSED"

        evidence["countdown"] = capture(driver, "cue-countdown", 10, countdown)
        source_pid = evidence["countdown"]["sourceProcess"]
        command = Path(f"/proc/{source_pid}/cmdline").read_bytes().decode().split("\0")
        jar = Path(command[command.index("-jar") + 1])
        evidence["jarSha256"] = hashlib.sha256(jar.read_bytes()).hexdigest()
        with zipfile.ZipFile(jar) as archive:
            for cue in ("go", "bonus"):
                asset = f"audio/{cue}.wav"
                assert (
                    archive.read(asset)
                    == (ROOT / "src/main/resources" / asset).read_bytes()
                )
        evidence["referenceWavsMatchRunningJar"] = True

        def resume():
            driver.tap("Escape")
            driver.wait_phase("RACING")
            time.sleep(0.8)
            driver.screenshot("audio-resumed")
            driver.tap("Escape")
            assert driver.state()["phase"] == "PAUSED"

        evidence["resume"] = capture(driver, "cue-resume", 5, resume)

        def pads():
            start = time.monotonic()
            launch(driver)
            driver.key("w", True)
            driver.wait_phase("RACING", timeout=30)
            seen = 0
            while time.monotonic() - start < 23:
                state = driver.state()
                if state["pads"] > seen:
                    seen = state["pads"]
                    evidence["events"].append(
                        {"wallSeconds": time.monotonic() - start, "state": state}
                    )
                    driver.screenshot(f"audio-pad-{seen}")
                    if seen >= 3:
                        time.sleep(0.4)
                        break
                target = 0
                for index in range(3):
                    pad = state["length"] * (0.15 + index * 0.25)
                    ahead = (pad - state["distance"]) % state["length"]
                    if ahead < 80 or ahead > state["length"] - 4:
                        target = -3.6 if index % 2 == 0 else 3.6
                driver.steer_toward(state, target)
                time.sleep(0.03)
            driver.release()
            driver.tap("Escape")
            assert driver.state()["phase"] == "PAUSED"

        evidence["pads"] = capture(driver, "cue-repeated-pads", 26, pads)
        (OUTPUT / "audio-cue-audit.json").write_text(
            json.dumps(evidence, indent=2) + "\n"
        )
        validate(evidence)
    finally:
        driver.release()


if __name__ == "__main__":
    main()
