# --------------------- IMPORTS --------------------
import discord
from discord.ext import commands
from Ediscord import variables, utils
from discord.ext.commands import CommandOnCooldown
import random
from discord.ext.commands import cooldown
from discord.ext.commands import CooldownMapping
from discord.ext.commands import BucketType
from discord.ext.commands import CommandOnCooldown
from discord.ext.commands import cooldown
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import asyncio

# --------------------- MONEY COMMANDS --------------------
print("✅ - Money loaded.")
class Money(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="buylevel")
    async def buylevel(self, ctx, levels: int = 1):
        """Buy levels using coins."""
        if levels <= 0:
            await ctx.send("❌ You must buy at least 1 level.")
            return

        user_id = ctx.author.id
        user_data = utils.get_user_data(user_id)

        cost = levels * 50  # Cost per level
        if user_data["coins"] < cost:
            await ctx.send(f"❌ You don't have enough coins. You need {cost} coins to buy {levels} level(s).")
            return

        # Deduct coins and increase levels
        user_data["coins"] -= cost
        user_data["level"] += levels
        utils.update_user_data(user_id, "coins", user_data["coins"])
        utils.update_user_data(user_id, "level", user_data["level"])

        await ctx.send(f"🎉 {ctx.author.mention} bought {levels} level(s) for {cost} coins! You are now **Level {user_data['level']}**.")

    @commands.command(name="balance")
    async def balance(self, ctx):
        """Check your current balance."""
        user_id = ctx.author.id
        balance = utils.get_coins(user_id)
        await ctx.send(
            f"💰 {ctx.author.mention}, your current balance is **{balance} coins**."
        )


    @commands.command(name="daily")
    async def daily(self, ctx):
        """Claim your daily reward."""
        user_id = ctx.author.id
        if utils.can_claim_daily(user_id):
            reward = 100  # Amount of coins rewarded daily
            utils.update_coins(user_id, reward)
            utils.update_last_daily(user_id)
            await ctx.send(
                f"✅ {ctx.author.mention}, you have claimed your daily reward of **{reward} coins**!"
            )
        else:
            await ctx.send(
                f"❌ {ctx.author.mention}, you have already claimed your daily reward. Try again tomorrow!"
            )


    @commands.command(name="give")
    async def give(self, ctx, member: discord.Member, amount: int):
        """Give coins to another user."""
        if amount <= 0:
            await ctx.send("❌ You must give a positive amount of coins.")
            return

        giver_id = ctx.author.id
        receiver_id = member.id

        giver_balance = utils.get_coins(giver_id)
        if giver_balance < amount:
            await ctx.send(
                f"❌ {ctx.author.mention}, you don't have enough coins to give. Your balance is **{giver_balance} coins**."
            )
            return

        # Deduct from giver and add to receiver
        utils.update_coins(giver_id, -amount)
        utils.update_coins(receiver_id, amount)

        await ctx.send(
            f"✅ {ctx.author.mention} gave **{amount} coins** to {member.mention}."
        )


    @commands.command(name="steal")
    @commands.cooldown(1, 60, commands.BucketType.user)  # 1 use per 60 seconds per user
    async def steal(self, ctx, member: discord.Member):
        """Attempt to steal coins from another user."""
        if member == ctx.author:
            await ctx.send("❌ You cannot steal from yourself!")
            return

        thief_id = ctx.author.id
        victim_id = member.id

        victim_balance = utils.get_coins(victim_id)
        if victim_balance <= 0:
            await ctx.send(f"❌ {member.mention} has no coins to steal.")
            return

        # Determine the amount to steal (randomized)
        stolen_amount = random.randint(1, min(50, victim_balance))

        # Deduct from victim and add to thief
        utils.update_coins(victim_id, -stolen_amount)
        utils.update_coins(thief_id, stolen_amount)

        await ctx.send(
            f"💰 {ctx.author.mention} stole **{stolen_amount} coins** from {member.mention}!"
        )


    # Handle cooldown errors
    @steal.error
    async def steal_error(self, ctx, error):
        if isinstance(error, CommandOnCooldown):
            await ctx.send(
                f"⏳ This command is on cooldown. Try again in {round(error.retry_after, 2)} seconds."
            )
    @commands.command(name="gems")
    async def gems(self, ctx, member: discord.Member = None):
        """Check how many gems a user has collected."""
        member = member or ctx.author
        user_id = str(member.id)
        user_data = utils.get_user_data(user_id)
        gems_collected = user_data.get("gems", 0)
        await ctx.send(f"💎 {member.mention} has collected **{gems_collected} gems**!")


    # Bank commands
    @commands.command(name="deposit")
    async def deposit(self, ctx, amount: int):
        """Deposit coins into the bank."""
        if amount <= 0:
            await ctx.send("❌ You must deposit a positive amount of coins.")
            return

        user_id = ctx.author.id
        balance = utils.get_coins(user_id)

        if balance < amount:
            await ctx.send(
                f"❌ You don't have enough coins to deposit. Your balance is **{balance} coins**."
            )
            return

        # Deduct from user's balance and add to the bank
        utils.update_coins(user_id, -amount)
        utils.update_bank_balance(user_id, amount)

        await ctx.send(
            f"✅ {ctx.author.mention}, you deposited **{amount} coins** into the bank."
        )


    @commands.command(name="withdraw")
    async def withdraw(self, ctx, amount: int):
        """Withdraw coins from the bank."""
        if amount <= 0:
            await ctx.send("❌ You must withdraw a positive amount of coins.")
            return

        user_id = ctx.author.id
        bank_balance = utils.get_bank_balance(user_id)

        if bank_balance < amount:
            await ctx.send(
                f"❌ You don't have enough coins in the bank to withdraw. Your bank balance is **{bank_balance} coins**."
            )
            return

        # Deduct from the bank and add to user's balance
        utils.update_bank_balance(user_id, -amount)
        utils.update_coins(user_id, amount)

        await ctx.send(
            f"✅ {ctx.author.mention}, you withdrew **{amount} coins** from the bank."
        )


    @commands.command(name="bank")
    async def bank(self, ctx):
        """Check your bank balance."""
        user_id = ctx.author.id
        bank_balance = utils.get_bank_balance(user_id)
        await ctx.send(
            f"🏦 {ctx.author.mention}, your bank balance is **{bank_balance} coins**."
        )


    @commands.command(name="buygem")
    async def buygem(self, ctx):
        """Buy a gem for 250 coins."""
        user_id = ctx.author.id
        cost = 250  # Cost of one gem

        # Check if the user has enough coins
        balance = utils.get_coins(user_id)
        if balance < cost:
            await ctx.send(
                f"❌ {ctx.author.mention}, you don't have enough coins to buy a gem. You need **{cost} coins**, but you only have **{balance} coins**."
            )
            return

        # Deduct coins and add a gem
        utils.update_coins(user_id, -cost)
        utils.update_gems(user_id, 1)

        await ctx.send(
            f"✅ {ctx.author.mention}, you bought **1 gem** for **{cost} coins**! 💎"
        )
        
    @commands.command(name="opencrate")
    @cooldown(1, 30, BucketType.user)
    async def open_crate(self, ctx):
        """Open a crate to receive a random object."""
        # Select an object based on rarity
        rarities = [obj["rarity"] for obj in variables.crate_objects]
        rarity = random.choices(
            list(variables.rarity_weights.keys()), weights=variables.rarity_weights.values(), k=1
        )[0]
        possible_objects = [obj for obj in variables.crate_objects if obj["rarity"] == rarity]
        selected_object = random.choice(possible_objects)

        # Add the object to the user's inventory
        user_id = str(ctx.author.id)
        inventory = utils.load_inventory()
        if user_id not in inventory:
            inventory[user_id] = []
        inventory[user_id].append(selected_object)
        utils.save_inventory(inventory)

        # Update the user's crate count and check for trophies
        user_data = utils.get_user_data(ctx.author.id)
        user_data["crates_opened"] = user_data.get("crates_opened", 0) + 1
        utils.update_user_data(ctx.author.id, "crates_opened", user_data["crates_opened"])
        utils.check_trophy_goals(
            ctx.author.id, ctx.channel
        )  # Pass the channel as the second argument

        # Notify the user
        await ctx.send(
            f"🎉 {ctx.author.mention}, you opened a crate and received a **{selected_object['name']}**! "
            f"(Rarity: {selected_object['rarity']})"
        )


    @commands.command(name="exchange")
    async def exchange(self, ctx, *, object_name: str):
        """Exchange an object for coins or gems."""
        user_id = str(ctx.author.id)
        inventory = utils.load_inventory()

        # Check if the user owns the object
        if user_id not in inventory or not any(
            obj["name"].lower() == object_name.lower() for obj in inventory[user_id]
        ):
            await ctx.send(
                f"❌ {ctx.author.mention}, you do not own an object named **{object_name}**."
            )
            return

        # Find the object in the user's inventory
        for obj in inventory[user_id]:
            if obj["name"].lower() == object_name.lower():
                selected_object = obj
                break

        # Exchange the object for coins or gems
        if "coins" in selected_object["value"]:
            utils.update_coins(user_id, selected_object["value"]["coins"])
            await ctx.send(
                f"✅ {ctx.author.mention}, you exchanged **{selected_object['name']}** for "
                f"**{selected_object['value']['coins']} coins**!"
            )
        elif "gems" in selected_object["value"]:
            utils.update_gems(user_id, selected_object["value"]["gems"])
            await ctx.send(
                f"✅ {ctx.author.mention}, you exchanged **{selected_object['name']}** for "
                f"**{selected_object['value']['gems']} gems**!"
            )

        # Remove the object from the user's inventory
        inventory[user_id].remove(selected_object)
        utils.save_inventory(inventory)


    @commands.command(name="inventory")
    async def inventory(self, ctx):
        """Check your inventory."""
        user_id = str(ctx.author.id)
        inventory = utils.load_inventory()

        if user_id not in inventory or not inventory[user_id]:
            await ctx.send(f"📦 {ctx.author.mention}, your inventory is empty.")
            return

        # Display the user's inventory
        embed = discord.Embed(
            title=f"{ctx.author.name}'s Inventory",
            description="Here are the items you own:",
            color=discord.Color.blue(),
        )
        for obj in inventory[user_id]:
            # Safely get the value (either coins or gems)
            value = obj["value"].get("coins", obj["value"].get("gems", "Unknown"))
            value_type = "coins" if "coins" in obj["value"] else "gems"
            embed.add_field(
                name=obj["name"],
                value=f"Rarity: {obj['rarity']} | Value: {value} {value_type}",
                inline=False,
            )

        await ctx.send(embed=embed)


    @commands.command(name="trophies")
    async def display_trophies(self, ctx):
        """Display the user's trophies."""
        user_id = str(ctx.author.id)
        user_trophies = variables.trophy_data.get(user_id, [])

        # Create the base image
        base = Image.new("RGBA", (800, 400), (30, 30, 30))  # Dark background
        draw = ImageDraw.Draw(base)

        # Add a title
        font = ImageFont.truetype("arial.ttf", 40)
        draw.text(
            (20, 20), f"{ctx.author.name}'s Trophies", fill=(255, 255, 255), font=font
        )

        # Add trophy icons
        x, y = 50, 100
        for trophy_id, trophy in variables.trophies.items():
            icon_path = (
                trophy["icon"]
                if trophy_id in user_trophies
                else "icons/trophies/placeholder.png"
            )
            try:
                icon = (
                    Image.open(icon_path).convert("RGBA").resize((100, 100))
                )  # Ensure the image has an alpha channel
                base.paste(icon, (x, y), icon)  # Paste the icon with transparency
            except FileNotFoundError:
                await ctx.send(
                    f"❌ Missing file: `{icon_path}`. Please ensure the file exists."
                )
                return
            except Exception as e:
                await ctx.send(f"❌ An error occurred while processing `{icon_path}`: {e}")
                return

            draw.text(
                (x, y + 110),
                trophy["name"],
                fill=(255, 255, 255),
                font=ImageFont.truetype("arial.ttf", 20),
            )
            x += 150
            if x > 650:
                x = 50
                y += 150

        # Save the image to a BytesIO object
        buffer = BytesIO()
        base.save(buffer, format="PNG")
        buffer.seek(0)

        # Send the image
        await ctx.send(file=discord.File(fp=buffer, filename="trophies.png"))


    @commands.command(name="sell")
    async def sell(self, ctx):
        """Sell everything in your inventory for coins or gems."""
        user_id = str(ctx.author.id)
        inventory = utils.load_inventory()

        # Check if the user has items in their inventory
        if user_id not in inventory or not inventory[user_id]:
            await ctx.send(
                f"📦 {ctx.author.mention}, your inventory is empty. Nothing to sell."
            )
            return

        # Calculate the total value of the inventory
        total_coins = sum(obj["value"].get("coins", 0) for obj in inventory[user_id])
        total_gems = sum(obj["value"].get("gems", 0) for obj in inventory[user_id])

        # Confirmation message
        confirmation_message = await ctx.send(
            f"⚠️ {ctx.author.mention}, are you sure you want to sell everything in your inventory?\n"
            f"You will receive **{total_coins} coins** and **{total_gems} gems**.\n"
            f"Type `yes` to confirm or `no` to cancel."
        )

        def check(m):
            return (
                m.author == ctx.author
                and m.channel == ctx.channel
                and m.content.lower() in ["yes", "no"]
            )

        try:
            response = await commands.wait_for("message", check=check, timeout=30.0)
            if response.content.lower() == "no":
                await ctx.send("❌ Sale canceled. Your inventory remains untouched.")
                return
            elif response.content.lower() == "yes":
                # Add the coins and gems to the user's balance
                utils.update_coins(user_id, total_coins)
                utils.update_gems(user_id, total_gems)

                # Clear the user's inventory
                inventory[user_id] = []
                utils.save_inventory(inventory)

                await ctx.send(
                    f"✅ {ctx.author.mention}, you sold everything in your inventory and received "
                    f"**{total_coins} coins** and **{total_gems} gems**!"
                )
        except asyncio.TimeoutError:
            await ctx.send("⏰ Sale timed out. Your inventory remains untouched.")
    
    @commands.command(name="exchange_gems")
    async def exchange_gems(self, ctx, gems: int):
        """Exchange gems for coins."""
        if gems <= 0:
            await ctx.send("❌ You must exchange at least 1 gem.")
            return

        user_id = ctx.author.id
        user_data = utils.get_user_data(user_id)

        # Check if the user has enough gems
        if user_data["gems"] < gems:
            await ctx.send(
                f"❌ {ctx.author.mention}, you don't have enough gems to exchange. You need **{gems} gems**, but you only have **{user_data['gems']} gems**."
            )
            return

        # Define the conversion rate
        conversion_rate = 250  # 1 gem = 250 coins
        coins_earned = gems * conversion_rate

        # Deduct gems and add coins
        user_data["gems"] -= gems
        user_data["coins"] += coins_earned
        utils.update_user_data(user_id, "gems", user_data["gems"])
        utils.update_user_data(user_id, "coins", user_data["coins"])

        await ctx.send(
            f"✅ {ctx.author.mention}, you exchanged **{gems} gems** for **{coins_earned} coins**!"
        )
    
    @commands.command(name="trade")
    async def trade(
        ctx,
        member: discord.Member,
        trade_type: str,
        amount_or_item: str,
        *,
        item_name: str = None,
        self
    ):
        """
        Trade items, gems, or coins with another user.
        Usage:
        - ?trade @user coins 100
        - ?trade @user gems 5
        - ?trade @user item "Item Name"
        """
        if member == ctx.author:
            await ctx.send("❌ You cannot trade with yourself!")
            return

        trade_type = trade_type.lower()
        user_id = str(ctx.author.id)
        target_id = str(member.id)

        # Trade coins
        if trade_type == "coins":
            try:
                amount = int(amount_or_item)
                if amount <= 0:
                    await ctx.send("❌ Amount must be positive.")
                    return
            except ValueError:
                await ctx.send("❌ Invalid amount.")
                return

            user_balance = utils.get_coins(user_id)
            if user_balance < amount:
                await ctx.send(
                    f"❌ You don't have enough coins. Your balance: {user_balance}"
                )
                return

            await ctx.send(
                f"🔄 {member.mention}, do you accept to receive **{amount} coins** from {ctx.author.mention}? Type `accept` to confirm."
            )

            def check(m):
                return (
                    m.author == member
                    and m.channel == ctx.channel
                    and m.content.lower() == "accept"
                )

            try:
                await commands.wait_for("message", check=check, timeout=30)
                utils.update_coins(user_id, -amount)
                utils.update_coins(target_id, amount)
                await ctx.send(
                    f"✅ Trade complete! {ctx.author.mention} sent **{amount} coins** to {member.mention}."
                )
            except asyncio.TimeoutError:
                await ctx.send("❌ Trade cancelled (no response).")
            return

        # Trade gems
        elif trade_type == "gems":
            try:
                amount = int(amount_or_item)
                if amount <= 0:
                    await ctx.send("❌ Amount must be positive.")
                    return
            except ValueError:
                await ctx.send("❌ Invalid amount.")
                return

            user_data = utils.get_user_data(user_id)
            if user_data.get("gems", 0) < amount:
                await ctx.send(
                    f"❌ You don't have enough gems. Your gems: {user_data.get('gems', 0)}"
                )
                return

            await ctx.send(
                f"🔄 {member.mention}, do you accept to receive **{amount} gems** from {ctx.author.mention}? Type `accept` to confirm."
            )

            def check(m):
                return (
                    m.author == member
                    and m.channel == ctx.channel
                    and m.content.lower() == "accept"
                )

            try:
                await commands.wait_for("message", check=check, timeout=30)
                utils.update_gems(user_id, -amount)
                utils.update_gems(target_id, amount)
                await ctx.send(
                    f"✅ Trade complete! {ctx.author.mention} sent **{amount} gems** to {member.mention}."
                )
            except asyncio.TimeoutError:
                await ctx.send("❌ Trade cancelled (no response).")
            return

        # Trade items
        elif trade_type == "item":
            if not item_name:
                item_name = amount_or_item
            item_name = item_name.strip('"').strip("'")
            inventory = utils.load_inventory()
            if user_id not in inventory or not any(
                obj["name"].lower() == item_name.lower() for obj in inventory[user_id]
            ):
                await ctx.send(f"❌ You do not own an item named **{item_name}**.")
                return

            await ctx.send(
                f"🔄 {member.mention}, do you accept to receive the item **{item_name}** from {ctx.author.mention}? Type `accept` to confirm."
            )

            def check(m):
                return (
                    m.author == member
                    and m.channel == ctx.channel
                    and m.content.lower() == "accept"
                )

            try:
                await commands.wait_for("message", check=check, timeout=30)
                # Remove item from sender
                for obj in inventory[user_id]:
                    if obj["name"].lower() == item_name.lower():
                        item_obj = obj
                        break
                inventory[user_id].remove(item_obj)
                # Add item to receiver
                if target_id not in inventory:
                    inventory[target_id] = []
                inventory[target_id].append(item_obj)
                utils.save_inventory(inventory)
                await ctx.send(
                    f"✅ Trade complete! {ctx.author.mention} sent **{item_name}** to {member.mention}."
                )
            except asyncio.TimeoutError:
                await ctx.send("❌ Trade cancelled (no response).")
            return

        else:
            await ctx.send("❌ Invalid trade type. Use `coins`, `gems`, or `item`.")


async def setup(bot):
    await bot.add_cog(Money(bot))