"""
terminal.py — Terminal & System Logs UI component.
Displays color-coded terminal messages with timestamping, copy to clipboard, and clear options.
"""
import time
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit, QApplication
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import Qt
import theme
from core.i18n import t


class TerminalWidget(QWidget):
    """Encapsulates the terminal output widget and control header."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.header = QHBoxLayout()
        self.header.setContentsMargins(0, 0, 0, 2)
        self.header.setSpacing(8)
        self.lbl_console = QLabel(t("terminal.header", "💻 TERMINAL & SYSTEM LOGS"))
        self.lbl_console.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {theme.TEXT_MUTED}; letter-spacing: 0.5px;")
        self.header.addWidget(self.lbl_console)

        from ui.components.progress_bar import ProgressControl
        self.progress_control = ProgressControl(self)
        self.header.addWidget(self.progress_control, stretch=1)

        self.btn_copy_log = QPushButton(t("terminal.copy_logs", "📋 Copy Logs"))
        self.btn_copy_log.setFixedHeight(22)
        self.btn_copy_log.setStyleSheet(f"font-size: 10px; padding: 1px 8px; background-color: {theme.SURFACE_2}; color: {theme.TEXT_MUTED}; border: 1px solid {theme.BORDER_SLATE}; border-radius: 4px;")
        self.btn_copy_log.clicked.connect(self.copy_logs)
        self.header.addWidget(self.btn_copy_log)

        self.btn_clear_log = QPushButton(t("terminal.clear", "Clear"))
        self.btn_clear_log.setFixedHeight(22)
        self.btn_clear_log.setStyleSheet(f"font-size: 10px; padding: 1px 8px; background-color: {theme.SURFACE_2}; color: {theme.TEXT_MUTED}; border: 1px solid {theme.BORDER_SLATE}; border-radius: 4px;")
        self.btn_clear_log.clicked.connect(self.clear_logs)
        self.header.addWidget(self.btn_clear_log)
        layout.addLayout(self.header)

        self.terminal_edit = QPlainTextEdit()
        self.terminal_edit.setReadOnly(True)
        self.terminal_edit.setObjectName("terminalEdit")
        self.terminal_edit.setFixedHeight(125)
        self.txt_terminal = self.terminal_edit
        layout.addWidget(self.terminal_edit)

        self.retranslate_ui()

    def retranslate_ui(self):
        """Re-translates terminal header, control buttons, and sets RTL direction."""
        from core.i18n import get_i18n
        is_rtl = get_i18n().is_rtl()

        self.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        self.terminal_edit.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)

        doc = self.terminal_edit.document()
        opt = doc.defaultTextOption()
        opt.setTextDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        opt.setAlignment(Qt.AlignRight if is_rtl else Qt.AlignLeft)
        doc.setDefaultTextOption(opt)

        self.lbl_console.setText(t("terminal.header", "💻 TERMINAL & SYSTEM LOGS"))
        self.btn_copy_log.setText(t("terminal.copy_logs", "📋 Copy Logs"))
        self.btn_clear_log.setText(t("terminal.clear", "Clear"))
        if hasattr(self, "progress_control") and self.progress_control:
            self.progress_control.retranslate_ui()

    def log_message(self, message: str, level: str = "cyan"):
        """Appends colorized, timestamped HTML message to terminal with proper RTL/LTR alignment."""
        t_stamp = time.strftime("[%H:%M:%S]")
        color_map = {
            "cyan": theme.TERM_TEXT_CYAN,
            "mint": theme.TERM_TEXT_MINT,
            "success": theme.TERM_TEXT_MINT,
            "danger": theme.CRIMSON_DANGER,
            "crimson": theme.CRIMSON_DANGER,
            "rose": theme.TERM_TEXT_ROSE,
            "warn": theme.AMBER_WARN,
            "dim": theme.TERM_TEXT_DIM,
            "info": theme.TERM_TEXT_CYAN
        }
        hex_col = color_map.get(level.lower(), theme.TERM_TEXT_CYAN)

        from core.i18n import get_i18n
        is_rtl = get_i18n().is_rtl()

        clean_msg = str(message).replace("\r\n", "\n").rstrip("\n")

        if is_rtl:
            html_msg = (
                f'<div dir="rtl" style="text-align: right; line-height: 140%; margin-bottom: 2px;">'
                f'<span dir="ltr" style="color:{theme.TEXT_DIM}; font-family: Consolas, monospace;">{t_stamp}</span>&lrm; '
                f'<span style="color:{hex_col}; font-family: \'Segoe UI\', Tahoma, sans-serif;">{clean_msg}</span>'
                f'</div>'
            )
        else:
            html_msg = (
                f'<div dir="ltr" style="text-align: left; line-height: 140%; margin-bottom: 2px;">'
                f'<span style="color:{theme.TEXT_DIM}; font-family: Consolas, monospace;">{t_stamp} </span>'
                f'<span style="color:{hex_col}; font-family: Consolas, monospace;">{clean_msg}</span>'
                f'</div>'
            )
        self.terminal_edit.appendHtml(html_msg)
        self.terminal_edit.moveCursor(QTextCursor.End)

    append_log = log_message

    def copy_logs(self):
        """Copies plain terminal text to clipboard."""
        text = self.terminal_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.log_message(t("terminal.copied", "Logs copied to clipboard."), "mint")

    def clear_logs(self):
        """Clears the terminal output."""
        self.terminal_edit.clear()
