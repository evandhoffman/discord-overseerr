# Python Implementation Guide for Discord Movie Request Bot

## Project Overview

This document provides detailed guidance for building a Python-based Discord bot that allows users to request movies through Discord slash commands, integrating with Overseerr to manage and process those requests. This is a simplified version of Requestrr focused on the core movie request functionality.

## Architecture Overview

### High-Level Flow

```
Discord User → Slash Command → Bot Handler → Movie Search → Display Results
                                    ↓
                              User Selection → Overseerr API → Request Movie
                                    ↓
                              Confirmation → Optional: Notification System
```

### Core Components

1. **Discord Bot Client** - Handles Discord API interactions (slash commands, buttons, selects)
2. **Overseerr Client** - Manages API calls to Overseerr for searching and requesting movies
3. **Workflow Manager** - Orchestrates the request flow (search → select → request)
4. **Settings Manager** - Handles configuration (bot token, Overseerr credentials, etc.)
5. **Notification System** (Optional) - Tracks requests and notifies users when available

## Technology Stack Recommendations

### Required Libraries

```python
# Discord Integration
discord.py >= 2.3.0  # Modern Discord API with slash command support
aiohttp >= 3.9.0     # Async HTTP for Overseerr API calls

# Data Management
pydantic >= 2.0      # Settings validation and data models
python-dotenv        # Environment variable management

# Optional but Recommended
asyncio              # Built-in async support
logging              # Built-in logging
json                 # Built-in JSON handling
```

### Installation

```bash
pip install discord.py aiohttp pydantic python-dotenv
```

## Detailed Implementation Guide

### 1. Discord Bot Setup

#### Creating the Bot Application

The current C# implementation uses DSharpPlus 4.5.0 with slash commands. In Python, use `discord.py` with the `app_commands` module.

**Key Discord Concepts:**

- **Slash Commands**: Commands that appear in Discord's command menu (e.g., `/request movie Inception`)
- **Interactions**: Discord's modern interaction system (buttons, select menus, modals)
- **Ephemeral Messages**: Responses visible only to the command user (privacy-focused)
- **Deferred Responses**: For operations taking > 3 seconds, defer then edit

#### Basic Bot Structure

```python
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MovieBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Required for some features
        
        super().__init__(
            command_prefix='!',  # Fallback, mainly using slash commands
            intents=intents
        )
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        # Load settings
        await self.load_settings()
        
        # Initialize Overseerr client
        self.overseerr = OverseerrClient(
            hostname=self.settings.overseerr_hostname,
            port=self.settings.overseerr_port,
            api_key=self.settings.overseerr_api_key,
            use_ssl=self.settings.overseerr_use_ssl
        )
        
        # Sync slash commands with Discord
        await self.tree.sync()
        logger.info("Slash commands synced")
    
    async def on_ready(self):
        """Called when bot successfully connects to Discord"""
        logger.info(f'Bot logged in as {self.user}')
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/help"
            )
        )

bot = MovieBot()
```

### 2. Settings Management

The C# implementation uses JSON files with automatic schema upgrades. For Python, use `pydantic` for type-safe settings.

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import json
import os
from pathlib import Path

class OverseerrSettings(BaseModel):
    """Overseerr connection settings"""
    hostname: str = "localhost"
    port: int = 5055
    api_key: str = ""
    use_ssl: bool = False
    default_user_id: Optional[str] = None
    
    @property
    def base_url(self) -> str:
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
    movie_roles: List[int] = Field(default_factory=list)  # Role IDs that can request movies
    enable_dm_requests: bool = False
    auto_notify_requesters: bool = True
    notification_mode: str = "PrivateMessages"  # or "Channels"
    notification_channels: List[int] = Field(default_factory=list)

class BotSettings(BaseModel):
    """Main bot settings"""
    discord: DiscordSettings = Field(default_factory=DiscordSettings)
    overseerr: OverseerrSettings = Field(default_factory=OverseerrSettings)
    movie_categories: List[MovieCategorySettings] = Field(default_factory=list)
    version: str = "1.0.0"

