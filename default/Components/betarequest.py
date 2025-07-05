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
        if not getattr(variables, "beta_mode", False):
            await ctx.send("❌ Beta program is currently closed.")
            return

        # Only allow the server owner to use this command
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.send("❌ Only the server owner can request beta access.")
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
            await ctx.send(f"✅ Approved! {guild.name} is now in the beta program.")
        else:
            await ctx.send("❌ Beta request denied by the bot owner.")

    @commands.command(name="betastatus")
    async def betastatus(self, ctx):
        """Check if this server is in the beta program."""
        servers = utils.load_beta_servers()
        if ctx.guild.id in servers:
            await ctx.send("✅ This server is in the beta program!")
        else:
            await ctx.send("❌ This server is not in the beta program.")

    @commands.command(name="betaremove")
    @commands.is_owner()
    async def betaremove(self, ctx, guild_id: int):
        """Remove a server from the beta program (owner only)."""
        servers = utils.load_beta_servers()
        if guild_id in servers:
            servers.remove(guild_id)
            utils.save_beta_servers(servers)
            await ctx.send(f"Removed server {guild_id} from the beta program.")
        else:
            await ctx.send("Server not found in the beta program.")

async def setup(bot):
    await bot.add_cog(Beta(bot))