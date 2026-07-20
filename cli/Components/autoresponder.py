import discord
from discord.ext import commands
from discord import app_commands
import json
import re
from typing import Optional

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db


class Autoresponder(commands.Cog, name="Autoresponder"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.triggers = {}

    async def load_triggers(self, guild_id: int):
        pool = await neon_db.get_pool()
        if not pool:
            return []
        rows = await pool.fetch(
            "SELECT trigger, response, match_type FROM autoresponder WHERE guild_id = $1 ORDER BY created_at ASC",
            str(guild_id),
        )
        return [{"trigger": r["trigger"], "response": r["response"], "match_type": r["match_type"]} for r in rows]

    async def save_trigger(self, guild_id: int, trigger: str, response: str, match_type: str):
        pool = await neon_db.get_pool()
        if not pool:
            return
        await pool.execute(
            "INSERT INTO autoresponder (guild_id, trigger, response, match_type) VALUES ($1, $2, $3, $4)",
            str(guild_id), trigger, response, match_type,
        )

    async def remove_trigger(self, guild_id: int, trigger: str):
        pool = await neon_db.get_pool()
        if not pool:
            return
        await pool.execute(
            "DELETE FROM autoresponder WHERE guild_id = $1 AND trigger = $2", str(guild_id), trigger,
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        triggers = await self.load_triggers(message.guild.id)
        for t in triggers:
            if t["match_type"] == "exact" and message.content.lower() == t["trigger"].lower():
                await message.channel.send(t["response"])
            elif t["match_type"] == "contains" and t["trigger"].lower() in message.content.lower():
                await message.channel.send(t["response"])
            elif t["match_type"] == "regex":
                try:
                    if re.search(t["trigger"], message.content, re.IGNORECASE):
                        await message.channel.send(t["response"])
                except:
                    pass

    autoresponder_group = app_commands.Group(name="autoresponder", description="Auto-response commands")

    @autoresponder_group.command(name="add", description="Add an auto-response trigger")
    @app_commands.describe(trigger="The word or phrase to trigger on", response="The bot's response", match_type="How to match (exact, contains, regex)")
    @app_commands.choices(match_type=[app_commands.Choice(name="Exact match", value="exact"), app_commands.Choice(name="Contains", value="contains"), app_commands.Choice(name="Regex", value="regex")])
    async def add(self, interaction: discord.Interaction, trigger: str, response: str, match_type: str = "contains"):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
        await self.save_trigger(interaction.guild_id, trigger, response, match_type)
        await interaction.response.send_message(f"Auto-response added: `{trigger}` → {response}", ephemeral=True)

    @autoresponder_group.command(name="remove", description="Remove an auto-response trigger")
    @app_commands.describe(trigger="The trigger to remove")
    async def remove(self, interaction: discord.Interaction, trigger: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
        await self.remove_trigger(interaction.guild_id, trigger)
        await interaction.response.send_message(f"Removed trigger: `{trigger}`", ephemeral=True)

    @autoresponder_group.command(name="list", description="List all auto-responses")
    async def list_triggers(self, interaction: discord.Interaction):
        triggers = await self.load_triggers(interaction.guild_id)
        if not triggers:
            return await interaction.response.send_message("No auto-responses configured.", ephemeral=True)
        lines = [f"`{t['trigger']}` → {t['response'][:50]} ({t['match_type']})" for t in triggers]
        embed = EmbedBuilder().title("Auto-Responses").description("\n".join(lines[:25])).color("blue").build()
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Autoresponder(bot))
