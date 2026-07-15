import time
import random
import discord
from discord import app_commands
from discord.ext import commands

from Ediscord import variables, utils


class General(commands.Cog):
    """General-purpose commands for Prowl."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check Prowl's latency.")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="Pong!",
            description=f"Latency: **{latency}ms**",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="info", description="Show Prowl's info.")
    async def info(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Prowl",
            description="A silly little cat bot with a ton of abilities.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Servers", value=len(self.bot.guilds))
        embed.add_field(name="Users", value=len(self.bot.users))
        embed.add_field(name="Uptime", value=utils.get_uptime())
        embed.add_field(name="Cogs Loaded", value=len(self.bot.cogs))
        embed.set_footer(text=f"Prowl v{variables.__version__}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="say", description="Echo back your message.")
    @app_commands.describe(text="The text to echo back.")
    async def say(self, interaction: discord.Interaction, text: str):
        await interaction.response.send_message(text)

    @app_commands.command(name="serverinfo", description="Show server information.")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=guild.name, color=discord.Color.gold())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Channels", value=len(guild.channels))
        embed.add_field(name="Roles", value=len(guild.roles))
        embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"))
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(General(bot))
