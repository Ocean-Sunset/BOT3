import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
from discord import FFmpegPCMAudio
import os
import openai  # For ChatGPT functionality
import time
import json
import sys
import logging
import requests
import random
import asyncio
from os import environ
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
token = environ["TOKEN"]

# Set OpenAI API Key
OPENAI_API_KEY = environ.get("OPEN_API_KEY") # Replace with your actual API key
openai.api_key = OPENAI_API_KEY

UNSPLACH_API_KEY = os.environ.get("UNSPLASH_API_KEY")

# Define intents and enable the message content intent
intents = discord.Intents.default()
intents.message_content = True  # This is required for processing commands
intents.guilds = True
intents.members = True
intents.reactions = True

# Create the bot with intents
bot = commands.Bot(command_prefix="?", intents=intents)

## filepath: /c:/Users/roland/Documents/Discord/BOT3/brain.py
@bot.command(name="search_img")
async def search_img(ctx, *, query: str):
    headers = {"Authorization": f"Client-ID {UNSPLACH_API_KEY}"}
    search_url = "https://api.unsplash.com/search/photos"
    params = {"query": query, "per_page": 1}

    response = requests.get(search_url, headers=headers, params=params)
    response.raise_for_status()
    search_results = response.json()

    if search_results["results"]:
        img_url = search_results["results"][0]["urls"]["regular"]
        await ctx.send(img_url)
    else:
        await ctx.send("No results found.")


# Load or initialize user data
if os.path.exists("data/user_data.json"):
    with open("data/user_data.json", "r") as f:
        user_data = json.load(f)
else:
    user_data = {}

# Load or initialize warnings data
if os.path.exists("data/warnings.json"):
    with open("data/warnings.json", "r") as f:
        warnings_data = json.load(f)
else:
    warnings_data = {}

# Save user data
def save_user_data():
    with open("data/user_data.json", "w") as f:
        json.dump(user_data, f)

# Save warnings data
def save_warnings_data():
    with open("data/warnings.json", "w") as f:
        json.dump(warnings_data, f)

# Add this function to get the logs channel
def get_logs_channel(guild):
    return discord.utils.get(guild.text_channels, name="『📂』logs "or "logs")

# Function to get the welcome and bye channels
def get_channel_by_name(guild, channel_name):
    return discord.utils.get(guild.text_channels, name="『🎊』all-announcements")

@bot.event
async def on_command(ctx):
    logging.info(f"{ctx.author} executed {ctx.command} in {ctx.channel}.")

@bot.event
async def on_command_completion(ctx):
    logs_channel = get_logs_channel(ctx.guild)
    if logs_channel:
        await logs_channel.send(f"{ctx.author} executed `{ctx.command}` in {ctx.channel}.")
    logging.info(f"{ctx.author} executed `{ctx.command}` successfully.")

@bot.event
async def on_command_error(ctx, error):
    logs_channel = get_logs_channel(ctx.guild)
    if logs_channel:
        await logs_channel.send(f"{ctx.author} tried to execute `{ctx.command}` in {ctx.channel}. Status: error. Reason: {error}")
    logging.error(f"{ctx.author} tried to execute `{ctx.command}`. Error: {error}")
    await ctx.send(f"❌ An error occurred: {error}")

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# File to store user money data
money_data_file = "data/money_data.json"

# Load or initialize money data
if os.path.exists(money_data_file):
    try:
        with open(money_data_file, "r") as f:
            money_data = json.load(f)
    except json.JSONDecodeError:
        money_data = {}
else:
    money_data = {}

# Save money data
def save_money_data():
    with open(money_data_file, "w") as f:
        json.dump(money_data, f)

# Custom logging handler to send logs to the logs channel
class DiscordLogHandler(logging.Handler):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def emit(self, record):
        log_entry = self.format(record)
        for guild in self.bot.guilds:
            logs_channel = get_logs_channel(guild)
            if logs_channel:
                self.bot.loop.create_task(logs_channel.send(log_entry))

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
discord_handler = DiscordLogHandler(bot)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
discord_handler.setFormatter(formatter)
logger.addHandler(discord_handler)

# Event: Bot is ready
@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user}")

# File to store banned server IDs
banned_servers_file = "data/banned_servers.json"

# Load or initialize banned servers data
if os.path.exists(banned_servers_file):
    try:
        with open(banned_servers_file, "r") as f:
            banned_servers = json.load(f)
    except json.JSONDecodeError:
        # If the file is empty or invalid, initialize an empty list
        banned_servers = []
else:
    banned_servers = []

# Save banned servers data
def save_banned_servers():
    with open(banned_servers_file, "w") as f:
        json.dump(banned_servers, f)

# Middleware to check if the server is banned
@bot.check
async def check_banned_server(ctx):
    if ctx.guild and ctx.guild.id in banned_servers:
        await ctx.send("❌ This server is banned from using the bot.")
        return False
    return True

# Command: Ban Server
@bot.command(name="BServer")
@commands.has_permissions(administrator=True)
async def ban_server(ctx, *, server_name: str):
    for guild in bot.guilds:
        if guild.name.lower() == server_name.lower():
            if guild.id in banned_servers:
                await ctx.send(f"❌ Server **{server_name}** is already banned.")
                return
            banned_servers.append(guild.id)
            save_banned_servers()
            await ctx.send(f"✅ Server **{server_name}** has been banned. The bot will no longer work there.")
            return
    await ctx.send(f"❌ Server **{server_name}** not found.")

# Command: Unban Server
@bot.command(name="UBServer")
@commands.has_permissions(administrator=True)
async def unban_server(ctx, *, server_name: str):
    for guild in bot.guilds:
        if guild.name.lower() == server_name.lower():
            if guild.id not in banned_servers:
                await ctx.send(f"❌ Server **{server_name}** is not banned.")
                return
            banned_servers.remove(guild.id)
            save_banned_servers()
            await ctx.send(f"✅ Server **{server_name}** has been unbanned. The bot will now work there.")
            return
    await ctx.send(f"❌ Server **{server_name}** not found.")

# File to store server restriction levels
server_restrictions_file = "data/server_restrictions.json"

# Load or initialize server restrictions data
if os.path.exists(server_restrictions_file):
    try:
        with open(server_restrictions_file, "r") as f:
            server_restrictions = json.load(f)
    except json.JSONDecodeError:
        # If the file is empty or invalid, initialize an empty dictionary
        server_restrictions = {}
else:
    server_restrictions = {}

# Save server restrictions data
def save_server_restrictions():
    with open(server_restrictions_file, "w") as f:
        json.dump(server_restrictions, f)

# Middleware to check server restrictions
@bot.check
async def check_server_restrictions(ctx):
    if ctx.guild:
        # Allow BServer and UBServer commands to bypass restrictions
        if ctx.command.name in ["BServer", "UBServer"]:
            return True

        restriction_level = server_restrictions.get(str(ctx.guild.id), "Free")
        if restriction_level == "Limited" and ctx.command.name in ["startgame", "givexp", "gainlvl", "choose_country"]:
            await ctx.send("❌ This command is restricted in Limited mode.")
            return False
        elif restriction_level == "Very Limited" and ctx.command.name not in ["ban", "kick"]:
            await ctx.send("❌ This command is restricted in Very Limited mode.")
            return False
        elif restriction_level == "Absolute Restriction" and ctx.command.name not in ["ban", "kick"]:
            await ctx.send("❌ This command is restricted in Absolute Restriction mode.")
            return False
    return True

# Command: Manage Server
@bot.command(name="MServer")
@commands.has_permissions(administrator=True)
async def manage_server(ctx, *, args: str):
    try:
        server_name, restriction_level = args.split(" / ")
    except ValueError:
        await ctx.send("❌ Invalid format. Use `?MServer <Server Name> / <Restriction Level>`.")
        return

    restriction_levels = ["Free", "Limited", "Very Limited", "Absolute Restriction"]

    if restriction_level not in restriction_levels:
        await ctx.send(f"❌ Invalid restriction level. Choose from: {', '.join(restriction_levels)}.")
        return

    for guild in bot.guilds:
        if guild.name.lower() == server_name.lower():
            server_restrictions[str(guild.id)] = restriction_level
            save_server_restrictions()
            await ctx.send(f"✅ Server **{server_name}** is now set to **{restriction_level}** mode.")
            return

    await ctx.send(f"❌ Server **{server_name}** not found.")

# File to store bot info (version and new features)
bot_info_file = "data/bot_info.json"

# Load or initialize bot info
if os.path.exists(bot_info_file):
    try:
        with open(bot_info_file, "r") as f:
            bot_info = json.load(f)
    except json.JSONDecodeError:
        bot_info = {"version": "1.6.2", "new_stuff": "Initial release"}
else:
    bot_info = {"version": "1.6.2", "new_stuff": "Initial release"}

# Save bot info
def save_bot_info():
    with open(bot_info_file, "w") as f:
        json.dump(bot_info, f)

