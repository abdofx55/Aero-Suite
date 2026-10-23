"""
restore_view.py — Feature 11: Restore Vehicle From Backup View.
Allows selecting a saved PC Vault backup archive and building a 12-step automated vehicle restore payload.
"""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QFrame
import theme
from core.i18n import t
from ui.components.dialogs import show_confirm_dialog, show_error_dialog
from sync_manager import get_local_backups


class RestoreView(QWidget):
    """View for configuring Restore from PC Vault payload."""
    def __init__(self, main_app, backups_dir: str, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.backups_dir = backups_dir
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

        self.lbl_head = QLabel(t("restore.view_title"))
        self.lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        c_layout.addWidget(self.lbl_head)

        self.lbl_desc = QLabel(t("restore.desc"))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        self.lbl_desc.setWordWrap(True)
        c_layout.addWidget(self.lbl_desc)

        self.restore_combo = QComboBox()
        self.restore_combo.currentIndexChanged.connect(lambda: self.update_restore_button_state())
        c_layout.addWidget(self.restore_combo)

        self.btn_restore = QPushButton(t("restore.btn_action"))
        self.btn_restore.setProperty("class", "btnPrimary")
        self.btn_restore.setFixedHeight(44)
        self.btn_restore.clicked.connect(self._execute_restore)
        c_layout.addWidget(self.btn_restore)

        layout.addWidget(card)
        layout.addStretch()

        self.populate_restore_combo()

    def retranslate_ui(self):
        """Re-translates elements in RestoreView."""
        self.lbl_head.setText(t("restore.view_title"))
        self.lbl_desc.setText(t("restore.desc"))
        self.populate_restore_combo()
        self.update_restore_button_state()

    def populate_restore_combo(self):
        self.restore_combo.clear()
        backups = get_local_backups(self.backups_dir)
        if not backups:
            self.restore_combo.addItem(t("restore.empty"))
            self.restore_combo.setEnabled(False)
        else:
            for b in backups:
                b_name = b.get("folder_name") or b.get("name") or os.path.basename(b["path"])
                b_date = b.get("formatted_datetime") or b.get("date", "Unknown date")
                b_size = b.get("size_str") or f"{b.get('size_mb', 0):.1f} MB"
                self.restore_combo.addItem(f"{b_name} ({b_date}, {b_size})", userData=b["path"])
            self.restore_combo.setEnabled(True)
        self.update_restore_button_state()

    def update_restore_button_state(self):
        b_path = self.restore_combo.currentData()
        if b_path and os.path.exists(b_path):
            self.btn_restore.setEnabled(True)
            self.btn_restore.setText(t("restore.btn_action"))
        else:
            self.btn_restore.setEnabled(False)
            self.btn_restore.setText(t("restore.btn_idle"))

    def _execute_restore(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        backup_path = self.restore_combo.currentData()
        if not backup_path or not os.path.exists(backup_path):
            show_error_dialog(self, t("common.error"), t("restore.empty"))
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = t("restore.confirm_msg", letter=letter, backup_name=os.path.basename(backup_path))
        if not show_confirm_dialog(self, t("restore.confirm_title"), confirm_msg, confirm_text=t("restore.btn_confirm", "📥 Prepare Restore USB")):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_restore_usb,
            letter,
            local_backup_folder=backup_path,
            success_title=t("restore.success_title"),
            success_msg=t("restore.success_msg", letter=letter),
            error_title=t("common.preparation_failed")
        )
