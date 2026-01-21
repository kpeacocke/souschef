#!/bin/bash
# Script to fix Docker socket permissions for development
# This ensures the vscode user can access docker.sock

set -e

echo "🐳 Fixing Docker socket permissions..."

# Check if docker.sock exists
if [ ! -S /var/run/docker.sock ]; then
    echo "❌ Docker socket not found at /var/run/docker.sock"
    echo "   Make sure Docker is running on the host"
    exit 1
fi

# Get current permissions
CURRENT_PERMS=$(stat -c '%a' /var/run/docker.sock 2>/dev/null || echo "unknown")

echo "📊 Current docker.sock permissions: $CURRENT_PERMS"

# Set permissions to allow access
echo "🔧 Setting docker.sock permissions to 666..."
sudo chmod 666 /var/run/docker.sock

# Verify the change
NEW_PERMS=$(stat -c '%a' /var/run/docker.sock)
echo "✅ Docker socket permissions updated to: $NEW_PERMS"

# Test docker access
echo "🧪 Testing Docker access..."
if docker ps >/dev/null 2>&1; then
    echo "✅ Docker access confirmed!"
else
    echo "❌ Docker access test failed"
    echo "   You may need to restart the devcontainer or check Docker host configuration"
    exit 1
fi

echo "🎉 Docker permissions fixed successfully!"
