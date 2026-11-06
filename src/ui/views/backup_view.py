"""
backup_view.py — Feature 10: System & Data Backup and PC Vault Sync View.
Allows generating non-destructive vehicle backup payloads (Personal 1:1 or Community Preset)
with optional user media capture, and syncing completed car backups to local PC.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QRadioButton, QButtonGroup, QCheckBox, QLineEdit, QScrollArea, QStackedWidget
)
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
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 12, 16, 12)
        root_layout.setSpacing(0)

        # Scroll area for clean look on different window heights
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.viewport().setAutoFillBackground(False)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 16)
        layout.setSpacing(14)

        # ===================================================================
        # Section 1: Prepare Backup USB
        # ===================================================================
        card_prep = QFrame()
        card_prep.setProperty("class", "card")
        cp_layout = QVBoxLayout(card_prep)
        cp_layout.setContentsMargins(18, 16, 18, 16)
        cp_layout.setSpacing(12)

        self.lbl_head1 = QLabel(t("backup.view_title"))
        self.lbl_head1.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; background: transparent; border: none;")
        cp_layout.addWidget(self.lbl_head1)

        self.lbl_desc1 = QLabel(t("backup.desc"))
        self.lbl_desc1.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 2px 0 6px 0; line-height: 1.4;")
        self.lbl_desc1.setWordWrap(True)
        cp_layout.addWidget(self.lbl_desc1)

        # --- Mode Selection (Personal vs Community) ---
        mode_box = QFrame()
        mode_box.setStyleSheet(f"background-color: {theme.SURFACE_1}; border-radius: 8px; border: 1px solid {theme.BORDER_SLATE};")
        mb_layout = QVBoxLayout(mode_box)
        mb_layout.setContentsMargins(14, 12, 14, 12)
        mb_layout.setSpacing(8)

        self.mode_group = QButtonGroup(self)

        radio_style = f"""
            QRadioButton {{
                font-size: 12px;
                font-weight: bold;
                color: {theme.TEXT_PRIMARY};
                background: transparent;
                border: none;
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid {theme.BORDER_SLATE};
                background-color: {theme.SURFACE_2};
            }}
            QRadioButton::indicator:hover {{
                border-color: {theme.CYAN_PRIMARY};
            }}
            QRadioButton::indicator:checked {{
                background-color: {theme.CYAN_PRIMARY};
                border-color: {theme.CYAN_PRIMARY};
                image: url("assets/checkbox_check.png");
            }}
        """

        self.radio_personal = QRadioButton(t("backup.mode_personal"))
        self.radio_personal.setCursor(Qt.PointingHandCursor)
        self.radio_personal.setStyleSheet(radio_style)
        self.mode_group.addButton(self.radio_personal, 0)
        mb_layout.addWidget(self.radio_personal)

        self.radio_community = QRadioButton(t("backup.mode_community"))
        self.radio_community.setCursor(Qt.PointingHandCursor)
        self.radio_community.setStyleSheet(radio_style)
        self.mode_group.addButton(self.radio_community, 1)
        mb_layout.addWidget(self.radio_community)

        # Subtle separator between mode selection and details
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"background-color: {theme.BORDER_SLATE}; max-height: 1px; border: none; margin: 2px 0;")
        mb_layout.addWidget(divider)

        # Dynamic details row: Fixed height ensures ZERO layout resizing when switching modes
        self.details_row = QWidget()
        self.details_row.setFixedHeight(110)
        det_layout = QHBoxLayout(self.details_row)
        det_layout.setContentsMargins(0, 2, 0, 0)
        det_layout.setSpacing(16)

        # Description hint
        self.lbl_mode_hint = QLabel()
        self.lbl_mode_hint.setAlignment(Qt.AlignTop | Qt.AlignLeading)
        self.lbl_mode_hint.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED}; background: transparent; border: none; line-height: 1.4;")
        self.lbl_mode_hint.setWordWrap(True)
        det_layout.addWidget(self.lbl_mode_hint, stretch=3)

        # Side stacked panel (Page 0: Personal 1:1 security info, Page 1: Community inputs)
        self.stack_side = QStackedWidget()
        self.stack_side.setFixedHeight(102)

        # Page 0: Personal Security Info
        page_personal = QFrame()
        page_personal.setStyleSheet(f"background-color: {theme.SURFACE_2}; border: 1px dashed {theme.BORDER_SLATE}; border-radius: 6px;")
        p_layout = QVBoxLayout(page_personal)
        p_layout.setContentsMargins(10, 8, 10, 8)
        p_layout.setSpacing(4)
        self.lbl_personal_side_title = QLabel(t("backup.personal_side_title", "🔒 Direct 1:1 Personal State"))
        self.lbl_personal_side_title.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        self.lbl_personal_side_desc = QLabel(t("backup.personal_side_desc", "• No metadata or naming required.\n• Automatically binds to vehicle VIN and hardware identity."))
        self.lbl_personal_side_desc.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_MUTED}; border: none; background: transparent; line-height: 1.35;")
        self.lbl_personal_side_desc.setWordWrap(True)
        p_layout.addWidget(self.lbl_personal_side_title)
        p_layout.addWidget(self.lbl_personal_side_desc)
        p_layout.addStretch()
        self.stack_side.addWidget(page_personal)

        # Page 1: Community Metadata Inputs
        page_community = QWidget()
        c_layout = QVBoxLayout(page_community)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(4)

        self.lbl_pname = QLabel(t("backup.preset_name_label", "Preset Name:"))
        self.lbl_pname.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {theme.CYAN_PRIMARY}; background: transparent; border: none;")
        c_layout.addWidget(self.lbl_pname)

        self.txt_preset_name = QLineEdit()
        self.txt_preset_name.setPlaceholderText(t("backup.preset_name_ph", "e.g. Agama Cyber Dark Edition"))
        self.txt_preset_name.setFixedHeight(28)
        self.txt_preset_name.setStyleSheet(
            f"QLineEdit {{ background-color: {theme.SURFACE_2}; color: {theme.TEXT_PRIMARY}; "
            f"border: 1px solid {theme.BORDER_CYAN}; border-radius: 4px; padding: 0 8px; font-size: 11px; }} "
            f"QLineEdit:focus {{ border: 1px solid {theme.CYAN_PRIMARY}; }}"
        )
        c_layout.addWidget(self.txt_preset_name)

        self.lbl_author = QLabel(t("backup.author_label", "Author / Creator:"))
        self.lbl_author.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {theme.CYAN_PRIMARY}; background: transparent; border: none;")
        c_layout.addWidget(self.lbl_author)

        self.txt_author = QLineEdit()
        self.txt_author.setPlaceholderText(t("backup.author_ph", "e.g. Abdo FX"))
        self.txt_author.setFixedHeight(28)
        self.txt_author.setStyleSheet(
            f"QLineEdit {{ background-color: {theme.SURFACE_2}; color: {theme.TEXT_PRIMARY}; "
            f"border: 1px solid {theme.BORDER_CYAN}; border-radius: 4px; padding: 0 8px; font-size: 11px; }} "
            f"QLineEdit:focus {{ border: 1px solid {theme.CYAN_PRIMARY}; }}"
        )
        c_layout.addWidget(self.txt_author)
        self.stack_side.addWidget(page_community)

        det_layout.addWidget(self.stack_side, stretch=2)
        mb_layout.addWidget(self.details_row)
        cp_layout.addWidget(mode_box)

        # --- User Media Checkbox ---
        media_box = QFrame()
        media_box.setStyleSheet(f"background-color: {theme.SURFACE_1}; border-radius: 6px; border: 1px solid {theme.BORDER_SLATE};")
        med_layout = QVBoxLayout(media_box)
        med_layout.setContentsMargins(14, 10, 14, 10)
        med_layout.setSpacing(4)

        self.chk_media = QCheckBox(t("backup.chk_media"))
        self.chk_media.setCursor(Qt.PointingHandCursor)
        self.chk_media.setChecked(False)
        self.chk_media.setStyleSheet(
            f"QCheckBox {{ font-size: 12px; font-weight: bold; color: {theme.TEXT_PRIMARY}; background: transparent; border: none; }}"
            f"QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {theme.BORDER_SLATE}; background-color: {theme.SURFACE_2}; }}"
            f"QCheckBox::indicator:hover {{ border-color: {theme.CYAN_PRIMARY}; }}"
            f"QCheckBox::indicator:checked {{ background-color: {theme.CYAN_PRIMARY}; border-color: {theme.CYAN_PRIMARY}; image: url('assets/checkbox_check.png'); }}"
        )
        med_layout.addWidget(self.chk_media)

        self.lbl_media_hint = QLabel(t("backup.media_hint"))
        self.lbl_media_hint.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_MUTED}; background: transparent; border: none; padding-left: 20px;")
        self.lbl_media_hint.setWordWrap(True)
        med_layout.addWidget(self.lbl_media_hint)

        cp_layout.addWidget(media_box)

        # Action Buttons for Backup Preparation & Basket
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_backup = QPushButton(t("backup.btn_prepare_personal"))
        self.btn_backup.setProperty("class", "btnPrimary")
        self.btn_backup.setFixedHeight(42)
        self.btn_backup.clicked.connect(self._execute_prepare_backup)
        btn_box.addWidget(self.btn_backup, 1)

        self.btn_add_basket = QPushButton(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.btn_add_basket.setFixedHeight(42)
        self.btn_add_basket.setCursor(Qt.PointingHandCursor)
        self.btn_add_basket.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.SURFACE_2};
                border: 1px solid {theme.BORDER_CYAN};
                color: {theme.CYAN_PRIMARY};
                border-radius: 6px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme.CYAN_ALPHA_15};
            }}
        """)
        self.btn_add_basket.clicked.connect(self._on_add_to_basket)
        btn_box.addWidget(self.btn_add_basket, 1)

        cp_layout.addLayout(btn_box)

        layout.addWidget(card_prep)

        # ===================================================================
        # Section 2: Sync to PC Vault
        # ===================================================================
        card_sync = QFrame()
        card_sync.setProperty("class", "card")
        cs_layout = QVBoxLayout(card_sync)
        cs_layout.setContentsMargins(18, 16, 18, 16)
        cs_layout.setSpacing(12)

        self.lbl_head2 = QLabel(t("backup.sync_title"))
        self.lbl_head2.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.MINT_SUCCESS}; background: transparent; border: none;")
        cs_layout.addWidget(self.lbl_head2)

        self.lbl_desc2 = QLabel(t("backup.sync_desc"))
        self.lbl_desc2.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED}; border: none; background: transparent; padding: 2px 0 6px 0; line-height: 1.4;")
        self.lbl_desc2.setWordWrap(True)
        cs_layout.addWidget(self.lbl_desc2)

        self.btn_sync = QPushButton(t("backup.sync_title"))
        self.btn_sync.setProperty("class", "btnSuccess")
        self.btn_sync.setFixedHeight(40)
        self.btn_sync.clicked.connect(self._execute_sync_to_pc)
        cs_layout.addWidget(self.btn_sync)

        layout.addWidget(card_sync)
        layout.addStretch()

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

        # Wire Mode Toggles
        self.radio_personal.toggled.connect(self._on_mode_changed)
        self.radio_community.toggled.connect(self._on_mode_changed)
        self.radio_personal.setChecked(True)
        self._on_mode_changed()
        self.update_sync_button_state()

    def _on_mode_changed(self):
        """Switches active page in stack_side and updates hints and button text."""
        is_comm = self.radio_community.isChecked()
        self.stack_side.setCurrentIndex(1 if is_comm else 0)
        if is_comm:
            self.lbl_mode_hint.setText(t("backup.hint_community"))
            self.btn_backup.setText(t("backup.btn_prepare_community"))
        else:
            self.lbl_mode_hint.setText(t("backup.hint_personal"))
            self.btn_backup.setText(t("backup.btn_prepare_personal"))

    def retranslate_ui(self):
        """Re-translates elements in BackupView."""
        self.lbl_head1.setText(t("backup.view_title"))
        self.lbl_desc1.setText(t("backup.desc"))
        self.radio_personal.setText(t("backup.mode_personal"))
        self.radio_community.setText(t("backup.mode_community"))
        self.lbl_personal_side_title.setText(t("backup.personal_side_title", "🔒 Direct 1:1 Personal State"))
        self.lbl_personal_side_desc.setText(t("backup.personal_side_desc", "• No metadata or naming required.\n• Automatically binds to vehicle VIN and hardware identity."))
        self.lbl_pname.setText(t("backup.preset_name_label", "Preset Name:"))
        self.txt_preset_name.setPlaceholderText(t("backup.preset_name_ph", "e.g. Agama Cyber Dark Edition"))
        self.lbl_author.setText(t("backup.author_label", "Author / Creator:"))
        self.txt_author.setPlaceholderText(t("backup.author_ph", "e.g. Abdo FX"))
        self.chk_media.setText(t("backup.chk_media"))
        self.lbl_media_hint.setText(t("backup.media_hint"))
        self.lbl_head2.setText(t("backup.sync_title"))
        self.lbl_desc2.setText(t("backup.sync_desc"))
        self.btn_add_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self._on_mode_changed()
        self.update_sync_button_state()

    def _on_add_to_basket(self):
        from services.basket_service import BasketItem
        is_comm = self.radio_community.isChecked()
        b_type = "community" if is_comm else "personal"
        inc_media = self.chk_media.isChecked()
        p_name = self.txt_preset_name.text().strip() if is_comm else ""
        p_author = self.txt_author.text().strip() if is_comm else ""

        mode_desc = t("backup.mode_community") if is_comm else t("backup.mode_personal")
        media_desc = t("backup.media_included") if inc_media else t("backup.media_skipped")
        summary = f"{mode_desc} ({media_desc})"

        item = BasketItem(
            action_type="backup",
            title=t("backup.view_title", "Full System & Data Backup"),
            summary=summary,
            config={
                "backup_type": b_type,
                "include_media": inc_media,
                "preset_name": p_name,
                "author": p_author
            },
            requires_reboot=False
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def update_sync_button_state(self):
        has_bk = False
        bk_date = ""
        letter = ""
        if self.main_app.current_usb:
            has_bk = bool(getattr(self.main_app.current_usb, "has_backup", False))
            bk_date = getattr(self.main_app.current_usb, "backup_date", "")
            letter = getattr(self.main_app.current_usb, "letter", "")

        if has_bk and letter:
            from sync_manager import find_existing_vault_backup
            existing = find_existing_vault_backup(letter, self.backups_dir)
            date_str = f" ({bk_date})" if bk_date else ""
            self.btn_sync.setEnabled(True)
            if existing:
                self.btn_sync.setText(t("backup.btn_sync_already_synced", f"✓ النسخة محفوظة بالكمبيوتر (إعادة المزامنة){date_str}", date_str=date_str))
                self.btn_sync.setProperty("class", "btnSecondary")
            else:
                self.btn_sync.setText(t("backup.btn_sync_ready", date_str=date_str))
                self.btn_sync.setProperty("class", "btnSuccess")
            self.btn_sync.style().unpolish(self.btn_sync)
            self.btn_sync.style().polish(self.btn_sync)
        else:
            self.btn_sync.setEnabled(False)
            self.btn_sync.setText(t("backup.btn_sync_no_backup"))
            self.btn_sync.setProperty("class", "btnSuccess")
            self.btn_sync.style().unpolish(self.btn_sync)
            self.btn_sync.style().polish(self.btn_sync)

    def _execute_prepare_backup(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        is_comm = self.radio_community.isChecked()
        b_type = "community" if is_comm else "personal"
        inc_media = self.chk_media.isChecked()
        p_name = self.txt_preset_name.text().strip() if is_comm else ""
        p_author = self.txt_author.text().strip() if is_comm else ""

        mode_name = t("backup.mode_community") if is_comm else t("backup.mode_personal")
        media_status = t("backup.media_included") if inc_media else t("backup.media_skipped")

        confirm_msg = t("backup.confirm_msg", letter=letter, mode=mode_name, media_status=media_status)
        confirm_btn_text = t("backup.btn_prepare_community") if is_comm else t("backup.btn_prepare_personal")

        if not show_confirm_dialog(self, t("backup.confirm_title"), confirm_msg, confirm_text=confirm_btn_text):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_backup_usb,
            letter,
            backup_type=b_type,
            include_media=inc_media,
            preset_name=p_name,
            author=p_author,
            success_title=t("backup.success_title"),
            success_msg=t("backup.success_msg", letter=letter, mode=mode_name),
            error_title=t("common.preparation_failed")
        )

    def _execute_sync_to_pc(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._check_usb_ready():
            return

        import os
        letter = self.main_app.current_usb.letter
        from sync_manager import find_existing_vault_backup, sync_backup_from_usb_to_pc
        existing = find_existing_vault_backup(letter, self.backups_dir)

        force_sync = False
        if existing:
            folder_name = os.path.basename(existing)
            warn_title = t("backup.warn_duplicate_title", "النسخة موجودة بالفعل بالكمبيوتر")
            warn_msg = t(
                "backup.warn_duplicate_msg",
                f"تنبيه: النسخة الاحتياطية الموجودة على الفلاشة ({letter}) محفوظة بالفعل على الكمبيوتر في المجلد:\n📁 {folder_name}\n\nإعادة العملية ستؤدي إلى استبدال وتحديث الملفات المحفوظة (Overwrite).\n\nهل تريد بالتأكيد إعادة مزامنة النسخة واستبدالها؟",
                letter=letter,
                folder=folder_name
            )
            btn_overwrite = t("backup.btn_overwrite_confirm", "⚠️ نعم، استبدال وإعادة المزامنة")
            if not show_confirm_dialog(self, warn_title, warn_msg, confirm_text=btn_overwrite, is_danger=True):
                return
            force_sync = True
        else:
            confirm_msg = t("backup.confirm_sync_msg", letter=letter, vault_dir=self.backups_dir)
            if not show_confirm_dialog(self, t("backup.confirm_sync_title"), confirm_msg, confirm_text=t("backup.btn_sync_confirm", "📥 Sync to PC")):
                return

        self.main_app.execute_payload_worker(
            sync_backup_from_usb_to_pc,
            letter,
            self.backups_dir,
            force=force_sync,
            success_title=t("backup.sync_success_title"),
            success_msg=t("backup.sync_success_msg"),
            error_title=t("common.sync_failed", default="Sync Failed"),
            has_guard=False
        )
