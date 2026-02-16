# Chef Server Integration Testing Guide

This guide explains how to test the authenticated Chef Server integration with a **live Chef Server**, including secrets redaction functionality.

> **💡 Testing Without Chef Server?** See [Mock Chef Server Testing Guide](MOCK_CHEF_SERVER.md) for testing with mocked HTTP responses - no Chef Server required!

## Quick Links

- **[Mock Testing Guide](MOCK_CHEF_SERVER.md)** - Test without a real Chef Server (recommended for development)
- **[Unit Tests](../../tests/unit/test_chef_server_client.py)** - Auth helpers and utility functions
- **[Mock Integration Tests](../../tests/integration/test_chef_server_mock.py)** - Full API flow with mocked responses
- **This Guide** - Testing with a live Chef Server instance

## Prerequisites

1. **Chef Server Access**: You need access to a Chef Server instance (Chef Infra Server, Hosted Chef, or AWS OpsWorks Chef Automate)
2. **Chef Client Credentials**: A client or user account with API access
3. **RSA Private Key**: The PEM-encoded private key for authentication

## Setting Up Test Environment

### Option 1: Using Chef Manage (Chef Server Web UI)

1. **Log into Chef Manage**:
   ```bash
   # Navigate to your Chef Server in a browser
   https://your-chef-server.example.com
   ```

2. **Create or Select a Client**:
   - Go to Policy → Clients
   - Create a new client or select an existing one
   - Download the private key (only shown once during creation)

3. **Note Your Organisation**:
   - Check the URL or dashboard for your organisation name
   - Common default is `"default"` or your company name

### Option 2: Using Chef Workstation CLI

1. **Install Chef Workstation**:
   ```bash
   # macOS
   brew install chef-workstation

   # Linux (see https://www.chef.io/downloads)
   ```

2. **Configure Knife**:
   ```bash
   knife configure
   # Enter your Chef Server URL, organisation, and user name
   ```

3. **Locate Your Credentials**:
   ```bash
   # Default location
   cat ~/.chef/client.pem
   ```

### Option 3: Local Test Chef Server (Docker)

For testing without production access, spin up a local Chef Server:

```bash
# Using Docker Compose
docker run -d \
  --name chef-server \
  -p 443:443 \
  chef/chef-server:latest

# Access container to create client
docker exec -it chef-server bash
chef-server-ctl user-create testuser Test User test@example.com password123
chef-server-ctl org-create testorg "Test Organisation" --association_user testuser
```

## Configuration

### Environment Variables Method (Recommended)

Set up environment variables for testing:

```bash
# Required
export CHEF_SERVER_URL="https://your-chef-server.example.com"
export CHEF_CLIENT_NAME="your-client-name"
export CHEF_CLIENT_KEY_PATH="/path/to/client.pem"

# Optional (defaults shown)
export CHEF_ORG="default"
```

### Direct Parameter Method

Alternatively, pass credentials directly to tools (useful for testing different configurations):

```bash
# See examples in CLI Testing section below
```

## Testing Secrets Redaction

### Test 1: Invalid Key Error (Redaction)

Test that malformed keys are redacted in error messages:

```bash
# Create a file with invalid key content
echo "-----BEGIN RSA PRIVATE KEY-----
INVALID_KEY_CONTENT_HERE
-----END RSA PRIVATE KEY-----" > /tmp/bad-key.pem

# Run validation (should fail with redacted key)
poetry run souschef validate-chef-server \
  --server-url "https://chef.example.com" \
  --organisation "default" \
  --client-name "testclient" \
  --client-key-path "/tmp/bad-key.pem"
```

**Expected Output**:
```
Failed: ***REDACTED***
# NOT: -----BEGIN RSA PRIVATE KEY----- INVALID_KEY_CONTENT_HERE ...
```

### Test 2: Authentication Failure (Redaction)

Test that authentication errors don't leak key material:

