import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import aiohttp
import asyncio
import datetime
from typing import Optional

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db


SOCIAL_DEFAULTS = {
    "youtube_enabled": False,
    "youtube_channel_id": None,
    "youtube_ping_role": None,
    "youtube_announce_channel_id": None,
    "youtube_message": None,
    "twitch_enabled": False,
    "twitch_channel": None,
    "twitch_ping_role": None,
    "twitch_announce_channel_id": None,
    "twitch_message": None,
    "twitter_enabled": False,
    "twitter_handle": None,
    "twitter_ping_role": None,
    "twitter_announce_channel_id": None,
    "twitter_message": None,
    # Extra alerts per platform: { "youtube": [{target, ping_role, message}], ... }
    "extra_alerts": {},
}


async def get_social_settings(guild_id: int):
    pool = await neon_db.get_pool()
    if not pool:
        return dict(SOCIAL_DEFAULTS)
    row = await pool.fetchrow("SELECT settings FROM social_settings WHERE guild_id = $1", str(guild_id))
    return neon_db.parse_settings(row["settings"], SOCIAL_DEFAULTS) if row else dict(SOCIAL_DEFAULTS)


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

    def _resolve_channel(self, guild: discord.Guild, channel_id, fallback_id=None) -> Optional[discord.TextChannel]:
        for cid in (channel_id, fallback_id):
            if not cid:
                continue
            channel = guild.get_channel(int(cid))
            if channel and isinstance(channel, discord.TextChannel):
                return channel
        return None

    social_group = app_commands.Group(name="social", description="Social media alert settings")

    @social_group.command(name="youtube", description="Set YouTube channel for upload alerts")
    @app_commands.describe(youtube_channel_id="Your YouTube channel ID", ping_role="Role to ping on upload", announce_channel="Channel for YouTube announcements")
    async def set_youtube(self, interaction: discord.Interaction, youtube_channel_id: str, ping_role: Optional[discord.Role] = None, announce_channel: Optional[discord.TextChannel] = None):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_social_settings(interaction.guild_id)
        settings["youtube_channel_id"] = youtube_channel_id
        settings["youtube_ping_role"] = str(ping_role.id) if ping_role else None
        settings["youtube_announce_channel_id"] = str(announce_channel.id) if announce_channel else str(interaction.channel_id)
        await save_social_settings(interaction.guild_id, settings)
        embed = (
            EmbedBuilder()
            .title("YouTube Alerts Set Up")
            .color("red")
            .field("Channel ID", f"`{youtube_channel_id}`")
            .field("Ping Role", ping_role.mention if ping_role else "None")
            .field("Announce Channel", announce_channel.mention if announce_channel else interaction.channel.mention)
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @social_group.command(name="twitch", description="Set Twitch channel for stream alerts")
    @app_commands.describe(twitch_channel="Your Twitch channel name", ping_role="Role to ping on stream", announce_channel="Channel for Twitch announcements")
    async def set_twitch(self, interaction: discord.Interaction, twitch_channel: str, ping_role: Optional[discord.Role] = None, announce_channel: Optional[discord.TextChannel] = None):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_social_settings(interaction.guild_id)
        settings["twitch_channel"] = twitch_channel
        settings["twitch_ping_role"] = str(ping_role.id) if ping_role else None
        settings["twitch_announce_channel_id"] = str(announce_channel.id) if announce_channel else str(interaction.channel_id)
        await save_social_settings(interaction.guild_id, settings)
        embed = (
            EmbedBuilder()
            .title("Twitch Alerts Set Up")
            .color("violet")
            .field("Channel", f"`{twitch_channel}`")
            .field("Ping Role", ping_role.mention if ping_role else "None")
            .field("Announce Channel", announce_channel.mention if announce_channel else interaction.channel.mention)
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @social_group.command(name="twitter", description="Set Twitter/X handle for post alerts")
    @app_commands.describe(handle="Twitter/X handle (without @)", ping_role="Role to ping on post", announce_channel="Channel for Twitter/X announcements")
    async def set_twitter(self, interaction: discord.Interaction, handle: str, ping_role: Optional[discord.Role] = None, announce_channel: Optional[discord.TextChannel] = None):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_social_settings(interaction.guild_id)
        settings["twitter_handle"] = handle.lstrip("@")
        settings["twitter_ping_role"] = str(ping_role.id) if ping_role else None
        settings["twitter_announce_channel_id"] = str(announce_channel.id) if announce_channel else str(interaction.channel_id)
        await save_social_settings(interaction.guild_id, settings)
        embed = (
            EmbedBuilder()
            .title("Twitter/X Alerts Set Up")
            .color("blue")
            .field("Handle", f"@{handle.lstrip('@')}")
            .field("Ping Role", ping_role.mention if ping_role else "None")
            .field("Announce Channel", announce_channel.mention if announce_channel else interaction.channel.mention)
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @social_group.command(name="config", description="View social alert settings")
    async def config(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_social_settings(interaction.guild_id)
        yt_role = interaction.guild.get_role(int(settings["youtube_ping_role"])) if settings.get("youtube_ping_role") else None
        tw_role = interaction.guild.get_role(int(settings["twitch_ping_role"])) if settings.get("twitch_ping_role") else None
        x_role = interaction.guild.get_role(int(settings["twitter_ping_role"])) if settings.get("twitter_ping_role") else None
        yt_channel = self._resolve_channel(interaction.guild, settings.get("youtube_announce_channel_id"))
        tw_channel = self._resolve_channel(interaction.guild, settings.get("twitch_announce_channel_id"))
        x_channel = self._resolve_channel(interaction.guild, settings.get("twitter_announce_channel_id"))
        embed = (
            EmbedBuilder()
            .title("📱 Social Alert Settings")
            .color("blue")
            .field("📺 YouTube", f"Channel: `{settings.get('youtube_channel_id') or 'Not set'}`\nPing: {yt_role.mention if yt_role else 'None'}\nAnnounces: {yt_channel.mention if yt_channel else 'Not set'}")
            .field("🟣 Twitch", f"Channel: `{settings.get('twitch_channel') or 'Not set'}`\nPing: {tw_role.mention if tw_role else 'None'}\nAnnounces: {tw_channel.mention if tw_channel else 'Not set'}")
            .field("🐦 Twitter/X", f"Handle: `@{settings.get('twitter_handle') or 'Not set'}`\nPing: {x_role.mention if x_role else 'None'}\nAnnounces: {x_channel.mention if x_channel else 'Not set'}")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @social_group.command(name="remove", description="Remove social alert settings")
    @app_commands.describe(platform="Which platform to remove")
    @app_commands.choices(platform=[
        app_commands.Choice(name="YouTube", value="youtube"),
        app_commands.Choice(name="Twitch", value="twitch"),
        app_commands.Choice(name="Twitter/X", value="twitter"),
        app_commands.Choice(name="All", value="all")
    ])
    async def remove(self, interaction: discord.Interaction, platform: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_social_settings(interaction.guild_id)
        if platform in ("youtube", "all"):
            settings["youtube_channel_id"] = None
            settings["youtube_ping_role"] = None
            settings["youtube_announce_channel_id"] = None
        if platform in ("twitch", "all"):
            settings["twitch_channel"] = None
            settings["twitch_ping_role"] = None
            settings["twitch_announce_channel_id"] = None
        if platform in ("twitter", "all"):
            settings["twitter_handle"] = None
            settings["twitter_ping_role"] = None
            settings["twitter_announce_channel_id"] = None
        await save_social_settings(interaction.guild_id, settings)
        await interaction.response.send_message(
            embed=EmbedBuilder().title("Social Alerts Removed").description(f"Removed alerts for **{platform}**.").color("green").timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(SocialAlerts(bot))
