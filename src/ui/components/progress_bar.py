"""
progress_bar.py — Smooth Progress Bar & Status Control component.
Integrated directly into the Terminal header for compact, modern IDE layout.
Uses QPropertyAnimation for fluid visual scaling without jitter or frozen steps.
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QProgressBar
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QTimer
import theme
from core.i18n import t, get_i18n

MAX_STATUS_CHARS = 45


def truncate_status(text: str, max_chars: int = MAX_STATUS_CHARS) -> str:
    """Truncates status text to max_chars while appending ellipsis if exceeded."""
    if not text:
        return ""
    clean = str(text).strip()
    if len(clean) <= max_chars:
        return clean
    return clean[:max_chars - 3] + "..."


class ProgressControl(QWidget):
    """Compact status and progress control component designed for terminal header integration."""
    cancel_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_status = ""
        self._init_ui()

    def _init_ui(self):
        is_rtl = get_i18n().is_rtl()
        self.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        # Status Label with smart truncation & hover tooltip
        self.lbl_status = QLabel("")
        self.lbl_status.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        self.lbl_status.setAlignment(Qt.AlignLeading | Qt.AlignVCenter)
        self._apply_label_style(is_rtl)
        self._set_status_text(t("app.idle_status", "System Idle — Ready for operation."))
        layout.addWidget(self.lbl_status, stretch=1)

        # Sleek Slim Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setFixedWidth(160)
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {theme.BG_BASE};
                border: 1px solid {theme.BORDER_SLATE};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {theme.CYAN_PRIMARY};
                border-radius: 2px;
            }}
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Percentage Badge
        self.lbl_percent = QLabel("")
        self.lbl_percent.setFixedWidth(36)
        self.lbl_percent.setAlignment(Qt.AlignCenter)
        self.lbl_percent.setStyleSheet(
            f"font-size: 10px; font-weight: bold; color: {theme.CYAN_PRIMARY}; font-family: 'Space Grotesk', 'Segoe UI', sans-serif;"
        )
        self.lbl_percent.setVisible(False)
        layout.addWidget(self.lbl_percent)

        # Cancel Button
        self.btn_cancel_op = QPushButton(t("common.cancel", "✖ Cancel"))
        self.btn_cancel_op.setObjectName("btnCancelOp")
        self.btn_cancel_op.setFixedHeight(20)
        self.btn_cancel_op.setFixedWidth(64)
        self.btn_cancel_op.setCursor(Qt.PointingHandCursor)
        self.btn_cancel_op.setStyleSheet(
            f"background-color: {theme.SURFACE_3}; color: {theme.CRIMSON_DANGER}; "
            f"border: 1px solid {theme.CRIMSON_DIM}; border-radius: 4px; padding: 1px 6px; "
            f"font-size: 10px; font-weight: bold;"
        )
        self.btn_cancel_op.setVisible(False)
        self.btn_cancel_op.clicked.connect(self.cancel_clicked.emit)
        layout.addWidget(self.btn_cancel_op)

        # Aliases for compatibility
        self.bar = self.progress_bar
        self.btn_cancel = self.btn_cancel_op

        # Smooth animation interpolation
        self.progress_anim = QPropertyAnimation(self.progress_bar, b"value")
        self.progress_bar.valueChanged.connect(self._on_value_changed)

    def _set_status_text(self, text: str):
        self._full_status = (text or "").strip()
        self.lbl_status.setToolTip(self._full_status)
        self.lbl_status.setText(truncate_status(self._full_status, MAX_STATUS_CHARS))

    def _on_value_changed(self, val: int):
        pct = val // 10
        if pct > 0:
            self.lbl_percent.setText(f"{pct}%")
        else:
            self.lbl_percent.setText("")

    def _apply_label_style(self, is_rtl: bool):
        font_family = "font-family: 'Segoe UI', 'Tahoma', 'Cairo', sans-serif;" if is_rtl else ""
        self.lbl_status.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED}; {font_family}")

    def retranslate_ui(self):
        """Re-translates idle status label, cancel button, and realigns for RTL/LTR."""
        is_rtl = get_i18n().is_rtl()
        self.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        self.lbl_status.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        self.lbl_status.setAlignment(Qt.AlignLeading | Qt.AlignVCenter)
        self._apply_label_style(is_rtl)

        if not self.progress_bar.isVisible() or self.progress_bar.value() == 0 or self.progress_bar.value() == 1000:
            self._set_status_text(t("app.idle_status", "System Idle — Ready for operation."))
        self.btn_cancel_op.setText(t("common.cancel", "✖ Cancel"))

    def reset(self):
        self.progress_anim.stop()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.lbl_percent.setText("0%")
        self.lbl_percent.setVisible(True)
        self._set_status_text(t("progress.preparing_op", "Preparing operation..."))
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setVisible(True)

    def show_control(self):
        self.progress_bar.setVisible(True)
        self.lbl_percent.setVisible(True)
        self.btn_cancel.setVisible(True)

    def set_progress(self, target_val: int, status_text: str = ""):
        self.smooth_set_progress(target_val, status_text)

    def finish(self, success: bool):
        self.btn_cancel.setVisible(False)
        idle_msg = t("app.idle_status", "System Idle — Ready for operation.")
        if success:
            self.smooth_set_progress(1000, idle_msg)
            self.lbl_percent.setText("100%")
            QTimer.singleShot(1500, self._on_finish_reset)
        else:
            self.smooth_set_progress(0, idle_msg)
            self._on_finish_reset()

    def _on_finish_reset(self):
        idle_msg = t("app.idle_status", "System Idle — Ready for operation.")
        self.progress_anim.stop()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.lbl_percent.setText("")
        self.lbl_percent.setVisible(False)
        self.btn_cancel.setVisible(False)
        self._set_status_text(idle_msg)

    def smooth_set_progress(self, target_val: int, status_text: str = ""):
        """Smoothly interpolates progress value to target percentage (0-1000 scale)."""
        if status_text:
            self._set_status_text(status_text)

        target_val = max(0, min(1000, int(target_val)))
        if target_val > 0 and not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)
            self.lbl_percent.setVisible(True)

        cur = self.progress_bar.value()
        if target_val <= cur:
            if target_val == 0:
                self.progress_anim.stop()
                self.progress_bar.setValue(0)
                self.lbl_percent.setText("")
            return

        diff = target_val - cur
        duration = min(200, max(50, int(diff * 1.5)))
        if target_val >= 1000:
            duration = 150

        self.progress_anim.stop()
        self.progress_anim.setDuration(duration)
        self.progress_anim.setStartValue(cur)
        self.progress_anim.setEndValue(target_val)
        self.progress_anim.start()

    def set_operation_state(self, is_busy: bool, loading_text: str = ""):
        """Updates UI visual state between busy/loading and idle."""
        self.btn_cancel_op.setVisible(is_busy)
        if is_busy:
            self.reset()
            self.smooth_set_progress(10, loading_text or t("progress.preparing_op", "Operation in progress..."))
        else:
            self.finish(True)
