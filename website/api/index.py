import os
import json
import time
import secrets
import logging
import urllib.parse
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from api import session as rotating_session
import httpx

from api.db import get_pool, query, fetchrow, fetchval, execute

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Config
# ---------------------------------------------------------------------------

DISCORD_API = "https://discord.com/api/v10"
CLIENT_ID = os.environ.get("CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("REDIRECT_URI", "http://localhost:8000/callback")
OAUTH_SCOPES = "identify guilds"
MANAGE_SERVER = 0x20

ROOT = Path(__file__).parent.parent

_missing = []
if not CLIENT_ID:
    _missing.append("CLIENT_ID")
if not CLIENT_SECRET:
    _missing.append("CLIENT_SECRET")
if not REDIRECT_URI or REDIRECT_URI.startswith("http://localhost"):
    _missing.append("REDIRECT_URI (should be production URL)")
if not os.environ.get("DATABASE_URL"):
    _missing.append("DATABASE_URL")
if not os.environ.get("SECRET_KEY"):
    _missing.append("SECRET_KEY")
if _missing:
    logger.warning("Missing/invalid environment variables: %s", ", ".join(_missing))


def _cfg():
    """Return only safe, template-needed env vars."""
    return {"CLIENT_ID": os.environ.get("CLIENT_ID", "")}


def _parse_guild_data(row):
    """Safely extract guild data dict from a DB row (handles TEXT vs JSONB)."""
    if not row:
        return None
    d = row["data"]
    if isinstance(d, str):
        try:
            d = json.loads(d)
        except (json.JSONDecodeError, TypeError):
            return None
    return d if isinstance(d, dict) else None


# ---------------------------------------------------------------------------
#  App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await get_pool()
    except Exception as e:
        logger.error("Failed to initialize database pool: %s", e)
    yield

app = FastAPI(title="Prowl", version="1.0.0", lifespan=lifespan)


class RotatingSessionMiddleware:
    """
    ASGI middleware that replaces Starlette's SessionMiddleware with
    server-side sessions and 30-second key rotation with 5-minute grace.
    """

    def __init__(self, app):
        self.app = app
        self._initial_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
        # Prime the key ring
        rotating_session._get_current_key()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from starlette.datastructures import MutableHeaders
        from starlette.requests import HTTPConnection

        conn = HTTPConnection(scope)
        cookie_val = conn.cookies.get("session")
        sid = None
        if cookie_val:
            sid = rotating_session.unsign_session_id(cookie_val)

        is_new = False
        if not sid:
            sid = rotating_session.create_session()
            is_new = True

        session_data = rotating_session.get_session(sid)
        if session_data is None:
            session_data = {}
            rotating_session.save_session(sid, session_data)

        scope["session"] = session_data

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                # Save session data back
                if scope.get("session") is not None:
                    rotating_session.save_session(sid, scope["session"])
                # Set cookie on new sessions or re-set on each response to refresh expiry
                signed = rotating_session.sign_session_id(sid)
                headers["Set-Cookie"] = (
                    f"session={signed}; Path=/; HttpOnly; SameSite=lax; Max-Age={86400}"
                )
            await send(message)

        await self.app(scope, receive, send_wrapper)


app.add_middleware(RotatingSessionMiddleware)

templates = Jinja2Templates(directory=str(ROOT / "templates"))
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


# ---------------------------------------------------------------------------
#  Error handlers
# ---------------------------------------------------------------------------

ERROR_PAGES = {
    400: ("Bad Request", "The request could not be understood."),
    403: ("Forbidden", "You don't have permission to access this."),
    404: ("Page Not Found", "The page you're looking for doesn't exist."),
    405: ("Method Not Allowed", "This method is not allowed here."),
    429: ("Too Many Requests", "Slow down there, partner."),
    500: ("Internal Server Error", "Something went wrong on our end."),
    502: ("Bad Gateway", "The upstream server is not responding."),
    503: ("Service Unavailable", "The service is temporarily unavailable."),
    504: ("Gateway Timeout", "The upstream server took too long to respond."),
}


@app.exception_handler(404)
async def not_found(request, exc):
    return templates.TemplateResponse(
        request, "error.html",
        {"code": 404, "title": ERROR_PAGES[404][0], "message": ERROR_PAGES[404][1]},
        status_code=404,
    )


@app.exception_handler(500)
async def server_error(request, exc):
    return templates.TemplateResponse(
        request, "error.html",
        {"code": 500, "title": ERROR_PAGES[500][0], "message": ERROR_PAGES[500][1]},
        status_code=500,
    )


@app.exception_handler(403)
async def forbidden(request, exc):
    return templates.TemplateResponse(
        request, "error.html",
        {"code": 403, "title": ERROR_PAGES[403][0], "message": ERROR_PAGES[403][1]},
        status_code=403,
    )


@app.exception_handler(429)
async def too_many(request, exc):
    return templates.TemplateResponse(
        request, "error.html",
        {"code": 429, "title": ERROR_PAGES[429][0], "message": ERROR_PAGES[429][1]},
        status_code=429,
    )


# ---------------------------------------------------------------------------
#  Favicon
# ---------------------------------------------------------------------------


@app.get("/favicon.ico")
async def favicon_ico():
    return FileResponse(ROOT / "static" / "favicon.ico")


@app.get("/favicon.png")
async def favicon_png():
    return FileResponse(ROOT / "static" / "favicon.png")


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

async def discord_get(path: str, token: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{DISCORD_API}{path}", headers={"Authorization": f"Bearer {token}"})
        if r.status_code == 200:
            return r.json()
    return None


def get_user(request: Request):
    return request.session.get("user")


def get_token(request: Request):
    return request.session.get("token")


def get_selected_guild(request: Request):
    return request.session.get("selected_guild")


def _relative_time(ts: float) -> str:
    diff = time.time() - ts
    if diff < 60: return f"{int(diff)}s ago"
    if diff < 3600: return f"{int(diff // 60)}m ago"
    if diff < 86400: return f"{int(diff // 3600)}h ago"
    return f"{int(diff // 86400)}d ago"


async def get_bot_guild_ids():
    rows = await query("SELECT guild_id FROM guild_data")
    return {row["guild_id"] for row in rows}


CACHE_TTL = 120  # seconds


async def get_user_guilds_filtered(request: Request):
    token = get_token(request)
    if not token:
        return []

    now = time.time()
    cached = request.session.get("guild_cache")
    if cached and (now - cached.get("ts", 0)) < CACHE_TTL:
        return cached["guilds"]

    user_guilds = await discord_get("/users/@me/guilds", token)
    if not user_guilds:
        return []
    bot_ids = await get_bot_guild_ids()
    eligible = []
    for g in user_guilds:
        perms = int(g.get("permissions", 0))
        gid = str(g["id"])
        if (perms & MANAGE_SERVER) and gid in bot_ids:
            eligible.append(g)

    request.session["guild_cache"] = {"ts": now, "guilds": eligible}
    return eligible


# ---------------------------------------------------------------------------
#  Routes - Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_user(request)
    return templates.TemplateResponse(request, "index.html", {
        "config": _cfg(),
        "user": user,
    })


@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse(request, "login.html", {"config": _cfg()})


@app.get("/invite", response_class=HTMLResponse)
async def invite(request: Request):
    return templates.TemplateResponse(request, "invite.html", {"config": _cfg()})


@app.get("/auth/discord")
async def auth_discord():
    if not CLIENT_ID:
        return HTMLResponse("OAuth not configured.", status_code=500)
    params = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": OAUTH_SCOPES,
        "prompt": "consent",
    })
    return RedirectResponse(f"https://discord.com/api/oauth2/authorize?{params}")


