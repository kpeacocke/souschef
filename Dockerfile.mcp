# Dockerfile for SousChef MCP server (stdio)
# Optimised for lightweight, secure container execution

ARG PYTHON_VERSION=3.13

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
    ca-certificates=20260413-r0 \
    curl=8.14.1-r2 \
    libffi=3.4.8-r0 \
    && apk upgrade --no-cache \
    && addgroup -g 1001 -S app \
    && adduser -u 1001 -S app -G app

WORKDIR /app

# ============================================================================
# Builder Stage - Install dependencies
# ============================================================================
FROM base AS builder

ARG PYTHON_VERSION

# Install build-time dependencies
RUN apk add --no-cache \
    gcc=14.2.0-r6 \
    libffi-dev=3.4.8-r0 \
    musl-dev=1.2.5-r12 \
    poetry=2.0.1-r0

# Copy project files required to build wheel
COPY pyproject.toml poetry.lock README.md ./
COPY souschef ./souschef

# Build and install pinned application wheel from the trusted local source tree.
RUN poetry config virtualenvs.create false \
    && poetry build -f wheel \
    && python -m pip install --no-cache-dir --only-binary :all: dist/*.whl

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
