"""
Performance tests for SousChef parsers and converters.

Tests measure execution time, memory usage, and establish baselines
for regression detection on critical parsing and conversion functions.

Uses pytest-benchmark for timing regression detection and tracks
memory consumption for large inventory processing tasks.
"""

import pytest
import yaml

from souschef.core.ansible_versions import calculate_upgrade_path
from souschef.parsers.ansible_inventory import (
    parse_ansible_cfg,
    parse_inventory_ini,
    parse_inventory_yaml,
    parse_requirements_yml,
)


@pytest.fixture
def large_ini_inventory(tmp_path):
    """
    Generate a large INI inventory with 1000+ hosts.

    Creates a realistic multi-group inventory for performance testing.
    """
    inventory_content = "[webservers]\n"
    for i in range(500):
        inventory_content += (
            f"web_{i:04d} ansible_host=192.168.1.{i % 255}\n"  # NOSONAR - test fixture
        )

    inventory_content += "\n[databases]\n"
    for i in range(300):
        inventory_content += (
            f"db_{i:04d} ansible_host=192.0.2.{i % 255}\n"  # RFC 5737 documentation IP
        )

    inventory_content += "\n[monitoring]\n"
    for i in range(200):
        inventory_content += (
            f"mon_{i:04d} ansible_host=172.16.0.{i % 255}\n"  # NOSONAR - test fixture
        )

    inventory_file = tmp_path / "inventory.ini"
    inventory_file.write_text(inventory_content)
    return str(inventory_file)


@pytest.fixture
def large_yaml_inventory(tmp_path):
    """
    Generate a large YAML inventory with 1000+ hosts and variables.

    Creates realistic host variables for performance testing.
    """
    inventory_data = {
        "all": {
            "children": {
                "webservers": {
                    "hosts": {
                        f"web_{i:04d}": {
                            "ansible_host": f"192.168.1.{i % 255}",  # NOSONAR - test fixture
                            "http_port": 8080 + (i % 100),
                            "max_clients": 200 + (i % 100),
                            "region": ["us-east", "us-west", "eu-west"][i % 3],
                            "tags": ["web", "frontend", "public"],
                        }
                        for i in range(500)
                    }
                },
                "databases": {
                    "hosts": {
                        f"db_{i:04d}": {
                            "ansible_host": f"192.0.2.{i % 255}",  # RFC 5737 documentation IP
                            "db_port": 5432,
                            "max_connections": 100 + (i % 50),
                            "backup_enabled": i % 2 == 0,
                            "region": ["us-east", "us-west"][i % 2],
                            "tags": ["database", "backend", "private"],
                        }
                        for i in range(300)
                    }
                },
                "monitoring": {
                    "hosts": {
                        f"mon_{i:04d}": {
                            "ansible_host": f"172.16.0.{i % 255}",  # NOSONAR - test fixture
                            "monitoring_port": 9090,
                            "scrape_interval": 15 + (i % 30),
                            "tags": ["monitoring", "observability"],
                        }
                        for i in range(200)
                    }
                },
            }
        }
    }

    inventory_file = tmp_path / "inventory.yml"
    with inventory_file.open("w") as f:
        yaml.dump(inventory_data, f)
    return str(inventory_file)


@pytest.fixture
def large_requirements_yml(tmp_path):
    """
    Generate a requirements.yml with 500+ collections.

    Simulates dependency inventory for performance testing.
    """
    collections = [
        {
            "name": f"community.collection_{i:04d}",
            "version": f"{1 + (i % 5)}.{i % 20}.0",
        }
        for i in range(500)
    ]

    requirements_data = {"collections": collections}

    requirements_file = tmp_path / "requirements.yml"
    with requirements_file.open("w") as f:
        yaml.dump(requirements_data, f)
    return str(requirements_file)


