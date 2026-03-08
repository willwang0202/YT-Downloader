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
import tempfile
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
        import faster_whisper  # noqa: F401
        import imageio_ffmpeg  # noqa: F401
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
        "yt-dlp", "certifi", "pywebview", "faster-whisper", "imageio-ffmpeg",
    ])
    os.execv(str(python), [str(python), __file__] + sys.argv[1:])


if __name__ == "__main__":
    _bootstrap()

# -----------------------------------------------------------------------------
# Imports (available after bootstrap)
# -----------------------------------------------------------------------------
import imageio_ffmpeg
import yt_dlp
from faster_whisper import WhisperModel
from faster_whisper.utils import download_model

try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    pass

import webview

# Bundled ffmpeg from imageio-ffmpeg; falls back to None (system ffmpeg) on failure
try:
    _FFMPEG_PATH: str | None = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    _FFMPEG_PATH = None

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
TRANSCRIBE_MODELS: dict[str, dict[str, object]] = {
    "tiny": {
        "label": "Tiny",
        "download_size_mb": 75,
        "disk_size_mb": 75,
        "description": "Fastest option with the lowest accuracy.",
    },
    "base": {
        "label": "Base",
        "download_size_mb": 145,
        "disk_size_mb": 145,
        "description": "Balanced speed and accuracy for most devices.",
    },
    "small": {
        "label": "Small",
        "download_size_mb": 465,
        "disk_size_mb": 465,
        "description": "Better accuracy, but slower on CPU.",
    },
    "medium": {
        "label": "Medium",
        "download_size_mb": 1530,
        "disk_size_mb": 1530,
        "description": "Most accurate here, but the largest and slowest.",
    },
}
DEFAULT_TRANSCRIBE_MODEL = "base"
TRANSCRIBE_OUTPUTS = ("txt", "srt")
TRANSCRIBE_FILE_TYPES = (
    "Audio / Video Files (*.mp3;*.wav;*.m4a;*.aac;*.ogg;*.flac;*.webm;*.mp4;*.mov;*.mkv;*.m4v)",
)
APP_STATE_DIR = Path.home() / ".yt-downloader"
MODEL_CACHE_DIR = APP_STATE_DIR / "models"
MODEL_REQUIRED_FILES = ("config.json", "model.bin", "tokenizer.json")


def _default_output_dir() -> Path:
    downloads = Path.home() / "Downloads"
    return downloads if downloads.exists() else Path.home()


def _slugify_filename(value: str, fallback: str = "transcript") -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', " ", (value or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(".")
    return cleaned or fallback


def _transcribe_model_path(model_name: str) -> Path:
    return MODEL_CACHE_DIR / model_name


def _is_transcribe_model_downloaded(model_name: str) -> bool:
    model_dir = _transcribe_model_path(model_name)
    return model_dir.exists() and all((model_dir / name).exists() for name in MODEL_REQUIRED_FILES)


def _list_transcribe_models() -> list[dict[str, object]]:
    models: list[dict[str, object]] = []
    for model_name, metadata in TRANSCRIBE_MODELS.items():
        item = dict(metadata)
        item["id"] = model_name
        item["installed"] = _is_transcribe_model_downloaded(model_name)
        models.append(item)
    return models


def _download_transcribe_model(model_name: str) -> Path:
    if model_name not in TRANSCRIBE_MODELS:
        raise ValueError(f"Invalid transcription model: {model_name}")
    model_dir = _transcribe_model_path(model_name)
    model_dir.mkdir(parents=True, exist_ok=True)
    download_model(model_name, output_dir=str(model_dir), cache_dir=str(MODEL_CACHE_DIR))
    return model_dir


def _format_srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(float(seconds) * 1000))
    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000
    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000
    secs = milliseconds // 1_000
    milliseconds -= secs * 1_000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def _write_transcript_files(segments: list[object], output_base: Path) -> list[Path]:
    txt_path = output_base.with_suffix(".txt")
    srt_path = output_base.with_suffix(".srt")

    txt_lines = [getattr(segment, "text", "").strip() for segment in segments]
    txt_path.write_text("\n".join(line for line in txt_lines if line), encoding="utf-8")

    srt_lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        text = getattr(segment, "text", "").strip()
        if not text:
            continue
        start = _format_srt_timestamp(getattr(segment, "start", 0.0))
        end = _format_srt_timestamp(getattr(segment, "end", 0.0))
        srt_lines.extend([str(index), f"{start} --> {end}", text, ""])
    srt_path.write_text("\n".join(srt_lines).strip() + "\n", encoding="utf-8")
    return [txt_path, srt_path]


