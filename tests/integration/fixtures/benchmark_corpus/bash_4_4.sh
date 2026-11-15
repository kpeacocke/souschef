#!/usr/bin/env bash
# Bash 4.4-compatible legacy provisioning sample; tests parse only.
set -e
apt-get update -y
apt-get install -y nginx python3
mkdir -p /var/lib/example-app
printf '%s\n' 'MODE=production' > /etc/example-app.env
systemctl enable nginx
systemctl start nginx
