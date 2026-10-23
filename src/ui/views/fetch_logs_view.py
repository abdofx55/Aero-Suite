"""
fetch_logs_view.py — Feature 13: Fetch Diagnostic Logs View.
Generates an on-the-fly extraction payload to capture Logcat, dmesg, tombstones, and hardware info.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
import theme
from ui.components.dialogs import show_confirm_dialog


class FetchLogsView(QWidget):
    """View for configuring Fetch Diagnostic Logs USB payload."""
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

        lbl_head = QLabel("📋 FETCH DIAGNOSTIC LOGS")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Fix screen issues fast without guessing! 🔍 If an app crashes or your screen acts up, don't worry:\n\n"
            "• 📋 Comprehensive Health Check: Gathers system reports, memory stats, and app crash logs in seconds.\n"
            "• 🛠️ Easy Problem Solving: Packages diagnostic logs into a clean folder on your USB drive.\n"
            "• 🤝 Quick Support: Share the folder with the community or developer to get an instant, pinpoint fix!"
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)

        btn_logs = QPushButton("📋 PREPARE FETCH LOGS USB")
        btn_logs.setProperty("class", "btnPrimary")
        btn_logs.setFixedHeight(44)
        btn_logs.clicked.connect(self._execute_fetch_logs)
        c_layout.addWidget(btn_logs)

        layout.addWidget(card)
        layout.addStretch()

    def _execute_fetch_logs(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = f"Prepare Fetch Logs USB payload on drive {letter}?"
        if not show_confirm_dialog(self, "Confirm Fetch Logs", confirm_msg, confirm_text="📋 Prepare Logs USB"):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_fetch_logs_usb,
            letter,
            success_title="Logs USB Ready",
            success_msg=f"Successfully prepared Fetch Logs payload on drive {letter}!",
            error_title="Preparation Failed"
        )
