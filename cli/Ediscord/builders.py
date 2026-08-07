"""
# Ediscord builders
Fluent builder utilities for Discord components.

Contains:
- EmbedBuilder   – chainable embed construction
- ButtonBuilder  – action buttons with callbacks
- LinkBuilder    – URL buttons and styled hyperlinks
- ModalBuilder   – text-input modals

Usage example:
    from Ediscord.builders import EmbedBuilder, ButtonBuilder, ModalBuilder

    embed = (
        EmbedBuilder()
        .title("Hello!")
        .description("Welcome to the server.")
        .color("blue")
        .field("Info", "Some value", inline=True)
        .footer("Powered by Prowl")
        .build()
    )
"""

import discord
from discord.ext import commands
from typing import Optional, Callable, Any, List, Union
from Ediscord import variables


# ==================================================================================================
#                                        UNIFIED BRAND / SEMANTIC COLORS
# ==================================================================================================

# Prowl brand palette — every embed should use one of these.
BRAND   = 0x8B5CF6   # violet — default / neutral
SUCCESS = 0x22C55E   # green  — actions that succeeded
ERROR   = 0xEF4444   # red    — failures / denied
WARN    = 0xF59E0B   # amber  — cautions / warnings
INFO    = 0x3B82F6   # blue   — informational

_SEMANTIC = {
    "brand": BRAND, "violet": BRAND, "purple": BRAND,
    "success": SUCCESS, "green": SUCCESS, "ok": SUCCESS,
    "error": ERROR, "danger": ERROR, "red": ERROR,
    "warn": WARN, "warning": WARN, "yellow": WARN, "amber": WARN, "orange": WARN,
    "info": INFO, "blue": INFO, "blurple": 0x5865F2,
}


# ==================================================================================================
#                                            EMBED BUILDER
# ==================================================================================================


