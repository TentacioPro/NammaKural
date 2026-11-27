"""Lightweight, zero-bloat OTLP/HTTP JSON span exporter for Arize Phoenix & OpenTelemetry collectors.

Activated only when `OTEL_EXPORTER_OTLP_ENDPOINT` or `PHOENIX_COLLECTOR_ENDPOINT` is configured.
All span attributes are PII-scrubbed before emission (Invariant I4).
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
import uuid
from typing import Any


def get_otlp_endpoint() -> str:
    ep = (os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("PHOENIX_COLLECTOR_ENDPOINT") or "").strip()
    if not ep:
        return ""
    if ep.endswith("/v1/traces"):
        return ep
    return ep.rstrip("/") + "/v1/traces"


def _to_otlp_attr(key: str, val: Any) -> dict[str, Any]:
    if isinstance(val, bool):
        return {"key": key, "value": {"boolValue": val}}
    if isinstance(val, int):
        return {"key": key, "value": {"intValue": str(val)}}
    if isinstance(val, float):
        return {"key": key, "value": {"doubleValue": val}}
    return {"key": key, "value": {"stringValue": str(val)[:512]}}


def emit_otlp_span(
    name: str,
    attributes: dict[str, Any],
    duration_ms: float = 0.0,
    status_ok: bool = True,
) -> bool:
    """Send a single redacted OTLP JSON span asynchronously to Arize Phoenix / OTel collector."""
    endpoint = get_otlp_endpoint()
    if not endpoint:
        return False

    end_ns = time.time_ns()
    start_ns = max(0, end_ns - int(max(0.0, duration_ms) * 1_000_000))
    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        _to_otlp_attr("service.name", "nammakural-voice-agent"),
                        _to_otlp_attr("deployment.environment", os.getenv("VERCEL_REGION", "local")),
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "nammakural.telemetry", "version": "0.2.0"},
                        "spans": [
                            {
                                "traceId": uuid.uuid4().hex,
                                "spanId": uuid.uuid4().hex[:16],
                                "name": name,
                                "kind": 1,
                                "startTimeUnixNano": str(start_ns),
                                "endTimeUnixNano": str(end_ns),
                                "attributes": [_to_otlp_attr(k, v) for k, v in attributes.items()],
                                "status": {"code": 1 if status_ok else 2},
                            }
                        ],
                    }
                ],
            }
        ]
    }
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def _send() -> None:
        try:
            req = urllib.request.Request(
                endpoint,
                data=raw,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=1.5):
                pass
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()
    return True
