import discord
from discord.ext import commands
from Ediscord import utils
from discord import app_commands
import logging

print("✅ - Subscriptions cog loaded.")
class Subscriptions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="subscribe_plus", description="Grant plus subscription to a user (owner-only).")
    @app_commands.checks.has_permissions(administrator=True)
    async def subscribe_plus(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        utils.subscription_plus(user.id)
        await interaction.response.send_message(f"✅ {user.mention} has been given Plus subscription (5 servers).", ephemeral=True)


    @app_commands.command(name="subscribe_max", description="Grant max subscription to a user (owner-only).")
    @app_commands.checks.has_permissions(administrator=True)
    async def subscribe_max(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        utils.subscription_max(user.id)
        await interaction.response.send_message(f"✅ {user.mention} has been given Max subscription (15 servers).", ephemeral=True)


    @app_commands.command(name="subscribe_status", description="Show subscription status for a user.")
    async def subscribe_status(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        tier = utils.user_subscription_tier(user.id)
        subs = utils.load_subscriptions()
        entry = subs.get(str(user.id), {"servers": []})
        servers = entry.get("servers", [])
        await interaction.response.send_message(f"Subscription for {user.mention}: Tier={tier} Servers={len(servers)} ({', '.join(servers)})", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Subscriptions(bot))
