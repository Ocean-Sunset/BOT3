import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import string
import aiohttp
import datetime
import os
from typing import Optional

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db


def provider_key(settings: dict, provider: str, kind: str) -> str:
    """Resolve a reCAPTCHA/Turnstile key: guild override first, then bot-owner .env default."""
    from_env = os.environ.get(f"{provider.upper()}_{kind.upper()}", "")
    if isinstance(settings, dict) and settings.get(f"{provider}_{kind}"):
        return settings[f"{provider}_{kind}"]
    return from_env


def captcha_solve_url(provider: str) -> str:
    """Public URL where a user solves the captcha and copies a token."""
    base = os.environ.get("DASHBOARD_URL", "").rstrip("/")
    return f"{base}/captcha/{provider}"


VERIFY_DEFAULTS = {
    "enabled": False, "channel_id": None, "verified_role_id": None,
    "log_channel_id": None, "type": "button", "captcha": False,
    "message": "Click the button below to verify yourself.",
    "reaction_emoji": "✅",
    "recaptcha_site_key": "", "recaptcha_secret": "",
    "turnstile_site_key": "", "turnstile_secret": "",
}


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


async def _verify_done(interaction: discord.Interaction, role_id, role_label="verified"):
    role = interaction.guild.get_role(role_id)
    if not role:
        await interaction.response.send_message(
            embed=EmbedBuilder().title("Error").description("Verification role not found.").color("red").timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )
        return
    if role in interaction.user.roles:
        await interaction.response.send_message(
            embed=EmbedBuilder().title("ℹ️ Already Verified").description("You are already verified.").color("blue").timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )
        return
    await interaction.user.add_roles(role, reason=f"Verified via {role_label}")
    await interaction.response.send_message(
        embed=EmbedBuilder().title("✅ Verified").description("You have been verified!").color("green").timestamp(datetime.datetime.utcnow()).build(),
        ephemeral=True
    )


class VerifyButtonView(discord.ui.View):
    def __init__(self, role_id: int):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.success, emoji="✅", custom_id="verify:click")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _verify_done(interaction, self.role_id, "button")


class CaptchaModal(discord.ui.Modal, title="Verification"):
    def __init__(self, role_id: int):
        super().__init__()
        self.role_id = role_id
        self.code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.add_item(discord.ui.TextInput(label=f"Enter this code: {self.code}", placeholder="Type the code above", max_length=6))

    async def on_submit(self, interaction: discord.Interaction):
        if self.children[0].value.strip().upper() != self.code:
            await interaction.response.send_message(
                embed=EmbedBuilder().title("Failed").description("Incorrect code. Try again.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
            return
        await _verify_done(interaction, self.role_id, "captcha")


class CaptchaButtonView(discord.ui.View):
    def __init__(self, role_id: int):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.success, emoji="🔐", custom_id="verify:captcha")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CaptchaModal(self.role_id))


