"""
# Ediscord utils package
Utility package for Ediscord.

Contains:
- Helper fonctions for easier maintenance.
"""

# --------------------- IMPORTS --------------------
import json, os, logging, discord
from datetime import datetime
from Ediscord import variables
import asyncio
import time
import sys
import random
import itertools
from PIL import Image, ImageDraw
# --------------------- DEFINITONS --------------------
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

def save_user_data(data):
    """Save user data to the JSON file."""
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(variables.USER_DATA_FILE), exist_ok=True)

        # Write the data to the file
        with open(variables.USER_DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
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

def write_bot_data(bot):
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
    with open(variables.BOT_DATA_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(data))
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

def load_akari_rewards():
    """Load akari rewards"""
    try:
        with open(variables.AKARI_REWARDS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def load_akari_points():
    try:
        with open(variables.AKARI_POINTS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_akari_points(data):
    with open(variables.AKARI_POINTS_FILE, "w") as f:
        json.dump(data, f)

def is_akari_event_active():
    now = datetime.now()
    return variables.AKARI_EVENT_START <= now <= variables.AKARI_EVENT_END

# --------------------- ASYNC DEFINITONS ---------------------
async def update_bot_data_periodically(bot):
    """Periodically update bot_data.txt."""
    while True:
        write_bot_data(bot)
        await asyncio.sleep(5)  # Update every 5 seconds

# Background task to monitor inactivity
async def monitor_inactivity():
    global last_activity_time
    
    # Update last activity time for inactivity monitoring
    last_activity_time = time.time()
    
    while True:
        await asyncio.sleep(60)  # Check every minute
        time_since_last_activity = time.time() - last_activity_time
        if time_since_last_activity > 1200:  # 20 minutes = 1200 seconds
            logging.info("No activity detected for 20 minutes. Restarting the bot...")
            os.execv(
                sys.executable, ["python", __file__, "--skip-input"]
            )  # Restart the bot

async def change_status(bot):
    """Rotate statuses dynamically or use a custom status."""
    global custom_status
    statuses = itertools.cycle(
        [
            discord.Game("with Python ❤️"),
            discord.Activity(
                type=discord.ActivityType.watching,
                name="[ 🔍 Akari's Ashed Graveyard]: https://discord.gg/HR48uPMUfK",
            ),
            discord.Streaming(
                name="DONT CLICK PLS", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
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
    role_name = variables.level_roles.get(level)
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
            await channel.send(
                f"🎉 {member.mention} has been assigned the **{role_name}** role for reaching Level {level}!"
            )
        except discord.Forbidden:
            logging.warning(
                f"Insufficient permissions to assign role '{role_name}' to {member.name}."
            )
        except Exception as e:
            logging.error(f"Error assigning role '{role_name}' to {member.name}: {e}")

async def akari_finale_task(bot):
    """Automatically run the Akari Points event finale at the end of the event."""
    await bot.wait_until_ready()
    while True:
        now = datetime.now()
        if now >= variables.AKARI_EVENT_END:
            for guild in bot.guilds:
                # Find the top Akari Points user in this guild
                points_data = load_akari_points()
                top_user_id = None
                top_points = -1
                for user_id, info in points_data.items():
                    member = guild.get_member(int(user_id))
                    if member and info.get("points", 0) > top_points:
                        top_user_id = user_id
                        top_points = info.get("points", 0)
                if top_user_id:
                    winner = guild.get_member(int(top_user_id))
                    role_name = "Guild Owner's Assistant 👑"
                    role = discord.utils.get(guild.roles, name=role_name)
                    if not role:
                        role = await guild.create_role(name=role_name, color=discord.Color.gold(), reason="Akari Points Event Winner")
                    await winner.add_roles(role)
                    # Announce in a general/announcement channel
                    channel = discord.utils.find(
                        lambda c: ("announcement" in c.name.lower() or "general" in c.name.lower()) and isinstance(c, discord.TextChannel),
                        guild.channels
                    )
                    if channel:
                        await channel.send(
                            f"🏆 **Akari Points Event Finale!** 🏆\n"
                            f"Congratulations {winner.mention}, you are now the **{role_name}** and must serve the Guild Owner for the next month! 🎉"
                        )
            break  # Only run once
        await asyncio.sleep(3600)  # Check every hour
