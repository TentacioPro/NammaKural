"""Structured PII-redacted pipeline telemetry, OTLP-compatible traces & persistent conversation logs."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

from backend.state import scrub_pii_and_aadhaar
from backend.telemetry import AGENT_VERSION, TELEMETRY_SCHEMA_VERSION, emit_otlp_span

ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_FILE = LOG_DIR / "nammakural.jsonl"
CONV_FILE = LOG_DIR / "conversations.jsonl"

_LOCK = threading.Lock()
_RING: deque[dict[str, Any]] = deque(maxlen=500)
_CONVS: deque[dict[str, Any]] = deque(maxlen=200)

_PY_LOGGER = logging.getLogger("nammakural")
if not _PY_LOGGER.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S"))
    _PY_LOGGER.addHandler(_handler)
    _PY_LOGGER.setLevel(logging.INFO)


def _hydrate_from_disk() -> None:
    """Load persisted logs and past conversation turns across restarts."""
    if LOG_FILE.is_file():
        try:
            lines = LOG_FILE.read_text(encoding="utf-8").splitlines()[-150:]
            for ln in lines:
                if ln.strip():
                    _RING.append(json.loads(ln))
        except Exception:
            pass
    if CONV_FILE.is_file():
        try:
            lines = CONV_FILE.read_text(encoding="utf-8").splitlines()[-200:]
            for ln in lines:
                if ln.strip():
                    _CONVS.append(json.loads(ln))
        except Exception:
            pass


_hydrate_from_disk()


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
        "agent_version": AGENT_VERSION,
        "schema_version": TELEMETRY_SCHEMA_VERSION,
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
    if stage in {"workflow.turn_complete", "llm.fast_turn", "tts.sarvam_bulbul", "tts.neural_synth", "client.ttfa"}:
        dur = float(safe_data.get("latency_ms", 0.0)) if isinstance(safe_data.get("latency_ms"), (int, float)) else 0.0
        emit_otlp_span(stage, {"level": level.upper(), "source": source, **safe_data}, duration_ms=dur, status_ok=level.upper() != "ERROR")
    return entry


def save_conversation_turn(
    session_id: str,
    role: str,
    text: str,
    fsm_state: str = "",
    ward: str = "",
    persona: str = "Neerja",
) -> dict[str, Any]:
    """Persist PII-redacted conversation history entries to logs/conversations.jsonl."""
    clean = scrub_pii_and_aadhaar(text)["clean_text"]
    item = {
        "ts": round(time.time(), 3),
        "time": time.strftime("%H:%M:%S"),
        "session_id": session_id[:20],
        "role": role,
        "persona": persona,
        "fsm_state": fsm_state,
        "ward": ward,
        "text": clean,
    }
    with _LOCK:
        _CONVS.append(item)
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with CONV_FILE.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")
        except OSError:
            pass
    return item


def get_logs(limit: int = 80) -> list[dict[str, Any]]:
    """Return latest structured logs (oldest-to-newest up to `limit`)."""
    with _LOCK:
        items = list(_RING)
    return items[-max(1, min(limit, 150)) :]


def get_conversations(limit: int = 60) -> list[dict[str, Any]]:
    """Return latest PII-redacted persisted conversation messages."""
    with _LOCK:
        items = list(_CONVS)
    return items[-max(1, min(limit, 200)) :]


def clear_logs() -> None:
    """Clear in-memory ring buffer cleanly."""
    with _LOCK:
        _RING.clear()


def observability_status() -> dict[str, Any]:
    """Report active tracing sinks (built-in JSONL + optional Arize Phoenix / Opik / OTLP)."""
    return {
        "local_jsonl": str(LOG_FILE.name),
        "past_conversations_file": str(CONV_FILE.name),
        "otel_endpoint": os.getenv("PHOENIX_COLLECTOR_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "not set (built-in trace ring active)",
    }
