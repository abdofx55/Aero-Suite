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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topBarPanel")
        self.setFixedHeight(65)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)

        # Brand & Subtitle
        brand_box = QHBoxLayout()
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

        self.lbl_sub = QLabel(t("app.subtitle", "Dongfeng Shine (Aeolus D53) IVI Studio"))
        self.lbl_sub.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED}; margin-left: 8px;")
        brand_box.addWidget(self.lbl_sub)
        layout.addLayout(brand_box)

        layout.addStretch()

        # Multi-Language Selector Dropdown
        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("langCombo")
        self.lang_combo.setFixedHeight(32)
        self.lang_combo.setFixedWidth(135)
        self.lang_combo.setCursor(Qt.PointingHandCursor)
        self.lang_combo.setToolTip("Select Language / اختر اللغة / 选择语言 / Выберите язык")

        for code, meta in SUPPORTED_LANGUAGES.items():
            self.lang_combo.addItem(f"{meta['flag']} {meta['native']}", userData=code)

        cur_lang = get_i18n().current_lang
        idx = list(SUPPORTED_LANGUAGES.keys()).index(cur_lang) if cur_lang in SUPPORTED_LANGUAGES else 0
        self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        layout.addWidget(self.lang_combo)

        # USB Controls Box
        usb_box = QHBoxLayout()
        usb_box.setSpacing(8)

        self.usb_status_dot = QLabel("●")
        self.usb_status_dot.setObjectName("usbStatusDot")
        self.usb_status_dot.setStyleSheet(f"color: {theme.CRIMSON_DANGER}; font-size: 16px;")
        self.usb_status_dot.setToolTip("No USB Flash Drive Detected")
        usb_box.addWidget(self.usb_status_dot)

        self.usb_combo = QComboBox()
        self.usb_combo.setObjectName("usbCombo")
        self.usb_combo.setFixedWidth(290)
        self.usb_combo.setFixedHeight(32)
        self.usb_combo.setCursor(Qt.PointingHandCursor)
        self.usb_combo.setContextMenuPolicy(Qt.CustomContextMenu)
        self.usb_combo.customContextMenuRequested.connect(lambda pt: self.menu_requested.emit(False))
        self.usb_combo.currentIndexChanged.connect(self.usb_selected.emit)
        usb_box.addWidget(self.usb_combo)

        self.btn_refresh_usb = QPushButton(t("common.refresh", "🔄 Refresh"))
        self.btn_refresh_usb.setObjectName("btnRefreshUsb")
        self.btn_refresh_usb.setFixedHeight(32)
        self.btn_refresh_usb.setFixedWidth(115)
        self.btn_refresh_usb.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_usb.setToolTip("Refresh & Rescan USB Flash Drives")
        self.btn_refresh_usb.clicked.connect(self.refresh_requested.emit)
        usb_box.addWidget(self.btn_refresh_usb)

        self.btn_usb_settings = QPushButton("⚙️")
        self.btn_usb_settings.setObjectName("btnUsbSettings")
        self.btn_usb_settings.setFixedSize(32, 32)
        self.btn_usb_settings.setCursor(Qt.PointingHandCursor)
        self.btn_usb_settings.setToolTip("Flash Drive Settings & Tools (Open in Explorer, Format FAT32, Rescan)")
        self.btn_usb_settings.clicked.connect(lambda: self.menu_requested.emit(True))
        usb_box.addWidget(self.btn_usb_settings)

        layout.addLayout(usb_box)

    def _on_lang_changed(self, index: int):
        lang_code = self.lang_combo.currentData()
        if lang_code:
            self.language_selected.emit(lang_code)
