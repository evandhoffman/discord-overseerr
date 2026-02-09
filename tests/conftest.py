"""Pytest configuration and shared fixtures for Discord Overseerr Bot tests"""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from aioresponses import aioresponses

from bot.settings import (
    BotSettings,
    DiscordSettings,
    OverseerrSettings,
    MovieCategorySettings,
    SettingsManager,
)
from bot.overseerr import OverseerrClient, Movie, TVShow, MediaStatus


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing"""
    env_vars = {
        "DISCORD_BOT_TOKEN": "test_bot_token_12345",
        "DISCORD_CLIENT_ID": "123456789",
        "OVERSEERR_HOSTNAME": "test.overseerr.local",
        "OVERSEERR_PORT": "5055",
        "OVERSEERR_API_KEY": "test_api_key_abcdef",
        "OVERSEERR_USE_SSL": "false",
        "DISCORD_AUTHORIZED_USERS": "111111111,222222222,333333333",
        "LOG_LEVEL": "DEBUG",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_settings_file(temp_config_dir):
    """Create a temporary settings.json file"""
    settings_file = temp_config_dir / "settings.json"
    settings_data = {
        "version": "1.0.0",
        "discord": {
            "monitored_channels": [123456789],
            "movie_roles": [987654321],
            "authorized_users": [],
            "enable_dm_requests": True,
            "auto_notify_requesters": True,
            "notification_mode": "PrivateMessages",
            "notification_channels": [],
        },
        "overseerr": {
            "hostname": "localhost",
            "port": 5055,
            "use_ssl": False,
        },
        "movie_categories": [
            {
                "id": 1,
                "name": "1080p",
                "is_4k": False,
                "service_id": 1,
                "profile_id": 1,
                "root_folder": "/movies",
                "tags": [],
            }
        ],
    }

    with open(settings_file, "w") as f:
        json.dump(settings_data, f, indent=2)

    return settings_file


@pytest.fixture
def bot_settings(mock_env_vars):
    """Create a BotSettings instance with test data"""
    settings = BotSettings()
    return settings


@pytest.fixture
def settings_manager(temp_settings_file):
    """Create a SettingsManager instance with temp file"""
    return SettingsManager(config_path=str(temp_settings_file))


@pytest.fixture
def discord_settings():
    """Create a DiscordSettings instance"""
    return DiscordSettings(
        bot_token="test_token",
        client_id="123456",
        monitored_channels=[111, 222],
        movie_roles=[333],
        authorized_users=[444, 555],
        enable_dm_requests=True,
        auto_notify_requesters=True,
        notification_mode="PrivateMessages",
        notification_channels=[],
        notification_check_interval=5,
    )


@pytest.fixture
def overseerr_settings():
    """Create an OverseerrSettings instance"""
    return OverseerrSettings(
        hostname="test.overseerr.local",
        port=5055,
        api_key="test_api_key",
        use_ssl=False,
        default_user_id="1",
    )


@pytest.fixture
async def overseerr_client(overseerr_settings):
    """Create an OverseerrClient instance"""
    client = OverseerrClient(
        hostname=overseerr_settings.hostname,
        port=overseerr_settings.port,
        api_key=overseerr_settings.api_key,
        use_ssl=overseerr_settings.use_ssl,
    )
    yield client
    await client.close()


@pytest.fixture
def mock_aiohttp():
    """Mock aiohttp responses"""
    with aioresponses() as m:
        yield m


@pytest.fixture
def sample_movie_data():
    """Sample movie data from Overseerr API"""
    return {
        "id": 550,
        "title": "Fight Club",
        "overview": "A ticking-time-bomb insomniac and a slippery soap salesman...",
        "releaseDate": "1999-10-15",
        "posterPath": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
        "mediaType": "movie",
        "popularity": 67.634,
        "mediaInfo": {
            "status": 5,  # AVAILABLE
            "status4k": 1,  # UNKNOWN
        },
    }


@pytest.fixture
def sample_tv_data():
    """Sample TV show data from Overseerr API"""
    return {
        "id": 1396,
        "name": "Breaking Bad",
        "overview": "A high school chemistry teacher diagnosed with cancer...",
        "firstAirDate": "2008-01-20",
        "posterPath": "/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
        "mediaType": "tv",
        "popularity": 456.789,
        "mediaInfo": {
            "status": 2,  # PENDING
            "status4k": 1,  # UNKNOWN
        },
    }


@pytest.fixture
def sample_movie():
    """Create a sample Movie object"""
    return Movie(
        tmdb_id=550,
        title="Fight Club",
        overview="A ticking-time-bomb insomniac...",
        release_date="1999-10-15",
        poster_path="/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
        available=True,
        requested=False,
        status=MediaStatus.AVAILABLE,
        popularity=67.634,
        cast=["Brad Pitt", "Edward Norton", "Helena Bonham Carter"],
    )


@pytest.fixture
def sample_tv_show():
    """Create a sample TVShow object"""
    return TVShow(
        tmdb_id=1396,
        name="Breaking Bad",
        overview="A high school chemistry teacher...",
        first_air_date="2008-01-20",
        poster_path="/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
        available=False,
        requested=True,
        status=MediaStatus.PENDING,
        popularity=456.789,
        cast=["Bryan Cranston", "Aaron Paul", "Anna Gunn"],
    )


@pytest.fixture
def mock_discord_bot():
    """Create a mock Discord bot"""
    bot = MagicMock()
    bot.user = MagicMock()
    bot.user.id = 123456789
    bot.user.name = "TestBot"
    bot.guilds = []
    bot.latency = 0.05

    # Mock settings
    bot.settings = BotSettings()
    bot.settings.discord.bot_token = "test_token"
    bot.settings.overseerr.api_key = "test_api_key"
    bot.settings.discord.authorized_users = [111, 222, 333]
    bot.settings.discord.notification_check_interval = 5

    return bot


@pytest.fixture
def mock_discord_interaction():
    """Create a mock Discord interaction"""
    interaction = AsyncMock()
    interaction.user = MagicMock()
    interaction.user.id = 111
    interaction.user.name = "TestUser"
    interaction.user.mention = "@TestUser"
    interaction.guild = MagicMock()
    interaction.guild.id = 999
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.edit_original_response = AsyncMock()

    return interaction


@pytest.fixture
def mock_notification_file(temp_config_dir):
    """Create a temporary notifications.json file"""
    notifications_file = temp_config_dir / "notifications.json"
    notifications_data = {
        "111:550": {
            "user_id": 111,
            "username": "TestUser",
            "tmdb_id": 550,
            "title": "Fight Club",
            "timestamp": "2026-02-01T12:00:00",
            "is_4k": False,
            "last_status": 2,
        }
    }

    with open(notifications_file, "w") as f:
        json.dump(notifications_data, f, indent=2)

    return notifications_file


@pytest.fixture
def overseerr_search_response():
    """Sample search response from Overseerr API"""
    return {
        "page": 1,
        "totalPages": 1,
        "totalResults": 2,
        "results": [
            {
                "id": 550,
                "title": "Fight Club",
                "overview": "A ticking-time-bomb insomniac...",
                "releaseDate": "1999-10-15",
                "posterPath": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
                "mediaType": "movie",
                "popularity": 67.634,
                "mediaInfo": {
                    "status": 5,
                    "status4k": 1,
                },
            },
            {
                "id": 1396,
                "name": "Breaking Bad",
                "overview": "A high school chemistry teacher...",
                "firstAirDate": "2008-01-20",
                "posterPath": "/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
                "mediaType": "tv",
                "popularity": 456.789,
                "mediaInfo": {
                    "status": 2,
                    "status4k": 1,
                },
            },
        ],
    }


@pytest.fixture
def overseerr_movie_details_response():
    """Sample movie details response from Overseerr API"""
    return {
        "id": 550,
        "title": "Fight Club",
        "overview": "A ticking-time-bomb insomniac...",
        "releaseDate": "1999-10-15",
        "posterPath": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
        "mediaType": "movie",
        "popularity": 67.634,
        "mediaInfo": {
            "status": 5,
            "status4k": 1,
            "requests": [],
        },
        "cast": [
            {"name": "Brad Pitt"},
            {"name": "Edward Norton"},
            {"name": "Helena Bonham Carter"},
        ],
    }


@pytest.fixture
def overseerr_request_success_response():
    """Sample successful request response from Overseerr API"""
    return {
        "id": 1,
        "status": 2,  # PENDING
        "createdAt": "2026-02-08T12:00:00.000Z",
        "updatedAt": "2026-02-08T12:00:00.000Z",
        "type": "movie",
        "is4k": False,
        "media": {
            "tmdbId": 550,
            "status": 2,
        },
    }


# Helper functions for tests
def create_mock_response(status: int = 200, payload: Dict[str, Any] = None):
    """Create a mock HTTP response"""
    mock_response = AsyncMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=payload or {})
    mock_response.text = AsyncMock(return_value=json.dumps(payload or {}))
    return mock_response
