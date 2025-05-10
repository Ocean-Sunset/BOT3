import discord
from discord.ext import commands
from discord.ext.commands import CooldownMapping
from discord.ext.commands import BucketType
from discord.ext.commands import CommandOnCooldown
from discord.ext.commands import cooldown
from discord.ui import Button, View
from yt_dlp import YoutubeDL
from discord import FFmpegPCMAudio
from googletrans import Translator
from discord.ui import Button, View
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import argparse
import os
import itertools
import openai  # For ChatGPT functionality
import time
from transformers import pipeline
import json
import difflib
import sys
import websockets
import logging
import requests
import random
import asyncio
from os import environ
from dotenv import load_dotenv
from datetime import datetime, timedelta

print("Startup sequence received.. (1 min wait activation)")
start_time = time.time()
is_sleeping = False  # Tracks whether the bot is in sleep mode
custom_status = None  # Tracks the custom status and activity
load_dotenv()
token = environ["TOKEN"]

SPAM_THRESHOLD = 5  # Number of messages allowed within the time window
TIME_WINDOW = 10  # Time window in seconds

last_activity_time = datetime.now()

EASTER_FILE = "data/easter.json"
TROPHY_FILE = "data/trophies.json"
BOT_DATA_FILE = "bot_data.txt"
WEBSITE_COMMANDS_FILE = "website_commands.txt"
LIMITATIONS_FILE = "f:\\Coding\\Discord\\BOT3\\data\\limitations.json"
LOGGING_CONFIG_FILE = "data/logging_config.json"

def load_logging_config():
    """Load logging configuration from the JSON file."""
    try:
        with open(LOGGING_CONFIG_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_logging_config(data):
    """Save logging configuration to the JSON file."""
    with open(LOGGING_CONFIG_FILE, "w") as file:
        json.dump(data, file, indent=4)


# Trophy definitions
trophies = {
    "trophy_1": {"name": "Coin Collector", "goal": "Collect 1,000 coins", "icon": "icons/coin_collector.png"},
    "trophy_2": {"name": "Gem Hoarder", "goal": "Collect 10 gems", "icon": "icons/gem_hoarder.png"},
    "trophy_3": {"name": "Impossible Victor", "goal": "Win 10 Impossible Easter fights", "icon": "icons/impossible_victor.png"},
    "trophy_4": {"name": "Level Master", "goal": "Reach Level 50", "icon": "icons/level_master.png"},
    "trophy_5": {"name": "Crate Opener", "goal": "Open 50 crates", "icon": "icons/crate_opener.png"},
}

# Load or initialize trophy data
if os.path.exists(TROPHY_FILE):
    with open(TROPHY_FILE, "r") as f:
        trophy_data = json.load(f)
else:
    trophy_data = {}

def save_trophy_data():
    """Save trophy data to the JSON file."""
    with open(TROPHY_FILE, "w") as f:
        json.dump(trophy_data, f, indent=4)

# Set OpenAI API Key
OPENAI_API_KEY = environ.get("OPEN_API_KEY") # Replace with your actual API key
openai.api_key = OPENAI_API_KEY

UNSPLACH_API_KEY = os.environ.get("UNSPLASH_API_KEY")
OPENWHEATHER_KEY = os.environ.get("OPENWEATHER_KEY")
openwheather = OPENWHEATHER_KEY

def is_owner(ctx):
    """Check if the command issuer is the bot owner."""
    return ctx.author.id == 917515232065228890  # Replace with your Discord user ID

# Define intents and enable the message content intent
intents = discord.Intents.default()
intents.message_content = True  # This is required for processing commands
intents.guilds = True
intents.members = True
intents.reactions = True

level_roles = {
    5: "[🌱 Novice]",
    10: "[🔰 Apprentice]",
    20: "[⚔️ Expert]",
    30: "[🏆 Master]",
    50: "[👑 Grandmaster]"
}

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


# Load or initialize the easter data
if os.path.exists(EASTER_FILE):
    with open(EASTER_FILE, "r") as f:
        easter_data = json.load(f)
else:
    easter_data = {}

def save_easter_data():
    """Save the easter data to the JSON file."""
    with open(EASTER_FILE, "w") as f:
        json.dump(easter_data, f, indent=4)

INVENTORY_FILE = "data/inventory.json"

def load_inventory():
    """Load the inventory data from the JSON file."""
    if os.path.exists(INVENTORY_FILE):
        with open(INVENTORY_FILE, "r") as f:
            return json.load(f)
    return {}

def award_trophy(user_id, trophy_id):
    """Award a trophy to a user."""
    user_id = str(user_id)
    if user_id not in trophy_data:
        trophy_data[user_id] = []
    if trophy_id not in trophy_data[user_id]:
        trophy_data[user_id].append(trophy_id)
        save_trophy_data()
        return True  # Trophy awarded
    return False  # Trophy already owned

def save_inventory(inventory):
    """Save the inventory data to the JSON file."""
    with open(INVENTORY_FILE, "w") as f:
        json.dump(inventory, f, indent=4)

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

# File to store bank data
BANK_FILE = "data/bank.json"

# Load or initialize bank data
if os.path.exists(BANK_FILE):
    try:
        with open(BANK_FILE, "r") as f:
            bank_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        # If the file is empty or invalid, initialize an empty dictionary
        bank_data = {}
        with open(BANK_FILE, "w") as f:
            json.dump(bank_data, f, indent=4)
else:
    # If the file doesn't exist, create it with an empty dictionary
    bank_data = {}
    os.makedirs(os.path.dirname(BANK_FILE), exist_ok=True)
    with open(BANK_FILE, "w") as f:
        json.dump(bank_data, f, indent=4)

def save_bank_data():
    """Save the bank data to the JSON file."""
    with open(BANK_FILE, "w") as f:
        json.dump(bank_data, f, indent=4)

def get_bank_balance(user_id):
    """Get the bank balance of a user."""
    user_id = str(user_id)
    return bank_data.get(user_id, 0)

def update_bank_balance(user_id, amount):
    """Update the bank balance of a user."""
    user_id = str(user_id)
    if user_id not in bank_data:
        bank_data[user_id] = 0
    bank_data[user_id] += amount
    save_bank_data()

def update_gems(user_id, gems_change):
    """Update the user's gem count."""
    data = load_user_data()
    if str(user_id) not in data:
        data[str(user_id)] = {"xp": 0, "level": 1, "coins": 100, "gems": 0, "warnings": []}
    data[str(user_id)]["gems"] = data[str(user_id)].get("gems", 0) + gems_change
    save_user_data(data)

def get_coins(user_id):
    """Get the balance of a user."""
    data = load_user_data()
    if str(user_id) not in data:
        data[str(user_id)] = {"xp": 0, "level": 1, "coins": 100, "warnings": []}
        save_user_data(data)
    return data[str(user_id)].get("coins", 0)

def update_coins(user_id, amount):
    """Update the balance of a user."""
    data = load_user_data()
    if str(user_id) not in data:
        data[str(user_id)] = {"xp": 0, "level": 1, "coins": 100, "warnings": []}
    data[str(user_id)]["coins"] = data[str(user_id)].get("coins", 0) + amount
    save_user_data(data)

USER_DATA_FILE = "data/user_data.json"


def save_user_data(data):
    """Save user data to the JSON file."""
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(USER_DATA_FILE), exist_ok=True)

        # Write the data to the file
        with open(USER_DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"❌ Error saving user data: {e}")

def load_user_data():
    """Load user data from the JSON file."""
    try:
        # Check if the file exists
        if not os.path.exists(USER_DATA_FILE):
            return {}

        # Read the data from the file
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("❌ Error: user_data.json is corrupted. Initializing with an empty dictionary.")
        return {}
    except Exception as e:
        print(f"❌ Error loading user data: {e}")
        return {}

