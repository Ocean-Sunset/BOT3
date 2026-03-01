"""
Cipher/Sovra - Moderation Commands
All moderation commands require Administrator permissions
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime, timedelta
from typing import Optional

print("✅ - Moderation loaded.")

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logging.info("Moderation cog initialized")

    # ==================== Ban Command ====================
    
    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        member="The member to ban",
        reason="Reason for the ban"
    )
    async def ban(
        self, 
        interaction: discord.Interaction, 
        member: discord.Member, 
        reason: str = "No reason provided"
    ):
        """Ban a member from the server"""
        try:
            # Check if target is higher than moderator
            if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                await interaction.response.send_message(
                    "❌ You cannot ban this user (role hierarchy).",
                    ephemeral=True
                )
                return
            
            # Check if bot can ban
            if member.top_role >= interaction.guild.me.top_role:
                await interaction.response.send_message(
                    "❌ I cannot ban this user (role hierarchy).",
                    ephemeral=True
                )
                return

            # Send DM before banning
            try:
                await member.send(
                    f"🔨 You have been **banned** from **{interaction.guild.name}**\n"
                    f"**Reason:** {reason}\n"
                    f"**Moderator:** {interaction.user}"
                )
            except:
                pass  # User has DMs disabled

            # Ban the member
            await member.ban(reason=f"[{interaction.user}] {reason}")
            
            # Create embed response
            embed = discord.Embed(
                title="🔨 Member Banned",
                description=f"{member.mention} has been banned.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=True)
            embed.set_footer(text=f"User ID: {member.id}")
            
            await interaction.response.send_message(embed=embed)
            logging.info(f"{interaction.user} banned {member} from {interaction.guild.name}: {reason}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to ban members.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Error in ban command: {e}")
            await interaction.response.send_message(
                f"❌ An error occurred: {e}",
                ephemeral=True
            )

    # ==================== Unban Command ====================
    
    @app_commands.command(name="unban", description="Unban a user from the server")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        user_id="The ID of the user to unban",
        reason="Reason for the unban"
    )
    async def unban(
        self, 
        interaction: discord.Interaction, 
        user_id: str,
        reason: str = "No reason provided"
    ):
        """Unban a user from the server"""
        try:
            # Convert to int
            user_id_int = int(user_id)
            
            # Get banned users
            bans = [entry async for entry in interaction.guild.bans()]
            user = discord.utils.get(bans, user__id=user_id_int)
            
            if not user:
                await interaction.response.send_message(
                    f"❌ User with ID `{user_id}` is not banned.",
                    ephemeral=True
                )
                return
            
            # Unban the user
            await interaction.guild.unban(user.user, reason=f"[{interaction.user}] {reason}")
            
            # Create embed response
            embed = discord.Embed(
                title="✅ User Unbanned",
                description=f"{user.user} has been unbanned.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=True)
            embed.set_footer(text=f"User ID: {user_id}")
            
            await interaction.response.send_message(embed=embed)
            logging.info(f"{interaction.user} unbanned {user.user} from {interaction.guild.name}: {reason}")
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid user ID. Please provide a valid number.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to unban members.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Error in unban command: {e}")
            await interaction.response.send_message(
                f"❌ An error occurred: {e}",
                ephemeral=True
            )

    # ==================== Kick Command ====================
    
    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        member="The member to kick",
        reason="Reason for the kick"
    )
    async def kick(
        self, 
        interaction: discord.Interaction, 
        member: discord.Member, 
        reason: str = "No reason provided"
    ):
        """Kick a member from the server"""
        try:
            # Check if target is higher than moderator
            if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                await interaction.response.send_message(
                    "❌ You cannot kick this user (role hierarchy).",
                    ephemeral=True
                )
                return
            
            # Check if bot can kick
            if member.top_role >= interaction.guild.me.top_role:
                await interaction.response.send_message(
                    "❌ I cannot kick this user (role hierarchy).",
                    ephemeral=True
                )
                return

            # Send DM before kicking
            try:
                await member.send(
                    f"👢 You have been **kicked** from **{interaction.guild.name}**\n"
                    f"**Reason:** {reason}\n"
                    f"**Moderator:** {interaction.user}"
                )
            except:
                pass  # User has DMs disabled

            # Kick the member
            await member.kick(reason=f"[{interaction.user}] {reason}")
            
            # Create embed response
            embed = discord.Embed(
                title="👢 Member Kicked",
                description=f"{member.mention} has been kicked.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=True)
            embed.set_footer(text=f"User ID: {member.id}")
            
            await interaction.response.send_message(embed=embed)
            logging.info(f"{interaction.user} kicked {member} from {interaction.guild.name}: {reason}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to kick members.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Error in kick command: {e}")
            await interaction.response.send_message(
                f"❌ An error occurred: {e}",
                ephemeral=True
            )

    # ==================== Timeout Command ====================
    
    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        member="The member to timeout",
        duration="Duration in minutes",
        reason="Reason for the timeout"
    )
    async def timeout(
        self, 
        interaction: discord.Interaction, 
        member: discord.Member, 
        duration: int,
        reason: str = "No reason provided"
    ):
        """Timeout a member for a specified duration"""
        try:
            # Validate duration (Discord max is 28 days)
            if duration < 1 or duration > 40320:  # 28 days in minutes
                await interaction.response.send_message(
                    "❌ Duration must be between 1 minute and 28 days (40320 minutes).",
                    ephemeral=True
                )
                return
            
            # Check if target is higher than moderator
            if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
                await interaction.response.send_message(
                    "❌ You cannot timeout this user (role hierarchy).",
                    ephemeral=True
                )
                return
            
            # Check if bot can timeout
            if member.top_role >= interaction.guild.me.top_role:
                await interaction.response.send_message(
                    "❌ I cannot timeout this user (role hierarchy).",
                    ephemeral=True
                )
                return

            # Calculate timeout duration
            timeout_until = datetime.utcnow() + timedelta(minutes=duration)
            
            # Send DM before timeout
            try:
                await member.send(
                    f"⏳ You have been **timed out** in **{interaction.guild.name}**\n"
                    f"**Duration:** {duration} minutes\n"
                    f"**Reason:** {reason}\n"
                    f"**Moderator:** {interaction.user}"
                )
            except:
                pass  # User has DMs disabled

            # Timeout the member
            await member.timeout(timeout_until, reason=f"[{interaction.user}] {reason}")
            
            # Create embed response
            embed = discord.Embed(
                title="⏳ Member Timed Out",
                description=f"{member.mention} has been timed out.",
                color=discord.Color.yellow(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Duration", value=f"{duration} minutes", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=f"User ID: {member.id}")
            
            await interaction.response.send_message(embed=embed)
            logging.info(f"{interaction.user} timed out {member} in {interaction.guild.name} for {duration}m: {reason}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to timeout members.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Error in timeout command: {e}")
            await interaction.response.send_message(
                f"❌ An error occurred: {e}",
                ephemeral=True
            )

    # ==================== Remove Timeout Command ====================
    
    @app_commands.command(name="untimeout", description="Remove timeout from a member")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        member="The member to remove timeout from"
    )
    async def untimeout(
        self, 
        interaction: discord.Interaction, 
        member: discord.Member
    ):
        """Remove timeout from a member"""
        try:
            if member.timed_out_until is None:
                await interaction.response.send_message(
                    f"❌ {member.mention} is not timed out.",
                    ephemeral=True
                )
                return
            
            # Remove timeout
            await member.timeout(None)
            
            embed = discord.Embed(
                title="✅ Timeout Removed",
                description=f"{member.mention}'s timeout has been removed.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Moderator", value=interaction.user.mention)
            
            await interaction.response.send_message(embed=embed)
            logging.info(f"{interaction.user} removed timeout from {member} in {interaction.guild.name}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to remove timeouts.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Error in untimeout command: {e}")
            await interaction.response.send_message(
                f"❌ An error occurred: {e}",
                ephemeral=True
            )

    # ==================== Purge Command ====================
    
    @app_commands.command(name="purge", description="Delete multiple messages")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        amount="Number of messages to delete (1-100)"
    )
    async def purge(
        self, 
        interaction: discord.Interaction, 
        amount: int
    ):
        """Delete a specified number of messages"""
        try:
            # Validate amount
            if amount < 1 or amount > 100:
                await interaction.response.send_message(
                    "❌ Amount must be between 1 and 100.",
                    ephemeral=True
                )
                return
            
            # Defer response since this might take a moment
            await interaction.response.defer(ephemeral=True)
            
            # Delete messages
            deleted = await interaction.channel.purge(limit=amount)
            
            await interaction.followup.send(
                f"✅ Deleted {len(deleted)} message(s).",
                ephemeral=True
            )
            logging.info(f"{interaction.user} purged {len(deleted)} messages in {interaction.channel.name}")
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to delete messages.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Error in purge command: {e}")
            await interaction.followup.send(
                f"❌ An error occurred: {e}",
                ephemeral=True
            )


async def setup(bot):
    """Load the Moderation cog"""
    await bot.add_cog(Moderation(bot))
