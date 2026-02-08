# Discord Overseerr Bot - AI Agent Instructions

## Architecture Overview

This is a **containerized Discord bot** that bridges Discord slash commands with Overseerr's API for movie/TV show requests. The architecture follows a clean separation of concerns:

- **bot/main.py**: Entry point; extends `discord.ext.commands.Bot` as `MovieBot` class
- **bot/overseerr.py**: API client using `aiohttp` with dataclass models (`Movie`, `MediaStatus`)
- **bot/cogs/**: Discord command handlers (currently `movie_commands.py`)
- **bot/settings.py**: Pydantic-based configuration with env var overrides

### Key Design Patterns

**Settings Priority**: Environment variables (`DISCORD_BOT_TOKEN`, etc.) > `config/settings.json` > defaults. This hybrid approach allows Docker env vars to override file-based config (see `BotSettings.model_post_init()`).

**Async Session Management**: `OverseerrClient` maintains a single `aiohttp.ClientSession` across requests via `_get_session()`. Must call `await overseerr.close()` on shutdown (handled in `MovieBot.close()`).

**Discord UI Flow**: `/request` → `_show_movie_selection()` (dropdown) → `_show_movie_details()` (embed + button). User ownership validation in callbacks (`if interaction.user.id != original_user.id`).

## Development Commands

### Local Development (Preferred)
```bash
# Install uv package manager (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -r requirements.txt

# Run bot directly
python -m bot.main
```

### Docker Development (Live Reload)
```bash
# Use dev compose overlay
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# View logs
docker-compose logs -f discord-bot
```

### Production Deployment
```bash
docker-compose up -d --build
docker-compose restart discord-bot  # After config changes
```

## Project-Specific Conventions

### Configuration Management
- **Never commit secrets**: Use `.env` (gitignored) or Docker env vars
- **Optional settings**: Edit `config/settings.json` for channels, roles, movie categories
- **Test connection**: Bot validates Overseerr API on startup in `setup_hook()`

### Discord Interaction Patterns
1. **Ephemeral responses**: All `/request` interactions use `ephemeral=True` (user-only visibility)
2. **Defer early**: Call `await interaction.response.defer()` immediately to avoid 3-second timeout
3. **Edit, don't send**: Use `interaction.edit_original_response()` after defer, not `followup.send()`

### Adding New Commands
Create a new cog in `bot/cogs/`:
```python
from discord.ext import commands
from discord import app_commands

class NewCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="command", description="...")
    async def my_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # Use self.bot.overseerr to access API client
        
async def setup(bot):
    await bot.add_cog(NewCommands(bot))
```

Then register in `bot/main.py` extensions list.

### Overseerr API Integration
- **Base URL construction**: `OverseerrClient.base_url` handles protocol/port (see `@property`)
- **4K support**: Pass `is_4k=True` to check/request UHD versions (uses `status4k` field)
- **Media status**: Use `MediaStatus` enum (1=UNKNOWN, 2=PENDING, 5=AVAILABLE)
- **Error handling**: API returns 403 for quota/permission issues, 404 for not found

### Logging
- **File location**: All logs write to `logs/bot.log` (Docker volume-mounted)
- **Format**: Timestamp + name + level + message (configured in `main.py`)
- **Log emoji**: Use ✅ for success, ❌ for errors, ⚠️ for warnings in log messages

## Critical Integration Points

### Environment Variables (Required)
```bash
DISCORD_BOT_TOKEN=...      # From Discord Developer Portal
DISCORD_CLIENT_ID=...      # Application ID
OVERSEERR_API_KEY=...      # From Overseerr Settings > General
OVERSEERR_HOSTNAME=...     # Use host.docker.internal for local Overseerr
```

### Overseerr API Endpoints Used
- `GET /api/v1/search` - Movie/TV search
- `GET /api/v1/movie/{tmdb_id}` - Movie details
- `POST /api/v1/request` - Submit request
- `GET /api/v1/settings/main` - Connection test

### Discord Permissions Required
Bot needs `applications.commands` scope with permissions:
- Read Messages/View Channels
- Send Messages
- Embed Links
- Attach Files

## Troubleshooting Patterns

**Commands not syncing**: Check `setup_hook()` logs for "Synced X command(s)". Discord can take 1-5 minutes to propagate globally.

**Overseerr 404 errors**: Verify `OVERSEERR_HOSTNAME` doesn't include protocol (no `http://`). Port defaults to 5055.

**Session closed warnings**: If seeing `aiohttp` session warnings, ensure `bot.close()` is called on shutdown (handled by async context manager in `main()`).
