"""Main entry point for the Discord Overseerr bot"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Any, Optional

import discord
from discord.ext import commands

from bot.notifications import NotificationManager
from bot.overseerr import OverseerrClient
from bot.settings import SettingsManager

# Configure logging
# Ensure logs directory exists
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / "bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


class MovieBot(commands.Bot):
    """Discord bot for movie and TV show requests via Overseerr"""

    def __init__(self, settings_manager: SettingsManager) -> None:
        self.settings_manager = settings_manager
        self.settings = settings_manager.load()

        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",  # Fallback prefix
            intents=intents,
            help_command=None,  # We'll create a custom help command
        )

        self.overseerr: Optional[OverseerrClient] = None
        self.notifications: Optional[NotificationManager] = None

    async def setup_hook(self) -> None:
        """Called when the bot is starting up"""
        logger.info("Starting bot setup...")

        # Initialize Overseerr client
        self.overseerr = OverseerrClient(
            hostname=self.settings.overseerr.hostname,
            port=self.settings.overseerr.port,
            api_key=self.settings.overseerr.api_key,
            use_ssl=self.settings.overseerr.use_ssl,
        )

        # Test Overseerr connection
        try:
            await self.overseerr.test_connection()
            logger.info("✅ Overseerr connection successful")
        except Exception as e:
            logger.error(f"❌ Overseerr connection failed: {e}")
            logger.error("Bot will start but requests will fail until Overseerr is configured")

        # Initialize notification manager
        self.notifications = NotificationManager(self)
        logger.info("✅ Notification manager initialized")

        # Load extensions/cogs
        await self.load_extensions()

        # Sync slash commands with Discord
        try:
            synced = await self.tree.sync()
            logger.info(f"✅ Synced {len(synced)} slash command(s)")
        except Exception as e:
            logger.error(f"❌ Failed to sync commands: {e}")

    async def load_extensions(self) -> None:
        """Load bot extensions/cogs"""
        extensions = [
            "bot.cogs.movie_commands",
            # "bot.cogs.tv_commands",  # Future extension
            # "bot.cogs.admin_commands",  # Future extension
        ]

        for extension in extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"✅ Loaded extension: {extension}")
            except Exception as e:
                logger.error(f"❌ Failed to load extension {extension}: {e}")

    async def on_ready(self) -> None:
        """Called when bot successfully connects to Discord"""
        logger.info(f"🤖 Bot logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"📊 Connected to {len(self.guilds)} guild(s)")

        # Check pending notifications immediately on startup
        if self.notifications:
            try:
                await self.notifications.check_pending_on_startup()
            except Exception as e:
                logger.error(f"Error checking pending notifications on startup: {e}")

            # Start background monitoring task
            self.notifications.start_monitoring()
            logger.info("✅ Started notification monitoring")

        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/request | /help",
            )
        )

    async def on_error(self, event_method: str, *args: Any, **kwargs: Any) -> None:
        """Global error handler"""
        logger.exception(f"Error in {event_method}")

    async def close(self) -> None:
        """Cleanup when bot shuts down"""
        logger.info("Shutting down bot...")
        if self.notifications:
            self.notifications.stop_monitoring()
        if self.overseerr:
            await self.overseerr.close()
        await super().close()


async def main() -> None:
    """Main entry point"""
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)

    # Load settings
    settings_manager = SettingsManager()
    settings = settings_manager.load()

    # Validate required configuration
    if not settings.discord.bot_token:
        logger.error("❌ DISCORD_BOT_TOKEN not configured!")
        logger.error("Please set the token in .env or config/settings.json")
        sys.exit(1)

    if not settings.overseerr.api_key:
        logger.warning("⚠️  OVERSEERR_API_KEY not configured!")
        logger.warning("Bot will start but movie requests will fail")

    # Create and run bot
    bot = MovieBot(settings_manager)

    # Setup signal handlers for graceful shutdown
    def handle_shutdown(sig: int, frame: Any) -> None:
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        asyncio.create_task(bot.close())

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    try:
        async with bot:
            await bot.start(settings.discord.bot_token)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
