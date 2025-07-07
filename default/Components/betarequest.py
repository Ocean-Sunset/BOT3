import discord
from discord.ext import commands
import json
import os
import asyncio
from Ediscord import variables, utils

class Beta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="betarequest")
    @commands.has_permissions(administrator=True)
    async def betarequest(self, ctx):
        """Request access to the beta program for this server (server owner only, and only if beta mode is enabled)."""
        # Check if beta mode is enabled
        if not getattr(variables, "beta_mode", True):
            await ctx.send("# ❌ Beta program is currently closed.\nPlease try again later.\n-# We're sorry for this but it appears the Beta Program is full or closed.")
            return

        # Only allow the server owner to use this command
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.send("# ❌ Only the server owner can request beta access.!")
            return

        app_info = await self.bot.application_info()
        owner = app_info.owner
        guild = ctx.guild

        # Ping the owner in the same channel
        approval_msg = await ctx.send(
            f"{owner.mention}, server **{guild.name}** (ID: {guild.id}) requests beta access.\n"
            f"React with ✅ to approve, ❌ to deny."
        )
        await approval_msg.add_reaction("✅")
        await approval_msg.add_reaction("❌")

        def check(reaction, user):
            return (
                user.id == owner.id
                and reaction.message.id == approval_msg.id
                and str(reaction.emoji) in ["✅", "❌"]
            )

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=120.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Beta request timed out. Please try again later.")
            return

        if str(reaction.emoji) == "✅":
            servers = utils.load_beta_servers()
            if guild.id not in servers:
                servers.append(guild.id)
                utils.save_beta_servers(servers)
            await ctx.send(f"# ✅ Approved!\n{guild.name} is now in the beta program.\n-# Please read the following message carefully.")
            await asyncio.sleep(1)
            await ctx.send(f"# Welcome to the beta program!\nYou have been chosen among **multiple servers** to test our **Beta Program!**\n\nPlease note that this program includes the following rules:\n- Do not spam send feedback\n- Do not show off your beta program,\n-# - if possible, create a channel where you, admins, and the bot can only speak and see.\n- Your use of this beta program can be revoked at any moment, please respect those rules.\n\n**That's all!!** Thanks for participating and we hope you enjoy!")
        else:
            await ctx.send("# ❌ Beta request denied by the bot owner.\nWe're sorry, but it appears your discord server does not meet the requirements to have a Beta Prorgam.")

    @commands.command(name="betastatus")
    async def betastatus(self, ctx):
        """Check if this server is in the beta program."""
        servers = utils.load_beta_servers()
        if ctx.guild.id in servers:
            await ctx.send("# ✅ This server is in the beta program!")
        else:
            await ctx.send("# ❌ This server is not in the beta program.\n-# Try running `?betarequest`!")

    @commands.command(name="betaremove")
    @commands.is_owner()
    async def betaremove(self, ctx, guild_id: int):
        """Remove a server from the beta program (owner only)."""
        servers = utils.load_beta_servers()
        if guild_id in servers:
            servers.remove(guild_id)
            utils.save_beta_servers(servers)
            await ctx.send(f"# ✅ Removed server {guild_id} from the beta program.\nYou will need permission from **the developper** to have it again.")
        else:
            await ctx.send("# ❌ Server not found in the beta program.\n-# Try running `?betarequest`!")

async def setup(bot):
    await bot.add_cog(Beta(bot))