```bash
# Use a valid key format but wrong credentials
poetry run souschef validate-chef-server \
  --server-url "https://chef.example.com" \
  --organisation "wrong-org" \
  --client-name "wrong-client" \
  --client-key-path "/path/to/valid-key.pem"
```

**Expected Output**:
```
Failed: Authentication failed - check your Chef Server credentials
# NOT: Any output containing the actual key content
```

### Test 3: Connection Timeout (Safe Output)

Test network errors don't expose credentials:

```bash
# Use unreachable server
poetry run souschef validate-chef-server \
  --server-url "https://nonexistent.example.com" \
  --organisation "default" \
  --client-name "testclient" \
  --client-key-path "/path/to/client.pem"
```

**Expected Output**:
```
Failed: Connection timeout - could not reach https://nonexistent.example.com
# No key material in output
```

## CLI Testing

### Test Connection Validation

```bash
# Test with environment variables
poetry run souschef validate-chef-server \
  --server-url "$CHEF_SERVER_URL" \
  --organisation "$CHEF_ORG" \
  --client-name "$CHEF_CLIENT_NAME" \
  --client-key-path "$CHEF_CLIENT_KEY_PATH"
```

**Expected Success Output**:
```
Success: Successfully connected to Chef Server at https://your-chef-server.example.com/organizations/default
```

### Test Node Query

```bash
# Query all nodes
poetry run souschef query-chef-nodes \
  --search-query "*:*" \
  --server-url "$CHEF_SERVER_URL" \
  --organisation "$CHEF_ORG" \
  --client-name "$CHEF_CLIENT_NAME" \
  --client-key-path "$CHEF_CLIENT_KEY_PATH"
```

**Expected Output**:
```json
{
  "status": "success",
  "count": 5,
  "nodes": [
    {
      "name": "web-server-01",
      "roles": ["role[webserver]"],
      "environment": "production",
      "platform": "ubuntu",
      "ipaddress": "10.0.1.10",
      "fqdn": "web-server-01.example.com"
    },
    ...
  ]
}
```

### Test with Inline Key (Not Recommended in Production)

```bash
# Read key into variable
KEY_CONTENT=$(cat /path/to/client.pem)

# Pass inline (for testing only)
poetry run souschef validate-chef-server \
  --server-url "$CHEF_SERVER_URL" \
  --organisation "$CHEF_ORG" \
  --client-name "$CHEF_CLIENT_NAME" \
  --client-key "$KEY_CONTENT"
```

## MCP Tool Testing

### Using Claude Desktop

1. **Configure MCP Server**:

   Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent:

   ```json
   {
     "mcpServers": {
       "souschef": {
         "command": "poetry",
         "args": ["run", "python", "-m", "souschef.server"],
         "cwd": "/path/to/souschef",
         "env": {
           "CHEF_SERVER_URL": "https://your-chef-server.example.com",
           "CHEF_ORG": "default",
           "CHEF_CLIENT_NAME": "your-client",
           "CHEF_CLIENT_KEY_PATH": "/path/to/client.pem"
         }
       }
     }
   }
   ```

2. **Test in Claude Desktop**:

   Ask Claude:
   ```
   Use the validate_chef_server_connection tool to test the Chef Server connection.
   ```

   Then:
   ```
   Use get_chef_nodes to list all nodes in the Chef Server.
   ```

3. **Verify Redaction**:

   Intentionally break the configuration:
   ```json
   "CHEF_CLIENT_KEY_PATH": "/nonexistent/key.pem"
   ```

   Restart Claude Desktop and ask it to validate the connection. The error message should show `***REDACTED***` instead of any key material.

### Using MCP Inspector

For lower-level testing:

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Run with SousChef
mcp-inspector poetry run python -m souschef.server
```

Navigate to `http://localhost:5173` and test tools interactively.

## Unit Test Verification

Run the secrets redaction test suite:

