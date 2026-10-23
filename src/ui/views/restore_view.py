"""
restore_view.py — Feature 11: Restore Vehicle From Backup View.
Allows selecting a saved PC Vault backup archive and building a 12-step automated vehicle restore payload.
"""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QFrame
import theme
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

        lbl_head = QLabel("📥 RESTORE VEHICLE FROM BACKUP")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Get all your apps and settings back in minutes! 📥 Restores your car screen to your favorite saved backup from your PC:\n\n"
            "• 🚀 One-Step Full Recovery: Installs all your saved apps, logins, and widget arrangements automatically.\n"
            "• 📶 Instant Reconnection: Reconnects your Bluetooth phones and Wi-Fi networks without re-typing passwords.\n"
            "• ⚡ Fast & Smart: Skips apps that are already on the screen to finish the restore super fast!"
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)

        self.restore_combo = QComboBox()
        self.restore_combo.currentIndexChanged.connect(lambda: self.update_restore_button_state())
        c_layout.addWidget(self.restore_combo)

        self.btn_restore = QPushButton("📥 PREPARE RESTORE USB")
        self.btn_restore.setProperty("class", "btnPrimary")
        self.btn_restore.setFixedHeight(44)
        self.btn_restore.clicked.connect(self._execute_restore)
        c_layout.addWidget(self.btn_restore)

        layout.addWidget(card)
        layout.addStretch()

        self.populate_restore_combo()

    def populate_restore_combo(self):
        self.restore_combo.clear()
        backups = get_local_backups(self.backups_dir)
        if not backups:
            self.restore_combo.addItem("No saved backups in PC Vault")
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
            self.btn_restore.setText("📥 PREPARE RESTORE USB")
        else:
            self.btn_restore.setEnabled(False)
            self.btn_restore.setText("⚠️ NO SAVED BACKUPS AVAILABLE IN PC VAULT")

    def _execute_restore(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        backup_path = self.restore_combo.currentData()
        if not backup_path or not os.path.exists(backup_path):
            show_error_dialog(self, "No Backup Selected", "Please select a valid backup archive.")
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = f"Prepare Restore USB on drive {letter} using backup '{os.path.basename(backup_path)}'?"
        if not show_confirm_dialog(self, "Confirm Restore USB", confirm_msg, confirm_text="📥 Prepare Restore USB"):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_restore_usb,
            letter,
            local_backup_folder=backup_path,
            success_title="Restore USB Ready",
            success_msg=f"Successfully prepared Restore USB on drive {letter}!",
            error_title="Restore Preparation Failed"
        )
