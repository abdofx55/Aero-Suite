"""
dialogs.py — Centered modal dialog helpers for Aero Suite.
Provides confirmation dialogs, success dialogs (with Open USB Drive), and error dialogs.
"""
import os
import re
from PySide6.QtWidgets import QMessageBox, QWidget
from PySide6.QtCore import Qt
import theme
from core.i18n import t


def show_confirm_dialog(
    parent: QWidget,
    title: str,
    message: str,
    confirm_text: str = None,
    is_danger: bool = False
) -> bool:
    """Shows a modal confirmation dialog."""
    if confirm_text is None:
        confirm_text = t("common.continue", "Continue")
    cancel_text = t("common.cancel", "Cancel")

    msg_box = QMessageBox(parent)
    msg_box.setWindowModality(Qt.WindowModal)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Warning if is_danger else QMessageBox.Question)
    btn_yes = msg_box.addButton(confirm_text, QMessageBox.YesRole)
    btn_no = msg_box.addButton(cancel_text, QMessageBox.NoRole)
    if is_danger:
        btn_yes.setStyleSheet(f"background-color: {theme.CRIMSON_DANGER}; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
    else:
        btn_yes.setStyleSheet(f"background-color: {theme.CYAN_PRIMARY}; color: black; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
    btn_no.setStyleSheet(f"background-color: {theme.SURFACE_3}; color: {theme.TEXT_PRIMARY}; padding: 6px 14px; border-radius: 4px;")
    msg_box.exec()
    return msg_box.clickedButton() == btn_yes


def show_success_dialog(
    parent: QWidget,
    title: str,
    message: str,
    on_open_usb=None,
    current_usb_letter: str = "",
    usb_drive: str = None
):
    """
    Shows a modal success dialog with 'OK' and 'Open USB Drive' buttons.
    Places 'OK' on the outer edge and 'Open USB' on the inside.
    """
    drive = usb_drive if usb_drive is not None else current_usb_letter
    msg_box = QMessageBox(parent)
    msg_box.setWindowModality(Qt.WindowModal)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Information)

    btn_open = msg_box.addButton(t("common.open_usb", "📂 Open USB Drive"), QMessageBox.ActionRole)
    btn_ok = msg_box.addButton(t("common.ok", "OK"), QMessageBox.AcceptRole)

    btn_ok.setStyleSheet(
        f"background-color: {theme.CYAN_PRIMARY}; color: black; font-weight: bold; "
        f"padding: 6px 20px; border: 1px solid {theme.CYAN_PRIMARY}; border-radius: 6px; min-height: 20px;"
    )
    btn_open.setStyleSheet(
        f"background-color: {theme.SURFACE_3}; color: {theme.TEXT_PRIMARY}; "
        f"font-weight: 600; padding: 6px 14px; border: 1px solid {theme.BORDER_SLATE}; "
        f"border-radius: 6px; min-height: 20px;"
    )

    msg_box.setDefaultButton(btn_ok)
    msg_box.exec()

    if msg_box.clickedButton() == btn_open:
        if not drive:
            m = re.search(r'drive\s+([A-Za-z]:[\\/]?)', message, re.IGNORECASE)
            if m:
                drive = m.group(1)
        if on_open_usb:
            on_open_usb(drive)
        elif drive and os.path.exists(drive):
            os.system(f'explorer "{drive}"')


def show_error_dialog(parent: QWidget, title: str, message: str):
    """Shows a modal error dialog."""
    msg_box = QMessageBox(parent)
    msg_box.setWindowModality(Qt.WindowModal)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Critical)
    btn_ok = msg_box.addButton(t("common.ok", "OK"), QMessageBox.AcceptRole)
    btn_ok.setStyleSheet(
        f"background-color: {theme.CYAN_PRIMARY}; color: black; font-weight: bold; "
        f"padding: 6px 20px; border: 1px solid {theme.CYAN_PRIMARY}; border-radius: 6px; min-height: 20px;"
    )
    msg_box.exec()
