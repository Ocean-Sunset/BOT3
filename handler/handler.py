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
import json
import argparse
import random
import time
import os
import asyncio
import discord
from discord.ext import commands, tasks
import sys
import typing
import datetime
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
     "here my token: MTM...",
     "i hardcoded this text to be random :D",
     "boblox sucks :(",
     "ur addictied to discorde",
     "lalalalalalalala",
     "did u know? this is an announcement",
]

# Assume SIGNALS_DIR is already defined
SIGNALS_DIR = os.path.join(os.path.dirname(__file__), "signals")


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"Handler bot logged in as {bot.user}")
    check_signals.start()
    keep_terminal_alive.start()
    # start guild sync task
    try:
        sync_main_bot_members.start()
    except Exception:
        pass

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

@bot.command(name="selfkick")
@commands.check(utils.is_owner)
async def selfkick(self, ctx):
    """Bot leaves the server when this command is used."""
    await ctx.send("# 👋 Leaving the server!\nSeems like my owner didn't like your server or something.")
    await ctx.guild.leave()

@bot.command(name="fix")
@commands.check(utils.is_owner)
async def fix_command(ctx, target: typing.Optional[str] = "all"):
    """Run the handler JSON fixer (user_data, server_settings, or all).

    Usage examples:
      !fix all           -> perform fixes (default)
      !fix all dry       -> dry-run: analyze but do not modify files
      !fix user_data --dry
    """
    # Determine if caller requested dry-run
    args = str(target).split()
    # If multiple words given, first is target, next may be 'dry' or '--dry'
    target_name = args[0] if args else "all"
    dry = False
    if len(args) > 1:
        for token in args[1:]:
            if token.lower() in ("dry", "--dry", "--no-write"):
                dry = True

    await ctx.send(f"🔧 Handler fixer running... dry-run={dry}. This may take a few seconds.")
    try:
        report = utils.fix_json_files(target=target_name, auto_fix=not dry)
    except Exception as e:
        await ctx.send(f"❌ Fixer raised an exception: {e}")
        return

    parts = []
    for name, r in report.get("reports", {}).items():
        parts.append(f"**{name}**: checked={r.get('checked',0)} fixed={r.get('fixed',0)} anomalies={len(r.get('anomalies',[]))}")

    summary = "\n".join(parts) if parts else "Nothing to fix"

    anomalies = []
    for name, r in report.get("reports", {}).items():
        for a in r.get("anomalies", []):
            anomalies.append(f"[{name}] {a}")

    msg = f"# ✅ Handler fix completed.\n{summary}"
    if anomalies:
        anomalies_txt = "\n".join(anomalies[:50])
        if len(anomalies) > 50:
            anomalies_txt += f"\n...and {len(anomalies)-50} more anomalies."
        msg += f"\n\nDetected anomalies (truncated):\n{anomalies_txt}"

    await ctx.send(msg)

# Assume SIGNALS_DIR is already defined
SIGNALS_DIR = os.path.join(os.path.dirname(__file__), "signals")

# Assume SIGNALS_DIR is already defined
SIGNALS_DIR_EXTRA = os.path.join(os.path.dirname(__file__), "../default/signals")

# A dictionary to manage active command states
active_commands = {}

