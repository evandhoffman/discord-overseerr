"""Integration tests for Discord Overseerr Bot

These tests verify interactions between different components
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aioresponses import aioresponses

# Patch logging before importing bot.main to prevent file handler creation
with patch("logging.basicConfig"):
    from bot.main import MovieBot

from bot.overseerr import MediaStatus, Movie
from bot.settings import SettingsManager


@pytest.mark.integration
class TestMovieRequestFlow:
    """Test complete movie request workflow"""

    @pytest.mark.asyncio
    async def test_full_movie_request_workflow(
        self,
        settings_manager,
        overseerr_search_response,
        overseerr_movie_details_response,
        overseerr_request_success_response,
    ):
        """Test complete workflow: search -> details -> request"""
        bot = MovieBot(settings_manager)

        # Setup mocks
        with patch("bot.main.OverseerrClient") as mock_client_class:
            mock_client = AsyncMock()

            # Mock search
            movie = Movie(
                tmdb_id=550,
                title="Fight Club",
                overview="A ticking-time-bomb insomniac...",
                release_date="1999-10-15",
                poster_path="/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
                available=False,
                requested=False,
                status=MediaStatus.UNKNOWN,
            )
            mock_client.search_media = AsyncMock(return_value=[movie])

            # Mock details
            movie_details = Movie(
                tmdb_id=550,
                title="Fight Club",
                overview="A ticking-time-bomb insomniac...",
                release_date="1999-10-15",
                poster_path="/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
                available=False,
                requested=False,
                status=MediaStatus.UNKNOWN,
                cast=["Brad Pitt", "Edward Norton"],
            )
            mock_client.get_movie_by_id = AsyncMock(return_value=movie_details)

            # Mock request
            from bot.overseerr import MovieRequestResult

            mock_client.request_movie = AsyncMock(return_value=MovieRequestResult(success=True))

            mock_client.test_connection = AsyncMock()
            mock_client_class.return_value = mock_client

            bot.tree.sync = AsyncMock(return_value=[])
            bot.load_extension = AsyncMock()

            with patch("bot.main.NotificationManager"):
                await bot.setup_hook()

            # Test search
            results = await bot.overseerr.search_media("Fight Club")
            assert len(results) == 1
            assert results[0].title == "Fight Club"

            # Test get details
            details = await bot.overseerr.get_movie_by_id(550)
            assert details.title == "Fight Club"
            assert len(details.cast) == 2

            # Test request
            result = await bot.overseerr.request_movie(550)
            assert result.success is True

            await bot.close()

    @pytest.mark.asyncio
    async def test_movie_request_with_authorization(
        self, settings_manager, mock_discord_interaction
    ):
        """Test movie request with user authorization check"""
        # Set up authorized users
        settings = settings_manager.load()
        settings.discord.authorized_users = [111, 222]  # Only these users

        bot = MovieBot(settings_manager)
        bot.settings = settings

        # Load movie commands cog
        from bot.cogs.movie_commands import MovieCommands

        # Mock Overseerr
        mock_overseerr = AsyncMock()
        bot.overseerr = mock_overseerr

        # Test authorized user (111)
        mock_discord_interaction.user.id = 111
        mock_overseerr.search_media = AsyncMock(return_value=[])

        # Create cog instance
        cog = MovieCommands(bot)

        # Call the command directly with the interaction
        await cog.request_media.callback(cog, mock_discord_interaction, "Test Movie")

        # Should have deferred and searched
        assert mock_discord_interaction.response.defer.called
        assert mock_overseerr.search_media.called


@pytest.mark.integration
class TestNotificationWorkflow:
    """Test notification workflow integration"""

    @pytest.mark.asyncio
    async def test_request_tracking_and_notification(self, settings_manager, temp_config_dir):
        """Test tracking a request and sending notification when available"""
        from bot.notifications import NotificationManager

        bot = MagicMock()
        bot.settings = settings_manager.load()
        bot.settings.discord.notification_check_interval = 5

        # Mock Overseerr client
        mock_overseerr = AsyncMock()

        # Initially movie is pending
        pending_movie = Movie(
            tmdb_id=550,
            title="Fight Club",
            overview="Test",
            release_date="1999-10-15",
            poster_path=None,
            available=False,
            requested=True,
            status=MediaStatus.PENDING,
        )

        # Then movie becomes available
        available_movie = Movie(
            tmdb_id=550,
            title="Fight Club",
            overview="Test",
            release_date="1999-10-15",
            poster_path=None,
            available=True,
            requested=True,
            status=MediaStatus.AVAILABLE,
        )

        mock_overseerr.get_movie_by_id = AsyncMock(side_effect=[pending_movie, available_movie])
        mock_overseerr.get_media_by_id = AsyncMock(side_effect=[pending_movie, available_movie])
        bot.overseerr = mock_overseerr

        # Mock fetch_user (async)
        mock_user = MagicMock()
        mock_user.id = 111
        mock_user.name = "TestUser"
        mock_user.send = AsyncMock()
        bot.fetch_user = AsyncMock(return_value=mock_user)

        # Create notification manager
        notifications_file = temp_config_dir / "notifications.json"
        manager = NotificationManager(
            bot=bot,
            notifications_file=str(notifications_file),
        )

        # Add request to track
        manager.add_request(
            user_id=111,
            username="TestUser",
            tmdb_id=550,
            title="Fight Club",
            is_4k=False,
        )

        # First check - movie still pending
        await manager._check_and_notify()
        assert "111:550" in manager.pending_requests
        # Note: Mock send might be called for status change notification

        # Second check - movie now available
        await manager._check_and_notify()
        assert "111:550" not in manager.pending_requests
        # Notification sending should happen when movie becomes available
        assert mock_user.send.called


@pytest.mark.integration
class TestBotInitialization:
    """Test bot initialization with all components"""

    @pytest.mark.asyncio
    async def test_bot_full_initialization(self, settings_manager):
        """Test complete bot initialization with all components"""
        bot = MovieBot(settings_manager)

        with patch("bot.main.OverseerrClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.test_connection = AsyncMock()
            mock_client_class.return_value = mock_client

            bot.tree.sync = AsyncMock(return_value=[1, 2, 3])
            bot.load_extension = AsyncMock()

            with patch("bot.main.NotificationManager") as mock_notif_class:
                mock_notif = MagicMock()
                mock_notif.check_pending_on_startup = AsyncMock()
                mock_notif.start_monitoring = MagicMock()
                mock_notif_class.return_value = mock_notif

                # Run setup
                await bot.setup_hook()

                # Verify all components initialized
                assert bot.overseerr is not None
                assert bot.notifications is not None

                # Verify connection was tested
                mock_client.test_connection.assert_called_once()

                # Verify commands synced
                bot.tree.sync.assert_called_once()

                # Verify extensions loaded
                assert bot.load_extension.called

                # Note: check_pending_on_startup and start_monitoring are called in on_ready, not setup_hook
                # So we don't assert them here

    @pytest.mark.asyncio
    async def test_bot_initialization_with_failures(self, settings_manager):
        """Test bot handles initialization failures gracefully"""
        bot = MovieBot(settings_manager)

        with patch("bot.main.OverseerrClient") as mock_client_class:
            mock_client = AsyncMock()
            # Connection test fails
            mock_client.test_connection = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client_class.return_value = mock_client

            bot.tree.sync = AsyncMock(return_value=[])
            # Extension loading fails
            bot.load_extension = AsyncMock(side_effect=Exception("Failed to load cog"))

            with patch("bot.main.NotificationManager") as mock_notif_class:
                mock_notif = MagicMock()
                mock_notif.check_pending_on_startup = AsyncMock()
                mock_notif.start_monitoring = MagicMock()
                mock_notif_class.return_value = mock_notif

                # Should not raise exception
                await bot.setup_hook()

                # Bot should still have components initialized
                assert bot.overseerr is not None
                assert bot.notifications is not None


@pytest.mark.integration
class TestSettingsIntegration:
    """Test settings integration with different components"""

    @pytest.mark.asyncio
    async def test_settings_propagation(self, mock_env_vars):
        """Test that settings propagate correctly to all components"""
        from bot.settings import SettingsManager

        manager = SettingsManager()
        settings = manager.load()

        # Verify env vars loaded
        assert settings.discord.bot_token == "test_bot_token_12345"
        assert settings.overseerr.hostname == "test.overseerr.local"
        assert settings.overseerr.api_key == "test_api_key_abcdef"
        assert settings.discord.authorized_users == [111111111, 222222222, 333333333]

        # Create bot with these settings
        bot = MovieBot(manager)

        # Verify bot has correct settings
        assert bot.settings.overseerr.hostname == "test.overseerr.local"
        assert bot.settings.discord.authorized_users == [111111111, 222222222, 333333333]

    def test_settings_file_and_env_precedence(self, temp_settings_file, monkeypatch):
        """Test that env vars override file settings"""
        # Set conflicting env var
        monkeypatch.setenv("OVERSEERR_HOSTNAME", "env.override.com")

        from bot.settings import SettingsManager

        manager = SettingsManager(config_path=str(temp_settings_file))
        settings = manager.load()

        # Env var should take precedence over file
        assert settings.overseerr.hostname == "env.override.com"


@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end workflow tests"""

    @pytest.mark.asyncio
    async def test_search_to_request_workflow(self, overseerr_client):
        """Test searching and requesting a movie end-to-end"""
        with aioresponses() as m:
            # Mock search
            m.get(
                f"{overseerr_client.base_url}search?query=inception&page=1&language=en",
                status=200,
                payload={
                    "page": 1,
                    "totalPages": 1,
                    "totalResults": 1,
                    "results": [
                        {
                            "id": 27205,
                            "title": "Inception",
                            "overview": "Cobb steals secrets...",
                            "releaseDate": "2010-07-16",
                            "posterPath": "/test.jpg",
                            "mediaType": "movie",
                            "popularity": 89.5,
                            "mediaInfo": {
                                "status": 1,
                                "status4k": 1,
                            },
                        }
                    ],
                },
            )

            # Mock movie details
            m.get(
                f"{overseerr_client.base_url}movie/27205",
                status=200,
                payload={
                    "id": 27205,
                    "title": "Inception",
                    "overview": "Cobb steals secrets...",
                    "releaseDate": "2010-07-16",
                    "posterPath": "/test.jpg",
                    "mediaType": "movie",
                    "popularity": 89.5,
                    "mediaInfo": {
                        "status": 1,
                        "status4k": 1,
                        "requests": [],
                    },
                    "cast": [
                        {"name": "Leonardo DiCaprio"},
                        {"name": "Joseph Gordon-Levitt"},
                    ],
                },
            )

            # Mock request
            m.post(
                f"{overseerr_client.base_url}request",
                status=201,
                payload={
                    "id": 1,
                    "status": 2,
                    "createdAt": "2026-02-08T12:00:00.000Z",
                    "type": "movie",
                    "is4k": False,
                },
            )

            # Execute workflow
            # 1. Search
            results = await overseerr_client.search_media("inception")
            assert len(results) == 1
            assert results[0].title == "Inception"

            movie_id = results[0].tmdb_id

            # 2. Get details
            details = await overseerr_client.get_movie_by_id(movie_id)
            assert details.title == "Inception"
            assert len(details.cast) == 2

            # 3. Request
            result = await overseerr_client.request_movie(movie_id)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_4k_request_workflow(self, overseerr_client):
        """Test requesting a movie in 4K"""
        with aioresponses() as m:
            # Mock search with 4K available
            m.get(
                f"{overseerr_client.base_url}search?query=interstellar&page=1&language=en",
                status=200,
                payload={
                    "page": 1,
                    "totalPages": 1,
                    "totalResults": 1,
                    "results": [
                        {
                            "id": 157336,
                            "title": "Interstellar",
                            "overview": "Space exploration...",
                            "releaseDate": "2014-11-07",
                            "posterPath": "/test.jpg",
                            "mediaType": "movie",
                            "popularity": 95.2,
                            "mediaInfo": {
                                "status": 5,  # Available in 1080p
                                "status4k": 1,  # Not in 4K
                            },
                        }
                    ],
                },
            )

            # Mock 4K details
            m.get(
                f"{overseerr_client.base_url}movie/157336",
                status=200,
                payload={
                    "id": 157336,
                    "title": "Interstellar",
                    "overview": "Space exploration...",
                    "releaseDate": "2014-11-07",
                    "posterPath": "/test.jpg",
                    "mediaType": "movie",
                    "mediaInfo": {
                        "status": 5,
                        "status4k": 1,
                        "requests": [],
                    },
                    "cast": [],
                },
            )

            # Mock 4K request
            m.post(
                f"{overseerr_client.base_url}request",
                status=201,
                payload={
                    "id": 2,
                    "status": 2,
                    "type": "movie",
                    "is4k": True,
                },
            )

            # Search with 4K flag
            results = await overseerr_client.search_media("interstellar", is_4k=True)
            assert len(results) == 1

            # Get 4K details
            details = await overseerr_client.get_movie_by_id(157336, is_4k=True)
            assert details.available is False  # Not available in 4K

            # Request in 4K
            result = await overseerr_client.request_movie(157336, is_4k=True)
            assert result.success is True
