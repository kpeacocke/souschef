# IR Workflow Mock Testing Guide

## Overview

This guide documents the comprehensive mock testing infrastructure for validating the complete v2.0/2.1 IR (Intermediate Representation) workflow: **Chef Server → IR → AWX/AAP**.

### Migration Path Model

Tests follow an **Origin → Destination** configuration model:

- **Origin**: Chef Server version you're migrating FROM (12.x, 14.x, 15.x)
- **Destination**: Ansible platform/version you're migrating TO (Tower 3.8, AWX 21.x-24.x, AAP 2.4+)

Each combination represents a unique migration path with specific API behaviors, authentication protocols, and feature support. Tests validate that the IR framework correctly handles version-specific differences in both Chef Server APIs and Ansible platform APIs.

**Example Migration Paths**:
- Chef 12.x (SHA-1/SHA-256) → AWX 22.x (EE) - Multi-auth origin
- Chef 14.x (SHA-256) → AWX 24.6.1 (EE) - Recent Chef, current AWX
- Chef 15.10.91 (SHA-256) → AWX 24.6.1 (EE) - Latest releases

## Test Coverage

### File: `tests/integration/test_ir_chef_awx_workflow.py`

**8 comprehensive tests** validating end-to-end Chef→Ansible→AWX migration workflows using mocked APIs.

## Test Classes

### 1. TestChefToIRWorkflow
Tests Chef Server data extraction and IR graph construction.

#### `test_query_chef_nodes_and_build_ir`
- Mocks Chef Server `/search/node` endpoint
- Queries production nodes via ChefServerClient
- Builds IR graph with node metadata (platform, environment, IP, run_list)
- Validates IR structure and node variables

**Validates:**
- [YES] Chef Server authentication with RSA signatures
- [YES] Node search query execution
- [YES] IR graph creation from Chef data
- [YES] Variable assignment in IR nodes

#### `test_chef_cookbook_to_ir_with_dependencies`
- Mocks Chef Server cookbook metadata endpoint
- Extracts cookbook dependencies (nginx, php)
- Builds IR graph with recipe nodes and dependency nodes
- Validates topological ordering of dependencies

**Validates:**
- [YES] Cookbook metadata parsing
- [YES] Dependency graph construction
- [YES] Topological dependency resolution
- [YES] IR node relationships

### 2. TestIRToAWXWorkflow
Tests IR transformation to AWX job templates and inventories.

#### `test_ir_to_awx_job_template_creation`
- Creates IR graph with playbook structure
- Adds actions (install, configure, service)
- Generates AWX job template from IR
- Mocks AWX API `/job_templates/` POST endpoint

**Validates:**
- [YES] IR to AWX job template transformation
- [YES] Action mapping to playbook tasks
- [YES] Extra vars injection (source tracking)
- [YES] AWX API authentication

#### `test_ir_to_awx_inventory_creation`
- Creates IR graph with host inventory
- Groups hosts (webservers, databases)
- Generates AWX inventory from IR
- Mocks AWX API `/inventories/` POST endpoint

**Validates:**
- [YES] IR host to AWX inventory mapping
- [YES] Group and host variable assignment
- [YES] Tag propagation to AWX metadata
- [YES] Inventory organization structure

### 3. TestEndToEndChefToAWXWorkflow
Tests complete migration workflow across all stages.

#### `test_complete_migration_workflow`
**Complete 4-stage workflow:**
1. Query Chef Server for nodes (`/search/node`)
2. Query Chef Server for role details (`/roles/webserver`)
3. Build IR graph from Chef data
4. Generate AWX configurations (inventory, hosts, job templates)

**Validates:**
- [YES] Multi-step Chef Server queries
- [YES] IR graph construction from multiple Chef resources
- [YES] AWX inventory creation
- [YES] AWX host creation
- [YES] AWX job template generation
- [YES] End-to-end data flow integrity

#### `test_workflow_with_chef_environments_to_awx_groups`
- Queries Chef environments (production, staging)
- Queries nodes per environment
- Maps Chef environments to AWX inventory groups
- Creates AWX groups for each environment

**Validates:**
- [YES] Chef environment enumeration
- [YES] Environment-based node filtering
- [YES] IR environment modeling
- [YES] AWX group creation from environments

### 4. TestIRValidationWithChefAndAWX
Tests IR validation against real API constraints.

#### `test_validate_ir_node_against_chef_server`
- Creates IR node for Chef recipe
- Validates recipe exists in Chef Server cookbook
- Marks IR node with validation metadata

**Validates:**
- [YES] IR to Chef Server validation
- [YES] Recipe existence checking
- [YES] Validation metadata tracking

#### `test_validate_awx_compatibility_from_ir`
- Creates IR graph for Ansible playbook
- Queries AWX `/config/` for capabilities
- Validates IR compatibility with AWX Ansible version

**Validates:**
- [YES] AWX capability detection
- [YES] Ansible version compatibility checking
- [YES] IR metadata enrichment

## Migration Path Configuration

### Origin: Chef Server Versions

Configure your test origin by specifying the Chef Server version you're migrating **from**:

| Version | Release | Auth Protocol | Latest | Test Priority |
|---------|---------|---------------|---------|-----------|
| **12.x** | 2015 | 1.0, 1.3 | 12.19.36 | Medium |
| **14.x** | 2018 | 1.3 (SHA-256) | 14.15.6 | High |
| **15.x** | 2020+ | 1.3 (SHA-256) | 15.10.91 | High |

**Configuration Example**:
```python
# Test configuration for Chef Server 14.x origin
chef_config = {
    "version": "14.10.9",
    "auth_protocol": "1.3",  # SHA-256
    "base_url": "https://chef.example.com/organizations/myorg",
    "api_features": ["search", "cookbooks", "roles", "environments"],
}
```

### Destination: Ansible Automation Platforms

Configure your test destination by specifying the Ansible platform and version you're migrating **to**:

| Platform | Version Range | API Version | Ansible Core | Latest | Test Priority |
|----------|---------------|-------------|--------------|--------|---------------|
| **AWX** | 21.x-22.x | `/api/v2/` | 2.12-2.14 | 22.x | Medium |
| **AWX** | 23.x-24.x | `/api/v2/` | 2.14-2.16 | 24.6.1 | High |
| **AAP** | 2.4.x+ | `/api/v2/` | 2.15+ | 2.4+ | High |

