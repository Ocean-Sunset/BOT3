import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import asyncio
import datetime
from typing import Optional

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db


AUTO_DEFAULTS = {"auto_roles": {}, "bot_auto_role": None, "mute_evasion": False, "anti_raid": False}


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

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = await get_auto_settings(member.guild.id)
        for role_id_str in settings.get("auto_roles", {}).values():
            role = member.guild.get_role(int(role_id_str))
            if role:
                try:
                    await member.add_roles(role, reason="Auto-role")
                except:
                    pass
        if member.bot:
            bot_role_id = settings.get("bot_auto_role")
            if bot_role_id:
                role = member.guild.get_role(int(bot_role_id))
                if role:
                    try:
                        await member.add_roles(role, reason="Bot auto-role")
                    except:
                        pass

    auto_group = app_commands.Group(name="automation", description="Automation settings")

    @auto_group.command(name="autorole", description="Set a role to auto-assign to new members")
    @app_commands.describe(role="The role to auto-assign")
    async def set_autorole(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message("You need Manage Roles permission.", ephemeral=True)
        settings = await get_auto_settings(interaction.guild_id)
        settings["auto_roles"]["default"] = str(role.id)
        await save_auto_settings(interaction.guild_id, settings)
        await interaction.response.send_message(f"Auto-role set to {role.mention}.", ephemeral=True)

    @auto_group.command(name="botrole", description="Set a role for bots on join")
    @app_commands.describe(role="The role for bots")
    async def set_botrole(self, interaction: discord.Interaction, role: Optional[discord.Role] = None):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message("You need Manage Roles permission.", ephemeral=True)
        settings = await get_auto_settings(interaction.guild_id)
        settings["bot_auto_role"] = str(role.id) if role else None
        await save_auto_settings(interaction.guild_id, settings)
        await interaction.response.send_message(f"Bot auto-role {'set to ' + role.mention if role else 'removed'}.", ephemeral=True)

    @auto_group.command(name="config", description="View automation settings")
    async def config(self, interaction: discord.Interaction):
        settings = await get_auto_settings(interaction.guild_id)
        auto_roles = settings.get("auto_roles", {})
        role_mentions = []
        for rid in auto_roles.values():
            r = interaction.guild.get_role(int(rid))
            role_mentions.append(r.mention if r else rid)
        embed = EmbedBuilder().title("Automation Settings").color("blue") \
            .field("Auto-Roles", ", ".join(role_mentions) or "None") \
            .field("Bot Role", interaction.guild.get_role(int(settings.get("bot_auto_role") or 0)).mention if settings.get("bot_auto_role") else "None") \
            .build()
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Automation(bot))
