
import discord
from discord.ext import commands
from discord import app_commands
from Ediscord import utils
import logging

class Migration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="migrate_data", description="Migrate your global data to this server.")
    async def migrate_data(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        
        # Load global data
        global_data = utils.load_user_data()
        
        if user_id not in global_data:
            await interaction.response.send_message("❌ You don't have any global data to migrate.", ephemeral=True)
            return

        user_global = global_data[user_id]
        
        # Load current guild data (to show what will be overwritten)
        guild_user_data = utils.get_guild_user_data(interaction.guild.id, interaction.user.id)
        
        # Create a formatted summary of what will be transferred
        # We migrate: XP, Level, Censored Count, Strikes, Warnings. 
        # (Coins/Gems/Inventory are seemingly global/shared in this bot based on money.py using load_user_data/inventory, 
        # but prompt said "Level system PER SERVER". So we focus on Level/XP).
        
        g_level = user_global.get("level", 1)
        g_xp = user_global.get("xp", 0)
        
        c_level = guild_user_data.get("level", 1)
        c_xp = guild_user_data.get("xp", 0)

        # Check if already migrated
        if guild_user_data.get("migrated"):
            await interaction.response.send_message("❌ You have already migrated your data to this server.", ephemeral=True)
            return

        # Check if global data is actually better
        if g_xp <= c_xp:
             await interaction.response.send_message("❌ Your current server data is already equal to or higher than your global data. Migration not needed.", ephemeral=True)
             return

        embed = discord.Embed(
            title="📊 Data Migration",
            description=f"Do you want to import your global stats to **{interaction.guild.name}**?",
            color=discord.Color.blue()
        )
        embed.add_field(name="Global Data (Source)", value=f"Level: {g_level}\nXP: {g_xp}", inline=True)
        embed.add_field(name="Current Server Data (Target)", value=f"Level: {c_level}\nXP: {c_xp}", inline=True)
        embed.add_field(name="⚠️ Warning", value="This will **overwrite** your current level and XP on this server with your global stats.", inline=False)
        
        view = discord.ui.View()
        
        async def confirm_callback(interact: discord.Interaction):
            if interact.user.id != interaction.user.id:
                await interact.response.send_message("❌ This confirmation is not for you.", ephemeral=True)
                return
            
            # Perform Migration
            # We copy specific fields. 
            # If we copy everything, we function as a full backup restore.
            # "Claim their data" implies full restoration.
            
            fields_to_migrate = ["xp", "level", "warnings", "censored_count", "strikes"] 
            # Coins/Gems are global in money.py, so we don't migrate them to per-server file (or if we do, they are ignored by money.py).
            # But let's copy them anyway just in case future updates use per-server economy.
            
            new_data = guild_user_data.copy()
            for key in fields_to_migrate:
                if key in user_global:
                    new_data[key] = user_global[key]
            
            # Save
            utils.update_guild_user_data(interaction.guild.id, interaction.user.id, "xp", new_data.get("xp", 0))
            utils.update_guild_user_data(interaction.guild.id, interaction.user.id, "level", new_data.get("level", 1))
            utils.update_guild_user_data(interaction.guild.id, interaction.user.id, "warnings", new_data.get("warnings", []))
            utils.update_guild_user_data(interaction.guild.id, interaction.user.id, "censored_count", new_data.get("censored_count", 0))
            utils.update_guild_user_data(interaction.guild.id, interaction.user.id, "strikes", new_data.get("strikes", 0))
            utils.update_guild_user_data(interaction.guild.id, interaction.user.id, "migrated", True)
            
            await interact.response.edit_message(content=f"✅ **Migration Complete!**\nYour global stats have been applied to {interaction.guild.name}.", view=None, embed=None)
            logging.info(f"User {interaction.user} migrated data to guild {interaction.guild.name}")

        async def cancel_callback(interact: discord.Interaction):
            if interact.user.id != interaction.user.id:
                await interact.response.send_message("❌ This confirmation is not for you.", ephemeral=True)
                return
            await interact.response.edit_message(content="❌ Migration cancelled.", view=None, embed=None)

        confirm_btn = discord.ui.Button(label="Confirm Migration", style=discord.ButtonStyle.green, custom_id="confirm_migrate")
        confirm_btn.callback = confirm_callback
        
        cancel_btn = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.red, custom_id="cancel_migrate")
        cancel_btn.callback = cancel_callback
        
        view.add_item(confirm_btn)
        view.add_item(cancel_btn)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Migration(bot))
