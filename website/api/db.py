from __future__ import annotations

import os
import logging
import time
import json
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)
_pool: Optional[asyncpg.Pool] = None
_SETTINGS_CACHE = {}
_SETTINGS_CACHE_TTL = 30.0


def _parse_settings(raw, defaults: dict) -> dict:
    """Parse JSONB or TEXT settings field."""
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


async def get_pool() -> Optional[asyncpg.Pool]:
    global _pool
    if _pool is not None:
        return _pool
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        logger.warning("DATABASE_URL not set")
        return None
    try:
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        return _pool
    except Exception as e:
        logger.error(f"Failed to create pool: {e}")
        return None


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
    
    pool = await get_pool()
    if pool is None:
        return dict(defaults)
    
    try:
        row = await pool.fetchrow(sql, str(guild_id))
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
    pool = await get_pool()
    if pool is None:
        return []
    return await pool.fetch(sql, *args)


async def fetchrow(sql: str, *args):
    pool = await get_pool()
    if pool is None:
        return None
    return await pool.fetchrow(sql, *args)


async def fetchval(sql: str, *args):
    pool = await get_pool()
    if pool is None:
        return None
    return await pool.fetchval(sql, *args)


async def execute(sql: str, *args):
    pool = await get_pool()
    if pool is None:
        return None
    return await pool.execute(sql, *args)
