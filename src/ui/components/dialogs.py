"""
dialogs.py — Custom Centered Modal Dialogs for Aero Suite (PySide6).
Replaces standard QMessageBox with full RTL/LTR bi-directional awareness,
correct natural icon placement, and proper button flow for Arabic and European languages.
"""
import sys
import os
import re
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QStyle, QFrame, QScrollArea
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
import theme
from core.i18n import t, get_i18n


def _apply_windows_rtl(dlg: QDialog):
    """Enforces native Windows RTL title bar (title on Right, [X] on Left) on Windows OS."""
    if sys.platform == "win32":
        try:
            import ctypes
            hwnd = int(dlg.winId())
            GWL_EXSTYLE = -20
            WS_EX_LAYOUTRTL = 0x00400000
            WS_EX_NOINHERITLAYOUT = 0x00100000
            current_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                current_style | WS_EX_LAYOUTRTL | WS_EX_NOINHERITLAYOUT
            )
            # SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED = 0x0027
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0027)
        except Exception:
            pass


def _format_bidi_text(msg: str, is_rtl: bool) -> str:
    """Formats text lines with Unicode Right-to-Left Embedding (RLE) to guarantee RTL alignment."""
    if not is_rtl or not msg:
        return msg
    lines = msg.split("\n")
    formatted = []
    for line in lines:
        if line.strip():
            # \u202B (RLE) forces line into RTL mode; \u202C (PDF) terminates it
            formatted.append("\u202B" + line + "\u202C")
        else:
            formatted.append("")
    return "\n".join(formatted)


def _create_base_dialog(parent: QWidget, title: str, message: str, icon_type: str = "question"):
    """Builds a custom styled modal dialog with native RTL/LTR layout flow."""
    is_rtl = get_i18n().is_rtl()
    dlg = QDialog(parent)
    dlg.setWindowModality(Qt.WindowModal)
    dlg.setWindowTitle(title)
    dlg.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
    if is_rtl:
        _apply_windows_rtl(dlg)
    dlg.setStyleSheet(f"""
        QDialog {{
            background-color: {theme.SURFACE_1};
            border: 1px solid {theme.BORDER_SLATE};
            border-radius: 8px;
        }}
    """)
    dlg.setMinimumWidth(480)
    dlg.setMaximumWidth(600)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(24, 22, 24, 18)
    root.setSpacing(18)

    # Content Row: Text + Icon
    content_row = QHBoxLayout()
    content_row.setSpacing(24)

    formatted_msg = _format_bidi_text(message, is_rtl)
    msg_lbl = QLabel(formatted_msg)
    msg_lbl.setWordWrap(True)
    msg_lbl.setTextFormat(Qt.PlainText)
    # In RTL, the icon is on the left so we add padding-left (22px) to prevent Arabic text from touching the icon.
    # In LTR, the icon is on the left as well, but text starts near it, so padding-right gives room before the edge.
    padding_style = "padding-left: 24px; padding-right: 4px;" if is_rtl else "padding-left: 4px; padding-right: 24px;"
    font_family = "font-family: 'Segoe UI', 'Cairo', 'Tahoma', sans-serif;"
    msg_lbl.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-size: 13px; font-weight: 500; background: transparent; border: none; line-height: 1.5; {padding_style} {font_family}")
    align = (Qt.AlignRight | Qt.AlignAbsolute) if is_rtl else (Qt.AlignLeft | Qt.AlignAbsolute)
    msg_lbl.setAlignment(align | Qt.AlignTop)

    icon_lbl = QLabel()
    icon_map = {
        "question": QStyle.SP_MessageBoxQuestion,
        "info": QStyle.SP_MessageBoxInformation,
        "warning": QStyle.SP_MessageBoxWarning,
        "error": QStyle.SP_MessageBoxCritical
    }
    pix = dlg.style().standardIcon(icon_map.get(icon_type, QStyle.SP_MessageBoxInformation)).pixmap(36, 36)
    icon_lbl.setPixmap(pix)
    icon_lbl.setFixedSize(36, 36)
    icon_lbl.setAlignment(Qt.AlignTop)

    # In RTL: msg_lbl is added first so it appears on the Right; icon_lbl is on the Left.
    # In LTR: icon_lbl is added first (Left); msg_lbl is on the Right.
    if is_rtl:
        content_row.addWidget(msg_lbl, 1, Qt.AlignTop)
        content_row.addWidget(icon_lbl, 0, Qt.AlignTop)
    else:
        content_row.addWidget(icon_lbl, 0, Qt.AlignTop)
        content_row.addWidget(msg_lbl, 1, Qt.AlignTop)

    root.addLayout(content_row)

    # Button Row layout
    btn_row = QHBoxLayout()
    btn_row.setSpacing(10)
    root.addLayout(btn_row)

    return dlg, btn_row, is_rtl


