#!/usr/bin/env python3
"""
Demo: Mock Chef Server + AWX Integration Testing

This script demonstrates end-to-end Chef-to-Ansible migration testing
WITHOUT real Chef Server or AWX infrastructure, using mocked responses.

Scenario: Query Chef Server for nodes → Create AWX inventory →
          Create job template → Launch deployment → Monitor results

Run: poetry run python examples/demo_mock_chef_and_awx.py
"""

import base64
import json
from datetime import datetime

import responses

from souschef.core.chef_server import requests_module

CHEF_SERVER_URL = "https://chef.example.com"
CHEF_ORG = "default"
AWX_BASE_URL = "https://awx.example.com"
AWX_AUTH_TOKEN = "demo-bearer-token"
CHEF_MIGRATED_INVENTORY = "Chef Migrated Production"
NGINX_JOB_TEMPLATE_NAME = "Chef Nginx Cookbook → Ansible"
NGINX_PLAYBOOK = "nginx_deploy.yml"

if requests_module is None:
    raise RuntimeError("requests is required to run this demo")


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


@responses.activate
def scenario_1_query_chef_nodes():
    """Step 1: Query Chef Server for nodes to migrate."""
    print_section("Step 1: Query Chef Server for Nodes")

    # Mock Chef Server authentication headers
    auth_headers = {
        "X-Ops-Sign": "algorithm=sha1;version=1.0",
        "X-Ops-Userid": "migration-user",
        "X-Ops-Timestamp": "2026-02-16T12:00:00Z",
        "X-Ops-Content-Hash": base64.b64encode(b"").decode(),
        "X-Chef-Version": "18.0",
        "X-Ops-Authorization-1": "mock-signature-line-1",
    }

    # Mock Chef Server node search response
    responses.add(
        responses.GET,
        f"{CHEF_SERVER_URL}/organizations/{CHEF_ORG}/search/node",
        json={
            "rows": [
                {
                    "name": "web-server-01",
                    "automatic": {
                        "platform": "ubuntu",
                        "platform_version": "22.04",
                        "ipaddress": "10.0.1.10",  # NOSONAR - S1313: mock data for demo
                        "fqdn": "web-01.example.com",
                    },
                    "run_list": ["recipe[nginx]", "recipe[php]"],
                    "environment": "production",
                },
                {
                    "name": "web-server-02",
                    "automatic": {
                        "platform": "ubuntu",
                        "platform_version": "22.04",
                        "ipaddress": "10.0.1.11",  # NOSONAR - S1313: mock data for demo
                        "fqdn": "web-02.example.com",
                    },
                    "run_list": ["recipe[nginx]", "recipe[php]"],
                    "environment": "production",
                },
                {
                    "name": "db-server-01",
                    "automatic": {
                        "platform": "centos",
                        "platform_version": "8",
                        "ipaddress": "10.0.2.20",  # NOSONAR - S1313: mock data for demo
                        "fqdn": "db-01.example.com",
                    },
                    "run_list": ["recipe[postgresql]", "recipe[backup]"],
                    "environment": "production",
                },
            ],
            "total": 3,
        },
        status=200,
    )

    # Query Chef Server
    print("🔍 Querying Chef Server for production nodes...")
    response = requests_module.get(
        f"{CHEF_SERVER_URL}/organizations/{CHEF_ORG}/search/node",
        params={"q": "environment:production"},
        headers=auth_headers,
    )

    nodes = response.json()["rows"]
    print(f"✅ Found {len(nodes)} nodes in production environment:\n")

    for node in nodes:
        print(f"  • {node['name']} ({node['automatic']['platform']})")
        print(f"    IP: {node['automatic']['ipaddress']}")
        print(f"    FQDN: {node['automatic']['fqdn']}")
        print(f"    Run list: {', '.join(node['run_list'])}")
        print()

    return nodes


