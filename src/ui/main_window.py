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
from core.exceptions import setup_global_exception_handler, log_exception, log_to_file
from ui.components.dialogs import show_confirm_dialog, show_success_dialog, show_error_dialog
from ui.components.progress_bar import ProgressControl
from ui.components.terminal import TerminalWidget
from ui.components.top_bar import TopBarWidget
from ui.components.side_nav import SideNavWidget, FEATURE_CATEGORIES
from ui.components.app_card import AppCard

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


def get_base_dir() -> str:
    if getattr(sys, 'frozen', False) or "__compiled__" in globals() or hasattr(sys, '__nuitka_version__'):
        if sys.argv and sys.argv[0]:
            candidate = os.path.dirname(os.path.abspath(sys.argv[0]))
            if os.path.exists(os.path.join(candidate, "apks")):
                return candidate
        if sys.executable:
            candidate = os.path.dirname(os.path.abspath(sys.executable))
            if os.path.exists(os.path.join(candidate, "apks")):
                return candidate
        if sys.argv and sys.argv[0]:
            return os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.dirname(os.path.abspath(sys.executable))

    fdir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(fdir) if os.path.basename(fdir).lower() == "src" else fdir


BASE_DIR = get_base_dir()
APKS_DIR = os.path.join(BASE_DIR, "apks")
GMS_DIR = os.path.join(APKS_DIR, "google_services")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")
FACTORY_BACKUP_DIR = os.path.join(BASE_DIR, "FactoryBackup")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

for d in [APKS_DIR, BACKUPS_DIR, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)


class UsbSignalBridge(QObject):
    """Bridges UsbWatcher background callbacks to Qt signals on the main thread."""
    drives_changed = Signal(list)


class PayloadWorker(QThread):
    """Executes a payload operation in the background and reports progress and logs."""
    progress_signal = Signal(int, str)
    log_signal = Signal(str, str)
    finished_signal = Signal(bool, str)

    def __init__(self, target_func, *args, cancel_event=None, **kwargs):
        super().__init__()
        self.target_func = target_func
        self.args = args
        self.kwargs = kwargs
        self.cancel_event = cancel_event or threading.Event()

    def run(self):
        try:
            def _log(msg, level="cyan", *a, **k):
                self.log_signal.emit(str(msg), str(level))

            def _progress(pct, text="", *a, **k):
                try:
                    pct_val = float(pct)
                    val = int(pct_val * 100) if pct_val <= 1.0 else int(pct_val)
                    val = max(0, min(100, val))
                    status_text = str(text)
                    if len(a) >= 3 and isinstance(a[1], (int, float)) and isinstance(a[2], (int, float)) and a[2] > 0:
                        spd = a[0] if isinstance(a[0], (int, float)) and a[0] > 0 else 0.0
                        if spd > 0.05:
                            status_text = f"Transferring {text} ({a[1]:.1f}/{a[2]:.1f} MB) • {spd:.1f} MB/s"
                        else:
                            status_text = f"Transferring {text} ({a[1]:.1f}/{a[2]:.1f} MB)"
                    self.progress_signal.emit(val, status_text)
                except Exception:
                    pass

            def _cancel_check(*a, **k):
                return self.cancel_event.is_set()

            success = self.target_func(
                *self.args,
                log_func=_log,
                progress_func=_progress,
                cancel_check=_cancel_check,
                **self.kwargs
            )
            if self.cancel_event.is_set():
                self.finished_signal.emit(False, "Operation cancelled by user.")
            else:
                self.finished_signal.emit(bool(success), "" if success else "Payload execution failed.")
        except Exception as e:
            log_exception(e, f"PayloadWorker running {getattr(self.target_func, '__name__', 'unknown')}")
            self.finished_signal.emit(False, str(e))


