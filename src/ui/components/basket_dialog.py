"""
basket_dialog.py — Modern, Aesthetic Basket Management Dialog for Aero Suite.
Allows users to review queued operations, observe reboot/launch statuses, remove items,
and initiate composite USB preparation.
Fully localized for ar, en, ru, and zh.
"""
import re
from PySide6.QtCore import Qt, Signal, QByteArray, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QMessageBox
)
import theme
from core.i18n import t, get_i18n
from services.basket_service import get_basket_service, BasketItem


def _make_trash_icon(color_hex: str = "#FF2D55", size: int = 18) -> QIcon:
    """Renders a razor-sharp vector SVG trash can icon with High-DPI support."""
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color_hex}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M3 6h18"/>
  <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>
  <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
  <line x1="10" y1="11" x2="10" y2="17"/>
  <line x1="14" y1="11" x2="14" y2="17"/>
</svg>"""
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    scale = 2
    pixmap = QPixmap(size * scale, size * scale)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(scale)
    return QIcon(pixmap)


class BasketDeleteButton(QPushButton):
    """High-DPI vector trash button with smooth crimson-to-white hover transition."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.PointingHandCursor)
        self._icon_normal = _make_trash_icon(theme.CRIMSON_DANGER, size=18)
        self._icon_hover = _make_trash_icon("#FFFFFF", size=18)
        self.setIcon(self._icon_normal)
        self.setIconSize(QSize(18, 18))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.SURFACE_3};
                border: 1px solid {theme.BORDER_SLATE};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {theme.CRIMSON_DANGER};
                border-color: {theme.CRIMSON_DANGER};
            }}
        """)

    def enterEvent(self, event):
        self.setIcon(self._icon_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(self._icon_normal)
        super().leaveEvent(event)


class BasketItemCard(QFrame):
    """Card representing an individual queued operation in the basket dialog."""
    remove_clicked = Signal(str)

    def __init__(self, item: BasketItem, step_num: int = 1, parent=None):
        super().__init__(parent)
        self.item = item
        self.step_num = step_num
        self.setObjectName("basketItemCard")
        self.setStyleSheet(f"""
            QFrame#basketItemCard {{
                background-color: {theme.SURFACE_2};
                border: 1px solid {theme.BORDER_SLATE};
                border-radius: 8px;
                padding: 10px;
            }}
            QFrame#basketItemCard:hover {{
                border-color: {theme.BORDER_CYAN};
            }}
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # Execution Sequence Step Badge
        lbl_step = QLabel(f"#{self.step_num}")
        lbl_step.setStyleSheet(f"""
            font-size: 11px; font-weight: bold; color: {theme.CYAN_PRIMARY};
            background-color: {theme.SURFACE_3}; border: 1px solid {theme.BORDER_CYAN};
            border-radius: 4px; padding: 2px 6px;
        """)
        lbl_step.setFixedWidth(34)
        lbl_step.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_step)

        icons = {
            "backup": "💾",
            "factory_reset": "⚠️",
            "install_apps": "📦",
            "uninstall_apps": "🛡️",
            "install_gms": "🌐",
            "uninstall_gms": "🧹",
            "disable_launcher": "❄️",
            "enable_launcher": "🔄",
            "open_app": "🚀",
            "open_settings": "⚙️",
            "reboot_screen": "🔄",
            "vehicle_tweaks": "⚡",
            "fetch_logs": "📋"
        }
        icon_str = icons.get(self.item.action_type, "⚡")
        lbl_icon = QLabel(icon_str)
        lbl_icon.setStyleSheet("font-size: 20px; background: transparent; border: none;")
        lbl_icon.setFixedWidth(30)
        lbl_icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_icon)

        # Info Box
        info_box = QVBoxLayout()
        info_box.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        # Strip any leading emojis from item title to avoid duplicate icon display!
        clean_title = re.sub(r'^[^\w\s\(\)]+\s*', '', self.item.title).strip() or self.item.title
        lbl_title = QLabel(clean_title)
        lbl_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {theme.CYAN_PRIMARY}; background: transparent; border: none;")
        header_row.addWidget(lbl_title)

        if self.item.requires_reboot or self.item.action_type == "reboot_screen":
            lbl_reboot = QLabel(t("basket.badge_reboot", "🔄 Reboot Required"))
            lbl_reboot.setStyleSheet(f"""
                font-size: 10px; font-weight: bold; color: {theme.AMBER_WARN};
                background-color: {theme.SURFACE_3}; border: 1px solid {theme.AMBER_WARN};
                border-radius: 4px; padding: 1px 6px;
            """)
            header_row.addWidget(lbl_reboot)

        if self.item.action_type == "install_gms":
            lbl_clean = QLabel(t("basket.badge_clean_reinstall", "🧹 Includes Deep Clean"))
            lbl_clean.setStyleSheet(f"""
                font-size: 10px; font-weight: bold; color: {theme.MINT_SUCCESS};
                background-color: {theme.SURFACE_3}; border: 1px solid {theme.MINT_SUCCESS};
                border-radius: 4px; padding: 1px 6px;
            """)
            header_row.addWidget(lbl_clean)

        if self.item.launch_target_pkg:
            target_lbl = self.item.launch_target_name or self.item.launch_target_pkg
            lbl_launch = QLabel(f"🚀 {target_lbl}")
            lbl_launch.setStyleSheet(f"""
                font-size: 10px; font-weight: bold; color: {theme.MINT_SUCCESS};
                background-color: {theme.SURFACE_3}; border: 1px solid {theme.MINT_SUCCESS};
                border-radius: 4px; padding: 1px 6px;
            """)
            header_row.addWidget(lbl_launch)

        header_row.addStretch()
        info_box.addLayout(header_row)

        lbl_summary = QLabel(self.item.summary)
        lbl_summary.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED}; background: transparent; border: none;")
        lbl_summary.setWordWrap(True)
        info_box.addWidget(lbl_summary)

        layout.addLayout(info_box, 1)

        # Prominent Vector Recycle Bin Delete Button
        btn_del = BasketDeleteButton(self)
        btn_del.setToolTip(t("basket.btn_remove_tip", "Remove from basket"))
        btn_del.clicked.connect(lambda: self.remove_clicked.emit(self.item.action_type))
        layout.addWidget(btn_del)


