# --------------------- IMPORTS --------------------
import discord
from discord.ext import commands
from Ediscord import utils, variables
import asyncio
import logging
import requests
import os
from yt_dlp import YoutubeDL
from discord import FFmpegPCMAudio
from googletrans import Translator
import typing
import re

class Patrivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="sewer", invoke_without_command=True)
    async def sewer(self, ctx):
        """Sewer system entry point."""
        await ctx.send("Use `?sewer enter` to enter or `?sewer exit` to leave the sewers.")

    @sewer.command(name="enter")
    async def sewer_enter(self, ctx, wing: typing.Optional[str] = None):
        """Enter the left or right sewer wing from the sewers-entrance channel."""
        if isinstance(ctx.channel, discord.Thread) or "sewers-entrance" not in ctx.channel.name.lower():
            await ctx.send("❌ You must use this command in the 'sewers-entrance' channel.")
            return

        if wing is None or wing.lower() not in ["left", "right"]:
            await ctx.send("❌ Please specify which wing to enter: `?sewer enter left` or `?sewer enter right`.")
            return

        left_role_name = "Left Sewer Wing."
        right_role_name = "Right Sewer Wing."
        left_role = discord.utils.get(ctx.guild.roles, name=left_role_name)
        right_role = discord.utils.get(ctx.guild.roles, name=right_role_name)

        # Create roles if they don't exist
        if not left_role:
            left_role = await ctx.guild.create_role(name=left_role_name, reason="Sewer system access role (left side)")
        if not right_role:
            right_role = await ctx.guild.create_role(name=right_role_name, reason="Sewer system access role (right side)")

        # Remove the other wing's role if present
        if wing.lower() == "left":
            if right_role in ctx.author.roles:
                await ctx.author.remove_roles(right_role)
            if left_role in ctx.author.roles:
                await ctx.send("🕳️ You are already in the left sewer wing!")
                return
            await ctx.author.add_roles(left_role)
            await ctx.send(f"🕳️ {ctx.author.mention} has entered the **Left Sewer Wing**! Beware of what lurks below...")
        else:
            if left_role in ctx.author.roles:
                await ctx.author.remove_roles(left_role)
            if right_role in ctx.author.roles:
                await ctx.send("🕳️ You are already in the right sewer wing!")
                return
            await ctx.author.add_roles(right_role)
            await ctx.send(f"🕳️ {ctx.author.mention} has entered the **Right Sewer Wing**! Beware of what lurks below...")

    @sewer.command(name="exit")
    async def sewer_exit(self, ctx):
        """Exit the sewer wing you are currently in. Use this in the correct wing channel."""
        channel_name = ctx.channel.name.lower()
        left_role_name = "Left Sewer Wing."
        right_role_name = "Right Sewer Wing."
        left_role = discord.utils.get(ctx.guild.roles, name=left_role_name)
        right_role = discord.utils.get(ctx.guild.roles, name=right_role_name)

        # Check for left wing exit
        if "left-system-wing" in channel_name:
            if not left_role or left_role not in ctx.author.roles:
                await ctx.send("❌ You are not in the left sewer wing or do not have the role.")
                return
            await ctx.send(f"🌞 {ctx.author.mention} has exited the **Left Sewer Wing**. Welcome back to the surface!")
            await asyncio.sleep(2)
            await ctx.author.remove_roles(left_role)
            return

        # Check for right wing exit
        if "right-system-wing" in channel_name:
            if not right_role or right_role not in ctx.author.roles:
                await ctx.send("❌ You are not in the right sewer wing or do not have the role.")
                return
            
            await ctx.send(f"🌞 {ctx.author.mention} has exited the **Right Sewer Wing**. Welcome back to the surface!")
            await asyncio.sleep(2)
            await ctx.author.remove_roles(right_role)
            return

        await ctx.send("❌ You must use this command in either the left or right sewer wing channel.")

async def setup(bot):
    await bot.add_cog(Patrivia(bot))