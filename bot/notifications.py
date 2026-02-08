"""Notification system for tracking and notifying users about completed requests"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import discord
from discord.ext import tasks

from bot.overseerr import MediaStatus

logger = logging.getLogger(__name__)


class PendingRequest:
    """Represents a pending media request"""

    def __init__(
        self,
        user_id: int,
        username: str,
        tmdb_id: int,
        title: str,
        timestamp: str,
        is_4k: bool = False,
    ):
        self.user_id = user_id
        self.username = username
        self.tmdb_id = tmdb_id
        self.title = title
        self.timestamp = timestamp
        self.is_4k = is_4k

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "tmdb_id": self.tmdb_id,
            "title": self.title,
            "timestamp": self.timestamp,
            "is_4k": self.is_4k,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            tmdb_id=data["tmdb_id"],
            title=data["title"],
            timestamp=data["timestamp"],
            is_4k=data.get("is_4k", False),
        )

    def get_elapsed_time(self) -> str:
        """Calculate elapsed time since request"""
        request_time = datetime.fromisoformat(self.timestamp)
        now = datetime.now()
        elapsed = now - request_time

        days = elapsed.days
        hours = elapsed.seconds // 3600
        minutes = (elapsed.seconds % 3600) // 60

        if days > 0:
            if days == 1:
                return f"{days} day, {hours} hours"
            return f"{days} days, {hours} hours"
        elif hours > 0:
            if hours == 1:
                return f"{hours} hour, {minutes} minutes"
            return f"{hours} hours, {minutes} minutes"
        else:
            if minutes == 1:
                return f"{minutes} minute"
            return f"{minutes} minutes"


class NotificationManager:
    """Manages user notifications for completed requests"""

    def __init__(self, bot, notifications_file: str = "./config/notifications.json"):
        self.bot = bot
        self.notifications_file = Path(notifications_file)
        self.pending_requests: Dict[str, PendingRequest] = {}
        self.load_notifications()

    def load_notifications(self):
        """Load pending notifications from file"""
        if self.notifications_file.exists():
            try:
                with open(self.notifications_file, "r") as f:
                    data = json.load(f)
                    self.pending_requests = {
                        key: PendingRequest.from_dict(req) for key, req in data.items()
                    }
                logger.info(f"Loaded {len(self.pending_requests)} pending notification(s)")
            except Exception as e:
                logger.error(f"Error loading notifications: {e}")
                self.pending_requests = {}
        else:
            self.pending_requests = {}

    def save_notifications(self):
        """Save pending notifications to file"""
        try:
            # Ensure directory exists
            self.notifications_file.parent.mkdir(parents=True, exist_ok=True)

            data = {key: req.to_dict() for key, req in self.pending_requests.items()}
            with open(self.notifications_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving notifications: {e}")

    def add_request(
        self, user_id: int, username: str, tmdb_id: int, title: str, is_4k: bool = False
    ):
        """Add a request to be tracked for notifications"""
        key = f"{user_id}:{tmdb_id}{'_4k' if is_4k else ''}"

        # Don't add if already tracking
        if key in self.pending_requests:
            logger.info(f"Request already tracked: {key}")
            return

        request = PendingRequest(
            user_id=user_id,
            username=username,
            tmdb_id=tmdb_id,
            title=title,
            timestamp=datetime.now().isoformat(),
            is_4k=is_4k,
        )

        self.pending_requests[key] = request
        self.save_notifications()
        logger.info(f"✅ Added notification tracking for {username}: {title}")

    async def check_pending_on_startup(self):
        """Check all pending requests immediately on startup"""
        if not self.pending_requests:
            logger.info("No pending notifications to check on startup")
            return

        logger.info(
            f"🔍 Checking {len(self.pending_requests)} pending request(s) from saved state on startup"
        )
        await self._check_and_notify()

    def start_monitoring(self):
        """Start the background task to monitor requests"""
        if not self.check_availability.is_running():
            self.check_availability.start()
            logger.info("Started notification monitoring task")

    def stop_monitoring(self):
        """Stop the background task"""
        if self.check_availability.is_running():
            self.check_availability.cancel()
            logger.info("Stopped notification monitoring task")

    async def _check_and_notify(self):
        """Core logic to check availability and notify users"""
        completed_keys = []

        for key, request in list(self.pending_requests.items()):
            try:
                # Check movie status in Overseerr
                movie = await self.bot.overseerr.get_movie_by_id(
                    request.tmdb_id, is_4k=request.is_4k
                )

                if movie.available:
                    # Content is now available - notify user
                    await self.notify_user(request)
                    completed_keys.append(key)
                else:
                    logger.debug(
                        f"Request still pending: {request.title} for {request.username} "
                        f"(Status: {movie.status.name})"
                    )

            except Exception as e:
                logger.error(f"Error checking availability for {request.title}: {e}")

        # Remove completed requests
        for key in completed_keys:
            del self.pending_requests[key]

        if completed_keys:
            self.save_notifications()
            logger.info(f"✅ Notified {len(completed_keys)} user(s) of completed requests")

        return len(completed_keys)

    @tasks.loop(minutes=10)
    async def check_availability(self):
        """Periodically check if requested content is now available"""
        if not self.pending_requests:
            return

        logger.info(f"Checking availability for {len(self.pending_requests)} pending request(s)")
        await self._check_and_notify()

    async def notify_user(self, request: PendingRequest):
        """Send notification to user that their request is complete"""
        try:
            user = await self.bot.fetch_user(request.user_id)
            elapsed_time = request.get_elapsed_time()

            embed = discord.Embed(
                title="🎬 Content Available!",
                description=f"The content you requested is now ready to watch!",
                color=discord.Color.green(),
            )

            embed.add_field(name="Title", value=request.title, inline=False)

            if request.is_4k:
                embed.add_field(name="Quality", value="4K UHD", inline=True)

            embed.add_field(name="Request Completed In", value=elapsed_time, inline=True)

            embed.set_footer(text="Enjoy your movie! 🍿")

            await user.send(embed=embed)
            logger.info(
                f"✅ Notified {request.username} that {request.title} is available "
                f"(completed in {elapsed_time})"
            )

        except discord.Forbidden:
            logger.warning(
                f"⚠️  Cannot send DM to {request.username} (user has DMs disabled or blocked bot)"
            )
        except Exception as e:
            logger.error(f"❌ Error notifying user {request.username}: {e}")

    @check_availability.before_loop
    async def before_check_availability(self):
        """Wait for bot to be ready before starting checks"""
        await self.bot.wait_until_ready()
        logger.info("Notification manager ready - starting availability checks")