def load_limitations():
    """Load limitations from the JSON file."""
    try:
        with open(LIMITATIONS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_limitations(data):
    """Save limitations to the JSON file."""
    with open(LIMITATIONS_FILE, "w") as file:
        json.dump(data, file, indent=4)

def get_user_data(user_id):
    """Get data for a specific user."""
    data = load_user_data()
    if str(user_id) not in data:
        # Initialize default values for new users
        data[str(user_id)] = {"xp": 0, "level": 1, "coins": 100, "gems": 0, "balance": 0, "warnings": []}
        save_user_data(data)
    else:
        # Ensure all required keys exist for existing users
        user_data = data[str(user_id)]
        user_data.setdefault("xp", 0)
        user_data.setdefault("level", 1)
        user_data.setdefault("coins", 100)
        user_data.setdefault("gems", 0)  # Initialize gems if missing
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
    global last_activity_time
    global is_sleeping
    last_activity_time = datetime.now()
    logging.info(f"{ctx.author} executed {ctx.command} in {ctx.channel}.")
    if is_sleeping:
        return

@bot.event
async def on_command_completion(ctx):
    logs_channel = get_logs_channel(ctx.guild)
    if logs_channel:
        await logs_channel.send(f"{ctx.author} executed `{ctx.command}` in {ctx.channel}.")
    logging.info(f"{ctx.author} executed `{ctx.command}` successfully.")
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

@bot.command(name="BServer")
@commands.check(is_owner)
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

@bot.command(name="UBServer")
@commands.check(is_owner)
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

def write_bot_data():
    """Write bot stats and leaderboard to bot_data.txt."""
    # Load user data
    user_data = load_user_data()

    # Generate leaderboard data (sorted by coins in descending order)
    leaderboard = sorted(
        [
            {"user_id": user_id, "coins": user_info.get("coins", 0)}
            for user_id, user_info in user_data.items()
        ],
        key=lambda x: x["coins"],
        reverse=True
    )

    # Format leaderboard as a string (e.g., "User123:1000,User456:800")
    leaderboard_str = ",".join(
        f"{entry['user_id']}:{entry['coins']}" for entry in leaderboard[:10]  # Top 10 users
    )

    # Prepare data to write to the file
    data = [
        f"total_users={len(bot.guilds[0].members) if bot.guilds else 0}",
        f"active_users={sum(1 for member in bot.guilds[0].members if member.status != discord.Status.offline) if bot.guilds else 0}",
        f"total_commands=500",  # Replace with actual command count
        f"uptime={get_uptime()}",
        f"bot_status=Running",
        f"leaderboard={leaderboard_str if leaderboard_str else '[404], No data.'}"  # Default if no data
    ]

    print("Writing data to bot_data.txt:", data)  # Debug log
    with open(BOT_DATA_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(data))

async def update_bot_data_periodically():
    """Periodically update bot_data.txt."""
    while True:
        write_bot_data()
        await asyncio.sleep(5)  # Update every 5 seconds
        
def read_website_command():
    """Read the latest command from website_commands.txt."""
    if not os.path.exists(WEBSITE_COMMANDS_FILE):
        return None
    with open(WEBSITE_COMMANDS_FILE, "r") as f:
        return f.read().strip()

def get_uptime():
    """Calculate bot uptime."""
    uptime_seconds = time.time() - start_time
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

async def handle_website_commands():
    """Handle commands from the website."""
    while True:
        command = read_website_command()
        if command == "stop_bot":
            print("⛔ Stopping bot...")
            await bot.close()
        elif command == "restart_bot":
            print("🔄 Restarting bot...")
            os.execv(sys.executable, ["python", __file__])
        await asyncio.sleep(2)  # Check every 2 seconds

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

@bot.command(name="MServer")
@commands.check(is_owner)
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
@commands.check(is_owner)
async def update(ctx, *, args: str):
    """Update the bot's version and new features, then restart."""
    global current_status
    try:
        version, new_stuff = args.split(" / ")
    except ValueError:
        await ctx.send("❌ Invalid format. Use `?update <version> / <new features>`.")
        return

    # Update the bot info
    bot_info["version"] = version
    bot_info["new_stuff"] = new_stuff
    save_bot_info()

    # Set the status to "Updating..."
    current_status = discord.Game("Updating...")
    await bot.change_presence(status=discord.Status.dnd, activity=current_status)

    await ctx.send(f"✅ Bot updated to version **{version}** with new features: **{new_stuff}**.")
    await ctx.send("🔄 Restarting the bot...")

    # Restart the bot
    os.execv(sys.executable, ["python", __file__, "--skip-input"])

custom_cooldown = CooldownMapping.from_cooldown(1, 10, BucketType.user)  # 1 message per 60 seconds

@bot.command(name="profile")
async def profile(ctx):
    """Check your XP, level, coins, and deposited coins."""
    user_id = ctx.author.id
    user_data = get_user_data(user_id)

    xp = user_data["xp"]
    level = user_data["level"]
    coins = user_data["coins"]
    deposited_coins = get_bank_balance(user_id)  # Retrieve the user's bank balance

    await ctx.send(
        f"📜 **{ctx.author.name}'s Profile**:\n"
        f"🔹 XP: {xp}\n"
        f"🔹 Level: {level}\n"
        f"🔹 Coins: {coins}\n"
        f"🔹 Deposited Coins: {deposited_coins}"
    )

@bot.command(name="buylevel")
async def buylevel(ctx, levels: int = 1):
    """Buy levels using coins."""
    if levels <= 0:
        await ctx.send("❌ You must buy at least 1 level.")
        return

    user_id = ctx.author.id
    user_data = get_user_data(user_id)

    cost = levels * 50  # Cost per level
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

@bot.command(name="choose_region")
@commands.has_permissions(administrator=True)
async def choose_region(ctx):
    """Allow users to choose a region by reacting to emojis."""
    message = await ctx.send(
        "Choose your region by reacting with the corresponding emoji:\n"
        "🌍 for Africa\n"
        "🌎 for Americas\n"
        "🌏 for Asia\n"
        "🇪🇺 for Europe\n"
        "🇦🇺 for Oceania"
    )
    reactions = ["🌍", "🌎", "🌏", "🇪🇺", "🇦🇺"]
    for reaction in reactions:
        await message.add_reaction(reaction)

    # Save the message ID for tracking reactions
    data = load_user_data()
    data["region_message_id"] = message.id
    save_user_data(data)

@bot.event
async def on_raw_reaction_add(payload):
    """Handle reactions for region roles and other commands."""
    try:
        # Ignore the bot's own reactions
        if payload.user_id == bot.user.id:
            return

        # Load user data
        data = load_user_data()

        # Handle region role reactions
        region_message_id = data.get("region_message_id")
        if region_message_id and payload.message_id == region_message_id:
            guild = bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            emoji_to_region = {
                "🌍": "Africa",
                "🌎": "Americas",
                "🌏": "Asia",
                "🇪🇺": "Europe",
                "🇦🇺": "Oceania",
            }
            role_name = emoji_to_region.get(str(payload.emoji))
            if role_name:
                role = discord.utils.get(guild.roles, name=role_name)
                if not role:
                    role = await guild.create_role(name=role_name)
                await member.add_roles(role)
                await member.send(f"✅ You have been given the **{role_name}** role.")
            return
        
                # Handle rules verification reactions
        rules_verify_message_id = data.get("rules_verify_message_id")
        if rules_verify_message_id and payload.message_id == rules_verify_message_id:
            guild = bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            if str(payload.emoji) == "🔵":
                # Find or create the verification role
                role_name = "「 Read and agreed to the rules 」🔵"
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
            return
        
        # Handle color role reactions
        colorrole_message_id = data.get("colorrole_message_id")
        if colorrole_message_id and payload.message_id == colorrole_message_id:
            guild = bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            emoji_to_color = {
                "🔴": "Red",
                "🟠": "Orange",
                "🟡": "Yellow",
                "🟢": "Green",
                "🔵": "Blue",
                "🟣": "Violet",
                "⚪": "White",
                "⚫": "Black",
            }
            role_name = emoji_to_color.get(str(payload.emoji))
            if role_name:
                role = discord.utils.get(guild.roles, name=role_name)
                if not role:
                    role = await guild.create_role(name=role_name)
                await member.add_roles(role)
                await member.send(f"✅ You have been given the **{role_name}** role.")
            return
        
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

        # Handle Chat Reviver role reactions
        chat_reviver_message_id = data.get("chat_reviver_message_id")
        if chat_reviver_message_id and payload.message_id == chat_reviver_message_id:
            guild = bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            if str(payload.emoji) == "🛠️":
                # Find or create the Chat Reviver role
                role_name = "Chat Reviver"
                role = discord.utils.get(guild.roles, name=role_name)
                if not role:
                    try:
                        role = await guild.create_role(name=role_name)
                        logging.info(f"Role '{role_name}' created in guild '{guild.name}' (ID: {guild.id}).")
                    except discord.Forbidden:
                        logging.error(f"Insufficient permissions to create role '{role_name}' in guild '{guild.name}'.")
                        await member.send("❌ I do not have permission to create the Chat Reviver role. Please contact an administrator.")
                        return
                    except Exception as e:
                        logging.error(f"Error creating role '{role_name}': {e}")
                        return

                # Assign the role to the member
                try:
                    await member.add_roles(role)
                    await member.send(f"✅ You have been given the **{role_name}** role.")
                    logging.info(f"Role '{role_name}' assigned to {member.name}#{member.discriminator} (ID: {member.id}).")
                except discord.Forbidden:
                    logging.error(f"Insufficient permissions to assign role '{role_name}' to {member.name}#{member.discriminator}.")
                    await member.send("❌ I do not have permission to assign the Chat Reviver role. Please contact an administrator.")
                except Exception as e:
                    logging.error(f"Error assigning role '{role_name}' to {member.name}#{member.discriminator}: {e}")
            return

    except Exception as e:
        logging.error(f"Error in on_raw_reaction_add: {e}")

@bot.event
async def on_member_join(member):
    """Event triggered when a user joins the server."""
    try:
        # Log the event
        logging.info(f"New member joined: {member.name}#{member.discriminator} (ID: {member.id})")

        # Get the welcome channel
        welcome_channel = discord.utils.get(member.guild.text_channels, name="welcome")
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

        # Load the background image
        background_path = "icons/welcome/background.jpg"  # Replace with the path to your background image
        try:
            background = Image.open(background_path).convert("RGBA")
        except FileNotFoundError:
            logging.error(f"Background image not found at {background_path}. Please ensure the file exists.")
            await welcome_channel.send("❌ Background image for the welcome card is missing. Please add it to `icons/welcome/background.jpg`.")
            return

        # Resize the background to fit the welcome card dimensions
        background = background.resize((800, 400))

        # Create the base image
        base = Image.new("RGBA", (800, 400), (30, 30, 30, 0))  # Transparent background
        base.paste(background, (0, 0))  # Paste the background onto the base image

        # Draw the circular avatar
        avatar = avatar.resize((150, 150))  # Resize the avatar
        mask = Image.new("L", avatar.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, avatar.size[0], avatar.size[1]), fill=255)
        base.paste(avatar, (325, 50), mask)  # Center the avatar on the image

        # Add the "WELCOME" text
        font_path = "fonts/impact.ttf"  # Replace with the path to your bold font file
        try:
            font_large = ImageFont.truetype(font_path, 80)  # Big and bold font
            font_small = ImageFont.truetype(font_path, 40)
        except OSError:
            await welcome_channel.send("❌ Font file not found. Please ensure the font file exists.")
            return

        draw = ImageDraw.Draw(base)
        draw.text((250, 220), "WELCOME", font=font_large, fill=(255, 255, 255), align="center")

        # Add the username below the "WELCOME" text
        draw.text((250, 300), member.name, font=font_small, fill=(255, 255, 255), align="center")

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

@bot.event
async def on_member_remove(member):
    """Event triggered when a user leaves the server."""
    try:
        # Log the event
        logging.info(f"Member left: {member.name}#{member.discriminator} (ID: {member.id})")

        # Replace this with the goodbye channel name you will provide
        goodbye_channel_name = "「ෆ-⌗-•-bye-ʚɞ」👋"  # Update this later with the actual channel name
        goodbye_channel = discord.utils.get(member.guild.text_channels, name=goodbye_channel_name)
        if not goodbye_channel:
            logging.warning(f"Goodbye channel not found in guild: {member.guild.name} (ID: {member.guild.id})")
            return  # Exit if no goodbye channel is found

        # Fetch the user's profile picture
        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
        response = requests.get(avatar_url)
        if response.status_code != 200:
            logging.error(f"Failed to fetch avatar for {member.name}#{member.discriminator}. HTTP Status: {response.status_code}")
            return
        avatar = Image.open(BytesIO(response.content)).convert("RGBA")

        # Load the background image
        background_path = "icons/welcome/background.jpg"  # Use the same background as the welcome image
        try:
            background = Image.open(background_path).convert("RGBA")
        except FileNotFoundError:
            logging.error(f"Background image not found at {background_path}. Please ensure the file exists.")
            await goodbye_channel.send("❌ Background image for the goodbye card is missing. Please add it to `icons/welcome/background.jpg`.")
            return

        # Resize the background to fit the goodbye card dimensions
        background = background.resize((800, 400))

        # Create the base image
        base = Image.new("RGBA", (800, 400), (30, 30, 30, 0))  # Transparent background
        base.paste(background, (0, 0))  # Paste the background onto the base image

        # Draw the circular avatar
        avatar = avatar.resize((150, 150))  # Resize the avatar
        mask = Image.new("L", avatar.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, avatar.size[0], avatar.size[1]), fill=255)
        base.paste(avatar, (325, 50), mask)  # Center the avatar on the image

        # Add the "GOODBYE" text
        font_path = "fonts/impact.ttf"  # Replace with the path to your bold font file
        try:
            font_large = ImageFont.truetype(font_path, 80)  # Big and bold font
            font_small = ImageFont.truetype(font_path, 40)
        except OSError:
            await goodbye_channel.send("❌ Font file not found. Please ensure the font file exists.")
            return

        draw = ImageDraw.Draw(base)
        draw.text((250, 220), "GOODBYE", font=font_large, fill=(255, 255, 255), align="center")

        # Add the username below the "GOODBYE" text
        draw.text((250, 300), member.name, font=font_small, fill=(255, 255, 255), align="center")

        # Save the image to a BytesIO object
        buffer = BytesIO()
        base.save(buffer, format="PNG")
        buffer.seek(0)

        # Send the image in the goodbye channel
        await goodbye_channel.send(
            f"👋 Goodbye, {member.mention}. We will miss you!",
            file=discord.File(fp=buffer, filename="goodbye.png")
        )
        logging.info(f"Goodbye message sent for {member.name}#{member.discriminator} in {goodbye_channel.name}.")
    except Exception as e:
        logging.error(f"Error in on_member_remove for {member.name}#{member.discriminator}: {e}")
        # Optionally, send an error message to a logs channel
        logs_channel = get_logs_channel(member.guild)
        if logs_channel:
            await logs_channel.send(f"❌ An error occurred while saying goodbye to {member.mention}: {e}")

