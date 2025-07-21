# --------------------- IMPORTS --------------------
from Ediscord import variables, utils
from discord.ext import commands
import os
import discord
from discord.ext.commands import CommandOnCooldown
from discord.ext.commands import CooldownMapping
from discord.ext.commands import cooldown
from discord.ext.commands import BucketType
import sys
from PIL import Image, ImageDraw, ImageFont
import logging
from discord.ui import Button, View
import asyncio
import typing

# --------------------- OWNER COMMANDS --------------------
print("✅ - Owner commands loaded.")
class Ownercommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="BServer")
    @commands.check(utils.is_owner)
    async def ban_server(self, ctx, *, server_name: str):
        for guild in self.bot.guilds:
            if guild.name.lower() == server_name.lower():
                if guild.id in variables.banned_servers:
                    await ctx.send(f"# ❌ Server **{server_name}** is already banned!\nMaybe just maybe.. unban them??")
                    return
                variables.banned_servers.append(guild.id)
                utils.save_banned_servers()
                await ctx.send(
                    f"# ✅ Server **{server_name}** has been banned.\nThe bot will no longer work there unless the removal of this ban."
                )
                return
        await ctx.send(f"# ❓ Server **{server_name}** not found.\nYou sure you entered the right name?")

    @commands.command(name="UBServer")
    @commands.check(utils.is_owner)
    async def unban_server(self, ctx, *, server_name: str):
        for guild in self.bot.guilds:
            if guild.name.lower() == server_name.lower():
                if guild.id not in variables.banned_servers:
                    await ctx.send(f"# ❌ Server **{server_name}** is not banned!\n{utils.little_text()}")
                    return
                variables.banned_servers.remove(guild.id)
                utils.save_banned_servers()
                await ctx.send(
                    f"# ✅ Server **{server_name}** has been un-banned.\nThe bot will now work there unless the reapplication of this ban."
                )
                return
        await ctx.send(f"# ❓ Server **{server_name}** not found.\nYou sure you entered the right name?")

    @commands.command(name="MServer")
    @commands.check(utils.is_owner)
    async def manage_server(self, ctx, *, args: str):
        try:
            server_name, restriction_level = args.split(" / ")
        except ValueError:
            await ctx.send(
                "# ❌ Invalid format\nUse `?MServer <Server Name> / <Restriction Level>`."
            )
            return

        restriction_levels = ["Free", "Limited", "Very Limited", "Absolute Restriction"]

        if restriction_level not in restriction_levels:
            await ctx.send(
                f"# ❌ Invalid restriction level\nChoose from: {', '.join(restriction_levels)}."
            )
            return

        for guild in self.bot.guilds:
            if guild.name.lower() == server_name.lower():
                variables.server_restrictions[str(guild.id)] = restriction_level
                utils.save_server_restrictions()
                await ctx.send(
                    f"# # ✅ Server **{server_name}**\nis now set to **{restriction_level}** mode."
                )
                return

        await ctx.send(f"# ❓ Server **{server_name}** not found.\nYou sure you entered the right name?")

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
        except ValueError:
            await ctx.send(
                "# ❌ Invalid format.\nUse `?update <version> / <new features>` or `?update insider <version> / <new features>`."
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
            utils.signal_update(f"main|New version: {version}\nNew stuff: {new_stuff}")

        # Restart the bot
        os.execv(sys.executable, [sys.executable] + sys.argv)

    
    @commands.command(name="restart")
    @commands.check(utils.is_owner)
    async def restart(self, ctx):
        """Restart the bot."""
        global current_status
        current_status = discord.Game("Restarting...")
        await self.bot.change_presence(status=discord.Status.dnd, activity=current_status)

        await ctx.send("# ** ---  🔄 Restarting the bot...  ---**")
        await self.bot.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @commands.command(name="shutdown")
    @commands.check(utils.is_owner)
    async def shutdown(self, ctx):
        """Shutdown the bot entirely."""
        await ctx.send("# Goobye!\nThe bot will now shut down.\n-# I hope i get restarted soon :(...")
        await self.bot.close()

    @commands.command()
    @commands.check(utils.is_owner)
    async def copychannel(self, ctx, channel: discord.TextChannel, *, text: str):
        try:
            await channel.send(f"{text}")
            await ctx.send(f"# ✅ Sent the message to {channel.mention}.\n-# Sent the following message to {channel.mention}: {text}")
        except discord.Forbidden:
            await ctx.send(f"# ❌ I cannot send messages to {channel.mention}.\nMaybe it's a role issue?")
        except Exception as e:
            await ctx.send(f"# ❌ An error occurred: {e}\n{utils.little_text()}")
    
    @commands.command()
    @commands.check(utils.is_owner)
    async def copy(self, ctx, *, text: str):
        await ctx.send(text)

    @commands.command()
    @commands.check(utils.is_owner)
    async def copydm(self, ctx, member: discord.Member, *, text: str):
        try:
            await member.send(text)
            await ctx.send(f"✅ Sent the message to {member.mention}'s DMs.\n-# Sent the following message to {member}'s DMs: {text}")
        except discord.Forbidden:
            await ctx.send(f"# ❌ I cannot send DMs to {member.mention}.\nThey may have their DMs disabled.")
        except Exception as e:
            await ctx.send(f"# ❌ An error occurred: {e}\n{utils.little_text()}")

    @commands.command(name="modify_status")
    @commands.check(utils.is_owner)
    async def modify_status(self, ctx, status_type: str, *, activity: typing.Optional[str] = None):
        """Modify the bot's status and activity."""
        global custom_status
        custom_status = None  # Ensure custom_status is always defined

        if status_type.lower() == "default":
            # Reset to default rotating statuses
            custom_status = None
            await ctx.send(
                f"# ✅ The bot's status has been reset to its default rotating behavior.\n{utils.little_text()}"
            )
            return

        # Validate the status type
        valid_status_types = ["playing", "watching", "listening", "streaming"]
        if status_type.lower() not in valid_status_types:
            await ctx.send(
                f"# ❌ Invalid status type.\nChoose from: {', '.join(valid_status_types)}."
            )
            return

        # Set the custom status
        if activity is None:
            await ctx.send("# ❌ Please provide an activity name for the status.\nSomething like: 'Gaming is fun!'")
            return

        if status_type.lower() == "playing":
            custom_status = discord.Game(activity)
        elif status_type.lower() == "watching":
            custom_status = discord.Activity(
                type=discord.ActivityType.watching, name=activity
            )
        elif status_type.lower() == "listening":
            custom_status = discord.Activity(
                type=discord.ActivityType.listening, name=activity
            )
        elif status_type.lower() == "streaming":
            custom_status = discord.Streaming(
                name=activity, url="https://www.twitch.tv/your_channel"
            )  # Replace with your Twitch URL

        await self.bot.change_presence(status=discord.Status.online, activity=custom_status)
        await ctx.send(
            f"# ✅ The bot's status has been updated!\nHere's the new status: **{status_type.capitalize()} {activity}**."
        )


    @commands.command(name="reset")
    @commands.check(utils.is_owner)
    async def reset(self, ctx):
        """Reset all data and delete all songs with triple confirmation."""
        # First confirmation
        await ctx.send(
            "# ⚠️ **Do you wish to proceed?**\nThis will delete ALL data and songs.\n\nType `yes` to proceed or `no` to cancel."
        )

        def check(m):
            return (
                m.author == ctx.author
                and m.channel == ctx.channel
                and m.content.lower() in ["yes", "no"]
            )

        try:
            response = await self.bot.wait_for("message", check=check, timeout=30.0)
            if response.content.lower() == "no":
                await ctx.send("# ❌ Reset canceled.")
                return
        except asyncio.TimeoutError:
            await ctx.send("# ⏰ You took too long to respond.\nReset canceled.")
            return

        # Second confirmation
        await ctx.send(
            "# ⚠️ **Are you ABSOLUTELY sure?**\nThis will delete EVERYTHING.\n\nType `yes` to proceed or `no` to cancel."
        )

        try:
            response = await self.bot.wait_for("message", check=check, timeout=30.0)
            if response.content.lower() == "no":
                await ctx.send("# ❌ Reset canceled.")
                return
        except asyncio.TimeoutError:
            await ctx.send("# ⏰ You took too long to respond.\nReset canceled.")
            return

        # Final confirmation
        await ctx.send(
            "# ⚠️ **ARE YOU SURE???**\nThis is your **FINAL WARNING**.\n\nType `yes` to proceed or `no` to cancel."
        )

        try:
            response = await self.bot.wait_for("message", check=check, timeout=30.0)
            if response.content.lower() == "no":
                await ctx.send("# ❌ Reset canceled.")
                return
        except asyncio.TimeoutError:
            await ctx.send("# ⏰ You took too long to respond.\nReset canceled.")
            return

        # Perform the reset
        try:
            # Delete all JSON files
            data_files = [
                "data/achievements.json",
                "data/akari_points.json",
                "data/bank.json",
                "data/insider_servers.json",
                "data/bot_info.json",
                "data/inventory.json",
                "data/limitations.json",
                "data/logging_config.json",
                "data/prefixes.json"
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
                    await ctx.send(f"🗑️ Deleted `{file}`.")

            # Delete all songs in the music folder
            folder = "music"
            if os.path.exists(folder):
                for file in os.listdir(folder):
                    file_path = os.path.join(folder, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                await ctx.send("🗑️ Deleted all songs in the `music` folder.")
            
            # Delete all songs in the backups folder
            folder = "backups"
            if os.path.exists(folder):
                for file in os.listdir(folder):
                    file_path = os.path.join(folder, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                await ctx.send("🗑️ Deleted all backups in the `backups` folder.")
            
            # Delete all songs in the backups folder
            folder = "assets"
            if os.path.exists(folder):
                for file in os.listdir(folder):
                    file_path = os.path.join(folder, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                await ctx.send("🗑️ Deleted all assets in the `assets` folder.")

            # Delete all songs in the backups folder
            folder = "Ediscord"
            if os.path.exists(folder):
                for file in os.listdir(folder):
                    file_path = os.path.join(folder, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                await ctx.send("🗑️ Deleted the module `Ediscord` folder.")

            await ctx.send("# ✅ **Reset complete.\nEverything has been deleted.\n-# Goodbye.**")

            # Restart the bot
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            await ctx.send(f"# ❌ An error occurred during the reset:\n{e}")

    @commands.command(name="setlogging")
    @commands.check(utils.is_owner)
    async def setlogging(self, ctx, action: typing.Optional[str] = None):
        """Enable or disable logging for the server."""
        if action not in ["enable", "disable"]:
            await ctx.send("# ❓ **Usage:**\n`?setlogging <enable|disable>`")
            return

        guild_id = str(ctx.guild.id)
        logging_config = utils.load_logging_config()

        if action == "enable":
            logging_config[guild_id] = True
            utils.save_logging_config(logging_config)
            await ctx.send("# ✅ Logging has been **enabled** for this server.")
        elif action == "disable":
            logging_config[guild_id] = False
            utils.save_logging_config(logging_config)
            await ctx.send("# ✅ Logging has been **disabled** for this server.")

    @commands.command(name="program")
    @commands.check(utils.is_owner)
    async def program(
        self,
        ctx,
        action: str,
        time_str: typing.Optional[str] = None,
        *,
        version: typing.Optional[int]= None,
        changelog: typing.Optional[str] = None
    ):
        """
        Schedule a bot action (mainly update) after a delay.
        Usage: ?program update :dd:hh:mm:ss "changelog here"
        """
        if action.lower() != "update":
            await ctx.send("# ❌ Only the 'update' action is supported for now.\n-# Sorry..")
            return

        # Parse the time string :dd:hh:mm:ss
        if not time_str or not time_str.startswith(":"):
            await ctx.send("# ❌ Please provide a time.\nwith the following format: `:dd:hh:mm:ss`.")
            return

        try:
            _, dd, hh, mm, ss = time_str.split(":")
            delay_seconds = int(dd) * 86400 + int(hh) * 3600 + int(mm) * 60 + int(ss)
        except Exception:
            await ctx.send(
                "# ❌ Incompatiple time format.\nUse `:dd:hh:mm:ss` (e.g., `:00:01:30:00` for 1 hour 30 minutes)."
            )
            return
        if not version:
            await ctx.send("# ❌ Please provide a number or something for the version")
            return

        if not changelog:
            await ctx.send("# ❌ Please provide a changelog in quotes.")
            return

        # Confirm scheduling
        await ctx.send(
            f"# 🕒 Scheduled a bot update in {dd}d {hh}h {mm}m {ss}s.\nChangelog: {changelog}"
        )

        async def scheduled_update():
            await asyncio.sleep(delay_seconds)
            # Update bot_info and restart (reuse your update logic)
            variables.bot_info["new_stuff"] = changelog
            variables.bot_info["version"] = version
            utils.save_bot_info()
            await ctx.send(f"# 🔄 Performing scheduled update!\n**Changelog:** {changelog}")
            os.execv(sys.executable, [sys.executable] + sys.argv)

        self.bot.loop.create_task(scheduled_update())


    @commands.command(name="selfkick")
    @commands.check(utils.is_owner)
    async def selfkick(self, ctx):
        """Bot leaves the server when this command is used."""
        await ctx.send("# 👋 Leaving the server!\nSeems like my owner didn't like your server or something.")
        await ctx.guild.leave()
    
    @commands.command(name="lockdown")
    @commands.is_owner()
    async def lockdown(self, ctx):
        variables.IS_LOCKDOWN = True
        utils.save_flags()
        await ctx.send("# 🔒 Lockdown enabled: JSON writing and XP are now disabled.")

    @commands.command(name="unlockdown")
    @commands.is_owner()
    async def unlockdown(self, ctx):
        variables.IS_LOCKDOWN = False
        utils.save_flags()
        await ctx.send("# 🔓 Lockdown disabled: Normal operations resumed.")
    
    @commands.command(name="backuplog")
    @commands.is_owner()
    async def backuplog(self, ctx, lines: int = 10):
        path = "backups/backup_log.txt"
        if not os.path.exists(path):
            await ctx.send("⚠️ No backup log found.")
            return

        with open(path, "r") as f:
            entries = f.readlines()

        last_lines = entries[-lines:]
        content = "```\n" + "".join(last_lines) + "\n```"
        await ctx.send(f"# 📋 Last {lines} backups:\n{content}")

async def setup(bot):
    await bot.add_cog(Ownercommands(bot))
