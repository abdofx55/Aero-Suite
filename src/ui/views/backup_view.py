"""
backup_view.py — Feature 10: System & Data Backup and PC Vault Sync View.
Allows generating non-destructive vehicle backup payloads and syncing completed car backups to local PC.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
import theme
from core.i18n import t
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

        self.lbl_head1 = QLabel(t("backup.view_title"))
        self.lbl_head1.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        cp_layout.addWidget(self.lbl_head1)

        self.lbl_desc1 = QLabel(t("backup.desc"))
        self.lbl_desc1.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        self.lbl_desc1.setWordWrap(True)
        cp_layout.addWidget(self.lbl_desc1)

        self.btn_backup = QPushButton(t("backup.btn_prepare"))
        self.btn_backup.setProperty("class", "btnPrimary")
        self.btn_backup.setFixedHeight(38)
        self.btn_backup.clicked.connect(self._execute_prepare_backup)
        cp_layout.addWidget(self.btn_backup)
        layout.addWidget(card_prep)

        # Section 2: Sync to PC Vault
        card_sync = QFrame()
        card_sync.setProperty("class", "card")
        cs_layout = QVBoxLayout(card_sync)
        cs_layout.setContentsMargins(18, 16, 18, 16)
        cs_layout.setSpacing(12)

        self.lbl_head2 = QLabel(t("backup.sync_title"))
        self.lbl_head2.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.MINT_SUCCESS};")
        cs_layout.addWidget(self.lbl_head2)

        self.lbl_desc2 = QLabel(t("backup.sync_desc"))
        self.lbl_desc2.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED}; border: none; background: transparent;")
        self.lbl_desc2.setWordWrap(True)
        cs_layout.addWidget(self.lbl_desc2)

        self.btn_sync = QPushButton(t("backup.sync_title"))
        self.btn_sync.setProperty("class", "btnSuccess")
        self.btn_sync.setFixedHeight(38)
        self.btn_sync.clicked.connect(self._execute_sync_to_pc)
        cs_layout.addWidget(self.btn_sync)
        layout.addWidget(card_sync)

        layout.addStretch()
        self.update_sync_button_state()

    def retranslate_ui(self):
        """Re-translates elements in BackupView."""
        self.lbl_head1.setText(t("backup.view_title"))
        self.lbl_desc1.setText(t("backup.desc"))
        self.btn_backup.setText(t("backup.btn_prepare"))
        self.lbl_head2.setText(t("backup.sync_title"))
        self.lbl_desc2.setText(t("backup.sync_desc"))
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
            self.btn_sync.setText(t("backup.btn_sync_ready", date_str=date_str))
        else:
            self.btn_sync.setEnabled(False)
            self.btn_sync.setText(t("backup.btn_sync_no_backup"))

    def _execute_prepare_backup(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = t("backup.confirm_msg", letter=letter)
        if not show_confirm_dialog(self, t("backup.confirm_title"), confirm_msg, confirm_text="💾 Prepare Backup USB"):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_backup_usb,
            letter,
            backup_type="personal",
            success_title=t("backup.success_title"),
            success_msg=t("backup.success_msg", letter=letter),
            error_title=t("common.preparation_failed")
        )

    def _execute_sync_to_pc(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._check_usb_ready():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = t("backup.confirm_sync_msg", letter=letter, vault_dir=self.backups_dir)
        if not show_confirm_dialog(self, t("backup.confirm_sync_title"), confirm_msg, confirm_text="📥 Sync to PC"):
            return

        from sync_manager import sync_backup_from_usb_to_pc
        self.main_app.execute_payload_worker(
            sync_backup_from_usb_to_pc,
            letter,
            self.backups_dir,
            success_title=t("backup.sync_success_title"),
            success_msg=t("backup.sync_success_msg"),
            error_title=t("common.sync_failed", default="Sync Failed")
        )
