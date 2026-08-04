"""
Server-side session store with rotating secret keys.
Cookie holds a random session ID; data lives in memory + Neon DB (shared across
serverless instances) with a /tmp file fallback for non-DB environments.
Secret key rotates every 30 seconds; old keys stay valid for 5 minutes.
"""

import os
import json
import time
import secrets
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Optional

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

logger = logging.getLogger(__name__)

KEY_ROTATION = 30
GRACE_PERIOD = 300
SESSION_TTL = 86400

# /tmp is the only writable dir on Vercel; fall back to project dir elsewhere.
try:
    _SESSION_FILE = Path("/tmp/.sessions.json")
    if not os.access("/tmp", os.W_OK):
        raise OSError
except (OSError, TypeError):
    _SESSION_FILE = Path(__file__).resolve().parent.parent / ".sessions.json"
_SAVE_INTERVAL = 10

_session_store = OrderedDict()
_key_ring = []
_last_rotation = 0
_last_save = 0

_SESSIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    sid     TEXT PRIMARY KEY,
    data    JSONB NOT NULL DEFAULT '{}',
    expires DOUBLE PRECISION NOT NULL
);
"""


_fallback_key = None


def _get_current_key() -> str:
    """Return a STABLE signing key.

    Uses the SECRET_KEY env var so every serverless instance can verify each
    other's cookies. Falls back to a per-process random key (single-instance dev).
    """
    global _fallback_key, _key_ring
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        if not _key_ring or _key_ring[-1]["key"] != env_key:
            _key_ring = [{"key": env_key, "since": 0}]
        return env_key
    # No env key (local dev without SECRET_KEY): stable per-process key.
    if not _key_ring:
        if _fallback_key is None:
            _fallback_key = secrets.token_hex(32)
        _key_ring = [{"key": _fallback_key, "since": 0}]
    return _key_ring[-1]["key"]


def _make_serializer(key: str):
    return URLSafeTimedSerializer(key, salt="prowl-session")


def sign_session_id(sid: str) -> str:
    return _make_serializer(_get_current_key()).dumps(sid)


def unsign_session_id(cookie: str) -> Optional[str]:
    for entry in reversed(_key_ring):
        try:
            return _make_serializer(entry["key"]).loads(cookie, max_age=SESSION_TTL)
        except (BadSignature, SignatureExpired):
            continue
    return None


# ── Signed-cookie sessions (data embedded in the cookie itself) ──
# Serverless-safe: no shared store needed; survives any instance / cold start.

def sign_session_data(data: dict) -> str:
    return _make_serializer(_get_current_key()).dumps(data or {})


def unsign_session_data(cookie: str) -> Optional[dict]:
    for entry in reversed(_key_ring):
        try:
            data = _make_serializer(entry["key"]).loads(cookie, max_age=SESSION_TTL)
            if isinstance(data, dict):
                return data
        except (BadSignature, SignatureExpired):
            continue
    return None


# ── File fallback (only used when DB is unavailable) ──

def _save_file():
    global _last_save
    now = time.time()
    if now - _last_save < _SAVE_INTERVAL:
        return
    _last_save = now
    try:
        _SESSION_FILE.write_text(
            json.dumps({k: v for k, v in _session_store.items()}, default=str),
            encoding="utf-8",
        )
    except Exception:
        pass


def _load_file():
    global _session_store
    try:
        if _SESSION_FILE.exists():
            raw = json.loads(_SESSION_FILE.read_text(encoding="utf-8"))
            now = time.time()
            store = OrderedDict()
            for sid, entry in raw.items():
                if entry.get("expires", 0) > now:
                    store[sid] = {"data": entry.get("data", {}), "expires": entry["expires"]}
            _session_store = store
    except Exception:
        pass


# ── Neon DB persistence (shared across serverless instances) ──

async def _db_get(sid: str):
    try:
        from api import db
        pool = await db.get_pool()
        if not pool:
            return None
        row = await pool.fetchrow(
            "SELECT data, expires FROM sessions WHERE sid = $1", sid
        )
        if not row:
            return None
        return row
    except Exception:
        return None


async def _db_save(sid: str, data: dict, expires: float):
    try:
        from api import db
        pool = await db.get_pool()
        if not pool:
            return
        try:
            await pool.execute(_SESSIONS_TABLE_SQL)
        except Exception:
            pass
        await pool.execute(
            "INSERT INTO sessions (sid, data, expires) VALUES ($1, $2::jsonb, $3) "
            "ON CONFLICT (sid) DO UPDATE SET data = $2::jsonb, expires = $3",
            sid, json.dumps(data), expires,
        )
    except Exception:
        pass


async def _db_delete(sid: str):
    try:
        from api import db
        pool = await db.get_pool()
        if not pool:
            return
        await pool.execute("DELETE FROM sessions WHERE sid = $1", sid)
    except Exception:
        pass


# ── Public async API (used by middleware) ──

async def create_session_async() -> str:
    while True:
        sid = secrets.token_hex(32)
        if sid not in _session_store:
            break
    expires = time.time() + SESSION_TTL
    _session_store[sid] = {"data": {}, "expires": expires}
    _trim_memory()
    await _db_save(sid, {}, expires)
    _save_file()
    return sid


async def get_session_async(sid: str) -> Optional[dict]:
    entry = _session_store.get(sid)
    if entry:
        if time.time() < entry["expires"]:
            return entry["data"]
        del _session_store[sid]
    # Not in memory — try DB (shared across instances / cold starts)
    row = await _db_get(sid)
    if row:
        if time.time() < row["expires"]:
            data = row["data"]
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    data = {}
            _session_store[sid] = {"data": data, "expires": row["expires"]}
            return data
    return None


async def save_session_async(sid: str, data: dict):
    expires = time.time() + SESSION_TTL
    _session_store[sid] = {"data": data, "expires": expires}
    await _db_save(sid, data, expires)
    _save_file()


async def delete_session_async(sid: str):
    _session_store.pop(sid, None)
    await _db_delete(sid)
    _save_file()


# ── Sync wrappers (kept for any non-async callers) ──

def create_session() -> str:
    while True:
        sid = secrets.token_hex(32)
        if sid not in _session_store:
            break
    expires = time.time() + SESSION_TTL
    _session_store[sid] = {"data": {}, "expires": expires}
    _trim_memory()
    _save_file()
    return sid


def get_session(sid: str) -> Optional[dict]:
    entry = _session_store.get(sid)
    if entry and time.time() < entry["expires"]:
        return entry["data"]
    if entry:
        del _session_store[sid]
    return None


def save_session(sid: str, data: dict):
    _session_store[sid] = {"data": data, "expires": time.time() + SESSION_TTL}
    _save_file()


def delete_session(sid: str):
    _session_store.pop(sid, None)
    _save_file()


def _trim_memory():
    now = time.time()
    expired = [k for k, v in _session_store.items() if v["expires"] < now]
    for k in expired:
        del _session_store[k]
    while len(_session_store) > 10000:
        _session_store.popitem(last=False)


_load_file()
