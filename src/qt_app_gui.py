"""
qt_app_gui.py — Aero Suite Automotive Infotainment Management Console (PySide6 Edition).
Calibrated for Dongfeng Shine (Aeolus D53) IVI System.
Engineered by Abdelrhman Hamdy - Senior Software Engineer.
"""
import os
import sys
import threading
import time

from PySide6.QtCore import Qt, QThread, Signal, Slot, QObject, QTimer
from PySide6.QtGui import QIcon, QFont, QColor, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QStackedWidget, QLabel, QPushButton, QLineEdit,
    QCheckBox, QRadioButton, QButtonGroup, QComboBox, QProgressBar,
    QPlainTextEdit, QScrollArea, QFrame, QMessageBox, QSizePolicy,
    QSplitter
)

import theme
from qt_theme import get_application_stylesheet
from apk_engine import scan_local_apks
from usb_detector import get_removable_drives, UsbWatcher, UsbDriveInfo
from sync_manager import sync_backup_from_usb_to_pc, get_local_backups, find_existing_vault_backup
import payload_engine


# Path discovery
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
    progress_signal = Signal(float, str)
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
            def _log(msg, level="cyan"):
                self.log_signal.emit(str(msg), level)

            def _progress(pct, text=""):
                self.progress_signal.emit(float(pct), str(text))

            def _cancel_check():
                return self.cancel_event.is_set()

            import inspect
            sig = inspect.signature(self.target_func)
            accepted = sig.parameters
            call_kwargs = dict(self.kwargs)
            if "log_func" in accepted:
                call_kwargs["log_func"] = _log
            if "progress_func" in accepted:
                call_kwargs["progress_func"] = _progress
            if "progress_callback" in accepted:
                call_kwargs["progress_callback"] = lambda pct, cur_f="", spd=0.0, c_mb=0.0, t_mb=0.0: _progress(pct, f"Syncing {cur_f} ({c_mb:.1f}/{t_mb:.1f} MB)" if cur_f else "Syncing...")
            if "cancel_check" in accepted:
                call_kwargs["cancel_check"] = _cancel_check

            ok = self.target_func(*self.args, **call_kwargs)
            self.finished_signal.emit(bool(ok), "")
        except Exception as e:
            self.log_signal.emit(f"Operation Exception: {e}", "danger")
            self.finished_signal.emit(False, str(e))


class AeroSuiteQtApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Aero Suite v{theme.APP_VERSION} — Dongfeng Shine IVI Studio")
        self.setMinimumSize(1050, 680)

        # State
        self.current_usb: UsbDriveInfo = None
        self.all_drives = []
        self.active_feature = "install_apps"
        self.is_busy = False
        self.current_worker = None
        self.cancel_event = threading.Event()

        # APK State
        self.local_apks = scan_local_apks(APKS_DIR)
        self.allowed_packages = {a["package"] for a in self.local_apks if a["package"]}
        self.selected_install_apks = {a["filename"]: False for a in self.local_apks}
        self.per_app_portrait = {a["filename"]: False for a in self.local_apks}
        self.per_app_target = {a["filename"]: "user" for a in self.local_apks}
        self.per_app_boot = {a["filename"]: False for a in self.local_apks}
        self.auto_launch_app_filename = None

        self.selected_uninstall_pkgs = {a["package"]: False for a in self.local_apks if a["package"]}
        self.selected_open_app_filename = None

        # Search queries
        self.install_search_query = ""
        self.uninstall_search_query = ""
        self.open_app_search_query = ""

        # Apply Stylesheet
        self.setStyleSheet(get_application_stylesheet())

        # Build Main UI
        self._init_ui()

        # Start USB Watcher
        self.usb_bridge = UsbSignalBridge()
        self.usb_bridge.drives_changed.connect(self._on_usb_drives_changed)
        self.usb_watcher = UsbWatcher(callback=self.usb_bridge.drives_changed.emit, interval_sec=1.5)
        self.usb_watcher.start()

        # Initial USB scan
        self._refresh_usb_drives()

        # Open maximized on startup
        self.showMaximized()

        # Initial greeting log
        self.log_terminal(f"Aero Suite v{theme.APP_VERSION} initialized successfully.", "mint")
        self.log_terminal(f"Vetted APK Repository: {len(self.local_apks)} application(s) indexed.", "cyan")

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---------------------------------------------------------
        # LEFT SIDEBAR
        # ---------------------------------------------------------
        sidebar = QWidget()
        sidebar.setObjectName("sidebarPanel")
        sidebar.setFixedWidth(270)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 14, 10, 10)
        sidebar_layout.setSpacing(6)

        # App Branding Header
        header_widget = QWidget()
        h_layout = QVBoxLayout(header_widget)
        h_layout.setContentsMargins(8, 4, 8, 8)
        h_layout.setSpacing(2)

        lbl_title = QLabel("AERO SUITE")
        lbl_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme.CYAN_PRIMARY}; letter-spacing: 2px;")
        lbl_sub = QLabel("Dongfeng Shine IVI Studio")
        lbl_sub.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED};")
        lbl_ver = QLabel(f"Version {theme.APP_VERSION}")
        lbl_ver.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_DIM};")

        h_layout.addWidget(lbl_title)
        h_layout.addWidget(lbl_sub)
        h_layout.addWidget(lbl_ver)
        sidebar_layout.addWidget(header_widget)

        # USB Drive Selector Card
        usb_card = QFrame()
        usb_card.setProperty("class", "card")
        usb_card_layout = QVBoxLayout(usb_card)
        usb_card_layout.setContentsMargins(10, 10, 10, 10)
        usb_card_layout.setSpacing(6)

        usb_header = QHBoxLayout()
        lbl_usb_title = QLabel("🎯 TARGET USB DRIVE")
        lbl_usb_title.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        btn_refresh_usb = QPushButton("🔄")
        btn_refresh_usb.setFixedSize(24, 24)
        btn_refresh_usb.setToolTip("Rescan connected USB drives")
        btn_refresh_usb.clicked.connect(self._refresh_usb_drives)
        usb_header.addWidget(lbl_usb_title)
        usb_header.addStretch()
        usb_header.addWidget(btn_refresh_usb)
        usb_card_layout.addLayout(usb_header)

        self.usb_combo = QComboBox()
        self.usb_combo.currentIndexChanged.connect(self._on_usb_selected)
        usb_card_layout.addWidget(self.usb_combo)

        self.lbl_usb_info = QLabel("Searching for USB drives...")
        self.lbl_usb_info.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_MUTED};")
        self.lbl_usb_info.setWordWrap(True)
        usb_card_layout.addWidget(self.lbl_usb_info)

        sidebar_layout.addWidget(usb_card)

        # Navigation Scroll Area
        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_widget = QWidget()
        self.nav_layout = QVBoxLayout(nav_widget)
        self.nav_layout.setContentsMargins(0, 4, 0, 4)
        self.nav_layout.setSpacing(2)

        self.nav_buttons = {}

        def _add_category(title):
            lbl = QLabel(title)
            lbl.setProperty("class", "navCategory")
            self.nav_layout.addWidget(lbl)

        def _add_nav_btn(feature_id, text, icon=""):
            btn = QPushButton(f"{icon}  {text}".strip())
            btn.setProperty("class", "navBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda: self.switch_view(feature_id))
            self.nav_layout.addWidget(btn)
            self.nav_buttons[feature_id] = btn

        _add_category("APPLICATIONS & STORE")
        _add_nav_btn("install_apps", "Install Applications", "⚡")
        _add_nav_btn("uninstall_apps", "Safe Uninstall Apps", "🛡")
        _add_nav_btn("install_gms", "Google Play Services", "🌐")
        _add_nav_btn("uninstall_gms", "Remove Google Services", "🗑")
        _add_nav_btn("open_settings", "Open Android Settings", "⚙")
        _add_nav_btn("open_app", "Launch Application", "🚀")

        _add_category("SYSTEM CONTROL")
        _add_nav_btn("disable_launcher", "Disable Factory Launcher", "🔒")
        _add_nav_btn("enable_launcher", "Enable Factory Launcher", "🔓")
        _add_nav_btn("reboot_screen", "Restart Infotainment", "🔄")

        _add_category("VAULT & RESCUE")
        _add_nav_btn("backup", "Vehicle Backup & Sync", "💾")
        _add_nav_btn("restore", "Restore from Backup", "♻")
        _add_nav_btn("factory_reset", "Zero-Trace Factory Reset", "⚠️")
        _add_nav_btn("fetch_logs", "Diagnostic Logs", "📋")

        self.nav_layout.addStretch()
        nav_scroll.setWidget(nav_widget)
        sidebar_layout.addWidget(nav_scroll)

        # Developer Info / About Button
        btn_about = QPushButton("ℹ️  Engineer Info & Community")
        btn_about.setProperty("class", "navBtn")
        btn_about.clicked.connect(self._show_about_dialog)
        sidebar_layout.addWidget(btn_about)

        main_layout.addWidget(sidebar)

        # ---------------------------------------------------------
        # RIGHT AREA: CONTENT & TERMINAL
        # ---------------------------------------------------------
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.setHandleWidth(1)

        # Top Section: Header & Content Pages
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Top Bar Panel
        top_bar = QWidget()
        top_bar.setObjectName("topBarPanel")
        top_bar.setFixedHeight(50)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 0, 20, 0)

        self.lbl_active_title = QLabel("⚡ INSTALL APPLICATIONS")
        self.lbl_active_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.TEXT_PRIMARY};")
        top_layout.addWidget(self.lbl_active_title)
        top_layout.addStretch()

        self.lbl_usb_status_chip = QLabel("🔴 NO USB DETECTED")
        self.lbl_usb_status_chip.setStyleSheet(
            f"background-color: {theme.SURFACE_2}; color: {theme.CRIMSON_DANGER}; "
            f"border: 1px solid {theme.BORDER_SLATE}; border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 11px;"
        )
        top_layout.addWidget(self.lbl_usb_status_chip)

        self.btn_cancel_op = QPushButton("⏹ CANCEL")
        self.btn_cancel_op.setProperty("class", "btnDanger")
        self.btn_cancel_op.setFixedHeight(28)
        self.btn_cancel_op.setVisible(False)
        self.btn_cancel_op.clicked.connect(self.cancel_current_operation)
        top_layout.addWidget(self.btn_cancel_op)

        content_layout.addWidget(top_bar)

        # Stacked Pages Widget
        self.page_stack = QStackedWidget()
        content_layout.addWidget(self.page_stack)

        right_splitter.addWidget(content_container)

        # Bottom Section: Terminal & Progress Bar
        bottom_panel = QWidget()
        bottom_panel.setObjectName("bottomPanel")
        bottom_panel.setFixedHeight(180)
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(16, 8, 16, 8)
        bottom_layout.setSpacing(6)

        # Terminal Header Bar
        term_bar = QHBoxLayout()
        lbl_term = QLabel("💻 TERMINAL & SYSTEM LOGS")
        lbl_term.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {theme.TEXT_MUTED};")
        term_bar.addWidget(lbl_term)
        term_bar.addStretch()

        btn_copy_log = QPushButton("Copy Logs")
        btn_copy_log.setFixedHeight(22)
        btn_copy_log.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        btn_copy_log.clicked.connect(self._copy_terminal_log)
        term_bar.addWidget(btn_copy_log)

        btn_clear_log = QPushButton("Clear")
        btn_clear_log.setFixedHeight(22)
        btn_clear_log.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        btn_clear_log.clicked.connect(self._clear_terminal_log)
        term_bar.addWidget(btn_clear_log)
        bottom_layout.addLayout(term_bar)

        # Terminal Output Box
        self.terminal_edit = QPlainTextEdit()
        self.terminal_edit.setObjectName("terminalEdit")
        self.terminal_edit.setReadOnly(True)
        bottom_layout.addWidget(self.terminal_edit)

        # Progress & Status Bar
        status_bar = QHBoxLayout()
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED};")
        status_bar.addWidget(self.lbl_status)
        status_bar.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(240)
        self.progress_bar.setValue(0)
        status_bar.addWidget(self.progress_bar)
        bottom_layout.addLayout(status_bar)

        right_splitter.addWidget(bottom_panel)
        right_splitter.setStretchFactor(0, 4)
        right_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(right_splitter)

        # Instantiate View Pages
        self.views = {}
        self._init_views()
        self.switch_view("install_apps")

    # ---------------------------------------------------------
    # VIEW INITIALIZATION & ROUTING
    # ---------------------------------------------------------
    def _init_views(self):
        self._add_view("install_apps", self._build_view_install_apps())
        self._add_view("uninstall_apps", self._build_view_uninstall_apps())
        self._add_view("install_gms", self._build_view_install_gms())
        self._add_view("uninstall_gms", self._build_view_uninstall_gms())
        self._add_view("open_settings", self._build_view_open_settings())
        self._add_view("open_app", self._build_view_open_app())
        self._add_view("disable_launcher", self._build_view_disable_launcher())
        self._add_view("enable_launcher", self._build_view_enable_launcher())
        self._add_view("reboot_screen", self._build_view_reboot_screen())
        self._add_view("backup", self._build_view_backup())
        self._add_view("restore", self._build_view_restore())
        self._add_view("factory_reset", self._build_view_factory_reset())
        self._add_view("fetch_logs", self._build_view_fetch_logs())

    def _add_view(self, name: str, widget: QWidget):
        self.views[name] = widget
        self.page_stack.addWidget(widget)

    def switch_view(self, feature_id: str):
        if feature_id not in self.views:
            return
        self.active_feature = feature_id
        self.page_stack.setCurrentWidget(self.views[feature_id])

        # Update Nav Button active state
        for fid, btn in self.nav_buttons.items():
            btn.setProperty("active", "true" if fid == feature_id else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Update Top Bar Title
        title_map = {
            "install_apps": "⚡ INSTALL APPLICATIONS",
            "uninstall_apps": "🛡 SAFE UNINSTALL APPS",
            "install_gms": "🌐 GOOGLE PLAY SERVICES SETUP",
            "uninstall_gms": "🗑 REMOVE GOOGLE PLAY SERVICES",
            "open_settings": "⚙ OPEN ANDROID SETTINGS",
            "open_app": "🚀 LAUNCH SPECIFIC APPLICATION",
            "disable_launcher": "🔒 DISABLE FACTORY LAUNCHER",
            "enable_launcher": "🔓 ENABLE FACTORY LAUNCHER",
            "reboot_screen": "🔄 RESTART INFOTAINMENT SCREEN",
            "backup": "💾 VEHICLE BACKUP & PC VAULT",
            "restore": "♻ RESTORE VEHICLE FROM BACKUP",
            "factory_reset": "⚠️ ZERO-TRACE FACTORY RESET",
            "fetch_logs": "📋 DIAGNOSTIC LOGS EXTRACTION",
        }
        self.lbl_active_title.setText(title_map.get(feature_id, feature_id.upper()))

    # ---------------------------------------------------------
    # USB MANAGEMENT & SIGNALS
    # ---------------------------------------------------------
    def _refresh_usb_drives(self):
        drives = get_removable_drives()
        self._on_usb_drives_changed(drives)

    @Slot(list)
    def _on_usb_drives_changed(self, drives: list):
        self.all_drives = drives
        self.usb_combo.blockSignals(True)
        self.usb_combo.clear()

        if not drives:
            self.current_usb = None
            self.usb_combo.addItem("No Removable USB Found")
            self.lbl_usb_info.setText("Insert a FAT32/exFAT USB flash drive into your PC.")
            self.lbl_usb_status_chip.setText("🔴 NO USB DETECTED")
            self.lbl_usb_status_chip.setStyleSheet(
                f"background-color: {theme.SURFACE_2}; color: {theme.CRIMSON_DANGER}; "
                f"border: 1px solid {theme.BORDER_SLATE}; border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 11px;"
            )
        else:
            prev_letter = self.current_usb.letter if self.current_usb else None
            matched_idx = 0
            for i, d in enumerate(drives):
                item_text = f"{d.drive_letter_only}:\\ [{d.label or 'USB'}] ({d.free_gb:.1f} GB free)"
                self.usb_combo.addItem(item_text, userData=d)
                if prev_letter and d.letter == prev_letter:
                    matched_idx = i

            self.usb_combo.setCurrentIndex(matched_idx)
            self.current_usb = drives[matched_idx]
            self._update_usb_display()

        self.usb_combo.blockSignals(False)

    def _on_usb_selected(self, index: int):
        drive = self.usb_combo.currentData()
        if drive and isinstance(drive, UsbDriveInfo):
            self.current_usb = drive
            self._update_usb_display()

    def _update_usb_display(self):
        if not self.current_usb:
            return
        d = self.current_usb
        fs_warn = " ⚠️ FAT32 is required for Dongfeng IVI" if d.fs_name.upper() != "FAT32" else " ✅ FAT32 Compatible"
        self.lbl_usb_info.setText(f"{d.label}\n{d.fs_name} • {d.free_gb:.1f} GB free of {d.total_gb:.1f} GB{fs_warn}")
        self.lbl_usb_status_chip.setText(f"🟢 USB: {d.drive_letter_only}:\\ ({d.fs_name}, {d.free_gb:.1f} GB Free)")
        self.lbl_usb_status_chip.setStyleSheet(
            f"background-color: {theme.SURFACE_2}; color: {theme.MINT_SUCCESS}; "
            f"border: 1px solid {theme.BORDER_CYAN}; border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 11px;"
        )

    def _check_usb_ready(self) -> bool:
        if not self.current_usb:
            self.show_error_dialog("No USB Drive", "Please insert a removable USB flash drive to continue.")
            return False
        return True

    # ---------------------------------------------------------
    # LOGGING & TERMINAL
    # ---------------------------------------------------------
    @Slot(str, str)
    def log_terminal(self, message: str, level: str = "cyan"):
        t_stamp = time.strftime("[%H:%M:%S] ")
        color_map = {
            "cyan": theme.TERM_TEXT_CYAN,
            "mint": theme.TERM_TEXT_MINT,
            "success": theme.TERM_TEXT_MINT,
            "danger": theme.CRIMSON_DANGER,
            "rose": theme.TERM_TEXT_ROSE,
            "warn": theme.AMBER_WARN,
            "dim": theme.TERM_TEXT_DIM
        }
        hex_col = color_map.get(level.lower(), theme.TERM_TEXT_CYAN)
        html_msg = f'<span style="color:{theme.TEXT_DIM};">{t_stamp}</span><span style="color:{hex_col};">{message}</span>'
        self.terminal_edit.appendHtml(html_msg)
        self.terminal_edit.moveCursor(QTextCursor.End)

    def _copy_terminal_log(self):
        text = self.terminal_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.log_terminal("Logs copied to clipboard.", "mint")

    def _clear_terminal_log(self):
        self.terminal_edit.clear()

    # ---------------------------------------------------------
    # PROGRESS & BACKGROUND TASK MANAGEMENT
    # ---------------------------------------------------------
    def set_operation_state(self, is_busy: bool, loading_text: str = ""):
        self.is_busy = is_busy
        self.btn_cancel_op.setVisible(is_busy)
        if is_busy:
            self.lbl_status.setText(loading_text or "Operation in progress...")
            self.progress_bar.setValue(5)
        else:
            self.lbl_status.setText("Ready")
            self.progress_bar.setValue(100)
            QTimer.singleShot(1500, lambda: self.progress_bar.setValue(0))

    def cancel_current_operation(self):
        if self.current_worker and self.is_busy:
            self.cancel_event.set()
            self.log_terminal("Cancellation requested by user. Waiting for safe abort...", "warn")

    def execute_payload_worker(self, target_func, *args, success_title="", success_msg="", error_title="", error_msg="", **kwargs):
        self.cancel_event.clear()
        self.set_operation_state(True, "Preparing USB Payload...")

        worker = PayloadWorker(target_func, *args, cancel_event=self.cancel_event, **kwargs)
        self.current_worker = worker

        worker.progress_signal.connect(lambda pct, txt: (self.progress_bar.setValue(int(pct)), self.lbl_status.setText(txt)))
        worker.log_signal.connect(self.log_terminal)

        def _on_finished(ok, err):
            self.set_operation_state(False)
            self.current_worker = None
            if ok:
                self.log_terminal("Operation completed successfully!", "mint")
                if success_title:
                    self.show_success_dialog(success_title, success_msg)
            else:
                self.log_terminal(f"Operation failed or cancelled: {err}", "danger")
                if error_title:
                    self.show_error_dialog(error_title, error_msg or f"Error: {err}")

        worker.finished_signal.connect(_on_finished)
        worker.start()

    # ---------------------------------------------------------
    # DIALOG HELPERS (NATIVE QT MESSAGE BOXES)
    # ---------------------------------------------------------
    def show_confirm_dialog(self, title: str, message: str, confirm_text: str = "Proceed", is_danger: bool = False) -> bool:
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Warning if is_danger else QMessageBox.Question)
        btn_yes = msg_box.addButton(confirm_text, QMessageBox.YesRole)
        btn_no = msg_box.addButton("Cancel", QMessageBox.NoRole)
        if is_danger:
            btn_yes.setStyleSheet(f"background-color: {theme.CRIMSON_DANGER}; color: white; font-weight: bold;")
        else:
            btn_yes.setStyleSheet(f"background-color: {theme.CYAN_PRIMARY}; color: black; font-weight: bold;")
        msg_box.exec()
        return msg_box.clickedButton() == btn_yes

    def show_success_dialog(self, title: str, message: str):
        QMessageBox.information(self, title, message)

    def show_error_dialog(self, title: str, message: str):
        QMessageBox.critical(self, title, message)

    def _show_about_dialog(self):
        about_text = (
            f"Aero Automotive Suite — Dongfeng Edition (v{theme.APP_VERSION})\n\n"
            f"Developed & Maintained By:\n"
            f"{theme.DEVELOPER_NAME}\n"
            f"✉️ {theme.DEVELOPER_EMAIL}\n"
            f"📞 {theme.DEVELOPER_PHONE}\n\n"
            f"{theme.GIFT_COMMUNITY_TEXT}"
        )
        QMessageBox.information(self, "About Aero Suite", about_text)

    # ---------------------------------------------------------
    # VIEW 1: INSTALL APPS
    # ---------------------------------------------------------
    def _build_view_install_apps(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Controls Strip
        ctrl_bar = QHBoxLayout()
        btn_all = QPushButton("Select All")
        btn_all.clicked.connect(lambda: self._set_all_install_apks(True))
        ctrl_bar.addWidget(btn_all)

        btn_none = QPushButton("Deselect All")
        btn_none.clicked.connect(lambda: self._set_all_install_apks(False))
        ctrl_bar.addWidget(btn_none)

        btn_invert = QPushButton("Invert")
        btn_invert.clicked.connect(self._invert_install_selection)
        ctrl_bar.addWidget(btn_invert)

        btn_refresh = QPushButton("🔄 Rescan APKs")
        btn_refresh.clicked.connect(self._rescan_apks)
        ctrl_bar.addWidget(btn_refresh)

        ctrl_bar.addSpacing(10)
        self.install_search_edit = QLineEdit()
        self.install_search_edit.setPlaceholderText("🔍 Search by App Name, Package, or Filename...")
        self.install_search_edit.textChanged.connect(self._filter_install_apks)
        ctrl_bar.addWidget(self.install_search_edit)

        layout.addLayout(ctrl_bar)

        # Global Partition Target Strip
        part_bar = QHBoxLayout()
        lbl_target = QLabel("Global Target Partition:")
        lbl_target.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED};")
        part_bar.addWidget(lbl_target)

        btn_all_user = QPushButton("Set All to User (/data/app)")
        btn_all_user.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        btn_all_user.clicked.connect(lambda: self._set_global_target("user"))
        part_bar.addWidget(btn_all_user)

        btn_all_sys = QPushButton("Set All to System (/system/app)")
        btn_all_sys.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        btn_all_sys.clicked.connect(lambda: self._set_global_target("system"))
        part_bar.addWidget(btn_all_sys)

        part_bar.addStretch()
        layout.addLayout(part_bar)

        # Scroll Area for APK Cards
        self.install_scroll = QScrollArea()
        self.install_scroll.setWidgetResizable(True)
        self.install_cards_container = QWidget()
        self.install_cards_layout = QVBoxLayout(self.install_cards_container)
        self.install_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.install_cards_layout.setSpacing(6)
        self.install_scroll.setWidget(self.install_cards_container)
        layout.addWidget(self.install_scroll)

        # Action Button
        self.btn_prepare_install = QPushButton("⚡ PREPARE INSTALL USB")
        self.btn_prepare_install.setProperty("class", "btnPrimary")
        self.btn_prepare_install.setFixedHeight(44)
        self.btn_prepare_install.clicked.connect(self._execute_prepare_install_usb)
        layout.addWidget(self.btn_prepare_install)

        self._render_install_cards()
        self._update_install_button()
        return view

    def _render_install_cards(self):
        # Clear existing
        while self.install_cards_layout.count():
            item = self.install_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        q = self.install_search_query.strip().lower()
        matching = [
            a for a in self.local_apks
            if not q or (q in a["display_name"].lower() or q in a["package"].lower() or q in a["filename"].lower())
        ]

        if not matching:
            empty_lbl = QLabel("No APK packages found matching search criteria.")
            empty_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding: 20px; font-size: 13px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.install_cards_layout.addWidget(empty_lbl)
            self.install_cards_layout.addStretch()
            return

        self.install_checkboxes = {}
        for a in matching:
            fname = a["filename"]
            card = QFrame()
            card.setProperty("class", "card")
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(12, 8, 12, 8)
            c_layout.setSpacing(12)

            # Checkbox + Title
            chk = QCheckBox(f"{a['display_name']}")
            chk.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {theme.TEXT_PRIMARY};")
            chk.setChecked(self.selected_install_apks.get(fname, False))
            chk.stateChanged.connect(lambda state, fn=fname: self._on_install_chk_changed(fn, bool(state)))
            self.install_checkboxes[fname] = chk
            c_layout.addWidget(chk)

            # Details (Package & Size)
            lbl_meta = QLabel(f"({a['package']}) • {a['size_mb']} MB")
            lbl_meta.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED};")
            c_layout.addWidget(lbl_meta)
            c_layout.addStretch()

            # Target Partition Combo
            combo_target = QComboBox()
            combo_target.addItems(["User (/data)", "System (/system)"])
            combo_target.setCurrentIndex(0 if self.per_app_target.get(fname, "user") == "user" else 1)
            combo_target.currentIndexChanged.connect(lambda idx, fn=fname: self.per_app_target.update({fn: "user" if idx == 0 else "system"}))
            c_layout.addWidget(combo_target)

            # Force Portrait Checkbox
            chk_port = QCheckBox("Portrait")
            chk_port.setStyleSheet(f"font-size: 11px; color: {theme.AMBER_WARN};")
            chk_port.setChecked(self.per_app_portrait.get(fname, False))
            chk_port.stateChanged.connect(lambda state, fn=fname: self.per_app_portrait.update({fn: bool(state)}))
            c_layout.addWidget(chk_port)

            # Block Boot Checkbox
            chk_boot = QCheckBox("Block Boot")
            chk_boot.setStyleSheet(f"font-size: 11px; color: {theme.CRIMSON_DANGER};")
            chk_boot.setChecked(self.per_app_boot.get(fname, False))
            chk_boot.stateChanged.connect(lambda state, fn=fname: self.per_app_boot.update({fn: bool(state)}))
            c_layout.addWidget(chk_boot)

            # Auto Launch Checkbox (Single-select across list)
            chk_auto = QCheckBox("🚀 Auto Launch")
            chk_auto.setStyleSheet(f"font-size: 11px; color: {theme.CYAN_PRIMARY}; font-weight: bold;")
            chk_auto.setChecked(self.auto_launch_app_filename == fname)
            chk_auto.stateChanged.connect(lambda state, fn=fname: self._on_auto_launch_changed(fn, bool(state)))
            c_layout.addWidget(chk_auto)

            self.install_cards_layout.addWidget(card)

        self.install_cards_layout.addStretch()

    def _on_install_chk_changed(self, filename: str, is_checked: bool):
        self.selected_install_apks[filename] = is_checked
        self._update_install_button()

    def _on_auto_launch_changed(self, filename: str, is_checked: bool):
        if is_checked:
            self.auto_launch_app_filename = filename
            # Automatically ensure the app is selected for install
            self.selected_install_apks[filename] = True
        elif self.auto_launch_app_filename == filename:
            self.auto_launch_app_filename = None
        self._render_install_cards()
        self._update_install_button()

    def _set_all_install_apks(self, state: bool):
        q = self.install_search_query.strip().lower()
        for a in self.local_apks:
            fname = a["filename"]
            if not q or (q in a["display_name"].lower() or q in a["package"].lower() or q in a["filename"].lower()):
                self.selected_install_apks[fname] = state
        self._render_install_cards()
        self._update_install_button()

    def _invert_install_selection(self):
        q = self.install_search_query.strip().lower()
        for a in self.local_apks:
            fname = a["filename"]
            if not q or (q in a["display_name"].lower() or q in a["package"].lower() or q in a["filename"].lower()):
                self.selected_install_apks[fname] = not self.selected_install_apks.get(fname, False)
        self._render_install_cards()
        self._update_install_button()

    def _set_global_target(self, target: str):
        for a in self.local_apks:
            self.per_app_target[a["filename"]] = target
        self._render_install_cards()

    def _filter_install_apks(self, text: str):
        self.install_search_query = text
        self._render_install_cards()

    def _rescan_apks(self):
        self.local_apks = scan_local_apks(APKS_DIR)
        for a in self.local_apks:
            fn = a["filename"]
            if fn not in self.selected_install_apks:
                self.selected_install_apks[fn] = False
                self.per_app_portrait[fn] = False
                self.per_app_target[fn] = "user"
                self.per_app_boot[fn] = False
        self._render_install_cards()
        self._update_install_button()
        self.log_terminal(f"Rescanned apks/ repository. Total: {len(self.local_apks)} packages.", "mint")

    def _update_install_button(self):
        selected_count = sum(1 for v in self.selected_install_apks.values() if v)
        if selected_count > 0:
            self.btn_prepare_install.setText(f"⚡ PREPARE INSTALL USB ({selected_count} APPLICATION{'S' if selected_count > 1 else ''} SELECTED)")
            self.btn_prepare_install.setEnabled(True)
        else:
            self.btn_prepare_install.setText("👆 SELECT AT LEAST ONE APPLICATION TO INSTALL")
            self.btn_prepare_install.setEnabled(False)

    def _execute_prepare_install_usb(self):
        if not self._check_usb_ready(): return
        if self.is_busy: return

        selected = [a for a in self.local_apks if self.selected_install_apks.get(a["filename"], False)]
        if not selected:
            return

        letter = self.current_usb.letter
        if len(selected) <= 15:
            apps_list = "\n".join(f"  {i+1}. {a['display_name']} (~{a['size_mb']} MB)" for i, a in enumerate(selected))
        else:
            first_12 = "\n".join(f"  {i+1}. {a['display_name']} (~{a['size_mb']} MB)" for i, a in enumerate(selected[:12]))
            remaining = len(selected) - 12
            apps_list = f"{first_12}\n  ... and {remaining} more applications"

        auto_info = f"\n\n🚀 Auto-Launch App: {self.auto_launch_app_filename}" if self.auto_launch_app_filename else ""
        confirm_msg = (
            f"Are you sure you want to prepare Application Installation USB on drive {letter}?\n\n"
            f"Selected Applications to Install ({len(selected)}):\n"
            f"{apps_list}"
            f"{auto_info}\n\n"
            f"This will copy the packages and write automated vehicle installation scripts to the USB drive."
        )
        if not self.show_confirm_dialog("Confirm Application Installation USB", confirm_msg, confirm_text="⚡ Prepare Install USB"):
            return

        selected_payload = []
        for a in selected:
            f = a["filename"]
            selected_payload.append({
                "filename": f,
                "path": a["path"],
                "package": a["package"],
                "display_name": a["display_name"],
                "size_mb": a["size_mb"],
                "force_portrait": self.per_app_portrait.get(f, False),
                "install_target": self.per_app_target.get(f, "user"),
                "block_boot": self.per_app_boot.get(f, False)
            })

        auto_launch_pkg = ""
        if self.auto_launch_app_filename:
            target_a = next((a for a in selected if a["filename"] == self.auto_launch_app_filename), None)
            if target_a and target_a.get("package"):
                auto_launch_pkg = target_a["package"]

        self.execute_payload_worker(
            payload_engine.prepare_install_apps_usb,
            letter,
            selected_payload,
            auto_launch_package=auto_launch_pkg,
            success_title="Install Apps USB Ready",
            success_msg=f"Successfully prepared Install Applications USB on drive {letter}!\n\nSafely unplug and insert into vehicle.",
            error_title="Install Apps USB Failed"
        )

    # ---------------------------------------------------------
    # VIEW 2: UNINSTALL APPS
    # ---------------------------------------------------------
    def _build_view_uninstall_apps(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Safety Banner
        banner = QFrame()
        banner.setProperty("class", "card")
        b_layout = QVBoxLayout(banner)
        lbl_banner = QLabel("🔒 STRICT SAFETY LOCK: Only apps originating from your vetted apks/ repository can be uninstalled.\nPurges from BOTH User Apps (/data/app) and System Apps (/system/priv-app & /system/app).")
        lbl_banner.setStyleSheet(f"font-size: 11px; color: {theme.MINT_SUCCESS};")
        b_layout.addWidget(lbl_banner)
        layout.addWidget(banner)

        # Controls Strip
        ctrl_bar = QHBoxLayout()
        btn_all = QPushButton("Select All")
        btn_all.clicked.connect(lambda: self._set_all_uninstall_pkgs(True))
        ctrl_bar.addWidget(btn_all)

        btn_none = QPushButton("Deselect All")
        btn_none.clicked.connect(lambda: self._set_all_uninstall_pkgs(False))
        ctrl_bar.addWidget(btn_none)

        ctrl_bar.addSpacing(10)
        self.uninstall_search_edit = QLineEdit()
        self.uninstall_search_edit.setPlaceholderText("🔍 Search packages to uninstall...")
        self.uninstall_search_edit.textChanged.connect(self._filter_uninstall_pkgs)
        ctrl_bar.addWidget(self.uninstall_search_edit)
        layout.addLayout(ctrl_bar)

        # Scroll Area for Packages
        self.uninstall_scroll = QScrollArea()
        self.uninstall_scroll.setWidgetResizable(True)
        self.uninstall_cards_container = QWidget()
        self.uninstall_cards_layout = QVBoxLayout(self.uninstall_cards_container)
        self.uninstall_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.uninstall_cards_layout.setSpacing(4)
        self.uninstall_scroll.setWidget(self.uninstall_cards_container)
        layout.addWidget(self.uninstall_scroll)

        # Action Button
        self.btn_prepare_uninstall = QPushButton("🗑 PREPARE SAFE UNINSTALL USB")
        self.btn_prepare_uninstall.setProperty("class", "btnDanger")
        self.btn_prepare_uninstall.setFixedHeight(44)
        self.btn_prepare_uninstall.clicked.connect(self._execute_prepare_uninstall_usb)
        layout.addWidget(self.btn_prepare_uninstall)

        self._render_uninstall_cards()
        self._update_uninstall_button()
        return view

    def _render_uninstall_cards(self):
        while self.uninstall_cards_layout.count():
            item = self.uninstall_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        q = self.uninstall_search_query.strip().lower()
        matching = [
            a for a in self.local_apks
            if a["package"] and (not q or (q in a["display_name"].lower() or q in a["package"].lower() or q in a["filename"].lower()))
        ]

        if not matching:
            empty_lbl = QLabel("No packages found.")
            empty_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding: 20px;")
            self.uninstall_cards_layout.addWidget(empty_lbl)
            self.uninstall_cards_layout.addStretch()
            return

        for a in matching:
            pkg = a["package"]
            row = QFrame()
            row.setProperty("class", "card")
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(10, 6, 10, 6)

            chk = QCheckBox(a["display_name"])
            chk.setStyleSheet(f"font-weight: bold; color: {theme.TEXT_PRIMARY};")
            chk.setChecked(self.selected_uninstall_pkgs.get(pkg, False))
            chk.stateChanged.connect(lambda state, p=pkg: self._on_uninstall_chk_changed(p, bool(state)))
            r_layout.addWidget(chk)

            lbl_pkg = QLabel(f"({pkg})")
            lbl_pkg.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
            r_layout.addWidget(lbl_pkg)
            r_layout.addStretch()

            self.uninstall_cards_layout.addWidget(row)

        self.uninstall_cards_layout.addStretch()

    def _on_uninstall_chk_changed(self, pkg: str, state: bool):
        self.selected_uninstall_pkgs[pkg] = state
        self._update_uninstall_button()

    def _set_all_uninstall_pkgs(self, state: bool):
        q = self.uninstall_search_query.strip().lower()
        for a in self.local_apks:
            pkg = a["package"]
            if not pkg: continue
            if not q or (q in a["display_name"].lower() or q in a["package"].lower() or q in a["filename"].lower()):
                self.selected_uninstall_pkgs[pkg] = state
        self._render_uninstall_cards()
        self._update_uninstall_button()

    def _filter_uninstall_pkgs(self, text: str):
        self.uninstall_search_query = text
        self._render_uninstall_cards()

    def _update_uninstall_button(self):
        count = sum(1 for v in self.selected_uninstall_pkgs.values() if v)
        if count > 0:
            self.btn_prepare_uninstall.setText(f"🗑 PREPARE SAFE UNINSTALL USB ({count} APPLICATION{'S' if count > 1 else ''} SELECTED)")
            self.btn_prepare_uninstall.setEnabled(True)
        else:
            self.btn_prepare_uninstall.setText("👆 SELECT AT LEAST ONE APPLICATION TO UNINSTALL")
            self.btn_prepare_uninstall.setEnabled(False)

    def _execute_prepare_uninstall_usb(self):
        if not self._check_usb_ready(): return
        if self.is_busy: return

        selected = [pkg for pkg, state in self.selected_uninstall_pkgs.items() if state]
        if not selected:
            return

        letter = self.current_usb.letter
        pkg_to_name = {a["package"]: a["display_name"] for a in self.local_apks if a.get("package")}
        if len(selected) <= 15:
            apps_list = "\n".join(f"  {i+1}. {pkg_to_name.get(pkg, pkg)} ({pkg})" for i, pkg in enumerate(selected))
        else:
            first_12 = "\n".join(f"  {i+1}. {pkg_to_name.get(pkg, pkg)} ({pkg})" for i, pkg in enumerate(selected[:12]))
            remaining = len(selected) - 12
            apps_list = f"{first_12}\n  ... and {remaining} more packages"

        confirm_msg = (
            f"Are you sure you want to prepare Safe Uninstall USB on drive {letter}?\n\n"
            f"Selected Applications to Remove ({len(selected)}):\n"
            f"{apps_list}\n\n"
            f"When plugged into the vehicle, the payload will safely purge these applications from both User and System partitions."
        )
        if not self.show_confirm_dialog("Confirm Safe Uninstall USB", confirm_msg, confirm_text="🗑 Prepare Uninstall USB", is_danger=True):
            return

        self.execute_payload_worker(
            payload_engine.prepare_uninstall_apps_usb,
            letter,
            selected,
            self.allowed_packages,
            success_title="Safe Uninstall USB Ready",
            success_msg=f"Successfully prepared Safe Uninstall USB on drive {letter}!\n\nSafely unplug and insert into vehicle.",
            error_title="Uninstall Preparation Failed"
        )

    # ---------------------------------------------------------
    # VIEW 3: INSTALL GMS
    # ---------------------------------------------------------
    def _build_view_install_gms(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        lbl_head = QLabel("🌐 GOOGLE PLAY SERVICES (MICROG & PLAY STORE)")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Injects a lightweight, battery-efficient Google Play Services ecosystem into Dongfeng Shine IVI:\n\n"
            "• MicroG GmsCore: Google Account login, Push Notifications (FCM), Maps API.\n"
            "• Google Play Store & Services Framework (GSF).\n"
            "• Voice Recognizer & Speech services for hands-free search.\n\n"
            "Optimized for Android 9/10/11 automotive head units."
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_desc)

        btn_gms = QPushButton("🌐 PREPARE GOOGLE PLAY SERVICES USB")
        btn_gms.setProperty("class", "btnPrimary")
        btn_gms.setFixedHeight(44)
        btn_gms.clicked.connect(self._execute_install_gms)
        c_layout.addWidget(btn_gms)

        layout.addWidget(card)
        layout.addStretch()
        return view

    def _execute_install_gms(self):
        if not self._check_usb_ready(): return
        if self.is_busy: return

        letter = self.current_usb.letter
        confirm_msg = (
            f"Are you sure you want to prepare Google Play Services USB on drive {letter}?\n\n"
            f"This will package MicroG Core, Google Play Store, Services Framework, and voice permissions to inject into your vehicle."
        )
        if not self.show_confirm_dialog("Confirm Google Services Installation", confirm_msg, confirm_text="🌐 Prepare GMS USB"):
            return

        self.execute_payload_worker(
            payload_engine.prepare_install_gms_usb,
            letter,
            GMS_DIR,
            success_title="Google Services USB Ready",
            success_msg=f"Successfully prepared Google Play Services USB on drive {letter}!\n\nSafely unplug and insert into vehicle.",
            error_title="GMS Preparation Failed"
        )

    # ---------------------------------------------------------
    # VIEW 4: UNINSTALL GMS
    # ---------------------------------------------------------
    def _build_view_uninstall_gms(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        lbl_head = QLabel("🗑 REMOVE GOOGLE PLAY SERVICES")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Safely removes all MicroG, Play Store, and Google Services Framework packages from the IVI screen.\n\n"
            "• Does not touch user applications or car settings.\n"
            "• Restores stock factory Google-free state."
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_desc)

        btn_del = QPushButton("🗑 PREPARE GOOGLE SERVICES REMOVAL USB")
        btn_del.setProperty("class", "btnDanger")
        btn_del.setFixedHeight(44)
        btn_del.clicked.connect(self._execute_uninstall_gms)
        c_layout.addWidget(btn_del)

        layout.addWidget(card)
        layout.addStretch()
        return view

    def _execute_uninstall_gms(self):
        if not self._check_usb_ready(): return
        if self.is_busy: return

        letter = self.current_usb.letter
        confirm_msg = (
            f"Are you sure you want to prepare Google Services Removal USB on drive {letter}?\n\n"
            f"This will prepare a script to purge MicroG and Play Store components from your car screen."
        )
        if not self.show_confirm_dialog("Confirm Google Services Removal", confirm_msg, confirm_text="🗑 Prepare Removal USB", is_danger=True):
            return

        self.execute_payload_worker(
            payload_engine.prepare_uninstall_gms_usb,
            letter,
            success_title="GMS Removal USB Ready",
            success_msg=f"Successfully prepared GMS Removal USB on drive {letter}!",
            error_title="Removal Preparation Failed"
        )

    # ---------------------------------------------------------
    # VIEW 5: OPEN ANDROID SETTINGS
    # ---------------------------------------------------------
    def _build_view_open_settings(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        lbl_head = QLabel("⚙ OPEN NATIVE ANDROID SETTINGS")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Unlocks the hidden native Android Settings app on the Dongfeng IVI screen.\n\n"
            "• Access Bluetooth, Wi-Fi, Storage, Developer Options, and Apps Permissions.\n"
            "• Instant one-touch launcher payload."
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_desc)

        btn_settings = QPushButton("⚙ PREPARE OPEN SETTINGS USB")
        btn_settings.setProperty("class", "btnPrimary")
        btn_settings.setFixedHeight(44)
        btn_settings.clicked.connect(self._execute_open_settings)
        c_layout.addWidget(btn_settings)

        layout.addWidget(card)
        layout.addStretch()
        return view

    def _execute_open_settings(self):
        if not self._check_usb_ready(): return
        if self.is_busy: return

        letter = self.current_usb.letter
        confirm_msg = (
            f"Are you sure you want to prepare Open Android Settings USB on drive {letter}?\n\n"
            f"When inserted into the vehicle, this payload immediately launches native Android Settings."
        )
        if not self.show_confirm_dialog("Confirm Settings USB", confirm_msg, confirm_text="⚙ Prepare Settings USB"):
            return

        self.execute_payload_worker(
            payload_engine.prepare_open_settings_usb,
            letter,
            success_title="Settings USB Ready",
            success_msg=f"Successfully prepared Open Android Settings USB on drive {letter}!",
            error_title="Preparation Failed"
        )

    # ---------------------------------------------------------
    # VIEW 6: LAUNCH APPLICATION (OPEN APP SELECT)
    # ---------------------------------------------------------
    def _build_view_open_app(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Search bar
        self.open_app_search_edit = QLineEdit()
        self.open_app_search_edit.setPlaceholderText("🔍 Search application to launch...")
        self.open_app_search_edit.textChanged.connect(self._filter_open_apps)
        layout.addWidget(self.open_app_search_edit)

        # Scroll Area for apps (Single-select radio style)
        self.open_app_scroll = QScrollArea()
        self.open_app_scroll.setWidgetResizable(True)
        self.open_app_container = QWidget()
        self.open_app_layout = QVBoxLayout(self.open_app_container)
        self.open_app_layout.setContentsMargins(0, 0, 0, 0)
        self.open_app_layout.setSpacing(4)
        self.open_app_scroll.setWidget(self.open_app_container)
        layout.addWidget(self.open_app_scroll)

        # Action Button
        self.btn_prepare_open_app = QPushButton("👆 SELECT AN APPLICATION TO LAUNCH")
        self.btn_prepare_open_app.setProperty("class", "btnPrimary")
        self.btn_prepare_open_app.setFixedHeight(44)
        self.btn_prepare_open_app.setEnabled(False)
        self.btn_prepare_open_app.clicked.connect(self._execute_prepare_open_app_usb)
        layout.addWidget(self.btn_prepare_open_app)

        self._render_open_app_cards()
        return view

    def _render_open_app_cards(self):
        while self.open_app_layout.count():
            item = self.open_app_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        q = self.open_app_search_query.strip().lower()
        matching = [
            a for a in self.local_apks
            if a["package"] and (not q or (q in a["display_name"].lower() or q in a["package"].lower() or q in a["filename"].lower()))
        ]

        if not matching:
            empty_lbl = QLabel("No applications found.")
            empty_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding: 20px;")
            self.open_app_layout.addWidget(empty_lbl)
            self.open_app_layout.addStretch()
            return

        for a in matching:
            fname = a["filename"]
            row = QFrame()
            row.setProperty("class", "card")
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(10, 6, 10, 6)

            is_sel = (self.selected_open_app_filename == fname)
            rb = QRadioButton(a["display_name"])
            rb.setStyleSheet(f"font-weight: bold; color: {theme.CYAN_PRIMARY if is_sel else theme.TEXT_PRIMARY};")
            rb.setChecked(is_sel)
            rb.toggled.connect(lambda checked, fn=fname: self._on_open_app_selected(fn, checked))
            r_layout.addWidget(rb)

            lbl_pkg = QLabel(f"({a['package']})")
            lbl_pkg.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
            r_layout.addWidget(lbl_pkg)
            r_layout.addStretch()

            self.open_app_layout.addWidget(row)

        self.open_app_layout.addStretch()

    def _on_open_app_selected(self, fname: str, is_checked: bool):
        if is_checked:
            self.selected_open_app_filename = fname
            app_info = next((a for a in self.local_apks if a["filename"] == fname), None)
            display_name = app_info["display_name"] if app_info else fname
            self.btn_prepare_open_app.setText(f"🚀 PREPARE LAUNCH USB FOR '{display_name}'")
            self.btn_prepare_open_app.setEnabled(True)
        elif self.selected_open_app_filename == fname:
            self.selected_open_app_filename = None
            self.btn_prepare_open_app.setText("👆 SELECT AN APPLICATION TO LAUNCH")
            self.btn_prepare_open_app.setEnabled(False)

    def _filter_open_apps(self, text: str):
        self.open_app_search_query = text
        self._render_open_app_cards()

    def _execute_prepare_open_app_usb(self):
        if not self._check_usb_ready(): return
        if self.is_busy: return

        selected_app_info = next((a for a in self.local_apks if a["filename"] == self.selected_open_app_filename), None)
        if not selected_app_info:
            return

        app_title = selected_app_info["display_name"]
        pkg = selected_app_info["package"]
        letter = self.current_usb.letter

        confirm_msg = (
            f"Are you sure you want to prepare Launch USB on drive {letter}?\n\n"
            f"• Target Application: {app_title}\n"
            f"• Package Name: {pkg}\n\n"
            f"When plugged into the vehicle, this payload brings {app_title} to the foreground immediately."
        )
        if not self.show_confirm_dialog("Confirm Launch Application USB", confirm_msg, confirm_text="🚀 Prepare Launch USB"):
            return

        self.execute_payload_worker(
            payload_engine.prepare_open_app_usb,
            letter,
            package_name=pkg,
            app_name=app_title,
            success_title="Launch USB Ready",
            success_msg=f"Successfully prepared Launch USB for '{app_title}' on drive {letter}!",
            error_title="Launch USB Preparation Failed"
        )

    # ---------------------------------------------------------
    # VIEW 7: DISABLE FACTORY LAUNCHER
    # ---------------------------------------------------------
    def _build_view_disable_launcher(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        lbl_head = QLabel("🔒 DISABLE FACTORY LAUNCHER")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Disables the stock factory home screen (launcher), allowing custom third-party launchers\n"
            "(e.g., Nova Launcher, Car Launcher Pro, Vivid Navigation) to become the primary interface.\n\n"
            "⚠️ IMPORTANT: Make sure at least one custom launcher is installed before disabling the stock launcher!"
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_desc)

        btn_dis = QPushButton("🔒 PREPARE DISABLE FACTORY LAUNCHER USB")
        btn_dis.setProperty("class", "btnDanger")
        btn_dis.setFixedHeight(44)
        btn_dis.clicked.connect(self._execute_disable_launcher)
        c_layout.addWidget(btn_dis)

        layout.addWidget(card)
        layout.addStretch()
        return view

    def _execute_disable_launcher(self):
        if not self._check_usb_ready(): return
        if self.is_busy: return

        letter = self.current_usb.letter
        confirm_msg = (
            f"Are you sure you want to disable the Factory Launcher on drive {letter}?\n\n"
            f"Ensure you have an alternative launcher installed on the car screen."
        )
        if not self.show_confirm_dialog("Confirm Disable Factory Launcher", confirm_msg, confirm_text="🔒 Disable Launcher", is_danger=True):
            return

        self.execute_payload_worker(
            payload_engine.prepare_disable_launcher_usb,
            letter,
            success_title="Disable Launcher USB Ready",
            success_msg=f"Successfully prepared payload on drive {letter}!",
            error_title="Preparation Failed"
        )

    # ---------------------------------------------------------
    # VIEW 8: ENABLE FACTORY LAUNCHER
    # ---------------------------------------------------------
    def _build_view_enable_launcher(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        lbl_head = QLabel("🔓 RESTORE FACTORY LAUNCHER")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Re-enables the original stock factory home screen launcher and restores default Dongfeng IVI behavior."
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_desc)

        btn_en = QPushButton("🔓 PREPARE ENABLE FACTORY LAUNCHER USB")
        btn_en.setProperty("class", "btnPrimary")
        btn_en.setFixedHeight(44)
        btn_en.clicked.connect(self._execute_enable_launcher)
        c_layout.addWidget(btn_en)

        layout.addWidget(card)
        layout.addStretch()
        return view

    def _execute_enable_launcher(self):
        if not self._check_usb_ready(): return
        if self.is_busy: return

        letter = self.current_usb.letter
        confirm_msg = f"Are you sure you want to restore the Factory Launcher on drive {letter}?"
        if not self.show_confirm_dialog("Confirm Enable Factory Launcher", confirm_msg, confirm_text="🔓 Enable Launcher"):
            return

        self.execute_payload_worker(
            payload_engine.prepare_enable_launcher_usb,
            letter,
            success_title="Enable Launcher USB Ready",
            success_msg=f"Successfully prepared payload on drive {letter}!",
            error_title="Preparation Failed"
        )

    # ---------------------------------------------------------
    # VIEW 9: REBOOT INFOTAINMENT SCREEN
    # ---------------------------------------------------------
    def _build_view_reboot_screen(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        lbl_head = QLabel("🔄 RESTART INFOTAINMENT HEAD UNIT")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Performs a clean, graceful software reboot of the Dongfeng IVI screen without requiring vehicle restart."
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_desc)

        btn_rb = QPushButton("🔄 PREPARE REBOOT SCREEN USB")
        btn_rb.setProperty("class", "btnPrimary")
        btn_rb.setFixedHeight(44)
        btn_rb.clicked.connect(self._execute_reboot_screen)
        c_layout.addWidget(btn_rb)

        layout.addWidget(card)
        layout.addStretch()
        return view

    def _execute_reboot_screen(self):
        if not self._check_usb_ready(): return
        if self.is_busy: return

        letter = self.current_usb.letter
        confirm_msg = f"Are you sure you want to prepare Screen Reboot USB on drive {letter}?"
        if not self.show_confirm_dialog("Confirm Restart Screen", confirm_msg, confirm_text="🔄 Prepare Reboot USB"):
            return

        self.execute_payload_worker(
            payload_engine.prepare_reboot_screen_usb,
            letter,
            success_title="Reboot USB Ready",
            success_msg=f"Successfully prepared reboot payload on drive {letter}!",
            error_title="Preparation Failed"
        )

    # ---------------------------------------------------------
    # VIEW 10: BACKUP & SYNC TO PC VAULT
    # ---------------------------------------------------------
    def _build_view_backup(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # Section 1: Prepare Backup USB
        card_prep = QFrame()
        card_prep.setProperty("class", "card")
        cp_layout = QVBoxLayout(card_prep)
        cp_layout.setSpacing(8)

        lbl_head1 = QLabel("💾 PREPARE VEHICLE BACKUP USB")
        lbl_head1.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        cp_layout.addWidget(lbl_head1)

        lbl_desc1 = QLabel("Extracts full vehicle backup: APKs, App Data (/data/data), vehicle calibration configs, and logs.")
        lbl_desc1.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED};")
        cp_layout.addWidget(lbl_desc1)

        btn_backup = QPushButton("💾 PREPARE VEHICLE BACKUP USB")
        btn_backup.setProperty("class", "btnPrimary")
        btn_backup.setFixedHeight(38)
        btn_backup.clicked.connect(self._execute_prepare_backup_usb)
        cp_layout.addWidget(btn_backup)
        layout.addWidget(card_prep)

        # Section 2: Sync to PC Vault
        card_sync = QFrame()
        card_sync.setProperty("class", "card")
        cs_layout = QVBoxLayout(card_sync)
        cs_layout.setSpacing(8)

        lbl_head2 = QLabel("📥 SYNC USB BACKUP TO PC VAULT")
        lbl_head2.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {theme.MINT_SUCCESS};")
        cs_layout.addWidget(lbl_head2)

        lbl_desc2 = QLabel("Safely copies vehicle backup files from your USB flash drive into the permanent PC Vault folder.")
        lbl_desc2.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED};")
        cs_layout.addWidget(lbl_desc2)

        btn_sync = QPushButton("📥 SYNC USB BACKUP TO PC VAULT")
        btn_sync.setProperty("class", "btnSuccess")
        btn_sync.setFixedHeight(38)
        btn_sync.clicked.connect(self._execute_sync_to_pc)
        cs_layout.addWidget(btn_sync)
        layout.addWidget(card_sync)

        layout.addStretch()
        return view

    def _execute_prepare_backup_usb(self):
        if not self._check_usb_ready(): return
        if self.is_busy: return

        letter = self.current_usb.letter
        confirm_msg = (
            f"Are you sure you want to prepare Vehicle Backup USB on drive {letter}?\n\n"
            f"When inserted into the vehicle, this payload safely extracts your applications, configurations, and calibration files."
        )
        if not self.show_confirm_dialog("Confirm Backup USB", confirm_msg, confirm_text="💾 Prepare Backup USB"):
            return

        self.execute_payload_worker(
            payload_engine.prepare_backup_usb,
            letter,
            success_title="Backup USB Ready",
            success_msg=f"Successfully prepared Backup payload on drive {letter}!",
            error_title="Backup Preparation Failed"
        )

    def _execute_sync_to_pc(self):
        if not self._check_usb_ready(): return
        if self.is_busy: return

        letter = self.current_usb.letter
        confirm_msg = f"Sync vehicle backup from USB drive {letter} to PC Vault ({BACKUPS_DIR})?"
        if not self.show_confirm_dialog("Confirm Sync Backup", confirm_msg, confirm_text="📥 Sync to PC"):
            return

        self.execute_payload_worker(
            sync_backup_from_usb_to_pc,
            letter,
            BACKUPS_DIR,
            success_title="Sync Complete",
            success_msg="Successfully synced vehicle backup archive to PC Vault!",
            error_title="Sync Failed"
        )

    # ---------------------------------------------------------
    # VIEW 11: ZERO-TRACE FACTORY RESET
    # ---------------------------------------------------------
    def _build_view_factory_reset(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        lbl_head = QLabel("⚠️ ZERO-TRACE FACTORY RESET (DESTRUCTIVE)")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Wipes all user data, installed apps, caches, and accounts from Dongfeng Shine IVI system.\n\n"
            "• Completely restores stock system partitions.\n"
            "• Zero traces or modified flags left behind.\n"
            "• Ideal before dealership maintenance or warranty inspections."
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_desc)

        btn_reset = QPushButton("⚠️ PREPARE ZERO-TRACE FACTORY RESET USB")
        btn_reset.setProperty("class", "btnDanger")
        btn_reset.setFixedHeight(44)
        btn_reset.clicked.connect(self._execute_factory_reset)
        c_layout.addWidget(btn_reset)

        layout.addWidget(card)
        layout.addStretch()
        return view

    def _execute_factory_reset(self):
        if not self._check_usb_ready(): return
        if self.is_busy: return

        letter = self.current_usb.letter
        confirm_msg = (
            f"CRITICAL WARNING:\n\n"
            f"Are you sure you want to prepare ZERO-TRACE FACTORY RESET USB on drive {letter}?\n\n"
            f"This will wipe all user-installed applications, Google services, accounts, and custom data from the car screen."
        )
        if not self.show_confirm_dialog("Confirm Factory Reset", confirm_msg, confirm_text="⚠️ Prepare Reset USB", is_danger=True):
            return

        self.execute_payload_worker(
            payload_engine.prepare_factory_reset_usb,
            letter,
            local_factory_backup_dir=FACTORY_BACKUP_DIR,
            success_title="Factory Reset USB Ready",
            success_msg=f"Successfully prepared Factory Reset payload on drive {letter}!",
            error_title="Reset Preparation Failed"
        )

    # ---------------------------------------------------------
    # VIEW 12: RESTORE FROM BACKUP
    # ---------------------------------------------------------
    def _build_view_restore(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        lbl_head = QLabel("♻ RESTORE VEHICLE FROM BACKUP")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel("Packages your saved PC Vault vehicle backup archive onto USB to restore your car screen to an exact state.")
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_desc)

        # Dropdown for available PC Vault backups
        self.restore_combo = QComboBox()
        self._populate_restore_combo()
        c_layout.addWidget(self.restore_combo)

        btn_restore = QPushButton("♻ PREPARE RESTORE USB")
        btn_restore.setProperty("class", "btnPrimary")
        btn_restore.setFixedHeight(44)
        btn_restore.clicked.connect(self._execute_restore)
        c_layout.addWidget(btn_restore)

        layout.addWidget(card)
        layout.addStretch()
        return view

    def _populate_restore_combo(self):
        self.restore_combo.clear()
        backups = get_local_backups(BACKUPS_DIR)
        if not backups:
            self.restore_combo.addItem("No saved backups in PC Vault")
            self.restore_combo.setEnabled(False)
        else:
            for b in backups:
                b_name = b.get("folder_name") or b.get("name") or os.path.basename(b["path"])
                b_date = b.get("formatted_datetime") or b.get("date", "Unknown date")
                b_size = b.get("size_str") or f"{b.get('size_mb', 0):.1f} MB"
                self.restore_combo.addItem(f"{b_name} ({b_date}, {b_size})", userData=b["path"])
            self.restore_combo.setEnabled(True)

    def _execute_restore(self):
        if not self._check_usb_ready(): return
        if self.is_busy: return

        backup_path = self.restore_combo.currentData()
        if not backup_path or not os.path.exists(backup_path):
            self.show_error_dialog("No Backup Selected", "Please select a valid backup archive.")
            return

        letter = self.current_usb.letter
        confirm_msg = f"Prepare Restore USB on drive {letter} using backup '{os.path.basename(backup_path)}'?"
        if not self.show_confirm_dialog("Confirm Restore USB", confirm_msg, confirm_text="♻ Prepare Restore USB"):
            return

        self.execute_payload_worker(
            payload_engine.prepare_restore_usb,
            letter,
            local_backup_folder=backup_path,
            success_title="Restore USB Ready",
            success_msg=f"Successfully prepared Restore USB on drive {letter}!",
            error_title="Restore Preparation Failed"
        )

    # ---------------------------------------------------------
    # VIEW 13: FETCH DIAGNOSTIC LOGS
    # ---------------------------------------------------------
    def _build_view_fetch_logs(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        lbl_head = QLabel("📋 FETCH DIAGNOSTIC LOGS & CRASH DUMPS")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Creates a payload that extracts Android logcat, dmesg kernel logs, tombstone crash dumps, and system properties\n"
            "from your car screen onto the USB drive for debugging."
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_desc)

        btn_logs = QPushButton("📋 PREPARE FETCH LOGS USB")
        btn_logs.setProperty("class", "btnPrimary")
        btn_logs.setFixedHeight(44)
        btn_logs.clicked.connect(self._execute_fetch_logs)
        c_layout.addWidget(btn_logs)

        layout.addWidget(card)
        layout.addStretch()
        return view

    def _execute_fetch_logs(self):
        if not self._check_usb_ready(): return
        if self.is_busy: return

        letter = self.current_usb.letter
        confirm_msg = f"Prepare Fetch Logs USB payload on drive {letter}?"
        if not self.show_confirm_dialog("Confirm Fetch Logs", confirm_msg, confirm_text="📋 Prepare Logs USB"):
            return

        self.execute_payload_worker(
            payload_engine.prepare_fetch_logs_usb,
            letter,
            success_title="Logs USB Ready",
            success_msg=f"Successfully prepared Fetch Logs payload on drive {letter}!",
            error_title="Preparation Failed"
        )

    def closeEvent(self, event):
        if hasattr(self, "usb_watcher"):
            self.usb_watcher.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = AeroSuiteQtApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
