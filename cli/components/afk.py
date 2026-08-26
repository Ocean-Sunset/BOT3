"""
Member-facing AFK status.

When a member marks themselves AFK (with an optional reason), anyone who pings
them or replies to them in that server automatically gets a notice. Sending any
message clears your own AFK status.

Commands:
  /afk [reason]   mark yourself AFK (no reason clears it if already set)
"""

import time
import datetime

import discord
from discord.ext import commands
from discord import app_commands

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db
from Ediscord.builders import emoji_title


AFK_COOLDOWN = 30  # seconds between repeat notices for the same AFK user in a channel


def _err(msg: str):
    return (
        EmbedBuilder()
        .title(emoji_title("error", "Error"))
        .description(msg)
        .color("red")
        .timestamp(datetime.datetime.utcnow())
        .build()
    )


def _ok(msg: str, title="Success"):
    return (
        EmbedBuilder()
        .title(emoji_title("success", title))
        .description(msg)
        .color("green")
        .timestamp(datetime.datetime.utcnow())
        .build()
    )


def _info(msg: str):
    return (
        EmbedBuilder()
        .title(emoji_title("info", "Heads up"))
        .description(msg)
        .color("blue")
        .timestamp(datetime.datetime.utcnow())
        .build()
    )


class AFK(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cooldowns = {}  # (guild_id, channel_id, user_id) -> last_ts

    @app_commands.command(name="afk", description="Mark yourself as AFK with an optional reason.")
    @app_commands.describe(reason="Message shown when someone pings you (leave empty to clear)")
    async def afk(self, interaction: discord.Interaction, reason: str = ""):
        guild_id = str(interaction.guild_id) if interaction.guild_id else None
        if not guild_id:
            return await interaction.response.send_message(
                embed=_err("AFK only works inside a server."), ephemeral=True
            )
        uid = str(interaction.user.id)
        existing = await neon_db.get_afk(guild_id, uid)
        reason = (reason or "").strip()

        if not reason:
            if existing:
                await neon_db.clear_afk(guild_id, uid)
                return await interaction.response.send_message(
                    embed=_ok("You're no longer AFK.", "AFK cleared"), ephemeral=True
                )
            return await interaction.response.send_message(
                embed=_info("You're not AFK. Add a reason to set yourself AFK, e.g. `/afk eating dinner`."),
                ephemeral=True,
            )

        await neon_db.set_afk(guild_id, uid, reason, interaction.user.display_name)
        await interaction.response.send_message(
            embed=_ok(f"I'll let people know you're AFK:\n> {reason}", "AFK set"),
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.webhook_id:
            return
        guild = message.guild
        if not guild:
            return
        guild_id = str(guild.id)
        author_id = str(message.author.id)

        # Auto-clear the author's AFK when they send a message.
        me = await neon_db.get_afk(guild_id, author_id)
        if me:
            await neon_db.clear_afk(guild_id, author_id)
            try:
                await message.channel.send(
                    f"Welcome back, {message.author.mention}! I've removed your AFK."
                )
            except Exception:
                pass

        # Collect users referenced in this message (pings + reply target).
        candidates = {str(u.id) for u in message.mentions}
        ref = message.reference
        if ref and getattr(ref, "resolved", None) and isinstance(ref.resolved, discord.Message):
            ref_author = ref.resolved.author
            if ref_author and not ref_author.bot:
                candidates.add(str(ref_author.id))
        candidates.discard(author_id)
        if not candidates:
            return

        # Responder respects the guild-level enable toggle.
        settings = await neon_db.get_afk_settings(guild_id)
        if not settings.get("enabled", True):
            return

        now = time.time()
        notices = []
        for cid in candidates:
            row = await neon_db.get_afk(guild_id, cid)
            if not row:
                continue
            key = (guild_id, str(message.channel.id), str(row["user_id"]))
            if now - self._cooldowns.get(key, 0) < AFK_COOLDOWN:
                continue
            self._cooldowns[key] = now
            reason = (row.get("reason") or "").strip()
            since = row.get("since") or now
            name = row.get("nickname") or f"<@{row['user_id']}>"
            since_txt = discord.utils.format_dt(datetime.datetime.fromtimestamp(since), "R")
            if reason:
                notices.append(f"\ud83d\udeab **{name}** is AFK: {reason} _(since {since_txt})_")
            else:
                notices.append(f"\ud83d\udeab **{name}** is AFK _(since {since_txt})_")

        if notices:
            try:
                await message.channel.send("\n".join(notices))
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(AFK(bot))
