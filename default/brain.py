# --------------------- IMPORTS ---------------------
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
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv()
from Ediscord import utils, variables
import asyncio
import time
import logging
import json

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
Components = ["events", "fun", "info", "moderation", "money", "others", "ownercommands", "utility", "super", "omega", "beta", "betarequest"]
# --------------------- ASYNC DEFINITON (important) ---------------------
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

# --------------------- ON_READY ---------------------

@bot.event
async def on_ready():
    if bot.user is not None:
        print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    else:
        print("Logged in, but bot.user is None.")
    if not hasattr(bot, "monitor_task"):
        setattr(bot, "monitor_task", asyncio.create_task(monitor_inactivity()))
        print("Monitor activity task has been started.")

# --------------------- IMPORTANT ---------------------


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

@bot.command(name="setprefix")
@commands.has_permissions(administrator=True)
async def setprefix(ctx, prefix: str):
    """Set a custom prefix for this server."""
    utils.set_guild_prefix(ctx.guild.id, prefix)
    await ctx.send(f"✅ Prefix set to `{prefix}` for this server.")

if __name__ == "__main__":
    print("🚀 Starting the bot...")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-input", action="store_true", help="Skip input prompts for auto-restart"
    )
    args = parser.parse_args()
    try:
        asyncio.run(print_all_commands())
        bot.run(variables.token)
    except Exception as e:
        print(f"❌ Error starting the bot: {e}")