class EmbedBuilder:
    """Fluent builder for :class:`discord.Embed`.

    All setter methods return ``self`` so calls can be chained.
    Call :meth:`build` to get the final ``discord.Embed``.

    Semantic shortcuts keep embeds consistent:
        EmbedBuilder().success("Member Muted")              # green, title only
        EmbedBuilder().error("Missing permissions")         # red, title only
        EmbedBuilder().info("Leaderboard").field("1.", "User")  # blue + fields
        EmbedBuilder().warn("Rate limited", "Try again later.")  # amber + description
    """

    def __init__(self):
        self._title: Optional[str] = None
        self._description: Optional[str] = None
        self._color: Optional[Union[int, discord.Color]] = None
        self._url: Optional[str] = None
        self._timestamp = None
        self._author: Optional[dict] = None
        self._footer: Optional[dict] = None
        self._image: Optional[str] = None
        self._thumbnail: Optional[str] = None
        self._fields: list = []

    # --- semantic shortcuts ---------------------------------------------------

    def success(self, title: str, description: str = None) -> "EmbedBuilder":
        return self.title(title).color("success").description(description or "")

    def error(self, title: str, description: str = None) -> "EmbedBuilder":
        return self.title(title).color("error").description(description or "")

    def warn(self, title: str, description: str = None) -> "EmbedBuilder":
        return self.title(title).color("warn").description(description or "")

    def info(self, title: str, description: str = None) -> "EmbedBuilder":
        return self.title(title).color("info").description(description or "")

    def brand(self, title: str, description: str = None) -> "EmbedBuilder":
        return self.title(title).color("brand").description(description or "")

    # --- core setters ----------------------------------------------------------

    def title(self, text: str) -> "EmbedBuilder":
        self._title = text[:256]
        return self

    def description(self, text: str) -> "EmbedBuilder":
        self._description = text[:4096] if text else None
        return self

    def color(self, value: Union[str, int, discord.Color]) -> "EmbedBuilder":
        if isinstance(value, str):
            resolved = _SEMANTIC.get(value.lower())
            if resolved is None:
                resolved = variables.COLOR_MAP.get(value.lower(), BRAND)
            self._color = discord.Color(resolved)
        elif isinstance(value, int):
            self._color = discord.Color(value)
        elif isinstance(value, discord.Color):
            self._color = value
        return self

    def hex_color(self, hex_str: str) -> "EmbedBuilder":
        hex_str = hex_str.lstrip("#")
        try:
            self._color = discord.Color(int(hex_str, 16))
        except ValueError:
            self._color = discord.Color.default()
        return self

    def url(self, url: str) -> "EmbedBuilder":
        self._url = url
        return self

    def timestamp(self, ts=None) -> "EmbedBuilder":
        """Set a timestamp. Defaults to *now* if no argument is given."""
        self._timestamp = ts
        return self

    # --- author / footer -------------------------------------------------------

    def author(self, name: str, url: str = None, icon_url: str = None) -> "EmbedBuilder":
        self._author = {"name": name, "url": url, "icon_url": icon_url}
        return self

    def footer(self, text: str, icon_url: str = None) -> "EmbedBuilder":
        self._footer = {"text": text, "icon_url": icon_url}
        return self

    # --- images ----------------------------------------------------------------

    def image(self, url: str) -> "EmbedBuilder":
        self._image = url
        return self

    def thumbnail(self, url: str) -> "EmbedBuilder":
        self._thumbnail = url
        return self

    # --- fields ----------------------------------------------------------------

    def field(self, name: str, value: str, inline: bool = False) -> "EmbedBuilder":
        self._fields.append({
            "name": name[:256],
            "value": value[:1024],
            "inline": inline,
        })
        return self

    def fields_from_dict(self, data: dict, inline: bool = False) -> "EmbedBuilder":
        for k, v in data.items():
            self.field(str(k), str(v), inline=inline)
        return self

    def clear_fields(self) -> "EmbedBuilder":
        self._fields.clear()
        return self

    # --- build / send ----------------------------------------------------------

    def build(self) -> discord.Embed:
        embed = discord.Embed(
            title=self._title,
            description=self._description,
            color=self._color or discord.Color(BRAND),
            url=self._url,
            timestamp=self._timestamp,
        )
        if self._author:
            embed.set_author(**{k: v for k, v in self._author.items() if v is not None})
        if self._footer:
            embed.set_footer(**{k: v for k, v in self._footer.items() if v is not None})
        if self._image:
            embed.set_image(url=self._image)
        if self._thumbnail:
            embed.set_thumbnail(url=self._thumbnail)
        for f in self._fields:
            embed.add_field(**f)
        # Discord rejects embeds with no content at all
        if not (embed.title or embed.description or embed.fields or embed.author or embed.footer or embed.image or embed.thumbnail):
            embed.description = "\u200b"
        return embed

    async def send(self, channel, content: str = None, **kwargs) -> discord.Message:
        """Build and send the embed to *channel*."""
        return await channel.send(content=content, embed=self.build(), **kwargs)

    async def respond(self, interaction: discord.Interaction, content: str = None, **kwargs):
        """Build and respond to an interaction."""
        return await interaction.response.send_message(
            content=content, embed=self.build(), **kwargs
        )


# ==================================================================================================
#                                           BUTTON BUILDER
# ==================================================================================================


