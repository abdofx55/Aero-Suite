# -*- mode: python ; coding: utf-8 -*-
# AeroSuite.spec — Official PyInstaller configuration for Aero Automotive Suite v1.1 Beta
# Developed & Maintained by Abdelrhman Hamdy - Senior Software Engineer.

import os

base_dir = os.path.abspath(".")

datas = [
    (os.path.join(base_dir, "src", "locales"), "locales"),
    (os.path.join(base_dir, "src", "templates"), "templates"),
    (os.path.join(base_dir, "assets"), "assets"),
    (os.path.join(base_dir, "src", "ui", "assets"), "ui/assets"),
]

hidden_imports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "cryptography",
    "core",
    "ui",
    "services",
    "controllers",
    "payloads",
    "apk_engine",
    "payload_engine",
    "sync_manager",
    "usb_detector",
    "theme",
    "qt_theme",
    "qt_app_gui",
]

a = Analysis(
    ["main.py"],
    pathex=["src", "."],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "customtkinter", "matplotlib", "numpy", "scipy", "pandas",
        "IPython", "jupyter", "notebook", "PyQt5", "PyQt6", "wx",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AeroSuite",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
