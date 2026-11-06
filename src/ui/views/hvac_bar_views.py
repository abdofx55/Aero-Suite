"""
hvac_bar_views.py — Feature: HVAC Climate Navigation Bar Customization & Restoration Views.
Provides a unified tabbed hub matching the exact architecture of GmsHubView.
Allows drivers to deploy the streamlined enhanced bar (with Back, Home, Recent Apps, and Installed Apps navigation controls, and centered fan)
or cleanly restore the factory original OEM bar.
Localized dynamically via core.i18n.
"""
import os
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QStackedWidget, QApplication, QScrollArea
)
import theme
from core.paths import ASSETS_DIR
from core.i18n import t, is_rtl
from ui.components.dialogs import show_confirm_dialog


class InstallHvacBarView(QWidget):
    """View for preparing the enhanced HVAC & Navigation Bar deployment USB."""
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.viewport().setAutoFillBackground(False)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(10)

        # 1. Main Deployment Card
        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(16, 14, 16, 14)
        c_layout.setSpacing(10)

        head_row = QHBoxLayout()
        head_row.setSpacing(8)

        self.lbl_head = QLabel(t("install_hvac_bar.view_title", "🚀 تثبيت شريط التنقل والتكييف المطور (Aero Bar)"))
        self.lbl_head.setStyleSheet(f"font-size: 14.5px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        head_row.addWidget(self.lbl_head)
        head_row.addStretch()
        c_layout.addLayout(head_row)

        self.lbl_desc = QLabel(t("install_hvac_bar.desc"))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 2px 0px;")
        self.lbl_desc.setWordWrap(True)
        c_layout.addWidget(self.lbl_desc)

        # Image Preview Card for Aero Bar
        preview_dock = os.path.join(ASSETS_DIR, "aerobar_dock.png")
        preview_screen = os.path.join(ASSETS_DIR, "aerobar_preview.png")
        chosen_preview = preview_dock if os.path.isfile(preview_dock) else (preview_screen if os.path.isfile(preview_screen) else None)
        if chosen_preview:
            preview_frame = QFrame()
            preview_frame.setStyleSheet(f"background-color: #07090E; border: 1px solid {theme.BORDER_CYAN}; border-radius: 8px; padding: 4px;")
            pf_layout = QVBoxLayout(preview_frame)
            pf_layout.setContentsMargins(8, 6, 8, 6)
            pf_layout.setSpacing(4)

            self.lbl_preview_title = QLabel(t("install_hvac_bar.preview_title", "📸 معاينة حية لشريط Aero Bar المطور:"))
            self.lbl_preview_title.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
            pf_layout.addWidget(self.lbl_preview_title)

            self.lbl_image_preview = QLabel()
            self.lbl_image_preview.setAlignment(Qt.AlignCenter)
            self.lbl_image_preview.setStyleSheet("border: none; background: transparent;")
            pix = QPixmap(chosen_preview)
            if not pix.isNull():
                self.lbl_image_preview.setPixmap(pix.scaledToWidth(580, Qt.SmoothTransformation))
            pf_layout.addWidget(self.lbl_image_preview)
            c_layout.addWidget(preview_frame)
        else:
            self.lbl_preview_title = None
            self.lbl_image_preview = None

        # Feature Specs Box
        specs_group = QFrame()
        specs_group.setStyleSheet(f"background-color: {theme.SURFACE_2}; border: 1px solid {theme.BORDER_SLATE}; border-radius: 6px;")
        sp_layout = QVBoxLayout(specs_group)
        sp_layout.setContentsMargins(14, 12, 14, 12)
        sp_layout.setSpacing(8)

        self.lbl_specs_title = QLabel(t("install_hvac_bar.specs_title", "✨ الميزات الحصرية المدمجة في شريط Aero Bar المطور:"))
        self.lbl_specs_title.setStyleSheet(f"font-size: 12.5px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        sp_layout.addWidget(self.lbl_specs_title)

        self.lbl_specs_body = QLabel(t("install_hvac_bar.specs_body"))
        self.lbl_specs_body.setStyleSheet(f"font-size: 11.5px; color: {theme.TEXT_MUTED}; border: none; background: transparent; padding: 4px 2px;")
        self.lbl_specs_body.setWordWrap(True)
        sp_layout.addWidget(self.lbl_specs_body)

        c_layout.addWidget(specs_group)

        # Action Buttons Strip
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_deploy = QPushButton("   " + t("install_hvac_bar.btn_action", "جهز فلاشة تثبيت شريط التنقل والتكييف"))
        self.btn_deploy.setProperty("class", "btnPrimary")
        self.btn_deploy.setFixedHeight(44)
        self.btn_deploy.setMinimumHeight(44)
        self.btn_deploy.setCursor(Qt.PointingHandCursor)
        self.btn_deploy.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.CYAN_PRIMARY};
                color: #000000;
                font-size: 13.5px;
                font-weight: bold;
                border-radius: 6px;
                padding: 10px 20px;
                border: 1px solid {theme.CYAN_PRIMARY};
            }}
            QPushButton:hover {{
                background-color: {theme.CYAN_HOVER};
                border: 1px solid {theme.CYAN_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {theme.CYAN_DIM};
                border: 1px solid {theme.CYAN_DIM};
            }}
            QPushButton:disabled {{
                background-color: {theme.SURFACE_2};
                color: {theme.TEXT_MUTED};
                border: 1px solid {theme.BORDER_SLATE};
            }}
        """)
        self.btn_deploy.clicked.connect(self._execute_install_hvac_bar)
        btn_box.addWidget(self.btn_deploy, 3)

        self.btn_add_basket = QPushButton(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.btn_add_basket.setFixedHeight(44)
        self.btn_add_basket.setMinimumHeight(44)
        self.btn_add_basket.setCursor(Qt.PointingHandCursor)
        self.btn_add_basket.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.SURFACE_2};
                border: 1px solid {theme.BORDER_CYAN};
                color: {theme.CYAN_PRIMARY};
                border-radius: 6px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: bold;
                min-height: 22px;
            }}
            QPushButton:hover {{
                background-color: {theme.CYAN_ALPHA_15};
            }}
        """)
        self.btn_add_basket.clicked.connect(self._on_add_to_basket)
        btn_box.addWidget(self.btn_add_basket, 1)

        c_layout.addLayout(btn_box)
        layout.addWidget(card)
        layout.addStretch()

        self.scroll.setWidget(scroll_widget)
        root_layout.addWidget(self.scroll)

    def retranslate_ui(self):
        self.lbl_head.setText(t("install_hvac_bar.view_title", "🚀 تثبيت شريط التنقل والتكييف المطور (Aero Bar)"))
        self.lbl_desc.setText(t("install_hvac_bar.desc"))
        if getattr(self, 'lbl_preview_title', None):
            self.lbl_preview_title.setText(t("install_hvac_bar.preview_title", "📸 معاينة حية لشريط Aero Bar المطور في الشاشة:"))
        self.lbl_specs_title.setText(t("install_hvac_bar.specs_title", "✨ الميزات الحصرية المدمجة في شريط Aero Bar المطور:"))
        self.lbl_specs_body.setText(t("install_hvac_bar.specs_body"))
        self.btn_deploy.setText("   " + t("install_hvac_bar.btn_action", "جهز فلاشة تثبيت شريط Aero Bar المطور"))
        self.btn_add_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))

    def _on_add_to_basket(self):
        # UX Guard: If restore_hvac_bar is already in basket, confirm switch
        if self.main_app.basket.has_item("restore_hvac_bar"):
            confirm = show_confirm_dialog(
                self,
                title=t("basket.hvac_switch_to_install_title", "تبديل إلى شريط التنقل والتكييف المطور"),
                message=t("basket.hvac_switch_to_install_msg", "السلة تحتوي حالياً على أمر استعادة شريط المصنع. هل ترغب في إزالته وإضافة شريط التنقل والتكييف المطور بدلاً منه؟"),
                confirm_text=t("basket.btn_confirm_switch_install", "❄️ نعم، تثبيت شريط التنقل المطور"),
                cancel_text=t("basket.btn_keep_restore", "إبقاء الاستعادة"),
                is_danger=False
            )
            if not confirm:
                return

        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="install_hvac_bar",
            title=t("install_hvac_bar.view_title", "تثبيت شريط أزرار التنقل والتكييف المطور"),
            summary=t("install_hvac_bar.basket_summary", "إضافة أزرار التنقل (Back, Home, Recents) وزر قائمة التطبيقات"),
            config={},
            requires_reboot=True
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def _execute_install_hvac_bar(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_title = t("install_hvac_bar.confirm_title", "تأكيد تجهيز فلاشة شريط التنقل والتكييف")
        confirm_msg = t("install_hvac_bar.confirm_msg", "سيتم تجهيز الفلاشة ({letter}) بنسخة واجهة النظام المدمج بها أزرار التنقل الأربعة (Back / Home / Recents / Apps) مع سكريبت التثبيت وإعادة التشغيل.\n\nهل تريد المتابعة؟", letter=letter)
        if not show_confirm_dialog(self, confirm_title, confirm_msg, confirm_text=t("install_hvac_bar.btn_confirm", "❄️ جهز الفلاشة الآن")):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_install_hvac_bar_usb,
            letter,
            success_title=t("install_hvac_bar.success_title", "فلاشة شريط التنقل والتكييف جاهزة"),
            success_msg=t("install_hvac_bar.success_msg", "تم تجهيز فلاشة تثبيت شريط التنقل والتكييف بنجاح على القرص ({letter}).\nقم بتركيب الفلاشة في شاشة السيارة لتفعيل الواجهة الجديدة تلقائياً.", letter=letter),
            error_title="فشل تجهيز فلاشة شريط التنقل والتكييف"
        )


