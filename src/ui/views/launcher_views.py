"""
launcher_views.py — Features 7 & 8: Disable and Enable Factory Launcher Views.
Controls freezing and unfreezing of the Dongfeng Aeolus stock dashboard launcher.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
import theme
from ui.components.dialogs import show_confirm_dialog


class DisableLauncherView(QWidget):
    """View for preparing Disable Factory Launcher USB payload."""
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

        lbl_head = QLabel("🚫 DISABLE FACTORY LAUNCHER")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Give your car a stunning, customized look! 🚫 Disables the rigid factory home screen so your favorite custom car launcher (like AGAMA or Nova) boots up instantly as your main dashboard:\n\n"
            "• 🏎️ True Car Dashboard Feel: Modern gauges, speedometers, and customized music widgets.\n"
            "• ⚡ Zero Screen Lag: Prevents the factory launcher from fighting for memory in the background.\n"
            "• 🔄 100% Reversible: You can restore the original factory launcher anytime with one click!\n\n"
            "⚠️ Note: Make sure you installed a custom launcher (e.g., AGAMA) before disabling the factory one!"
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)

        btn_dis = QPushButton("🚫 PREPARE DISABLE FACTORY LAUNCHER USB")
        btn_dis.setProperty("class", "btnDanger")
        btn_dis.setFixedHeight(44)
        btn_dis.clicked.connect(self._execute_disable_launcher)
        c_layout.addWidget(btn_dis)

        layout.addWidget(card)
        layout.addStretch()

    def _execute_disable_launcher(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = (
            f"Are you sure you want to disable the Factory Launcher on drive {letter}?\n\n"
            f"Ensure you have an alternative launcher installed on the car screen."
        )
        if not show_confirm_dialog(self, "Confirm Disable Factory Launcher", confirm_msg, confirm_text="🚫 Disable Launcher", is_danger=True):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_disable_launcher_usb,
            letter,
            success_title="Disable Launcher USB Ready",
            success_msg=f"Successfully prepared payload on drive {letter}!",
            error_title="Preparation Failed"
        )


class EnableLauncherView(QWidget):
    """View for preparing Enable Factory Launcher USB payload."""
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

        lbl_head = QLabel("✅ ENABLE FACTORY LAUNCHER")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Miss the original factory look? ✅ Restores the original Dongfeng factory home screen launcher in seconds! Simply insert the USB, and your stock dashboard interface is back up and running just like the day you bought the car."
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)

        btn_en = QPushButton("✅ PREPARE ENABLE FACTORY LAUNCHER USB")
        btn_en.setProperty("class", "btnPrimary")
        btn_en.setFixedHeight(44)
        btn_en.clicked.connect(self._execute_enable_launcher)
        c_layout.addWidget(btn_en)

        layout.addWidget(card)
        layout.addStretch()

    def _execute_enable_launcher(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = f"Are you sure you want to restore the Factory Launcher on drive {letter}?"
        if not show_confirm_dialog(self, "Confirm Enable Factory Launcher", confirm_msg, confirm_text="✅ Enable Launcher"):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_enable_launcher_usb,
            letter,
            success_title="Enable Launcher USB Ready",
            success_msg=f"Successfully prepared payload on drive {letter}!",
            error_title="Preparation Failed"
        )
