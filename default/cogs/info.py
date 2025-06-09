# --------------------- IMPORTS --------------------
import discord
from discord.ext import commands
from Ediscord import utils, variables

# --------------------- INFO COMMANDS --------------------
print("✅ - Info loaded.")
class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="profile")
    async def profile(self, ctx):
        """Check your XP, level, coins, and deposited coins."""
        user_id = ctx.author.id
        user_data = utils.get_user_data(user_id)

        xp = user_data["xp"]
        level = user_data["level"]
        coins = user_data["coins"]
        deposited_coins = utils.get_bank_balance(
            user_id
        )  # Retrieve the user's bank balance

        await ctx.send(
            f"📜 **{ctx.author.name}'s Profile**:\n"
            f"🔹 XP: {xp}\n"
            f"🔹 Level: {level}\n"
            f"🔹 Coins: {coins}\n"
            f"🔹 Deposited Coins: {deposited_coins}"
        )

    @commands.command(name="help")
    async def smart_help(self, ctx):
        """
        Show a list of all commands in a compact embed.
        """
        # Get all visible command names
        command_names = [f"`{cmd.name}`" for cmd in self.bot.commands if not cmd.hidden]
        # Split into lines of up to 10 commands each for readability
        lines = []
        for i in range(0, len(command_names), 10):
            lines.append(" ".join(command_names[i : i + 10]))

        embed = discord.Embed(
            title="📖 Available Commands",
            description="Here are all available commands. Use `?help <command>` for more info.",
            color=discord.Color.blue(),
        )
        for idx, line in enumerate(lines):
            embed.add_field(name=f"Commands {idx+1}", value=line, inline=False)

        await ctx.send(embed=embed)
    
    @commands.command()
    async def info(self, ctx):
        custominfo = f"""# I am a multifunctional python Discord bot!
        - Status: Normal
        - Version: **{variables.bot_info['version']}**
        - Developper: th3_t1sm
    
        I am multifunctional discord bot created by th3_t1sm,
        This is just a python discord bot made with love.
        **:D**
        """
        await ctx.send(custominfo)


    @commands.command(name="changelog")
    async def changelog(self, ctx):
        changelog = f"Here is the changelog for the {variables.bot_info['version']} version: {variables.bot_info['new_stuff']}"
        await ctx.send(changelog)


    @commands.command(name="analyse")
    async def analyse(self, ctx, member: discord.Member = None):
        """Analyse a user with all available data."""
        if member is None:
            member = ctx.author  # Default to the command author if no member is mentioned

        # Load user data
        user_id = str(member.id)
        user_data = utils.get_user_data(user_id)
        inventory = utils.load_inventory().get(user_id, [])
        trophies = variables.trophy_data.get(user_id, [])
        warnings = variables.warnings_data.get(user_id, {}).get("warnings", 0)
        eggs_collected = variables.easter_data.get(user_id, {}).get("eggs", 0)
        gems_collected = user_data.get("gems", 0)
        bank_balance = utils.get_bank_balance(user_id)

        # Create the embed
        embed = discord.Embed(
            title=f"Analysis of {member.name}",
            description=f"Here are the details of {member.mention}",
            color=discord.Color.blue(),
        )

        # Add Discord profile details
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        embed.add_field(
            name="Full Name", value=f"{member.name}#{member.discriminator}", inline=False
        )
        embed.add_field(name="ID", value=member.id, inline=False)
        embed.add_field(name="Status", value=member.status, inline=False)
        embed.add_field(
            name="Account Created On",
            value=member.created_at.strftime("%d %B %Y, %H:%M:%S"),
            inline=False,
        )
        embed.add_field(
            name="Joined Server On",
            value=member.joined_at.strftime("%d %B %Y, %H:%M:%S"),
            inline=False,
        )
        embed.add_field(
            name="Roles",
            value=", ".join(
                [role.name for role in member.roles if role.name != "@everyone"]
            )
            or "None",
            inline=False,
        )

        # Add bot-related stats
        embed.add_field(name="Level", value=user_data.get("level", 0), inline=True)
        embed.add_field(name="XP", value=user_data.get("xp", 0), inline=True)
        embed.add_field(name="Coins", value=user_data.get("coins", 0), inline=True)
        embed.add_field(name="Gems", value=gems_collected, inline=True)
        embed.add_field(name="Eggs Collected", value=eggs_collected, inline=True)
        embed.add_field(name="Bank Balance", value=f"{bank_balance} coins", inline=True)
        embed.add_field(name="Warnings", value=warnings, inline=True)

        # Add inventory details
        if inventory:
            inventory_items = "\n".join(
                [f"{item['name']} (Rarity: {item['rarity']})" for item in inventory]
            )
            embed.add_field(name="Inventory", value=inventory_items, inline=False)
        else:
            embed.add_field(name="Inventory", value="Empty", inline=False)

        # Add trophies
        if trophies:
            trophy_names = [
                trophies[trophy_id]["name"]
                for trophy_id in trophies
                if trophy_id in trophies
            ]
            embed.add_field(name="Trophies", value=", ".join(trophy_names), inline=False)
        else:
            embed.add_field(name="Trophies", value="None", inline=False)

        # Send the embed
        await ctx.send(embed=embed)


    # ?serverinfo command
    @commands.command()
    async def serverinfo(self, ctx):
        server = ctx.guild
        server_info = (
             f"Server Name: {server.name}\n"
            f"Member Count: {server.member_count}\n"
            f"Created At: {server.created_at.strftime('%Y-%m-%d')}\n"
        )
        print(
            f"Server info command triggered by {ctx.author} in channel {ctx.channel}. State: success."
        )
        await ctx.send(server_info)
    

async def setup(bot):
    print("Loading Info cog...")
    await bot.add_cog(Info(bot))
