# Mock AWX/AAP Testing Guide

This guide shows you how to test AWX/Ansible Automation Platform API integrations **without a real AWX server** using mocked HTTP responses.

## Why Mock AWX Testing?

- **No Infrastructure Required**: Test without deploying AWX/Tower
- **Fast Execution**: Tests run in milliseconds
- **Reliable**: No network dependencies or authentication complexity
- **Controlled Scenarios**: Test edge cases, errors, and specific API responses
- **CI/CD Friendly**: Run in any environment without AWX infrastructure

## Quick Start

### Run All Mock Tests

```bash
# Run all AWX mock API tests
poetry run pytest tests/integration/test_awx_mock.py -v

# Run with specific test class
poetry run pytest tests/integration/test_awx_mock.py::TestAWXMockJobTemplates -v

# Run single test
poetry run pytest tests/integration/test_awx_mock.py::TestAWXMockJobs::test_get_job_status -v
```

### Example Output

```
tests/integration/test_awx_mock.py::TestAWXMockJobTemplates::test_list_job_templates PASSED
tests/integration/test_awx_mock.py::TestAWXMockJobTemplates::test_create_job_template PASSED
tests/integration/test_awx_mock.py::TestAWXMockJobTemplates::test_launch_job_template PASSED
tests/integration/test_awx_mock.py::TestAWXMockInventories::test_list_inventories PASSED
...
======================== 20 passed in 1.2s ========================
```

## AWX API Coverage

The mock tests cover all major AWX/AAP API endpoints:

### ✅ Job Templates
- List job templates
- Create job template
- Launch job template
- Get job template details

### ✅ Inventories
- List inventories
- Sync inventory sources
- Get inventory hosts and groups

### ✅ Projects
- List projects
- Update project (SCM sync)
- Get project details

### ✅ Credentials
- List credentials
- Create credentials
- Manage credential types

### ✅ Workflows
- List workflow templates
- Launch workflow
- Get workflow job status

### ✅ Jobs & Monitoring
- Get job status
- Get job output/stdout
- Cancel running jobs
- List job events

### ✅ Authentication & Errors
- 401 Unauthorized responses
- 403 Forbidden responses
- 404 Not Found responses
- 400 Validation errors

### ✅ Organizations
- List organizations
- Get organization details

## How It Works

Mock AWX testing uses the **`responses`** library to intercept HTTP requests:

```python
import responses
import requests

@responses.activate
def test_awx_job_template():
    # Mock AWX API response
    responses.add(
        responses.GET,
        "https://awx.example.com/api/v2/job_templates/",
        json={
            "count": 1,
            "results": [
                {
                    "id": 1,
                    "name": "Deploy Apache",
                    "playbook": "apache_deploy.yml"
                }
            ]
        },
        status=200
    )

    # Make real HTTP request (intercepted by responses)
    response = requests.get(
        "https://awx.example.com/api/v2/job_templates/",
        headers={"Authorization": "Bearer test-token"}
    )

    # Verify response
    assert response.status_code == 200
    assert response.json()["count"] == 1
```

## Writing Your Own AWX Mock Tests

### Basic Structure

```python
import responses
import requests

@responses.activate
def test_my_awx_feature():
    # 1. Setup mock AWX response
    responses.add(
        responses.POST,
        "https://awx.example.com/api/v2/job_templates/1/launch/",
        json={
            "job": 42,
            "status": "pending"
        },
        status=201
    )

    # 2. Make API call
    response = requests.post(
        "https://awx.example.com/api/v2/job_templates/1/launch/",
        json={"extra_vars": {"env": "prod"}},
        headers={"Authorization": "Bearer test-token"}
    )

    # 3. Assert results
    assert response.status_code == 201
    assert response.json()["job"] == 42
```

### Testing Job Launches

```python
@responses.activate
def test_launch_and_monitor_job():
    # Mock job launch
    responses.add(
        responses.POST,
        "https://awx.example.com/api/v2/job_templates/1/launch/",
        json={"job": 42, "status": "pending"},
        status=201
    )

    # Mock job status check
    responses.add(
        responses.GET,
        "https://awx.example.com/api/v2/jobs/42/",
        json={"id": 42, "status": "successful", "failed": False},
        status=200
    )

    # Launch job
    launch_response = requests.post(
        "https://awx.example.com/api/v2/job_templates/1/launch/",
        headers={"Authorization": "Bearer test-token"}
    )
    job_id = launch_response.json()["job"]

    # Check job status
    status_response = requests.get(
        f"https://awx.example.com/api/v2/jobs/{job_id}/",
        headers={"Authorization": "Bearer test-token"}
    )

    assert status_response.json()["status"] == "successful"
```

