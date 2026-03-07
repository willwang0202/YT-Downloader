# YT Downloader

A minimal YouTube (and yt-dlp–supported) downloader with a static frontend for **GitHub Pages** and a serverless backend using a **Cloudflare Worker** (free tier).

## Features

- **No install needed for end users** — just open the page and paste a URL
- Supports `youtube.com/watch`, `youtu.be`, and **YouTube Shorts** (`youtube.com/shorts/…`)
- **Cloudflare Worker** backend — free, global, no cold starts
- **Playlist or single**: choose "Download full playlist" or only the linked video (default single)
- **Formats**: `.mp4`, `.mov`, `.webm`, `.mkv`, `.m4a` (and more via the Python backend)
- Minimal, dark UI with smooth animations

## Quick Start

### Option 1 — Cloudflare Worker (recommended, free, no Python needed)

1. Install [Wrangler](https://developers.cloudflare.com/workers/wrangler/):
   ```bash
   npm install -g wrangler
   wrangler login   # opens browser to authenticate with your Cloudflare account
   ```

2. Deploy the Worker:
   ```bash
   cd worker
   npm install
   npm run deploy
   ```
   Wrangler will print your Worker URL, e.g. `https://yt-downloader.YOUR-NAME.workers.dev`.

3. Paste that URL into **`config.js`**:
   ```js
   window.YT_DOWNLOADER_API = 'https://yt-downloader.YOUR-NAME.workers.dev';
   ```

4. Push to GitHub → GitHub Pages serves the frontend. Done — any browser, no setup for users.

> **Note on audio formats**: The Worker returns audio as `.m4a` (no FFmpeg in Cloudflare). For mp3/wav/flac transcoding, use Option 2 below.

---

### Option 2 — Python backend (full format support, requires FFmpeg)

1. **Start locally** (requires [FFmpeg](https://ffmpeg.org/) and Python 3.10+):
   ```bash
   cd api
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python server.py
   ```
   Open **http://127.0.0.1:8000/**.

2. **Deploy** to Railway or Render:
   - Root directory: `api`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn server:app --host 0.0.0.0 --port $PORT`
   - Add FFmpeg to the environment (buildpack or Docker).
   - Copy the URL and paste it into the **Advanced → API base URL** field (saved in localStorage).

---

## Project Layout

```
YT-Downloader/
├── index.html        # Single-page UI
├── styles.css        # Layout and animations
├── app.js            # Form logic and API calls
├── config.js         # Set window.YT_DOWNLOADER_API here after deploying
├── worker/
│   ├── index.js      # Cloudflare Worker (Innertube API → stream redirect)
│   ├── wrangler.toml # Wrangler deploy config
│   └── package.json
├── api/
│   ├── server.py     # FastAPI + yt-dlp (full transcoding)
│   └── requirements.txt
└── README.md
```

## API Contract

`POST /api/download`  
Body: `{ "url": "<YouTube URL>", "format": "mp4"|"m4a"|…, "playlist": true|false }`  
Returns: binary file (single) or `playlist.zip` (playlist) — or a `302` redirect to the stream (Worker mode).  
CORS is enabled for all origins.

## Disclaimer

For personal use only. Respect creators' rights and the terms of the platforms you download from.
