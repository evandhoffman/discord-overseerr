# Stage 1: Build with dependencies
FROM chainguard/python:latest-dev as builder

WORKDIR /app

# Copy dependency files
COPY pyproject.toml requirements.txt ./

# Create virtual environment and install dependencies using uv
RUN python -m venv /app/venv && \
    . /app/venv/bin/activate && \
    pip install --upgrade pip>=25.0 wheel>=0.46.2 && \
    pip install uv && \
    uv pip install --no-cache -r requirements.txt

# Create directories for runtime data
RUN mkdir -p /app/config /app/logs

# Stage 2: Minimal runtime
FROM chainguard/python:latest

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/venv/bin:$PATH"

# Copy virtual environment from builder
COPY --from=builder /app/venv /app/venv

# Copy directories from builder
COPY --from=builder /app/config /app/config
COPY --from=builder /app/logs /app/logs

# Copy application code
COPY bot/ ./bot/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the bot
# Note: Chainguard images run as 'nonroot' user (UID 65532) by default
# If you need to adjust host directory permissions, use: chown -R 65532:65532 ./config ./logs
# Override entrypoint to use venv's python instead of system python
ENTRYPOINT ["/app/venv/bin/python"]
CMD ["-m", "bot.main"]
