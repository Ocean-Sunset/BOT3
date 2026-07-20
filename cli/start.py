"""
Prowl - Entry Point
Run this script to start the bot.
"""

import os
import sys
import time
import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import discord
from discord.ext import commands
import psutil
import json

from Ediscord import variables, logger, utils, __version__
from Ediscord import db as neon_db


COGS_DIR = Path(__file__).parent / "components"


class ProwlBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="",
            intents=variables.intents,
            activity=discord.Game("starting up..."),
            status=discord.Status.online,
        )
        self.version = __version__
        self.launch_time = 0

    async def setup_hook(self):
        await self.load_cogs()
        synced = await self.tree.sync()
        logger.info(f"Synced {len(synced)} slash commands.")
        self.loop.create_task(self._dashboard_writer())
        self.loop.create_task(self._initial_neon_push())
        self.loop.create_task(self._neon_syncer())
        self.loop.create_task(self._mod_settings_poller())
        logger.info("Setup hook complete.")

    async def _initial_neon_push(self):
        await self.wait_until_ready()
        import os as _os
        if not _os.environ.get("DATABASE_URL"):
            logger.warning("DATABASE_URL not set — bot won't push guild data to Neon. Set it in cli/.env")
            return
        try:
            await self._push_to_neon()
            logger.info("Initial Neon push complete.")
        except Exception as e:
            logger.error(f"Initial Neon push failed: {e}")

    async def load_cogs(self):
        for file in COGS_DIR.glob("*.py"):
            if file.name.startswith("_"):
                continue
            cog_name = f"components.{file.stem}"
            try:
                await self.load_extension(cog_name, package=str(COGS_DIR.parent))
                logger.info(f"Loaded cog: {cog_name}")
            except Exception as e:
                logger.error(f"Failed to load {cog_name}: {e}")

    async def on_ready(self):
        logger.info(f"Prowl is online! Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Servers: {len(self.guilds)} | Users: {len(self.users)}")
        self.launch_time = time.time()
        utils.write_bot_data(self)
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Game("with commands"),
        )

    async def _dashboard_writer(self):
        """Periodically write bot data for the dashboard."""
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                utils.write_bot_data(self)
            except Exception as e:
                logger.error(f"Dashboard write failed: {e}")
            await asyncio.sleep(60)

    async def _neon_syncer(self):
        """Push bot stats and guild data to Neon every 5 minutes."""
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                await self._push_to_neon()
            except Exception as e:
                logger.error(f"Neon sync failed: {e}")
            await asyncio.sleep(300)

    async def _mod_settings_poller(self):
        """Periodically cache mod_settings from Neon for command permission checks."""
        await self.wait_until_ready()
        self._mod_cache = {}
        while not self.is_closed():
            try:
                for guild in self.guilds:
                    gid = str(guild.id)
                    self._mod_cache[gid] = await neon_db.fetch_mod_settings(gid)
            except Exception as e:
                logger.error(f"Mod settings poller failed: {e}")
            await asyncio.sleep(120)

    async def _push_to_neon(self):
        """Build stats and push directly to Neon PostgreSQL."""
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss // 1024 // 1024
        cpu = process.cpu_percent()

        total_users = len(self.users)
        active_users = sum(1 for m in self.get_all_members() if m.status != discord.Status.offline)
        total_commands = getattr(self, "total_commands", 0)
        launch_time = getattr(self, "launch_time", None)
        uptime_seconds = int(time.time() - launch_time) if launch_time else 0
        uptime_str = time.strftime("%Hh %Mm %Ss", time.gmtime(uptime_seconds))
        bot_status = "Running" if self.is_ready() else "Not Running"
        bot_version = f"{getattr(self, 'version', 'unknown')} (2025.09.19.19.00.12)"
        python_version = sys.version.replace("\n", " ")
        guilds = list(self.guilds)
        guild_ids = [str(g.id) for g in guilds]
        loaded_cogs = list(self.cogs.keys())
        all_commands = [cmd.name for cmd in self.tree.get_commands()]
        last_restart = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(launch_time)) if launch_time else "unknown"

        bot_stats = {
            "total_users": total_users,
            "active_users": active_users,
            "total_commands": total_commands,
            "uptime": uptime_str,
            "bot_status": bot_status,
            "bot_version": bot_version,
            "python_version": python_version,
            "num_guilds": len(guilds),
            "guild_ids": json.dumps(guild_ids),
            "num_channels": sum(len(g.channels) for g in guilds),
            "num_roles": sum(len(g.roles) for g in guilds),
            "num_emojis": sum(len(g.emojis) for g in guilds),
            "loaded_cogs": json.dumps(loaded_cogs),
            "all_commands": json.dumps(all_commands),
            "memory_usage_mb": mem,
            "cpu_usage_percent": cpu,
            "last_restart": last_restart,
        }

        guild_list = []
        for guild in guilds:
            icon_url = str(guild.icon.url) if guild.icon else None
            guild_list.append({
                "id": guild.id,
                "name": guild.name,
                "icon_url": icon_url,
                "member_count": guild.member_count,
                "online_count": sum(1 for m in guild.members if m.status != discord.Status.offline),
                "channel_count": len(guild.channels),
                "text_channels": len(guild.text_channels),
                "voice_channels": len(guild.voice_channels),
                "role_count": len(guild.roles),
                "emoji_count": len(guild.emojis),
                "created_at": guild.created_at.isoformat(),
                "owner_id": guild.owner_id,
                "bot_top_role_position": guild.me.top_role.position if guild.me else 0,
                "members": [{"id": m.id, "name": m.name, "display_name": m.display_name, "avatar_url": str(m.display_avatar.url)} for m in guild.members],
                "channels": [{"id": c.id, "name": c.name, "type": c.type.value} for c in guild.channels],
                "roles": [{"id": r.id, "name": r.name, "color": r.color.value, "position": r.position, "managed": r.managed, "count": len(r.members), "permissions": r.permissions.value} for r in guild.roles],
            })

        await neon_db.push_bot_stats(bot_stats)
        await neon_db.push_guild_data(guild_list)
        logger.info("Neon sync: data pushed successfully.")


def main():
    token = os.environ.get("TOKEN")
    if not token:
        logger.error("TOKEN not found in environment variables. Add it to cli/.env")
        sys.exit(1)

    bot = ProwlBot()
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
