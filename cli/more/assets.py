# --------------------- IMPORTS --------------------
import os
import shutil
import discord
from discord.ext import commands
import logging
from discord import app_commands


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ASSETS_BASE_DIR = "assets"

DEFAULT_ASSETS_PATH = os.path.join(ASSETS_BASE_DIR, "default_assets")

GUILD_ASSETS_BASE_PATH = os.path.join(ASSETS_BASE_DIR, "guild_assets")

class AssetManager(commands.Cog):
    """
    A cog for managing server-specific assets (images) for the Discord bot.
    It creates unique folders for each guild and allows admins to upload assets.
    """
    def __init__(self, bot):
        self.bot = bot
        self._ensure_base_directories_exist()
        logging.info("AssetManager cog initialized.")

    def _ensure_base_directories_exist(self):
        """Ensures the base asset directories exist."""
        os.makedirs(ASSETS_BASE_DIR, exist_ok=True)
        os.makedirs(DEFAULT_ASSETS_PATH, exist_ok=True)
        os.makedirs(GUILD_ASSETS_BASE_PATH, exist_ok=True)
        logging.info(f"Ensured base asset directories exist: {ASSETS_BASE_DIR}, {DEFAULT_ASSETS_PATH}, {GUILD_ASSETS_BASE_PATH}")

    def _get_guild_asset_path(self, guild_id: int) -> str:
        """Returns the path to a specific guild's asset folder."""
        return os.path.join(GUILD_ASSETS_BASE_PATH, str(guild_id))

    def _create_guild_asset_folder(self, guild_id: int):
        """Creates a dedicated asset folder for a given guild if it doesn't exist."""
        guild_folder = self._get_guild_asset_path(guild_id)
        os.makedirs(guild_folder, exist_ok=True)
        logging.info(f"Ensured guild asset folder exists: {guild_folder}")

    def _copy_default_assets(self, guild_id: int):
        """Copies default assets from the default_assets folder to a guild's folder."""
        guild_folder = self._get_guild_asset_path(guild_id)
        
        # List of default image filenames you provided
        default_images = ["background.png", "border.png", "cat.png", "confetti.png", "impact.ttf", "impacted.ttf", "STENCIL.ttf", "unicode.impact.ttf"]

        for image_name in default_images:
            src_path = os.path.join(DEFAULT_ASSETS_PATH, image_name)
            dest_path = os.path.join(guild_folder, image_name)

            if not os.path.exists(src_path):
                logging.warning(f"Default asset not found: {src_path}. Skipping copy.")
                continue

            if not os.path.exists(dest_path):
                try:
                    shutil.copy2(src_path, dest_path)
                    logging.info(f"Copied default asset '{image_name}' to guild {guild_id} folder.")
                except Exception as e:
                    logging.error(f"Error copying default asset '{image_name}' to guild {guild_id}: {e}")
            else:
                logging.info(f"Default asset '{image_name}' already exists in guild {guild_id} folder. Skipping copy.")

    async def initialize_guild_assets(self, guild: discord.Guild):
        """
        Initializes the asset folder for a given guild, creating it if necessary
        and copying default assets.
        """
        logging.info(f"Initializing assets for guild: {guild.name} (ID: {guild.id})")
        self._create_guild_asset_folder(guild.id)
        self._copy_default_assets(guild.id)
        logging.info(f"Finished initializing assets for guild: {guild.name}")

    # --- Discord Commands for Asset Management ---

    @app_commands.command(name="uploadasset", description="Uploads an asset for this server. Usage: /uploadasset <filename> (attach file)")
    @app_commands.describe(filename="The filename to save the asset as.", attachment="The image file to upload.")
    @app_commands.checks.has_permissions(administrator=True)
    async def upload_asset(self, interaction: discord.Interaction, filename: str, attachment: discord.Attachment):
        """
        Allows an administrator to upload an image asset for their server.
        The command expects an attached file and a desired filename for the asset.
        Please make sure this is an .PNG file and it's resolution is 500x180 before uploading!
        """
        if not attachment.content_type or not attachment.content_type.startswith("image/"):
            await interaction.response.send_message("# ❌ Only image files are supported for upload.", ephemeral=True)
            return

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("# ❌ This command can only be used in a server.", ephemeral=True)
            return

        guild_asset_path = self._get_guild_asset_path(guild.id)
        file_extension = os.path.splitext(attachment.filename)[1]
        if not filename.endswith(file_extension):
            filename += file_extension

        save_path = os.path.join(guild_asset_path, filename)

        is_background = filename.lower() == "background.png"
        if is_background:
            try:
                from Ediscord import utils as edutils
                if not edutils.can_use_subscription_for_guild(interaction.user.id, guild.id):
                    await interaction.followup.send("# ❌ Uploading a custom background is limited to subscribers.\nIf you have a subscription, register this server with `/subscribe` first.", ephemeral=True)
                    return
                registered = edutils.register_guild_for_subscription(interaction.user.id, guild.id)
                if not registered:
                    await interaction.followup.send("# ❌ Could not register server under your subscription: server limit reached.", ephemeral=True)
                    return
            except Exception as e:
                logging.error(f"Subscription check failed: {e}")
                await interaction.followup.send("# ❌ Subscription check failed. Please try again later.", ephemeral=True)
                return

        try:
            await attachment.save(save_path)
            await interaction.followup.send(f"✅ Asset `{filename}` uploaded successfully to your server's assets.", ephemeral=True)
            logging.info(f"Asset '{filename}' uploaded by {interaction.user} to guild {guild.id}.")
        except Exception as e:
            await interaction.followup.send(f"# ❌ Failed to upload asset `{filename}`: {e}", ephemeral=True)
            logging.error(f"Error uploading asset '{filename}' for guild {guild.id}: {e}")

    @app_commands.command(name="listassets", description="Lists all assets available for this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_assets(self, interaction: discord.Interaction):
        """
        Lists all image assets currently stored in the server's dedicated folder.
        """
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("# ❌ This command can only be used in a server.", ephemeral=True)
            return

        guild_asset_path = self._get_guild_asset_path(guild.id)

        if not os.path.exists(guild_asset_path) or not os.listdir(guild_asset_path):
            await interaction.response.send_message("# ℹ️ No custom assets found for this server.", ephemeral=True)
            return

        asset_files = [f for f in os.listdir(guild_asset_path) if os.path.isfile(os.path.join(guild_asset_path, f))]
        if not asset_files:
            await interaction.response.send_message("# ℹ️ No custom assets found for this server.", ephemeral=True)
            return

        assets_list = "\n".join([f"- `{file}`" for file in asset_files])
        await interaction.response.send_message(f"## 🖼️ Assets for this server:\n{assets_list}", ephemeral=True)
        logging.info(f"Assets listed for guild {guild.id} by {interaction.user}.")


async def setup(bot):
    """Adds the AssetManager cog to the bot and syncs slash commands."""
    cog = AssetManager(bot)
    await bot.add_cog(cog)
    try:
        bot.tree.add_command(cog.upload_asset)
        bot.tree.add_command(cog.list_assets)
        await bot.tree.sync()
        logging.info("AssetManager slash commands synced.")
    except Exception as e:
        logging.error(f"Failed to sync AssetManager slash commands: {e}")
    logging.info("AssetManager cog setup complete.")

