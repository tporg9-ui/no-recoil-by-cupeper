@echo off
REM Build a portable Windows .exe. Run on Windows with Python 3.10+ installed.
setlocal

python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
python build.py

echo.
echo Done. Portable executable is in:  dist\RecoilControlStudio.exe
echo Copy it to your flash drive. Profiles are saved next to the .exe.
pause
