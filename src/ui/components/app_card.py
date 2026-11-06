"""
app_card.py — Unified App Row Card Component for Aero Suite.
Renders consistent, high-performance horizontal cards for:
- "install": Checkbox, Name, Package, Auto-Launch, Force Portrait, Block Boot, Target (User/System), Size
- "uninstall": Checkbox, Name, Package, Size
- "open": Single-select Checkbox, Name, Package, Size
"""
import re
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QCheckBox, QComboBox
import theme


def detect_variant_lang(filename: str) -> str:
    """Detects ISO language code token from APK filename."""
    fn = filename.lower()
    if re.search(r'(?:^|[\-_.\(\)\[\]\s])(ar|arabic|عربي)(?:[\-_.\(\)\[\]\s]|$)', fn):
        return 'ar'
    if re.search(r'(?:^|[\-_.\(\)\[\]\s])(en|english)(?:[\-_.\(\)\[\]\s]|$)', fn):
        return 'en'
    if re.search(r'(?:^|[\-_.\(\)\[\]\s])(zh|chinese|cn)(?:[\-_.\(\)\[\]\s]|$)', fn):
        return 'zh'
    if re.search(r'(?:^|[\-_.\(\)\[\]\s])(ru|russian)(?:[\-_.\(\)\[\]\s]|$)', fn):
        return 'ru'
    if re.search(r'(?:^|[\-_.\(\)\[\]\s])(es|spanish|espanol|español)(?:[\-_.\(\)\[\]\s]|$)', fn):
        return 'es'
    if re.search(r'(?:^|[\-_.\(\)\[\]\s])(vi|vietnamese|viet)(?:[\-_.\(\)\[\]\s]|$)', fn):
        return 'vi'
    if re.search(r'(?:^|[\-_.\(\)\[\]\s])(pt|portuguese|brasil|brazil)(?:[\-_.\(\)\[\]\s]|$)', fn):
        return 'pt'
    return ''


def extract_version_tuple(filename: str) -> tuple:
    """Extracts semantic version tuple from filename for version comparison."""
    matches = re.findall(r'(?:v|ver|version)?\s*(\d+(?:\.\d+)+)', filename, re.IGNORECASE)
    if matches:
        best = max(matches, key=lambda m: tuple(int(x) if x.isdigit() else 0 for x in m.split('.')))
        try:
            return tuple(int(x) for x in best.split('.'))
        except Exception:
            pass
    return (0,)


def extract_version_str(filename: str) -> str:
    """Extracts displayable version string from filename."""
    matches = re.findall(r'(?:v|ver|version)?\s*(\d+(?:\.\d+)+)', filename, re.IGNORECASE)
    if matches:
        return max(matches, key=lambda m: tuple(int(x) if x.isdigit() else 0 for x in m.split('.')))
    return ''


def clean_variant_title(name: str) -> str:
    """Strips common variant identifiers (lang tokens, version tags) from display name for grouped card header."""
    c = re.sub(r'(?i)\b(ar|en|zh|ru|es|vi|pt|arabic|english|chinese|russian|spanish|vietnamese|portuguese)\b', '', name)
    c = re.sub(r'(?i)\bv?\d+(?:\.\d+)+\b', '', c)
    c = re.sub(r'\s+', ' ', c).strip()
    return c or name


def variant_sort_key(item: dict, active_lang: str = "ar") -> tuple:
    """Priority sorting key: matching locale first, then semantic version, then size."""
    fname = item.get("filename", "")
    lang = detect_variant_lang(fname)
    if lang:
        if lang == active_lang:
            lang_prio = 100
        elif active_lang == "ar" and lang != "ar":
            lang_prio = 10
        elif active_lang != "ar" and lang == "en":
            lang_prio = 80
        else:
            lang_prio = 20
    else:
        lang_prio = 50
    ver = extract_version_tuple(fname)
    size = item.get("size_mb", 0)
    return (lang_prio, ver, size)


