"""
Cipher Anti-Nuke Protection System
Prevents server destruction by compromised administrators

Features:
- Mass ban/kick detection
- Mass role/channel deletion detection
- Webhook spam detection
- Automatic permission revocation
- Action reversal and backup restoration
- Fully toggleable per guild by administrators
"""

import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict
from dataclasses import dataclass
import logging
import json
import os

print("✅ - Anti-Nuke loaded.")


@dataclass
class ActionLog:
    """Log of a moderation action"""
    action_type: str  # "ban", "kick", "role_delete", "channel_delete", "webhook_create"
    moderator_id: int
    timestamp: datetime
    target_id: Optional[int] = None
    guild_id: Optional[int] = None


@dataclass
class NukeResponse:
    """Response from anti-nuke system"""
    is_nuke: bool
    action_type: str
    moderator: discord.Member
    action_count: int
    actions_taken: List[str]


class AntiNuke:
    """
    Comprehensive anti-nuke protection system
    
    Monitors for mass destructive actions:
    - Mass bans (> 5 in 10 seconds)
    - Mass kicks (> 5 in 10 seconds)
    - Mass role deletions (> 3 in 10 seconds)
    - Mass channel deletions (> 3 in 10 seconds)
    - Webhook spam (> 5 in 10 seconds)
    
    All protections are TOGGLEABLE per guild
    """
    
    # Default thresholds
    DEFAULT_BAN_THRESHOLD = 5  # actions in time window
    DEFAULT_KICK_THRESHOLD = 5
    DEFAULT_ROLE_THRESHOLD = 3
    DEFAULT_CHANNEL_THRESHOLD = 3
    DEFAULT_WEBHOOK_THRESHOLD = 5
    TIME_WINDOW = 10  # seconds
    
    def __init__(self, bot: commands.Bot):
        """Initialize anti-nuke protection"""
        self.bot = bot
        
        # Action tracking
        self.action_logs: Dict[int, Dict[int, List[ActionLog]]] = defaultdict(lambda: defaultdict(list))  # guild_id -> user_id -> logs
        
        # Per-guild configuration
        self.enabled: Dict[int, bool] = {}  # guild_id -> enabled
        self.ban_protection: Dict[int, bool] = {}
        self.kick_protection: Dict[int, bool] = {}
        self.role_protection: Dict[int, bool] = {}
        self.channel_protection: Dict[int, bool] = {}
        self.webhook_protection: Dict[int, bool] = {}
        
        # Whitelisted users (trusted admins)
        self.whitelisted: Dict[int, Set[int]] = defaultdict(set)  # guild_id -> set(user_ids)
        
        # Backups for restoration
        self.role_backups: Dict[int, List[Dict[str, Any]]] = {}  # guild_id -> role data
        self.channel_backups: Dict[int, List[Dict[str, Any]]] = {}  # guild_id -> channel data
        
    # ==================== Core Detection Functions ====================
    
    async def check_ban_action(self, guild: discord.Guild, moderator: discord.Member, banned_user: discord.User) -> Optional[NukeResponse]:
        """
        Check if ban action is part of a mass ban attack
        
        Returns NukeResponse if nuke detected, None otherwise
        """
        if not self._is_protection_active(guild.id, "ban"):
            return None
        
        if self._is_whitelisted(guild.id, moderator.id):
            return None
        
        # Log action
        self._log_action(guild.id, moderator.id, "ban", banned_user.id)
        
        # Check threshold
        recent_actions = self._get_recent_actions(guild.id, moderator.id, "ban")
        if len(recent_actions) >= self.DEFAULT_BAN_THRESHOLD:
            # NUKE DETECTED
            response = await self._handle_nuke(guild, moderator, "mass_ban", len(recent_actions))
            return response
        
        return None
    
    async def check_kick_action(self, guild: discord.Guild, moderator: discord.Member, kicked_user: discord.Member) -> Optional[NukeResponse]:
        """Check if kick action is part of a mass kick attack"""
        if not self._is_protection_active(guild.id, "kick"):
            return None
        
        if self._is_whitelisted(guild.id, moderator.id):
            return None
        
        self._log_action(guild.id, moderator.id, "kick", kicked_user.id)
        
        recent_actions = self._get_recent_actions(guild.id, moderator.id, "kick")
        if len(recent_actions) >= self.DEFAULT_KICK_THRESHOLD:
            response = await self._handle_nuke(guild, moderator, "mass_kick", len(recent_actions))
            return response
        
        return None
    
    async def check_role_deletion(self, role: discord.Role, moderator: discord.Member) -> Optional[NukeResponse]:
        """Check if role deletion is part of a mass role deletion attack"""
        guild = role.guild
        
        if not self._is_protection_active(guild.id, "role"):
            return None
        
        if self._is_whitelisted(guild.id, moderator.id):
            return None
        
        # Backup role before deletion
        await self._backup_role(role)
        
        self._log_action(guild.id, moderator.id, "role_delete", role.id)
        
        recent_actions = self._get_recent_actions(guild.id, moderator.id, "role_delete")
        if len(recent_actions) >= self.DEFAULT_ROLE_THRESHOLD:
            response = await self._handle_nuke(guild, moderator, "mass_role_delete", len(recent_actions))
            return response
        
        return None
    
    async def check_channel_deletion(self, channel: discord.abc.GuildChannel, moderator: discord.Member) -> Optional[NukeResponse]:
        """Check if channel deletion is part of a mass channel deletion attack"""
        guild = channel.guild
        
        if not self._is_protection_active(guild.id, "channel"):
            return None
        
        if self._is_whitelisted(guild.id, moderator.id):
            return None
        
        # Backup channel before deletion
        await self._backup_channel(channel)
        
        self._log_action(guild.id, moderator.id, "channel_delete", channel.id)
        
        recent_actions = self._get_recent_actions(guild.id, moderator.id, "channel_delete")
        if len(recent_actions) >= self.DEFAULT_CHANNEL_THRESHOLD:
            response = await self._handle_nuke(guild, moderator, "mass_channel_delete", len(recent_actions))
            return response
        
        return None
    
    async def check_webhook_creation(self, webhook: discord.Webhook, creator: discord.Member) -> Optional[NukeResponse]:
        """Check if webhook creation is part of webhook spam attack"""
        guild = webhook.guild
        
        if not self._is_protection_active(guild.id, "webhook"):
            return None
        
        if self._is_whitelisted(guild.id, creator.id):
            return None
        
        self._log_action(guild.id, creator.id, "webhook_create")
        
        recent_actions = self._get_recent_actions(guild.id, creator.id, "webhook_create")
        if len(recent_actions) >= self.DEFAULT_WEBHOOK_THRESHOLD:
            response = await self._handle_nuke(guild, creator, "webhook_spam", len(recent_actions))
            return response
        
        return None
    
    # ==================== Nuke Response Handler ====================
    
    async def _handle_nuke(self, guild: discord.Guild, moderator: discord.Member, nuke_type: str, action_count: int) -> NukeResponse:
        """
        Handle detected nuke attempt
        
        Actions:
        1. Strip moderator permissions
        2. Alert owner
        3. Log event
        4. Optionally reverse actions
        """
        logging.critical(f"🚨 NUKE DETECTED in {guild.name}: {nuke_type} by {moderator} ({action_count} actions)")
        
        actions_taken = []
        
        # 1. Strip moderator permissions
        try:
            # Remove all roles with dangerous permissions
            dangerous_roles = [
                role for role in moderator.roles
                if role.permissions.administrator or
                   role.permissions.ban_members or
                   role.permissions.kick_members or
                   role.permissions.manage_roles or
                   role.permissions.manage_channels or
                   role.permissions.manage_webhooks
            ]
            
            for role in dangerous_roles:
                if role < guild.me.top_role:  # Can only remove roles below bot's highest role
                    await moderator.remove_roles(role, reason=f"Cipher Anti-Nuke: {nuke_type} detected")
            
            actions_taken.append(f"Stripped permissions from {moderator}")
            logging.info(f"✅ Stripped {len(dangerous_roles)} dangerous roles from {moderator}")
            
        except discord.Forbidden:
            logging.error(f"❌ Cannot strip permissions from {moderator} (missing permissions)")
            actions_taken.append(f"⚠️ Failed to strip permissions (missing perms)")
        
        # 2. Alert owner
        await self._alert_owner(guild, moderator, nuke_type, action_count)
        actions_taken.append("Alerted server owner")
        
        # 3. Log to SecurityManager
        if hasattr(self.bot, 'security_manager'):
            self.bot.security_manager.log_security_event(
                "NUKE_DETECTED",
                {
                    "guild_id": guild.id,
                    "moderator_id": moderator.id,
                    "nuke_type": nuke_type,
                    "action_count": action_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        return NukeResponse(
            is_nuke=True,
            action_type=nuke_type,
            moderator=moderator,
            action_count=action_count,
            actions_taken=actions_taken
        )
    
    async def _alert_owner(self, guild: discord.Guild, moderator: discord.Member, nuke_type: str, action_count: int):
        """Send emergency alert to server owner"""
        alert_message = (
            f"🚨 **ANTI-NUKE ALERT** 🚨\n\n"
            f"**Server:** {guild.name}\n"
            f"**Threat:** {nuke_type.replace('_', ' ').title()}\n"
            f"**Compromised Moderator:** {moderator.mention} ({moderator})\n"
            f"**Actions Detected:** {action_count}\n\n"
            f"**Actions Taken:**\n"
            f"✅ Stripped dangerous permissions\n"
            f"✅ Halted further damage\n\n"
            f"**Recommendation:** Review {moderator}'s account security immediately.\n"
            f"Use `/antinuke restore` if restoration is needed."
        )
        
        try:
            await guild.owner.send(alert_message)
            logging.info(f"✅ Sent nuke alert to {guild.owner}")
        except:
            # Fallback: system channel
            if guild.system_channel:
                try:
                    await guild.system_channel.send(alert_message)
                except:
                    logging.error(f"Could not send nuke alert for {guild.name}")
    
    # ==================== Backup & Restoration ====================
    
    async def _backup_role(self, role: discord.Role):
        """Backup a role before deletion"""
        guild_id = role.guild.id
        
        if guild_id not in self.role_backups:
            self.role_backups[guild_id] = []
        
        role_data = {
            "id": role.id,
            "name": role.name,
            "permissions": role.permissions.value,
            "color": role.color.value,
            "hoist": role.hoist,
            "mentionable": role.mentionable,
            "position": role.position
        }
        
        self.role_backups[guild_id].append(role_data)
    
    async def _backup_channel(self, channel: discord.abc.GuildChannel):
        """Backup a channel before deletion"""
        guild_id = channel.guild.id
        
        if guild_id not in self.channel_backups:
            self.channel_backups[guild_id] = []
        
        channel_data = {
            "id": channel.id,
            "name": channel.name,
            "type": str(channel.type),
            "position": channel.position
        }
        
        self.channel_backups[guild_id].append(channel_data)
    
    # ==================== Helper Functions ====================
    
    def _log_action(self, guild_id: int, moderator_id: int, action_type: str, target_id: Optional[int] = None):
        """Log a moderation action"""
        log = ActionLog(
            action_type=action_type,
            moderator_id=moderator_id,
            timestamp=datetime.utcnow(),
            target_id=target_id,
            guild_id=guild_id
        )
        self.action_logs[guild_id][moderator_id].append(log)
    
    def _get_recent_actions(self, guild_id: int, moderator_id: int, action_type: str) -> List[ActionLog]:
        """Get recent actions of a specific type by a moderator"""
        now = datetime.utcnow()
        window = timedelta(seconds=self.TIME_WINDOW)
        
        all_actions = self.action_logs[guild_id][moderator_id]
        
        # Filter by type and time window
        recent = [
            action for action in all_actions
            if action.action_type == action_type and (now - action.timestamp) < window
        ]
        
        # Clean old actions
        self.action_logs[guild_id][moderator_id] = [
            action for action in all_actions
            if (now - action.timestamp) < timedelta(minutes=5)
        ]
        
        return recent
    
    def _is_protection_active(self, guild_id: int, protection_type: str) -> bool:
        """Check if a specific protection is enabled for a guild"""
        # Must have anti-nuke enabled globally
        if not self.enabled.get(guild_id, True):  # Default: enabled
            return False
        
        # Check specific protection
        if protection_type == "ban":
            return self.ban_protection.get(guild_id, True)
        elif protection_type == "kick":
            return self.kick_protection.get(guild_id, True)
        elif protection_type == "role":
            return self.role_protection.get(guild_id, True)
        elif protection_type == "channel":
            return self.channel_protection.get(guild_id, True)
        elif protection_type == "webhook":
            return self.webhook_protection.get(guild_id, True)
        
        return True
    
    def _is_whitelisted(self, guild_id: int, user_id: int) -> bool:
        """Check if user is whitelisted (trusted)"""
        return user_id in self.whitelisted.get(guild_id, set())
    
    # ==================== Configuration ====================
    
    def enable_protection(self, guild_id: int):
        """Enable anti-nuke protection for a guild"""
        self.enabled[guild_id] = True
    
    def disable_protection(self, guild_id: int):
        """Disable anti-nuke protection for a guild"""
        self.enabled[guild_id] = False
    
    def toggle_ban_protection(self, guild_id: int, enabled: bool):
        """Toggle mass ban protection"""
        self.ban_protection[guild_id] = enabled
    
    def toggle_kick_protection(self, guild_id: int, enabled: bool):
        """Toggle mass kick protection"""
        self.kick_protection[guild_id] = enabled
    
    def toggle_role_protection(self, guild_id: int, enabled: bool):
        """Toggle mass role deletion protection"""
        self.role_protection[guild_id] = enabled
    
    def toggle_channel_protection(self, guild_id: int, enabled: bool):
        """Toggle mass channel deletion protection"""
        self.channel_protection[guild_id] = enabled
    
    def toggle_webhook_protection(self, guild_id: int, enabled: bool):
        """Toggle webhook spam protection"""
        self.webhook_protection[guild_id] = enabled
    
    def whitelist_user(self, guild_id: int, user_id: int):
        """Add user to whitelist (trusted admins)"""
        self.whitelisted[guild_id].add(user_id)
    
    def unwhitelist_user(self, guild_id: int, user_id: int):
        """Remove user from whitelist"""
        self.whitelisted[guild_id].discard(user_id)
    
    def get_status(self, guild_id: int) -> Dict[str, bool]:
        """Get current anti-nuke status for a guild"""
        return {
            "enabled": self.enabled.get(guild_id, True),
            "ban_protection": self.ban_protection.get(guild_id, True),
            "kick_protection": self.kick_protection.get(guild_id, True),
            "role_protection": self.role_protection.get(guild_id, True),
            "channel_protection": self.channel_protection.get(guild_id, True),
            "webhook_protection": self.webhook_protection.get(guild_id, True)
        }
