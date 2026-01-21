#!/bin/bash
# Post-create setup script for SousChef devcontainer
set -e

echo "🍳 Setting up SousChef development environment..."

# Configure git
cat > ~/.gitconfig << 'EOF'
[include]
	path = ~/.gitconfig.host
[gpg]
	program = gpg
[commit]
	gpgsign = false
EOF

# Ensure PATH includes local bin
export PATH="$HOME/.local/bin:$PATH"

# Install Ansible and ansible-lint globally
echo "📦 Installing Ansible..."
pip install --user ansible ansible-lint

# Install Docker CLI
echo "🐳 Installing Docker CLI..."
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce-cli docker-compose-plugin

# Add vscode user to docker group for socket access
echo "👤 Adding vscode user to docker group..."
sudo usermod -aG docker vscode

# Set docker socket permissions for immediate access
echo "🔧 Setting docker socket permissions..."
sudo chmod 666 /var/run/docker.sock

# Create systemd service for persistent docker permissions
echo "🔧 Creating persistent docker permissions service..."
sudo tee /etc/systemd/system/docker-permissions.service > /dev/null << 'EOF'
[Unit]
Description=Fix Docker socket permissions for devcontainer
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'chmod 666 /var/run/docker.sock 2>/dev/null || true'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable docker-permissions.service

# Also create a cron job as backup
echo "🔧 Setting up cron job for docker permissions..."
sudo tee /etc/cron.d/docker-permissions > /dev/null << 'EOF'
*/5 * * * * root chmod 666 /var/run/docker.sock 2>/dev/null || true
EOF

# Configure Poetry
echo "📦 Configuring Poetry..."
poetry config virtualenvs.in-project true

# Install project dependencies
echo "📦 Installing project dependencies..."
poetry install

# Ensure cache directory exists
echo "📁 Ensuring cache directory exists..."
mkdir -p ~/.cache
sudo chown vscode:vscode ~/.cache

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
poetry run pre-commit install

# Set up Go environment
echo "🐹 Setting up Go environment..."
mkdir -p ~/.cache/go-build
mkdir -p ~/go/pkg/mod
sudo chown vscode:vscode ~/.cache/go-build
sudo chown vscode:vscode ~/go/pkg/mod
cd /workspaces/souschef/terraform-provider
go mod download
go mod tidy

# Return to workspace root
cd /workspaces/souschef

# Install CodeQL CLI (with architecture detection)
echo "🔍 Checking for CodeQL CLI compatibility..."
ARCH=$(uname -m)
CODEQL_SUPPORTED=false

case $ARCH in
    x86_64|amd64)
        echo "✅ x86_64 architecture detected - CodeQL CLI supported"
        CODEQL_SUPPORTED=true
        ;;
    aarch64|arm64)
        echo "⚠️  ARM64 architecture detected - CodeQL CLI not officially supported"
        echo "   CodeQL can still run via GitHub Actions (already configured)"
        echo "   For local testing, consider using x86_64 hardware or GitHub Codespaces"
        CODEQL_SUPPORTED=false
        ;;
    *)
        echo "⚠️  Unknown architecture: $ARCH - CodeQL CLI support unknown"
        CODEQL_SUPPORTED=false
        ;;
esac

if [ "$CODEQL_SUPPORTED" = true ]; then
    CODEQL_DIR="$HOME/.codeql"
    mkdir -p "$CODEQL_DIR"

    echo "📥 Downloading CodeQL CLI..."
    CODEQL_URL="https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip"

    if curl -fsSL "$CODEQL_URL" -o "$CODEQL_DIR/codeql.zip"; then
        echo "📦 Extracting CodeQL CLI..."
        unzip -q "$CODEQL_DIR/codeql.zip" -d "$CODEQL_DIR"
        rm "$CODEQL_DIR/codeql.zip"

        # Add CodeQL to PATH
        echo 'export PATH="$HOME/.codeql/codeql:$PATH"' >> ~/.zshrc
        export PATH="$HOME/.codeql/codeql:$PATH"

        # Verify installation
        if "$CODEQL_DIR/codeql/codeql" version > /dev/null 2>&1; then
            CODEQL_VERSION=$("$CODEQL_DIR/codeql/codeql" version --format=text | head -n1)
            echo "✅ CodeQL CLI installed successfully: $CODEQL_VERSION"
        else
            echo "⚠️  CodeQL CLI installed but verification failed"
        fi
    else
        echo "⚠️  Failed to download CodeQL CLI"
    fi
fi

# Run tests to verify setup
echo "🧪 Running tests..."
poetry run pytest -q

echo "✅ SousChef development environment ready!"
