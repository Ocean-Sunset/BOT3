"""
Cipher Permission System - Security tier definitions and decorators.

Defines security tiers and provides decorators for command permission checks.
"""

from enum import IntEnum
from discord.ext import commands
import discord
from typing import Optional


class SecurityTier(IntEnum):
    """
    Cipher Security Tier System
    
    TIER 1 (OWNER): Organization Owner - Full API Debugger access
    TIER 2 (ADMINISTRATOR): Server Administrators - All moderation commands
    TIER 3 (MODERATOR): Moderators - Basic moderation only
    """
    OWNER = 1
    ADMINISTRATOR = 2
    MODERATOR = 3


def require_security_tier(tier: SecurityTier):
    """
    Decorator to require a specific security tier for command execution.
    
    Usage:
        @require_security_tier(SecurityTier.ADMINISTRATOR)
        async def my_command(self, interaction):
            ...
    
    Args:
        tier: Minimum SecurityTier required
        
    Returns:
        Decorator function
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        bot = interaction.client
        
        # Check if bot has security manager
        if not hasattr(bot, 'security_manager'):
            await interaction.response.send_message(
                "❌ Security system not initialized.",
                ephemeral=True
            )
            return False
        
        # Validate permission tier
        has_permission = await bot.security_manager.validate_permission_tier(
            interaction.user,
            interaction.guild,
            tier
        )
        
        if not has_permission:
            tier_names = {
                SecurityTier.OWNER: "Bot Owner",
                SecurityTier.ADMINISTRATOR: "Administrator",
                SecurityTier.MODERATOR: "Moderator"
            }
            
            await interaction.response.send_message(
                f"❌ Insufficient permissions. Required: **{tier_names[tier]}**",
                ephemeral=True
            )
            return False
        
        return True
    
    return commands.check(predicate)


def is_owner():
    """Shortcut decorator for owner-only commands."""
    return require_security_tier(SecurityTier.OWNER)


def is_administrator():
    """Shortcut decorator for administrator commands."""
    return require_security_tier(SecurityTier.ADMINISTRATOR)


def is_moderator():
    """Shortcut decorator for moderator commands."""
    return require_security_tier(SecurityTier.MODERATOR)
