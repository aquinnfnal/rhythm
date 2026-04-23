import sys
import os
import datetime
import threading
import traceback

class RhythmLogger:
    """
    Minimal thread-safe logger using only Python core libraries.
    Methods: info(msg), debug(msg), error(msg[, exc_info=False])
    Configurable log level: DEBUG (10), INFO (20), ERROR (30)
    """

    # Level constants
    DEBUG = 10
    INFO = 20
    WARNING = 25
    ERROR = 30

    # ANSI escape sequences (will be disabled automatically if not a TTY)
    ANSI = {
        "reset": "\x1b[0m",
        "bold": "\x1b[1m",
        "red": "\x1b[31m",
        "green": "\x1b[32m",
        "cyan": "\x1b[36m",
        "yellow": "\x1b[33m",
    }

    def __init__(self, name="rhythm", level=INFO, stream=None, use_color=None):
        """
        name: optional logger name to include in output
        level: one of DEBUG/INFO/ERROR
        stream: output stream (defaults to sys.stderr)
        use_color: True/False to force color on/off; if None auto-detects
        """
        self.name = name or "root"
        self.level = level
        self.stream = stream or sys.stderr
        self._lock = threading.Lock()

        if use_color is None:
            # Auto-detect: only use colors when stream is a TTY and NO_COLOR not set
            self.use_color = getattr(self.stream, "isatty", lambda: False)() and ("NO_COLOR" not in os.environ)
        else:
            self.use_color = bool(use_color)

        if not self.use_color:
            # blank out ANSI codes
            for k in list(self.ANSI.keys()):
                self.ANSI[k] = ""

    def _timestamp(self):
        # ISO-like compact timestamp including milliseconds
        return datetime.datetime.now().strftime("<%H:%M:%S>")

    def _format(self, level_name, msg, color_code, extra=""):
        ts = self._timestamp()
        name_part = f"{self.name} " if self.name else ""
        level_tag = f"{level_name}"
        # Example: 2025-12-12 10:05:01.123 [INFO] root: message
        formatted = f"{ts} [{level_tag}] {name_part}: {msg}"
        if extra:
            formatted += f"\n{extra}"
        if self.use_color:
            # bold level tag, colored
            return f"{self.ANSI['bold']}{self.ANSI[color_code]}{formatted}{self.ANSI['reset']}"
        return formatted

    def set_level(self, level):
        self.level = int(level)

    def debug(self, msg, *args, **kwargs):
        """Log a debug message (visible when level <= DEBUG)."""
        if self.level > self.DEBUG:
            return
        if args or kwargs:
            try:
                msg = msg.format(*args, **kwargs)
            except Exception:
                # fall back to simple concatenation if format fails
                msg = f"{msg} {args} {kwargs}"
        line = self._format("DEBUG", msg, "cyan")
        with self._lock:
            print(line, file=self.stream)

    def info(self, msg, *args, **kwargs):
        """Log an info message (visible when level <= INFO)."""
        if self.level > self.INFO:
            return
        if args or kwargs:
            try:
                msg = msg.format(*args, **kwargs)
            except Exception:
                msg = f"{msg} {args} {kwargs}"
        line = self._format("INFO", msg, "green")
        with self._lock:
            print(line, file=self.stream)

    def warning(self, msg, *args, **kwargs):
        """Log an info message (visible when level <= INFO)."""
        if self.level > self.INFO:
            return
        if args or kwargs:
            try:
                msg = msg.format(*args, **kwargs)
            except Exception:
                msg = f"{msg} {args} {kwargs}"
        line = self._format("WARNING", msg, "yellow")
        with self._lock:
            print(line, file=self.stream)

    def error(self, msg, *args, exc_info=False, **kwargs):
        """
        Log an error message. If exc_info=True, append a stack trace of the current exception.
        """
        if args or kwargs:
            try:
                msg = msg.format(*args, **kwargs)
            except Exception:
                msg = f"{msg} {args} {kwargs}"

        extra = ""
        if exc_info:
            # capture the current exception stack
            extra = traceback.format_exc()

        # use red and bold for errors; include stack trace if present
        line = self._format("ERROR", msg, "red", extra=extra)
        with self._lock:
            print(line, file=self.stream)
