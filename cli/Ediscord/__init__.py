"""
# Ediscord
Cog package for the Prowl Discord bot.

Contains:
- Shared utilities and variables
- Helper functions for the main bot
- Builder utilities for embeds, buttons, links, and modals

**Copyright (C) 2025 th3_t1sm. (GPL v3)**
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

__version__ = "1.6.3"
__author__ = "th3_t1sm"


def __getattr__(name):
    if name in ("EmbedBuilder", "ButtonBuilder", "ModalBuilder", "LinkBuilder", "quick_embed", "success_embed", "error_embed", "info_embed"):
        import importlib
        mod = importlib.import_module("Ediscord.builders")
        return getattr(mod, name)
    if name in ("variables", "utils", "db"):
        import importlib
        return importlib.import_module(f"Ediscord.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")