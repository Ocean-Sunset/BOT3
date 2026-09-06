import discord
from discord.ext import commands
import json
import time

from Ediscord import logger
from Ediscord import db as neon_db


# ── Helpers ────────────────────────────────────────────────────────────────

async def _get_stat(key: str):
    pool = await neon_db.get_pool()
    if not pool:
        return None
    row = await pool.fetchrow("SELECT value FROM bot_stats WHERE key = ?", key)
    return row["value"] if row else None


async def _set_stat(key: str, value: str):
    pool = await neon_db.get_pool()
    if not pool:
        return
    await pool.execute(
        "INSERT INTO bot_stats (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT (key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        key, value, time.time(),
    )


def _skey(guild_id: int, suffix: str) -> str:
    return f"more_sticky_{suffix}_{guild_id}"


async def _get_bool(guild_id: int, suffix: str, default: bool = False) -> bool:
    val = await _get_stat(_skey(guild_id, suffix))
    if val is None:
        return default
    return val == "1"


async def _get_str(guild_id: int, suffix: str, default: str = "") -> str:
    val = await _get_stat(_skey(guild_id, suffix))
    return val if val else default


async def _get_embed(guild_id: int):
    val = await _get_stat(_skey(guild_id, "embed"))
    if not val:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return None


# ── Sticky state per guild: {channel_id: message_count} ────────────────────

class StickyMessages(commands.Cog):
    """Automatically re-post a sticky message in a configured channel."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._counters: dict[int, int] = {}  # channel_id -> msg count since last sticky
        self._posted: dict[int, discord.Message] = {}  # channel_id -> last sticky msg
        self._processing: set[int] = set()  # channels currently re-posting
        self._STICKY_INTERVAL = 5  # re-post every N messages

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        guild_id = message.guild.id
        ch_id = message.channel.id

        enabled = await _get_bool(guild_id, "enabled")
        if not enabled:
            return

        channel_id_str = await _get_str(guild_id, "channel_id")
        if not channel_id_str or str(ch_id) != channel_id_str:
            return

        # Don't count our own sticky messages
        if message.author == self.bot.user:
            return

        self._counters[ch_id] = self._counters.get(ch_id, 0) + 1

        if self._counters[ch_id] >= self._STICKY_INTERVAL and ch_id not in self._processing:
            self._processing.add(ch_id)
            try:
                await self._repost_sticky(message.guild, message.channel)
                self._counters[ch_id] = 0
            finally:
                self._processing.discard(ch_id)

    async def _repost_sticky(self, guild: discord.Guild, channel: discord.TextChannel):
        """Delete old sticky (if any) and post a new one."""
        old = self._posted.get(channel.id)
        if old:
            try:
                await old.delete()
            except (discord.NotFound, discord.Forbidden):
                pass

        message_type = await _get_str(guild.id, "message_type", "basic")

        embed = None
        content = None

        if message_type == "custom":
            embed_data = await _get_embed(guild.id)
            if embed_data:
                embed = self._build_embed(embed_data, guild, channel)
            else:
                content = "(no embed configured)"
        else:
            msg = await _get_str(guild.id, "message")
            if msg:
                content = self._apply_vars(msg, guild, channel)
            else:
                content = "(no sticky message configured)"

        try:
            new_msg = await channel.send(content=content, embed=embed)
            self._posted[channel.id] = new_msg
        except discord.Forbidden:
            pass

    def _build_embed(self, data: dict, guild: discord.Guild, channel: discord.TextChannel) -> discord.Embed:
        e = discord.Embed()
        if data.get("title"):
            e.title = data["title"]
        if data.get("description"):
            e.description = self._apply_vars(data["description"], guild, channel)
        if data.get("url"):
            e.url = data["url"]
        color = data.get("color", "#5865f2")
        if color:
            try:
                e.color = int(color.lstrip("#"), 16)
            except ValueError:
                pass
        if data.get("author_name"):
            e.set_author(name=data["author_name"], icon_url=data.get("author_icon"))
        if data.get("footer_text"):
            e.set_footer(text=data["footer_text"], icon_url=data.get("footer_icon"))
        if data.get("image_url"):
            e.set_image(url=data["image_url"])
        if data.get("thumbnail_url"):
            e.set_thumbnail(url=data["thumbnail_url"])
        for f in data.get("fields", []):
            e.add_field(name=f.get("name", ""), value=self._apply_vars(f.get("value", ""), guild, channel), inline=f.get("inline", False))
        return e

    def _apply_vars(self, text: str, guild: discord.Guild, channel: discord.TextChannel) -> str:
        return (
            text
            .replace("{server}", guild.name)
            .replace("{channel}", channel.name)
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(StickyMessages(bot))
