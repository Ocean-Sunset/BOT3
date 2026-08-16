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

# Prowl brand palette - every embed should use one of these.
BRAND   = 0x8B5CF6   # violet - default / neutral
SUCCESS = 0x22C55E   # green  - actions that succeeded
ERROR   = 0xEF4444   # red    - failures / denied
WARN    = 0xF59E0B   # amber  - cautions / warnings
INFO    = 0x3B82F6   # blue   - informational

# ==================================================================================================
#                                        EMBED TYPE EMOJIS
# ==================================================================================================

# Every embed "type" maps to an emoji used to prefix its title (emoji + two spaces).
# Values are unicode fallbacks for now - replace any with a custom server emoji string
# like "<:prowl_ban:1234567890>" once the emojis are built.
# Placeholder IDs below are replaced with real ones after uploading to Discord.
_E = "0000000000000000000"  # placeholder - swap for real emoji IDs
EMBED_EMOJIS = {
    # ── Moderation ──
    "ban":        f"<:ban:1538638670423392316>",
    "tempban":    f"<:tempban:1538638690224578621>",
    "kick":       f"<:kick:1538638679810252882>",
    "mute":       f"<:mute:1538638685317374032>",
    "unmute":     f"<:unmute:1538638696994050129>",
    "warn":       f"<:warn:1538638702950223892>",
    "unban":      f"<:unban:1538638695505076234>",
    "purge":      f"<:purge:1538638686428602408>",
    "modlog":     f"<:modlog:1538638684298158260>",
    "dm":         f"<:dm:1538638671740149871>",
    "timeout":    f"<:timeout:1538660560152043682>",
    "softban":    f"<:softban:1538660541357232179>",
    "case":       f"<:case:1538660436101169313>",
    "evidence":   f"<:evidence:1538660463318007830>",
    # ── Leveling ──
    "level_up":   f"<:level_up:1538638682427367454>",
    "rank":       f"<:rank:1538638687611654225>",
    "leaderboard":f"<:leaderboard:1538638681102090340>",
    "xp":         f"<:xp:1538660575897329694>",
    "streak":     f"<:streak:1538660546398916649>",
    "milestone":  f"<:milestone:1538660508448591978>",
    "reward":     f"<:reward:1538660528229056562>",
    # ── Welcomer ──
    "welcome":    f"<:welcome:1538638704069972059>",
    "goodbye":    f"<:goodbye:1538638674156064931>",
    "auto_role":  f"<:auto_role:1538638669198528623>",
    "boost":      f"<:boost:1538660428790370396>",
    # ── Tickets ──
    "ticket":       f"<:ticket:1538638691399106661>",
    "ticket_open":  f"<:ticket_open:1538638694439985254>",
    "ticket_close": f"<:ticket_close:1538638692795682856>",
    "ticket_claim": f"<:ticket_claim:1538660555588636837>",
    "ticket_reopen":f"<:ticket_reopen:1538660558566334596>",
    # ── Verification ──
    "verify":         f"<:verify:1538638698860511414>",
    "verify_fail":    f"<:verify_fail:1538638700978896906>",
    "verify_pending": f"<:verify_pending:1538660568267886642>",
    # ── Invite Tracker ──
    "invite_join":    f"<:invite_join:1538638675389456564>",
    "invite_stats":   f"<:invite_stats:1538638678190985246>",
    "invite_create":  f"<:invite_create:1538660485652684910>",
    "invite_revoke":  f"<:invite_revoke:1538660487422546001>",
    # ── Global Chat ──
    "global_chat":    f"<:global_chat:1538638672876937256>",
    "global_msg":     f"<:global_msg:1538660477838565406>",
    "global_linked":  f"<:global_linked:1538660476593119372>",
    # ── Anti-Raid / Security ──
    "anti_raid":     f"<:anti_raid:1538638667692646430>",
    "raid_detected": f"<:raid_detected:1538660525020414072>",
    "raid_blocked":  f"<:raid_blocked:1538660523669987489>",
    # ── Status / Feedback ──
    "success":  f"<:success:1538660547791429694>",
    "error":    f"<:error:1538660462068113438>",
    "info":     f"<:info:1538660484352311357>",
    "warning":  f"<:warning:1538660572386697236>",
    "pending":  f"<:pending:1538660516908765184>",
    # ── UI / General ──
    "settings":  f"<:settings:1538638688806903938>",
    "dashboard": f"<:dashboard:1538660455365484544>",
    "analytics": f"<:analytics:1538660411786924065>",
    "database":  f"<:database:1538660457286602802>",
    "server":    f"<:server:1538660536344911893>",
    "member":    f"<:member:1538660501309890570>",
    "members":   f"<:members:1538660504426512525>",
    "channel":   f"<:channel:1538660437187371018>",
    "role":      f"<:role:1538660530628202637>",
    "bot":       f"<:bot:1538660430090739782>",
    "link":      f"<:link:1538660494481690624>",
    "copy":      f"<:copy:1538660449824931901>",
    "save":      f"<:save:1538660531781505144>",
    "search":    f"<:search:1538660534071853196>",
    "refresh":   f"<:refresh:1538660527096598609>",
    "download":  f"<:download:1538660460738642011>",
    "upload":    f"<:upload:1538660565042331758>",
    "lock":      f"<:lock:1538660495878258688>",
    "unlock":    f"<:unlock:1538660562223898714>",
    "key":       f"<:key:1538660489310249080>",
    "star":      f"<:star:1538660544356294747>",
    "pin":       f"<:pin:1538660519479742545>",
    "clock":     f"<:clock:1538660440245272596>",
    "calendar":  f"<:calendar:1538660433786052618>",
    "bell":      f"<:bell:1538660422251450468>",
    "bell_off":  f"<:bell_off:1538660423992344606>",
    "eye":       f"<:eye:1538660464723107870>",
    "eye_off":   f"<:eye_off:1538660465809432696>",
    "check":     f"<:check:1538660438626017370>",
    "cross":     f"<:cross:1538660452530393199>",
    "heart":     f"<:heart:1538660480711921856>",
    "bolt":      f"<:bolt:1538660426353614991>",
    "fire":      f"<:fire:1538660467931881623>",
    "code":      f"<:code:1538660442870653123>",
    "terminal":  f"<:terminal:1538660552988037311>",
    "bug":       f"<:bug:1538660431609208832>",
    "rocket":    f"<:rocket:1538660529508323328>",
    "sparkle":   f"<:sparkle:1538660542896672890>",
    "cloud":     f"<:cloud:1538660441759289344>",
    "sun":       f"<:sun:1538660549297053786>",
    "moon":      f"<:moon:1538660510478639155>",
    "leaf":      f"<:leaf:1538660492262772867>",
    "mountain":  f"<:mountain:1538660511493783562>",
    "flag":      f"<:flag:1538660469236175001>",
    "compass":   f"<:compass:1538660447459221535>",
    "map":       f"<:map:1538660498265084036>",
    "globe":     f"<:globe:1538660478879014983>",
    "anchor":    f"<:anchor:1538660413208793138>",
    "tag":       f"<:tag:1538660550932693032>",
    "bookmark":  f"<:bookmark:1538660427771154674>",
    "folder":    f"<:folder:1538660471958278246>",
    "file":      f"<:file:1538660466883035237>",
    "archive":   f"<:archive:1538660416555589672>",
    "package":   f"<:package:1538660515553878076>",
    "cpu":       f"<:cpu:1538660451259514991>",
    "wifi":      f"<:wifi:1538660574731313162>",
    "bluetooth": f"<:bluetooth:1538660425195987145>",
    "power":     f"<:power:1538660521652523199>",
    "music":     f"<:music:1538660512789958656>",
    "image":     f"<:image:1538660482221605027>",
    "video":     f"<:video:1538660569417252945>",
    "camera":    f"<:camera:1538660435073695975>",
    "mic":       f"<:mic:1538660507018596523>",
    "phone":     f"<:phone:1538660518162731078>",
    "mail":      f"<:mail:1538660496947806209>",
    "message":   f"<:message:1538660505827151943>",
    "send":      f"<:send:1538660535317561404>",
    "inbox":     f"<:inbox:1538660483291283516>",
    "shield":    f"<:shield:1538660540266709193>",
    "scan":      f"<:scan:1538660532977016842>",
    "atom":      f"<:atom:1538660417679794276>",
    "dna":       f"<:dna:1538660459425701938>",
    "flask":     f"<:flask:1538660470393671840>",
    "award":     f"<:award:1538660419483344957>",
    "crown":     f"<:crown:1538660454052921364>",
    "gem":       f"<:gem:1538660473174753360>",
    "coffee":    f"<:coffee:1538660444217278584>",
    "cake":      f"<:cake:1538660432787537921>",
    "pizza":     f"<:pizza:1538660520482045972>",
    "cookie":    f"<:cookie:1538660448725901363>",
    "gift":      f"<:gift:1538660474407878698>",
}


