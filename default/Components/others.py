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

    @commands.command(name="trivia")
    async def trivia(self, ctx):
        """Start a trivia game."""
        questions = {
            "What is the capital of France?": "Paris",
            "What is 757.124964164? + 64565*(6454/15)": "27799991.524964165",
            "Who wrote 'To Kill a Mockingbird'?": "Harper Lee",
            "What is the largest planet in our solar system?": "Jupiter",
            "What is the chemical symbol for gold?": "Au",
            "What is the smallest prime number?": "2",
            "Who painted the Mona Lisa?": "Leonardo da Vinci",
            "What is the largest mammal?": "Blue Whale",
            "What is the capital of Japan?": "Tokyo",
            "What is the hardest natural substance on Earth?": "Diamond",
            "What is the main ingredient in guacamole?": "Avocado",
            "What is the longest river in the world?": "Nile",
            "What is the largest desert in the world?": "Sahara",
            "What is the speed of light?": "299792458 m/s",
            "What is the boiling point of water?": "100°C",
            "What is the largest ocean on Earth?": "Pacific Ocean",
            "What is the most spoken language in the world?": "Mandarin Chinese",
            "What is the capital of Canada?": "Ottawa",
            "What is the currency of Japan?": "Yen",
            "What is the tallest mountain in the world?": "Mount Everest",
            "What is the largest continent?": "Asia",
            "What is the main ingredient in sushi?": "Rice",
            "What is the capital of Italy?": "Rome",
            "What is the largest country in the world?": "Russia",
            "What is the most populous country?": "China",
            "What is the capital of Australia?": "Canberra",
            "What is the largest island in the world?": "Greenland",
            "What is the main ingredient in hummus?": "Chickpeas",
            "What is the capital of Germany?": "Berlin",
            "What is the largest volcano in the world?": "Mauna Loa",
            "What is the chemical symbol for silver?": "Ag",
            "What is the largest city in the world?": "Tokyo",
            "What is the main ingredient in chocolate?": "Cocoa",
            "What is the capital of Spain?": "Madrid",
            "What is the largest lake in the world?": "Caspian Sea",
            "What is the main ingredient in bread?": "Flour",
            "What is the capital of Russia?": "Moscow",
            "What is the largest animal on land?": "African Elephant",
            "What is the main ingredient in pizza?": "Dough",
            "What is the capital of Egypt?": "Cairo",
            "What is the largest city in the USA?": "New York City",
            "What is the main ingredient in curry?": "Spices",
            "What is the capital of Brazil?": "Brasilia",
            "What is the largest organ in the human body?": "Skin",
            "What is the main ingredient in pancakes?": "Flour",
            "What is the capital of India?": "New Delhi",
            "What is the largest city in Canada?": "Toronto",
            "What is the main ingredient in salad?": "Vegetables",
            "What is the capital of Mexico?": "Mexico City",
            "What is the largest city in Australia?": "Sydney",
            "What is the main ingredient in soup?": "Broth",
            "What is the capital of Argentina?": "Buenos Aires",
            "What is the largest city in Europe?": "Moscow",
            "What is the main ingredient in ice cream?": "Cream",
            "What is the capital of South Africa?": "Pretoria",
            "What is the main ingredient in cheese?": "Milk",
            "What is the capital of Turkey?": "Ankara",
            "What is the main ingredient in jelly?": "Fruit",
            "What is the capital of Thailand?": "Bangkok",
            "What is the main ingredient in mayonnaise?": "Eggs",
            "What is the capital of Greece?": "Athens",
            "What is the main ingredient in ketchup?": "Tomatoes",
            "What is the capital of Portugal?": "Lisbon",
            "What is the main ingredient in mustard?": "Mustard seeds",
            "What is the capital of Sweden?": "Stockholm",
            "What is the main ingredient in salsa?": "Tomatoes",
            "What is the capital of Norway?": "Oslo",
            "What is the main ingredient in pesto?": "Basil",
            "What is the capital of Denmark?": "Copenhagen",
            "What is the main ingredient in guacamole?": "Avocado",
            "What is the capital of Finland?": "Helsinki",
            "What is the main ingredient in tzatziki?": "Yogurt",
            "What is the capital of Hungary?": "Budapest",
            "What is the main ingredient in hummus?": "Chickpeas",
            "What is the capital of Czech Republic?": "Prague",
            "What is the main ingredient in falafel?": "Chickpeas",
            "What is the capital of Slovakia?": "Bratislava",
            "What is the main ingredient in tabbouleh?": "Bulgur",
            "What is the capital of Romania?": "Bucharest",
            "What is the main ingredient in moussaka?": "Eggplant",
            "What is the capital of Bulgaria?": "Sofia",
            "What is the main ingredient in baklava?": "Phyllo dough",
            "What is the capital of Serbia?": "Belgrade",
            "What is the main ingredient in goulash?": "Beef",
            "What is the capital of Croatia?": "Zagreb",
            "What is the chemical symbol for iron?": "Fe",
            "What is the main ingredient in paella?": "Rice",
            "What is the capital of Slovenia?": "Ljubljana",
            "What is the main ingredient in risotto?": "Rice",
            "What is the capital of Bosnia and Herzegovina?": "Sarajevo",
            "What is the main ingredient in borscht?": "Beets",
            "What is the capital of Montenegro?": "Podgorica",
            "What is the main ingredient in cevapi?": "Ground meat",
            "What is the capital of North Macedonia?": "Skopje",
            "What is the main ingredient in ajvar?": "Red peppers",
            "What is the capital of Albania?": "Tirana",
            "What is the main ingredient in sarma?": "Cabbage",
            "What is the capital of Kosovo?": "Pristina",
            "What is the main ingredient in burek?": "Phyllo dough",
            "What is the capital of Malta?": "Valletta",
            "What is the main ingredient in pastizzi?": "Ricotta",
            "What is the capital of Cyprus?": "Nicosia",
            "What is the main ingredient in halloumi?": "Cheese",
            "What is the capital of Luxembourg?": "Luxembourg City",
            "What is the main ingredient in quiche?": "Eggs",
            "What is the capital of Liechtenstein?": "Vaduz",
            "What is the main ingredient in fondue?": "Cheese",
            "What is the capital of Monaco?": "Monaco",
            "What is the main ingredient in ratatouille?": "Vegetables",
            "What is the capital of San Marino?": "San Marino",
            "What is the main ingredient in tiramisu?": "Coffee",
            "What is the capital of Vatican City?": "Vatican City",
            "What is the main ingredient in panna cotta?": "Cream",
            "What is the capital of Andorra?": "Andorra la Vella",
            "What is the main ingredient in churros?": "Dough",
            "What is the capital of Monaco?": "Monaco",
            "What is the main ingredient in croissants?": "Dough",
            "What is the capital of Gibraltar?": "Gibraltar",
            "What is the main ingredient in scones?": "Flour",
            "What is the capital of Bermuda?": "Hamilton",
            "What is the main ingredient in shortbread?": "Butter",
            "What is the capital of the Bahamas?": "Nassau",
            

        }
        question, answer = random.choice(list(questions.items()))
        await ctx.send(f"❓ {question}")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            response = await self.bot.wait_for("message", check=check, timeout=60.0)
            if response.content.lower() == answer.lower():
                reward = random.randrange(0, 1000)
                user_id = str(ctx.author.id)
                utils.update_coins(user_id, reward)
                await ctx.send(f"✅ Correct! You earned {reward} coins.")
            else:
                await ctx.send(f"❌ Wrong! The correct answer was **{answer}**.")
        except asyncio.TimeoutError:
            await ctx.send("⏰ Time's up! You didn't answer in time.")

async def setup(bot):
    await bot.add_cog(Other(bot))
