"""
paths.py — Centralized Path Resolution for Aero Suite.
Resolves runtime directories accurately in both development mode and compiled
executables (PyInstaller / Nuitka standalone builds).
"""
import os
import sys


def get_base_dir() -> str:
    """Returns the application base directory across development and frozen environments."""
    if getattr(sys, 'frozen', False) or "__compiled__" in globals() or hasattr(sys, '__nuitka_version__'):
        if sys.argv and sys.argv[0]:
            candidate = os.path.dirname(os.path.abspath(sys.argv[0]))
            if os.path.exists(os.path.join(candidate, "apks")):
                return candidate
        if sys.executable:
            candidate = os.path.dirname(os.path.abspath(sys.executable))
            if os.path.exists(os.path.join(candidate, "apks")):
                return candidate
        if sys.argv and sys.argv[0]:
            return os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.dirname(os.path.abspath(sys.executable))

    # In development: src/core/paths.py -> src -> project root
    core_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(core_dir)
    return os.path.dirname(src_dir) if os.path.basename(src_dir).lower() == "src" else src_dir


BASE_DIR = get_base_dir()
APKS_DIR = os.path.join(BASE_DIR, "apks")
GMS_DIR = os.path.join(APKS_DIR, "google_services")
SYSTEM_MODS_DIR = os.path.join(APKS_DIR, "system_mods")
AEROBAR_APK = os.path.join(SYSTEM_MODS_DIR, "AeroBar.apk")
HVAC_MOD_APK = os.path.join(SYSTEM_MODS_DIR, "AeroBar.apk") if os.path.isfile(os.path.join(SYSTEM_MODS_DIR, "AeroBar.apk")) else os.path.join(SYSTEM_MODS_DIR, "SystemUI_mod_160px.apk")
HVAC_STOCK_APK = os.path.join(SYSTEM_MODS_DIR, "SystemUI_stock_200px.apk")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")
FACTORY_BACKUP_DIR = os.path.join(BASE_DIR, "FactoryBackup")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
def _resolve_templates_dir() -> str:
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"),
        os.path.join(BASE_DIR, "templates"),
        os.path.join(BASE_DIR, "src", "templates"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]


TEMPLATES_DIR = _resolve_templates_dir()
