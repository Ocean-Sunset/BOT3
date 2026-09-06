import discord
from discord.ext import commands
from discord import app_commands
import json
import datetime

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db
from Ediscord.builders import emoji_title


# ── Helpers ────────────────────────────────────────────────────────────────

async def _get_stat(key: str):
    pool = await neon_db.get_pool()
    if not pool:
        return None
    row = await pool.fetchrow("SELECT value FROM bot_stats WHERE key = ?", key)
    return row["value"] if row else None


async def _set_stat(key: str, value: str):
    pool = await neon_db.get_pool()
    if not pool:
        return
    await pool.execute(
        "INSERT INTO bot_stats (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
        key, value,
    )


def _gc_key(guild_id: int, suffix: str) -> str:
    return f"global_chat_{suffix}_{guild_id}"


async def _get_bool(guild_id: int, suffix: str, default: bool = False) -> bool:
    val = await _get_stat(_gc_key(guild_id, suffix))
    if val is None:
        return default
    return val.lower() == "true"


async def _set_bool(guild_id: int, suffix: str, value: bool):
    await _set_stat(_gc_key(guild_id, suffix), str(value))


async def _get_list(guild_id: int, suffix: str) -> list:
    val = await _get_stat(_gc_key(guild_id, suffix))
    if not val:
        return []
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return []


async def _set_list(guild_id: int, suffix: str, items: list):
    await _set_stat(_gc_key(guild_id, suffix), json.dumps(items))


# ── Persistent View ────────────────────────────────────────────────────────

