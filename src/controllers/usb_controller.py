"""
usb_controller.py — USB Detection, Lifecycle, and Formatting Controller for Aero Suite.
Monitors removable drives, guards against mutations during payloads, and manages FAT32 formats.
"""
from PySide6.QtCore import QObject, Signal, Slot
from usb_detector import get_removable_drives, UsbWatcher
from core.store import get_store
from core.state import UsbDrivesChangedIntent, SelectUsbIntent, LogTerminalIntent
from core.i18n import t


class UsbSignalBridge(QObject):
    """Bridges UsbWatcher background callbacks to Qt signals on the main thread."""
    drives_changed = Signal(list)


class UsbController(QObject):
    """
    Manages removable USB drive detection, filesystem validation, and MVI store updates.
    """
    drives_updated = Signal(list)
    active_drive_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.store = get_store()
        self._pending_drives = None
        self._last_warned_count = 0
        self._last_logged_backup = None

        # USB Bridge & Monitoring
        self.bridge = UsbSignalBridge()
        self.bridge.drives_changed.connect(self._on_drives_changed)
        self.watcher = UsbWatcher(callback=self.bridge.drives_changed.emit, interval_sec=1.5)

    def start_watcher(self):
        """Starts background USB polling thread."""
        self.watcher.start()

    def stop_watcher(self):
        """Stops background USB polling thread."""
        self.watcher.stop()

    def rescan_drives(self):
        """Manually forces a rescan of all removable drives."""
        drives = get_removable_drives()
        self._on_drives_changed(drives)

    def select_drive(self, letter: str):
        """Selects a specific drive by its letter in the central store."""
        self.store.dispatch(SelectUsbIntent(letter))
        self.active_drive_changed.emit(self.store.state.active_usb)

    @Slot(list)
    def _on_drives_changed(self, drives: list):
        """Handles drive insertion or removal with active payload protection."""
        # BUG 2 GUARD: While payload is executing, never mutate active drive!
        if self.store.state.is_busy:
            self._pending_drives = drives
            return

        self.store.dispatch(UsbDrivesChangedIntent(drives))
        self.drives_updated.emit(drives)
        self.active_drive_changed.emit(self.store.state.active_usb)

        # Multi-drive safety warning
        if len(drives) > 1 and self._last_warned_count != len(drives):
            self._last_warned_count = len(drives)
            msg = t("common.multiple_drives_warn", f"⚠️ Multiple removable drives detected ({len(drives)} drives)! Please verify the target USB drive selected in the dropdown.", count=len(drives))
            self.store.dispatch(LogTerminalIntent(msg, "warn"))
        elif len(drives) == 1:
            self._last_warned_count = 1

        # Backup detection log
        active = self.store.state.active_usb
        if active and getattr(active, "has_backup", False):
            if self._last_logged_backup != active.letter:
                self._last_logged_backup = active.letter
                msg = t("logs.backup_detected", f"Car backup detected on {active.letter} (Date: {active.backup_date}). Ready for PC Vault Sync.", letter=active.letter, date=active.backup_date)
                self.store.dispatch(LogTerminalIntent(msg, "mint"))
        else:
            self._last_logged_backup = None

    def on_payload_finished(self):
        """Flushes any pending drive mutations that arrived while a payload was executing."""
        if self._pending_drives is not None:
            pending = self._pending_drives
            self._pending_drives = None
            self._on_drives_changed(pending)
