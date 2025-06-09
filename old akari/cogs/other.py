import discord
from discord.ext import commands

class ExampleCog(commands.Cog):
    """Example commands and events."""
    # basically add ur shit here

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        """Responds with pong."""
        await ctx.send("Pong!")

    @commands.command()
    async def say(self, ctx, *, message: str):
        """Repeats your message."""
        await ctx.send(message)
        
    # dont delete this pls
    @commands.Cog.listener()
    async def on_ready(self):
        print("ExampleCog is loaded and ready!")

def setup(bot):
    bot.add_cog(ExampleCog(bot))