"""Movie request commands"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.overseerr import Movie

logger = logging.getLogger(__name__)


class MovieCommands(commands.Cog):
    """Movie request slash commands"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check if the bot is alive")
    async def ping(self, interaction: discord.Interaction):
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
    async def help_command(self, interaction: discord.Interaction):
        """Help command showing all available commands"""
        embed = discord.Embed(
            title="🎬 Discord Overseerr Bot - Help",
            description="Request movies and TV shows directly from Discord!",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="/request <title>",
            value="Search for and request a movie by title\nExample: `/request The Matrix`",
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
    async def overseerr_health(self, interaction: discord.Interaction):
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

    @app_commands.command(name="request", description="Request a movie by title")
    @app_commands.describe(title="Title of the movie to request")
    async def request_movie(self, interaction: discord.Interaction, title: str):
        """Request a movie by title"""
        await interaction.response.defer(ephemeral=True)

        # Check if user is authorized (if whitelist is configured)
        authorized_users = self.bot.settings.discord.authorized_users
        if authorized_users and interaction.user.id not in authorized_users:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="🚫 Not Authorized",
                    description="Sorry, you're not authorized to use this bot.",
                    color=discord.Color.red(),
                )
            )
            logger.warning(
                f"Unauthorized request attempt from user {interaction.user.id} ({interaction.user.name})"
            )
            return

        try:
            # Search for movies
            movies = await self.bot.overseerr.search_movies(title)

            if not movies:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ No Results",
                        description=f"No movies found matching: **{title}**",
                        color=discord.Color.red(),
                    )
                )
                return

            if len(movies) == 1:
                # Single result - show details
                await self._show_movie_details(interaction, movies[0])
            else:
                # Multiple results - show selection
                await self._show_movie_selection(interaction, movies)

        except Exception as e:
            logger.error(f"Error in request command: {e}")
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Error",
                    description=f"An error occurred: {str(e)}",
                    color=discord.Color.red(),
                )
            )

    async def _show_movie_selection(self, interaction: discord.Interaction, movies: list[Movie]):
        """Display dropdown of movies"""
        options = []
        for movie in movies[:25]:  # Discord limit
            label = self._format_movie_title(movie)
            options.append(
                discord.SelectOption(
                    label=label[:100],  # Discord limit
                    value=str(movie.tmdb_id),
                    description=movie.overview[:100] if movie.overview else None,
                )
            )

        select = discord.ui.Select(
            placeholder="Choose a movie...",
            options=options,
        )

        async def select_callback(select_interaction: discord.Interaction):
            if select_interaction.user.id != interaction.user.id:
                await select_interaction.response.send_message(
                    "This selection is not for you!", ephemeral=True
                )
                return

            await select_interaction.response.defer()
            tmdb_id = int(select_interaction.data["values"][0])
            movie = await self.bot.overseerr.get_movie_by_id(tmdb_id)
            await self._show_movie_details(interaction, movie)

        select.callback = select_callback

        view = discord.ui.View()
        view.add_item(select)

        await interaction.followup.send("Please select a movie:", view=view)

    async def _show_movie_details(self, interaction: discord.Interaction, movie: Movie):
        """Show movie details with request button"""
        embed = discord.Embed(
            title=movie.title,
            description=movie.overview[:500] if movie.overview else "No description available",
            color=discord.Color.blue(),
        )

        if movie.release_year:
            embed.add_field(name="Release Year", value=movie.release_year)

        if movie.poster_url:
            embed.set_thumbnail(url=movie.poster_url)

        # Check status
        if movie.available:
            embed.color = discord.Color.green()
            embed.add_field(name="Status", value="✅ Available", inline=False)
            await interaction.edit_original_response(embed=embed, view=None)
            return

        if movie.requested:
            embed.color = discord.Color.orange()
            embed.add_field(name="Status", value="⏳ Already Requested", inline=False)
            await interaction.edit_original_response(embed=embed, view=None)
            return

        # Create request button
        button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Request This Movie",
            emoji="🎬",
        )

        async def button_callback(button_interaction: discord.Interaction):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message(
                    "This button is not for you!", ephemeral=True
                )
                return

            await button_interaction.response.defer()
            result = await self.bot.overseerr.request_movie(movie.tmdb_id)

            if result.success:
                # Add to notification tracking
                if self.bot.notifications:
                    self.bot.notifications.add_request(
                        user_id=button_interaction.user.id,
                        username=button_interaction.user.name,
                        tmdb_id=movie.tmdb_id,
                        title=movie.title,
                        is_4k=False,  # TODO: Add 4K support
                    )

                success_embed = discord.Embed(
                    title="✅ Request Submitted",
                    description=f"**{movie.title}** has been requested successfully!\n\n"
                    f"You'll receive a notification when it's available.",
                    color=discord.Color.green(),
                )
                await interaction.edit_original_response(embed=success_embed, view=None)
            else:
                error_embed = discord.Embed(
                    title="❌ Request Failed",
                    description=f"Failed to request **{movie.title}**: {result.error_message}",
                    color=discord.Color.red(),
                )
                await interaction.edit_original_response(embed=error_embed, view=None)

        button.callback = button_callback

        view = discord.ui.View()
        view.add_item(button)

        await interaction.edit_original_response(embed=embed, view=view)

    def _format_movie_title(self, movie: Movie) -> str:
        """Format movie title for display"""
        if movie.release_year:
            return f"{movie.title} ({movie.release_year})"
        return movie.title


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(MovieCommands(bot))
