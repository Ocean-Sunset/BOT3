import discord
from discord.ext import commands
from discord import app_commands
import json
import datetime
from typing import Optional

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db


TICKET_DEFAULTS = {"enabled": False, "category_id": None, "support_role_id": None, "log_channel_id": None, "welcome_message": "Support will be with you shortly. Please describe your issue."}


async def get_ticket_settings(guild_id: int):
    pool = await neon_db.get_pool()
    if not pool:
        return dict(TICKET_DEFAULTS)
    row = await pool.fetchrow("SELECT settings FROM ticket_settings WHERE guild_id = $1", str(guild_id))
    return {**TICKET_DEFAULTS, **row["settings"]} if row else dict(TICKET_DEFAULTS)


async def save_ticket_settings(guild_id: int, settings: dict):
    pool = await neon_db.get_pool()
    if not pool:
        return
    await pool.execute(
        "INSERT INTO ticket_settings (guild_id, settings) VALUES ($1, $2::jsonb) ON CONFLICT (guild_id) DO UPDATE SET settings = $2::jsonb",
        str(guild_id), json.dumps(settings),
    )


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.channel or not interaction.channel.name.startswith("ticket-"):
            return await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)

        confirm_view = discord.ui.View()
        async def confirm_cb(i: discord.Interaction):
            await i.response.defer()
            transcript = []
            async for msg in i.channel.history(limit=200, oldest_first=True):
                transcript.append(f"[{msg.created_at}] {msg.author.name}: {msg.content}")
            transcript_text = "\n".join(transcript[-100:])

            pool = await neon_db.get_pool()
            if pool:
                await pool.execute(
                    "INSERT INTO ticket_logs (guild_id, channel_id, user_id, transcript, closed_at) VALUES ($1, $2, $3, $4, $5)",
                    str(i.guild_id), str(i.channel.id), str(interaction.user.id), transcript_text[:5000], datetime.datetime.utcnow().isoformat(),
                )

            await i.channel.delete(reason="Ticket closed")
        async def cancel_cb(i: discord.Interaction):
            await i.response.edit_message(content="Close cancelled.", view=None)

        confirm_btn = discord.ui.Button(label="Confirm Close", style=discord.ButtonStyle.danger)
        confirm_btn.callback = confirm_cb
        cancel_btn = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)
        cancel_btn.callback = cancel_cb

        confirm_view.add_item(confirm_btn)
        confirm_view.add_item(cancel_btn)
        await interaction.response.send_message("Are you sure you want to close this ticket?", view=confirm_view, ephemeral=True)


class CreateTicketView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="ticket:create")
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await get_ticket_settings(interaction.guild_id)
        if not settings.get("enabled"):
            return await interaction.response.send_message("Ticket system is not configured.", ephemeral=True)

        existing = discord.utils.get(interaction.guild.text_channels, name=f"ticket-{interaction.user.name.lower().replace(' ', '-')}")
        if existing:
            return await interaction.response.send_message(f"You already have an open ticket: {existing.mention}", ephemeral=True)

        category = interaction.guild.get_channel(settings.get("category_id") or 0)
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        support_role_id = settings.get("support_role_id")
        if support_role_id:
            role = interaction.guild.get_role(support_role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        try:
            channel = await interaction.guild.create_text_channel(
                f"ticket-{interaction.user.name[:20].lower().replace(' ', '-')}",
                category=category,
                overwrites=overwrites,
                reason=f"Ticket created by {interaction.user}",
            )
            welcome = settings.get("welcome_message", "Support will be with you shortly.")
            embed = EmbedBuilder().title("Ticket Created").description(welcome).color("blue").field("User", interaction.user.mention).build()
            view = TicketView()
            await channel.send(content=interaction.user.mention, embed=embed, view=view)
            await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Could not create ticket: {str(e)[:100]}", ephemeral=True)


class Tickets(commands.Cog, name="Tickets"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    ticket_group = app_commands.Group(name="ticket", description="Ticket system commands")

    @ticket_group.command(name="setup", description="Set up the ticket system")
    @app_commands.describe(category="Category for ticket channels", role="Support role", log_channel="Channel for transcripts")
    async def setup(self, interaction: discord.Interaction, category: discord.CategoryChannel, role: Optional[discord.Role] = None, log_channel: Optional[discord.TextChannel] = None):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You need Administrator permission.", ephemeral=True)
        settings = {"enabled": True, "category_id": category.id, "support_role_id": role.id if role else None, "log_channel_id": log_channel.id if log_channel else None}
        await save_ticket_settings(interaction.guild_id, settings)
        embed = EmbedBuilder().title("Support Tickets").description("Click the button below to create a support ticket.").color("blue").build()
        view = CreateTicketView(self)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"Ticket system set up in {category.mention}.", ephemeral=True)

    @ticket_group.command(name="panel", description="Send the ticket creation panel to the current channel")
    async def panel(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You need Administrator permission.", ephemeral=True)
        embed = EmbedBuilder().title("Support Tickets").description("Click below to create a ticket.").color("blue").build()
        view = CreateTicketView(self)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("Panel sent.", ephemeral=True)

    @ticket_group.command(name="add", description="Add a user to the current ticket")
    @app_commands.describe(user="The user to add")
    async def add_user(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.channel or not interaction.channel.name.startswith("ticket-"):
            return await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
        await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"{user.mention} has been added to this ticket.", ephemeral=False)

    @ticket_group.command(name="remove", description="Remove a user from the current ticket")
    @app_commands.describe(user="The user to remove")
    async def remove_user(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.channel or not interaction.channel.name.startswith("ticket-"):
            return await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
        await interaction.channel.set_permissions(user, overwrite=None)
        await interaction.response.send_message(f"{user.mention} has been removed from this ticket.", ephemeral=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
