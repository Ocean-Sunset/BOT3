import io
import os
import re
import time
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from Ediscord import logger
from Ediscord import db as neon_db
from components.leveling import get_user_xp


# Must match website/api/index.py PROFILE_DEFAULTS
PROFILE_DEFAULTS = {
    "enabled": False,
    "bg_type": "gradient",
    "gradient_from": "#5865f2",
    "gradient_to": "#eb459e",
    "solid_color": "#1a1a1a",
    "bg_image_url": "",
    "bg_opacity": 35,
    "accent_auto": True,
    "accent_color": "#5865f2",
    "text_color": "#ffffff",
    "show_level": True,
    "show_joinage": True,
    "show_roles": True,
    "bio_enabled": True,
    "footer_text": "",
}

CARD_W, CARD_H = 900, 360
AVATAR_SIZE = 150
AVATAR_X, AVATAR_RING = 48, 6
TEXT_X = AVATAR_X + AVATAR_SIZE + AVATAR_RING * 2 + 42
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


async def get_profile_settings(guild_id: int):
    return await neon_db.load_cached_settings("profile_settings", guild_id, PROFILE_DEFAULTS)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _safe_hex(value, fallback: str) -> str:
    return value if isinstance(value, str) and HEX_RE.match(value) else fallback


def _dim(rgb: tuple, factor: float = 0.62) -> tuple:
    return tuple(int(c * factor) for c in rgb)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int = 3) -> list:
    lines = []
    for raw_line in text.splitlines():
        words = raw_line.split(" ")
        cur = ""
        for word in words:
            trial = (cur + " " + word).strip()
            if draw.textlength(trial, font=font) <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
                if len(lines) == max_lines:
                    return lines
        lines.append(cur)
        if len(lines) == max_lines:
            break
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    if lines and len(lines) == max_lines:
        # ellipsize the last line if text remains
        last = lines[-1]
        while last and draw.textlength(last + "...", font=font) > max_width:
            last = last[:-1]
        lines[-1] = last + "..."
    return [ln for ln in lines if ln]


async def _fetch_bytes(url: str) -> Optional[bytes]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.read()
    except Exception as e:
        logger.debug(f"profile fetch failed for {url}: {e}")
    return None