@bot.command(name="update")
@commands.has_permissions(administrator=True)
async def update(ctx, *, args: str):
    """Update the bot's version and new features, then restart."""
    try:
        version, new_stuff = args.split(" / ")
    except ValueError:
        await ctx.send("❌ Invalid format. Use `?update <version> / <new features>`.")
        return

    # Update the bot info
    bot_info["version"] = version
    bot_info["new_stuff"] = new_stuff
    save_bot_info()

    await ctx.send(f"✅ Bot updated to version **{version}** with new features: **{new_stuff}**.")
    await ctx.send("🔄 Restarting the bot...")

    # Restart the bot with the skip-input flag
    os.execv(sys.executable, ["python", __file__, "--skip-input"])

# Event: On message
@bot.event
async def on_message(message):
    global user_data  # Add this line to reference the global user_data variable

    if message.author == bot.user:
        return

    user_id = str(message.author.id)
    if user_id not in user_data:
        user_data[user_id] = {"xp": 0, "level": 1}

    user_data[user_id]["xp"] += 2  # Reward 10 XP per message
    current_xp = user_data[user_id]["xp"]
    current_level = user_data[user_id]["level"]
    next_level_xp = current_level * 100  # Example: 100 XP per level

    if current_xp >= next_level_xp:
        user_data[user_id]["level"] += 1
        user_data[user_id]["xp"] = current_xp - next_level_xp
        await message.channel.send(f"🎉 {message.author.mention} has reached level {user_data[user_id]['level']}!")
        logging.info(f"{message.author} has reached level {user_data[user_id]['level']}")

    save_user_data()

    # Anti-spam logic
    user_id = str(message.author.id)
    current_time = time.time()

    if user_id in warnings_data:
        user_data = warnings_data[user_id]
        user_data["messages"].append(current_time)

        # Remove messages older than 10 seconds from tracking
        user_data["messages"] = [msg_time for msg_time in user_data["messages"] if current_time - msg_time < 10]

        # Take action if the user exceeds the message limit
        if len(user_data["messages"]) > 5:  # Limit: 5 messages in 10 seconds
            await message.channel.send(f"🚨 {message.author.mention}, you are spamming! Please slow down.")
            await message.delete()  # Optionally delete the spam message
            logs_channel = get_logs_channel(message.guild)
            if logs_channel:
                await logs_channel.send(f"User {message.author} was warned for spamming in {message.channel}")
            # Add a warning
            if user_id not in warnings_data:
                warnings_data[user_id] = {"warnings": 0}
            warnings_data[user_id]["warnings"] += 1
            save_warnings_data()

            # Mute the user if they reach 5 warnings
            if warnings_data[user_id]["warnings"] >= 5:
                mute_role = discord.utils.get(message.guild.roles, name="Muted")
                if not mute_role:
                    mute_role = await message.guild.create_role(name="Muted")
                    for channel in message.guild.channels:
                        await channel.set_permissions(mute_role, send_messages=False, speak=False)
                await message.author.add_roles(mute_role)
                await message.channel.send(f"{message.author.mention} has been muted for 10 minutes due to excessive warnings.")
                await logs_channel.send(f"{message.author} has been muted for 10 minutes due to excessive warnings.")
                await asyncio.sleep(600)  # 10 minutes
                await message.author.remove_roles(mute_role)
                await message.channel.send(f"{message.author.mention} has been unmuted.")
                await logs_channel.send(f"{message.author} has been unmuted.")
    else:
        # Start tracking the user
        warnings_data[user_id] = {"messages": [current_time], "warnings": 0}

    save_user_data()
    # Allow commands to be processed
    await bot.process_commands(message)

# Event: On reaction add
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member is None:
        member = await guild.fetch_member(payload.user_id)
    emoji = str(payload.emoji)

    if emoji == "✅":
        role_name = "Verified"
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            role = await guild.create_role(name=role_name)
        await member.add_roles(role)
        await member.send(f"You have been given the {role_name} role.")

# Event: On reaction remove (optional, to remove the role when the reaction is removed)
@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member is None:
        member = await guild.fetch_member(payload.user_id)
    emoji = str(payload.emoji)

    if emoji == "✅":
        role_name = "Verified"
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            await member.remove_roles(role)
            await member.send(f"The {role_name} role has been removed from you.")

# Command: Copy text
@bot.command()
@commands.has_permissions(administrator=True)
async def copy(ctx, *, text: str):
    await ctx.send(text)

# Command: Copy text to DM
@bot.command()
@commands.has_permissions(administrator=True)
async def copydm(ctx, member: discord.Member, *, text: str):
    try:
        await member.send(text)
        await ctx.send(f"✅ Sent the message to {member.mention}'s DMs.")
    except discord.Forbidden:
        await ctx.send(f"❌ I cannot send DMs to {member.mention}. They might have DMs disabled.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")

# Command: Send verification message
@bot.command()
@commands.has_permissions(administrator=True)
async def verify(ctx):
    message = await ctx.send("React to this message to verify!\n✅ to verify")
    await message.add_reaction("✅")

# Command: Choose Continent
@bot.command()
@commands.has_permissions(administrator=True)
async def choose_country(ctx):
    message = await ctx.send(
        "Choose your country by reacting with the corresponding emoji:\n"
        "🇺🇸 for United States\n"
        "🇨🇦 for Canada\n"
        "🇬🇧 for United Kingdom\n"
        "🇦🇺 for Australia\n"
        "🇮🇳 for India\n"
        "🇩🇪 for Germany\n"
        "🇫🇷 for France\n"
        "🇯🇵 for Japan\n"
        "🇰🇷 for South Korea\n"
        "🇧🇷 for Brazil"
    )
    reactions = ["🇺🇸", "🇨🇦", "🇬🇧", "🇦🇺", "🇮🇳", "🇩🇪", "🇫🇷", "🇯🇵", "🇰🇷", "🇧🇷"]
    for reaction in reactions:
        await message.add_reaction(reaction)

# Event: On member join
@bot.event
async def on_member_join(member):
    welcome_channel = get_channel_by_name(member.guild, ["welcome", "『🎊』all-announcements"])
    if welcome_channel:
        await welcome_channel.send(f"Welcome to the server, {member.mention}!")

# Event: On member remove
@bot.event
async def on_member_remove(member):
    bye_channel = get_channel_by_name(member.guild, ["bye", "『🎊』all-announcements"])
    if bye_channel:
        await bye_channel.send(f"Goodbye, {member.mention}. We will miss you!")

# Event: On command completion
@bot.event
async def on_command_completion(ctx):
    logs_channel = get_logs_channel(ctx.guild)
    if logs_channel:
        await logs_channel.send(f"{ctx.author} executed {ctx.command} in {ctx.channel}. Status: success.")

# Event: On command error
@bot.event
async def on_command_error(ctx, error):
    logs_channel = get_logs_channel(ctx.guild)
    if logs_channel:
        await logs_channel.send(f"{ctx.author} tried to execute {ctx.command} in {ctx.channel}. Status: error. Reason: {error}")
    await ctx.send(f"❌ An error occurred: {error}")

# ?help command
@bot.command(name="myhelp")
async def help(ctx):
    print(f"Help command triggered by {ctx.author} in channel {ctx.channel}.")
    help_message = """Available commands:
    ?help - Show this help message
    ?info - Get information about the bot
    ?serverinfo - Get information about the current server
    ?shutdown - Shut down the bot (Admin only)
    ?start - Start the bot (Admin only)
    ?poll - Create a poll (Usage: ?poll <question> <option1, option2, ...>)
    ?chat - Chat with ChatGPT (Usage: ?chat <your message>)
    ?analyse - Analyse the user you want (Usage: ?analyse @user)
    ?createrole - Create a role (Usage: ?createrole <name> <permissions: (member, mod or admin)> <color:(Hex code)>)
    ?giverole - Give a role (Usage: ?giverole <name> <user>)
    ?removerole - Remove a role (Usage: ?removerole <user> <role>)
    ?warn - Warn an user (Usage: ?warn <name> <reason>)
    ?kick - Kick an user (Usage: ?kick <name> <reason>)
    ?ban - Ban an user (Usage: ?ban <name> <reason>)
    ?givexp - Give XP to a user (Usage: ?givexp <user> <xp>)
    ?gainlvl - Give a level to a user (Usage: ?gainlvl <user>)
    ?copydm - Copy text to a user's DM (Usage: ?copydm <user> <text>)
    ?copychannel - Copy text to a specific channel (Usage: ?copychannel <channel> <text>)
    ?colorrole - Create a color role
    ?verify - Send a verification message
    ?copy - Copy text (Usage: ?copy <text>)
    ?choose_country - Choose your country
    ?startgame - Starts a Truth or Dare game (members MUST be already in the VC)
    ?checkvc - Checks wether all the users are in a voice channel or not (specifically Truth or Dare channel)
    ?continue - Continues the Truth or Dare game
    """
    help_message2 = """
    ?endgame - Ends the Truth or Dare game
    ?timeout - Timeout a user (Usage: ?timeout <user> <time> <reason>)
    ?search_img - Search for an image (Usage: ?search_img <query>)
    ?zen - Zen mode (Usage: ?zen <user> <time.hh:mm:ss>)
    ?BServer - Ban a server (Usage: ?BServer <server_name>)
    ?UBServer - Unban a server (Usage: ?UBServer <server_name>)
    ?MServer - Manage server restrictions (Usage: ?MServer <server_name> / <restriction_level>)
    ?update - Update the bot (Admin only, Usage: ?update <version> / <new features>)
    ?unzen - Unzen a user (Admin only, Usage: ?unzen <user>)
    ?balance - Check your balance
    ?daily - Claim your daily reward
    ?steal - Steal money from another user (Usage: ?steal <user>)
    ?give - Give money to another user (Usage: ?give <user> <amount>)
    ?stealadmin - Steal money and bypassing any time limit (Usage: ?stealadmin <user> <receiveuser>) <amount>)
    ?wheel - Spin the wheel (Usage: ?wheel any)
    ?leaderboard - Show the leaderboard
    ?trivia - Play trivia (Usage: ?trivia <question> <answer1, answer2, ...>)
    ?reminder - Set a reminder (Usage: ?reminder <time> <message>)
    ?join - Join a voice channel (Usage: ?join <channel_name>)
    ?leave - Leave a voice channel (Usage: ?leave <channel_name>)
    ?mute - Mute a user (Usage: ?mute <user>)
    ?unmute - Unmute a user (Usage: ?unmute <user>)
    ?purge - Purge messages (Usage: ?purge <number_of_messages>)
    ?rps - Play Rock-Paper-Scissors (Usage: ?rps <choice>)
    ?setwelcome - Set a welcome channel (Usage: ?setwelcome <channel_name>)
    ?afk - Set yourself as AFK (Usage: ?afk <reason>)
    ?restart - Restart the bot (Admin only)
    """
    
    await ctx.send(help_message)
    await ctx.send(help_message2)