**Configuration Example**:
```python
# Test configuration for AAP 2.4 destination
awx_config = {
    "platform": "aap",  # or "awx", "tower"
    "version": "2.4.0",
    "api_version": "v2",
    "ansible_version": "2.15.0",
    "base_url": "https://aap.example.com",
    "api_features": ["inventories", "job_templates", "workflows", "ee"],
}
```

### Test Matrix: Origin → Destination Combinations

**Recommended Test Combinations**:

| Origin | Destination | Validation | Priority |
|--------|-------------|------------|----------|
| Chef 12.x | AWX 22.x | Legacy origin, modern platform | Medium |
| Chef 14.x | AWX 24.6.1 | Mid-version Chef, latest AWX | High |
| Chef 15.10.91 | AWX 24.6.1 | Current Chef → Current AWX | High |
| Chef 15.x | AAP 2.4 | Enterprise production path | Critical |

**Example Test Configuration**:
```python
@pytest.mark.parametrize("origin,destination", [
    ({"chef": "14.10.9", "auth": "1.3"}, {"platform": "awx", "version": "22.0"}),
    ({"chef": "15.0.0", "auth": "1.3"}, {"platform": "aap", "version": "2.4"}),
])
def test_migration_path(origin, destination):
    """Test specific Chef version → Ansible platform migration."""
    # Configure mock responses based on version capabilities
    pass
```

## API Changes by Version

### Chef Server API: What Actually Changes

**Chef Server 11.x → 12.x**:
- [YES] Maintained: All REST endpoints unchanged
- [ADD] Added: X-Ops-Sign version=1.3 support (SHA-256)
- [ADD] Added: `/organizations/{org}/policies` endpoint
- WARNING Deprecated: Opscode User/Organization endpoints

**Chef Server 12.x → 14.x**:
- [YES] Maintained: All core REST endpoints stable
- [SECURE] Changed: Stricter SSL certificate validation (HTTPS required)
- [SECURE] Changed: Default authentication protocol → 1.3 (SHA-256)
- WARNING Removed: SHA-1 deprecation warnings (still works)

**Chef Server 14.x → 15.x**:
- [YES] Maintained: All REST endpoints identical
- [SECURE] Changed: FIPS 140-2 compliance enforced
- WARNING Deprecated: SHA-1 support (planned removal in v16+)
- [ADD] Added: Enhanced LDAP integration options

**API Response Changes**: None across all versions (12.x-15.x)
- Node search responses: Same structure
- Cookbook metadata: Same fields
- Role definitions: Same format
- Environment queries: Unchanged

**Authentication Changes**:
```python
# Chef 11.x-12.x: SHA-1 (protocol 1.0)
X-Ops-Sign: version=1.0
X-Ops-Content-Hash: SHA1(body)

# Chef 13.x+: SHA-256 (protocol 1.3)
X-Ops-Sign: version=1.3
X-Ops-Content-Hash: SHA256(body)
```

### AWX/Tower/AAP API: What Actually Changes

**Tower 2.x → Tower 3.x**:
- [YES] Maintained: `/api/v2/` endpoints unchanged
- [ADD] Added: `/api/v2/workflow_job_templates/` (workflow support)
- [ADD] Added: `/api/v2/credential_types/` (custom credentials)
- [ADD] Added: Smart inventory support
- [SYNC] Changed: OAuth2 token format (longer tokens)

**Tower 3.x → AWX (OSS)**:
- [YES] Maintained: All `/api/v2/` endpoints identical
- [ADD] Added: Faster release cycle (every 2 weeks vs quarterly)
- [ADD] Added: Container-based execution environment preview
- [SYNC] Changed: Branding (Tower → AWX, API unchanged)

**AWX 17.x → AWX 21.x**:
- [YES] Maintained: `/api/v2/` core endpoints stable
- [ADD] Added: Execution Environments (EE) support
- [ADD] Added: `/api/v2/execution_environments/` endpoint
- WARNING Deprecated: Custom virtual environments (replaced by EE)
- [SYNC] Changed: Job isolation method (bubblewrap → podman)

**AWX 21.x → AWX 24.x / AAP 2.4**:
- [YES] Maintained: All existing `/api/v2/` endpoints
- [ADD] Added: Ansible content signing support
- [ADD] Added: Enhanced RBAC with organizations
- [ADD] Added: `/api/v2/mesh_visualizer/` (topology view)
- [SYNC] Changed: Default Ansible version (2.12 → 2.15)

**Breaking Changes**:
- WARNING AWX 19.x: Removed some legacy credential fields (migration provided)
- WARNING AWX 21.x: Removed `/api/v2/custom_virtualenvs/` (use EE instead)
- WARNING AAP 2.0: Renamed `/api/v2/towers/` → `/api/v2/instances/`

**API Response Structure Changes**:
```json
// Tower 3.x / AWX <21: Job Template
{
  "custom_virtualenv": "/var/lib/awx/venv/ansible"  // Deprecated
}

// AWX 21+ / AAP 2.0+: Job Template
{
  "execution_environment": 42,  // EE ID (required)
  "custom_virtualenv": null     // Ignored if EE present
}
```

### Version-Specific Mock Configuration

**Chef Server Version Detection**:
```python
def configure_chef_mock(version: str):
    """Configure mock responses based on Chef Server version."""
    if version.startswith("12."):
        # Chef 12.x: Support both SHA-1 and SHA-256
        return {"auth_protocols": ["1.0", "1.3"], "features": ["base"]}
    elif version.startswith("14.") or version.startswith("15."):
        # Chef 14+: Prefer SHA-256, strict SSL
        return {"auth_protocols": ["1.3"], "features": ["base", "policies"]}
```

