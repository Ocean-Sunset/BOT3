from __future__ import annotations

import os
import logging
import time
import json
import asyncio
from typing import Optional, List

logger = logging.getLogger(__name__)

_url = None
_token = None
_SETTINGS_CACHE = {}
_SETTINGS_CACHE_TTL = 30.0


class Record:
    """Dict-like wrapper for DB rows, mimicking asyncpg Record access."""
    __slots__ = ("_columns", "_values")

    def __init__(self, columns: list, values: tuple):
        self._columns = columns
        self._values = values

    def __getitem__(self, key):
        try:
            idx = self._columns.index(key)
            return self._values[idx]
        except (ValueError, IndexError):
            raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        return key in self._columns

    def __iter__(self):
        return zip(self._columns, self._values)

    def keys(self):
        return self._columns

    def values(self):
        return self._values

    def items(self):
        return zip(self._columns, self._values)

    def __len__(self):
        return len(self._columns)

    def __repr__(self):
        return f"Record({dict(self)})"


def _to_http_url(url: str) -> str:
    """Convert libsql:// or ws:// URLs to https:// for the HTTP API, appending /v2/pipeline."""
    if url.startswith("libsql://"):
        base = "https://" + url[len("libsql://"):]
    elif url.startswith("ws://"):
        base = "http://" + url[len("ws://"):]
    elif url.startswith("wss://"):
        base = "https://" + url[len("wss://"):]
    else:
        base = url
    base = base.rstrip("/")
    if not base.endswith("/v2/pipeline"):
        base += "/v2/pipeline"
    return base


def _wrap_arg(value) -> dict:
    """Wrap a Python value as a Turso pipeline arg."""
    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, int):
        return {"type": "integer", "value": value}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    return {"type": "text", "value": str(value)}


def _unwrap_cell(cell) -> str:
    """Extract a plain Python value from a Turso pipeline cell {type, value}."""
    if isinstance(cell, dict):
        return cell.get("value", "")
    return cell


def _rows_to_records(result: dict) -> List[Record]:
    """Convert a Turso pipeline result object to a list of Record objects."""
    cols = [c["name"] for c in result.get("cols", [])]
    rows = []
    for row in result.get("rows", []):
        rows.append(Record(cols, tuple(_unwrap_cell(c) for c in row)))
    return rows


