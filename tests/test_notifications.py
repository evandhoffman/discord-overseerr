"""Unit tests for notification manager"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.notifications import NotificationManager, PendingRequest
from bot.overseerr import MediaStatus


@pytest.mark.unit
class TestPendingRequest:
    """Test PendingRequest model"""

    def test_pending_request_creation(self):
        """Test creating a PendingRequest"""
        request = PendingRequest(
            user_id=111,
            username="TestUser",
            tmdb_id=550,
            title="Fight Club",
            timestamp="2026-02-01T12:00:00",
            is_4k=False,
            last_status=MediaStatus.PENDING,
        )

        assert request.user_id == 111
        assert request.username == "TestUser"
        assert request.tmdb_id == 550
        assert request.title == "Fight Club"
        assert request.is_4k is False
        assert request.last_status == MediaStatus.PENDING

    def test_pending_request_to_dict(self):
        """Test converting PendingRequest to dictionary"""
        request = PendingRequest(
            user_id=111,
            username="TestUser",
            tmdb_id=550,
            title="Fight Club",
            timestamp="2026-02-01T12:00:00",
            is_4k=False,
            last_status=MediaStatus.PENDING,
        )

        data = request.to_dict()

        assert data["user_id"] == 111
        assert data["username"] == "TestUser"
        assert data["tmdb_id"] == 550
        assert data["title"] == "Fight Club"
        assert data["is_4k"] is False
        assert data["last_status"] == 2

    def test_pending_request_from_dict(self):
        """Test creating PendingRequest from dictionary"""
        data = {
            "user_id": 111,
            "username": "TestUser",
            "tmdb_id": 550,
            "title": "Fight Club",
            "timestamp": "2026-02-01T12:00:00",
            "is_4k": False,
            "last_status": 2,
        }

        request = PendingRequest.from_dict(data)

        assert request.user_id == 111
        assert request.username == "TestUser"
        assert request.tmdb_id == 550
        assert request.title == "Fight Club"
        assert request.is_4k is False
        assert request.last_status == MediaStatus.PENDING

    def test_pending_request_4k(self):
        """Test creating a 4K pending request"""
        request = PendingRequest(
            user_id=111,
            username="TestUser",
            tmdb_id=550,
            title="Fight Club",
            timestamp="2026-02-01T12:00:00",
            is_4k=True,
            last_status=MediaStatus.PENDING,
        )

        assert request.is_4k is True

    def test_get_elapsed_time_minutes(self):
        """Test elapsed time in minutes"""
        # 30 minutes ago
        timestamp = (datetime.now() - timedelta(minutes=30)).isoformat()
        request = PendingRequest(
            user_id=111,
            username="TestUser",
            tmdb_id=550,
            title="Fight Club",
            timestamp=timestamp,
            is_4k=False,
        )

        elapsed = request.get_elapsed_time()
        assert "minute" in elapsed

    def test_get_elapsed_time_hours(self):
        """Test elapsed time in hours"""
        # 3 hours ago
        timestamp = (datetime.now() - timedelta(hours=3)).isoformat()
        request = PendingRequest(
            user_id=111,
            username="TestUser",
            tmdb_id=550,
            title="Fight Club",
            timestamp=timestamp,
            is_4k=False,
        )

        elapsed = request.get_elapsed_time()
        assert "hour" in elapsed

    def test_get_elapsed_time_days(self):
        """Test elapsed time in days"""
        # 2 days ago
        timestamp = (datetime.now() - timedelta(days=2)).isoformat()
        request = PendingRequest(
            user_id=111,
            username="TestUser",
            tmdb_id=550,
            title="Fight Club",
            timestamp=timestamp,
            is_4k=False,
        )

        elapsed = request.get_elapsed_time()
        assert "day" in elapsed

    def test_get_elapsed_time_singular(self):
        """Test elapsed time with singular units"""
        # 1 hour and 1 minute ago
        timestamp = (datetime.now() - timedelta(hours=1, minutes=1)).isoformat()
        request = PendingRequest(
            user_id=111,
            username="TestUser",
            tmdb_id=550,
            title="Fight Club",
            timestamp=timestamp,
            is_4k=False,
        )

        elapsed = request.get_elapsed_time()
        # Should use singular 'hour' not 'hours'
        assert "1 hour" in elapsed


@pytest.mark.unit
class TestNotificationManager:
    """Test NotificationManager"""

    def test_notification_manager_creation(self, mock_discord_bot, temp_config_dir):
        """Test creating a NotificationManager"""
        notifications_file = temp_config_dir / "notifications.json"
        manager = NotificationManager(
            bot=mock_discord_bot,
            notifications_file=str(notifications_file),
        )

        assert manager.bot == mock_discord_bot
        assert manager.notifications_file == notifications_file
        assert manager.pending_requests == {}

    def test_load_notifications_empty(self, mock_discord_bot, temp_config_dir):
        """Test loading notifications when file doesn't exist"""
        notifications_file = temp_config_dir / "notifications.json"
        manager = NotificationManager(
            bot=mock_discord_bot,
            notifications_file=str(notifications_file),
        )

        assert manager.pending_requests == {}

    def test_load_notifications_from_file(self, mock_discord_bot, mock_notification_file):
        """Test loading notifications from existing file"""
        manager = NotificationManager(
            bot=mock_discord_bot,
            notifications_file=str(mock_notification_file),
        )

        assert len(manager.pending_requests) == 1
        assert "111:550" in manager.pending_requests

        request = manager.pending_requests["111:550"]
        assert request.user_id == 111
        assert request.tmdb_id == 550
        assert request.title == "Fight Club"

    def test_load_notifications_invalid_file(self, mock_discord_bot, temp_config_dir):
        """Test loading notifications with invalid JSON file"""
        notifications_file = temp_config_dir / "invalid.json"

        # Write invalid JSON
        with open(notifications_file, "w") as f:
            f.write("invalid json content {")

        manager = NotificationManager(
            bot=mock_discord_bot,
            notifications_file=str(notifications_file),
        )

        # Should gracefully handle error and return empty dict
        assert manager.pending_requests == {}

    def test_save_notifications(self, mock_discord_bot, temp_config_dir):
        """Test saving notifications to file"""
        notifications_file = temp_config_dir / "notifications.json"
        manager = NotificationManager(
            bot=mock_discord_bot,
            notifications_file=str(notifications_file),
        )

        # Add a request
        manager.add_request(
            user_id=111,
            username="TestUser",
            tmdb_id=550,
            title="Fight Club",
            is_4k=False,
        )

        # File should be created
        assert notifications_file.exists()

        # Read and verify file content
        with open(notifications_file, "r") as f:
            data = json.load(f)

        assert "111:550" in data
        assert data["111:550"]["user_id"] == 111
        assert data["111:550"]["tmdb_id"] == 550

    def test_add_request(self, mock_discord_bot, temp_config_dir):
        """Test adding a request for tracking"""
        notifications_file = temp_config_dir / "notifications.json"
        manager = NotificationManager(
            bot=mock_discord_bot,
            notifications_file=str(notifications_file),
        )

        manager.add_request(
            user_id=111,
            username="TestUser",
            tmdb_id=550,
            title="Fight Club",
            is_4k=False,
        )

        assert len(manager.pending_requests) == 1
        assert "111:550" in manager.pending_requests

        request = manager.pending_requests["111:550"]
        assert request.user_id == 111
        assert request.username == "TestUser"
        assert request.tmdb_id == 550
        assert request.title == "Fight Club"
        assert request.is_4k is False

    def test_add_request_4k(self, mock_discord_bot, temp_config_dir):
        """Test adding a 4K request"""
        notifications_file = temp_config_dir / "notifications.json"
        manager = NotificationManager(
            bot=mock_discord_bot,
            notifications_file=str(notifications_file),
        )

        manager.add_request(
            user_id=111,
            username="TestUser",
            tmdb_id=550,
            title="Fight Club",
            is_4k=True,
        )

        # 4K requests have different key
        assert "111:550_4k" in manager.pending_requests

    def test_add_request_duplicate(self, mock_discord_bot, temp_config_dir):
        """Test adding duplicate request doesn't create duplicates"""
        notifications_file = temp_config_dir / "notifications.json"
        manager = NotificationManager(
            bot=mock_discord_bot,
            notifications_file=str(notifications_file),
        )

        # Add same request twice
        manager.add_request(
            user_id=111,
            username="TestUser",
            tmdb_id=550,
            title="Fight Club",
            is_4k=False,
        )
        manager.add_request(
            user_id=111,
            username="TestUser",
            tmdb_id=550,
            title="Fight Club",
            is_4k=False,
        )

        # Should only have one request
        assert len(manager.pending_requests) == 1

    def test_add_request_different_users(self, mock_discord_bot, temp_config_dir):
        """Test adding requests from different users for same movie"""
        notifications_file = temp_config_dir / "notifications.json"
        manager = NotificationManager(
            bot=mock_discord_bot,
            notifications_file=str(notifications_file),
        )

        # Add requests from two different users for same movie
        manager.add_request(111, "User1", 550, "Fight Club", False)
        manager.add_request(222, "User2", 550, "Fight Club", False)

        # Should have two separate requests
        assert len(manager.pending_requests) == 2
        assert "111:550" in manager.pending_requests
        assert "222:550" in manager.pending_requests

    def test_notification_check_interval(self, mock_discord_bot, temp_config_dir):
        """Test that notification check interval is configured from settings"""
        mock_discord_bot.settings.discord.notification_check_interval = 10

        notifications_file = temp_config_dir / "notifications.json"
        manager = NotificationManager(
            bot=mock_discord_bot,
            notifications_file=str(notifications_file),
        )

        # Verify interval was set (task should exist)
        assert manager.check_availability is not None

    @pytest.mark.asyncio
    async def test_check_availability_task(self, mock_discord_bot, temp_config_dir, sample_movie):
        """Test the availability checking background task"""
        notifications_file = temp_config_dir / "notifications.json"

        # Mock overseerr client
        mock_overseerr = AsyncMock()
        mock_overseerr.get_movie_by_id = AsyncMock(return_value=sample_movie)
        mock_discord_bot.overseerr = mock_overseerr

        # Mock fetch_user method (async)
        mock_user = MagicMock()
        mock_user.id = 111
        mock_user.name = "TestUser"
        mock_user.send = AsyncMock()
        mock_discord_bot.fetch_user = AsyncMock(return_value=mock_user)

        manager = NotificationManager(
            bot=mock_discord_bot,
            notifications_file=str(notifications_file),
        )

        # Add a pending request with PENDING status
        request = PendingRequest(
            user_id=111,
            username="TestUser",
            tmdb_id=550,
            title="Fight Club",
            timestamp=datetime.now().isoformat(),
            is_4k=False,
            last_status=MediaStatus.PENDING,
        )
        manager.pending_requests["111:550"] = request

        # Set movie to available
        sample_movie.status = MediaStatus.AVAILABLE
        sample_movie.available = True

        # Run the check manually
        await manager._check_and_notify()

        # User should have been notified
        assert mock_user.send.called

        # Request should be removed from pending
        assert "111:550" not in manager.pending_requests

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, mock_discord_bot, temp_config_dir):
        """Test starting and stopping the monitoring task"""
        notifications_file = temp_config_dir / "notifications.json"
        manager = NotificationManager(
            bot=mock_discord_bot,
            notifications_file=str(notifications_file),
        )

        # Start monitoring
        manager.start_monitoring()
        assert manager.check_availability.is_running()

        # Stop monitoring
        manager.stop_monitoring()
        # Give it a moment to stop
        import asyncio

        await asyncio.sleep(0.1)
        assert not manager.check_availability.is_running()

    def test_save_creates_directory(self, mock_discord_bot, temp_config_dir):
        """Test that save creates parent directory if it doesn't exist"""
        notifications_file = temp_config_dir / "subdir" / "notifications.json"
        manager = NotificationManager(
            bot=mock_discord_bot,
            notifications_file=str(notifications_file),
        )

        manager.add_request(111, "TestUser", 550, "Fight Club", False)

        # Directory should be created
        assert notifications_file.parent.exists()
        assert notifications_file.exists()
