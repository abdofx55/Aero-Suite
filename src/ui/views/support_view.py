"""
support_view.py — Aero Journey Partners & R&D Contribution View.
Pure Fintech layout:
- Right side: Seamless dark canvas with centered narrative typography (fully localized).
- Left side: 5 distinct, high-fidelity payment cards with authentic, full-scale brand logos:
  1. Visa + Mastercard (combined in one card)
  2. PayPal (wide official vector logo)
  3. Binance (full official gold logo & wordmark)
  4. InstaPay Egypt (ultra-HD official logo from instapay.eg)
  5. Vodafone Cash (ultra-HD official horizontal logo)
"""
import os
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication, QPixmap
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QDialog
)
import theme
from core.i18n import t, get_i18n


def get_asset_file(filename: str) -> str:
    """Finds an asset file safely across possible assets directories."""
    cur_file = os.path.abspath(__file__)
    views_dir = os.path.dirname(cur_file)
    ui_dir = os.path.dirname(views_dir)
    src_dir = os.path.dirname(ui_dir)
    root_dir = os.path.dirname(src_dir)

    for p in [
        os.path.join(src_dir, "assets", filename),
        os.path.join(ui_dir, "assets", filename),
        os.path.join(root_dir, "assets", filename),
    ]:
        if os.path.isfile(p):
            return p
    return ""


class QrDisplayDialog(QDialog):
    """Sleek Cyber-Dialog showing crystal-clear full-size vector QR code with comfortable, tall action buttons."""
    def __init__(self, title: str, subtitle: str, svg_filename: str, action_url: str = None, action_label: str = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedWidth(420)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #0c101c;
                border: 1px solid {theme.BORDER_CYAN};
                border-radius: 14px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Dialog Title
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme.CYAN_PRIMARY};")
        lbl_t.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_t)

        # Dialog Subtitle
        lbl_s = QLabel(subtitle)
        lbl_s.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED}; line-height: 1.45;")
        lbl_s.setAlignment(Qt.AlignCenter)
        lbl_s.setWordWrap(True)
        layout.addWidget(lbl_s)

        # Crisp QR Vector Container
        qr_frame = QFrame()
        qr_frame.setStyleSheet(f"""
            background-color: #FFFFFF;
            border: 2px solid {theme.BORDER_CYAN};
            border-radius: 14px;
            padding: 10px;
        """)
        q_box = QVBoxLayout(qr_frame)
        q_box.setContentsMargins(6, 6, 6, 6)
        q_box.setAlignment(Qt.AlignCenter)

        svg_path = get_asset_file(svg_filename)
        if svg_path and os.path.exists(svg_path):
            svg_widget = QSvgWidget(svg_path)
            svg_widget.setFixedSize(220, 220)
            q_box.addWidget(svg_widget)
        else:
            fallback = QLabel("[QR NOT FOUND]")
            fallback.setStyleSheet("color: black; font-weight: bold;")
            q_box.addWidget(fallback)

        layout.addWidget(qr_frame, 0, Qt.AlignCenter)

        # Action Buttons Row (Solid, tall, ergonomic buttons)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        if action_url:
            btn_act = QPushButton(action_label or t("support.dialog_close", "⚡ فتح الرابط المباشر"))
            btn_act.setFixedHeight(56)
            btn_act.setCursor(Qt.PointingHandCursor)
            btn_act.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.CYAN_PRIMARY};
                    color: #0A0F1D;
                    font-weight: bold;
                    font-size: 15px;
                    border-radius: 10px;
                    padding: 0 20px;
                    min-height: 56px;
                    height: 56px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: #38bdf8; }}
            """)
            btn_act.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(action_url)))
            btn_row.addWidget(btn_act, 1)

        btn_close = QPushButton(t("support.dialog_close", "إغلاق"))
        btn_close.setFixedHeight(56)
        btn_close.setMinimumWidth(135)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.SURFACE_2};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER_SLATE};
                font-size: 15px;
                font-weight: bold;
                border-radius: 10px;
                padding: 0 26px;
                min-height: 56px;
                height: 56px;
            }}
            QPushButton:hover {{ border-color: {theme.BORDER_CYAN}; color: {theme.CYAN_PRIMARY}; }}
        """)
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)