@bot.command(name="rules-verify")
@commands.has_permissions(administrator=True)
async def rules_verify(ctx):
    """Send a rules verification message and assign the role '.・🍨︴Member ✰' when reacted to."""
    try:
        # Create the embed for the rules verification message
        embed = discord.Embed(
            title="Rules Verification",
            description=(
                "Please read the rules before verifying yourself again!:\n\n"
                "React with 🔵 to verify that you agree to the rules and gain access to the server."
            ),
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1828/1828640.png")  # Blue checkmark icon

        # Send the embed message
        message = await ctx.send(embed=embed)

        # Add the 🔵 reaction to the message
        await message.add_reaction("🔵")

        # Save the message ID in the user_data.json file
        data = load_user_data()
        data["rules_verify_message_id"] = message.id
        save_user_data(data)

        logging.info(f"Rules verification message sent in {ctx.channel.name} (ID: {ctx.channel.id}). Message ID: {message.id}")
        await ctx.send("✅ Rules verification message sent successfully!")
    except Exception as e:
        logging.error(f"Error in rules_verify command: {e}")
        await ctx.send(f"❌ An error occurred while setting up rules verification: {e}")

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

@bot.command(name="Mhelp")
async def mhelp(ctx, command_name: str = None):
    """Provide help information for commands dynamically."""
    # Dictionary to store command descriptions
    command_descriptions = {
        "help": "Show this help message.",
        "info": "Get information about the bot.",
        "serverinfo": "Get information about the current server.",
        "shutdown": "Shut down the bot (Admin only).",
        "poll": "Create a poll (Usage: ?poll <question> <option1, option2, ...>).",
        "ask": "Ask ChatGPT (Usage: ?ask <your message>).",
        "analyse": "Analyse a user or yourself (Usage: ?analyse @user).",
        "createrole": "Create a role (Usage: ?createrole <name> <permissions: member, mod, or admin> <color: Hex code>).",
        "giverole": "Give a role to a user (Usage: ?giverole <role_name> <user>).",
        "removerole": "Remove a role from a user (Usage: ?removerole <role_name> <user>).",
        "warn": "Warn a user (Usage: ?warn <user> <reason>).",
        "kick": "Kick a user (Usage: ?kick <user> <reason>).",
        "ban": "Ban a user (Usage: ?ban <user> <reason>).",
        "givexp": "Give XP to a user (Usage: ?givexp <user> <xp>).",
        "gainlvl": "Give a level to a user (Usage: ?gainlvl <user>).",
        "copydm": "Send a message to a user's DM (Usage: ?copydm <user> <message>).",
        "copychannel": "Send a message to a specific channel (Usage: ?copychannel <channel> <message>).",
        "colorrole": "Allow users to choose a color role by reacting to emojis.",
        "verify": "Send a verification message.",
        "copy": "Copy text (Usage: ?copy <text>).",
        "choose_country": "Choose your country by reacting to emojis.",
        "startgame": "Start a Truth or Dare game (members must be in the VC).",
        "checkvc": "Check if all users are in the Truth or Dare voice channel.",
        "continue": "Continue the Truth or Dare game.",
        "endgame": "End the Truth or Dare game.",
        "timeout": "Timeout a user (Usage: ?timeout <user> <time> <reason>).",
        "search_img": "Search for an image (Usage: ?search_img <query>).",
        "zen": "Put a user in Zen mode (timeout) for a specified duration.",
        "BServer": "Ban a server (Usage: ?BServer <server_name>).",
        "UBServer": "Unban a server (Usage: ?UBServer <server_name>).",
        "MServer": "Manage server restrictions (Usage: ?MServer <server_name> / <restriction_level>).",
        "update": "Update the bot (Admin only).",
        "unzen": "Remove Zen mode from a user (Admin only).",
        "balance": "Check your balance.",
        "daily": "Claim your daily reward.",
        "steal": "Attempt to steal coins from another user (Usage: ?steal <user>).",
        "give": "Give coins to another user (Usage: ?give <user> <amount>).",
        "stealadmin": "Steal coins bypassing time limits (Admin only).",
        "wheel": "Spin a wheel of names (Usage: ?wheel <name1 / name2 / ...>).",
        "leaderboard": "Show the leaderboard for level, XP, or coins.",
        "trivia": "Play a trivia game (Usage: ?trivia <question> <option1, option2, ...>).",
        "reminder": "Set a reminder (Usage: ?reminder <time> <message>).",
        "join": "Join a voice channel.",
        "leave": "Leave a voice channel.",
        "mute": "Mute a user (Usage: ?mute <user>).",
        "unmute": "Unmute a user (Usage: ?unmute <user>).",
        "purge": "Delete a number of messages (Usage: ?purge <number>).",
        "rps": "Play Rock-Paper-Scissors (Usage: ?rps <choice>).",
        "setwelcome": "Set a custom welcome message.",
        "afk": "Set yourself as AFK (Usage: ?afk <reason>).",
        "restart": "Restart the bot (Admin only).",
        "changelog": "View the bot's changelog.",
        "play": "Play a song from a URL or the music folder.",
        "download": "Download a YouTube song or video.",
        "upload": "Upload an audio file or provide a URL to download.",
        "queue": "List all songs in the music folder.",
        "easterfight": "Initiate a combat between an user or a bot"
    }

    if command_name is None:
        # If no command is specified, list all available commands
        embed = discord.Embed(
            title="Available Commands",
            description="Here is a list of all available commands. Use `?Mhelp <command>` for more details.",
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/Blue_question_mark_icon.svg/1024px-Blue_question_mark_icon.svg.png")  # Blue question mark thumbnail
        for command in valid_commands:
            embed.add_field(
                name=f"?{command}",
                value=command_descriptions.get(command, "No description available."),
                inline=False,
            )
        await ctx.send(embed=embed)
    else:
        # If a specific command is requested, show its details
        command_name = command_name.lower()
        if command_name in valid_commands:
            embed = discord.Embed(
                title=f"Help: ?{command_name}",
                description=command_descriptions.get(command_name, "No description available."),
                color=discord.Color.blue(),
            )
            embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/Blue_question_mark_icon.svg/1024px-Blue_question_mark_icon.svg.png")  # Blue question mark thumbnail
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Command `{command_name}` not found. Use `?Mhelp` to see the list of available commands.")

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
@commands.check(is_owner)
async def restart(ctx):
    """Restart the bot."""
    global current_status
    current_status = discord.Game("Restarting...")
    await bot.change_presence(status=discord.Status.dnd, activity=current_status)

    await ctx.send("🔄 Restarting the bot...")
    await bot.close()
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
@commands.check(is_owner) # Ensure the user has the required permissions
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
@commands.check(is_owner) # Ensure the user has the required permissions
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
@commands.check(is_owner)
async def removerole(ctx, role: discord.Role, member: discord.Member):
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"✅ Removed role **{role.name}** from {member.mention}.")
    else:
        await ctx.send(f"❌ {member.mention} does not have the role **{role.name}**.")

# Updated ?info command to use dynamic data
@bot.command()
async def info(ctx):
    custominfo = f"""# I am a multifunctional python Discord bot!
    - Status: Exclusive
    - Build: A-1 Exclusive
    - Version: **{bot_info['version']}**
    - Developper: th3_t1sm
    
    I am multifunctional discord bot created by th3_t1sm,
    This bot is Exclusive to Akari's Ashed Graveyard.
    As well as the build who will receive custom updates.
    """
    await ctx.send(custominfo)

@bot.command(name="changelog")
async def changelog(ctx):
    changelog = f"Here is the changelog for the {bot_info['version']} version: {bot_info['new_stuff']}"
    await ctx.send(changelog)


@bot.command(name="analyse")
async def analyse(ctx, member: discord.Member = None):
    """Analyse a user with all available data."""
    if member is None:
        member = ctx.author  # Default to the command author if no member is mentioned

    # Load user data
    user_id = str(member.id)
    user_data = get_user_data(user_id)
    inventory = load_inventory().get(user_id, [])
    trophies = trophy_data.get(user_id, [])
    warnings = warnings_data.get(user_id, {}).get("warnings", 0)
    eggs_collected = easter_data.get(user_id, {}).get("eggs", 0)
    gems_collected = user_data.get("gems", 0)
    bank_balance = get_bank_balance(user_id)

    # Create the embed
    embed = discord.Embed(
        title=f"Analysis of {member.name}",
        description=f"Here are the details of {member.mention}",
        color=discord.Color.blue()
    )

    # Add Discord profile details
    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
    embed.add_field(name="Full Name", value=f"{member.name}#{member.discriminator}", inline=False)
    embed.add_field(name="ID", value=member.id, inline=False)
    embed.add_field(name="Status", value=member.status, inline=False)
    embed.add_field(name="Account Created On", value=member.created_at.strftime("%d %B %Y, %H:%M:%S"), inline=False)
    embed.add_field(name="Joined Server On", value=member.joined_at.strftime("%d %B %Y, %H:%M:%S"), inline=False)
    embed.add_field(name="Roles", value=", ".join([role.name for role in member.roles if role.name != "@everyone"]) or "None", inline=False)

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
        inventory_items = "\n".join([f"{item['name']} (Rarity: {item['rarity']})" for item in inventory])
        embed.add_field(name="Inventory", value=inventory_items, inline=False)
    else:
        embed.add_field(name="Inventory", value="Empty", inline=False)

    # Add trophies
    if trophies:
        trophy_names = [trophies[trophy_id]["name"] for trophy_id in trophies if trophy_id in trophies]
        embed.add_field(name="Trophies", value=", ".join(trophy_names), inline=False)
    else:
        embed.add_field(name="Trophies", value="None", inline=False)

    # Send the embed
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

@bot.command(name="shutdown")
@commands.check(is_owner)
async def shutdown(ctx):
    """Put the bot into sleep mode."""
    global is_sleeping
    is_sleeping = True  # Enable sleep mode

    # Set the bot's status to "Offline" and idle
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game("[🔌⚠️] : Offline"))
    await ctx.send("🔌 The bot is now in sleep mode. Use `?start` to wake it up.")

@bot.command(name="start")
@commands.check(is_owner)
async def start(ctx):
    """Wake the bot up from sleep mode."""
    global is_sleeping
    if not is_sleeping:
        await ctx.send("✅ The bot is already active.")
        return

    is_sleeping = False  # Disable sleep mode

    # Restore the bot's normal status
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("with Python 🐍"))
    await ctx.send("✅ The bot is now active and ready to use!")
    
@bot.command(name="kys")
@commands.check(is_owner)
async def kys(ctx):
    """commit die the bot."""
    await ctx.send("Commiting die...")
    await bot.close()

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

