"""
open_settings_view.py — Feature 4: Open Native Android Settings View.
Prepares an instantaneous, zero-reboot launch payload for native Android Settings.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
import theme


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

        lbl_head = QLabel("⚙️ OPEN NATIVE ANDROID SETTINGS")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Unlock the hidden Android power inside your car! ⚙️ Opens the full native Android Settings menu instantly on your screen without rebooting:\n\n"
            "• 📶 Wi-Fi & Hotspots: Connect to any wireless network or phone hotspot easily.\n"
            "• 🎧 Bluetooth Devices: Pair and manage phones, remotes, and audio accessories.\n"
            "• 💾 Storage & Memory: Check your available storage and free up space.\n"
            "• 🌐 Languages & Options: Adjust system languages, app permissions, and advanced controls freely!"
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)

        btn_settings = QPushButton("⚙️ PREPARE OPEN SETTINGS USB")
        btn_settings.setProperty("class", "btnPrimary")
        btn_settings.setFixedHeight(44)
        btn_settings.clicked.connect(self._execute_open_settings)
        c_layout.addWidget(btn_settings)

        layout.addWidget(card)
        layout.addStretch()

    def _execute_open_settings(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = (
            f"Are you sure you want to prepare Open Android Settings USB on drive {letter}?\n\n"
            f"When inserted into the vehicle, this payload immediately launches native Android Settings."
        )
        from ui.components.dialogs import show_confirm_dialog
        if not show_confirm_dialog(self, "Confirm Settings USB", confirm_msg, confirm_text="⚙️ Prepare Settings USB"):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_open_settings_usb,
            letter,
            success_title="Settings USB Ready",
            success_msg=f"Successfully prepared Open Android Settings USB on drive {letter}!",
            error_title="Preparation Failed"
        )
