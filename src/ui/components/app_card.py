"""
app_card.py — Unified App Row Card Component for Aero Suite.
Renders consistent, high-performance horizontal cards for:
- "install": Checkbox, Name, Package, Auto-Launch, Force Portrait, Block Boot, Target (User/System), Size
- "uninstall": Checkbox, Name, Package, Size
- "open": Single-select Checkbox, Name, Package, Size
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QCheckBox, QComboBox
import theme


class AppCard(QFrame):
    """Interactive card representing an application row."""
    def __init__(self, mode: str, app_data: dict, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.app_data = app_data
        self.setProperty("class", "card")
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)

        self.fname = app_data.get("filename", "")
        self.pkg = app_data.get("package", "")
        self.disp_name = app_data.get("display_name", self.fname)
        self.size_mb = app_data.get("size_mb", 0)

        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)

        # 1. Main Checkbox
        self.chk_main = QCheckBox()
        self.chk_main.setCursor(Qt.PointingHandCursor)
        self.chk_main.setStyleSheet("background-color: transparent; border: none;")
        layout.addWidget(self.chk_main)

        # 2. App Display Name (Truncated at 26 chars)
        max_name_len = 26
        name_text = self.disp_name[:max_name_len] + "…" if len(self.disp_name) > max_name_len else self.disp_name
        self.lbl_name = QLabel(name_text)
        self.lbl_name.setStyleSheet(
            f"font-weight: bold; font-size: 12px; color: {theme.TEXT_PRIMARY}; "
            "background-color: transparent; border: none;"
        )
        self.lbl_name.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_name)

        # 3. Package Name (Truncated at 30 chars)
        max_pkg_len = 30
        pkg_text = f"({self.pkg[:max_pkg_len]}…)" if len(self.pkg) > max_pkg_len else f"({self.pkg})"
        self.lbl_pkg = QLabel(pkg_text)
        self.lbl_pkg.setStyleSheet(
            f"font-size: 10px; color: {theme.TEXT_MUTED}; font-family: Consolas, monospace; "
            "background-color: transparent; border: none;"
        )
        self.lbl_pkg.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_pkg)

        self.setToolTip(f"{self.disp_name}\n{self.pkg}\n{self.size_mb} MB")
        layout.addStretch()

        # Mode-specific right controls
        if self.mode == "install":
            # Auto Launch Checkbox
            self.chk_auto = QCheckBox("Auto Launch")
            self.chk_auto.setCursor(Qt.PointingHandCursor)
            self.chk_auto.setStyleSheet(
                f"font-size: 11px; font-weight: normal; color: {theme.TEXT_PRIMARY}; "
                "background-color: transparent; border: none;"
            )
            layout.addWidget(self.chk_auto)
            layout.addSpacing(14)

            # Force Portrait Checkbox
            self.chk_port = QCheckBox("Force Portrait")
            self.chk_port.setCursor(Qt.PointingHandCursor)
            self.chk_port.setStyleSheet(
                f"font-size: 11px; font-weight: normal; color: {theme.TEXT_PRIMARY}; "
                "background-color: transparent; border: none;"
            )
            layout.addWidget(self.chk_port)
            layout.addSpacing(14)

            # Block Boot Launch Checkbox
            self.chk_boot = QCheckBox("Block Boot Launch")
            self.chk_boot.setCursor(Qt.PointingHandCursor)
            self.chk_boot.setStyleSheet(
                f"font-size: 11px; font-weight: normal; color: {theme.TEXT_PRIMARY}; "
                "background-color: transparent; border: none;"
            )
            layout.addWidget(self.chk_boot)
            layout.addSpacing(14)

            # Target Dropdown (User App vs System App)
            self.combo_target = QComboBox()
            self.combo_target.setObjectName("comboTarget")
            self.combo_target.setFixedWidth(92)
            self.combo_target.setFixedHeight(22)
            self.combo_target.setCursor(Qt.PointingHandCursor)
            self.combo_target.addItems(["User App", "System App"])
            self.combo_target.setToolTip("Target partition: User App (/data/app) vs System App (/system/app)")
            layout.addWidget(self.combo_target)
            layout.addSpacing(14)

        # File/Package Size Label
        self.lbl_size = QLabel(f"{self.size_mb} MB")
        self.lbl_size.setStyleSheet(
            f"font-size: 10px; font-family: Consolas, monospace; font-weight: bold; "
            f"color: {theme.TEXT_MUTED}; background-color: transparent; border: none;"
        )
        self.lbl_size.setFixedWidth(65)
        self.lbl_size.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_size.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_size)

    def set_selected_visual(self, is_selected: bool):
        """Updates card border and background glow based on selection."""
        if is_selected:
            self.setStyleSheet(f"""
                QFrame[class="card"] {{
                    background-color: {theme.SURFACE_2};
                    border: 1px solid {theme.CYAN_PRIMARY};
                    border-radius: 6px;
                }}
            """)
        else:
            self.setStyleSheet("")