### Testing Workflows

```python
@responses.activate
def test_workflow_execution():
    # Mock workflow launch
    responses.add(
        responses.POST,
        "https://awx.example.com/api/v2/workflow_job_templates/1/launch/",
        json={"workflow_job": 25, "status": "pending"},
        status=201
    )

    # Mock workflow status
    responses.add(
        responses.GET,
        "https://awx.example.com/api/v2/workflow_jobs/25/",
        json={
            "id": 25,
            "status": "successful",
            "workflow_nodes": [
                {"job": 42, "status": "successful"},
                {"job": 43, "status": "successful"}
            ]
        },
        status=200
    )

    # Launch workflow
    response = requests.post(
        "https://awx.example.com/api/v2/workflow_job_templates/1/launch/",
        headers={"Authorization": "Bearer test-token"}
    )

    workflow_job_id = response.json()["workflow_job"]

    # Check workflow status
    status = requests.get(
        f"https://awx.example.com/api/v2/workflow_jobs/{workflow_job_id}/",
        headers={"Authorization": "Bearer test-token"}
    )

    assert status.json()["status"] == "successful"
```

### Testing Inventory Updates

```python
@responses.activate
def test_inventory_sync():
    # Mock inventory source sync
    responses.add(
        responses.POST,
        "https://awx.example.com/api/v2/inventory_sources/5/update/",
        json={"inventory_update": 15, "status": "pending"},
        status=202
    )

    # Mock inventory update status
    responses.add(
        responses.GET,
        "https://awx.example.com/api/v2/inventory_updates/15/",
        json={"id": 15, "status": "successful", "total_hosts": 50},
        status=200
    )

    # Trigger sync
    sync_response = requests.post(
        "https://awx.example.com/api/v2/inventory_sources/5/update/",
        headers={"Authorization": "Bearer test-token"}
    )

    update_id = sync_response.json()["inventory_update"]

    # Check sync status
    status = requests.get(
        f"https://awx.example.com/api/v2/inventory_updates/{update_id}/",
        headers={"Authorization": "Bearer test-token"}
    )

    assert status.json()["total_hosts"] == 50
```

## Common AWX API Patterns

### List Resources (GET with Pagination)

```python
responses.add(
    responses.GET,
    "https://awx.example.com/api/v2/job_templates/",
    json={
        "count": 100,
        "next": "/api/v2/job_templates/?page=2",
        "previous": None,
        "results": [
            {"id": 1, "name": "Template 1"},
            {"id": 2, "name": "Template 2"}
        ]
    },
    status=200
)
```

### Create Resource (POST)

```python
responses.add(
    responses.POST,
    "https://awx.example.com/api/v2/job_templates/",
    json={
        "id": 3,
        "name": "New Template",
        "created": "2026-02-16T12:00:00Z"
    },
    status=201
)
```

### Update Resource (PATCH/PUT)

```python
responses.add(
    responses.PATCH,
    "https://awx.example.com/api/v2/job_templates/1/",
    json={
        "id": 1,
        "name": "Updated Template",
        "modified": "2026-02-16T12:00:00Z"
    },
    status=200
)
```

### Delete Resource (DELETE)

```python
responses.add(
    responses.DELETE,
    "https://awx.example.com/api/v2/job_templates/1/",
    status=204  # No content
)
```

### Authentication Errors

```python
responses.add(
    responses.GET,
    "https://awx.example.com/api/v2/job_templates/",
    json={"detail": "Authentication credentials were not provided."},
    status=401
)
```

## AWX API Authentication Methods

AWX supports multiple authentication methods:

### Bearer Token (Recommended for testing)

```python
headers = {"Authorization": "Bearer test-token"}
```

### Basic Auth

```python
import base64

auth = base64.b64encode(b"username:password").decode()
headers = {"Authorization": f"Basic {auth}"}
```

### Session Auth (OAuth2)

```python
# Mock OAuth token endpoint
responses.add(
    responses.POST,
    "https://awx.example.com/api/o/token/",
    json={"access_token": "test-token", "expires_in": 36000},
    status=200
)
```

## Testing Error Scenarios

### Validation Errors

