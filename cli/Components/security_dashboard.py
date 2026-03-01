"""
Cipher Security Management Cog
Exposes security configurations and manual triggers to administrators

Commands:
- /security setup: Comprehensive security wizard
- /security config: View and toggle settings
- /whitelist: Manage trusted users
- /lockdown: Emergency server freeze
- /raid: Raid protection status and manual triggers
- /antinuke: Anti-nuke status and logs
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime
from typing import Optional, Union
from Cipher.oauth_verification import VerificationView
from Cipher.security_manager import SecurityTier

print("✅ - Security Dashboard loaded.")

class SecurityDashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logging.info("Security Dashboard cog initialized")

    # ==================== Lockdown Commands ====================

    @app_commands.command(name="emergency_lockdown", description="Enable emergency server lockdown")
    @app_commands.describe(mode="Lockdown severity: 'soft' (no messages) or 'hard' (no messages/voice/joins)")
    @app_commands.checks.has_permissions(administrator=True)
    async def lockdown(self, interaction: discord.Interaction, mode: str = "soft"):
        """Enable emergency server lockdown"""
        await interaction.response.defer(ephemeral=True)
        
        if mode not in ["soft", "hard"]:
            await interaction.followup.send("❌ Invalid mode. Use `soft` or `hard`.")
            return
            
        actions = await self.bot.lockdown_manager.enable_lockdown(interaction.guild, mode)
        
        embed = discord.Embed(
            title=f"🔒 Server Lockdown: {mode.upper()}",
            description="\n".join([f"✅ {a}" for a in actions]),
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Triggered by {interaction.user}")
        
        await interaction.followup.send(embed=embed)
        
        # Log event
        self.bot.security_manager.log_security_event("LOCKDOWN_ENABLED", {
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id,
            "mode": mode
        })

    @app_commands.command(name="emergency_unlockdown", description="Lift server lockdown and restore permissions")
    @app_commands.checks.has_permissions(administrator=True)
    async def unlockdown(self, interaction: discord.Interaction):
        """Restore server permissions after lockdown"""
        await interaction.response.defer(ephemeral=True)
        
        actions = await self.bot.lockdown_manager.disable_lockdown(interaction.guild)
        
        embed = discord.Embed(
            title="🔓 Lockdown Lifted",
            description="\n".join([f"✅ {a}" for a in actions]),
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.followup.send(embed=embed)
        
        # Log event
        self.bot.security_manager.log_security_event("LOCKDOWN_DISABLED", {
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id
        })

    # ==================== Whitelist Management ====================

    whitelist_group = app_commands.Group(name="whitelist", description="Manage trusted users who bypass security checks")

    @whitelist_group.command(name="add", description="Add a user to the security whitelist")
    @app_commands.checks.has_permissions(administrator=True)
    async def whitelist_add(self, interaction: discord.Interaction, member: discord.Member):
        self.bot.config_manager.add_to_whitelist(interaction.guild.id, member.id)
        await interaction.response.send_message(f"✅ {member.mention} added to whitelist.", ephemeral=True)

    @whitelist_group.command(name="remove", description="Remove a user from the security whitelist")
    @app_commands.checks.has_permissions(administrator=True)
    async def whitelist_remove(self, interaction: discord.Interaction, member: discord.Member):
        self.bot.config_manager.remove_from_whitelist(interaction.guild.id, member.id)
        await interaction.response.send_message(f"✅ {member.mention} removed from whitelist.", ephemeral=True)

    @whitelist_group.command(name="list", description="List all whitelisted users")
    @app_commands.checks.has_permissions(administrator=True)
    async def whitelist_list(self, interaction: discord.Interaction):
        config = self.bot.config_manager.get_config(interaction.guild.id)
        users = [f"<@{uid}>" for uid in config.whitelisted_user_ids]
        
        embed = discord.Embed(
            title="🛡️ Security Whitelist",
            description="\n".join(users) if users else "No whitelisted users.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==================== Security Dashboard ====================

    @app_commands.command(name="security", description="View and manage server security settings")
    @app_commands.checks.has_permissions(administrator=True)
    async def security_dashboard(self, interaction: discord.Interaction):
        """Main security dashboard"""
        config = self.bot.config_manager.get_config(interaction.guild.id)
        
        embed = discord.Embed(
            title="🛡️ Cipher Security Dashboard",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Anti-Nuke Status
        an_status = "✅ ENABLED" if config.anti_nuke_enabled else "❌ DISABLED"
        embed.add_field(name="Anti-Nuke", value=an_status, inline=True)
        
        # Raid Protection
        raid_metrics = self.bot.raid_protection.get_metrics(interaction.guild.id)
        raid_status = "🚨 ACTIVE RAID" if raid_metrics.is_raid_active else "✅ SECURE"
        embed.add_field(name="Raid Status", value=raid_status, inline=True)
        
        # Bot Detection
        embed.add_field(name="Bot Threshold", value=f"{config.bot_detection_threshold}%", inline=True)
        
        # General Info
        lockdown_mode = self.bot.lockdown_manager.is_locked_down(interaction.guild.id)
        embed.add_field(name="Lockdown Mode", value=lockdown_mode.upper() if lockdown_mode else "NONE", inline=True)
        
        # Metrics
        embed.add_field(name="Recent Joins (1m)", value=str(raid_metrics.joins_last_minute), inline=True)
        embed.add_field(name="Verified Role", value=f"<@&{config.verification_role_id}>" if config.verification_role_id else "Not Set", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==================== Raid Controls ====================

    raid_group = app_commands.Group(name="raid", description="Raid protection management")

    @raid_group.command(name="status", description="View current raid metrics and status")
    @app_commands.checks.has_permissions(administrator=True)
    async def raid_status(self, interaction: discord.Interaction):
        metrics = self.bot.raid_protection.get_metrics(interaction.guild.id)
        
        embed = discord.Embed(
            title="📉 Raid Metrics",
            color=discord.Color.red() if metrics.is_raid_active else discord.Color.green()
        )
        embed.add_field(name="Status", value="🚨 RAID ACTIVE" if metrics.is_raid_active else "✅ Stable", inline=False)
        embed.add_field(name="Joins (Last 60s)", value=str(metrics.joins_last_minute), inline=True)
        embed.add_field(name="Messages (Last 10s)", value=str(metrics.messages_last_10s), inline=True)
        
        if metrics.raid_start_time:
            duration = datetime.utcnow() - metrics.raid_start_time
            embed.add_field(name="Started", value=f"<t:{int(metrics.raid_start_time.timestamp())}:R>", inline=True)
            embed.set_footer(text=f"Raid duration: {duration.seconds}s")
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @raid_group.command(name="end", description="Manually end raid mode and restore verification")
    @app_commands.checks.has_permissions(administrator=True)
    async def raid_end(self, interaction: discord.Interaction):
        self.bot.raid_protection.end_raid(interaction.guild.id)
        # Restore verification level if it was changed
        try:
            await interaction.guild.edit(verification_level=discord.VerificationLevel.medium)
        except: pass
        await interaction.response.send_message("✅ Raid mode ended manually.", ephemeral=True)

    # ==================== System/Owner Commands ====================

    @app_commands.command(name="sync", description="Synchronize or purge slash commands (Owner Only)")
    @app_commands.describe(
        guild_id="Specific Guild ID to sync to (leave empty for global)",
        purge="Clear all commands before syncing?"
    )
    async def sync_commands(self, interaction: discord.Interaction, guild_id: Optional[str] = None, purge: bool = False):
        """Owner-only command to sync or purge slash commands"""
        # Manual check for owner as app_commands.checks.is_owner() can be tricky if not set up
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("❌ This command is restricted to the bot owner.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        
        try:
            target_guild = discord.Object(id=int(guild_id)) if guild_id else None
            
            if purge:
                self.bot.tree.clear_commands(guild=target_guild)
                await self.bot.tree.sync(guild=target_guild)
                msg = "🗑️ Commands purged"
            else:
                msg = "🔄 Commands synchronized"
                
            # Perform final sync
            synced = await self.bot.tree.sync(guild=target_guild)
            
            scope = f"guild `{guild_id}`" if guild_id else "globally"
            await interaction.followup.send(f"✅ {msg} {scope}. ({len(synced)} commands registered)")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Synchronization failed: {e}")
            logging.error(f"Sync error: {e}")

    # ==================== Verification Commands ====================

    verify_group = app_commands.Group(name="verify", description="Manage customizable verification system")

    @verify_group.command(name="set_channel", description="Set the channel for verification messages")
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.bot.config_manager.update_config(interaction.guild.id, verification_channel_id=channel.id)
        await interaction.response.send_message(f"✅ Verification channel set to {channel.mention}.", ephemeral=True)

    @verify_group.command(name="set_role", description="Set the role given upon verification")
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_set_role(self, interaction: discord.Interaction, role: discord.Role):
        self.bot.config_manager.update_config(interaction.guild.id, verification_role_id=role.id)
        await interaction.response.send_message(f"✅ Verification role set to **{role.name}**.", ephemeral=True)

    @verify_group.command(name="set_unverified_role", description="Set the role removed upon verification (e.g. Restricted)")
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_set_unverified_role(self, interaction: discord.Interaction, role: discord.Role):
        self.bot.config_manager.update_config(interaction.guild.id, unverified_role_id=role.id)
        await interaction.response.send_message(f"✅ Unverified role set to **{role.name}**.", ephemeral=True)

    @verify_group.command(name="set_title", description="Set the title of the verification embed")
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_set_title(self, interaction: discord.Interaction, title: str):
        self.bot.config_manager.update_config(interaction.guild.id, verification_title=title)
        await interaction.response.send_message(f"✅ Verification title set to: **{title}**.", ephemeral=True)

    @verify_group.command(name="set_description", description="Set the description of the verification embed")
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_set_description(self, interaction: discord.Interaction, description: str):
        # Allow \n for newlines in input
        description = description.replace("\\n", "\n")
        self.bot.config_manager.update_config(interaction.guild.id, verification_description=description)
        await interaction.response.send_message(f"✅ Verification description updated.", ephemeral=True)

    @verify_group.command(name="set_button", description="Set the label of the verification button")
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_set_button(self, interaction: discord.Interaction, label: str):
        self.bot.config_manager.update_config(interaction.guild.id, verification_button_label=label)
        await interaction.response.send_message(f"✅ Verification button label set to: **{label}**.", ephemeral=True)

    @verify_group.command(name="set_image", description="Set the image URL for the verification embed")
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_set_image(self, interaction: discord.Interaction, url: str):
        self.bot.config_manager.update_config(interaction.guild.id, verification_image_url=url)
        await interaction.response.send_message(f"✅ Verification image URL updated.", ephemeral=True)

    @verify_group.command(name="send", description="Send the customized verification message to the configured channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_send(self, interaction: discord.Interaction):
        config = self.bot.config_manager.get_config(interaction.guild.id)
        channel = interaction.guild.get_channel(config.verification_channel_id) if config.verification_channel_id else interaction.channel
        
        if not channel:
            await interaction.response.send_message("❌ Configuration error: Verification channel not found.", ephemeral=True)
            return

        embed = discord.Embed(
            title=config.verification_title,
            description=config.verification_description,
            color=discord.Color.blue()
        )
        if config.verification_image_url:
            embed.set_image(url=config.verification_image_url)
        
        view = VerificationView(self.bot, interaction.guild.id)
        # Update button label
        view.verify_button.label = config.verification_button_label
        
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Verification message sent to {channel.mention}.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SecurityDashboard(bot))
