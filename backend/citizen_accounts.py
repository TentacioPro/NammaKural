"""Mobile OTP sessions and citizen-owned local request history."""

from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from typing import Literal
from uuid import UUID, uuid4, uuid5

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.session_store import STORE


router = APIRouter(prefix="/api")
COOKIE = "nk_citizen"
TTL = 8 * 60 * 60
HISTORY_DB = Path(__file__).resolve().parents[1] / "logs" / "citizen_history.sqlite3"
OPERATOR_PATHS = ("/api/debug", "/api/telemetry/runs", "/api/telemetry/summary",
                  "/api/conversations", "/api/logs", "/api/telemetry")


def provider_config() -> tuple[str, str]:
    url = os.getenv("NK_SUPABASE_URL", "").rstrip("/")
    key = os.getenv("NK_SUPABASE_PUBLIC_KEY", "")
    if not re.fullmatch(r"https://[a-z0-9-]+\.supabase\.co", url) or not key:
        return "", ""
    return url, key


def auth_required() -> bool:
    return os.getenv("NK_AUTH_REQUIRED") == "1" or bool(os.getenv("VERCEL") or provider_config()[0])


def current_citizen(request: Request) -> str | None:
    if "nk.citizen" in request.scope:
        return request.scope["nk.citizen"]
    try:
        token = str(UUID(request.cookies.get(COOKIE, "")))
    except ValueError:
        return None
    account = STORE.get_json(f"citizen-login:{token}") or {}
    request.scope["nk.citizen"] = account.get("citizen")
    return request.scope["nk.citizen"]


def operator_allowed(request: Request) -> bool:
    if not auth_required():
        return True
    operators = set(os.getenv("NK_OPERATOR_IDS", "").replace(",", " ").split())
    citizen = current_citizen(request)
    return bool(citizen and citizen in operators)


def scoped_session(request: Request, session_id: str | None) -> str | None:
    citizen = current_citizen(request) if auth_required() else None
    return str(uuid5(UUID(citizen), session_id)) if citizen and session_id else session_id


def _must_be_signed_in(request: Request) -> str:
    citizen = current_citizen(request)
    if not citizen:
        raise HTTPException(401, "Sign in to access your request history.")
    return citizen


class Mobile(BaseModel):
    phone: str = Field(pattern=r"^\+91[6-9][0-9]{9}$")


class Verification(Mobile):
    code: str = Field(pattern=r"^[0-9]{6}$")


async def _auth_post(action: Literal["otp", "verify"], body: dict) -> dict:
    url, key = provider_config()
    if not url:
        raise HTTPException(503, "Mobile sign-in is unavailable until the SMS provider is configured.")
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.post(f"{url}/auth/v1/{action}", headers={"apikey": key}, json=body)
    except httpx.HTTPError:
        raise HTTPException(503, "Could not reach the sign-in provider.") from None
    if response.status_code == 429:
        raise HTTPException(429, "Too many attempts. Try again in a minute.")
    if response.status_code >= 500:
        raise HTTPException(503, "Sign-in is temporarily unavailable.")
    if not response.is_success:
        raise HTTPException(400, "Could not send the code." if action == "otp" else "Code is invalid or expired.")
    return response.json()


@router.get("/auth/status")
def sign_in_status(request: Request) -> JSONResponse:
    return JSONResponse({
        "required": auth_required(), "configured": bool(provider_config()[0]),
        "signed_in": bool(current_citizen(request)), "operator": operator_allowed(request),
    }, headers={"Cache-Control": "no-store"})


@router.post("/auth/send")
async def send_code(body: Mobile, request: Request) -> dict:
    if not provider_config()[0]:
        raise HTTPException(503, "Mobile sign-in is unavailable until the SMS provider is configured.")
    host = request.client.host if request.client else "unknown"
    if not STORE.consume_once(f"citizen-otp-ip:{host}", ttl_sec=10):
        raise HTTPException(429, "Please wait before requesting another code.")
    await _auth_post("otp", {"phone": body.phone, "channel": "sms", "create_user": True})
    return {"sent": True}


