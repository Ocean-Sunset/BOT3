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
from starlette.middleware.sessions import SessionMiddleware
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
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", secrets.token_hex(32)))

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
#  Routes — Pages
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
#  Routes — API v1
# ---------------------------------------------------------------------------

async def require_auth(request: Request):
    user = get_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
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
async def api_db_test():
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
async def api_status():
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
async def api_commands():
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
    current = await _get_mod_settings(guild_id)
    current[key] = value
    await execute(
        "INSERT INTO mod_settings (guild_id, settings) VALUES ($1, $2::jsonb) "
        "ON CONFLICT (guild_id) DO UPDATE SET settings = $2::jsonb",
        str(guild_id), json.dumps(current),
    )
    return {"ok": True}


@app.get("/api/v1/mod/{guild_id}/feed")
async def mod_feed(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    rows = await query(
        "SELECT user_name, action, reason, created_at FROM mod_log WHERE guild_id = $1 ORDER BY created_at DESC LIMIT 20",
        str(guild_id),
    )
    if rows:
        return {"events": [{
            "user": r["user_name"],
            "action": r["action"],
            "reason": r.get("reason", ""),
            "time": _relative_time(r["created_at"]),
            "color": {"ban": "red", "kick": "red", "mute": "blue", "warn": "yellow", "join": "green"}.get(r["action"], "gray"),
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
    if d and "members" in d:
        return {"members": d["members"]}
    return {"members": [
        {"id":"1001","name":"Alice","avatar":None},
        {"id":"1002","name":"Bob","avatar":None},
        {"id":"1003","name":"Charlie","avatar":None},
        {"id":"1004","name":"Diana","avatar":None},
        {"id":"1005","name":"Eve","avatar":None},
    ]}


@app.get("/api/v1/mod/{guild_id}/channels")
async def mod_channels(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "channels" in d:
        return {"channels": d["channels"]}
    return {"channels": [
        {"id":"2001","name":"general"},
        {"id":"2002","name":"chat"},
        {"id":"2003","name":"spam"},
    ]}


@app.get("/api/v1/mod/{guild_id}/muted")
async def mod_muted(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    rows = await query(
        "SELECT user_id, user_name, reason, created_at FROM mod_log "
        "WHERE guild_id = $1 AND action = 'mute' ORDER BY created_at DESC LIMIT 50",
        str(guild_id),
    )
    if rows:
        return {"muted": [{"id": r["user_id"], "name": r["user_name"], "reason": r.get("reason", ""), "end_ts": 0} for r in rows]}
    return {"muted": []}


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
    return {"ok": True}


@app.post("/api/v1/mod/{guild_id}/emergency")
async def mod_emergency(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    await execute(
        "INSERT INTO mod_settings (guild_id, settings) VALUES ($1, $2::jsonb) "
        "ON CONFLICT (guild_id) DO UPDATE SET settings = mod_settings.settings || $2::jsonb",
        str(guild_id), json.dumps({"emergency_lock": body.get("locked", False)}),
    )
    return {"ok": True}


@app.post("/api/v1/mod/{guild_id}/purge")
async def mod_purge(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    return {"ok": True, "purged": body.get("count", 0)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="127.0.0.1", port=8000, reload=True)