@app.get("/login/google")
async def login_google():
    google_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    if not google_id:
        return HTMLResponse("Google OAuth not configured yet.", status_code=503)
    google_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/callback/google")
    params = urllib.parse.urlencode({
        "client_id": google_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    })
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@app.get("/callback")
async def callback(request: Request, code: str = None):
    if not code:
        return RedirectResponse("/dashboard")

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{DISCORD_API}/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=(CLIENT_ID, CLIENT_SECRET),
        )
    if r.status_code != 200:
        return RedirectResponse("/dashboard")

    token_json = r.json()
    access_token = token_json.get("access_token")
    if not access_token:
        return RedirectResponse("/dashboard")

    request.session["token"] = access_token
    user = await discord_get("/users/@me", access_token)
    if user:
        request.session["user"] = user

    return RedirectResponse("/dashboard")


@app.get("/callback/google")
async def callback_google():
    return RedirectResponse("/dashboard")


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@app.get("/dashboard")
async def dashboard_redirect(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login")

    # Bust guild cache so the picker shows fresh data
    request.session.pop("guild_cache", None)

    guilds = await get_user_guilds_filtered(request)
    if not guilds:
        return templates.TemplateResponse(request, "servers.html", {
            "user": user, "guilds": [], "config": _cfg(),
        })

    selected = get_selected_guild(request)
    if not selected or str(selected.get("id")) not in {str(g["id"]) for g in guilds}:
        return templates.TemplateResponse(request, "servers.html", {
            "user": user, "guilds": guilds, "config": _cfg(),
        })

    return RedirectResponse(f"/guild/{selected['id']}/overview")


@app.get("/servers")
async def servers_page(request: Request):
    """Always shows the server picker, never auto-redirects."""
    user = get_user(request)
    if not user:
        return RedirectResponse("/login")

    request.session.pop("guild_cache", None)
    guilds = await get_user_guilds_filtered(request)
    return templates.TemplateResponse(request, "servers.html", {
        "user": user, "guilds": guilds, "config": _cfg(),
    })


@app.post("/select_guild")
async def select_guild(
    request: Request,
    guild_id: str = Form(...),
    guild_name: str = Form(""),
    guild_icon: str = Form(""),
):
    request.session["selected_guild"] = {"id": guild_id, "name": guild_name, "icon": guild_icon}
    return RedirectResponse(f"/guild/{guild_id}/overview", status_code=303)


@app.get("/guild/{guild_id}/{panel}")
@app.get("/guild/{guild_id}/")
async def dashboard(request: Request, guild_id: str, panel: str = "overview"):
    user = get_user(request)
    if not user:
        return RedirectResponse("/dashboard")

    guilds = await get_user_guilds_filtered(request)
    guild_ids = {str(g["id"]) for g in guilds}
    if guild_id not in guild_ids:
        return RedirectResponse("/dashboard")

    guild_info = next((g for g in guilds if str(g["id"]) == guild_id), None)

    valid_panels = [
        "overview", "welcomer", "ai", "moderation", "members", "logs", "automod",
        "oauth2", "music", "leveling", "verification", "automation",
        "social_alerts", "invite_tracker", "tickets", "global_chat",
        "autoresponder", "settings",
    ]
    if panel not in valid_panels:
        panel = "overview"

    ctx = {
        "user": user,
        "guild": guild_info,
        "guild_id": guild_id,
        "active_panel": panel,
        "bot_data": {},
        "config": _cfg(),
    }

    return templates.TemplateResponse(request, f"dashboard/{panel}.html", ctx)


# ---------------------------------------------------------------------------
#  Routes - API v1
# ---------------------------------------------------------------------------

# Simple per-user rate limiter to mitigate API scraping
_RATE_LIMIT = {}
_RATE_WINDOW = 60
_RATE_MAX = 60  # requests per minute per user


def _check_rate_limit(user_id: str):
    now = time.time()
    entry = _RATE_LIMIT.get(user_id)
    if not entry or now - entry["start"] >= _RATE_WINDOW:
        _RATE_LIMIT[user_id] = {"start": now, "count": 1}
        return
    entry["count"] += 1
    if entry["count"] > _RATE_MAX:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a moment.")
    if len(_RATE_LIMIT) > 10000:
        _RATE_LIMIT.clear()


async def require_auth(request: Request):
    user = get_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    _check_rate_limit(str(user.get("id", "anon")))
    return user


async def require_guild_access(request: Request, guild_id: str):
    user = await require_auth(request)
    guilds = await get_user_guilds_filtered(request)
    if not any(str(g["id"]) == guild_id for g in guilds):
        raise HTTPException(status_code=403, detail="No access to this guild")
    return user


@app.get("/api/v1/health")
async def api_health():
    return {"status": "ok", "service": "prowl-api"}


@app.get("/api/v1/ping")
async def api_ping():
    return {"ping": "pong"}


@app.get("/api/v1/db-test")
async def api_db_test(request: Request):
    await require_auth(request)
    try:
        row = await fetchval("SELECT 1")
        return {"db": "connected", "result": row}
    except Exception as e:
        return {"db": "error", "detail": str(e)}


@app.get("/api/v1/@me")
async def api_me(request: Request):
    user = await require_auth(request)
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "discriminator": user.get("discriminator"),
        "avatar": user.get("avatar"),
    }


