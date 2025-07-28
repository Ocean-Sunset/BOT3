# --------------------- IMPORTS --------------------
import discord
from discord.ext import commands
from Ediscord import utils, variables
import asyncio
import logging
import requests
import os
from yt_dlp import YoutubeDL
from discord import FFmpegPCMAudio
from googletrans import Translator
import typing
import re

# --------------------- UTILITY COMMANDS --------------------
print("✅ - Utility loaded.")
class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="choose_region")
    @utils.admin_or_owner()
    async def choose_region(self, ctx):
        """Allow users to choose a region by reacting to emojis."""
        message = await ctx.send(
            "# Choose your region by reacting with the corresponding emoji:\n"
            "🌍 for **Africa**\n"
            "🌎 for **America**s\n"
            "🌏 for **Asia**\n"
            "🇪🇺 for **Europe**\n"
            "🇦🇺 for **Oceania**"
        )
        reactions = ["🌍", "🌎", "🌏", "🇪🇺", "🇦🇺"]
        for reaction in reactions:
            await message.add_reaction(reaction)

        # Save the message ID for tracking reactions
        data = utils.load_user_data()
        data["region_message_id"] = message.id
        utils.save_user_data(data)
    
    @commands.command(name="search_img")
    async def search_img(self, ctx, *, query: str):
        if query == None:
            await ctx.send("# ❌  No query has been implemented!\nTry typing: `cute dogs` or something else.")
            return
        headers = {"Authorization": f"Client-ID {variables.UNSPLACH_API_KEY}"}
        search_url = "https://api.unsplash.com/search/photos"
        params = {"query": query, "per_page": 1}

        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        search_results = response.json()

        if search_results["results"]:
            img_url = search_results["results"][0]["urls"]["regular"]
            await ctx.send(img_url)
        else:
            await ctx.send("# ❓ No results found.\nMaybe try typing something else?")
    
    @commands.command()
    @commands.check(utils.is_owner)  # Ensure the user has the required permissions
    async def createrole(self, ctx, name: str, power: str, color: str):
        if name == None:
            await ctx.send("# ❌ No name has been put!\n-# Use `Member` for example!")
            return
        if power == None:
            await ctx.send("# ❌ No administration / level power put!\n-# You can use member, mod or admin!")
            return
        if color == None:
            await ctx.send("# ❌ No color has been implemented!\n-# The colors are HEX-CODE! search them with `?color`")
            return
        """Create a role with a specified name, power level, and color."""
        
        # Map power levels to Discord permissions
        permissions_map = {
            "member": discord.Permissions(permissions=0),  # No special permissions
            "mod": discord.Permissions(manage_messages=True, kick_members=True),
            "admin": discord.Permissions(administrator=True),
        }

        # Validate power level
        if power.lower() not in permissions_map:
            print(
                f"Create role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Invalid power level."
            )
            await ctx.send("# ❌ Invalid power level.\nUse `member`, `mod`, or `admin`.")
            return

        # Validate color
        try:
            color_hex = color
            discord_color = discord.Color(int(color_hex.lstrip("#"), 16))  # Convert hex color to Discord.Color
        except ValueError:
            print(
                f"Create role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Invalid color."
            )
            await ctx.send(
                "# ❌ Invalid color.\nPlease provide a valid hex color (e.g., `#FF5733`)."
            )
            return

        # Create the role
        try:
            role = await ctx.guild.create_role(
                name=name,
                permissions=permissions_map[power.lower()],
                color=discord_color,
                reason=f"Role created by {ctx.author}",
            )
            print(
                f"Create role command triggered by {ctx.author} in channel {ctx.channel}. State: success."
            )
            await ctx.send(f"✅ Role **{role.name}** created successfully!")
            logs_channel = utils.get_logs_channel(ctx.guild)
            if logs_channel:
                await logs_channel.send(f"Role **{role.name}** created by {ctx.author}")
        except discord.Forbidden:
            print(
                f"Create role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Forbidden."
            )
            await ctx.send("# ❌ I do not have permission to create roles.\nPlease grant me a higher permission for me to create roles.")
        except Exception as e:
            print(
                f"Create role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: {e}"
            )
            await ctx.send(f"# ❌ An error occurred:\n{e}")
            
    @commands.command()
    @commands.check(utils.is_owner)  # Ensure the user has the required permissions
    async def giverole(self, ctx, role_name: str, member: discord.Member):
        if role_name == None:
            await ctx.send("# ❌ No role name has been specified!\n-# Try inserting a already existing role name!")
            return
        if member == None:
            await ctx.send("# ❌ No member has been specified!\n-# Please specify a member so that i can give him his role!")
            return
        """Assign a role to a specified user."""
        # Find the role in the server
        role = discord.utils.find(lambda r: r.name == role_name, ctx.guild.roles)

        if role is None:
            print(
                f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Role not found."
            )
            await ctx.send(f"# ❌ Role **{role_name}** not found in this server.\nThe bot couldn't find the role!\n-# does it exist?")
            return

        # Check if the bot has permission to assign this role
        if ctx.guild.me.top_role <= role:
            print(
                f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Insufficient permissions."
            )
            await ctx.send(
                f"# ❌ I cannot assign this role because it is higher or equal to my highest role.\n-# Sorry.. here's a tip btw: {utils.little_text()}"
            )
            return

        # Assign the role
        try:
            if role in member.roles:
                print(
                    f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Role already assigned."
                )
                await ctx.send(
                    f"# :grey_question: {member.mention} already has the **{role.name}** role.\n{utils.little_text()}"
                )
            else:
                await member.add_roles(role, reason=f"Role assigned by {ctx.author}")
                print(
                    f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: success."
                )
                await ctx.send(
                    f"# ✅ Role **{role.name}** assigned to {member.mention} successfully!"
                )
            return
        except discord.Forbidden:
            print(
                f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Forbidden."
            )
            await ctx.send("# ❌ I do not have permission to assign this role.\nMaybe try giving me more permissions?\n-# You can do that by giving me a higher role!")
        except Exception as e:
            print(
                f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: {e}"
            )
            await ctx.send(f"# ❌ An error occurred:\n{e}")

    @commands.command()
    @commands.check(utils.is_owner)
    async def removerole(self, ctx, role: discord.Role, member: discord.Member):
        if role == None:
            await ctx.send("# ❌ No role name has been specified!\n-# Try inserting a already existing role name!")
            return
        if member == None:
            await ctx.send("❌ No member has been specified!\n-# Please specify a member so that i can remove his role!")
            return
        if role in member.roles:
            await member.remove_roles(role)
            await ctx.send(f"# ✅ Removed role **{role.name}** from {member.mention}.")
        else:
            await ctx.send(f"# ❌ {member.mention} does not have the role **{role.name}**.\n-# Maybe you spelt it wrong? Try again!")
    
    @commands.command(name="OLDcolorrole")
    async def OLDcolorrole(self, ctx):
        """Allow users to choose a color role by reacting to emojis."""
        message = await ctx.send(
            "# Which color do you want?\n"
            "React with:\n"
            "- 🔴 for **Red**\n"
            "- 🟠 for **Orange**\n"
            "- 🟡 for **Yellow**\n"
            "- 🟢 for **Green**\n"
            "- 🔵 for **Blue**\n"
            "- 🟣 for **Violet**\n"
            "- ⚪ for **White**\n"
            "- ⚫ for **Black**\n"
            "- 🟫f or **Brown**\n"
            "- 🟦 for **Cyan**\n"
            "- 🟪 for **Magenta**\n"
            "- 🩵 for **Light Blue**\n"
            "- 🩷 for **Pink**\n"
            "- 🩶 for **Grey**"
        )
        reactions = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "⚪", "⚫", "🟫", "🟦", "🟪", "🩵", "🩷", "🩶"]
        for reaction in reactions:
            await message.add_reaction(reaction)

        # Save the message ID for tracking reactions
        data = utils.load_user_data()
        data["colorrole_message_id"] = message.id
        utils.save_user_data(data)
    
    @commands.command(name="colorrole")
    async def colorrole(self, ctx, *, color_input: str = None):
        """Assigns or resets a shared color role."""
        if not color_input:
            return await ctx.send("# ⚠️ WARNING!\nPlease provide a color name, HEX code, or `reset` to remove your color.")

        guild = ctx.guild
        member = ctx.author
        

        # Reset command
        if color_input.lower() == "reset":
            removed = False
            for role in member.roles:
                if role.name.startswith("Color: "):
                    try:
                        await member.remove_roles(role)
                        removed = True
                    except discord.Forbidden:
                        return await ctx.send("# ❌ I don't have permission to remove your old color role. Please check my role permissions.")
                    except Exception as e:
                        return await ctx.send(f"# ❌ Failed to remove old color role: {e}")
            if removed:
                await ctx.send("# 🗑️ Your color role has been removed.\n-# Are you gonna choose another color? maybe?..")
            else:
                await ctx.send("# ❌ You don’t have a color role.\n-# Sure you spelt it right? Try again!")
            return

        # Get color
        color_input = color_input.lower().replace(" ", "")
        if color_input in variables.COLOR_MAP:
            hex_value = variables.COLOR_MAP[color_input]
            role_name = f"Color: {color_input.capitalize()}"
        else:
            match = re.match(variables.HEX_REGEX, color_input)
            if match:
                hex_value = int(match.group(1), 16)
                role_name = f"Color: #{match.group(1).upper()}"
            else:
                return await ctx.send(f"# ❌ Invalid color.\nUse a name like `red` or a HEX code like `#00ffcc`.\n-# {utils.little_error_variant()}")

        for role in member.roles:
            if role.name.startswith("Color: "):
                try:
                    await member.remove_roles(role)
                except discord.Forbidden:
                    return await ctx.send("# ❌ I don't have permission to remove old color roles. Please check my role permissions.")
                except Exception as e:
                    return await ctx.send(f"# ❌ Failed to remove old color role: {e}")

        # Look for existing role
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            # Create role if it doesn't exist
            bot_member = guild.get_member(self.bot.user.id)
            target_position = 1 
            sorted_roles_desc = sorted(guild.roles, key=lambda r: r.position, reverse=True)
            effective_ceiling_position = 0 # Default to @everyone position
            for r in sorted_roles_desc:
                if not r.permissions.administrator and not r.managed:
                    effective_ceiling_position = r.position 
                    break

            new_role_position = effective_ceiling_position + 1
            if bot_member and bot_member.top_role:
                new_role_position = min(new_role_position, bot_member.top_role.position - 1)
            
            new_role_position = max(1, new_role_position)
            
            try:
                role = await guild.create_role(name=role_name, colour=discord.Colour(hex_value), reason="New shared color role")
                await role.edit(position=new_role_position)
            except discord.Forbidden:
                return await ctx.send("# ❌ I don't have permission to manage roles (create/position). Please check my role permissions.")
            except Exception as e:
                return await ctx.send(f"# ❌ Failed to create/assign role: {e}")

        # Assign role
        try:
            await member.add_roles(role)
            await ctx.send(f"# ✅ You now have the `{role_name}` role!\n-# {utils.little_text()}", delete_after=5)
        except discord.Forbidden:
            await ctx.send("# ❌ I don't have permission to assign roles. Please check my role permissions.", delete_after=5)
        except Exception as e:
            await ctx.send(f"# ❌ Failed to assign role: {e}", delete_after=5)
    
    @commands.command(name="reminder")
    async def remindme(self, ctx, time: int, *, reminder: str):
        """Set a reminder."""
        if time == None:
            await ctx.send(f"# ❌ No time has been specified\n-# {utils.little_error_variant()}")
            return
        if reminder == None:
            await ctx.send(f"# ❌ No description reminder has been specified!\n {utils.little_error_variant()}")
            return
        await ctx.send(f"# ⏰ I will remind you in **{time}** seconds:\n{reminder}")
        await asyncio.sleep(time)
        await ctx.send(f"🔔 {ctx.author.mention}, here is your **reminder**:\n# {reminder}")


    @commands.command(name="mute")
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, *, reason=None):
        """Mute a user."""
        if member == None:
            await ctx.send(f"# ❌ No member has been specified!\n-# {utils.little_error_variant()}")
            return
        if reason == None:
            reason = "No reason has been specified"
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False)
        await member.add_roles(mute_role, reason=reason)
        await ctx.send(f"# ✅ {member.mention} has been muted.\nReason: {reason}")


    @commands.command(name="unmute")
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        """"Unmute a user."""
        if member == None:
            await ctx.send(f"# ❌ No member has been specified!\n-# {utils.little_error_variant()}")
            return
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if mute_role in member.roles:
            await member.remove_roles(mute_role)
            await ctx.send(f"# ✅ {member.mention} has been unmuted.")
        else:
            await ctx.send(f"# ❌ {member.mention} is not muted.\n-# {utils.little_error_variant()}")


    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Delete a number of messages."""
        if amount == None:
            await ctx.send(f"# ❌ No amount has been specified!\nInput an amount like this: `?purge 3`\n-# {utils.little_error_variant()}")
            return
        await ctx.channel.purge(limit=amount)
        await ctx.send(f"# ✅ Deleted {amount} messages.", delete_after=5)
    
    @commands.command(name="setwelcome")
    @utils.admin_or_owner()
    async def set_welcome_message(self, ctx, *, message: str):
        """Set a custom welcome message for this server."""
        if message == None:
            await ctx.send(f"# ❌ No message has been specified!\nType a message like this: `?setwelcome Hi welcome!`\n-# {utils.little_error_variant()}")
            return
        utils.set_guild_welcome_message(ctx.guild.id, message)
        await ctx.send("# ✅ Custom welcome message set!")

    @commands.command(name="setgoodbye")
    @utils.admin_or_owner()
    async def set_goodbye_message(self, ctx, *, message: str):
        """Set a custom goodbye message for this server."""
        if message == None:
            await ctx.send(f"# ❌ No message has been specified!\nType a message like this: `?setgoodbye Oh ok.. bye...`\n-# {utils.little_error_variant()}")
            return
        utils.set_guild_goodbye_message(ctx.guild.id, message)
        await ctx.send("# ✅ Custom goodbye message set!")

    @commands.command(name="color")
    async def color(self, ctx, *, color_input: str):
        """Display the exact color based on a name or hex code."""
        if color_input == None:
            await ctx.send("# ❌ No color has been specified!")
            return
        try:
            # Use a predefined dictionary of color names and their hex values
            color_names = {
                "red": "#FF0000",
                "green": "#00FF00",
                "blue": "#0000FF",
                "yellow": "#FFFF00",
                "orange": "#FFA500",
                "purple": "#800080",
                "pink": "#FFC0CB",
                "black": "#000000",
                "white": "#FFFFFF",
                "gray": "#808080",
                "cyan": "#00FFFF",
                "magenta": "#FF00FF",
                "brown": "#A52A2A",
            }
            # Check if the input is a hex code
            if color_input.startswith("#"):
                # Convert the hex code to an integer and create a Discord color
                color_value = discord.Color(int(color_input.lstrip("#"), 16))
            else:
                if color_input.lower() not in color_names:
                    await ctx.send(f"# ❌ Invalid color name or hex code.\n-# {utils.little_error_variant()}")
                    return
                color_value = discord.Color(
                    int(color_names[color_input.lower()].lstrip("#"), 16)
                )

            # Create an embed to display the color
            embed = discord.Embed(
                title="Color Preview",
                description=f"Here is the color for `{color_input}`.",
                color=color_value,
            )
            embed.add_field(
                name="Hex Code",
                value=(
                    color_input
                    if color_input.startswith("#")
                    else color_names[color_input.lower()]
                ),
            )
            embed.set_thumbnail(
                url=f"https://singlecolorimage.com/get/{color_value.value:06x}/400x400"
            )
            await ctx.send(embed=embed)

        except ValueError:
            await ctx.send(
                f"# ❌ Invalid color input.\nPlease provide a valid color name or hex code (e.g., `red` or `#FF0000`).\n-# {utils.little_error_variant()}"
            )
        
    @commands.command(name="upload")
    async def upload(self, ctx, *, url: typing.Optional[str] = None):
        await ctx.send("-# WARNING: The current music system doesn't work, we are working to fix this issue.")
        """Allow users to upload .mp3 files or provide a URL to download."""
        if url == None:
            await ctx.send(f"# ❌ No url or file has been specified and or sent!\n-# {utils.little_error_variant()}")
            return
        # Check if the music folder has more than 50 files
        oldest_file = utils.check_music_folder()
        if oldest_file:
            await ctx.send(
                f"# ⚠️ WARNING:\n The music folder has more than 50 songs. Continuing will delete the oldest file: `{os.path.basename(oldest_file)}`. Do you want to proceed? (yes/no)\n-# {utils.little_unsure_variant()}"
            )

            def check(m):
                return (
                    m.author == ctx.author
                    and m.channel == ctx.channel
                    and m.content.lower() in ["yes", "no"]
                )

            try:
                response = await ctx.bot.wait_for("message", check=check, timeout=30.0)
                if response.content.lower() == "no":
                    await ctx.send("# ❌ Operation canceled.")
                    return
                else:
                    os.remove(oldest_file)  # Delete the oldest file
                    await ctx.send(
                        f"# 🗑️ Deleted the oldest file:\n`{os.path.basename(oldest_file)}`."
                    )
            except asyncio.TimeoutError:
                await ctx.send("# ⏰ You took too long to respond.\nAs a result of this the operation canceled.")
                return

        # Proceed with the upload logic
        if not ctx.message.attachments and not url:
            await ctx.send(f"# ❌ Please attach an audio file or provide a URL to upload.\n-# {utils.little_error_variant()}")
            return

        # Handle file attachments
        if ctx.message.attachments:
            for attachment in ctx.message.attachments:
                if attachment.filename.endswith((".mp3", ".wav", ".ogg")):
                    file_path = os.path.join("music", attachment.filename)
                    await attachment.save(file_path)
                    await ctx.send(
                        f"# ✅ File `{attachment.filename}` has been uploaded and saved."
                    )
                else:
                    await ctx.send(
                        f"# ❌ `{attachment.filename}` is not a supported audio format.\nPlease upload .mp3, .wav, or .ogg files.\n-# More support for custom sound files (.wma, .aiff, etc..) are coming soon!"
                    )

        # Handle URL input
        if url:
            if url.startswith("http://") or url.startswith("https://"):
                await ctx.send(f"🔍 Downloading from URL: `{url}`...")
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": "music/%(title)s.%(ext)s",
                    "noplaylist": True,
                }
                try:
                    with YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        if info is not None and 'title' in info:
                            file_name = ydl.prepare_filename(info)
                            await ctx.send(
                                f"# ✅ Downloaded `{info['title']}`\nand saved to the music folder."
                            )
                        else:
                            await ctx.send(f"# ❌ Failed to retrieve video information after download.\n{utils.little_error_variant()}")
                except Exception as e:
                    await ctx.send(f"# ❌ Failed to download from URL:\n{e}")
            else:
                await ctx.send(
                    "# ❌ Invalid URL.\nPlease provide a valid URL starting with `http://` or `https://`."
                )


    @commands.command(name="play")
    async def play(self, ctx, *, query: typing.Optional[str] = None):
        await ctx.send("-# WARNING: The current music system doesn't work, we are working to fix this issue.")
        """Play a song from a URL, the music folder, or by its number, with an optional loop count."""
        if query == None:
            await ctx.send("# ❌ No query (url or file) has been specified!\n-# If you want more info of our current soung file systems, run `?queue`!")
            return
        # Check if the music folder has more than 50 files
        oldest_file = utils.check_music_folder()
        if oldest_file:
            await ctx.send(
                f"# ⚠️ WARNING:\n The music folder has more than 50 songs. Continuing will delete the oldest file: `{os.path.basename(oldest_file)}`. Do you want to proceed? (yes/no)\n-# {utils.little_unsure_variant()}"
            )

            def check(m):
                return (
                    m.author == ctx.author
                    and m.channel == ctx.channel
                    and m.content.lower() in ["yes", "no"]
                )

            try:
                response = await ctx.bot.wait_for("message", check=check, timeout=30.0)
                if response.content.lower() == "no":
                    await ctx.send("# ❌ Operation canceled.")
                    return
                else:
                    os.remove(oldest_file)  # Delete the oldest file
                    await ctx.send(
                        f"# 🗑️ Deleted the oldest file:\n`{os.path.basename(oldest_file)}`."
                    )
            except asyncio.TimeoutError:
                await ctx.send("# ⏰ You took too long to respond.\nAs a result of this the operation canceled.")
                return

        # Proceed with the play logic
        if not ctx.author.voice:
            await ctx.send("# ❌ You must be in a voice channel to use this command.!\n-# Don't have an *easy-to-access* channel? just ask a mod to help you!")
            return

        voice_channel = ctx.author.voice.channel

        try:
            # Join the voice channel
            if ctx.voice_client is None:
                vc = await voice_channel.connect()
            else:
                vc = ctx.voice_client

            # Parse the query and loop count
            if query:
                parts = query.split(" ")
                song_query = " ".join(parts[:-1]) if parts[-1].isdigit() else query
                loop_count = int(parts[-1]) if parts[-1].isdigit() else 1

                if loop_count < 1:
                    await ctx.send("# ❌ Loop count must be at least 1.\n-# Ex. `?play <number>`")
                    return

                # Determine the song path
                if song_query.isdigit():
                    # Play the song by its number
                    songs = sorted(os.listdir("music"))
                    song_index = int(song_query) - 1  # Convert to zero-based index
                    if 0 <= song_index < len(songs):
                        song_path = os.path.join("music", songs[song_index])
                        await ctx.send(
                            f"# 🎵 Now playing: `{songs[song_index]}`\n-# (Looping {loop_count} times)\n-# That must be a cool song! right?.."
                        )
                    else:
                        await ctx.send(
                            f"# ❌ Invalid song number.\nPlease use a number between 1 and {len(songs)}.\nIf you want more info on our current song file system, use `?queue`!"
                        )
                        return
                elif song_query.startswith("http://") or song_query.startswith("https://"):
                    # Play a song from a URL
                    await ctx.send(f"# 🔍 Now downloading..\n`{song_query}`...")
                    ydl_opts = {
                        "format": "bestaudio/best",
                        "outtmpl": "music/%(title)s.%(ext)s",
                        "noplaylist": True,
                    }
                    with YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(song_query, download=True)
                        song_path = ydl.prepare_filename(info)
                        if info is not None and 'title' in info:
                            await ctx.send(
                                f"-# ✅ Downloaded `{info['title']}`."
                            )
                            await ctx.send(
                                f"# 🎵 Now playing: `{songs[song_index]}`\n-# (Looping {loop_count} times)\n-# That must be a cool song! right?.."
                            )
                        else:
                            await ctx.send(
                                f"# ❌ Failed to retrieve video information after download.\n{utils.little_error_variant()}"
                            )
                else:
                    # Play a song by its name
                    song_path = os.path.join("music", song_query)
                    if not os.path.exists(song_path):
                        await ctx.send(
                            f"# ❌ The file `{song_query}` does not exist in the music folder.\nCheck the songs with `?queue` for more help!\n-# {utils.little_error_variant()}"
                        )
                        return
                    await ctx.send(
                        f"# 🎵 Now playing: `{song_query}`\n-# (Looping {loop_count} times)\n-# That must be a cool song! right?.."
                    )

                # Set the status to "Playing <song>"
                current_status = discord.Game(f"Playing {os.path.basename(song_path)}")
                await self.bot.change_presence(
                    status=discord.Status.online, activity=current_status
                )

            else:
                # Play the first song in the music folder
                songs = sorted(os.listdir("music"))
                if not songs:
                    await ctx.send(
                        f"# ❌ The music folder is empty.\nUpload some songs using `?upload` or provide a URL.\n-# {utils.little_error_variant()}"
                    )
                    return
                song = songs[0]
                song_path = os.path.join("music", song)
                loop_count = 1
                await ctx.send(f"# 🎵 Now playing: `{song}`\n-# (Looping {loop_count} times)\n-# That must be a cool song! right?..")

            # Play the song with looping
            for i in range(loop_count):
                vc.play(
                    discord.FFmpegPCMAudio(song_path, executable=variables.ffmpeg_path),
                    after=lambda e: variables.logger.info(f"Finished playing: {song_path}"),
                )
                while vc.is_playing():
                    await asyncio.sleep(1)  # Wait for the song to finish before looping
        except Exception as e:
            variables.logger.error(f"An error occurred in the play command: {e}")
            await ctx.send(f"# ❌ An error occurred:\n{e}")


    @commands.command(name="queue")
    async def queue(self, ctx):
        await ctx.send("-# WARNING: The current music system doesn't work, we are working to fix this issue.")
        """List all songs in the music folder."""
        songs = sorted(os.listdir("music"))
        if not songs:
            await ctx.send(
                "# ❌ The music folder is empty.\nUpload some songs using `?upload`."
            )
            return

        song_list = "\n".join(f"{i + 1}. {song}" for i, song in enumerate(songs))
        await ctx.send(f"# 🎶 **Music Queue:**\n{song_list}")


    @commands.command(name="skip")
    async def skip(self, ctx):
        await ctx.send("-# WARNING: The current music system doesn't work, we are working to fix this issue.")
        """Skip the currently playing song."""
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await ctx.send("# ❌ No song is currently playing.\nPlay a song using `?play`")
            return

        ctx.voice_client.stop()
        await ctx.send("# ⏭️ Skipped the current song.")


    @commands.command(name="stop")
    async def stop(self, ctx):
        await ctx.send("-# WARNING: The current music system doesn't work, we are working to fix this issue.")
        """Stop the music and disconnect the bot."""
        if not ctx.voice_client:
            await ctx.send("❌ The bot is not connected to a voice channel.")
            return

        await ctx.voice_client.disconnect()
        await ctx.send("# ⏹️ Stopped the music and disconnected.\n-# If you ever wish to play a music again, just do `?play`!")


    @commands.command(name="check_ffmpeg")
    async def check_ffmpeg(self, ctx):
        """Check if FFmpeg is accessible."""
        try:
            import subprocess

            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode == 0:
                await ctx.send(
                    f"✅ FFmpeg is installed and accessible:\n```\n{result.stdout.splitlines()[0]}\n```"
                )
                variables.logger.info(f"FFmpeg is accessible: {result.stdout.splitlines()[0]}")
            else:
                await ctx.send(
                    "# ❌ FFmpeg is not accessible.\nPlease check your installation."
                )
                variables.logger.error(f"FFmpeg error: {result.stderr}")
        except FileNotFoundError:
            await ctx.send("# ❌ FFmpeg is not installed or not in PATH.")
            variables.logger.error("FFmpeg executable not found.")


    @commands.command(name="download")
    async def download(self, ctx, url: str):
        await ctx.send("-# WARNING: The current music system doesn't work, we are working to fix this issue.")
        """Download a YouTube song or video and save it to the music folder."""
        if url == None:
            await ctx.send("# ❌ No URL message has been specified!\n-# Do remember to use `https` or `http`!")
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            await ctx.send(
                "# ❌ Invalid URL.\nPlease provide a valid YouTube URL starting with `http://` or `https://`."
            )
            return

        await ctx.send(f"# 🔍 Downloading from URL:\n`{url}`...")
        ydl_opts = {
            "format": "bestaudio/best",  # Download the best audio format
            "outtmpl": "music/%(title)s.%(ext)s",  # Save to the music folder with the title as the filename
            "noplaylist": True,  # Do not download playlists
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is not None and 'title' in info:
                    file_name = ydl.prepare_filename(info)
                    await ctx.send(
                        f"# ✅ Downloaded `{info['title']}`\nand saved to the music folder as `{file_name}`."
                    )
                else:
                    await ctx.send("# ❌ Failed to retrieve video information after download.")
        except Exception as e:
            await ctx.send(f"# ❌ Failed to download from URL:\n{e}")
    
    @commands.command(name="ask")
    async def ask(self, ctx, *, question: str):
        await ctx.send("-# WARNING: This AI model is not trained to respond to your messages, **it will only create stories.**")
        """Answer a question using a local AI model."""
        if question == None:
            await ctx.send("# ❌ No question has been specified!\n-# it's not really a question lol :P")
            return
        try:
            # Generate a response using the Hugging Face model
            response_gen = variables.qa_pipeline(question, max_length=400, num_return_sequences=1)
            if response_gen is None:
                await ctx.send("# ❌ No answer could be generated.")
                return
            if hasattr(response_gen, "__iter__") and not isinstance(response_gen, (str, bytes, dict)):
                response = list(response_gen)
            else:
                response = [response_gen]
            if response and isinstance(response[0], dict) and "generated_text" in response[0]:
                answer = response[0]["generated_text"]
                await ctx.send(answer)
            else:
                await ctx.send("# ❌ No answer could be generated.")
        except Exception as e:
            await ctx.send(f"# ❌ An error occurred:\n{e}")
        
    @commands.command(name="translate")
    async def translate(self, ctx, target_language: str, *, text: str):
        """Translate text to a specified language."""
        if target_language == None:
            await ctx.send("# ❌ No target language has been specified!\nPlease be sure to spell your language correctly!")
            return
        if text == None:
            await ctx.send(f"# ❌ No text to translate to {target_language} has been specified!")
            return
        try:
            translation = await variables.translator.translate(text, dest=target_language)
            await ctx.send(f"# 🌐 **Translation ({target_language}):** {translation.text}")
        except Exception as e:
            await ctx.send(f"# ❌ Failed to translate:\n{e}")
        
    @commands.command(name="weather")
    async def weather(self, ctx, *, city: str):
        """Get the current weather for a city."""
        if city == None:
            await ctx.send("# ❌ No city has been specified!\nBe sure to specify a city too! not a country >:(")
            return
        api_key = variables.openwheather  # Replace with your API key
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        try:
            response = requests.get(url)
            data = response.json()
            if data["cod"] != 200:
                await ctx.send(f"❌ City not found: {city}")
                return
            weather_desc = data["weather"][0]["description"].capitalize()
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]
            await ctx.send(
                f"🌤️ **Weather in {city.capitalize()}**:\n"
                f"- Description: {weather_desc}\n"
                f"- Temperature: {temp}°C (Feels like {feels_like}°C)\n"
                f"- Humidity: {humidity}%\n"
                f"- Wind Speed: {wind_speed} m/s"
            )
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name="setverifyrole")
    @utils.admin_or_owner()
    async def set_verify_role(self, ctx, *, role: discord.Role):
        """Set the role to be given on verification for this server."""
        if not role:
            await ctx.send("# ❌ No role specified!")
            return
        settings = utils.load_server_settings()
        guild_settings = settings.get(str(ctx.guild.id), {})
        guild_settings["verify_role"] = role.name
        settings[str(ctx.guild.id)] = guild_settings
        utils.save_server_settings(settings)
        await ctx.send(f"✅ Verification role set to `{role.name}` for this server.")

    @commands.command()
    @utils.admin_or_owner()
    async def disablevariants(self, ctx):
        if ctx.guild:
            utils.disabled_variants.add(ctx.guild.id)
            await ctx.send("✅ Little variants have been **disabled** in this server.")
            utils.save_disabled_variants(ctx.guild.id)
        else:
            await ctx.send("⚠️ This command must be used in a server.")

    @commands.command()
    @utils.admin_or_owner()
    async def enablevariants(self, ctx):
        if ctx.guild:
            utils.disabled_variants.discard(ctx.guild.id)
            await ctx.send("✅ Little variants have been **re-enabled** in this server.")
        else:
            await ctx.send("⚠️ This command must be used in a server.")

    @commands.command(name="verify")
    @utils.admin_or_owner()
    async def verify(self, ctx):
        """Send a verification message and assign the custom verification role when reacted to."""
        try:
            # Get the custom verify role or default
            settings = utils.load_server_settings()
            guild_settings = settings.get(str(ctx.guild.id), {})
            verify_role_name = guild_settings.get("verify_role", ".・🍨︴Member ✰")

            # Create the embed for the verification message
            embed = discord.Embed(
                title="Verification",
                description=f"React with ✅ to verify yourself and gain access to the server!\n(You will get the `{verify_role_name}` role.)",
                color=discord.Color.green(),
            )
            embed.set_thumbnail(
                url="https://www.freeiconspng.com/thumbs/checkmark-png/checkmark-png-5.png"
            )

            # Send the embed message
            message = await ctx.send(embed=embed)

            # Add the ✅ reaction to the message
            await message.add_reaction("✅")

            # Save the message ID in the user_data.json file
            data = utils.load_user_data()
            data["verify_message_id"] = message.id
            utils.save_user_data(data)

            logging.info(
                f"Verification message sent in {ctx.channel.name} (ID: {ctx.channel.id}). Message ID: {message.id}"
            )
            await ctx.send("✅ Verification message sent successfully!")
        except Exception as e:
            logging.error(f"Error in verify command: {e}")
            await ctx.send(f"❌ An error occurred while setting up verification: {e}")

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx, category: typing.Optional[str] = None):
        """Display the leaderboard for level, XP, coins, or Easter Eggs."""
        valid_categories = ["level", "xp", "coins", "eggs"]
        if category == None:
            await ctx.send("❌ No category has been specified!")
            return
        if category not in valid_categories:
            await ctx.send(
                f"❌ Invalid category. Use `?leaderboard level`, `?leaderboard xp`, `?leaderboard coins`, or `?leaderboard eggs`."
            )
            return

        # Load user data
        data = utils.load_user_data()

        # Prepare the leaderboard
        leaderboard_data = []
        for user_id, user_info in data.items():
            if user_id.isdigit():  # Ensure it's a user ID
                user = ctx.guild.get_member(int(user_id))
                if user:  # Only include users who are in the server
                    leaderboard_data.append(
                        {
                            "name": user.display_name,
                            "level": user_info.get("level", 0),
                            "xp": user_info.get("xp", 0),
                            "coins": user_info.get("coins", 0),
                            "eggs": variables.easter_data.get(user_id, {}).get(
                                "eggs", 0
                            ),  # Include Easter Eggs
                        }
                    )

        # Sort the leaderboard based on the selected category
        leaderboard_data = sorted(leaderboard_data, key=lambda x: x[category], reverse=True)

        # Create the leaderboard message
        embed = discord.Embed(
            title=f"🏆 {category.capitalize()} Leaderboard",
            description=f"Top users by {category.capitalize()}",
            color=discord.Color.gold(),
        )

        for i, entry in enumerate(leaderboard_data[:10], start=1):  # Show top 10 users
            embed.add_field(
                name=f"{i}. {entry['name']}",
                value=f"**{category.capitalize()}:** {entry[category]}",
                inline=False,
            )

        await ctx.send(embed=embed)
    
    @commands.command(name="chatreviver-role")
    @utils.admin_or_owner()
    async def chatreviver_role(self, ctx):
        """Send a message to allow users to get the 'Chat Reviver' role by reacting."""
        try:
            # Create the embed for the Chat Reviver role
            embed = discord.Embed(
                title="Get the Chat Reviver Role",
                description=(
                    "React with 🛠️ to get the **Chat Reviver** role.\n"
                    "This role will be mentioned when the bot sends messages to revive the chat!"
                ),
                color=discord.Color.blue(),
            )
            embed.set_thumbnail(
                url="https://cdn-icons-png.flaticon.com/512/3593/3593455.png"
            )  # Example icon

            # Send the embed message
            message = await ctx.send(embed=embed)

            # Add the 🛠️ reaction to the message
            await message.add_reaction("🛠️")

            # Save the message ID in the user_data.json file
            data = utils.load_user_data()
            data["chat_reviver_message_id"] = message.id
            utils.save_user_data(data)

            logging.info(
                f"Chat Reviver role message sent in {ctx.channel.name} (ID: {ctx.channel.id}). Message ID: {message.id}"
            )
            await ctx.send("✅ Chat Reviver role message sent successfully!")
        except Exception as e:
            logging.error(f"Error in chatreviver_role command: {e}")
            await ctx.send(
                f"❌ An error occurred while setting up the Chat Reviver role: {e}"
            )
            
    @commands.command(name="announcement")
    @commands.check(utils.is_owner)
    async def announcement(self, ctx, channel_name: typing.Optional[str] = None, *, message: str):
        """
        Send an announcement to all servers' announcement channels.
        If a specific channel name is provided, send the message to that channel instead.
        """
        if channel_name == None:
            await ctx.send("❌ No channel name for the announcement has been specified!")
            return
        if message == None:
            await ctx.send("❌ No message has been specified!")
            return
        if not message:
            await ctx.send("❌ You must provide a message to send.")
            return

        # Iterate through all servers the bot is in
        for guild in self.bot.guilds:
            try:
                # If a specific channel name is provided
                if channel_name:
                    target_channel = discord.utils.find(
                        lambda c: channel_name.lower() in c.name.lower()
                        and isinstance(c, discord.TextChannel),
                        guild.channels,
                    )
                else:
                    # Default to an announcements channel
                    target_channel = discord.utils.find(
                        lambda c: "announcement" in c.name.lower()
                        and isinstance(c, discord.TextChannel),
                        guild.channels,
                    )

                if target_channel:
                    # Send the message to the target channel
                    await target_channel.send(f"📢 **Announcement:**\n{message}")
                    logging.info(
                        f"Announcement sent to {target_channel.name} in {guild.name}."
                    )
                else:
                    logging.warning(f"No suitable channel found in {guild.name}.")
                    # Optionally notify the server owner if no suitable channel is found
                    owner = guild.owner
                    if owner:
                        await owner.send(
                            f"❌ Could not find a suitable channel in your server **{guild.name}** "
                            f"to send the announcement. Please ensure an announcements channel exists."
                        )
            except discord.Forbidden:
                logging.warning(f"Permission denied to send message in {guild.name}.")
            except Exception as e:
                logging.error(f"Error sending announcement in {guild.name}: {e}")

        await ctx.send("✅ Announcement sent to all servers.")

    @commands.command(name="addrolereaction")
    @utils.admin_or_owner()
    async def add_role_reaction(self, ctx, message_id: int, emoji: str, *, role: discord.Role):
        """Link an emoji to a role for a specific message (for reaction roles)."""
        if message_id == None:
            await ctx.send("❌ No message ID has been specified! ( Right click on a message to get your ID (DEV MODE MUST BE ON) )")
            return
        if emoji == None:
            await ctx.send("❌ No emoji has been specified!")
            return
        if role == None:
            await ctx.send("❌ No role has been specified!")
            return
        utils.set_guild_role_reaction(ctx.guild.id, message_id, emoji, role.id)
        await ctx.send(f"✅ Reaction role set: {emoji} → {role.name} on message {message_id}")

    @commands.command(name="removerolereaction")
    @utils.admin_or_owner()
    async def remove_role_reaction(self, ctx, message_id: int, emoji: str):
        """Remove a reaction role mapping."""
        if message_id == None:
            await ctx.send("❌ No message ID has been specified!")
            return
        if emoji == None:
            await ctx.send("❌ No emoji has been specified!")
            return
        utils.remove_guild_role_reaction(ctx.guild.id, message_id, emoji)
        await ctx.send(f"✅ Removed reaction role for {emoji} on message {message_id}")

    @commands.command(name="lookup")
    async def lookup(self, ctx, input_value: str):
        """Look up a user by their ID or username."""
        if input_value == None:
            await ctx.send("❌ No input value has been specified!")
            return
        # Check if the input is a user ID
        if input_value.isdigit():
            user = await self.bot.fetch_user(int(input_value))
            if user:
                await ctx.send(
                    f"🔍 User ID `{input_value}` belongs to: **{user.name}#{user.discriminator}**"
                )
            else:
                await ctx.send(f"❌ No user found with ID `{input_value}`.")
        else:
            # Check if the input is a mention or username
            user = discord.utils.get(
                ctx.guild.members, name=input_value
            ) or discord.utils.get(ctx.guild.members, mention=input_value)
            if user:
                await ctx.send(
                    f"🔍 User `{user.name}#{user.discriminator}` has the ID: **{user.id}**"
                )
            else:
                await ctx.send(
                    f"❌ No user found with the name or mention `{input_value}`."
                )

    @commands.command(name="togglelevelroles")
    @utils.admin_or_owner()
    async def toggle_level_roles(self, ctx):
        """Toggle the level role system on or off for this server."""
        current_status = utils.is_level_role_system_enabled(ctx.guild.id)
        new_status = not current_status
        utils.set_guild_setting(ctx.guild.id, 'level_role_system_enabled', new_status)
        status_text = "enabled" if new_status else "disabled"
        await ctx.send(f"✅ Level role system has been **{status_text}** for this server.")

    @commands.command(name="setlevelrole")
    @utils.admin_or_owner()
    async def set_level_role(self, ctx, level: int, role: discord.Role, color: str = None):
        """
        Set a custom role for a specific level (per server) with an optional color.
        Color can be a hex code (e.g., #FF00FF).
        """
        if level is None:
            await ctx.send("❌ No level has been specified!")
            return
        if role is None:
            await ctx.send("❌ No role has been specified!")
            return

        role_color_hex = None
        if color:
            # Validate hex color
            color = color.lstrip('#')
            if len(color) == 6 and all(c in '0123456789abcdefABCDEF' for c in color):
                role_color_hex = color
            else:
                await ctx.send("❌ Invalid color format. Please use a 6-digit hex code (e.g., `#FF00FF`).")
                return

        utils.set_guild_level_role(ctx.guild.id, level, role.name, role_color_hex)
        await ctx.send(f"✅ Level {level} will now grant the role: **{role.name}**{' with color ' + color if color else ''}.")

    @commands.command(name="removelevelrole")
    @utils.admin_or_owner()
    async def remove_level_role(self, ctx, level: int):
        """Remove the custom role for a specific level (per server)."""
        if level is None:
            await ctx.send("❌ No level has been specified!")
            return
        utils.remove_guild_level_role(ctx.guild.id, level)
        await ctx.send(f"✅ Removed custom role for level {level}.")

    @commands.command(name="listlevelroles")
    @utils.admin_or_owner()
    async def list_level_roles(self, ctx):
        """List all custom level-role mappings for this server."""
        level_roles = utils.get_guild_level_roles(ctx.guild.id)
        if not level_roles:
            await ctx.send("No custom level-role mappings set for this server.")
        else:
            msg = "Custom level-role mappings:\n"
            for lvl, role_data in level_roles.items():
                role_name = role_data['name']
                role_color = role_data.get('color', 'Default/Random')
                msg += f"**Level {lvl}**: {role_name} (Color: #{role_color})\n"
            await ctx.send(msg)

    @commands.command(name="addselfrole")
    @utils.admin_or_owner()
    async def add_selfrole(self, ctx, *, role: discord.Role):
        """Add a role to the list of self-assignable roles."""
        if role == None:
            await ctx.send("❌ No role has been specified!")
            return
        utils.add_guild_self_role(ctx.guild.id, role.name)
        await ctx.send(f"✅ `{role.name}` is now self-assignable.")

    @commands.command(name="removeselfrole")
    @utils.admin_or_owner()
    async def remove_selfrole(self, ctx, *, role: discord.Role):
        """Remove a role from the list of self-assignable roles."""
        if role == None:
            await ctx.send("❌ No role has been specified!")
            return
        utils.remove_guild_self_role(ctx.guild.id, role.name)
        await ctx.send(f"✅ `{role.name}` is no longer self-assignable.")

    @commands.command(name="selfroles")
    async def list_selfroles(self, ctx):
        """List all self-assignable roles."""
        roles = utils.get_guild_self_roles(ctx.guild.id)
        if not roles:
            await ctx.send("No self-assignable roles set for this server.")
        else:
            await ctx.send("Self-assignable roles:\n" + "\n".join(f"- {r}" for r in roles))

    @commands.command(name="iam")
    async def iam(self, ctx, *, role: discord.Role):
        """Assign yourself a self-assignable role."""
        if role == None:
            await ctx.send("❌ No role has been specified!")
            return
        roles = utils.get_guild_self_roles(ctx.guild.id)
        if role.name not in roles:
            await ctx.send("❌ That role is not self-assignable.")
            return
        if role in ctx.author.roles:
            await ctx.send("You already have that role.")
            return
        await ctx.author.add_roles(role)
        await ctx.send(f"✅ You have been given the `{role.name}` role.")

    @commands.command(name="iamnot")
    async def iamnot(self, ctx, *, role: discord.Role):
        """Remove a self-assignable role from yourself."""
        if role == None:
            await ctx.send("❌ No role has been specified!")
            return
        roles = utils.get_guild_self_roles(ctx.guild.id)
        if role.name not in roles:
            await ctx.send("❌ That role is not self-assignable.")
            return
        if role not in ctx.author.roles:
            await ctx.send("You don't have that role.")
            return
        await ctx.author.remove_roles(role)
        await ctx.send(f"✅ `{role.name}` role removed from you.")
        
    @commands.command(name="servercustom")
    @utils.admin_or_owner()
    async def server_customization(self, ctx):
        """Show all customizations for this server."""
        guild_id = ctx.guild.id
        prefix = utils.get_guild_prefix(guild_id)
        welcome = utils.get_guild_welcome_message(guild_id) or "Not set"
        goodbye = utils.get_guild_goodbye_message(guild_id) or "Not set"
        level_roles = utils.get_guild_level_roles(guild_id)
        self_roles = utils.get_guild_self_roles(guild_id)
        role_reactions = utils.get_guild_role_reactions(guild_id)

        embed = discord.Embed(
            title=f"Server Customizations for {ctx.guild.name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Prefix", value=f"`{prefix}`", inline=False)
        embed.add_field(name="Welcome Message", value=welcome, inline=False)
        embed.add_field(name="Goodbye Message", value=goodbye, inline=False)
        embed.add_field(
            name="Level Roles",
            value="\n".join(f"Level {lvl}: {role}" for lvl, role in level_roles.items()) or "None",
            inline=False
        )
        embed.add_field(
            name="Self-Assignable Roles",
            value="\n".join(self_roles) or "None",
            inline=False
        )
        if role_reactions:
            rr_lines = []
            for msg_id, mapping in role_reactions.items():
                for emoji, role_id in mapping.items():
                    rr_lines.append(f"Msg {msg_id}: {emoji} → <@&{role_id}>")
            embed.add_field(
                name="Role Reactions",
                value="\n".join(rr_lines) or "None",
                inline=False
            )
        else:
            embed.add_field(name="Role Reactions", value="None", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="addtag")
    @utils.admin_or_owner()
    async def add_tag(self, ctx, tag: str, *, content: str):
        """Add a custom tag for this server."""
        if tag == None:
            await ctx.send("❌ No tag has been specified!")
            return
        if content == None:
            await ctx.send("❌ No content for the tag has been specified!")
            return
        utils.set_guild_tag(ctx.guild.id, tag, content)
        await ctx.send(f"✅ Tag `{tag}` added.")

    @commands.command(name="removetag")
    @utils.admin_or_owner()
    async def remove_tag(self, ctx, tag: str):
        """Remove a custom tag from this server."""
        if tag == None:
            await ctx.send("❌ No tag has been specified!")
            return
        utils.remove_guild_tag(ctx.guild.id, tag)
        await ctx.send(f"✅ Tag `{tag}` removed.")

    @commands.command(name="tags")
    async def list_tags(self, ctx):
        """List all tags for this server."""
        tags = utils.get_guild_tags(ctx.guild.id)
        if not tags:
            await ctx.send("No tags set for this server.")
        else:
            await ctx.send("Tags:\n" + "\n".join(f"- {name}" for name in tags.keys()))

    @commands.command(name="tag")
    async def get_tag(self, ctx, tag: str):
        """Show the content of a tag."""
        if tag == None:
            await ctx.send("❌ No tag has been specified!")
            return
        tags = utils.get_guild_tags(ctx.guild.id)
        content = tags.get(tag.lower())
        if content:
            await ctx.send(content)
        else:
            await ctx.send("❌ Tag not found.")
    
    @commands.command(name="addachievement")
    @utils.admin_or_owner()
    async def add_achievement(self, ctx, ach_id: str, name: str, power: int, asset_url: str, *, description: str):
        """Add a custom achievement (ID, name, power, asset_url, description)."""
        if ach_id == None:
            await ctx.send("❌ No achievement ID has been specified!")
            return
        if name == None:
            await ctx.send("❌ No name for the ID has been specified!")
            return
        if power == None:
            await ctx.send("❌ No power has been specified!")
            return
        if asset_url == None:
            await ctx.send("❌ No asset_url (pfp) has been specified!")
            return
        if description == None:
            await ctx.send("❌ No description of this achievement has been specified!")
            return
        utils.set_guild_achievement(ctx.guild.id, ach_id, name, description, power, asset_url)
        await ctx.send(f"✅ Achievement `{name}` added with ID `{ach_id}`.")

    @commands.command(name="removeachievement")
    @utils.admin_or_owner()
    async def remove_achievement(self, ctx, ach_id: str):
        """Remove an achievement by ID."""
        if ach_id == None:
            await ctx.send("❌ No achievement ID has been specified!")
            return
        utils.remove_guild_achievement(ctx.guild.id, ach_id)
        await ctx.send(f"✅ Achievement `{ach_id}` removed.")

    @commands.command(name="achievements")
    async def list_achievements(self, ctx, member: typing.Optional[discord.Member] = None):
        """Show your or another user's achievements."""
        if member == None:
            await ctx.send("❌ No member has been specified!")
            return
        member = member or ctx.author
        user_ach_ids = utils.get_user_achievements(member.id)
        achievements = utils.get_guild_achievements(ctx.guild.id)
        if not achievements:
            await ctx.send("No achievements set for this server.")
            return
        embed = discord.Embed(
            title=f"{member.display_name}'s Achievements",
            color=discord.Color.gold()
        )
        for ach_id, ach in achievements.items():
            owned = "✅" if ach_id in user_ach_ids else "❌"
            desc = f"{ach['description']}\nPower: {ach['power']}"
            if ach.get("asset_url"):
                embed.set_thumbnail(url=ach["asset_url"])
            embed.add_field(
                name=f"{owned} {ach['name']} (ID: {ach_id})",
                value=desc,
                inline=False
            )
        await ctx.send(embed=embed)
    
    @commands.group(name="adminmsg", invoke_without_command=True)
    @utils.admin_or_owner()
    async def adminmsg(self, ctx):
        """Admin message scheduler. Use subcommands: set, send, list, remove."""
        await ctx.send("Use `?adminmsg set <name> <message>`, `?adminmsg send <name>`, `?adminmsg list`, or `?adminmsg remove <name>`.")

    @adminmsg.command(name="set")
    @utils.admin_or_owner()
    async def adminmsg_set(self, ctx, name: str, *, message: str):
        """Set a scheduled message with a name."""
        data = utils.load_scheduled_messages()
        data[name] = message
        utils.save_scheduled_messages(data)
        await ctx.send(f"✅ Message '{name}' saved.")

    @adminmsg.command(name="send")
    @utils.admin_or_owner()
    async def adminmsg_send(self, ctx, name: str):
        """Send a scheduled message by name."""
        data = utils.load_scheduled_messages()
        msg = data.get(name)
        if not msg:
            await ctx.send(f"❌ No message found with name '{name}'.")
            return
        await ctx.send(msg)

    @adminmsg.command(name="list")
    @utils.admin_or_owner()
    async def adminmsg_list(self, ctx):
        """List all scheduled message names."""
        data = utils.load_scheduled_messages()
        if not data:
            await ctx.send("No scheduled messages found.")
            return
        await ctx.send("Scheduled messages: " + ", ".join(data.keys()))

    @adminmsg.command(name="remove")
    @utils.admin_or_owner()
    async def adminmsg_remove(self, ctx, name: str):
        """Remove a scheduled message by name."""
        data = utils.load_scheduled_messages()
        if name in data:
            del data[name]
            utils.save_scheduled_messages(data)
            await ctx.send(f"✅ Message '{name}' removed.")
        else:
            await ctx.send(f"❌ No message found with name '{name}'.")


async def setup(bot):
    await bot.add_cog(Utility(bot))