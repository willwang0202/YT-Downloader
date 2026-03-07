#!/usr/bin/env python3
"""
YT-Downloader — Single runnable release file.
Run:  python YT-Downloader.py   (opens web UI in browser)
      python YT-Downloader.py --gui
      python YT-Downloader.py --gui
      python YT-Downloader.py "https://youtube.com/watch?v=..."
First run creates .venv and installs dependencies next to this file.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from typing import Callable
from urllib.parse import quote
from urllib.request import Request, urlopen

# -----------------------------------------------------------------------------
# Bootstrap: ensure we run with venv that has yt-dlp, fastapi, etc.
# -----------------------------------------------------------------------------
def _bootstrap() -> None:
    try:
        import yt_dlp  # noqa: F401
        import fastapi  # noqa: F401
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
        pip = venv_dir / "Scripts" / "pip.exe"
        python = venv_dir / "Scripts" / "python.exe"
    else:
        pip = venv_dir / "bin" / "pip"
        python = venv_dir / "bin" / "python"
    if not python.exists():
        print("Virtual environment incomplete. Remove .venv and run again.", file=sys.stderr)
        sys.exit(1)
    print("Installing dependencies...")
    subprocess.check_call([
        str(pip), "install", "-q",
        "yt-dlp", "certifi", "fastapi", "uvicorn[standard]", "pydantic",
    ])
    os.execv(str(python), [str(python), __file__] + sys.argv[1:])


if __name__ == "__main__":
    _bootstrap()

# -----------------------------------------------------------------------------
# Imports (after bootstrap we have venv)
# -----------------------------------------------------------------------------
import yt_dlp
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, field_validator

# -----------------------------------------------------------------------------
# Version & GitHub update check
# -----------------------------------------------------------------------------
__version__ = "2.1.2"
GITHUB_REPO = "willwang0202/YT-Downloader"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"
_version_cached: dict | None = None

def _parse_version(s: str) -> tuple[int, ...]:
    s = re.sub(r"^v", "", str(s).strip())
    parts = re.split(r"[.-]", s)
    return tuple(int(p) if p.isdigit() else 0 for p in parts[:4])

def _check_github_update() -> dict:
    global _version_cached
    result = {"current": __version__, "latest": None, "update_available": False, "release_url": RELEASE_URL}
    try:
        req = Request(GITHUB_API_LATEST, headers={"Accept": "application/json"})
        ctx = ssl.create_default_context()
        with urlopen(req, timeout=5, context=ctx) as resp:
            data = json.loads(resp.read().decode())
        tag = (data.get("tag_name") or "").strip()
        latest = re.sub(r"^v", "", tag)
        if latest:
            result["latest"] = latest
            result["update_available"] = _parse_version(latest) > _parse_version(__version__)
            _version_cached = result
    except Exception:
        if _version_cached is not None:
            return _version_cached
    return result

def _print_update_if_available() -> None:
    def _run() -> None:
        try:
            r = _check_github_update()
            if r.get("update_available") and r.get("latest"):
                print(f"Update available: v{r['latest']} — {RELEASE_URL}")
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()

# -----------------------------------------------------------------------------
# Formats & yt-dlp
# -----------------------------------------------------------------------------
VIDEO_FORMATS = ("mp4", "mov", "webm", "mkv")
AUDIO_FORMATS = ("mp3", "wav", "m4a", "aac", "ogg", "flac")
ALL_FORMATS = VIDEO_FORMATS + AUDIO_FORMATS

def get_ydl_opts(format_key: str, out_dir: str | Path, single: bool) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_only = format_key in AUDIO_FORMATS
    opts = {
        "outtmpl": str(out_dir / "%(title)s [%(id)s].%(ext)s"),
        "noplaylist": single,
        "quiet": False,
        "no_warnings": False,
        "extractor_args": {"youtube": {"player_client": ["android_testsuite"]}},
    }
    if audio_only:
        opts["format"] = "bestaudio/best"
        codec = "vorbis" if format_key == "ogg" else format_key
        pp = {"key": "FFmpegExtractAudio", "preferredcodec": codec}
        if format_key == "mp3":
            pp["preferredquality"] = "192"
        elif format_key in ("wav", "flac"):
            pp["preferredquality"] = None
        opts["postprocessors"] = [pp]
    else:
        opts["format"] = "bv*+ba/b"
        opts["merge_output_format"] = format_key
    return opts

def download(url: str, format_key: str = "mp4", playlist: bool = False,
             output_dir: str | Path | None = None, progress_hook: Callable | None = None) -> None:
    if format_key not in ALL_FORMATS:
        raise ValueError(f"format must be one of: {', '.join(ALL_FORMATS)}")
    out_dir = Path(output_dir or os.getcwd()).resolve()
    opts = get_ydl_opts(format_key, out_dir, not playlist)
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

# -----------------------------------------------------------------------------
# Embedded web UI (HTML, CSS, JS)
# -----------------------------------------------------------------------------
WEB_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>YT Downloader</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600&family=Outfit:wght@400;500;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="/styles.css" />
</head>
<body>
  <div class="noise" aria-hidden="true"></div>
  <main class="wrap">
    <header class="header">
      <h1 class="title">YT Downloader</h1>
      <p class="tagline">Paste a link. Pick a format. Download. (Local only.)</p>
    </header>
    <form class="form" id="form" novalidate>
      <div class="field">
        <label class="label" for="url">URL</label>
        <input type="text" id="url" name="url" class="input" placeholder="https://youtube.com/watch?v=…" required autocomplete="off" />
        <span class="input-focus"></span>
      </div>
      <div class="field">
        <label class="label" for="format">Format</label>
        <select id="format" name="format" class="input input-select">
          <optgroup label="Video"><option value="mp4">MP4</option><option value="mov">MOV</option><option value="webm">WebM</option><option value="mkv">MKV</option></optgroup>
          <optgroup label="Audio"><option value="mp3">MP3</option><option value="wav">WAV</option><option value="m4a">M4A</option><option value="aac">AAC</option><option value="ogg">OGG</option><option value="flac">FLAC</option></optgroup>
        </select>
        <span class="input-focus"></span>
      </div>
      <div class="field playlist-field">
        <label class="toggle-wrap">
          <input type="checkbox" id="playlist" name="playlist" class="toggle" />
          <span class="toggle-track"></span>
          <span class="toggle-label">Download full playlist</span>
        </label>
        <p class="hint">When unchecked, only the single video is downloaded.</p>
      </div>
      <div class="actions">
        <button type="submit" class="btn btn-primary" id="submit" disabled><span class="btn-text">Download</span><span class="btn-loader" aria-hidden="true"></span></button>
      </div>
      <div class="message" id="message" role="alert" hidden></div>
    </form>
    <footer class="footer">
      <p>Runs locally. Uses yt-dlp. For personal use only.</p>
      <p class="version" id="version"></p>
    </footer>
  </main>
  <script src="/app.js"></script>
</body>
</html>
"""

