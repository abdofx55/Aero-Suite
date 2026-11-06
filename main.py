"""
main.py — Main Entry Point for Aero Suite
Automotive APK & System Studio — Dongfeng Shine Edition
"""
import os
import sys

# Ensure src directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Switch between PySide6 (New Ultra-Fast GUI) and CustomTkinter (Legacy GUI)
USE_LEGACY_CTK = "--ctk" in sys.argv or os.environ.get("AERO_UI", "").lower() == "ctk"

if USE_LEGACY_CTK:
    import importlib
    legacy_dir = os.path.join(BASE_DIR, "legacy")
    if legacy_dir not in sys.path:
        sys.path.insert(0, legacy_dir)
    app_gui = importlib.import_module("app_gui")
    if __name__ == "__main__":
        app = app_gui.AeroSuiteApp()
        app.mainloop()
else:
    from PySide6.QtWidgets import QApplication
    from core.exceptions import setup_global_exception_handler
    from qt_app_gui import AeroSuiteQtApp

    if __name__ == "__main__":
        setup_global_exception_handler()
        app = QApplication(sys.argv)
        from core.i18n import get_i18n
        from PySide6.QtCore import Qt
        if get_i18n().is_rtl():
            app.setLayoutDirection(Qt.RightToLeft)
        # Eliminate OS window animation desync / flickering with custom styled widgets
        app.setEffectEnabled(Qt.UIEffect.UI_AnimateCombo, False)
        window = AeroSuiteQtApp()
        window.showMaximized()
        sys.exit(app.exec())
