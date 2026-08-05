import os
import json
import time
import secrets
import logging
import urllib.parse
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env.local")
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
        await _ensure_incidents()
    except Exception as e:
        logger.error("Failed to initialize database pool: %s", e)
    yield

app = FastAPI(title="Prowl", version="1.0.0", lifespan=lifespan)

# CORS for api.prowlbot.xyz (cross-origin API calls from the main site)
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://prowlbot.xyz",
        "https://www.prowlbot.xyz",
        "https://api.prowlbot.xyz",
        "https://status.prowlbot.xyz",
        "http://localhost:5000",
        "http://localhost:8000",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        # Session data lives in the signed cookie itself - serverless-safe.
        session_data = rotating_session.unsign_session_data(cookie_val) if cookie_val else None
        if session_data is None:
            session_data = {}
        session_snapshot = json.dumps(session_data, sort_keys=True, default=str)

        scope["session"] = session_data

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                # Re-sign the cookie whenever the data changed, to keep it fresh.
                cur = json.dumps(scope.get("session") or {}, sort_keys=True, default=str)
                if cur != session_snapshot or not cookie_val:
                    signed = rotating_session.sign_session_data(scope.get("session") or {})
                    host = (conn.headers.get("host") or "").lower()
                    if "prowlbot.xyz" in host:
                        headers["Set-Cookie"] = (
                            f"session={signed}; Path=/; HttpOnly; SameSite=None; Secure; Domain=.prowlbot.xyz; Max-Age={86400}"
                        )
                    else:
                        headers["Set-Cookie"] = (
                            f"session={signed}; Path=/; HttpOnly; SameSite=lax; Max-Age={86400}"
                        )
            await send(message)

        await self.app(scope, receive, send_wrapper)


app.add_middleware(RotatingSessionMiddleware)

# ── Security headers ──
# 'unsafe-inline'/'unsafe-eval' are required by the CDN-based JS, tailwind play
# CDN, and inline dashboard scripts. The CSP still restricts every other source
# to known domains (defense in depth against injected external resources).
CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
    "https://cdn.tailwindcss.com https://unpkg.com https://cdnjs.cloudflare.com "
    "https://cdn.jsdelivr.net https://www.google.com https://www.gstatic.com "
    "https://challenges.cloudflare.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: https://cdn.discordapp.com https://img.itch.zone; "
    "connect-src 'self' https://api.prowlbot.xyz https://discord.com "
    "https://www.google.com https://www.gstatic.com https://challenges.cloudflare.com; "
    "frame-src https://www.google.com https://www.gstatic.com https://challenges.cloudflare.com; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'"
)


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        host = ""
        for k, v in scope.get("headers") or []:
            if k == b"host":
                host = v.decode("latin-1").lower()
                break

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                from starlette.datastructures import MutableHeaders
                headers = MutableHeaders(scope=message)
                headers["Content-Security-Policy"] = CSP
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
                headers["X-Frame-Options"] = "DENY"
                # Only on production hosts - HSTS on localhost would break dev
                if "prowlbot.xyz" in host:
                    headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
            await send(message)

        await self.app(scope, receive, send_wrapper)


app.add_middleware(SecurityHeadersMiddleware)

# ── Request counting (status page graph) ──
_REQUEST_SKIP = ("/static/", "/favicon.ico", "/favicon.png")
_REQUEST_SKIP_EXACT = ("/api/v1/status/summary", "/api/v1/health", "/api/v1/ping")


class RequestCountMiddleware:
    """Best-effort hourly request counter for the public status page graph."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        host = ""
        for k, v in scope.get("headers") or []:
            if k == b"host":
                host = v.decode("latin-1").lower()
                break
        skip = path.startswith(_REQUEST_SKIP) or path in _REQUEST_SKIP_EXACT or "prowlbot.xyz" not in host
        await self.app(scope, receive, send)
        if skip:
            return
        # Awaited (not fire-and-forget): serverless functions die right after the
        # response, so the write must complete inside the request lifecycle.
        await self._count()

    async def _count(self):
        try:
            bucket = int(time.time() // 3600) * 3600
            await execute(
                "INSERT INTO request_stats (bucket_ts, count) VALUES ($1, 1) "
                "ON CONFLICT (bucket_ts) DO UPDATE SET count = request_stats.count + 1",
                bucket,
            )
        except Exception:
            try:
                await execute(_REQUEST_TABLE_SQL)
                bucket = int(time.time() // 3600) * 3600
                await execute(
                    "INSERT INTO request_stats (bucket_ts, count) VALUES ($1, 1) "
                    "ON CONFLICT (bucket_ts) DO UPDATE SET count = request_stats.count + 1",
                    bucket,
                )
            except Exception:
                pass


_REQUEST_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS request_stats (
    bucket_ts DOUBLE PRECISION PRIMARY KEY,
    count INTEGER NOT NULL DEFAULT 0
);
"""


app.add_middleware(RequestCountMiddleware)

# ── Subdomain routing: enforce api.prowlbot.xyz = API only, prowlbot.xyz = pages ──
class SubdomainRouteMiddleware:
    """
    Enforce the subdomain split:
      - api.prowlbot.xyz  -> API-only (only /api/*, plus a small root descriptor)
      - status.prowlbot.xyz -> status page at any non-static path
      - prowlbot.xyz / www.prowlbot.xyz -> main website; /api/* redirects to api subdomain
    """

    def __init__(self, app):
        self.app = app

    def _host(self, scope):
        headers = dict(scope.get("headers") or [])
        # Prefer the real host; Vercel may forward via x-forwarded-host
        host = headers.get(b"host", b"").decode("latin-1").lower()
        if not host and b"x-forwarded-host" in headers:
            host = headers.get(b"x-forwarded-host", b"").decode("latin-1").lower()
        if host and ":" in host:
            host = host.split(":")[0]
        return host

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        host = self._host(scope)
        path = scope.get("path", "")
        query = scope.get("query_string", b"").decode("latin-1")

        is_api_host = host == "api.prowlbot.xyz"
        is_status_host = host == "status.prowlbot.xyz"
        is_main_host = host in ("prowlbot.xyz", "www.prowlbot.xyz")

        # api.prowlbot.xyz: API-only gateway
        if is_api_host:
            if path in ("/", ""):
                return await self._send_json(
                    scope, receive, send, 200,
                    {
                        "service": "prowl-api",
                        "version": "1.0.0",
                        "endpoints": {
                            "health": "https://api.prowlbot.xyz/api/v1/health",
                            "ping": "https://api.prowlbot.xyz/api/v1/ping",
                        },
                    },
                )
            # Browsers request the favicon when API endpoints 4xx - let it through
            if path in ("/favicon.ico", "/favicon.png"):
                await self.app(scope, receive, send)
                return
            if not path.startswith("/api/"):
                return await self._send_json(
                    scope, receive, send, 404,
                    {"error": "Not Found", "message": "Only /api/* routes are available on this subdomain."},
                )
            await self.app(scope, receive, send)
            return

        # status.prowlbot.xyz: serve the status page at the root
        if is_status_host:
            # API + static assets are shared with the main app; allow them through
            if path.startswith("/api/") or path.startswith("/static/") or path in ("/favicon.ico", "/favicon.png"):
                await self.app(scope, receive, send)
                return
            # Rewrite everything else to the /status page handler
            scope["path"] = "/status"
            scope["raw_path"] = b"/status"
            await self.app(scope, receive, send)
            return

        # prowlbot.xyz: main website; API routes should live on the API subdomain
        if is_main_host and path.startswith("/api/"):
            from starlette.responses import RedirectResponse
            new_path = f"https://api.prowlbot.xyz{path}"
            if query:
                new_path += "?" + query
            resp = RedirectResponse(new_path, status_code=307)
            await resp(scope, receive, send)
            return

        await self.app(scope, receive, send)

    async def _send_json(self, scope, receive, send, status, obj):
        from starlette.responses import JSONResponse
        resp = JSONResponse(obj, status_code=status)
        await resp(scope, receive, send)


