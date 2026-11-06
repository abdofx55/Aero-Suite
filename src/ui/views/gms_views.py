"""
gms_views.py — Features 5 & 6: Google Play Services Setup and Removal Views.
Provides dedicated interfaces for calibrated GMS injection (Framework, Services, Login, Store)
and clean system-level GMS removal.
Localized dynamically via core.i18n.
"""
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QCheckBox, QStackedWidget, QApplication
)
import theme
from core.i18n import t
from ui.components.dialogs import show_confirm_dialog


def _render_globe_icon(color_hex: str, size: int = 22) -> QPixmap:
    """Draws a vector globe icon with crisp contrast in any specified theme color."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color_hex))
    pen.setWidthF(1.8)
    painter.setPen(pen)
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.drawLine(1, size // 2, size - 1, size // 2)
    painter.drawLine(size // 2, 1, size // 2, size - 1)
    painter.drawEllipse(size // 4, 1, size // 2, size - 2)
    painter.end()
    return pix


class InstallGmsView(QWidget):
    """View for preparing Google Play Services installation USB and quick launch payloads."""
    def __init__(self, main_app, gms_dir: str, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.gms_dir = gms_dir
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(10)

        # 1. Main Install GMS Card
        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(16, 12, 16, 12)
        c_layout.setSpacing(8)

        import os
        from PySide6.QtGui import QIcon, QPixmap
        from PySide6.QtCore import QSize
        from core.paths import ASSETS_DIR
        assets_dir = ASSETS_DIR

        # Header Row with Official Google Play Services Square Icon
        head_row = QHBoxLayout()
        head_row.setSpacing(8)
        self.lbl_head_icon = QLabel()
        self.lbl_head_icon.setFixedSize(20, 20)
        self.lbl_head_icon.setStyleSheet("padding: 0px; margin: 0px; border: none; background: transparent;")
        _gms_icon_path = os.path.join(assets_dir, "google_services_square.png")
        if os.path.isfile(_gms_icon_path):
            self.lbl_head_icon.setPixmap(QPixmap(_gms_icon_path).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.lbl_head_icon.setAlignment(Qt.AlignCenter)
            head_row.addWidget(self.lbl_head_icon)

        clean_vtitle = t("install_gms.view_title", "GOOGLE PLAY SERVICES SETUP").replace("🌐", "").strip()
        self.lbl_head = QLabel(clean_vtitle)
        self.lbl_head.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        head_row.addWidget(self.lbl_head)
        head_row.addStretch()
        c_layout.addLayout(head_row)

        self.lbl_desc = QLabel(t("install_gms.desc"))
        self.lbl_desc.setStyleSheet(f"font-size: 11.5px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 0px; line-height: 1.35;")
        self.lbl_desc.setWordWrap(True)
        c_layout.addWidget(self.lbl_desc)

        # Deep Clean Reinstall Informational Notice
        self.lbl_clean_notice = QLabel(t("install_gms.clean_reinstall_notice"))
        self.lbl_clean_notice.setStyleSheet(f"""
            QLabel {{
                background-color: {theme.SURFACE_2};
                border: 1px solid {theme.BORDER_CYAN};
                border-radius: 6px;
                color: {theme.CYAN_PRIMARY};
                font-weight: 500;
                padding: 5px 10px;
                font-size: 11px;
                line-height: 1.3;
            }}
        """)
        self.lbl_clean_notice.setWordWrap(True)
        c_layout.addWidget(self.lbl_clean_notice)

        # Optional User Apps Section
        opt_group = QFrame()
        opt_group.setStyleSheet(f"background-color: {theme.SURFACE_2}; border: 1px solid {theme.BORDER_SLATE}; border-radius: 6px;")
        opt_layout = QVBoxLayout(opt_group)
        opt_layout.setContentsMargins(10, 6, 10, 6)
        opt_layout.setSpacing(4)

        self.lbl_opt_title = QLabel(t("install_gms.optional_apps_title", "📦 تطبيقات إضافية اختيارية (User Apps):"))
        self.lbl_opt_title.setStyleSheet(f"font-size: 11.5px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        opt_layout.addWidget(self.lbl_opt_title)

        chk_row = QHBoxLayout()
        chk_row.setSpacing(16)

        self.chk_gboard = QCheckBox(t("install_gms.opt_gboard", "⌨️ لوحة مفاتيح Gboard"))
        self.chk_gboard.setChecked(True)
        self.chk_gboard.setCursor(Qt.PointingHandCursor)
        self.chk_gboard.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-size: 11.5px; font-weight: 500;")
        chk_row.addWidget(self.chk_gboard)

        self.chk_chrome = QCheckBox(t("install_gms.opt_chrome", "🌐 متصفح Chrome"))
        self.chk_chrome.setChecked(False)
        self.chk_chrome.setCursor(Qt.PointingHandCursor)
        self.chk_chrome.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-size: 11.5px; font-weight: 500;")
        chk_row.addWidget(self.chk_chrome)

        self.chk_maps = QCheckBox(t("install_gms.opt_maps", "🗺️ خرائط Google Maps"))
        self.chk_maps.setChecked(False)
        self.chk_maps.setCursor(Qt.PointingHandCursor)
        self.chk_maps.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-size: 11.5px; font-weight: 500;")
        chk_row.addWidget(self.chk_maps)

        chk_row.addStretch()
        opt_layout.addLayout(chk_row)
        c_layout.addWidget(opt_group)

        # Main Action Buttons Strip
        gms_btn_box = QHBoxLayout()
        gms_btn_box.setSpacing(8)

        self.btn_gms = QPushButton("   " + t("install_gms.btn_action", "جهز فلاشة خدمات جوجل (Install GMS)"))
        self.btn_gms.setProperty("class", "btnPrimary")
        self.btn_gms.setFixedHeight(44)
        if os.path.isfile(_gms_icon_path):
            self.btn_gms.setIcon(QIcon(_gms_icon_path))
            self.btn_gms.setIconSize(QSize(20, 20))
        self.btn_gms.clicked.connect(self._execute_install_gms)
        gms_btn_box.addWidget(self.btn_gms, 3)

        self.btn_add_basket = QPushButton(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.btn_add_basket.setFixedHeight(44)
        self.btn_add_basket.setCursor(Qt.PointingHandCursor)
        self.btn_add_basket.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.SURFACE_2};
                border: 1px solid {theme.BORDER_CYAN};
                color: {theme.CYAN_PRIMARY};
                border-radius: 6px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme.CYAN_ALPHA_15};
            }}
        """)
        self.btn_add_basket.clicked.connect(self._on_add_to_basket)
        gms_btn_box.addWidget(self.btn_add_basket, 1)

        c_layout.addLayout(gms_btn_box)

        layout.addWidget(card)

        # 2. Quick Launch Card (for stock launcher owners)
        launch_card = QFrame()
        launch_card.setProperty("class", "card")
        l_layout = QVBoxLayout(launch_card)
        l_layout.setContentsMargins(16, 12, 16, 12)
        l_layout.setSpacing(8)

        self.lbl_launch_head = QLabel(t("install_gms.quick_launch_title", "🚀 تشغيل متجر جوجل ومدير الملفات (Quick Launch)"))
        self.lbl_launch_head.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        l_layout.addWidget(self.lbl_launch_head)

        self.lbl_launch_desc = QLabel(t("install_gms.quick_launch_desc", "إذا كانت شاشتك تستخدم واجهة المصنع الأصلية ولا تعرض التطبيقات الخارجية، يمكنك تجهيز فلاشة سريعة لفتح التطبيق مباشرة بدون ريستارت:"))
        self.lbl_launch_desc.setStyleSheet(f"font-size: 11.5px; color: {theme.TEXT_MUTED}; border: none; background: transparent; padding: 0px; line-height: 1.3;")
        self.lbl_launch_desc.setWordWrap(True)
        l_layout.addWidget(self.lbl_launch_desc)

        # Row 1: Google Play Store Launch
        vending_box = QHBoxLayout()
        vending_box.setSpacing(8)

        _play_icon_path = os.path.join(assets_dir, "google_play.png")
        self.btn_open_vending = QPushButton("   " + t("install_gms.btn_open_vending", "تجهيز فلاشة فتح متجر Google Play"))
        self.btn_open_vending.setFixedHeight(36)
        self.btn_open_vending.setCursor(Qt.PointingHandCursor)
        if os.path.isfile(_play_icon_path):
            self.btn_open_vending.setIcon(QIcon(_play_icon_path))
            self.btn_open_vending.setIconSize(QSize(18, 18))
        self.btn_open_vending.clicked.connect(self._prepare_open_vending)
        vending_box.addWidget(self.btn_open_vending, 3)

        self.btn_basket_vending = QPushButton(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.btn_basket_vending.setFixedHeight(36)
        self.btn_basket_vending.setCursor(Qt.PointingHandCursor)
        self.btn_basket_vending.setToolTip(t("basket.btn_add_to_basket", "Add to Basket"))
        self.btn_basket_vending.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.SURFACE_2};
                border: 1px solid {theme.BORDER_CYAN};
                color: {theme.CYAN_PRIMARY};
                border-radius: 6px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {theme.CYAN_PRIMARY};
                background-color: {theme.CYAN_ALPHA_15};
            }}
        """)
        self.btn_basket_vending.clicked.connect(self._add_vending_to_basket)
        vending_box.addWidget(self.btn_basket_vending, 1)
        l_layout.addLayout(vending_box)

        # Row 2: Files by Google Launch
        docui_box = QHBoxLayout()
        docui_box.setSpacing(8)

        _doc_icon_path = os.path.join(assets_dir, "documents_ui.png")
        self.btn_open_docui = QPushButton("   " + t("install_gms.btn_open_docui", "تجهيز فلاشة فتح تطبيق Files by Google"))
        self.btn_open_docui.setFixedHeight(36)
        self.btn_open_docui.setCursor(Qt.PointingHandCursor)
        if os.path.isfile(_doc_icon_path):
            self.btn_open_docui.setIcon(QIcon(_doc_icon_path))
            self.btn_open_docui.setIconSize(QSize(18, 18))
        self.btn_open_docui.clicked.connect(self._prepare_open_docui)
        docui_box.addWidget(self.btn_open_docui, 3)

        self.btn_basket_docui = QPushButton(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.btn_basket_docui.setFixedHeight(36)
        self.btn_basket_docui.setCursor(Qt.PointingHandCursor)
        self.btn_basket_docui.setToolTip(t("basket.btn_add_to_basket", "Add to Basket"))
        self.btn_basket_docui.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.SURFACE_2};
                border: 1px solid {theme.BORDER_CYAN};
                color: {theme.CYAN_PRIMARY};
                border-radius: 6px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {theme.CYAN_PRIMARY};
                background-color: {theme.CYAN_ALPHA_15};
            }}
        """)
        self.btn_basket_docui.clicked.connect(self._add_docui_to_basket)
        docui_box.addWidget(self.btn_basket_docui, 1)
        l_layout.addLayout(docui_box)

        layout.addWidget(launch_card)

        layout.addStretch()

    def retranslate_ui(self):
        """Re-translates elements in InstallGmsView."""
        clean_vtitle = t("install_gms.view_title", "GOOGLE PLAY SERVICES SETUP").replace("🌐", "").strip()
        self.lbl_head.setText(clean_vtitle)
        self.lbl_desc.setText(t("install_gms.desc"))
        self.lbl_clean_notice.setText(t("install_gms.clean_reinstall_notice"))
        self.lbl_opt_title.setText(t("install_gms.optional_apps_title", "📦 تطبيقات إضافية اختيارية (User Apps):"))
        self.chk_gboard.setText(t("install_gms.opt_gboard", "⌨️ لوحة مفاتيح Gboard"))
        self.chk_chrome.setText(t("install_gms.opt_chrome", "🌐 متصفح Chrome"))
        self.chk_maps.setText(t("install_gms.opt_maps", "🗺️ خرائط Google Maps"))
        self.btn_gms.setText("   " + t("install_gms.btn_action", "جهز فلاشة خدمات جوجل (Install GMS)"))
        self.btn_add_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.lbl_launch_head.setText(t("install_gms.quick_launch_title", "🚀 تشغيل متجر جوجل ومدير الملفات (Quick Launch)"))
        self.lbl_launch_desc.setText(t("install_gms.quick_launch_desc", "إذا كانت شاشتك تستخدم واجهة المصنع الأصلية ولا تعرض التطبيقات الخارجية، يمكنك تجهيز فلاشة سريعة لفتح التطبيق مباشرة بدون ريستارت:"))
        self.btn_open_vending.setText("   " + t("install_gms.btn_open_vending", "تجهيز فلاشة فتح متجر Google Play"))
        self.btn_basket_vending.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.btn_open_docui.setText("   " + t("install_gms.btn_open_docui", "تجهيز فلاشة فتح تطبيق Files by Google"))
        self.btn_basket_docui.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))

    def _on_add_to_basket(self):
        # UX Reassurance Guard: If uninstall_gms is already queued, explain that install_gms includes deep purge
        if self.main_app.basket.has_item("uninstall_gms"):
            confirm = show_confirm_dialog(
                self,
                title=t("basket.gms_conflict_title", "🛒 Clean Reinstall Google Services"),
                message=t("basket.gms_conflict_msg"),
                confirm_text=t("basket.btn_clean_reinstall", "✨ Yes, Clean Reinstall"),
                cancel_text=t("basket.btn_keep_uninstall", "Keep Uninstall Only"),
                is_danger=False
            )
            if not confirm:
                return

        inc_gboard = self.chk_gboard.isChecked()
        inc_chrome = self.chk_chrome.isChecked()
        inc_maps = self.chk_maps.isChecked()

        summary_parts = ["Framework", "Play Services", "Account Manager", "Play Store"]
        if inc_gboard:
            summary_parts.append("Gboard")
        if inc_chrome:
            summary_parts.append("Chrome")
        if inc_maps:
            summary_parts.append("Maps")

        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="install_gms",
            title=t("install_gms.view_title", "Google Play Services Setup"),
            summary=", ".join(summary_parts),
            config={
                "gms_dir": self.gms_dir,
                "include_gboard": inc_gboard,
                "include_chrome": inc_chrome,
                "include_maps": inc_maps
            },
            requires_reboot=True
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def _add_vending_to_basket(self):
        allowed = self.main_app.prompt_launch_target_selection("open_app", "com.android.vending", "Google Play Store")
        if not allowed:
            return
        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="open_app",
            title="تشغيل متجر Google Play",
            summary="Google Play Store (com.android.vending)",
            config={"package_name": "com.android.vending", "app_name": "Google Play Store"},
            requires_reboot=False,
            launch_target_pkg="com.android.vending",
            launch_target_name="Google Play Store"
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def _add_docui_to_basket(self):
        app_name = t("install_gms.files_app_label", "Files by Google")
        allowed = self.main_app.prompt_launch_target_selection("open_app", "com.google.android.apps.nbu.files", app_name)
        if not allowed:
            return
        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="open_app",
            title=f"تشغيل {app_name}",
            summary=f"{app_name} (com.google.android.apps.nbu.files)",
            config={"package_name": "com.google.android.apps.nbu.files", "app_name": app_name},
            requires_reboot=False,
            launch_target_pkg="com.google.android.apps.nbu.files",
            launch_target_name=app_name
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def _execute_install_gms(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_title = t("install_gms.confirm_title", "Confirm Google Services Installation")
        confirm_msg = t("install_gms.confirm_msg", letter=letter)
        if not show_confirm_dialog(self, confirm_title, confirm_msg, confirm_text=t("install_gms.btn_confirm", "🌐 Prepare GMS USB")):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_install_gms_usb,
            letter,
            self.gms_dir,
            include_gboard=self.chk_gboard.isChecked(),
            include_chrome=self.chk_chrome.isChecked(),
            include_maps=self.chk_maps.isChecked(),
            success_title=t("install_gms.success_title", "Google Services USB Ready"),
            success_msg=t("install_gms.success_msg", letter=letter),
            error_title="GMS Preparation Failed"
        )

    def _prepare_open_vending(self):
        """Prepares a quick-launch USB specifically for Google Play Store."""
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_title = t("install_gms.confirm_open_vending_title", "تأكيد فلاشة فتح متجر Google Play")
        confirm_msg = t("install_gms.confirm_open_vending_msg", letter=letter)
        if not show_confirm_dialog(self, confirm_title, confirm_msg, confirm_text=t("install_gms.btn_confirm_launch", "🚀 جهز فلاشة الفتح")):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_open_app_usb,
            letter,
            package_name="com.android.vending",
            app_name="Google Play Store",
            success_title=t("open_app.success_title", "Launch USB Ready"),
            success_msg=t("open_app.success_msg", app_title="Google Play Store", letter=letter),
            error_title="Launch USB Preparation Failed"
        )

    def _prepare_open_docui(self):
        """Prepares a quick-launch USB specifically for Files by Google."""
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_title = t("install_gms.confirm_open_docui_title", "تأكيد فلاشة فتح تطبيق Files by Google")
        confirm_msg = t("install_gms.confirm_open_docui_msg", letter=letter)
        if not show_confirm_dialog(self, confirm_title, confirm_msg, confirm_text=t("install_gms.btn_confirm_launch", "🚀 جهز فلاشة الفتح")):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_open_app_usb,
            letter,
            package_name="com.google.android.apps.nbu.files",
            app_name=t("install_gms.files_app_label", "Files by Google"),
            success_title=t("open_app.success_title", "Launch USB Ready"),
            success_msg=t("open_app.success_msg", app_title=t("install_gms.files_app_label", "Files by Google"), letter=letter),
            error_title="Launch USB Preparation Failed"
        )


