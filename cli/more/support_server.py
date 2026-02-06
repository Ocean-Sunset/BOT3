# --------------------- IMPORTS --------------------
import discord
from discord.ext import commands, tasks
from Ediscord import utils, variables
import os
import json
import time
from datetime import datetime, timedelta
from discord import app_commands

# --------------------- SUPPORT SERVER COG --------------------
print("✅ - Support Server cog loaded.")

SUPPORT_MESSAGES_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "support_messages.json"))


def _load_messages_data():
    if os.path.exists(SUPPORT_MESSAGES_FILE):
        try:
            with open(SUPPORT_MESSAGES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_messages_data(data: dict):
    os.makedirs(os.path.dirname(SUPPORT_MESSAGES_FILE), exist_ok=True)
    with open(SUPPORT_MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class SupportServer(commands.Cog):
    """Background tasks for the support server channels:

    - Status updater: edits/creates a message in the configured status channel containing online status, uptime and version.
    - Changelog updater: when the version in `variables.bot_info` changes, edits a fixed message in the changelog channel with the new changelog text (removes any `@everyone`).

    Channel IDs should be added to `Ediscord/variables.py` as:
      SUPPORT_STATUS_CHANNEL_ID = 123456789012345678
      CHANGELOG_CHANNEL_ID = 123456789012345678

    """

    def __init__(self, bot):
        self.bot = bot
        self.messages = _load_messages_data()
        # Keep track of last seen version to detect updates
        self._last_version = variables.bot_info.get("version") if isinstance(variables.bot_info, dict) else None

        # Start tasks
        self.status_updater.start()
        self.changelog_updater.start()

    def cog_unload(self):
        self.status_updater.cancel()
        self.changelog_updater.cancel()

    async def _get_channel(self, attr_name: str):
        """Resolve a channel ID from either `variables` or the local messages file.

        This allows storing IDs in `Ediscord/variables.py` (preferred) or
        writing them via the commands below which persist them into
        `default/data/support_messages.json`.
        """
        channel_id = getattr(variables, attr_name, None)
        if not channel_id:
            # fallback to values stored in support_messages.json
            channel_id = self.messages.get(attr_name)
        if not channel_id:
            return None
        try:
            return self.bot.get_channel(int(channel_id))
        except Exception:
            return None


    @app_commands.command(name="setsupportchannel", description="Set the status channel where the bot posts its uptime/status.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setsupportchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the status channel where the bot posts its uptime/status."""
        self.messages["SUPPORT_STATUS_CHANNEL_ID"] = int(channel.id)
        _save_messages_data(self.messages)
        await interaction.response.send_message(f"✅ Support status channel set to {channel.mention}", ephemeral=True)

    @app_commands.command(name="setchangelogchannel", description="Set the changelog channel where the bot posts its changelog.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setchangelogchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the changelog channel where the bot posts its changelog."""
        self.messages["CHANGELOG_CHANNEL_ID"] = int(channel.id)
        _save_messages_data(self.messages)
        await interaction.response.send_message(f"✅ Changelog channel set to {channel.mention}", ephemeral=True)

    async def _fetch_or_create_message(self, channel: discord.TextChannel, key: str, initial_content: str):
        # Try to fetch by stored message id
        if not channel:
            return None
        msg_id = self.messages.get(key)
        if msg_id:
            try:
                msg = await channel.fetch_message(int(msg_id))
                return msg
            except Exception:
                # stored message id invalid, remove it
                self.messages.pop(key, None)
                _save_messages_data(self.messages)

        # Search the channel history for a message authored by the bot with our marker line
        async for msg in channel.history(limit=200):
            if msg.author == self.bot.user:
                # Heuristic: check for one of our markers
                if msg.content.startswith("# Bot status:") or msg.content.startswith("# Here is the changelog"):
                    self.messages[key] = msg.id
                    _save_messages_data(self.messages)
                    return msg
        # Not found: create a new message and store it
        try:
            new_msg = await channel.send(initial_content)
            self.messages[key] = new_msg.id
            _save_messages_data(self.messages)
            return new_msg
        except Exception:
            return None

    def _format_uptime(self, start_ts: float):
        seconds = int(time.time() - start_ts)
        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        return " ".join(parts)

    @tasks.loop(seconds=30.0)
    async def status_updater(self):
        await self.bot.wait_until_ready()
        channel = await self._get_channel(variables.SUPPORT_STATUS_CHANNEL_ID)
        if not channel:
            return

        # Compose the status message
        uptime = self._format_uptime(variables.start_time) if getattr(variables, "start_time", None) else "Unknown"
        version = variables.bot_info.get("version") if isinstance(variables.bot_info, dict) else "Unknown"
        is_online = True  # If this code is running, the bot is online

        content = (
            f"# Bot status: {'Online ✅' if is_online else 'Offline ❌'}\n"
            f"Uptime: **{uptime}**\n"
            f"Build / Version: **{version}**\n"
            f"Last checked: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

        msg = await self._fetch_or_create_message(channel, "status_message_id", content)
        if msg:
            try:
                await msg.edit(content=content)
            except Exception:
                pass

    @tasks.loop(seconds=15.0)
    async def changelog_updater(self):
        await self.bot.wait_until_ready()
        channel = await self._get_channel(variables.CHANGELOG_CHANNEL_ID)
        if not channel:
            return

        current_version = variables.bot_info.get("version") if isinstance(variables.bot_info, dict) else None
        current_text = variables.bot_info.get("new_stuff") if isinstance(variables.bot_info, dict) else None

        # If we don't have a version yet, skip
        if not current_version:
            return

        # If version hasn't changed and we already saved a message, do nothing
        if self._last_version == current_version and self.messages.get("changelog_message_id"):
            return

        # Compose new changelog content and remove any @everyone tags
        new_content = f"# Here is the changelog for the **{current_version}**:\n{current_text or ''}"
        new_content = new_content.replace("@everyone", "")

        msg = await self._fetch_or_create_message(channel, "changelog_message_id", new_content)
        if msg:
            try:
                # Also remove @everyone if present in existing message
                edited = msg.content.replace("@everyone", "")
                # Replace content with the new changelog text
                await msg.edit(content=new_content)
                self._last_version = current_version
                # Save message id if not already saved
                if self.messages.get("changelog_message_id") != msg.id:
                    self.messages["changelog_message_id"] = msg.id
                    _save_messages_data(self.messages)
            except Exception:
                pass


async def setup(bot):
    print("Loading SupportServer cog...")
    await bot.add_cog(SupportServer(bot))
