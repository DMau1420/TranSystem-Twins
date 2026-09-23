FROM python:3.14-slim

# Install SUMO, tools and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    sumo \
    sumo-tools \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# SUMO environment variables
ENV SUMO_HOME=/usr/share/sumo \
    PYTHONPATH=/usr/share/sumo/tools:$PYTHONPATH \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependency specifications first
COPY pyproject.toml uv.lock* .python-version* ./

# Install project dependencies
RUN uv sync --no-install-project --no-dev

# Copy application source code
COPY . /app

# Sync project
RUN uv sync --no-dev

# Place virtual environment binaries in PATH
ENV PATH="/app/.venv/bin:$PATH"

CMD ["uv", "run", "python", "main.py"]
