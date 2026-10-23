"""
terminal.py — Terminal & System Logs UI component.
Displays color-coded terminal messages with timestamping, copy to clipboard, and clear options.
"""
import time
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit, QApplication
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import Qt
import theme


class TerminalWidget(QWidget):
    """Encapsulates the terminal output widget and control header."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 2)
        lbl_console = QLabel("💻 TERMINAL & SYSTEM LOGS")
        lbl_console.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {theme.TEXT_MUTED}; letter-spacing: 0.5px;")
        header.addWidget(lbl_console)
        header.addStretch()

        btn_copy_log = QPushButton("📋 Copy Logs")
        btn_copy_log.setFixedHeight(22)
        btn_copy_log.setStyleSheet(f"font-size: 10px; padding: 1px 8px; background-color: {theme.SURFACE_2}; color: {theme.TEXT_MUTED}; border: 1px solid {theme.BORDER_SLATE}; border-radius: 4px;")
        btn_copy_log.clicked.connect(self.copy_logs)
        header.addWidget(btn_copy_log)

        btn_clear_log = QPushButton("Clear")
        btn_clear_log.setFixedHeight(22)
        btn_clear_log.setStyleSheet(f"font-size: 10px; padding: 1px 8px; background-color: {theme.SURFACE_2}; color: {theme.TEXT_MUTED}; border: 1px solid {theme.BORDER_SLATE}; border-radius: 4px;")
        btn_clear_log.clicked.connect(self.clear_logs)
        header.addWidget(btn_clear_log)
        layout.addLayout(header)

        self.terminal_edit = QPlainTextEdit()
        self.terminal_edit.setReadOnly(True)
        self.terminal_edit.setObjectName("terminalArea")
        self.terminal_edit.setFixedHeight(125)
        self.txt_terminal = self.terminal_edit
        layout.addWidget(self.terminal_edit)

    def log_message(self, message: str, level: str = "cyan"):
        """Appends colorized, timestamped HTML message to terminal."""
        t_stamp = time.strftime("[%H:%M:%S] ")
        color_map = {
            "cyan": theme.TERM_TEXT_CYAN,
            "mint": theme.TERM_TEXT_MINT,
            "success": theme.TERM_TEXT_MINT,
            "danger": theme.CRIMSON_DANGER,
            "rose": theme.TERM_TEXT_ROSE,
            "warn": theme.AMBER_WARN,
            "dim": theme.TERM_TEXT_DIM
        }
        hex_col = color_map.get(level.lower(), theme.TERM_TEXT_CYAN)
        html_msg = f'<span style="color:{theme.TEXT_DIM};">{t_stamp}</span><span style="color:{hex_col};">{message}</span>'
        self.terminal_edit.appendHtml(html_msg)
        self.terminal_edit.moveCursor(QTextCursor.End)

    append_log = log_message

    def copy_logs(self):
        """Copies plain terminal text to clipboard."""
        text = self.terminal_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.log_message("Logs copied to clipboard.", "mint")

    def clear_logs(self):
        """Clears the terminal output."""
        self.terminal_edit.clear()
