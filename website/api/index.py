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

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import httpx

from api.db import get_pool, query, fetchrow, fetchval

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


async def get_bot_guild_ids():
    rows = await query("SELECT guild_id FROM guild_data")
    return {row["guild_id"] for row in rows}


async def get_user_guilds_filtered(request: Request):
    token = get_token(request)
    if not token:
        return []
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
    return eligible


# ---------------------------------------------------------------------------
#  Routes — Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "landing.html", {"config": _cfg()})


@app.get("/login")
async def login():
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
        "overview", "ai", "welcomer", "verification", "roles", "leveling",
        "commands", "lideration", "logs", "statistics", "music", "settings",
    ]
    if panel not in valid_panels:
        panel = "overview"

    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "guild": guild_info,
        "guild_id": guild_id,
        "active_panel": panel,
        "bot_data": {},
        "config": _cfg(),
    })


# ---------------------------------------------------------------------------
#  Routes — API
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def api_health():
    return {"status": "ok", "service": "prowl-api", "version": "1.0.1"}


@app.get("/api/ping")
async def api_ping():
    return {"ping": "pong"}


@app.get("/api/db-test")
async def api_db_test():
    try:
        row = await fetchval("SELECT 1")
        return {"db": "connected", "result": row}
    except Exception as e:
        return {"db": "error", "detail": str(e)}


@app.get("/api/@me")
async def api_me(request: Request):
    user = get_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "discriminator": user.get("discriminator"),
        "avatar": user.get("avatar"),
    }


@app.get("/api/status")
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


@app.get("/api/guilds")
async def api_guilds():
    rows = await query("SELECT data FROM guild_data ORDER BY updated_at DESC")
    guilds = []
    for row in rows:
        g = row["data"]
        guilds.append({
            "id": g.get("id"),
            "name": g.get("name"),
            "icon_url": g.get("icon_url"),
            "member_count": g.get("member_count", 0),
            "online_count": g.get("online_count", 0),
        })
    return {"guilds": guilds}


@app.get("/api/guild/{guild_id}")
async def api_guild(guild_id: str):
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    if row:
        return row["data"]
    return JSONResponse({"error": "Guild not found"}, status_code=404)


@app.get("/api/commands")
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
