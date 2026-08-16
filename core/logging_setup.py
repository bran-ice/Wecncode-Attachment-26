"""Console + file logging, configured once per process."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from core.config import PROJECT_ROOT

_configured = False

_FORMAT = "%(asctime)s %(levelname)-7s %(name)-22s %(message)s"


def setup_logging(level: str = "INFO", log_dir: Path | None = None) -> None:
    global _configured
    if _configured:
        return

    log_dir = log_dir or (PROJECT_ROOT / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # Windows consoles default to cp1252, which mangles (or raises on) the
    # non-ASCII text that manuals are full of.
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(logging.Formatter(_FORMAT, datefmt="%H:%M:%S"))
    root.addHandler(console)

    file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
