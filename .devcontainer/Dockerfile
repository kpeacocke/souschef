# Use the official Python devcontainer as base
FROM mcr.microsoft.com/devcontainers/python:3.13

# Build arguments
ARG SNYK_VERSION=latest
ARG CODEQL_VERSION=latest
ARG SONAR_SCANNER_VERSION=latest

# Configure APT early to handle repositories with missing/expired GPG keys
# This MUST be done before features are installed, as they may add problematic repositories
# (e.g., Yarn repository used by Node.js feature). The devcontainers CLI injects feature
# installation steps after this RUN command, so this config will be available for them.
RUN apt-get update -o APT::Get::AllowUnauthenticated=true 2>&1 | grep -v "^Get:" | grep -v "^Hit:" || true && \
    mkdir -p /etc/apt/apt.conf.d && \
    # Allow installation from unsigned repositories
    echo 'APT::Get::AllowUnauthenticated "true";' > /etc/apt/apt.conf.d/99-allow-unsigned && \
    echo 'Acquire::AllowInsecureRepositories "true";' >> /etc/apt/apt.conf.d/99-allow-unsigned && \
    echo 'Acquire::AllowUnauthenticatedPackages "true";' >> /etc/apt/apt.conf.d/99-allow-unsigned && \
    # Try to add the Yarn GPG key preemptively (used by Node.js feature)
    curl -fsSL https://dl.yarnpkg.com/debian/pubkey.gpg 2>/dev/null | apt-key add - 2>/dev/null || \
    echo "Note: Yarn GPG key not available, but APT is configured to handle unsigned packages" && \
    # Update package lists (will warn about unsigned repos but won't fail)
    apt-get update 2>&1 | grep -E "^(E:|W:)" | grep -v "Could not" || true

# Set shell options for safer piping
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install Poetry, system packages, and optional tools
# hadolint ignore=DL3016,DL4006,DL3008
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry && \
    poetry config virtualenvs.in-project true && \
    apt-get update && apt-get install -y --no-install-recommends \
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
    npm \
    docker.io \
    && \
    # Install Trivy vulnerability scanner
    wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | apt-key add - && \
    echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | tee -a /etc/apt/sources.list.d/trivy.list && \
    apt-get update && apt-get install -y --no-install-recommends trivy && \
    rm -rf /var/lib/apt/lists/* && \
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
