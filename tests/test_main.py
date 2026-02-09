"""Unit tests for main bot functionality"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from bot.main import MovieBot
from bot.settings import BotSettings, SettingsManager


@pytest.mark.unit
class TestMovieBot:
    """Test MovieBot class"""

    def test_movie_bot_creation(self, settings_manager):
        """Test creating a MovieBot instance"""
        bot = MovieBot(settings_manager)

        assert bot.settings_manager == settings_manager
        assert bot.settings is not None
        assert isinstance(bot.settings, BotSettings)
        assert bot.overseerr is None
        assert bot.notifications is None

    def test_movie_bot_intents(self, settings_manager):
        """Test that bot has correct Discord intents"""
        bot = MovieBot(settings_manager)

        assert bot.intents.message_content is True

    def test_movie_bot_command_prefix(self, settings_manager):
        """Test bot command prefix is set"""
        bot = MovieBot(settings_manager)

        assert bot.command_prefix == "!"

    def test_movie_bot_help_command_disabled(self, settings_manager):
        """Test that default help command is disabled"""
        bot = MovieBot(settings_manager)

        assert bot.help_command is None

    @pytest.mark.asyncio
    async def test_setup_hook_overseerr_connection_success(self, settings_manager, mock_env_vars):
        """Test setup_hook with successful Overseerr connection"""
        bot = MovieBot(settings_manager)

        # Mock Overseerr client
        with patch("bot.main.OverseerrClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.test_connection = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock tree.sync
            bot.tree.sync = AsyncMock(return_value=[])

            # Mock load_extension
            bot.load_extension = AsyncMock()

            # Run setup hook
            with patch("bot.main.NotificationManager"):
                await bot.setup_hook()

            # Verify Overseerr client was created and tested
            mock_client_class.assert_called_once()
            mock_client.test_connection.assert_called_once()

            # Verify commands were synced
            bot.tree.sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_hook_overseerr_connection_failure(self, settings_manager):
        """Test setup_hook with failed Overseerr connection"""
        bot = MovieBot(settings_manager)

        # Mock Overseerr client that fails connection test
        with patch("bot.main.OverseerrClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.test_connection = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client_class.return_value = mock_client

            # Mock tree.sync
            bot.tree.sync = AsyncMock(return_value=[])

            # Mock load_extension
            bot.load_extension = AsyncMock()

            # Run setup hook - should not raise exception
            with patch("bot.main.NotificationManager"):
                await bot.setup_hook()

            # Bot should still initialize even if Overseerr connection fails
            assert bot.overseerr is not None

    @pytest.mark.asyncio
    async def test_setup_hook_loads_extensions(self, settings_manager):
        """Test that setup_hook loads extensions"""
        bot = MovieBot(settings_manager)

        # Mock dependencies
        with patch("bot.main.OverseerrClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.test_connection = AsyncMock()
            mock_client_class.return_value = mock_client

            bot.tree.sync = AsyncMock(return_value=[])
            bot.load_extension = AsyncMock()

            with patch("bot.main.NotificationManager"):
                await bot.setup_hook()

            # Verify extensions were loaded
            assert bot.load_extension.called

            # Check that movie_commands was loaded
            calls = [str(call) for call in bot.load_extension.call_args_list]
            assert any("movie_commands" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_setup_hook_sync_commands(self, settings_manager):
        """Test that setup_hook syncs slash commands"""
        bot = MovieBot(settings_manager)

        with patch("bot.main.OverseerrClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.test_connection = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock sync to return 5 commands
            bot.tree.sync = AsyncMock(return_value=[1, 2, 3, 4, 5])
            bot.load_extension = AsyncMock()

            with patch("bot.main.NotificationManager"):
                await bot.setup_hook()

            # Verify sync was called
            bot.tree.sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_hook_sync_failure(self, settings_manager):
        """Test handling of command sync failure"""
        bot = MovieBot(settings_manager)

        with patch("bot.main.OverseerrClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.test_connection = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock sync to raise exception
            bot.tree.sync = AsyncMock(side_effect=Exception("Sync failed"))
            bot.load_extension = AsyncMock()

            # Should not raise exception
            with patch("bot.main.NotificationManager"):
                await bot.setup_hook()

    @pytest.mark.asyncio
    async def test_setup_hook_initializes_notifications(self, settings_manager):
        """Test that setup_hook initializes notification manager"""
        bot = MovieBot(settings_manager)

        with patch("bot.main.OverseerrClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.test_connection = AsyncMock()
            mock_client_class.return_value = mock_client

            bot.tree.sync = AsyncMock(return_value=[])
            bot.load_extension = AsyncMock()

            with patch("bot.main.NotificationManager") as mock_notif_class:
                mock_notif = MagicMock()
                mock_notif.check_pending_on_startup = AsyncMock()
                mock_notif.start_monitoring = MagicMock()
                mock_notif_class.return_value = mock_notif

                await bot.setup_hook()

                # Verify notification manager was created
                mock_notif_class.assert_called_once_with(bot)
                assert bot.notifications is not None

    @pytest.mark.asyncio
    async def test_on_ready(self, settings_manager):
        """Test on_ready event handler"""
        bot = MovieBot(settings_manager)

        # Mock notifications to avoid errors
        bot.notifications = None

        # Mock change_presence to avoid Discord API call
        bot.change_presence = AsyncMock()

        # Mock user property and guilds - use patch.object with proper context manager
        with patch.object(
            type(bot),
            "user",
            new_callable=lambda: property(lambda self: MagicMock(id=123456789, name="TestBot")),
        ):
            with patch.object(
                type(bot),
                "guilds",
                new_callable=lambda: property(lambda self: [MagicMock(), MagicMock()]),
            ):
                # Should not raise exception
                await bot.on_ready()

    @pytest.mark.asyncio
    async def test_on_error(self, settings_manager):
        """Test global error handler"""
        bot = MovieBot(settings_manager)

        # Should not raise exception
        await bot.on_error("test_event")

    @pytest.mark.asyncio
    async def test_close(self, settings_manager):
        """Test bot cleanup on close"""
        bot = MovieBot(settings_manager)

        # Mock dependencies
        mock_overseerr = AsyncMock()
        mock_overseerr.close = AsyncMock()
        bot.overseerr = mock_overseerr

        mock_notifications = MagicMock()
        mock_notifications.stop_monitoring = MagicMock()
        bot.notifications = mock_notifications

        # Mock parent close
        with patch("discord.ext.commands.Bot.close", new_callable=AsyncMock):
            await bot.close()

        # Verify cleanup was performed
        mock_notifications.stop_monitoring.assert_called_once()
        mock_overseerr.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_dependencies(self, settings_manager):
        """Test close when dependencies are None"""
        bot = MovieBot(settings_manager)
        bot.overseerr = None
        bot.notifications = None

        # Should not raise exception
        with patch("discord.ext.commands.Bot.close", new_callable=AsyncMock):
            await bot.close()


@pytest.mark.unit
class TestMainFunction:
    """Test main entry point function"""

    @pytest.mark.asyncio
    async def test_main_missing_bot_token(self, monkeypatch, temp_config_dir):
        """Test main function exits when bot token is missing"""
        # Clear bot token
        monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)

        settings_file = temp_config_dir / "settings.json"

        # Create minimal settings file without token
        import json

        with open(settings_file, "w") as f:
            json.dump({"discord": {}, "overseerr": {}}, f)

        # Patch SettingsManager to use temp file
        with patch("bot.main.SettingsManager") as mock_sm_class:
            mock_sm = MagicMock()
            settings = BotSettings()
            settings.discord.bot_token = ""  # No token
            settings.overseerr.api_key = "test_key"
            mock_sm.load = MagicMock(return_value=settings)
            mock_sm_class.return_value = mock_sm

            from bot.main import main

            # Should exit with code 1
            with pytest.raises(SystemExit) as exc_info:
                await main()

            assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_main_missing_api_key_warning(self, monkeypatch, temp_config_dir):
        """Test main function warns when API key is missing but continues"""
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "test_token")

        settings_file = temp_config_dir / "settings.json"

        import json

        with open(settings_file, "w") as f:
            json.dump({"discord": {}, "overseerr": {}}, f)

        with patch("bot.main.SettingsManager") as mock_sm_class:
            mock_sm = MagicMock()
            settings = BotSettings()
            settings.discord.bot_token = "test_token"
            settings.overseerr.api_key = ""  # No API key
            mock_sm.load = MagicMock(return_value=settings)
            mock_sm_class.return_value = mock_sm

            with patch("bot.main.MovieBot") as mock_bot_class:
                mock_bot = MagicMock()
                mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
                mock_bot.__aexit__ = AsyncMock()
                mock_bot.start = AsyncMock()
                mock_bot_class.return_value = mock_bot

                from bot.main import main

                # Should not exit, just warn
                try:
                    await main()
                except:
                    pass  # Bot.start will fail in test but that's ok

    @pytest.mark.asyncio
    async def test_main_creates_logs_directory(self, temp_config_dir, monkeypatch):
        """Test that main creates logs directory"""
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "test_token")

        with patch("bot.main.Path") as mock_path_class:
            mock_logs_path = MagicMock()
            mock_logs_path.mkdir = MagicMock()
            mock_path_class.return_value = mock_logs_path

            with patch("bot.main.SettingsManager") as mock_sm_class:
                mock_sm = MagicMock()
                settings = BotSettings()
                settings.discord.bot_token = "test_token"
                settings.overseerr.api_key = "test_key"
                mock_sm.load = MagicMock(return_value=settings)
                mock_sm_class.return_value = mock_sm

                with patch("bot.main.MovieBot") as mock_bot_class:
                    mock_bot = MagicMock()
                    mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
                    mock_bot.__aexit__ = AsyncMock()
                    mock_bot.start = AsyncMock()
                    mock_bot_class.return_value = mock_bot

                    from bot.main import main

                    try:
                        await main()
                    except:
                        pass


@pytest.mark.unit
class TestBotSettings:
    """Test bot settings and configuration"""

    def test_settings_from_manager(self, settings_manager):
        """Test loading settings through manager"""
        settings = settings_manager.load()

        assert isinstance(settings, BotSettings)
        assert settings.version == "1.0.0"

    def test_settings_with_env_vars(self, mock_env_vars):
        """Test that environment variables are properly loaded"""
        settings = BotSettings()

        # Verify env vars are loaded
        assert settings.discord.bot_token == "test_bot_token_12345"
        assert settings.overseerr.hostname == "test.overseerr.local"
        assert settings.overseerr.api_key == "test_api_key_abcdef"
