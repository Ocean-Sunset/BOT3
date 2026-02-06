import discord
from discord.ext import commands
import asyncio
from Ediscord import variables
import aiohttp
import json

class MacroRelay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.settings_path = variables.SERVER_SETTINGS_FILE

        # NEW: Track all delayed relay tasks to safely cancel on unload
        self.tasks = set()

    # Called when the cog loads / reloads
    async def cog_load(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            print("MacroRelay: aiohttp session created.")

    # Called when the cog unloads / bot shuts down / reloads
    def cog_unload(self):
        print("COG UNLOADED — SOMETHING IS RELOADING OR SHUTTING DOWN")
        # Cancel all running/sleeping relay tasks
        alive = 0
        for task in list(self.tasks):
            if not task.done():
                task.cancel()
                alive += 1
        self.tasks.clear()

        print(f"MacroRelay: Cancelled {alive} pending relay tasks.")

        # Close aiohttp session safely
        if self.session and not self.session.closed:
            asyncio.create_task(self.session.close())
            print("MacroRelay: Scheduled aiohttp session closure.")

    # Load server config
    def get_relay_config(self, guild_id: int):
        try:
            with open(self.settings_path, "r") as f:
                data = json.load(f)
                guild_data = data.get(str(guild_id))
                if guild_data:
                    return guild_data.get("relay_system")
        except FileNotFoundError:
            print("Settings file not found.")
        return None

    # Admin command to view relay configuration
    @commands.command(name="viewrelay")
    @commands.has_permissions(administrator=True)
    async def view_relay_config(self, ctx):
        config = self.get_relay_config(ctx.guild.id)

        if not config:
            await ctx.send("❌ No relay system configuration found for this server.")
            return

        embed = discord.Embed(
            title="⚙️ Sol's RNG Macro Relay Config",
            color=0x00ff00
        )

        sources = [f"<#{cid}>" for cid in config.get("source_channel_ids", [])]
        embed.add_field(name="📡 Listening In", value=", ".join(sources) or "None", inline=False)

        ignored = config.get("ignored_keywords", [])
        embed.add_field(name="🚫 Ignored Biomes", value=", ".join(ignored) or "None", inline=False)

        # list targets with delays
        targets = config.get("targets", [])
        target_text = ""
        for i, t in enumerate(targets, 1):
            target_text += f"**Target {i}:** Delay {t['delay']}s\n"

        embed.add_field(name="🎯 Forwarding To", value=target_text or "None", inline=False)

        await ctx.send(embed=embed)

    # Check ignored keywords in content + embeds
    def check_if_ignored(self, message, ignored_words):
        search_text = (message.content or "").lower()

        if message.embeds:
            for embed in message.embeds:
                if embed.title:
                    search_text += " " + embed.title.lower()
                if embed.description:
                    search_text += " " + embed.description.lower()
                for field in embed.fields:
                    search_text += f" {field.name.lower()} {field.value.lower()}"

        for word in ignored_words:
            if word.lower() in search_text:
                return True

        return False

    # Post webhook with safe fallback session
    async def post_webhook(self, webhook_url, content, author_name, author_avatar, embeds):
        payload = {
            "content": content or None,
            "username": author_name,
            "avatar_url": author_avatar,
            "embeds": [e.to_dict() for e in embeds] if embeds else None
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        # Use main session, or a temporary fallback if session is closed
        session_to_use = self.session
        temp = False

        if not session_to_use or session_to_use.closed:
            session_to_use = aiohttp.ClientSession()
            temp = True

        try:
            async with session_to_use.post(webhook_url, json=payload) as resp:
                if resp.status not in (200, 204):
                    print(f"Webhook failed: {resp.status} | {await resp.text()}")
        except Exception as e:
            print(f"Webhook error during post: {e}")
        finally:
            if temp:
                await session_to_use.close()

    # Delayed relay task (tracked & cancel-safe)
    async def delayed_relay_task(self, webhook_url, delay, message):
        try:
            print("DEBUG: delayed relay task started")
            print("DEBUG: sleeping", delay)

            await asyncio.sleep(max(0, delay))

            print("DEBUG: relay task woke up")


            await self.post_webhook(
                webhook_url,
                message.content,
                message.author.display_name,
                str(message.author.display_avatar.url),
                message.embeds
            )

        except asyncio.CancelledError:
            # This happens when bot/cog unloads.
            return

        except Exception as e:
            print(f"Relay task error: {e}")

    # Message listener
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return

        if message.author.id == self.bot.user.id:
            return

        config = self.get_relay_config(message.guild.id)
        if not config:
            return

        if message.channel.id not in config.get("source_channel_ids", []):
            return

        ignored_keywords = config.get("ignored_keywords", [])
        if self.check_if_ignored(message, ignored_keywords):
            return

        targets = config.get("targets", [])
        print(f"Biome detected! Forwarding to {len(targets)} targets.")

        for target in targets:
            task = asyncio.create_task(
                self.delayed_relay_task(
                    target["webhook_url"],
                    target["delay"],
                    message
                )
            )

            # Track the task
            self.tasks.add(task)
            task.add_done_callback(lambda t: self.tasks.discard(t))


# Cog setup
async def setup(bot):
    cog = MacroRelay(bot)
    await bot.add_cog(cog)
    await cog.cog_load()
