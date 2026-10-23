"""
top_bar.py — Aero Suite Top Navigation Bar Component.
Provides IVI Studio branding, app version badge, USB drive selection, refresh, and tools menu.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QWidget, QHBoxLayout, QLabel, QPushButton, QComboBox, QMenu
)
from PySide6.QtGui import QCursor
import theme


class TopBarWidget(QFrame):
    """Header panel managing brand identity and USB target selection."""
    usb_selected = Signal(int)
    refresh_requested = Signal()
    menu_requested = Signal(bool)

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
        lbl_title = QLabel("⚡ AERO SUITE")
        lbl_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme.CYAN_PRIMARY}; letter-spacing: 1px;")
        brand_box.addWidget(lbl_title)

        lbl_badge = QLabel(f"v{theme.APP_VERSION}")
        lbl_badge.setFixedHeight(28)
        lbl_badge.setAlignment(Qt.AlignCenter)
        lbl_badge.setStyleSheet(
            f"background-color: {theme.CYAN_ALPHA_15}; color: {theme.CYAN_PRIMARY}; "
            f"border: 1px solid {theme.BORDER_CYAN}; border-radius: 6px; padding: 0 10px; "
            f"font-size: 11px; font-weight: bold;"
        )
        brand_box.addWidget(lbl_badge)

        lbl_sub = QLabel("Dongfeng Shine (Aeolus D53) IVI Studio")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED}; margin-left: 8px;")
        brand_box.addWidget(lbl_sub)
        layout.addLayout(brand_box)

        layout.addStretch()

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
        self.usb_combo.setFixedWidth(300)
        self.usb_combo.setFixedHeight(32)
        self.usb_combo.setCursor(Qt.PointingHandCursor)
        self.usb_combo.setContextMenuPolicy(Qt.CustomContextMenu)
        self.usb_combo.customContextMenuRequested.connect(lambda pt: self.menu_requested.emit(False))
        self.usb_combo.currentIndexChanged.connect(self.usb_selected.emit)
        usb_box.addWidget(self.usb_combo)

        self.btn_refresh_usb = QPushButton("🔄 Refresh")
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
