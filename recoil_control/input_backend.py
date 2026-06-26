"""Platform input layer: relative mouse movement + global listeners.

Mouse movement uses the OS-native relative-move API on Windows (SendInput)
because games read raw relative motion. On other platforms (used for
development/testing) it falls back to pynput's relative move.

Button and hotkey listening is done with pynput, which is cross-platform.
"""

from __future__ import annotations

import sys
from typing import Callable

IS_WINDOWS = sys.platform.startswith("win")


class MouseMover:
    """Applies relative mouse movement in integer mouse counts."""

    def __init__(self) -> None:
        if IS_WINDOWS:
            self._move = self._build_windows_mover()
        else:
            self._move = self._build_pynput_mover()

    def move(self, dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        self._move(dx, dy)

    # -- Windows: SendInput with MOUSEEVENTF_MOVE (relative) ---------------
    def _build_windows_mover(self) -> Callable[[int, int], None]:
        import ctypes
        from ctypes import wintypes

        MOUSEEVENTF_MOVE = 0x0001
        INPUT_MOUSE = 0

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
            ]

        class _INPUTunion(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT)]

        class INPUT(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD), ("u", _INPUTunion)]

        send_input = ctypes.windll.user32.SendInput

        def move(dx: int, dy: int) -> None:
            mi = MOUSEINPUT(dx, dy, 0, MOUSEEVENTF_MOVE, 0, None)
            inp = INPUT(INPUT_MOUSE, _INPUTunion(mi=mi))
            send_input(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

        return move

    # -- Other platforms: pynput relative move ----------------------------
    def _build_pynput_mover(self) -> Callable[[int, int], None]:
        from pynput.mouse import Controller

        controller = Controller()

        def move(dx: int, dy: int) -> None:
            controller.move(dx, dy)

        return move


class InputListener:
    """Listens for mouse buttons and a single keyboard toggle hotkey.

    Callbacks are invoked from listener threads, so keep them light and
    thread-safe.
    """

    def __init__(
        self,
        on_left: Callable[[bool], None],
        on_right: Callable[[bool], None],
        on_hotkey: Callable[[], None],
    ) -> None:
        self._on_left = on_left
        self._on_right = on_right
        self._on_hotkey = on_hotkey
        self._hotkey = "f8"
        self._extra_hotkeys: dict[str, Callable[[], None]] = {}
        self._capture_callback: Callable[[str], None] | None = None
        self._mouse_listener = None
        self._keyboard_listener = None

    def set_hotkey(self, hotkey: str) -> None:
        self._hotkey = (hotkey or "").strip().lower()

    def set_extra_hotkeys(self, mapping: dict[str, Callable[[], None]]) -> None:
        """Map key strings (e.g. "1", "f2") to callbacks (e.g. switch profile)."""
        self._extra_hotkeys = {
            (k or "").strip().lower(): cb for k, cb in mapping.items() if (k or "").strip()
        }

    def capture_next_key(self, callback: Callable[[str], None]) -> None:
        """Intercept the next key press and report it as a string (one-shot)."""
        self._capture_callback = callback

    def cancel_capture(self) -> None:
        self._capture_callback = None

    def start(self) -> None:
        from pynput import mouse, keyboard

        def on_click(x, y, button, pressed):
            name = getattr(button, "name", "")
            if name == "left":
                self._on_left(pressed)
            elif name == "right":
                self._on_right(pressed)

        def on_press(key):
            name = self._key_to_str(key)
            if self._capture_callback is not None:
                cb = self._capture_callback
                self._capture_callback = None
                if name:
                    cb(name)
                return
            if name and name == self._hotkey:
                self._on_hotkey()
            elif name and name in self._extra_hotkeys:
                self._extra_hotkeys[name]()

        self._mouse_listener = mouse.Listener(on_click=on_click)
        self._keyboard_listener = keyboard.Listener(on_press=on_press)
        self._mouse_listener.start()
        self._keyboard_listener.start()

    @staticmethod
    def _key_to_str(key) -> str:
        try:
            from pynput import keyboard

            if isinstance(key, keyboard.Key):
                return key.name
            if isinstance(key, keyboard.KeyCode) and key.char is not None:
                return key.char.lower()
        except Exception:
            return ""
        return ""

    def stop(self) -> None:
        for listener in (self._mouse_listener, self._keyboard_listener):
            if listener is not None:
                try:
                    listener.stop()
                except Exception:
                    pass
        self._mouse_listener = None
        self._keyboard_listener = None
