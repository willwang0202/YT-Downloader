# YT Downloader

A minimal YouTube (and yt-dlp–supported) downloader with a static frontend for **GitHub Pages** and a small API backend using **yt-dlp**.

## Features

- **yt-dlp** for reliable downloads
- **GitHub Pages**–ready static UI; public users can trigger downloads once the API is set
- **Playlist or single**: choose “Download full playlist” or only the linked video/song (default single)
- **Formats**: `.mov`, `.mp4`, `.mp3`, `.wav`
- Minimal, dark UI with smooth animations

## Quick start (local)

1. **Backend** (requires [FFmpeg](https://ffmpeg.org/) and Python 3.10+):

   ```bash
   cd api
   python -m venv venv
   source venv/bin/activate   # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   python server.py
   ```

   API runs at `http://127.0.0.1:8000`. Open **http://127.0.0.1:8000/** in a browser (you’re redirected to `/static/`). No need to set the API URL—same origin is used automatically.

## Deploy for public use

- **Frontend (GitHub Pages)**  
  - Push the repo and enable GitHub Pages (Settings → Pages → source: main branch, root or `/docs` if you put the site in `docs/`).  
  - The site is static; no build step.

- **Backend**  
  GitHub Pages cannot run Python or yt-dlp. Deploy the API separately so the frontend can call it:

  1. **Railway**  
     - New project → Deploy from GitHub (this repo).  
     - Set root directory to `api` or the folder that contains `server.py`.  
     - Add a start command: `uvicorn server:app --host 0.0.0.0 --port $PORT` (or run `python server.py` if it reads `PORT`).  
     - Install **FFmpeg** in the environment (e.g. use an [FFmpeg buildpack](https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest) or a Dockerfile that installs FFmpeg + Python).

  2. **Render**  
     - New Web Service → connect repo.  
     - Root directory: `api`.  
     - Build: `pip install -r requirements.txt`.  
     - Start: `uvicorn server:app --host 0.0.0.0 --port $PORT` or `python server.py`.  
     - Add FFmpeg via a [native environment](https://render.com/docs/native-environments) or Docker.

  3. After deploy, copy the backend URL (e.g. `https://your-app.railway.app`) and in the **frontend** set **API base URL** to that URL (once per device; it’s stored in `localStorage`).

## Project layout

```
YT-Downloader/
├── index.html      # Single-page UI
├── styles.css      # Layout and animations
├── app.js          # Form logic and API calls
├── config.js       # Optional: set window.YT_DOWNLOADER_API
├── requirements.txt
├── api/
│   ├── requirements.txt
│   └── server.py   # FastAPI + yt-dlp
└── README.md
```

## API

- `POST /api/download`  
  Body (JSON): `{ "url": "<video or playlist URL>", "format": "mp4"|"mov"|"mp3"|"wav", "playlist": true|false }`  
  Returns: binary file (single) or `playlist.zip` (playlist).  
  CORS is enabled for all origins so the GitHub Pages site can call it.

## Disclaimer

For personal use only. Respect creators’ rights and the terms of the platforms you download from.
