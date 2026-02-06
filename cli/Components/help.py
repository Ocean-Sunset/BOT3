import discord
from discord.ext import commands

# -------------------------------------------------------------------
# CONFIGURATION: Command-Based Category Logic
# -------------------------------------------------------------------
# Map specific COMMAND NAMES (or Cog names as a fallback) to Categories.
# The code checks this list first. If a command name is here, it goes here.
# If the command name isn't found, it checks if the Cog name is here.
# If neither, it goes to "Other".

CATEGORY_MAPPING = {
    "🛡️ Moderation": [
        "ban", "kick", "mute", "unmute", "warn", "purge", 
        "strike", "clearstrikes", "infractions", "setlimitations"
    ],
    "💰 Economy": [
        "balance", "daily", "steal", "gems", "keys", "deposit", 
        "withdraw", "bank", "opencrate", "inventory", "sell", "trade", "shop", "exchange"
    ],
    "⚙️ Utility": [
        "setbumpchannel", "colorrole", 
        "setwelcome", "setgoodbye", "color", "translate", "weather", "setverifyrole", "verify", "leaderboard", "announcement", "addrolereaction", 
        "removerolereaction", "addselfrole", "removeselfrole", "selfroles", "servercustom", "autorole", "setdestination", "setwelcomechannel", "setgoodbyechannel", "setlivestream",
        "setlivestreamchannel", "checklivestream", "iam", "iamnot", "setlevelrole", "removelevelrole", "listlevelroles", "copy", "copychannel", "copydm", "setprefix", "settingsannouncement"
        "chatreviver"
    ],
    "🎵 Music": [
        "upload", "play", "queue", "skip", "stop", "download", 
        "check_ffmpeg"
    ],
    "ℹ️ Information": [
        "profile", "info", "changelog", "analyse", "serverstats", "setannouncements"
    ],
    "🚨 Owner only commands": [
        "BServer", "UBServer", "MServer", "update", "restart", "shutdown", 
        "modify_status", "levelsystem", "levelannouncements", "setlogging", "lookup",  
        "serverlockdown", "omega", "selfkick", "backuplog", "lockdown", "unlockdown" "reload_super", "reset"
    ],
    "🌐 Insider Program": [
        "testembed", "insidersecret", "insider", "insiderchangelog", "rssfetch", 
        "ytalert", "twitchalert", "insiderstatus", "forceinsider", "insiderrequest", "insiderdaily" "subscribe_plus", "subscribre_max", "subscribe_status"
    ],
    "🎊 Giveaways & Events": [
        "giveaway", "giveawaycancel", "giveawayinfo", "poll"
    ],
    "📝 Miscellaneous": [
        "uploadasset", "listassets", "setsupportchannel", "setchangelogchannel", 
        "submitidea", "feedback", "crashreport", "kaps"
    ],
    # Any command not listed above ends up in "📂 Other" automatically
}

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="help", description="Show the bot's help menu or info about a command.")
    async def help(self, interaction: discord.Interaction, query: str = None):
        prefix = "/"  # Slash commands use / as the prefix

        # -------------------------
        # 1. SPECIFIC COMMAND HELP
        # -------------------------

        if query:
            # Search for slash command by name
            command = discord.utils.find(lambda c: c.name == query, self.bot.application_commands)
            if not command:
                # Fuzzy Search Fallback for slash commands
                matches = [
                    cmd for cmd in self.bot.application_commands
                    if query.lower() in cmd.name.lower()
                ]
                if matches:
                    suggestion = ", ".join(f"`/{c.name}`" for c in matches[:5])
                    await interaction.response.send_message(f"❌ Command not found.\nDid you mean: {suggestion}?", ephemeral=True)
                else:
                    await interaction.response.send_message(f"❌ Command `{query}` not found. Use `/help` for the menu.", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"❓ Help — `/{command.name}`",
                description=command.description or "No description available.",
                color=discord.Color.green()
            )
            # Usage generation for slash commands
            params = []
            for opt in getattr(command, 'options', []):
                if opt.required:
                    params.append(f"<{opt.name}>")
                else:
                    params.append(f"[{opt.name}]")
            usage = f"/{command.name} {' '.join(params)}".strip()
            embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
            embed.set_footer(text="<> = required | [] = optional")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # -------------------------
        # 2. SORT COMMANDS INTO CATEGORIES
        # -------------------------

        sorted_categories = {}

        def get_category(cmd):
            """
            Determines category by checking Command Name first, then Cog Name (if available).
            """
            # 1. Check if Command Name is explicitly in the list
            for cat_name, identifiers in CATEGORY_MAPPING.items():
                if cmd.name in identifiers:
                    return cat_name
            # 2. Check if Cog Name is in the list (Fallback)
            cog_name = getattr(cmd, 'cog_name', None) or "No Cog"
            for cat_name, identifiers in CATEGORY_MAPPING.items():
                if cog_name in identifiers:
                    return cat_name
            # 3. Default
            return "📂 Other"

        for cmd in self.bot.application_commands:
            cat = get_category(cmd)
            if cat not in sorted_categories:
                sorted_categories[cat] = []
            sorted_categories[cat].append(cmd)

        # Move "Other" to the end if it exists
        if "📂 Other" in sorted_categories:
            sorted_categories["📂 Other"] = sorted_categories.pop("📂 Other")

        # -------------------------
        # 3. DEFINE VIEW & SELECT MENU
        # -------------------------
        class HelpSelect(discord.ui.Select):
            def __init__(self, categories, home_embed):
                self.categories = categories
                self.home_embed = home_embed
                
                options = [
                    discord.SelectOption(
                        label="Home", description="Back to main menu", emoji="🏠"
                    )
                ]

                for cat_name, cmds in categories.items():
                    emoji = cat_name.split()[0] if len(cat_name) > 0 else "🔹"
                    label = cat_name.replace(emoji, "").strip() or cat_name
                    
                    options.append(discord.SelectOption(
                        label=label,
                        description=f"{len(cmds)} commands",
                        emoji=emoji,
                        value=cat_name
                    ))

                super().__init__(
                    placeholder="Select a category...",
                    min_values=1,
                    max_values=1,
                    options=options
                )

            async def callback(self, interaction: discord.Interaction):
                if self.values[0] == "Home":
                    await interaction.response.edit_message(embed=self.home_embed)
                    return

                selected_cat = self.values[0]
                cmds = self.categories.get(selected_cat, [])
                cmds.sort(key=lambda c: c.name)

                embed = discord.Embed(
                    title=f"{selected_cat}",
                    color=discord.Color.blurple(),
                    description=f"List of commands in **{selected_cat}**."
                )

                # Format the commands as strings for slash commands
                cmd_strings = [
                    f"**`/{c.name}`** — {c.description or 'No description'}"
                    for c in cmds
                ]

                # Function to chunk list so we don't hit 1024 char limit per field
                def chunk_list(lst, n):
                    for i in range(0, len(lst), n):
                        yield lst[i:i + n]

                # If there are NO commands (rare)
                if not cmd_strings:
                    embed.description += "\n*No commands found.*"
                else:
                    # Split into chunks of 10 commands per field to stay safe
                    chunks = list(chunk_list(cmd_strings, 10))
                    for index, chunk in enumerate(chunks):
                        field_name = "Commands" if len(chunks) == 1 else f"Commands (Part {index + 1})"
                        field_value = "\n".join(chunk)
                        embed.add_field(name=field_name, value=field_value, inline=False)

                embed.set_footer(text=f"Total: {len(cmds)} | Type /help <command> for details")
                await interaction.response.edit_message(embed=embed)

        class HelpView(discord.ui.View):
            def __init__(self, categories, home_embed):
                super().__init__(timeout=120)
                self.add_item(HelpSelect(categories, home_embed))
                self.message = None

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True
                if self.message:
                    try: 
                        await self.message.edit(view=self)
                    except: pass

        # -------------------------
        # 4. INITIAL HOME EMBED
        # -------------------------
        total_commands = sum(len(c) for c in sorted_categories.values())

        home_embed = discord.Embed(
            title="🤖 Bot Command Menu",
            description=(
                f"Select a category below to view commands.\n"
                f"To get help for a specific command, type `/help <command>`"
            ),
            color=discord.Color.gold()
        )
        home_embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        home_embed.add_field(name="📊 Stats", value=f"**{total_commands}** Commands\n**{len(sorted_categories)}** Categories", inline=False)

        # Optional: Add a field showing the categories nicely
        cat_list = ", ".join(f"`{k}`" for k in sorted_categories.keys())
        home_embed.add_field(name="📂 Available Categories", value=cat_list or "None", inline=False)

        view = HelpView(sorted_categories, home_embed)
        msg = await interaction.response.send_message(embed=home_embed, view=view, ephemeral=True)
        # Discord returns None for interaction.response.send_message, so we can't set view.message here

async def setup(bot):
    await bot.add_cog(Help(bot))