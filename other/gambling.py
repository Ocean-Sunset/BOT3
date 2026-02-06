# --------------------------------
# --------------------------------
# DEPRECATED, USE AT YOUR OWN RISK
# --------------------------------
# --------------------------------

import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import os
from Ediscord import utils, variables


ITEMS = {
    "Yippee (Normal)": 1.0,  # 1%
    "Yippee (Gold)": 0.3,    # 0.3%
    "Yippee (Diamond)": 0.03, # 0.03%
    "Empty Slot": 80.0,
    "Basic Gem": 10.0,
    "Silver Coin": 5.0,
    "Gold Coin": 2.0,
    "Enchanted Feather": 1.0,
    "Lucky Charm": 0.67,
}

class GamblingAchievements(commands.Cog):
    """
    A cog that handles a gambling and achievement system.
    """

    def __init__(self, bot):
        self.bot = bot
        self.user_data = {}
        self.all_achievements = self.load_achievements()

    def load_achievements(self, file_path="../data/achivements.json"):
        """
        Loads achievement data from the specified JSON file.
        If the file is not found, it creates a new one with default data.

        Returns:
            list: A list of achievement dictionaries, or an empty list.
        """
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: The file '{file_path}' was not found.")
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
            os.makedirs(data_dir, exist_ok=True)

            achievements_data = [
                {
                    "name": "Get a hold of HIM.",
                    "description": "Roll YIPPEE !!!!!",
                    "image": "yippee.png",
                    "condition": "roll == 'Yippee (Normal)'"
                },
                {
                    "name": "Midas touch.",
                    "description": "Roll YIPPEE gold.",
                    "image": "yippeegold.png",
                    "condition": "roll == 'Yippee (Gold)'"
                },
                {
                    "name": "MONIIIIIIIIIII!!!!",
                    "description": "Roll YIPPEE diamond.",
                    "image": "yippeediamond.png",
                    "condition": "roll == 'Yippee (Diamond)'"
                },
                {
                    "name": "Lady Luck",
                    "description": "Roll the same thing, 3X.",
                    "image": "ladyluck.png",
                    "condition": "last_rolls[0] == last_rolls[1] == last_rolls[2]"
                }
            ]
            
            with open(os.path.join(data_dir, "achivements.json"), "w") as f:
                json.dump(achievements_data, f, indent=4)

            print(f"Created a new 'achivements.json' with default data. Please restart the bot to load.")
            return []
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from '{file_path}'.")
            return []

    def roll_item(self):
        """
        Simulates a gambling roll and returns a random item based on its probability.

        Returns:
            str: The name of the item rolled.
        """
        items_list = list(ITEMS.keys())
        chances_list = list(ITEMS.values())
        return random.choices(items_list, weights=chances_list, k=1)[0]

    def check_achievements(self, roll, last_rolls, user_achievements):
        """
        Checks if any new achievements have been unlocked and returns them.

        Args:
            roll (str): The name of the item just rolled.
            last_rolls (list): A list of the last 3 rolled items.
            user_achievements (list): A list of achievement names the user already has.

        Returns:
            list: A list of new achievement dictionaries unlocked in this roll.
        """
        newly_unlocked = []
        
        environment = {
            "roll": roll,
            "last_rolls": last_rolls
        }

        for achievement in self.all_achievements:
            if achievement["name"] not in user_achievements:
                try:
                    if eval(achievement["condition"], {}, environment):
                        newly_unlocked.append(achievement)
                except Exception as e:
                    print(f"Error evaluating achievement condition '{achievement['condition']}': {e}")
                    
        return newly_unlocked

    @commands.command(name='gamble')
    async def roll_command(self, ctx):
        if not utils.is_insider_server(ctx.guild.id):
            return await ctx.send("# ❌ Not an insider server!\nThis is a beta command and is therefor only for the insider program servers.\n-# If you wish to have an insider program server, please do `?insiderrequest` and wait for **the owner to approve your server!**")
        """
        Simulates a gambling roll for a user and checks for achievements.
        """
        user_id = str(ctx.author.id)
        
        # Initialize user data if it doesn't exist
        if user_id not in self.user_data:
            self.user_data[user_id] = {"last_rolls": [], "unlocked_achievements": []}
            
        # Perform the roll
        rolled_item = self.roll_item()
        
        # Update the user's roll history
        self.user_data[user_id]["last_rolls"].insert(0, rolled_item)
        if len(self.user_data[user_id]["last_rolls"]) > 3:
            self.user_data[user_id]["last_rolls"].pop()
            
        # Check for new achievements
        unlocked = self.check_achievements(
            rolled_item,
            self.user_data[user_id]["last_rolls"],
            self.user_data[user_id]["unlocked_achievements"]
        )
        
        # Build the response message
        response = f"**{ctx.author.name}**, you rolled a **{rolled_item}**!\n"
        
        if unlocked:
            for achievement in unlocked:
                self.user_data[user_id]["unlocked_achievements"].append(achievement["name"])
                
                # Construct the image path dynamically
                image_path = f"assets/guild_assets/{ctx.guild.id}/{achievement['image']}"
                
                response += (
                    f"🎉 **Congratulations!** You unlocked the achievement: **{achievement['name']}**\n"
                    f"> *Description:* {achievement['description']}\n"
                    f"> *Image Path:* `{image_path}`\n"
                )
        
        await ctx.send(response)

# The setup function required by discord.py to load the cog
async def setup(bot):
    await bot.add_cog(GamblingAchievements(bot))
