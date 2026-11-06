"""
about_view.py — Aero Suite About & Supported Systems Full View.
Provides comprehensive information on:
- Current Aero Suite engine release & architecture
- Officially tested & certified vehicle models (Dongfeng Shine)
- Target infotainment hardware & platform specifications (PATEO Connect+, Snapdragon 450, Android 8.1 32-bit)
- High-fidelity visual screen & console reference
- Open compatibility & experimentation policy
"""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea
)
from PySide6.QtGui import QPixmap
import theme
from core.i18n import t, get_i18n
from core.constants import DEVELOPER_NAME, DEVELOPER_EMAIL


def _find_screen_asset() -> str:
    """Finds screen reference image asset across known asset directories."""
    cur_file = os.path.abspath(__file__)
    views_dir = os.path.dirname(cur_file)
    ui_dir = os.path.dirname(views_dir)
    src_dir = os.path.dirname(ui_dir)
    root_dir = os.path.dirname(src_dir)

    for folder in [
        os.path.join(src_dir, "assets"),
        os.path.join(ui_dir, "assets"),
        os.path.join(root_dir, "assets"),
    ]:
        for fname in ["screen_reference.png", "screen_reference.jpg", "screen_reference.jpeg", "target_screen.png", "target_screen.jpg"]:
            p = os.path.join(folder, fname)
            if os.path.isfile(p):
                return p
    return ""


