# --------------------- IMPORTS --------------------
import discord
from discord.ext import commands
import asyncio
from Ediscord import variables, utils
import requests
import random

# --------------------- FUN COMMANDS --------------------
print("✅ - Fun loaded.")
class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="startgame")
    @commands.has_permissions(administrator=True)
    async def startgame(self, ctx):
        global game_ongoing
        if game_ongoing:
            await ctx.send("A game is already ongoing!")
            return

        vc_channel = utils.get_truth_or_dare_vc(ctx.guild)
        text_channel = utils.get_truth_or_dare_text_channel(ctx.guild)

        if not vc_channel or not text_channel:
            await ctx.send("Truth or Dare voice or text channel not found!")
            return

        members_in_vc = [member for member in vc_channel.members if not member.bot]
        if not members_in_vc:
            await ctx.send("No members in the Truth or Dare voice channel!")
            return
        if len(members_in_vc) > 3:
            await ctx.send("Cannot start game with more the 2 members!")
            return
        if len(members_in_vc) < 2:
            await ctx.send("Cannot start game with less than 2 members!")
            return
        player_names = ", ".join(member.display_name for member in members_in_vc)
        player_usernames = ", ".join(member.mention for member in members_in_vc)

        game_ongoing = True
        await text_channel.send(
            f"Starting Truth or Dare game! '({player_names}) Use `?continue` to proceed with the game."
        )
        utils.game_logic(ctx)
        await ctx.send("Game started!")

    @commands.command(name="startgamenovc")
    @commands.has_permissions(administrator=True)
    async def startgamenovc(self, ctx, member: discord.Member = None, member2: discord.Member = None):
        global game_ongoing
        if member is None:
            member = ctx.author
            ctx.send(f"You didnt mention any member so we chose you ({member}, by default)")
            if member2 is None:
                member2 = ctx.author
            if member2 == member:
                ctx.send("You cannot choose the same member twice!")
                return
            ctx.send(
                f"You didnt mention any member so we chose you ({member2}, by default)"
            )
        if game_ongoing:
            await ctx.send("A game is already ongoing!")
            return
        player_names = [member, member2]

        text_channel = utils.get_truth_or_dare_text_channel(ctx.guild)

        if not text_channel:
            await ctx.send("Truth or Dare text channel not found!")
            return
        game_ongoing = True
        text_channel.send(
            f"Starting Truth or Dare game! '({player_names}) Use `?continue` to proceed with the game."
        )
        utils.game_logic(ctx)
        await ctx.send("Game started!")

    @commands.command(name="continue")
    async def continue_game(self, ctx):
        global game_ongoing
        if not game_ongoing:
            await ctx.send("No game is currently ongoing!")
            return

        text_channel = utils.get_truth_or_dare_text_channel(ctx.guild)
        if ctx.channel != text_channel:
            await ctx.send(
                f"Please use the `?continue` command in the {text_channel.mention} channel."
            )
            return

        utils.game_logic(ctx)
        await text_channel.send("It's your turn! Choose Truth or Dare.")

    @commands.command(name="endgame")
    async def endgame(self, ctx):
        global game_ongoing
        if not game_ongoing:
            await ctx.send("No game is currently ongoing!")
            return

        game_ongoing = False
        text_channel = utils.get_truth_or_dare_text_channel(ctx.guild)
        await text_channel.send("The Truth or Dare game has ended.")
        await ctx.send("Game ended!")
    
    @commands.command(name="rps")
    async def rps(self, ctx, choice: str):
        """Play Rock-Paper-Scissors."""
        choices = ["rock", "paper", "scissors"]
        bot_choice = random.choice(choices)
        if choice not in choices:
            await ctx.send("❌ Invalid choice! Choose rock, paper, or scissors.")
            return
        if choice == bot_choice:
            result = "It's a tie!"
        elif (
            (choice == "rock" and bot_choice == "scissors")
            or (choice == "paper" and bot_choice == "rock")
            or (choice == "scissors" and bot_choice == "paper")
        ):
            result = "You win!"
        else:
            result = "You lose!"
        await ctx.send(f"🤖 I chose {bot_choice}. {result}")
    
    @commands.command(name="joke")
    async def joke(self, ctx):
        """Fetch a random joke."""
        url = "https://official-joke-api.appspot.com/random_joke"
        try:
            response = requests.get(url)
            data = response.json()
            await ctx.send(f"😂 **{data['setup']}**\n{data['punchline']}")
        except Exception as e:
            await ctx.send(f"❌ Failed to fetch a joke: {e}")


    @commands.command(name="flip")
    async def flip(self, ctx):
        """Flip a coin."""
        result = random.choice(["Heads", "Tails"])
        await ctx.send(f"🪙 The coin landed on: **{result}**!")
    
    @commands.command(name="roll")
    async def roll(ctx, sides: int = 6):
        """Roll a dice with a specified number of sides (default: 6)."""
        if sides < 1:
            await ctx.send("❌ The dice must have at least 1 side.")
            return
        result = random.randint(1, sides)
        await ctx.send(f"🎲 You rolled a {result} on a {sides}-sided dice!")


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
            await ctx.send(f"❌ Failed to fetch a meme: {e}")

async def setup(bot):
    await bot.add_cog(Fun(bot))
