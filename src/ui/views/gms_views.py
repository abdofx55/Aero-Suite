"""
gms_views.py — Features 5 & 6: Google Play Services Setup and Removal Views.
Provides dedicated interfaces for calibrated GMS injection (Framework, Services, Login, Store)
and clean system-level GMS removal.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
import theme
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

        lbl_head = QLabel("🌐 GOOGLE PLAY SERVICES SETUP")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Bring the full Google experience right into your car! 🌐 Install official Google Play Services and Google Play Store tailored specifically for Dongfeng Shine:\n\n"
            "• 🛒 Official Google Play Store: Download, install, and update millions of apps directly on your screen!\n"
            "• 👤 Seamless Google Account: Sign in with your Google account to sync your profile and preferences.\n"
            "• 🗺️ Real Google Maps: Enjoy live traffic, saved locations, and voice search without limits!\n"
            "• ⚡ 100% App Compatibility: Run all your favorite streaming and navigation apps smoothly."
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)

        btn_gms = QPushButton("🌐 PREPARE GOOGLE PLAY SERVICES USB")
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
        confirm_msg = (
            f"Are you sure you want to prepare Google Play Services USB on drive {letter}?\n\n"
            f"This will package the integrated Google Play Services suite, native runtime libraries, and voice permissions for your vehicle."
        )
        if not show_confirm_dialog(self, "Confirm Google Services Installation", confirm_msg, confirm_text="🌐 Prepare GMS USB"):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_install_gms_usb,
            letter,
            self.gms_dir,
            success_title="Google Services USB Ready",
            success_msg=f"Successfully prepared Google Play Services USB on drive {letter}!\n\nSafely unplug and insert into vehicle.",
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

        lbl_head = QLabel("🧹 REMOVE GOOGLE PLAY SERVICES")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER}; border: none; background: transparent;")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Want a completely clean, lightweight screen? 🧹 Removes Google Play Services and cleans all related accounts with a single USB plugin:\n\n"
            "• ⚡ Maximum Speed: Frees up memory and system resources for ultra-fast screen performance.\n"
            "• 🔒 Safe & Clean: Leaves zero leftover accounts or background battery drain.\n"
            "• 🚗 Dealership Ready: Restores your car screen to its original stock state before routine service visits!"
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)

        btn_del = QPushButton("🧹 PREPARE GOOGLE SERVICES REMOVAL USB")
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
        confirm_msg = (
            f"Are you sure you want to prepare Google Services Removal USB on drive {letter}?\n\n"
            f"This will prepare a script to safely purge Google Play Services and clean associated account data from your car screen."
        )
        if not show_confirm_dialog(self, "Confirm Google Services Removal", confirm_msg, confirm_text="🧹 Prepare Removal USB", is_danger=True):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_uninstall_gms_usb,
            letter,
            success_title="GMS Removal USB Ready",
            success_msg=f"Successfully prepared GMS Removal USB on drive {letter}!",
            error_title="Removal Preparation Failed"
        )
