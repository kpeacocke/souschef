# Mock Chef Server Testing Guide

This guide shows you how to test Chef Server integration **without a real Chef Server** using mocked HTTP responses.

## Why Mock Testing?

- **No Infrastructure Required**: Test without deploying a Chef Server
- **Fast Execution**: Tests run in milliseconds instead of seconds
- **Reliable**: No network dependencies or flaky connections
- **Controlled Scenarios**: Test edge cases like timeouts, auth failures, and malformed responses
- **CI/CD Friendly**: Run in any environment without external dependencies

## Quick Start

### Run All Mock Tests

```bash
# Run all Chef Server mock integration tests
poetry run pytest tests/integration/test_chef_server_mock.py -v

# Run with coverage
poetry run pytest tests/integration/test_chef_server_mock.py --cov=souschef.core.chef_server -v

# Run specific test class
poetry run pytest tests/integration/test_chef_server_mock.py::TestChefServerMockIntegration -v
```

### Example Output

```
tests/integration/test_chef_server_mock.py::TestChefServerMockIntegration::test_connection_success PASSED
tests/integration/test_chef_server_mock.py::TestChefServerMockIntegration::test_search_nodes PASSED
tests/integration/test_chef_server_mock.py::TestChefServerMockIntegration::test_list_roles PASSED
tests/integration/test_chef_server_mock.py::TestChefServerMockIntegration::test_list_cookbooks PASSED
...
======================== 18 passed in 1.55s ========================
```

## Test Coverage

The mock integration tests cover:

### ✅ Connection & Authentication
- Successful Chef Server connections with RSA-signed requests
- 401 Authentication failures (invalid credentials)
- 403 Authorization failures (access denied)
- 404 Not Found errors (missing endpoints)
- Connection timeouts
- 500 Internal Server Errors

### ✅ Node Search & Queries
- Searching nodes by query (`role:webserver`, `*:*`)
- Node metadata extraction (name, roles, environment, platform, IP, FQDN)
- Empty result handling
- Multiple node responses

### ✅ Chef Server Resources
- Listing roles with URLs
- Listing environments (production, staging, _default)
- Listing cookbooks with version metadata
- Listing policies (policyfiles)
- Getting specific cookbook versions

### ✅ Authentication Headers
- X-Ops-Userid (client name)
- X-Ops-Sign (signature algorithm and version)
- X-Ops-Timestamp (request timestamp)
- X-Ops-Content-Hash (body hash)
- X-Ops-Authorization-{1..N} (signature chunks, ≤60 chars each)
- Query parameters included in signature

### ✅ Error Handling
- Malformed JSON responses
- Empty/missing data in responses
- Network errors and timeouts
- Secrets redaction in error messages

## How It Works

The mock tests use the **`responses`** library to intercept HTTP requests and return predefined responses:

```python
import responses

@responses.activate
def test_search_nodes():
    # Mock the Chef Server API response
    responses.add(
        responses.GET,
        "https://chef.example.com/organizations/testorg/search/node",
        json={"rows": [{"name": "web-01", "platform": "ubuntu"}]},
        status=200
    )

    # Call the real Chef Server client
    client = ChefServerClient(config)
    nodes = client.search_nodes("*:*")

    # Verify the response
    assert len(nodes) == 1
    assert nodes[0]["name"] == "web-01"

    # Verify auth headers were sent
    assert "X-Ops-Userid" in responses.calls[0].request.headers
```

**What happens:**
1. `@responses.activate` intercepts all HTTP requests
2. `responses.add()` defines mock HTTP responses
3. Your code makes real HTTP requests using `requests` library
4. `responses` returns the mocked data instead of hitting the network
5. You can inspect `responses.calls` to verify headers, parameters, etc.

## Writing Your Own Mock Tests

### Basic Structure

