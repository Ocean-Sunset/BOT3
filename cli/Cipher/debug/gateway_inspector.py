"""
Cipher API Debugger - Gateway Event Inspector

Intercepts and inspects raw Discord Gateway events for debugging.
Owner-only module for deep API inspection.
"""

import discord
from discord.ext import commands
from discord import app_commands
import json
from datetime import datetime
from typing import Optional, Dict, Any
import asyncio


class GatewayInspector(commands.Cog):
    """
    Gateway Event Inspector for Cipher.
    
    Allows bot owner to:
    - Intercept raw Gateway events
    - Filter by event type
    - Stream events in real-time
    - Inspect payloads
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.monitoring = False
        self.event_filter: Optional[str] = None
        self.event_log = []
        self.max_log_size = 1000
    
    @commands.Cog.listener()
    async def on_socket_raw_receive(self, msg):
        """Intercept all raw socket messages from Discord Gateway."""
        if not self.monitoring:
            return
        
        try:
            data = json.loads(msg)
            event_type = data.get('t')
            
            # Apply filter if set
            if self.event_filter and event_type != self.event_filter:
                return
            
            # Log the event
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "op_code": data.get('op'),
                "sequence": data.get('s'),
                "payload_preview": str(data.get('d', {}))[:200]  # First 200 chars
            }
            
            self.event_log.append(entry)
            
            # Prevent memory bloat
            if len(self.event_log) > self.max_log_size:
                self.event_log = self.event_log[-self.max_log_size:]
        
        except Exception as e:
            print(f"Gateway Inspector Error: {e}")
    
    @app_commands.command(name="gateway_start")
    @app_commands.describe(event_filter="Optional: Filter by event type (e.g., MESSAGE_CREATE)")
    async def gateway_start(
        self, 
        interaction: discord.Interaction,
        event_filter: Optional[str] = None
    ):
        """Start monitoring Gateway events (Owner only)."""
        # Check if user is owner
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            return await interaction.response.send_message(
                "❌ This command is restricted to the bot owner only.",
                ephemeral=True
            )
        
        self.monitoring = True
        self.event_filter = event_filter
        self.event_log = []
        
        filter_msg = f" (filter: `{event_filter}`)" if event_filter else ""
        await interaction.response.send_message(
            f"🔍 **Gateway monitoring started**{filter_msg}\n"
            f"Use `/gateway_stop` to stop monitoring.\n"
            f"Use `/gateway_view` to view captured events.",
            ephemeral=True
        )
    
    @app_commands.command(name="gateway_stop")
    async def gateway_stop(self, interaction: discord.Interaction):
        """Stop monitoring Gateway events (Owner only)."""
        # Check if user is owner
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            return await interaction.response.send_message(
                "❌ This command is restricted to the bot owner only.",
                ephemeral=True
            )
        
        self.monitoring = False
        event_count = len(self.event_log)
        
        await interaction.response.send_message(
            f"⏹️ **Gateway monitoring stopped**\n"
            f"Captured {event_count} events.",
            ephemeral=True
        )
    
    @app_commands.command(name="gateway_view")
    @app_commands.describe(limit="Number of recent events to view (default: 10)")
    async def gateway_view(
        self, 
        interaction: discord.Interaction,
        limit: int = 10
    ):
        """View captured Gateway events (Owner only)."""
        # Check if user is owner
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            return await interaction.response.send_message(
                "❌ This command is restricted to the bot owner only.",
                ephemeral=True
            )
        
        if not self.event_log:
            return await interaction.response.send_message(
                "📭 No events captured yet. Start monitoring with `/gateway_start`.",
                ephemeral=True
            )
        
        # Get recent events
        recent = self.event_log[-limit:]
        
        # Format for display
        lines = []
        for entry in recent:
            timestamp = entry['timestamp'].split('T')[1][:8]  # HH:MM:SS
            event = entry['event_type'] or 'HEARTBEAT'
            lines.append(f"`{timestamp}` **{event}** (op:{entry['op_code']}, seq:{entry['sequence']})")
        
        embed = discord.Embed(
            title="🔍 Gateway Event Log",
            description="\n".join(lines[-10:]),  # Show last 10
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Showing {len(recent)} of {len(self.event_log)} total events")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Load the Gateway Inspector cog."""
    await bot.add_cog(GatewayInspector(bot))
    print("✅ - Gateway Inspector loaded.")
