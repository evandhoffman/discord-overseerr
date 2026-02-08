"""Settings management with Pydantic"""

import json
import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OverseerrSettings(BaseModel):
    """Overseerr connection settings"""

    hostname: str = "localhost"
    port: int = 5055
    api_key: str = ""
    use_ssl: bool = False
    default_user_id: Optional[str] = None

    @property
    def base_url(self) -> str:
        """Construct base URL for Overseerr API"""
        protocol = "https" if self.use_ssl else "http"
        return f"{protocol}://{self.hostname}:{self.port}/api/v1/"


class MovieCategorySettings(BaseModel):
    """Movie category configuration (e.g., 1080p vs 4K)"""

    id: int
    name: str
    is_4k: bool = False
    service_id: int = -1  # Radarr service ID in Overseerr
    profile_id: int = -1
    root_folder: str = ""
    tags: List[int] = Field(default_factory=list)


class DiscordSettings(BaseModel):
    """Discord bot configuration"""

    bot_token: str = ""
    client_id: str = ""
    monitored_channels: List[int] = Field(default_factory=list)
    movie_roles: List[int] = Field(default_factory=list)
    authorized_users: List[int] = Field(default_factory=list)  # Discord user IDs allowed to use bot
    enable_dm_requests: bool = False
    auto_notify_requesters: bool = True
    notification_mode: str = "PrivateMessages"  # or "Channels"
    notification_channels: List[int] = Field(default_factory=list)


class BotSettings(BaseSettings):
    """Main bot settings with environment variable support"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    discord: DiscordSettings = Field(default_factory=DiscordSettings)
    overseerr: OverseerrSettings = Field(default_factory=OverseerrSettings)
    movie_categories: List[MovieCategorySettings] = Field(default_factory=list)
    version: str = "1.0.0"
    log_level: str = "INFO"

    # Environment variable overrides
    discord_bot_token: Optional[str] = Field(None, alias="DISCORD_BOT_TOKEN")
    discord_client_id: Optional[str] = Field(None, alias="DISCORD_CLIENT_ID")
    discord_authorized_users: Optional[str] = Field(None, alias="DISCORD_AUTHORIZED_USERS")
    overseerr_hostname: Optional[str] = Field(None, alias="OVERSEERR_HOSTNAME")
    overseerr_port: Optional[int] = Field(None, alias="OVERSEERR_PORT")
    overseerr_api_key: Optional[str] = Field(None, alias="OVERSEERR_API_KEY")
    overseerr_use_ssl: Optional[bool] = Field(None, alias="OVERSEERR_USE_SSL")

    def model_post_init(self, __context):
        """Apply environment variable overrides after initialization"""
        if self.discord_bot_token:
            self.discord.bot_token = self.discord_bot_token
        if self.discord_client_id:
            self.discord.client_id = self.discord_client_id
        if self.discord_authorized_users:
            # Parse comma-separated list of user IDs
            user_ids = [
                int(uid.strip())
                for uid in self.discord_authorized_users.split(",")
                if uid.strip()
            ]
            self.discord.authorized_users = user_ids
        if self.overseerr_hostname:
            self.overseerr.hostname = self.overseerr_hostname
        if self.overseerr_port:
            self.overseerr.port = self.overseerr_port
        if self.overseerr_api_key:
            self.overseerr.api_key = self.overseerr_api_key
        if self.overseerr_use_ssl is not None:
            self.overseerr.use_ssl = self.overseerr_use_ssl


class SettingsManager:
    """Manages bot settings with file persistence"""

    def __init__(self, config_path: str = "./config/settings.json"):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings: Optional[BotSettings] = None

    def load(self) -> BotSettings:
        """Load settings from file and environment variables"""
        # First load from environment variables
        self.settings = BotSettings()

        # Then merge with JSON file if it exists
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                data = json.load(f)

                # Update settings from file (env vars take precedence)
                if not self.settings.discord.bot_token and "discord" in data:
                    discord_data = data["discord"]
                    if "bot_token" in discord_data:
                        self.settings.discord.bot_token = discord_data["bot_token"]
                    if "client_id" in discord_data:
                        self.settings.discord.client_id = discord_data["client_id"]

                # Merge other settings
                if "movie_categories" in data:
                    self.settings.movie_categories = [
                        MovieCategorySettings(**cat) for cat in data["movie_categories"]
                    ]
        else:
            # Create default settings file
            self.save()

        return self.settings

    def save(self):
        """Save current settings to file"""
        if self.settings:
            # Don't save sensitive data to file
            data = {
                "version": self.settings.version,
                "discord": {
                    "monitored_channels": self.settings.discord.monitored_channels,
                    "movie_roles": self.settings.discord.movie_roles,
                    "authorized_users": self.settings.discord.authorized_users,
                    "enable_dm_requests": self.settings.discord.enable_dm_requests,
                    "auto_notify_requesters": self.settings.discord.auto_notify_requesters,
                    "notification_mode": self.settings.discord.notification_mode,
                    "notification_channels": self.settings.discord.notification_channels,
                },
                "overseerr": {
                    "hostname": self.settings.overseerr.hostname,
                    "port": self.settings.overseerr.port,
                    "use_ssl": self.settings.overseerr.use_ssl,
                },
                "movie_categories": [
                    cat.model_dump() for cat in self.settings.movie_categories
                ],
            }

            with open(self.config_path, "w") as f:
                json.dump(data, f, indent=2)

    def reload(self) -> BotSettings:
        """Reload settings from file"""
        return self.load()
