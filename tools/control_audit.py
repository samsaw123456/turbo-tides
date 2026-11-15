"""Exhaustive keyboard audit using the real window, frames and game-only PCM.

Run after city_playtest.py menu and before city_playtest.py circuits, which
also exercises every result-menu action. No microphone or system mix is captured.
"""

import argparse
import array
import json
import math
import re
import subprocess
import time
import wave

from city_playtest import DIFFICULTIES, drive_for, garage, launch, mechanics, select
from playtest import OUTPUT, Driver


def record_game_audio(
    driver,
    name,
    *,
    seconds=1,
    action=None,
    node_name="TurboTidesAuditCapture",
):
    """Connect only the game's two output ports to an isolated recording node."""
    window_pid = subprocess.check_output(
        ["xprop", "-id", hex(driver.window), "_NET_WM_PID"], text=True
    )
    pid = int(window_pid.rsplit("=", 1)[1].strip())
    objects = json.loads(subprocess.check_output(["pw-dump"], text=True))
    clients = {
        item["id"]
        for item in objects
        if str(item.get("info", {}).get("props", {}).get("application.process.id"))
        == str(pid)
    }
    nodes = {
        item["id"]
        for item in objects
        if item.get("info", {}).get("props", {}).get("client.id") in clients
        and item.get("info", {}).get("props", {}).get("media.class")
        == "Stream/Output/Audio"
    }
    outputs = {}
    for side in ("FL", "FR"):
        ports = [
            item["id"]
            for item in objects
            if item.get("info", {}).get("props", {}).get("node.id") in nodes
            and item.get("info", {}).get("props", {}).get("audio.channel") == side
            and item.get("info", {}).get("props", {}).get("port.direction") == "out"
        ]
        if len(ports) != 1:
            raise RuntimeError(f"Expected one {side} output port for game PID {pid}")
        outputs[side] = ports[0]
    path = OUTPUT / f"{name}.wav"
    frames = round(48000 * seconds)
    process = subprocess.Popen(
        [
            "pw-record",
            "--target",
            "0",
            "--properties",
            f'{{ node.name = "{node_name}" node.autoconnect = false }}',
            "--rate",
            "48000",
            "--channels",
            "2",
            "--format",
            "s16",
            "--sample-count",
            str(frames),
            str(path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        for _ in range(60):
            ports = subprocess.check_output(["pw-link", "-i"], text=True)
            if f"{node_name}:input_FL" in ports:
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("Audio audit capture ports did not appear")
        for side in ("FL", "FR"):
            subprocess.run(
                [
                    "pw-link",
                    str(outputs[side]),
                    f"{node_name}:input_{side}",
                ],
                check=True,
            )
        if action is not None:
            action()
        _, error = process.communicate(timeout=seconds + 10)
        # This pw-record build returns 1 on reaching --sample-count. Validate
        # the actual PCM payload, not that unusual exit status alone.
        with wave.open(str(path)) as wav:
            assert wav.getnframes() == frames, error.decode()
            samples = array.array("h", wav.readframes(wav.getnframes()))
        return {
            "rms": math.sqrt(sum(sample * sample for sample in samples) / len(samples)),
            "peak": max(map(abs, samples)),
            "frames": len(samples) // 2,
            "captureExit": process.returncode,
            "sourceProcess": pid,
        }
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


def snap(driver, name, *, settle=True):
    if settle:
        driver.settle()
    before = driver.state()
    driver.screenshot(f"control-{name}")
    after = driver.state()
    (OUTPUT / f"control-{name}.json").write_text(
        json.dumps({"beforeCapture": before, "afterCapture": after}, indent=2) + "\n"
    )
    return after


def start_driving(driver, seconds=1.5, key="w"):
    launch(driver)
    driver.key(key, True)
    driver.wait_phase("RACING")
    drive_for(driver, seconds)


def focus_release(driver):
    """Release every driving binding off-window, then prove modifiers stayed up."""
    start_driving(driver, 1.5)
    for key in (
        "w",
        "Up",
        "s",
        "Down",
        "a",
        "Left",
        "d",
        "Right",
        "space",
        "Shift_L",
        "Shift_R",
        "c",
    ):
        driver.key(key, True)
    driver.settle()
    before = snap(driver, "focus-chord-held")
    driver.x.XSetInputFocus(
        driver.display, driver.x.XDefaultRootWindow(driver.display), 2, 0
    )
    driver.x.XFlush(driver.display)
    driver.wait_phase("PAUSED")
    driver.release()
    driver.focus()
    driver.tap("Escape")
    driver.wait_phase("RACING")
    recovered = snap(driver, "focus-all-recovered")
    assert not recovered["inputThrottle"] and not recovered["inputBrake"]
    assert recovered["inputSteer"] == 0 and recovered["screenRight"] > 0
    assert not recovered["boosting"] and not recovered["drifting"]
    driver.key("w", True)
    drive_for(driver, 1.5)
    driver.key("d", True)
    drive_for(driver, 0.3)
    normal = snap(driver, "focus-normal-driving")
    assert normal["inputThrottle"] and not normal["inputBrake"]
    assert normal["inputSteer"] == 1 and normal["speed"] > 18
    assert not normal["boosting"] and not normal["drifting"]
    assert normal["screenRight"] > 0
    driver.release()
    released = snap(driver, "focus-normal-released")
    assert not released["inputThrottle"] and released["inputSteer"] == 0
    result = [before, recovered, normal, released]
    (OUTPUT / "focus-release-audit.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    garage(driver)
    print(
        "Every driving key cleared on focus loss; no latent brake/drift/boost",
        flush=True,
    )
    return result


def drift_release(driver, key, direction):
    """Prove release banks a drift, before an edge can end it automatically."""
    launch(driver)
    driver.wait_phase("RACING")
    # Let the pack leave, spend some nitro, and pass the first pad. This gives
    # the release feedback room to appear without a contact/pad replacing it.
    drive_for(driver, 3)
    driver.key("w", True)
    driver.key("Shift_L", True)
    drive_for(driver, 1)
    driver.key("Shift_L", False)
    driver.center_for(2.4)
    target = -direction * 6
    deadline = time.monotonic() + 20
    while abs(driver.state()["lane"] - target) > 0.8:
        assert time.monotonic() < deadline, driver.state()
        driver.steer_toward(driver.state(), target)
        time.sleep(0.03)
    driver.key("a", False)
    driver.key("d", False)
    driver.key("space", True)
    drive_for(driver, 0.15)
    assert not driver.state()["drifting"]
    before = snap(driver, f"drift-{key}-before")
    driver.key(key, True)
    drive_for(driver, 0.5)
    # Capture promptly: waiting for several extra frames while steering would
    # test leaving the road instead of releasing the drift command.
    driver.screenshot(f"control-drift-{key}")
    during = driver.state()
    assert during["drifting"] and during["driftBonuses"] == 0, during
    assert abs(during["lane"]) < 8, during
    driver.key("space", False)
    # Observe the release on its first diagnostic frame. Waiting for three more
    # frames with steering held can reach the wall on a slow renderer, obscuring
    # the isolated Space-release effect with an unrelated collision.
    deadline = time.monotonic() + 5
    while driver.state()["driftBonuses"] == during["driftBonuses"]:
        assert time.monotonic() < deadline, driver.state()
        time.sleep(0.01)
    after = snap(driver, f"drift-{key}-released", settle=False)
    assert not after["drifting"] and after["driftBonuses"] == 1, after
    # Keep steering held: Space release itself must cause the bonus.
    assert after["inputSteer"] == direction
    assert after["nitro"] > during["nitro"] + 10, (during, after)
    assert after["pads"] == during["pads"] == before["pads"], (before, during, after)
    assert after["bumps"] == during["bumps"] == before["bumps"], (before, during, after)
    assert (during["lane"] - before["lane"]) * direction > 0.8
    driver.key(key, False)
    settled = snap(driver, f"drift-{key}-steering-released")
    assert settled["inputSteer"] == 0 and not settled["drifting"]
    driver.release()
    return [before, during, after]


def opposing_steer(driver, left, right):
    start_driving(driver, 1)
    before = snap(driver, f"opposed-{left}-{right}-before")
    driver.key(left, True)
    driver.key(right, True)
    drive_for(driver, 0.3)
    held = snap(driver, f"opposed-{left}-{right}-held")
    assert held["inputSteer"] == 0
    # At speed, the car should continue along its line with only the ordinary
    # corner drift, rather than steering hard to either side.
    assert abs(held["lane"] - before["lane"]) < 1.5, (before, held)
    driver.key(left, False)
    driver.key(right, False)
    after = snap(driver, f"opposed-{left}-{right}-released")
    assert after["inputSteer"] == 0
    driver.release()
    return [before, held, after]


def presentation(driver):
    """Recapture changes after presentation has caught up on slow X11 displays."""
    garage(driver)
    driver.resize(1280, 800)
    root_info = subprocess.check_output(["xwininfo", "-root"], text=True)
    fullscreen_size = [
        int(re.search(rf"{field}:\s+(\d+)", root_info)[1])
        for field in ("Width", "Height")
    ]
    driver.key("F11", True)
    driver.settle()
    for _ in range(3):
        info = subprocess.check_output(
            ["xwininfo", "-id", hex(driver.window)], text=True
        )
        actual_size = [
            int(re.search(rf"{field}:\s+(\d+)", info)[1])
            for field in ("Width", "Height")
        ]
        assert actual_size == fullscreen_size
        time.sleep(0.3)
    snap(driver, "held-fullscreen")
    driver.key("F11", False)
    driver.tap("F11")
    snap(driver, "held-fullscreen-restored")
    select(driver, 2)
    evidence = {}
    for key in ("w", "Up"):
        launch(driver)
        driver.wait_phase("RACING")
        before = snap(driver, f"{key}-before")
        driver.key(key, True)
        drive_for(driver, 1.4)
        held = snap(driver, f"{key}-held")
        driver.key(key, False)
        driver.settle()
        released = driver.state()
        drive_for(driver, 1.5)
        after = snap(driver, f"{key}-released")
        assert held["speed"] > before["speed"] and after["speed"] < released["speed"]
        evidence[key] = [before, held, released, after]
        driver.release()
    start_driving(driver, 1.2, "Up")
    driver.key("Down", True)
    driver.key("Shift_L", True)
    drive_for(driver, 1.8)
    stopped = snap(driver, "up-down-brake-priority")
    assert stopped["speed"] == 0 and not stopped["boosting"]
    driver.release()
    for key in ("a", "d", "Left", "Right", "Shift_L", "Shift_R"):
        before = driver.state()
        driver.key("space", True)
        driver.key(key, True)
        drive_for(driver, 0.3)
        after = snap(driver, f"stopped-{key}")
        assert after["distance"] == before["distance"]
        assert abs(after["lane"] - before["lane"]) < 0.05
        assert not after["drifting"] and not after["boosting"]
        driver.release()
    evidence["stopped-inputs"] = stopped
    for left, right in (("a", "d"), ("Left", "Right"), ("a", "Right"), ("Left", "d")):
        evidence[f"{left}+{right}"] = opposing_steer(driver, left, right)
    for key, direction in (("a", -1), ("d", 1), ("Left", -1), ("Right", 1)):
        evidence[f"Space+{key}"] = drift_release(driver, key, direction)
    for key, direction in (("a", -1), ("d", 1), ("Left", -1), ("Right", 1)):
        start_driving(driver, 1.1)
        driver.key("c", True)
        before = snap(driver, f"rear-{key}-before")
        driver.key(key, True)
        drive_for(driver, 0.2)
        held = snap(driver, f"rear-{key}-held")
        driver.key(key, False)
        driver.key("c", False)
        driver.key("w", False)
        driver.settle()
        drive_for(driver, 0.3)
        after = snap(driver, f"rear-{key}-released")
        assert held["screenRight"] < 0 and after["screenRight"] > 0
        assert (held["lane"] - before["lane"]) * direction > 0.8
        evidence[f"C+{key}"] = [before, held, after]
        driver.release()
    start_driving(driver, 1)
    driver.key("c", True)
    rear = snap(driver, "rear-before-pause")
    assert rear["screenRight"] < 0
    driver.tap("Escape")
    paused = snap(driver, "rear-paused")
    assert paused["phase"] == "PAUSED" and paused["screenRight"] > 0
    driver.release()
    driver.settle()
    assert driver.state()["time"] == paused["time"]
    driver.tap("Escape")
    resumed = snap(driver, "rear-resumed")
    assert resumed["phase"] == "RACING" and resumed["screenRight"] > 0
    evidence["C-pause-release-resume"] = [rear, paused, resumed]
    garage(driver)
    (OUTPUT / "presentation-audit.json").write_text(
        json.dumps(evidence, indent=2) + "\n"
    )
    print(
        "Presented fullscreen, acceleration/coasting, drift release and rear-view transitions passed",
        flush=True,
    )


def states(driver):
    """Capture each disabled binding separately in its different contexts."""
    evidence = {}
    disabled = ("w", "s", "a", "d", "space", "Shift_L", "Shift_R", "c", "r")
    if driver.state()["phase"] != "FINISHED":
        garage(driver)
        launch(driver)
        result = driver.pilot(seconds=180, capture_prefix="state-")
        assert result["phase"] == "FINISHED", result
    result = driver.state()
    evidence["completed-race"] = result
    for key in (*disabled[:-1], "p"):
        driver.key(key, True)
        held = snap(driver, f"state-finished-{key}")
        assert held["phase"] == "FINISHED" and held["time"] == result["time"]
        assert held["distance"] == result["distance"] and held["screenRight"] > 0
        driver.key(key, False)
        driver.settle()
        evidence[f"finished-{key}"] = held
    for forward, backward in (
        ("Down", "Up"),
        ("Right", "Left"),
        ("Tab", "Shift_L"),
        ("Tab", "Shift_R"),
    ):
        driver.tap(forward)
        snap(driver, f"state-result-{forward}-{backward}-forward")
        if backward.startswith("Shift"):
            driver.key(backward, True)
            driver.tap("Tab")
            driver.key(backward, False)
        else:
            driver.tap(backward)
        snap(driver, f"state-result-{forward}-{backward}-back")
    driver.tap("Return")
    driver.wait_phase("COUNTDOWN")
    garage(driver)
    for key in disabled:
        driver.key(key, True)
        held = snap(driver, f"state-garage-{key}")
        assert held["phase"] == "GARAGE" and held["distance"] == 0
        driver.key(key, False)
        driver.settle()
        evidence[f"garage-{key}"] = held
    launch(driver)
    for key in (*disabled[:-1], "Up", "Down", "Left", "Right", "Return", "Tab", "p"):
        driver.tap("r")
        driver.key(key, True)
        held = snap(driver, f"state-countdown-{key}")
        assert held["phase"] == "COUNTDOWN", held
        assert held["time"] == 0 and held["distance"] == 0 and held["lane"] == -3
        assert not held["drifting"] and not held["boosting"]
        assert held["screenRight"] > 0
        driver.key(key, False)
        driver.settle()
        evidence[f"countdown-{key}"] = held
    driver.wait_phase("RACING")
    driver.key("w", True)
    drive_for(driver, 1)
    for key in ("Return", "Tab", "p"):
        before = driver.state()
        driver.tap(key)
        after = snap(driver, f"state-racing-{key}")
        assert after["phase"] == "RACING" and after["time"] > before["time"]
        assert after["overview"] == before["overview"]
        evidence[f"racing-{key}"] = after
    driver.release()
    driver.tap("Escape")
    baseline = driver.state()
    for key in (*disabled[:-1], "p"):
        driver.key(key, True)
        held = snap(driver, f"state-paused-{key}")
        assert held["phase"] == "PAUSED" and held["time"] == baseline["time"]
        assert held["distance"] == baseline["distance"]
        assert held["lane"] == baseline["lane"] and held["screenRight"] > 0
        driver.key(key, False)
        driver.settle()
        evidence[f"paused-{key}"] = held
    for forward, backward in (
        ("Down", "Up"),
        ("Right", "Left"),
        ("Tab", "Shift_L"),
        ("Tab", "Shift_R"),
    ):
        driver.tap(forward)
        snap(driver, f"state-focus-{forward}-{backward}-forward")
        if backward.startswith("Shift"):
            driver.key(backward, True)
            driver.tap("Tab")
            driver.key(backward, False)
        else:
            driver.tap(backward)
        snap(driver, f"state-focus-{forward}-{backward}-back")
    driver.tap("r")
    reset = snap(driver, "state-paused-r-reset")
    assert reset["phase"] == "COUNTDOWN" and reset["distance"] == reset["time"] == 0
    assert reset["nitro"] == 65 and reset["pads"] == reset["bumps"] == 0
    evidence["paused-R"] = reset
    garage(driver)
    (OUTPUT / "state-controls.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(
        "Individual disabled bindings, menu focus recovery and paused R passed",
        flush=True,
    )


def holds(driver):
    """Discrete commands fire once per press, even across native key repeat."""
    garage(driver)
    driver.resize(1280, 800)
    evidence = {}
    original = driver.state()["circuit"]
    driver.tap("Right")  # Browsing also works while Start has focus.
    assert driver.state()["circuit"] != original
    driver.tap("Left")
    assert driver.state()["circuit"] == original
    driver.ui_click(530, 186)
    preview = driver.state()["overview"]
    driver.tap("Left")
    assert driver.state()["overview"] != preview
    snap(driver, "preview-left-arrow")
    driver.tap("Right")
    assert driver.state()["overview"] == preview
    snap(driver, "preview-right-arrow")
    for key, field in (("m", "muted"), ("n", "reducedMotion"), ("p", "overview")):
        before = snap(driver, f"held-{key}-before")
        driver.key(key, True)
        driver.settle()
        changed = driver.state()
        assert changed[field] != before[field]
        time.sleep(1)
        after = snap(driver, f"held-{key}-during")
        assert after[field] == changed[field]
        driver.key(key, False)
        released = snap(driver, f"held-{key}-released")
        assert released[field] == changed[field]
        driver.tap(key)
        assert driver.state()[field] == before[field]
        evidence[key] = [before, after, released]
    launch(driver)
    driver.key("r", True)
    driver.settle()
    before = driver.state()
    time.sleep(1)
    after = snap(driver, "held-r-during")
    assert after["countdown"] < before["countdown"] - 0.3
    driver.key("r", False)
    driver.wait_phase("RACING")
    driver.key("Escape", True)
    driver.wait_phase("PAUSED")
    before = driver.state()
    time.sleep(1)
    after = snap(driver, "held-escape-during")
    assert after["phase"] == "PAUSED" and after["time"] == before["time"]
    driver.key("Escape", False)
    for forward, backward in (
        ("Down", "Up"),
        ("Right", "Left"),
        ("Tab", "Shift_L"),
        ("Tab", "Shift_R"),
    ):
        driver.key(forward, True)
        driver.settle()
        time.sleep(0.8)
        driver.key(forward, False)
        snap(driver, f"held-menu-{forward}-{backward}")
        if backward.startswith("Shift"):
            driver.key(backward, True)
            driver.key("Tab", True)
            driver.settle()
            time.sleep(0.8)
            driver.key("Tab", False)
            driver.key(backward, False)
        else:
            driver.key(backward, True)
            driver.settle()
            time.sleep(0.8)
            driver.key(backward, False)
        driver.tap("Return")
        driver.wait_phase("RACING")
        driver.tap("Escape")
        driver.wait_phase("PAUSED")
    garage(driver)
    driver.key("Return", True)
    driver.wait_phase("COUNTDOWN")
    time.sleep(0.8)
    assert driver.state()["phase"] == "COUNTDOWN"
    driver.key("Return", False)
    garage(driver)
    (OUTPUT / "held-controls.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(
        "Held toggle, restart, pause, Enter and menu-repeat checks passed", flush=True
    )


def audit(driver):
    from PIL import Image, ImageChops

    evidence = {}
    garage(driver)
    driver.resize(1280, 800)
    select(driver, 2)

    def window_size():
        info = subprocess.check_output(
            ["xwininfo", "-id", hex(driver.window)], text=True
        )
        return [
            int(re.search(rf"{field}:\s+(\d+)", info)[1])
            for field in ("Width", "Height")
        ]

    normal_size = window_size()
    driver.tap("F11")
    evidence["F11-fullscreen"] = window_size()
    snap(driver, "fullscreen")
    assert window_size() != normal_size
    driver.tap("F11")
    assert window_size() == normal_size
    snap(driver, "window-restored")
    # An unbound mouse button must not accidentally start a race.
    for button in (2, 3):
        driver.ui_click(180, 660, button)
        assert driver.state()["phase"] == "GARAGE"
    baseline = snap(driver, "garage-before-disabled")
    for key in ("w", "s", "a", "d", "space", "Shift_L", "Shift_R", "c", "r"):
        driver.tap(key)
        assert driver.state()["phase"] == "GARAGE"
        assert driver.state()["distance"] == 0
        assert driver.state()["paint"] == baseline["paint"]
    evidence["garage-disabled"] = snap(driver, "garage-after-disabled")

    # All five paints wrap correctly and change the actual starting-grid car.
    for i in range(5):
        driver.ui_click(180, 538)
        state = snap(driver, f"paint-{i}")
        assert state["paint"] == (baseline["paint"] + i + 1) % 5
        assert not state["overview"]
    paint = driver.state()["paint"]
    driver.tap("Return")
    assert driver.state()["paint"] == (paint + 1) % 5
    driver.tap("Left")
    assert driver.state()["paint"] == paint
    pace = driver.state()["difficulty"]
    pace_index = DIFFICULTIES.index(pace)
    for step in range(1, 5):
        driver.ui_click(180, 590)
        expected = DIFFICULTIES[(pace_index + step) % 4]
        assert driver.state()["difficulty"] == expected
        snap(driver, f"difficulty-{expected}")
    driver.ui_click(180, 590)
    assert driver.state()["difficulty"] == DIFFICULTIES[(pace_index + 1) % 4]
    driver.tap("Return")
    assert driver.state()["difficulty"] == DIFFICULTIES[(pace_index + 2) % 4]
    driver.tap("Left")
    assert driver.state()["difficulty"] == DIFFICULTIES[(pace_index + 1) % 4]
    driver.tap("Left")
    assert driver.state()["difficulty"] == pace
    driver.ui_click(530, 186)
    assert driver.state()["overview"]
    driver.tap("Return")
    assert not driver.state()["overview"]
    driver.tap("Return")
    assert driver.state()["overview"]
    driver.tap("p")
    assert not driver.state()["overview"]
    driver.tap("p")
    assert driver.state()["overview"]
    driver.tap("Tab")  # Wrap from preview (last action) to first circuit.
    assert driver.state()["circuit"] == "SUNSET"
    driver.key("Shift_R", True)
    driver.tap("Tab")
    driver.key("Shift_R", False)
    driver.key("Shift_L", True)
    driver.tap("Tab")
    driver.key("Shift_L", False)
    driver.tap("Return")  # Start race from the focused primary action.
    driver.wait_phase("COUNTDOWN")
    driver.tap("Escape")
    driver.tap("Down")
    driver.tap("Return")  # Enter on Restart.
    driver.wait_phase("COUNTDOWN")
    driver.tap("Escape")
    driver.tap("Up")  # Wrap from Resume to Garage.
    driver.tap("Return")
    driver.wait_phase("GARAGE")
    for key, expected in (("Right", "SILICON_VALLEY"), ("Left", "CINDER")):
        select(driver, 0)
        driver.ui_hover(165, 284)
        assert driver.state()["circuit"] == "SUNSET"
        driver.tap(key)
        assert driver.state()["circuit"] == expected
        evidence[f"hover-{key}"] = snap(driver, f"hover-route-{key}")
    select(driver, 0)
    driver.ui_hover(165, 284)  # Hover the SF route, without clicking/selecting it.
    assert driver.state()["circuit"] == "SUNSET"
    snap(driver, "hover-route-before-enter")
    driver.tap("Return")  # Enter must activate the visibly focused route.
    driver.wait_phase("COUNTDOWN")
    assert driver.state()["circuit"] == "SAN_FRANCISCO"
    evidence["hover-Enter"] = snap(driver, "hover-route-after-enter")
    garage(driver)

    # Camera motion is verified from pixels, in addition to the setting label.
    if not driver.state()["reducedMotion"]:
        driver.tap("n")
    snap(driver, "motion-reduced-before")
    time.sleep(1.2)
    snap(driver, "motion-reduced-after")

    def scene(name):
        return (
            Image.open(OUTPUT / f"control-{name}.png")
            .convert("RGB")
            .crop((700, 270, 1050, 550))
        )

    assert (
        ImageChops.difference(
            scene("motion-reduced-before"), scene("motion-reduced-after")
        ).getbbox()
        is None
    )
    driver.tap("n")
    snap(driver, "motion-full-before")
    time.sleep(1.2)
    snap(driver, "motion-full-after")
    assert (
        ImageChops.difference(
            scene("motion-full-before"), scene("motion-full-after")
        ).getbbox()
        is not None
    )
    evidence["N-garage"] = "reduced frames identical; full-motion frames differ"

    if driver.state()["muted"]:
        driver.tap("m")
    evidence["M-menu-on"] = record_game_audio(driver, "audio-menu-on")
    driver.tap("m")
    snap(driver, "sound-off")
    evidence["M-menu-off"] = record_game_audio(driver, "audio-menu-off")
    driver.tap("m")
    snap(driver, "sound-on")
    evidence["M-menu-restored"] = record_game_audio(driver, "audio-menu-restored")
    assert evidence["M-menu-on"]["rms"] > 10
    assert evidence["M-menu-off"]["peak"] <= 1
    assert evidence["M-menu-restored"]["rms"] > 10

    # Both physical acceleration and brake bindings, with release/coast evidence.
    for throttle, brake in (("w", "s"), ("Up", "Down")):
        launch(driver)
        driver.wait_phase("RACING")
        before = snap(driver, f"{throttle}-before")
        driver.key(throttle, True)
        drive_for(driver, 1.4)
        during = snap(driver, f"{throttle}-held")
        assert during["speed"] > 25 and during["distance"] > before["distance"]
        driver.key(throttle, False)
        driver.settle()
        coast_start = driver.state()
        assert not coast_start["inputThrottle"]
        drive_for(driver, 1.2)
        after = snap(driver, f"{throttle}-released")
        assert after["speed"] < coast_start["speed"], (coast_start, after)
        driver.key(brake, True)
        drive_for(driver, 1.5)
        stopped = snap(driver, f"{brake}-stopped")
        assert stopped["speed"] == 0
        driver.release()
        evidence[throttle] = [before, during, coast_start, after]
        evidence[brake] = stopped

    # Both Shift keys cause fuel use, faster travel, zoom and visible exhaust.
    for key in ("Shift_L", "Shift_R"):
        if key == "Shift_L":
            launch(driver)
            driver.wait_phase("RACING")
            # The motion comparison includes multiple captured frames. Fill
            # nitro through normal regeneration so it cannot expire mid-check.
            drive_for(driver, 11.8)
            assert driver.state()["nitro"] >= 99
            driver.key("w", True)
            drive_for(driver, 2.3)
        else:
            start_driving(driver, 2.3)
        driver.center_for(0.3)
        before = snap(driver, f"{key}-before")
        driver.key(key, True)
        driver.center_for(0.6)
        during = snap(driver, f"{key}-held")
        assert during["boosting"] and during["speed"] > before["speed"]
        assert during["nitro"] < before["nitro"]
        if key == "Shift_L":
            assert during["cameraFov"] > 71
            driver.tap("n")
            driver.center_for(0.8)
            reduced = snap(driver, "motion-reduced-boost")
            assert reduced["boosting"] and reduced["cameraFov"] < 70, reduced
            evidence["N-racing"] = [during, reduced]
            driver.tap("n")
        driver.key(key, False)
        drive_for(driver, 0.2)
        after = snap(driver, f"{key}-released")
        assert not after["boosting"]
        evidence[key] = [before, during, after]
        driver.release()

    # Space needs steering; each directional binding also works in the chord.
    for key, direction in (("a", -1), ("d", 1), ("Left", -1), ("Right", 1)):
        evidence[f"Space+{key}"] = drift_release(driver, key, direction)

    # Rear view deliberately keeps car-relative steering; the HUD explains it.
    for key, direction in (("a", -1), ("d", 1), ("Left", -1), ("Right", 1)):
        start_driving(driver, 1.3)
        driver.key("c", True)
        before = snap(driver, f"rear-{key}-before")
        assert before["screenRight"] < 0
        driver.key(key, True)
        drive_for(driver, 0.35)
        during = snap(driver, f"rear-{key}-held")
        assert (during["lane"] - before["lane"]) * direction > 0.8
        assert during["screenRight"] < 0
        driver.key(key, False)
        driver.key("c", False)
        after = snap(driver, f"rear-{key}-released")
        assert after["screenRight"] > 0
        evidence[f"C+{key}"] = [before, during, after]
        driver.release()

    start_driving(driver, 1.5)
    preview = driver.state()["overview"]
    driver.tap("p")
    assert driver.state()["overview"] == preview
    driver.key("s", True)
    drive_for(driver, 1.5)
    assert driver.state()["speed"] == 0  # Brake wins over held W.
    driver.release()
    for pair in (("a", "d"), ("Left", "Right")):
        for key in pair:
            driver.key(key, True)
        driver.settle()
        assert driver.state()["inputSteer"] == 0
        driver.release()
    evidence["opposing-inputs"] = snap(driver, "opposing-inputs")

    # Record actual racing audio before/after M, then verify pause is silent.
    driver.key("w", True)
    drive_for(driver, 1)
    evidence["M-race-on"] = record_game_audio(driver, "audio-race-on")
    driver.tap("m")
    evidence["M-race-off"] = record_game_audio(driver, "audio-race-off")
    driver.tap("m")
    evidence["M-race-restored"] = record_game_audio(driver, "audio-race-restored")
    assert evidence["M-race-on"]["rms"] > 10 and evidence["M-race-restored"]["rms"] > 10
    assert evidence["M-race-off"]["peak"] <= 1
    driver.release()
    driver.tap("Escape")
    driver.wait_phase("PAUSED")
    evidence["paused-audio"] = record_game_audio(driver, "audio-paused")
    assert evidence["paused-audio"]["peak"] <= 1
    driver.tap("m")
    driver.tap("Escape")
    driver.wait_phase("RACING")
    evidence["M-muted-through-resume"] = record_game_audio(driver, "audio-muted-resume")
    assert evidence["M-muted-through-resume"]["peak"] <= 1
    driver.tap("m")
    driver.tap("Escape")
    driver.wait_phase("PAUSED")

    # Every navigation binding and both Shift+Tab chords: focus moves, then
    # Enter proves that focus is on Resume rather than Restart or Garage.
    for forward, backward in (
        ("Down", "Up"),
        ("Right", "Left"),
        ("Tab", "Shift_L"),
        ("Tab", "Shift_R"),
    ):
        driver.tap(forward)
        snap(driver, f"pause-focus-{forward}-{backward}")
        if backward.startswith("Shift"):
            driver.key(backward, True)
            driver.tap("Tab")
            driver.key(backward, False)
        else:
            driver.tap(backward)
        before = driver.state()["time"]
        driver.tap("Return")
        driver.wait_phase("RACING")
        assert driver.state()["time"] >= before
        driver.tap("Escape")
        driver.wait_phase("PAUSED")
    driver.ui_click(610, 344)  # Resume.
    driver.wait_phase("RACING")
    driver.tap("Escape")
    driver.ui_click(610, 415)  # Restart.
    driver.wait_phase("COUNTDOWN")
    frozen = driver.state()
    for key in ("w", "a", "space", "Shift_L", "c"):
        driver.key(key, True)
    time.sleep(0.35)
    assert driver.state()["distance"] == 0
    assert driver.state()["screenRight"] > 0
    assert not driver.state()["boosting"] and not driver.state()["drifting"]
    driver.release()
    driver.tap("Escape")
    driver.wait_phase("PAUSED")
    before = driver.state()
    for key in ("w", "s", "a", "d", "space", "Shift_L", "Shift_R", "c", "p"):
        driver.tap(key)
    after = snap(driver, "paused-disabled")
    for field in ("time", "distance", "lane", "countdown", "nitro"):
        assert before[field] == after[field]
    driver.tap("r")
    driver.wait_phase("COUNTDOWN")
    driver.tap("r")
    driver.wait_phase("COUNTDOWN")
    assert driver.state()["countdown"] > frozen["countdown"] - 0.3
    for key in (
        "w",
        "Up",
        "s",
        "Down",
        "a",
        "Left",
        "d",
        "Right",
        "space",
        "Shift_L",
        "Shift_R",
        "c",
        "p",
    ):
        driver.tap(key)
        assert (
            driver.state()["phase"] == "COUNTDOWN" and driver.state()["distance"] == 0
        )
        driver.tap("r")
    evidence["countdown-disabled"] = snap(driver, "countdown-disabled")
    garage(driver)

    evidence["focus-release"] = focus_release(driver)
    # Repeat the original mechanics audit on the final build as well.
    mechanics(driver)
    (OUTPUT / "control-audit.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("Control audit passed:", len(evidence), "evidence groups", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--holds-only", action="store_true")
    mode.add_argument("--presentation-only", action="store_true")
    mode.add_argument("--states-only", action="store_true")
    mode.add_argument("--focus-only", action="store_true")
    args = parser.parse_args()
    instance = Driver()
    try:
        if args.focus_only:
            focus_release(instance)
        elif args.states_only:
            states(instance)
        elif args.presentation_only:
            presentation(instance)
        elif args.holds_only:
            holds(instance)
        else:
            audit(instance)
    except AssertionError:
        (OUTPUT / "control-audit-failure.json").write_text(
            json.dumps(instance.state(), indent=2) + "\n"
        )
        instance.screenshot("control-audit-failure")
        raise
    finally:
        instance.release()
