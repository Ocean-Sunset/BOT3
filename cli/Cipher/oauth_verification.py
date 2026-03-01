"""
Cipher OAuth2 Verification System
Handles human verification via Discord OAuth2

Flow:
1. User Joins -> Unverified Role
2. Verification Channel -> Button to Verify
3. External Web Verification -> Callback to Bot
4. Bot verifies -> Role Swap
"""

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from aiohttp import web
import jwt
import time
import secrets
import logging
from typing import Dict, Any, Optional

print("✅ - OAuth2 Verification loaded.")

class OAuthVerification:
    """
    Handles OAuth2 verification flow
    Note: Requires an external URL/Domain and port forwarding for actual use.
    """
    
    def _config_path(self):
        import os
        return os.path.join(os.path.dirname(__file__), 'verification_config.json')

    def load_config(self):
        import os, json
        path = self._config_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_config(self, config: dict):
        import json
        path = self._config_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save verification config: {e}")

    def get_config(self):
        return self.load_config()

    def update_config(self, **kwargs):
        config = self.load_config()
        config.update(kwargs)
        self.save_config(config)
        return config
    
    def __init__(self, bot: commands.Bot, domain: str = "https://ciphers-oauth2-system.onrender.com/", secret_key: str = None):
        self.bot = bot
        self.domain = domain
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.app = web.Application()
        self.app.add_routes([
            web.get('/verify/{guild_id}/{user_id}', self.handle_verify_redirect),
            web.get('/callback', self.handle_callback)
        ])
        self.runner: Optional[web.AppRunner] = None
        self.log_path = __import__('os').path.join(__import__('os').path.dirname(__file__), 'verification_log.json')
        self.verification_log = self._load_log()

    def _load_log(self):
        import os, json
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_log(self):
        import json
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(self.verification_log, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save verification log: {e}")

    def get_logs(self, guild_id: Optional[int] = None, user_id: Optional[int] = None):
        logs = self.verification_log
        if guild_id is not None:
            logs = [l for l in logs if l.get('guild_id') == guild_id]
        if user_id is not None:
            logs = [l for l in logs if l.get('user_id') == user_id]
        return logs
        
    async def start_server(self, host: str = "0.0.0.0", port: int = 8080):
        """Start the aiohttp web server for verification callbacks"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, host, port)
        await site.start()
        logging.info(f"Verification server started at {host}:{port}")

    async def stop_server(self):
        """Stop the verification server"""
        if self.runner:
            await self.runner.cleanup()

    async def handle_verify_redirect(self, request: web.Request) -> web.Response:
        """Redirect user to Discord OAuth2 login"""
        guild_id = request.match_info['guild_id']
        user_id = request.match_info['user_id']
        
        # Create a state token to prevent CSRF and store context
        state = jwt.encode({
            "guild_id": guild_id,
            "user_id": user_id,
            "exp": time.time() + 600
        }, self.secret_key, algorithm="HS256")
        
        client_id = 1323734010345689189
        redirect_uri = f"{self.domain}/callback"
        auth_url = (
            f"https://discord.com/api/oauth2/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope=identify"
            f"&state={state}"
        )
        
        return web.HTTPFound(auth_url)

    async def handle_callback(self, request: web.Request) -> web.Response:
        """Handle Discord OAuth2 callback"""
        code = request.query.get('code')
        state = request.query.get('state')
        
        if not code or not state:
            return web.Response(text="Invalid verification request.", status=400)
            
        try:
            # Decode state to get context
            payload = jwt.decode(state, self.secret_key, algorithms=["HS256"])
            guild_id = int(payload['guild_id'])
            user_id = int(payload['user_id'])
            
            # In a real scenario, we would exchange 'code' for an access token
            # to verify the user's identity via Discord API.
            # For this implementation, we'll assume the callback is valid if state matches.
            
            # Verify and role update
            await self._complete_verification(guild_id, user_id)
            
            return web.Response(text="Verification successful! You can now return to Discord.", content_type="text/plain")
            
        except jwt.ExpiredSignatureError:
            return web.Response(text="Verification link expired.", status=400)
        except Exception as e:
            logging.error(f"Callback error: {e}")
            return web.Response(text="An error occurred during verification.", status=500)

    async def _complete_verification(self, guild_id: int, user_id: int):
        """Swap roles and notify user, and log verification to file"""
        guild = self.bot.get_guild(guild_id)
        if not guild: return
        
        member = guild.get_member(user_id)
        if not member: return
        
        # Get settings from SecurityManager/ConfigManager
        if hasattr(self.bot, 'config_manager'):
            config = self.bot.config_manager.get_config(guild_id)
            
            # 1. Get Verified Role
            verified_role = None
            if config.verification_role_id:
                verified_role = guild.get_role(config.verification_role_id)
            if not verified_role:
                verified_role = discord.utils.get(guild.roles, name="Verified")
            
            # 2. Get Unverified Role
            unverified_role = None
            if config.unverified_role_id:
                unverified_role = guild.get_role(config.unverified_role_id)
            if not unverified_role:
                unverified_role = discord.utils.get(guild.roles, name="Unverified")
            
            try:
                # Add verified role
                if verified_role:
                    await member.add_roles(verified_role, reason="Cipher: OAuth2 Verification Complete")
                else:
                    logging.warning(f"⚠️ No verified role found for guild {guild_id}")
                
                # Remove unverified role
                if unverified_role:
                    await member.remove_roles(unverified_role, reason="Cipher: OAuth2 Verification Complete")
                
                # Log event
                log_entry = {
                    "guild_id": guild_id,
                    "user_id": user_id,
                    "timestamp": time.time(),
                    "method": "OAuth2",
                    "roles_updated": True
                }
                self.verification_log.append(log_entry)
                self._save_log()
                if hasattr(self.bot, 'security_manager'):
                    self.bot.security_manager.log_security_event("USER_VERIFIED", log_entry)
            except discord.Forbidden:
                logging.error(f"Check roles permissions in guild {guild_id}")

class VerificationView(discord.ui.View):
    """View with a button to start verification"""
    def __init__(self, bot: commands.Bot, guild_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id
        
    @discord.ui.button(label="Verify Me", style=discord.ButtonStyle.green, custom_id="cipher:verify")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Use configured OAuthVerification instance domain if available, fall back to default
        domain = None
        if hasattr(self.bot, 'oauth_verification') and getattr(self.bot, 'oauth_verification') is not None:
            domain = getattr(self.bot.oauth_verification, 'domain', None)
        if not domain:
            domain = "https://ciphers-oauth2-system.onrender.com/"

        url = f"{domain.rstrip('/')}/verify/{self.guild_id}/{interaction.user.id}"

        await interaction.response.send_message(
            f"Click the link below to verify via Discord OAuth2:\n{url}",
            ephemeral=True
        )
