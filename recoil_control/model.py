"""Data model: weapon profiles, recoil steps and application config.

Everything is plain dataclasses that serialize to/from JSON so profiles
are portable (they live next to the executable, not in the registry).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Activation modes decide *when* compensation is applied.
ACTIVATION_LMB = "lmb"            # while left mouse button is held (firing)
ACTIVATION_RMB = "rmb"            # while right mouse button is held (aiming)
ACTIVATION_LMB_AND_RMB = "lmb+rmb"  # only while both are held (ADS + fire)

ACTIVATION_MODES = (ACTIVATION_LMB, ACTIVATION_RMB, ACTIVATION_LMB_AND_RMB)

ACTIVATION_LABELS = {
    ACTIVATION_LMB: "While firing (LMB held)",
    ACTIVATION_RMB: "While aiming (RMB held)",
    ACTIVATION_LMB_AND_RMB: "ADS + fire (LMB + RMB held)",
}


@dataclass
class Step:
    """A single recoil-compensation move.

    dx/dy are mouse counts applied at this step. Positive dy moves the
    aim down (compensating for upward kick). delay_ms is the pause before
    the next step is applied.
    """

    dx: float = 0.0
    dy: float = 0.0
    delay_ms: int = 20

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Step":
        return cls(
            dx=float(data.get("dx", 0.0)),
            dy=float(data.get("dy", 0.0)),
            delay_ms=int(data.get("delay_ms", 20)),
        )


@dataclass
class Profile:
    """A named recoil pattern for one weapon plus its behaviour settings."""

    name: str = "New profile"
    weapon: str = ""
    steps: list[Step] = field(default_factory=list)
    sensitivity: float = 1.0
    activation: str = ACTIVATION_LMB
    loop: bool = False
    repeat_last: bool = False
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "weapon": self.weapon,
            "steps": [s.to_dict() for s in self.steps],
            "sensitivity": self.sensitivity,
            "activation": self.activation,
            "loop": self.loop,
            "repeat_last": self.repeat_last,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        activation = data.get("activation", ACTIVATION_LMB)
        if activation not in ACTIVATION_MODES:
            activation = ACTIVATION_LMB
        return cls(
            name=str(data.get("name", "New profile")),
            weapon=str(data.get("weapon", "")),
            steps=[Step.from_dict(s) for s in data.get("steps", [])],
            sensitivity=float(data.get("sensitivity", 1.0)),
            activation=activation,
            loop=bool(data.get("loop", False)),
            repeat_last=bool(data.get("repeat_last", False)),
            note=str(data.get("note", "")),
        )


@dataclass
class AppConfig:
    """Top-level, persisted application state."""

    profiles: list[Profile] = field(default_factory=list)
    active_index: int = 0
    master_enabled: bool = False
    toggle_hotkey: str = "f8"
    global_sensitivity: float = 1.0
    tick_ms: int = 8

    def active_profile(self) -> Profile | None:
        if 0 <= self.active_index < len(self.profiles):
            return self.profiles[self.active_index]
        return None

    def to_dict(self) -> dict:
        return {
            "profiles": [p.to_dict() for p in self.profiles],
            "active_index": self.active_index,
            "master_enabled": self.master_enabled,
            "toggle_hotkey": self.toggle_hotkey,
            "global_sensitivity": self.global_sensitivity,
            "tick_ms": self.tick_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        return cls(
            profiles=[Profile.from_dict(p) for p in data.get("profiles", [])],
            active_index=int(data.get("active_index", 0)),
            master_enabled=bool(data.get("master_enabled", False)),
            toggle_hotkey=str(data.get("toggle_hotkey", "f8")),
            global_sensitivity=float(data.get("global_sensitivity", 1.0)),
            tick_ms=int(data.get("tick_ms", 8)),
        )


def base_dir() -> Path:
    """Directory the app should read/write portable files from.

    When frozen by PyInstaller we use the folder of the executable so the
    config sits next to the .exe on the flash drive. In dev we use the
    project root.
    """

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    return base_dir() / "recoil_profiles.json"


def default_config() -> AppConfig:
    """A friendly starter config with one illustrative spray pattern."""

    demo_steps = [
        Step(0, 7, 30), Step(0, 8, 30), Step(-1, 9, 30), Step(-2, 9, 30),
        Step(-3, 8, 30), Step(-2, 7, 30), Step(2, 6, 30), Step(4, 6, 30),
        Step(5, 5, 30), Step(3, 4, 30), Step(-2, 4, 30), Step(-4, 3, 30),
    ]
    demo = Profile(
        name="Example rifle",
        weapon="Rifle",
        steps=demo_steps,
        sensitivity=1.0,
        activation=ACTIVATION_LMB,
        note="Sample pattern — edit or replace with your own.",
    )
    return AppConfig(profiles=[demo], active_index=0)


def load_config() -> AppConfig:
    path = config_path()
    if not path.exists():
        return default_config()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cfg = AppConfig.from_dict(data)
        if not cfg.profiles:
            cfg.profiles = default_config().profiles
            cfg.active_index = 0
        return cfg
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        return default_config()


def save_config(cfg: AppConfig) -> None:
    path = config_path()
    path.write_text(
        json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
