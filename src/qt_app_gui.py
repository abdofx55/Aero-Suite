"""
qt_app_gui.py — Backward-compatible facade for Aero Suite Qt Application.
Delegates to modular architecture under `src/ui/`.
"""
import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import (
    AeroSuiteQtApp,
    PayloadWorker,
    UsbSignalBridge,
    BASE_DIR,
    APKS_DIR,
    GMS_DIR,
    BACKUPS_DIR,
    FACTORY_BACKUP_DIR,
    LOGS_DIR,
    get_base_dir
)

__all__ = [
    "AeroSuiteQtApp",
    "PayloadWorker",
    "UsbSignalBridge",
    "BASE_DIR",
    "APKS_DIR",
    "GMS_DIR",
    "BACKUPS_DIR",
    "FACTORY_BACKUP_DIR",
    "LOGS_DIR",
    "get_base_dir",
    "main"
]


def main():
    app = QApplication(sys.argv)
    window = AeroSuiteQtApp()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
