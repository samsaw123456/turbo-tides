"""Drive the native Linux window with real X11 key events, using opt-in telemetry.

Launch with --telemetry /tmp/turbo-tides-playtest.json first. No game state is
modified by this script. Requires XTest/libX11 and xwininfo; frame captures use
Pillow or ImageMagick.
"""

import argparse
import ctypes
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(os.environ.get("TURBO_TEST_OUTPUT", ROOT / "build/playtest"))
TELEMETRY = Path(
    os.environ.get("TURBO_TEST_TELEMETRY", "/tmp/turbo-tides-playtest.json")
)


class PointerEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("serial", ctypes.c_ulong),
        ("send_event", ctypes.c_int),
        ("display", ctypes.c_void_p),
        ("window", ctypes.c_ulong),
        ("root", ctypes.c_ulong),
        ("subwindow", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("x_root", ctypes.c_int),
        ("y_root", ctypes.c_int),
        ("state", ctypes.c_uint),
        ("button", ctypes.c_uint),
        ("same_screen", ctypes.c_int),
    ]


class NativeEvent(ctypes.Union):
    # XEvent is padded to 24 native longs on X11.
    _fields_ = [("pointer", PointerEvent), ("pad", ctypes.c_long * 24)]


class XImage(ctypes.Structure):
    _fields_ = [
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("xoffset", ctypes.c_int),
        ("format", ctypes.c_int),
        ("data", ctypes.c_void_p),
        ("byte_order", ctypes.c_int),
        ("bitmap_unit", ctypes.c_int),
        ("bitmap_bit_order", ctypes.c_int),
        ("bitmap_pad", ctypes.c_int),
        ("depth", ctypes.c_int),
        ("bytes_per_line", ctypes.c_int),
        ("bits_per_pixel", ctypes.c_int),
        ("red_mask", ctypes.c_ulong),
        ("green_mask", ctypes.c_ulong),
        ("blue_mask", ctypes.c_ulong),
    ]


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
        self.x.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.x.XQueryKeymap.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        self.x.XDefaultRootWindow.restype = ctypes.c_ulong
        self.x.XSendEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_long,
            ctypes.POINTER(NativeEvent),
        ]
        self.native_pointer = os.environ.get("TURBO_TEST_NATIVE_POINTER") == "1"
        self.x.XWarpPointer.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_int,
        ]
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
        # LWJGL maps the window before loading assets and publishing its first
        # diagnostic frame. Wait for that frame before sending menu input.
        self.state()
        self.settle()

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
        if down:
            # Even a late delivery after an acknowledgement timeout needs cleanup.
            self.held.add(name)
        # Wait until each injected edge reaches X11 before issuing the next one.
        # Deferred XTest requests can be dropped when a short-lived driver exits.
        self.xt.XTestFakeKeyEvent(self.display, code, int(down), 0)
        self.x.XSync(self.display, False)
        deadline = time.monotonic() + 2
        keymap = ctypes.create_string_buffer(32)
        while True:
            self.x.XQueryKeymap(self.display, keymap)
            native_down = bool(keymap.raw[code // 8] & (1 << (code % 8)))
            if native_down == down:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    f"X11 did not acknowledge {name} {'press' if down else 'release'}"
                )
            time.sleep(0.005)
        time.sleep(0.005)
        if not down:
            self.held.discard(name)

    def tap(self, name):
        self.key(name, True)
        time.sleep(0.12)
        self.key(name, False)
        self.settle()

    def settle(self):
        # Wait for the native input/render loop and diagnostic writer, including
        # slow software-rendered frames. A fixed sleep can read the old scene.
        deadline = time.monotonic() + 8
        for _ in range(3):
            stamp = TELEMETRY.stat().st_mtime_ns
            while TELEMETRY.stat().st_mtime_ns == stamp:
                if time.monotonic() > deadline:
                    raise RuntimeError("The game stopped publishing frames")
                time.sleep(0.03)

    def release(self):
        errors = []
        for key in list(self.held):
            try:
                self.key(key, False)
            except RuntimeError as error:
                errors.append(str(error))
        if errors:
            raise RuntimeError("Could not release injected keys: " + "; ".join(errors))

    def state(self):
        for _ in range(100):
            try:
                if time.time() - TELEMETRY.stat().st_mtime < 4:
                    return json.loads(TELEMETRY.read_text())
            except (OSError, json.JSONDecodeError):
                pass
            time.sleep(0.1)
        raise RuntimeError("No fresh telemetry from the game; it may have exited")

    def wait_phase(self, phase, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.state()["phase"] == phase:
                return
            time.sleep(0.08)
        raise AssertionError(f"Expected {phase}, got {self.state()}")

    def screenshot(self, name):
        # Telemetry is written before the native buffer swap; let the displayed
        # frame catch up before capturing a just-finished race or changed menu.
        time.sleep(max(0.1, min(0.5, 1 / max(1, self.state()["fps"]))))
        try:
            from PIL import Image
        except ImportError:
            Image = None
        if Image is not None:
            info = subprocess.check_output(
                ["xwininfo", "-id", hex(self.window)], text=True
            )
            width = int(re.search(r"Width:\s+(\d+)", info)[1])
            height = int(re.search(r"Height:\s+(\d+)", info)[1])
            self.x.XGetImage.argtypes = [
                ctypes.c_void_p,
                ctypes.c_ulong,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_uint,
                ctypes.c_uint,
                ctypes.c_ulong,
                ctypes.c_int,
            ]
            self.x.XGetImage.restype = ctypes.POINTER(XImage)
            self.x.XDestroyImage.argtypes = [ctypes.POINTER(XImage)]
            native = self.x.XGetImage(
                self.display,
                self.window,
                0,
                0,
                width,
                height,
                ctypes.c_ulong(-1).value,
                2,
            )
            if native:
                try:
                    pixels = native.contents
                    if (
                        pixels.bits_per_pixel == 32
                        and pixels.byte_order == 0
                        and pixels.red_mask == 0xFF0000
                    ):
                        data = ctypes.string_at(
                            pixels.data, pixels.bytes_per_line * height
                        )
                        Image.frombytes(
                            "RGB",
                            (width, height),
                            data,
                            "raw",
                            "BGRX",
                            pixels.bytes_per_line,
                        ).save(
                            OUTPUT / f"{name}.png",
                            compress_level=1,
                        )
                        return
                finally:
                    self.x.XDestroyImage(native)
        subprocess.run(
            ["import", "-window", hex(self.window), str(OUTPUT / f"{name}.png")],
            check=True,
        )

    def resize(self, width, height):
        self.x.XResizeWindow(self.display, self.window, width, height)
        self.x.XFlush(self.display)
        time.sleep(0.4)

    def window_bounds(self):
        """Read the actual client rectangle, independently of game telemetry."""
        info = subprocess.check_output(["xwininfo", "-id", hex(self.window)], text=True)
        labels = ("Absolute upper-left X", "Absolute upper-left Y", "Width", "Height")
        return tuple(
            int(re.search(label + r":\s+(-?\d+)", info)[1]) for label in labels
        )

    def click(self, x, y, button=1):
        if self.native_pointer:
            self.pointer_event(6, x, y)  # MotionNotify, then press/hold/release.
            time.sleep(0.1)
            self.pointer_event(4, x, y, button)
            time.sleep(0.12)
            self.pointer_event(5, x, y, button)
            self.settle()
            return
        info = subprocess.check_output(["xwininfo", "-id", hex(self.window)], text=True)
        left = int(re.search(r"Absolute upper-left X:\s+(\d+)", info)[1])
        top = int(re.search(r"Absolute upper-left Y:\s+(\d+)", info)[1])
        self.xt.XTestFakeMotionEvent(self.display, -1, left + x, top + y, 0)
        self.xt.XTestFakeButtonEvent(self.display, button, 1, 0)
        self.xt.XTestFakeButtonEvent(self.display, button, 0, 0)
        self.x.XFlush(self.display)
        self.settle()

    def pointer_event(self, kind, x, y, button=0):
        """Deliver native window events when XWayland drops XTest pointer input."""
        info = subprocess.check_output(["xwininfo", "-id", hex(self.window)], text=True)
        left = int(re.search(r"Absolute upper-left X:\s+(-?\d+)", info)[1])
        top = int(re.search(r"Absolute upper-left Y:\s+(-?\d+)", info)[1])
        event = NativeEvent()
        p = event.pointer
        p.type, p.send_event = kind, 1
        p.display, p.window = self.display, self.window
        p.root = self.x.XDefaultRootWindow(self.display)
        p.x, p.y, p.x_root, p.y_root = x, y, left + x, top + y
        p.button, p.same_screen = button, 1
        if kind == 5:
            p.state = 1 << (button + 7)
        mask = {4: 1 << 2, 5: 1 << 3, 6: 1 << 6}[kind]
        if not self.x.XSendEvent(
            self.display, self.window, 0, mask, ctypes.byref(event)
        ):
            raise RuntimeError("Could not send native pointer input to the game window")
        self.x.XFlush(self.display)

    def ui_position(self, x, y):
        """Convert the game's 1280×800 layout into window coordinates."""
        info = subprocess.check_output(["xwininfo", "-id", hex(self.window)], text=True)
        width = int(re.search(r"Width:\s+(\d+)", info)[1])
        height = int(re.search(r"Height:\s+(\d+)", info)[1])
        scale = min(width / 1280, height / 800)
        return (
            round((width - 1280 * scale) / 2 + x * scale),
            round((height - 800 * scale) / 2 + y * scale),
        )

    def ui_click(self, x, y, button=1):
        self.click(*self.ui_position(x, y), button=button)

    def ui_hover(self, x, y):
        if self.native_pointer:
            self.pointer_event(6, *self.ui_position(x, y))
        else:
            self.x.XWarpPointer(
                self.display, 0, self.window, 0, 0, 0, 0, *self.ui_position(x, y)
            )
        self.x.XFlush(self.display)
        self.settle()

    def steer_toward(self, state, target_lane=0):
        steer = (
            (target_lane - state["lane"]) * 4
            - state["lateralSpeed"] * 0.9
            - state["cornerForce"]
        ) / 11
        self.key("a", steer < -0.12)
        self.key("d", steer > 0.12)

    def center_for(self, seconds):
        start = self.state()["time"]
        deadline = time.monotonic() + seconds * 5 + 8
        while self.state()["time"] < start + seconds:
            if time.monotonic() > deadline:
                raise AssertionError("Race stopped advancing during steering")
            self.steer_toward(self.state())
            time.sleep(0.03)
        self.key("a", False)
        self.key("d", False)

    def pilot(self, seconds=100, capture=True, capture_prefix=""):
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
            target_lane = 0
            for index in range(3):
                pad = state["length"] * (0.15 + index * 0.25)
                ahead = (pad - state["distance"]) % state["length"]
                if ahead < 65 or ahead > state["length"] - 4:
                    target_lane = -3.6 if index % 2 == 0 else 3.6
            self.steer_toward(state, target_lane)
            if state["nitro"] < 5:
                boost = False
            if state["nitro"] > 35:
                boost = True
            self.key("Shift_L", boost)
            if capture and state["lap"] not in seen and state["time"] > 7:
                seen.add(state["lap"])
                self.screenshot(
                    f"{capture_prefix}{state['circuit'].lower()}-lap-{state['lap']}"
                )
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
        driver.ui_click(180, 660)
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
    from city_playtest import mechanics, menu

    menu(driver)
    mechanics(driver)


def loss(driver):
    driver.resize(960, 640)
    if driver.state()["phase"] == "GARAGE":
        driver.ui_click(180, 660)
    else:
        driver.tap("r")
    driver.wait_phase("RACING")
    deadline = time.monotonic() + 250
    while driver.state()["time"] < 85 and time.monotonic() < deadline:
        time.sleep(0.3)
    assert driver.state()["time"] >= 85, driver.state()
    assert driver.state()["position"] == 6, driver.state()
    print(
        "Rivals crossed the line while player waited; now driving to a sixth-place finish.",
        flush=True,
    )
    result = driver.pilot(seconds=180, capture_prefix="loss-")
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
    driver.resize(1280, 800)
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
