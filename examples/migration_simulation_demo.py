"""
Demonstration: Migration Simulation in Action

Shows a complete Chef 15.10.91 → AAP 2.4.0 migration simulation workflow
with realistic mocked API responses.
"""

import json

from souschef.migration_simulation import create_simulation_config


def demo_simulation():
    """Run complete migration simulation demonstration."""

    print("\n" + "=" * 80)
    print("MIGRATION SIMULATION DEMO: Chef 15.10.91 → AAP 2.4.0")
    print("=" * 80)

    # ===== STAGE 1: Configure Simulation =====
    print("\n[STAGE 1] 🔧 Configuring Simulation")
    print("-" * 80)

    config = create_simulation_config(
        chef_version="15.10.91",
        target_platform="aap",
        target_version="2.4.0",
        fips_mode=True,
        inventory_id=1,
        project_id=2,
        execution_environment_id=42,
    )

    print(f"Source: Chef Server {config.chef_version}")
    print(f"  • Authentication: Protocol {config.chef_auth_protocol} (SHA-256)")
    print(f"  • FIPS Mode: {config.fips_mode}")
    print(f"Target: AAP {config.target_version}")
    print(f"  • Execution Model: {config.execution_model}")
    print(f"  • Ansible Version: {config.ansible_version}")
    print(f"  • Content Signing: {config.content_signing}")

    # ===== STAGE 2: Show Mock Endpoints =====
    print("\n[STAGE 2] 📡 Available Mock Endpoints")
    print("-" * 80)

    print(f"Will mock {len(config.available_endpoints)} AAP 2.4.0 API endpoints:")
    for i, endpoint in enumerate(config.available_endpoints, 1):
        print(f"  {i:2}. POST {endpoint}")

    # ===== STAGE 3: Show Response Headers =====
    print("\n[STAGE 3] 📋 Mock Response Headers")
    print("-" * 80)

    headers = config.get_mock_response_headers()
    for key, value in headers.items():
        print(f"  {key}: {value}")

    # ===== STAGE 4: Show Job Template Structure =====
    print("\n[STAGE 4] 📝 Job Template Structure")
    print("-" * 80)

    jt = config.get_job_template_structure()
    print("Generated job template will have these fields:")
    print(json.dumps(jt, indent=2))

    # ===== STAGE 5: Simulate Chef Server Query =====
    print("\n[STAGE 5] 🍳 Simulated Chef Server Response")
    print("-" * 80)

    mock_chef_response = {
        "rows": [
            {
                "data": {
                    "name": "web-prod-01",
                    "platform": "ubuntu",
                    "platform_version": "20.04",
                    "automatic": {
                        "ipaddress": "10.0.1.10",  # NOSONAR - S1313: mock data for demo
                        "environment": "production",
                    },
                    "normal": {
                        "run_list": ["role[webserver]", "recipe[nginx::default]"]
                    },
                }
            },
            {
                "data": {
                    "name": "app-prod-01",
                    "platform": "ubuntu",
                    "platform_version": "20.04",
                    "automatic": {
                        "ipaddress": "10.0.2.10",  # NOSONAR - S1313: mock data for demo
                        "environment": "production",
                    },
                    "normal": {"run_list": ["role[app]", "recipe[chef-app::deploy]"]},
                }
            },
        ],
        "total": 2,
    }

    print("Query: GET /organizations/myorg/search/node?q=environment:production")
    print(f"Response: {mock_chef_response['total']} nodes found")
    for row in mock_chef_response["rows"]:
        node = row["data"]
        print(
            f"  • {node['name']}: {node['automatic']['ipaddress']} ({node['platform']})"
        )

    # ===== STAGE 6: Simulate Inventory Creation =====
    print("\n[STAGE 6] 📦 Simulated AAP Inventory Creation")
    print("-" * 80)

    mock_inventory_response = {
        "id": 1,
        "name": "Production-from-Chef",
        "description": "Migrated from Chef Server 15.10.91",
        "kind": "ssh",
        "organization": 1,
        "created": "2026-02-16T10:30:00Z",
    }

    print("POST /api/v2/inventories/")
    print(f"Response: {mock_inventory_response['id']}")
    print(json.dumps(mock_inventory_response, indent=2))

    # ===== STAGE 7: Simulate Host Addition =====
    print("\n[STAGE 7] 🖥️ Simulated Host Addition to Inventory")
    print("-" * 80)

    for node in mock_chef_response["rows"]:
        host_data = node["data"]
        mock_host_response = {
            "id": hash(host_data["name"]) % 1000 + 100,
            "name": host_data["name"],
            "inventory": 1,
            "variables": json.dumps(
                {
                    "ansible_host": host_data["automatic"]["ipaddress"],
                    "platform": host_data["platform"],
                    "chef_environment": host_data["automatic"]["environment"],
                }
            ),
        }
        print("POST /api/v2/inventories/1/hosts/")
        print(f"  Host: {mock_host_response['name']}")
        print(f"  IP: {host_data['automatic']['ipaddress']}")
        print(f"  ID: {mock_host_response['id']}")

    # ===== STAGE 8: Simulate EE Creation =====
    print("\n[STAGE 8] 🎪 Simulated Execution Environment Setup")
    print("-" * 80)

    mock_ee_response = {
        "id": 42,
        "name": "ee-chef-migration-15",
        "image": "quay.io/ansible/creator-ee:0.5.0",
        "pull": "always",
        "description": "EE for Chef 15.10.91 migration with content signing",
    }

    print("POST /api/v2/execution_environments/")
    print(f"Response ID: {mock_ee_response['id']}")
    print(json.dumps(mock_ee_response, indent=2))

    # ===== STAGE 9: Simulate Job Template Creation =====
    print("\n[STAGE 9] 🎬 Simulated Job Template Creation")
    print("-" * 80)

    mock_jt_response = {
        "id": 1,
        "name": "Deploy-from-Chef-Migration",
        "job_type": "run",
        "inventory": 1,
        "project": 2,
        "playbook": "deploy_chef_to_ansible.yml",
        "execution_environment": 42,  # ← KEY DIFFERENCE from Tower/old AWX
        "extra_vars": json.dumps({"source": "chef-15.10.91", "target": "aap-2.4"}),
        "verbosity": 1,
        "forks": 5,
        "limit": "",
        "organization": 1,
        "ask_extra_vars": False,
        "ask_tags": False,
        "ask_limit": False,
        "content_signing": True,  # ← AAP 2.4 feature
        "sign_key": "https://aap.example.com/api/v2/signing_keys/1/",
        "created": "2026-02-16T10:35:00Z",
        "modified": "2026-02-16T10:35:00Z",
        "url": "https://aap.example.com/api/v2/job_templates/1/",
    }

    print("POST /api/v2/job_templates/")
    print(f"Response ID: {mock_jt_response['id']}")
    print(f"  Name: {mock_jt_response['name']}")
    print(
        f"  Execution Environment: {mock_jt_response['execution_environment']} (REQUIRED)"
    )
    print(f"  Content Signing: {mock_jt_response['content_signing']} (AAP 2.4 feature)")
    print(f"  Ansible: {config.ansible_version}")
    print("  Status: ✅ Ready to run")

    # ===== STAGE 10: Validation Summary =====
    print("\n[STAGE 10] ✅ Validation Summary")
    print("-" * 80)

    validation = {
        "source_chef_version": config.chef_version,
        "source_auth_protocol": "1.3 (SHA-256)",
        "source_fips_mode": config.fips_mode,
        "target_platform": config.target_platform,
        "target_version": config.target_version,
        "target_ansible_version": config.ansible_version,
        "target_execution_model": config.execution_model,
        "target_content_signing": config.content_signing,
        "nodes_queried": mock_chef_response["total"],
        "hosts_created": mock_chef_response["total"],
        "execution_environments_created": 1,
        "job_templates_created": 1,
        "endpoints_used": len(mock_chef_response["rows"])
        + 4,  # hosts + inventory + EE + JT
        "status": "✅ SUCCESS",
    }

    print(json.dumps(validation, indent=2))

    # ===== FINAL REPORT =====
    print("\n" + "=" * 80)
    print("✅ MIGRATION SIMULATION COMPLETE")
    print("=" * 80)
    print(f"""
Simulation: Chef {config.chef_version} → AAP {config.target_version}

✓ Configured for production environment
✓ {mock_chef_response["total"]} nodes migrated to Ansible inventory
✓ Execution environment created with EE-based model (not legacy virtualenv)
✓ Job template configured with content signing for supply chain security
✓ FIPS compliance enabled
✓ Ansible {config.ansible_version} core version requirement met

Next steps:
  1. Execute migration with mocked APIs
  2. Run generated playbook: {mock_jt_response["playbook"]}
  3. Validate against {len(config.available_endpoints)} available AAP 2.4 endpoints
  4. Deploy to production
""")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    demo_simulation()
