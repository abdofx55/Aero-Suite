"""
tweak_card.py — Vehicle Tweak Row Card Component for Aero Suite.
Mirrors the high-performance horizontal design of AppCard:
- Selection Checkbox
- Feature Icon & Localized Name
- Granular Feature Description
- Action Dropdown (Enable / Disable)
- Visual selection glow
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QCheckBox, QComboBox
import theme
from core.i18n import get_i18n, t


class VehicleTweakCard(QFrame):
    """Interactive card representing a configurable vehicle CAN-Bus feature."""
    selection_changed = Signal(bool)
    action_changed = Signal(str)

    def __init__(self, tweak_data: dict, parent=None):
        super().__init__(parent)
        self.tweak_data = tweak_data
        self.setProperty("class", "card")
        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)

        self.tweak_id = tweak_data.get("id", "")
        self.icon = tweak_data.get("icon", "🚗")
        self.name_ar = tweak_data.get("name_ar", "")
        self.name_en = tweak_data.get("name_en", "")
        self.desc_ar = tweak_data.get("desc_ar", "")
        self.desc_en = tweak_data.get("desc_en", "")

        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        is_rtl = get_i18n().is_rtl()
        lang = get_i18n().current_lang
        display_name = self.tweak_data.get(f"name_{lang}") or (self.name_ar if is_rtl else self.name_en)
        display_desc = self.tweak_data.get(f"desc_{lang}") or (self.desc_ar if is_rtl else self.desc_en)

        # Ensure ample padding at the end of the item (left in RTL, right in LTR) to clear scrollbar
        left_margin = 20 if is_rtl else 12
        right_margin = 12 if is_rtl else 20
        layout.setContentsMargins(left_margin, 0, right_margin, 0)
        layout.setSpacing(10)

        # 1. Main Checkbox
        self.chk_main = QCheckBox()
        self.chk_main.setCursor(Qt.PointingHandCursor)
        self.chk_main.setStyleSheet("background-color: transparent; border: none;")
        self.chk_main.toggled.connect(self._on_toggled)
        layout.addWidget(self.chk_main)

        # 2. Icon
        self.lbl_icon = QLabel(self.icon)
        self.lbl_icon.setStyleSheet("font-size: 16px; background-color: transparent; border: none;")
        self.lbl_icon.setFixedWidth(24)
        self.lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_icon)

        # 3. Feature Name
        self.lbl_name = QLabel(display_name)
        self.lbl_name.setStyleSheet(
            f"font-weight: bold; font-size: 12px; color: {theme.TEXT_PRIMARY}; "
            "background-color: transparent; border: none;"
        )
        self.lbl_name.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_name)

        # 4. Feature Description (subtext)
        self.lbl_desc = QLabel(f"— {display_desc}")
        self.lbl_desc.setStyleSheet(
            f"font-size: 11px; color: {theme.TEXT_MUTED}; "
            "background-color: transparent; border: none;"
        )
        self.lbl_desc.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_desc)

        layout.addStretch()

        # 5. Action Dropdown (Enable / Disable)
        self.combo_action = QComboBox()
        self.combo_action.setObjectName("comboTarget")
        self.combo_action.setFixedWidth(130)
        self.combo_action.setFixedHeight(26)
        self.combo_action.setCursor(Qt.PointingHandCursor)

        enable_text = t("tweaks.action_enable", "🟢 Enable (تفعيل)")
        disable_text = t("tweaks.action_disable", "🔴 Disable (تعطيل)")
        self.combo_action.addItem(enable_text, "enable")
        self.combo_action.addItem(disable_text, "disable")

        self.combo_action.currentIndexChanged.connect(self._on_action_changed)
        layout.addWidget(self.combo_action)
        layout.addSpacing(6)

        self.setToolTip(f"{display_name}\n{display_desc}")

    def _on_toggled(self, checked: bool):
        self.set_selected_visual(checked)
        if not checked:
            self.set_action("enable")
        self.selection_changed.emit(checked)

    def _on_action_changed(self, index: int):
        action_val = self.combo_action.currentData()
        self.action_changed.emit(action_val)

    def is_selected(self) -> bool:
        return self.chk_main.isChecked()

    def set_selected(self, selected: bool):
        self.chk_main.setChecked(selected)
        if not selected:
            self.set_action("enable")
        self.set_selected_visual(selected)

    def get_action(self) -> str:
        return self.combo_action.currentData() or "enable"

    def set_action(self, action: str):
        index = self.combo_action.findData(action)
        if index >= 0:
            self.combo_action.setCurrentIndex(index)

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

    def mousePressEvent(self, event):
        """Clicking on empty card area toggles selection."""
        child = self.childAt(event.position().toPoint()) if hasattr(event, "position") else self.childAt(event.pos())
        if child is not self.combo_action and not self.combo_action.isAncestorOf(child):
            self.chk_main.setChecked(not self.chk_main.isChecked())
        super().mousePressEvent(event)
