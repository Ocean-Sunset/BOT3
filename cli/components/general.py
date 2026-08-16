import time
import random
import discord
from discord import app_commands
from discord.ext import commands
import datetime

from Ediscord import variables, utils, EmbedBuilder
from Ediscord.builders import emoji_title


class General(commands.Cog):
    """General-purpose commands for Prowl."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check Prowl's latency.")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = (
            EmbedBuilder()
            .title(emoji_title("bolt", "Pong!"))
            .description(f"**Latency:** {latency}ms\n**API Latency:** {round(self.bot.latency * 1000)}ms")
            .color("warn")
            .footer(f"Prowl v{variables.__version__}")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="info", description="Show Prowl's info.")
    async def info(self, interaction: discord.Interaction):
        uptime = utils.get_uptime()
        embed = (
            EmbedBuilder()
            .title(emoji_title("bot", "Prowl"))
            .description("A silly little cat bot with a ton of abilities.")
            .color("gray")
            .thumbnail("https://prowlbot.xyz/static/favicon.png")
            .field("Servers", str(len(self.bot.guilds)), inline=True)
            .field("Users", str(len(self.bot.users)), inline=True)
            .field("Uptime", uptime, inline=True)
            .field("Cogs Loaded", str(len(self.bot.cogs)), inline=True)
            .field("Commands", str(len(self.bot.tree.get_commands())), inline=True)
            .field("Python Version", f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}.{__import__('sys').version_info.micro}", inline=True)
            .field("discord.py Version", discord.__version__, inline=True)
            .footer(f"Prowl v{variables.__version__}")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="say", description="Echo back your message.")
    @app_commands.describe(text="The text to echo back.", channel="Channel to send to (optional)")
    async def say(self, interaction: discord.Interaction, text: str, channel: discord.TextChannel = None):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Messages permission.").color("error").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        target = channel or interaction.channel
        embed = (
            EmbedBuilder()
            .description(text)
            .color("blurple")
            .footer(f"Requested by {interaction.user.display_name}")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await target.send(embed=embed)
        if target != interaction.channel:
            await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("send", "Message Sent")).description(f"Sent to {target.mention}").color("success").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("send", "Message Sent")).color("success").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )

    @app_commands.command(name="serverinfo", description="Show server information.")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        owner = await guild.fetch_member(guild.owner_id) if guild.owner_id else None
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        online = sum(1 for m in guild.members if m.status == discord.Status.online)
        idle = sum(1 for m in guild.members if m.status == discord.Status.idle)
        dnd = sum(1 for m in guild.members if m.status == discord.Status.dnd)
        offline = sum(1 for m in guild.members if m.status == discord.Status.offline)
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count or 0
        embed = (
            EmbedBuilder()
            .title(emoji_title("server", guild.name))
            .color("gray")
            .thumbnail(guild.icon.url if guild.icon else None)
            .field("Owner", owner.mention if owner else "Unknown")
            .field("Members", str(guild.member_count), inline=True)
            .field("Humans", str(sum(1 for m in guild.members if not m.bot)), inline=True)
            .field("Bots", str(sum(1 for m in guild.members if m.bot)), inline=True)
            .field("Online", f"🟢 {online}", inline=True)
            .field("Idle", f"🟡 {idle}", inline=True)
            .field("DND", f"🔴 {dnd}", inline=True)
            .field("Text Channels", str(text_channels), inline=True)
            .field("Voice Channels", str(voice_channels), inline=True)
            .field("Categories", str(categories), inline=True)
            .field("Roles", str(len(guild.roles)))
            .field("Emojis", str(len(guild.emojis)))
            .field("Boost Level", f"Level {boost_level} ({boost_count} boosts)")
            .field("Created", discord.utils.format_dt(guild.created_at, style="F"))
            .field("Server ID", str(guild.id))
            .footer(f"Requested by {interaction.user.display_name}")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Show information about a user.")
    @app_commands.describe(user="The user to look up")
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member = None):
        target = user or interaction.user
        roles = [r.mention for r in target.roles if r != target.guild.default_role]
        roles_str = ", ".join(roles[:20]) if roles else "None"
        if len(roles) > 20:
            roles_str += f" and {len(roles) - 20} more..."
        permissions = [p for p, v in target.guild_permissions if v]
        key_perms = [p.replace("_", " ").title() for p in permissions if p in ["administrator", "manage_guild", "manage_roles", "manage_channels", "manage_messages", "ban_members", "kick_members"]]
        perms_str = ", ".join(key_perms[:5]) if key_perms else "None"
        embed = (
            EmbedBuilder()
            .title(emoji_title("member", target.display_name))
            .color(target.color if target.color != discord.Color.default() else "gray")
            .thumbnail(target.display_avatar.url)
            .field("Username", target.name, inline=True)
            .field("Nickname", target.nick or "None", inline=True)
            .field("User ID", str(target.id), inline=True)
            .field("Account Created", discord.utils.format_dt(target.created_at, style="F"), inline=True)
            .field("Joined Server", discord.utils.format_dt(target.joined_at, style="F") if target.joined_at else "Unknown", inline=True)
            .field("Roles", roles_str[:1024], inline=True)
            .field("Key Permissions", perms_str, inline=True)
            .field("Status", str(target.status).title(), inline=True)
            .field("Bot", "Yes" if target.bot else "No", inline=True)
            .footer(f"Requested by {interaction.user.display_name}")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Show a user's avatar.")
    @app_commands.describe(user="The user whose avatar to show")
    async def avatar(self, interaction: discord.Interaction, user: discord.Member = None):
        target = user or interaction.user
        avatar_url = target.display_avatar.url
        embed = (
            EmbedBuilder()
            .title(emoji_title("member", f"{target.display_name}'s Avatar"))
            .color("gray")
            .image(avatar_url)
            .description(f"[Open in Browser]({avatar_url})")
            .footer(f"Requested by {interaction.user.display_name}")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roleinfo", description="Show information about a role.")
    @app_commands.describe(role="The role to look up")
    async def roleinfo(self, interaction: discord.Interaction, role: discord.Role):
        members_with_role = [m for m in role.guild.members if role in m.roles]
        embed = (
            EmbedBuilder()
            .title(emoji_title("role", role.name))
            .color(role.color if role.color != discord.Color.default() else "brand")
            .field("Role ID", str(role.id), inline=True)
            .field("Color", f"#{role.color.value:06x}" if role.color != discord.Color.default() else "Default", inline=True)
            .field("Position", str(role.position), inline=True)
            .field("Members", str(len(members_with_role)), inline=True)
            .field("Mentionable", "Yes" if role.mentionable else "No", inline=True)
            .field("Hoisted", "Yes" if role.hoist else "No", inline=True)
            .field("Managed", "Yes" if role.managed else "No", inline=True)
            .field("Created", discord.utils.format_dt(role.created_at, style="F"), inline=True)
            .field("Permissions", ", ".join([p.replace("_", " ").title() for p, v in role.permissions if v][:10]) or "None", inline=True)
            .footer(f"Requested by {interaction.user.display_name}")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="channelinfo", description="Show information about a channel.")
    @app_commands.describe(channel="The channel to look up")
    async def channelinfo(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        target = channel or interaction.channel
        topic = target.topic or "No topic set"
        slowmode = target.slowmode_delay
        slowmode_str = f"{slowmode}s" if slowmode else "Disabled"
        embed = (
            EmbedBuilder()
            .title(emoji_title("channel", target.name))
            .color("gray")
            .field("Channel ID", str(target.id), inline=True)
            .field("Type", str(target.type).title(), inline=True)
            .field("Category", target.category.name if target.category else "None", inline=True)
            .field("Topic", topic[:1024], inline=True)
            .field("Slowmode", slowmode_str, inline=True)
            .field("NSFW", "Yes" if target.nsfw else "No", inline=True)
            .field("Position", str(target.position), inline=True)
            .field("Created", discord.utils.format_dt(target.created_at, style="F"), inline=True)
            .footer(f"Requested by {interaction.user.display_name}")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(General(bot))
