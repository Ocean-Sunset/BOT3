import discord
from discord.ext import tasks, commands
import os
from dotenv import load_dotenv
load_dotenv()
from EdiscordH import variables, utils 
import sys
import difflib
import asyncio
import logging
import argparse
import random
TOKEN = os.getenv("TOKEN")
ERROR_CHANNEL_ID = 1389940334578106470
UPDATE_CHANNEL_ID = 1389940334578106470
ANNOUNCEMENT_CHANNEL_IDS = [
    1368353297253138435, # thatguy's server
    1366939146949496893, # hangout test
    1362911721328742491, # hangout
    1389709510561628300, # kepershi's server
    1367500237668749372, # ducky's servr
    1365292101205758085, # death corp
    1325857545880993903 # void room
]
SIGNALS_DIR = os.path.join(os.path.dirname(__file__), "signals")
ERROR_FILE = os.path.join(SIGNALS_DIR, "error.txt")
UPDATE_FILE = os.path.join(SIGNALS_DIR, "update.txt")
LAST_COMMAND_FILE = os.path.join(SIGNALS_DIR, "last_command.txt")
lil_text = [
     "fishh :D",
     "did you know? i know :)",
     "nantedo 2 is costy",
     "here my token: MTM...",
     "i hardcoded this text to be random :D",
     "null",
     "boblox sucks :(",
     "ur addictied to discorde",
     "lalalalalalalala",
     "did u know? this is an announcement",
     "THIS IS AN ALERT, MY KFC IS CLOSING TONIGHT :((((("
]


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"Handler bot logged in as {bot.user}")
    check_signals.start()
    keep_terminal_alive.start()

@bot.command(name="update")
@commands.check(utils.is_owner)
async def update(ctx, *, args: str):
        """Update the bot's version and new features, then restart."""
        global current_status
        try:
            version, new_stuff = args.split(" / ")
        except ValueError:
            await ctx.send(
                "❌ Invalid format. Use `!update <version> / <new features>`."
            )
            return

        # Update the bot info
        variables.bot_info["version"] = version
        variables.bot_info["new_stuff"] = new_stuff
        utils.save_bot_info()

        # Set the status to "Updating..."
        current_status = discord.Game("Updating...")
        await bot.change_presence(
            status=discord.Status.dnd, activity=current_status
        )

        await ctx.send(
            f"✅ Handler updated to version **{version}** with new features: **{new_stuff}**."
        )
        await ctx.send("🔄 Restarting the bot...")

        utils.signal_update(f"**HANDLER** New version: {version}\n**HANDLER** New stuff: {new_stuff}")

        # Restart the bot
        os.execv(sys.executable, [sys.executable] + sys.argv)

@bot.command(name="info")
async def info(ctx):
        custominfo = f"""# I am EobotCat's Handler system!
        - Status: Normal
        - Build: Elysia's crash handler
        - Version: **{variables.bot_info['version']}**
        - Developper: th3_t1sm
    
        I am simple handler system capable of detecing crashes and others,
        I am fully automatic and i'm made with love
        """
        await ctx.send(custominfo)

@bot.command(name="changelog")
async def changelog(ctx):
        changelog = f"Here is the changelog for the {variables.bot_info['version']} version: {variables.bot_info['new_stuff']}"
        await ctx.send(changelog)

@bot.command(name="restart")
@commands.check(utils.is_owner)
async def restart(ctx):
        await ctx.send("🔄 Restarting the handler...")
        await bot.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    
@bot.command(name="shutdown")
@commands.check(utils.is_owner)
async def shutdown(ctx):
        await ctx.send("🔌 Coming in 1.2..")


@bot.command(name="start")
@commands.check(utils.is_owner)
async def start(ctx):
        await ctx.send("✅ Coming in 1.2..")

