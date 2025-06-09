# --------------------- IMPORTS --------------------
import discord
from discord.ext import commands
from Ediscord import utils, variables
import asyncio
import typing

# --------------------- MODERATION COMMANDS --------------------
print("✅ - Moderation loaded.")
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def warn(self, ctx, member: discord.Member, *, reason=None):
        user_id = str(member.id)
        if user_id not in variables.warnings_data:
            variables.warnings_data[user_id] = {"messages": [], "warnings": 0}

        variables.warnings_data[user_id]["warnings"] += 1
        utils.save_warnings_data()

        await ctx.send(
            f"✅ {member.mention} has been warned. Total warnings: {variables.warnings_data[user_id]['warnings']}"
        )
        logs_channel = utils.get_logs_channel(ctx.guild)
        if logs_channel:
            await logs_channel.send(
                f"{ctx.author} warned {member.mention} in {ctx.channel}. Reason: {reason}. Total warnings: {variables.warnings_data[user_id]['warnings']}"
            )

        # Mute the user if they reach 5 warnings
        if variables.warnings_data[user_id]["warnings"] >= 5:
            mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
            if not mute_role:
                mute_role = await ctx.guild.create_role(name="Muted")
                for channel in ctx.guild.channels:
                    await channel.set_permissions(
                        mute_role, send_messages=False, speak=False
                    )
            await member.add_roles(mute_role)
            await ctx.send(
                f"{member.mention} has been muted for 10 minutes due to excessive warnings."
            )
            if logs_channel:
                await logs_channel.send(
                    f"{member.mention} has been muted for 10 minutes due to excessive warnings."
                )
            await asyncio.sleep(600)  # 10 minutes
            await member.remove_roles(mute_role)
            await ctx.send(f"{member.mention} has been unmuted.")
            if logs_channel:
                await logs_channel.send(f"{member.mention} has been unmuted.")


    # Ban command
    @commands.command()
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        if reason is None:
            reason = "No reason provided"

        await member.ban(reason=reason)
        print(
            f"{ctx.author} Banned {ctx.member} in channel {ctx.channel}. Reason: {reason}."
        )
        await ctx.send(f"✅{member.mention} has successfully been banned for: {reason}")

    @commands.command(name="strike")
    @commands.has_permissions(manage_roles=True)
    async def strike(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Give a strike to a user."""
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

        await ctx.send(
            f"⚠️ {member.mention} has been given a strike. Total strikes: **{strikes}**. Reason: {reason}"
        )

        # Take action based on the number of strikes
        if strikes == 3:
            mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
            if not mute_role:
                mute_role = await ctx.guild.create_role(name="Muted")
                for channel in ctx.guild.channels:
                    await channel.set_permissions(
                        mute_role, send_messages=False, speak=False
                    )
            await member.add_roles(mute_role)
            await ctx.send(
                f"🔇 {member.mention} has been muted for accumulating 3 strikes."
            )
        elif strikes == 5:
            await member.kick(reason="Reached 5 strikes")
            await ctx.send(f"👢 {member.mention} has been kicked for reaching 5 strikes.")
        elif strikes >= 7:
            await member.ban(reason="Reached 7 strikes")
            await ctx.send(f"⛔ {member.mention} has been banned for reaching 7 strikes.")


    @commands.command(name="clearstrikes")
    @commands.has_permissions(manage_roles=True)
    async def clearstrikes(self, ctx, member: discord.Member):
        """Clear all strikes for a user."""
        user_id = str(member.id)
        user_data = utils.load_user_data()

        if user_id in user_data and "strikes" in user_data[user_id]:
            user_data[user_id]["strikes"] = 0
            utils.save_user_data(user_data)
            await ctx.send(f"✅ Cleared all strikes for {member.mention}.")
        else:
            await ctx.send(f"❌ {member.mention} has no strikes.")


    @commands.command(name="infractions")
    @commands.has_permissions(manage_roles=True)
    async def infractions(self, ctx, member: discord.Member):
        """View a user's strikes and warnings."""
        user_id = str(member.id)
        user_data = utils.load_user_data()

        # Extract strikes and warnings
        strikes = user_data.get(user_id, {}).get("strikes", 0)
        warnings = len(user_data.get(user_id, {}).get("warnings", []))

        await ctx.send(
            f"📋 **Infractions for {member.mention}:**\n"
            f"- Strikes: {strikes}\n"
            f"- Warnings: {warnings}"
        )


    @commands.command(name="setlimitations")
    @commands.has_permissions(administrator=True)
    async def setlimitations(self, ctx, level: typing.Optional[str] = None):
        """Set the offensive word filtering level."""
        if not level:
            await ctx.send(
                "❓ **Usage:** `?setlimitations <level>`\n"
                "Levels:\n"
                "1 - Minimal filtering\n"
                "2 - Moderate filtering\n"
                "3 - Strict filtering\n"
                "4 - Very strict filtering\n"
                "5 - Block all offensive words"
            )
            return

        # Validate level
        if level not in ["1", "2", "3", "4", "5"]:
            await ctx.send("❌ Invalid level. Please choose a level between 1 and 5.")
            return

        # Save the level to the JSON file
        guild_id = str(ctx.guild.id)
        limitations = utils.load_limitations()
        limitations[guild_id] = int(level)
        utils.save_limitations(limitations)

        await ctx.send(f"✅ Offensive word filtering level set to **{level}**.")


async def setup(bot):
    await bot.add_cog(Moderation(bot))