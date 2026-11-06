"""
payload_controller.py — Background Payload Execution & Lifecycle Controller for Aero Suite.
Handles asynchronous worker threads, cancellation, progress normalization, and logging.
"""
import os
import threading
import inspect
from PySide6.QtCore import QObject, QThread, Signal
from core.i18n import t, get_i18n
from core.exceptions import log_exception
from core.store import get_store
from core.state import SetBusyIntent, LogTerminalIntent


def format_progress_status(text: str, extra_args: tuple) -> str:
    """Localizes progress text and transfer status into current application language."""
    is_rtl = get_i18n().is_rtl()
    str_text = str(text).strip()
    if not str_text:
        return ""

    if str_text.startswith("Configuring & repacking: "):
        name = str_text[25:].rstrip(".")
        return f"تجهيز وضبط الحزمة: {name}..." if is_rtl else t("progress.repacking_pkg", f"Configuring & repacking: {name}...", name=name)

    if str_text.startswith("Signing package: "):
        name = str_text[17:].rstrip(".")
        return f"توقيع الحزمة رقمياً: {name}..." if is_rtl else t("progress.signing_pkg", f"Signing package: {name}...", name=name)

    if str_text.startswith("Page-aligning package: "):
        name = str_text[23:].rstrip(".")
        return f"ضبط محاذاة المعالج: {name}..." if is_rtl else t("progress.aligning_pkg", f"Page-aligning package: {name}...", name=name)

    if str_text.startswith("Extracting native libraries for "):
        name = str_text[32:].rstrip(".")
        return f"فك مكتبات المعالج لـ {name}..." if is_rtl else t("progress.extracting_libs_for", f"Extracting native libraries for {name}...", name=name)

    # File transfer progress (copied_mb, total_mb, speed)
    if len(extra_args) >= 3 and isinstance(extra_args[1], (int, float)) and isinstance(extra_args[2], (int, float)) and extra_args[2] > 0:
        c_mb = extra_args[1]
        t_mb = extra_args[2]
        spd = extra_args[0] if len(extra_args) >= 1 and isinstance(extra_args[0], (int, float)) and extra_args[0] > 0 else 0.0
        clean_name = os.path.basename(str(text)) if ("/" in str(text) or "\\" in str(text)) else str(text)

        if spd > 0.05:
            if is_rtl:
                return f"جاري نسخ {clean_name} \u200e({c_mb:.1f} / {t_mb:.1f} ميجا)\u200e • \u200e{spd:.1f} ميجا/ث\u200e"
            return t("progress.transferring_speed", f"Transferring {clean_name} ({c_mb:.1f}/{t_mb:.1f} MB) • {spd:.1f} MB/s", name=clean_name, copied=c_mb, total=t_mb, speed=spd)
        else:
            if is_rtl:
                return f"جاري نسخ {clean_name} \u200e({c_mb:.1f} / {t_mb:.1f} ميجا)\u200e"
            return t("progress.transferring", f"Transferring {clean_name} ({c_mb:.1f}/{t_mb:.1f} MB)", name=clean_name, copied=c_mb, total=t_mb)

    if str_text.startswith("Cleaning: "):
        item = str_text[10:]
        return f"جاري تنظيف: {item}" if is_rtl else t("progress.cleaning_item", f"Cleaning: {item}", name=item)

    if "ready!" in str_text.lower():
        return "فلاشة الـ USB جاهزة للاستخدام في عربيتك! ✨" if is_rtl else t("progress.usb_ready", str_text)

    mapping = {
        "Inspecting USB drive contents...": ("progress.inspecting_usb", "فحص محتويات الفلاشة..."),
        "Cleaning USB drive...": ("progress.cleaning_usb", "جاري تنظيف الفلاشة..."),
        "USB drive is clean and ready.": ("progress.usb_clean_ready", "الفلاشة جاهزة ونظيفة."),
        "Flushing filesystem buffers to USB drive...": ("progress.flushing_buffers", "تأكيد كتابة وتفريغ البيانات ع الفلاشة..."),
        "Extracting native libraries & verifying signatures...": ("progress.extracting_libs", "فك مكتبات المعالج والتأكد من التوقيع..."),
        "Generating automated installer script (custom_rep.sh)...": ("progress.generating_script", "تجهيز سكريبت التثبيت التلقائي..."),
        "Writing vehicle manual & manifest flags...": ("progress.writing_manual", "كتابة دليل الاستخدام وملف التعليمات..."),
        "Writing uninstallation manual & instructions...": ("progress.writing_manual", "كتابة دليل الاستخدام وملف التعليمات..."),
        "Writing Google Services manual & permissions...": ("progress.writing_manual", "كتابة دليل الاستخدام وملف التعليمات..."),
        "Writing Google Services removal manual...": ("progress.writing_manual", "كتابة دليل الاستخدام وملف التعليمات..."),
        "Writing disable launcher manual...": ("progress.writing_manual", "كتابة دليل الاستخدام وملف التعليمات..."),
        "Writing enable launcher manual...": ("progress.writing_manual", "كتابة دليل الاستخدام وملف التعليمات..."),
        "Writing restart screen manual...": ("progress.writing_manual", "كتابة دليل الاستخدام وملف التعليمات..."),
        "Writing restoration manual & verification flags...": ("progress.writing_manual", "كتابة دليل الاستخدام وملف التعليمات..."),
        "Writing Zero-Trace purge manual...": ("progress.writing_manual", "كتابة دليل الاستخدام وملف التعليمات..."),
        "Writing diagnostic logs manual...": ("progress.writing_manual", "كتابة دليل الاستخدام وملف التعليمات..."),
        "Generating GMS injection script & permissions...": ("progress.generating_script", "تجهيز سكريبت تثبيت خدمات جوجل..."),
        "Configuring GMS clean purge script...": ("progress.generating_script", "تجهيز سكريبت حذف خدمات جوجل..."),
        "Generating infotainment reboot payload...": ("progress.generating_script", "تجهيز أمر إعادة تشغيل الشاشة..."),
        "Verifying backup metadata & vehicle profile...": ("progress.verifying_backup", "التحقق من بيانات وملفات النسخة الاحتياطية..."),
        "Generating 12-step restoration script (custom_rep.sh)...": ("progress.generating_script", "تجهيز سكريبت استرجاع البيانات..."),
        "Configuring logcat & diagnostic dump script...": ("progress.generating_script", "تجهيز سكريبت سحب اللوجات والفحص..."),
        "Preparing operation...": ("progress.preparing_op", "بنجهز للعملية..."),
        "System Idle — Ready for operation.": ("app.idle_status", "النظام جاهز ومستني أوامرك."),
    }

    for k, (loc_key, default_ar) in mapping.items():
        if k.lower() in str_text.lower() or str_text.lower() in k.lower():
            return default_ar if is_rtl else t(loc_key, k)

    if str_text.startswith("Writing ") and "manual" in str_text:
        return "كتابة دليل الاستخدام وملف التعليمات..." if is_rtl else t("progress.writing_manual", str_text)

    if str_text.startswith("Configuring ") and "command" in str_text:
        return "تجهيز أوامر الحذف الآمن..." if is_rtl else t("progress.generating_script", str_text)

    return str_text


