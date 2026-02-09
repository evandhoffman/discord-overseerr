"""Unit tests for Overseerr API client"""

import pytest
from aioresponses import aioresponses

from bot.overseerr import (
    OverseerrClient,
    Movie,
    TVShow,
    MediaStatus,
    MovieRequestResult,
)


@pytest.mark.unit
class TestMediaStatus:
    """Test MediaStatus enum"""

    def test_media_status_values(self):
        """Test MediaStatus enum values"""
        assert MediaStatus.UNKNOWN == 1
        assert MediaStatus.PENDING == 2
        assert MediaStatus.PROCESSING == 3
        assert MediaStatus.PARTIALLY_AVAILABLE == 4
        assert MediaStatus.AVAILABLE == 5

    def test_media_status_from_int(self):
        """Test creating MediaStatus from int"""
        status = MediaStatus(5)
        assert status == MediaStatus.AVAILABLE


@pytest.mark.unit
class TestMovie:
    """Test Movie data model"""

    def test_movie_creation(self, sample_movie):
        """Test creating a Movie instance"""
        assert sample_movie.tmdb_id == 550
        assert sample_movie.title == "Fight Club"
        assert sample_movie.release_date == "1999-10-15"
        assert sample_movie.available is True
        assert sample_movie.requested is False
        assert sample_movie.status == MediaStatus.AVAILABLE

    def test_poster_url(self, sample_movie):
        """Test poster URL generation"""
        expected_url = "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg"
        assert sample_movie.poster_url == expected_url

    def test_poster_url_none(self):
        """Test poster URL when poster_path is None"""
        movie = Movie(
            tmdb_id=1,
            title="Test",
            overview="Test",
            release_date="2024-01-01",
            poster_path=None,
        )
        assert movie.poster_url == ""

    def test_release_year(self, sample_movie):
        """Test release year extraction"""
        assert sample_movie.release_year == "1999"

    def test_release_year_no_date(self):
        """Test release year when date is not set"""
        movie = Movie(
            tmdb_id=1,
            title="Test",
            overview="Test",
            release_date="",
            poster_path=None,
        )
        assert movie.release_year is None

    def test_cast_list(self, sample_movie):
        """Test cast list formatting"""
        assert sample_movie.cast_list == "Brad Pitt, Edward Norton, Helena Bonham Carter"

    def test_cast_list_empty(self):
        """Test cast list when empty"""
        movie = Movie(
            tmdb_id=1,
            title="Test",
            overview="Test",
            release_date="2024-01-01",
            poster_path=None,
            cast=[],
        )
        assert movie.cast_list == ""

    def test_cast_list_truncation(self):
        """Test cast list truncates to first 3 actors"""
        movie = Movie(
            tmdb_id=1,
            title="Test",
            overview="Test",
            release_date="2024-01-01",
            poster_path=None,
            cast=["Actor 1", "Actor 2", "Actor 3", "Actor 4", "Actor 5"],
        )
        assert movie.cast_list == "Actor 1, Actor 2, Actor 3"


@pytest.mark.unit
class TestTVShow:
    """Test TVShow data model"""

    def test_tv_show_creation(self, sample_tv_show):
        """Test creating a TVShow instance"""
        assert sample_tv_show.tmdb_id == 1396
        assert sample_tv_show.name == "Breaking Bad"
        assert sample_tv_show.first_air_date == "2008-01-20"
        assert sample_tv_show.available is False
        assert sample_tv_show.requested is True
        assert sample_tv_show.status == MediaStatus.PENDING

    def test_title_alias(self, sample_tv_show):
        """Test title property alias"""
        assert sample_tv_show.title == "Breaking Bad"
        assert sample_tv_show.title == sample_tv_show.name

    def test_release_year_alias(self, sample_tv_show):
        """Test release_year property alias"""
        assert sample_tv_show.release_year == "2008"
        assert sample_tv_show.release_year == sample_tv_show.first_year

    def test_first_year(self, sample_tv_show):
        """Test first year extraction"""
        assert sample_tv_show.first_year == "2008"

    def test_poster_url(self, sample_tv_show):
        """Test poster URL generation"""
        expected_url = "https://image.tmdb.org/t/p/w500/ggFHVNu6YYI5L9pCfOacjizRGt.jpg"
        assert sample_tv_show.poster_url == expected_url


