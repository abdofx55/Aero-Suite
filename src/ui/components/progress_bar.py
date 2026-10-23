"""
progress_bar.py — Smooth Progress Bar & Status Control component.
Uses QPropertyAnimation for fluid visual scaling without jitter or frozen steps.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QTimer
import theme


class ProgressControl(QWidget):
    """Encapsulates the progress bar, live status label, and cancel button."""
    cancel_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        prog_bar = QHBoxLayout()
        prog_bar.setContentsMargins(0, 0, 0, 0)
        prog_bar.setSpacing(8)

        self.lbl_status = QLabel("System Idle — Ready for operation.")
        self.lbl_status.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED};")
        prog_bar.addWidget(self.lbl_status, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(240)
        prog_bar.addWidget(self.progress_bar)

        self.btn_cancel_op = QPushButton("✖ Cancel")
        self.btn_cancel_op.setObjectName("btnCancelOp")
        self.btn_cancel_op.setFixedHeight(22)
        self.btn_cancel_op.setStyleSheet(
            f"background-color: {theme.SURFACE_3}; color: {theme.CRIMSON_DANGER}; "
            f"border: 1px solid {theme.BORDER_SLATE}; border-radius: 4px; padding: 2px 8px; "
            f"font-size: 10px; font-weight: bold;"
        )
        self.btn_cancel_op.setVisible(False)
        self.btn_cancel_op.clicked.connect(self.cancel_clicked.emit)
        prog_bar.addWidget(self.btn_cancel_op)
        layout.addLayout(prog_bar)

        # Aliases for compatibility
        self.bar = self.progress_bar
        self.btn_cancel = self.btn_cancel_op

        # Smooth animation interpolation
        self.progress_anim = QPropertyAnimation(self.progress_bar, b"value")

    def reset(self):
        self.progress_anim.stop()
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Preparing operation...")
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setVisible(True)

    def show_control(self):
        self.btn_cancel.setVisible(True)

    def set_progress(self, target_val: int, status_text: str = ""):
        self.smooth_set_progress(target_val, status_text)

    def finish(self, success: bool):
        self.btn_cancel.setVisible(False)
        if success:
            self.smooth_set_progress(100, "System Idle — Ready for operation.")
            QTimer.singleShot(1500, lambda: self.smooth_set_progress(0))
        else:
            self.smooth_set_progress(0, "System Idle — Ready for operation.")

    def smooth_set_progress(self, target_val: int, status_text: str = ""):
        """Smoothly interpolates progress value to target percentage."""
        if status_text:
            self.lbl_status.setText(status_text)

        cur = self.progress_bar.value()
        if target_val <= cur:
            if target_val == 0:
                self.progress_anim.stop()
                self.progress_bar.setValue(0)
            return

        diff = target_val - cur
        duration = min(280, max(80, diff * 12))
        if target_val >= 100:
            duration = 180

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
            self.smooth_set_progress(5, loading_text or "Operation in progress...")
        else:
            self.finish(True)
