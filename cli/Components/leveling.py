import discord
from discord.ext import commands
from discord import app_commands
import json
import math
import random
from typing import Optional

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db


LEVELING_DEFAULTS = {"enabled": True, "announce_channel_id": None, "xp_rate": 1.0, "xp_cooldown": 60, "level_roles": {}}
XP_PER_MESSAGE = (15, 25)
XP_COOLDOWN = 60


def xp_for_level(level: int) -> int:
    return 100 * level + 50 * (level - 1)


def level_from_xp(xp: int) -> int:
    lvl = 1
    while xp_for_level(lvl + 1) <= xp:
        lvl += 1
    return lvl


async def get_leveling_settings(guild_id: int):
    pool = await neon_db.get_pool()
    if not pool:
        return dict(LEVELING_DEFAULTS)
    row = await pool.fetchrow("SELECT settings FROM leveling_settings WHERE guild_id = $1", str(guild_id))
    return neon_db.parse_settings(row["settings"], LEVELING_DEFAULTS) if row else dict(LEVELING_DEFAULTS)


async def save_leveling_settings(guild_id: int, settings: dict):
    pool = await neon_db.get_pool()
    if not pool:
        return
    await pool.execute(
        "INSERT INTO leveling_settings (guild_id, settings) VALUES ($1, $2::jsonb) ON CONFLICT (guild_id) DO UPDATE SET settings = $2::jsonb",
        str(guild_id), json.dumps(settings),
    )


async def get_user_xp(guild_id: int, user_id: int):
    pool = await neon_db.get_pool()
    if not pool:
        return {"xp": 0, "level": 1}
    row = await pool.fetchrow(
        "SELECT xp FROM leveling_data WHERE guild_id = $1 AND user_id = $2", str(guild_id), str(user_id)
    )
    xp = row["xp"] if row else 0
    return {"xp": xp, "level": level_from_xp(xp)}


async def set_user_xp(guild_id: int, user_id: int, xp: int):
    pool = await neon_db.get_pool()
    if not pool:
        return
    await pool.execute(
        "INSERT INTO leveling_data (guild_id, user_id, xp) VALUES ($1, $2, $3) ON CONFLICT (guild_id, user_id) DO UPDATE SET xp = $3",
        str(guild_id), str(user_id), xp,
    )


class Leveling(commands.Cog, name="Leveling"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cooldowns = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        settings = await get_leveling_settings(message.guild.id)
        if not settings.get("enabled", True):
            return

        user_id = message.author.id
        now = message.created_at.timestamp()
        last = self.cooldowns.get((message.guild.id, user_id), 0)
        cooldown = settings.get("xp_cooldown", XP_COOLDOWN)
        if now - last < cooldown:
            return
        self.cooldowns[(message.guild.id, user_id)] = now

        rate = settings.get("xp_rate", 1.0)
        earned = random.randint(XP_PER_MESSAGE[0], XP_PER_MESSAGE[1])
        earned = int(earned * rate)

        data = await get_user_xp(message.guild.id, user_id)
        old_level = data["level"]
        new_xp = data["xp"] + earned
        await set_user_xp(message.guild.id, user_id, new_xp)
        new_level = level_from_xp(new_xp)

        if new_level > old_level:
            level_roles = settings.get("level_roles", {})
            role_id = level_roles.get(str(new_level))
            if role_id:
                role = message.guild.get_role(int(role_id))
                if role:
                    try:
                        await message.author.add_roles(role, reason=f"Level {new_level} reward")
                    except:
                        pass

            channel_id = settings.get("announce_channel_id")
            channel = message.guild.get_channel(channel_id) if channel_id else message.channel
            if channel:
                try:
                    await channel.send(f"🎉 {message.author.mention} reached **level {new_level}**!")
                except:
                    pass

    level_group = app_commands.Group(name="level", description="Leveling system commands")

    @level_group.command(name="rank", description="Check your or another member's rank")
    @app_commands.describe(member="The member to check")
    async def rank(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target = member or interaction.user
        data = await get_user_xp(interaction.guild_id, target.id)
        embed = EmbedBuilder().title(f"{target.display_name}'s Rank").color("blue") \
            .field("Level", str(data["level"])) \
            .field("XP", f"{data['xp']} / {xp_for_level(data['level'] + 1)}") \
            .thumbnail(target.display_avatar.url) \
            .build()
        await interaction.response.send_message(embed=embed)

    @level_group.command(name="leaderboard", description="Show the server XP leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        pool = await neon_db.get_pool()
        if not pool:
            return await interaction.response.send_message("Database unavailable.", ephemeral=True)
        rows = await pool.fetch(
            "SELECT user_id, xp FROM leveling_data WHERE guild_id = $1 ORDER BY xp DESC LIMIT 10",
            str(interaction.guild_id),
        )
        if not rows:
            return await interaction.response.send_message("No leveling data yet.", ephemeral=True)
        lines = []
        for i, row in enumerate(rows, 1):
            user = interaction.guild.get_member(int(row["user_id"]))
            name = user.display_name if user else row["user_id"][:8]
            lvl = level_from_xp(row["xp"])
            lines.append(f"**{i}.** {name} — Level {lvl} ({row['xp']} XP)")
        embed = EmbedBuilder().title("Leaderboard").description("\n".join(lines)).color("blue").build()
        await interaction.response.send_message(embed=embed)

    @level_group.command(name="toggle", description="Enable or disable XP gain")
    async def toggle(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
        settings = await get_leveling_settings(interaction.guild_id)
        settings["enabled"] = not settings.get("enabled", True)
        await save_leveling_settings(interaction.guild_id, settings)
        status = "enabled" if settings["enabled"] else "disabled"
        await interaction.response.send_message(f"XP system **{status}**.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))