async def send_heartbeat_to_owner(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            owner = (await bot.application_info()).owner
            await owner.send(f"✅ Bot heartbeat: still alive at {datetime.datetime.now().isoformat()}")
        except Exception as e:
            print(f"Failed to send heartbeat to owner: {e}")
        await asyncio.sleep(300)  # 5 minutes

@bot.command(name="force_restart")
@commands.check(utils.is_owner)
async def force_restart(ctx):
    """Stylish restart of the main bot"""
    msg = await ctx.send("🔄 Preparing restart...")
    
    # Stages for the progress bar
    stages = [
        "Stopping bot...",
        "Device set to use CPU",
        "Loading cogs...",
        "Loading asset manager...",
        "Finalizing startup...",
        "OK",
        "✅ Restart complete!"
    ]
    
    # Store the command state in the dictionary
    command_id = ctx.message.id
    active_commands[command_id] = {
        "message": msg,
        "stages": stages,
        "current_stage": 0,
        "is_restarting": True,
        "timeout_task": asyncio.create_task(timeout_check(ctx, command_id))
    }
    
    # Send a simple restart signal to the main bot
    try:
        with open(os.path.join(SIGNALS_DIR_EXTRA, "restart_request.txt"), "w") as f:
            f.write(str(command_id))
    except Exception as e:
        await ctx.send(f"❌ Failed to send restart signal: {e}")
        del active_commands[command_id]
        return

    # Start the progression based on signals
    await update_progress(command_id)

@bot.command(name="help")
async def smart_help(ctx, *, command: str = None): # Added default None and changed to * for multi-word commands
    """
    Show a list of all commands grouped by category (cog), paginated with buttons,
    or provide detailed help for a specific command.
    """
    prefix = ctx.prefix

    if command is None:
        # Group commands by cog
        categories = {}
        for cmd in bot.commands: # Changed 'command' to 'cmd' to avoid conflict
            if cmd.hidden:
                continue
            cog = cmd.cog_name or "Other"
            categories.setdefault(cog, []).append(cmd)

        # Prepare pages (one page per category/cog)
        pages = []
        for cog, cmds in categories.items():
            lines = [f"`{prefix}{c.name}`: {c.short_doc or 'No description'}" for c in cmds] # Changed 'command' to 'c'
            value = ""
            more = False
            for line in lines:
                if len(value) + len(line) + 1 > 1000:
                    more = True
                    break
                value += line + "\n"
            if more:
                value += "...and more"
            embed = discord.Embed(
                title="📖 Bot Commands",
                description=f"Use `{prefix}help <command>` for more info.",
                color=discord.Color.blue(),
            )
            embed.add_field(
                name=cog,
                value=value or "No commands.",
                inline=False
            )
            pages.append(embed)

        if not pages:
            await ctx.send("No commands available.")
            return

        class HelpView(discord.ui.View):
            def __init__(self, pages):
                super().__init__(timeout=60)
                self.pages = pages
                self.index = 0

            async def update_message(self, interaction: discord.Interaction):
                for child in self.children:
                    if isinstance(child, discord.ui.Button):
                        child.disabled = False
                if self.index == 0:
                    self.children[0].disabled = True  # Previous
                if self.index == len(self.pages) - 1:
                    self.children[1].disabled = True  # Next
                await interaction.response.edit_message(embed=self.pages[self.index], view=self)

            @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, disabled=True)
            async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.index > 0:
                    self.index -= 1
                    await self.update_message(interaction)

            @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
            async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.index < len(self.pages) - 1:
                    self.index += 1
                    await self.update_message(interaction)

        view = HelpView(pages)
        await ctx.send(embed=pages[0], view=view)
    else:
        # Handle specific command help
        target_command = bot.get_command(command)

        if target_command:
            embed = discord.Embed(
                title=f"❓ Help for `{prefix}{target_command.name}`",
                color=discord.Color.green()
            )
            
            # Use the 'help' attribute first, then 'short_doc'
            description = target_command.help or target_command.short_doc or "No detailed description available."
            embed.description = description

            # Add command usage if available (e.g., from signature)
            if target_command.signature:
                embed.add_field(name="Usage", value=f"`{prefix}{target_command.qualified_name} {target_command.signature}`", inline=False)
            else:
                embed.add_field(name="Usage", value=f"`{prefix}{target_command.qualified_name}`", inline=False)
            
            # You can add more fields if your commands have aliases, cooldowns, etc.
            if target_command.aliases:
                embed.add_field(name="Aliases", value=", ".join([f"`{alias}`" for alias in target_command.aliases]), inline=False)

            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Command `{command}` not found. Use `{prefix}help` to see all commands.")

async def update_progress(command_id):
    """Updates the progress bar and status text."""
    if command_id not in active_commands:
        return

    state = active_commands[command_id]
    msg = state["message"]
    current_stage_index = state["current_stage"]
    stages = state["stages"]

    # This loop will continue until all stages are complete or a signal fails
    while state["is_restarting"] and current_stage_index < len(stages):
        stage_text = stages[current_stage_index]
        
        # Build the progress bar
        filled = "█" * (current_stage_index + 1)
        dots = "• " * (len(stages) - (current_stage_index + 1))
        bar = f"[ {filled:<{len(stages)}}░░{dots}]"
        
        spinner = ["|", "/", "-", "\\"]
        spin = spinner[(current_stage_index) % len(spinner)]
        
        await msg.edit(content=f"# {spin} {stage_text}\n{bar}")
        
        # Wait for the main bot's signal confirming this stage is done
        try:
            # We'll poll for a response file from the bot
            response_file = os.path.join(SIGNALS_DIR_EXTRA, "restart_status.txt")
            
            # Wait with a timeout for the bot's response
            await asyncio.wait_for(
                wait_for_file_with_id(response_file, command_id),
                timeout=30 # 30 seconds timeout
            )
            
            # Once the file is found and read, we can proceed to the next stage
            current_stage_index += 1
            state["current_stage"] = current_stage_index
            
        except asyncio.TimeoutError:
            await msg.edit(content=f"# ❌ ERR_444 - No response from bot. Restart cancelled.")
            state["is_restarting"] = False
            # Clean up the state
            if command_id in active_commands:
                if "timeout_task" in active_commands[command_id]:
                    active_commands[command_id]["timeout_task"].cancel()
                del active_commands[command_id]
            # You might also want to signal the bot to cancel its operation here.
            return
        
    # Final message after successful completion
    if state["is_restarting"] and current_stage_index == len(stages):
        await msg.edit(content="# ✅ Restart complete!")
        # Clean up the state
        if command_id in active_commands:
            if "timeout_task" in active_commands[command_id]:
                active_commands[command_id]["timeout_task"].cancel()
            del active_commands[command_id]

