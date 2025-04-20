import discord
from discord.ext import commands
from discord.ext.commands import CooldownMapping
from discord.ext.commands import BucketType
from yt_dlp import YoutubeDL
from discord import FFmpegPCMAudio
from googletrans import Translator
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import argparse
import os
import openai  # For ChatGPT functionality
import time
from transformers import pipeline
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
OPENWHEATHER_KEY = os.environ.get("OPENWEATHER_KEY")
openwheather = OPENWHEATHER_KEY

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

def get_balance(user_id):
    """Get the balance of a user."""
    data = load_user_data()
    if str(user_id) not in data:
        data[str(user_id)] = {"xp": 0, "level": 1, "coins": 100, "balance": 0, "warnings": []}
        save_user_data(data)
    return data[str(user_id)].get("balance", 0)

def update_balance(user_id, amount):
    """Update the balance of a user."""
    data = load_user_data()
    if str(user_id) not in data:
        data[str(user_id)] = {"xp": 0, "level": 1, "coins": 100, "balance": 0, "warnings": []}
    data[str(user_id)]["balance"] = data[str(user_id)].get("balance", 0) + amount
    save_user_data(data)

USER_DATA_FILE = "data/user_data.json"


def save_user_data(data):
    """Save user data to the JSON file."""
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)
        
def load_user_data():
    """Load user data from the JSON file."""
    if not os.path.exists(USER_DATA_FILE):
        return {}
    with open(USER_DATA_FILE, "r") as f:
        return json.load(f)

def get_user_data(user_id):
    """Get data for a specific user."""
    data = load_user_data()
    if str(user_id) not in data:
        # Initialize default values for new users
        data[str(user_id)] = {"xp": 0, "level": 1, "coins": 100, "balance": 0, "warnings": []}
        save_user_data(data)
    else:
        # Ensure all required keys exist for existing users
        user_data = data[str(user_id)]
        user_data.setdefault("xp", 0)
        user_data.setdefault("level", 1)
        user_data.setdefault("coins", 100)
        user_data.setdefault("balance", 0)
        user_data.setdefault("warnings", [])
        data[str(user_id)] = user_data
        save_user_data(data)
    return data[str(user_id)]

def update_user_data(user_id, key, value):
    """Update a specific field for a user."""
    data = load_user_data()
    if str(user_id) not in data:
        data[str(user_id)] = {"xp": 0, "level": 1, "coins": 100, "balance": 0, "warnings": []}
    data[str(user_id)][key] = value
    save_user_data(data)
    logging.info(f"Updated {key} for user {user_id}: {value}")

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

cooldown = CooldownMapping.from_cooldown(1, 10, BucketType.user)  # 1 message per 60 seconds

@bot.command(name="profile")
async def profile(ctx):
    """Check your XP, level, and coins."""
    user_id = ctx.author.id
    user_data = get_user_data(user_id)

    xp = user_data["xp"]
    level = user_data["level"]
    coins = user_data["coins"]

    await ctx.send(f"📜 **{ctx.author.name}'s Profile**:\n"
                   f"🔹 XP: {xp}\n"
                   f"🔹 Level: {level}\n"
                   f"🔹 Coins: {coins}")

@bot.command(name="buylevel")
async def buylevel(ctx, levels: int = 1):
    """Buy levels using coins."""
    if levels <= 0:
        await ctx.send("❌ You must buy at least 1 level.")
        return

    user_id = ctx.author.id
    user_data = get_user_data(user_id)

    cost = levels * 100  # Cost per level
    if user_data["coins"] < cost:
        await ctx.send(f"❌ You don't have enough coins. You need {cost} coins to buy {levels} level(s).")
        return

    # Deduct coins and increase levels
    user_data["coins"] -= cost
    user_data["level"] += levels
    update_user_data(user_id, "coins", user_data["coins"])
    update_user_data(user_id, "level", user_data["level"])

    await ctx.send(f"🎉 {ctx.author.mention} bought {levels} level(s) for {cost} coins! You are now **Level {user_data['level']}**.")

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

