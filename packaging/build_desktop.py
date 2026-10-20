"""Builds a standalone desktop executable with PyInstaller.

Run this ON the OS you want an executable for -- PyInstaller bundles the
interpreter and native libraries for the machine it runs on, it doesn't
cross-compile. So a Windows .exe needs to be built on Windows, a macOS
.app needs to be built on a Mac, and a Linux binary needs to be built on
Linux. There's no way around that from a single machine; this script is
what each of those machines runs.

Usage (from the repository root, with requirements.txt installed):

    pip install pyinstaller
    python packaging/build_desktop.py

The result lands in dist/Kobito (or dist/Kobito.exe on Windows, or
dist/Kobito.app on macOS) -- copy that one file/folder anywhere and run
it; no Python install or `pip install` needed on the machine that runs it.

AI hints need nothing extra in the bundle (they use plain HTTPS from the
standard library): set ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY or
KOBITO_AI_URL before running the app.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_SEP = ";" if sys.platform == "win32" else ":"

if __name__ == "__main__":
    subprocess.run(
        [
            sys.executable, "-m", "PyInstaller",
            "--name", "Kobito",
            "--onefile",
            "--noconfirm",
            "--add-data", f"assets{DATA_SEP}assets",
            os.path.join(ROOT, "main.py"),
        ],
        cwd=ROOT,
        check=True,
    )