def _download_youtube_audio(url: str, download_dir: Path) -> tuple[Path, str]:
    opts = {
        "outtmpl": str(download_dir / "%(title)s [%(id)s].%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "format": "bestaudio/best",
        "extractor_args": {"youtube": {"player_client": ["android_testsuite"]}},
    }
    if _FFMPEG_PATH:
        opts["ffmpeg_location"] = _FFMPEG_PATH
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info is None:
            raise RuntimeError("Unable to download audio from the provided URL.")
        requested = info.get("requested_downloads") or []
        file_path = requested[0].get("filepath") if requested else None
        if not file_path:
            file_path = ydl.prepare_filename(info)
        audio_path = Path(file_path)
        if not audio_path.exists():
            candidates = [path for path in download_dir.iterdir() if path.is_file()]
            if len(candidates) == 1:
                audio_path = candidates[0]
        if not audio_path.exists():
            raise RuntimeError("Downloaded audio file could not be located.")
        title = _slugify_filename(str(info.get("title") or audio_path.stem), fallback="youtube-transcript")
        return audio_path, title


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
    if _FFMPEG_PATH:
        opts["ffmpeg_location"] = _FFMPEG_PATH
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
        self._model_cache: dict[str, WhisperModel] = {}

    # ------------------------------------------------------------------
    def get_version(self) -> dict:
        """Return version info (cached; non-blocking after first call)."""
        return _check_github_update()

    # ------------------------------------------------------------------
    def get_app_state(self) -> dict:
        """Return frontend boot data for the local app."""
        return {
            "version": _check_github_update(),
            "default_output_dir": str(_default_output_dir()),
            "transcription": {
                "default_model": DEFAULT_TRANSCRIBE_MODEL,
                "outputs": list(TRANSCRIBE_OUTPUTS),
                "models": _list_transcribe_models(),
            },
        }

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
    def pick_audio_file(self) -> str | None:
        """Show a native file picker for audio/video sources."""
        if self._window is None:
            return None
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=TRANSCRIBE_FILE_TYPES,
        )
        if result and len(result) > 0:
            return result[0]
        return None

    # ------------------------------------------------------------------
    def download_transcription_model(self, model_name: str) -> dict:
        """Download a local faster-whisper model after user confirmation."""
        model_name = (model_name or DEFAULT_TRANSCRIBE_MODEL).strip().lower()
        try:
            model_path = _download_transcribe_model(model_name)
            return {
                "success": True,
                "model_name": model_name,
                "model_path": str(model_path),
                "models": _list_transcribe_models(),
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    def _get_transcribe_model(self, model_name: str) -> WhisperModel:
        model_name = (model_name or DEFAULT_TRANSCRIBE_MODEL).strip().lower()
        if model_name not in TRANSCRIBE_MODELS:
            raise ValueError(f"Invalid transcription model: {model_name}")
        if not _is_transcribe_model_downloaded(model_name):
            _download_transcribe_model(model_name)
        model = self._model_cache.get(model_name)
        if model is None:
            model = WhisperModel(
                str(_transcribe_model_path(model_name)),
                device="cpu",
                compute_type="int8",
            )
            self._model_cache[model_name] = model
        return model

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
    def transcribe(self, source_type: str, source_value: str, model_name: str, output_dir: str) -> dict:
        """
        Transcribe local audio/video files or YouTube audio into .txt and .srt files.
        Returns {"success": True, ...} or {"success": False, "error": msg}.
        """
        source_type = (source_type or "").strip().lower()
        source_value = (source_value or "").strip()
        model_name = (model_name or DEFAULT_TRANSCRIBE_MODEL).strip().lower()

        if source_type not in {"youtube", "file"}:
            return {"success": False, "error": "Invalid transcription source."}
        if not source_value:
            return {"success": False, "error": "Please choose a source to transcribe."}

        out_dir = Path(output_dir).resolve() if output_dir else _default_output_dir()
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            model = self._get_transcribe_model(model_name)
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
            }

        try:
            if source_type == "file":
                audio_path = Path(source_value).expanduser().resolve()
                if not audio_path.exists():
                    return {"success": False, "error": "The selected audio file could not be found."}
                base_name = _slugify_filename(audio_path.stem, fallback="audio-transcript")
                segments, info = model.transcribe(str(audio_path), vad_filter=True)
            else:
                with tempfile.TemporaryDirectory(prefix="yt-downloader-stt-") as temp_dir:
                    audio_path, base_name = _download_youtube_audio(source_value, Path(temp_dir))
                    segments, info = model.transcribe(str(audio_path), vad_filter=True)
                    segment_list = list(segments)
                output_base = out_dir / f"{base_name} transcript"
                files = _write_transcript_files(segment_list, output_base)
                return {
                    "success": True,
                    "output_dir": str(out_dir),
                    "files": [path.name for path in files],
                    "language": getattr(info, "language", None),
                }

            segment_list = list(segments)
            output_base = out_dir / f"{base_name} transcript"
            files = _write_transcript_files(segment_list, output_base)
            return {
                "success": True,
                "output_dir": str(out_dir),
                "files": [path.name for path in files],
                "language": getattr(info, "language", None),
            }
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
        height=860,
        min_size=(460, 680),
        resizable=True,
    )
    api._window = window

    # Pre-warm the GitHub update check so get_version() returns fast
    threading.Thread(target=_check_github_update, daemon=True).start()

    debug = "--debug" in sys.argv
    webview.start(debug=debug)


if __name__ == "__main__":
    main()