@bot.event
async def on_member_join(member):
    """Event triggered when a user joins the server."""
    try:
        # Log the event
        logging.info(f"New member joined: {member.name}#{member.discriminator} (ID: {member.id})")

        # Get the welcome channel
        welcome_channel = discord.utils.get(member.guild.text_channels, name="「ෆ-⌗-•-welcome-ʚɞ」👋" or "welcome-🚃⋆｡˚⋆")
        if not welcome_channel:
            logging.warning(f"Welcome channel not found in guild: {member.guild.name} (ID: {member.guild.id})")
            return  # Exit if no welcome channel is found

        # Fetch the user's profile picture
        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
        response = requests.get(avatar_url)
        if response.status_code != 200:
            logging.error(f"Failed to fetch avatar for {member.name}#{member.discriminator}. HTTP Status: {response.status_code}")
            return
        avatar = Image.open(BytesIO(response.content)).convert("RGBA")

        # Create the base image
        base = Image.new("RGBA", (800, 300), (30, 30, 30))  # Dark background
        draw = ImageDraw.Draw(base)

        # Add a decorative border
        draw.rectangle([(0, 0), (799, 299)], outline=(255, 255, 255), width=5)

        # Paste the user's avatar
        avatar = avatar.resize((150, 150))  # Resize the avatar
        base.paste(avatar, (50, 75), avatar)  # Paste with transparency

        # Add text (username and welcome message)
        font = ImageFont.truetype("arial.ttf", 30)  # Use a font available on your system
        draw.text((220, 100), f"Welcome, {member.name}!", fill=(255, 255, 255), font=font)
        draw.text((220, 150), f"Member #{len(member.guild.members)}", fill=(200, 200, 200), font=font)

        # Save the image to a BytesIO object
        buffer = BytesIO()
        base.save(buffer, format="PNG")
        buffer.seek(0)

        # Send the image in the welcome channel
        await welcome_channel.send(
            f"🎉 Welcome to the server, {member.mention}!",
            file=discord.File(fp=buffer, filename="welcome.png")
        )
        logging.info(f"Welcome message sent for {member.name}#{member.discriminator} in {welcome_channel.name}.")
    except Exception as e:
        logging.error(f"Error in on_member_join for {member.name}#{member.discriminator}: {e}")
        # Optionally, send an error message to a logs channel
        logs_channel = discord.utils.get(member.guild.text_channels, name="logs")
        if logs_channel:
            await logs_channel.send(f"❌ An error occurred while welcoming {member.mention}: {e}")

# Event: On member remove
@bot.event
async def on_member_leave(member):
    bye_channel = get_channel_by_name(member.guild, ["「ෆ-⌗-•-bye-ʚɞ」👋"])
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


@bot.command(name="Mhelp")
async def mhelp(ctx, command_name: str = None):
    if command_name is None:
        embed = discord.Embed(
            title="Error",
            description="❌ You did not insert any command name.",
            color=discord.Color.red(),
        )
        embed.set_thumbnail(url="https://www.clipartmax.com/png/full/388-3887666_wrong-icon-with-png-and-vector-format-for-free-unlimited-wrong-icon.png")
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title=command_name,
        description=f"Here is the info about {command_name}.",
        color=discord.Color.blue(),
    )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3593/3593455.png")

    if command_name == "info":
        embed.add_field(name="Info", value="Info is used when you want to get info about the bot, its version, or other details.")
        embed.add_field(name="How to execute", value="?info")
    elif command_name == "serverinfo":
        embed.add_field(name="Server Information", value="This command is used to get information about the server you're in.")
        embed.add_field(name="How to execute", value="?serverinfo")
    elif command_name == "shutdown":
        embed.add_field(name="Shut Down", value="Turn the bot off. ⚠ **ADMIN COMMAND** ⚠")
        embed.add_field(name="How to execute", value="?shutdown")
    elif command_name == "poll":
        embed.add_field(name="Poll", value="Create a timed poll. This command is limited to only 10 answers!")
        embed.add_field(name="How to execute", value="?poll 'Question' 'Answer one' 'Answer two'...")
    elif command_name == "ask":
        embed.add_field(name="Ask", value="Ask ChatGPT 2 Turbo a question.")
        embed.add_field(name="How to execute", value="?ask 'Question'")
    elif command_name == "analyse":
        embed.add_field(name="Analyse", value="Analyse a user or yourself")
        embed.add_field(name="How to execute", value="?analyse 'nothing = yourself or @user")
    elif command_name == "createrole":
        embed.add_field(name="Create a role", value="Create a custom role.")
        embed.add_field(name="How to execute", value="?createrole 'role name' 'permissions (member, mod or admin)' 'color (hex code)'")
    elif command_name == "giverole":
        embed.add_field(name="Give a role", value="Give a custom role")
        embed.add_field(name="How to execute", value="?giverole 'rolename' 'user'")
    elif command_name == "removerole":
        embed.add_field(name="Remove a role", value="Remove a custom role")
        embed.add_field(name="How to execute", value="?removerole 'rolename' 'user'")
    elif command_name == "warn":
        embed.add_field(name="Warn an user", value="Warn a user with or without a specific reason")
        embed.add_field(name="How to execute", value="?warn 'user' 'reason'")
    elif command_name == "kick":
        embed.add_field(name="Kick an user", value="Kick a user with or without a specific reason")
        embed.add_field(name="How to execute", value="?kick 'user' 'reason'")
    elif command_name == "ban":
        embed.add_field(name="Ban", value="Ban an user with or without a specific reason")
        embed.add_field(name="How to execute", value="?ban 'user' 'reason'")
    elif command_name == "givexp":
        embed.add_field(name="Give XP", value="Give XP to a specific user or yourself (i think)")
        embed.add_field(name="How to execute", value="?givexp 'user' 'xp'")
    elif command_name == "gainlvl":
        embed.add_field(name="Gain a level", value="Gain a level from a specific command")
        embed.add_field(name="How to execute", value="?gainlvl 'user'")
    elif command_name == "copydm":
        embed.add_field(name="Copy DM", value="Copy and send a message to a user's DM")
        embed.add_field(name="How to execute", value="?copydm 'user' 'message'")
    else:
        embed = discord.Embed(
            title="Oops...",
            description=f"Sorry, we couldn't find the command named `{command_name}`.",
            color=discord.Color.gray(),
        )

    await ctx.send(embed=embed)


