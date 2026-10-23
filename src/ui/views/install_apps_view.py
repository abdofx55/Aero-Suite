"""
install_apps_view.py — Feature 1: Install Applications View.
Manages selection of APK packages, per-app configuration (Auto-Launch, Force Portrait,
Block Boot Launch, Target Partition), conflict resolution, and USB preparation.
Localized dynamically via core.i18n.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QScrollArea, QFrame, QMessageBox
)
import theme
from core.i18n import t
from ui.components.app_card import AppCard


class InstallAppsView(QWidget):
    """View for staging and configuring APK installations for Dongfeng head unit."""
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
        title_box = QHBoxLayout()
        self.lbl_vtitle = QLabel(t("install_apps.view_title", "📦 INSTALL APPLICATIONS"))
        self.lbl_vtitle.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        title_box.addWidget(self.lbl_vtitle)

        count = len(self.main_app.local_apks)
        self.install_count_label = QLabel(t("install_apps.count_badge", f"({count} APKs available in repository)", count=count))
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
        self.lbl_desc = QLabel(t("install_apps.banner"))
        self.lbl_desc.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        self.lbl_desc.setWordWrap(True)
        b_layout.addWidget(self.lbl_desc)
        layout.addWidget(banner)

        # Controls & Search Strip
        ctrl_bar = QHBoxLayout()
        self.btn_all = QPushButton(t("common.select_all", "Select All"))
        self.btn_all.setFixedHeight(32)
        self.btn_all.clicked.connect(lambda: self.set_all_selected(True))
        ctrl_bar.addWidget(self.btn_all)

        self.btn_none = QPushButton(t("common.deselect_all", "Deselect All"))
        self.btn_none.setFixedHeight(32)
        self.btn_none.clicked.connect(lambda: self.set_all_selected(False))
        ctrl_bar.addWidget(self.btn_none)

        self.btn_invert = QPushButton(t("common.invert", "Invert"))
        self.btn_invert.setFixedHeight(32)
        self.btn_invert.clicked.connect(self.invert_selection)
        ctrl_bar.addWidget(self.btn_invert)

        self.btn_refresh = QPushButton(t("common.refresh", "🔄 Refresh"))
        self.btn_refresh.setFixedHeight(32)
        self.btn_refresh.clicked.connect(self.main_app._rescan_apks)
        ctrl_bar.addWidget(self.btn_refresh)

        ctrl_bar.addSpacing(10)
        self.search_edit = QLineEdit()
        self.search_edit.setFixedHeight(32)
        self.search_edit.setPlaceholderText(t("install_apps.search_placeholder", "🔍 Search APKs (name, package, file)..."))
        self.search_edit.textChanged.connect(self._on_search_changed)
        ctrl_bar.addWidget(self.search_edit)
        layout.addLayout(ctrl_bar)

        # Scroll Area for APK Cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 10, 0)
        self.cards_layout.setSpacing(5)
        self.scroll.setWidget(self.cards_container)
        layout.addWidget(self.scroll)

        # Action Button
        self.btn_prepare_install = QPushButton(t("install_apps.btn_idle", "👆 SELECT AT LEAST ONE APPLICATION TO INSTALL"))
        self.btn_prepare_install.setProperty("class", "btnPrimary")
        self.btn_prepare_install.setFixedHeight(44)
        self.btn_prepare_install.setEnabled(False)
        self.btn_prepare_install.clicked.connect(self._execute_prepare_install)
        layout.addWidget(self.btn_prepare_install)

        self.render_cards()
        self.update_action_button()

    def render_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.cards_map = {}
        q = self.search_query.strip().lower()
        matching = [
            a for a in self.main_app.local_apks
            if not q or (q in a.get("display_name", "").lower() or q in a.get("package", "").lower() or q in a.get("filename", "").lower())
        ]

        if not matching:
            empty_lbl = QLabel("No APK packages found matching search criteria.")
            empty_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding: 20px; font-size: 13px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(empty_lbl)
            self.cards_layout.addStretch()
            return

        for a in matching:
            fname = a["filename"]
            card = AppCard("install", a)
            is_selected = self.main_app.selected_install_apks.get(fname, False)
            card.chk_main.setChecked(is_selected)
            card.set_selected_visual(is_selected)

            # Auto launch
            card.chk_auto.setChecked(self.main_app.auto_launch_app_filename == fname)
            card.chk_auto.stateChanged.connect(lambda state, fn=fname: self._on_auto_launch_toggled(fn, bool(state)))

            # Force portrait
            card.chk_port.setChecked(self.main_app.per_app_portrait.get(fname, False))
            card.chk_port.stateChanged.connect(lambda state, fn=fname: self.main_app.per_app_portrait.update({fn: bool(state)}))

            # Block boot launch
            card.chk_boot.setChecked(self.main_app.per_app_boot.get(fname, False))
            card.chk_boot.stateChanged.connect(lambda state, fn=fname: self.main_app.per_app_boot.update({fn: bool(state)}))

            # Target dropdown
            cur_target = self.main_app.per_app_target.get(fname, "user")
            card.combo_target.setCurrentIndex(0 if cur_target == "user" else 1)
            card.combo_target.currentIndexChanged.connect(lambda idx, fn=fname: self.main_app.per_app_target.update({fn: "user" if idx == 0 else "system"}))

            # Wire selection interactions
            card.chk_main.clicked.connect(lambda checked, fn=fname: self._on_chk_changed(fn, checked))
            def _make_press_handler(fn=fname):
                return lambda event: self._on_card_pressed(event, fn)
            card.mousePressEvent = _make_press_handler()

            self.cards_layout.addWidget(card)
            self.cards_map[fname] = {
                "card": card,
                "chk_install": card.chk_main,
                "chk_auto": card.chk_auto,
                "chk_port": card.chk_port,
                "chk_boot": card.chk_boot,
                "combo_target": card.combo_target,
                "lbl_size": card.lbl_size
            }

        self.cards_layout.addStretch()

    def _on_card_pressed(self, event, fname: str):
        if event.button() == Qt.LeftButton:
            cur = self.main_app.selected_install_apks.get(fname, False)
            self._on_chk_changed(fname, not cur)

    def _on_chk_changed(self, fname: str, is_checked: bool):
        self.main_app.selected_install_apks[fname] = is_checked
        if fname in self.cards_map:
            item = self.cards_map[fname]
            chk_i = item["chk_install"]
            chk_i.blockSignals(True)
            chk_i.setChecked(is_checked)
            chk_i.blockSignals(False)
            item["card"].set_selected_visual(is_checked)

        if not is_checked and self.main_app.auto_launch_app_filename == fname:
            self.main_app.auto_launch_app_filename = None
            if fname in self.cards_map:
                chk_a = self.cards_map[fname]["chk_auto"]
                chk_a.blockSignals(True)
                chk_a.setChecked(False)
                chk_a.blockSignals(False)
        self.update_action_button()

    def _on_auto_launch_toggled(self, fname: str, is_checked: bool):
        if is_checked:
            self.main_app.auto_launch_app_filename = fname
            for fn, item in self.cards_map.items():
                chk = item["chk_auto"]
                chk.blockSignals(True)
                chk.setChecked(fn == fname)
                chk.blockSignals(False)
        else:
            if self.main_app.auto_launch_app_filename == fname:
                self.main_app.auto_launch_app_filename = None
            if fname in self.cards_map:
                chk = self.cards_map[fname]["chk_auto"]
                chk.blockSignals(True)
                chk.setChecked(False)
                chk.blockSignals(False)

    def set_all_selected(self, state: bool):
        q = self.search_query.strip().lower()
        for a in self.main_app.local_apks:
            fname = a["filename"]
            if not q or (q in a.get("display_name", "").lower() or q in a.get("package", "").lower() or q in fname.lower()):
                self.main_app.selected_install_apks[fname] = state
                if not state and self.main_app.auto_launch_app_filename == fname:
                    self.main_app.auto_launch_app_filename = None
                if fname in self.cards_map:
                    item = self.cards_map[fname]
                    chk_i = item["chk_install"]
                    chk_i.blockSignals(True)
                    chk_i.setChecked(state)
                    chk_i.blockSignals(False)
                    item["card"].set_selected_visual(state)
                    if not state:
                        chk_a = item["chk_auto"]
                        chk_a.blockSignals(True)
                        chk_a.setChecked(False)
                        chk_a.blockSignals(False)
        self.update_action_button()

    def invert_selection(self):
        q = self.search_query.strip().lower()
        for a in self.main_app.local_apks:
            fname = a["filename"]
            if not q or (q in a.get("display_name", "").lower() or q in a.get("package", "").lower() or q in fname.lower()):
                new_state = not self.main_app.selected_install_apks.get(fname, False)
                self.main_app.selected_install_apks[fname] = new_state
                if not new_state and self.main_app.auto_launch_app_filename == fname:
                    self.main_app.auto_launch_app_filename = None
                if fname in self.cards_map:
                    item = self.cards_map[fname]
                    chk_i = item["chk_install"]
                    chk_i.blockSignals(True)
                    chk_i.setChecked(new_state)
                    chk_i.blockSignals(False)
                    item["card"].set_selected_visual(new_state)
                    if not new_state:
                        chk_a = item["chk_auto"]
                        chk_a.blockSignals(True)
                        chk_a.setChecked(False)
                        chk_a.blockSignals(False)
        self.update_action_button()

    def _on_search_changed(self, text: str):
        self.search_query = text
        self.render_cards()

    def update_action_button(self):
        selected_count = sum(1 for v in self.main_app.selected_install_apks.values() if v)
        if selected_count > 0:
            plural = "S" if selected_count > 1 else ""
            self.btn_prepare_install.setText(t("install_apps.btn_action", f"⚡ PREPARE INSTALL USB ({selected_count} APPLICATION{plural} SELECTED)", count=selected_count, plural=plural))
            self.btn_prepare_install.setEnabled(True)
        else:
            self.btn_prepare_install.setText(t("install_apps.btn_idle", "👆 SELECT AT LEAST ONE APPLICATION TO INSTALL"))
            self.btn_prepare_install.setEnabled(False)

    def _execute_prepare_install(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        selected = [a for a in self.main_app.local_apks if self.main_app.selected_install_apks.get(a["filename"], False)]
        if not selected:
            return

        # System App & Auto-Launch Conflict Check
        system_apps = [a for a in selected if self.main_app.per_app_target.get(a["filename"], "user") == "system"]
        auto_launch_app = next((a for a in selected if a["filename"] == self.main_app.auto_launch_app_filename), None) if self.main_app.auto_launch_app_filename else None

        if system_apps and auto_launch_app:
            sys_names = ", ".join(f"'{a['display_name']}'" for a in system_apps[:3])
            if len(system_apps) > 3:
                sys_names += f" and {len(system_apps) - 3} more"

            msg_box = QMessageBox(self)
            msg_box.setWindowModality(Qt.WindowModal)
            msg_box.setWindowTitle(t("install_apps.conflict_title", "System App & Auto-Launch Conflict"))
            msg_box.setIcon(QMessageBox.Warning)
            conflict_msg = t(
                "install_apps.conflict_msg",
                names=sys_names,
                auto_app=auto_launch_app["display_name"]
            )
            msg_box.setText(conflict_msg)

            btn_auto = msg_box.addButton(t("install_apps.btn_uncheck_auto", "⚡ Uncheck Auto-Launch & Proceed"), QMessageBox.ActionRole)
            btn_back = msg_box.addButton(t("install_apps.btn_go_back", "Go Back & Edit"), QMessageBox.RejectRole)

            btn_auto.setStyleSheet(f"background-color: {theme.CYAN_PRIMARY}; color: black; font-weight: bold; padding: 6px 14px; border-radius: 6px; min-height: 20px;")
            btn_back.setStyleSheet(f"background-color: {theme.SURFACE_3}; color: {theme.TEXT_PRIMARY}; font-weight: 600; padding: 6px 14px; border: 1px solid {theme.BORDER_SLATE}; border-radius: 6px; min-height: 20px;")

            msg_box.setDefaultButton(btn_back)
            msg_box.exec()

            if msg_box.clickedButton() == btn_auto:
                self._on_auto_launch_toggled(auto_launch_app["filename"], False)
                self.main_app.log_terminal(t("logs.auto_launch_disabled_reboot", f"Auto-Launch disabled for '{auto_launch_app['display_name']}' due to System App reboot requirement.", app_name=auto_launch_app['display_name']), "mint")
            else:
                self.main_app.log_terminal(t("logs.auto_launch_conflict_paused", "Installation paused: System apps require a reboot, which conflicts with Auto-Launch. Please adjust your configuration."), "warn")
                return

        letter = self.main_app.current_usb.letter
        if len(selected) <= 15:
            apps_list = "\n".join(f"  {i+1}. {a['display_name']} (~{a['size_mb']} MB)" for i, a in enumerate(selected))
        else:
            first_12 = "\n".join(f"  {i+1}. {a['display_name']} (~{a['size_mb']} MB)" for i, a in enumerate(selected[:12]))
            remaining = len(selected) - 12
            apps_list = f"{first_12}\n  ... and {remaining} more applications"

        auto_launch_pkg = ""
        if self.main_app.auto_launch_app_filename:
            target_a = next((a for a in selected if a["filename"] == self.main_app.auto_launch_app_filename), None)
            if target_a and target_a.get("package"):
                auto_launch_pkg = target_a["package"]
                self.main_app.log_terminal(t("logs.auto_launch_target_set", f"Auto Launch target set: {target_a['display_name']} ({auto_launch_pkg})", app_name=target_a['display_name'], pkg=auto_launch_pkg), "mint")
            else:
                self.main_app.log_terminal(t("logs.auto_launch_skipped_not_selected", f"Note: Auto Launch app '{self.main_app.auto_launch_app_filename}' was not selected for installation; Auto Launch will be skipped.", app_name=self.main_app.auto_launch_app_filename), "warn")

        auto_info = f"\n\n🚀 Auto-Launch App: {self.main_app.auto_launch_app_filename}" if auto_launch_pkg else ""
        confirm_title = t("install_apps.confirm_title", "Confirm Application Installation USB")
        confirm_msg = t(
            "install_apps.confirm_msg",
            letter=letter,
            count=len(selected),
            apps_list=apps_list,
            auto_info=auto_info
        )
        from ui.components.dialogs import show_confirm_dialog
        if not show_confirm_dialog(self, confirm_title, confirm_msg, confirm_text=t("install_apps.btn_confirm", "⚡ Prepare Install USB")):
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
                "force_portrait": self.main_app.per_app_portrait.get(f, False),
                "install_target": self.main_app.per_app_target.get(f, "user"),
                "block_boot": self.main_app.per_app_boot.get(f, False)
            })

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_install_apps_usb,
            letter,
            selected_payload,
            auto_launch_package=auto_launch_pkg,
            success_title=t("install_apps.success_title", "Install Apps USB Ready"),
            success_msg=t("install_apps.success_msg", letter=letter),
            error_title="Install Apps USB Failed"
        )

    def retranslate_ui(self):
        """Re-translates all static and dynamic UI elements for this view."""
        self.lbl_vtitle.setText(t("install_apps.view_title", "📦 INSTALL APPLICATIONS"))
        count = len(self.main_app.local_apks)
        self.install_count_label.setText(t("install_apps.count_badge", f"({count} APKs available in repository)", count=count))
        self.lbl_desc.setText(t("install_apps.banner"))
        self.btn_all.setText(t("common.select_all", "Select All"))
        self.btn_none.setText(t("common.deselect_all", "Deselect All"))
        self.btn_invert.setText(t("common.invert", "Invert"))
        self.btn_refresh.setText(t("common.refresh", "🔄 Refresh"))
        self.search_edit.setPlaceholderText(t("install_apps.search_placeholder", "🔍 Search APKs (name, package, file)..."))
        self.update_action_button()
        self.render_cards()
