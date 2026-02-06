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
from discord import app_commands
import typing
import time

# --------------------- MONEY COMMANDS --------------------
print("✅ - Money loaded.")

# Shop items definition
SHOP_ITEMS = {
    "xp_boost": {
        "name": "XP Boost (1 Hour)", 
        "description": "Doubles XP gain for 1 hour", 
        "cost": 500, 
        "currency": "coins", 
        "effect": "xp_multiplier", 
        "multiplier": 2, 
        "duration": 3600  # seconds
    },
    "gem_pack": {
        "name": "Gem Pack", 
        "description": "Receive 5 gems instantly", 
        "cost": 1000, 
        "currency": "coins", 
        "effect": "add_gems", 
        "amount": 5
    },
    "level_skip": {
        "name": "Level Skip", 
        "description": "Gain 1 level instantly", 
        "cost": 1000, 
        "currency": "coins", 
        "effect": "add_level", 
        "amount": 1
    },
    "coin_boost": {
        "name": "Coin Boost (1 Hour)", 
        "description": "Doubles coin rewards for 1 hour", 
        "cost": 750, 
        "currency": "coins", 
        "effect": "coin_multiplier", 
        "multiplier": 2, 
        "duration": 3600
    },
    "super_coin_boost": {
        "name": "Mega Coin Boost!! (24 hours)",
        "description": "TRIPLES coin rewards for 24 hours!",
        "cost": 10000,
        "currency": "coins",
        "effect": "coin_multiplier",
        "multiplier": 3,
        "duration": 360000
    },
    "key": {
        "name": "Crate Key", 
        "description": "A key to open crates", 
        "cost": 50, 
        "currency": "coins", 
        "effect": "add_keys", 
        "amount": 1
    },
    "multi_key": {
        "name": "5 Crate Keys", 
        "description": "5 keys to open crates", 
        "cost": 200, 
        "currency": "coins", 
        "effect": "add_keys", 
        "amount": 5
    }
}
class Money(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your current balance.")
    async def balance(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        balance = utils.get_coins(user_id)
        user_data = utils.get_user_data(user_id)
        keys = user_data.get("keys", 0)
        await interaction.response.send_message(
            f"# 💰 {interaction.user.mention}, your current balance is **{balance} coins** and **{keys} keys**.\n-# Try running `/daily`, `/opencrate` to get more money and keys!"
        )


    @app_commands.command(name="daily", description="Claim your daily reward.")
    async def daily(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if utils.can_claim_daily(user_id):
            reward = random.randint(100, 1000)
            utils.update_coins(user_id, reward)
            utils.update_last_daily(user_id)
            message = f"✅ {interaction.user.mention}, you have claimed your daily reward of **{reward} coins**!"
            if random.randint(1, 10) == 1:
                user_data = utils.get_user_data(user_id)
                user_data["keys"] = user_data.get("keys", 0) + 1
                utils.update_user_data(user_id, "keys", user_data["keys"])
                message += f"\n🎁 Bonus! You also received a **crate key**!"
            await interaction.response.send_message(message)
        else:
            await interaction.response.send_message(
                f"❌ {interaction.user.mention}, you have already claimed your daily reward. Try again tomorrow!\n-# {utils.little_text()}"
            )

    @app_commands.command(name="steal", description="Attempt to steal coins from another user.")
    @app_commands.describe(member="The member to steal from")
    async def steal(self, interaction: discord.Interaction, member: discord.Member):
        if member == interaction.user:
            await interaction.response.send_message("# ❌ You cannot steal from yourself!\n-# Try using another member!", ephemeral=True)
            return
        thief_id = interaction.user.id
        victim_id = member.id
        victim_balance = utils.get_coins(victim_id)
        if victim_balance <= 0:
            await interaction.response.send_message(f"# ❌ {member.mention} has no coins to steal.\n-# Damn he's actually broke..\n-# {utils.little_text()}", ephemeral=True)
            return
        stolen_amount = random.randint(1, min(50, victim_balance))
        utils.update_coins(victim_id, -stolen_amount)
        utils.update_coins(thief_id, stolen_amount)
        await interaction.response.send_message(
            f"💰 {interaction.user.mention} stole **{stolen_amount} coins** from {member.mention}!"
        )

    @app_commands.command(name="gems", description="Check how many gems a user has collected.")
    @app_commands.describe(member="The member to check (optional)")
    async def gems(self, interaction: discord.Interaction, member: typing.Optional[discord.Member] = None):
        member = member or interaction.user
        user_id = str(member.id)
        user_data = utils.get_user_data(user_id)
        gems_collected = user_data.get("gems", 0)
        await interaction.response.send_message(f"💎 {member.mention} has collected **{gems_collected}** gems!")

    @app_commands.command(name="keys", description="Check how many keys a user has.")
    @app_commands.describe(member="The member to check (optional)")
    async def keys(self, interaction: discord.Interaction, member: typing.Optional[discord.Member] = None):
        member = member or interaction.user
        user_id = str(member.id)
        user_data = utils.get_user_data(user_id)
        keys_collected = user_data.get("keys", 0)
        await interaction.response.send_message(f"🔑 {member.mention} has **{keys_collected}** crate keys!")


    # Bank commands
    @app_commands.command(name="deposit", description="Deposit coins into the bank.")
    @app_commands.describe(amount="Amount of coins to deposit")
    async def deposit(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            await interaction.response.send_message(f"# ❌ You must specify a positive amount of coins.\n-# {utils.little_text()}", ephemeral=True)
            return
        user_id = interaction.user.id
        balance = utils.get_coins(user_id)
        if balance < amount:
            await interaction.response.send_message(
                f"# ❌ You don't have enough coins to deposit\nYour balance is **{balance}** coins.", ephemeral=True
            )
            return
        utils.update_coins(user_id, -amount)
        utils.update_bank_balance(user_id, amount)
        await interaction.response.send_message(
            f"✅ {interaction.user.mention}, you deposited **{amount}** coins into the bank."
        )


    @app_commands.command(name="withdraw", description="Withdraw coins from the bank.")
    @app_commands.describe(amount="Amount of coins to withdraw")
    async def withdraw(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            await interaction.response.send_message(f"# ❌ You must specify a positive amount of coins.\n-# {utils.little_text()}", ephemeral=True)
            return
        user_id = interaction.user.id
        bank_balance = utils.get_bank_balance(user_id)
        if bank_balance < amount:
            await interaction.response.send_message(
                f"# ❌ You don't have enough coins in the bank to withdraw\nYour bank balance is **{bank_balance} coins**.", ephemeral=True
            )
            return
        utils.update_bank_balance(user_id, -amount)
        utils.update_coins(user_id, amount)
        await interaction.response.send_message(
            f"✅ {interaction.user.mention}, you withdrew **{amount} coins** from the bank."
        )


    @app_commands.command(name="bank", description="Check your bank balance.")
    async def bank(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        bank_balance = utils.get_bank_balance(user_id)
        await interaction.response.send_message(
            f"🏦 {interaction.user.mention}, your bank balance is **{bank_balance} coins**."
        )


    @app_commands.command(name="exchange_gems", description="Exchange gems for coins (250 coins per gem).")
    @app_commands.describe(amount="Amount of gems to exchange")
    async def exchange_gems_for_coins(self, interaction: discord.Interaction, amount: int):
        if amount is None or amount <= 0:
            await interaction.response.send_message("❌ Please specify how many gems to exchange. Usage: `/exchange_gems <amount>`", ephemeral=True)
            return
        user_id = interaction.user.id
        user_data = utils.get_user_data(user_id)
        if user_data.get("gems", 0) < amount:
            await interaction.response.send_message(
                f"❌ You don't have enough gems to exchange. You need **{amount} gems**, but you only have **{user_data.get('gems', 0)} gems**.", ephemeral=True
            )
            return
        conversion_rate = 250
        coins_earned = amount * conversion_rate
        user_data["gems"] -= amount
        user_data["coins"] += coins_earned
        utils.update_user_data(user_id, "gems", user_data["gems"])
        utils.update_user_data(user_id, "coins", user_data["coins"])
        await interaction.response.send_message(
            f"✅ {interaction.user.mention}, you exchanged **{amount} gems** for **{coins_earned} coins**!"
        )
    @app_commands.command(name="shop", description="View and buy items from the shop.")
    @app_commands.describe(item_name="Name of the item to buy (optional)")
    async def shop(self, interaction: discord.Interaction, item_name: typing.Optional[str] = None):
        if item_name is None:
            embed = discord.Embed(
                title="🛒 Bot Shop",
                description="Welcome to the shop! Use `/shop <item>` to purchase.",
                color=discord.Color.green()
            )
            for key, item in SHOP_ITEMS.items():
                embed.add_field(
                    name=f"{item['name']} - {item['cost']} {item['currency']}",
                    value=item['description'],
                    inline=False
                )
            await interaction.response.send_message(embed=embed)
            return
        item_key = None
        for key, item in SHOP_ITEMS.items():
            if item_name.lower() in item['name'].lower():
                item_key = key
                break
        if not item_key:
            await interaction.response.send_message("❌ Item not found. Use `/shop` to see available items.", ephemeral=True)
            return
        item = SHOP_ITEMS[item_key]
        user_id = interaction.user.id
        user_data = utils.get_user_data(user_id)
        if item['currency'] == 'coins':
            balance = user_data.get('coins', 0)
        elif item['currency'] == 'gems':
            balance = user_data.get('gems', 0)
        else:
            await interaction.response.send_message("❌ Invalid currency.", ephemeral=True)
            return
        if balance < item['cost']:
            await interaction.response.send_message(f"❌ You don't have enough {item['currency']}. You need {item['cost']}, but you have {balance}.", ephemeral=True)
            return
        if item['currency'] == 'coins':
            user_data['coins'] -= item['cost']
            utils.update_user_data(user_id, 'coins', user_data['coins'])
        elif item['currency'] == 'gems':
            user_data['gems'] -= item['cost']
            utils.update_user_data(user_id, 'gems', user_data['gems'])
        if item['effect'] == 'add_gems':
            user_data['gems'] = user_data.get('gems', 0) + item['amount']
            utils.update_user_data(user_id, 'gems', user_data['gems'])
            await interaction.response.send_message(f"✅ Purchased {item['name']}! You received {item['amount']} gems.")
        elif item['effect'] == 'add_level':
            user_data['level'] = user_data.get('level', 1) + item['amount']
            utils.update_user_data(user_id, 'level', user_data['level'])
            await interaction.response.send_message(f"✅ Purchased {item['name']}! You gained {item['amount']} level(s).")
        elif item['effect'] == 'add_keys':
            user_data['keys'] = user_data.get('keys', 0) + item['amount']
            utils.update_user_data(user_id, 'keys', user_data['keys'])
            await interaction.response.send_message(f"✅ Purchased {item['name']}! You received {item['amount']} key(s).")
        elif item['effect'] in ['xp_multiplier', 'coin_multiplier']:
            boost_end = time.time() + item['duration']
            user_data[f"{item['effect']}_end"] = boost_end
            user_data[f"{item['effect']}_value"] = item['multiplier']
            utils.update_user_data(user_id, f"{item['effect']}_end", boost_end)
            utils.update_user_data(user_id, f"{item['effect']}_value", item['multiplier'])
            await interaction.response.send_message(f"✅ Purchased {item['name']}! {item['description']} is now active.")
    @app_commands.command(name="opencrate", description="Open a crate to receive a random object. Costs 1 key.")
    async def open_crate(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        user_data = utils.get_user_data(user_id)
        if user_data.get("keys", 0) < 1:
            await interaction.response.send_message(f"# ❌ You need at least 1 key to open a crate.\n-# You have {user_data.get('keys', 0)} keys.", ephemeral=True)
            return
        user_data["keys"] -= 1
        utils.update_user_data(user_id, "keys", user_data["keys"])
        rarities = [obj["rarity"] for obj in variables.crate_objects]
        rarity = random.choices(
            list(variables.rarity_weights.keys()), weights=list(variables.rarity_weights.values()), k=1
        )[0]
        possible_objects = [obj for obj in variables.crate_objects if obj["rarity"] == rarity]
        selected_object = random.choice(possible_objects)
        user_id_str = str(interaction.user.id)
        inventory = utils.load_inventory()
        if user_id_str not in inventory:
            inventory[user_id_str] = []
        inventory[user_id_str].append(selected_object)
        utils.save_inventory(inventory)
        user_data["crates_opened"] = user_data.get("crates_opened", 0) + 1
        utils.update_user_data(interaction.user.id, "crates_opened", user_data["crates_opened"])
        # For trophy goals, pass the channel object (interaction.channel)
        utils.check_trophy_goals(
            interaction.user.id, interaction.channel
        )
        wow = "WOW!!" if selected_object['rarity'] == "Legendary" else ""
        wow = "# WHAT?!?" if selected_object['rarity'] == "Transcendent" else wow
        if selected_object['rarity'] == "Transcendent":
            await interaction.response.send_message(
                f"# OMG!!!!"
                f"# 🎉 {interaction.user.mention}, YOU OPENED A CRATE AND RECEIVED A **{selected_object['name']}**!\n"
                f"-# (Rarity: {selected_object['rarity']} {wow})"
            )
        else:
            await interaction.response.send_message(
                f"# 🎉 {interaction.user.mention}, you opened a crate and received a **{selected_object['name']}**!\n"
                f"-# (Rarity: {selected_object['rarity']} {wow})"
            )
        if random.random() < 0.5:
            user_data["keys"] = user_data.get("keys", 0) + 1
            utils.update_user_data(user_id, "keys", user_data["keys"])
            await interaction.followup.send("🔑 Bonus: You found an extra key!")

    @app_commands.command(name="inventory", description="Check your inventory.")
    async def inventory(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        inventory = utils.load_inventory()
        if user_id not in inventory or not inventory[user_id]:
            await interaction.response.send_message(f"# 📦❔ {interaction.user.mention}, your inventory is empty.\n-# Try running /opencrate to get items!", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"{interaction.user.name}'s Inventory",
            description="Here are the items you own:",
            color=discord.Color.blue(),
        )
        for obj in inventory[user_id]:
            value = obj["value"].get("coins", obj["value"].get("gems", "Unknown"))
            value_type = "coins" if "coins" in obj["value"] else "gems"
            embed.add_field(
                name=obj["name"],
                value=f"Rarity: {obj['rarity']} | Value: {value} {value_type}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="sell", description="Sell everything in your inventory for coins or gems.")
    async def sell(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        inventory = utils.load_inventory()
        if user_id not in inventory or not inventory[user_id]:
            await interaction.response.send_message(
                f"# 📦❔ {interaction.user.mention}, your inventory is empty.\n-# Try running /opencrate to get items!", ephemeral=True
            )
            return
        total_coins = sum(obj["value"].get("coins", 0) for obj in inventory[user_id])
        total_gems = sum(obj["value"].get("gems", 0) for obj in inventory[user_id])
        # Confirm via button interaction
        view = discord.ui.View()
        async def confirm_callback(interact):
            utils.update_coins(user_id, total_coins)
            utils.update_gems(user_id, total_gems)
            inventory[user_id] = []
            utils.save_inventory(inventory)
            await interact.response.edit_message(content=f"# ✅ {interaction.user.mention}, you sold everything in your inventory and\nreceived: **{total_coins} coins** and **{total_gems} gems**!", view=None)
        async def cancel_callback(interact):
            await interact.response.edit_message(content=f"# ❌ Sale canceled.\nYour inventory remains untouched.\n{utils.little_text()}", view=None)
        view.add_item(discord.ui.Button(label="Yes", style=discord.ButtonStyle.success, custom_id="yes"))
        view.add_item(discord.ui.Button(label="No", style=discord.ButtonStyle.danger, custom_id="no"))
        async def on_button(interact):
            if interact.data["custom_id"] == "yes":
                await confirm_callback(interact)
            else:
                await cancel_callback(interact)
        view.on_timeout = lambda: None
        view.interaction_check = lambda i: i.user.id == interaction.user.id
        view.on_button_click = on_button
        await interaction.response.send_message(
            f"# ⚠️ {interaction.user.mention}, are you sure you want to sell everything in your inventory?\nYou will receive **{total_coins} coins** and **{total_gems} gems**.",
            view=view, ephemeral=True
        )
    
    @app_commands.command(name="trade", description="Trade items, gems, or coins with another user.")
    @app_commands.describe(member="The member to trade with", trade_type="Type of trade: coins, gems, or item", amount_or_item="Amount or item name", item_name="Item name (optional, for item trades)")
    async def trade(self, interaction: discord.Interaction, member: discord.Member, trade_type: str, amount_or_item: str, item_name: typing.Optional[str] = None):
        if member == interaction.user:
            await interaction.response.send_message("❌ You cannot trade with yourself!", ephemeral=True)
            return
        trade_type = trade_type.lower()
        user_id = str(interaction.user.id)
        target_id = str(member.id)
        if trade_type == "coins":
            try:
                amount = int(amount_or_item)
                if amount <= 0:
                    await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ Invalid amount.", ephemeral=True)
                return
            user_balance = utils.get_coins(user_id)
            if user_balance < amount:
                await interaction.response.send_message(
                    f"❌ You don't have enough coins. Your balance: {user_balance}", ephemeral=True
                )
                return
            await interaction.response.send_message(
                f"🔄 {member.mention}, do you accept to receive **{amount} coins** from {interaction.user.mention}? Use `/accept_trade` to confirm.", ephemeral=False
            )
            # You must implement a /accept_trade command for the recipient to confirm
            # On confirmation, update balances as in the original code
            return
        elif trade_type == "gems":
            try:
                amount = int(amount_or_item)
                if amount <= 0:
                    await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ Invalid amount.", ephemeral=True)
                return
            user_data = utils.get_user_data(user_id)
            if user_data.get("gems", 0) < amount:
                await interaction.response.send_message(
                    f"❌ You don't have enough gems. Your gems: {user_data.get('gems', 0)}", ephemeral=True
                )
                return
            await interaction.response.send_message(
                f"🔄 {member.mention}, do you accept to receive **{amount} gems** from {interaction.user.mention}? Use `/accept_trade` to confirm.", ephemeral=False
            )
            # You must implement a /accept_trade command for the recipient to confirm
            return
        elif trade_type == "item":
            if not item_name:
                item_name = amount_or_item
            item_name = item_name.strip('"').strip("'")
            inventory = utils.load_inventory()
            if user_id not in inventory or not any(
                obj["name"].lower() == item_name.lower() for obj in inventory[user_id]
            ):
                await interaction.response.send_message(f"❌ You do not own an item named **{item_name}**.", ephemeral=True)
                return
            await interaction.response.send_message(
                f"🔄 {member.mention}, do you accept to receive the item **{item_name}** from {interaction.user.mention}? Use `/accept_trade` to confirm.", ephemeral=False
            )
            # You must implement a /accept_trade command for the recipient to confirm
            return
        else:
            await interaction.response.send_message("❌ Invalid trade type. Use `coins`, `gems`, or `item`.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Money(bot))