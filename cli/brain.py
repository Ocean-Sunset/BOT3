# ---------------------------------------------------------------------------------------------
# ---------------------------------------- IMPORTS --------------------------------------------
# ---------------------------------------------------------------------------------------------
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import discord
from discord.ext import commands
from discord.ext.commands import CooldownMapping
from discord.ext.commands import BucketType
from discord.ext.commands import CommandOnCooldown
from discord.ext.commands import cooldown
import argparse
from discord import app_commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv()
from Ediscord import utils, variables
import asyncio
import time
from flask import Flask, request, jsonify
import threading
import secrets
import logging
import json
import shutil
import filecmp
import difflib

utils.load_flags()

import json

with open("BOT3/default/data/user_data.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

cleaned = {}
for k, v in raw.items():
    if k.isdigit():
        cleaned[k] = v

with open("BOT3/default/data/user_data.json", "w", encoding="utf-8") as f:
    json.dump(cleaned, f, indent=4)

print("✅ Cleaned user_data.json")

def get_prefix(bot, message):
    if not message.guild:
        return "?"
    # Fallback: load prefix from file if utils.get_guild_prefix is missing
    try:
        return utils.get_guild_prefix(message.guild.id)
    except AttributeError:
        # Local implementation if not present in utils
        if os.path.exists(variables.PREFIXES_FILE):
            with open(variables.PREFIXES_FILE, "r", encoding="utf-8") as f:
                prefixes = json.load(f)
            return prefixes.get(str(message.guild.id), "?")
        return "?"

bot = commands.Bot(command_prefix=get_prefix, intents=variables.intents, help_command=None)
Components = ["events", "info", "moderation", "money", "others", "ownercommands", "utility", "omega", "assets", "chatreviver", "support_server", "migration"]

# ---------------------------------------------------------------------------------------------
# ---------------------------------------- VERSION CHECK --------------------------------------
# ---------------------------------------------------------------------------------------------

VER_FILE = os.path.join(os.path.dirname(__file__), 'ver.txt')
COGS_DIR = os.path.join(os.path.dirname(__file__), 'Components')
MORE_DIR = os.path.join(os.path.dirname(__file__), 'more')

COG_LIST = [
    'assets.py', 'chatreviver.py', 'events.py', 'help.py', 'info.py', 'insider.py', 'insiderrequest.py',
    'moderation.py', 'money.py', 'music.py', 'omega.py', 'others.py', 'ownercommands.py', 'patriviaarchives.py',
    'slash.py', 'subscriptions.py', 'support_server.py', 'utility.py'
]

def read_versions():
    versions = {}
    if os.path.exists(VER_FILE):
        with open(VER_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    versions[k.strip()] = v.strip()
    return versions

def write_versions(versions):
    with open(VER_FILE, 'w', encoding='utf-8') as f:
        for k, v in versions.items():
            f.write(f'{k}={v}\n')

def ensure_more_folder():
    os.makedirs(MORE_DIR, exist_ok=True)
    for cog in COG_LIST:
        src = os.path.join(COGS_DIR, cog)
        dst = os.path.join(MORE_DIR, cog)
        if not os.path.exists(dst):
            if os.path.exists(src):
                shutil.copy2(src, dst)

def compare_and_update_versions():
    versions = read_versions()
    updated = False
    for cog in COG_LIST:
        cog_name = cog.replace('.py', '')
        src = os.path.join(COGS_DIR, cog)
        dst = os.path.join(MORE_DIR, cog)
        if not os.path.exists(src) or not os.path.exists(dst):
            continue
        if not filecmp.cmp(src, dst, shallow=False):
            print(f'Cog changed: {cog}')
            # Show diff for context
            with open(src, 'r', encoding='utf-8') as f1, open(dst, 'r', encoding='utf-8') as f2:
                diff = list(difflib.unified_diff(f2.readlines(), f1.readlines(), fromfile=dst, tofile=src))
            if diff:
                print(''.join(diff[:10]) + ('...\n' if len(diff) > 10 else ''))
            # Ask for update type
            while True:
                resp = input(f'Is this {cog_name} a BIG, MEDIUM or SMALL update? ').strip().lower()
                if resp in ('big', 'medium', 'small'):
                    break
                print('Please type BIG, MEDIUM or SMALL.')
            old_ver = versions.get(cog_name, '1.0.0')
            parts = (old_ver.split('.') + ['0', '0'])[:3]
            try:
                major, minor, patch = map(int, parts)
            except Exception:
                major, minor, patch = 1, 0, 0
            if resp == 'big':
                major += 1
                minor = 0
                patch = 0
            elif resp == 'medium':
                minor += 1
                patch = 0
            else:
                patch += 1
            new_ver = f'{major}.{minor}.{patch}'
            versions[cog_name] = new_ver
            print(f'Updated {cog_name} version: {old_ver} -> {new_ver}')
            shutil.copy2(src, dst)
            updated = True
    if updated:
        write_versions(versions)

def run_version_check():
    ensure_more_folder()
    compare_and_update_versions()

# ---------------------------------------------------------------------------------------------
# ---------------------------------------- ASYNC DEFINITION -----------------------------------
# ---------------------------------------------------------------------------------------------

# Background task to monitor inactivity
async def monitor_inactivity():
    global last_activity_time
    
    # Update last activity time for inactivity monitoring
    last_activity_time = time.time()
    
    while True:
        await asyncio.sleep(60)  # Check every minute
        time_since_last_activity = time.time() - last_activity_time
        if time_since_last_activity > 3600:  # 20 minutes = 1200 seconds
            os.execv(sys.executable, [sys.executable] + sys.argv)
            logging.info("No activity detected for 20 minutes. Restarting the bot...")
            # Restart the bot

# ---------------------------------------------------------------------------------------------
# ---------------------------------------- ON_READY -------------------------------------------
# ---------------------------------------------------------------------------------------------

@bot.event
async def on_ready():
    await bot.tree.sync()
    if bot.user is not None:
        print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    else:
        print("Logged in, but bot.user is None.")
    if not hasattr(bot, "monitor_task"):
        setattr(bot, "monitor_task", asyncio.create_task(monitor_inactivity()))
        print("Monitor activity task has been started.")

# ---------------------------------------------------------------------------------------------
# ---------------------------------------- IMPORTANT ------------------------------------------
# ---------------------------------------------------------------------------------------------

async def setup_required_roles(guild):
    """Set up any required roles that don't exist yet."""
    # Get the auto-role if configured
    auto_role_name = utils.get_auto_role(guild.id)
    if auto_role_name and not discord.utils.get(guild.roles, name=auto_role_name):
        try:
            await guild.create_role(name=auto_role_name)
            print(f"Created missing auto-role '{auto_role_name}' in {guild.name}")
        except discord.Forbidden:
            print(f"Cannot create auto-role '{auto_role_name}' in {guild.name} - missing permissions")

async def load_cogs():
    for cog in Components:
        try:
            await bot.load_extension(f"Components.{cog}")
            print(f"✅ Loaded cog: {cog}")
        except Exception as e:
            print(f"❌ Failed to load cog {cog}: {e}")

async def print_all_commands():
    await load_cogs()
    print("\n=== Registered Commands ===")
    count = 0
    for command in bot.commands:
        print(f"- {command.name}: {command.help or 'No description provided.'}")
        count += 1
    variables.total_commands = count
    print(f"\nTotal commands: {count}\n")


@bot.check
async def check_banned_server(ctx):
    if ctx.guild and ctx.guild.id in variables.banned_servers:
        await ctx.send("❌ This server is banned from using the bot.")
        return False
    return True


if not os.path.exists("music"):
    os.makedirs("music")


@bot.check
async def check_server_restrictions(ctx):
    if ctx.guild:
        if ctx.command.name in ["BServer", "UBServer"]:
            return True

        restriction_level = variables.server_restrictions.get(str(ctx.guild.id), "Free")
        if restriction_level == "Limited" and ctx.command.name in [
            "startgame",
            "givexp",
            "gainlvl",
            "choose_country",
        ]:
            await ctx.send("❌ This command is restricted in Limited mode.")
            return False
        elif restriction_level == "Very Limited" and ctx.command.name not in [
            "ban",
            "kick",
        ]:
            await ctx.send("❌ This command is restricted in Very Limited mode.")
            return False
        elif restriction_level == "Absolute Restriction" and ctx.command.name not in [
            "ban",
            "kick",
        ]:
            await ctx.send(
                "❌ This command is restricted in Absolute Restriction mode."
            )
            return False
    return True

# ---------------------------------------------------------------------------------------------
# ---------------------------------------- COMMANDS -------------------------------------------
# ---------------------------------------------------------------------------------------------

@bot.hybrid_command(name="setprefix")
@utils.admin_or_owner()
async def setprefix(ctx, prefix: str):
    """Set a custom prefix for this server."""
    utils.set_guild_prefix(ctx.guild.id, prefix)
    await ctx.send(f"✅ Prefix set to `{prefix}` for this server.")

@bot.hybrid_command()
@commands.check(utils.is_owner)
async def reload_super(ctx):
    await bot.unload_extension("cogs.supercommands")
    await bot.load_extension("cogs.supercommands")
    await ctx.send("♻️ Reloaded `supercommands.py`.")

# ---------------------------------------------------------------------------------------------
# ---------------------------------------- FLASK API -------------------------------------------
# ---------------------------------------------------------------------------------------------

app = Flask(__name__)

API_KEY_FILE = "api_key.txt"

def load_api_key():
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r") as f:
            return f.read().strip()

    # Generate one if missing
    key = secrets.token_hex(32)
    with open(API_KEY_FILE, "w") as f:
        f.write(key)

    print("🔑 API key generated and saved.")
    return key

API_KEY = load_api_key()

def authorized(req):
    return req.headers.get("Authorization") == API_KEY


@app.route("/")
def home():
    try:
        # This literally reads the file and sends it to your browser
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error loading index.html: {e}", 500

# Ensure the Flask thread starts BEFORE the bot.run()
def run_flask():
    app.run(
        host="0.0.0.0",
        port=25246,  # Change 5050 to 25246
        debug=False,
        use_reloader=False
    )

@app.route("/status", methods=["GET"])
def api_status():
    if not authorized(request):
        return jsonify({"error": "unauthorized"}), 401
    
    # We use 'bot' directly here since it's in the same global scope
    return jsonify({
        "bot_user": str(bot.user) if bot.user else "Initializing...",
        "guilds": len(bot.guilds),
        "latency_ms": round(bot.latency * 1000, 2) if bot.latency else 0,
    })


@app.route("/restart", methods=["POST"])
def api_restart():
    if not authorized(request):
        return jsonify({"error": "unauthorized"}), 401

    return jsonify({"status": "Restarting bot…"}), 200, {
        "X-Restart": "true"
    }

if __name__ == "__main__":
    print("🚀 Starting the bot and Web Portal...")

    # Run Flask on port 5050. 0.0.0.0 makes it accessible via your IP.
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=25246, debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()
    print("🌐 Web Dashboard live at http://172.18.0.35:25246")

    try:
        # Run the bot's startup
        run_version_check()
        asyncio.run(load_cogs())
        bot.run(variables.token)
    except Exception as e:
        print(f"❌ Error starting the bot: {e}")