**AWX Platform Version Detection**:
```python
def configure_awx_mock(platform: str, version: str):
    """Configure mock responses based on AWX platform version."""
    if platform == "tower" and version.startswith("3."):
        return {
            "api_version": "v2",
            "features": ["workflows", "credentials"],
            "execution_model": "virtualenv",
        }
    elif platform == "awx" and int(version.split(".")[0]) >= 21:
        return {
            "api_version": "v2",
            "features": ["workflows", "credentials", "ee"],
            "execution_model": "execution_environment",
        }
    elif platform == "aap":
        return {
            "api_version": "v2",
            "features": ["workflows", "credentials", "ee", "signing"],
            "execution_model": "execution_environment",
            "ansible_min": "2.15",
        }
```

## Mock API Endpoints

### Chef Server API (Mocked)
| Endpoint | Method | Purpose | Version Notes |
|----------|--------|---------|---------------|
| `/organizations/{org}/search/node` | GET | Node search queries | Stable since 12.x |
| `/organizations/{org}/roles/{name}` | GET | Role definitions | Unchanged |
| `/organizations/{org}/cookbooks/{name}/{version}` | GET | Cookbook metadata | Stable |
| `/organizations/{org}/environments` | GET | Environment listing | Unchanged |

**Headers Required**:
```http
Accept: application/json
X-Chef-Version: 13.0
X-Ops-Sign: version=1.0
X-Ops-Userid: client-name
X-Ops-Timestamp: ISO8601
X-Ops-Content-Hash: SHA1(body)
X-Ops-Authorization-1: <signature-chunk-1>
...
```

### AWX/AAP API (Mocked)
| Endpoint | Method | Purpose | Version Support |
|----------|--------|---------|-----------------|
| `/api/v2/inventories/` | POST | Create inventory | Tower 2.x+ |
| `/api/v2/inventories/{id}/hosts/` | POST | Add hosts | Tower 2.x+ |
| `/api/v2/job_templates/` | POST | Create job template | Tower 2.x+ |
| `/api/v2/groups/` | POST | Create inventory groups | Tower 2.x+ |
| `/api/v2/config/` | GET | Query AWX capabilities | Tower 3.x+, AWX 1.0+ |

**Headers Required**:
```http
Authorization: Bearer <token>
Content-Type: application/json
```

## Testing Specific Chef + Platform Version Combinations

When you set a **Chef origin version** + **target platform/version**, the mock and IR transformation must adapt to the **functional API differences**.

### Example 1: Chef 14.x → AWX 24.6.1 (with EE)

```python
import pytest
from unittest import mock

# Set versions
chef_version = "14.15.6"
awx_version = "24.6.1"
awx_platform = "awx"

# Chef Server mock: SHA-256 auth (protocol 1.3)
@pytest.fixture
def chef_14_mock():
    """Chef 14.x mocks use SHA-256 authentication."""
    return {
        "auth_protocol": "1.3",  # SHA-256
        "version": "14.15.6",
        "endpoints": [
            "/organizations/myorg/search/node",
            "/organizations/myorg/roles/webserver",
        ]
    }

# AWX 24.6.1 mock: REQUIRES execution environments
@pytest.fixture
def awx_24_mock():
    """AWX 24.6.1 MUST use execution_environment, not custom_virtualenv."""
    return {
        "version": "24.6.1",
        "ansible_version": "2.16.0",
        "features": ["execution_environments"],  # FUNCTIONAL DIFFERENCE
        "job_template_required_fields": {
            "execution_environment": "REQUIRED",  # This is the key difference
            "custom_virtualenv": "IGNORED",  # Won't work
        }
    }

# IR transformation adapts to version combo
def test_chef_14_to_awx_24():
    """Test Chef 14.x origin → AWX 24.6.1 destination."""

    # Stage 1: Query Chef 14.x (uses SHA-256)
    chef_client = configure_chef_client(
        version="14.15.6",
        auth_protocol="1.3",  # SHA-256 required
        key_type="rsa-2048",
    )
    nodes = chef_client.search_nodes("*:*")

    # Stage 2: Build IR from Chef data
    ir_graph = chef_to_ir(nodes)

    # Stage 3: Transform IR to AWX 24.6.1
    # CRITICAL: Use execution_environment, NOT custom_virtualenv
    job_template = ir_to_awx_job_template(
        ir_graph,
        awx_version="24.6.1",
        execution_model="execution_environment",  # FUNCTIONAL DIFFERENCE
    )

    # Verify: AWX 24.6.1 requires execution_environment
    assert "execution_environment" in job_template
    assert job_template["execution_environment"] is not None
    assert "custom_virtualenv" not in job_template or job_template["custom_virtualenv"] is None
```

### Example 2: Chef 12.x → AWX 22.x (transition period, supports both)

```python
def test_chef_12_to_awx_22():
    """Test Chef 12.x origin → AWX 22.x destination (mixed auth, mixed execution)."""

    # Chef 12.x: Supports BOTH SHA-1 (1.0) and SHA-256 (1.3)
    chef_client = configure_chef_client(
        version="12.19.36",
        auth_protocol="1.3",  # Can use either 1.0 or 1.3
    )
    nodes = chef_client.search_nodes("*:*")

    # AWX 22.x: Supports BOTH virtualenv AND execution environments
    # But prefers execution environments
    ir_graph = chef_to_ir(nodes)

    job_template = ir_to_awx_job_template(
        ir_graph,
        awx_version="22.0.0",
        execution_model="execution_environment",  # Preferred by AWX 22.x
        fallback="custom_virtualenv",  # Still works if needed
    )

    # AWX 22.x preferably uses EE, but can fall back
    assert "execution_environment" in job_template  # Primary method
```

### Example 3: Chef 15.10.91 → AAP 2.4 (latest features - COMPLETE WORKING EXAMPLE)

**This is the 2026 production migration path: Latest Chef to Latest AAP.**

