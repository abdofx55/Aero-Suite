"""
dialogs.py — Centered modal dialog helpers for Aero Suite.
Provides confirmation dialogs, success dialogs (with Open USB Drive), and error dialogs.
"""
import os
import re
from PySide6.QtWidgets import QMessageBox, QWidget
from PySide6.QtCore import Qt
import theme


def show_confirm_dialog(
    parent: QWidget,
    title: str,
    message: str,
    confirm_text: str = "Proceed",
    is_danger: bool = False
) -> bool:
    """Shows a modal confirmation dialog."""
    msg_box = QMessageBox(parent)
    msg_box.setWindowModality(Qt.WindowModal)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Warning if is_danger else QMessageBox.Question)
    btn_yes = msg_box.addButton(confirm_text, QMessageBox.YesRole)
    btn_no = msg_box.addButton("Cancel", QMessageBox.NoRole)
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
    current_usb_letter: str = ""
):
    """Shows a modal success dialog with 'Open USB Drive' and 'OK' buttons."""
    msg_box = QMessageBox(parent)
    msg_box.setWindowModality(Qt.WindowModal)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Information)

    btn_open = msg_box.addButton("📂 Open USB Drive", QMessageBox.ActionRole)
    btn_ok = msg_box.addButton("OK", QMessageBox.RejectRole)

    btn_open.setStyleSheet(
        f"background-color: {theme.SURFACE_3}; color: {theme.TEXT_PRIMARY}; "
        f"font-weight: 600; padding: 6px 14px; border: 1px solid {theme.BORDER_SLATE}; "
        f"border-radius: 6px; min-height: 20px;"
    )
    btn_ok.setStyleSheet(
        f"background-color: {theme.CYAN_PRIMARY}; color: black; font-weight: bold; "
        f"padding: 6px 20px; border: 1px solid {theme.CYAN_PRIMARY}; border-radius: 6px; min-height: 20px;"
    )

    msg_box.setDefaultButton(btn_ok)
    msg_box.exec()

    if msg_box.clickedButton() == btn_open and on_open_usb:
        drive = current_usb_letter
        if not drive:
            m = re.search(r'drive\s+([A-Za-z]:[\\/]?)', message, re.IGNORECASE)
            if m:
                drive = m.group(1)
        on_open_usb(drive)


def show_error_dialog(parent: QWidget, title: str, message: str):
    """Shows a modal error dialog."""
    QMessageBox.critical(parent, title, message)
