# --------------------- IMPORTS --------------------
from Ediscord import utils, variables
import discord
from discord.ext import commands
import discord.ext.commands
import time
import logging
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import difflib
import asyncio
import random


# --------------------- EVENTS --------------------
print("✅ - Events loaded.")
class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command(self, ctx):
        # DM the owner on every command
        owner = (await self.bot.application_info()).owner
        try:
            await owner.send(
                f"🔔 Command `{ctx.command}` used by {ctx.author} in {ctx.guild.name}#{ctx.channel.name}:\n> {ctx.message.content}"
            )
        except Exception as e:
            print(f"Failed to DM owner: {e}")
        if variables.is_sleeping:
            return

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        logs_channel = utils.get_logs_channel(ctx.guild)
        if logs_channel:
            await logs_channel.send(
                f"{ctx.author} executed `{ctx.command}` in {ctx.channel}."
            )
            logging.info(f"{ctx.author} executed `{ctx.command}` successfully.")

        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reactions for region roles and other commands."""
        try:
            if payload.user_id == self.bot.user.id:
                return

            data = utils.load_user_data()
            region_message_id = data.get("region_message_id")
            if region_message_id and payload.message_id == region_message_id:
                guild = commands.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)
                emoji_to_region = {
                    "🌍": "Africa",
                    "🌎": "Americas",
                    "🌏": "Asia",
                    "🇪🇺": "Europe",
                    "🇦🇺": "Oceania",
                }
                role_name = emoji_to_region.get(str(payload.emoji))
                if role_name:
                    role = discord.utils.get(guild.roles, name=role_name)
                    if not role:
                        role = await guild.create_role(name=role_name)
                    await member.add_roles(role)
                    await member.send(
                        f"✅ You have been given the **{role_name}** role."
                    )
                return
            
            rules_verify_message_id = data.get("rules_verify_message_id")
            if (
                rules_verify_message_id
                and payload.message_id == rules_verify_message_id
            ):
                guild = commands.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)
                if str(payload.emoji) == "🔵":
                    role_name = "「 Read and agreed to the rules 」🔵"
                    role = discord.utils.get(guild.roles, name=role_name)
                    if not role:
                        try:
                            role = await guild.create_role(name=role_name)
                            logging.info(
                                f"Role '{role_name}' created in guild '{guild.name}' (ID: {guild.id})."
                            )
                        except discord.Forbidden:
                            logging.error(
                                f"Insufficient permissions to create role '{role_name}' in guild '{guild.name}'."
                            )
                            await member.send(
                                "❌ I do not have permission to create the verification role. Please contact an administrator."
                            )
                            return
                        except Exception as e:
                            logging.error(f"Error creating role '{role_name}': {e}")
                            return

                    try:
                        await member.add_roles(role)
                        await member.send(
                            f"✅ You have been verified and given the role: **{role_name}**."
                        )
                        logging.info(
                            f"Role '{role_name}' assigned to {member.name}#{member.discriminator} (ID: {member.id})."
                        )

                        user_data = utils.load_user_data()
                        if str(member.id) not in user_data:
                            user_data[str(member.id)] = {
                                "xp": 0,
                                "level": 1,
                                "coins": 100,
                                "balance": 0,
                                "warnings": [],
                            }
                        user_data[str(member.id)]["verified"] = True
                        utils.save_user_data(user_data)
                    except discord.Forbidden:
                        logging.error(
                            f"Insufficient permissions to assign role '{role_name}' to {member.name}#{member.discriminator}."
                        )
                        await member.send(
                            "❌ I do not have permission to assign the verification role. Please contact an administrator."
                        )
                    except Exception as e:
                        logging.error(
                            f"Error assigning role '{role_name}' to {member.name}#{member.discriminator}: {e}"
                        )
                return

            colorrole_message_id = data.get("colorrole_message_id")
            if colorrole_message_id and payload.message_id == colorrole_message_id:
                guild = commands.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)
                emoji_to_color = {
                    "🔴": "Red",
                    "🟠": "Orange",
                    "🟡": "Yellow",
                    "🟢": "Green",
                    "🔵": "Blue",
                    "🟣": "Violet",
                    "⚪": "White",
                    "⚫": "Black",
                }
                role_name = emoji_to_color.get(str(payload.emoji))
                if role_name:
                    role = discord.utils.get(guild.roles, name=role_name)
                    if not role:
                        role = await guild.create_role(name=role_name)
                    await member.add_roles(role)
                    await member.send(
                        f"✅ You have been given the **{role_name}** role."
                    )
                return

            verify_message_id = data.get("verify_message_id")
            if not verify_message_id:
                logging.warning("Verification message ID not found in user data.")
                return

            if payload.message_id != verify_message_id:
                return

            if str(payload.emoji) == "✅":
                guild = commands.get_guild(payload.guild_id)
                if not guild:
                    logging.error(f"Guild not found for ID: {payload.guild_id}")
                    return

                member = guild.get_member(payload.user_id)
                if not member:
                    member = await guild.fetch_member(payload.user_id)
                    if not member:
                        logging.error(f"Member not found for ID: {payload.user_id}")
                        return

                role_name = ".・🍨︴Member ✰"
                role = discord.utils.get(guild.roles, name=role_name)
                if not role:
                    try:
                        role = await guild.create_role(name=role_name)
                        logging.info(
                            f"Role '{role_name}' created in guild '{guild.name}' (ID: {guild.id})."
                        )
                    except discord.Forbidden:
                        logging.error(
                            f"Insufficient permissions to create role '{role_name}' in guild '{guild.name}'."
                        )
                        await member.send(
                            "❌ I do not have permission to create the verification role. Please contact an administrator."
                        )
                        return
                    except Exception as e:
                        logging.error(f"Error creating role '{role_name}': {e}")
                        return

                try:
                    await member.add_roles(role)
                    await member.send(
                        f"✅ You have been verified and given the role: **{role_name}**."
                    )
                    logging.info(
                        f"Role '{role_name}' assigned to {member.name}#{member.discriminator} (ID: {member.id})."
                    )

                    user_data = utils.load_user_data()
                    if str(member.id) not in user_data:
                        user_data[str(member.id)] = {
                            "xp": 0,
                            "level": 1,
                            "coins": 100,
                            "balance": 0,
                            "warnings": [],
                        }
                    user_data[str(member.id)]["verified"] = True
                    utils.save_user_data(user_data)
                except discord.Forbidden:
                    logging.error(
                        f"Insufficient permissions to assign role '{role_name}' to {member.name}#{member.discriminator}."
                    )
                    await member.send(
                        "❌ I do not have permission to assign the verification role. Please contact an administrator."
                    )
                except Exception as e:
                    logging.error(
                        f"Error assigning role '{role_name}' to {member.name}#{member.discriminator}: {e}"
                    )

            chat_reviver_message_id = data.get("chat_reviver_message_id")
            if (
                chat_reviver_message_id
                and payload.message_id == chat_reviver_message_id
            ):
                guild = commands.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)
                if str(payload.emoji) == "🛠️":
                    role_name = "Chat Reviver"
                    role = discord.utils.get(guild.roles, name=role_name)
                    if not role:
                        try:
                            role = await guild.create_role(name=role_name)
                            logging.info(
                                f"Role '{role_name}' created in guild '{guild.name}' (ID: {guild.id})."
                            )
                        except discord.Forbidden:
                            logging.error(
                                f"Insufficient permissions to create role '{role_name}' in guild '{guild.name}'."
                            )
                            await member.send(
                                "❌ I do not have permission to create the Chat Reviver role. Please contact an administrator."
                            )
                            return
                        except Exception as e:
                            logging.error(f"Error creating role '{role_name}': {e}")
                            return
                    
                    try:
                        await member.add_roles(role)
                        await member.send(
                            f"✅ You have been given the **{role_name}** role."
                        )
                        logging.info(
                            f"Role '{role_name}' assigned to {member.name}#{member.discriminator} (ID: {member.id})."
                        )
                    except discord.Forbidden:
                        logging.error(
                            f"Insufficient permissions to assign role '{role_name}' to {member.name}#{member.discriminator}."
                        )
                        await member.send(
                            "❌ I do not have permission to assign the Chat Reviver role. Please contact an administrator."
                        )
                    except Exception as e:
                        logging.error(
                            f"Error assigning role '{role_name}' to {member.name}#{member.discriminator}: {e}"
                        )
                return

        except Exception as e:
            logging.error(f"Error in on_raw_reaction_add: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Event triggered when a user joins the server with a custom cat-themed welcome image."""
        try:
            logging.info(
                f"New member joined: {member.name}#{member.discriminator} (ID: {member.id})"
            )

            welcome_channel_name = "👋〢「welcome」"
            welcome_channel = discord.utils.get(
                member.guild.text_channels, name=welcome_channel_name
            )
            if not welcome_channel:
                logging.warning(
                    f"Welcome channel not found in guild: {member.guild.name} (ID: {member.guild.id})"
                )
                return

            avatar_url = (
                member.avatar.url if member.avatar else member.default_avatar.url
            )
            response = requests.get(avatar_url)
            if response.status_code != 200:
                logging.error(
                    f"Failed to fetch avatar for {member.name}#{member.discriminator}. HTTP Status: {response.status_code}"
                )
                return
            avatar = (
                Image.open(BytesIO(response.content)).convert("RGBA").resize((120, 120))
            )

            background_path = "assets/welcome/background.jpg"
            background = Image.open(background_path).convert("RGBA").resize((800, 400))

            border_path = "assets/welcome/border.png"
            border_img = (
                Image.open(border_path).convert("RGBA").resize((140, 140))
            )  

            avatar_pos = (60, 120)  
            base = Image.new("RGBA", (800, 400), (255, 255, 255, 255))
            base.paste(background, (0, 0))

            border_pos = (
                avatar_pos[0] - 10,
                avatar_pos[1] - 10,
            )  
            avatar_mask = Image.new("L", avatar.size, 0)
            mask_draw = ImageDraw.Draw(avatar_mask)
            mask_draw.ellipse((0, 0, avatar.size[0], avatar.size[1]), fill=255)
            base.paste(avatar, avatar_pos, avatar_mask)
            base.paste(border_img, border_pos, border_img)

            base.paste(border_img, border_pos, border_img)
            user_rect = (210, 160, 670, 210)

            font_path = "assets/impact.ttf"
            font_large = ImageFont.truetype(font_path, 70)
            font_small = ImageFont.truetype(font_path, 36)
            bubble_font = ImageFont.truetype(font_path, 24)

            draw = ImageDraw.Draw(base)

            def rounded_rectangle(draw, xy, radius, fill, outline, width):
                draw.rounded_rectangle(
                    xy, radius=radius, fill=fill, outline=outline, width=width
                )

            def draw_centered_text(draw, rect, text, font, fill):
                x1, y1, x2, y2 = rect
                w, h = draw.textbbox((0, 0), text, font=font)[2:]
                text_x = x1 + ((x2 - x1) - w) // 2
                text_y = y1 + ((y2 - y1) - h) // 2
                draw.text((text_x, text_y), text, font=font, fill=fill)

            def draw_centered_outlined_text(
                draw, rect, text, font, fill, outline, outline_width
            ):
                x1, y1, x2, y2 = rect
                w, h = draw.textbbox((0, 0), text, font=font)[2:]
                text_x = x1 + ((x2 - x1) - w) // 2
                text_y = y1 + ((y2 - y1) - h) // 2
                draw.text(
                    (text_x, text_y),
                    text,
                    font=font,
                    fill=fill,
                    stroke_width=outline_width,
                    stroke_fill=outline,
                )

            welcome_rect = (210, 60, 670, 140)
            draw_centered_outlined_text(
                draw,
                welcome_rect,
                "WELCOME!",
                font_large,
                (255, 255, 255),
                (0, 0, 0),
                4,
            )

            username = f"{member.name}  {member.discriminator}"

            bubble_text = "Welcome!"
            bubble_x, bubble_y = 670, 60
            bubble_w, bubble_h = 170, 50
            bubble_rect = (bubble_x, bubble_y, bubble_x + bubble_w, bubble_y + bubble_h)
            draw.rounded_rectangle(
                bubble_rect,
                radius=12,
                fill=(255, 255, 255, 230),
                outline=(0, 0, 0),
                width=3,
            )
            draw_centered_text(draw, bubble_rect, "Welcome!", bubble_font, (0, 0, 0))

            def add_rounded_corners(im, rad):
                circle = Image.new("L", (rad * 2, rad * 2), 0)
                draw_c = ImageDraw.Draw(circle)
                draw_c.ellipse((0, 0, rad * 2, rad * 2), fill=255)
                alpha = Image.new("L", im.size, 255)
                w, h = im.size
                alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
                alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
                alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
                alpha.paste(
                    circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad)
                )
                im.putalpha(alpha)
                return im

            base = add_rounded_corners(base, 30)

            buffer = BytesIO()
            base.save(buffer, format="PNG")
            buffer.seek(0)

            await welcome_channel.send(
                f"🎉 Welcome to the server, {member.mention}!",
                file=discord.File(fp=buffer, filename="welcome.png"),
            )
            logging.info(
                f"Welcome message sent for {member.name}#{member.discriminator} in {welcome_channel.name}."
            )
        except Exception as e:
            logging.error(
                f"Error in on_member_join for {member.name}#{member.discriminator}: {e}"
            )
            logs_channel = discord.utils.get(member.guild.text_channels, name="logs")
            if logs_channel:
                await logs_channel.send(
                    f"❌ An error occurred while welcoming {member.mention}: {e}"
                )
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Event triggered when a user leaves the server."""
        try:
            logging.info(
            f"Member left: {member.name}#{member.discriminator} (ID: {member.id})"
            )

            goodbye_channel_name = (
                "「💬」general-❯"  
            )
            goodbye_channel = discord.utils.get(
                member.guild.text_channels, name=goodbye_channel_name
            )
            if not goodbye_channel:
                logging.warning(
                    f"Goodbye channel not found in guild: {member.guild.name} (ID: {member.guild.id})"
                )
                return  

            avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
            response = requests.get(avatar_url)
            if response.status_code != 200:
                logging.error(
                    f"Failed to fetch avatar for {member.name}#{member.discriminator}. HTTP Status: {response.status_code}"
                )
                return
            avatar = Image.open(BytesIO(response.content)).convert("RGBA")

            # Load the background image
            background_path = "assets/welcome/background.jpg"  # Use the same background as the welcome image
            try:
                background = Image.open(background_path).convert("RGBA")
            except FileNotFoundError:
                logging.error(
                    f"Background image not found at {background_path}. Please ensure the file exists."
                )
                await goodbye_channel.send(
                    "❌ Background image for the goodbye card is missing. Please add it to `icons/welcome/background.jpg`."
                )
                return

            # Resize the background to fit the goodbye card dimensions
            background = background.resize((800, 400))

            # Create the base image
            base = Image.new("RGBA", (800, 400), (30, 30, 30, 0))  # Transparent background
            base.paste(background, (0, 0))  # Paste the background onto the base image

            # Draw the circular avatar
            avatar = avatar.resize((150, 150))  # Resize the avatar
            mask = Image.new("L", avatar.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, avatar.size[0], avatar.size[1]), fill=255)
            base.paste(avatar, (325, 50), mask)  # Center the avatar on the image

            # Add the "GOODBYE" text
            font_path = "fonts/impact.ttf"  # Replace with the path to your bold font file
            try:
                font_large = ImageFont.truetype(font_path, 80)  # Big and bold font
                font_small = ImageFont.truetype(font_path, 40)
            except OSError:
                await goodbye_channel.send(
                    "❌ Font file not found. Please ensure the font file exists."
                )
                return

            draw = ImageDraw.Draw(base)
            draw.text(
                (250, 220), "GOODBYE", font=font_large, fill=(255, 255, 255), align="center"
            )

            # Add the username below the "GOODBYE" text
            draw.text(
                (250, 300),
                member.name,
                font=font_small,
                fill=(255, 255, 255),
                align="center",
            )

            # Save the image to a BytesIO object
            buffer = BytesIO()
            base.save(buffer, format="PNG")
            buffer.seek(0)

            # Send the image in the goodbye channel
            await goodbye_channel.send(
                f"👋 Goodbye, {member.mention}. We will miss you!",
                file=discord.File(fp=buffer, filename="goodbye.png"),
            )
            logging.info(
                f"Goodbye message sent for {member.name}#{member.discriminator} in {goodbye_channel.name}."
            )
        except Exception as e:
            logging.error(
                f"Error in on_member_remove for {member.name}#{member.discriminator}: {e}"
            )
            # Optionally, send an error message to a logs channel
            logs_channel = utils.get_logs_channel(member.guild)
            if logs_channel:
                await logs_channel.send(
                    f"❌ An error occurred while saying goodbye to {member.mention}: {e}"
                )
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # Ignore messages starting with "??" or more
        if ctx.message.content.startswith("?") and ctx.message.content.count("?") > 1:
            return

        if isinstance(error, commands.CommandNotFound):
            # Get the command name the user tried to use
            attempted_command = ctx.message.content.split()[0][
                1:
            ]  # Remove the prefix (e.g., "?")

            # Dynamically get all command names and aliases
            all_commands = set()
            for cmd in self.bot.commands:
                all_commands.add(cmd.name)
                all_commands.update(cmd.aliases)
            # Remove hidden commands
            all_commands = {
                name
                for name in all_commands
                if not self.bot.get_command(name) or not self.bot.get_command(name).hidden
            }

            # Find the closest match to the attempted command
            closest_match = difflib.get_close_matches(
                attempted_command, all_commands, n=1, cutoff=0.6
        )

            if closest_match:
                await ctx.send(f"❌ Command not found. Did you mean: `{closest_match[0]}`?")
            else:
                await ctx.send(
                    "❌ Command not found. Use `?help` to see the list of available commands."
                )
        else:
            await ctx.send(f"An error occurred: {error}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        print(f"📩 Message received: {message.content} from {message.author}")
        """Handle all on_message events."""
        print(f"{variables.last_activity};{variables.last_activity_time}")
        guild_id = str(message.guild.id)
        limitations = utils.load_limitations()
        level = limitations.get(guild_id, 0)  # Default to no filtering if not set

        # Ignore bot's own messages
        if message.author.bot:
            return

        # Update the last activity time for the guild
        variables.last_activity[message.guild.id] = time.time()

        # Handle AFK users
        if message.author.id in variables.afk_users:
            del variables.afk_users[message.author.id]
            await message.channel.send(f"✅ Welcome back, {message.author.mention}!")
        for mention in message.mentions:
            if mention.id in variables.afk_users:
                await message.channel.send(
                    f"🔔 {mention.mention} is AFK: {variables.afk_users[mention.id]}"
                )

        # Handle XP system with custom cooldown
        user_id = message.author.id
        now = time.time()

        # Check if the user is on cooldown
        if user_id in variables.message_cooldowns:
            cooldown_end = variables.message_cooldowns[user_id]
            if now < cooldown_end:
                # User is still on cooldown, skip granting XP
                await commands.process_commands(message)
                return

        # Get the user's data
        user_data = utils.get_user_data(user_id)

        # Grant XP
        user_data["xp"] += 10
        xp_needed = user_data["level"] * 100  # XP needed to level up

        # Check for level up
        if user_data["xp"] >= xp_needed:
            user_data["xp"] -= xp_needed
            user_data["level"] += 1
            user_data["coins"] += 50  # Reward coins for leveling up

            # Determine rewards based on level
            coins_reward = 50  # Default coin reward
            gems_reward = 0  # Default gem reward
            if user_data["level"] >= 50:  # Special reward for Level 50+
                coins_reward = 100
                gems_reward = 5

            # Add rewards
            user_data["coins"] += coins_reward
            user_data["gems"] += gems_reward

            # Calculate bonus XP based on the level reached
            bonus_xp = user_data["level"] * 10  # Example: 10 XP per level
            user_data["xp"] += bonus_xp

            # Notify the user
            rewards_message = (
                f"🎉 {message.author.mention} leveled up to **Level {user_data['level']}**! "
                f"You earned **{coins_reward} coins** and **{bonus_xp} bonus XP**"
            )
            if gems_reward > 0:
                rewards_message += f", and **{gems_reward} gems**!"
            else:
                rewards_message += "!"

            await message.channel.send(rewards_message)

            # Assign level-based role
            await utils.assign_level_role(message.author, user_data["level"], message.channel)

        # Save updated user data
        utils.update_user_data(user_id, "xp", user_data["xp"])
        utils.update_user_data(user_id, "level", user_data["level"])
        utils.update_user_data(user_id, "coins", user_data["coins"])
        logging.info(
            f"User {message.author.name} (ID: {user_id}) gained 10 XP. Total XP: {user_data['xp']}."
        )

        user_id = str(message.author.id)
        data = utils.load_user_data()

        # Ensure the user exists in the data and initialize the "messages" key if not present
        if user_id not in data:
            data[user_id] = {
                "xp": 0,
                "level": 1,
                "coins": 100,
                "warnings": [],
                "messages": [],
            }
        elif "messages" not in data[user_id]:
            data[user_id]["messages"] = []

        # Track message timestamps
        current_time = time.time()
        data[user_id]["messages"].append(current_time)

        # Remove messages outside the time window
        data[user_id]["messages"] = [
            timestamp
            for timestamp in data[user_id]["messages"]
            if current_time - timestamp <= variables.TIME_WINDOW
        ]

        # Check if the user exceeds the spam threshold
        if len(data[user_id]["messages"]) > variables.SPAM_THRESHOLD:
            # Take action for spamming
            await message.channel.send(
                f"⚠️ {message.author.mention}, you are sending messages too quickly. Please slow down!"
            )
            data[user_id]["warnings"].append(
                {"reason": "Spamming", "timestamp": time.time().isoformat()}
            )

            # Optional: Mute the user temporarily
            mute_role = discord.utils.get(message.guild.roles, name="Muted")
            if not mute_role:
                mute_role = await message.guild.create_role(name="Muted")
                for channel in message.guild.channels:
                    await channel.set_permissions(
                        mute_role, send_messages=False, speak=False
                    )
            await message.author.add_roles(mute_role, reason="Spamming")
            await asyncio.sleep(10)  # Mute duration (10 seconds)
            await message.author.remove_roles(mute_role, reason="Mute expired")

            # 1% chance to spawn a gem reaction
            if random.randint(1, 200) == 1:
                gem_emoji = "💎"  # Gem emoji
                await message.add_reaction(gem_emoji)

                try:
                    # Wait for a user to react within 10 seconds
                    reaction, user = await commands.wait_for(
                        "reaction_add", timeout=5.0, check=utils.check
                    )

                    # Add the gem to the user's count in easter.json
                    user_id = str(user.id)
                    utils.update_gems(user_id, 1)

                    # Remove the reaction and notify the user
                    await message.clear_reaction(gem_emoji)
                    await message.channel.send(
                        f"💎 {user.mention} found a gem! Total gems: {variables.easter_data[user_id]['gems']}"
                    )
                except asyncio.TimeoutError:
                    # Remove the reaction if no one reacts within 10 seconds
                    await message.clear_reaction(gem_emoji)

        offensive_words = {
            1: ["nigga", "nigger", "Nigga", "Nigger", "NIGGA", "NIGGER"],
            2: [
                "nigga",
                "nigger",
                "Nigga",
                "Nigger",
                "NIGGA",
                "NIGGER",
                "kys",
                "kms",
                "Kill yourself",
                "kill yourself",
        ],
            3: [
                "nigga",
                "nigger",
                "Nigga",
                "Nigger",
                "NIGGA",
                "NIGGER",
                "kys",
                "kms",
                "Kill yourself",
                "kill yourself",
                "fuck",
                "bitch",
                "kill",
                "Fuck",
                "Bitch",
                "FUCK",
                "BITCH",
            ],
            4: [
                "nigga",
                "nigger",
                "Nigga",
                "Nigger",
                "NIGGA",
                "NIGGER",
                "kys",
                "kms",
                "Kill yourself",
                "kill yourself",
                "fuck",
                "bitch",
                "kill",
                "Fuck",
                "Bitch",
                "FUCK",
                "BITCH",
                "shit",
                "SHIT",
                "Shit",
                "ts",
            ],
            5: [
                "nigga",
                "nigger",
                "Nigga",
                "Nigger",
                "NIGGA",
                "NIGGER",
                "kys",
                "kms",
                "Kill yourself",
                "kill yourself",
                "fuck",
                "bitch",
                "kill",
                "Fuck",
                "Bitch",
                "FUCK",
                "BITCH",
                "shit",
                "SHIT",
                "Shit",
                "ts",
                "dumb",
                "Dumb",
                "DUMB",
                "ass",
                "Ass",
                "ASS",
                "idiot",
                "Idiot",
                "IDIOT",
            ],
        }

        # Ensure the user exists in the data and initialize missing keys
        if user_id not in user_data:
            user_data[user_id] = {
                "xp": 0,
                "level": 1,
                "coins": 100,
                "warnings": [],
                "censored_count": 0,
                "strikes": 0,
            }
        elif "censored_count" not in user_data[user_id]:
            user_data[user_id]["censored_count"] = 0

        # Check for offensive words
        if level > 0:
            for word in offensive_words.get(level, []):
                if word in message.content.lower():
                    await message.delete()
                    await message.channel.send(
                        f"⚠️ {message.author.mention}, your message was removed for containing offensive language."
                    )
                    # Increment the censored count
                    user_data[user_id]["censored_count"] += 1
                    censored_count = user_data[user_id]["censored_count"]

                    # Check if the user has reached the limit
                    if censored_count >= 15:
                        user_data[user_id]["censored_count"] = 0  # Reset the count
                        user_data[user_id]["strikes"] += 1  # Add a strike
                        utils.save_user_data(user_data)

                        # Notify the user and the channel
                        await message.channel.send(
                            f"⚠️ {message.author.mention} has been given a **strike** for repeated offensive language. Total strikes: {user_data[user_id]['strikes']}."
                        )

                        # Take action based on the number of strikes
                        if user_data[user_id]["strikes"] == 3:
                            mute_role = discord.utils.get(message.guild.roles, name="Muted")
                            if not mute_role:
                                mute_role = await message.guild.create_role(name="Muted")
                                for channel in message.guild.channels:
                                    await channel.set_permissions(
                                        mute_role, send_messages=False, speak=False
                                    )
                            await message.author.add_roles(mute_role)
                            await message.channel.send(
                                f"🔇 {message.author.mention} has been muted for accumulating 3 strikes."
                            )
                        elif user_data[user_id]["strikes"] == 5:
                            await message.author.kick(reason="Reached 5 strikes")
                            await message.channel.send(
                                f"👢 {message.author.mention} has been kicked for reaching 5 strikes."
                            )
                        elif user_data[user_id]["strikes"] >= 7:
                            await message.author.ban(reason="Reached 7 strikes")
                            await message.channel.send(
                                f"⛔ {message.author.mention} has been banned for reaching 7 strikes."
                            )

                    utils.save_user_data(user_data)
                    return

        # Allow the `?start` command to bypass sleep mode
        if variables.is_sleeping and message.content.startswith("?start"):
            await self.bot.process_commands(message)
            return

        # Ignore all messages if the bot is in sleep mode
        if variables.is_sleeping:
            return

        # Save updated user data
        utils.save_user_data(data)
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ Bot is ready! Logged in as {self.bot.user}")
        print(f"Connected to {len(self.bot.guilds)} guild(s).")
        logging.info(f"Logged in as {self.bot.user}")
        self.bot.loop.create_task(utils.monitor_inactivity())
        print("Monitor activity task has been started.")
        asyncio.create_task(utils.update_bot_data_periodically(self.bot))
        print("Update bot through website task has started.")
        self.bot.loop.create_task(utils.refresh_leaderboard(self.bot))
        print("refreshing leaderboard started ok")
        self.bot.loop.create_task(utils.change_status(self.bot))
        print("Status task has been sent!")
        await asyncio.sleep(18000)
        self.bot.loop.create_task(utils.chat_reviver_task(self.bot))
        logging.info(f"Chat reviver task started.")

async def setup(bot):
    await bot.add_cog(Events(bot))
