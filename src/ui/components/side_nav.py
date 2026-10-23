"""
side_nav.py — Aero Suite Sidebar Navigation Component.
Categorised side navigation menu with active accent borders and status styling.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea
)
import theme


FEATURE_CATEGORIES = [
    ("APPLICATION MANAGEMENT", [
        ("install_apps",     "📦", "Install Apps",           "Custom apps with autostart & portrait"),
        ("uninstall_apps",   "🗑", "Safe Uninstall",         "Remove unwanted user & system apps"),
        ("open_app",         "🚀", "Open Application",       "Launch any installed package directly"),
        ("open_settings",    "⚙️", "Android Settings",       "Access hidden native Android settings"),
    ]),
    ("GOOGLE & LAUNCHER MODS", [
        ("install_gms",      "🌐", "Google Services",        "Inject Play Store & Google Framework"),
        ("uninstall_gms",    "🧹", "Purge Google Services",  "Clean wipe of Google framework & apps"),
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


class SideNavWidget(QFrame):
    """Categorized sidebar menu for navigating between features."""
    feature_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sideBar")
        self.setFixedWidth(260)
        self.feature_buttons = {}
        self.current_feature = None
        self._build_ui()

    def _build_ui(self):
        sidebar_layout = QVBoxLayout(self)
        sidebar_layout.setContentsMargins(8, 12, 8, 12)
        sidebar_layout.setSpacing(6)

        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setStyleSheet("background: transparent; border: none;")

        nav_widget = QWidget()
        self.nav_layout = QVBoxLayout(nav_widget)
        self.nav_layout.setContentsMargins(0, 0, 4, 0)
        self.nav_layout.setSpacing(4)

        for i, (cat_title, cat_feats) in enumerate(FEATURE_CATEGORIES):
            if i > 0:
                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                sep.setFixedHeight(1)
                sep.setStyleSheet(f"background-color: {theme.BORDER_SLATE}; border: none; margin: 4px 4px;")
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
                icon_lbl.setStyleSheet(
                    f"font-size: 15px; color: {theme.CRIMSON_DANGER if feat_id == 'factory_reset' else theme.CYAN_PRIMARY}; "
                    "background: transparent; border: none;"
                )
                ib_layout.addWidget(icon_lbl)

                text_box = QVBoxLayout()
                text_box.setSpacing(1)
                t_lbl = QLabel(feat_title)
                t_lbl.setStyleSheet(
                    f"font-size: 12px; font-weight: bold; color: {theme.CRIMSON_DANGER if feat_id == 'factory_reset' else theme.TEXT_PRIMARY}; "
                    "background: transparent; border: none;"
                )
                d_lbl = QLabel(feat_desc)
                d_lbl.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_MUTED}; background: transparent; border: none;")
                text_box.addWidget(t_lbl)
                text_box.addWidget(d_lbl)
                ib_layout.addLayout(text_box)

                # Click handler
                def _make_handler(fid=feat_id):
                    return lambda event: self.select_feature(fid)
                item_btn.mousePressEvent = _make_handler()

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

    def select_feature(self, feat_id: str):
        """Highlights the active feature and emits feature_selected signal."""
        if feat_id == self.current_feature:
            return

        for fid, btn_data in self.feature_buttons.items():
            fr = btn_data["frame"]
            obj_name = fr.objectName()
            is_active = (fid == feat_id)
            is_danger = (fid == "factory_reset")

            if is_active:
                fr.setStyleSheet(f"""
                    QFrame#{obj_name} {{
                        background-color: {theme.CYAN_ALPHA_15};
                        border: 1px solid {theme.CYAN_PRIMARY};
                        border-left: 3px solid {theme.CYAN_PRIMARY};
                        border-radius: 8px;
                    }}
                """)
                btn_data["title"].setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme.CRIMSON_DANGER if is_danger else theme.CYAN_PRIMARY}; background: transparent; border: none;")
                btn_data["desc"].setStyleSheet(f"font-size: 10px; color: {theme.TEXT_PRIMARY}; background: transparent; border: none;")
            else:
                fr.setStyleSheet("")
                btn_data["title"].setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme.CRIMSON_DANGER if is_danger else theme.TEXT_PRIMARY}; background: transparent; border: none;")
                btn_data["desc"].setStyleSheet(f"font-size: 10px; color: {theme.TEXT_MUTED}; background: transparent; border: none;")

        self.current_feature = feat_id
        self.feature_selected.emit(feat_id)
