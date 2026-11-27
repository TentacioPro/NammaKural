"""Vercel Python ASGI entrypoint exposing NammaKural FastAPI app."""

from backend.main import app

__all__ = ["app"]
