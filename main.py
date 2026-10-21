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
    from app_gui import AeroSuiteApp
    if __name__ == "__main__":
        app = AeroSuiteApp()
        app.mainloop()
else:
    from PySide6.QtWidgets import QApplication
    from qt_app_gui import AeroSuiteQtApp

    if __name__ == "__main__":
        app = QApplication(sys.argv)
        window = AeroSuiteQtApp()
        window.show()
        sys.exit(app.exec())