class BasketDialog(QDialog):
    """Interactive modal showing the multi-action basket and preparation trigger."""
    prepare_requested = Signal()

    def __init__(self, main_app, parent=None):
        dialog_parent = parent or (main_app if isinstance(main_app, QWidget) else None)
        super().__init__(dialog_parent)
        self.main_app = main_app
        self.basket = get_basket_service()

        self.setWindowTitle(t("basket.dialog_title", "🛒 Multi-Command Basket"))
        self.resize(920, 600)
        self.setMinimumSize(840, 500)

        is_rtl = get_i18n().is_rtl()
        self.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme.SURFACE_1};
                color: {theme.TEXT_PRIMARY};
            }}
        """)
        self._build_ui()
        self.basket.basket_changed.connect(self._refresh_list)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Header Title & Subtitle
        header_box = QVBoxLayout()
        header_box.setSpacing(4)

        self.lbl_title = QLabel(t("basket.dialog_title", "🛒 Multi-Command Basket"))
        self.lbl_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        header_box.addWidget(self.lbl_title)

        self.lbl_subtitle = QLabel(t("basket.dialog_subtitle", "Review queued operations. Aero Suite will generate a unified batch script executed sequentially on your car."))
        self.lbl_subtitle.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED}; line-height: 1.4;")
        self.lbl_subtitle.setWordWrap(True)
        header_box.addWidget(self.lbl_subtitle)

        main_layout.addLayout(header_box)

        # Scroll Area for Queued Items (Auto-scrolls horizontally and vertically when needed)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: 1px solid {theme.BORDER_SLATE};
                border-radius: 8px;
            }}
            QScrollBar:vertical {{
                width: 8px;
                background: transparent;
                margin: 4px 2px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme.SURFACE_3};
                min-height: 24px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {theme.CYAN_PRIMARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                height: 8px;
                background: transparent;
                margin: 2px 4px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {theme.SURFACE_3};
                min-width: 24px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {theme.CYAN_PRIMARY};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)
        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(18, 14, 18, 22)
        self.items_layout.setSpacing(10)
        self.scroll.setWidget(self.items_container)
        main_layout.addWidget(self.scroll, 1)

        # Status & Warning Strip (Reboot vs Auto-launch indicator)
        self.status_banner = QFrame()
        self.status_banner.setObjectName("statusBanner")
        self.status_banner.setStyleSheet(f"""
            QFrame#statusBanner {{
                background-color: {theme.SURFACE_2};
                border: 1px solid {theme.BORDER_SLATE};
                border-radius: 8px;
            }}
        """)
        self.status_banner_layout = QHBoxLayout(self.status_banner)
        self.status_banner_layout.setContentsMargins(14, 10, 14, 10)
        self.status_banner_layout.setSpacing(12)

        # Crisp dedicated accent color strip on the leading edge
        self.status_accent_bar = QFrame()
        self.status_accent_bar.setFixedWidth(4)
        self.status_accent_bar.setStyleSheet(f"background-color: {theme.AMBER_WARN}; border-radius: 2px;")
        self.status_banner_layout.addWidget(self.status_accent_bar)

        self.lbl_status_icon = QLabel("⚠️")
        self.lbl_status_icon.setStyleSheet("font-size: 20px; background: transparent; border: none;")
        self.lbl_status_icon.setAlignment(Qt.AlignTop | Qt.AlignCenter)
        self.status_banner_layout.addWidget(self.lbl_status_icon)

        self.lbl_status_info = QLabel("")
        self.lbl_status_info.setStyleSheet(f"font-size: 12px; line-height: 1.5; color: {theme.TEXT_PRIMARY}; background: transparent; border: none;")
        self.lbl_status_info.setWordWrap(True)
        self.status_banner_layout.addWidget(self.lbl_status_info, 1)
        main_layout.addWidget(self.status_banner)

        # Bottom Buttons Bar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        clear_raw = t("basket.btn_clear", "Clear Basket")
        clear_text = re.sub(r'[\U0001f5d1\ufe0f]+', '', clear_raw).strip()
        self.btn_clear = QPushButton(f"  {clear_text}")
        self.btn_clear.setIcon(_make_trash_icon(theme.CRIMSON_DANGER, size=15))
        self.btn_clear.setIconSize(QSize(15, 15))
        self.btn_clear.setFixedHeight(38)
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.SURFACE_2};
                border: 1px solid {theme.BORDER_SLATE};
                color: {theme.TEXT_PRIMARY};
                border-radius: 6px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {theme.CRIMSON_DANGER};
                color: {theme.CRIMSON_DANGER};
            }}
        """)
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        btn_bar.addWidget(self.btn_clear)

        btn_bar.addStretch()

        self.btn_close = QPushButton(t("common.close", "Close"))
        self.btn_close.setFixedHeight(38)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(self.btn_close)

        self.btn_prepare = QPushButton(t("basket.btn_prepare", "🚀 Prepare Composite USB"))
        self.btn_prepare.setFixedHeight(38)
        self.btn_prepare.setProperty("class", "btnPrimary")
        self.btn_prepare.setCursor(Qt.PointingHandCursor)
        self.btn_prepare.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.CYAN_PRIMARY};
                color: #000000;
                border-radius: 6px;
                padding: 0 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #38bdf8;
            }}
            QPushButton:disabled {{
                background-color: {theme.SURFACE_3};
                color: {theme.TEXT_MUTED};
            }}
        """)
        self.btn_prepare.clicked.connect(self._on_prepare_clicked)
        btn_bar.addWidget(self.btn_prepare)

        main_layout.addLayout(btn_bar)

        self._refresh_list()

    def _refresh_list(self):
        """Cleans and populates cards for all items currently in the basket."""
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        items = self.basket.get_ordered_items()
        if not items:
            empty_lbl = QLabel(t("basket.empty_msg", "🛒 Your basket is currently empty.\nAdd actions from any feature screen using the 'Add to Basket' button."))
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 13px; padding: 40px;")
            self.items_layout.addWidget(empty_lbl)
            self.items_layout.addStretch()
            self.btn_prepare.setEnabled(False)
            self.btn_prepare.setText(t("basket.btn_prepare", "🚀 Prepare Composite USB"))
            self.status_banner.setVisible(False)
            return

        self.btn_prepare.setEnabled(True)
        self.status_banner.setVisible(True)

        for idx, it in enumerate(items, 1):
            card = BasketItemCard(it, step_num=idx, parent=self)
            card.remove_clicked.connect(self._on_remove_item)
            self.items_layout.addWidget(card)

        self.items_layout.addStretch()

        # Update Status Banner
        has_reboot = self.basket.has_reboot()
        reboot_count = self.basket.get_reboot_count()
        launch_info = self.basket.get_current_launch_target()

        if reboot_count == 2 and launch_info:
            _, pkg, name = launch_info
            self.lbl_status_icon.setText("🚀")
            self.status_accent_bar.setStyleSheet(f"background-color: {theme.MINT_SUCCESS}; border-radius: 2px;")
            self.status_banner.setStyleSheet(f"QFrame#statusBanner {{ background-color: {theme.SURFACE_2}; border: 1px solid {theme.MINT_SUCCESS}; border-radius: 8px; }}")
            raw_msg = t(
                "basket.multistage_double_reboot_launch",
                f"🔄 Note: Screen will reboot twice (after reset and after installs), and '{name}' will launch automatically after the second reboot.",
                app_name=name
            )
            clean_msg = re.sub(r'^[🔄🚀\s]+', '', raw_msg).strip()
            self.lbl_status_info.setText(clean_msg)
            self.lbl_status_info.setStyleSheet(f"color: {theme.MINT_SUCCESS}; background: transparent; border: none; font-size: 12px; line-height: 1.5;")
        elif reboot_count == 2:
            self.lbl_status_icon.setText("🔄")
            self.status_accent_bar.setStyleSheet(f"background-color: {theme.CYAN_PRIMARY}; border-radius: 2px;")
            self.status_banner.setStyleSheet(f"QFrame#statusBanner {{ background-color: {theme.SURFACE_2}; border: 1px solid {theme.BORDER_CYAN}; border-radius: 8px; }}")
            raw_msg = t(
                "basket.reboot_scheduled_double",
                "🔄 Note: Exactly 2 consecutive reboots scheduled (1st after factory reset, 2nd after installs). Keep USB connected."
            )
            clean_msg = re.sub(r'^[🔄\s]+', '', raw_msg).strip()
            self.lbl_status_info.setText(clean_msg)
            self.lbl_status_info.setStyleSheet(f"color: {theme.CYAN_PRIMARY}; background: transparent; border: none; font-size: 12px; line-height: 1.5;")
        elif has_reboot and launch_info:
            _, pkg, name = launch_info
            self.lbl_status_icon.setText("🚀")
            self.status_accent_bar.setStyleSheet(f"background-color: {theme.MINT_SUCCESS}; border-radius: 2px;")
            self.status_banner.setStyleSheet(f"QFrame#statusBanner {{ background-color: {theme.SURFACE_2}; border: 1px solid {theme.MINT_SUCCESS}; border-radius: 8px; }}")
            raw_msg = t(
                "basket.multistage_launch_scheduled",
                f"🚀 Note: System will reboot as required, and '{name}' will launch automatically after the screen finishes booting and stabilizes.",
                app_name=name
            )
            clean_msg = re.sub(r'^[🚀\s]+', '', raw_msg).strip()
            self.lbl_status_info.setText(clean_msg)
            self.lbl_status_info.setStyleSheet(f"color: {theme.MINT_SUCCESS}; background: transparent; border: none; font-size: 12px; line-height: 1.5;")
        elif has_reboot:
            self.lbl_status_icon.setText("🔄")
            self.status_accent_bar.setStyleSheet(f"background-color: {theme.CYAN_PRIMARY}; border-radius: 2px;")
            self.status_banner.setStyleSheet(f"QFrame#statusBanner {{ background-color: {theme.SURFACE_2}; border: 1px solid {theme.BORDER_CYAN}; border-radius: 8px; }}")
            raw_msg = t("basket.reboot_scheduled", "🔄 Note: A single automated reboot is scheduled at the end of execution to apply system changes.")
            clean_msg = re.sub(r'^[🔄\s]+', '', raw_msg).strip()
            self.lbl_status_info.setText(clean_msg)
            self.lbl_status_info.setStyleSheet(f"color: {theme.CYAN_PRIMARY}; background: transparent; border: none; font-size: 12px; line-height: 1.5;")
        elif launch_info:
            _, pkg, name = launch_info
            self.lbl_status_icon.setText("🚀")
            self.status_accent_bar.setStyleSheet(f"background-color: {theme.MINT_SUCCESS}; border-radius: 2px;")
            self.status_banner.setStyleSheet(f"QFrame#statusBanner {{ background-color: {theme.SURFACE_2}; border: 1px solid {theme.MINT_SUCCESS}; border-radius: 8px; }}")
            raw_msg = t("basket.launch_scheduled", f"🚀 Note: '{name}' will launch automatically after operations complete.", app_name=name)
            clean_msg = re.sub(r'^[🚀\s]+', '', raw_msg).strip()
            self.lbl_status_info.setText(clean_msg)
            self.lbl_status_info.setStyleSheet(f"color: {theme.MINT_SUCCESS}; background: transparent; border: none; font-size: 12px; line-height: 1.5;")
        else:
            self.status_banner.setVisible(False)

        count = len(items)
        if count == 1:
            self.btn_prepare.setText(t("basket.btn_prepare_single", "🚀 Prepare Composite USB (1 Operation)"))
        else:
            self.btn_prepare.setText(t("basket.btn_prepare_count", f"🚀 Prepare Composite USB ({count} Operations)", count=count))

    def _on_remove_item(self, action_type: str):
        self.basket.remove_item(action_type)
        self._refresh_list()

    def _on_clear_clicked(self):
        from ui.components.dialogs import show_confirm_dialog
        if show_confirm_dialog(
            self,
            t("basket.clear_confirm_title", "Clear Basket"),
            t("basket.clear_confirm_msg", "Are you sure you want to remove all operations from the basket?"),
            confirm_text=t("basket.btn_clear_confirm", "Clear All"),
            is_danger=True
        ):
            self.basket.clear()
            self._refresh_list()

    def _on_prepare_clicked(self):
        self.accept()
        self.prepare_requested.emit()

    def retranslate_ui(self):
        is_rtl = get_i18n().is_rtl()
        self.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        self.setWindowTitle(t("basket.dialog_title", "🛒 Multi-Command Basket"))
        self.lbl_title.setText(t("basket.dialog_title", "🛒 Multi-Command Basket"))
        self.lbl_subtitle.setText(t("basket.dialog_subtitle", "Review queued operations. Aero Suite will generate a unified batch script executed sequentially on your car."))
        clear_raw = t("basket.btn_clear", "Clear Basket")
        clear_text = re.sub(r'[\U0001f5d1\ufe0f]+', '', clear_raw).strip()
        self.btn_clear.setText(f"  {clear_text}")
        self.btn_clear.setIcon(_make_trash_icon(theme.CRIMSON_DANGER, size=15))
        self.btn_close.setText(t("common.close", "Close"))
        self._refresh_list()