valid_commands = [
    "help", "info", "serverinfo", "shutdown", "poll", "ask", "analyse", "createrole",
    "giverole", "removerole", "warn", "kick", "ban", "givexp", "gainlvl", "copydm",
    "copychannel", "colorrole", "verify", "copy", "choose_country", "startgame",
    "checkvc", "continue", "endgame", "timeout", "search_img", "zen", "BServer",
    "UBServer", "MServer", "update", "unzen", "balance", "daily", "steal", "give",
    "stealadmin", "wheel", "leaderboard", "trivia", "reminder", "join", "leave",
    "mute", "unmute", "purge", "rps", "setwelcome", "afk", "restart", "changelog",
    "zen", "play", "download", "upload", "queue", 
]

@bot.event
async def on_command_error(ctx, error):
    # Ignore messages starting with "??" or more
    if ctx.message.content.startswith("??" or "???" or "????" or "?????"):
        return
    
    if isinstance(error, commands.CommandNotFound):
        # Get the command name the user tried to use
        attempted_command = ctx.message.content.split()[0][1:]  # Remove the prefix (e.g., "?")

        # Find the closest match to the attempted command
        closest_match = difflib.get_close_matches(attempted_command, valid_commands, n=1, cutoff=0.6)

        if closest_match:
            # Suggest the closest matching command
            await ctx.send(f"❌ Command not found. Did you mean: `{closest_match[0]}`?")
        else:
            # No close match found
            await ctx.send("❌ Command not found. Use `?Mhelp` or `?myhelp` to see the list of available commands.")
    else:
        await ctx.send(f"An error occured: {error}")

# Dictionary to track users and their message activity
user_message_counts = {}

def check_trophy_goals(user_id, channel):
    """Check if a user has met any trophy goals and notify in the server channel."""
    user_data = get_user_data(user_id)

    # Trophy 1: Collect 1,000 coins
    if user_data["coins"] >= 1000:
        if award_trophy(user_id, "trophy_1"):
            bonus_xp = 100  # Example: 100 XP for earning this trophy
            user_data["xp"] += bonus_xp
            update_user_data(user_id, "xp", user_data["xp"])
            asyncio.create_task(channel.send(
                f"🏆 You earned the **Coin Collector** trophy and received **{bonus_xp} bonus XP**!"
            ))

    # Trophy 2: Collect 10 gems
    if easter_data.get(str(user_id), {}).get("gems", 0) >= 10:
        if award_trophy(user_id, "trophy_2"):
            bonus_xp = 150  # Example: 150 XP for earning this trophy
            user_data["xp"] += bonus_xp
            update_user_data(user_id, "xp", user_data["xp"])
            asyncio.create_task(channel.send(
                f"🏆 You earned the **Gem Hoarder** trophy and received **{bonus_xp} bonus XP**!"
            ))

    # Trophy 3: Win 10 Impossible Easter fights
    if user_data.get("impossible_wins", 0) >= 10:
        if award_trophy(user_id, "trophy_3"):
            bonus_xp = 200  # Example: 200 XP for earning this trophy
            user_data["xp"] += bonus_xp
            update_user_data(user_id, "xp", user_data["xp"])
            asyncio.create_task(channel.send(
                f"🏆 You earned the **Impossible Victor** trophy and received **{bonus_xp} bonus XP**!"
            ))

    # Trophy 4: Reach Level 50
    if user_data["level"] >= 50:
        if award_trophy(user_id, "trophy_4"):
            bonus_xp = 500  # Example: 500 XP for earning this trophy
            user_data["xp"] += bonus_xp
            update_user_data(user_id, "xp", user_data["xp"])
            asyncio.create_task(channel.send(
                f"🏆 You earned the **Level Master** trophy and received **{bonus_xp} bonus XP**!"
            ))

    # Trophy 5: Open 50 crates
    if user_data.get("crates_opened", 0) >= 50:
        if award_trophy(user_id, "trophy_5"):
            bonus_xp = 250  # Example: 250 XP for earning this trophy
            user_data["xp"] += bonus_xp
            update_user_data(user_id, "xp", user_data["xp"])
            asyncio.create_task(channel.send(
                f"🏆 You earned the **Crate Opener** trophy and received **{bonus_xp} bonus XP**!"
            ))

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

@bot.command(name="colorrole")
async def colorrole(ctx):
    """Allow users to choose a color role by reacting to emojis."""
    message = await ctx.send(
        "Which color do you want?\n"
        "React with:\n"
        "🔴 for Red\n"
        "🟠 for Orange\n"
        "🟡 for Yellow\n"
        "🟢 for Green\n"
        "🔵 for Blue\n"
        "🟣 for Violet\n"
        "⚪ for White\n"
        "⚫ for Black"
    )
    reactions = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "⚪", "⚫"]
    for reaction in reactions:
        await message.add_reaction(reaction)

    # Save the message ID for tracking reactions
    data = load_user_data()
    data["colorrole_message_id"] = message.id
    save_user_data(data)

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

# Dictionary to track cooldowns for users
message_cooldowns = {}

@bot.event
async def on_message(message):
    print(f"📩 Message received: {message.content} from {message.author}")
    """Handle all on_message events."""
    global last_activity_time
    global last_activity
    print(f"{last_activity};{last_activity_time}")
    guild_id = str(message.guild.id)
    limitations = load_limitations()
    level = limitations.get(guild_id, 0)  # Default to no filtering if not set

    # Ignore bot's own messages
    if message.author.bot:
        return

    # Update last activity time for inactivity monitoring
    last_activity_time = datetime.now()
    
    # Update the last activity time for the guild
    last_activity[message.guild.id] = datetime.now()

    # Handle AFK users
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(f"✅ Welcome back, {message.author.mention}!")
    for mention in message.mentions:
        if mention.id in afk_users:
            await message.channel.send(f"🔔 {mention.mention} is AFK: {afk_users[mention.id]}")
    
    # Handle XP system with custom cooldown
    user_id = message.author.id
    now = datetime.now()

    # Check if the user is on cooldown
    if user_id in message_cooldowns:
        cooldown_end = message_cooldowns[user_id]
        if now < cooldown_end:
            # User is still on cooldown, skip granting XP
            await bot.process_commands(message)
            return
        
    
    # Get the user's data
    user_data = get_user_data(user_id)

    # Grant XP
    user_data["xp"] += 10
    xp_needed = user_data["level"] * 100  # XP needed to level up

    # Check for level up
    if user_data["xp"] >= xp_needed:
        user_data["xp"] -= xp_needed
        user_data["level"] += 1
        user_data["coins"] += 50  # Reward coins for leveling up

        # Determine rewards based on level
        coins_reward = 50  # Default coin reward
        gems_reward = 0    # Default gem reward
        if user_data["level"] >= 50:  # Special reward for Level 50+
            coins_reward = 100
            gems_reward = 5

        # Add rewards
        user_data["coins"] += coins_reward
        user_data["gems"] += gems_reward

        # Calculate bonus XP based on the level reached
        bonus_xp = user_data["level"] * 10  # Example: 10 XP per level
        user_data["xp"] += bonus_xp

        # Notify the user
        rewards_message = (
            f"🎉 {message.author.mention} leveled up to **Level {user_data['level']}**! "
            f"You earned **{coins_reward} coins** and **{bonus_xp} bonus XP**"
        )
        if gems_reward > 0:
            rewards_message += f", and **{gems_reward} gems**!"
        else:
            rewards_message += "!"

        await message.channel.send(rewards_message)

        # Assign level-based role
        await assign_level_role(message.author, user_data["level"], message.channel)    

    # Save updated user data
    update_user_data(user_id, "xp", user_data["xp"])
    update_user_data(user_id, "level", user_data["level"])
    update_user_data(user_id, "coins", user_data["coins"])
    logging.info(f"User {message.author.name} (ID: {user_id}) gained 10 XP. Total XP: {user_data['xp']}.")

    user_id = str(message.author.id)
    data = load_user_data()

    # Ensure the user exists in the data and initialize the "messages" key if not present
    if user_id not in data:
        data[user_id] = {"xp": 0, "level": 1, "coins": 100, "warnings": [], "messages": []}
    elif "messages" not in data[user_id]:
        data[user_id]["messages"] = []

    # Track message timestamps
    current_time = time.time()
    data[user_id]["messages"].append(current_time)

    # Remove messages outside the time window
    data[user_id]["messages"] = [
        timestamp for timestamp in data[user_id]["messages"]
        if current_time - timestamp <= TIME_WINDOW
    ]

    # Check if the user exceeds the spam threshold
    if len(data[user_id]["messages"]) > SPAM_THRESHOLD:
        # Take action for spamming
        await message.channel.send(f"⚠️ {message.author.mention}, you are sending messages too quickly. Please slow down!")
        data[user_id]["warnings"].append({
            "reason": "Spamming",
            "timestamp": datetime.now().isoformat()
        })

        # Optional: Mute the user temporarily
        mute_role = discord.utils.get(message.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await message.guild.create_role(name="Muted")
            for channel in message.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False)
        await message.author.add_roles(mute_role, reason="Spamming")
        await asyncio.sleep(10)  # Mute duration (10 seconds)
        await message.author.remove_roles(mute_role, reason="Mute expired")
            
        # 1% chance to spawn a gem reaction
        if random.randint(1, 200) == 1:
            gem_emoji = "💎"  # Gem emoji
        await message.add_reaction(gem_emoji)

        def check(reaction, user):
            return (
                str(reaction.emoji) == gem_emoji
                and reaction.message.id == message.id
                and not user.bot
            )

        try:
            # Wait for a user to react within 10 seconds
            reaction, user = await bot.wait_for("reaction_add", timeout=5.0, check=check)

            # Add the gem to the user's count in easter.json
            user_id = str(user.id)
            update_gems(user_id, 1)

            # Remove the reaction and notify the user
            await message.clear_reaction(gem_emoji)
            await message.channel.send(f"💎 {user.mention} found a gem! Total gems: {easter_data[user_id]['gems']}")
        except asyncio.TimeoutError:
            # Remove the reaction if no one reacts within 10 seconds
            await message.clear_reaction(gem_emoji)
            
    offensive_words = {
        1: ["nigga", "nigger", "Nigga", "Nigger", "NIGGA", "NIGGER"],
        2: ["nigga", "nigger", "Nigga", "Nigger", "NIGGA", "NIGGER", "kys", "kms", "Kill yourself", "kill yourself"],
        3: ["nigga", "nigger", "Nigga", "Nigger", "NIGGA", "NIGGER", "kys", "kms", "Kill yourself", "kill yourself", "fuck", "bitch", "kill", "Fuck", "Bitch", "FUCK", "BITCH"],
        4: ["nigga", "nigger", "Nigga", "Nigger", "NIGGA", "NIGGER", "kys", "kms", "Kill yourself", "kill yourself", "fuck", "bitch", "kill", "Fuck", "Bitch", "FUCK", "BITCH", "shit", "SHIT", "Shit", "ts"],
        5: ["nigga", "nigger", "Nigga", "Nigger", "NIGGA", "NIGGER", "kys", "kms", "Kill yourself", "kill yourself", "fuck", "bitch", "kill", "Fuck", "Bitch", "FUCK", "BITCH", "shit", "SHIT", "Shit", "ts", "dumb", "Dumb", "DUMB", "ass", "Ass", "ASS", "idiot", "Idiot", "IDIOT"],
    }
    
    # Ensure the user exists in the data and initialize missing keys
    if user_id not in user_data:
        user_data[user_id] = {"xp": 0, "level": 1, "coins": 100, "warnings": [], "censored_count": 0, "strikes": 0}
    elif "censored_count" not in user_data[user_id]:
        user_data[user_id]["censored_count"] = 0
    
    # Check for offensive words
    if level > 0:
        for word in offensive_words.get(level, []):
            if word in message.content.lower():
                await message.delete()
                await message.channel.send(f"⚠️ {message.author.mention}, your message was removed for containing offensive language.")
                # Increment the censored count
                user_data[user_id]["censored_count"] += 1
                censored_count = user_data[user_id]["censored_count"]

                # Check if the user has reached the limit
                if censored_count >= 15:
                    user_data[user_id]["censored_count"] = 0  # Reset the count
                    user_data[user_id]["strikes"] += 1  # Add a strike
                    save_user_data(user_data)

                    # Notify the user and the channel
                    await message.channel.send(
                        f"⚠️ {message.author.mention} has been given a **strike** for repeated offensive language. Total strikes: {user_data[user_id]['strikes']}."
                    )

                    # Take action based on the number of strikes
                    if user_data[user_id]["strikes"] == 3:
                        mute_role = discord.utils.get(message.guild.roles, name="Muted")
                        if not mute_role:
                            mute_role = await message.guild.create_role(name="Muted")
                            for channel in message.guild.channels:
                                await channel.set_permissions(mute_role, send_messages=False, speak=False)
                        await message.author.add_roles(mute_role)
                        await message.channel.send(f"🔇 {message.author.mention} has been muted for accumulating 3 strikes.")
                    elif user_data[user_id]["strikes"] == 5:
                        await message.author.kick(reason="Reached 5 strikes")
                        await message.channel.send(f"👢 {message.author.mention} has been kicked for reaching 5 strikes.")
                    elif user_data[user_id]["strikes"] >= 7:
                        await message.author.ban(reason="Reached 7 strikes")
                        await message.channel.send(f"⛔ {message.author.mention} has been banned for reaching 7 strikes.")

                save_user_data(user_data)
                return
    
    # Allow the `?start` command to bypass sleep mode
    if is_sleeping and message.content.startswith("?start"):
        await bot.process_commands(message)
        return
    
    # Ignore all messages if the bot is in sleep mode
    if is_sleeping:
        return

    # Save updated user data
    save_user_data(data)

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

