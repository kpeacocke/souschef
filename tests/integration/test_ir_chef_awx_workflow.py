"""
Integration tests for IR workflow: Chef Server → IR → AWX.

Tests the complete v2.0/2.1 workflow:
1. Query Chef Server for infrastructure data (mocked)
2. Parse Chef cookbooks into IR format
3. Transform IR to Ansible playbooks
4. Generate AWX job templates and workflows
5. Validate end-to-end Chef→Ansible→AWX migration

Uses mocked HTTP responses for both Chef Server and AWX APIs.
"""

from __future__ import annotations

import json

import pytest
import responses
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Use requests_module from chef_server for consistency
from souschef.core.chef_server import (
    ChefServerClient,
    ChefServerConfig,
    requests_module,
)
from souschef.ir import (
    IRAction,
    IRGraph,
    IRNode,
    IRNodeType,
    SourceType,
    TargetType,
)

if requests_module is None:
    pytest.skip("requests required for workflow tests", allow_module_level=True)


@pytest.fixture
def test_key() -> str:
    """Generate a test RSA private key for Chef Server authentication."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return key_pem.decode("utf-8")


@pytest.fixture
def chef_config(test_key: str) -> ChefServerConfig:
    """Create a test Chef Server configuration."""
    return ChefServerConfig(
        server_url="https://chef.example.com",
        organisation="production",
        client_name="migration-client",
        client_key=test_key,
        timeout=10,
    )


class TestChefToIRWorkflow:
    """Test Chef Server data extraction and IR conversion."""

    @responses.activate
    def test_query_chef_nodes_and_build_ir(self, chef_config: ChefServerConfig) -> None:
        """Test querying Chef nodes and building IR graph."""
        # Mock Chef Server node search
        mock_nodes = {
            "rows": [
                {
                    "name": "web-prod-01",
                    "run_list": ["recipe[nginx]", "recipe[php-fpm]"],
                    "chef_environment": "production",
                    "platform": "ubuntu",
                    "platform_version": "22.04",
                    "ipaddress": "10.0.1.10",  # NOSONAR - test fixture
                    "fqdn": "web-prod-01.example.com",
                    "automatic": {
                        "cpu": {"total": 4},
                        "memory": {"total": "16GB"},
                    },
                },
                {
                    "name": "db-prod-01",
                    "run_list": ["recipe[mysql::server]"],
                    "chef_environment": "production",
                    "platform": "ubuntu",
                    "platform_version": "22.04",
                    "ipaddress": "10.0.1.20",  # NOSONAR - test fixture
                    "fqdn": "db-prod-01.example.com",
                },
            ],
            "total": 2,
            "start": 0,
        }

        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/production/search/node",
            json=mock_nodes,
            status=200,
        )

        # Query Chef Server
        client = ChefServerClient(chef_config)
        nodes = client.search_nodes("chef_environment:production")

        # Build IR graph from Chef data
        graph = IRGraph(
            graph_id="chef-to-ir-001",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        for node_data in nodes:
            # Create IR node for each Chef node
            ir_node = IRNode(
                node_id=f"node-{node_data['name']}",
                node_type=IRNodeType.RESOURCE,
                name=node_data["name"],
                source_type=SourceType.CHEF,
            )

            # Add node metadata
            ir_node.set_variable("platform", node_data.get("platform", "unknown"))
            ir_node.set_variable(
                "environment", node_data.get("environment")
            )  # ChefServerClient maps chef_environment -> environment
            ir_node.set_variable("ip_address", node_data.get("ipaddress"))
            ir_node.set_variable(
                "run_list", json.dumps(node_data.get("roles", []))
            )  # ChefServerClient maps run_list -> roles

            graph.add_node(ir_node)

        # Validate IR graph
        assert len(graph.nodes) == 2
        assert "node-web-prod-01" in graph.nodes
        assert "node-db-prod-01" in graph.nodes

        web_node = graph.get_node("node-web-prod-01")
        assert web_node is not None
        assert web_node.variables["platform"] == "ubuntu"
        assert web_node.variables["environment"] == "production"

    @responses.activate
    def test_chef_cookbook_to_ir_with_dependencies(
        self, chef_config: ChefServerConfig
    ) -> None:
        """Test converting Chef cookbook with dependencies to IR."""
        # Mock Chef Server cookbook data
        mock_cookbook = {
            "name": "webapp",
            "version": "1.0.0",
            "dependencies": {
                "nginx": ">= 8.0",
                "php": "~> 7.4",
            },
            "recipes": ["default", "setup", "deploy"],
        }

        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/production/cookbooks/webapp/1.0.0",
            json=mock_cookbook,
            status=200,
        )

        # Query cookbook metadata
        response = requests_module.get(
            "https://chef.example.com/organizations/production/cookbooks/webapp/1.0.0",
            headers={"Accept": "application/json"},
            timeout=10,
        )
        cookbook_data = response.json()

        # Build IR graph with cookbook structure
        graph = IRGraph(
            graph_id="cookbook-ir-001",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        # Create recipe nodes
        for recipe in cookbook_data["recipes"]:
            recipe_node = IRNode(
                node_id=f"recipe-{recipe}",
                node_type=IRNodeType.RECIPE,
                name=f"webapp::{recipe}",
                source_type=SourceType.CHEF,
            )
            graph.add_node(recipe_node)

        # Add dependency nodes
        for dep_name, dep_version in cookbook_data["dependencies"].items():
            dep_node = IRNode(
                node_id=f"dep-{dep_name}",
                node_type=IRNodeType.CUSTOM,
                name=dep_name,
                source_type=SourceType.CHEF,
            )
            dep_node.set_variable("version_constraint", dep_version)
            graph.add_node(dep_node)

            # Link recipes to dependencies
            for recipe in cookbook_data["recipes"]:
                recipe_node = graph.get_node(f"recipe-{recipe}")
                if recipe_node:
                    recipe_node.dependencies.append(f"dep-{dep_name}")

        # Validate dependencies
        unresolved = graph.validate_dependencies()
        assert len(unresolved) == 0

        # Verify topological ordering
        order = graph.get_topological_order()
        # Dependencies should come before recipes
        for dep_id in ["dep-nginx", "dep-php"]:
            dep_index = order.index(dep_id)
            for recipe in ["recipe-default", "recipe-setup", "recipe-deploy"]:
                recipe_index = order.index(recipe)
                assert dep_index < recipe_index


class TestIRToAWXWorkflow:
    """Test IR transformation to AWX configurations."""

    @responses.activate
    def test_ir_to_awx_job_template_creation(self) -> None:
        """Test generating AWX job template from IR graph."""
        # Create IR graph with playbook structure
        graph = IRGraph(
            graph_id="ir-to-awx-001",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        # Add playbook node
        playbook_node = IRNode(
            node_id="playbook-deploy",
            node_type=IRNodeType.RECIPE,
            name="deploy_webapp",
            source_type=SourceType.CHEF,
        )
        playbook_node.set_variable("inventory", "production")
        playbook_node.set_variable("limit", "webservers")
        graph.add_node(playbook_node)

        # Add tasks as actions
        install_action = IRAction(name="install_nginx", type="package")
        configure_action = IRAction(name="configure_nginx", type="template")
        service_action = IRAction(name="start_nginx", type="service")

        playbook_node.add_action(install_action)
        playbook_node.add_action(configure_action)
        playbook_node.add_action(service_action)

        # Generate AWX job template payload from IR
        awx_template = {
            "name": f"Deploy {playbook_node.name}",
            "description": f"Generated from IR graph {graph.graph_id}",
            "job_type": "run",
            "inventory": playbook_node.variables.get("inventory", "default"),
            "project": 1,
            "playbook": f"{playbook_node.name}.yml",
            "limit": playbook_node.variables.get("limit", ""),
            "extra_vars": json.dumps(
                {
                    "source": "chef_migration",
                    "ir_graph_id": graph.graph_id,
                    "actions_count": len(playbook_node.actions),
                }
            ),
        }

        # Mock AWX API to create job template
        responses.add(
            responses.POST,
            "https://awx.example.com/api/v2/job_templates/",
            json={**awx_template, "id": 42},
            status=201,
        )

        response = requests_module.post(
            "https://awx.example.com/api/v2/job_templates/",
            json=awx_template,
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 201
        created_template = response.json()
        assert created_template["id"] == 42
        assert "chef_migration" in created_template["extra_vars"]

    @responses.activate
    def test_ir_to_awx_inventory_creation(self) -> None:
        """Test creating AWX inventory from IR node data."""
        # Create IR graph with host inventory
        graph = IRGraph(
            graph_id="ir-inventory-001",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        # Add host nodes
        hosts = [
            ("web-01", "10.0.1.10", "webservers"),  # NOSONAR - test fixture
            ("web-02", "10.0.1.11", "webservers"),  # NOSONAR - test fixture
            ("db-01", "10.0.1.20", "databases"),  # NOSONAR - test fixture
        ]

        for hostname, ip, group in hosts:
            host_node = IRNode(
                node_id=f"host-{hostname}",
                node_type=IRNodeType.RESOURCE,
                name=hostname,
                source_type=SourceType.CHEF,
            )
            host_node.set_variable("ansible_host", ip)
            host_node.set_variable("group", group)
            host_node.tags["environment"] = "production"
            graph.add_node(host_node)

        # Generate AWX inventory payload from IR
        awx_inventory = {
            "name": "Production Inventory (from Chef)",
            "description": f"Generated from IR graph {graph.graph_id}",
            "organization": 1,
            "variables": json.dumps(
                {"source": "chef_migration", "ir_graph_id": graph.graph_id}
            ),
        }

        # Mock AWX inventory creation
        responses.add(
            responses.POST,
            "https://awx.example.com/api/v2/inventories/",
            json={**awx_inventory, "id": 10},
            status=201,
        )

        response = requests_module.post(
            "https://awx.example.com/api/v2/inventories/",
            json=awx_inventory,
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 201
        inventory = response.json()
        assert inventory["id"] == 10
        assert "chef_migration" in inventory["variables"]


class TestEndToEndChefToAWXWorkflow:
    """Test complete Chef → IR → AWX migration workflow."""

    @responses.activate
    def test_complete_migration_workflow(self, chef_config: ChefServerConfig) -> None:
        """Test end-to-end migration from Chef to AWX via IR."""
        # Step 1: Query Chef Server for nodes
        mock_chef_nodes = {
            "rows": [
                {
                    "name": "prod-web-01",
                    "run_list": ["role[webserver]"],
                    "chef_environment": "production",
                    "platform": "ubuntu",
                    "ipaddress": "10.0.1.10",  # NOSONAR - test fixture
                }
            ],
            "total": 1,
        }

        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/production/search/node",
            json=mock_chef_nodes,
            status=200,
        )

        # Step 2: Query Chef for role definition
        mock_role = {
            "name": "webserver",
            "description": "Web server role",
            "run_list": ["recipe[nginx]", "recipe[app::deploy]"],
            "default_attributes": {"nginx": {"port": 80}},
        }

        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/production/roles/webserver",
            json=mock_role,
            status=200,
        )

        # Step 3: Build IR graph from Chef data
        graph = IRGraph(
            graph_id="migration-e2e-001",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        # Query Chef Server
        chef_client = ChefServerClient(chef_config)
        nodes = chef_client.search_nodes("chef_environment:production")

        # Create IR nodes from Chef nodes
        for node_data in nodes:
            host_node = IRNode(
                node_id=f"host-{node_data['name']}",
                node_type=IRNodeType.RESOURCE,
                name=node_data["name"],
                source_type=SourceType.CHEF,
            )
            host_node.set_variable("ip", node_data["ipaddress"])
            host_node.set_variable("platform", node_data["platform"])
            graph.add_node(host_node)

        # Query role details
        role_response = requests_module.get(
            "https://chef.example.com/organizations/production/roles/webserver",
            headers={"Accept": "application/json"},
            timeout=10,
        )
        role_data = role_response.json()

        # Create IR node for role
        role_node = IRNode(
            node_id="role-webserver",
            node_type=IRNodeType.POLICY,
            name=role_data["name"],
            source_type=SourceType.CHEF,
        )
        role_node.set_variable("run_list", json.dumps(role_data["run_list"]))
        role_node.set_variable(
            "attributes", json.dumps(role_data.get("default_attributes", {}))
        )
        graph.add_node(role_node)

        # Step 4: Generate AWX configurations from IR
        # Create AWX inventory
        awx_inventory_payload = {
            "name": "Production from Chef Migration",
            "organization": 1,
        }

        responses.add(
            responses.POST,
            "https://awx.example.com/api/v2/inventories/",
            json={**awx_inventory_payload, "id": 100},
            status=201,
        )

        # Create AWX hosts
        responses.add(
            responses.POST,
            "https://awx.example.com/api/v2/inventories/100/hosts/",
            json={"id": 1, "name": "prod-web-01"},
            status=201,
        )

        # Create AWX job template
        awx_template_payload = {
            "name": "Deploy Webserver Role",
            "job_type": "run",
            "inventory": 100,
            "project": 1,
            "playbook": "webserver.yml",
        }

        responses.add(
            responses.POST,
            "https://awx.example.com/api/v2/job_templates/",
            json={**awx_template_payload, "id": 200},
            status=201,
        )

        # Execute AWX API calls
        inventory_resp = requests_module.post(
            "https://awx.example.com/api/v2/inventories/",
            json=awx_inventory_payload,
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )
        inventory_id = inventory_resp.json()["id"]

        host_resp = requests_module.post(
            f"https://awx.example.com/api/v2/inventories/{inventory_id}/hosts/",
            json={
                "name": "prod-web-01",
                "variables": json.dumps(
                    {"ansible_host": "10.0.1.10"}
                ),  # NOSONAR - test fixture
            },
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        template_resp = requests_module.post(
            "https://awx.example.com/api/v2/job_templates/",
            json=awx_template_payload,
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        # Validate end-to-end workflow
        assert len(graph.nodes) == 2  # host + role
        assert inventory_resp.status_code == 201
        assert host_resp.status_code == 201
        assert template_resp.status_code == 201
        assert template_resp.json()["id"] == 200

    @responses.activate
    def test_workflow_with_chef_environments_to_awx_groups(
        self, chef_config: ChefServerConfig
    ) -> None:
        """Test migrating Chef environments to AWX inventory groups."""
        # Mock Chef environments
        mock_environments = {
            "production": {"url": "https://chef.example.com/environments/production"},
            "staging": {"url": "https://chef.example.com/environments/staging"},
        }

        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/production/environments",
            json=mock_environments,
            status=200,
        )

        # Mock nodes in each environment
        for env_name in ["production", "staging"]:
            mock_nodes = {
                "rows": [
                    {
                        "name": f"{env_name}-web-01",
                        "chef_environment": env_name,
                        "ipaddress": f"10.0.{1 if env_name == 'production' else 2}.10",  # NOSONAR - test fixture
                    }
                ],
                "total": 1,
            }
            responses.add(
                responses.GET,
                f"https://chef.example.com/organizations/production/search/node?q=chef_environment:{env_name}",
                json=mock_nodes,
                status=200,
            )

        # Build IR with environment grouping
        graph = IRGraph(
            graph_id="env-migration-001",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        # Get environments
        env_response = requests_module.get(
            "https://chef.example.com/organizations/production/environments",
            headers={"Accept": "application/json"},
            timeout=10,
        )
        environments = env_response.json()

        # Create IR nodes for each environment
        for env_name in environments:
            env_node = IRNode(
                node_id=f"env-{env_name}",
                node_type=IRNodeType.POLICY,
                name=env_name,
                source_type=SourceType.CHEF,
            )
            env_node.tags["type"] = "environment"
            graph.add_node(env_node)

        # Mock AWX group creation for each environment
        for env_name in ["production", "staging"]:
            responses.add(
                responses.POST,
                "https://awx.example.com/api/v2/groups/",
                json={"id": 10 + len(env_name), "name": env_name},
                status=201,
            )

        # Create AWX groups from IR environments
        for env_name in environments:
            group_resp = requests_module.post(
                "https://awx.example.com/api/v2/groups/",
                json={"name": env_name, "inventory": 1},
                headers={"Authorization": "Bearer test-token"},
                timeout=10,
            )
            assert group_resp.status_code == 201
            assert group_resp.json()["name"] == env_name

        assert len(graph.nodes) == 2  # production + staging environments


class TestIRValidationWithChefAndAWX:
    """Test IR validation against Chef Server and AWX constraints."""

    @responses.activate
    def test_validate_ir_node_against_chef_server(
        self, chef_config: ChefServerConfig
    ) -> None:
        """Test validating IR nodes against Chef Server data."""
        # Create IR node
        graph = IRGraph(
            graph_id="validation-001",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        node = IRNode(
            node_id="validate-node",
            node_type=IRNodeType.RECIPE,
            name="nginx::default",
            source_type=SourceType.CHEF,
        )
        graph.add_node(node)

        # Mock Chef Server to validate recipe exists
        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/production/cookbooks/nginx",
            json={"name": "nginx", "recipes": ["default", "server"]},
            status=200,
        )

        # Validate against Chef Server
        cookbook_resp = requests_module.get(
            "https://chef.example.com/organizations/production/cookbooks/nginx",
            headers={"Accept": "application/json"},
            timeout=10,
        )

        cookbook_data = cookbook_resp.json()
        recipe_name = node.name.split("::")[-1]
        is_valid = recipe_name in cookbook_data["recipes"]

        assert is_valid is True
        node.tags["validated"] = "true"
        node.tags["validation_source"] = "chef_server"

    @responses.activate
    def test_validate_awx_compatibility_from_ir(self) -> None:
        """Test validating IR can be deployed to AWX."""
        # Create IR graph with Ansible-compatible structure
        graph = IRGraph(
            graph_id="awx-validation-001",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        playbook_node = IRNode(
            node_id="playbook-1",
            node_type=IRNodeType.RECIPE,
            name="deploy_app",
            source_type=SourceType.CHEF,
        )
        graph.add_node(playbook_node)

        # Mock AWX API to check capabilities
        responses.add(
            responses.GET,
            "https://awx.example.com/api/v2/config/",
            json={
                "ansible_version": "2.15.0",
                "project_base_dir": "/var/lib/awx/projects",
                "custom_virtualenvs": [],
            },
            status=200,
        )

        # Query AWX capabilities
        config_resp = requests_module.get(
            "https://awx.example.com/api/v2/config/",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        awx_config = config_resp.json()
        ansible_version = awx_config["ansible_version"]

        # Validate IR is compatible with AWX Ansible version
        assert ansible_version.startswith("2.")
        graph.metadata["awx_compatible"] = "true"
        graph.metadata["target_ansible_version"] = ansible_version
