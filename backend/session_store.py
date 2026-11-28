"""Durable Redis-compatible session, OTP, cooldown & turn-idempotency store with zero-key memory fallback."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any


def _load_local_env() -> None:
    """Populate os.environ from project .env without overriding already-set platform env vars."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            key = k.strip()
            val = v.strip().strip('"').strip("'")
            if key and val:
                os.environ.setdefault(key, val)
    except OSError:
        pass


_load_local_env()


class SessionStore:
    """Atomic key-value & turn-dedup store backed by Redis when REDIS_URL is set, else thread-safe TTL memory."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._mem: dict[str, tuple[str, float]] = {}
        self._redis = None
        if os.getenv("PYTEST_CURRENT_TEST") and os.getenv("NK_TEST_REDIS") != "1":
            return
        redis_url = os.getenv("REDIS_URL", "").strip()
        if redis_url:
            try:
                import redis

                client = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=1.5)
                client.ping()
                self._redis = client
            except Exception:
                self._redis = None

    @property
    def backend_name(self) -> str:
        return "redis" if self._redis is not None else "memory-ttl"

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [k for k, (_, exp) in self._mem.items() if exp and exp < now]
        for k in expired:
            del self._mem[k]

    def get_json(self, key: str) -> dict[str, Any] | None:
        if self._redis is not None:
            try:
                raw = self._redis.get(key)
                return json.loads(raw) if raw else None
            except Exception:
                pass
        with self._lock:
            self._purge_expired()
            entry = self._mem.get(key)
            if not entry:
                return None
            return json.loads(entry[0])

    def set_json(self, key: str, value: dict[str, Any], ttl_sec: int = 3600) -> None:
        payload = json.dumps(value, ensure_ascii=False)
        if self._redis is not None:
            try:
                self._redis.set(key, payload, ex=ttl_sec)
                return
            except Exception:
                pass
        with self._lock:
            self._purge_expired()
            self._mem[key] = (payload, time.time() + ttl_sec if ttl_sec > 0 else 0.0)

    def consume_once(self, key: str, ttl_sec: int = 3600) -> bool:
        """Atomically mark a turn_id / confirmation token as consumed; returns False if already used."""
        if self._redis is not None:
            try:
                return bool(self._redis.set(key, "1", nx=True, ex=ttl_sec))
            except Exception:
                pass
        with self._lock:
            self._purge_expired()
            if key in self._mem:
                return False
            self._mem[key] = ("1", time.time() + ttl_sec if ttl_sec > 0 else 0.0)
            return True

    def delete(self, key: str) -> None:
        if self._redis is not None:
            self._redis.delete(key)
        with self._lock:
            self._mem.pop(key, None)


STORE = SessionStore()

_DEFAULT_SECRET = uuid.uuid4().hex


def _signing_secret() -> bytes:
    return (os.getenv("SESSION_SIGNING_SECRET", "").strip() or _DEFAULT_SECRET).encode("utf-8")


def sign_session_token(payload: dict[str, Any]) -> str:
    """Create a compact HMAC-SHA256 signed token for stateless Vercel cold-start continuity."""
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    import base64

    b64 = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    sig = hmac.new(_signing_secret(), b64.encode("ascii"), hashlib.sha256).hexdigest()[:24]
    return f"{b64}.{sig}"


def verify_session_token(token: str) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    b64, sig = token.rsplit(".", 1)
    expected = hmac.new(_signing_secret(), b64.encode("ascii"), hashlib.sha256).hexdigest()[:24]
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        import base64

        padded = b64 + "=" * (-len(b64) % 4)
        parsed = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None