# ?help command
@bot.command(name="myhelp")
async def help(ctx):
    print(f"Help command triggered by {ctx.author} in channel {ctx.channel}.")
    help_message = """Available commands:
    ?help - Show this help message
    ?info - Get information about the bot
    ?serverinfo - Get information about the current server
    ?shutdown - Shut down the bot (Admin only)
    ?poll - Create a poll (Usage: ?poll <question> <option1, option2, ...>)
    ?ask - Ask ChatGPT (Usage: ?ask <your message>)
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

@bot.command(name="restart")
@commands.has_permissions(administrator=True)
async def restart(ctx):
    """Restart the bot."""
    await ctx.send("🔄 Restarting the bot...")
    await bot.close()  # Close the bot connection
    os.execv(sys.executable, ["python", __file__, "--skip-input"])

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
async def removerole(ctx, role: discord.Role, member: discord.Member):
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
    Use changelog if you wanna see the new features added in this update!
    """
    await ctx.send(custominfo)

@bot.command(name="changelog")
async def changelog(ctx):
    changelog = f"Here is the changelog for the {bot_info['version']} version: {bot_info['new_stuff']}"
    await ctx.send(changelog)


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
        await ctx.send("❌ That command does not exist. Use `?Mhelp` to see the list of available commands.")
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

afk_users = {}

@bot.command(name="afk")
async def afk(ctx, *, reason="AFK"):
    """Set yourself as AFK."""
    afk_users[ctx.author.id] = reason
    await ctx.send(f"✅ {ctx.author.mention} is now AFK: {reason}")

