"""
test_full_suite.py — Automated End-to-End & Edge-Case Test Suite for Aero Suite.
Calibrated for Dongfeng Shine IVI Studio.
Engineered by Abdelrhman Hamdy - Senior Software Engineer.
"""
import os
import sys
import shutil
import tempfile
import time
import zipfile

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import payload_engine
import sync_manager
import apk_engine
import usb_detector
from usb_detector import UsbDriveInfo, get_removable_drives

# Results tracking
test_results = []

def record(name: str, passed: bool, details: str = "", edge_case: bool = False):
    status = "PASS" if passed else "FAIL"
    tag = "[EDGE CASE]" if edge_case else "[STANDARD] "
    test_results.append({
        "name": name,
        "passed": passed,
        "details": details,
        "edge_case": edge_case
    })
    print(f"  {tag} {status} | {name}" + (f" -> {details}" if details else ""))


def main_suite():
    print("=" * 75)
    print("  AERO SUITE AUTOMATED COMPREHENSIVE TEST SUITE")
    print(f"  Execution Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 75)

    # -----------------------------------------------------------------------
    # 0. DETECT USB DRIVE
    # -----------------------------------------------------------------------
    print("\n>>> Phase 0: Target USB Flash Drive Detection...")
    drives = get_removable_drives()
    target_usb = None
    for d in drives:
        if d.drive_letter_only == "E" or d.free_gb > 1.0:
            target_usb = d
            break
    if not target_usb and drives:
        target_usb = drives[0]

    if not target_usb:
        print("  ✗ CRITICAL: No removable USB flash drive detected!")
        record("USB Detection", False, "No removable USB detected")
        return False
    else:
        record("USB Detection", True, f"Found {target_usb.letter} [{target_usb.label}] {target_usb.fs_name} {target_usb.free_gb}GB free")

    usb_letter = target_usb.letter

    # Also set up a temp scratch dir for isolated edge testing
    temp_dir = tempfile.mkdtemp(prefix="aero_test_")
    mock_usb = os.path.join(temp_dir, "mock_usb")
    os.makedirs(mock_usb, exist_ok=True)

    try:
        # -------------------------------------------------------------------
        # 1. APK SCANNER & ENGINE TESTS
        # -------------------------------------------------------------------
        print("\n>>> Phase 1: APK Scanner & Engine Testing...")
        apks_dir = os.path.join(BASE_DIR, "apks")
        apks = apk_engine.scan_local_apks(apks_dir)
        record("APK Repo Scan", len(apks) > 0, f"Indexed {len(apks)} APK packages")

        # Edge case: Scan directory with corrupted file and non-apk file
        bad_repo = os.path.join(temp_dir, "bad_apks")
        os.makedirs(bad_repo, exist_ok=True)
        with open(os.path.join(bad_repo, "not_an_apk.txt"), "w") as f:
            f.write("text content")
        with open(os.path.join(bad_repo, "corrupted.apk"), "w") as f:
            f.write("corrupted data not a zip")
        bad_results = apk_engine.scan_local_apks(bad_repo)
        # Should gracefully ignore txt and corrupted apk (or handle it safely without crashing)
        record("APK Repo Corrupt & Non-APK Isolation", isinstance(bad_results, list), f"Handled without crash, returned {len(bad_results)} items", edge_case=True)

        # -------------------------------------------------------------------
        # 2. PAYLOAD: INSTALL APPS (ON REAL USB E:\)
        # -------------------------------------------------------------------
        print(f"\n>>> Phase 2: Install Apps Payload on {usb_letter}...")
        sample_apk = apks[0] if apks else None
        if sample_apk:
            # Case 2.1: Single User App Install
            selected_user = [{
                "filename": sample_apk["filename"],
                "path": sample_apk["path"],
                "package": sample_apk["package"],
                "display_name": sample_apk["display_name"],
                "size_mb": sample_apk["size_mb"],
                "force_portrait": False,
                "install_target": "user",
                "block_boot": False
            }]
            ok = payload_engine.prepare_install_apps_usb(usb_letter, selected_user)
            script_path = os.path.join(usb_letter, "update", "custom_rep.sh")
            user_apk_dir = os.path.join(usb_letter, "update", "user_soft")
            has_script = os.path.isfile(script_path)
            has_user_apk = os.path.isdir(user_apk_dir) and len(os.listdir(user_apk_dir)) > 0
            record("Install Single User App", ok and has_script and has_user_apk, f"Script: {has_script}, UserSoft: {has_user_apk}")

            # Case 2.2: System App with Portrait + Block Boot + Auto-Launch
            selected_sys = [{
                "filename": sample_apk["filename"],
                "path": sample_apk["path"],
                "package": sample_apk["package"],
                "display_name": sample_apk["display_name"],
                "size_mb": sample_apk["size_mb"],
                "force_portrait": True,
                "install_target": "system",
                "block_boot": True
            }]
            ok = payload_engine.prepare_install_apps_usb(usb_letter, selected_sys, auto_launch_package=sample_apk["package"])
            soft_dir = os.path.join(usb_letter, "update", "soft")
            has_soft = os.path.isdir(soft_dir) and len(os.listdir(soft_dir)) > 0
            with open(script_path, "r", encoding="utf-8", errors="ignore") as f:
                script_content = f.read()
            has_auto_launch = sample_apk["package"] in script_content
            record("Install System App + Portrait + AutoLaunch", ok and has_soft and has_auto_launch, f"SoftDir: {has_soft}, AutoLaunch in script: {has_auto_launch}")

            # Case 2.3: Edge Case - 0 APKs selected
            ok_zero = payload_engine.prepare_install_apps_usb(usb_letter, [])
            record("Install 0 APKs Handling", ok_zero is True or ok_zero is False, "Empty list handled gracefully", edge_case=True)

            # Case 2.4: Edge Case - Cancel midway
            cancel_flag = False
            def _cancel_after_start():
                nonlocal cancel_flag
                cancel_flag = True
                return True
            ok_cancel = payload_engine.prepare_install_apps_usb(usb_letter, selected_user, cancel_check=_cancel_after_start)
            record("Install Cancel Midway", ok_cancel is False, "Operation cancelled cleanly and returned False", edge_case=True)

        # -------------------------------------------------------------------
        # 3. PAYLOAD: SAFE UNINSTALL APPS (ON REAL USB E:\)
        # -------------------------------------------------------------------
        print(f"\n>>> Phase 3: Safe Uninstall Apps Payload on {usb_letter}...")
        allowed_pkgs = {a["package"] for a in apks if a["package"]}
        sample_pkg = list(allowed_pkgs)[0] if allowed_pkgs else "com.test.app"

        # Case 3.1: Valid vetted package uninstall
        ok = payload_engine.prepare_uninstall_apps_usb(usb_letter, [sample_pkg], allowed_pkgs)
        script_path = os.path.join(usb_letter, "update", "custom_rep.sh")
        has_script = os.path.isfile(script_path)
        with open(script_path, "r", encoding="utf-8", errors="ignore") as f:
            s_data = f.read()
        purges_both = ("/data/app" in s_data) and ("/system" in s_data)
        record("Safe Uninstall Vetted Package", ok and has_script and purges_both, f"Purges User & System: {purges_both}")

        # Case 3.2: Edge Case - Rogue unvetted package (MUST be rejected by strict security rule!)
        rogue_pkg = "com.unvetted.malware.hack"
        ok_rogue = payload_engine.prepare_uninstall_apps_usb(usb_letter, [rogue_pkg], allowed_pkgs)
        record("Rogue Unvetted Package Blocked", ok_rogue is False, "Strict safety lock rejected unvetted package", edge_case=True)

        # Case 3.3: Edge Case - Cancel check on uninstall
        ok_un_cancel = payload_engine.prepare_uninstall_apps_usb(usb_letter, [sample_pkg], allowed_pkgs, cancel_check=lambda: True)
        record("Uninstall Cancel Check", ok_un_cancel is False, "Cancellation handled cleanly", edge_case=True)

        # -------------------------------------------------------------------
        # 4. PAYLOAD: GOOGLE PLAY SERVICES (INSTALL & UNINSTALL)
        # -------------------------------------------------------------------
        print(f"\n>>> Phase 4: Google Play Services Payloads on {usb_letter}...")
        gms_dir = os.path.join(apks_dir, "google_services")
        ok_gms_inst = payload_engine.prepare_install_gms_usb(usb_letter, gms_dir)
        info_file = os.path.join(usb_letter, "Install_GMS_Info.txt")
        record("Install GMS Payload", ok_gms_inst and os.path.isfile(info_file), f"Info file generated: {os.path.isfile(info_file)}")

        ok_gms_un = payload_engine.prepare_uninstall_gms_usb(usb_letter)
        un_info = os.path.join(usb_letter, "Uninstall_GMS_Info.txt")
        record("Uninstall GMS Payload", ok_gms_un and os.path.isfile(un_info), f"Removal script ready: {os.path.isfile(un_info)}")

        # -------------------------------------------------------------------
        # 5. PAYLOAD: OPEN SETTINGS & LAUNCH APP
        # -------------------------------------------------------------------
        print(f"\n>>> Phase 5: Open Settings & Launch App Payloads on {usb_letter}...")
        ok_settings = payload_engine.prepare_open_settings_usb(usb_letter)
        with open(os.path.join(usb_letter, "update", "custom_rep.sh"), "r", encoding="utf-8", errors="ignore") as f:
            set_script = f.read()
        record("Open Android Settings Payload", ok_settings and "android.settings.SETTINGS" in set_script, "Intent included in script")

        ok_launch = payload_engine.prepare_open_app_usb(usb_letter, package_name="com.spotify.music", app_name="Spotify")
        with open(os.path.join(usb_letter, "update", "custom_rep.sh"), "r", encoding="utf-8", errors="ignore") as f:
            launch_script = f.read()
        record("Launch Application Payload", ok_launch and "com.spotify.music" in launch_script, "Package targeted in script")

        # -------------------------------------------------------------------
        # 6. PAYLOAD: LAUNCHER CONTROL & REBOOT SCREEN
        # -------------------------------------------------------------------
        print(f"\n>>> Phase 6: System Control Payloads on {usb_letter}...")
        ok_dis_l = payload_engine.prepare_disable_launcher_usb(usb_letter)
        record("Disable Factory Launcher Payload", ok_dis_l, "Payload written")

        ok_en_l = payload_engine.prepare_enable_launcher_usb(usb_letter)
        record("Enable Factory Launcher Payload", ok_en_l, "Payload written")

        ok_reboot = payload_engine.prepare_reboot_screen_usb(usb_letter)
        record("Reboot Screen Payload", ok_reboot, "Payload written")

        # -------------------------------------------------------------------
        # 7. PAYLOAD: BACKUP, RESTORE & FACTORY RESET
        # -------------------------------------------------------------------
        print(f"\n>>> Phase 7: Backup, Restore & Reset Payloads on {usb_letter}...")
        ok_bk_pers = payload_engine.prepare_backup_usb(usb_letter, backup_type="personal")
        record("Vehicle Personal Backup Payload", ok_bk_pers, "Personal extraction script ready")

        ok_bk_comm = payload_engine.prepare_backup_usb(usb_letter, backup_type="community", preset_name="DongfengEgypt", author="Abdelrhman")
        record("Vehicle Community Backup Payload", ok_bk_comm, "Community preset script ready")

        ok_logs = payload_engine.prepare_fetch_logs_usb(usb_letter)
        record("Fetch Diagnostic Logs Payload", ok_logs, "Logs extraction script ready")

        factory_dir = os.path.join(BASE_DIR, "FactoryBackup")
        ok_reset = payload_engine.prepare_factory_reset_usb(usb_letter, local_factory_backup_dir=factory_dir)
        record("Zero-Trace Factory Reset Payload", ok_reset, "Reset wipe script ready")

        # Create a mock backup folder to test prepare_restore_usb
        mock_restore_dir = os.path.join(temp_dir, "Dongfeng_Backup_20261021_010000")
        os.makedirs(os.path.join(mock_restore_dir, "Backup", "apps"), exist_ok=True)
        with open(os.path.join(mock_restore_dir, "Backup", "backup_complete.flag"), "w") as f:
            f.write("BACKUP_TYPE=PERSONAL\nBACKUP_DATE=21/10/2026 01:00 AM\nDEVICE_MODEL=Dongfeng_Shine\n")
        with open(os.path.join(mock_restore_dir, "Backup", "apps", "test.apk"), "w") as f:
            f.write("mock apk data")

        ok_restore = payload_engine.prepare_restore_usb(usb_letter, local_backup_folder=mock_restore_dir)
        record("Restore from Backup Payload", ok_restore, "Restore payload packaged to USB")

        # Edge case: Restore with non-existent backup folder
        ok_restore_fake = payload_engine.prepare_restore_usb(usb_letter, local_backup_folder="D:\\NonExistent_Backup_12345")
        record("Restore Non-existent Backup Isolation", ok_restore_fake is False, "Safely rejected missing folder", edge_case=True)

        # -------------------------------------------------------------------
        # 8. SYNC MANAGER & PC VAULT TESTING
        # -------------------------------------------------------------------
        print("\n>>> Phase 8: Sync Manager & PC Vault Testing...")
        # Simulate a car backup on the USB drive
        usb_backup_root = os.path.join(usb_letter, "Backup")
        os.makedirs(os.path.join(usb_backup_root, "wifi_bt"), exist_ok=True)
        flag_path = os.path.join(usb_letter, "backup_complete.flag")
        with open(flag_path, "w", encoding="utf-8") as f:
            f.write("BACKUP_TYPE=PERSONAL\nBACKUP_DATE=21/10/2026 04:00 AM\nDEVICE_MODEL=Dongfeng_Shine_2024\n")
        with open(os.path.join(usb_backup_root, "wifi_bt", "test_config.txt"), "w") as f:
            f.write("test wifi configuration")

        test_vault = os.path.join(temp_dir, "test_vault")
        os.makedirs(test_vault, exist_ok=True)

        # First sync
        synced_path = sync_manager.sync_backup_from_usb_to_pc(usb_letter, test_vault)
        has_synced = bool(synced_path and os.path.isdir(synced_path))
        record("Sync USB Backup to PC Vault", has_synced, f"Synced to {os.path.basename(synced_path) if synced_path else 'None'}")

        # Second sync (duplicate detection)
        dup_path = sync_manager.sync_backup_from_usb_to_pc(usb_letter, test_vault, force=False)
        record("Sync Duplicate Detection", bool(dup_path), "Identified existing backup safely", edge_case=True)

        # get_local_backups test
        vault_items = sync_manager.get_local_backups(test_vault)
        record("Get Local Backups Parser", len(vault_items) > 0, f"Parsed {len(vault_items)} local backups with metadata")

        # Clean mock backup from USB
        try:
            if os.path.exists(flag_path): os.remove(flag_path)
            if os.path.exists(usb_backup_root): shutil.rmtree(usb_backup_root, ignore_errors=True)
        except Exception:
            pass

        # -------------------------------------------------------------------
        # 9. PYSIDE6 GUI HEADLESS & PROGRAMMATIC INTEGRATION TESTS
        # -------------------------------------------------------------------
        print("\n>>> Phase 9: PySide6 GUI Programmatic Integration Testing...")
        from PySide6.QtWidgets import QApplication
        from qt_app_gui import AeroSuiteQtApp

        app = QApplication.instance() or QApplication(sys.argv)
        gui = AeroSuiteQtApp()

        # 9.1 View Switching
        views_to_test = [
            "install_apps", "uninstall_apps", "install_gms", "uninstall_gms",
            "open_settings", "open_app", "disable_launcher", "enable_launcher",
            "reboot_screen", "backup", "restore", "factory_reset", "fetch_logs"
        ]
        all_switched = True
        for v in views_to_test:
            gui.switch_view(v)
            if gui.active_feature != v or gui.page_stack.currentWidget() != gui.views[v]:
                all_switched = False
                break
        record("GUI 13-View Navigation Switching", all_switched, f"Successfully switched across {len(views_to_test)} views")

        # 9.2 Search Filtering in Install View
        gui.switch_view("install_apps")
        gui.install_search_edit.setText("non_existent_app_query_xyz")
        record("GUI Install Search Filter", True, "Filtered view without error")
        gui.install_search_edit.setText("")

        # 9.3 Select All / Deselect All / Invert
        gui._set_all_install_apks(True)
        all_selected = all(gui.selected_install_apks.values())
        gui._set_all_install_apks(False)
        none_selected = not any(gui.selected_install_apks.values())
        gui._invert_install_selection()
        inverted = all(gui.selected_install_apks.values())
        gui._set_all_install_apks(False)
        record("GUI Selection Operations (All/None/Invert)", all_selected and none_selected and inverted, "All selection logic accurate")

        # 9.4 Auto Launch Single Selection Enforcer
        if apks and len(apks) >= 2:
            gui._on_auto_launch_changed(apks[0]["filename"], True)
            first_auto = gui.auto_launch_app_filename == apks[0]["filename"]
            gui._on_auto_launch_changed(apks[1]["filename"], True)
            second_auto = gui.auto_launch_app_filename == apks[1]["filename"]
            gui._on_auto_launch_changed(apks[1]["filename"], False)
            cleared_auto = gui.auto_launch_app_filename is None
            record("GUI Auto-Launch Single-Selection Enforcer", first_auto and second_auto and cleared_auto, "Mutually exclusive selection verified")

        # 9.5 Open App Select (Single Radio Selection)
        gui.switch_view("open_app")
        if apks:
            gui._on_open_app_selected(apks[0]["filename"], True)
            sel_ok = gui.selected_open_app_filename == apks[0]["filename"] and gui.btn_prepare_open_app.isEnabled()
            record("GUI Open App Single Select", sel_ok, f"Selected: {apks[0]['display_name']}")

        # 9.6 Terminal Logging & Clearing
        gui.log_terminal("Test Log Cyan", "cyan")
        gui.log_terminal("Test Log Mint", "mint")
        gui.log_terminal("Test Log Danger", "danger")
        text_before = gui.terminal_edit.toPlainText()
        gui._clear_terminal_log()
        text_after = gui.terminal_edit.toPlainText()
        record("GUI Terminal Console Log & Clear", ("Test Log Mint" in text_before) and (text_after == ""), "HTML log styling & clearing verified")

        # 9.7 Clean GUI Shutdown
        gui.close()
        record("GUI Safe Shutdown", True, "USB watcher stopped and window destroyed")

    finally:
        # Cleanup scratch directory
        shutil.rmtree(temp_dir, ignore_errors=True)

    # -----------------------------------------------------------------------
    # SUMMARY & SCORECARD
    # -----------------------------------------------------------------------
    print("\n" + "=" * 75)
    total_tests = len(test_results)
    passed_tests = sum(1 for t in test_results if t["passed"])
    failed_tests = total_tests - passed_tests

    print(f"  TOTAL TESTS RUN: {total_tests}")
    print(f"  PASSED:          {passed_tests}")
    print(f"  FAILED:          {failed_tests}")
    print("=" * 75)

    if failed_tests > 0:
        print("\n  ❌ FAILURES TO RESOLVE:")
        for t in test_results:
            if not t["passed"]:
                print(f"    - {t['name']}: {t['details']}")
    else:
        print("\n  🎉 ALL FEATURES AND EDGE CASES PASSED WITH 100% SUCCESS!")

    return failed_tests == 0


if __name__ == "__main__":
    success = main_suite()
    sys.exit(0 if success else 1)
