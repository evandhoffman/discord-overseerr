# Discord Overseerr Bot - AI Agent Instructions

## Architecture Overview

This is a **containerized Discord bot** that bridges Discord slash commands with Overseerr's API for movie/TV show requests. The architecture follows a clean separation of concerns:

- **bot/main.py**: Entry point; extends `discord.ext.commands.Bot` as `MovieBot` class
- **bot/overseerr.py**: API client using `aiohttp` with dataclass models (`Movie`, `MediaStatus`)
- **bot/cogs/**: Discord command handlers (currently `movie_commands.py`)
- **bot/settings.py**: Pydantic-based configuration with env var overrides
- **entrypoint.sh**: Container entrypoint that handles directory permissions before starting bot

### Key Design Patterns

**Settings Priority**: Environment variables (`DISCORD_BOT_TOKEN`, etc.) > `config/settings.json` > defaults. This hybrid approach allows Docker env vars to override file-based config (see `BotSettings.model_post_init()`).

**Async Session Management**: `OverseerrClient` maintains a single `aiohttp.ClientSession` across requests via `_get_session()`. Must call `await overseerr.close()` on shutdown (handled in `MovieBot.close()`).

**Discord UI Flow**: `/request` → `_show_movie_selection()` (dropdown) → `_show_movie_details()` (embed + button). User ownership validation in callbacks (`if interaction.user.id != original_user.id`).

**User Authorization**: Optional whitelist via `DISCORD_AUTHORIZED_USERS` (comma-separated Discord user IDs). Empty list = all users allowed. Check implemented at command level in cogs.

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
- **Primary config method**: Environment variables in `.env` file
- **Optional settings**: Edit `config/settings.json` for channels, roles, movie categories (less common)
- **Test connection**: Bot validates Overseerr API on startup in `setup_hook()`

### Docker Container Conventions
- **User/Group**: Runs as configurable UID/GID (default 3333:3333) for file permission control
- **Entrypoint**: `entrypoint.sh` ensures directories exist and are writable before starting bot
- **Volume mounts**: Config and logs persisted to host via configurable paths
- **Permissions**: If you see permission errors, ensure host directories match PUID/PGID
- **Rebuilds**: Always rebuild after Dockerfile changes: `docker-compose up -d --build`

### Discord Interaction Patterns
1. **Ephemeral responses**: All `/request` interactions use `ephemeral=True` (user-only visibility)
2. **Defer early**: Call `await interaction.response.defer()` immediately to avoid 3-second timeout
3. **Edit, don't send**: Use `interaction.edit_original_response()` after defer, not `followup.send()`

### Available Slash Commands

Currently implemented commands in `bot/cogs/movie_commands.py`:

- **`/ping`**: Bot health check (returns latency)
- **`/overseerr-health`**: Overseerr connection test (validates API access)
- **`/help`**: Display command reference
- **`/request <title>`**: Search and request movies
  - Authorization check if whitelist enabled
  - Search → select → details → request flow
  - Status indicators: available, requested, requestable

### Adding New Commands
Create a new cog in `bot/cogs/`:
```python
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger(__name__)

class NewCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="command", description="...")
    async def my_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Authorization check (if needed)
        authorized_users = self.bot.settings.discord.authorized_users
        if authorized_users and interaction.user.id not in authorized_users:
            await interaction.followup.send("Not authorized", ephemeral=True)
            return
        
        # Use self.bot.overseerr to access API client
        # Use self.bot.settings for configuration
        
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

### Environment Variables

**Required**:
```bash
DISCORD_BOT_TOKEN=...           # From Discord Developer Portal
DISCORD_CLIENT_ID=...           # Application ID
OVERSEERR_API_KEY=...           # From Overseerr Settings > General
OVERSEERR_HOSTNAME=...          # Use host.docker.internal for local Overseerr
```

**Optional**:
```bash
DISCORD_AUTHORIZED_USERS=...    # Comma-separated user IDs (empty = all users)
OVERSEERR_PORT=5055            # Default port
OVERSEERR_USE_SSL=false        # Use HTTPS
LOG_LEVEL=INFO                 # DEBUG, INFO, WARNING, ERROR
TZ=UTC                         # Timezone
PUID=3333                      # User ID for container
PGID=3333                      # Group ID for container
CONFIG_PATH=./config           # Config mount path
LOGS_PATH=./logs               # Logs mount path
```

All settings are configurable via `docker-compose.yml` and `.env` file. The bot creates `config/settings.json` at runtime with merged configuration.

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

**Commands not syncing**: Check `setup_hook()` logs for "Synced X command(s)". Discord can take 1-5 minutes to propagate globally. Try `/ping` first as it's always available.

**Overseerr 404 errors**: Verify `OVERSEERR_HOSTNAME` doesn't include protocol (no `http://`). Port defaults to 5055. Use `/overseerr-health` command to test connection.

**Session closed warnings**: If seeing `aiohttp` session warnings, ensure `bot.close()` is called on shutdown (handled by async context manager in `main()`).

**Permission denied errors**: 
- Check PUID/PGID match your host user: `id -u` and `id -g`
- Ensure host directories exist and are owned by PUID:PGID
- Entrypoint script should handle most cases automatically

**Unauthorized users**: Users not in `DISCORD_AUTHORIZED_USERS` will see "🚫 Not Authorized" message. Check logs for unauthorized access attempts.

**Container restart loops**: Check logs with `docker-compose logs -f`. Common causes:
- Invalid Discord token
- Missing required environment variables
- File permission issues
