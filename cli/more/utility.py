# --------------------- IMPORTS --------------------
import discord
import json
from discord.ext import commands, tasks
from Ediscord import utils, variables
import asyncio
import logging
import unicodedata
import requests
from discord import app_commands
import os
from yt_dlp import YoutubeDL
from discord import FFmpegPCMAudio
from googletrans import Translator
import typing
import time
import re
import random
from typing import Optional

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

    # Normalize fancy unicode fonts → ascii
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))

    # Remove emojis
    text = EMOJI_REGEX.sub("", text)

    # Replace separators with spaces
    text = SEPARATORS_REGEX.sub(" ", text)

    # Lowercase + collapse spaces
    text = re.sub(r"\s+", " ", text.lower()).strip()

    return text

def score_channel(channel: discord.TextChannel) -> int:
    score = 0

    name = normalize_text(channel.name)
    topic = normalize_text(channel.topic or "")

    combined = f"{name} {topic}"

    # Strong priority: official Discord announcement channels
    if channel.type == discord.ChannelType.news:
        score += 100

    for keyword in ANNOUNCEMENT_KEYWORDS:
        if keyword in name:
            score += 10
        if keyword in topic:
            score += 6

    # Bonus for plural or obvious intent
    if "announce" in combined:
        score += 5

    # Penalize generic chat channels
    if "general" in name or "chat" in name:
        score -= 5

    return score

class GiveawayView(discord.ui.View):
    def __init__(self, message_id, timeout=3600):
        super().__init__(timeout=timeout)
        self.message_id = message_id
        self.entries = set()

    @discord.ui.button(label="Enter Giveaway", style=discord.ButtonStyle.green)
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.entries.add(interaction.user.id)
        await interaction.response.send_message("🎉 You have entered the giveaway!", ephemeral=True)


