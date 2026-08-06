import discord
from discord.ext import commands
from discord import app_commands
import json
import asyncio
import datetime
from typing import Optional

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db


GC_DEFAULTS = {"enabled": False, "channel_id": None, "global_channel_id": None}


class GlobalChat(commands.Cog, name="GlobalChat"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_linked_channel(self):
        pool = await neon_db.get_pool()
        if not pool:
            return None
        row = await pool.fetchrow("SELECT value FROM bot_stats WHERE key = 'global_chat_channel'")
        return str(row["value"]) if row else None

    async def set_linked_channel(self, channel_id: str):
        pool = await neon_db.get_pool()
        if not pool:
            return
        await pool.execute(
            "INSERT INTO bot_stats (key, value) VALUES ('global_chat_channel', $1) ON CONFLICT (key) DO UPDATE SET value = $1",
            channel_id,
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        hub_channel_id = await self.get_linked_channel()
        if not hub_channel_id:
            return
        if str(message.channel.id) != str(hub_channel_id):
            return

        content = message.content[:1000] if message.content else "[attachment]"
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if str(channel.id) == str(hub_channel_id) and str(channel.id) != str(message.channel.id):
                    webhooks = await channel.webhooks()
                    webhook = discord.utils.get(webhooks, name="GlobalChat")
                    if not webhook:
                        try:
                            webhook = await channel.create_webhook(name="GlobalChat")
                        except Exception as e:
                            logger.warning(f"Failed to create GlobalChat webhook: {e}")
                            continue
                    try:
                        await webhook.send(
                            content=content,
                            username=f"{message.author.display_name} ({message.guild.name})",
                            avatar_url=message.author.display_avatar.url,
                        )
                    except Exception as e:
                        logger.warning(f"GlobalChat webhook send failed: {e}")
                        continue

    gc_group = app_commands.Group(name="globalchat", description="Global chat commands")

    @gc_group.command(name="link", description="Link this channel to the global chat network")
    async def link(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        await self.set_linked_channel(str(interaction.channel_id))
        embed = (
            EmbedBuilder()
            .title("Global Chat Linked")
            .description(f"This channel ({interaction.channel.mention}) is now linked to the global chat!")
            .color("green")
            .field("Channel ID", str(interaction.channel_id))
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)

    @gc_group.command(name="unlink", description="Unlink this channel from the global chat")
    async def unlink(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        await self.set_linked_channel("0")
        await interaction.response.send_message(
            embed=EmbedBuilder().title("Global Chat Unlinked").description("This channel has been unlinked from global chat.").color("orange").timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )

    @gc_group.command(name="info", description="Check global chat status")
    async def info(self, interaction: discord.Interaction):
        hub_channel_id = await self.get_linked_channel()
        if hub_channel_id and hub_channel_id != "0":
            channel = self.bot.get_channel(int(hub_channel_id))
            embed = (
                EmbedBuilder()
                .title("Global Chat Status")
                .description(f"Global chat is linked to {channel.mention if channel else f'<#{hub_channel_id}>'}")
                .color("green")
                .field("Channel ID", str(hub_channel_id))
                .timestamp(datetime.datetime.utcnow())
                .build()
            )
        else:
            embed = (
                EmbedBuilder()
                .title("Global Chat Status")
                .description("Global chat is not set up yet.")
                .color("red")
                .timestamp(datetime.datetime.utcnow())
                .build()
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GlobalChat(bot))
