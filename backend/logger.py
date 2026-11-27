"""Structured PII-redacted pipeline telemetry & live log ring buffer for NammaKural."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

from backend.state import scrub_pii_and_aadhaar

ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_FILE = LOG_DIR / "nammakural.jsonl"

_LOCK = threading.Lock()
_RING: deque[dict[str, Any]] = deque(maxlen=150)

_PY_LOGGER = logging.getLogger("nammakural")
if not _PY_LOGGER.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S"))
    _PY_LOGGER.addHandler(_handler)
    _PY_LOGGER.setLevel(logging.INFO)


def _scrub_value(val: Any) -> Any:
    if isinstance(val, str):
        return scrub_pii_and_aadhaar(val)["clean_text"]
    if isinstance(val, dict):
        return {str(k): _scrub_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_scrub_value(v) for v in val]
    return val


def log_event(
    stage: str,
    message: str = "",
    data: dict[str, Any] | None = None,
    level: str = "INFO",
    source: str = "backend",
) -> dict[str, Any]:
    """Emit a PII-scrubbed structured log entry to stdout, memory ring, and JSONL file."""
    safe_msg = scrub_pii_and_aadhaar(message)["clean_text"] if message else ""
    safe_data = _scrub_value(data or {})
    entry = {
        "ts": round(time.time(), 3),
        "time": time.strftime("%H:%M:%S"),
        "source": source,
        "level": level.upper(),
        "stage": stage,
        "message": safe_msg,
        "data": safe_data,
    }
    with _LOCK:
        _RING.append(entry)
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with LOG_FILE.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    line = f"[{source}] {stage}: {safe_msg}" + (f" | {json.dumps(safe_data, ensure_ascii=False)}" if safe_data else "")
    if level.upper() == "ERROR":
        _PY_LOGGER.error(line)
    elif level.upper() == "WARN":
        _PY_LOGGER.warning(line)
    else:
        _PY_LOGGER.info(line)
    return entry


def get_logs(limit: int = 80) -> list[dict[str, Any]]:
    """Return latest structured logs (oldest-to-newest up to `limit`)."""
    with _LOCK:
        items = list(_RING)
    return items[-max(1, min(limit, 150)) :]


def clear_logs() -> None:
    """Clear in-memory ring buffer cleanly."""
    with _LOCK:
        _RING.clear()
