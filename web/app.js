(function () {
  "use strict";

  var form       = document.getElementById("form");
  var urlInput   = document.getElementById("url");
  var submitBtn  = document.getElementById("submit");
  var messageEl  = document.getElementById("message");
  var outputDirInput = document.getElementById("output-dir");
  var browseBtn  = document.getElementById("browse-btn");
  var langButtons = document.querySelectorAll(".lang-btn");

  // Default output directory — overwritten after pywebviewready fires
  var outputDir = "";

  // ---------------------------------------------------------------------------
  // i18n
  // ---------------------------------------------------------------------------
  var translations = {
    "en": {
      title: "YT Downloader",
      tagline: "Paste a link. Pick a format. Download. (Local only \u2014 runs on your machine.)",
      urlLabel: "URL",
      urlPlaceholder: "https://youtube.com/watch?v=\u2026 or playlist link",
      formatLabel: "Format",
      outputDirLabel: "Save to",
      browseButton: "Browse\u2026",
      playlistLabel: "Download full playlist",
      playlistHint: "When unchecked, only the single video is downloaded (even if the URL is a playlist).",
      downloadButton: "Download",
      footerText: "Runs locally on your computer. Uses yt-dlp. For personal use only.",
      showInFinder: "Show in Finder",
      messages: {
        enterUrl: "Please enter a URL.",
        downloadFailed: "Download failed",
        genericError: "Something went wrong.",
        savedTo: "Saved to: "
      }
    },
    "zh-TW": {
      title: "YT \u5f71\u97f3\u4e0b\u8f09\u5668",
      tagline: "\u8cbc\u4e0a\u9023\u7d50\uff0c\u9078\u64c7\u683c\u5f0f\uff0c\u7acb\u5373\u4e0b\u8f09\u3002\uff08\u5b8c\u5168\u5728\u672c\u6a5f\u57f7\u884c\uff09",
      urlLabel: "\u7db2\u5740",
      urlPlaceholder: "https://youtube.com/watch?v=\u2026 \u6216\u64ad\u653e\u6e05\u55ae\u9023\u7d50",
      formatLabel: "\u683c\u5f0f",
      outputDirLabel: "\u5132\u5b58\u81f3",
      browseButton: "\u700f\u89bd\u2026",
      playlistLabel: "\u4e0b\u8f09\u6574\u500b\u64ad\u653e\u6e05\u55ae",
      playlistHint: "\u672a\u52fe\u9078\u6642\uff0c\u5373\u4f7f\u662f\u64ad\u653e\u6e05\u55ae\u7db2\u5740\u4e5f\u53ea\u6703\u4e0b\u8f09\u55ae\u4e00\u5f71\u7247\u3002",
      downloadButton: "\u4e0b\u8f09",
      footerText: "\u5728\u4f60\u7684\u96fb\u8166\u672c\u6a5f\u57f7\u884c\uff0c\u4f7f\u7528 yt-dlp\u3002\u50c5\u4f9b\u500b\u4eba\u4f7f\u7528\u3002",
      showInFinder: "\u5728 Finder \u4e2d\u986f\u793a",
      messages: {
        enterUrl: "\u8acb\u8f38\u5165\u7db2\u5740\u3002",
        downloadFailed: "\u4e0b\u8f09\u5931\u6557",
        genericError: "\u51fa\u73fe\u932f\u8aa4\uff0c\u8acb\u7a0d\u5f8c\u518d\u8a66\u3002",
        savedTo: "\u5df2\u5132\u5b58\u81f3\uff1a"
      }
    }
  };

  var currentLang = (function () {
    try {
      var stored = localStorage.getItem("yt_downloader_lang");
      if (stored === "zh-TW") return "zh-TW";
    } catch (e) {}
    return "en";
  })();

  function t(key) {
    var dict  = translations[currentLang] || translations["en"];
    var parts = key.split(".");
    var value = dict;
    for (var i = 0; i < parts.length; i++) {
      if (!value || typeof value !== "object") return null;
      value = value[parts[i]];
    }
    return typeof value === "string" ? value : null;
  }

  function applyLanguage(lang) {
    if (!translations[lang]) lang = "en";
    currentLang = lang;
    try { localStorage.setItem("yt_downloader_lang", lang); } catch (e) {}

    var htmlEl = document.documentElement;
    if (htmlEl) htmlEl.lang = lang === "zh-TW" ? "zh-Hant" : "en";

    var titleEl = document.querySelector(".title");
    if (titleEl && t("title")) titleEl.textContent = t("title");

    var taglineEl = document.querySelector(".tagline");
    if (taglineEl && t("tagline")) taglineEl.textContent = t("tagline");

    var urlLabelEl = document.querySelector("label[for='url']");
    if (urlLabelEl && t("urlLabel")) urlLabelEl.textContent = t("urlLabel");

    if (urlInput && t("urlPlaceholder")) urlInput.placeholder = t("urlPlaceholder");

    var formatLabelEl = document.querySelector("label[for='format']");
    if (formatLabelEl && t("formatLabel")) formatLabelEl.textContent = t("formatLabel");

    var outputDirLabelEl = document.querySelector("label[for='output-dir']");
    if (outputDirLabelEl && t("outputDirLabel")) outputDirLabelEl.textContent = t("outputDirLabel");

    if (browseBtn && t("browseButton")) browseBtn.textContent = t("browseButton");

    var playlistLabelEl = document.querySelector(".toggle-label");
    if (playlistLabelEl && t("playlistLabel")) playlistLabelEl.textContent = t("playlistLabel");

    var hintEl = document.querySelector(".playlist-field .hint");
    if (hintEl && t("playlistHint")) hintEl.textContent = t("playlistHint");

    var btnTextEl = document.querySelector(".btn-text");
    if (btnTextEl && t("downloadButton")) btnTextEl.textContent = t("downloadButton");

    var footerTextEl = document.querySelector(".footer p");
    if (footerTextEl && t("footerText")) footerTextEl.textContent = t("footerText");

    Array.prototype.forEach.call(langButtons, function (btn) {
      btn.classList.toggle("is-active", (btn.getAttribute("data-lang") || "en") === lang);
    });
  }

  // ---------------------------------------------------------------------------
  // UI helpers
  // ---------------------------------------------------------------------------
  function setLoading(loading) {
    form.classList.toggle("loading", loading);
    submitBtn.disabled = loading || urlInput.value.trim().length === 0;
  }

  function showMessage(html, type) {
    messageEl.innerHTML = html;
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

  // ---------------------------------------------------------------------------
  // Folder picker
  // ---------------------------------------------------------------------------
  function setOutputDir(path) {
    if (!path) return;
    outputDir = path;
    if (outputDirInput) outputDirInput.value = path;
  }

  if (browseBtn) {
    browseBtn.addEventListener("click", function () {
      window.pywebview.api.pick_folder().then(function (path) {
        if (path) setOutputDir(path);
      });
    });
  }

  // ---------------------------------------------------------------------------
  // URL input validation
  // ---------------------------------------------------------------------------
  urlInput.addEventListener("input", function () {
    setValidity(urlInput.value.trim().length > 0);
    hideMessage();
  });
  urlInput.addEventListener("paste", function () {
    setTimeout(function () { setValidity(urlInput.value.trim().length > 0); }, 0);
  });

  // ---------------------------------------------------------------------------
  // Form submit → pywebview API call
  // ---------------------------------------------------------------------------
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    hideMessage();

    var url = urlInput.value.trim();
    if (!url) {
      showMessage(t("messages.enterUrl") || "Please enter a URL.", "error");
      return;
    }

    var formatEl = document.getElementById("format");
    var format   = formatEl ? (formatEl.value || "mp4").toLowerCase() : "mp4";
    var playlist = document.getElementById("playlist").checked;

    setLoading(true);

    window.pywebview.api.download(url, format, playlist, outputDir)
      .then(function (result) {
        if (result.success) {
          var path    = result.output_dir || "";
          var label   = t("messages.savedTo") || "Saved to: ";
          var linkTxt = t("showInFinder") || "Show in Finder";
          var html = label + "<strong>" + escHtml(path) + "</strong>"
            + " &mdash; <a href=\"#\" class=\"reveal-link\">" + escHtml(linkTxt) + "</a>";
          showMessage(html, "success");
          var link = messageEl.querySelector(".reveal-link");
          if (link) {
            link.addEventListener("click", function (ev) {
              ev.preventDefault();
              window.pywebview.api.reveal_folder(path);
            });
          }
        } else {
          var errMsg = result.error || t("messages.genericError") || "Something went wrong.";
          showMessage(escHtml(errMsg), "error");
        }
      })
      .catch(function (err) {
        showMessage(escHtml((err && err.message) || t("messages.genericError") || "Something went wrong."), "error");
      })
      .finally(function () {
        setLoading(false);
      });
  });

  function escHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ---------------------------------------------------------------------------
  // Language buttons
  // ---------------------------------------------------------------------------
  Array.prototype.forEach.call(langButtons, function (btn) {
    btn.addEventListener("click", function () {
      applyLanguage(btn.getAttribute("data-lang") || "en");
    });
  });

  // ---------------------------------------------------------------------------
  // Boot: wait for pywebview, then initialise
  // ---------------------------------------------------------------------------
  function init() {
    applyLanguage(currentLang);
    setValidity(urlInput.value.trim().length > 0);

    // Set default output dir from Python (home/Downloads)
    window.pywebview.api.get_version().then(function (data) {
      if (!data) return;
      var versionEl = document.getElementById("version");
      if (versionEl) versionEl.textContent = "v" + data.current;
    }).catch(function () {});
  }

  // pywebview injects window.pywebview before firing this event
  window.addEventListener("pywebviewready", function () {
    // Resolve the default output folder on the Python side
    // (~/Downloads works cross-platform; Python resolved it already)
    var defaultDir = "";
    try {
      // Use the platform home dir via a simple heuristic
      if (window.navigator.platform.toLowerCase().indexOf("win") !== -1) {
        defaultDir = "";
      }
    } catch (e) {}

    // Ask Python for a safe default (just use a known cross-platform path)
    // We derive it client-side: navigator gives us nothing useful, so we
    // leave it empty and let the Python side fill it on first download.
    // Instead, show a placeholder so the user knows they can browse.
    if (outputDirInput && !outputDir) {
      outputDirInput.placeholder = "~/Downloads";
    }

    init();
  });

  // Fallback in case pywebviewready already fired (shouldn't happen but safe)
  if (window.pywebview) {
    init();
  }
})();
