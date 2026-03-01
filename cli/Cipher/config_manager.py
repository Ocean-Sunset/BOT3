"""
Cipher Configuration Manager
Handles per-guild security settings and persistence

Features:
- Enable/disable individual security modules
- Configure detection thresholds
- Manage whitelisted users
- Set security alerts channels
- JSON-based persistence
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict, field

print("✅ - Config Manager loaded.")

@dataclass
class GuildSecurityConfig:
    """Security configuration for a single guild"""
    guild_id: int
    bot_detection_threshold: int = 60
    raid_join_threshold: int = 10
    raid_message_threshold: int = 20
    anti_nuke_enabled: bool = True
    anti_nuke_protections: Dict[str, bool] = field(default_factory=lambda: {
        "ban": True,
        "kick": True,
        "role": True,
        "channel": True,
        "webhook": True
    })
    verification_enabled: bool = False
    verification_channel_id: Optional[int] = None
    verification_role_id: Optional[int] = None
    unverified_role_id: Optional[int] = None
    verification_title: str = "Member Verification"
    verification_description: str = "Welcome! Click the button below to verify your account and gain access to the server."
    verification_button_label: str = "Verify Me"
    verification_image_url: Optional[str] = None
    security_alerts_channel_id: Optional[int] = None
    whitelisted_user_ids: List[int] = field(default_factory=list)

class ConfigManager:
    """
    Manages security configurations across all guilds
    """
    
    def __init__(self, config_path: str = "config/security_configs.json"):
        self.config_path = config_path
        self.configs: Dict[int, GuildSecurityConfig] = {}
        self._ensure_config_dir()
        self.load_all()
        
    def _ensure_config_dir(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
    def load_all(self):
        """Load all guild configurations from disk"""
        if not os.path.exists(self.config_path):
            self.configs = {}
            return
            
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                for guild_id_str, config_data in data.items():
                    guild_id = int(guild_id_str)
                    # Handle nested anti_nuke_protections if they don't exist in older data
                    if "anti_nuke_protections" not in config_data:
                        config_data["anti_nuke_protections"] = {
                            "ban": True, "kick": True, "role": True, "channel": True, "webhook": True
                        }
                    self.configs[guild_id] = GuildSecurityConfig(**config_data)
        except Exception as e:
            logging.error(f"Failed to load security configs: {e}")
            self.configs = {}
            
    def save_all(self):
        """Save all configurations to disk"""
        try:
            data = {str(k): asdict(v) for k, v in self.configs.items()}
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save security configs: {e}")
            
    def get_config(self, guild_id: int) -> GuildSecurityConfig:
        """Get config for a guild, creates default if missing"""
        if guild_id not in self.configs:
            self.configs[guild_id] = GuildSecurityConfig(guild_id=guild_id)
            self.save_all()
        return self.configs[guild_id]
        
    def update_config(self, guild_id: int, **kwargs):
        """Update specific settings in a guild's config"""
        config = self.get_config(guild_id)
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        self.save_all()
        
    def is_whitelisted(self, guild_id: int, user_id: int) -> bool:
        """Check if a user is whitelisted in a guild"""
        config = self.get_config(guild_id)
        return user_id in config.whitelisted_user_ids
        
    def add_to_whitelist(self, guild_id: int, user_id: int):
        config = self.get_config(guild_id)
        if user_id not in config.whitelisted_user_ids:
            config.whitelisted_user_ids.append(user_id)
            self.save_all()
            
    def remove_from_whitelist(self, guild_id: int, user_id: int):
        config = self.get_config(guild_id)
        if user_id in config.whitelisted_user_ids:
            config.whitelisted_user_ids.remove(user_id)
            self.save_all()
