#!/usr/bin/env bash
# Bash 5.2 syntax sample with loops, guards, files, packages, and services.
set -euo pipefail
packages=(nginx python3 python3-venv)
for package in "${packages[@]}"; do
  apt-get install -y "$package"
done

app_root=/srv/example-app
install -d -m 0750 "$app_root" /var/log/example-app
cat > /etc/nginx/conf.d/example-app.conf <<'EOF'
server {
    listen 8080;
    server_name localhost;
    location /health {
        return 200 "ok";
    }
}
EOF
chown root:root /etc/nginx/conf.d/example-app.conf
chmod 0640 /etc/nginx/conf.d/example-app.conf
systemctl enable --now nginx
systemctl reload nginx
