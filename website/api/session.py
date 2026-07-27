"""
Server-side session store with rotating secret keys.
Cookie holds a random session ID, actual data lives in memory.
Secret key rotates every 30 seconds; old keys stay valid for 5 minutes.
"""

import time
import secrets
import logging
from collections import OrderedDict
from typing import Optional

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

logger = logging.getLogger(__name__)

KEY_ROTATION = 30
GRACE_PERIOD = 300
SESSION_TTL = 86400

_session_store = OrderedDict()
_key_ring = []
_last_rotation = 0


def _get_current_key() -> str:
    global _last_rotation
    now = time.time()
    if now - _last_rotation >= KEY_ROTATION or not _key_ring:
        new_key = secrets.token_hex(32)
        _key_ring.append({"key": new_key, "since": now})
        _last_rotation = now
        cutoff = now - GRACE_PERIOD
        _key_ring[:] = [k for k in _key_ring if k["since"] > cutoff]
        if not _key_ring:
            _key_ring.append({"key": secrets.token_hex(32), "since": now})
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


def create_session() -> str:
    while True:
        sid = secrets.token_hex(32)
        if sid not in _session_store:
            break
    _session_store[sid] = {"data": {}, "expires": time.time() + SESSION_TTL}
    _trim_store()
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


def delete_session(sid: str):
    _session_store.pop(sid, None)


def _trim_store():
    now = time.time()
    expired = [k for k, v in _session_store.items() if v["expires"] < now]
    for k in expired:
        del _session_store[k]
    while len(_session_store) > 10000:
        _session_store.popitem(last=False)
