FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Create virtual environment and install dependencies (production only)
RUN uv sync --frozen --no-dev

# Copy backend source
COPY backend/ ./backend/

# Copy and make startup script executable
COPY backend/scripts/startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Set Python path
ENV PYTHONPATH=/app/backend

# Expose port
EXPOSE 8000

# Health check with longer start period for migration
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use startup script as entrypoint
ENTRYPOINT ["/app/startup.sh"]
# Default command for production
CMD ["uv", "run", "uvicorn", "kiremisu.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]