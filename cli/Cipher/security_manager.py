"""
Cipher Security Manager - Central security gateway for all bot operations.

This module provides:
- Rate limiting per user/guild
- Permission tier validation (Owner, Administrator, Moderator)
- Event interception and security logging
- Audit trail generation for all security-relevant actions
"""

import discord
from discord.ext import commands
import asyncio
import time
import json
from Ediscord import variables
import os
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Dict, List, Optional, Any


class SecurityTier(IntEnum):
    """Security permission tiers for Cipher bot."""
    OWNER = 1           # Bot owner - full API debugger access
    ADMINISTRATOR = 2   # Server administrators - all moderation
    MODERATOR = 3       # Moderators - basic moderation only


class SecurityManager:
    """
    Central SecurityManager class - Gateway for all bot events.
    
    Handles:
    - Rate limiting enforcement
    - Permission tier validation
    - Security event logging
    - Audit trail maintenance
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rate_limits: Dict[str, Dict[int, List[float]]] = {}
        self.audit_log: List[Dict[str, Any]] = []
        self.audit_log_path = os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "data", 
            "security_audit.json"
        )
        self._load_audit_log()
        
        # Rate limit config: command -> (max_uses, time_window_seconds)
        self.rate_limit_config = {
            "warn": (5, 60),      # 5 warns per minute
            "ban": (3, 60),       # 3 bans per minute
            "kick": (5, 60),      # 5 kicks per minute
            "purge": (3, 60),     # 3 purges per minute
            "mute": (5, 60),      # 5 mutes per minute
            "default": (10, 60),  # 10 commands per minute default
        }
    
    def _load_audit_log(self):
        """Load existing audit log from disk."""
        try:
            if os.path.exists(self.audit_log_path):
                with open(self.audit_log_path, 'r', encoding='utf-8') as f:
                    self.audit_log = json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load audit log: {e}")
            self.audit_log = []
    
    def _save_audit_log(self):
        """Persist audit log to disk."""
        try:
            os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)
            with open(self.audit_log_path, 'w', encoding='utf-8') as f:
                # Only keep last 10,000 entries to prevent bloat
                recent_logs = self.audit_log[-10000:]
                json.dump(recent_logs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Failed to save audit log: {e}")
    
    async def is_owner(self, user: discord.User) -> bool:
        """
        Check if a user is the bot owner.
        
        Args:
            user: The Discord user to check
            
        Returns:
            True if user is the bot owner, False otherwise
        """
        try:
            app_info = await self.bot.application_info()
            return user.id == variables.OWNER_ID
        except Exception as e:
            print(f"Error checking owner status: {e}")
            return False
    
    async def validate_permission_tier(
        self, 
        user: discord.User, 
        guild: Optional[discord.Guild],
        required_tier: SecurityTier
    ) -> bool:
        """
        Validate that a user has the required security tier.
        
        Args:
            user: The Discord user to check
            guild: The guild context (None for DMs)
            required_tier: Minimum required SecurityTier
            
        Returns:
            True if user has sufficient permissions, False otherwise
        """
        # Owner check
        if required_tier == SecurityTier.OWNER:
            return await self.is_owner(user)
        
        # Guild-based checks
        if guild is None:
            return False
        
        member = guild.get_member(user.id)
        if member is None:
            return False
        
        # Administrator check
        if required_tier == SecurityTier.ADMINISTRATOR:
            return member.guild_permissions.administrator
        
        # Moderator check (has kick or ban permissions)
        if required_tier == SecurityTier.MODERATOR:
            perms = member.guild_permissions
            return perms.kick_members or perms.ban_members or perms.moderate_members
        
        return False
    
    async def check_rate_limit(
        self, 
        user_id: int, 
        command: str
    ) -> bool:
        """
        Check if user is within rate limits for a command.
        
        Args:
            user_id: Discord user ID
            command: Command name being executed
            
        Returns:
            True if within limits, False if rate limited
        """
        # Get config for this command
        config = self.rate_limit_config.get(
            command, 
            self.rate_limit_config["default"]
        )
        max_uses, window = config
        
        # Initialize tracking for this command if needed
        if command not in self.rate_limits:
            self.rate_limits[command] = {}
        
        current_time = time.time()
        
        # Get user's usage timestamps for this command
        if user_id not in self.rate_limits[command]:
            self.rate_limits[command][user_id] = []
        
        usage_times = self.rate_limits[command][user_id]
        
        # Remove timestamps outside the window
        cutoff = current_time - window
        usage_times = [t for t in usage_times if t > cutoff]
        
        # Check if user exceeded limits
        if len(usage_times) >= max_uses:
            return False
        
        # Add current usage
        usage_times.append(current_time)
        self.rate_limits[command][user_id] = usage_times
        
        return True
    
    async def log_security_event(
        self,
        event_type: str,
        details: Dict[str, Any]
    ):
        """
        Log a security-relevant event to the audit trail.
        
        Args:
            event_type: Type of event (e.g., "WARN_ISSUED", "BAN_EXECUTED")
            details: Event details including user IDs, reason, etc.
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "details": details
        }
        
        self.audit_log.append(entry)
        
        # Save every 10 events to avoid excessive I/O
        if len(self.audit_log) % 10 == 0:
            self._save_audit_log()
    
    async def get_audit_trail(
        self,
        guild_id: Optional[int] = None,
        user_id: Optional[int] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit log entries with optional filters.
        
        Args:
            guild_id: Filter by guild ID
            user_id: Filter by user ID (moderator or target)
            event_type: Filter by event type
            limit: Maximum entries to return
            
        Returns:
            List of audit log entries matching filters
        """
        filtered = self.audit_log
        
        # Apply filters
        if guild_id is not None:
            filtered = [e for e in filtered if e.get("details", {}).get("guild") == guild_id]
        
        if user_id is not None:
            filtered = [
                e for e in filtered 
                if user_id in [
                    e.get("details", {}).get("moderator"),
                    e.get("details", {}).get("target")
                ]
            ]
        
        if event_type is not None:
            filtered = [e for e in filtered if e.get("event_type") == event_type]
        
        # Return most recent entries
        return filtered[-limit:]
    
    async def cleanup_old_rate_limits(self):
        """Clean up expired rate limit data to prevent memory bloat."""
        current_time = time.time()
        
        for command, user_data in list(self.rate_limits.items()):
            for user_id, timestamps in list(user_data.items()):
                # Get window for this command
                config = self.rate_limit_config.get(
                    command,
                    self.rate_limit_config["default"]
                )
                _, window = config
                cutoff = current_time - window
                
                # Filter expired timestamps
                active_timestamps = [t for t in timestamps if t > cutoff]
                
                if active_timestamps:
                    self.rate_limits[command][user_id] = active_timestamps
                else:
                    # Remove user if no active rate limits
                    del self.rate_limits[command][user_id]
            
            # Remove command if no users have rate limits
            if not self.rate_limits[command]:
                del self.rate_limits[command]
