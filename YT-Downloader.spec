# PyInstaller spec for YT-Downloader
# Build: pyinstaller YT-Downloader.spec
# Windows: dist/YT-Downloader.exe
# macOS:   dist/YT-Downloader.app

import sys

block_cipher = None
is_onefile = sys.platform == 'win32'  # one .exe on Windows; .app bundle on macOS

a = Analysis(
    ['YT-Downloader.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'yt_dlp',
        'certifi',
        'fastapi',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'pydantic',
        'pydantic_core',
        'starlette',
        'anyio',
        'click',
        'h11',
        'httptools',
        'watchfiles',
        'websockets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if is_onefile:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='YT-Downloader',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='YT-Downloader',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=True,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='YT-Downloader',
    )
    app = BUNDLE(
        coll,
        name='YT-Downloader.app',
        icon=None,
        bundle_identifier='com.ytdownloader.app',
        info_plist={
            'CFBundleName': 'YT-Downloader',
            'CFBundleDisplayName': 'YT Downloader',
            'CFBundleVersion': '2.1.0',
            'CFBundleShortVersionString': '2.1.0',
            'NSHighResolutionCapable': True,
        },
    )
