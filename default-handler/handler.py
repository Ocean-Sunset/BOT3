import discord
from discord.ext import tasks, commands
import os
from dotenv import load_dotenv
load_dotenv()
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

@tasks.loop(seconds=5)
async def check_signals():
    # Handle error signal
    if os.path.exists(ERROR_FILE):
        if os.path.exists(LAST_COMMAND_FILE):
            with open(LAST_COMMAND_FILE, "r", encoding="utf-8") as f:
                line = f.read().strip()
                if "," in line:
                    channel_id, message_id = map(int, line.split(","))
                    channel = bot.get_channel(channel_id)
                    if channel:
                        try:
                            msg = await channel.fetch_message(message_id)
                            await msg.reply(f"# ⚠️ The main bot has crashed.\nPlease try again later or contact support.\n-# If you do end up contacting support, please send them this as well:```{error_details}```")
                        except Exception:
                            # Fallback: just send to the channel
                            await channel.send("⚠️ The main bot has crashed. Please try again later or contact support.\n-# (COULD NOT FIND CHANNEL)")
        with open(ERROR_FILE, "r", encoding="utf-8") as f:
            error_details = f.read()
        channel = bot.get_channel(ERROR_CHANNEL_ID)
        if channel:
            await channel.send(
                f"# A CRITICAL ERROR OCCURED \nDetails:\n```{error_details}```"
            )
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

bot.run(TOKEN)