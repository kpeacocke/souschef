"""Tests for migration_simulation module covering all validation paths."""

import pytest

from souschef.migration_simulation import (
    CHEF_VERSIONS,
    PLATFORM_VERSIONS,
    MigrationSimulationConfig,
    create_simulation_config,
    get_all_version_combinations,
    validate_version_combination,
)


class TestMigrationSimulationConfigValidation:
    """Test validation in MigrationSimulationConfig."""

    def test_invalid_chef_version(self) -> None:
        """Test invalid Chef version raises ValueError (line 151-154)."""
        with pytest.raises(ValueError) as exc_info:
            MigrationSimulationConfig(
                chef_version="99.99.99",
                target_platform="awx",
                target_version="24.6.1",
            )

        assert "Invalid Chef version" in str(exc_info.value)
        assert "99.99.99" in str(exc_info.value)

    def test_invalid_target_platform(self) -> None:
        """Test invalid target platform raises ValueError (line 159)."""
        with pytest.raises(ValueError) as exc_info:
            MigrationSimulationConfig(
                chef_version="15.10.91",
                target_platform="invalid_platform",  # type: ignore[arg-type]
                target_version="1.0.0",
            )

        assert "Invalid target platform" in str(exc_info.value)

    def test_invalid_target_version_for_platform(self) -> None:
        """Test invalid version for platform raises ValueError (line 165)."""
        with pytest.raises(ValueError) as exc_info:
            MigrationSimulationConfig(
                chef_version="15.10.91",
                target_platform="awx",
                target_version="99.99.99",
            )

        assert "Invalid awx version" in str(exc_info.value)
        assert "99.99.99" in str(exc_info.value)

    def test_invalid_auth_protocol_for_chef_version(self) -> None:
        """Test invalid auth protocol for Chef version (line 176)."""
        with pytest.raises(ValueError) as exc_info:
            MigrationSimulationConfig(
                chef_version="15.10.91",
                target_platform="awx",
                target_version="24.6.1",
                chef_auth_protocol="1.0",  # Invalid for Chef 15 (requires 1.3)
            )

        assert "Invalid auth protocol" in str(exc_info.value)
        assert "1.0" in str(exc_info.value)

    def test_default_auth_protocol_set_correctly(self) -> None:
        """Test default auth protocol is set from supported protocols."""
        config = MigrationSimulationConfig(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
            chef_auth_protocol="",  # Empty, should use default
        )

        assert config.chef_auth_protocol == "1.3"

    def test_chef_12_supports_multiple_auth_protocols(self) -> None:
        """Test Chef 12 supports both 1.0 and 1.3 protocols."""
        # Should work with 1.0
        config = MigrationSimulationConfig(
            chef_version="12.19.36",
            target_platform="awx",
            target_version="20.1.0",
            chef_auth_protocol="1.0",
        )
        assert config.chef_auth_protocol == "1.0"

        # Should work with 1.3
        config = MigrationSimulationConfig(
            chef_version="12.19.36",
            target_platform="awx",
            target_version="20.1.0",
            chef_auth_protocol="1.3",
        )
        assert config.chef_auth_protocol == "1.3"

    def test_chef_14_only_supports_1_3(self) -> None:
        """Test Chef 14 only supports 1.3 protocol."""
        config = MigrationSimulationConfig(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="20.1.0",
            chef_auth_protocol="1.3",
        )
        assert config.chef_auth_protocol == "1.3"

        # 1.0 should fail
        with pytest.raises(ValueError) as exc_info:
            MigrationSimulationConfig(
                chef_version="14.15.6",
                target_platform="awx",
                target_version="20.1.0",
                chef_auth_protocol="1.0",
            )
        assert "Invalid auth protocol" in str(exc_info.value)

    def test_aap_forces_content_signing(self) -> None:
        """Test AAP target always sets content_signing=True."""
        config = MigrationSimulationConfig(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
            content_signing=False,  # Explicitly set to False
        )

        assert config.content_signing is True

    def test_non_aap_preserves_content_signing(self) -> None:
        """Test non-AAP targets preserve content_signing value."""
        config = MigrationSimulationConfig(
            chef_version="15.10.91",
            target_platform="awx",
            target_version="24.6.1",
            content_signing=True,
        )

        assert config.content_signing is True

        config = MigrationSimulationConfig(
            chef_version="15.10.91",
            target_platform="awx",
            target_version="24.6.1",
            content_signing=False,
        )

        assert config.content_signing is False