class PayloadWorker(QThread):
    """Executes a payload operation in the background and reports progress and logs."""
    progress_signal = Signal(int, str)
    log_signal = Signal(str, str)
    finished_signal = Signal(bool, str)

    def __init__(self, target_func, *args, cancel_event=None, **kwargs):
        super().__init__()
        self.target_func = target_func
        self.args = args
        self.kwargs = kwargs
        self.cancel_event = cancel_event or threading.Event()

    def run(self):
        try:
            def _log(msg, level="cyan", *a, **k):
                self.log_signal.emit(str(msg), str(level))

            def _progress(pct, text="", *a, **k):
                try:
                    pct_val = float(pct)
                    val = int(round(pct_val * 1000)) if pct_val <= 1.0 else int(round(pct_val * 10))
                    val = max(0, min(1000, val))
                    status_text = format_progress_status(text, a)
                    self.progress_signal.emit(val, status_text)
                except Exception:
                    pass

            def _cancel_check(*a, **k):
                return self.cancel_event.is_set()

            # Adapt callback argument names to target function signature
            sig = None
            try:
                sig = inspect.signature(self.target_func)
            except Exception:
                pass

            call_kwargs = dict(self.kwargs)
            if sig:
                params = sig.parameters
                has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
                if "log_func" in params or has_varkw:
                    call_kwargs["log_func"] = _log
                if "progress_func" in params or has_varkw:
                    call_kwargs["progress_func"] = _progress
                if "progress_callback" in params and "progress_func" not in params:
                    call_kwargs["progress_callback"] = _progress
                if "cancel_check" in params or has_varkw:
                    call_kwargs["cancel_check"] = _cancel_check
            else:
                call_kwargs.setdefault("log_func", _log)
                call_kwargs.setdefault("progress_func", _progress)
                call_kwargs.setdefault("cancel_check", _cancel_check)

            success = self.target_func(*self.args, **call_kwargs)
            if self.cancel_event.is_set():
                self.finished_signal.emit(False, t("logs.cancelled_by_user", "Operation cancelled by user."))
            else:
                self.finished_signal.emit(bool(success), "" if success else t("logs.payload_failed", "Payload execution failed."))
        except Exception as e:
            log_exception(e, f"PayloadWorker running {getattr(self.target_func, '__name__', 'unknown')}")
            self.finished_signal.emit(False, str(e))


class PayloadController(QObject):
    """
    Manages the lifecycle of payload execution worker threads.
    Coordinates busy state, cancellation, and signal bridging to the MVI store.
    """
    progress_changed = Signal(int, str)
    operation_finished = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.store = get_store()
        self.current_worker = None
        self.cancel_event = threading.Event()

    @property
    def is_busy(self) -> bool:
        return self.store.state.is_busy

    def execute_payload(self, target_func, *args, on_success=None, on_error=None, **kwargs):
        """Starts a background worker thread to execute target_func safely."""
        if self.is_busy:
            return False

        self.cancel_event.clear()
        self.store.dispatch(SetBusyIntent(True, t("app.preparing_payload", "Preparing payload...")))

        self.current_worker = PayloadWorker(target_func, *args, cancel_event=self.cancel_event, **kwargs)
        self.current_worker.progress_signal.connect(self._on_progress)
        self.current_worker.log_signal.connect(self._on_log)

        def _handle_finished(success, err_msg):
            self.store.dispatch(SetBusyIntent(False))
            self.operation_finished.emit(success, err_msg)
            if success and on_success:
                on_success()
            elif not success and on_error:
                on_error(err_msg)
            self.current_worker = None

        self.current_worker.finished_signal.connect(_handle_finished)
        self.current_worker.start()
        return True

    def cancel_operation(self):
        """Signals current worker to abort immediately."""
        if self.current_worker and self.is_busy:
            self.cancel_event.set()
            self.store.dispatch(LogTerminalIntent(t("app.cancelling", "Cancelling operation, hang on..."), "warn"))

    def _on_progress(self, val: int, text: str):
        self.progress_changed.emit(val, text)

    def _on_log(self, msg: str, level: str):
        self.store.dispatch(LogTerminalIntent(msg, level))
