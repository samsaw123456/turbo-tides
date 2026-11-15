"""Native-input regression audit for the city update; never writes game state.

Run with DISPLAY set and the app launched using --telemetry
/tmp/turbo-tides-playtest.json. Screenshots and measured evidence go to build/playtest.
"""

import argparse
import ctypes
import json
import time

from playtest import OUTPUT, Driver

CIRCUITS = (
    "SUNSET",
    "CINDER",
    "SAN_FRANCISCO",
    "SILICON_VALLEY",
    "NEW_YORK",
    "CHICAGO",
)


def save(name, result):
    (OUTPUT / f"{name}.json").write_text(json.dumps(result, indent=2) + "\n")
    print(name, json.dumps(result), flush=True)


def garage(driver):
    driver.release()
    phase = driver.state()["phase"]
    if phase == "FINISHED":
        driver.tap("Escape")
    elif phase != "GARAGE":
        if phase != "PAUSED":
            driver.tap("Escape")
        driver.ui_click(610, 490)
    driver.wait_phase("GARAGE")


def select(driver, index):
    driver.ui_click(165, 160 + index * 62)
    deadline = time.monotonic() + 8
    while driver.state()["circuit"] != CIRCUITS[index]:
        if time.monotonic() > deadline:
            raise AssertionError(driver.state())
        time.sleep(0.1)


def menu(driver):
    garage(driver)
    driver.resize(1280, 800)
    results = []
    for index, circuit in enumerate(CIRCUITS):
        select(driver, index)
        assert driver.state()["overview"]
        time.sleep(0.5)
        driver.screenshot(f"preview-{circuit.lower()}")
        results.append(driver.state())
        driver.tap("p")
        assert not driver.state()["overview"]
        driver.screenshot(f"grid-{circuit.lower()}")
        driver.tap("p")
    select(driver, 0)
    driver.tap("Left")
    assert driver.state()["circuit"] == "CHICAGO"
    driver.tap("Right")
    assert driver.state()["circuit"] == "SUNSET"
    driver.tap("Down")
    assert driver.state()["circuit"] == "CINDER"
    driver.tap("Up")
    assert driver.state()["circuit"] == "SUNSET"
    # All six scenes are cached; repeated selection must remain responsive.
    for _ in range(18):
        driver.tap("Right")
    assert driver.state()["circuit"] == "SUNSET"
    select(driver, 5)
    driver.tap("Tab")
    paint = driver.state()["paint"]
    driver.tap("Right")
    assert driver.state()["paint"] == (paint + 1) % 5
    assert not driver.state()["overview"]
    driver.tap("Left")
    assert driver.state()["paint"] == paint
    driver.tap("Tab")
    pace = driver.state()["difficulty"]
    driver.tap("Right")
    assert driver.state()["difficulty"] != pace
    driver.tap("Left")
    assert driver.state()["difficulty"] == pace
    for key, field in (("m", "muted"), ("n", "reducedMotion")):
        before = driver.state()[field]
        driver.tap(key)
        assert driver.state()[field] != before
        driver.tap(key)
        assert driver.state()[field] == before
    driver.resize(960, 640)
    for index, circuit in enumerate(CIRCUITS):
        select(driver, index)
        driver.screenshot(f"preview-{circuit.lower()}-960")
    windowed_bounds = driver.window_bounds()
    for cycle in range(3):
        driver.tap("F11")
        time.sleep(0.5)
        if cycle == 0:
            driver.screenshot("city-fullscreen")
        driver.tap("F11")
        time.sleep(1.1)
        assert driver.window_bounds() == windowed_bounds, (
            "Fullscreen must restore the client size and position on every toggle",
            windowed_bounds,
            driver.window_bounds(),
        )
    driver.resize(1280, 800)
    save("city-menu", results)


def launch(driver):
    driver.release()
    if driver.state()["phase"] == "GARAGE":
        driver.ui_click(180, 660)
    else:
        driver.tap("r")
    driver.wait_phase("COUNTDOWN")


def drive_for(driver, seconds):
    """Measure held input in simulation time, even on a loaded software renderer."""
    start = driver.state()["time"]
    deadline = time.monotonic() + seconds * 5 + 8
    while driver.state()["time"] < start + seconds:
        if time.monotonic() > deadline:
            raise AssertionError(f"Race did not advance: {driver.state()}")
        time.sleep(0.03)


