"""Single source of truth for app version and GitHub update check."""
from __future__ import annotations

import json
import re
import ssl
import threading
from urllib.request import Request, urlopen

__version__ = "2.1.1"

GITHUB_REPO = "willwang0202/YT-Downloader"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"

# In-memory cache for the latest release (avoid hitting API every time)
_cached: dict | None = None


def _parse_version(s: str) -> tuple[int, ...]:
    """Convert version string to comparable tuple (e.g. 'v1.2.3' -> (1, 2, 3))."""
    s = re.sub(r"^v", "", str(s).strip())
    parts = re.split(r"[.-]", s)
    out = []
    for p in parts[:4]:  # max 4 parts (e.g. 1.2.3.4)
        try:
            out.append(int(p))
        except ValueError:
            out.append(0)
    return tuple(out)


def _is_newer(latest: str, current: str) -> bool:
    """Return True if latest > current."""
    return _parse_version(latest) > _parse_version(current)


def check_github_update() -> dict:
    """
    Fetch latest release from GitHub and compare with current version.
    Returns dict: { "current", "latest" | None, "update_available": bool, "release_url": str }
    """
    global _cached
    result = {
        "current": __version__,
        "latest": None,
        "update_available": False,
        "release_url": RELEASE_URL,
    }
    try:
        ctx = ssl.create_default_context()
        req = Request(GITHUB_API_LATEST, headers={"Accept": "application/json"})
        with urlopen(req, timeout=5, context=ctx) as resp:
            data = json.loads(resp.read().decode())
        tag = data.get("tag_name") or ""
        latest = re.sub(r"^v", "", tag).strip()
        if latest:
            result["latest"] = latest
            result["update_available"] = _is_newer(latest, __version__)
            _cached = result
    except Exception:
        if _cached is not None:
            return _cached
    return result


def check_github_update_cached() -> dict:
    """Return cached result if recent; otherwise fetch and cache."""
    if _cached is not None:
        return _cached
    return check_github_update()


def print_update_if_available() -> None:
    """Non-blocking: in a background thread, check for update and print one line if available."""
    def _run() -> None:
        try:
            r = check_github_update()
            if r.get("update_available") and r.get("latest"):
                print(f"Update available: v{r['latest']} — {RELEASE_URL}")
        except Exception:
            pass
    t = threading.Thread(target=_run, daemon=True)
    t.start()
