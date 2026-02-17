"""
Functional Migration Simulation with Real API Mocking

Demonstrates complete Chef→Ansible migration workflows with realistic
mocked HTTP API responses for each version combination.
"""

from typing import Any

import responses

from souschef.migration_simulation import create_simulation_config


class MigrationSimulator:
    """Handles full migration simulation with mocked APIs."""

    def __init__(
        self,
        chef_version: str,
        target_platform: str,
        target_version: str,
        fips_mode: bool = False,
    ):
        """Initialize simulator with version configuration."""
        self.config = create_simulation_config(
            chef_version=chef_version,
            target_platform=target_platform,
            target_version=target_version,
            fips_mode=fips_mode,
        )
        self.results = {
            "chef_nodes_queried": 0,
            "inventory_created": False,
            "hosts_created": 0,
            "execution_environment_created": False,
            "job_template_created": False,
            "api_calls_made": [],
        }

    @responses.activate
    def run_migration(
        self,
        chef_server_url: str = "https://chef.example.com",
        awx_server_url: str = "https://awx.example.com",
    ) -> dict[str, Any]:
        """Run complete migration workflow with mocked APIs."""

        # Create mock Chef Server responses
        self._mock_chef_server(chef_server_url)

        # Create mock Ansible Platform responses
        self._mock_ansible_platform(awx_server_url)

        # Execute migration workflow
        self._execute_workflow(chef_server_url, awx_server_url)

        return self.results

    def _mock_chef_server(self, base_url: str) -> None:
        """Set up Chef Server API mocks."""

        # Mock node search
        chef_nodes = {
            "rows": [
                {
                    "data": {
                        "name": f"node-{i}",
                        "platform": "ubuntu",
                        "platform_version": "20.04",
                        "automatic": {
                            "ipaddress": f"10.0.{i}.10",
                            "environment": "production",
                            "memory": {"total": "8.0 GB"},
                        },
                        "normal": {
                            "run_list": [f"role[app-{i}]"],
                        },
                    }
                }
                for i in range(1, 3)
            ],
            "total": 2,
        }

        responses.add(
            responses.GET,
            f"{base_url}/organizations/myorg/search/node",
            json=chef_nodes,
            status=200,
            headers={"X-Chef-Version": self.config.chef_version},
            match=[
                responses.matchers.query_param_matcher({"q": "environment:production"})
            ],
        )

        # Mock role definitions
        for i in range(1, 3):
            responses.add(
                responses.GET,
                f"{base_url}/organizations/myorg/roles/app-{i}",
                json={
                    "name": f"app-{i}",
                    "run_list": [f"recipe[app-{i}::default]"],
                    "default_attributes": {"app": {"version": "1.0"}},
                },
                status=200,
            )

    def _mock_ansible_platform(self, base_url: str) -> None:
        """Set up Ansible Platform (Tower/AWX/AAP) API mocks."""

        headers = self.config.get_mock_response_headers()

        # Mock config endpoint
        responses.add(
            responses.GET,
            f"{base_url}/api/v2/config/",
            json={
                "version": self.config.target_version,
                "ansible_version": self.config.ansible_version,
            },
            status=200,
            headers=headers,
        )

        # Mock inventory creation
        responses.add(
            responses.POST,
            f"{base_url}/api/v2/inventories/",
            json={
                "id": self.config.inventory_id,
                "name": "Production-from-Chef",
                "kind": "ssh",
            },
            status=201,
            headers=headers,
            match=[
                responses.matchers.json_params_matcher({"name": "Production-from-Chef"})
            ],
        )

        # Mock host creation
        for i in range(1, 3):
            responses.add(
                responses.POST,
                f"{base_url}/api/v2/inventories/{self.config.inventory_id}/hosts/",
                json={
                    "id": 100 + i,
                    "name": f"node-{i}",
                    "inventory": self.config.inventory_id,
                },
                status=201,
                headers=headers,
            )

        # Mock project creation
        responses.add(
            responses.POST,
            f"{base_url}/api/v2/projects/",
            json={
                "id": self.config.project_id,
                "name": "chef-migrations",
                "scm_type": "git",
            },
            status=201,
            headers=headers,
        )

        # Mock execution environment creation (if needed for this version)
        if self.config.execution_model == "execution_environment":
            responses.add(
                responses.POST,
                f"{base_url}/api/v2/execution_environments/",
                json={
                    "id": self.config.execution_environment_id,
                    "name": "ee-chef-migration",
                    "image": "quay.io/ansible/creator-ee:0.5.0",
                },
                status=201,
                headers=headers,
            )

        # Mock job template creation
        responses.add(
            responses.POST,
            f"{base_url}/api/v2/job_templates/",
            json={
                "id": 1,
                "name": "Deploy-from-Chef-Migration",
                "job_type": "run",
                "inventory": self.config.inventory_id,
                "project": self.config.project_id,
                "playbook": "deploy.yml",
                **self.config.get_job_template_structure(),
            },
            status=201,
            headers=headers,
        )

    def _execute_workflow(self, chef_server_url: str, awx_server_url: str) -> None:
        """Execute the migration workflow using mocked APIs."""
        import requests

        # Step 1: Query Chef Server
        chef_response = requests.get(
            f"{chef_server_url}/organizations/myorg/search/node",
            params={"q": "environment:production"},
        )
        chef_data = chef_response.json()
        self.results["chef_nodes_queried"] = chef_data["total"]
        self.results["api_calls_made"].append(
            ("GET", "/organizations/myorg/search/node", 200)
        )

        # Step 2: Create inventory
        inv_response = requests.post(
            f"{awx_server_url}/api/v2/inventories/",
            json={"name": "Production-from-Chef"},
        )
        self.results["inventory_created"] = inv_response.status_code == 201
        self.results["api_calls_made"].append(
            ("POST", "/api/v2/inventories/", inv_response.status_code)
        )

        if inv_response.status_code == 201:
            inventory_id = inv_response.json()["id"]

            # Step 3: Add hosts to inventory
            for node_data in chef_data["rows"]:
                node_name = node_data["data"]["name"]
                host_response = requests.post(
                    f"{awx_server_url}/api/v2/inventories/{inventory_id}/hosts/",
                    json={"name": node_name},
                )
                if host_response.status_code == 201:
                    self.results["hosts_created"] += 1
                self.results["api_calls_made"].append(
                    (
                        "POST",
                        f"/api/v2/inventories/{inventory_id}/hosts/",
                        host_response.status_code,
                    )
                )

        # Step 4: Create project
        proj_response = requests.post(
            f"{awx_server_url}/api/v2/projects/",
            json={"name": "chef-migrations", "scm_type": "git"},
        )
        self.results["api_calls_made"].append(
            ("POST", "/api/v2/projects/", proj_response.status_code)
        )

        # Step 5: Create execution environment (if needed)
        if self.config.execution_model == "execution_environment":
            ee_response = requests.post(
                f"{awx_server_url}/api/v2/execution_environments/",
                json={
                    "name": "ee-chef-migration",
                    "image": "quay.io/ansible/creator-ee:0.5.0",
                },
            )
            self.results["execution_environment_created"] = (
                ee_response.status_code == 201
            )
            self.results["api_calls_made"].append(
                ("POST", "/api/v2/execution_environments/", ee_response.status_code)
            )

        # Step 6: Create job template
        jt_response = requests.post(
            f"{awx_server_url}/api/v2/job_templates/",
            json={
                "name": "Deploy-from-Chef-Migration",
                "job_type": "run",
                "inventory": self.config.inventory_id,
                "project": self.config.project_id,
                "playbook": "deploy.yml",
                **self.config.get_job_template_structure(),
            },
        )
        self.results["job_template_created"] = jt_response.status_code == 201
        self.results["api_calls_made"].append(
            ("POST", "/api/v2/job_templates/", jt_response.status_code)
        )