def show_confirm_dialog(
    parent: QWidget,
    title: str,
    message: str,
    confirm_text: str = None,
    cancel_text: str = None,
    is_danger: bool = False
) -> bool:
    """Shows a modal confirmation dialog with proper RTL/LTR alignment and button styling."""
    if confirm_text is None:
        confirm_text = t("common.continue", "Continue")
    if cancel_text is None:
        cancel_text = t("common.cancel", "Cancel")

    icon_type = "warning" if is_danger else "question"
    dlg, btn_row, is_rtl = _create_base_dialog(parent, title, message, icon_type=icon_type)

    confirmed = False

    def _on_confirm():
        nonlocal confirmed
        confirmed = True
        dlg.accept()

    def _on_cancel():
        nonlocal confirmed
        confirmed = False
        dlg.reject()

    btn_cancel = QPushButton(cancel_text)
    btn_cancel.setCursor(Qt.PointingHandCursor)
    btn_cancel.setFixedHeight(50)
    btn_cancel.setMinimumWidth(120)
    btn_cancel.setStyleSheet(
        f"background-color: {theme.SURFACE_3}; color: {theme.TEXT_PRIMARY}; "
        f"font-weight: bold; padding: 0 22px; border: 1px solid {theme.BORDER_SLATE}; "
        f"border-radius: 9px; font-size: 14px; min-height: 50px; height: 50px;"
    )
    btn_cancel.clicked.connect(_on_cancel)

    btn_confirm = QPushButton(confirm_text)
    btn_confirm.setCursor(Qt.PointingHandCursor)
    btn_confirm.setFixedHeight(50)
    btn_confirm.setMinimumWidth(130)
    if is_danger:
        btn_confirm.setStyleSheet(
            f"background-color: {theme.CRIMSON_DANGER}; color: white; "
            f"font-weight: bold; padding: 0 24px; border-radius: 9px; font-size: 14px; min-height: 50px; height: 50px;"
        )
    else:
        btn_confirm.setStyleSheet(
            f"background-color: {theme.CYAN_PRIMARY}; color: #0A0F1D; "
            f"font-weight: bold; padding: 0 24px; border-radius: 9px; font-size: 14px; min-height: 50px; height: 50px;"
        )
    btn_confirm.clicked.connect(_on_confirm)

    if is_rtl:
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_confirm)
    else:
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_confirm)

    dlg.exec()
    return confirmed


def show_success_dialog(
    parent: QWidget,
    title: str,
    message: str,
    on_open_usb=None,
    current_usb_letter: str = "",
    usb_drive: str = None
):
    """Shows a modal success dialog with 'OK' and 'Open USB Drive' buttons in native RTL/LTR."""
    drive = usb_drive if usb_drive is not None else current_usb_letter
    dlg, btn_row, is_rtl = _create_base_dialog(parent, title, message, icon_type="info")

    btn_ok = QPushButton(t("common.ok", "OK"))
    btn_ok.setCursor(Qt.PointingHandCursor)
    btn_ok.setFixedHeight(50)
    btn_ok.setMinimumWidth(120)
    btn_ok.setStyleSheet(
        f"background-color: {theme.CYAN_PRIMARY}; color: #0A0F1D; font-weight: bold; "
        f"padding: 0 24px; border: none; border-radius: 9px; font-size: 14px; min-height: 50px; height: 50px;"
    )
    btn_ok.clicked.connect(dlg.accept)

    open_usb_clicked = False

    def _on_open_usb():
        nonlocal open_usb_clicked
        open_usb_clicked = True
        dlg.accept()

    btn_open = QPushButton(t("common.open_usb", "📂 Open USB Drive"))
    btn_open.setCursor(Qt.PointingHandCursor)
    btn_open.setFixedHeight(50)
    btn_open.setMinimumWidth(140)
    btn_open.setStyleSheet(
        f"background-color: {theme.SURFACE_3}; color: {theme.TEXT_PRIMARY}; "
        f"font-weight: bold; padding: 0 22px; border: 1px solid {theme.BORDER_SLATE}; "
        f"border-radius: 9px; font-size: 14px; min-height: 50px; height: 50px;"
    )
    btn_open.clicked.connect(_on_open_usb)

    if is_rtl:
        btn_row.addStretch(1)
        btn_row.addWidget(btn_open)
        btn_row.addWidget(btn_ok)
    else:
        btn_row.addStretch(1)
        btn_row.addWidget(btn_open)
        btn_row.addWidget(btn_ok)

    dlg.exec()

    if open_usb_clicked:
        if not drive:
            m = re.search(r'drive\s+([A-Za-z]:[\\/]?)', message, re.IGNORECASE)
            if m:
                drive = m.group(1)
        if on_open_usb:
            on_open_usb(drive)
        elif drive and os.path.exists(drive):
            os.system(f'explorer "{drive}"')


