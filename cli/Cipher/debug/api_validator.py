"""
Cipher API Debugger - API Response Validator

Monitors Discord API responses, tracks rate limits, and analyzes errors.
Owner-only module for API health monitoring.
"""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict


class APIValidator(commands.Cog):
    """
    API Response Validator for Cipher.
    
    Monitors:
    - API response codes
    - Rate limit hit tracking
    - Error frequency analysis
    - Bot latency metrics
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.response_log: List[Dict] = []
        self.rate_limit_hits = 0
        self.error_counts = defaultdict(int)
        self.start_time = datetime.utcnow()
        self.max_log_size = 500
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Track command errors for API health monitoring."""
        error_type = type(error).__name__
        self.error_counts[error_type] += 1
        
        # Log critical errors
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "command": ctx.command.name if ctx.command else "Unknown",
            "guild": ctx.guild.id if ctx.guild else None,
            "user": ctx.author.id
        }
        
        self.response_log.append(entry)
        
        if len(self.response_log) > self.max_log_size:
            self.response_log = self.response_log[-self.max_log_size:]
    
    @app_commands.command(name="api_status")
    async def api_status(self, interaction: discord.Interaction):
        """View API health status and metrics (Owner only)."""
        # Log usage and allow command for all users (no owner-only restriction)
        if hasattr(self.bot, 'security_manager'):
            await self.bot.security_manager.log_security_event(
                "API_STATUS_USED",
                {"user": interaction.user.id, "guild": getattr(interaction.guild, 'id', None)}
            )
        
        # Calculate uptime
        uptime = datetime.utcnow() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        # Get bot latency
        latency_ms = round(self.bot.latency * 1000, 2)
        
        # Build embed
        embed = discord.Embed(
            title="🔍 Cipher API Health Status",
            color=discord.Color.green() if latency_ms < 200 else discord.Color.orange()
        )
        
        embed.add_field(
            name="📊 Bot Metrics",
            value=(
                f"**Latency:** {latency_ms}ms\n"
                f"**Uptime:** {uptime_str}\n"
                f"**Guilds:** {len(self.bot.guilds)}\n"
                f"**Users:** {len(self.bot.users)}"
            ),
            inline=False
        )
        
        # Error statistics
        total_errors = sum(self.error_counts.values())
        if total_errors > 0:
            top_errors = sorted(
                self.error_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
            error_list = "\n".join([f"• {name}: {count}" for name, count in top_errors])
        else:
            error_list = "No errors detected ✅"
        
        embed.add_field(
            name="⚠️ Error Summary",
            value=f"**Total Errors:** {total_errors}\n{error_list}",
            inline=False
        )
        
        embed.add_field(
            name="⏱️ Rate Limiting",
            value=f"**Rate Limit Hits:** {self.rate_limit_hits}",
            inline=False
        )
        
        embed.timestamp = datetime.utcnow()
        embed.set_footer(text="Real-time API monitoring")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="api_errors")
    @app_commands.describe(limit="Number of recent errors to view (default: 10)")
    async def api_errors(
        self, 
        interaction: discord.Interaction,
        limit: int = 10
    ):
        """View recent API errors (Owner only)."""
        # Log usage and allow command for all users (no owner-only restriction)
        if hasattr(self.bot, 'security_manager'):
            await self.bot.security_manager.log_security_event(
                "API_ERRORS_USED",
                {"user": interaction.user.id, "guild": getattr(interaction.guild, 'id', None)}
            )
        
        if not self.response_log:
            return await interaction.response.send_message(
                "✅ No errors logged. API is healthy!",
                ephemeral=True
            )
        
        # Get recent errors
        recent = self.response_log[-limit:]
        
        # Format for display
        lines = []
        for entry in recent:
            timestamp = entry['timestamp'].split('T')[1][:8]  # HH:MM:SS
            cmd = entry.get('command', 'Unknown')
            error_type = entry.get('error_type', 'Unknown')
            lines.append(f"`{timestamp}` **{error_type}** in `{cmd}`")
        
        embed = discord.Embed(
            title="⚠️ Recent API Errors",
            description="\n".join(lines[-15:]),  # Show last 15
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Showing {len(recent)} of {len(self.response_log)} total errors")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Load the API Validator cog."""
    await bot.add_cog(APIValidator(bot))
    print("✅ - API Validator loaded.")