# Configure logging
logging.basicConfig(level=logging.INFO)  # Change to DEBUG for more detailed logs
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)  # Enable debug-level logging for Discord events

# Zen mode: idea is whenever a people executes the command, 
# They will be timed out and won't see any messages for a custom set of time.
# This is a temporary timeout, so it will be removed after the time is up.
# This command can be used by everyone including themselves.
# THE TIME IS DIVIDED IN 3 PARTS:
# hh:mm:ss
# (Only an admin can unzen them)
# Command: Zen Mode
@bot.command(name="zen")
async def zen(ctx, member: discord.Member = None, time: str = None):
    """Put a user in Zen mode (timeout) for a specified duration."""
    if member is None:
        member = ctx.author  # If no member is mentioned, use the command author
    if time is None:
        await ctx.send("❌ Please provide a time in the format `hh:mm:ss`.")
        return

    # Parse the time string into hours, minutes, and seconds
    try:
        hours, minutes, seconds = map(int, time.split(":"))
        total_seconds = hours * 3600 + minutes * 60 + seconds
    except ValueError:
        await ctx.send("❌ Invalid time format. Use `hh:mm:ss`.")
        return

    # Check if the bot has permission to timeout members
    if not ctx.guild.me.guild_permissions.moderate_members:
        await ctx.send("❌ I do not have permission to timeout members.")
        return

    # Apply the timeout
    try:
        # Use the `timedelta` to calculate the timeout duration
        timeout_until = discord.utils.utcnow() + timedelta(seconds=total_seconds)
        await member.edit(timed_out_until=timeout_until)  # Correct method to apply timeout
        await ctx.send(f"✅ {member.mention} has been put in Zen mode for {time}.")
    except discord.Forbidden:
        await ctx.send("❌ I do not have permission to timeout this member.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")

# Command: Unzen (Admin only)
@bot.command(name="unzen")
@commands.has_permissions(administrator=True)
async def unzen(ctx, member: discord.Member):
    """Remove Zen mode (timeout) from a user."""
    try:
        await member.timeout(until=None)  # Remove the timeout
        await ctx.send(f"✅ {member.mention} has been removed from Zen mode.")
    except discord.Forbidden:
        await ctx.send("❌ I do not have permission to remove the timeout.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")
# timeout command
@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, time: int, *, reason: str = None):
    if reason is None:
        reason = "No reason provided"

    # Create a timeout role if it doesn't exist
    timeout_role = discord.utils.get(ctx.guild.roles, name="Timeout")
    if not timeout_role:
        timeout_role = await ctx.guild.create_role(name="Timeout")
        for channel in ctx.guild.channels:
            await channel.set_permissions(timeout_role, send_messages=False, speak=False)

    # Add the timeout role to the member
    await member.add_roles(timeout_role, reason=reason)
    await ctx.send(f"✅ {member.mention} has been put in timeout for {time} seconds. Reason: {reason}")

    # Wait for the specified time and remove the role
    await asyncio.sleep(time)
    await member.remove_roles(timeout_role, reason="Timeout expired")
    await ctx.send(f"✅ {member.mention} has been removed from timeout.")

game_ongoing = False

def get_truth_or_dare_vc(guild):
    return discord.utils.get(guild.voice_channels, name="truth-or-dare")

# Function to get the Truth or Dare text channel
def get_truth_or_dare_text_channel(guild):
    return discord.utils.get(guild.text_channels, name="truth-or-dare")

def assign_numbers_to_players(members):
    player_numbers = {member.display_name: index + 1 for index, member in enumerate(members)}
    return player_numbers

def game_logic(ctx):
    vc_channel = get_truth_or_dare_vc(ctx.guild)
    text_channel = get_truth_or_dare_text_channel(ctx.guild)
    members_in_vc = [member for member in vc_channel.members if not member.bot]
    player_numbers = assign_numbers_to_players(members_in_vc)
    player_names = ', '.join(f"{name} ({number})" for name, number in player_numbers.items())
    ctx.send(f"Players: {player_numbers}")
    return player_names

# ?startgame command
@bot.command(name="startgame")
@commands.has_permissions(administrator=True)
async def startgame(ctx):
    global game_ongoing
    if game_ongoing:
        await ctx.send("A game is already ongoing!")
        return

    vc_channel = get_truth_or_dare_vc(ctx.guild)
    text_channel = get_truth_or_dare_text_channel(ctx.guild)

    if not vc_channel or not text_channel:
        await ctx.send("Truth or Dare voice or text channel not found!")
        return


    members_in_vc = [member for member in vc_channel.members if not member.bot]
    if not members_in_vc:
        await ctx.send("No members in the Truth or Dare voice channel!")
        return
    if len(members_in_vc) > 3:
        await ctx.send("Cannot start game with more the 2 members!")
        return
    if len(members_in_vc) < 2:
        await ctx.send("Cannot start game with less than 2 members!")
        return
    player_names = ', '.join(member.display_name for member in members_in_vc)
    player_usernames = ', '.join(member.mention for member in members_in_vc)

    game_ongoing = True
    await text_channel.send(f"Starting Truth or Dare game! '({player_names}) Use `?continue` to proceed with the game.")
    game_logic(ctx)
    await ctx.send("Game started!")

# ?startgamenovc command
@bot.command(name="startgamenovc")
@commands.has_permissions(administrator=True)
async def startgame(ctx,  member: discord.Member = None,  member2: discord.Member = None):
    global game_ongoing
    if member is None:
        member = ctx.author
        ctx.send(f"You didnt mention any member so we chose you ({member}, by default)")
    if member2 is None:
        member2 = ctx.author
        if member2 == member:
            ctx.send("You cannot choose the same member twice!")
            return
        ctx.send(f"You didnt mention any member so we chose you ({member2}, by default)")
    if game_ongoing:
        await ctx.send("A game is already ongoing!")
        return
    player_names = [member, member2]
    
    text_channel = get_truth_or_dare_text_channel(ctx.guild)

    if not text_channel:
        await ctx.send("Truth or Dare text channel not found!")
        return
    game_ongoing = True
    text_channel.send(f"Starting Truth or Dare game! '({player_names}) Use `?continue` to proceed with the game.")
    game_logic(ctx)
    await ctx.send("Game started!")

# ?continue command
@bot.command(name="continue")
async def continue_game(ctx):
    global game_ongoing
    if not game_ongoing:
        await ctx.send("No game is currently ongoing!")
        return

    text_channel = get_truth_or_dare_text_channel(ctx.guild)
    if ctx.channel != text_channel:
        await ctx.send(f"Please use the `?continue` command in the {text_channel.mention} channel.")
        return

    game_logic(ctx)
    await text_channel.send("It's your turn! Choose Truth or Dare.")

# ?endgame command
@bot.command(name="endgame")
async def endgame(ctx):
    global game_ongoing
    if not game_ongoing:
        await ctx.send("No game is currently ongoing!")
        return

    game_ongoing = False
    text_channel = get_truth_or_dare_text_channel(ctx.guild)
    await text_channel.send("The Truth or Dare game has ended.")
    await ctx.send("Game ended!")

# ?checkvc command
@bot.command(name="checkvc")
async def checkvc(ctx):
    vc_channel = get_truth_or_dare_vc(ctx.guild)
    if not vc_channel:
        await ctx.send("Truth or Dare voice channel not found!")
        return

    members_in_vc = [member for member in vc_channel.members if not member.bot]
    if members_in_vc:
        await ctx.send(f"Members in the Truth or Dare voice channel: {', '.join(member.mention for member in members_in_vc)}")
    else:
        await ctx.send("No members in the Truth or Dare voice channel.")

