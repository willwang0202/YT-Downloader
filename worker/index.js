/**
 * YT-Downloader — Cloudflare Worker
 *
 * Tries multiple Innertube clients in sequence until one returns streaming data.
 * Clients: IOS → ANDROID_TESTSUITE → ANDROID (newest)
 *
 * Deploy: cd worker && npm run deploy
 */

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

const INNERTUBE_URL = "https://www.youtube.com/youtubei/v1/player";

// Clients tried in order until one returns streamingData
const CLIENTS = [
  {
    // IOS — direct stream URLs, no cipher needed
    context: {
      client: {
        clientName: "IOS",
        clientVersion: "19.29.1",
        deviceModel: "iPhone16,2",
        deviceMake: "Apple",
        osName: "iPhone",
        osVersion: "17.5.1.21F90",
        hl: "en", gl: "US", utcOffsetMinutes: 0,
      },
    },
    headers: {
      "X-Youtube-Client-Name": "5",
      "X-Youtube-Client-Version": "19.29.1",
      "User-Agent": "com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X)",
      "Origin": "https://www.youtube.com",
    },
  },
  {
    // ANDROID_TESTSUITE — often bypasses authentication checks
    context: {
      client: {
        clientName: "ANDROID_TESTSUITE",
        clientVersion: "1.9",
        androidSdkVersion: 30,
        hl: "en", gl: "US", utcOffsetMinutes: 0,
      },
    },
    headers: {
      "X-Youtube-Client-Name": "30",
      "X-Youtube-Client-Version": "1.9",
      "User-Agent": "com.google.android.youtube/1.9 (Linux; U; Android 11) gzip",
      "Origin": "https://www.youtube.com",
    },
  },
  {
    // ANDROID — newest version
    context: {
      client: {
        clientName: "ANDROID",
        clientVersion: "19.44.38",
        androidSdkVersion: 30,
        hl: "en", gl: "US", utcOffsetMinutes: 0,
      },
    },
    headers: {
      "X-Youtube-Client-Name": "3",
      "X-Youtube-Client-Version": "19.44.38",
      "User-Agent": "com.google.android.youtube/19.44.38 (Linux; U; Android 11) gzip",
      "Origin": "https://www.youtube.com",
    },
  },
];

const VIDEO_FORMATS = new Set(["mp4", "mov", "webm", "mkv"]);
const AUDIO_FORMATS = new Set(["mp3", "wav", "m4a", "aac", "ogg", "flac"]);

function extractVideoId(url) {
  try {
    const u = new URL(url);
    const shortsMatch = u.pathname.match(/^\/shorts\/([a-zA-Z0-9_-]{11})/);
    if (shortsMatch) return shortsMatch[1];
    const v = u.searchParams.get("v");
    if (v && v.length === 11) return v;
    if (u.hostname === "youtu.be") {
      const id = u.pathname.slice(1, 12);
      if (id.length === 11) return id;
    }
    const embedMatch = u.pathname.match(/^\/embed\/([a-zA-Z0-9_-]{11})/);
    if (embedMatch) return embedMatch[1];
  } catch (_) { }
  return null;
}

async function tryClient(client, videoId) {
  const res = await fetch(INNERTUBE_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...client.headers },
    body: JSON.stringify({
      videoId,
      context: client.context,
      contentCheckOk: true,
      racyCheckOk: true,
    }),
  });
  if (!res.ok) return null;
  const data = await res.json();
  if (!data.streamingData) return null;
  return data;
}

function pickStream(data, format) {
  const isAudio = AUDIO_FORMATS.has(format);
  const { streamingData } = data;

  if (isAudio) {
    const audioFormats = (streamingData.adaptiveFormats || []).filter(
      (f) => f.mimeType && f.mimeType.startsWith("audio/")
    );
    if (!audioFormats.length) throw new Error("No audio streams found");
    const m4a = audioFormats.find((f) => f.mimeType.includes("mp4"));
    const best = m4a || audioFormats.sort((a, b) => (b.bitrate || 0) - (a.bitrate || 0))[0];
    return { url: best.url, ext: "m4a" };
  }

  const progressive = (streamingData.formats || []).sort(
    (a, b) => (b.height || 0) - (a.height || 0)
  );
  if (progressive.length) return { url: progressive[0].url, ext: "mp4" };

  const videoFormats = (streamingData.adaptiveFormats || []).filter(
    (f) => f.mimeType && f.mimeType.startsWith("video/")
  );
  if (!videoFormats.length) throw new Error("No video streams found");
  videoFormats.sort((a, b) => (b.height || 0) - (a.height || 0));
  return { url: videoFormats[0].url, ext: "mp4" };
}

async function handleDownload(request) {
  let body;
  try { body = await request.json(); } catch (_) {
    return json({ detail: "Invalid JSON body" }, 400);
  }

  const { url, format = "mp4" } = body;
  if (!url) return json({ detail: "url is required" }, 400);
  if (!VIDEO_FORMATS.has(format) && !AUDIO_FORMATS.has(format))
    return json({ detail: `Unsupported format: ${format}` }, 400);

  const videoId = extractVideoId(url);
  if (!videoId) return json({ detail: "Could not extract a YouTube video ID from the URL" }, 400);

  // Try each client in sequence
  let playerData = null;
  for (const client of CLIENTS) {
    try {
      playerData = await tryClient(client, videoId);
      if (playerData) break;
    } catch (_) { }
  }

  if (!playerData) {
    return json({
      detail: "YouTube rejected all client attempts. Try deploying the Python api/ backend instead.",
    }, 502);
  }

  const title = ((playerData.videoDetails || {}).title || videoId)
    .replace(/[^\w\s-]/g, "").trim().slice(0, 80);

  let stream;
  try { stream = pickStream(playerData, format); } catch (err) {
    return json({ detail: err.message }, 404);
  }

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

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
  });
}

export default {
  async fetch(request) {
    const { method } = request;
    const path = new URL(request.url).pathname;

    if (method === "OPTIONS") return new Response(null, { status: 204, headers: CORS_HEADERS });
    if (method === "POST" && path === "/api/download") return handleDownload(request);
    if (method === "GET" && path === "/") return json({ service: "YT-Downloader Worker", status: "ok" });
    return json({ detail: "Not found" }, 404);
  },
};
