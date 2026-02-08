# Discord Overseerr Bot

A containerized Discord bot that integrates with Overseerr to enable movie and TV show requests through Discord slash commands.

## Features

- 🎬 Request movies via Discord slash commands
- 🔍 Search and browse movie results
- ✅ Check movie availability status
- 🐳 Fully containerized with Docker
- ⚙️ Environment-based configuration
- 📦 Built with Python and `uv` for fast dependency management

## Quick Start Guide

This guide will walk you through setting up the bot from scratch, even if you've never created a Discord bot before.

### Prerequisites

- Docker and Docker Compose installed on your machine
- A Discord account and server where you have admin permissions
- An Overseerr instance (can be local or remote)

---

## Part 1: Creating Your Discord Bot

### Step 1: Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** in the top right
3. Give your application a name (e.g., "Movie Request Bot")
4. Accept the Terms of Service and click **"Create"**

### Step 2: Configure Your Bot

1. In the left sidebar, click **"Bot"**
2. Click **"Add Bot"** and confirm by clicking **"Yes, do it!"**
3. Under the bot's username, you'll see a **"Token"** section
   - Click **"Reset Token"** and then **"Copy"**
   - **⚠️ IMPORTANT**: Save this token somewhere safe! You'll need it later and can't view it again without resetting
   - This is your `DISCORD_BOT_TOKEN`

4. Scroll down to **"Privileged Gateway Intents"**
   - Enable **"Message Content Intent"** (required for the bot to work properly)
   - Click **"Save Changes"**

### Step 3: Get Your Application ID

1. In the left sidebar, click **"General Information"**
2. Under **"Application ID"**, click **"Copy"**
   - This is your `DISCORD_CLIENT_ID`

### Step 4: Set Bot Permissions

1. In the left sidebar, click **"OAuth2"** → **"URL Generator"**
2. In the **"Scopes"** section, check:
   - ✅ `bot`
   - ✅ `applications.commands`

3. In the **"Bot Permissions"** section that appears below, check:
   - ✅ **Read Messages/View Channels**
   - ✅ **Send Messages**
   - ✅ **Embed Links**
   - ✅ **Attach Files**
   - ✅ **Read Message History**
   - ✅ **Use Slash Commands**

4. Scroll down and copy the **"Generated URL"** at the bottom

### Step 5: Invite the Bot to Your Server

1. Paste the URL you copied into your browser
2. Select the server you want to add the bot to from the dropdown
3. Click **"Continue"**
4. Review the permissions and click **"Authorize"**
5. Complete the CAPTCHA if prompted

✅ Your bot should now appear in your Discord server (offline until you start it)!

---

## Part 2: Setting Up Overseerr Integration

### Step 1: Access Your Overseerr Instance

1. Open your Overseerr web interface (e.g., `http://localhost:5055` or your remote URL)
2. Log in with your admin account

### Step 2: Generate an API Key

1. Click on your profile picture in the top right
2. Select **"Settings"** from the dropdown
3. In the left sidebar, click **"General"**
4. Scroll down to the **"API Key"** section
5. Click **"Generate"** if you don't have a key, or copy your existing key
   - This is your `OVERSEERR_API_KEY`

### Step 3: Note Your Overseerr Connection Details

You'll need:
- **Hostname**: The IP address or domain name of your Overseerr instance
  - If running on the same machine as the bot: `host.docker.internal` (Docker) or `localhost` (local dev)
  - If running on another machine: the IP address (e.g., `192.168.1.100`) or domain name
- **Port**: Usually `5055` (default Overseerr port)
- **SSL**: Whether you're using HTTPS (`true`) or HTTP (`false`)

---

## Part 3: Deploying the Bot

### Step 1: Clone and Configure

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd discord-overseerr
   ```

2. **Create your environment file**
   ```bash
   cp .env.example .env
   ```

3. **Edit the `.env` file** with your actual credentials:
   ```bash
   nano .env  # or use your preferred editor
   ```

   Fill in the values you collected:
   ```env
   # From Discord Developer Portal
   DISCORD_BOT_TOKEN=xxxxxxxxxx
   DISCORD_CLIENT_ID=yyyyyyy

   # From Overseerr Settings
   OVERSEERR_API_KEY=zzzzzzzz
   
   # Your Overseerr connection details
   OVERSEERR_HOSTNAME=host.docker.internal  # or your Overseerr IP/domain
   OVERSEERR_PORT=5055
   OVERSEERR_USE_SSL=false

   # Optional
   LOG_LEVEL=INFO
   TZ=America/New_York  # Your timezone
   ```

### Step 2: Start the Bot

Using Docker (recommended):
```bash
docker-compose up -d
```

Or for local development:
```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -r requirements.txt

