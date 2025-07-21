"""
# Ediscord utils package
Utility package for Ediscord.

Contains:
- Helper fonctions for easier maintenance.
"""
# ---------------------------------------------------------------------------------------------------
# --------------------------------------------- IMPORTS ---------------------------------------------
# ---------------------------------------------------------------------------------------------------

import json, os, logging, discord
from discord.ext import commands
from datetime import datetime
from Ediscord import variables
import asyncio
import time
import sys
import random
import itertools
from PIL import Image, ImageDraw
import psutil
import shutil
import glob
disabled_variants = set()

# ---------------------------------------------------------------------------------------------------
# -------------------------------------------- DEFINITONS -------------------------------------------
# ---------------------------------------------------------------------------------------------------

def load_logging_config():
    """Load logging configuration from the JSON file."""
    try:
        with open(variables.LOGGING_CONFIG_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_logging_config(data):
    """Save logging configuration to the JSON file."""
    with open(variables.LOGGING_CONFIG_FILE, "w") as file:
        json.dump(data, file, indent=4)

def save_trophy_data():
    """Save trophy data to the JSON file."""
    with open(variables.TROPHY_FILE, "w") as f:
        json.dump(variables.trophy_data, f, indent=4)

def is_owner(ctx):
    """Check if the command issuer is the bot owner."""
    return ctx.author.id == 917515232065228890  # Replace with your Discord user ID

async def is_owner_async(ctx):
    """Async version for use in command checks."""
    return ctx.author.id == 917515232065228890  # Same logic, but async

def admin_or_owner():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator or await is_owner_async(ctx)
    return commands.check(predicate)

def save_easter_data():
    """Save the easter data to the JSON file."""
    with open(variables.EASTER_FILE, "w") as f:
        json.dump(variables.easter_data, f, indent=4)
def load_inventory():
    """Load the inventory data from the JSON file."""
    if os.path.exists(variables.INVENTORY_FILE):
        with open(variables.INVENTORY_FILE, "r") as f:
            return json.load(f)
    return {}

def award_trophy(user_id, trophy_id):
    """Award a trophy to a user."""
    user_id = str(user_id)
    if user_id not in variables.trophy_data:
        variables.trophy_data[user_id] = []
    if trophy_id not in variables.trophy_data[user_id]:
        variables.trophy_data[user_id].append(trophy_id)
        save_trophy_data()
        return True  # Trophy awarded
    return False  # Trophy already owned

def save_inventory(inventory):
    """Save the inventory data to the JSON file."""
    with open(variables.INVENTORY_FILE, "w") as f:
        json.dump(inventory, f, indent=4)

def save_bank_data():
    """Save the bank data to the JSON file."""
    with open(variables.BANK_FILE, "w") as f:
        json.dump(variables.bank_data, f, indent=4)

def get_bank_balance(user_id):
    """Get the bank balance of a user."""
    user_id = str(user_id)
    return variables.bank_data.get(user_id, 0)

def update_bank_balance(user_id, amount):
    """Update the bank balance of a user."""
    user_id = str(user_id)
    if user_id not in variables.bank_data:
        variables.bank_data[user_id] = 0
    variables.bank_data[user_id] += amount
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

def save_user_data(data: dict):
    try:
        # Ensure correct structure: all keys must be user IDs
        cleaned_data = {}
        for k, v in data.items():
            if k.isdigit():
                cleaned_data[k] = v
            else:
                print(f"⚠️ Warning: Skipping malformed root key '{k}'")

        # Backup before saving
        os.makedirs(variables.BACKUP_FOLDER, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{timestamp}_user_data.json"
        backup_path = os.path.join(variables.BACKUP_FOLDER, backup_filename)
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, indent=4)

        # Write to log
        with open(variables.LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"{datetime.now()}: {backup_filename}\n")

        # Delete oldest if too many backups
        backups = sorted(os.listdir(variables.BACKUP_FOLDER))
        while len(backups) > variables.MAX_BACKUPS:
            os.remove(os.path.join(variables.BACKUP_FOLDER, backups.pop(0)))

        # Final write to main file
        with open(variables.USER_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, indent=4)

    except Exception as e:
        print(f"❌ Error saving user data: {e}")

def load_user_data():
    """Load user data from the JSON file."""
    try:
        # Check if the file exists
        if not os.path.exists(variables.USER_DATA_FILE):
            return {}

        # Read the data from the file
        with open(variables.USER_DATA_FILE, "r") as f:
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
        with open(variables.LIMITATIONS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_limitations(data):
    """Save limitations to the JSON file."""
    with open(variables.LIMITATIONS_FILE, "w") as file:
        json.dump(data, file, indent=4)

def get_user_data(user_id):
    """Get data for a specific user."""
    data = load_user_data()
    user_id_str = str(user_id) # Convert user_id to string once

    if user_id_str not in data or not isinstance(data[user_id_str], dict):
        # Initialize default values for new users or if data is corrupted/not a dict
        data[user_id_str] = {"xp": 0, "level": 1, "coins": 100, "gems": 0, "balance": 0, "warnings": []}
        save_user_data(data)
    else:
        # Ensure all required keys exist for existing users
        user_data = data[user_id_str]
        user_data.setdefault("xp", 0)
        user_data.setdefault("level", 1)
        user_data.setdefault("coins", 100)
        user_data.setdefault("gems", 0)
        user_data.setdefault("warnings", [])
        user_data.setdefault("balance", 0) # Added 'balance' for consistency
        data[user_id_str] = user_data # Reassign after setdefault calls

    return data[user_id_str]

def update_user_data(user_id, key, value):
    """Update a single key for a specific user in the user_data file."""
    data = load_user_data()
    user_id = str(user_id)

    if user_id not in data:
        data[user_id] = {
            "xp": 0,
            "level": 1,
            "coins": 100,
            "warnings": [],
            "censored_count": 0,
            "strikes": 0,
            "gems": 0,
            "balance": 0,
        }

    data[user_id][key] = value
    save_user_data(data)


# Save warnings data
def save_warnings_data():
    with open("data/warnings.json", "w") as f:
        json.dump(variables.warnings_data, f)

# Add this function to get the logs channel
def get_logs_channel(guild):
    return discord.utils.get(guild.text_channels, name="『📂』logs "or "logs")

# Function to get the welcome and bye channels
def get_channel_by_name(guild, channel_name):
    return discord.utils.get(guild.text_channels, name="『🎊』all-announcements")

# Save banned servers data
def save_banned_servers():
    with open(variables.banned_servers_file, "w") as f:
        json.dump(variables.banned_servers, f)

# Save server restrictions data
def save_server_restrictions():
    with open(variables.server_restrictions_file, "w") as f:
        json.dump(variables.server_restrictions, f)

def backup_file(json_path, max_backups=10):
    """Create a dated backup of the given JSON file, organized by folder, and purge oldest if needed."""
    if not os.path.exists(json_path):
        print(f"⚠️ Tried to back up missing file: {json_path}")
        return

    filename = os.path.basename(json_path)
    base_name = os.path.splitext(filename)[0]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    backup_folder = os.path.join("backups", base_name)
    os.makedirs(backup_folder, exist_ok=True)

    backup_filename = f"{timestamp}_{filename}"
    backup_path = os.path.join(backup_folder, backup_filename)

    try:
        shutil.copy2(json_path, backup_path)

        # Log only after successful backup
        log_path = os.path.join("backups", "backup_log.txt")
        log_entry = f"[{timestamp}] Backed up '{json_path}' to '{backup_path}'\n"
        with open(log_path, "a") as log_file:
            log_file.write(log_entry)

        # Clean old backups
        existing_backups = sorted(glob.glob(os.path.join(backup_folder, f"*_{filename}")))
        if len(existing_backups) > max_backups:
            to_delete = existing_backups[:-max_backups]
            for path in to_delete:
                try:
                    os.remove(path)
                    print(f"🗑️ Removed old backup: {path}")
                except Exception as e:
                    print(f"❌ Failed to delete backup {path}: {e}")

    except Exception as e:
        print(f"❌ Failed to back up {json_path}: {e}")

def write_bot_data(bot):
    """Write bot stats and leaderboard to bot_data.txt."""
    # Load user data
    try:
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss // 1024 // 1024  # MB
        cpu = process.cpu_percent()
    except ImportError:
        mem = cpu = "N/A"

    user_data = load_user_data()

    total_users = len(bot.users)
    active_users = sum(1 for m in bot.get_all_members() if m.status != discord.Status.offline)
    total_commands = getattr(bot, "total_commands", 0)  # Only works if you set this attribute yourself
    launch_time = getattr(bot, "launch_time", None)
    uptime_seconds = int(time.time() - launch_time) if launch_time else 0
    uptime_str = time.strftime("%Hh %Mm %Ss", time.gmtime(uptime_seconds))
    bot_status = "Running" if bot.is_ready() else "Not Running"
    bot_version = getattr(bot, "version", "unknown")  # Only works if you set this attribute yourself
    python_version = sys.version.replace("\n", " ")
    guilds = list(bot.guilds)
    num_guilds = len(guilds)
    guild_ids = [str(g.id) for g in guilds]
    num_channels = sum(len(g.channels) for g in guilds)
    num_roles = sum(len(g.roles) for g in guilds)
    num_emojis = sum(len(g.emojis) for g in guilds)
    loaded_cogs = list(bot.cogs.keys())
    all_commands = [cmd.name for cmd in bot.commands]
    last_restart = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(launch_time)) if launch_time else "unknown"


    leaderboard = sorted(
        [
            {"user_id": user_id, "coins": user_info.get("coins", 0)}
            for user_id, user_info in user_data.items()
            if isinstance(user_info, dict)
        ],
        key=lambda x: x["coins"],
        reverse=True
    )

    # Format leaderboard as a string (e.g., "User123:1000,User456:800")
    leaderboard_str = ",".join(
        f"{entry['user_id']}:{entry['coins']}" for entry in leaderboard[:10]  # Top 10 users
    )

    # Prepare data to write to the file
    data = (
        f"total_users={total_users}\n"
        f"active_users={active_users}\n"
        f"total_commands={total_commands}\n"
        f"uptime={uptime_str}\n"
        f"bot_status={bot_status}\n"
        f"leaderboard={leaderboard_str}\n"
        f"bot_version={bot_version}\n"
        f"python_version={python_version}\n"
        f"num_guilds={num_guilds}\n"
        f"guild_ids={json.dumps(guild_ids)}\n"
        f"num_channels={num_channels}\n"
        f"num_roles={num_roles}\n"
        f"num_emojis={num_emojis}\n"
        f"loaded_cogs={json.dumps(loaded_cogs)}\n"
        f"all_commands={json.dumps(all_commands)}\n"
        f"memory_usage_mb={mem}\n"
        f"cpu_usage_percent={cpu}\n"
        f"last_restart={last_restart}\n"
    )

    print("Writing data to bot_data.txt.")  # Debug log
    with open(variables.BOT_DATA_FILE, "w", encoding="utf-8") as f:
        f.write(data)

def read_website_command():
    """Read the latest command from website_commands.txt."""
    if not os.path.exists(variables.WEBSITE_COMMANDS_FILE):
        return None
    with open(variables.WEBSITE_COMMANDS_FILE, "r") as f:
        return f.read().strip()

def get_uptime():
    """Calculate bot uptime."""
    uptime_seconds = time.time() - variables.start_time
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

# Save bot info
def save_bot_info():
    with open(variables.bot_info_file, "w") as f:
        json.dump(variables.bot_info, f)

def get_truth_or_dare_vc(guild):
    return discord.utils.get(guild.voice_channels, name="truth-or-dare")


# Function to get the Truth or Dare text channel
def get_truth_or_dare_text_channel(guild):
    return discord.utils.get(guild.text_channels, name="truth-or-dare")


def assign_numbers_to_players(members):
    player_numbers = {
        member.display_name: index + 1 for index, member in enumerate(members)
    }
    return player_numbers


def game_logic(ctx):
    vc_channel = get_truth_or_dare_vc(ctx.guild)
    text_channel = get_truth_or_dare_text_channel(ctx.guild)
    members_in_vc = [member for member in vc_channel.members if not member.bot]
    player_numbers = assign_numbers_to_players(members_in_vc)
    player_names = ", ".join(
        f"{name} ({number})" for name, number in player_numbers.items()
    )
    ctx.send(f"Players: {player_numbers}")
    return player_names

def print_board():
    return f"""
        {variables.board[0]} | {variables.board[1]} | {variables.board[2]}
        ---------
        {variables.board[3]} | {variables.board[4]} | {variables.board[5]}
        ---------
        {variables.board[6]} | {variables.board[7]} | {variables.board[8]}
        """


def check_winner():
    win_conditions = [
        [0, 1, 2],
        [3, 4, 5],
        [6, 7, 8],  # Rows
        [0, 3, 6],
        [1, 4, 7],
        [2, 5, 8],  # Columns
        [0, 4, 8],
        [2, 4, 6],  # Diagonals
    ]
    for condition in win_conditions:
        if variables.board[condition[0]] == variables.board[condition[1]] == variables.board[condition[2]] != " ":
            return True
    return False

def check_trophy_goals(user_id, channel):
    """Check if a user has met any trophy goals and notify in the server channel."""
    user_data = get_user_data(user_id)

    # Trophy 1: Collect 1,000 coins
    if user_data["coins"] >= 1000:
        if award_trophy(user_id, "trophy_1"):
            bonus_xp = 100  # Example: 100 XP for earning this trophy
            user_data["xp"] += bonus_xp
            update_user_data(user_id, "xp", user_data["xp"])
            asyncio.create_task(
                channel.send(
                    f"🏆 You earned the **Coin Collector** trophy and received **{bonus_xp} bonus XP**!"
                )
            )

    # Trophy 2: Collect 10 gems
    if variables.easter_data.get(str(user_id), {}).get("gems", 0) >= 10:
        if award_trophy(user_id, "trophy_2"):
            bonus_xp = 150  # Example: 150 XP for earning this trophy
            user_data["xp"] += bonus_xp
            update_user_data(user_id, "xp", user_data["xp"])
            asyncio.create_task(
                channel.send(
                    f"🏆 You earned the **Gem Hoarder** trophy and received **{bonus_xp} bonus XP**!"
                )
            )

    # Trophy 3: Win 10 Impossible Easter fights
    if user_data.get("impossible_wins", 0) >= 10:
        if award_trophy(user_id, "trophy_3"):
            bonus_xp = 200  # Example: 200 XP for earning this trophy
            user_data["xp"] += bonus_xp
            update_user_data(user_id, "xp", user_data["xp"])
            asyncio.create_task(
                channel.send(
                    f"🏆 You earned the **Impossible Victor** trophy and received **{bonus_xp} bonus XP**!"
                )
            )

    # Trophy 4: Reach Level 50
    if user_data["level"] >= 50:
        if award_trophy(user_id, "trophy_4"):
            bonus_xp = 500  # Example: 500 XP for earning this trophy
            user_data["xp"] += bonus_xp
            update_user_data(user_id, "xp", user_data["xp"])
            asyncio.create_task(
                channel.send(
                    f"🏆 You earned the **Level Master** trophy and received **{bonus_xp} bonus XP**!"
                )
            )

    # Trophy 5: Open 50 crates
    if user_data.get("crates_opened", 0) >= 50:
        if award_trophy(user_id, "trophy_5"):
            bonus_xp = 250  # Example: 250 XP for earning this trophy
            user_data["xp"] += bonus_xp
            update_user_data(user_id, "xp", user_data["xp"])
            asyncio.create_task(
                channel.send(
                    f"🏆 You earned the **Crate Opener** trophy and received **{bonus_xp} bonus XP**!"
                )
            )

def check_music_folder():
    """Check if the music folder has more than 50 files and return the oldest file."""
    music_folder = "music"
    files = [
        os.path.join(music_folder, f)
        for f in os.listdir(music_folder)
        if os.path.isfile(os.path.join(music_folder, f))
    ]
    if len(files) > 37:
        oldest_file = min(
            files, key=os.path.getctime
        )  # Get the oldest file based on creation time
        return oldest_file
    return None

def can_claim_daily(user_id):
    """Check if the user can claim their daily reward."""
    data = load_user_data()
    if str(user_id) not in data:
        data[str(user_id)] = {
            "xp": 0,
            "level": 1,
            "coins": 100,
            "balance": 0,
            "warnings": [],
            "last_daily": None,
        }
        save_user_data(data)
    last_daily = data[str(user_id)].get("last_daily")
    if last_daily:
        last_claim_time = datetime.fromisoformat(last_daily)
        return datetime.now() >= last_claim_time + variables.timedelta(days=1)
    return True


def update_last_daily(user_id):
    """Update the last daily claim time for a user."""
    data = load_user_data()
    if str(user_id) not in data:
        data[str(user_id)] = {
            "xp": 0,
            "level": 1,
            "coins": 100,
            "balance": 0,
            "warnings": [],
            "last_daily": None,
        }
    data[str(user_id)]["last_daily"] = datetime.now().isoformat()
    save_user_data(data)
    
def update_eggs(user_id, eggs_change):
    """Update the user's egg count."""
    user_id = str(user_id)
    if user_id not in variables.easter_data:
        variables.easter_data[user_id] = {"eggs": 0}
    variables.easter_data[user_id]["eggs"] += eggs_change
    save_easter_data()

def random_blue_color():
    # Generate a random blue shade (RGB: R low, G medium, B high)
    return discord.Color.from_rgb(
        random.randint(0, 50),  # R: 0-50
        random.randint(100, 200),  # G: 100-200
        random.randint(180, 255),  # B: 180-255
    )
# --- Rounded rectangle helper ---
def rounded_rectangle(draw, xy, radius, fill, outline, width):
    draw.rounded_rectangle(
         xy, radius=radius, fill=fill, outline=outline, width=width
     )

# Centered text helper
def draw_centered_text(draw, rect, text, font, fill):
    x1, y1, x2, y2 = rect
    w, h = draw.textbbox((0, 0), text, font=font)[2:]
    text_x = x1 + ((x2 - x1) - w) // 2
    text_y = y1 + ((y2 - y1) - h) // 2
    draw.text((text_x, text_y), text, font=font, fill=fill)

def draw_centered_outlined_text(
    draw, rect, text, font, fill, outline, outline_width
):
    x1, y1, x2, y2 = rect
    w, h = draw.textbbox((0, 0), text, font=font)[2:]
    text_x = x1 + ((x2 - x1) - w) // 2
    text_y = y1 + ((y2 - y1) - h) // 2
    draw.text(
        (text_x, text_y),
        text,
        font=font,
        fill=fill,
        stroke_width=outline_width,
        stroke_fill=outline,
    )

# Optional: Rounded corners for the whole image
def add_rounded_corners(im, rad):
    circle = Image.new("L", (rad * 2, rad * 2), 0)
    draw_c = ImageDraw.Draw(circle)
    draw_c.ellipse((0, 0, rad * 2, rad * 2), fill=255)
    alpha = Image.new("L", im.size, 255)
    w, h = im.size
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
    alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
    alpha.paste(
        circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad)
    )
    im.putalpha(alpha)
    return im