# Background task to monitor inactivity
async def monitor_inactivity():
    global last_activity_time
    while True:
        await asyncio.sleep(60)  # Check every minute
        time_since_last_activity = (datetime.now() - last_activity_time).total_seconds()
        if time_since_last_activity > 1200:  # 20 minutes = 1200 seconds
            logging.info("No activity detected for 20 minutes. Restarting the bot...")
            os.execv(sys.executable, ["python", __file__, "--skip-input"])  # Restart the bot

# Start the background task when the bot is ready
@bot.event
async def on_ready():
    print(f"✅ Bot is ready! Logged in as {bot.user}")
    print(f"Connected to {len(bot.guilds)} guild(s).")
    logging.info(f"Logged in as {bot.user}")
    bot.loop.create_task(monitor_inactivity())
    print("Monitor activity task has been started.")
    asyncio.create_task(update_bot_data_periodically())
    print("Update bot through website task has started.")
    asyncio.create_task(handle_website_commands())
    print("Handling website commands task has started.")
    bot.loop.create_task(change_status())
    print("Status task has been sent!")
    await asyncio.sleep(18000)
    bot.loop.create_task(chat_reviver_task())
    logging.info(f"Chat reviver task started.")

current_status = None
async def change_status():
    """Rotate statuses dynamically or use a custom status."""
    global custom_status
    global is_sleeping
    statuses = itertools.cycle([
        discord.Game("with Python ❤️"),
        discord.Activity(type=discord.ActivityType.watching, name="[ 🔍 Akari's Ashed Graveyard]: https://discord.gg/HR48uPMUfK"),
        discord.Streaming(name="DONT CLICK PLS", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    ])
    while True:
        if is_sleeping:
            # If the bot is in sleep mode, stop updating the status
            await asyncio.sleep(10)  # Check every 10 seconds if the bot is still in sleep mode
            continue

        if custom_status:  # If a custom status is set, use it
            await bot.change_presence(status=discord.Status.online, activity=custom_status)
        else:  # Otherwise, rotate through the default statuses
            current_status = next(statuses)
            await bot.change_presence(status=discord.Status.online, activity=current_status)
        await asyncio.sleep(360)  # Change status every 360 seconds

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

async def ensure_level_roles(guild):
    """Ensure all level roles exist in the server."""
    for level, role_name in level_roles.items():
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            try:
                # Create the role if it doesn't exist
                await guild.create_role(name=role_name, reason="Level-based role created by the bot.")
                logging.info(f"Role '{role_name}' created in guild '{guild.name}'.")
            except discord.Forbidden:
                logging.warning(f"Insufficient permissions to create role '{role_name}' in guild '{guild.name}'.")
                owner = guild.owner
                if owner:
                    await owner.send(
                        f"❌ I couldn't create the role '{role_name}' in your server **{guild.name}**. "
                        f"Please create it manually or grant me the necessary permissions."
                    )
            except Exception as e:
                logging.error(f"Error creating role '{role_name}' in guild '{guild.name}': {e}")

async def assign_level_role(member, level, channel):
    """Assign a level-based role to a user and notify in the server channel."""
    guild = member.guild
    role_name = level_roles.get(level)

    if not role_name:
        return  # No role for this level

    # Ensure the role exists
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        await ensure_level_roles(guild)
        role = discord.utils.get(guild.roles, name=role_name)

    # Assign the role
    if role and role not in member.roles:
        try:
            await member.add_roles(role, reason=f"Reached Level {level}")
            await channel.send(f"🎉 {member.mention} has been assigned the **{role_name}** role for reaching Level {level}!")
        except discord.Forbidden:
            logging.warning(f"Insufficient permissions to assign role '{role_name}' to {member.name}.")
        except Exception as e:
            logging.error(f"Error assigning role '{role_name}' to {member.name}: {e}")

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

ffmpeg_path = r"C:\Users\roland\Downloads\ffmpeg-2025-03-31-git-35c091f4b7-full_build\bin\ffmpeg.exe"
            

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
    """Play a song from a URL, the music folder, or by its number, with an optional loop count."""
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

        # Parse the query and loop count
        if query:
            parts = query.split(" ")
            song_query = " ".join(parts[:-1]) if parts[-1].isdigit() else query
            loop_count = int(parts[-1]) if parts[-1].isdigit() else 1

            if loop_count < 1:
                await ctx.send("❌ Loop count must be at least 1.")
                return

            # Determine the song path
            if song_query.isdigit():
                # Play the song by its number
                songs = sorted(os.listdir("music"))
                song_index = int(song_query) - 1  # Convert to zero-based index
                if 0 <= song_index < len(songs):
                    song_path = os.path.join("music", songs[song_index])
                    await ctx.send(f"🎵 Now playing: `{songs[song_index]}` (Looping {loop_count} times)")
                else:
                    await ctx.send(f"❌ Invalid song number. Please use a number between 1 and {len(songs)}.")
                    return
            elif song_query.startswith("http://") or song_query.startswith("https://"):
                # Play a song from a URL
                await ctx.send(f"🔍 Searching for `{song_query}`...")
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": "music/%(title)s.%(ext)s",
                    "noplaylist": True,
                }
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(song_query, download=True)
                    song_path = ydl.prepare_filename(info)
                    await ctx.send(f"✅ Downloaded `{info['title']}`. Now playing (Looping {loop_count} times)...")
            else:
                # Play a song by its name
                song_path = os.path.join("music", song_query)
                if not os.path.exists(song_path):
                    await ctx.send(f"❌ The file `{song_query}` does not exist in the music folder.")
                    return
                await ctx.send(f"🎵 Now playing: `{song_query}` (Looping {loop_count} times)")
                
            # Set the status to "Playing <song>"
            current_status = discord.Game(f"Playing {os.path.basename(song_path)}")
            await bot.change_presence(status=discord.Status.online, activity=current_status)

        else:
            # Play the first song in the music folder
            songs = sorted(os.listdir("music"))
            if not songs:
                await ctx.send("❌ The music folder is empty. Upload some songs using `?upload` or provide a URL.")
                return
            song = songs[0]
            song_path = os.path.join("music", song)
            loop_count = 1
            await ctx.send(f"🎵 Now playing: `{song}` (Looping {loop_count} times)")

        # Play the song with looping
        for i in range(loop_count):
            vc.play(discord.FFmpegPCMAudio(song_path, executable=ffmpeg_path), after=lambda e: logger.info(f"Finished playing: {song_path}"))
            while vc.is_playing():
                await asyncio.sleep(1)  # Wait for the song to finish before looping
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
    if len(files) > 37:
        oldest_file = min(files, key=os.path.getctime)  # Get the oldest file based on creation time
        return oldest_file
    return None

@bot.command(name="balance")
async def balance(ctx):
    """Check your current balance."""
    user_id = ctx.author.id
    balance = get_coins(user_id)
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
        return datetime.now() >= last_claim_time + timedelta(days=1)
    return True

def update_last_daily(user_id):
    """Update the last daily claim time for a user."""
    data = load_user_data()
    if str(user_id) not in data:
        data[str(user_id)] = {"xp": 0, "level": 1, "coins": 100, "balance": 0, "warnings": [], "last_daily": None}
    data[str(user_id)]["last_daily"] = datetime.now().isoformat()
    save_user_data(data)

@bot.command(name="daily")
async def daily(ctx):
    """Claim your daily reward."""
    user_id = ctx.author.id
    if can_claim_daily(user_id):
        reward = 100  # Amount of coins rewarded daily
        update_coins(user_id, reward)
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

    giver_balance = get_coins(giver_id)
    if giver_balance < amount:
        await ctx.send(f"❌ {ctx.author.mention}, you don't have enough coins to give. Your balance is **{giver_balance} coins**.")
        return

    # Deduct from giver and add to receiver
    update_coins(giver_id, -amount)
    update_coins(receiver_id, amount)

    await ctx.send(f"✅ {ctx.author.mention} gave **{amount} coins** to {member.mention}.")

@bot.command(name="steal")
@commands.cooldown(1, 60, commands.BucketType.user)  # 1 use per 60 seconds per user
async def steal(ctx, member: discord.Member):
    """Attempt to steal coins from another user."""
    if member == ctx.author:
        await ctx.send("❌ You cannot steal from yourself!")
        return

    thief_id = ctx.author.id
    victim_id = member.id

    victim_balance = get_coins(victim_id)
    if victim_balance <= 0:
        await ctx.send(f"❌ {member.mention} has no coins to steal.")
        return

    # Determine the amount to steal (randomized)
    stolen_amount = random.randint(1, min(50, victim_balance))

    # Deduct from victim and add to thief
    update_coins(victim_id, -stolen_amount)
    update_coins(thief_id, stolen_amount)

    await ctx.send(f"💰 {ctx.author.mention} stole **{stolen_amount} coins** from {member.mention}!")

