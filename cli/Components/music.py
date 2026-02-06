import discord
import typing
import asyncio
from discord.ext import commands
from discord import FFmpegPCMAudio
from Ediscord import utils, variables
from yt_dlp import YoutubeDL
import time
import json
import os


from discord import app_commands

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="upload", description="Allow users to upload .mp3 files or provide a URL to download.")
    async def upload(self, interaction: discord.Interaction, url: typing.Optional[str] = None):
        # ...existing code for upload...
        await interaction.response.send_message("-# WARNING: The current music system doesn't work, we are working to fix this issue.")
        if url is None and not interaction.attachments:
            await interaction.followup.send(f"# ❌ No url or file has been specified and or sent!\n-# {utils.little_error_variant()}")
            return
        oldest_file = utils.check_music_folder()
        if oldest_file:
            await interaction.followup.send(
                f"# ⚠️ WARNING:\n The music folder has more than 50 songs. Continuing will delete the oldest file: `{os.path.basename(oldest_file)}`.\n-# {utils.little_unsure_variant()}"
            )
            os.remove(oldest_file)
            await interaction.followup.send(
                f"# 🗑️ Deleted the oldest file:\n`{os.path.basename(oldest_file)}`."
            )
        if interaction.attachments:
            for attachment in interaction.attachments:
                if attachment.filename.endswith((".mp3", ".wav", ".ogg")):
                    file_path = os.path.join("music", attachment.filename)
                    await attachment.save(file_path)
                    await interaction.followup.send(
                        f"# ✅ File `{attachment.filename}` has been uploaded and saved."
                    )
                else:
                    await interaction.followup.send(
                        f"# ❌ `{attachment.filename}` is not a supported audio format.\nPlease upload .mp3, .wav, or .ogg files.\n-# More support for custom sound files (.wma, .aiff, etc..) are coming soon!"
                    )
        if url:
            if url.startswith("http://") or url.startswith("https://"):
                await interaction.followup.send(f"🔍 Downloading from URL: `{url}`...")
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
                            await interaction.followup.send(
                                f"# ✅ Downloaded `{info['title']}`\nand saved to the music folder."
                            )
                        else:
                            await interaction.followup.send(f"# ❌ Failed to retrieve video information after download.\n{utils.little_error_variant()}")
                except Exception as e:
                    await interaction.followup.send(f"# ❌ Failed to download from URL:\n{e}")
            else:
                await interaction.followup.send(
                    "# ❌ Invalid URL.\nPlease provide a valid URL starting with `http://` or `https://`."
                )

    @app_commands.command(name="play", description="Play a song from a URL, the music folder, or by its number, with an optional loop count.")
    @app_commands.describe(query="Song name, number, or URL (optional)")
    async def play(self, interaction: discord.Interaction, query: typing.Optional[str] = None):
        # ...existing code for play...
        await interaction.response.send_message("-# WARNING: The current music system doesn't work, we are working to fix this issue.")
        if query == None:
            await interaction.followup.send("# ❌ No query (url or file) has been specified!\n-# If you want more info of our current soung file systems, run `/queue`!")
            return
        oldest_file = utils.check_music_folder()
        if oldest_file:
            await interaction.followup.send(
                f"# ⚠️ WARNING:\n The music folder has more than 50 songs. Continuing will delete the oldest file: `{os.path.basename(oldest_file)}`.\n-# {utils.little_unsure_variant()}"
            )
            # Skipping confirmation logic for slash command
            os.remove(oldest_file)
            await interaction.followup.send(
                f"# 🗑️ Deleted the oldest file:\n`{os.path.basename(oldest_file)}`."
            )
        user = interaction.user
        if not user.voice or not user.voice.channel:
            await interaction.followup.send("# ❌ You must be in a voice channel to use this command.!\n-# Don't have an *easy-to-access* channel? just ask a mod to help you!")
            return
        voice_channel = user.voice.channel
        try:
            if interaction.guild.voice_client is None:
                vc = await voice_channel.connect()
            else:
                vc = interaction.guild.voice_client
            if query:
                parts = query.split(" ")
                song_query = " ".join(parts[:-1]) if parts[-1].isdigit() else query
                loop_count = int(parts[-1]) if parts[-1].isdigit() else 1
                if loop_count < 1:
                    await interaction.followup.send("# ❌ Loop count must be at least 1.\n-# Ex. `/play <number>`")
                    return
                if song_query.isdigit():
                    songs = sorted(os.listdir("music"))
                    song_index = int(song_query) - 1
                    if 0 <= song_index < len(songs):
                        song_path = os.path.join("music", songs[song_index])
                        await interaction.followup.send(
                            f"# 🎵 Now playing: `{songs[song_index]}`\n-# (Looping {loop_count} times)\n-# That must be a cool song! right?.."
                        )
                    else:
                        await interaction.followup.send(
                            f"# ❌ Invalid song number.\nPlease use a number between 1 and {len(songs)}.\nIf you want more info on our current song file system, use `/queue`!"
                        )
                        return
                elif song_query.startswith("http://") or song_query.startswith("https://"):
                    await interaction.followup.send(f"# 🔍 Now downloading..\n`{song_query}`...")
                    ydl_opts = {
                        "format": "bestaudio/best",
                        "outtmpl": "music/%(title)s.%(ext)s",
                        "noplaylist": True,
                    }
                    with YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(song_query, download=True)
                        song_path = ydl.prepare_filename(info)
                        if info is not None and 'title' in info:
                            await interaction.followup.send(
                                f"-# ✅ Downloaded `{info['title']}`."
                            )
                            await interaction.followup.send(
                                f"# 🎵 Now playing: `{os.path.basename(song_path)}`\n-# (Looping {loop_count} times)\n-# That must be a cool song! right?.."
                            )
                        else:
                            await interaction.followup.send(
                                f"# ❌ Failed to retrieve video information after download.\n{utils.little_error_variant()}"
                            )
                else:
                    song_path = os.path.join("music", song_query)
                    if not os.path.exists(song_path):
                        await interaction.followup.send(
                            f"# ❌ The file `{song_query}` does not exist in the music folder.\nCheck the songs with `/queue` for more help!\n-# {utils.little_error_variant()}"
                        )
                        return
                    await interaction.followup.send(
                        f"# 🎵 Now playing: `{song_query}`\n-# (Looping {loop_count} times)\n-# That must be a cool song! right?.."
                    )
                current_status = discord.Game(f"Playing {os.path.basename(song_path)}")
                await self.bot.change_presence(
                    status=discord.Status.online, activity=current_status
                )
            else:
                songs = sorted(os.listdir("music"))
                if not songs:
                    await interaction.followup.send(
                        f"# ❌ The music folder is empty.\nUpload some songs using `/upload` or provide a URL.\n-# {utils.little_error_variant()}"
                    )
                    return
                song = songs[0]
                song_path = os.path.join("music", song)
                loop_count = 1
                await interaction.followup.send(f"# 🎵 Now playing: `{song}`\n-# (Looping {loop_count} times)\n-# That must be a cool song! right?..")
            for i in range(loop_count):
                vc.play(
                    discord.FFmpegPCMAudio(song_path, executable=variables.ffmpeg_path),
                    after=lambda e: variables.logger.info(f"Finished playing: {song_path}"),
                )
                while vc.is_playing():
                    await asyncio.sleep(1)
        except Exception as e:
            variables.logger.error(f"An error occurred in the play command: {e}")
            await interaction.followup.send(f"# ❌ An error occurred:\n{e}")

    @app_commands.command(name="queue", description="List all songs in the music folder.")
    async def queue(self, interaction: discord.Interaction):
        # ...existing code for queue...
        await interaction.response.send_message("-# WARNING: The current music system doesn't work, we are working to fix this issue.")
        songs = sorted(os.listdir("music"))
        if not songs:
            await interaction.followup.send(
                "# ❌ The music folder is empty.\nUpload some songs using `/upload`."
            )
            return
        song_list = "\n".join(f"{i + 1}. {song}" for i, song in enumerate(songs))
        await interaction.followup.send(f"# 🎶 **Music Queue:**\n{song_list}")

    @app_commands.command(name="skip", description="Skip the currently playing song.")
    async def skip(self, interaction: discord.Interaction):
        # ...existing code for skip...
        await interaction.response.send_message("-# WARNING: The current music system doesn't work, we are working to fix this issue.")
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            await interaction.followup.send("# ❌ No song is currently playing.\nPlay a song using `/play`")
            return
        vc.stop()
        await interaction.followup.send("# ⏭️ Skipped the current song.")

    @app_commands.command(name="stop", description="Stop the music and disconnect the bot.")
    async def stop(self, interaction: discord.Interaction):
        # ...existing code for stop...
        await interaction.response.send_message("-# WARNING: The current music system doesn't work, we are working to fix this issue.")
        vc = interaction.guild.voice_client
        if not vc:
            await interaction.followup.send("❌ The bot is not connected to a voice channel.")
            return
        await vc.disconnect()
        await interaction.followup.send("# ⏹️ Stopped the music and disconnected.\n-# If you ever wish to play a music again, just do `/play`!")

    @app_commands.command(name="check_ffmpeg", description="Check if FFmpeg is accessible.")
    async def check_ffmpeg(self, interaction: discord.Interaction):
        # ...existing code for check_ffmpeg...
        try:
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode == 0:
                await interaction.response.send_message(
                    f"✅ FFmpeg is installed and accessible:\n```\n{result.stdout.splitlines()[0]}\n```"
                )
                variables.logger.info(f"FFmpeg is accessible: {result.stdout.splitlines()[0]}")
            else:
                await interaction.response.send_message(
                    "# ❌ FFmpeg is not accessible.\nPlease check your installation."
                )
                variables.logger.error(f"FFmpeg error: {result.stderr}")
        except FileNotFoundError:
            await interaction.response.send_message("# ❌ FFmpeg is not installed or not in PATH.")
            variables.logger.error("FFmpeg executable not found.")

    @app_commands.command(name="download", description="Download a YouTube song or video and save it to the music folder.")
    @app_commands.describe(url="YouTube URL to download")
    async def download(self, interaction: discord.Interaction, url: str):
        # ...existing code for download...
        await interaction.response.send_message("-# WARNING: The current music system doesn't work, we are working to fix this issue.")
        if url == None:
            await interaction.followup.send("# ❌ No URL message has been specified!\n-# Do remember to use `https` or `http`!")
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            await interaction.followup.send(
                "# ❌ Invalid URL.\nPlease provide a valid YouTube URL starting with `http://` or `https://`."
            )
            return
        await interaction.followup.send(f"# 🔍 Downloading from URL:\n`{url}`...")
        ydl_opts = {
            "cookiefile": "youtube_cookies.txt",
            "format": "bestaudio/best",  # Download the best audio format
            "outtmpl": "music/%(title)s.%(ext)s",  # Save to the music folder with the title as the filename
            "noplaylist": True,  # Do not download playlists
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is not None and 'title' in info:
                    file_name = ydl.prepare_filename(info)
                    await interaction.followup.send(
                        f"# ✅ Downloaded `{info['title']}`\nand saved to the music folder as `{file_name}`."
                    )
                else:
                    await interaction.followup.send("# ❌ Failed to retrieve video information after download.")
        except Exception as e:
            await interaction.followup.send(f"# ❌ Failed to download from URL:\n{e}")

async def setup(bot):
    await bot.add_cog(Music(bot))