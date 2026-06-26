"""Recoil-compensation engine.

A background worker thread that, while the configured fire condition is
held, walks the active profile's pattern and applies relative mouse
movement to counter recoil. Movement is fraction-accumulated so small
per-step values aren't lost to integer rounding.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from .model import (
    ACTIVATION_LMB,
    ACTIVATION_RMB,
    ACTIVATION_LMB_AND_RMB,
    Profile,
)
from .input_backend import MouseMover


class RecoilEngine:
    def __init__(
        self,
        mover: Optional[MouseMover] = None,
        status_callback: Optional[Callable[[bool, int], None]] = None,
    ) -> None:
        self._mover = mover or MouseMover()
        self._status_callback = status_callback

        self._lock = threading.Lock()
        self._fire_event = threading.Event()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # State updated from the UI / listener threads.
        self._master_enabled = False
        self._global_sensitivity = 1.0
        self._active_profile: Optional[Profile] = None
        self._left_down = False
        self._right_down = False

    # -- lifecycle --------------------------------------------------------
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._fire_event.set()  # wake the worker so it can exit
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    # -- state setters (thread-safe) -------------------------------------
    def set_master_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._master_enabled = enabled
            self._recompute_locked()

    def set_global_sensitivity(self, value: float) -> None:
        with self._lock:
            self._global_sensitivity = max(0.01, float(value))

    def set_active_profile(self, profile: Optional[Profile]) -> None:
        with self._lock:
            self._active_profile = profile
            self._recompute_locked()

    def set_button(self, left: Optional[bool] = None, right: Optional[bool] = None) -> None:
        with self._lock:
            if left is not None:
                self._left_down = left
            if right is not None:
                self._right_down = right
            self._recompute_locked()

    @property
    def master_enabled(self) -> bool:
        return self._master_enabled

    # -- internals --------------------------------------------------------
    def _should_fire_locked(self) -> bool:
        if not self._master_enabled or self._active_profile is None:
            return False
        mode = self._active_profile.activation
        if mode == ACTIVATION_LMB:
            return self._left_down
        if mode == ACTIVATION_RMB:
            return self._right_down
        if mode == ACTIVATION_LMB_AND_RMB:
            return self._left_down and self._right_down
        return False

    def _recompute_locked(self) -> None:
        if self._should_fire_locked():
            self._fire_event.set()
        else:
            self._fire_event.clear()

    def _snapshot(self):
        with self._lock:
            profile = self._active_profile
            sens = self._global_sensitivity
            if profile is None:
                return None
            steps = [(s.dx, s.dy, s.delay_ms) for s in profile.steps]
            return (
                steps,
                profile.sensitivity * sens,
                profile.loop,
                profile.repeat_last,
            )

    def _emit(self, active: bool, step_index: int) -> None:
        if self._status_callback is not None:
            try:
                self._status_callback(active, step_index)
            except Exception:
                pass

    def _loop(self) -> None:
        while self._running:
            self._fire_event.wait()
            if not self._running:
                break
            self._run_pattern()
            # One trigger = one spray: wait for release before re-arming.
            while self._fire_event.is_set() and self._running:
                time.sleep(0.004)
            self._emit(False, -1)

    def _run_pattern(self) -> None:
        snap = self._snapshot()
        if snap is None:
            return
        steps, sens, loop, repeat_last = snap
        n = len(steps)
        if n == 0:
            return

        acc_x = 0.0
        acc_y = 0.0
        i = 0
        while self._fire_event.is_set() and self._running:
            if i >= n:
                if loop:
                    i = 0
                elif repeat_last:
                    i = n - 1
                else:
                    break
            dx, dy, delay_ms = steps[i]
            mx = dx * sens + acc_x
            my = dy * sens + acc_y
            imx = int(mx)
            imy = int(my)
            acc_x = mx - imx
            acc_y = my - imy
            self._mover.move(imx, imy)
            self._emit(True, i)
            time.sleep(max(0.0, delay_ms / 1000.0))
            if not repeat_last or i < n - 1:
                i += 1