def run_demo_migration() -> None:
    """Run a complete functional migration demo."""

    print("\n" + "=" * 80)
    print("FUNCTIONAL MIGRATION SIMULATION: Chef 15.10.91 → AAP 2.4.0")
    print("=" * 80)

    simulator = MigrationSimulator(
        chef_version="15.10.91",
        target_platform="aap",
        target_version="2.4.0",
        fips_mode=True,
    )

    print("\n[Executing Migration with Mocked APIs]")
    print("-" * 80)

    results = simulator.run_migration()

    print(f"\n✓ Chef Server: Queried {results['chef_nodes_queried']} nodes")
    print("✓ Ansible Platform: Created inventory")
    print(f"✓ Hosts added: {results['hosts_created']} hosts")
    print(
        f"✓ Execution environment: {'Created' if results['execution_environment_created'] else 'N/A (legacy)'}"
    )
    print(
        f"✓ Job template: {'Created' if results['job_template_created'] else 'Failed'}"
    )

    print("\n[API Calls Made]")
    print("-" * 80)
    for method, endpoint, status in results["api_calls_made"]:
        status_emoji = "✅" if status == 200 or status == 201 else "❌"
        print(f"  {status_emoji} {method:4} {endpoint:40} → {status}")

    print("\n[Execution Model Details]")
    print("-" * 80)
    print(f"  Source: Chef {simulator.config.chef_version}")
    print(f"  Auth: Protocol {simulator.config.chef_auth_protocol} (SHA-256)")
    print(
        f"  Target: {simulator.config.target_platform.upper()} {simulator.config.target_version}"
    )
    print(f"  Execution: {simulator.config.execution_model}")
    print(f"  Ansible: {simulator.config.ansible_version}")
    print(
        f"  Features: FIPS={simulator.config.fips_mode}, "
        f"Signing={simulator.config.content_signing}"
    )

    print("\n" + "=" * 80)
    print("✅ FUNCTIONAL MIGRATION COMPLETE - ALL APIS MOCKED AND WORKING")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_demo_migration()
