# Release description (copy into GitHub Release)

Use this as the **description** for a new release. Attach:
- **YT-Downloader.py** (single runnable file; any platform with Python 3.10+)
- **YT-Downloader.exe** (Windows standalone; build on Windows)
- **YT-Downloader.app** (macOS standalone; build on macOS)

---

## v2.1.0

**YT Downloader** — download videos and audio from YouTube and other sites. Runs **entirely on your machine**; no account, no cloud API. Uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) under the hood.

### What's in this release

- **Single-file Python script** — `YT-Downloader.py` works on Windows and macOS. First run installs dependencies into a local `.venv`; no admin rights needed.
- **Standalone executables** — **YT-Downloader.exe** (Windows) and **YT-Downloader.app** (macOS) so you can run without installing Python.
- **Web UI** — paste a URL, pick format (MP4, MP3, etc.), download. Opens in your browser at `http://127.0.0.1:8765`.
- **CLI & desktop GUI** — use from the terminal or the built-in tkinter window.
- **Proper filenames** — downloads are named after the video title (e.g. `My Video.mp3`).
- **Update check** — app checks GitHub for a newer version and shows a notice when one is available.

### How to run

| File | How to run |
|------|------------|
| **YT-Downloader.py** | Requires [Python 3.10+](https://www.python.org/downloads/). Double‑click or: `python YT-Downloader.py` |
| **YT-Downloader.exe** | No Python needed. Double‑click or run from a terminal. |
| **YT-Downloader.app** | No Python needed. Double‑click or run from Finder. |

With no arguments, the app opens the **web UI** in your browser. From a terminal you can also do:

```bash
# Web UI (default)
python YT-Downloader.py

# Download one video (MP4)
python YT-Downloader.py "https://youtube.com/watch?v=..."

# MP3, full playlist, or desktop GUI
python YT-Downloader.py "https://..." -f mp3 --playlist
python YT-Downloader.py --gui
```

**Formats:** MP4, MOV, WebM, MKV (video) · MP3, WAV, M4A, AAC, OGG, FLAC (audio).  
**FFmpeg** is optional but needed for MP3/WAV/FLAC; [download FFmpeg](https://ffmpeg.org/download.html) if you use those.

### Requirements

- **Python 3.10+** (only if using the `.py` file)
- **FFmpeg** (optional, for MP3/WAV/FLAC)
- Internet connection (to fetch videos)

### Version

**2.1.0** — [Semantic Versioning](https://semver.org/). Check for updates from the app (Web UI footer or CLI message).

---

*For personal use only. Respect creators and platform terms.*
