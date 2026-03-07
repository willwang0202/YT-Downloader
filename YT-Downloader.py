#!/usr/bin/env python3
"""
YT-Downloader — pywebview desktop app.
Run:  python YT-Downloader.py
First run creates .venv and installs dependencies next to this file.
"""
from __future__ import annotations

import json
import os
import re
import ssl
import subprocess
import sys
import threading
from pathlib import Path
from urllib.request import Request, urlopen

# -----------------------------------------------------------------------------
# Bootstrap: ensure we run with a venv that has yt-dlp and pywebview
# -----------------------------------------------------------------------------
def _bootstrap() -> None:
    if getattr(sys, "frozen", False):
        return  # Running as a PyInstaller bundle; all deps are included
    try:
        import yt_dlp   # noqa: F401
        import webview  # noqa: F401
        return
    except ImportError:
        pass
    root = Path(__file__).resolve().parent
    os.chdir(root)
    venv_dir = root / ".venv"
    if not venv_dir.exists():
        print("Creating virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir)])
    if sys.platform == "win32":
        pip    = venv_dir / "Scripts" / "pip.exe"
        python = venv_dir / "Scripts" / "python.exe"
    else:
        pip    = venv_dir / "bin" / "pip"
        python = venv_dir / "bin" / "python"
    if not python.exists():
        print("Virtual environment incomplete. Remove .venv and run again.", file=sys.stderr)
        sys.exit(1)
    print("Installing dependencies...")
    subprocess.check_call([
        str(pip), "install", "-q",
        "yt-dlp", "certifi", "pywebview",
    ])
    os.execv(str(python), [str(python), __file__] + sys.argv[1:])


if __name__ == "__main__":
    _bootstrap()

# -----------------------------------------------------------------------------
# Imports (available after bootstrap)
# -----------------------------------------------------------------------------
import yt_dlp

try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    pass

import webview

# -----------------------------------------------------------------------------
# Version & GitHub update check
# -----------------------------------------------------------------------------
__version__ = "3.0.1"
GITHUB_REPO       = "willwang0202/YT-Downloader"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASE_URL       = f"https://github.com/{GITHUB_REPO}/releases/latest"
_version_cached: dict | None = None


def _parse_version(s: str) -> tuple[int, ...]:
    s = re.sub(r"^v", "", str(s).strip())
    parts = re.split(r"[.-]", s)
    return tuple(int(p) if p.isdigit() else 0 for p in parts[:4])


def _check_github_update() -> dict:
    global _version_cached
    result: dict = {
        "current": __version__,
        "latest": None,
        "update_available": False,
        "release_url": RELEASE_URL,
    }
    try:
        req = Request(GITHUB_API_LATEST, headers={"Accept": "application/json"})
        ctx = ssl.create_default_context()
        with urlopen(req, timeout=5, context=ctx) as resp:
            data = json.loads(resp.read().decode())
        tag    = (data.get("tag_name") or "").strip()
        latest = re.sub(r"^v", "", tag)
        if latest:
            result["latest"]           = latest
            result["update_available"] = _parse_version(latest) > _parse_version(__version__)
            _version_cached = result
    except Exception:
        if _version_cached is not None:
            return _version_cached
    return result

# -----------------------------------------------------------------------------
# Formats & yt-dlp helpers
# -----------------------------------------------------------------------------
VIDEO_FORMATS = ("mp4", "mov", "webm", "mkv")
AUDIO_FORMATS = ("mp3", "wav", "m4a", "aac", "ogg", "flac")
ALL_FORMATS   = VIDEO_FORMATS + AUDIO_FORMATS


def _get_ydl_opts(format_key: str, out_dir: Path, single: bool) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_only = format_key in AUDIO_FORMATS
    opts: dict = {
        "outtmpl":        str(out_dir / "%(title)s [%(id)s].%(ext)s"),
        "noplaylist":     single,
        "quiet":          False,
        "no_warnings":    False,
        "extractor_args": {"youtube": {"player_client": ["android_testsuite"]}},
    }
    if audio_only:
        opts["format"] = "bestaudio/best"
        codec = "vorbis" if format_key == "ogg" else format_key
        pp: dict = {"key": "FFmpegExtractAudio", "preferredcodec": codec}
        if format_key == "mp3":
            pp["preferredquality"] = "192"
        elif format_key in ("wav", "flac"):
            pp["preferredquality"] = None
        opts["postprocessors"] = [pp]
    else:
        opts["format"]               = "bv*+ba/b"
        opts["merge_output_format"]  = format_key
    return opts

# -----------------------------------------------------------------------------
# pywebview JS API
# -----------------------------------------------------------------------------
class Api:
    """Methods exposed to the webview frontend via window.pywebview.api.*"""

    def __init__(self) -> None:
        self._window: webview.Window | None = None

    # ------------------------------------------------------------------
    def get_version(self) -> dict:
        """Return version info (cached; non-blocking after first call)."""
        return _check_github_update()

    # ------------------------------------------------------------------
    def pick_folder(self) -> str | None:
        """Show a native folder picker; return the chosen path or None."""
        if self._window is None:
            return None
        result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            return result[0]
        return None

    # ------------------------------------------------------------------
    def download(self, url: str, format: str, playlist: bool, output_dir: str) -> dict:
        """
        Download a video/audio file with yt-dlp.
        Returns {"success": True, "output_dir": path} or {"success": False, "error": msg}.
        pywebview calls this on a worker thread, so the UI stays responsive.
        """
        url    = (url    or "").strip()
        format = (format or "mp4").strip().lower()

        if not url:
            return {"success": False, "error": "Please enter a URL."}
        if format not in ALL_FORMATS:
            return {"success": False, "error": f"Invalid format: {format}"}

        out_dir = Path(output_dir).resolve() if output_dir else Path.home() / "Downloads"
        opts    = _get_ydl_opts(format, out_dir, not playlist)

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return {"success": True, "output_dir": str(out_dir)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    def reveal_folder(self, path: str) -> None:
        """Open the output folder in Finder / Explorer / file manager."""
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            elif sys.platform == "win32":
                subprocess.run(["explorer", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception:
            pass

# -----------------------------------------------------------------------------
# macOS dock icon (script mode only; frozen .app gets icon from PyInstaller)
# -----------------------------------------------------------------------------
def _set_macos_icon(base: Path) -> None:
    if sys.platform != "darwin" or getattr(sys, "frozen", False):
        return
    try:
        from AppKit import NSApplication, NSImage  # type: ignore[import]
        icon_path = str(base / "Icon.png")
        if Path(icon_path).exists():
            NSApplication.sharedApplication().setApplicationIconImage_(
                NSImage.alloc().initByReferencingFile_(icon_path)
            )
    except Exception:
        pass

# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
def main() -> None:
    # When frozen by PyInstaller, resources live in sys._MEIPASS
    _base    = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    _web_dir = _base / "web"
    _html    = str(_web_dir / "index.html")

    _set_macos_icon(_base)

    api    = Api()
    window = webview.create_window(
        "YT Downloader",
        _html,
        js_api=api,
        width=560,
        height=740,
        min_size=(420, 580),
        resizable=True,
    )
    api._window = window

    # Pre-warm the GitHub update check so get_version() returns fast
    threading.Thread(target=_check_github_update, daemon=True).start()

    debug = "--debug" in sys.argv
    webview.start(debug=debug)


if __name__ == "__main__":
    main()
