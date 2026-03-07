/**
 * YT-Downloader — Cloudflare Worker
 *
 * Replaces the Python/FastAPI backend for users who don't want to self-host.
 * Deploy once with `wrangler deploy`; the frontend calls this Worker by default.
 *
 * Flow:
 *   Browser → POST /api/download {url, format, playlist}
 *           → Worker calls YouTube Innertube API
 *           → Worker responds with 302 → YouTube CDN stream
 *           → Browser downloads the file natively
 *
 * Note: Audio transcoding (mp3/wav/flac etc.) requires FFmpeg which can't run
 * in a Worker. Audio downloads are served as the best available .m4a stream.
 * Use the Python api/ backend for full format transcoding.
 */

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

const INNERTUBE_API_URL =
  "https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8";

const INNERTUBE_CONTEXT = {
  client: {
    clientName: "ANDROID",
    clientVersion: "17.31.35",
    androidSdkVersion: 30,
    hl: "en",
    gl: "US",
    utcOffsetMinutes: 0,
  },
};

const VIDEO_FORMATS = new Set(["mp4", "mov", "webm", "mkv"]);
const AUDIO_FORMATS = new Set(["mp3", "wav", "m4a", "aac", "ogg", "flac"]);

/** Extract video ID from any YouTube URL format */
function extractVideoId(url) {
  try {
    const u = new URL(url);
    // youtube.com/shorts/ID
    const shortsMatch = u.pathname.match(/^\/shorts\/([a-zA-Z0-9_-]{11})/);
    if (shortsMatch) return shortsMatch[1];
    // youtube.com/watch?v=ID
    const v = u.searchParams.get("v");
    if (v && v.length === 11) return v;
    // youtu.be/ID
    if (u.hostname === "youtu.be") {
      const id = u.pathname.slice(1, 12);
      if (id.length === 11) return id;
    }
    // youtube.com/embed/ID
    const embedMatch = u.pathname.match(/^\/embed\/([a-zA-Z0-9_-]{11})/);
    if (embedMatch) return embedMatch[1];
  } catch (_) {}
  return null;
}

/** Call the Innertube player API and return adaptive formats */
async function getPlayerData(videoId) {
  const res = await fetch(INNERTUBE_API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json", "User-Agent": "com.google.android.youtube/17.31.35" },
    body: JSON.stringify({
      videoId,
      context: INNERTUBE_CONTEXT,
    }),
  });
  if (!res.ok) throw new Error(`Innertube error: ${res.status}`);
  return res.json();
}

/** Pick the best stream URL for the requested format */
function pickStream(data, format) {
  const isAudio = AUDIO_FORMATS.has(format);
  const streamingData = data.streamingData;
  if (!streamingData) throw new Error("No streaming data returned by YouTube");

  if (isAudio) {
    // Pick best audio-only adaptive format
    const audioFormats = (streamingData.adaptiveFormats || []).filter(
      (f) => f.mimeType && f.mimeType.startsWith("audio/")
    );
    if (!audioFormats.length) throw new Error("No audio streams found");
    // Prefer m4a (audio/mp4 container) then any
    const m4a = audioFormats.find((f) => f.mimeType.includes("mp4"));
    const best = m4a || audioFormats.sort((a, b) => (b.bitrate || 0) - (a.bitrate || 0))[0];
    return { url: best.url, mimeType: best.mimeType, ext: "m4a" };
  }

  // Video: prefer progressive (combined) streams first
  const progressive = streamingData.formats || [];
  if (progressive.length) {
    // Highest quality progressive stream
    const best = progressive.sort((a, b) => (b.height || 0) - (a.height || 0))[0];
    return { url: best.url, mimeType: best.mimeType || "video/mp4", ext: "mp4" };
  }

  // Fall back to best adaptive video stream (no audio — still downloadable)
  const videoFormats = (streamingData.adaptiveFormats || []).filter(
    (f) => f.mimeType && f.mimeType.startsWith("video/")
  );
  if (!videoFormats.length) throw new Error("No video streams found");
  const best = videoFormats.sort((a, b) => (b.height || 0) - (a.height || 0))[0];
  return { url: best.url, mimeType: best.mimeType, ext: "mp4" };
}

async function handleDownload(request) {
  let body;
  try {
    body = await request.json();
  } catch (_) {
    return new Response(JSON.stringify({ detail: "Invalid JSON body" }), {
      status: 400,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    });
  }

  const { url, format = "mp4" } = body;

  if (!url) {
    return new Response(JSON.stringify({ detail: "url is required" }), {
      status: 400,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    });
  }

  if (!VIDEO_FORMATS.has(format) && !AUDIO_FORMATS.has(format)) {
    return new Response(
      JSON.stringify({ detail: `Unsupported format: ${format}` }),
      { status: 400, headers: { ...CORS_HEADERS, "Content-Type": "application/json" } }
    );
  }

  const videoId = extractVideoId(url);
  if (!videoId) {
    return new Response(
      JSON.stringify({ detail: "Could not extract a YouTube video ID from the URL" }),
      { status: 400, headers: { ...CORS_HEADERS, "Content-Type": "application/json" } }
    );
  }

  let playerData;
  try {
    playerData = await getPlayerData(videoId);
  } catch (err) {
    return new Response(JSON.stringify({ detail: err.message }), {
      status: 502,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    });
  }

  const videoDetails = playerData.videoDetails || {};
  const title = (videoDetails.title || videoId).replace(/[^\w\s-]/g, "").trim().slice(0, 80);

  let stream;
  try {
    stream = pickStream(playerData, format);
  } catch (err) {
    return new Response(JSON.stringify({ detail: err.message }), {
      status: 404,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    });
  }

  // Instead of proxying the bytes (expensive), redirect the browser directly
  // to YouTube's CDN. The browser will download the file from there.
  const filename = `${title} [${videoId}].${stream.ext}`;
  return new Response(null, {
    status: 302,
    headers: {
      ...CORS_HEADERS,
      Location: stream.url,
      "Content-Disposition": `attachment; filename="${filename}"`,
    },
  });
}

export default {
  async fetch(request) {
    const { method, url } = request;
    const path = new URL(url).pathname;

    // CORS preflight
    if (method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    if (method === "POST" && path === "/api/download") {
      return handleDownload(request);
    }

    if (method === "GET" && path === "/") {
      return new Response(
        JSON.stringify({ service: "YT-Downloader Worker", status: "ok" }),
        { status: 200, headers: { ...CORS_HEADERS, "Content-Type": "application/json" } }
      );
    }

    return new Response(JSON.stringify({ detail: "Not found" }), {
      status: 404,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    });
  },
};