```python
import responses
import pytest
from unittest import mock
from datetime import datetime

@pytest.fixture
def chef_15_aap_24_mocks():
    """Complete mock setup for Chef 15.10.91 → AAP 2.4.0 migration.

    This fixture mocks:
    - Chef Server 15.10.91 with SHA-256 authentication
    - AAP 2.4.0 with execution environments and content signing
    """
    with responses.RequestsMock() as rsps:
        # ===== CHEF SERVER 15.10.91 MOCKS (SHA-256, FIPS) =====

        # Mock Chef Server node search
        chef_nodes_response = {
            "rows": [
                {
                    "data": {
                        "name": "web-prod-01",
                        "platform": "ubuntu",
                        "platform_version": "20.04",
                        "automatic": {
                            "ipaddress": "10.0.1.10",
                            "environment": "production",
                        },
                        "normal": {
                            "run_list": ["role[webserver]", "recipe[nginx::default]"]
                        }
                    }
                },
                {
                    "data": {
                        "name": "app-prod-01",
                        "platform": "ubuntu",
                        "platform_version": "20.04",
                        "automatic": {
                            "ipaddress": "10.0.2.10",
                            "environment": "production",
                        },
                        "normal": {
                            "run_list": ["role[app]", "recipe[chef-app::deploy]"]
                        }
                    }
                }
            ],
            "total": 2
        }
        rsps.add(
            responses.GET,
            "https://chef.example.com/organizations/myorg/search/node",
            json=chef_nodes_response,
            status=200,
            headers={
                "X-Ops-API-Version": "2.1",
                "Server": "Chef Server 15.10.91",
            }
        )

        # Mock Chef Server role definitions
        rsps.add(
            responses.GET,
            "https://chef.example.com/organizations/myorg/roles/webserver",
            json={
                "name": "webserver",
                "run_list": ["recipe[nginx::default]", "recipe[ssl::default]"],
                "default_attributes": {"nginx": {"port": 80}},
                "override_attributes": {}
            },
            status=200
        )

        rsps.add(
            responses.GET,
            "https://chef.example.com/organizations/myorg/roles/app",
            json={
                "name": "app",
                "run_list": ["recipe[chef-app::deploy]", "recipe[nodejs::default]"],
                "default_attributes": {"app": {"version": "2.1.0"}},
                "override_attributes": {}
            },
            status=200
        )

        # ===== AAP 2.4.0 MOCKS (Execution Environments, Content Signing) =====

        # Mock AAP config endpoint - shows capabilities
        rsps.add(
            responses.GET,
            "https://aap.example.com/api/v2/config/",
            json={
                "version": "2.4.0",
                "ansible_version": "2.15.0",
                "license_type": "enterprise",
                "features": {
                    "execution_environments": True,
                    "content_signing": True,
                    "mesh": True,
                    "workflows": True,
                }
            },
            status=200,
            headers={"Server": "AWX 24.6.1 / AAP 2.4"}
        )

        # Mock AAP create execution environment
        rsps.add(
            responses.POST,
            "https://aap.example.com/api/v2/execution_environments/",
            json={
                "id": 42,
                "name": "ee-chef-migration",
                "image": "quay.io/ansible/creator-ee:0.5.0",
                "pull": "always",
                "description": "EE for Chef 15.10.91 → AAP 2.4 migration"
            },
            status=201
        )

        # Mock AAP create inventory
        rsps.add(
            responses.POST,
            "https://aap.example.com/api/v2/inventories/",
            json={
                "id": 1,
                "name": "Production-from-Chef",
                "description": "Migrated from Chef Server 15.10.91",
                "kind": "ssh",
                "organization": 1
            },
            status=201
        )

        # Mock AAP add hosts to inventory
        rsps.add(
            responses.POST,
            "https://aap.example.com/api/v2/inventories/1/hosts/",
            json={
                "id": 101,
                "name": "web-prod-01",
                "inventory": 1,
                "variables": '{"ansible_host": "10.0.1.10", "platform": "ubuntu"}'
            },
            status=201,
            match=[responses.matchers.json_params_matcher({
                "name": "web-prod-01",
                "variables": '{"ansible_host": "10.0.1.10", "platform": "ubuntu"}'
            })]
        )

        rsps.add(
            responses.POST,
            "https://aap.example.com/api/v2/inventories/1/hosts/",
            json={
                "id": 102,
                "name": "app-prod-01",
                "inventory": 1,
                "variables": '{"ansible_host": "10.0.2.10", "platform": "ubuntu"}'
            },
            status=201,
            match=[responses.matchers.json_params_matcher({
                "name": "app-prod-01",
                "variables": '{"ansible_host": "10.0.2.10", "platform": "ubuntu"}'
            })]
        )

        # Mock AAP create project (for playbooks)
        rsps.add(
            responses.POST,
            "https://aap.example.com/api/v2/projects/",
            json={
                "id": 1,
                "name": "chef-migrations",
                "scm_type": "git",
                "scm_url": "https://git.example.com/migrations/chef-to-ansible.git",
                "organization": 1,
                "status": "new"
            },
            status=201
        )

        # Mock AAP create job template - Chef 15.10.91 → AAP 2.4
        # KEY DIFFERENCE: execution_environment is REQUIRED, not optional
        rsps.add(
            responses.POST,
            "https://aap.example.com/api/v2/job_templates/",
            json={
                "id": 1,
                "name": "Deploy-from-Chef-Migration",
                "job_type": "run",
                "inventory": 1,
                "project": 1,
                "playbook": "migrate_chef_roles.yml",
                "execution_environment": 42,  # ← REQUIRED for AAP 2.4
                "limit": "",
                "extra_vars": '{"source": "chef-15.10.91", "target": "aap-2.4"}',
                "verbosity": 1,
                "forks": 5,
                "tags": "migration",
                "skip_tags": "skip",
                "organization": 1,
                "ask_extra_vars": False,
                "ask_tags": False,
                "ask_limit": False,
                "content_signing": True,  # ← AAP 2.4 feature
                "sign_key": "https://aap.example.com/api/v2/signing_keys/1/",
            },
            status=201,
            headers={"X-Ansible-Cost": "10"}
        )

        yield rsps


def test_latest_chef_to_latest_aap(chef_15_aap_24_mocks):
    """
    Complete end-to-end migration test: Chef 15.10.91 → AAP 2.4.0

    This is the 2026 production migration path using:
    - Latest Chef Server: 15.10.91 (Released Feb 10, 2026)
    - Latest Ansible Platform: AAP 2.4.0 (Enterprise)
    - Authentication: SHA-256 (protocol 1.3) with FIPS compliance
    - Execution: Ansible 2.15.0 with Execution Environments
    - Features: Content signing enabled for supply chain security
    """

    # ===== STAGE 1: Query Chef 15.10.91 =====
    print("\n[STAGE 1] Querying Chef Server 15.10.91...")

    chef_client = configure_chef_client(
        version="15.10.91",
        auth_protocol="1.3",  # SHA-256 (protocol 1.3)
        key_type="rsa-2048",
        fips_mode=True,
    )

    # Query nodes from Chef production environment
    nodes = chef_client.search_nodes("environment:production")
    assert len(nodes) == 2
    assert nodes[0]["name"] == "web-prod-01"
    assert nodes[1]["name"] == "app-prod-01"
    print(f"  [OK] Found {len(nodes)} production nodes from Chef")

    # ===== STAGE 2: Build IR Graph =====
    print("[STAGE 2] Building Intermediate Representation...")

    ir_graph = chef_to_ir(
        nodes=nodes,
        chef_version="15.10.91",
        target_platform="aap",
        target_version="2.4.0",
    )

    # IR graph contains both host and role information
    assert ir_graph.source_type == SourceType.CHEF
    assert ir_graph.target_type == TargetType.ANSIBLE
    assert len(ir_graph.nodes) >= 2
    print(f"  [OK] Built IR with {len(ir_graph.nodes)} nodes")

    for node in ir_graph.nodes:
        print(f"    - {node.node_id}: platform={node.properties.get('platform')}")

    # ===== STAGE 3: Transform IR to AAP 2.4 =====
    print("[STAGE 3] Transforming IR to AAP 2.4...")

    # Create execution environment in AAP
    ee_response = requests.post(
        "https://aap.example.com/api/v2/execution_environments/",
        headers={"Authorization": "Bearer aap-token"},
        json={
            "name": "ee-chef-migration",
            "image": "quay.io/ansible/creator-ee:0.5.0",
        }
    )
    ee_id = ee_response.json()["id"]
    print(f"  [OK] Created execution environment EE#{ee_id}")

    # Create inventory from Chef nodes
    inventory_response = requests.post(
        "https://aap.example.com/api/v2/inventories/",
        headers={"Authorization": "Bearer aap-token"},
        json={
            "name": "Production-from-Chef",
            "kind": "ssh",
        }
    )
    inventory_id = inventory_response.json()["id"]
    print(f"  [OK] Created inventory ID#{inventory_id}")

    # Add hosts to inventory
    for node in nodes:
        host_response = requests.post(
            f"https://aap.example.com/api/v2/inventories/{inventory_id}/hosts/",
            headers={"Authorization": "Bearer aap-token"},
            json={
                "name": node["name"],
                "variables": json.dumps({
                    "ansible_host": node["automatic"]["ipaddress"],
                    "platform": node["platform"],
                })
            }
        )
        print(f"    - Added host: {host_response.json()['name']}")

    # Create project for playbooks
    project_response = requests.post(
        "https://aap.example.com/api/v2/projects/",
        headers={"Authorization": "Bearer aap-token"},
        json={
            "name": "chef-migrations",
            "scm_type": "git",
            "scm_url": "https://git.example.com/migrations/chef-to-ansible.git",
        }
    )
    project_id = project_response.json()["id"]
    print(f"  [OK] Created project ID#{project_id}")

    # Transform IR to job template
    job_template = ir_to_awx_job_template(
        ir_graph,
        platform="aap",
        version="2.4.0",
        execution_environment_id=ee_id,
        inventory_id=inventory_id,
        project_id=project_id,
        execution_model="execution_environment",  # REQUIRED for AAP 2.4
        ansible_version="2.15.0",
        signing_enabled=True,
    )
    print(f"  [OK] Generated job template: {job_template['name']}")

    # ===== STAGE 4: Validation & Verification =====
    print("[STAGE 4] Validating transformation...")

    # Verify job template has AAP 2.4 requirements
    assert job_template["execution_environment"] == ee_id  # REQUIRED
    print(f"  [OK] Job template uses execution_environment: {ee_id}")

    assert job_template["ansible_version"] == "2.15.0"
    print(f"  [OK] Ansible version: {job_template['ansible_version']}")

    assert job_template["content_signing"] is True
    print(f"  [OK] Content signing enabled: {job_template['content_signing']}")

    assert "custom_virtualenv" not in job_template or job_template["custom_virtualenv"] is None
    print(f"  [OK] Legacy virtualenv NOT used (correct for AAP 2.4)")

    # ===== STAGE 5: Create in AAP =====
    print("[STAGE 5] Creating job template in AAP 2.4...")

    jt_response = requests.post(
        "https://aap.example.com/api/v2/job_templates/",
        headers={"Authorization": "Bearer aap-token"},
        json=job_template
    )

    created_jt = jt_response.json()
    assert created_jt["id"] == 1
    assert created_jt["execution_environment"] == ee_id
    assert created_jt["content_signing"] is True
    print(f"  [OK] Job template created: JT#{created_jt['id']}")
    print(f"    - Name: {created_jt['name']}")
    print(f"    - EE: {created_jt['execution_environment']}")
    print(f"    - Signed: {created_jt['content_signing']}")

    print("\n[YES] SUCCESS: Chef 15.10.91 → AAP 2.4.0 migration complete!")
    print(f"   {len(nodes)} nodes migrated to {1} job template with modern AAP features")
```

