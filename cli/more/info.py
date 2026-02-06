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

# --------------------- INFO COMMANDS --------------------
print("✅ - Info loaded.")
class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="profile",
        description="Check your XP, level, coins, and deposited coins."
    )
    async def profile(self, interaction: discord.Interaction, member: typing.Optional[discord.Member] = None):
        """Check your XP, level, coins, and deposited coins. Optionally mention another user to view their profile."""
        member = member or interaction.user  # Default to command author if no member mentioned
        user_id = member.id
        user_data = utils.get_user_data(user_id)

        xp = user_data["xp"]
        level = user_data["level"]
        coins = user_data["coins"]
        deposited_coins = utils.get_bank_balance(user_id)  # Retrieve the user's bank balance

        await interaction.response.send_message(
            f"# 📜 **{member.name}'s Profile**:\n"
            f"🔹 XP: **{xp}**\n"
            f"🔹 Level: **{level}**\n"
            f"🔹 Coins: **{coins}**\n"
            f"🔹 Deposited Coins: **{deposited_coins}**"
        )

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
            custominfo = textwrap.dedent(f"""\
                # I am a multifunctional python Discord bot! ❤️
                - Status: Insider Build
                - Build: Lunara-insider
                - Version: **{variables.bot_info['version']}**-insider
                - Developer: th3_t1sm

                You are using the exclusive insider Program build of the bot, **codenamed Lunara.**
                This version includes **upcoming features** and **experimental changes.**

                # Thank you for helping test and improve the bot!
            """)
        else:
            custominfo = textwrap.dedent(f"""\
                # I am a multifunctional python Discord bot! 🐍
                - Status: Public Build
                - Build: Celestra
                - Version: **{variables.bot_info['version']}**
                - Developer: th3_t1sm

                I am multifunctional discord bot created by th3_t1sm,
                This is just a python discord bot made with love.

                # Thanks for using our bot! ❤️
            """)
        
        # Use interaction.response.send_message instead of ctx.send
        await interaction.response.send_message(custominfo)


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

        # Load user data
        user_id = str(member.id)
        user_data = utils.get_user_data(user_id)
        inventory = utils.load_inventory().get(user_id, [])
        trophies = variables.trophy_data.get(user_id, [])
        warnings = variables.warnings_data.get(user_id, {}).get("warnings", 0)
        eggs_collected = variables.easter_data.get(user_id, {}).get("eggs", 0)
        gems_collected = user_data.get("gems", 0)
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
        embed.add_field(name="Level", value=user_data.get("level", 0), inline=True)
        embed.add_field(name="XP", value=user_data.get("xp", 0), inline=True)
        embed.add_field(name="Coins", value=user_data.get("coins", 0), inline=True)
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
