"""Drive the native Linux window with real X11 key events, using opt-in telemetry.

Launch with --telemetry /tmp/turbo-tides-playtest.json first. No game state is
modified by this script. XTest/libX11 and ImageMagick are the only system tools.
"""

import argparse
import ctypes
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/playtest"
TELEMETRY = Path("/tmp/turbo-tides-playtest.json")


class Driver:
    def __init__(self):
        self.x = ctypes.CDLL("libX11.so.6")
        self.xt = ctypes.CDLL("libXtst.so.6")
        self.x.XOpenDisplay.restype = ctypes.c_void_p
        self.x.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.display = self.x.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError("An X11/XWayland display is required")
        self.x.XStringToKeysym.argtypes = [ctypes.c_char_p]
        self.x.XStringToKeysym.restype = ctypes.c_ulong
        self.x.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        self.x.XKeysymToKeycode.restype = ctypes.c_uint
        self.x.XSetInputFocus.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_ulong,
        ]
        self.x.XRaiseWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        self.x.XResizeWindow.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_uint,
            ctypes.c_uint,
        ]
        self.x.XFlush.argtypes = [ctypes.c_void_p]
        self.xt.XTestFakeKeyEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_ulong,
        ]
        self.xt.XTestFakeMotionEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_ulong,
        ]
        self.xt.XTestFakeButtonEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_ulong,
        ]
        match = None
        for _ in range(50):
            tree = subprocess.check_output(["xwininfo", "-root", "-tree"], text=True)
            match = re.search(r'(0x[0-9a-f]+) "Turbo Tides": \("Turbo Tides"', tree)
            if match:
                break
            time.sleep(0.1)
        if not match:
            raise RuntimeError("Turbo Tides is not running")
        self.window = int(match.group(1), 16)
        for _ in range(100):
            info = subprocess.check_output(
                ["xwininfo", "-id", hex(self.window)], text=True
            )
            if "Map State: IsViewable" in info:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("The native game window did not become visible")
        self.held = set()
        self.focus()
        OUTPUT.mkdir(parents=True, exist_ok=True)

    def focus(self):
        self.x.XRaiseWindow(self.display, self.window)
        self.x.XSetInputFocus(self.display, self.window, 2, 0)
        self.x.XFlush(self.display)
        time.sleep(0.15)

    def key(self, name, down):
        if down == (name in self.held):
            return
        code = self.x.XKeysymToKeycode(
            self.display, self.x.XStringToKeysym(name.encode())
        )
        self.xt.XTestFakeKeyEvent(self.display, code, int(down), 0)
        self.x.XFlush(self.display)
        if down:
            self.held.add(name)
        else:
            self.held.discard(name)

    def tap(self, name):
        self.key(name, True)
        time.sleep(0.09)
        self.key(name, False)
        time.sleep(0.12)

    def release(self):
        for key in list(self.held):
            self.key(key, False)

    def state(self):
        for _ in range(100):
            try:
                if time.time() - TELEMETRY.stat().st_mtime < 4:
                    return json.loads(TELEMETRY.read_text())
            except (OSError, json.JSONDecodeError):
                pass
            time.sleep(0.1)
        raise RuntimeError("No fresh telemetry from the game; it may have exited")

    def wait_phase(self, phase, timeout=8):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.state()["phase"] == phase:
                return
            time.sleep(0.08)
        raise AssertionError(f"Expected {phase}, got {self.state()}")

    def screenshot(self, name):
        # Telemetry is written before the native buffer swap; let the displayed
        # frame catch up before capturing a just-finished race or changed menu.
        time.sleep(0.1)
        subprocess.run(
            ["import", "-window", hex(self.window), str(OUTPUT / f"{name}.png")],
            check=True,
        )

    def resize(self, width, height):
        self.x.XResizeWindow(self.display, self.window, width, height)
        self.x.XFlush(self.display)
        time.sleep(0.4)

    def click(self, x, y):
        info = subprocess.check_output(["xwininfo", "-id", hex(self.window)], text=True)
        left = int(re.search(r"Absolute upper-left X:\s+(\d+)", info)[1])
        top = int(re.search(r"Absolute upper-left Y:\s+(\d+)", info)[1])
        self.xt.XTestFakeMotionEvent(self.display, -1, left + x, top + y, 0)
        self.xt.XTestFakeButtonEvent(self.display, 1, 1, 0)
        self.xt.XTestFakeButtonEvent(self.display, 1, 0, 0)
        self.x.XFlush(self.display)
        time.sleep(0.25)

    def pilot(self, seconds=100, capture=True):
        deadline = time.monotonic() + seconds
        boost = True
        seen = set()
        while time.monotonic() < deadline:
            state = self.state()
            if state["phase"] == "FINISHED":
                self.release()
                return state
            if state["phase"] == "PAUSED":
                self.focus()
                self.tap("Escape")
            self.key("w", True)
            force = -state["curvature"] * state["speed"] ** 2 * 0.065
            target_lane = 0
            for index in range(3):
                pad = state["length"] * (0.15 + index * 0.25)
                ahead = (pad - state["distance"]) % state["length"]
                if ahead < 65 or ahead > state["length"] - 4:
                    target_lane = -3.6 if index % 2 == 0 else 3.6
            steer = (
                (target_lane - state["lane"]) * 4 - state["lateralSpeed"] * 0.9 - force
            ) / 11
            self.key("a", steer < -0.12)
            self.key("d", steer > 0.12)
            if state["nitro"] < 5:
                boost = False
            if state["nitro"] > 35:
                boost = True
            self.key("Shift_L", boost)
            if capture and state["lap"] not in seen and state["time"] > 7:
                seen.add(state["lap"])
                self.screenshot(f"{state['circuit'].lower()}-lap-{state['lap']}")
                print(json.dumps(state), flush=True)
            time.sleep(0.05)
        self.release()
        return self.state()


