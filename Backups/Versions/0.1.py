import discord
from discord.ext import commands
import os
import openai  # For ChatGPT functionality

# Define intents and enable the message content intent
intents = discord.Intents.default()
intents.message_content = True  # This is required for processing commands

# Create the bot with intents
bot = commands.Bot(command_prefix="?", intents=intents)

# Set OpenAI API Key
OPENAI_API_KEY = "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"  # Replace with your actual API key
openai.api_key = OPENAI_API_KEY

# Event: Bot is ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Allow commands to be processed
    await bot.process_commands(message)


# ?help command
@bot.command(name="myhelp")
async def help(ctx):
    print(f"Help command triggered by {ctx.author} in channel {ctx.channel}.")
    help_message = """Available commands:
    ?help - Show this help message
    ?info - Get information about the bot
    ?serverinfo - Get information about the current server
    ?shutdown - Shut down the bot (Admin only)
    ?start - Start the bot (Admin only)
    ?poll - Create a poll (Usage: ?poll <question> <option1, option2, ...>)
    ?chat - Chat with ChatGPT (Usage: ?chat <your message>)
    """
    await ctx.send(help_message)



# ?info command
@bot.command()
async def info(ctx):
    custominfo = (
    "I am a multifunctional Discord bot, here to assist you!"
    )
    await ctx.send(custominfo)


# ?serverinfo command
@bot.command()
async def serverinfo(ctx):
    server = ctx.guild
    server_info = (
        f"Server Name: {server.name}\n"
        f"Member Count: {server.member_count}\n"
        f"Created At: {server.created_at.strftime('%Y-%m-%d')}\n"
    )
    await ctx.send(server_info)

# ?shutdown command
@bot.command()
@commands.has_permissions(administrator=True)
async def shutdown(ctx):
    await ctx.send("Shutting down...")
    await bot.close()

# ?start command
@bot.command()
@commands.has_permissions(administrator=True)
async def start(ctx):
    await ctx.send("The bot is already running!")

# ?poll command
@bot.command()
async def poll(ctx, question: str, *options):
    if len(options) < 2:
        await ctx.send("You need at least two options to create a poll.")
        return

    if len(options) > 10:
        await ctx.send("You cannot create a poll with more than 10 options.")
        return

    embed = discord.Embed(title=question, description="React to vote!")
    reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for i, option in enumerate(options):
        embed.add_field(name=f"Option {i+1}", value=option, inline=False)

    poll_message = await ctx.send(embed=embed)

    for i in range(len(options)):
        await poll_message.add_reaction(reactions[i])

# ?chat command (ChatGPT integration)
@bot.command()
async def chat(ctx, *, message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message}]
        )
        reply = response['choices'][0]['message']['content']
        await ctx.send(reply)
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.event
async def on_command_error(ctx, error):
    # Check if the error is a "CommandNotFound" error
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ That command does not exist. Use `?help` to see the list of available commands.")
    # Handle other errors (optional)
    else:
        await ctx.send("❌ An error occurred while processing your command. Please try again.")


# Run the bot
TOKEN = "MTMyMzAyNTc3NTc2NjY2NzMzNA.GhlAHV.zAkNHoPrnkAJutl9END4znCl3oTWNokYk4dIeE"  # Replace with your actual bot token
bot.run(TOKEN)