@responses.activate
def scenario_2_create_awx_inventory(nodes):
    """Step 2: Create AWX inventory from Chef nodes."""
    print_section("Step 2: Create AWX Inventory from Chef Nodes")

    # Mock AWX inventory creation
    responses.add(
        responses.POST,
        f"{AWX_BASE_URL}/api/v2/inventories/",
        json={
            "id": 10,
            "name": CHEF_MIGRATED_INVENTORY,
            "description": "Imported from Chef Server on "
            + datetime.now().strftime("%Y-%m-%d"),
            "organization": 1,
            "created": datetime.now().isoformat(),
        },
        status=201,
    )

    # Mock host creation (multiple responses)
    for idx, node in enumerate(nodes, start=100):
        responses.add(
            responses.POST,
            f"{AWX_BASE_URL}/api/v2/inventories/10/hosts/",
            json={
                "id": idx,
                "name": node["name"],
                "variables": json.dumps(
                    {
                        "ansible_host": node["automatic"]["ipaddress"],
                        "chef_environment": node["environment"],
                        "chef_platform": node["automatic"]["platform"],
                        "chef_run_list": node["run_list"],
                    }
                ),
                "created": datetime.now().isoformat(),
            },
            status=201,
        )

    # Create inventory
    print("📦 Creating AWX inventory...")
    inv_response = requests_module.post(
        f"{AWX_BASE_URL}/api/v2/inventories/",
        json={
            "name": CHEF_MIGRATED_INVENTORY,
            "description": f"Imported from Chef Server on {datetime.now().strftime('%Y-%m-%d')}",
            "organization": 1,
        },
        headers={"Authorization": f"Bearer {AWX_AUTH_TOKEN}"},
    )

    inventory = inv_response.json()
    print(f"✅ Created inventory (ID: {inventory['id']})")
    print(f"  Name: {inventory['name']}")
    print(f"  Description: {inventory['description']}")

    # Add hosts
    print(f"\n➕ Adding {len(nodes)} hosts to inventory...\n")

    for node in nodes:
        host_response = requests_module.post(
            f"{AWX_BASE_URL}/api/v2/inventories/{inventory['id']}/hosts/",
            json={
                "name": node["name"],
                "variables": json.dumps(
                    {
                        "ansible_host": node["automatic"]["ipaddress"],
                        "chef_environment": node["environment"],
                        "chef_platform": node["automatic"]["platform"],
                        "chef_run_list": node["run_list"],
                    }
                ),
            },
            headers={"Authorization": f"Bearer {AWX_AUTH_TOKEN}"},
        )

        host = host_response.json()
        print(f"  ✅ Added host: {host['name']} (ID: {host['id']})")

    return inventory["id"]


@responses.activate
def scenario_3_create_job_template(inventory_id):
    """Step 3: Create AWX job template from Chef cookbook."""
    print_section("Step 3: Create Job Template from Chef Cookbook")

    # Mock job template creation
    responses.add(
        responses.POST,
        f"{AWX_BASE_URL}/api/v2/job_templates/",
        json={
            "id": 50,
            "name": NGINX_JOB_TEMPLATE_NAME,
            "description": "Converted from Chef nginx cookbook using SousChef",
            "playbook": NGINX_PLAYBOOK,
            "project": 5,
            "inventory": inventory_id,
            "extra_vars": json.dumps(
                {
                    "nginx_version": "1.24.0",
                    "nginx_worker_processes": "auto",
                    "nginx_keepalive_timeout": 65,
                }
            ),
            "created": datetime.now().isoformat(),
        },
        status=201,
    )

    # Create job template
    print("📝 Creating job template from Chef nginx cookbook...")
    template_response = requests_module.post(
        f"{AWX_BASE_URL}/api/v2/job_templates/",
        json={
            "name": NGINX_JOB_TEMPLATE_NAME,
            "description": "Converted from Chef nginx cookbook using SousChef",
            "playbook": NGINX_PLAYBOOK,
            "project": 5,
            "inventory": inventory_id,
            "extra_vars": json.dumps(
                {
                    "nginx_version": "1.24.0",
                    "nginx_worker_processes": "auto",
                    "nginx_keepalive_timeout": 65,
                }
            ),
        },
        headers={"Authorization": f"Bearer {AWX_AUTH_TOKEN}"},
    )

    template = template_response.json()
    print(f"✅ Created job template (ID: {template['id']})")
    print(f"  Name: {template['name']}")
    print(f"  Playbook: {template['playbook']}")
    print(f"  Project ID: {template['project']}")
    print(f"  Inventory ID: {template['inventory']}")

    extra_vars = json.loads(template["extra_vars"])
    print("  Extra Variables:")
    for key, value in extra_vars.items():
        print(f"    - {key}: {value}")

    return template["id"]


@responses.activate
def scenario_4_launch_deployment(template_id):
    """Step 4: Launch deployment job."""
    print_section("Step 4: Launch Deployment Job")

    # Mock job launch
    responses.add(
        responses.POST,
        f"{AWX_BASE_URL}/api/v2/job_templates/{template_id}/launch/",
        json={"job": 123, "status": "pending", "url": "/api/v2/jobs/123/"},
        status=201,
    )

    # Mock job status progression
    responses.add(
        responses.GET,
        f"{AWX_BASE_URL}/api/v2/jobs/123/",
        json={
            "id": 123,
            "name": f"{NGINX_JOB_TEMPLATE_NAME} #123",
            "status": "running",
            "failed": False,
            "started": datetime.now().isoformat(),
            "finished": None,
            "elapsed": 15.3,
        },
        status=200,
    )

    # Launch job
    print(f"🚀 Launching job template #{template_id}...")
    launch_response = requests_module.post(
        f"{AWX_BASE_URL}/api/v2/job_templates/{template_id}/launch/",
        json={
            "extra_vars": {
                "migration_timestamp": datetime.now().isoformat(),
                "migration_source": "chef_server",
            }
        },
        headers={"Authorization": f"Bearer {AWX_AUTH_TOKEN}"},
    )

    job = launch_response.json()
    print("✅ Job launched successfully!")
    print(f"  Job ID: {job['job']}")
    print(f"  Status: {job['status']}")
    print(f"  URL: {AWX_BASE_URL}{job['url']}")

    return job["job"]


