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

# --------------------- UTILITY COMMANDS --------------------
print("✅ - Utility loaded.")
class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="choose_region")
    @commands.has_permissions(administrator=True)
    async def choose_region(self, ctx):
        """Allow users to choose a region by reacting to emojis."""
        message = await ctx.send(
            "Choose your region by reacting with the corresponding emoji:\n"
            "🌍 for Africa\n"
            "🌎 for Americas\n"
            "🌏 for Asia\n"
            "🇪🇺 for Europe\n"
            "🇦🇺 for Oceania"
        )
        reactions = ["🌍", "🌎", "🌏", "🇪🇺", "🇦🇺"]
        for reaction in reactions:
            await message.add_reaction(reaction)

        # Save the message ID for tracking reactions
        data = utils.load_user_data()
        data["region_message_id"] = message.id
        utils.save_user_data(data)

    @commands.command(name="rules-verify")
    @commands.has_permissions(administrator=True)
    async def rules_verify(self, ctx):
        """Send a rules verification message and assign the role '.・🍨︴Member ✰' when reacted to."""
        try:
            # Create the embed for the rules verification message
            embed = discord.Embed(
                title="Rules Verification",
                description=(
                    "Please read the rules before verifying yourself again!:\n\n"
                    "React with 🔵 to verify that you agree to the rules and gain access to the server."
                ),
                color=discord.Color.blue(),
            )
            embed.set_thumbnail(
                url="https://cdn-icons-png.flaticon.com/512/1828/1828640.png"
            )  # Blue checkmark icon

            # Send the embed message
            message = await ctx.send(embed=embed)

            # Add the 🔵 reaction to the message
            await message.add_reaction("🔵")

            # Save the message ID in the user_data.json file
            data = utils.load_user_data()
            data["rules_verify_message_id"] = message.id
            utils.save_user_data(data)

            logging.info(
                f"Rules verification message sent in {ctx.channel.name} (ID: {ctx.channel.id}). Message ID: {message.id}"
            )
            await ctx.send("✅ Rules verification message sent successfully!")
        except Exception as e:
            logging.error(f"Error in rules_verify command: {e}")
            await ctx.send(f"❌ An error occurred while setting up rules verification: {e}")
    
    @commands.command(name="search_img")
    async def search_img(self, ctx, *, query: str):
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
            await ctx.send("No results found.")
    
    @commands.command(name="checkvc")
    async def checkvc(self, ctx):
        vc_channel = utils.get_truth_or_dare_vc(ctx.guild)
        if not vc_channel:
            await ctx.send("Truth or Dare voice channel not found!")
            return

        members_in_vc = [member for member in vc_channel.members if not member.bot]
        if members_in_vc:
            await ctx.send(
                f"Members in the Truth or Dare voice channel: {', '.join(member.mention for member in members_in_vc)}"
            )
        else:
            await ctx.send("No members in the Truth or Dare voice channel.")
    
    @commands.command()
    @commands.check(utils.is_owner)  # Ensure the user has the required permissions
    async def createrole(self, ctx, name: str, power: str, color: str):
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
            await ctx.send("❌ Invalid power level. Use `member`, `mod`, or `admin`.")
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
                "❌ Invalid color. Please provide a valid hex color (e.g., `#FF5733`)."
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
            await ctx.send("❌ I do not have permission to create roles.")
        except Exception as e:
            print(
                f"Create role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: {e}"
            )
            await ctx.send(f"❌ An error occurred: {e}")
            
    @commands.command()
    @commands.check(utils.is_owner)  # Ensure the user has the required permissions
    async def giverole(self, ctx, role_name: str, member: discord.Member):
        """Assign a role to a specified user."""
        # Find the role in the server
        role = discord.utils.find(lambda r: r.name == role_name, ctx.guild.roles)

        if role is None:
            print(
                f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Role not found."
            )
            await ctx.send(f"❌ Role **{role_name}** not found in this server.")
            return

        # Check if the bot has permission to assign this role
        if ctx.guild.me.top_role <= role:
            print(
                f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Insufficient permissions."
            )
            await ctx.send(
                "❌ I cannot assign this role because it is higher or equal to my highest role."
            )
            return

        # Assign the role
        try:
            await member.add_roles(role, reason=f"Role assigned by {ctx.author}")
            print(
                f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: success."
            )
            await ctx.send(
                f"✅ Role **{role.name}** assigned to {member.mention} successfully!"
            )
            if role in member.roles:
                print(
                    f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Role already assigned."
                )
                await ctx.send(
                    f":grey_question: {member.mention} already has the **{role.name}** role."
                )
            return
        except discord.Forbidden:
            print(
                f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: Forbidden."
            )
            await ctx.send("❌ I do not have permission to assign this role.")
        except Exception as e:
            print(
                f"Give role command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: {e}"
            )
            await ctx.send(f"❌ An error occurred: {e}")

    @commands.command()
    @commands.check(utils.is_owner)
    async def removerole(self, ctx, role: discord.Role, member: discord.Member):
        if role in member.roles:
            await member.remove_roles(role)
            await ctx.send(f"✅ Removed role **{role.name}** from {member.mention}.")
        else:
            await ctx.send(f"❌ {member.mention} does not have the role **{role.name}**.")
    
    @commands.command(name="colorrole")
    async def colorrole(self, ctx):
        """Allow users to choose a color role by reacting to emojis."""
        message = await ctx.send(
            "Which color do you want?\n"
            "React with:\n"
            "🔴 for Red\n"
            "🟠 for Orange\n"
            "🟡 for Yellow\n"
            "🟢 for Green\n"
            "🔵 for Blue\n"
            "🟣 for Violet\n"
                "⚪ for White\n"
            "⚫ for Black"
    )
        reactions = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "⚪", "⚫"]
        for reaction in reactions:
            await message.add_reaction(reaction)

        # Save the message ID for tracking reactions
        data = utils.load_user_data()
        data["colorrole_message_id"] = message.id
        utils.save_user_data(data)
    
    @commands.command(name="reminder")
    async def remindme(self, ctx, time: int, *, reminder: str):
        """Set a reminder."""
        await ctx.send(f"⏰ I will remind you in {time} seconds: {reminder}")
        await asyncio.sleep(time)
        await ctx.send(f"🔔 {ctx.author.mention}, here is your reminder: {reminder}")


    @commands.command(name="mute")
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, *, reason=None):
        """Mute a user."""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False)
        await member.add_roles(mute_role, reason=reason)
        await ctx.send(f"✅ {member.mention} has been muted. Reason: {reason}")


    @commands.command(name="unmute")
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a user."""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if mute_role in member.roles:
            await member.remove_roles(mute_role)
            await ctx.send(f"✅ {member.mention} has been unmuted.")
        else:
            await ctx.send(f"❌ {member.mention} is not muted.")


    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Delete a number of messages."""
        await ctx.channel.purge(limit=amount)
        await ctx.send(f"✅ Deleted {amount} messages.", delete_after=5)
    
    @commands.command(name="setwelcome")
    @commands.has_permissions(administrator=True)
    async def setwelcome(self, ctx, *, message: str):
        """Set a custom welcome message."""
        variables.welcome_messages[str(ctx.guild.id)] = message
        await ctx.send("✅ Welcome message set!")


    @commands.command(name="afk")
    async def afk(self, ctx, *, reason="AFK"):
        """Set yourself as AFK."""
        variables.afk_users[ctx.author.id] = reason
        await ctx.send(f"✅ {ctx.author.mention} is now AFK: {reason}")

    @commands.command(name="color")
    async def color(self, ctx, *, color_input: str):
        """Display the exact color based on a name or hex code."""
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
                    await ctx.send("❌ Invalid color name or hex code. Please try again.")
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
                "❌ Invalid color input. Please provide a valid color name or hex code (e.g., `red` or `#FF0000`)."
            )
        
    @commands.command(name="upload")
    async def upload(self, ctx, *, url: str = None):
        """Allow users to upload .mp3 files or provide a URL to download."""
        # Check if the music folder has more than 50 files
        oldest_file = utils.check_music_folder()
        if oldest_file:
            await ctx.send(
                f"⚠️ The music folder has more than 50 songs. Continuing will delete the oldest file: `{os.path.basename(oldest_file)}`. Do you want to proceed? (yes/no)"
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
                    await ctx.send("❌ Operation canceled.")
                    return
                else:
                    os.remove(oldest_file)  # Delete the oldest file
                    await ctx.send(
                        f"🗑️ Deleted the oldest file: `{os.path.basename(oldest_file)}`."
                    )
            except asyncio.TimeoutError:
                await ctx.send("⏰ You took too long to respond. Operation canceled.")
                return

        # Proceed with the upload logic
        if not ctx.message.attachments and not url:
            await ctx.send("❌ Please attach an audio file or provide a URL to upload.")
            return

        # Handle file attachments
        if ctx.message.attachments:
            for attachment in ctx.message.attachments:
                if attachment.filename.endswith((".mp3", ".wav", ".ogg")):
                    file_path = os.path.join("music", attachment.filename)
                    await attachment.save(file_path)
                    await ctx.send(
                        f"✅ File `{attachment.filename}` has been uploaded and saved."
                    )
                else:
                    await ctx.send(
                        f"❌ `{attachment.filename}` is not a supported audio format. Please upload .mp3, .wav, or .ogg files."
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
                                f"✅ Downloaded `{info['title']}` and saved to the music folder."
                            )
                        else:
                            await ctx.send("❌ Failed to retrieve video information after download.")
                except Exception as e:
                    await ctx.send(f"❌ Failed to download from URL: {e}")
            else:
                await ctx.send(
                    "❌ Invalid URL. Please provide a valid URL starting with `http://` or `https://`."
                )


    @commands.command(name="play")
    async def play(self, ctx, *, query: str = None):
        """Play a song from a URL, the music folder, or by its number, with an optional loop count."""
        # Check if the music folder has more than 50 files
        oldest_file = utils.check_music_folder()
        if oldest_file:
            await ctx.send(
                f"⚠️ The music folder has more than 50 songs. Continuing will delete the oldest file: `{os.path.basename(oldest_file)}`. Do you want to proceed? (yes/no)"
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
                    await ctx.send("❌ Operation canceled.")
                    return
                else:
                    os.remove(oldest_file)  # Delete the oldest file
                    await ctx.send(
                        f"🗑️ Deleted the oldest file: `{os.path.basename(oldest_file)}`."
                    )
            except asyncio.TimeoutError:
                await ctx.send("⏰ You took too long to respond. Operation canceled.")
                return

        # Proceed with the play logic
        if not ctx.author.voice:
            await ctx.send("❌ You must be in a voice channel to use this command.")
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
                    await ctx.send("❌ Loop count must be at least 1.")
                    return

                # Determine the song path
                if song_query.isdigit():
                    # Play the song by its number
                    songs = sorted(os.listdir("music"))
                    song_index = int(song_query) - 1  # Convert to zero-based index
                    if 0 <= song_index < len(songs):
                        song_path = os.path.join("music", songs[song_index])
                        await ctx.send(
                            f"🎵 Now playing: `{songs[song_index]}` (Looping {loop_count} times)"
                        )
                    else:
                        await ctx.send(
                            f"❌ Invalid song number. Please use a number between 1 and {len(songs)}."
                        )
                        return
                elif song_query.startswith("http://") or song_query.startswith("https://"):
                    # Play a song from a URL
                    await ctx.send(f"🔍 Searching for `{song_query}`...")
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
                                f"✅ Downloaded `{info['title']}`. Now playing (Looping {loop_count} times)..."
                            )
                        else:
                            await ctx.send(
                                "❌ Failed to retrieve video information after download."
                            )
                else:
                    # Play a song by its name
                    song_path = os.path.join("music", song_query)
                    if not os.path.exists(song_path):
                        await ctx.send(
                            f"❌ The file `{song_query}` does not exist in the music folder."
                        )
                        return
                    await ctx.send(
                        f"🎵 Now playing: `{song_query}` (Looping {loop_count} times)"
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
                        "❌ The music folder is empty. Upload some songs using `?upload` or provide a URL."
                    )
                    return
                song = songs[0]
                song_path = os.path.join("music", song)
                loop_count = 1
                await ctx.send(f"🎵 Now playing: `{song}` (Looping {loop_count} times)")

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
            await ctx.send(f"❌ An error occurred: {e}")


    @commands.command(name="queue")
    async def queue(self, ctx):
        """List all songs in the music folder."""
        songs = sorted(os.listdir("music"))
        if not songs:
            await ctx.send(
                "❌ The music folder is empty. Upload some songs using `?upload`."
            )
            return

        song_list = "\n".join(f"{i + 1}. {song}" for i, song in enumerate(songs))
        await ctx.send(f"🎶 **Music Queue:**\n{song_list}")


    @commands.command(name="skip")
    async def skip(self, ctx):
        """Skip the currently playing song."""
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await ctx.send("❌ No song is currently playing.")
            return

        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped the current song.")


    @commands.command(name="stop")
    async def stop(self, ctx):
        """Stop the music and disconnect the bot."""
        if not ctx.voice_client:
            await ctx.send("❌ The bot is not connected to a voice channel.")
            return

        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Stopped the music and disconnected.")


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
                    "❌ FFmpeg is not accessible. Please check your installation."
                )
                variables.logger.error(f"FFmpeg error: {result.stderr}")
        except FileNotFoundError:
            await ctx.send("❌ FFmpeg is not installed or not in PATH.")
            variables.logger.error("FFmpeg executable not found.")


    @commands.command(name="download")
    async def download(self, ctx, url: str):
        """Download a YouTube song or video and save it to the music folder."""
        if not (url.startswith("http://") or url.startswith("https://")):
            await ctx.send(
                "❌ Invalid URL. Please provide a valid YouTube URL starting with `http://` or `https://`."
            )
            return

        await ctx.send(f"🔍 Downloading from URL: `{url}`...")
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
                        f"✅ Downloaded `{info['title']}` and saved to the music folder as `{file_name}`."
                    )
                else:
                    await ctx.send("❌ Failed to retrieve video information after download.")
        except Exception as e:
            await ctx.send(f"❌ Failed to download from URL: {e}")
    
    @commands.command(name="ask")
    async def ask(self, ctx, *, question: str):
        """Answer a question using a local AI model."""
        try:
            # Generate a response using the Hugging Face model
            response_gen = variables.qa_pipeline(question, max_length=100, num_return_sequences=1)
            if response_gen is None:
                await ctx.send("❌ No answer could be generated.")
                return
            if hasattr(response_gen, "__iter__") and not isinstance(response_gen, (str, bytes, dict)):
                response = list(response_gen)
            else:
                response = [response_gen]
            if response and isinstance(response[0], dict) and "generated_text" in response[0]:
                answer = response[0]["generated_text"]
                await ctx.send(answer)
            else:
                await ctx.send("❌ No answer could be generated.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
        
    @commands.command(name="translate")
    async def translate(self, ctx, target_language: str, *, text: str):
        """Translate text to a specified language."""
        try:
            translation = await variables.translator.translate(text, dest=target_language)
            await ctx.send(f"🌐 **Translation ({target_language}):** {translation.text}")
        except Exception as e:
            await ctx.send(f"❌ Failed to translate: {e}")
        
    @commands.command(name="weather")
    async def weather(self, ctx, *, city: str):
        """Get the current weather for a city."""
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
    
    @commands.command(name="verify")
    @commands.has_permissions(administrator=True)
    async def verify(self, ctx):
        """Send a verification message and assign the role '.・🍨︴Member ✰' when reacted to."""
        try:
            # Create the embed for the verification message
            embed = discord.Embed(
                title="Verification",
                description="React with ✅ to verify yourself and gain access to the server!",
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
    async def leaderboard(self, ctx, category: str = None):
        """Display the leaderboard for level, XP, coins, or Easter Eggs."""
        valid_categories = ["level", "xp", "coins", "eggs"]
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
    @commands.has_permissions(administrator=True)
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
    async def announcement(self, ctx, channel_name: str = None, *, message: str):
        """
        Send an announcement to all servers' announcement channels.
        If a specific channel name is provided, send the message to that channel instead.
        """
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


    @commands.command(name="lookup")
    async def lookup(self, ctx, input_value: str):
        """Look up a user by their ID or username."""
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

async def setup(bot):
    await bot.add_cog(Utility(bot))