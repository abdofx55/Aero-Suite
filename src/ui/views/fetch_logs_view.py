"""
fetch_logs_view.py — Feature 13: Fetch Diagnostic Logs View.
Generates an on-the-fly extraction payload to capture Logcat, dmesg, tombstones, and hardware info.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
import theme
from core.i18n import t
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

        self.lbl_head = QLabel(t("fetch_logs.view_title"))
        self.lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        c_layout.addWidget(self.lbl_head)

        self.lbl_desc = QLabel(t("fetch_logs.desc"))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        self.lbl_desc.setWordWrap(True)
        c_layout.addWidget(self.lbl_desc)

        self.btn_logs = QPushButton(t("fetch_logs.btn_action"))
        self.btn_logs.setProperty("class", "btnPrimary")
        self.btn_logs.setFixedHeight(44)
        self.btn_logs.clicked.connect(self._execute_fetch_logs)
        c_layout.addWidget(self.btn_logs)

        layout.addWidget(card)
        layout.addStretch()

    def retranslate_ui(self):
        """Re-translates elements in FetchLogsView."""
        self.lbl_head.setText(t("fetch_logs.view_title"))
        self.lbl_desc.setText(t("fetch_logs.desc"))
        self.btn_logs.setText(t("fetch_logs.btn_action"))

    def _execute_fetch_logs(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = t("fetch_logs.confirm_msg", letter=letter)
        if not show_confirm_dialog(self, t("fetch_logs.confirm_title"), confirm_msg, confirm_text=t("fetch_logs.btn_confirm", "📋 Prepare Logs USB")):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_fetch_logs_usb,
            letter,
            success_title=t("fetch_logs.success_title"),
            success_msg=t("fetch_logs.success_msg", letter=letter),
            error_title=t("common.preparation_failed")
        )
