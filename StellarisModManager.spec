# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path.cwd()


def collect_steamcmd_bundle(root: Path):
    steamcmd_datas = []
    if not root.exists():
        return steamcmd_datas

    steamcmd_executable = root / "steamcmd.exe"
    if steamcmd_executable.exists():
        steamcmd_datas.append((str(steamcmd_executable), "steamcmd"))

    return steamcmd_datas


common_datas = []
common_binaries = []
hiddenimports = [
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebChannel",
]
excluded_qt_bindings = [
    "PySide6.QtOpenGL",
    "PySide6.QtPositioning",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
]
webengine_locales = {
    "en-GB.pak",
    "en-US.pak",
    "zh-CN.pak",
    "zh-TW.pak",
}


def filter_qt_runtime_entries(entries):
    filtered = []
    for entry in entries:
        destination = str(entry[0]).replace("\\", "/")
        normalized = f"/{destination.lower()}"
        filename = Path(destination).name

        if "/pyside6/qml/" in normalized:
            continue
        if "/pyside6/resources/" in normalized and ".debug." in filename.lower():
            continue
        if "/pyside6/translations/qtwebengine_locales/" in normalized:
            if filename not in webengine_locales:
                continue
        elif "/pyside6/translations/" in normalized:
            continue

        filtered.append(entry)
    return filtered

steamcmd_root = project_root / "steamcmd"
if steamcmd_root.exists():
    common_datas += collect_steamcmd_bundle(steamcmd_root)


a_main = Analysis(
    ["gui.py"],
    pathex=[str(project_root)],
    binaries=common_binaries,
    datas=common_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_qt_bindings,
    noarchive=False,
    optimize=0,
)
a_main.binaries = filter_qt_runtime_entries(a_main.binaries)
a_main.datas = filter_qt_runtime_entries(a_main.datas)
pyz_main = PYZ(a_main.pure)

exe_main = EXE(
    pyz_main,
    a_main.scripts,
    [],
    exclude_binaries=True,
    name="StellarisModManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

a_updater = Analysis(
    ["updater_helper.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz_updater = PYZ(a_updater.pure)

exe_updater = EXE(
    pyz_updater,
    a_updater.scripts,
    [],
    exclude_binaries=True,
    name="StellarisModManagerUpdater",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe_main,
    exe_updater,
    a_main.binaries,
    a_main.datas,
    a_updater.binaries,
    a_updater.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="StellarisModManager",
)
