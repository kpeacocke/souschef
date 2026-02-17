#!/usr/bin/env python3
"""
Demo: Mock AWX/AAP API Testing without a Real Server

This script demonstrates how to test AWX/Ansible Automation Platform API
integrations without deploying actual AWX infrastructure, using mocked responses.

Run: poetry run python examples/demo_mock_awx.py
"""

import json

import responses

from souschef.core.chef_server import requests_module

AWX_BASE_URL = "https://awx.example.com"
AUTH_TOKEN = "demo-bearer-token"
PRODUCTION_INVENTORY_NAME = "Production Servers"

if requests_module is None:
    raise RuntimeError("requests is required to run this demo")


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


@responses.activate
def demo_1_list_job_templates():
    """Demo 1: List Job Templates."""
    print_section("Demo 1: List Job Templates")

    # Mock AWX API response
    responses.add(
        responses.GET,
        f"{AWX_BASE_URL}/api/v2/job_templates/",
        json={
            "count": 3,
            "results": [
                {
                    "id": 1,
                    "name": "Deploy Web Application",
                    "playbook": "site.yml",
                    "project": "Chef Migrated Playbooks",
                },
                {
                    "id": 2,
                    "name": "Update System Packages",
                    "playbook": "system_update.yml",
                    "project": "Maintenance",
                },
                {
                    "id": 3,
                    "name": "Database Backup",
                    "playbook": "backup_db.yml",
                    "project": "Database Operations",
                },
            ],
        },
        status=200,
    )

    # Make request
    response = requests_module.get(
        f"{AWX_BASE_URL}/api/v2/job_templates/",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    # Display results
    data = response.json()
    print(f"✅ Found {data['count']} job templates:")
    for template in data["results"]:
        print(f"  - [{template['id']}] {template['name']}")
        print(f"    Playbook: {template['playbook']}")
        print(f"    Project: {template['project']}")


@responses.activate
def demo_2_create_job_template():
    """Demo 2: Create Job Template from Chef Cookbook."""
    print_section("Demo 2: Create Job Template from Chef Cookbook")

    # Mock AWX API response for creating job template
    responses.add(
        responses.POST,
        f"{AWX_BASE_URL}/api/v2/job_templates/",
        json={
            "id": 4,
            "name": "Chef Nginx Deployment",
            "description": "Migrated from Chef nginx cookbook",
            "playbook": "nginx_deploy.yml",
            "project": "Chef Migrations",
            "inventory": PRODUCTION_INVENTORY_NAME,
            "created": "2026-02-16T12:30:00Z",
        },
        status=201,
    )

    # Request payload (from Chef cookbook conversion)
    new_template = {
        "name": "Chef Nginx Deployment",
        "description": "Migrated from Chef nginx cookbook",
        "playbook": "nginx_deploy.yml",
        "project": 5,  # Project ID
        "inventory": 2,  # Inventory ID
        "extra_vars": json.dumps(
            {
                "nginx_version": "1.24.0",
                "nginx_port": 80,
                "nginx_worker_processes": "auto",
            }
        ),
    }

    # Make request
    response = requests_module.post(
        f"{AWX_BASE_URL}/api/v2/job_templates/",
        json=new_template,
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    # Display results
    data = response.json()
    print(f"✅ Created job template (ID: {data['id']})")
    print(f"  Name: {data['name']}")
    print(f"  Description: {data['description']}")
    print(f"  Playbook: {data['playbook']}")
    print(f"  Project: {data['project']}")
    print(f"  Inventory: {data['inventory']}")
    print(f"  Created: {data['created']}")


@responses.activate
def demo_3_launch_and_monitor_job():
    """Demo 3: Launch Job and Monitor Status."""
    print_section("Demo 3: Launch Job and Monitor Status")

    # Mock job launch
    responses.add(
        responses.POST,
        f"{AWX_BASE_URL}/api/v2/job_templates/1/launch/",
        json={"job": 42, "status": "pending", "url": "/api/v2/jobs/42/"},
        status=201,
    )

    # Mock job status check
    responses.add(
        responses.GET,
        f"{AWX_BASE_URL}/api/v2/jobs/42/",
        json={
            "id": 42,
            "name": "Deploy Web Application",
            "status": "successful",
            "failed": False,
            "started": "2026-02-16T12:35:00Z",
            "finished": "2026-02-16T12:38:25Z",
            "elapsed": 205.42,
            "playbook": "site.yml",
            "inventory": PRODUCTION_INVENTORY_NAME,
        },
        status=200,
    )

    # Mock job output/stdout
    responses.add(
        responses.GET,
        f"{AWX_BASE_URL}/api/v2/jobs/42/stdout/",
        json={
            "content": "PLAY [webservers]\n\nTASK [nginx : Install Nginx]\nok: [web-01]\n\nPLAY RECAP\nweb-01: ok=15 changed=3 unreachable=0 failed=0"
        },
        status=200,
    )

    # Launch job
    print("🚀 Launching job template #1...")
    launch_response = requests_module.post(
        f"{AWX_BASE_URL}/api/v2/job_templates/1/launch/",
        json={"extra_vars": {"deploy_env": "production"}},
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    job_data = launch_response.json()
    job_id = job_data["job"]
    print(f"  Job ID: {job_id}")
    print(f"  Initial Status: {job_data['status']}")

    # Check job status
    print("\n📊 Checking job status...")
    status_response = requests_module.get(
        f"{AWX_BASE_URL}/api/v2/jobs/{job_id}/",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    status_data = status_response.json()
    print(f"  Status: {status_data['status']}")
    print(f"  Failed: {status_data['failed']}")
    print(f"  Started: {status_data['started']}")
    print(f"  Finished: {status_data['finished']}")
    print(f"  Elapsed: {status_data['elapsed']:.2f} seconds")
    print(f"  Playbook: {status_data['playbook']}")
    print(f"  Inventory: {status_data['inventory']}")

    # Get job output
    print("\n📝 Job output:")
    output_response = requests_module.get(
        f"{AWX_BASE_URL}/api/v2/jobs/{job_id}/stdout/",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )
    print(output_response.json()["content"])


@responses.activate
def demo_4_workflow_execution():
    """Demo 4: Workflow Execution (Multi-Playbook)."""
    print_section("Demo 4: Workflow Execution (Multi-Playbook)")

    # Mock workflow list
    responses.add(
        responses.GET,
        f"{AWX_BASE_URL}/api/v2/workflow_job_templates/",
        json={
            "count": 2,
            "results": [
                {
                    "id": 1,
                    "name": "Chef Runlist Migration",
                    "description": "Execute full Chef runlist as Ansible workflow",
                },
                {
                    "id": 2,
                    "name": "Database Deployment Pipeline",
                    "description": "Install DB → Configure → Backup",
                },
            ],
        },
        status=200,
    )

    # Mock workflow launch
    responses.add(
        responses.POST,
        f"{AWX_BASE_URL}/api/v2/workflow_job_templates/1/launch/",
        json={"workflow_job": 25, "status": "pending"},
        status=201,
    )

    # Mock workflow status
    responses.add(
        responses.GET,
        f"{AWX_BASE_URL}/api/v2/workflow_jobs/25/",
        json={
            "id": 25,
            "name": "Chef Runlist Migration #25",
            "status": "successful",
            "failed": False,
            "elapsed": 456.78,
            "workflow_nodes": [
                {
                    "unified_job_template": 10,
                    "job": 50,
                    "status": "successful",
                    "summary_fields": {"job": {"name": "Base System Setup"}},
                },
                {
                    "unified_job_template": 11,
                    "job": 51,
                    "status": "successful",
                    "summary_fields": {"job": {"name": "Install Nginx"}},
                },
                {
                    "unified_job_template": 12,
                    "job": 52,
                    "status": "successful",
                    "summary_fields": {"job": {"name": "Configure Application"}},
                },
            ],
        },
        status=200,
    )

    # List workflows
    print("📋 Available workflows:")
    list_response = requests_module.get(
        f"{AWX_BASE_URL}/api/v2/workflow_job_templates/",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    for workflow in list_response.json()["results"]:
        print(f"  - [{workflow['id']}] {workflow['name']}")
        print(f"    Description: {workflow['description']}")

    # Launch workflow
    print("\n🚀 Launching workflow #1...")
    launch_response = requests_module.post(
        f"{AWX_BASE_URL}/api/v2/workflow_job_templates/1/launch/",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    workflow_job_id = launch_response.json()["workflow_job"]
    print(f"  Workflow Job ID: {workflow_job_id}")

    # Check workflow status
    print("\n📊 Workflow execution status:")
    status_response = requests_module.get(
        f"{AWX_BASE_URL}/api/v2/workflow_jobs/{workflow_job_id}/",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    workflow_data = status_response.json()
    print(f"  Status: {workflow_data['status']}")
    print(f"  Failed: {workflow_data['failed']}")
    print(f"  Elapsed: {workflow_data['elapsed']:.2f} seconds")
    print("  Workflow Nodes:")

    for node in workflow_data["workflow_nodes"]:
        job_name = node["summary_fields"]["job"]["name"]
        print(f"    - Job {node['job']}: {job_name} [{node['status']}]")


@responses.activate
def demo_5_inventory_management():
    """Demo 5: Inventory Management (Chef to AWX)."""
    print_section("Demo 5: Inventory Management (Chef to AWX)")

    # Mock inventory list
    responses.add(
        responses.GET,
        f"{AWX_BASE_URL}/api/v2/inventories/",
        json={
            "count": 2,
            "results": [
                {
                    "id": 1,
                    "name": "Chef Migrated Hosts",
                    "description": "Imported from Chef Server node search",
                    "total_hosts": 25,
                    "total_groups": 5,
                },
                {
                    "id": 2,
                    "name": PRODUCTION_INVENTORY_NAME,
                    "description": "Manual inventory",
                    "total_hosts": 50,
                    "total_groups": 10,
                },
            ],
        },
        status=200,
    )

    # Mock inventory source sync
    responses.add(
        responses.POST,
        f"{AWX_BASE_URL}/api/v2/inventory_sources/5/update/",
        json={"inventory_update": 15, "status": "pending"},
        status=202,
    )

    # Mock inventory update status
    responses.add(
        responses.GET,
        f"{AWX_BASE_URL}/api/v2/inventory_updates/15/",
        json={
            "id": 15,
            "status": "successful",
            "source": "scm",
            "total_hosts": 30,
            "hosts_added": 5,
            "hosts_deleted": 2,
            "hosts_updated": 3,
        },
        status=200,
    )

    # List inventories
    print("📦 Available inventories:")
    list_response = requests_module.get(
        f"{AWX_BASE_URL}/api/v2/inventories/",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    for inv in list_response.json()["results"]:
        print(f"  - [{inv['id']}] {inv['name']}")
        print(f"    Description: {inv['description']}")
        print(f"    Hosts: {inv['total_hosts']}, Groups: {inv['total_groups']}")

    # Sync inventory source
    print("\n🔄 Syncing inventory source #5 (Chef Server)...")
    sync_response = requests_module.post(
        f"{AWX_BASE_URL}/api/v2/inventory_sources/5/update/",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    update_id = sync_response.json()["inventory_update"]
    print(f"  Inventory Update ID: {update_id}")

    # Check sync status
    print("\n📊 Sync results:")
    status_response = requests_module.get(
        f"{AWX_BASE_URL}/api/v2/inventory_updates/{update_id}/",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    update_data = status_response.json()
    print(f"  Status: {update_data['status']}")
    print(f"  Source: {update_data['source']}")
    print(f"  Total Hosts: {update_data['total_hosts']}")
    print(f"  Hosts Added: {update_data['hosts_added']}")
    print(f"  Hosts Deleted: {update_data['hosts_deleted']}")
    print(f"  Hosts Updated: {update_data['hosts_updated']}")


@responses.activate
def demo_6_error_handling():
    """Demo 6: Error Handling (Invalid Token)."""
    print_section("Demo 6: Error Handling (Invalid Token)")

    # Mock authentication error
    responses.add(
        responses.GET,
        f"{AWX_BASE_URL}/api/v2/job_templates/",
        json={"detail": "Authentication credentials were not provided."},
        status=401,
    )

    # Try to access with invalid token
    print("🔒 Attempting to list job templates with invalid token...")
    response = requests_module.get(
        f"{AWX_BASE_URL}/api/v2/job_templates/",
        headers={"Authorization": "Bearer invalid-token-12345"},
    )

    print(f"  Status Code: {response.status_code}")
    print(f"  Error: {response.json()['detail']}")
    print("\n✅ Authentication error handled correctly!")


@responses.activate
def demo_7_project_update():
    """Demo 7: Project Update (SCM Sync)."""
    print_section("Demo 7: Project Update (SCM Sync)")

    # Mock project list
    responses.add(
        responses.GET,
        f"{AWX_BASE_URL}/api/v2/projects/",
        json={
            "count": 2,
            "results": [
                {
                    "id": 5,
                    "name": "Chef Migrated Playbooks",
                    "scm_type": "git",
                    "scm_url": "https://github.com/example/chef-playbooks.git",
                    "scm_branch": "main",
                    "status": "successful",
                    "last_updated": "2026-02-16T10:00:00Z",
                },
                {
                    "id": 6,
                    "name": "Ansible Custom Roles",
                    "scm_type": "git",
                    "scm_url": "https://github.com/example/ansible-roles.git",
                    "scm_branch": "production",
                    "status": "successful",
                    "last_updated": "2026-02-15T18:30:00Z",
                },
            ],
        },
        status=200,
    )

    # Mock project update
    responses.add(
        responses.POST,
        f"{AWX_BASE_URL}/api/v2/projects/5/update/",
        json={"project_update": 20, "status": "pending"},
        status=202,
    )

    # Mock project update status
    responses.add(
        responses.GET,
        f"{AWX_BASE_URL}/api/v2/project_updates/20/",
        json={
            "id": 20,
            "status": "successful",
            "scm_revision": "a1b2c3d4e5f6",
            "playbook_counts": {"playbook": 15, "role": 8},
        },
        status=200,
    )

    # List projects
    print("📚 Available projects:")
    list_response = requests_module.get(
        f"{AWX_BASE_URL}/api/v2/projects/",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    for project in list_response.json()["results"]:
        print(f"  - [{project['id']}] {project['name']}")
        print(f"    SCM: {project['scm_type']} ({project['scm_url']})")
        print(f"    Branch: {project['scm_branch']}")
        print(f"    Status: {project['status']}")
        print(f"    Last Updated: {project['last_updated']}")

    # Update project
    print("\n🔄 Updating project #5 (sync from Git)...")
    update_response = requests_module.post(
        f"{AWX_BASE_URL}/api/v2/projects/5/update/",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    update_id = update_response.json()["project_update"]
    print(f"  Project Update ID: {update_id}")

    # Check update status
    print("\n📊 Update results:")
    status_response = requests_module.get(
        f"{AWX_BASE_URL}/api/v2/project_updates/{update_id}/",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    update_data = status_response.json()
    print(f"  Status: {update_data['status']}")
    print(f"  SCM Revision: {update_data['scm_revision']}")
    print(f"  Playbooks: {update_data['playbook_counts']['playbook']}")
    print(f"  Roles: {update_data['playbook_counts']['role']}")


def main():
    """Run all demos."""
    print("=" * 70)
    print("  Mock AWX/AAP API Testing Demo")
    print("  Testing AWX integrations WITHOUT a real AWX server!")
    print("=" * 70)

    try:
        demo_1_list_job_templates()
        demo_2_create_job_template()
        demo_3_launch_and_monitor_job()
        demo_4_workflow_execution()
        demo_5_inventory_management()
        demo_6_error_handling()
        demo_7_project_update()

        print("\n" + "=" * 70)
        print("  ✅ All demos completed successfully!")
        print("  No real AWX server required - all responses were mocked!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