def emoji_for(key: str) -> str:
    """Return the emoji registered for an embed type ("" if none)."""
    return EMBED_EMOJIS.get(key, "")


def emoji_title(key: str, text: str) -> str:
    """Prefix *text* with the type's emoji, separated by two spaces."""
    emoji = emoji_for(key)
    if not emoji:
        return text
    return f"{emoji}  {text}"

_SEMANTIC = {
    "brand": BRAND, "violet": BRAND, "purple": BRAND,
    "success": SUCCESS, "green": SUCCESS, "ok": SUCCESS,
    "error": ERROR, "danger": ERROR, "red": ERROR,
    "warn": WARN, "warning": WARN, "yellow": WARN, "amber": WARN, "orange": WARN,
    "info": INFO, "blue": INFO, "blurple": 0x5865F2,
    "fire": 0xF97316,
    "pink": 0xF472B6,
    "gray": 0x6B7280, "grey": 0x6B7280,
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
    """Green success embed - title only unless a description is given."""
    return EmbedBuilder().success(title, description).build()


def error_embed(title: str, description: str = None) -> discord.Embed:
    """Red error embed."""
    return EmbedBuilder().error(title, description).build()


def info_embed(title: str, description: str = None) -> discord.Embed:
    """Blue info embed."""
    return EmbedBuilder().info(title, description).build()


def embed_from_dict(data: dict) -> discord.Embed:
    """Build a :class:`discord.Embed` from a dashboard-configured dict.

    Shared across every cog that renders dashboard embeds (moderation actions,
    leveling, welcome/goodbye, tickets, ...).
    """
    if not isinstance(data, dict):
        data = {}
    color = data.get("color")
    try:
        color = int(str(color).lstrip("#"), 16) if color else BRAND
    except (ValueError, TypeError):
        color = BRAND
    embed = discord.Embed(
        title=data.get("title") or None,
        description=data.get("description") or None,
        color=color,
    )
    if data.get("url"):
        embed.url = data["url"]
    if data.get("author_name"):
        embed.set_author(name=data["author_name"], url=data.get("author_url") or None, icon_url=data.get("author_icon") or None)
    if data.get("image_url"):
        embed.set_image(url=data["image_url"])
    if data.get("thumbnail_url"):
        embed.set_thumbnail(url=data["thumbnail_url"])
    if data.get("footer_text") or data.get("footer_icon"):
        embed.set_footer(text=data.get("footer_text") or "", icon_url=data.get("footer_icon") or None)
    for f in (data.get("fields") or []):
        if isinstance(f, dict) and f.get("name"):
            embed.add_field(name=f["name"][:256], value=(f.get("value") or "\u200b")[:1024], inline=bool(f.get("inline")))
    # Discord rejects embeds with no content at all - fall back so the action
    # still works even when a custom embed is configured but empty.
    if not (embed.title or embed.description or embed.fields or embed.author or embed.footer or embed.image or embed.thumbnail):
        embed.title = "Action Completed"
        embed.description = "\u200b"
    return embed


def basic_action_embed(key: str, message: str, color: str = "brand") -> discord.Embed:
    """Basic-mode action embed: emoji + two spaces + message as the title (no fields)."""
    return EmbedBuilder().title(emoji_title(key, message)).color(color).build()
