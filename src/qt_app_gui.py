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
    QCheckBox, QComboBox, QProgressBar, QPlainTextEdit, QScrollArea,
    QFrame, QMessageBox, QSizePolicy, QSplitter
)

import theme
from qt_theme import get_application_stylesheet
from apk_engine import scan_local_apks
from usb_detector import get_removable_drives, UsbWatcher, UsbDriveInfo
from sync_manager import sync_backup_from_usb_to_pc, get_local_backups
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

            # Accepts (pct, text, speed, current, total, *a, **k) - never raises TypeError!
            def _progress(pct, text="", *a, **k):
                try:
                    pct_val = float(pct)
                    val = int(pct_val * 100) if pct_val <= 1.0 else int(pct_val)
                    val = max(0, min(100, val))
                    self.progress_signal.emit(val, str(text))
                except Exception:
                    pass

            def _cancel_check(*a, **k):
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

        # Load local APK data
        self.local_apks = scan_local_apks(APKS_DIR)
        self.allowed_packages = {a["package"] for a in self.local_apks if a["package"]}

        # Unified per-app install state (all unselected by default)
        self.selected_install_apks = {a["filename"]: False for a in self.local_apks}
        self.per_app_portrait = {a["filename"]: False for a in self.local_apks}
        self.per_app_target = {a["filename"]: "user" for a in self.local_apks}
        self.per_app_boot = {a["filename"]: False for a in self.local_apks}
        self.auto_launch_app_filename = None

        # Uninstall & Open App states
        self.selected_uninstall_pkgs = {a["package"]: False for a in self.local_apks if a["package"]}
        self.selected_open_app_filename = ""  # No default selection!

        # Search queries
        self.install_search_query = ""
        self.uninstall_search_query = ""
        self.open_app_search_query = ""

        # UI Reference maps for in-place updates without flicker
        self.install_cards_map = {}
        self.open_app_row_items = {}

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
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---------------------------------------------------------
        # TOP HEADER: Brand + Interactive USB Selector
        # ---------------------------------------------------------
        header = QWidget()
        header.setObjectName("topBarPanel")
        header.setFixedHeight(65)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)

        # Left: Brand & Title
        brand_box = QHBoxLayout()
        lbl_title = QLabel("⚡ AERO SUITE")
        lbl_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme.CYAN_PRIMARY}; letter-spacing: 1px;")
        brand_box.addWidget(lbl_title)

        lbl_badge = QLabel(f"v{theme.APP_VERSION}")
        lbl_badge.setStyleSheet(
            f"background-color: {theme.CYAN_ALPHA_15}; color: {theme.CYAN_PRIMARY}; "
            f"border: 1px solid {theme.BORDER_CYAN}; border-radius: 6px; padding: 2px 7px; "
            f"font-size: 10px; font-weight: bold;"
        )
        brand_box.addWidget(lbl_badge)

        lbl_sub = QLabel("Dongfeng Shine (Aeolus D53) IVI Studio")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED}; margin-left: 8px;")
        brand_box.addWidget(lbl_sub)
        header_layout.addLayout(brand_box)

        header_layout.addStretch()

        # Right: USB status dot + Interactive dropdown + Refresh
        usb_box = QHBoxLayout()
        self.usb_status_dot = QLabel("●")
        self.usb_status_dot.setStyleSheet(f"color: {theme.CRIMSON_DANGER}; font-size: 16px;")
        usb_box.addWidget(self.usb_status_dot)

        self.usb_combo = QComboBox()
        self.usb_combo.setFixedWidth(300)
        self.usb_combo.currentIndexChanged.connect(self._on_usb_selected)
        usb_box.addWidget(self.usb_combo)

        btn_refresh_usb = QPushButton("🔄 Refresh")
        btn_refresh_usb.setFixedHeight(28)
        btn_refresh_usb.setStyleSheet("font-size: 11px; font-weight: bold; padding: 4px 10px;")
        btn_refresh_usb.clicked.connect(self._refresh_usb_drives)
        usb_box.addWidget(btn_refresh_usb)
        header_layout.addLayout(usb_box)

        main_layout.addWidget(header)

        # ---------------------------------------------------------
        # DEVELOPER BIO & COMMUNITY BAR
        # ---------------------------------------------------------
        dev_bar = QWidget()
        dev_bar.setFixedHeight(30)
        dev_bar.setStyleSheet(f"background-color: {theme.SURFACE_2}; border-bottom: 1px solid {theme.BORDER_SLATE};")
        dev_layout = QHBoxLayout(dev_bar)
        dev_layout.setContentsMargins(20, 2, 20, 2)

        lbl_dev = QLabel(f"👨‍💻 {theme.DEVELOPER_NAME}   |   ✉️ {theme.DEVELOPER_EMAIL}   |   📞 {theme.DEVELOPER_PHONE}")
        lbl_dev.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED};")
        dev_layout.addWidget(lbl_dev)

        dev_layout.addStretch()

        lbl_gift = QLabel(theme.GIFT_COMMUNITY_TEXT)
        lbl_gift.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {theme.MINT_SUCCESS};")
        dev_layout.addWidget(lbl_gift)

        main_layout.addWidget(dev_bar)

        # ---------------------------------------------------------
        # WORKSPACE: SIDEBAR + CONTENT
        # ---------------------------------------------------------
        workspace = QWidget()
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(16, 12, 16, 12)
        workspace_layout.setSpacing(12)

        # Left Sidebar (Feature Matrix)
        sidebar = QWidget()
        sidebar.setObjectName("sidebarPanel")
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 10, 8, 10)
        sidebar_layout.setSpacing(4)

        lbl_side_title = QLabel("SYSTEM FEATURES")
        lbl_side_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme.CYAN_PRIMARY}; padding: 4px 8px;")
        sidebar_layout.addWidget(lbl_side_title)

        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_widget = QWidget()
        self.nav_layout = QVBoxLayout(nav_widget)
        self.nav_layout.setContentsMargins(0, 4, 0, 4)
        self.nav_layout.setSpacing(2)

        # EXACT ORIGINAL FEATURE CATEGORIES & NAMES
        self.feature_categories = [
            ("APPLICATIONS & CONTROL", [
                ("install_apps",      "📦", "Install Apps",             "Deploy APKs from repository"),
                ("uninstall_apps",    "🛡", "Uninstall Apps",           "Safe removal of user apps"),
                ("open_app",          "🚀", "Open App",                 "Launch any installed car app"),
                ("open_settings",     "⚙️", "Open Settings",            "Launch native Android Settings"),
            ]),
            ("GOOGLE PLAY SERVICES", [
                ("install_gms",       "🌐", "Install GMS",              "Deploy Google Framework & Store"),
                ("uninstall_gms",     "🧹", "Uninstall GMS",            "Scrub Google Services & Accounts"),
            ]),
            ("LAUNCHER & POWER", [
                ("disable_launcher",  "🚫", "Disable Launcher",         "Freeze factory stock launcher"),
                ("enable_launcher",   "✅", "Enable Launcher",          "Unfreeze factory stock launcher"),
                ("reboot_screen",     "🔄", "Restart Screen",           "Quick reboot infotainment unit"),
            ]),
            ("BACKUP & MAINTENANCE", [
                ("backup",            "💾", "Backup",                   "Clone car state & auto-sync to PC"),
                ("restore",           "📥", "Restore",                  "Transfer PC backup to car"),
                ("factory_reset",     "⚠️", "Factory Reset",            "Zero-trace restoration to stock"),
                ("fetch_logs",        "📋", "Fetch Logs",               "Dump logcat & crash diagnostics"),
            ])
        ]

        self.feature_buttons = {}
        for cat_title, cat_feats in self.feature_categories:
            lbl_cat = QLabel(cat_title)
            lbl_cat.setProperty("class", "navCategory")
            self.nav_layout.addWidget(lbl_cat)

            for feat_id, feat_icon, feat_title, feat_desc in cat_feats:
                item_btn = QFrame()
                item_btn.setProperty("class", "card")
                item_btn.setFixedHeight(48)
                item_btn.setCursor(Qt.PointingHandCursor)

                ib_layout = QHBoxLayout(item_btn)
                ib_layout.setContentsMargins(10, 4, 10, 4)
                ib_layout.setSpacing(8)

                icon_lbl = QLabel(feat_icon)
                icon_lbl.setFixedWidth(24)
                icon_lbl.setStyleSheet(f"font-size: 15px; color: {theme.CRIMSON_DANGER if feat_id == 'factory_reset' else theme.CYAN_PRIMARY};")
                ib_layout.addWidget(icon_lbl)

                text_box = QVBoxLayout()
                text_box.setSpacing(1)
                t_lbl = QLabel(feat_title)
                t_lbl.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme.CRIMSON_DANGER if feat_id == 'factory_reset' else theme.TEXT_PRIMARY};")
                d_lbl = QLabel(feat_desc)
                d_lbl.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_MUTED};")
                text_box.addWidget(t_lbl)
                text_box.addWidget(d_lbl)
                ib_layout.addLayout(text_box)

                # Mouse click handler
                def _make_click_handler(fid=feat_id):
                    return lambda event: self.switch_view(fid)
                item_btn.mousePressEvent = _make_click_handler()

                self.nav_layout.addWidget(item_btn)
                self.feature_buttons[feat_id] = {
                    "frame": item_btn,
                    "title": t_lbl,
                    "desc": d_lbl
                }

        self.nav_layout.addStretch()
        nav_scroll.setWidget(nav_widget)
        sidebar_layout.addWidget(nav_scroll)
        workspace_layout.addWidget(sidebar)

        # Right Area: Splitter holding Content & Terminal
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.setHandleWidth(1)

        # Content Card Frame
        content_frame = QFrame()
        content_frame.setProperty("class", "card")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.page_stack = QStackedWidget()
        content_layout.addWidget(self.page_stack)
        right_splitter.addWidget(content_frame)

        # Bottom Terminal & Progress Box
        bottom_box = QFrame()
        bottom_box.setProperty("class", "card")
        bottom_box.setFixedHeight(175)
        bottom_layout = QVBoxLayout(bottom_box)
        bottom_layout.setContentsMargins(16, 8, 16, 8)
        bottom_layout.setSpacing(6)

        # Progress bar strip & Controls
        prog_bar = QHBoxLayout()
        self.lbl_status = QLabel("System Idle — Ready for operation.")
        self.lbl_status.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED};")
        prog_bar.addWidget(self.lbl_status)
        prog_bar.addStretch()

        self.btn_cancel_op = QPushButton("⏹ CANCEL")
        self.btn_cancel_op.setProperty("class", "btnDanger")
        self.btn_cancel_op.setFixedHeight(24)
        self.btn_cancel_op.setVisible(False)
        self.btn_cancel_op.clicked.connect(self.cancel_current_operation)
        prog_bar.addWidget(self.btn_cancel_op)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(260)
        self.progress_bar.setValue(0)
        prog_bar.addWidget(self.progress_bar)
        bottom_layout.addLayout(prog_bar)

        # Terminal Console Strip
        term_header = QHBoxLayout()
        lbl_console = QLabel("💻 TERMINAL & SYSTEM LOGS")
        lbl_console.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {theme.TEXT_MUTED};")
        term_header.addWidget(lbl_console)
        term_header.addStretch()

        btn_copy = QPushButton("Copy Logs")
        btn_copy.setFixedHeight(22)
        btn_copy.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        btn_copy.clicked.connect(self._copy_terminal_log)
        term_header.addWidget(btn_copy)

        btn_clear = QPushButton("Clear")
        btn_clear.setFixedHeight(22)
        btn_clear.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        btn_clear.clicked.connect(self._clear_terminal_log)
        term_header.addWidget(btn_clear)
        bottom_layout.addLayout(term_header)

        self.terminal_edit = QPlainTextEdit()
        self.terminal_edit.setObjectName("terminalEdit")
        self.terminal_edit.setReadOnly(True)
        bottom_layout.addWidget(self.terminal_edit)

        right_splitter.addWidget(bottom_box)
        right_splitter.setStretchFactor(0, 4)
        right_splitter.setStretchFactor(1, 1)

        workspace_layout.addWidget(right_splitter)
        main_layout.addWidget(workspace)

        # Initialize View Pages
        self.views = {}
        self._init_views()
        self.switch_view("install_apps")

    # ---------------------------------------------------------
    # VIEW INITIALIZATION & ROUTING
    # ---------------------------------------------------------
    def _init_views(self):
        self._add_view("install_apps", self._build_view_install_apps())
        self._add_view("uninstall_apps", self._build_view_uninstall_apps())
        self._add_view("open_app", self._build_view_open_app())
        self._add_view("open_settings", self._build_view_open_settings())
        self._add_view("install_gms", self._build_view_install_gms())
        self._add_view("uninstall_gms", self._build_view_uninstall_gms())
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

        # Highlight sidebar item
        for fid, item in self.feature_buttons.items():
            fr = item["frame"]
            t = item["title"]
            if fid == feature_id:
                fr.setStyleSheet(f"background-color: {theme.CYAN_ALPHA_15}; border: 1px solid {theme.CYAN_PRIMARY}; border-radius: 8px;")
                t.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
            else:
                fr.setStyleSheet(f"background-color: transparent; border: 1px solid transparent; border-radius: 8px;")
                t.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme.CRIMSON_DANGER if fid == 'factory_reset' else theme.TEXT_PRIMARY};")

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
            self.usb_combo.addItem("NO USB FLASH DETECTED")
            self.usb_status_dot.setStyleSheet(f"color: {theme.CRIMSON_DANGER}; font-size: 16px;")
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
            self.usb_status_dot.setStyleSheet(f"color: {theme.MINT_SUCCESS}; font-size: 16px;")

        self.usb_combo.blockSignals(False)

    def _on_usb_selected(self, index: int):
        drive = self.usb_combo.currentData()
        if drive and isinstance(drive, UsbDriveInfo):
            self.current_usb = drive
            self.usb_status_dot.setStyleSheet(f"color: {theme.MINT_SUCCESS}; font-size: 16px;")

    _on_user_selected_drive = _on_usb_selected

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
            self.lbl_status.setText("System Idle — Ready for operation.")
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

        worker.progress_signal.connect(lambda val, txt: (self.progress_bar.setValue(val), self.lbl_status.setText(txt)))
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
    # DIALOG HELPERS (MODAL CENTERED MESSAGE BOXES)
    # ---------------------------------------------------------
    def show_confirm_dialog(self, title: str, message: str, confirm_text: str = "Proceed", is_danger: bool = False) -> bool:
        msg_box = QMessageBox(self)
        msg_box.setWindowModality(Qt.WindowModal)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Warning if is_danger else QMessageBox.Question)
        btn_yes = msg_box.addButton(confirm_text, QMessageBox.YesRole)
        btn_no = msg_box.addButton("Cancel", QMessageBox.NoRole)
        if is_danger:
            btn_yes.setStyleSheet(f"background-color: {theme.CRIMSON_DANGER}; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        else:
            btn_yes.setStyleSheet(f"background-color: {theme.CYAN_PRIMARY}; color: black; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        btn_no.setStyleSheet(f"background-color: {theme.SURFACE_3}; color: {theme.TEXT_PRIMARY}; padding: 6px 14px; border-radius: 4px;")
        msg_box.exec()
        return msg_box.clickedButton() == btn_yes

    def show_success_dialog(self, title: str, message: str):
        QMessageBox.information(self, title, message)

    def show_error_dialog(self, title: str, message: str):
        QMessageBox.critical(self, title, message)

    # ---------------------------------------------------------
    # VIEW 1: INSTALL APPS (UNIFIED BUTTON BEHAVIOR)
    # ---------------------------------------------------------
    def _build_view_install_apps(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Header Title
        title_box = QHBoxLayout()
        lbl_vtitle = QLabel("📦 INSTALL APPLICATIONS")
        lbl_vtitle.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        title_box.addWidget(lbl_vtitle)

        self.install_count_label = QLabel(f"({len(self.local_apks)} APKs available in repository)")
        self.install_count_label.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED};")
        title_box.addWidget(self.install_count_label)
        title_box.addStretch()
        layout.addLayout(title_box)

        # Controls & Search Strip
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

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self._rescan_apks)
        ctrl_bar.addWidget(btn_refresh)

        ctrl_bar.addSpacing(10)
        self.install_search_edit = QLineEdit()
        self.install_search_edit.setPlaceholderText("🔍 Search APKs (name, package, file)...")
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
        self.btn_prepare_install = QPushButton("👆 SELECT AT LEAST ONE APPLICATION TO INSTALL")
        self.btn_prepare_install.setProperty("class", "btnPrimary")
        self.btn_prepare_install.setFixedHeight(44)
        self.btn_prepare_install.setEnabled(False)
        self.btn_prepare_install.clicked.connect(self._execute_prepare_install_usb)
        layout.addWidget(self.btn_prepare_install)

        self._render_install_cards()
        self._update_install_button()
        return view

    def _render_install_cards(self):
        while self.install_cards_layout.count():
            item = self.install_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.install_cards_map = {}
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

        for a in matching:
            fname = a["filename"]
            card = QFrame()
            card.setProperty("class", "card")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(12, 8, 12, 8)
            c_layout.setSpacing(6)

            # Top Row: Checkbox + Meta + Target
            top_row = QHBoxLayout()
            chk_install = QCheckBox(f"{a['display_name']}")
            chk_install.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {theme.TEXT_PRIMARY};")
            chk_install.setChecked(self.selected_install_apks.get(fname, False))
            chk_install.stateChanged.connect(lambda state, fn=fname: self._on_install_chk_changed(fn, bool(state)))
            top_row.addWidget(chk_install)

            lbl_meta = QLabel(f"({a['package']}) • {a['size_mb']} MB")
            lbl_meta.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED};")
            top_row.addWidget(lbl_meta)
            top_row.addStretch()

            combo_target = QComboBox()
            combo_target.addItems(["User (/data)", "System (/system)"])
            combo_target.setCurrentIndex(0 if self.per_app_target.get(fname, "user") == "user" else 1)
            combo_target.currentIndexChanged.connect(lambda idx, fn=fname: self.per_app_target.update({fn: "user" if idx == 0 else "system"}))
            top_row.addWidget(combo_target)
            c_layout.addLayout(top_row)

            # Bottom Row: 3 Feature Toggles (UNIFIED BEHAVIOR - Unchecked by default, never forces install selection)
            bot_row = QHBoxLayout()
            chk_port = QCheckBox("Force Portrait")
            chk_port.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_PRIMARY};")
            chk_port.setChecked(self.per_app_portrait.get(fname, False))
            chk_port.stateChanged.connect(lambda state, fn=fname: self.per_app_portrait.update({fn: bool(state)}))
            bot_row.addWidget(chk_port)
            bot_row.addSpacing(16)

            chk_boot = QCheckBox("Block Boot Launch")
            chk_boot.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_PRIMARY};")
            chk_boot.setChecked(self.per_app_boot.get(fname, False))
            chk_boot.stateChanged.connect(lambda state, fn=fname: self.per_app_boot.update({fn: bool(state)}))
            bot_row.addWidget(chk_boot)
            bot_row.addSpacing(16)

            chk_auto = QCheckBox("Auto Launch")
            is_auto = (self.auto_launch_app_filename == fname)
            chk_auto.setStyleSheet(f"font-size: 11px; font-weight: {'bold' if is_auto else 'normal'}; color: {theme.MINT_SUCCESS if is_auto else theme.TEXT_PRIMARY};")
            chk_auto.setChecked(is_auto)
            chk_auto.stateChanged.connect(lambda state, fn=fname: self._on_auto_launch_toggle(fn, bool(state)))
            bot_row.addWidget(chk_auto)
            bot_row.addStretch()
            c_layout.addLayout(bot_row)

            self.install_cards_map[fname] = {
                "chk_install": chk_install,
                "chk_auto": chk_auto,
            }
            self.install_cards_layout.addWidget(card)

        self.install_cards_layout.addStretch()

    def _on_install_chk_changed(self, fname: str, is_checked: bool):
        self.selected_install_apks[fname] = is_checked
        # If user unselects an app that had auto launch, clear auto launch
        if not is_checked and self.auto_launch_app_filename == fname:
            self.auto_launch_app_filename = None
            if fname in self.install_cards_map:
                chk_a = self.install_cards_map[fname]["chk_auto"]
                chk_a.blockSignals(True)
                chk_a.setChecked(False)
                chk_a.setStyleSheet(f"font-size: 11px; font-weight: normal; color: {theme.TEXT_PRIMARY};")
                chk_a.blockSignals(False)
        self._update_install_button()

    def _on_auto_launch_toggle(self, fname: str, is_checked: bool):
        # UNIFIED BEHAVIOR: Toggling auto-launch does NOT change whether the app is selected for install!
        if is_checked:
            self.auto_launch_app_filename = fname
            # Update all cards in-place without rebuilding or flicker!
            for fn, item in self.install_cards_map.items():
                chk = item["chk_auto"]
                chk.blockSignals(True)
                if fn == fname:
                    chk.setChecked(True)
                    chk.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {theme.MINT_SUCCESS};")
                else:
                    chk.setChecked(False)
                    chk.setStyleSheet(f"font-size: 11px; font-weight: normal; color: {theme.TEXT_PRIMARY};")
                chk.blockSignals(False)
        else:
            if self.auto_launch_app_filename == fname:
                self.auto_launch_app_filename = None
            if fname in self.install_cards_map:
                chk = self.install_cards_map[fname]["chk_auto"]
                chk.blockSignals(True)
                chk.setChecked(False)
                chk.setStyleSheet(f"font-size: 11px; font-weight: normal; color: {theme.TEXT_PRIMARY};")
                chk.blockSignals(False)

    _on_auto_launch_changed = _on_auto_launch_toggle

    def _set_all_install_apks(self, state: bool):
        q = self.install_search_query.strip().lower()
        for a in self.local_apks:
            fname = a["filename"]
            if not q or (q in a["display_name"].lower() or q in a["package"].lower() or q in fname.lower()):
                self.selected_install_apks[fname] = state
                if not state and self.auto_launch_app_filename == fname:
                    self.auto_launch_app_filename = None
                if fname in self.install_cards_map:
                    chk_i = self.install_cards_map[fname]["chk_install"]
                    chk_i.blockSignals(True)
                    chk_i.setChecked(state)
                    chk_i.blockSignals(False)
                    if not state:
                        chk_a = self.install_cards_map[fname]["chk_auto"]
                        chk_a.blockSignals(True)
                        chk_a.setChecked(False)
                        chk_a.setStyleSheet(f"font-size: 11px; font-weight: normal; color: {theme.TEXT_PRIMARY};")
                        chk_a.blockSignals(False)
        self._update_install_button()

    def _invert_install_selection(self):
        q = self.install_search_query.strip().lower()
        for a in self.local_apks:
            fname = a["filename"]
            if not q or (q in a["display_name"].lower() or q in a["package"].lower() or q in fname.lower()):
                new_state = not self.selected_install_apks.get(fname, False)
                self.selected_install_apks[fname] = new_state
                if not new_state and self.auto_launch_app_filename == fname:
                    self.auto_launch_app_filename = None
                if fname in self.install_cards_map:
                    chk_i = self.install_cards_map[fname]["chk_install"]
                    chk_i.blockSignals(True)
                    chk_i.setChecked(new_state)
                    chk_i.blockSignals(False)
                    if not new_state:
                        chk_a = self.install_cards_map[fname]["chk_auto"]
                        chk_a.blockSignals(True)
                        chk_a.setChecked(False)
                        chk_a.setStyleSheet(f"font-size: 11px; font-weight: normal; color: {theme.TEXT_PRIMARY};")
                        chk_a.blockSignals(False)
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
        self.install_count_label.setText(f"({len(self.local_apks)} APKs available in repository)")
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

        auto_launch_pkg = ""
        if self.auto_launch_app_filename:
            target_a = next((a for a in selected if a["filename"] == self.auto_launch_app_filename), None)
            if target_a and target_a.get("package"):
                auto_launch_pkg = target_a["package"]
                self.log_terminal(f"Auto Launch target set: {target_a['display_name']} ({auto_launch_pkg})", "mint")
            else:
                self.log_terminal(f"Note: Auto Launch app '{self.auto_launch_app_filename}' was not selected for installation; Auto Launch will be skipped.", "warn")

        auto_info = f"\n\n🚀 Auto-Launch App: {self.auto_launch_app_filename}" if auto_launch_pkg else ""
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
    # VIEW 2: SAFE UNINSTALL APPS
    # ---------------------------------------------------------
    def _build_view_uninstall_apps(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Header Title
        lbl_vtitle = QLabel("🛡 SAFE UNINSTALL APPS")
        lbl_vtitle.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme.AMBER_WARN};")
        layout.addWidget(lbl_vtitle)

        # Safety Banner
        banner = QFrame()
        banner.setProperty("class", "card")
        b_layout = QVBoxLayout(banner)
        lbl_banner = QLabel("🔒 STRICT SAFETY LOCK: Only apps originating from your vetted apks/ repository can be uninstalled.\nSearches and purges from BOTH User Apps (/data/app) and System Apps (/system/priv-app & /system/app).")
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

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self._rescan_apks)
        ctrl_bar.addWidget(btn_refresh)

        ctrl_bar.addSpacing(10)
        self.uninstall_search_edit = QLineEdit()
        self.uninstall_search_edit.setPlaceholderText("🔍 Search Packages to Uninstall (contains name, package)...")
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
        self.btn_prepare_uninstall = QPushButton("👆 SELECT AT LEAST ONE APPLICATION TO UNINSTALL")
        self.btn_prepare_uninstall.setProperty("class", "btnDanger")
        self.btn_prepare_uninstall.setFixedHeight(44)
        self.btn_prepare_uninstall.setEnabled(False)
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
            row.setFixedHeight(36)
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(10, 4, 10, 4)

            chk = QCheckBox(a["display_name"])
            chk.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {theme.TEXT_PRIMARY};")
            chk.setChecked(self.selected_uninstall_pkgs.get(pkg, False))
            chk.stateChanged.connect(lambda state, p=pkg: self._on_uninstall_chk_changed(p, bool(state)))
            r_layout.addWidget(chk)

            lbl_pkg = QLabel(f"({pkg})")
            lbl_pkg.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 10px; font-family: Consolas;")
            r_layout.addWidget(lbl_pkg)
            r_layout.addStretch()

            lbl_size = QLabel(f"{a['size_mb']} MB")
            lbl_size.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 10px; font-family: Consolas; font-weight: bold;")
            r_layout.addWidget(lbl_size)

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
    # VIEW 3: OPEN APP (EXACT LOOK & BEHAVIOR: SINGLE-SELECT ONLY)
    # ---------------------------------------------------------
    def _build_view_open_app(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Header Title
        lbl_vtitle = QLabel("🚀 LAUNCH APPLICATION ON CAR")
        lbl_vtitle.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        layout.addWidget(lbl_vtitle)

        # Instruction Banner
        banner = QFrame()
        banner.setProperty("class", "card")
        b_layout = QVBoxLayout(banner)
        lbl_banner = QLabel("💡 Select an application below to generate an auto-launch USB payload.\nWhen plugged into the vehicle, the script brings the chosen application to the foreground immediately.")
        lbl_banner.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED};")
        b_layout.addWidget(lbl_banner)
        layout.addWidget(banner)

        # Controls & Search Strip
        ctrl_bar = QHBoxLayout()
        self.open_app_search_edit = QLineEdit()
        self.open_app_search_edit.setPlaceholderText("🔍 Search Apps to Open (name or package)...")
        self.open_app_search_edit.textChanged.connect(self._filter_open_apps)
        ctrl_bar.addWidget(self.open_app_search_edit)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self._rescan_apks)
        ctrl_bar.addWidget(btn_refresh)
        layout.addLayout(ctrl_bar)

        # Scroll Area for apps (Appears EXACTLY like uninstall list)
        self.open_app_scroll = QScrollArea()
        self.open_app_scroll.setWidgetResizable(True)
        self.open_app_container = QWidget()
        self.open_app_layout = QVBoxLayout(self.open_app_container)
        self.open_app_layout.setContentsMargins(0, 0, 0, 0)
        self.open_app_layout.setSpacing(4)
        self.open_app_scroll.setWidget(self.open_app_container)
        layout.addWidget(self.open_app_scroll)

        # Action Button (Disabled by default when no app is selected)
        self.btn_open_app_launch = QPushButton("👆 SELECT AN APP FROM THE LIST ABOVE TO PREPARE LAUNCH USB")
        self.btn_open_app_launch.setProperty("class", "btnPrimary")
        self.btn_open_app_launch.setFixedHeight(44)
        self.btn_open_app_launch.setEnabled(False)
        self.btn_open_app_launch.clicked.connect(self._execute_prepare_open_app_usb)
        self.btn_prepare_open_app = self.btn_open_app_launch
        layout.addWidget(self.btn_open_app_launch)

        self._render_open_app_rows()
        return view

    def _render_open_app_rows(self):
        while self.open_app_layout.count():
            item = self.open_app_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.open_app_row_items = {}
        q = self.open_app_search_query.strip().lower()
        matching = [
            a for a in self.local_apks
            if a.get("package") and (not q or q in a["display_name"].lower() or q in a["package"].lower() or q in a["filename"].lower())
        ]

        if not matching:
            empty_lbl = QLabel("No matching applications found.")
            empty_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding: 20px;")
            self.open_app_layout.addWidget(empty_lbl)
            self.open_app_layout.addStretch()
            return

        for a in matching:
            fname = a["filename"]
            pkg = a["package"]
            is_selected = (self.selected_open_app_filename == fname and self.selected_open_app_filename != "")

            row = QFrame()
            row.setProperty("class", "card")
            row.setFixedHeight(36)
            row.setCursor(Qt.PointingHandCursor)
            if is_selected:
                row.setStyleSheet(f"background-color: {theme.CYAN_ALPHA_15}; border: 1px solid {theme.CYAN_PRIMARY}; border-radius: 8px;")
            else:
                row.setStyleSheet(f"background-color: {theme.SURFACE_2}; border: 1px solid {theme.BORDER_SLATE}; border-radius: 8px;")

            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(10, 4, 10, 4)

            chk = QCheckBox(a["display_name"])
            chk.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {theme.CYAN_PRIMARY if is_selected else theme.TEXT_PRIMARY};")
            chk.setChecked(is_selected)
            chk.clicked.connect(lambda checked, fn=fname: self._on_open_app_item_clicked(fn))
            r_layout.addWidget(chk)

            lbl_pkg = QLabel(f"({pkg})")
            lbl_pkg.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 10px; font-family: Consolas;")
            r_layout.addWidget(lbl_pkg)
            r_layout.addStretch()

            lbl_size = QLabel(f"{a['size_mb']} MB")
            lbl_size.setStyleSheet(f"color: {theme.CYAN_PRIMARY if is_selected else theme.TEXT_MUTED}; font-size: 10px; font-family: Consolas; font-weight: bold;")
            r_layout.addWidget(lbl_size)

            def _make_row_click(fn=fname):
                return lambda event: self._on_open_app_item_clicked(fn)
            row.mousePressEvent = _make_row_click(fname)

            self.open_app_row_items[fname] = {
                "row": row,
                "chk": chk,
                "lbl_size": lbl_size
            }
            self.open_app_layout.addWidget(row)

        self.open_app_layout.addStretch()

    def _sync_open_app_rows(self):
        # Mutate row items in-place without rebuilding!
        for fn, item in self.open_app_row_items.items():
            is_cur = (fn == self.selected_open_app_filename and bool(self.selected_open_app_filename))
            row = item["row"]
            chk = item["chk"]
            lbl_size = item["lbl_size"]

            chk.blockSignals(True)
            chk.setChecked(is_cur)
            chk.blockSignals(False)

            if is_cur:
                row.setStyleSheet(f"background-color: {theme.CYAN_ALPHA_15}; border: 1px solid {theme.CYAN_PRIMARY}; border-radius: 8px;")
                chk.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {theme.CYAN_PRIMARY};")
                lbl_size.setStyleSheet(f"color: {theme.CYAN_PRIMARY}; font-size: 10px; font-family: Consolas; font-weight: bold;")
            else:
                row.setStyleSheet(f"background-color: {theme.SURFACE_2}; border: 1px solid {theme.BORDER_SLATE}; border-radius: 8px;")
                chk.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {theme.TEXT_PRIMARY};")
                lbl_size.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 10px; font-family: Consolas; font-weight: bold;")

        self._update_open_app_launch_button()

    def _on_open_app_item_clicked(self, clicked_filename: str):
        # Strict single-selection toggle keyed by unique filename:
        # If user clicks the currently selected app, deselect it. Otherwise select it and deselect all others.
        if self.selected_open_app_filename == clicked_filename:
            self.selected_open_app_filename = ""
        else:
            self.selected_open_app_filename = clicked_filename
        self._sync_open_app_rows()

    def _on_open_app_selected(self, filename: str, checked: bool = True):
        if checked:
            self.selected_open_app_filename = filename
        elif self.selected_open_app_filename == filename:
            self.selected_open_app_filename = ""
        self._sync_open_app_rows()

    def _update_open_app_launch_button(self):
        if self.selected_open_app_filename:
            selected_app_info = next((a for a in self.local_apks if a["filename"] == self.selected_open_app_filename), None)
            selected_title = selected_app_info["display_name"] if selected_app_info else self.selected_open_app_filename
            display_title = selected_title if len(selected_title) <= 30 else (selected_title[:27] + "...")
            self.btn_open_app_launch.setText(f"🚀 PREPARE LAUNCH USB FOR: {display_title.upper()}")
            self.btn_open_app_launch.setEnabled(True)
        else:
            self.btn_open_app_launch.setText("👆 SELECT AN APP FROM THE LIST ABOVE TO PREPARE LAUNCH USB")
            self.btn_open_app_launch.setEnabled(False)

    def _filter_open_apps(self, text: str):
        self.open_app_search_query = text
        self._render_open_app_rows()

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
    # VIEW 4: OPEN SETTINGS
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

        lbl_head = QLabel("⚙️ OPEN NATIVE ANDROID SETTINGS")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Unlocks the hidden native Android Settings app on the Dongfeng IVI screen.\n\n"
            "• Access Bluetooth, Wi-Fi, Storage, Developer Options, and Apps Permissions.\n"
            "• Instant one-touch launcher payload."
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_desc)

        btn_settings = QPushButton("⚙️ PREPARE OPEN SETTINGS USB")
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
        if not self.show_confirm_dialog("Confirm Settings USB", confirm_msg, confirm_text="⚙️ Prepare Settings USB"):
            return

        self.execute_payload_worker(
            payload_engine.prepare_open_settings_usb,
            letter,
            success_title="Settings USB Ready",
            success_msg=f"Successfully prepared Open Android Settings USB on drive {letter}!",
            error_title="Preparation Failed"
        )

    # ---------------------------------------------------------
    # VIEW 5: INSTALL GMS
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

        lbl_head = QLabel("🌐 GOOGLE PLAY SERVICES SETUP")
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
    # VIEW 6: UNINSTALL GMS
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

        lbl_head = QLabel("🧹 REMOVE GOOGLE PLAY SERVICES")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Safely removes all MicroG, Play Store, and Google Services Framework packages from the IVI screen.\n\n"
            "• Does not touch user applications or car settings.\n"
            "• Restores stock factory Google-free state."
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_desc)

        btn_del = QPushButton("🧹 PREPARE GOOGLE SERVICES REMOVAL USB")
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
        if not self.show_confirm_dialog("Confirm Google Services Removal", confirm_msg, confirm_text="🧹 Prepare Removal USB", is_danger=True):
            return

        self.execute_payload_worker(
            payload_engine.prepare_uninstall_gms_usb,
            letter,
            success_title="GMS Removal USB Ready",
            success_msg=f"Successfully prepared GMS Removal USB on drive {letter}!",
            error_title="Removal Preparation Failed"
        )

    # ---------------------------------------------------------
    # VIEW 7: DISABLE LAUNCHER
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

        lbl_head = QLabel("🚫 DISABLE FACTORY LAUNCHER")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Disables the stock factory home screen (launcher), allowing custom third-party launchers\n"
            "(e.g., Nova Launcher, Car Launcher Pro, Vivid Navigation) to become the primary interface.\n\n"
            "⚠️ IMPORTANT: Make sure at least one custom launcher is installed before disabling the stock launcher!"
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_desc)

        btn_dis = QPushButton("🚫 PREPARE DISABLE FACTORY LAUNCHER USB")
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
        if not self.show_confirm_dialog("Confirm Disable Factory Launcher", confirm_msg, confirm_text="🚫 Disable Launcher", is_danger=True):
            return

        self.execute_payload_worker(
            payload_engine.prepare_disable_launcher_usb,
            letter,
            success_title="Disable Launcher USB Ready",
            success_msg=f"Successfully prepared payload on drive {letter}!",
            error_title="Preparation Failed"
        )

    # ---------------------------------------------------------
    # VIEW 8: ENABLE LAUNCHER
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

        lbl_head = QLabel("✅ ENABLE FACTORY LAUNCHER")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Re-enables the original stock factory home screen launcher and restores default Dongfeng IVI behavior."
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_desc)

        btn_en = QPushButton("✅ PREPARE ENABLE FACTORY LAUNCHER USB")
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
        if not self.show_confirm_dialog("Confirm Enable Factory Launcher", confirm_msg, confirm_text="✅ Enable Launcher"):
            return

        self.execute_payload_worker(
            payload_engine.prepare_enable_launcher_usb,
            letter,
            success_title="Enable Launcher USB Ready",
            success_msg=f"Successfully prepared payload on drive {letter}!",
            error_title="Preparation Failed"
        )

    # ---------------------------------------------------------
    # VIEW 9: RESTART SCREEN
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

        lbl_head = QLabel("🔄 RESTART INFOTAINMENT SCREEN")
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

        lbl_head1 = QLabel("💾 SYSTEM & DATA BACKUP")
        lbl_head1.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
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
        lbl_head2.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.MINT_SUCCESS};")
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
            backup_type="personal",
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
    # VIEW 11: RESTORE FROM BACKUP
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

        lbl_head = QLabel("📥 RESTORE VEHICLE FROM BACKUP")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel("Packages your saved PC Vault vehicle backup archive onto USB to restore your car screen to an exact state.")
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY};")
        c_layout.addWidget(lbl_desc)

        self.restore_combo = QComboBox()
        self._populate_restore_combo()
        c_layout.addWidget(self.restore_combo)

        btn_restore = QPushButton("📥 PREPARE RESTORE USB")
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
        if not self.show_confirm_dialog("Confirm Restore USB", confirm_msg, confirm_text="📥 Prepare Restore USB"):
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
    # VIEW 12: ZERO-TRACE FACTORY RESET
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

        lbl_head = QLabel("⚠️ ZERO-TRACE FACTORY RESET")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Completely restores the head unit to factory state before dealership inspection:\n"
            "• Preserves all 69 factory priv-apps + 33 apps and re-enables stock launcher\n"
            "• Deep Bluetooth hardware chip wipe (AT#BX & NVRAM clear)\n"
            "• Wipes all user APKs, accounts, databases, Wi-Fi networks, and storage\n"
            "• Deep telemetry wipe: Purges all crash tombstones, ANR traces, DropBox & system logs\n"
            "• Locks system Read-Only and triggers automatic reboot to pristine factory state."
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

        lbl_head = QLabel("📋 FETCH DIAGNOSTIC LOGS")
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