class AeroSuiteQtApp(QMainWindow):
    """Main Application Window for Aero Suite."""
    def __init__(self):
        super().__init__()
        setup_global_exception_handler()

        self.setWindowTitle(f"Aero Suite v{theme.APP_VERSION} — Automotive APK & System Studio")
        self.resize(1180, 800)
        self.setMinimumSize(1000, 680)

        # Global State
        self.all_drives = []
        self.current_usb = None
        self.is_busy = False
        self._pending_usb_drives = None
        self.current_worker = None
        self.cancel_event = threading.Event()
        self.feature_categories = FEATURE_CATEGORIES

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
        self.setStyleSheet(get_application_stylesheet())
        self._build_main_ui()

        # USB Bridge & Monitoring
        self.usb_bridge = UsbSignalBridge()
        self.usb_bridge.drives_changed.connect(self._on_usb_drives_changed)
        self.usb_watcher = UsbWatcher(callback=self.usb_bridge.drives_changed.emit, interval_sec=1.5)
        self.usb_watcher.start()

        # Initial Rescan
        QTimer.singleShot(100, self._initial_startup_log)

    def _initial_startup_log(self):
        self.log_terminal(f"Aero Suite v{theme.APP_VERSION} initialized successfully.", "cyan")
        self.log_terminal(f"Vetted APK Repository: {len(self.local_apks)} application(s) indexed.", "mint")
        drives = get_removable_drives()
        self._on_usb_drives_changed(drives)

    def _build_main_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
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
        main_layout.addWidget(self.top_bar)

        # 2. Developer Bio Bar
        dev_bar = QWidget()
        dev_bar.setFixedHeight(30)
        dev_bar.setStyleSheet(f"background-color: {theme.SURFACE_2}; border-bottom: 1px solid {theme.BORDER_SLATE};")
        dev_layout = QHBoxLayout(dev_bar)
        dev_layout.setContentsMargins(20, 2, 20, 2)

        lbl_dev = QLabel(f"👨‍💻 {DEVELOPER_NAME}   |   ✉️ {DEVELOPER_EMAIL}   |   📞 {DEVELOPER_PHONE}")
        lbl_dev.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED};")
        dev_layout.addWidget(lbl_dev)
        dev_layout.addStretch()
        lbl_gift = QLabel("🎁 Free Community Tool for Dongfeng Shine Owners")
        lbl_gift.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {theme.MINT_SUCCESS};")
        dev_layout.addWidget(lbl_gift)
        main_layout.addWidget(dev_bar)

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

        # Instantiate View Modules
        self.view_install_apps = InstallAppsView(self)
        self.view_uninstall_apps = UninstallAppsView(self)
        self.view_open_app = OpenAppView(self)
        self.view_open_settings = OpenSettingsView(self)
        self.view_install_gms = InstallGmsView(self, GMS_DIR)
        self.view_uninstall_gms = UninstallGmsView(self)
        self.view_disable_launcher = DisableLauncherView(self)
        self.view_enable_launcher = EnableLauncherView(self)
        self.view_reboot_screen = RebootScreenView(self)
        self.view_backup = BackupView(self, BACKUPS_DIR)
        self.view_restore = RestoreView(self, BACKUPS_DIR)
        self.view_factory_reset = FactoryResetView(self, FACTORY_BACKUP_DIR)
        self.view_fetch_logs = FetchLogsView(self)

        self.views_map = {
            "install_apps": self.view_install_apps,
            "uninstall_apps": self.view_uninstall_apps,
            "open_app": self.view_open_app,
            "open_settings": self.view_open_settings,
            "install_gms": self.view_install_gms,
            "uninstall_gms": self.view_uninstall_gms,
            "disable_launcher": self.view_disable_launcher,
            "enable_launcher": self.view_enable_launcher,
            "reboot_screen": self.view_reboot_screen,
            "backup": self.view_backup,
            "restore": self.view_restore,
            "factory_reset": self.view_factory_reset,
            "fetch_logs": self.view_fetch_logs
        }

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
        self.views = self.views_map

        for feat_id, view_widget in self.views_map.items():
            self.page_stack.addWidget(view_widget)

        content_layout.addWidget(self.page_stack)
        right_splitter.addWidget(content_frame)

        # Bottom Area: Progress Control & Terminal Widget
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(16, 6, 16, 10)
        bottom_layout.setSpacing(6)

        self.progress_control = ProgressControl(self)
        self.progress_control.cancel_clicked.connect(self.cancel_current_operation)
        self.prog_bar = self.progress_control.bar
        self.lbl_prog_status = self.progress_control.lbl_status
        self.btn_cancel = self.progress_control.btn_cancel
        bottom_layout.addWidget(self.progress_control)

        self.terminal = TerminalWidget(self)
        self.txt_terminal = self.terminal.txt_terminal
        self.terminal_edit = self.terminal.terminal_edit
        self._clear_terminal_log = self.terminal.clear_logs
        bottom_layout.addWidget(self.terminal)

        right_splitter.addWidget(bottom_widget)
        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 1)

        workspace_layout.addWidget(right_splitter)
        main_layout.addWidget(workspace)

        # Select first feature by default
        self.side_nav.select_feature("install_apps")

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
        self.log_terminal(f"Rescanned apks/ repository. Total: {len(self.local_apks)} packages.", "mint")

    @property
    def active_feature(self) -> str:
        return self.side_nav.current_feature if hasattr(self, "side_nav") else "install_apps"

    def switch_view(self, feat_id: str):
        if feat_id in self.views_map:
            self.page_stack.setCurrentWidget(self.views_map[feat_id])
            if hasattr(self, "side_nav") and self.side_nav.current_feature != feat_id:
                self.side_nav.select_feature(feat_id)
            if feat_id == "restore":
                self.view_restore.populate_restore_combo()
            elif feat_id == "backup":
                self.view_backup.update_sync_button_state()

    def _on_open_app_selected(self, filename: str, checked: bool = True):
        if checked:
            self.selected_open_app_filename = filename
        elif self.selected_open_app_filename == filename:
            self.selected_open_app_filename = ""
        self.view_open_app.sync_rows()

    def _on_language_changed(self, lang_code: str):
        from core.i18n import get_i18n, t
        get_i18n().set_language(lang_code)
        self.log_terminal(f"Language changed to: {lang_code.upper()} ({get_i18n().current_lang})", "mint")
        # Update top bar dynamic texts
        self.top_bar.lbl_title.setText(t("app.title", "⚡ AERO SUITE"))
        self.top_bar.lbl_sub.setText(t("app.subtitle", "Dongfeng Shine (Aeolus D53) IVI Studio"))
        self.top_bar.btn_refresh_usb.setText(t("common.refresh", "🔄 Refresh"))
        # Rerender views
        self.view_install_apps.render_cards()
        self.view_uninstall_apps.render_cards()
        self.view_open_app.render_rows()
        self.view_restore.populate_restore_combo()
        self.view_backup.update_sync_button_state()

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
            self.usb_combo.addItem("NO USB FLASH DETECTED")
            self.usb_combo.setToolTip("Please insert a removable USB flash drive to prepare payloads.")
            self.usb_status_dot.setStyleSheet(f"color: {theme.CRIMSON_DANGER}; font-size: 16px;")
            self.usb_status_dot.setToolTip("No USB Flash Drive Detected")
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
                self.log_terminal(f"⚠️ Multiple removable drives detected ({len(drives)} drives)! Please verify the target USB drive selected in the dropdown.", "warn")
            elif len(drives) == 1:
                self._last_warned_drive_count = 1

            if self.current_usb and getattr(self.current_usb, "has_backup", False):
                if getattr(self, "_last_logged_backup_drive", None) != self.current_usb.letter:
                    self._last_logged_backup_drive = self.current_usb.letter
                    self.log_terminal(f"Car backup detected on {self.current_usb.letter} (Date: {self.current_usb.backup_date}). Ready for PC Vault Sync.", "mint")
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
            self.usb_status_dot.setToolTip("No USB Flash Drive Detected")
            return

        is_fat32 = self.current_usb.fs_type.upper() == "FAT32"
        if is_fat32:
            self.usb_status_dot.setStyleSheet(f"color: {theme.MINT_SUCCESS}; font-size: 16px;")
            self.usb_status_dot.setToolTip(f"Ready: {self.current_usb.letter} ({self.current_usb.fs_type})")
        else:
            self.usb_status_dot.setStyleSheet(f"color: {theme.AMBER_WARN}; font-size: 16px;")
            self.usb_status_dot.setToolTip(f"Warning: {self.current_usb.fs_type} detected. FAT32 strongly recommended!")

    def _refresh_usb_drives(self):
        drives = get_removable_drives()
        self._on_usb_drives_changed(drives)
        if hasattr(self, "btn_refresh_usb"):
            self.btn_refresh_usb.setText("✓ Refreshed!")
            self.btn_refresh_usb.setStyleSheet(f"color: {theme.MINT_SUCCESS};")
            QTimer.singleShot(1200, lambda: (
                self.btn_refresh_usb.setText("🔄 Refresh"),
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
        a_open = menu.addAction("📂 Open in Windows Explorer")
        a_open.triggered.connect(self._open_usb_in_explorer)

        a_fmt = menu.addAction("⚡ Format Drive (FAT32)")
        a_fmt.triggered.connect(self._format_usb_fat32)

        menu.addSeparator()
        a_rescan = menu.addAction("🔄 Rescan Removable Drives")
        a_rescan.triggered.connect(self._refresh_usb_drives)

        if button_anchor:
            pos = self.btn_usb_settings.mapToGlobal(QPoint(0, self.btn_usb_settings.height() + 2))
        else:
            pos = QCursor.pos()
        menu.exec(pos)

    def _open_usb_in_explorer(self):
        if not self.current_usb or not os.path.exists(self.current_usb.letter):
            self.show_error_dialog("No Drive Selected", "Please select a valid USB flash drive first.")
            return
        os.system(f'explorer "{self.current_usb.letter}"')

    def _format_usb_fat32(self):
        if self._check_busy_and_warn():
            return
        if not self.current_usb or not os.path.exists(self.current_usb.letter):
            self.show_error_dialog("No USB Selected", "Please select a valid USB flash drive first.")
            return

        letter = self.current_usb.letter
        confirm_msg = (
            f"WARNING: FORMATTING WILL ERASE ALL DATA ON {letter}!\n\n"
            f"Target Drive: {letter} ({self.current_usb.label})\n"
            f"File System: FAT32 [AERO_USB]\n\n"
            f"Are you completely sure you want to format this drive now?"
        )
        if not show_confirm_dialog(self, "Confirm USB Format (FAT32)", confirm_msg, confirm_text="⚠️ FORMAT TO FAT32", is_danger=True):
            return

        self.execute_payload_worker(
            payload_engine.format_usb_drive,
            letter,
            volume_label="AERO_USB",
            success_title="Format Completed",
            success_msg=f"Drive {letter} successfully formatted to FAT32 [AERO_USB]!",
            error_title="Format Failed"
        )

    def _check_busy_and_warn(self) -> bool:
        if self.is_busy:
            self.show_error_dialog("Operation in Progress", "An operation is currently running. Please wait or cancel it first.")
            return True
        return False

    def _check_usb_ready(self) -> bool:
        if not self.current_usb:
            self.show_error_dialog("No USB Flash Drive", "Please insert a removable USB flash drive first.")
            return False
        return True

    def _validate_usb_filesystem(self) -> bool:
        if not self._check_usb_ready():
            return False
        if self.current_usb.fs_type.upper() != "FAT32":
            msg = (
                f"Drive {self.current_usb.letter} is formatted as {self.current_usb.fs_type}.\n\n"
                f"Dongfeng Shine infotainment hardware requires FAT32 for reliable USB recognition.\n\n"
                f"Would you like to format this drive to FAT32 now?"
            )
            if show_confirm_dialog(self, "Incompatible File System", msg, confirm_text="⚡ Format FAT32", is_danger=True):
                self._format_usb_fat32()
            return False
        return True

    # ---------------------------------------------------------
    # Worker Execution & Progress Management
    # ---------------------------------------------------------
    def execute_payload_worker(self, target_func, *args, success_title="", success_msg="", error_title="", **kwargs):
        self.is_busy = True
        self.cancel_event.clear()
        self.progress_control.reset()
        self.progress_control.show_control()

        self._current_success_title = success_title
        self._current_success_msg = success_msg
        self._current_error_title = error_title

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
            self.log_terminal("Operation completed successfully!", "mint")
            title = getattr(self, "_current_success_title", "Operation Succeeded")
            msg = getattr(self, "_current_success_msg", "The requested payload has been prepared.")
            show_success_dialog(self, title, msg, usb_drive=self.current_usb.letter if self.current_usb else None)
        else:
            title = getattr(self, "_current_error_title", "Operation Failed")
            msg = err_msg or "An error occurred during execution."
            self.log_terminal(f"Error: {msg}", "crimson")
            show_error_dialog(self, title, msg)

    def cancel_current_operation(self):
        if self.is_busy and self.current_worker:
            self.cancel_event.set()
            self.log_terminal("Cancelling operation, please wait...", "warn")
            self.progress_control.lbl_status.setText("Cancelling operation...")
            self.progress_control.btn_cancel.setEnabled(False)

    def show_confirm_dialog(self, title: str, text: str, confirm_text: str = "Continue", is_danger: bool = False) -> bool:
        return show_confirm_dialog(self, title, text, confirm_text=confirm_text, is_danger=is_danger)

    def show_success_dialog(self, title: str, text: str):
        return show_success_dialog(self, title, text, usb_drive=self.current_usb.letter if self.current_usb else None)

    def show_error_dialog(self, title: str, text: str):
        return show_error_dialog(self, title, text)

    def closeEvent(self, event):
        if hasattr(self, "usb_watcher"):
            self.usb_watcher.stop()
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
