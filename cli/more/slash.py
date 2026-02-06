import discord
from discord import app_commands
from discord.ext import commands

class Slash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ping",
        description="Ping the bot"
    )
    async def slash_ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("🏓 Pong (slash)!")
    

async def setup(bot):
    await bot.add_cog(Slash(bot))
