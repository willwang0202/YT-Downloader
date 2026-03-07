#!/usr/bin/env python3
"""
Single entry point for YT-Downloader on macOS and Windows.
Creates a venv and installs dependencies if needed, then runs the app.
Usage:
  python run.py
  python run.py --web
  python run.py --gui
  python run.py "https://youtube.com/watch?v=..."
  python run.py "https://..." -f mp3 --playlist
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

try:
    from version import print_update_if_available
except ImportError:
    def print_update_if_available() -> None:
        pass


def main() -> None:
    root = Path(__file__).resolve().parent
    os.chdir(root)

    venv_dir = root / ".venv"
    if not venv_dir.exists():
        print("Creating virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir)])

    if sys.platform == "win32":
        pip = venv_dir / "Scripts" / "pip.exe"
        python = venv_dir / "Scripts" / "python.exe"
    else:
        pip = venv_dir / "bin" / "pip"
        python = venv_dir / "bin" / "python"

    if not python.exists():
        print("Virtual environment incomplete. Remove .venv and run again.", file=sys.stderr)
        sys.exit(1)

    print("Installing dependencies...")
    subprocess.check_call([str(pip), "install", "-q", "-r", "requirements.txt"])

    # Check for new version on GitHub (non-blocking)
    print_update_if_available()

    args = [str(python), "yt_downloader.py"] + sys.argv[1:]
    # No arguments → open web UI by default
    if len(sys.argv) == 1:
        args.append("--web")
    if sys.platform == "win32":
        # On Windows, execv doesn't replace the process the same way; run and exit
        sys.exit(subprocess.call(args))
    os.execv(str(python), args)


if __name__ == "__main__":
    main()
