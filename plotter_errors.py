"""plotter_errors.py — Centralized error handling and logging for Spectra."""

import logging
import logging.handlers
import os
import threading
import traceback

LOG_PATH = os.path.expanduser("~/Library/Logs/spectra.log")

# Set up logging
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
_logger = logging.getLogger("spectra")
_logger.setLevel(logging.DEBUG)

if not _logger.handlers:
    try:
        _handler = logging.handlers.RotatingFileHandler(
            LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"
        )
    except Exception:
        _handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    _logger.addHandler(_handler)


def log_info(msg: str) -> None:
    _logger.info(msg)


def log_warning(msg: str) -> None:
    _logger.warning(msg)


def log_error(msg: str, exc: Exception = None) -> None:
    if exc is not None:
        tb = traceback.format_exc()
        _logger.error("%s\n%s", msg, tb)
    else:
        _logger.error(msg)


class ErrorReporter:
    """Show error dialogs from any thread and log everything."""

    def __init__(self, root_tk=None):
        self._root = root_tk

    def set_root(self, root_tk) -> None:
        self._root = root_tk

    def report(self, title: str, message: str, exc: Exception = None,
               level: str = "error") -> None:
        """Show messagebox (thread-safe) and log the error."""
        log_error(f"{title}: {message}", exc=exc)
        self._show_dialog(title, message, level)

    def _show_dialog(self, title: str, message: str, level: str) -> None:
        if self._root is None:
            return
        try:
            from tkinter import messagebox
        except ImportError:
            return

        def show():
            try:
                if level == "warning":
                    messagebox.showwarning(title, message)
                elif level == "info":
                    messagebox.showinfo(title, message)
                else:
                    messagebox.showerror(title, message)
            except Exception:
                pass

        if threading.current_thread() is threading.main_thread():
            show()
        else:
            try:
                self._root.after(0, show)
            except Exception:
                pass

    def wrap_thread(self, fn, error_title: str = "Background Error"):
        """Return a wrapper that catches exceptions and calls report()."""
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                self.report(error_title, str(e), exc=e)
        return wrapper


# Module-level singleton
reporter = ErrorReporter()
