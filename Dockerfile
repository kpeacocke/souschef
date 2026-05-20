# Dockerfile for SousChef MCP server (stdio)
# Optimised for lightweight, secure container execution

ARG PYTHON_VERSION=3.13
ARG POETRY_VERSION=2.3.4

# ============================================================================
# Base Stage - Runtime dependencies only
# ============================================================================
FROM python:${PYTHON_VERSION}-alpine3.22 AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONPATH=/app

# Install runtime libraries only (not -dev packages)
RUN apk add --no-cache \
    ca-certificates \
    curl \
    libffi \
    && apk upgrade --no-cache \
    && addgroup -g 1001 -S app \
    && adduser -u 1001 -S app -G app

WORKDIR /app

# ============================================================================
# Builder Stage - Install dependencies
# ============================================================================
FROM base AS builder

ARG PYTHON_VERSION
ARG POETRY_VERSION

# Install build-time dependencies
RUN apk add --no-cache \
    gcc \
    libffi-dev \
    musl-dev

# Install Poetry with the application Python interpreter to avoid system-managed
# environment conflicts when syncing dependencies.
RUN python -m pip install --no-cache-dir --only-binary :all: "pip==26.1.1" \
    && python -m pip install --no-cache-dir --only-binary :all: "poetry==${POETRY_VERSION}"

# Copy project files required to build wheel
COPY pyproject.toml poetry.lock README.md ./
COPY souschef ./souschef

# Install runtime dependencies first, then install the project package without
# allowing Poetry to prune its own runtime from the global interpreter.
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi --no-root \
    && python -m pip install --no-cache-dir --no-deps .

# Copy site-packages to predictable location
RUN PYTHON_MAJOR_MINOR=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")') && \
    cp -r "/usr/local/lib/python${PYTHON_MAJOR_MINOR}/site-packages" /tmp/runtime-site-packages

# ============================================================================
# Production Stage - Minimal runtime image
# ============================================================================
FROM base AS production

ARG PYTHON_VERSION

# Copy site-packages from builder
COPY --from=builder --chown=root:root /tmp/runtime-site-packages /tmp/site-packages

# Install to final location and cleanup
RUN PYTHON_MAJOR_MINOR=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")') && \
    rm -rf "/usr/local/lib/python${PYTHON_MAJOR_MINOR}/site-packages" && \
    mv /tmp/site-packages "/usr/local/lib/python${PYTHON_MAJOR_MINOR}/site-packages" && \
    find "/usr/local/lib/python${PYTHON_MAJOR_MINOR}/site-packages" \
        -type d -name "tests" -exec rm -rf {} + && \
    find "/usr/local/lib/python${PYTHON_MAJOR_MINOR}/site-packages" \
        -maxdepth 1 -type d -name "poetry*" -exec rm -rf {} + && \
    find "/usr/local/lib/python${PYTHON_MAJOR_MINOR}/site-packages" \
        -maxdepth 1 -type d -name "poetry-*.dist-info" -exec rm -rf {} + && \
    find "/usr/local/lib/python${PYTHON_MAJOR_MINOR}/site-packages" \
        -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

USER app

CMD ["python", "-m", "souschef.server"]
