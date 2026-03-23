"""plotter_events.py — Lightweight publish/subscribe event bus for Refraction."""

import collections
import logging
import threading

_log = logging.getLogger(__name__)

# Canonical event name constants
FILE_LOADED            = "file_loaded"
FILE_VALIDATED         = "file_validated"
SHEET_CHANGED          = "sheet_changed"
CHART_TYPE_CHANGED     = "chart_type_changed"
PLOT_STARTED           = "plot_started"
PLOT_FINISHED          = "plot_finished"
PLOT_FAILED            = "plot_failed"
SETTINGS_CHANGED       = "settings_changed"
COMPARISON_CHANGED     = "comparison_changed"
EXPORT_REQUESTED       = "export_requested"
CANVAS_BAR_CLICKED     = "canvas_bar_clicked"
SESSION_SAVING         = "session_saving"
SESSION_LOADED         = "session_loaded"


class EventBus:
    """Thread-safe publish/subscribe event bus."""

    def __init__(self):
        self._lock = threading.Lock()
        # {event: sorted list of (priority, id, handler)}
        self._handlers = collections.defaultdict(list)
        self._next_id = 0

    def on(self, event: str, handler, priority: int = 0):
        """Subscribe handler to event. Returns an unsubscribe function."""
        with self._lock:
            hid = self._next_id
            self._next_id += 1
            self._handlers[event].append((priority, hid, handler))
            self._handlers[event].sort(key=lambda x: (-x[0], x[1]))

        def unsubscribe():
            with self._lock:
                self._handlers[event] = [
                    h for h in self._handlers[event] if h[1] != hid
                ]

        return unsubscribe

    def emit(self, event: str, **kwargs) -> None:
        """Fire all handlers for event synchronously, catching exceptions."""
        with self._lock:
            handlers = list(self._handlers.get(event, []))
        for priority, hid, handler in handlers:
            try:
                handler(**kwargs)
            except Exception:
                _log.debug("EventBus handler raised an exception (event=%r, handler=%r)",
                           event, handler, exc_info=True)

    def once(self, event: str, handler, priority: int = 0):
        """Subscribe handler to fire once, then auto-unsubscribe."""
        unsub = None

        def wrapper(**kwargs):
            if unsub is not None:
                unsub()
            handler(**kwargs)

        unsub = self.on(event, wrapper, priority=priority)
        return unsub

    def clear(self, event: str = None) -> None:
        """Remove all handlers for event, or all events if None."""
        with self._lock:
            if event is None:
                self._handlers.clear()
            else:
                self._handlers.pop(event, None)