class AboutView(QWidget):
    """Aero Suite Dedicated About & Supported Systems View."""
    def __init__(self, main_app=None, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._build_ui()

    def _build_ui(self):
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(16, 12, 16, 12)
        master_layout.setSpacing(10)

        # Scroll Area for full responsiveness
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.scroll_widget = QWidget()
        self.scroll_widget.setStyleSheet("background: transparent;")

        self.content_layout = QVBoxLayout(self.scroll_widget)
        self.content_layout.setContentsMargins(4, 0, 8, 8)
        self.content_layout.setSpacing(14)

        # -------------------------------------------------------------
        # 1. HEADER BANNER: App Brand, Version & Description
        # -------------------------------------------------------------
        self.header_card = QFrame()
        self.header_card.setProperty("class", "card")
        self.header_card.setStyleSheet(f"""
            QFrame {{
                background-color: #0b111e;
                border: 1px solid {theme.BORDER_CYAN};
                border-radius: 10px;
            }}
        """)
        h_layout = QVBoxLayout(self.header_card)
        h_layout.setContentsMargins(20, 16, 20, 16)
        h_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        self.lbl_title = QLabel("⚡ AERO SUITE")
        self.lbl_title.setStyleSheet(f"font-size: 24px; font-weight: 900; color: {theme.CYAN_PRIMARY}; letter-spacing: 1.5px; background: transparent; border: none;")
        top_row.addWidget(self.lbl_title)

        self.lbl_badge = QLabel(f"v{theme.APP_VERSION} PRODUCTION")
        self.lbl_badge.setStyleSheet(f"""
            font-size: 11px; font-weight: bold; color: {theme.MINT_SUCCESS};
            background-color: rgba(16, 185, 129, 0.12);
            border: 1px solid {theme.MINT_SUCCESS};
            border-radius: 6px; padding: 3px 10px;
        """)
        top_row.addWidget(self.lbl_badge)
        top_row.addStretch()

        self.lbl_arch_badge = QLabel("32-bit ARM (armeabi-v7a) Engine")
        self.lbl_arch_badge.setStyleSheet(f"""
            font-size: 10px; font-weight: bold; color: {theme.TEXT_MUTED};
            border: 1px solid {theme.BORDER_SLATE};
            border-radius: 6px; padding: 3px 8px;
        """)
        top_row.addWidget(self.lbl_arch_badge)
        h_layout.addLayout(top_row)

        self.lbl_subtitle = QLabel(t("about.header_subtitle"))
        self.lbl_subtitle.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; line-height: 1.5;")
        self.lbl_subtitle.setWordWrap(True)
        h_layout.addWidget(self.lbl_subtitle)
        self.content_layout.addWidget(self.header_card)

        # -------------------------------------------------------------
        # 2. TWO-COLUMN GRID: Tested Models + Target Specs
        # -------------------------------------------------------------
        self.grid_row = QHBoxLayout()
        self.grid_row.setSpacing(14)

        # Column 1: Tested Models (Identical structure to RestoreView)
        self.card_models = QFrame()
        self.card_models.setProperty("class", "card")
        self.card_models.setStyleSheet(f"background-color: #0b111e; border: 1px solid {theme.BORDER_SLATE}; border-radius: 10px;")
        cm_layout = QVBoxLayout(self.card_models)
        cm_layout.setContentsMargins(18, 16, 18, 16)
        cm_layout.setSpacing(12)

        self.lbl_models_title = QLabel(t("about.models_title"))
        self.lbl_models_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.MINT_SUCCESS}; border: none; background: transparent;")
        cm_layout.addWidget(self.lbl_models_title)

        self.lbl_models_desc = QLabel(t("about.models_desc"))
        self.lbl_models_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; line-height: 1.55;")
        self.lbl_models_desc.setWordWrap(True)
        cm_layout.addWidget(self.lbl_models_desc)
        cm_layout.addStretch()
        self.grid_row.addWidget(self.card_models, 1)

        # Column 2: Target Infotainment Platform Specs (Identical structure to RestoreView)
        self.card_specs = QFrame()
        self.card_specs.setProperty("class", "card")
        self.card_specs.setStyleSheet(f"background-color: #0b111e; border: 1px solid {theme.BORDER_SLATE}; border-radius: 10px;")
        cs_layout = QVBoxLayout(self.card_specs)
        cs_layout.setContentsMargins(18, 16, 18, 16)
        cs_layout.setSpacing(12)

        self.lbl_specs_title = QLabel(t("about.specs_title"))
        self.lbl_specs_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        cs_layout.addWidget(self.lbl_specs_title)

        self.lbl_specs_desc = QLabel(t("about.specs_desc"))
        self.lbl_specs_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; line-height: 1.55;")
        self.lbl_specs_desc.setWordWrap(True)
        cs_layout.addWidget(self.lbl_specs_desc)
        cs_layout.addStretch()
        self.grid_row.addWidget(self.card_specs, 1)

        self.content_layout.addLayout(self.grid_row)

        # -------------------------------------------------------------
        # 3. VISUAL SCREEN REFERENCE CARD
        # -------------------------------------------------------------
        self.card_screen_img = QFrame()
        self.card_screen_img.setProperty("class", "card")
        self.card_screen_img.setStyleSheet(f"background-color: #0b111e; border: 1px solid {theme.BORDER_SLATE}; border-radius: 10px;")
        img_box = QVBoxLayout(self.card_screen_img)
        img_box.setContentsMargins(18, 16, 18, 16)
        img_box.setSpacing(12)

        self.lbl_img_title = QLabel(t("about.visual_title"))
        self.lbl_img_title.setStyleSheet(f"font-size: 14.5px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        img_box.addWidget(self.lbl_img_title)

        screen_path = _find_screen_asset()
        if screen_path and os.path.exists(screen_path):
            self.lbl_screen_pixmap = QLabel()
            pix = QPixmap(screen_path)
            if not pix.isNull():
                scaled_pix = pix.scaled(380, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.lbl_screen_pixmap.setPixmap(scaled_pix)
                self.lbl_screen_pixmap.setAlignment(Qt.AlignCenter)
                self.lbl_screen_pixmap.setStyleSheet(f"""
                    QLabel {{
                        border-radius: 10px;
                        border: 1px solid {theme.BORDER_CYAN};
                        background-color: #060a12;
                        padding: 6px;
                    }}
                """)
                img_box.addWidget(self.lbl_screen_pixmap, 0, Qt.AlignCenter)
        else:
            self.lbl_screen_pixmap = QLabel(t("about.img_placeholder", (
                "📷 صورة الشاشة المرجعية: ضع صورة الشاشة في مسار: assets/screen_reference.png لتظهر هنا كدليل بصري لملاك السيارات الأخرى"
            )))
            self.lbl_screen_pixmap.setStyleSheet(f"""
                font-size: 11.5px; color: {theme.TEXT_MUTED}; font-style: italic;
                background-color: rgba(15, 23, 42, 0.4);
                border: 1px dashed {theme.BORDER_SLATE}; border-radius: 8px;
                padding: 20px;
            """)
            self.lbl_screen_pixmap.setAlignment(Qt.AlignCenter)
            img_box.addWidget(self.lbl_screen_pixmap)

        self.lbl_img_note = QLabel(t("about.visual_note"))
        self.lbl_img_note.setStyleSheet(f"font-size: 11.5px; color: {theme.TEXT_MUTED}; border: none; background: transparent; line-height: 1.5;")
        self.lbl_img_note.setWordWrap(True)
        img_box.addWidget(self.lbl_img_note)

        self.content_layout.addWidget(self.card_screen_img)

        # -------------------------------------------------------------
        # 4. OPEN POLICY & COMMUNITY NOTICE
        # -------------------------------------------------------------
        self.card_policy = QFrame()
        self.card_policy.setProperty("class", "card")
        self.card_policy.setStyleSheet(f"background-color: #0b111e; border: 1px solid {theme.BORDER_SLATE}; border-radius: 10px;")
        cp_layout = QVBoxLayout(self.card_policy)
        cp_layout.setContentsMargins(18, 16, 18, 16)
        cp_layout.setSpacing(10)

        self.lbl_policy_title = QLabel(t("about.policy_title"))
        self.lbl_policy_title.setStyleSheet(f"font-size: 14.5px; font-weight: bold; color: {theme.AMBER_WARN}; border: none; background: transparent;")
        cp_layout.addWidget(self.lbl_policy_title)

        self.lbl_policy_desc = QLabel(t("about.policy_desc"))
        self.lbl_policy_desc.setStyleSheet("font-size: 11.5px; color: #CBD5E1; border: none; background: transparent; line-height: 1.55;")
        self.lbl_policy_desc.setWordWrap(True)
        cp_layout.addWidget(self.lbl_policy_desc)

        self.content_layout.addWidget(self.card_policy)

        # -------------------------------------------------------------
        # 5. CREDITS & DEDICATION
        # -------------------------------------------------------------
        self.card_credits = QFrame()
        self.card_credits.setProperty("class", "card")
        self.card_credits.setStyleSheet(f"background-color: #0b111e; border: 1px solid {theme.BORDER_SLATE}; border-radius: 10px;")
        cc_layout = QHBoxLayout(self.card_credits)
        cc_layout.setContentsMargins(18, 12, 18, 12)
        cc_layout.setSpacing(12)

        self.lbl_dev_credits = QLabel(t("about.credits_dev", f"👨‍💻 هندسة وتطوير: {DEVELOPER_NAME}   |   ✉️ {DEVELOPER_EMAIL}"))
        self.lbl_dev_credits.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED}; background: transparent; border: none;")
        cc_layout.addWidget(self.lbl_dev_credits, 1)

        self.lbl_dedication = QLabel(t("about.credits_gift", "🎁 إهداء خاص لملاك سيارات دونج فينج في مصر ❤️"))
        self.lbl_dedication.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {theme.MINT_SUCCESS}; background: transparent; border: none;")
        cc_layout.addWidget(self.lbl_dedication)

        self.content_layout.addWidget(self.card_credits)

        scroll.setWidget(self.scroll_widget)
        master_layout.addWidget(scroll)

    def retranslate_ui(self):
        """Dynamically re-translates all text elements and forces proper RTL layout flow."""
        self.lbl_subtitle.setText(t("about.header_subtitle"))
        self.lbl_models_title.setText(t("about.models_title"))
        self.lbl_models_desc.setText(t("about.models_desc"))
        self.lbl_specs_title.setText(t("about.specs_title"))
        self.lbl_specs_desc.setText(t("about.specs_desc"))
        self.lbl_img_title.setText(t("about.visual_title"))
        self.lbl_img_note.setText(t("about.visual_note"))
        self.lbl_policy_title.setText(t("about.policy_title"))
        self.lbl_policy_desc.setText(t("about.policy_desc"))
        self.lbl_dev_credits.setText(t("about.credits_dev", f"👨‍💻 هندسة وتطوير: {DEVELOPER_NAME}   |   ✉️ {DEVELOPER_EMAIL}"))
        self.lbl_dedication.setText(t("about.credits_gift", "🎁 إهداء خاص لملاك سيارات دونج فينج في مصر ❤️"))
