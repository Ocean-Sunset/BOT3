# --------------------------------
# --------------------------------
# DEPRECATED, USE AT YOUR OWN RISK
# --------------------------------
# --------------------------------

import os
import sys
import asyncio
import time
from discord.ext import commands
import discord
import requests
import random
import re

# Main API endpoint for user details by ID
REGULAR_USER_API_HTTP = "https://users.roblox.com/v1/users/"
# API endpoint for getting user ID from username
USERNAME_TO_ID_API = "https://users.roblox.com/v1/usernames/users"
# API endpoint for getting user description by ID
USER_DESCRIPTION_API_HTTP = "https://users.roblox.com/v1/users/"

print("✅ - Roblox API loaded.")

# Define the main cog class
class RobloxAPI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Create a command group for Roblox APIs
    @commands.group(name="RobloxAPI", invoke_without_command=True)
    async def roblox_api(self, ctx):
        """
        Base command for all Roblox API interactions.
        Use `!RobloxAPI GET <api_name> <user_input>`
        """
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="RobloxAPI",
                description="This is a command group for interacting with Roblox APIs. Use the following subcommands:\n\n**GET API:**\n`?RobloxAPI GET User <user_id_or_username>`\n`?RobloxAPI GET Description <user_id_or_username>`\n\n**Note:** Other APIs are coming soon!",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)

    # Sub-command for the GET method, which takes the API name as an argument
    @roblox_api.command(name="GET")
    async def get_command(self, ctx, api_name: str, *, user_input: str):
        """
        Get details from a specified Roblox API.
        
        Args:
            api_name (str): The name of the API (e.g., "User" or "Description").
            user_input (str): The input for the specified API.
        """
        user_id = None
        # First, attempt to get the user ID from the user input.
        # This is a shared function now to reduce redundant code.
        try:
            if re.match(r"^\d+$", user_input):
                user_id = user_input
            else:
                payload = {
                    "usernames": [user_input],
                    "excludeBannedUsers": True
                }
                response = requests.post(USERNAME_TO_ID_API, json=payload)
                response.raise_for_status()
                
                data = response.json()
                
                if data and data.get("data"):
                    user_id = data["data"][0]["id"]
                else:
                    embed = discord.Embed(
                        title="User Not Found ❌",
                        description=f"Could not find a user with the username `{user_input}`. Please try again with a valid username or ID.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
                    return # Exit the function if the user is not found
                
        except requests.exceptions.RequestException as e:
            embed = discord.Embed(
                title="Request Error ⚠️",
                description=f"An error occurred while fetching user ID: {e}",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

        # Handle different API requests based on the user's input.
        if api_name.lower() == "user":
            await ctx.send("⌛ Fetching user data...", ephemeral=True)
            try:
                response = requests.get(f"{REGULAR_USER_API_HTTP}{user_id}")
                response.raise_for_status()

                user_details = response.json()

                embed = discord.Embed(
                    title=user_details.get("displayName", "N/A"),
                    description=f"Details for the Roblox user.",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Username", value=user_details.get("name", "N/A"), inline=True)
                embed.add_field(name="User ID", value=user_details.get("id", "N/A"), inline=True)
                embed.add_field(name="Created", value=user_details.get("created", "N/A"), inline=False)

                await ctx.send(embed=embed)

            except requests.exceptions.HTTPError as errh:
                embed = discord.Embed(
                    title="API Error ⚠️",
                    description=f"HTTP Error: {errh}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
            except requests.exceptions.RequestException as e:
                embed = discord.Embed(
                    title="Request Error ⚠️",
                    description=f"An error occurred: {e}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
        
        elif api_name.lower() == "description":
            await ctx.send("⌛ Fetching user description...", ephemeral=True)
            try:
                # The endpoint needs the user ID in the path
                description_url = f"{USER_DESCRIPTION_API_HTTP}{user_id}/description"
                response = requests.get(description_url)
                response.raise_for_status()

                description_data = response.json()

                # Get the user's display name for the embed title
                user_details_response = requests.get(f"{REGULAR_USER_API_HTTP}{user_id}")
                user_details_response.raise_for_status()
                user_details = user_details_response.json()

                user_description = description_data.get("description", "No description available.")
                if not user_description:
                    user_description = "No description available."

                embed = discord.Embed(
                    title=f"{user_details.get('displayName', 'N/A')}'s Description",
                    description=user_description,
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)

            except requests.exceptions.HTTPError as errh:
                embed = discord.Embed(
                    title="API Error ⚠️",
                    description=f"HTTP Error: {errh}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
            except requests.exceptions.RequestException as e:
                embed = discord.Embed(
                    title="Request Error ⚠️",
                    description=f"An error occurred: {e}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)

        else:
            # Handle unknown API names
            embed = discord.Embed(
                title="Unknown API ❌",
                description=f"The API `{api_name}` is not currently supported.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
# The setup function for the bot
async def setup(bot):
    await bot.add_cog(RobloxAPI(bot))