"""
# Ediscord variables package
Variable package for Ediscord.

Contains:
- All global variables for easier access and maintenance.
"""

# --------------------- IMPORTS --------------------
import time
from os import environ
from dotenv import load_dotenv
from datetime import datetime, timedelta
import openai
import os
import discord
import logging
import json
from discord.ext.commands import CooldownMapping
from discord.ext.commands import BucketType
from transformers.pipelines import pipeline
from googletrans import Translator
from PIL import Image, ImageDraw, ImageFont
from Ediscord import utils
from io import BytesIO
# --------------------- VARIABLES --------------------
start_time = time.time()
is_sleeping = False  # Tracks whether the bot is in sleep mode
custom_status = None  # Tracks the custom status and activity
token = os.environ["TOKEN"]
SPAM_THRESHOLD = 5  # Number of messages allowed within the time window
TIME_WINDOW = 10  # Time window in seconds
last_activity_time = datetime.now()
EASTER_FILE = "data/easter.json"
TROPHY_FILE = "data/trophies.json"
BOT_DATA_FILE = "bot_data.txt"
WEBSITE_COMMANDS_FILE = "website_commands.txt"
LIMITATIONS_FILE = "f:\\Coding\\Discord\\BOT3\\data\\limitations.json"
LOGGING_CONFIG_FILE = "data/logging_config.json"
trophies = {
    "trophy_1": {"name": "Coin Collector", "goal": "Collect 1,000 coins", "icon": "icons/coin_collector.png"},
    "trophy_2": {"name": "Gem Hoarder", "goal": "Collect 10 gems", "icon": "icons/gem_hoarder.png"},
    "trophy_3": {"name": "Impossible Victor", "goal": "Win 10 Impossible Easter fights", "icon": "icons/impossible_victor.png"},
    "trophy_4": {"name": "Level Master", "goal": "Reach Level 50", "icon": "icons/level_master.png"},
    "trophy_5": {"name": "Crate Opener", "goal": "Open 50 crates", "icon": "icons/crate_opener.png"},
}
OPENAI_API_KEY = environ.get("OPEN_API_KEY")
openai.api_key = OPENAI_API_KEY
UNSPLACH_API_KEY = os.environ.get("UNSPLASH_API_KEY")
OPENWHEATHER_KEY = os.environ.get("OPENWEATHER_KEY")
openwheather = OPENWHEATHER_KEY
intents = discord.Intents.default()
intents.message_content = True  # This is required for processing commands
intents.guilds = True
intents.members = True
intents.reactions = True
banned_servers_file = "data/banned_servers.json"
server_restrictions_file = "data/server_restrictions.json"
BANK_FILE = "data/bank.json"
bot_info_file = "data/bot_info.json"
game_ongoing = False
board = [" " for _ in range(9)]
custom_cooldown = CooldownMapping.from_cooldown(
    1, 10, BucketType.user
)  # 1 message per 60 seconds
INVENTORY_FILE = "data/inventory.json"
USER_DATA_FILE = "data/user_data.json"
current_status = None
level_roles = {
    5: "🔵 • NOVICE",
    10: "🔵 • APPRENTICE",
    20: "🔵 • EXPERT",
    30: "🔵 • MASTER",
    50: "🔵 • GRANDMASTER",
}
last_activity = {}
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
    "Who's ready for some fun? 🎉",
]
valid_commands = [
    "help",
    "info",
    "serverinfo",
    "shutdown",
    "poll",
    "ask",
    "analyse",
    "createrole",
    "giverole",
    "removerole",
    "warn",
    "kick",
    "ban",
    "givexp",
    "gainlvl",
    "copydm",
    "copychannel",
    "colorrole",
    "verify",
    "copy",
    "choose_country",
    "startgame",
    "checkvc",
    "continue",
    "endgame",
    "timeout",
    "search_img",
    "zen",
    "BServer",
    "UBServer",
    "MServer",
    "update",
    "unzen",
    "balance",
    "daily",
    "steal",
    "give",
    "stealadmin",
    "wheel",
    "leaderboard",
    "trivia",
    "reminder",
    "join",
    "leave",
    "mute",
    "unmute",
    "purge",
    "rps",
    "setwelcome",
    "afk",
    "restart",
    "changelog",
    "zen",
    "play",
    "download",
    "upload",
    "queue",
]
message_cooldowns = {}
afk_users = {}
welcome_messages = {}
ffmpeg_path = r"C:\Users\roland\Downloads\ffmpeg-2025-03-31-git-35c091f4b7-full_build\bin\ffmpeg.exe"
qa_pipeline = pipeline("text-generation", model="gpt2")
translator = Translator()
crate_objects = [
    {"name": "Golden Egg", "rarity": "Legendary", "value": {"gems": 1000}},
    {"name": "Diamond Shard", "rarity": "Legendary", "value": {"gems": 50}},
    {"name": "Mystic Feather", "rarity": "Epic", "value": {"gems": 5}},
    {"name": "Ancient Relic", "rarity": "Epic", "value": {"coins": 750}},
    {"name": "Silver Coin", "rarity": "Rare", "value": {"coins": 250}},
    {"name": "Bronze Coin", "rarity": "Rare", "value": {"coins": 100}},
    {"name": "Magic Scroll", "rarity": "Rare", "value": {"coins": 150}},
    {"name": "Wooden Shield", "rarity": "Uncommon", "value": {"coins": 50}},
    {"name": "Iron Sword", "rarity": "Uncommon", "value": {"coins": 75}},
    {"name": "Healing Potion", "rarity": "Uncommon", "value": {"coins": 30}},
    {"name": "Rusty Key", "rarity": "Common", "value": {"coins": 10}},
    {"name": "Old Map", "rarity": "Common", "value": {"coins": 15}},
    {"name": "Broken Compass", "rarity": "Common", "value": {"coins": 5}},
    {"name": "Phoenix Feather", "rarity": "Legendary", "value": {"gems": 100}},
    {"name": "Dragon Scale", "rarity": "Epic", "value": {"gems": 4}},
    {"name": "Enchanted Amulet", "rarity": "Epic", "value": {"coins": 1000}},
    {"name": "Crystal Orb", "rarity": "Rare", "value": {"coins": 200}},
    {"name": "Golden Chalice", "rarity": "Rare", "value": {"coins": 300}},
    {"name": "Emerald Ring", "rarity": "Uncommon", "value": {"coins": 60}},
    {"name": "Sapphire Pendant", "rarity": "Uncommon", "value": {"coins": 80}},
    {"name": "Cursed Doll", "rarity": "Common", "value": {"coins": 20}},
    {"name": "Ancient Coin", "rarity": "Common", "value": {"coins": 25}},
    {"name": "Pirate's Hat", "rarity": "Rare", "value": {"coins": 150}},
    {"name": "Treasure Chest", "rarity": "Legendary", "value": {"gems": 100}},
    {"name": "Mystic Rune", "rarity": "Epic", "value": {"gems": 3}},
]

