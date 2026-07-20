import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import math
import re
import json
from typing import Optional

from Ediscord import logger, EmbedBuilder


URL_REGEX = re.compile(r"https?://(?:www\.)?.+")


class MusicQueue:
    def __init__(self):
        self.queue = []
        self.current = None
        self.loop = False
        self.volume = 0.5

    def add(self, item: dict):
        self.queue.append(item)

    def next(self):
        if self.queue:
            self.current = self.queue.pop(0)
            return self.current
        self.current = None
        return None

    def clear(self):
        self.queue.clear()
        self.current = None

    def remove(self, index: int):
        if 0 <= index < len(self.queue):
            return self.queue.pop(index)
        return None

    def shuffle(self):
        import random
        random.shuffle(self.queue)

    def total_length(self):
        return sum(item.get("duration", 0) for item in self.queue)

    def __len__(self):
        return len(self.queue)


class MusicPlayer(discord.ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=None)
        self.cog = cog
        self.ctx = ctx

    @discord.ui.button(label="⏸", style=discord.ButtonStyle.secondary)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("Not connected.", ephemeral=True)
        if interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            button.label = "⏸"
        elif interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            button.label = "▶"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="⏹", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, voice_client: discord.VoiceProtocol):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("Not connected.", ephemeral=True)
        q = self.cog.queues.get(interaction.guild_id)
        if q:
            q.clear()
        interaction.guild.voice_client.stop()
        await interaction.guild.voice_client.disconnect()
        embed = EmbedBuilder().description("Stopped and disconnected.").color("red").build()
        await interaction.response.send_message(embed=embed)
        self.stop()

    @discord.ui.button(label="⏭", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("Not connected.", ephemeral=True)
        interaction.guild.voice_client.stop()
        await self.cog.play_next(interaction.guild)
        await interaction.response.defer()

    @discord.ui.button(label="🔀", style=discord.ButtonStyle.secondary)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        q = self.cog.queues.get(interaction.guild_id)
        if q:
            q.shuffle()
            await interaction.response.send_message("Queue shuffled!", ephemeral=True)
        else:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)


class Music(commands.Cog, name="Music"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queues = {}
        self.voice_states = {}

    def get_queue(self, guild_id: int) -> MusicQueue:
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue()
        return self.queues[guild_id]

    async def play_next(self, guild: discord.Guild):
        q = self.queues.get(guild.id)
        if not q:
            return
        item = q.next()
        if not item:
            return
        q.current = item
        voice = guild.voice_client
        if not voice:
            return

        source = await discord.FFmpegOpusAudio.from_probe(item["url"], **{'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'})
        def after(error):
            coro = self.play_next(guild)
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except:
                pass
        voice.play(source, after=after)
        voice.source = discord.PCMVolumeTransformer(voice.source)
        voice.source.volume = q.volume

    async def ensure_voice(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("You must be in a voice channel.", ephemeral=True)
            return False
        voice = interaction.guild.voice_client
        if voice and voice.channel.id != interaction.user.voice.channel.id:
            await interaction.response.send_message("I'm already in another voice channel.", ephemeral=True)
            return False
        return True

    music_group = app_commands.Group(name="music", description="Music playback commands")

    @music_group.command(name="play", description="Play a song from a URL or search query")
    @app_commands.describe(query="Song URL or search term")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        if not await self.ensure_voice(interaction):
            return

        voice = interaction.guild.voice_client
        if not voice:
            voice = await interaction.user.voice.channel.connect()

        q = self.get_queue(interaction.guild_id)
        item = {"url": query, "title": query[:100], "duration": 0, "requester": interaction.user.name}

        if not voice.is_playing():
            q.add(item)
            await self.play_next(interaction.guild)
            embed = EmbedBuilder().title("Now Playing").description(query[:200]).color("green").field("Requested by", interaction.user.mention).build()
        else:
            q.add(item)
            embed = EmbedBuilder().title("Added to Queue").description(query[:200]).color("blue").field("Position", len(q)).build()

        view = MusicPlayer(self, interaction)
        await interaction.followup.send(embed=embed, view=view)

    @music_group.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if not voice or not voice.is_playing():
            return await interaction.response.send_message("Nothing is playing.", ephemeral=True)
        voice.stop()
        embed = EmbedBuilder().description("Skipped.").color("blue").build()
        await interaction.response.send_message(embed=embed)

    @music_group.command(name="stop", description="Stop playback and clear the queue")
    async def stop_music(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if not voice:
            return await interaction.response.send_message("Not connected.", ephemeral=True)
        q = self.queues.get(interaction.guild_id)
        if q:
            q.clear()
        voice.stop()
        await voice.disconnect()
        embed = EmbedBuilder().description("Stopped and disconnected.").color("red").build()
        await interaction.response.send_message(embed=embed)

    @music_group.command(name="queue", description="Show the current music queue")
    async def show_queue(self, interaction: discord.Interaction):
        q = self.queues.get(interaction.guild_id)
        if not q or not q.queue:
            return await interaction.response.send_message("Queue is empty.", ephemeral=True)
        lines = [f"**Now Playing:** {q.current.get('title', 'Unknown') if q.current else 'Nothing'}" if q.current else "", "**Up Next:**"]
        for i, item in enumerate(q.queue[:10], 1):
            duration = item.get("duration", 0)
            dur_str = f"{duration // 60}:{duration % 60:02d}" if duration else ""
            lines.append(f"`{i}.` {item.get('title', 'Unknown')} [{dur_str}]")
        embed = EmbedBuilder().title("Music Queue").description("\n".join(lines)).color("blue").field("Total Songs", len(q)).build()
        await interaction.response.send_message(embed=embed)

    @music_group.command(name="volume", description="Set the player volume")
    @app_commands.describe(level="Volume level (0-100)")
    async def volume(self, interaction: discord.Interaction, level: int):
        if level < 0 or level > 100:
            return await interaction.response.send_message("Volume must be between 0 and 100.", ephemeral=True)
        voice = interaction.guild.voice_client
        if not voice or not voice.source:
            return await interaction.response.send_message("Nothing is playing.", ephemeral=True)
        voice.source.volume = level / 100
        q = self.queues.get(interaction.guild_id)
        if q:
            q.volume = level / 100
        await interaction.response.send_message(f"Volume set to {level}%.")

    @music_group.command(name="nowplaying", description="Show what's currently playing")
    async def nowplaying(self, interaction: discord.Interaction):
        q = self.queues.get(interaction.guild_id)
        if not q or not q.current:
            return await interaction.response.send_message("Nothing is playing.", ephemeral=True)
        embed = EmbedBuilder().title("Now Playing").description(q.current.get("title", "Unknown")).color("green").build()
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
