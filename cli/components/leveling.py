import discord
from discord.ext import commands
from discord import app_commands
import json
import math
import random
import datetime
from typing import Optional

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db
from Ediscord.builders import embed_from_dict, emoji_title


LEVELING_DEFAULTS = {
    "enabled": True,
    "announce_channel_id": None,
    "xp_rate": 1.0,
    "xp_cooldown": 60,
    "random_xp": True,
    "level_roles": {},
    "role_xp_multipliers": {},
    "level_up_message": "🎉 {user} reached **level {level}**!",
    "level_up_message_mode": "basic", "level_up_embed": {},
    "xp_per_message_min": 15,
    "xp_per_message_max": 25,
}
XP_PER_MESSAGE = (15, 25)
XP_COOLDOWN = 60


def xp_for_level(level: int) -> int:
    return 100 * level + 50 * (level - 1)


def level_from_xp(xp: int) -> int:
    lvl = 1
    while xp_for_level(lvl + 1) <= xp:
        lvl += 1
    return lvl


def create_progress_bar(current: int, maximum: int, length: int = 10) -> str:
    if maximum <= 0:
        return "░" * length
    filled = int((current / maximum) * length)
    filled = min(filled, length)
    return "▓" * filled + "░" * (length - filled)


def format_level_up_message(
    template: str,
    message: discord.Message,
    level: int,
    xp: int,
    xp_needed: int,
    granted_role=None,
) -> str:
    """Replace {vars} in the level-up message with real values."""
    member = message.author
    role_str = granted_role.mention if granted_role else "none"
    replacements = {
        "{user}": member.mention,
        "{mention}": member.mention,
        "{name}": member.display_name,
        "{avatar}": str(member.display_avatar.url),
        "{level}": str(level),
        "{next_level}": str(level + 1),
        "{xp}": str(xp),
        "{xp_needed}": str(xp_needed),
        "{role}": role_str,
        "{servername}": message.guild.name,
        "{server}": message.guild.name,
        "{membercount}": str(message.guild.member_count or 0),
    }
    out = template
    for key, value in replacements.items():
        out = out.replace(key, value)
    return out


