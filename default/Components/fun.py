# --------------------- IMPORTS --------------------
import discord
from discord.ext import commands
import asyncio
from Ediscord import variables, utils
import requests
import random
import typing

# --------------------- FUN COMMANDS --------------------
print("✅ - Fun loaded.")
class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="rps")
    async def rps(self, ctx, choice: str):
        """Play Rock-Paper-Scissors."""
        choices = ["rock", "paper", "scissors"]
        bot_choice = random.choice(choices)
        if choice not in choices:
            await ctx.send("# ❌ Invalid choice!\nChoose rock, paper, or scissors.")
            return
        if choice == bot_choice:
            result = "# 🤝 It's a tie!"
        elif (
            (choice == "rock" and bot_choice == "scissors")
            or (choice == "paper" and bot_choice == "rock")
            or (choice == "scissors" and bot_choice == "paper")
        ):
            result = "You win!"
        else:
            result = "You lose!"
        await ctx.send(f"🤖 I chose {bot_choice}.\n# {result}")
    
    @commands.command(name="joke")
    async def joke(self, ctx):
        """Fetch a random joke."""
        url = "https://official-joke-api.appspot.com/random_joke"
        try:
            response = requests.get(url)
            data = response.json()
            await ctx.send(f"😂 **{data['setup']}**\n# {data['punchline']}")
        except Exception as e:
            await ctx.send(f"# ❌ Failed to fetch a joke\n{e}")


    @commands.command(name="flip")
    async def flip(self, ctx):
        """Flip a coin."""
        result = random.choice(["Heads", "Tails"])
        await ctx.send(f"🪙 The coin landed on:\n# **{result}**!")
    
    @commands.command(name="roll")
    async def roll(self, ctx, sides: int = 6):
        """Roll a dice with a specified number of sides (default: 6)."""
        if sides < 1:
            await ctx.send("# ❌ The dice must have at least 1 side!\nEnter a number beetwen 1 and 6!")
            return
        result = random.randint(1, sides)
        await ctx.send(f"# 🎲 You rolled a **{result}** on a **{sides}**-sided dice!")


    @commands.command(name="meme")
    async def meme(self, ctx):
        """Fetch a random meme from Reddit."""
        url = "https://www.reddit.com/r/memes/random/.json"
        headers = {"User-Agent": "DiscordBot"}
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            meme_url = data[0]["data"]["children"][0]["data"]["url"]
            title = data[0]["data"]["children"][0]["data"]["title"]
            await ctx.send(f"**{title}**\n{meme_url}")
        except Exception as e:
            await ctx.send(f"# ❌ Failed to fetch a meme\n{e}")

async def setup(bot):
    await bot.add_cog(Fun(bot))
