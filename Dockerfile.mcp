# Dockerfile for SousChef MCP server (stdio)
# Optimised for lightweight, secure container execution

ARG POETRY_VERSION=2.5.1

# ============================================================================
# Base Stage - Runtime dependencies only
# ============================================================================
FROM python:3.14-alpine3.22@sha256:6b91e66ab2a880ce9ca5a1b91c70f45963ff71ff68268df056336e1a657d5efd AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONPATH=/app

# Install runtime libraries only (not -dev packages)
# Resolve supported Alpine branch packages on rebuild; see docs/SECURITY.md.
# hadolint ignore=DL3018
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

ARG POETRY_VERSION

# Keep build tooling separate from the application environment.
RUN python -m pip install --no-cache-dir --only-binary :all: "pip==26.2.0" \
    && python -m pip install --no-cache-dir --only-binary :all: "poetry==${POETRY_VERSION}" \
    && python -m venv --without-pip /opt/venv

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Copy project files required to build wheel
COPY pyproject.toml poetry.lock README.md ./
COPY souschef ./souschef

# Build only trusted local source; third-party dependencies must provide wheels.
RUN poetry config installer.only-binary :all: \
    && poetry install --only main --no-interaction --no-ansi --no-root \
    && /usr/local/bin/python -m pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/wheels . \
    && /usr/local/bin/python -m pip --python /opt/venv/bin/python install \
        --no-cache-dir --no-index --no-deps --only-binary :all: /tmp/wheels/*.whl

# ============================================================================
# Production Stage - Minimal runtime image
# ============================================================================
FROM base AS production

# Production has application dependencies, not package managers or their vendors.
RUN python -m pip uninstall --yes pip

COPY --from=builder --chown=root:root /opt/venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

USER 1001:1001

CMD ["python", "-m", "souschef.server"]