async def wait_for_file_with_id(file_path, command_id):
    """Waits for a file to appear with the correct command ID."""
    while True:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content == str(command_id):
                os.remove(file_path)
                return True
        await asyncio.sleep(1)

async def timeout_check(ctx, command_id):
    """A separate task to handle timeouts."""
    await asyncio.sleep(30)
    if command_id in active_commands and active_commands[command_id]["is_restarting"]:
        await active_commands[command_id]["message"].edit(
            content="# ❌ ERR_444 - No response from bot. Restart cancelled."
        )
        active_commands[command_id]["is_restarting"] = False
        del active_commands[command_id]
        # You would also signal the bot to stop here
        with open(os.path.join(SIGNALS_DIR_EXTRA, "cancel_restart.txt"), "w") as f:
            f.write(str(command_id))

@tasks.loop(seconds=1)
async def check_signals():
    # This loop now primarily handles errors and updates, not the command flow itself.
    # The `update_progress` function handles the restart flow.
    # ... (rest of your check_signals for ERROR_FILE and UPDATE_FILE remains the same)
    pass


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
    # Check for main bot leaving signal
    botleft_path = os.path.join(SIGNALS_DIR, "botleft.txt")
    if os.path.exists(botleft_path):
        try:
            with open(botleft_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                try:
                    gid = int(content)
                    # If handler is also in that guild, leave it
                    for g in list(bot.guilds):
                        if g.id == gid:
                            try:
                                logging.info(f"Handler detected main bot left guild {g.id}; leaving")
                                await g.leave()
                            except Exception as e:
                                logging.warning(f"Failed to leave guild {g.id}: {e}")
                            break
                except Exception:
                    logging.debug(f"Invalid guild id in botleft.txt: {content}")
        except Exception as e:
            logging.debug(f"Error processing botleft.txt: {e}")
        finally:
            try:
                os.remove(botleft_path)
            except Exception:
                pass
    
    handler_signal_path = os.path.join(SIGNALS_DIR, "handler_signal.txt")
    if os.path.exists(handler_signal_path):
        await asyncio.sleep(0.5) # Wait for file to be fully written
        try:
            with open(handler_signal_path, "r", encoding="utf-8") as f:
                signal_data = f.read().strip().split(",")
            
            # Example signal format: "restart_status,user_id,message_id,status_code,message_text"
            command_type = signal_data[0]
            user_id = int(signal_data[1])
            message_id = int(signal_data[2])
            status = signal_data[3]
            message_text = signal_data[4]
            
            if command_type == "restart_status" and user_id in utils.active_commands:
                command_info = utils.active_commands[user_id]
                if command_info["message_id"] == message_id:
                    channel = bot.get_channel(command_info["channel_id"])
                    if channel:
                        try:
                            msg = await channel.fetch_message(message_id)
                            # Update the progress bar and text based on the status
                            # You'll need to define a mapping from status codes to progress.
                            total_stages = 7 # Example
                            current_stage = int(status)
                            filled = "█" * current_stage
                            dots = "• " * (total_stages - current_stage)
                            bar = f"[ {filled:<{total_stages}}░░{dots}]" # This needs to be adjusted
                            
                            await msg.edit(content=f"# {message_text}\n{bar}")

                            if status == "complete" or status.startswith("ERR_"):
                                del utils.active_commands[user_id]
                                # Add logic to handle final message for success/failure
                                if status == "complete":
                                    await msg.edit(content="# ✅ Restart command executed!")
                                else:
                                    await msg.edit(content=f"# ❌ Restart failed.\nDetails: {message_text}")

                        except discord.HTTPException as e:
                            print(f"Failed to edit message {message_id}: {e}")
            
            os.remove(handler_signal_path)

        except Exception as e:
            print(f"Error processing handler signal file: {e}")
            # Ensure the file is removed even on error
            if os.path.exists(handler_signal_path):
                os.remove(handler_signal_path)

    # Timeout check for commands
    for user_id, command_info in list(utils.active_commands.items()):
        if asyncio.get_event_loop().time() - command_info["last_update"] > 30:
            channel = bot.get_channel(command_info["channel_id"])
            if channel:
                try:
                    msg = await channel.fetch_message(command_info["message_id"])
                    await msg.edit(content="# ❌ ERR_444 - No response from bot.\nRestart cancelled. Try again.")
                    # Cancel the request on the bot side by signaling it
                    cancel_signal_path = os.path.join(SIGNALS_DIR, "cancel_restart.txt")
                    with open(cancel_signal_path, "w") as f:
                        f.write(f"cancel_restart,{user_id},{command_info['message_id']}")
                except discord.HTTPException:
                    pass
            del utils.active_commands[user_id]


@tasks.loop(minutes=1)
async def keep_terminal_alive():
    try:
        print("Heartbeat: handler still running...")
    except Exception as e:
        print(f"[Heartbeat Error] {e}")


async def main():
    # ...existing bot setup code...
    bot.loop.create_task(send_heartbeat_to_owner(bot))
    # ...existing code to run the bot...


@tasks.loop(seconds=30)
async def sync_main_bot_members():
    """Read main bot_data.txt and leave any guilds the main bot is no longer in.

    The main bot writes a file `bot_data.txt` in the default folder. This task
    reads `guild_ids=` line and parses the JSON array saved there. If the
    handler is in a guild whose id is not present in that list, the handler
    will attempt to leave that guild. This runs every 30 seconds and also
    runs once when the handler becomes ready.
    """
    # wait until bot is ready
    await bot.wait_until_ready()
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "default", "bot_data.txt"))
    try:
        if not os.path.exists(data_path):
            return
        # Prefer reading a direct main bot id file written by the main bot. If present
        # we can test membership by trying to resolve the user in each guild.
        main_id_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "default", "handler", "signals", "main_bot_id.txt"))
        main_bot_id = None
        if os.path.exists(main_id_file):
            try:
                with open(main_id_file, "r", encoding="utf-8") as f:
                    main_bot_id = int(f.read().strip())
            except Exception:
                main_bot_id = None

        main_guild_ids = None
        if main_bot_id:
            # Use direct membership test per guild
            for guild in list(bot.guilds):
                try:
                    member = guild.get_member(main_bot_id)
                    # If not cached, try fetch (best-effort)
                    if member is None:
                        try:
                            member = await guild.fetch_member(main_bot_id)
                        except Exception:
                            member = None

                    if member is None:
                        # main bot not found in this guild -> leave
                        try:
                            logging.info(f"Handler leaving guild {guild.name} ({guild.id}) because main bot (id={main_bot_id}) is not present")
                            await guild.leave()
                        except Exception as e:
                            logging.warning(f"Failed to leave guild {guild.id}: {e}")
                except Exception:
                    continue
        else:
            # Fallback: parse bot_data.txt for guild_ids line
            with open(data_path, "r", encoding="utf-8") as f:
                content = f.read()
            # find the line starting with 'guild_ids='
            guild_ids_line = None
            for line in content.splitlines():
                if line.startswith("guild_ids="):
                    guild_ids_line = line[len("guild_ids="):]
                    break
            if not guild_ids_line:
                return
            try:
                main_guild_ids = set(json.loads(guild_ids_line))
            except Exception:
                # if parsing fails, skip this run
                return

            # compare with handler guilds
            for guild in list(bot.guilds):
                try:
                    if str(guild.id) not in main_guild_ids and guild.id not in main_guild_ids:
                        # The main bot is not in this guild according to bot_data.txt
                        try:
                            logging.info(f"Handler leaving guild {guild.name} ({guild.id}) because main bot is gone")
                            await guild.leave()
                        except Exception as e:
                            logging.warning(f"Failed to leave guild {guild.id}: {e}")
                except Exception:
                    continue
    except Exception as e:
        logging.debug(f"sync_main_bot_members error: {e}")

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