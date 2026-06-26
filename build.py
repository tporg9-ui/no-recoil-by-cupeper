"""Build a portable single-file executable with PyInstaller.

Run this on the target OS (Windows for the festival PCs):

    pip install -r requirements.txt pyinstaller
    python build.py

The result is dist/RecoilControlStudio(.exe) — copy it onto the flash
drive. Profiles are written to recoil_profiles.json next to the
executable, so they travel with it.
"""

import PyInstaller.__main__

APP_NAME = "RecoilControlStudio"


def main() -> None:
    PyInstaller.__main__.run(
        [
            "main.py",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--windowed",
            # Request elevation: games usually run as administrator, and
            # Windows (UIPI) blocks injected input from a lower-integrity
            # process, so without this the mouse won't move in-game.
            "--uac-admin",
            f"--name={APP_NAME}",
        ]
    )


if __name__ == "__main__":
    main()