@pytest.mark.unit
class TestMovieRequestResult:
    """Test MovieRequestResult"""

    def test_success_result(self):
        """Test successful request result"""
        result = MovieRequestResult(success=True)
        assert result.success is True
        assert result.was_denied is False
        assert result.error_message == ""

    def test_failure_result(self):
        """Test failed request result"""
        result = MovieRequestResult(success=False, error_message="Quota exceeded")
        assert result.success is False
        assert result.was_denied is True
        assert result.error_message == "Quota exceeded"


@pytest.mark.unit
class TestOverseerrClient:
    """Test OverseerrClient"""

    def test_client_creation(self, overseerr_client):
        """Test creating an OverseerrClient"""
        assert overseerr_client.hostname == "test.overseerr.local"
        assert overseerr_client.port == 5055
        assert overseerr_client.api_key == "test_api_key"
        assert overseerr_client.use_ssl is False

    def test_base_url_http(self):
        """Test base URL with HTTP"""
        client = OverseerrClient(
            hostname="localhost",
            port=5055,
            api_key="test",
            use_ssl=False,
        )
        assert client.base_url == "http://localhost:5055/api/v1/"

    def test_base_url_https(self):
        """Test base URL with HTTPS"""
        client = OverseerrClient(
            hostname="overseerr.example.com",
            port=443,
            api_key="test",
            use_ssl=True,
        )
        assert client.base_url == "https://overseerr.example.com:443/api/v1/"

    @pytest.mark.asyncio
    async def test_test_connection_success(self, overseerr_client):
        """Test successful connection test"""
        with aioresponses() as m:
            m.get(
                f"{overseerr_client.base_url}settings/main",
                status=200,
                payload={"apiKey": "test_key", "applicationUrl": "http://test"},
            )

            result = await overseerr_client.test_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_invalid_api_key(self, overseerr_client):
        """Test connection with invalid API key"""
        with aioresponses() as m:
            m.get(
                f"{overseerr_client.base_url}settings/main",
                status=401,
            )

            with pytest.raises(Exception, match="Invalid API key"):
                await overseerr_client.test_connection()

    @pytest.mark.asyncio
    async def test_test_connection_not_found(self, overseerr_client):
        """Test connection with invalid hostname/port"""
        with aioresponses() as m:
            m.get(
                f"{overseerr_client.base_url}settings/main",
                status=404,
            )

            with pytest.raises(Exception, match="Invalid hostname/port"):
                await overseerr_client.test_connection()

    @pytest.mark.asyncio
    async def test_test_connection_invalid_response(self, overseerr_client):
        """Test connection with unexpected response"""
        with aioresponses() as m:
            m.get(
                f"{overseerr_client.base_url}settings/main",
                status=200,
                payload={"invalid": "data"},
            )

            with pytest.raises(Exception, match="Unexpected response"):
                await overseerr_client.test_connection()

    @pytest.mark.asyncio
    async def test_search_media_success(self, overseerr_client, overseerr_search_response):
        """Test successful media search"""
        with aioresponses() as m:
            m.get(
                f"{overseerr_client.base_url}search?query=fight%20club&page=1&language=en",
                status=200,
                payload=overseerr_search_response,
            )

            results = await overseerr_client.search_media("fight club")

            assert len(results) == 2
            assert isinstance(results[0], TVShow)  # Higher popularity
            assert results[0].tmdb_id == 1396
            assert isinstance(results[1], Movie)
            assert results[1].tmdb_id == 550

    @pytest.mark.asyncio
    async def test_search_media_empty_results(self, overseerr_client):
        """Test media search with no results"""
        with aioresponses() as m:
            m.get(
                f"{overseerr_client.base_url}search?query=nonexistent&page=1&language=en",
                status=200,
                payload={"page": 1, "totalPages": 1, "totalResults": 0, "results": []},
            )

            results = await overseerr_client.search_media("nonexistent")
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_media_error(self, overseerr_client):
        """Test media search with API error"""
        with aioresponses() as m:
            m.get(
                f"{overseerr_client.base_url}search?query=error&page=1&language=en",
                status=500,
                payload={"message": "Internal server error"},
            )

            with pytest.raises(Exception, match="Search failed"):
                await overseerr_client.search_media("error")

    @pytest.mark.asyncio
    async def test_search_media_special_characters(self, overseerr_client):
        """Test media search with special characters"""
        with aioresponses() as m:
            # URL encoding should handle special characters
            m.get(
                f"{overseerr_client.base_url}search?query=the%20%26%20fast&page=1&language=en",
                status=200,
                payload={"page": 1, "totalPages": 1, "totalResults": 0, "results": []},
            )

            results = await overseerr_client.search_media("the & fast")
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_movie_by_id(self, overseerr_client, overseerr_movie_details_response):
        """Test getting movie details by ID"""
        with aioresponses() as m:
            m.get(
                f"{overseerr_client.base_url}movie/550",
                status=200,
                payload=overseerr_movie_details_response,
            )

            movie = await overseerr_client.get_movie_by_id(550)

            assert isinstance(movie, Movie)
            assert movie.tmdb_id == 550
            assert movie.title == "Fight Club"
            assert movie.available is True
            assert len(movie.cast) == 3

    @pytest.mark.asyncio
    async def test_get_movie_by_id_4k(self, overseerr_client, overseerr_movie_details_response):
        """Test getting movie details with 4K status"""
        # Set 4K status to PENDING
        overseerr_movie_details_response["mediaInfo"]["status4k"] = 2

        with aioresponses() as m:
            m.get(
                f"{overseerr_client.base_url}movie/550",
                status=200,
                payload=overseerr_movie_details_response,
            )

            movie = await overseerr_client.get_movie_by_id(550, is_4k=True)

            assert movie.requested is True
            assert movie.status == MediaStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_movie_by_id_not_found(self, overseerr_client):
        """Test getting details for non-existent movie"""
        with aioresponses() as m:
            m.get(
                f"{overseerr_client.base_url}movie/999999",
                status=404,
                payload={"message": "Movie not found"},
            )

            with pytest.raises(Exception, match="Movie not found"):
                await overseerr_client.get_movie_by_id(999999)

    @pytest.mark.asyncio
    async def test_request_movie_success(
        self, overseerr_client, overseerr_request_success_response
    ):
        """Test successful movie request"""
        with aioresponses() as m:
            m.post(
                f"{overseerr_client.base_url}request",
                status=201,
                payload=overseerr_request_success_response,
            )

            result = await overseerr_client.request_movie(550)

            assert isinstance(result, MovieRequestResult)
            assert result.success is True
            assert result.was_denied is False

    @pytest.mark.asyncio
    async def test_request_movie_quota_exceeded(self, overseerr_client):
        """Test movie request with quota exceeded"""
        with aioresponses() as m:
            m.post(
                f"{overseerr_client.base_url}request",
                status=403,
                payload={"message": "Request limit exceeded"},
            )

            result = await overseerr_client.request_movie(550)

            assert result.success is False
            assert result.was_denied is True
            assert "quota" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_request_movie_4k(self, overseerr_client, overseerr_request_success_response):
        """Test requesting a movie in 4K"""
        overseerr_request_success_response["is4k"] = True

        with aioresponses() as m:
            m.post(
                f"{overseerr_client.base_url}request",
                status=201,
                payload=overseerr_request_success_response,
            )

            result = await overseerr_client.request_movie(550, is_4k=True)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_request_movie_already_available(self, overseerr_client):
        """Test requesting a movie that's already available"""
        with aioresponses() as m:
            m.post(
                f"{overseerr_client.base_url}request",
                status=400,  # Non-201 status
                payload={"message": "Already available"},
            )

            result = await overseerr_client.request_movie(550)
            # Should return failure since status is not 201
            assert result.success is False

    @pytest.mark.asyncio
    async def test_close_session(self, overseerr_client):
        """Test closing the HTTP session"""
        # Create a session first
        session = await overseerr_client._get_session()
        assert session is not None
        assert not session.closed

        # Close the client
        await overseerr_client.close()
        assert session.closed

    @pytest.mark.asyncio
    async def test_session_reuse(self, overseerr_client):
        """Test that the same session is reused"""
        session1 = await overseerr_client._get_session()
        session2 = await overseerr_client._get_session()

        assert session1 is session2

        await overseerr_client.close()

    @pytest.mark.asyncio
    async def test_session_recreation_after_close(self, overseerr_client):
        """Test that a new session is created after closing"""
        session1 = await overseerr_client._get_session()
        await overseerr_client.close()

        session2 = await overseerr_client._get_session()

        assert session1 is not session2
        assert not session2.closed

        await overseerr_client.close()
