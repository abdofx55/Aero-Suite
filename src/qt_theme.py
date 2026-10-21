"""
qt_theme.py — Aero Suite Qt Cyber-Luxury Design System & QSS Stylesheet.
Calibrated for Dongfeng Shine (Aeolus D53) IVI Studio.
Engineered by Abdelrhman Hamdy - Senior Software Engineer.
"""
import theme

def get_application_stylesheet() -> str:
    """Returns the complete, unified QSS stylesheet for PySide6."""
    return f"""
    /* Global Base */
    QMainWindow, QWidget {{
        background-color: {theme.BG_BASE};
        color: {theme.TEXT_PRIMARY};
        font-family: "Segoe UI", "Inter", "Space Grotesk", sans-serif;
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
        border-bottom: 1px solid {theme.BORDER_SLATE};
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
        color: {theme.TEXT_DIM};
        border-color: {theme.BORDER_SLATE};
    }}

    /* Primary Accent Buttons (Cyan) */
    QPushButton[class="btnPrimary"] {{
        background-color: {theme.CYAN_PRIMARY};
        color: #070A0F;
        border: none;
        font-size: 13px;
        font-weight: bold;
        padding: 10px 20px;
        border-radius: 6px;
    }}
    QPushButton[class="btnPrimary"]:hover {{
        background-color: {theme.CYAN_HOVER};
    }}
    QPushButton[class="btnPrimary"]:pressed {{
        background-color: {theme.CYAN_DIM};
        color: {theme.TEXT_PRIMARY};
    }}
    QPushButton[class="btnPrimary"]:disabled {{
        background-color: {theme.SURFACE_3};
        color: {theme.TEXT_MUTED};
    }}

    /* Danger Accent Buttons (Crimson) */
    QPushButton[class="btnDanger"] {{
        background-color: {theme.CRIMSON_DANGER};
        color: #FFFFFF;
        border: none;
        font-size: 13px;
        font-weight: bold;
        padding: 10px 20px;
        border-radius: 6px;
    }}
    QPushButton[class="btnDanger"]:hover {{
        background-color: {theme.CRIMSON_HOVER};
    }}
    QPushButton[class="btnDanger"]:disabled {{
        background-color: {theme.SURFACE_3};
        color: {theme.TEXT_MUTED};
    }}

    /* Success Buttons (Mint) */
    QPushButton[class="btnSuccess"] {{
        background-color: {theme.MINT_SUCCESS};
        color: #070A0F;
        border: none;
        font-size: 12px;
        font-weight: bold;
        border-radius: 6px;
    }}
    QPushButton[class="btnSuccess"]:hover {{
        background-color: {theme.MINT_HOVER};
    }}

    /* Line Edits & Search Boxes */
    QLineEdit {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
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
        padding: 4px 24px 4px 10px;
        font-size: 11px;
        font-weight: 600;
        min-height: 26px;
    }}
    QComboBox:hover {{
        border-color: {theme.CYAN_PRIMARY};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
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
        padding: 4px;
    }}

    /* Specialized USB Header Bar */
    QComboBox#usbCombo {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 8px;
        padding: 4px 24px 4px 12px;
        font-size: 11px;
        font-weight: bold;
        min-height: 32px;
    }}
    QComboBox#usbCombo:hover {{
        border-color: {theme.CYAN_PRIMARY};
        background-color: {theme.SURFACE_3};
    }}
    QComboBox#usbCombo::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border: none;
    }}
    QComboBox#usbCombo::down-arrow {{
        image: url("assets/arrow_down.png");
        width: 10px;
        height: 10px;
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
    }}

    /* Compact Borderless Target Partition Dropdown (User App / System App) */
    QComboBox#comboTarget {{
        background-color: transparent;
        color: {theme.TEXT_MUTED};
        border: none;
        padding: 0px 18px 0px 2px;
        font-size: 11px;
        font-weight: 600;
        min-height: 20px;
        max-height: 22px;
    }}
    QComboBox#comboTarget:hover {{
        color: {theme.CYAN_PRIMARY};
        border: none;
    }}
    QComboBox#comboTarget::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: center right;
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

    QPushButton#btnRefreshUsb {{
        background-color: {theme.SURFACE_2};
        color: {theme.CYAN_PRIMARY};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 8px;
        padding: 4px 14px;
        font-size: 11px;
        font-weight: bold;
        min-height: 32px;
    }}
    QPushButton#btnRefreshUsb:hover {{
        background-color: {theme.SURFACE_3};
        border-color: {theme.CYAN_PRIMARY};
        color: #38BDF8;
    }}
    QPushButton#btnRefreshUsb:pressed {{
        background-color: {theme.CYAN_ALPHA_15};
    }}

    QPushButton#btnUsbSettings {{
        background-color: {theme.SURFACE_2};
        color: {theme.TEXT_MUTED};
        border: 1px solid {theme.BORDER_SLATE};
        border-radius: 8px;
        font-size: 14px;
        min-height: 32px;
        min-width: 34px;
    }}
    QPushButton#btnUsbSettings:hover {{
        background-color: {theme.SURFACE_3};
        border-color: {theme.CYAN_PRIMARY};
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
        border-radius: 8px;
        border: 1px solid {theme.BORDER_SLATE};
        background-color: {theme.SURFACE_1};
    }}
    QRadioButton::indicator:hover {{
        border-color: {theme.CYAN_PRIMARY};
    }}
    QRadioButton::indicator:checked {{
        background-color: {theme.CYAN_PRIMARY};
        border: 3px solid {theme.SURFACE_1};
    }}

    /* Operation Cancel Button */
    QPushButton#btnCancelOp {{
        background-color: {theme.CRIMSON_DANGER};
        color: #FFFFFF;
        border: none;
        font-size: 11px;
        font-weight: bold;
        padding: 4px 12px;
        border-radius: 6px;
        min-height: 24px;
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
        background-color: {theme.SURFACE_3};
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
    QPlainTextEdit#terminalEdit {{
        background-color: {theme.TERM_BG};
        color: {theme.TERM_TEXT_CYAN};
        font-family: "Consolas", "Courier New", monospace;
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
        height: 8px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background-color: {theme.CYAN_PRIMARY};
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
    """;