@bot.command()
@commands.has_permissions(manage_roles=True)  # Ensure the user has the required permissions
async def createrole(ctx, name: str, power: str, color: str):
    """Create a role with a specified name, power level, and color."""
    # Map power levels to Discord permissions
    permissions_map = {
        "member": discord.Permissions(permissions=0),  # No special permissions
        "mod": discord.Permissions(manage_messages=True, kick_members=True),
        "admin": discord.Permissions(administrator=True)
    }

    # Validate power level
    if power.lower() not in permissions_map:
        print(f"Create role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Invalid power level.")
        await ctx.send("❌ Invalid power level. Use `member`, `mod`, or `admin`.")
        return

    # Validate color
    try:
        color = discord.Color(int(color.lstrip("#"), 16))  # Convert hex color to Discord.Color
    except ValueError:
        print(f"Create role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Invalid color.")
        await ctx.send("❌ Invalid color. Please provide a valid hex color (e.g., `#FF5733`).")
        return

    # Create the role
    try:
        role = await ctx.guild.create_role(
            name=name,
            permissions=permissions_map[power.lower()],
            color=color,
            reason=f"Role created by {ctx.author}"
        )
        print(f"Create role command triggered by {ctx.author} in channel {ctx.channel}. State: success.")
        await ctx.send(f"✅ Role **{role.name}** created successfully!")
        logs_channel = get_logs_channel(ctx.guild)
        if logs_channel:
            await logs_channel.send(f"Role **{role.name}** created by {ctx.author}")
    except discord.Forbidden:
        print(f"Create role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Forbidden.")
        await ctx.send("❌ I do not have permission to create roles.")
    except Exception as e:
        print(f"Create role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: {e}")
        await ctx.send(f"❌ An error occurred: {e}")

