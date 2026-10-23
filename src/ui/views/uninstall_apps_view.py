"""
uninstall_apps_view.py — Feature 2: Safe Uninstall Applications View.
Allows selecting installed packages to cleanly purge from User and System partitions.
Equipped with deduplication to prevent package collisions when multiple APKs share the same package name.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QScrollArea, QFrame
)
import theme
from ui.components.app_card import AppCard


class UninstallAppsView(QWidget):
    """View for managing and executing Safe Uninstallation payloads."""
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.cards_map = {}
        self.search_query = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
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
            "Clean up your screen and free up storage safely! 🛡️ Select any installed apps you want to remove. "
            "Aero Suite purges the app and its leftover files completely—while 100% protecting all your car's original factory functions "
            "(AC controls, radio, reverse camera, and car settings). No risk, pure peace of mind!"
        )
        lbl_banner.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_banner.setWordWrap(True)
        b_layout.addWidget(lbl_banner)
        layout.addWidget(banner)

        # Controls Strip
        ctrl_bar = QHBoxLayout()
        self.btn_all = QPushButton("Select All")
        self.btn_all.setFixedHeight(32)
        self.btn_all.clicked.connect(lambda: self.set_all_selected(True))
        ctrl_bar.addWidget(self.btn_all)

        self.btn_none = QPushButton("Deselect All")
        self.btn_none.setFixedHeight(32)
        self.btn_none.clicked.connect(lambda: self.set_all_selected(False))
        ctrl_bar.addWidget(self.btn_none)

        self.btn_invert = QPushButton("Invert")
        self.btn_invert.setFixedHeight(32)
        self.btn_invert.clicked.connect(self.invert_selection)
        ctrl_bar.addWidget(self.btn_invert)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setFixedHeight(32)
        self.btn_refresh.clicked.connect(self.main_app._rescan_apks)
        ctrl_bar.addWidget(self.btn_refresh)

        ctrl_bar.addSpacing(10)
        self.search_edit = QLineEdit()
        self.search_edit.setFixedHeight(32)
        self.search_edit.setPlaceholderText("🔍 Search Packages to Uninstall (contains name, package)...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        ctrl_bar.addWidget(self.search_edit)
        layout.addLayout(ctrl_bar)

        # Scroll Area for Packages
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 10, 0)
        self.cards_layout.setSpacing(4)
        self.scroll.setWidget(self.cards_container)
        layout.addWidget(self.scroll)

        # Action Button
        self.btn_prepare_uninstall = QPushButton("👆 SELECT AT LEAST ONE APPLICATION TO UNINSTALL")
        self.btn_prepare_uninstall.setProperty("class", "btnDanger")
        self.btn_prepare_uninstall.setFixedHeight(44)
        self.btn_prepare_uninstall.setEnabled(False)
        self.btn_prepare_uninstall.clicked.connect(self._execute_prepare_uninstall)
        layout.addWidget(self.btn_prepare_uninstall)

        self.render_cards()
        self.update_action_button()

    def _get_unique_matching_apps(self):
        """Returns unique applications by package name to eliminate duplicate card collisions."""
        q = self.search_query.strip().lower()
        seen_pkgs = set()
        unique_apps = []

        for a in self.main_app.local_apks:
            pkg = a.get("package", "")
            if not pkg or pkg in seen_pkgs:
                continue
            if not q or (q in a.get("display_name", "").lower() or q in pkg.lower() or q in a.get("filename", "").lower()):
                seen_pkgs.add(pkg)
                unique_apps.append(a)

        return unique_apps

    def render_cards(self):
        """Renders deduplicated package rows."""
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.cards_map = {}
        unique_matching = self._get_unique_matching_apps()

        if not unique_matching:
            empty_lbl = QLabel("No packages found matching search criteria.")
            empty_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding: 20px; font-size: 13px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(empty_lbl)
            self.cards_layout.addStretch()
            return

        for a in unique_matching:
            pkg = a["package"]
            card = AppCard("uninstall", a)
            is_selected = self.main_app.selected_uninstall_pkgs.get(pkg, False)
            card.chk_main.setChecked(is_selected)
            card.set_selected_visual(is_selected)

            # Wire click interactions
            card.chk_main.clicked.connect(lambda checked, p=pkg: self._on_chk_changed(p, checked))
            def _make_press_handler(p=pkg):
                return lambda event: self._on_card_pressed(event, p)
            card.mousePressEvent = _make_press_handler()

            self.cards_layout.addWidget(card)
            self.cards_map[pkg] = {
                "card": card,
                "chk": card.chk_main,
                "lbl_size": card.lbl_size
            }

        self.cards_layout.addStretch()

    def _on_card_pressed(self, event, pkg: str):
        if event.button() == Qt.LeftButton:
            cur = self.main_app.selected_uninstall_pkgs.get(pkg, False)
            self._on_chk_changed(pkg, not cur)

    def _on_chk_changed(self, pkg: str, state: bool):
        self.main_app.selected_uninstall_pkgs[pkg] = state
        if pkg in self.cards_map:
            item = self.cards_map[pkg]
            chk = item["chk"]
            chk.blockSignals(True)
            chk.setChecked(state)
            chk.blockSignals(False)
            item["card"].set_selected_visual(state)
        self.update_action_button()

    def set_all_selected(self, state: bool):
        """Selects or deselects all filtered packages, handling unique packages cleanly."""
        unique_matching = self._get_unique_matching_apps()
        for a in unique_matching:
            pkg = a["package"]
            self.main_app.selected_uninstall_pkgs[pkg] = state
            if pkg in self.cards_map:
                item = self.cards_map[pkg]
                chk = item["chk"]
                chk.blockSignals(True)
                chk.setChecked(state)
                chk.blockSignals(False)
                item["card"].set_selected_visual(state)
        self.update_action_button()

    def invert_selection(self):
        """Inverts selection for currently filtered packages exactly once per package."""
        unique_matching = self._get_unique_matching_apps()
        for a in unique_matching:
            pkg = a["package"]
            cur = self.main_app.selected_uninstall_pkgs.get(pkg, False)
            new_state = not cur
            self.main_app.selected_uninstall_pkgs[pkg] = new_state
            if pkg in self.cards_map:
                item = self.cards_map[pkg]
                chk = item["chk"]
                chk.blockSignals(True)
                chk.setChecked(new_state)
                chk.blockSignals(False)
                item["card"].set_selected_visual(new_state)
        self.update_action_button()

    def _on_search_changed(self, text: str):
        self.search_query = text
        self.render_cards()

    def update_action_button(self):
        count = sum(1 for v in self.main_app.selected_uninstall_pkgs.values() if v)
        if count > 0:
            self.btn_prepare_uninstall.setText(f"🗑 PREPARE SAFE UNINSTALL USB ({count} APPLICATION{'S' if count > 1 else ''} SELECTED)")
            self.btn_prepare_uninstall.setEnabled(True)
        else:
            self.btn_prepare_uninstall.setText("👆 SELECT AT LEAST ONE APPLICATION TO UNINSTALL")
            self.btn_prepare_uninstall.setEnabled(False)

    def _execute_prepare_uninstall(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        selected = [pkg for pkg, state in self.main_app.selected_uninstall_pkgs.items() if state]
        if not selected:
            return

        letter = self.main_app.current_usb.letter
        pkg_to_name = {a["package"]: a.get("display_name", a["package"]) for a in self.main_app.local_apks if a.get("package")}

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
        from ui.components.dialogs import show_confirm_dialog
        if not show_confirm_dialog(self, "Confirm Safe Uninstall USB", confirm_msg, confirm_text="🗑 Prepare Uninstall USB", is_danger=True):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_uninstall_apps_usb,
            letter,
            selected,
            self.main_app.allowed_packages,
            success_title="Safe Uninstall USB Ready",
            success_msg=f"Successfully prepared Safe Uninstall USB on drive {letter}!\n\nSafely unplug and insert into vehicle.",
            error_title="Uninstall Preparation Failed"
        )
