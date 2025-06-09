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

# --------------------- OTHER COMMANDS --------------------
print("✅ - Others loaded.")
class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="zen")
    async def zen(self, ctx, member: discord.Member = None, time: str = None):
        """Put a user in Zen mode (timeout) for a specified duration."""
        if member is None:
            member = ctx.author  # If no member is mentioned, use the command author
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
        try:
            await member.timeout(until=None)  # Remove the timeout
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
        winner = max(results, key=results.get)
        await ctx.send(f"🏆 The winning option is: {winner}")
        
    # ?chat command (ChatGPT integration)
    @commands.command()
    async def chat(self, ctx, *, message):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", messages=[{"role": "user", "content": message}]
            )
            reply = response["choices"][0]["message"]["content"]
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
    async def eggs(self, ctx, member: discord.Member = None):
        """Check how many eggs a user has collected."""
        member = member or ctx.author
        user_id = str(member.id)
        eggs_collected = variables.easter_data.get(user_id, {}).get("eggs", 0)
        await ctx.send(f"🥚 {member.mention} has collected **{eggs_collected} eggs**!")
    
    @commands.command(name="akari_points")
    async def akari_points(self, ctx):
        """Check your Akari Points balance."""
        points_data = utils.load_akari_points()
        points = points_data.get(str(ctx.author.id), {}).get("points", 0)
        await ctx.send(f"🌸 {ctx.author.mention}, you have **{points} Akari Points**!")

    @commands.command(name="akari_redeem")
    async def akari_redeem(self, ctx, reward: str, *, extra: str = None):
        """Redeem Akari Points for rewards."""
        reward = reward.lower()
        if reward not in variables.AKARI_REWARDS:
            await ctx.send(f"❌ Invalid reward. Available: {', '.join(variables.AKARI_REWARDS.keys())}")
            return

        points_data = utils.load_akari_points()
        user_id = str(ctx.author.id)
        user_points = points_data.get(user_id, {}).get("points", 0)
        cost = variables.AKARI_REWARDS[reward]["cost"]

        if user_points < cost:
            await ctx.send(f"❌ You need {cost} Akari Points to redeem **{reward}**. You have {user_points}.")
            return

        points_data[user_id]["points"] -= cost
        utils.save_akari_points(points_data)

        # Grant reward logic
        if reward in ["voice", "image"]:
            role_name = f"Akari {reward.capitalize()} Reward"
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            if not role:
                role = await ctx.guild.create_role(name=role_name, mentionable=False, hoist=False, reason="Akari Points Reward")
            await ctx.author.add_roles(role)
            await ctx.send(f"✅ {ctx.author.mention}, you redeemed **{cost} Akari Points** for: {variables.AKARI_REWARDS[reward]['desc']}! Use your reward and the role will be removed automatically.")
        elif reward == "nickname":
            if extra:
                await ctx.author.edit(nick=extra)
                await ctx.send(f"✅ Nickname changed to **{extra}** for 24h!")
                await asyncio.sleep(86400)
                await ctx.author.edit(nick=None)
            else:
                await ctx.send("❌ Please provide a nickname. Usage: `?akari_redeem nickname <new_nickname>`")
        elif reward == "shoutout":
            channel = discord.utils.find(lambda c: "announcement" in c.name.lower(), ctx.guild.text_channels)
            if channel:
                await channel.send(f"🎉 Shoutout to {ctx.author.mention}: {extra or 'You are awesome!'}")
                await ctx.send("✅ Shoutout sent!")
            else:
                await ctx.send("❌ Announcements channel not found.")
        elif reward == "colorrole":
            if extra and extra.startswith("#") and len(extra) == 7:
                color = discord.Color(int(extra[1:], 16))
                role_name = f"Akari Color {ctx.author.id}"
                role = discord.utils.get(ctx.guild.roles, name=role_name)
                if not role:
                    role = await ctx.guild.create_role(name=role_name, color=color, mentionable=False, hoist=False)
                await ctx.author.add_roles(role)
                await ctx.send(f"✅ Custom color role granted for 24h!")
                await asyncio.sleep(86400)
                await ctx.author.remove_roles(role)
                await role.delete()
            else:
                await ctx.send("❌ Please provide a hex color (e.g., #FF5733). Usage: `?akari_redeem colorrole #RRGGBB`")
        elif reward == "pin":
            if ctx.message.reference:
                msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                await msg.pin()
                await ctx.send("✅ Message pinned!")
            else:
                await ctx.send("❌ Reply to the message you want to pin and use this command.")
        elif reward == "emoji":
            if extra and ctx.message.attachments:
                img = await ctx.message.attachments[0].read()
                emoji = await ctx.guild.create_custom_emoji(name=extra, image=img)
                await ctx.send(f"✅ Custom emoji `{emoji}` added for 24h!")
                await asyncio.sleep(86400)
                await emoji.delete()
            else:
                await ctx.send("❌ Attach an image and provide a name. Usage: `?akari_redeem emoji <name>`")
        elif reward == "poll":
            if extra:
                await ctx.send(f"📊 Poll: {extra}\nReact with 👍 or 👎")
            else:
                await ctx.send("❌ Please provide a poll question. Usage: `?akari_redeem poll <question>`")
        elif reward == "highlight":
            highlight_channel = discord.utils.find(lambda c: "highlight" in c.name.lower(), ctx.guild.text_channels)
            if ctx.message.reference and highlight_channel:
                msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                await highlight_channel.send(f"🌟 Highlighted by {ctx.author.mention}:\n{msg.content}")
                await ctx.send("✅ Message highlighted!")
            else:
                await ctx.send("❌ Reply to the message you want to highlight and make sure a #highlights channel exists.")
        elif reward == "priorityqueue":
            await ctx.send("✅ You will be moved to the front of the music queue the next time you use `?play`!")
            # Implement your queue logic here
        elif reward == "gift":
            if extra and ctx.message.mentions:
                target = ctx.message.mentions[0]
                utils.update_coins(target.id, 100)
                await ctx.send(f"🎁 {ctx.author.mention} gifted 100 coins to {target.mention}!")
            else:
                await ctx.send("❌ Mention a user to gift coins. Usage: `?akari_redeem gift @user`")
        else:
            await ctx.send("✅ Reward redeemed! (No special action for this reward yet)")

            

async def setup(bot):
    await bot.add_cog(Other(bot))
