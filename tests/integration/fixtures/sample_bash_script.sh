#!/bin/bash
# Sample provisioning script for testing Bash script migration
# This script installs and configures a web server

set -e

# Update package lists and install web server + runtime dependencies
apt-get update -y
apt-get install -y nginx python3 curl wget

# Install Python packages
pip3 install gunicorn flask

# Download application archive
curl -o /tmp/app.tar.gz https://example.com/releases/app-1.0.tar.gz
wget -O /tmp/config.zip https://example.com/configs/config-v2.zip

# Write a configuration file via heredoc
cat <<EOF > /etc/nginx/conf.d/app.conf
server {
    listen 80;
    server_name example.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
EOF

# Write another file via echo redirect
echo "LOG_LEVEL=info" > /etc/app/env

# Install from yum on RHEL-based systems (commented out - for pattern testing)
# yum install -y httpd

# Service management
systemctl enable nginx
systemctl start nginx
service nginx restart

# Some unrecognised command (will fall back to shell)
custom-configure --site example.com --port 8080
