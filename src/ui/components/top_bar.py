"""
top_bar.py — Aero Suite Top Navigation Bar Component.
Provides IVI Studio branding, app version badge, multi-language selector (EN, AR, ZH, RU),
USB drive selection, refresh, and tools menu.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QWidget, QHBoxLayout, QLabel, QPushButton, QComboBox, QMenu
)
from PySide6.QtGui import QCursor
import theme
from core.i18n import t, get_i18n, SUPPORTED_LANGUAGES


class TopBarWidget(QFrame):
    """Header panel managing brand identity, language selection, and USB target selection."""
    usb_selected = Signal(int)
    refresh_requested = Signal()
    menu_requested = Signal(bool)
    language_selected = Signal(str)
    basket_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._basket_count = 0
        self.setObjectName("topBarPanel")
        self.setFixedHeight(65)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)

        # Brand & Subtitle
        brand_box = QHBoxLayout()
        brand_box.setSpacing(10)
        self.lbl_title = QLabel(t("app.title", "⚡ AERO SUITE"))
        self.lbl_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme.CYAN_PRIMARY}; letter-spacing: 1px;")
        brand_box.addWidget(self.lbl_title)

        lbl_badge = QLabel(f"v{theme.APP_VERSION}")
        lbl_badge.setFixedHeight(28)
        lbl_badge.setAlignment(Qt.AlignCenter)
        lbl_badge.setStyleSheet(
            f"background-color: {theme.CYAN_ALPHA_15}; color: {theme.CYAN_PRIMARY}; "
            f"border: 1px solid {theme.BORDER_CYAN}; border-radius: 6px; padding: 0 10px; "
            f"font-size: 11px; font-weight: bold;"
        )
        brand_box.addWidget(lbl_badge)

        self.lbl_sub = QLabel(t("app.subtitle", "Advanced Dongfeng IVI Studio"))
        brand_box.addWidget(self.lbl_sub)
        layout.addLayout(brand_box)

        layout.addStretch()

        # Action Controls Box
        controls_box = QHBoxLayout()
        controls_box.setSpacing(8)

        # 1. USB Controls: Status Dot + Combo + Refresh
        self.usb_status_dot = QLabel("●")
        self.usb_status_dot.setObjectName("usbStatusDot")
        self.usb_status_dot.setStyleSheet(f"color: {theme.CRIMSON_DANGER}; font-size: 16px;")
        self.usb_status_dot.setToolTip(t("app.no_usb_tooltip", "No USB Flash Drive Detected"))
        controls_box.addWidget(self.usb_status_dot)

        from qt_theme import configure_smooth_combobox

        self.usb_combo = QComboBox()
        self.usb_combo.setObjectName("usbCombo")
        self.usb_combo.setFixedWidth(290)
        self.usb_combo.setFixedHeight(32)
        self.usb_combo.setCursor(Qt.PointingHandCursor)
        configure_smooth_combobox(self.usb_combo)
        self.usb_combo.setContextMenuPolicy(Qt.CustomContextMenu)
        self.usb_combo.customContextMenuRequested.connect(lambda pt: self.menu_requested.emit(False))
        self.usb_combo.currentIndexChanged.connect(self.usb_selected.emit)
        controls_box.addWidget(self.usb_combo)

        self.btn_refresh_usb = QPushButton(t("common.refresh", "🔄 Refresh"))
        self.btn_refresh_usb.setObjectName("btnRefreshUsb")
        self.btn_refresh_usb.setFixedHeight(32)
        self.btn_refresh_usb.setFixedWidth(115)
        self.btn_refresh_usb.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_usb.setToolTip(t("app.refresh_usb_tip", "Refresh & Rescan USB Flash Drives"))
        self.btn_refresh_usb.clicked.connect(self.refresh_requested.emit)
        controls_box.addWidget(self.btn_refresh_usb)

        # 1.5. Basket Button
        self.btn_basket = QPushButton("🛒 0")
        self.btn_basket.setObjectName("btnBasket")
        self.btn_basket.setFixedHeight(32)
        self.btn_basket.setCursor(Qt.PointingHandCursor)
        self.btn_basket.setToolTip(t("basket.tooltip", "Multi-Command Basket — View queued operations"))
        self._update_basket_style(0)
        self.btn_basket.clicked.connect(self.basket_clicked.emit)
        controls_box.addWidget(self.btn_basket)

        # 2. Language Selector Dropdown (with prominent 🌐 globe indicator)
        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("langCombo")
        self.lang_combo.setFixedHeight(32)
        self.lang_combo.setFixedWidth(135)
        self.lang_combo.setCursor(Qt.PointingHandCursor)
        configure_smooth_combobox(self.lang_combo)
        self.lang_combo.setToolTip("Select Language / اختر اللغة / 选择语言 / Выберите язык / Seleccionar idioma")

        for code, meta in SUPPORTED_LANGUAGES.items():
            flag = meta.get("flag", "")
            native = meta.get("native", code)
            label = f"{flag} {native}".strip()
            self.lang_combo.addItem(label, userData=code)

        cur_lang = get_i18n().current_lang
        idx = list(SUPPORTED_LANGUAGES.keys()).index(cur_lang) if cur_lang in SUPPORTED_LANGUAGES else 0
        self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        controls_box.addWidget(self.lang_combo)

        # 3. Settings & Tools Button ⚙️ (Anchor button at the outer edge)
        self.btn_usb_settings = QPushButton("⚙️")
        self.btn_usb_settings.setObjectName("btnUsbSettings")
        self.btn_usb_settings.setFixedSize(32, 32)
        self.btn_usb_settings.setCursor(Qt.PointingHandCursor)
        self.btn_usb_settings.setToolTip(t("app.usb_tools_tip", "Flash Drive Settings & Tools (Open in Explorer, Format FAT32, Rescan)"))
        self.btn_usb_settings.clicked.connect(lambda: self.menu_requested.emit(True))
        controls_box.addWidget(self.btn_usb_settings)

        layout.addLayout(controls_box)

    def update_basket_count(self, count: int):
        self._basket_count = count
        txt = t("basket.badge_count", f"🛒 ({count})", count=count) if count > 0 else "🛒 0"
        self.btn_basket.setText(txt)
        self._update_basket_style(count)

    def _update_basket_style(self, count: int):
        if count > 0:
            self.btn_basket.setStyleSheet(f"""
                QPushButton#btnBasket {{
                    background-color: {theme.CYAN_ALPHA_15};
                    color: {theme.CYAN_PRIMARY};
                    border: 1px solid {theme.CYAN_PRIMARY};
                    border-radius: 6px;
                    padding: 0 12px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                QPushButton#btnBasket:hover {{
                    background-color: {theme.CYAN_PRIMARY};
                    color: #000000;
                }}
            """)
        else:
            self.btn_basket.setStyleSheet(f"""
                QPushButton#btnBasket {{
                    background-color: {theme.SURFACE_2};
                    color: {theme.TEXT_MUTED};
                    border: 1px solid {theme.BORDER_SLATE};
                    border-radius: 6px;
                    padding: 0 12px;
                    font-size: 12px;
                }}
                QPushButton#btnBasket:hover {{
                    border-color: {theme.BORDER_CYAN};
                    color: {theme.TEXT_PRIMARY};
                }}
            """)

    def _on_lang_changed(self, index: int):
        lang_code = self.lang_combo.currentData()
        if lang_code:
            self.language_selected.emit(lang_code)

    def retranslate_ui(self):
        """Dynamically re-translates top bar elements."""
        self.lbl_title.setText(t("app.title", "⚡ AERO SUITE"))
        self.lbl_sub.setText(t("app.subtitle", "Advanced Dongfeng IVI Studio"))
        self.btn_refresh_usb.setText(t("common.refresh", "🔄 Refresh"))
        self.btn_refresh_usb.setToolTip(t("app.refresh_usb_tip", "Refresh & Rescan USB Flash Drives"))
        self.btn_usb_settings.setToolTip(t("app.usb_tools_tip", "Flash Drive Settings & Tools (Open in Explorer, Format FAT32, Rescan)"))
        self.btn_basket.setToolTip(t("basket.tooltip", "Multi-Command Basket — View queued operations"))
        self.update_basket_count(self._basket_count)
