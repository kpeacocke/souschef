# Build Docker MCP CLI plugin
FROM golang:1.25-bookworm AS docker-mcp-builder
WORKDIR /src/mcp-gateway
COPY mcp-gateway/ ./
RUN mkdir -p /root/.docker/cli-plugins && \
    make docker-mcp

# Use the official Python devcontainer as base
FROM mcr.microsoft.com/devcontainers/python:3.13

# Build arguments
ARG SNYK_VERSION=latest
ARG CODEQL_VERSION=latest
ARG SONAR_SCANNER_VERSION=latest

# Set shell options for safer piping
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Remove problematic Yarn repository that has signing issues and add the GPG key
RUN rm -f /etc/apt/sources.list.d/yarn.list && \
    rm -f /etc/apt/sources.list.d/yarn.sources && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys FF7CB5667B542092084BBDC562D54FD4003F6525 2>/dev/null || true

# Update package lists and install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    git \
    gnupg \
    wget \
    apt-transport-https \
    lsb-release \
    build-essential \
    libssl-dev \
    libffi-dev \
    unzip \
    npm && \
    # Install Poetry
    curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry && \
    poetry config virtualenvs.in-project true && \
    # Clean up APT cache
    rm -rf /var/lib/apt/lists/*

# Install Docker CLI (docker-ce-cli)
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# Install Trivy vulnerability scanner
RUN apt-get update && \
    curl -fsSL https://aquasecurity.github.io/trivy-repo/deb/public.key -o /etc/apt/trusted.gpg.d/trivy.gpg && \
    TRIVY_SUITE="$(lsb_release -sc)" && \
    if [ "$TRIVY_SUITE" = "trixie" ]; then TRIVY_SUITE="bookworm"; fi && \
    echo "deb [signed-by=/etc/apt/trusted.gpg.d/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb ${TRIVY_SUITE} main" | tee -a /etc/apt/sources.list.d/trivy.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends trivy && \
    rm -rf /var/lib/apt/lists/*

# Install development tools (Snyk, CodeQL, SonarScanner)
RUN if [ "$SNYK_VERSION" != "skip" ]; then \
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

# Install Docker MCP CLI plugin
RUN mkdir -p /usr/local/lib/docker/cli-plugins
COPY --from=docker-mcp-builder /src/mcp-gateway/dist/docker-mcp /usr/local/lib/docker/cli-plugins/docker-mcp
RUN chmod +x /usr/local/lib/docker/cli-plugins/docker-mcp

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
