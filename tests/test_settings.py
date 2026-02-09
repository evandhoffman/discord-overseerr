"""Unit tests for settings management"""

import json
import os
from pathlib import Path

import pytest

from bot.settings import (
    BotSettings,
    DiscordSettings,
    OverseerrSettings,
    MovieCategorySettings,
    SettingsManager,
)


@pytest.mark.unit
class TestOverseerrSettings:
    """Test OverseerrSettings model"""

    def test_default_values(self):
        """Test default values are set correctly"""
        settings = OverseerrSettings()
        assert settings.hostname == "localhost"
        assert settings.port == 5055
        assert settings.api_key == ""
        assert settings.use_ssl is False
        assert settings.default_user_id is None

    def test_custom_values(self):
        """Test custom values are set correctly"""
        settings = OverseerrSettings(
            hostname="overseerr.example.com",
            port=443,
            api_key="test_key",
            use_ssl=True,
            default_user_id="123",
        )
        assert settings.hostname == "overseerr.example.com"
        assert settings.port == 443
        assert settings.api_key == "test_key"
        assert settings.use_ssl is True
        assert settings.default_user_id == "123"

    def test_base_url_http(self):
        """Test base_url property with HTTP"""
        settings = OverseerrSettings(hostname="localhost", port=5055, use_ssl=False)
        assert settings.base_url == "http://localhost:5055/api/v1/"

    def test_base_url_https(self):
        """Test base_url property with HTTPS"""
        settings = OverseerrSettings(hostname="overseerr.example.com", port=443, use_ssl=True)
        assert settings.base_url == "https://overseerr.example.com:443/api/v1/"


@pytest.mark.unit
class TestDiscordSettings:
    """Test DiscordSettings model"""

    def test_default_values(self):
        """Test default values are set correctly"""
        settings = DiscordSettings()
        assert settings.bot_token == ""
        assert settings.client_id == ""
        assert settings.monitored_channels == []
        assert settings.movie_roles == []
        assert settings.authorized_users == []
        assert settings.enable_dm_requests is False
        assert settings.auto_notify_requesters is True
        assert settings.notification_mode == "PrivateMessages"
        assert settings.notification_channels == []
        assert settings.notification_check_interval == 5

    def test_custom_values(self):
        """Test custom values are set correctly"""
        settings = DiscordSettings(
            bot_token="test_token",
            client_id="123",
            monitored_channels=[111, 222],
            movie_roles=[333],
            authorized_users=[444, 555],
            enable_dm_requests=True,
            notification_check_interval=10,
        )
        assert settings.bot_token == "test_token"
        assert settings.client_id == "123"
        assert settings.monitored_channels == [111, 222]
        assert settings.movie_roles == [333]
        assert settings.authorized_users == [444, 555]
        assert settings.enable_dm_requests is True
        assert settings.notification_check_interval == 10


@pytest.mark.unit
class TestMovieCategorySettings:
    """Test MovieCategorySettings model"""

    def test_default_values(self):
        """Test default values are set correctly"""
        settings = MovieCategorySettings(id=1, name="1080p")
        assert settings.id == 1
        assert settings.name == "1080p"
        assert settings.is_4k is False
        assert settings.service_id == -1
        assert settings.profile_id == -1
        assert settings.root_folder == ""
        assert settings.tags == []

    def test_4k_category(self):
        """Test 4K category settings"""
        settings = MovieCategorySettings(
            id=2,
            name="4K",
            is_4k=True,
            service_id=2,
            profile_id=5,
            root_folder="/movies4k",
            tags=[1, 2],
        )
        assert settings.is_4k is True
        assert settings.service_id == 2
        assert settings.profile_id == 5
        assert settings.root_folder == "/movies4k"
        assert settings.tags == [1, 2]