```python
import responses
from souschef.core.chef_server import ChefServerClient, ChefServerConfig

@responses.activate
def test_my_chef_server_feature():
    # 1. Setup mock response
    responses.add(
        responses.GET,  # HTTP method
        "https://chef.example.com/organizations/testorg/roles",  # URL
        json={"webserver": {"url": "..."}},  # Response body
        status=200  # HTTP status code
    )

    # 2. Create client config
    config = ChefServerConfig(
        server_url="https://chef.example.com",
        organisation="testorg",
        client_name="testclient",
        client_key=test_key,  # Use test RSA key
        timeout=10
    )

    # 3. Call the API
    client = ChefServerClient(config)
    roles = client.list_roles()

    # 4. Assert results
    assert len(roles) == 1
    assert roles[0]["name"] == "webserver"
```

### Testing Error Scenarios

```python
@responses.activate
def test_auth_failure():
    # Mock 401 authentication failure
    responses.add(
        responses.GET,
        "https://chef.example.com/organizations/testorg/search/node",
        json={"error": "Invalid signature"},
        status=401
    )

    client = ChefServerClient(config)
    success, message = client.test_connection()

    assert success is False
    assert "Authentication failed" in message
```

### Testing Query Parameters

```python
@responses.activate
def test_query_params():
    # Verify specific query params are sent
    responses.add(
        responses.GET,
        "https://chef.example.com/organizations/testorg/search/node",
        json={"rows": []},
        status=200,
        match=[responses.matchers.query_param_matcher({"q": "role:webserver"})]
    )

    client = ChefServerClient(config)
    nodes = client.search_nodes("role:webserver")

    # Matcher will fail if query params don't match
    assert len(responses.calls) == 1
```

### Inspecting Request Headers

```python
@responses.activate
def test_auth_headers():
    responses.add(
        responses.GET,
        "https://chef.example.com/organizations/testorg/search/node",
        json={"rows": []},
        status=200
    )

    client = ChefServerClient(config)
    client.test_connection()

    # Inspect the actual request that was made
    request_headers = responses.calls[0].request.headers

    assert "X-Ops-Userid" in request_headers
    assert request_headers["X-Ops-Userid"] == "testclient"
    assert "X-Ops-Sign" in request_headers
    assert "X-Ops-Authorization-1" in request_headers
```

## Common Mock Response Patterns

### Successful Node Search

```python
responses.add(
    responses.GET,
    "https://chef.example.com/organizations/testorg/search/node",
    json={
        "rows": [
            {
                "name": "web-01",
                "run_list": ["role[webserver]"],
                "chef_environment": "production",
                "platform": "ubuntu",
                "ipaddress": "10.0.1.10",
                "fqdn": "web-01.example.com",
                "automatic": {"platform": "ubuntu"}
            }
        ],
        "total": 1,
        "start": 0
    },
    status=200
)
```

### Roles List

```python
responses.add(
    responses.GET,
    "https://chef.example.com/organizations/testorg/roles",
    json={
        "webserver": {"url": "https://chef.example.com/roles/webserver"},
        "database": {"url": "https://chef.example.com/roles/database"}
    },
    status=200
)
```

### Cookbooks with Versions

```python
responses.add(
    responses.GET,
    "https://chef.example.com/organizations/testorg/cookbooks",
    json={
        "apache2": {
            "url": "https://chef.example.com/cookbooks/apache2",
            "versions": [
                {"url": "https://chef.example.com/cookbooks/apache2/8.6.0"}
            ]
        }
    },
    status=200
)
```

### Authentication Failure

```python
responses.add(
    responses.GET,
    "https://chef.example.com/organizations/testorg/search/node",
    json={"error": "Authentication failed"},
    status=401
)
```

### Connection Timeout

```python
responses.add(
    responses.GET,
    "https://chef.example.com/organizations/testorg/search/node",
    body=Exception("Connection timeout")
)
```

## Fixtures for Test Keys

Use these fixtures in your tests:

```python
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

@pytest.fixture
def test_key() -> str:
    """Generate a test RSA private key."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return key_pem.decode("utf-8")

@pytest.fixture
def test_config(test_key: str) -> ChefServerConfig:
    """Create a test Chef Server configuration."""
    return ChefServerConfig(
        server_url="https://chef.example.com",
        organisation="testorg",
        client_name="testclient",
        client_key=test_key,
        timeout=10,
    )
```

## Combining Unit & Mock Tests