def explore(driver):
    driver.screenshot("garage")
    driver.tap("Return")
    driver.key("w", True)
    driver.wait_phase("RACING")
    time.sleep(3)
    driver.screenshot("race-first")
    driver.tap("Escape")
    driver.release()
    driver.wait_phase("PAUSED")
    before = driver.state()
    time.sleep(0.5)
    after = driver.state()
    assert before["time"] == after["time"]
    assert before["distance"] == after["distance"]
    driver.screenshot("paused")
    print("Native input start, drive and pause passed:", json.dumps(after), flush=True)


def win(driver):
    if driver.state()["phase"] == "GARAGE":
        driver.resize(1280, 800)
        driver.click(200, 575)
    else:
        driver.tap("r")
    result = driver.pilot()
    driver.screenshot("victory")
    assert result["phase"] == "FINISHED", result
    assert result["position"] == 1, result
    assert result["lap"] == 3, result
    assert result["best"] is not None, result
    print("Native input victory:", json.dumps(result), flush=True)
    (OUTPUT / "victory.json").write_text(json.dumps(result, indent=2) + "\n")


def checks(driver):
    driver.wait_phase("GARAGE")
    driver.resize(960, 640)
    driver.screenshot("garage-960")
    for _ in range(3):
        driver.tap("Up")
    before = driver.state()["circuit"]
    driver.tap("Right")
    assert driver.state()["circuit"] != before
    if driver.state()["circuit"] != "CINDER":
        driver.tap("Right")
    driver.tap("Down")
    before = driver.state()["paint"]
    driver.tap("Right")
    assert driver.state()["paint"] != before
    driver.tap("Down")
    driver.tap("Right")
    before = driver.state()["muted"]
    driver.tap("m")
    assert driver.state()["muted"] != before
    before = driver.state()["reducedMotion"]
    driver.tap("n")
    assert driver.state()["reducedMotion"] != before
    driver.screenshot("cinder-garage-960")
    driver.resize(1280, 800)
    before = driver.state()["circuit"]
    driver.click(160, 260)
    assert driver.state()["circuit"] != before
    driver.click(160, 260)
    assert driver.state()["circuit"] == before
    driver.click(200, 575)
    driver.wait_phase("COUNTDOWN")
    driver.tap("Escape")
    driver.wait_phase("PAUSED")
    countdown = driver.state()["countdown"]
    time.sleep(0.4)
    assert countdown == driver.state()["countdown"]
    driver.tap("Escape")
    driver.key("w", True)
    driver.wait_phase("RACING")
    time.sleep(3)
    driver.key("a", True)
    driver.key("space", True)
    time.sleep(0.7)
    driver.screenshot("drift")
    driver.key("space", False)
    driver.key("a", False)
    time.sleep(0.3)
    assert driver.state()["driftBonuses"] > 0, driver.state()
    driver.key("d", True)
    time.sleep(3)
    driver.key("d", False)
    assert driver.state()["bumps"] > 0, driver.state()
    assert driver.state()["speed"] < 35, driver.state()
    driver.screenshot("barrier-recovery")
    driver.pilot(seconds=5, capture=False)
    assert abs(driver.state()["lane"]) < 6
    driver.key("c", True)
    time.sleep(0.3)
    driver.screenshot("rear-view")
    driver.key("c", False)
    driver.tap("Escape")
    driver.release()
    driver.wait_phase("PAUSED")
    driver.resize(960, 640)
    driver.screenshot("pause-960")
    driver.resize(1280, 800)
    driver.tap("Escape")
    driver.x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    driver.x.XDefaultRootWindow.restype = ctypes.c_ulong
    root = driver.x.XDefaultRootWindow(driver.display)
    driver.x.XSetInputFocus(driver.display, root, 2, 0)
    driver.x.XFlush(driver.display)
    driver.wait_phase("PAUSED")
    driver.focus()
    driver.tap("r")
    driver.wait_phase("COUNTDOWN")
    state = driver.state()
    assert state["time"] == 0 and state["bumps"] == 0 and state["nitro"] == 65, state
    driver.tap("F11")
    time.sleep(0.4)
    driver.screenshot("fullscreen")
    driver.tap("F11")
    result = driver.pilot()
    assert result["phase"] == "FINISHED", result
    assert result["position"] == 1, result
    assert result["pads"] > 0, result
    assert not result["saveError"], result
    driver.screenshot("cinder-victory")
    (OUTPUT / "native-checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "Native menus, drift, collision, pads, resize, fullscreen, focus, reset and Cinder victory passed:",
        json.dumps(result),
        flush=True,
    )


