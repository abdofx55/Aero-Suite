"""
main_window.py — Aero Suite Automotive Infotainment Management Console (PySide6 Edition).
Dongfeng Shine (Aeolus D53) IVI System.
Clean Modular Architecture adhering to SOLID principles.
"""
import os
import sys
import threading
import time
import re

from PySide6.QtCore import Qt, QThread, Signal, Slot, QObject, QTimer, QPoint
from PySide6.QtGui import QIcon, QFont, QCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QLabel, QPushButton, QFrame, QMessageBox, QSplitter, QMenu
)

import theme
from qt_theme import get_application_stylesheet
from apk_engine import scan_local_apks
from usb_detector import get_removable_drives, UsbWatcher, UsbDriveInfo
from sync_manager import sync_backup_from_usb_to_pc, get_local_backups
import payload_engine

from core.constants import (
    FACTORY_PRIV_APPS, FACTORY_APPS, FACTORY_LAUNCHER_PKG,
    SIGNATURE_BANNER, DEVELOPER_NAME, DEVELOPER_EMAIL, DEVELOPER_PHONE
)
from core.i18n import t, get_i18n, is_onboarding_completed, SUPPORTED_LANGUAGES
from core.store import get_store
from core.state import AppState
from core.exceptions import setup_global_exception_handler, log_exception, log_to_file
from ui.components.dialogs import show_confirm_dialog, show_success_dialog, show_error_dialog
from ui.components.progress_bar import ProgressControl
from ui.components.terminal import TerminalWidget
from ui.components.top_bar import TopBarWidget
from ui.components.side_nav import SideNavWidget, FEATURE_CATEGORIES
from ui.components.app_card import AppCard
from ui.components.basket_dialog import BasketDialog
from services.basket_service import get_basket_service, BasketItem

from ui.views.onboarding_view import OnboardingView
from ui.views.install_apps_view import InstallAppsView
from ui.views.uninstall_apps_view import UninstallAppsView
from ui.views.open_app_view import OpenAppView
from ui.views.open_settings_view import OpenSettingsView
from ui.views.gms_views import InstallGmsView, UninstallGmsView
from ui.views.launcher_views import DisableLauncherView, EnableLauncherView
from ui.views.reboot_view import RebootScreenView
from ui.views.backup_view import BackupView
from ui.views.restore_view import RestoreView
from ui.views.factory_reset_view import FactoryResetView
from ui.views.fetch_logs_view import FetchLogsView
from ui.views.vehicle_tweaks_view import VehicleTweaksView
from ui.views.roadmap_view import RoadmapView
from ui.views.support_view import SupportView
from ui.views.about_view import AboutView
from ui.views.registry import get_view_registry
from core.paths import BASE_DIR, APKS_DIR, GMS_DIR, BACKUPS_DIR, FACTORY_BACKUP_DIR, LOGS_DIR, get_base_dir

for d in [APKS_DIR, BACKUPS_DIR, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)


from controllers import UsbSignalBridge, PayloadWorker, PayloadController, UsbController, format_progress_status


