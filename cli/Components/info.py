# --------------------- IMPORTS --------------------
import discord
from discord.ext import commands
from discord.ui import View, Button
from Ediscord import utils, variables
import typing
from PIL import Image, ImageDraw, ImageFont
import io
import requests
from discord import app_commands
import textwrap
from io import BytesIO

import os

# --------------------- VIEW --------------------
class InfoView(discord.ui.View):
    def __init__(self, embed_general, embed_versions):
        super().__init__()
        self.embed_general = embed_general
        self.embed_versions = embed_versions

    @discord.ui.button(label="General Info", style=discord.ButtonStyle.primary, disabled=True)
    async def general_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = False
        button.disabled = True
        await interaction.response.edit_message(embed=self.embed_general, view=self)

    @discord.ui.button(label="Versions", style=discord.ButtonStyle.secondary)
    async def versions_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = False
        button.disabled = True
        await interaction.response.edit_message(embed=self.embed_versions, view=self)

# --------------------- INFO COMMANDS --------------------
print("✅ - Info loaded.")
class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="profile",
        description="Check your stats, coins, and bank balance."
    )
    async def profile(self, interaction: discord.Interaction, member: typing.Optional[discord.Member] = None):
        """Check your XP, level, coins, and deposited coins. Optionally mention another user to view their profile."""
        member = member or interaction.user
        user_id = member.id
        
        # Load Per-Server Data (XP, Level)
        guild_user_data = utils.get_guild_user_data(interaction.guild.id, user_id)
        xp = guild_user_data.get("xp", 0)
        level = guild_user_data.get("level", 1)
        xp_needed = level * 50
        
        # Load Global Data (Coins)
        global_user_data = utils.get_user_data(user_id)
        coins = global_user_data.get("coins", 0)
        gems = global_user_data.get("gems", 0)
        
        deposited_coins = utils.get_bank_balance(user_id)

        embed = discord.Embed(
            title=f"👤 {member.display_name}'s Profile",
            color=member.color if member.color != discord.Color.default() else discord.Color.blue()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Leveling Section
        embed.add_field(
            name="📊 Leveling", 
            value=f"**Level:** `{level}`\n**XP:** `{xp}/{xp_needed}`", 
            inline=True
        )
        
        # Economy Section
        embed.add_field(
            name="💰 Economy", 
            value=f"**Coins:** `{coins}`\n**Gems:** `{gems}`\n**Bank:** `{deposited_coins}`", 
            inline=True
        )

        embed.set_footer(text=f"Server: {interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="info",
        description="Provides information about this bot."
    )
    async def info(self, interaction: discord.Interaction):
        """
        Note: The docstring here doesn't set the slash command description 
        in discord.py; the 'description' argument in the decorator does.
        """
        # List of insider program server IDs
        insider_server_ids = utils.load_insider_servers()
        
        # In slash commands, ctx.guild.id becomes interaction.guild_id
        if interaction.guild and interaction.guild.id in insider_server_ids:
            description = textwrap.dedent(f"""\
                # I am a multifunctional python Discord bot! ❤️
                - Status: Insider Build
                - Build: Mystralyn-insider
                - Version: **{variables.bot_info['version']}**-insider
                - Developer: th3_t1sm

                You are using the exclusive insider Program build of the bot, **codenamed Mystralyn.**
                This version includes **upcoming features** and **experimental changes.**

                # Thank you for helping test and improve the bot!
            """)
            color = discord.Color.gold()
        else:
            description = textwrap.dedent(f"""\
                # I am a multifunctional python Discord bot! 🐍
                - Status: Public Build
                - Build: beta-Auralis
                - Version: **{variables.bot_info['version']}**
                - Developer: th3_t1sm

                I am multifunctional discord bot created by th3_t1sm,
                This is just a python discord bot made with love.

                ⚠️ **WARNING** ⚠️
                - This bot is still under development.
                - There may be bugs and errors due to the bot being in preview.
                - Some features may not work as expected.
                - If you find any bugs or errors, please report them to the developer using /crashreport

                # Thanks for using our bot! ❤️
            """)
            color = discord.Color.blue()
        
        embed_general = discord.Embed(title="Bot Information", description=description, color=color)

        # --- Version Embed Construction ---
        ver_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ver.txt')
        versions = {}
        if os.path.exists(ver_path):
            with open(ver_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        versions[k.strip()] = v.strip()
        
        if versions:
            ver_desc = "Here are the current versions of all loaded components:\n\n"
            for k, v in versions.items():
                ver_desc += f"**{k}**: `{v}`\n"
        else:
            ver_desc = "No version information found."

        embed_versions = discord.Embed(title="Component Versions", description=ver_desc, color=discord.Color.green())
        
        view = InfoView(embed_general, embed_versions)
        await interaction.response.send_message(embed=embed_general, view=view)


    @app_commands.command(
        name="changelog",
        description="Provides the changelog for this bot."
    )
    async def changelog(self, interaction: discord.Interaction):
        changelog = f"# Here is the changelog for the **{variables.bot_info['version']}**: {variables.bot_info['new_stuff']}"
        await interaction.response.send_message(changelog)

    @app_commands.command(
        name="analyse",
        description="Analyse a user with all available data."
    )
    async def analyse(self, interaction: discord.Interaction, member: typing.Optional[discord.Member] = None):
        """Analyse a user with all available data."""
        member = member or interaction.user  # Default to the command author if no member is mentioned

        # Load Data
        user_id = str(member.id)
        
        # Per-Server Data (XP, Level, Warnings)
        guild_user_data = utils.get_guild_user_data(interaction.guild.id, user_id)
        level = guild_user_data.get("level", 1)
        xp = guild_user_data.get("xp", 0)
        # Warnings in per-server data is a list of objects or just a count in some contexts?
        # In moderation.py update, we made it a list.
        warnings_data = guild_user_data.get("warnings", [])
        warnings = len(warnings_data) if isinstance(warnings_data, list) else 0

        # Global Data (Coins, Gems)
        global_user_data = utils.get_user_data(user_id)
        coins = global_user_data.get("coins", 0)
        gems_collected = global_user_data.get("gems", 0)
        
        # Other Global Data
        inventory = utils.load_inventory().get(user_id, [])
        trophies = variables.trophy_data.get(user_id, [])
        eggs_collected = variables.easter_data.get(user_id, {}).get("eggs", 0)
        bank_balance = utils.get_bank_balance(user_id)

        # Create the embed
        embed = discord.Embed(
            title=f"Analysis of {member.name}",
            description=f"Here are the details of {member.mention}",
            color=discord.Color.blue(),
        )

        # Add Discord profile details
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        embed.add_field(
            name="Full Name", value=f"{member.name}#{member.discriminator}", inline=False
        )
        embed.add_field(name="ID", value=member.id, inline=False)
        embed.add_field(name="Status", value=member.status, inline=False)
        embed.add_field(
            name="Account Created On",
            value=member.created_at.strftime("%d %B %Y, %H:%M:%S"),
            inline=False,
        )
        embed.add_field(
            name="Joined Server On",
            value=member.joined_at.strftime("%d %B %Y, %H:%M:%S") if member.joined_at else "Unknown",
            inline=False,
        )
        embed.add_field(
            name="Roles",
            value=", ".join(
                [role.name for role in member.roles if role.name != "@everyone"]
            )
            or "None",
            inline=False,
        )

        # Add bot-related stats
        embed.add_field(name="Level", value=level, inline=True)
        embed.add_field(name="XP", value=xp, inline=True)
        embed.add_field(name="Coins", value=coins, inline=True)
        embed.add_field(name="Gems", value=gems_collected, inline=True)
        embed.add_field(name="Eggs Collected", value=eggs_collected, inline=True)
        embed.add_field(name="Bank Balance", value=f"{bank_balance} coins", inline=True)
        embed.add_field(name="Warnings", value=warnings, inline=True)

        # Add inventory details
        if inventory:
            inventory_items = "\n".join(
                [f"{item['name']} (Rarity: {item['rarity']})" for item in inventory]
            )
            embed.add_field(name="Inventory", value=inventory_items, inline=False)
        else:
            embed.add_field(name="Inventory", value="Empty", inline=False)

        # Add trophies
        if trophies:
            trophy_names = [
                trophies[trophy_id]["name"]
                for trophy_id in trophies
                if trophy_id in trophies
            ]
            embed.add_field(name="Trophies", value=", ".join(trophy_names), inline=False)
        else:
            embed.add_field(name="Trophies", value="None", inline=False)

        # Send the embed
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="serverstats",
        description="Show detailed server statistics."
    )
    async def server_stats(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not utils.is_insider_server(guild.id):
            await interaction.response.send_message("# ❌ This server is not in the insider program.\nTry requesting insider access with `?insiderrequest`!")
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

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="setannouncements",
        description="Enable or disable announcements for this server."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_announcements(self, interaction: discord.Interaction, ann_type: str, state: str):
        """Enable or disable announcements for this server.

        Usage: `/setannouncements <announcements|general_updates> <on|off>`
        """
        ann_type = ann_type.lower()
        state = state.lower()

        if ann_type in ("announcements", "announcement", "ann"):
            key = "announcements_enabled"
        elif ann_type in ("general_updates", "updates", "general"):
            key = "general_updates_enabled"
        else:
            await interaction.response.send_message("❌ Unknown announcement type. Use `announcements` or `general_updates`.")
            return

        if state in ("on", "enable", "true", "1"):
            val = True
        elif state in ("off", "disable", "false", "0"):
            val = False
        else:
            await interaction.response.send_message("❌ State must be `on` or `off`.")
            return

        utils.set_guild_setting(interaction.guild.id, key, val)
        await interaction.response.send_message(f"✅ Set `{key}` to `{val}` for this server.")

    @app_commands.command(
        name="showannouncementssettings",
        description="Show the current announcements settings for this server."
    )
    async def show_announcements_settings(self, interaction: discord.Interaction):
        """Show the current announcements settings for this server."""
        ann = utils.get_guild_setting(interaction.guild.id, "announcements_enabled", True)
        gen = utils.get_guild_setting(interaction.guild.id, "general_updates_enabled", True)
        await interaction.response.send_message(f"📢 Announcements enabled: `{ann}`\n📰 General updates enabled: `{gen}`)")
    
    @app_commands.command(
        name="submitidea",
        description="Submit an idea for the bot."
    )
    async def submit_idea(self, interaction: discord.Interaction, message: str):
        idea_channel_id = 1433185701100388392  # dev channel ID
        idea_channel = self.bot.get_channel(idea_channel_id)
        embed = discord.Embed(
            title="💡 New Idea",
            description=message,
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"From {interaction.user} in {interaction.guild.name}")
        if idea_channel:
            await idea_channel.send(embed=embed)
        await interaction.response.send_message("✅ Your idea has been submitted!")
    
    @app_commands.command(
        name="feedback",
        description="Send feedback about the insider program."
    )
    async def insider_feedback(self, interaction: discord.Interaction, message: str):
        """Send feedback about the insider program (only for insider servers)."""
        # You can change this to log to a file, database, or a specific channel
        feedback_channel_id = 1433185701100388392  # Replace with your feedback channel ID
        feedback_channel = self.bot.get_channel(feedback_channel_id)
        feedback_msg = f"📝 **insider Feedback from {interaction.user} in {interaction.guild.name}**:\n{message}"
        if feedback_channel:
            await feedback_channel.send(feedback_msg)
        await interaction.response.send_message("# ✅ Thank you for your feedback!\n-# There is up to a 7 day max delay before the developer gives you his feedback!")
    
    @app_commands.command(
        name="crashreport",
        description="Submit a crash report for the bot."
    )
    async def crash_report(self, interaction: discord.Interaction, description: str):
        log_channel = self.bot.get_channel(1433185701100388392)
        embed = discord.Embed(title="🚨 Crash Report", description=description, color=discord.Color.red())
        embed.set_footer(text=f"From {interaction.user} in {interaction.guild.name}")
        if log_channel:
            await log_channel.send(embed=embed)
        await interaction.response.send_message("✅ Crash report logged. Thanks!")
    
async def setup(bot):
    print("Loading Info cog...")
    await bot.add_cog(Info(bot))
