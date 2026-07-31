import discord
from discord.ext import commands
from discord import app_commands
import json
from typing import Optional

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db


WELCOME_DEFAULTS = {"enabled": False, "channel_id": None, "welcome_message": "Welcome {member} to {server}!", "goodbye_message": "{member} has left {server}.", "welcome_dm": False, "auto_role_id": None}


async def get_welcome_settings(guild_id: int):
    pool = await neon_db.get_pool()
    if not pool:
        return dict(WELCOME_DEFAULTS)
    row = await pool.fetchrow("SELECT settings FROM welcome_settings WHERE guild_id = $1", str(guild_id))
    return neon_db.parse_settings(row["settings"], WELCOME_DEFAULTS) if row else dict(WELCOME_DEFAULTS)


async def save_welcome_settings(guild_id: int, settings: dict):
    pool = await neon_db.get_pool()
    if not pool:
        return
    await pool.execute(
        "INSERT INTO welcome_settings (guild_id, settings) VALUES ($1, $2::jsonb) "
        "ON CONFLICT (guild_id) DO UPDATE SET settings = $2::jsonb",
        str(guild_id), json.dumps(settings),
    )


class Welcomer(commands.Cog, name="Welcomer"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = await get_welcome_settings(member.guild.id)
        if not settings.get("enabled"):
            return

        channel = member.guild.get_channel(settings.get("channel_id") or 0)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        msg = settings.get("welcome_message", "").replace("{member}", member.mention).replace("{server}", member.guild.name).replace("{count}", str(member.guild.member_count))
        try:
            await channel.send(msg)
        except:
            pass

        if settings.get("welcome_dm"):
            try:
                await member.send(f"Welcome to **{member.guild.name}**!")
            except:
                pass

        auto_role_id = settings.get("auto_role_id")
        if auto_role_id:
            role = member.guild.get_role(int(auto_role_id))
            if role:
                try:
                    await member.add_roles(role, reason="Auto-role on join")
                except:
                    pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        settings = await get_welcome_settings(member.guild.id)
        if not settings.get("enabled"):
            return
        channel = member.guild.get_channel(settings.get("channel_id") or 0)
        if not channel or not isinstance(channel, discord.TextChannel):
            return
        if not settings.get("goodbye_message"):
            return
        msg = settings.get("goodbye_message", "").replace("{member}", member.name).replace("{server}", member.guild.name)
        try:
            await channel.send(msg)
        except:
            pass

    welcomer_group = app_commands.Group(name="welcomer", description="Welcome message settings")

    @welcomer_group.command(name="toggle", description="Enable or disable welcome messages")
    async def toggle(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
        settings = await get_welcome_settings(interaction.guild_id)
        settings["enabled"] = not settings.get("enabled")
        await save_welcome_settings(interaction.guild_id, settings)
        status = "enabled" if settings["enabled"] else "disabled"
        await interaction.response.send_message(f"Welcome messages **{status}**.", ephemeral=True)

    @welcomer_group.command(name="channel", description="Set the welcome message channel")
    @app_commands.describe(channel="The channel for welcome messages")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
        settings = await get_welcome_settings(interaction.guild_id)
        settings["channel_id"] = channel.id
        await save_welcome_settings(interaction.guild_id, settings)
        await interaction.response.send_message(f"Welcome channel set to {channel.mention}.", ephemeral=True)

    @welcomer_group.command(name="message", description="Set the welcome message")
    @app_commands.describe(message="Use {member}, {server}, {count} as placeholders")
    async def set_message(self, interaction: discord.Interaction, message: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
        if len(message) > 500:
            return await interaction.response.send_message("Message too long (max 500).", ephemeral=True)
        settings = await get_welcome_settings(interaction.guild_id)
        settings["welcome_message"] = message
        await save_welcome_settings(interaction.guild_id, settings)
        embed = EmbedBuilder().title("Welcome Message Updated").description(f"New message:\n{message.replace('{member}', '@user').replace('{server}', interaction.guild.name).replace('{count}', str(interaction.guild.member_count))}").color("green").build()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @welcomer_group.command(name="goodbye", description="Set the goodbye message")
    @app_commands.describe(message="Use {member}, {server} as placeholders. Set to 'off' to disable.")
    async def set_goodbye(self, interaction: discord.Interaction, message: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
        settings = await get_welcome_settings(interaction.guild_id)
        settings["goodbye_message"] = None if message.lower() == "off" else message
        await save_welcome_settings(interaction.guild_id, settings)
        status = "disabled" if message.lower() == "off" else "updated"
        await interaction.response.send_message(f"Goodbye message {status}.", ephemeral=True)

    @welcomer_group.command(name="autorole", description="Set a role to give to new members on join")
    @app_commands.describe(role="The role to assign automatically. Leave empty to remove.")
    async def autorole(self, interaction: discord.Interaction, role: Optional[discord.Role] = None):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
        settings = await get_welcome_settings(interaction.guild_id)
        settings["auto_role_id"] = str(role.id) if role else None
        await save_welcome_settings(interaction.guild_id, settings)
        if role:
            await interaction.response.send_message(f"Auto-role set to {role.mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("Auto-role removed.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcomer(bot))
