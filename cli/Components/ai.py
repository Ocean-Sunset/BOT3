import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
from typing import Optional

from Ediscord import logger, EmbedBuilder, error_embed
from Ediscord import db as neon_db
from Ediscord.variables import OPENAI_API_KEY


AI_DEFAULTS = {"enabled": True, "channel_id": None, "model": "gpt-3.5-turbo", "system_prompt": "You are a helpful Discord bot named Prowl."}


async def get_ai_settings(guild_id: int):
    pool = await neon_db.get_pool()
    if not pool:
        return dict(AI_DEFAULTS)
    row = await pool.fetchrow("SELECT settings FROM ai_settings WHERE guild_id = $1", str(guild_id))
    return {**AI_DEFAULTS, **row["settings"]} if row else dict(AI_DEFAULTS)


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

    ai_group = app_commands.Group(name="ai", description="AI-powered features")

    @ai_group.command(name="chat", description="Chat with the AI")
    @app_commands.describe(prompt="What you want to say to the AI")
    async def chat(self, interaction: discord.Interaction, prompt: str):
        if not OPENAI_API_KEY or OPENAI_API_KEY == "":
            return await interaction.response.send_message("AI is not configured. No API key set.", ephemeral=True)

        await interaction.response.defer()
        guild_id = str(interaction.guild_id)
        if guild_id not in self.sessions:
            self.sessions[guild_id] = []

        self.sessions[guild_id].append({"role": "user", "content": prompt})
        messages = [{"role": "system", "content": AI_DEFAULTS["system_prompt"]}] + self.sessions[guild_id][-20:]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                    json={"model": "gpt-3.5-turbo", "messages": messages, "max_tokens": 500},
                ) as resp:
                    data = await resp.json()
                    reply = data["choices"][0]["message"]["content"]
                    self.sessions[guild_id].append({"role": "assistant", "content": reply})
                    embed = EmbedBuilder().description(reply[:2000]).color("blue").build()
                    await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"AI request failed: {str(e)[:200]}", ephemeral=True)

    @ai_group.command(name="clear", description="Clear the AI conversation history")
    async def clear_history(self, interaction: discord.Interaction):
        self.sessions.pop(str(interaction.guild_id), None)
        await interaction.response.send_message("Conversation history cleared.", ephemeral=True)

    @ai_group.command(name="imagine", description="Generate an image from a text prompt")
    @app_commands.describe(prompt="Describe the image you want to generate")
    async def imagine(self, interaction: discord.Interaction, prompt: str):
        if not OPENAI_API_KEY:
            return await interaction.response.send_message("AI not configured.", ephemeral=True)
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                    json={"model": "dall-e-3", "prompt": prompt, "n": 1, "size": "1024x1024"},
                ) as resp:
                    data = await resp.json()
                    image_url = data["data"][0]["url"]
                    embed = EmbedBuilder().title("Generated Image").description(prompt[:1000]).image(image_url).color("blue").build()
                    await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"Image generation failed: {str(e)[:200]}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AI(bot))
