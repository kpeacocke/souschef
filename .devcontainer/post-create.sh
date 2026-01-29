#!/bin/bash
# Post-create setup script for SousChef devcontainer
# This runs after git clone, focusing on project-specific setup
set -e

echo "🍳 Setting up SousChef development environment..."

# ============================================================================
# Docker Socket Permissions - CRITICAL FOR DOCKER-IN-DOCKER
# ============================================================================
# Container needs explicit permission setup because docker.sock is mounted
# from host and may not have correct permissions for the vscode user
if [ -S /var/run/docker.sock ]; then
    echo "🐳 Configuring Docker socket access..."
    
    # Check if vscode user exists (runs as root in features phase)
    if id "vscode" &>/dev/null 2>&1; then
        # Get docker group if it exists, create if not
        if ! grep -q "^docker:" /etc/group; then
            sudo groupadd -f docker || echo "Docker group setup skipped"
        fi
        
        # Add vscode to docker group
        sudo usermod -aG docker vscode || echo "Unable to add vscode to docker group"
        
        # Fix socket permissions
        sudo chmod 666 /var/run/docker.sock || echo "Unable to set socket permissions"
        
        echo "✅ Docker socket configured for vscode user"
    fi
    
    # Verify docker is accessible
    if docker ps >/dev/null 2>&1; then
        DOCKER_VERSION=$(docker --version)
        echo "✅ Docker available: $DOCKER_VERSION"
    else
        echo "⚠️  Docker socket mounted but not yet accessible (this is normal on first start)"
        echo "    Permissions will be fixed automatically when the container restarts"
    fi
else
    echo "⚠️  Docker socket not mounted at /var/run/docker.sock"
    echo "    DevContainer will still work without Docker access"
fi

# Ensure Poetry is in PATH
export PATH="/root/.local/bin:/usr/local/bin:$PATH"

# Verify Poetry is available
if ! command -v poetry &> /dev/null; then
    echo "⚠️  Poetry not found in PATH, installing..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Configure git to include host config
cat > ~/.gitconfig << 'EOF'
[include]
	path = ~/.gitconfig.host
[gpg]
	program = gpg
[commit]
	gpgsign = false
EOF

# Install project dependencies (changes with code)
echo "📦 Installing Python project dependencies..."
poetry install

# Install pre-commit hooks (project-specific)
echo "🪝 Installing pre-commit hooks..."
poetry run pre-commit install

# Set up Go environment for terraform-provider
echo "🐹 Setting up Go dependencies..."
cd /workspaces/souschef/terraform-provider
go mod download
go mod tidy
cd /workspaces/souschef

# Verify CodeQL installation (if available)
if command -v codeql &> /dev/null; then
    CODEQL_VERSION=$(codeql version --format=text 2>/dev/null | head -n1 || echo "unknown")
    echo "✅ CodeQL CLI available: $CODEQL_VERSION"
else
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        echo "ℹ️  CodeQL CLI not available (ARM64 architecture)"
        echo "   CodeQL analysis will run via GitHub Actions"
    fi
fi

# Run quick test to verify setup
echo "🧪 Running quick verification tests..."
poetry run pytest -q --co -q 2>/dev/null || echo "⚠️  Test discovery completed"

echo "✅ SousChef development environment ready!"

