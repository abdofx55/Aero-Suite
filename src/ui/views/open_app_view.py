"""
open_app_view.py — Feature 3: Launch Specific Application on Car View.
Allows single-selecting an installed APK package to create a zero-reboot launch payload.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QScrollArea, QFrame
)
import theme
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
        lbl_vtitle = QLabel("🚀 LAUNCH APPLICATION ON CAR")
        lbl_vtitle.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        layout.addWidget(lbl_vtitle)

        # Instruction Banner
        banner = QFrame()
        banner.setProperty("class", "card")
        b_layout = QVBoxLayout(banner)
        b_layout.setContentsMargins(14, 10, 14, 10)
        lbl_banner = QLabel(
            "Can't find your installed app on the car dashboard? No problem! 😎 Some apps don't show an icon on the factory home screen. "
            "Select your app here, plug the USB into your car, and it instantly launches directly on screen. Quick, smart, and effortless!"
        )
        lbl_banner.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent;")
        lbl_banner.setWordWrap(True)
        b_layout.addWidget(lbl_banner)
        layout.addWidget(banner)

        # Controls & Search Strip
        ctrl_bar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setFixedHeight(32)
        self.search_edit.setPlaceholderText("🔍 Search Apps to Open (name or package)...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        ctrl_bar.addWidget(self.search_edit)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setFixedHeight(32)
        btn_refresh.clicked.connect(self.main_app._rescan_apks)
        ctrl_bar.addWidget(btn_refresh)
        layout.addLayout(ctrl_bar)

        # Scroll Area for apps
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(0, 0, 10, 0)
        self.cards_layout.setSpacing(4)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        # Action Button
        self.btn_launch = QPushButton("👆 SELECT AN APP FROM THE LIST ABOVE TO PREPARE LAUNCH USB")
        self.btn_launch.setProperty("class", "btnPrimary")
        self.btn_launch.setFixedHeight(44)
        self.btn_launch.setEnabled(False)
        self.btn_launch.clicked.connect(self._execute_prepare_open_app)
        layout.addWidget(self.btn_launch)

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
            empty_lbl = QLabel("No matching applications found.")
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

            # Wiring single-selection clicks
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
            self.btn_launch.setText(f"🚀 PREPARE LAUNCH USB FOR: {display_title.upper()}")
            self.btn_launch.setEnabled(True)
        else:
            self.btn_launch.setText("👆 SELECT AN APP FROM THE LIST ABOVE TO PREPARE LAUNCH USB")
            self.btn_launch.setEnabled(False)

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

        confirm_msg = (
            f"Are you sure you want to prepare Launch USB on drive {letter}?\n\n"
            f"• Target Application: {app_title}\n"
            f"• Package Name: {pkg}\n\n"
            f"When plugged into the vehicle, this payload brings {app_title} to the foreground immediately."
        )
        from ui.components.dialogs import show_confirm_dialog
        if not show_confirm_dialog(self, "Confirm Launch Application USB", confirm_msg, confirm_text="🚀 Prepare Launch USB"):
            return

        import payload_engine
        self.main_app.execute_payload_worker(
            payload_engine.prepare_open_app_usb,
            letter,
            package_name=pkg,
            app_name=app_title,
            success_title="Launch USB Ready",
            success_msg=f"Successfully prepared Launch USB for '{app_title}' on drive {letter}!",
            error_title="Launch USB Preparation Failed"
        )
