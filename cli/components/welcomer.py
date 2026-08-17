import discord
from discord.ext import commands
from discord import app_commands
import json
import datetime
import io
import os
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
import aiohttp

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db
from Ediscord.builders import embed_from_dict, emoji_title


WELCOME_DEFAULTS = {
    "enabled": False,
    "channel_id": None,
    "goodbye_channel_id": None,
    "welcome_message": "Welcome {member} to {server}!",
    "welcome_mode": "basic",
    "welcome_embed_data": {},
    "welcome_image_config": None,
    "goodbye_message": "{member} has left {server}.",
    "goodbye_mode": "basic",
    "goodbye_embed_data": {},
    "goodbye_image_config": None,
    "welcome_dm": False,
    "welcome_dm_message": "Welcome to **{server}**! Make sure to read the rules.",
    "auto_role_ids": [],
    "bot_auto_role": None,
    "auto_nickname": None,
}

DEFAULT_IMAGE_CONFIG = {
    "enabled": True,
    "width": 950,
    "height": 450,
    "gradient": {"color1": "#1a1a2e", "color2": "#16213e"},
    "bg_image": "",
    "avatar_border": "#ffffff",
    "avatar_size": 150,
    "avatar_y": 60,
    "text_layers": [
        {"content": "Welcome!", "y": 260, "font_size": 38, "color": "#ffffff", "enabled": True},
        {"content": "{name}", "y": 310, "font_size": 26, "color": "#aaaaaa", "enabled": True},
        {"content": "Member #{count}", "y": 350, "font_size": 18, "color": "#666666", "enabled": True},
    ],
}


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\calibrib.ttf" if bold else "C:\\Windows\\Fonts\\calibri.ttf",
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _circle_avatar(avatar_bytes: bytes, size: int, border_color: str = "#ffffff") -> Image.Image:
    raw = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    raw = raw.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(raw, mask=mask)
    border = 6
    bordered = Image.new("RGBA", (size + border * 2, size + border * 2), (0, 0, 0, 0))
    bc = tuple(int(border_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    ImageDraw.Draw(bordered).ellipse((0, 0, size + border * 2 - 1, size + border * 2 - 1), fill=bc + (255,))
    bordered.paste(result, (border, border), result)
    return bordered


def render_image_text(template: str, member: discord.Member) -> str:
    return (template
            .replace("{name}", member.name)
            .replace("{server}", member.guild.name)
            .replace("{count}", str(member.guild.member_count)))


async def generate_card_image(member: discord.Member, config: dict) -> bytes:
    if not config:
        config = DEFAULT_IMAGE_CONFIG
    w = config.get("width", 950)
    h = config.get("height", 450)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background
    bg_url = config.get("bg_image", "")
    if bg_url:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(bg_url) as resp:
                    if resp.status == 200:
                        bg_data = await resp.read()
                        bg = Image.open(io.BytesIO(bg_data)).convert("RGBA").resize((w, h), Image.LANCZOS)
                        img.paste(bg, (0, 0))
        except Exception as e:
            logger.warning(f"Failed to load background image: {e}")

    grad = config.get("gradient", {})
    if grad:
        c1 = tuple(int(grad.get("color1", "#1a1a2e").lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        c2 = tuple(int(grad.get("color2", "#16213e").lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        grad_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad_layer)
        for y_pos in range(h):
            ratio = y_pos / h
            r = int(c1[0] + (c2[0] - c1[0]) * ratio)
            g = int(c1[1] + (c2[1] - c1[1]) * ratio)
            b = int(c1[2] + (c2[2] - c1[2]) * ratio)
            gd.line([(0, y_pos), (w, y_pos)], fill=(r, g, b, 180))
        img = Image.alpha_composite(img, grad_layer)
        draw = ImageDraw.Draw(img)

    # Avatar
    try:
        avatar_bytes = await member.display_avatar.read()
        av_size = config.get("avatar_size", 150)
        av_y = config.get("avatar_y", 60)
        av_border = config.get("avatar_border", "#ffffff")
        av = _circle_avatar(avatar_bytes, av_size, av_border)
        av_x = (w - av.width) // 2
        img.paste(av, (av_x, av_y), av)
        draw = ImageDraw.Draw(img)
    except Exception as e:
        logger.warning(f"Failed to load avatar for card: {e}")

    # Text layers
    for layer in config.get("text_layers", []):
        if not layer.get("enabled", True):
            continue
        content = render_image_text(layer.get("content", ""), member)
        font_size = layer.get("font_size", 24)
        font = _load_font(font_size, bold=True)
        color_hex = layer.get("color", "#ffffff")
        color = tuple(int(color_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        bbox = draw.textbbox((0, 0), content, font=font)
        tw = bbox[2] - bbox[0]
        tx = (w - tw) // 2
        ty = layer.get("y", h // 2)
        draw.text((tx, ty), content, font=font, fill=color + (255,))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


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


def render_welcome(template: str, member: discord.Member) -> str:
    return (template
            .replace("{member}", member.mention)
            .replace("{member.name}", member.name)
            .replace("{member.tag}", member.discriminator if member.discriminator != "0" else "")
            .replace("{member.nick}", member.display_name)
            .replace("{member.id}", str(member.id))
            .replace("{avatar}", str(member.display_avatar.url))
            .replace("{server}", member.guild.name)
            .replace("{server.id}", str(member.guild.id))
            .replace("{count}", str(member.guild.member_count))
            .replace("{server.membercount}", str(member.guild.member_count)))


def render_welcome_embed(data: dict, member: discord.Member) -> dict:
    """Render welcome placeholders inside a custom embed dict's text fields."""
    out = dict(data or {})
    for key in ("title", "description", "footer_text", "author_name", "url"):
        if out.get(key):
            out[key] = render_welcome(str(out[key]), member)
    return out


class Welcomer(commands.Cog, name="Welcomer"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = await get_welcome_settings(member.guild.id)
        if not settings.get("enabled"):
            return

        channel = member.guild.get_channel(int(settings.get("channel_id") or 0))
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        # Custom embed mode renders the user-configured embed; otherwise the default styled embed
        mode = settings.get("welcome_mode", "basic")
        image_config = settings.get("welcome_image_config")
        card_file = None
        if image_config and image_config.get("enabled"):
            try:
                card_bytes = await generate_card_image(member, image_config)
                card_file = discord.File(io.BytesIO(card_bytes), filename="welcome.png")
            except Exception as e:
                logger.warning(f"Failed to generate welcome card: {e}")

        if mode == "custom" and settings.get("welcome_embed_data"):
            try:
                embed = embed_from_dict(render_welcome_embed(settings["welcome_embed_data"], member))
                if card_file:
                    embed.set_image(url="attachment://welcome.png")
                await channel.send(embed=embed, file=card_file) if card_file else await channel.send(embed=embed)
            except Exception as e:
                logger.warning(f"Failed to send custom welcome embed: {e}")
        else:
            msg = render_welcome(settings.get("welcome_message", ""), member)
            try:
                embed = (
                    EmbedBuilder()
                    .title(emoji_title("welcome", "Welcome!"))
                    .description(msg)
                    .color("green")
                    .thumbnail(member.display_avatar.url)
                    .field("Account Created", discord.utils.format_dt(member.created_at, style="R"))
                    .field("Member Count", f"{member.guild.member_count:,}")
                    .footer(f"User ID: {str(member.id)}")
                    .timestamp(datetime.datetime.utcnow())
                    .build()
                )
                if card_file:
                    embed.set_image(url="attachment://welcome.png")
                await channel.send(embed=embed, file=card_file) if card_file else await channel.send(embed=embed)
            except Exception as e:
                logger.warning(f"Failed to send welcome message: {e}")

        if settings.get("welcome_dm"):
            dm_msg = render_welcome(settings.get("welcome_dm_message", "Welcome to **{server}**!"), member)
            try:
                dm_embed = (
                    EmbedBuilder()
                    .title(emoji_title("welcome", f"Welcome to {member.guild.name}!"))
                    .description(dm_msg)
                    .color("green")
                    .thumbnail(member.guild.icon.url if member.guild.icon else None)
                    .timestamp(datetime.datetime.utcnow())
                    .build()
                )
                await member.send(embed=dm_embed)
            except (discord.Forbidden, discord.HTTPException):
                pass

        # Auto-role: add every configured role (falls back to the old single-role key)
        auto_roles = settings.get("auto_role_ids") or []
        if not auto_roles and settings.get("auto_role_id"):
            auto_roles = [settings["auto_role_id"]]
        for rid in auto_roles:
            role = member.guild.get_role(int(rid))
            if role:
                try:
                    await member.add_roles(role, reason="Auto-role on join")
                except Exception as e:
                    logger.warning(f"Failed to add auto-role {rid}: {e}")

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
    async def on_member_remove(self, member: discord.Member):
        settings = await get_welcome_settings(member.guild.id)
        if not settings.get("enabled"):
            return
        goodbye_ch_id = settings.get("goodbye_channel_id") or settings.get("channel_id")
        channel = member.guild.get_channel(int(goodbye_ch_id or 0))
        if not channel or not isinstance(channel, discord.TextChannel):
            return
        if not settings.get("goodbye_message"):
            return
        msg = render_welcome(settings.get("goodbye_message", ""), member)
        mode = settings.get("goodbye_mode", "basic")
        image_config = settings.get("goodbye_image_config")
        card_file = None
        if image_config and image_config.get("enabled"):
            try:
                card_bytes = await generate_card_image(member, image_config)
                card_file = discord.File(io.BytesIO(card_bytes), filename="goodbye.png")
            except Exception as e:
                logger.warning(f"Failed to generate goodbye card: {e}")
        try:
            if mode == "custom" and settings.get("goodbye_embed_data"):
                embed = embed_from_dict(render_welcome_embed(settings["goodbye_embed_data"], member))
                if card_file:
                    embed.set_image(url="attachment://goodbye.png")
                await channel.send(embed=embed, file=card_file) if card_file else await channel.send(embed=embed)
            else:
                embed = (
                    EmbedBuilder()
                    .title(emoji_title("goodbye", "Goodbye"))
                    .description(msg)
                    .color("red")
                    .thumbnail(member.display_avatar.url)
                    .field("Member Count", f"{member.guild.member_count:,}")
                    .footer(f"User ID: {str(member.id)}")
                    .timestamp(datetime.datetime.utcnow())
                    .build()
                )
                if card_file:
                    embed.set_image(url="attachment://goodbye.png")
                await channel.send(embed=embed, file=card_file) if card_file else await channel.send(embed=embed)
        except Exception as e:
            logger.warning(f"Failed to send goodbye message: {e}")

    welcomer_group = app_commands.Group(name="welcomer", description="Welcome message settings")

    @welcomer_group.command(name="toggle", description="Enable or disable welcome messages")
    async def toggle(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_welcome_settings(interaction.guild_id)
        settings["enabled"] = not settings.get("enabled")
        await save_welcome_settings(interaction.guild_id, settings)
        status = "enabled" if settings["enabled"] else "disabled"
        color = "green" if settings["enabled"] else "red"
        await interaction.response.send_message(
            embed=EmbedBuilder().title(emoji_title("success", "Welcomer Toggled")).description(f"Welcome messages **{status}**.").color(color).timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )

    @welcomer_group.command(name="channel", description="Set the welcome message channel")
    @app_commands.describe(channel="The channel for welcome messages")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_welcome_settings(interaction.guild_id)
        settings["channel_id"] = str(channel.id)
        await save_welcome_settings(interaction.guild_id, settings)
        await interaction.response.send_message(
            embed=EmbedBuilder().title(emoji_title("success", "Channel Set")).description(f"Welcome channel set to {channel.mention}").color("green").timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )

    @welcomer_group.command(name="goodbyechannel", description="Set the goodbye message channel")
    @app_commands.describe(channel="The channel for goodbye messages. Leave empty to use the welcome channel.")
    async def set_goodbye_channel(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_welcome_settings(interaction.guild_id)
        settings["goodbye_channel_id"] = str(channel.id) if channel else None
        await save_welcome_settings(interaction.guild_id, settings)
        if channel:
            await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("success", "Goodbye Channel Set")).description(f"Goodbye channel set to {channel.mention}").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("info", "Goodbye Channel Reset")).description("Goodbye messages will use the welcome channel.").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )

    @welcomer_group.command(name="message", description="Set the welcome message")
    @app_commands.describe(message="Use {member}, {server}, {count} as placeholders")
    async def set_message(self, interaction: discord.Interaction, message: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        if len(message) > 500:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Too Long")).description("Message too long (max 500 characters).").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_welcome_settings(interaction.guild_id)
        settings["welcome_message"] = message
        await save_welcome_settings(interaction.guild_id, settings)
        preview = render_welcome(message, interaction.user)
        embed = (
            EmbedBuilder()
            .title(emoji_title("success", "Welcome Message Updated"))
            .description(f"**Preview:**\n{preview}")
            .color("green")
            .field("Placeholders", "`{member}` `{member.name}` `{server}` `{count}`")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @welcomer_group.command(name="goodbye", description="Set the goodbye message")
    @app_commands.describe(message="Use {member}, {server} as placeholders. Set to 'off' to disable.")
    async def set_goodbye(self, interaction: discord.Interaction, message: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_welcome_settings(interaction.guild_id)
        settings["goodbye_message"] = None if message.lower() == "off" else message
        await save_welcome_settings(interaction.guild_id, settings)
        if message.lower() == "off":
            await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("info", "Goodbye Disabled")).description("Goodbye messages have been disabled.").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        else:
            preview = render_welcome(message, interaction.user)
            await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("success", "Goodbye Message Updated")).description(f"**Preview:**\n{preview}").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )

    @welcomer_group.command(name="autorole", description="Set a role to give to new members on join")
    @app_commands.describe(role="The role to assign automatically. Leave empty to remove.")
    async def autorole(self, interaction: discord.Interaction, role: Optional[discord.Role] = None):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_welcome_settings(interaction.guild_id)
        settings["auto_role_id"] = str(role.id) if role else None
        await save_welcome_settings(interaction.guild_id, settings)
        if role:
            await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("success", "Auto-Role Set")).description(f"New members will receive {role.mention}").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("info", "Auto-Role Removed")).description("Auto-role has been removed.").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )

    @welcomer_group.command(name="botrole", description="Set a role for bots on join")
    @app_commands.describe(role="The role for bots. Leave empty to remove.")
    async def botrole(self, interaction: discord.Interaction, role: Optional[discord.Role] = None):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Roles permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_welcome_settings(interaction.guild_id)
        settings["bot_auto_role"] = str(role.id) if role else None
        await save_welcome_settings(interaction.guild_id, settings)
        if role:
            await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("success", "Bot Auto-Role Set")).description(f"Bots will receive {role.mention}").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("info", "Bot Auto-Role Removed")).description("Bot auto-role has been removed.").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )

    @welcomer_group.command(name="nickname", description="Set auto-nickname for new members")
    @app_commands.describe(nickname="Nickname template (use {user} and {server}). Leave empty to disable.")
    async def nickname(self, interaction: discord.Interaction, nickname: str = None):
        if not interaction.user.guild_permissions.manage_nicknames:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Nicknames permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_welcome_settings(interaction.guild_id)
        settings["auto_nickname"] = nickname
        await save_welcome_settings(interaction.guild_id, settings)
        if nickname:
            await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("success", "Auto-Nickname Set")).description(f"New members will be nicknamed: `{nickname}`").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("info", "Auto-Nickname Disabled")).description("Auto-nickname has been removed.").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )

    @welcomer_group.command(name="test", description="Test the welcome message")
    async def test(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_welcome_settings(interaction.guild_id)
        msg = render_welcome(settings.get("welcome_message", "Welcome {member}!"), interaction.user)
        image_config = settings.get("welcome_image_config")
        card_file = None
        if image_config and image_config.get("enabled"):
            try:
                card_bytes = await generate_card_image(interaction.user, image_config)
                card_file = discord.File(io.BytesIO(card_bytes), filename="welcome.png")
            except Exception as e:
                logger.warning(f"Failed to generate test card: {e}")
        if settings.get("welcome_embed", True):
            embed = (
                EmbedBuilder()
                .title(emoji_title("success", "Welcome! (Test)"))
                .description(msg)
                .color("green")
                .thumbnail(interaction.user.display_avatar.url)
                .field("Account Created", discord.utils.format_dt(interaction.user.created_at, style="R"))
                .field("Member Count", f"{interaction.guild.member_count:,}")
                .footer(f"User ID: {str(interaction.user.id)}")
                .timestamp(datetime.datetime.utcnow())
                .build()
            )
            if card_file:
                embed.set_image(url="attachment://welcome.png")
            await interaction.response.send_message(embed=embed, file=card_file, ephemeral=True) if card_file else await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("success", "Welcome! (Test)")).description(msg).color("green").timestamp(datetime.datetime.utcnow()).build(),
                file=card_file, ephemeral=True
            ) if card_file else await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("success", "Welcome! (Test)")).description(msg).color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )

    @welcomer_group.command(name="config", description="View current welcomer configuration")
    async def config(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_welcome_settings(interaction.guild_id)
        channel_id = settings.get("channel_id")
        channel = interaction.guild.get_channel(int(channel_id)) if channel_id else None
        goodbye_ch_id = settings.get("goodbye_channel_id")
        goodbye_channel = interaction.guild.get_channel(int(goodbye_ch_id)) if goodbye_ch_id else None
        auto_role_id = settings.get("auto_role_id")
        auto_role = interaction.guild.get_role(int(auto_role_id)) if auto_role_id else None
        bot_role_id = settings.get("bot_auto_role")
        bot_role = interaction.guild.get_role(int(bot_role_id)) if bot_role_id else None
        embed = (
            EmbedBuilder()
            .title(emoji_title("info", "Welcomer Configuration"))
            .color("blue")
            .field("Enabled", "Yes" if settings.get("enabled") else "No")
            .field("Welcome Channel", channel.mention if channel else "Not set")
            .field("Goodbye Channel", goodbye_channel.mention if goodbye_channel else "Same as welcome")
            .field("Welcome Embed", "Yes" if settings.get("welcome_embed", True) else "No")
            .field("Goodbye Embed", "Yes" if settings.get("goodbye_embed", True) else "No")
            .field("Welcome DM", "Yes" if settings.get("welcome_dm") else "No")
            .field("Auto-Role", auto_role.mention if auto_role else "None")
            .field("Bot Auto-Role", bot_role.mention if bot_role else "None")
            .field("Auto-Nickname", settings.get("auto_nickname") or "Disabled")
            .field("Welcome Message", settings.get("welcome_message", "Not set")[:1024])
            .field("Goodbye Message", settings.get("goodbye_message") or "Disabled")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @welcomer_group.command(name="dm", description="Configure welcome DM messages")
    @app_commands.describe(enabled="Enable or disable welcome DMs", message="The DM message (optional)")
    async def dm(self, interaction: discord.Interaction, enabled: bool, message: str = None):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_welcome_settings(interaction.guild_id)
        settings["welcome_dm"] = enabled
        if message:
            settings["welcome_dm_message"] = message
        await save_welcome_settings(interaction.guild_id, settings)
        status = "enabled" if enabled else "disabled"
        color = "green" if enabled else "red"
        embed = (
            EmbedBuilder()
            .title(emoji_title("success", "Welcome DM Updated"))
            .description(f"Welcome DMs are now **{status}**.")
            .color(color)
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        if enabled and message:
            embed.add_field(name="DM Message", value=message[:1024])
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcomer(bot))