class SettingsManager:
    """Manages bot settings with file persistence"""
    
    def __init__(self, config_path: str = "./config/settings.json"):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings: Optional[BotSettings] = None
    
    def load(self) -> BotSettings:
        """Load settings from file or create defaults"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                self.settings = BotSettings(**data)
        else:
            # Create default settings
            self.settings = BotSettings()
            self.save()
        
        return self.settings
    
    def save(self):
        """Save current settings to file"""
        if self.settings:
            with open(self.config_path, 'w') as f:
                json.dump(
                    self.settings.model_dump(),
                    f,
                    indent=2
                )
    
    def reload(self) -> BotSettings:
        """Reload settings from file"""
        return self.load()
```

### 3. Overseerr API Client

The C# implementation shows extensive Overseerr integration. Here's the Python equivalent focusing on movie requests.

#### Core Overseerr Endpoints

Based on the C# code analysis:

- **Search**: `GET /search/?query={query}&page=1&language=en`
- **Movie Details**: `GET /movie/{tmdb_id}`
- **Request Movie**: `POST /request`
- **User Lookup**: `GET /user/{user_id}`
- **User Permissions**: `GET /user/{user_id}/settings/permissions`
- **Test Connection**: `GET /settings/main`

```python
import aiohttp
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import IntEnum

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

class MovieRequestResult:
    """Result of a movie request operation"""
    def __init__(self, was_denied: bool = False, error_message: str = ""):
        self.was_denied = was_denied
        self.error_message = error_message

class OverseerrClient:
    """Client for Overseerr API interactions"""
    
    def __init__(self, hostname: str, port: int, api_key: str, use_ssl: bool = False):
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
                    "Content-Type": "application/json"
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
                    raise Exception("Invalid hostname/port")
                
                data = await resp.json()
                
                # Verify API key matches
                if data.get("apiKey") != self.api_key:
                    raise Exception("Invalid hostname/port")
                
                return True
        except aiohttp.ClientError:
            raise Exception("Connection failed - check hostname and port")
    
    async def search_movies(self, query: str, is_4k: bool = False) -> List[Movie]:
        """
        Search for movies by title
        
        Args:
            query: Movie title to search for
            is_4k: Whether to check 4K status
            
        Returns:
            List of matching movies
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}search/"
            params = {
                "query": query,
                "page": 1,
                "language": "en"
            }
            
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    error = await resp.json()
                    raise Exception(f"Search failed: {error.get('message', 'Unknown error')}")
                
                data = await resp.json()
                results = data.get("results", [])
                
                # Filter to movies only
                movies = [
                    self._convert_movie(item, is_4k)
                    for item in results
                    if item.get("mediaType") == "movie"
                ]
                
                return movies
        except Exception as e:
            logger.error(f"Error searching movies: {e}")
            raise
    
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
    
    async def request_movie(
        self,
        tmdb_id: int,
        user_id: Optional[str] = None,
        is_4k: bool = False,
        category: Optional[MovieCategorySettings] = None
    ) -> MovieRequestResult:
        """
        Request a movie in Overseerr
        
        Args:
            tmdb_id: TheMovieDB ID
            user_id: Overseerr user ID (optional)
            is_4k: Request 4K version
            category: Movie category settings for advanced options
            
        Returns:
            MovieRequestResult indicating success/failure
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}request"
            
            # Build request payload
            payload: Dict[str, Any] = {
                "mediaId": tmdb_id,
                "mediaType": "movie",
                "is4k": is_4k
            }
            
            # Add category-specific settings if provided
            if category:
                payload.update({
                    "serverId": category.service_id,
                    "profileId": category.profile_id,
                    "rootFolder": category.root_folder,
                    "tags": category.tags
                })
            
            # Add user ID if provided
            if user_id:
                payload["userId"] = int(user_id)
            
            async with session.post(url, json=payload) as resp:
                if resp.status == 403:
                    # User doesn't have permission or quota exceeded
                    return MovieRequestResult(was_denied=True)
                elif resp.status != 201:
                    error = await resp.json()
                    return MovieRequestResult(
                        was_denied=True,
                        error_message=error.get("message", "Request failed")
                    )
                
                return MovieRequestResult()
        except Exception as e:
            logger.error(f"Error requesting movie {tmdb_id}: {e}")
            return MovieRequestResult(was_denied=True, error_message=str(e))
    
    def _convert_movie(self, data: Dict[str, Any], is_4k: bool) -> Movie:
        """Convert Overseerr JSON to Movie object"""
        media_info = data.get("mediaInfo")
        
        # Determine status based on 4K or regular
        if media_info:
            if is_4k:
                status = media_info.get("status4k", MediaStatus.UNKNOWN)
            else:
                status = media_info.get("status", MediaStatus.UNKNOWN)
            
            available = status in [MediaStatus.AVAILABLE, MediaStatus.PARTIALLY_AVAILABLE]
            requested = status in [MediaStatus.PENDING, MediaStatus.PROCESSING]
        else:
            status = MediaStatus.UNKNOWN
            available = False
            requested = False
        
        return Movie(
            tmdb_id=data.get("id"),
            title=data.get("title", "Unknown"),
            overview=data.get("overview", ""),
            release_date=data.get("releaseDate", ""),
            poster_path=data.get("posterPath"),
            available=available,
            requested=requested,
            status=status
        )
```

### 4. Workflow Implementation

The C# code uses a `MovieRequestingWorkflow` class to orchestrate the request flow. Here's the Python equivalent:

```python
from typing import Protocol, Optional

class MovieUserInterface(Protocol):
    """Interface for UI operations (Discord-specific)"""
    async def show_movie_selection(self, movies: List[Movie], category_id: int):
        """Display movie selection dropdown"""
        ...
    
    async def display_movie_details(self, movie: Movie, category_id: int):
        """Show movie details with request button"""
        ...
    
    async def display_request_success(self, movie: Movie):
        """Show success message"""
        ...
    
    async def display_request_denied(self, movie: Movie):
        """Show denial message"""
        ...
    
    async def warn_movie_already_available(self, movie: Movie):
        """Warn that movie is already available"""
        ...
    
    async def warn_no_movie_found(self, query: str):
        """Warn that no movies were found"""
        ...

@dataclass
class MovieRequest:
    """Represents a user's movie request"""
    user_id: str
    username: str
    category_id: int

