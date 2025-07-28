# --------------------- IMPORTS --------------------
import os
import shutil
import discord
from discord.ext import commands
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration for Asset Paths ---
# Base directory for all assets. Make sure this exists in your bot's root.
ASSETS_BASE_DIR = "assets"
# Path to the default assets that will be copied to new guild folders.
# Ensure you have an 'assets/default_assets' directory with your images.
DEFAULT_ASSETS_PATH = os.path.join(ASSETS_BASE_DIR, "default_assets")
# Base path where individual guild asset folders will be created.
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
        default_images = ["background.jpg", "border.png", "cat.jpeg", "confetti.png"]

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

    @commands.command(name="uploadasset", help="Uploads an asset for this server. Usage: ?uploadasset <filename> (attach file)")
    @commands.has_permissions(administrator=True) # Only administrators can use this command
    @commands.guild_only() # Ensure this command is only used in a guild
    async def upload_asset(self, ctx: commands.Context, filename: str):
        """
        Allows an administrator to upload an image asset for their server.
        The command expects an attached file and a desired filename for the asset.
        """
        if not ctx.message.attachments:
            await ctx.send("# ❌ Please attach an image file to upload.")
            return

        attachment = ctx.message.attachments[0] # Get the first attachment

        # Basic check for image file types
        if not attachment.content_type or not attachment.content_type.startswith("image/"):
            await ctx.send("# ❌ Only image files are supported for upload.")
            return

        guild_asset_path = self._get_guild_asset_path(ctx.guild.id)
        file_extension = os.path.splitext(attachment.filename)[1] # Get original extension
        
        # Ensure the provided filename has the correct extension
        if not filename.endswith(file_extension):
            filename += file_extension

        save_path = os.path.join(guild_asset_path, filename)

        try:
            await attachment.save(save_path)
            await ctx.send(f"✅ Asset `{filename}` uploaded successfully to your server's assets.")
            logging.info(f"Asset '{filename}' uploaded by {ctx.author} to guild {ctx.guild.id}.")
        except Exception as e:
            await ctx.send(f"# ❌ Failed to upload asset `{filename}`: {e}")
            logging.error(f"Error uploading asset '{filename}' for guild {ctx.guild.id}: {e}")

    @commands.command(name="listassets", help="Lists all assets available for this server.")
    @commands.has_permissions(administrator=True) # Only administrators can use this command
    @commands.guild_only() # Ensure this command is only used in a guild
    async def list_assets(self, ctx: commands.Context):
        """
        Lists all image assets currently stored in the server's dedicated folder.
        """
        guild_asset_path = self._get_guild_asset_path(ctx.guild.id)

        if not os.path.exists(guild_asset_path) or not os.listdir(guild_asset_path):
            await ctx.send("# ℹ️ No custom assets found for this server.")
            return

        asset_files = [f for f in os.listdir(guild_asset_path) if os.path.isfile(os.path.join(guild_asset_path, f))]
        
        if not asset_files:
            await ctx.send("# ℹ️ No custom assets found for this server.")
            return

        assets_list = "\n".join([f"- `{file}`" for file in asset_files])
        await ctx.send(f"## 🖼️ Assets for this server:\n{assets_list}")
        logging.info(f"Assets listed for guild {ctx.guild.id} by {ctx.author}.")


async def setup(bot):
    """Adds the AssetManager cog to the bot."""
    await bot.add_cog(AssetManager(bot))
    logging.info("AssetManager cog setup complete.")

