"""
qt_app_gui.py — Aero Suite Automotive Infotainment Management Console (PySide6 Edition).
Calibrated for Dongfeng Shine (Aeolus D53) IVI System.
Engineered by Abdelrhman Hamdy - Senior Software Engineer.
"""
import os
import sys
import threading
import time

from PySide6.QtCore import Qt, QThread, Signal, Slot, QObject, QTimer, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QFont, QColor, QTextCursor, QAction, QCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QStackedWidget, QLabel, QPushButton, QLineEdit,
    QCheckBox, QComboBox, QProgressBar, QPlainTextEdit, QScrollArea,
    QFrame, QMessageBox, QSizePolicy, QSplitter, QMenu
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

            import inspect
            sig = inspect.signature(self.target_func)
            accepted = sig.parameters
            has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in accepted.values())
            call_kwargs = dict(self.kwargs)
            if "log_func" in accepted or has_var_kw:
                call_kwargs["log_func"] = _log
            if "progress_func" in accepted or has_var_kw:
                call_kwargs["progress_func"] = _progress
            if "progress_callback" in accepted or has_var_kw:
                call_kwargs["progress_callback"] = lambda pct, cur_f="", spd=0.0, c_mb=0.0, t_mb=0.0, *a, **k: _progress(pct, cur_f, spd, c_mb, t_mb)
            if "cancel_check" in accepted or has_var_kw:
                call_kwargs["cancel_check"] = _cancel_check

            ok = self.target_func(*self.args, **call_kwargs)
            if self.cancel_event.is_set():
                self.finished_signal.emit(False, "cancelled")
            elif not ok:
                self.finished_signal.emit(False, "aborted")
            else:
                self.finished_signal.emit(True, "")
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
        self.uninstall_cards_map = {}
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
        lbl_badge.setFixedHeight(26)
        lbl_badge.setAlignment(Qt.AlignCenter)
        lbl_badge.setStyleSheet(
            f"background-color: {theme.CYAN_ALPHA_15}; color: {theme.CYAN_PRIMARY}; "
            f"border: 1px solid {theme.BORDER_CYAN}; border-radius: 6px; padding: 0 10px; "
            f"font-size: 11px; font-weight: bold;"
        )
        brand_box.addWidget(lbl_badge)

        lbl_sub = QLabel("Dongfeng Shine (Aeolus D53) IVI Studio")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED}; margin-left: 8px;")
        brand_box.addWidget(lbl_sub)
        header_layout.addLayout(brand_box)

        header_layout.addStretch()

        # Right: USB status dot + Interactive dropdown + Refresh + Tools
        usb_box = QHBoxLayout()
        usb_box.setSpacing(8)

        self.usb_status_dot = QLabel("●")
        self.usb_status_dot.setObjectName("usbStatusDot")
        self.usb_status_dot.setStyleSheet(f"color: {theme.CRIMSON_DANGER}; font-size: 16px;")
        self.usb_status_dot.setToolTip("No USB Flash Drive Detected")
        usb_box.addWidget(self.usb_status_dot)

        self.usb_combo = QComboBox()
        self.usb_combo.setObjectName("usbCombo")
        self.usb_combo.setFixedWidth(300)
        self.usb_combo.setFixedHeight(28)
        self.usb_combo.setCursor(Qt.PointingHandCursor)
        self.usb_combo.setContextMenuPolicy(Qt.CustomContextMenu)
        self.usb_combo.customContextMenuRequested.connect(self._show_usb_menu)
        self.usb_combo.currentIndexChanged.connect(self._on_usb_selected)
        usb_box.addWidget(self.usb_combo)

        self.btn_refresh_usb = QPushButton("🔄 Refresh")
        self.btn_refresh_usb.setObjectName("btnRefreshUsb")
        self.btn_refresh_usb.setFixedHeight(28)
        self.btn_refresh_usb.setFixedWidth(115)
        self.btn_refresh_usb.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_usb.setToolTip("Refresh & Rescan USB Flash Drives")
        self.btn_refresh_usb.clicked.connect(self._refresh_usb_drives)
        usb_box.addWidget(self.btn_refresh_usb)

        self.btn_usb_settings = QPushButton("⚙️")
        self.btn_usb_settings.setObjectName("btnUsbSettings")
        self.btn_usb_settings.setFixedSize(28, 28)
        self.btn_usb_settings.setCursor(Qt.PointingHandCursor)
        self.btn_usb_settings.setToolTip("Flash Drive Settings & Tools (Open in Explorer, Format FAT32, Rescan)")
        self.btn_usb_settings.clicked.connect(lambda: self._show_usb_menu(button_anchor=True))
        usb_box.addWidget(self.btn_usb_settings)

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
                ("install_apps",      "📦", "Install Apps",             "Install favorite apps with 1 click"),
                ("uninstall_apps",    "🛡", "Uninstall Apps",           "Clean apps & free up storage"),
                ("open_app",          "🚀", "Open App",                 "Launch hidden or installed apps"),
                ("open_settings",     "⚙️", "Open Settings",            "Unlock full Android Settings"),
            ]),
            ("GOOGLE PLAY SERVICES", [
                ("install_gms",       "🌐", "Install GMS",              "Get Google Play Store & Maps"),
                ("uninstall_gms",     "🧹", "Uninstall GMS",            "Remove Google & boost speed"),
            ]),
            ("LAUNCHER & POWER", [
                ("disable_launcher",  "🚫", "Disable Launcher",         "Switch to custom dashboard"),
                ("enable_launcher",   "✅", "Enable Launcher",          "Restore original dashboard"),
                ("reboot_screen",     "🔄", "Restart Screen",           "Quick safe screen restart"),
            ]),
            ("BACKUP & MAINTENANCE", [
                ("backup",            "💾", "Backup",                   "Save full car backup to PC"),
                ("restore",           "📥", "Restore",                  "Restore saved apps & settings"),
                ("factory_reset",     "⚠️", "Factory Reset",            "100% clean dealership reset"),
                ("fetch_logs",        "📋", "Fetch Logs",               "Get diagnostic error logs"),
            ])
        ]

        self.feature_buttons = {}
        for i, (cat_title, cat_feats) in enumerate(self.feature_categories):
            if i > 0:
                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                sep.setFixedHeight(1)
                sep.setStyleSheet(f"background-color: {theme.BORDER_SLATE}; border: none; margin: 4px 8px;")
                self.nav_layout.addWidget(sep)
            lbl_cat = QLabel(cat_title)
            lbl_cat.setProperty("class", "navCategory")
            self.nav_layout.addWidget(lbl_cat)

            for feat_id, feat_icon, feat_title, feat_desc in cat_feats:
                item_btn = QFrame()
                item_btn.setObjectName(f"navItem_{feat_id}")
                item_btn.setProperty("class", "navItem")
                item_btn.setFixedHeight(48)
                item_btn.setCursor(Qt.PointingHandCursor)

                ib_layout = QHBoxLayout(item_btn)
                ib_layout.setContentsMargins(10, 4, 10, 4)
                ib_layout.setSpacing(8)

                icon_lbl = QLabel(feat_icon)
                icon_lbl.setFixedWidth(24)
                icon_lbl.setStyleSheet(f"font-size: 15px; color: {theme.CRIMSON_DANGER if feat_id == 'factory_reset' else theme.CYAN_PRIMARY}; background: transparent; border: none;")
                ib_layout.addWidget(icon_lbl)

                text_box = QVBoxLayout()
                text_box.setSpacing(1)
                t_lbl = QLabel(feat_title)
                t_lbl.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme.CRIMSON_DANGER if feat_id == 'factory_reset' else theme.TEXT_PRIMARY}; background: transparent; border: none;")
                d_lbl = QLabel(feat_desc)
                d_lbl.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_MUTED}; background: transparent; border: none;")
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
                    "desc": d_lbl,
                    "icon": icon_lbl
                }

        self.nav_layout.addStretch()
        nav_scroll.setWidget(nav_widget)
        sidebar_layout.addWidget(nav_scroll)
        workspace_layout.addWidget(sidebar)

        # Right Area: Splitter holding Content & Terminal
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.setHandleWidth(1)

        # Content Card Frame (holds the active feature views without outer card border)
        content_frame = QFrame()
        content_frame.setObjectName("contentPanel")
        content_frame.setStyleSheet("QFrame#contentPanel { background-color: transparent; border: none; }")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.page_stack = QStackedWidget()
        content_layout.addWidget(self.page_stack)
        right_splitter.addWidget(content_frame)

        # Bottom Terminal & Progress Box
        bottom_box = QFrame()
        bottom_box.setProperty("class", "card")
        bottom_box.setFixedHeight(195)
        bottom_layout = QVBoxLayout(bottom_box)
        bottom_layout.setContentsMargins(16, 10, 16, 10)
        bottom_layout.setSpacing(8)

        # Progress bar strip & Controls
        prog_bar = QHBoxLayout()
        prog_bar.setContentsMargins(0, 0, 0, 0)
        prog_bar.setSpacing(10)

        self.lbl_status = QLabel("System Idle — Ready for operation.")
        self.lbl_status.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED};")
        prog_bar.addWidget(self.lbl_status)
        prog_bar.addStretch()

        self.btn_cancel_op = QPushButton("⏹ CANCEL")
        self.btn_cancel_op.setObjectName("btnCancelOp")
        self.btn_cancel_op.setCursor(Qt.PointingHandCursor)
        self.btn_cancel_op.setFixedHeight(22)
        self.btn_cancel_op.setVisible(False)
        self.btn_cancel_op.clicked.connect(self.cancel_current_operation)
        prog_bar.addWidget(self.btn_cancel_op)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(260)
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_anim = QPropertyAnimation(self.progress_bar, b"value")
        self.progress_anim.setEasingCurve(QEasingCurve.OutQuad)
        prog_bar.addWidget(self.progress_bar)
        bottom_layout.addLayout(prog_bar)

        term_sep = QFrame()
        term_sep.setFrameShape(QFrame.HLine)
        term_sep.setFixedHeight(1)
        term_sep.setStyleSheet(f"background-color: {theme.BORDER_SLATE}; border: none;")
        bottom_layout.addWidget(term_sep)

        # Terminal Console Strip
        term_header = QHBoxLayout()
        lbl_console = QLabel("💻 TERMINAL & SYSTEM LOGS")
        lbl_console.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {theme.TEXT_MUTED}; letter-spacing: 0.5px;")
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
            d = item["desc"]
            icon = item.get("icon")
            obj_name = fr.objectName() or f"navItem_{fid}"
            is_active = (fid == feature_id)
            if is_active:
                fr.setStyleSheet(f"""
                    QFrame#{obj_name} {{
                        background-color: {theme.CYAN_ALPHA_15};
                        border: 1px solid {theme.CYAN_PRIMARY};
                        border-left: 3px solid {theme.CYAN_PRIMARY};
                        border-radius: 8px;
                    }}
                    QLabel {{
                        border: none;
                        background-color: transparent;
                    }}
                """)
                t.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
                d.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_MUTED}; border: none; background: transparent;")
                if icon:
                    icon.setStyleSheet(f"font-size: 15px; color: {theme.CRIMSON_DANGER if fid == 'factory_reset' else theme.CYAN_PRIMARY}; border: none; background: transparent;")
            else:
                fr.setStyleSheet(f"""
                    QFrame#{obj_name} {{
                        background-color: transparent;
                        border: 1px solid transparent;
                        border-radius: 8px;
                    }}
                    QFrame#{obj_name}:hover {{
                        background-color: {theme.SURFACE_2};
                        border: 1px solid {theme.BORDER_SLATE};
                    }}
                    QLabel {{
                        border: none;
                        background-color: transparent;
                    }}
                """)
                t.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme.CRIMSON_DANGER if fid == 'factory_reset' else theme.TEXT_PRIMARY}; border: none; background: transparent;")
                d.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_MUTED}; border: none; background: transparent;")
                if icon:
                    icon.setStyleSheet(f"font-size: 15px; color: {theme.CRIMSON_DANGER if fid == 'factory_reset' else theme.CYAN_PRIMARY}; border: none; background: transparent;")

    # ---------------------------------------------------------
    # USB MANAGEMENT & SIGNALS
    # ---------------------------------------------------------
    def _refresh_usb_drives(self):
        if hasattr(self, "btn_refresh_usb"):
            self.btn_refresh_usb.setText("🔄 Scanning...")
            self.btn_refresh_usb.setStyleSheet(f"color: {theme.CYAN_PRIMARY};")
            QApplication.processEvents()

        drives = get_removable_drives()
        self._on_usb_drives_changed(drives)

        if hasattr(self, "btn_refresh_usb"):
            self.btn_refresh_usb.setText("✓ Refreshed!")
            self.btn_refresh_usb.setStyleSheet(f"color: {theme.MINT_SUCCESS};")
            QTimer.singleShot(1200, lambda: (
                self.btn_refresh_usb.setText("🔄 Refresh"),
                self.btn_refresh_usb.setStyleSheet("")
            ))

    @Slot(list)
    def _on_usb_drives_changed(self, drives: list):
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
                elif d.has_backup:
                    item_text += " ★ BACKUP"
                self.usb_combo.addItem(item_text, userData=d)
                if prev_letter and d.letter == prev_letter:
                    matched_idx = i

            self.usb_combo.setCurrentIndex(matched_idx)
            self.current_usb = drives[matched_idx]
            self._update_usb_status_ui()

            # Warn user if multiple removable drives are detected
            if len(drives) > 1 and getattr(self, "_last_warned_drive_count", 0) != len(drives):
                self._last_warned_drive_count = len(drives)
                self.log_terminal(f"⚠️ Multiple removable drives detected ({len(drives)} drives)! Please verify the target USB drive selected in the dropdown.", "warn")
            elif len(drives) == 1:
                self._last_warned_drive_count = 1

            # Auto-prompt if backup found
            if self.current_usb and self.current_usb.has_backup:
                if getattr(self, "_last_logged_backup_drive", None) != self.current_usb.letter:
                    self._last_logged_backup_drive = self.current_usb.letter
                    self.log_terminal(f"Car backup detected on {self.current_usb.letter} (Date: {self.current_usb.backup_date}). Ready for PC Vault Sync.", "mint")
            else:
                self._last_logged_backup_drive = None

        self.usb_combo.blockSignals(False)

    def _update_usb_status_ui(self):
        if not self.current_usb:
            self.usb_status_dot.setStyleSheet(f"color: {theme.CRIMSON_DANGER}; font-size: 16px;")
            self.usb_status_dot.setToolTip("No USB Flash Drive Detected")
            self.usb_combo.setToolTip("Please insert a USB flash drive to prepare payloads.")
            self._update_backup_sync_button()
            return

        d = self.current_usb
        self.usb_status_dot.setStyleSheet(f"color: {theme.MINT_SUCCESS}; font-size: 16px;")
        self.usb_status_dot.setToolTip(f"USB Connected: {d.letter} [{d.label or 'Removable Disk'}]")
        tip = (
            f"💾 Removable USB Flash Drive\n"
            f"───────────────────────────────\n"
            f"• Target Drive: {d.letter}\n"
            f"• Volume Label: {d.label or 'Removable Disk'}\n"
            f"• File System: {d.fs_name} ({'Optimal for Dongfeng IVI' if d.fs_name.upper() == 'FAT32' else 'Recommended: FAT32'})\n"
            f"• Free Space: {d.free_gb:.1f} GB / {d.total_gb:.1f} GB Total\n"
            f"• Used Space: {d.used_gb:.1f} GB\n"
            f"• Status: Connected & Monitored\n"
            f"───────────────────────────────\n"
            f"💡 Click ⚙️ or Right-Click for Settings & Tools"
        )
        self.usb_combo.setToolTip(tip)
        self._update_backup_sync_button()

    def _on_usb_selected(self, index: int):
        drive = self.usb_combo.currentData()
        if drive and isinstance(drive, UsbDriveInfo):
            self.current_usb = drive
            self._update_usb_status_ui()
            self._update_backup_sync_button()
            self.log_terminal(f"Target USB Drive switched to: {drive.letter} [{drive.label}] ({drive.free_gb:.1f} GB free)", "mint")

    _on_user_selected_drive = _on_usb_selected

    def _show_usb_menu(self, pos=None, button_anchor=False):
        if not self.current_usb:
            self.show_error_dialog("No USB Drive", "Please insert a removable USB flash drive to access tools.")
            return

        menu = QMenu(self)
        menu.setObjectName("usbToolsMenu")

        d = self.current_usb
        title_action = menu.addAction(f"💾 USB Drive: {d.letter} [{d.label or 'Removable Disk'}]")
        title_action.setEnabled(False)
        menu.addSeparator()

        act_open = menu.addAction("📂 Open in Windows Explorer")
        act_open.triggered.connect(self._open_usb_in_explorer)

        act_format = menu.addAction("⚡ Format Flash Drive (FAT32)")
        act_format.triggered.connect(lambda: self._format_usb_fat32_interactive("FAT32"))

        menu.addSeparator()
        act_rescan = menu.addAction("🔄 Rescan Removable Drives")
        act_rescan.triggered.connect(self._refresh_usb_drives)

        if button_anchor and hasattr(self, "btn_usb_settings"):
            btn_pos = self.btn_usb_settings.mapToGlobal(QPoint(0, self.btn_usb_settings.height() + 4))
            menu.exec(btn_pos)
        elif pos is not None and isinstance(pos, QPoint):
            global_pos = self.usb_combo.mapToGlobal(pos)
            menu.exec(global_pos)
        else:
            menu.exec(QCursor.pos())

    def _open_usb_in_explorer(self):
        if not self._check_usb_ready(): return
        try:
            os.startfile(self.current_usb.letter)
            self.log_terminal(f"Opened target USB {self.current_usb.letter} in Windows Explorer.", "mint")
        except Exception as e:
            self.show_error_dialog("Error", f"Failed to open USB drive: {e}")

    def _format_usb_fat32_interactive(self, target_fs: str = "FAT32"):
        if not self._check_usb_ready(): return
        if self.is_busy:
            self.show_error_dialog("Operation Busy", "Please wait for current operation to complete before formatting.")
            return

        d = self.current_usb
        letter = d.letter
        confirm_msg = (
            f"Are you sure you want to format USB drive {letter}?\n\n"
            f"• Target File System: {target_fs}\n"
            f"• Volume Label: AERO_USB\n"
            f"• Total Capacity: {d.total_gb:.1f} GB\n\n"
            f"⚠️ CRITICAL WARNING:\n"
            f"All existing files, partitions, and data on drive {letter} will be PERMANENTLY ERASED!\n\n"
            f"Do you wish to proceed with formatting?"
        )
        if not self.show_confirm_dialog(f"Format USB Drive ({target_fs})", confirm_msg, confirm_text=f"⚡ Format {letter}", is_danger=True):
            return

        from payload_engine import format_usb_drive

        def _on_format_done(ok, err):
            if ok:
                QTimer.singleShot(1000, self._refresh_usb_drives)

        self.execute_payload_worker(
            format_usb_drive,
            letter,
            fs=target_fs,
            label="AERO_USB",
            success_title="USB Format Completed",
            success_msg=f"Drive {letter} was successfully formatted as {target_fs}!"
        )
        if self.current_worker:
            self.current_worker.finished_signal.connect(_on_format_done)

    def _validate_usb_filesystem(self) -> bool:
        """
        Pre-flight check to verify target USB drive filesystem before preparing payload.
        Vehicles require FAT32 (or exFAT for >32GB drives).
        If not properly formatted, presents a modal warning with direct format action.
        """
        if not self._check_usb_ready():
            return False

        d = self.current_usb
        fs = (d.fs_type or "").strip().upper()
        size_gb = getattr(d, "total_gb", 0.0)

        # FAT32 and FAT are valid for all drives. exFAT is valid for large drives (>32GB).
        is_valid = (fs in ["FAT32", "FAT"]) or (fs == "EXFAT" and size_gb > 32.0)
        if is_valid:
            return True

        rec_fs = "exFAT" if size_gb > 32.0 and fs != "FAT32" else "FAT32"

        msg_box = QMessageBox(self)
        msg_box.setWindowModality(Qt.WindowModal)
        msg_box.setWindowTitle("⚠️ Incompatible USB File System")
        msg_box.setIcon(QMessageBox.Warning)

        warn_text = (
            f"Target USB drive ({d.letter}) is currently formatted as {fs or 'Unknown'}.\n\n"
            f"Vehicle infotainment systems (Dongfeng IVI) require FAT32 (or exFAT for large drives) "
            f"to read and execute automotive payload scripts. Scripts placed on an {fs or 'unsupported'} "
            f"drive will NOT be recognized by your car's screen.\n\n"
            f"Would you like to format this drive to {rec_fs} now?"
        )
        msg_box.setText(warn_text)

        btn_format = msg_box.addButton(f"⚡ Format Drive to {rec_fs} Now", QMessageBox.AcceptRole)
        btn_format.setStyleSheet(f"background-color: {theme.CYAN_PRIMARY}; color: black; font-weight: bold; padding: 6px 14px; border-radius: 4px;")

        btn_cancel = msg_box.addButton("Cancel", QMessageBox.RejectRole)
        btn_cancel.setStyleSheet(f"background-color: {theme.SURFACE_3}; color: {theme.TEXT_PRIMARY}; padding: 6px 14px; border-radius: 4px;")

        msg_box.exec()

        if msg_box.clickedButton() == btn_format:
            self._format_usb_fat32_interactive(target_fs=rec_fs)
            return False
        return False

    def _check_usb_ready(self) -> bool:
        if not self.current_usb:
            self.show_error_dialog("No USB Drive", "Please insert a removable USB flash drive to continue.")
            return False
        return True

    def _check_busy_and_warn(self) -> bool:
        """Returns True if busy, after logging to terminal and presenting a warning modal."""
        if self.is_busy:
            self.log_terminal("⚠️ Operation in progress! Please wait or cancel the current operation before starting a new one.", "warn")
            self.show_error_dialog(
                "Operation in Progress",
                "Another operation is currently running. Please wait for it to complete or click [CANCEL] in the progress bar before starting a new operation."
            )
            return True
        return False

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
    def _smooth_set_progress(self, target_val: int, status_text: str = ""):
        """Smoothly interpolates progress bar value using QPropertyAnimation without sudden jerky jumps."""
        if status_text:
            self.lbl_status.setText(status_text)

        cur = self.progress_bar.value()
        if target_val <= cur:
            if target_val == 0:
                self.progress_anim.stop()
                self.progress_bar.setValue(0)
            return

        diff = target_val - cur
        # Adaptive duration: faster for small incremental byte chunks, smooth for larger steps
        duration = min(280, max(80, diff * 12))
        if target_val >= 100:
            duration = 180

        self.progress_anim.stop()
        self.progress_anim.setDuration(duration)
        self.progress_anim.setStartValue(cur)
        self.progress_anim.setEndValue(target_val)
        self.progress_anim.start()

    def set_operation_state(self, is_busy: bool, loading_text: str = ""):
        self.is_busy = is_busy
        self.btn_cancel_op.setVisible(is_busy)
        if is_busy:
            self.progress_anim.stop()
            self.progress_bar.setValue(0)
            self._smooth_set_progress(5, loading_text or "Operation in progress...")
        else:
            self._smooth_set_progress(100, "System Idle — Ready for operation.")
            QTimer.singleShot(1500, lambda: self._smooth_set_progress(0) if not self.is_busy else None)

    def cancel_current_operation(self):
        if self.current_worker and self.is_busy:
            self.cancel_event.set()
            self.log_terminal("Cancellation requested by user. Waiting for safe abort...", "warn")

    def execute_payload_worker(self, target_func, *args, success_title="", success_msg="", error_title="", error_msg="", **kwargs):
        self.cancel_event.clear()
        self.set_operation_state(True, "Preparing USB Payload...")

        worker = PayloadWorker(target_func, *args, cancel_event=self.cancel_event, **kwargs)
        self.current_worker = worker

        worker.progress_signal.connect(self._smooth_set_progress)
        worker.log_signal.connect(self.log_terminal)

        def _on_finished(ok, err):
            self.set_operation_state(False)
            self.current_worker = None
            if ok:
                self.log_terminal("Operation completed successfully!", "mint")
                if success_title:
                    self.show_success_dialog(success_title, success_msg)
            elif self.cancel_event.is_set() or "cancel" in str(err).lower():
                self.log_terminal("⚠ Operation cancelled safely by user.", "warn")
            else:
                self.log_terminal(f"✗ Operation failed: {err or 'Action aborted'}", "danger")
                if error_title:
                    self.show_error_dialog(error_title, error_msg or f"Operation Failed:\n{err or 'Action aborted'}")

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
        self.install_count_label.setStyleSheet(
            f"font-size: 11px; color: {theme.CYAN_PRIMARY}; "
            f"background-color: {theme.CYAN_ALPHA_15}; border: 1px solid {theme.BORDER_CYAN}; "
            f"border-radius: 10px; padding: 1px 8px;"
        )
        title_box.addWidget(self.install_count_label)
        title_box.addStretch()
        layout.addLayout(title_box)

        # Feature Description Banner
        banner = QFrame()
        banner.setProperty("class", "card")
        b_layout = QVBoxLayout(banner)
        b_layout.setContentsMargins(14, 8, 14, 8)
        b_layout.setSpacing(2)
        lbl_desc = QLabel(
            "Select apps to install automatically via USB on your Dongfeng screen without manual setup.\n"
            "Features Auto-Launch on complete, Force Portrait mode, and Fast Startup optimization."
        )
        lbl_desc.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        b_layout.addWidget(lbl_desc)
        layout.addWidget(banner)

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

        # Scroll Area for APK Cards
        self.install_scroll = QScrollArea()
        self.install_scroll.setWidgetResizable(True)
        self.install_cards_container = QWidget()
        self.install_cards_layout = QVBoxLayout(self.install_cards_container)
        self.install_cards_layout.setContentsMargins(0, 0, 10, 0)
        self.install_cards_layout.setSpacing(5)
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

    def _set_card_selected_visual(self, card: QFrame, is_selected: bool):
        if is_selected:
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme.CYAN_ALPHA_15};
                    border: 1px solid {theme.CYAN_PRIMARY};
                    border-radius: 8px;
                }}
                QLabel, QCheckBox, QRadioButton {{
                    border: none;
                    background-color: transparent;
                }}
            """)
        else:
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme.SURFACE_2};
                    border: 1px solid {theme.BORDER_SLATE};
                    border-radius: 8px;
                }}
                QFrame:hover {{
                    border: 1px solid {theme.BORDER_CYAN};
                }}
                QLabel, QCheckBox, QRadioButton {{
                    border: none;
                    background-color: transparent;
                }}
            """)

    def _build_unified_app_row(self, mode: str, a: dict) -> QFrame:
        fname = a["filename"]
        pkg = a.get("package", "")

        card = QFrame()
        card.setProperty("class", "card")
        card.setFixedHeight(40)
        card.setCursor(Qt.PointingHandCursor)

        # Determine selection state
        if mode == "install":
            is_selected = self.selected_install_apks.get(fname, False)
        elif mode == "uninstall":
            is_selected = self.selected_uninstall_pkgs.get(pkg, False)
        elif mode == "open":
            is_selected = (self.selected_open_app_filename == fname and bool(self.selected_open_app_filename))
        else:
            is_selected = False

        self._set_card_selected_visual(card, is_selected)

        c_layout = QHBoxLayout(card)
        c_layout.setContentsMargins(12, 0, 12, 0)
        c_layout.setSpacing(10)

        # 1. Main Checkbox (16x16, no text, transparent)
        chk_main = QCheckBox()
        chk_main.setCursor(Qt.PointingHandCursor)
        chk_main.setChecked(is_selected)
        chk_main.setStyleSheet("background-color: transparent; border: none;")
        c_layout.addWidget(chk_main)

        # 2. App Name with max characters (26 chars)
        disp_name = a.get("display_name", fname)
        max_name_len = 26
        name_text = disp_name[:max_name_len] + "…" if len(disp_name) > max_name_len else disp_name
        lbl_name = QLabel(name_text)
        lbl_name.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {theme.TEXT_PRIMARY}; background-color: transparent; border: none;")
        lbl_name.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        c_layout.addWidget(lbl_name)

        # 3. App Package with max characters (30 chars)
        max_pkg_len = 30
        pkg_text = f"({pkg[:max_pkg_len]}…)" if len(pkg) > max_pkg_len else f"({pkg})"
        lbl_pkg = QLabel(pkg_text)
        lbl_pkg.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_MUTED}; font-family: Consolas, monospace; background-color: transparent; border: none;")
        lbl_pkg.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        c_layout.addWidget(lbl_pkg)

        card.setToolTip(f"{disp_name}\n{pkg}\n{a.get('size_mb', 0)} MB")

        # Flexible space pushing right controls to the right
        c_layout.addStretch()

        # Right side controls:
        # Visual LTR order: Auto Launch -> Force Portrait -> Block Boot Launch -> Target Dropdown -> App Size
        # (Reading from right to left: App Size -> Target Dropdown -> Block Boot Launch -> Force Portrait -> Auto Launch)
        if mode == "install":
            # Auto Launch checkbox: font size and color act like Force Portrait and Block Boot Launch, never changes when selected
            chk_auto = QCheckBox("Auto Launch")
            chk_auto.setCursor(Qt.PointingHandCursor)
            chk_auto.setChecked(self.auto_launch_app_filename == fname)
            chk_auto.setStyleSheet(f"font-size: 11px; font-weight: normal; color: {theme.TEXT_PRIMARY}; background-color: transparent; border: none;")
            chk_auto.stateChanged.connect(lambda state, fn=fname: self._on_auto_launch_toggle(fn, bool(state)))
            c_layout.addWidget(chk_auto)
            c_layout.addSpacing(14)

            # Force Portrait checkbox
            chk_port = QCheckBox("Force Portrait")
            chk_port.setCursor(Qt.PointingHandCursor)
            chk_port.setStyleSheet(f"font-size: 11px; font-weight: normal; color: {theme.TEXT_PRIMARY}; background-color: transparent; border: none;")
            chk_port.setChecked(self.per_app_portrait.get(fname, False))
            chk_port.stateChanged.connect(lambda state, fn=fname: self.per_app_portrait.update({fn: bool(state)}))
            c_layout.addWidget(chk_port)
            c_layout.addSpacing(14)

            # Block Boot Launch checkbox
            chk_boot = QCheckBox("Block Boot Launch")
            chk_boot.setCursor(Qt.PointingHandCursor)
            chk_boot.setStyleSheet(f"font-size: 11px; font-weight: normal; color: {theme.TEXT_PRIMARY}; background-color: transparent; border: none;")
            chk_boot.setChecked(self.per_app_boot.get(fname, False))
            chk_boot.stateChanged.connect(lambda state, fn=fname: self.per_app_boot.update({fn: bool(state)}))
            c_layout.addWidget(chk_boot)
            c_layout.addSpacing(14)

            # Target Dropdown (User App / System App) - compact height 22px, subtle outline, width 92px
            combo_target = QComboBox()
            combo_target.setObjectName("comboTarget")
            combo_target.setFixedWidth(92)
            combo_target.setFixedHeight(22)
            combo_target.setCursor(Qt.PointingHandCursor)
            combo_target.addItems(["User App", "System App"])
            combo_target.setToolTip("Target partition: User App (/data/app) vs System App (/system/app)")
            cur_target = self.per_app_target.get(fname, "user")
            combo_target.setCurrentIndex(0 if cur_target == "user" else 1)
            combo_target.currentIndexChanged.connect(lambda idx, fn=fname: self.per_app_target.update({fn: "user" if idx == 0 else "system"}))
            c_layout.addWidget(combo_target)
            c_layout.addSpacing(14)

        # App Size label (aligned to far right on all 3 modes)
        lbl_size = QLabel(f"{a.get('size_mb', 0)} MB")
        lbl_size.setStyleSheet(f"font-size: 10px; font-family: Consolas, monospace; font-weight: bold; color: {theme.TEXT_MUTED}; background-color: transparent; border: none;")
        lbl_size.setFixedWidth(65)
        lbl_size.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_size.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        c_layout.addWidget(lbl_size)

        # Interaction wiring:
        if mode == "install":
            chk_main.clicked.connect(lambda checked, fn=fname: self._on_install_chk_changed(fn, checked))
            def _card_inst_clicked(event, fn=fname):
                if event.button() == Qt.LeftButton:
                    cur = self.selected_install_apks.get(fn, False)
                    self._on_install_chk_changed(fn, not cur)
            card.mousePressEvent = _card_inst_clicked

            self.install_cards_map[fname] = {
                "card": card,
                "chk_install": chk_main,
                "chk_auto": chk_auto,
                "chk_port": chk_port,
                "chk_boot": chk_boot,
                "combo_target": combo_target,
                "lbl_size": lbl_size
            }

        elif mode == "uninstall":
            chk_main.clicked.connect(lambda checked, p=pkg: self._on_uninstall_chk_changed(p, checked))
            def _card_uninst_clicked(event, p=pkg):
                if event.button() == Qt.LeftButton:
                    cur = self.selected_uninstall_pkgs.get(p, False)
                    self._on_uninstall_chk_changed(p, not cur)
            card.mousePressEvent = _card_uninst_clicked

            self.uninstall_cards_map[pkg] = {
                "card": card,
                "chk": chk_main,
                "lbl_size": lbl_size
            }

        elif mode == "open":
            chk_main.clicked.connect(lambda checked, fn=fname: self._on_open_app_item_clicked(fn))
            def _card_open_clicked(event, fn=fname):
                if event.button() == Qt.LeftButton:
                    self._on_open_app_item_clicked(fn)
            card.mousePressEvent = _card_open_clicked

            self.open_app_row_items[fname] = {
                "row": card,
                "chk": chk_main,
                "lbl_size": lbl_size
            }

        return card

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
            card = self._build_unified_app_row("install", a)
            self.install_cards_layout.addWidget(card)

        self.install_cards_layout.addStretch()

    def _on_install_chk_changed(self, fname: str, is_checked: bool):
        self.selected_install_apks[fname] = is_checked
        if fname in self.install_cards_map:
            item = self.install_cards_map[fname]
            chk_i = item["chk_install"]
            chk_i.blockSignals(True)
            chk_i.setChecked(is_checked)
            chk_i.blockSignals(False)
            self._set_card_selected_visual(item["card"], is_checked)

        # If user unselects an app that had auto launch, clear auto launch
        if not is_checked and self.auto_launch_app_filename == fname:
            self.auto_launch_app_filename = None
            if fname in self.install_cards_map:
                chk_a = self.install_cards_map[fname]["chk_auto"]
                chk_a.blockSignals(True)
                chk_a.setChecked(False)
                chk_a.blockSignals(False)
        self._update_install_button()

    def _on_auto_launch_toggle(self, fname: str, is_checked: bool):
        # UNIFIED BEHAVIOR: Toggling auto-launch does NOT change whether the app is selected for install!
        if is_checked:
            self.auto_launch_app_filename = fname
            # Update all cards in-place without rebuilding or changing font/color!
            for fn, item in self.install_cards_map.items():
                chk = item["chk_auto"]
                chk.blockSignals(True)
                chk.setChecked(fn == fname)
                chk.blockSignals(False)
        else:
            if self.auto_launch_app_filename == fname:
                self.auto_launch_app_filename = None
            if fname in self.install_cards_map:
                chk = self.install_cards_map[fname]["chk_auto"]
                chk.blockSignals(True)
                chk.setChecked(False)
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
                    item = self.install_cards_map[fname]
                    chk_i = item["chk_install"]
                    chk_i.blockSignals(True)
                    chk_i.setChecked(state)
                    chk_i.blockSignals(False)
                    self._set_card_selected_visual(item["card"], state)
                    if not state:
                        chk_a = item["chk_auto"]
                        chk_a.blockSignals(True)
                        chk_a.setChecked(False)
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
                    item = self.install_cards_map[fname]
                    chk_i = item["chk_install"]
                    chk_i.blockSignals(True)
                    chk_i.setChecked(new_state)
                    chk_i.blockSignals(False)
                    self._set_card_selected_visual(item["card"], new_state)
                    if not new_state:
                        chk_a = item["chk_auto"]
                        chk_a.blockSignals(True)
                        chk_a.setChecked(False)
                        chk_a.blockSignals(False)
        self._update_install_button()

    def _set_global_target(self, target: str):
        for a in self.local_apks:
            self.per_app_target[a["filename"]] = target
        for fn, item in self.install_cards_map.items():
            if "combo_target" in item:
                cb = item["combo_target"]
                cb.blockSignals(True)
                cb.setCurrentIndex(0 if target == "user" else 1)
                cb.blockSignals(False)

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
        if self._check_busy_and_warn(): return
        if not self._validate_usb_filesystem(): return

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
        b_layout.setContentsMargins(14, 10, 14, 10)
        lbl_banner = QLabel(
            "Clean up your screen and free up storage safely! 🛡️ Select any installed apps you want to remove. Aero Suite purges the app and its leftover files completely—while 100% protecting all your car's original factory functions (AC controls, radio, reverse camera, and car settings). No risk, pure peace of mind!"
        )
        lbl_banner.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_banner.setWordWrap(True)
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

        btn_invert = QPushButton("Invert")
        btn_invert.clicked.connect(self._invert_uninstall_selection)
        ctrl_bar.addWidget(btn_invert)

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
        self.uninstall_cards_layout.setContentsMargins(0, 0, 10, 0)
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

        self.uninstall_cards_map = {}
        q = self.uninstall_search_query.strip().lower()
        matching = [
            a for a in self.local_apks
            if a["package"] and (not q or (q in a["display_name"].lower() or q in a["package"].lower() or q in a["filename"].lower()))
        ]

        if not matching:
            empty_lbl = QLabel("No packages found matching search criteria.")
            empty_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding: 20px; font-size: 13px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.uninstall_cards_layout.addWidget(empty_lbl)
            self.uninstall_cards_layout.addStretch()
            return

        for a in matching:
            card = self._build_unified_app_row("uninstall", a)
            self.uninstall_cards_layout.addWidget(card)

        self.uninstall_cards_layout.addStretch()

    def _on_uninstall_chk_changed(self, pkg: str, state: bool):
        self.selected_uninstall_pkgs[pkg] = state
        if pkg in self.uninstall_cards_map:
            item = self.uninstall_cards_map[pkg]
            chk = item["chk"]
            chk.blockSignals(True)
            chk.setChecked(state)
            chk.blockSignals(False)
            self._set_card_selected_visual(item["card"], state)
        self._update_uninstall_button()

    def _set_all_uninstall_pkgs(self, state: bool):
        q = self.uninstall_search_query.strip().lower()
        for a in self.local_apks:
            pkg = a["package"]
            if not pkg: continue
            if not q or (q in a["display_name"].lower() or q in a["package"].lower() or q in a["filename"].lower()):
                self.selected_uninstall_pkgs[pkg] = state
                if pkg in self.uninstall_cards_map:
                    item = self.uninstall_cards_map[pkg]
                    chk = item["chk"]
                    chk.blockSignals(True)
                    chk.setChecked(state)
                    chk.blockSignals(False)
                    self._set_card_selected_visual(item["card"], state)
        self._update_uninstall_button()

    def _invert_uninstall_selection(self):
        q = self.uninstall_search_query.strip().lower()
        for a in self.local_apks:
            pkg = a.get("package", "")
            if not pkg: continue
            if not q or (q in a["display_name"].lower() or q in a["package"].lower() or q in a["filename"].lower()):
                cur = self.selected_uninstall_pkgs.get(pkg, False)
                self.selected_uninstall_pkgs[pkg] = not cur
                if pkg in self.uninstall_cards_map:
                    item = self.uninstall_cards_map[pkg]
                    chk = item["chk"]
                    chk.blockSignals(True)
                    chk.setChecked(not cur)
                    chk.blockSignals(False)
                    self._set_card_selected_visual(item["card"], not cur)
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
        if self._check_busy_and_warn(): return
        if not self._validate_usb_filesystem(): return

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
        b_layout.setContentsMargins(14, 10, 14, 10)
        lbl_banner = QLabel(
            "Can't find your installed app on the car dashboard? No problem! 😎 Some apps don't show an icon on the factory home screen. Select your app here, plug the USB into your car, and it instantly launches directly on screen. Quick, smart, and effortless!"
        )
        lbl_banner.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_banner.setWordWrap(True)
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
        self.open_app_layout.setContentsMargins(0, 0, 10, 0)
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
            empty_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding: 20px; font-size: 13px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.open_app_layout.addWidget(empty_lbl)
            self.open_app_layout.addStretch()
            return

        for a in matching:
            card = self._build_unified_app_row("open", a)
            self.open_app_layout.addWidget(card)

        self.open_app_layout.addStretch()

    def _sync_open_app_rows(self):
        # Mutate row items in-place without rebuilding!
        for fn, item in self.open_app_row_items.items():
            is_cur = (fn == self.selected_open_app_filename and bool(self.selected_open_app_filename))
            row = item["row"]
            chk = item["chk"]

            chk.blockSignals(True)
            chk.setChecked(is_cur)
            chk.blockSignals(False)

            self._set_card_selected_visual(row, is_cur)

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
        if self._check_busy_and_warn(): return
        if not self._validate_usb_filesystem(): return

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
        c_layout.setContentsMargins(18, 16, 18, 16)
        c_layout.setSpacing(14)

        lbl_head = QLabel("⚙️ OPEN NATIVE ANDROID SETTINGS")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Unlock the hidden Android power inside your car! ⚙️ Opens the full native Android Settings menu instantly on your screen without rebooting:\n\n"
            "• 📶 Wi-Fi & Hotspots: Connect to any wireless network or phone hotspot easily.\n"
            "• 🎧 Bluetooth Devices: Pair and manage phones, remotes, and audio accessories.\n"
            "• 💾 Storage & Memory: Check your available storage and free up space.\n"
            "• 🌐 Languages & Options: Adjust system languages, app permissions, and advanced controls freely!"
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
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
        if self._check_busy_and_warn(): return
        if not self._validate_usb_filesystem(): return

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
        return view

    def _execute_install_gms(self):
        if self._check_busy_and_warn(): return
        if not self._validate_usb_filesystem(): return

        letter = self.current_usb.letter
        confirm_msg = (
            f"Are you sure you want to prepare Google Play Services USB on drive {letter}?\n\n"
            f"This will package the integrated Google Play Services suite, native runtime libraries, and voice permissions for your vehicle."
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
        return view

    def _execute_uninstall_gms(self):
        if self._check_busy_and_warn(): return
        if not self._validate_usb_filesystem(): return

        letter = self.current_usb.letter
        confirm_msg = (
            f"Are you sure you want to prepare Google Services Removal USB on drive {letter}?\n\n"
            f"This will prepare a script to safely purge Google Play Services and clean associated account data from your car screen."
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
        return view

    def _execute_disable_launcher(self):
        if self._check_busy_and_warn(): return
        if not self._validate_usb_filesystem(): return

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
        return view

    def _execute_enable_launcher(self):
        if self._check_busy_and_warn(): return
        if not self._validate_usb_filesystem(): return

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
        c_layout.setContentsMargins(18, 16, 18, 16)
        c_layout.setSpacing(14)

        lbl_head = QLabel("🔄 RESTART INFOTAINMENT SCREEN")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Quick screen refresh on the fly! 🔄 Restarts your infotainment screen safely in just a few seconds without turning off your engine, stopping the car, or disconnecting the vehicle battery. Perfect for clearing temporary glitches and speeding up your screen instantly!"
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
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
        if self._check_busy_and_warn(): return
        if not self._validate_usb_filesystem(): return

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
        cp_layout.setContentsMargins(18, 16, 18, 16)
        cp_layout.setSpacing(12)

        lbl_head1 = QLabel("💾 SYSTEM & DATA BACKUP")
        lbl_head1.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        cp_layout.addWidget(lbl_head1)

        lbl_desc1 = QLabel(
            "Never lose your personalized setup! 💾 Saves a complete, secure snapshot of your car screen:\n\n"
            "• 📱 All Your Apps & Accounts: Saves your installed apps, logged-in accounts, and app data.\n"
            "• 🎨 Custom Layouts: Keeps your launcher widgets, custom icons, and favorite shortcuts intact.\n"
            "• 📶 Saved Connections: Backs up your paired Bluetooth phones and saved Wi-Fi networks.\n"
            "• 🔒 Total Peace of Mind: Plug the USB into your car, and it automatically extracts your backup in under a minute!"
        )
        lbl_desc1.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc1.setWordWrap(True)
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
        cs_layout.setContentsMargins(18, 16, 18, 16)
        cs_layout.setSpacing(12)

        lbl_head2 = QLabel("📥 SYNC USB BACKUP TO PC VAULT")
        lbl_head2.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.MINT_SUCCESS};")
        cs_layout.addWidget(lbl_head2)

        lbl_desc2 = QLabel("Safely copies your car backup from your USB drive into your PC Vault repository for permanent safekeeping.")
        lbl_desc2.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED}; border: none; background: transparent;")
        lbl_desc2.setWordWrap(True)
        cs_layout.addWidget(lbl_desc2)

        self.btn_sync = QPushButton("📥 SYNC USB BACKUP TO PC VAULT")
        self.btn_sync.setProperty("class", "btnSuccess")
        self.btn_sync.setFixedHeight(38)
        self.btn_sync.clicked.connect(self._execute_sync_to_pc)
        cs_layout.addWidget(self.btn_sync)
        layout.addWidget(card_sync)

        layout.addStretch()
        self._update_backup_sync_button()
        return view

    def _update_backup_sync_button(self):
        if not hasattr(self, "btn_sync"):
            return
        has_bk = False
        bk_date = ""
        if self.current_usb:
            letter = self.current_usb.letter
            flag1 = os.path.join(letter, "backup_complete.flag")
            dir1 = os.path.join(letter, "Backup")
            dir2 = os.path.join(letter, "PersonalBackup")
            has_bk = bool(getattr(self.current_usb, "has_backup", False) or os.path.exists(flag1) or os.path.isdir(dir1) or os.path.isdir(dir2))
            bk_date = getattr(self.current_usb, "backup_date", "")

        if has_bk:
            date_str = f" ({bk_date})" if bk_date else " (BACKUP DETECTED)"
            self.btn_sync.setEnabled(True)
            self.btn_sync.setText(f"📥 SYNC VEHICLE BACKUP TO PC VAULT{date_str}")
        else:
            self.btn_sync.setEnabled(False)
            self.btn_sync.setText("📥 NO VEHICLE BACKUP DETECTED ON USB DRIVE")

    def _execute_prepare_backup_usb(self):
        if self._check_busy_and_warn(): return
        if not self._validate_usb_filesystem(): return

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
        if self._check_busy_and_warn(): return
        if not self._check_usb_ready(): return

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
        c_layout.setContentsMargins(18, 16, 18, 16)
        c_layout.setSpacing(14)

        lbl_head = QLabel("📥 RESTORE VEHICLE FROM BACKUP")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Get all your apps and settings back in minutes! 📥 Restores your car screen to your favorite saved backup from your PC:\n\n"
            "• 🚀 One-Step Full Recovery: Installs all your saved apps, logins, and widget arrangements automatically.\n"
            "• 📶 Instant Reconnection: Reconnects your Bluetooth phones and Wi-Fi networks without re-typing passwords.\n"
            "• ⚡ Fast & Smart: Skips apps that are already on the screen to finish the restore super fast!"
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)

        self.restore_combo = QComboBox()
        c_layout.addWidget(self.restore_combo)

        self.btn_restore = QPushButton("📥 PREPARE RESTORE USB")
        self.btn_restore.setProperty("class", "btnPrimary")
        self.btn_restore.setFixedHeight(44)
        self.btn_restore.clicked.connect(self._execute_restore)
        c_layout.addWidget(self.btn_restore)

        self._populate_restore_combo()
        self.restore_combo.currentIndexChanged.connect(lambda: self._update_restore_button_state())

        layout.addWidget(card)
        layout.addStretch()
        return view

    def _update_restore_button_state(self):
        if not hasattr(self, "btn_restore"):
            return
        b_path = self.restore_combo.currentData() if hasattr(self, "restore_combo") else None
        if b_path and os.path.exists(b_path):
            self.btn_restore.setEnabled(True)
            self.btn_restore.setText("📥 PREPARE RESTORE USB")
        else:
            self.btn_restore.setEnabled(False)
            self.btn_restore.setText("⚠️ NO SAVED BACKUPS AVAILABLE IN PC VAULT")

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
        self._update_restore_button_state()

    def _execute_restore(self):
        if self._check_busy_and_warn(): return
        if not self._validate_usb_filesystem(): return

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
        c_layout.setContentsMargins(18, 16, 18, 16)
        c_layout.setSpacing(14)

        lbl_head = QLabel("⚠️ ZERO-TRACE FACTORY RESET")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER}; border: none; background: transparent;")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "The ultimate clean slate & dealership reset! ⚠️ Restores your Dongfeng Shine screen to 100% factory-fresh condition:\n\n"
            "• 🚗 Showroom Fresh: Wipes all added apps, Google services, and personal accounts cleanly.\n"
            "• 🛡️ Auto-Healing Stock Apps: Automatically restores any missing original car applications from the factory archive.\n"
            "• 🏢 100% Dealership Ready: Completely hides all modifications before dealership visits and routine maintenance.\n"
            "• 🔒 Safe Protection: Your air conditioning, reverse cameras, and steering wheel controls remain 100% safe and untouched!"
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
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
        if self._check_busy_and_warn(): return
        if not self._validate_usb_filesystem(): return

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
        c_layout.setContentsMargins(18, 16, 18, 16)
        c_layout.setSpacing(14)

        lbl_head = QLabel("📋 FETCH DIAGNOSTIC LOGS")
        lbl_head.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        c_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "Fix screen issues fast without guessing! 🔍 If an app crashes or your screen acts up, don't worry:\n\n"
            "• 📋 Comprehensive Health Check: Gathers system reports, memory stats, and app crash logs in seconds.\n"
            "• 🛠️ Easy Problem Solving: Packages diagnostic logs into a clean folder on your USB drive.\n"
            "• 🤝 Quick Support: Share the folder with the community or developer to get an instant, pinpoint fix!"
        )
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
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
        if self._check_busy_and_warn(): return
        if not self._validate_usb_filesystem(): return

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
