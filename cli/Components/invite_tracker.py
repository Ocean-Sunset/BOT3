import discord
from discord.ext import commands
from discord import app_commands
import json
from typing import Optional

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db


INVITE_DEFAULTS = {"enabled": False, "announce_channel_id": None, "ping_on_join": False}


async def get_invite_settings(guild_id: int):
    pool = await neon_db.get_pool()
    if not pool:
        return dict(INVITE_DEFAULTS)
    row = await pool.fetchrow("SELECT settings FROM invite_settings WHERE guild_id = $1", str(guild_id))
    return neon_db.parse_settings(row["settings"], INVITE_DEFAULTS) if row else dict(INVITE_DEFAULTS)


async def save_invite_settings(guild_id: int, settings: dict):
    pool = await neon_db.get_pool()
    if not pool:
        return
    await pool.execute(
        "INSERT INTO invite_settings (guild_id, settings) VALUES ($1, $2::jsonb) ON CONFLICT (guild_id) DO UPDATE SET settings = $2::jsonb",
        str(guild_id), json.dumps(settings),
    )


class InviteTracker(commands.Cog, name="InviteTracker"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.invites = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                self.invites[guild.id] = await guild.invites()
            except:
                self.invites[guild.id] = []

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if not guild.me.guild_permissions.manage_guild:
            return
        try:
            self.invites[guild.id] = await guild.invites()
        except:
            self.invites[guild.id] = []

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not member.guild.me.guild_permissions.manage_guild:
            return
        before = self.invites.get(member.guild.id, [])
        try:
            after = await member.guild.invites()
        except:
            return

        used = None
        for invite in before:
            found = discord.utils.get(after, code=invite.code)
            if found and found.uses > invite.uses:
                used = invite
                break
        self.invites[member.guild.id] = after

        settings = await get_invite_settings(member.guild.id)
        if not settings.get("enabled"):
            return

        channel_id = settings.get("announce_channel_id")
        if not channel_id:
            return
        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        if used:
            inviter = used.inviter
            inviter_name = inviter.mention if inviter else "Unknown"
            embed = EmbedBuilder().title("Member Joined").description(f"{member.mention} was invited by {inviter_name}").field("Code", used.code).field("Uses", used.uses).color("green").build()
        else:
            embed = EmbedBuilder().title("Member Joined").description(f"{member.mention} joined (no invite tracked)").color("green").build()
        await channel.send(embed=embed)

    invite_group = app_commands.Group(name="invites", description="Invite tracking commands")

    @invite_group.command(name="toggle", description="Enable or disable invite tracking")
    async def toggle(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
        settings = await get_invite_settings(interaction.guild_id)
        settings["enabled"] = not settings.get("enabled", False)
        await save_invite_settings(interaction.guild_id, settings)
        status = "enabled" if settings["enabled"] else "disabled"
        await interaction.response.send_message(f"Invite tracking **{status}**.", ephemeral=True)

    @invite_group.command(name="channel", description="Set channel for invite announcements")
    @app_commands.describe(channel="The announcement channel")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
        settings = await get_invite_settings(interaction.guild_id)
        settings["announce_channel_id"] = channel.id
        await save_invite_settings(interaction.guild_id, settings)
        await interaction.response.send_message(f"Invite announcement channel set to {channel.mention}.", ephemeral=True)

    @invite_group.command(name="stats", description="Show invite leaderboard")
    async def stats(self, interaction: discord.Interaction):
        await interaction.response.send_message("Invite stats tracking coming soon.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(InviteTracker(bot))