# Handle cooldown errors
@steal.error
async def steal_error(ctx, error):
    if isinstance(error, CommandOnCooldown):
        await ctx.send(f"⏳ This command is on cooldown. Try again in {round(error.retry_after, 2)} seconds.")

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
    """Display the leaderboard for level, XP, coins, or Easter Eggs."""
    valid_categories = ["level", "xp", "coins", "eggs"]
    if category not in valid_categories:
        await ctx.send(f"❌ Invalid category. Use `?leaderboard level`, `?leaderboard xp`, `?leaderboard coins`, or `?leaderboard eggs`.")
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
                    "coins": user_info.get("coins", 0),
                    "eggs": easter_data.get(user_id, {}).get("eggs", 0)  # Include Easter Eggs
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

@bot.command(name="Supdate")
@commands.check(is_owner)
async def supdate(ctx, *, args: str):
    """Send an update message to the announcements channel in all servers and restart the bot."""
    try:
        # Parse the version and new features from the arguments
        version, new_stuff = args.split(" / ")
    except ValueError:
        await ctx.send("❌ Invalid format. Use `?Supdate <version> / <new features>`.")
        return

    # Update the bot info
    bot_info["version"] = version
    bot_info["new_stuff"] = new_stuff
    save_bot_info()

    # Send the update message to all servers
    for guild in bot.guilds:
        # Try to find a channel with "announcements" in its name
        announcement_channel = discord.utils.find(
            lambda c: ("announcements" in c.name.lower() or "announcement" in c.name.lower())  and isinstance(c, discord.TextChannel),
            guild.channels
        )

        if announcement_channel:
            try:
                # Send the update message to the announcements channel
                await announcement_channel.send(
                    f"# 📢 **Bot Update Announcement:**\n"
                    f"**Version:** {version}\n"
                    f"**New Features:** {new_stuff}"
                )
                logging.info(f"Update message sent to {announcement_channel.name} in {guild.name}.")
            except discord.Forbidden:
                logging.warning(f"Could not send message to {announcement_channel.name} in {guild.name} (Permission denied).")
            except Exception as e:
                logging.error(f"Error sending message to {announcement_channel.name} in {guild.name}: {e}")
        else:
            logging.warning(f"No announcements channel found in {guild.name}.")
            try:
                # Notify the server owner if no announcements channel is found
                owner = guild.owner
                if owner:
                    await owner.send(
                        f"❌ Could not find an announcements channel in your server **{guild.name}**. "
                        f"Please create one or ensure the bot has access to it."
                    )
            except Exception as e:
                logging.error(f"Error notifying owner of {guild.name}: {e}")

    # Notify the command issuer and restart the bot
    await ctx.send(f"✅ Update message sent to all servers with an announcements channel.\n"
                   f"**Version:** {version}\n"
                   f"**New Features:** {new_stuff}\n"
                   f"🔄 Restarting the bot...")

    # Restart the bot
    os.execv(sys.executable, ["python", __file__, "--skip-input"])

@bot.command(name="button")
async def button(ctx):
    """Send a message with a button."""
    # Create a button
    button = Button(label="Click Me!", style=discord.ButtonStyle.green)

    # Define what happens when the button is clicked
    async def button_callback(interaction):
        await interaction.response.send_message(f"🎉 {interaction.user.mention} clicked the button!", ephemeral=True)

    button.callback = button_callback

    # Create a view and add the button to it
    view = View()
    view.add_item(button)

    # Send the message with the button
    await ctx.send("Here is a button for you:", view=view)

@bot.command(name="eggs")
async def eggs(ctx, member: discord.Member = None):
    """Check how many eggs a user has collected."""
    member = member or ctx.author
    user_id = str(member.id)
    eggs_collected = easter_data.get(user_id, {}).get("eggs", 0)
    await ctx.send(f"🥚 {member.mention} has collected **{eggs_collected} eggs**!")

# Dictionary to track the last activity time for each guild
last_activity = {}

# List of random messages for the chat reviver
chat_reviver_messages = [
    "Hey everyone! What's up? 👋",
    "Let's keep the chat alive! What's on your mind? 💬",
    "Who's up for a fun conversation? 😄",
    "What's your favorite movie or TV show? 🎥",
    "If you could travel anywhere in the world, where would you go? 🌍",
    "What's the best thing that happened to you today? 🌟",
    "Let's play a quick game! What's 5 + 7? 🤔",
    "Share your favorite meme! 😂",
    "What's your favorite food? 🍕",
    "Who's ready for some fun? 🎉"
]
    

async def chat_reviver_task():
    """Send a random message every hour to revive the chat if no activity has occurred."""
    await bot.wait_until_ready()  # Ensure the bot is ready before starting the task
    while not bot.is_closed():
        try:
            for guild in bot.guilds:
                # Check if there has been activity in the last hour
                last_active = last_activity.get(guild.id, None)
                if last_active and (datetime.now() - last_active).total_seconds() < 18000:
                    logging.info(f"Skipping chat reviver for {guild.name} due to recent activity.")
                    continue

                # Find a role with "chat reviver" in its name
                chat_reviver_role = discord.utils.find(
                    lambda r: "chat reviver" in r.name.lower(),
                    guild.roles
                )

                # Find a general or chat-related channel
                target_channel = discord.utils.find(
                    lambda c: ("general" in c.name.lower() or "chat" in c.name.lower()) and isinstance(c, discord.TextChannel),
                    guild.channels
                )

                if chat_reviver_role and target_channel:
                    # Choose a random message and send it
                    random_message = random.choice(chat_reviver_messages)
                    await target_channel.send(f"{chat_reviver_role.mention} {random_message}")
                    logging.info(f"Chat reviver message sent to {target_channel.name} in {guild.name}.")
                else:
                    logging.warning(f"Chat reviver role or target channel not found in {guild.name}.")
        except Exception as e:
            logging.error(f"Error in chat reviver task: {e}")

        # Wait for 1 hour before checking again
        await asyncio.sleep(18000)

