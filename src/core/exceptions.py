"""
exceptions.py — Global Exception Handling, Crash Logging, and Custom Domain Exceptions.
Captures all uncaught exceptions across main and background threads into logs/crash.log.
"""
import sys
import os
import traceback
import time
import threading

# Base log path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
CRASH_LOG_PATH = os.path.join(LOGS_DIR, "crash.log")
APP_LOG_PATH = os.path.join(LOGS_DIR, "session.log")


class AeroSuiteError(Exception):
    """Base exception for all Aero Suite domain errors."""
    pass


class UsbError(AeroSuiteError):
    """Raised when USB detection, validation, or formatting fails."""
    pass


class PayloadError(AeroSuiteError):
    """Raised when payload preparation or script generation fails."""
    pass


class ApkEngineError(AeroSuiteError):
    """Raised when APK parsing, patching, or extraction fails."""
    pass


def log_to_file(file_path: str, message: str):
    """Thread-safe append to a log file with directory creation."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        t_stamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        with open(file_path, "a", encoding="utf-8", errors="replace") as f:
            f.write(f"{t_stamp} {message}\n")
    except Exception:
        pass


def log_exception(exc: BaseException, context: str = ""):
    """Logs an exception with traceback to both console, session log, and crash.log."""
    t_stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    header = f"=== CRASH / UNHANDLED EXCEPTION [{t_stamp}] ==="
    if context:
        header += f"\nContext: {context}"
    msg = f"{header}\n{tb_str}\n{'=' * 60}\n"

    try:
        sys.stderr.write(msg)
        sys.stderr.flush()
    except Exception:
        pass

    log_to_file(CRASH_LOG_PATH, msg)
    log_to_file(APP_LOG_PATH, f"ERROR: {exc} | Context: {context}")


def global_excepthook(exc_type, exc_value, exc_traceback):
    """Catches uncaught exceptions on the main thread."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    log_exception(exc_value, context="Main Thread Uncaught Exception")


def global_thread_excepthook(args):
    """Catches uncaught exceptions inside worker threads (Python 3.8+)."""
    log_exception(args.exc_value, context=f"Thread: {args.thread.name if args.thread else 'Unknown'}")


def setup_global_exception_handler():
    """Activates global main-thread and worker-thread crash capture."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    sys.excepthook = global_excepthook
    if hasattr(threading, "excepthook"):
        threading.excepthook = global_thread_excepthook
    log_to_file(APP_LOG_PATH, "Aero Suite Global Exception Handler & Crash Logger initialized.")
