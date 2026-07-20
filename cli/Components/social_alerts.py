import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import aiohttp
import asyncio
from typing import Optional

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db


SOCIAL_DEFAULTS = {"youtube_channel_id": None, "youtube_ping_role": None, "twitch_channel": None, "twitch_ping_role": None, "announce_channel_id": None}


async def get_social_settings(guild_id: int):
    pool = await neon_db.get_pool()
    if not pool:
        return dict(SOCIAL_DEFAULTS)
    row = await pool.fetchrow("SELECT settings FROM social_settings WHERE guild_id = $1", str(guild_id))
    return {**SOCIAL_DEFAULTS, **row["settings"]} if row else dict(SOCIAL_DEFAULTS)


async def save_social_settings(guild_id: int, settings: dict):
    pool = await neon_db.get_pool()
    if not pool:
        return
    await pool.execute(
        "INSERT INTO social_settings (guild_id, settings) VALUES ($1, $2::jsonb) ON CONFLICT (guild_id) DO UPDATE SET settings = $2::jsonb",
        str(guild_id), json.dumps(settings),
    )


class SocialAlerts(commands.Cog, name="SocialAlerts"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_youtube.start()

    def cog_unload(self):
        self.check_youtube.cancel()

    @tasks.loop(minutes=15)
    async def check_youtube(self):
        await self.bot.wait_until_ready()

    @check_youtube.before_loop
    async def before_check(self):
        await asyncio.sleep(30)

    social_group = app_commands.Group(name="social", description="Social media alert settings")

    @social_group.command(name="youtube", description="Set YouTube channel for upload alerts")
    @app_commands.describe(youtube_channel_id="Your YouTube channel ID", ping_role="Role to ping on upload", announce_channel="Channel for announcements")
    async def set_youtube(self, interaction: discord.Interaction, youtube_channel_id: str, ping_role: Optional[discord.Role] = None, announce_channel: Optional[discord.TextChannel] = None):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
        settings = await get_social_settings(interaction.guild_id)
        settings["youtube_channel_id"] = youtube_channel_id
        settings["youtube_ping_role"] = str(ping_role.id) if ping_role else None
        settings["announce_channel_id"] = announce_channel.id if announce_channel else interaction.channel_id
        await save_social_settings(interaction.guild_id, settings)
        await interaction.response.send_message(f"YouTube alerts set up for channel `{youtube_channel_id}`.", ephemeral=True)

    @social_group.command(name="twitch", description="Set Twitch channel for stream alerts")
    @app_commands.describe(twitch_channel="Your Twitch channel name", ping_role="Role to ping on stream", announce_channel="Channel for announcements")
    async def set_twitch(self, interaction: discord.Interaction, twitch_channel: str, ping_role: Optional[discord.Role] = None, announce_channel: Optional[discord.TextChannel] = None):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
        settings = await get_social_settings(interaction.guild_id)
        settings["twitch_channel"] = twitch_channel
        settings["twitch_ping_role"] = str(ping_role.id) if ping_role else None
        settings["announce_channel_id"] = announce_channel.id if announce_channel else interaction.channel_id
        await save_social_settings(interaction.guild_id, settings)
        await interaction.response.send_message(f"Twitch alerts set up for `{twitch_channel}`.", ephemeral=True)

    @social_group.command(name="config", description="View social alert settings")
    async def config(self, interaction: discord.Interaction):
        settings = await get_social_settings(interaction.guild_id)
        embed = EmbedBuilder().title("Social Alert Settings").color("blue") \
            .field("YouTube", f"Channel: `{settings.get('youtube_channel_id') or 'Not set'}`") \
            .field("Twitch", f"Channel: `{settings.get('twitch_channel') or 'Not set'}`") \
            .build()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @social_group.command(name="remove", description="Remove social alert settings")
    @app_commands.describe(platform="Which platform to remove")
    @app_commands.choices(platform=[app_commands.Choice(name="YouTube", value="youtube"), app_commands.Choice(name="Twitch", value="twitch"), app_commands.Choice(name="Both", value="all")])
    async def remove(self, interaction: discord.Interaction, platform: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
        settings = await get_social_settings(interaction.guild_id)
        if platform in ("youtube", "all"):
            settings["youtube_channel_id"] = None
            settings["youtube_ping_role"] = None
        if platform in ("twitch", "all"):
            settings["twitch_channel"] = None
            settings["twitch_ping_role"] = None
        await save_social_settings(interaction.guild_id, settings)
        await interaction.response.send_message(f"Social alerts removed for {platform}.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SocialAlerts(bot))
