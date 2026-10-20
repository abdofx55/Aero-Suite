"""
app_gui.py — Aero Suite Automotive Infotainment Management Console.
Calibrated for Dongfeng Shine (Aeolus D53) IVI System.
Engineered by Abdelrhman Hamdy - Senior Software Engineer.
"""
import os
import sys
import threading
import time
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image

import theme
from apk_engine import scan_local_apks
from usb_detector import get_removable_drives, UsbWatcher, UsbDriveInfo
from sync_manager import sync_backup_from_usb_to_pc, get_local_backups, find_existing_vault_backup
import payload_engine

# Path discovery
def get_base_dir() -> str:
    # Check if running in a compiled bundle (Nuitka or PyInstaller)
    if getattr(sys, 'frozen', False) or "__compiled__" in globals() or hasattr(sys, '__nuitka_version__'):
        # In Nuitka onefile, sys.argv[0] holds the real on-disk executable path
        if sys.argv and sys.argv[0]:
            candidate = os.path.dirname(os.path.abspath(sys.argv[0]))
            if os.path.exists(os.path.join(candidate, "apks")):
                return candidate
        # In PyInstaller, sys.executable points to the real on-disk exe
        if sys.executable:
            candidate = os.path.dirname(os.path.abspath(sys.executable))
            if os.path.exists(os.path.join(candidate, "apks")):
                return candidate
        # Fallback to sys.argv[0] if valid, else sys.executable
        if sys.argv and sys.argv[0]:
            return os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.dirname(os.path.abspath(sys.executable))

    fdir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(fdir) if os.path.basename(fdir).lower() == "src" else fdir

BASE_DIR = get_base_dir()
APKS_DIR = os.path.join(BASE_DIR, "apks")
GMS_DIR  = os.path.join(APKS_DIR, "google_services")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")
FACTORY_BACKUP_DIR = os.path.join(BASE_DIR, "FactoryBackup")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

