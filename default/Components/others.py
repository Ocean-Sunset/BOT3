# --------------------- IMPORTS --------------------
import discord
from discord.ext import commands
import logging
from datetime import datetime, timedelta
from Ediscord import variables, utils
import requests
import asyncio
import openai
import random
import typing
# --------------------- OTHER COMMANDS --------------------
print("✅ - Others loaded.")
class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="zen")
    async def zen(self, ctx, member: typing.Optional[discord.Member] = None, time: typing.Optional[str] = None):
        """Put a user in Zen mode (timeout) for a specified duration."""
        if member is None:
            member = ctx.author  # If no member is mentioned, use the command author
        if member is None:
            await ctx.send("❌ Could not find the specified member.")
            return
        if time is None:
            await ctx.send("❌ Please provide a time in the format `hh:mm:ss`.")
            return

        # Parse the time string into hours, minutes, and seconds
        try:
            hours, minutes, seconds = map(int, time.split(":"))
            total_seconds = hours * 3600 + minutes * 60 + seconds
        except ValueError:
            await ctx.send("❌ Invalid time format. Use `hh:mm:ss`.")
            return

        # Check if the bot has permission to timeout members
        if not ctx.guild.me.guild_permissions.moderate_members:
            await ctx.send("❌ I do not have permission to timeout members.")
            return

        # Apply the timeout
        try:
            # Use the `timedelta` to calculate the timeout duration
            timeout_until = discord.utils.utcnow() + timedelta(seconds=total_seconds)
            await member.edit(
                timed_out_until=timeout_until
            )  # Correct method to apply timeout
            await ctx.send(f"✅ {member.mention} has been put in Zen mode for {time}.")
        except discord.Forbidden:
            await ctx.send("❌ I do not have permission to timeout this member.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")

    @commands.command(name="unzen")
    @commands.has_permissions(administrator=True)
    async def unzen(self, ctx, member: discord.Member):
        """Remove Zen mode (timeout) from a user."""
        if member == None:
            await ctx.send("❌ You didn't input an user!")
            return
        try:
            await member.edit(timed_out_until=None)  # Remove the timeout
            await ctx.send(f"✅ {member.mention} has been removed from Zen mode.")
        except discord.Forbidden:
            await ctx.send("❌ I do not have permission to remove the timeout.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
 
    # ?poll command
    @commands.command(name="poll")
    async def poll(self, ctx, question: str, *options):
        """Create a poll with a time limit."""
        if len(options) < 2:
            await ctx.send("❌ You need at least two options to create a poll.")
            return
        if options == None:
            await ctx.send("❌ You need to have questions!")
            return

        embed = discord.Embed(title=question, description="React to vote!")
        reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        for i, option in enumerate(options):
            embed.add_field(name=f"Option {i+1}", value=option, inline=False)

        poll_message = await ctx.send(embed=embed)

        for i in range(len(options)):
            await poll_message.add_reaction(reactions[i])

        await asyncio.sleep(30)  # Wait for 30 seconds
        poll_message = await ctx.channel.fetch_message(poll_message.id)
        results = {
            reaction.emoji: reaction.count - 1 for reaction in poll_message.reactions
        }
        winner = max(results, key=lambda k: results[k])
        await ctx.send(f"🏆 The winning option is: {winner}")
        
    # ?chat command (ChatGPT integration)
    @commands.command()
    async def chat(self, ctx, *, message):
        if message == None:
            await ctx.send("❌ You need to have a message!")
            return
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo", messages=[{"role": "user", "content": message}]
            )
            reply = response.choices[0].message.content
            print(
                f"chat command triggered by {ctx.author} in channel {ctx.channel}. State: success."
            )
            await ctx.send(reply)
        except Exception as e:
            print(
                f"chat command triggered by {ctx.author} in channel {ctx.channel}. State: failed. Reason: {e}"
            )
            await ctx.send(f"Error: {e}")
    
    @commands.command(name="wheel")
    async def wheel(self, ctx, *, names: str):
        print(names)
        if names == None:
            await ctx.send("❌ You didn't put any options")
            return
        """Spin a wheel of names and pick one randomly."""
        # Split the input into a list of names
        name_list = [name.strip() for name in names.split("/") if name.strip()]

        # Check if there are at least two names
        if len(name_list) < 2:
            await ctx.send(
                "❌ You need at least two names to spin the wheel. Use the format: `?wheel name1 / name2 / name3`."
            )
            return

        # Simulate spinning the wheel
        await ctx.send("🎡 Spinning the wheel...")
        await asyncio.sleep(2)  # Add a delay for effect

        # Pick a random name
        chosen_name = random.choice(name_list)
        await ctx.send(f"🎉 The wheel has chosen: **{chosen_name}**!")
        
    @commands.command(name="eggs")
    async def eggs(self, ctx, member: typing.Optional[discord.Member] = None):
        if member == None:
            await ctx.send("❌ You have to input a member!")
            return
        """Check how many eggs a user has collected."""
        member = member or ctx.author
        user_id = str(member.id)
        eggs_collected = variables.easter_data.get(user_id, {}).get("eggs", 0)
        await ctx.send(f"🥚 {member.mention} has collected **{eggs_collected} eggs**!")

            

async def setup(bot):
    await bot.add_cog(Other(bot))
