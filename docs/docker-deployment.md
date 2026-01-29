# Docker Deployment Guide

This guide covers building, testing, and deploying the SousChef UI as a Docker container.

## Overview

The SousChef project includes a production-ready Dockerfile for containerising the Streamlit UI. The Docker image is:

- **Secure**: Runs as non-root user, minimal dependencies, security scanning
- **Robust**: Multi-stage build, health checks, proper signal handling
- **Efficient**: Optimised for caching, supports multiple architectures (amd64, arm64)
- **Observable**: Comprehensive logging, health checks, metadata labels

## Quick Start

### Prerequisites

- Docker 20.10+ or Docker Desktop
- Docker Compose 2.0+ (for local development)
- Make (for convenience commands)

### Building the Image Locally

```bash
# Build the image with all supported tags
make docker-build

# Or directly with Docker
docker build -t ghcr.io/mcp-souschef:latest .
```

### Running Locally

```bash
# Start with docker-compose (recommended for development)
make docker-run

# Access the UI at: http://localhost:9999

# View logs
make docker-logs

# Stop the container
make docker-stop
```

## Published Images on GitHub Container Registry (GHCR)

The SousChef project automatically publishes Docker images to [GitHub Container Registry](https://ghcr.io) on each release.

### Finding the Image

1. **Direct URL**: https://ghcr.io/mcp-souschef
2. **GitHub Package Page**: https://github.com/kpeacocke/souschef/pkgs/container/mcp-souschef
3. **Command Line**:
   ```bash
   docker search ghcr.io/mcp-souschef
   ```

### What's Displayed on GHCR

The image metadata includes:

- **Title**: "SousChef - MCP AI Chef to Ansible Converter"
- **Description**: "AI-powered Model Context Protocol server and web UI for converting Chef cookbooks to Ansible playbooks"
- **License**: MIT
- **Vendor**: SousChef Project
- **Documentation**: https://kpeacocke.github.io/souschef/
- **Source**: https://github.com/kpeacocke/souschef

### Available Tags

- `latest` - Most recent release
- `3.2.0` - Specific version (semver)
- `3.2` - Latest patch of minor version
- `3` - Latest patch of major version

### Pulling and Running Images

```bash
# Pull latest release
docker pull ghcr.io/mcp-souschef:latest

# Pull specific version
docker pull ghcr.io/mcp-souschef:3.2.0

# Run with environment configuration
docker run -p 9999:9999 \
  --env-file .env \
  ghcr.io/mcp-souschef:latest

# Check image details
docker inspect ghcr.io/mcp-souschef:latest
```

## Image Architecture

### Multi-Stage Build

The Dockerfile uses three build stages for optimal efficiency:

1. **Base Stage** (`base`)
   - Python slim image with security updates
   - System dependencies (curl, git, ca-certificates)
   - Non-root user creation
   - OCI metadata labels

2. **Builder Stage** (`builder`)
   - Build dependencies (gcc, python3-dev)
   - Poetry installation and configuration
   - Dependency compilation and installation
   - Discarded in final image (keeps image small)

3. **Production Stage** (`production`)
   - Minimal base image
   - Pre-compiled dependencies from builder
   - Application code
   - Security hardening (read-only filesystem, reduced tmpfs)

### Image Size Optimisation

- Uses `python:3.14-slim` instead of full image (~40MB vs 900MB)
- Multi-stage build discards build dependencies
- Aggressive apt cleanup (`rm -rf /var/lib/apt/lists/*`)
- Layer caching for faster rebuilds

## Building for Production

### Automated Publishing (GitHub Actions)

The repository includes automated Docker publishing via GitHub Actions:

```
.github/workflows/docker-publish.yml
```

Triggers:
- Tags matching `v[0-9]+.[0-9]+.[0-9]+` (releases)
- Pushes to `main` branch (tags with `latest`)
- Manual workflow dispatch for testing

Features:
- Multi-platform builds (amd64, arm64)
- Automatic tagging (version-based)
- Push to GitHub Container Registry (GHCR)
- Vulnerability scanning with Trivy
- SBOM generation
- Image testing

### Manual Publishing

```bash
# Login to registry (GHCR)
docker login ghcr.io

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/mcp-souschef:v1.0.0 \
  --push .
```

## Configuration

### Environment Variables

Standard Streamlit environment variables can be set via:

1. `.env` file in project root
2. `docker run -e VARIABLE=VALUE`
3. `docker-compose.yml` environment section

Key variables:

```bash
STREAMLIT_SERVER_PORT=9999              # UI port
STREAMLIT_SERVER_HEADLESS=true          # No browser auto-open
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false  # Disable telemetry
STREAMLIT_SERVER_ENABLE_CORS=true       # Enable CORS
STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true  # Enable XSRF protection
PYTHONUNBUFFERED=1                      # Immediate log output
```

### Docker Compose Configuration

The `docker-compose.yml` file provides:

```yaml
services:
  souschef-ui:
    # Security options
    security_opt:
      - no-new-privileges:true  # Prevent escalation
    read_only: true              # Read-only filesystem
    tmpfs:                        # Temporary filesystems with restrictions
      - /tmp:noexec,nosuid
      - /run:noexec,nosuid

    # Resource limits
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: 0.5

    # Health monitoring
    healthcheck:
      test: python -m souschef.ui.health_check
      interval: 30s
      timeout: 10s
      retries: 3
```

## Deployment

### Kubernetes

Example deployment manifest:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: souschef-ui
spec:
  replicas: 2
  selector:
    matchLabels:
      app: souschef-ui
  template:
    metadata:
      labels:
        app: souschef-ui
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
      containers:
      - name: souschef-ui
        image: ghcr.io/mcp-souschef:v1.0.0
        ports:
        - containerPort: 9999
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 9999
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /healthz
            port: 9999
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Docker Swarm

```bash
# Pull image from registry
docker pull ghcr.io/mcp-souschef:v1.0.0

# Create service
docker service create \
  --name souschef-ui \
  --publish 9999:9999 \
  --limit-memory 1G \
  --limit-cpus 0.5 \
  ghcr.io/mcp-souschef:v1.0.0
```

### Plain Docker

```bash
# Pull image
docker pull ghcr.io/mcp-souschef:v1.0.0

# Run container
docker run -d \
  --name souschef-ui \
  -p 9999:9999 \
  --memory 1g \
  --cpus 0.5 \
  --restart unless-stopped \
  -e STREAMLIT_SERVER_HEADLESS=true \
  ghcr.io/mcp-souschef:v1.0.0
```

## Testing

### Local Testing

```bash
# Build and test image
make docker-test

# Manually test with docker run
docker run --rm \
  -p 9999:9999 \
  ghcr.io/mcp-souschef:latest

# Test health check
docker run --rm \
  ghcr.io/mcp-souschef:latest \
  python -m souschef.ui.health_check
```

### Security Scanning

```bash
# Scan with Trivy (requires Trivy installation)
make docker-scan

# Or manually
trivy image ghcr.io/mcp-souschef:latest
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs <container_id>

# Run with verbose logging
docker run -e STREAMLIT_LOGGER_LEVEL=debug ghcr.io/mcp-souschef:latest
```

### Permission denied errors

Ensure the container runs with proper permissions:

```bash
# Check running user
docker exec <container_id> whoami
# Should output: app

# Check file permissions
docker exec <container_id> ls -la /app
```

### Health check failing

```bash
# Test health check manually
docker run --rm \
  ghcr.io/mcp-souschef:latest \
  python -m souschef.ui.health_check

# Expected output:
# {"status": "healthy", "service": "souschef-ui", "version": "X.Y.Z"}
```

### Memory/CPU issues

Adjust resource limits in `docker-compose.yml` or deployment:

```yaml
deploy:
  resources:
    limits:
      memory: 2G      # Increase from 1G
      cpus: '1'       # Increase from 0.5
    reservations:
      memory: 512M    # Increase from 256M
      cpus: '0.5'     # Increase from 0.25
```

## Best Practices

1. **Always use version tags**
   ```bash
   # Good
   docker pull ghcr.io/mcp-souschef:v1.0.0

   # Avoid (unpredictable)
   docker pull ghcr.io/mcp-souschef:latest
   ```

2. **Run as non-root user**
   ```bash
   # Already configured in image (user: app, uid: 1001)
   # Verify with:
   docker run ghcr.io/mcp-souschef:latest id
   # uid=1001(app) gid=1001(app) groups=1001(app)
   ```

3. **Use health checks**
   - Configured in image and compose
   - Validates application readiness
   - Enables orchestration decisions

4. **Set resource limits**
   - Prevents resource exhaustion
   - Improves orchestration efficiency
   - See docker-compose.yml for examples

5. **Monitor logs**
   ```bash
   docker logs -f <container_id>
   docker-compose logs -f souschef-ui
   ```

6. **Use read-only filesystem**
   - Configured in docker-compose.yml
   - Reduces attack surface
   - tmpfs used for temporary data

## Image Metadata

The image includes comprehensive OCI metadata:

```
org.opencontainers.image.title=SousChef UI
org.opencontainers.image.description=AI-powered UI for Chef to Ansible conversion
org.opencontainers.image.authors=SousChef Contributors
org.opencontainers.image.licenses=MIT
org.opencontainers.image.url=https://github.com/kpeacocke/souschef
org.opencontainers.image.documentation=https://kpeacocke.github.io/souschef/
org.opencontainers.image.source=https://github.com/kpeacocke/souschef
```

View metadata:

```bash
docker inspect ghcr.io/mcp-souschef:latest | grep -A10 Labels
```

## Registry Information

### GitHub Container Registry (GHCR)

- Registry: `ghcr.io`
- Image: `ghcr.io/mcp-souschef`
- Documentation: https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- Authentication: GitHub token or personal access token

```bash
# Login
docker login ghcr.io

# Pull
docker pull ghcr.io/mcp-souschef:v1.0.0
```

## Additional Resources

- [Dockerfile Best Practices](https://docs.docker.com/develop/dev-best-practices/dockerfile_best-practices/)
- [OCI Image Spec](https://specs.opencontainers.org/image-spec/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Streamlit Docker Guide](https://docs.streamlit.io/knowledge-base/tutorials/deploy/docker)
- [Trivy Vulnerability Scanner](https://github.com/aquasecurity/trivy)
