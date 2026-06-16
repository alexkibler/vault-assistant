FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for markdown processing and file watching
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY pyproject.toml uv.lock ./
COPY . .

# Install Python dependencies
RUN uv sync --no-dev

# Create cache directory for LanceDB
RUN mkdir -p /app/.lancedb

# Expose API port
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8765/health || exit 1

# Default: run API server
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765"]
