# Use the official Python devcontainer as base
FROM mcr.microsoft.com/devcontainers/python:3.13

# Build arguments
ARG SNYK_VERSION=latest
ARG CODEQL_VERSION=latest
ARG SONAR_SCANNER_VERSION=latest

# Set shell options for safer piping
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install Poetry, system packages, and optional tools
# hadolint ignore=DL4006
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry && \
    poetry config virtualenvs.in-project true && \
    apt-get update && apt-get install -y --no-install-recommends \
    curl=7.* \
    git=1:* \
    gnupg=2.* \
    build-essential=12.* \
    libssl-dev=3.* \
    libffi-dev=3.* \
    unzip=6.* \
    npm=* \
    && rm -rf /var/lib/apt/lists/* && \
    if [ "$SNYK_VERSION" != "skip" ]; then \
    npm install -g snyk && \
    snyk --version; \
    fi && \
    if [ "$CODEQL_VERSION" != "skip" ]; then \
    ARCH=$(uname -m); \
    if [ "$ARCH" = "x86_64" ] || [ "$ARCH" = "amd64" ]; then \
        curl -L https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip -o /tmp/codeql.zip && \
        unzip /tmp/codeql.zip -d /opt && \
        ln -s /opt/codeql/codeql /usr/local/bin/codeql && \
        rm /tmp/codeql.zip; \
    fi; \
    fi && \
    if [ "$SONAR_SCANNER_VERSION" != "skip" ]; then \
    if [ "$SONAR_SCANNER_VERSION" = "latest" ]; then \
        SONAR_SCANNER_VERSION="6.2.1.4610"; \
    fi; \
    curl -L https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-${SONAR_SCANNER_VERSION}-linux-x64.zip -o /tmp/sonar-scanner.zip && \
    unzip /tmp/sonar-scanner.zip -d /opt && \
    mv /opt/sonar-scanner-${SONAR_SCANNER_VERSION}-linux-x64 /opt/sonar-scanner && \
    ln -s /opt/sonar-scanner/bin/sonar-scanner /usr/local/bin/sonar-scanner && \
    rm /tmp/sonar-scanner.zip; \
    fi

# Set the working directory
WORKDIR /workspaces/souschef

# Copy only necessary project files for dependency installation
COPY pyproject.toml poetry.lock* README.md ./

# Install Python project dependencies with Poetry
# Use --no-root to skip installing the package itself during the build
# Verify installations
RUN poetry install --no-interaction --no-ansi --no-root && \
    poetry --version && \
    python --version && \
    poetry run python --version
