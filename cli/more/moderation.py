# --------------------- IMPORTS --------------------
import discord
from discord.ext import commands
from Ediscord import utils, variables
import asyncio
import typing
from discord import app_commands

# --------------------- MODERATION COMMANDS --------------------
print("✅ - Moderation loaded.")

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="warn", description="Warn a member. Mutes after 5 warnings.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        if member is None:
            await interaction.response.send_message("# ❌ You have to have a member to warn!\n-# Usage: `/warn @user1234 reason`", ephemeral=True)
            return
        user_id = str(member.id)
        if user_id not in variables.warnings_data:
            variables.warnings_data[user_id] = {"messages": [], "warnings": 0}
        variables.warnings_data[user_id]["warnings"] += 1
        utils.save_warnings_data()
        await interaction.response.send_message(
            f"# ✅ {member.mention} has been warned.\nTotal warnings: {variables.warnings_data[user_id]['warnings']}"
        )
        logs_channel = utils.get_logs_channel(interaction.guild)
        if logs_channel:
            await logs_channel.send(
                f"{interaction.user} warned {member.mention} in {interaction.channel}. Reason: {reason}. Total warnings: {variables.warnings_data[user_id]['warnings']}"
            )
        # Mute the user if they reach 5 warnings
        if variables.warnings_data[user_id]["warnings"] >= 5:
            mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
            if not mute_role:
                mute_role = await interaction.guild.create_role(name="Muted")
                for channel in interaction.guild.channels:
                    await channel.set_permissions(
                        mute_role, send_messages=False, speak=False
                    )
            await member.add_roles(mute_role)
            await interaction.followup.send(
                f"❗{member.mention} has been muted for **10 minutes due to excessive warnings.**"
            )
            if logs_channel:
                await logs_channel.send(
                    f"{member.mention} has been muted for 10 minutes due to excessive warnings."
                )
            await asyncio.sleep(600)  # 10 minutes
            await member.remove_roles(mute_role)
            await interaction.followup.send(f"✔️ {member.mention} has been unmuted.")
            if logs_channel:
                await logs_channel.send(f"{member.mention} has been unmuted.")

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if member is None:
            await interaction.response.send_message("# ❌ You have to have a member to ban!\n-# Usage: `/ban @user1234 reason(optional)`", ephemeral=True)
            return
        await member.ban(reason=reason)
        await interaction.response.send_message(f"# ✅ {member.mention} has successfully been banned\nReason: {reason}")

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await member.kick(reason=reason)
        await interaction.response.send_message(f"# ✅ {member.mention} has successfully been kicked for:\n{reason}")

    @app_commands.command(name="strike", description="Give a strike to a user.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def strike(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if member is None:
            await interaction.response.send_message("# ❌ You have to have a member to strike!\n-# Usage: `/strike @user1234 reason(optional)`", ephemeral=True)
            return
        user_id = str(member.id)
        user_data = utils.load_user_data()
        # Initialize strikes if not present
        if user_id not in user_data:
            user_data[user_id] = {
                "xp": 0,
                "level": 1,
                "coins": 100,
                "warnings": [],
                "strikes": 0,
            }
        elif "strikes" not in user_data[user_id]:
            user_data[user_id]["strikes"] = 0
        # Increment the user's strikes
        user_data[user_id]["strikes"] += 1
        strikes = user_data[user_id]["strikes"]
        utils.save_user_data(user_data)
        await interaction.response.send_message(
            f"# ⚠️ {member.mention} has been given a strike.\nTotal strikes: **{strikes}**.\nReason: {reason}"
        )
        # Take action based on the number of strikes
        if strikes == 3:
            mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
            if not mute_role:
                mute_role = await interaction.guild.create_role(name="Muted")
                for channel in interaction.guild.channels:
                    await channel.set_permissions(
                        mute_role, send_messages=False, speak=False
                    )
            await member.add_roles(mute_role)
            await interaction.followup.send(
                f"🔇 {member.mention} has also been muted for accumulating 3 strikes."
            )
        elif strikes == 5:
            await member.kick(reason="Reached 5 strikes")
            await interaction.followup.send(f"👢 {member.mention} has also been kicked for reaching 5 strikes.")
        elif strikes >= 7:
            await member.ban(reason="Reached 7 strikes")
            await interaction.followup.send(f"⛔ {member.mention} has also been banned for reaching 7 strikes.\n-# bye!!")

    @app_commands.command(name="clearstrikes", description="Clear all strikes for a user.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def clearstrikes(self, interaction: discord.Interaction, member: discord.Member):
        if member is None:
            await interaction.response.send_message("❌ You have to have a member to clear their strikes!\n-# Usage: `/clearstrikes @user1234`", ephemeral=True)
            return
        user_id = str(member.id)
        user_data = utils.load_user_data()
        if user_id in user_data and "strikes" in user_data[user_id]:
            user_data[user_id]["strikes"] = 0
            utils.save_user_data(user_data)
            await interaction.response.send_message(f"✅ Cleared all strikes for {member.mention}.")
        else:
            await interaction.response.send_message(f"❌ {member.mention} has no strikes.")

    @app_commands.command(name="infractions", description="View a user's strikes and warnings.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def infractions(self, interaction: discord.Interaction, member: discord.Member):
        if member is None:
            await interaction.response.send_message("❌ You have to have a member to see their infractions!\n-# Usage: `/infractions @user1234`", ephemeral=True)
            return
        user_id = str(member.id)
        user_data = utils.load_user_data()
        # Extract strikes and warnings
        strikes = user_data.get(user_id, {}).get("strikes", 0)
        warnings = len(user_data.get(user_id, {}).get("warnings", []))
        await interaction.response.send_message(
            f"# 📋 **Infractions for {member.mention}:**\n"
            f"- Strikes: **{strikes}**\n"
            f"- Warnings: **{warnings}**"
        )

    @app_commands.command(name="setlimitations", description="Set the offensive word filtering level.")
    @utils.admin_or_owner()
    async def setlimitations(self, interaction: discord.Interaction, level: str = None):
        if not level:
            await interaction.response.send_message(
                "❓ **Usage:** `/setlimitations <level>`\n"
                "Levels:\n"
                "1 - Minimal filtering\n"
                "2 - Moderate filtering\n"
                "3 - Strict filtering\n"
                "4 - Very strict filtering\n"
                "5 - Block all offensive words"
            )
            return
        if level not in ["1", "2", "3", "4", "5"]:
            await interaction.response.send_message("# ❌ Invalid level.\nPlease choose a level between 1 and 5.")
            return
        guild_id = str(interaction.guild.id)
        limitations = utils.load_limitations()
        limitations[guild_id] = int(level)
        utils.save_limitations(limitations)
        await interaction.response.send_message(f"✅ Offensive word filtering level set to **{level}**.")

    @app_commands.command(name="mute", description="Mute a user.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        if member is None:
            await interaction.response.send_message(f"# ❌ No member has been specified!\n-# {utils.little_error_variant()}", ephemeral=True)
            return
        if reason is None:
            reason = "No reason has been specified"
        mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await interaction.guild.create_role(name="Muted")
            for channel in interaction.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False)
        await member.add_roles(mute_role, reason=reason)
        await interaction.response.send_message(f"# ✅ {member.mention} has been muted.\nReason: {reason}")

    @app_commands.command(name="unmute", description="Unmute a user.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        if member is None:
            await interaction.response.send_message(f"# ❌ No member has been specified!\n-# {utils.little_error_variant()}", ephemeral=True)
            return
        mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if mute_role in member.roles:
            await member.remove_roles(mute_role)
            await interaction.response.send_message(f"# ✅ {member.mention} has been unmuted.")
        else:
            await interaction.response.send_message(f"# ❌ {member.mention} is not muted.\n-# {utils.little_error_variant()}")

    @app_commands.command(name="purge", description="Delete a number of messages.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        if amount is None:
            await interaction.response.send_message(f"# ❌ No amount has been specified!\nInput an amount like this: `/purge 3`\n-# {utils.little_error_variant()}", ephemeral=True)
            return
        await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(f"# ✅ Deleted {amount} messages.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
