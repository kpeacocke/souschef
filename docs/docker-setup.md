# Docker Setup and Permissions

## Overview
This devcontainer environment mounts the host's Docker socket to enable Docker operations within the container. However, the Docker socket has restrictive permissions by default that prevent the `vscode` user from accessing it.

## Accessing Services from Devcontainer

When running containers via `docker compose` from within the devcontainer, they are accessible in different ways depending on your location:

### From Host Machine
- **localhost:9999** - Direct access to exposed ports
- **127.0.0.1:9999** - Same as localhost

### From Within Devcontainer
- **localhost:9999** [NO] Does NOT work (network isolation)
- **172.17.0.1:9999** [YES] Use the host gateway IP
- **host.docker.internal:9999** [NO] May not be available

To find the correct host IP from devcontainer:
```bash
ip route show | grep default | awk '{print $3}'
# Or use this alias:
get_host_ip() { ip route show | grep default | awk '{print $3}'; }
```

## Automatic Setup

## Automatic Setup
The devcontainer automatically handles Docker permissions through:

1. **Post-create script**: Sets initial permissions during container creation
2. **Systemd service**: Maintains permissions across container restarts
3. **Cron job**: Backup mechanism that checks permissions every 5 minutes

## Manual Fix
If Docker access is lost (e.g., after host restart), you can fix it using:

### Quick Fix (alias)
```bash
fix-docker
```

### Full Script
```bash
./fix-docker-permissions.sh
```

## Troubleshooting

### Check Current Permissions
```bash
ls -la /var/run/docker.sock
```

Expected output should show permissions like `srw-rw-rw-` (666).

### Test Docker Access
```bash
docker ps
```

If this fails, run the fix command above.

### Host Docker Service
Ensure Docker is running on the host:
```bash
# On host machine
sudo systemctl status docker
sudo systemctl start docker  # if not running
```

## Security Note
The socket permissions are set to `666` (world-writable) for development convenience. In production environments, consider more restrictive permissions or alternative approaches like Docker-in-Docker.