class RestoreHvacBarView(QWidget):
    """View for preparing the factory OEM HVAC Navigation Bar restoration USB."""
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.viewport().setAutoFillBackground(False)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(10)

        # 1. Main Restoration Card
        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(16, 14, 16, 14)
        c_layout.setSpacing(10)

        head_row = QHBoxLayout()
        head_row.setSpacing(8)

        self.lbl_head = QLabel(t("restore_hvac_bar.view_title", "🔄 استعادة شريط المصنع الأصلي"))
        self.lbl_head.setStyleSheet(f"font-size: 14.5px; font-weight: bold; color: {theme.AMBER_WARN}; border: none; background: transparent;")
        head_row.addWidget(self.lbl_head)
        head_row.addStretch()
        c_layout.addLayout(head_row)

        self.lbl_desc = QLabel(t("restore_hvac_bar.desc"))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 2px 0px;")
        self.lbl_desc.setWordWrap(True)
        c_layout.addWidget(self.lbl_desc)

        # Notice Box
        notice_group = QFrame()
        notice_group.setStyleSheet(f"background-color: {theme.SURFACE_2}; border: 1px solid {theme.BORDER_SLATE}; border-radius: 6px;")
        nt_layout = QVBoxLayout(notice_group)
        nt_layout.setContentsMargins(14, 12, 14, 12)
        nt_layout.setSpacing(8)

        self.lbl_notice_title = QLabel(t("restore_hvac_bar.notice_title", "🛡️ تفاصيل استعادة المصنع (100% Stock OEM):"))
        self.lbl_notice_title.setStyleSheet(f"font-size: 12.5px; font-weight: bold; color: {theme.AMBER_WARN}; border: none; background: transparent;")
        nt_layout.addWidget(self.lbl_notice_title)

        self.lbl_notice_body = QLabel(t("restore_hvac_bar.notice_body"))
        self.lbl_notice_body.setStyleSheet(f"font-size: 11.5px; color: {theme.TEXT_MUTED}; border: none; background: transparent; padding: 4px 2px;")
        self.lbl_notice_body.setWordWrap(True)
        nt_layout.addWidget(self.lbl_notice_body)

        c_layout.addWidget(notice_group)

        # Action Buttons Strip
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_restore = QPushButton("   " + t("restore_hvac_bar.btn_action", "جهز فلاشة استعادة شريط المصنع الأصلي"))
        self.btn_restore.setProperty("class", "btnWarning")
        self.btn_restore.setFixedHeight(44)
        self.btn_restore.setMinimumHeight(44)
        self.btn_restore.setCursor(Qt.PointingHandCursor)
        self.btn_restore.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.AMBER_WARN};
                color: #050B14;
                font-size: 13.5px;
                font-weight: bold;
                border-radius: 6px;
                padding: 10px 20px;
                border: 1px solid {theme.AMBER_WARN};
            }}
            QPushButton:hover {{
                background-color: #FCD34D;
                border: 1px solid #FCD34D;
            }}
            QPushButton:pressed {{
                background-color: #D97706;
                border: 1px solid #D97706;
            }}
            QPushButton:disabled {{
                background-color: {theme.SURFACE_2};
                color: {theme.TEXT_MUTED};
                border: 1px solid {theme.BORDER_SLATE};
            }}
        """)
        self.btn_restore.clicked.connect(self._execute_restore_hvac_bar)
        btn_box.addWidget(self.btn_restore, 3)

        self.btn_add_basket = QPushButton(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.btn_add_basket.setFixedHeight(44)
        self.btn_add_basket.setMinimumHeight(44)
        self.btn_add_basket.setCursor(Qt.PointingHandCursor)
        self.btn_add_basket.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.SURFACE_2};
                border: 1px solid {theme.BORDER_CYAN};
                color: {theme.CYAN_PRIMARY};
                border-radius: 6px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: bold;
                min-height: 22px;
            }}
            QPushButton:hover {{
                background-color: {theme.CYAN_ALPHA_15};
            }}
        """)
        self.btn_add_basket.clicked.connect(self._on_add_to_basket)
        btn_box.addWidget(self.btn_add_basket, 1)

        c_layout.addLayout(btn_box)
        layout.addWidget(card)
        layout.addStretch()

        self.scroll.setWidget(scroll_widget)
        root_layout.addWidget(self.scroll)

    def retranslate_ui(self):
        self.lbl_head.setText(t("restore_hvac_bar.view_title", "🔄 استعادة شريط المصنع الأصلي"))
        self.lbl_desc.setText(t("restore_hvac_bar.desc"))
        self.lbl_notice_title.setText(t("restore_hvac_bar.notice_title", "🛡️ تفاصيل استعادة المصنع (100% Stock OEM):"))
        self.lbl_notice_body.setText(t("restore_hvac_bar.notice_body"))
        self.btn_restore.setText("   " + t("restore_hvac_bar.btn_action", "جهز فلاشة استعادة شريط المصنع الأصلي"))
        self.btn_add_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))

    def _on_add_to_basket(self):
        # UX Guard: If install_hvac_bar is already in basket, confirm switch
        if self.main_app.basket.has_item("install_hvac_bar"):
            confirm = show_confirm_dialog(
                self,
                title=t("basket.hvac_switch_to_restore_title", "تبديل إلى استعادة شريط المصنع"),
                message=t("basket.hvac_switch_to_restore_msg", "السلة تحتوي حالياً على أمر تثبيت شريط التنقل والتكييف المطور. هل ترغب في إزالته وإضافة استعادة شريط المصنع بدلاً منه؟"),
                confirm_text=t("basket.btn_confirm_switch_restore", "🔄 نعم، استعادة شريط المصنع"),
                cancel_text=t("basket.btn_keep_install", "إبقاء التثبيت"),
                is_danger=True
            )
            if not confirm:
                return

        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="restore_hvac_bar",
            title=t("restore_hvac_bar.view_title", "استعادة شريط المصنع الأصلي"),
            summary=t("restore_hvac_bar.basket_summary", "استعادة شريط الوكالة الأصلي بدون أزرار التنقل"),
            config={},
            requires_reboot=True
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def _execute_restore_hvac_bar(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_title = t("restore_hvac_bar.confirm_title", "تأكيد استعادة شريط المصنع الأصلي")
        confirm_msg = t("restore_hvac_bar.confirm_msg", "سيتم تجهيز الفلاشة ({letter}) بنسخة SystemUI الرسمية الأصلية لإرجاع واجهة المصنع بالكامل.\n\nهل ترغب في المتابعة؟", letter=letter)
        if not show_confirm_dialog(self, confirm_title, confirm_msg, confirm_text=t("restore_hvac_bar.btn_confirm", "🔄 استعادة المصنع الآن"), is_danger=True):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_restore_hvac_bar_usb,
            letter,
            success_title=t("restore_hvac_bar.success_title", "فلاشة استعادة المصنع جاهزة"),
            success_msg=t("restore_hvac_bar.success_msg", "تم تجهيز فلاشة استعادة شريط المصنع الأصلي بنجاح على القرص ({letter}).\nركب الفلاشة في الشاشة لاستعادة الواجهة الأصلية بالكامل.", letter=letter),
            error_title="فشل تجهيز فلاشة استعادة المصنع"
        )