@bot.command()
@commands.has_permissions(manage_roles=True)  # Ensure the user has the required permissions
async def giverole(ctx, role_name: str, member: discord.Member):
    """Assign a role to a specified user."""
    # Find the role in the server
    role = discord.utils.find(lambda r: r.name == role_name, ctx.guild.roles)
    
    if role is None:
        print(f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Role not found.")
        await ctx.send(f"❌ Role **{role_name}** not found in this server.")
        return

    # Check if the bot has permission to assign this role
    if ctx.guild.me.top_role <= role:
        print(f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Insufficient permissions.")
        await ctx.send("❌ I cannot assign this role because it is higher or equal to my highest role.")
        return

    # Assign the role
    try:
        await member.add_roles(role, reason=f"Role assigned by {ctx.author}")
        print(f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: success.")
        await ctx.send(f"✅ Role **{role.name}** assigned to {member.mention} successfully!")
        if role in member.roles:
            print(f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Role already assigned.")
            await ctx.send(f":grey_question: {member.mention} already has the **{role.name}** role.")
        return
    except discord.Forbidden:
        print(f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Forbidden.")
        await ctx.send("❌ I do not have permission to assign this role.")
    except Exception as e:
        print(f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: {e}")
        await ctx.send(f"❌ An error occurred: {e}")

# Command: Remove Role
@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"✅ Removed role **{role.name}** from {member.mention}.")
    else:
        await ctx.send(f"❌ {member.mention} does not have the role **{role.name}**.")

# Updated ?info command to use dynamic data
@bot.command()
async def info(ctx):
    custominfo = f"""I am a multifunctional Discord bot, here to assist you!
    Status: Unstable build
    Version: {bot_info['version']}
    Owner: smiley_unsmiley
    New stuff: {bot_info['new_stuff']}
    """
    await ctx.send(custominfo)


@bot.command()
async def analyse(ctx, member: discord.Member = None):
    """Analyse un utilisateur mentionné ou l'utilisateur qui exécute la commande."""
    if member is None:
        member = ctx.author  # Si aucun membre n'est mentionné, analyser l'auteur de la commande

    embed = discord.Embed(
        title=f"Analyse de {member.name}",
        description=f"Voici les détails de l'utilisateur {member.mention}",
        color=discord.Color.green()
    )

    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
    embed.add_field(name="Nom complet", value=f"{member.name}#{member.discriminator}", inline=False)
    embed.add_field(name="ID", value=member.id, inline=False)
    embed.add_field(name="Statut", value=member.status, inline=False)
    embed.add_field(name="Créé le", value=member.created_at.strftime("%d %B %Y, %H:%M:%S"), inline=False)
    embed.add_field(name="A rejoint le serveur", value=member.joined_at.strftime("%d %B %Y, %H:%M:%S"), inline=False)
    embed.add_field(name="Rôles", value=", ".join([role.name for role in member.roles if role.name != "@everyone"]), inline=False)
    
    print(f"Analyse command triggered by {ctx.author} in channel {ctx.channel}. State: success.")
    await ctx.send(embed=embed)

# ?serverinfo command
@bot.command()
async def serverinfo(ctx):
    server = ctx.guild
    server_info = (
        f"Server Name: {server.name}\n"
        f"Member Count: {server.member_count}\n"
        f"Created At: {server.created_at.strftime('%Y-%m-%d')}\n"
    )
    print(f"Server info command triggered by {ctx.author} in channel {ctx.channel}. State: success.")
    await ctx.send(server_info)

# ?shutdown command
@bot.command()
@commands.has_permissions(administrator=True)
async def shutdown(ctx):
    await ctx.send("Shutting down...")
    print(f"Shutdown command triggered by {ctx.author} in channel {ctx.channel}. State: success.")
    await ctx.send("✅ The bot has successfully shut down.")
    await bot.close()

# ?start command
@bot.command()
@commands.has_permissions(administrator=True)
async def start(ctx):
    print(f"Start command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Bot already running.")
    await ctx.send("The bot is already running!")

# ?poll command
@bot.command(name="poll")
async def poll(ctx, question: str, *options):
    """Create a poll with a time limit."""
    if len(options) < 2:
        await ctx.send("❌ You need at least two options to create a poll.")
        return

    embed = discord.Embed(title=question, description="React to vote!")
    reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for i, option in enumerate(options):
        embed.add_field(name=f"Option {i+1}", value=option, inline=False)

    poll_message = await ctx.send(embed=embed)

    for i in range(len(options)):
        await poll_message.add_reaction(reactions[i])

    await asyncio.sleep(30)  # Wait for 30 seconds
    poll_message = await ctx.channel.fetch_message(poll_message.id)
    results = {reaction.emoji: reaction.count - 1 for reaction in poll_message.reactions}
    winner = max(results, key=results.get)
    await ctx.send(f"🏆 The winning option is: {winner}")

# ?chat command (ChatGPT integration)
@bot.command()
async def chat(ctx, *, message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message}]
        )
        reply = response['choices'][0]['message']['content']
        print(f"chat command triggered by {ctx.author} in channel {ctx.channel}. State: success.")
        await ctx.send(reply)
    except Exception as e:
        print(f"chat command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: {e}")
        await ctx.send(f"Error: {e}")

@bot.event
async def on_command_error(ctx, error):
    # Check if the error is a "CommandNotFound" error
    if isinstance(error, commands.CommandNotFound):
        print(f"{ctx.author} Tried to use a command in {ctx.channel}. Error: command not found.")
        await ctx.send("❌ That command does not exist. Use `?help` to see the list of available commands.")
    # Handle other errors (optional)
    else:
        print(f"{ctx.author} Tried to use a command in {ctx.channel}. Error: {error}")
        await ctx.send("❌ An error occurred while processing your command. Please try again.")

# Dictionary to track users and their message activity
user_message_counts = {}

# Command: Warn user
@bot.command()
@commands.has_permissions(manage_roles=True)
async def warn(ctx, member: discord.Member, *, reason=None):
    user_id = str(member.id)
    if user_id not in warnings_data:
        warnings_data[user_id] = {"messages": [], "warnings": 0}

    warnings_data[user_id]["warnings"] += 1
    save_warnings_data()

    await ctx.send(f"✅ {member.mention} has been warned. Total warnings: {warnings_data[user_id]['warnings']}")
    logs_channel = get_logs_channel(ctx.guild)
    if logs_channel:
        await logs_channel.send(f"{ctx.author} warned {member.mention} in {ctx.channel}. Reason: {reason}. Total warnings: {warnings_data[user_id]['warnings']}")

    # Mute the user if they reach 5 warnings
    if warnings_data[user_id]["warnings"] >= 5:
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False)
        await member.add_roles(mute_role)
        await ctx.send(f"{member.mention} has been muted for 10 minutes due to excessive warnings.")
        if logs_channel:
            await logs_channel.send(f"{member.mention} has been muted for 10 minutes due to excessive warnings.")
        await asyncio.sleep(600)  # 10 minutes
        await member.remove_roles(mute_role)
        await ctx.send(f"{member.mention} has been unmuted.")
        if logs_channel:
            await logs_channel.send(f"{member.mention} has been unmuted.")

# Kick command
@bot.command()
async def kick(ctx, member: discord.Member, *, reason=None):
    if reason is None:
        reason = "No reason provided"
    
    await member.kick(reason=reason)
    print(f"{ctx.author} Kicked {ctx.member} in channel {ctx.channel}. Reason: {reason}.")
    await ctx.send(f"✅{member.mention} has successfully been kicked for: {reason}")

# Ban command
@bot.command()
async def ban(ctx, member: discord.Member, *, reason=None):
    if reason is None:
        reason = "No reason provided"
    
    await member.ban(reason=reason)
    print(f"{ctx.author} Banned {ctx.member} in channel {ctx.channel}. Reason: {reason}.")
    await ctx.send(f"✅{member.mention} has successfully been banned for: {reason}")

# Command: Give XP
@bot.command()
@commands.has_permissions(administrator=True)
async def givexp(ctx, member: discord.Member, xp: int):
    user_id = str(member.id)
    if user_id not in user_data:
        user_data[user_id] = {"xp": 0, "level": 1}

    user_data[user_id]["xp"] += xp
    await ctx.send(f"✅ Gave {xp} XP to {member.mention}.")
    save_user_data()

# Command: Gain Level
@bot.command()
@commands.has_permissions(administrator=True)
async def gainlvl(ctx, member: discord.Member):
    user_id = str(member.id)
    if user_id not in user_data:
        user_data[user_id] = {"xp": 0, "level": 1}

    user_data[user_id]["level"] += 1
    await ctx.send(f"✅ {member.mention} has gained a level.")
    save_user_data()

# Command: Copy text to a specific channel
@bot.command()
@commands.has_permissions(administrator=True)
async def copychannel(ctx, channel: discord.TextChannel, *, text: str):
    try:
        await channel.send(f"{text}")
        await ctx.send(f"✅ Sent the message to {channel.mention}.")
    except discord.Forbidden:
        await ctx.send(f"❌ I cannot send messages to {channel.mention}.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")

# Command: Color Role
@bot.command()
async def colorrole(ctx):
    message = await ctx.send(
        "Which color do you want?\n"
        "React with:\n"
        "🔴 for Red\n"
        "🟠 for Orange\n"
        "🟡 for Yellow\n"
        "🟢 for Green\n"
        "🌲 for Dark Green\n"
        "🔵 for Light Blue\n"
        "🔷 for Blue\n"
        "🔹 for Dark Blue\n"
        "🟣 for Violet\n"
        "🌸 for Pink\n"
        "⚪ for White\n"
        "⚫ for Black\n"
        "🟤 for Brown"
    )
    reactions = ["🔴", "🟠", "🟡", "🟢", "🌲", "🔵", "🔷", "🔹", "🟣", "🌸", "⚪", "⚫", "🟤"]
    for reaction in reactions:
        await message.add_reaction(reaction)

# Event: On reaction add
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member is None:
        member = await guild.fetch_member(payload.user_id)
    emoji = str(payload.emoji)

    role_name = None
    if emoji == "🔴":
        role_name = "Red"
    elif emoji == "🟠":
        role_name = "Orange"
    elif emoji == "🟡":
        role_name = "Yellow"
    elif emoji == "🟢":
        role_name = "Green"
    elif emoji == "🌲":
        role_name = "Dark Green"
    elif emoji == "🔵":
        role_name = "Light Blue"
    elif emoji == "🔷":
        role_name = "Blue"
    elif emoji == "🔹":
        role_name = "Dark Blue"
    elif emoji == "🟣":
        role_name = "Violet"
    elif emoji == "🌸":
        role_name = "Pink"
    elif emoji == "⚪":
        role_name = "White"
    elif emoji == "⚫":
        role_name = "Black"
    elif emoji == "🟤":
        role_name = "Brown"
    elif emoji == "🇺🇸":
        role_name = "United States 🇺🇸"
    elif emoji == "🇨🇦":
        role_name = "Canada 🇨🇦"
    elif emoji == "🇬🇧":
        role_name = "United Kingdom 🇬🇧"
    elif emoji == "🇦🇺":
        role_name = "Australia 🇦🇺"
    elif emoji == "🇮🇳":
        role_name = "India 🇮🇳"
    elif emoji == "🇩🇪":
        role_name = "Germany 🇩🇪"
    elif emoji == "🇫🇷":
        role_name = "France 🇫🇷"
    elif emoji == "🇯🇵":
        role_name = "Japan 🇯🇵"
    elif emoji == "🇰🇷":
        role_name = "South Korea 🇰🇷"
    elif emoji == "🇧🇷":
        role_name = "Brazil 🇧🇷"

    if role_name:
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            role = await guild.create_role(name=role_name)
        await member.add_roles(role)
        await member.send(f"You have been given the {role_name} role.")

# Event: On reaction remove (optional, to remove the role when the reaction is removed)
@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member is None:
        member = await guild.fetch_member(payload.user_id)
    emoji = str(payload.emoji)

    role_name = None
    if emoji == "🔴":
        role_name = "Red"
    elif emoji == "🟠":
        role_name = "Orange"
    elif emoji == "🟡":
        role_name = "Yellow"
    elif emoji == "🟢":
        role_name = "Green"
    elif emoji == "🌲":
        role_name = "Dark Green"
    elif emoji == "🔵":
        role_name = "Light Blue"
    elif emoji == "🔷":
        role_name = "Blue"
    elif emoji == "🔹":
        role_name = "Dark Blue"
    elif emoji == "🟣":
        role_name = "Violet"
    elif emoji == "🌸":
        role_name = "Pink"
    elif emoji == "⚪":
        role_name = "White"
    elif emoji == "⚫":
        role_name = "Black"
    elif emoji == "🟤":
        role_name = "Brown"
    elif emoji == "🇺🇸":
        role_name = "United States 🇺🇸"
    elif emoji == "🇨🇦":
        role_name = "Canada 🇨🇦"
    elif emoji == "🇬🇧":
        role_name = "United Kingdom 🇬🇧"
    elif emoji == "🇦🇺":
        role_name = "Australia 🇦🇺"
    elif emoji == "🇮🇳":
        role_name = "India 🇮🇳"
    elif emoji == "🇩🇪":
        role_name = "Germany 🇩🇪"
    elif emoji == "🇫🇷":
        role_name = "France 🇫🇷"
    elif emoji == "🇯🇵":
        role_name = "Japan 🇯🇵"
    elif emoji == "🇰🇷":
        role_name = "South Korea 🇰🇷"
    elif emoji == "🇧🇷":
        role_name = "Brazil 🇧🇷"

    if role_name:
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            await member.remove_roles(role)
            await member.send(f"The {role_name} role has been removed from you.")

@bot.command(name="daily")
async def daily(ctx):
    user_id = str(ctx.author.id)
    current_time = datetime.utcnow()

    # Initialize user data if not present
    if user_id not in money_data:
        money_data[user_id] = {"balance": 0, "last_daily": None}

    # Check if the user has already claimed their daily reward
    last_daily = money_data[user_id]["last_daily"]
    if last_daily:
        last_daily_time = datetime.strptime(last_daily, "%Y-%m-%d %H:%M:%S")
        if (current_time - last_daily_time).days < 1:
            await ctx.send("❌ You have already claimed your daily reward. Try again tomorrow!")
            return

    # Give daily reward
    reward = 100  # Amount of daily reward
    money_data[user_id]["balance"] += reward
    money_data[user_id]["last_daily"] = current_time.strftime("%Y-%m-%d %H:%M:%S")
    save_money_data()

    await ctx.send(f"✅ You have claimed your daily reward of {reward} coins! Your new balance is {money_data[user_id]['balance']} coins.")

@bot.command(name="balance")
async def balance(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    user_id = str(member.id)
    balance = money_data.get(user_id, {}).get("balance", 0)
    await ctx.send(f"💰 {member.mention} has {balance} coins.")

@bot.command(name="steal")
async def steal(ctx, target: discord.Member):
    if target == ctx.author:
        await ctx.send("❌ You cannot steal from yourself!")
        return

    user_id = str(ctx.author.id)
    target_id = str(target.id)

    # Ensure both users have balances
    if user_id not in money_data:
        money_data[user_id] = {"balance": 0, "last_daily": None}
    if target_id not in money_data:
        money_data[target_id] = {"balance": 0, "last_daily": None}

    # Check if the target has enough money to steal
    if money_data[target_id]["balance"] < 50:
        await ctx.send(f"❌ {target.mention} does not have enough coins to steal from!")
        return

    # Guess game
    number_to_guess = random.randint(1, 10)
    await ctx.send(f"🎲 Guess a number between 1 and 10 to steal from {target.mention}. You have 1 attempt!")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

    try:
        guess = await bot.wait_for("message", check=check, timeout=15.0)
        if int(guess.content) == number_to_guess:
            stolen_amount = random.randint(20, 50)
            money_data[user_id]["balance"] += stolen_amount
            money_data[target_id]["balance"] -= stolen_amount
            save_money_data()
            await ctx.send(f"✅ You guessed correctly and stole {stolen_amount} coins from {target.mention}!")
        else:
            await ctx.send(f"❌ Wrong guess! The correct number was {number_to_guess}. Better luck next time!")
    except asyncio.TimeoutError:
        await ctx.send("⏰ You took too long to respond! The stealing attempt failed.")

@bot.command(name="give")
@commands.has_permissions(administrator=True)
async def give(ctx, member: discord.Member, amount: int):
    """Give coins to a user (Admin only)."""
    if amount <= 0:
        await ctx.send("❌ The amount must be greater than 0.")
        return

    user_id = str(member.id)

    # Ensure the user has a balance entry
    if user_id not in money_data:
        money_data[user_id] = {"balance": 0, "last_daily": None}

    # Add the amount to the user's balance
    money_data[user_id]["balance"] += amount
    save_money_data()

    await ctx.send(f"✅ {amount} coins have been given to {member.mention}. Their new balance is {money_data[user_id]['balance']} coins.")

@bot.command(name="stealadmin")
@commands.has_permissions(administrator=True)
async def stealadmin(ctx, target: discord.Member, recipient: discord.Member, amount: int):
    """Steal coins from one user and give them to another (Admin only)."""
    if amount <= 0:
        await ctx.send("❌ The amount must be greater than 0.")
        return

    target_id = str(target.id)
    recipient_id = str(recipient.id)

    # Ensure both users have balance entries
    if target_id not in money_data:
        money_data[target_id] = {"balance": 0, "last_daily": None}
    if recipient_id not in money_data:
        money_data[recipient_id] = {"balance": 0, "last_daily": None}

    # Check if the target has enough coins
    if money_data[target_id]["balance"] < amount:
        await ctx.send(f"❌ {target.mention} does not have enough coins to steal!")
        return

    # Transfer the coins
    money_data[target_id]["balance"] -= amount
    money_data[recipient_id]["balance"] += amount
    save_money_data()

    await ctx.send(f"✅ {amount} coins have been stolen from {target.mention} and given to {recipient.mention}.")

@bot.command(name="wheel")
async def wheel(ctx, *, names: str):
    """Spin a wheel of names and pick one randomly."""
    # Split the input into a list of names
    name_list = [name.strip() for name in names.split("/") if name.strip()]

    # Check if there are at least two names
    if len(name_list) < 2:
        await ctx.send("❌ You need at least two names to spin the wheel. Use the format: `?wheel name1 / name2 / name3`.")
        return

    # Simulate spinning the wheel
    await ctx.send("🎡 Spinning the wheel...")
    await asyncio.sleep(2)  # Add a delay for effect

    # Pick a random name
    chosen_name = random.choice(name_list)
    await ctx.send(f"🎉 The wheel has chosen: **{chosen_name}**!")

@bot.command(name="leaderboard")
async def leaderboard(ctx):
    """Display the top users based on their balance."""
    sorted_users = sorted(money_data.items(), key=lambda x: x[1]["balance"], reverse=True)
    leaderboard_message = "🏆 **Leaderboard** 🏆\n"
    for i, (user_id, data) in enumerate(sorted_users[:10], start=1):
        user = await bot.fetch_user(int(user_id))
        leaderboard_message += f"{i}. {user.name} - {data['balance']} coins\n"
    await ctx.send(leaderboard_message)

@bot.command(name="trivia")
async def trivia(ctx):
    """Start a trivia game."""
    questions = {
        "What is the capital of France?": "Paris",
        "What is 757.124964164? + 64565*(6454/15)": "27799991.524964165",
        "Who wrote 'To Kill a Mockingbird'?": "Harper Lee",
        "What is the largest planet in our solar system?": "Jupiter",
        "What is the chemical symbol for gold?": "Au",
        "What is the smallest prime number?": "2",
        "Who painted the Mona Lisa?": "Leonardo da Vinci",
        "What is the largest mammal?": "Blue Whale",
        "What is the capital of Japan?": "Tokyo",
        "What is the hardest natural substance on Earth?": "Diamond",
        "What is the main ingredient in guacamole?": "Avocado",
        "What is the longest river in the world?": "Nile",
        "What is the largest desert in the world?": "Sahara",
        "What is the speed of light?": "299792458 m/s",
        "What is the boiling point of water?": "100°C",
        "What is the largest ocean on Earth?": "Pacific Ocean",
        "What is the most spoken language in the world?": "Mandarin Chinese",
        "What is the capital of Canada?": "Ottawa",
        "What is the currency of Japan?": "Yen",
        "What is the tallest mountain in the world?": "Mount Everest",
        "What is the largest continent?": "Asia",
        "What is the main ingredient in sushi?": "Rice",
        "What is the capital of Italy?": "Rome",
        "What is the largest country in the world?": "Russia",
        "What is the most populous country?": "China",
        "What is the capital of Australia?": "Canberra",
        "What is the largest island in the world?": "Greenland",
        "What is the main ingredient in hummus?": "Chickpeas",
        "What is the capital of Germany?": "Berlin",
        "What is the largest volcano in the world?": "Mauna Loa",
        "What is the chemical symbol for silver?": "Ag",
        "What is the largest city in the world?": "Tokyo",
        "What is the main ingredient in chocolate?": "Cocoa",
        "What is the capital of Spain?": "Madrid",
        "What is the largest lake in the world?": "Caspian Sea",
        "What is the main ingredient in bread?": "Flour",
        "What is the capital of Russia?": "Moscow",
        "What is the largest animal on land?": "African Elephant",
        "What is the main ingredient in pizza?": "Dough",
        "What is the capital of Egypt?": "Cairo",
        "What is the largest city in the USA?": "New York City",
        "What is the main ingredient in curry?": "Spices",
        "What is the capital of Brazil?": "Brasilia",
        "What is the largest organ in the human body?": "Skin",
        "What is the main ingredient in pancakes?": "Flour",
        "What is the capital of India?": "New Delhi",
        "What is the largest city in Canada?": "Toronto",
        "What is the main ingredient in salad?": "Vegetables",
        "What is the capital of Mexico?": "Mexico City",
        "What is the largest city in Australia?": "Sydney",
        "What is the main ingredient in soup?": "Broth",
        "What is the capital of Argentina?": "Buenos Aires",
        "What is the largest city in Europe?": "Moscow",
        "What is the main ingredient in ice cream?": "Cream",
        "What is the capital of South Africa?": "Pretoria",
        "What is the main ingredient in cheese?": "Milk",
        "What is the capital of Turkey?": "Ankara",
        "What is the main ingredient in jelly?": "Fruit",
        "What is the capital of Thailand?": "Bangkok",
        "What is the main ingredient in mayonnaise?": "Eggs",
        "What is the capital of Greece?": "Athens",
        "What is the main ingredient in ketchup?": "Tomatoes",
        "What is the capital of Portugal?": "Lisbon",
        "What is the main ingredient in mustard?": "Mustard seeds",
        "What is the capital of Sweden?": "Stockholm",
        "What is the main ingredient in salsa?": "Tomatoes",
        "What is the capital of Norway?": "Oslo",
        "What is the main ingredient in pesto?": "Basil",
        "What is the capital of Denmark?": "Copenhagen",
        "What is the main ingredient in guacamole?": "Avocado",
        "What is the capital of Finland?": "Helsinki",
        "What is the main ingredient in tzatziki?": "Yogurt",
        "What is the capital of Hungary?": "Budapest",
        "What is the main ingredient in hummus?": "Chickpeas",
        "What is the capital of Czech Republic?": "Prague",
        "What is the main ingredient in falafel?": "Chickpeas",
        "What is the capital of Slovakia?": "Bratislava",
        "What is the main ingredient in tabbouleh?": "Bulgur",
        "What is the capital of Romania?": "Bucharest",
        "What is the main ingredient in moussaka?": "Eggplant",
        "What is the capital of Bulgaria?": "Sofia",
        "What is the main ingredient in baklava?": "Phyllo dough",
        "What is the capital of Serbia?": "Belgrade",
        "What is the main ingredient in goulash?": "Beef",
        "What is the capital of Croatia?": "Zagreb",
        "What is the chemical symbol for iron?": "Fe",
        "What is the main ingredient in paella?": "Rice",
        "What is the capital of Slovenia?": "Ljubljana",
        "What is the main ingredient in risotto?": "Rice",
        "What is the capital of Bosnia and Herzegovina?": "Sarajevo",
        "What is the main ingredient in borscht?": "Beets",
        "What is the capital of Montenegro?": "Podgorica",
        "What is the main ingredient in cevapi?": "Ground meat",
        "What is the capital of North Macedonia?": "Skopje",
        "What is the main ingredient in ajvar?": "Red peppers",
        "What is the capital of Albania?": "Tirana",
        "What is the main ingredient in sarma?": "Cabbage",
        "What is the capital of Kosovo?": "Pristina",
        "What is the main ingredient in burek?": "Phyllo dough",
        "What is the capital of Malta?": "Valletta",
        "What is the main ingredient in pastizzi?": "Ricotta",
        "What is the capital of Cyprus?": "Nicosia",
        "What is the main ingredient in halloumi?": "Cheese",
        "What is the capital of Luxembourg?": "Luxembourg City",
        "What is the main ingredient in quiche?": "Eggs",
        "What is the capital of Liechtenstein?": "Vaduz",
        "What is the main ingredient in fondue?": "Cheese",
        "What is the capital of Monaco?": "Monaco",
        "What is the main ingredient in ratatouille?": "Vegetables",
        "What is the capital of San Marino?": "San Marino",
        "What is the main ingredient in tiramisu?": "Coffee",
        "What is the capital of Vatican City?": "Vatican City",
        "What is the main ingredient in panna cotta?": "Cream",
        "What is the capital of Andorra?": "Andorra la Vella",
        "What is the main ingredient in churros?": "Dough",
        "What is the capital of Monaco?": "Monaco",
        "What is the main ingredient in croissants?": "Dough",
        "What is the capital of Gibraltar?": "Gibraltar",
        "What is the main ingredient in scones?": "Flour",
        "What is the capital of Bermuda?": "Hamilton",
        "What is the main ingredient in shortbread?": "Butter",
        "What is the capital of the Bahamas?": "Nassau",
        

    }
    question, answer = random.choice(list(questions.items()))
    await ctx.send(f"❓ {question}")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        response = await bot.wait_for("message", check=check, timeout=60.0)
        if response.content.lower() == answer.lower():
            reward = 50
            user_id = str(ctx.author.id)
            if user_id not in money_data:
                money_data[user_id] = {"balance": 0, "last_daily": None}
            money_data[user_id]["balance"] += reward
            save_money_data()
            await ctx.send(f"✅ Correct! You earned {reward} coins.")
        else:
            await ctx.send(f"❌ Wrong! The correct answer was **{answer}**.")
    except asyncio.TimeoutError:
        await ctx.send("⏰ Time's up! You didn't answer in time.")

@bot.command(name="reminder")
async def remindme(ctx, time: int, *, reminder: str):
    """Set a reminder."""
    await ctx.send(f"⏰ I will remind you in {time} seconds: {reminder}")
    await asyncio.sleep(time)
    await ctx.send(f"🔔 {ctx.author.mention}, here is your reminder: {reminder}")

@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    """Mute a user."""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False, speak=False)
    await member.add_roles(mute_role, reason=reason)
    await ctx.send(f"✅ {member.mention} has been muted. Reason: {reason}")

@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    """Unmute a user."""
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role in member.roles:
        await member.remove_roles(mute_role)
        await ctx.send(f"✅ {member.mention} has been unmuted.")
    else:
        await ctx.send(f"❌ {member.mention} is not muted.")

@bot.event
async def on_member_join(member):
    logs_channel = discord.utils.get(member.guild.text_channels, name="logs")
    if logs_channel:
        await logs_channel.send(f"✅ {member.mention} joined the server.")

@bot.event
async def on_member_remove(member):
    logs_channel = discord.utils.get(member.guild.text_channels, name="logs")
    if logs_channel:
        await logs_channel.send(f"❌ {member.mention} left the server.")

@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    """Delete a number of messages."""
    await ctx.channel.purge(limit=amount)
    await ctx.send(f"✅ Deleted {amount} messages.", delete_after=5)

@bot.command(name="rps")
async def rps(ctx, choice: str):
    """Play Rock-Paper-Scissors."""
    choices = ["rock", "paper", "scissors"]
    bot_choice = random.choice(choices)
    if choice not in choices:
        await ctx.send("❌ Invalid choice! Choose rock, paper, or scissors.")
        return
    if choice == bot_choice:
        result = "It's a tie!"
    elif (choice == "rock" and bot_choice == "scissors") or \
         (choice == "paper" and bot_choice == "rock") or \
         (choice == "scissors" and bot_choice == "paper"):
        result = "You win!"
    else:
        result = "You lose!"
    await ctx.send(f"🤖 I chose {bot_choice}. {result}")

welcome_messages = {}

@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def setwelcome(ctx, *, message: str):
    """Set a custom welcome message."""
    welcome_messages[str(ctx.guild.id)] = message
    await ctx.send("✅ Welcome message set!")

@bot.event
async def on_member_join(member):
    message = welcome_messages.get(str(member.guild.id), f"Welcome to the server, {member.mention}!")
    channel = discord.utils.get(member.guild.text_channels, name="welcome")
    if channel:
        await channel.send(message)

afk_users = {}

@bot.command(name="afk")
async def afk(ctx, *, reason="AFK"):
    """Set yourself as AFK."""
    afk_users[ctx.author.id] = reason
    await ctx.send(f"✅ {ctx.author.mention} is now AFK: {reason}")

@bot.event
async def on_message(message):
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(f"✅ Welcome back, {message.author.mention}!")
    for mention in message.mentions:
        if mention.id in afk_users:
            await message.channel.send(f"🔔 {mention.mention} is AFK: {afk_users[mention.id]}")
    await bot.process_commands(message)

@bot.event
async def on_message(message):
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(f"✅ Welcome back, {message.author.mention}!")
    for mention in message.mentions:
        if mention.id in afk_users:
            await message.channel.send(f"🔔 {mention.mention} is AFK: {afk_users[mention.id]}")
    await bot.process_commands(message)

@bot.command(name="restart")
@commands.has_permissions(administrator=True)
async def restart(ctx):
    """Restart the bot."""
    await ctx.send("🔄 Restarting the bot...")
    await bot.close()  # Close the bot connection
    os.execv(sys.executable, ["python", __file__, "--skip-input"])  # Restart the bot with the skip-input flag

@bot.command(name="tictactoe")
async def tictactoe(ctx, player1: discord.Member, player2: discord.Member):
    """Start a Tic-Tac-Toe game."""
    board = [" " for _ in range(9)]
    current_player = player1

    def print_board():
        return f"""
        {board[0]} | {board[1]} | {board[2]}
        ---------
        {board[3]} | {board[4]} | {board[5]}
        ---------
        {board[6]} | {board[7]} | {board[8]}
        """

    await ctx.send(f"Tic-Tac-Toe Game Started!\n{print_board()}")

    def check_winner():
        win_conditions = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
            [0, 4, 8], [2, 4, 6]             # Diagonals
        ]
        for condition in win_conditions:
            if board[condition[0]] == board[condition[1]] == board[condition[2]] != " ":
                return True
        return False

    for _ in range(9):
        await ctx.send(f"{current_player.mention}, it's your turn! Choose a position (1-9).")

        def check(m):
            return m.author == current_player and m.channel == ctx.channel and m.content.isdigit()

        try:
            move = await bot.wait_for("message", check=check, timeout=30.0)
            position = int(move.content) - 1
            if board[position] != " ":
                await ctx.send("❌ Invalid move. Try again.")
                continue
            board[position] = "X" if current_player == player1 else "O"
            if check_winner():
                await ctx.send(f"🎉 {current_player.mention} wins!\n{print_board()}")
                return
            current_player = player2 if current_player == player1 else player1
        except asyncio.TimeoutError:
            await ctx.send("⏰ Time's up! Game ended.")
            return

    await ctx.send(f"🤝 It's a tie!\n{print_board()}")

@bot.command(name="color")
async def color(ctx, *, color_input: str):
    """Display the exact color based on a name or hex code."""
    try:
        # Check if the input is a hex code
        if color_input.startswith("#"):
            # Convert the hex code to an integer and create a Discord color
            color_value = discord.Color(int(color_input.lstrip("#"), 16))
        else:
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
            if color_input.lower() not in color_names:
                await ctx.send("❌ Invalid color name or hex code. Please try again.")
                return
            color_value = discord.Color(int(color_names[color_input.lower()].lstrip("#"), 16))

        # Create an embed to display the color
        embed = discord.Embed(
            title="Color Preview",
            description=f"Here is the color for `{color_input}`.",
            color=color_value
        )
        embed.add_field(name="Hex Code", value=color_input if color_input.startswith("#") else color_names[color_input.lower()])
        embed.set_thumbnail(url=f"https://singlecolorimage.com/get/{color_value.value:06x}/400x400")
        await ctx.send(embed=embed)

    except ValueError:
        await ctx.send("❌ Invalid color input. Please provide a valid color name or hex code (e.g., `red` or `#FF0000`).")

@bot.command(name="delmoney")
@commands.has_permissions(administrator=True)
async def delmoney(ctx, member: discord.Member, amount: int):
    """Delete money from a user's balance (Admin only)."""
    if amount <= 0:
        await ctx.send("❌ The amount must be greater than 0.")
        return

    user_id = str(member.id)

    # Ensure the user has a balance entry
    if user_id not in money_data:
        money_data[user_id] = {"balance": 0, "last_daily": None}

    # Check if the user has enough money to delete
    if money_data[user_id]["balance"] < amount:
        await ctx.send(f"❌ {member.mention} does not have enough coins to delete {amount} coins.")
        return

    # Deduct the amount from the user's balance
    money_data[user_id]["balance"] -= amount
    save_money_data()

    await ctx.send(f"✅ {amount} coins have been deleted from {member.mention}'s balance. Their new balance is {money_data[user_id]['balance']} coins.")

try:
    with open("shared.json", "r") as f:
        shared_data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    shared_data = {}  # Initialize with an empty dictionary if the file is missing or invalid
    with open("shared.json", "w") as f:
        json.dump(shared_data, f)

# Track the last activity time
last_activity_time = datetime.utcnow()

# Update the last activity time on any command or message
@bot.event
async def on_message(message):
    global last_activity_time
    if message.author != bot.user:  # Ignore bot's own messages
        last_activity_time = datetime.utcnow()
    await bot.process_commands(message)  # Allow commands to be processed

@bot.event
async def on_command(ctx):
    global last_activity_time
    last_activity_time = datetime.utcnow()

# Background task to monitor inactivity
async def monitor_inactivity():
    global last_activity_time
    while True:
        await asyncio.sleep(60)  # Check every minute
        time_since_last_activity = (datetime.utcnow() - last_activity_time).total_seconds()
        if time_since_last_activity > 1200:  # 20 minutes = 1200 seconds
            logging.info("No activity detected for 20 minutes. Restarting the bot...")
            os.execv(sys.executable, ["python"] + sys.argv)  # Restart the bot

# Start the background task when the bot is ready
@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user}")
    bot.loop.create_task(monitor_inactivity())

