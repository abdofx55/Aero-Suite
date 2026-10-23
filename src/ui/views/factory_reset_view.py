"""
factory_reset_view.py — Feature 12: Zero-Trace Dealership Factory Reset View.
Builds the emergency wipe & auto-healing factory payload with security confirmations.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
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
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        self.lbl_desc.setWordWrap(True)
        c_layout.addWidget(self.lbl_desc)

        self.btn_reset = QPushButton(t("factory_reset.btn_action"))
        self.btn_reset.setProperty("class", "btnDanger")
        self.btn_reset.setFixedHeight(44)
        self.btn_reset.clicked.connect(self._execute_factory_reset)
        c_layout.addWidget(self.btn_reset)

        layout.addWidget(card)
        layout.addStretch()

    def retranslate_ui(self):
        """Re-translates elements in FactoryResetView."""
        self.lbl_head.setText(t("factory_reset.view_title"))
        self.lbl_desc.setText(t("factory_reset.desc"))
        self.btn_reset.setText(t("factory_reset.btn_action"))

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