def load_server_settings():
    if os.path.exists(variables.SERVER_SETTINGS_FILE):
        with open(variables.SERVER_SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_server_settings(data):
    with open(variables.SERVER_SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_guild_prefix(guild_id):
    settings = load_server_settings()
    return settings.get(str(guild_id), {}).get("prefix", "?")

def set_guild_prefix(guild_id, prefix):
    settings = load_server_settings()
    guild_settings = settings.get(str(guild_id), {})
    guild_settings["prefix"] = prefix
    settings[str(guild_id)] = guild_settings
    save_server_settings(settings)

def load_role_reactions():
    settings = load_server_settings()
    # Returns {message_id: {emoji: role_id, ...}, ...} or {}
    return {gid: s.get("role_reactions", {}) for gid, s in settings.items()}

def get_guild_role_reactions(guild_id):
    settings = load_server_settings()
    return settings.get(str(guild_id), {}).get("role_reactions", {})

def set_guild_role_reaction(guild_id, message_id, emoji, role_id):
    settings = load_server_settings()
    guild_settings = settings.get(str(guild_id), {})
    role_reactions = guild_settings.get("role_reactions", {})
    if str(message_id) not in role_reactions:
        role_reactions[str(message_id)] = {}
    role_reactions[str(message_id)][emoji] = role_id
    guild_settings["role_reactions"] = role_reactions
    settings[str(guild_id)] = guild_settings
    save_server_settings(settings)

def remove_guild_role_reaction(guild_id, message_id, emoji):
    settings = load_server_settings()
    guild_settings = settings.get(str(guild_id), {})
    role_reactions = guild_settings.get("role_reactions", {})
    if str(message_id) in role_reactions:
        role_reactions[str(message_id)].pop(emoji, None)
        if not role_reactions[str(message_id)]:
            role_reactions.pop(str(message_id))
    guild_settings["role_reactions"] = role_reactions
    settings[str(guild_id)] = guild_settings
    save_server_settings(settings)

def get_guild_welcome_message(guild_id):
    settings = load_server_settings()
    return settings.get(str(guild_id), {}).get("welcome_message", None)

def set_guild_welcome_message(guild_id, message):
    settings = load_server_settings()
    guild_settings = settings.get(str(guild_id), {})
    guild_settings["welcome_message"] = message
    settings[str(guild_id)] = guild_settings
    save_server_settings(settings)

def get_guild_goodbye_message(guild_id):
    settings = load_server_settings()
    return settings.get(str(guild_id), {}).get("goodbye_message", None)

def set_guild_goodbye_message(guild_id, message):
    settings = load_server_settings()
    guild_settings = settings.get(str(guild_id), {})
    guild_settings["goodbye_message"] = message
    settings[str(guild_id)] = guild_settings
    save_server_settings(settings)

def get_guild_level_roles(guild_id):
    settings = load_server_settings()
    return settings.get(str(guild_id), {}).get("level_roles", {})

def set_guild_level_role(guild_id, level: int, role_name: str):
    settings = load_server_settings()
    guild_settings = settings.get(str(guild_id), {})
    level_roles = guild_settings.get("level_roles", {})
    level_roles[str(level)] = role_name
    guild_settings["level_roles"] = level_roles
    settings[str(guild_id)] = guild_settings
    save_server_settings(settings)

def remove_guild_level_role(guild_id, level: int):
    settings = load_server_settings()
    guild_settings = settings.get(str(guild_id), {})
    level_roles = guild_settings.get("level_roles", {})
    level_roles.pop(str(level), None)
    guild_settings["level_roles"] = level_roles
    settings[str(guild_id)] = guild_settings
    save_server_settings(settings)

def get_guild_self_roles(guild_id):
    settings = load_server_settings()
    return settings.get(str(guild_id), {}).get("self_roles", [])

def add_guild_self_role(guild_id, role_name):
    settings = load_server_settings()
    guild_settings = settings.get(str(guild_id), {})
    self_roles = set(guild_settings.get("self_roles", []))
    self_roles.add(role_name)
    guild_settings["self_roles"] = list(self_roles)
    settings[str(guild_id)] = guild_settings
    save_server_settings(settings)

def remove_guild_self_role(guild_id, role_name):
    settings = load_server_settings()
    guild_settings = settings.get(str(guild_id), {})
    self_roles = set(guild_settings.get("self_roles", []))
    self_roles.discard(role_name)
    guild_settings["self_roles"] = list(self_roles)
    settings[str(guild_id)] = guild_settings
    save_server_settings(settings)

def get_guild_tags(guild_id):
    settings = load_server_settings()
    return settings.get(str(guild_id), {}).get("tags", {})

def set_guild_tag(guild_id, tag_name, tag_content):
    settings = load_server_settings()
    guild_settings = settings.get(str(guild_id), {})
    tags = guild_settings.get("tags", {})
    tags[tag_name.lower()] = tag_content
    guild_settings["tags"] = tags
    settings[str(guild_id)] = guild_settings
    save_server_settings(settings)

def remove_guild_tag(guild_id, tag_name):
    settings = load_server_settings()
    guild_settings = settings.get(str(guild_id), {})
    tags = guild_settings.get("tags", {})
    tags.pop(tag_name.lower(), None)
    guild_settings["tags"] = tags
    settings[str(guild_id)] = guild_settings
    save_server_settings(settings)

def get_guild_achievements(guild_id):
    settings = load_server_settings()
    return settings.get(str(guild_id), {}).get("achievements", {})

def set_guild_achievement(guild_id, ach_id, name, description, power, asset_url):
    settings = load_server_settings()
    guild_settings = settings.get(str(guild_id), {})
    achievements = guild_settings.get("achievements", {})
    achievements[ach_id] = {
        "name": name,
        "description": description,
        "power": power,
        "asset_url": asset_url,
    }
    guild_settings["achievements"] = achievements
    settings[str(guild_id)] = guild_settings
    save_server_settings(settings)

def remove_guild_achievement(guild_id, ach_id):
    settings = load_server_settings()
    guild_settings = settings.get(str(guild_id), {})
    achievements = guild_settings.get("achievements", {})
    achievements.pop(ach_id, None)
    guild_settings["achievements"] = achievements
    settings[str(guild_id)] = guild_settings
    save_server_settings(settings)

def get_user_achievements(user_id):
    data = load_user_data()
    return data.get(str(user_id), {}).get("achievements", [])

def add_user_achievement(user_id, ach_id):
    data = load_user_data()
    user = data.setdefault(str(user_id), {})
    achievements = user.setdefault("achievements", [])
    if ach_id not in achievements:
        achievements.append(ach_id)
        save_user_data(data)
        return True
    return False

def signal_error(error_message):
    signals_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "default-handler", "signals"))
    os.makedirs(signals_dir, exist_ok=True)
    with open(os.path.join(signals_dir, "error.txt"), "w", encoding="utf-8") as f:
        f.write(error_message)
        print(f"[signal_error] The error has been sent.")
    time.sleep(3)

