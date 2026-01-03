FROM mcr.microsoft.com/devcontainers/python:3.14

# Install clipboard utilities for Snyk and other tools
RUN apt-get update && apt-get install -y xclip xsel && rm -rf /var/lib/apt/lists/*

# Install Snyk CLI
RUN curl -sSL https://static.snyk.io/cli/latest/snyk-linux -o /usr/local/bin/snyk && \
    chmod +x /usr/local/bin/snyk
