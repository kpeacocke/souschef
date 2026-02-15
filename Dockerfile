# Multi-stage Dockerfile for SousChef UI - Production Ready
# Optimised for security, robustness, and Docker registry publishing

ARG PYTHON_VERSION=3.14
ARG POETRY_VERSION=2.3.2

# ============================================================================
# Base Stage - Common configuration for all stages
# ============================================================================
FROM python:${PYTHON_VERSION}-alpine AS base

ARG PYTHON_VERSION

# Metadata for Docker registry and CI/CD
LABEL org.opencontainers.image.title="SousChef" \
      org.opencontainers.image.description="Web UI for converting Chef cookbooks to Ansible playbooks" \
      org.opencontainers.image.authors="SousChef Contributors" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="SousChef Project" \
      org.opencontainers.image.url="https://github.com/kpeacocke/souschef" \
      org.opencontainers.image.documentation="https://kpeacocke.github.io/souschef/" \
      org.opencontainers.image.source="https://github.com/kpeacocke/souschef" \
      org.opencontainers.image.base.name="python:${PYTHON_VERSION}-alpine"

# Set environment variables for Python and Streamlit
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
    STREAMLIT_SERVER_LOGGER_LEVEL=INFO \
    STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200

# Install runtime dependencies only (Alpine)
RUN apk add --no-cache \
    ca-certificates \
    curl \
    # Runtime libraries (not -dev packages)
    libffi \
    libpq \
    && addgroup -g 1001 -S app \
    && adduser -u 1001 -S app -G app \
    && mkdir -p /app \
    && chown -R app:app /app

# Set work directory
WORKDIR /app

# ============================================================================
# Builder Stage - Install dependencies in isolated layer
# ============================================================================
FROM base AS builder

ARG POETRY_VERSION
ARG PYTHON_VERSION

# Install build-time dependencies (not needed in runtime image)
RUN apk add --no-cache \
    gcc \
    git \
    libffi-dev \
    musl-dev \
    postgresql-dev

# Copy dependency files first (for better layer caching)
COPY pyproject.toml poetry.lock ./

# Upgrade pip to pick up security fixes (pip >= 26.0 for CVE-2026-1703 fix)
RUN python -m pip install --no-cache-dir --upgrade "pip>=26.0"

# Install Poetry with pinned version for reproducibility
RUN pip install --no-cache-dir --require-hashes \
    poetry=="$POETRY_VERSION" || \
    pip install --no-cache-dir poetry=="$POETRY_VERSION"

# Configure poetry to not create virtual environment (install globally)
RUN poetry config virtualenvs.create false

# Install production dependencies with all required extras
# Use --no-interaction for automated environments
# --only=main installs only main dependencies (excludes dev), --extras specifies optional packages
RUN poetry install \
    --only=main \
    --extras "ui ai storage" \
    --no-interaction \
    --no-root && \
    poetry cache clear pypi --all || true

# Copy site-packages to a predictable location for the runtime stage
# This avoids glob expansion issues in COPY commands
RUN PYTHON_MAJOR_MINOR=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")') && \
    cp -r "/usr/local/lib/python${PYTHON_MAJOR_MINOR}/site-packages" /tmp/runtime-site-packages

# ============================================================================
# Runtime Stage - Minimal production image
# ============================================================================
FROM base AS production

ARG PYTHON_VERSION

# Upgrade pip to pick up security fixes (pip >= 26.0 for CVE-2026-1703 fix)
RUN python -m pip install --no-cache-dir --upgrade "pip>=26.0"

# Copy site-packages from builder (at predictable location, no glob expansion)
COPY --from=builder --chown=root:root /tmp/runtime-site-packages /tmp/site-packages

# Install to final location
RUN PYTHON_MAJOR_MINOR=$(echo "${PYTHON_VERSION}" | cut -d. -f1-2) && \
    rm -rf "/usr/local/lib/python${PYTHON_MAJOR_MINOR}/site-packages" && \
    mv /tmp/site-packages "/usr/local/lib/python${PYTHON_MAJOR_MINOR}/site-packages" && \
    \
    # Remove test files and compiled artifacts, but KEEP dist-info (required for package discovery) \
    find "/usr/local/lib/python${PYTHON_MAJOR_MINOR}/site-packages" \
        -type d -name "tests" -exec rm -rf {} + && \
    find "/usr/local/lib/python${PYTHON_MAJOR_MINOR}/site-packages" \
        -type d -name "*.egg-info" -exec rm -rf {} + && \
    find "/usr/local/lib/python${PYTHON_MAJOR_MINOR}/site-packages" \
        -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "*.dist-info/RECORD" \) -delete

# Copy application code (keep root-owned for security)
COPY souschef/ ./souschef/

# Copy Streamlit configuration
COPY .streamlit/ ./.streamlit/

# Create application directories with restricted permissions
RUN mkdir -p /app/.streamlit && \
    mkdir -p /app/.cache && \
    mkdir -p /app/.tmp && \
    chmod 755 /app && \
    chmod 755 /app/souschef && \
    chmod 755 /app/.streamlit && \
    chmod 755 /app/.cache && \
    chmod 755 /app/.tmp && \
    find /app -type f -name '*.py' -exec chmod 644 {} \; && \
    chown -R app:app /app/.streamlit /app/.cache /app/.tmp

# Switch to non-root user for security
USER app

# Expose Streamlit port
EXPOSE 9999

# Health check - robust implementation with timeout
# Note: Must override ENTRYPOINT to avoid streamlit run being prepended
HEALTHCHECK \
    --interval=30s \
    --timeout=10s \
    --start-period=5s \
    --retries=3 \
    CMD /bin/sh -c "python -m souschef.ui.health_check" || exit 1

# Use ENTRYPOINT for proper signal handling
# This ensures Ctrl+C and container stop signals work correctly
ENTRYPOINT ["python", "-m", "streamlit", "run"]

# CMD provides the default arguments
CMD ["souschef/ui/app.py", \
     "--server.address", "0.0.0.0", \
     "--server.port", "9999", \
    "--client.showErrorDetails", "false", \
     "--logger.level", "info", \
     "--server.headless", "true", \
     "--server.runOnSave", "false", \
     "--client.toolbarMode", "auto"]
