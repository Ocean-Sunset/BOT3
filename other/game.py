# --------------------------------
# --------------------------------
# DEPRECATED, USE AT YOUR OWN RISK
# --------------------------------
# --------------------------------

import discord
from discord.ext import commands
from Ediscord import utils, variables
import asyncio
from discord import app_commands
import logging
from typing import List

# Simple game Cog: ?game -> host-only menu -> invite flow -> Tic-Tac-Toe game

# Numbered games registry. Add more entries here when new games are implemented.
GAMES = {
    "1": {
        "name": "Tic-Tac-Toe",
        "id": "tictactoe",
        "description": "Classic X's and O's game",
        "available": True,
        "color": discord.Color.green(),
    },
    "2": {
        "name": "Chess",
        "id": "chess",
        "description": "Coming soon",
        "available": False,
        "color": discord.Color.blurple(),
    },
    "3": {
        "name": "Halloween Special",
        "id": "halloween",
        "description": "Coming soon",
        "available": False,
        "color": discord.Color.orange(),
    },
}


class InviteView(discord.ui.View):
    def __init__(self, host_id: int, max_players: int = 2, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.host_id = host_id
        self.invited: List[int] = []
        self.max_players = max_players
        self.started = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Allow interactions from anyone — specific buttons will enforce host-only where necessary
        return True

    @discord.ui.button(label="Invite by ID or mention", style=discord.ButtonStyle.primary)
    async def invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only host may open the invite modal
        if interaction.user.id != self.host_id:
            await interaction.response.send_message("Only the host may open the invite modal.", ephemeral=True)
            return
        await interaction.response.send_modal(InviteModal(self))

    @discord.ui.button(label="Start Game", style=discord.ButtonStyle.success)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only host may start
        if interaction.user.id != self.host_id:
            await interaction.response.send_message("Only the host may start the game.", ephemeral=True)
            return
        if not self.invited:
            await interaction.response.send_message("You must invite at least one player.", ephemeral=True)
            return
        self.started = True
        # Acknowledge and update the invite message
        try:
            await interaction.response.edit_message(content=f"Game starting with {len(self.invited)+1} player(s)...", view=self)
        except Exception:
            await interaction.response.send_message("Game starting...", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Join Game", style=discord.ButtonStyle.secondary)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Open join: anyone may click to join (except bots and host)
        if interaction.user.bot:
            await interaction.response.send_message("Bots cannot join games.", ephemeral=True)
            return
        if interaction.user.id == self.host_id:
            await interaction.response.send_message("Host is already in the game.", ephemeral=True)
            return
        if interaction.user.id in self.invited:
            await interaction.response.send_message("You already joined the game.", ephemeral=True)
            return
        if len(self.invited) >= self.max_players - 1:
            await interaction.response.send_message("Game is full.", ephemeral=True)
            return
        self.invited.append(interaction.user.id)
        # Try to DM as a courtesy
        try:
            await interaction.user.send(f"You joined a game hosted by <@{self.host_id}> in {interaction.guild.name}.")
        except Exception:
            # fallback: do nothing (we will edit the invite message)
            pass
        # Edit the invite message to show updated invited list
        invited_mentions = ", ".join(f"<@{uid}>" for uid in self.invited) or "None"
        try:
            await interaction.response.edit_message(content=f"Invited: {invited_mentions} (Host: <@{self.host_id}>)", view=self)
        except Exception:
            await interaction.response.send_message(f"You joined the game. Current invited: {invited_mentions}", ephemeral=True)


class InviteModal(discord.ui.Modal):
    def __init__(self, view: InviteView):
        super().__init__(title="Invite players (IDs or mentions)")
        self.view_ref = view
        self.input = discord.ui.TextInput(label="Users (space separated)", placeholder="@user1 @user2 or 123456789012345678", required=True)
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        text = self.input.value.strip()
        parts = text.split()
        added = 0
        for p in parts:
            # try to parse mention or id
            user = None
            if p.startswith("<@") and p.endswith(">"):
                try:
                    uid = int(p.strip("<@!>"))
                    user = interaction.guild.get_member(uid)
                except Exception:
                    user = None
            else:
                try:
                    uid = int(p)
                    user = interaction.guild.get_member(uid)
                except Exception:
                    user = None
            if user and user.id not in self.view_ref.invited and user.id != self.view_ref.host_id and len(self.view_ref.invited) < self.view_ref.max_players - 1:
                self.view_ref.invited.append(user.id)
                # Send DM and fallback to channel
                try:
                    await user.send(f"You are invited to a game by {interaction.user} in {interaction.guild.name}. Use the game invite in server to join when it starts.")
                except Exception:
                    # fallback: send in channel
                    await interaction.channel.send(f"{user.mention}, you were invited to a game by {interaction.user.mention} — open DMs disabled, so here's a ping.")
                added += 1
        await interaction.response.send_message(f"Invited {added} user(s). Current invited: {len(self.view_ref.invited)}", ephemeral=True)


class TicTacToeBoard(discord.ui.View):
    def __init__(self, player_x: int, player_o: int, channel: discord.TextChannel, timeout: int = 900):
        super().__init__(timeout=timeout)
        self.player_x = player_x
        self.player_o = player_o
        self.channel = channel
        self.board = [" "] * 9
        self.turn = "X"  # X always starts
        self.current_player = self.player_x
        self.finished = False

        # create 9 button placeholders (labels updated on click)
        for i in range(9):
            btn = discord.ui.Button(label=" ", style=discord.ButtonStyle.secondary, row=i // 3)
            btn.callback = self._make_callback(i)
            self.add_item(btn)

    def _make_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            # Acknowledge immediately to avoid interaction timeouts in some discord.py builds
            # We'll use ephemeral deferral and then edit the original message object.
            try:
                await interaction.response.defer(ephemeral=True)
            except Exception:
                # If defer fails, fall back to a normal send_message ack
                try:
                    await interaction.response.send_message("Processing...", ephemeral=True)
                except Exception:
                    pass

            # Quick checks and ephemeral feedback via followup
            if self.finished:
                await interaction.followup.send("Game already finished.", ephemeral=True)
                return
            # Only allow the two players to play
            if interaction.user.id not in (self.player_x, self.player_o):
                await interaction.followup.send("You are not a player in this game.", ephemeral=True)
                return
            # Check if it's this user's turn
            if (self.turn == "X" and interaction.user.id != self.player_x) or (self.turn == "O" and interaction.user.id != self.player_o):
                await interaction.followup.send("Not your turn.", ephemeral=True)
                return
            # If cell occupied
            if self.board[index] != " ":
                await interaction.followup.send("That cell is already taken.", ephemeral=True)
                return

            # Make move
            mark = self.turn
            self.board[index] = mark

            # update buttons (labels and disabled state) based on self.board
            for i, child in enumerate(self.children):
                if isinstance(child, discord.ui.Button):
                    child.label = self.board[i]
                    child.disabled = (self.board[i] != " ")

            # Check win/draw
            winner = self.check_winner()
            if winner:
                self.finished = True
                # edit the original message (interaction.message is available after ack)
                try:
                    await interaction.message.edit(content=f"Game finished — {interaction.user.mention} ({mark}) wins!", view=self)
                except Exception:
                    await interaction.followup.send(f"Game finished — {interaction.user.mention} ({mark}) wins!", ephemeral=False)
                await self.award_rewards(interaction, winner_user_id=interaction.user.id)
                self.stop()
                return

            if all(c != " " for c in self.board):
                self.finished = True
                try:
                    await interaction.message.edit(content="Game finished — Draw!", view=self)
                except Exception:
                    await interaction.followup.send("Game finished — Draw!", ephemeral=False)
                await self.award_rewards(interaction, draw=True)
                self.stop()
                return

            # switch turn
            if self.turn == "X":
                self.turn = "O"
                self.current_player = self.player_o
            else:
                self.turn = "X"
                self.current_player = self.player_x

            try:
                await interaction.message.edit(content=f"Turn: {self.turn}", view=self)
            except Exception:
                await interaction.followup.send(f"Turn: {self.turn}", ephemeral=False)
        return callback

    def check_winner(self):
        b = self.board
        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        for a,b_idx,c in wins:
            if self.board[a] == self.board[b_idx] == self.board[c] != " ":
                return True
        return False

    async def award_rewards(self, interaction: discord.Interaction, winner_user_id: int = None, draw: bool = False):
        try:
            if draw:
                # small reward to both
                reward_coins = 100
                reward_xp = 50
                for uid in (self.player_x, self.player_o):
                    utils.update_coins(uid, reward_coins)
                    data = utils.load_user_data()
                    data.setdefault(str(uid), {}).setdefault("xp", 0)
                    data[str(uid)]["xp"] = data[str(uid)].get("xp", 0) + reward_xp
                    utils.save_user_data(data)
                await self.channel.send(f"Draw — both players receive {reward_coins} coins and {reward_xp} XP!")
            else:
                # winner bigger reward
                reward_coins = 500
                reward_xp = 250
                utils.update_coins(winner_user_id, reward_coins)
                data = utils.load_user_data()
                data.setdefault(str(winner_user_id), {}).setdefault("xp", 0)
                data[str(winner_user_id)]["xp"] = data[str(winner_user_id)].get("xp", 0) + reward_xp
                utils.save_user_data(data)
                await self.channel.send(f"<@{winner_user_id}> wins and receives {reward_coins} coins and {reward_xp} XP!")
        except Exception as e:
            logging.error(f"Failed to award rewards: {e}")


class Games(commands.Cog):
    """Simple interactive games Cog. Currently implements Tic-Tac-Toe."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="game")
    async def start_game(self, ctx: commands.Context):
        host = ctx.author

        # Build numbered menu embed from GAMES
        description = "\n\n".join([f"**{num}. {g['name']}**\n{g['description']}" for num, g in GAMES.items()])
        description += "\n\nType the number anywhere in your message to select that game. Only the host's response will be accepted."

        embed = discord.Embed(title="Choose a game", description=description, color=discord.Color.blurple())
        msg = await ctx.send(content=f"{host.mention}", embed=embed)

        import re

        def check(m: commands.Context):
            if m.author.id != host.id or m.channel.id != ctx.channel.id:
                return False
            match = re.search(r"(\d+)", m.content)
            if not match:
                return False
            return match.group(1) in GAMES

        try:
            response = await self.bot.wait_for('message', check=check, timeout=120)
            choice = re.search(r"(\d+)", response.content).group(1)
            game = GAMES[choice]

            if not game['available']:
                await ctx.send(f"{game['name']} is not available yet. Stay tuned!")
                return

            # Update message to show selection
            embed = discord.Embed(title="Game selected",
                                  description=f"{game['name']} selected. Preparing invite UI...",
                                  color=game['color'])
            await msg.edit(embed=embed)
            chosen = game['id']

        except asyncio.TimeoutError:
            embed = discord.Embed(title="Menu timed out",
                                  description="No selection was made.",
                                  color=discord.Color.red())
            try:
                await msg.edit(embed=embed)
            except Exception:
                await ctx.send("Menu timed out or no selection made.")
            return
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")
            return

        if chosen == "tictactoe":
            # invite flow (2 players max)
            invite_view = InviteView(host.id, max_players=2)
            invite_embed = discord.Embed(title="Invite players", description="Invite a friend or let them Join.", color=discord.Color.green())
            # Edit the original menu message to become the invite UI so there's a single persistent message
            try:
                await msg.edit(embed=invite_embed, view=invite_view)
            except Exception:
                # fallback: send a new message if edit fails
                await ctx.send(embed=invite_embed, view=invite_view)

            # delete the host's selection message to keep the channel clean
            try:
                await response.delete()
            except Exception:
                pass

            await invite_view.wait()
            if not invite_view.started:
                return await ctx.send("Invite timed out or not started.")
            # determine players: host + first invited
            if not invite_view.invited:
                return await ctx.send("No players successfully invited. Cancelled.")
            player_o_id = invite_view.invited[0]
            player_x_id = host.id
            # countdown
            countdown_msg = await ctx.send("Starting in 3...")
            for i in range(3, 0, -1):
                await countdown_msg.edit(content=f"Starting in {i}...")
                await asyncio.sleep(1)
            await countdown_msg.edit(content="Game started!")
            board = TicTacToeBoard(player_x_id, player_o_id, ctx.channel)
            await ctx.send(f"Tic-Tac-Toe: <@{player_x_id}> (X) vs <@{player_o_id}> (O)\nTurn: X", view=board)


async def setup(bot):
    await bot.add_cog(Games(bot))
