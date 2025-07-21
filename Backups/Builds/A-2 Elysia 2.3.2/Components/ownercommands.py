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
                    await ctx.send(f"❌ Server **{server_name}** is already banned.")
                    return
                variables.banned_servers.append(guild.id)
                utils.save_banned_servers()
                await ctx.send(
                    f"✅ Server **{server_name}** has been banned. The bot will no longer work there."
                )
                return
        await ctx.send(f"❌ Server **{server_name}** not found.")

    @commands.command(name="UBServer")
    @commands.check(utils.is_owner)
    async def unban_server(self, ctx, *, server_name: str):
        for guild in self.bot.guilds:
            if guild.name.lower() == server_name.lower():
                if guild.id not in variables.banned_servers:
                    await ctx.send(f"❌ Server **{server_name}** is not banned.")
                    return
                variables.banned_servers.remove(guild.id)
                utils.save_banned_servers()
                await ctx.send(
                    f"✅ Server **{server_name}** has been unbanned. The bot will now work there."
                )
                return
        await ctx.send(f"❌ Server **{server_name}** not found.")

    @commands.command(name="MServer")
    @commands.check(utils.is_owner)
    async def manage_server(self, ctx, *, args: str):
        try:
            server_name, restriction_level = args.split(" / ")
        except ValueError:
            await ctx.send(
                "❌ Invalid format. Use `?MServer <Server Name> / <Restriction Level>`."
            )
            return

        restriction_levels = ["Free", "Limited", "Very Limited", "Absolute Restriction"]

        if restriction_level not in restriction_levels:
            await ctx.send(
                f"❌ Invalid restriction level. Choose from: {', '.join(restriction_levels)}."
            )
            return

        for guild in self.bot.guilds:
            if guild.name.lower() == server_name.lower():
                variables.server_restrictions[str(guild.id)] = restriction_level
                utils.save_server_restrictions()
                await ctx.send(
                    f"✅ Server **{server_name}** is now set to **{restriction_level}** mode."
                )
                return

        await ctx.send(f"❌ Server **{server_name}** not found.")

    @commands.command(name="update")
    @commands.check(utils.is_owner)
    async def update(self, ctx, *, args: str):
        """Update the bot's version and new features, then restart."""
        global current_status
        try:
            version, new_stuff = args.split(" / ")
        except ValueError:
            await ctx.send(
                "❌ Invalid format. Use `?update <version> / <new features>`."
            )
            return

        # Update the bot info
        variables.bot_info["version"] = version
        variables.bot_info["new_stuff"] = new_stuff
        utils.save_bot_info()

        # Set the status to "Updating..."
        current_status = discord.Game("Updating...")
        await self.bot.change_presence(
            status=discord.Status.dnd, activity=current_status
        )

        await ctx.send(
            f"✅ Bot updated to version **{version}** with new features: **{new_stuff}**."
        )
        await ctx.send("🔄 Restarting the bot...")

        utils.signal_update(f"New version: {version}\nNew stuff: {new_stuff}")

        # Restart the bot
        os.execv(sys.executable, [sys.executable] + sys.argv)

    
    @commands.command(name="restart")
    @commands.check(utils.is_owner)
    async def restart(self, ctx):
        """Restart the bot."""
        global current_status
        current_status = discord.Game("Restarting...")
        await self.bot.change_presence(status=discord.Status.dnd, activity=current_status)

        await ctx.send("🔄 Restarting the bot...")
        await self.bot.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    
    @commands.command(name="shutdown")
    @commands.check(utils.is_owner)
    async def shutdown(self, ctx):
        """Put the bot into sleep mode."""
        global is_sleeping
        is_sleeping = True  # Enable sleep mode

        # Set the bot's status to "Offline" and idle
        await self.bot.change_presence(
            status=discord.Status.idle, activity=discord.Game("[🔌⚠️] : Offline")
        )
        await ctx.send("🔌 The bot is now in sleep mode. Use `?start` to wake it up.")


    @commands.command(name="start")
    @commands.check(utils.is_owner)
    async def start(self, ctx):
        """Wake the bot up from sleep mode."""
        global is_sleeping
        if not is_sleeping:
            await ctx.send("✅ The bot is already active.")
            return

        is_sleeping = False  # Disable sleep mode

        # Restore the bot's normal status
        await self.bot.change_presence(
            status=discord.Status.online, activity=discord.Game("with Python 🐍")
        )
        await ctx.send("✅ The bot is now active and ready to use!")


    @commands.command(name="kys")
    @commands.check(utils.is_owner)
    async def kys(self, ctx):
        """commit die the bot."""
        await ctx.send("Commiting die...")
        await self.bot.close()
    

    @commands.command()
    @commands.check(utils.is_owner)
    async def givexp(self, ctx, member: discord.Member, xp: int):
        user_id = str(member.id)
        if user_id not in variables.user_data:
            variables.user_data[user_id] = {"xp": 0, "level": 1}

        variables.user_data[user_id]["xp"] += xp
        await ctx.send(f"✅ Gave {xp} XP to {member.mention}.")
        utils.save_user_data(variables.user_data)



    @commands.command()
    @commands.check(utils.is_owner)
    async def gainlvl(self, ctx, member: discord.Member):
        user_id = str(member.id)
        if user_id not in variables.user_data:
            variables.user_data[user_id] = {"xp": 0, "level": 1}

        variables.user_data[user_id]["level"] += 1
        await ctx.send(f"✅ {member.mention} has gained a level.")
        utils.save_user_data(variables.user_data)



    @commands.command()
    @commands.check(utils.is_owner)
    async def copychannel(self, ctx, channel: discord.TextChannel, *, text: str):
        try:
            await channel.send(f"{text}")
            await ctx.send(f"✅ Sent the message to {channel.mention}.")
        except discord.Forbidden:
            await ctx.send(f"❌ I cannot send messages to {channel.mention}.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    

    @commands.command()
    @commands.check(utils.is_owner)
    async def copy(self, ctx, *, text: str):
        await ctx.send(text)


    @commands.command()
    @commands.check(utils.is_owner)
    async def copydm(self, ctx, member: discord.Member, *, text: str):
        try:
            await member.send(text)
            await ctx.send(f"✅ Sent the message to {member.mention}'s DMs.")
        except discord.Forbidden:
            await ctx.send(f"❌ I cannot send DMs to {member.mention}. They might have DMs disabled.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")


    @commands.command(name="button")
    @commands.check(utils.is_owner)
    async def button(self, ctx):
        """Send a message with a button."""
        # Create a button
        button = Button(label="Click Me!", style=discord.ButtonStyle.green)

        # Define what happens when the button is clicked
        async def button_callback(interaction):
            await interaction.response.send_message(
                f"🎉 {interaction.user.mention} clicked the button!", ephemeral=True
            )

        button.callback = button_callback

        # Create a view and add the button to it
        view = View()
        view.add_item(button)

        # Send the message with the button
        await ctx.send("Here is a button for you:", view=view)

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
                "✅ The bot's status has been reset to its default rotating behavior."
            )
            return

        # Validate the status type
        valid_status_types = ["playing", "watching", "listening", "streaming"]
        if status_type.lower() not in valid_status_types:
            await ctx.send(
                f"❌ Invalid status type. Choose from: {', '.join(valid_status_types)}."
            )
            return

        # Set the custom status
        if activity is None:
            await ctx.send("❌ Please provide an activity name for the status.")
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
            f"✅ The bot's status has been updated to **{status_type.capitalize()} {activity}**."
        )


    @commands.command(name="reset")
    @commands.check(utils.is_owner)
    async def reset(self, ctx):
        """Reset all data and delete all songs with triple confirmation."""
        # First confirmation
        await ctx.send(
            "⚠️ **Do you wish to proceed?** This will delete ALL data and songs. Type `yes` to proceed or `no` to cancel."
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
                await ctx.send("❌ Reset canceled.")
                return
        except asyncio.TimeoutError:
            await ctx.send("⏰ You took too long to respond. Reset canceled.")
            return

        # Second confirmation
        await ctx.send(
            "⚠️ **Are you ABSOLUTELY sure?** This will delete EVERYTHING. Type `yes` to proceed or `no` to cancel."
        )

        try:
            response = await self.bot.wait_for("message", check=check, timeout=30.0)
            if response.content.lower() == "no":
                await ctx.send("❌ Reset canceled.")
                return
        except asyncio.TimeoutError:
            await ctx.send("⏰ You took too long to respond. Reset canceled.")
            return

        # Final confirmation
        await ctx.send(
            "⚠️ **ARE YOU SURE?** This is your FINAL WARNING. Type `yes` to proceed or `no` to cancel."
        )

        try:
            response = await self.bot.wait_for("message", check=check, timeout=30.0)
            if response.content.lower() == "no":
                await ctx.send("❌ Reset canceled.")
                return
        except asyncio.TimeoutError:
            await ctx.send("⏰ You took too long to respond. Reset canceled.")
            return

        # Perform the reset
        try:
            # Delete all JSON files
            data_files = [
                "data/user_data.json",
                "data/easter.json",
                "data/trophies.json",
                "data/warnings.json",
                "data/bank.json",
                "data/server_restrictions.json",
                "data/banned_servers.json",
            ]
            for file in data_files:
                if os.path.exists(file):
                    os.remove(file)
                    await ctx.send(f"🗑️ Deleted `{file}`.")

            # Delete all songs in the music folder
            music_folder = "music"
            if os.path.exists(music_folder):
                for file in os.listdir(music_folder):
                    file_path = os.path.join(music_folder, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                await ctx.send("🗑️ Deleted all songs in the `music` folder.")

            await ctx.send("✅ **Reset complete. All data and songs have been deleted.**")

            # Restart the bot
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            await ctx.send(f"❌ An error occurred during the reset: {e}")

    @commands.command(name="setlogging")
    @commands.has_permissions(administrator=True)
    async def setlogging(self, ctx, action: typing.Optional[str] = None):
        """Enable or disable logging for the server."""
        if action not in ["enable", "disable"]:
            await ctx.send("❓ **Usage:** `?setlogging <enable|disable>`")
            return

        guild_id = str(ctx.guild.id)
        logging_config = utils.load_logging_config()

        if action == "enable":
            logging_config[guild_id] = True
            utils.save_logging_config(logging_config)
            await ctx.send("✅ Logging has been **enabled** for this server.")
        elif action == "disable":
            logging_config[guild_id] = False
            utils.save_logging_config(logging_config)
            await ctx.send("✅ Logging has been **disabled** for this server.")

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
            await ctx.send("❌ Only the 'update' action is supported for now.")
            return

        # Parse the time string :dd:hh:mm:ss
        if not time_str or not time_str.startswith(":"):
            await ctx.send("❌ Please provide a time in the format `:dd:hh:mm:ss`.")
            return

        try:
            _, dd, hh, mm, ss = time_str.split(":")
            delay_seconds = int(dd) * 86400 + int(hh) * 3600 + int(mm) * 60 + int(ss)
        except Exception:
            await ctx.send(
                "❌ Invalid time format. Use `:dd:hh:mm:ss` (e.g., `:00:01:30:00` for 1 hour 30 minutes)."
            )
            return
        if not version:
            await ctx.send("❌ Please provide a number or something for the version")
            return

        if not changelog:
            await ctx.send("❌ Please provide a changelog in quotes.")
            return

        # Confirm scheduling
        await ctx.send(
            f"🕒 Scheduled a bot update in {dd}d {hh}h {mm}m {ss}s.\nChangelog: {changelog}"
        )

        async def scheduled_update():
            await asyncio.sleep(delay_seconds)
            # Update bot_info and restart (reuse your update logic)
            variables.bot_info["new_stuff"] = changelog
            variables.bot_info["version"] = version
            utils.save_bot_info()
            await ctx.send(f"🔄 Performing scheduled update!\n**Changelog:** {changelog}")
            os.execv(sys.executable, [sys.executable] + sys.argv)

        self.bot.loop.create_task(scheduled_update())


    @commands.command(name="selfkick")
    @commands.check(utils.is_owner)
    async def selfkick(self, ctx):
        """Bot leaves the server when this command is used."""
        await ctx.send("👋 Leaving the server!")
        await ctx.guild.leave()

async def setup(bot):
    await bot.add_cog(Ownercommands(bot))
