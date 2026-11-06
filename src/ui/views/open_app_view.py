"""
open_app_view.py — Feature 3: Launch Specific Application on Car View.
Allows single-selecting an installed APK package to create a zero-reboot launch payload.
Localized dynamically via core.i18n.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QScrollArea, QFrame
)
import theme
from core.i18n import t
from ui.components.app_card import AppCard


class OpenAppView(QWidget):
    """View for configuring single-app launch payloads."""
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.row_items = {}
        self.search_query = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Header Title
        self.lbl_vtitle = QLabel(t("open_app.view_title", "🚀 LAUNCH APPLICATION ON CAR"))
        self.lbl_vtitle.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        layout.addWidget(self.lbl_vtitle)

        # Instruction Banner
        banner = QFrame()
        banner.setProperty("class", "card")
        b_layout = QVBoxLayout(banner)
        b_layout.setContentsMargins(14, 10, 14, 12)
        self.lbl_banner = QLabel(t("open_app.banner"))
        self.lbl_banner.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 2px 0 6px 0; line-height: 1.4;")
        self.lbl_banner.setWordWrap(True)
        b_layout.addWidget(self.lbl_banner)
        layout.addWidget(banner)

        # Controls & Search Strip
        ctrl_bar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setFixedHeight(32)
        self.search_edit.setPlaceholderText(t("open_app.search_placeholder", "🔍 Search Apps to Open (name or package)..."))
        self.search_edit.textChanged.connect(self._on_search_changed)
        ctrl_bar.addWidget(self.search_edit)

        self.btn_refresh = QPushButton(t("common.refresh", "🔄 Refresh"))
        self.btn_refresh.setFixedHeight(32)
        self.btn_refresh.clicked.connect(self.main_app._rescan_apks)
        ctrl_bar.addWidget(self.btn_refresh)
        layout.addLayout(ctrl_bar)

        # Scroll Area for apps
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.cards_layout = QVBoxLayout(self.container)
        self._update_cards_margins()
        self.cards_layout.setSpacing(4)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        # Action Buttons Strip
        btn_action_box = QHBoxLayout()
        btn_action_box.setSpacing(10)

        self.btn_launch = QPushButton(t("open_app.btn_idle", "👆 SELECT AN APP FROM THE LIST ABOVE TO PREPARE LAUNCH USB"))
        self.btn_launch.setProperty("class", "btnPrimary")
        self.btn_launch.setFixedHeight(44)
        self.btn_launch.setEnabled(False)
        self.btn_launch.clicked.connect(self._execute_prepare_open_app)
        btn_action_box.addWidget(self.btn_launch, 3)

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

        self.render_rows()

    def render_rows(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.row_items = {}
        q = self.search_query.strip().lower()
        matching = [
            a for a in self.main_app.local_apks
            if a.get("package") and (not q or q in a.get("display_name", "").lower() or q in a.get("package", "").lower() or q in a.get("filename", "").lower())
        ]

        if not matching:
            empty_lbl = QLabel(t("open_app.empty", "No matching applications found."))
            empty_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding: 20px; font-size: 13px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(empty_lbl)
            self.cards_layout.addStretch()
            return

        for a in matching:
            fname = a["filename"]
            card = AppCard("open", a)
            is_cur = (fname == self.main_app.selected_open_app_filename and bool(self.main_app.selected_open_app_filename))
            card.chk_main.setChecked(is_cur)
            card.set_selected_visual(is_cur)

            card.chk_main.clicked.connect(lambda checked, fn=fname: self._on_item_clicked(fn))
            def _make_press_handler(fn=fname):
                return lambda event: self._on_card_pressed(event, fn)
            card.mousePressEvent = _make_press_handler()

            self.cards_layout.addWidget(card)
            self.row_items[fname] = {
                "row": card,
                "chk": card.chk_main,
                "lbl_size": card.lbl_size
            }

        self.cards_layout.addStretch()
        self.update_action_button()

    def _on_card_pressed(self, event, fname: str):
        if event.button() == Qt.LeftButton:
            self._on_item_clicked(fname)

    def _on_item_clicked(self, clicked_filename: str):
        if self.main_app.selected_open_app_filename == clicked_filename:
            self.main_app.selected_open_app_filename = ""
        else:
            self.main_app.selected_open_app_filename = clicked_filename
        self.sync_rows()

    def sync_rows(self):
        for fn, item in self.row_items.items():
            is_cur = (fn == self.main_app.selected_open_app_filename and bool(self.main_app.selected_open_app_filename))
            item["chk"].blockSignals(True)
            item["chk"].setChecked(is_cur)
            item["chk"].blockSignals(False)
            item["row"].set_selected_visual(is_cur)
        self.update_action_button()

    def _on_search_changed(self, text: str):
        self.search_query = text
        self.render_rows()

    def update_action_button(self):
        if self.main_app.selected_open_app_filename:
            selected_app_info = next((a for a in self.main_app.local_apks if a["filename"] == self.main_app.selected_open_app_filename), None)
            selected_title = selected_app_info["display_name"] if selected_app_info else self.main_app.selected_open_app_filename
            display_title = selected_title if len(selected_title) <= 30 else (selected_title[:27] + "...")
            self.btn_launch.setText(t("open_app.btn_action", f"🚀 PREPARE LAUNCH USB FOR: {display_title.upper()}", app_name=display_title.upper()))
            self.btn_launch.setEnabled(True)
            self.btn_add_basket.setEnabled(True)
        else:
            self.btn_launch.setText(t("open_app.btn_idle", "👆 SELECT AN APP FROM THE LIST ABOVE TO PREPARE LAUNCH USB"))
            self.btn_launch.setEnabled(False)
            self.btn_add_basket.setEnabled(False)

    def _on_add_to_basket(self):
        selected_app_info = next((a for a in self.main_app.local_apks if a["filename"] == self.main_app.selected_open_app_filename), None)
        if not selected_app_info:
            return

        app_title = selected_app_info["display_name"]
        pkg = selected_app_info["package"]

        # Trap Launch Conflict
        allowed = self.main_app.prompt_launch_target_selection("open_app", pkg, app_title)
        if not allowed:
            return

        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="open_app",
            title=t("open_app.view_title", "Launch Application") + f": {app_title}",
            summary=f"{app_title} ({pkg})",
            config={"package_name": pkg, "app_name": app_title},
            requires_reboot=False,
            launch_target_pkg=pkg,
            launch_target_name=app_title
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def _execute_prepare_open_app(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        selected_app_info = next((a for a in self.main_app.local_apks if a["filename"] == self.main_app.selected_open_app_filename), None)
        if not selected_app_info:
            return

        app_title = selected_app_info["display_name"]
        pkg = selected_app_info["package"]
        letter = self.main_app.current_usb.letter

        confirm_title = t("open_app.confirm_title", "Confirm Launch Application USB")
        confirm_msg = t("open_app.confirm_msg", letter=letter, app_title=app_title, pkg=pkg)
        from ui.components.dialogs import show_confirm_dialog
        if not show_confirm_dialog(self, confirm_title, confirm_msg, confirm_text=t("open_app.btn_confirm", "🚀 Prepare Launch USB")):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_open_app_usb,
            letter,
            package_name=pkg,
            app_name=app_title,
            success_title=t("open_app.success_title", "Launch USB Ready"),
            success_msg=t("open_app.success_msg", app_title=app_title, letter=letter),
            error_title="Launch USB Preparation Failed"
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
        self.lbl_vtitle.setText(t("open_app.view_title", "🚀 LAUNCH APPLICATION ON CAR"))
        self.lbl_banner.setText(t("open_app.banner"))
        self.search_edit.setPlaceholderText(t("open_app.search_placeholder", "🔍 Search Apps to Open (name or package)..."))
        self.btn_refresh.setText(t("common.refresh", "🔄 Refresh"))
        self.btn_add_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.update_action_button()
        self.render_rows()
