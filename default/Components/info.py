# --------------------- IMPORTS --------------------
import discord
from discord.ext import commands
from discord.ui import View, Button
from Ediscord import utils, variables
import typing
from PIL import Image, ImageDraw, ImageFont
import io
import requests
import textwrap

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
            f"# 📜 **{ctx.author.name}'s Profile**:\n"
            f"🔹 XP: **{xp}**\n"
            f"🔹 Level: **{level}**\n"
            f"🔹 Coins: **{coins}**\n"
            f"🔹 Deposited Coins: **{deposited_coins}**"
        )

    @commands.command(name="help")
    async def smart_help(self, ctx):
        """
        Show a list of all commands grouped by category (cog), paginated with buttons.
        """
        prefix = ctx.prefix

        # Group commands by cog
        categories = {}
        for command in self.bot.commands:
            if command.hidden:
                continue
            cog = command.cog_name or "Other"
            categories.setdefault(cog, []).append(command)

        # Prepare pages (one page per category/cog)
        pages = []
        for cog, cmds in categories.items():
            lines = [f"`{prefix}{cmd.name}`: {cmd.short_doc or 'No description'}" for cmd in cmds]
            value = ""
            more = False
            for line in lines:
                if len(value) + len(line) + 1 > 1000:
                    more = True
                    break
                value += line + "\n"
            if more:
                value += "...and more"
            embed = discord.Embed(
                title="📖 Bot Commands",
                description=f"Use `{prefix}help <command>` for more info.",
                color=discord.Color.blue(),
            )
            embed.add_field(
                name=cog,
                value=value or "No commands.",
                inline=False
            )
            pages.append(embed)

        if not pages:
            await ctx.send("No commands available.")
            return

        class HelpView(View):
            def __init__(self, pages):
                super().__init__(timeout=60)
                self.pages = pages
                self.index = 0

            async def update_message(self, interaction):
                for child in self.children:
                    if isinstance(child, Button):
                        child.disabled = False
                if self.index == 0:
                    self.children[0].disabled = True  # Previous
                if self.index == len(self.pages) - 1:
                    self.children[1].disabled = True  # Next
                await interaction.response.edit_message(embed=self.pages[self.index], view=self)

            @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, disabled=True)
            async def previous(self, interaction: discord.Interaction, button: Button):
                if self.index > 0:
                    self.index -= 1
                    await self.update_message(interaction)

            @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
            async def next(self, interaction: discord.Interaction, button: Button):
                if self.index < len(self.pages) - 1:
                    self.index += 1
                    await self.update_message(interaction)

        view = HelpView(pages)
        await ctx.send(embed=pages[0], view=view)
    
    @commands.command()
    async def info(self, ctx):
        # List of beta program server IDs
        beta_server_ids = utils.load_beta_servers()
        if ctx.guild and ctx.guild.id in beta_server_ids:
            custominfo = textwrap.dedent(f"""\
                # I am a multifunctional python Discord bot!
                - Status: Beta Program
                - Build: Celestra-beta
                - Version: **{variables.bot_info['version']}**-beta
                - Developer: th3_t1sm

                You are using the exclusive Beta Program build of the bot, codenamed Celestra.
                This version includes upcoming features and experimental changes.
                Thank you for helping test and improve the bot!
            """)
        else:
            custominfo = textwrap.dedent(f"""\
                # I am a multifunctional python Discord bot!
                - Status: Normal
                - Build: Elysia
                - Version: **{variables.bot_info['version']}**
                - Developper: th3_t1sm

                I am multifunctional discord bot created by th3_t1sm,
                This is just a python discord bot made with love.
            """)
        await ctx.send(custominfo)


    @commands.command(name="changelog")
    async def changelog(self, ctx):
        changelog = f"# Here is the changelog for the **{variables.bot_info['version']}**: {variables.bot_info['new_stuff']}"
        await ctx.send(changelog)


    @commands.command(name="analyse")
    async def analyse(self, ctx, member: typing.Optional[discord.Member] = None):
        """Analyse a user with all available data."""
        member = member or ctx.author  # Default to the command author if no member is mentioned

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
            value=member.joined_at.strftime("%d %B %Y, %H:%M:%S") if member.joined_at else "Unknown",
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


    @commands.command(name="levelcard")
    async def levelcard(self, ctx, member: typing.Optional[discord.Member] = None):
        """Show your (or another user's) level card as an image."""
        member = member or ctx.author
        user_id = member.id
        user_data = utils.get_user_data(user_id)
        level = user_data.get("level", 1)
        xp = user_data.get("xp", 0)
        coins = user_data.get("coins", 0)
        next_level_xp = (level + 1) * 100  # Example XP formula

        # Create image
        width, height = 600, 180
        card = Image.new("RGBA", (width, height), (30, 33, 36, 255))
        draw = ImageDraw.Draw(card)

        # Fonts (use default if custom not available)
        try:
            font_big = ImageFont.truetype("arial.ttf", 36)
            font_small = ImageFont.truetype("arial.ttf", 22)
        except:
            font_big = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Draw avatar
        avatar_asset = member.display_avatar.with_size(128)
        avatar_bytes = await avatar_asset.read()
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((128, 128))
        mask = Image.new("L", (128, 128), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 128, 128), fill=255)
        card.paste(avatar, (30, 26), mask)

        # Draw username and level
        draw.text((180, 30), f"{member.display_name}", font=font_big, fill=(255, 255, 255))
        draw.text((180, 75), f"Level: {level}", font=font_small, fill=(200, 200, 255))
        draw.text((180, 105), f"XP: {xp} / {next_level_xp}", font=font_small, fill=(200, 255, 200))
        draw.text((180, 135), f"Coins: {coins}", font=font_small, fill=(255, 255, 180))

        # Draw XP bar
        bar_x, bar_y, bar_w, bar_h = 180, 160, 370, 15
        draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], fill=(50, 50, 50))
        progress = min(xp / next_level_xp, 1.0)
        draw.rectangle([bar_x, bar_y, bar_x + int(bar_w * progress), bar_y + bar_h], fill=(80, 180, 255))

        # Save to buffer
        buf = io.BytesIO()
        card.save(buf, format="PNG")
        buf.seek(0)

        await ctx.send(file=discord.File(buf, filename="levelcard.png"))

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