@bot.event
async def on_message(message):
    """Handle all on_message events."""
    global last_activity_time

    # Ignore bot's own messages
    if message.author.bot:
        return

    # Update last activity time for inactivity monitoring
    last_activity_time = datetime.utcnow()

    # Handle AFK users
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(f"✅ Welcome back, {message.author.mention}!")
    for mention in message.mentions:
        if mention.id in afk_users:
            await message.channel.send(f"🔔 {mention.mention} is AFK: {afk_users[mention.id]}")

    # Handle XP system
    bucket = cooldown.get_bucket(message)
    retry_after = bucket.update_rate_limit()
    if not retry_after:  # Only grant XP if not in cooldown
        user_id = message.author.id
        user_data = get_user_data(user_id)

        # Grant XP
        user_data["xp"] += 10
        xp_needed = user_data["level"] * 100  # XP needed to level up

        # Check for level up
        if user_data["xp"] >= xp_needed:
            user_data["xp"] -= xp_needed
            user_data["level"] += 1
            user_data["coins"] += 50  # Reward coins for leveling up
            await message.channel.send(f"🎉 {message.author.mention} leveled up to **Level {user_data['level']}**! You earned 50 coins!")

        # Save updated user data
        update_user_data(user_id, "xp", user_data["xp"])
        update_user_data(user_id, "level", user_data["level"])
        update_user_data(user_id, "coins", user_data["coins"])
        logging.info(f"User {message.author.name} (ID: {user_id}) gained 10 XP. Total XP: {user_data['xp']}.")

    # Process commands
    await bot.process_commands(message)

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
            os.execv(sys.executable, ["python", __file__, "--skip-input"])  # Restart the bot

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

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-input", action="store_true", help="Skip input prompts for auto-restart")
    args = parser.parse_args()

    # Skip the input prompts if the `--skip-input` flag is provided
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
    # Check if the music folder has more than 50 files
    oldest_file = check_music_folder()
    if oldest_file:
        await ctx.send(
            f"⚠️ The music folder has more than 50 songs. Continuing will delete the oldest file: `{os.path.basename(oldest_file)}`. Do you want to proceed? (yes/no)"
        )

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]

        try:
            response = await bot.wait_for("message", check=check, timeout=30.0)
            if response.content.lower() == "no":
                await ctx.send("❌ Operation canceled.")
                return
            else:
                os.remove(oldest_file)  # Delete the oldest file
                await ctx.send(f"🗑️ Deleted the oldest file: `{os.path.basename(oldest_file)}`.")
        except asyncio.TimeoutError:
            await ctx.send("⏰ You took too long to respond. Operation canceled.")
            return

    # Proceed with the upload logic
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
    """Play a song from a URL, the music folder, or by its number."""
    # Check if the music folder has more than 50 files
    oldest_file = check_music_folder()
    if oldest_file:
        await ctx.send(
            f"⚠️ The music folder has more than 50 songs. Continuing will delete the oldest file: `{os.path.basename(oldest_file)}`. Do you want to proceed? (yes/no)"
        )

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]

        try:
            response = await bot.wait_for("message", check=check, timeout=30.0)
            if response.content.lower() == "no":
                await ctx.send("❌ Operation canceled.")
                return
            else:
                os.remove(oldest_file)  # Delete the oldest file
                await ctx.send(f"🗑️ Deleted the oldest file: `{os.path.basename(oldest_file)}`.")
        except asyncio.TimeoutError:
            await ctx.send("⏰ You took too long to respond. Operation canceled.")
            return

    # Proceed with the play logic
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

        # If a query is provided, check if it's a number or a URL
        if query:
            if query.isdigit():
                # Play the song by its number
                songs = sorted(os.listdir("music"))
                song_index = int(query) - 1  # Convert to zero-based index
                if 0 <= song_index < len(songs):
                    song_path = os.path.join("music", songs[song_index])
                    await ctx.send(f"🎵 Now playing: `{songs[song_index]}`")
                else:
                    await ctx.send(f"❌ Invalid song number. Please use a number between 1 and {len(songs)}.")
                    return
            elif query.startswith("http://") or query.startswith("https://"):
                # Play a song from a URL
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
                # Play a song by its name
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

