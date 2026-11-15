"""Create the game's original, deterministic synth sounds using the standard library."""

import math
import random
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src/main/resources/audio"
RATE = 22050
TAU = 2 * math.pi


def save(name, duration, sample):
    ROOT.mkdir(parents=True, exist_ok=True)
    data = bytearray()
    for index in range(round(duration * RATE)):
        value = max(-1, min(1, sample(index / RATE)))
        data.extend(struct.pack("<h", round(value * 24000)))
    with wave.open(str(ROOT / f"{name}.wav"), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(data)


def tone(t, frequency):
    return math.sin(TAU * frequency * t)


def melody(t, notes, step):
    phase = t % step
    frequency = notes[min(len(notes) - 1, int(t / step))]
    envelope = min(1, phase * 120) * math.exp(-phase * 5)
    return envelope * (tone(t, frequency) + 0.15 * tone(t, frequency * 2)) * 0.5


def music(t):
    beat = 0.5
    phase = t % beat
    bar = int(t / 2) % 4
    root = [130.813, 174.614, 164.814, 146.832][bar]
    notes = [1, 1.5, 2, 1.25, 1.5, 2.5, 2, 1.5]
    note = root * notes[int(t * 4) % len(notes)]
    pluck = tone(t, note * 2) * math.exp(-(t % 0.25) * 18) * 0.12
    bass = (tone(t, root / 2) + 0.15 * tone(t, root)) * math.exp(-phase * 4) * 0.3
    kick = (
        math.sin(TAU * (48 * phase + 1.8 * (1 - math.exp(-phase * 30))))
        * math.exp(-phase * 22)
        * 0.3
    )
    hat = (tone(t, 7321) + tone(t, 5893)) * math.exp(-(t % 0.25) * 100) * 0.035
    return pluck + bass + kick + hat


def main():
    save(
        "engine",
        1,
        lambda t: (tone(t, 60) + 0.45 * tone(t, 120) + 0.2 * tone(t, 180)) * 0.45,
    )
    save("music", 8, music)
    save("go", 0.42, lambda t: melody(t, [523.25, 659.25, 1046.5], 0.14))
    save("bonus", 0.3, lambda t: melody(t, [659.25, 880, 1318.51], 0.1))
    save(
        "finish",
        1.2,
        lambda t: melody(t, [523.25, 659.25, 783.99, 1046.5, 783.99, 1046.5], 0.2),
    )
    randomizer = random.Random(91)
    save("bump", 0.18, lambda t: randomizer.uniform(-1, 1) * math.exp(-t * 28) * 0.5)


if __name__ == "__main__":
    main()
