import discord
from discord.ext import commands
from discord import app_commands
import asyncio
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
    # ── Modlog ──
    "modlog_channel_id": None,
    # ── Ban ──
    "ban_dm": True, "ban_purge": True,
    "ban_message": "{username} has been banned.", "ban_message_enabled": True,
    # ── Temp ban ──
    "tempban_dm": True, "tempban_purge": True,
    "tempban_message": "{username} has been temporarily banned.", "tempban_message_enabled": True,
    "tempban_duration": 1440,  # minutes
    # ── Mute ──
    "mute_dm": True, "mute_duration": 60,
    # ── Kick ──
    "kick_dm": True, "kick_message": "{username} has been kicked.", "kick_message_enabled": True,
    # ── Warn ──
    "warn_dm": True, "warn_message": "{username} has been warned.", "warn_message_enabled": True,
}


def render_template(template: str, member: discord.Member, reason: str = "", msg_count: int = 0) -> str:
    """Replace template placeholders with member/context values."""
    if not template:
        return ""
    guild = member.guild
    joined = member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "unknown"
    return (template
            .replace("{username}", member.name)
            .replace("{name}", member.display_name)
            .replace("{server}", guild.name if guild else "")
            .replace("{servername}", guild.name if guild else "")
            .replace("{servermembercount}", str(guild.member_count if guild else 0))
            .replace("{datejoined}", joined)
            .replace("{messagessent}", str(msg_count))
            .replace("{reason}", reason))


async def send_modlog(guild, settings, embed):
    """Send a log embed to the configured modlog channel."""
    channel_id = settings.get("modlog_channel_id")
    if not channel_id:
        return
    channel = guild.get_channel(int(channel_id))
    if channel:
        try:
            await channel.send(embed=embed)
        except Exception:
            pass


async def safe_dm(member, content):
    try:
        await member.send(content)
    except Exception:
        pass


