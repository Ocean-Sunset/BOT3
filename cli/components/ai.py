import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
import os
import time
import datetime
from typing import Optional

from Ediscord import logger, EmbedBuilder
from Ediscord import db as neon_db


async def _resolve_key():
    """Pick the active API key: DB first, then env vars (openrouter > groq > openai)."""
    for name in ("openrouter", "groq", "openai"):
        try:
            pool = await neon_db.get_pool()
            if pool:
                row = await pool.fetchrow("SELECT value FROM api_keys WHERE key_name = $1", name)
                if row and row["value"]:
                    return row["value"], name
        except Exception:
            pass
        env = os.environ.get(f"{name.upper()}_API_KEY", "")
        if env:
            return env, name
    return "", ""


async def _resolve_base(provider):
    if provider == "openrouter":
        return "https://openrouter.ai/api/v1"
    if provider == "groq":
        return "https://api.groq.com/openai/v1"
    return "https://api.openai.com/v1"


AI_DEFAULTS = {
    "enabled": True,
    "model": "gpt-3.5-turbo",
    "system_prompt": "You are a helpful Discord bot named Prowl. Be concise and friendly.",
    "max_tokens": 500,
    "temperature": 0.7,
}


async def get_ai_settings(guild_id: int):
    pool = await neon_db.get_pool()
    if not pool:
        return dict(AI_DEFAULTS)
    row = await pool.fetchrow("SELECT settings FROM ai_settings WHERE guild_id = $1", str(guild_id))
    return neon_db.parse_settings(row["settings"], AI_DEFAULTS) if row else dict(AI_DEFAULTS)


async def save_ai_settings(guild_id: int, settings: dict):
    pool = await neon_db.get_pool()
    if not pool:
        return
    await pool.execute(
        "INSERT INTO ai_settings (guild_id, settings) VALUES ($1, $2::jsonb) "
        "ON CONFLICT (guild_id) DO UPDATE SET settings = $2::jsonb",
        str(guild_id), json.dumps(settings),
    )


