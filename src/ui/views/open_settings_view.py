"""
open_settings_view.py — Feature 4: Open Native Android Settings View.
Prepares an instantaneous, zero-reboot launch payload for native Android Settings.
Localized dynamically via core.i18n.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
import theme
from core.i18n import t


class OpenSettingsView(QWidget):
    """View for configuring Open Native Android Settings USB payloads."""
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

        self.lbl_head = QLabel(t("open_settings.view_title", "⚙️ OPEN NATIVE ANDROID SETTINGS"))
        self.lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        c_layout.addWidget(self.lbl_head)

        self.lbl_desc = QLabel(t("open_settings.desc"))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 2px 0 6px 0; line-height: 1.4;")
        self.lbl_desc.setWordWrap(True)
        c_layout.addWidget(self.lbl_desc)

        # Action Buttons Strip
        stg_btn_box = QHBoxLayout()
        stg_btn_box.setSpacing(10)

        self.btn_settings = QPushButton(t("open_settings.btn_action", "⚙️ PREPARE OPEN SETTINGS USB"))
        self.btn_settings.setProperty("class", "btnPrimary")
        self.btn_settings.setFixedHeight(44)
        self.btn_settings.clicked.connect(self._execute_open_settings)
        stg_btn_box.addWidget(self.btn_settings, 3)

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
        stg_btn_box.addWidget(self.btn_add_basket, 1)

        c_layout.addLayout(stg_btn_box)

        layout.addWidget(card)
        layout.addStretch()

    def retranslate_ui(self):
        """Re-translates elements in OpenSettingsView."""
        self.lbl_head.setText(t("open_settings.view_title", "⚙️ OPEN NATIVE ANDROID SETTINGS"))
        self.lbl_desc.setText(t("open_settings.desc"))
        self.btn_settings.setText(t("open_settings.btn_action", "⚙️ PREPARE OPEN SETTINGS USB"))
        self.btn_add_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))

    def _on_add_to_basket(self):
        title = t("open_settings.view_title", "Open Native Android Settings")
        allowed = self.main_app.prompt_launch_target_selection("open_settings", "com.android.settings", title)
        if not allowed:
            return

        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="open_settings",
            title=title,
            summary="فتح إعدادات أندرويد الأصلية وخيارات المطور",
            config={},
            requires_reboot=False,
            launch_target_pkg="com.android.settings",
            launch_target_name=title
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def _execute_open_settings(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_title = t("open_settings.confirm_title", "Confirm Settings USB")
        confirm_msg = t("open_settings.confirm_msg", letter=letter)
        from ui.components.dialogs import show_confirm_dialog
        if not show_confirm_dialog(self, confirm_title, confirm_msg, confirm_text=t("open_settings.btn_confirm", "⚙️ Prepare Settings USB")):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_open_settings_usb,
            letter,
            success_title=t("open_settings.success_title", "Settings USB Ready"),
            success_msg=t("open_settings.success_msg", letter=letter),
            error_title="Preparation Failed"
        )
