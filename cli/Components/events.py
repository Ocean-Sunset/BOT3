"""
Cipher Security Bot - Events Module
Handles Discord events with security logging and monitoring
"""

import discord
from discord.ext import commands
import logging
from datetime import datetime
from Cipher.bot_detector import BotDetector
from Cipher.raid_protection import RaidProtection
from Cipher.anti_nuke import AntiNuke
from Cipher.lockdown import LockdownManager
from Cipher.config_manager import ConfigManager

print("✅ - Events loaded.")

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Initialize security systems if not already on bot
        if not hasattr(bot, 'bot_detector'): bot.bot_detector = BotDetector()
        if not hasattr(bot, 'raid_protection'): bot.raid_protection = RaidProtection(bot)
        if not hasattr(bot, 'anti_nuke'): bot.anti_nuke = AntiNuke(bot)
        if not hasattr(bot, 'lockdown_manager'): bot.lockdown_manager = LockdownManager(bot)
        if not hasattr(bot, 'config_manager'): bot.config_manager = ConfigManager()
        
        logging.info("Events cog initialized with Advanced Security integration")

    # ==================== Member Events ====================
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Log when members join for security monitoring"""
        try:
            # 1. Bot Detection
            analysis = self.bot.bot_detector.analyze_account(member)
            
            # 2. Raid Protection
            is_raid = await self.bot.raid_protection.track_join(member)
            
            # Security logging
            if hasattr(self.bot, 'security_manager'):
                await self.bot.security_manager.log_security_event(
                    "MEMBER_JOIN",
                    {
                        "user_id": member.id,
                        "user_name": str(member),
                        "guild_id": member.guild.id,
                        "bot_score": analysis.total_score,
                        "risk_level": analysis.risk_level,
                        "is_raid_context": is_raid
                    }
                )
            
            # Alert and take action if high risk
            if analysis.total_score >= 80:
                logging.warning(f"🚨 CRITICAL BOT RISK: Kicking {member} ({analysis.total_score}%)")
                try:
                    await member.send(f"⚠️ Your account was flagged as a high-risk bot ({analysis.total_score}%) and removed from {member.guild.name}. If this is an error, please contact the server owner.")
                except: pass
                await member.kick(reason=f"Cipher Bot Detection: Critical Risk ({analysis.total_score}%)")
                
            elif analysis.total_score >= 60:
                logging.warning(f"🚨 HIGH BOT RISK: Quarantining {member} ({analysis.total_score}%)")
                # Apply Unverified/Quarantine role if configured
                config = self.bot.config_manager.get_config(member.guild.id)
                unverified_role = member.guild.get_role(config.verification_role_id) # Using verification role as quarantine
                if not unverified_role:
                    unverified_role = discord.utils.get(member.guild.roles, name="Unverified")
                
                if unverified_role:
                    await member.add_roles(unverified_role, reason=f"Cipher Bot Detection: High Risk ({analysis.total_score}%)")
                    try:
                        await member.send(f"⚠️ Your account was flagged as suspicious ({analysis.total_score}%) and has been restricted. Please complete verification or contact staff.")
                    except: pass
        except Exception as e:
            logging.error(f"Error in on_member_join: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Log when members leave and check for kicks"""
        try:
            # Check for kick via audit logs
            async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id:
                    moderator = entry.user
                    # Trigger Anti-Nuke check
                    response = await self.bot.anti_nuke.check_kick_action(member.guild, moderator, member)
                    if response and response.is_nuke:
                        logging.critical(f"🛑 MASS KICK DETECTED: {moderator} stripped of perms.")
                    break

            if hasattr(self.bot, 'security_manager'):
                await self.bot.security_manager.log_security_event(
                    "MEMBER_LEAVE",
                    {
                        "user_id": member.id,
                        "user_name": str(member),
                        "guild_id": member.guild.id,
                        "roles": [role.name for role in member.roles if role.name != "@everyone"]
                    }
                )
        except Exception as e:
            logging.error(f"Error in on_member_remove: {e}")

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Log ban events and check for mass ban attack"""
        try:
            # Check audit logs to find moderator
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    moderator = entry.user
                    # Trigger Anti-Nuke check
                    response = await self.bot.anti_nuke.check_ban_action(guild, moderator, user)
                    if response and response.is_nuke:
                        logging.critical(f"🛑 MASS BAN DETECTED: {moderator} stripped of perms.")
                    break

            if hasattr(self.bot, 'security_manager'):
                await self.bot.security_manager.log_security_event(
                    "MEMBER_BANNED",
                    {
                        "user_id": user.id,
                        "user_name": str(user),
                        "guild_id": guild.id
                    }
                )
            logging.info(f"🔨 Member banned: {user} from {guild.name}")
        except Exception as e:
            logging.error(f"Error in on_member_ban: {e}")

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """Log unban events for audit trail"""
        try:
            if hasattr(self.bot, 'security_manager'):
                await self.bot.security_manager.log_security_event(
                    "MEMBER_UNBANNED",
                    {
                        "user_id": user.id,
                        "user_name": str(user),
                        "guild_id": guild.id
                    }
                )
            logging.info(f"✅ Member unbanned: {user} from {guild.name}")
        except Exception as e:
            logging.error(f"Error in on_member_unban: {e}")

    # ==================== Message Events ====================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Monitor messages for raid patterns (spam/mentions)"""
        if message.author.bot or not message.guild:
            return
            
        # 1. Check for mention spam
        await self.bot.raid_protection.check_mention_spam(message)
        
        # 2. Check for message flood/spam
        await self.bot.raid_protection.track_message(message)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Log message deletions for moderation tracking"""
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return
            
        try:
            if hasattr(self.bot, 'security_manager'):
                await self.bot.security_manager.log_security_event(
                    "MESSAGE_DELETED",
                    {
                        "user_id": message.author.id,
                        "user_name": str(message.author),
                        "channel_id": message.channel.id,
                        "guild_id": message.guild.id,
                        "content_preview": message.content[:100] if message.content else "[No content]"
                    }
                )
        except Exception as e:
            logging.error(f"Error in on_message_delete: {e}")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Log message edits for moderation tracking"""
        # Ignore bot messages, DMs, and non-content edits
        if before.author.bot or not before.guild or before.content == after.content:
            return
            
        try:
            if hasattr(self.bot, 'security_manager'):
                await self.bot.security_manager.log_security_event(
                    "MESSAGE_EDITED",
                    {
                        "user_id": before.author.id,
                        "user_name": str(before.author),
                        "channel_id": before.channel.id,
                        "guild_id": before.guild.id,
                        "before_preview": before.content[:100] if before.content else "[No content]",
                        "after_preview": after.content[:100] if after.content else "[No content]"
                    }
                )
        except Exception as e:
            logging.error(f"Error in on_message_edit: {e}")

    # ==================== Guild Events ====================

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Log when bot joins a new guild"""
        try:
            logging.info(f"📥 Joined new guild: {guild.name} (ID: {guild.id}, Members: {guild.member_count})")
            
            if hasattr(self.bot, 'security_manager'):
                await self.bot.security_manager.log_security_event(
                    "GUILD_JOIN",
                    {
                        "guild_id": guild.id,
                        "guild_name": guild.name,
                        "member_count": guild.member_count,
                        "owner_id": guild.owner_id
                    }
                )
        except Exception as e:
            logging.error(f"Error in on_guild_join: {e}")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Log when bot leaves a guild"""
        try:
            logging.info(f"📤 Left guild: {guild.name} (ID: {guild.id})")
            
            if hasattr(self.bot, 'security_manager'):
                await self.bot.security_manager.log_security_event(
                    "GUILD_LEAVE",
                    {
                        "guild_id": guild.id,
                        "guild_name": guild.name
                    }
                )
        except Exception as e:
            logging.error(f"Error in on_guild_remove: {e}")

    # ==================== Role Events ====================

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Track role changes for security monitoring"""
        # Only track role changes
        if before.roles == after.roles:
            return
            
        try:
            added_roles = set(after.roles) - set(before.roles)
            removed_roles = set(before.roles) - set(after.roles)
            
            if added_roles or removed_roles:
                # Security logging for role changes
                if hasattr(self.bot, 'security_manager'):
                    await self.bot.security_manager.log_security_event(
                        "MEMBER_ROLES_CHANGED",
                        {
                            "user_id": after.id,
                            "user_name": str(after),
                            "guild_id": after.guild.id,
                            "added_roles": [role.name for role in added_roles],
                            "removed_roles": [role.name for role in removed_roles]
                        }
                    )
        except Exception as e:
            logging.error(f"Error in on_member_update: {e}")
                
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Anti-Nuke: Detect mass role deletion"""
        try:
            async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
                if entry.target.id == role.id:
                    await self.bot.anti_nuke.check_role_deletion(role, entry.user)
                    break
        except Exception as e:
            logging.error(f"Error in on_guild_role_delete: {e}")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Anti-Nuke: Detect mass channel deletion"""
        try:
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                if entry.target.id == channel.id:
                    await self.bot.anti_nuke.check_channel_deletion(channel, entry.user)
                    break
        except Exception as e:
            logging.error(f"Error in on_guild_channel_delete: {e}")

    # ==================== Error Handling ====================

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Global error handler for commands"""
        # Ignore command not found errors
        if isinstance(error, commands.CommandNotFound):
            return
            
        # Handle permission errors
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
            return
            
        # Handle missing arguments
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
            return
            
        # Handle cooldown errors
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Command on cooldown. Try again in {error.retry_after:.1f}s")
            return
            
        # Log unexpected errors
        logging.error(f"Command error in {ctx.command}: {error}", exc_info=error)
        await ctx.send("❌ An unexpected error occurred. The incident has been logged.")


async def setup(bot):
    """Load the Events cog"""
    await bot.add_cog(Events(bot))