@bot.command(name="download")
async def download(ctx, url: str):
    """Download a YouTube song or video and save it to the music folder."""
    if not (url.startswith("http://") or url.startswith("https://")):
        await ctx.send("❌ Invalid URL. Please provide a valid YouTube URL starting with `http://` or `https://`.")
        return

    await ctx.send(f"🔍 Downloading from URL: `{url}`...")
    ydl_opts = {
        "format": "bestaudio/best",  # Download the best audio format
        "outtmpl": "music/%(title)s.%(ext)s",  # Save to the music folder with the title as the filename
        "noplaylist": True,  # Do not download playlists
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(info)
            await ctx.send(f"✅ Downloaded `{info['title']}` and saved to the music folder as `{file_name}`.")
    except Exception as e:
        await ctx.send(f"❌ Failed to download from URL: {e}")

# Load the Hugging Face model (e.g., GPT-2)
qa_pipeline = pipeline("text-generation", model="gpt2")

@bot.command(name="ask")
async def ask(ctx, *, question: str):
    """Answer a question using a local AI model."""
    try:
        # Generate a response using the Hugging Face model
        response = qa_pipeline(question, max_length=100, num_return_sequences=1)
        answer = response[0]["generated_text"]
        await ctx.send(answer)
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")

@bot.command(name="joke")
async def joke(ctx):
    """Fetch a random joke."""
    url = "https://official-joke-api.appspot.com/random_joke"
    try:
        response = requests.get(url)
        data = response.json()
        await ctx.send(f"😂 **{data['setup']}**\n{data['punchline']}")
    except Exception as e:
        await ctx.send(f"❌ Failed to fetch a joke: {e}")

@bot.command(name="flip")
async def flip(ctx):
    """Flip a coin."""
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 The coin landed on: **{result}**!")

translator = Translator()

@bot.command(name="translate")
async def translate(ctx, target_language: str, *, text: str):
    """Translate text to a specified language."""
    try:
        translation = translator.translate(text, dest=target_language)
        await ctx.send(f"🌐 **Translation ({target_language}):** {translation.text}")
    except Exception as e:
        await ctx.send(f"❌ Failed to translate: {e}")

@bot.command(name="roll")
async def roll(ctx, sides: int = 6):
    """Roll a dice with a specified number of sides (default: 6)."""
    if sides < 1:
        await ctx.send("❌ The dice must have at least 1 side.")
        return
    result = random.randint(1, sides)
    await ctx.send(f"🎲 You rolled a {result} on a {sides}-sided dice!")

@bot.command(name="meme")
async def meme(ctx):
    """Fetch a random meme from Reddit."""
    url = "https://www.reddit.com/r/memes/random/.json"
    headers = {"User-Agent": "DiscordBot"}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        meme_url = data[0]["data"]["children"][0]["data"]["url"]
        title = data[0]["data"]["children"][0]["data"]["title"]
        await ctx.send(f"**{title}**\n{meme_url}")
    except Exception as e:
        await ctx.send(f"❌ Failed to fetch a meme: {e}")

import requests

@bot.command(name="weather")
async def weather(ctx, *, city: str):
    """Get the current weather for a city."""
    api_key = openwheather # Replace with your API key
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(url)
        data = response.json()
        if data["cod"] != 200:
            await ctx.send(f"❌ City not found: {city}")
            return
        weather_desc = data["weather"][0]["description"].capitalize()
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        await ctx.send(
            f"🌤️ **Weather in {city.capitalize()}**:\n"
            f"- Description: {weather_desc}\n"
            f"- Temperature: {temp}°C (Feels like {feels_like}°C)\n"
            f"- Humidity: {humidity}%\n"
            f"- Wind Speed: {wind_speed} m/s"
        )
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")

def check_music_folder():
    """Check if the music folder has more than 50 files and return the oldest file."""
    music_folder = "music"
    files = [os.path.join(music_folder, f) for f in os.listdir(music_folder) if os.path.isfile(os.path.join(music_folder, f))]
    if len(files) > 50:
        oldest_file = min(files, key=os.path.getctime)  # Get the oldest file based on creation time
        return oldest_file
    return None

@bot.command(name="balance")
async def balance(ctx):
    """Check your current balance."""
    user_id = ctx.author.id
    balance = get_balance(user_id)
    await ctx.send(f"💰 {ctx.author.mention}, your current balance is **{balance} coins**.")

def can_claim_daily(user_id):
    """Check if the user can claim their daily reward."""
    data = load_user_data()
    if str(user_id) not in data:
        data[str(user_id)] = {"xp": 0, "level": 1, "coins": 100, "balance": 0, "warnings": [], "last_daily": None}
        save_user_data(data)
    last_daily = data[str(user_id)].get("last_daily")
    if last_daily:
        last_claim_time = datetime.fromisoformat(last_daily)
        return datetime.utcnow() >= last_claim_time + timedelta(days=1)
    return True

def update_last_daily(user_id):
    """Update the last daily claim time for a user."""
    data = load_user_data()
    if str(user_id) not in data:
        data[str(user_id)] = {"xp": 0, "level": 1, "coins": 100, "balance": 0, "warnings": [], "last_daily": None}
    data[str(user_id)]["last_daily"] = datetime.utcnow().isoformat()
    save_user_data(data)

@bot.command(name="daily")
async def daily(ctx):
    """Claim your daily reward."""
    user_id = ctx.author.id
    if can_claim_daily(user_id):
        reward = 100  # Amount of coins rewarded daily
        update_balance(user_id, reward)
        update_last_daily(user_id)
        await ctx.send(f"✅ {ctx.author.mention}, you have claimed your daily reward of **{reward} coins**!")
    else:
        await ctx.send(f"❌ {ctx.author.mention}, you have already claimed your daily reward. Try again tomorrow!")

@bot.command(name="give")
async def give(ctx, member: discord.Member, amount: int):
    """Give coins to another user."""
    if amount <= 0:
        await ctx.send("❌ You must give a positive amount of coins.")
        return

    giver_id = ctx.author.id
    receiver_id = member.id

    giver_balance = get_balance(giver_id)
    if giver_balance < amount:
        await ctx.send(f"❌ {ctx.author.mention}, you don't have enough coins to give. Your balance is **{giver_balance} coins**.")
        return

    # Deduct from giver and add to receiver
    update_balance(giver_id, -amount)
    update_balance(receiver_id, amount)

    await ctx.send(f"✅ {ctx.author.mention} gave **{amount} coins** to {member.mention}.")

@bot.command(name="steal")
async def steal(ctx, member: discord.Member):
    """Attempt to steal coins from another user."""
    if member == ctx.author:
        await ctx.send("❌ You cannot steal from yourself!")
        return

    thief_id = ctx.author.id
    victim_id = member.id

    victim_balance = get_balance(victim_id)
    if victim_balance <= 0:
        await ctx.send(f"❌ {member.mention} has no coins to steal.")
        return

    # Determine the amount to steal (randomized)
    stolen_amount = random.randint(1, min(50, victim_balance))

    # Deduct from victim and add to thief
    update_balance(victim_id, -stolen_amount)
    update_balance(thief_id, stolen_amount)

    await ctx.send(f"💰 {ctx.author.mention} stole **{stolen_amount} coins** from {member.mention}!")

@bot.command(name="verify")
@commands.has_permissions(administrator=True)
async def verify(ctx):
    """Send a verification message and assign the role '.・🍨︴Member ✰' when reacted to."""
    try:
        # Create the embed for the verification message
        embed = discord.Embed(
            title="Verification",
            description="React with ✅ to verify yourself and gain access to the server!",
            color=discord.Color.green(),
        )
        embed.set_thumbnail(url="https://www.freeiconspng.com/thumbs/checkmark-png/checkmark-png-5.png")

        # Send the embed message
        message = await ctx.send(embed=embed)

        # Add the ✅ reaction to the message
        await message.add_reaction("✅")

        # Save the message ID in the user_data.json file
        data = load_user_data()
        data["verify_message_id"] = message.id
        save_user_data(data)

        logging.info(f"Verification message sent in {ctx.channel.name} (ID: {ctx.channel.id}). Message ID: {message.id}")
        await ctx.send("✅ Verification message sent successfully!")
    except Exception as e:
        logging.error(f"Error in verify command: {e}")
        await ctx.send(f"❌ An error occurred while setting up verification: {e}")
        
@bot.event
async def on_raw_reaction_add(payload):
    """Handle reactions to the verification message."""
    try:
        # Ignore the bot's own reactions
        if payload.user_id == bot.user.id:
            return

        # Load the verification message ID from user_data.json
        data = load_user_data()
        verify_message_id = data.get("verify_message_id")
        if not verify_message_id:
            logging.warning("Verification message ID not found in user data.")
            return

        if payload.message_id != verify_message_id:
            return

        # Check if the reaction is ✅
        if str(payload.emoji) == "✅":
            guild = bot.get_guild(payload.guild_id)
            if not guild:
                logging.error(f"Guild not found for ID: {payload.guild_id}")
                return

            member = guild.get_member(payload.user_id)
            if not member:
                member = await guild.fetch_member(payload.user_id)
                if not member:
                    logging.error(f"Member not found for ID: {payload.user_id}")
                    return

            # Find or create the verification role
            role_name = ".・🍨︴Member ✰"
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                try:
                    role = await guild.create_role(name=role_name)
                    logging.info(f"Role '{role_name}' created in guild '{guild.name}' (ID: {guild.id}).")
                except discord.Forbidden:
                    logging.error(f"Insufficient permissions to create role '{role_name}' in guild '{guild.name}'.")
                    await member.send("❌ I do not have permission to create the verification role. Please contact an administrator.")
                    return
                except Exception as e:
                    logging.error(f"Error creating role '{role_name}': {e}")
                    return

            # Assign the role to the member
            try:
                await member.add_roles(role)
                await member.send(f"✅ You have been verified and given the role: **{role_name}**.")
                logging.info(f"Role '{role_name}' assigned to {member.name}#{member.discriminator} (ID: {member.id}).")

                # Update the user_data.json file to mark the user as verified
                user_data = load_user_data()
                if str(member.id) not in user_data:
                    user_data[str(member.id)] = {"xp": 0, "level": 1, "coins": 100, "balance": 0, "warnings": []}
                user_data[str(member.id)]["verified"] = True
                save_user_data(user_data)
            except discord.Forbidden:
                logging.error(f"Insufficient permissions to assign role '{role_name}' to {member.name}#{member.discriminator}.")
                await member.send("❌ I do not have permission to assign the verification role. Please contact an administrator.")
            except Exception as e:
                logging.error(f"Error assigning role '{role_name}' to {member.name}#{member.discriminator}: {e}")
    except Exception as e:
        logging.error(f"Error in on_raw_reaction_add: {e}")

@bot.command(name="trivia")
async def trivia(ctx, question: str, *options):
    """Play a trivia game with a question and multiple options."""
    if len(options) < 2:
        await ctx.send("❌ You need at least two options to create a trivia question.")
        return
    if len(options) > 10:
        await ctx.send("❌ You can only have up to 10 options for a trivia question.")
        return

    # Create an embed for the trivia question
    embed = discord.Embed(
        title="Trivia Time! 🎉",
        description=question,
        color=discord.Color.blue()
    )
    reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    # Add options to the embed
    for i, option in enumerate(options):
        embed.add_field(name=f"Option {i + 1}", value=option, inline=False)

    # Send the trivia question
    trivia_message = await ctx.send(embed=embed)

    # Add reactions for each option
    for i in range(len(options)):
        await trivia_message.add_reaction(reactions[i])

    # Wait for 30 seconds to collect answers
    await asyncio.sleep(30)

    # Fetch the updated message to count reactions
    trivia_message = await ctx.channel.fetch_message(trivia_message.id)
    results = {reactions[i]: trivia_message.reactions[i].count - 1 for i in range(len(options))}

    # Determine the winning option
    winner = max(results, key=results.get)
    winning_index = reactions.index(winner)
    winning_option = options[winning_index]

    # Announce the winner
    await ctx.send(f"🏆 The winning option is: **{winning_option}** with **{results[winner]} votes**!")

@bot.command(name="leaderboard")
async def leaderboard(ctx, category: str = None):
    """Display the leaderboard for level, XP, or coins."""
    if category not in ["level", "xp", "coins"]:
        await ctx.send("❌ Invalid category. Use `?leaderboard level`, `?leaderboard xp`, or `?leaderboard coins`.")
        return

    # Load user data
    data = load_user_data()

    # Prepare the leaderboard
    leaderboard_data = []
    for user_id, user_info in data.items():
        if user_id.isdigit():  # Ensure it's a user ID
            user = ctx.guild.get_member(int(user_id))
            if user:  # Only include users who are in the server
                leaderboard_data.append({
                    "name": user.display_name,
                    "level": user_info.get("level", 0),
                    "xp": user_info.get("xp", 0),
                    "coins": user_info.get("coins", 0)
                })

    # Sort the leaderboard based on the selected category
    leaderboard_data = sorted(leaderboard_data, key=lambda x: x[category], reverse=True)

    # Create the leaderboard message
    embed = discord.Embed(
        title=f"🏆 {category.capitalize()} Leaderboard",
        description=f"Top users by {category.capitalize()}",
        color=discord.Color.gold()
    )

    for i, entry in enumerate(leaderboard_data[:10], start=1):  # Show top 10 users
        embed.add_field(
            name=f"{i}. {entry['name']}",
            value=f"**{category.capitalize()}:** {entry[category]}",
            inline=False
        )

    await ctx.send(embed=embed)

# Run the bot
bot.run(token)  # Replace with your actual bot token
save_user_data()