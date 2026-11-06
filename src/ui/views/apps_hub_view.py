"""
apps_hub_view.py — Unified Application Management Hub for Aero Suite.
Unifies App Installation (InstallAppsView), Clean Removal (UninstallAppsView),
and Instant Car Launch (OpenAppView) into a single cohesive, tabbed control studio.
Localized dynamically via core.i18n and fully compliant with UI_RTL_GUIDELINES.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget, QFrame, QApplication
)
import theme
from core.i18n import t
from ui.views.install_apps_view import InstallAppsView
from ui.views.uninstall_apps_view import UninstallAppsView
from ui.views.open_app_view import OpenAppView


class AppsHubView(QWidget):
    """Unified Tabbed Hub for Application Installation, Removal, and On-Car Launch."""
    tab_changed = Signal(int)

    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.current_tab = 0
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 14, 20, 12)
        root_layout.setSpacing(10)

        # 1. Connected Segmented Pill Tab Bar (Option 4: 50px, spacing 0, dynamic radii & dividers)
        self.tab_container = QFrame()
        self.tab_container.setObjectName("segmentedTabBar")
        self.tab_container.setFixedHeight(50)
        self.tab_container.setStyleSheet(f"""
            QFrame#segmentedTabBar {{
                background-color: {theme.SURFACE_1};
                border: 1.5px solid {theme.BORDER_SLATE};
                border-radius: 25px;
            }}
        """)

        tab_layout = QHBoxLayout(self.tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        self.btn_tab_install = QPushButton(t("apps_hub.tab_install", "📥 Install Apps"))
        self.btn_tab_install.setFixedHeight(50)
        self.btn_tab_install.setCursor(Qt.PointingHandCursor)
        self.btn_tab_install.clicked.connect(lambda: self.set_active_tab(0))
        tab_layout.addWidget(self.btn_tab_install, 1)

        self.btn_tab_uninstall = QPushButton(t("apps_hub.tab_uninstall", "🛡️ Uninstall Apps"))
        self.btn_tab_uninstall.setFixedHeight(50)
        self.btn_tab_uninstall.setCursor(Qt.PointingHandCursor)
        self.btn_tab_uninstall.clicked.connect(lambda: self.set_active_tab(1))
        tab_layout.addWidget(self.btn_tab_uninstall, 1)

        self.btn_tab_launch = QPushButton(t("apps_hub.tab_launch", "🚀 Launch App"))
        self.btn_tab_launch.setFixedHeight(50)
        self.btn_tab_launch.setCursor(Qt.PointingHandCursor)
        self.btn_tab_launch.clicked.connect(lambda: self.set_active_tab(2))
        tab_layout.addWidget(self.btn_tab_launch, 1)

        root_layout.addWidget(self.tab_container)

        # 2. Content Stack for Embedded Views
        self.stack = QStackedWidget()

        # Child View 0: Install Apps
        self.install_view = InstallAppsView(self.main_app, self)
        if self.install_view.layout():
            self.install_view.layout().setContentsMargins(0, 6, 0, 0)
        self.stack.addWidget(self.install_view)

        # Child View 1: Uninstall Apps
        self.uninstall_view = UninstallAppsView(self.main_app, self)
        if self.uninstall_view.layout():
            self.uninstall_view.layout().setContentsMargins(0, 6, 0, 0)
        self.stack.addWidget(self.uninstall_view)

        # Child View 2: Open App
        self.open_view = OpenAppView(self.main_app, self)
        if self.open_view.layout():
            self.open_view.layout().setContentsMargins(0, 6, 0, 0)
        self.stack.addWidget(self.open_view)

        root_layout.addWidget(self.stack)

        # Apply initial tab styling
        self._update_tab_styles()

    def set_active_tab(self, index: int):
        """Switches active sub-view and refreshes tab styles."""
        if index < 0 or index >= self.stack.count():
            return
        self.current_tab = index
        self.stack.setCurrentIndex(index)
        self._update_tab_styles()

        # Trigger reactive view refreshes when switching
        if index == 0:
            if hasattr(self.install_view, "render_cards"):
                self.install_view.render_cards()
        elif index == 1:
            if hasattr(self.uninstall_view, "render_cards"):
                self.uninstall_view.render_cards()
        elif index == 2:
            if hasattr(self.open_view, "sync_rows"):
                self.open_view.sync_rows()

        self.tab_changed.emit(index)

    def _update_tab_styles(self):
        """Highlights the active tab with solid cyan fill and dynamic corner radii and dividers (Option 4)."""
        buttons = [self.btn_tab_install, self.btn_tab_uninstall, self.btn_tab_launch]
        is_rtl = QApplication.isRightToLeft()
        N = len(buttons)
        phys_order = list(reversed(range(N))) if is_rtl else list(range(N))

        for pos_idx, log_idx in enumerate(phys_order):
            btn = buttons[log_idx]
            is_leftmost = (pos_idx == 0)
            is_rightmost = (pos_idx == N - 1)
            is_active = (log_idx == self.current_tab)

            if is_leftmost:
                radius_str = "border-top-left-radius: 23px; border-bottom-left-radius: 23px; border-top-right-radius: 0px; border-bottom-right-radius: 0px;"
            elif is_rightmost:
                radius_str = "border-top-right-radius: 23px; border-bottom-right-radius: 23px; border-top-left-radius: 0px; border-bottom-left-radius: 0px;"
            else:
                radius_str = "border-radius: 0px;"

            border_left_str = "border: none;"
            if not is_leftmost and not is_active:
                left_neighbor_log_idx = phys_order[pos_idx - 1]
                if left_neighbor_log_idx != self.current_tab:
                    border_left_str = f"border-left: 1px solid {theme.BORDER_SLATE}; border-right: none; border-top: none; border-bottom: none;"

            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {theme.CYAN_PRIMARY};
                        color: #050B14;
                        font-size: 14px;
                        font-weight: bold;
                        border: none;
                        {radius_str}
                        padding: 0 14px;
                    }}
                    QPushButton:hover {{
                        background-color: {theme.CYAN_HOVER};
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {theme.TEXT_MUTED};
                        font-size: 14px;
                        font-weight: 600;
                        {border_left_str}
                        {radius_str}
                        padding: 0 14px;
                    }}
                    QPushButton:hover {{
                        color: {theme.TEXT_PRIMARY};
                        background-color: {theme.SURFACE_2};
                    }}
                """)

    def retranslate_ui(self):
        """Re-translates tab buttons and propagates to embedded views."""
        self.btn_tab_install.setText(t("apps_hub.tab_install", "📥 Install Apps"))
        self.btn_tab_uninstall.setText(t("apps_hub.tab_uninstall", "🛡️ Uninstall Apps"))
        self.btn_tab_launch.setText(t("apps_hub.tab_launch", "🚀 Launch App"))
        self._update_tab_styles()

        if hasattr(self.install_view, "retranslate_ui"):
            self.install_view.retranslate_ui()
        if hasattr(self.uninstall_view, "retranslate_ui"):
            self.uninstall_view.retranslate_ui()
        if hasattr(self.open_view, "retranslate_ui"):
            self.open_view.retranslate_ui()