async def _execute_http(sql: str, args=()) -> dict:
    """Execute a single SQL statement via Turso pipeline API."""
    import httpx
    global _url, _token
    if not _url:
        raise RuntimeError("TURSO_DATABASE_URL not set")
    headers = {"Content-Type": "application/json"}
    if _token:
        headers["Authorization"] = f"Bearer {_token}"
    body = {
        "requests": [
            {"type": "execute", "stmt": {"sql": sql, "args": [_wrap_arg(a) for a in (args or [])]}},
            {"type": "close"},
        ]
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(_url, json=body, headers=headers)
        data = resp.json()
        if resp.status_code >= 400:
            raise RuntimeError(f"Turso HTTP {resp.status_code}: {data}")
        results = data.get("results", [])
        if not results:
            return {}
        first = results[0]
        if first.get("type") == "error":
            raise RuntimeError(f"Turso pipeline error: {first.get('error', {})}")
        return first.get("response", {}).get("result", {})


async def _execute_batch_http(statements: list) -> list:
    """Execute multiple SQL statements in one Turso pipeline request."""
    import httpx
    global _url, _token
    if not _url:
        raise RuntimeError("TURSO_DATABASE_URL not set")
    headers = {"Content-Type": "application/json"}
    if _token:
        headers["Authorization"] = f"Bearer {_token}"
    requests = []
    for sql, args in statements:
        requests.append({"type": "execute", "stmt": {"sql": sql, "args": [_wrap_arg(a) for a in (args or [])]}})
    requests.append({"type": "close"})
    body = {"requests": requests}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(_url, json=body, headers=headers)
        data = resp.json()
        if resp.status_code >= 400:
            raise RuntimeError(f"Turso HTTP {resp.status_code}: {data}")
        results = data.get("results", [])
        out = []
        for r in results:
            if r.get("type") == "error":
                raise RuntimeError(f"Turso pipeline error: {r.get('error', {})}")
            out.append(r.get("response", {}).get("result", {}))
        return out


async def get_conn():
    """Initialize connection settings (lazy, once per process)."""
    global _url, _token
    if _url is not None:
        return True
    raw = os.environ.get("TURSO_DATABASE_URL") or os.environ.get("DATABASE_URL")
    _url = _to_http_url(raw) if raw else None
    _token = os.environ.get("TURSO_AUTH_TOKEN")
    if not _url:
        logger.warning("TURSO_DATABASE_URL not set")
        return None
    return True


class _ConnWrapper:
    """Async wrapper matching the interface callers expect."""

    async def fetchrow(self, sql: str, *args) -> Optional[Record]:
        result = await _execute_http(sql, args)
        records = _rows_to_records(result)
        return records[0] if records else None

    async def fetch(self, sql: str, *args) -> List[Record]:
        result = await _execute_http(sql, args)
        return _rows_to_records(result)

    async def execute(self, sql: str, *args) -> str:
        await _execute_http(sql, args)
        return "OK"


async def get_pool():
    """Get a connection wrapper (mimics asyncpg pool interface for callers)."""
    ok = await get_conn()
    if not ok:
        return None
    return _ConnWrapper()


def _parse_settings(raw, defaults: dict) -> dict:
    """Parse JSON or TEXT settings field."""
    if not raw:
        return dict(defaults)
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return dict(defaults)
    return dict(defaults)


def _get_cache_key(table: str, guild_id) -> tuple:
    return (table, str(guild_id))


def _get_cached_settings(table: str, guild_id, defaults: dict) -> Optional[dict]:
    key = _get_cache_key(table, guild_id)
    entry = _SETTINGS_CACHE.get(key)
    if entry and time.time() - entry["ts"] < _SETTINGS_CACHE_TTL:
        return dict(entry["value"])
    return None


async def fetchrow_cached(table: str, sql: str, guild_id, defaults: dict):
    """Fetch a settings row with built-in cache (only for settings queries)."""
    cached = _get_cached_settings(table, guild_id, defaults)
    if cached is not None:
        return cached

    ok = await get_conn()
    if not ok:
        return dict(defaults)

    try:
        result = await _execute_http(sql, (str(guild_id),))
        records = _rows_to_records(result)
        row = records[0] if records else None
        if row and row.get("settings"):
            value = _parse_settings(row["settings"], defaults)
            key = _get_cache_key(table, guild_id)
            _SETTINGS_CACHE[key] = {"value": value, "ts": time.time()}
            return value
        return dict(defaults)
    except Exception as e:
        logger.debug(f"fetchrow_cached failed for {table}/{guild_id}: {e}")
        return dict(defaults)


def _update_cache(table: str, guild_id, value: dict):
    """Update the cache after a settings save."""
    key = _get_cache_key(table, guild_id)
    _SETTINGS_CACHE[key] = {"value": dict(value), "ts": time.time()}


async def query(sql: str, *args):
    ok = await get_conn()
    if not ok:
        return []
    try:
        result = await _execute_http(sql, args)
        return _rows_to_records(result)
    except Exception as e:
        logger.debug(f"query failed: {e}")
        return []


async def fetchrow(sql: str, *args):
    ok = await get_conn()
    if not ok:
        return None
    try:
        result = await _execute_http(sql, args)
        records = _rows_to_records(result)
        return records[0] if records else None
    except Exception as e:
        logger.debug(f"fetchrow failed: {e}")
        return None


async def fetchval(sql: str, *args):
    ok = await get_conn()
    if not ok:
        return None
    try:
        records = await query(sql, *args)
        if records:
            return records[0][0] if len(records[0]) > 0 else None
        return None
    except Exception as e:
        logger.debug(f"fetchval failed: {e}")
        return None


async def execute(sql: str, *args):
    ok = await get_conn()
    if not ok:
        return None
    try:
        await _execute_http(sql, args)
        return "OK"
    except Exception as e:
        logger.debug(f"execute failed: {e}")
        return None
