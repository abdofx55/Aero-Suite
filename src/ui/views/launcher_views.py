"""
launcher_views.py — Features 7 & 8: Disable and Enable Factory Launcher Views.
Controls freezing and unfreezing of the Dongfeng Aeolus stock dashboard launcher.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
import theme
from core.i18n import t
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

        self.lbl_head = QLabel(t("disable_launcher.view_title"))
        self.lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER};")
        c_layout.addWidget(self.lbl_head)

        self.lbl_desc = QLabel(t("disable_launcher.desc"))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        self.lbl_desc.setWordWrap(True)
        c_layout.addWidget(self.lbl_desc)

        self.btn_dis = QPushButton(t("disable_launcher.btn_action"))
        self.btn_dis.setProperty("class", "btnDanger")
        self.btn_dis.setFixedHeight(44)
        self.btn_dis.clicked.connect(self._execute_disable_launcher)
        c_layout.addWidget(self.btn_dis)

        layout.addWidget(card)
        layout.addStretch()

    def retranslate_ui(self):
        """Re-translates elements in DisableLauncherView."""
        self.lbl_head.setText(t("disable_launcher.view_title"))
        self.lbl_desc.setText(t("disable_launcher.desc"))
        self.btn_dis.setText(t("disable_launcher.btn_action"))

    def _execute_disable_launcher(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = t("disable_launcher.confirm_msg", letter=letter)
        if not show_confirm_dialog(self, t("disable_launcher.confirm_title"), confirm_msg, confirm_text="🚫 Disable Launcher", is_danger=True):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_disable_launcher_usb,
            letter,
            success_title=t("disable_launcher.success_title"),
            success_msg=t("disable_launcher.success_msg", letter=letter),
            error_title=t("common.preparation_failed")
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

        self.lbl_head = QLabel(t("enable_launcher.view_title"))
        self.lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        c_layout.addWidget(self.lbl_head)

        self.lbl_desc = QLabel(t("enable_launcher.desc"))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        self.lbl_desc.setWordWrap(True)
        c_layout.addWidget(self.lbl_desc)

        self.btn_en = QPushButton(t("enable_launcher.btn_action"))
        self.btn_en.setProperty("class", "btnPrimary")
        self.btn_en.setFixedHeight(44)
        self.btn_en.clicked.connect(self._execute_enable_launcher)
        c_layout.addWidget(self.btn_en)

        layout.addWidget(card)
        layout.addStretch()

    def retranslate_ui(self):
        """Re-translates elements in EnableLauncherView."""
        self.lbl_head.setText(t("enable_launcher.view_title"))
        self.lbl_desc.setText(t("enable_launcher.desc"))
        self.btn_en.setText(t("enable_launcher.btn_action"))

    def _execute_enable_launcher(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        confirm_msg = t("enable_launcher.confirm_msg", letter=letter)
        if not show_confirm_dialog(self, t("enable_launcher.confirm_title"), confirm_msg, confirm_text="✅ Enable Launcher"):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_enable_launcher_usb,
            letter,
            success_title=t("enable_launcher.success_title"),
            success_msg=t("enable_launcher.success_msg", letter=letter),
            error_title=t("common.preparation_failed")
        )
