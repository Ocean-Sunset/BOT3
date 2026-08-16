import discord
from discord.ext import commands
from discord import app_commands
import json
import datetime
from typing import Optional

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db
from Ediscord.builders import embed_from_dict, emoji_title


TICKET_DEFAULTS = {
    "enabled": False,
    "category_id": None,
    "support_role_id": None,
    "log_channel_id": None,
    "welcome_message": "Support will be with you shortly. Please describe your issue.",
    "ticket_limit": 3,
    "auto_close_hours": 0,
    "panel_channel_id": None,
    "panel_embed": {},
    "questions": [],
}


async def get_ticket_settings(guild_id: int):
    pool = await neon_db.get_pool()
    if not pool:
        return dict(TICKET_DEFAULTS)
    row = await pool.fetchrow("SELECT settings FROM ticket_settings WHERE guild_id = $1", str(guild_id))
    return neon_db.parse_settings(row["settings"], TICKET_DEFAULTS) if row else dict(TICKET_DEFAULTS)


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
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Error").description("This is not a ticket channel.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )

        confirm_view = discord.ui.View()
        async def confirm_cb(i: discord.Interaction):
            await i.response.defer()
            transcript = []
            async for msg in i.channel.history(limit=200, oldest_first=True):
                transcript.append(f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {msg.author.name}: {msg.content}")
            transcript_text = "\n".join(transcript[-100:])

            pool = await neon_db.get_pool()
            if pool:
                await pool.execute(
                    "INSERT INTO ticket_logs (guild_id, channel_id, user_id, transcript, closed_at) VALUES ($1, $2, $3, $4, $5)",
                    str(i.guild_id), str(i.channel.id), str(interaction.user.id), transcript_text[:5000], datetime.datetime.utcnow().isoformat(),
                )

            settings = await get_ticket_settings(i.guild_id)
            log_channel_id = settings.get("log_channel_id")
            if log_channel_id:
                log_channel = i.guild.get_channel(int(log_channel_id))
                if log_channel:
                    log_embed = (
                        EmbedBuilder()
                        .title(emoji_title("ticket", "Ticket Closed"))
                        .description(f"Ticket {i.channel.mention} has been closed.")
                        .color("red")
                        .field("Closed By", interaction.user.mention)
                        .field("Messages", str(len(transcript)))
                        .field("Transcript", f"```\n{transcript_text[:1000]}\n```")
                        .footer(f"Channel ID: {str(i.channel.id)}")
                        .timestamp(datetime.datetime.utcnow())
                        .build()
                    )
                    await log_channel.send(embed=log_embed)

            await i.channel.delete(reason="Ticket closed")

        async def cancel_cb(i: discord.Interaction):
            await i.response.edit_message(
                embed=EmbedBuilder().title("Cancelled").description("Ticket close cancelled.").color("grey").timestamp(datetime.datetime.utcnow()).build(),
                view=None
            )

        confirm_btn = discord.ui.Button(label="Confirm Close", style=discord.ButtonStyle.danger)
        confirm_btn.callback = confirm_cb
        cancel_btn = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)
        cancel_btn.callback = cancel_cb

        confirm_view.add_item(confirm_btn)
        confirm_view.add_item(cancel_btn)
        await interaction.response.send_message(
            embed=EmbedBuilder().title("Close Ticket?").description("Are you sure you want to close this ticket?").color("orange").timestamp(datetime.datetime.utcnow()).build(),
            view=confirm_view,
            ephemeral=True
        )


class CreateTicketView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="ticket:create")
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await get_ticket_settings(interaction.guild_id)
        if not settings.get("enabled"):
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Not Configured").description("Ticket system is not configured.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        questions = settings.get("questions") or []
        if questions:
            modal = TicketQuestionsModal(self.cog, questions)
            await interaction.response.send_modal(modal)
        else:
            await self.cog._create_ticket(interaction, [])


class TicketQuestionsModal(discord.ui.Modal):
    """Modal that asks the configured ticket questions before opening a ticket."""

    def __init__(self, cog, questions):
        super().__init__(title="Open a Ticket")
        self.cog = cog
        self._inputs = []
        for q in questions[:5]:  # Discord allows max 5 modal inputs
            item = discord.ui.TextInput(
                label=(q.get("label") or "Question")[:45],
                placeholder=(q.get("placeholder") or "")[:100] or None,
                required=bool(q.get("required", True)),
                max_length=1000,
            )
            self.add_item(item)
            self._inputs.append(item)

    async def on_submit(self, interaction: discord.Interaction):
        answers = [inp.value for inp in self._inputs]
        await self.cog._create_ticket(interaction, answers)


