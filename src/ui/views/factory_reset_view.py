"""
factory_reset_view.py — Feature 12: Zero-Trace Dealership Factory Reset View.
Builds the emergency wipe & auto-healing factory payload with security confirmations.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
import theme
from core.i18n import t
from ui.components.dialogs import show_confirm_dialog


class FactoryResetView(QWidget):
    """View for configuring Zero-Trace Factory Reset USB payload."""
    def __init__(self, main_app, factory_backup_dir: str, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.factory_backup_dir = factory_backup_dir
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

        self.lbl_head = QLabel(t("factory_reset.view_title"))
        self.lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER}; border: none; background: transparent;")
        c_layout.addWidget(self.lbl_head)

        self.lbl_desc = QLabel(t("factory_reset.desc"))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 2px 0 6px 0; line-height: 1.4;")
        self.lbl_desc.setWordWrap(True)
        c_layout.addWidget(self.lbl_desc)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_reset = QPushButton(t("factory_reset.btn_action"))
        self.btn_reset.setProperty("class", "btnDanger")
        self.btn_reset.setFixedHeight(44)
        self.btn_reset.clicked.connect(self._execute_factory_reset)
        btn_box.addWidget(self.btn_reset, 1)

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
        btn_box.addWidget(self.btn_add_basket, 1)

        c_layout.addLayout(btn_box)

        layout.addWidget(card)
        layout.addStretch()

    def retranslate_ui(self):
        """Re-translates elements in FactoryResetView."""
        self.lbl_head.setText(t("factory_reset.view_title"))
        self.lbl_desc.setText(t("factory_reset.desc"))
        self.btn_reset.setText(t("factory_reset.btn_action"))
        self.btn_add_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))

    def _on_add_to_basket(self):
        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="factory_reset",
            title=t("factory_reset.view_title", "Zero-Trace Factory Reset"),
            summary="مسح شامل للبيانات واستعادة ضبط المصنع الكامل للشاشة",
            config={},
            requires_reboot=True
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def _execute_factory_reset(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = t("factory_reset.confirm_msg", letter=letter)
        if not show_confirm_dialog(self, t("factory_reset.confirm_title"), confirm_msg, confirm_text=t("factory_reset.btn_confirm", "⚠️ Prepare Reset USB"), is_danger=True):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_factory_reset_usb,
            letter,
            local_factory_backup_dir=self.factory_backup_dir,
            success_title=t("factory_reset.success_title"),
            success_msg=t("factory_reset.success_msg", letter=letter),
            error_title=t("common.preparation_failed")
        )
