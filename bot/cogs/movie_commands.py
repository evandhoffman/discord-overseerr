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

    @app_commands.command(name="request", description="Request a movie by title")
    @app_commands.describe(title="Title of the movie to request")
    async def request_movie(self, interaction: discord.Interaction, title: str):
        """Request a movie by title"""
        await interaction.response.defer(ephemeral=True)

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

    async def _show_movie_selection(
        self, interaction: discord.Interaction, movies: list[Movie]
    ):
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
                success_embed = discord.Embed(
                    title="✅ Request Submitted",
                    description=f"**{movie.title}** has been requested successfully!",
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
