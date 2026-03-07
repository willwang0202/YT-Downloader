(function () {
  "use strict";

  var form = document.getElementById("form");
  var urlInput = document.getElementById("url");
  var submitBtn = document.getElementById("submit");
  var messageEl = document.getElementById("message");

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
    setValidity(urlInput.value.trim().length > 0);
    hideMessage();
  });
  urlInput.addEventListener("paste", function () {
    setTimeout(function () { setValidity(urlInput.value.trim().length > 0); }, 0);
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
    var format = formatEl ? (formatEl.value || "mp4").toLowerCase() : "mp4";
    var playlist = document.getElementById("playlist").checked;

    var endpoint = "/api/download";
    setLoading(true);

    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url, format: format, playlist: playlist }),
    })
      .then(function (res) {
        if (!res.ok) {
          return res.json().then(function (body) {
            var detail = body.detail;
            var msg = "Download failed";
            if (typeof detail === "string") msg = detail;
            else if (Array.isArray(detail) && detail[0] && detail[0].msg) msg = detail[0].msg;
            throw new Error(msg);
          }).catch(function (err) {
            if (err.message) throw err;
            return res.text().then(function (t) { throw new Error(t || "Download failed"); });
          });
        }
        return res.blob().then(function (blob) { return { blob: blob, res: res }; });
      })
      .then(function (data) {
        var blob = data.blob;
        var res = data.res;
        var contentType = blob.type || "application/octet-stream";
        var isZip = contentType.indexOf("zip") !== -1;
        var disposition;
        if (isZip) {
          disposition = "playlist.zip";
        } else {
          disposition = parseFilenameFromContentDisposition(res.headers.get("Content-Disposition"));
          if (!disposition) disposition = "download." + format;
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

  function parseFilenameFromContentDisposition(header) {
    if (!header) return null;
    var filenameStar = /filename\*=UTF-8''([^;]+)/i.exec(header);
    if (filenameStar) {
      try { return decodeURIComponent(filenameStar[1].trim()); } catch (e) { }
    }
    var filename = /filename="?([^";\n]+)"?/i.exec(header);
    if (filename) return filename[1].replace(/\\"/g, '"').trim();
    return null;
  }

  setValidity(urlInput.value.trim().length > 0);

  // Fetch and display app version (no update banner)
  fetch("/api/version")
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      if (!data) return;
      var versionEl = document.getElementById("version");
      if (versionEl) versionEl.textContent = "v" + data.current;
    })
    .catch(function () {});
})();
