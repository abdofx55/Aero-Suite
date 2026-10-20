# AeroSuite.spec
# PyInstaller configuration for Aero Automotive Suite — Dongfeng Edition.
# Developed & Maintained by Abdelrhman Hamdy - Senior Software Engineer.

import os
from PyInstaller.utils.hooks import collect_data_files

base_dir = os.path.abspath(".")
datas = collect_data_files("customtkinter")

binaries = []
for fname in ("adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll"):
    fpath = os.path.join(base_dir, fname)
    if os.path.exists(fpath):
        binaries.append((fpath, "."))

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=["src", "."],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        "customtkinter",
        "tkinter",
        "tkinter.messagebox",
        "PIL",
        "PIL._tkinter_finder",
        "apk_engine",
        "usb_detector",
        "sync_manager",
        "payload_engine",
        "theme",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "numpy", "scipy", "pandas",
        "IPython", "jupyter", "notebook",
        "PyQt5", "PyQt6", "wx",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AeroSuite",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)
