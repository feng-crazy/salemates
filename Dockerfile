# =============================================================================
# SalesMate Docker Image
# =============================================================================
# Build: docker build -t salesmate:latest .
# Run:   docker run -d salesmate:latest
# =============================================================================

# -----------------------------------------------------------------------------
# Base Stage - Python runtime
# -----------------------------------------------------------------------------
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.8.4

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

WORKDIR /app

# -----------------------------------------------------------------------------
# Dependencies Stage - Install Python packages
# -----------------------------------------------------------------------------
FROM base as deps

# Copy only dependency files first for better caching
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main

# -----------------------------------------------------------------------------
# Production Stage
# -----------------------------------------------------------------------------
FROM base as production

# Copy installed dependencies
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create workspace directory
RUN mkdir -p /app/workspace

# Install the application in editable mode
RUN pip install --no-cache-dir -e .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose ports
EXPOSE 18790 18791

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:18790/health || exit 1

# Default command
CMD ["salesmate", "gateway"]