class UninstallGmsView(QWidget):
    """View for preparing Google Play Services removal USB."""
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(18, 16, 18, 16)
        c_layout.setSpacing(14)

        self.lbl_head = QLabel(t("uninstall_gms.view_title", "🧹 REMOVE GOOGLE PLAY SERVICES"))
        self.lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER}; border: none; background: transparent;")
        c_layout.addWidget(self.lbl_head)

        self.lbl_desc = QLabel(t("uninstall_gms.desc"))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 2px 0 6px 0; line-height: 1.4;")
        self.lbl_desc.setWordWrap(True)
        c_layout.addWidget(self.lbl_desc)

        # Action Buttons Strip
        del_btn_box = QHBoxLayout()
        del_btn_box.setSpacing(10)

        self.btn_del = QPushButton(t("uninstall_gms.btn_action", "🧹 PREPARE GOOGLE SERVICES REMOVAL USB"))
        self.btn_del.setProperty("class", "btnDanger")
        self.btn_del.setFixedHeight(44)
        self.btn_del.clicked.connect(self._execute_uninstall_gms)
        del_btn_box.addWidget(self.btn_del, 3)

        self.btn_add_basket = QPushButton(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.btn_add_basket.setFixedHeight(44)
        self.btn_add_basket.setCursor(Qt.PointingHandCursor)
        self.btn_add_basket.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.SURFACE_2};
                border: 1px solid {theme.BORDER_CYAN};
                color: {theme.CYAN_PRIMARY};
                border-radius: 6px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme.CYAN_ALPHA_15};
            }}
        """)
        self.btn_add_basket.clicked.connect(self._on_add_to_basket)
        del_btn_box.addWidget(self.btn_add_basket, 1)

        c_layout.addLayout(del_btn_box)

        layout.addWidget(card)
        layout.addStretch()

    def retranslate_ui(self):
        """Re-translates elements in UninstallGmsView."""
        self.lbl_head.setText(t("uninstall_gms.view_title", "🧹 REMOVE GOOGLE PLAY SERVICES"))
        self.lbl_desc.setText(t("uninstall_gms.desc"))
        self.btn_del.setText(t("uninstall_gms.btn_action", "🧹 PREPARE GOOGLE SERVICES REMOVAL USB"))
        self.btn_add_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))

    def _on_add_to_basket(self):
        # UX Guard: If install_gms is already in basket, explain and confirm switch
        if self.main_app.basket.has_item("install_gms"):
            confirm = show_confirm_dialog(
                self,
                title=t("basket.gms_switch_to_uninstall_title", "Switch to Uninstall GMS"),
                message=t("basket.gms_switch_to_uninstall_msg"),
                confirm_text=t("basket.btn_confirm_switch_uninstall", "🗑️ Yes, Uninstall Only"),
                cancel_text=t("basket.btn_keep_install", "Keep Install"),
                is_danger=True
            )
            if not confirm:
                return

        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="uninstall_gms",
            title=t("uninstall_gms.view_title", "Remove Google Play Services"),
            summary="حذف خدمات جوجل وملفات التهيئة بالكامل",
            config={},
            requires_reboot=True
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def _execute_uninstall_gms(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_title = t("uninstall_gms.confirm_title", "Confirm Google Services Removal")
        confirm_msg = t("uninstall_gms.confirm_msg", letter=letter)
        if not show_confirm_dialog(self, confirm_title, confirm_msg, confirm_text=t("uninstall_gms.btn_confirm", "🧹 Prepare Removal USB"), is_danger=True):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_uninstall_gms_usb,
            letter,
            success_title=t("uninstall_gms.success_title", "GMS Removal USB Ready"),
            success_msg=t("uninstall_gms.success_msg", letter=letter),
            error_title="Removal Preparation Failed"
        )


class GmsHubView(QWidget):
    """
    Unified Google Play Services Hub for Aero Suite.
    Unifies GMS Installation/Injection with Clean GMS Removal
    into a single tabbed studio view.
    """
    def __init__(self, main_app, gms_dir: str, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.gms_dir = gms_dir
        self.current_tab = 0
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 12, 18, 12)
        root_layout.setSpacing(10)

        # 1. Connected Segmented Pill Tab Bar (Option 4: 50px, spacing 0, dynamic radii & dividers)
        self.tab_container = QFrame()
        self.tab_container.setObjectName("segmentedTabBarGms")
        self.tab_container.setFixedHeight(50)
        self.tab_container.setStyleSheet(f"""
            QFrame#segmentedTabBarGms {{
                background-color: {theme.SURFACE_1};
                border: 1.5px solid {theme.BORDER_SLATE};
                border-radius: 25px;
            }}
        """)

        tab_layout = QHBoxLayout(self.tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        self.btn_tab_setup = QPushButton(t("gms_hub.tab_setup", "Google Play Setup").replace("🌐", "").strip())
        self.btn_tab_setup.setFixedHeight(50)
        self.btn_tab_setup.setCursor(Qt.PointingHandCursor)
        self.btn_tab_setup.setIconSize(QSize(20, 20))
        self.btn_tab_setup.clicked.connect(lambda: self.set_active_tab(0))
        tab_layout.addWidget(self.btn_tab_setup, 1)

        self.btn_tab_uninstall = QPushButton(t("gms_hub.tab_uninstall", "🧹 Clean Uninstall"))
        self.btn_tab_uninstall.setFixedHeight(50)
        self.btn_tab_uninstall.setCursor(Qt.PointingHandCursor)
        self.btn_tab_uninstall.clicked.connect(lambda: self.set_active_tab(1))
        tab_layout.addWidget(self.btn_tab_uninstall, 1)

        root_layout.addWidget(self.tab_container)

        # 2. Content Stack
        self.stack = QStackedWidget()

        # Child View 0: Install GMS
        self.install_view = InstallGmsView(self.main_app, self.gms_dir, self)
        if self.install_view.layout():
            self.install_view.layout().setContentsMargins(0, 4, 0, 0)
        self.stack.addWidget(self.install_view)

        # Child View 1: Uninstall GMS
        self.uninstall_view = UninstallGmsView(self.main_app, self)
        if self.uninstall_view.layout():
            self.uninstall_view.layout().setContentsMargins(0, 4, 0, 0)
        self.stack.addWidget(self.uninstall_view)

        root_layout.addWidget(self.stack)

        self._update_tab_styles()

    def set_active_tab(self, index: int):
        if index < 0 or index >= self.stack.count():
            return
        self.current_tab = index
        self.stack.setCurrentIndex(index)
        self._update_tab_styles()

    def _update_tab_styles(self):
        """Highlights the active tab with solid cyan fill, high-contrast dynamic icons, and Option 4 pill styling."""
        buttons = [self.btn_tab_setup, self.btn_tab_uninstall]
        is_rtl = QApplication.isRightToLeft()
        N = len(buttons)
        phys_order = list(reversed(range(N))) if is_rtl else list(range(N))

        # Dynamic Globe Icon: Jet Black (#050B14) when tab is active (cyan bg), Muted (#94A3B8) when inactive
        globe_color = "#050B14" if self.current_tab == 0 else theme.TEXT_MUTED
        self.btn_tab_setup.setIcon(QIcon(_render_globe_icon(globe_color, 20)))
        self.btn_tab_setup.setText("  " + t("gms_hub.tab_setup", "Google Play Setup").replace("🌐", "").strip())

        for pos_idx, log_idx in enumerate(phys_order):
            btn = buttons[log_idx]
            is_leftmost = (pos_idx == 0)
            is_rightmost = (pos_idx == N - 1)
            is_active = (log_idx == self.current_tab)

            if is_leftmost:
                radius_str = "border-top-left-radius: 23px; border-bottom-left-radius: 23px; border-top-right-radius: 0px; border-bottom-right-radius: 0px;"
            elif is_rightmost:
                radius_str = "border-top-right-radius: 23px; border-bottom-right-radius: 23px; border-top-left-radius: 0px; border-bottom-left-radius: 0px;"
            else:
                radius_str = "border-radius: 0px;"

            border_left_str = "border: none;"
            if not is_leftmost and not is_active:
                left_neighbor_log_idx = phys_order[pos_idx - 1]
                if left_neighbor_log_idx != self.current_tab:
                    border_left_str = f"border-left: 1px solid {theme.BORDER_SLATE}; border-right: none; border-top: none; border-bottom: none;"

            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {theme.CYAN_PRIMARY};
                        color: #050B14;
                        font-size: 14px;
                        font-weight: bold;
                        border: none;
                        {radius_str}
                        padding: 0 14px;
                    }}
                    QPushButton:hover {{
                        background-color: {theme.CYAN_HOVER};
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {theme.TEXT_MUTED};
                        font-size: 14px;
                        font-weight: 600;
                        {border_left_str}
                        {radius_str}
                        padding: 0 14px;
                    }}
                    QPushButton:hover {{
                        color: {theme.TEXT_PRIMARY};
                        background-color: {theme.SURFACE_2};
                    }}
                """)

    def retranslate_ui(self):
        self._update_tab_styles()
        self.btn_tab_uninstall.setText(t("gms_hub.tab_uninstall", "🧹 Clean Uninstall"))
        if hasattr(self.install_view, "retranslate_ui"):
            self.install_view.retranslate_ui()
        if hasattr(self.uninstall_view, "retranslate_ui"):
            self.uninstall_view.retranslate_ui()

