# Discord Overseerr Bot

A containerized Discord bot that integrates with Overseerr to enable movie and TV show requests through Discord slash commands.

## Features

- 🎬 Request movies via Discord slash commands
- 🔍 Search and browse movie results
- ✅ Check movie availability status
- 🐳 Fully containerized with Docker
- ⚙️ Environment-based configuration
- 📦 Built with Python and `uv` for fast dependency management

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Discord Bot Token ([Create one here](https://discord.com/developers/applications))
- Overseerr instance with API access

### Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd discord-overseerr
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your credentials:
   ```env
   DISCORD_BOT_TOKEN=your_bot_token_here
   DISCORD_CLIENT_ID=your_client_id_here
   OVERSEERR_API_KEY=your_overseerr_api_key_here
   OVERSEERR_HOSTNAME=your_overseerr_host
   ```

3. **Start the bot**
   ```bash
   docker-compose up -d
   ```

4. **Check logs**
   ```bash
   docker-compose logs -f
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_BOT_TOKEN` | Discord bot token | Required |
| `DISCORD_CLIENT_ID` | Discord application client ID | Required |
| `OVERSEERR_HOSTNAME` | Overseerr server hostname | `localhost` |
| `OVERSEERR_PORT` | Overseerr server port | `5055` |
| `OVERSEERR_API_KEY` | Overseerr API key | Required |
| `OVERSEERR_USE_SSL` | Use HTTPS for Overseerr | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Advanced Configuration

Edit `config/settings.json` for advanced settings:

- **Monitored Channels**: Restrict bot to specific channels
- **Role Restrictions**: Limit access by Discord roles
- **Movie Categories**: Configure 4K vs 1080p options
- **Notification Settings**: Configure request notifications

## Usage

### Slash Commands

- `/request <title>` - Search and request a movie

### Example

1. Type `/request The Matrix`
2. Select the correct movie from the dropdown (if multiple results)
3. Review movie details
4. Click "Request This Movie" button
5. Receive confirmation

## Development

### Local Development (without Docker)

1. **Install dependencies with uv**
   ```bash
   # Install uv if you haven't
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Install dependencies
   uv pip install -r requirements.txt
   ```

2. **Run the bot**
   ```bash
   python -m bot.main
   ```

### Development with Docker

Use the development compose file for live code reloading:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Project Structure

```
discord-overseerr/
├── bot/
│   ├── __init__.py
│   ├── main.py              # Application entry point
│   ├── settings.py          # Configuration management
│   ├── overseerr.py         # Overseerr API client
│   └── cogs/
│       ├── __init__.py
│       └── movie_commands.py # Movie request commands
├── config/
│   └── settings.json        # Bot configuration
├── docs/
│   └── python.md           # Implementation guide
├── logs/                    # Application logs
├── .env                     # Environment variables (not in git)
├── .env.example            # Example environment file
├── docker-compose.yml      # Production compose file
├── docker-compose.dev.yml  # Development compose file
├── Dockerfile              # Container image
├── pyproject.toml          # Python project metadata
└── requirements.txt        # Python dependencies
```

## Docker Commands

```bash
# Start the bot
docker-compose up -d

# Stop the bot
docker-compose down

# View logs
docker-compose logs -f discord-bot

# Restart the bot
docker-compose restart discord-bot

# Rebuild after code changes
docker-compose up -d --build

# Remove everything (including volumes)
docker-compose down -v
```

## Troubleshooting

### Bot doesn't respond to commands

1. Check bot is online in Discord
2. Verify bot has proper permissions in your server
3. Ensure slash commands are synced (check logs for "Synced X command(s)")
4. Check logs: `docker-compose logs -f`

### Overseerr connection fails

1. Verify Overseerr is accessible from the bot container
2. Check API key is correct
3. Verify hostname/port settings
4. If Overseerr is on the host machine, use `host.docker.internal` instead of `localhost`

### Commands don't appear in Discord

1. Ensure bot has `applications.commands` scope
2. Wait a few minutes for Discord to sync commands
3. Try kicking and re-inviting the bot
4. Check bot logs for sync errors

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [discord.py](https://github.com/Rapptz/discord.py)
- Integrates with [Overseerr](https://overseerr.dev/)
- Dependency management by [uv](https://github.com/astral-sh/uv)