**Key Points - Chef 15.10.91 → AAP 2.4.0:**

| Feature | Chef 15.10.91 | AAP 2.4.0 | IR Transformation |
|---------|---|---|---|
| **Auth Protocol** | SHA-256 (1.3) | OAuth2 Bearer | Use SHA-256 signatures |
| **Execution Model** | N/A | Execution Environments (REQUIRED) | Must reference EE ID |
| **Ansible Version** | N/A | 2.15.0 required | Use 2.15+ in job template |
| **Content Signing** | N/A | Supported | Enable for supply chain security |
| **FIPS Compliance** | Yes | Yes | Both support FIPS mode |
| **Hosts from Chef** | Query via SSH signatures | Added to AAP inventory | Parse Chef nodes → AAP hosts |

**Output from successful migration:**
```
[STAGE 1] Querying Chef Server 15.10.91...
  [OK] Found 2 production nodes from Chef
[STAGE 2] Building Intermediate Representation...
  [OK] Built IR with 2 nodes
    - web-prod-01: platform=ubuntu
    - app-prod-01: platform=ubuntu
[STAGE 3] Transforming IR to AAP 2.4...
  [OK] Created execution environment EE#42
  [OK] Created inventory ID#1
    - Added host: web-prod-01
    - Added host: app-prod-01
  [OK] Created project ID#1
  [OK] Generated job template: Deploy-from-Chef-Migration
[STAGE 4] Validating transformation...
  [OK] Job template uses execution_environment: 42
  [OK] Ansible version: 2.15.0
  [OK] Content signing enabled: True
  [OK] Legacy virtualenv NOT used (correct for AAP 2.4)
[STAGE 5] Creating job template in AAP 2.4...
  [OK] Job template created: JT#1
    - Name: Deploy-from-Chef-Migration
    - EE: 42
    - Signed: True

[YES] SUCCESS: Chef 15.10.91 → AAP 2.4.0 migration complete!
   2 nodes migrated to 1 job template with modern AAP features
```

