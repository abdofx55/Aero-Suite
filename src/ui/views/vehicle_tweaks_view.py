"""
vehicle_tweaks_view.py — Advanced Vehicle Tweaks & Comfort Controls View.
Mirrors the high-performance layout of InstallAppsView:
- Checkbox selection for granular payload creation
- Per-feature Action Dropdown (Enable / Disable)
- Real-time search and filter
- Single unified Action Button to generate customized USB payload
- Extensible data model based on core.vehicle_tweaks_data
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QScrollArea, QFrame
)
import theme
from core.i18n import t, get_i18n
from core.vehicle_tweaks_data import get_all_vehicle_tweaks
from ui.components.tweak_card import VehicleTweakCard
from payloads.vehicle_tweaks import prepare_vehicle_tweaks_usb


class VehicleTweaksView(QWidget):
    """View for configuring and applying advanced Dongfeng Shine CAN-Bus tweaks."""
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.cards = []
        self.search_query = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # 1. Header Title & Count Badge
        title_box = QHBoxLayout()
        self.lbl_vtitle = QLabel(t("tweaks.view_title", "🚗 VEHICLE CUSTOMIZATION & TWEAKS"))
        self.lbl_vtitle.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        title_box.addWidget(self.lbl_vtitle)

        tweaks = get_all_vehicle_tweaks()
        count = len(tweaks)
        self.tweaks_count_label = QLabel(t("tweaks.count_badge", f"({count} Features Available)", count=count))
        self.tweaks_count_label.setStyleSheet(
            f"font-size: 11px; color: {theme.CYAN_PRIMARY}; "
            f"background-color: {theme.CYAN_ALPHA_15}; border: 1px solid {theme.BORDER_CYAN}; "
            f"border-radius: 10px; padding: 1px 8px;"
        )
        title_box.addWidget(self.tweaks_count_label)
        title_box.addStretch()
        layout.addLayout(title_box)

        # 2. Description Banner
        banner = QFrame()
        banner.setProperty("class", "card")
        b_layout = QVBoxLayout(banner)
        b_layout.setContentsMargins(14, 10, 14, 12)
        b_layout.setSpacing(2)
        self.lbl_desc = QLabel(t(
            "tweaks.banner",
            "Select specific vehicle features to customize. Only selected features are written to the USB flash drive with their chosen action (Enable or Disable), leaving all other vehicle settings untouched."
        ))
        self.lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; padding: 2px 0 6px 0; line-height: 1.4;")
        self.lbl_desc.setWordWrap(True)
        b_layout.addWidget(self.lbl_desc)
        layout.addWidget(banner)

        # 3. Controls & Search Bar
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

        ctrl_bar.addSpacing(10)
        self.search_edit = QLineEdit()
        self.search_edit.setFixedHeight(32)
        self.search_edit.setPlaceholderText(t("tweaks.search_placeholder", "🔍 Search vehicle features..."))
        self.search_edit.textChanged.connect(self._on_search_changed)
        ctrl_bar.addWidget(self.search_edit)
        layout.addLayout(ctrl_bar)

        # 4. Scroll Area for Tweak Cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self._update_cards_margins()
        self.cards_layout.setSpacing(6)
        self.scroll.setWidget(self.cards_container)
        layout.addWidget(self.scroll)

        # 5. Bottom Action Buttons Strip
        twk_btn_box = QHBoxLayout()
        twk_btn_box.setSpacing(10)

        self.btn_prepare = QPushButton(t("tweaks.btn_idle", "👆 SELECT AT LEAST ONE FEATURE TO PREPARE USB"))
        self.btn_prepare.setProperty("class", "btnPrimary")
        self.btn_prepare.setFixedHeight(44)
        self.btn_prepare.setEnabled(False)
        self.btn_prepare.clicked.connect(self._execute_prepare_tweaks)
        twk_btn_box.addWidget(self.btn_prepare, 3)

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
        twk_btn_box.addWidget(self.btn_add_basket, 1)

        layout.addLayout(twk_btn_box)

        self.render_cards()
        self.update_action_button()

    def render_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.cards = []
        tweaks = get_all_vehicle_tweaks()
        q = self.search_query.strip().lower()

        matching = [
            tweak for tweak in tweaks
            if not q or (
                q in tweak.get("name_ar", "").lower() or
                q in tweak.get("name_en", "").lower() or
                q in tweak.get("name_zh", "").lower() or
                q in tweak.get("name_ru", "").lower() or
                q in tweak.get("desc_ar", "").lower() or
                q in tweak.get("desc_en", "").lower() or
                q in tweak.get("desc_zh", "").lower() or
                q in tweak.get("desc_ru", "").lower()
            )
        ]

        if not matching:
            empty_lbl = QLabel(t("tweaks.no_match", "No vehicle features match your search."))
            empty_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding: 20px; font-size: 13px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(empty_lbl)
            self.cards_layout.addStretch()
            return

        for tweak in matching:
            card = VehicleTweakCard(tweak)
            card.selection_changed.connect(lambda _: self.update_action_button())
            self.cards.append(card)
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def _on_search_changed(self, text: str):
        self.search_query = text
        self.render_cards()
        self.update_action_button()

    def set_all_selected(self, selected: bool):
        for card in self.cards:
            card.set_selected(selected)
            if not selected:
                card.set_action("enable")
        self.update_action_button()

    def invert_selection(self):
        for card in self.cards:
            new_state = not card.is_selected()
            card.set_selected(new_state)
            if not new_state:
                card.set_action("enable")
        self.update_action_button()

    def get_selected_items(self) -> list:
        selected = []
        for card in self.cards:
            if card.is_selected():
                selected.append({
                    "tweak": card.tweak_data,
                    "action": card.get_action()
                })
        return selected

    def update_action_button(self):
        selected = self.get_selected_items()
        count = len(selected)
        if count == 0:
            self.btn_prepare.setText(t("tweaks.btn_idle", "👆 SELECT AT LEAST ONE FEATURE TO PREPARE USB"))
            self.btn_prepare.setEnabled(False)
            self.btn_add_basket.setEnabled(False)
        else:
            self.btn_prepare.setText(t("tweaks.btn_active", f"⚡ PREPARE VEHICLE TWEAKS USB ({count} FEATURES SELECTED)", count=count))
            self.btn_prepare.setEnabled(True)
            self.btn_add_basket.setEnabled(True)

    def _on_add_to_basket(self):
        selected = self.get_selected_items()
        if not selected:
            return

        from services.basket_service import BasketItem
        item = BasketItem(
            action_type="vehicle_tweaks",
            title=t("tweaks.view_title", "Vehicle Tweaks") + f" ({len(selected)})",
            summary=f"تطبيق إعدادات {len(selected)} ميزة مختارة عبر CAN-Bus",
            config={"selected_tweaks": selected},
            requires_reboot=False
        )
        self.main_app.basket.add_item(item)
        self.main_app.log_terminal(t("basket.added_toast", f"✓ Added {item.title} to basket successfully!", title=item.title), "mint")

    def _execute_prepare_tweaks(self):
        if self.main_app._check_busy_and_warn():
            return
        if not self.main_app._validate_usb_filesystem():
            return

        selected = self.get_selected_items()
        if not selected:
            return

        letter = self.main_app.current_usb.letter
        is_rtl = get_i18n().is_rtl()

        summary_lines = []
        for i, item in enumerate(selected):
            tweak = item["tweak"]
            action = item["action"]
            lang = get_i18n().current_lang
            name = tweak.get(f"name_{lang}") or (tweak.get("name_ar") if is_rtl else tweak.get("name_en"))
            action_badge = "🟢 " + t("tweaks.action_enable", "Enable") if action == "enable" else "🔴 " + t("tweaks.action_disable", "Disable")
            summary_lines.append(f"  {i+1}. {name} ➜ {action_badge}")

        features_list_text = "\n".join(summary_lines)
        confirm_title = t("tweaks.confirm_title", "Confirm Vehicle Customization USB")
        confirm_msg = t(
            "tweaks.confirm_msg",
            f"Are you sure you want to prepare USB drive ({letter}) with {len(selected)} vehicle features?\n\nConfigured Actions:\n{features_list_text}\n\nUnselected features will remain untouched on the vehicle.",
            letter=letter,
            count=len(selected),
            features_list=features_list_text
        )

        from ui.components.dialogs import show_confirm_dialog
        if not show_confirm_dialog(self, confirm_title, confirm_msg, confirm_text=t("tweaks.btn_confirm", "⚡ Prepare Tweaks USB")):
            return

        success_title = t("tweaks.success_title", "الفلاشة جهزت يا بطل! 🚀")
        success_msg = t("tweaks.success_msg", letter=letter)

        self.main_app.execute_payload_worker(
            prepare_vehicle_tweaks_usb,
            letter,
            selected,
            success_title=success_title,
            success_msg=success_msg,
            error_title=t("tweaks.error_title", "Failed to Prepare Vehicle Tweaks USB")
        )

    def _update_cards_margins(self):
        """Sets safe margins from the scrollbar: in RTL, the scrollbar is on the left; in LTR, on the right."""
        from core.i18n import get_i18n
        if get_i18n().is_rtl():
            self.cards_layout.setContentsMargins(18, 0, 4, 0)
        else:
            self.cards_layout.setContentsMargins(4, 0, 18, 0)

    def retranslate_ui(self):
        """Re-translates static and dynamic UI elements for this view."""
        self._update_cards_margins()
        self.lbl_vtitle.setText(t("tweaks.view_title", "🚗 VEHICLE CUSTOMIZATION & TWEAKS"))
        tweaks = get_all_vehicle_tweaks()
        count = len(tweaks)
        self.tweaks_count_label.setText(t("tweaks.count_badge", f"({count} Features Available)", count=count))
        self.lbl_desc.setText(t("tweaks.banner"))
        self.btn_all.setText(t("common.select_all", "Select All"))
        self.btn_none.setText(t("common.deselect_all", "Deselect All"))
        self.btn_invert.setText(t("common.invert", "Invert"))
        self.search_edit.setPlaceholderText(t("tweaks.search_placeholder", "🔍 Search vehicle features..."))
        self.btn_add_basket.setText(t("basket.btn_add_to_basket", "➕ Add to Basket"))
        self.update_action_button()
        self.render_cards()

