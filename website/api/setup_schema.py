"""Run once to create the database schema."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.local")
load_dotenv(Path(__file__).parent.parent / ".env")

import libsql


SCHEMA = """
CREATE TABLE IF NOT EXISTS bot_stats (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS guild_data (
    guild_id    TEXT PRIMARY KEY,
    data        TEXT NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    TEXT NOT NULL DEFAULT '{}',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS mod_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    TEXT NOT NULL DEFAULT '{}',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS mod_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    user_name   TEXT NOT NULL,
    action      TEXT NOT NULL,
    reason      TEXT DEFAULT '',
    moderator   TEXT DEFAULT '',
    created_at  REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mod_log_guild ON mod_log (guild_id, created_at DESC);

CREATE TABLE IF NOT EXISTS mod_actions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    TEXT NOT NULL,
    action      TEXT NOT NULL,
    target_id   TEXT NOT NULL,
    target_name TEXT DEFAULT '',
    reason      TEXT DEFAULT '',
    moderator   TEXT DEFAULT '',
    duration    INTEGER,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mod_actions_guild ON mod_actions (guild_id, status);

CREATE TABLE IF NOT EXISTS muted_users (
    guild_id    TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    user_name   TEXT DEFAULT '',
    reason      TEXT DEFAULT '',
    end_ts      REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_muted_users_guild ON muted_users (guild_id, end_ts);
CREATE INDEX IF NOT EXISTS idx_mod_actions_pending ON mod_actions (guild_id, status) WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS member_history (
    guild_id    TEXT NOT NULL,
    timestamp   REAL NOT NULL,
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
    timestamp   REAL NOT NULL,
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
    settings    TEXT NOT NULL DEFAULT '{}',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS music_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    TEXT NOT NULL DEFAULT '{}',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS api_keys (
    key_name    TEXT PRIMARY KEY,
    value       TEXT NOT NULL DEFAULT '',
    updated_at  REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS welcome_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    TEXT NOT NULL DEFAULT '{}',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS verify_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    TEXT NOT NULL DEFAULT '{}',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS leveling_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    TEXT NOT NULL DEFAULT '{}',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS logging_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    TEXT NOT NULL DEFAULT '{}',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS leveling_data (
    guild_id    TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    xp          INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS automation_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    TEXT NOT NULL DEFAULT '{}',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS automation_runs (
    guild_id    TEXT NOT NULL,
    bucket_ts   REAL NOT NULL,
    count       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, bucket_ts)
);

CREATE TABLE IF NOT EXISTS automation_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    TEXT NOT NULL,
    message     TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS automation_graph (
    guild_id    TEXT PRIMARY KEY,
    nodes       TEXT NOT NULL DEFAULT '[]',
    connections TEXT NOT NULL DEFAULT '[]',
    updated_at  REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS automod_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    TEXT NOT NULL DEFAULT '{}',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS raid_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    TEXT NOT NULL DEFAULT '{}',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS autoresponder (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    TEXT NOT NULL,
    trigger     TEXT NOT NULL,
    response    TEXT NOT NULL,
    match_type  TEXT NOT NULL DEFAULT 'contains',
    created_at  REAL NOT NULL
);

ALTER TABLE autoresponder ADD COLUMN IF NOT EXISTS channel_id TEXT;
ALTER TABLE autoresponder ADD COLUMN IF NOT EXISTS cooldown INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_autoresponder_guild ON autoresponder (guild_id);

CREATE TABLE IF NOT EXISTS social_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    TEXT NOT NULL DEFAULT '{}',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS invite_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    TEXT NOT NULL DEFAULT '{}',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS ticket_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    TEXT NOT NULL DEFAULT '{}',
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS ticket_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    TEXT NOT NULL,
    channel_id  TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    transcript  TEXT NOT NULL,
    closed_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS captcha_codes (
    code        TEXT PRIMARY KEY,
    provider    TEXT NOT NULL,
    created_at  REAL NOT NULL,
    expires_at  REAL NOT NULL,
    used        INTEGER NOT NULL DEFAULT 0
);

ALTER TABLE captcha_codes ADD COLUMN IF NOT EXISTS guild_id TEXT DEFAULT '';
ALTER TABLE captcha_codes ADD COLUMN IF NOT EXISTS user_id TEXT DEFAULT '';

CREATE TABLE IF NOT EXISTS sessions (
    sid     TEXT PRIMARY KEY,
    data    TEXT NOT NULL DEFAULT '{}',
    expires REAL NOT NULL
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
    created_at  REAL NOT NULL,
    last_login  REAL NOT NULL
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS github_id TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS github_username TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS github_email TEXT DEFAULT '';
"""


def main():
    url = os.environ.get("TURSO_DATABASE_URL") or os.environ.get("DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    if not url:
        print("TURSO_DATABASE_URL not set")
        return
    kwargs = {"database": url}
    if token:
        kwargs["auth_token"] = token
    conn = libsql.connect(**kwargs)
    # Execute each statement individually (libsql doesn't support multi-statement)
    for stmt in SCHEMA.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)
    conn.commit()
    print("Schema created successfully.")
    conn.close()


main()
