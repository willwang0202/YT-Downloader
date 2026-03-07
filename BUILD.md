# Building standalone .exe (Windows) and .app (macOS)

You need to build on each platform to get that platform’s binary: **.exe on Windows**, **.app on macOS**.

## Can I build .exe on my Mac?

**Not directly.** PyInstaller builds for the OS it runs on, so a Mac build produces a Mac app, not a Windows .exe.

**Options:**

1. **GitHub Actions (recommended)** — Push a version tag from your Mac; GitHub builds both the .exe and the .app and uploads them as artifacts:
   ```bash
   git tag v2.1.0
   git push origin v2.1.0
   ```
   Then open **Actions** → the “Build release” run → download **YT-Downloader-windows** (.exe) and **YT-Downloader-macos** (.app in a zip).

2. **Windows VM or PC** — Run Windows (e.g. in Parallels, VirtualBox, or another machine) and build there with the same steps below.

## Prerequisites

- **Python 3.10+** and pip
- Install PyInstaller:  
  `pip install pyinstaller`

## Build

1. Clone or download the repo and `cd` into it.
2. (Optional) Create a venv and install deps:  
   `pip install -r requirements.txt pyinstaller`
3. Run PyInstaller with the provided spec:

```bash
pyinstaller YT-Downloader.spec
```

- **On Windows:** output is `dist/YT-Downloader.exe` (single file).
- **On macOS:** output is `dist/YT-Downloader.app` (bundle).

## Attach to a GitHub release

1. Create a new release and tag (e.g. `v2.1.0`).
2. Attach:
   - `YT-Downloader.py` (from repo)
   - `dist/YT-Downloader.exe` (built on Windows)
   - `dist/YT-Downloader.app` (built on macOS; zip it first: `zip -r YT-Downloader-mac.zip dist/YT-Downloader.app`)
3. Paste the contents of `RELEASE_DESCRIPTION.md` as the release description.

## Version

The version is set in `version.py` and `YT-Downloader.py` (`__version__ = "2.1.0"`). Bump both when cutting a new release and update `YT-Downloader.spec`’s `CFBundleShortVersionString` / `CFBundleVersion` for the .app.
