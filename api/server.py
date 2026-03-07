"""
YT-Downloader API — FastAPI backend using yt-dlp.
Deploy this (e.g. Railway, Render) and point the GitHub Pages frontend to it.
"""
import os
import tempfile
import zipfile
import io
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import yt_dlp

app = FastAPI(title="YT-Downloader API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend from parent dir when running locally (same-origin, no API URL needed)
_static_dir = Path(__file__).resolve().parent.parent
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=_static_dir, html=True), name="static")

    @app.get("/")
    def serve_root():
        return RedirectResponse(url="/static/")
else:

    @app.get("/")
    def root():
        return {"service": "YT-Downloader API", "docs": "/docs"}


class DownloadRequest(BaseModel):
    url: str
    format: str  # mov | mp4 | mp3 | wav
    playlist: bool = False


def get_ydl_opts(format_key: str, out_dir: str, single: bool) -> dict:
    """Build yt-dlp options for the chosen format and mode."""
    audio_only = format_key in ("mp3", "wav")
    opts = {
        "outtmpl": os.path.join(out_dir, "%(title).100s [%(id)s].%(ext)s"),
        "noplaylist": single,
        "quiet": True,
        "no_warnings": True,
    }

    if audio_only:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": format_key,
            "preferredquality": "192" if format_key == "mp3" else None,
        }]
        if format_key == "wav":
            opts["postprocessors"][0]["preferredquality"] = None
    else:
        opts["format"] = "bv*+ba/b"
        opts["merge_output_format"] = "mov" if format_key == "mov" else "mp4"

    return opts


@app.post("/api/download")
def download(req: DownloadRequest):
    if req.format not in ("mov", "mp4", "mp3", "wav"):
        raise HTTPException(status_code=400, detail="format must be mov, mp4, mp3, or wav")

    with tempfile.TemporaryDirectory() as tmpdir:
        single = not req.playlist
        opts = get_ydl_opts(req.format, tmpdir, single)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
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
            return StreamingResponse(
                buf,
                media_type="application/octet-stream",
                headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
