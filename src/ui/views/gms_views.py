"""
gms_views.py — Features 5 & 6: Google Play Services Setup and Removal Views.
Provides dedicated interfaces for calibrated GMS injection (Framework, Services, Login, Store)
and clean system-level GMS removal.
Localized dynamically via core.i18n.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
import theme
from core.i18n import t
from ui.components.dialogs import show_confirm_dialog


class InstallGmsView(QWidget):
    """View for preparing Google Play Services installation USB."""
    def __init__(self, main_app, gms_dir: str, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.gms_dir = gms_dir
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

        lbl_head = QLabel(t("install_gms.view_title", "🌐 GOOGLE PLAY SERVICES SETUP"))
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(t("install_gms.desc"))
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)

        btn_gms = QPushButton(t("install_gms.btn_action", "🌐 PREPARE GOOGLE PLAY SERVICES USB"))
        btn_gms.setProperty("class", "btnPrimary")
        btn_gms.setFixedHeight(44)
        btn_gms.clicked.connect(self._execute_install_gms)
        c_layout.addWidget(btn_gms)

        layout.addWidget(card)
        layout.addStretch()

    def _execute_install_gms(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_title = t("install_gms.confirm_title", "Confirm Google Services Installation")
        confirm_msg = t("install_gms.confirm_msg", letter=letter)
        if not show_confirm_dialog(self, confirm_title, confirm_msg, confirm_text="🌐 Prepare GMS USB"):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_install_gms_usb,
            letter,
            self.gms_dir,
            success_title=t("install_gms.success_title", "Google Services USB Ready"),
            success_msg=t("install_gms.success_msg", letter=letter),
            error_title="GMS Preparation Failed"
        )


class UninstallGmsView(QWidget):
    """View for preparing Google Play Services removal USB."""
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

        lbl_head = QLabel(t("uninstall_gms.view_title", "🧹 REMOVE GOOGLE PLAY SERVICES"))
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER}; border: none; background: transparent;")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(t("uninstall_gms.desc"))
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)

        btn_del = QPushButton(t("uninstall_gms.btn_action", "🧹 PREPARE GOOGLE SERVICES REMOVAL USB"))
        btn_del.setProperty("class", "btnDanger")
        btn_del.setFixedHeight(44)
        btn_del.clicked.connect(self._execute_uninstall_gms)
        c_layout.addWidget(btn_del)

        layout.addWidget(card)
        layout.addStretch()

    def _execute_uninstall_gms(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_title = t("uninstall_gms.confirm_title", "Confirm Google Services Removal")
        confirm_msg = t("uninstall_gms.confirm_msg", letter=letter)
        if not show_confirm_dialog(self, confirm_title, confirm_msg, confirm_text="🧹 Prepare Removal USB", is_danger=True):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_uninstall_gms_usb,
            letter,
            success_title=t("uninstall_gms.success_title", "GMS Removal USB Ready"),
            success_msg=t("uninstall_gms.success_msg", letter=letter),
            error_title="Removal Preparation Failed"
        )