app.add_middleware(SubdomainRouteMiddleware)

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
    detail = getattr(exc, "detail", None)
    retry = 30
    headers = getattr(exc, "headers", None)
    if headers:
        ra = headers.get("Retry-After")
        if ra:
            try:
                retry = int(ra)
            except (ValueError, TypeError):
                pass
    return templates.TemplateResponse(
        request, "error.html",
        {"code": 429, "title": "Rate Limited", "message": detail or ERROR_PAGES[429][1], "retry_in": retry},
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
    if get_user(request):
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse(request, "login.html", {"config": _cfg()})


@app.get("/invite", response_class=HTMLResponse)
async def invite(request: Request):
    return templates.TemplateResponse(request, "invite.html", {"config": _cfg()})


@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    return templates.TemplateResponse(request, "tos.html", {"config": _cfg()})


@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse(request, "privacy.html", {"config": _cfg()})


@app.get("/status", response_class=HTMLResponse)
async def status_page(request: Request):
    return templates.TemplateResponse(request, "status.html", {"config": _cfg()})


@app.get("/captcha/{provider}", response_class=HTMLResponse)
async def captcha_page(request: Request, provider: str):
    """Hosted captcha solve page: renders the widget and auto-verifies on solve."""
    if provider not in ("recaptcha",):
        return templates.TemplateResponse(request, "error.html",
            {"code": 404, "title": "Not Found", "message": "Unknown captcha provider."}, status_code=404)
    code = request.query_params.get("code", "")
    info = await _validate_captcha_code(code, provider)
    if not info:
        return templates.TemplateResponse(request, "error.html",
            {"code": 403, "title": "Link Expired", "message": "This verification link is invalid or has already been used. Click Verify again in Discord to get a fresh link."},
            status_code=403)
    site_key = os.environ.get(f"{provider.upper()}_SITE_KEY", "")
    return templates.TemplateResponse(request, "captcha.html", {
        "provider": provider,
        "site_key": site_key,
        "code": code,
        "recaptcha_version": os.environ.get("RECAPTCHA_VERSION", "v2"),
        "config": _cfg(),
    })


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
        await _upsert_user(user)

    return RedirectResponse("/dashboard")


@app.get("/callback/google")
async def callback_google(request: Request, code: str = None):
    """Complete Google OAuth. If a dashboard user is logged in, link the Google
    account to their Prowl account. Otherwise redirect to the login page."""
    if not code:
        return RedirectResponse("/login")
    google_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    google_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/callback/google")
    if not google_id or not google_secret:
        return RedirectResponse("/login")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": google_id,
                    "client_secret": google_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if r.status_code != 200:
                return RedirectResponse("/login")
            token_json = r.json()
            access_token = token_json.get("access_token")
            if not access_token:
                return RedirectResponse("/login")
            ui = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if ui.status_code != 200:
                return RedirectResponse("/login")
            profile = ui.json()
    except Exception as e:
        logger.error("Google OAuth failed: %s", e)
        return RedirectResponse("/login")

    gid = str(profile.get("sub", "") or "")
    gemail = profile.get("email", "") or ""
    user = get_user(request)
    if user and user.get("id"):
        try:
            await execute(
                "UPDATE users SET google_id = $1, google_email = $2 WHERE id = $3",
                gid, gemail, str(user.get("id")),
            )
        except Exception as e:
            logger.error("Google account link failed: %s", e)
        return RedirectResponse("/guild/profile")
    return RedirectResponse("/login")


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


@app.get("/guild/profile")
async def guild_profile(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/dashboard")
    # No guild context; the sidebar uses the last-viewed guild (saved client-side)
    return templates.TemplateResponse(request, "dashboard/profile.html", {
        "user": user,
        "guild": None,
        "guild_id": "",
        "active_panel": "profile",
        "bot_data": {},
        "config": _cfg(),
    }, headers={"Cache-Control": "no-store"})


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
        "autoresponder", "settings", "raid_protection", "profile",
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

    return templates.TemplateResponse(request, f"dashboard/{panel}.html", ctx,
                                      headers={"Cache-Control": "no-store"})


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


# ---------------------------------------------------------------------------
#  Accounts
# ---------------------------------------------------------------------------

async def _upsert_user(user: dict):
    """Record (or update) a user account on login."""
    if not user or not user.get("id"):
        return
    try:
        await execute(
            "INSERT INTO users (id, username, global_name, avatar, email, created_at, last_login) "
            "VALUES ($1, $2, $3, $4, $5, $6, $6) "
            "ON CONFLICT (id) DO UPDATE SET username = EXCLUDED.username, "
            "global_name = EXCLUDED.global_name, avatar = EXCLUDED.avatar, "
            "email = EXCLUDED.email, last_login = EXCLUDED.last_login",
            str(user["id"]), user.get("username", ""), user.get("global_name") or user.get("username", ""),
            user.get("avatar"), user.get("email", ""), time.time(),
        )
    except Exception as e:
        logger.error("Failed to upsert user account: %s", e)


@app.get("/api/v1/account")
async def account_info(request: Request):
    user = await require_auth(request)
    row = await fetchrow("SELECT id, username, global_name, created_at, last_login, google_id, google_email FROM users WHERE id = $1", str(user.get("id")))
    if not row:
        # Account not recorded yet (e.g. logged in before this feature) - record it now
        await _upsert_user(user)
        row = await fetchrow("SELECT id, username, global_name, created_at, last_login, google_id, google_email FROM users WHERE id = $1", str(user.get("id")))
    return {"account": dict(row) if row else None}


@app.post("/api/v1/account/google/unlink")
async def account_google_unlink(request: Request):
    user = await require_auth(request)
    try:
        await execute("UPDATE users SET google_id = '', google_email = '' WHERE id = $1", str(user.get("id")))
    except Exception as e:
        logger.error("google unlink failed: %s", e)
    return {"ok": True}


@app.post("/api/v1/account/delete")
async def account_delete(request: Request):
    user = await require_auth(request)
    uid = str(user.get("id"))
    username = user.get("username", "Unknown")
    # Find every server this user owns
    owned = []
    try:
        rows = await query("SELECT guild_id, data FROM guild_data")
        for row in rows:
            d = _parse_guild_data(row)
            if d and str(d.get("owner_id")) == uid:
                owned.append(str(row["guild_id"]))
    except Exception as e:
        logger.error("account delete: failed to list owned guilds: %s", e)
    # Wipe moderation state for those servers, then queue Prowl to leave each one
    for gid in owned:
        try:
            await execute("DELETE FROM muted_users WHERE guild_id = $1", gid)
            await execute("DELETE FROM mod_log WHERE guild_id = $1", gid)
            await execute("DELETE FROM mod_actions WHERE guild_id = $1", gid)
            await _queue_action(gid, "leave_guild", uid, username, "Account deleted", None, "System")
        except Exception as e:
            logger.error("account delete: cleanup failed for %s: %s", gid, e)
    await execute("DELETE FROM users WHERE id = $1", uid)
    request.session.clear()
    return {"ok": True, "cleaned_guilds": len(owned)}


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


# ---------------------------------------------------------------------------
#  Public status summary (no auth) - powers the status.prowlbot.xyz page
# ---------------------------------------------------------------------------

_INCIDENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS incidents (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    severity TEXT NOT NULL DEFAULT 'minor',
    starts_at DOUBLE PRECISION NOT NULL,
    resolves_at DOUBLE PRECISION
);
"""


async def _ensure_incidents():
    try:
        await execute(_INCIDENTS_TABLE_SQL)
    except Exception as e:
        logger.error("incidents table failed: %s", e)


@app.get("/api/v1/status/summary")
async def status_summary(request: Request):
    t0_all = time.perf_counter()
    rows = await query("SELECT key, value, updated_at FROM bot_stats")
    data = {row["key"]: row["value"] for row in rows}
    last_upd = {row["key"]: row["updated_at"] for row in rows}

    def safe_int(key, default=0):
        try:
            return int(data.get(key, default))
        except (ValueError, TypeError):
            return default

    def safe_str(key, default=""):
        return data.get(key, default)

    # Heartbeat staleness: the bot pushes stats every ~2 min. If nothing has
    # been written recently the process is down, regardless of the stored value.
    STALE_BOT_SECONDS = 240
    last_sync = 0
    for v in last_upd.values():
        try:
            last_sync = max(last_sync, int(v))
        except (TypeError, ValueError):
            pass
    bot_stale = bool(last_sync) and (time.time() - last_sync) > STALE_BOT_SECONDS

    def ago(ts):
        if not ts:
            return "never"
        s = int(max(0, time.time() - ts))
        if s < 60:
            return f"{s}s ago"
        if s < 3600:
            return f"{s // 60}m ago"
        return f"{s // 3600}h ago"

    # Live DB check + measured latency
    db_ok = False
    db_ms = None
    try:
        t0 = time.perf_counter()
        await fetchval("SELECT 1")
        db_ok = True
        db_ms = int((time.perf_counter() - t0) * 1000)
    except Exception:
        pass

    bot_up = data.get("bot_status") == "Running" and not bot_stale
    try:
        gateway_ping = int(float(data.get("gateway_ping_ms", 0)))
        gateway_ping = gateway_ping if gateway_ping > 0 else None
    except (TypeError, ValueError):
        gateway_ping = None

    # Live Discord API check (public gateway endpoint)
    discord_ok = False
    discord_ms = None
    try:
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{DISCORD_API}/gateway")
        discord_ok = r.status_code == 200
        discord_ms = int((time.perf_counter() - t0) * 1000)
    except Exception:
        pass

    music_raw = data.get("music_status", "disabled")
    if bot_stale and music_raw in ("operational", "disabled", "unknown"):
        music_status = "down"
    else:
        music_status = music_raw if music_raw in ("operational", "degraded", "down", "disabled") else "disabled"
    shard_count = safe_int("num_shards", 1) or 1

    services = [
        {"id": "gateway", "name": "Bot Gateway", "status": "operational" if bot_up else "down",
         "detail": f"Uptime {safe_str('uptime', 'N/A')}" if bot_up else f"No heartbeat · last seen {ago(last_sync)}",
         "latency_ms": gateway_ping},
        {"id": "web", "name": "Web Dashboard & API", "status": "operational",
         "detail": f"v{safe_str('bot_version', '?')} · Python {safe_str('python_version', '?')}", "latency_ms": None},
        {"id": "db", "name": "Database (Neon)", "status": "operational" if db_ok else "down",
         "detail": "PostgreSQL · Neon", "latency_ms": db_ms},
        {"id": "discord", "name": "Discord API", "status": "operational" if discord_ok else "down",
         "detail": f"{shard_count} shard{'s' if shard_count != 1 else ''}", "latency_ms": discord_ms},
        {"id": "music", "name": "Music", "status": music_status,
         "detail": "Audio playback", "latency_ms": None},
    ]

    shards = []
    try:
        raw = data.get("shards")
        if raw:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                shards = [dict(s) for s in parsed]
    except Exception:
        pass

    incidents = []
    try:
        rows_i = await query(
            "SELECT title, body, status, severity, starts_at, resolves_at "
            "FROM incidents ORDER BY starts_at DESC"
        )
        incidents = [
            {
                "title": r["title"], "body": r["body"], "status": r["status"],
                "severity": r["severity"], "starts_at": r["starts_at"],
                "resolves_at": r["resolves_at"],
            }
            for r in rows_i
        ]
    except Exception:
        pass

    requests = []
    try:
        since = int(time.time() // 3600) * 3600 - 23 * 3600
        rows_r = await query(
            "SELECT bucket_ts, count FROM request_stats WHERE bucket_ts >= $1 ORDER BY bucket_ts ASC",
            since,
        )
        by_bucket = {int(r["bucket_ts"]): int(r["count"]) for r in rows_r}
        for i in range(24):
            b = since + i * 3600
            requests.append({"t": b, "count": by_bucket.get(b, 0)})
    except Exception:
        pass

    web_ms = int((time.perf_counter() - t0_all) * 1000)
    for s in services:
        if s["id"] == "web":
            s["latency_ms"] = web_ms

    return {
        "stats": {
            "status": "online" if bot_up else "offline",
            "guilds": safe_int("num_guilds"),
            "users": safe_int("total_users"),
            "active_users": safe_int("active_users"),
            "commands": safe_int("total_commands"),
            "uptime": safe_str("uptime", "N/A"),
            "memory_mb": safe_str("memory_usage_mb", "N/A"),
            "cpu_percent": safe_str("cpu_usage_percent", "N/A"),
            "version": safe_str("bot_version", "unknown"),
            "python_version": safe_str("python_version", "unknown"),
            "shards": safe_int("num_shards"),
            "last_restart": safe_str("last_restart", "unknown"),
            "last_sync": last_sync,
            "stale": bot_stale,
            "downtime": (int(time.time() - last_sync) if bot_stale else None),
        },
        "services": services,
        "shards": shards,
        "incidents": incidents,
        "requests": requests,
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
    "cmd_ban": True, "cmd_kick": True, "cmd_mute": True, "cmd_timeout": True, "cmd_warn": True,
    # ── Modlog ──
    "modlog_channel_id": None,
    # ── Ban ──
    "ban_dm": True, "ban_purge": True, "ban_message": "{username} has been banned.", "ban_message_enabled": True,
    "ban_message_mode": "basic", "ban_embed": {},
    # ── Temp ban ──
    "tempban_dm": True, "tempban_purge": True,
    "tempban_message": "{username} has been temporarily banned.", "tempban_message_enabled": True,
    "tempban_message_mode": "basic", "tempban_embed": {},
    "tempban_duration": 1440,
    # ── Mute ──
    "mute_dm": True, "mute_duration": 60, "mute_message": "{username} has been muted.", "mute_message_enabled": True,
    "mute_message_mode": "basic", "mute_embed": {},
    # ── Kick ──
    "kick_dm": True, "kick_message": "{username} has been kicked.", "kick_message_enabled": True,
    "kick_message_mode": "basic", "kick_embed": {},
    # ── Warn ──
    "warn_dm": True, "warn_message": "{username} has been warned.", "warn_message_enabled": True,
    "warn_message_mode": "basic", "warn_embed": {},
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
              or key.endswith("_channel")
              or key in ("modlog_channel_id", "default_announce_channel_id", "default_ping_role",
                         "channel_id", "auto_role_id", "verified_role_id", "support_role_id",
                         "category_id", "panel_channel_id", "log_channel_id", "panel_message_id"))
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
    # Floats (rates / multipliers)
    if isinstance(default, float):
        try:
            f = float(value)
        except (TypeError, ValueError):
            return None, f"'{key}' must be a number"
        if f < 0:
            return None, f"'{key}' must be positive"
        return f, None
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
    # Custom action embeds are dicts - validate via _sanitize_panel_embed
    if key.endswith("_embed"):
        clean, err = _sanitize_panel_embed(value)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        err = await _save_settings("mod_settings", str(guild_id), key, clean, MOD_SETTINGS_DEFAULTS)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        return {"ok": True}
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
        ACTION_LABELS = {
            "ban": "Banned", "tempban": "Temp-Banned", "unban": "Unbanned",
            "kick": "Kicked", "mute": "Muted", "unmute": "Unmuted", "warn": "Warned",
            "purge": "Purged messages", "lockdown": "Lockdown",
            "verify_panel": "Deployed verification panel",
            "verify_user": "Verified member", "add_role": "Added role",
            "remove_role": "Removed role", "nickname": "Changed nickname",
            "emergency_lock": "Locked down server", "emergency_unlock": "Unlocked server",
            "panel_send": "Deployed ticket panel",
        }
        return {"events": [{
            "user": (f"#{ch_map.get(r['user_name'], r['user_name'])}" if r["action"] == "purge" and r["user_name"].isdigit() else (r["user_name"] if r["user_name"] and r["user_name"] != "0" else r.get("moderator") or "Dashboard")),
            "action": ACTION_LABELS.get(r["action"], r["action"]),
            "reason": r.get("reason", ""),
            "moderator": r.get("moderator") or "",
            "time": _relative_time(r["created_at"]),
            "color": {"ban": "red", "kick": "red", "tempban": "red", "mute": "blue", "unmute": "green", "warn": "yellow", "unban": "green", "purge": "blue", "lockdown": "gray", "verify_panel": "gray", "verify_user": "green", "add_role": "blue", "remove_role": "blue", "nickname": "gray"}.get(r["action"], "gray"),
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


_CAPTCHA_CODES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS captcha_codes (
    code TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    guild_id TEXT DEFAULT '',
    user_id TEXT DEFAULT '',
    created_at DOUBLE PRECISION NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE
);
"""


async def _validate_captcha_code(code: str, provider: str):
    """Check a code is valid (exists, right provider, unused, unexpired) WITHOUT consuming it.
    Returns the guild_id/user_id or None."""
    if not code:
        return None
    try:
        try:
            await execute(_CAPTCHA_CODES_TABLE_SQL)
        except Exception:
            pass
        row = await fetchrow(
            "SELECT used, expires_at, guild_id, user_id FROM captcha_codes WHERE code = $1 AND provider = $2",
            code, provider,
        )
        if not row or row["used"] or time.time() > row["expires_at"]:
            return None
        return {"guild_id": row["guild_id"], "user_id": row["user_id"]}
    except Exception:
        return None


async def _consume_captcha_code(code: str, provider: str):
    """Validate AND mark a code used. Returns guild_id/user_id dict or None."""
    info = await _validate_captcha_code(code, provider)
    if not info:
        return None
    try:
        await execute("UPDATE captcha_codes SET used = TRUE WHERE code = $1", code)
    except Exception:
        return None
    return info


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


_STATS_HISTORY_SQL = """
CREATE TABLE IF NOT EXISTS guild_stats_history (
    guild_id        TEXT NOT NULL,
    day             TEXT NOT NULL,
    member_count    INTEGER NOT NULL DEFAULT 0,
    channel_count   INTEGER NOT NULL DEFAULT 0,
    role_count      INTEGER NOT NULL DEFAULT 0,
    category_count  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, day)
);
"""


@app.get("/api/v1/mod/{guild_id}/stats/daily")
async def mod_stats_daily(guild_id: str, request: Request):
    """Daily snapshot of the 4 server stats + day-over-day % change."""
    await require_guild_access(request, guild_id)
    from datetime import date, timedelta
    try:
        await execute(_STATS_HISTORY_SQL)
    except Exception:
        pass
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    d = d or {}
    members = int(d.get("member_count", 0) or 0)
    channels = sum(1 for c in (d.get("channels") or []) if c.get("type", 0) == 0)
    categories = sum(1 for c in (d.get("channels") or []) if c.get("type", 0) == 4)
    roles = len(d.get("roles", []) or [])
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    try:
        await execute(
            "INSERT INTO guild_stats_history (guild_id, day, member_count, channel_count, role_count, category_count) "
            "VALUES ($1, $2, $3, $4, $5, $6) "
            "ON CONFLICT (guild_id, day) DO UPDATE SET "
            "member_count = EXCLUDED.member_count, channel_count = EXCLUDED.channel_count, "
            "role_count = EXCLUDED.role_count, category_count = EXCLUDED.category_count",
            str(guild_id), today, members, channels, roles, categories,
        )
    except Exception:
        pass
    prev = None
    try:
        yrow = await fetchrow(
            "SELECT member_count, channel_count, role_count, category_count "
            "FROM guild_stats_history WHERE guild_id = $1 AND day = $2",
            str(guild_id), yesterday,
        )
        prev = dict(yrow) if yrow else None
    except Exception:
        pass

    def pct(cur, p):
        if p is None or p <= 0:
            return None
        return round((cur - p) / p * 100, 1)

    return {
        "today": {"members": members, "channels": channels, "roles": roles, "categories": categories},
        "yesterday": prev,
        "pct": {
            "members": pct(members, prev["member_count"] if prev else None),
            "channels": pct(channels, prev["channel_count"] if prev else None),
            "roles": pct(roles, prev["role_count"] if prev else None),
            "categories": pct(categories, prev["category_count"] if prev else None),
        },
    }


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
#  Leveling API v1
# ---------------------------------------------------------------------------

LEVELING_DEFAULTS = {
    "enabled": True,
    "announce_channel_id": None,
    "xp_rate": 1.0,
    "xp_cooldown": 60,
    "random_xp": True,
    "xp_per_message_min": 15,
    "xp_per_message_max": 25,
    "role_xp_multipliers": {},
    "level_roles": {},
    "level_up_message": "🎉 {user} reached **level {level}**!",
    "level_up_message_mode": "basic", "level_up_embed": {},
}


async def _get_leveling_settings(guild_id: str):
    row = await fetchrow("SELECT settings FROM leveling_settings WHERE guild_id = $1", str(guild_id))
    if row:
        settings = row["settings"]
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except (json.JSONDecodeError, TypeError):
                return dict(LEVELING_DEFAULTS)
        if isinstance(settings, dict):
            return {**LEVELING_DEFAULTS, **settings}
    return dict(LEVELING_DEFAULTS)


def _sanitize_role_multipliers(value):
    """Validate role_xp_multipliers: dict of {role_id(snowflake): float>=0}."""
    if not isinstance(value, dict):
        return None, "role_xp_multipliers must be an object"
    if len(value) > 50:
        return None, "too many role multipliers (max 50)"
    clean = {}
    for role_id, mult in value.items():
        if not _valid_snowflake(role_id):
            return None, f"role '{role_id}' is not a valid Discord ID"
        try:
            f = float(mult)
        except (TypeError, ValueError):
            return None, f"multiplier for role '{role_id}' must be a number"
        if f < 0:
            return None, f"multiplier for role '{role_id}' must be 0 or higher"
        clean[str(role_id)] = round(f, 2)
    return clean, None


def _sanitize_level_roles(value):
    """Validate level_roles: dict of {level(str/int): role_id(snowflake)}."""
    if not isinstance(value, dict):
        return None, "level_roles must be an object"
    if len(value) > 50:
        return None, "too many level roles (max 50)"
    clean = {}
    for level, role_id in value.items():
        try:
            lvl = int(level)
        except (TypeError, ValueError):
            return None, f"level '{level}' must be an integer"
        if lvl < 1:
            return None, "levels must be 1 or higher"
        if not _valid_snowflake(role_id):
            return None, f"role for level {lvl} must be a valid Discord ID"
        clean[str(lvl)] = str(role_id)
    return clean, None


@app.get("/api/v1/leveling/{guild_id}/settings")
async def leveling_settings(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    return {"settings": await _get_leveling_settings(guild_id)}


@app.post("/api/v1/leveling/{guild_id}/settings")
async def leveling_settings_set(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    key = body.get("key")
    value = body.get("value")
    if not key:
        return JSONResponse({"error": "missing key"}, status_code=400)
    if key == "level_roles":
        clean, err = _sanitize_level_roles(value)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        err = await _save_settings("leveling_settings", str(guild_id), key, clean, LEVELING_DEFAULTS)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        return {"ok": True}
    if key == "role_xp_multipliers":
        clean, err = _sanitize_role_multipliers(value)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        err = await _save_settings("leveling_settings", str(guild_id), key, clean, LEVELING_DEFAULTS)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        return {"ok": True}
    if key == "level_up_embed":
        clean, err = _sanitize_panel_embed(value)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        err = await _save_settings("leveling_settings", str(guild_id), key, clean, LEVELING_DEFAULTS)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        return {"ok": True}
    err = await _save_settings("leveling_settings", str(guild_id), key, value, LEVELING_DEFAULTS)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    return {"ok": True}


@app.get("/api/v1/leveling/{guild_id}/leaderboard")
async def leveling_leaderboard(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    rows = await query(
        "SELECT user_id, xp FROM leveling_data WHERE guild_id = $1 ORDER BY xp DESC LIMIT 50",
        str(guild_id),
    )
    if not rows:
        return {"members": []}
    # Join with cached member data for names/avatars
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    by_id = {}
    if d and "members" in d:
        for m in d["members"]:
            av = m.get("avatar_url") or m.get("avatar")
            if av and not str(av).startswith("http"):
                av = f"https://cdn.discordapp.com/avatars/{m.get('id')}/{av}.png?size=64"
            by_id[str(m.get("id"))] = {
                "name": m.get("name", ""), "display_name": m.get("display_name", ""),
                "avatar_url": av or None,
            }

    def xp_for_level(lvl: int) -> int:
        return 100 * lvl + 50 * (lvl - 1)

    def level_from_xp(xp: int) -> int:
        lvl = 1
        while xp_for_level(lvl + 1) <= xp:
            lvl += 1
        return lvl

    members = []
    for r in rows:
        uid = str(r["user_id"])
        meta = by_id.get(uid, {})
        xp = int(r["xp"] or 0)
        level = level_from_xp(xp)
        members.append({
            "id": uid, "name": meta.get("name") or uid, "display_name": meta.get("display_name", ""),
            "avatar_url": meta.get("avatar_url"),
            "xp": xp, "level": level,
            "xp_next": xp_for_level(level + 1) - xp_for_level(level),
        })
    return {"members": members}


@app.get("/api/v1/leveling/{guild_id}/channels")
async def leveling_channels(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "channels" in d:
        return {"channels": [{"id": str(c.get("id")), "name": c.get("name", "")} for c in d["channels"] if c.get("type", 0) == 0]}
    return {"channels": [{"id": "2001", "name": "general"}]}


@app.get("/api/v1/leveling/{guild_id}/roles")
async def leveling_roles(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    roles = d.get("roles", []) if d else []
    if row and isinstance(row["data"], dict) and "roles" in row["data"]:
        roles = row["data"]["roles"]
    result = []
    for r in roles:
        if str(r.get("id", "")) == str(guild_id):
            continue
        tags = r.get("tags")
        if isinstance(tags, dict) and tags.get("bot_id"):
            continue
        if r.get("managed", False):
            continue
        result.append({"id": str(r.get("id")), "name": r.get("name", ""), "color": r.get("color", 0), "position": r.get("position", 0), "count": r.get("count") or r.get("member_count") or 0})
    result.sort(key=lambda x: x["position"], reverse=True)
    if not result:
        result = [
            {"id": "4005", "name": "VIP", "color": 0, "position": 1, "count": 15},
            {"id": "4006", "name": "Member", "color": 0, "position": 0, "count": 120},
        ]
    return {"roles": result}


# ---------------------------------------------------------------------------
#  Logging API v1
# ---------------------------------------------------------------------------

LOGGING_DEFAULTS = {
    "message_delete_channel": None,
    "message_edit_channel": None,
    "member_join_channel": None,
    "member_leave_channel": None,
    "member_ban_channel": None,
    "member_unban_channel": None,
    "nickname_channel": None,
    "member_roles_channel": None,
    "member_mute_channel": None,
    "channel_create_channel": None,
    "channel_delete_channel": None,
    "channel_update_channel": None,
    "role_create_channel": None,
    "role_delete_channel": None,
    "role_update_channel": None,
    "server_update_channel": None,
    "emoji_update_channel": None,
    "invite_create_channel": None,
    "voice_channel": None,
}


async def _get_logging_settings(guild_id: str):
    row = await fetchrow("SELECT settings FROM logging_settings WHERE guild_id = $1", str(guild_id))
    if row:
        settings = row["settings"]
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except (json.JSONDecodeError, TypeError):
                return dict(LOGGING_DEFAULTS)
        if isinstance(settings, dict):
            return {**LOGGING_DEFAULTS, **settings}
    return dict(LOGGING_DEFAULTS)


@app.get("/api/v1/logging/{guild_id}/settings")
async def logging_settings_get(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    return {"settings": await _get_logging_settings(guild_id)}


@app.post("/api/v1/logging/{guild_id}/settings")
async def logging_settings_set(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    key = body.get("key")
    value = body.get("value")
    if not key:
        return JSONResponse({"error": "missing key"}, status_code=400)
    err = await _save_settings("logging_settings", str(guild_id), key, value, LOGGING_DEFAULTS)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    return {"ok": True}


@app.get("/api/v1/logging/{guild_id}/channels")
async def logging_channels(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "channels" in d:
        return {"channels": [{"id": str(c.get("id")), "name": c.get("name", "")} for c in d["channels"] if c.get("type", 0) == 0]}
    return {"channels": [{"id": "2001", "name": "general"}]}


# ---------------------------------------------------------------------------
#  AutoMod API v1
# ---------------------------------------------------------------------------

AUTOMOD_DEFAULTS = {
    "enabled": False,
    "moderation_channel_id": None,
    "filter_mute_minutes": 60,
    "profanity_enabled": True,
    "profanity_action": "delete",
    "profanity_words": "",
    "spam_enabled": True,
    "spam_action": "delete",
    "spam_messages": 5,
    "spam_window": 5,
    "links_enabled": False,
    "links_action": "delete",
    "links_allowlist": "",
    "caps_enabled": False,
    "caps_action": "delete",
    "caps_percent": 70,
    "caps_min_chars": 6,
    "mentions_enabled": False,
    "mentions_action": "delete",
    "mentions_max": 5,
    "invites_enabled": False,
    "invites_action": "delete",
    "zalgo_enabled": False,
    "zalgo_action": "delete",
    "emoji_enabled": False,
    "emoji_action": "delete",
    "emoji_max": 10,
    "action_configs": {},
}

AUTOMOD_ACTIONS = ("delete", "delete_dm", "warn", "warn_dm", "mute", "mute_dm", "kick", "kick_dm", "ban", "ban_dm")
AUTOMOD_FILTERS = ("profanity", "spam", "links", "caps", "mentions", "invites", "zalgo", "emoji")


def _sanitize_action_configs(value):
    """Validate action_configs: dict of {filter: {warn_message, mute_minutes, kick_message, ban_message, ban_days}}."""
    if not isinstance(value, dict):
        return None, "action_configs must be an object"
    clean = {}
    for fk, cfg in value.items():
        if fk not in AUTOMOD_FILTERS:
            continue
        if not isinstance(cfg, dict):
            continue
        c = {}
        for k, v in cfg.items():
            if k in ("warn_message", "kick_message", "ban_message") and isinstance(v, str) and v.strip():
                c[k] = v[:500]
            elif k in ("warn_mode", "kick_mode", "ban_mode") and v in ("basic", "custom"):
                c[k] = v
            elif k in ("warn_embed", "kick_embed", "ban_embed"):
                clean_embed, err = _sanitize_panel_embed(v)
                if not err:
                    c[k] = clean_embed
            elif k == "mute_minutes":
                try:
                    c[k] = max(1, int(v))
                except (TypeError, ValueError):
                    pass
            elif k == "ban_days":
                try:
                    c[k] = max(0, min(7, int(v)))
                except (TypeError, ValueError):
                    pass
        clean[fk] = c
    return clean, None


async def _get_automod_settings(guild_id: str):
    row = await fetchrow("SELECT settings FROM automod_settings WHERE guild_id = $1", str(guild_id))
    if row:
        settings = row["settings"]
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except (json.JSONDecodeError, TypeError):
                return dict(AUTOMOD_DEFAULTS)
        if isinstance(settings, dict):
            return {**AUTOMOD_DEFAULTS, **settings}
    return dict(AUTOMOD_DEFAULTS)


@app.get("/api/v1/automod/{guild_id}/settings")
async def automod_settings_get(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    return {"settings": await _get_automod_settings(guild_id)}


@app.post("/api/v1/automod/{guild_id}/settings")
async def automod_settings_set(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    key = body.get("key")
    value = body.get("value")
    if not key:
        return JSONResponse({"error": "missing key"}, status_code=400)
    if key.endswith("_action") and value not in AUTOMOD_ACTIONS:
        return JSONResponse({"error": "invalid action"}, status_code=400)
    if key == "action_configs":
        clean, err = _sanitize_action_configs(value)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        err = await _save_settings("automod_settings", str(guild_id), key, clean, AUTOMOD_DEFAULTS)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        return {"ok": True}
    err = await _save_settings("automod_settings", str(guild_id), key, value, AUTOMOD_DEFAULTS)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    return {"ok": True}


@app.get("/api/v1/automod/{guild_id}/channels")
async def automod_channels(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "channels" in d:
        return {"channels": [{"id": str(c.get("id")), "name": c.get("name", "")} for c in d["channels"] if c.get("type", 0) == 0]}
    return {"channels": [{"id": "2001", "name": "general"}]}


# ---------------------------------------------------------------------------
#  Raid Protection API v1
# ---------------------------------------------------------------------------

RAID_DEFAULTS = {
    "enabled": False,
    "join_threshold": 5,
    "join_window": 10,
    "join_action": "kick",
    "account_age_min": 0,
    "account_age_action": "kick",
    "auto_recovery": True,
    "recovery_minutes": 30,
    "moderation_channel_id": None,
}

RAID_ACTIONS = ("kick", "ban", "lockdown", "verify")


async def _get_raid_settings(guild_id: str):
    row = await fetchrow("SELECT settings FROM raid_settings WHERE guild_id = $1", str(guild_id))
    if row:
        settings = row["settings"]
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except (json.JSONDecodeError, TypeError):
                return dict(RAID_DEFAULTS)
        if isinstance(settings, dict):
            return {**RAID_DEFAULTS, **settings}
    return dict(RAID_DEFAULTS)


@app.get("/api/v1/raid/{guild_id}/settings")
async def raid_settings_get(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    return {"settings": await _get_raid_settings(guild_id)}


@app.post("/api/v1/raid/{guild_id}/settings")
async def raid_settings_set(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    key = body.get("key")
    value = body.get("value")
    if not key:
        return JSONResponse({"error": "missing key"}, status_code=400)
    if key.endswith("_action") and value not in RAID_ACTIONS:
        return JSONResponse({"error": "invalid action"}, status_code=400)
    err = await _save_settings("raid_settings", str(guild_id), key, value, RAID_DEFAULTS)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    return {"ok": True}


@app.get("/api/v1/raid/{guild_id}/channels")
async def raid_channels(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "channels" in d:
        return {"channels": [{"id": str(c.get("id")), "name": c.get("name", "")} for c in d["channels"] if c.get("type", 0) == 0]}
    return {"channels": [{"id": "2001", "name": "general"}]}


# ---------------------------------------------------------------------------
#  Welcomer API v1
# ---------------------------------------------------------------------------

WELCOME_DEFAULTS = {
    "enabled": False,
    "channel_id": None,
    "welcome_message": "Welcome {member} to {server}!",
    "goodbye_message": "{member} has left {server}.",
    "welcome_dm": False,
    "welcome_dm_message": "Welcome to **{server}**! Make sure to read the rules.",
    "auto_role_id": None,
    "welcome_embed": True,
    "goodbye_embed": True,
}


async def _get_welcome_settings(guild_id: str):
    row = await fetchrow("SELECT settings FROM welcome_settings WHERE guild_id = $1", str(guild_id))
    if row:
        settings = row["settings"]
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except (json.JSONDecodeError, TypeError):
                return dict(WELCOME_DEFAULTS)
        if isinstance(settings, dict):
            return {**WELCOME_DEFAULTS, **settings}
    return dict(WELCOME_DEFAULTS)


@app.get("/api/v1/welcomer/{guild_id}/settings")
async def welcomer_settings_get(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    return {"settings": await _get_welcome_settings(guild_id)}


@app.post("/api/v1/welcomer/{guild_id}/settings")
async def welcomer_settings_set(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    key = body.get("key")
    value = body.get("value")
    if not key:
        return JSONResponse({"error": "missing key"}, status_code=400)
    err = await _save_settings("welcome_settings", str(guild_id), key, value, WELCOME_DEFAULTS)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    return {"ok": True}


@app.get("/api/v1/welcomer/{guild_id}/channels")
async def welcomer_channels(guild_id: str, request: Request):
    """Text channels for the welcome channel dropdown."""
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "channels" in d:
        return {"channels": [{"id": str(c.get("id")), "name": c.get("name", "")} for c in d["channels"] if c.get("type", 0) == 0]}
    return {"channels": []}


@app.get("/api/v1/welcomer/{guild_id}/roles")
async def welcomer_roles(guild_id: str, request: Request):
    """All roles for the auto-role dropdown."""
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "roles" in d:
        return {"roles": [{"id": str(r.get("id")), "name": r.get("name", "")} for r in d["roles"]]}
    return {"roles": []}


# ---------------------------------------------------------------------------
#  Autoresponder API v1
# ---------------------------------------------------------------------------

@app.get("/api/v1/autoresponder/{guild_id}/triggers")
async def autoresponder_triggers(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    rows = await query(
        "SELECT id, trigger, response, match_type, channel_id, cooldown FROM autoresponder WHERE guild_id = $1 ORDER BY created_at ASC",
        str(guild_id),
    )
    if not rows:
        return {"triggers": []}
    return {"triggers": [dict(r) for r in rows]}


@app.get("/api/v1/autoresponder/{guild_id}/channels")
async def autoresponder_channels(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    row = await fetchrow("SELECT data FROM guild_data WHERE guild_id = $1", str(guild_id))
    d = _parse_guild_data(row)
    if d and "channels" in d:
        return {"channels": [{"id": str(c.get("id")), "name": c.get("name", "")} for c in d["channels"] if c.get("type", 0) == 0]}
    return {"channels": [{"id": "2001", "name": "general"}]}


@app.post("/api/v1/autoresponder/{guild_id}/triggers")
async def autoresponder_trigger_add(guild_id: str, request: Request):
    await require_guild_access(request, guild_id)
    body = await request.json()
    trigger = (body.get("trigger") or "").strip()
    response = (body.get("response") or "").strip()
    match_type = body.get("match_type") or "contains"
    channel_id = body.get("channel_id") or None
    cooldown = body.get("cooldown") or 0
    if not trigger or not response:
        return JSONResponse({"error": "trigger and response are required"}, status_code=400)
    if len(trigger) > 300:
        return JSONResponse({"error": "trigger is too long (max 300 chars)"}, status_code=400)
    if len(response) > 2000:
        return JSONResponse({"error": "response is too long (max 2000 chars)"}, status_code=400)
    if match_type not in ("contains", "exact", "starts_with", "ends_with", "regex"):
        return JSONResponse({"error": "invalid match_type"}, status_code=400)
    if channel_id is not None and not _valid_snowflake(channel_id):
        return JSONResponse({"error": "channel must be a valid Discord ID or null"}, status_code=400)
    try:
        cooldown = max(0, int(cooldown))
    except (TypeError, ValueError):
        return JSONResponse({"error": "cooldown must be an integer (seconds)"}, status_code=400)
    existing = await query(
        "SELECT id FROM autoresponder WHERE guild_id = $1 AND lower(trigger) = lower($2) AND match_type = $3",
        str(guild_id), trigger, match_type,
    )
    if existing:
        return JSONResponse({"error": "A trigger with this text and match type already exists."}, status_code=400)
    r = await query(
        "INSERT INTO autoresponder (guild_id, trigger, response, match_type, channel_id, cooldown) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id, trigger, response, match_type, channel_id, cooldown",
        str(guild_id), trigger, response, match_type, channel_id, cooldown,
    )
    return {"ok": True, "trigger": dict(r[0]) if r else None}


@app.delete("/api/v1/autoresponder/{guild_id}/triggers/{trigger_id}")
async def autoresponder_trigger_remove(guild_id: str, trigger_id: str, request: Request):
    await require_guild_access(request, guild_id)
    try:
        tid = int(trigger_id)
    except (TypeError, ValueError):
        return JSONResponse({"error": "invalid trigger id"}, status_code=400)
    await execute("DELETE FROM autoresponder WHERE guild_id = $1 AND id = $2", str(guild_id), tid)
    return {"ok": True}


# ---------------------------------------------------------------------------
#  Social Alerts API v1
# ---------------------------------------------------------------------------

SOCIAL_SETTINGS_DEFAULTS = {
    "enabled": True,
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
    # Bot-owner defaults from .env - server owners don't need their own keys.
    "recaptcha_site_key": os.environ.get("RECAPTCHA_SITE_KEY", ""),
    "recaptcha_secret": "",
    "panel_embed": {}, "panel_message_id": None,
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
    # Disabling verification should also remove the deployed panel
    if key == "enabled" and not value:
        await _queue_action(str(guild_id), "verify_panel_remove", "0", "", "Verification disabled - panel removed", None)
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


@app.get("/verify/{guild_id}", response_class=HTMLResponse)
async def verify_page(guild_id: str, request: Request):
    """Public verification page that renders the reCAPTCHA / Turnstile widget."""
    settings = await _get_verify_settings(guild_id)
    provider = settings.get("type", "")
    if not settings.get("enabled") or provider != "recaptcha":
        return HTMLResponse("This server doesn't use link-based verification.", status_code=400)
    site_key = settings.get(f"{provider}_site_key", "")
    user_id = request.query_params.get("u", "")
    return templates.TemplateResponse(request, "verify.html", {
        "guild_id": guild_id,
        "provider": provider,
        "site_key": site_key,
        "user_id": user_id,
    })


@app.post("/api/v1/verify/{guild_id}/complete")
async def verify_complete(guild_id: str, request: Request):
    """Verify a captcha token and queue the bot to assign the verified role."""
    body = await request.json()
    token = body.get("token", "")
    user_id = body.get("user_id", "")
    provider = body.get("provider", "")
    if not token or not user_id or provider != "recaptcha":
        return JSONResponse({"error": "invalid request"}, status_code=400)
    settings = await _get_verify_settings(guild_id)
    if not settings.get("enabled") or settings.get("type") != provider:
        return JSONResponse({"error": "verification not configured for this method"}, status_code=400)
    secret = os.environ.get(f"{provider.upper()}_SECRET", "") or settings.get(f"{provider}_secret", "")
    if not secret:
        return JSONResponse({"error": "captcha secret not configured"}, status_code=400)

    verify_url = "https://www.google.com/recaptcha/api/siteverify"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(verify_url, data={"secret": secret, "response": token})
            data = r.json()
    except Exception as e:
        return JSONResponse({"error": f"verify failed: {e}"}, status_code=500)

    if not data.get("success"):
        return JSONResponse({"error": "captcha verification failed"}, status_code=400)

    await _queue_action(guild_id, "verify_user", user_id, "", "Verified via " + provider, None)
    return {"ok": True, "queued": True}


@app.post("/api/v1/captcha/complete")
async def captcha_complete(request: Request):
    """Auto-verify a user after they solve the captcha on the web page (no token copying)."""
    raw = await request.body()
    print(f"[CAPTCHA] hit /complete, raw body bytes={len(raw)}: {raw[:200]!r}")
    body = await request.json()
    token = body.get("token", "")
    code = body.get("code", "")
    provider = body.get("provider", "")
    if not token or not code or provider != "recaptcha":
        print(f"[CAPTCHA] invalid request: token_len={len(token)} code={code!r} provider={provider!r}")
        return JSONResponse({"error": "invalid request"}, status_code=400)
    info = await _consume_captcha_code(code, provider)
    if not info or not info.get("guild_id") or not info.get("user_id"):
        print(f"[CAPTCHA] code invalid/expired/used: code={code!r}")
        return JSONResponse({"error": "verification link expired or already used"}, status_code=403)

    settings = await _get_verify_settings(info["guild_id"])
    secret = os.environ.get(f"{provider.upper()}_SECRET", "") or settings.get(f"{provider}_secret", "")
    if not secret:
        print(f"[CAPTCHA] missing {provider.upper()}_SECRET for guild {info['guild_id']}")
        return JSONResponse({"error": "captcha secret not configured"}, status_code=400)

    verify_url = "https://www.google.com/recaptcha/api/siteverify"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(verify_url, data={"secret": secret, "response": token})
            data = r.json()
    except Exception as e:
        return JSONResponse({"error": f"verify failed: {e}"}, status_code=500)

    if not data.get("success"):
        codes = ", ".join(data.get("error-codes", []))
        print(f"[CAPTCHA] siteverify failed: {codes}")
        return JSONResponse({"error": f"captcha verification failed ({codes})"}, status_code=400)

    await _queue_action(info["guild_id"], "verify_user", info["user_id"], "", "Verified via " + provider, None)
    return {"ok": True, "queued": True}


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