class ButtonView(discord.ui.View):
    """A ``View`` that holds one or more buttons created by :class:`ButtonBuilder`."""

    def __init__(self, buttons: list, *, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        for btn in buttons:
            self.add_item(btn)


class ButtonBuilder:
    """Fluent builder for :class:`discord.ui.Button`.

    Call :meth:`build` for a single ``Button``, or :meth:`view` / :meth:`send`
    to wrap everything in a ``View`` and ship it.
    """

    STYLES = {
        "primary":   discord.ButtonStyle.primary,
        "secondary": discord.ButtonStyle.secondary,
        "success":   discord.ButtonStyle.success,
        "danger":    discord.ButtonStyle.danger,
        "link":      discord.ButtonStyle.link,
    }

    def __init__(self):
        self._label: Optional[str] = None
        self._style: discord.ButtonStyle = discord.ButtonStyle.primary
        self._emoji: Optional[str] = None
        self._custom_id: Optional[str] = None
        self._url: Optional[str] = None
        self._disabled: bool = False
        self._row: Optional[int] = None
        self._callback: Optional[Callable] = None

    # --- setters ---------------------------------------------------------------

    def label(self, text: str) -> "ButtonBuilder":
        self._label = text[:80]
        return self

    def style(self, value: str) -> "ButtonBuilder":
        self._style = self.STYLES.get(value.lower(), discord.ButtonStyle.primary)
        return self

    def emoji(self, value: str) -> "ButtonBuilder":
        self._emoji = value
        return self

    def custom_id(self, cid: str) -> "ButtonBuilder":
        self._custom_id = cid
        return self

    def url(self, url: str) -> "ButtonBuilder":
        self._url = url
        self._style = discord.ButtonStyle.link
        return self

    def disabled(self, value: bool = True) -> "ButtonBuilder":
        self._disabled = value
        return self

    def row(self, r: int) -> "ButtonBuilder":
        self._row = r
        return self

    def on_click(self, callback: Callable) -> "ButtonBuilder":
        """Register an ``async def callback(interaction)`` for this button."""
        self._callback = callback
        return self

    # --- build / send ----------------------------------------------------------

    def build(self) -> discord.ui.Button:
        kwargs = {
            "label": self._label,
            "style": self._style,
            "disabled": self._disabled,
        }
        if self._emoji:
            kwargs["emoji"] = self._emoji
        if self._url:
            kwargs["url"] = self._url
        elif self._custom_id:
            kwargs["custom_id"] = self._custom_id
        if self._row is not None:
            kwargs["row"] = self._row
        return discord.ui.Button(**kwargs)

    def view(self, *, timeout: float = 180.0) -> ButtonView:
        """Wrap the button in a :class:`ButtonView`."""
        v = ButtonView([self.build()], timeout=timeout)
        if self._callback:
            btn = v.children[0]
            btn.callback = self._callback
        return v

    async def send(self, channel, content: str = None, **kwargs) -> discord.Message:
        """Build a view and send it."""
        return await channel.send(content=content, view=self.view(), **kwargs)


def button_row(*builders: "ButtonBuilder", timeout: float = 180.0) -> ButtonView:
    """Create a ``ButtonView`` from multiple :class:`ButtonBuilder` instances."""
    view = ButtonView([b.build() for b in builders], timeout=timeout)
    for b, item in zip(builders, view.children):
        if b._callback:
            item.callback = b._callback
    return view


# ==================================================================================================
#                                            LINK BUILDER
# ==================================================================================================


class LinkBuilder:
    """Fluent builder for URL-based buttons and styled hyperlink embeds.

    Use :meth:`button` for a ``discord.ui.Button`` (link style),
    or :meth:`embed` to create an embed that highlights the link.
    """

    def __init__(self):
        self._url: str = ""
        self._label: Optional[str] = None
        self._emoji: Optional[str] = None
        self._description: Optional[str] = None
        self._color: Union[str, int, discord.Color] = "blurple"

    # --- setters ---------------------------------------------------------------

    def url(self, url: str) -> "LinkBuilder":
        self._url = url
        return self

    def label(self, text: str) -> "LinkBuilder":
        self._label = text[:80]
        return self

    def emoji(self, value: str) -> "LinkBuilder":
        self._emoji = value
        return self

    def description(self, text: str) -> "LinkBuilder":
        self._description = text
        return self

    def color(self, value: Union[str, int, discord.Color]) -> "LinkBuilder":
        self._color = value
        return self

    # --- build -----------------------------------------------------------------

    def button(self) -> discord.ui.Button:
        """Return a link-style ``Button``."""
        kwargs = {
            "style": discord.ButtonStyle.link,
            "url": self._url,
            "label": self._label,
        }
        if self._emoji:
            kwargs["emoji"] = self._emoji
        return discord.ui.Button(**{k: v for k, v in kwargs.items() if v is not None})

    def embed(self) -> discord.Embed:
        """Return an ``Embed`` that displays the link with a description."""
        eb = EmbedBuilder()
        if self._label:
            eb.title(self._label)
        if self._description:
            eb.description(self._description)
        eb.color(self._color)
        eb.field("Link", f"[Click here]({self._url})", inline=False)
        return eb.build()

    def view(self, *, timeout: float = 180.0) -> ButtonView:
        """Wrap the link button in a ``ButtonView``."""
        return ButtonView([self.button()], timeout=timeout)

    async def send(self, channel, content: str = None, **kwargs) -> discord.Message:
        """Send the link button in a view."""
        return await channel.send(content=content, view=self.view(), **kwargs)


# ==================================================================================================
#                                           MODAL BUILDER
# ==================================================================================================


class _ModalInput:
    """Internal descriptor for a single text input row."""

    def __init__(
        self,
        custom_id: str,
        label: str,
        *,
        style: str = "short",
        placeholder: str = None,
        default: str = None,
        required: bool = True,
        min_length: int = None,
        max_length: int = None,
    ):
        self.custom_id = custom_id
        self.label = label
        self.style = style
        self.placeholder = placeholder
        self.default = default
        self.required = required
        self.min_length = min_length
        self.max_length = max_length

    def to_input(self) -> discord.ui.TextInput:
        style_map = {
            "short": discord.TextStyle.short,
            "paragraph": discord.TextStyle.paragraph,
        }
        kwargs = {
            "custom_id": self.custom_id,
            "label": self.label,
            "style": style_map.get(self.style, discord.TextStyle.short),
            "required": self.required,
        }
        if self.placeholder:
            kwargs["placeholder"] = self.placeholder
        if self.default:
            kwargs["default"] = self.default
        if self.min_length is not None:
            kwargs["min_length"] = self.min_length
        if self.max_length is not None:
            kwargs["max_length"] = self.max_length
        return discord.ui.TextInput(**kwargs)


class ModalView(discord.ui.Modal):
    """A ``Modal`` generated by :class:`ModalBuilder`."""

    def __init__(self, title: str, inputs: list, *, on_submit: Callable = None):
        super().__init__(title=title)
        self._on_submit = on_submit
        for inp in inputs:
            self.add_item(inp.to_input())

    async def on_submit(self, interaction: discord.Interaction):
        if self._on_submit:
            await self._on_submit(interaction, self)
        else:
            await interaction.response.send_message("Submitted!", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message(
            f"Something went wrong: {error}", ephemeral=True
        )


class ModalBuilder:
    """Fluent builder for :class:`discord.ui.Modal`.

    Call :meth:`add_input` to define text-input rows, then :meth:`build` or
    :meth:`send` / :meth:`respond`.
    """

    def __init__(self):
        self._title: str = "Modal"
        self._inputs: List[_ModalInput] = []
        self._on_submit: Optional[Callable] = None

    # --- setters ---------------------------------------------------------------

    def title(self, text: str) -> "ModalBuilder":
        self._title = text[:45]
        return self

    def add_input(
        self,
        custom_id: str,
        label: str,
        *,
        style: str = "short",
        placeholder: str = None,
        default: str = None,
        required: bool = True,
        min_length: int = None,
        max_length: int = None,
    ) -> "ModalBuilder":
        """Append a text-input row (max 5)."""
        if len(self._inputs) >= 5:
            raise ValueError("A modal can have at most 5 text inputs.")
        self._inputs.append(_ModalInput(
            custom_id, label,
            style=style, placeholder=placeholder, default=default,
            required=required, min_length=min_length, max_length=max_length,
        ))
        return self

    def on_submit(self, callback: Callable) -> "ModalBuilder":
        """Set an ``async def callback(interaction, modal)`` handler."""
        self._on_submit = callback
        return self

    # --- build / send ----------------------------------------------------------

    def build(self) -> ModalView:
        return ModalView(self._title, self._inputs, on_submit=self._on_submit)

    async def send(self, interaction: discord.Interaction):
        """Respond to an interaction by showing this modal."""
        await interaction.response.send_modal(self.build())

    async def respond(self, interaction: discord.Interaction):
        """Alias for :meth:`send`."""
        await self.send(interaction)


# ==================================================================================================
#                                          CONVENIENCE ALIASES
# ==================================================================================================


def quick_embed(title: str, description: str = None, color: str = "brand") -> discord.Embed:
    """One-liner embed shortcut (title-first, optional description)."""
    eb = EmbedBuilder()
    getattr(eb, color if color in ("success", "error", "warn", "info", "brand") else "brand")(title, description)
    return eb.build()


def success_embed(title: str, description: str = None) -> discord.Embed:
    """Green success embed — title only unless a description is given."""
    return EmbedBuilder().success(title, description).build()


def error_embed(title: str, description: str = None) -> discord.Embed:
    """Red error embed."""
    return EmbedBuilder().error(title, description).build()


def info_embed(title: str, description: str = None) -> discord.Embed:
    """Blue info embed."""
    return EmbedBuilder().info(title, description).build()