@bot.command(name="game")
async def game(ctx, *, game_name: str):
    """Set yourself as gaming and deafen notifications."""
    user_id = str(ctx.author.id)

    # Ensure the user has an entry in user_data
    if user_id not in user_data:
        user_data[user_id] = {"xp": 0, "level": 1, "gaming": None}

    # Update the user's gaming status
    user_data[user_id]["gaming"] = game_name
    save_user_data()  # Save the updated user_data to the file

    await ctx.send(f"🎮 {ctx.author.mention} is now gaming on **{game_name}**. Notifications will be muted.")

    # Try to deafen the user (if in a voice channel)
    if ctx.author.voice:
        try:
            await ctx.author.edit(deafen=True)
            await ctx.send(f"🔇 {ctx.author.mention} has been deafened in their voice channel.")
        except discord.Forbidden:
            await ctx.send(f"❌ I do not have permission to deafen {ctx.author.mention}.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred while trying to deafen {ctx.author.mention}: {e}")

@bot.command(name="stopgame")
async def stopgame(ctx):
    """Stop gaming mode for yourself."""
    user_id = str(ctx.author.id)

    # Check if the user is gaming
    if user_id in user_data and user_data[user_id].get("gaming"):
        user_data[user_id]["gaming"] = None  # Clear the gaming status
        save_user_data()  # Save the updated user_data to the file

        await ctx.send(f"✅ {ctx.author.mention} is no longer gaming.")

        # Try to undeafen the user (if in a voice channel)
        if ctx.author.voice:
            try:
                await ctx.author.edit(deafen=False)
                await ctx.send(f"🔊 {ctx.author.mention} has been undeafened in their voice channel.")
            except discord.Forbidden:
                await ctx.send(f"❌ I do not have permission to undeafen {ctx.author.mention}.")
            except Exception as e:
                await ctx.send(f"❌ An error occurred while trying to undeafen {ctx.author.mention}: {e}")
    else:
        await ctx.send(f"❌ {ctx.author.mention}, you are not currently gaming.")

