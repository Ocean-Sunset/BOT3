import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import string
import asyncio
from typing import Optional

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db


VERIFY_DEFAULTS = {"enabled": False, "channel_id": None, "verified_role_id": None, "log_channel_id": None, "type": "button", "captcha": False}


async def get_verify_settings(guild_id: int):
    pool = await neon_db.get_pool()
    if not pool:
        return dict(VERIFY_DEFAULTS)
    row = await pool.fetchrow("SELECT settings FROM verify_settings WHERE guild_id = $1", str(guild_id))
    return neon_db.parse_settings(row["settings"], VERIFY_DEFAULTS) if row else dict(VERIFY_DEFAULTS)


async def save_verify_settings(guild_id: int, settings: dict):
    pool = await neon_db.get_pool()
    if not pool:
        return
    await pool.execute(
        "INSERT INTO verify_settings (guild_id, settings) VALUES ($1, $2::jsonb) ON CONFLICT (guild_id) DO UPDATE SET settings = $2::jsonb",
        str(guild_id), json.dumps(settings),
    )


class VerifyView(discord.ui.View):
    def __init__(self, role_id: int):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.success, emoji="✅", custom_id="verify:click")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(self.role_id)
        if not role:
            return await interaction.response.send_message("Verification role not found.", ephemeral=True)
        if role in interaction.user.roles:
            return await interaction.response.send_message("You are already verified.", ephemeral=True)
        await interaction.user.add_roles(role, reason="Verified via button")
        await interaction.response.send_message("You have been verified!", ephemeral=True)


class CaptchaView(discord.ui.Modal, title="Verification"):
    def __init__(self, answer: str, role_id: int):
        super().__init__()
        self.answer = answer
        self.role_id = role_id
        self.code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.add_item(discord.ui.TextInput(label=f"Enter this code: {self.code}", placeholder="Type the code above", max_length=6))

    async def on_submit(self, interaction: discord.Interaction):
        if self.children[0].value.strip().upper() == self.code:
            role = interaction.guild.get_role(self.role_id)
            if role:
                await interaction.user.add_roles(role, reason="Verified via captcha")
                await interaction.response.send_message("Verification successful!", ephemeral=True)
            else:
                await interaction.response.send_message("Verification role not found.", ephemeral=True)
        else:
            await interaction.response.send_message("Incorrect code. Try again.", ephemeral=True)


class Verification(commands.Cog, name="Verification"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    verify_group = app_commands.Group(name="verify", description="Verification system commands")

    @verify_group.command(name="setup", description="Set up the verification panel")
    @app_commands.describe(channel="Channel for the verification panel", role="Role to assign on verification", captcha="Require captcha entry")
    async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role, captcha: bool = False):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You need Administrator permission.", ephemeral=True)
        settings = {"enabled": True, "channel_id": channel.id, "verified_role_id": role.id, "type": "captcha" if captcha else "button", "captcha": captcha}
        await save_verify_settings(interaction.guild_id, settings)
        if captcha:
            view = discord.ui.View()
            async def captcha_cb(i: discord.Interaction):
                await i.response.send_modal(CaptchaView("", role.id))
            btn = discord.ui.Button(label="Verify", style=discord.ButtonStyle.success, emoji="✅")
            btn.callback = captcha_cb
            view.add_item(btn)
        else:
            view = VerifyView(role.id)
        embed = EmbedBuilder().title("Verification").description("Click the button below to verify yourself.").color("green").build()
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"Verification panel set up in {channel.mention}.", ephemeral=True)

    @verify_group.command(name="config", description="View current verification settings")
    async def config(self, interaction: discord.Interaction):
        settings = await get_verify_settings(interaction.guild_id)
        if not settings.get("enabled"):
            return await interaction.response.send_message("Verification is not set up.", ephemeral=True)
        channel = interaction.guild.get_channel(settings.get("channel_id") or 0)
        role = interaction.guild.get_role(settings.get("verified_role_id") or 0)
        embed = EmbedBuilder().title("Verification Settings").color("blue") \
            .field("Status", "✅ Active") \
            .field("Channel", channel.mention if channel else "Not set") \
            .field("Verified Role", role.mention if role else "Not set") \
            .field("Type", "Captcha" if settings.get("captcha") else "Button") \
            .build()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @verify_group.command(name="remove", description="Remove the verification system")
    async def remove(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You need Administrator permission.", ephemeral=True)
        await save_verify_settings(interaction.guild_id, {"enabled": False})
        await interaction.response.send_message("Verification system removed.", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = await get_verify_settings(member.guild.id)
        if not settings.get("enabled"):
            return
        role_id = settings.get("verified_role_id")
        if not role_id:
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(Verification(bot))