@app.get("/api/v1/status")
async def api_status(request: Request):
    await require_auth(request)
    rows = await query("SELECT key, value FROM bot_stats")
    data = {row["key"]: row["value"] for row in rows}

    def safe_int(key, default=0):
        try:
            return int(data.get(key, default))
        except (ValueError, TypeError):
            return default

    return {
        "status": "online" if data.get("bot_status") == "Running" else "offline",
        "guilds": safe_int("num_guilds"),
        "users": safe_int("total_users"),
        "active_users": safe_int("active_users"),
        "uptime": data.get("uptime", "N/A"),
        "memory_mb": data.get("memory_usage_mb", "N/A"),
        "cpu_percent": data.get("cpu_usage_percent", "N/A"),
        "version": data.get("bot_version", "unknown"),
        "python_version": data.get("python_version", "unknown"),
        "channels": safe_int("num_channels"),
        "roles": safe_int("num_roles"),
        "emojis": safe_int("num_emojis"),
    }


@app.get("/api/v1/guilds")
async def api_guilds(request: Request):
    await require_auth(request)
    rows = await query("SELECT data FROM guild_data ORDER BY updated_at DESC")
    guilds = []
    for row in rows:
        g = _parse_guild_data(row)
        if g is None:
            continue
        guilds.append({
            "id": g.get("id"),
            "name": g.get("name"),
            "icon_url": g.get("icon_url"),
            "member_count": g.get("member_count", 0),
            "online_count": g.get("online_count", 0),
        })
    return {"guilds": guilds}


