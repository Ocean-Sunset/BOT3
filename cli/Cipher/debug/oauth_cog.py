"""OAuth management cog that integrates with `oauth_verification.py`.

Commands:
- /oauth_start domain port : start the verification HTTP server and attach to `bot.oauth_verification`
- /oauth_stop : stop the server and remove `bot.oauth_verification`
- /oauth_status : show server/domain/status
- /oauth_link [user] : produce a verification link for the user (or caller)

This uses the existing `OAuthVerification` implementation in `Cipher.oauth_verification`.
"""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from Cipher.oauth_verification import OAuthVerification


class OAuthCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="oauth_start")
    @app_commands.describe(domain="Base domain for verification callbacks (e.g. https://example.com)", port="Port for local server (default 8080)")
    async def oauth_start(self, interaction: discord.Interaction, domain: Optional[str] = None, port: int = 8080):
        """Start the local verification callback server and attach it to the bot."""
        await interaction.response.defer(ephemeral=True)

        # Create instance and start
        ov = OAuthVerification(self.bot, domain=domain or None)
        try:
            await ov.start_server(port=port)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to start server: {e}", ephemeral=True)
            return

        self.bot.oauth_verification = ov
        if hasattr(self.bot, 'security_manager'):
            await self.bot.security_manager.log_security_event("OAUTH_SERVER_STARTED", {"user": interaction.user.id, "domain": ov.domain, "port": port})

        await interaction.followup.send(f"✅ Verification server started at {ov.domain} (port {port}).", ephemeral=True)

    @app_commands.command(name="oauth_stop")
    async def oauth_stop(self, interaction: discord.Interaction):
        """Stop the verification server and detach it."""
        await interaction.response.defer(ephemeral=True)
        ov = getattr(self.bot, 'oauth_verification', None)
        if not ov:
            await interaction.followup.send("🔌 No verification server is running.", ephemeral=True)
            return

        try:
            await ov.stop_server()
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to stop server: {e}", ephemeral=True)
            return

        delattr(self.bot, 'oauth_verification')
        if hasattr(self.bot, 'security_manager'):
            await self.bot.security_manager.log_security_event("OAUTH_SERVER_STOPPED", {"user": interaction.user.id})

        await interaction.followup.send("✅ Verification server stopped.", ephemeral=True)

    @app_commands.command(name="oauth_status")
    async def oauth_status(self, interaction: discord.Interaction):
        """Show status of the verification server."""
        ov = getattr(self.bot, 'oauth_verification', None)
        if not ov:
            await interaction.response.send_message("🔌 No verification server configured.", ephemeral=True)
            return

        status = "running" if getattr(ov, 'runner', None) else "not running"
        await interaction.response.send_message(f"Domain: {ov.domain}\nStatus: {status}", ephemeral=True)

    @app_commands.command(name="oauth_link")
    @app_commands.describe(target_user="User to produce a verification link for (defaults to you)")
    async def oauth_link(self, interaction: discord.Interaction, target_user: Optional[discord.User] = None):
        """Produce a verification link for `target_user` (or caller)."""
        user = target_user or interaction.user
        ov = getattr(self.bot, 'oauth_verification', None)
        if not ov:
            await interaction.response.send_message("❌ Verification server not configured. Use /oauth_start first.", ephemeral=True)
            return

        url = f"{ov.domain.rstrip('/')}\/verify/{interaction.guild.id}/{user.id}"
        if hasattr(self.bot, 'security_manager'):
            await self.bot.security_manager.log_security_event("OAUTH_LINK_GENERATED", {"user": interaction.user.id, "target": user.id})

        await interaction.response.send_message(f"🔗 Verification link: {url}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(OAuthCog(bot))
    print("✅ - OAuth management cog loaded.")