def loss(driver):
    driver.tap("r")
    driver.wait_phase("RACING")
    deadline = time.monotonic() + 110
    while driver.state()["time"] < 85 and time.monotonic() < deadline:
        time.sleep(0.3)
    assert driver.state()["time"] >= 85, driver.state()
    assert driver.state()["position"] == 6, driver.state()
    print(
        "Rivals crossed the line while player waited; now driving to a sixth-place finish.",
        flush=True,
    )
    result = driver.pilot()
    assert result["phase"] == "FINISHED" and result["position"] == 6, result
    driver.screenshot("sixth-place")
    (OUTPUT / "loss.json").write_text(json.dumps(result, indent=2) + "\n")
    driver.tap("r")
    driver.wait_phase("COUNTDOWN")
    assert driver.state()["time"] == 0 and driver.state()["distance"] == 0
    driver.tap("Escape")
    driver.tap("Down")
    driver.tap("Down")
    driver.tap("Return")
    driver.wait_phase("GARAGE")
    driver.screenshot("final-garage")
    print(
        "Native sixth-place finish, retry and return to garage passed:",
        json.dumps(result),
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=["explore", "win", "checks", "loss"])
    args = parser.parse_args()
    driver = Driver()
    try:
        globals()[args.scenario](driver)
    finally:
        driver.release()


if __name__ == "__main__":
    main()
