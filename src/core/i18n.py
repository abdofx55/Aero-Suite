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
    "ru": {"name": "Russian", "native": "Русский", "flag": "🇷🇺", "rtl": False},
    "es": {"name": "Spanish", "native": "Español", "flag": "🇪🇸", "rtl": False},
    "vi": {"name": "Vietnamese", "native": "Tiếng Việt", "flag": "🇻🇳", "rtl": False},
    "pt": {"name": "Portuguese", "native": "Português", "flag": "🇧🇷", "rtl": False}
}

DEFAULT_LANGUAGE = "ar"


def get_settings_file_path() -> str:
    import sys
    if getattr(sys, 'frozen', False) or "__compiled__" in globals() or hasattr(sys, '__nuitka_version__'):
        if sys.argv and sys.argv[0]:
            candidate = os.path.dirname(os.path.abspath(sys.argv[0]))
            return os.path.join(candidate, "app_settings.json")
        if sys.executable:
            return os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "app_settings.json")
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, "app_settings.json")


def is_onboarding_completed() -> bool:
    """Checks whether the first-run onboarding screen was already completed."""
    try:
        cfg_path = get_settings_file_path()
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return bool(data.get("onboarding_completed", False))
    except Exception:
        pass
    return False


def set_onboarding_completed(completed: bool = True):
    """Marks onboarding as completed in the persistent app_settings.json."""
    try:
        cfg_path = get_settings_file_path()
        data = {}
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["onboarding_completed"] = completed
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


class I18nManager(QObject):
    """Manages active locale, language catalogs, translation lookup, and RTL direction."""
    language_changed = Signal(str)

    def __init__(self, locales_dir: str = None):
        super().__init__()
        if not locales_dir:
            from core.paths import BASE_DIR
            candidates = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locales"),
                os.path.join(BASE_DIR, "locales"),
                os.path.join(BASE_DIR, "src", "locales"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales"),
            ]
            locales_dir = candidates[0]
            for cand in candidates:
                if os.path.exists(os.path.join(cand, "en.json")):
                    locales_dir = cand
                    break

        self.locales_dir = locales_dir
        self.catalogs = {}
        self.load_catalogs()

        # Determine initial language: saved preference -> default (en)
        saved = self._load_saved_language()
        if saved and saved in SUPPORTED_LANGUAGES:
            self.current_lang = saved
        else:
            self.current_lang = DEFAULT_LANGUAGE

    def _save_language(self, lang_code: str):
        try:
            cfg_path = get_settings_file_path()
            data = {}
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["language"] = lang_code
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _load_saved_language(self):
        try:
            cfg_path = get_settings_file_path()
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("language")
        except Exception:
            pass
        return None

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

    def set_language(self, lang_code: str, save: bool = True):
        """Changes active language and adjusts application layout direction (RTL/LTR)."""
        if lang_code not in SUPPORTED_LANGUAGES:
            lang_code = DEFAULT_LANGUAGE

        self.current_lang = lang_code
        if save:
            self._save_language(lang_code)
        is_rtl = SUPPORTED_LANGUAGES[lang_code]["rtl"]

        app = QApplication.instance()
        if app:
            app.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)

        self.language_changed.emit(lang_code)

    def is_rtl(self) -> bool:
        """Returns True if current language requires Right-To-Left layout."""
        return bool(SUPPORTED_LANGUAGES.get(self.current_lang, {}).get("rtl", False))


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


def is_rtl() -> bool:
    """Returns True if the current language requires Right-To-Left layout."""
    return get_i18n().is_rtl()


def get_current_locale() -> str:
    """Returns the current active language code (e.g. 'ar', 'en')."""
    return get_i18n().current_lang
