"""
roadmap_view.py — Aero Suite Future Vision & v2.0 Roadmap View.
Displays the upcoming features and technical vision for Aero Suite v2.0:
1. Aero Wireless Sync & Live Shell (Zero-cable ADB & remote shell)
2. Aero Cloud App Hub (Curated, tested cloud repository for Dongfeng Shine)
3. Aero Community Presets Cloud (Share & install community launcher setups)
4. IVI Smart Health & Diagnostics (RAM/storage diagnostics & 1-click lag fix)
"""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtGui import QPixmap, QPainter, QPainterPath
import theme
from core.i18n import t, get_i18n


def get_rounded_pixmap(image_path: str, width: int, height: int, radius: int = 10) -> QPixmap:
    """Loads and crops an image to exact dimensions with smoothly rounded corners."""
    if not os.path.exists(image_path):
        return QPixmap()
    src = QPixmap(image_path)
    if src.isNull():
        return QPixmap()

    scaled = src.scaled(width, height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = max(0, (scaled.width() - width) // 2)
    y = max(0, (scaled.height() - height) // 2)
    cropped = scaled.copy(x, y, width, height)

    out = QPixmap(width, height)
    out.fill(Qt.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.Antialiasing, True)
    path = QPainterPath()
    path.addRoundedRect(0, 0, width, height, radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, cropped)
    painter.end()
    return out


class FeatureCard(QFrame):
    """High-tech card showcasing an upcoming major feature with visual mockup illustration."""
    def __init__(self, badge_key: str, title_key: str, desc_key: str, image_filename: str, accent_color: str = theme.CYAN_PRIMARY, parent=None):
        super().__init__(parent)
        self.badge_key = badge_key
        self.title_key = title_key
        self.desc_key = desc_key
        self.image_filename = image_filename
        self.accent_color = accent_color

        self.setStyleSheet(f"""
            FeatureCard {{
                background-color: #0b111e;
                border: 1px solid #1e293b;
                border-radius: 12px;
            }}
            FeatureCard:hover {{
                border-color: {self.accent_color};
            }}
        """)

        # Main horizontal layout: Content area + Image Mockup
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(18, 16, 18, 16)
        self.main_layout.setSpacing(18)

        # 1. Text Details Container
        self.text_container = QWidget()
        self.text_container.setStyleSheet("background: transparent; border: none;")
        self.text_layout = QVBoxLayout(self.text_container)
        self.text_layout.setContentsMargins(0, 0, 0, 0)
        self.text_layout.setSpacing(8)

        # Header Row: Title & Badge
        self.header_row = QHBoxLayout()
        self.header_row.setSpacing(8)

        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("font-size: 14.5px; font-weight: bold; color: #FFFFFF; background: transparent; border: none;")
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setTextFormat(Qt.RichText)
        self.header_row.addWidget(self.lbl_title, 1)

        self.lbl_badge = QLabel()
        self.lbl_badge.setStyleSheet(f"""
            font-size: 11px;
            font-weight: bold;
            color: {self.accent_color};
            background-color: rgba(6, 182, 212, 0.1);
            border: 1px solid {self.accent_color};
            border-radius: 7px;
            padding: 4px 10px;
        """)
        self.header_row.addWidget(self.lbl_badge)
        self.text_layout.addLayout(self.header_row)

        # Bullet Points Container
        self.bullets_box = QWidget()
        self.bullets_box.setStyleSheet("background: transparent; border: none;")
        self.bullets_layout = QVBoxLayout(self.bullets_box)
        self.bullets_layout.setContentsMargins(0, 2, 0, 0)
        self.bullets_layout.setSpacing(6)
        self.text_layout.addWidget(self.bullets_box)
        self.text_layout.addStretch()

        # 2. Visual Illustration Mockup Label
        self.lbl_image = QLabel()
        self.lbl_image.setFixedSize(260, 150)
        self.lbl_image.setStyleSheet(f"""
            QLabel {{
                border-radius: 10px;
                border: 1px solid rgba(30, 41, 59, 0.8);
                background-color: #050811;
            }}
        """)
        self.lbl_image.setAlignment(Qt.AlignCenter)

        # Resolve asset image path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.img_full_path = os.path.join(base_dir, "assets", "roadmap", self.image_filename)

        # Add to card layout
        self.main_layout.addWidget(self.text_container, 1)
        self.main_layout.addWidget(self.lbl_image, 0)

        self.retranslate_ui()

    def retranslate_ui(self):
        is_rtl = get_i18n().is_rtl()
        dir_attr = "rtl" if is_rtl else "ltr"
        align_attr = "right" if is_rtl else "left"
        align_qt = (Qt.AlignRight | Qt.AlignVCenter) if is_rtl else (Qt.AlignLeft | Qt.AlignVCenter)
        align_top = (Qt.AlignRight | Qt.AlignTop) if is_rtl else (Qt.AlignLeft | Qt.AlignTop)

        self.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        self.text_container.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)

        # Title
        raw_title = t(self.title_key)
        self.lbl_title.setAlignment(align_qt)
        self.lbl_title.setText(f'<div align="{align_attr}" dir="{dir_attr}" style="font-size: 14.5px; font-weight: bold; color: #FFFFFF;">{raw_title}</div>')

        # Badge
        self.lbl_badge.setText(t(self.badge_key))

        # Clear existing bullets
        while self.bullets_layout.count():
            item = self.bullets_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        # Rebuild discrete bullets
        raw_desc = t(self.desc_key)
        for line in raw_desc.strip().split("\n"):
            line_s = line.strip()
            if not line_s:
                continue
            lbl = QLabel()
            lbl.setTextFormat(Qt.RichText)
            lbl.setWordWrap(True)
            lbl.setAlignment(align_top)
            lbl.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)

            if line_s.startswith("• "):
                content = line_s[2:].strip()
                if ":" in content:
                    pfx, rest = content.split(":", 1)
                    html = f'<div align="{align_attr}" dir="{dir_attr}" style="line-height: 1.45;"><span style="color: {self.accent_color}; font-weight: bold; font-size: 12.5px;">• {pfx}:</span><span style="color: #E2E8F0; font-size: 12px;">{rest}</span></div>'
                else:
                    html = f'<div align="{align_attr}" dir="{dir_attr}" style="line-height: 1.45;"><span style="color: #E2E8F0; font-size: 12px;">• {content}</span></div>'
            else:
                html = f'<div align="{align_attr}" dir="{dir_attr}" style="line-height: 1.45;"><span style="color: #CBD5E1; font-size: 12px;">{line_s}</span></div>'

            lbl.setText(html)
            self.bullets_layout.addWidget(lbl)

        # Reload rounded pixmap
        pix = get_rounded_pixmap(self.img_full_path, 260, 150, radius=10)
        if not pix.isNull():
            self.lbl_image.setPixmap(pix)


class RoadmapView(QWidget):
    """Aero Suite Future Vision & v2.0 Roadmap View."""
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.container = QWidget()
        self.c_layout = QVBoxLayout(self.container)
        self.c_layout.setContentsMargins(20, 16, 20, 16)
        self.c_layout.setSpacing(14)

        # -------------------------------------------------------------
        # 1. HEADER SECTION
        # -------------------------------------------------------------
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet("background: transparent; border: none;")
        h_layout = QVBoxLayout(self.header_frame)
        h_layout.setContentsMargins(0, 0, 0, 4)
        h_layout.setSpacing(8)

        # Pill Tag / Badge Row
        tag_row = QHBoxLayout()
        self.top_tag = QLabel(t("roadmap.badge"))
        self.top_tag.setStyleSheet("""
            font-size: 11px;
            font-weight: bold;
            color: #F59E0B;
            background-color: rgba(245, 158, 11, 0.12);
            border: 1px solid #F59E0B;
            border-radius: 6px;
            padding: 3px 10px;
        """)
        tag_row.addWidget(self.top_tag)
        tag_row.addStretch()
        h_layout.addLayout(tag_row)

        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {theme.CYAN_PRIMARY}; border: none; background: transparent;")
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setTextFormat(Qt.RichText)
        h_layout.addWidget(self.lbl_title)

        self.lbl_subtitle = QLabel()
        self.lbl_subtitle.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_PRIMARY}; border: none; background: transparent; line-height: 1.55;")
        self.lbl_subtitle.setWordWrap(True)
        self.lbl_subtitle.setTextFormat(Qt.RichText)
        h_layout.addWidget(self.lbl_subtitle)

        self.c_layout.addWidget(self.header_frame)

        # -------------------------------------------------------------
        # 2. FOUR DETAILED FEATURE CARDS WITH VISUAL MOCKUPS
        # -------------------------------------------------------------
        self.cards = [
            FeatureCard("roadmap.feat1_badge", "roadmap.feat1_title", "roadmap.feat1_desc", "feat1_wireless.jpg", accent_color=theme.CYAN_PRIMARY, parent=self),
            FeatureCard("roadmap.feat2_badge", "roadmap.feat2_title", "roadmap.feat2_desc", "feat2_cloud.jpg", accent_color="#38BDF8", parent=self),
            FeatureCard("roadmap.feat3_badge", "roadmap.feat3_title", "roadmap.feat3_desc", "feat3_presets.jpg", accent_color="#A855F7", parent=self),
            FeatureCard("roadmap.feat4_badge", "roadmap.feat4_title", "roadmap.feat4_desc", "feat4_diagnostics.jpg", accent_color=theme.MINT_SUCCESS, parent=self),
        ]

        for card in self.cards:
            self.c_layout.addWidget(card)

        # -------------------------------------------------------------
        # 3. BOTTOM CALL-TO-ACTION & PARTNERS BANNER
        # -------------------------------------------------------------
        self.footer_card = QFrame()
        self.footer_card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(14, 22, 38, 0.85);
                border: 1px dashed {theme.BORDER_CYAN};
                border-radius: 12px;
                padding: 4px;
            }}
        """)
        f_layout = QVBoxLayout(self.footer_card)
        f_layout.setContentsMargins(18, 14, 18, 14)
        f_layout.setSpacing(10)

        self.lbl_footer_text = QLabel()
        self.lbl_footer_text.setStyleSheet(f"font-size: 12px; color: #CBD5E1; line-height: 1.5; background: transparent; border: none;")
        self.lbl_footer_text.setWordWrap(True)
        self.lbl_footer_text.setTextFormat(Qt.RichText)
        f_layout.addWidget(self.lbl_footer_text)

        btn_row = QHBoxLayout()
        self.btn_support_shortcut = QPushButton(t("roadmap.btn_support_shortcut", "🤝 المساهمة والشراكة في قسم شركاء Aero ⚡"))
        self.btn_support_shortcut.setObjectName("btnSupportShortcut")
        self.btn_support_shortcut.setCursor(Qt.PointingHandCursor)
        self.btn_support_shortcut.setFixedHeight(48)
        self.btn_support_shortcut.setStyleSheet(f"""
            QPushButton#btnSupportShortcut {{
                background-color: {theme.SURFACE_2};
                color: {theme.CYAN_PRIMARY};
                border: 1.5px solid {theme.CYAN_PRIMARY};
                font-size: 13px;
                font-weight: bold;
                border-radius: 24px;
                padding: 0 28px;
                min-height: 48px;
                max-height: 48px;
                height: 48px;
            }}
            QPushButton#btnSupportShortcut:hover {{
                background-color: {theme.CYAN_PRIMARY};
                color: #0A0F1D;
            }}
            QPushButton#btnSupportShortcut:pressed {{
                background-color: {theme.CYAN_DIM};
            }}
        """)
        self.btn_support_shortcut.clicked.connect(self._go_to_support)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_support_shortcut)
        f_layout.addLayout(btn_row)

        self.c_layout.addWidget(self.footer_card)

        self.scroll.setWidget(self.container)
        root_layout.addWidget(self.scroll)

        self.retranslate_ui()

    def scroll_to_top(self):
        """Scrolls view back to top."""
        if hasattr(self, "scroll") and self.scroll.verticalScrollBar():
            self.scroll.verticalScrollBar().setValue(0)

    def _go_to_support(self):
        """Switches view to Support."""
        if hasattr(self.main_app, "switch_view"):
            self.main_app.switch_view("support")

    def retranslate_ui(self):
        """Dispatches dynamic retranslation across all cards, titles, and footer."""
        is_rtl = get_i18n().is_rtl()
        dir_attr = "rtl" if is_rtl else "ltr"
        align_attr = "right" if is_rtl else "left"
        align_qt = (Qt.AlignRight | Qt.AlignVCenter) if is_rtl else (Qt.AlignLeft | Qt.AlignVCenter)
        align_top = (Qt.AlignRight | Qt.AlignTop) if is_rtl else (Qt.AlignLeft | Qt.AlignTop)

        self.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        self.container.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        self.header_frame.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        self.footer_card.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)

        self.top_tag.setText(t("roadmap.badge"))
        self.lbl_title.setAlignment(align_qt)
        self.lbl_title.setText(f'<div align="{align_attr}" dir="{dir_attr}" style="font-size: 20px; font-weight: bold; color: {theme.CYAN_PRIMARY};">{t("roadmap.view_title")}</div>')
        self.lbl_subtitle.setAlignment(align_qt)
        self.lbl_subtitle.setText(f'<div align="{align_attr}" dir="{dir_attr}" style="font-size: 12px; line-height: 1.55; color: {theme.TEXT_PRIMARY};">{t("roadmap.view_subtitle")}</div>')
        self.lbl_footer_text.setAlignment(align_top)
        self.lbl_footer_text.setText(f'<div align="{align_attr}" dir="{dir_attr}" style="font-size: 12px; line-height: 1.5; color: #CBD5E1;">{t("roadmap.footer_note")}</div>')
        self.btn_support_shortcut.setText(t("roadmap.btn_support_shortcut", "🤝 المساهمة والشراكة في قسم شركاء Aero ⚡"))

        for card in self.cards:
            card.retranslate_ui()
