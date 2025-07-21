from discord.ext import commands
import discord
import os
import json
from Ediscord import variables, utils
import feedparser
import requests
from datetime import datetime, timedelta
import time
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

    @commands.command(name="bprofile_public")
    async def bprofile_public(self, ctx, toggle: str = None):
        if not utils.is_insider_server(ctx.guild.id):
            return await ctx.send("# ❌ Not an insider server.")
        if toggle not in ["on", "off"]:
            return await ctx.send("# ⚙️ Usage: `?bprofile public on/off`")
        if os.path.exists(self.public_profiles_path):
            with open(self.public_profiles_path, 'r', encoding='utf-8') as f:
                public_flags = json.load(f)
        else:
            public_flags = {}
        public_flags[str(ctx.author.id)] = toggle == "on"
        with open(self.public_profiles_path, 'w', encoding='utf-8') as f:
            json.dump(public_flags, f, indent=2)
        await ctx.send(f"# ✅ Public profile mode `{toggle}`.")

    @commands.command(name="profilemusic")
    async def profilemusic(self, ctx, yt_link: str = None):
        if not utils.is_insider_server(ctx.guild.id):
            return await ctx.send("# ❌ Not an insider server.")
        if not yt_link or not yt_link.startswith("https://"):
            return await ctx.send("# ⚠️ Please provide a valid YouTube link.")
        if os.path.exists(self.profile_music_path):
            with open(self.profile_music_path, 'r', encoding='utf-8') as f:
                music_data = json.load(f)
        else:
            music_data = {}
        music_data[str(ctx.author.id)] = yt_link
        with open(self.profile_music_path, 'w', encoding='utf-8') as f:
            json.dump(music_data, f, indent=2)
        await ctx.send("# ✅ Your profile music has been set!")

    @commands.command(name="insiderdaily")
    async def insiderdaily(self, ctx):
        if not utils.is_insider_server(ctx.guild.id):
            return await ctx.send("# ❌ Not an insider server.")
        user_id = str(ctx.author.id)
        now = datetime.utcnow()
        if os.path.exists(self.daily_path):
            with open(self.daily_path, 'r', encoding='utf-8') as f:
                daily_data = json.load(f)
        else:
            daily_data = {}
        last_claim = datetime.fromisoformat(daily_data.get(user_id, "1970-01-01T00:00:00"))
        if now - last_claim < timedelta(hours=20):
            return await ctx.send("# 🕒 You've already claimed your daily reward! Try again later.")
        daily_data[user_id] = now.isoformat()
        with open(self.daily_path, 'w', encoding='utf-8') as f:
            json.dump(daily_data, f, indent=2)
        self.add_xp(ctx.author.id, 10)
        await ctx.send("# 🎁 You claimed 10 XP for your daily check-in!")

    @commands.command(name="insiderlevels")
    async def insiderlevels(self, ctx):
        await ctx.send(
            "# 🧪 **Insider XP Milestones**\n"
            "- Level 1 → Access to profile customization\n"
            "- Level 3 → Insider badge unlocked\n"
            "- Level 5 → Access to test-only commands\n"
            "- Level 10 → Easter egg content\n"
            "- Level 15 → `gold` badge & leaderboard invite"
        )

    @commands.command(name="insidergiveaway")
    @utils.admin_or_owner()
    async def insidergiveaway(self, ctx, *, prize: str = None):
        if not prize:
            return await ctx.send("# 🎉 Usage: `?insidergiveaway <prize>`")
        embed = discord.Embed(title="🎉 Insider Giveaway!", description=f"Prize: {prize}\nReact with 🎁 to enter!", color=discord.Color.green())
        embed.set_footer(text=f"Started by {ctx.author}")
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("🎁")

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

    def add_xp(self, user_id: int, amount: int):
        if os.path.exists(self.user_xp_path):
            with open(self.user_xp_path, 'r', encoding='utf-8') as f:
                xp_data = json.load(f)
        else:
            xp_data = {}
        user_id = str(user_id)
        xp_data[user_id] = xp_data.get(user_id, 0) + amount
        with open(self.user_xp_path, 'w', encoding='utf-8') as f:
            json.dump(xp_data, f, indent=2)

    def get_xp(self, user_id: int):
        if os.path.exists(self.user_xp_path):
            with open(self.user_xp_path, 'r', encoding='utf-8') as f:
                xp_data = json.load(f)
            return xp_data.get(str(user_id), 0)
        return 0

    def get_level(self, xp: int):
        return int(xp ** 0.5 // 5)

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

    @commands.command(name="insiderrank")
    async def insiderrank(self, ctx):
        if not utils.is_insider_server(ctx.guild.id):
            return await ctx.send("# ❌ Not an insider server.")
        xp = self.get_xp(ctx.author.id)
        level = self.get_level(xp)
        await ctx.send(f"🎖️ **{ctx.author.display_name}'s Insider Rank**\nXP: `{xp}` | Level: `{level}`")

    @commands.command(name="insiderquest")
    async def insiderquest(self, ctx):
        if not utils.is_insider_server(ctx.guild.id):
            return await ctx.send("# ❌ Not an insider server.")
        now = datetime.utcnow()
        refresh_time = datetime.fromisoformat(self.quests["next_refresh"])
        if now >= refresh_time:
            self.quests["current"] = random.choice([
                "Send 5 messages.",
                "Use a badge command.",
                "Try a changelog command.",
                "Give feedback with ?insiderfeedback."
            ])
            self.quests["next_refresh"] = (now + timedelta(days=7)).isoformat()
            self.save_quests()
        await ctx.send(f"📜 **Weekly Insider Quest:** {self.quests['current']}")

    @commands.command(name="submitidea")
    async def submitidea(self, ctx, *, message: str = None):
        if not utils.is_insider_server(ctx.guild.id):
            return await ctx.send("# ❌ Not an insider server.")
        if not message:
            return await ctx.send("# ⚠️ Provide an idea to submit!")
        idea_channel_id = 1391096986811371590  # dev channel ID
        idea_channel = self.bot.get_channel(idea_channel_id)
        embed = discord.Embed(
            title="💡 New Insider Idea",
            description=message,
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"From {ctx.author} in {ctx.guild.name}")
        if idea_channel:
            await idea_channel.send(embed=embed)
        await ctx.send("✅ Your idea has been submitted!")

    @commands.command(name="insiderbadges")
    async def insiderbadges(self, ctx):
        if not utils.is_insider_server(ctx.guild.id):
            return await ctx.send("# ❌ Not an insider server.")
        await ctx.send(
            "# 🎖️ **Available Insider Badges**\n"
            "- 🐞 **Bug Hunter** – Submitted 3 crash reports\n"
            "- 💬 **Feedback Giver** – Sent feedback using `?insiderfeedback`\n"
            "- 🔥 **Quest Finisher** – Completed 3 weekly quests\n"
            "- 👑 **Beta Tester** – Used 10 early access features\n"
            "- 🎉 **Founding Insider** – Among the first 10 insider servers!"
        )

    @commands.command(name="insiderpoll")
    async def insiderpoll(self, ctx, *, poll: str = None):
        if not utils.is_insider_server(ctx.guild.id):
            return await ctx.send("# ❌ Not an insider server.")
        if not poll or '|' not in poll:
            return await ctx.send("# ⚠️ Format: `?insiderpoll Question|Option1|Option2|...`")
        parts = poll.split('|')
        question = parts[0]
        options = parts[1:]
        if len(options) > 10:
            return await ctx.send("⚠️ Max 10 options allowed.")
        emojis = ['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣','🔟']
        description = ""
        for i, option in enumerate(options):
            description += f"{emojis[i]} {option}\n"
        embed = discord.Embed(title=f"📊 {question}", description=description, color=discord.Color.blurple())
        poll_msg = await ctx.send(embed=embed)
        for i in range(len(options)):
            await poll_msg.add_reaction(emojis[i])

    @commands.command(name="reactiontheme")
    async def reactiontheme(self, ctx, action: str = None, theme: str = None):
        if not utils.is_insider_server(ctx.guild.id):
            return await ctx.send("# ❌ Not an insider server.")
        if action != "set" or theme not in self.reaction_themes:
            available = ", ".join(self.reaction_themes.keys())
            return await ctx.send(f"# ⚙️ Available Themes: {available}\nUsage: `?reactiontheme set <theme>`")
        await ctx.send(f"✅ Reaction theme set to `{theme}` (not yet globally applied)")

    @commands.command(name="testembed")
    async def testembed(self, ctx, *, json_text: str = None):
        if not utils.is_insider_server(ctx.guild.id):
            return await ctx.send("# ❌ Not an insider server.")
        try:
            data = json.loads(json_text)
            embed = discord.Embed.from_dict(data)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"# ❌ Invalid JSON: {e}")

    @commands.command(name="crashreport")
    async def crashreport(self, ctx, *, description: str = None):
        if not utils.is_insider_server(ctx.guild.id):
            return await ctx.send("# ❌ Not an insider server.")
        if not description:
            return await ctx.send("# ⚠️ Please provide a crash description!")
        log_channel = self.bot.get_channel(1391096986811371590)
        embed = discord.Embed(title="🚨 Crash Report", description=description, color=discord.Color.red())
        embed.set_footer(text=f"From {ctx.author} in {ctx.guild.name}")
        if log_channel:
            await log_channel.send(embed=embed)
        await ctx.send("✅ Crash report logged. Thanks!")

    @commands.command(name="earlyfeature")
    async def earlyfeature(self, ctx, toggle: str = None):
        if not utils.is_insider_server(ctx.guild.id):
            return await ctx.send("# ❌ Not an insider server.")
        if not toggle or toggle not in ["on", "off"]:
            return await ctx.send("# Usage: `?earlyfeature on/off`")
        user_id = str(ctx.author.id)
        if os.path.exists(self.early_features_path):
            with open(self.early_features_path, 'r', encoding='utf-8') as f:
                flags = json.load(f)
        else:
            flags = {}
        flags[user_id] = toggle == "on"
        with open(self.early_features_path, "w", encoding='utf-8') as f:
            json.dump(flags, f, indent=2)
        await ctx.send(f"✅ Early feature access `{toggle}`.")

    @commands.command(name="insidersecret")
    async def insidersecret(self, ctx):
        if not utils.is_insider_server(ctx.guild.id):
            return await ctx.send("# ❌ Not an insider server.")
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
        await ctx.send(f"🔍 **Insider Secret:** {self.secret['message']}")

    @commands.command(name="insider")
    async def insider(self, ctx):
        """Show info about the insider program (only for approved servers)."""
        if not utils.is_insider_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the insider program.\nTry requesting insider access with `?insiderrequest`!")
            return

        await ctx.send(
            "# Welcome to the Insider Program!\n"
            "Use `?insiderstatus` to confirm you're in.\n"
            "Use `?insiderremove <guild_id>` to remove a server from insider.\n"
            "Use `?serverstats` to check your server statics.\n"
            "Use `?insiderfeedback <message>` to feedback your experience with the insider Program.\n"
            "Use `?insiderchangelog` to check the insider Program changelog.\n"
            "Use `?rssfetch <feed_id>` to fetch a feed from RSS.\n"
            "Use `?ytalert <channel_id>` to fetch the latest video from the user.\n"
            "Use `?twitchalert <channel_id>` to fetch the latest video / stream from the user.\n"
            "Use `?setbio <guild_id>` to set a custom bio for yourself.\n"
            "Use `?bprofile <user>` to check your or other peoples profiles.\n"
            "Use `?addbadge <member> <badge>` to add a badge to other people (admin only).\n"
            "Use `?setbg <url>` set your profile background.\n"
            "Use `?bprofile_public on/off` to set your profile public or private.\n"
            "Use `?profilemusic <youtube_link>` to set music for your profile.\n"
            "Use `?insiderdaily` to claim your daily reward.\n"
            "Use `?insiderlevels` to see insider XP milestones.\n"
            "Use `?insidergiveaway <prize>` to start an insider giveaway (admin only).\n"
            "Use `?insiderrank` to check your insider XP and level.\n"
            "Use `?insiderquest` to see the weekly insider quest.\n"
            "Use `?submitidea <message>` to submit an idea to the developers.\n"
            "Use `?insiderbadges` to see available insider badges.\n"
            "Use `?insiderpoll <Question|Option1|Option2|...>` to create a poll.\n"
            "Use `?reactiontheme set <theme>` to set your reaction theme.\n"
            "Use `?testembed <json_text>` to test an embed using JSON.\n"
            "Use `?crashreport <description>` to submit a crash report.\n"
            "Use `?earlyfeature on/off` to toggle early feature access.\n"
            "Use `?insidersecret` to reveal the weekly insider secret.\n"
        )
    
    @commands.command(name="serverstats")
    async def serverstats(self, ctx):
        """Show detailed server statistics."""
        guild = ctx.guild
        if not utils.is_insider_server(guild.id):
            await ctx.send("# ❌ This server is not in the insider program.\nTry requesting insider access with `?insiderrequest`!")
            return

        total_members = guild.member_count
        humans = len([m for m in guild.members if not m.bot])
        bots = len([m for m in guild.members if m.bot])
        online = len([m for m in guild.members if m.status == discord.Status.online])
        idle = len([m for m in guild.members if m.status == discord.Status.idle])
        dnd = len([m for m in guild.members if m.status == discord.Status.dnd])
        offline = len([m for m in guild.members if m.status == discord.Status.offline])
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        roles = len(guild.roles)
        emojis = len(guild.emojis)
        created_at = guild.created_at.strftime("%Y-%m-%d %H:%M:%S")
        owner = guild.owner

        embed = discord.Embed(
            title=f"Server Stats for {guild.name}",
            color=discord.Color.green()
        )
        embed.add_field(name="Owner", value=str(owner), inline=True)
        embed.add_field(name="Created At", value=created_at, inline=True)
        embed.add_field(name="Total Members", value=total_members, inline=True)
        embed.add_field(name="Humans", value=humans, inline=True)
        embed.add_field(name="Bots", value=bots, inline=True)
        embed.add_field(name="Online", value=online, inline=True)
        embed.add_field(name="Idle", value=idle, inline=True)
        embed.add_field(name="Do Not Disturb", value=dnd, inline=True)
        embed.add_field(name="Offline", value=offline, inline=True)
        embed.add_field(name="Text Channels", value=text_channels, inline=True)
        embed.add_field(name="Voice Channels", value=voice_channels, inline=True)
        embed.add_field(name="Categories", value=categories, inline=True)
        embed.add_field(name="Roles", value=roles, inline=True)
        embed.add_field(name="Emojis", value=emojis, inline=True)

        await ctx.send(embed=embed)
    
    @commands.command(name="insiderfeedback")
    async def insiderfeedback(self, ctx, *, message: str = None):
        """Send feedback about the insider program (only for insider servers)."""
        if not utils.is_insider_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the insider program.\nTry requesting insider access with `?insiderrequest`!")
            return
        if not message:
            await ctx.send("# ⚠️ Please provide feedback text,\ne.g. `?insiderfeedback <your feedback>`")
            return
        # You can change this to log to a file, database, or a specific channel
        feedback_channel_id = 1391096986811371590  # Replace with your feedback channel ID
        feedback_channel = self.bot.get_channel(feedback_channel_id)
        feedback_msg = f"📝 **insider Feedback from {ctx.author} in {ctx.guild.name}**:\n{message}"
        if feedback_channel:
            await feedback_channel.send(feedback_msg)
        await ctx.send("# ✅ Thank you for your feedback!\n-# There is up to a 7 day max delay before the developer gives you his feedback!")

    @commands.command(name="insiderchangelog")
    async def insiderchangelog(self, ctx):
        """Show the latest insider-specific changelog."""
        if not utils.is_insider_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the insider program.\nTry requesting insider access with `?insiderrequest`!")
            return
        # You can store this in a file or variable for easier updates
        changelog = (
            "# Insider Changelog:\n"
            "- Added 10+ new commands\n"
            "- Update for ?insider\n"
            "- not much sorry..\n"
        )
        await ctx.send(changelog)
    
    @commands.command(name="rssfetch")
    async def rssfetch(self, ctx, feed_url: str = None):
        """Fetch and display the latest entry from an RSS feed (insider servers only)."""
        if not utils.is_insider_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the insider program.\nTry requesting insider access with `?insiderrequest`!")
            return
        if not feed_url:
            await ctx.send("# ⚠️ Please provide an RSS feed URL,\ne.g. `?rssfetch <url>`")
            return
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                await ctx.send("❔ No entries found in this feed.\n-# It either doesn't exist, has been deleted, or you entered the wrong ID. Try again!")
                return
            entry = feed.entries[0]
            title = entry.title
            link = entry.link
            summary = entry.summary if hasattr(entry, "summary") else ""
            embed = discord.Embed(title=title, url=link, description=summary[:2048], color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"# ❌ Failed to fetch RSS feed: {e}\n-# B.critical, please contact support.")
        
    @commands.command(name="ytalert")
    async def ytalert(self, ctx, channel_id: str = None):
        """Check and announce the latest YouTube video from a channel (insider servers only)."""
        if not utils.is_insider_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the insider program.\nTry requesting insider access with `?insiderrequest`!")
            return
        if not channel_id:
            await ctx.send("# ⚠️ Please provide a YouTube channel ID,\ne.g. `?ytalert <channel_id>`")
            return

        api_key = "YOUR_YOUTUBE_API_KEY"
        url = (
            f"https://www.googleapis.com/youtube/v3/search"
            f"?key={api_key}&channelId={channel_id}&part=snippet,id&order=date&maxResults=1"
        )
        try:
            response = requests.get(url)
            data = response.json()
            if "items" not in data or not data["items"]:
                await ctx.send("❔ No videos found or invalid channel ID,\n-# It either doesn't exist, has been deleted, or you entered your ID wrong, Try again!")
                return
            video = data["items"][0]
            if video["id"]["kind"] != "youtube#video":
                await ctx.send("❗ Latest item is not a video.")
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
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"# ❌ Failed to fetch YouTube video: {e}\n-# B.critical, please contact support.")
    
    @commands.command(name="twitchalert")
    async def twitchalert(self, ctx, twitch_username: str = None):
        """Check and announce if a Twitch channel is live (insider servers only)."""
        if not utils.is_insider_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the insider program.\nTry requesting insider access with `?insiderrequest`!")
            return
        if not twitch_username:
            await ctx.send("# ⚠️ Please provide a Twitch username,\ne.g. `?twitchalert <username>`")
            return

        client_id = "YOUR_TWITCH_CLIENT_ID" 
        access_token = "YOUR_TWITCH_APP_ACCESS_TOKEN" 

        headers = {
            "Client-ID": client_id,
            "Authorization": f"Bearer {access_token}"
        }
        url = f"https://api.twitch.tv/helix/streams?user_login={twitch_username}"

        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            if "data" not in data or not data["data"]:
                await ctx.send(f"❔ {twitch_username} is currently offline or the username is invalid.")
                return
            stream = data["data"][0]
            title = stream["title"]
            game = stream.get("game_name", "Unknown")
            viewer_count = stream["viewer_count"]
            started_at = stream["started_at"]
            thumbnail_url = stream["thumbnail_url"].format(width=640, height=360)
            stream_url = f"https://twitch.tv/{twitch_username}"

            embed = discord.Embed(
                title=f"{twitch_username} is LIVE on Twitch!",
                url=stream_url,
                description=f"**{title}**\nGame: {game}\nViewers: {viewer_count}\nStarted at: {started_at}",
                color=discord.Color.purple()
            )
            embed.set_image(url=thumbnail_url)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"# ❌ Failed to fetch Twitch stream info: {e}\n-# B.critical, please contact support.")
    
    @commands.command(name="setbio")
    async def setbio(self, ctx, *, bio: str = None):
        """Set your personal bio (insider servers only)."""
        if not utils.is_insider_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the insider program.\nTry requesting insider access with `?insiderrequest`!")
            return
        if not bio or len(bio) > 200:
            await ctx.send("# ⚠️ Please provide a bio (max 200 characters).")
            return
        bios_path = "user_bios.json"
        if os.path.exists(bios_path):
            with open(bios_path, "r", encoding="utf-8") as f:
                bios = json.load(f)
        else:
            bios = {}
        bios[str(ctx.author.id)] = bio
        with open(bios_path, "w", encoding="utf-8") as f:
            json.dump(bios, f, ensure_ascii=False, indent=2)
        await ctx.send("# ✅ Your bio has been updated!")
    
    @commands.command(name="setbg")
    async def setbg(self, ctx, url: str = None):
        """Set your profile background image (insider servers only)."""
        if not utils.is_insider_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the insider program.\nTry requesting insider access with `?insiderrequest`!")
            return
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            await ctx.send("# ⚠️ Please provide a valid image URL.")
            return
        bgs_path = "user_bgs.json"
        if os.path.exists(bgs_path):
            with open(bgs_path, "r", encoding="utf-8") as f:
                bgs = json.load(f)
        else:
            bgs = {}
        bgs[str(ctx.author.id)] = url
        with open(bgs_path, "w", encoding="utf-8") as f:
            json.dump(bgs, f, ensure_ascii=False, indent=2)
        await ctx.send("# ✅ Your profile background has been updated!")
    
    @commands.command(name="insiderstatus")
    async def insiderstatus(self, ctx):
        """Show detailed insider status info."""
        if not utils.is_insider_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the insider program.\nTry requesting insider access with `?insiderrequest`!")
            return
        insider_server_ids = utils.load_insider_servers()
        is_insider = ctx.guild and ctx.guild.id in insider_server_ids
        info = variables.bot_info
        msg = (
            f"# insider Status\n"
            f"- Server: {'insider' if is_insider else 'Normal'}\n"
            f"- Version: {info.get('version', 'N/A')}\n"
            f"- insider Version: {info.get('insider_version', 'N/A')}\n"
            f"- New Features: {info.get('new_stuff', 'N/A')}\n"
            f"- insider Features: {info.get('insider_new_stuff', 'N/A')}\n"
            f"- Developer: th3_t1sm\n"
            f"- insider Servers: {len(insider_server_ids)}\n"
        )
        await ctx.send(msg)

    @commands.command(name="addbadge")
    @utils.admin_or_owner()
    async def addbadge(self, ctx, member: discord.Member = None, *, badge: str = None):
        """Give a badge to a user (admin only, insider servers only)."""
        if not utils.is_insider_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the insider program.\nTry requesting insider access with `?insiderrequest`!")
            return
        if not member or not badge:
            await ctx.send("# ❓\nUsage: ?addbadge @user <badge name>")
            return
        badges_path = "user_badges.json"
        if os.path.exists(badges_path):
            with open(badges_path, "r", encoding="utf-8") as f:
                badges = json.load(f)
        else:
            badges = {}
        user_badges = badges.get(str(member.id), [])
        if badge not in user_badges:
            user_badges.append(badge)
        badges[str(member.id)] = user_badges
        with open(badges_path, "w", encoding="utf-8") as f:
            json.dump(badges, f, ensure_ascii=False, indent=2)
        await ctx.send(f"# ✅ {member.display_name} has been awarded the badge: {badge}")

    @commands.command(name="bprofile")
    async def myprofile(self, ctx, member: discord.Member = None):
        """Show your profile, bio, badges, and background (insider servers only)."""
        if not utils.is_insider_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the insider program.\nTry requesting insider access with `?insiderrequest`!")
            return
        member = member or ctx.author
        bios_path = "user_bios.json"
        bgs_path = "user_bgs.json"
        badges_path = "user_badges.json"
        # Load bio
        if os.path.exists(bios_path):
            with open(bios_path, "r", encoding="utf-8") as f:
                bios = json.load(f)
        else:
            bios = {}
        bio = bios.get(str(member.id), "No bio set.")
        # Load background
        if os.path.exists(bgs_path):
            with open(bgs_path, "r", encoding="utf-8") as f:
                bgs = json.load(f)
        else:
            bgs = {}
        bg_url = bgs.get(str(member.id))
        # Load badges
        if os.path.exists(badges_path):
            with open(badges_path, "r", encoding="utf-8") as f:
                badges = json.load(f)
        else:
            badges = {}
        user_badges = badges.get(str(member.id), [])
        badge_str = ", ".join(user_badges) if user_badges else "No badges yet."
        embed = discord.Embed(
            title=f"{member.display_name}'s Profile",
            description=f"Bio: {bio}\nBadges: {badge_str}",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        if bg_url:
            embed.set_image(url=bg_url)
        await ctx.send(embed=embed)
    
async def setup(bot):
    await bot.add_cog(insiderCore(bot))