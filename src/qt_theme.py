"""
qt_theme.py — Aero Suite Qt Cyber-Luxury Design System & QSS Stylesheet.
Calibrated for Dongfeng Shine (Aeolus D53) IVI Studio.
Engineered by Abdelrhman Hamdy - Senior Software Engineer.
"""
import theme

def get_application_stylesheet(is_rtl: bool = False) -> str:
    """Returns the complete, unified QSS stylesheet for PySide6 with RTL awareness."""
    combo_dropdown_pos = "top right"
    combo_padding = "4px 24px 4px 10px"
    usb_combo_padding = "1px 24px 1px 8px"
    target_combo_pos = "center right"
    target_combo_padding = "1px 16px 1px 4px"
    app_font_family = '"Segoe UI", "Cairo", "Tahoma", sans-serif' if is_rtl else '"Segoe UI", "Inter", "Space Grotesk", sans-serif'

    return f"""
    /* Global Base */
    QMainWindow, QWidget {{
        background-color: {theme.BG_BASE};
        color: {theme.TEXT_PRIMARY};
        font-family: {app_font_family};
        font-size: 13px;
    }}

    /* Sidebar Panel */
    #sidebarPanel {{
        background-color: {theme.SURFACE_1};
        border-right: 1px solid {theme.BORDER_SLATE};
    }}

    /* Top Bar Panel */
    #topBarPanel {{
        background-color: {theme.SURFACE_1};
        border-bottom: 1px solid {theme.CYAN_DIM};
    }}

    /* Bottom Console & Status Panel */
    #bottomPanel {{
        background-color: {theme.SURFACE_1};
        border-top: 1px solid {theme.BORDER_SLATE};
    }}

    /* Card Frames */
    QFrame[class="card"] {{
        background-color: {theme.SURFACE_2};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 8px;
    }}
    QFrame[class="card"]:hover {{
        border: 1px solid {theme.BORDER_CYAN};
    }}
    QFrame[class="card"] QLabel,
    QFrame[class="card"] QCheckBox,
    QFrame[class="card"] QRadioButton {{
        background-color: transparent;
        border: none;
        padding-bottom: 4px;
    }}

    /* Sidebar Navigation Items */
    QFrame[class="navItem"] {{
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 8px;
        margin: 1px 4px;
    }}
    QFrame[class="navItem"]:hover {{
        background-color: {theme.SURFACE_2};
        border: 1px solid {theme.BORDER_SLATE};
    }}
    QFrame[class="navItem"][active="true"] {{
        background-color: {theme.CYAN_ALPHA_15};
        border: 1px solid {theme.CYAN_PRIMARY};
    }}
    QFrame[class="navItem"] QLabel {{
        background-color: transparent;
        border: none;
    }}

    /* Category Navigation Headers */
    QLabel[class="navCategory"] {{
        color: {theme.TEXT_MUTED};
        font-size: 10px;
        font-weight: bold;
        letter-spacing: 1px;
        padding: 10px 12px 4px 12px;
    }}

    /* Navigation Buttons */
    QPushButton[class="navBtn"] {{
        background-color: transparent;
        color: {theme.TEXT_PRIMARY};
        font-size: 12px;
        font-weight: 600;
        text-align: left;
        padding: 8px 14px;
        border: none;
        border-radius: 6px;
        margin: 1px 8px;
    }}
    QPushButton[class="navBtn"]:hover {{
        background-color: {theme.SURFACE_2};
        color: {theme.CYAN_PRIMARY};
    }}
    QPushButton[class="navBtn"][active="true"] {{
        background-color: {theme.CYAN_ALPHA_15};
        color: {theme.CYAN_PRIMARY};
        border-left: 3px solid {theme.CYAN_PRIMARY};
        font-weight: bold;
    }}

    /* Standard Push Buttons */
    QPushButton {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 12px;
        font-weight: 600;
        outline: none;
        min-height: 18px;
    }}
    QPushButton:hover {{
        background-color: {theme.SURFACE_3};
        border-color: {theme.CYAN_PRIMARY};
    }}
    QPushButton:pressed {{
        background-color: {theme.CYAN_ALPHA_15};
    }}
    QPushButton:disabled {{
        background-color: {theme.SURFACE_1};
        color: {theme.TEXT_MUTED};
        border: 1px solid {theme.BORDER_SLATE};
    }}

    /* Primary Accent Buttons (Cyan) */
    QPushButton[class="btnPrimary"] {{
        background-color: {theme.CYAN_PRIMARY};
        color: #000000;
        border: 1px solid {theme.CYAN_PRIMARY};
        font-size: 13px;
        font-weight: bold;
        padding: 10px 20px;
        border-radius: 6px;
        outline: none;
    }}
    QPushButton[class="btnPrimary"]:hover {{
        background-color: {theme.CYAN_HOVER};
        border: 1px solid {theme.CYAN_HOVER};
        color: #000000;
    }}
    QPushButton[class="btnPrimary"]:pressed {{
        background-color: {theme.CYAN_DIM};
        border: 1px solid {theme.CYAN_DIM};
        color: #000000;
    }}
    QPushButton[class="btnPrimary"]:disabled {{
        background-color: {theme.SURFACE_2};
        border: 1px solid {theme.BORDER_SLATE};
        color: {theme.TEXT_MUTED};
    }}

    /* Danger Accent Buttons (Crimson) */
    QPushButton[class="btnDanger"] {{
        background-color: {theme.CRIMSON_DANGER};
        color: #FFFFFF;
        border: 1px solid {theme.CRIMSON_DANGER};
        font-size: 13px;
        font-weight: bold;
        padding: 10px 20px;
        border-radius: 6px;
        outline: none;
    }}
    QPushButton[class="btnDanger"]:hover {{
        background-color: {theme.CRIMSON_HOVER};
        border: 1px solid {theme.CRIMSON_HOVER};
        color: #FFFFFF;
    }}
    QPushButton[class="btnDanger"]:pressed {{
        background-color: #B91C1C;
        border: 1px solid #B91C1C;
        color: #FFFFFF;
    }}
    QPushButton[class="btnDanger"]:disabled {{
        background-color: {theme.SURFACE_2};
        border: 1px solid {theme.BORDER_SLATE};
        color: {theme.TEXT_MUTED};
    }}

    /* Success Buttons (Mint) */
    QPushButton[class="btnSuccess"] {{
        background-color: {theme.MINT_SUCCESS};
        color: #000000;
        border: 1px solid {theme.MINT_SUCCESS};
        font-size: 12px;
        font-weight: bold;
        border-radius: 6px;
        outline: none;
    }}

    /* Warning / Amber Buttons */
    QPushButton[class="btnWarning"] {{
        background-color: {theme.AMBER_WARN};
        color: #050B14;
        border: 1px solid {theme.AMBER_WARN};
        font-size: 13px;
        font-weight: bold;
        padding: 10px 20px;
        border-radius: 6px;
        outline: none;
        min-height: 22px;
    }}
    QPushButton[class="btnWarning"]:hover {{
        background-color: #FCD34D;
        border: 1px solid #FCD34D;
        color: #050B14;
    }}
    QPushButton[class="btnWarning"]:pressed {{
        background-color: #D97706;
        border: 1px solid #D97706;
        color: #050B14;
    }}
    QPushButton[class="btnWarning"]:disabled {{
        background-color: {theme.SURFACE_2};
        border: 1px solid {theme.BORDER_SLATE};
        color: {theme.TEXT_MUTED};
    }}
    QPushButton[class="btnSuccess"]:hover {{
        background-color: {theme.MINT_HOVER};
        border: 1px solid {theme.MINT_HOVER};
        color: #000000;
    }}
    QPushButton[class="btnSuccess"]:pressed {{
        background-color: #059669;
        border: 1px solid #059669;
        color: #000000;
    }}
    QPushButton[class="btnSuccess"]:disabled {{
        background-color: {theme.SURFACE_2};
        border: 1px solid {theme.BORDER_SLATE};
        color: {theme.TEXT_MUTED};
    }}

    /* Line Edits & Search Boxes */
    QLineEdit {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
        min-height: 18px;
        selection-background-color: {theme.CYAN_DIM};
    }}
    QLineEdit:focus {{
        border: 1px solid {theme.CYAN_PRIMARY};
        background-color: {theme.SURFACE_3};
    }}

    /* Combo Boxes */
    QComboBox {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 6px;
        padding: {combo_padding};
        font-size: 11px;
        font-weight: 500;
        min-height: 28px;
    }}
    QComboBox:hover {{
        border-color: {theme.CYAN_PRIMARY};
    }}
    QComboBox:on {{
        border-color: {theme.CYAN_PRIMARY};
        background-color: {theme.SURFACE_3};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: {combo_dropdown_pos};
        width: 22px;
        border: none;
    }}
    QComboBox::down-arrow {{
        image: url("assets/arrow_down.png");
        width: 10px;
        height: 10px;
    }}
    QComboBox::down-arrow:hover {{
        image: url("assets/arrow_down_cyan.png");
    }}
    QComboBox QAbstractItemView {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_PRIMARY};
        selection-background-color: {theme.CYAN_ALPHA_15};
        selection-color: {theme.CYAN_PRIMARY};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 6px;
        padding: 4px;
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{
        min-height: 28px;
        padding: 4px 10px;
        border-radius: 4px;
        border: none;
    }}
    QComboBox QAbstractItemView::item:hover {{
        background-color: {theme.SURFACE_3};
        color: {theme.CYAN_PRIMARY};
    }}
    QComboBox QAbstractItemView::item:selected {{
        background-color: {theme.CYAN_ALPHA_15};
        color: {theme.CYAN_PRIMARY};
    }}

    /* Specialized USB Header Bar */
    QComboBox#usbCombo {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 6px;
        padding: {usb_combo_padding};
        font-size: 11px;
        font-weight: bold;
        height: 24px;
        min-height: 24px;
        max-height: 24px;
    }}
    QComboBox#usbCombo:hover {{
        border: 1px solid {theme.CYAN_PRIMARY};
        background-color: {theme.SURFACE_3};
    }}
    QComboBox#usbCombo:on {{
        border: 1px solid {theme.CYAN_PRIMARY};
        background-color: {theme.SURFACE_3};
    }}
    QComboBox#usbCombo::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: {combo_dropdown_pos};
        width: 22px;
        border: none;
    }}
    QComboBox#usbCombo::down-arrow {{
        image: url("assets/arrow_down.png");
        width: 9px;
        height: 9px;
    }}
    QComboBox#usbCombo::down-arrow:hover {{
        image: url("assets/arrow_down_cyan.png");
    }}
    QComboBox#usbCombo QAbstractItemView {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_PRIMARY};
        selection-background-color: {theme.SURFACE_3};
        selection-color: {theme.CYAN_PRIMARY};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 6px;
        padding: 4px;
        outline: none;
    }}
    QComboBox#usbCombo QAbstractItemView::item {{
        min-height: 26px;
        padding: 3px 8px;
        border-radius: 4px;
        border: none;
    }}
    QComboBox#usbCombo QAbstractItemView::item:hover {{
        background-color: {theme.SURFACE_3};
        color: {theme.CYAN_PRIMARY};
    }}
    QComboBox#usbCombo QAbstractItemView::item:selected {{
        background-color: {theme.CYAN_ALPHA_15};
        color: {theme.CYAN_PRIMARY};
    }}

    /* Specialized Language Selector in Header Bar */
    QComboBox#langCombo {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 6px;
        padding: {usb_combo_padding};
        font-size: 11px;
        font-weight: 600;
        height: 24px;
        min-height: 24px;
        max-height: 24px;
    }}
    QComboBox#langCombo:hover {{
        border: 1px solid {theme.CYAN_PRIMARY};
        background-color: {theme.SURFACE_3};
    }}
    QComboBox#langCombo:on {{
        border: 1px solid {theme.CYAN_PRIMARY};
        background-color: {theme.SURFACE_3};
    }}
    QComboBox#langCombo::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: {combo_dropdown_pos};
        width: 22px;
        border: none;
    }}
    QComboBox#langCombo::down-arrow {{
        image: url("assets/arrow_down.png");
        width: 9px;
        height: 9px;
    }}
    QComboBox#langCombo::down-arrow:hover {{
        image: url("assets/arrow_down_cyan.png");
    }}
    QComboBox#langCombo QAbstractItemView {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_PRIMARY};
        selection-background-color: {theme.SURFACE_3};
        selection-color: {theme.CYAN_PRIMARY};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 6px;
        padding: 4px;
        outline: none;
    }}
    QComboBox#langCombo QAbstractItemView::item {{
        min-height: 26px;
        padding: 3px 8px;
        border-radius: 4px;
        border: none;
    }}
    QComboBox#langCombo QAbstractItemView::item:hover {{
        background-color: {theme.SURFACE_3};
        color: {theme.CYAN_PRIMARY};
    }}
    QComboBox#langCombo QAbstractItemView::item:selected {{
        background-color: {theme.CYAN_ALPHA_15};
        color: {theme.CYAN_PRIMARY};
    }}

    /* Compact Target Partition Dropdown (User App / System App) */
    QComboBox#comboTarget {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 4px;
        padding: {target_combo_padding};
        font-size: 11px;
        font-weight: 500;
        min-height: 20px;
        max-height: 22px;
    }}
    QComboBox#comboTarget:hover {{
        color: {theme.CYAN_PRIMARY};
        border: 1px solid {theme.CYAN_PRIMARY};
    }}
    QComboBox#comboTarget:on {{
        border: 1px solid {theme.CYAN_PRIMARY};
    }}
    QComboBox#comboTarget::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: {target_combo_pos};
        width: 14px;
        border: none;
        background: transparent;
    }}
    QComboBox#comboTarget::down-arrow {{
        image: url("assets/arrow_down.png");
        width: 8px;
        height: 8px;
    }}
    QComboBox#comboTarget::down-arrow:hover {{
        image: url("assets/arrow_down_cyan.png");
    }}
    QComboBox#comboTarget QAbstractItemView {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_PRIMARY};
        selection-background-color: {theme.SURFACE_3};
        selection-color: {theme.CYAN_PRIMARY};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 6px;
        padding: 4px;
        outline: none;
    }}
    QComboBox#comboTarget QAbstractItemView::item {{
        min-height: 22px;
        padding: 2px 6px;
        border-radius: 3px;
        border: none;
    }}
    QComboBox#comboTarget QAbstractItemView::item:hover {{
        background-color: {theme.SURFACE_3};
        color: {theme.CYAN_PRIMARY};
    }}
    QComboBox#comboTarget QAbstractItemView::item:selected {{
        background-color: {theme.CYAN_ALPHA_15};
        color: {theme.CYAN_PRIMARY};
    }}

    /* Compact Variant Dropdown (Language / Version Variants) */
    QComboBox#comboVariant {{
        background-color: {theme.SURFACE_2};
        color: {theme.CYAN_PRIMARY};
        border: 1px solid {theme.BORDER_CYAN};
        border-radius: 4px;
        padding: {target_combo_padding};
        font-size: 11px;
        font-weight: bold;
        min-height: 20px;
        max-height: 22px;
    }}
    QComboBox#comboVariant:hover {{
        background-color: {theme.SURFACE_3};
        border: 1px solid {theme.CYAN_PRIMARY};
        color: {theme.CYAN_HOVER};
    }}
    QComboBox#comboVariant:on {{
        border: 1px solid {theme.CYAN_PRIMARY};
        background-color: {theme.SURFACE_3};
    }}
    QComboBox#comboVariant::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: {target_combo_pos};
        width: 14px;
        border: none;
        background: transparent;
    }}
    QComboBox#comboVariant::down-arrow {{
        image: url("assets/arrow_down.png");
        width: 8px;
        height: 8px;
    }}
    QComboBox#comboVariant::down-arrow:hover {{
        image: url("assets/arrow_down_cyan.png");
    }}
    QComboBox#comboVariant QAbstractItemView {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_PRIMARY};
        selection-background-color: {theme.SURFACE_3};
        selection-color: {theme.CYAN_PRIMARY};
        border: 1px solid {theme.BORDER_CYAN};
        border-radius: 6px;
        padding: 4px;
        outline: none;
    }}
    QComboBox#comboVariant QAbstractItemView::item {{
        min-height: 22px;
        padding: 2px 6px;
        border-radius: 3px;
        border: none;
    }}
    QComboBox#comboVariant QAbstractItemView::item:hover {{
        background-color: {theme.SURFACE_3};
        color: {theme.CYAN_PRIMARY};
    }}
    QComboBox#comboVariant QAbstractItemView::item:selected {{
        background-color: {theme.CYAN_ALPHA_15};
        color: {theme.CYAN_PRIMARY};
    }}

    QPushButton#btnRefreshUsb {{
        background-color: {theme.SURFACE_2};
        color: {theme.CYAN_PRIMARY};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 6px;
        padding: 1px 8px;
        font-size: 11px;
        font-weight: bold;
        height: 24px;
        min-height: 24px;
        max-height: 24px;
    }}
    QPushButton#btnRefreshUsb:hover {{
        background-color: {theme.SURFACE_3};
        border: 1px solid {theme.CYAN_PRIMARY};
        color: #38BDF8;
    }}
    QPushButton#btnRefreshUsb:pressed {{
        background-color: {theme.CYAN_ALPHA_15};
    }}

    QPushButton#btnUsbSettings {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_MUTED};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 6px;
        font-size: 13px;
        height: 26px;
        min-height: 26px;
        max-height: 26px;
        width: 26px;
        min-width: 26px;
        max-width: 26px;
        padding: 0px;
    }}
    QPushButton#btnUsbSettings:hover {{
        background-color: {theme.SURFACE_3};
        border: 1px solid {theme.CYAN_PRIMARY};
        color: {theme.CYAN_PRIMARY};
    }}
    QPushButton#btnUsbSettings:pressed {{
        background-color: {theme.CYAN_ALPHA_15};
    }}

    /* Popup Menus */
    QMenu {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 8px;
        padding: 6px;
        font-size: 12px;
    }}
    QMenu::item {{
        padding: 6px 20px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: {theme.CYAN_ALPHA_15};
        color: {theme.CYAN_PRIMARY};
    }}
    QMenu::separator {{
        height: 1px;
        background-color: {theme.BORDER_SLATE};
        margin: 4px 8px;
    }}

    /* Labels */
    QLabel {{
        background-color: transparent;
        padding-bottom: 2px;
    }}

    /* CheckBoxes */
    QCheckBox {{
        color: {theme.TEXT_PRIMARY};
        spacing: 8px;
        font-size: 12px;
        background-color: transparent;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {theme.BORDER_SLATE};
        background-color: {theme.SURFACE_1};
    }}
    QCheckBox::indicator:hover {{
        border-color: {theme.CYAN_PRIMARY};
    }}
    QCheckBox::indicator:checked {{
        background-color: {theme.CYAN_PRIMARY};
        border-color: {theme.CYAN_PRIMARY};
        image: url("assets/checkbox_check.png");
    }}

    /* Radio Buttons */
    QRadioButton {{
        color: {theme.TEXT_PRIMARY};
        spacing: 8px;
        font-size: 12px;
        background-color: transparent;
    }}
    QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {theme.BORDER_SLATE};
        background-color: {theme.SURFACE_2};
    }}
    QRadioButton::indicator:hover {{
        border-color: {theme.CYAN_PRIMARY};
    }}
    QRadioButton::indicator:checked {{
        background-color: {theme.CYAN_PRIMARY};
        border-color: {theme.CYAN_PRIMARY};
        image: url("assets/checkbox_check.png");
    }}

    /* Operation Cancel Button */
    QPushButton#btnCancelOp {{
        background-color: {theme.CRIMSON_DANGER};
        color: #FFFFFF;
        border: none;
        font-size: 11px;
        font-weight: bold;
        padding: 0px 10px;
        border-radius: 4px;
        min-height: 22px;
        max-height: 22px;
    }}
    QPushButton#btnCancelOp:hover {{
        background-color: {theme.CRIMSON_HOVER};
    }}
    QPushButton#btnCancelOp:pressed {{
        background-color: #B91C1C;
    }}

    /* Scroll Areas & Scrollbars */
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}
    QScrollBar:vertical {{
        background-color: {theme.SURFACE_1};
        width: 8px;
        margin: 0;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {theme.BORDER_SLATE};
        min-height: 24px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {theme.CYAN_DIM};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
        background: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}

    QScrollBar:horizontal {{
        background-color: {theme.SURFACE_1};
        height: 8px;
        margin: 0;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {theme.SURFACE_3};
        min-width: 24px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {theme.CYAN_DIM};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
        background: none;
    }}

    /* Terminal Console */
    QPlainTextEdit#terminalEdit, QPlainTextEdit#terminalArea {{
        background-color: {theme.TERM_BG};
        color: {theme.TERM_TEXT_CYAN};
        font-family: "Consolas", "Courier New", "Segoe UI", "Tahoma", monospace;
        font-size: 11px;
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 6px;
        padding: 6px;
    }}

    /* Progress Bar */
    QProgressBar {{
        background-color: {theme.SURFACE_2};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 4px;
        min-height: 20px;
        max-height: 22px;
        height: 22px;
        text-align: center;
        color: #FFFFFF;
        font-size: 11px;
        font-weight: bold;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0099BB, stop:0.6 #00D2FF, stop:1 #33DCFF);
        border-radius: 3px;
    }}

    /* Message Box */
    QMessageBox {{
        background-color: {theme.SURFACE_1};
        color: {theme.TEXT_PRIMARY};
    }}
    QMessageBox QLabel {{
        color: {theme.TEXT_PRIMARY};
        font-size: 13px;
    }}
    """


def configure_smooth_combobox(combo) -> None:
    """
    Configures a QComboBox with an optimized, flicker-free QListView.
    Enforces uniform item sizing and disables OS window animation desync.
    """
    try:
        from PySide6.QtWidgets import QListView, QApplication
        from PySide6.QtCore import Qt

        app = QApplication.instance()
        if app:
            app.setEffectEnabled(Qt.UIEffect.UI_AnimateCombo, False)

        view = QListView(combo)
        view.setUniformItemSizes(True)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setAutoScroll(False)
        combo.setView(view)
    except Exception:
        pass

