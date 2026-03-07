# YT Downloader

A **local-only** Python app that wraps [yt-dlp](https://github.com/yt-dlp/yt-dlp). No web API, no backend — it runs entirely on your machine and only connects to the internet to fetch videos. Works on **Windows** and **macOS**.

## Single-file release (easiest)

Download **one file** and run it (no repo clone needed):

```bash
# Download YT-Downloader.py from the repo, then:
python YT-Downloader.py
```

With no arguments it opens the **web UI** in your browser. First run creates a `.venv` next to the file and installs dependencies; later runs reuse it.

```bash
python YT-Downloader.py "https://youtube.com/watch?v=..."
python YT-Downloader.py --web
python YT-Downloader.py --gui
python YT-Downloader.py "https://..." -f mp3 --playlist
```

You can attach `YT-Downloader.py` to a [GitHub Release](https://github.com/willwang0202/YT-Downloader/releases) so users download a single runnable file.

### Standalone .exe (Windows) and .app (macOS)

To build **YT-Downloader.exe** and **YT-Downloader.app** so users don’t need Python:

- **Windows:** build on Windows → `dist/YT-Downloader.exe`
- **macOS:** build on macOS → `dist/YT-Downloader.app`

See **[BUILD.md](BUILD.md)** for PyInstaller steps. Use **[RELEASE_DESCRIPTION.md](RELEASE_DESCRIPTION.md)** as the GitHub release description.

## What you need

- **Python 3.10+** — [python.org](https://www.python.org/downloads/) (Windows: check “Add Python to PATH” when installing)
- **FFmpeg** (optional) — needed for audio formats (MP3, WAV, FLAC, etc.). Video (MP4, WebM, MKV) and M4A often work without it. [FFmpeg downloads](https://ffmpeg.org/download.html)

## Quick start

**One command on both macOS and Windows:**

```bash
python run.py "https://youtube.com/watch?v=..."
```

The first run creates a virtual environment (`.venv`) and installs dependencies. Later runs reuse it.

### Optional: script wrappers

- **macOS / Linux:** `chmod +x run.sh` then `./run.sh "https://..."`
- **Windows:** `run.bat "https://..."`

Both call `run.py`; use whichever you prefer.

## Usage

### Command line

```bash
# Single video (default: MP4)
python run.py "https://youtube.com/watch?v=..."

# Audio only (e.g. MP3) — requires FFmpeg
python run.py "https://youtube.com/watch?v=..." -f mp3

# Full playlist
python run.py "https://youtube.com/playlist?list=..." --playlist

# Web UI (opens in browser)
python run.py --web

# Desktop GUI
python run.py --gui
```

**Formats:** `mp4`, `mov`, `webm`, `mkv` (video) | `mp3`, `wav`, `m4a`, `aac`, `ogg`, `flac` (audio).

**Options:**

| Option | Description |
|--------|-------------|
| `url` | Video or playlist URL (positional) |
| `-f`, `--format` | Output format (default: `mp4`) |
| `-p`, `--playlist` | Download full playlist |
| `-o`, `--output-dir` | Folder to save files (default: current directory) |
| `--gui` | Open the graphical interface instead of CLI |
| `--web` | Start the local web UI (opens in browser) |

### Graphical interface (GUI)

```bash
python run.py --gui
```

Paste a URL, pick format and options, choose a folder, and click Download. No cloud API — everything runs locally.

### Web UI

```bash
python run.py --web
```

Your browser will open to the UI. Paste a URL, choose format and playlist option, and click Download. Files are sent to your browser; the server does not expose your machine to the network.

## Project layout

```
YT-Downloader/
├── YT-Downloader.py   # Single runnable release file (embed all-in-one)
├── run.py             # Entry point (macOS + Windows)
├── yt_downloader.py   # Main app (CLI + GUI + --web)
├── server.py          # Local web server for web UI
├── version.py         # Version & GitHub update check
├── web/               # Web UI (HTML, CSS, JS)
├── requirements.txt
├── run.sh
├── run.bat
└── README.md
```

## Without the run script

If you prefer to manage the virtual environment yourself:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python yt_downloader.py "https://youtube.com/watch?v=..."
```

## Disclaimer

For personal use only. Respect creators’ rights and the terms of the platforms you download from.