@bot.event
async def on_message(message):
    """Handle pings to gaming users."""
    if message.author.bot:
        return

    # Check if the message mentions a gaming user
    for mention in message.mentions:
        user_id = str(mention.id)
        if user_id in user_data and user_data[user_id].get("gaming"):
            game_name = user_data[user_id]["gaming"]
            await message.channel.send(f"⛔ {mention.mention} is currently gaming on **{game_name}**. Please try again later!")
            return

    await bot.process_commands(message)

if __name__ == "__main__":
    import argparse

    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-input", action="store_true", help="Skip input prompts for auto-restart")
    args = parser.parse_args()

    if not args.skip_input:
        inpwhen = input(str("Update?: "))
        if inpwhen == "yes":
            print(f"Current version: {bot_info['version']}")
            inpwhen2 = input(str("Version?: "))
            print(f"Updating to {inpwhen2} from {bot_info['version']}...")
            
            bot_info['version'] = inpwhen2
            save_bot_info()

            inpwhen2 = None
            print(f"Current new stuff: {bot_info['new_stuff']}")
            inpwhen2 = input(str("New stuff?: "))
            print(f"Updating new stuff to {inpwhen2} from {bot_info['new_stuff']}...")

            bot_info['new_stuff'] = inpwhen2
            save_bot_info()
            
        elif inpwhen == "no":
            print("Proceeding without update.")
        else:
            print("Error, try again later.")
            time.sleep(0.6)
            print("Proceeding without update.")

        inpwhen3 = input(str("Clear all data?: "))
        if inpwhen3 == "yes":
            print("Are you sure?")
            input()
            if input() == "yes":
                print("Deleting all data...")
            elif input() == "no":
                print("Proceeding...")
            else:
                print("Error, proceeding nonetheless.")