def _cover_resize(img: Image.Image, w: int, h: int) -> Image.Image:
    sw, sh = img.size
    scale = max(w / sw, h / sh)
    img = img.resize((max(1, int(sw * scale)), max(1, int(sh * scale))), Image.LANCZOS)
    left = (img.width - w) // 2
    top = (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def render_profile_card(member_name: str, display_name: str, username: str,
                        avatar_bytes: Optional[bytes], bio: str, settings: dict,
                        accent_hex: str, stats: list, bg_bytes: Optional[bytes] = None) -> bytes:
    w, h = CARD_W, CARD_H
    bg_type = settings.get("bg_type", "gradient")

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    if bg_type == "image" and bg_bytes:
        try:
            bg = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
            img = _cover_resize(bg, w, h)
        except Exception:
            bg_type = "gradient"
    elif bg_type == "image":
        bg_type = "gradient"

    if bg_type == "solid":
        sc = _hex_to_rgb(_safe_hex(settings.get("solid_color"), "#1a1a1a"))
        img = Image.new("RGBA", (w, h), sc + (255,))

    if bg_type == "gradient":
        c1 = _hex_to_rgb(_safe_hex(settings.get("gradient_from"), "#5865f2"))
        c2 = _hex_to_rgb(_safe_hex(settings.get("gradient_to"), "#eb459e"))
        grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad)
        for x_pos in range(w):
            ratio = x_pos / w
            r = int(c1[0] + (c2[0] - c1[0]) * ratio)
            g = int(c1[1] + (c2[1] - c1[1]) * ratio)
            b = int(c1[2] + (c2[2] - c1[2]) * ratio)
            gd.line([(x_pos, 0), (x_pos, h)], fill=(r, g, b, 255))
        img = grad

    draw = ImageDraw.Draw(img)

    # Dark scrim scaled by bg_opacity so text stays readable on any background
    opacity = max(0, min(100, int(settings.get("bg_opacity", 35))))
    scrim_alpha = int(255 * (100 - opacity) / 100 / 2) + 40
    scrim = Image.new("RGBA", (w, h), (0, 0, 0, min(200, scrim_alpha)))
    img = Image.alpha_composite(img, scrim)
    draw = ImageDraw.Draw(img)

    text_rgb = _hex_to_rgb(_safe_hex(settings.get("text_color"), "#ffffff"))
    accent_rgb = _hex_to_rgb(accent_hex)
    dim_rgb = _dim(text_rgb)

    # Avatar with accent ring
    ring = AVATAR_RING
    total = AVATAR_SIZE + ring * 2
    ax, ay = AVATAR_X, (h - total) // 2
    draw.ellipse([ax, ay, ax + total - 1, ay + total - 1], fill=accent_rgb + (255,))
    avatar_img = None
    if avatar_bytes:
        try:
            raw = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            raw = raw.resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
            mask = Image.new("L", (AVATAR_SIZE, AVATAR_SIZE), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, AVATAR_SIZE - 1, AVATAR_SIZE - 1), fill=255)
            avatar_img = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (0, 0, 0, 0))
            avatar_img.paste(raw, mask=mask)
        except Exception:
            avatar_img = None
    if avatar_img is None:
        avatar_img = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), _dim(accent_rgb, 0.5) + (255,))
        ad = ImageDraw.Draw(avatar_img)
        ad.text((AVATAR_SIZE // 2, AVATAR_SIZE // 2), (display_name or member_name or "?")[0].upper(),
                font=_load_font(64, bold=True), fill=text_rgb + (255,), anchor="mm")
    img.paste(avatar_img, (ax + ring, ay + ring), avatar_img)

    name_font = _load_font(40, bold=True)
    sub_font = _load_font(22)
    bio_font = _load_font(20)
    stats_font = _load_font(22, bold=True)
    footer_font = _load_font(16)

    # Name (truncate to fit)
    name = display_name or member_name
    while name and draw.textlength(name, font=name_font) > w - TEXT_X - 40:
        name = name[:-1]
    draw.text((TEXT_X, 58), name, font=name_font, fill=text_rgb + (255,))
    name_bottom = 58 + 46

    draw.text((TEXT_X, name_bottom + 2), "@" + username, font=sub_font, fill=dim_rgb + (255,))

    # Divider
    line_y = name_bottom + 44
    draw.line([(TEXT_X, line_y), (w - 40, line_y)], fill=_dim(text_rgb, 0.25) + (255,), width=2)

    # Bio
    y_cursor = line_y + 16
    if bio:
        for line in _wrap_text(draw, bio, bio_font, w - TEXT_X - 40, max_lines=3):
            draw.text((TEXT_X, y_cursor), line, font=bio_font, fill=dim_rgb + (255,))
            y_cursor += 28

    # Stats row pinned to the bottom of the card
    stats_y = h - 56
    x_cursor = TEXT_X
    for i, segment in enumerate(stats):
        if i > 0:
            draw.ellipse([x_cursor + 8, stats_y + 14, x_cursor + 16, stats_y + 22], fill=accent_rgb + (255,))
            x_cursor += 30
        seg_font = stats_font
        draw.text((x_cursor, stats_y), segment, font=seg_font, fill=text_rgb + (255,))
        x_cursor += int(draw.textlength(segment, font=seg_font))

    footer = (settings.get("footer_text") or "").strip()
    if footer:
        ftext = footer[:80]
        fw = draw.textlength(ftext, font=footer_font)
        draw.text((w - 40 - fw, h - 34), ftext, font=footer_font, fill=dim_rgb + (200,))

    # Rounded corners
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=28, fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)

    buf = io.BytesIO()
    out.convert("RGB").save(buf, "PNG")
    return buf.getvalue()


