"""
backup_view.py — Feature 10: System & Data Backup and PC Vault Sync View.
Allows generating non-destructive vehicle backup payloads and syncing completed car backups to local PC.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
import theme
from ui.components.dialogs import show_confirm_dialog


class BackupView(QWidget):
    """View for configuring Backup USB payloads and PC Vault synchronization."""
    def __init__(self, main_app, backups_dir: str, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.backups_dir = backups_dir
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # Section 1: Prepare Backup USB
        card_prep = QFrame()
        card_prep.setProperty("class", "card")
        cp_layout = QVBoxLayout(card_prep)
        cp_layout.setContentsMargins(18, 16, 18, 16)
        cp_layout.setSpacing(12)

        lbl_head1 = QLabel("💾 SYSTEM & DATA BACKUP")
        lbl_head1.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        cp_layout.addWidget(lbl_head1)

        lbl_desc1 = QLabel(
            "Never lose your personalized setup! 💾 Saves a complete, secure snapshot of your car screen:\n\n"
            "• 📱 All Your Apps & Accounts: Saves your installed apps, logged-in accounts, and app data.\n"
            "• 🎨 Custom Layouts: Keeps your launcher widgets, custom icons, and favorite shortcuts intact.\n"
            "• 📶 Saved Connections: Backs up your paired Bluetooth phones and saved Wi-Fi networks.\n"
            "• 🔒 Total Peace of Mind: Plug the USB into your car, and it automatically extracts your backup in under a minute!"
        )
        lbl_desc1.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc1.setWordWrap(True)
        cp_layout.addWidget(lbl_desc1)

        btn_backup = QPushButton("💾 PREPARE VEHICLE BACKUP USB")
        btn_backup.setProperty("class", "btnPrimary")
        btn_backup.setFixedHeight(38)
        btn_backup.clicked.connect(self._execute_prepare_backup)
        cp_layout.addWidget(btn_backup)
        layout.addWidget(card_prep)

        # Section 2: Sync to PC Vault
        card_sync = QFrame()
        card_sync.setProperty("class", "card")
        cs_layout = QVBoxLayout(card_sync)
        cs_layout.setContentsMargins(18, 16, 18, 16)
        cs_layout.setSpacing(12)

        lbl_head2 = QLabel("📥 SYNC USB BACKUP TO PC VAULT")
        lbl_head2.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.MINT_SUCCESS};")
        cs_layout.addWidget(lbl_head2)

        lbl_desc2 = QLabel("Safely copies your car backup from your USB drive into your PC Vault repository for permanent safekeeping.")
        lbl_desc2.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED}; border: none; background: transparent;")
        lbl_desc2.setWordWrap(True)
        cs_layout.addWidget(lbl_desc2)

        self.btn_sync = QPushButton("📥 SYNC USB BACKUP TO PC VAULT")
        self.btn_sync.setProperty("class", "btnSuccess")
        self.btn_sync.setFixedHeight(38)
        self.btn_sync.clicked.connect(self._execute_sync_to_pc)
        cs_layout.addWidget(self.btn_sync)
        layout.addWidget(card_sync)

        layout.addStretch()
        self.update_sync_button_state()

    def update_sync_button_state(self):
        has_bk = False
        bk_date = ""
        if self.main_app.current_usb:
            has_bk = bool(getattr(self.main_app.current_usb, "has_backup", False))
            bk_date = getattr(self.main_app.current_usb, "backup_date", "")

        if has_bk:
            date_str = f" ({bk_date})" if bk_date else ""
            self.btn_sync.setEnabled(True)
            self.btn_sync.setText(f"📥 SYNC VEHICLE BACKUP TO PC VAULT{date_str}")
        else:
            self.btn_sync.setEnabled(False)
            self.btn_sync.setText("📥 NO VEHICLE BACKUP DETECTED ON USB DRIVE")

    def _execute_prepare_backup(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = (
            f"Are you sure you want to prepare Vehicle Backup USB on drive {letter}?\n\n"
            f"When inserted into the vehicle, this payload safely extracts your applications, configurations, and calibration files."
        )
        if not show_confirm_dialog(self, "Confirm Backup USB", confirm_msg, confirm_text="💾 Prepare Backup USB"):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_backup_usb,
            letter,
            backup_type="personal",
            success_title="Backup USB Ready",
            success_msg=f"Successfully prepared Backup payload on drive {letter}!",
            error_title="Backup Preparation Failed"
        )

    def _execute_sync_to_pc(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._check_usb_ready():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = f"Sync vehicle backup from USB drive {letter} to PC Vault ({self.backups_dir})?"
        if not show_confirm_dialog(self, "Confirm Sync Backup", confirm_msg, confirm_text="📥 Sync to PC"):
            return

        from sync_manager import sync_backup_from_usb_to_pc
        self.main_app.execute_payload_worker(
            sync_backup_from_usb_to_pc,
            letter,
            self.backups_dir,
            success_title="Sync Complete",
            success_msg="Successfully synced vehicle backup archive to PC Vault!",
            error_title="Sync Failed"
        )
