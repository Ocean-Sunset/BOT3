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

## Current Features

### Birthday Tracking (COMPLETE)
- `cli/components/birthday.py` — Commands + daily loop + 24h role removal + Basic/Custom message modes
- Dashboard with channel/role selectors, message template, embed editor
- API: GET/POST settings, GET birthdays, channels, roles

### Activity Roles (COMPLETE)
- `cli/components/activity_roles.py` — Auto-assign roles based on game/activity
- Monitors `on_presence_update` for playing activity changes
- DB: `activity_role_rules` table
- Commands: `/activityrole add`, `/remove`, `/list`
- Dashboard with rule management

### Badges (COMPLETE)
- `cli/components/badges.py` — Achievement badge system with VC tracking
- 20 badges across 4 categories: messages, voice, tenure, special
- VC time tracking via `on_voice_state_update` (in-memory sessions, flushed to DB)
- Badge checking triggered from leveling cog's `on_message`
- Commands: `/badges`, `/badges @user`, `/badgesboard`
- DB: `user_activity`, `user_badges` tables
- Dashboard showing badge categories + leaderboard

### Temp Channels (COMPLETE)
- `cli/components/temp_channels.py` — JTC voice + timed text channels
- **JTC Voice:** Join hub → auto-create voice channel → owner controls → auto-delete when empty
- **Temp Chat:** `/tempchat [minutes] [name]` → auto-deletes after duration
- Commands: `/tempchat`, `/tempchat_close`, `/tempchat_list`
- DB: `temp_channel_settings`, `temp_channels` tables
- Dashboard with JTC and temp chat configuration

### Frenzy Mode (COMPLETE)
- `cli/components/frenzy.py` — XP multiplier system with auto-triggers
- **Manual trigger:** `/frenzy start [multiplier] [duration] [reason]` / `/frenzy stop`
- **Auto-triggers:** Member join spike, message spike, voice activity, boost, level milestone
- **Duration:** Time-limited or until manually stopped
- **Multipliers:** Configurable (default 2x, max 10x)
- **Announcements:** Optional start/end messages
- DB: `frenzy_settings`, `frenzy_active` tables
- Dashboard with quick start, general settings, and auto-trigger configuration
- Hooked into leveling cog's XP calculation

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
- `cli/Ediscord/db.py` — DB helpers, `_unwrap_cell` type coercion, GUILD_TABLES
- `cli/Ediscord/http_bridge.py` — Bot HTTP server, DIRECT_ACTIONS, action_stats
- `cli/Ediscord/cache.py` — AsyncTTLCache, settings_cache
- `cli/components/birthday.py` — Birthday tracking cog
- `cli/components/activity_roles.py` — Activity-based role assignment
- `cli/components/badges.py` — Badge system with VC tracking
- `cli/components/temp_channels.py` — JTC voice + temp text channels
- `cli/components/frenzy.py` — XP frenzy mode with auto-triggers
- `cli/components/leveling.py` — XP/leveling (hooks into badge tracking, frenzy multiplier)
- `website/api/index.py` — All API routes, _save_settings, valid_panels
- `website/api/db.py` — execute(), query(), fetchval(), fetchrow()
- `website/api/setup_schema.py` — DB schema setup script
- `website/templates/dashboard/base.html` — Dashboard layout, nav, mobile tab bar
- `website/templates/dashboard/activity_roles.html` — Activity roles dashboard
- `website/templates/dashboard/badges.html` — Badges dashboard
- `website/static/dashboard.css` — Dashboard styles
- `website/static/moderation.css` — Shared dashboard component styles
