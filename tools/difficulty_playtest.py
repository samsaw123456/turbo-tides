"""Verify four difficulty choices and their effect through native keyboard input."""

import argparse
import json
import time

from city_playtest import (
    CIRCUITS,
    DIFFICULTIES,
    garage,
    launch,
    save,
    select,
    select_difficulty,
)
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


def skilled_pilot(driver, capture_prefix="difficulty-skilled-"):
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
                driver.screenshot(f"{capture_prefix}lap-{state['lap']}")
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


def matrix(driver, circuits=CIRCUITS, difficulties=DIFFICULTIES):
    """Finish every selected combination through the native interface.

    Keep failed finishes as evidence and continue the other combinations. Use
    a separate output directory for retries so no earlier capture is replaced.
    """
    path = OUTPUT / "matrix-results.json"
    if path.exists():
        raise RuntimeError("Use a new TURBO_TEST_OUTPUT directory for each matrix run")
    results = []
    garage(driver)
    driver.resize(1280, 800)
    for circuit in circuits:
        select(driver, CIRCUITS.index(circuit))
        for difficulty in difficulties:
            select_difficulty(driver, difficulty)
            assert driver.state()["circuit"] == circuit
            prefix = f"matrix-{difficulty.lower()}-{circuit.lower()}-"
            driver.screenshot(prefix + "menu")
            launch(driver)
            start = driver.state()
            assert start["time"] == 0 and start["distance"] == 0, start
            wall_start = time.monotonic()
            if difficulty in ("HARD", "SUPER_HARD"):
                finish = skilled_pilot(driver, capture_prefix=prefix)
                strategy = "digital steering, drifting, pads and boost"
            else:
                finish = driver.pilot(
                    seconds=180,
                    capture_prefix=f"matrix-{difficulty.lower()}-",
                )
                strategy = "digital steering, pads and boost"
            driver.release()
            driver.settle()
            driver.screenshot(prefix + "result")
            passed = (
                finish["phase"] == "FINISHED"
                and finish["circuit"] == circuit
                and finish["difficulty"] == difficulty
                and finish["position"] == 1
                and finish["lap"] == 3
                and finish["distance"] >= finish["length"] * 3
                and not finish["saveError"]
            )
            results.append(
                {
                    "circuit": circuit,
                    "difficulty": difficulty,
                    "status": "passed" if passed else "failed",
                    "strategy": strategy,
                    "wallSeconds": round(time.monotonic() - wall_start, 2),
                    "framePrefix": prefix,
                    "start": start,
                    "finish": finish,
                }
            )
            path.write_text(json.dumps(results, indent=2) + "\n")
            print(
                f"{'PASS' if passed else 'FAIL'} {circuit} {difficulty}: "
                f"position {finish['position']}, time {finish['time']:.2f}s, "
                f"drifts {finish['driftBonuses']}, pads {finish['pads']}",
                flush=True,
            )
            garage(driver)
    assert all(row["status"] == "passed" for row in results), (
        "Matrix contains failed finishes; inspect matrix-results.json"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=("menu", "races", "skill", "matrix"))
    parser.add_argument("--circuit", choices=CIRCUITS, action="append")
    parser.add_argument("--difficulty", choices=DIFFICULTIES, action="append")
    args = parser.parse_args()
    if args.scenario != "matrix" and (args.circuit or args.difficulty):
        parser.error("Track/difficulty filters apply only to matrix")
    driver = Driver()
    try:
        if args.scenario == "matrix":
            matrix(
                driver,
                tuple(dict.fromkeys(args.circuit or CIRCUITS)),
                tuple(dict.fromkeys(args.difficulty or DIFFICULTIES)),
            )
        else:
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
