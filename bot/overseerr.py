"""Overseerr API client"""

import logging
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import aiohttp

logger = logging.getLogger(__name__)


class MediaStatus(IntEnum):
    """Overseerr media status codes"""

    UNKNOWN = 1
    PENDING = 2
    PROCESSING = 3
    PARTIALLY_AVAILABLE = 4
    AVAILABLE = 5


@dataclass
class Movie:
    """Movie data model"""

    tmdb_id: int
    title: str
    overview: str
    release_date: str
    poster_path: Optional[str]
    available: bool = False
    requested: bool = False
    status: MediaStatus = MediaStatus.UNKNOWN
    media_type: str = "movie"

    @property
    def poster_url(self) -> str:
        """Full TMDB poster URL"""
        if self.poster_path:
            return f"https://image.tmdb.org/t/p/w500{self.poster_path}"
        return ""

    @property
    def release_year(self) -> Optional[str]:
        """Extract year from release date"""
        if self.release_date and len(self.release_date) >= 4:
            return self.release_date[:4]
        return None


@dataclass
class TVShow:
    """TV Show data model"""

    tmdb_id: int
    name: str
    overview: str
    first_air_date: str
    poster_path: Optional[str]
    available: bool = False
    requested: bool = False
    status: MediaStatus = MediaStatus.UNKNOWN
    media_type: str = "tv"

    @property
    def poster_url(self) -> str:
        """Full TMDB poster URL"""
        if self.poster_path:
            return f"https://image.tmdb.org/t/p/w500{self.poster_path}"
        return ""

    @property
    def first_year(self) -> Optional[str]:
        """Extract year from first air date"""
        if self.first_air_date and len(self.first_air_date) >= 4:
            return self.first_air_date[:4]
        return None

    @property
    def title(self) -> str:
        """Alias for name to match Movie interface"""
        return self.name

    @property
    def release_year(self) -> Optional[str]:
        """Alias for first_year to match Movie interface"""
        return self.first_year


# Union type for media items
MediaItem = Movie | TVShow


class MovieRequestResult:
    """Result of a movie request operation"""

    def __init__(self, success: bool = True, error_message: str = ""):
        self.success = success
        self.error_message = error_message

    @property
    def was_denied(self) -> bool:
        return not self.success


