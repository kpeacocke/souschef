FROM mcr.microsoft.com/devcontainers/python:3.14

# Install Snyk CLI with architecture detection
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        SNYK_ARCH="linux"; \
    elif [ "$ARCH" = "arm64" ]; then \
        SNYK_ARCH="linux-arm64"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    curl -sSL "https://static.snyk.io/cli/latest/snyk-${SNYK_ARCH}" -o /usr/local/bin/snyk && \
    chmod +x /usr/local/bin/snyk
