import discord
from discord.ext import commands
from Ediscord import utils, variables
import json
import logging
import typing
import os


from discord import app_commands

class ChatReviver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    chatreviver = app_commands.Group(name="chatreviver", description="Chat reviver configuration commands.")


    @chatreviver.command(name="toggle", description="Enable or disable chat reviver for this server.")
    @utils.admin_or_owner()
    async def cr_toggle(self, interaction: discord.Interaction, enabled: bool):
        """
        Enable or disable chat reviver for this server.
        Usage: /chatreviver toggle enabled:true/false
        """
        settings = utils.load_server_settings()
        guild_settings = settings.setdefault(str(interaction.guild.id), {})
        chat_settings = guild_settings.setdefault("chat_reviver", {
            "enabled": False,
            "interval": 60,  # Default 60 minutes
            "channel": None,  # Default to None (will find general/chat channel)
            "role": "Chat Reviver",  # Default role name
            "messages": variables.chat_reviver_messages.copy()  # Copy default messages
        })
        chat_settings["enabled"] = enabled
        settings[str(interaction.guild.id)] = guild_settings
        utils.save_server_settings(settings)
        if enabled:
            await interaction.response.send_message("✅ Chat reviver enabled for this server.")
        else:
            await interaction.response.send_message("✅ Chat reviver disabled for this server.")

    @chatreviver.command(name="interval", description="Set how often the chat reviver sends messages.")
    @utils.admin_or_owner()
    async def cr_interval(self, interaction: discord.Interaction, minutes: int):
        if minutes < 1:
            await interaction.response.send_message("❌ Interval must be at least 1 minute.")
            return
        settings = utils.load_server_settings()
        guild_settings = settings.setdefault(str(interaction.guild.id), {})
        chat_settings = guild_settings.setdefault("chat_reviver", {
            "enabled": False,
            "interval": 60,
            "channel": None,
            "role": "Chat Reviver",
            "messages": variables.chat_reviver_messages.copy()
        })
        chat_settings["interval"] = minutes
        settings[str(interaction.guild.id)] = guild_settings
        utils.save_server_settings(settings)
        await interaction.response.send_message(f"✅ Chat reviver interval set to {minutes} minutes.")

    @chatreviver.command(name="channel", description="Set which channel to send chat reviver messages in.")
    @utils.admin_or_owner()
    async def cr_channel(self, interaction: discord.Interaction, channel: typing.Optional[discord.TextChannel] = None):
        if channel is None:
            channel = interaction.channel
        settings = utils.load_server_settings()
        guild_settings = settings.setdefault(str(interaction.guild.id), {})
        chat_settings = guild_settings.setdefault("chat_reviver", {
            "enabled": False,
            "interval": 60,
            "channel": None,
            "role": "Chat Reviver", 
            "messages": variables.chat_reviver_messages.copy()
        })
        chat_settings["channel"] = channel.name
        settings[str(interaction.guild.id)] = guild_settings
        utils.save_server_settings(settings)
        await interaction.response.send_message(f"✅ Chat reviver channel set to {channel.mention}.")

    @chatreviver.command(name="role", description="Set which role to mention in chat reviver messages.")
    @utils.admin_or_owner()
    async def cr_role(self, interaction: discord.Interaction, role_name: str):
        settings = utils.load_server_settings()
        guild_settings = settings.setdefault(str(interaction.guild.id), {})
        chat_settings = guild_settings.setdefault("chat_reviver", {
            "enabled": False,
            "interval": 60,
            "channel": None,
            "role": "Chat Reviver",
            "messages": variables.chat_reviver_messages.copy()
        })
        chat_settings["role"] = role_name
        settings[str(interaction.guild.id)] = guild_settings
        utils.save_server_settings(settings)
        await interaction.response.send_message(f"✅ Chat reviver role set to '{role_name}'.")

    @chatreviver.command(name="addmessage", description="Add a custom chat reviver message.")
    @utils.admin_or_owner()
    async def cr_addmessage(self, interaction: discord.Interaction, message: str):
        settings = utils.load_server_settings()
        guild_settings = settings.setdefault(str(interaction.guild.id), {})
        chat_settings = guild_settings.setdefault("chat_reviver", {
            "enabled": False,
            "interval": 60,
            "channel": None,
            "role": "Chat Reviver",
            "messages": variables.chat_reviver_messages.copy()
        })
        chat_settings["messages"].append(message)
        settings[str(interaction.guild.id)] = guild_settings
        utils.save_server_settings(settings)
        await interaction.response.send_message(f"✅ Added new chat reviver message:\n{message}")

    @chatreviver.command(name="removemessage", description="Remove a custom chat reviver message by its number.")
    @utils.admin_or_owner()
    async def cr_removemessage(self, interaction: discord.Interaction, number: int):
        settings = utils.load_server_settings()
        guild_settings = settings.setdefault(str(interaction.guild.id), {})
        chat_settings = guild_settings.setdefault("chat_reviver", {
            "enabled": False,
            "interval": 60,
            "channel": None, 
            "role": "Chat Reviver",
            "messages": variables.chat_reviver_messages.copy()
        })
        if number < 1 or number > len(chat_settings["messages"]):
            await interaction.response.send_message(f"❌ Please specify a valid message number between 1 and {len(chat_settings['messages'])}.")
            return
        removed = chat_settings["messages"].pop(number - 1)
        settings[str(interaction.guild.id)] = guild_settings
        utils.save_server_settings(settings)
        await interaction.response.send_message(f"✅ Removed message:\n{removed}")

    @chatreviver.command(name="messages", description="List all custom chat reviver messages.")
    @utils.admin_or_owner()
    async def cr_messages(self, interaction: discord.Interaction):
        settings = utils.load_server_settings()
        guild_settings = settings.setdefault(str(interaction.guild.id), {})
        chat_settings = guild_settings.setdefault("chat_reviver", {
            "enabled": False,
            "interval": 60,
            "channel": None,
            "role": "Chat Reviver",
            "messages": variables.chat_reviver_messages.copy()
        })
        if not chat_settings["messages"]:
            await interaction.response.send_message("No custom chat reviver messages set.")
            return
        messages = []
        for i, msg in enumerate(chat_settings["messages"], 1):
            messages.append(f"{i}. {msg}")
        await interaction.response.send_message("# Chat Reviver Messages:\n" + "\n".join(messages))

    @chatreviver.command(name="settings", description="Show current chat reviver settings.")
    @utils.admin_or_owner()
    async def cr_settings(self, interaction: discord.Interaction):
        settings = utils.load_server_settings()
        guild_settings = settings.setdefault(str(interaction.guild.id), {})
        chat_settings = guild_settings.setdefault("chat_reviver", {
            "enabled": False,
            "interval": 60,
            "channel": None,
            "role": "Chat Reviver",
            "messages": variables.chat_reviver_messages.copy()
        })
        embed = discord.Embed(
            title="Chat Reviver Settings",
            color=discord.Color.blue()
        )
        embed.add_field(name="Enabled", value="Yes" if chat_settings["enabled"] else "No", inline=False)
        embed.add_field(name="Interval", value=f"{chat_settings['interval']} minutes", inline=False)
        embed.add_field(name="Channel", value=chat_settings["channel"] or "Auto-detect (general/chat)", inline=False) 
        embed.add_field(name="Role", value=chat_settings["role"], inline=False)
        embed.add_field(name="Number of Messages", value=str(len(chat_settings["messages"])), inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    cog = ChatReviver(bot)
    bot.tree.add_command(cog.chatreviver)
    await bot.add_cog(cog)