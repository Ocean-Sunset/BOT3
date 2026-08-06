import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import asyncio
import datetime
from typing import Optional

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db


AUTO_DEFAULTS = {
    "auto_roles": {},
    "bot_auto_role": None,
    "mute_evasion": False,
    "anti_raid": False,
    "anti_raid_threshold": 5,
    "anti_raid_window": 10,
    "min_account_age_days": 0,
    "auto_nickname": None,
}


async def get_auto_settings(guild_id: int):
    pool = await neon_db.get_pool()
    if not pool:
        return dict(AUTO_DEFAULTS)
    row = await pool.fetchrow("SELECT settings FROM automation_settings WHERE guild_id = $1", str(guild_id))
    return neon_db.parse_settings(row["settings"], AUTO_DEFAULTS) if row else dict(AUTO_DEFAULTS)


async def save_auto_settings(guild_id: int, settings: dict):
    pool = await neon_db.get_pool()
    if not pool:
        return
    await pool.execute(
        "INSERT INTO automation_settings (guild_id, settings) VALUES ($1, $2::jsonb) ON CONFLICT (guild_id) DO UPDATE SET settings = $2::jsonb",
        str(guild_id), json.dumps(settings),
    )


class Automation(commands.Cog, name="Automation"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.recent_joins = {}

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = await get_auto_settings(member.guild.id)

        min_age = settings.get("min_account_age_days", 0)
        if min_age > 0:
            account_age = (datetime.datetime.utcnow() - member.created_at).days
            if account_age < min_age:
                try:
                    await member.kick(reason=f"Account too new ({account_age} days, min: {min_age})")
                    logger.info(f"Kicked {member.name} from {member.guild.name}: account too new")
                except Exception as e:
                    logger.warning(f"Failed to kick new account: {e}")
                return

        if settings.get("anti_raid"):
            threshold = settings.get("anti_raid_threshold", 5)
            window = settings.get("anti_raid_window", 10)
            guild_id = member.guild.id
            now = datetime.datetime.utcnow().timestamp()
            if guild_id not in self.recent_joins:
                self.recent_joins[guild_id] = []
            self.recent_joins[guild_id] = [t for t in self.recent_joins[guild_id] if now - t < window]
            self.recent_joins[guild_id].append(now)
            if len(self.recent_joins[guild_id]) >= threshold:
                try:
                    await member.kick(reason="Anti-raid: too many joins in short time")
                    logger.warning(f"Anti-raid kicked {member.name} from {member.guild.name}")
                except Exception as e:
                    logger.warning(f"Anti-raid kick failed: {e}")
                return

        for role_id_str in settings.get("auto_roles", {}).values():
            role = member.guild.get_role(int(role_id_str))
            if role:
                try:
                    await member.add_roles(role, reason="Auto-role")
                except Exception as e:
                    logger.warning(f"Failed to add auto-role: {e}")

        if member.bot:
            bot_role_id = settings.get("bot_auto_role")
            if bot_role_id:
                role = member.guild.get_role(int(bot_role_id))
                if role:
                    try:
                        await member.add_roles(role, reason="Bot auto-role")
                    except Exception as e:
                        logger.warning(f"Failed to add bot auto-role: {e}")

        auto_nick = settings.get("auto_nickname")
        if auto_nick and not member.bot:
            try:
                nick = auto_nick.replace("{user}", member.name).replace("{server}", member.guild.name)
                await member.edit(nick=nick[:32], reason="Auto-nickname")
            except Exception as e:
                logger.warning(f"Failed to set auto-nickname: {e}")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        settings = await get_auto_settings(after.guild.id)
        if not settings.get("mute_evasion"):
            return
        if before.is_timed_out() and not after.is_timed_out():
            if before.timed_out_until and before.timed_out_until > discord.utils.utcnow():
                try:
                    await after.timeout(before.timed_out_until, reason="Mute evasion detected")
                    logger.info(f"Re-applied mute to {after.name} in {after.guild.name} (mute evasion)")
                except Exception as e:
                    logger.warning(f"Failed to re-apply mute: {e}")

    auto_group = app_commands.Group(name="automation", description="Automation settings")

    @auto_group.command(name="autorole", description="Set a role to auto-assign to new members")
    @app_commands.describe(role="The role to auto-assign")
    async def set_autorole(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Roles permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_auto_settings(interaction.guild_id)
        settings["auto_roles"]["default"] = str(role.id)
        await save_auto_settings(interaction.guild_id, settings)
        await interaction.response.send_message(
            embed=EmbedBuilder().title("Auto-Role Set").description(f"New members will receive {role.mention}").color("green").timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )

    @auto_group.command(name="botrole", description="Set a role for bots on join")
    @app_commands.describe(role="The role for bots")
    async def set_botrole(self, interaction: discord.Interaction, role: Optional[discord.Role] = None):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Roles permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_auto_settings(interaction.guild_id)
        settings["bot_auto_role"] = str(role.id) if role else None
        await save_auto_settings(interaction.guild_id, settings)
        if role:
            await interaction.response.send_message(
                embed=EmbedBuilder().title("Bot Auto-Role Set").description(f"Bots will receive {role.mention}").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=EmbedBuilder().title("Bot Auto-Role Removed").description("Bot auto-role has been removed.").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )

    @auto_group.command(name="antiraid", description="Configure anti-raid protection")
    @app_commands.describe(enabled="Enable or disable", threshold="Max joins before triggering", window="Time window in seconds")
    async def antiraid(self, interaction: discord.Interaction, enabled: bool, threshold: int = 5, window: int = 10):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Administrator permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_auto_settings(interaction.guild_id)
        settings["anti_raid"] = enabled
        settings["anti_raid_threshold"] = threshold
        settings["anti_raid_window"] = window
        await save_auto_settings(interaction.guild_id, settings)
        status = "enabled" if enabled else "disabled"
        color = "green" if enabled else "red"
        embed = (
            EmbedBuilder()
            .title("Anti-Raid Updated")
            .description(f"Anti-raid protection **{status}**.")
            .color(color)
            .field("Threshold", f"{threshold} joins")
            .field("Window", f"{window} seconds")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @auto_group.command(name="minage", description="Set minimum account age for new members")
    @app_commands.describe(days="Minimum account age in days (0 to disable)")
    async def minage(self, interaction: discord.Interaction, days: int):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Administrator permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        if days < 0:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Invalid").description("Days cannot be negative.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_auto_settings(interaction.guild_id)
        settings["min_account_age_days"] = days
        await save_auto_settings(interaction.guild_id, settings)
        if days > 0:
            await interaction.response.send_message(
                embed=EmbedBuilder().title("Account Age Set").description(f"Accounts newer than **{days} days** will be kicked.").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=EmbedBuilder().title("Account Age Disabled").description("No minimum account age requirement.").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )

    @auto_group.command(name="muteevasion", description="Toggle mute evasion detection")
    @app_commands.describe(enabled="Enable or disable")
    async def muteevasion(self, interaction: discord.Interaction, enabled: bool):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Administrator permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_auto_settings(interaction.guild_id)
        settings["mute_evasion"] = enabled
        await save_auto_settings(interaction.guild_id, settings)
        status = "enabled" if enabled else "disabled"
        color = "green" if enabled else "red"
        await interaction.response.send_message(
            embed=EmbedBuilder().title("Mute Evasion Updated").description(f"Mute evasion detection **{status}**.").color(color).timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )

    @auto_group.command(name="nickname", description="Set auto-nickname for new members")
    @app_commands.describe(nickname="Nickname template (use {user} and {server}). Leave empty to disable.")
    async def nickname(self, interaction: discord.Interaction, nickname: str = None):
        if not interaction.user.guild_permissions.manage_nicknames:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Nicknames permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_auto_settings(interaction.guild_id)
        settings["auto_nickname"] = nickname
        await save_auto_settings(interaction.guild_id, settings)
        if nickname:
            await interaction.response.send_message(
                embed=EmbedBuilder().title("Auto-Nickname Set").description(f"New members will be nicknamed: `{nickname}`").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=EmbedBuilder().title("Auto-Nickname Disabled").description("Auto-nickname has been removed.").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )

    @auto_group.command(name="config", description="View automation settings")
    async def config(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_auto_settings(interaction.guild_id)
        auto_roles = settings.get("auto_roles", {})
        role_mentions = []
        for rid in auto_roles.values():
            r = interaction.guild.get_role(int(rid))
            role_mentions.append(r.mention if r else str(rid))
        bot_role_id = settings.get("bot_auto_role")
        bot_role = interaction.guild.get_role(int(bot_role_id)) if bot_role_id else None
        embed = (
            EmbedBuilder()
            .title("Automation Settings")
            .color("blue")
            .field("Auto-Roles", ", ".join(role_mentions) or "None")
            .field("Bot Role", bot_role.mention if bot_role else "None")
            .field("Anti-Raid", "Enabled" if settings.get("anti_raid") else "Disabled")
            .field("Anti-Raid Threshold", f"{settings.get('anti_raid_threshold', 5)} joins in {settings.get('anti_raid_window', 10)}s")
            .field("Mute Evasion", "Enabled" if settings.get("mute_evasion") else "Disabled")
            .field("Min Account Age", f"{settings.get('min_account_age_days', 0)} days")
            .field("Auto-Nickname", settings.get("auto_nickname") or "Disabled")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Automation(bot))
