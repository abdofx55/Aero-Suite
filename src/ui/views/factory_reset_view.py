"""
factory_reset_view.py — Feature 12: Zero-Trace Dealership Factory Reset View.
Builds the emergency wipe & auto-healing factory payload with security confirmations.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
import theme
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

        lbl_head = QLabel("⚠️ ZERO-TRACE FACTORY RESET")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER}; border: none; background: transparent;")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "The ultimate clean slate & dealership reset! ⚠️ Restores your Dongfeng Shine screen to 100% factory-fresh condition:\n\n"
            "• 🚗 Showroom Fresh: Wipes all added apps, Google services, and personal accounts cleanly.\n"
            "• 🛡️ Auto-Healing Stock Apps: Automatically restores any missing original car applications from the factory archive.\n"
            "• 🏢 100% Dealership Ready: Completely hides all modifications before dealership visits and routine maintenance.\n"
            "• 🔒 Safe Protection: Your air conditioning, reverse cameras, and steering wheel controls remain 100% safe and untouched!"
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)

        btn_reset = QPushButton("⚠️ PREPARE ZERO-TRACE FACTORY RESET USB")
        btn_reset.setProperty("class", "btnDanger")
        btn_reset.setFixedHeight(44)
        btn_reset.clicked.connect(self._execute_factory_reset)
        c_layout.addWidget(btn_reset)

        layout.addWidget(card)
        layout.addStretch()

    def _execute_factory_reset(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = (
            f"CRITICAL WARNING:\n\n"
            f"Are you sure you want to prepare ZERO-TRACE FACTORY RESET USB on drive {letter}?\n\n"
            f"This will wipe all user-installed applications, Google services, accounts, and custom data from the car screen."
        )
        if not show_confirm_dialog(self, "Confirm Factory Reset", confirm_msg, confirm_text="⚠️ Prepare Reset USB", is_danger=True):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_factory_reset_usb,
            letter,
            local_factory_backup_dir=self.factory_backup_dir,
            success_title="Factory Reset USB Ready",
            success_msg=f"Successfully prepared Factory Reset payload on drive {letter}!",
            error_title="Reset Preparation Failed"
        )