```python
@responses.activate
def test_invalid_job_template():
    responses.add(
        responses.POST,
        "https://awx.example.com/api/v2/job_templates/",
        json={
            "name": ["This field is required."],
            "inventory": ["Invalid inventory ID."]
        },
        status=400
    )

    response = requests.post(
        "https://awx.example.com/api/v2/job_templates/",
        json={"description": "Missing required fields"},
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 400
    assert "name" in response.json()
```

### Permission Errors

```python
@responses.activate
def test_insufficient_permissions():
    responses.add(
        responses.POST,
        "https://awx.example.com/api/v2/job_templates/1/launch/",
        json={"detail": "You do not have permission to perform this action."},
        status=403
    )

    response = requests.post(
        "https://awx.example.com/api/v2/job_templates/1/launch/",
        headers={"Authorization": "Bearer limited-token"}
    )

    assert response.status_code == 403
```

### Resource Not Found

```python
@responses.activate
def test_template_not_found():
    responses.add(
        responses.GET,
        "https://awx.example.com/api/v2/job_templates/999/",
        json={"detail": "Not found."},
        status=404
    )

    response = requests.get(
        "https://awx.example.com/api/v2/job_templates/999/",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 404
```

## Debugging Mock Tests

### Inspect Requests Made

```python
@responses.activate
def test_with_debugging():
    responses.add(responses.GET, "https://awx.example.com/api/v2/jobs/42/", json={}, status=200)

    requests.get("https://awx.example.com/api/v2/jobs/42/", headers={"Authorization": "Bearer test"})

    # Debug: see what was sent
    print(f"Total requests: {len(responses.calls)}")
    print(f"URL: {responses.calls[0].request.url}")
    print(f"Headers: {dict(responses.calls[0].request.headers)}")
```

### Verify Query Parameters

```python
@responses.activate
def test_with_query_params():
    responses.add(
        responses.GET,
        "https://awx.example.com/api/v2/job_templates/",
        json={"results": []},
        status=200,
        match=[responses.matchers.query_param_matcher({"page": "2", "page_size": "20"})]
    )

    # This will only match if query params are exactly as specified
    response = requests.get(
        "https://awx.example.com/api/v2/job_templates/",
        params={"page": 2, "page_size": 20}
    )
```

## Performance

Mock AWX tests are extremely fast:

```bash
# 20 comprehensive AWX API tests in ~1.2 seconds
poetry run pytest tests/integration/test_awx_mock.py -v
# 20 passed in 1.20s
```

Compare to real AWX API calls which might take 1-3 seconds each due to:
- Network latency
- TLS handshake
- Authentication
- Database queries
- Job scheduling

## CI/CD Integration

<Mock tests work perfectly in CI/CD:

```yaml
# .github/workflows/test.yml
- name: Run AWX Mock Tests
  run: poetry run pytest tests/integration/test_awx_mock.py -v
```

No AWX infrastructure needed!

## Combining with Chef Server Mocks

Test complete migration scenarios by mocking both Chef Server AND AWX:

```python
@responses.activate
def test_chef_to_awx_migration():
    # Mock Chef Server node query
    responses.add(
        responses.GET,
        "https://chef.example.com/organizations/default/search/node",
        json={"rows": [{"name": "web-01", "platform": "ubuntu"}]},
        status=200
    )

    # Mock AWX inventory creation
    responses.add(
        responses.POST,
        "https://awx.example.com/api/v2/inventories/",
        json={"id": 5, "name": "Chef Migrated Hosts"},
        status=201
    )

    # Mock AWX host creation
    responses.add(
        responses.POST,
        "https://awx.example.com/api/v2/inventories/5/hosts/",
        json={"id": 10, "name": "web-01"},
        status=201
    )

    # Your migration code here...
    # 1. Query Chef Server for nodes
    # 2. Create AWX inventory
    # 3. Populate AWX inventory with nodes
```

## Real AWX Testing

For testing with a real AWX instance, see:
- [AWX Official Docs](https://docs.ansible.com/ansible-tower/latest/html/userguide/index.html)
- [AWX CLI](https://github.com/ansible/awx/tree/devel/awxkit)
- [AWX API Guide](https://docs.ansible.com/ansible-tower/latest/html/towerapi/index.html)

## Further Reading

- **AWX API Documentation**: https://docs.ansible.com/ansible-tower/latest/html/towerapi/
- **responses library**: https://github.com/getsentry/responses
- **Mock tests**: [tests/integration/test_awx_mock.py](../../tests/integration/test_awx_mock.py)
- **Chef Server mocks**: [MOCK_CHEF_SERVER.md](MOCK_CHEF_SERVER.md)
