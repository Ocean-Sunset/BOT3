# Prowl — Developer / AI Agent Guide

Read this before making ANY change. It exists because past AI sessions kept
repeating the same mistakes.

## Repo layout
- `cli/` — the Discord bot (Python, discord.py). Deployed to the bot server
  (hidencloud) via the auto-built `deploy-bot` branch (see GitHub Action
  `.github/workflows/deploy-bot.yml`, rebuilds from `cli/**`).
- `website/` — the dashboard + API (FastAPI, deployed to Vercel from the
  `website` branch root, `website/` folder).

## Git rules
- **Always work on and push to the `website` branch. NEVER touch `main`.**
- Vercel deploys `website`. The `deploy-bot` branch is generated — never
  commit to it directly, never point the website at it.
- Commit message: single line, imperative, describe what + why.
- **Never commit `.env` / `.env.local` / any secrets.** They are gitignored.
- After touching `cli/**`, the deploy-bot Action rebuilds automatically —
  mention to the user that the bot server needs to pull the new build.

## The #1 recurring bug: CSS cache-busting
Every template links CSS with `?v=N` (e.g. `/static/automod.css?v=2`).
**When you edit a CSS file, you MUST bump the `?v=` number in every template
that references it**, or users keep seeing the old cached CSS and report the
bug as "not fixed". Same applies to JS embedded in templates if you rely on a
versioned static file.

## The #2 recurring bug: save-bar discard logic
Dashboard pages use a pending/original/LOADED/SETTINGS_SNAPSHOT pattern:

- `markChanged(key, value)` stores `original[key]` (the value when first
  edited), sets `pending[key]`, mutates `SETTINGS_SNAPSHOT[key]`, shows the
  save bar.
- **On save: you MUST `delete original[key]` in addition to updating
  `LOADED[key]` and clearing `pending[key]`.** If you leave stale entries in
  `original`, then edit→save→edit→discard reverts to the pre-save value
  instead of the saved one.
- **On discard:** rebuild the state from `LOADED`, overlay `original` for
  keys still in `pending`, then re-render the UI from that state. Do NOT
  fall back to default values (`None`, `delete`, etc.) — read the snapshot.
- `LOADED` = state as loaded from server, never mutated except on save.

## Custom dropdowns
`.md-custom-select` dropdowns are absolutely positioned — they do NOT push
layout. **Never bind the same dropdown twice.** A classic bug: a generic
`bindSelects()` that selects `.lg-select .md-custom-select-btn` also catches
a special "everything" dropdown, so two click handlers toggle the menu twice
and it never opens. If a dropdown has custom behavior, exclude it from the
generic binder (check by `id` / `closest(...)`).

## API + settings conventions
- Guild settings live in per-feature tables (`*_settings(guild_id, settings
  JSONB, updated_at)`). Add new tables to `website/api/setup_schema.py` AND
  run `cd website && python api/setup_schema.py` to apply.
- `_save_settings(table, guild_id, key, value, defaults)` + `_sanitize_setting`
  handle validation. Snowflake/channel keys must end in `_channel`, `_channel_id`,
  `_id` or `_role` (see `id_key` in `_sanitize_setting`) — add new suffixes there.
- Complex dict values (embed, level_roles, action_configs, ...) are validated
  in the POST endpoint with a dedicated `_sanitize_*` function.
- API endpoints: `require_guild_access(request, guild_id)` at the top.
- Bot cogs read settings via `neon_db.parse_settings(row["settings"], DEFAULTS)`.

## Bot conventions
- Every `.py` in `cli/components/` auto-loads (unless `_`-prefixed).
- Intents live in `cli/Ediscord/variables.py`. Message logging needs
  `message_content` intent enabled (privileged — also required in the Discord
  Developer Portal).
- All bot feature defaults must match between `cli/components/<feature>.py`
  and `website/api/index.py` (keep keys identical).

## Misc gotchas
- Windows is case-insensitive; Linux (deploy) is not. Keep import paths
  case-exact (`components.*`, `Ediscord.*`).
- PowerShell escaping breaks inline Python with quotes — write a temp `.py`
  file instead of `python -c "..."` with SQL.
- After adding a bot feature, verify `python -m py_compile` and that templates
  render (Jinja2) before committing.
