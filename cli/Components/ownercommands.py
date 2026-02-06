# --------------------- IMPORTS --------------------
from Ediscord import variables, utils
from discord.ext import commands
import os
import discord
from discord.ext.commands import CommandOnCooldown
from discord.ext.commands import CooldownMapping
from discord.ext.commands import cooldown
from discord import app_commands
from discord.ext.commands import BucketType
import sys
import re
import unicodedata
from PIL import Image, ImageDraw, ImageFont
import logging
from discord.ui import Button, View
import asyncio
import typing

# --------------------- OWNER COMMANDS --------------------

ANNOUNCEMENT_KEYWORDS = {
    "announcement", "announcements", "announce",
    "news", "update", "updates", "info",
    "changelog", "changes", "broadcast",
    "notice", "notices",
    "bot", "system", "status",
    "alerts", "alert"
}

SEPARATORS_REGEX = re.compile(r"[│┃丨•·—–\-_=+~]+")
EMOJI_REGEX = re.compile(
    "["
    "\U0001F300-\U0001FAD6"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "]+",
    flags=re.UNICODE
)

def normalize_text(text: str) -> str:
    if not text:
        return ""
    # Normalize fancy unicode fonts to standard ascii
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Remove emojis and clean separators
    text = EMOJI_REGEX.sub("", text)
    text = SEPARATORS_REGEX.sub(" ", text)
    # Collapse whitespace
    return re.sub(r"\s+", " ", text.lower()).strip()

def score_channel(channel: discord.TextChannel) -> int:
    score = 0
    name = normalize_text(channel.name)
    topic = normalize_text(channel.topic or "")
    combined = f"{name} {topic}"

    # Priority 1: Official Announcement Channels
    if channel.type == discord.ChannelType.news:
        score += 100

    # Priority 2: Keyword matches
    for keyword in ANNOUNCEMENT_KEYWORDS:
        if keyword in name:
            score += 10
        if keyword in topic:
            score += 6

    # Priority 3: Specific intent bonus
    if "announce" in combined:
        score += 5

    # Penalty: Chatty channels
    if "general" in name or "chat" in name:
        score -= 5

    return score