@bot.command(name="chatreviver-role")
@commands.has_permissions(administrator=True)
async def chatreviver_role(ctx):
    """Send a message to allow users to get the 'Chat Reviver' role by reacting."""
    try:
        # Create the embed for the Chat Reviver role
        embed = discord.Embed(
            title="Get the Chat Reviver Role",
            description=(
                "React with 🛠️ to get the **Chat Reviver** role.\n"
                "This role will be mentioned when the bot sends messages to revive the chat!"
            ),
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3593/3593455.png")  # Example icon

        # Send the embed message
        message = await ctx.send(embed=embed)

        # Add the 🛠️ reaction to the message
        await message.add_reaction("🛠️")

        # Save the message ID in the user_data.json file
        data = load_user_data()
        data["chat_reviver_message_id"] = message.id
        save_user_data(data)

        logging.info(f"Chat Reviver role message sent in {ctx.channel.name} (ID: {ctx.channel.id}). Message ID: {message.id}")
        await ctx.send("✅ Chat Reviver role message sent successfully!")
    except Exception as e:
        logging.error(f"Error in chatreviver_role command: {e}")
        await ctx.send(f"❌ An error occurred while setting up the Chat Reviver role: {e}")

def update_eggs(user_id, eggs_change):
    """Update the user's egg count."""
    user_id = str(user_id)
    if user_id not in easter_data:
        easter_data[user_id] = {"eggs": 0}
    easter_data[user_id]["eggs"] += eggs_change
    save_easter_data()

@bot.command(name="gems")
async def gems(ctx, member: discord.Member = None):
    """Check how many gems a user has collected."""
    member = member or ctx.author
    user_id = str(member.id)
    user_data = get_user_data(user_id)
    gems_collected = user_data.get("gems", 0)
    await ctx.send(f"💎 {member.mention} has collected **{gems_collected} gems**!")

# Bank commands
@bot.command(name="deposit")
async def deposit(ctx, amount: int):
    """Deposit coins into the bank."""
    if amount <= 0:
        await ctx.send("❌ You must deposit a positive amount of coins.")
        return

    user_id = ctx.author.id
    balance = get_coins(user_id)

    if balance < amount:
        await ctx.send(f"❌ You don't have enough coins to deposit. Your balance is **{balance} coins**.")
        return

    # Deduct from user's balance and add to the bank
    update_coins(user_id, -amount)
    update_bank_balance(user_id, amount)

    await ctx.send(f"✅ {ctx.author.mention}, you deposited **{amount} coins** into the bank.")

@bot.command(name="withdraw")
async def withdraw(ctx, amount: int):
    """Withdraw coins from the bank."""
    if amount <= 0:
        await ctx.send("❌ You must withdraw a positive amount of coins.")
        return

    user_id = ctx.author.id
    bank_balance = get_bank_balance(user_id)

    if bank_balance < amount:
        await ctx.send(f"❌ You don't have enough coins in the bank to withdraw. Your bank balance is **{bank_balance} coins**.")
        return

    # Deduct from the bank and add to user's balance
    update_bank_balance(user_id, -amount)
    update_coins(user_id, amount)

    await ctx.send(f"✅ {ctx.author.mention}, you withdrew **{amount} coins** from the bank.")

@bot.command(name="bank")
async def bank(ctx):
    """Check your bank balance."""
    user_id = ctx.author.id
    bank_balance = get_bank_balance(user_id)
    await ctx.send(f"🏦 {ctx.author.mention}, your bank balance is **{bank_balance} coins**.")

@bot.command(name="buygem")
async def buygem(ctx):
    """Buy a gem for 250 coins."""
    user_id = ctx.author.id
    cost = 250  # Cost of one gem

    # Check if the user has enough coins
    balance = get_coins(user_id)
    if balance < cost:
        await ctx.send(f"❌ {ctx.author.mention}, you don't have enough coins to buy a gem. You need **{cost} coins**, but you only have **{balance} coins**.")
        return

    # Deduct coins and add a gem
    update_coins(user_id, -cost)
    update_gems(user_id, 1)

    await ctx.send(f"✅ {ctx.author.mention}, you bought **1 gem** for **{cost} coins**! 💎")

crate_objects = [
    {"name": "Golden Egg", "rarity": "Legendary", "value": {"gems": 5}},
    {"name": "Diamond Shard", "rarity": "Legendary", "value": {"gems": 3}},
    {"name": "Mystic Feather", "rarity": "Epic", "value": {"gems": 2}},
    {"name": "Ancient Relic", "rarity": "Epic", "value": {"coins": 500}},
    {"name": "Silver Coin", "rarity": "Rare", "value": {"coins": 250}},
    {"name": "Bronze Coin", "rarity": "Rare", "value": {"coins": 100}},
    {"name": "Magic Scroll", "rarity": "Rare", "value": {"coins": 150}},
    {"name": "Wooden Shield", "rarity": "Uncommon", "value": {"coins": 50}},
    {"name": "Iron Sword", "rarity": "Uncommon", "value": {"coins": 75}},
    {"name": "Healing Potion", "rarity": "Uncommon", "value": {"coins": 30}},
    {"name": "Rusty Key", "rarity": "Common", "value": {"coins": 10}},
    {"name": "Old Map", "rarity": "Common", "value": {"coins": 15}},
    {"name": "Broken Compass", "rarity": "Common", "value": {"coins": 5}},
    {"name": "Phoenix Feather", "rarity": "Legendary", "value": {"gems": 4}},
    {"name": "Dragon Scale", "rarity": "Epic", "value": {"gems": 2}},
    {"name": "Enchanted Amulet", "rarity": "Epic", "value": {"coins": 400}},
    {"name": "Crystal Orb", "rarity": "Rare", "value": {"coins": 200}},
    {"name": "Golden Chalice", "rarity": "Rare", "value": {"coins": 300}},
    {"name": "Emerald Ring", "rarity": "Uncommon", "value": {"coins": 60}},
    {"name": "Sapphire Pendant", "rarity": "Uncommon", "value": {"coins": 80}},
    {"name": "Cursed Doll", "rarity": "Common", "value": {"coins": 20}},
    {"name": "Ancient Coin", "rarity": "Common", "value": {"coins": 25}},
    {"name": "Pirate's Hat", "rarity": "Rare", "value": {"coins": 150}},
    {"name": "Treasure Chest", "rarity": "Legendary", "value": {"gems": 6}},
    {"name": "Mystic Rune", "rarity": "Epic", "value": {"gems": 3}},
]

# Rarity weights for random selection
rarity_weights = {
    "Legendary": 1,  # 1% chance
    "Epic": 5,       # 5% chance
    "Rare": 15,      # 15% chance
    "Uncommon": 30,  # 30% chance
    "Common": 49     # 49% chance
}

import random

@bot.command(name="opencrate")
@cooldown(1, 60, BucketType.user) 
async def open_crate(ctx):
    """Open a crate to receive a random object."""
    # Select an object based on rarity
    rarities = [obj["rarity"] for obj in crate_objects]
    rarity = random.choices(list(rarity_weights.keys()), weights=rarity_weights.values(), k=1)[0]
    possible_objects = [obj for obj in crate_objects if obj["rarity"] == rarity]
    selected_object = random.choice(possible_objects)

    # Add the object to the user's inventory
    user_id = str(ctx.author.id)
    inventory = load_inventory()
    if user_id not in inventory:
        inventory[user_id] = []
    inventory[user_id].append(selected_object)
    save_inventory(inventory)
    
    # Update the user's crate count and check for trophies
    user_data = get_user_data(ctx.author.id)
    user_data["crates_opened"] = user_data.get("crates_opened", 0) + 1
    update_user_data(ctx.author.id, "crates_opened", user_data["crates_opened"])
    check_trophy_goals(ctx.author.id, ctx.channel)  # Pass the channel as the second argument

    # Notify the user
    await ctx.send(
        f"🎉 {ctx.author.mention}, you opened a crate and received a **{selected_object['name']}**! "
        f"(Rarity: {selected_object['rarity']})"
    )

@bot.command(name="exchange")
async def exchange(ctx, *, object_name: str):
    """Exchange an object for coins or gems."""
    user_id = str(ctx.author.id)
    inventory = load_inventory()

    # Check if the user owns the object
    if user_id not in inventory or not any(obj["name"].lower() == object_name.lower() for obj in inventory[user_id]):
        await ctx.send(f"❌ {ctx.author.mention}, you do not own an object named **{object_name}**.")
        return

    # Find the object in the user's inventory
    for obj in inventory[user_id]:
        if obj["name"].lower() == object_name.lower():
            selected_object = obj
            break

    # Exchange the object for coins or gems
    if "coins" in selected_object["value"]:
        update_coins(user_id, selected_object["value"]["coins"])
        await ctx.send(
            f"✅ {ctx.author.mention}, you exchanged **{selected_object['name']}** for "
            f"**{selected_object['value']['coins']} coins**!"
        )
    elif "gems" in selected_object["value"]:
        update_gems(user_id, selected_object["value"]["gems"])
        await ctx.send(
            f"✅ {ctx.author.mention}, you exchanged **{selected_object['name']}** for "
            f"**{selected_object['value']['gems']} gems**!"
        )

    # Remove the object from the user's inventory
    inventory[user_id].remove(selected_object)
    save_inventory(inventory)

@bot.command(name="inventory")
async def inventory(ctx):
    """Check your inventory."""
    user_id = str(ctx.author.id)
    inventory = load_inventory()

    if user_id not in inventory or not inventory[user_id]:
        await ctx.send(f"📦 {ctx.author.mention}, your inventory is empty.")
        return

    # Display the user's inventory
    embed = discord.Embed(
        title=f"{ctx.author.name}'s Inventory",
        description="Here are the items you own:",
        color=discord.Color.blue()
    )
    for obj in inventory[user_id]:
        # Safely get the value (either coins or gems)
        value = obj["value"].get("coins", obj["value"].get("gems", "Unknown"))
        value_type = "coins" if "coins" in obj["value"] else "gems"
        embed.add_field(
            name=obj["name"],
            value=f"Rarity: {obj['rarity']} | Value: {value} {value_type}",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command(name="trophies")
async def display_trophies(ctx):
    """Display the user's trophies."""
    user_id = str(ctx.author.id)
    user_trophies = trophy_data.get(user_id, [])

    # Create the base image
    base = Image.new("RGBA", (800, 400), (30, 30, 30))  # Dark background
    draw = ImageDraw.Draw(base)

    # Add a title
    font = ImageFont.truetype("arial.ttf", 40)
    draw.text((20, 20), f"{ctx.author.name}'s Trophies", fill=(255, 255, 255), font=font)

    # Add trophy icons
    x, y = 50, 100
    for trophy_id, trophy in trophies.items():
        icon_path = trophy["icon"] if trophy_id in user_trophies else "icons/trophies/placeholder.png"
        try:
            icon = Image.open(icon_path).convert("RGBA").resize((100, 100))  # Ensure the image has an alpha channel
            base.paste(icon, (x, y), icon)  # Paste the icon with transparency
        except FileNotFoundError:
            await ctx.send(f"❌ Missing file: `{icon_path}`. Please ensure the file exists.")
            return
        except Exception as e:
            await ctx.send(f"❌ An error occurred while processing `{icon_path}`: {e}")
            return

        draw.text((x, y + 110), trophy["name"], fill=(255, 255, 255), font=ImageFont.truetype("arial.ttf", 20))
        x += 150
        if x > 650:
            x = 50
            y += 150

    # Save the image to a BytesIO object
    buffer = BytesIO()
    base.save(buffer, format="PNG")
    buffer.seek(0)

    # Send the image
    await ctx.send(file=discord.File(fp=buffer, filename="trophies.png"))

@bot.command(name="sell")
async def sell(ctx):
    """Sell everything in your inventory for coins or gems."""
    user_id = str(ctx.author.id)
    inventory = load_inventory()

    # Check if the user has items in their inventory
    if user_id not in inventory or not inventory[user_id]:
        await ctx.send(f"📦 {ctx.author.mention}, your inventory is empty. Nothing to sell.")
        return

    # Calculate the total value of the inventory
    total_coins = sum(obj["value"].get("coins", 0) for obj in inventory[user_id])
    total_gems = sum(obj["value"].get("gems", 0) for obj in inventory[user_id])

    # Confirmation message
    confirmation_message = await ctx.send(
        f"⚠️ {ctx.author.mention}, are you sure you want to sell everything in your inventory?\n"
        f"You will receive **{total_coins} coins** and **{total_gems} gems**.\n"
        f"Type `yes` to confirm or `no` to cancel."
    )

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]

    try:
        response = await bot.wait_for("message", check=check, timeout=30.0)
        if response.content.lower() == "no":
            await ctx.send("❌ Sale canceled. Your inventory remains untouched.")
            return
        elif response.content.lower() == "yes":
            # Add the coins and gems to the user's balance
            update_coins(user_id, total_coins)
            update_gems(user_id, total_gems)

            # Clear the user's inventory
            inventory[user_id] = []
            save_inventory(inventory)

            await ctx.send(
                f"✅ {ctx.author.mention}, you sold everything in your inventory and received "
                f"**{total_coins} coins** and **{total_gems} gems**!"
            )
    except asyncio.TimeoutError:
        await ctx.send("⏰ Sale timed out. Your inventory remains untouched.")

@bot.command(name="modify_status")
@commands.check(is_owner)
async def modify_status(ctx, status_type: str, *, activity: str = None):
    """Modify the bot's status and activity."""
    global custom_status

    if status_type.lower() == "default":
        # Reset to default rotating statuses
        custom_status = None
        await ctx.send("✅ The bot's status has been reset to its default rotating behavior.")
        return

    # Validate the status type
    valid_status_types = ["playing", "watching", "listening", "streaming"]
    if status_type.lower() not in valid_status_types:
        await ctx.send(f"❌ Invalid status type. Choose from: {', '.join(valid_status_types)}.")
        return

    # Set the custom status
    if status_type.lower() == "playing":
        custom_status = discord.Game(activity)
    elif status_type.lower() == "watching":
        custom_status = discord.Activity(type=discord.ActivityType.watching, name=activity)
    elif status_type.lower() == "listening":
        custom_status = discord.Activity(type=discord.ActivityType.listening, name=activity)
    elif status_type.lower() == "streaming":
        custom_status = discord.Streaming(name=activity, url="https://www.twitch.tv/your_channel")  # Replace with your Twitch URL

    await bot.change_presence(status=discord.Status.online, activity=custom_status)
    await ctx.send(f"✅ The bot's status has been updated to **{status_type.capitalize()} {activity}**.")

@bot.command(name="reset")
@commands.check(is_owner)
async def reset(ctx):
    """Reset all data and delete all songs with triple confirmation."""
    # First confirmation
    await ctx.send("⚠️ **Do you wish to proceed?** This will delete ALL data and songs. Type `yes` to proceed or `no` to cancel.")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]

    try:
        response = await bot.wait_for("message", check=check, timeout=30.0)
        if response.content.lower() == "no":
            await ctx.send("❌ Reset canceled.")
            return
    except asyncio.TimeoutError:
        await ctx.send("⏰ You took too long to respond. Reset canceled.")
        return

    # Second confirmation
    await ctx.send("⚠️ **Are you ABSOLUTELY sure?** This will delete EVERYTHING. Type `yes` to proceed or `no` to cancel.")

    try:
        response = await bot.wait_for("message", check=check, timeout=30.0)
        if response.content.lower() == "no":
            await ctx.send("❌ Reset canceled.")
            return
    except asyncio.TimeoutError:
        await ctx.send("⏰ You took too long to respond. Reset canceled.")
        return

    # Final confirmation
    await ctx.send("⚠️ **ARE YOU SURE?** This is your FINAL WARNING. Type `yes` to proceed or `no` to cancel.")

    try:
        response = await bot.wait_for("message", check=check, timeout=30.0)
        if response.content.lower() == "no":
            await ctx.send("❌ Reset canceled.")
            return
    except asyncio.TimeoutError:
        await ctx.send("⏰ You took too long to respond. Reset canceled.")
        return

    # Perform the reset
    try:
        # Delete all JSON files
        data_files = ["data/user_data.json", "data/easter.json", "data/trophies.json", "data/warnings.json", "data/bank.json", "data/server_restrictions.json", "data/banned_servers.json"]
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
        os.execv(sys.executable, ["python", __file__, "--skip-input"])
    except Exception as e:
        await ctx.send(f"❌ An error occurred during the reset: {e}")

