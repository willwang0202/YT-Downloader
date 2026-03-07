#!/usr/bin/env python3
"""
Local web server for YT-Downloader. Serves the web UI and /api/download.
Runs on 127.0.0.1 only — no external access.
"""
from __future__ import annotations

import io
import os
import re
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import quote

# Use certifi's CA bundle so HTTPS works on macOS (avoids CERTIFICATE_VERIFY_FAILED)
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, field_validator

import yt_dlp

from yt_downloader import ALL_FORMATS, get_ydl_opts

try:
    from version import __version__, check_github_update_cached
except ImportError:
    __version__ = "2.1.0"
    def check_github_update_cached():
        return {"current": __version__, "latest": None, "update_available": False, "release_url": ""}

app = FastAPI(title="YT-Downloader", version=__version__)

WEB_DIR = Path(__file__).resolve().parent / "web"


def _safe_content_disposition(filename: str, default: str = "download") -> str:
    """Build Content-Disposition header value safe for HTTP (latin-1). Uses RFC 5987 for Unicode."""
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')
    try:
        filename.encode("ascii")
        return f'attachment; filename="{esc(filename)}"'
    except UnicodeEncodeError:
        ascii_fallback = re.sub(r"[^\x00-\x7f]+", "_", filename) or default
        encoded = quote(filename, safe="")
        return f"attachment; filename=\"{esc(ascii_fallback)}\"; filename*=UTF-8''{encoded}"


def _sanitize_filename(s: str) -> str:
    """Remove characters that are invalid in filenames (Windows + Unix)."""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s)
    return s.strip(" .") or "download"


def _get_video_title(ydl: yt_dlp.YoutubeDL, url: str, single: bool) -> str | None:
    """Fetch video title without downloading. Returns None for playlists when single=False."""
    try:
        info = ydl.extract_info(url, download=False, process=False)
        if not info:
            return None
        if single and "entries" in info and info["entries"]:
            entry = info["entries"][0]
            return entry.get("title") if isinstance(entry, dict) else getattr(entry, "title", None)
        return info.get("title") if isinstance(info, dict) else getattr(info, "title", None)
    except Exception:
        return None


@app.get("/")
def serve_index():
    if not WEB_DIR.exists():
        return {"service": "YT-Downloader", "message": "Web UI not found. Run from project root."}
    return FileResponse(WEB_DIR / "index.html")


@app.get("/styles.css")
def serve_css():
    if not WEB_DIR.exists():
        raise HTTPException(404)
    return FileResponse(WEB_DIR / "styles.css", media_type="text/css")


@app.get("/app.js")
def serve_js():
    if not WEB_DIR.exists():
        raise HTTPException(404)
    return FileResponse(WEB_DIR / "app.js", media_type="application/javascript")


@app.get("/api/version")
def api_version():
    """Return current version and whether a newer release is available on GitHub."""
    return check_github_update_cached()


class DownloadRequest(BaseModel):
    url: str  # any string; validated only as non-empty after strip
    format: str
    playlist: bool = False

    @field_validator("url", mode="before")
    @classmethod
    def url_accept_any(cls, v) -> str:
        return str(v).strip() if v is not None else ""

    @field_validator("format", mode="before")
    @classmethod
    def format_lower(cls, v) -> str:
        return str(v).strip().lower() if v else "mp4"


@app.post("/api/download")
def download_api(req: DownloadRequest):
    if req.format not in ALL_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"format must be one of: {', '.join(ALL_FORMATS)}",
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        single = not req.playlist
        opts = get_ydl_opts(req.format, tmpdir, single)
        opts["quiet"] = True
        opts["no_warnings"] = True
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                # Fetch video title first (single-video only) so we can use it as the download filename
                title = _get_video_title(ydl, req.url, single) if single else None
                ydl.download([req.url])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")

        files = list(Path(tmpdir).iterdir())
        if not files:
            raise HTTPException(status_code=404, detail="No media found for this URL")

        if len(files) == 1:
            path = files[0]
            data = path.read_bytes()
            buf = io.BytesIO(data)
            # Use fetched title as filename when available, else fall back to actual file name
            if title:
                safe_title = _sanitize_filename(title)[:200]
                ext = path.suffix.lstrip(".")
                download_name = f"{safe_title}.{ext}" if ext else path.name
            else:
                download_name = path.name
            return StreamingResponse(
                buf,
                media_type="application/octet-stream",
                headers={"Content-Disposition": _safe_content_disposition(download_name, "download")},
            )

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in files:
                zf.write(path, path.name)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=playlist.zip"},
        )


def run_server(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    import webbrowser
    import uvicorn

    url = f"http://{host}:{port}"
    if open_browser:
        webbrowser.open(url)
    print(f"Web UI: {url}")
    print("Press Ctrl+C to stop.")
    uvicorn.run(app, host=host, port=port, log_level="warning")