WEB_CSS = """:root{--bg:#f8f5f0;--surface:#ebe5dc;--border:rgba(61,54,48,0.14);--text:#3d3630;--text-muted:#7a6f65;--accent:#b86f50;--accent-hover:#a35f42;--accent-subtle:rgba(184,111,80,0.18);--error:#b84a3a;--error-bg:rgba(184,74,58,0.12);--success:#5a7d5a;--radius:12px;--radius-sm:8px;--font-sans:"DM Sans",system-ui,sans-serif;--font-display:"Outfit",system-ui,sans-serif;--transition:0.25s cubic-bezier(0.4,0,0.2,1);}
*,*::before,*::after{box-sizing:border-box;}body{margin:0;min-height:100vh;font-family:var(--font-sans);color:var(--text);background:var(--bg);line-height:1.5;-webkit-font-smoothing:antialiased;}
.noise{position:fixed;inset:0;pointer-events:none;z-index:0;opacity:0.04;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");}
.wrap{position:relative;z-index:1;max-width:480px;margin:0 auto;padding:clamp(2rem,6vw,4rem) 1.5rem;animation:fadeUp 0.6s var(--transition) both;}
@keyframes fadeUp{from{opacity:0;transform:translateY(16px);}to{opacity:1;transform:translateY(0);}}
.header{text-align:center;margin-bottom:2.5rem;}.title{font-family:var(--font-display);font-weight:600;font-size:clamp(1.75rem,4vw,2rem);letter-spacing:-0.02em;margin:0 0 0.35em;background:linear-gradient(135deg,var(--text) 0%,var(--accent) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.tagline{margin:0;font-size:0.95rem;color:var(--text-muted);}
.update-banner{display:flex;align-items:center;justify-content:space-between;gap:0.75rem;margin-bottom:1rem;padding:0.6rem 1rem;font-size:0.85rem;background:var(--accent-subtle);border:1px solid var(--accent);border-radius:var(--radius-sm);}
.update-banner a{color:var(--accent);font-weight:500;text-decoration:none;}.update-banner a:hover{text-decoration:underline;}
.update-banner-dismiss{background:none;border:none;font-size:1.25rem;line-height:1;color:var(--text-muted);cursor:pointer;padding:0 0.25rem;}.update-banner-dismiss:hover{color:var(--text);}
.footer{margin-top:3rem;padding-top:1.5rem;border-top:1px solid var(--border);text-align:center;}.footer p{margin:0;font-size:0.8rem;color:var(--text-muted);}.footer .version{margin-top:0.35rem;font-size:0.75rem;opacity:0.7;}
.form{display:flex;flex-direction:column;gap:1.5rem;}.field{display:flex;flex-direction:column;gap:0.5rem;}.label{font-size:0.8rem;font-weight:500;color:var(--text-muted);}
.input{width:100%;padding:0.9rem 1rem;font:inherit;font-size:0.95rem;color:var(--text);background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);transition:border-color 0.15s,box-shadow 0.15s;}
.input:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-subtle);}.field{position:relative;}
.input-focus{position:absolute;left:0;bottom:0;width:100%;height:2px;background:var(--accent);transform:scaleX(0);transform-origin:center;border-radius:0 0 var(--radius-sm) var(--radius-sm);transition:transform var(--transition);}.field:focus-within .input-focus{transform:scaleX(1);}
.input-select{cursor:pointer;appearance:none;padding-right:2.25rem;}.playlist-field .hint{margin:0.35rem 0 0;font-size:0.8rem;color:var(--text-muted);}
.toggle-wrap{display:inline-flex;align-items:center;gap:0.75rem;cursor:pointer;}.toggle{display:none;}
.toggle-track{position:relative;width:44px;height:24px;background:var(--surface);border:1px solid var(--border);border-radius:999px;transition:background 0.15s,border-color 0.15s;}
.toggle-track::after{content:"";position:absolute;top:2px;left:2px;width:18px;height:18px;background:var(--text-muted);border-radius:50%;transition:transform var(--transition);}
.toggle:checked+.toggle-track{background:var(--accent-subtle);border-color:var(--accent);}.toggle:checked+.toggle-track::after{transform:translateX(20px);background:var(--accent);}.toggle-label{font-size:0.95rem;}
.actions{margin-top:0.25rem;}.btn{display:inline-flex;align-items:center;justify-content:center;gap:0.5rem;min-width:140px;padding:0.85rem 1.5rem;font:inherit;font-size:0.95rem;font-weight:500;border:none;border-radius:var(--radius-sm);cursor:pointer;transition:opacity 0.15s,transform 0.15s;}
.btn:disabled{cursor:not-allowed;opacity:0.6;}.btn-primary{width:100%;color:#fff;background:var(--accent);}.btn-primary:not(:disabled):hover{background:var(--accent-hover);}
.btn-loader{display:none;width:18px;height:18px;border:2px solid rgba(255,255,255,0.35);border-top-color:#fff;border-radius:50%;animation:spin 0.7s linear infinite;}
@keyframes spin{to{transform:rotate(360deg);}}.form.loading .btn-text{visibility:hidden;}.form.loading .btn-loader{display:block;position:absolute;}
.message{padding:0.75rem 1rem;font-size:0.875rem;border-radius:var(--radius-sm);}.message.error{color:var(--error);background:var(--error-bg);border:1px solid rgba(184,74,58,0.28);}
.message.success{color:var(--success);background:rgba(90,125,90,0.15);border:1px solid rgba(90,125,90,0.35);}
"""