```bash
# Run all redaction tests
poetry run pytest tests/unit/test_chef_server_client.py::TestSecretsRedaction -v

# Run integration test for MCP tool redaction
poetry run pytest tests/unit/test_server.py::test_validate_chef_server_connection_redacts_keys -v

# Run all Chef Server tests
poetry run pytest tests/unit/test_chef_server_ui.py tests/unit/test_chef_server_client.py \
  tests/unit/test_server.py::test_validate_chef_server_connection_success \
  tests/unit/test_server.py::test_validate_chef_server_connection_redacts_keys \
  tests/unit/test_server.py::test_get_chef_nodes_success -v
```

## Debugging

### Enable Debug Logging

To see detailed request/response information (keys still redacted):

```bash
export LOG_LEVEL=DEBUG
poetry run souschef validate-chef-server \
  --server-url "$CHEF_SERVER_URL" \
  --organisation "$CHEF_ORG" \
  --client-name "$CHEF_CLIENT_NAME" \
  --client-key-path "$CHEF_CLIENT_KEY_PATH"
```

### Test Signature Generation

Use Python interactively to test auth headers:

```python
from souschef.core.chef_server import _build_auth_headers, _load_client_key

key = _load_client_key("/path/to/client.pem", None)
headers = _build_auth_headers(
    "GET",
    "/organizations/default/search/node?q=*:*",
    b"",
    "your-client-name",
    "2026-02-16T12:00:00Z",
    key
)

print(headers)
# Should see X-Ops-Authorization-1, X-Ops-Userid, etc.
```

### Common Issues

#### "Authentication failed" with valid credentials

- **Check organisation name**: Must match Chef Server configuration
- **Verify client name**: Case-sensitive
- **Key format**: Must be unencrypted PEM format (not PKCS#8 or encrypted)

#### "Connection timeout"

- **Firewall**: Ensure port 443 is accessible
- **URL format**: Include `https://` scheme
- **DNS**: Server hostname must resolve

#### "Client key path does not exist"

- **Path resolution**: Use absolute paths, not relative
- **Permissions**: Key file must be readable
- **Path expansion**: Use `$HOME` instead of `~` in environment variables

## Security Considerations

### What Gets Redacted

The `_redact_sensitive_data()` function redacts:

1. **PEM private keys**: Any `-----BEGIN ... PRIVATE KEY-----` blocks
2. **Base64 key content**: Multi-line base64 strings (40+ chars per line)
3. **Credential assignments**: `password=value`, `token:value`, `secret="value"`

### What Doesn't Get Redacted

Safe to include in error messages:
- Server URLs
- Client/user names
- Organisation names
- Node names, roles, environments
- Status codes (401, 403, 404)

### Production Recommendations

1. **Use key paths**: Prefer `CHEF_CLIENT_KEY_PATH` over `CHEF_CLIENT_KEY`
2. **Protect key files**: Set permissions to `0600`
3. **Rotate keys**: Periodically regenerate client keys
4. **Audit logs**: Monitor Chef Server logs for API access
5. **Use secrets managers**: Store keys in Vault, AWS Secrets Manager, etc.

## Acceptance Criteria Verification

From Issue #197, verify each criterion:

- ✅ **Key-based auth**: RSA signature with X-Ops-* headers
- ✅ **Configuration**: Server URL, org, client name via env vars
- ✅ **Basic endpoints**: nodes, roles, environments, cookbooks, policies
- ✅ **Connection test**: `validate_chef_server_connection` tool
- ✅ **Clear errors**: HTTP status codes with helpful messages
- ✅ **Secrets redaction**: PEM keys and passwords masked in output

## Next Steps

After validating the integration:

1. **Test with production Chef Server** (read-only operations first)
2. **Integrate with CI/CD** (see [docs/docker-deployment.md](../docker-deployment.md))
3. **Implement cookbook downloading** (Issue #198)
4. **Add caching layer** (reduce API calls)

## Support

If you encounter issues:

1. Check the [Chef Server API documentation](https://docs.chef.io/server/api_chef_server/)
2. Review [ARCHITECTURE.md](../ARCHITECTURE.md) for code structure
3. Open an issue on GitHub with redacted error output
