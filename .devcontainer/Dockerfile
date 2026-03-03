# Build Docker MCP CLI plugin from docker/mcp-gateway source
FROM golang:1.25-bookworm AS docker-mcp-builder
WORKDIR /src
RUN apt-get update && apt-get install -y --no-install-recommends make git && rm -rf /var/lib/apt/lists/*
# Create the target directory that the Makefile expects
RUN mkdir -p /root/.docker/cli-plugins
# Retry logic for git clone to handle transient network issues
RUN for i in 1 2 3; do \
    if git clone --depth 1 https://github.com/docker/mcp-gateway.git; then \
      cd mcp-gateway && make docker-mcp && exit 0; \
    else \
      echo "Clone attempt $i failed, retrying..."; \
      sleep $((i * 5)); \
    fi; \
  done; exit 1

# Use the official Python devcontainer as base
FROM mcr.microsoft.com/devcontainers/python:3.14

# Build arguments
ARG SNYK_VERSION=latest
ARG CODEQL_VERSION=latest
ARG SONAR_SCANNER_VERSION=latest

# Set shell options for safer piping
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Update package lists and install system dependencies
RUN rm -f /etc/apt/sources.list.d/yarn.list && \
    rm -f /etc/apt/sources.list.d/yarn.sources && \
    apt-key adv --keyserver keyserver.ubuntu.com \
        --recv-keys FF7CB5667B542092084BBDC562D54FD4003F6525 \
        2>/dev/null || true && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    apt-transport-https \
    build-essential \
    curl \
    git \
    gnupg \
    libffi-dev \
    libssl-dev \
    lsb-release \
    npm \
    unzip \
    wget && \
    # Install Terraform CLI from HashiCorp APT repository
    install -m 0755 -d /usr/share/keyrings && \
    curl -fsSL --proto '=https' --tlsv1.2 https://apt.releases.hashicorp.com/gpg \
        | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" \
        | tee /etc/apt/sources.list.d/hashicorp.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends terraform && \
    # Install Poetry (enforce HTTPS and TLS 1.2+)
    curl -sSL --proto '=https' --tlsv1.2 https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry && \
    poetry config virtualenvs.in-project true && \
    # Install Docker CLI (docker-ce-cli) and docker-mcp plugin
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL --proto '=https' --tlsv1.2 https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    mkdir -p /usr/local/lib/docker/cli-plugins && \
    rm -rf /var/lib/apt/lists/*

# Install docker-mcp plugin from builder stage (system-wide location for all users)
COPY --from=docker-mcp-builder /src/mcp-gateway/dist/docker-mcp /usr/local/lib/docker/cli-plugins/docker-mcp

# Install Trivy vulnerability scanner and development tools
RUN chmod +x /usr/local/lib/docker/cli-plugins/docker-mcp && \
    apt-get update && \
    curl -fsSL --proto '=https' --tlsv1.2 https://aquasecurity.github.io/trivy-repo/deb/public.key -o /etc/apt/trusted.gpg.d/trivy.gpg && \
    TRIVY_SUITE="$(lsb_release -sc)" && \
    if [ "$TRIVY_SUITE" = "trixie" ]; then TRIVY_SUITE="bookworm"; fi && \
    echo "deb [signed-by=/etc/apt/trusted.gpg.d/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb ${TRIVY_SUITE} main" | tee -a /etc/apt/sources.list.d/trivy.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends trivy && \
    rm -rf /var/lib/apt/lists/* && \
    if [ "$SNYK_VERSION" != "skip" ]; then \
    npm install -g --ignore-scripts snyk && \
    snyk --version; \
    fi && \
    if [ "$CODEQL_VERSION" != "skip" ]; then \
    ARCH=$(uname -m); \
    if [ "$ARCH" = "x86_64" ] || [ "$ARCH" = "amd64" ]; then \
        curl -L --proto '=https' --tlsv1.2 https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip -o /tmp/codeql.zip && \
        unzip /tmp/codeql.zip -d /opt && \
        ln -s /opt/codeql/codeql /usr/local/bin/codeql && \
        rm /tmp/codeql.zip; \
    fi; \
    fi && \
    if [ "$SONAR_SCANNER_VERSION" != "skip" ]; then \
    if [ "$SONAR_SCANNER_VERSION" = "latest" ]; then \
        SONAR_SCANNER_VERSION="6.2.1.4610"; \
    fi; \
    curl -L --proto '=https' --tlsv1.2 https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-"${SONAR_SCANNER_VERSION}"-linux-x64.zip -o /tmp/sonar-scanner.zip && \
    unzip /tmp/sonar-scanner.zip -d /opt && \
    mv /opt/sonar-scanner-"${SONAR_SCANNER_VERSION}"-linux-x64 /opt/sonar-scanner && \
    ln -s /opt/sonar-scanner/bin/sonar-scanner /usr/local/bin/sonar-scanner && \
    rm /tmp/sonar-scanner.zip; \
    fi

# Set the working directory
WORKDIR /workspaces/souschef

# Copy only necessary project files for dependency installation
# Individual files specified to avoid recursive directory copying (S6470)
COPY pyproject.toml ./pyproject.toml
COPY README.md ./README.md
# poetry.lock is optional but recommended for reproducible builds
COPY poetry.lock ./poetry.lock

# Install Python project dependencies with Poetry
# Use --no-root to skip installing the package itself during the build
# Verify installations
RUN poetry install --no-interaction --no-ansi --no-root && \
    poetry --version && \
    python --version && \
    poetry run python --version

# Switch to non-root user for security (devcontainer default user)
USER vscode
