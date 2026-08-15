"""
Direct HTTP bridge for the dashboard.

Lets the website send moderation quick-actions straight to the bot process,
bypassing the ~5s DB queue poll. Requests are authorized with a shared secret
token (BOT_HTTP_TOKEN) that lives only in the bot's and the website's server
environments - never in browser JS.

Endpoints:
  GET  /health            -> {"ok": true, "bot": ..., "guilds": N}
  POST /api/action        -> execute a moderation quick-action immediately
  GET  /api/stats/actions -> last 24h hourly dashboard-action counts (in-memory)

Set BOT_HTTP_TOKEN in cli/.env and the website env. Port defaults to 24612
(BOT_HTTP_PORT). The website must be able to reach http://<host>:<port>.
"""

import os
import time
import hmac
import hashlib
import logging

from aiohttp import web

logger = logging.getLogger(__name__)

BRIDGE_BUILD = 3

# Kept for diagnostics so /health can report the registered routes.
_APP = None


def _source_sha():
    try:
        with open(__file__, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:12]
    except Exception:
        return "unknown"

_bot = None

# Actions that may be executed directly. Everything else keeps using the queue.
DIRECT_ACTIONS = ("mute", "unmute", "kick", "ban", "add_role", "remove_role", "nickname")

# In-memory per-hour dashboard action counters. The status page polls these via
# /api/stats/actions so it can render a "bot actions" graph. Not persisted on
# purpose - it's a live view since the last bot restart.
_ACTION_BUCKETS = {}
_ACTION_BUCKET_HOURS = 48


def set_bot(bot):
    global _bot
    _bot = bot


def record_action():
    """Count one dashboard action executed by the bot (in-memory, hourly)."""
    bucket = int(time.time() // 3600) * 3600
    _ACTION_BUCKETS[bucket] = _ACTION_BUCKETS.get(bucket, 0) + 1
    cutoff = bucket - _ACTION_BUCKET_HOURS * 3600
    for k in [k for k in _ACTION_BUCKETS if k < cutoff]:
        del _ACTION_BUCKETS[k]


def action_stats():
    """Last 24 hourly buckets, zero-filled: [{"t": ts, "count": n}, ...]."""
    start = int(time.time() // 3600) * 3600 - 23 * 3600
    return [
        {"t": start + i * 3600, "count": _ACTION_BUCKETS.get(start + i * 3600, 0)}
        for i in range(24)
    ]


def _get_token():
    return os.environ.get("BOT_HTTP_TOKEN", "")


async def _check_auth(request) -> bool:
    token = _get_token()
    if not token:
        return False
    supplied = request.headers.get("X-Prowl-Token", "")
    return hmac.compare_digest(token, supplied)


async def handle_health(request):
    if not await _check_auth(request):
        return web.json_response({"ok": False, "error": "unauthorized"}, status=401)
    routes = sorted({r.resource.canonical for r in _APP.router.routes()}) if _APP else []
    return web.json_response({
        "ok": True,
        "build": BRIDGE_BUILD,
        "sha": _source_sha(),
        "routes": routes,
        "bot": _bot.user.name if _bot and _bot.user else None,
        "guilds": len(_bot.guilds) if _bot else 0,
        "ready": bool(_bot and _bot.is_ready()),
    })


async def handle_action(request):
    if not await _check_auth(request):
        return web.json_response({"ok": False, "error": "unauthorized"}, status=401)
    if _bot is None or not _bot.is_ready():
        return web.json_response({"ok": False, "error": "bot not ready"}, status=503)
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid json"}, status=400)

    action = body.get("action")
    guild_id = str(body.get("guild_id", ""))
    user_id = body.get("user_id")
    if action not in DIRECT_ACTIONS or not guild_id or not user_id:
        return web.json_response({"ok": False, "error": "invalid action, guild_id or user_id"}, status=400)

    guild = _bot.get_guild(int(guild_id)) if guild_id.isdigit() else None
    if guild is None:
        return web.json_response({"ok": False, "error": "bot not in guild"}, status=404)

    ok, message = await _bot.execute_action(
        guild_id,
        action,
        user_id,
        target_name=str(body.get("target") or body.get("user_name") or ""),
        reason=str(body.get("reason") or "No reason provided"),
        duration=body.get("duration"),
        moderator=str(body.get("moderator") or "Dashboard"),
    )
    return web.json_response({"ok": ok, "message": message}, status=200 if ok else 400)


async def handle_action_stats(request):
    if not await _check_auth(request):
        return web.json_response({"ok": False, "error": "unauthorized"}, status=401)
    return web.json_response({"actions": action_stats()})


async def start_http_server():
    """Start the aiohttp bridge. No-op (with a warning) if BOT_HTTP_TOKEN unset."""
    token = _get_token()
    if not token:
        logger.warning("BOT_HTTP_TOKEN not set - direct dashboard HTTP bridge disabled.")
        return
    app = web.Application()
    app.router.add_get("/health", handle_health)
    app.router.add_post("/api/action", handle_action)
    app.router.add_get("/api/stats/actions", handle_action_stats)
    global _APP
    _APP = app
    port = int(os.environ.get("BOT_HTTP_PORT", "24612"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logger.info(f"HTTP bridge listening on 0.0.0.0:{port}.")
