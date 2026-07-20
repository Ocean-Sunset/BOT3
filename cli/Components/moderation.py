import discord
from discord.ext import commands
from discord import app_commands
import datetime
import time
import json
from typing import Optional

from Ediscord import logger, EmbedBuilder, error_embed
from Ediscord import db as neon_db
from Ediscord.utils import is_owner


MOD_DEFAULTS = {
    "dm_on_action": True, "require_reason": True, "silent_mod": False,
    "auto_thread": False, "track_stats": True,
    "cmd_ban": True, "cmd_kick": True, "cmd_timeout": True, "cmd_warn": True,
    "mod_roles": [], "emergency_lock": False,
}


async def get_mod_settings(guild_id: int):
    pool = await neon_db.get_pool()
    if not pool:
        return dict(MOD_DEFAULTS)
    row = await pool.fetchrow(
        "SELECT settings FROM mod_settings WHERE guild_id = $1", str(guild_id)
    )
    if row:
        return {**MOD_DEFAULTS, **row["settings"]}
    return dict(MOD_DEFAULTS)


async def save_mod_settings(guild_id: int, settings: dict):
    pool = await neon_db.get_pool()
    if not pool:
        return
    await pool.execute(
        "INSERT INTO mod_settings (guild_id, settings) VALUES ($1, $2::jsonb) "
        "ON CONFLICT (guild_id) DO UPDATE SET settings = $2::jsonb",
        str(guild_id), json.dumps(settings),
    )


async def log_mod_action(guild_id: int, user_id: str, user_name: str, action: str, reason: str = ""):
    await neon_db.push_mod_event(guild_id, user_id, user_name, action, reason)


def is_mod():
    async def predicate(interaction: discord.Interaction):
        settings = await get_mod_settings(interaction.guild_id)
        mod_roles = settings.get("mod_roles", [])
        user_roles = [str(r.id) for r in interaction.user.roles]
        if any(rid in mod_roles for rid in user_roles):
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        if interaction.user.guild_permissions.moderate_members:
            return True
        await interaction.response.send_message(
            "You don't have permission to use this command.", ephemeral=True
        )
        return False
    return app_commands.check(predicate)


async def check_emergency_lock(interaction: discord.Interaction) -> bool:
    settings = await get_mod_settings(interaction.guild_id)
    if settings.get("emergency_lock"):
        await interaction.response.send_message(
            "Server is in emergency lockdown. Mod commands are disabled.", ephemeral=True
        )
        return False
    return True


class ConfirmationView(discord.ui.View):
    def __init__(self, timeout: float = 30):
        super().__init__(timeout=timeout)
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


