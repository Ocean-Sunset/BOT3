import discord
from discord.ext import commands
import json
import os
import asyncio
from Ediscord import variables, utils

class insider(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="forceinsider")
    @commands.is_owner()
    async def forceinsider(self, ctx, ID = str):
        """Force a server to get insider wether they like it or not."""
        try:
            server = utils.load_insider_servers
            server.append(ID)
            utils.save_insider_servers(server)
            await ctx.send(f"# ✅ Force complete!\n{ID} is now an Insider Server.")
        except Exception as e:
            await ctx.send("# ❌ An error occured during forcing.")

    @commands.command(name="insiderrequest")
    @utils.admin_or_owner()
    async def insiderrequest(self, ctx):
        """Request access to the insider program for this server (server owner only, and only if insider mode is enabled)."""
        # Check if insider mode is enabled
        if not getattr(variables, "insider_mode", True):
            await ctx.send("# ❌ insider program is currently closed.\nPlease try again later.\n-# We're sorry for this but it appears the insider Program is full or closed.")
            return

        # Only allow the server owner to use this command
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.send("# ❌ Only the server owner can request insider access!")
            return
        
        app_info = await self.bot.application_info()
        owner = app_info.owner
        guild = ctx.guild

        # Ping the owner in the same channel
        approval_msg = await ctx.send(
            f"{owner.mention}, server **{guild.name}** (ID: {guild.id}) requests insider access.\n"
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
            await ctx.send("insider request timed out. Please try again later.")
            return

        if str(reaction.emoji) == "✅":
            servers = utils.load_insider_servers()
            if guild.id not in servers:
                servers.append(guild.id)
                utils.save_insider_servers(servers)
            await ctx.send(f"# ✅ Approved!\n{guild.name} is now in the insider program.\n-# Please read the following message carefully.")
            await asyncio.sleep(1)
            await ctx.send(f"# Welcome to the insider program!\nYou have been chosen among **multiple servers** to test our **insider Program!**\n\nPlease note that this program includes the following rules:\n- Do not spam send feedback\n- Do not show off your insider program,\n-# - if possible, create a channel where you, admins, and the bot can only speak and see.\n- Your use of this insider program can be revoked at any moment, please respect those rules.\n\n**That's all!!** Thanks for participating and we hope you enjoy!")
        else:
            await ctx.send("# ❌ insider request denied by the bot owner.\nWe're sorry, but it appears your discord server does not meet the requirements to have a insider Prorgam.")

    @commands.command(name="insiderremove")
    @commands.is_owner()
    async def insiderremove(self, ctx, guild_id: int):
        """Remove a server from the insider program (owner only)."""
        servers = utils.load_insider_servers()
        if guild_id in servers:
            servers.remove(guild_id)
            utils.save_insider_servers(servers)
            await ctx.send(f"# ✅ Removed server {guild_id} from the insider program.\nYou will need permission from **the developper** to have it again.")
        else:
            await ctx.send("# ❌ Server not found in the insider program.\n-# Try running `?insiderrequest`!")

async def setup(bot):
    await bot.add_cog(insider(bot))