# Rarity weights for random selection
rarity_weights = {
    "Legendary": 1,  # 1% chance
    "Epic": 5,  # 5% chance
    "Rare": 15,  # 15% chance
    "Uncommon": 30,  # 30% chance
    "Common": 49,  # 49% chance
}
user_strikes = {}
logger = logging.getLogger(__name__)
bubble_text = "Welcome!"
bubble_x, bubble_y = 670, 60
bubble_w, bubble_h = 170, 50
bubble_rect = (bubble_x, bubble_y, bubble_x + bubble_w, bubble_y + bubble_h)
AKARI_POINTS_FILE = "data/akari_points.json"
AKARI_EVENT_START = datetime(2025, 5, 16)  # Set to event start date
AKARI_EVENT_END = AKARI_EVENT_START + timedelta(days=30)
AKARI_REWARDS_FILE = "data/akari_rewards.json"
AKARI_REWARDS = {
    "voice": {"cost": 50, "desc": "Send 1 voice message (role removed after use)"},
    "image": {"cost": 30, "desc": "Send 1 image (role removed after use)"},
    "nickname": {"cost": 40, "desc": "Change your nickname for 24h"},
    "shoutout": {"cost": 60, "desc": "Get a custom shoutout in announcements"},
    "colorrole": {"cost": 80, "desc": "Pick a custom color role for 24h"},
    "pin": {"cost": 25, "desc": "Pin one message of your choice"},
    "emoji": {"cost": 100, "desc": "Add a custom emoji for 24h"},
    "poll": {"cost": 35, "desc": "Create a server-wide poll"},
    "highlight": {"cost": 20, "desc": "Highlight a message in #highlights"},
    "priorityqueue": {"cost": 70, "desc": "Skip to the front of the music queue once"},
    "gift": {"cost": 50, "desc": "Gift 100 coins to another user instantly"},
}
# --------------------- CONDITIONAL VARIABLES --------------------
if os.path.exists(TROPHY_FILE):
    with open(TROPHY_FILE, "r") as f:
        trophy_data = json.load(f)
else:
    trophy_data = {}

if os.path.exists(EASTER_FILE):
    with open(EASTER_FILE, "r") as f:
        easter_data = json.load(f)
else:
    easter_data = {}

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

# Load or initialize bot info
if os.path.exists(bot_info_file):
    try:
        with open(bot_info_file, "r") as f:
            bot_info = json.load(f)
    except json.JSONDecodeError:
        bot_info = {"version": "1.6.2", "new_stuff": "Initial release"}
else:
    bot_info = {"version": "1.6.2", "new_stuff": "Initial release"}