@bot.command(name="exchange_gems")
async def exchange_gems(ctx, gems: int):
    """Exchange gems for coins."""
    if gems <= 0:
        await ctx.send("❌ You must exchange at least 1 gem.")
        return

    user_id = ctx.author.id
    user_data = get_user_data(user_id)

    # Check if the user has enough gems
    if user_data["gems"] < gems:
        await ctx.send(f"❌ {ctx.author.mention}, you don't have enough gems to exchange. You need **{gems} gems**, but you only have **{user_data['gems']} gems**.")
        return

    # Define the conversion rate
    conversion_rate = 250  # 1 gem = 250 coins
    coins_earned = gems * conversion_rate

    # Deduct gems and add coins
    user_data["gems"] -= gems
    user_data["coins"] += coins_earned
    update_user_data(user_id, "gems", user_data["gems"])
    update_user_data(user_id, "coins", user_data["coins"])

    await ctx.send(f"✅ {ctx.author.mention}, you exchanged **{gems} gems** for **{coins_earned} coins**!")

@bot.command(name="announcement")
@commands.check(is_owner)
async def announcement(ctx, channel_name: str = None, *, message: str):
    """
    Send an announcement to all servers' announcement channels.
    If a specific channel name is provided, send the message to that channel instead.
    """
    if not message:
        await ctx.send("❌ You must provide a message to send.")
        return

    # Iterate through all servers the bot is in
    for guild in bot.guilds:
        try:
            # If a specific channel name is provided
            if channel_name:
                target_channel = discord.utils.find(
                    lambda c: channel_name.lower() in c.name.lower() and isinstance(c, discord.TextChannel),
                    guild.channels
                )
            else:
                # Default to an announcements channel
                target_channel = discord.utils.find(
                    lambda c: "announcement" in c.name.lower() and isinstance(c, discord.TextChannel),
                    guild.channels
                )

            if target_channel:
                # Send the message to the target channel
                await target_channel.send(f"📢 **Announcement:**\n{message}")
                logging.info(f"Announcement sent to {target_channel.name} in {guild.name}.")
            else:
                logging.warning(f"No suitable channel found in {guild.name}.")
                # Optionally notify the server owner if no suitable channel is found
                owner = guild.owner
                if owner:
                    await owner.send(
                        f"❌ Could not find a suitable channel in your server **{guild.name}** "
                        f"to send the announcement. Please ensure an announcements channel exists."
                    )
        except discord.Forbidden:
            logging.warning(f"Permission denied to send message in {guild.name}.")
        except Exception as e:
            logging.error(f"Error sending announcement in {guild.name}: {e}")

    await ctx.send("✅ Announcement sent to all servers.")
    
@bot.command(name="lookup")
async def lookup(ctx, input_value: str):
    """Look up a user by their ID or username."""
    # Check if the input is a user ID
    if input_value.isdigit():
        user = await bot.fetch_user(int(input_value))
        if user:
            await ctx.send(f"🔍 User ID `{input_value}` belongs to: **{user.name}#{user.discriminator}**")
        else:
            await ctx.send(f"❌ No user found with ID `{input_value}`.")
    else:
        # Check if the input is a mention or username
        user = discord.utils.get(ctx.guild.members, name=input_value) or discord.utils.get(ctx.guild.members, mention=input_value)
        if user:
            await ctx.send(f"🔍 User `{user.name}#{user.discriminator}` has the ID: **{user.id}**")
        else:
            await ctx.send(f"❌ No user found with the name or mention `{input_value}`.")
            
# EXCEPTIONAL DELETE AFTER EVENT.
    
# Add a dictionary to track user strikes
user_strikes = {}

@bot.command(name="strike")
@commands.has_permissions(manage_roles=True)
async def strike(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Give a strike to a user."""
    user_id = str(member.id)
    user_data = load_user_data()

    # Initialize strikes if not present
    if user_id not in user_data:
        user_data[user_id] = {"xp": 0, "level": 1, "coins": 100, "warnings": [], "strikes": 0}
    elif "strikes" not in user_data[user_id]:
        user_data[user_id]["strikes"] = 0

    # Increment the user's strikes
    user_data[user_id]["strikes"] += 1
    strikes = user_data[user_id]["strikes"]
    save_user_data(user_data)

    await ctx.send(f"⚠️ {member.mention} has been given a strike. Total strikes: **{strikes}**. Reason: {reason}")

    # Take action based on the number of strikes
    if strikes == 3:
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False)
        await member.add_roles(mute_role)
        await ctx.send(f"🔇 {member.mention} has been muted for accumulating 3 strikes.")
    elif strikes == 5:
        await member.kick(reason="Reached 5 strikes")
        await ctx.send(f"👢 {member.mention} has been kicked for reaching 5 strikes.")
    elif strikes >= 7:
        await member.ban(reason="Reached 7 strikes")
        await ctx.send(f"⛔ {member.mention} has been banned for reaching 7 strikes.")

@bot.command(name="clearstrikes")
@commands.has_permissions(manage_roles=True)
async def clearstrikes(ctx, member: discord.Member):
    """Clear all strikes for a user."""
    user_id = str(member.id)
    user_data = load_user_data()

    if user_id in user_data and "strikes" in user_data[user_id]:
        user_data[user_id]["strikes"] = 0
        save_user_data(user_data)
        await ctx.send(f"✅ Cleared all strikes for {member.mention}.")
    else:
        await ctx.send(f"❌ {member.mention} has no strikes.")
        
@bot.command(name="infractions")
@commands.has_permissions(manage_roles=True)
async def infractions(ctx, member: discord.Member):
    """View a user's strikes and warnings."""
    user_id = str(member.id)
    user_data = load_user_data()

    # Extract strikes and warnings
    strikes = user_data.get(user_id, {}).get("strikes", 0)
    warnings = len(user_data.get(user_id, {}).get("warnings", []))

    await ctx.send(
        f"📋 **Infractions for {member.mention}:**\n"
        f"- Strikes: {strikes}\n"
        f"- Warnings: {warnings}"
    )
    
@bot.command(name="setlimitations")
@commands.has_permissions(administrator=True)
async def setlimitations(ctx, level: str = None):
    """Set the offensive word filtering level."""
    if not level:
        await ctx.send(
            "❓ **Usage:** `?setlimitations <level>`\n"
            "Levels:\n"
            "1 - Minimal filtering\n"
            "2 - Moderate filtering\n"
            "3 - Strict filtering\n"
            "4 - Very strict filtering\n"
            "5 - Block all offensive words"
        )
        return

    # Validate level
    if level not in ["1", "2", "3", "4", "5"]:
        await ctx.send("❌ Invalid level. Please choose a level between 1 and 5.")
        return

    # Save the level to the JSON file
    guild_id = str(ctx.guild.id)
    limitations = load_limitations()
    limitations[guild_id] = int(level)
    save_limitations(limitations)

    await ctx.send(f"✅ Offensive word filtering level set to **{level}**.")

# EXCEPTIONAL DELETE AFTER EVENT.

bot.command(name="easter_finale")
@commands.check(is_owner)
async def easter_finale(ctx):
    """Trigger the Easter Event Finale."""
    # Announce the finale
    await ctx.send("🎉 **The Easter Event Finale has begun!** 🎉")

    # Fetch the top 3 users with the most eggs
    top_users = sorted(
        easter_data.items(),
        key=lambda x: x[1].get("eggs", 0),
        reverse=True
    )[:3]

    # Prepare the leaderboard message
    embed = discord.Embed(
        title="🏆 Easter Event Leaderboard",
        description="Here are the top 3 egg collectors:",
        color=discord.Color.gold()
    )
    for rank, (user_id, data) in enumerate(top_users, start=1):
        user = await bot.fetch_user(int(user_id))
        embed.add_field(
            name=f"{rank}. {user.name}#{user.discriminator}",
            value=f"🥚 Eggs Collected: {data['eggs']}",
            inline=False
        )

    # Send the leaderboard
    await ctx.send(embed=embed)

    # Reward the top 3 users
    rewards = [
        {"coins": 1000, "gems": 10, "role": "Easter Champion 🥇"},
        {"coins": 750, "gems": 7, "role": "Easter Runner-Up 🥈"},
        {"coins": 500, "gems": 5, "role": "Easter Participant 🥉"}
    ]
    for rank, (user_id, reward) in enumerate(zip(top_users, rewards), start=1):
        user_id = user_id[0]
        user = ctx.guild.get_member(int(user_id))
        if user:
            # Add coins and gems
            update_coins(user_id, reward["coins"])
            update_gems(user_id, reward["gems"])

            # Assign the role with a random blue color
            random_blue = discord.Color.from_rgb(
                random.randint(0, 50),  # Low red value
                random.randint(100, 200),  # Medium green value
                random.randint(200, 255)  # High blue value
            )
            role = discord.utils.get(ctx.guild.roles, name=reward["role"])
            if not role:
                role = await ctx.guild.create_role(name=reward["role"], color=random_blue)
            await user.add_roles(role)

            # Notify the user
            await ctx.send(
                f"🎉 {user.mention} has been rewarded with **{reward['coins']} coins**, **{reward['gems']} gems**, "
                f"and the **{reward['role']}** role!"
            )

    # Announce the end of the event
    await ctx.send("🎊 **The Easter Event has officially ended! Thank you for participating!** 🎊")

async def send_closing_message():
    """Send a closing message to all servers."""
    for guild in bot.guilds:
        channel = discord.utils.find(
            lambda c: "announcements" in c.name.lower() or "general" in c.name.lower(),
            guild.text_channels
        )
        if channel:
            await channel.send(
                "🎊 **The Easter Event has officially ended!** 🎊\n"
                "Thank you to everyone who participated. Stay tuned for more events in the future!"
            )

async def schedule_easter_finale():
    """Schedule the Easter Event Finale."""
    await bot.wait_until_ready()
    now = datetime.now()
    target_time = datetime.combine(now.date(), datetime.min.time()) + timedelta(days=1, hours=2)  # 00:00 UTC+2
    wait_time = (target_time - now).total_seconds()

    await asyncio.sleep(wait_time)  # Wait until the target time
    channel = discord.utils.get(bot.get_all_channels(), name="announcements")  # Replace with your channel name
    if channel:
        await channel.send("🎉 **The Easter Event Finale has begun!** 🎉")
    await easter_finale(channel)
    await send_closing_message()

@bot.command(name="setlogging")
@commands.has_permissions(administrator=True)
async def setlogging(ctx, action: str = None):
    """Enable or disable logging for the server."""
    if action not in ["enable", "disable"]:
        await ctx.send("❓ **Usage:** `?setlogging <enable|disable>`")
        return

    guild_id = str(ctx.guild.id)
    logging_config = load_logging_config()

    if action == "enable":
        logging_config[guild_id] = True
        save_logging_config(logging_config)
        await ctx.send("✅ Logging has been **enabled** for this server.")
    elif action == "disable":
        logging_config[guild_id] = False
        save_logging_config(logging_config)
        await ctx.send("✅ Logging has been **disabled** for this server.")
    
async def log_event(guild, message):
    """Log an event to the logs channel if logging is enabled."""
    logging_config = load_logging_config()
    guild_id = str(guild.id)

    if logging_config.get(guild_id, False):  # Check if logging is enabled
        logs_channel = discord.utils.get(guild.text_channels, name="logs")
        if logs_channel:
            try:
                await logs_channel.send(message)
            except discord.Forbidden:
                print(f"❌ Unable to send message to the logs channel in {guild.name}.")

if __name__ == "__main__":
    print("🚀 Starting the bot...")
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-input", action="store_true", help="Skip input prompts for auto-restart")
    args = parser.parse_args()
    try:
        bot.run(token)  # Replace with your bot token
    except Exception as e:
        print(f"❌ Error starting the bot: {e}")

save_user_data()