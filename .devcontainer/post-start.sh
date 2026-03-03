#!/bin/bash
# Post-start script for SousChef devcontainer
# This runs every time the container starts

echo "Starting SousChef devcontainer services..."

# Ensure Python dependencies are installed
echo "Checking Python dependencies..."
cd /workspaces/souschef || exit 1
if command -v poetry &> /dev/null; then
    # Install all dependencies including optional extras (needed for tests)
    poetry install --all-extras --sync --quiet
    echo "  Python dependencies up to date"
else
    echo "  WARNING: Poetry not found - dependencies may be missing"
fi

# Initialize MCP Catalog
echo "Initializing MCP Catalog..."
docker mcp catalog init 2>/dev/null || {
    echo "MCP Catalog initialization failed - Docker MCP may not be available"
}

# Configure SonarCloud MCP server if credentials are set
if [ -n "${SONARQUBE_URL}" ] && [ -n "${SONARQUBE_ORG}" ] && [ -n "${SONARQUBE_TOKEN}" ]; then
    echo "Configuring SonarCloud MCP server..."

    # Ensure sonarqube server is added
    docker mcp server add sonarqube 2>/dev/null || true

    echo "SonarCloud MCP server configured"
else
    echo "SonarCloud credentials not found in .env.devcontainer - skipping configuration"
    echo "   To enable: copy .env.devcontainer.example to .env.devcontainer and add your credentials"
fi

# Start MCP Gateway in HTTP/SSE mode for VS Code access
if command -v docker &> /dev/null && docker mcp --version &>/dev/null; then
    echo "Starting Docker MCP Gateway on http://localhost:3000/sse"

    # Kill any existing gateway process
    pkill -f "docker mcp gateway" 2>/dev/null || true
    sleep 1

    # Start gateway in SSE mode with nohup to persist after shell exits
    nohup docker mcp gateway run --transport sse --port 3000 > /tmp/gateway.log 2>&1 &

    # Wait for startup
    sleep 3

    # Check if gateway is running
    if pgrep -f "docker mcp gateway" > /dev/null; then
        echo "✓ MCP Gateway running at http://localhost:3000/sse"
        echo "  View log: tail -f /tmp/gateway.log"
        echo "  VS Code config: ~/.config/Code/User/mcp.json"
    else
        echo "Gateway failed to start - check /tmp/gateway.log"
    fi
else
    echo "Docker MCP not available - gateway features disabled"
fi

echo ""
echo "SousChef devcontainer ready!"
