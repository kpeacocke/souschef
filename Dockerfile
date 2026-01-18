# Dockerfile for SousChef UI
FROM python:3.14.1-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_ENABLE_CORS=true \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true \
    STREAMLIT_SERVER_ENABLE_STATIC_SERVING=false \
    STREAMLIT_LOGGER_LEVEL=INFO \
    STREAMLIT_SERVER_LOGGER_LEVEL=INFO

# Install system dependencies and create non-root user
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash --uid 1001 app \
    && mkdir -p /app \
    && chown -R app:app /app

# Set work directory
WORKDIR /app

# Build stage for dependencies
FROM base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.3

# Configure poetry
RUN poetry config virtualenvs.create false

# Install dependencies (including UI extras)
RUN poetry install --only=main --extras=ui --no-dev

# Production stage
FROM base AS production

# Copy installed dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY souschef/ ./souschef/

# Copy Streamlit configuration
COPY .streamlit/ ./.streamlit/

# Change ownership to non-root user
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 9999

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python souschef/ui/health_check.py

# Default command
CMD ["streamlit", "run", "souschef/ui/app.py", "--server.address", "0.0.0.0", "--server.port", "9999", "--logger.level", "debug", "--server.headless", "true"]