class GCBlockUserModal(discord.ui.Modal, title="Block User from Global Chat"):
    user_id = discord.ui.TextInput(label="User ID or @mention", placeholder="e.g. 123456789012345678 or @user", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.user_id.value.strip()
        uid = raw.strip("<@!>")
        if not uid.isdigit():
            return await interaction.response.send_message("Invalid user ID.", ephemeral=True)
        blocked = await _get_list(interaction.guild_id, "gc_blocked_users")
        if uid not in blocked:
            blocked.append(uid)
            await _set_list(interaction.guild_id, "gc_blocked_users", blocked)
        await interaction.response.send_message(f"Blocked user `{uid}` from global chat.", ephemeral=True)
        await _refresh_panel(interaction.client, interaction.guild_id)


class GCUnblockUserModal(discord.ui.Modal, title="Unblock User from Global Chat"):
    user_id = discord.ui.TextInput(label="User ID or @mention", placeholder="e.g. 123456789012345678 or @user", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.user_id.value.strip()
        uid = raw.strip("<@!>")
        if not uid.isdigit():
            return await interaction.response.send_message("Invalid user ID.", ephemeral=True)
        blocked = await _get_list(interaction.guild_id, "gc_blocked_users")
        if uid in blocked:
            blocked.remove(uid)
            await _set_list(interaction.guild_id, "gc_blocked_users", blocked)
        await interaction.response.send_message(f"Unblocked user `{uid}` from global chat.", ephemeral=True)
        await _refresh_panel(interaction.client, interaction.guild_id)


class GCBlockServerModal(discord.ui.Modal, title="Block Server from Global Chat"):
    server_id = discord.ui.TextInput(label="Server ID", placeholder="e.g. 123456789012345678", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.server_id.value.strip()
        if not raw.isdigit():
            return await interaction.response.send_message("Invalid server ID.", ephemeral=True)
        blocked = await _get_list(interaction.guild_id, "gc_blocked_servers")
        if raw not in blocked:
            blocked.append(raw)
            await _set_list(interaction.guild_id, "gc_blocked_servers", blocked)
        await interaction.response.send_message(f"Blocked server `{raw}` from global chat.", ephemeral=True)
        await _refresh_panel(interaction.client, interaction.guild_id)


class GCUnblockServerModal(discord.ui.Modal, title="Unblock Server from Global Chat"):
    server_id = discord.ui.TextInput(label="Server ID", placeholder="e.g. 123456789012345678", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.server_id.value.strip()
        if not raw.isdigit():
            return await interaction.response.send_message("Invalid server ID.", ephemeral=True)
        blocked = await _get_list(interaction.guild_id, "gc_blocked_servers")
        if raw in blocked:
            blocked.remove(raw)
            await _set_list(interaction.guild_id, "gc_blocked_servers", blocked)
        await interaction.response.send_message(f"Unblocked server `{raw}` from global chat.", ephemeral=True)
        await _refresh_panel(interaction.client, interaction.guild_id)


class GCPickChannelModal(discord.ui.Modal, title="Change Global Chat Channel"):
    channel_id = discord.ui.TextInput(label="Channel ID", placeholder="Paste the new channel ID", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.channel_id.value.strip()
        if not raw.isdigit():
            return await interaction.response.send_message("Invalid channel ID.", ephemeral=True)
        ch = interaction.guild.get_channel(int(raw))
        if ch is None:
            return await interaction.response.send_message("Channel not found in this server.", ephemeral=True)
        if not isinstance(ch, (discord.TextChannel, discord.Thread)):
            return await interaction.response.send_message("Must be a text channel.", ephemeral=True)
        await _set_stat(_gc_key(interaction.guild_id, "channel"), str(raw))
        await interaction.response.send_message(f"Global chat channel set to {ch.mention}.", ephemeral=True)
        await _refresh_panel(interaction.client, interaction.guild_id)


def _build_panel_embed(guild: discord.Guild, enabled: bool, muted: bool,
                       channel_id: str | None, blocked_users: list, blocked_servers: list):
    ch_mention = f"<#{channel_id}>" if channel_id else "Not set"
    status = "🟢 Enabled" if enabled else "🔴 Disabled"
    mute_str = "🔇 Muted" if muted else "🔊 Active"
    users_str = ", ".join(f"`{u}`" for u in blocked_users[:10]) or "None"
    servers_str = ", ".join(f"`{s}`" for s in blocked_servers[:10]) or "None"
    if len(blocked_users) > 10:
        users_str += f" +{len(blocked_users) - 10} more"
    if len(blocked_servers) > 10:
        servers_str += f" +{len(blocked_servers) - 10} more"
    embed = (
        EmbedBuilder()
        .title(emoji_title("globe", "Global Chat Control Panel"))
        .color("blue" if enabled else "gray")
        .field("Status", status, inline=True)
        .field("Audio", mute_str, inline=True)
        .field("Channel", ch_mention, inline=True)
        .field("Blocked Users", users_str, inline=False)
        .field("Blocked Servers", servers_str, inline=False)
        .description("Use the buttons below to manage global chat.")
        .timestamp(datetime.datetime.utcnow())
        .build()
    )
    return embed


class GCControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        perms = interaction.user.guild_permissions
        if not (perms.manage_guild or perms.administrator):
            await interaction.response.send_message("You need Manage Server permission.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Mute", emoji="<:mute_white:1546113568527749220>", custom_id="gc_btn_mute", style=discord.ButtonStyle.danger)
    async def btn_mute(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _set_bool(interaction.guild_id, "gc_muted", True)
        await interaction.response.send_message("Global chat muted.", ephemeral=True)
        await _refresh_panel(interaction.client, interaction.guild_id)

    @discord.ui.button(label="Unmute", emoji="<:unmute_white:1546113892978270248>", custom_id="gc_btn_unmute", style=discord.ButtonStyle.success)
    async def btn_unmute(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _set_bool(interaction.guild_id, "gc_muted", False)
        await interaction.response.send_message("Global chat unmuted.", ephemeral=True)
        await _refresh_panel(interaction.client, interaction.guild_id)

    @discord.ui.button(label="Block User", emoji="<:user_block_white:1546114552104493066>", custom_id="gc_btn_block_user", style=discord.ButtonStyle.secondary)
    async def btn_block_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GCBlockUserModal())

    @discord.ui.button(label="Unblock User", emoji="<:user_unblock_white:1546114944385286144>", custom_id="gc_btn_unblock_user", style=discord.ButtonStyle.secondary)
    async def btn_unblock_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GCUnblockUserModal())

    @discord.ui.button(label="Block Server", emoji="<:server_block_white:1546115797007597639>", custom_id="gc_btn_block_server", style=discord.ButtonStyle.secondary)
    async def btn_block_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GCBlockServerModal())

    @discord.ui.button(label="Unblock Server", emoji="<:server_unblock_white:1546116037773230163>", custom_id="gc_btn_unblock_server", style=discord.ButtonStyle.secondary)
    async def btn_unblock_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GCUnblockServerModal())

    @discord.ui.button(label="Change Channel", emoji="<:reload_channels:1546116677719298078>", custom_id="gc_btn_change_channel", style=discord.ButtonStyle.primary)
    async def btn_change_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GCPickChannelModal())

    @discord.ui.button(label="Toggle Global Chat", emoji="<:CURRENT_OFF:1546117436556714155>", custom_id="gc_btn_toggle", style=discord.ButtonStyle.danger, row=4)
    async def btn_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        current = await _get_bool(interaction.guild_id, "gc_enabled")
        new_state = not current
        await _set_bool(interaction.guild_id, "gc_enabled", new_state)
        state_str = "enabled" if new_state else "disabled"
        await interaction.response.send_message(f"Global chat {state_str}.", ephemeral=True)
        await _refresh_panel(interaction.client, interaction.guild_id)


async def _refresh_panel(bot: commands.Bot, guild_id: int):
    """Re-post (edit) the control panel embed in the management channel."""
    mgmt_ch_id = await _get_stat(_gc_key(guild_id, "gc_management_channel"))
    if not mgmt_ch_id:
        return
    guild = bot.get_guild(guild_id)
    if not guild:
        return
    ch = guild.get_channel(int(mgmt_ch_id))
    if not ch:
        return
    enabled = await _get_bool(guild_id, "gc_enabled")
    muted = await _get_bool(guild_id, "gc_muted")
    channel_id = await _get_stat(_gc_key(guild_id, "channel"))
    blocked_users = await _get_list(guild_id, "gc_blocked_users")
    blocked_servers = await _get_list(guild_id, "gc_blocked_servers")
    embed = _build_panel_embed(guild, enabled, muted, channel_id, blocked_users, blocked_servers)
    view = GCControlView()
    if enabled:
        view.btn_toggle.emoji = "<:CURRENT_ON:1546117669932114014>"
        view.btn_toggle.style = discord.ButtonStyle.success
    else:
        view.btn_toggle.emoji = "<:CURRENT_OFF:1546117436556714155>"
        view.btn_toggle.style = discord.ButtonStyle.danger
    try:
        async for message in ch.history(limit=50):
            if message.author == bot.user and message.embeds:
                title = message.embeds[0].title or ""
                if "Global Chat Control Panel" in title:
                    await message.edit(embed=embed, view=view)
                    return
        await ch.send(embed=embed, view=view)
    except Exception as e:
        logger.warning(f"Failed to refresh GC panel in guild {guild_id}: {e}")


# ── Cog ────────────────────────────────────────────────────────────────────

class GlobalChat(commands.Cog, name="GlobalChat"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.add_view(GCControlView())

    async def get_linked_channel(self, guild_id: int):
        val = await _get_stat(_gc_key(guild_id, "channel"))
        if not val or val == "0":
            return None
        return str(val)

    async def set_linked_channel(self, guild_id: int, channel_id: str):
        await _set_stat(_gc_key(guild_id, "channel"), channel_id)

    async def get_all_linked_channels(self):
        pool = await neon_db.get_pool()
        if not pool:
            return []
        rows = await pool.fetch(
            "SELECT key, value FROM bot_stats WHERE key LIKE 'global_chat_channel_%' AND value != '0' AND value != ''"
        )
        results = []
        for row in rows:
            guild_id = row["key"].rsplit("_", 1)[-1]
            channel_id = row["value"]
            results.append((guild_id, channel_id))
        return results

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        my_channel_id = await self.get_linked_channel(message.guild.id)
        if not my_channel_id:
            return
        if str(message.channel.id) != my_channel_id:
            return

        enabled = await _get_bool(message.guild.id, "gc_enabled")
        if not enabled:
            return

        muted = await _get_bool(message.guild.id, "gc_muted")
        if muted:
            return

        blocked_users = await _get_list(message.guild.id, "gc_blocked_users")
        if str(message.author.id) in blocked_users:
            return

        blocked_servers = await _get_list(message.guild.id, "gc_blocked_servers")
        if str(message.guild.id) in blocked_servers:
            return

        all_linked = await self.get_all_linked_channels()

        content = message.content[:1000] if message.content else "[attachment]"
        for guild_id, channel_id in all_linked:
            if str(message.guild.id) == guild_id and str(message.channel.id) == channel_id:
                continue
            target_guild = self.bot.get_guild(int(guild_id))
            if not target_guild:
                continue
            if str(message.guild.id) in blocked_servers:
                continue
            target_channel = target_guild.get_channel(int(channel_id))
            if not target_channel:
                continue
            target_muted = await _get_bool(int(guild_id), "gc_muted")
            if target_muted:
                continue
            target_enabled = await _get_bool(int(guild_id), "gc_enabled")
            if not target_enabled:
                continue
            target_blocked_users = await _get_list(int(guild_id), "gc_blocked_users")
            if str(message.author.id) in target_blocked_users:
                continue
            webhooks = await target_channel.webhooks()
            webhook = discord.utils.get(webhooks, name="GlobalChat")
            if not webhook:
                try:
                    webhook = await target_channel.create_webhook(name="GlobalChat")
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
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        await self.set_linked_channel(interaction.guild.id, str(interaction.channel_id))
        embed = (
            EmbedBuilder()
            .title(emoji_title("global_chat", "Global Chat Linked"))
            .description(f"This channel ({interaction.channel.mention}) is now linked to the global chat!")
            .color("blue")
            .field("Channel ID", str(interaction.channel_id))
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)

    @gc_group.command(name="unlink", description="Unlink this channel from the global chat")
    async def unlink(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title(emoji_title("error", "Permission Denied")).description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        await self.set_linked_channel(interaction.guild.id, "0")
        await interaction.response.send_message(
            embed=EmbedBuilder().title(emoji_title("success", "Global Chat Unlinked")).description("This channel has been unlinked from global chat.").color("green").timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )

    @gc_group.command(name="info", description="Check global chat status")
    async def info(self, interaction: discord.Interaction):
        hub_channel_id = await self.get_linked_channel(interaction.guild.id)
        if hub_channel_id:
            channel = self.bot.get_channel(int(hub_channel_id))
            embed = (
                EmbedBuilder()
                .title(emoji_title("global_chat", "Global Chat Status"))
                .description(f"Global chat is linked to {channel.mention if channel else f'<#{hub_channel_id}>'}")
                .color("blue")
                .field("Channel ID", str(hub_channel_id))
                .timestamp(datetime.datetime.utcnow())
                .build()
            )
        else:
            embed = (
                EmbedBuilder()
                .title(emoji_title("global_chat", "Global Chat Status"))
                .description("Global chat is not set up yet.")
                .color("red")
                .timestamp(datetime.datetime.utcnow())
                .build()
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GlobalChat(bot))
