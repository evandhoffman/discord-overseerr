"""Unit tests for Discord slash commands in movie_commands.py"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord import app_commands

from bot.cogs.movie_commands import MovieCommands
from bot.overseerr import Movie, TVShow, MediaStatus, MovieRequestResult


@pytest.mark.unit
class TestPingCommand:
    """Test /ping command"""

    @pytest.mark.asyncio
    async def test_ping_command(self, mock_discord_bot, mock_discord_interaction):
        """Test ping command responds with latency"""
        # Setup
        cog = MovieCommands(mock_discord_bot)
        mock_discord_bot.latency = 0.045  # 45ms

        # Execute
        await cog.ping.callback(cog, mock_discord_interaction)

        # Verify
        mock_discord_interaction.response.send_message.assert_called_once()
        call_args = mock_discord_interaction.response.send_message.call_args

        # Check embed
        embed = call_args.kwargs["embed"]
        assert "Pong!" in embed.title
        assert "45ms" in embed.description
        assert embed.color == discord.Color.green()
        assert call_args.kwargs["ephemeral"] is True


@pytest.mark.unit
class TestHelpCommand:
    """Test /help command"""

    @pytest.mark.asyncio
    async def test_help_command_no_authorization(self, mock_discord_bot, mock_discord_interaction):
        """Test help command without authorization whitelist"""
        # Setup
        mock_discord_bot.settings.discord.authorized_users = []
        cog = MovieCommands(mock_discord_bot)

        # Execute
        await cog.help_command.callback(cog, mock_discord_interaction)

        # Verify
        mock_discord_interaction.response.send_message.assert_called_once()
        call_args = mock_discord_interaction.response.send_message.call_args

        embed = call_args.kwargs["embed"]
        assert "Discord Overseerr Bot" in embed.title
        assert "/request" in str(embed.fields)
        assert "/ping" in str(embed.fields)
        assert "/overseerr-health" in str(embed.fields)

        # Should not have authorization field
        field_names = [field.name for field in embed.fields]
        assert "Authorization" not in " ".join(field_names)

        assert call_args.kwargs["ephemeral"] is True

    @pytest.mark.asyncio
    async def test_help_command_with_authorization(
        self, mock_discord_bot, mock_discord_interaction
    ):
        """Test help command with authorization whitelist enabled"""
        # Setup
        mock_discord_bot.settings.discord.authorized_users = [111, 222, 333]
        cog = MovieCommands(mock_discord_bot)

        # Execute
        await cog.help_command.callback(cog, mock_discord_interaction)

        # Verify
        call_args = mock_discord_interaction.response.send_message.call_args
        embed = call_args.kwargs["embed"]

        # Should have authorization field
        field_names = [field.name for field in embed.fields]
        assert any("Authorization" in name for name in field_names)


@pytest.mark.unit
class TestOverseerrHealthCommand:
    """Test /overseerr-health command"""

    @pytest.mark.asyncio
    async def test_overseerr_health_success(self, mock_discord_bot, mock_discord_interaction):
        """Test health check with successful connection"""
        # Setup
        cog = MovieCommands(mock_discord_bot)
        mock_discord_bot.overseerr = AsyncMock()
        mock_discord_bot.overseerr.test_connection = AsyncMock()
        mock_discord_bot.settings.overseerr.hostname = "test.overseerr.local"

        # Execute
        await cog.overseerr_health.callback(cog, mock_discord_interaction)

        # Verify
        mock_discord_interaction.response.defer.assert_called_once_with(ephemeral=True)
        mock_discord_bot.overseerr.test_connection.assert_called_once()

        call_args = mock_discord_interaction.followup.send.call_args
        embed = call_args.kwargs["embed"]
        assert "Health Check" in embed.title
        assert "✅" in embed.title
        assert embed.color == discord.Color.green()
        assert "Connected" in str(embed.fields)

    @pytest.mark.asyncio
    async def test_overseerr_health_failure(self, mock_discord_bot, mock_discord_interaction):
        """Test health check with connection failure"""
        # Setup
        cog = MovieCommands(mock_discord_bot)
        mock_discord_bot.overseerr = AsyncMock()
        mock_discord_bot.overseerr.test_connection = AsyncMock(
            side_effect=Exception("Connection refused")
        )
        mock_discord_bot.settings.overseerr.hostname = "test.overseerr.local"

        # Execute
        await cog.overseerr_health.callback(cog, mock_discord_interaction)

        # Verify
        mock_discord_interaction.response.defer.assert_called_once_with(ephemeral=True)
        call_args = mock_discord_interaction.followup.send.call_args
        embed = call_args.kwargs["embed"]
        assert "Failed" in embed.title
        assert "❌" in embed.title
        assert embed.color == discord.Color.red()
        assert "Connection refused" in str(embed.fields)


@pytest.mark.unit
class TestRequestCommand:
    """Test /request command"""

    @pytest.mark.asyncio
    async def test_request_unauthorized_user(self, mock_discord_bot, mock_discord_interaction):
        """Test request command rejects unauthorized user"""
        # Setup
        mock_discord_bot.settings.discord.authorized_users = [222, 333]  # Not including 111
        mock_discord_interaction.user.id = 111  # User not in whitelist
        cog = MovieCommands(mock_discord_bot)

        # Execute
        await cog.request_media.callback(cog, mock_discord_interaction, "Fight Club")

        # Verify
        mock_discord_interaction.response.defer.assert_called_once_with(ephemeral=True)
        call_args = mock_discord_interaction.followup.send.call_args
        embed = call_args.kwargs["embed"]
        assert "Not Authorized" in embed.title
        assert "🚫" in embed.title
        assert embed.color == discord.Color.red()

    @pytest.mark.asyncio
    async def test_request_authorized_user(
        self, mock_discord_bot, mock_discord_interaction, sample_movie
    ):
        """Test request command allows authorized user"""
        # Setup
        mock_discord_bot.settings.discord.authorized_users = [111, 222, 333]
        mock_discord_interaction.user.id = 111  # User in whitelist
        mock_discord_bot.overseerr = AsyncMock()
        mock_discord_bot.overseerr.search_media = AsyncMock(return_value=[sample_movie])

        cog = MovieCommands(mock_discord_bot)

        # Execute
        await cog.request_media.callback(cog, mock_discord_interaction, "Fight Club")

        # Verify authorized user can proceed
        mock_discord_bot.overseerr.search_media.assert_called_once_with("Fight Club")

    @pytest.mark.asyncio
    async def test_request_no_authorization_list(
        self, mock_discord_bot, mock_discord_interaction, sample_movie
    ):
        """Test request command when no authorization whitelist is set (all users allowed)"""
        # Setup
        mock_discord_bot.settings.discord.authorized_users = []  # Empty = all allowed
        mock_discord_bot.overseerr = AsyncMock()
        mock_discord_bot.overseerr.search_media = AsyncMock(return_value=[sample_movie])

        cog = MovieCommands(mock_discord_bot)

        # Execute
        await cog.request_media.callback(cog, mock_discord_interaction, "Fight Club")

        # Verify search was called (user was allowed)
        mock_discord_bot.overseerr.search_media.assert_called_once_with("Fight Club")

    @pytest.mark.asyncio
    async def test_request_no_results(self, mock_discord_bot, mock_discord_interaction):
        """Test request command when no results found"""
        # Setup
        mock_discord_bot.settings.discord.authorized_users = []
        mock_discord_bot.overseerr = AsyncMock()
        mock_discord_bot.overseerr.search_media = AsyncMock(return_value=[])

        cog = MovieCommands(mock_discord_bot)

        # Execute
        await cog.request_media.callback(cog, mock_discord_interaction, "NonexistentMovie12345")

        # Verify
        call_args = mock_discord_interaction.followup.send.call_args
        embed = call_args.kwargs["embed"]
        assert "No Results" in embed.title
        assert "❌" in embed.title
        assert "NonexistentMovie12345" in embed.description

    @pytest.mark.asyncio
    async def test_request_single_result_movie(
        self, mock_discord_bot, mock_discord_interaction, sample_movie
    ):
        """Test request command with single movie result"""
        # Setup
        mock_discord_bot.settings.discord.authorized_users = []
        mock_discord_bot.overseerr = AsyncMock()
        mock_discord_bot.overseerr.search_media = AsyncMock(return_value=[sample_movie])

        cog = MovieCommands(mock_discord_bot)

        with patch.object(cog, "_show_media_details", new_callable=AsyncMock) as mock_show_details:
            # Execute
            await cog.request_media.callback(cog, mock_discord_interaction, "Fight Club")

            # Verify it shows details directly for single result
            mock_show_details.assert_called_once_with(mock_discord_interaction, sample_movie)

    @pytest.mark.asyncio
    async def test_request_single_result_tv(
        self, mock_discord_bot, mock_discord_interaction, sample_tv_show
    ):
        """Test request command with single TV show result"""
        # Setup
        mock_discord_bot.settings.discord.authorized_users = []
        mock_discord_bot.overseerr = AsyncMock()
        mock_discord_bot.overseerr.search_media = AsyncMock(return_value=[sample_tv_show])

        cog = MovieCommands(mock_discord_bot)

        with patch.object(cog, "_show_media_details", new_callable=AsyncMock) as mock_show_details:
            # Execute
            await cog.request_media.callback(cog, mock_discord_interaction, "Breaking Bad")

            # Verify
            mock_show_details.assert_called_once_with(mock_discord_interaction, sample_tv_show)

    @pytest.mark.asyncio
    async def test_request_multiple_results(
        self, mock_discord_bot, mock_discord_interaction, sample_movie, sample_tv_show
    ):
        """Test request command with multiple results shows dropdown"""
        # Setup
        mock_discord_bot.settings.discord.authorized_users = []
        mock_discord_bot.overseerr = AsyncMock()
        mock_discord_bot.overseerr.search_media = AsyncMock(
            return_value=[sample_movie, sample_tv_show]
        )

        cog = MovieCommands(mock_discord_bot)

        with patch.object(
            cog, "_show_media_selection", new_callable=AsyncMock
        ) as mock_show_selection:
            # Execute
            await cog.request_media.callback(cog, mock_discord_interaction, "Fight")

            # Verify selection dropdown is shown
            mock_show_selection.assert_called_once()
            call_args = mock_show_selection.call_args
            assert call_args[0][0] == mock_discord_interaction
            assert len(call_args[0][1]) == 2  # Both movie and TV show

    @pytest.mark.asyncio
    async def test_request_error_handling(self, mock_discord_bot, mock_discord_interaction):
        """Test request command handles errors gracefully"""
        # Setup
        mock_discord_bot.settings.discord.authorized_users = []
        mock_discord_bot.overseerr = AsyncMock()
        mock_discord_bot.overseerr.search_media = AsyncMock(side_effect=Exception("API Error"))

        cog = MovieCommands(mock_discord_bot)

        # Execute
        await cog.request_media.callback(cog, mock_discord_interaction, "Fight Club")

        # Verify error message shown
        call_args = mock_discord_interaction.followup.send.call_args
        embed = call_args.kwargs["embed"]
        assert "Error" in embed.title
        assert "❌" in embed.title
        assert "API Error" in embed.description


@pytest.mark.unit
class TestShowMediaSelection:
    """Test _show_media_selection method"""

    @pytest.mark.asyncio
    async def test_show_media_selection_movies_and_tv(
        self, mock_discord_bot, mock_discord_interaction, sample_movie, sample_tv_show
    ):
        """Test media selection dropdown with both movies and TV shows"""
        # Setup
        cog = MovieCommands(mock_discord_bot)
        media_items = [sample_movie, sample_tv_show]

        # Execute
        await cog._show_media_selection(mock_discord_interaction, media_items)

        # Verify
        call_args = mock_discord_interaction.followup.send.call_args
        assert "select" in call_args[0][0].lower()

        view = call_args.kwargs["view"]
        assert isinstance(view, discord.ui.View)

        # Check that view has a select menu
        select_menu = view.children[0]
        assert isinstance(select_menu, discord.ui.Select)
        assert len(select_menu.options) == 2

        # Check options have correct format
        movie_option = select_menu.options[0]
        assert "🎬" in movie_option.label
        assert "Fight Club" in movie_option.label
        assert "movie:" in movie_option.value

        tv_option = select_menu.options[1]
        assert "📺" in tv_option.label
        assert "Breaking Bad" in tv_option.label
        assert "tv:" in tv_option.value

    @pytest.mark.asyncio
    async def test_show_media_selection_truncation(
        self, mock_discord_bot, mock_discord_interaction
    ):
        """Test media selection dropdown truncates to 25 items (Discord limit)"""
        # Setup
        cog = MovieCommands(mock_discord_bot)

        # Create 30 movies
        media_items = []
        for i in range(30):
            movie = Movie(
                tmdb_id=i,
                title=f"Movie {i}",
                overview=f"Overview {i}",
                release_date="2024-01-01",
                poster_path=None,
            )
            media_items.append(movie)

        # Execute
        await cog._show_media_selection(mock_discord_interaction, media_items)

        # Verify only 25 options (Discord limit)
        view = mock_discord_interaction.followup.send.call_args.kwargs["view"]
        select_menu = view.children[0]
        assert len(select_menu.options) == 25

    @pytest.mark.asyncio
    async def test_media_selection_callback_wrong_user(
        self, mock_discord_bot, mock_discord_interaction, sample_movie
    ):
        """Test media selection callback rejects wrong user"""
        # Setup
        cog = MovieCommands(mock_discord_bot)
        mock_discord_bot.overseerr = AsyncMock()

        await cog._show_media_selection(mock_discord_interaction, [sample_movie])

        # Get the callback
        view = mock_discord_interaction.followup.send.call_args.kwargs["view"]
        select_menu = view.children[0]
        callback = select_menu.callback

        # Create different user interaction
        wrong_user_interaction = AsyncMock()
        wrong_user_interaction.user.id = 999  # Different from original user (111)
        wrong_user_interaction.response = AsyncMock()

        # Execute callback with wrong user
        await callback(wrong_user_interaction)

        # Verify rejection
        wrong_user_interaction.response.send_message.assert_called_once()
        call_args = wrong_user_interaction.response.send_message.call_args
        assert "not for you" in call_args[0][0].lower()
        assert call_args.kwargs["ephemeral"] is True

    @pytest.mark.asyncio
    async def test_media_selection_callback_success(
        self, mock_discord_bot, mock_discord_interaction, sample_movie
    ):
        """Test media selection callback fetches and shows details"""
        # Setup
        cog = MovieCommands(mock_discord_bot)
        mock_discord_bot.overseerr = AsyncMock()
        mock_discord_bot.overseerr.get_media_by_id = AsyncMock(return_value=sample_movie)

        await cog._show_media_selection(mock_discord_interaction, [sample_movie])

        # Get the callback
        view = mock_discord_interaction.followup.send.call_args.kwargs["view"]
        select_menu = view.children[0]
        callback = select_menu.callback

        # Create select interaction
        select_interaction = AsyncMock()
        select_interaction.user.id = 111  # Same as original user
        select_interaction.response = AsyncMock()
        select_interaction.data = {"values": ["movie:550"]}

        with patch.object(cog, "_show_media_details", new_callable=AsyncMock) as mock_show_details:
            # Execute callback
            await callback(select_interaction)

            # Verify
            select_interaction.response.defer.assert_called_once()
            mock_discord_bot.overseerr.get_media_by_id.assert_called_once_with(550, "movie")
            mock_show_details.assert_called_once_with(mock_discord_interaction, sample_movie)


@pytest.mark.unit
class TestShowMediaDetails:
    """Test _show_media_details method"""

    @pytest.mark.asyncio
    async def test_show_movie_details_available(self, mock_discord_bot, mock_discord_interaction):
        """Test showing details for available movie"""
        # Setup
        cog = MovieCommands(mock_discord_bot)
        movie = Movie(
            tmdb_id=550,
            title="Fight Club",
            overview="A ticking-time-bomb insomniac...",
            release_date="1999-10-15",
            poster_path="/poster.jpg",
            available=True,
            requested=False,
            status=MediaStatus.AVAILABLE,
        )

        # Execute
        await cog._show_media_details(mock_discord_interaction, movie)

        # Verify
        call_args = mock_discord_interaction.edit_original_response.call_args
        embed = call_args.kwargs["embed"]
        assert "🎬" in embed.title
        assert "Fight Club" in embed.title
        assert embed.color == discord.Color.green()
        assert "✅ Available" in str(embed.fields)
        assert call_args.kwargs["view"] is None  # No request button for available

    @pytest.mark.asyncio
    async def test_show_movie_details_requested(self, mock_discord_bot, mock_discord_interaction):
        """Test showing details for already requested movie"""
        # Setup
        cog = MovieCommands(mock_discord_bot)
        movie = Movie(
            tmdb_id=550,
            title="Fight Club",
            overview="A ticking-time-bomb insomniac...",
            release_date="1999-10-15",
            poster_path="/poster.jpg",
            available=False,
            requested=True,
            status=MediaStatus.PENDING,
        )

        # Execute
        await cog._show_media_details(mock_discord_interaction, movie)

        # Verify
        call_args = mock_discord_interaction.edit_original_response.call_args
        embed = call_args.kwargs["embed"]
        assert embed.color == discord.Color.orange()
        assert "Already Requested" in str(embed.fields)
        assert call_args.kwargs["view"] is None  # No request button

    @pytest.mark.asyncio
    async def test_show_movie_details_requestable(self, mock_discord_bot, mock_discord_interaction):
        """Test showing details for requestable movie with button"""
        # Setup
        cog = MovieCommands(mock_discord_bot)
        movie = Movie(
            tmdb_id=550,
            title="Fight Club",
            overview="A ticking-time-bomb insomniac...",
            release_date="1999-10-15",
            poster_path="/poster.jpg",
            available=False,
            requested=False,
            status=MediaStatus.UNKNOWN,
        )

        # Execute
        await cog._show_media_details(mock_discord_interaction, movie)

        # Verify
        call_args = mock_discord_interaction.edit_original_response.call_args
        embed = call_args.kwargs["embed"]
        assert "🎬" in embed.title
        assert "Fight Club" in embed.title

        view = call_args.kwargs["view"]
        assert isinstance(view, discord.ui.View)

        button = view.children[0]
        assert isinstance(button, discord.ui.Button)
        assert "Request This Movie" in button.label
        assert button.emoji.name == "🎬"

    @pytest.mark.asyncio
    async def test_show_tv_details_requestable(self, mock_discord_bot, mock_discord_interaction):
        """Test showing details for requestable TV show"""
        # Setup
        cog = MovieCommands(mock_discord_bot)
        tv_show = TVShow(
            tmdb_id=1396,
            name="Breaking Bad",
            overview="A high school chemistry teacher...",
            first_air_date="2008-01-20",
            poster_path="/poster.jpg",
            available=False,
            requested=False,
            status=MediaStatus.UNKNOWN,
        )

        # Execute
        await cog._show_media_details(mock_discord_interaction, tv_show)

        # Verify
        call_args = mock_discord_interaction.edit_original_response.call_args
        embed = call_args.kwargs["embed"]
        assert "📺" in embed.title
        assert "Breaking Bad" in embed.title

        view = call_args.kwargs["view"]
        button = view.children[0]
        assert "Request This Show" in button.label
        assert button.emoji.name == "📺"


@pytest.mark.unit
class TestRequestButtonCallback:
    """Test request button callback functionality"""

    @pytest.mark.asyncio
    async def test_request_button_wrong_user(self, mock_discord_bot, mock_discord_interaction):
        """Test request button rejects wrong user"""
        # Setup
        cog = MovieCommands(mock_discord_bot)
        movie = Movie(
            tmdb_id=550,
            title="Fight Club",
            overview="Test",
            release_date="1999-10-15",
            poster_path=None,
            available=False,
            requested=False,
        )

        await cog._show_media_details(mock_discord_interaction, movie)

        # Get the button callback
        view = mock_discord_interaction.edit_original_response.call_args.kwargs["view"]
        button = view.children[0]
        callback = button.callback

        # Create different user interaction
        wrong_user_interaction = AsyncMock()
        wrong_user_interaction.user.id = 999
        wrong_user_interaction.response = AsyncMock()

        # Execute
        await callback(wrong_user_interaction)

        # Verify rejection
        wrong_user_interaction.response.send_message.assert_called_once()
        call_args = wrong_user_interaction.response.send_message.call_args
        assert "not for you" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_request_movie_success(self, mock_discord_bot, mock_discord_interaction):
        """Test successful movie request"""
        # Setup
        cog = MovieCommands(mock_discord_bot)
        mock_discord_bot.overseerr = AsyncMock()
        mock_discord_bot.overseerr.request_movie = AsyncMock(
            return_value=MovieRequestResult(success=True)
        )
        mock_discord_bot.notifications = MagicMock()
        mock_discord_bot.notifications.add_request = MagicMock()

        movie = Movie(
            tmdb_id=550,
            title="Fight Club",
            overview="Test",
            release_date="1999-10-15",
            poster_path=None,
            available=False,
            requested=False,
        )

        await cog._show_media_details(mock_discord_interaction, movie)

        # Get the button callback
        view = mock_discord_interaction.edit_original_response.call_args.kwargs["view"]
        button = view.children[0]
        callback = button.callback

        # Create button click interaction
        button_interaction = AsyncMock()
        button_interaction.user.id = 111  # Same as original
        button_interaction.user.name = "TestUser"
        button_interaction.response = AsyncMock()

        # Execute
        await callback(button_interaction)

        # Verify
        button_interaction.response.defer.assert_called_once()
        mock_discord_bot.overseerr.request_movie.assert_called_once_with(550)

        # Verify notification was added
        mock_discord_bot.notifications.add_request.assert_called_once_with(
            user_id=111,
            username="TestUser",
            tmdb_id=550,
            title="Fight Club",
            is_4k=False,
        )

        # Verify success message
        edit_call_args = mock_discord_interaction.edit_original_response.call_args_list[-1]
        embed = edit_call_args.kwargs["embed"]
        assert "✅" in embed.title
        assert "Request Submitted" in embed.title
        assert "Fight Club" in embed.description
        assert embed.color == discord.Color.green()

    @pytest.mark.asyncio
    async def test_request_tv_success(self, mock_discord_bot, mock_discord_interaction):
        """Test successful TV show request"""
        # Setup
        cog = MovieCommands(mock_discord_bot)
        mock_discord_bot.overseerr = AsyncMock()
        mock_discord_bot.overseerr.request_tv = AsyncMock(
            return_value=MovieRequestResult(success=True)
        )
        mock_discord_bot.notifications = MagicMock()
        mock_discord_bot.notifications.add_request = MagicMock()

        tv_show = TVShow(
            tmdb_id=1396,
            name="Breaking Bad",
            overview="Test",
            first_air_date="2008-01-20",
            poster_path=None,
            available=False,
            requested=False,
        )

        await cog._show_media_details(mock_discord_interaction, tv_show)

        # Get the button callback
        view = mock_discord_interaction.edit_original_response.call_args.kwargs["view"]
        button = view.children[0]
        callback = button.callback

        # Create button click interaction
        button_interaction = AsyncMock()
        button_interaction.user.id = 111
        button_interaction.user.name = "TestUser"
        button_interaction.response = AsyncMock()

        # Execute
        await callback(button_interaction)

        # Verify TV request was called
        mock_discord_bot.overseerr.request_tv.assert_called_once_with(1396)

    @pytest.mark.asyncio
    async def test_request_movie_failure(self, mock_discord_bot, mock_discord_interaction):
        """Test failed movie request"""
        # Setup
        cog = MovieCommands(mock_discord_bot)
        mock_discord_bot.overseerr = AsyncMock()
        mock_discord_bot.overseerr.request_movie = AsyncMock(
            return_value=MovieRequestResult(success=False, error_message="Quota exceeded")
        )

        movie = Movie(
            tmdb_id=550,
            title="Fight Club",
            overview="Test",
            release_date="1999-10-15",
            poster_path=None,
            available=False,
            requested=False,
        )

        await cog._show_media_details(mock_discord_interaction, movie)

        # Get the button callback
        view = mock_discord_interaction.edit_original_response.call_args.kwargs["view"]
        button = view.children[0]
        callback = button.callback

        # Create button click interaction
        button_interaction = AsyncMock()
        button_interaction.user.id = 111
        button_interaction.response = AsyncMock()

        # Execute
        await callback(button_interaction)

        # Verify error message
        edit_call_args = mock_discord_interaction.edit_original_response.call_args_list[-1]
        embed = edit_call_args.kwargs["embed"]
        assert "❌" in embed.title
        assert "Request Failed" in embed.title
        assert "Quota exceeded" in embed.description
        assert embed.color == discord.Color.red()

    @pytest.mark.asyncio
    async def test_request_without_notification_manager(
        self, mock_discord_bot, mock_discord_interaction
    ):
        """Test request works without notification manager"""
        # Setup
        cog = MovieCommands(mock_discord_bot)
        mock_discord_bot.overseerr = AsyncMock()
        mock_discord_bot.overseerr.request_movie = AsyncMock(
            return_value=MovieRequestResult(success=True)
        )
        mock_discord_bot.notifications = None  # No notification manager

        movie = Movie(
            tmdb_id=550,
            title="Fight Club",
            overview="Test",
            release_date="1999-10-15",
            poster_path=None,
            available=False,
            requested=False,
        )

        await cog._show_media_details(mock_discord_interaction, movie)

        # Get the button callback
        view = mock_discord_interaction.edit_original_response.call_args.kwargs["view"]
        button = view.children[0]
        callback = button.callback

        # Create button click interaction
        button_interaction = AsyncMock()
        button_interaction.user.id = 111
        button_interaction.user.name = "TestUser"
        button_interaction.response = AsyncMock()

        # Execute - should not raise error
        await callback(button_interaction)

        # Verify request still succeeded
        mock_discord_bot.overseerr.request_movie.assert_called_once_with(550)


@pytest.mark.unit
class TestFormatMediaTitle:
    """Test _format_media_title helper method"""

    def test_format_title_with_year(self, mock_discord_bot):
        """Test formatting title with release year"""
        cog = MovieCommands(mock_discord_bot)
        movie = Movie(
            tmdb_id=550,
            title="Fight Club",
            overview="Test",
            release_date="1999-10-15",
            poster_path=None,
        )

        result = cog._format_media_title(movie)
        assert result == "Fight Club (1999)"

    def test_format_title_without_year(self, mock_discord_bot):
        """Test formatting title without release year"""
        cog = MovieCommands(mock_discord_bot)
        movie = Movie(
            tmdb_id=550,
            title="Fight Club",
            overview="Test",
            release_date="",
            poster_path=None,
        )

        result = cog._format_media_title(movie)
        assert result == "Fight Club"


@pytest.mark.unit
class TestCogSetup:
    """Test cog setup function"""

    @pytest.mark.asyncio
    async def test_setup_function(self, mock_discord_bot):
        """Test the setup function adds cog to bot"""
        from bot.cogs.movie_commands import setup

        mock_discord_bot.add_cog = AsyncMock()

        await setup(mock_discord_bot)

        mock_discord_bot.add_cog.assert_called_once()
        cog = mock_discord_bot.add_cog.call_args[0][0]
        assert isinstance(cog, MovieCommands)
        assert cog.bot == mock_discord_bot