# Run the bot
python -m bot.main
```

### Step 3: Verify It's Working

1. **Check the logs**
   ```bash
   docker-compose logs -f discord-bot
   ```

   You should see:
   ```
   ✅ Overseerr connection successful
   ✅ Synced 1 slash command(s)
   🤖 Bot logged in as Movie Request Bot
   ```

2. **Test in Discord**
   - Go to your Discord server
   - Type `/` and you should see the `/request` command appear
   - Try: `/request The Matrix`

🎉 **Congratulations!** Your bot is now running!

---

## Common Issues During Setup

### Discord Bot Issues

**Problem**: Bot appears offline
- **Solution**: Check that you started the bot with `docker-compose up -d`
- **Solution**: Check logs for errors: `docker-compose logs -f`

**Problem**: Slash commands don't appear
- **Solution**: Wait 5-10 minutes for Discord to sync commands globally
- **Solution**: Check that you enabled `applications.commands` scope when inviting the bot
- **Solution**: Try kicking and re-inviting the bot with the correct permissions

**Problem**: "Invalid Token" error
- **Solution**: Make sure you copied the token correctly without extra spaces
- **Solution**: Reset the token in the Discord Developer Portal and update your `.env` file

### Overseerr Connection Issues

**Problem**: "Overseerr connection failed"
- **Solution**: If Overseerr is on the same machine, use `OVERSEERR_HOSTNAME=host.docker.internal`
- **Solution**: If using a custom port, make sure `OVERSEERR_PORT` matches your Overseerr configuration
- **Solution**: Check that your Overseerr API key is correct

**Problem**: "Invalid API key"
- **Solution**: Regenerate the API key in Overseerr Settings → General
- **Solution**: Make sure there are no extra spaces when copying the key

**Problem**: "Connection refused"
- **Solution**: Verify Overseerr is running and accessible
- **Solution**: Test connectivity: `curl http://your-overseerr-host:5055/api/v1/settings/main`
- **Solution**: Check firewall settings if Overseerr is on a different machine

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_BOT_TOKEN` | Discord bot token | Required |
| `DISCORD_CLIENT_ID` | Discord application client ID | Required |
| `DISCORD_AUTHORIZED_USERS` | Comma-separated Discord user IDs allowed to use bot (empty = all users) | None |
| `OVERSEERR_HOSTNAME` | Overseerr server hostname | `localhost` |
| `OVERSEERR_PORT` | Overseerr server port | `5055` |
| `OVERSEERR_API_KEY` | Overseerr API key | Required |
| `OVERSEERR_USE_SSL` | Use HTTPS for Overseerr | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Advanced Configuration

Edit `config/settings.json` for advanced settings:

- **Monitored Channels**: Restrict bot to specific channels
- **Role Restrictions**: Limit access by Discord roles
- **Authorized Users**: Whitelist specific Discord users by their User ID
- **Movie Categories**: Configure 4K vs 1080p options
- **Notification Settings**: Configure request notifications

#### Setting Up User Whitelist

To restrict bot access to specific Discord users:

1. **Get Discord User IDs**: 
   - Enable Developer Mode in Discord: Settings → Advanced → Developer Mode
   - Right-click on a user and select "Copy User ID"

2. **Configure the whitelist**:
   
   **Option A - Via Environment Variable** (recommended):
   ```env
   # In your .env file
   DISCORD_AUTHORIZED_USERS=123456789012345678,987654321098765432
   ```

   **Option B - Via config/settings.json**:
   ```json
   {
     "discord": {
       "authorized_users": [123456789012345678, 987654321098765432]
     }
   }
   ```

3. **Leave empty to allow everyone**: If `authorized_users` is empty, all server members can use the bot

**Note**: Unauthorized users will receive a "Not Authorized" message when trying to use bot commands.

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

## Advanced Troubleshooting

### Permission Issues

**Problem**: Bot can't send messages in certain channels
- **Solution**: Check channel-specific permissions for the bot role
- **Solution**: Ensure the bot role is not below roles that restrict access

### Request Failures

**Problem**: Movie requests fail with "Permission denied"
- **Solution**: Check that the Overseerr user account has request permissions
- **Solution**: Verify quota limits haven't been exceeded in Overseerr

**Problem**: "Movie already requested" but it's not visible
- **Solution**: Check if another user already requested it in Overseerr
- **Solution**: Verify you're checking the correct quality profile (4K vs HD)

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