class ExternalCaptchaModal(discord.ui.Modal, title="Verification"):
    """Modal for reCAPTCHA / Turnstile: user solves at the given URL, pastes the token."""

    def __init__(self, role_id: int, url: str, provider: str):
        super().__init__()
        self.role_id = role_id
        self.provider = provider
        placeholder = f"Open {url} , solve the captcha, then paste the token here"
        if len(placeholder) > 100:
            placeholder = "Solve the captcha, then paste the token here"
        self.add_item(discord.ui.TextInput(label=f"Token from {provider}", placeholder=placeholder, required=True, max_length=2000, style=discord.TextStyle.paragraph))

    async def on_submit(self, interaction: discord.Interaction):
        token = self.children[0].value.strip()
        settings = await get_verify_settings(interaction.guild_id)
        secret = provider_key(settings, self.provider, "secret")
        verify_url = (
            "https://www.google.com/recaptcha/api/siteverify" if self.provider == "recaptcha"
            else "https://challenges.cloudflare.com/turnstile/v0/siteverify"
        )
        if not secret:
            await interaction.response.send_message("Verification captcha is not configured.", ephemeral=True)
            return
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(verify_url, data={"secret": secret, "response": token}) as resp:
                    data = await resp.json()
            if data.get("success"):
                await _verify_done(interaction, self.role_id, self.provider)
            else:
                await interaction.response.send_message(
                    embed=EmbedBuilder().title("Failed").description("Verification failed. Please try again.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"External captcha verify failed: {e}")
            await interaction.response.send_message("Could not verify captcha. Try again.", ephemeral=True)


class ExternalCaptchaButtonView(discord.ui.View):
    def __init__(self, role_id: int, url: str, provider: str):
        super().__init__(timeout=None)
        self.role_id = role_id
        self.provider = provider
        verify = discord.ui.Button(label="Verify", style=discord.ButtonStyle.success, emoji="🛡️", custom_id=f"verify:{provider}")
        async def cb(i: discord.Interaction):
            await i.response.send_modal(ExternalCaptchaModal(self.role_id, url, self.provider))
        verify.callback = cb
        self.add_item(verify)


class Verification(commands.Cog, name="Verification"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.panel_messages = {}  # message_id -> guild_id (for reaction tracking)

    async def _build_view(self, settings) -> discord.ui.View:
        vtype = settings.get("type", "button")
        role_id = int(settings.get("verified_role_id") or 0)
        if vtype == "reaction":
            return None  # reaction panels have no view
        if vtype == "captcha":
            return CaptchaButtonView(role_id)
        if vtype == "recaptcha":
            return ExternalCaptchaButtonView(role_id, captcha_solve_url("recaptcha"), "recaptcha")
        if vtype == "turnstile":
            return ExternalCaptchaButtonView(role_id, captcha_solve_url("turnstile"), "turnstile")
        return VerifyButtonView(role_id)

    async def _send_panel(self, guild: discord.Guild, settings) -> bool:
        channel = guild.get_channel(int(settings.get("channel_id") or 0))
        if not channel or not isinstance(channel, discord.TextChannel):
            return False
        role = guild.get_role(int(settings.get("verified_role_id") or 0))
        role_text = role.mention if role else "Verified"
        msg_text = settings.get("message") or "Click the button below to verify yourself."
        embed = EmbedBuilder().title("🔐 Verification").description(msg_text).color("green").field("After verifying", f"You'll receive the **{role_text}** role.").timestamp(datetime.datetime.utcnow()).build()

        vtype = settings.get("type", "button")
        if vtype == "reaction":
            view = discord.ui.View()
            message = await channel.send(embed=embed, view=view)
            emoji = settings.get("reaction_emoji", "✅")
            try:
                await message.add_reaction(emoji)
            except Exception:
                await message.add_reaction("✅")
            self.panel_messages[message.id] = guild.id
        else:
            view = await self._build_view(settings)
            await channel.send(embed=embed, view=view)
        return True

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if payload.message_id not in self.panel_messages:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        settings = await get_verify_settings(payload.guild_id)
        if not settings.get("enabled") or settings.get("type") != "reaction":
            return
        role = guild.get_role(int(settings.get("verified_role_id") or 0))
        member = guild.get_member(payload.user_id)
        if not role or not member:
            return
        try:
            if role not in member.roles:
                await member.add_roles(role, reason="Verified via reaction")
                await member.send("You have been verified!")
        except Exception as e:
            logger.error(f"Reaction verify failed: {e}")

    verify_group = app_commands.Group(name="verify", description="Verification system commands")

    @verify_group.command(name="setup", description="Set up the verification panel")
    @app_commands.describe(channel="Channel for the verification panel", role="Role to assign on verification", type="Verification method")
    @app_commands.choices(type=[
        app_commands.Choice(name="Button", value="button"),
        app_commands.Choice(name="Reaction Role", value="reaction"),
        app_commands.Choice(name="Captcha Code", value="captcha"),
        app_commands.Choice(name="reCAPTCHA", value="recaptcha"),
        app_commands.Choice(name="Cloudflare Turnstile", value="turnstile"),
    ])
    async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role, type: str = "button"):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You need Administrator permission.", ephemeral=True)
        settings = await get_verify_settings(interaction.guild_id)
        settings.update({"enabled": True, "channel_id": channel.id, "verified_role_id": role.id, "type": type})
        await save_verify_settings(interaction.guild_id, settings)
        ok = await self._send_panel(interaction.guild, settings)
        await interaction.response.send_message(
            embed=EmbedBuilder().title("Setup Complete").description(f"Verification panel {'deployed in ' + channel.mention if ok else 'saved but channel not found'}.").color("green").timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )

    @verify_group.command(name="deploy", description="(Re)post the verification panel to the configured channel")
    async def deploy(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You need Administrator permission.", ephemeral=True)
        settings = await get_verify_settings(interaction.guild_id)
        ok = await self._send_panel(interaction.guild, settings)
        await interaction.response.send_message(
            embed=EmbedBuilder().title("Panel Deployed").description("Verification panel posted." if ok else "Configure a channel first.").color("green" if ok else "red").timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )

    @verify_group.command(name="config", description="View current verification settings")
    async def config(self, interaction: discord.Interaction):
        settings = await get_verify_settings(interaction.guild_id)
        channel = interaction.guild.get_channel(settings.get("channel_id") or 0)
        role = interaction.guild.get_role(settings.get("verified_role_id") or 0)
        embed = EmbedBuilder().title("Verification Settings").color("blue") \
            .field("Status", "Active" if settings.get("enabled") else "Inactive") \
            .field("Channel", channel.mention if channel else "Not set") \
            .field("Verified Role", role.mention if role else "Not set") \
            .field("Type", settings.get("type", "button")) \
            .timestamp(datetime.datetime.utcnow()) \
            .build()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @verify_group.command(name="remove", description="Remove the verification system")
    async def remove(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You need Administrator permission.", ephemeral=True)
        await save_verify_settings(interaction.guild_id, {"enabled": False})
        await interaction.response.send_message("Verification system removed.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Verification(bot))