class VodafoneDialog(QDialog):
    """Direct modal for Vodafone Cash with 1-click copy and fully localized typography."""
    def __init__(self, number: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("support.dialog_vodafone_title", "محفظة فودافون كاش"))
        self.setModal(True)
        self.setFixedWidth(400)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #0c101c;
                border: 1px solid {theme.CRIMSON_DANGER};
                border-radius: 14px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        lbl_t = QLabel(t("support.dialog_vodafone_title", "📞 محفظة فودافون كاش (Vodafone Cash)"))
        lbl_t.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.CRIMSON_DANGER};")
        lbl_t.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_t)

        lbl_desc = QLabel(t("support.dialog_vodafone_sub", "يمكنك التحويل المباشر من أي محفظة إلكترونية داخل مصر أو عبر كود #9*"))
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED}; line-height: 1.45;")
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        num_frame = QFrame()
        num_frame.setStyleSheet(f"""
            background-color: rgba(225, 29, 72, 0.12);
            border: 1.5px dashed {theme.CRIMSON_DANGER};
            border-radius: 10px;
            padding: 10px;
        """)
        n_box = QVBoxLayout(num_frame)
        n_box.setAlignment(Qt.AlignCenter)
        lbl_num = QLabel(number)
        lbl_num.setStyleSheet("font-size: 22px; font-weight: bold; color: #FFFFFF; letter-spacing: 2px;")
        lbl_num.setAlignment(Qt.AlignCenter)
        n_box.addWidget(lbl_num)
        layout.addWidget(num_frame)

        self.btn_copy = QPushButton(t("support.dialog_vodafone_btn", "📋 نسخ رقم المحفظة"))
        self.btn_copy.setFixedHeight(56)
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.CRIMSON_DANGER};
                color: #FFFFFF;
                font-weight: bold;
                font-size: 15px;
                border-radius: 10px;
                border: none;
                min-height: 56px;
                height: 56px;
            }}
            QPushButton:hover {{ background-color: #f43f5e; }}
        """)
        self.btn_copy.clicked.connect(lambda: self._copy(number))
        layout.addWidget(self.btn_copy)

        btn_close = QPushButton(t("support.dialog_close", "إغلاق"))
        btn_close.setFixedHeight(50)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.SURFACE_2};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER_SLATE};
                font-size: 14px;
                font-weight: bold;
                border-radius: 10px;
                min-height: 50px;
                height: 50px;
            }}
            QPushButton:hover {{ border-color: {theme.CRIMSON_DANGER}; color: #FFFFFF; }}
        """)
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

    def _copy(self, num: str):
        QGuiApplication.clipboard().setText(num)
        self.btn_copy.setText(t("support.dialog_vodafone_copied", "✓ تم النسخ بنجاح!"))
        self.btn_copy.setStyleSheet(f"background-color: {theme.MINT_SUCCESS}; color: #0A0F1D; font-weight: bold; border-radius: 8px;")


class PaymentCardButton(QFrame):
    """Clean, high-fidelity clickable payment card tile showing pure brand logos at native aspect ratio."""
    clicked = Signal()

    def __init__(self, bg: str = "#FFFFFF", border: str = "#CBD5E1", hover_border: str = theme.CYAN_PRIMARY, w: int = 200, h: int = 98, parent=None):
        super().__init__(parent)
        self.setFixedSize(w, h)
        self.setCursor(Qt.PointingHandCursor)
        self.bg = bg
        self.border_normal = border
        self.border_hover = hover_border

        self.setStyleSheet(f"""
            PaymentCardButton {{
                background-color: {self.bg};
                border: 1.5px solid {self.border_normal};
                border-radius: 14px;
            }}
            PaymentCardButton:hover {{
                border: 2px solid {self.border_hover};
            }}
        """)

        self.content_layout = QHBoxLayout(self)
        self.content_layout.setContentsMargins(12, 10, 12, 10)
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.content_layout.setSpacing(10)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class SupportView(QWidget):
    """Aero Journey Partners & Contribution View (Seamless Dark Split Layout)."""
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._build_ui()

    def _build_ui(self):
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(18, 12, 18, 10)
        master_layout.setSpacing(10)

        # -------------------------------------------------------------
        # SPLIT CONTAINER (Text Narrative on Right, 5 Cards on Left)
        # -------------------------------------------------------------
        split_layout = QHBoxLayout()
        split_layout.setSpacing(26)

        is_rtl = get_i18n().is_rtl()

        # Add leading spacer/padding in the beginning (in RTL: on the right side)
        # to comfortably inset the narrative text away from the sidebar
        self.leading_spacer = QWidget()
        self.leading_spacer.setStyleSheet("background: transparent; border: none;")
        self.leading_spacer.setFixedWidth(75 if is_rtl else 0)
        split_layout.addWidget(self.leading_spacer)

        # =============================================================
        # 1. RIGHT SIDE: SEAMLESS DARK BACKGROUND & CENTERED TEXT
        # =============================================================
        story_box = QFrame()
        story_box.setMaximumWidth(460)
        story_box.setStyleSheet("background: transparent; border: none;")
        s_layout = QVBoxLayout(story_box)
        s_layout.setContentsMargins(10, 10, 10, 10)
        s_layout.setSpacing(14)
        s_layout.setAlignment(Qt.AlignCenter)

        s_layout.addStretch(1)

        # Centered Headline
        self.lbl_head = QLabel(t("support.view_title", "شركاء رحلة Aero ⚡🏎️"))
        self.lbl_head.setAlignment(Qt.AlignCenter)
        self.lbl_head.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {theme.CYAN_PRIMARY}; background: transparent; border: none;")
        s_layout.addWidget(self.lbl_head)

        # Centered Full Engineering Narrative
        self.lbl_sub = QLabel(t("support.view_subtitle"))
        self.lbl_sub.setAlignment(Qt.AlignCenter)
        self.lbl_sub.setStyleSheet(f"font-size: 11.5px; color: {theme.TEXT_PRIMARY}; line-height: 1.6; background: transparent; border: none;")
        self.lbl_sub.setWordWrap(True)
        s_layout.addWidget(self.lbl_sub)

        # Centered Fully-Localized Prompt Hint
        self.lbl_hint = QLabel(t("support.prompt_hint", "👈 اضغط على وسيلة الدفع المناسبة لك للمساهمة المباشرة"))
        self.lbl_hint.setAlignment(Qt.AlignCenter)
        self.lbl_hint.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {theme.MINT_SUCCESS}; background: transparent; border: none;")
        s_layout.addWidget(self.lbl_hint)

        s_layout.addStretch(1)

        split_layout.addWidget(story_box, 8)

        # =============================================================
        # 2. LEFT SIDE: 5 AUTHENTIC BRAND TILES (STAGGERED 2 COLUMNS)
        # =============================================================
        tiles_container = QFrame()
        tiles_container.setStyleSheet("background: transparent; border: none;")
        tiles_layout = QHBoxLayout(tiles_container)
        tiles_layout.setContentsMargins(20, 0, 0, 0)
        tiles_layout.setSpacing(18)
        tiles_layout.setAlignment(Qt.AlignCenter)

        # ----------------- COLUMN 1 (Visa/Mastercard + PayPal) -----------------
        col1 = QVBoxLayout()
        col1.setSpacing(14)
        col1.setAlignment(Qt.AlignCenter)

        # CARD 1: VISA & MASTERCARD (Combined in one card)
        self.card_cards = PaymentCardButton(bg="#FFFFFF", border="#CBD5E1", hover_border=theme.CYAN_PRIMARY, w=200, h=98)
        self.card_cards.setToolTip(t("support.tooltip_cards"))
        self.card_cards.clicked.connect(self._open_paypal)
        
        # Visa SVG
        visa_path = get_asset_file("visa_full.svg")
        if visa_path and os.path.exists(visa_path):
            sw_visa = QSvgWidget(visa_path)
            sw_visa.setFixedSize(76, 30)
            self.card_cards.content_layout.addWidget(sw_visa)
            
        # Mastercard SVG
        mc_path = get_asset_file("mastercard_full.svg")
        if mc_path and os.path.exists(mc_path):
            sw_mc = QSvgWidget(mc_path)
            sw_mc.setFixedSize(66, 44)
            self.card_cards.content_layout.addWidget(sw_mc)
            
        col1.addWidget(self.card_cards)

        # CARD 2: PAYPAL (Full-scale wide official logo, uncompressed)
        self.card_paypal = PaymentCardButton(bg="#FFFFFF", border="#0079C1", hover_border=theme.CYAN_PRIMARY, w=200, h=98)
        self.card_paypal.setToolTip(t("support.tooltip_paypal"))
        self.card_paypal.clicked.connect(self._open_paypal)
        
        pp_path = get_asset_file("paypal_full.svg")
        if pp_path and os.path.exists(pp_path):
            sw_pp = QSvgWidget(pp_path)
            sw_pp.setFixedSize(155, 46)
            self.card_paypal.content_layout.addWidget(sw_pp)
            
        col1.addWidget(self.card_paypal)

        # CARD 3: BINANCE (Full-scale official gold logo & wordmark)
        self.card_binance = PaymentCardButton(bg="#181A20", border="#F0B90B", hover_border="#fcd535", w=200, h=98)
        self.card_binance.setToolTip(t("support.tooltip_binance"))
        self.card_binance.clicked.connect(self._open_binance_qr)
        
        bn_path = get_asset_file("binance_full.svg")
        if bn_path and os.path.exists(bn_path):
            sw_bn = QSvgWidget(bn_path)
            sw_bn.setFixedSize(162, 36)
            self.card_binance.content_layout.addWidget(sw_bn)
            
        col1.addWidget(self.card_binance)

        tiles_layout.addLayout(col1)

        # ----------------- COLUMN 2 (InstaPay + Vodafone Cash - Offset) -----------------
        col2 = QVBoxLayout()
        col2.setSpacing(14)
        col2.setAlignment(Qt.AlignCenter)
        col2.addSpacing(25)  # Visual stagger offset

        # CARD 4: INSTAPAY EGYPT (Ultra-HD official logo from instapay.eg)
        self.card_insta = PaymentCardButton(bg="#FFFFFF", border="#6C5CE7", hover_border="#a29bfe", w=200, h=98)
        self.card_insta.setToolTip(t("support.tooltip_instapay"))
        self.card_insta.clicked.connect(self._open_instapay_qr)
        
        # Load ultra-HD transparent logo
        insta_path = get_asset_file("instapay_hd.png") or get_asset_file("logo_instapay_clean.png") or get_asset_file("logo_instapay.png")
        if insta_path and os.path.exists(insta_path):
            lbl_insta = QLabel()
            pix = QPixmap(insta_path).scaled(162, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_insta.setPixmap(pix)
            lbl_insta.setStyleSheet("background: transparent; border: none;")
            self.card_insta.content_layout.addWidget(lbl_insta)
            
        col2.addWidget(self.card_insta)

        # CARD 5: VODAFONE CASH (Ultra-HD official horizontal logo)
        self.card_voda = PaymentCardButton(bg="#FFFFFF", border="#E60000", hover_border="#f43f5e", w=200, h=98)
        self.card_voda.setToolTip(t("support.tooltip_vodafone"))
        self.card_voda.clicked.connect(self._open_vodafone_dialog)
        
        voda_path = get_asset_file("vodafone_hd.png") or get_asset_file("vodafone_full.svg")
        if voda_path and os.path.exists(voda_path):
            lbl_voda = QLabel()
            pix = QPixmap(voda_path).scaled(165, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_voda.setPixmap(pix)
            lbl_voda.setStyleSheet("background: transparent; border: none;")
            self.card_voda.content_layout.addWidget(lbl_voda)
            
        col2.addWidget(self.card_voda)

        tiles_layout.addLayout(col2)

        split_layout.addWidget(tiles_container, 12)

        master_layout.addLayout(split_layout, 1)

        # -------------------------------------------------------------
        # BOTTOM TRUST BAR
        # -------------------------------------------------------------
        is_rtl = get_i18n().is_rtl()
        self.trust_card = QFrame()
        self.trust_card.setObjectName("trustBanner")
        self.trust_card.setFixedHeight(28)
        self.trust_card.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        self.trust_card.setStyleSheet(f"""
            QFrame#trustBanner {{
                background-color: #0b0f19;
                border: 1px solid {theme.BORDER_SLATE};
                border-radius: 6px;
                padding: 2px 10px;
            }}
        """)
        t_layout = QHBoxLayout(self.trust_card)
        t_layout.setContentsMargins(8, 2, 8, 2)
        t_layout.setSpacing(8)

        self.icon_heart = QLabel("🛡️")
        self.icon_heart.setStyleSheet("font-size: 13px; background: transparent; border: none;")
        t_layout.addWidget(self.icon_heart)

        self.lbl_footer = QLabel(t("support.footer_note", "صُنع بفخر لخدمة مجتمع ملاك السيارات • شكراً لكل شريك في هذا النجاح"))
        self.lbl_footer.setAlignment((Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter) if is_rtl else (Qt.AlignLeft | Qt.AlignAbsolute | Qt.AlignVCenter))
        self.lbl_footer.setStyleSheet(f"font-size: 10.5px; font-weight: bold; color: {theme.TEXT_MUTED}; background: transparent; border: none;")
        t_layout.addWidget(self.lbl_footer, 1)

        self.badge_open = QLabel("100% FREE CORE TOOLS")
        self.badge_open.setStyleSheet(f"""
            font-size: 9px; font-weight: bold; color: {theme.MINT_SUCCESS};
            border: 1px solid {theme.MINT_SUCCESS};
            border-radius: 4px;
            padding: 1px 6px;
            background: transparent;
        """)
        t_layout.addWidget(self.badge_open)

        master_layout.addWidget(self.trust_card)

    # -------------------------------------------------------------
    # Interactive Actions
    # -------------------------------------------------------------
    def _open_paypal(self):
        """Opens PayPal / Card payment gateway."""
        QDesktopServices.openUrl(QUrl("https://www.paypal.com/ncp/payment/NPSN3P5Y8QD2S"))

    def _open_binance_qr(self):
        """Opens Binance Pay high-res QR Dialog with full i18n localization."""
        dlg = QrDisplayDialog(
            title=t("support.dialog_binance_title", "🟡 التحويل عبر Binance Pay (USDT)"),
            subtitle=t("support.dialog_binance_sub", "امسح الرمز عبر تطبيق Binance للإرسال الفوري بدون رسوم (0% Fee) أو افتح الرابط بالأسفل:"),
            svg_filename="binance_qr.svg",
            action_url="https://app.binance.com/uni-qr/DQ3juDCV",
            action_label=t("support.dialog_binance_btn", "⚡ فتح في تطبيق Binance"),
            parent=self
        )
        dlg.exec()

    def _open_instapay_qr(self):
        """Opens InstaPay Egypt high-res QR Dialog with full i18n localization."""
        dlg = QrDisplayDialog(
            title=t("support.dialog_instapay_title", "📱 الدفع عبر إنستاباي (InstaPay Egypt)"),
            subtitle=t("support.dialog_instapay_sub", "امسح الرمز عبر تطبيق إنستاباي للتحويل المباشر واللحظي:"),
            svg_filename="instapay_qr.svg",
            action_url="https://ipn.eg/S/abdofx55/instapay/27EY56",
            action_label=t("support.dialog_instapay_btn", "⚡ فتح في تطبيق إنستاباي"),
            parent=self
        )
        dlg.exec()

    def _open_vodafone_dialog(self):
        """Opens Vodafone Cash details modal with instant copy."""
        dlg = VodafoneDialog("01095449725", parent=self)
        dlg.exec()

    # -------------------------------------------------------------
    # Dynamic i18n Retranslate
    # -------------------------------------------------------------
    def retranslate_ui(self):
        """Dispatches dynamic retranslation across all titles, hints, tooltips."""
        is_rtl = get_i18n().is_rtl()
        self.lbl_head.setText(t("support.view_title", "شركاء رحلة Aero ⚡🏎️"))
        self.lbl_sub.setText(t("support.view_subtitle"))
        self.lbl_hint.setText(t("support.prompt_hint", "👈 اضغط على وسيلة الدفع المناسبة لك للمساهمة المباشرة"))
        self.lbl_footer.setText(t("support.footer_note"))
        self.lbl_footer.setAlignment((Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter) if is_rtl else (Qt.AlignLeft | Qt.AlignAbsolute | Qt.AlignVCenter))
        self.trust_card.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        if hasattr(self, "leading_spacer"):
            self.leading_spacer.setFixedWidth(75 if is_rtl else 0)

        self.card_cards.setToolTip(t("support.tooltip_cards"))
        self.card_paypal.setToolTip(t("support.tooltip_paypal"))
        self.card_binance.setToolTip(t("support.tooltip_binance"))
        self.card_insta.setToolTip(t("support.tooltip_instapay"))
        self.card_voda.setToolTip(t("support.tooltip_vodafone"))