class MovieRequestingWorkflow:
    """Orchestrates the movie request flow"""
    
    def __init__(
        self,
        request: MovieRequest,
        overseerr: OverseerrClient,
        ui: MovieUserInterface,
        category: Optional[MovieCategorySettings] = None
    ):
        self.request = request
        self.overseerr = overseerr
        self.ui = ui
        self.category = category or MovieCategorySettings(id=0, name="default")
    
    async def search_movie_by_name(self, movie_name: str):
        """Search for movies by title and display results"""
        # Clean up query
        movie_name = movie_name.replace(".", " ")
        
        # Search
        movies = await self.overseerr.search_movies(
            movie_name,
            is_4k=self.category.is_4k
        )
        
        if not movies:
            await self.ui.warn_no_movie_found(movie_name)
            return
        
        if len(movies) == 1:
            # Single result - show details immediately
            await self.handle_movie_selection(movies[0])
        else:
            # Multiple results - show selection UI
            await self.ui.show_movie_selection(movies, self.category.id)
    
    async def search_movie_by_id(self, tmdb_id: int):
        """Search for movie by TMDB ID and display details"""
        try:
            movie = await self.overseerr.get_movie_by_id(
                tmdb_id,
                is_4k=self.category.is_4k
            )
            await self.handle_movie_selection(movie)
        except Exception as e:
            await self.ui.warn_no_movie_found(f"TMDB ID {tmdb_id}")
    
    async def handle_movie_selection(self, movie: Movie):
        """Handle when user selects a movie"""
        if movie.available:
            await self.ui.warn_movie_already_available(movie)
        elif movie.requested:
            # Movie already requested - could add notification signup here
            await self.ui.warn_movie_already_available(movie)
        else:
            # Show details with request button
            await self.ui.display_movie_details(movie, self.category.id)
    
    async def request_movie(self, tmdb_id: int):
        """Execute the movie request"""
        # Get movie details
        movie = await self.overseerr.get_movie_by_id(
            tmdb_id,
            is_4k=self.category.is_4k
        )
        
        # Submit request to Overseerr
        result = await self.overseerr.request_movie(
            tmdb_id,
            user_id=None,  # Could map Discord user to Overseerr user
            is_4k=self.category.is_4k,
            category=self.category
        )
        
        if result.was_denied:
            await self.ui.display_request_denied(movie)
        else:
            await self.ui.display_request_success(movie)
            # Could trigger notification system here
