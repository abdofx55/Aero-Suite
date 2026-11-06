"""
uninstall_apps_view.py — Feature 2: Safe Uninstall Applications View.
Allows selecting installed packages to cleanly purge from User and System partitions.
Equipped with deduplication and full localization via core.i18n.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QScrollArea, QFrame
)
import theme
from core.i18n import t
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
        self.lbl_vtitle = QLabel(t("uninstall_apps.view_title", "🛡 SAFE UNINSTALL APPS"))
        self.lbl_vtitle.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme.AMBER_WARN};")
        layout.addWidget(self.lbl_vtitle)

        # Safety Banner
        banner = QFrame()
        banner.setProperty("class", "card")
        b_layout = QVBoxLayout(banner)
        b_layout.setContentsMargins(14, 10, 14, 12)
        self.lbl_banner = QLabel(t("uninstall_apps.banner"))
        self.lbl_banner.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 2px 0 6px 0; line-height: 1.4;")
        self.lbl_banner.setWordWrap(True)
        b_layout.addWidget(self.lbl_banner)
        layout.addWidget(banner)

        # Controls Strip
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
        self.search_edit.setPlaceholderText(t("uninstall_apps.search_placeholder", "🔍 Search Packages to Uninstall (contains name, package)..."))
        self.search_edit.textChanged.connect(self._on_search_changed)
        ctrl_bar.addWidget(self.search_edit)
        layout.addLayout(ctrl_bar)

        # Scroll Area for Packages
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self._update_cards_margins()
        self.cards_layout.setSpacing(4)
        self.scroll.setWidget(self.cards_container)
        layout.addWidget(self.scroll)

        # Action Buttons Strip
        uninst_btn_box = QHBoxLayout()
        uninst_btn_box.setSpacing(10)

        self.btn_prepare_uninstall = QPushButton(t("uninstall_apps.btn_idle", "👆 SELECT AT LEAST ONE APPLICATION TO UNINSTALL"))
        self.btn_prepare_uninstall.setProperty("class", "btnDanger")
        self.btn_prepare_uninstall.setFixedHeight(44)
        self.btn_prepare_uninstall.setEnabled(False)
        self.btn_prepare_uninstall.clicked.connect(self._execute_prepare_uninstall)
        uninst_btn_box.addWidget(self.btn_prepare_uninstall, 3)

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
        uninst_btn_box.addWidget(self.btn_add_basket, 1)

        layout.addLayout(uninst_btn_box)

        self.render_cards()
        self.update_action_button()

    def _get_unique_matching_apps(self):
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
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.cards_map = {}
        unique_matching = self._get_unique_matching_apps()

        if not unique_matching:
            empty_lbl = QLabel(t("uninstall_apps.empty", "No packages found matching search criteria."))
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
            plural = "S" if count > 1 else ""
            self.btn_prepare_uninstall.setText(t("uninstall_apps.btn_action", f"🗑 PREPARE SAFE UNINSTALL USB ({count} APPLICATION{plural} SELECTED)", count=count, plural=plural))
            self.btn_prepare_uninstall.setEnabled(True)
            self.btn_add_basket.setEnabled(True)
        else:
            self.btn_prepare_uninstall.setText(t("uninstall_apps.btn_idle", "👆 SELECT AT LEAST ONE APPLICATION TO UNINSTALL"))
            self.btn_prepare_uninstall.setEnabled(False)
            self.btn_add_basket.setEnabled(False)

    def _on_add_to_basket(self):
        selected = [pkg for pkg, state in self.main_app.selected_uninstall_pkgs.items() if state]
        if not selected:
            return

        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="uninstall_apps",
            title=t("uninstall_apps.view_title", "Uninstall Applications") + f" ({len(selected)})",
            summary=f"حذف {len(selected)} تطبيق ومسح بياناتها",
            config={"packages": selected},
            requires_reboot=False
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

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

        confirm_title = t("uninstall_apps.confirm_title", "Confirm Safe Uninstall USB")
        confirm_msg = t("uninstall_apps.confirm_msg", letter=letter, count=len(selected), apps_list=apps_list)

        from ui.components.dialogs import show_confirm_dialog
        if not show_confirm_dialog(self, confirm_title, confirm_msg, confirm_text=t("uninstall_apps.btn_confirm", "🗑 Prepare Uninstall USB"), is_danger=True):
            return

        # Check if any selected app is in system_apps whitelist or installed under system
        system_priv_whitelist = {"com.qinggan.app.launcher", "com.google.android.gms", "com.google.android.gsf", "com.android.vending", "com.google.android.apps.nbu.files", "com.android.documentsui"}
        has_system_uninstalls = any(p in system_priv_whitelist for p in selected)

        if has_system_uninstalls:
            dyn_msg = t("uninstall_apps.success_msg_system", letter=letter)
        else:
            dyn_msg = t("uninstall_apps.success_msg_user", letter=letter)

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_uninstall_apps_usb,
            letter,
            selected,
            self.main_app.allowed_packages,
            success_title=t("uninstall_apps.success_title", "Safe Uninstall USB Ready"),
            success_msg=dyn_msg,
            error_title="Uninstall Preparation Failed"
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
        self.lbl_vtitle.setText(t("uninstall_apps.view_title", "🛡 SAFE UNINSTALL APPS"))
        self.lbl_banner.setText(t("uninstall_apps.banner"))
        self.btn_all.setText(t("common.select_all", "Select All"))
        self.btn_none.setText(t("common.deselect_all", "Deselect All"))
        self.btn_invert.setText(t("common.invert", "Invert"))
        self.btn_refresh.setText(t("common.refresh", "🔄 Refresh"))
        self.btn_add_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.search_edit.setPlaceholderText(t("uninstall_apps.search_placeholder", "🔍 Search Packages to Uninstall (contains name, package)..."))
        self.update_action_button()
        self.render_cards()