class TestCreateSimulationConfig:
    """Test create_simulation_config factory function."""

    def test_create_valid_config(self) -> None:
        """Test creating valid simulation config."""
        config = create_simulation_config(
            chef_version="15.10.91",
            target_platform="awx",
            target_version="24.6.1",
        )

        assert config.chef_version == "15.10.91"
        assert config.target_platform == "awx"
        assert config.target_version == "24.6.1"

    def test_create_config_with_extra_kwargs(self) -> None:
        """Test creating config with additional options."""
        config = create_simulation_config(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
            execution_environment_id=99,
            inventory_id=42,
            fips_mode=True,
        )

        assert config.execution_environment_id == 99
        assert config.inventory_id == 42
        assert config.fips_mode is True


class TestValidateVersionCombination:
    """Test validate_version_combination helper function."""

    def test_validate_valid_combination(self) -> None:
        """Test validation of valid version combination."""
        result = validate_version_combination(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        assert result["valid"] is True
        assert result["chef_version"] == "15.10.91"
        assert result["target_platform"] == "aap"
        assert result["target_version"] == "2.4.0"

    def test_validate_invalid_chef_version(self) -> None:
        """Test validation fails for invalid Chef version."""
        with pytest.raises(ValueError) as exc_info:
            validate_version_combination(
                chef_version="99.99.99",
                target_platform="awx",
                target_version="24.6.1",
            )

        assert "Invalid Chef version" in str(exc_info.value)

    def test_validate_includes_ansible_version(self) -> None:
        """Test validation result includes required Ansible version."""
        result = validate_version_combination(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="22.0.0",
        )

        assert "ansible_version" in result
        assert result["ansible_version"] == "2.12.0"


class TestMockResponseHeaders:
    """Test get_mock_response_headers method."""

    def test_tower_mock_headers(self) -> None:
        """Test Tower mock response headers."""
        config = MigrationSimulationConfig(
            chef_version="12.19.36",
            target_platform="tower",
            target_version="3.8.5",
        )

        headers = config.get_mock_response_headers()

        assert headers["Content-Type"] == "application/json"
        assert headers["Server"] == "Ansible Tower 3.8.5"
        assert headers["X-Ansible-Cost"] == "5"

    def test_awx_201_mock_headers(self) -> None:
        """Test AWX 20.1 mock response headers."""
        config = MigrationSimulationConfig(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="20.1.0",
        )

        headers = config.get_mock_response_headers()

        assert headers["Content-Type"] == "application/json"
        assert headers["Server"] == "AWX 20.1.0"
        assert headers["X-Ansible-Cost"] == "10"

    def test_awx_2461_mock_headers(self) -> None:
        """Test AWX 24.6.1 mock response headers."""
        config = MigrationSimulationConfig(
            chef_version="15.10.91",
            target_platform="awx",
            target_version="24.6.1",
        )

        headers = config.get_mock_response_headers()

        assert headers["Content-Type"] == "application/json"
        assert headers["Server"] == "AWX 24.6.1"
        assert headers["X-Ansible-Cost"] == "10"

    def test_aap_mock_headers(self) -> None:
        """Test AAP mock response headers."""
        config = MigrationSimulationConfig(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        headers = config.get_mock_response_headers()

        assert headers["Content-Type"] == "application/json"
        assert headers["Server"] == "Ansible Automation Platform 2.4.0"
        assert headers["X-Ansible-Cost"] == "15"


class TestJobTemplateStructure:
    """Test get_job_template_structure method."""

    def test_tower_virtualenv_structure(self) -> None:
        """Test Tower job template uses custom_virtualenv."""
        config = MigrationSimulationConfig(
            chef_version="12.19.36",
            target_platform="tower",
            target_version="3.8.5",
        )

        structure = config.get_job_template_structure()

        assert "custom_virtualenv" in structure
        assert structure["name"] == "placeholder"
        assert structure["job_type"] == "run"

    def test_awx_early_virtualenv_structure(self) -> None:
        """Test AWX 20.x uses custom_virtualenv."""
        config = MigrationSimulationConfig(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="20.1.0",
        )

        structure = config.get_job_template_structure()

        assert "custom_virtualenv" in structure
        assert structure["custom_virtualenv"] == "/var/lib/awx/venv/ansible"

    def test_awx_new_execution_environment_structure(self) -> None:
        """Test AWX 24.6.1 uses execution_environment."""
        config = MigrationSimulationConfig(
            chef_version="15.10.91",
            target_platform="awx",
            target_version="24.6.1",
        )

        structure = config.get_job_template_structure()

        assert "execution_environment" in structure
        assert structure["execution_environment"] == 42

    def test_aap_content_signing_in_structure(self) -> None:
        """Test AAP job template includes content_signing."""
        config = MigrationSimulationConfig(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        structure = config.get_job_template_structure()

        assert "content_signing" in structure
        assert structure["content_signing"] is True

    def test_awx_24_mesh_mode_enabled(self) -> None:
        """Test AWX 24+ includes mesh_mode."""
        config = MigrationSimulationConfig(
            chef_version="15.10.91",
            target_platform="awx",
            target_version="24.6.1",
        )

        structure = config.get_job_template_structure()

        assert "mesh_mode" in structure
        assert structure["mesh_mode"] == "enabled"

    def test_awx_22_no_mesh_mode(self) -> None:
        """Test AWX 22.x does not include mesh_mode."""
        config = MigrationSimulationConfig(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="22.0.0",
        )

        structure = config.get_job_template_structure()

        assert "mesh_mode" not in structure

    def test_extra_vars_included_in_structure(self) -> None:
        """Test extra_vars are included in job template."""
        extra_vars = {"var1": "value1", "var2": "value2"}
        config = MigrationSimulationConfig(
            chef_version="15.10.91",
            target_platform="awx",
            target_version="24.6.1",
            extra_vars=extra_vars,
        )

        structure = config.get_job_template_structure()

        assert structure["extra_vars"] == extra_vars


class TestVersionCombinations:
    """Test get_all_version_combinations function."""

    def test_get_all_combinations(self) -> None:
        """Test getting all valid version combinations."""
        combinations = get_all_version_combinations()

        assert isinstance(combinations, list)
        assert len(combinations) > 0

    def test_all_combinations_have_required_fields(self) -> None:
        """Test all combinations have chef_version, platform, version."""
        combinations = get_all_version_combinations()

        for combo in combinations:
            assert "chef_version" in combo
            assert "target_platform" in combo
            assert "target_version" in combo

    def test_combinations_use_valid_versions(self) -> None:
        """Test combinations only include valid versions."""
        combinations = get_all_version_combinations()

        for combo in combinations:
            assert combo["chef_version"] in CHEF_VERSIONS
            assert combo["target_platform"] in PLATFORM_VERSIONS
            assert (
                combo["target_version"] in PLATFORM_VERSIONS[combo["target_platform"]]
            )

    def test_expected_combination_count(self) -> None:
        """Test expected number of version combinations."""
        combinations = get_all_version_combinations()

        # 3 Chef versions × 4 platforms × various platform versions
        # Tower: 1, AWX: 4, AAP: 1
        expected_count = 3 * (1 + 4 + 1)
        assert len(combinations) == expected_count

    def test_all_combinations_are_valid(self) -> None:
        """Test all combinations can create valid configs."""
        combinations = get_all_version_combinations()

        for combo in combinations:
            config = MigrationSimulationConfig(**combo)  # type: ignore[arg-type]
            assert config.chef_version == combo["chef_version"]
            assert config.target_platform == combo["target_platform"]
            assert config.target_version == combo["target_version"]