class AeroSuiteQtApp(QMainWindow):
    """Main Application Window for Aero Suite."""
    def __init__(self):
        super().__init__()
        setup_global_exception_handler()

        app_inst = QApplication.instance()
        if app_inst:
            app_inst.setEffectEnabled(Qt.UIEffect.UI_AnimateCombo, False)

        self.setWindowTitle(f"Aero Suite v{theme.APP_VERSION} — Automotive APK & System Studio")
        self.resize(1180, 800)
        self.setMinimumSize(1000, 680)
        self.setWindowState(Qt.WindowState.WindowMaximized)

        # Global MVI State & Controllers
        self.store = get_store()
        self.payload_ctrl = PayloadController(self)
        self.usb_ctrl = UsbController(self)

        self.all_drives = []
        self.current_usb = None
        self.is_busy = False
        self._pending_usb_drives = None
        self.current_worker = None
        self.cancel_event = threading.Event()
        self.feature_categories = FEATURE_CATEGORIES
        self.basket = get_basket_service()

        # Local APKs & Selections
        self.local_apks = scan_local_apks(APKS_DIR)
        self.allowed_packages = [a["package"] for a in self.local_apks if a.get("package")]
        self.selected_install_apks = {a["filename"]: False for a in self.local_apks}
        self.per_app_portrait = {a["filename"]: False for a in self.local_apks}
        self.per_app_target = {a["filename"]: "user" for a in self.local_apks}
        self.per_app_boot = {a["filename"]: False for a in self.local_apks}
        self.auto_launch_app_filename = None

        self.selected_uninstall_pkgs = {a["package"]: False for a in self.local_apks if a.get("package")}
        self.selected_open_app_filename = ""

        # Setup UI
        is_rtl = get_i18n().is_rtl()
        self.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        self.setStyleSheet(get_application_stylesheet(is_rtl=is_rtl))
        self._build_main_ui()
        self._update_dev_bar_layout()
        self.retranslate_ui()

        # USB Bridge & Monitoring via UsbController
        self.usb_bridge = self.usb_ctrl.bridge
        self.usb_watcher = self.usb_ctrl.watcher
        self.usb_ctrl.drives_updated.connect(self._on_usb_drives_changed)
        self.usb_ctrl.start_watcher()

        # Initial Rescan
        QTimer.singleShot(100, self._initial_startup_log)

    def _initial_startup_log(self):
        self.log_terminal(t("logs.app_initialized", f"Aero Suite v{theme.APP_VERSION} initialized successfully.", version=theme.APP_VERSION), "cyan")
        self.log_terminal(t("logs.repo_indexed", f"Vetted APK Repository: {len(self.local_apks)} application(s) indexed.", count=len(self.local_apks)), "mint")
        drives = get_removable_drives()
        self._on_usb_drives_changed(drives)

    def _build_main_ui(self):
        self.root_stack = QStackedWidget()
        self.setCentralWidget(self.root_stack)

        # Page 0: Main Studio Widget
        main_studio_widget = QWidget()
        main_layout = QVBoxLayout(main_studio_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Top Bar Widget
        self.top_bar = TopBarWidget(self)
        self.usb_combo = self.top_bar.usb_combo
        self.usb_status_dot = self.top_bar.usb_status_dot
        self.btn_refresh_usb = self.top_bar.btn_refresh_usb
        self.btn_usb_settings = self.top_bar.btn_usb_settings

        self.top_bar.usb_selected.connect(self._on_usb_selected)
        self.top_bar.refresh_requested.connect(self._refresh_usb_drives)
        self.top_bar.menu_requested.connect(self._show_usb_menu)
        self.top_bar.language_selected.connect(self._on_language_changed)
        self.top_bar.basket_clicked.connect(self._open_basket_dialog)
        self.basket.basket_changed.connect(self.top_bar.update_basket_count)
        main_layout.addWidget(self.top_bar)

        # 2. Developer Bio Bar
        self.dev_bar = QWidget()
        self.dev_bar.setFixedHeight(30)
        self.dev_bar.setStyleSheet(f"background-color: {theme.SURFACE_2}; border-bottom: 1px solid {theme.BORDER_SLATE};")
        self.dev_layout = QHBoxLayout(self.dev_bar)
        self.dev_layout.setContentsMargins(20, 2, 20, 2)

        self.lbl_dev = QLabel(f"👨‍💻 {DEVELOPER_NAME}   |   ✉️ {DEVELOPER_EMAIL}   |   📞 {DEVELOPER_PHONE}")
        self.lbl_dev.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED};")
        self.lbl_gift = QLabel(t("app.community_gift", "🎁 A Special Gift for Dongfeng Owners in Egypt ❤️"))
        self.lbl_gift.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {theme.MINT_SUCCESS};")

        self._update_dev_bar_layout()
        main_layout.addWidget(self.dev_bar)

        # 3. Workspace Layout: Sidebar + Splitter (Content Views + Terminal)
        workspace = QWidget()
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        # Side Navigation Widget
        self.side_nav = SideNavWidget(self)
        self.side_nav.feature_selected.connect(self.switch_view)
        workspace_layout.addWidget(self.side_nav)

        # Right Area Splitter
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.setHandleWidth(1)

        # Content Card Frame
        content_frame = QFrame()
        content_frame.setObjectName("contentPanel")
        content_frame.setStyleSheet("QFrame#contentPanel { background-color: transparent; border: none; }")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.page_stack = QStackedWidget()

        # Instantiate View Modules declaratively via ViewRegistry
        self.view_registry = get_view_registry()
        self.views_map = {}
        for desc in self.view_registry.get_all_views():
            view_inst = desc.create_view(self)
            self.views_map[desc.id] = view_inst
            setattr(self, f"view_{desc.id}", view_inst)
            self.page_stack.addWidget(view_inst)

        # Wire up backward-compatible view aliases
        if hasattr(self, "view_apps_hub"):
            self.view_install_apps = self.view_apps_hub.install_view
            self.view_uninstall_apps = self.view_apps_hub.uninstall_view
            self.view_open_app = self.view_apps_hub.open_view
            self.views_map["install_apps"] = self.view_apps_hub
            self.views_map["uninstall_apps"] = self.view_apps_hub
            self.views_map["open_app"] = self.view_apps_hub

        if hasattr(self, "view_gms_hub"):
            self.view_install_gms = self.view_gms_hub.install_view
            self.view_uninstall_gms = self.view_gms_hub.uninstall_view
            self.views_map["install_gms"] = self.view_gms_hub
            self.views_map["uninstall_gms"] = self.view_gms_hub

        if hasattr(self, "view_launcher_control"):
            self.view_disable_launcher = self.view_launcher_control
            self.view_enable_launcher = self.view_launcher_control
            self.views_map["disable_launcher"] = self.view_launcher_control
            self.views_map["enable_launcher"] = self.view_launcher_control

        # Expose sub-controls for backward compatibility with tests/properties
        self.btn_prepare_install = self.view_install_apps.btn_prepare_install
        self.btn_prepare_uninstall = self.view_uninstall_apps.btn_prepare_uninstall
        self.btn_prepare_open_app = self.view_open_app.btn_launch
        self.btn_open_app_launch = self.view_open_app.btn_launch
        self.install_count_label = self.view_install_apps.install_count_label
        self.install_search_edit = self.view_install_apps.search_edit
        self.uninstall_search_edit = self.view_uninstall_apps.search_edit
        self.open_app_search_edit = self.view_open_app.search_edit
        self.restore_combo = self.view_restore.restore_combo
        self.btn_restore = self.view_restore.btn_restore
        self.btn_backup = self.view_backup.btn_backup
        self.btn_prep_backup = self.view_backup.btn_backup
        self.views = self.views_map

        content_layout.addWidget(self.page_stack)
        right_splitter.addWidget(content_frame)

        # Bottom Area: Terminal Widget (with integrated ProgressControl in header)
        self.bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(self.bottom_widget)
        bottom_layout.setContentsMargins(16, 6, 16, 10)
        bottom_layout.setSpacing(0)

        self.terminal = TerminalWidget(self)
        self.txt_terminal = self.terminal.txt_terminal
        self.terminal_edit = self.terminal.terminal_edit
        self._clear_terminal_log = self.terminal.clear_logs

        self.progress_control = self.terminal.progress_control
        self.progress_control.cancel_clicked.connect(self.cancel_current_operation)
        self.prog_bar = self.progress_control.bar
        self.lbl_prog_status = self.progress_control.lbl_status
        self.btn_cancel = self.progress_control.btn_cancel

        bottom_layout.addWidget(self.terminal)

        right_splitter.addWidget(self.bottom_widget)
        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 1)

        workspace_layout.addWidget(right_splitter)
        main_layout.addWidget(workspace)

        # Select first feature by default
        self.side_nav.select_feature("quick_setup")

        self.root_stack.addWidget(main_studio_widget)

        # Page 1: Immersive Fullscreen Onboarding View
        self.onboarding_view = OnboardingView(self)
        self.onboarding_view.completed.connect(self._on_onboarding_finished)
        self.root_stack.addWidget(self.onboarding_view)

        # Initial view selection: Onboarding on first run, otherwise Main Studio
        if is_onboarding_completed():
            self.root_stack.setCurrentWidget(main_studio_widget)
        else:
            self.root_stack.setCurrentWidget(self.onboarding_view)

    def _on_onboarding_finished(self, lang_code: str):
        """Called when first-run onboarding is completed by the user."""
        self._on_language_changed(lang_code)
        idx = list(SUPPORTED_LANGUAGES.keys()).index(lang_code) if lang_code in SUPPORTED_LANGUAGES else 0
        self.top_bar.lang_combo.blockSignals(True)
        self.top_bar.lang_combo.setCurrentIndex(idx)
        self.top_bar.lang_combo.blockSignals(False)
        self.root_stack.setCurrentIndex(0)

    # ---------------------------------------------------------
    # Backward Compatibility Proxies for Tests / Facade
    # ---------------------------------------------------------
    @property
    def install_cards_map(self):
        return self.view_install_apps.cards_map

    @property
    def uninstall_cards_map(self):
        return self.view_uninstall_apps.cards_map

    @property
    def open_app_row_items(self):
        return self.view_open_app.row_items

    @property
    def install_search_query(self):
        return self.view_install_apps.search_query

    @install_search_query.setter
    def install_search_query(self, val):
        self.view_install_apps.search_query = val

    @property
    def uninstall_search_query(self):
        return self.view_uninstall_apps.search_query

    @uninstall_search_query.setter
    def uninstall_search_query(self, val):
        self.view_uninstall_apps.search_query = val

    @property
    def open_app_search_query(self):
        return self.view_open_app.search_query

    @open_app_search_query.setter
    def open_app_search_query(self, val):
        self.view_open_app.search_query = val

    def _render_install_cards(self):
        self.view_install_apps.render_cards()

    def _render_uninstall_cards(self):
        self.view_uninstall_apps.render_cards()

    def _render_open_app_rows(self):
        self.view_open_app.render_rows()

    def _build_unified_app_row(self, mode: str, a: dict) -> AppCard:
        card = AppCard(mode, a)
        if mode == "install":
            self.view_install_apps.cards_map[a["filename"]] = {
                "card": card,
                "chk_install": card.chk_main,
                "chk_auto": card.chk_auto,
                "chk_port": card.chk_port,
                "chk_boot": card.chk_boot,
                "combo_target": card.combo_target,
                "lbl_size": card.lbl_size
            }
        elif mode == "uninstall":
            self.view_uninstall_apps.cards_map[a["package"]] = {
                "card": card,
                "chk": card.chk_main,
                "lbl_size": card.lbl_size
            }
        elif mode == "open":
            self.view_open_app.row_items[a["filename"]] = {
                "row": card,
                "chk": card.chk_main,
                "lbl_size": card.lbl_size
            }
        return card

    def _set_card_selected_visual(self, card: QFrame, is_selected: bool):
        if hasattr(card, "set_selected_visual"):
            card.set_selected_visual(is_selected)

    def _set_all_install_apks(self, state: bool):
        self.view_install_apps.set_all_selected(state)

    def _invert_install_selection(self):
        self.view_install_apps.invert_selection()

    def _set_all_uninstall_pkgs(self, state: bool):
        self.view_uninstall_apps.set_all_selected(state)

    def _invert_uninstall_selection(self):
        self.view_uninstall_apps.invert_selection()

    def _update_install_button(self):
        self.view_install_apps.update_action_button()

    def _update_uninstall_button(self):
        self.view_uninstall_apps.update_action_button()

    def _update_open_app_launch_button(self):
        self.view_open_app.update_action_button()

    def _on_auto_launch_toggle(self, fname: str, is_checked: bool):
        self.view_install_apps._on_auto_launch_toggled(fname, is_checked)

    _on_auto_launch_changed = _on_auto_launch_toggle

    def _rescan_apks(self):
        self.local_apks = scan_local_apks(APKS_DIR)
        for a in self.local_apks:
            fn = a["filename"]
            if fn not in self.selected_install_apks:
                self.selected_install_apks[fn] = False
                self.per_app_portrait[fn] = False
                self.per_app_target[fn] = "user"
                self.per_app_boot[fn] = False
        self.allowed_packages = [a["package"] for a in self.local_apks if a.get("package")]
        self.view_install_apps.install_count_label.setText(f"({len(self.local_apks)} APKs available in repository)")
        self.view_install_apps.render_cards()
        self.view_install_apps.update_action_button()
        self.view_uninstall_apps.render_cards()
        self.view_uninstall_apps.update_action_button()
        self.view_open_app.render_rows()
        self.log_terminal(t("logs.rescanned_repo", f"Rescanned apks/ repository. Total: {len(self.local_apks)} packages.", count=len(self.local_apks)), "mint")

    @property
    def active_feature(self) -> str:
        if hasattr(self, "_active_feature_override") and self._active_feature_override:
            return self._active_feature_override
        return self.side_nav.current_feature if hasattr(self, "side_nav") else "quick_setup"

    def switch_view(self, feat_id: str):
        self._active_feature_override = feat_id

        # Route legacy child views to corresponding hub tab
        target_nav_id = feat_id
        if feat_id in ("install_apps", "uninstall_apps", "open_app") and hasattr(self, "view_apps_hub"):
            target_nav_id = "apps_hub"
            if feat_id == "install_apps":
                self.view_apps_hub.set_active_tab(0)
            elif feat_id == "uninstall_apps":
                self.view_apps_hub.set_active_tab(1)
            elif feat_id == "open_app":
                self.view_apps_hub.set_active_tab(2)
        elif feat_id in ("install_gms", "uninstall_gms") and hasattr(self, "view_gms_hub"):
            target_nav_id = "gms_hub"
            if feat_id == "install_gms":
                self.view_gms_hub.set_active_tab(0)
            elif feat_id == "uninstall_gms":
                self.view_gms_hub.set_active_tab(1)
        elif feat_id in ("disable_launcher", "enable_launcher") and hasattr(self, "view_launcher_control"):
            target_nav_id = "launcher_control"

        if feat_id in self.views_map:
            self.page_stack.setCurrentWidget(self.views_map[feat_id])
            if hasattr(self, "side_nav") and self.side_nav.current_feature != target_nav_id:
                self.side_nav.select_feature(target_nav_id)

            # Hide bottom terminal panel on standalone canvas views declaratively
            desc = self.view_registry.get_view(target_nav_id) if hasattr(self, "view_registry") else None
            hide_term = desc.hide_terminal if desc else target_nav_id in ("support", "roadmap", "about")
            if hasattr(self, "bottom_widget"):
                self.bottom_widget.setVisible(not hide_term)

            if feat_id == "restore":
                self.view_restore.populate_restore_combo()
            elif feat_id == "backup":
                self.view_backup.update_sync_button_state()
            elif feat_id == "roadmap":
                self.view_roadmap.scroll_to_top()

    def _on_open_app_selected(self, filename: str, checked: bool = True):
        if checked:
            self.selected_open_app_filename = filename
        elif self.selected_open_app_filename == filename:
            self.selected_open_app_filename = ""
        self.view_open_app.sync_rows()

    def _on_language_changed(self, lang_code: str):
        from core.i18n import get_i18n
        get_i18n().set_language(lang_code)
        is_rtl = get_i18n().is_rtl()
        self.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        self.setStyleSheet(get_application_stylesheet(is_rtl=is_rtl))
        self._update_dev_bar_layout()
        self.log_terminal(t("logs.lang_changed", f"Language changed to: {lang_code.upper()} ({get_i18n().current_lang})", lang_code=lang_code.upper(), lang_name=get_i18n().current_lang), "mint")
        self.retranslate_ui()

    def _update_dev_bar_layout(self):
        """Ensures the gift banner is placed on the primary reading side (Right in RTL, Left in LTR)."""
        while self.dev_layout.count():
            self.dev_layout.takeAt(0)
        from core.i18n import get_i18n
        if get_i18n().is_rtl():
            self.dev_layout.addWidget(self.lbl_gift)
            self.dev_layout.addStretch()
            self.dev_layout.addWidget(self.lbl_dev)
        else:
            self.dev_layout.addWidget(self.lbl_dev)
            self.dev_layout.addStretch()
            self.dev_layout.addWidget(self.lbl_gift)

    def retranslate_ui(self):
        """Dispatches dynamic retranslation across all top bar, sidebar, and view components."""
        self.top_bar.retranslate_ui()
        self.side_nav.retranslate_ui()
        self.lbl_gift.setText(t("app.community_gift", "🎁 A Special Gift for Dongfeng Owners in Egypt ❤️"))
        self.progress_control.retranslate_ui()
        self.terminal.retranslate_ui()

        # Retranslate all views declaratively
        for view_widget in self.views_map.values():
            if hasattr(view_widget, "retranslate_ui"):
                view_widget.retranslate_ui()

        # Retranslate USB dropdown and status indicators in active language
        if hasattr(self, "_on_usb_drives_changed"):
            self._on_usb_drives_changed(getattr(self, "all_drives", []))

    def log_terminal(self, msg: str, level: str = "cyan"):
        self.terminal.append_log(msg, level)

    # ---------------------------------------------------------
    # USB Watcher & Selection (Bug 2 Protection)
    # ---------------------------------------------------------
    @Slot(list)
    def _on_usb_drives_changed(self, drives: list):
        # BUG 2 GUARD: While payload is executing, never reset combo box or mutate active drive!
        if self.is_busy:
            self._pending_usb_drives = drives
            return

        self.all_drives = drives
        self.usb_combo.blockSignals(True)
        self.usb_combo.clear()

        if not drives:
            self.current_usb = None
            self.usb_combo.addItem(t("common.no_usb_detected", "NO USB FLASH DETECTED"))
            self.usb_combo.setToolTip(t("app.insert_usb_tooltip", "Please insert a removable USB flash drive to prepare payloads."))
            self.usb_status_dot.setStyleSheet(f"color: {theme.CRIMSON_DANGER}; font-size: 16px;")
            self.usb_status_dot.setToolTip(t("app.no_usb_tooltip", "No USB Flash Drive Detected"))
        else:
            prev_letter = self.current_usb.letter if self.current_usb else None
            matched_idx = 0
            for i, d in enumerate(drives):
                item_text = f"{d.drive_letter_only}:\\ [{d.label or 'USB'}] ({d.free_gb:.1f} GB free)"
                if getattr(d, "is_restore_ready", False):
                    item_text += " 🔄 RESTORE"
                elif getattr(d, "has_backup", False):
                    item_text += " ★ BACKUP"
                self.usb_combo.addItem(item_text, userData=d)
                if prev_letter and d.letter == prev_letter:
                    matched_idx = i

            self.usb_combo.setCurrentIndex(matched_idx)
            self.current_usb = drives[matched_idx]
            self._update_usb_status_ui()

            if len(drives) > 1 and getattr(self, "_last_warned_drive_count", 0) != len(drives):
                self._last_warned_drive_count = len(drives)
                self.log_terminal(t("common.multiple_drives_warn", f"⚠️ Multiple removable drives detected ({len(drives)} drives)! Please verify the target USB drive selected in the dropdown.", count=len(drives)), "warn")
            elif len(drives) == 1:
                self._last_warned_drive_count = 1

            if self.current_usb and getattr(self.current_usb, "has_backup", False):
                if getattr(self, "_last_logged_backup_drive", None) != self.current_usb.letter:
                    self._last_logged_backup_drive = self.current_usb.letter
                    self.log_terminal(t("logs.backup_detected", f"Car backup detected on {self.current_usb.letter} (Date: {self.current_usb.backup_date}). Ready for PC Vault Sync.", letter=self.current_usb.letter, date=self.current_usb.backup_date), "mint")
            else:
                self._last_logged_backup_drive = None

        self.usb_combo.blockSignals(False)
        self.view_backup.update_sync_button_state()

    def _on_usb_selected(self, index: int):
        if 0 <= index < len(self.all_drives):
            self.current_usb = self.all_drives[index]
            self._update_usb_status_ui()
            self.view_backup.update_sync_button_state()

    def _update_usb_status_ui(self):
        if not self.current_usb:
            self.usb_status_dot.setStyleSheet(f"color: {theme.CRIMSON_DANGER}; font-size: 16px;")
            self.usb_status_dot.setToolTip(t("app.no_usb_tooltip", "No USB Flash Drive Detected"))
            return

        is_supported = (self.current_usb.fs_type or "").upper() == "FAT32"
        if is_supported:
            self.usb_status_dot.setStyleSheet(f"color: {theme.MINT_SUCCESS}; font-size: 16px;")
            self.usb_status_dot.setToolTip(f"Ready: {self.current_usb.letter} (FAT32)")
        else:
            self.usb_status_dot.setStyleSheet(f"color: {theme.AMBER_WARN}; font-size: 16px;")
            self.usb_status_dot.setToolTip(f"Warning: {self.current_usb.fs_type} detected. Dongfeng Shine strictly requires FAT32!")

    def _refresh_usb_drives(self):
        drives = get_removable_drives()
        self._on_usb_drives_changed(drives)
        if hasattr(self, "btn_refresh_usb"):
            self.btn_refresh_usb.setText(t("common.refreshed", "✓ Refreshed!"))
            self.btn_refresh_usb.setStyleSheet(f"color: {theme.MINT_SUCCESS};")
            QTimer.singleShot(1200, lambda: (
                self.btn_refresh_usb.setText(t("common.refresh", "🔄 Refresh")),
                self.btn_refresh_usb.setStyleSheet("")
            ))

    def _show_usb_menu(self, button_anchor=False):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {theme.SURFACE_2};
                border: 1px solid {theme.BORDER_SLATE};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 14px;
                color: {theme.TEXT_PRIMARY};
                font-size: 11px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {theme.CYAN_ALPHA_15};
                color: {theme.CYAN_PRIMARY};
            }}
        """)
        a_open = menu.addAction(t("common.open_explorer", "📂 Open in Windows Explorer"))
        a_open.triggered.connect(self._open_usb_in_explorer)

        a_fmt = menu.addAction(t("common.format_fat32", "⚡ Format Drive (FAT32)"))
        a_fmt.triggered.connect(self._format_usb_fat32)

        menu.addSeparator()
        a_rescan = menu.addAction(t("common.rescan_drives", "🔄 Rescan Removable Drives"))
        a_rescan.triggered.connect(self._refresh_usb_drives)

        if button_anchor:
            pos = self.btn_usb_settings.mapToGlobal(QPoint(0, self.btn_usb_settings.height() + 2))
        else:
            pos = QCursor.pos()
        menu.exec(pos)

    def _show_about_dialog(self):
        from ui.components.dialogs import show_about_dialog
        show_about_dialog(self)

    def _open_usb_in_explorer(self):
        if not self.current_usb or not os.path.exists(self.current_usb.letter):
            self.show_error_dialog(t("common.no_drive_selected", "No Drive Selected"), t("common.no_drive_selected_msg", "Please select a valid USB flash drive first."))
            return
        os.system(f'explorer "{self.current_usb.letter}"')

    def _format_usb_fat32(self):
        """Formats target USB drive strictly as FAT32, bypassing Windows 32GB artificial caps."""
        if self._check_busy_and_warn():
            return
        if not self.current_usb or not os.path.exists(self.current_usb.letter):
            self.show_error_dialog(t("common.no_drive_selected", "No USB Selected"), t("common.no_drive_selected_msg", "Please select a valid USB flash drive first."))
            return

        letter = self.current_usb.letter
        size_gb = getattr(self.current_usb, "size_gb", 0) or 0

        confirm_title = t("format_usb.confirm_title", "Confirm USB Format (FAT32)")
        confirm_msg = t(
            "format_usb.confirm_msg",
            f"WARNING: Formatting will permanently erase all data on flash drive {letter}!\n\n• Drive: {letter} ({self.current_usb.label or 'USB'})\n• Capacity: {size_gb} GB\n• FileSystem: FAT32 (Strictly required for vehicle screen)\n\nAre you sure you want to format this drive now to FAT32?",
            letter=letter,
            label=self.current_usb.label or "USB",
            size_gb=size_gb
        )

        btn_confirm_txt = t("format_usb.btn_confirm", "⚠️ FORMAT TO FAT32")
        if not show_confirm_dialog(self, confirm_title, confirm_msg, confirm_text=btn_confirm_txt, is_danger=True):
            return

        self.execute_payload_worker(
            payload_engine.format_usb_drive,
            letter,
            fs="FAT32",
            label="AERO_USB",
            success_title=t("format_usb.success_title", "Format Completed"),
            success_msg=t("format_usb.success_msg", f"Drive {letter} successfully formatted to FAT32 [AERO_USB]!", letter=letter),
            error_title=t("format_usb.error_title", "Format Failed"),
            has_guard=False
        )

    def _format_usb(self, forced_fs: str = None):
        """Alias for _format_usb_fat32 to guarantee FAT32 format."""
        self._format_usb_fat32()

    def _check_busy_and_warn(self) -> bool:
        if self.is_busy:
            self.show_error_dialog(t("common.op_in_progress", "Operation in Progress"), t("common.op_in_progress_msg", "An operation is currently running. Please wait or cancel it first."))
            return True
        return False

    def _check_usb_ready(self) -> bool:
        if not self.current_usb:
            self.show_error_dialog(t("common.no_drive_selected", "No USB Flash Drive"), t("common.no_drive_selected_msg", "Please insert a removable USB flash drive first."))
            return False
        return True

    def _validate_usb_filesystem(self) -> bool:
        if not self._check_usb_ready():
            return False
        # Re-query the live filesystem information from the OS before every operation
        if hasattr(self.current_usb, "_refresh"):
            self.current_usb._refresh()
            self._update_usb_status_ui()
            idx = self.usb_combo.currentIndex()
            if 0 <= idx < len(self.all_drives):
                label_txt = f"{self.current_usb.letter} [{self.current_usb.label}] ({self.current_usb.size_gb} GB, {self.current_usb.fs_type})"
                self.usb_combo.setItemText(idx, label_txt)

        # Dongfeng Shine automotive screen strictly requires FAT32
        current_fs = (self.current_usb.fs_type or "").upper()
        if current_fs != "FAT32":
            size_gb = getattr(self.current_usb, "size_gb", 0) or 0
            incompat_title = t("format_usb.incompatible_title", "Incompatible File System")
            incompat_msg = t(
                "format_usb.incompatible_msg",
                f"Flash drive ({self.current_usb.letter}) is formatted as ({self.current_usb.fs_type}).\n\nDongfeng Shine screen strictly requires FAT32 to automatically recognize USB payloads.\n\nWould you like to format this drive now to FAT32 (works for all sizes, including {size_gb} GB)?",
                letter=self.current_usb.letter,
                fs_type=self.current_usb.fs_type,
                size_gb=size_gb
            )
            btn_txt = t("format_usb.btn_format_now", "⚡ Format to FAT32")
            if show_confirm_dialog(self, incompat_title, incompat_msg, confirm_text=btn_txt, is_danger=True):
                self._format_usb_fat32()
            return False
        return True

    # ---------------------------------------------------------
    # Worker Execution & Progress Management
    # ---------------------------------------------------------
    def execute_payload_worker(self, target_func, *args, success_title="", success_msg="", error_title="", has_guard=None, **kwargs):
        self.is_busy = True
        self.cancel_event.clear()
        self.progress_control.reset()
        self.progress_control.show_control()

        self._current_success_title = success_title
        self._current_success_msg = success_msg
        self._current_error_title = error_title

        # Determine if payload writes a vehicle execution guard (completed_cars serial registry)
        if has_guard is None:
            func_name = getattr(target_func, "__name__", "")
            self._current_has_guard = (func_name not in ("format_usb_drive", "sync_backup_from_usb_to_pc"))
        else:
            self._current_has_guard = bool(has_guard)

        self.current_worker = PayloadWorker(target_func, *args, cancel_event=self.cancel_event, **kwargs)
        self.current_worker.progress_signal.connect(self._on_worker_progress)
        self.current_worker.log_signal.connect(self._on_worker_log)
        self.current_worker.finished_signal.connect(self._on_worker_finished)
        self.current_worker.start()

    @Slot(int, str)
    def _on_worker_progress(self, val: int, text: str):
        self.progress_control.set_progress(val, text)

    @Slot(str, str)
    def _on_worker_log(self, msg: str, level: str):
        self.log_terminal(msg, level)

    @Slot(bool, str)
    def _on_worker_finished(self, success: bool, err_msg: str):
        self.is_busy = False
        self.progress_control.finish(success)

        # Apply pending USB drive changes if any arrived during payload execution
        if self._pending_usb_drives is not None:
            pending = self._pending_usb_drives
            self._pending_usb_drives = None
            self._on_usb_drives_changed(pending)

        if success:
            if self.current_usb and hasattr(self.current_usb, "_refresh"):
                self.current_usb._refresh()
                self._update_usb_status_ui()
                idx = self.usb_combo.currentIndex()
                if 0 <= idx < len(self.all_drives):
                    label_txt = f"{self.current_usb.letter} [{self.current_usb.label}] ({self.current_usb.size_gb} GB, {self.current_usb.fs_type})"
                    self.usb_combo.setItemText(idx, label_txt)
            if hasattr(self, "view_backup"):
                self.view_backup.update_sync_button_state()
            if hasattr(self, "view_restore"):
                self.view_restore.populate_restore_combo()
            self.log_terminal(t("app.operation_success", "Operation completed successfully!"), "mint")
            if getattr(self, "_current_has_guard", True):
                self.log_terminal(t("logs.one_time_guard_active", "✓ Smart serial guard active (multi-car registry deployed)."), "cyan")
            title = getattr(self, "_current_success_title", "Operation Succeeded")
            msg = getattr(self, "_current_success_msg", "The requested payload has been prepared.")
            show_success_dialog(self, title, msg, usb_drive=self.current_usb.letter if self.current_usb else None)
        else:
            title = getattr(self, "_current_error_title", "Operation Failed")
            msg = err_msg or "An error occurred during execution."
            self.log_terminal(t("logs.error_occurred", f"Error: {msg}", msg=msg), "crimson")
            show_error_dialog(self, title, msg)

    def cancel_current_operation(self):
        if self.is_busy and self.current_worker:
            self.cancel_event.set()
            self.log_terminal(t("app.cancelling", "Cancelling operation, please wait..."), "warn")
            self.progress_control.lbl_status.setText(t("app.cancelling", "Cancelling operation..."))
            self.progress_control.btn_cancel.setEnabled(False)

    def show_confirm_dialog(self, title: str, text: str, confirm_text: str = "Continue", is_danger: bool = False) -> bool:
        return show_confirm_dialog(self, title, text, confirm_text=confirm_text, is_danger=is_danger)

    def show_success_dialog(self, title: str, text: str):
        return show_success_dialog(self, title, text, usb_drive=self.current_usb.letter if self.current_usb else None)

    def show_error_dialog(self, title: str, text: str):
        return show_error_dialog(self, title, text)

    def _open_basket_dialog(self):
        dlg = BasketDialog(self)
        dlg.prepare_requested.connect(self._execute_prepare_composite_basket)
        dlg.exec()

    def _execute_prepare_composite_basket(self):
        if self._check_busy_and_warn():
            return
        if not self._validate_usb_filesystem():
            return

        if self.basket.is_empty():
            self.show_error_dialog(t("basket.dialog_title"), t("basket.empty_msg"))
            return

        letter = self.current_usb.letter

        # If a reboot is scheduled, purge any open commands and launch targets since vehicle screen restarts
        if self.basket.has_reboot():
            if self.basket.get_current_launch_target():
                _, _, app_name = self.basket.get_current_launch_target()
                self.log_terminal(t("basket.reboot_launch_conflict", f"⚠️ Note: A system reboot is required for these operations. Auto-launch for '{app_name}' will be skipped to allow the vehicle screen to restart safely.", app_name=app_name), "warn")
            self.basket.remove_item("open_app")
            self.basket.remove_item("open_settings")
            self.basket.clear_all_launch_targets()

        ordered_items = self.basket.get_ordered_items()
        count = len(ordered_items)

        ops_lines = []
        for idx, it in enumerate(ordered_items, 1):
            extra = []
            if it.action_type == "install_gms":
                extra.append(t("basket.badge_clean_reinstall", "🧹 Clean Reinstall"))
            if it.requires_reboot or it.action_type == "reboot_screen":
                extra.append(t("basket.badge_reboot", "🔄 Reboot"))
            if it.launch_target_pkg:
                target_name = it.launch_target_name or it.launch_target_pkg
                extra.append(f"🚀 {target_name}")
            extra_str = f" [{', '.join(extra)}]" if extra else ""
            ops_lines.append(f"  {idx}. {it.title}{extra_str}")
        ops_list_str = "\n".join(ops_lines)

        confirm_title = t("basket.dialog_title", "🛒 Multi-Command Basket")
        reboots = self.basket.get_reboot_count()
        if reboots == 2:
            reboot_notice = "\n\n" + t(
                "basket.confirm_reboot_double",
                "⚠️ مسار التنفيذ: ستقوم الشاشة بعمل إعادتين تشغيل متتاليتين (ريستارت #1 بعد الفورمات، وريستارت #2 بعد التثبيت). يجب ترك الفلاشة موصولة طوال الوقت."
            )
        elif reboots == 1:
            reboot_notice = "\n\n" + t(
                "basket.confirm_reboot_single",
                "🔄 مسار التنفيذ: ستقوم الشاشة بإعادة تشغيل واحدة لتطبيق التعديلات. اترك الفلاشة موصولة حتى اكتمال الإقلاع."
            )
        else:
            reboot_notice = "\n\n" + t(
                "basket.confirm_reboot_none",
                "⚡ مسار التنفيذ: ستُنفذ العمليات مباشرة بدون أي إعادة تشغيل للشاشة (0 ريستارت)."
            )

        confirm_msg = t(
            "basket.confirm_exec_summary",
            f"Are you sure you want to prepare composite USB on drive {letter}?\n\nActual Vehicle Execution Sequence ({count} operations):\n{ops_list_str}",
            letter=letter,
            count=count,
            ops_list=ops_list_str
        ) + reboot_notice

        if not self.show_confirm_dialog(confirm_title, confirm_msg, confirm_text=t("basket.btn_prepare", "🚀 Prepare Composite USB")):
            return

        success_title = t("basket.success_title", "Composite USB Ready! 🚀")
        if reboots == 2:
            success_reboot_note = t(
                "basket.success_reboot_double",
                "⚠️ تنبيه هام: ستعمل الشاشة إعادة تشغيل مرتين متتاليتين في السيارة. اترك الفلاشة موصولة طوال فترات الإقلاع حتى يفتح التطبيق النهائي أو اللانشر."
            )
        elif reboots == 1:
            success_reboot_note = t(
                "basket.success_reboot_single",
                "⚠️ تنبيه هام: ستقوم الشاشة بإعادة تشغيل واحدة. اترك الفلاشة موصولة حتى اكتمال إقلاع النظام."
            )
        else:
            success_reboot_note = t(
                "basket.success_reboot_none",
                "✨ تنبيه: ستعمل العمليات بدون إعادة تشغيل للشاشة، ويمكنك نزع الفلاشة فور سماع صوت التنبيه."
            )

        success_msg = t("basket.success_msg", f"Composite customization USB prepared successfully on {letter}!", letter=letter) + f"\n\n{success_reboot_note}"

        self.execute_payload_worker(
            self.basket.prepare_composite_usb,
            letter,
            success_title=success_title,
            success_msg=success_msg,
            error_title="Composite USB Failed"
        )

    def prompt_launch_target_selection(self, new_action: str, new_pkg: str, new_name: str) -> bool:
        """
        Traps app launch conflicts across all entry points:
        - open_app view
        - install_apps auto-launch
        - GMS Play Store / Files
        Prompts user immediately if another target is active.
        """
        conflict = self.basket.check_launch_conflict(new_action, new_pkg, new_name)
        if conflict:
            cur_action, cur_pkg, cur_name = conflict
            confirm_title = t("basket.launch_conflict_title", "App Launch Conflict")
            confirm_msg = t(
                "basket.launch_conflict_msg",
                f"You already selected '{cur_name}' to launch in the basket.\n\nDo you want to switch to '{new_name}' instead?",
                current_name=cur_name,
                new_name=new_name
            )
            btn_switch = t("basket.btn_switch_launch", f"⚡ Switch to {new_name}", new_name=new_name)
            if self.show_confirm_dialog(confirm_title, confirm_msg, confirm_text=btn_switch, is_danger=False):
                self.basket.set_launch_target(new_action, new_pkg, new_name)
                if cur_action == "install_apps":
                    self.auto_launch_app_filename = None
                    if hasattr(self, "view_install_apps"):
                        self.view_install_apps.render_cards()
                self.log_terminal(f"Launch target switched to: {new_name} ({new_pkg})", "mint")
                return True
            else:
                return False
        else:
            self.basket.set_launch_target(new_action, new_pkg, new_name)
            return True

    def closeEvent(self, event):
        if hasattr(self, "usb_ctrl"):
            self.usb_ctrl.stop_watcher()
        elif hasattr(self, "usb_watcher"):
            self.usb_watcher.stop()
        if hasattr(self, "payload_ctrl") and self.payload_ctrl.is_busy:
            self.payload_ctrl.cancel_operation()
        if self.current_worker and self.current_worker.isRunning():
            self.cancel_event.set()
            self.current_worker.wait(1000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = AeroSuiteQtApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
