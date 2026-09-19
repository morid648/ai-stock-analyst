"""Process-wide environment setup helpers."""

import os
import sys


def configure_utf8() -> None:
    """Forces UTF-8 stdout/stderr, avoiding mojibake on Windows consoles."""
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