class Moderation(commands.Cog, name="Moderation"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="The member to kick", reason="Reason for the kick")
    @is_mod()
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        settings = await get_mod_settings(interaction.guild_id)
        if not settings.get("cmd_kick", True):
            return await interaction.response.send_message("Kick command is disabled.", ephemeral=True)
        if not await check_emergency_lock(interaction):
            return

        view = ConfirmationView()
        await interaction.response.send_message(
            f"Are you sure you want to kick {member.mention}?", view=view, ephemeral=True
        )
        await view.wait()
        if view.value is True:
            try:
                if settings.get("dm_on_action"):
                    await member.send(f"You have been kicked from {interaction.guild.name}.\nReason: {reason}")
            except:
                pass
            await member.kick(reason=reason)
            embed = EmbedBuilder().title("Member Kicked").description(f"{member.mention} has been kicked.").color("red").field("Reason", reason).build()
            await interaction.followup.send(embed=embed)
            await log_mod_action(interaction.guild_id, str(member.id), member.name, "kick", reason)
        else:
            await interaction.followup.send("Kick cancelled.", ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(member="The member to ban", reason="Reason for the ban", delete_days="Days of messages to delete (0-7)")
    @is_mod()
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided", delete_days: int = 1):
        settings = await get_mod_settings(interaction.guild_id)
        if not settings.get("cmd_ban", True):
            return await interaction.response.send_message("Ban command is disabled.", ephemeral=True)
        if not await check_emergency_lock(interaction):
            return
        if delete_days < 0 or delete_days > 7:
            return await interaction.response.send_message("Delete days must be between 0 and 7.", ephemeral=True)

        view = ConfirmationView()
        await interaction.response.send_message(f"Are you sure you want to ban {member.mention}?", view=view, ephemeral=True)
        await view.wait()
        if view.value is True:
            try:
                if settings.get("dm_on_action"):
                    await member.send(f"You have been banned from {interaction.guild.name}.\nReason: {reason}")
            except:
                pass
            await member.ban(reason=reason, delete_message_days=delete_days)
            embed = EmbedBuilder().title("Member Banned").description(f"{member.mention} has been banned.").color("red").field("Reason", reason).build()
            await interaction.followup.send(embed=embed)
            await log_mod_action(interaction.guild_id, str(member.id), member.name, "ban", reason)
        else:
            await interaction.followup.send("Ban cancelled.", ephemeral=True)

    @app_commands.command(name="unban", description="Unban a user by ID")
    @app_commands.describe(user_id="The user ID to unban", reason="Reason for the unban")
    @is_mod()
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "No reason provided"):
        settings = await get_mod_settings(interaction.guild_id)
        if not settings.get("cmd_ban", True):
            return await interaction.response.send_message("Unban command is disabled.", ephemeral=True)
        if not await check_emergency_lock(interaction):
            return

        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user, reason=reason)
            embed = EmbedBuilder().title("User Unbanned").description(f"{user.mention} has been unbanned.").color("green").field("Reason", reason).build()
            await interaction.response.send_message(embed=embed)
            await log_mod_action(interaction.guild_id, user_id, user.name, "unban", reason)
        except discord.NotFound:
            await interaction.response.send_message("User not found or not banned.", ephemeral=True)

    @app_commands.command(name="mute", description="Timeout a member")
    @app_commands.describe(member="The member to mute", duration="Duration in minutes", reason="Reason for the mute")
    @is_mod()
    async def mute(self, interaction: discord.Interaction, member: discord.Member, duration: int = 60, reason: str = "No reason provided"):
        settings = await get_mod_settings(interaction.guild_id)
        if not settings.get("cmd_timeout", True):
            return await interaction.response.send_message("Timeout command is disabled.", ephemeral=True)
        if not await check_emergency_lock(interaction):
            return

        until = discord.utils.utcnow() + datetime.timedelta(minutes=duration)
        await member.timeout(until, reason=reason)
        embed = EmbedBuilder().title("Member Muted").description(f"{member.mention} has been timed out.").color("orange").field("Duration", f"{duration} minutes").field("Reason", reason).build()
        await interaction.response.send_message(embed=embed)
        await log_mod_action(interaction.guild_id, str(member.id), member.name, "mute", f"{duration}min - {reason}")

        if settings.get("dm_on_action"):
            try:
                await member.send(f"You have been muted in {interaction.guild.name} for {duration} minutes.\nReason: {reason}")
            except:
                pass

    @app_commands.command(name="unmute", description="Remove a timeout from a member")
    @app_commands.describe(member="The member to unmute", reason="Reason for the unmute")
    @is_mod()
    async def unmute(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await member.timeout(None, reason=reason)
        embed = EmbedBuilder().title("Member Unmuted").description(f"{member.mention}'s timeout has been removed.").color("green").field("Reason", reason).build()
        await interaction.response.send_message(embed=embed)
        await log_mod_action(interaction.guild_id, str(member.id), member.name, "unmute", reason)

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(member="The member to warn", reason="Warning reason")
    @is_mod()
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        settings = await get_mod_settings(interaction.guild_id)
        if not settings.get("cmd_warn", True):
            return await interaction.response.send_message("Warn command is disabled.", ephemeral=True)
        if not await check_emergency_lock(interaction):
            return

        embed = EmbedBuilder().title("Member Warned").description(f"{member.mention} has been warned.").color("yellow").field("Reason", reason).build()
        await interaction.response.send_message(embed=embed)
        await log_mod_action(interaction.guild_id, str(member.id), member.name, "warn", reason)

        if settings.get("dm_on_action"):
            try:
                await member.send(f"You have been warned in {interaction.guild.name}.\nReason: {reason}")
            except:
                pass

    @app_commands.command(name="purge", description="Bulk delete messages in a channel")
    @app_commands.describe(count="Number of messages to delete (1-100)")
    @is_mod()
    async def purge(self, interaction: discord.Interaction, count: int = 10):
        if count < 1 or count > 100:
            return await interaction.response.send_message("Count must be between 1 and 100.", ephemeral=True)
        deleted = await interaction.channel.purge(limit=count)
        embed = EmbedBuilder().title("Messages Purged").description(f"Deleted {len(deleted)} messages.").color("blue").build()
        await interaction.response.send_message(embed=embed, delete_after=5)
        await log_mod_action(interaction.guild_id, "0", interaction.user.name, "purge", f"{len(deleted)} messages")

    @app_commands.command(name="settings", description="View current moderation settings")
    @is_mod()
    async def view_settings(self, interaction: discord.Interaction):
        settings = await get_mod_settings(interaction.guild_id)
        embed = EmbedBuilder() \
            .title("Moderation Settings") \
            .color("blue") \
            .field("DM on Action", "✅ Enabled" if settings.get("dm_on_action") else "❌ Disabled") \
            .field("Require Reason", "✅ Enabled" if settings.get("require_reason") else "❌ Disabled") \
            .field("Silent Mod", "✅ Enabled" if settings.get("silent_mod") else "❌ Disabled") \
            .field("Track Stats", "✅ Enabled" if settings.get("track_stats") else "❌ Disabled") \
            .field("Emergency Lock", "⚠️ LOCKED" if settings.get("emergency_lock") else "✅ Normal") \
            .build()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="lockdown", description="Toggle emergency server lockdown")
    @is_mod()
    async def lockdown(self, interaction: discord.Interaction):
        settings = await get_mod_settings(interaction.guild_id)
        current = settings.get("emergency_lock", False)
        settings["emergency_lock"] = not current
        await save_mod_settings(interaction.guild_id, settings)
        status = "LOCKED DOWN" if not current else "normal"
        embed = EmbedBuilder().title("Emergency Lockdown").description(f"Server is now in **{status}** mode.").color("red" if not current else "green").build()
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