def get_variant_short_label(item: dict, is_top: bool = False, active_lang: str = "ar") -> str:
    """Builds concise text for variant dropdown."""
    fname = item.get("filename", "")
    lang = detect_variant_lang(fname)
    ver = extract_version_str(fname)
    ver_str = f" v{ver}" if ver else ""
    if lang == "ar":
        return f"عربي{ver_str}"
    elif lang == "en":
        return ("إنجليزي" if active_lang == "ar" else "English") + ver_str
    elif lang == "zh":
        return f"中文{ver_str}"
    elif lang == "ru":
        return f"Русский{ver_str}"
    elif lang == "es":
        return f"Español{ver_str}"
    elif lang == "vi":
        return f"Tiếng Việt{ver_str}"
    elif lang == "pt":
        return f"Português{ver_str}"
    elif ver:
        return f"v{ver}"
    return item.get("display_name", fname)[:14]


class AppCard(QFrame):
    """Interactive card representing an application row."""
    def __init__(self, mode: str, app_data: dict, parent=None, variants: list = None, on_variant_changed=None):
        super().__init__(parent)
        self.mode = mode
        self.variants = variants if (variants and len(variants) > 1) else [app_data]
        self.on_variant_changed = on_variant_changed
        self.combo_variant = None

        self.active_variant = self.variants[0]
        self.app_data = self.active_variant
        self.fname = self.active_variant.get("filename", "")
        self.pkg = self.active_variant.get("package", "")

        if len(self.variants) > 1:
            self.disp_name = clean_variant_title(self.active_variant.get("display_name", self.fname))
        else:
            self.disp_name = self.active_variant.get("display_name", self.fname)

        self.size_mb = self.active_variant.get("size_mb", 0)

        self.setProperty("class", "card")
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)

        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)

        # 1. Main Checkbox
        self.chk_main = QCheckBox()
        self.chk_main.setCursor(Qt.PointingHandCursor)
        self.chk_main.setStyleSheet("background-color: transparent; border: none;")
        layout.addWidget(self.chk_main)

        # 2. App Display Name
        max_name_len = 20 if len(self.variants) > 1 else 26
        name_text = self.disp_name[:max_name_len] + "…" if len(self.disp_name) > max_name_len else self.disp_name
        self.lbl_name = QLabel(name_text)
        self.lbl_name.setStyleSheet(
            f"font-weight: bold; font-size: 12px; color: {theme.TEXT_PRIMARY}; "
            "background-color: transparent; border: none;"
        )
        self.lbl_name.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_name)

        # 3. Package Name
        max_pkg_len = 22 if len(self.variants) > 1 else 30
        pkg_text = f"({self.pkg[:max_pkg_len]}…)" if len(self.pkg) > max_pkg_len else f"({self.pkg})"
        self.lbl_pkg = QLabel(pkg_text)
        self.lbl_pkg.setStyleSheet(
            f"font-size: 10px; color: {theme.TEXT_MUTED}; font-family: Consolas, monospace; "
            "background-color: transparent; border: none;"
        )
        self.lbl_pkg.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_pkg)

        # 4. Variant Selector Dropdown (only in install mode when multiple variants exist)
        if self.mode == "install" and len(self.variants) > 1:
            from core.i18n import get_i18n
            active_lang = get_i18n().current_lang

            self.combo_variant = QComboBox()
            self.combo_variant.setObjectName("comboVariant")
            self.combo_variant.setFixedWidth(128)
            self.combo_variant.setFixedHeight(22)
            self.combo_variant.setCursor(Qt.PointingHandCursor)

            labels = []
            seen = {}
            for i, v in enumerate(self.variants):
                base_lbl = get_variant_short_label(v, is_top=(i == 0), active_lang=active_lang)
                if base_lbl in seen:
                    seen[base_lbl] += 1
                    lbl = f"{base_lbl} ({seen[base_lbl]})"
                else:
                    seen[base_lbl] = 1
                    lbl = base_lbl
                labels.append(lbl)

            for lbl, v in zip(labels, self.variants):
                self.combo_variant.addItem(lbl, v.get("filename", ""))

            self.combo_variant.currentIndexChanged.connect(self._on_variant_index_changed)
            layout.addWidget(self.combo_variant)
            layout.addSpacing(6)

        self.setToolTip(f"{self.disp_name}\n{self.pkg}\n{self.fname}\n{self.size_mb} MB")
        layout.addStretch()

        # Mode-specific right controls
        if self.mode == "install":
            from core.i18n import t

            # Auto Launch Checkbox (Run Upon Install)
            self.chk_auto = QCheckBox(t("card.auto_launch", "Run Upon Install"))
            self.chk_auto.setToolTip(t("card.auto_launch_tooltip", "Run Upon Install: Launches the application once immediately after installation to verify it works."))
            self.chk_auto.setCursor(Qt.PointingHandCursor)
            self.chk_auto.setStyleSheet(
                f"font-size: 11px; font-weight: normal; color: {theme.TEXT_PRIMARY}; "
                "background-color: transparent; border: none;"
            )
            layout.addWidget(self.chk_auto)
            layout.addSpacing(14)

            # Force Portrait Checkbox
            self.chk_port = QCheckBox(t("card.force_portrait", "Force Portrait"))
            self.chk_port.setToolTip(t("card.force_portrait_tooltip", "Force Portrait: Patches binary Manifest to lock landscape or rotated apps into proper portrait mode for car screens."))
            self.chk_port.setCursor(Qt.PointingHandCursor)
            self.chk_port.setStyleSheet(
                f"font-size: 11px; font-weight: normal; color: {theme.TEXT_PRIMARY}; "
                "background-color: transparent; border: none;"
            )
            layout.addWidget(self.chk_port)
            layout.addSpacing(14)

            # Block Boot Launch Checkbox (Block Autostart)
            self.chk_boot = QCheckBox(t("card.block_boot", "Block Autostart"))
            self.chk_boot.setToolTip(t("card.block_boot_tooltip", "Block Autostart: Disables boot receiver components to prevent the app from auto-starting in background when vehicle turns on."))
            self.chk_boot.setCursor(Qt.PointingHandCursor)
            self.chk_boot.setStyleSheet(
                f"font-size: 11px; font-weight: normal; color: {theme.TEXT_PRIMARY}; "
                "background-color: transparent; border: none;"
            )
            layout.addWidget(self.chk_boot)
            layout.addSpacing(14)

            # Target Dropdown (User App vs System App)
            self.combo_target = QComboBox()
            self.combo_target.setObjectName("comboTarget")
            self.combo_target.setFixedWidth(102)
            self.combo_target.setFixedHeight(22)
            self.combo_target.setCursor(Qt.PointingHandCursor)
            self.combo_target.addItems([t("card.target_user", "User App"), t("card.target_system", "System App")])
            self.combo_target.setToolTip(t("card.target_tooltip", "Target partition: User App (/data/app) vs System App (/system/app)"))
            layout.addWidget(self.combo_target)
            layout.addSpacing(14)

        # File/Package Size Label
        self.lbl_size = QLabel(f"{self.size_mb} MB")
        self.lbl_size.setStyleSheet(
            f"font-size: 10px; font-family: Consolas, monospace; font-weight: bold; "
            f"color: {theme.TEXT_MUTED}; background-color: transparent; border: none;"
        )
        self.lbl_size.setFixedWidth(65)
        self.lbl_size.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_size.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_size)

    def _on_variant_index_changed(self, index: int):
        if 0 <= index < len(self.variants):
            old_fname = self.fname
            self.active_variant = self.variants[index]
            self.app_data = self.active_variant
            self.fname = self.active_variant.get("filename", "")
            self.size_mb = self.active_variant.get("size_mb", 0)
            self.lbl_size.setText(f"{self.size_mb} MB")
            self.setToolTip(f"{self.disp_name}\n{self.pkg}\n{self.fname}\n{self.size_mb} MB")
            if self.on_variant_changed:
                self.on_variant_changed(self, old_fname, self.fname)

    def set_active_variant_by_filename(self, filename: str):
        """Programmatically sets the active variant dropdown to match a specific filename."""
        if not self.combo_variant or not self.variants:
            return
        for idx, v in enumerate(self.variants):
            if v.get("filename") == filename:
                self.combo_variant.blockSignals(True)
                self.combo_variant.setCurrentIndex(idx)
                self.combo_variant.blockSignals(False)
                self.active_variant = v
                self.app_data = v
                self.fname = filename
                self.size_mb = v.get("size_mb", 0)
                self.lbl_size.setText(f"{self.size_mb} MB")
                self.setToolTip(f"{self.disp_name}\n{self.pkg}\n{self.fname}\n{self.size_mb} MB")
                break

    def set_selected_visual(self, is_selected: bool):
        """Updates card border and background glow based on selection."""
        if is_selected:
            self.setStyleSheet(f"""
                QFrame[class="card"] {{
                    background-color: {theme.SURFACE_2};
                    border: 1px solid {theme.CYAN_PRIMARY};
                    border-radius: 6px;
                }}
            """)
        else:
            self.setStyleSheet("")