@pytest.mark.unit
class TestBotSettings:
    """Test BotSettings model with environment variables"""

    def test_default_values(self):
        """Test default values without environment variables"""
        settings = BotSettings()
        assert settings.version == "1.0.0"
        assert settings.log_level == "INFO"
        assert isinstance(settings.discord, DiscordSettings)
        assert isinstance(settings.overseerr, OverseerrSettings)
        assert settings.movie_categories == []

    def test_env_var_overrides(self, mock_env_vars):
        """Test environment variable overrides"""
        settings = BotSettings()

        # Check that env vars override defaults
        assert settings.discord.bot_token == "test_bot_token_12345"
        assert settings.discord.client_id == "123456789"
        assert settings.overseerr.hostname == "test.overseerr.local"
        assert settings.overseerr.port == 5055
        assert settings.overseerr.api_key == "test_api_key_abcdef"
        assert settings.overseerr.use_ssl is False

    def test_authorized_users_parsing(self, monkeypatch):
        """Test parsing comma-separated authorized users"""
        monkeypatch.setenv("DISCORD_AUTHORIZED_USERS", "111,222,333")
        settings = BotSettings()
        assert settings.discord.authorized_users == [111, 222, 333]

    def test_authorized_users_with_spaces(self, monkeypatch):
        """Test parsing authorized users with spaces"""
        monkeypatch.setenv("DISCORD_AUTHORIZED_USERS", "111, 222 , 333")
        settings = BotSettings()
        assert settings.discord.authorized_users == [111, 222, 333]

    def test_empty_authorized_users(self, monkeypatch):
        """Test empty authorized users string"""
        monkeypatch.setenv("DISCORD_AUTHORIZED_USERS", "")
        settings = BotSettings()
        assert settings.discord.authorized_users == []

    def test_notification_interval_override(self, monkeypatch):
        """Test notification check interval override"""
        monkeypatch.setenv("NOTIFICATION_CHECK_INTERVAL", "10")
        settings = BotSettings()
        assert settings.discord.notification_check_interval == 10


@pytest.mark.unit
class TestSettingsManager:
    """Test SettingsManager"""

    def test_create_settings_manager(self, temp_settings_file):
        """Test creating a SettingsManager instance"""
        manager = SettingsManager(config_path=str(temp_settings_file))
        assert manager.config_path == temp_settings_file
        assert manager.settings is None

    def test_load_from_file(self, temp_settings_file):
        """Test loading settings from file"""
        manager = SettingsManager(config_path=str(temp_settings_file))
        settings = manager.load()

        assert isinstance(settings, BotSettings)
        # Movie categories are loaded from file
        assert len(settings.movie_categories) == 1
        assert settings.movie_categories[0].name == "1080p"
        # Discord settings like monitored_channels are NOT loaded from file
        # (they come from env vars only in current implementation)
        # This is by design - only bot_token, client_id, and movie_categories
        # are loaded from file

    def test_load_with_env_override(self, temp_settings_file, monkeypatch):
        """Test that environment variables override file settings"""
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "env_token")
        monkeypatch.setenv("OVERSEERR_HOSTNAME", "env.host.com")

        manager = SettingsManager(config_path=str(temp_settings_file))
        settings = manager.load()

        # Env vars should take precedence
        assert settings.discord.bot_token == "env_token"
        assert settings.overseerr.hostname == "env.host.com"

    def test_save_settings(self, temp_config_dir):
        """Test saving settings to file"""
        settings_file = temp_config_dir / "new_settings.json"
        manager = SettingsManager(config_path=str(settings_file))

        # Load settings (will create file)
        settings = manager.load()
        settings.discord.monitored_channels = [111, 222]
        settings.discord.authorized_users = [333, 444]
        manager.settings = settings

        # Save settings
        manager.save()

        # Verify file was created and contains data
        assert settings_file.exists()

        with open(settings_file, "r") as f:
            data = json.load(f)

        assert data["discord"]["monitored_channels"] == [111, 222]
        assert data["discord"]["authorized_users"] == [333, 444]

    def test_reload_settings(self, temp_settings_file):
        """Test reloading settings from file"""
        manager = SettingsManager(config_path=str(temp_settings_file))

        # Load initial settings
        settings1 = manager.load()
        assert len(settings1.movie_categories) == 1

        # Modify the file
        with open(temp_settings_file, "r") as f:
            data = json.load(f)
        data["movie_categories"][0]["name"] = "4K"
        with open(temp_settings_file, "w") as f:
            json.dump(data, f)

        # Reload settings
        settings2 = manager.reload()
        assert settings2.movie_categories[0].name == "4K"

    def test_create_default_file(self, temp_config_dir):
        """Test creating default settings file when none exists"""
        settings_file = temp_config_dir / "default_settings.json"
        manager = SettingsManager(config_path=str(settings_file))

        # Load will create default file
        settings = manager.load()

        # File should now exist
        assert settings_file.exists()

    def test_sensitive_data_not_saved(self, temp_config_dir):
        """Test that sensitive data (tokens, API keys) are not saved to file"""
        settings_file = temp_config_dir / "secure_settings.json"
        manager = SettingsManager(config_path=str(settings_file))

        settings = manager.load()
        manager.settings = settings
        manager.save()

        with open(settings_file, "r") as f:
            data = json.load(f)

        # Bot token and API key should not be in the file
        assert "bot_token" not in data.get("discord", {})
        assert "api_key" not in data.get("overseerr", {})
