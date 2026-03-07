#!/usr/bin/env python3
"""
YT-Downloader — Local Python app that wraps yt-dlp.
No web API. Runs entirely on your machine. Only connects to the internet to fetch videos.
Works on Windows and macOS. Requires Python 3.10+ and (for audio formats) FFmpeg.
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
from pathlib import Path
from typing import Callable

# Use certifi's CA bundle so HTTPS works on macOS (avoids CERTIFICATE_VERIFY_FAILED)
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    pass

try:
    import yt_dlp
except ImportError:
    print("yt-dlp is not installed. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

# -----------------------------------------------------------------------------
# Format and options (same logic as original API)
# -----------------------------------------------------------------------------
VIDEO_FORMATS = ("mp4", "mov", "webm", "mkv")
AUDIO_FORMATS = ("mp3", "wav", "m4a", "aac", "ogg", "flac")
ALL_FORMATS = VIDEO_FORMATS + AUDIO_FORMATS


def get_ydl_opts(format_key: str, out_dir: str | Path, single: bool) -> dict:
    """Build yt-dlp options for the chosen format and mode."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_only = format_key in AUDIO_FORMATS
    opts = {
        "outtmpl": str(out_dir / "%(title)s [%(id)s].%(ext)s"),
        "noplaylist": single,
        "quiet": False,
        "no_warnings": False,
    }
    opts["extractor_args"] = {"youtube": {"player_client": ["android_testsuite"]}}

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


def download(
    url: str,
    format_key: str = "mp4",
    playlist: bool = False,
    output_dir: str | Path | None = None,
    progress_hook: Callable | None = None,
) -> None:
    """Run yt-dlp for the given URL. Raises on error."""
    if format_key not in ALL_FORMATS:
        raise ValueError(f"format must be one of: {', '.join(ALL_FORMATS)}")
    out_dir = Path(output_dir or os.getcwd()).resolve()
    single = not playlist
    opts = get_ydl_opts(format_key, out_dir, single)
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def main_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Download videos/audio from YouTube and other sites using yt-dlp (local only, no web API)."
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Video or playlist URL (e.g. youtube.com/watch?v=..., youtu.be/..., youtube.com/shorts/...)",
    )
    parser.add_argument(
        "-f", "--format",
        choices=ALL_FORMATS,
        default="mp4",
        help="Output format (default: mp4)",
    )
    parser.add_argument(
        "-p", "--playlist",
        action="store_true",
        help="Download full playlist; if not set, only the single video is downloaded",
    )
    parser.add_argument(
        "-o", "--output-dir",
        default=None,
        metavar="DIR",
        help="Directory to save files (default: current directory)",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open the graphical interface instead of CLI",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start the local web UI (browser opens automatically)",
    )
    args = parser.parse_args()

    if args.gui:
        launch_gui(output_dir=args.output_dir)
        return

    if args.web:
        launch_web()
        return

    if not args.url or not args.url.strip():
        parser.error("Please provide a URL. Example: yt_downloader.py https://youtube.com/watch?v=...")
    url = args.url.strip()

    try:
        download(
            url=url,
            format_key=args.format,
            playlist=args.playlist,
            output_dir=args.output_dir,
        )
        print("Done.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


# -----------------------------------------------------------------------------
# Web UI (local server — browser opens to 127.0.0.1)
# -----------------------------------------------------------------------------
def launch_web() -> None:
    try:
        from server import run_server
    except ImportError as e:
        print("Web server dependencies missing or server not found.", file=sys.stderr)
        print("Install with: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)
    run_server()


# -----------------------------------------------------------------------------
# GUI (tkinter — no extra dependencies, works on Windows and macOS)
# -----------------------------------------------------------------------------
def launch_gui(output_dir: str | Path | None = None) -> None:
    try:
        import tkinter as tk
        from tkinter import ttk, scrolledtext, messagebox, filedialog
    except ImportError:
        print("tkinter is not available. Use the CLI: python yt_downloader.py <URL>", file=sys.stderr)
        sys.exit(1)

    root = tk.Tk()
    root.title("YT Downloader")
    root.minsize(420, 380)
    root.geometry("480x420")

    out_dir_var = tk.StringVar(value=str(Path(output_dir or os.getcwd()).resolve()))

    # URL
    ttk.Label(root, text="URL").pack(anchor="w", padx=12, pady=(12, 2))
    url_entry = ttk.Entry(root, width=60)
    url_entry.pack(fill="x", padx=12, pady=(0, 8))
    url_entry.focus()

    # Format
    ttk.Label(root, text="Format").pack(anchor="w", padx=12, pady=(4, 2))
    format_var = tk.StringVar(value="mp4")
    format_combo = ttk.Combobox(root, textvariable=format_var, values=list(ALL_FORMATS), state="readonly", width=12)
    format_combo.pack(anchor="w", padx=12, pady=(0, 8))

    # Playlist
    playlist_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(root, text="Download full playlist", variable=playlist_var).pack(anchor="w", padx=12, pady=4)

    # Output directory
    ttk.Label(root, text="Save to folder").pack(anchor="w", padx=12, pady=(8, 2))
    out_frame = ttk.Frame(root)
    out_frame.pack(fill="x", padx=12, pady=(0, 8))
    ttk.Entry(out_frame, textvariable=out_dir_var, width=50).pack(side="left", fill="x", expand=True, padx=(0, 4))

    def choose_dir() -> None:
        d = filedialog.askdirectory(initialdir=out_dir_var.get() or None)
        if d:
            out_dir_var.set(d)

    ttk.Button(out_frame, text="Browse…", command=choose_dir).pack(side="right")

    # Log
    ttk.Label(root, text="Log").pack(anchor="w", padx=12, pady=(8, 2))
    log = scrolledtext.ScrolledText(root, height=8, state="disabled", wrap="word", font=("Consolas", 9))
    log.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    def log_msg(msg: str) -> None:
        log.config(state="normal")
        log.insert("end", msg + "\n")
        log.see("end")
        log.config(state="disabled")

    def do_download() -> None:
        url = (url_entry.get() or "").strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a video or playlist URL.")
            return
        out_dir = (out_dir_var.get() or "").strip() or os.getcwd()
        format_key = format_var.get() or "mp4"
        if format_key not in ALL_FORMATS:
            format_key = "mp4"

        def run() -> None:
            try:
                log_msg(f"Downloading: {url} ({format_key}, playlist={playlist_var.get()})")

                def hook(d: dict) -> None:
                    status = d.get("status")
                    if status == "finished":
                        log_msg(f"Finished: {d.get('filename', '')}")

                download(
                    url=url,
                    format_key=format_key,
                    playlist=playlist_var.get(),
                    output_dir=out_dir,
                    progress_hook=hook,
                )
                root.after(0, lambda: (log_msg("Done."), messagebox.showinfo("Done", "Download finished.")))
            except Exception as e:
                root.after(0, lambda: (log_msg(f"Error: {e}"), messagebox.showerror("Error", str(e))))

        btn_dl.config(state="disabled")
        threading.Thread(target=run, daemon=True).start()

        def reenable() -> None:
            btn_dl.config(state="normal")

        root.after(500, reenable)

    btn_dl = ttk.Button(root, text="Download", command=do_download)
    btn_dl.pack(pady=8)

    root.mainloop()


if __name__ == "__main__":
    main_cli()