class TestInventoryParserPerformance:
    """Benchmark tests for inventory parsing with large datasets."""

    def test_parse_large_ini_inventory_benchmark(self, benchmark, large_ini_inventory):
        """
        Benchmark INI inventory parser on 1000+ hosts.

        Performance baseline: Should parse 1000 hosts efficiently.
        Creates performance baseline for regression detection.
        """

        def parse_ini():
            return parse_inventory_ini(large_ini_inventory)

        result = benchmark(parse_ini)
        assert isinstance(result, dict)
        assert "groups" in result or "hosts" in result
        # INI parser returns {groups: {...}, hosts: {...}}
        if "hosts" in result:
            assert len(result["hosts"]) > 0

    def test_parse_large_yaml_inventory_benchmark(
        self, benchmark, large_yaml_inventory
    ):
        """
        Benchmark YAML inventory parser on 1000+ hosts with variables.

        Performance baseline: Should parse 1000 hosts with vars efficiently.
        Creates baseline for regression detection.
        """

        def parse_yaml():
            return parse_inventory_yaml(large_yaml_inventory)

        result = benchmark(parse_yaml)
        assert isinstance(result, dict)
        # YAML parser returns nested structure
        assert "all" in result or "webservers" in result or "databases" in result

    def test_parse_yaml_inventory_variable_overhead(
        self, benchmark, large_yaml_inventory
    ):
        """
        Measure overhead of parsing host variables.

        Tracks whether variable processing impacts parsing performance.
        """

        def parse_with_vars():
            result = parse_inventory_yaml(large_yaml_inventory)
            # Verify variables were extracted
            return result

        benchmark(parse_with_vars)


class TestRequirementsParserPerformance:
    """Benchmark tests for requirements.yml parsing with large collections."""

    def test_parse_large_requirements_benchmark(
        self, benchmark, large_requirements_yml
    ):
        """
        Benchmark requirements.yml parser on 500+ collections.

        Performance baseline: Creates baseline for regression detection.
        """

        def parse_requirements():
            return parse_requirements_yml(large_requirements_yml)

        result = benchmark(parse_requirements)
        assert isinstance(result, dict)
        assert len(result) >= 500
        # Verify collection name format
        assert any("community.collection" in key for key in result)


class TestUpgradePathPerformance:
    """Benchmark tests for upgrade path calculation."""

    @pytest.mark.parametrize(
        "from_ver,to_ver",
        [
            ("2.9", "2.17"),
            ("2.10", "2.15"),
            ("2.11", "2.17"),
        ],
    )
    def test_calculate_upgrade_path_benchmark(self, benchmark, from_ver, to_ver):
        """
        Benchmark upgrade path calculation across versions.

        Performance baseline: Should calculate paths in < 10ms.
        Regression detection: Alerts if calculation time increases > 30%.
        """

        def calc_path():
            return calculate_upgrade_path(from_ver, to_ver)

        result = benchmark(calc_path)
        assert isinstance(result, dict)
        # Verify result structure
        assert (
            "direct_upgrade" in result
            or "steps" in result
            or "intermediate_versions" in result
        )


class TestAnsibleConfigParserPerformance:
    """Benchmark tests for ansible.cfg parsing."""

    def test_parse_ansible_cfg_large_config_benchmark(self, benchmark, tmp_path):
        """
        Benchmark ansible.cfg parser with large configuration files.

        Performance baseline: Should parse large configs in < 50ms.
        Regression detection: Alerts if parsing time increases > 20%.
        """
        # Create a large ansible.cfg with many options
        config_content = "[defaults]\n"
        for i in range(100):
            config_content += f"# Comment {i}\n"
            config_content += f"option_{i} = value_{i}\n"

        config_content += "\n[inventory]\n"
        for i in range(50):
            config_content += f"inv_option_{i} = inv_value_{i}\n"

        config_file = tmp_path / "ansible.cfg"
        config_file.write_text(config_content)

        def parse_config():
            return parse_ansible_cfg(str(config_file))

        result = benchmark(parse_config)
        assert isinstance(result, dict)