```

### 5. Discord Slash Commands

The C# implementation dynamically compiles slash commands using Roslyn. In Python, define them statically:

```python
class MovieCommands(commands.Cog):
    """Movie request slash commands"""
    
    def __init__(self, bot: MovieBot):
        self.bot = bot
    
    @app_commands.command(name="request-movie", description="Request a movie by title")
    @app_commands.describe(title="Title of the movie to request")
    async def request_movie(
        self,
        interaction: discord.Interaction,
        title: str
    ):
        """Request a movie by title"""
        # Defer response as search might take a few seconds
        await interaction.response.defer(ephemeral=True)
        
        # Create workflow
        workflow = MovieRequestingWorkflow(
            request=MovieRequest(
                user_id=str(interaction.user.id),
                username=interaction.user.name,
                category_id=0  # Default category
            ),
            overseerr=self.bot.overseerr,
            ui=DiscordMovieUI(interaction),
            category=None  # Use default
        )
        
        # Execute search
        await workflow.search_movie_by_name(title)
    
    @app_commands.command(name="request-movie-id", description="Request a movie by TMDB ID")
    @app_commands.describe(tmdb_id="TheMovieDB ID of the movie")
    async def request_movie_id(
        self,
        interaction: discord.Interaction,
        tmdb_id: int
    ):
        """Request a movie by TMDB ID"""
        await interaction.response.defer(ephemeral=True)
        
        workflow = MovieRequestingWorkflow(
            request=MovieRequest(
                user_id=str(interaction.user.id),
                username=interaction.user.name,
                category_id=0
            ),
            overseerr=self.bot.overseerr,
            ui=DiscordMovieUI(interaction),
            category=None
        )
        
        await workflow.search_movie_by_id(tmdb_id)

# Register the cog
async def setup(bot: MovieBot):
    await bot.add_cog(MovieCommands(bot))
```

### 6. Discord UI Implementation

The C# code uses select menus and buttons extensively. Here's how to implement in Python:

```python
class DiscordMovieUI:
    """Discord-specific UI implementation"""
    
    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
    
    async def show_movie_selection(self, movies: List[Movie], category_id: int):
        """Display dropdown of movies"""
        # Create select options (max 25)
        options = []
        for movie in movies[:25]:
            label = self._format_movie_title(movie)
            value = f"{category_id}/{movie.tmdb_id}"
            options.append(discord.SelectOption(label=label, value=value))
        
        # Create select menu
        select = discord.ui.Select(
            custom_id=f"movie_select:{self.interaction.user.id}:{category_id}",
            placeholder="Choose a movie...",
            options=options
        )
        
        view = discord.ui.View()
        view.add_item(select)
        
        await self.interaction.edit_original_response(
            content="Please select a movie:",
            view=view
        )
    
    async def display_movie_details(self, movie: Movie, category_id: int):
        """Show movie details with request button"""
        # Create embed
        embed = discord.Embed(
            title=movie.title,
            description=movie.overview[:500] if movie.overview else "No description available",
            color=discord.Color.blue()
        )
        
        if movie.release_year:
            embed.add_field(name="Release Year", value=movie.release_year)
        
        if movie.poster_url:
            embed.set_thumbnail(url=movie.poster_url)
        
        # Create request button
        button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Request",
            custom_id=f"movie_request:{self.interaction.user.id}:{category_id}:{movie.tmdb_id}"
        )
        
        view = discord.ui.View()
        view.add_item(button)
        
        await self.interaction.edit_original_response(
            content="Here are the details:",
            embed=embed,
            view=view
        )
    
    async def display_request_success(self, movie: Movie):
        """Show success message"""
        embed = discord.Embed(
            title="✅ Request Submitted",
            description=f"**{movie.title}** has been requested successfully!",
            color=discord.Color.green()
        )
        
        await self.interaction.edit_original_response(
            content=None,
            embed=embed,
            view=None
        )
    
    async def display_request_denied(self, movie: Movie):
        """Show denial message"""
        embed = discord.Embed(
            title="❌ Request Denied",
            description=f"Your request for **{movie.title}** was denied. You may have exceeded your quota or lack permissions.",
            color=discord.Color.red()
        )
        
        await self.interaction.edit_original_response(
            content=None,
            embed=embed,
            view=None
        )
    
    async def warn_movie_already_available(self, movie: Movie):
        """Warn movie is available"""
        status = "already available" if movie.available else "already requested"
        embed = discord.Embed(
            title="ℹ️ Already Exists",
            description=f"**{movie.title}** is {status}.",
            color=discord.Color.orange()
        )
        
        await self.interaction.edit_original_response(
            content=None,
            embed=embed,
            view=None
        )
    
    async def warn_no_movie_found(self, query: str):
        """Warn no results"""
        embed = discord.Embed(
            title="❌ No Results",
            description=f"No movies found matching: **{query}**",
            color=discord.Color.red()
        )
        
        await self.interaction.edit_original_response(
            content=None,
            embed=embed,
            view=None
        )
    
    def _format_movie_title(self, movie: Movie) -> str:
        """Format movie title for display"""
        if movie.release_year:
            title = f"{movie.title} ({movie.release_year})"
        else:
            title = movie.title
        
        # Truncate if too long (max 100 chars for select options)
        if len(title) > 97:
            title = title[:94] + "..."
        
        return title
