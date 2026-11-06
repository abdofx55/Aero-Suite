"""
reboot_view.py — Feature 9: Restart Infotainment Screen View.
Generates an on-the-fly soft restart payload without stopping the car or disconnecting power.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
import theme
from core.i18n import t
from ui.components.dialogs import show_confirm_dialog


class RebootScreenView(QWidget):
    """View for preparing Reboot Infotainment Screen USB payload."""
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

        self.lbl_head = QLabel(t("reboot_screen.view_title"))
        self.lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        c_layout.addWidget(self.lbl_head)

        self.lbl_desc = QLabel(t("reboot_screen.desc"))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 2px 0 6px 0; line-height: 1.4;")
        self.lbl_desc.setWordWrap(True)
        c_layout.addWidget(self.lbl_desc)

        # Action Buttons Strip
        rb_btn_box = QHBoxLayout()
        rb_btn_box.setSpacing(10)

        self.btn_rb = QPushButton(t("reboot_screen.btn_action"))
        self.btn_rb.setProperty("class", "btnPrimary")
        self.btn_rb.setFixedHeight(44)
        self.btn_rb.clicked.connect(self._execute_reboot_screen)
        rb_btn_box.addWidget(self.btn_rb, 3)

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
        rb_btn_box.addWidget(self.btn_add_basket, 1)

        c_layout.addLayout(rb_btn_box)

        layout.addWidget(card)
        layout.addStretch()

    def retranslate_ui(self):
        """Re-translates elements in RebootScreenView."""
        self.lbl_head.setText(t("reboot_screen.view_title"))
        self.lbl_desc.setText(t("reboot_screen.desc"))
        self.btn_rb.setText(t("reboot_screen.btn_action"))
        self.btn_add_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))

    def _on_add_to_basket(self):
        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="reboot_screen",
            title=t("reboot_screen.view_title", "Reboot Infotainment Screen"),
            summary="إعادة تشغيل الشاشة تلقائياً في نهاية العمليات",
            config={},
            requires_reboot=True
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def _execute_reboot_screen(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = t("reboot_screen.confirm_msg", letter=letter)
        if not show_confirm_dialog(self, t("reboot_screen.confirm_title"), confirm_msg, confirm_text=t("reboot_screen.btn_confirm", "🔄 Prepare Reboot USB")):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_reboot_screen_usb,
            letter,
            success_title=t("reboot_screen.success_title"),
            success_msg=t("reboot_screen.success_msg", letter=letter),
            error_title=t("common.preparation_failed")
        )