for d in [APKS_DIR, BACKUPS_DIR, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class AeroSuiteApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Aero Suite v{theme.APP_VERSION} — Dongfeng Shine IVI Studio")
        self.geometry("1200x680")
        self.minsize(1050, 580)
        self.configure(fg_color=theme.BG_BASE)

        # State
        self.current_usb: UsbDriveInfo = None
        self.all_drives = []
        self.active_feature = "install_apps"
        self.is_busy = False

        # Load local APK data
        self.local_apks = scan_local_apks(APKS_DIR)
        self.allowed_packages = {a["package"] for a in self.local_apks if a["package"]}
        
        # Per-app install state (Target, Portrait, BootBlock - all unselected by default)
        self.selected_install_apks = {a["filename"]: False for a in self.local_apks}
        self.per_app_portrait = {a["filename"]: False for a in self.local_apks}
        self.per_app_target = {a["filename"]: "user" for a in self.local_apks}   # "user" by default, or "system"
        self.per_app_boot = {a["filename"]: False for a in self.local_apks}      # False by default (unselected)
        self.auto_launch_app_filename = None                                     # Single selection (exclusive)

        # Drive selection preference
        self.preferred_usb_letter = None

        # Safe Uninstall selection state
        self.selected_uninstall_pkgs = {a["package"]: False for a in self.local_apks if a["package"]}

        # Real-time substring search queries (Contains matching)
        self.install_search_query = ""
        self.uninstall_search_query = ""
        self.open_app_search_query = ""
        self.selected_open_app_pkg = ""

        # Global Operation & View State Tracker (Preserved across tab switches)
        self.current_operation = ""
        self.current_operation_title = ""
        self.cancel_event = threading.Event()
        self.selected_restore_path = ""
        self.confirmed_reset_state = False

        # Dual Backup Configuration State
        self.backup_mode_var = ctk.StringVar(value="🔒 Personal Private (1:1 Clone)")
        self.backup_media_var = ctk.BooleanVar(value=False)
        self.backup_preset_name_var = ctk.StringVar(value="")
        self.backup_author_var = ctk.StringVar(value="")

        # UI Setup
        self._build_header()
        self._build_developer_chip()
        self._build_terminal()
        self._build_main_layout()

        # Start USB background watcher
        self.usb_watcher = UsbWatcher(self._on_usb_change_detected, interval_sec=1.5)
        self.usb_watcher.start()
        self._refresh_usb_drives()

        # Initial Tab
        self.select_feature("install_apps")
        self.log_terminal(f"Aero Suite Studio v{theme.APP_VERSION} initialized successfully.", "info")
        self.log_terminal(f"Loaded {len(self.local_apks)} local automotive APKs from apks/ repository.", "mint")
        try:
            with open(os.path.join(LOGS_DIR, "session.log"), "a", encoding="utf-8") as lf:
                lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] BASE_DIR: {BASE_DIR} | Loaded {len(self.local_apks)} APKs\n")
        except Exception:
            pass

    def _rescan_local_apks(self):
        """Re-scans the apks/ directory and updates internal repository lists in-place."""
        self.local_apks = scan_local_apks(APKS_DIR)
        self.allowed_packages = {a["package"] for a in self.local_apks if a["package"]}
        current_filenames = {a["filename"] for a in self.local_apks}

        # Preserve existing selections while adding new APKs
        for a in self.local_apks:
            f = a["filename"]
            pkg = a["package"]
            if f not in self.selected_install_apks: self.selected_install_apks[f] = False
            if f not in self.per_app_portrait: self.per_app_portrait[f] = False
            if f not in self.per_app_target: self.per_app_target[f] = "user"
            if f not in self.per_app_boot: self.per_app_boot[f] = False
            if pkg and pkg not in self.selected_uninstall_pkgs: self.selected_uninstall_pkgs[pkg] = False

        if self.auto_launch_app_filename and self.auto_launch_app_filename not in current_filenames:
            self.auto_launch_app_filename = None

        if hasattr(self, "selected_open_app_pkg") and self.selected_open_app_pkg not in self.allowed_packages:
            self.selected_open_app_pkg = ""

        self.log_terminal(f"🔄 APK Repository refreshed: {len(self.local_apks)} applications found in apks/ folder.", "mint")
        self._refresh_active_view()

    # -----------------------------------------------------------------------
    # Top Header & Status Bar
    # -----------------------------------------------------------------------
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=theme.SURFACE_1, height=65, corner_radius=0)
        header.pack(fill="x", side="top")

        # Left brand info
        left_box = ctk.CTkFrame(header, fg_color="transparent")
        left_box.pack(side="left", padx=20, pady=10)

        title_label = ctk.CTkLabel(
            left_box,
            text="⚡ AERO SUITE",
            font=("Space Grotesk", 18, "bold"),
            text_color=theme.CYAN_PRIMARY
        )
        title_label.pack(side="left", padx=(0, 10))

        # Version Pill Badge
        ver_badge = ctk.CTkFrame(
            left_box,
            fg_color=theme.CYAN_ALPHA_15,
            corner_radius=6,
            border_width=1,
            border_color=theme.BORDER_CYAN
        )
        ver_badge.pack(side="left", padx=(0, 15))
        ctk.CTkLabel(
            ver_badge,
            text=f"v{theme.APP_VERSION}",
            font=("Space Grotesk", 10, "bold"),
            text_color=theme.CYAN_PRIMARY
        ).pack(padx=7, pady=2)

        sub_label = ctk.CTkLabel(
            left_box,
            text="Dongfeng Shine (Aeolus D53) IVI Studio",
            font=("Inter", 12),
            text_color=theme.TEXT_MUTED
        )
        sub_label.pack(side="left")

        # Right USB indicator & Interactive Drive Selector
        right_box = ctk.CTkFrame(header, fg_color="transparent")
        right_box.pack(side="right", padx=20, pady=10)

        self.usb_status_dot = ctk.CTkLabel(
            right_box,
            text="●",
            font=("Arial", 16),
            text_color=theme.CRIMSON_DANGER
        )
        self.usb_status_dot.pack(side="left", padx=(0, 6))

        self.usb_dropdown_var = ctk.StringVar(value="NO USB FLASH DETECTED")
        self.usb_dropdown = ctk.CTkOptionMenu(
            right_box,
            values=["NO USB FLASH DETECTED"],
            variable=self.usb_dropdown_var,
            width=290,
            height=28,
            font=("Space Grotesk", 11, "bold"),
            dropdown_font=("Space Grotesk", 11),
            fg_color=theme.SURFACE_2,
            button_color=theme.SURFACE_3,
            button_hover_color=theme.CYAN_HOVER,
            dropdown_fg_color=theme.SURFACE_1,
            dropdown_hover_color=theme.SURFACE_3,
            text_color=theme.TEXT_PRIMARY,
            command=self._on_user_selected_drive
        )
        self.usb_dropdown.pack(side="left", padx=(0, 10))

        btn_refresh = ctk.CTkButton(
            right_box,
            text="🔄 Refresh",
            width=80,
            height=28,
            font=("Inter", 11, "bold"),
            fg_color=theme.SURFACE_2,
            hover_color=theme.SURFACE_3,
            text_color=theme.CYAN_PRIMARY,
            command=self._refresh_usb_drives
        )
        btn_refresh.pack(side="left")

    def _build_developer_chip(self):
        chip_bar = ctk.CTkFrame(self, fg_color=theme.SURFACE_2, height=32, corner_radius=0)
        chip_bar.pack(fill="x", side="top")

        # Left: Developer Contact & Bio
        dev_label = ctk.CTkLabel(
            chip_bar,
            text=f"👨‍💻 {theme.DEVELOPER_NAME}   |   ✉️ {theme.DEVELOPER_EMAIL}   |   📞 {theme.DEVELOPER_PHONE}",
            font=("Inter", 11),
            text_color=theme.TEXT_MUTED
        )
        dev_label.pack(side="left", padx=20, pady=4)

        # Right: Free Community Gift Notice
        gift_label = ctk.CTkLabel(
            chip_bar,
            text=theme.GIFT_COMMUNITY_TEXT,
            font=("Inter", 11, "bold"),
            text_color=theme.MINT_SUCCESS
        )
        gift_label.pack(side="right", padx=20, pady=4)

    # -----------------------------------------------------------------------
    # Main Workspace (Sidebar + Dynamic Panels)
    # -----------------------------------------------------------------------
    def _build_main_layout(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=16, pady=10)

        # Left Sidebar (Feature Matrix)
        self.sidebar = ctk.CTkScrollableFrame(
            self.main_container,
            fg_color=theme.SURFACE_1,
            width=275,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER_SLATE
        )
        self.sidebar.pack(side="left", fill="y", padx=(0, 12), pady=0)

        sidebar_title = ctk.CTkLabel(
            self.sidebar,
            text="SYSTEM FEATURES",
            font=("Space Grotesk", 12, "bold"),
            text_color=theme.CYAN_PRIMARY
        )
        sidebar_title.pack(anchor="w", padx=12, pady=(10, 4))

        # Categorized Features Matrix (ID, Icon, Title, Subtitle)
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
        self.features = [feat for _, feats in self.feature_categories for feat in feats]

        self.feature_buttons = {}
        for cat_title, cat_feats in self.feature_categories:
            cat_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
            cat_box.pack(fill="x", padx=10, pady=(8, 2))
            ctk.CTkLabel(
                cat_box,
                text=cat_title,
                font=("Space Grotesk", 9, "bold"),
                text_color=theme.TEXT_MUTED
            ).pack(side="left")

            for feat_id, feat_icon, feat_title, feat_desc in cat_feats:
                item_frame = ctk.CTkFrame(
                    self.sidebar,
                    height=46,
                    corner_radius=8,
                    fg_color="transparent",
                    border_width=0
                )
                item_frame.pack(fill="x", padx=6, pady=2)
                item_frame.pack_propagate(False)

                # Fixed-width Icon slot (exactly 34px wide)
                icon_lbl = ctk.CTkLabel(
                    item_frame,
                    text=feat_icon,
                    width=34,
                    font=("Segoe UI Emoji", 14),
                    text_color=theme.CYAN_PRIMARY if feat_id != "factory_reset" else theme.CRIMSON_DANGER
                )
                icon_lbl.pack(side="left", padx=(6, 2), fill="y")

                # Text block (Title + Subtitle) - completely aligned
                text_block = ctk.CTkFrame(item_frame, fg_color="transparent")
                text_block.pack(side="left", fill="both", expand=True, pady=2)

                title_color = theme.TEXT_PRIMARY if feat_id != "factory_reset" else theme.CRIMSON_DANGER
                title_lbl = ctk.CTkLabel(
                    text_block,
                    text=feat_title,
                    font=("Inter", 11, "bold"),
                    text_color=title_color,
                    anchor="w"
                )
                title_lbl.pack(fill="x", anchor="w")

                desc_lbl = ctk.CTkLabel(
                    text_block,
                    text=feat_desc,
                    font=("Inter", 9),
                    text_color=theme.TEXT_MUTED,
                    anchor="w"
                )
                desc_lbl.pack(fill="x", anchor="w")

                def _bind_item(fr, fid, widgets):
                    def _click(e=None):
                        self.select_feature(fid)
                    def _enter(e=None):
                        if self.active_feature != fid:
                            fr.configure(fg_color=theme.SURFACE_3)
                    def _leave(e=None):
                        if self.active_feature != fid:
                            fr.configure(fg_color="transparent")

                    for w in widgets:
                        w.bind("<Button-1>", _click)
                        w.bind("<Enter>", _enter)
                        w.bind("<Leave>", _leave)

                _bind_item(item_frame, feat_id, [item_frame, icon_lbl, text_block, title_lbl, desc_lbl])
                self.feature_buttons[feat_id] = item_frame

        # Right Dynamic Panel
        self.content_panel = ctk.CTkFrame(
            self.main_container,
            fg_color=theme.SURFACE_1,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER_SLATE
        )
        self.content_panel.pack(side="right", fill="both", expand=True)

    # -----------------------------------------------------------------------
    # Terminal Console & Progress Bar
    # -----------------------------------------------------------------------
    def _build_terminal(self):
        bottom_box = ctk.CTkFrame(self, fg_color=theme.SURFACE_1, height=145, corner_radius=0)
        bottom_box.pack(fill="x", side="bottom")
        bottom_box.pack_propagate(False)

        # Progress bar strip & Controls
        self.prog_container = ctk.CTkFrame(bottom_box, fg_color="transparent")
        self.prog_container.pack(fill="x", padx=16, pady=(6, 2))

        # Fixed-width action/file label
        self.prog_label = ctk.CTkLabel(
            self.prog_container,
            text="System Idle — Ready for operation.",
            width=370,
            anchor="w",
            font=("Consolas", 11),
            text_color=theme.CYAN_PRIMARY
        )
        self.prog_label.pack(side="left")

        # Copy Logs Button (Fixed width)
        self.btn_copy_logs = ctk.CTkButton(
            self.prog_container,
            text="📋 Copy Logs",
            width=85,
            height=24,
            font=("Inter", 10, "bold"),
            fg_color=theme.SURFACE_2,
            hover_color=theme.SURFACE_3,
            text_color=theme.CYAN_PRIMARY,
            command=self._copy_terminal_logs
        )
        self.btn_copy_logs.pack(side="right", padx=(6, 0))

        # Clear Logs Button (Fixed width)
        self.btn_clear_logs = ctk.CTkButton(
            self.prog_container,
            text="🗑 Clear",
            width=55,
            height=24,
            font=("Inter", 10),
            fg_color=theme.SURFACE_2,
            hover_color=theme.SURFACE_3,
            text_color=theme.TEXT_MUTED,
            command=self._clear_terminal_logs
        )
        self.btn_clear_logs.pack(side="right", padx=(6, 0))

        # Cancel Operation Button (Active only when operation is running)
        self.btn_cancel_op = ctk.CTkButton(
            self.prog_container,
            text="⏹ Cancel",
            width=75,
            height=24,
            font=("Inter", 10, "bold"),
            fg_color=theme.SURFACE_2,
            hover_color=theme.SURFACE_3,
            text_color=theme.TEXT_MUTED,
            state="disabled",
            command=self.cancel_current_operation
        )
        self.btn_cancel_op.pack(side="right", padx=(6, 0))

        # Fixed-width Stats Label (Percentage, speed MB/s, total MB - strictly anchored)
        self.prog_stats = ctk.CTkLabel(
            self.prog_container,
            text="[  0%] Idle",
            width=190,
            anchor="e",
            font=("Consolas", 11),
            text_color=theme.MINT_SUCCESS
        )
        self.prog_stats.pack(side="right", padx=(6, 10))

        # Progress bar in middle (occupies fixed remaining space without jitter)
        self.progress_bar = ctk.CTkProgressBar(
            self.prog_container,
            height=8,
            corner_radius=4,
            progress_color=theme.CYAN_PRIMARY,
            fg_color=theme.SURFACE_2
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self.progress_bar.set(0.0)

        # Monospaced Log View
        self.terminal_view = ctk.CTkTextbox(
            bottom_box,
            height=100,
            fg_color=theme.TERM_BG,
            text_color=theme.TERM_TEXT_CYAN,
            font=("Consolas", 10),
            corner_radius=6,
            border_width=1,
            border_color=theme.BORDER_SLATE
        )
        self.terminal_view.pack(fill="both", expand=True, padx=16, pady=(4, 8))

    def _copy_terminal_logs(self):
        log_text = self.terminal_view.get("1.0", "end-1c")
        if log_text.strip():
            self.clipboard_clear()
            self.clipboard_append(log_text)
            self.btn_copy_logs.configure(text="✓ Copied!", text_color=theme.MINT_SUCCESS)
            self.after(2000, lambda: self.btn_copy_logs.configure(text="📋 Copy Logs", text_color=theme.CYAN_PRIMARY))

    def _clear_terminal_logs(self):
        self.terminal_view.delete("1.0", "end")

    def cancel_current_operation(self):
        """Signals active background threads to abort immediately and unlocks application."""
        if not self.is_busy:
            return
        self.cancel_event.set()
        self.log_terminal("Cancellation requested! Aborting current operation...", "warn")
        self.prog_label.configure(text="⏳ Cancelling operation...")
        self.prog_stats.configure(text="[--%] Cancelling...")
        if hasattr(self, "btn_cancel_op") and self.btn_cancel_op.winfo_exists():
            self.btn_cancel_op.configure(state="disabled", fg_color=theme.SURFACE_2, text_color=theme.TEXT_MUTED)

    def log_terminal(self, message: str, level: str = "cyan"):
        timestamp = time.strftime("[%H:%M:%S] ")
        prefix = "• "
        color = theme.TERM_TEXT_CYAN
        if level == "mint":
            color = theme.TERM_TEXT_MINT
            prefix = "✓ "
        elif level == "danger":
            color = theme.TERM_TEXT_ROSE
            prefix = "✗ "
        elif level == "warn":
            color = theme.AMBER_WARN
            prefix = "⚠ "

        line = f"{timestamp}{prefix}{message}\n"
        self.terminal_view.insert("end", line)
        self.terminal_view.see("end")

    def start_progress(self, action_title: str):
        """Immediately updates progress bar to 0% with clear descriptive starting message and enables Cancel."""
        self.cancel_event.clear()
        self.current_operation_title = action_title
        def _ui():
            self.progress_bar.set(0.0)
            self.prog_label.configure(text=f"⏳ {action_title}...")
            self.prog_stats.configure(text="[  0%] Starting...")
            if hasattr(self, "btn_cancel_op") and self.btn_cancel_op.winfo_exists():
                self.btn_cancel_op.configure(
                    state="normal",
                    fg_color=theme.CRIMSON_DANGER,
                    hover_color=theme.CRIMSON_HOVER,
                    text_color=theme.TEXT_PRIMARY
                )
        self.after(0, _ui)

    def finish_progress(self, success: bool = True, final_text: str = ""):
        """Sets progress bar to final status with descriptive message and resets Cancel button."""
        self.current_operation_title = ""
        def _ui():
            if hasattr(self, "btn_cancel_op") and self.btn_cancel_op.winfo_exists():
                self.btn_cancel_op.configure(
                    state="disabled",
                    fg_color=theme.SURFACE_2,
                    hover_color=theme.SURFACE_3,
                    text_color=theme.TEXT_MUTED
                )
            if self.cancel_event.is_set():
                self.progress_bar.set(0.0)
                self.prog_label.configure(text="⚠ Operation cancelled by user.")
                self.prog_stats.configure(text="[ 0%] Cancelled")
            elif success:
                self.progress_bar.set(1.0)
                self.prog_label.configure(text=f"✓ {final_text or 'Payload prepared successfully.'}")
                self.prog_stats.configure(text="[100%] Ready")
            else:
                self.progress_bar.set(0.0)
                self.prog_label.configure(text=f"✗ {final_text or 'Operation failed.'}")
                self.prog_stats.configure(text="[ 0%] Error")
        self.after(0, _ui)

    def update_progress(self, percent: float, filename: str, speed_mb_s: float, copied_mb: float, total_mb: float):
        def _ui():
            self.progress_bar.set(percent)
            pct_int = int(percent * 100)

            # Strict maximum character limit on filename (doubled to 44 chars)
            max_chars = 44
            fname = filename
            if len(fname) > max_chars:
                fname = fname[:max_chars - 3] + "..."

            if percent >= 1.0 or filename == "Complete":
                self.prog_label.configure(text="✓ Payload prepared successfully.")
                self.prog_stats.configure(
                    text=f"[100%] Vaulted ({total_mb:.1f} MB)" if total_mb > 10 else "[100%] Complete"
                )
            elif speed_mb_s > 0:
                self.prog_label.configure(text=f"Transferring: {fname}")
                self.prog_stats.configure(
                    text=f"[{pct_int:3d}%] {speed_mb_s:4.1f}MB/s {copied_mb:.0f}/{total_mb:.0f}MB"
                )
            else:
                self.prog_label.configure(text=f"Working: {fname}")
                if total_mb > 0:
                    self.prog_stats.configure(text=f"[{pct_int:3d}%] {int(copied_mb)}/{int(total_mb)}")
                else:
                    self.prog_stats.configure(text=f"[{pct_int:3d}%]")
        self.after(0, _ui)

    # -----------------------------------------------------------------------
    # USB Drive Monitoring & Auto-Sync
    # -----------------------------------------------------------------------
    def _on_user_selected_drive(self, selection_str: str):
        if not hasattr(self, "all_drives") or not self.all_drives:
            return
        chosen = None
        for d in self.all_drives:
            if selection_str.startswith(d.letter[:2]) or d.letter.startswith(selection_str[:2]):
                chosen = d
                break
        if chosen:
            self.current_usb = chosen
            self.preferred_usb_letter = chosen.letter
            self.log_terminal(f"Target USB Drive switched to: {chosen.letter} [{chosen.label}] ({chosen.free_gb:.1f} GB free)", "mint")
            self._update_backup_sync_button_state()

    def _refresh_usb_drives(self):
        self.all_drives = get_removable_drives()
        if self.all_drives:
            drive_options = []
            chosen_drive = None

            # 1. Prefer user-selected drive if it's still connected
            if self.preferred_usb_letter:
                chosen_drive = next((d for d in self.all_drives if d.letter == self.preferred_usb_letter), None)

            # 2. Otherwise prefer drive with car backup
            if not chosen_drive:
                chosen_drive = next((d for d in self.all_drives if d.has_backup), None)

            # 3. Fallback to first drive
            if not chosen_drive:
                chosen_drive = self.all_drives[0]

            self.current_usb = chosen_drive
            self.preferred_usb_letter = chosen_drive.letter

            chosen_label = ""
            for d in self.all_drives:
                lbl = f"{d.letter[:2]} [{d.label or 'USB'}] ({d.free_gb:.1f} GB free)"
                if getattr(d, "is_restore_ready", False):
                    lbl += " 🔄 RESTORE"
                elif d.has_backup:
                    lbl += " ★ BACKUP"
                drive_options.append(lbl)
                if d.letter == chosen_drive.letter:
                    chosen_label = lbl

            self.usb_dropdown.configure(values=drive_options)
            self.usb_dropdown_var.set(chosen_label)
            self.usb_status_dot.configure(text="●", text_color=theme.MINT_SUCCESS)

            # Warn user if multiple drives are plugged in (prevent accidental SD card / memory card wipe)
            if len(self.all_drives) > 1:
                if getattr(self, "_last_warned_drive_count", 0) != len(self.all_drives):
                    self._last_warned_drive_count = len(self.all_drives)
                    self.log_terminal(
                        f"⚠️ Multiple removable drives detected ({len(self.all_drives)} drives)! Please verify the target USB drive selected in the dropdown to avoid unintended writes to memory cards.",
                        "warn"
                    )
            else:
                self._last_warned_drive_count = 1

            # Auto-prompt if backup found
            if self.current_usb.has_backup:
                if getattr(self, "_last_logged_backup_drive", None) != self.current_usb.letter:
                    self._last_logged_backup_drive = self.current_usb.letter
                    self.log_terminal(f"Car backup detected on {self.current_usb.letter} (Date: {self.current_usb.backup_date}). Ready for PC Vault Sync.", "mint")
            else:
                self._last_logged_backup_drive = None
        else:
            self.current_usb = None
            self._last_logged_backup_drive = None
            self._last_warned_drive_count = 0
            self.usb_status_dot.configure(text="○", text_color=theme.CRIMSON_DANGER)
            self.usb_dropdown.configure(values=["NO USB FLASH DETECTED"])
            self.usb_dropdown_var.set("NO USB FLASH DETECTED")

        self._update_backup_sync_button_state()

    def _update_backup_sync_button_state(self):
        """Dynamically updates the backup view sync button state to reflect the currently selected USB drive."""
        if hasattr(self, "btn_sync_vault") and self.btn_sync_vault.winfo_exists() and self.current_operation != "sync_vault":
            usb_has_b = bool(self.current_usb and self.current_usb.has_backup)
            already_vaulted = find_existing_vault_backup(self.current_usb.letter, BACKUPS_DIR) if (usb_has_b and self.current_usb) else ""

            if not usb_has_b:
                self.btn_sync_vault.configure(
                    state="disabled",
                    text="📥 SYNC USB BACKUP TO PC VAULT (WITH PROGRESS)",
                    fg_color=theme.SURFACE_3,
                    hover_color=theme.SURFACE_3,
                    text_color=theme.TEXT_MUTED
                )
                if hasattr(self, "lbl_backup_status") and self.lbl_backup_status.winfo_exists():
                    if getattr(self.current_usb, "is_restore_ready", False):
                        status_txt = f"USB ({self.current_usb.letter}) is prepared with a Restore Payload for the car.\nPlug into the car to execute restore. (No new car backup to sync)."
                        color = theme.CYAN_PRIMARY
                    else:
                        status_txt = "No completed backup currently detected on USB. Plug in the USB after taking the car backup."
                        color = theme.TEXT_MUTED
                    self.lbl_backup_status.configure(
                        text=status_txt,
                        text_color=color
                    )
            elif already_vaulted:
                folder_bname = os.path.basename(already_vaulted)
                self.btn_sync_vault.configure(
                    state="normal",
                    text=f"✓ ALREADY VAULTED ({folder_bname}) — Click to Re-Sync",
                    fg_color=theme.SURFACE_3,
                    hover_color=theme.SURFACE_2,
                    text_color=theme.CYAN_PRIMARY
                )
                if hasattr(self, "lbl_backup_status") and self.lbl_backup_status.winfo_exists():
                    self.lbl_backup_status.configure(
                        text=f"✓ This car backup is ALREADY safely stored in PC Vault:\n  Folder: {folder_bname} (Date: {self.current_usb.backup_date})",
                        text_color=theme.MINT_SUCCESS
                    )
            else:
                self.btn_sync_vault.configure(
                    state="normal",
                    text="📥 SYNC USB BACKUP TO PC VAULT (WITH PROGRESS)",
                    fg_color=theme.MINT_SUCCESS,
                    hover_color=theme.MINT_HOVER,
                    text_color=theme.BG_BASE
                )
                if hasattr(self, "lbl_backup_status") and self.lbl_backup_status.winfo_exists():
                    self.lbl_backup_status.configure(
                        text=f"★ New Car Backup Detected on USB ({self.current_usb.letter})! Ready to save to PC Vault.",
                        text_color=theme.MINT_SUCCESS
                    )

    def _on_usb_change_detected(self, drives):
        self.after(0, self._refresh_usb_drives)

    # -----------------------------------------------------------------------
    # Dynamic Feature Switching
    # -----------------------------------------------------------------------
    def select_feature(self, feature_id: str):
        self.active_feature = feature_id

        # Highlight active button
        for fid, btn in self.feature_buttons.items():
            if fid == feature_id:
                btn.configure(
                    fg_color=theme.CYAN_DIM if fid != "factory_reset" else theme.CRIMSON_DIM,
                    border_width=1,
                    border_color=theme.CYAN_PRIMARY if fid != "factory_reset" else theme.CRIMSON_DANGER
                )
            else:
                btn.configure(fg_color="transparent", border_width=0)

        # Clear content panel and route
        for widget in self.content_panel.winfo_children():
            widget.destroy()

        handler = getattr(self, f"_view_{feature_id}", None)
        if handler:
            handler()

    def _refresh_active_view(self):
        """Re-renders the currently active tab to reflect changed state."""
        if hasattr(self, "active_feature") and self.active_feature:
            handler = getattr(self, f"_view_{self.active_feature}", None)
            if handler:
                for widget in self.content_panel.winfo_children():
                    widget.destroy()
                handler()

    # -----------------------------------------------------------------------
    # 1. VIEW: INSTALL APPS (WITH REALTIME SUBSTRING SEARCH & PER-APP OPTIONS)
    # -----------------------------------------------------------------------
    def _view_install_apps(self):
        title_frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(16, 6))

        ctk.CTkLabel(
            title_frame,
            text="📦 INSTALL APPLICATIONS",
            font=("Space Grotesk", 16, "bold"),
            text_color=theme.CYAN_PRIMARY
        ).pack(side="left")

        ctk.CTkLabel(
            title_frame,
            text=f"({len(self.local_apks)} APKs available in repository)",
            font=("Inter", 12),
            text_color=theme.TEXT_MUTED
        ).pack(side="left", padx=10)

        # Controls & Search Strip
        ctrl_frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=20, pady=(0, 8))

        btn_all = ctk.CTkButton(
            ctrl_frame, text="Select All", width=85, height=28, font=("Inter", 11, "bold"),
            fg_color=theme.SURFACE_2, hover_color=theme.SURFACE_3,
            text_color=theme.CYAN_PRIMARY,
            command=lambda: self._toggle_install_all(True)
        )
        btn_all.pack(side="left", padx=(0, 6))

        btn_none = ctk.CTkButton(
            ctrl_frame, text="Deselect All", width=85, height=28, font=("Inter", 11, "bold"),
            fg_color=theme.SURFACE_2, hover_color=theme.SURFACE_3,
            text_color=theme.TEXT_MUTED,
            command=lambda: self._toggle_install_all(False)
        )
        btn_none.pack(side="left", padx=(0, 6))

        btn_refresh = ctk.CTkButton(
            ctrl_frame, text="🔄 Refresh", width=85, height=28, font=("Inter", 11, "bold"),
            fg_color=theme.SURFACE_2, hover_color=theme.SURFACE_3,
            text_color=theme.CYAN_PRIMARY,
            command=self._rescan_local_apks
        )
        btn_refresh.pack(side="left", padx=(0, 12))

        # Realtime Search Entry (Contains matching)
        self.install_search_entry = ctk.CTkEntry(
            ctrl_frame,
            placeholder_text="🔍 Search APKs (contains name, package)...",
            height=28,
            font=("Inter", 11),
            fg_color=theme.SURFACE_2,
            border_color=theme.BORDER_SLATE
        )
        self.install_search_entry.pack(side="right", fill="x", expand=True)
        if self.install_search_query:
            self.install_search_entry.insert(0, self.install_search_query)
        self.install_search_entry.bind("<KeyRelease>", self._on_install_search_change)

        # Action Button Bar & In-View Cancel (Anchored strictly to bottom FIRST so it never gets clipped)
        is_running = (self.current_operation == "install_apps")
        if is_running:
            d_text = "⏳ Loading... Preparing Install USB..."
            d_fg = theme.SURFACE_3
            d_text_color = theme.TEXT_MUTED
            d_state = "disabled"
        elif self.is_busy:
            d_text = f"🔒 System Busy ({self.current_operation_title or 'Operation in progress'})..."
            d_fg = theme.SURFACE_3
            d_text_color = theme.TEXT_MUTED
            d_state = "disabled"
        else:
            d_text = "⚡ PREPARE INSTALL USB"
            d_fg = theme.CYAN_PRIMARY
            d_text_color = theme.BG_BASE
            d_state = "normal"

        btn_bar = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        btn_bar.pack(side="bottom", fill="x", padx=20, pady=(0, 16))

        btn_deploy = ctk.CTkButton(
            btn_bar,
            text=d_text,
            height=44,
            font=("Space Grotesk", 14, "bold"),
            fg_color=d_fg,
            hover_color=d_fg if (is_running or self.is_busy) else theme.CYAN_HOVER,
            text_color=d_text_color,
            state=d_state,
            command=self._execute_prepare_install_usb
        )
        btn_deploy.pack(side="left", fill="x", expand=True)
        self.btn_install_apps = btn_deploy

        if is_running:
            btn_cancel = ctk.CTkButton(
                btn_bar, text="⏹ CANCEL OPERATION", height=44, width=170, font=("Space Grotesk", 12, "bold"),
                fg_color=theme.CRIMSON_DANGER, hover_color=theme.CRIMSON_HOVER,
                text_color=theme.TEXT_PRIMARY,
                command=self.cancel_current_operation
            )
            btn_cancel.pack(side="left", padx=(10, 0))

        # Scrollable container for cards (claims remaining area above button bar)
        self.install_scroll = ctk.CTkScrollableFrame(self.content_panel, fg_color="transparent")
        self.install_scroll.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 10))

        self._render_install_apk_cards()

    def _on_install_search_change(self, event=None):
        self.install_search_query = self.install_search_entry.get()
        self._render_install_apk_cards()

    def _render_install_apk_cards(self):
        for w in self.install_scroll.winfo_children():
            w.destroy()

        self.install_cards_map = {}
        q = self.install_search_query.strip().lower()
        matching_apks = [
            a for a in self.local_apks
            if not q or (q in a["display_name"].lower() or q in a["package"].lower() or q in a["filename"].lower())
        ]

        if not matching_apks:
            empty_box = ctk.CTkFrame(self.install_scroll, fg_color=theme.SURFACE_2, corner_radius=8)
            empty_box.pack(fill="x", pady=20)
            ctk.CTkLabel(
                empty_box,
                text=f"No applications matching '{q}' found.",
                font=("Inter", 12), text_color=theme.TEXT_MUTED
            ).pack(pady=16)
            return

        for a in matching_apks:
            f = a["filename"]
            pkg = a["package"]

            card = ctk.CTkFrame(self.install_scroll, fg_color=theme.SURFACE_2, corner_radius=8, border_width=1, border_color=theme.BORDER_SLATE)
            card.pack(fill="x", pady=4, padx=2)

            # Top Row: Checkbox + Title + Package + Size
            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=10, pady=(6, 2))

            sel_var = ctk.BooleanVar(value=self.selected_install_apks.get(f, False))

            chk = ctk.CTkCheckBox(
                top_row, text=a["display_name"], variable=sel_var,
                font=("Inter", 12, "bold"), text_color=theme.TEXT_PRIMARY,
                checkmark_color=theme.BG_BASE, fg_color=theme.CYAN_PRIMARY,
                command=lambda fname=f: self._on_install_chk_toggle(fname)
            )
            chk.pack(side="left")

            ctk.CTkLabel(
                top_row, text=f"({pkg})",
                font=("Consolas", 10), text_color=theme.TEXT_MUTED
            ).pack(side="left", padx=8)

            ctk.CTkLabel(
                top_row, text=f"{a['size_mb']} MB",
                font=("Consolas", 10, "bold"), text_color=theme.CYAN_PRIMARY
            ).pack(side="right")

            # Bottom Row: Target SegmentedButton + Auto Launch Checkbox + Force Portrait Checkbox + Block Boot Launch Checkbox
            bot_row = ctk.CTkFrame(card, fg_color="transparent")
            bot_row.pack(fill="x", padx=10, pady=(2, 6))

            ctk.CTkLabel(
                bot_row, text="Target:", font=("Inter", 10, "bold"), text_color=theme.TEXT_MUTED
            ).pack(side="left", padx=(0, 4))

            cur_target = "System App" if self.per_app_target.get(f, "user") == "system" else "User App"
            def _on_target_change(val, fname=f):
                self.per_app_target[fname] = "system" if val == "System App" else "user"

            target_seg = ctk.CTkSegmentedButton(
                bot_row, values=["User App", "System App"],
                width=155, height=24, font=("Inter", 10, "bold"),
                selected_color="#007B99",
                selected_hover_color=theme.CYAN_HOVER,
                unselected_color=theme.SURFACE_3,
                unselected_hover_color=theme.SURFACE_HOVER,
                text_color="#FFFFFF",
                command=_on_target_change
            )
            target_seg.set(cur_target)
            target_seg.pack(side="left", padx=(0, 16))

            # Auto Launch Checkbox (FIRST option before Force Portrait and Block Boot Launch, default: False / Unchecked, single selection)
            is_auto = (self.auto_launch_app_filename == f)
            auto_var = ctk.BooleanVar(value=is_auto)

            chk_auto = ctk.CTkCheckBox(
                bot_row, text="Auto Launch", variable=auto_var,
                font=("Inter", 10, "bold" if is_auto else "normal"),
                text_color=theme.MINT_SUCCESS if is_auto else theme.TEXT_PRIMARY,
                checkmark_color=theme.BG_BASE, fg_color=theme.MINT_SUCCESS,
                width=16, command=lambda fname=f: self._on_auto_launch_toggle(fname)
            )
            chk_auto.pack(side="left", padx=(0, 16))

            # Force Portrait checkbox (Default: False / Unchecked)
            port_var = ctk.BooleanVar(value=self.per_app_portrait.get(f, False))
            def _on_port_change(fname=f, v=port_var):
                self.per_app_portrait[fname] = v.get()

            chk_port = ctk.CTkCheckBox(
                bot_row, text="Force Portrait", variable=port_var,
                font=("Inter", 10), text_color=theme.TEXT_PRIMARY,
                checkmark_color=theme.BG_BASE, fg_color=theme.CYAN_PRIMARY,
                width=16, command=_on_port_change
            )
            chk_port.pack(side="left", padx=(0, 16))

            # Block Boot Launch checkbox (Default: False / Unchecked)
            boot_var = ctk.BooleanVar(value=self.per_app_boot.get(f, False))
            def _on_boot_change(fname=f, v=boot_var):
                self.per_app_boot[fname] = v.get()

            chk_boot = ctk.CTkCheckBox(
                bot_row, text="Block Boot Launch", variable=boot_var,
                font=("Inter", 10), text_color=theme.TEXT_PRIMARY,
                checkmark_color=theme.BG_BASE, fg_color=theme.CYAN_PRIMARY,
                width=16, command=_on_boot_change
            )
            chk_boot.pack(side="left")

            self.install_cards_map[f] = {
                "sel_var": sel_var,
                "auto_var": auto_var,
                "chk_auto": chk_auto,
            }

    def _on_install_chk_toggle(self, fname: str):
        target = self.install_cards_map.get(fname)
        if not target:
            return
        is_selected = target["sel_var"].get()
        self.selected_install_apks[fname] = is_selected
        if not is_selected and self.auto_launch_app_filename == fname:
            self.auto_launch_app_filename = None
            target["auto_var"].set(False)
            target["chk_auto"].configure(font=("Inter", 10, "normal"), text_color=theme.TEXT_PRIMARY)

    def _on_auto_launch_toggle(self, fname: str):
        target = self.install_cards_map.get(fname)
        if not target:
            return

        is_checked = target["auto_var"].get()
        if is_checked:
            self.auto_launch_app_filename = fname
            self.selected_install_apks[fname] = True
            target["sel_var"].set(True)

            # In-place state update across all cards: NO recomposition, NO flicker!
            for f_key, card_widgets in self.install_cards_map.items():
                if f_key == fname:
                    card_widgets["chk_auto"].configure(
                        font=("Inter", 10, "bold"),
                        text_color=theme.MINT_SUCCESS
                    )
                else:
                    card_widgets["auto_var"].set(False)
                    card_widgets["chk_auto"].configure(
                        font=("Inter", 10, "normal"),
                        text_color=theme.TEXT_PRIMARY
                    )
        else:
            if self.auto_launch_app_filename == fname:
                self.auto_launch_app_filename = None
            target["chk_auto"].configure(
                font=("Inter", 10, "normal"),
                text_color=theme.TEXT_PRIMARY
            )

    def _toggle_install_all(self, state: bool):
        q = self.install_search_query.strip().lower()
        for a in self.local_apks:
            f = a["filename"]
            if not q or (q in a["display_name"].lower() or q in a["package"].lower() or q in f.lower()):
                self.selected_install_apks[f] = state
                if not state and self.auto_launch_app_filename == f:
                    self.auto_launch_app_filename = None

                if hasattr(self, "install_cards_map") and f in self.install_cards_map:
                    item = self.install_cards_map[f]
                    item["sel_var"].set(state)
                    if not state:
                        item["auto_var"].set(False)
                        item["chk_auto"].configure(font=("Inter", 10, "normal"), text_color=theme.TEXT_PRIMARY)


    def _execute_prepare_install_usb(self):
        if not self._check_usb_ready(): return
        if self.is_busy:
            self.log_terminal("An operation is already in progress. Please wait.", "warn")
            return

        selected = []
        for a in self.local_apks:
            f = a["filename"]
            if self.selected_install_apks.get(f, False):
                selected.append({
                    "filename": f,
                    "path": a["path"],
                    "package": a["package"],
                    "display_name": a["display_name"],
                    "size_mb": a["size_mb"],
                    "force_portrait": self.per_app_portrait.get(f, False),
                    "install_target": self.per_app_target.get(f, "user"),
                    "block_boot": self.per_app_boot.get(f, False)
                })

        if not selected:
            self.log_terminal("No APKs selected for installation.", "warn")
            return

        auto_launch_pkg = ""
        if self.auto_launch_app_filename:
            target_app = next((a for a in selected if a["filename"] == self.auto_launch_app_filename), None)
            if target_app and target_app.get("package"):
                auto_launch_pkg = target_app["package"]
                self.log_terminal(f"Auto Launch target set: {target_app['display_name']} ({auto_launch_pkg})", "mint")

        self.is_busy = True
        self.current_operation = "install_apps"
        self.start_progress("Preparing Install Apps USB")
        self._refresh_active_view()

        def _worker():
            ok = payload_engine.prepare_install_apps_usb(
                self.current_usb.letter, selected,
                auto_launch_package=auto_launch_pkg,
                log_func=lambda m: self.log_terminal(m, "cyan"),
                progress_func=self.update_progress,
                cancel_check=self.cancel_event.is_set
            )
            was_cancelled = self.cancel_event.is_set()
            self.is_busy = False
            self.current_operation = ""
            if was_cancelled:
                self.log_terminal("Install Apps preparation cancelled by user.", "warn")
                self.finish_progress(False, "Install Apps Cancelled")
            elif ok:
                self.log_terminal("Install Apps USB Ready! Safe to plug into car.", "mint")
                self.finish_progress(True, "Install Apps USB Ready")
            else:
                self.log_terminal("Failed to prepare Install Apps USB.", "danger")
                self.finish_progress(False, "Failed to prepare Install Apps USB")
            self.after(0, self._refresh_active_view)

        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # 2. VIEW: UNINSTALL APPS (WITH REALTIME SUBSTRING SEARCH & SELECT ALL)
    # -----------------------------------------------------------------------
    def _view_uninstall_apps(self):
        title_frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(16, 6))

        ctk.CTkLabel(
            title_frame,
            text="🛡 SAFE UNINSTALL APPS",
            font=("Space Grotesk", 16, "bold"),
            text_color=theme.AMBER_WARN
        ).pack(side="left")

        # Safety Banner
        banner = ctk.CTkFrame(self.content_panel, fg_color=theme.SURFACE_2, corner_radius=8, border_width=1, border_color=theme.BORDER_SLATE)
        banner.pack(fill="x", padx=20, pady=(0, 6))

        ctk.CTkLabel(
            banner,
            text="🔒 STRICT SAFETY LOCK: Only apps originating from your vetted apks/ repository can be uninstalled.\nSearches and purges from BOTH User Apps (/data/app) and System Apps (/system/priv-app & /system/app).",
            font=("Inter", 11),
            text_color=theme.MINT_SUCCESS,
            justify="left"
        ).pack(padx=12, pady=6, anchor="w")

        # Controls & Search Strip
        ctrl_frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=20, pady=(0, 8))

        btn_all = ctk.CTkButton(
            ctrl_frame, text="Select All", width=85, height=28, font=("Inter", 11, "bold"),
            fg_color=theme.SURFACE_2, hover_color=theme.SURFACE_3,
            text_color=theme.CRIMSON_DANGER,
            command=lambda: self._toggle_uninstall_all(True)
        )
        btn_all.pack(side="left", padx=(0, 6))

        btn_none = ctk.CTkButton(
            ctrl_frame, text="Deselect All", width=85, height=28, font=("Inter", 11, "bold"),
            fg_color=theme.SURFACE_2, hover_color=theme.SURFACE_3,
            text_color=theme.TEXT_MUTED,
            command=lambda: self._toggle_uninstall_all(False)
        )
        btn_none.pack(side="left", padx=(0, 6))

        btn_refresh = ctk.CTkButton(
            ctrl_frame, text="🔄 Refresh", width=85, height=28, font=("Inter", 11, "bold"),
            fg_color=theme.SURFACE_2, hover_color=theme.SURFACE_3,
            text_color=theme.CYAN_PRIMARY,
            command=self._rescan_local_apks
        )
        btn_refresh.pack(side="left", padx=(0, 12))

        # Realtime Search Entry (Contains matching)
        self.uninstall_search_entry = ctk.CTkEntry(
            ctrl_frame,
            placeholder_text="🔍 Search Packages to Uninstall (contains name, package)...",
            height=28,
            font=("Inter", 11),
            fg_color=theme.SURFACE_2,
            border_color=theme.BORDER_SLATE
        )
        self.uninstall_search_entry.pack(side="right", fill="x", expand=True)
        if self.uninstall_search_query:
            self.uninstall_search_entry.insert(0, self.uninstall_search_query)
        self.uninstall_search_entry.bind("<KeyRelease>", self._on_uninstall_search_change)

        # Action Button Bar & In-View Cancel (Anchored strictly to bottom FIRST so it never gets clipped)
        is_running = (self.current_operation == "uninstall_apps")
        if is_running:
            d_text = "⏳ Loading... Preparing Safe Uninstall USB..."
            d_fg = theme.SURFACE_3
            d_text_color = theme.TEXT_MUTED
            d_state = "disabled"
        elif self.is_busy:
            d_text = f"🔒 System Busy ({self.current_operation_title or 'Operation in progress'})..."
            d_fg = theme.SURFACE_3
            d_text_color = theme.TEXT_MUTED
            d_state = "disabled"
        else:
            d_text = "🗑 PREPARE SAFE UNINSTALL USB"
            d_fg = theme.CRIMSON_DANGER
            d_text_color = theme.TEXT_PRIMARY
            d_state = "normal"

        btn_bar = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        btn_bar.pack(side="bottom", fill="x", padx=20, pady=(0, 16))

        btn_uninstall = ctk.CTkButton(
            btn_bar,
            text=d_text,
            height=44,
            font=("Space Grotesk", 14, "bold"),
            fg_color=d_fg,
            hover_color=d_fg if (is_running or self.is_busy) else theme.CRIMSON_HOVER,
            text_color=d_text_color,
            state=d_state,
            command=self._execute_prepare_uninstall_usb
        )
        btn_uninstall.pack(side="left", fill="x", expand=True)
        self.btn_uninstall_apps = btn_uninstall

        if is_running:
            btn_cancel = ctk.CTkButton(
                btn_bar, text="⏹ CANCEL OPERATION", height=44, width=170, font=("Space Grotesk", 12, "bold"),
                fg_color=theme.CRIMSON_DANGER, hover_color=theme.CRIMSON_HOVER,
                text_color=theme.TEXT_PRIMARY,
                command=self.cancel_current_operation
            )
            btn_cancel.pack(side="left", padx=(10, 0))

        # Scrollable container (claims remaining area above button bar)
        self.uninstall_scroll = ctk.CTkScrollableFrame(self.content_panel, fg_color="transparent")
        self.uninstall_scroll.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 10))

        self._render_uninstall_apk_rows()

    def _on_uninstall_search_change(self, event=None):
        self.uninstall_search_query = self.uninstall_search_entry.get()
        self._render_uninstall_apk_rows()

    def _render_uninstall_apk_rows(self):
        for w in self.uninstall_scroll.winfo_children():
            w.destroy()

        q = self.uninstall_search_query.strip().lower()
        matching_apks = [
            a for a in self.local_apks
            if a["package"] and (not q or (q in a["display_name"].lower() or q in a["package"].lower() or q in a["filename"].lower()))
        ]

        if not matching_apks:
            empty_box = ctk.CTkFrame(self.uninstall_scroll, fg_color=theme.SURFACE_2, corner_radius=8)
            empty_box.pack(fill="x", pady=20)
            ctk.CTkLabel(
                empty_box,
                text=f"No packages matching '{q}' found.",
                font=("Inter", 12), text_color=theme.TEXT_MUTED
            ).pack(pady=16)
            return

        for a in matching_apks:
            pkg = a["package"]
            row = ctk.CTkFrame(self.uninstall_scroll, fg_color=theme.SURFACE_2, corner_radius=8, height=36, border_width=1, border_color=theme.BORDER_SLATE)
            row.pack(fill="x", pady=3, padx=2)

            sel_var = ctk.BooleanVar(value=self.selected_uninstall_pkgs.get(pkg, False))
            def _on_chk(p=pkg, v=sel_var):
                self.selected_uninstall_pkgs[p] = v.get()

            chk = ctk.CTkCheckBox(
                row, text=a["display_name"], variable=sel_var,
                font=("Inter", 12, "bold"), text_color=theme.TEXT_PRIMARY,
                checkmark_color=theme.TEXT_PRIMARY, fg_color=theme.CRIMSON_DANGER,
                command=_on_chk
            )
            chk.pack(side="left", padx=10, pady=6)

            ctk.CTkLabel(
                row, text=f"({pkg})",
                font=("Consolas", 10), text_color=theme.TEXT_MUTED
            ).pack(side="left", padx=6)

    def _toggle_uninstall_all(self, state: bool):
        q = self.uninstall_search_query.strip().lower()
        for a in self.local_apks:
            pkg = a["package"]
            if not pkg: continue
            if not q or (q in a["display_name"].lower() or q in a["package"].lower() or q in a["filename"].lower()):
                self.selected_uninstall_pkgs[pkg] = state
        self._render_uninstall_apk_rows()

    def _execute_prepare_uninstall_usb(self):
        if not self._check_usb_ready(): return
        if self.is_busy:
            self.log_terminal("An operation is already in progress. Please wait.", "warn")
            return

        selected = [pkg for pkg, state in self.selected_uninstall_pkgs.items() if state]
        if not selected:
            self.log_terminal("No packages selected for uninstall.", "warn")
            return

        self.is_busy = True
        self.current_operation = "uninstall_apps"
        self.start_progress("Preparing Safe Uninstall Apps USB")
        self._refresh_active_view()

        def _worker():
            ok = payload_engine.prepare_uninstall_apps_usb(
                self.current_usb.letter, selected, self.allowed_packages,
                log_func=lambda m: self.log_terminal(m, "cyan"),
                progress_func=self.update_progress,
                cancel_check=self.cancel_event.is_set
            )
            was_cancelled = self.cancel_event.is_set()
            self.is_busy = False
            self.current_operation = ""
            if was_cancelled:
                self.log_terminal("Uninstall preparation cancelled by user.", "warn")
                self.finish_progress(False, "Uninstall Cancelled")
            elif ok:
                self.log_terminal("Safe Uninstall USB Ready! Plug into car to execute.", "mint")
                self.finish_progress(True, "Safe Uninstall USB Ready")
            else:
                self.log_terminal("Failed to prepare Uninstall USB.", "danger")
                self.finish_progress(False, "Failed to prepare Uninstall USB")
            self.after(0, self._refresh_active_view)

        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # 3. VIEW: INSTALL GMS
    # -----------------------------------------------------------------------
    def _view_install_gms(self):
        self._build_simple_action_card(
            title="🌐 INSTALL GOOGLE PLAY SERVICES (GMS)",
            desc="Injects the complete Google Play Services framework, Google Play Store, Google Services Framework, Google Account Manager, and enables voice recognition permissions.",
            badge="FRAMEWORK INJECTION",
            btn_text="🌐 PREPARE GMS INSTALL USB",
            btn_color=theme.CYAN_PRIMARY,
            action_handler=self._execute_install_gms,
            op_id="install_gms",
            loading_text="⏳ Loading... Preparing GMS Install USB..."
        )

    def _execute_install_gms(self):
        if not self._check_usb_ready(): return
        if self.is_busy:
            self.log_terminal("An operation is already in progress. Please wait.", "warn")
            return

        self.is_busy = True
        self.current_operation = "install_gms"
        self.start_progress("Preparing Google Play Services USB")
        self._refresh_active_view()

        def _worker():
            ok = payload_engine.prepare_install_gms_usb(
                self.current_usb.letter, GMS_DIR,
                log_func=lambda m: self.log_terminal(m, "cyan"),
                progress_func=self.update_progress,
                cancel_check=self.cancel_event.is_set
            )
            was_cancelled = self.cancel_event.is_set()
            self.is_busy = False
            self.current_operation = ""
            if was_cancelled:
                self.log_terminal("GMS Install preparation cancelled by user.", "warn")
                self.finish_progress(False, "GMS Install Cancelled")
            elif ok:
                self.log_terminal("GMS Install USB Ready!", "mint")
                self.finish_progress(True, "GMS Install USB Ready")
            else:
                self.log_terminal("Failed to prepare GMS Install USB.", "danger")
                self.finish_progress(False, "Failed to prepare GMS Install USB")
            self.after(0, self._refresh_active_view)

        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # 4. VIEW: UNINSTALL GMS
    # -----------------------------------------------------------------------
    def _view_uninstall_gms(self):
        self._build_simple_action_card(
            title="🧹 UNINSTALL GOOGLE PLAY SERVICES (CLEAN PURGE)",
            desc="Scrubs all Google Play Services packages, account tokens, sync databases, and removes voice recognizer permissions from /system.",
            badge="CLEAN PURGE",
            btn_text="🧹 PREPARE GMS PURGE USB",
            btn_color=theme.CYAN_PRIMARY,
            action_handler=self._execute_uninstall_gms,
            op_id="uninstall_gms",
            loading_text="⏳ Loading... Preparing GMS Purge USB..."
        )

    def _execute_uninstall_gms(self):
        if not self._check_usb_ready(): return
        if self.is_busy:
            self.log_terminal("An operation is already in progress. Please wait.", "warn")
            return

        self.is_busy = True
        self.current_operation = "uninstall_gms"
        self.start_progress("Preparing GMS Clean Purge USB")
        self._refresh_active_view()

        def _worker():
            ok = payload_engine.prepare_uninstall_gms_usb(
                self.current_usb.letter,
                log_func=lambda m: self.log_terminal(m, "cyan"),
                progress_func=self.update_progress,
                cancel_check=self.cancel_event.is_set
            )
            was_cancelled = self.cancel_event.is_set()
            self.is_busy = False
            self.current_operation = ""
            if was_cancelled:
                self.log_terminal("GMS Purge preparation cancelled by user.", "warn")
                self.finish_progress(False, "GMS Purge Cancelled")
            elif ok:
                self.log_terminal("GMS Purge USB Ready!", "mint")
                self.finish_progress(True, "GMS Purge USB Ready")
            else:
                self.log_terminal("Failed to prepare GMS Purge USB.", "danger")
                self.finish_progress(False, "Failed to prepare GMS Purge USB")
            self.after(0, self._refresh_active_view)

        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # 5. VIEW: OPEN SETTINGS
    # -----------------------------------------------------------------------
    def _view_open_settings(self):
        self._build_simple_action_card(
            title="⚙️ LAUNCH ANDROID SETTINGS",
            desc="Creates a fast USB trigger that immediately pops open the hidden stock Android Settings panel on the car screen.",
            badge="SYSTEM UTILITY",
            btn_text="⚙️ PREPARE OPEN SETTINGS USB",
            btn_color=theme.CYAN_PRIMARY,
            action_handler=self._execute_open_settings,
            op_id="open_settings",
            loading_text="⏳ Loading... Preparing Open Settings USB..."
        )

    def _execute_open_settings(self):
        if not self._check_usb_ready(): return
        if self.is_busy:
            self.log_terminal("An operation is already in progress. Please wait.", "warn")
            return

        self.is_busy = True
        self.current_operation = "open_settings"
        self.start_progress("Preparing Open Android Settings USB")
        self._refresh_active_view()

        def _worker():
            ok = payload_engine.prepare_open_settings_usb(
                self.current_usb.letter,
                log_func=lambda m: self.log_terminal(m, "cyan"),
                progress_func=self.update_progress,
                cancel_check=self.cancel_event.is_set
            )
            was_cancelled = self.cancel_event.is_set()
            self.is_busy = False
            self.current_operation = ""
            if was_cancelled:
                self.log_terminal("Open Settings preparation cancelled by user.", "warn")
                self.finish_progress(False, "Open Settings Cancelled")
            elif ok:
                self.log_terminal("Open Settings USB Ready!", "mint")
                self.finish_progress(True, "Open Settings USB Ready")
            else:
                self.log_terminal("Failed to prepare Open Settings USB.", "danger")
                self.finish_progress(False, "Failed to prepare Open Settings USB")
            self.after(0, self._refresh_active_view)

        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # VIEW: OPEN APPLICATION ON CAR
    # -----------------------------------------------------------------------
    def _view_open_app(self):
        title_frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(16, 6))

        ctk.CTkLabel(
            title_frame,
            text="🚀 LAUNCH APPLICATION ON CAR",
            font=("Space Grotesk", 16, "bold"),
            text_color=theme.CYAN_PRIMARY
        ).pack(side="left")

        # Instruction Banner
        banner = ctk.CTkFrame(self.content_panel, fg_color=theme.SURFACE_2, corner_radius=8, border_width=1, border_color=theme.BORDER_SLATE)
        banner.pack(fill="x", padx=20, pady=(0, 6))

        ctk.CTkLabel(
            banner,
            text="💡 Select an application below to generate an auto-launch USB payload.\nWhen plugged into the vehicle, the script brings the chosen application to the foreground immediately.",
            font=("Inter", 11),
            text_color=theme.TEXT_MUTED,
            justify="left"
        ).pack(padx=12, pady=6, anchor="w")

        # Controls & Search Strip
        ctrl_frame = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=20, pady=(0, 8))

        self.open_app_search_entry = ctk.CTkEntry(
            ctrl_frame,
            placeholder_text="🔍 Search Apps to Open (name or package)...",
            height=28,
            font=("Inter", 11),
            fg_color=theme.SURFACE_2,
            border_color=theme.BORDER_SLATE
        )
        self.open_app_search_entry.pack(side="left", fill="x", expand=True)
        if self.open_app_search_query:
            self.open_app_search_entry.insert(0, self.open_app_search_query)
        self.open_app_search_entry.bind("<KeyRelease>", self._on_open_app_search_change)

        btn_refresh = ctk.CTkButton(
            ctrl_frame,
            text="🔄 Refresh",
            width=85,
            height=28,
            font=("Inter", 11, "bold"),
            fg_color=theme.SURFACE_2,
            hover_color=theme.SURFACE_3,
            text_color=theme.CYAN_PRIMARY,
            command=self._rescan_local_apks
        )
        btn_refresh.pack(side="right", padx=(8, 0))

        # Default to first available app if none is selected, so the button is immediately ready & enabled
        if (not getattr(self, "selected_open_app_pkg", None) or self.selected_open_app_pkg not in self.allowed_packages) and self.local_apks:
            first_pkg = next((a["package"] for a in self.local_apks if a.get("package")), "")
            if first_pkg:
                self.selected_open_app_pkg = first_pkg

        # Action Button Bar (Anchored strictly to bottom FIRST so it never disappears)
        is_running = (self.current_operation == "open_app")
        selected_pkg = getattr(self, "selected_open_app_pkg", "")
        selected_app_info = next((a for a in self.local_apks if a["package"] == selected_pkg), None)
        selected_title = selected_app_info["display_name"] if selected_app_info else ""

        if is_running:
            d_text = f"⏳ Loading... Preparing Launch USB for {selected_title}..."
            d_fg = theme.SURFACE_3
            d_hover = theme.SURFACE_3
            d_text_color = theme.TEXT_MUTED
            d_state = "disabled"
        elif self.is_busy:
            d_text = f"🔒 System Busy ({self.current_operation_title or 'Operation in progress'})..."
            d_fg = theme.SURFACE_3
            d_hover = theme.SURFACE_3
            d_text_color = theme.TEXT_MUTED
            d_state = "disabled"
        elif not selected_pkg:
            d_text = "👆 SELECT AN APP FROM THE LIST ABOVE TO PREPARE LAUNCH USB"
            d_fg = theme.SURFACE_2
            d_hover = theme.SURFACE_2
            d_text_color = theme.TEXT_MUTED
            d_state = "disabled"
        else:
            d_text = f"🚀 PREPARE LAUNCH USB FOR: {selected_title.upper()}"
            d_fg = theme.CYAN_PRIMARY
            d_hover = theme.CYAN_HOVER
            d_text_color = theme.BG_BASE
            d_state = "normal"

        btn_bar = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        btn_bar.pack(side="bottom", fill="x", padx=20, pady=(0, 16))

        self.btn_open_app_launch = ctk.CTkButton(
            btn_bar,
            text=d_text,
            height=44,
            font=("Space Grotesk", 14, "bold"),
            fg_color=d_fg,
            hover_color=d_hover,
            text_color=d_text_color,
            state=d_state,
            command=self._execute_prepare_open_app_usb
        )
        self.btn_open_app_launch.pack(side="left", fill="x", expand=True)

        if is_running:
            btn_cancel = ctk.CTkButton(
                btn_bar, text="⏹ CANCEL OPERATION", height=44, width=170, font=("Space Grotesk", 12, "bold"),
                fg_color=theme.CRIMSON_DANGER, hover_color=theme.CRIMSON_HOVER,
                text_color=theme.TEXT_PRIMARY,
                command=self.cancel_current_operation
            )
            btn_cancel.pack(side="left", padx=(10, 0))

        # Scrollable container for app rows (claims remaining area above button bar)
        self.open_app_scroll = ctk.CTkScrollableFrame(self.content_panel, fg_color="transparent")
        self.open_app_scroll.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 10))

        self.open_app_row_items = {}
        self._render_open_app_rows()

    def _on_open_app_search_change(self, event=None):
        self.open_app_search_query = self.open_app_search_entry.get()
        self._render_open_app_rows()

    def _select_open_app(self, pkg_name: str):
        # Strict single selection enforcement: only ONE app can be selected at a time
        self.selected_open_app_pkg = pkg_name

        for p, item in self.open_app_row_items.items():
            is_cur = (p == pkg_name)
            item["var"].set(is_cur)
            if hasattr(item["row"], "winfo_exists") and item["row"].winfo_exists():
                item["row"].configure(
                    fg_color=theme.CYAN_ALPHA_15 if is_cur else theme.SURFACE_2,
                    border_color=theme.CYAN_PRIMARY if is_cur else theme.BORDER_SLATE
                )
                item["chk"].configure(
                    text_color=theme.CYAN_PRIMARY if is_cur else theme.TEXT_PRIMARY
                )
                item["size_lbl"].configure(
                    text_color=theme.CYAN_PRIMARY if is_cur else theme.TEXT_MUTED
                )

        self._update_open_app_launch_button()

    def _update_open_app_launch_button(self):
        if not hasattr(self, "btn_open_app_launch") or not self.btn_open_app_launch.winfo_exists():
            return
        if self.is_busy or self.current_operation == "open_app":
            return

        if self.selected_open_app_pkg:
            selected_app_info = next((a for a in self.local_apks if a["package"] == self.selected_open_app_pkg), None)
            selected_title = selected_app_info["display_name"] if selected_app_info else self.selected_open_app_pkg
            self.btn_open_app_launch.configure(
                text=f"🚀 PREPARE LAUNCH USB FOR: {selected_title.upper()}",
                fg_color=theme.CYAN_PRIMARY,
                hover_color=theme.CYAN_HOVER,
                text_color=theme.BG_BASE,
                state="normal"
            )
        else:
            self.btn_open_app_launch.configure(
                text="👆 SELECT AN APP FROM THE LIST ABOVE TO PREPARE LAUNCH USB",
                fg_color=theme.SURFACE_2,
                hover_color=theme.SURFACE_2,
                text_color=theme.TEXT_MUTED,
                state="disabled"
            )

    def _render_open_app_rows(self):
        for w in self.open_app_scroll.winfo_children():
            w.destroy()

        self.open_app_row_items = {}
        q = self.open_app_search_query.strip().lower()
        matching_apks = [
            a for a in self.local_apks
            if a.get("package") and (not q or q in a["display_name"].lower() or q in a["package"].lower() or q in a["filename"].lower())
        ]

        if not matching_apks:
            empty_box = ctk.CTkFrame(self.open_app_scroll, fg_color=theme.SURFACE_2, corner_radius=8)
            empty_box.pack(fill="x", pady=20)
            ctk.CTkLabel(
                empty_box,
                text=f"No matching applications found.",
                font=("Inter", 12), text_color=theme.TEXT_MUTED
            ).pack(pady=16)
            return

        for a in matching_apks:
            pkg = a["package"]
            is_selected = (self.selected_open_app_pkg == pkg)

            # Compact row matching Safe Uninstall exactly (height=36, corner_radius=8, border_width=1)
            row = ctk.CTkFrame(
                self.open_app_scroll,
                fg_color=theme.CYAN_ALPHA_15 if is_selected else theme.SURFACE_2,
                corner_radius=8,
                height=36,
                border_width=1,
                border_color=theme.CYAN_PRIMARY if is_selected else theme.BORDER_SLATE
            )
            row.pack(fill="x", pady=3, padx=2)

            sel_var = ctk.BooleanVar(value=is_selected)

            chk = ctk.CTkCheckBox(
                row,
                text=a["display_name"],
                variable=sel_var,
                font=("Inter", 12, "bold"),
                text_color=theme.CYAN_PRIMARY if is_selected else theme.TEXT_PRIMARY,
                checkmark_color=theme.BG_BASE,
                fg_color=theme.CYAN_PRIMARY,
                command=lambda p=pkg: self._select_open_app(p)
            )
            chk.pack(side="left", padx=10, pady=6)

            pkg_lbl = ctk.CTkLabel(
                row,
                text=f"({pkg})",
                font=("Consolas", 10),
                text_color=theme.TEXT_MUTED
            )
            pkg_lbl.pack(side="left", padx=6)

            size_lbl = ctk.CTkLabel(
                row,
                text=f"{a['size_mb']} MB",
                font=("Consolas", 10, "bold"),
                text_color=theme.CYAN_PRIMARY if is_selected else theme.TEXT_MUTED
            )
            size_lbl.pack(side="right", padx=10)

            self.open_app_row_items[pkg] = {
                "row": row,
                "var": sel_var,
                "chk": chk,
                "size_lbl": size_lbl,
            }

            # Allow clicking anywhere on the row to select this app
            def _bind_row(r_widget, p=pkg):
                def _click(e):
                    self._select_open_app(p)
                r_widget.bind("<Button-1>", _click)

            _bind_row(row, pkg)
            _bind_row(pkg_lbl, pkg)
            _bind_row(size_lbl, pkg)


    def _execute_prepare_open_app_usb(self):
        if not self._check_usb_ready(): return
        if not self.selected_open_app_pkg:
            self.log_terminal("Please select an application to open.", "warn")
            return
        if self.is_busy:
            self.log_terminal("An operation is already in progress. Please wait.", "warn")
            return

        selected_app_info = next((a for a in self.local_apks if a["package"] == self.selected_open_app_pkg), None)
        app_title = selected_app_info["display_name"] if selected_app_info else self.selected_open_app_pkg
        pkg = self.selected_open_app_pkg

        self.is_busy = True
        self.current_operation = "open_app"
        self.start_progress(f"Preparing Launch USB for {app_title}")
        self._refresh_active_view()

        def _worker():
            ok = payload_engine.prepare_open_app_usb(
                self.current_usb.letter,
                package_name=pkg,
                app_name=app_title,
                log_func=lambda m: self.log_terminal(m, "cyan"),
                progress_func=self.update_progress,
                cancel_check=self.cancel_event.is_set
            )
            was_cancelled = self.cancel_event.is_set()
            self.is_busy = False
            self.current_operation = ""
            if was_cancelled:
                self.log_terminal(f"Launch USB preparation cancelled for {app_title}.", "warn")
                self.finish_progress(False, "Open App Cancelled")
            elif ok:
                self.log_terminal(f"Launch USB Ready for {app_title}! Plug into car to launch.", "mint")
                self.finish_progress(True, f"Open {app_title} USB Ready")
            else:
                self.log_terminal(f"Failed to prepare Launch USB for {app_title}.", "danger")
                self.finish_progress(False, "Failed to prepare Open App USB")
            self.after(0, self._refresh_active_view)

        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # VIEW: DISABLE FACTORY LAUNCHER
    # -----------------------------------------------------------------------
    def _view_disable_launcher(self):
        self._build_simple_action_card(
            title="🚫 DISABLE FACTORY LAUNCHER",
            desc="Creates a USB payload to freeze (disable) the stock Dongfeng system launcher (com.qinggan.app.launcher).\nPrevents the factory home screen from overriding custom launchers (such as AGAMA Car Launcher).",
            badge="LAUNCHER CONTROL",
            btn_text="🚫 PREPARE DISABLE LAUNCHER USB",
            btn_color=theme.AMBER_WARN,
            action_handler=self._execute_disable_launcher,
            op_id="disable_launcher",
            loading_text="⏳ Loading... Preparing Disable Launcher USB..."
        )

    def _execute_disable_launcher(self):
        if not self._check_usb_ready(): return
        if self.is_busy:
            self.log_terminal("An operation is already in progress. Please wait.", "warn")
            return

        self.is_busy = True
        self.current_operation = "disable_launcher"
        self.start_progress("Preparing Disable Launcher USB")
        self._refresh_active_view()

        def _worker():
            ok = payload_engine.prepare_disable_launcher_usb(
                self.current_usb.letter,
                log_func=lambda m: self.log_terminal(m, "cyan"),
                progress_func=self.update_progress,
                cancel_check=self.cancel_event.is_set
            )
            was_cancelled = self.cancel_event.is_set()
            self.is_busy = False
            self.current_operation = ""
            if was_cancelled:
                self.log_terminal("Disable Launcher preparation cancelled by user.", "warn")
                self.finish_progress(False, "Disable Launcher Cancelled")
            elif ok:
                self.log_terminal("Disable Launcher USB Ready! Plug into car to freeze stock launcher.", "mint")
                self.finish_progress(True, "Disable Launcher USB Ready")
            else:
                self.log_terminal("Failed to prepare Disable Launcher USB.", "danger")
                self.finish_progress(False, "Failed to prepare Disable Launcher USB")
            self.after(0, self._refresh_active_view)

        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # VIEW: ENABLE FACTORY LAUNCHER
    # -----------------------------------------------------------------------
    def _view_enable_launcher(self):
        self._build_simple_action_card(
            title="✅ ENABLE FACTORY LAUNCHER",
            desc="Creates a USB payload to unfreeze (enable) the stock Dongfeng system launcher (com.qinggan.app.launcher).\nRestores the original factory home screen to active status.",
            badge="LAUNCHER CONTROL",
            btn_text="✅ PREPARE ENABLE LAUNCHER USB",
            btn_color=theme.MINT_SUCCESS,
            action_handler=self._execute_enable_launcher,
            op_id="enable_launcher",
            loading_text="⏳ Loading... Preparing Enable Launcher USB..."
        )

    def _execute_enable_launcher(self):
        if not self._check_usb_ready(): return
        if self.is_busy:
            self.log_terminal("An operation is already in progress. Please wait.", "warn")
            return

        self.is_busy = True
        self.current_operation = "enable_launcher"
        self.start_progress("Preparing Enable Launcher USB")
        self._refresh_active_view()

        def _worker():
            ok = payload_engine.prepare_enable_launcher_usb(
                self.current_usb.letter,
                log_func=lambda m: self.log_terminal(m, "cyan"),
                progress_func=self.update_progress,
                cancel_check=self.cancel_event.is_set
            )
            was_cancelled = self.cancel_event.is_set()
            self.is_busy = False
            self.current_operation = ""
            if was_cancelled:
                self.log_terminal("Enable Launcher preparation cancelled by user.", "warn")
                self.finish_progress(False, "Enable Launcher Cancelled")
            elif ok:
                self.log_terminal("Enable Launcher USB Ready! Plug into car to unfreeze stock launcher.", "mint")
                self.finish_progress(True, "Enable Launcher USB Ready")
            else:
                self.log_terminal("Failed to prepare Enable Launcher USB.", "danger")
                self.finish_progress(False, "Failed to prepare Enable Launcher USB")
            self.after(0, self._refresh_active_view)

        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # VIEW: RESTART SCREEN
    # -----------------------------------------------------------------------
    def _view_reboot_screen(self):
        self._build_simple_action_card(
            title="🔄 RESTART INFOTAINMENT SCREEN",
            desc="Creates a fast USB trigger to safely reboot / restart the car's Android infotainment unit.\nUseful for restarting the screen without turning off the car or disconnecting power.",
            badge="POWER UTILITY",
            btn_text="🔄 PREPARE RESTART SCREEN USB",
            btn_color=theme.CYAN_PRIMARY,
            action_handler=self._execute_reboot_screen,
            op_id="reboot_screen",
            loading_text="⏳ Loading... Preparing Restart Screen USB..."
        )

    def _execute_reboot_screen(self):
        if not self._check_usb_ready(): return
        if self.is_busy:
            self.log_terminal("An operation is already in progress. Please wait.", "warn")
            return

        self.is_busy = True
        self.current_operation = "reboot_screen"
        self.start_progress("Preparing Restart Infotainment Screen USB")
        self._refresh_active_view()

        def _worker():
            ok = payload_engine.prepare_reboot_screen_usb(
                self.current_usb.letter,
                log_func=lambda m: self.log_terminal(m, "cyan"),
                progress_func=self.update_progress,
                cancel_check=self.cancel_event.is_set
            )
            was_cancelled = self.cancel_event.is_set()
            self.is_busy = False
            self.current_operation = ""
            if was_cancelled:
                self.log_terminal("Restart Screen preparation cancelled by user.", "warn")
                self.finish_progress(False, "Restart Screen Cancelled")
            elif ok:
                self.log_terminal("Restart Screen USB Ready! Plug into car to reboot head unit.", "mint")
                self.finish_progress(True, "Restart Screen USB Ready")
            else:
                self.log_terminal("Failed to prepare Restart Screen USB.", "danger")
                self.finish_progress(False, "Failed to prepare Restart Screen USB")
            self.after(0, self._refresh_active_view)

        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # 6. VIEW: BACKUP (CAR TO USB + AUTO PC SYNC)
    # -----------------------------------------------------------------------
    def _view_backup(self):
        for widget in self.content_panel.winfo_children():
            widget.destroy()

        pad = ctk.CTkScrollableFrame(self.content_panel, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=12, pady=(12, 10))

        ctk.CTkLabel(
            pad, text="💾 SYSTEM & DATA BACKUP",
            font=("Space Grotesk", 18, "bold"), text_color=theme.CYAN_PRIMARY
        ).pack(anchor="w", padx=6)

        ctk.CTkLabel(
            pad,
            text="Extracts personal state from your car into your USB drive.\n"
                 "Create a 1:1 Personal Clone for yourself, or a clean Community Preset to share with other car owners without leaking sensitive accounts.",
            font=("Inter", 12), text_color=theme.TEXT_MUTED, justify="left"
        ).pack(anchor="w", padx=6, pady=(4, 14))

        # Step 1 Card: Configure & Prepare Car Backup USB
        c1 = ctk.CTkFrame(pad, fg_color=theme.SURFACE_2, corner_radius=10, border_width=1, border_color=theme.BORDER_SLATE)
        c1.pack(fill="x", pady=6, padx=6)

        ctk.CTkLabel(c1, text="STEP 1: CONFIGURE & PREPARE BACKUP USB", font=("Space Grotesk", 13, "bold"), text_color=theme.CYAN_PRIMARY).pack(anchor="w", padx=16, pady=(12, 4))
        ctk.CTkLabel(c1, text="Choose your backup scope and stage the extraction payload to your USB drive.", font=("Inter", 11), text_color=theme.TEXT_MUTED).pack(anchor="w", padx=16, pady=(0, 10))

        # Mode Selector Segmented Button
        modes = ["🔒 Personal Private (1:1 Clone)", "🌐 Community Shared Preset"]
        if self.backup_mode_var.get() not in modes:
            self.backup_mode_var.set(modes[0])

        cur_mode = self.backup_mode_var.get()
        is_community = ("Community" in cur_mode)

        def _on_mode_change(val):
            self.backup_mode_var.set(val)
            self._refresh_active_view()

        seg = ctk.CTkSegmentedButton(
            c1,
            values=modes,
            variable=self.backup_mode_var,
            width=460, height=34, font=("Space Grotesk", 12, "bold"),
            selected_color="#007B99",
            selected_hover_color=theme.CYAN_HOVER,
            unselected_color=theme.SURFACE_3,
            unselected_hover_color=theme.SURFACE_HOVER,
            text_color="#FFFFFF",
            command=_on_mode_change
        )
        seg.set(cur_mode)
        seg.pack(anchor="w", padx=16, pady=(0, 10))

        # Contextual info box based on mode
        hint_box = ctk.CTkFrame(c1, fg_color=theme.SURFACE_1, corner_radius=8, border_width=1, border_color=theme.BORDER_CYAN if is_community else theme.BORDER_SLATE)
        hint_box.pack(fill="x", padx=16, pady=(0, 10))

        if is_community:
            ctk.CTkLabel(
                hint_box,
                text="🌐 Community Shared Preset (Safe for Distribution):\n"
                     "• Zero-Leakage: Completely scrubs Google accounts, Wi-Fi passwords, and paired Bluetooth devices.\n"
                     "• Captured Elements: Custom Launchers (AGAMA/Lico), app widgets, installed third-party apps & custom settings.\n"
                     "• Safe for Sharing: Other drivers can safely restore this preset without wiping or corrupting their own accounts.",
                font=("Inter", 11), text_color=theme.CYAN_PRIMARY, justify="left"
            ).pack(anchor="w", padx=14, pady=8)

            meta_row = ctk.CTkFrame(c1, fg_color="transparent")
            meta_row.pack(fill="x", padx=16, pady=(0, 10))

            ctk.CTkLabel(meta_row, text="Preset Name:", font=("Inter", 11, "bold"), text_color=theme.TEXT_PRIMARY).pack(side="left", padx=(0, 6))
            ent_pname = ctk.CTkEntry(
                meta_row, textvariable=self.backup_preset_name_var,
                placeholder_text="e.g. Agama Cyber Dark Edition",
                width=240, height=32, font=("Inter", 11)
            )
            ent_pname.pack(side="left", padx=(0, 16))

            ctk.CTkLabel(meta_row, text="Author / Creator:", font=("Inter", 11, "bold"), text_color=theme.TEXT_PRIMARY).pack(side="left", padx=(0, 6))
            ent_author = ctk.CTkEntry(
                meta_row, textvariable=self.backup_author_var,
                placeholder_text="e.g. Abdo FX",
                width=170, height=32, font=("Inter", 11)
            )
            ent_author.pack(side="left")
        else:
            ctk.CTkLabel(
                hint_box,
                text="🔒 Personal Private Backup (1:1 Complete Vehicle State):\n"
                     "• Full Image: Preserves your Google accounts, synced accounts, saved Wi-Fi networks, paired Bluetooth, apps & settings.\n"
                     "• Disaster Recovery: Intended solely for personal restoration back to this exact car.",
                font=("Inter", 11), text_color=theme.TEXT_MUTED, justify="left"
            ).pack(anchor="w", padx=14, pady=8)

        # Single Checkbox for User Media
        media_row = ctk.CTkFrame(c1, fg_color="transparent")
        media_row.pack(fill="x", padx=16, pady=(0, 12))

        chk_media = ctk.CTkCheckBox(
            media_row,
            text="Include User Files & Media (/sdcard, Music, Downloads)",
            variable=self.backup_media_var,
            font=("Inter", 11, "bold"),
            fg_color=theme.CYAN_PRIMARY,
            hover_color=theme.CYAN_HOVER,
            text_color=theme.TEXT_PRIMARY
        )
        chk_media.pack(anchor="w")

        ctk.CTkLabel(
            media_row,
            text="  (Recommended: Unchecked by default. Skipping /sdcard keeps backup fast ~30s (~250 MB). Check only if you need media files ~4 GB+)",
            font=("Inter", 10), text_color=theme.TEXT_MUTED
        ).pack(anchor="w", padx=(24, 0), pady=(2, 0))

        # Button Bar for Step 1
        is_prep_running = (self.current_operation == "prepare_backup")
        btn_bar1 = ctk.CTkFrame(c1, fg_color="transparent")
        btn_bar1.pack(anchor="w", padx=16, pady=(0, 14))

        if is_prep_running:
            b1_text = "⏳ Loading... Preparing Backup USB..."
            b1_fg = theme.SURFACE_3
            b1_state = "disabled"
            b1_text_color = theme.TEXT_MUTED
        elif self.is_busy:
            b1_text = f"🔒 System Busy ({self.current_operation_title or 'In progress'})"
            b1_fg = theme.SURFACE_3
            b1_state = "disabled"
            b1_text_color = theme.TEXT_MUTED
        else:
            btn_scope = "COMMUNITY PRESET" if is_community else "PERSONAL BACKUP"
            b1_text = f"💾 PREPARE {btn_scope} USB"
            b1_fg = theme.CYAN_PRIMARY
            b1_state = "normal"
            b1_text_color = theme.BG_BASE

        self.btn_prep_backup = ctk.CTkButton(
            btn_bar1,
            text=b1_text,
            height=40, font=("Space Grotesk", 12, "bold"),
            fg_color=b1_fg,
            hover_color=b1_fg if (is_prep_running or self.is_busy) else theme.CYAN_HOVER,
            text_color=b1_text_color,
            state=b1_state,
            command=self._execute_prepare_backup_usb
        )
        self.btn_prep_backup.pack(side="left")

        if is_prep_running:
            btn_cancel_prep = ctk.CTkButton(
                btn_bar1, text="⏹ CANCEL OPERATION", height=40, width=170, font=("Space Grotesk", 12, "bold"),
                fg_color=theme.CRIMSON_DANGER, hover_color=theme.CRIMSON_HOVER,
                text_color=theme.TEXT_PRIMARY,
                command=self.cancel_current_operation
            )
            btn_cancel_prep.pack(side="left", padx=(10, 0))

        # Step 2 Card: PC Vault Sync
        c2 = ctk.CTkFrame(pad, fg_color=theme.SURFACE_2, corner_radius=10, border_width=1, border_color=theme.BORDER_SLATE)
        c2.pack(fill="x", pady=(6, 20), padx=6)

        ctk.CTkLabel(c2, text="STEP 2: AUTO-SYNC USB BACKUP TO PC VAULT", font=("Space Grotesk", 13, "bold"), text_color=theme.MINT_SUCCESS).pack(anchor="w", padx=16, pady=(12, 4))

        usb_has_b = self.current_usb and self.current_usb.has_backup
        already_vaulted = find_existing_vault_backup(self.current_usb.letter, BACKUPS_DIR) if usb_has_b else ""

        is_sync_running = (self.current_operation == "sync_vault")
        if is_sync_running:
            status_txt = "Syncing car backup snapshot to PC Vault in progress..."
            status_color = theme.CYAN_PRIMARY
            btn_txt = "⏳ Syncing Backup to PC Vault..."
            btn_color = theme.SURFACE_3
            btn_hover = theme.SURFACE_3
            btn_text_color = theme.TEXT_MUTED
            btn_state = "disabled"
        elif self.is_busy:
            status_txt = f"System busy with another operation: {self.current_operation_title or 'Please wait'}."
            status_color = theme.TEXT_MUTED
            btn_txt = f"🔒 System Busy ({self.current_operation_title or 'In progress'})"
            btn_color = theme.SURFACE_3
            btn_hover = theme.SURFACE_3
            btn_text_color = theme.TEXT_MUTED
            btn_state = "disabled"
        elif not usb_has_b:
            if getattr(self.current_usb, "is_restore_ready", False):
                status_txt = f"USB ({self.current_usb.letter if self.current_usb else 'N/A'}) is prepared with a Restore Payload for the car.\nPlug into the car to execute restore. (No new car backup to sync)."
                status_color = theme.CYAN_PRIMARY
            else:
                status_txt = "No completed backup currently detected on USB. Plug in the USB after taking the car backup."
                status_color = theme.TEXT_MUTED
            btn_txt = "📥 SYNC USB BACKUP TO PC VAULT (WITH PROGRESS)"
            btn_color = theme.SURFACE_3
            btn_hover = theme.SURFACE_3
            btn_text_color = theme.TEXT_MUTED
            btn_state = "disabled"
        elif already_vaulted:
            folder_bname = os.path.basename(already_vaulted)
            b_info = get_usb_backup_info(self.current_usb.letter)
            b_type_desc = "Community Preset" if b_info.get("backup_type") == "COMMUNITY" else "Personal Backup"
            status_txt = f"✓ This {b_type_desc} is ALREADY safely stored in PC Vault:\n  Folder: {folder_bname} (Date: {self.current_usb.backup_date})"
            btn_txt = f"✓ ALREADY VAULTED ({folder_bname}) — Click to Re-Sync"
            btn_color = theme.SURFACE_3
            btn_hover = theme.SURFACE_2
            btn_text_color = theme.CYAN_PRIMARY
            btn_state = "normal"
            status_color = theme.MINT_SUCCESS
        else:
            b_info = get_usb_backup_info(self.current_usb.letter)
            if b_info.get("backup_type") == "COMMUNITY":
                p_desc = f" [{b_info.get('preset_name') or 'Community Preset'}]"
                if b_info.get("author"):
                    p_desc += f" by {b_info.get('author')}"
                status_txt = f"★ New Community Preset{p_desc} Detected on USB ({self.current_usb.letter})! Ready to save to PC Vault."
            else:
                status_txt = f"★ New Personal Car Backup Detected on USB ({self.current_usb.letter})! Ready to save to PC Vault."
            btn_txt = "📥 SYNC USB BACKUP TO PC VAULT (WITH PROGRESS)"
            btn_color = theme.MINT_SUCCESS
            btn_hover = theme.MINT_HOVER
            btn_text_color = theme.BG_BASE
            btn_state = "normal"
            status_color = theme.MINT_SUCCESS

        self.lbl_backup_status = ctk.CTkLabel(c2, text=status_txt, font=("Inter", 11), text_color=status_color, justify="left")
        self.lbl_backup_status.pack(anchor="w", padx=16, pady=(0, 8))

        btn_bar2 = ctk.CTkFrame(c2, fg_color="transparent")
        btn_bar2.pack(anchor="w", padx=16, pady=(0, 14))

        self.btn_sync_vault = ctk.CTkButton(
            btn_bar2, text=btn_txt, height=40, font=("Space Grotesk", 12, "bold"),
            fg_color=btn_color, hover_color=btn_hover,
            text_color=btn_text_color, state=btn_state,
            command=self._execute_sync_to_pc
        )
        self.btn_sync_vault.pack(side="left")

        if is_sync_running:
            btn_cancel_sync = ctk.CTkButton(
                btn_bar2, text="⏹ CANCEL OPERATION", height=40, width=170, font=("Space Grotesk", 12, "bold"),
                fg_color=theme.CRIMSON_DANGER, hover_color=theme.CRIMSON_HOVER,
                text_color=theme.TEXT_PRIMARY,
                command=self.cancel_current_operation
            )
            btn_cancel_sync.pack(side="left", padx=(10, 0))

    def _execute_prepare_backup_usb(self):
        if self.is_busy:
            self.log_terminal("An operation is already in progress. Please wait.", "warn")
            return
        if not self._check_usb_ready(): return

        b_type = "community" if ("Community" in self.backup_mode_var.get()) else "personal"
        inc_media = self.backup_media_var.get()
        p_name = self.backup_preset_name_var.get().strip()
        p_author = self.backup_author_var.get().strip()

        self.is_busy = True
        self.current_operation = "prepare_backup"
        self.start_progress(f"Preparing {b_type.upper()} Backup USB")
        self._refresh_active_view()

        def _worker():
            ok = payload_engine.prepare_backup_usb(
                self.current_usb.letter,
                backup_type=b_type,
                include_media=inc_media,
                preset_name=p_name,
                author=p_author,
                log_func=lambda m: self.log_terminal(m, "cyan"),
                progress_func=self.update_progress,
                cancel_check=self.cancel_event.is_set
            )
            was_cancelled = self.cancel_event.is_set()
            self.is_busy = False
            self.current_operation = ""
            if was_cancelled:
                self.log_terminal("Backup preparation cancelled by user.", "warn")
                self.finish_progress(False, "Backup Preparation Cancelled")
            elif ok:
                self.log_terminal(f"Backup USB Ready ({b_type.upper()})! Plug into car to create snapshot.", "mint")
                self.finish_progress(True, "Backup USB Ready")
            else:
                self.log_terminal("Failed to prepare Backup USB.", "danger")
                self.finish_progress(False, "Failed to prepare Backup USB")
            self.after(0, self._refresh_active_view)

        threading.Thread(target=_worker, daemon=True).start()

    def _execute_sync_to_pc(self):
        if self.is_busy:
            self.log_terminal("An operation is already in progress. Please wait.", "warn")
            return
        if not self._check_usb_ready(): return
        if getattr(self.current_usb, "is_restore_ready", False):
            self.log_terminal("Cannot sync: USB is currently prepared as a Restore Payload for the car, not a new car backup.", "warn")
            return

        # Check if already vaulted and confirm with user
        already_vaulted = find_existing_vault_backup(self.current_usb.letter, BACKUPS_DIR)
        force_sync = False
        if already_vaulted:
            folder_bname = os.path.basename(already_vaulted)
            confirmed = messagebox.askyesno(
                "Backup Already in Vault",
                f"This exact car backup is ALREADY vaulted on your PC:\n{folder_bname}\n\nDo you want to re-sync anyway?",
                parent=self
            )
            if not confirmed:
                self.log_terminal("Sync skipped (backup is already vaulted in PC).", "cyan")
                return
            force_sync = True

        # Lock UI immediately on main thread to prevent multiple clicks
        self.is_busy = True
        self.current_operation = "sync_vault"
        self.start_progress("Syncing Car Backup to PC Vault")
        self._refresh_active_view()

        def _worker():
            dest = sync_backup_from_usb_to_pc(
                self.current_usb.letter, BACKUPS_DIR,
                progress_callback=self.update_progress,
                log_func=lambda m: self.log_terminal(m, "cyan"),
                force=force_sync,
                cancel_check=self.cancel_event.is_set
            )
            was_cancelled = self.cancel_event.is_set()
            self.is_busy = False
            self.current_operation = ""
            if was_cancelled:
                self.log_terminal("Backup sync cancelled by user.", "warn")
                self.finish_progress(False, "Backup Sync Cancelled")
            elif dest:
                self.log_terminal(f"Backup safely vaulted to PC: {dest}", "mint")
                self.finish_progress(True, "Backup Safely Vaulted to PC")
            else:
                self.log_terminal("Backup sync failed or aborted.", "danger")
                self.finish_progress(False, "Backup Sync Failed")
            self.after(0, self._refresh_active_view)
        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # 7. VIEW: FACTORY RESET (SPORT CRIMSON ALERT)
    # -----------------------------------------------------------------------
    def _view_factory_reset(self):
        pad = ctk.CTkScrollableFrame(self.content_panel, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=12, pady=(12, 10))

        ctk.CTkLabel(
            pad, text="⚠️ ZERO-TRACE FACTORY RESET",
            font=("Space Grotesk", 18, "bold"), text_color=theme.CRIMSON_DANGER
        ).pack(anchor="w", padx=6)

        ctk.CTkLabel(
            pad,
            text="Completely restores the head unit to factory state before dealership inspection:\n• Preserves all 69 factory priv-apps + 33 apps and re-enables stock launcher\n• Deep Bluetooth hardware chip wipe (AT#BX & NVRAM clear)\n• Wipes all user APKs, accounts, databases, Wi-Fi networks, and storage\n• Deep telemetry wipe: Purges all crash tombstones, ANR traces, DropBox & system logs\n• Locks system Read-Only and triggers automatic reboot to pristine factory state.",
            font=("Inter", 12), text_color=theme.TEXT_MUTED, justify="left"
        ).pack(anchor="w", pady=(4, 16))

        card = ctk.CTkFrame(pad, fg_color=theme.SURFACE_2, corner_radius=10, border_width=1, border_color=theme.CRIMSON_DANGER)
        card.pack(fill="x", pady=8)

        self.var_confirm_reset = ctk.BooleanVar(value=self.confirmed_reset_state)
        def _on_confirm_change():
            self.confirmed_reset_state = self.var_confirm_reset.get()

        chk = ctk.CTkCheckBox(
            card, text="I understand this payload will completely reset vehicle head unit data to factory zero.",
            variable=self.var_confirm_reset, font=("Inter", 11, "bold"),
            checkmark_color=theme.TEXT_PRIMARY, fg_color=theme.CRIMSON_DANGER,
            command=_on_confirm_change
        )
        chk.pack(padx=16, pady=16, anchor="w")

        is_reset_running = (self.current_operation == "factory_reset")
        btn_bar = ctk.CTkFrame(card, fg_color="transparent")
        btn_bar.pack(anchor="w", padx=16, pady=(0, 16))

        if is_reset_running:
            d_text = "⏳ Loading... Preparing Factory Purge USB..."
            d_fg = theme.SURFACE_3
            d_hover = theme.SURFACE_3
            d_text_color = theme.TEXT_MUTED
            d_state = "disabled"
        elif self.is_busy:
            d_text = f"🔒 System Busy ({self.current_operation_title or 'In progress'})"
            d_fg = theme.SURFACE_3
            d_hover = theme.SURFACE_3
            d_text_color = theme.TEXT_MUTED
            d_state = "disabled"
        else:
            d_text = "⚠️ PREPARE ZERO-TRACE FACTORY PURGE USB"
            d_fg = theme.CRIMSON_DANGER
            d_hover = theme.CRIMSON_HOVER
            d_text_color = theme.TEXT_PRIMARY
            d_state = "normal"

        self.btn_factory_reset = ctk.CTkButton(
            btn_bar,
            text=d_text,
            height=44,
            font=("Space Grotesk", 13, "bold"),
            fg_color=d_fg,
            hover_color=d_hover,
            text_color=d_text_color,
            state=d_state,
            command=self._execute_factory_reset
        )
        self.btn_factory_reset.pack(side="left")

        if is_reset_running:
            btn_cancel = ctk.CTkButton(
                btn_bar, text="⏹ CANCEL OPERATION", height=44, width=170, font=("Space Grotesk", 12, "bold"),
                fg_color=theme.CRIMSON_DANGER, hover_color=theme.CRIMSON_HOVER,
                text_color=theme.TEXT_PRIMARY,
                command=self.cancel_current_operation
            )
            btn_cancel.pack(side="left", padx=(10, 0))

    def _execute_factory_reset(self):
        if self.is_busy:
            self.log_terminal("An operation is already in progress. Please wait.", "warn")
            return
        if not self._check_usb_ready(): return
        if not self.var_confirm_reset.get():
            self.log_terminal("Please check the confirmation box before preparing Factory Reset USB.", "danger")
            return

        self.is_busy = True
        self.current_operation = "factory_reset"
        self.start_progress("Preparing Zero-Trace Factory Reset USB")
        self._refresh_active_view()

        def _worker():
            ok = payload_engine.prepare_factory_reset_usb(
                self.current_usb.letter, FACTORY_BACKUP_DIR,
                log_func=lambda m: self.log_terminal(m, "cyan"),
                progress_func=self.update_progress,
                cancel_check=self.cancel_event.is_set
            )
            was_cancelled = self.cancel_event.is_set()
            self.is_busy = False
            self.current_operation = ""
            if was_cancelled:
                self.log_terminal("Factory Reset preparation cancelled by user.", "warn")
                self.finish_progress(False, "Factory Reset Cancelled")
            elif ok:
                self.log_terminal("Zero-Trace Factory Reset USB Ready!", "mint")
                self.finish_progress(True, "Zero-Trace Factory Reset USB Ready")
            else:
                self.log_terminal("Failed to prepare Factory Reset USB.", "danger")
                self.finish_progress(False, "Failed to prepare Factory Reset USB")
            self.after(0, self._refresh_active_view)

        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # 8. VIEW: RESTORE (PC VAULT TO USB TO CAR)
    # -----------------------------------------------------------------------
    def _view_restore(self):
        for widget in self.content_panel.winfo_children():
            widget.destroy()

        pad = ctk.CTkScrollableFrame(self.content_panel, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=12, pady=(12, 10))

        ctk.CTkLabel(
            pad, text="🔄 RESTORE (PC VAULT TO CAR)",
            font=("Space Grotesk", 18, "bold"), text_color=theme.CYAN_PRIMARY
        ).pack(anchor="w", padx=6)

        ctk.CTkLabel(
            pad,
            text="Transfers your chosen PC backup snapshot or community preset to USB and writes the 12-step car restoration script.",
            font=("Inter", 12), text_color=theme.TEXT_MUTED
        ).pack(anchor="w", pady=(4, 12))

        local_b = get_local_backups(BACKUPS_DIR)
        if not local_b:
            empty_frame = ctk.CTkFrame(pad, fg_color=theme.SURFACE_2, corner_radius=8)
            empty_frame.pack(fill="x", pady=10)
            ctk.CTkLabel(
                empty_frame, text="No backups found in local PC Vault.\nCreate a backup on your car first, then sync it to PC under the 'Backup' tab.",
                font=("Inter", 12), text_color=theme.TEXT_MUTED, justify="center"
            ).pack(padx=20, pady=24)
            return

        ctk.CTkLabel(pad, text="SELECT VAULT BACKUP / COMMUNITY PRESET TO RESTORE:", font=("Space Grotesk", 12, "bold"), text_color=theme.CYAN_PRIMARY).pack(anchor="w", pady=(8, 4))

        if not self.selected_restore_path or not any(b["path"] == self.selected_restore_path for b in local_b):
            self.selected_restore_path = local_b[0]["path"]

        scroll = ctk.CTkScrollableFrame(pad, fg_color=theme.SURFACE_2, corner_radius=8, height=180)
        scroll.pack(fill="x", pady=(0, 10))

        self.restore_radio_var = ctk.StringVar(value=self.selected_restore_path)
        def _on_restore_radio_change():
            self.selected_restore_path = self.restore_radio_var.get()
            self._refresh_active_view()

        for b in local_b:
            is_active = (b["path"] == self.selected_restore_path)
            is_latest = b.get("is_latest", False)
            row = ctk.CTkFrame(scroll, fg_color=theme.SURFACE_3 if is_active else "transparent", corner_radius=6)
            row.pack(fill="x", pady=3, padx=4)

            is_comm = (b.get("backup_type") == "COMMUNITY")
            badge_txt = "🌐 COMMUNITY" if is_comm else "🔒 PERSONAL"
            badge_color = theme.CYAN_PRIMARY if is_comm else theme.SURFACE_1
            badge_fg = theme.BG_BASE if is_comm else theme.TEXT_MUTED

            badge = ctk.CTkLabel(
                row, text=badge_txt,
                font=("Space Grotesk", 9, "bold"),
                fg_color=badge_color,
                text_color=badge_fg,
                corner_radius=4,
                width=90, height=20
            )
            badge.pack(side="left", padx=(8, 4), pady=6)

            if is_latest:
                latest_badge = ctk.CTkLabel(
                    row, text="★ الأحدث (LATEST)",
                    font=("Space Grotesk", 9, "bold"),
                    fg_color=theme.MINT_SUCCESS,
                    text_color=theme.BG_BASE,
                    corner_radius=4,
                    width=110, height=20
                )
                latest_badge.pack(side="left", padx=(0, 6), pady=6)
            else:
                order_badge = ctk.CTkLabel(
                    row, text=f"#{b.get('order', '')}",
                    font=("Space Grotesk", 9, "bold"),
                    fg_color=theme.SURFACE_1,
                    text_color=theme.TEXT_MUTED,
                    corner_radius=4,
                    width=32, height=20
                )
                order_badge.pack(side="left", padx=(0, 6), pady=6)

            if is_comm:
                pname = b.get('preset_name') or b['folder_name']
                auth = f" (by {b['author']})" if b.get('author') else ""
                rb_text = f"🌐 {pname}{auth}  •  📅 {b.get('formatted_datetime', b.get('date', ''))}  •  {b.get('size_str', '')}"
            else:
                rb_text = f"📅 {b.get('formatted_datetime', b.get('date', ''))}  —  {b.get('size_str', '')}   [{b['folder_name']}]"

            rb = ctk.CTkRadioButton(
                row, text=rb_text,
                value=b["path"], variable=self.restore_radio_var,
                font=("Inter", 11, "bold"), fg_color=theme.CYAN_PRIMARY,
                command=_on_restore_radio_change
            )
            rb.pack(side="left", padx=4, pady=6)

        # Contextual explanation card for selected restore target
        selected_b_entry = next((x for x in local_b if x["path"] == self.selected_restore_path), local_b[0])
        sel_is_comm = (selected_b_entry.get("backup_type") == "COMMUNITY")
        sel_is_latest = selected_b_entry.get("is_latest", False)

        detail_box = ctk.CTkFrame(pad, fg_color=theme.SURFACE_1, corner_radius=8, border_width=1, border_color=theme.BORDER_CYAN if sel_is_comm else (theme.MINT_SUCCESS if sel_is_latest else theme.BORDER_SLATE))
        detail_box.pack(fill="x", pady=(0, 12))

        # Selected backup summary header
        sum_frame = ctk.CTkFrame(detail_box, fg_color="transparent")
        sum_frame.pack(fill="x", padx=14, pady=(10, 4))

        latest_mark = " ★ [أحدث نسخة احتياطية — LATEST]" if sel_is_latest else f" [النسخة رقم #{selected_b_entry.get('order', '')}]"
        ctk.CTkLabel(
            sum_frame,
            text=f"📁 {selected_b_entry['folder_name']}{latest_mark}",
            font=("Space Grotesk", 12, "bold"),
            text_color=theme.MINT_SUCCESS if sel_is_latest else theme.CYAN_PRIMARY
        ).pack(anchor="w")

        info_line = f"📅 التاريخ: {selected_b_entry.get('formatted_datetime', 'N/A')}  |  💾 الحجم: {selected_b_entry.get('size_str', 'N/A')}  |  🏷️ النوع: {'🌐 Community Preset' if sel_is_comm else '🔒 Personal Private (1:1 Clone)'}"
        ctk.CTkLabel(
            sum_frame,
            text=info_line,
            font=("Inter", 11),
            text_color=theme.TEXT_PRIMARY
        ).pack(anchor="w", pady=(2, 6))

        if sel_is_comm:
            pname = selected_b_entry.get("preset_name") or selected_b_entry.get("folder_name")
            pauthor = selected_b_entry.get("author") or "Community Member"
            ctk.CTkLabel(
                detail_box,
                text=f"🛡️ Safe Community Preset Restore ({pname} by {pauthor}):\n"
                     f"• Non-Destructive: Target car's Google accounts, Wi-Fi networks & Bluetooth pairings are 100% PRESERVED untouched.\n"
                     f"• Installed: Custom launchers, app widgets, third-party user apps & custom settings.",
                font=("Inter", 11), text_color=theme.CYAN_PRIMARY, justify="left"
            ).pack(anchor="w", padx=14, pady=(0, 10))
        else:
            ctk.CTkLabel(
                detail_box,
                text="🔄 Full 1:1 Personal Restore:\n"
                     "• Complete Vehicle Restore: Restores Google accounts, saved Wi-Fi connections, paired Bluetooth, apps & full settings.\n"
                     "• Recommended only when restoring to your own vehicle.",
                font=("Inter", 11), text_color=theme.TEXT_MUTED, justify="left"
            ).pack(anchor="w", padx=14, pady=(0, 10))

        is_restore_running = (self.current_operation == "restore")
        btn_bar = ctk.CTkFrame(pad, fg_color="transparent")
        btn_bar.pack(fill="x", pady=(4, 20), padx=6)

        if is_restore_running:
            d_text = "⏳ Loading... Transferring Backup to USB..."
            d_fg = theme.SURFACE_3
            d_hover = theme.SURFACE_3
            d_text_color = theme.TEXT_MUTED
            d_state = "disabled"
        elif self.is_busy:
            d_text = f"🔒 System Busy ({self.current_operation_title or 'In progress'})"
            d_fg = theme.SURFACE_3
            d_hover = theme.SURFACE_3
            d_text_color = theme.TEXT_MUTED
            d_state = "disabled"
        else:
            action_noun = "COMMUNITY PRESET" if sel_is_comm else "PERSONAL BACKUP"
            d_text = f"🔄 TRANSFER {action_noun} TO USB & PREPARE RESTORE"
            d_fg = theme.CYAN_PRIMARY
            d_hover = theme.CYAN_HOVER
            d_text_color = theme.BG_BASE
            d_state = "normal"

        self.transfer_backup_to_usb_button = ctk.CTkButton(
            btn_bar,
            text=d_text,
            height=46,
            font=("Space Grotesk", 14, "bold"),
            fg_color=d_fg,
            hover_color=d_hover,
            text_color=d_text_color,
            state=d_state,
            command=self._execute_restore
        )
        self.transfer_backup_to_usb_button.pack(side="left", fill="x", expand=True)

        if is_restore_running:
            btn_cancel = ctk.CTkButton(
                btn_bar, text="⏹ CANCEL OPERATION", height=46, width=170, font=("Space Grotesk", 12, "bold"),
                fg_color=theme.CRIMSON_DANGER, hover_color=theme.CRIMSON_HOVER,
                text_color=theme.TEXT_PRIMARY,
                command=self.cancel_current_operation
            )
            btn_cancel.pack(side="left", padx=(10, 0))

    def _execute_restore(self):
        if self.is_busy:
            self.log_terminal("An operation is already in progress. Please wait.", "warn")
            return
        if not self._check_usb_ready(): return

        bpath = self.restore_radio_var.get()
        if not bpath or not os.path.exists(bpath):
            self.log_terminal("No valid backup selected for restore.", "warn")
            return

        self.selected_restore_path = bpath

        # Immediate lock and visual loading state to prevent double-clicks
        self.is_busy = True
        self.current_operation = "restore"
        self.start_progress("Transferring Backup to USB & Preparing Restore")
        self._refresh_active_view()

        def _worker():
            ok = payload_engine.prepare_restore_usb(
                self.current_usb.letter, bpath,
                log_func=lambda m: self.log_terminal(m, "cyan"),
                progress_func=self.update_progress,
                cancel_check=self.cancel_event.is_set
            )
            was_cancelled = self.cancel_event.is_set()
            self.is_busy = False
            self.current_operation = ""
            if was_cancelled:
                self.log_terminal("Restore preparation cancelled by user.", "warn")
                self.finish_progress(False, "Restore Cancelled")
            elif ok:
                self.log_terminal("Restore USB Prepared Successfully! Ready to plug into car.", "mint")
                self.finish_progress(True, "Restore USB Prepared Successfully")
            else:
                self.log_terminal("Failed to prepare Restore USB.", "danger")
                self.finish_progress(False, "Failed to prepare Restore USB")
            self.after(0, self._refresh_active_view)

        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # 9. VIEW: FETCH LOGS
    # -----------------------------------------------------------------------
    def _view_fetch_logs(self):
        self._build_simple_action_card(
            title="📋 FETCH DIAGNOSTIC LOGS",
            desc="Generates a USB payload that extracts logcat, dmesg, tombstone crash traces, memory status, and package lists from the car.",
            badge="DIAGNOSTIC DUMP",
            btn_text="📋 PREPARE FETCH LOGS USB",
            btn_color=theme.CYAN_PRIMARY,
            action_handler=self._execute_fetch_logs,
            op_id="fetch_logs",
            loading_text="⏳ Loading... Preparing Fetch Logs USB..."
        )

    def _execute_fetch_logs(self):
        if self.is_busy:
            self.log_terminal("An operation is already in progress. Please wait.", "warn")
            return
        if not self._check_usb_ready(): return

        self.is_busy = True
        self.current_operation = "fetch_logs"
        self.start_progress("Preparing Fetch Diagnostic Logs USB")
        self._refresh_active_view()

        def _worker():
            ok = payload_engine.prepare_fetch_logs_usb(
                self.current_usb.letter,
                log_func=lambda m: self.log_terminal(m, "cyan"),
                progress_func=self.update_progress,
                cancel_check=self.cancel_event.is_set
            )
            was_cancelled = self.cancel_event.is_set()
            self.is_busy = False
            self.current_operation = ""
            if was_cancelled:
                self.log_terminal("Fetch Diagnostic Logs cancelled by user.", "warn")
                self.finish_progress(False, "Fetch Logs Cancelled")
            elif ok:
                self.log_terminal("Fetch Logs USB Ready!", "mint")
                self.finish_progress(True, "Fetch Logs USB Ready")
            else:
                self.log_terminal("Failed to prepare Fetch Logs USB.", "danger")
                self.finish_progress(False, "Failed to prepare Fetch Logs USB")
            self.after(0, self._refresh_active_view)

        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # Helper Component: Action Card
    # -----------------------------------------------------------------------
    def _build_simple_action_card(self, title, desc, badge, btn_text, btn_color, action_handler, op_id: str = "", loading_text: str = ""):
        pad = ctk.CTkFrame(self.content_panel, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(pad, text=title, font=("Space Grotesk", 18, "bold"), text_color=btn_color).pack(anchor="w")
        ctk.CTkLabel(pad, text=desc, font=("Inter", 12), text_color=theme.TEXT_MUTED, justify="left").pack(anchor="w", pady=(6, 20))

        card = ctk.CTkFrame(pad, fg_color=theme.SURFACE_2, corner_radius=10, border_width=1, border_color=theme.BORDER_SLATE)
        card.pack(fill="x", pady=10)

        ctk.CTkLabel(
            card, text=f"TAG: {badge}", font=("Consolas", 10, "bold"),
            text_color=theme.CYAN_PRIMARY
        ).pack(anchor="w", padx=16, pady=(16, 8))

        is_running = bool(op_id and self.current_operation == op_id)
        btn_bar = ctk.CTkFrame(card, fg_color="transparent")
        btn_bar.pack(anchor="w", padx=16, pady=(0, 16))

        if is_running:
            d_text = loading_text or f"⏳ Loading... {btn_text.lstrip('⚡🌐🧹⚙️📋⚠️🔄💾 ')}..."
            d_fg = theme.SURFACE_3
            d_hover = theme.SURFACE_3
            d_text_color = theme.TEXT_MUTED
            d_state = "disabled"
            btn = ctk.CTkButton(
                btn_bar, text=d_text, height=44, font=("Space Grotesk", 13, "bold"),
                fg_color=d_fg, hover_color=d_hover,
                text_color=d_text_color,
                state=d_state,
                command=action_handler
            )
            btn.pack(side="left")
            btn_cancel = ctk.CTkButton(
                btn_bar, text="⏹ CANCEL OPERATION", height=44, width=170, font=("Space Grotesk", 12, "bold"),
                fg_color=theme.CRIMSON_DANGER, hover_color=theme.CRIMSON_HOVER,
                text_color=theme.TEXT_PRIMARY,
                command=self.cancel_current_operation
            )
            btn_cancel.pack(side="left", padx=(10, 0))
        elif self.is_busy:
            btn = ctk.CTkButton(
                btn_bar, text=f"🔒 System Busy ({self.current_operation_title or 'Operation in progress'})",
                height=44, font=("Space Grotesk", 13, "bold"),
                fg_color=theme.SURFACE_3, hover_color=theme.SURFACE_3,
                text_color=theme.TEXT_MUTED,
                state="disabled"
            )
            btn.pack(side="left")
        else:
            d_text = btn_text
            d_fg = btn_color
            d_hover = theme.CYAN_HOVER
            d_text_color = theme.BG_BASE if btn_color != theme.CRIMSON_DANGER else theme.TEXT_PRIMARY
            btn = ctk.CTkButton(
                btn_bar, text=d_text, height=44, font=("Space Grotesk", 13, "bold"),
                fg_color=d_fg, hover_color=d_hover,
                text_color=d_text_color,
                state="normal",
                command=action_handler
            )
            btn.pack(side="left")

        if op_id:
            setattr(self, f"btn_card_{op_id}", btn)

    def _check_usb_ready(self) -> bool:
        if self.is_busy:
            self.log_terminal("An operation is already in progress. Please wait.", "warn")
            return False
        if not self.current_usb:
            self.log_terminal("No USB drive detected! Please insert a USB flash drive.", "danger")
            return False
        return True


if __name__ == "__main__":
    app = AeroSuiteApp()
    app.mainloop()