@router.post("/auth/verify")
async def verify_code(body: Verification, request: Request) -> JSONResponse:
    host = request.client.host if request.client else "unknown"
    if not STORE.consume_once(f"citizen-verify-ip:{host}", ttl_sec=2):
        raise HTTPException(429, "Please wait before checking another code.")
    payload = await _auth_post("verify", {"phone": body.phone, "token": body.code, "type": "sms"})
    try:
        citizen = str(UUID(payload["user"]["id"]))
        if payload["user"]["phone"].lstrip("+") != body.phone[1:] or not payload["access_token"]:
            raise ValueError
    except (KeyError, TypeError, ValueError, AttributeError):
        raise HTTPException(502, "The provider did not return a verified mobile account.") from None
    prior = request.cookies.get(COOKIE)
    if prior and re.fullmatch(r"[a-f0-9-]{36}", prior):
        STORE.delete(f"citizen-login:{prior}")
        STORE.delete(f"otp:{prior}")
    token = str(uuid4())
    STORE.set_json(f"citizen-login:{token}", {"citizen": citizen}, ttl_sec=TTL)
    STORE.set_json(f"otp:{token}", {"verified": True, "identity": "mobile_otp"}, ttl_sec=TTL)
    response = JSONResponse({"signed_in": True}, headers={"Cache-Control": "no-store"})
    response.set_cookie(COOKIE, token, max_age=TTL, httponly=True, samesite="lax",
                        secure=request.url.scheme == "https" or bool(os.getenv("VERCEL")))
    return response


@router.post("/auth/signout")
def sign_out(request: Request) -> JSONResponse:
    token = request.cookies.get(COOKIE, "")
    if re.fullmatch(r"[a-f0-9-]{36}", token):
        STORE.delete(f"citizen-login:{token}")
        STORE.delete(f"otp:{token}")
    response = JSONResponse({"signed_in": False})
    response.delete_cookie(COOKIE)
    return response


def _history_db() -> sqlite3.Connection:
    HISTORY_DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(HISTORY_DB, timeout=5)
    db.execute("""CREATE TABLE IF NOT EXISTS requests (
        citizen TEXT NOT NULL, id TEXT NOT NULL, updated INTEGER NOT NULL, title TEXT NOT NULL,
        destination TEXT NOT NULL, details TEXT NOT NULL, filing_reference TEXT,
        PRIMARY KEY(citizen, id)
    )""")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS request_reference ON requests(citizen, destination, filing_reference)")
    return db


@router.get("/requests")
def request_history(request: Request) -> JSONResponse:
    citizen = _must_be_signed_in(request)
    with closing(_history_db()) as db:
        rows = db.execute(
            "SELECT id, updated, title, destination, details, filing_reference FROM requests "
            "WHERE citizen = ? ORDER BY updated DESC, id LIMIT 100", (citizen,),
        ).fetchall()
        saved, reported = db.execute(
            "SELECT COUNT(*), COUNT(filing_reference) FROM requests WHERE citizen = ?", (citizen,),
        ).fetchone()
    items = [{"id": row[0], "updated": row[1], "title": row[2], "destination": row[3],
              "draft": json.loads(row[4]), "filing_reference": row[5]} for row in rows]
    return JSONResponse({"saved": saved, "reported_filed": reported, "items": items},
                        headers={"Cache-Control": "no-store"})


class SavedRequest(BaseModel):
    session_id: UUID


@router.post("/requests")
def save_draft(body: SavedRequest, request: Request) -> dict:
    from backend.agent_workflow import get_grievance_draft

    citizen = _must_be_signed_in(request)
    draft_id = scoped_session(request, str(body.session_id))
    draft = get_grievance_draft(draft_id)
    if not draft:
        raise HTTPException(404, "There is no current grievance draft to save.")
    with closing(_history_db()) as db, db:
        result = db.execute(
            "INSERT INTO requests VALUES (?, ?, ?, ?, ?, ?, NULL) "
            "ON CONFLICT(citizen,id) DO UPDATE SET updated=excluded.updated,title=excluded.title,"
            "destination=excluded.destination,details=excluded.details WHERE requests.filing_reference IS NULL",
            (citizen, draft_id, int(time.time()), draft["label"], draft["destination"]["name"],
             json.dumps(draft, ensure_ascii=False)),
        )
        if not result.rowcount:
            raise HTTPException(409, "This request has a recorded filing reference. Start a new grievance to save changes.")
    return {"saved": True}


class FilingReference(BaseModel):
    reference: str = Field(pattern=r"(?i)^[a-z0-9][a-z0-9/-]{3,49}$")


@router.post("/requests/{draft_id}/filing-reference")
def save_filing_reference(draft_id: UUID, body: FilingReference, request: Request) -> dict:
    from backend.state import scrub_pii_and_aadhaar

    citizen = _must_be_signed_in(request)
    reference = body.reference.upper()
    if scrub_pii_and_aadhaar(reference)["pii_masked"]:
        raise HTTPException(422, "Enter the complaint reference, without a phone or identity number.")
    try:
        with closing(_history_db()) as db, db:
            updated = db.execute("UPDATE requests SET filing_reference = ?, updated = ? WHERE citizen = ? AND id = ?",
                                 (reference, int(time.time()), citizen, str(draft_id))).rowcount
    except sqlite3.IntegrityError:
        raise HTTPException(409, "This reference is already recorded for that channel.") from None
    if not updated:
        raise HTTPException(404, "Request not found.")
    return {"status": "reported_by_citizen"}
