"""
i18n.py — Internationalization (i18n) Manager for Aero Suite.
Supports English (Default/Fallback), Arabic (with RTL), Chinese, and Russian.
Provides dot-notation key lookup, string interpolation, and layout direction switching.
"""
import os
import json
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QApplication

SUPPORTED_LANGUAGES = {
    "en": {"name": "English", "native": "English", "flag": "🇺🇸", "rtl": False},
    "ar": {"name": "Arabic", "native": "العربية", "flag": "🇪🇬", "rtl": True},
    "zh": {"name": "Chinese", "native": "简体中文", "flag": "🇨🇳", "rtl": False},
    "ru": {"name": "Russian", "native": "Русский", "flag": "🇷🇺", "rtl": False}
}

DEFAULT_LANGUAGE = "en"


class I18nManager(QObject):
    """Manages active locale, language catalogs, translation lookup, and RTL direction."""
    language_changed = Signal(str)

    def __init__(self, locales_dir: str = None):
        super().__init__()
        if not locales_dir:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            locales_dir = os.path.join(base_dir, "locales")

        self.locales_dir = locales_dir
        self.current_lang = DEFAULT_LANGUAGE
        self.catalogs = {}
        self.load_catalogs()

    def load_catalogs(self):
        """Loads all supported language JSON files from locales directory."""
        self.catalogs = {}
        for lang_code in SUPPORTED_LANGUAGES:
            file_path = os.path.join(self.locales_dir, f"{lang_code}.json")
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self.catalogs[lang_code] = json.load(f)
                except Exception as e:
                    print(f"Error loading translation catalog '{lang_code}': {e}")
                    self.catalogs[lang_code] = {}
            else:
                self.catalogs[lang_code] = {}

    def get_text(self, key: str, default: str = None, **kwargs) -> str:
        """
        Retrieves localized text using dot-notation (e.g. 'install_apps.title').
        Falls back to English if missing in current language, then to default or key.
        Supports keyword formatting: get_text('install.count', count=3)
        """
        val = self._lookup_key(self.current_lang, key)
        if val is None and self.current_lang != DEFAULT_LANGUAGE:
            val = self._lookup_key(DEFAULT_LANGUAGE, key)

        if val is None:
            val = default if default is not None else key

        if kwargs and isinstance(val, str):
            try:
                val = val.format(**kwargs)
            except Exception:
                pass

        return str(val)

    def _lookup_key(self, lang_code: str, key: str):
        catalog = self.catalogs.get(lang_code, {})
        parts = key.split(".")
        cur = catalog
        for part in parts:
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return None
        return cur

    def set_language(self, lang_code: str):
        """Changes active language and adjusts application layout direction (RTL/LTR)."""
        if lang_code not in SUPPORTED_LANGUAGES:
            lang_code = DEFAULT_LANGUAGE

        self.current_lang = lang_code
        is_rtl = SUPPORTED_LANGUAGES[lang_code]["rtl"]

        app = QApplication.instance()
        if app:
            app.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)

        self.language_changed.emit(lang_code)


# Global singleton instance
_i18n_instance = None


def get_i18n() -> I18nManager:
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18nManager()
    return _i18n_instance


def t(key: str, default: str = None, **kwargs) -> str:
    """Convenience helper for translation lookup."""
    return get_i18n().get_text(key, default=default, **kwargs)