WEB_JS = """(function(){
var form=document.getElementById("form"),urlInput=document.getElementById("url"),submitBtn=document.getElementById("submit"),messageEl=document.getElementById("message");
function setLoading(l){form.classList.toggle("loading",l);submitBtn.disabled=l;}
function showMessage(t,type){messageEl.textContent=t;messageEl.className="message "+(type||"info");messageEl.hidden=false;}
function hideMessage(){messageEl.hidden=true;messageEl.className="message";}
function setValidity(v){urlInput.setCustomValidity(v?"":" ");submitBtn.disabled=!v;}
urlInput.addEventListener("input",function(){setValidity(urlInput.value.trim().length>0);hideMessage();});
urlInput.addEventListener("paste",function(){setTimeout(function(){setValidity(urlInput.value.trim().length>0);},0);});
form.addEventListener("submit",function(e){
e.preventDefault();hideMessage();
var url=urlInput.value.trim();if(!url){showMessage("Please enter a URL.","error");return;}
var format=(document.getElementById("format")?.value||"mp4").toLowerCase(),playlist=document.getElementById("playlist").checked;
setLoading(true);
fetch("/api/download",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:url,format:format,playlist:playlist})})
.then(function(res){
if(!res.ok)return res.json().then(function(b){throw new Error(b.detail||res.statusText||"Download failed");}).catch(function(err){if(err.message)throw err;return res.text().then(function(t){throw new Error(t||"Download failed");});});
return res.blob().then(function(blob){return{blob:blob,res:res};});
})
.then(function(data){
var isZip=(data.blob.type||"").indexOf("zip")!==-1,disposition=isZip?"playlist.zip":null;
if(!disposition){var h=data.res.headers.get("Content-Disposition");if(h){var m=/filename\\*=UTF-8''([^;]+)/i.exec(h);if(m){try{disposition=decodeURIComponent(m[1].trim());}catch(e){}}if(!disposition){var m2=/filename="?([^";\\n]+)"?/i.exec(h);if(m2)disposition=m2[1].replace(/\\\\"/g,'"').trim();}}}
if(!disposition)disposition="download."+format;
var a=document.createElement("a");a.href=URL.createObjectURL(data.blob);a.download=disposition;a.click();URL.revokeObjectURL(a.href);showMessage("Download started.","success");
})
.catch(function(err){showMessage(err.message||"Something went wrong.","error");})
.finally(function(){setLoading(false);});
});
setValidity(urlInput.value.trim().length>0);
fetch("/api/version").then(function(r){return r.ok?r.json():null;}).then(function(d){
if(!d)return;var ve=document.getElementById("version");if(ve)ve.textContent="v"+d.current;
}).catch(function(){});
})();
"""