class HvacBarHubView(QWidget):
    """
    Unified Climate & Navigation Bar Hub for Aero Suite.
    Unifies Enhanced Navigation Bar Installation and Stock Bar Restoration
    into a single tabbed studio view mirroring GmsHubView architecture.
    """
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.current_tab = 0
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 12, 18, 12)
        root_layout.setSpacing(10)

        # 1. Connected Segmented Pill Tab Bar (Height 50px, border-radius 25px)
        self.tab_container = QFrame()
        self.tab_container.setObjectName("segmentedTabBarHvac")
        self.tab_container.setFixedHeight(50)
        self.tab_container.setStyleSheet(f"""
            QFrame#segmentedTabBarHvac {{
                background-color: {theme.SURFACE_1};
                border: 1.5px solid {theme.BORDER_SLATE};
                border-radius: 25px;
            }}
        """)

        tab_layout = QHBoxLayout(self.tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        self.btn_tab_install = QPushButton(t("hvac_hub.tab_install", "❄️ تثبيت شريط التنقل والتكييف المطور"))
        self.btn_tab_install.setFixedHeight(50)
        self.btn_tab_install.setCursor(Qt.PointingHandCursor)
        self.btn_tab_install.clicked.connect(lambda: self.set_active_tab(0))
        tab_layout.addWidget(self.btn_tab_install, 1)

        self.btn_tab_restore = QPushButton(t("hvac_hub.tab_restore", "🔄 استعادة شريط المصنع الأصلي"))
        self.btn_tab_restore.setFixedHeight(50)
        self.btn_tab_restore.setCursor(Qt.PointingHandCursor)
        self.btn_tab_restore.clicked.connect(lambda: self.set_active_tab(1))
        tab_layout.addWidget(self.btn_tab_restore, 1)

        root_layout.addWidget(self.tab_container)

        # 2. Content Stack
        self.stack = QStackedWidget()

        # Child View 0: Install Enhanced Bar
        self.install_view = InstallHvacBarView(self.main_app, self)
        if self.install_view.layout():
            self.install_view.layout().setContentsMargins(0, 4, 0, 0)
        self.stack.addWidget(self.install_view)

        # Child View 1: Restore OEM Bar
        self.restore_view = RestoreHvacBarView(self.main_app, self)
        if self.restore_view.layout():
            self.restore_view.layout().setContentsMargins(0, 4, 0, 0)
        self.stack.addWidget(self.restore_view)

        root_layout.addWidget(self.stack)

        self._update_tab_styles()

    def set_active_tab(self, index: int):
        if index < 0 or index >= self.stack.count():
            return
        self.current_tab = index
        self.stack.setCurrentIndex(index)
        self._update_tab_styles()

    def _update_tab_styles(self):
        """Highlights the active tab with solid cyan fill and connected pill styling."""
        buttons = [self.btn_tab_install, self.btn_tab_restore]
        is_rtl = QApplication.isRightToLeft()
        N = len(buttons)
        phys_order = list(reversed(range(N))) if is_rtl else list(range(N))

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
                        font-size: 13.5px;
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
                        font-size: 13.5px;
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
        self.btn_tab_install.setText(t("hvac_hub.tab_install", "❄️ تثبيت شريط التنقل والتكييف المطور"))
        self.btn_tab_restore.setText(t("hvac_hub.tab_restore", "🔄 استعادة شريط المصنع الأصلي"))
        if hasattr(self.install_view, "retranslate_ui"):
            self.install_view.retranslate_ui()
        if hasattr(self.restore_view, "retranslate_ui"):
            self.restore_view.retranslate_ui()