class Tickets(commands.Cog, name="Tickets"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _create_ticket(self, interaction: discord.Interaction, answers: list):
        settings = await get_ticket_settings(interaction.guild_id)
        existing_tickets = [c for c in interaction.guild.text_channels if c.name.startswith(f"ticket-{interaction.user.name.lower()[:20]}")]
        ticket_limit = settings.get("ticket_limit", 3)
        if len(existing_tickets) >= ticket_limit:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Limit Reached").description(f"You already have {len(existing_tickets)} open tickets (limit: {ticket_limit}).").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        category = interaction.guild.get_channel(int(settings.get("category_id") or 0))
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        support_role_id = settings.get("support_role_id")
        if support_role_id:
            role = interaction.guild.get_role(int(support_role_id))
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
            embed = (
                EmbedBuilder()
                .title(emoji_title("ticket", "Ticket Created"))
                .description(welcome)
                .color("blue")
                .field("User", interaction.user.mention)
                .field("Created", discord.utils.format_dt(datetime.datetime.utcnow(), style="R"))
                .footer(f"Ticket ID: {str(channel.id)}")
                .timestamp(datetime.datetime.utcnow())
                .build()
            )
            view = TicketView()
            content = interaction.user.mention
            # If custom questions were answered, post them in the ticket
            questions = settings.get("questions") or []
            if answers and questions:
                qa = "\n".join(f"**{q.get('label','Question')}:** {a}" for q, a in zip(questions[:5], answers) if a)
                if qa:
                    content = f"{interaction.user.mention}\n{qa}"
            await channel.send(content=content, embed=embed, view=view)
            await interaction.response.send_message(
                embed=EmbedBuilder().title("Ticket Created").description(f"Your ticket has been created: {channel.mention}").color("green").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Failed to create ticket: {e}")
            await interaction.response.send_message(
                embed=EmbedBuilder().title("Error").description(f"Could not create ticket: {str(e)[:100]}").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )

    async def _send_panel(self, guild, channel_id) -> bool:
        """Send the ticket panel (embed + create button) to a channel."""
        channel = guild.get_channel(int(channel_id))
        if not channel or not isinstance(channel, discord.TextChannel):
            return False
        settings = await get_ticket_settings(guild.id)
        embed = embed_from_dict(settings.get("panel_embed") or {})
        view = CreateTicketView(self)
        try:
            await channel.send(embed=embed, view=view)
            settings["panel_channel_id"] = str(channel_id)
            await save_ticket_settings(guild.id, settings)
            return True
        except Exception as e:
            logger.error(f"Failed to send ticket panel: {e}")
            return False

    ticket_group = app_commands.Group(name="ticket", description="Ticket system commands")

    @ticket_group.command(name="setup", description="Set up the ticket system")
    @app_commands.describe(category="Category for ticket channels", role="Support role", log_channel="Channel for transcripts")
    async def setup(self, interaction: discord.Interaction, category: discord.CategoryChannel, role: Optional[discord.Role] = None, log_channel: Optional[discord.TextChannel] = None):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Administrator permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = {
            "enabled": True,
            "category_id": str(category.id),
            "support_role_id": str(role.id) if role else None,
            "log_channel_id": str(log_channel.id) if log_channel else None,
        }
        await save_ticket_settings(interaction.guild_id, settings)
        embed = (
            EmbedBuilder()
            .title(emoji_title("ticket", "Support Tickets"))
            .description("Click the button below to create a support ticket.")
            .color("blue")
            .field("Category", category.mention)
            .field("Support Role", role.mention if role else "None")
            .field("Log Channel", log_channel.mention if log_channel else "None")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        view = CreateTicketView(self)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            embed=EmbedBuilder().title("Setup Complete").description(f"Ticket system set up in {category.mention}.").color("green").timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )

    @ticket_group.command(name="panel", description="Send the ticket creation panel to the current channel")
    async def panel(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Administrator permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        embed = (
            EmbedBuilder()
            .title(emoji_title("ticket", "Support Tickets"))
            .description("Click below to create a ticket.")
            .color("blue")
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        view = CreateTicketView(self)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            embed=EmbedBuilder().title("Panel Sent").description("Ticket panel sent to this channel.").color("green").timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )

    @ticket_group.command(name="add", description="Add a user to the current ticket")
    @app_commands.describe(user="The user to add")
    async def add_user(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.channel or not interaction.channel.name.startswith("ticket-"):
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Error").description("This is not a ticket channel.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
        embed = (
            EmbedBuilder()
            .title("User Added")
            .description(f"{user.mention} has been added to this ticket.")
            .color("green")
            .field("Added By", interaction.user.mention)
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)

    @ticket_group.command(name="remove", description="Remove a user from the current ticket")
    @app_commands.describe(user="The user to remove")
    async def remove_user(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.channel or not interaction.channel.name.startswith("ticket-"):
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Error").description("This is not a ticket channel.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        await interaction.channel.set_permissions(user, overwrite=None)
        embed = (
            EmbedBuilder()
            .title("User Removed")
            .description(f"{user.mention} has been removed from this ticket.")
            .color("orange")
            .field("Removed By", interaction.user.mention)
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)

    @ticket_group.command(name="rename", description="Rename the current ticket")
    @app_commands.describe(name="The new ticket name")
    async def rename(self, interaction: discord.Interaction, name: str):
        if not interaction.channel or not interaction.channel.name.startswith("ticket-"):
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Error").description("This is not a ticket channel.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Channels permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        new_name = f"ticket-{name[:30].lower().replace(' ', '-')}"
        await interaction.channel.edit(name=new_name, reason=f"Ticket renamed by {interaction.user}")
        embed = (
            EmbedBuilder()
            .title("Ticket Renamed")
            .description(f"Ticket renamed to **{new_name}**")
            .color("blue")
            .field("Renamed By", interaction.user.mention)
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed)

    @ticket_group.command(name="stats", description="View ticket statistics")
    async def stats(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        ticket_channels = [c for c in interaction.guild.text_channels if c.name.startswith("ticket-")]
        pool = await neon_db.get_pool()
        closed_count = 0
        if pool:
            row = await pool.fetchrow(
                "SELECT COUNT(*) as count FROM ticket_logs WHERE guild_id = $1",
                str(interaction.guild_id)
            )
            closed_count = row["count"] if row else 0
        embed = (
            EmbedBuilder()
            .title("Ticket Statistics")
            .color("blue")
            .field("Open Tickets", str(len(ticket_channels)))
            .field("Closed Tickets", str(closed_count))
            .field("Total", str(len(ticket_channels) + closed_count))
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
