from discord.ext import commands
import discord
import os
import json
from Ediscord import variables, utils
import feedparser
import requests
from datetime import datetime, timedelta
import time
from discord import app_commands
import random

class insiderCore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.quest_data_path = "insider_quests.json"
        self.user_xp_path = "insider_xp.json"
        self.early_features_path = "early_features.json"
        self.secret_path = "insider_secret.json"
        self.public_profiles_path = "public_profiles.json"
        self.profile_music_path = "profile_music.json"
        self.daily_path = "daily_claims.json"
        self.reaction_themes = {
            "default": ["👍", "👎"],
            "fire": ["🔥", "💀"],
            "funny": ["😂", "🤨"],
            "stars": ["⭐", "🌟"]
        }
        self.load_quests()
        self.load_secret()
    
    def load_quests(self):
        if os.path.exists(self.quest_data_path):
            with open(self.quest_data_path, 'r', encoding='utf-8') as f:
                self.quests = json.load(f)
        else:
            self.quests = {
                "current": "Use 5 bot commands in a day!",
                "next_refresh": (datetime.utcnow() + timedelta(days=7)).isoformat()
            }
            self.save_quests()

    def save_quests(self):
        with open(self.quest_data_path, 'w', encoding='utf-8') as f:
            json.dump(self.quests, f, indent=2)

    def load_secret(self):
        if os.path.exists(self.secret_path):
            with open(self.secret_path, 'r', encoding='utf-8') as f:
                self.secret = json.load(f)
        else:
            self.secret = {"message": "You found the secret! 🕵️", "next": (datetime.utcnow() + timedelta(days=7)).isoformat()}
            self.save_secret()

    def save_secret(self):
        with open(self.secret_path, 'w', encoding='utf-8') as f:
            json.dump(self.secret, f, indent=2)

    @app_commands.command(name="testembed", description="Test an embed using JSON (insider only)")
    @app_commands.describe(json_text="The JSON text for the embed")
    async def testembed(self, interaction: discord.Interaction, json_text: str):
        if not utils.is_insider_server(interaction.guild.id):
            await interaction.response.send_message("# ❌ Not an insider server!\nThis is a beta command and is therefor only for the insider program servers.\n-# If you wish to have an insider program server, please do `/insiderrequest` and wait for **the owner to approve your server!**", ephemeral=True)
            return
        try:
            data = json.loads(json_text)
            embed = discord.Embed.from_dict(data)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"# ❌ Invalid JSON: {e}", ephemeral=True)

    @app_commands.command(name="insidersecret", description="Reveal the weekly insider secret (insider only)")
    async def insidersecret(self, interaction: discord.Interaction):
        if not utils.is_insider_server(interaction.guild.id):
            await interaction.response.send_message("# ❌ Not an insider server!\nThis is a beta command and is therefor only for the insider program servers.\n-# If you wish to have an insider program server, please do `/insiderrequest` and wait for **the owner to approve your server!**", ephemeral=True)
            return
        now = datetime.utcnow()
        if now >= datetime.fromisoformat(self.secret["next"]):
            self.secret["message"] = random.choice([
                "🧪 This week’s codeword: `paradox`.",
                "👽 Aliens have taken over the dev logs.",
                "🔐 The password is always `swordfish`.",
                "🌌 There's a void where version 0.1 was."
            ])
            self.secret["next"] = (now + timedelta(days=7)).isoformat()
            self.save_secret()
        await interaction.response.send_message(f"🔍 **Insider Secret:** {self.secret['message']}")

    @app_commands.command(name="insider", description="Show info about the insider program (insider only)")
    async def insider(self, interaction: discord.Interaction):
        if not utils.is_insider_server(interaction.guild.id):
            await interaction.response.send_message("# ❌ This server is not in the insider program.\nTry requesting insider access with `/insiderrequest`!", ephemeral=True)
            return
        await interaction.response.send_message(
            "# Welcome to the Insider Program!\n"
            "Use `/insiderstatus` to confirm you're in.\n"
            "Use `/insiderremove <guild_id>` to remove a server from insider.\n"
            "Use `/serverstats` to check your server statics.\n"
            "Use `/insiderfeedback <message>` to feedback your experience with the insider Program.\n"
            "Use `/insiderchangelog` to check the insider Program changelog.\n"
            "Use `/rssfetch <feed_id>` to fetch a feed from RSS.\n"
            "Use `/ytalert <channel_id>` to fetch the latest video from the user.\n"
            "Use `/twitchalert <channel_id>` to fetch the latest video / stream from the user.\n"
            "Use `/setbio <guild_id>` to set a custom bio for yourself.\n"
            "Use `/bprofile <user>` to check your or other peoples profiles.\n"
            "Use `/addbadge <member> <badge>` to add a badge to other people (admin only).\n"
            "Use `/setbg <url>` set your profile background.\n"
            "Use `/bprofile_public on/off` to set your profile public or private.\n"
            "Use `/profilemusic <youtube_link>` to set music for your profile.\n"
            "Use `/insiderdaily` to claim your daily reward.\n"
            "Use `/insiderlevels` to see insider XP milestones.\n"
            "Use `/insidergiveaway <prize>` to start an insider giveaway (admin only).\n"
            "Use `/insiderrank` to check your insider XP and level.\n"
            "Use `/insiderquest` to see the weekly insider quest.\n"
            "Use `/submitidea <message>` to submit an idea to the developers.\n"
            "Use `/insiderbadges` to see available insider badges.\n"
            "Use `/insiderpoll <Question|Option1|Option2|...>` to create a poll.\n"
            "Use `/reactiontheme set <theme>` to set your reaction theme.\n"
            "Use `/testembed <json_text>` to test an embed using JSON.\n"
            "Use `/crashreport <description>` to submit a crash report.\n"
            "Use `/earlyfeature on/off` to toggle early feature access.\n"
            "Use `/insidersecret` to reveal the weekly insider secret.\n"
        )

    @app_commands.command(name="insiderchangelog", description="Show the latest insider-specific changelog (insider only)")
    async def insiderchangelog(self, interaction: discord.Interaction):
        if not utils.is_insider_server(interaction.guild.id):
            await interaction.response.send_message("# ❌ This server is not in the insider program.\nTry requesting insider access with `/insiderrequest`!", ephemeral=True)
            return
        changelog = (
            "# Insider Changelog:\n"
            "- Added 10+ new commands\n"
            "- Update for /insider\n"
            "- not much sorry..\n"
        )
        await interaction.response.send_message(changelog)
    
    @app_commands.command(name="rssfetch", description="Fetch and display the latest entry from an RSS feed (insider only)")
    @app_commands.describe(feed_url="The RSS feed URL")
    async def rssfetch(self, interaction: discord.Interaction, feed_url: str):
        if not utils.is_insider_server(interaction.guild.id):
            await interaction.response.send_message("# ❌ This server is not in the insider program.\nTry requesting insider access with `/insiderrequest`!", ephemeral=True)
            return
        if not feed_url:
            await interaction.response.send_message("# ⚠️ Please provide an RSS feed URL, e.g. `/rssfetch <url>`", ephemeral=True)
            return
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                await interaction.response.send_message("❔ No entries found in this feed.\n-# It either doesn't exist, has been deleted, or you entered the wrong ID. Try again!", ephemeral=True)
                return
            entry = feed.entries[0]
            title = entry.title
            link = entry.link
            summary = entry.summary if hasattr(entry, "summary") else ""
            embed = discord.Embed(title=title, url=link, description=summary[:2048], color=discord.Color.orange())
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"# ❌ Failed to fetch RSS feed: {e}\n-# B.critical, please contact support.", ephemeral=True)
        
    @app_commands.command(name="ytalert", description="Check and announce the latest YouTube video from a channel (insider only)")
    @app_commands.describe(channel_id="The YouTube channel ID")
    async def ytalert(self, interaction: discord.Interaction, channel_id: str):
        if not utils.is_insider_server(interaction.guild.id):
            await interaction.response.send_message("# ❌ This server is not in the insider program.\nTry requesting insider access with `/insiderrequest`!", ephemeral=True)
            return
        if not channel_id:
            await interaction.response.send_message("# ⚠️ Please provide a YouTube channel ID, e.g. `/ytalert <channel_id>`", ephemeral=True)
            return
        api_key = "AIzaSyC3ik7r-4UX6eITy_Fn2orsLadA0mWt7uE"
        url = (
            f"https://www.googleapis.com/youtube/v3/search"
            f"?key={api_key}&channelId={channel_id}&part=snippet,id&order=date&maxResults=1"
        )
        try:
            response = requests.get(url)
            data = response.json()
            if "items" not in data or not data["items"]:
                await interaction.response.send_message("❔ No videos found or invalid channel ID,\n-# It either doesn't exist, has been deleted, or you entered your ID wrong, Try again!", ephemeral=True)
                return
            video = data["items"][0]
            if video["id"]["kind"] != "youtube#video":
                await interaction.response.send_message("❗ Latest item is not a video.", ephemeral=True)
                return
            video_id = video["id"]["videoId"]
            title = video["snippet"]["title"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            embed = discord.Embed(
                title=f"New YouTube Video: {title}",
                url=video_url,
                description=video["snippet"]["description"][:2048],
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=video["snippet"]["thumbnails"]["high"]["url"])
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"# ❌ Failed to fetch YouTube video: {e}\n-# B.critical, please contact support.", ephemeral=True)
    
    @app_commands.command(name="twitchalert", description="Check and announce if a Twitch channel is live (insider only)")
    @app_commands.describe(twitch_username="The Twitch username")
    async def twitchalert(self, interaction: discord.Interaction, twitch_username: str):
        await interaction.response.send_message("# ❌ Sorry!\nThis command is currently unavailable.", ephemeral=True)
    
    @app_commands.command(name="insiderstatus", description="Show detailed insider status info (insider only)")
    async def insiderstatus(self, interaction: discord.Interaction):
        if not utils.is_insider_server(interaction.guild.id):
            await interaction.response.send_message("# ❌ This server is not in the insider program.\nTry requesting insider access with `/insiderrequest`!", ephemeral=True)
            return
        insider_server_ids = utils.load_insider_servers()
        is_insider = interaction.guild and interaction.guild.id in insider_server_ids
        info = variables.bot_info
        msg = (
            f"# insider Status\n"
            f"- Server: {'insider' if is_insider else 'Normal'}\n"
            f"- Version: {info.get('version', 'N/A')}\n"
            f"- insider Version: {info.get('insider_version', 'N/A')}\n"
            f"- insider Features: {info.get('insider_new_stuff', 'N/A')}\n"
            f"- Developer: th3_t1sm\n"
            f"- insider Servers: {len(insider_server_ids)}\n"
        )
        await interaction.response.send_message(msg)
    
async def setup(bot):
    await bot.add_cog(insiderCore(bot))