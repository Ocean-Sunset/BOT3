# --------------------- IMPORTS --------------------
from Ediscord import utils, variables
import discord
from discord.ext.commands import (
    CommandNotFound,
    MissingRequiredArgument,
    BadArgument,
    CommandOnCooldown,
    CheckFailure,
    DisabledCommand,
    NoPrivateMessage,
    CommandInvokeError,
)
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

    async def is_spam(self, message):
        # Simple spam check: repeated messages or too many messages in a short time
        # Replace with your own logic as needed
        if hasattr(self, "_last_message"):
            last = self._last_message.get(message.author.id)
            if last and last["content"] == message.content and (message.created_at - last["time"]).total_seconds() < 3:
                return True
        else:
            self._last_message = {}
        self._last_message[message.author.id] = {"content": message.content, "time": message.created_at}
        return False

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
        try:
            utils.write_last_command(ctx.channel.id, ctx.message.id)
        except Exception as e:
            print(f"Failed to write last command: {e}")
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
                guild = self.bot.get_guild(payload.guild_id)
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
                guild = self.bot.get_guild(payload.guild_id)
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
            if payload.message_id == colorrole_message_id:
                member = guild.get_member(payload.user_id)
                if member is None or member.bot:
                    return

                emoji = str(payload.emoji)
                
                # Define your color roles and their corresponding emojis
                color_roles_map = {
                    "🔴": "Red Role",
                    "🟠": "Orange Role",
                    "🟡": "Yellow Role",
                    "🟢": "Green Role",
                    "🔵": "Blue Role",
                    "🟣": "Violet Role",
                    "⚪": "White Role",
                    "⚫": "Black Role",
                    "🟫": "Brown Role",
                    "🟦": "Cyan Role",
                    "🟪": "Magenta Role",
                    "🩵": "Light Blue Role",
                    "🩷": "Pink Role",
                    "🩶": "Grey Role",
                }

                role_name = color_roles_map.get(emoji)
                if role_name:
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role and role not in member.roles:
                        try:
                            await member.add_roles(role)
                            print(f"Assigned {role.name} to {member.display_name}")
                            
                            # --- Send DM Notification for role gained ---
                            try:
                                await member.send(f"🎉 You've successfully been given the **{role.name}** role in {guild.name}!")
                            except discord.Forbidden:
                                print(f"Could not send DM to {member.display_name}. DMs might be disabled.")
                            except Exception as e:
                                print(f"Error sending DM to {member.display_name}: {e}")
                            # --- End DM Notification ---

                        except discord.Forbidden:
                            print(f"Bot lacks permissions to add role {role.name} to {member.display_name}.")
                        except Exception as e:
                            print(f"Error adding role {role.name} to {member.display_name}: {e}")
                    else:
                        print(f"{member.display_name} already has the {role.name} role.")
                return

            verify_message_id = data.get("verify_message_id")
            if not verify_message_id:
                logging.warning("Verification message ID not found in user data.")
                return

            if payload.message_id != verify_message_id:
                return

            if str(payload.emoji) == "✅":
                guild = self.bot.get_guild(payload.guild_id)
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
                guild = self.bot.get_guild(payload.guild_id)
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

            # Custom role reactions
            role_reactions = utils.get_guild_role_reactions(payload.guild_id)
            if str(payload.message_id) in role_reactions:
                emoji = str(payload.emoji)
                role_id = role_reactions[str(payload.message_id)].get(emoji)
                if role_id:
                    guild = self.bot.get_guild(payload.guild_id)
                    member = guild.get_member(payload.user_id)
                    role = guild.get_role(role_id)
                    if role and member:
                        await member.add_roles(role, reason="Reaction role")

        except Exception as e:
            logging.error(f"Error in on_raw_reaction_add: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Handle reactions for region roles and other commands."""
        try:
            if payload.user_id == self.bot.user.id:
                return

            data = utils.load_user_data()
            region_message_id = data.get("region_message_id")
            if region_message_id and payload.message_id == region_message_id:
                guild = self.bot.get_guild(payload.guild_id)
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
                guild = self.bot.get_guild(payload.guild_id)
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
            if payload.message_id == colorrole_message_id:
                member = guild.get_member(payload.user_id)
                if member is None or member.bot:
                    return

                emoji = str(payload.emoji)

                # Define your color roles and their corresponding emojis
                color_roles_map = {
                    "🔴": "Red Role",
                    "🟠": "Orange Role",
                    "🟡": "Yellow Role",
                    "🟢": "Green Role",
                    "🔵": "Blue Role",
                    "🟣": "Violet Role",
                    "⚪": "White Role",
                    "⚫": "Black Role",
                    "🟫": "Brown Role",
                    "🟦": "Cyan Role",
                    "🟪": "Magenta Role",
                    "🩵": "Light Blue Role",
                    "🩷": "Pink Role",
                    "🩶": "Grey Role",
                }

                role_name = color_roles_map.get(emoji)
                if role_name:
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role and role in member.roles:
                        try:
                            await member.remove_roles(role)
                            print(f"Removed {role.name} from {member.display_name}")

                            # --- Send DM Notification for role lost ---
                            try:
                                await member.send(f"👋 You've successfully lost the **{role.name}** role in {guild.name}.")
                            except discord.Forbidden:
                                print(f"Could not send DM to {member.display_name}. DMs might be disabled.")
                            except Exception as e:
                                print(f"Error sending DM to {member.display_name}: {e}")
                            # --- End DM Notification ---

                        except discord.Forbidden:
                            print(f"Bot lacks permissions to remove role {role.name} from {member.display_name}.")
                        except Exception as e:
                            print(f"Error removing role {role.name} from {member.display_name}: {e}")
                    else:
                        print(f"{member.display_name} did not have the {role.name} role.")
                return

            verify_message_id = data.get("verify_message_id")
            if not verify_message_id:
                logging.warning("Verification message ID not found in user data.")
                return

            if payload.message_id != verify_message_id:
                return

            if str(payload.emoji) == "✅":
                guild = self.bot.get_guild(payload.guild_id)
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
                guild = self.bot.get_guild(payload.guild_id)
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

            # Custom role reactions
            role_reactions = utils.get_guild_role_reactions(payload.guild_id)
            if str(payload.message_id) in role_reactions:
                emoji = str(payload.emoji)
                role_id = role_reactions[str(payload.message_id)].get(emoji)
                if role_id:
                    guild = self.bot.get_guild(payload.guild_id)
                    member = guild.get_member(payload.user_id)
                    role = guild.get_role(role_id)
                    if role and member:
                        await member.remove_roles(role, reason="Reaction role removed")

        except Exception as e:
            logging.error(f"Error in on_raw_reaction_remove: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Event triggered when a user joins the server with a custom cat-themed welcome image."""
        try:
            logging.info(
                f"New member joined: {member.name}#{member.discriminator} (ID: {member.id})"
            )

            welcome_channel = discord.utils.find(
                lambda c: c.name.lower() in ["welcome", "chat", "general"], member.guild.text_channels
            )
            if not welcome_channel:
                logging.warning(
                    f"No suitable welcome channel found in {member.guild.name} (ID: {member.guild.id})"
                )
                return

            avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
            response = requests.get(avatar_url)
            if response.status_code != 200:
                logging.error(
                    f"Failed to fetch avatar for {member.name}#{member.discriminator}. HTTP Status: {response.status_code}"
                )
                return
            avatar = Image.open(BytesIO(response.content)).convert("RGBA").resize((120, 120))

            # Create a circular mask for the avatar
            mask = Image.new("L", (120, 120), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.ellipse((0, 0, 120, 120), fill=255)
            avatar_rounded = Image.new("RGBA", (120, 120))
            avatar_rounded.paste(avatar, (0, 0), mask=mask)

            # Background (simple gray, or use your own image)
            base = Image.new("RGBA", (500, 180), (140, 140, 140, 255))

            # Optionally, paste your cat drawing here
            # cat_img = Image.open("assets/welcome/cat.png").convert("RGBA").resize((350, 120))
            # base.paste(cat_img, (150, 30), cat_img)

            # Paste avatar
            base.paste(avatar_rounded, (20, 30), avatar_rounded)

            # Draw text
            draw = ImageDraw.Draw(base)
            font_large = ImageFont.truetype("assets/impact.ttf", 28)
            font_small = ImageFont.truetype("assets/impact.ttf", 18)

            username = member.display_name
            welcome_text = f"Welcome, {username}!"
            sub_text = "We hope you enjoy your stay"

            # Draw main welcome text
            draw.text((160, 50), welcome_text, font=font_large, fill=(255, 255, 255, 255))
            # Draw subtext
            draw.text((160, 90), sub_text, font=font_small, fill=(220, 220, 220, 255))

            # Optionally, draw member number
            member_count = member.guild.member_count
            member_num_text = f"Member #{member_count}"
            draw.text((160, 120), member_num_text, font=font_small, fill=(200, 200, 200, 255))

            # Save to buffer
            buffer = BytesIO()
            base.save(buffer, format="PNG")
            buffer.seek(0)

            # Send image
            await welcome_channel.send(
                f"Welcome, {member.mention}!",
                file=discord.File(buffer, filename="welcome.png")
            )
            logging.info(
                        f"Welcome message sent for {member.name}#{member.discriminator} in {welcome_channel.name}."
                    )
        except Exception as e:
            logging.error(f"Error in on_member_join: {e}")

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

            goodbye_channel_name = discord.utils.find(
                lambda c: c.name.lower() in ["goodbye", "chat", "general"], member.guild.text_channels
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

            # Send the image and custom message
            goodbye_msg = utils.get_guild_goodbye_message(member.guild.id) or f"👋 Goodbye, {member.mention}. We will miss you!"
            await goodbye_channel.send(
                goodbye_msg,
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
            attempted_command = ctx.message.content.split()[0][1:]  # Remove the prefix (e.g., "?")

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
            return  # <-- THIS IS IMPORTANT

        elif isinstance(error, MissingRequiredArgument):
            await ctx.send("❌ Missing required argument. Please check your command usage.")
            return
        elif isinstance(error, BadArgument):
            await ctx.send("❌ Invalid argument. Please check your input.")
            return
        elif isinstance(error, CommandOnCooldown):
            await ctx.send(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
            return
        elif isinstance(error, CheckFailure):
            await ctx.send("❌ You do not have permission to use this command.")
            return
        elif isinstance(error, DisabledCommand):
            await ctx.send("❌ This command is currently disabled.")
            return
        elif isinstance(error, NoPrivateMessage):
            await ctx.send("❌ This command cannot be used in private messages.")
            return

        # Only signal the handler for unhandled/critical errors
        await ctx.send(f"An error occurred: {error}")
        try:
            utils.signal_error(
                f"{type(error).__name__}: {error}\nCommand: {ctx.command}\nUser: {ctx.author}\nMessage: {ctx.message.content}"
            )
        except Exception as e:
            print(f"Failed to signal error: {e}")
        
    @commands.Cog.listener()
    async def on_message(self, message):
        print(f"📩 Message received: {message.content} from {message.author}")
        """Handle all on_message events."""
        print(f"{variables.last_activity};{variables.last_activity_time}")
        if message.guild is None:
            # This is a DM, handle accordingly or just return
            return
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

        # --- SPAM DETECTION AND HANDLING ---
        if await self.is_spam(message):
            try:
                await message.delete()
            except Exception:
                pass  # Ignore if already deleted or missing permissions
            try:
                await message.author.send(
                    f"⚠️ You have been warned for spamming in **{message.guild.name}**. Please stop or further action may be taken."
                )
            except Exception:
                pass  # User may have DMs closed
            return  # Don't process further

        # Handle XP system with custom cooldown
        user_id = message.author.id
        now = time.time()

        # Check if the user is on cooldown
        if user_id in variables.message_cooldowns:
            cooldown_end = variables.message_cooldowns[user_id]
            if now < cooldown_end:
                # User is still on cooldown, skip granting XP
                await self.bot.process_commands(message)
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
            import datetime
            data[user_id]["warnings"].append(
                {"reason": "Spamming", "timestamp": datetime.datetime.now().isoformat()}
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
                    # Define the check function for reaction_add
                    def check(reaction, user):
                        return (
                            reaction.message.id == message.id
                            and str(reaction.emoji) == gem_emoji
                            and not user.bot
                        )

                    # Wait for a user to react within 5 seconds
                    reaction, user = await self.bot.wait_for(
                        "reaction_add", timeout=5.0, check=check
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
                
        async def cog_checrk(self, ctx):
            # Allow all commands to run as normal
            return True

        # Allow the `?start` command to bypass sleep mode
        if variables.is_sleeping and message.content.startswith("?start"):
            await self.bot.process_commands(message)
            return
            
        if message.author.bot:
            return

        channel_name = message.channel.name.lower()

        # Restrict sewers-entrance: only allow ?sewer enter
        if channel_name == "⚠️・sewers-entrance":
            if not message.content.strip().lower().startswith("?sewer enter"):
                try:
                    await message.delete()
                    warn = await message.channel.send(
                        f"{message.author.mention} You are not allowed to speak in this channel. Use `?sewer enter left` or `?sewer enter right`."
                    )
                    await asyncio.sleep(3)
                    await warn.delete()
                except Exception:
                    pass
            return

        # Restrict left/right wing channels: only allow ?sewer exit
        if channel_name in ["⚠️・left-system-wing", "⚠️・right-system-wing"]:
            if not message.content.strip().lower().startswith("?sewer exit"):
                try:
                    await message.delete()
                    warn = await message.channel.send(
                        f"{message.author.mention} You are not allowed to speak in this channel. Use `?sewer exit` to leave."
                    )
                    await asyncio.sleep(3)
                    await warn.delete()
                except Exception:
                    pass

        # Ignore all messages if the bot is in sleep mode
        if variables.is_sleeping:
            return
        
        
        if message.author.bot:
            return

        # Save updated user data
        utils.save_user_data(data)
    
    @commands.Cog.listener()
    async def on_ready(self):
        # In your on_ready event or at startup:
        if not hasattr(self.bot, "launch_time"):
            self.bot.launch_time = time.time()
        if not hasattr(self.bot, "version"):
            self.bot.version = variables.bot_info["version"]
        if not hasattr(self.bot, "total_commands"):
            self.bot.total_commands = variables.total_commands
        print(f"✅ Bot is ready! Logged in as {self.bot.user}")
        print(f"Connected to {len(self.bot.guilds)} guild(s).")
        logging.info(f"Logged in as {self.bot.user}")
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