def render_embed_vars(data: dict, message: discord.Message, level: int, xp: int, xp_needed: int, granted_role=None) -> dict:
    """Render level-up variables inside an embed's text fields."""
    out = dict(data)
    for key in ("title", "description", "footer_text", "author_name", "url"):
        if out.get(key):
            out[key] = format_level_up_message(str(out[key]), message, level, xp, xp_needed, granted_role)
    return out


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

        base_rate = settings.get("xp_rate", 1.0)
        xp_min = settings.get("xp_per_message_min", 15)
        xp_max = settings.get("xp_per_message_max", 25)
        if settings.get("random_xp", True):
            earned = random.randint(xp_min, xp_max)
        else:
            earned = xp_min
        # Role-specific multipliers: apply the highest one the member holds
        role_mult = 1.0
        multipliers = settings.get("role_xp_multipliers", {})
        if isinstance(multipliers, dict) and multipliers:
            for role in message.author.roles:
                try:
                    rmult = multipliers.get(str(role.id))
                except Exception:
                    rmult = None
                if rmult:
                    role_mult = max(role_mult, float(rmult))
        rate = base_rate * role_mult
        earned = int(earned * rate)
        if earned <= 0:
            return

        data = await get_user_xp(message.guild.id, user_id)
        old_level = data["level"]
        new_xp = data["xp"] + earned
        await set_user_xp(message.guild.id, user_id, new_xp)
        new_level = level_from_xp(new_xp)

        if new_level > old_level:
            level_roles = settings.get("level_roles", {})
            granted_role = None
            role_id = level_roles.get(str(new_level))
            if role_id:
                role = message.guild.get_role(int(role_id))
                if role:
                    try:
                        await message.author.add_roles(role, reason=f"Level {new_level} reward")
                        granted_role = role
                    except Exception as e:
                        logger.warning(f"Failed to add level role: {e}")

            channel_id = settings.get("announce_channel_id")
            channel = message.guild.get_channel(int(channel_id)) if channel_id else message.channel
            if channel:
                try:
                    level_up_msg = settings.get("level_up_message", "🎉 {user} reached **level {level}**!")
                    xp_needed = xp_for_level(new_level + 1) - new_xp
                    mode = settings.get("level_up_message_mode", "basic")
                    if mode == "custom" and settings.get("level_up_embed"):
                        data = render_embed_vars(
                            settings.get("level_up_embed") or {}, message=message,
                            level=new_level, xp=new_xp, xp_needed=xp_needed, granted_role=granted_role,
                        )
                        embed = embed_from_dict(data)
                        await channel.send(embed=embed)
                    else:
                        msg = format_level_up_message(
                            level_up_msg,
                            message=message,
                            level=new_level,
                            xp=new_xp,
                            xp_needed=xp_needed,
                            granted_role=granted_role,
                        )
                        await channel.send(msg)
                except Exception as e:
                    logger.warning(f"Failed to send level up message: {e}")

    level_group = app_commands.Group(name="level", description="Leveling system commands")

    @level_group.command(name="rank", description="Check your or another member's rank")
    @app_commands.describe(member="The member to check")
    async def rank(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target = member or interaction.user
        data = await get_user_xp(interaction.guild_id, target.id)
        current_xp = data["xp"]
        current_level = data["level"]
        next_level_xp = xp_for_level(current_level + 1)
        current_level_xp = xp_for_level(current_level)
        xp_in_level = current_xp - current_level_xp
        xp_needed = next_level_xp - current_level_xp
        progress_bar = create_progress_bar(xp_in_level, xp_needed, 15)
        embed = (
            EmbedBuilder()
            .title(emoji_title("rank", f"{target.display_name}'s Rank"))
            .color("blue")
            .thumbnail(target.display_avatar.url)
            .field("Level", str(current_level))
            .field("Total XP", f"{current_xp:,}")
            .field("Progress", f"{progress_bar}\n{xp_in_level:,} / {xp_needed:,} XP to next level")
            .field("Next Level", f"Level {current_level + 1} at {next_level_xp:,} XP")
            .footer(f"User ID: {str(target.id)}")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)

    @level_group.command(name="leaderboard", description="Show the server XP leaderboard")
    @app_commands.describe(page="Page number (10 per page)")
    async def leaderboard(self, interaction: discord.Interaction, page: int = 1):
        pool = await neon_db.get_pool()
        if not pool:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Error")).description("Database unavailable.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        offset = (page - 1) * 10
        rows = await pool.fetch(
            "SELECT user_id, xp FROM leveling_data WHERE guild_id = $1 ORDER BY xp DESC LIMIT 10 OFFSET $2",
            str(interaction.guild_id), offset,
        )
        total_rows = await pool.fetchrow(
            "SELECT COUNT(*) as count FROM leveling_data WHERE guild_id = $1",
            str(interaction.guild_id),
        )
        total_users = total_rows["count"] if total_rows else 0
        total_pages = math.ceil(total_users / 10) if total_users > 0 else 1
        if not rows:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("info", "Leaderboard")).description("No leveling data yet.").color("blue").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        lines = []
        for i, row in enumerate(rows, offset + 1):
            user = interaction.guild.get_member(int(row["user_id"]))
            name = user.display_name if user else f"User {row['user_id'][:8]}"
            lvl = level_from_xp(row["xp"])
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
            lines.append(f"{medal} {name} - Level {lvl} ({row['xp']:,} XP)")
        embed = (
            EmbedBuilder()
            .title(emoji_title("leaderboard", "XP Leaderboard"))
            .description("\n".join(lines))
            .color("gold")
            .footer(f"Page {page}/{total_pages} | Total: {total_users} users")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)

    @level_group.command(name="toggle", description="Enable or disable XP gain")
    async def toggle(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_leveling_settings(interaction.guild_id)
        settings["enabled"] = not settings.get("enabled", True)
        await save_leveling_settings(interaction.guild_id, settings)
        status = "enabled" if settings["enabled"] else "disabled"
        color = "green" if settings["enabled"] else "red"
        embed = (
            EmbedBuilder()
            .title(emoji_title("success", "XP System Toggled"))
            .description(f"XP system is now **{status}**.")
            .color(color)
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @level_group.command(name="setxp", description="Set a user's XP (admin only)")
    @app_commands.describe(member="The member", xp="The XP amount")
    async def setxp(self, interaction: discord.Interaction, member: discord.Member, xp: int):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        if xp < 0:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Invalid XP")).description("XP cannot be negative.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        await set_user_xp(interaction.guild_id, member.id, xp)
        new_level = level_from_xp(xp)
        embed = (
            EmbedBuilder()
            .title(emoji_title("success", "XP Updated"))
            .description(f"Set {member.mention}'s XP to **{xp:,}**")
            .color("green")
            .field("New Level", str(new_level))
            .field("Moderator", interaction.user.mention)
            .footer(f"User ID: {str(member.id)}")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)

    @level_group.command(name="reset", description="Reset a user's XP (admin only)")
    @app_commands.describe(member="The member to reset")
    async def reset(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        await set_user_xp(interaction.guild_id, member.id, 0)
        embed = (
            EmbedBuilder()
            .title(emoji_title("info", "XP Reset"))
            .description(f"Reset {member.mention}'s XP to 0")
            .color("orange")
            .field("Moderator", interaction.user.mention)
            .footer(f"User ID: {str(member.id)}")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)

    @level_group.command(name="config", description="View leveling configuration")
    async def config(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_leveling_settings(interaction.guild_id)
        channel_id = settings.get("announce_channel_id")
        channel = interaction.guild.get_channel(int(channel_id)) if channel_id else None
        level_roles = settings.get("level_roles", {})
        roles_str = "\n".join([f"Level {lvl}: <@&{rid}>" for lvl, rid in level_roles.items()]) if level_roles else "None configured"
        embed = (
            EmbedBuilder()
            .title(emoji_title("info", "Leveling Configuration"))
            .color("blue")
            .field("Enabled", "Yes" if settings.get("enabled") else "No")
            .field("XP Rate", f"{settings.get('xp_rate', 1.0)}x")
            .field("XP Cooldown", f"{settings.get('xp_cooldown', 60)}s")
            .field("XP per Message", f"{settings.get('xp_per_message_min', 15)}-{settings.get('xp_per_message_max', 25)}")
            .field("Announce Channel", channel.mention if channel else "Current channel")
            .field("Level Roles", roles_str[:1024])
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @level_group.command(name="setrole", description="Set a role reward for a specific level")
    @app_commands.describe(level="The level to reward", role="The role to give")
    async def setrole(self, interaction: discord.Interaction, level: int, role: discord.Role):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        if level < 1:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Invalid Level")).description("Level must be at least 1.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_leveling_settings(interaction.guild_id)
        settings["level_roles"][str(level)] = str(role.id)
        await save_leveling_settings(interaction.guild_id, settings)
        embed = (
            EmbedBuilder()
            .title(emoji_title("success", "Level Role Set"))
            .description(f"Users who reach **level {level}** will receive {role.mention}")
            .color("green")
            .field("XP Required", f"{xp_for_level(level):,} XP")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))
