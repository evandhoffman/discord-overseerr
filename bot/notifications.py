"""Notification system for tracking and notifying users about completed requests"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import discord
from discord.ext import tasks

from bot.overseerr import MediaStatus

if TYPE_CHECKING:
    from bot.main import MovieBot

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
        last_status: int = MediaStatus.UNKNOWN,
    ) -> None:
        self.user_id = user_id
        self.username = username
        self.tmdb_id = tmdb_id
        self.title = title
        self.timestamp = timestamp
        self.is_4k = is_4k
        self.last_status = MediaStatus(last_status) if isinstance(last_status, int) else last_status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "tmdb_id": self.tmdb_id,
            "title": self.title,
            "timestamp": self.timestamp,
            "is_4k": self.is_4k,
            "last_status": int(self.last_status),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PendingRequest":
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            tmdb_id=data["tmdb_id"],
            title=data["title"],
            timestamp=data["timestamp"],
            is_4k=data.get("is_4k", False),
            last_status=data.get("last_status", MediaStatus.UNKNOWN),
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

    def __init__(
        self, bot: "MovieBot", notifications_file: str = "./config/notifications.json"
    ) -> None:
        self.bot = bot
        self.notifications_file = Path(notifications_file)
        self.pending_requests: Dict[str, PendingRequest] = {}
        self.load_notifications()

        # Configure check interval from settings
        check_interval = bot.settings.discord.notification_check_interval
        self.check_availability.change_interval(minutes=check_interval)
        logger.info(f"Notification check interval set to {check_interval} minute(s)")

    def load_notifications(self) -> None:
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

    def save_notifications(self) -> None:
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
    ) -> None:
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

    async def check_pending_on_startup(self) -> None:
        """Check all pending requests immediately on startup"""
        if not self.pending_requests:
            logger.info("No pending notifications to check on startup")
            return

        logger.info(
            f"🔍 Checking {len(self.pending_requests)} pending request(s) from saved state on startup"
        )
        await self._check_and_notify()

    def start_monitoring(self) -> None:
        """Start the background task to monitor requests"""
        if not self.check_availability.is_running():
            self.check_availability.start()
            logger.info("Started notification monitoring task")

    def stop_monitoring(self) -> None:
        """Stop the background task"""
        if self.check_availability.is_running():
            self.check_availability.cancel()
            logger.info("Stopped notification monitoring task")

    async def _check_and_notify(self) -> int:
        """Core logic to check availability and notify users"""
        completed_keys: List[str] = []

        logger.info(
            f"━━━━━━━━━━ Checking {len(self.pending_requests)} Pending Request(s) ━━━━━━━━━━"
        )

        for key, request in list(self.pending_requests.items()):
            try:
                # Log request details
                request_time = datetime.fromisoformat(request.timestamp)
                time_ago = request.get_elapsed_time()
                human_time = request_time.strftime("%Y-%m-%d %H:%M:%S")

                logger.info(f"  📋 Checking: '{request.title}' [TMDB ID: {request.tmdb_id}]")
                logger.info(f"     Requested by: {request.username} (UID {request.user_id})")
                logger.info(f"     Requested at: {human_time} ({time_ago} ago)")

                # Check movie status in Overseerr
                movie = await self.bot.overseerr.get_movie_by_id(
                    request.tmdb_id, is_4k=request.is_4k
                )

                logger.info(
                    f"     Current status: {movie.status.name} "
                    f"({'4K' if request.is_4k else 'HD/SD'})"
                )

                # Check if status changed
                if movie.status != request.last_status:
                    logger.info(
                        f"     🔄 Status changed: {request.last_status.name} → {movie.status.name}"
                    )
                    await self.notify_status_change(request, request.last_status, movie.status)
                    request.last_status = movie.status
                    self.save_notifications()

                if movie.available:
                    logger.info(f"     ✅ AVAILABLE - Removing from tracking")
                    # Content is now available - remove from tracking
                    completed_keys.append(key)
                else:
                    logger.info(f"     ⏳ Still pending")

            except Exception as e:
                logger.error(f"     ❌ Error checking availability: {e}")

        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Remove completed requests
        for key in completed_keys:
            del self.pending_requests[key]

        if completed_keys:
            self.save_notifications()
            logger.info(f"✅ {len(completed_keys)} request(s) completed and removed from tracking")
        else:
            logger.info(f"No requests completed in this check")

        return len(completed_keys)

    @tasks.loop()
    async def check_availability(self) -> None:
        """Periodically check if requested content is now available"""
        if not self.pending_requests:
            return

        logger.info(f"Checking availability for {len(self.pending_requests)} pending request(s)")
        await self._check_and_notify()

    def _get_status_message(self, status: MediaStatus) -> tuple[str, str, discord.Color]:
        """Get status-specific message details"""
        status_map = {
            MediaStatus.PENDING: (
                "📝 Request Pending",
                "Your request has been received and is pending approval.",
                discord.Color.orange(),
            ),
            MediaStatus.PROCESSING: (
                "⚙️ Processing",
                "Your request is being processed! The content is being downloaded.",
                discord.Color.blue(),
            ),
            MediaStatus.PARTIALLY_AVAILABLE: (
                "📦 Partially Available",
                "Part of your requested content is ready!",
                discord.Color.gold(),
            ),
            MediaStatus.AVAILABLE: (
                "🎬 Available!",
                "Your requested content is now ready to watch!",
                discord.Color.green(),
            ),
        }
        return status_map.get(
            status,
            ("ℹ️ Status Update", "Status updated.", discord.Color.greyple()),
        )

    async def notify_status_change(
        self, request: PendingRequest, old_status: MediaStatus, new_status: MediaStatus
    ) -> None:
        """Send notification to user about status change"""
        try:
            user = await self.bot.fetch_user(request.user_id)
            elapsed_time = request.get_elapsed_time()

            title, description, color = self._get_status_message(new_status)

            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
            )

            embed.add_field(name="Title", value=request.title, inline=False)
            embed.add_field(
                name="Status",
                value=f"{old_status.name} → **{new_status.name}**",
                inline=True,
            )

            if request.is_4k:
                embed.add_field(name="Quality", value="4K UHD", inline=True)

            embed.add_field(name="Time Elapsed", value=elapsed_time, inline=True)

            if new_status == MediaStatus.AVAILABLE:
                embed.set_footer(text="Enjoy your movie! 🍿")
            else:
                embed.set_footer(text="You'll be notified when the status changes.")

            await user.send(embed=embed)
            logger.info(
                f"✅ Notified {request.username} of status change for {request.title}: "
                f"{old_status.name} → {new_status.name}"
            )

        except discord.Forbidden:
            logger.warning(
                f"⚠️  Cannot send DM to {request.username} (user has DMs disabled or blocked bot)"
            )
        except Exception as e:
            logger.error(f"❌ Error notifying user {request.username}: {e}")

    @check_availability.before_loop
    async def before_check_availability(self) -> None:
        """Wait for bot to be ready before starting checks"""
        await self.bot.wait_until_ready()
        logger.info("Notification manager ready - starting availability checks")
