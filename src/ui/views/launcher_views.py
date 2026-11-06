"""
launcher_views.py — Features 7 & 8: Disable and Enable Factory Launcher Views.
Controls freezing and unfreezing of the Dongfeng Aeolus stock dashboard launcher.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
import theme
from core.i18n import t
from ui.components.dialogs import show_confirm_dialog


class DisableLauncherView(QWidget):
    """View for preparing Disable Factory Launcher USB payload."""
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

        self.lbl_head = QLabel(t("disable_launcher.view_title"))
        self.lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER};")
        c_layout.addWidget(self.lbl_head)

        self.lbl_desc = QLabel(t("disable_launcher.desc"))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 2px 0 6px 0; line-height: 1.4;")
        self.lbl_desc.setWordWrap(True)
        c_layout.addWidget(self.lbl_desc)

        # Action Buttons Strip
        dis_btn_box = QHBoxLayout()
        dis_btn_box.setSpacing(10)

        self.btn_dis = QPushButton(t("disable_launcher.btn_action"))
        self.btn_dis.setProperty("class", "btnDanger")
        self.btn_dis.setFixedHeight(44)
        self.btn_dis.clicked.connect(self._execute_disable_launcher)
        dis_btn_box.addWidget(self.btn_dis, 3)

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
        dis_btn_box.addWidget(self.btn_add_basket, 1)

        c_layout.addLayout(dis_btn_box)

        layout.addWidget(card)
        layout.addStretch()

    def retranslate_ui(self):
        """Re-translates elements in DisableLauncherView."""
        self.lbl_head.setText(t("disable_launcher.view_title"))
        self.lbl_desc.setText(t("disable_launcher.desc"))
        self.btn_dis.setText(t("disable_launcher.btn_action"))
        self.btn_add_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))

    def _on_add_to_basket(self):
        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="disable_launcher",
            title=t("disable_launcher.view_title", "Disable Factory Launcher"),
            summary="تجميد لانشر المصنع الأصلي وإخفائه",
            config={},
            requires_reboot=False
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def _execute_disable_launcher(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = t("disable_launcher.confirm_msg", letter=letter)
        if not show_confirm_dialog(self, t("disable_launcher.confirm_title"), confirm_msg, confirm_text=t("disable_launcher.btn_confirm", "🚫 Disable Launcher"), is_danger=True):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_disable_launcher_usb,
            letter,
            success_title=t("disable_launcher.success_title"),
            success_msg=t("disable_launcher.success_msg", letter=letter),
            error_title=t("common.preparation_failed")
        )


class EnableLauncherView(QWidget):
    """View for preparing Enable Factory Launcher USB payload."""
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

        self.lbl_head = QLabel(t("enable_launcher.view_title"))
        self.lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        c_layout.addWidget(self.lbl_head)

        self.lbl_desc = QLabel(t("enable_launcher.desc"))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 2px 0 6px 0; line-height: 1.4;")
        self.lbl_desc.setWordWrap(True)
        c_layout.addWidget(self.lbl_desc)

        # Action Buttons Strip
        en_btn_box = QHBoxLayout()
        en_btn_box.setSpacing(10)

        self.btn_en = QPushButton(t("enable_launcher.btn_action"))
        self.btn_en.setProperty("class", "btnPrimary")
        self.btn_en.setFixedHeight(44)
        self.btn_en.clicked.connect(self._execute_enable_launcher)
        en_btn_box.addWidget(self.btn_en, 3)

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
        en_btn_box.addWidget(self.btn_add_basket, 1)

        c_layout.addLayout(en_btn_box)

        layout.addWidget(card)
        layout.addStretch()

    def retranslate_ui(self):
        """Re-translates elements in EnableLauncherView."""
        self.lbl_head.setText(t("enable_launcher.view_title"))
        self.lbl_desc.setText(t("enable_launcher.desc"))
        self.btn_en.setText(t("enable_launcher.btn_action"))
        self.btn_add_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))

    def _on_add_to_basket(self):
        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="enable_launcher",
            title=t("enable_launcher.view_title", "Enable Factory Launcher"),
            summary="استعادة لانشر المصنع الأصلي وإلغاء تجميده",
            config={},
            requires_reboot=False
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def _execute_enable_launcher(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = t("enable_launcher.confirm_msg", letter=letter)
        if not show_confirm_dialog(self, t("enable_launcher.confirm_title"), confirm_msg, confirm_text=t("enable_launcher.btn_confirm", "✅ Enable Launcher")):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_enable_launcher_usb,
            letter,
            success_title=t("enable_launcher.success_title"),
            success_msg=t("enable_launcher.success_msg", letter=letter),
            error_title=t("common.preparation_failed")
        )


class LauncherControlView(QWidget):
    """
    Unified Factory Launcher & Power Management View.
    Consolidates stock launcher freezing (Disable), unfreezing (Enable),
    and soft screen restart into a single cohesive control studio.
    """
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(12)

        # 1. Header Banner Card
        banner_card = QFrame()
        banner_card.setProperty("class", "card")
        b_layout = QVBoxLayout(banner_card)
        b_layout.setContentsMargins(18, 14, 18, 14)
        b_layout.setSpacing(8)

        self.lbl_vtitle = QLabel(t("launcher_control.view_title", "⚡ FACTORY LAUNCHER CONTROL"))
        self.lbl_vtitle.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        b_layout.addWidget(self.lbl_vtitle)

        self.lbl_desc = QLabel(t("launcher_control.desc"))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 0; line-height: 1.5;")
        self.lbl_desc.setWordWrap(True)
        b_layout.addWidget(self.lbl_desc)

        root_layout.addWidget(banner_card)

        # 2. Unified Launcher Operations Card
        ops_card = QFrame()
        ops_card.setProperty("class", "card")
        o_layout = QVBoxLayout(ops_card)
        o_layout.setContentsMargins(18, 16, 18, 16)
        o_layout.setSpacing(14)

        # Section A: Freeze / Disable Launcher
        self.lbl_freeze_title = QLabel(t("launcher_control.freeze_card_title", "🚫 FREEZE FACTORY LAUNCHER"))
        self.lbl_freeze_title.setStyleSheet(f"font-size: 13.5px; font-weight: bold; color: {theme.CRIMSON_DANGER};")
        o_layout.addWidget(self.lbl_freeze_title)

        self.lbl_freeze_desc = QLabel(t("launcher_control.freeze_desc"))
        self.lbl_freeze_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED}; border: none; background: transparent; padding: 0; line-height: 1.4;")
        self.lbl_freeze_desc.setWordWrap(True)
        o_layout.addWidget(self.lbl_freeze_desc)

        freeze_btn_box = QHBoxLayout()
        freeze_btn_box.setSpacing(10)

        self.btn_freeze = QPushButton(t("disable_launcher.btn_action", "🚫 Freeze Launcher"))
        self.btn_freeze.setProperty("class", "btnDanger")
        self.btn_freeze.setFixedHeight(44)
        self.btn_freeze.clicked.connect(self._execute_disable_launcher)
        freeze_btn_box.addWidget(self.btn_freeze, 3)

        self.btn_freeze_basket = QPushButton(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.btn_freeze_basket.setFixedHeight(44)
        self.btn_freeze_basket.setCursor(Qt.PointingHandCursor)
        self.btn_freeze_basket.setStyleSheet(self._basket_btn_style())
        self.btn_freeze_basket.clicked.connect(self._on_add_freeze_basket)
        freeze_btn_box.addWidget(self.btn_freeze_basket, 1)

        o_layout.addLayout(freeze_btn_box)

        # Separator Line
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setFixedHeight(1)
        sep1.setStyleSheet(f"background-color: {theme.BORDER_SLATE}; border: none; margin: 4px 0;")
        o_layout.addWidget(sep1)

        # Section B: Restore / Enable Launcher
        self.lbl_unfreeze_title = QLabel(t("launcher_control.unfreeze_card_title", "✅ RESTORE FACTORY LAUNCHER"))
        self.lbl_unfreeze_title.setStyleSheet(f"font-size: 13.5px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        o_layout.addWidget(self.lbl_unfreeze_title)

        self.lbl_unfreeze_desc = QLabel(t("launcher_control.unfreeze_desc"))
        self.lbl_unfreeze_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED}; border: none; background: transparent; padding: 0; line-height: 1.4;")
        self.lbl_unfreeze_desc.setWordWrap(True)
        o_layout.addWidget(self.lbl_unfreeze_desc)

        restore_btn_box = QHBoxLayout()
        restore_btn_box.setSpacing(10)

        self.btn_restore = QPushButton(t("enable_launcher.btn_action", "✅ Restore Launcher"))
        self.btn_restore.setProperty("class", "btnPrimary")
        self.btn_restore.setFixedHeight(44)
        self.btn_restore.clicked.connect(self._execute_enable_launcher)
        restore_btn_box.addWidget(self.btn_restore, 3)

        self.btn_restore_basket = QPushButton(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.btn_restore_basket.setFixedHeight(44)
        self.btn_restore_basket.setCursor(Qt.PointingHandCursor)
        self.btn_restore_basket.setStyleSheet(self._basket_btn_style())
        self.btn_restore_basket.clicked.connect(self._on_add_restore_basket)
        restore_btn_box.addWidget(self.btn_restore_basket, 1)

        o_layout.addLayout(restore_btn_box)

        root_layout.addWidget(ops_card)
        root_layout.addStretch()

    def _basket_btn_style(self) -> str:
        return f"""
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
        """

    def retranslate_ui(self):
        """Re-translates all titles, descriptions, and buttons."""
        self.lbl_vtitle.setText(t("launcher_control.view_title", "⚡ FACTORY LAUNCHER CONTROL"))
        self.lbl_desc.setText(t("launcher_control.desc"))
        self.lbl_freeze_title.setText(t("launcher_control.freeze_card_title", "🚫 FREEZE FACTORY LAUNCHER"))
        self.lbl_freeze_desc.setText(t("launcher_control.freeze_desc"))
        self.btn_freeze.setText(t("disable_launcher.btn_action", "🚫 Freeze Launcher"))
        self.btn_freeze_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))

        self.lbl_unfreeze_title.setText(t("launcher_control.unfreeze_card_title", "✅ RESTORE FACTORY LAUNCHER"))
        self.lbl_unfreeze_desc.setText(t("launcher_control.unfreeze_desc"))
        self.btn_restore.setText(t("enable_launcher.btn_action", "✅ Restore Launcher"))
        self.btn_restore_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))

    def _execute_disable_launcher(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = t("disable_launcher.confirm_msg", letter=letter)
        if not show_confirm_dialog(self, t("disable_launcher.confirm_title"), confirm_msg, confirm_text=t("disable_launcher.btn_confirm", "🚫 Disable Launcher"), is_danger=True):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_disable_launcher_usb,
            letter,
            success_title=t("disable_launcher.success_title"),
            success_msg=t("disable_launcher.success_msg", letter=letter),
            error_title=t("common.preparation_failed")
        )

    def _on_add_freeze_basket(self):
        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="disable_launcher",
            title=t("disable_launcher.view_title", "Disable Factory Launcher"),
            summary="تجميد لانشر المصنع الأصلي وإخفائه",
            config={},
            requires_reboot=False
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def _execute_enable_launcher(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = t("enable_launcher.confirm_msg", letter=letter)
        if not show_confirm_dialog(self, t("enable_launcher.confirm_title"), confirm_msg, confirm_text=t("enable_launcher.btn_confirm", "✅ Enable Launcher")):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_enable_launcher_usb,
            letter,
            success_title=t("enable_launcher.success_title"),
            success_msg=t("enable_launcher.success_msg", letter=letter),
            error_title=t("common.preparation_failed")
        )

    def _on_add_restore_basket(self):
        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="enable_launcher",
            title=t("enable_launcher.view_title", "Enable Factory Launcher"),
            summary="استعادة لانشر المصنع الأصلي وإلغاء تجميده",
            config={},
            requires_reboot=False
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")