class OverseerrClient:
    """Client for Overseerr API interactions"""

    def __init__(
        self,
        hostname: str,
        port: int,
        api_key: str,
        use_ssl: bool = False,
    ):
        self.hostname = hostname
        self.port = port
        self.api_key = api_key
        self.use_ssl = use_ssl
        self.session: Optional[aiohttp.ClientSession] = None

    @property
    def base_url(self) -> str:
        protocol = "https" if self.use_ssl else "http"
        return f"{protocol}://{self.hostname}:{self.port}/api/v1/"

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "X-Api-Key": self.api_key,
                    "Content-Type": "application/json",
                }
            )
        return self.session

    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def test_connection(self) -> bool:
        """Test connection to Overseerr"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}settings/main") as resp:
                if resp.status == 401:
                    raise Exception("Invalid API key")
                elif resp.status == 404:
                    raise Exception("Invalid hostname/port - API endpoint not found")

                data = await resp.json()

                # Verify we got valid data
                if "apiKey" not in data:
                    raise Exception("Unexpected response from Overseerr")

                return True
        except aiohttp.ClientError as e:
            raise Exception(f"Connection failed: {e}")

    async def search_media(self, query: str, is_4k: bool = False) -> List[MediaItem]:
        """
        Search for both movies and TV shows

        Args:
            query: Search query
            is_4k: Whether to check 4K status

        Returns:
            List of matching media items (movies and TV shows)
        """
        try:
            logger.debug(f"Searching for media: query='{query}', is_4k={is_4k}")
            session = await self._get_session()

            # Manually URL encode the query to satisfy Overseerr's strict requirements
            encoded_query = quote(query, safe="")
            url = f"{self.base_url}search?query={encoded_query}&page=1&language=en"

            logger.debug(f"Request URL: {url}")

            async with session.get(url) as resp:
                logger.debug(f"Response status: {resp.status}")

                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Search failed with status {resp.status}: {error_text}")

                    try:
                        error = await resp.json()
                        error_message = error.get("message", "Unknown error")
                    except:
                        error_message = error_text

                    raise Exception(f"Search failed: {error_message}")

                data = await resp.json()
                results = data.get("results", [])

                logger.debug(f"Found {len(results)} total results")

                # Convert both movies and TV shows
                media_items = []
                for item in results:
                    media_type = item.get("mediaType")
                    if media_type == "movie":
                        media_items.append(self._convert_movie(item, is_4k))
                    elif media_type == "tv":
                        media_items.append(self._convert_tv(item, is_4k))

                logger.info(
                    f"Search for '{query}' returned {len(media_items)} result(s) "
                    f"({sum(1 for m in media_items if m.media_type == 'movie')} movies, "
                    f"{sum(1 for m in media_items if m.media_type == 'tv')} TV shows)"
                )

                return media_items
        except Exception as e:
            logger.error(f"Error searching media for query '{query}': {e}", exc_info=True)
            raise

    async def search_movies(self, query: str, is_4k: bool = False) -> List[Movie]:
        """
        Search for movies only (kept for backwards compatibility)

        Args:
            query: Movie title to search for
            is_4k: Whether to check 4K status

        Returns:
            List of matching movies
        """
        all_media = await self.search_media(query, is_4k)
        return [item for item in all_media if isinstance(item, Movie)]

    async def get_movie_by_id(self, tmdb_id: int, is_4k: bool = False) -> Movie:
        """
        Get movie details by TMDB ID

        Args:
            tmdb_id: TheMovieDB ID
            is_4k: Whether to check 4K status

        Returns:
            Movie details
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}movie/{tmdb_id}"

            async with session.get(url) as resp:
                if resp.status != 200:
                    raise Exception(f"Movie not found: {tmdb_id}")

                data = await resp.json()
                return self._convert_movie(data, is_4k)
        except Exception as e:
            logger.error(f"Error getting movie {tmdb_id}: {e}")
            raise

    async def get_tv_by_id(self, tmdb_id: int, is_4k: bool = False) -> TVShow:
        """
        Get TV show details by TMDB ID

        Args:
            tmdb_id: TheMovieDB ID
            is_4k: Whether to check 4K status

        Returns:
            TV show details
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}tv/{tmdb_id}"

            async with session.get(url) as resp:
                if resp.status != 200:
                    raise Exception(f"TV show not found: {tmdb_id}")

                data = await resp.json()
                return self._convert_tv(data, is_4k)
        except Exception as e:
            logger.error(f"Error getting TV show {tmdb_id}: {e}")
            raise

    async def get_media_by_id(
        self, tmdb_id: int, media_type: str, is_4k: bool = False
    ) -> MediaItem:
        """
        Get media details by TMDB ID and type

        Args:
            tmdb_id: TheMovieDB ID
            media_type: 'movie' or 'tv'
            is_4k: Whether to check 4K status

        Returns:
            Media details (Movie or TVShow)
        """
        if media_type == "movie":
            return await self.get_movie_by_id(tmdb_id, is_4k)
        elif media_type == "tv":
            return await self.get_tv_by_id(tmdb_id, is_4k)
        else:
            raise ValueError(f"Unknown media type: {media_type}")

    async def request_movie(
        self,
        tmdb_id: int,
        user_id: Optional[str] = None,
        is_4k: bool = False,
    ) -> MovieRequestResult:
        """
        Request a movie in Overseerr

        Args:
            tmdb_id: TheMovieDB ID
            user_id: Overseerr user ID (optional)
            is_4k: Request 4K version

        Returns:
            MovieRequestResult indicating success/failure
        """
        return await self._request_media(tmdb_id, "movie", user_id, is_4k)

    async def request_tv(
        self,
        tmdb_id: int,
        user_id: Optional[str] = None,
        is_4k: bool = False,
        seasons: Optional[List[int]] = None,
    ) -> MovieRequestResult:
        """
        Request a TV show in Overseerr

        Args:
            tmdb_id: TheMovieDB ID
            user_id: Overseerr user ID (optional)
            is_4k: Request 4K version
            seasons: List of season numbers to request (None = all seasons)

        Returns:
            MovieRequestResult indicating success/failure
        """
        return await self._request_media(tmdb_id, "tv", user_id, is_4k, seasons)

    async def _request_media(
        self,
        tmdb_id: int,
        media_type: str,
        user_id: Optional[str] = None,
        is_4k: bool = False,
        seasons: Optional[List[int]] = None,
    ) -> MovieRequestResult:
        """
        Internal method to request media in Overseerr

        Args:
            tmdb_id: TheMovieDB ID
            media_type: 'movie' or 'tv'
            user_id: Overseerr user ID (optional)
            is_4k: Request 4K version
            seasons: For TV shows, list of season numbers (None = all)

        Returns:
            MovieRequestResult indicating success/failure
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}request"

            # Build request payload
            payload: Dict[str, Any] = {
                "mediaId": tmdb_id,
                "mediaType": media_type,
                "is4k": is_4k,
            }

            # Add seasons for TV shows (if not specified, defaults to all)
            if media_type == "tv" and seasons is not None:
                payload["seasons"] = seasons

            # Add user ID if provided
            if user_id:
                payload["userId"] = int(user_id)

            async with session.post(url, json=payload) as resp:
                if resp.status == 403:
                    return MovieRequestResult(
                        success=False,
                        error_message="Permission denied or quota exceeded",
                    )
                elif resp.status != 201:
                    error = await resp.json()
                    return MovieRequestResult(
                        success=False,
                        error_message=error.get("message", "Request failed"),
                    )

                return MovieRequestResult(success=True)
        except Exception as e:
            logger.error(f"Error requesting {media_type} {tmdb_id}: {e}")
            return MovieRequestResult(success=False, error_message=str(e))

    def _convert_movie(self, data: Dict[str, Any], is_4k: bool) -> Movie:
        """Convert Overseerr JSON to Movie object"""
        media_info = data.get("mediaInfo")
        status, available, requested = self._parse_media_status(media_info, is_4k)

        return Movie(
            tmdb_id=data.get("id"),
            title=data.get("title", "Unknown"),
            overview=data.get("overview", ""),
            release_date=data.get("releaseDate", ""),
            poster_path=data.get("posterPath"),
            available=available,
            requested=requested,
            status=status,
        )

    def _convert_tv(self, data: Dict[str, Any], is_4k: bool) -> TVShow:
        """Convert Overseerr JSON to TVShow object"""
        media_info = data.get("mediaInfo")
        status, available, requested = self._parse_media_status(media_info, is_4k)

        return TVShow(
            tmdb_id=data.get("id"),
            name=data.get("name", "Unknown"),
            overview=data.get("overview", ""),
            first_air_date=data.get("firstAirDate", ""),
            poster_path=data.get("posterPath"),
            available=available,
            requested=requested,
            status=status,
        )

    def _parse_media_status(
        self, media_info: Optional[Dict[str, Any]], is_4k: bool
    ) -> tuple[MediaStatus, bool, bool]:
        """Parse media status from Overseerr response"""
        if media_info:
            if is_4k:
                status_value = media_info.get("status4k", MediaStatus.UNKNOWN)
            else:
                status_value = media_info.get("status", MediaStatus.UNKNOWN)

            # Convert int to MediaStatus enum if needed
            if isinstance(status_value, int):
                try:
                    status = MediaStatus(status_value)
                except ValueError:
                    logger.warning(f"Unknown status value {status_value}, defaulting to UNKNOWN")
                    status = MediaStatus.UNKNOWN
            else:
                status = status_value

            available = status in [MediaStatus.AVAILABLE, MediaStatus.PARTIALLY_AVAILABLE]
            requested = status in [MediaStatus.PENDING, MediaStatus.PROCESSING]
        else:
            status = MediaStatus.UNKNOWN
            available = False
            requested = False

        return status, available, requested
