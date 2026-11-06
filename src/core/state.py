"""
state.py — MVI (Model-View-Intent) State & Reducer Core for Aero Suite.
Provides immutable application state and typed intents for unidirectional data flow.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from core.models import UsbDriveModel, ApkMetadata


@dataclass(frozen=True)
class AppState:
    """Immutable single source of truth for the entire application state."""
    # USB & Hardware
    drives: Tuple[Any, ...] = ()
    active_usb: Optional[Any] = None
    is_busy: bool = False
    busy_message: str = ""

    # Navigation & Language
    current_view: str = "install_apps"
    current_language: str = "ar"

    # Multi-command basket
    basket_count: int = 0
    basket_items: Tuple[Any, ...] = ()

    # Terminal Logs history (text, level)
    logs: Tuple[Tuple[str, str], ...] = ()

    # App selections (pkg/filename -> bool or settings)
    selected_install_apks: Dict[str, bool] = field(default_factory=dict)
    selected_uninstall_pkgs: Dict[str, bool] = field(default_factory=dict)
    per_app_target: Dict[str, str] = field(default_factory=dict)       # filename -> "user" | "system"
    per_app_portrait: Dict[str, bool] = field(default_factory=dict)     # filename -> bool
    per_app_boot: Dict[str, bool] = field(default_factory=dict)         # filename -> bool
    auto_launch_app: Optional[str] = None


# -------------------------------------------------------------
# Typed User & System Intents (Actions)
# -------------------------------------------------------------
@dataclass(frozen=True)
class Intent:
    """Base marker class for all MVI intents."""
    pass


@dataclass(frozen=True)
class UsbDrivesChangedIntent(Intent):
    drives: List[Any]


@dataclass(frozen=True)
class SelectUsbIntent(Intent):
    drive_letter: str


@dataclass(frozen=True)
class SetBusyIntent(Intent):
    is_busy: bool
    message: str = ""


@dataclass(frozen=True)
class ChangeViewIntent(Intent):
    view_name: str


@dataclass(frozen=True)
class ChangeLanguageIntent(Intent):
    language_code: str


@dataclass(frozen=True)
class LogTerminalIntent(Intent):
    message: str
    level: str = "cyan"


@dataclass(frozen=True)
class UpdateBasketIntent(Intent):
    count: int
    items: List[Any] = field(default_factory=list)


@dataclass(frozen=True)
class ToggleInstallApkIntent(Intent):
    filename: str
    selected: bool


@dataclass(frozen=True)
class SetAppTargetIntent(Intent):
    filename: str
    target: str   # "user" or "system"


@dataclass(frozen=True)
class SetAppPortraitIntent(Intent):
    filename: str
    portrait: bool


@dataclass(frozen=True)
class SetAutoLaunchAppIntent(Intent):
    filename: Optional[str]


# -------------------------------------------------------------
# Pure State Reducer
# -------------------------------------------------------------
def app_reducer(state: AppState, intent: Intent) -> AppState:
    """Pure reducer function that computes a new AppState from an Intent."""
    if isinstance(intent, UsbDrivesChangedIntent):
        drives = tuple(intent.drives)
        active = state.active_usb
        # If currently selected USB is still present, retain it
        if drives:
            matched = next((d for d in drives if active and getattr(d, 'letter', None) == getattr(active, 'letter', None)), None)
            active = matched if matched else drives[0]
        else:
            active = None

        return AppState(
            drives=drives,
            active_usb=active,
            is_busy=state.is_busy,
            busy_message=state.busy_message,
            current_view=state.current_view,
            current_language=state.current_language,
            basket_count=state.basket_count,
            basket_items=state.basket_items,
            logs=state.logs,
            selected_install_apks=state.selected_install_apks,
            selected_uninstall_pkgs=state.selected_uninstall_pkgs,
            per_app_target=state.per_app_target,
            per_app_portrait=state.per_app_portrait,
            per_app_boot=state.per_app_boot,
            auto_launch_app=state.auto_launch_app,
        )

    elif isinstance(intent, SelectUsbIntent):
        matched = next((d for d in state.drives if getattr(d, 'letter', '') == intent.drive_letter), None)
        return AppState(
            drives=state.drives,
            active_usb=matched,
            is_busy=state.is_busy,
            busy_message=state.busy_message,
            current_view=state.current_view,
            current_language=state.current_language,
            basket_count=state.basket_count,
            basket_items=state.basket_items,
            logs=state.logs,
            selected_install_apks=state.selected_install_apks,
            selected_uninstall_pkgs=state.selected_uninstall_pkgs,
            per_app_target=state.per_app_target,
            per_app_portrait=state.per_app_portrait,
            per_app_boot=state.per_app_boot,
            auto_launch_app=state.auto_launch_app,
        )

    elif isinstance(intent, SetBusyIntent):
        return AppState(
            drives=state.drives,
            active_usb=state.active_usb,
            is_busy=intent.is_busy,
            busy_message=intent.message,
            current_view=state.current_view,
            current_language=state.current_language,
            basket_count=state.basket_count,
            basket_items=state.basket_items,
            logs=state.logs,
            selected_install_apks=state.selected_install_apks,
            selected_uninstall_pkgs=state.selected_uninstall_pkgs,
            per_app_target=state.per_app_target,
            per_app_portrait=state.per_app_portrait,
            per_app_boot=state.per_app_boot,
            auto_launch_app=state.auto_launch_app,
        )

    elif isinstance(intent, ChangeViewIntent):
        return AppState(
            drives=state.drives,
            active_usb=state.active_usb,
            is_busy=state.is_busy,
            busy_message=state.busy_message,
            current_view=intent.view_name,
            current_language=state.current_language,
            basket_count=state.basket_count,
            basket_items=state.basket_items,
            logs=state.logs,
            selected_install_apks=state.selected_install_apks,
            selected_uninstall_pkgs=state.selected_uninstall_pkgs,
            per_app_target=state.per_app_target,
            per_app_portrait=state.per_app_portrait,
            per_app_boot=state.per_app_boot,
            auto_launch_app=state.auto_launch_app,
        )

    elif isinstance(intent, ChangeLanguageIntent):
        return AppState(
            drives=state.drives,
            active_usb=state.active_usb,
            is_busy=state.is_busy,
            busy_message=state.busy_message,
            current_view=state.current_view,
            current_language=intent.language_code,
            basket_count=state.basket_count,
            basket_items=state.basket_items,
            logs=state.logs,
            selected_install_apks=state.selected_install_apks,
            selected_uninstall_pkgs=state.selected_uninstall_pkgs,
            per_app_target=state.per_app_target,
            per_app_portrait=state.per_app_portrait,
            per_app_boot=state.per_app_boot,
            auto_launch_app=state.auto_launch_app,
        )

    elif isinstance(intent, LogTerminalIntent):
        new_logs = state.logs + ((intent.message, intent.level),)
        # Keep latest 500 logs to protect memory
        if len(new_logs) > 500:
            new_logs = new_logs[-500:]
        return AppState(
            drives=state.drives,
            active_usb=state.active_usb,
            is_busy=state.is_busy,
            busy_message=state.busy_message,
            current_view=state.current_view,
            current_language=state.current_language,
            basket_count=state.basket_count,
            basket_items=state.basket_items,
            logs=new_logs,
            selected_install_apks=state.selected_install_apks,
            selected_uninstall_pkgs=state.selected_uninstall_pkgs,
            per_app_target=state.per_app_target,
            per_app_portrait=state.per_app_portrait,
            per_app_boot=state.per_app_boot,
            auto_launch_app=state.auto_launch_app,
        )

    elif isinstance(intent, UpdateBasketIntent):
        return AppState(
            drives=state.drives,
            active_usb=state.active_usb,
            is_busy=state.is_busy,
            busy_message=state.busy_message,
            current_view=state.current_view,
            current_language=state.current_language,
            basket_count=intent.count,
            basket_items=tuple(intent.items),
            logs=state.logs,
            selected_install_apks=state.selected_install_apks,
            selected_uninstall_pkgs=state.selected_uninstall_pkgs,
            per_app_target=state.per_app_target,
            per_app_portrait=state.per_app_portrait,
            per_app_boot=state.per_app_boot,
            auto_launch_app=state.auto_launch_app,
        )

    elif isinstance(intent, ToggleInstallApkIntent):
        new_sel = dict(state.selected_install_apks)
        new_sel[intent.filename] = intent.selected
        return AppState(
            drives=state.drives,
            active_usb=state.active_usb,
            is_busy=state.is_busy,
            busy_message=state.busy_message,
            current_view=state.current_view,
            current_language=state.current_language,
            basket_count=state.basket_count,
            basket_items=state.basket_items,
            logs=state.logs,
            selected_install_apks=new_sel,
            selected_uninstall_pkgs=state.selected_uninstall_pkgs,
            per_app_target=state.per_app_target,
            per_app_portrait=state.per_app_portrait,
            per_app_boot=state.per_app_boot,
            auto_launch_app=state.auto_launch_app,
        )

    return state
