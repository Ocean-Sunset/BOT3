# --------------------- IMPORTS --------------------
import discord
from discord.ext import commands
from Ediscord import utils, variables
import asyncio
import logging
import requests
import os
from yt_dlp import YoutubeDL
from discord import FFmpegPCMAudio
from googletrans import Translator
import typing
import re
import json
from discord.ext import tasks
from discord import ui
import string
import unicodedata

FORBIDDEN_CHARS = set("? ! / \\ $ %".split())

def is_valid_bracket(bracket: str):
    # Bracket must not contain spaces or forbidden chars, and must be non-empty
    return (
        bracket
        and all(c not in FORBIDDEN_CHARS for c in bracket)
        and " " not in bracket
    )

KAPS_JSON_PATH = os.path.join(os.path.dirname(__file__), "../data/kaps.json")

DISALLOWED_BRACKETS = {"?", "!", "/", "\\", "$", "%"}

def load_kaps():
    if not os.path.exists(KAPS_JSON_PATH):
        return {}
    with open(KAPS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _unicode_base_letter(ch: str) -> str:
    """Return an ASCII base letter for many Unicode 'font' variants.

    This attempts to map characters like MATHEMATICAL BOLD SMALL A to 'a'
    by inspecting the Unicode character name. Falls back to NFKD
    decomposition and ASCII stripping. Returns an empty string when no
    sensible letter mapping is found.
    """
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return ""
    # Try to find 'LETTER X' in the Unicode name (covers many styled letters)
    m = re.search(r"LETTER ([A-Z])", name)
    if m:
        letter = m.group(1)
        if "SMALL" in name:
            return letter.lower()
        return letter.upper()
    # Fallback: decompose and strip non-ascii
    decomp = unicodedata.normalize("NFKD", ch)
    try:
        ascii_bytes = decomp.encode("ascii", "ignore")
        ascii_str = ascii_bytes.decode("ascii")
        return ascii_str
    except Exception:
        return ""

def save_kaps(kaps):
    with open(KAPS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(kaps, f, indent=2)

class KapsListView(ui.View):
    def __init__(self, user_id, kaps, page=0):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.kaps = kaps
        self.page = page
        self.max_page = max(0, (len(kaps) - 1) // 5)
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.page > 0:
            self.add_item(ui.Button(label="Previous", style=discord.ButtonStyle.primary, custom_id="prev"))
        if self.page < self.max_page:
            self.add_item(ui.Button(label="Next", style=discord.ButtonStyle.primary, custom_id="next"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return str(interaction.user.id) == self.user_id

    @ui.button(label="Previous", style=discord.ButtonStyle.primary, custom_id="prev", row=0)
    async def prev(self, interaction: discord.Interaction, button: ui.Button):
        if self.page > 0:
            self.page -= 1
            await self.show_page(interaction)

    @ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="next", row=0)
    async def next(self, interaction: discord.Interaction, button: ui.Button):
        if self.page < self.max_page:
            self.page += 1
            await self.show_page(interaction)

    async def show_page(self, interaction):
        embed = self.make_embed()
        self.update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    def make_embed(self):
        embed = discord.Embed(
            title=f"Your Kaps (Page {self.page+1}/{self.max_page+1})",
            color=discord.Color.blurple()
        )
        start = self.page * 5
        end = start + 5
        for name, avatar_url in list(self.kaps.items())[start:end]:
            embed.add_field(name=name, value=f"[Avatar Link]({avatar_url})", inline=False)
            embed.set_thumbnail(url=avatar_url)
        return embed

class Patrivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Load kaps from file
        self.kaps = load_kaps()
        self.proxy_sessions = {}

    def save_kaps(self):
        save_kaps(self.kaps)


    @discord.app_commands.guild_only()
    @discord.app_commands.command(name="kaps", description="Kapsbox-like roleplay system. Use subcommands: create, list, say, become, unbecome.")
    async def kaps(self, interaction: discord.Interaction):
        await interaction.response.send_message("Kaps!Box: Use `/kaps_create <name> <avatar_url> <bracket>`, `/kaps_list`, `/kaps_say <name> <message>`, `/kaps_become <name> <#channel>`, or `/kaps_unbecome`.", ephemeral=True)


    @discord.app_commands.command(name="kaps_create", description="Create a kaps with a name, avatar URL, and bracket.")
    async def kaps_create(self, interaction: discord.Interaction, name: str, avatar_url: str, bracket: str):
        user_id = str(interaction.user.id)
        if not is_valid_bracket(bracket):
            await interaction.response.send_message("# ❌ Invalid bracket.\nBracket must not contain spaces or any of: ? ! / \\ $ %", ephemeral=True)
            return
        if user_id not in self.kaps:
            self.kaps[user_id] = {}
        if name in self.kaps[user_id]:
            await interaction.response.send_message(f"# ❌ Name!\nYou already have a kaps named `{name}`.", ephemeral=True)
            return
        if not avatar_url.startswith("http"):
            await interaction.response.send_message("# ❌ HTTP Error\nPlease provide a valid avatar URL (must start with http).", ephemeral=True)
            return
        self.kaps[user_id][name] = {
            "avatar_url": avatar_url,
            "brackets": [bracket]
        }
        self.save_kaps()
        await interaction.response.send_message(f"# ✅ Kaps `{name}` created!\nKaps created with bracket `{bracket}`! Type `{bracket} 'your text' {bracket}` to speak as them.", ephemeral=True)


    @discord.app_commands.command(name="kaps_list", description="List your kaps with interactive embed pagination.")
    async def kaps_list(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        kaps = self.kaps.get(user_id, {})
        if not kaps:
            await interaction.response.send_message("# ❌ No kaps found for this user.", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"Your Kaps (Page 1)",
            color=discord.Color.blurple()
        )
        items = list(kaps.items())
        for name, data in items[:5]:
            avatar_url = data["avatar_url"] if isinstance(data, dict) else data
            brackets = ", ".join(data["brackets"]) if isinstance(data, dict) and "brackets" in data else ""
            embed.add_field(name=name, value=f"[Avatar Link]({avatar_url})\nBracket: `{brackets}`", inline=False)
            embed.set_thumbnail(url=avatar_url)
        view = KapsListView(user_id, kaps, page=0)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


    @discord.app_commands.command(name="kaps_say", description="Speak as your kaps using a webhook.")
    async def kaps_say(self, interaction: discord.Interaction, name: str, message: str):
        user_id = str(interaction.user.id)
        kaps = self.kaps.get(user_id, {})
        if name not in kaps:
            await interaction.response.send_message(f"# ❌ Kaps Error.\nYou don't have a kaps named `{name}`.", ephemeral=True)
            return
        avatar_url = kaps[name]["avatar_url"] if isinstance(kaps[name], dict) else kaps[name]
        channel = interaction.channel
        webhooks = await channel.webhooks()
        webhook = None
        for wh in webhooks:
            if wh.user == interaction.guild.me:
                webhook = wh
                break
        if not webhook:
            webhook = await channel.create_webhook(name="Kapsbox")
        await webhook.send(
            message,
            username=name,
            avatar_url=avatar_url,
            allowed_mentions=discord.AllowedMentions.none()
        )
        await interaction.response.send_message(f"# ✅ Sent as `{name}`.", ephemeral=True)


    @discord.app_commands.command(name="kaps_become", description="Become a kaps in a public channel (admin only)")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def kaps_become(self, interaction: discord.Interaction, kaps_name: str, channel_destination: discord.TextChannel):
        user_id = str(interaction.user.id)
        kaps = self.kaps.get(user_id, {})
        if kaps_name not in kaps:
            await interaction.response.send_message(f"# ❌ No kaps\nNo kaps named `{kaps_name}` found for you.", ephemeral=True)
            return
        avatar_url = kaps[kaps_name]["avatar_url"] if isinstance(kaps[kaps_name], dict) else kaps[kaps_name]
        self.proxy_sessions[user_id] = {
            "kaps_name": kaps_name,
            "avatar_url": avatar_url,
            "public_channel_id": channel_destination.id,
            "hidden_channel_id": interaction.channel.id
        }
        await interaction.response.send_message(f"✅ Speaking as `{kaps_name}` in {channel_destination.mention}. Type messages here to send as your kaps. Use `/kaps_unbecome` to stop.", ephemeral=True)


    @discord.app_commands.command(name="kaps_delete", description="Delete one of your kaps by name.")
    async def kaps_delete(self, interaction: discord.Interaction, name: str):
        user_id = str(interaction.user.id)
        kaps = self.kaps.get(user_id, {})
        if name not in kaps:
            await interaction.response.send_message(f"# ❌ No kaps\nNo kaps named `{name}` found for you.", ephemeral=True)
            return
        del kaps[name]
        if not kaps:
            del self.kaps[user_id]
        self.save_kaps()
        await interaction.response.send_message(f"# 🗑️ Kaps `{name}` deleted.", ephemeral=True)


    @discord.app_commands.command(name="kaps_unbecome", description="Stop proxying as a kaps (admin only)")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def kaps_unbecome(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id in self.proxy_sessions:
            del self.proxy_sessions[user_id]
            await interaction.response.send_message(f"# 🛑 Proxy session ended.", ephemeral=True)
        else:
            await interaction.response.send_message("# ❌ User Error.\nYou are not currently proxying as a kaps.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        # --- Ignore bot messages ---
        if message.author.bot:
            return

        user_id = str(message.author.id)

        # --- Proxy: Admin to Public Channel ---
        # If admin is in a proxy session and sends a message in the hidden channel
        if user_id in self.proxy_sessions:
            session = self.proxy_sessions[user_id]
            if message.channel.id == session["hidden_channel_id"]:
                # Relay as kaps in public channel
                public_channel = self.bot.get_channel(session["public_channel_id"])
                if public_channel:
                    # Find or create webhook
                    webhooks = await public_channel.webhooks()
                    webhook = None
                    for wh in webhooks:
                        if wh.user == message.guild.me:
                            webhook = wh
                            break
                    if not webhook:
                        webhook = await public_channel.create_webhook(name="Kapsbox")
                    await webhook.send(
                        message.content,
                        username=session["kaps_name"],
                        avatar_url=session["avatar_url"],
                        allowed_mentions=discord.AllowedMentions.none()
                    )
                return  # Don't process further

        # --- Proxy: User to Admin (Public Channel to Hidden Channel) ---
        # Check if this channel is a destination for any proxy session
        for admin_id, session in self.proxy_sessions.items():
            if message.channel.id == session["public_channel_id"] and not message.author.bot:
                # Relay user's message to hidden channel
                hidden_channel = self.bot.get_channel(session["hidden_channel_id"])
                admin = message.guild.get_member(int(admin_id))
                if hidden_channel and admin:
                    embed = discord.Embed(
                        description=message.content,
                        color=discord.Color.blue()
                    )
                    embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.avatar.url if message.author.avatar else None)
                    await hidden_channel.send(
                        f"💬 Message from {message.author.mention} in {message.channel.mention} (for {admin.mention}):",
                        embed=embed
                    )
                break  # Only relay for one session

        # --- Bracket-based kaps proxy ---
        if not message.author.bot:
            user_id = str(message.author.id)
            kaps = self.kaps.get(user_id, {})
            for name, data in kaps.items():
                for bracket in data.get("brackets", []):
                    # Match: bracket + space + text
                    if (
                        message.content.startswith(bracket + " ")
                        and len(message.content) > len(bracket) + 1
                    ):
                        text = message.content[len(bracket) + 1 :]
                        avatar_url = data["avatar_url"]
                        # Find or create webhook for this channel
                        webhooks = await message.channel.webhooks()
                        webhook = None
                        for wh in webhooks:
                            if wh.user == message.guild.me:
                                webhook = wh
                                break
                        if not webhook:
                            webhook = await message.channel.create_webhook(name="Kapsbox")
                        await webhook.send(
                            text,
                            username=name,
                            avatar_url=avatar_url,
                            allowed_mentions=discord.AllowedMentions.none()
                        )
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        return  # Only proxy one kaps per message

async def setup(bot):
    await bot.add_cog(Patrivia(bot))