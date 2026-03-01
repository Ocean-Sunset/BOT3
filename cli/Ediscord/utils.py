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
import typing
from Ediscord import variables
import asyncio
import time
import sys
import random
import itertools
from PIL import Image, ImageDraw, ImageFont
import psutil
import shutil
import glob
import difflib


SIGNALS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "handler", "signals"))
ERROR_FILE = os.path.join(SIGNALS_DIR, "error.txt")
LAST_COMMAND_FILE = os.path.join(SIGNALS_DIR, "last_command.txt")

# ---------------------------------------------------------------------------------------------------
# -------------------------------------------- DEFINITONS -------------------------------------------
# ---------------------------------------------------------------------------------------------------

def atomic_write_json(path, data):
    """Write data to a JSON file atomically to prevent corruption."""
    try:
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        
        # Create a temp file
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(f.fileno()) # Ensure data is written to disk
        
        # Rename tmp file to actual file (atomic operation)
        os.replace(tmp_path, path)
        return True
    except Exception as e:
        logging.error(f"❌ Failed to atomically write to {path}: {e}")
        return False

def load_logging_config():
    """Load logging configuration from the JSON file."""
    try:
        with open(variables.LOGGING_CONFIG_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_logging_config(data):
    """Save logging configuration to the JSON file."""
    atomic_write_json(variables.LOGGING_CONFIG_FILE, data)

def is_owner(ctx):
    """Check if the command issuer is the bot owner."""
    return ctx.author.id == variables.OWNER_ID

async def is_owner_async(ctx):
    """Async version for use in command checks."""
    return ctx.author.id == variables.OWNER_ID

def admin_or_owner():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator or await is_owner_async(ctx)
    return commands.check(predicate)

# ============================================================================================
# CIPHER: Trophy/Achievement system removed - Not part of security bot
# ============================================================================================

# def save_trophy_data():
#     """Save trophy data to the JSON file."""
#     atomic_write_json(variables.TROPHY_FILE, variables.trophy_data)

# def award_trophy(user_id, trophy_id):
#     """Award a trophy to a user."""
#     user_id = str(user_id)
#     if user_id not in variables.trophy_data:
#         variables.trophy_data[user_id] = []
#     if trophy_id not in variables.trophy_data[user_id]:
#         variables.trophy_data[user_id].append(trophy_id)
#         save_trophy_data()
#         return True  # Trophy awarded
#     return False  # Trophy already owned

# def load_inventory():
#     """Load the inventory data from the JSON file."""
#     if os.path.exists(variables.INVENTORY_FILE):
#         with open(variables.INVENTORY_FILE, "r") as f:
#             return json.load(f)
#     return {}

# def save_inventory(inventory):
#     """Save the inventory data to the JSON file."""
#     atomic_write_json(variables.INVENTORY_FILE, inventory)

# def save_easter_data():
#     """Save the easter data to the JSON file."""
#     atomic_write_json(variables.EASTER_FILE, variables.easter_data)

# Stub functions to prevent imports errors
def save_trophy_data():
    raise NotImplementedError("CIPHER: Trophy system removed")

def award_trophy(user_id, trophy_id):
    raise NotImplementedError("CIPHER: Trophy system removed")

def load_inventory():
    raise NotImplementedError("CIPHER: Inventory system removed")

def save_inventory(inventory):
    raise NotImplementedError("CIPHER: Inventory system removed")

def save_easter_data():
    raise NotImplementedError("CIPHER: Easter event system removed")

# ============================================================================================
# CIPHER: Economy system removed - Bank, Coins, and Gems are not part of security bot
# ============================================================================================

# def save_bank_data():
#     """Save the bank data to the JSON file."""
#     atomic_write_json(variables.BANK_FILE, variables.bank_data)

# def get_bank_balance(user_id):
#     """Get the bank balance of a user."""
#     user_id = str(user_id)
#     return variables.bank_data.get(user_id, 0)

# def update_bank_balance(user_id, amount):
#     """Update the bank balance of a user."""
#     user_id = str(user_id)
#     if user_id not in variables.bank_data:
#         variables.bank_data[user_id] = 0
#     variables.bank_data[user_id] += amount
#     save_bank_data()

# def update_gems(user_id, gems_change):
#     """Update the user's gem count."""
#     data = load_user_data()
#     if str(user_id) not in data:
#         data[str(user_id)] = {"xp": 0, "level": 1, "coins": 100, "gems": 0, "warnings": []}
#     data[str(user_id)]["gems"] = data[str(user_id)].get("gems", 0) + gems_change
#     save_user_data(data)

# def get_coins(user_id):
#     """Get the balance of a user."""
#     data = load_user_data()
#     if str(user_id) not in data:
#         data[str(user_id)] = {"xp": 0, "level": 1, "coins": 100, "warnings": []}
#         save_user_data(data)
#     return data[str(user_id)].get("coins", 0)

# def update_coins(user_id, amount):
#     """Update the balance of a user."""
#     data = load_user_data()
#     if str(user_id) not in data:
#         data[str(user_id)] = {"xp": 0, "level": 1, "coins": 100, "warnings": []}
#     data[str(user_id)]["coins"] = data[str(user_id)].get("coins", 0) + amount
#     save_user_data(data)

# Stub functions to prevent import errors
def save_bank_data():
    raise NotImplementedError("CIPHER: Economy system removed - bank functionality disabled")

def get_bank_balance(user_id):
    raise NotImplementedError("CIPHER: Economy system removed - bank functionality disabled")

def update_bank_balance(user_id, amount):
    raise NotImplementedError("CIPHER: Economy system removed - bank functionality disabled")

def update_gems(user_id, gems_change):
    raise NotImplementedError("CIPHER: Economy system removed - gems functionality disabled")

def get_coins(user_id):
    raise NotImplementedError("CIPHER: Economy system removed - coins functionality disabled")

def update_coins(user_id, amount):
    raise NotImplementedError("CIPHER: Economy system removed - coins functionality disabled")

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
        # Final write to main file
        atomic_write_json(variables.USER_DATA_PATH, cleaned_data)

    except Exception as e:
        logging.error(f"❌ Error saving user data: {e}")

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


def normalize_user_data(auto_fix=True):
    """Analyze and optionally fix anomalies in user_data.json.

    Returns a report dict with counts and anomaly messages.
    """
    report = {"checked": 0, "fixed": 0, "anomalies": []}
    data = load_user_data()
    cleaned = {}

    for k, v in list(data.items()):
        report["checked"] += 1
        if not str(k).isdigit():
            report["anomalies"].append(f"root_key_not_digit: {k}")
            # skip non-user keys
            continue

        if not isinstance(v, dict):
            report["anomalies"].append(f"user_not_object: {k}")
            if auto_fix:
                cleaned[k] = {
                    "xp": 0,
                    "level": 1,
                    "coins": 100,
                    "gems": 0,
                    "balance": 0,
                    "warnings": [],
                    "censored_count": 0,
                    "strikes": 0,
                    "messages": [],
                }
                report["fixed"] += 1
            continue

        user = v.copy()

        # Ensure lists/keys exist
        user.setdefault("warnings", [])
        user.setdefault("messages", [])
        user.setdefault("xp", 0)
        user.setdefault("level", 1)
        user.setdefault("coins", 100)
        user.setdefault("gems", 0)
        user.setdefault("balance", 0)
        user.setdefault("censored_count", 0)
        user.setdefault("strikes", 0)

        # Coerce numeric-like fields to ints
        for num_key in ("xp", "level", "coins", "gems", "balance", "censored_count", "strikes"):
            val = user.get(num_key)
            if isinstance(val, (int, float)):
                user[num_key] = int(val)
            else:
                # try to coerce from string
                try:
                    user[num_key] = int(float(str(val)))
                    report["fixed"] += 1
                except Exception:
                    report["anomalies"].append(f"bad_numeric_{num_key}: user={k} value={val}")
                    user[num_key] = 0 if num_key != "level" else 1

        # Ensure messages is a list of timestamps (leave as-is otherwise)
        if not isinstance(user.get("messages"), list):
            report["anomalies"].append(f"messages_not_list: user={k}")
            user["messages"] = []
            report["fixed"] += 1

        cleaned[k] = user

    # Backup and save only when auto_fix is True. In dry-run mode we only analyze.
    if auto_fix:
        try:
            os.makedirs(os.path.dirname(variables.USER_DATA_PATH), exist_ok=True)
            backup_path = variables.USER_DATA_PATH + ".bak"
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            report["backup"] = backup_path
        except Exception as e:
            report["anomalies"].append(f"backup_failed: {e}")

        try:
            save_user_data(cleaned)
        except Exception as e:
            report["anomalies"].append(f"save_failed: {e}")
    else:
        report["note"] = "dry-run: no files modified"

    return report


def normalize_generic_json_files(auto_fix=True, folder="."):
    """Generic normalizer for basic JSON files (conservative: only scalar coercions)."""
    report = {"checked": 0, "fixed": 0, "anomalies": [], "files": {}}

    candidates = [
        os.path.join(folder, "data", "bank.json"),
    ]
    candidates = [p for p in dict.fromkeys(candidates) if os.path.exists(p)]

    def _coerce_value(v):
        if isinstance(v, int):
            return v, False
        if isinstance(v, float):
            return int(v), True
        if isinstance(v, str):
            try:
                return int(v), True
            except Exception:
                try:
                    return int(float(v)), True
                except Exception:
                    return v, False
        return v, False

    for path in candidates:
        file_report = {"checked": 0, "fixed": 0, "anomalies": []}
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            report["anomalies"].append(f"failed_read:{path}:{e}")
            continue

        report["checked"] += 1
        file_report["checked"] = 1
        modified = False

        if isinstance(raw, dict):
            for k, v in list(raw.items()):
                if isinstance(v, (str, int, float)):
                    new_v, changed = _coerce_value(v)
                    if changed:
                        raw[k] = new_v
                        modified = True
                        file_report["fixed"] += 1
                elif isinstance(v, list):
                    new_list = []
                    changed_any = False
                    for item in v:
                        new_item, changed = _coerce_value(item)
                        new_list.append(new_item)
                        if changed:
                            changed_any = True
                    if changed_any:
                        raw[k] = new_list
                        modified = True
                        file_report["fixed"] += 1
        elif isinstance(raw, list):
            new_list = []
            changed_any = False
            for item in raw:
                if isinstance(item, (str, int, float)):
                    new_item, changed = _coerce_value(item)
                    new_list.append(new_item)
                    if changed:
                        changed_any = True
                else:
                    new_list.append(item)
            if changed_any:
                raw = new_list
                modified = True
                file_report["fixed"] += 1
        else:
            file_report["anomalies"].append(f"top_level_not_object_or_list:{type(raw).__name__}")

        if modified:
            report["fixed"] += file_report["fixed"]
            if auto_fix:
                try:
                    bak = path + ".bak"
                    shutil.copy2(path, bak)
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(raw, f, indent=2)
                    file_report["backup"] = bak
                except Exception as e:
                    file_report["anomalies"].append(f"save_failed:{e}")
            else:
                file_report["note"] = "dry-run: no file written"

        report["files"][path] = file_report

    return report


def fix_json_files(target="all", auto_fix=True):
    combined = {"reports": {}, "timestamp": datetime.now().isoformat()}
    if target in ("all", "user_data"):
        combined["reports"]["user_data"] = normalize_user_data(auto_fix=auto_fix)
    if target in ("all", "generic"):
        combined["reports"]["generic"] = normalize_generic_json_files(auto_fix=auto_fix)
    return combined
# --- Per-Server User Data Functions ---

def get_guild_user_data_path(guild_id):
    """Get the path to the user data file for a specific guild."""
    return os.path.join("data", "guilds", str(guild_id), "user_data.json")

def load_guild_user_data(guild_id):
    """Load user data for a specific guild."""
    path = get_guild_user_data_path(guild_id)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        print(f"❌ Error loading guild data for {guild_id}: {e}")
        return {}

def save_guild_user_data(guild_id, data):
    """Save user data for a specific guild."""
    path = get_guild_user_data_path(guild_id)
    atomic_write_json(path, data)

def get_guild_user_data(guild_id, user_id):
    """Get data for a specific user in a specific guild."""
    data = load_guild_user_data(guild_id)
    user_id_str = str(user_id)
    
    if user_id_str not in data or not isinstance(data[user_id_str], dict):
        # Initialize default values
        data[user_id_str] = {
            "xp": 0, 
            "level": 1, 
            "coins": 0, # Coins might be global? notes checks per server leveling. Coins usually global but let's separate for now if requested.
            # actually user said "Make the level system PER SERVER."
            # He also said "fix sell command", implying inventory/money might be global?
            # For now, let's keep money global? Use `update_coins` for global money.
            # But the structure requested was: "{ctx.guild.id} ... load json or save json" for "Level system".
            # So I will separate XP/Level here.
            "warnings": [],
            "censored_count": 0,
            "strikes": 0
        }
        save_guild_user_data(guild_id, data)
    else:
        # Ensure defaults
        user_data = data[user_id_str]
        user_data.setdefault("xp", 0)
        user_data.setdefault("level", 1)
        user_data.setdefault("warnings", [])
        user_data.setdefault("censored_count", 0)
        user_data.setdefault("strikes", 0)
        data[user_id_str] = user_data

    return data[user_id_str]

def update_guild_user_data(guild_id, user_id, key, value):
    """Update a single key for a specific user in a guild."""
    data = load_guild_user_data(guild_id)
    user_id_str = str(user_id)
    
    if user_id_str not in data:
         data[user_id_str] = {
            "xp": 0, 
            "level": 1, 
            "warnings": [],
            "censored_count": 0,
            "strikes": 0
        }
    
    data[user_id_str][key] = value
    save_guild_user_data(guild_id, data)

def backup_file(json_path, max_backups=10):
    """Create a dated backup of the given JSON file, organized by folder, and purge oldest if needed."""
    if not os.path.exists(json_path):
        print(f"⚠️ Tried to back up missing file: {json_path}")
        return

    filename = os.path.basename(json_path)
    base_name = os.path.splitext(filename)[0]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

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
    bot_version = f"{getattr(bot, 'version', 'unknown')} (2025.09.19.19.00.12)"  # Only works if you set this attribute yourself
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
    # Also write the main bot's user id into the handler signals folder so the handler
    # can perform a direct membership check without parsing bot_data.txt.
    try:
        os.makedirs(SIGNALS_DIR, exist_ok=True)
        main_id_path = os.path.join(SIGNALS_DIR, "main_bot_id.txt")
        with open(main_id_path, "w", encoding="utf-8") as f:
            f.write(str(bot.user.id))
    except Exception:
        # non-fatal; handler will fall back to bot_data.txt parsing
        pass

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
    atomic_write_json(variables.bot_info_file, variables.bot_info)

def signal_error(error_message, is_critical=True):
    os.makedirs(SIGNALS_DIR, exist_ok=True) # Ensure the directory exists

    # Prefix the error message based on criticality
    error_file_content = f"CRITICAL:{error_message}" if is_critical else f"NON_CRITICAL:{error_message}"
    with open(ERROR_FILE, "w", encoding="utf-8") as f:
        f.write(error_file_content)
    print(f"[signal_error] The error has been sent. Critical: {is_critical}")
    time.sleep(3) # Keep the delay for file system sync


def write_last_command(channel_id, message_id):
    os.makedirs(SIGNALS_DIR, exist_ok=True) # Ensure the directory exists
    with open(LAST_COMMAND_FILE, "w", encoding="utf-8") as f:
        f.write(f"{channel_id},{message_id}")
    print(f"[write_last_command] Last command info written: {channel_id},{message_id}")


def signal_update(update_message):
    signals_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "handler", "signals"))
    os.makedirs(signals_dir, exist_ok=True)
    file_path = os.path.join(signals_dir, "update.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(update_message)
        print(f"[signal_update] Wrote update to {file_path}.")
    time.sleep(3)

def little_text(ctx=None):
    if ctx and ctx.guild and ctx.guild.id in variables.disabled_variants:
        return ""
    tips = [
        "TIP: Use `/daily` every day to get free coins!",
        "TIP: You can trade items with friends using `/trade`.",
        "TIP: Deposit your coins in the bank to keep them safe from thieves.",
        "TIP: Use `/buylevel max` to buy as many levels as you can afford.",
        "TIP: Open crates for a chance to get rare items!",
        "TIP: You can exchange gems for coins with `/exchange gems`.",
        "TIP: Check your inventory with `/inventory`.",
        "TIP: Use `/profile` to see your stats.",
        "TIP: Invite your friends to the server for more fun!",
        "TIP: fishh",
        "TIP: This is supposed to be a TIP but you got so lucky I won't even display anything :D",
        "TIP: fart :PIT"
    ]
    return random.choice(tips)

def little_unknowncommand_variant(ctx=None):
    if ctx and ctx.guild and ctx.guild.id in variables.disabled_variants:
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
    if ctx and ctx.guild and ctx.guild.id in variables.disabled_variants:
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
    if ctx and ctx.guild and ctx.guild.id in variables.disabled_variants:
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

def welcome_message_random(ctx=None):
    if ctx and ctx.guild and ctx.guild.id in variables.disabled_variants:
        return ""
    messages = [
        "We hope you enjoy your stay!",
        "Get comfy here!",
        "Welcome to our server!",
        "Glad you could join us!",
        "Hello and welcome!",
        "Welcome aboard!",
        "Make yourself comfy here!",
        "Should be pretty nice here!"
    ]
    return random.choice(messages)

def goodbye_message_random(ctx=None):
    if ctx and ctx.guild and ctx.guild.id in variables.disabled_variants:
        return ""
    messages = [
        "Oh man, they left..",
        "Welp, goodbye.",
        "We hope you ENJOYED your stay..",
        "See you later, alligator!",
        "Goodbye! Come back soon!",
        "Farewell, friend!",
        "Take care! We'll miss you!",
        "Safe travels!",
        "May the road rise up to meet you.",
        "It's sad seeing you go..."
    ]
    return random.choice(messages)

def little_try_again_variant(ctx=None):
    if ctx and ctx.guild and ctx.guild.id in variables.disabled_variants:
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

def load_swearwords():
    if not os.path.exists(variables.SWEAR_JSON_PATH):
        # Example structure: { "1": ["word1", "word2"], "2": [...], ... }
        with open(variables.SWEAR_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump({str(i): [] for i in range(1, 6)}, f, indent=2)
    with open(variables.SWEAR_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def is_offensive(message: str, level: int) -> bool:
    """
    Returns True if the message contains a swear word at the given level.
    Uses difflib for fuzzy matching.
    """
    swearwords = load_swearwords()
    words_to_check = swearwords.get(str(level), [])
    for word in words_to_check:
        for msg_word in message.lower().split():
            similarity = difflib.SequenceMatcher(None, word.lower(), msg_word).ratio()
            if similarity > 0.85:  # Threshold for fuzzy match
                return True
    return False

def get_offensive_words(message: str, level: int):
    """
    Returns a list of detected offensive words in the message for the given level.
    """
    detected = []
    swearwords = load_swearwords()
    words_to_check = swearwords.get(str(level), [])
    for word in words_to_check:
        for msg_word in message.lower().split():
            similarity = difflib.SequenceMatcher(None, word.lower(), msg_word).ratio()
            if similarity > 0.85:
                detected.append(msg_word)
    return detected

# ---------------------------------------------------------------------------------------------------
# --------------------------------------- ASYNC DEFINITONS ------------------------------------------
# ---------------------------------------------------------------------------------------------------

async def change_status(bot):
    """Rotate statuses dynamically or use a custom status."""
    global custom_status
    statuses = itertools.cycle(
        [
            discord.Game("Just being myself 🐍!"),
            discord.Activity(
                type=discord.ActivityType.watching,
                name="Watching our commands! || Type /help to know more!",
            ),
            discord.Game(
                "Powered by HidenCloud ☁️"
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
