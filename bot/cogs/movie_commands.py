"""Movie and TV show request commands"""

import logging
from typing import TYPE_CHECKING, List

import discord
from discord import app_commands
from discord.ext import commands

from bot.overseerr import Movie, TVShow, MediaItem

if TYPE_CHECKING:
    from bot.main import MovieBot

logger = logging.getLogger(__name__)


class MovieCommands(commands.Cog):
    """Movie request slash commands"""

    def __init__(self, bot: "MovieBot") -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Check if the bot is alive")
    async def ping(self, interaction: discord.Interaction) -> None:
        """Health check command"""
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🏓 Pong!",
                description=f"Bot is alive and responding.\nLatency: {round(self.bot.latency * 1000)}ms",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )

    @app_commands.command(name="help", description="Show available commands and how to use them")
    async def help_command(self, interaction: discord.Interaction) -> None:
        """Help command showing all available commands"""
        embed = discord.Embed(
            title="🎬 Discord Overseerr Bot - Help",
            description="Request movies and TV shows directly from Discord!",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="/request <title>",
            value="Search for and request movies or TV shows\nExample: `/request The Matrix` or `/request The Office`",
            inline=False,
        )

        embed.add_field(
            name="/ping", value="Check if the bot is alive and responding", inline=False
        )

        embed.add_field(
            name="/overseerr-health",
            value="Check Overseerr connection and health status",
            inline=False,
        )

        embed.add_field(name="/help", value="Show this help message", inline=False)

        # Add authorization info if whitelist is enabled
        authorized_users = self.bot.settings.discord.authorized_users
        if authorized_users:
            embed.add_field(
                name="ℹ️ Authorization",
                value="This bot is restricted to authorized users only.",
                inline=False,
            )

        embed.set_footer(text="Powered by Overseerr")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="overseerr-health", description="Check Overseerr connection and health"
    )
    async def overseerr_health(self, interaction: discord.Interaction) -> None:
        """Check if Overseerr is reachable and healthy"""
        await interaction.response.defer(ephemeral=True)

        try:
            # Test connection
            await self.bot.overseerr.test_connection()

            # Get additional info
            overseerr_url = self.bot.settings.overseerr.base_url.rstrip("/api/v1/")

            embed = discord.Embed(
                title="✅ Overseerr Health Check",
                description="Overseerr is reachable and healthy!",
                color=discord.Color.green(),
            )

            embed.add_field(name="Overseerr URL", value=overseerr_url, inline=False)

            embed.add_field(name="Connection", value="✅ Connected", inline=True)

            embed.add_field(name="API Status", value="✅ Responding", inline=True)

            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Overseerr Health Check Failed",
                description="Unable to connect to Overseerr",
                color=discord.Color.red(),
            )

            embed.add_field(name="Error", value=str(e), inline=False)

            embed.add_field(
                name="Configured URL",
                value=self.bot.settings.overseerr.base_url.rstrip("/api/v1/"),
                inline=False,
            )

            await interaction.followup.send(embed=embed)
            logger.error(f"Overseerr health check failed: {e}")

    @app_commands.command(name="request", description="Request a movie or TV show")
    @app_commands.describe(title="Title of the movie or TV show to request")
    async def request_media(self, interaction: discord.Interaction, title: str) -> None:
        """Request a movie or TV show by title"""
        await interaction.response.defer(ephemeral=True)

        # Check if user is authorized (if whitelist is configured)
        authorized_users = self.bot.settings.discord.authorized_users
        if authorized_users:
            if interaction.user.id not in authorized_users:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="🚫 Not Authorized",
                        description="Sorry, you're not authorized to use this bot.",
                        color=discord.Color.red(),
                    )
                )
                logger.warning(
                    f"Unauthorized request attempt from user {interaction.user.name} "
                    f"(UID {interaction.user.id})"
                )
                return
            else:
                logger.info(
                    f"User {interaction.user.name} (UID {interaction.user.id}) is authorized"
                )

        try:
            logger.info(
                f"User {interaction.user.name} ({interaction.user.id}) searching for: '{title}'"
            )

            # Search for movies and TV shows
            media_items = await self.bot.overseerr.search_media(title)

            if not media_items:
                logger.info(f"No results found for query: '{title}'")
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ No Results",
                        description=f"No movies or TV shows found matching: **{title}**",
                        color=discord.Color.red(),
                    )
                )
                return

            logger.info(
                f"Found {len(media_items)} result(s) for query: '{title}' "
                f"({sum(1 for m in media_items if isinstance(m, Movie))} movies, "
                f"{sum(1 for m in media_items if isinstance(m, TVShow))} TV shows)"
            )

            if len(media_items) == 1:
                # Single result - show details
                await self._show_media_details(interaction, media_items[0])
            else:
                # Multiple results - show selection
                await self._show_media_selection(interaction, media_items)

        except Exception as e:
            logger.error(
                f"Error in request command for user {interaction.user.name} "
                f"searching '{title}': {e}",
                exc_info=True,
            )
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Error",
                    description=f"An error occurred while searching for **{title}**.\n\n"
                    f"Error: {str(e)}\n\n"
                    f"Please try again or contact an administrator if the problem persists.",
                    color=discord.Color.red(),
                )
            )

    async def _show_media_selection(
        self, interaction: discord.Interaction, media_items: List[MediaItem]
    ) -> None:
        """Display dropdown of movies and TV shows"""
        options = []
        for media in media_items[:25]:  # Discord limit
            # Create label with emoji and text type indicator
            if isinstance(media, Movie):
                type_indicator = "🎬 [Movie]"
            else:  # TVShow
                type_indicator = "📺 [TV]"

            title_text = self._format_media_title(media)
            label = f"{type_indicator} {title_text}"

            # Store both TMDB ID and media type in value
            value = f"{media.media_type}:{media.tmdb_id}"

            # Prefer cast list in description, fallback to overview
            description = None
            if media.cast_list:
                description = f"★ {media.cast_list}"
            elif media.overview:
                description = media.overview[:100]

            options.append(
                discord.SelectOption(
                    label=label[:100],  # Discord limit
                    value=value,
                    description=description[:100] if description else None,
                )
            )

        select = discord.ui.Select(
            placeholder="Choose a movie or TV show...",
            options=options,
        )

        async def select_callback(select_interaction: discord.Interaction):
            if select_interaction.user.id != interaction.user.id:
                await select_interaction.response.send_message(
                    "This selection is not for you!", ephemeral=True
                )
                return

            await select_interaction.response.defer()
            # Parse media type and ID from value
            media_type, tmdb_id_str = select_interaction.data["values"][0].split(":")
            tmdb_id = int(tmdb_id_str)

            # Fetch media details
            media = await self.bot.overseerr.get_media_by_id(tmdb_id, media_type)

            logger.info(
                f"User {select_interaction.user.name} (UID {select_interaction.user.id}) "
                f"selected: '{media.title}' ({media.release_year or 'Unknown year'}) "
                f"[{media_type.upper()}] [TMDB ID: {media.tmdb_id}]"
            )

            await self._show_media_details(interaction, media)

        select.callback = select_callback

        view = discord.ui.View()
        view.add_item(select)

        await interaction.followup.send("Please select a movie or TV show:", view=view)

    async def _show_media_details(self, interaction: discord.Interaction, media: MediaItem) -> None:
        """Show media details with request button"""
        media_type_label = "Movie" if isinstance(media, Movie) else "TV Show"
        logger.info(
            f"Showing details for: '{media.title}' ({media.release_year or 'Unknown year'}) "
            f"[{media_type_label}] [TMDB ID: {media.tmdb_id}] - Status: {media.status.name}"
        )

        # Add media type emoji to title
        if isinstance(media, Movie):
            title_prefix = "🎬"
            year_label = "Release Year"
        else:
            title_prefix = "📺"
            year_label = "First Aired"

        embed = discord.Embed(
            title=f"{title_prefix} {media.title}",
            description=media.overview[:500] if media.overview else "No description available",
            color=discord.Color.blue(),
        )

        if media.release_year:
            embed.add_field(name=year_label, value=media.release_year)

        if media.poster_url:
            embed.set_thumbnail(url=media.poster_url)

        # Check status
        if media.available:
            embed.color = discord.Color.green()
            embed.add_field(name="Status", value="✅ Available", inline=False)
            await interaction.edit_original_response(embed=embed, view=None)
            return

        if media.requested:
            embed.color = discord.Color.orange()
            embed.add_field(name="Status", value="⏳ Already Requested", inline=False)
            await interaction.edit_original_response(embed=embed, view=None)
            return

        # Create request button
        button_label = "Request This Movie" if isinstance(media, Movie) else "Request This Show"
        button_emoji = "🎬" if isinstance(media, Movie) else "📺"

        button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label=button_label,
            emoji=button_emoji,
        )

        async def button_callback(button_interaction: discord.Interaction):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message(
                    "This button is not for you!", ephemeral=True
                )
                return

            await button_interaction.response.defer()

            # Request based on media type
            if isinstance(media, Movie):
                result = await self.bot.overseerr.request_movie(media.tmdb_id)
            else:  # TVShow - request all seasons by default
                result = await self.bot.overseerr.request_tv(media.tmdb_id)

            if result.success:
                # Add to notification tracking
                if self.bot.notifications:
                    self.bot.notifications.add_request(
                        user_id=button_interaction.user.id,
                        username=button_interaction.user.name,
                        tmdb_id=media.tmdb_id,
                        title=media.title,
                        is_4k=False,  # TODO: Add 4K support
                    )

                success_message = (
                    f"**{media.title}** has been requested successfully!\n\n"
                    f"You'll receive a notification when it's available."
                )

                success_embed = discord.Embed(
                    title="✅ Request Submitted",
                    description=success_message,
                    color=discord.Color.green(),
                )
                await interaction.edit_original_response(embed=success_embed, view=None)
            else:
                error_embed = discord.Embed(
                    title="❌ Request Failed",
                    description=f"Failed to request **{media.title}**: {result.error_message}",
                    color=discord.Color.red(),
                )
                await interaction.edit_original_response(embed=error_embed, view=None)

        button.callback = button_callback

        view = discord.ui.View()
        view.add_item(button)

        await interaction.edit_original_response(embed=embed, view=view)

    def _format_media_title(self, media: MediaItem) -> str:
        """Format media title for display"""
        if media.release_year:
            return f"{media.title} ({media.release_year})"
        return media.title


async def setup(bot: "MovieBot") -> None:
    """Load the cog"""
    await bot.add_cog(MovieCommands(bot))