class Profiles(commands.Cog):
    """Per-server customizable member profile cards."""

    prof = app_commands.Group(name="profile", description="Server profile cards")

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _resolve_card(self, interaction: discord.Interaction, target: discord.abc.User):
        """Returns (png_bytes, error_message)."""
        guild = interaction.guild
        if guild is None:
            return None, "Profiles only work inside a server."
        settings = await get_profile_settings(guild.id)
        if not settings.get("enabled"):
            return None, "Profiles are disabled on this server. An admin can enable them in the dashboard."

        member = guild.get_member(target.id)
        bio = ""
        if settings.get("bio_enabled"):
            pool = await neon_db.get_pool()
            if pool:
                try:
                    row = await pool.fetchrow(
                        "SELECT bio FROM profile_bios WHERE guild_id = ? AND user_id = ?",
                        str(guild.id), str(target.id),
                    )
                    bio = (row["bio"] or "").strip() if row else ""
                except Exception as e:
                    logger.warning(f"profile bio fetch failed: {e}")

        xp_data = await get_user_xp(guild.id, target.id)

        stats = []
        if settings.get("show_level"):
            stats.append(f"Level {xp_data.get('level', 1)}")
            stats.append(f"{xp_data.get('xp', 0)} XP")
        if settings.get("show_joinage"):
            joined = member.joined_at if member else None
            stats.append("Joined " + (joined.strftime("%b %Y") if joined else "unknown"))
        if settings.get("show_roles"):
            n_roles = len(member.roles) - 1 if member else 0
            stats.append(f"{n_roles} role" + ("s" if n_roles != 1 else ""))

        if settings.get("accent_auto") and member and member.top_role.color.value:
            accent_hex = "#" + format(member.top_role.color.value, "06x")
        else:
            accent_hex = _safe_hex(settings.get("accent_color"), "#5865f2")

        avatar_bytes = await _fetch_bytes(target.display_avatar.replace(size=256, format="png").url)

        bg_bytes = None
        if settings.get("bg_type") == "image" and (settings.get("bg_image_url") or "").strip():
            bg_bytes = await _fetch_bytes(settings["bg_image_url"].strip())

        png = render_profile_card(
            member_name=target.name,
            display_name=getattr(member, "display_name", None) or target.global_name or target.name,
            username=target.name,
            avatar_bytes=avatar_bytes,
            bio=bio,
            settings=settings,
            accent_hex=accent_hex,
            stats=stats,
            bg_bytes=bg_bytes,
        )
        return png, None

    @prof.command(name="view", description="Show a member's profile card")
    @app_commands.describe(user="Whose profile to show (defaults to you)")
    async def profile_view(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        target = user or interaction.user
        await interaction.response.defer()
        try:
            png, err = await self._resolve_card(interaction, target)
        except Exception as e:
            logger.warning(f"profile render failed: {e}")
            png, err = None, "Something went wrong while rendering that profile."
        if err:
            await interaction.followup.send(err, ephemeral=True)
            return
        await interaction.followup.send(file=discord.File(io.BytesIO(png), filename="profile.png"))

    @prof.command(name="setbio", description="Set the bio shown on your profile in this server")
    @app_commands.describe(bio="Your bio (max 200 characters)")
    @app_commands.checks.cooldown(2, 30.0)
    async def profile_setbio(self, interaction: discord.Interaction, bio: app_commands.Range[str, 1, 200]):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Profiles only work inside a server.", ephemeral=True)
            return
        settings = await get_profile_settings(guild.id)
        if not settings.get("enabled"):
            await interaction.response.send_message("Profiles are disabled on this server.", ephemeral=True)
            return
        if not settings.get("bio_enabled"):
            await interaction.response.send_message("Bios are turned off on this server.", ephemeral=True)
            return
        pool = await neon_db.get_pool()
        if pool is None:
            await interaction.response.send_message("Storage unavailable, try again later.", ephemeral=True)
            return
        clean = " ".join(bio.strip().splitlines())
        try:
            await pool.execute(
                "INSERT INTO profile_bios (guild_id, user_id, bio, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT (guild_id, user_id) DO UPDATE SET bio = ?, updated_at = ?",
                str(guild.id), str(interaction.user.id), clean, time.time(), clean, time.time(),
            )
        except Exception as e:
            logger.warning(f"profile setbio failed: {e}")
            await interaction.response.send_message("Could not save your bio, try again later.", ephemeral=True)
            return
        await interaction.response.send_message("Your bio has been updated.", ephemeral=True)

    @prof.command(name="clearbio", description="Remove your bio from your profile in this server")
    async def profile_clearbio(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("Profiles only work inside a server.", ephemeral=True)
            return
        pool = await neon_db.get_pool()
        if pool is None:
            await interaction.response.send_message("Storage unavailable, try again later.", ephemeral=True)
            return
        try:
            await pool.execute(
                "DELETE FROM profile_bios WHERE guild_id = ? AND user_id = ?",
                str(interaction.guild.id), str(interaction.user.id),
            )
        except Exception as e:
            logger.warning(f"profile clearbio failed: {e}")
        await interaction.response.send_message("Your bio has been removed.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Profiles(bot))