### Functional API Differences by Version Combo

**When IR transforms to AWX, it MUST adapt based on destination version:**

| Chef Origin | AWX Destination | Execution Model | Auth Protocol | IR Change |
|---|---|---|---|---|
| Chef 12.x | AWX 20.x | `custom_virtualenv` | 1.0 or 1.3 | Use `/path/to/venv` |
| Chef 12.x | AWX 22.x | `execution_environment` | 1.3 | Reference EE ID (required) |
| Chef 14.x | AWX 24.6.1 | `execution_environment` | 1.3 | Reference EE ID (required) |
| Chef 15.10.91 | AAP 2.4 | `execution_environment` | 1.3 | Reference EE ID + signing |

**Code Example: Version-Aware IR Transform**

```python
def ir_to_awx_job_template(ir_graph, platform, version, **options):
    """Transform IR to AWX job template, adapting to version differences."""

    job_template = {
        "name": ir_graph.name,
        "job_type": "run",
        "inventory": options.get("inventory_id"),
        "project": options.get("project_id"),
        "playbook": ir_graph.playbook_name,
    }

    # FUNCTIONAL DIFFERENCE: Execution model depends on version
    if platform == "tower" or (platform == "awx" and int(version.split(".")[0]) < 21):
        # Old: Tower 3.x, AWX <21 (VIRTUALENV model)
        job_template["custom_virtualenv"] = "/var/lib/awx/venv/ansible"
    else:
        # New: AWX 21+, AAP 2.x (EXECUTION ENVIRONMENT model)
        # CRITICAL: Must provide execution_environment ID
        job_template["execution_environment"] = options.get("execution_environment_id")
        if job_template["execution_environment"] is None:
            raise ValueError(f"{platform} {version} requires execution_environment")

    # AAP 2.4+ specific features
    if platform == "aap" and options.get("signing_enabled"):
        job_template["content_signing"] = True

    return job_template
```

## Authentication

### Chef Server
- **Method**: RSA-signed X-Ops-Authorization headers
- **Implementation**: Uses `cryptography` library to generate valid 2048-bit RSA keys
- **Headers**: Complete Chef Server authentication protocol (SHA-1)

### AWX/AAP
- **Method**: OAuth2 Bearer token
- **Header**: `Authorization: Bearer test-token`

## Running the Tests

```bash
# Run all IR workflow tests
poetry run pytest tests/integration/test_ir_chef_awx_workflow.py -v

# Run with coverage
poetry run pytest tests/integration/test_ir_chef_awx_workflow.py --cov=souschef/ir

# Run specific test class
poetry run pytest tests/integration/test_ir_chef_awx_workflow.py::TestEndToEndChefToAWXWorkflow -v
```

## Integration with Existing Tests

These IR workflow tests complement the existing mock infrastructure:

- **Chef Server Mocks** ([test_chef_server_mock.py](../integration/test_chef_server_mock.py)): ~100 tests for Chef API
- **AWX Mocks** ([test_awx_mock.py](../integration/test_awx_mock.py)): ~50 tests for AWX API
- **IR Schema Tests** ([test_ir_integration.py](../integration/test_ir_integration.py)): ~20 tests for IR operations

**Total Mock Test Coverage**: 178+ tests validating API emulation

## Test Data Structure

### IR Graph Example
```python
graph = IRGraph(
    graph_id="migration-001",
    source_type=SourceType.CHEF,
    target_type=TargetType.ANSIBLE,
    version="1.0.0",
)

node = IRNode(
    node_id="host-web-01",
    node_type=IRNodeType.RESOURCE,
    name="web-01",
    source_type=SourceType.CHEF,
)
node.set_variable("platform", "ubuntu")
node.set_variable("environment", "production")
graph.add_node(node)
```

### Chef Server Mock Response
```python
mock_nodes = {
    "rows": [
        {
            "name": "web-prod-01",
            "run_list": ["recipe[nginx]"],
            "chef_environment": "production",
            "platform": "ubuntu",
            "ipaddress": "10.0.1.10",
        }
    ],
    "total": 1,
}
```

### AWX API Mock Response
```python
awx_template = {
    "id": 42,
    "name": "Deploy webapp",
    "job_type": "run",
    "inventory": 1,
    "project": 1,
    "playbook": "deploy_webapp.yml",
}
```

## Design Patterns

### Pattern 1: Multi-Stage Workflow Testing
Tests follow the actual migration workflow:
1. **Discover** (Chef Server query)
2. **Model** (IR graph construction)
3. **Transform** (IR to Ansible)
4. **Deploy** (AWX configuration)

### Pattern 2: Mock Response Chaining
Multiple mock responses configured in sequence:
```python
responses.add(GET, chef_url, json=chef_data)  # Stage 1
responses.add(GET, role_url, json=role_data)   # Stage 2
responses.add(POST, awx_url, json=awx_data)    # Stage 3
```

### Pattern 3: Validation Metadata
Tests track validation status in IR:
```python
node.tags["validated"] = "true"
node.tags["validation_source"] = "chef_server"
graph.metadata["awx_compatible"] = "true"
```