@bot.command(name="announcement")
@commands.check(utils.is_owner)
async def announcement(ctx, *, message: str = None):
    """
    Send an announcement to all known announcement channels by ID.
    """
    if not message:
        await ctx.send("❌ You must provide a message to send.")
        return

    random_text = random.choice(lil_text)  # Or little_text() if you're using a function

    for channel_id in ANNOUNCEMENT_CHANNEL_IDS:
        try:
            channel = bot.get_channel(channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                await channel.send(f"# 📢 Announcement:\n{message}\n-# {random_text}")
                logging.info(f"✅ Announcement sent to {channel.name} in {channel.guild.name}")
            else:
                logging.warning(f"⚠️ Channel ID {channel_id} is invalid or not found.")
        except Exception as e:
            logging.error(f"❌ Error sending to channel {channel_id}: {e}")

@bot.command(name="kys")
@commands.check(utils.is_owner)
async def kys(ctx):
        """commit die the bot."""
        await ctx.send("Commiting die...")
        await bot.close()

@bot.event
async def on_command_error(ctx, error):
        # Ignore messages starting with "??" or more
        if ctx.message.content.startswith("!") and ctx.message.content.count("!") > 1:
            return

        if isinstance(error, commands.CommandNotFound):
            # Get the command name the user tried to use
            attempted_command = ctx.message.content.split()[0][
                1:
            ]  # Remove the prefix (e.g., "?")

            # Dynamically get all command names and aliases
            all_commands = set()
            for cmd in bot.commands:
                all_commands.add(cmd.name)
                all_commands.update(cmd.aliases)
            # Remove hidden commands
            all_commands = {
                name
                for name in all_commands
                if not bot.get_command(name) or not bot.get_command(name).hidden
            }

            # Find the closest match to the attempted command
            closest_match = difflib.get_close_matches(
                attempted_command, all_commands, n=1, cutoff=0.6
        )

            if closest_match:
                await ctx.send(f"❌ Did you mean: `{closest_match[0]}`?")
            else:
                await ctx.send(
                    "❌ Command not found."
                )
        else:
            await ctx.send(f"An error occurred: {error}")
            # Signal the handler bot about the error
            try:
                utils.signal_error(f"{type(error).__name__}: {error}\nCommand: {ctx.command}\nUser: {ctx.author}\nMessage: {ctx.message.content}")
            except Exception as e:
                print(f"Failed to signal error: {e}")

@tasks.loop(seconds=1)
async def check_signals():
    if os.path.exists(ERROR_FILE):
        await asyncio.sleep(1) # Give a moment for files to be fully written

        with open(ERROR_FILE, "r", encoding="utf-8") as f:
            full_error_details = f.read().strip()
        
        is_critical = full_error_details.startswith("CRITICAL:")
        error_details = full_error_details.replace("CRITICAL:", "").replace("NON_CRITICAL:", "")

        channel = bot.get_channel(ERROR_CHANNEL_ID)
        if is_critical:
            # This block now only executes for critical errors
            if os.path.exists(LAST_COMMAND_FILE):
                with open(LAST_COMMAND_FILE, "r", encoding="utf-8") as f:
                    line = f.read().strip()
                if "," in line:
                    channel_id, message_id = map(int, line.split(","))
                    source_channel = bot.get_channel(channel_id)
                    if source_channel:
                        try:
                            msg = await source_channel.fetch_message(message_id)
                            await msg.reply(
                                "# ⚠️ The main bot has encountered a **critical error** and now maybe disabled.\nPlease try again later or contact support.\n-# If you do end up contacting support, please make sure to explain precisely what happened."
                            )
                        except discord.HTTPException as e:
                            print(f"Failed to reply to message in channel {channel_id}: {e}")
                            if source_channel: # Try to send general message if reply failed
                                await source_channel.send(
                                    "-# B.error, reply failed\n# ⚠️ The main bot has encountered a **critical error** and now maybe disabled.\nPlease try again later or contact support.\n-# If you do end up contacting support, please make sure to explain precisely what happened."
                                )
                os.remove(LAST_COMMAND_FILE) # Remove last command file after processing critical error
            
            if channel:
                await channel.send(f"# A CRITICAL ERROR OCCURRED \nDetails:\n```{error_details}```")
        else:
            # Optional: send non-critical errors to the error channel too, but without the "bot disabled" message
            if channel:
                await channel.send(f"# A NON-CRITICAL ERROR OCCURRED \nDetails:\n```{error_details}```")
        
        os.remove(ERROR_FILE) # Always remove the error file after processing

    # ... (rest of your check_signals for UPDATE_FILE remains the same)
    if os.path.exists(UPDATE_FILE):
        # ... your existing update handling logic ...
        with open(UPDATE_FILE, "r", encoding="utf-8") as f:
            update_details = f.read()
        # Check if this is a insider-only update
        if update_details.startswith("insider|"):
            update_details = update_details[len("insider|"):]
            # Dynamically get insider server IDs
            insider_server_ids = utils.load_insider_servers()
            for guild in bot.guilds:
                if guild.id in insider_server_ids:
                    announcement_channel = None
                    # Attempt to find a suitable announcement channel within the guild
                    for chan_id in ANNOUNCEMENT_CHANNEL_IDS:
                        chan = guild.get_channel(chan_id)
                        if chan and isinstance(chan, discord.TextChannel):
                            announcement_channel = chan
                            break
                    
                    if not announcement_channel and guild.text_channels:
                        announcement_channel = guild.text_channels[0]
                    if announcement_channel:
                        try:
                            await announcement_channel.send(f"# 📢 **insider Update Announcement:**\n{update_details}")
                        except Exception as e:
                            print(f"Failed to send insider update to channel {announcement_channel.id}: {e}")
        else:
            # Main update, send to all announcement channels
            channel = bot.get_channel(UPDATE_CHANNEL_ID)
            if channel:
                await channel.send(f"# 📢 **BOT Update Announcement:**\n{update_details}")
            for channel_id in ANNOUNCEMENT_CHANNEL_IDS:
                channel = bot.get_channel(channel_id)
                if channel:
                    try:
                        await channel.send(f"# 📢 **BOT Update Announcement:**\n{update_details}")
                    except Exception as e:
                        print(f"Failed to send update to channel {channel_id}: {e}")
        os.remove(UPDATE_FILE)


@tasks.loop(minutes=1)
async def keep_terminal_alive():
    try:
        print("Heartbeat: handler still running...")
    except Exception as e:
        print(f"[Heartbeat Error] {e}")


if __name__ == "__main__":
    print("🚀 Starting the bot...")
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-input", action="store_true", help="Skip input prompts for auto-restart"
    )
    args = parser.parse_args()
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Failed to start handler bot: {e}")
        if not args.skip_input:
            input("Press Enter to exit...")