**Use unit tests for:** Testing individual functions with mocked dependencies
- [tests/unit/test_chef_server_client.py](../tests/unit/test_chef_server_client.py) - Auth helpers, URL normalization, secrets redaction

**Use mock integration tests for:** Testing full request/response flow
- [tests/integration/test_chef_server_mock.py](../tests/integration/test_chef_server_mock.py) - End-to-end API calls with mocked HTTP

**Use real integration tests for:** Testing with actual Chef Server (optional)
- [docs/testing/CHEF_SERVER_TESTING.md](CHEF_SERVER_TESTING.md) - Live Chef Server testing guide

## Debugging Mock Tests

### See What Requests Were Made

```python
@responses.activate
def test_debug():
    responses.add(responses.GET, "https://chef.example.com/...", json={}, status=200)

    client.search_nodes("*:*")

    # Print all captured requests
    print(f"Total requests: {len(responses.calls)}")
    for call in responses.calls:
        print(f"Method: {call.request.method}")
        print(f"URL: {call.request.url}")
        print(f"Headers: {dict(call.request.headers)}")
```

### Verify Mock Was Called

```python
@responses.activate
def test_verify_call():
    responses.add(responses.GET, "https://chef.example.com/...", json={}, status=200)

    client.search_nodes("*:*")

    assert len(responses.calls) == 1
    assert responses.calls[0].request.method == "GET"
```

### Test Multiple Endpoints

```python
@responses.activate
def test_multiple_calls():
    # Add multiple mocks
    responses.add(responses.GET, ".../search/node", json={"rows": []}, status=200)
    responses.add(responses.GET, ".../roles", json={}, status=200)
    responses.add(responses.GET, ".../environments", json={}, status=200)

    # Make multiple requests
    client.search_nodes("*:*")
    client.list_roles()
    client.list_environments()

    # All three should have been called
    assert len(responses.calls) == 3
```

## Performance

Mock tests are **much faster** than real network calls:

```bash
# Mock tests: ~0.08 seconds per test
poetry run pytest tests/integration/test_chef_server_mock.py -v
# 18 passed in 1.55s

# Unit tests: ~0.05 seconds per test
poetry run pytest tests/unit/test_chef_server_client.py -v
# 13 passed in 0.85s
```

Compare to a real Chef Server which might take 0.5-2 seconds per API call due to:
- Network latency
- TLS handshake
- Request signing computation
- Server processing time

## CI/CD Integration

Mock tests work perfectly in CI/CD pipelines:

```yaml
# .github/workflows/test.yml
- name: Run Chef Server Mock Tests
  run: poetry run pytest tests/integration/test_chef_server_mock.py -v
```

No Chef Server required in CI environments!

## Troubleshooting

### Error: "Connection refused"

If you see connection errors, ensure `@responses.activate` decorator is present:

```python
@responses.activate  # ← Don't forget this!
def test_my_feature():
    responses.add(...)
```

### Error: "No mock address"

If the URL doesn't match, `responses` won't intercept it. Ensure URLs match exactly:

```python
# ❌ Wrong - URL mismatch
responses.add(responses.GET, "https://chef.com/...", ...)
client = ChefServerClient(config)  # config uses chef.example.com

# ✅ Correct - URLs match
responses.add(responses.GET, "https://chef.example.com/...", ...)
```

### Inspecting Signature Generation

To debug signature issues, use the unit tests instead:

```bash
# Test signature generation without HTTP
poetry run pytest tests/unit/test_chef_server_client.py::TestChefServerAuthHelpers::test_build_auth_headers_includes_signature -v
```

## Further Reading

- **responses documentation**: https://github.com/getsentry/responses
- **Unit tests**: [tests/unit/test_chef_server_client.py](../tests/unit/test_chef_server_client.py)
- **Mock integration tests**: [tests/integration/test_chef_server_mock.py](../tests/integration/test_chef_server_mock.py)
- **Live testing guide**: [CHEF_SERVER_TESTING.md](CHEF_SERVER_TESTING.md)
- **Chef Server API docs**: https://docs.chef.io/server/api_chef_server/
