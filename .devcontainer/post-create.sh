#!/bin/bash
# Post-create setup script for SousChef devcontainer
# This runs after git clone, focusing on project-specific setup
set -e

echo "Setting up SousChef development environment..."

# ============================================================================
# Docker Socket Permissions - Cross-Platform Support
# ============================================================================
# Container needs explicit permission setup because docker.sock is mounted
# from host and may not have correct permissions for the vscode user
# Handles Linux (docker group) and Windows/WSL2 (socket binding)
if [ -S /var/run/docker.sock ]; then
    echo "Configuring Docker socket access..."

    # Detect if we're on Linux (docker group exists) or Windows/WSL2
    if uname -s | grep -q "Linux"; then
        # Linux-specific: use docker group
        if id "vscode" &>/dev/null 2>&1; then
            # Create docker group if it doesn't exist
            if ! grep -q "^docker:" /etc/group; then
                if sudo groupadd docker 2>/dev/null; then
                    echo "  Created docker group"
                fi
            fi

            # Add vscode user to docker group
            if sudo usermod -aG docker vscode 2>/dev/null; then
                echo "  Added vscode to docker group"
            fi

            # Fix socket permissions (redundant but safe)
            if sudo chmod 666 /var/run/docker.sock 2>/dev/null; then
                echo "  Fixed socket permissions"
            fi
        fi
    else
        # Windows/WSL2: socket permissions are typically inherited from host
        # Just verify the socket is readable
        if [ -r /var/run/docker.sock ]; then
            echo "  Docker socket accessible (Windows/WSL2)"
        else
            echo "  Docker socket not readable - may need manual fix"
        fi
    fi

    # Verify docker CLI is accessible
    if docker ps >/dev/null 2>&1; then
        DOCKER_VERSION=$(docker --version 2>/dev/null || echo "Docker CLI")
        echo "Docker available: $DOCKER_VERSION"
    else
        echo "Docker socket mounted but not yet accessible"
        echo "        This is normal on first start - restart the container if needed"
    fi
fi

# Verify and install Go if missing (fallback for feature installation issues)
if ! command -v go &> /dev/null; then
    echo "Go not found in PATH, installing from go.dev..."
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        GO_ARCH="arm64"
    else
        GO_ARCH="amd64"
    fi
    GO_VERSION="1.24.0"
    GO_URL="https://go.dev/dl/go${GO_VERSION}.linux-${GO_ARCH}.tar.gz"

    mkdir -p /tmp/go-install
    if curl -fsSL --proto '=https' --tlsv1.2 "$GO_URL" -o /tmp/go-install/go.tar.gz; then
        rm -rf /usr/local/go
        tar -C /usr/local -xzf /tmp/go-install/go.tar.gz
        rm -rf /tmp/go-install
        echo "Go $GO_VERSION installed successfully"
    else
        echo "  WARNING: Failed to install Go from go.dev"
        echo "  This may be a network issue. Go may still be available from the feature installation."
    fi
else
    GO_VERSION=$(go version | awk '{print $3}')
    echo "Go already installed: $GO_VERSION"
fi

# Verify Poetry is available
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found in PATH, installing..."
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

# Configure Poetry to create venv in project directory
echo "Configuring Poetry..."
poetry config virtualenvs.in-project true

# Install project dependencies with all extras (changes with code)
echo "Installing Python project dependencies (including all extras)..."
poetry install --all-extras

# Add automatic virtual environment activation to shell
echo "Configuring shell to auto-activate virtual environment..."
if ! grep -q "Auto-activate Poetry venv" ~/.zshrc 2>/dev/null; then
    cat >> ~/.zshrc << 'EOF'

# Auto-activate Poetry venv for SousChef project
if [[ -d "/workspaces/souschef/.venv" ]] && [[ "$PWD" == /workspaces/souschef* ]]; then
    source /workspaces/souschef/.venv/bin/activate
fi
EOF
    echo "  Added venv activation to ~/.zshrc"
fi

if ! grep -q "Auto-activate Poetry venv" ~/.bashrc 2>/dev/null; then
    cat >> ~/.bashrc << 'EOF'

# Auto-activate Poetry venv for SousChef project
if [[ -d "/workspaces/souschef/.venv" ]] && [[ "$PWD" == /workspaces/souschef* ]]; then
    source /workspaces/souschef/.venv/bin/activate
fi
EOF
    echo "  Added venv activation to ~/.bashrc"
fi

# Install pre-commit hooks (project-specific)
echo "Installing pre-commit hooks..."
poetry run pre-commit install

# Initialize MCP Catalog (needed for gateway)
echo "Initializing MCP Catalog..."
docker mcp catalog init 2>/dev/null || echo "Catalog initialization will run on container start"

# Set up Go environment for terraform-provider
echo "Setting up Go dependencies..."
cd /workspaces/souschef/terraform-provider
go mod download
go mod tidy
cd /workspaces/souschef

# Verify CodeQL installation (if available)
if command -v codeql &> /dev/null; then
    CODEQL_VERSION=$(codeql version --format=text 2>/dev/null | head -n1 || echo "unknown")
    echo "CodeQL CLI available: $CODEQL_VERSION"
else
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        echo "CodeQL CLI not available (ARM64 architecture)"
        echo "       CodeQL analysis will run via GitHub Actions"
    fi
fi

# Run quick test to verify setup
echo "Running quick verification tests..."
poetry run pytest -q --co -q 2>/dev/null || echo "Test discovery completed"

echo "SousChef development environment ready!"
echo ""
echo "Gateway services will be available on container start."


