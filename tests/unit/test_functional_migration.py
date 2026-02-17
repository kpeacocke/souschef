"""
Tests for functional migration simulation with real API mocking.

Validates that migrations work correctly for all supported version combinations
with realistic mocked HTTP API responses.
"""

import pytest

from examples.functional_migration_sim import MigrationSimulator


class TestMigrationSimulator:
    """Test suite for MigrationSimulator with all version combinations."""

    @pytest.mark.parametrize(
        "chef_version,platform,target_version",
        [
            # Legacy migrations (virtualenv-based)
            ("12.19.36", "tower", "3.8.5"),
            ("12.19.36", "awx", "20.1.0"),
            # Transition migrations (execution environment support)
            ("14.15.6", "awx", "21.0.0"),
            ("14.15.6", "awx", "22.0.0"),
            ("14.15.6", "awx", "24.6.1"),
            # Modern migrations (EE required + features)
            ("15.10.91", "aap", "2.4.0"),
            ("15.10.91", "awx", "24.6.1"),
        ],
    )
    def test_migration_initialization(
        self, chef_version: str, platform: str, target_version: str
    ) -> None:
        """Test that simulator initializes correctly for each version combo."""
        simulator = MigrationSimulator(
            chef_version=chef_version,
            target_platform=platform,
            target_version=target_version,
        )

        assert simulator.config.chef_version == chef_version
        assert simulator.config.target_platform == platform
        assert simulator.config.target_version == target_version

    @pytest.mark.parametrize(
        "chef_version,platform,target_version",
        [
            ("12.19.36", "tower", "3.8.5"),
            ("14.15.6", "awx", "22.0.0"),
            ("15.10.91", "aap", "2.4.0"),
        ],
    )
    def test_migration_workflow_execution(
        self, chef_version: str, platform: str, target_version: str
    ) -> None:
        """Test complete migration workflow for different version combos."""
        simulator = MigrationSimulator(
            chef_version=chef_version,
            target_platform=platform,
            target_version=target_version,
        )

        results = simulator.run_migration()

        # Verify all migration stages completed
        assert results["chef_nodes_queried"] > 0
        assert results["inventory_created"] is True
        assert results["hosts_created"] > 0
        assert results["job_template_created"] is True
        assert len(results["api_calls_made"]) > 0

    @pytest.mark.parametrize(
        "chef_version,platform,target_version,expect_ee",
        [
            ("12.19.36", "tower", "3.8.5", False),  # virtualenv
            ("12.19.36", "awx", "20.1.0", False),  # virtualenv
            ("14.15.6", "awx", "21.0.0", True),  # EE
            ("15.10.91", "aap", "2.4.0", True),  # EE required
        ],
    )
    def test_execution_model_by_version(
        self,
        chef_version: str,
        platform: str,
        target_version: str,
        expect_ee: bool,
    ) -> None:
        """Test that execution model is correct for each version."""
        simulator = MigrationSimulator(
            chef_version=chef_version,
            target_platform=platform,
            target_version=target_version,
        )

        if expect_ee:
            assert simulator.config.execution_model == "execution_environment"
            assert (
                "execution_environment" in simulator.config.get_job_template_structure()
            )
        else:
            assert simulator.config.execution_model == "custom_virtualenv"
            assert "custom_virtualenv" in simulator.config.get_job_template_structure()

    @pytest.mark.parametrize(
        "chef_version,expect_fips",
        [
            ("12.19.36", False),
            ("14.15.6", False),
            ("15.10.91", True),  # 1510 supports FIPS
        ],
    )
    def test_fips_support_by_chef_version(
        self, chef_version: str, expect_fips: bool
    ) -> None:
        """Test FIPS mode support based on Chef version."""
        simulator = MigrationSimulator(
            chef_version=chef_version,
            target_platform="aap",
            target_version="2.4.0",
            fips_mode=True,
        )

        # FIPS mode annotation (for 15.x only)
        if expect_fips:
            assert simulator.config.fips_mode is True

    def test_aap_requires_content_signing(self) -> None:
        """Test that AAP target automatically requires content signing."""
        simulator = MigrationSimulator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        assert simulator.config.content_signing is True
        structure = simulator.config.get_job_template_structure()
        assert structure["content_signing"] is True

    @pytest.mark.parametrize(
        "platform,target_version,expected_endpoints",
        [
            ("tower", "3.8.5", 6),  # Tower 3.8
            ("awx", "20.1.0", 7),  # AWX 20 with virtualenv
            ("awx", "21.0.0", 8),  # AWX 21+ with EE
            ("awx", "24.6.1", 8),  # AWX 24 with mesh
            ("aap", "2.4.0", 10),  # AAP 2.4 with all features
        ],
    )
    def test_available_endpoints_by_version(
        self,
        platform: str,
        target_version: str,
        expected_endpoints: int,
    ) -> None:
        """Test that correct API endpoints are available for each version."""
        simulator = MigrationSimulator(
            chef_version="14.15.6",
            target_platform=platform,
            target_version=target_version,
        )

        endpoints = simulator.config.available_endpoints
        assert len(endpoints) == expected_endpoints
        # All should have core endpoints
        assert "/api/v2/inventories/" in endpoints
        assert "/api/v2/job_templates/" in endpoints

    def test_mock_response_headers_tower(self) -> None:
        """Test that mock headers identify Tower correctly."""
        simulator = MigrationSimulator(
            chef_version="12.19.36",
            target_platform="tower",
            target_version="3.8.5",
        )

        headers = simulator.config.get_mock_response_headers()
        assert "Ansible Tower 3.8.5" in headers["Server"]

    def test_mock_response_headers_awx(self) -> None:
        """Test that mock headers identify AWX correctly."""
        simulator = MigrationSimulator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

        headers = simulator.config.get_mock_response_headers()
        assert "AWX 24.6.1" in headers["Server"]

    def test_mock_response_headers_aap(self) -> None:
        """Test that mock headers identify AAP correctly."""
        simulator = MigrationSimulator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        headers = simulator.config.get_mock_response_headers()
        assert "Ansible Automation Platform 2.4.0" in headers["Server"]

    @pytest.mark.parametrize("chef_version", ["12.19.36", "14.15.6", "15.10.91"])
    def test_all_chef_versions_supported(self, chef_version: str) -> None:
        """Test that all Chef versions can initialize simulators."""
        # Use universal compatible target
        simulator = MigrationSimulator(
            chef_version=chef_version,
            target_platform="awx",
            target_version="24.6.1",
        )

        assert simulator.config.chef_version == chef_version

    def test_config_json_serializable(self) -> None:
        """Test that configuration can be serialized to JSON."""
        import json

        simulator = MigrationSimulator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        config_dict = {
            "chef_version": simulator.config.chef_version,
            "target_platform": simulator.config.target_platform,
            "target_version": simulator.config.target_version,
            "execution_model": simulator.config.execution_model,
            "ansible_version": simulator.config.ansible_version,
            "available_endpoints": simulator.config.available_endpoints,
        }

        # Should serialize without error
        json_str = json.dumps(config_dict)
        assert isinstance(json_str, str)

    def test_migration_results_structure(self) -> None:
        """Test that migration results have expected structure."""
        simulator = MigrationSimulator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        results = simulator.run_migration()

        # Check expected keys
        assert "chef_nodes_queried" in results
        assert "inventory_created" in results
        assert "hosts_created" in results
        assert "execution_environment_created" in results
        assert "job_template_created" in results
        assert "api_calls_made" in results

        # Check expected types
        assert isinstance(results["chef_nodes_queried"], int)
        assert isinstance(results["inventory_created"], bool)
        assert isinstance(results["hosts_created"], int)
        assert isinstance(results["api_calls_made"], list)
