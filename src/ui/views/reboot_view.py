"""
reboot_view.py — Feature 9: Restart Infotainment Screen View.
Generates an on-the-fly soft restart payload without stopping the car or disconnecting power.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
import theme
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

        lbl_head = QLabel("🔄 RESTART INFOTAINMENT SCREEN")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Quick screen refresh on the fly! 🔄 Restarts your infotainment screen safely in just a few seconds without turning off your engine, stopping the car, or disconnecting the vehicle battery. Perfect for clearing temporary glitches and speeding up your screen instantly!"
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)

        btn_rb = QPushButton("🔄 PREPARE REBOOT SCREEN USB")
        btn_rb.setProperty("class", "btnPrimary")
        btn_rb.setFixedHeight(44)
        btn_rb.clicked.connect(self._execute_reboot_screen)
        c_layout.addWidget(btn_rb)

        layout.addWidget(card)
        layout.addStretch()

    def _execute_reboot_screen(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = f"Are you sure you want to prepare Screen Reboot USB on drive {letter}?"
        if not show_confirm_dialog(self, "Confirm Restart Screen", confirm_msg, confirm_text="🔄 Prepare Reboot USB"):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_reboot_screen_usb,
            letter,
            success_title="Reboot USB Ready",
            success_msg=f"Successfully prepared reboot payload on drive {letter}!",
            error_title="Preparation Failed"
        )