def signal_update(update_message):
    signals_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "default-handler", "signals"))
    os.makedirs(signals_dir, exist_ok=True)
    file_path = os.path.join(signals_dir, "update.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(update_message)
        print(f"[signal_update] Wrote update to {file_path}.")
    time.sleep(3)

def write_last_command(channel_id, message_id):
    signals_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "default-handler", "signals"))
    os.makedirs(signals_dir, exist_ok=True)
    with open(os.path.join(signals_dir, "last_command.txt"), "w", encoding="utf-8") as f:
        f.write(f"{channel_id},{message_id}")
        print(f"[signal_update] Registered last command")
    time.sleep(3)

def is_insider_server(guild_id: int) -> bool:
    if not os.path.exists(variables.insider_FILE):
        return False
    with open(variables.insider_FILE, "r", encoding="utf-8") as f:
        try:
            servers = json.load(f)
            return guild_id in servers
        except json.JSONDecodeError:
            return False

def load_insider_servers():
    if not os.path.exists(variables.insider_FILE):
        return []
    with open(variables.insider_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_insider_servers(servers):
    with open(variables.insider_FILE, "w", encoding="utf-8") as f:
        json.dump(servers, f, indent=2)

def load_scheduled_messages():
    if not os.path.exists(variables.SCHEDULED_MSGS_FILE):
        return {}
    with open(variables.SCHEDULED_MSGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_scheduled_messages(data):
    with open(variables.SCHEDULED_MSGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def little_text(ctx=None):
    if ctx and ctx.guild and ctx.guild.id in disabled_variants:
        return ""
    tips = [
        "TIP: Use `?daily` every day to get free coins!",
        "TIP: You can trade items with friends using `?trade`.",
        "TIP: Deposit your coins in the bank to keep them safe from thieves.",
        "TIP: Use `?buylevel max` to buy as many levels as you can afford.",
        "TIP: Open crates for a chance to get rare items!",
        "TIP: You can exchange gems for coins with `?exchange_gems`.",
        "TIP: Check your inventory with `?inventory`.",
        "TIP: Use `?profile` to see your stats.",
        "TIP: Invite your friends to the server for more fun!",
        "TIP: fishh",
        "TIP: This is supposed to be a TIP but you got so lucky I won't even display anything :D",
        "TIP: fart :PIT"
    ]
    return random.choice(tips)

def little_unknowncommand_variant(ctx=None):
    if ctx and ctx.guild and ctx.guild.id in disabled_variants:
        return ""
    messages = [
        "Hmm... that command doesn't exist. Did you spell it right?",
        "Sure you spelt that command right?",
        "I don’t recognize that… are you sure it’s a thing?",
        "Ouch! That looks wrong. Want to double-check your spelling?",
        "Checked if that command exists, nope.",
        "Command not found! But hey, nobody’s perfect.",
        "Welp, that's not a command..",
        "Nope. Not the right command..",
        "Try again! maybe you spelt it wrong.?",
        "Did you just make that up? >xD"
    ]
    return random.choice(messages)

def little_error_variant(ctx=None):
    if ctx and ctx.guild and ctx.guild.id in disabled_variants:
        return ""
    messages = [
        "Hmm... seems like an error occured.",
        "That didn't work. Try again maybe?",
        "Oh well! Try again and again!",
        "Ouch! That hurt.. :(",
        "Well that failed miserably...",
        "The command broke!? But hey, nobody’s perfect.",
        "I tried my best. It wasn’t good enough.",
        "Nope. Still doesn’t work.",
        "Hmm. Not sure what to do with that.",
        "Try again and again and again.."
    ]
    return random.choice(messages)

def little_unsure_variant(ctx=None):
    if ctx and ctx.guild and ctx.guild.id in disabled_variants:
        return ""
    messages = [
        "You sure about that?",
        "That’s a bold move.",
        "Well… okay then.",
        "I wouldn't do that, but go off I guess.",
        "This could backfire. Just saying.",
        "Hmm... interesting choice.",
        "Alright... if you're really sure.",
        "Well, alrighty then.",
        "Proceeding... cautiously."
    ]
    return random.choice(messages)

def little_try_again_variant(ctx=None):
    if ctx and ctx.guild and ctx.guild.id in disabled_variants:
        return ""
    messages = [
        "Give it another shot?",
        "Try again, maybe?",
        "You got this!",
        "Want to try that one more time?",
        "Oops! Wanna try again?",
        "Could be a typo… go again!",
        "Don’t give up yet!",
        "Retry, retry, retry!",
        "That one got away. Try once more?",
        "Failure is the first step to greatness!"
    ]
    return random.choice(messages)

def save_disabled_variants():
    with open('data/disabled_variants.json', 'w') as f:
        json.dump(list(disabled_variants), f)

def load_disabled_variants():
    global disabled_variants
    try:
        with open('data/disabled_variants.json', 'r') as f:
            disabled_variants = set(json.load(f))
    except FileNotFoundError:
        disabled_variants = set()

def load_flags():
    global IS_LOCKDOWN
    if os.path.exists("data/system_flags.json"):
        try:
            with open("data/system_flags.json", "r") as f:
                flags = json.load(f)
                IS_LOCKDOWN = flags.get("IS_LOCKDOWN", False)
        except Exception:
            print("⚠️ Could not load system flags. Lockdown defaults to OFF.")

def save_flags():
    try:
        with open("data/system_flags.json", "w") as f:
            json.dump({
                "IS_LOCKDOWN": IS_LOCKDOWN
            }, f, indent=4)
    except Exception as e:
        print(f"❌ Failed to save system flags: {e}")

def get_user(user_data, user_id: str) -> dict:
    """Ensures the user ID exists in the data with all required keys."""
    if user_id not in user_data:
        user_data[user_id] = {
            "xp": 0,
            "level": 1,
            "coins": 100,
            "gems": 0,
            "balance": 0,
            "warnings": [],
            "censored_count": 0,
            "strikes": 0
        }
    else:
        # Patch missing keys in case of partial data
        defaults = {
            "xp": 0,
            "level": 1,
            "coins": 100,
            "gems": 0,
            "balance": 0,
            "warnings": [],
            "censored_count": 0,
            "strikes": 0
        }
        for key, default in defaults.items():
            user_data[user_id].setdefault(key, default)

    return user_data[user_id]

# ---------------------------------------------------------------------------------------------------
# --------------------------------------- ASYNC DEFINITONS ------------------------------------------
# ---------------------------------------------------------------------------------------------------

async def update_bot_data_periodically(bot):
    """Periodically update bot_data.txt."""
    while True:
        write_bot_data(bot)
        await asyncio.sleep(5)  # Update every 5 seconds

async def change_status(bot):
    """Rotate statuses dynamically or use a custom status."""
    global custom_status
    statuses = itertools.cycle(
        [
            discord.Game("insider testing Celestra! 🐍 "),
            discord.Activity(
                type=discord.ActivityType.watching,
                name="[ 🔍 Our support server]: https://discord.gg/QgUQnxCwEk",
            ),
            discord.Streaming(
                name="do click", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            ),
        ]
    )
    while True:
        if variables.is_sleeping:
            # If the bot is in sleep mode, stop updating the status
            await asyncio.sleep(
                10
            )  # Check every 10 seconds if the bot is still in sleep mode
            continue

        if variables.custom_status:  # If a custom status is set, use it
            await bot.change_presence(
                status=discord.Status.online, activity=variables.custom_status
            )
        else:  # Otherwise, rotate through the default statuses
            current_status = next(statuses)
            await bot.change_presence(
                status=discord.Status.online, activity=current_status
            )
        await asyncio.sleep(360)  # Change status every 360 seconds

async def chat_reviver_task(bot):
    """Send a random message every hour to revive the chat if no activity has occurred."""
    await bot.wait_until_ready()  # Ensure the bot is ready before starting the task
    while not bot.is_closed():
        try:
            for guild in bot.guilds:
                # Check if there has been activity in the last hour
                last_active = variables.last_activity.get(guild.id, None)
                if (
                    last_active
                    and (datetime.now() - last_active).total_seconds() < 18000
                ):
                    logging.info(
                        f"Skipping chat reviver for {guild.name} due to recent activity."
                    )
                    continue

                # Find a role with "chat reviver" in its name
                chat_reviver_role = discord.utils.find(
                    lambda r: "CHAT REVIVER" in r.name.lower(), guild.roles
                )

                # Find a general or chat-related channel
                target_channel = discord.utils.find(
                    lambda c: ("general" in c.name.lower() or "chat" in c.name.lower())
                    and isinstance(c, discord.TextChannel),
                    guild.channels,
                )

                if chat_reviver_role and target_channel:
                    # Choose a random message and send it
                    random_message = random.choice(variables.chat_reviver_messages)
                    await target_channel.send(
                        f"{chat_reviver_role.mention} {random_message}"
                    )
                    logging.info(
                        f"Chat reviver message sent to {target_channel.name} in {guild.name}."
                    )
                else:
                    logging.warning(
                        f"Chat reviver role or target channel not found in {guild.name}."
                    )
        except Exception as e:
            logging.error(f"Error in chat reviver task: {e}")

        # Wait for 1 hour before checking again
        await asyncio.sleep(18000)

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

async def refresh_leaderboard(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        for guild in bot.guilds:
            channel = discord.utils.get(
                guild.text_channels, name="「🏆」tbbe-leaderboard-❯"
            )
            if channel:
                # Get user data and sort by level
                data = load_user_data()
                leaderboard = []
                for user_id, user_info in data.items():
                    if user_id.isdigit():
                        member = guild.get_member(int(user_id))
                        if member:
                            leaderboard.append(
                                (member.display_name, user_info.get("level", 0))
                            )
                leaderboard.sort(key=lambda x: x[1], reverse=True)
                # Prepare leaderboard message
                desc = ""
                for i, (name, level) in enumerate(leaderboard[:10], start=1):
                    desc += f"**{i}. {name}** — Level {level}\n"
                embed = discord.Embed(
                    title="🏆 Server Level Leaderboard",
                    description=desc or "No data yet.",
                    color=discord.Color.gold(),
                )
                # Try to find the last leaderboard message sent by the bot
                async for msg in channel.history(limit=10):
                    if (
                        msg.author == bot.user
                        and msg.embeds
                        and msg.embeds[0].title == "🏆 Server Level Leaderboard"
                    ):
                        await msg.edit(embed=embed)
                        break
                else:
                    await channel.send(embed=embed)
        await asyncio.sleep(60)  # Refresh every minute



async def ensure_level_roles(guild):
    """Ensure all level roles exist in the server with the correct name and a blue color."""
    for level, role_name in variables.level_roles.items():
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            try:
                await guild.create_role(
                    name=role_name,
                    color=random_blue_color(),
                    reason="Level-based role created by the bot.",
                )
                logging.info(f"Role '{role_name}' created in guild '{guild.name}'.")
            except discord.Forbidden:
                logging.warning(
                    f"Insufficient permissions to create role '{role_name}' in guild '{guild.name}'."
                )
                owner = guild.owner
                if owner:
                    await owner.send(
                        f"❌ I couldn't create the role '{role_name}' in your server **{guild.name}**. "
                        f"Please create it manually or grant me the necessary permissions."
                    )
            except Exception as e:
                logging.error(
                    f"Error creating role '{role_name}' in guild '{guild.name}': {e}"
                )


async def assign_level_role(member, level, channel):
    """Assign a level-based role to a user and notify in the server channel."""
    guild = member.guild
    # Try per-guild custom level roles first
    level_roles = get_guild_level_roles(guild.id)
    role_name = level_roles.get(str(level))
    if not role_name:
        # Fallback to global variables.level_roles if not set
        role_name = variables.level_roles.get(level)
    if not role_name:
        return  # No role for this level

    # Ensure the role exists
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        try:
            role = await guild.create_role(
                name=role_name,
                color=random_blue_color(),
                reason="Level-based role created by the bot.",
            )
        except Exception:
            return

    # Assign the role
    if role and role not in member.roles:
        try:
            await member.add_roles(role, reason=f"Reached Level {level}")
            await channel.send(
                f"🎉 {member.mention} has been assigned the **{role_name}** role for reaching Level {level}!"
            )
        except discord.Forbidden:
            logging.warning(
                f"Insufficient permissions to assign role '{role_name}' to {member.name}."
            )
        except Exception as e:
            logging.error(f"Error assigning role '{role_name}' to {member.name}: {e}")


