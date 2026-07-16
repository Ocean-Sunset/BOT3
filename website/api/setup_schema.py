"""Run once to create the database schema in Neon."""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

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

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS mod_settings (
    guild_id    TEXT PRIMARY KEY,
    settings    JSONB NOT NULL DEFAULT '{}',
    updated_at  DOUBLE PRECISION GENERATED ALWAYS AS (extract(epoch from now())) STORED
);

CREATE TABLE IF NOT EXISTS mod_log (
    id          SERIAL PRIMARY KEY,
    guild_id    TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    user_name   TEXT NOT NULL,
    action      TEXT NOT NULL,
    reason      TEXT DEFAULT '',
    created_at  DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mod_log_guild ON mod_log (guild_id, created_at DESC);
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