def show_error_dialog(parent: QWidget, title: str, message: str):
    """Shows a modal error dialog in native RTL/LTR."""
    dlg, btn_row, is_rtl = _create_base_dialog(parent, title, message, icon_type="error")

    btn_ok = QPushButton(t("common.ok", "OK"))
    btn_ok.setCursor(Qt.PointingHandCursor)
    btn_ok.setFixedHeight(50)
    btn_ok.setMinimumWidth(130)
    btn_ok.setStyleSheet(
        f"background-color: {theme.CYAN_PRIMARY}; color: #0A0F1D; font-weight: bold; "
        f"padding: 0 26px; border: none; border-radius: 9px; font-size: 14px; min-height: 50px; height: 50px;"
    )
    btn_ok.clicked.connect(dlg.accept)

    if is_rtl:
        btn_row.addStretch(1)
        btn_row.addWidget(btn_ok)
    else:
        btn_row.addStretch(1)
        btn_row.addWidget(btn_ok)

    dlg.exec()


def _find_screen_asset() -> str:
    """Finds screen reference image asset across known asset directories."""
    cur_file = os.path.abspath(__file__)
    components_dir = os.path.dirname(cur_file)
    ui_dir = os.path.dirname(components_dir)
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


def show_about_dialog(parent: QWidget):
    """Displays a rich, cyber-luxury About & Compatibility modal dialog."""
    is_rtl = get_i18n().is_rtl()
    dlg = QDialog(parent)
    dlg.setWindowModality(Qt.WindowModal)
    title = "حول البرنامج والموديلات المدعومة" if is_rtl else "About Aero Suite & Supported Systems"
    dlg.setWindowTitle(title)
    dlg.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
    if is_rtl:
        _apply_windows_rtl(dlg)

    dlg.setFixedSize(600, 650)
    dlg.setStyleSheet(f"""
        QDialog {{
            background-color: {theme.SURFACE_1};
            border: 1px solid {theme.BORDER_SLATE};
            border-radius: 12px;
        }}
        QFrame[class="infoCard"] {{
            background-color: {theme.SURFACE_2};
            border: 1px solid {theme.BORDER_SLATE};
            border-radius: 8px;
        }}
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: {theme.SURFACE_1};
            width: 8px;
            margin: 0px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {theme.BORDER_SLATE};
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {theme.CYAN_PRIMARY};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
    """)

    main_dlg_layout = QVBoxLayout(dlg)
    main_dlg_layout.setContentsMargins(20, 18, 20, 18)
    main_dlg_layout.setSpacing(12)

    # 1. Header Banner
    header_layout = QVBoxLayout()
    header_layout.setSpacing(3)
    lbl_app = QLabel("⚡ AERO SUITE")
    lbl_app.setStyleSheet(f"font-size: 18px; font-weight: 900; color: {theme.CYAN_PRIMARY}; letter-spacing: 1px; background: transparent; border: none;")
    lbl_ver = QLabel(f"v{theme.APP_VERSION} — Automotive Infotainment Studio")
    lbl_ver.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {theme.TEXT_MUTED}; background: transparent; border: none;")
    header_layout.addWidget(lbl_app)
    header_layout.addWidget(lbl_ver)
    main_dlg_layout.addLayout(header_layout)

    # Scrollable Container for Cards & Image
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll_content = QWidget()
    scroll_content.setStyleSheet("background: transparent;")
    root = QVBoxLayout(scroll_content)
    root.setContentsMargins(4, 4, 10, 4)
    root.setSpacing(12)

    # 2. Card: Target Screen Reference & Visual UI
    card_screen = QFrame()
    card_screen.setProperty("class", "infoCard")
    csc_layout = QVBoxLayout(card_screen)
    csc_layout.setSpacing(8)
    csc_layout.setContentsMargins(14, 12, 14, 12)

    title_screen = "📸 شكل وتصميم الشاشة المستهدفة (Target Screen):" if is_rtl else "📸 Target Infotainment Screen & Console:"
    lbl_screen_title = QLabel(title_screen)
    lbl_screen_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme.CYAN_PRIMARY}; background: transparent; border: none;")
    csc_layout.addWidget(lbl_screen_title)

    screen_img = _find_screen_asset()
    if screen_img:
        lbl_img = QLabel()
        pix = QPixmap(screen_img)
        if not pix.isNull():
            lbl_img.setPixmap(pix.scaled(380, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            lbl_img.setAlignment(Qt.AlignCenter)
            lbl_img.setStyleSheet("border-radius: 8px; border: 1px solid #1e293b; background-color: #000000; padding: 4px;")
            csc_layout.addWidget(lbl_img, 0, Qt.AlignCenter)
    else:
        lbl_placeholder = QLabel(
            "📷 بانتظار إضافة صورة الشاشة المرجعية (ضع الصورة في مجلد assets باسم screen_reference.png)"
            if is_rtl else
            "📷 Awaiting target screen reference image (place image in assets/screen_reference.png)"
        )
        lbl_placeholder.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED}; font-style: italic; background: transparent; border: 1px dashed {theme.BORDER_SLATE}; border-radius: 6px; padding: 14px;")
        lbl_placeholder.setAlignment(Qt.AlignCenter)
        csc_layout.addWidget(lbl_placeholder)

    desc_screen_note = (
        "• واجهة الكونسول الأوسط الأصلية لنظام Qinggan / WindLink OS.\n"
        "• إذا كانت سيارتك تحمل نفس هذه الشاشة ونظام أندرويد 8.1، فالبرنامج متوافق معها تلقائياً."
        if is_rtl else
        "• Factory Qinggan / WindLink central console interface.\n"
        "• Any vehicle model sharing this exact display platform and Android 8.1 is fully compatible."
    )
    lbl_screen_note = QLabel(desc_screen_note)
    lbl_screen_note.setStyleSheet(f"font-size: 10.5px; color: {theme.TEXT_PRIMARY}; line-height: 1.4; background: transparent; border: none;")
    csc_layout.addWidget(lbl_screen_note)
    root.addWidget(card_screen)

    # 3. Card: Tested & Officially Verified Vehicles
    card_models = QFrame()
    card_models.setProperty("class", "infoCard")
    cm_layout = QVBoxLayout(card_models)
    cm_layout.setSpacing(6)
    cm_layout.setContentsMargins(14, 12, 14, 12)

    title_models = "🚗 الموديلات المعتمدة والمختبرة رسمياً:" if is_rtl else "🚗 Officially Tested & Verified Models:"
    lbl_cm_title = QLabel(title_models)
    lbl_cm_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme.MINT_SUCCESS}; background: transparent; border: none;")
    cm_layout.addWidget(lbl_cm_title)

    desc_models = (
        "• Dongfeng Shine (Aeolus D53 / 奕炫) — جميع الفئات والموديلات\n"
        "• Dongfeng Mage EV (Aeolus Haohan / 皓瀚) — النسخة الكهربائية (التجميع المحلي المصري)"
        if is_rtl else
        "• Dongfeng Shine (Aeolus D53) — All trim levels & model years\n"
        "• Dongfeng Mage EV (Aeolus Haohan) — Electric version (Egyptian Local Assembly)"
    )
    lbl_cm_desc = QLabel(desc_models)
    lbl_cm_desc.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_PRIMARY}; line-height: 1.5; background: transparent; border: none;")
    cm_layout.addWidget(lbl_cm_desc)
    root.addWidget(card_models)

    # 4. Card: Target Screen Hardware & OS Specifications
    card_specs = QFrame()
    card_specs.setProperty("class", "infoCard")
    cs_layout = QVBoxLayout(card_specs)
    cs_layout.setSpacing(6)
    cs_layout.setContentsMargins(14, 12, 14, 12)

    title_specs = "🖥️ مواصفات منصة الشاشة المستهدفة (Target Specs):" if is_rtl else "🖥️ Target Infotainment Platform Specs:"
    lbl_cs_title = QLabel(title_specs)
    lbl_cs_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme.CYAN_PRIMARY}; background: transparent; border: none;")
    cs_layout.addWidget(lbl_cs_title)

    desc_specs = (
        "• المُصنّع المورّد للشاشة: PATEO Connect+ (نظام WindLink / Qinggan)\n"
        "• نظام التشغيل: Android 8.1.0 Oreo (API Level 27 / OPM1.171019.026)\n"
        "• معالج الشاشة: Qualcomm Snapdragon 450 (msm8953_32)\n"
        "• معمارية المعالج: 32-bit (armeabi-v7a)"
        if is_rtl else
        "• IVI Tier-1 Supplier: PATEO Connect+ (WindLink / Qinggan Platform)\n"
        "• Operating System: Android 8.1.0 Oreo (API Level 27 / OPM1.171019.026)\n"
        "• Chipset / SoC: Qualcomm Snapdragon 450 (msm8953_32)\n"
        "• CPU Architecture: 32-bit (armeabi-v7a)"
    )
    lbl_cs_desc = QLabel(desc_specs)
    lbl_cs_desc.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_PRIMARY}; line-height: 1.5; background: transparent; border: none;")
    cs_layout.addWidget(lbl_cs_desc)
    root.addWidget(card_specs)

    # 5. Card: Open Policy & Experimentation
    card_open = QFrame()
    card_open.setProperty("class", "infoCard")
    co_layout = QVBoxLayout(card_open)
    co_layout.setSpacing(6)
    co_layout.setContentsMargins(14, 12, 14, 12)

    title_open = "💡 سياسة التوافق والتجربة (Open Compatibility):" if is_rtl else "💡 Open Compatibility & Experimentation Policy:"
    lbl_co_title = QLabel(title_open)
    lbl_co_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme.AMBER_WARN}; background: transparent; border: none;")
    co_layout.addWidget(lbl_co_title)

    desc_open = (
        "• البرنامج مصمم بدون أي قيود برمجية تمنع التجربة.\n"
        "• يمكن للحزم أن تعمل على أي طرازات أخرى لسيارات Dongfeng إذا كانت تشترك في نفس منصة PATEO ونظام أندرويد 8.1.\n"
        "• تنبيه: سيارات Mage البنزين (المستوردة) تأتي بشاشات وأنظمة أحدث (أندرويد 10/11) ولا تتطابق مع هذه المعمارية."
        if is_rtl else
        "• Aero Suite enforces NO artificial software blocks or restrictions.\n"
        "• Payloads can work on other Dongfeng models sharing the PATEO 8.1 platform.\n"
        "• Notice: Imported Mage ICE (Petrol) models feature different screens (Android 10/11) and are not targeted."
    )
    lbl_co_desc = QLabel(desc_open)
    lbl_co_desc.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_MUTED}; line-height: 1.5; background: transparent; border: none;")
    lbl_co_desc.setWordWrap(True)
    co_layout.addWidget(lbl_co_desc)
    root.addWidget(card_open)

    scroll.setWidget(scroll_content)
    main_dlg_layout.addWidget(scroll, 1)

    # 6. Bottom Row: Developer Info + Close Button
    bot_layout = QHBoxLayout()
    bot_layout.setSpacing(12)

    dev_text = (
        "هندسة وتطوير: م. عبدالرحمن حمدي\nإهداء لملاك ومجتمع السيارات في مصر ❤️"
        if is_rtl else
        "Engineered by: Eng. Abdelrhman Hamdy\nDedicated to Automotive Community in Egypt ❤️"
    )
    lbl_dev_info = QLabel(dev_text)
    lbl_dev_info.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_MUTED}; line-height: 1.3; background: transparent; border: none;")
    bot_layout.addWidget(lbl_dev_info)
    bot_layout.addStretch()

    btn_close = QPushButton(t("common.ok", "تمام") if is_rtl else "Close")
    btn_close.setCursor(Qt.PointingHandCursor)
    btn_close.setFixedHeight(36)
    btn_close.setMinimumWidth(100)
    btn_close.setStyleSheet(f"""
        QPushButton {{
            background-color: {theme.CYAN_PRIMARY};
            color: #0A0F1D;
            font-weight: bold;
            font-size: 12px;
            border-radius: 6px;
            border: none;
            padding: 0 16px;
        }}
        QPushButton:hover {{
            background-color: {theme.CYAN_HOVER};
        }}
    """)
    btn_close.clicked.connect(dlg.accept)
    bot_layout.addWidget(btn_close)

    main_dlg_layout.addLayout(bot_layout)
    dlg.exec()

