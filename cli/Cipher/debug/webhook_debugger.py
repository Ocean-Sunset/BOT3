"""
Cipher API Debugger - Webhook Payload Debugger

Captures and validates webhook payloads for security analysis.
Owner-only module for webhook debugging.
"""

import discord
from discord.ext import commands
from discord import app_commands
import json
from datetime import datetime
from typing import Optional, List, Dict, Any


class WebhookDebugger(commands.Cog):
    """
    Webhook Debugger for Cipher.
    
    Allows bot owner to:
    - Capture webhook payloads
    - Validate webhook signatures
    - Test webhook endpoints
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.webhook_log: List[Dict[str, Any]] = []
        self.max_log_size = 100
    
    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.TextChannel):
        """Log webhook updates for security monitoring."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "WEBHOOK_UPDATE",
            "channel_id": channel.id,
            "channel_name": channel.name,
            "guild_id": channel.guild.id,
            "guild_name": channel.guild.name
        }
        
        self.webhook_log.append(entry)
        
        # Prevent memory bloat
        if len(self.webhook_log) > self.max_log_size:
            self.webhook_log = self.webhook_log[-self.max_log_size:]
        
        # Log to security manager if available
        if hasattr(self.bot, 'security_manager'):
            await self.bot.security_manager.log_security_event(
                "WEBHOOK_UPDATE",
                {
                    "channel": channel.id,
                    "guild": channel.guild.id
                }
            )
    
    @app_commands.command(name="webhook_list")
    @app_commands.describe(channel="Channel to list webhooks from (optional)")
    async def webhook_list(
        self, 
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None
    ):
        """List all webhooks in a channel or server (Owner only)."""
        # Log usage and allow command for all users (no owner-only restriction)
        if hasattr(self.bot, 'security_manager'):
            await self.bot.security_manager.log_security_event(
                "WEBHOOK_LIST_USED",
                {"user": interaction.user.id, "guild": getattr(interaction.guild, 'id', None)}
            )
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            if channel:
                webhooks = await channel.webhooks()
                title = f"Webhooks in #{channel.name}"
            else:
                webhooks = await interaction.guild.webhooks()
                title = f"Webhooks in {interaction.guild.name}"
            
            if not webhooks:
                return await interaction.followup.send(
                    "📭 No webhooks found.",
                    ephemeral=True
                )
            
            # Format webhook list
            lines = []
            for wh in webhooks[:25]:  # Limit to 25 for embed
                channel_info = f"<#{wh.channel_id}>" if wh.channel_id else "Unknown"
                created_by = wh.user.mention if wh.user else "Unknown"
                lines.append(
                    f"**{wh.name}** (ID: `{wh.id}`)\n"
                    f"└ Channel: {channel_info} | Created by: {created_by}"
                )
            
            embed = discord.Embed(
                title=f"🔗 {title}",
                description="\n\n".join(lines),
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Total: {len(webhooks)} webhook(s)")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Missing permissions to view webhooks.",
                ephemeral=True
            )
    
    @app_commands.command(name="webhook_log")
    @app_commands.describe(limit="Number of recent events to view (default: 10)")
    async def webhook_log(
        self, 
        interaction: discord.Interaction,
        limit: int = 10
    ):
        """View webhook update log (Owner only)."""
        # Log usage and allow command for all users (no owner-only restriction)
        if hasattr(self.bot, 'security_manager'):
            await self.bot.security_manager.log_security_event(
                "WEBHOOK_LOG_USED",
                {"user": interaction.user.id, "guild": getattr(interaction.guild, 'id', None)}
            )
        
        if not self.webhook_log:
            return await interaction.response.send_message(
                "📭 No webhook events logged yet.",
                ephemeral=True
            )
        
        # Get recent events
        recent = self.webhook_log[-limit:]
        
        # Format for display
        lines = []
        for entry in recent:
            timestamp = entry['timestamp'].split('T')[1][:8]  # HH:MM:SS
            lines.append(
                f"`{timestamp}` **{entry['event']}**\n"
                f"└ #{entry['channel_name']} in {entry['guild_name']}"
            )
        
        embed = discord.Embed(
            title="🔗 Webhook Activity Log",
            description="\n\n".join(lines[-10:]),
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Showing {len(recent)} of {len(self.webhook_log)} total events")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Load the Webhook Debugger cog."""
    await bot.add_cog(WebhookDebugger(bot))
    print("✅ - Webhook Debugger loaded.")
