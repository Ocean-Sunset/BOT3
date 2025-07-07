from discord.ext import commands
import discord
import os
import json
from Ediscord import variables, utils
import feedparser
import requests

class BetaCore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="beta")
    async def beta(self, ctx):
        """Show info about the beta program (only for approved servers)."""
        if not utils.is_beta_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the beta program.\nTry requesting beta access with `?betarequest`!")
            return

        await ctx.send(
            "# Welcome to the Beta Program!\n"
            "Use `?betastatus` to confirm you're in.\n"
            "Use `?betaremove <guild_id>` to remove a server from beta.\n"
            "Use `?serverstats` to check your server statics.\n"
            "Use `?betafeedback <message>` to feedback your experience with the Beta Program.\n"
            "Use `?betachangelog` to check the Beta Program changelog.\n"
            "Use `?rssfetch <feed_id>` to fetch a feed from RSS.\n"
            "Use `?ytalert <channel_id>` to fetch the latest video from the user.\n"
            "Use `?twitchalert <channel_id>` to fetch the latest video / stream from the user.\n"
            "Use `?setbio <guild_id>` to set a custom bio for yourself.\n"
            "Use `?bprofile <user>` to check your or other peoples profiles.\n"
            "Use `?addbadge <member> <badge>` to add a badge to other people (admin only).\n"
            "Use `?setbg <url>` set your profile background.\n"
        )
    
    @commands.command(name="serverstats")
    async def serverstats(self, ctx):
        """Show detailed server statistics."""
        guild = ctx.guild
        if not utils.is_beta_server(guild.id):
            await ctx.send("# ❌ This server is not in the beta program.\nTry requesting beta access with `?betarequest`!")
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
    
    @commands.command(name="betafeedback")
    async def betafeedback(self, ctx, *, message: str = None):
        """Send feedback about the beta program (only for beta servers)."""
        if not utils.is_beta_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the beta program.\nTry requesting beta access with `?betarequest`!")
            return
        if not message:
            await ctx.send("# ⚠️ Please provide feedback text,\ne.g. `?betafeedback <your feedback>`")
            return
        # You can change this to log to a file, database, or a specific channel
        feedback_channel_id = 1391096986811371590  # Replace with your feedback channel ID
        feedback_channel = self.bot.get_channel(feedback_channel_id)
        feedback_msg = f"📝 **Beta Feedback from {ctx.author} in {ctx.guild.name}**:\n{message}"
        if feedback_channel:
            await feedback_channel.send(feedback_msg)
        await ctx.send("# ✅ Thank you for your feedback!\n-# There is up to a 7 day max delay before the developer gives you his feedback!")

    @commands.command(name="betachangelog")
    async def betachangelog(self, ctx):
        """Show the latest beta-specific changelog."""
        if not utils.is_beta_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the beta program.\nTry requesting beta access with `?betarequest`!")
            return
        # You can store this in a file or variable for easier updates
        changelog = (
            "**Beta Changelog:**\n"
            "- Added server stats command\n"
            "- Added beta feedback command\n"
            "- More features coming soon!\n"
        )
        await ctx.send(changelog)
    
    @commands.command(name="rssfetch")
    async def rssfetch(self, ctx, feed_url: str = None):
        """Fetch and display the latest entry from an RSS feed (beta servers only)."""
        if not utils.is_beta_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the beta program.\nTry requesting beta access with `?betarequest`!")
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
        """Check and announce the latest YouTube video from a channel (beta servers only)."""
        if not utils.is_beta_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the beta program.\nTry requesting beta access with `?betarequest`!")
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
        """Check and announce if a Twitch channel is live (beta servers only)."""
        if not utils.is_beta_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the beta program.\nTry requesting beta access with `?betarequest`!")
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
        """Set your personal bio (beta servers only)."""
        if not utils.is_beta_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the beta program.\nTry requesting beta access with `?betarequest`!")
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
        """Set your profile background image (beta servers only)."""
        if not utils.is_beta_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the beta program.\nTry requesting beta access with `?betarequest`!")
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

    @commands.command(name="addbadge")
    @commands.has_permissions(administrator=True)
    async def addbadge(self, ctx, member: discord.Member = None, *, badge: str = None):
        """Give a badge to a user (admin only, beta servers only)."""
        if not utils.is_beta_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the beta program.\nTry requesting beta access with `?betarequest`!")
            return
        if not member or not badge:
            await ctx.send("❓ Usage: ?addbadge @user <badge name>")
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
        """Show your profile, bio, badges, and background (beta servers only)."""
        if not utils.is_beta_server(ctx.guild.id):
            await ctx.send("# ❌ This server is not in the beta program.\nTry requesting beta access with `?betarequest`!")
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
    await bot.add_cog(BetaCore(bot))