print("✅ - Owner commands loaded.")
class Ownercommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="ban_server", description="Ban a server by name (owner only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def ban_server(self, interaction: discord.Interaction, server_name: str):
        for guild in self.bot.guilds:
            if guild.name.lower() == server_name.lower():
                if guild.id in variables.banned_servers:
                    await interaction.response.send_message(f"# ❌ Server **{server_name}** is already banned!\nMaybe just maybe.. unban them??", ephemeral=True)
                    return
                variables.banned_servers.append(guild.id)
                utils.save_banned_servers()
                await interaction.response.send_message(
                    f"# ✅ Server **{server_name}** has been banned.\nThe bot will no longer work there unless the removal of this ban.", ephemeral=True
                )
                return
        await interaction.response.send_message(f"# ❓ Server **{server_name}** not found.\nYou sure you entered the right name?", ephemeral=True)


    @app_commands.command(name="unban_server", description="Unban a server by name (owner only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def unban_server(self, interaction: discord.Interaction, server_name: str):
        for guild in self.bot.guilds:
            if guild.name.lower() == server_name.lower():
                if guild.id not in variables.banned_servers:
                    await interaction.response.send_message(f"# ❌ Server **{server_name}** is not banned!\n{utils.little_text()}", ephemeral=True)
                    return
                variables.banned_servers.remove(guild.id)
                utils.save_banned_servers()
                await interaction.response.send_message(
                    f"# ✅ Server **{server_name}** has been un-banned.\nThe bot will now work there unless the reapplication of this ban.", ephemeral=True
                )
                return
        await interaction.response.send_message(f"# ❓ Server **{server_name}** not found.\nYou sure you entered the right name?", ephemeral=True)


    @app_commands.command(name="manage_server", description="Set restriction level for a server (owner only)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(server_name="The server name", restriction_level="Restriction level: Free, Limited, Very Limited, Absolute Restriction")
    async def manage_server(self, interaction: discord.Interaction, server_name: str, restriction_level: str):
        restriction_levels = ["Free", "Limited", "Very Limited", "Absolute Restriction"]
        if restriction_level not in restriction_levels:
            await interaction.response.send_message(
                f"# ❌ Invalid restriction level\nChoose from: {', '.join(restriction_levels)}.", ephemeral=True
            )
            return
        for guild in self.bot.guilds:
            if guild.name.lower() == server_name.lower():
                variables.server_restrictions[str(guild.id)] = restriction_level
                utils.save_server_restrictions()
                await interaction.response.send_message(
                    f"# # ✅ Server **{server_name}**\nis now set to **{restriction_level}** mode.", ephemeral=True
                )
                return
        await interaction.response.send_message(f"# ❓ Server **{server_name}** not found.\nYou sure you entered the right name?", ephemeral=True)


    @commands.command(name="update")
    @commands.check(utils.is_owner)
    async def update(self, ctx, *, args: str):
        """
        Update the bot's version and new features, then restart.
        Usage:
        ?update <version> / <new features>
        ?update insider <version> / <new features>
        """
        global current_status
        is_insider = False

        # Check for insider flag
        if args.lower().startswith("insider "):
            is_insider = True
            args = args[5:].strip()

        try:
            version, new_stuff = args.split(" / ")
        except ValueError as e:
            await ctx.send(
                f"# ❌ Invalid format.\nUse `?update <version> / <new features>` or `?update insider <version> / <new features>`.\nError: {e}"
            )
            return

        if is_insider:
            # Update only insider info (you may want to store this separately)
            variables.bot_info["insider_version"] = version
            variables.bot_info["insider_new_stuff"] = new_stuff
            utils.save_bot_info()
            await ctx.send(
                f"# ✅ insider updated to version **{version}**\nwith new features: **{new_stuff}**."
            )
            await ctx.send("** ---  🔄 Restarting the bot for insider testers only...  ---**")
            utils.signal_update(f"insider|New version: {version}\nNew stuff: {new_stuff}")
        else:
            # Update the main info
            variables.bot_info["version"] = version
            variables.bot_info["new_stuff"] = new_stuff
            utils.save_bot_info()
            current_status = discord.Game("Updating...")
            await self.bot.change_presence(
                status=discord.Status.dnd, activity=current_status
            )
            await ctx.send(
                f"# ✅ Bot updated to version **{version}**\nwith new features: **{new_stuff}**."
            )
            await ctx.send("** ---  🔄 Restarting the bot...  ---**")

        # Restart the bot
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @app_commands.command(name="restart", description="Restart the bot (owner only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def restart(self, interaction: discord.Interaction):
        global current_status
        current_status = discord.Game("Restarting...")
        await self.bot.change_presence(status=discord.Status.dnd, activity=current_status)
        await interaction.response.send_message("# **🔄 Restarting the bot...**", ephemeral=True)
        await self.bot.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)


    @app_commands.command(name="shutdown", description="Shutdown the bot entirely (owner only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def shutdown(self, interaction: discord.Interaction):
        await interaction.response.send_message("# Goobye!\nThe bot will now shut down.\n-# I hope i get restarted soon :(...", ephemeral=True)
        await self.bot.close()


    @app_commands.command(name="copychannel", description="Send a message to a channel (owner only)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Channel to send to", text="Text to send")
    async def copychannel(self, interaction: discord.Interaction, channel: discord.TextChannel, text: str):
        try:
            await channel.send(f"{text}")
            await interaction.response.send_message(f"# ✅ Sent the message to {channel.mention}.\n-# Sent the following message to {channel.mention}: {text}", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"# ❌ I cannot send messages to {channel.mention}.\nMaybe it's a role issue?", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"# ❌ An error occurred: {e}\n{utils.little_text()}", ephemeral=True)
    

    @app_commands.command(name="copy", description="Echo a message (owner only)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(text="Text to echo")
    async def copy(self, interaction: discord.Interaction, text: str):
        await interaction.response.send_message(text, ephemeral=True)


    @app_commands.command(name="copydm", description="Send a DM to a member (owner only)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(member="Member to DM", text="Text to send")
    async def copydm(self, interaction: discord.Interaction, member: discord.Member, text: str):
        try:
            await member.send(text)
            await interaction.response.send_message(f"✅ Sent the message to {member.mention}'s DMs.\n-# Sent the following message to {member}'s DMs: {text}", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"# ❌ I cannot send DMs to {member.mention}.\nThey may have their DMs disabled.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"# ❌ An error occurred: {e}\n{utils.little_text()}", ephemeral=True)


    @app_commands.command(name="modify_status", description="Modify the bot's status and activity (owner only)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(status_type="Type: playing, watching, listening, streaming", activity="Activity name")
    async def modify_status(self, interaction: discord.Interaction, status_type: str, activity: typing.Optional[str] = None):
        global custom_status
        custom_status = None
        if status_type.lower() == "default":
            custom_status = None
            await interaction.response.send_message(
                f"# ✅ The bot's status has been reset to its default rotating behavior.\n{utils.little_text()}", ephemeral=True
            )
            return
        valid_status_types = ["playing", "watching", "listening", "streaming"]
        if status_type.lower() not in valid_status_types:
            await interaction.response.send_message(
                f"# ❌ Invalid status type.\nChoose from: {', '.join(valid_status_types)}.", ephemeral=True
            )
            return
        if activity is None:
            await interaction.response.send_message("# ❌ Please provide an activity name for the status.\nSomething like: 'Gaming is fun!'", ephemeral=True)
            return
        if status_type.lower() == "playing":
            custom_status = discord.Game(activity)
        elif status_type.lower() == "watching":
            custom_status = discord.Activity(type=discord.ActivityType.watching, name=activity)
        elif status_type.lower() == "listening":
            custom_status = discord.Activity(type=discord.ActivityType.listening, name=activity)
        elif status_type.lower() == "streaming":
            custom_status = discord.Streaming(name=activity, url="https://www.twitch.tv/your_channel")
        await self.bot.change_presence(status=discord.Status.online, activity=custom_status)
        await interaction.response.send_message(
            f"# ✅ The bot's status has been updated!\nHere's the new status: **{status_type.capitalize()} {activity}**.", ephemeral=True
        )



    @app_commands.command(name="levelsystem", description="Enable, disable, or check status of level role system.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(action="Action: enable, disable, status")
    async def levelsystem(self, interaction: discord.Interaction, action: str):
        action = action.lower()
        guild_id = interaction.guild.id
        if action == "enable":
            utils.set_level_role_system_enabled(guild_id, True)
            await interaction.response.send_message("✅ Level role system has been enabled for this server.", ephemeral=True)
        elif action == "disable":
            utils.set_level_role_system_enabled(guild_id, False)
            await interaction.response.send_message("✅ Level role system has been disabled for this server.", ephemeral=True)
        elif action == "status":
            enabled = utils.is_level_role_system_enabled(guild_id)
            await interaction.response.send_message(f"Level role system is currently **{'enabled' if enabled else 'disabled'}** for this server.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Invalid action. Use `enable`, `disable`, or `status`.", ephemeral=True)


    @app_commands.command(name="levelannouncements", description="Enable, disable, or check status of level-up announcements.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(action="Action: enable, disable, status")
    async def levelannouncements(self, interaction: discord.Interaction, action: str):
        action = action.lower()
        guild_id = interaction.guild.id
        if action == "enable":
            utils.set_level_announcements_enabled(guild_id, True)
            await interaction.response.send_message("✅ Level announcements have been enabled for this server.", ephemeral=True)
        elif action == "disable":
            utils.set_level_announcements_enabled(guild_id, False)
            await interaction.response.send_message("✅ Level announcements have been disabled for this server.", ephemeral=True)
        elif action == "status":
            enabled = utils.is_level_announcements_enabled(guild_id)
            await interaction.response.send_message(f"Level announcements are currently **{'enabled' if enabled else 'disabled'}** for this server.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Invalid action. Use `enable`, `disable`, or `status`.", ephemeral=True)


    @app_commands.command(name="setlevelrole", description="Set an existing role as a level role.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(level="Level number", role="Role to set")
    async def setlevelrole_existing(self, interaction: discord.Interaction, level: int, role: discord.Role):
        if level < 1:
            await interaction.response.send_message("❌ Level must be a positive number.", ephemeral=True)
            return
        utils.set_guild_level_role(interaction.guild.id, level, role.name)
        await interaction.response.send_message(f"✅ Set level {level} role to {role.mention}", ephemeral=True)


    @app_commands.command(name="removelevelrole", description="Remove the custom role for a specific level.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(level="Level number")
    async def removelevelrole(self, interaction: discord.Interaction, level: int):
        utils.remove_guild_level_role(interaction.guild.id, level)
        await interaction.response.send_message(f"✅ Removed custom role for level {level}", ephemeral=True)


    @app_commands.command(name="listlevelroles", description="List all level roles for this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def listlevelroles(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        custom_roles = utils.get_guild_level_roles(guild_id)
        system_enabled = utils.is_level_role_system_enabled(guild_id)
        embed = discord.Embed(
            title="Level Role Configuration",
            description=f"System Status: **{'Enabled' if system_enabled else 'Disabled'}**",
            color=discord.Color.blue()
        )
        if custom_roles:
            custom_text = ""
            for level, role_name in sorted(custom_roles.items(), key=lambda x: int(x[0])):
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if role:
                    custom_text += f"Level {level}: {role.mention}\n"
                else:
                    custom_text += f"Level {level}: {role_name}\n"
            embed.add_field(name="Custom Level Roles", value=custom_text or "None set", inline=False)
        else:
            default_text = ""
            for level, role_name in sorted(variables.level_roles.items()):
                default_text += f"Level {level}: {role_name}\n"
            embed.add_field(name="Default Level Roles", value=default_text, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="reset", description="Reset all data and delete all songs (owner only, no confirmation)")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset(self, interaction: discord.Interaction):
        # WARNING: This version does not do interactive confirmation, as slash commands do not support message-based confirmation easily.
        try:
            data_files = [
                "data/achievements.json",
                "data/akari_points.json",
                "data/bank.json",
                "data/insider_servers.json",
                "data/bot_info.json",
                "data/inventory.json",
                "data/limitations.json",
                "data/logging_config.json",
                "data/prefixes.json",
                "data/scheduled_messages.json",
                "data/server_settings.json",
                "data/user_badges.json",
                "data/user_bgs.json",
                "data/user_bios.json",
                "data/user_data.json"
            ]
            for file in data_files:
                if os.path.exists(file):
                    os.remove(file)
                    await interaction.channel.send(f"🗑️ Deleted `{file}`.")
            for folder in ["music", "backups", "assets", "Ediscord"]:
                if os.path.exists(folder):
                    for file in os.listdir(folder):
                        file_path = os.path.join(folder, file)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    await interaction.channel.send(f"🗑️ Deleted all files in the `{folder}` folder.")
            await interaction.response.send_message("# ✅ **Reset complete.\nEverything has been deleted.\n-# Goodbye.**", ephemeral=True)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            await interaction.response.send_message(f"# ❌ An error occurred during the reset:\n{e}", ephemeral=True)


    @app_commands.command(name="setlogging", description="Enable or disable logging for the server.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(action="enable or disable")
    async def setlogging(self, interaction: discord.Interaction, action: str):
        if action not in ["enable", "disable"]:
            await interaction.response.send_message("# ❓ **Usage:**\n`/setlogging <enable|disable>`", ephemeral=True)
            return
        guild_id = str(interaction.guild.id)
        logging_config = utils.load_logging_config()
        if action == "enable":
            logging_config[guild_id] = True
            utils.save_logging_config(logging_config)
            await interaction.response.send_message("# ✅ Logging has been **enabled** for this server.", ephemeral=True)
        elif action == "disable":
            logging_config[guild_id] = False
            utils.save_logging_config(logging_config)
            await interaction.response.send_message("# ✅ Logging has been **disabled** for this server.", ephemeral=True)


    @app_commands.command(name="selfkick", description="Bot leaves the server (owner only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def selfkick(self, interaction: discord.Interaction):
        await interaction.response.send_message("# 👋 Leaving the server!\nSeems like my owner didn't like your server or something.", ephemeral=True)
        try:
            signals_dir = utils.SIGNALS_DIR
        except Exception:
            signals_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "handler", "signals"))
        try:
            os.makedirs(signals_dir, exist_ok=True)
            path = os.path.join(signals_dir, "botleft.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(interaction.guild.id))
        except Exception as e:
            await interaction.channel.send(f"⚠️ Failed to notify handler: {e}")
        await interaction.guild.leave()
    

    @app_commands.command(name="lockdown", description="Enable lockdown mode (owner only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def lockdown(self, interaction: discord.Interaction):
        variables.IS_LOCKDOWN = True
        utils.save_flags()
        await interaction.response.send_message("# 🔒 Lockdown enabled: JSON writing and XP are now disabled.", ephemeral=True)


    @app_commands.command(name="unlockdown", description="Disable lockdown mode (owner only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def unlockdown(self, interaction: discord.Interaction):
        variables.IS_LOCKDOWN = False
        utils.save_flags()
        await interaction.response.send_message("# 🔓 Lockdown disabled: Normal operations resumed.", ephemeral=True)
    

    @app_commands.command(name="backuplog", description="Show the last N lines of the backup log (owner only)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(lines="Number of lines to show")
    async def backuplog(self, interaction: discord.Interaction, lines: int = 10):
        path = "backups/backup_log.txt"
        if not os.path.exists(path):
            await interaction.response.send_message("⚠️ No backup log found.", ephemeral=True)
            return
        with open(path, "r") as f:
            entries = f.readlines()
        last_lines = entries[-lines:]
        content = "```\n" + "".join(last_lines) + "\n```"
        await interaction.response.send_message(f"# 📋 Last {lines} backups:\n{content}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ownercommands(bot))
