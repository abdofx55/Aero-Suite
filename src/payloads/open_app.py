"""
open_app.py — Feature 3: Launch Specific Application Payload Generator.
Dispatches an Android intent to launch any installed package directly into the foreground.
"""
import os
import re
import time
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, write_script_file
from payloads.bash_builder import gen_bash_header, gen_launch_app, gen_bash_footer
from payloads.manual_generator import generate_info_content, write_payload_manuals


def prepare_open_app_usb(
    usb_drive: str,
    package_name: str,
    app_name: str = "",
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """Prepares USB payload to launch a specific application on the vehicle screen if installed."""
    def _log(msg):
        if log_func:
            log_func(msg)

    display_label = app_name or package_name
    _log(t("logs.prep_usb_header", f"\n── Preparing Open App USB ({display_label}): {usb_drive} ──", title=f"{t('nav.open_app_title', 'Open App')} ({display_label})", drive=usb_drive))
    if not os.path.exists(usb_drive):
        _log(t("logs.usb_not_found", f"  ✗ USB Drive not found: {usb_drive}", drive=usb_drive))
        return False

    if not package_name:
        _log(t("logs.no_pkg_launch", "  ✗ No package name provided to launch."))
        return False

    if cancel_check and cancel_check():
        _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
        return False

    clean_pkg = re.sub(r'[^a-zA-Z0-9._]', '', package_name)

    try:
        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=0.30)
        if cancel_check and cancel_check():
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False

        update_dir = os.path.join(usb_drive, "update")
        os.makedirs(update_dir, exist_ok=True)

        if progress_func:
            progress_func(0.60, f"Configuring launch trigger for {display_label}...", 0.0, 0, 0)

        script = (
            gen_bash_header(f"LAUNCH SPECIFIC APPLICATION\n# Target: {clean_pkg} ({display_label})", "open_app.log")
            + gen_launch_app(clean_pkg, log_var="LOG_FILE", capture_debug_log=True)
            + gen_bash_footer(success_status="SUCCESS", with_reboot=False)
        )
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.85, f"Writing launch manual (HTML) for {display_label}...", 0.0, 0, 0)

        write_payload_manuals(usb_drive, "Open_App_Info", "open_app", display_label=display_label, clean_pkg=clean_pkg)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, f"Launch {display_label} USB ready!", 0.0, 0, 0)

        _log(t("logs.prep_usb_success", f"✓ Open App USB prepared successfully for {display_label}.", title=f"{t('nav.open_app_title', 'Open App')} ({display_label})"))
        return True
    except Exception as e:
        log_exception(e, "prepare_open_app_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=f"{t('nav.open_app_title', 'Open App')} ({display_label})", err=str(e)))
        return False