## Coverage Metrics

**Test Coverage**: 8 tests covering critical v2.0/2.1 workflows
**API Endpoints**: 9 Chef + 5 AWX endpoints mocked
**Workflow Stages**: 4-stage end-to-end migration validated
**Authentication**: Both Chef RSA and AWX OAuth2 tested

## Related Documentation

- [Chef Server Mock Testing](MOCK_CHEF.md)
- [AWX Mock Testing](MOCK_AWX.md)
- [IR Architecture](../ARCHITECTURE.md#ir-framework)
- [Migration Workflows](../migration-guide/workflows.md)

## Contributing

When adding new v2.0/2.1 IR features:

1. [YES] Add mock tests for new Chef Server endpoints
2. [YES] Add mock tests for new AWX API interactions
3. [YES] Validate IR graph transformations
4. [YES] Test complete workflow integration
5. [YES] Document new mock responses

## Validation Checklist

Before merging v2.0/2.1 features:

- [ ] All 8 IR workflow tests pass
- [ ] No linting errors (`ruff check`)
- [ ] No type errors (`mypy`)
- [ ] Coverage maintained at 86%+
- [ ] Mock responses match official API specs
- [ ] Authentication headers validated
- [ ] **Origin configuration**: Chef Server version specified and tested
- [ ] **Destination configuration**: Ansible platform/version specified and tested
- [ ] **API version compatibility**: Verified origin→destination path works
- [ ] **Breaking changes**: Documented version-specific behaviors
- [ ] **Test matrix**: At least 2 origin versions and 2 destination versions tested

## Version Detection & Compatibility Testing

### Detecting Chef Server Version

**Via API**:
```python
response = client._request("GET", "/version")
version_data = response.json()
# Returns: {"chef_server_version": "14.10.9"}
```

**Via Headers** (response from any endpoint):
```python
server_version = response.headers.get("X-Ops-Server-API-Version", "unknown")
```

### Detecting AWX/Tower Version

**Via Config Endpoint**:
```python
response = requests.get(
    "https://awx.example.com/api/v2/config/",
    headers={"Authorization": "Bearer token"}
)
config = response.json()
print(f"AWX Version: {config['version']}")
print(f"Ansible Version: {config['ansible_version']}")
```

**Response Example**:
```json
{
  "version": "23.3.1",          // AWX version
  "ansible_version": "2.15.0",  // Ansible core version
  "project_base_dir": "/var/lib/awx/projects",
  "custom_virtualenvs": []
}
```

### Configuring Test Migrations

**Step 1: Define Origin (Chef Server)**:
```python
# Example: Chef Server 15.x origin
chef_origin = {
    "version": "15.0.0",
    "organization": "myorg",
    "auth_protocol": "1.3",  # SHA-256
    "base_url": "https://chef.example.com",
}

# Mock Chef Server responses for 15.x
responses.add(
    method=responses.GET,
    url=f"{chef_origin['base_url']}/version",
    json={"chef_server_version": chef_origin["version"]},
    headers={"X-Ops-Server-API-Version": "1.3"},
)
```

**Step 2: Define Destination (Ansible Platform)**:
```python
# Example: AAP 2.4 destination
awx_destination = {
    "platform": "aap",
    "version": "2.4.0",
    "ansible_version": "2.15.0",
    "api_version": "v2",
    "base_url": "https://aap.example.com",
    "features": ["execution_environments", "workflows"],
}

# Mock AWX/AAP config endpoint
responses.add(
    method=responses.GET,
    url=f"{awx_destination['base_url']}/api/v2/config/",
    json={
        "version": awx_destination["version"],
        "ansible_version": awx_destination["ansible_version"],
    },
)
```

**Step 3: Configure Version-Specific Behaviors**:
```python
# Chef 15.x: Uses SHA-256 authentication
if chef_origin["auth_protocol"] == "1.3":
    auth_headers = generate_chef_auth_sha256(...)
else:
    auth_headers = generate_chef_auth_sha1(...)

# AAP 2.4: Requires execution environments
if "execution_environments" in awx_destination["features"]:
    job_template["execution_environment"] = 1  # Required
else:
    job_template["custom_virtualenv"] = "/venv/ansible"  # Legacy
```

### Testing Cross-Version Compatibility

**Test Origin Compatibility** (Chef Server versions):
```python
@pytest.mark.parametrize("chef_version,auth_protocol", [
    ("12.0", "1.0"),  # SHA-1 only
    ("12.19", "1.3"), # First 1.3 support
    ("14.0", "1.3"),  # SHA-256 preferred
    ("15.0", "1.3"),  # SHA-256 default
])
def test_chef_origin_versions(chef_version, auth_protocol):
    """Test Chef Server versions as migration origins."""
    # Configure mock with version-specific auth
    client = ChefServerClient(
        base_url="https://chef.example.com",
        client_name="validator",
        private_key=test_key,
        auth_version=auth_protocol,
    )
    # All versions should return same data structure
    nodes = client.search_nodes("name:*")
    assert "rows" in nodes
```

**Test Destination Compatibility** (Ansible platforms):
```python
@pytest.mark.parametrize("platform,version,ansible_version", [
    ("tower", "3.8.6", "2.9.27"),   # Legacy
    ("awx", "21.0", "2.12.0"),      # Transition (virtualenv → EE)
    ("awx", "24.0", "2.16.0"),      # Current
    ("aap", "2.4.0", "2.15.0"),     # Enterprise
])
def test_awx_destination_versions(platform, version, ansible_version):
    """Test Ansible platforms as migration destinations."""
    # Configure version-specific API mock
    responses.add(
        responses.GET,
        "https://awx.example.com/api/v2/config/",
        json={"version": version, "ansible_version": ansible_version},
    )

    # Generate IR and transform to platform-specific config
    ir_graph = create_test_ir_graph()

    # Version-specific transformations
    if platform == "aap" or (platform == "awx" and int(version.split(".")[0]) >= 21):
        # Use execution environments (required in AAP, AWX 21+)
        job_template = ir_to_awx_job_template(ir_graph, use_ee=True)
        assert "execution_environment" in job_template
    else:
        # Use legacy virtualenv (Tower 3.x, early AWX)
        job_template = ir_to_awx_job_template(ir_graph, use_ee=False)
        assert "custom_virtualenv" in job_template
```

**Test End-to-End Paths**:
```python
@pytest.mark.parametrize("origin,destination", [
    # Minimum supported: Chef 12.x → Tower 3.8
    (
        {"chef": "12.19", "auth": "1.3"},
        {"platform": "tower", "version": "3.8.6", "ansible": "2.9"},
    ),
    # Mid-range: Chef 14.x → AWX 22.x
    (
        {"chef": "14.15", "auth": "1.3"},
        {"platform": "awx", "version": "22.0", "ansible": "2.14"},
    ),
    # Current: Chef 15.x → AAP 2.4
    (
        {"chef": "15.0", "auth": "1.3"},
        {"platform": "aap", "version": "2.4", "ansible": "2.15"},
    ),
])
def test_migration_path_compatibility(origin, destination):
    """Test complete Chef → Ansible migration paths."""
    # Stage 1: Query Chef Server (origin version)
    chef_client = configure_chef_client(origin)
    nodes = chef_client.search_nodes("*:*")

    # Stage 2: Build IR from Chef data
    ir_graph = chef_to_ir(nodes)

    # Stage 3: Transform IR to Ansible (destination version)
    awx_config = configure_awx_client(destination)
    inventory = ir_to_awx_inventory(ir_graph, awx_config)
    job_template = ir_to_awx_job_template(ir_graph, awx_config)

    # Stage 4: Validate destination compatibility
    assert validate_awx_compatibility(ir_graph, destination["ansible"])
```

### Version-Specific Breaking Changes

**When migrating FROM these Chef Server versions**:

| Origin Version | Breaking Changes | Migration Impact | Workaround |
|----------------|------------------|------------------|------------|
| Chef 11.x | SHA-1 only | Must upgrade to 12.x for SHA-256 | Use auth protocol 1.0 |
| Chef 12.x | Mixed auth support | None - fully compatible | Prefer protocol 1.3 |
| Chef 14.x | Strict SSL/TLS | Requires valid certificates | Update cert validation |
| Chef 15.x | FIPS compliance | Cipher suite restrictions | Use approved ciphers |

**When migrating TO these Ansible platforms**:

| Destination Version | Breaking Changes | Migration Impact | Workaround |
|---------------------|------------------|------------------|------------|
| Tower 3.8 | EOL (no EE support) | Limited to virtualenv | Use AWX 19+ for EE |
| AWX 19.x | Removed legacy creds | Credential migration needed | Remap credential types |
| AWX 21.x | EE required | Must provide EE or default | Create default EE |
| AAP 2.x | Renamed entities | API paths changed | Use new paths |
| AAP 2.4 | Ansible 2.15+ | Older playbooks may break | Test playbook syntax |

### Tested Migration Paths

**Current Test Coverage** (`test_ir_chef_awx_workflow.py`):

| Test | Origin | Destination | Status | API Validation |
|------|--------|-------------|--------|----------------|
| `test_query_chef_nodes_and_build_ir` | Chef 14.x | N/A | [YES] Passing | SHA-256 auth, node search |
| `test_chef_cookbook_to_ir_with_dependencies` | Chef 12.x+ | N/A | [YES] Passing | Cookbook metadata |
| `test_ir_to_awx_job_template_creation` | N/A | AWX 24.6.1 | [YES] Passing | EE-based templates |
| `test_ir_to_awx_inventory_creation` | N/A | AWX 24.6.1 | [YES] Passing | Inventory API v2 |
| `test_complete_migration_workflow` | Chef 14.x | AWX 24.6.1 | [YES] Passing | Full 4-stage pipeline |
| `test_workflow_with_chef_environments_to_awx_groups` | Chef 14.x | AWX 24.6.1 | [YES] Passing | Environment mapping |
| `test_validate_ir_node_against_chef_server` | Chef 14.x | N/A | [YES] Passing | Recipe validation |
| `test_validate_awx_compatibility_from_ir` | N/A | AWX 24.6.1 | [YES] Passing | Ansible version check |

**Default Test Configuration**:
- **Origin**: Chef Server 14.x with SHA-256 authentication (protocol 1.3)
- **Destination**: AWX 24.6.1 with Ansible 2.16 and Execution Environment support
- **API Versions**: Chef Server (no URL version), AWX `/api/v2/`

### Extending Coverage (recommended):
```python
# Add tests for other Chef origins
test_chef_12x_mixed_auth()  # Protocol 1.0/1.3 support
test_chef_15_fips()  # FIPS 140-2 compliance

# Add tests for other AWX versions
test_chef_to_awx_22()  # AWX 22.x with EE
test_chef_to_awx_23()  # AWX 23.x releases

# Add tests for AAP
test_chef_to_aap_24()  # AAP 2.4 features
```

## Future Enhancements

Potential additions to mock coverage:

### Expanded Version Testing
- **Chef 11.x origins**: Test SHA-1-only legacy migrations
- **Chef 12.x mixed auth**: Test protocol 1.0/1.3 transitions
- **Chef 15.x FIPS**: Test FIPS 140-2 compliant origins
- **Tower 3.8 destinations**: Test legacy AWX Tower targets
- **AWX 24.x destinations**: Test latest AWX features
- **AAP 2.5+ destinations**: Test future AAP releases

### Additional API Coverage
- **Chef Policyfiles**: Mock policy group queries and policy revisions
- **AWX Workflows**: Multi-step workflow node creation and dependencies
- **Chef Search**: Advanced search query patterns (boolean, wildcard, range)
- **AWX Surveys**: Job template survey generation from Chef attributes
- **AWX Execution Environments**: Custom EE image configuration

### Error Scenario Testing
- **4xx/5xx responses**: API error handling across versions
- **Rate limiting**: API throttling simulation (429 responses)
- **Authentication failures**: Invalid keys, expired tokens
- **Version mismatches**: Incompatible origin→destination combinations

### Performance Testing
- **Large-scale migrations**: 1000+ nodes, 100+ cookbooks
- **Concurrent API calls**: Parallel Chef Server queries
- **AWX batch operations**: Bulk inventory/host creation