@responses.activate
def scenario_5_monitor_job(job_id):
    """Step 5: Monitor job execution."""
    print_section("Step 5: Monitor Job Execution")

    # Mock job status (completed)
    responses.add(
        responses.GET,
        f"{AWX_BASE_URL}/api/v2/jobs/{job_id}/",
        json={
            "id": job_id,
            "name": f"{NGINX_JOB_TEMPLATE_NAME} #123",
            "status": "successful",
            "failed": False,
            "started": "2026-02-16T12:05:00Z",
            "finished": "2026-02-16T12:08:45Z",
            "elapsed": 225.6,
            "playbook": NGINX_PLAYBOOK,
            "inventory": CHEF_MIGRATED_INVENTORY,
            "summary_fields": {"job_template": {"name": NGINX_JOB_TEMPLATE_NAME}},
            "play_count": 2,
            "task_count": 18,
            "host_status_counts": {
                "ok": 3,
                "changed": 3,
                "failures": 0,
                "unreachable": 0,
            },
        },
        status=200,
    )

    # Mock job output
    responses.add(
        responses.GET,
        f"{AWX_BASE_URL}/api/v2/jobs/{job_id}/stdout/",
        json={
            "content": """PLAY [webservers] ***********************************************************

TASK [Gathering Facts] ******************************************************
ok: [web-server-01]
ok: [web-server-02]

TASK [nginx : Install Nginx] ************************************************
changed: [web-server-01]
changed: [web-server-02]

TASK [nginx : Configure Nginx] **********************************************
changed: [web-server-01]
changed: [web-server-02]

TASK [nginx : Start Nginx Service] ******************************************
changed: [web-server-01]
changed: [web-server-02]

PLAY RECAP ******************************************************************
web-server-01              : ok=15   changed=3    unreachable=0    failed=0
web-server-02              : ok=15   changed=3    unreachable=0    failed=0
"""
        },
        status=200,
    )

    # Check job status
    print(f"📊 Checking job #{job_id} status...")
    status_response = requests_module.get(
        f"{AWX_BASE_URL}/api/v2/jobs/{job_id}/",
        headers={"Authorization": f"Bearer {AWX_AUTH_TOKEN}"},
    )

    job = status_response.json()
    print("\n✅ Job completed successfully!")
    print(f"  Status: {job['status']}")
    print(f"  Failed: {job['failed']}")
    print(f"  Started: {job['started']}")
    print(f"  Finished: {job['finished']}")
    print(f"  Elapsed: {job['elapsed']:.1f} seconds")
    print(f"  Playbook: {job['playbook']}")
    print(f"  Inventory: {job['inventory']}")
    print("\n📈 Execution Summary:")
    print(f"  Plays: {job['play_count']}")
    print(f"  Tasks: {job['task_count']}")
    print("  Host Status:")
    for status_type, count in job["host_status_counts"].items():
        print(f"    - {status_type}: {count}")

    # Get job output
    print("\n📝 Job Output (last 20 lines):")
    output_response = requests_module.get(
        f"{AWX_BASE_URL}/api/v2/jobs/{job_id}/stdout/",
        headers={"Authorization": f"Bearer {AWX_AUTH_TOKEN}"},
    )

    output_lines = output_response.json()["content"].strip().split("\n")
    for line in output_lines[-20:]:
        print(f"  {line}")


def main():
    """Run end-to-end Chef to AWX migration scenario."""
    print("=" * 70)
    print("  Chef Server → AWX Migration Demo (Mock Testing)")
    print("  End-to-End Testing WITHOUT Real Infrastructure!")
    print("=" * 70)

    try:
        # Step 1: Query Chef Server
        nodes = scenario_1_query_chef_nodes()

        # Step 2: Create AWX inventory
        inventory_id = scenario_2_create_awx_inventory(nodes)

        # Step 3: Create job template
        template_id = scenario_3_create_job_template(inventory_id)

        # Step 4: Launch deployment
        job_id = scenario_4_launch_deployment(template_id)

        # Step 5: Monitor execution
        scenario_5_monitor_job(job_id)

        # Summary
        print_section("Migration Summary")
        print("✅ Successfully demonstrated complete Chef → AWX migration:")
        print(f"  1. Queried Chef Server for {len(nodes)} production nodes")
        print(f"  2. Created AWX inventory #{inventory_id} with {len(nodes)} hosts")
        print(f"  3. Created job template #{template_id} from Chef cookbook")
        print(f"  4. Launched deployment job #{job_id}")
        print("  5. Monitored execution to successful completion")
        print("\n🎉 All operations completed without ANY real infrastructure!")
        print("   No Chef Server • No AWX Server • Pure Mock Testing")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
