(function () {
  "use strict";

  var form = document.getElementById("form");
  var urlInput = document.getElementById("url");
  var submitBtn = document.getElementById("submit");
  var messageEl = document.getElementById("message");
  var outputDirInput = document.getElementById("output-dir");
  var browseBtn = document.getElementById("browse-btn");
  var langButtons = document.querySelectorAll(".lang-btn");
  var modeEl = document.getElementById("mode");
  var transcribeSourceEl = document.getElementById("transcribe-source");
  var transcribeSourceField = document.getElementById("transcribe-source-field");
  var formatField = document.getElementById("format-field");
  var playlistField = document.getElementById("playlist-field");
  var transcribeModelField = document.getElementById("transcribe-model-field");
  var transcribeModelEl = document.getElementById("transcribe-model");
  var transcribeModelHintEl = document.getElementById("transcribe-model-hint");
  var audioFileField = document.getElementById("audio-file-field");
  var audioFileInput = document.getElementById("audio-file");
  var audioBrowseBtn = document.getElementById("audio-browse-btn");
  var modelModal = document.getElementById("model-modal");
  var modelModalTitle = document.getElementById("model-modal-title");
  var modelModalCopy = document.getElementById("model-modal-copy");
  var modelModalCancelBtn = document.getElementById("model-modal-cancel");
  var modelModalConfirmBtn = document.getElementById("model-modal-confirm");

  var outputDir = "";
  var audioFilePath = "";
  var sttModels = [];
  var defaultTranscribeModel = "base";
  var modalResolver = null;
  var _initialized = false;
  var _modelPromptPending = false;
  var _suppressChangeCheck = false;

  var translations = {
    "en": {
      title: "YT Downloader",
      tagline: "Download videos or transcribe speech locally on your machine.",
      actionLabel: "Action",
      actions: {
        download: "Download",
        transcribe: "Transcribe"
      },
      transcribeSourceLabel: "Transcribe from",
      transcribeSources: {
        youtube: "YouTube URL",
        file: "Audio file"
      },
      urlLabel: "URL",
      youtubeUrlLabel: "YouTube URL",
      urlPlaceholder: "https://youtube.com/watch?v=\u2026 or playlist link",
      audioFileLabel: "Audio file",
      audioFilePlaceholder: "Choose an audio or video file",
      formatLabel: "Format",
      modelLabel: "Model",
      modelHint: "Creates .txt and .srt transcript files locally on your computer.",
      outputDirLabel: "Save to",
      browseButton: "Browse\u2026",
      browseAudioButton: "Browse\u2026",
      playlistLabel: "Download full playlist",
      playlistHint: "When unchecked, only the single video is downloaded (even if the URL is a playlist).",
      downloadButton: "Download",
      transcribeButton: "Transcribe",
      footerText: "Runs locally on your computer. Uses yt-dlp. For personal use only.",
      showInFinder: "Show in Finder",
      installedSuffix: "Installed",
      modal: {
        title: "Download transcription model?",
        confirm: "Download model",
        cancel: "Cancel"
      },
      messages: {
        enterUrl: "Please enter a URL.",
        chooseAudioFile: "Please choose an audio or video file.",
        genericError: "Something went wrong.",
        savedTo: "Saved to: ",
        transcriptSavedTo: "Transcript saved to: ",
        filesCreated: "Files: ",
        detectedLanguage: "Detected language: ",
        downloadingModel: "Downloading the transcription model. This may take a few minutes on first use.",
        modelDownloadCancelled: "Transcription was cancelled because the model was not downloaded.",
        modelMissing: "This transcription model is not installed yet.",
        modelDownloadFailed: "Model download failed.",
        modelReady: "Model downloaded. Starting transcription\u2026",
        transcribeFailed: "Transcription failed"
      }
    },
    "zh-TW": {
      title: "YT \u5f71\u97f3\u4e0b\u8f09\u5668",
      tagline: "\u53ef\u4ee5\u5728\u4f60\u7684\u96fb\u8166\u672c\u6a5f\u4e0b\u8f09\u5f71\u97f3\uff0c\u6216\u9032\u884c\u8a9e\u97f3\u8f49\u6587\u5b57\u3002",
      actionLabel: "\u529f\u80fd",
      actions: {
        download: "\u4e0b\u8f09",
        transcribe: "\u8f49\u9304"
      },
      transcribeSourceLabel: "\u8f49\u9304\u4f86\u6e90",
      transcribeSources: {
        youtube: "YouTube \u7db2\u5740",
        file: "\u97f3\u8a0a\u6a94\u6848"
      },
      urlLabel: "\u7db2\u5740",
      youtubeUrlLabel: "YouTube \u7db2\u5740",
      urlPlaceholder: "https://youtube.com/watch?v=\u2026 \u6216\u64ad\u653e\u6e05\u55ae\u9023\u7d50",
      audioFileLabel: "\u97f3\u8a0a\u6a94\u6848",
      audioFilePlaceholder: "\u9078\u64c7\u97f3\u8a0a\u6216\u5f71\u7247\u6a94",
      formatLabel: "\u683c\u5f0f",
      modelLabel: "\u6a21\u578b",
      modelHint: "\u6703\u5728\u4f60\u7684\u96fb\u8166\u672c\u6a5f\u7522\u751f .txt \u8207 .srt \u8f49\u9304\u6a94\u3002",
      outputDirLabel: "\u5132\u5b58\u81f3",
      browseButton: "\u700f\u89bd\u2026",
      browseAudioButton: "\u700f\u89bd\u2026",
      playlistLabel: "\u4e0b\u8f09\u6574\u500b\u64ad\u653e\u6e05\u55ae",
      playlistHint: "\u672a\u52fe\u9078\u6642\uff0c\u5373\u4f7f\u662f\u64ad\u653e\u6e05\u55ae\u7db2\u5740\u4e5f\u53ea\u6703\u4e0b\u8f09\u55ae\u4e00\u5f71\u7247\u3002",
      downloadButton: "\u4e0b\u8f09",
      transcribeButton: "\u958b\u59cb\u8f49\u9304",
      footerText: "\u5728\u4f60\u7684\u96fb\u8166\u672c\u6a5f\u57f7\u884c\uff0c\u4f7f\u7528 yt-dlp\u3002\u50c5\u4f9b\u500b\u4eba\u4f7f\u7528\u3002",
      showInFinder: "\u5728 Finder \u4e2d\u986f\u793a",
      installedSuffix: "\u5df2\u5b89\u88dd",
      modal: {
        title: "\u8981\u4e0b\u8f09\u8f49\u9304\u6a21\u578b\u55ce\uff1f",
        confirm: "\u4e0b\u8f09\u6a21\u578b",
        cancel: "\u53d6\u6d88"
      },
      messages: {
        enterUrl: "\u8acb\u8f38\u5165\u7db2\u5740\u3002",
        chooseAudioFile: "\u8acb\u9078\u64c7\u97f3\u8a0a\u6216\u5f71\u7247\u6a94\u3002",
        genericError: "\u51fa\u73fe\u932f\u8aa4\uff0c\u8acb\u7a0d\u5f8c\u518d\u8a66\u3002",
        savedTo: "\u5df2\u5132\u5b58\u81f3\uff1a",
        transcriptSavedTo: "\u8f49\u9304\u6a94\u5df2\u5132\u5b58\u81f3\uff1a",
        filesCreated: "\u6a94\u6848\uff1a",
        detectedLanguage: "\u5075\u6e2c\u8a9e\u8a00\uff1a",
        downloadingModel: "\u6b63\u5728\u4e0b\u8f09\u8f49\u9304\u6a21\u578b\uff0c\u9996\u6b21\u4f7f\u7528\u53ef\u80fd\u9700\u8981\u5e7e\u5206\u9418\u3002",
        modelDownloadCancelled: "\u672a\u4e0b\u8f09\u6a21\u578b\uff0c\u5df2\u53d6\u6d88\u8f49\u9304\u3002",
        modelMissing: "\u9019\u500b\u8f49\u9304\u6a21\u578b\u5c1a\u672a\u5b89\u88dd\u3002",
        modelDownloadFailed: "\u6a21\u578b\u4e0b\u8f09\u5931\u6557\u3002",
        modelReady: "\u6a21\u578b\u4e0b\u8f09\u5b8c\u6210\uff0c\u6b63\u5728\u958b\u59cb\u8f49\u9304\u2026",
        transcribeFailed: "\u8f49\u9304\u5931\u6557"
      }
    }
  };

  var currentLang = (function () {
    try {
      var stored = localStorage.getItem("yt_downloader_lang");
      if (stored === "zh-TW") return "zh-TW";
    } catch (e) { }
    return "en";
  })();

  function t(key) {
    var dict = translations[currentLang] || translations.en;
    var parts = key.split(".");
    var value = dict;
    for (var i = 0; i < parts.length; i++) {
      if (!value || typeof value !== "object") return null;
      value = value[parts[i]];
    }
    return typeof value === "string" ? value : null;
  }

  function escHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function isTranscribeMode() {
    return !!modeEl && modeEl.value === "transcribe";
  }

  function usesAudioFile() {
    return isTranscribeMode() && transcribeSourceEl && transcribeSourceEl.value === "file";
  }

  function getActiveInputValue() {
    return usesAudioFile() ? audioFilePath : urlInput.value.trim();
  }

  function setOutputDir(path) {
    if (!path) return;
    outputDir = path;
    if (outputDirInput) outputDirInput.value = path;
  }

  function setAudioFile(path) {
    audioFilePath = path || "";
    if (audioFileInput) audioFileInput.value = audioFilePath;
  }

  function getSelectedModel() {
    var selectedId = transcribeModelEl ? transcribeModelEl.value : defaultTranscribeModel;
    for (var i = 0; i < sttModels.length; i++) {
      if (sttModels[i].id === selectedId) return sttModels[i];
    }
    return null;
  }

  function formatModelSummary(model) {
    if (!model) return "";
    var parts = [];
    if (model.description) parts.push(model.description);
    if (typeof model.download_size_mb === "number") parts.push("~" + model.download_size_mb + " MB");
    if (model.installed) parts.push(t("installedSuffix") || "Installed");
    return parts.join(" \u2022 ");
  }

  function refreshModelOptions(selectedId) {
    if (!transcribeModelEl) return;
    _suppressChangeCheck = true;
    transcribeModelEl.innerHTML = "";
    for (var i = 0; i < sttModels.length; i++) {
      var model = sttModels[i];
      var option = document.createElement("option");
      option.value = model.id;
      option.textContent = model.label + " - " + formatModelSummary(model);
      transcribeModelEl.appendChild(option);
    }
    transcribeModelEl.value = selectedId || defaultTranscribeModel;
    _suppressChangeCheck = false;
    updateModelHint();
  }

  function updateModelHint() {
    if (!transcribeModelHintEl) return;
    var model = getSelectedModel();
    var base = t("modelHint") || "Creates .txt and .srt transcript files locally on your computer.";
    var summary = formatModelSummary(model);
    transcribeModelHintEl.textContent = summary ? base + " " + summary : base;
  }

  function updateSubmitLabel() {
    var btnTextEl = document.querySelector(".btn-text");
    if (!btnTextEl) return;
    btnTextEl.textContent = isTranscribeMode() ? (t("transcribeButton") || "Transcribe") : (t("downloadButton") || "Download");
  }

  function updateModeUI() {
    var transcribe = isTranscribeMode();
    var fileSource = usesAudioFile();
    var urlField = urlInput ? urlInput.closest(".field") : null;
    var urlLabelEl = document.querySelector("label[for='url']");

    if (transcribeSourceField) transcribeSourceField.hidden = !transcribe;
    if (transcribeModelField) transcribeModelField.hidden = !transcribe;
    if (formatField) formatField.hidden = transcribe;
    if (playlistField) playlistField.hidden = transcribe;
    if (audioFileField) audioFileField.hidden = !(transcribe && fileSource);
    if (urlField) urlField.hidden = (transcribe && fileSource);

    if (urlLabelEl) {
      urlLabelEl.textContent = transcribe ? (t("youtubeUrlLabel") || "YouTube URL") : (t("urlLabel") || "URL");
    }
    if (urlInput) {
      urlInput.placeholder = t("urlPlaceholder") || "https://youtube.com/watch?v=\u2026 or playlist link";
    }

    updateSubmitLabel();
    updateModelHint();
    validateForm();
  }

  function validateForm() {
    var valid = getActiveInputValue().length > 0;
    if (urlInput) {
      urlInput.setCustomValidity(valid || usesAudioFile() ? "" : " ");
    }
    if (submitBtn) submitBtn.disabled = !valid;
    return valid;
  }

  function setLoading(loading) {
    form.classList.toggle("loading", loading);
    submitBtn.disabled = loading || !validateForm();
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

  function attachRevealLink(path) {
    var link = messageEl.querySelector(".reveal-link");
    if (!link) return;
    link.addEventListener("click", function (ev) {
      ev.preventDefault();
      window.pywebview.api.reveal_folder(path);
    });
  }

  function showDownloadSuccess(result) {
    var path = result.output_dir || outputDir || "";
    var label = t("messages.savedTo") || "Saved to: ";
    var linkTxt = t("showInFinder") || "Show in Finder";
    var html = label + "<strong>" + escHtml(path) + "</strong>"
      + " &mdash; <a href=\"#\" class=\"reveal-link\">" + escHtml(linkTxt) + "</a>";
    showMessage(html, "success");
    attachRevealLink(path);
  }

  function showTranscriptionSuccess(result) {
    var path = result.output_dir || outputDir || "";
    var label = t("messages.transcriptSavedTo") || "Transcript saved to: ";
    var filesLabel = t("messages.filesCreated") || "Files: ";
    var languageLabel = t("messages.detectedLanguage") || "Detected language: ";
    var linkTxt = t("showInFinder") || "Show in Finder";
    var parts = [
      label + "<strong>" + escHtml(path) + "</strong>"
    ];
    if (result.files && result.files.length) {
      parts.push(filesLabel + escHtml(result.files.join(", ")));
    }
    if (result.language) {
      parts.push(languageLabel + "<strong>" + escHtml(result.language) + "</strong>");
    }
    parts.push("<a href=\"#\" class=\"reveal-link\">" + escHtml(linkTxt) + "</a>");
    showMessage(parts.join("<br />"), "success");
    attachRevealLink(path);
  }





  function submitDownload() {
    var url = urlInput.value.trim();
    var formatEl = document.getElementById("format");
    var format = formatEl ? (formatEl.value || "mp4").toLowerCase() : "mp4";
    var playlist = document.getElementById("playlist").checked;

    return window.pywebview.api.download(url, format, playlist, outputDir).then(function (result) {
      if (!result || !result.success) {
        throw new Error((result && result.error) || (t("messages.genericError") || "Something went wrong."));
      }
      showDownloadSuccess(result);
    });
  }

  function submitTranscription() {
    var sourceType = transcribeSourceEl ? transcribeSourceEl.value : "youtube";
    var sourceValue = sourceType === "file" ? audioFilePath : urlInput.value.trim();
    var modelName = transcribeModelEl ? transcribeModelEl.value : defaultTranscribeModel;

    var model = getSelectedModel();
    if (model && !model.installed) {
      showMessage(escHtml(t("messages.downloadingModel") || "Downloading the transcription model. This may take a few minutes on first use."), "info");
    }

    return window.pywebview.api.transcribe(sourceType, sourceValue, modelName, outputDir).then(function (result) {
      if (!result || !result.success) {
        throw new Error((result && result.error) || (t("messages.transcribeFailed") || "Transcription failed"));
      }
      var modelData = getSelectedModel();
      if (modelData && !modelData.installed) {
        modelData.installed = true;
        refreshModelOptions(modelName);
      }
      showTranscriptionSuccess(result);
    });
  }

  function applyLanguage(lang) {
    if (!translations[lang]) lang = "en";
    currentLang = lang;
    try { localStorage.setItem("yt_downloader_lang", lang); } catch (e) { }

    var htmlEl = document.documentElement;
    if (htmlEl) htmlEl.lang = lang === "zh-TW" ? "zh-Hant" : "en";

    var titleEl = document.querySelector(".title");
    if (titleEl) titleEl.textContent = t("title") || "YT Downloader";

    var taglineEl = document.querySelector(".tagline");
    if (taglineEl) taglineEl.textContent = t("tagline") || "";

    var actionLabelEl = document.querySelector("label[for='mode']");
    if (actionLabelEl) actionLabelEl.textContent = t("actionLabel") || "Action";

    if (modeEl && modeEl.options.length >= 2) {
      modeEl.options[0].textContent = t("actions.download") || "Download";
      modeEl.options[1].textContent = t("actions.transcribe") || "Transcribe";
    }

    var transcribeSourceLabelEl = document.querySelector("label[for='transcribe-source']");
    if (transcribeSourceLabelEl) transcribeSourceLabelEl.textContent = t("transcribeSourceLabel") || "Transcribe from";
    if (transcribeSourceEl && transcribeSourceEl.options.length >= 2) {
      transcribeSourceEl.options[0].textContent = t("transcribeSources.youtube") || "YouTube URL";
      transcribeSourceEl.options[1].textContent = t("transcribeSources.file") || "Audio file";
    }

    var audioFileLabelEl = document.querySelector("label[for='audio-file']");
    if (audioFileLabelEl) audioFileLabelEl.textContent = t("audioFileLabel") || "Audio file";
    if (audioFileInput) audioFileInput.placeholder = t("audioFilePlaceholder") || "Choose an audio or video file";
    if (audioBrowseBtn) audioBrowseBtn.textContent = t("browseAudioButton") || "Browse\u2026";

    var formatLabelEl = document.querySelector("label[for='format']");
    if (formatLabelEl) formatLabelEl.textContent = t("formatLabel") || "Format";

    var modelLabelEl = document.querySelector("label[for='transcribe-model']");
    if (modelLabelEl) modelLabelEl.textContent = t("modelLabel") || "Model";

    var outputDirLabelEl = document.querySelector("label[for='output-dir']");
    if (outputDirLabelEl) outputDirLabelEl.textContent = t("outputDirLabel") || "Save to";
    if (browseBtn) browseBtn.textContent = t("browseButton") || "Browse\u2026";

    var playlistLabelEl = document.querySelector(".toggle-label");
    if (playlistLabelEl) playlistLabelEl.textContent = t("playlistLabel") || "Download full playlist";
    var playlistHintEl = document.querySelector(".playlist-field .hint");
    if (playlistHintEl) playlistHintEl.textContent = t("playlistHint") || "";

    var footerTextEl = document.querySelector(".footer p");
    if (footerTextEl) footerTextEl.textContent = t("footerText") || "";

    Array.prototype.forEach.call(langButtons, function (btn) {
      btn.classList.toggle("is-active", (btn.getAttribute("data-lang") || "en") === lang);
    });

    refreshModelOptions(transcribeModelEl ? transcribeModelEl.value : defaultTranscribeModel);
    updateModeUI();
  }

  if (browseBtn) {
    browseBtn.addEventListener("click", function () {
      window.pywebview.api.pick_folder().then(function (path) {
        if (path) setOutputDir(path);
      });
    });
  }

  if (audioBrowseBtn) {
    audioBrowseBtn.addEventListener("click", function () {
      window.pywebview.api.pick_audio_file().then(function (path) {
        if (path) {
          setAudioFile(path);
          hideMessage();
          validateForm();
        }
      });
    });
  }

  if (modeEl) {
    modeEl.addEventListener("change", function () {
      hideMessage();
      updateModeUI();
    });
  }

  if (transcribeSourceEl) {
    transcribeSourceEl.addEventListener("change", function () {
      hideMessage();
      updateModeUI();
    });
  }

  if (transcribeModelEl) {
    transcribeModelEl.addEventListener("change", function () {
      updateModelHint();
    });
  }

  urlInput.addEventListener("input", function () {
    hideMessage();
    validateForm();
  });

  urlInput.addEventListener("paste", function () {
    setTimeout(validateForm, 0);
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    hideMessage();

    if (usesAudioFile()) {
      if (!audioFilePath) {
        showMessage(escHtml(t("messages.chooseAudioFile") || "Please choose an audio or video file."), "error");
        return;
      }
    } else if (!urlInput.value.trim()) {
      showMessage(escHtml(t("messages.enterUrl") || "Please enter a URL."), "error");
      return;
    }

    setLoading(true);
    var runner = isTranscribeMode() ? submitTranscription() : submitDownload();
    Promise.resolve(runner)
      .catch(function (err) {
        showMessage(escHtml((err && err.message) || (t("messages.genericError") || "Something went wrong.")), "error");
      })
      .finally(function () {
        setLoading(false);
      });
  });

  Array.prototype.forEach.call(langButtons, function (btn) {
    btn.addEventListener("click", function () {
      applyLanguage(btn.getAttribute("data-lang") || "en");
    });
  });

  function init() {
    applyLanguage(currentLang);

    window.pywebview.api.get_app_state().then(function (state) {
      if (!state) return;

      if (state.version) {
        var versionEl = document.getElementById("version");
        if (versionEl && state.version.current) versionEl.textContent = "v" + state.version.current;
      }

      if (state.default_output_dir) {
        setOutputDir(state.default_output_dir);
      } else if (outputDirInput && !outputDir) {
        outputDirInput.placeholder = "~/Downloads";
      }

      if (state.transcription) {
        defaultTranscribeModel = state.transcription.default_model || defaultTranscribeModel;
        sttModels = state.transcription.models || [];
        refreshModelOptions(defaultTranscribeModel);
      }

      updateModeUI();
      validateForm();
      _initialized = true;
    }).catch(function () {
      validateForm();
      _initialized = true;
    });
  }

  window.addEventListener("pywebviewready", init);

  if (window.pywebview) {
    init();
  }
})();