# --------------------- UTILITY COMMANDS --------------------
print("✅ - Utility loaded.")
class Utility(commands.Cog):
    @app_commands.command(
        name="migrate",
        description="Survey: Migrate your user data to a specific server."
    )
    async def migratedata(self, interaction: discord.Interaction):
        """
        Survey command for users to migrate their data to a specific server.
        Reads from user_data_old.json and writes to user_data.json in the new per-server structure.
        Only migrates if not already migrated. Users who do not migrate will lose their data.
        """
        user_id = str(interaction.user.id)
        # Load old data (source) and new data (destination)
        try:
            with open("data/user_data.json", "r", encoding="utf-8") as f:
                old_data = json.load(f)
        except Exception as e:
            await interaction.response.send_message(f"❌ Could not load old user data for migration. Error: {e}", ephemeral=True)
            return
        try:
            with open("data/user_data_new.json", "r", encoding="utf-8") as f:
                new_data = json.load(f)
        except Exception as e:
            await interaction.response.send_message(f"❌ Could not load new user data for migration. Error: {e}", ephemeral=True)
            return

        guilds = [guild for guild in self.bot.guilds if interaction.user in guild.members]
        if not guilds:
            await interaction.response.send_message("You are not a member of any guilds. that's quite a problem!", ephemeral=True)
            return

        # List guilds for the user to choose
        guild_list = "\n".join([f"{i+1}. {guild.name} (ID: {guild.id})" for i, guild in enumerate(guilds)])
        await interaction.response.send_message(f"Please reply with the number of the server you want to migrate your data to:\n{guild_list}")

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel and m.content.isdigit() and 1 <= int(m.content) <= len(guilds)

        try:
            reply = await self.bot.wait_for("message", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Migration cancelled: no response.", ephemeral=True)
            return

        chosen_guild = guilds[int(reply.content) - 1]
        guild_id = str(chosen_guild.id)

        # Only migrate if user exists in old data and not already migrated in new data
        if user_id in old_data and (user_id not in new_data or guild_id not in new_data[user_id]):
            # Move all top-level user data to the chosen server
            user_entry = old_data[user_id]
            server_data = {
                "xp": user_entry.get("xp", 0),
                "level": user_entry.get("level", 1),
                "coins": user_entry.get("coins", 0),
                "gems": user_entry.get("gems", 0),
                "balance": user_entry.get("balance", 0),
                "warnings": user_entry.get("warnings", []),
                "messages": user_entry.get("messages", []),
                "verified": user_entry.get("verified", False),
                "censored_count": user_entry.get("censored_count", 0),
                "strikes": user_entry.get("strikes", 0),
                "crates_opened": user_entry.get("crates_opened", 0),
                "keys": user_entry.get("keys", 0)
            }
            # Preserve other top-level fields
            for k, v in user_entry.items():
                if k not in server_data:
                    server_data[k] = v
            # Insert into new structure
            if user_id not in new_data:
                new_data[user_id] = {}
            new_data[user_id][guild_id] = server_data
            # Save to user_data.json (destination)
            with open("data/user_data.json", "w", encoding="utf-8") as f:
                json.dump(new_data, f, indent=4)
            await interaction.followup.send(f"Your data has been migrated to {chosen_guild.name}.", ephemeral=True)
        else:
            await interaction.followup.send("Migration not needed or already completed.", ephemeral=True)
            
    @commands.Cog.listener()
    async def on_ready(self):
        # In your on_ready event or at startup:
        if not hasattr(self.bot, "launch_time"):
            self.bot.launch_time = time.time()
        if not hasattr(self.bot, "version"):
            self.bot.version = variables.bot_info["version"]
        if not hasattr(self.bot, "total_commands"):
            self.bot.total_commands = variables.total_commands
        print(f"✅ Bot is ready! Logged in as {self.bot.user}")
        print(f"Connected to {len(self.bot.guilds)} guild(s).")
        logging.info(f"Logged in as {self.bot.user}")

        # Get the AssetManager cog instance
        self.assets = self.bot.get_cog("AssetManager")
        if self.assets:
            logging.info("AssetManager cog found. Initializing guild assets...")
            for guild in self.bot.guilds:
                await self.assets.initialize_guild_assets(guild)
            logging.info("All existing guild assets initialized.")
        else:
            logging.error("AssetManager cog not found. Asset initialization skipped.")

        # Bulk assign level roles to all members
        logging.info("Starting bulk level role assignment...")
        for guild in self.bot.guilds:
            await self.assign_level_roles_bulk(guild)
        logging.info("Bulk level role assignment completed for all guilds.")

    def __init__(self, bot):
        self.bot = bot
        # Per-guild mapping: guild_id (str) -> last bumper id (string) or role id (string)
        self.last_bumper = {}
        # Load persisted bump data from server settings (if present)
        try:
            settings = utils.load_server_settings()
            for gid, gsettings in settings.items():
                lb = gsettings.get("last_bumper")
                if lb is not None:
                    self.last_bumper[str(gid)] = str(lb)
        except Exception:
            # If loading fails, continue with empty mapping
            pass
        self.bump_reminder_task.start()

    
    @tasks.loop(seconds=5)
    async def assign_level_roles_bulk(self, guild):
        """Assigns level roles to all members in a guild based on their current level.
        Both default level roles (if enabled) and custom level role mappings are handled."""
        try:
            # Load user data once for efficiency
            user_data = utils.load_user_data()
            # Load server settings to check if level roles are disabled
            settings = utils.load_server_settings()
            guild_settings = settings.get(str(guild.id), {})
            # Get custom level role mappings
            level_roles = utils.get_guild_level_roles(guild.id)
            # Whether default level roles are disabled
            level_roles_disabled = guild_settings.get("disable_level_roles", False)
            
            processed = 0
            updated = 0

            # If using custom roles, create any missing roles from the config first
            if level_roles:
                for req_level, role_name in level_roles.items():
                    role = discord.utils.get(guild.roles, name=role_name)
                    if not role:
                        try:
                            role = await guild.create_role(name=role_name, reason="Missing custom level role")
                            logging.info(f"Created missing custom level role {role_name} in {guild.name}")
                        except Exception as e:
                            logging.warning(f"Failed to create custom level role {role_name}: {e}")
            # If using default roles, check predefined thresholds
            elif not level_roles_disabled:
                default_thresholds = [5, 10, 15, 20, 25, 30, 40, 50, 75, 100]
                for threshold in default_thresholds:
                    role_name = f"Level {threshold}"
                    role = discord.utils.get(guild.roles, name=role_name)
                    if not role:
                        try:
                            role = await guild.create_role(name=role_name, reason="Default level role")
                            logging.info(f"Created default level role {role_name} in {guild.name}")
                        except Exception as e:
                            logging.warning(f"Failed to create default level role {role_name}: {e}")
            
            # Now assign roles to members
            for member in guild.members:
                if member.bot:
                    continue
                    
                # Get member's level
                member_data = user_data.get(str(member.id), {})
                level = member_data.get("level", 1)
                
                processed += 1
                
                # Handle custom level role mappings first
                if level_roles:
                    for req_level, role_name in level_roles.items():
                        if level >= int(req_level):
                            role = discord.utils.get(guild.roles, name=role_name)
                            if role and role not in member.roles:
                                try:
                                    await member.add_roles(role, reason=f"Level {level} role")
                                    updated += 1
                                    logging.info(f"Assigned custom level role {role.name} to {member.name} in {guild.name}")
                                except Exception as e:
                                    logging.warning(f"Failed to assign custom level role {role.name} to {member.name}: {e}")
                
                # Handle default level roles unless disabled
                elif not level_roles_disabled:
                    # Find the highest threshold the member has reached
                    threshold = next((t for t in reversed(default_thresholds) if level >= t), None)
                    if threshold:
                        role = discord.utils.get(guild.roles, name=f"Level {threshold}")
                        if role and role not in member.roles:
                            try:
                                await member.add_roles(role, reason="Default level role")
                                updated += 1
                                logging.info(f"Assigned default level role {role.name} to {member.name} in {guild.name}")
                            except Exception as e:
                                logging.warning(f"Failed to assign default level role {role.name} to {member.name}: {e}")
            
            logging.info(f"Bulk level role assignment complete for {guild.name}: {updated}/{processed} members updated")
            
        except Exception as e:
            logging.error(f"Error during bulk level role assignment for {guild.name}: {e}")

    @app_commands.command(
        name="setbumpchannel",
        description="Set the channel where bump reminders are sent."
    )
    @utils.admin_or_owner()
    async def set_bump_channel(self, interaction: discord.Interaction, channel: typing.Optional[discord.TextChannel] = None):
        """Set the channel where bump reminders are sent. If no channel provided, uses current channel."""
        channel = channel or interaction.channel
        # Persist bump channel to server settings per-guild
        settings = utils.load_server_settings()
        guild_settings = settings.get(str(interaction.guild.id), {})
        guild_settings["bump_channel_id"] = channel.id
        settings[str(interaction.guild.id)] = guild_settings
        utils.save_server_settings(settings)
        await interaction.response.send_message(f"✅ Bump reminder channel set to {channel.mention}.")

    def set_last_bumper(self, guild_id, bumper_id):
        """Set last bumper for a specific guild and persist it.

        bumper_id should be a string or int representing a user id or role id.
        """
        try:
            gid = str(guild_id)
            # normalize to string for storage
            self.last_bumper[gid] = str(bumper_id)
            settings = utils.load_server_settings()
            guild_settings = settings.get(gid, {})
            guild_settings["last_bumper"] = str(bumper_id)
            settings[gid] = guild_settings
            utils.save_server_settings(settings)
        except Exception:
            # Swallow errors to avoid crashing event handlers
            pass
        
    @tasks.loop(hours=2)
    async def bump_reminder_task(self):
        await self.bot.wait_until_ready()
        # Loop through all guilds and send reminders according to per-guild settings
        try:
            settings = utils.load_server_settings()
        except Exception:
            settings = {}

        for guild in list(self.bot.guilds):
            try:
                guild_settings = settings.get(str(guild.id), {})
                bump_channel_id = guild_settings.get("bump_channel_id")
                if not bump_channel_id:
                    continue
                channel = self.bot.get_channel(int(bump_channel_id))
                if channel is None:
                    continue

                # Determine last bumper: prefer in-memory mapping, then persisted value
                last = self.last_bumper.get(str(guild.id)) or guild_settings.get("last_bumper")

                if not last:
                    # Default: ping a role named "Bump Reminder" if present
                    role = discord.utils.get(guild.roles, name="Bump Reminder")
                    if role and channel.permissions_for(guild.me).send_messages:
                        await channel.send(f"{role.mention} Please bump the server using `/bump`!")
                    continue

                # last is stored as a string of digits (user id or role id)
                try:
                    last_id = int(str(last))
                except Exception:
                    # invalid id stored; skip
                    continue

                # Try to mention a member first
                member = guild.get_member(last_id)
                if member and channel.permissions_for(guild.me).send_messages:
                    await channel.send(f"{member.mention} Please bump the server again using `/bump`!")
                    continue

                # Fallback: try role by id
                role = discord.utils.get(guild.roles, id=last_id)
                if role and channel.permissions_for(guild.me).send_messages:
                    await channel.send(f"{role.mention} Please bump the server using `/bump`!")
            except Exception:
                # Guard each guild so one failure doesn't stop the loop
                continue
    
    @app_commands.command(
        name="colorrole",
        description="Assigns or resets a shared color role."
    )
    async def colorrole(self, interaction: discord.Interaction, color_input: str):
        """Assigns or resets a shared color role."""
        guild = interaction.guild
        member = interaction.user
        

        # Reset command
        if color_input.lower() == "reset":
            removed = False
            for role in member.roles:
                if role.name.startswith("Color: "):
                    try:
                        await member.remove_roles(role)
                        removed = True
                    except discord.Forbidden:
                        return await interaction.response.send_message("# ❌ I don't have permission to remove your old color role. Please check my role permissions.")
                    except Exception as e:
                        return await interaction.response.send_message(f"# ❌ Failed to remove old color role: {e}")
            if removed:
                await interaction.response.send_message("# 🗑️ Your color role has been removed.\n-# Are you gonna choose another color? maybe?..")
            else:
                await interaction.response.send_message("# ❌ You don’t have a color role.\n-# Sure you spelt it right? Try again!")
            return

        # Get color
        color_input = color_input.lower().replace(" ", "")
        if color_input in variables.COLOR_MAP:
            hex_value = variables.COLOR_MAP[color_input]
            role_name = f"Color: {color_input.capitalize()}"
        else:
            match = re.match(variables.HEX_REGEX, color_input)
            if match:
                hex_value = int(match.group(1), 16)
                role_name = f"Color: #{match.group(1).upper()}"
            else:
                return await interaction.response.send_message(f"# ❌ Invalid color.\nUse a name like `red` or a HEX code like `#00ffcc`.\n-# {utils.little_error_variant()}")

        for role in member.roles:
            if role.name.startswith("Color: "):
                try:
                    await member.remove_roles(role)
                except discord.Forbidden:
                    return await interaction.response.send_message("# ❌ I don't have permission to remove old color roles. Please check my role permissions.")
                except Exception as e:
                    return await interaction.response.send_message(f"# ❌ Failed to remove old color role: {e}")

        # Look for existing role
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            # Create role if it doesn't exist
            bot_member = guild.get_member(self.bot.user.id)
            target_position = 1 
            sorted_roles_desc = sorted(guild.roles, key=lambda r: r.position, reverse=True)
            effective_ceiling_position = 0 # Default to @everyone position
            for r in sorted_roles_desc:
                if not r.permissions.administrator and not r.managed:
                    effective_ceiling_position = r.position 
                    break

            new_role_position = effective_ceiling_position + 1
            if bot_member and bot_member.top_role:
                new_role_position = min(new_role_position, bot_member.top_role.position - 1)
            
            new_role_position = max(1, new_role_position)
            
            try:
                role = await guild.create_role(name=role_name, colour=discord.Colour(hex_value), reason="New shared color role")
                await role.edit(position=new_role_position)
            except discord.Forbidden:
                return await interaction.response.send_message("# ❌ I don't have permission to manage roles (create/position). Please check my role permissions.")
            except Exception as e:
                return await interaction.response.send_message(f"# ❌ Failed to create/assign role: {e}")

        # Assign role
        try:
            await member.add_roles(role)
            await interaction.response.send_message(f"# ✅ You now have the `{role_name}` role!\n-# {utils.little_text()}")
        except discord.Forbidden:
            await interaction.response.send_message("# ❌ I don't have permission to assign roles. Please check my role permissions.")
        except Exception as e:
            await interaction.response.send_message(f"# ❌ Failed to assign role: {e}")
    
    @app_commands.command(
        name="setwelcome",
        description="Set a custom welcome message for this server."
    )
    @utils.admin_or_owner()
    async def set_welcome_message(self, interaction: discord.Interaction, message: str):
        """Set a custom welcome message for this server."""
        utils.set_guild_welcome_message(interaction.guild.id, message)
        await interaction.response.send_message("# ✅ Custom welcome message set!")

    @app_commands.command(
        name="setgoodbye",
        description="Set a custom goodbye message for this server."
    )
    @utils.admin_or_owner()
    async def set_goodbye_message(self, interaction: discord.Interaction, message: str):
        """Set a custom goodbye message for this server."""
        utils.set_guild_goodbye_message(interaction.guild.id, message)
        await interaction.response.send_message("# ✅ Custom goodbye message set!")

    @app_commands.command(
        name="color",
        description="Display the exact color based on a name or hex code."
    )
    async def color(self, interaction: discord.Interaction, color_input: str):
        """Display the exact color based on a name or hex code."""
        try:
            # Use a predefined dictionary of color names and their hex values
            color_names = {
                "red": "#FF0000",
                "green": "#00FF00",
                "blue": "#0000FF",
                "yellow": "#FFFF00",
                "orange": "#FFA500",
                "purple": "#800080",
                "pink": "#FFC0CB",
                "black": "#000000",
                "white": "#FFFFFF",
                "gray": "#808080",
                "cyan": "#00FFFF",
                "magenta": "#FF00FF",
                "brown": "#A52A2A",
            }
            # Check if the input is a hex code
            if color_input.startswith("#"):
                # Convert the hex code to an integer and create a Discord color
                color_value = discord.Color(int(color_input.lstrip("#"), 16))
            else:
                if color_input.lower() not in color_names:
                    await interaction.response.send_message(f"# ❌ Invalid color name or hex code.\n-# {utils.little_error_variant()}")
                    return
                color_value = discord.Color(
                    int(color_names[color_input.lower()].lstrip("#"), 16)
                )

            # Create an embed to display the color
            embed = discord.Embed(
                title="Color Preview",
                description=f"Here is the color for `{color_input}`.",
                color=color_value,
            )
            embed.add_field(
                name="Hex Code",
                value=(
                    color_input
                    if color_input.startswith("#")
                    else color_names[color_input.lower()]
                ),
            )
            embed.set_thumbnail(
                url=f"https://singlecolorimage.com/get/{color_value.value:06x}/400x400"
            )
            await interaction.response.send_message(embed=embed)

        except ValueError:
            await interaction.response.send_message(
                f"# ❌ Invalid color input.\nPlease provide a valid color name or hex code (e.g., `red` or `#FF0000`).\n-# {utils.little_error_variant()}"
            )
        
    @app_commands.command(
        name="translate",
        description="Translate text to a specified language."
    )
    async def translate(self, interaction: discord.Interaction, target_language: str, text: str):
        """Translate text to a specified language."""
        try:
            translation = await variables.translator.translate(text, dest=target_language)
            await interaction.response.send_message(f"# 🌐 **Translation ({target_language}):** {translation.text}")
        except Exception as e:
            await interaction.response.send_message(f"# ❌ Failed to translate:\n{e}")
        
    @app_commands.command(
        name="weather",
        description="Get the current weather for a city."
    )
    async def weather(self, interaction: discord.Interaction, city: str):
        """Get the current weather for a city."""
        api_key = variables.openwheather  # Replace with your API key
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        try:
            response = requests.get(url)
            data = response.json()
            if data["cod"] != 200:
                await interaction.response.send_message(f"❌ City not found: {city}")
                return
            weather_desc = data["weather"][0]["description"].capitalize()
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]
            await interaction.response.send_message(
                f"🌤️ **Weather in {city.capitalize()}**:\n"
                f"- Description: {weather_desc}\n"
                f"- Temperature: {temp}°C (Feels like {feels_like}°C)\n"
                f"- Humidity: {humidity}%\n"
                f"- Wind Speed: {wind_speed} m/s"
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}")
    
    @app_commands.command(
        name="setverifyrole",
        description="Set the role to be given on verification for this server."
    )
    @utils.admin_or_owner()
    async def set_verify_role(self, interaction: discord.Interaction, role: discord.Role):
        """Set the role to be given on verification for this server."""
        # Store role ID to avoid relying on names
        utils.set_guild_setting(interaction.guild.id, "verify_role_id", role.id)
        await interaction.response.send_message(f"✅ Verification role set to `{role.name}` for this server.")

    @app_commands.command(
        name="verify",
        description="Send a verification message and assign the custom verification role when reacted to."
    )
    @utils.admin_or_owner()
    async def verify(self, interaction: discord.Interaction):
        """Send a verification message and assign the custom verification role when reacted to."""
        try:
            # Get the custom verify role or default
            settings = utils.load_server_settings()
            guild_settings = settings.get(str(interaction.guild.id), {})
            verify_role_name = guild_settings.get("verify_role", ".・🍨︴Member ✰")

            # Create the embed for the verification message
            embed = discord.Embed(
                title="Verification",
                description=f"React with ✅ to verify yourself and gain access to the server!\n(You will get the `{verify_role_name}` role.)",
                color=discord.Color.green(),
            )
            embed.set_thumbnail(
                url="https://www.freeiconspng.com/thumbs/checkmark-png/checkmark-png-5.png"
            )

            # Send the embed message
            message = await interaction.channel.send(embed=embed)

            # Add the ✅ reaction to the message (bot adds it so users can react)
            await message.add_reaction("✅")

            # Save the message ID in server_settings.json
            guild_settings["verify_message_id"] = message.id
            settings[str(interaction.guild.id)] = guild_settings
            utils.save_server_settings(settings)

            logging.info(
                f"Verification message sent in {interaction.channel.name} (ID: {interaction.channel.id}). Message ID: {message.id}"
            )
            await interaction.response.send_message("✅ Verification message sent successfully!")
        except Exception as e:
            logging.error(f"Error in verify command: {e}")
            await interaction.response.send_message(f"❌ An error occurred while setting up verification: {e}")

    @app_commands.command(
        name="leaderboard",
        description="Display the leaderboard for level, XP, coins, or Easter Eggs."
    )
    async def leaderboard(self, interaction: discord.Interaction, category: str = "level"):
        """Display the leaderboard for level, XP, coins, or Easter Eggs."""
        valid_categories = ["level", "xp", "coins", "eggs"]
        if category not in valid_categories:
            await interaction.response.send_message(
                f"❌ Invalid category. Use `level`, `xp`, `coins`, or `eggs`."
            )
            return

        # Load user data
        data = utils.load_user_data()

        # Prepare the leaderboard
        leaderboard_data = []
        for user_id, user_info in data.items():
            if user_id.isdigit():  # Ensure it's a user ID
                user = interaction.guild.get_member(int(user_id))
                if user:  # Only include users who are in the server
                    leaderboard_data.append(
                        {
                            "name": user.display_name,
                            "level": user_info.get("level", 0),
                            "xp": user_info.get("xp", 0),
                            "coins": user_info.get("coins", 0),
                            "eggs": variables.easter_data.get(user_id, {}).get(
                                "eggs", 0
                            ),  # Include Easter Eggs
                        }
                    )

        # Sort the leaderboard based on the selected category
        # Ensure values are compared as integers to avoid TypeError when some data is stored as strings
        def _safe_key(x):
            val = x.get(category, 0)
            try:
                return int(val)
            except Exception:
                try:
                    return int(float(val))
                except Exception:
                    return 0

        leaderboard_data = sorted(leaderboard_data, key=_safe_key, reverse=True)

        # Create the leaderboard message
        embed = discord.Embed(
            title=f"🏆 {category.capitalize()} Leaderboard",
            description=f"Top users by {category.capitalize()}",
            color=discord.Color.gold(),
        )

        for i, entry in enumerate(leaderboard_data[:10], start=1):  # Show top 10 users
            embed.add_field(
                name=f"{i}. {entry['name']}",
                value=f"**{category.capitalize()}:** {entry[category]}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)
            
    @app_commands.command(
        name="announcement",
        description="Send an announcement to all servers."
    )
    @commands.check(utils.is_owner)
    async def announcement(self, interaction: discord.Interaction, message: str):
        """
        Send an announcement to all servers.
        Ultra-robust detection:
        - Unicode fonts
        - Emojis
        - Symbols
        - Synonyms
        - Topics + names
        - Scoring-based selection
        """
        for guild in self.bot.guilds:
            try:
                # Settings check
                try:
                    if not utils.get_guild_setting(guild.id, "announcements_enabled", True):
                        continue
                except Exception:
                    pass

                best_channel = None
                best_score = -999

                for channel in guild.text_channels:
                    if not channel.permissions_for(guild.me).send_messages:
                        continue

                    score = score_channel(channel)

                    if score > best_score:
                        best_score = score
                        best_channel = channel

                if best_channel and best_score > 0:
                    await best_channel.send(
                        f"📢 **General Announcement!: **\n{message}"
                    )
                else:
                    # Fallback: DM owner
                    try:
                        if guild.owner:
                            await guild.owner.send(
                                f"❌ No announcement channel detected in **{guild.name}**.\n"
                                f"Tip: Use words like *announcement, news, update* in the channel name or topic."
                            )
                    except Exception:
                        pass

            except discord.Forbidden:
                pass
            except Exception as e:
                logging.error(f"[Announcement Error] {guild.name}: {e}")

        await interaction.response.send_message("✅ Announcement process complete.")

    @app_commands.command(
        name="addrolereaction",
        description="Link an emoji to a role for a specific message (for reaction roles)."
    )
    @utils.admin_or_owner()
    async def add_role_reaction(self, interaction: discord.Interaction, message_id: int, emoji: str, role: discord.Role):
        """Link an emoji to a role for a specific message (for reaction roles)."""
        utils.set_guild_role_reaction(interaction.guild.id, message_id, emoji, role.id)
        await interaction.response.send_message(f"✅ Reaction role set: {emoji} → {role.name} on message {message_id}")

    @app_commands.command(
        name="removerolereaction",
        description="Remove a reaction role mapping."
    )
    @utils.admin_or_owner()
    async def remove_role_reaction(self, interaction: discord.Interaction, message_id: int, emoji: str):
        """Remove a reaction role mapping."""
        utils.remove_guild_role_reaction(interaction.guild.id, message_id, emoji)
        await interaction.response.send_message(f"✅ Removed reaction role for {emoji} on message {message_id}")

    @app_commands.command(
        name="lookup",
        description="Look up a user by their ID or username."
    )
    async def lookup(self, interaction: discord.Interaction, input_value: str):
        """Look up a user by their ID or username."""
        # Check if the input is a user ID
        if input_value.isdigit():
            user = await self.bot.fetch_user(int(input_value))
            if user:
                await interaction.response.send_message(
                    f"🔍 User ID `{input_value}` belongs to: **{user.name}#{user.discriminator}**"
                )
            else:
                await interaction.response.send_message(f"❌ No user found with ID `{input_value}`.")
        else:
            # Check if the input is a mention or username
            user = discord.utils.get(
                interaction.guild.members, name=input_value
            ) or discord.utils.get(interaction.guild.members, mention=input_value)
            if user:
                await interaction.response.send_message(
                    f"🔍 User `{user.name}#{user.discriminator}` has the ID: **{user.id}**"
                )
            else:
                await interaction.response.send_message(
                    f"❌ No user found with the name or mention `{input_value}`."
                )


    # Consolidated selfrole group
    selfrole_group = app_commands.Group(name="selfrole", description="Manage self-assignable roles.")

    @selfrole_group.command(name="add", description="Add a role to the list of self-assignable roles.")
    @utils.admin_or_owner()
    async def selfrole_add(self, interaction: discord.Interaction, role: discord.Role):
        utils.add_guild_self_role(interaction.guild.id, role.id)
        await interaction.response.send_message(f"✅ `{role.name}` is now self-assignable.")

    @selfrole_group.command(name="remove", description="Remove a role from the list of self-assignable roles.")
    @utils.admin_or_owner()
    async def selfrole_remove(self, interaction: discord.Interaction, role: discord.Role):
        utils.remove_guild_self_role(interaction.guild.id, role.id)
        await interaction.response.send_message(f"✅ `{role.name}` is no longer self-assignable.")

    @selfrole_group.command(name="list", description="List all self-assignable roles.")
    async def selfrole_list(self, interaction: discord.Interaction):
        role_ids = utils.get_guild_self_roles(interaction.guild.id)
        if not role_ids:
            await interaction.response.send_message("No self-assignable roles set for this server.")
            return
        names = []
        for rid in role_ids:
            try:
                r = interaction.guild.get_role(int(rid))
                if r:
                    names.append(r.name)
                else:
                    names.append(f"<missing role {rid}>")
            except Exception:
                names.append(str(rid))
        await interaction.response.send_message("Self-assignable roles:\n" + "\n".join(f"- {n}" for n in names))

    @selfrole_group.command(name="assign", description="Assign yourself a self-assignable role.")
    async def selfrole_assign(self, interaction: discord.Interaction, role: discord.Role):
        roles = utils.get_guild_self_roles(interaction.guild.id)
        if str(role.id) not in roles:
            await interaction.response.send_message("❌ That role is not self-assignable.")
            return
        if role in interaction.user.roles:
            await interaction.response.send_message("You already have that role.")
            return
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"✅ You have been given the `{role.name}` role.")

    @selfrole_group.command(name="unassign", description="Remove a self-assignable role from yourself.")
    async def selfrole_unassign(self, interaction: discord.Interaction, role: discord.Role):
        roles = utils.get_guild_self_roles(interaction.guild.id)
        if str(role.id) not in roles:
            await interaction.response.send_message("❌ That role is not self-assignable.")
            return
        if role not in interaction.user.roles:
            await interaction.response.send_message("You don't have that role.")
            return
        await interaction.user.remove_roles(role)
        await interaction.response.send_message(f"✅ `{role.name}` role removed from you.")

    # Consolidated autorole group
    autorole_group = app_commands.Group(name="autorole", description="Manage auto-role configuration.")

    @autorole_group.command(name="set", description="Set a role to be automatically assigned to new members.")
    @utils.admin_or_owner()
    async def autorole_set(self, interaction: discord.Interaction, role: discord.Role):
        utils.set_auto_role(interaction.guild.id, role.id)
        await interaction.response.send_message(f"✅ Set auto-role to **{role.name}**. All new members will receive this role.")

    @autorole_group.command(name="remove", description="Remove the auto-role configuration.")
    @utils.admin_or_owner()
    async def autorole_remove(self, interaction: discord.Interaction):
        data = utils.load_auto_roles()
        if str(interaction.guild.id) in data:
            del data[str(interaction.guild.id)]
            utils.save_auto_roles(data)
            await interaction.response.send_message("✅ Removed auto-role configuration.")
        else:
            await interaction.response.send_message("❌ No auto-role was configured.")

    @autorole_group.command(name="show", description="Show the current auto-role configuration.")
    @utils.admin_or_owner()
    async def autorole_show(self, interaction: discord.Interaction):
        role_identifier = utils.get_auto_role(interaction.guild.id)
        if role_identifier:
            try:
                role = interaction.guild.get_role(int(role_identifier))
            except Exception:
                role = discord.utils.get(interaction.guild.roles, name=str(role_identifier))
            if role:
                await interaction.response.send_message(f"Current auto-role: **{role.name}**")
            else:
                await interaction.response.send_message(f"⚠️ Auto-role was set to '{role_identifier}' but the role no longer exists.")
        else:
            await interaction.response.send_message("❌ No auto-role configured.")

    # Consolidated rolereaction group
    rolereaction_group = app_commands.Group(name="rolereaction", description="Manage reaction role mappings.")

    @rolereaction_group.command(name="add", description="Link an emoji to a role for a specific message (for reaction roles).")
    @utils.admin_or_owner()
    async def rolereaction_add(self, interaction: discord.Interaction, message_id: int, emoji: str, role: discord.Role):
        utils.set_guild_role_reaction(interaction.guild.id, message_id, emoji, role.id)
        await interaction.response.send_message(f"✅ Reaction role set: {emoji} → {role.name} on message {message_id}")

    @rolereaction_group.command(name="remove", description="Remove a reaction role mapping.")
    @utils.admin_or_owner()
    async def rolereaction_remove(self, interaction: discord.Interaction, message_id: int, emoji: str):
        utils.remove_guild_role_reaction(interaction.guild.id, message_id, emoji)
        await interaction.response.send_message(f"✅ Removed reaction role for {emoji} on message {message_id}")
        
    @app_commands.command(
        name="autorole_set",
        description="Set a role to be automatically assigned to new members."
    )
    @utils.admin_or_owner()
    async def autorole_set(self, interaction: discord.Interaction, role: discord.Role):
        """Set a role to be automatically assigned to new members."""
        utils.set_auto_role(interaction.guild.id, role.id)
        await interaction.response.send_message(f"✅ Set auto-role to **{role.name}**. All new members will receive this role.")

    @app_commands.command(
        name="autorole_remove",
        description="Remove the auto-role configuration."
    )
    @utils.admin_or_owner()
    async def autorole_remove(self, interaction: discord.Interaction):
        """Remove the auto-role configuration."""
        data = utils.load_auto_roles()
        if str(interaction.guild.id) in data:
            del data[str(interaction.guild.id)]
            utils.save_auto_roles(data)
            await interaction.response.send_message("✅ Removed auto-role configuration.")
        else:
            await interaction.response.send_message("❌ No auto-role was configured.")

    @app_commands.command(
        name="autorole_show",
        description="Show the current auto-role configuration."
    )
    @utils.admin_or_owner()
    async def autorole_show(self, interaction: discord.Interaction):
        """Show the current auto-role configuration."""
        role_identifier = utils.get_auto_role(interaction.guild.id)
        if role_identifier:
            # Try interpret as ID first
            try:
                role = interaction.guild.get_role(int(role_identifier))
            except Exception:
                role = discord.utils.get(interaction.guild.roles, name=str(role_identifier))
            if role:
                await interaction.response.send_message(f"Current auto-role: **{role.name}**")
            else:
                await interaction.response.send_message(f"⚠️ Auto-role was set to '{role_identifier}' but the role no longer exists.")
        else:
            await interaction.response.send_message("❌ No auto-role configured.")

    @app_commands.command(
        name="servercustom",
        description="Show all customizations for this server."
    )
    @utils.admin_or_owner()
    async def server_customization(self, interaction: discord.Interaction):
        """Show all customizations for this server."""
        guild_id = interaction.guild.id
        prefix = utils.get_guild_prefix(guild_id)
        welcome = utils.get_guild_welcome_message(guild_id) or "Not set"
        goodbye = utils.get_guild_goodbye_message(guild_id) or "Not set"
        level_roles = utils.get_guild_level_roles(guild_id)
        self_roles = utils.get_guild_self_roles(guild_id)
        role_reactions = utils.get_guild_role_reactions(guild_id)

        embed = discord.Embed(
            title=f"Server Customizations for {interaction.guild.name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Prefix", value=f"`{prefix}`", inline=False)
        embed.add_field(name="Welcome Message", value=welcome, inline=False)
        embed.add_field(name="Goodbye Message", value=goodbye, inline=False)
        embed.add_field(
            name="Level Roles",
            value="\n".join(f"Level {lvl}: {role}" for lvl, role in level_roles.items()) or "None",
            inline=False
        )
        embed.add_field(
            name="Self-Assignable Roles",
            value="\n".join(self_roles) or "None",
            inline=False
        )
        if role_reactions:
            rr_lines = []
            for msg_id, mapping in role_reactions.items():
                for emoji, role_id in mapping.items():
                    rr_lines.append(f"Msg {msg_id}: {emoji} → <@&{role_id}>")
            embed.add_field(
                name="Role Reactions",
                value="\n".join(rr_lines) or "None",
                inline=False
            )
        else:
            embed.add_field(name="Role Reactions", value="None", inline=False)

        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(
        name="giveaway",
        description="Start a giveaway."
    )
    @commands.has_permissions(administrator=True)
    async def giveaway(self, interaction: discord.Interaction, duration: int, reward: str, image_url: typing.Optional[str] = None):
        """
        Start a giveaway.
        """
        embed = discord.Embed(
            title="🎉 Giveaway!",
            description=f"React or click the button below to enter!\n**Reward:** {reward}\n**Ends in:** {duration} seconds",
            color=discord.Color.gold()
        )
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(text=f"Hosted by {interaction.user.display_name}")

        # Send the embed first, then get the message object
        sent_message = await interaction.channel.send(embed=embed)
        view = GiveawayView(sent_message.id, timeout=duration)
        await sent_message.edit(view=view)
        await sent_message.add_reaction("🎉")

        # Save giveaway info
        giveaways = utils.load_giveaways()
        giveaways[str(sent_message.id)] = {
            "channel_id": interaction.channel.id,
            "reward": reward,
            "host_id": interaction.user.id,
            "end_time": asyncio.get_event_loop().time() + duration,
            "image_url": image_url,
            "entries": []
        }
        utils.save_giveaways(giveaways)

        await interaction.response.send_message(f"✅ Giveaway started for **{reward}**! Ends in {duration} seconds.")

        # Wait for the duration
        await asyncio.sleep(duration)

        # Fetch message again to get reactions
        message = await interaction.channel.fetch_message(sent_message.id)
        users = set()
        for reaction in message.reactions:
            if str(reaction.emoji) == "🎉":
                async for user in reaction.users():
                    if not user.bot:
                        users.add(user.id)

        # Add button entries
        if hasattr(view, "entries"):
            users.update(view.entries)

        if not users:
            await interaction.channel.send("No one entered the giveaway.")
            return

        winner_id = random.choice(list(users))
        winner = interaction.guild.get_member(winner_id)
        await interaction.channel.send(f"🎊 Congratulations {winner.mention}! You won **{reward}**!")

        # Update giveaway data
        giveaways = utils.load_giveaways()
        giveaways[str(sent_message.id)]["entries"] = list(users)
        giveaways[str(sent_message.id)]["winner_id"] = winner_id
        utils.save_giveaways(giveaways)

    @app_commands.command(
        name="giveawaycancel",
        description="Cancel an active giveaway."
    )
    @commands.has_permissions(administrator=True)
    async def giveawaycancel(self, interaction: discord.Interaction, message_id: int):
        """Cancel an active giveaway."""
        giveaways = utils.load_giveaways()
        if str(message_id) in giveaways:
            del giveaways[str(message_id)]
            utils.save_giveaways(giveaways)
            await interaction.response.send_message("❌ Giveaway cancelled.")
        else:
            await interaction.response.send_message("No giveaway found with that message ID.")

    @app_commands.command(
        name="giveawayinfo",
        description="Show info about a giveaway."
    )
    @commands.has_permissions(administrator=True)
    async def giveawayinfo(self, interaction: discord.Interaction, message_id: int):
        """Show info about a giveaway."""
        giveaways = utils.load_giveaways()
        info = giveaways.get(str(message_id))
        if not info:
            await interaction.response.send_message("No giveaway found with that message ID.")
            return
        embed = discord.Embed(
            title="Giveaway Info",
            description=f"**Reward:** {info['reward']}\n**Host:** <@{info['host_id']}>\n**Entries:** {len(info.get('entries', []))}",
            color=discord.Color.blue()
        )
        if info.get("image_url"):
            embed.set_image(url=info["image_url"])
        if "winner_id" in info:
            embed.add_field(name="Winner", value=f"<@{info['winner_id']}>")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(
        name="setdestination",
        description="Set the destination channel for level-up notifications."
    )
    @commands.has_permissions(administrator=True)
    async def setdestination(self, interaction: discord.Interaction, channel_name: str):
        """Set the destination channel for level-up notifications."""
        settings = utils.load_server_settings()
        guild_id = str(interaction.guild.id)
        if guild_id not in settings:
            settings[guild_id] = {}
        settings[guild_id]["destination"] = channel_name
        utils.save_server_settings(settings)
        await interaction.response.send_message(f"✅ Destination channel set to `{channel_name}` for level-up notifications.")
    
        
    @app_commands.command(
        name="setwelcomechannel",
        description="Set the welcome channel for this server."
    )
    @utils.admin_or_owner()
    async def set_welcome_channel(self, interaction: discord.Interaction, channel: typing.Optional[discord.TextChannel] = None):
        """Set the welcome channel for this server."""
        if channel is None:
            channel = interaction.channel
        settings = utils.load_server_settings()
        guild_settings = settings.get(str(interaction.guild.id), {})
        guild_settings["welcome_channel"] = channel.name.lower()
        settings[str(interaction.guild.id)] = guild_settings
        utils.save_server_settings(settings)
        await interaction.response.send_message(f"# ✅ Welcome channel set to `{channel.name}`.")

    @app_commands.command(
        name="setgoodbyechannel",
        description="Set the goodbye channel for this server."
    )
    @utils.admin_or_owner()
    async def set_goodbye_channel(self, interaction: discord.Interaction, channel: typing.Optional[discord.TextChannel] = None):
        """Set the goodbye channel for this server."""
        if channel is None:
            channel = interaction.channel
        settings = utils.load_server_settings()
        guild_settings = settings.get(str(interaction.guild.id), {})
        guild_settings["goodbye_channel"] = channel.name.lower()
        settings[str(interaction.guild.id)] = guild_settings
        utils.save_server_settings(settings)
        await interaction.response.send_message(f"# ✅ Goodbye channel set to `{channel.name}`.")