# Ensure the music folder exists
if not os.path.exists("music"):
    os.makedirs("music")

@bot.command(name="upload")
async def upload(ctx, *, url: str = None):
    """Allow users to upload .mp3 files or provide a URL to download."""
    if not ctx.message.attachments and not url:
        await ctx.send("❌ Please attach an audio file or provide a URL to upload.")
        return

    # Handle file attachments
    if ctx.message.attachments:
        for attachment in ctx.message.attachments:
            if attachment.filename.endswith((".mp3", ".wav", ".ogg")):
                file_path = os.path.join("music", attachment.filename)
                await attachment.save(file_path)
                await ctx.send(f"✅ File `{attachment.filename}` has been uploaded and saved.")
            else:
                await ctx.send(f"❌ `{attachment.filename}` is not a supported audio format. Please upload .mp3, .wav, or .ogg files.")

    # Handle URL input
    if url:
        if url.startswith("http://") or url.startswith("https://"):
            await ctx.send(f"🔍 Downloading from URL: `{url}`...")
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": "music/%(title)s.%(ext)s",
                "noplaylist": True,
            }
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    file_name = ydl.prepare_filename(info)
                    await ctx.send(f"✅ Downloaded `{info['title']}` and saved to the music folder.")
            except Exception as e:
                await ctx.send(f"❌ Failed to download from URL: {e}")
        else:
            await ctx.send("❌ Invalid URL. Please provide a valid URL starting with `http://` or `https://`.")

ffmpeg_path = r"C:\Users\roland\Downloads\ffmpeg-2025-03-31-git-35c091f4b7-full_build\bin\ffmpeg.exe"

@bot.command(name="play")
async def play(ctx, *, query: str = None):
    """Play a song from a URL or the music folder."""
    if not ctx.author.voice:
        await ctx.send("❌ You must be in a voice channel to use this command.")
        return

    voice_channel = ctx.author.voice.channel


    try:
        # Join the voice channel
        if ctx.voice_client is None:
            vc = await voice_channel.connect()
        else:
            vc = ctx.voice_client

        # Log FFmpeg path
        ffmpeg_path = "ffmpeg"  # Default to "ffmpeg" if it's in PATH
        logger.info(f"Using FFmpeg executable: {ffmpeg_path}")

        # If a query is provided, check if it's a URL
        if query:
            if query.startswith("http://") or query.startswith("https://"):
                await ctx.send(f"🔍 Searching for `{query}`...")
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": "music/%(title)s.%(ext)s",
                    "noplaylist": True,
                }
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(query, download=True)
                    song_path = ydl.prepare_filename(info)
                    await ctx.send(f"✅ Downloaded `{info['title']}`. Now playing...")
            else:
                # Assume the query is a local file name
                song_path = os.path.join("music", query)
                if not os.path.exists(song_path):
                    await ctx.send(f"❌ The file `{query}` does not exist in the music folder.")
                    return
                await ctx.send(f"🎵 Now playing: `{query}`")
        else:
            # Play the first song in the music folder
            songs = sorted(os.listdir("music"))
            if not songs:
                await ctx.send("❌ The music folder is empty. Upload some songs using `?upload` or provide a URL.")
                return
            song = songs[0]
            song_path = os.path.join("music", song)
            await ctx.send(f"🎵 Now playing: `{song}`")

        # Play the song
        vc.play(discord.FFmpegPCMAudio(song_path, executable=ffmpeg_path), after=lambda e: logger.info(f"Finished playing: {song_path}"))
    except Exception as e:
        logger.error(f"An error occurred in the play command: {e}")
        await ctx.send(f"❌ An error occurred: {e}")

@bot.command(name="queue")
async def queue(ctx):
    """List all songs in the music folder."""
    songs = sorted(os.listdir("music"))
    if not songs:
        await ctx.send("❌ The music folder is empty. Upload some songs using `?upload`.")
        return

    song_list = "\n".join(f"{i + 1}. {song}" for i, song in enumerate(songs))
    await ctx.send(f"🎶 **Music Queue:**\n{song_list}")

@bot.command(name="skip")
async def skip(ctx):
    """Skip the currently playing song."""
    if not ctx.voice_client or not ctx.voice_client.is_playing():
        await ctx.send("❌ No song is currently playing.")
        return

    ctx.voice_client.stop()
    await ctx.send("⏭️ Skipped the current song.")

@bot.command(name="stop")
async def stop(ctx):
    """Stop the music and disconnect the bot."""
    if not ctx.voice_client:
        await ctx.send("❌ The bot is not connected to a voice channel.")
        return

    await ctx.voice_client.disconnect()
    await ctx.send("⏹️ Stopped the music and disconnected.")

@bot.command(name="check_ffmpeg")
async def check_ffmpeg(ctx):
    """Check if FFmpeg is accessible."""
    try:
        import subprocess
        result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            await ctx.send(f"✅ FFmpeg is installed and accessible:\n```\n{result.stdout.splitlines()[0]}\n```")
            logger.info(f"FFmpeg is accessible: {result.stdout.splitlines()[0]}")
        else:
            await ctx.send("❌ FFmpeg is not accessible. Please check your installation.")
            logger.error(f"FFmpeg error: {result.stderr}")
    except FileNotFoundError:
        await ctx.send("❌ FFmpeg is not installed or not in PATH.")
        logger.error("FFmpeg executable not found.")

# Run the bot
bot.run(token)  # Replace with your actual bot token
shared_data == {"Connection: true"}
save_user_data()