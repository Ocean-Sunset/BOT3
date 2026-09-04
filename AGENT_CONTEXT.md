# Prowl Bot — Agent Context (Read This First)

## Quick Start
This file exists so the next agent session knows the full state of the project. READ THIS before doing anything.

## Project Overview
Prowl is a Discord bot (Python/discord.py 2.7.x) with a web dashboard (FastAPI + Turso/libSQL). 
- Bot entry: `cli/start.py` (ProwlBot class, 21+ cogs)
- Website: `website/api/index.py` (FastAPI app), `website/api/db.py` (Turso DB wrapper)
- All commands are slash commands (`@app_commands.command`)
- To call command callbacks in tests: `_cmd(self.cog.method)(self.cog, interaction)`

## Critical Gotchas

### Turso returns ALL values as strings
- `fetchval("SELECT COUNT(*) ...")` returns `"7"` not `7`
- Always wrap in `int()` / `float()` before math/comparison
- Mitigation exists in `_unwrap_cell` in `db.py` but still use manual `int()` as defense

### execute() silently swallows errors
- `execute()` in `website/api/db.py` returns `None` on failure, never raises
- Check return value: `result = await execute(...)` then `if result is None: ...`
- This caused request_stats table to never get created (fallback never fired)

### Bot-server communication
- Website talks to bot via HTTP bridge: `cli/Ediscord/http_bridge.py`
- `BOT_SERVER_URL` and `BOT_HTTP_TOKEN` env vars required
- Direct actions (instant toast): check `_call_bot_direct()` in `index.py`
- `DIRECT_ACTIONS` lists in both `http_bridge.py` and `index.py`

### Settings tables pattern
- All settings tables: `guild_id TEXT PRIMARY KEY, settings TEXT NOT NULL DEFAULT '{}', updated_at REAL NOT NULL`
- The `updated_at` is NOT NULL without DEFAULT — INSERT statements MUST include it
- `_save_settings()` in `index.py` handles this

### Embed/Color system
- BRAND=0x8B5CF6 (violet), SUCCESS=0x22C55E, ERROR=0xEF4444, WARN=0xF59E0B, INFO=0x3B82F6
- `EMBED_EMOJIS` dict in `cli/Ediscord/builders.py` has all icon names
- `EmbedBuilder.row(*fields, columns=2)` for 2-column inline grid

### Ephemeral follow-up rule
- After ephemeral response, follow-up MUST be `ephemeral=True`
- OR send via `interaction.channel.send(...)` for public announcements

### Windows environment
- Python 3.9 at `C:\Program Files (x86)\Microsoft Visual Studio\Shared\Python39_64\python.exe`
- Use `;` not `&&`, no `head` command
- Tests: `python -m cli.test_all_commands` (135 tests, all passing)

## Repo State (as of last session)
- Branch: `website` (all development here)
- `main` branch has older code, `deploy-bot` is single deployment commit
- CSS versions: index.css?v=14, dashboard.css?v=27, status.css?v=8
- 135 tests passing in `cli/test_all_commands.py`
- Features roadmap: `FEATURES.md`

## Current Feature: Birthday Tracking (COMPLETE)
Birthday tracking feature has been fully implemented:

### Files Created/Modified
- `cli/components/birthday.py` — New cog with commands + background loop
- `website/api/setup_schema.py` — Added `birthday_settings` and `birthdays` tables
- `website/api/index.py` — Added API endpoints + valid_panels entry
- `website/templates/dashboard/birthday.html` — New dashboard page
- `website/templates/dashboard/base.html` — Added nav link + mobile tab
- `cli/Ediscord/db.py` — Added tables to GUILD_TABLES for cleanup

### Bot Commands
- `/birthday set <month> <day> [year]` — Set your birthday
- `/birthday remove` — Remove your birthday
- `/birthday list` — List all birthdays in server
- `/birthday upcoming` — Show next 7 days of birthdays
- Background loop: posts daily at midnight UTC, assigns birthday role

### Dashboard Features
- Enable/disable toggle
- Channel selector for announcements
- Role selector for birthday role
- Message template with {member}, {name}, {server}, {age} variables
- Show birth year toggle
- Live preview

### API Endpoints
- `GET /api/v1/birthday/{guild_id}/settings`
- `POST /api/v1/birthday/{guild_id}/settings`
- `GET /api/v1/birthday/{guild_id}/birthdays`
- `GET /api/v1/birthday/{guild_id}/channels`
- `GET /api/v1/birthday/{guild_id}/roles`

### Next Steps (User Decides)
- Test the feature
- Run `python website/api/setup_schema.py` on live DB
- Commit changes

## Useful Patterns to Follow

### Adding a new cog
1. Create `cli/components/birthday.py` with `class Birthday(commands.Cog)`
2. Cogs auto-load via `COGS_DIR.glob("*.py")` in `start.py`
3. Add API endpoints in `index.py` following existing patterns
4. Add to `GUILD_TABLES` in `cli/Ediscord/db.py` for cleanup

### Adding a new dashboard page
1. Create `website/templates/dashboard/birthday.html` extending `base.html`
2. Add to `valid_panels` list in `index.py`
3. Add nav link in `base.html` sidebar + mobile tab bar

### Adding DB tables
1. Add to `website/api/setup_schema.py` SCHEMA string
2. Add table name to `_TABLE_NAMES` if it needs cache invalidation
3. Run `python website/api/setup_schema.py` on live DB

## File Reference
- `cli/start.py` — ProwlBot class, cog loading, `on_message` override
- `cli/Ediscord/builders.py` — EmbedBuilder, EMBED_EMOJIS, brand colors
- `cli/Ediscord/db.py` — DB helpers, `_unwrap_cell` type coercion
- `cli/Ediscord/http_bridge.py` — Bot HTTP server, DIRECT_ACTIONS, action_stats
- `cli/Ediscord/cache.py` — AsyncTTLCache, settings_cache
- `website/api/index.py` — All API routes, _save_settings, _call_bot_direct
- `website/api/db.py` — execute(), query(), fetchval(), fetchrow()
- `website/api/setup_schema.py` — DB schema setup script
- `website/templates/dashboard/base.html` — Dashboard layout, nav, mobile tab bar
- `website/static/dashboard.css` — Dashboard styles
- `website/static/index.css` — Landing page styles (v14)
