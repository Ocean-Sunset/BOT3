import discord
from discord.ext import tasks, commands
import os
from dotenv import load_dotenv
load_dotenv()
from EdiscordH import variables, utils 
import sys
import asyncio
TOKEN = os.getenv("TOKEN")
ERROR_CHANNEL_ID = 1389940334578106470
UPDATE_CHANNEL_ID = 1389940334578106470

SIGNALS_DIR = os.path.join(os.path.dirname(__file__), "signals")
ERROR_FILE = os.path.join(SIGNALS_DIR, "error.txt")
UPDATE_FILE = os.path.join(SIGNALS_DIR, "update.txt")
LAST_COMMAND_FILE = os.path.join(SIGNALS_DIR, "last_command.txt")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

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
            f"✅ Bot updated to version **{version}** with new features: **{new_stuff}**."
        )
        await ctx.send("🔄 Restarting the bot...")

        utils.signal_update(f"New version: {version}\nNew stuff: {new_stuff}")

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
        await ctx.send("🔄 Restarting the bot...")
        await bot.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    
@bot.command(name="shutdown")
@commands.check(utils.is_owner)
async def shutdown(ctx):
        await ctx.send("🔌 Coming in 1.1..")


@bot.command(name="start")
@commands.check(utils.is_owner)
async def start(ctx):
        await ctx.send("✅ Coming in 1.1..")

@tasks.loop(seconds=1)
async def check_signals():
    # Handle error signal
    if os.path.exists(ERROR_FILE):
        await asyncio.sleep(1)
        with open(ERROR_FILE, "r", encoding="utf-8") as f:
            error_details = f.read()
        if os.path.exists(LAST_COMMAND_FILE):
            with open(LAST_COMMAND_FILE, "r", encoding="utf-8") as f:
                line = f.read().strip()
                if "," in line:
                    channel_id, message_id = map(int, line.split(","))
                    channel = bot.get_channel(channel_id)
                    if channel:
                        try:
                            msg = await channel.fetch_message(message_id)
                            await msg.reply(f"# ⚠️ The main bot has crashed.\nPlease try again later or contact support.\n-# If you do end up contacting support, please make sure to explain precisly what happened.")
                        except Exception:
                            # Fallback: just send to the channel
                            await channel.send(f"# ⚠️ The main bot has crashed.\nPlease try again later or contact support.\n-# If you do end up contacting support, please make sure to explain precisly what happened.\n-# (B.error, reply failed)")
        channel = bot.get_channel(ERROR_CHANNEL_ID)
        if channel:
            await channel.send(
                f"# A CRITICAL ERROR OCCURED \nDetails:\n```{error_details}```"
            )
        else:
            # Retry logic if last_command.txt not ready yet
            await asyncio.sleep(2)
            if os.path.exists(LAST_COMMAND_FILE):
                with open(LAST_COMMAND_FILE, "r", encoding="utf-8") as f:
                    line = f.read().strip()
                    if "," in line:
                        channel_id, message_id = map(int, line.split(","))
                        channel = bot.get_channel(channel_id)
                        if channel:
                            try:
                                msg = await channel.fetch_message(message_id)
                                await msg.reply("# ⚠️ The main bot has crashed.\nPlease try again later or contact support.\n-# If you do end up contacting support, please make sure to explain precisly what happened.\n-# (B.success, retry success)")
                            except Exception:
                                await channel.send("# ⚠️ The main bot has crashed.\nPlease try again later or contact support.\n-# If you do end up contacting support, please make sure to explain precisly what happened.\n-# (B.error, reply failed || B.success, retry success)")
        os.remove(ERROR_FILE)
    

    # Handle update signal
    if os.path.exists(UPDATE_FILE):
        with open(UPDATE_FILE, "r", encoding="utf-8") as f:
            update_details = f.read()
        channel = bot.get_channel(UPDATE_CHANNEL_ID)
        if channel:
            await channel.send(
                f"# 📢 **BOT Update Announcement:**\n{update_details}"
            )
        for guild in bot.guilds:
            for text_channel in guild.text_channels:
                if text_channel.name.lower() in [
                    "announcement",
                    "announcements",  
                    "⌞-announcements-⌝-📢", 
                    "📣︱annnouncements",
                    "│announcements"
                    "🧪| test-lab"
                    ]:
                    try:
                        await text_channel.send(
                            f"# 📢 **BOT Update Announcement:**\n{update_details}"
                        )
                    except Exception as e:
                        print(f"Failed to send update to {text_channel}: {e}")
        os.remove(UPDATE_FILE)

@tasks.loop(minutes=2)
async def keep_terminal_alive():
    try:
        print("💓 Heartbeat: handler still running...")
    except Exception as e:
        print(f"[Heartbeat Error] {e}")

bot.run(TOKEN)