```

### 7. Interaction Handlers

The C# code handles button/select interactions via `ComponentInteractionCreated` event. In Python:

```python
@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Handle all interactions (buttons, selects)"""
    if interaction.type != discord.InteractionType.component:
        return
    
    custom_id = interaction.data.get("custom_id", "")
    
    # Parse custom_id to determine action
    # Format: "action:user_id:category_id:tmdb_id"
    parts = custom_id.split(":")
    if len(parts) < 2:
        return
    
    action = parts[0]
    expected_user_id = parts[1]
    
    # Verify user
    if str(interaction.user.id) != expected_user_id:
        await interaction.response.send_message(
            "This interaction is not for you!",
            ephemeral=True
        )
        return
    
    # Handle movie selection
    if action == "movie_select":
        await interaction.response.defer()
        
        # Get selected value
        selected = interaction.data.get("values", [])[0]
        category_id, tmdb_id = selected.split("/")
        
        # Create workflow and handle selection
        workflow = MovieRequestingWorkflow(
            request=MovieRequest(
                user_id=str(interaction.user.id),
                username=interaction.user.name,
                category_id=int(category_id)
            ),
            overseerr=bot.overseerr,
            ui=DiscordMovieUI(interaction)
        )
        
        movie = await bot.overseerr.get_movie_by_id(int(tmdb_id))
        await workflow.handle_movie_selection(movie)
    
    # Handle movie request button
    elif action == "movie_request":
        await interaction.response.defer()
        
        category_id = int(parts[2])
        tmdb_id = int(parts[3])
        
        # Create workflow and execute request
        workflow = MovieRequestingWorkflow(
            request=MovieRequest(
                user_id=str(interaction.user.id),
                username=interaction.user.name,
                category_id=category_id
            ),
            overseerr=bot.overseerr,
            ui=DiscordMovieUI(interaction)
        )
        
        await workflow.request_movie(tmdb_id)
```

### 8. Complete Main Application

```python
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def main():
    """Main entry point"""
    # Create bot
    bot = MovieBot()
    
    # Load settings
    settings_manager = SettingsManager()
    bot.settings = settings_manager.load()
    
    # Validate configuration
    if not bot.settings.discord.bot_token:
        logger.error("Discord bot token not configured!")
        return
    
    if not bot.settings.overseerr.api_key:
        logger.error("Overseerr API key not configured!")
        return
    
    # Test Overseerr connection
    try:
        await bot.overseerr.test_connection()
        logger.info("Overseerr connection successful")
    except Exception as e:
        logger.error(f"Overseerr connection failed: {e}")
        return
    
    # Load cogs
    await bot.load_extension("movie_commands")  # Assuming commands in movie_commands.py
    
    # Run bot
    try:
        await bot.start(bot.settings.discord.bot_token)
    finally:
        await bot.overseerr.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### 9. Configuration File Structure

Create a `config/settings.json`:

```json
{
  "version": "1.0.0",
  "discord": {
    "bot_token": "YOUR_BOT_TOKEN",
    "client_id": "YOUR_CLIENT_ID",
    "monitored_channels": [],
    "movie_roles": [],
    "enable_dm_requests": false,
    "auto_notify_requesters": true,
    "notification_mode": "PrivateMessages",
    "notification_channels": []
  },
  "overseerr": {
    "hostname": "localhost",
    "port": 5055,
    "api_key": "YOUR_OVERSEERR_API_KEY",
    "use_ssl": false,
    "default_user_id": null
  },
  "movie_categories": [
    {
      "id": 0,
      "name": "1080p",
      "is_4k": false,
      "service_id": 1,
      "profile_id": 1,
      "root_folder": "/movies",
      "tags": []
    }
  ]
}
```

## Key Differences from C# Implementation

### 1. **No Dynamic Compilation**
- C# uses Roslyn to dynamically compile slash commands
- Python defines commands statically in code
- Benefit: Simpler, more maintainable
- Tradeoff: Requires bot restart to change commands

### 2. **Async/Await Everywhere**
- Discord.py is fully async
- All I/O operations use `await`
- Use `asyncio` for concurrency

### 3. **Type Hints vs. Strong Typing**
- Python uses type hints (optional but recommended)
- Pydantic provides runtime validation
- Less strict than C# but still type-safe

### 4. **No Settings Polling**
- C# polls settings every second and restarts
- Python: Manual reload or signal handling
- Consider using file watchers for auto-reload

### 5. **Simpler Notification System**
- C# has three separate notification engines
- Python: Can implement as async background tasks
- Use `discord.ext.tasks` for scheduled checks

## Advanced Features (Optional)

### Notification System

```python
from discord.ext import tasks

class NotificationManager:
    """Manages user notifications for requested content"""
    
    def __init__(self, bot: MovieBot, notifications_file: str = "./config/notifications.json"):
        self.bot = bot
        self.notifications_file = notifications_file
        self.notifications: Dict[str, List[int]] = {}  # user_id -> [tmdb_ids]
        self.load_notifications()
    
    def load_notifications(self):
        """Load notifications from file"""
        path = Path(self.notifications_file)
        if path.exists():
            with open(path, 'r') as f:
                self.notifications = json.load(f)
    
    def save_notifications(self):
        """Save notifications to file"""
        with open(self.notifications_file, 'w') as f:
            json.dump(self.notifications, f, indent=2)
    
    def add_notification(self, user_id: str, tmdb_id: int):
        """Add notification for user"""
        if user_id not in self.notifications:
            self.notifications[user_id] = []
        
        if tmdb_id not in self.notifications[user_id]:
            self.notifications[user_id].append(tmdb_id)
            self.save_notifications()
    
    @tasks.loop(minutes=10)
    async def check_availability(self):
        """Check if requested movies are now available"""
        if not self.notifications:
            return
        
        # Get all unique tmdb_ids
        all_tmdb_ids = set()
        for tmdb_ids in self.notifications.values():
            all_tmdb_ids.update(tmdb_ids)
        
        # Check each movie
        for tmdb_id in all_tmdb_ids:
            try:
                movie = await self.bot.overseerr.get_movie_by_id(tmdb_id)
                
                if movie.available:
                    # Notify all users watching this movie
                    await self.notify_users(movie)
            except Exception as e:
                logger.error(f"Error checking movie {tmdb_id}: {e}")
    
    async def notify_users(self, movie: Movie):
        """Notify users that a movie is available"""
        notified_users = []
        
        for user_id, tmdb_ids in self.notifications.items():
            if movie.tmdb_id in tmdb_ids:
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    
                    embed = discord.Embed(
                        title="🎬 Movie Available!",
                        description=f"**{movie.title}** is now available to watch!",
                        color=discord.Color.green()
                    )
                    
                    if movie.poster_url:
                        embed.set_thumbnail(url=movie.poster_url)
                    
                    await user.send(embed=embed)
                    notified_users.append(user_id)
                except Exception as e:
                    logger.error(f"Error notifying user {user_id}: {e}")
        
        # Remove notifications for notified users
        for user_id in notified_users:
            self.notifications[user_id].remove(movie.tmdb_id)
            if not self.notifications[user_id]:
                del self.notifications[user_id]
        
        if notified_users:
            self.save_notifications()
```

### Role/Channel Restrictions

```python
from discord import app_commands
from typing import List

def has_movie_role():
    """Check decorator for movie roles"""
    async def predicate(interaction: discord.Interaction) -> bool:
        bot = interaction.client
        allowed_roles = bot.settings.discord.movie_roles
        
        if not allowed_roles:
            return True  # No restrictions
        
        user_roles = [role.id for role in interaction.user.roles]
        return any(role_id in user_roles for role_id in allowed_roles)
    
    return app_commands.check(predicate)

def in_monitored_channel():
    """Check decorator for monitored channels"""
    async def predicate(interaction: discord.Interaction) -> bool:
        bot = interaction.client
        monitored = bot.settings.discord.monitored_channels
        
        if not monitored:
            return True  # No restrictions
        
        return interaction.channel_id in monitored
    
    return app_commands.check(predicate)

# Usage:
@app_commands.command()
@has_movie_role()
@in_monitored_channel()
async def request_movie(interaction: discord.Interaction, title: str):
    """Request a movie (role and channel restricted)"""
    pass
```

## Project Structure

```
movie-request-bot/
├── config/
│   ├── settings.json
│   └── notifications.json
├── bot/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── settings.py             # Settings models
│   ├── overseerr.py            # Overseerr client
│   ├── workflows.py            # Request workflows
│   ├── ui.py                   # Discord UI components
│   ├── commands.py             # Slash commands
│   └── notifications.py        # Notification system
├── .env                        # Environment variables
├── requirements.txt
└── README.md
```

## Testing Checklist

1. **Bot Connection**
   - [ ] Bot connects to Discord
   - [ ] Slash commands appear in Discord
   - [ ] Bot status shows correctly

2. **Overseerr Integration**
   - [ ] Connection test passes
   - [ ] Movie search returns results
   - [ ] Movie details display correctly
   - [ ] Requests submit successfully

3. **Discord UI**
   - [ ] Search returns dropdown (multiple results)
   - [ ] Search shows details (single result)
   - [ ] Movie details embed displays properly
   - [ ] Request button works
   - [ ] Success/error messages show

4. **Error Handling**
   - [ ] Invalid TMDB ID handled
   - [ ] No results handled
   - [ ] Already available/requested handled
   - [ ] Overseerr errors handled gracefully

## Common Issues & Solutions

### Issue: Slash commands don't appear
- **Cause**: Commands not synced or missing bot permissions
- **Solution**: Ensure `bot.tree.sync()` is called and bot has `applications.commands` scope

### Issue: Interactions time out
- **Cause**: Response takes > 3 seconds
- **Solution**: Use `await interaction.response.defer()` immediately

### Issue: "Unknown interaction" error
- **Cause**: Bot restarted and lost interaction context
- **Solution**: Persist interaction data or handle gracefully

### Issue: Overseerr requests fail silently
- **Cause**: Missing permissions or quota exceeded
- **Solution**: Check Overseerr user permissions and quota settings

## Performance Considerations

1. **Use connection pooling**: Single `aiohttp.ClientSession` for all Overseerr calls
2. **Cache movie posters**: Avoid repeated TMDB image requests
3. **Limit search results**: Max 25 for select menus (Discord limit)
4. **Debounce notifications**: Check availability every 10-15 minutes, not every second

## Security Best Practices

1. **Never commit tokens**: Use environment variables or config files in `.gitignore`
2. **Validate user input**: Sanitize movie titles, limit query length
3. **Use ephemeral responses**: Keep user requests private
4. **Rate limit**: Prevent spam with cooldowns
5. **Validate interactions**: Check user_id matches expected user

## Next Steps

1. Implement the basic bot structure
2. Add Overseerr client and test connection
3. Create workflow for movie search
4. Implement Discord UI components
5. Add slash commands
6. Test end-to-end flow
7. Add notification system (optional)
8. Deploy and monitor

## Resources

- **Discord.py Documentation**: https://discordpy.readthedocs.io/
- **Overseerr API**: https://api-docs.overseerr.dev/
- **Discord Developer Portal**: https://discord.com/developers/applications
- **Pydantic Documentation**: https://docs.pydantic.dev/

This implementation provides a solid foundation for a Python-based Discord movie request bot. Start with the core functionality (search and request) and iterate from there!
