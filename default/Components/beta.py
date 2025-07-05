from discord.ext import commands
import discord
import os
import json
from Ediscord import variables, utils

class BetaCore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="beta")
    async def beta(self, ctx):
        """Show info about the beta program (only for approved servers)."""
        if not utils.is_beta_server(ctx.guild.id):
            await ctx.send("❌ This server is not in the beta program.")
            return

        await ctx.send(
            "✅ Welcome to the Beta Program!\n"
            "Use `?betastatus` to confirm you're in.\n"
            "Use `?betaremove <guild_id>` (bot owner only) to remove a server from beta."
        )

async def setup(bot):
    await bot.add_cog(BetaCore(bot))