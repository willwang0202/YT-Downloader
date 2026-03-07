(function () {
  "use strict";

  var form = document.getElementById("form");
  var urlInput = document.getElementById("url");
  var apiUrlInput = document.getElementById("apiUrl");
  var submitBtn = document.getElementById("submit");
  var messageEl = document.getElementById("message");

  var STORAGE_KEY = "yt_downloader_api_url";

  function getApiBase() {
    var fromInput = apiUrlInput && apiUrlInput.value.trim();
    if (fromInput) return fromInput.replace(/\/$/, "");
    if (typeof window.YT_DOWNLOADER_API !== "undefined" && window.YT_DOWNLOADER_API) {
      return window.YT_DOWNLOADER_API.replace(/\/$/, "");
    }
    try {
      var stored = localStorage.getItem(STORAGE_KEY);
      if (stored) return stored.replace(/\/$/, "");
    } catch (_) { }
    return window.location.origin;
  }

  function setApiBase(url) {
    try { localStorage.setItem(STORAGE_KEY, url); } catch (_) { }
  }

  function setLoading(loading) {
    form.classList.toggle("loading", loading);
    submitBtn.disabled = loading;
  }

  function showMessage(text, type) {
    messageEl.textContent = text;
    messageEl.className = "message " + (type || "info");
    messageEl.hidden = false;
  }

  function hideMessage() {
    messageEl.hidden = true;
    messageEl.className = "message";
  }

  function setValidity(valid) {
    urlInput.setCustomValidity(valid ? "" : " ");
    submitBtn.disabled = !valid;
  }

  urlInput.addEventListener("input", function () {
    var v = urlInput.value.trim();
    setValidity(v.length > 0);
    hideMessage();
  });

  urlInput.addEventListener("paste", function () {
    setTimeout(function () {
      var v = urlInput.value.trim();
      setValidity(v.length > 0);
    }, 0);
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    hideMessage();

    var url = urlInput.value.trim();
    if (!url) {
      showMessage("Please enter a URL.", "error");
      return;
    }

    var formatEl = document.getElementById("format");
    var format = formatEl ? formatEl.value : "mp4";
    var playlist = document.getElementById("playlist").checked;

    var apiBase = getApiBase();
    if (!apiBase) {
      showMessage("Open Advanced and set the API base URL, or deploy the api/ folder and use this app from the same origin.", "error");
      return;
    }
    if (apiUrlInput && apiUrlInput.value.trim()) setApiBase(apiBase);

    var endpoint = apiBase + "/api/download";
    setLoading(true);

    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url, format: format, playlist: playlist }),
    })
      .then(function (res) {
        if (!res.ok) {
          return res.json().then(function (body) {
            throw new Error(body.detail || res.statusText || "Download failed");
          }).catch(function (err) {
            if (err.message) throw err;
            return res.text().then(function (t) { throw new Error(t || "Download failed"); });
          });
        }
        return res.blob();
      })
      .then(function (blob) {
        var disposition = "playlist.zip";
        var contentType = blob.type || "application/octet-stream";
        var isZip = contentType.indexOf("zip") !== -1;
        if (!isZip && blob.size > 0) {
          var ext = format;
          disposition = "download." + ext;
        }
        var a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = disposition;
        a.click();
        URL.revokeObjectURL(a.href);
        showMessage("Download started.", "success");
      })
      .catch(function (err) {
        showMessage(err.message || "Something went wrong.", "error");
      })
      .finally(function () {
        setLoading(false);
      });
  });

  if (apiUrlInput) {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved) apiUrlInput.value = saved;
    } catch (_) { }
  }

  setValidity(urlInput.value.trim().length > 0);

  var versionEl = document.getElementById("version");
  if (versionEl && window.YT_DOWNLOADER_VERSION) {
    versionEl.textContent = "v" + window.YT_DOWNLOADER_VERSION;
  }
})();