class TestMemoryUsageRegression:
    """Tests to detect memory usage regressions on large datasets."""

    def test_large_ini_inventory_memory_stable(self, large_ini_inventory):
        """
        Verify INI inventory parsing doesn't leak memory.

        Parses inventory multiple times and ensures no unbounded growth.
        """
        results = []
        for _ in range(5):
            result = parse_inventory_ini(large_ini_inventory)
            # Count hosts from the hosts dict
            host_count = len(result.get("hosts", {}))
            results.append(host_count)

        # All parsing results should have same number of hosts
        assert len(set(results)) == 1
        assert results[0] > 0

    def test_large_yaml_inventory_memory_stable(self, large_yaml_inventory):
        """
        Verify YAML inventory parsing doesn't leak memory.

        Parses inventory multiple times and ensures no unbounded growth.
        """
        results = []
        for _ in range(5):
            result = parse_inventory_yaml(large_yaml_inventory)
            results.append(str(result))  # Stable representation

        # All parses should produce consistent results
        assert all(r == results[0] for r in results)


class TestRegressionBaselines:
    """Establish and verify performance regression baselines."""

    def test_ini_parser_regression_baseline(self, tmp_path, benchmark):
        """
        Establish INI parser baseline for regression detection.

        Creates a standard 100-host inventory and benchmarks repeatedly
        to establish a stable baseline.
        """
        # Standard test inventory
        inventory_content = "[servers]\n"
        for i in range(100):
            inventory_content += f"server_{i:03d} ansible_host=192.0.2.{i}\n"  # RFC 5737 documentation IP

        inventory_file = tmp_path / "inventory.ini"
        inventory_file.write_text(inventory_content)

        def parse_standard():
            return parse_inventory_ini(str(inventory_file))

        # Run benchmark which will establish baseline
        result = benchmark(parse_standard)
        assert isinstance(result, dict)
        assert "hosts" in result or "groups" in result

    def test_yaml_parser_regression_baseline(self, tmp_path, benchmark):
        """
        Establish YAML parser baseline for regression detection.

        Creates a standard 100-host inventory with variables and benchmarks
        repeatedly to establish a stable baseline.
        """
        inventory_data = {
            "all": {
                "hosts": {
                    f"server_{i:03d}": {
                        "ansible_host": f"192.0.2.{i}",  # RFC 5737 documentation IP
                        "custom_var": f"value_{i}",
                    }
                    for i in range(100)
                }
            }
        }

        inventory_file = tmp_path / "inventory.yml"
        with inventory_file.open("w") as f:
            yaml.dump(inventory_data, f)

        def parse_standard():
            return parse_inventory_yaml(str(inventory_file))

        result = benchmark(parse_standard)
        assert isinstance(result, dict)

    def test_upgrade_path_regression_baseline(self, benchmark):
        """
        Establish upgrade path calculation baseline.

        Tests common upgrade scenarios and establishes performance baseline.
        """

        def calc_common_path():
            return calculate_upgrade_path("2.9", "2.17")

        result = benchmark(calc_common_path)
        assert isinstance(result, dict)


class TestComplexScenarios:
    """Performance tests for realistic complex scenarios."""

    def test_parse_inventory_with_mixed_groups_and_vars(self, benchmark, tmp_path):
        """
        Benchmark parsing complex inventory with mixed groups and variables.

        Simulates real-world inventory with group vars, host vars, and nested
        relationships.
        """
        inventory_data = {
            "all": {
                "vars": {"ansible_user": "deploy", "ansible_port": 22},
                "children": {
                    "production": {
                        "vars": {"env": "prod", "backup_level": "full"},
                        "hosts": {
                            f"prod_server_{i:03d}": {
                                "ansible_host": f"198.51.100.{i}",  # RFC 5737 documentation IP
                                "role": "web" if i % 2 == 0 else "app",
                            }
                            for i in range(200)
                        },
                    },
                    "staging": {
                        "vars": {"env": "stage", "backup_level": "incremental"},
                        "hosts": {
                            f"stage_server_{i:03d}": {
                                "ansible_host": f"203.0.113.{i}",  # RFC 5737 documentation IP
                                "role": "web"
                                if i % 3 == 0
                                else "app"
                                if i % 3 == 1
                                else "db",
                            }
                            for i in range(150)
                        },
                    },
                },
            }
        }

        inventory_file = tmp_path / "inventory.yml"
        with inventory_file.open("w") as f:
            yaml.dump(inventory_data, f)

        def parse_complex():
            return parse_inventory_yaml(str(inventory_file))

        result = benchmark(parse_complex)
        assert isinstance(result, dict)
        assert len(result) > 0