async def get_mod_settings(guild_id: int):
    pool = await neon_db.get_pool()
    if not pool:
        return dict(MOD_DEFAULTS)
    row = await pool.fetchrow(
        "SELECT settings FROM mod_settings WHERE guild_id = $1", str(guild_id)
    )
    if row:
        return neon_db.parse_settings(row["settings"], MOD_DEFAULTS)
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
        self.msg_counts = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        key = (str(message.guild.id), str(message.author.id))
        self.msg_counts[key] = self.msg_counts.get(key, 0) + 1

    def get_msg_count(self, guild_id, user_id) -> int:
        return self.msg_counts.get((str(guild_id), str(user_id)), 0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="The member to kick", reason="Reason for the kick (optional)")
    @is_mod()
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        settings = await get_mod_settings(interaction.guild_id)
        if not settings.get("cmd_kick", True):
            return await interaction.response.send_message("Kick command is disabled.", ephemeral=True)
        if not await check_emergency_lock(interaction):
            return
        if not reason:
            reason = "No reason provided"

        view = ConfirmationView()
        await interaction.response.send_message(
            f"Are you sure you want to kick {member.mention}?", view=view, ephemeral=True
        )
        await view.wait()
        if view.value is True:
            if settings.get("kick_dm", True):
                await safe_dm(member, f"You have been kicked from {interaction.guild.name}.\nReason: {reason}")
            await member.kick(reason=reason)

            if not settings.get("silent_mod"):
                embed = EmbedBuilder().title("Member Kicked").description(f"{member.mention} has been kicked.").color("red").field("Reason", reason).build()
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("Member kicked.", ephemeral=True)

            # Announcement in channel with custom message
            msg = render_template(settings.get("kick_message", ""), member, reason, self.get_msg_count(interaction.guild_id, member.id))
            if msg and settings.get("kick_message_enabled", True) and not settings.get("silent_mod"):
                try:
                    await interaction.channel.send(msg)
                except Exception:
                    pass

            # Modlog
            log_embed = EmbedBuilder().title("Member Kicked").description(f"{member.mention} ({member.id})").color("red").field("Moderator", interaction.user.mention).field("Reason", reason).build()
            await send_modlog(interaction.guild, settings, log_embed)
            await log_mod_action(interaction.guild_id, str(member.id), member.name, "kick", reason)
        else:
            await interaction.followup.send("Kick cancelled.", ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(member="The member to ban", reason="Reason for the ban (optional)", delete_days="Days of messages to delete (0-7)")
    @is_mod()
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = None, delete_days: int = None):
        settings = await get_mod_settings(interaction.guild_id)
        if not settings.get("cmd_ban", True):
            return await interaction.response.send_message("Ban command is disabled.", ephemeral=True)
        if not await check_emergency_lock(interaction):
            return
        if not reason:
            reason = "No reason provided"
        if delete_days is None:
            delete_days = 1 if settings.get("ban_purge", True) else 0
        if delete_days < 0 or delete_days > 7:
            return await interaction.response.send_message("Delete days must be between 0 and 7.", ephemeral=True)

        view = ConfirmationView()
        await interaction.response.send_message(f"Are you sure you want to ban {member.mention}?", view=view, ephemeral=True)
        await view.wait()
        if view.value is True:
            if settings.get("ban_dm", True):
                await safe_dm(member, f"You have been banned from {interaction.guild.name}.\nReason: {reason}")
            await member.ban(reason=reason, delete_message_days=delete_days)

            if not settings.get("silent_mod"):
                embed = EmbedBuilder().title("Member Banned").description(f"{member.mention} has been banned.").color("red").field("Reason", reason).build()
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("Member banned.", ephemeral=True)

            msg = render_template(settings.get("ban_message", ""), member, reason, self.get_msg_count(interaction.guild_id, member.id))
            if msg and settings.get("ban_message_enabled", True) and not settings.get("silent_mod"):
                try:
                    await interaction.channel.send(msg)
                except Exception:
                    pass

            log_embed = EmbedBuilder().title("Member Banned").description(f"{member.mention} ({member.id})").color("red").field("Moderator", interaction.user.mention).field("Reason", reason).field("Delete Days", str(delete_days)).build()
            await send_modlog(interaction.guild, settings, log_embed)
            await log_mod_action(interaction.guild_id, str(member.id), member.name, "ban", reason)
        else:
            await interaction.followup.send("Ban cancelled.", ephemeral=True)

    @app_commands.command(name="tempban", description="Temporarily ban a member (auto-unbans after duration)")
    @app_commands.describe(member="The member to temporarily ban", duration="Duration in minutes", reason="Reason for the temp ban (optional)")
    @is_mod()
    async def tempban(self, interaction: discord.Interaction, member: discord.Member, duration: int = None, reason: str = None):
        settings = await get_mod_settings(interaction.guild_id)
        if not settings.get("cmd_ban", True):
            return await interaction.response.send_message("Ban command is disabled.", ephemeral=True)
        if not await check_emergency_lock(interaction):
            return
        if duration is None:
            duration = int(settings.get("tempban_duration", 1440))
        if duration <= 0:
            return await interaction.response.send_message("Duration must be positive.", ephemeral=True)
        if not reason:
            reason = "No reason provided"

        delete_days = 1 if settings.get("tempban_purge", True) else 0

        view = ConfirmationView()
        await interaction.response.send_message(f"Are you sure you want to temp-ban {member.mention} for {duration} minutes?", view=view, ephemeral=True)
        await view.wait()
        if view.value is True:
            if settings.get("tempban_dm", True):
                await safe_dm(member, f"You have been temporarily banned from {interaction.guild.name} for {duration} minutes.\nReason: {reason}")
            await member.ban(reason=f"Temp ban ({duration}m): {reason}", delete_message_days=delete_days)

            if not settings.get("silent_mod"):
                embed = EmbedBuilder().title("Member Temp-Banned").description(f"{member.mention} has been banned for **{duration}** minutes.").color("red").field("Reason", reason).build()
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("Member temp-banned.", ephemeral=True)

            msg = render_template(settings.get("tempban_message", ""), member, reason, self.get_msg_count(interaction.guild_id, member.id))
            if msg and settings.get("tempban_message_enabled", True) and not settings.get("silent_mod"):
                try:
                    await interaction.channel.send(msg)
                except Exception:
                    pass

            log_embed = EmbedBuilder().title("Member Temp-Banned").description(f"{member.mention} ({member.id})").color("red").field("Moderator", interaction.user.mention).field("Duration", f"{duration} minutes").field("Reason", reason).build()
            await send_modlog(interaction.guild, settings, log_embed)
            await log_mod_action(interaction.guild_id, str(member.id), member.name, "tempban", f"{duration}min - {reason}")

            # Auto-unban after duration
            self.bot.loop.create_task(self._auto_unban(interaction.guild_id, member.id, duration))
        else:
            await interaction.followup.send("Temp ban cancelled.", ephemeral=True)

    async def _auto_unban(self, guild_id, user_id, duration_minutes):
        await asyncio.sleep(duration_minutes * 60)
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        try:
            user = await self.bot.fetch_user(user_id)
            await guild.unban(user, reason="Temp ban expired")
            logger.info(f"Auto-unbanned {user_id} in {guild_id} (temp ban expired)")
        except Exception as e:
            logger.error(f"Auto-unban failed: {e}")

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
    @app_commands.describe(member="The member to mute", duration="Duration in minutes (optional)", reason="Reason for the mute (optional)")
    @is_mod()
    async def mute(self, interaction: discord.Interaction, member: discord.Member, duration: int = None, reason: str = None):
        settings = await get_mod_settings(interaction.guild_id)
        if not settings.get("cmd_timeout", True):
            return await interaction.response.send_message("Timeout command is disabled.", ephemeral=True)
        if not await check_emergency_lock(interaction):
            return
        if duration is None:
            duration = int(settings.get("mute_duration", 60))
        if not reason:
            reason = "No reason provided"

        until = discord.utils.utcnow() + datetime.timedelta(minutes=duration)
        await member.timeout(until, reason=reason)

        if not settings.get("silent_mod"):
            embed = EmbedBuilder().title("Member Muted").description(f"{member.mention} has been timed out.").color("orange").field("Duration", f"{duration} minutes").field("Reason", reason).build()
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Member muted.", ephemeral=True)

        if settings.get("mute_dm", True):
            await safe_dm(member, f"You have been muted in {interaction.guild.name} for {duration} minutes.\nReason: {reason}")

        log_embed = EmbedBuilder().title("Member Muted").description(f"{member.mention} ({member.id})").color("orange").field("Moderator", interaction.user.mention).field("Duration", f"{duration} minutes").field("Reason", reason).build()
        await send_modlog(interaction.guild, settings, log_embed)
        await log_mod_action(interaction.guild_id, str(member.id), member.name, "mute", f"{duration}min - {reason}")

    @app_commands.command(name="unmute", description="Remove a timeout from a member")
    @app_commands.describe(member="The member to unmute", reason="Reason for the unmute")
    @is_mod()
    async def unmute(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await member.timeout(None, reason=reason)
        embed = EmbedBuilder().title("Member Unmuted").description(f"{member.mention}'s timeout has been removed.").color("green").field("Reason", reason).build()
        await interaction.response.send_message(embed=embed)
        await log_mod_action(interaction.guild_id, str(member.id), member.name, "unmute", reason)

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(member="The member to warn", reason="Warning reason (optional)")
    @is_mod()
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        settings = await get_mod_settings(interaction.guild_id)
        if not settings.get("cmd_warn", True):
            return await interaction.response.send_message("Warn command is disabled.", ephemeral=True)
        if not await check_emergency_lock(interaction):
            return
        if not reason:
            reason = "No reason provided"

        if not settings.get("silent_mod"):
            embed = EmbedBuilder().title("Member Warned").description(f"{member.mention} has been warned.").color("yellow").field("Reason", reason).build()
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Member warned.", ephemeral=True)

        msg = render_template(settings.get("warn_message", ""), member, reason, self.get_msg_count(interaction.guild_id, member.id))
        if msg and settings.get("warn_message_enabled", True) and not settings.get("silent_mod"):
            try:
                await interaction.channel.send(msg)
            except Exception:
                pass

        if settings.get("warn_dm", True):
            await safe_dm(member, f"You have been warned in {interaction.guild.name}.\nReason: {reason}")

        log_embed = EmbedBuilder().title("Member Warned").description(f"{member.mention} ({member.id})").color("yellow").field("Moderator", interaction.user.mention).field("Reason", reason).build()
        await send_modlog(interaction.guild, settings, log_embed)
        await log_mod_action(interaction.guild_id, str(member.id), member.name, "warn", reason)

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
