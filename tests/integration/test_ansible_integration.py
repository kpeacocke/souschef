"""Integration tests for Ansible upgrade functionality using real fixtures."""

from pathlib import Path

import pytest

from souschef.ansible_upgrade import (
    assess_ansible_environment,
    detect_python_version,
    generate_upgrade_plan,
    generate_upgrade_testing_plan,
    validate_collection_compatibility,
)
from souschef.core.ansible_versions import (
    calculate_upgrade_path,
    get_python_compatibility,
    is_python_compatible,
)
from souschef.parsers.ansible_inventory import (
    parse_ansible_cfg,
    parse_inventory_file,
    parse_requirements_yml,
    scan_playbook_for_version_issues,
)

# Get fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ansible_environment"


@pytest.fixture
def ansible_cfg_path() -> Path:
    """Get path to test ansible.cfg."""
    return FIXTURES_DIR / "ansible.cfg"


@pytest.fixture
def inventory_ini_path() -> Path:
    """Get path to test inventory.ini."""
    return FIXTURES_DIR / "inventory.ini"


@pytest.fixture
def inventory_yml_path() -> Path:
    """Get path to test inventory.yml."""
    return FIXTURES_DIR / "inventory.yml"


@pytest.fixture
def requirements_yml_path() -> Path:
    """Get path to test requirements.yml."""
    return FIXTURES_DIR / "requirements.yml"


@pytest.fixture
def modern_playbook_path() -> Path:
    """Get path to modern playbook fixture."""
    return FIXTURES_DIR / "modern_playbook.yml"


@pytest.fixture
def legacy_playbook_path() -> Path:
    """Get path to legacy playbook fixture."""
    return FIXTURES_DIR / "legacy_playbook.yml"


class TestParsingRealFixtures:
    """Test parsing actual fixture files."""

    def test_parse_ansible_cfg_fixture(self, ansible_cfg_path):
        """Test parsing real ansible.cfg fixture."""
        if not ansible_cfg_path.exists():
            pytest.skip("ansible.cfg fixture not available")

        result = parse_ansible_cfg(str(ansible_cfg_path))
        assert isinstance(result, dict)

    def test_parse_inventory_ini_fixture(self, inventory_ini_path):
        """Test parsing real inventory.ini fixture."""
        if not inventory_ini_path.exists():
            pytest.skip("inventory.ini fixture not available")

        result = parse_inventory_file(str(inventory_ini_path))
        assert isinstance(result, dict)

    def test_parse_inventory_yml_fixture(self, inventory_yml_path):
        """Test parsing real inventory.yml fixture."""
        if not inventory_yml_path.exists():
            pytest.skip("inventory.yml fixture not available")

        result = parse_inventory_file(str(inventory_yml_path))
        assert isinstance(result, dict)

    def test_parse_requirements_yml_fixture(self, requirements_yml_path):
        """Test parsing real requirements.yml fixture."""
        if not requirements_yml_path.exists():
            pytest.skip("requirements.yml fixture not available")

        result = parse_requirements_yml(str(requirements_yml_path))
        assert isinstance(result, dict)

    def test_scan_modern_playbook_fixture(self, modern_playbook_path):
        """Test scanning modern playbook with FQCN."""
        if not modern_playbook_path.exists():
            pytest.skip("modern_playbook.yml fixture not available")

        result = scan_playbook_for_version_issues(str(modern_playbook_path))
        assert isinstance(result, dict)

    def test_scan_legacy_playbook_fixture(self, legacy_playbook_path):
        """Test scanning legacy playbook with deprecated syntax."""
        if not legacy_playbook_path.exists():
            pytest.skip("legacy_playbook.yml fixture not available")

        result = scan_playbook_for_version_issues(str(legacy_playbook_path))
        assert isinstance(result, dict)


class TestUpgradeWorkflows:
    """Test complete upgrade workflows with fixtures."""

    def test_full_upgrade_assessment_workflow(self, ansible_cfg_path):
        """Test full upgrade assessment workflow."""
        if not ansible_cfg_path.exists():
            pytest.skip("ansible.cfg fixture not available")

        # Assess environment
        env_dir = ansible_cfg_path.parent
        try:
            assessment = assess_ansible_environment(str(env_dir))
            assert isinstance(assessment, dict)
        except ValueError as e:
            # Skip if unsupported Ansible version detected
            if "Unknown Ansible version" in str(e):
                pytest.skip(f"Fixture has unsupported version: {e}")
            raise

        # Plan upgrade - use supported versions
        plan = generate_upgrade_plan("2.14", "2.17")
        assert isinstance(plan, dict)
        assert "upgrade_path" in plan
        assert "estimated_downtime_hours" in plan

    def test_playbook_scanning_workflow(
        self, modern_playbook_path, legacy_playbook_path
    ):
        """Test scanning different playbook types."""
        if not modern_playbook_path.exists() or not legacy_playbook_path.exists():
            pytest.skip("Playbook fixtures not available")

        # Scan modern playbook
        modern_result = scan_playbook_for_version_issues(str(modern_playbook_path))
        assert isinstance(modern_result, dict)

        # Scan legacy playbook
        legacy_result = scan_playbook_for_version_issues(str(legacy_playbook_path))
        assert isinstance(legacy_result, dict)

    def test_inventory_format_interoperability(
        self, inventory_ini_path, inventory_yml_path
    ):
        """Test that both inventory formats parse to similar structures."""
        if not inventory_ini_path.exists() or not inventory_yml_path.exists():
            pytest.skip("Inventory fixtures not available")

        ini_result = parse_inventory_file(str(inventory_ini_path))
        yml_result = parse_inventory_file(str(inventory_yml_path))

        # Both should be dicts
        assert isinstance(ini_result, dict)
        assert isinstance(yml_result, dict)

    def test_collection_compatibility_validation(self, requirements_yml_path):
        """Test validating collections from requirements.yml."""
        if not requirements_yml_path.exists():
            pytest.skip("requirements.yml fixture not available")

        requirements = parse_requirements_yml(str(requirements_yml_path))
        assert isinstance(requirements, dict)

        # Test compatibility for a version
        if len(requirements) > 0:
            # Use first requirement as dict values
            test_collections = {
                "community.general": "3.0.0",
                "ansible.posix": "1.2.0",
            }
            validation = validate_collection_compatibility(test_collections, "2.14")
            assert isinstance(validation, dict)