@app.get("/api/v1/guild/{guild_id}")
async def api_guild(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    g = _parse_guild_data(row)
    if g is not None:
        return g
    return JSONResponse({"error": "Guild not found"}, status_code=404)


@app.get("/api/v1/commands")
async def api_commands(request: Request):
    await require_auth(request)
    row = await fetchrow("SELECT value FROM bot_stats WHERE key = 'all_commands'")
    commands = []
    try:
        commands = json.loads(row["value"]) if row else []
    except (json.JSONDecodeError, TypeError):
        pass

    row2 = await fetchrow("SELECT value FROM bot_stats WHERE key = 'loaded_cogs'")
    cogs = []
    try:
        cogs = json.loads(row2["value"]) if row2 else []
    except (json.JSONDecodeError, TypeError):
        pass

    return {"commands": commands, "cogs": cogs}


# ---------------------------------------------------------------------------
#  Moderation API v1
# ---------------------------------------------------------------------------

MOD_SETTINGS_DEFAULTS = {
    "dm_on_action": True, "require_reason": True, "silent_mod": False,
    "auto_thread": False, "track_stats": True,
    "cmd_ban": True, "cmd_kick": True, "cmd_timeout": True, "cmd_warn": True,
    # ── Modlog ──
    "modlog_channel_id": None,
    # ── Ban ──
    "ban_dm": True, "ban_purge": True, "ban_message": "{username} has been banned.", "ban_message_enabled": True,
    # ── Temp ban ──
    "tempban_dm": True, "tempban_purge": True,
    "tempban_message": "{username} has been temporarily banned.", "tempban_message_enabled": True,
    "tempban_duration": 1440,
    # ── Mute ──
    "mute_dm": True, "mute_duration": 60,
    # ── Kick ──
    "kick_dm": True, "kick_message": "{username} has been kicked.", "kick_message_enabled": True,
    # ── Warn ──
    "warn_dm": True, "warn_message": "{username} has been warned.", "warn_message_enabled": True,
}


async def _get_mod_settings(guild_id: str):
    row = await fetchrow("SELECT settings FROM mod_settings WHERE guild_id = $1", str(guild_id))
    if row:
        settings = row["settings"]
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except (json.JSONDecodeError, TypeError):
                return dict(MOD_SETTINGS_DEFAULTS)
        if isinstance(settings, dict):
            return {**MOD_SETTINGS_DEFAULTS, **settings}
    return dict(MOD_SETTINGS_DEFAULTS)


def _valid_snowflake(value) -> bool:
    """True if value is None or a numeric string/int (Discord ID)."""
    if value is None:
        return True
    s = str(value).strip()
    return s.isdigit() and len(s) <= 20


def _sanitize_extra_alerts(value):
    """Validate extra_alerts: dict of {platform: [{target, ping_role, message}]}, max 5/platform."""
    if not isinstance(value, dict):
        return None, "extra_alerts must be an object"
    clean = {}
    for platform, items in value.items():
        if platform not in ("youtube", "twitch", "twitter"):
            return None, f"invalid platform '{platform}'"
        if not isinstance(items, list):
            return None, f"'{platform}' alerts must be a list"
        if len(items) > 5:
            return None, f"'{platform}' exceeds max of 5 alerts"
        clean_items = []
        for it in items:
            if not isinstance(it, dict):
                return None, "each alert must be an object"
            target = str(it.get("target") or "").strip()
            if not target:
                return None, "alert target is required"
            ping_role = it.get("ping_role")
            if ping_role is not None and not _valid_snowflake(ping_role):
                return None, "invalid ping role id"
            message = it.get("message")
            if message is not None and not isinstance(message, str):
                return None, "message must be a string"
            clean_items.append({
                "target": target[:200],
                "ping_role": str(ping_role) if ping_role else None,
                "message": message[:500] if message else None,
            })
        clean[platform] = clean_items
    return clean, None


def _sanitize_setting(key: str, value, defaults: dict):
    """Coerce/validate a single settings key. Returns (clean_value, error)."""
    if key not in defaults:
        return value, f"unknown key '{key}'"
    default = defaults[key]

    # Discord ID fields (channel/role selectors) must be a snowflake or null
    id_key = (key.endswith("_ping_role") or key.endswith("_announce_channel_id")
              or key in ("modlog_channel_id", "default_announce_channel_id", "default_ping_role"))
    if id_key:
        if value is None or value == "":
            return None, None
        if not _valid_snowflake(value):
            return None, f"'{key}' must be a valid Discord ID or null"
        return str(value), None

    # Booleans
    if isinstance(default, bool):
        return bool(value), None
    # None-able free-text (handles, channel ids, messages)
    if default is None:
        if value is None or value == "":
            return None, None
        return str(value)[:500], None
    # Integers (durations)
    if isinstance(default, int):
        try:
            n = int(value)
        except (TypeError, ValueError):
            return None, f"'{key}' must be an integer"
        return n, None
    return str(value), None


async def _save_settings(table, guild_id, key, value, defaults):
    """Validate + persist a settings key with server-side checks."""
    clean, err = _sanitize_setting(key, value, defaults)
    if err:
        return err
    current = dict(defaults)
    row = await fetchrow(f"SELECT settings FROM {table} WHERE guild_id = $1", str(guild_id))
    if row:
        stored = row["settings"]
        if isinstance(stored, str):
            try:
                stored = json.loads(stored)
            except (json.JSONDecodeError, TypeError):
                stored = {}
        if isinstance(stored, dict):
            current.update(stored)
    current[key] = clean
    await execute(
        f"INSERT INTO {table} (guild_id, settings) VALUES ($1, $2::jsonb) "
        f"ON CONFLICT (guild_id) DO UPDATE SET settings = $2::jsonb",
        str(guild_id), json.dumps(current),
    )
    return None


@app.get("/api/v1/mod/{guild_id}/settings")
async def mod_settings(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    return {"settings": await _get_mod_settings(guild_id)}


@app.post("/api/v1/mod/{guild_id}/settings")
async def mod_settings_set(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    key = body.get("key")
    value = body.get("value")
    if not key:
        return JSONResponse({"error": "missing key"}, status_code=400)
    err = await _save_settings("mod_settings", str(guild_id), key, value, MOD_SETTINGS_DEFAULTS)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    return {"ok": True}


@app.get("/api/v1/mod/{guild_id}/feed")
async def mod_feed(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    scope = request.query_params.get("scope", "all")
    MOD_ONLY = ("kick", "ban", "unban", "tempban", "mute", "unmute", "warn", "purge", "lockdown")
    sql = "SELECT user_name, action, reason, moderator, created_at FROM mod_log WHERE guild_id = $1"
    params = [str(guild_id)]
    if scope == "mod":
        sql += " AND action = ANY($2::text[])"
        params.append(list(MOD_ONLY))
    sql += " ORDER BY created_at DESC LIMIT 20"
    rows = await query(sql, *params)
    if rows:
        # Build channel-name lookup for purge events that stored raw IDs
        ch_map = {}
        gd = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
        parsed = _parse_guild_data({"data": gd["data"]}) if gd else None
        if parsed and isinstance(parsed.get("channels"), list):
            for c in parsed["channels"]:
                ch_map[str(c.get("id"))] = c.get("name", "")
        return {"events": [{
            "user": (f"#{ch_map.get(r['user_name'], r['user_name'])}" if r["action"] == "purge" and r["user_name"].isdigit() else r["user_name"]),
            "action": r["action"],
            "reason": r.get("reason", ""),
            "moderator": r.get("moderator") or "",
            "time": _relative_time(r["created_at"]),
            "color": {"ban": "red", "kick": "red", "tempban": "red", "mute": "blue", "unmute": "green", "warn": "yellow", "unban": "green", "purge": "blue", "lockdown": "gray"}.get(r["action"], "gray"),
        } for r in rows]}
    return {"events": []}


@app.post("/api/v1/mod/{guild_id}/log")
async def mod_log_push(guild_id: str, request: Request):
    """Endpoint for the bot to push moderation events."""
    body = await request.json()
    await execute(
        "INSERT INTO mod_log (guild_id, user_id, user_name, action, reason, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
        str(guild_id), body.get("user_id", ""), body.get("user_name", ""),
        body.get("action", ""), body.get("reason", ""), time.time(),
    )
    return {"ok": True}


async def push_mod_event(guild_id, user_id, user_name, action, reason=""):
    """Insert a moderation event into mod_log."""
    await execute(
        "INSERT INTO mod_log (guild_id, user_id, user_name, action, reason, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
        str(guild_id), str(user_id), user_name, action, reason, time.time(),
    )


_MOD_ACTIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS mod_actions (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_name TEXT DEFAULT '',
    reason TEXT DEFAULT '',
    moderator TEXT DEFAULT '',
    error TEXT DEFAULT '',
    duration INTEGER,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now())),
    processed_at DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_mod_actions_pending ON mod_actions (status, created_at);
"""


async def _ensure_mod_actions_table():
    await execute(_MOD_ACTIONS_TABLE_SQL)


async def _queue_action(guild_id, action, target_id, target_name="", reason="", duration=None, moderator=""):
    try:
        duration_int = int(duration) if duration is not None and duration != "" else None
    except (ValueError, TypeError):
        duration_int = None
    try:
        await execute(
            "INSERT INTO mod_actions (guild_id, action, target_id, target_name, reason, moderator, duration, status, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending', $8)",
            str(guild_id), action, str(target_id), target_name, reason, moderator,
            duration_int, time.time(),
        )
    except Exception:
        await _ensure_mod_actions_table()
        await execute(
            "INSERT INTO mod_actions (guild_id, action, target_id, target_name, reason, moderator, duration, status, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending', $8)",
            str(guild_id), action, str(target_id), target_name, reason, moderator,
            duration_int, time.time(),
        )
    # Wake the bot instantly via Postgres NOTIFY
    try:
        await execute("SELECT pg_notify('prowl_actions', $1)", str(guild_id))
    except Exception:
        pass


@app.get("/api/v1/mod/{guild_id}/debug")
async def mod_debug(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d is not None:
        return {"has_data": True, "has_members": "members" in d, "has_channels": "channels" in d, "has_roles": "roles" in d, "keys": list(d.keys()), "member_count": len(d.get("members", [])), "channel_count": len(d.get("channels", [])), "role_count": len(d.get("roles", []))}
    raw = row["data"] if row else None
    return {"has_data": bool(row), "raw_type": str(type(raw)), "raw_value_preview": str(raw)[:200] if raw else None}


@app.get("/api/v1/mod/{guild_id}/members")
async def mod_members(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)

    def avatar_url(m):
        av = m.get("avatar_url") or m.get("avatar")
        if not av:
            return None
        if str(av).startswith("http"):
            return str(av)
        return f"https://cdn.discordapp.com/avatars/{m.get('id')}/{av}.png?size=64"

    if d and "members" in d:
        # Filter out the bot (bot user ID is in config); coerce IDs to strings
        return {"members": [{
            "id": str(m.get("id")), "name": m.get("name", ""), "display_name": m.get("display_name", ""),
            "avatar_url": avatar_url(m), "joined_at": m.get("joined_at"), "roles": m.get("roles") or [],
        } for m in d["members"] if str(m.get("id", "")) != _cfg().get("CLIENT_ID")]}
    return {"members": [
        {"id":"1001","name":"Alice","avatar_url":"https://cdn.discordapp.com/embed/avatars/0.png"},
        {"id":"1002","name":"Bob","avatar_url":"https://cdn.discordapp.com/embed/avatars/1.png"},
        {"id":"1003","name":"Charlie","avatar_url":"https://cdn.discordapp.com/embed/avatars/2.png"},
        {"id":"1004","name":"Diana","avatar_url":"https://cdn.discordapp.com/embed/avatars/3.png"},
        {"id":"1005","name":"Eve","avatar_url":"https://cdn.discordapp.com/embed/avatars/4.png"},
    ]}


@app.get("/api/v1/mod/{guild_id}/channels")
async def mod_channels(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "channels" in d:
        # Coerce IDs to strings (JS-safe) - categories reported separately
        return {
            "channels": [{"id": str(c.get("id")), "name": c.get("name", "")} for c in d["channels"] if c.get("type", 0) == 0],
            "categories": [{"id": str(c.get("id")), "name": c.get("name", "")} for c in d["channels"] if c.get("type", 0) == 4],
        }
    return {"channels": [
        {"id":"2001","name":"general","type":0},
        {"id":"2002","name":"chat","type":0},
        {"id":"2003","name":"spam","type":0},
    ], "categories": []}


@app.get("/api/v1/mod/{guild_id}/muted")
async def mod_muted(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    now = time.time()
    try:
        rows = await query(
            "SELECT user_id, user_name, reason, end_ts FROM muted_users WHERE guild_id = $1 AND end_ts > $2 ORDER BY end_ts ASC",
            str(guild_id), now,
        )
    except Exception:
        await execute(
            "CREATE TABLE IF NOT EXISTS muted_users (guild_id TEXT NOT NULL, user_id TEXT NOT NULL, user_name TEXT DEFAULT '', reason TEXT DEFAULT '', end_ts DOUBLE PRECISION NOT NULL DEFAULT 0, PRIMARY KEY (guild_id, user_id))"
        )
        rows = await query(
            "SELECT user_id, user_name, reason, end_ts FROM muted_users WHERE guild_id = $1 AND end_ts > $2 ORDER BY end_ts ASC",
            str(guild_id), now,
        )

    # Avatar lookup from guild_data members
    avatar_map = {}
    gd = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    parsed = _parse_guild_data({"data": gd["data"]}) if gd else None
    if parsed and isinstance(parsed.get("members"), list):
        for m in parsed["members"]:
            av = m.get("avatar_url") or m.get("avatar")
            if av:
                if not str(av).startswith("http"):
                    av = f"https://cdn.discordapp.com/avatars/{m.get('id')}/{av}.png?size=64"
                avatar_map[str(m.get("id"))] = av

    muted = []
    for r in rows:
        uid = str(r["user_id"])
        avatar = avatar_map.get(uid)
        muted.append({
            "id": uid,
            "name": r["user_name"],
            "reason": r.get("reason", ""),
            "end_ts": r.get("end_ts") or 0,
            "avatar": avatar,
            "avatar_url": avatar,
        })
    return {"muted": muted}


@app.get("/api/v1/mod/{guild_id}/roles")
async def mod_roles(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    roles = d.get("roles", []) if d else []
    if row and isinstance(row["data"], dict) and "roles" in row["data"]:
        roles = row["data"]["roles"]
    settings = await _get_mod_settings(guild_id)
    mod_role_ids = settings.get("mod_roles", [])

    # Get bot's highest role position from guild data
    bot_role_pos = None
    if d and "bot_top_role_position" in d:
        bot_role_pos = d["bot_top_role_position"]

    exclude = ["level", "verified", "member", "bot"]
    result = []
    for r in roles:
        name = (r.get("name") or "").lower()
        # Skip @everyone (role ID matches guild ID)
        if str(r.get("id", "")) == str(guild_id):
            continue
        # Skip roles with excluded words and bot-managed roles
        if any(kw in name.split() for kw in exclude):
            continue
        tags = r.get("tags")
        if isinstance(tags, dict) and tags.get("bot_id"):
            continue
        if r.get("managed", False):
            continue
        # Auto-enable for roles with administrator permission (bit 3 = 8)
        perms = r.get("permissions", 0) or 0
        has_admin = bool(perms & 8)
        # Mark roles above Prowl's highest role as disabled (can't assign)
        is_above = bot_role_pos is not None and r.get("position", 0) > bot_role_pos
        r["id"] = str(r.get("id"))
        r["disabled"] = is_above
        r["is_mod"] = has_admin or (str(r.get("id")) in mod_role_ids)
        r["count"] = r.get("count") or r.get("member_count") or 0
        result.append(r)
    if not result:
        result = [
            {"id":"4001","name":"Admin","count":3,"is_mod":True,"disabled":True},
            {"id":"4002","name":"Moderator","count":8,"is_mod":True},
            {"id":"4005","name":"VIP","count":15,"is_mod":False},
        ]
    return {"roles": result}


@app.post("/api/v1/mod/{guild_id}/roles")
async def mod_roles_set(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    role_id = body.get("role_id")
    is_mod = body.get("is_mod", False)
    if not role_id:
        return JSONResponse({"error": "missing role_id"}, status_code=400)
    current = await _get_mod_settings(guild_id)
    mod_roles = current.get("mod_roles", [])
    if is_mod and role_id not in mod_roles:
        mod_roles.append(role_id)
    elif not is_mod and role_id in mod_roles:
        mod_roles.remove(role_id)
    current["mod_roles"] = mod_roles
    await execute(
        "INSERT INTO mod_settings (guild_id, settings) VALUES ($1, $2::jsonb) "
        "ON CONFLICT (guild_id) DO UPDATE SET settings = $2::jsonb",
        str(guild_id), json.dumps(current),
    )
    return {"ok": True}


@app.post("/api/v1/mod/{guild_id}/roles/batch")
async def mod_roles_batch(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    role_ids = body.get("role_ids", [])
    current = await _get_mod_settings(guild_id)
    current["mod_roles"] = role_ids
    await execute(
        "INSERT INTO mod_settings (guild_id, settings) VALUES ($1, $2::jsonb) "
        "ON CONFLICT (guild_id) DO UPDATE SET settings = $2::jsonb",
        str(guild_id), json.dumps(current),
    )
    logger.info(f"Mod roles saved for guild {guild_id}: {role_ids}")
    return {"ok": True, "mod_roles": role_ids}


@app.post("/api/v1/mod/{guild_id}/emergency")
async def mod_emergency(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    locked = body.get("locked", False)
    await execute(
        "INSERT INTO mod_settings (guild_id, settings) VALUES ($1, $2::jsonb) "
        "ON CONFLICT (guild_id) DO UPDATE SET settings = mod_settings.settings || $2::jsonb",
        str(guild_id), json.dumps({"emergency_lock": locked}),
    )
    # Queue the actual lockdown/restore for the bot to execute
    session_user = request.session.get("user") or {}
    moderator = session_user.get("username", "Unknown")
    action = "emergency_lock" if locked else "emergency_unlock"
    await _queue_action(guild_id, action, "", "", "Emergency lockdown" if locked else "Emergency unlock", None, moderator)
    return {"ok": True}


@app.post("/api/v1/mod/{guild_id}/purge")
async def mod_purge(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    channel_id = body.get("channel_id")
    count = int(body.get("count", 10))
    if not channel_id:
        return JSONResponse({"error": "missing channel_id"}, status_code=400)
    if count < 1 or count > 100:
        return JSONResponse({"error": "count must be 1-100"}, status_code=400)
    await _queue_action(guild_id, "purge", channel_id, "", f"Purge {count} messages", count)
    return {"ok": True, "queued": True, "purged": count}


@app.get("/api/v1/mod/{guild_id}/stats/members")
async def mod_member_stats(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    rows = await query(
        "SELECT timestamp, member_count FROM member_history WHERE guild_id = $1 ORDER BY timestamp ASC LIMIT 168",
        str(guild_id),
    )
    return {"points": [{"t": r["timestamp"], "v": r["member_count"]} for r in rows]}


@app.get("/api/v1/mod/{guild_id}/stats/messages")
async def mod_message_stats(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    rows = await query(
        "SELECT timestamp, message_count FROM message_history WHERE guild_id = $1 ORDER BY timestamp ASC LIMIT 168",
        str(guild_id),
    )
    return {"points": [{"t": r["timestamp"], "v": r["message_count"]} for r in rows]}


@app.get("/api/v1/mod/{guild_id}/actions")
async def mod_actions_list(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    rows = await query(
        "SELECT id, action, target_id, target_name, reason, moderator, duration, status, error, created_at, processed_at "
        "FROM mod_actions WHERE guild_id = $1 ORDER BY created_at DESC LIMIT 30",
        str(guild_id),
    )
    return {"actions": [dict(r) for r in rows]}


@app.post("/api/v1/mod/{guild_id}/action")
async def mod_action(guild_id: str, request: Request):
    """Queue a moderation action for the bot to process."""
    await require_guild_access(request, guild_id)
    body = await request.json()
    action = body.get("action")
    user_id = body.get("user_id")
    reason = body.get("reason", "")
    duration = body.get("duration")
    user_name = body.get("user_name", "")
    if action not in ("mute", "unmute", "kick", "ban", "add_role", "remove_role", "nickname"):
        return JSONResponse({"error": "Invalid action"}, status_code=400)
    session_user = request.session.get("user") or {}
    moderator = session_user.get("username", "Unknown")
    # For role/nickname actions, target_name carries the role ID or new nickname
    target_name = body.get("target") if action in ("add_role", "remove_role", "nickname") else user_name
    await _queue_action(guild_id, action, user_id, target_name, reason, duration, moderator)
    return {"ok": True, "queued": True}


# ---------------------------------------------------------------------------
#  Social Alerts API v1
# ---------------------------------------------------------------------------

SOCIAL_SETTINGS_DEFAULTS = {
    "youtube_enabled": False, "youtube_channel_id": None, "youtube_ping_role": None, "youtube_announce_channel_id": None, "youtube_message": None,
    "twitch_enabled": False, "twitch_channel": None, "twitch_ping_role": None, "twitch_announce_channel_id": None, "twitch_message": None,
    "twitter_enabled": False, "twitter_handle": None, "twitter_ping_role": None, "twitter_announce_channel_id": None, "twitter_message": None,
    "default_announce_channel_id": None, "default_ping_role": None,
    "extra_alerts": {},
}


async def _get_social_settings(guild_id: str):
    row = await fetchrow("SELECT settings FROM social_settings WHERE guild_id = $1", str(guild_id))
    if row:
        settings = row["settings"]
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except (json.JSONDecodeError, TypeError):
                return dict(SOCIAL_SETTINGS_DEFAULTS)
        if isinstance(settings, dict):
            return {**SOCIAL_SETTINGS_DEFAULTS, **settings}
    return dict(SOCIAL_SETTINGS_DEFAULTS)


@app.get("/api/v1/social/{guild_id}/settings")
async def social_settings(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    return {"settings": await _get_social_settings(guild_id)}


@app.post("/api/v1/social/{guild_id}/settings")
async def social_settings_set(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    key = body.get("key")
    value = body.get("value")
    if not key:
        return JSONResponse({"error": "missing key"}, status_code=400)

    # Special validation for extra_alerts
    if key == "extra_alerts":
        clean, err = _sanitize_extra_alerts(value)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        err = await _save_settings("social_settings", str(guild_id), "extra_alerts", clean, SOCIAL_SETTINGS_DEFAULTS)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        return {"ok": True}

    err = await _save_settings("social_settings", str(guild_id), key, value, SOCIAL_SETTINGS_DEFAULTS)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    return {"ok": True}


@app.get("/api/v1/social/{guild_id}/roles")
async def social_roles(guild_id: str, request: Request):
    """All roles for ping-role dropdowns."""
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "roles" in d:
        return {"roles": [{"id": str(r.get("id")), "name": r.get("name", "")} for r in d["roles"]]}
    return {"roles": []}


@app.get("/api/v1/social/{guild_id}/channels")
async def social_channels(guild_id: str, request: Request):
    """Text channels for the announce-channel dropdown."""
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "channels" in d:
        return {"channels": [{"id": str(c.get("id")), "name": c.get("name", "")} for c in d["channels"] if c.get("type", 0) == 0]}
    return {"channels": []}


# ---------------------------------------------------------------------------
#  Tickets API v1
# ---------------------------------------------------------------------------

TICKET_SETTINGS_DEFAULTS = {
    "enabled": False,
    "category_id": None,
    "support_role_id": None,
    "log_channel_id": None,
    "welcome_message": "Support will be with you shortly. Please describe your issue.",
    "ticket_limit": 3,
    "auto_close_hours": 0,
    "panel_channel_id": None,
    "panel_embed": {},
    "questions": [],
}


def _sanitize_panel_embed(value):
    """Validate panel_embed: dict with bounded string/field limits."""
    if not isinstance(value, dict):
        return None, "panel_embed must be an object"
    clean = {}
    for key in ("title", "description", "url", "author_name", "author_url", "author_icon",
                "image_url", "thumbnail_url", "footer_text", "footer_icon"):
        v = value.get(key)
        if v is not None:
            if not isinstance(v, str):
                return None, f"'{key}' must be a string"
            clean[key] = v[:1024]
    color = value.get("color")
    if color is not None:
        try:
            int(str(color).lstrip("#"), 16)
        except (ValueError, TypeError):
            return None, "invalid color"
        clean["color"] = str(color)
    fields = value.get("fields")
    if fields is not None:
        if not isinstance(fields, list) or len(fields) > 25:
            return None, "fields must be a list of max 25"
        clean_fields = []
        for f in fields:
            if not isinstance(f, dict):
                return None, "each field must be an object"
            name = str(f.get("name") or "")[:256]
            if not name:
                return None, "field name is required"
            clean_fields.append({
                "name": name,
                "value": str(f.get("value") or "\u200b")[:1024],
                "inline": bool(f.get("inline")),
            })
        clean["fields"] = clean_fields
    return clean, None


def _sanitize_questions(value):
    """Validate questions: list of {label, placeholder, required}, max 5 (Discord modal limit)."""
    if not isinstance(value, list):
        return None, "questions must be a list"
    if len(value) > 5:
        return None, "questions exceeds max of 5 (Discord modal limit)"
    clean = []
    for q in value:
        if not isinstance(q, dict):
            return None, "each question must be an object"
        label = str(q.get("label") or "").strip()
        if not label:
            return None, "question label is required"
        clean.append({
            "label": label[:45],
            "placeholder": (str(q.get("placeholder") or "").strip())[:100] or None,
            "required": bool(q.get("required", True)),
        })
    return clean, None


async def _get_ticket_settings(guild_id: str):
    row = await fetchrow("SELECT settings FROM ticket_settings WHERE guild_id = $1", str(guild_id))
    if row:
        settings = row["settings"]
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except (json.JSONDecodeError, TypeError):
                return dict(TICKET_SETTINGS_DEFAULTS)
        if isinstance(settings, dict):
            return {**TICKET_SETTINGS_DEFAULTS, **settings}
    return dict(TICKET_SETTINGS_DEFAULTS)


@app.get("/api/v1/tickets/{guild_id}/settings")
async def ticket_settings(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    return {"settings": await _get_ticket_settings(guild_id)}


@app.post("/api/v1/tickets/{guild_id}/settings")
async def ticket_settings_set(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    key = body.get("key")
    value = body.get("value")
    if not key:
        return JSONResponse({"error": "missing key"}, status_code=400)
    if key == "panel_embed":
        clean, err = _sanitize_panel_embed(value)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        err = await _save_settings("ticket_settings", str(guild_id), "panel_embed", clean, TICKET_SETTINGS_DEFAULTS)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        return {"ok": True}
    if key == "questions":
        clean, err = _sanitize_questions(value)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        err = await _save_settings("ticket_settings", str(guild_id), "questions", clean, TICKET_SETTINGS_DEFAULTS)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        return {"ok": True}
    err = await _save_settings("ticket_settings", str(guild_id), key, value, TICKET_SETTINGS_DEFAULTS)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    return {"ok": True}


@app.post("/api/v1/tickets/{guild_id}/send_panel")
async def ticket_send_panel(guild_id: str, request: Request):
    """Queue the bot to send the ticket panel embed to a channel."""
    await require_guild_access(request, guild_id)
    body = await request.json()
    channel_id = body.get("channel_id")
    if not channel_id:
        return JSONResponse({"error": "missing channel_id"}, status_code=400)
    session_user = request.session.get("user") or {}
    moderator = session_user.get("username", "Unknown")
    await _queue_action(guild_id, "panel_send", channel_id, "panel", "Ticket panel", None, moderator)
    return {"ok": True, "queued": True}


@app.get("/api/v1/tickets/{guild_id}/categories")
async def ticket_categories(guild_id: str, request: Request):
    """Categories for the ticket category dropdown."""
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "channels" in d:
        return {"categories": [{"id": str(c.get("id")), "name": c.get("name", "")} for c in d["channels"] if c.get("type", 0) == 4]}
    return {"categories": []}


@app.get("/api/v1/tickets/{guild_id}/channels")
async def ticket_channels(guild_id: str, request: Request):
    """Text channels for the log-channel dropdown."""
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "channels" in d:
        return {"channels": [{"id": str(c.get("id")), "name": c.get("name", "")} for c in d["channels"] if c.get("type", 0) == 0]}
    return {"channels": []}


@app.get("/api/v1/tickets/{guild_id}/roles")
async def ticket_roles(guild_id: str, request: Request):
    """All roles for the support-role dropdown."""
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "roles" in d:
        return {"roles": [{"id": str(r.get("id")), "name": r.get("name", "")} for r in d["roles"]]}
    return {"roles": []}


# ---------------------------------------------------------------------------
#  Verification API v1
# ---------------------------------------------------------------------------

VERIFY_SETTINGS_DEFAULTS = {
    "enabled": False, "channel_id": None, "verified_role_id": None,
    "log_channel_id": None, "type": "button", "captcha": False,
    "message": "Click the button below to verify yourself.",
    "reaction_emoji": "✅",
    "recaptcha_site_key": "", "recaptcha_secret": "",
    "turnstile_site_key": "", "turnstile_secret": "",
}


async def _get_verify_settings(guild_id: str):
    row = await fetchrow("SELECT settings FROM verify_settings WHERE guild_id = $1", str(guild_id))
    if row:
        settings = row["settings"]
        if isinstance(settings, str):
            try: settings = json.loads(settings)
            except: return dict(VERIFY_SETTINGS_DEFAULTS)
        if isinstance(settings, dict):
            return {**VERIFY_SETTINGS_DEFAULTS, **settings}
    return dict(VERIFY_SETTINGS_DEFAULTS)


@app.get("/api/v1/verify/{guild_id}/settings")
async def verify_settings(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    return {"settings": await _get_verify_settings(guild_id)}


@app.post("/api/v1/verify/{guild_id}/settings")
async def verify_settings_set(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    key = body.get("key"); value = body.get("value")
    if not key: return JSONResponse({"error": "missing key"}, 400)
    err = await _save_settings("verify_settings", str(guild_id), key, value, VERIFY_SETTINGS_DEFAULTS)
    if err: return JSONResponse({"error": err}, 400)
    return {"ok": True}


@app.post("/api/v1/verify/{guild_id}/deploy")
async def verify_deploy(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    await _queue_action(guild_id, "verify_panel", "0", "", "Deploy verification panel", None)
    return {"ok": True, "queued": True}


@app.get("/api/v1/verify/{guild_id}/channels")
async def verify_channels(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "channels" in d:
        return {"channels": [{"id": str(c.get("id")), "name": c.get("name")} for c in d["channels"] if c.get("type", 0) == 0]}
    return {"channels": []}


@app.get("/api/v1/verify/{guild_id}/roles")
async def verify_roles(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "roles" in d:
        return {"roles": [{"id": str(r.get("id")), "name": r.get("name")} for r in d["roles"]]}
    return {"roles": []}


@app.get("/api/v1/members/{guild_id}/roles")
async def members_roles(guild_id: str, request: Request):
    """All roles (unfiltered) with positions + managed flag for member management."""
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "roles" in d:
        return {"roles": [{"id": str(r.get("id")), "name": r.get("name", ""), "position": r.get("position", 0), "managed": bool(r.get("managed", False))} for r in d["roles"]]}
    return {"roles": []}


@app.get("/api/v1/members/{guild_id}/bot")
async def members_bot_info(guild_id: str, request: Request):
    """Bot hierarchy/permission info for member management checks."""
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d:
        return {
            "bot_top_role_position": d.get("bot_top_role_position", 0),
            "bot_permissions": int(d.get("bot_permissions", 0) or 0),
            "can_manage_nicknames": bool(int(d.get("bot_permissions", 0) or 0) & (1 << 27)),
            "can_manage_roles": bool(int(d.get("bot_permissions", 0) or 0) & (1 << 28)),
        }
    return {"bot_top_role_position": 0, "bot_permissions": 0, "can_manage_nicknames": False, "can_manage_roles": False}


# ---------------------------------------------------------------------------
#  Global Chat API v1
# ---------------------------------------------------------------------------

GC_DEFAULTS = {"enabled": False, "channel_id": None}


async def _get_gc_settings(guild_id: str):
    d = dict(GC_DEFAULTS)
    for key in ("global_chat_enabled", "global_chat_channel"):
        row = await fetchrow("SELECT value FROM bot_stats WHERE key = $1", key)
        if row:
            d["enabled" if key == "global_chat_enabled" else "channel_id"] = (
                row["value"].lower() == "true" if key == "global_chat_enabled" else str(row["value"])
            )
    return d


@app.get("/api/v1/global_chat/{guild_id}/settings")
async def gc_settings(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    return {"settings": await _get_gc_settings(guild_id)}


@app.post("/api/v1/global_chat/{guild_id}/settings")
async def gc_settings_set(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    key = body.get("key"); value = body.get("value")
    if not key: return JSONResponse({"error": "missing key"}, 400)
    if key not in GC_DEFAULTS and key not in ("enabled", "channel_id"):
        return JSONResponse({"error": f"unknown key '{key}'"}, 400)
    db_key = "global_chat_enabled" if key == "enabled" else "global_chat_channel" if key == "channel_id" else key
    db_val = str(value) if value is not None else ""
    await execute(
        "INSERT INTO bot_stats (key, value, updated_at) VALUES ($1, $2, $3) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at",
        db_key, db_val, time.time(),
    )
    return {"ok": True}


@app.get("/api/v1/global_chat/{guild_id}/channels")
async def gc_channels(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "channels" in d:
        return {"channels": [{"id": str(c.get("id")), "name": c.get("name")} for c in d["channels"] if c.get("type", 0) == 0]}
    return {"channels": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="127.0.0.1", port=8000, reload=True)