def mechanics(driver):
    garage(driver)
    select(driver, 2)
    evidence = {}
    # Each pair is measured from a fresh start, free of previous lateral input.
    for key, direction in (("a", -1), ("d", 1), ("Left", -1), ("Right", 1)):
        launch(driver)
        driver.key("Up", True)
        driver.wait_phase("RACING")
        drive_for(driver, 1.35)
        before = driver.state()
        driver.key(key, True)
        drive_for(driver, 0.5)
        after = driver.state()
        assert after["inputSteer"] == direction, after
        assert (after["lane"] - before["lane"]) * direction > 1.4, (before, after)
        assert after["screenRight"] > 0, after
        driver.screenshot(f"steering-{key.lower()}")
        evidence[key] = {"before": before, "after": after}
        driver.release()
    driver.key("a", True)
    driver.key("d", True)
    driver.settle()
    assert driver.state()["inputSteer"] == 0
    driver.release()
    driver.key("Down", True)
    drive_for(driver, 2)
    assert driver.state()["speed"] == 0
    stopped = driver.state()
    driver.key("Left", True)
    drive_for(driver, 0.6)
    assert abs(driver.state()["lane"] - stopped["lane"]) < 0.05
    driver.release()
    # Boost, drift and recovery are exercised with ordinary held keys.
    launch(driver)
    driver.key("w", True)
    driver.wait_phase("RACING")
    drive_for(driver, 2.2)
    driver.key("space", True)
    driver.key("d", True)
    drive_for(driver, 0.65)
    assert driver.state()["drifting"]
    driver.screenshot("city-drift")
    driver.key("space", False)
    driver.key("d", False)
    driver.settle()
    assert driver.state()["driftBonuses"] > 0
    driver.pilot(seconds=2, capture=False)
    driver.key("Shift_R", True)
    driver.key("w", True)
    fuel = driver.state()["nitro"]
    drive_for(driver, 0.35)
    assert driver.state()["boosting"], driver.state()
    assert driver.state()["nitro"] < fuel, driver.state()
    driver.screenshot("city-boost")
    driver.release()
    driver.key("w", True)
    driver.key("d", True)
    drive_for(driver, 3.5)
    assert driver.state()["bumps"] > 0
    assert abs(driver.state()["lane"]) <= 12
    assert driver.state()["speed"] <= 29
    driver.screenshot("city-wall")
    driver.release()
    driver.pilot(seconds=4, capture=False)
    assert abs(driver.state()["lane"]) < 6
    driver.key("c", True)
    time.sleep(0.3)
    driver.screenshot("city-rear-view")
    driver.key("c", False)
    driver.tap("Escape")
    driver.release()
    driver.wait_phase("PAUSED")
    paused = driver.state()
    time.sleep(0.7)
    after = driver.state()
    for field in ("time", "distance", "lane", "nitro"):
        assert paused[field] == after[field], (paused, after)
    driver.resize(960, 640)
    driver.screenshot("city-paused-960")
    driver.resize(1280, 800)
    driver.tap("Escape")
    driver.wait_phase("RACING")
    # Release the accelerator while focus is elsewhere, then resume: no stuck W.
    driver.key("w", True)
    driver.x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    driver.x.XDefaultRootWindow.restype = ctypes.c_ulong
    root = driver.x.XDefaultRootWindow(driver.display)
    driver.x.XSetInputFocus(driver.display, root, 2, 0)
    driver.x.XFlush(driver.display)
    driver.wait_phase("PAUSED")
    driver.release()
    driver.focus()
    driver.tap("Escape")
    driver.wait_phase("RACING")
    assert not driver.state()["inputThrottle"]
    driver.tap("r")
    driver.wait_phase("COUNTDOWN")
    fresh = driver.state()
    assert fresh["time"] == fresh["distance"] == fresh["bumps"] == fresh["pads"] == 0
    assert fresh["nitro"] == 65 and fresh["driftBonuses"] == 0
    driver.tap("Escape")
    frozen = driver.state()["countdown"]
    time.sleep(0.5)
    assert driver.state()["countdown"] == frozen
    driver.tap("Escape")
    driver.wait_phase("COUNTDOWN")
    evidence["pause"] = paused
    evidence["restart"] = fresh
    save("city-mechanics", evidence)
    garage(driver)


def circuits(driver):
    results = []
    garage(driver)
    for index, circuit in enumerate(CIRCUITS):
        select(driver, index)
        expected_pace = "CRUISE" if index % 2 == 0 else "RACE"
        if driver.state()["difficulty"] != expected_pace:
            driver.ui_click(180, 590)
        if index == 4:
            driver.resize(960, 640)
            if not driver.state()["reducedMotion"]:
                driver.tap("n")
        else:
            driver.resize(1280, 800)
        launch(driver)
        result = driver.pilot(seconds=150)
        driver.screenshot(f"finish-{circuit.lower()}")
        assert result["phase"] == "FINISHED", result
        assert result["position"] == 1 and result["lap"] == 3, result
        assert result["pads"] >= 3, result
        assert result["best"] is not None and not result["saveError"], result
        results.append(result)
        save("city-races", results)
        if index == 0:
            # Disabled driving inputs cannot change a completed result.
            for key in ("w", "s", "a", "d", "space", "Shift_L", "Shift_R", "c", "p"):
                driver.tap(key)
                assert driver.state()["time"] == result["time"]
                assert driver.state()["distance"] == result["distance"]
            # Result-menu arrows, Tab and both reverse-Tab bindings move focus.
            for forward, backward in (
                ("Down", "Up"),
                ("Right", "Left"),
                ("Tab", "Shift_L"),
                ("Tab", "Shift_R"),
            ):
                driver.tap(forward)
                driver.screenshot(f"result-focus-{forward}-{backward}")
                if backward.startswith("Shift"):
                    driver.key(backward, True)
                    driver.tap("Tab")
                    driver.key(backward, False)
                else:
                    driver.tap(backward)
            driver.tap("Return")
            driver.wait_phase("COUNTDOWN")
            garage(driver)
        elif index == 1:
            driver.ui_click(480, 568)
            driver.wait_phase("COUNTDOWN")
            garage(driver)
        elif index == 2:
            driver.tap("r")
            driver.wait_phase("COUNTDOWN")
            garage(driver)
        elif index == 3:
            driver.tap("Escape")
            driver.wait_phase("GARAGE")
        elif index == 4:
            driver.ui_click(760, 568)
            driver.wait_phase("GARAGE")
        else:
            driver.tap("Right")
            driver.tap("Return")
            driver.wait_phase("GARAGE")
    driver.resize(1280, 800)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=("menu", "mechanics", "circuits"))
    args = parser.parse_args()
    driver = Driver()
    try:
        globals()[args.scenario](driver)
    finally:
        driver.release()


if __name__ == "__main__":
    main()