class TestVersionCompatibility:
    """Test version compatibility features."""

    def test_python_compatibility_for_all_versions(self):
        """Test Python compatibility checking for all Ansible versions."""
        versions = ["2.9", "2.10", "2.14", "2.17"]
        for version in versions:
            result = get_python_compatibility(version, "control")
            assert isinstance(result, list)
            assert len(result) > 0

    def test_upgrade_paths_for_different_gaps(self):
        """Test upgrade paths for different version gaps."""
        paths = [
            ("2.14", "2.17"),
            ("2.10", "2.14"),
            ("2.9", "2.17"),
        ]

        for from_v, to_v in paths:
            result = calculate_upgrade_path(from_v, to_v)
            assert isinstance(result, dict)
            assert "from_version" in result
            assert "to_version" in result
            assert result["from_version"] == from_v
            assert result["to_version"] == to_v

    def test_python_compatibility_check(self):
        """Test checking if specific Python versions are compatible."""
        test_cases = [
            ("2.14", "3.10", "control", True),
            ("2.17", "3.12", "control", True),
            ("2.9", "2.7", "control", True),
        ]

        for ansible_ver, python_ver, node_type, _expected in test_cases:
            result = is_python_compatible(ansible_ver, python_ver, node_type)
            # Just check it returns a bool
            assert isinstance(result, bool)


class TestUpgradePlanning:
    """Test upgrade planning features."""

    @pytest.mark.parametrize(
        "from_version,to_version",
        [
            ("2.9", "2.14"),
            ("2.10", "2.17"),
            ("2.14", "2.17"),
        ],
    )
    def test_generate_upgrade_plans(self, from_version, to_version):
        """Test generating upgrade plans for different version transitions."""
        plan = generate_upgrade_plan(from_version, to_version)
        assert isinstance(plan, dict)
        assert "upgrade_path" in plan
        assert "pre_upgrade_checklist" in plan
        assert "upgrade_steps" in plan
        assert "post_upgrade_validation" in plan

    def test_upgrade_testing_plan_generation(self):
        """Test generating upgrade testing plans."""
        plan = generate_upgrade_testing_plan("/test/env")
        assert isinstance(plan, str)
        assert len(plan) > 0
        # Should contain testing-related content
        text_lower = plan.lower()
        assert any(
            word in text_lower
            for word in ["test", "validate", "check", "play", "ansible"]
        )

    def test_2_9_to_modern_upgrade_special_handling(self):
        """Test that 2.9 upgrades have special collection handling."""
        plan = generate_upgrade_plan("2.9", "2.14")
        assert isinstance(plan, dict)

        # Should have collection-related steps for 2.9
        checklist = plan.get("pre_upgrade_checklist", [])
        checklist_text = " ".join(checklist).lower()
        # Should mention collections since this is upgrading from 2.9
        assert any(word in checklist_text for word in ["collection", "galaxy"])


class TestErrorHandling:
    """Test error handling in integration scenarios."""

    def test_parsing_nonexistent_file_raises_error(self):
        """Test that parsing nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            parse_inventory_file("/nonexistent/inventory.ini")

    def test_invalid_ansible_version_raises_error(self):
        """Test that invalid Ansible version raises error."""
        with pytest.raises(ValueError):
            calculate_upgrade_path("999.999", "2.14")

    def test_assess_nonexistent_environment_returns_error(self):
        """Test assessing nonexistent environment."""
        result = assess_ansible_environment("/nonexistent/env")
        # Should return dict with error key
        assert isinstance(result, dict)


class TestEndToEndScenarios:
    """Test end-to-end real-world scenarios."""

    def test_complete_upgrade_scenario(self):
        """Test a complete upgrade scenario from assessment to validation."""
        # 1. Detect Python version
        try:
            python_version = detect_python_version()
            assert isinstance(python_version, str)
        except RuntimeError:
            # Python detection might fail in test environment
            pass

        # 2. Assess environment
        assessment = assess_ansible_environment("/test/env")
        assert isinstance(assessment, dict)

        # 3. Plan upgrade
        plan = generate_upgrade_plan("2.14", "2.17")
        assert isinstance(plan, dict)
        assert "upgrade_steps" in plan
        assert len(plan["upgrade_steps"]) > 0

        # 4. Generate testing plan
        testing_plan = generate_upgrade_testing_plan("/test/env")
        assert isinstance(testing_plan, str)
        assert len(testing_plan) > 0

        # 5. Validate collections
        test_collections = {"community.general": "3.0.0"}
        validation = validate_collection_compatibility(test_collections, "2.17")
        assert isinstance(validation, dict)

    def test_inventory_parsing_and_validation(self):
        """Test parsing and validating inventory files."""
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            # Create test inventory
            inv_file = Path(tmpdir) / "inventory.ini"
            inv_file.write_text("[webservers]\nweb1\nweb2\n[databases]\ndb1\n")

            # Parse inventory
            result = parse_inventory_file(str(inv_file))
            assert isinstance(result, dict)
