FROM python:3.12-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Copy dependency metadata first for optimal layer caching
COPY pyproject.toml uv.lock* .python-version* ./

# Install dependencies into virtualenv
RUN uv sync --no-install-project --no-dev

# Copy application source code
COPY . /app

# Sync project package
RUN uv sync --no-dev

# Place virtual environment binaries at the start of PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


