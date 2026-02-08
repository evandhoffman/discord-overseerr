FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Set working directory
WORKDIR /app

# Build arguments for user configuration
ARG PUID=3333
ARG PGID=3333

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# Install system dependencies (if needed)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml requirements.txt ./

# Install Python dependencies using uv
RUN uv pip install --no-cache -r requirements.txt

# Copy application code
COPY bot/ ./bot/

# Create directories for runtime data
RUN mkdir -p /app/config /app/logs

# Create non-root user for security
RUN groupadd -g ${PGID} botuser && \
    useradd -m -u ${PUID} -g ${PGID} botuser && \
    chown -R botuser:botuser /app

USER botuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the bot
CMD ["python", "-m", "bot.main"]