import typing
import discord
from discord.ext import commands
import os
import json
import time as _t

# Assume 'utils' is imported or defined elsewhere and contains 'is_owner'
# and the command is part of a cog class.

class ServerAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="serverlockdown",
        description="Dangerous: Permanently modify the server to lockdown state. Owner-only and requires explicit confirmation."
    )
    @commands.check(lambda interaction: interaction.guild is not None and (interaction.user.id == interaction.guild.owner_id or utils.is_owner(interaction)))
    async def serverlockdown(self, interaction: discord.Interaction, confirm1: str, confirm2: str, optional_server_id: typing.Optional[str] = None):
        """Dangerous: Permanently modify the server to lockdown state. Owner-only and requires explicit confirmation."""
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("# ❌ This command must be used in a server.")

        # Only allow the server owner or the bot owner to run this
        if interaction.user.id != guild.owner_id and not utils.is_owner(interaction):
            return await interaction.response.send_message("# ❌ Only the server owner or the bot owner can run this command.")

        # Ensure bot has administrator permissions
        me = guild.me
        if not me.guild_permissions.administrator:
            return await interaction.response.send_message("# ❌ I need Administrator permissions to perform a lockdown.")

        # --- Enhanced Confirmation Check ---
        
        # Check for the mandatory confirmation phrase
        required_confirmation = "CONFIRM LOCKDOWN"
        provided_confirmation = f"{confirm1} {confirm2}"
        
        # Check if the mandatory phrase matches
        if provided_confirmation.upper().strip() != required_confirmation:
            return await interaction.response.send_message(f"# ⚠️ This is destructive!\nTo confirm, run: `/serverlockdown {required_confirmation} [SERVER_ID]`")

        # Check for optional Server ID verification
        if optional_server_id and str(optional_server_id).strip() != str(guild.id):
             return await interaction.response.send_message(f"# ❌ Optional Server ID verification failed.\nThe provided ID `{optional_server_id}` does not match this server's ID `{guild.id}`.")

        # --- End of Confirmation Check ---

        await interaction.response.send_message("# 🚨 Lockdown starting. This may take a while. I will attempt to backup the server state where possible.")

        # Try to create a backup of basic settings we can later restore (roles and channels list JSON)
        try:
            backup = {
                "roles": [],
                "channels": []
            }
            for r in guild.roles:
                backup["roles"].append({
                    "id": r.id,
                    "name": r.name,
                    "permissions": r.permissions.value,
                    "colour": r.colour.value,
                    "hoist": r.hoist,
                    "position": r.position,
                    "managed": r.managed,
                })
            for c in guild.channels:
                backup["channels"].append({
                    "id": c.id,
                    "name": c.name,
                    "type": str(type(c)), 
                })
            os.makedirs("backups/server_lockdowns", exist_ok=True)
            path = f"backups/server_lockdowns/{guild.id}_{int(_t.time())}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(backup, f, indent=2)
            await interaction.followup.send(f"# 💾 Server state backed up to `{path}` locally.")
        except Exception as e:
            await interaction.followup.send(f"# ⚠️ Failed to create a local backup:\n`{e}`")

        # Step 1: Delete channels
        try:
            channels = list(guild.channels)
            for ch in channels:
                try:
                    await ch.delete(reason=f"Server lockdown invoked by {interaction.user}")
                except Exception:
                    pass
            await interaction.followup.send("# ✅ Channels deleted.")
        except Exception as e:
            await interaction.followup.send(f"# ⚠️ Channel deletion encountered an error:\n`{e}`")

        # Step 2: Delete roles below the bot's top role
        try:
            bot_top = me.top_role.position if me and me.top_role else 0
            roles_to_remove = [r for r in guild.roles if r.position < bot_top and not r.managed and r != guild.default_role]
            for r in roles_to_remove:
                try:
                    await r.delete(reason=f"Server lockdown invoked by {interaction.user}")
                except Exception:
                    pass
            await interaction.followup.send("# ✅ Roles deleted.")
        except Exception as e:
            await interaction.followup.send(f"# ⚠️ Role deletion encountered an error:\n`{e}`")
        
        lockdown_role = None

        # Step 3: Create a 'lockdown' role and assign to all members
        try:
            lockdown_role = await guild.create_role(name="lockdown", permissions=discord.Permissions.none(), reason=f"Created lockdown role by {interaction.user}")
            try:
                await lockdown_role.edit(position=me.top_role.position - 1 if me and me.top_role else 1)
            except Exception:
                pass

            for member in guild.members:
                try:
                    if not member.bot:
                        await member.add_roles(lockdown_role, reason="Server lockdown applied")
                except Exception:
                    pass
            await interaction.followup.send("# ✅ Lockdown role created and assigned to members.")
        except Exception as e:
            await interaction.followup.send(f"# ⚠️ Failed creating or assigning lockdown role:\n`{e}`")

        # Step 4: Recreate a help channel with send_permissions for everyone disabled
        if lockdown_role is not None:
            try:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(send_messages=False, view_channel=True),
                    lockdown_role: discord.PermissionOverwrite(send_messages=False, view_channel=True)
                }
                help_chan = await guild.create_text_channel("help", overwrites=overwrites, reason=f"Created help channel during lockdown by {interaction.user}")
                await help_chan.send("# Sorry! This server is now in lockdown.")
                await interaction.followup.send("# ✅ Help channel recreated.")
            except Exception as e:
                await interaction.followup.send(f"# ⚠️ Failed creating help channel:\n`{e}`")
        else:
            await interaction.followup.send("# ⚠️ Skipped help channel creation as lockdown role was not created.")

        await interaction.followup.send("# ✅ Lockdown completed (best-effort).\nMembers have been assigned the lockdown role and channels/roles were removed where possible.")


async def setup(bot):
    await bot.add_cog(Utility(bot))