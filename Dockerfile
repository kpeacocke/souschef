# Dockerfile for SousChef UI
FROM python:3.14-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# Install system dependencies and create non-root user
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Install Python dependencies
FROM base AS dependencies

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install Poetry
RUN pip install poetry==1.8.3

# Configure poetry
RUN poetry config virtualenvs.create false

# Install dependencies (including UI extras)
RUN poetry install --only=main --extras=ui --no-dev

# Production stage
FROM base AS production

# Copy installed dependencies from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY souschef/ ./souschef/

# Copy Streamlit configuration
COPY .streamlit/ ./.streamlit/

# Change ownership to non-root user
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python souschef/ui/health_check.py

# Default command
CMD ["streamlit", "run", "souschef/ui/app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