# -----------------------------------------------------------------------------
# FastAPI app (embedded web server)
# -----------------------------------------------------------------------------
def _safe_content_disposition(filename: str, default: str = "download") -> str:
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
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s)
    return s.strip(" .") or "download"

def _get_video_title(ydl: yt_dlp.YoutubeDL, url: str, single: bool) -> str | None:
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

app = FastAPI(title="YT-Downloader", version=__version__)

@app.get("/")
def _serve_index():
    return Response(content=WEB_HTML, media_type="text/html")

@app.get("/styles.css")
def _serve_css():
    return Response(content=WEB_CSS, media_type="text/css")

@app.get("/app.js")
def _serve_js():
    return Response(content=WEB_JS, media_type="application/javascript")

@app.get("/api/version")
def _api_version():
    return _check_github_update()

class DownloadRequest(BaseModel):
    url: str
    format: str
    playlist: bool = False
    @field_validator("url", mode="before")
    @classmethod
    def _url(cls, v): return str(v).strip() if v is not None else ""
    @field_validator("format", mode="before")
    @classmethod
    def _fmt(cls, v): return str(v).strip().lower() if v else "mp4"

@app.post("/api/download")
def _download_api(req: DownloadRequest):
    if req.format not in ALL_FORMATS:
        raise HTTPException(status_code=400, detail=f"format must be one of: {', '.join(ALL_FORMATS)}")
    with tempfile.TemporaryDirectory() as tmpdir:
        single = not req.playlist
        opts = get_ydl_opts(req.format, tmpdir, single)
        opts["quiet"] = True
        opts["no_warnings"] = True
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
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
            if title:
                safe_title = _sanitize_filename(title)[:200]
                ext = path.suffix.lstrip(".")
                download_name = f"{safe_title}.{ext}" if ext else path.name
            else:
                download_name = path.name
            return StreamingResponse(buf, media_type="application/octet-stream",
                headers={"Content-Disposition": _safe_content_disposition(download_name, "download")})
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in files:
                zf.write(p, p.name)
        buf.seek(0)
        return StreamingResponse(buf, media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=playlist.zip"})

def _run_server(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    import uvicorn
    url = f"http://{host}:{port}"

    def _open_browser() -> None:
        # Packaged .app on macOS: webbrowser.open() often fails; use macOS "open" command
        if sys.platform == "darwin" and getattr(sys, "frozen", False):
            try:
                subprocess.run(["open", url], check=False, timeout=5)
                return
            except Exception:
                pass
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass

    # Open browser after a short delay so the server is ready
    if open_browser:
        threading.Thread(target=lambda: (time.sleep(1.5), _open_browser()), daemon=True).start()

    print(f"Web UI: {url}")
    print("Press Ctrl+C to stop.")
    # Run server on the main thread (simpler and works both as script and as bundled app)
    uvicorn.run(app, host=host, port=port, log_level="warning")

# -----------------------------------------------------------------------------
# GUI (tkinter)
# -----------------------------------------------------------------------------
def _launch_gui(output_dir: str | Path | None = None) -> None:
    try:
        import tkinter as tk
        from tkinter import ttk, scrolledtext, messagebox, filedialog
    except ImportError as e:
        print("tkinter is not available. Use --web for the browser UI.", file=sys.stderr)
        sys.exit(1)
    root = tk.Tk()
    root.title("YT Downloader")
    root.minsize(420, 380)
    root.geometry("480x420")
    # Bring window to front (helps when launched from .app / double-click)
    root.attributes("-topmost", True)
    root.after(100, lambda: root.attributes("-topmost", False))
    out_dir_var = tk.StringVar(value=str(Path(output_dir or os.getcwd()).resolve()))
    ttk.Label(root, text="URL").pack(anchor="w", padx=12, pady=(12, 2))
    url_entry = ttk.Entry(root, width=60)
    url_entry.pack(fill="x", padx=12, pady=(0, 8))
    url_entry.focus()
    ttk.Label(root, text="Format").pack(anchor="w", padx=12, pady=(4, 2))
    format_var = tk.StringVar(value="mp4")
    ttk.Combobox(root, textvariable=format_var, values=list(ALL_FORMATS), state="readonly", width=12).pack(anchor="w", padx=12, pady=(0, 8))
    playlist_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(root, text="Download full playlist", variable=playlist_var).pack(anchor="w", padx=12, pady=4)
    ttk.Label(root, text="Save to folder").pack(anchor="w", padx=12, pady=(8, 2))
    out_frame = ttk.Frame(root)
    out_frame.pack(fill="x", padx=12, pady=(0, 8))
    ttk.Entry(out_frame, textvariable=out_dir_var, width=50).pack(side="left", fill="x", expand=True, padx=(0, 4))
    def choose_dir():
        d = filedialog.askdirectory(initialdir=out_dir_var.get() or None)
        if d:
            out_dir_var.set(d)
    ttk.Button(out_frame, text="Browse…", command=choose_dir).pack(side="right")
    ttk.Label(root, text="Log").pack(anchor="w", padx=12, pady=(8, 2))
    log = scrolledtext.ScrolledText(root, height=8, state="disabled", wrap="word", font=("Consolas", 9))
    log.pack(fill="both", expand=True, padx=12, pady=(0, 8))
    def log_msg(msg: str):
        log.config(state="normal")
        log.insert("end", msg + "\n")
        log.see("end")
        log.config(state="disabled")
    def do_download():
        url = (url_entry.get() or "").strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a URL.")
            return
        out_dir = (out_dir_var.get() or "").strip() or os.getcwd()
        format_key = format_var.get() or "mp4"
        if format_key not in ALL_FORMATS:
            format_key = "mp4"
        def run():
            try:
                log_msg(f"Downloading: {url} ({format_key})")
                def hook(d):
                    if d.get("status") == "finished":
                        log_msg(f"Finished: {d.get('filename', '')}")
                download(url=url, format_key=format_key, playlist=playlist_var.get(), output_dir=out_dir, progress_hook=hook)
                root.after(0, lambda: (log_msg("Done."), messagebox.showinfo("Done", "Download finished.")))
            except Exception as e:
                root.after(0, lambda: (log_msg(str(e)), messagebox.showerror("Error", str(e))))
        btn_dl.config(state="disabled")
        threading.Thread(target=run, daemon=True).start()
        root.after(500, lambda: btn_dl.config(state="normal"))
    btn_dl = ttk.Button(root, text="Download", command=do_download)
    btn_dl.pack(pady=8)
    root.update_idletasks()
    root.lift()
    root.focus_force()
    root.mainloop()

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def main_cli() -> None:
    parser = argparse.ArgumentParser(description="Download videos/audio with yt-dlp (local only).")
    parser.add_argument("url", nargs="?", help="Video or playlist URL")
    parser.add_argument("-f", "--format", choices=ALL_FORMATS, default="mp4", help="Output format")
    parser.add_argument("-p", "--playlist", action="store_true", help="Download full playlist")
    parser.add_argument("-o", "--output-dir", default=None, metavar="DIR", help="Output directory")
    parser.add_argument("--gui", action="store_true", help="Open desktop GUI")
    parser.add_argument("--web", action="store_true", help="Open web UI in browser")
    args = parser.parse_args()

    # No arguments (e.g. double-click .app/.exe) → open web UI
    if len(sys.argv) == 1:
        args.web = True

    if args.gui:
        _launch_gui(output_dir=args.output_dir)
        return
    if args.web:
        _run_server()
        return
    if not args.url or not args.url.strip():
        parser.error("Provide a URL, or use --web / --gui")
    url = args.url.strip()
    try:
        download(url=url, format_key=args.format, playlist=args.playlist, output_dir=args.output_dir)
        print("Done.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    _print_update_if_available()
    main_cli()
