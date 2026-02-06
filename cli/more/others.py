# --------------------- IMPORTS --------------------
import discord
from discord.ext import commands
import logging
from datetime import datetime, timedelta
from Ediscord import variables, utils
import requests
import asyncio
import openai
from discord import app_commands
import random
import typing
# --------------------- OTHER COMMANDS --------------------
print("✅ - Others loaded.")
class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="poll", description="Create a poll with a time limit.")
    @app_commands.describe(question="The poll question", option1="Option 1", option2="Option 2", option3="Option 3", option4="Option 4", option5="Option 5", option6="Option 6", option7="Option 7", option8="Option 8", option9="Option 9", option10="Option 10")
    async def poll(self, interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str = None, option4: str = None, option5: str = None, option6: str = None, option7: str = None, option8: str = None, option9: str = None, option10: str = None):
        options = [option1, option2, option3, option4, option5, option6, option7, option8, option9, option10]
        options = [opt for opt in options if opt is not None]
        if len(options) < 2:
            await interaction.response.send_message("# ❌ You need at least two options to create a poll.\n-# There can be a minimum of 2 and a maximum of 10!", ephemeral=True)
            return
        embed = discord.Embed(title=question, description="React to vote!")
        reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for i, option in enumerate(options):
            embed.add_field(name=f"Option {i+1}", value=option, inline=False)
        poll_message = await interaction.response.send_message(embed=embed, wait=True)
        # Fetch the message object for adding reactions
        channel = interaction.channel
        last_message = None
        async for msg in channel.history(limit=1):
            last_message = msg
        if last_message:
            for i in range(len(options)):
                await last_message.add_reaction(reactions[i])
            await asyncio.sleep(30)
            poll_message = await channel.fetch_message(last_message.id)
            results = {reaction.emoji: reaction.count - 1 for reaction in poll_message.reactions}
            winner = max(results, key=lambda k: results[k])
            await channel.send(f"# 🏆 The winning option is: {winner}\nThanks for participating!!")

async def setup(bot):
    await bot.add_cog(Other(bot))
