# Recoil Control Studio

A desktop tool for building, visualizing and running **recoil-compensation
patterns** for mouse-driven aiming. It is built for macro-building events
where the macro itself is the product being judged on **configuration
flexibility, convenience and GUI** — everything lives in one portable app
that runs from a flash drive.

> Use only where input macros are permitted (e.g. the festival rules that
> explicitly allow them). Don't use this in online games whose terms of
> service or anti-cheat forbid input automation.

## Features

- **Weapon profiles** — unlimited named profiles, each with its own
  pattern and behaviour. Switch instantly from the sidebar.
- **Visual pattern editor** — click to add recoil points, drag to fine
  tune, right-click to delete; the cumulative aim path is drawn live on a
  grid with zoom.
- **Editable step table** — precise `dx`, `dy`, `delay (ms)` per shot,
  kept in sync with the canvas.
- **Flexible activation** — apply compensation while firing (LMB), while
  aiming (RMB), or only with both held (ADS + fire).
- **Per-profile + global sensitivity** multipliers, `loop` and
  `hold-last-step` modes.
- **Toggle hotkey** (default `F8`) to arm/disarm, plus `Esc` panic-off.
- **Animated preview** that walks the pattern without touching the mouse.
- **Portable JSON storage** — profiles save to `recoil_profiles.json`
  next to the executable; import/export individual profiles to share.

## Run from source

```bash
pip install -r requirements.txt
python main.py
```

On Windows the engine uses the native `SendInput` relative-move API. On
Linux/macOS it falls back to `pynput` (useful for development and trying
out the UI).

## Build a portable Windows .exe

Run on Windows (the festival PCs' OS):

```bat
build_windows.bat
```

or manually:

```bash
pip install -r requirements.txt pyinstaller
python build.py
```

The single-file `dist/RecoilControlStudio.exe` is what you copy to the
flash drive. It needs no installation; profiles travel alongside it.

## How it works

A background thread watches the configured fire condition (mouse buttons).
While the condition holds and the app is **armed**, it walks the active
profile's steps and applies relative mouse movement, scaled by the
per-profile and global sensitivity. Sub-pixel movement is accumulated so
small per-shot values are not lost to rounding. A single trigger produces
one pass through the pattern (unless *loop* or *hold-last-step* is set).
