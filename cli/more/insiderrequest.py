import discord
from discord.ext import commands
import json
import os
from discord import app_commands
import asyncio
from Ediscord import variables, utils

class insider(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="forceinsider", description="Force a server to get insider whether they like it or not (owner only)")
    @app_commands.describe(guild_id="The guild ID to force insider on")
    async def forceinsider(self, interaction: discord.Interaction, guild_id: int):
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("# ❌ Only the bot owner can use this command.", ephemeral=True)
            return
        try:
            servers = utils.load_insider_servers()
            if guild_id not in servers:
                servers.append(guild_id)
                utils.save_insider_servers(servers)
            await interaction.response.send_message(f"# ✅ Force complete!\n{guild_id} is now an Insider Server.")
        except Exception as e:
            await interaction.response.send_message("# ❌ An error occurred during forcing.", ephemeral=True)

    @app_commands.command(name="insiderrequest", description="Request access to the insider program for this server (server owner only)")
    async def insiderrequest(self, interaction: discord.Interaction):
        if not getattr(variables, "insider_mode", True):
            await interaction.response.send_message("# ❌ insider program is currently closed.\nPlease try again later.\n-# We're sorry for this but it appears the insider Program is full or closed.", ephemeral=True)
            return
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("# ❌ Only the server owner can request insider access!", ephemeral=True)
            return
        app_info = await self.bot.application_info()
        owner = app_info.owner
        guild = interaction.guild
        # Instead of reactions, DM the owner for approval
        try:
            await owner.send(f"Server **{guild.name}** (ID: {guild.id}) requests insider access.")
            await interaction.response.send_message(f"# ✅ Request sent!\nThe bot owner has been notified. You will be informed if your server is approved.")
        except Exception as e:
            await interaction.response.send_message("# ❌ Could not notify the bot owner. Please try again later.", ephemeral=True)

    @app_commands.command(name="insiderremove", description="Remove a server from the insider program (owner only)")
    @app_commands.describe(guild_id="The guild ID to remove from insider")
    async def insiderremove(self, interaction: discord.Interaction, guild_id: int):
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("# ❌ Only the bot owner can use this command.", ephemeral=True)
            return
        servers = utils.load_insider_servers()
        if guild_id in servers:
            servers.remove(guild_id)
            utils.save_insider_servers(servers)
            await interaction.response.send_message(f"# ✅ Removed server {guild_id} from the insider program.\nYou will need permission from **the developer** to have it again.")
        else:
            await interaction.response.send_message("# ❌ Server not found in the insider program.\n-# Try running `/insiderrequest`!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(insider(bot))