"""Verify four difficulty choices and their effect through native keyboard input."""

import argparse
import json
import time

from city_playtest import DIFFICULTIES, garage, launch, save, select, select_difficulty
from playtest import OUTPUT, Driver


def menu(driver):
    garage(driver)
    select(driver, 2)
    original = driver.state()["difficulty"]
    for width, height in ((1280, 800), (960, 640)):
        driver.resize(width, height)
        select_difficulty(driver, "EASY")
        driver.ui_hover(180, 590)
        driver.settle()
        for direction, expected in (
            ("Left", ("SUPER_HARD", "HARD", "MEDIUM", "EASY")),
            ("Right", ("MEDIUM", "HARD", "SUPER_HARD", "EASY")),
            ("Return", ("MEDIUM", "HARD", "SUPER_HARD", "EASY")),
        ):
            for name in expected:
                driver.tap(direction)
                assert driver.state()["difficulty"] == name, driver.state()
                driver.screenshot(f"difficulty-{width}-{direction}-{name}")
        for name in ("MEDIUM", "HARD", "SUPER_HARD", "EASY"):
            driver.ui_click(180, 590)
            assert driver.state()["difficulty"] == name
        driver.key("Right", True)
        time.sleep(1)
        driver.settle()
        assert driver.state()["difficulty"] == "MEDIUM"
        driver.key("Right", False)
        driver.screenshot(f"difficulty-{width}-held-right")
    driver.resize(1280, 800)
    select_difficulty(driver, original)
    save(
        "difficulty-menu",
        {
            "directions": "both",
            "levels": DIFFICULTIES,
            "sizes": [1280, 960],
            "heldKeyRepeats": False,
        },
    )


def skilled_pilot(driver):
    deadline = time.monotonic() + 160
    captured = set()
    try:
        while time.monotonic() < deadline:
            state = driver.state()
            if state["phase"] == "FINISHED":
                return state
            target = 4.5 if int(state["time"] / 0.9) % 2 == 0 else -4.5
            for pad in range(3):
                ahead = (
                    state["length"] * (0.15 + pad * 0.25) - state["distance"]
                ) % state["length"]
                if ahead < 65 or ahead > state["length"] - 4:
                    target = -3.6 if pad % 2 == 0 else 3.6
            driver.key("w", True)
            driver.key("space", state["time"] % 0.9 < 0.75)
            driver.key("Shift_L", True)
            driver.steer_toward(state, target)
            if state["lap"] not in captured and state["time"] > 7:
                captured.add(state["lap"])
                driver.screenshot(f"difficulty-skilled-lap-{state['lap']}")
            time.sleep(0.035)
    finally:
        driver.release()
    raise AssertionError("Skilled race did not finish")


def races(driver):
    results = []
    garage(driver)
    select(driver, 2)
    for name in DIFFICULTIES:
        select_difficulty(driver, name)
        launch(driver)
        result = driver.pilot(seconds=160, capture_prefix=f"difficulty-{name.lower()}-")
        assert result["phase"] == "FINISHED" and result["difficulty"] == name
        if name in ("EASY", "MEDIUM"):
            assert result["position"] == 1, result
        else:
            assert result["position"] > 1, result
        driver.screenshot(f"difficulty-{name}-result")
        results.append(result)
        save("difficulty-races", results)
        driver.tap("r")
        assert driver.state()["difficulty"] == name
        driver.wait_phase("COUNTDOWN")
        driver.tap("Escape")
        driver.screenshot(f"difficulty-{name}-paused-retry")
        assert driver.state()["difficulty"] == name
        garage(driver)
    select_difficulty(driver, "EASY")


def skill(driver):
    garage(driver)
    select(driver, 2)
    select_difficulty(driver, "SUPER_HARD")
    launch(driver)
    result = skilled_pilot(driver)
    driver.screenshot("difficulty-super-hard-skilled-result")
    save("difficulty-skilled", result)
    assert result["position"] == 1 and result["driftBonuses"] >= 10, result
    garage(driver)
    select_difficulty(driver, "EASY")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=("menu", "races", "skill"))
    args = parser.parse_args()
    driver = Driver()
    try:
        globals()[args.scenario](driver)
    except AssertionError:
        (OUTPUT / "difficulty-failure.json").write_text(
            json.dumps(driver.state(), indent=2)
        )
        driver.screenshot("difficulty-failure")
        raise
    finally:
        driver.release()


if __name__ == "__main__":
    main()
