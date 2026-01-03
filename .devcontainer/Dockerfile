# SousChef Development Container
# Chef-to-Ansible conversion MCP server

FROM mcr.microsoft.com/devcontainers/python:3.14

# Metadata labels
LABEL org.opencontainers.image.title="SousChef Dev Container" \
      org.opencontainers.image.description="Development environment for SousChef MCP server" \
      org.opencontainers.image.source="https://github.com/kpeacocke/souschef" \
      org.opencontainers.image.authors="SousChef Contributors" \
      org.opencontainers.image.licenses="MIT"

# Use bash for better script support
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Snyk CLI version - pin for reproducibility
ARG SNYK_VERSION=latest

# Install Snyk CLI with architecture detection
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        SNYK_ARCH="linux"; \
    elif [ "$ARCH" = "arm64" ]; then \
        SNYK_ARCH="linux-arm64"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    curl -sSL "https://static.snyk.io/cli/${SNYK_VERSION}/snyk-${SNYK_ARCH}" -o /usr/local/bin/snyk && \
    chmod +x /usr/local/bin/snyk && \
    snyk --version
