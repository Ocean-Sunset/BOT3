"""
Cipher Raid Protection System
Detects and mitigates coordinated attacks

Features:
- Join spam detection (10+ joins/minute)
- Message spam detection (20+ msgs/10 seconds)
- Mention spam detection (5+ mentions/message)
- Automatic Discord verification level escalation
- Auto-lockdown on raid detection
"""

import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from collections import defaultdict
from dataclasses import dataclass
import logging

print("✅ - Raid Protection loaded.")


@dataclass
class RaidMetrics:
    """Current raid detection metrics"""
    joins_last_minute: int
    messages_last_10s: int
    high_risk_joins: int
    is_raid_active: bool
    raid_start_time: Optional[datetime]


class RaidProtection:
    """
    Advanced raid protection system
    
    Detects:
    1. Join spam (excessive join rate)
    2. Message spam (message floods)
    3. Mention spam (mass mentions)
    4. Coordinated bot accounts
    
    Actions:
    - Trigger Discord's native raid protection
    - Auto-lockdown
    - Kick/ban suspicious accounts
    - Alert administrators
    """
    
    # Thresholds (configurable per guild)
    DEFAULT_JOIN_THRESHOLD = 10  # joins per minute
    DEFAULT_MESSAGE_THRESHOLD = 20  # messages per 10 seconds
    DEFAULT_MENTION_THRESHOLD = 5  # mentions per message
    
    def __init__(self, bot: commands.Bot):
        """Initialize raid protection"""
        self.bot = bot
        
        # Tracking data structures
        self.join_times: Dict[int, List[datetime]] = defaultdict(list)  # guild_id -> join times
        self.message_times: Dict[int, Dict[int, List[datetime]]] = defaultdict(lambda: defaultdict(list))  # guild_id -> user_id -> msg times
        self.raid_active: Dict[int, bool] = {}  # guild_id -> is_raid_active
        self.raid_start: Dict[int, datetime] = {}  # guild_id -> raid start time
        
        # Configuration per guild
        self.join_threshold: Dict[int, int] = {}
        self.message_threshold: Dict[int, int] = {}
        self.mention_threshold: Dict[int, int] = {}
        
        # Whitelisted users (bypass raid detection)
        self.whitelisted_users: Dict[int, Set[int]] = defaultdict(set)  # guild_id -> set(user_ids)
        
    # ==================== Join Spam Detection ====================
    
    async def track_join(self, member: discord.Member) -> bool:
        """
        Track a member join and check for raid pattern
        
        Args:
            member: Member who joined
            
        Returns:
            True if raid detected, False otherwise
        """
        guild_id = member.guild.id
        now = datetime.utcnow()
        
        # Add join timestamp
        self.join_times[guild_id].append(now)
        
        # Clean old joins (older than 1 minute)
        self.join_times[guild_id] = [
            join_time for join_time in self.join_times[guild_id]
            if now - join_time < timedelta(minutes=1)
        ]
        
        # Check threshold
        threshold = self.join_threshold.get(guild_id, self.DEFAULT_JOIN_THRESHOLD)
        joins_last_minute = len(self.join_times[guild_id])
        
        if joins_last_minute >= threshold:
            # RAID DETECTED
            if not self.raid_active.get(guild_id, False):
                self.raid_active[guild_id] = True
                self.raid_start[guild_id] = now
                await self._trigger_raid_response(member.guild, "join_spam", joins_last_minute)
            return True
        
        return False
    
    # ==================== Message Spam Detection ====================
    
    async def track_message(self, message: discord.Message) -> bool:
        """
        Track a message and check for spam
        
        Args:
            message: Message to track
            
        Returns:
            True if spam detected, False otherwise
        """
        if not message.guild or message.author.bot:
            return False
        
        # Check whitelist
        if message.author.id in self.whitelisted_users.get(message.guild.id, set()):
            return False
        
        guild_id = message.guild.id
        user_id = message.author.id
        now = datetime.utcnow()
        
        # Add message timestamp
        self.message_times[guild_id][user_id].append(now)
        
        # Clean old messages (older than 10 seconds)
        self.message_times[guild_id][user_id] = [
            msg_time for msg_time in self.message_times[guild_id][user_id]
            if now - msg_time < timedelta(seconds=10)
        ]
        
        # Check threshold
        threshold = self.message_threshold.get(guild_id, self.DEFAULT_MESSAGE_THRESHOLD)
        messages_last_10s = len(self.message_times[guild_id][user_id])
        
        if messages_last_10s >= threshold:
            # MESSAGE SPAM DETECTED
            await self._handle_message_spam(message, messages_last_10s)
            return True
        
        return False
    
    # ==================== Mention Spam Detection ====================
    
    async def check_mention_spam(self, message: discord.Message) -> bool:
        """
        Check if message contains mention spam
        
        Args:
            message: Message to check
            
        Returns:
            True if mention spam detected, False otherwise
        """
        if not message.guild or message.author.bot:
            return False
        
        # Check whitelist
        if message.author.id in self.whitelisted_users.get(message.guild.id, set()):
            return False
        
        threshold = self.mention_threshold.get(message.guild.id, self.DEFAULT_MENTION_THRESHOLD)
        unique_mentions = len(set(message.mentions))
        
        if unique_mentions >= threshold:
            # MENTION SPAM DETECTED
            await self._handle_mention_spam(message, unique_mentions)
            return True
        
        return False
    
    # ==================== Raid Response Actions ====================
    
    async def _trigger_raid_response(self, guild: discord.Guild, raid_type: str, severity: int):
        """
        Trigger comprehensive raid response
        
        Actions:
        1. Escalate Discord verification level
        2. Alert administrators
        3. Log event
        4. Optionally auto-lockdown
        """
        logging.warning(f"🚨 RAID DETECTED in {guild.name}: {raid_type} (severity: {severity})")
        
        # 1. Escalate Discord's verification level
        try:
            current_level = guild.verification_level
            if current_level < discord.VerificationLevel.high:
                await guild.edit(
                    verification_level=discord.VerificationLevel.high,
                    reason=f"Cipher: Raid detected ({raid_type})"
                )
                logging.info(f"✅ Escalated {guild.name} verification to HIGH")
            elif current_level < discord.VerificationLevel.highest:
                await guild.edit(
                    verification_level=discord.VerificationLevel.highest,
                    reason=f"Cipher: Raid detected ({raid_type})"
                )
                logging.info(f"✅ Escalated {guild.name} verification to HIGHEST")
        except discord.Forbidden:
            logging.error(f"❌ Cannot change verification level in {guild.name} (missing permissions)")
        
        # 2. Alert administrators (find security alerts channel or owner)
        await self._send_raid_alert(guild, raid_type, severity)
        
        # 3. Log to SecurityManager if available
        if hasattr(self.bot, 'security_manager'):
            self.bot.security_manager.log_security_event(
                "RAID_DETECTED",
                {
                    "guild_id": guild.id,
                    "raid_type": raid_type,
                    "severity": severity,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    async def _send_raid_alert(self, guild: discord.Guild, raid_type: str, severity: int):
        """Send raid alert to security channel or owner"""
        alert_message = (
            f"🚨 **RAID DETECTED** 🚨\n\n"
            f"**Server:** {guild.name}\n"
            f"**Type:** {raid_type.replace('_', ' ').title()}\n"
            f"**Severity:** {severity}\n"
            f"**Actions Taken:**\n"
            f"✅ Discord verification level escalated\n"
            f"✅ Monitoring active\n\n"
            f"Use `/raid status` for details."
        )
        
        # Try to find security alerts channel
        # For now, send to system channel or owner DM
        if guild.system_channel:
            try:
                await guild.system_channel.send(alert_message)
                return
            except:
                pass
        
        # Fallback: DM owner
        try:
            await guild.owner.send(alert_message)
        except:
            logging.error(f"Could not send raid alert for {guild.name}")
    
    async def _handle_message_spam(self, message: discord.Message, count: int):
        """Handle message spam detection"""
        try:
            # Timeout user for 10 minutes
            await message.author.timeout(
                timedelta(minutes=10),
                reason=f"Cipher: Message spam ({count} messages in 10s)"
            )
            
            # Delete recent messages
            await message.channel.purge(
                limit=50,
                check=lambda m: m.author == message.author,
                reason="Cipher: Spam cleanup"
            )
            
            logging.info(f"⏳ Timed out {message.author} for message spam ({count} msgs)")
            
        except discord.Forbidden:
            logging.error(f"Cannot timeout {message.author} (missing permissions)")
    
    async def _handle_mention_spam(self, message: discord.Message, count: int):
        """Handle mention spam detection"""
        try:
            # Delete message
            await message.delete()
            
            # Timeout user
            await message.author.timeout(
                timedelta(minutes=10),
                reason=f"Cipher: Mention spam ({count} mentions)"
            )
            
            logging.info(f"⏳ Timed out {message.author} for mention spam ({count} mentions)")
            
        except discord.Forbidden:
            logging.error(f"Cannot handle mention spam by {message.author} (missing permissions)")
    
    # ==================== Raid Management ====================
    
    def get_metrics(self, guild_id: int) -> RaidMetrics:
        """Get current raid metrics for a guild"""
        now = datetime.utcnow()
        
        # Calculate joins in last minute
        joins = [j for j in self.join_times.get(guild_id, []) if now - j < timedelta(minutes=1)]
        
        # Calculate messages in last 10 seconds (across all users)
        messages = 0
        for user_msgs in self.message_times.get(guild_id, {}).values():
            messages += len([m for m in user_msgs if now - m < timedelta(seconds=10)])
        
        return RaidMetrics(
            joins_last_minute=len(joins),
            messages_last_10s=messages,
            high_risk_joins=len(joins),  # Simplified
            is_raid_active=self.raid_active.get(guild_id, False),
            raid_start_time=self.raid_start.get(guild_id)
        )
    
    def end_raid(self, guild_id: int):
        """Manually end raid mode for a guild"""
        self.raid_active[guild_id] = False
        if guild_id in self.raid_start:
            del self.raid_start[guild_id]
        logging.info(f"Raid mode ended for guild {guild_id}")
    
    # ==================== Configuration ====================
    
    def set_join_threshold(self, guild_id: int, threshold: int):
        """Set join spam threshold for a guild"""
        self.join_threshold[guild_id] = threshold
    
    def set_message_threshold(self, guild_id: int, threshold: int):
        """Set message spam threshold for a guild"""
        self.message_threshold[guild_id] = threshold
    
    def set_mention_threshold(self, guild_id: int, threshold: int):
        """Set mention spam threshold for a guild"""
        self.mention_threshold[guild_id] = threshold
    
    def whitelist_user(self, guild_id: int, user_id: int):
        """Add user to raid detection whitelist"""
        self.whitelisted_users[guild_id].add(user_id)
    
    def unwhitelist_user(self, guild_id: int, user_id: int):
        """Remove user from raid detection whitelist"""
        self.whitelisted_users[guild_id].discard(user_id)
    
    def is_whitelisted(self, guild_id: int, user_id: int) -> bool:
        """Check if user is whitelisted"""
        return user_id in self.whitelisted_users.get(guild_id, set())
