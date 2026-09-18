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

`anthropic` (and its dependency chain, including `cryptography`) is
deliberately excluded from the bundle -- kobito/hint_service.py already
falls back to a local hint whenever that import fails, so the game plays
identically either way, and skipping it sidesteps a `cryptography`
build-time crash PyInstaller hits on some platforms. If you want the
Claude-generated hints in your own build, drop the three
--exclude-module lines below and set ANTHROPIC_API_KEY before running
the built executable.
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
            "--exclude-module", "anthropic",
            "--exclude-module", "cryptography",
            "--exclude-module", "httpx",
            "--exclude-module", "httpcore",
            os.path.join(ROOT, "main.py"),
        ],
        cwd=ROOT,
        check=True,
    )
