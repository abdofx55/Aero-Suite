"""
quick_setup_view.py — Master Technician Fast Provisioning View.
1-Click deployment of Aero Bar + Full Google Play Services (all optional apps),
optional factory reset, and post-reboot auto-launch.
Zero lock files written to vehicle internal storage.
Follows standard OpenSettingsView architecture for flawless BiDi / RTL text flow.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QFrame, QCheckBox
)
import theme
from core.i18n import t, is_rtl
from ui.components.dialogs import show_confirm_dialog


class QuickSetupView(QWidget):
    """View for configuring the Quick Setup Master USB payload."""

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

        self.lbl_head = QLabel(t("quick_setup.view_title", "⚡ فلاشة التجهيز السريع الشامل"))
        self.lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        c_layout.addWidget(self.lbl_head)

        self.lbl_desc = QLabel(t("quick_setup.desc"))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 2px 0 6px 0; line-height: 1.5;")
        self.lbl_desc.setWordWrap(True)
        c_layout.addWidget(self.lbl_desc)

        # Framed factory wipe container box
        self.wipe_box = QFrame()
        self.wipe_box.setObjectName("quickSetupWipeBox")
        self.wipe_box.setStyleSheet(f"""
            QFrame#quickSetupWipeBox {{
                background-color: {theme.SURFACE_2};
                border: 1px solid rgba(255, 179, 0, 0.25);
                border-radius: 8px;
            }}
        """)
        wb_layout = QVBoxLayout(self.wipe_box)
        wb_layout.setContentsMargins(16, 12, 16, 12)
        wb_layout.setSpacing(4)

        self.chk_wipe = QCheckBox(t("quick_setup.chk_wipe_title", "⚠️ إجراء ضبط مصنع كامل وتصفير البيانات (اختياري)"))
        self.chk_wipe.setChecked(False)
        self.chk_wipe.setCursor(Qt.PointingHandCursor)
        self.chk_wipe.setStyleSheet(f"color: {theme.AMBER_WARN}; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        wb_layout.addWidget(self.chk_wipe)

        hint_pad = "padding-right: 24px;" if is_rtl() else "padding-left: 24px;"
        self.lbl_wipe_hint = QLabel(t("quick_setup.chk_wipe_hint", "يوصى به للبدء على نظافة والتخلص من أي تطبيقات أو تعديلات سابقة."))
        self.lbl_wipe_hint.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px; border: none; background: transparent; {hint_pad}")
        self.lbl_wipe_hint.setWordWrap(True)
        wb_layout.addWidget(self.lbl_wipe_hint)

        c_layout.addWidget(self.wipe_box)

        # Comfortable spacing between factory wipe box and action button
        c_layout.addSpacing(16)

        # Standalone Master Deploy Button (Quick Setup acts as its own all-in-one suite)
        self.btn_deploy = QPushButton("   " + t("quick_setup.btn_action", "⚡ جهز فلاشة التجهيز السريع الآن"))
        self.btn_deploy.setProperty("class", "btnPrimary")
        self.btn_deploy.setFixedHeight(44)
        self.btn_deploy.setCursor(Qt.PointingHandCursor)
        self.btn_deploy.clicked.connect(self._execute_quick_setup)
        c_layout.addWidget(self.btn_deploy)

        layout.addWidget(card)
        layout.addStretch()

    def retranslate_ui(self):
        """Refreshes all localized texts."""
        self.lbl_head.setText(t("quick_setup.view_title", "⚡ فلاشة التجهيز السريع الشامل"))
        self.lbl_desc.setText(t("quick_setup.desc"))
        self.chk_wipe.setText(t("quick_setup.chk_wipe_title", "⚠️ إجراء ضبط مصنع كامل وتصفير البيانات (اختياري)"))
        hint_pad = "padding-right: 24px;" if is_rtl() else "padding-left: 24px;"
        self.lbl_wipe_hint.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px; border: none; background: transparent; {hint_pad}")
        self.lbl_wipe_hint.setText(t("quick_setup.chk_wipe_hint", "يوصى به للبدء على نظافة والتخلص من أي تطبيقات أو تعديلات سابقة."))
        self.btn_deploy.setText("   " + t("quick_setup.btn_action", "⚡ جهز فلاشة التجهيز السريع الآن"))

    def _execute_quick_setup(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        letter = self.main_app.current_usb.letter
        wipe_enabled = self.chk_wipe.isChecked()

        confirm_msg = t("quick_setup.confirm_msg", letter=letter)
        if wipe_enabled:
            confirm_msg += "\n\n" + t("quick_setup.confirm_wipe_warn", "⚠️ تنبيه: تم تفعيل خيار ضبط المصنع؛ سيتم تصفير بيانات /data بالكامل قبل التثبيت.")

        if not show_confirm_dialog(
            self,
            t("quick_setup.confirm_title", "تأكيد تجهيز فلاشة التجهيز السريع"),
            confirm_msg,
            confirm_text=t("quick_setup.btn_confirm", "⚡ جهز الفلاشة الآن"),
            is_danger=wipe_enabled
        ):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_quick_setup_usb,
            letter,
            wipe_factory_data=wipe_enabled,
            success_title=t("quick_setup.success_title", "فلاشة التجهيز السريع جاهزة"),
            success_msg=t("quick_setup.success_msg", letter=letter),
            error_title=t("common.preparation_failed", "فشل التجهيز")
        )
