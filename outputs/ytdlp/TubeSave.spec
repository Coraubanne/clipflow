from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules, copy_metadata


project = Path(SPECPATH)
datas = [
    (str(project / "assets" / "ClipFlow.png"), "assets"),
    (str(project / "native_host"), "ytdlp"),
]
binaries = []
hiddenimports = []

for package in ("yt_dlp", "yt_dlp_ejs", "imageio_ffmpeg", "certifi", "curl_cffi"):
    package_datas, package_binaries, package_imports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_imports

hiddenimports += collect_submodules("yt_dlp_plugins")
datas += collect_data_files("yt_dlp_plugins")
hiddenimports += [
    "native_host",
    "updater",
    "yt_dlp_plugins.extractor.webkit_jsi",
    "yt_dlp_plugins.extractor.ytjsc",
    "yt_dlp_plugins.webkit_jsi.lib.api",
    "yt_dlp_plugins.webkit_jsi.lib.consts",
    "yt_dlp_plugins.webkit_jsi.lib.easy",
    "yt_dlp_plugins.webkit_jsi.lib.logging",
    "yt_dlp_plugins.webkit_jsi.lib.pyneapple_objc",
]

for distribution in (
    "yt-dlp",
    "yt-dlp-ejs",
    "yt-dlp-apple-webkit-jsi",
    "imageio-ffmpeg",
    "certifi",
    "curl-cffi",
):
    datas += copy_metadata(distribution)

a = Analysis(
    [str(project / "app.py")],
    pathex=[str(project)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ClipFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ClipFlow",
)
app = BUNDLE(
    coll,
    name="ClipFlow.app",
    icon=str(project / "assets" / "ClipFlow.png"),
    bundle_identifier="fr.clipflow.app",
    version="2.11.0",
    info_plist={
        "CFBundleDisplayName": "ClipFlow",
        "CFBundleName": "ClipFlow",
        "CFBundleShortVersionString": "2.11.0",
        "CFBundleVersion": "54",
        "CFBundleDevelopmentRegion": "fr",
        "LSApplicationCategoryType": "public.app-category.utilities",
        "LSUIElement": True,
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
    },
)
