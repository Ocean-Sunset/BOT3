import discord
from discord.ext import commands
from discord.ext.commands import CooldownMapping
from discord.ext.commands import BucketType
from discord.ext.commands import CommandOnCooldown
from discord.ext.commands import cooldown
import argparse
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv()
from Ediscord import utils, variables
import asyncio


bot = commands.Bot(command_prefix="?", intents=variables.intents, help_command=None)
cogs = ["events", "fun", "info", "moderation", "money", "others", "ownercommands"]

async def load_cogs():
    for cog in cogs:
        try:
            await bot.load_extension(f"cogs.{cog}")
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