class AI(commands.Cog, name="AI"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sessions = {}
        self._last_global = 0
        self._last_user = {}

    ai_group = app_commands.Group(name="ai", description="AI-powered features")

    @ai_group.command(name="chat", description="Chat with the AI")
    @app_commands.describe(prompt="What you want to say to the AI")
    async def chat(self, interaction: discord.Interaction, prompt: str):
        api_key, provider = await _resolve_key()
        if not api_key:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("AI Not Configured").description("No API key set. Contact the bot owner.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )

        # Rate limits: 5s global, 1min per user
        now = time.time()
        if now - self._last_global < 5:
            wait = int(5 - (now - self._last_global))
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Slow Down").description(f"Global cooldown — try again in {wait}s.").color("orange").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        uid = str(interaction.user.id)
        last = self._last_user.get(uid, 0)
        if now - last < 60:
            wait = int(60 - (now - last))
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Cooldown").description(f"You can use AI again in {wait}s.").color("orange").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        self._last_global = now
        self._last_user[uid] = now

        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        if guild_id not in self.sessions:
            self.sessions[guild_id] = []

        settings = await get_ai_settings(interaction.guild_id)
        system_prompt = settings.get("system_prompt", AI_DEFAULTS["system_prompt"])
        model = settings.get("model", "gpt-3.5-turbo")
        max_tokens = settings.get("max_tokens", 500)
        temperature = settings.get("temperature", 0.7)

        self.sessions[guild_id].append({"role": "user", "content": prompt})
        messages = [{"role": "system", "content": system_prompt}] + self.sessions[guild_id][-20:]

        try:
            api_base = await _resolve_base(provider)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_base + "/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature},
                ) as resp:
                    if resp.status != 200:
                        error_data = await resp.json()
                        error_msg = error_data.get("error", {}).get("message", "Unknown error")
                        return await interaction.followup.send(
                            embed=EmbedBuilder().title("AI Error").description(f"API returned error: {error_msg[:200]}").color("red").timestamp(datetime.datetime.utcnow()).build(),
                            ephemeral=True
                        )
                    data = await resp.json()
                    reply = data["choices"][0]["message"]["content"]
                    tokens_used = data.get("usage", {}).get("total_tokens", 0)
                    self.sessions[guild_id].append({"role": "assistant", "content": reply})
                    await interaction.followup.send(
                        content=f"{interaction.user.mention}\n\n{reply[:4000]}",
                        embed=EmbedBuilder()
                        .color("blue")
                        .field("Model", model)
                        .field("Tokens Used", str(tokens_used))
                        .footer(f"Requested by {interaction.user.display_name}")
                        .timestamp(datetime.datetime.utcnow())
                        .build()
                    )
        except aiohttp.ClientError as e:
            await interaction.followup.send(
                embed=EmbedBuilder().title("Connection Error").description(f"Failed to reach AI service: {str(e)[:200]}").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"AI chat error: {e}")
            await interaction.followup.send(
                embed=EmbedBuilder().title("AI Error").description(f"Something went wrong: {str(e)[:200]}").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )

    @ai_group.command(name="clear", description="Clear the AI conversation history")
    async def clear_history(self, interaction: discord.Interaction):
        self.sessions.pop(str(interaction.guild_id), None)
        await interaction.response.send_message(
            embed=EmbedBuilder().title("History Cleared").description("AI conversation history has been cleared.").color("green").timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )

    @ai_group.command(name="imagine", description="Generate an image from a text prompt")
    @app_commands.describe(prompt="Describe the image you want to generate")
    async def imagine(self, interaction: discord.Interaction, prompt: str):
        api_key, _ = await _resolve_key()
        if not api_key:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("AI Not Configured").description("No API key set.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                    json={"model": "dall-e-3", "prompt": prompt, "n": 1, "size": "1024x1024"},
                ) as resp:
                    if resp.status != 200:
                        error_data = await resp.json()
                        error_msg = error_data.get("error", {}).get("message", "Unknown error")
                        return await interaction.followup.send(
                            embed=EmbedBuilder().title("Generation Failed").description(f"API error: {error_msg[:200]}").color("red").timestamp(datetime.datetime.utcnow()).build(),
                            ephemeral=True
                        )
                    data = await resp.json()
                    image_url = data["data"][0]["url"]
                    embed = (
                        EmbedBuilder()
                        .title("Generated Image")
                        .description(prompt[:1000])
                        .image(image_url)
                        .color("blue")
                        .footer(f"Requested by {interaction.user.display_name}")
                        .timestamp(datetime.datetime.utcnow())
                        .build()
                    )
                    await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"AI imagine error: {e}")
            await interaction.followup.send(
                embed=EmbedBuilder().title("Generation Failed").description(f"Something went wrong: {str(e)[:200]}").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )

    @ai_group.command(name="config", description="View AI configuration")
    async def config(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_ai_settings(interaction.guild_id)
        embed = (
            EmbedBuilder()
            .title("AI Configuration")
            .color("blue")
            .field("Enabled", "Yes" if settings.get("enabled") else "No")
            .field("Model", settings.get("model", "gpt-3.5-turbo"))
            .field("Max Tokens", str(settings.get("max_tokens", 500)))
            .field("Temperature", str(settings.get("temperature", 0.7)))
            .field("System Prompt", settings.get("system_prompt", AI_DEFAULTS["system_prompt"])[:1024])
            .timestamp(datetime.datetime.utcnow())
            .build()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ai_group.command(name="model", description="Set the AI model to use")
    @app_commands.describe(model="The model name")
    @app_commands.choices(model=[
        app_commands.Choice(name="GPT-3.5 Turbo", value="gpt-3.5-turbo"),
        app_commands.Choice(name="GPT-4", value="gpt-4"),
        app_commands.Choice(name="GPT-4 Turbo", value="gpt-4-turbo"),
        app_commands.Choice(name="GPT-4o", value="gpt-4o"),
        app_commands.Choice(name="GPT-4o Mini", value="gpt-4o-mini"),
    ])
    async def set_model(self, interaction: discord.Interaction, model: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_ai_settings(interaction.guild_id)
        settings["model"] = model
        await save_ai_settings(interaction.guild_id, settings)
        await interaction.response.send_message(
            embed=EmbedBuilder().title("Model Updated").description(f"AI model set to **{model}**").color("green").timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )

    @ai_group.command(name="prompt", description="Set the AI system prompt")
    @app_commands.describe(prompt="The system prompt for the AI")
    async def set_prompt(self, interaction: discord.Interaction, prompt: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Permission Denied").description("You need Manage Server permission.").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        if len(prompt) > 1000:
            return await interaction.response.send_message(
                embed=EmbedBuilder().title("Too Long").description("System prompt too long (max 1000 characters).").color("red").timestamp(datetime.datetime.utcnow()).build(),
                ephemeral=True
            )
        settings = await get_ai_settings(interaction.guild_id)
        settings["system_prompt"] = prompt
        await save_ai_settings(interaction.guild_id, settings)
        await interaction.response.send_message(
            embed=EmbedBuilder().title("Prompt Updated").description(f"System prompt updated:\n```\n{prompt[:500]}\n```").color("green").timestamp(datetime.datetime.utcnow()).build(),
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AI(bot))
