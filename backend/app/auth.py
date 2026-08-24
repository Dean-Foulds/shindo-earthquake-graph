"""
Account signup / login and per-user request quotas.

Users live in SQLite rather than Neo4j on purpose: authentication must keep
working when the seismic graph is unavailable, and it has no relationship to
the graph data model.
"""

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .i18n import DEFAULT, lang_of, msg

router = APIRouter(prefix="/auth")

DB_PATH        = os.getenv("SHINDO_AUTH_DB", "shindo_auth.db")
TOKEN_TTL_DAYS = int(os.getenv("AUTH_TOKEN_TTL_DAYS", "30"))
REQUEST_QUOTA  = int(os.getenv("USER_REQUEST_QUOTA", "50"))
EMAIL_RE       = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# scrypt parameters — memory-hard, stdlib, no external password library.
_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 32}


def _secret() -> str:
    """JWT signing key. Refuses to fall back to a default in production."""
    key = os.getenv("AUTH_SECRET")
    if not key:
        raise RuntimeError(
            "AUTH_SECRET is not set — generate one with "
            "`python -c 'import secrets; print(secrets.token_urlsafe(48))'`"
        )
    return key


# ── storage ───────────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                email          TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                password_hash  TEXT    NOT NULL,
                salt           TEXT    NOT NULL,
                created_at     TEXT    NOT NULL,
                request_count  INTEGER NOT NULL DEFAULT 0,
                input_tokens   INTEGER NOT NULL DEFAULT 0,
                output_tokens  INTEGER NOT NULL DEFAULT 0,
                quota_reset_at TEXT    NOT NULL
            )
        """)


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT).hex()


def _next_reset() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()


# ── tokens ────────────────────────────────────────────────────────────────────

def _issue_token(user_id: int, email: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub":   str(user_id),
            "email": email,
            "iat":   int(now.timestamp()),
            "exp":   int((now + timedelta(days=TOKEN_TTL_DAYS)).timestamp()),
        },
        _secret(),
        algorithm="HS256",
    )


_bearer = HTTPBearer(auto_error=False)


def current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> sqlite3.Row:
    """Resolve the bearer token to a user row, or 401."""
    lang = lang_of(request)
    if creds is None:
        raise HTTPException(401, msg(lang, "auth.signin_required"))
    try:
        payload = jwt.decode(creds.credentials, _secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, msg(lang, "auth.session_expired"))
    except jwt.InvalidTokenError:
        raise HTTPException(401, msg(lang, "auth.invalid_session"))

    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (payload["sub"],)
        ).fetchone()
    if row is None:
        raise HTTPException(401, msg(lang, "auth.account_gone"))
    return row


def check_quota(user: sqlite3.Row, lang: str = DEFAULT) -> None:
    """Raise 429 when the user has spent their allowance for this window."""
    if datetime.fromisoformat(user["quota_reset_at"]) <= datetime.now(timezone.utc):
        with _connect() as conn:
            conn.execute(
                "UPDATE users SET request_count = 0, quota_reset_at = ? WHERE id = ?",
                (_next_reset(), user["id"]),
            )
        return
    if user["request_count"] >= REQUEST_QUOTA:
        raise HTTPException(
            429,
            msg(lang, "auth.quota_reached",
                quota=REQUEST_QUOTA, resets=user["quota_reset_at"][:10]),
        )


def record_usage(user_id: int, input_tokens: int, output_tokens: int) -> None:
    with _connect() as conn:
        conn.execute(
            """UPDATE users
                  SET request_count = request_count + 1,
                      input_tokens  = input_tokens  + ?,
                      output_tokens = output_tokens + ?
                WHERE id = ?""",
            (input_tokens, output_tokens, user_id),
        )


# ── request / response models ─────────────────────────────────────────────────

class Credentials(BaseModel):
    email:    str
    password: str = Field(min_length=10, max_length=200)


class Session(BaseModel):
    token: str
    email: str
    quota: dict


def _quota_of(row: sqlite3.Row) -> dict:
    return {
        "used":     row["request_count"],
        "limit":    REQUEST_QUOTA,
        "resets":   row["quota_reset_at"],
        "tokens_in":  row["input_tokens"],
        "tokens_out": row["output_tokens"],
    }


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=Session)
def signup(body: Credentials, request: Request):
    if not EMAIL_RE.match(body.email):
        raise HTTPException(400, msg(lang_of(request), "auth.invalid_email"))

    salt = secrets.token_bytes(16)
    now  = datetime.now(timezone.utc).isoformat()
    try:
        with _connect() as conn:
            cur = conn.execute(
                """INSERT INTO users
                       (email, password_hash, salt, created_at, quota_reset_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (body.email, _hash_password(body.password, salt), salt.hex(),
                 now, _next_reset()),
            )
            user_id = cur.lastrowid
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(409, msg(lang_of(request), "auth.email_taken"))

    return Session(token=_issue_token(user_id, body.email),
                   email=body.email, quota=_quota_of(row))


@router.post("/login", response_model=Session)
def login(body: Credentials, request: Request):
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (body.email,)
        ).fetchone()

    # Hash even when the account is missing, so a wrong email and a wrong
    # password take the same time and can't be told apart.
    salt     = bytes.fromhex(row["salt"]) if row else secrets.token_bytes(16)
    expected = row["password_hash"] if row else _hash_password("", salt)
    ok = hmac.compare_digest(_hash_password(body.password, salt), expected)

    if row is None or not ok:
        raise HTTPException(401, msg(lang_of(request), "auth.bad_credentials"))

    return Session(token=_issue_token(row["id"], row["email"]),
                   email=row["email"], quota=_quota_of(row))


@router.get("/me")
def me(user: sqlite3.Row = Depends(current_user)):
    return {"email": user["email"], "quota": _quota_of(user)}
