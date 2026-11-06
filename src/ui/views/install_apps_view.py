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
from ui.components.app_card import AppCard, variant_sort_key


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
        b_layout.setContentsMargins(14, 10, 14, 12)
        b_layout.setSpacing(2)
        self.lbl_desc = QLabel(t("install_apps.banner"))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 2px 0 6px 0; line-height: 1.4;")
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
        self._update_cards_margins()
        self.cards_layout.setSpacing(5)
        self.scroll.setWidget(self.cards_container)
        layout.addWidget(self.scroll)

        # Action Buttons Strip
        btn_action_box = QHBoxLayout()
        btn_action_box.setSpacing(10)

        self.btn_prepare_install = QPushButton(t("install_apps.btn_idle", "👆 SELECT AT LEAST ONE APPLICATION TO INSTALL"))
        self.btn_prepare_install.setProperty("class", "btnPrimary")
        self.btn_prepare_install.setFixedHeight(44)
        self.btn_prepare_install.setEnabled(False)
        self.btn_prepare_install.clicked.connect(self._execute_prepare_install)
        btn_action_box.addWidget(self.btn_prepare_install, 3)

        self.btn_add_basket = QPushButton(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.btn_add_basket.setFixedHeight(44)
        self.btn_add_basket.setEnabled(False)
        self.btn_add_basket.setCursor(Qt.PointingHandCursor)
        self.btn_add_basket.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.SURFACE_2};
                border: 1px solid {theme.BORDER_CYAN};
                color: {theme.CYAN_PRIMARY};
                border-radius: 6px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme.CYAN_ALPHA_15};
            }}
            QPushButton:disabled {{
                border-color: {theme.BORDER_SLATE};
                color: {theme.TEXT_MUTED};
            }}
        """)
        self.btn_add_basket.clicked.connect(self._on_add_to_basket)
        btn_action_box.addWidget(self.btn_add_basket, 1)

        layout.addLayout(btn_action_box)

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
            empty_lbl = QLabel(t("install_apps.no_apks_found", "No APK packages found matching search criteria."))
            empty_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding: 20px; font-size: 13px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(empty_lbl)
            self.cards_layout.addStretch()
            return

        from collections import OrderedDict
        from core.i18n import get_i18n
        active_lang = get_i18n().current_lang

        # Group matching APKs by package name (preserving distinct cards for unknown/empty packages)
        grouped_apks = OrderedDict()
        for a in matching:
            pkg = a.get("package")
            key = pkg if (pkg and pkg != "unknown.package") else a.get("filename")
            grouped_apks.setdefault(key, []).append(a)

        for key, variants in grouped_apks.items():
            # Sort variants: locale-aware first, then newest version, then size
            if len(variants) > 1:
                variants = sorted(variants, key=lambda it: variant_sort_key(it, active_lang=active_lang), reverse=True)

            # Check if any variant in this group is currently selected in app state
            chosen_variant = variants[0]
            for v in variants:
                fn = v.get("filename", "")
                if self.main_app.selected_install_apks.get(fn, False):
                    chosen_variant = v
                    break

            top_variant = variants[0]
            card = AppCard(
                "install",
                top_variant,
                variants=variants,
                on_variant_changed=self._on_card_variant_changed
            )

            # If a non-top variant was previously selected, activate it in card
            if chosen_variant != top_variant:
                card.set_active_variant_by_filename(chosen_variant.get("filename", ""))

            fname = card.fname
            is_selected = self.main_app.selected_install_apks.get(fname, False)
            card.chk_main.setChecked(is_selected)
            card.set_selected_visual(is_selected)

            # Auto launch
            card.chk_auto.setChecked(self.main_app.auto_launch_app_filename == fname)
            def _on_auto_toggled(state, c=card):
                fn = c.fname
                if bool(state) and not self.main_app.selected_install_apks.get(fn, False):
                    self._on_chk_changed(fn, True)
                self._on_auto_launch_toggled(fn, bool(state))
            card.chk_auto.stateChanged.connect(_on_auto_toggled)

            # Force portrait
            card.chk_port.setChecked(self.main_app.per_app_portrait.get(fname, False))
            def _on_port_toggled(state, c=card):
                fn = c.fname
                self.main_app.per_app_portrait[fn] = bool(state)
                if bool(state) and not self.main_app.selected_install_apks.get(fn, False):
                    self._on_chk_changed(fn, True)
            card.chk_port.stateChanged.connect(_on_port_toggled)

            # Block boot launch (Block Autostart)
            card.chk_boot.setChecked(self.main_app.per_app_boot.get(fname, False))
            def _on_boot_toggled(state, c=card):
                fn = c.fname
                self.main_app.per_app_boot[fn] = bool(state)
                if bool(state) and not self.main_app.selected_install_apks.get(fn, False):
                    self._on_chk_changed(fn, True)
            card.chk_boot.stateChanged.connect(_on_boot_toggled)

            # Target dropdown
            cur_target = self.main_app.per_app_target.get(fname, "user")
            card.combo_target.setCurrentIndex(0 if cur_target == "user" else 1)
            def _on_target_changed(idx, c=card):
                fn = c.fname
                self.main_app.per_app_target[fn] = "user" if idx == 0 else "system"
                if not self.main_app.selected_install_apks.get(fn, False):
                    self._on_chk_changed(fn, True)
            card.combo_target.currentIndexChanged.connect(_on_target_changed)

            # Wire selection interactions
            card.chk_main.clicked.connect(lambda checked, c=card: self._on_chk_changed(c.fname, checked))
            card.mousePressEvent = lambda event, c=card: self._on_card_pressed(event, c.fname)

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

    def _on_card_variant_changed(self, card, old_fname: str, new_fname: str):
        was_selected = self.main_app.selected_install_apks.get(old_fname, False)
        if was_selected:
            self.main_app.selected_install_apks[old_fname] = False
            self.main_app.selected_install_apks[new_fname] = True

        if self.main_app.auto_launch_app_filename == old_fname:
            self.main_app.auto_launch_app_filename = new_fname

        if old_fname in self.main_app.per_app_portrait:
            self.main_app.per_app_portrait[new_fname] = self.main_app.per_app_portrait.pop(old_fname)
        if old_fname in self.main_app.per_app_boot:
            self.main_app.per_app_boot[new_fname] = self.main_app.per_app_boot.pop(old_fname)
        if old_fname in self.main_app.per_app_target:
            self.main_app.per_app_target[new_fname] = self.main_app.per_app_target.pop(old_fname)

        if old_fname in self.cards_map:
            self.cards_map[new_fname] = self.cards_map.pop(old_fname)

        card.chk_port.blockSignals(True)
        card.chk_port.setChecked(self.main_app.per_app_portrait.get(new_fname, False))
        card.chk_port.blockSignals(False)

        card.chk_boot.blockSignals(True)
        card.chk_boot.setChecked(self.main_app.per_app_boot.get(new_fname, False))
        card.chk_boot.blockSignals(False)

        card.combo_target.blockSignals(True)
        t_val = self.main_app.per_app_target.get(new_fname, "user")
        card.combo_target.setCurrentIndex(0 if t_val == "user" else 1)
        card.combo_target.blockSignals(False)

        card.chk_auto.blockSignals(True)
        card.chk_auto.setChecked(self.main_app.auto_launch_app_filename == new_fname)
        card.chk_auto.blockSignals(False)

        self.update_action_button()

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

            # Ensure any other variant of this card is unchecked in app state
            card = item["card"]
            if hasattr(card, "variants") and card.variants:
                for v in card.variants:
                    v_fn = v.get("filename", "")
                    if v_fn and v_fn != fname:
                        self.main_app.selected_install_apks[v_fn] = False

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
            target_a = next((a for a in self.main_app.local_apks if a["filename"] == fname), None)
            if target_a and hasattr(self.main_app, "prompt_launch_target_selection"):
                allowed = self.main_app.prompt_launch_target_selection("install_apps", target_a.get("package", ""), target_a.get("display_name", fname))
                if not allowed:
                    if fname in self.cards_map:
                        chk = self.cards_map[fname]["chk_auto"]
                        chk.blockSignals(True)
                        chk.setChecked(False)
                        chk.blockSignals(False)
                    return

            self.main_app.auto_launch_app_filename = fname
            for fn, item in self.cards_map.items():
                chk = item["chk_auto"]
                chk.blockSignals(True)
                chk.setChecked(fn == fname)
                chk.blockSignals(False)
        else:
            if self.main_app.auto_launch_app_filename == fname:
                self.main_app.auto_launch_app_filename = None
                if hasattr(self.main_app, "basket"):
                    cur = self.main_app.basket.get_current_launch_target()
                    if cur and cur[0] == "install_apps":
                        self.main_app.basket.clear_all_launch_targets()
            if fname in self.cards_map:
                chk = self.cards_map[fname]["chk_auto"]
                chk.blockSignals(True)
                chk.setChecked(False)
                chk.blockSignals(False)

    def set_all_selected(self, state: bool):
        if not state:
            for a in self.main_app.local_apks:
                fname = a["filename"]
                self.main_app.selected_install_apks[fname] = False
                self.main_app.per_app_portrait[fname] = False
                self.main_app.per_app_boot[fname] = False
                self.main_app.per_app_target[fname] = "user"
            self.main_app.auto_launch_app_filename = None

            for fname, item in self.cards_map.items():
                chk_i = item["chk_install"]
                chk_i.blockSignals(True)
                chk_i.setChecked(False)
                chk_i.blockSignals(False)
                item["card"].set_selected_visual(False)

                chk_a = item["chk_auto"]
                chk_a.blockSignals(True)
                chk_a.setChecked(False)
                chk_a.blockSignals(False)

                chk_p = item["chk_port"]
                chk_p.blockSignals(True)
                chk_p.setChecked(False)
                chk_p.blockSignals(False)

                chk_b = item["chk_boot"]
                chk_b.blockSignals(True)
                chk_b.setChecked(False)
                chk_b.blockSignals(False)

                combo = item["combo_target"]
                combo.blockSignals(True)
                combo.setCurrentIndex(0)
                combo.blockSignals(False)
        else:
            for fname, item in self.cards_map.items():
                card = item["card"]
                fn = card.fname
                if hasattr(card, "variants") and card.variants:
                    for v in card.variants:
                        v_fn = v.get("filename", "")
                        if v_fn and v_fn != fn:
                            self.main_app.selected_install_apks[v_fn] = False

                self.main_app.selected_install_apks[fn] = True
                chk_i = item["chk_install"]
                chk_i.blockSignals(True)
                chk_i.setChecked(True)
                chk_i.blockSignals(False)
                card.set_selected_visual(True)

        self.update_action_button()

    def invert_selection(self):
        for fname, item in self.cards_map.items():
            card = item["card"]
            fn = card.fname
            cur = self.main_app.selected_install_apks.get(fn, False)
            new_state = not cur

            if hasattr(card, "variants") and card.variants:
                for v in card.variants:
                    v_fn = v.get("filename", "")
                    if v_fn and v_fn != fn:
                        self.main_app.selected_install_apks[v_fn] = False

            self.main_app.selected_install_apks[fn] = new_state
            if not new_state and self.main_app.auto_launch_app_filename == fn:
                self.main_app.auto_launch_app_filename = None

            chk_i = item["chk_install"]
            chk_i.blockSignals(True)
            chk_i.setChecked(new_state)
            chk_i.blockSignals(False)
            card.set_selected_visual(new_state)

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
            self.btn_add_basket.setEnabled(True)
        else:
            self.btn_prepare_install.setText(t("install_apps.btn_idle", "👆 SELECT AT LEAST ONE APPLICATION TO INSTALL"))
            self.btn_prepare_install.setEnabled(False)
            self.btn_add_basket.setEnabled(False)

    def _on_add_to_basket(self):
        selected = [a for a in self.main_app.local_apks if self.main_app.selected_install_apks.get(a["filename"], False)]
        if not selected:
            return

        # Deduplicate packages as safety guard (keep single variant per package)
        seen_pkgs = set()
        deduped = []
        for a in selected:
            pkg = a.get("package")
            if pkg and pkg != "unknown.package":
                if pkg in seen_pkgs:
                    continue
                seen_pkgs.add(pkg)
            deduped.append(a)
        selected = deduped

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

        auto_launch_pkg = ""
        auto_launch_name = ""
        if self.main_app.auto_launch_app_filename:
            target_a = next((a for a in selected if a["filename"] == self.main_app.auto_launch_app_filename), None)
            if target_a and target_a.get("package"):
                auto_launch_pkg = target_a["package"]
                auto_launch_name = target_a["display_name"]

        has_sys = any(a.get("install_target") == "system" for a in selected_payload)
        summary = f"{len(selected_payload)} application(s)"
        if has_sys:
            summary += " (Includes System Apps)"
        if auto_launch_pkg:
            summary += f" • Auto-Launch: {auto_launch_name}"

        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="install_apps",
            title=t("install_apps.view_title", "Install Applications") + f" ({len(selected_payload)})",
            summary=summary,
            config={"selected_apks": selected_payload, "auto_launch_package": auto_launch_pkg},
            requires_reboot=has_sys,
            launch_target_pkg=auto_launch_pkg if auto_launch_pkg else None,
            launch_target_name=auto_launch_name if auto_launch_pkg else None
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def _execute_prepare_install(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        selected = [a for a in self.main_app.local_apks if self.main_app.selected_install_apks.get(a["filename"], False)]
        if not selected:
            return

        # Deduplicate packages as safety guard (keep single variant per package)
        seen_pkgs = set()
        deduped = []
        for a in selected:
            pkg = a.get("package")
            if pkg and pkg != "unknown.package":
                if pkg in seen_pkgs:
                    continue
                seen_pkgs.add(pkg)
            deduped.append(a)
        selected = deduped

        # System App & Auto-Launch Conflict Check
        system_apps = [a for a in selected if self.main_app.per_app_target.get(a["filename"], "user") == "system"]
        auto_launch_app = next((a for a in selected if a["filename"] == self.main_app.auto_launch_app_filename), None) if self.main_app.auto_launch_app_filename else None

        if system_apps and auto_launch_app:
            sys_names = ", ".join(f"'{a['display_name']}'" for a in system_apps[:3])
            if len(system_apps) > 3:
                sys_names += f" and {len(system_apps) - 3} more"

            from ui.components.dialogs import show_confirm_dialog
            conflict_title = t("install_apps.conflict_title", "System App & Auto-Launch Conflict")
            conflict_msg = t(
                "install_apps.conflict_msg",
                names=sys_names,
                auto_app=auto_launch_app["display_name"]
            )
            proceed = show_confirm_dialog(
                self,
                conflict_title,
                conflict_msg,
                confirm_text=t("install_apps.btn_uncheck_auto", "⚡ Uncheck Auto-Launch & Proceed"),
                cancel_text=t("install_apps.btn_go_back", "Go Back & Edit"),
                is_danger=True
            )

            if proceed:
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

        # Compute dynamic success dialog message based on installed apps & targets
        has_sys = any(a.get("install_target") == "system" for a in selected_payload)
        has_usr = any(a.get("install_target") == "user" for a in selected_payload)
        
        if has_sys and has_usr:
            dyn_msg = t("install_apps.success_msg_mixed", letter=letter, auto_info=auto_info)
        elif has_sys:
            dyn_msg = t("install_apps.success_msg_system", letter=letter)
        else:
            dyn_msg = t("install_apps.success_msg_user", letter=letter, auto_info=auto_info)

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_install_apps_usb,
            letter,
            selected_payload,
            auto_launch_package=auto_launch_pkg,
            success_title=t("install_apps.success_title", "Install Apps USB Ready"),
            success_msg=dyn_msg,
            error_title="Install Apps USB Failed"
        )

    def _update_cards_margins(self):
        """Sets safe margins from the scrollbar: in RTL, the scrollbar is on the left; in LTR, on the right."""
        from core.i18n import get_i18n
        if get_i18n().is_rtl():
            self.cards_layout.setContentsMargins(14, 0, 4, 0)
        else:
            self.cards_layout.setContentsMargins(4, 0, 14, 0)

    def retranslate_ui(self):
        """Re-translates all static and dynamic UI elements for this view."""
        self._update_cards_margins()
        self.lbl_vtitle.setText(t("install_apps.view_title", "📦 INSTALL APPLICATIONS"))
        count = len(self.main_app.local_apks)
        self.install_count_label.setText(t("install_apps.count_badge", f"({count} APKs available in repository)", count=count))
        self.lbl_desc.setText(t("install_apps.banner"))
        self.btn_all.setText(t("common.select_all", "Select All"))
        self.btn_none.setText(t("common.deselect_all", "Deselect All"))
        self.btn_invert.setText(t("common.invert", "Invert"))
        self.btn_refresh.setText(t("common.refresh", "🔄 Refresh"))
        self.btn_add_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.search_edit.setPlaceholderText(t("install_apps.search_placeholder", "🔍 Search APKs (name, package, file)..."))
        self.update_action_button()
        self.render_cards()
