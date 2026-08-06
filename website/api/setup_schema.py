"""Run once to create the database schema in Neon."""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.local")
load_dotenv(Path(__file__).parent.parent / ".env")

import asyncpg


SCHEMA = """
CREATE TABLE IF NOT EXISTS bot_stats (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS guild_data (
    guild_id    TEXT PRIMARY KEY,
    data        JSONB NOT NULL,
    updated_at  DOUBLE PRECISION NOT NULL
);

ALTER TABLE guild_data ALTER COLUMN data TYPE JSONB USING data::jsonb;

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS mod_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE TABLE IF NOT EXISTS mod_log (
    id          SERIAL PRIMARY KEY,
    guild_id    TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    user_name   TEXT NOT NULL,
    action      TEXT NOT NULL,
    reason      TEXT DEFAULT '',
    moderator   TEXT DEFAULT '',
    created_at  DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mod_log_guild ON mod_log (guild_id, created_at DESC);

CREATE TABLE IF NOT EXISTS mod_actions (
    id          SERIAL PRIMARY KEY,
    guild_id    TEXT NOT NULL,
    action      TEXT NOT NULL,
    target_id   TEXT NOT NULL,
    target_name TEXT DEFAULT '',
    reason      TEXT DEFAULT '',
    moderator   TEXT DEFAULT '',
    duration    INTEGER,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE INDEX IF NOT EXISTS idx_mod_actions_guild ON mod_actions (guild_id, status);

CREATE TABLE IF NOT EXISTS muted_users (
    guild_id    TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    user_name   TEXT DEFAULT '',
    reason      TEXT DEFAULT '',
    end_ts      DOUBLE PRECISION NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_muted_users_guild ON muted_users (guild_id, end_ts);
CREATE INDEX IF NOT EXISTS idx_mod_actions_pending ON mod_actions (guild_id, status) WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS member_history (
    guild_id    TEXT NOT NULL,
    timestamp   DOUBLE PRECISION NOT NULL,
    member_count INTEGER NOT NULL,
    PRIMARY KEY (guild_id, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_member_history_guild ON member_history (guild_id, timestamp);

CREATE TABLE IF NOT EXISTS guild_stats_history (
    guild_id        TEXT NOT NULL,
    day             TEXT NOT NULL,
    member_count    INTEGER NOT NULL DEFAULT 0,
    channel_count   INTEGER NOT NULL DEFAULT 0,
    role_count      INTEGER NOT NULL DEFAULT 0,
    category_count  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, day)
);

CREATE TABLE IF NOT EXISTS message_history (
    guild_id    TEXT NOT NULL,
    timestamp   DOUBLE PRECISION NOT NULL,
    message_count INTEGER NOT NULL,
    PRIMARY KEY (guild_id, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_message_history_guild ON message_history (guild_id, timestamp);

CREATE TABLE IF NOT EXISTS invite_stats (
    guild_id    TEXT NOT NULL,
    inviter_id  TEXT NOT NULL,
    code        TEXT NOT NULL,
    uses        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, inviter_id, code)
);

CREATE TABLE IF NOT EXISTS ai_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE TABLE IF NOT EXISTS music_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE TABLE IF NOT EXISTS api_keys (
    key_name    TEXT PRIMARY KEY,
    value       TEXT NOT NULL DEFAULT '',
    updated_at  DOUBLE PRECISION NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS welcome_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE TABLE IF NOT EXISTS verify_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE TABLE IF NOT EXISTS leveling_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE TABLE IF NOT EXISTS logging_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE TABLE IF NOT EXISTS leveling_data (
    guild_id    TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    xp          INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS automation_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE TABLE IF NOT EXISTS automation_runs (
    guild_id    TEXT NOT NULL,
    bucket_ts   DOUBLE PRECISION NOT NULL,
    count       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, bucket_ts)
);

CREATE TABLE IF NOT EXISTS automation_logs (
    id          SERIAL PRIMARY KEY,
    guild_id    TEXT NOT NULL,
    message     TEXT NOT NULL DEFAULT '',
    created_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE TABLE IF NOT EXISTS automation_graph (
    guild_id    TEXT PRIMARY KEY,
    nodes       JSONB NOT NULL DEFAULT '[]',
    connections JSONB NOT NULL DEFAULT '[]',
    updated_at  DOUBLE PRECISION NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS automod_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE TABLE IF NOT EXISTS raid_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE TABLE IF NOT EXISTS autoresponder (
    id          SERIAL PRIMARY KEY,
    guild_id    TEXT NOT NULL,
    trigger     TEXT NOT NULL,
    response    TEXT NOT NULL,
    match_type  TEXT NOT NULL DEFAULT 'contains',
    created_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

ALTER TABLE autoresponder ADD COLUMN IF NOT EXISTS channel_id TEXT;
ALTER TABLE autoresponder ADD COLUMN IF NOT EXISTS cooldown INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_autoresponder_guild ON autoresponder (guild_id);

CREATE TABLE IF NOT EXISTS social_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE TABLE IF NOT EXISTS invite_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE TABLE IF NOT EXISTS ticket_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE TABLE IF NOT EXISTS ticket_logs (
    id          SERIAL PRIMARY KEY,
    guild_id    TEXT NOT NULL,
    channel_id  TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    transcript  TEXT NOT NULL,
    closed_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS captcha_codes (
    code        TEXT PRIMARY KEY,
    provider    TEXT NOT NULL,
    created_at  DOUBLE PRECISION NOT NULL,
    expires_at  DOUBLE PRECISION NOT NULL,
    used        BOOLEAN NOT NULL DEFAULT FALSE
);

ALTER TABLE captcha_codes ADD COLUMN IF NOT EXISTS guild_id TEXT DEFAULT '';
ALTER TABLE captcha_codes ADD COLUMN IF NOT EXISTS user_id TEXT DEFAULT '';

CREATE TABLE IF NOT EXISTS sessions (
    sid     TEXT PRIMARY KEY,
    data    JSONB NOT NULL DEFAULT '{}',
    expires DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    username    TEXT NOT NULL DEFAULT '',
    global_name TEXT DEFAULT '',
    avatar      TEXT DEFAULT '',
    email       TEXT DEFAULT '',
    github_id   TEXT DEFAULT '',
    github_username TEXT DEFAULT '',
    github_email TEXT DEFAULT '',
    created_at  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now())),
    last_login  DOUBLE PRECISION NOT NULL DEFAULT (extract(epoch from now()))
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS github_id TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS github_username TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS github_email TEXT DEFAULT '';
ALTER TABLE users DROP COLUMN IF EXISTS google_id;
ALTER TABLE users DROP COLUMN IF EXISTS google_email;
"""


async def main():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set")
        return
    conn = await asyncpg.connect(dsn)
    await conn.execute(SCHEMA)
    print("Schema created successfully.")
    await conn.close()


asyncio.run(main())
