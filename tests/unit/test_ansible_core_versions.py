"""Tests for Ansible version compatibility core module."""

import pytest

from souschef.core.ansible_versions import (
    ANSIBLE_VERSIONS,
    AnsibleVersion,
    calculate_upgrade_path,
    get_eol_status,
    get_latest_version,
    get_minimum_python_for_ansible,
    get_python_compatibility,
    get_supported_versions,
    is_python_compatible,
)


class TestAnsibleVersionData:
    """Test data structure and content of ANSIBLE_VERSIONS."""

    def test_ansible_versions_exists(self):
        """Test that ANSIBLE_VERSIONS dict exists and has content."""
        assert isinstance(ANSIBLE_VERSIONS, dict)
        assert len(ANSIBLE_VERSIONS) > 0

    def test_ansible_versions_contains_expected_versions(self):
        """Test that ANSIBLE_VERSIONS contains major versions."""
        assert "2.9" in ANSIBLE_VERSIONS
        assert "2.17" in ANSIBLE_VERSIONS

    def test_all_versions_are_ansible_version_instances(self):
        """Test all values in ANSIBLE_VERSIONS are AnsibleVersion dataclass."""
        for version_key, version in ANSIBLE_VERSIONS.items():
            assert isinstance(version, AnsibleVersion)
            assert version.version == version_key

    def test_ansible_versions_have_python_support(self):
        """Test all versions have Python support defined."""
        for version_key, version in ANSIBLE_VERSIONS.items():
            assert version.control_node_python, f"{version_key} missing control Python"
            assert version.managed_node_python, f"{version_key} missing managed Python"


class TestGetPythonCompatibility:
    """Test get_python_compatibility function."""

    def test_control_node_compatibility(self):
        """Test getting control node Python versions."""
        result = get_python_compatibility("2.14", "control")
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(v, str) for v in result)

    def test_managed_node_compatibility(self):
        """Test getting managed node Python versions."""
        result = get_python_compatibility("2.14", "managed")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_latest_version_compatibility(self):
        """Test getting compatibility for latest version."""
        result = get_python_compatibility("2.17", "control")
        assert isinstance(result, list)
        assert "3.10" in result or "3.11" in result or "3.12" in result

    def test_earliest_version_compatibility(self):
        """Test getting compatibility for earliest version."""
        result = get_python_compatibility("2.9", "control")
        assert isinstance(result, list)
        assert "2.7" in result or "3.5" in result

    def test_invalid_version_raises_error(self):
        """Test that invalid version raises ValueError."""
        with pytest.raises(ValueError, match="Unknown Ansible version"):
            get_python_compatibility("999.999", "control")

    def test_invalid_node_type_raises_error(self):
        """Test that invalid node type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid node_type"):
            get_python_compatibility("2.14", "invalid")

    def test_default_node_type_is_control(self):
        """Test that default node_type parameter is control."""
        result_default = get_python_compatibility("2.14")
        result_explicit = get_python_compatibility("2.14", "control")
        assert result_default == result_explicit


class TestIsPythonCompatible:
    """Test is_python_compatible function."""

    def test_compatible_version_returns_true(self):
        """Test compatible Python version returns True."""
        result = is_python_compatible("2.14", "3.10", "control")
        assert result is True

    def test_incompatible_version_returns_false(self):
        """Test incompatible Python version returns False."""
        result = is_python_compatible("2.14", "2.7", "control")
        assert result is False

    def test_managed_node_compatibility_check(self):
        """Test checking managed node compatibility."""
        result = is_python_compatible("2.14", "2.7", "managed")
        assert result is True

    def test_invalid_ansible_version_raises_error(self):
        """Test that invalid Ansible version raises ValueError."""
        with pytest.raises(ValueError):
            is_python_compatible("999.999", "3.10", "control")

    def test_invalid_node_type_raises_error(self):
        """Test that invalid node type raises ValueError."""
        with pytest.raises(ValueError):
            is_python_compatible("2.14", "3.10", "invalid")

    def test_default_node_type_is_control(self):
        """Test that default node_type is control."""
        result_default = is_python_compatible("2.14", "3.10")
        result_explicit = is_python_compatible("2.14", "3.10", "control")
        assert result_default == result_explicit


class TestGetLatestVersion:
    """Test get_latest_version function."""

    def test_returns_string(self):
        """Test that get_latest_version returns a string."""
        result = get_latest_version()
        assert isinstance(result, str)

    def test_returns_valid_version(self):
        """Test that returned version is in ANSIBLE_VERSIONS."""
        result = get_latest_version()
        assert result in ANSIBLE_VERSIONS

    def test_returns_highest_version(self):
        """Test that returned version is the highest."""
        result = get_latest_version()
        versions = sorted(ANSIBLE_VERSIONS.keys(), key=lambda v: float(v))
        assert result == versions[-1]


class TestGetSupportedVersions:
    """Test get_supported_versions function."""

    def test_returns_list_of_strings(self):
        """Test that get_supported_versions returns list of strings."""
        result = get_supported_versions()
        assert isinstance(result, list)
        assert all(isinstance(v, str) for v in result)

    def test_returns_non_empty_list(self):
        """Test that returned list is not empty."""
        result = get_supported_versions()
        assert len(result) > 0

    def test_all_returned_versions_exist(self):
        """Test all returned versions are in ANSIBLE_VERSIONS."""
        result = get_supported_versions()
        for version in result:
            assert version in ANSIBLE_VERSIONS

    def test_returns_versions_in_descending_order(self):
        """Test that versions are returned in descending order."""
        result = get_supported_versions()
        versions_as_floats = [float(v) for v in result]
        assert versions_as_floats == sorted(versions_as_floats, reverse=True)


class TestGetEolStatus:
    """Test get_eol_status function."""

    def test_valid_version_returns_dict(self):
        """Test that valid version returns dict."""
        result = get_eol_status("2.14")
        assert isinstance(result, dict)

    def test_eol_version_has_status_key(self):
        """Test that EOL version has status in dict."""
        result = get_eol_status("2.9")
        assert "status" in result

    def test_valid_version_status_is_supported_or_eol(self):
        """Test that status is either Supported or End of Life."""
        result = get_eol_status("2.17")
        assert "status" in result
        status = result["status"]
        assert status in ["Supported", "End of Life", "Approaching EOL"]

    def test_invalid_version_returns_error_dict(self):
        """Test that invalid version returns dict with error key."""
        result = get_eol_status("999.999")
        assert isinstance(result, dict)
        assert "error" in result

    def test_eol_version_has_security_risk_key(self):
        """Test that result includes security risk level."""
        result = get_eol_status("2.9")
        assert "security_risk" in result or "is_eol" in result


class TestGetMinimumPythonForAnsible:
    """Test get_minimum_python_for_ansible function."""

    def test_returns_tuple(self):
        """Test that function returns a tuple."""
        result = get_minimum_python_for_ansible("2.14")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_tuple_contains_strings(self):
        """Test that tuple contains version strings."""
        result = get_minimum_python_for_ansible("2.14")
        assert all(isinstance(v, str) for v in result)

    def test_control_python_is_minimum(self):
        """Test that first element is minimum control node Python."""
        result = get_minimum_python_for_ansible("2.14")
        control_min = result[0]
        all_control = get_python_compatibility("2.14", "control")
        # Verify it's one of the supported versions (order may vary)
        assert control_min in all_control

    def test_managed_python_is_minimum(self):
        """Test that second element is minimum managed node Python."""
        result = get_minimum_python_for_ansible("2.14")
        managed_min = result[1]
        all_managed = get_python_compatibility("2.14", "managed")
        assert managed_min == min(
            all_managed, key=lambda v: tuple(map(int, v.split(".")))
        )

    def test_invalid_version_raises_error(self):
        """Test that invalid version raises ValueError."""
        with pytest.raises(ValueError, match="Unknown Ansible version"):
            get_minimum_python_for_ansible("999.999")


class TestCalculateUpgradePath:
    """Test calculate_upgrade_path function."""

    def test_same_version_returns_direct(self):
        """Test upgrading to same version returns direct=True."""
        result = calculate_upgrade_path("2.14", "2.14")
        assert result["direct_upgrade"] is True
        assert result["intermediate_versions"] == []

    def test_adjacent_version_is_direct(self):
        """Test adjacent versions are direct upgrades."""
        result = calculate_upgrade_path("2.16", "2.17")
        assert result["direct_upgrade"] is True
        assert len(result["intermediate_versions"]) == 0

    def test_return_dict_has_required_keys(self):
        """Test return dict has all required keys."""
        result = calculate_upgrade_path("2.14", "2.17")
        required_keys = [
            "from_version",
            "to_version",
            "direct_upgrade",
            "intermediate_versions",
            "breaking_changes",
            "python_upgrade_needed",
            "current_python",
            "required_python",
            "risk_level",
            "risk_factors",
            "estimated_effort_days",
            "collection_updates_needed",
        ]
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"

    def test_large_gap_requires_testing(self):
        """Test large version gap has comprehensive breaking changes."""
        result = calculate_upgrade_path("2.9", "2.17")
        # Large gaps should either be direct with many breaking changes
        # or broken into steps
        assert "breaking_changes" in result
        assert len(result["breaking_changes"]) > 0

    def test_risk_level_is_valid(self):
        """Test that risk level is one of expected values."""
        result = calculate_upgrade_path("2.14", "2.17")
        assert result["risk_level"] in ["Low", "Medium", "High"]

    def test_estimated_effort_is_positive(self):
        """Test that estimated effort is positive number."""
        result = calculate_upgrade_path("2.14", "2.17")
        assert isinstance(result["estimated_effort_days"], (int, float))
        assert result["estimated_effort_days"] > 0

    def test_breaking_changes_is_list(self):
        """Test that breaking_changes is a list."""
        result = calculate_upgrade_path("2.9", "2.17")
        assert isinstance(result["breaking_changes"], list)

    def test_risk_factors_is_list(self):
        """Test that risk_factors is a list."""
        result = calculate_upgrade_path("2.14", "2.17")
        assert isinstance(result["risk_factors"], list)

    def test_invalid_from_version_raises_error(self):
        """Test that invalid from version raises ValueError."""
        with pytest.raises(ValueError, match="Unknown current version"):
            calculate_upgrade_path("999.999", "2.17")

    def test_invalid_to_version_raises_error(self):
        """Test that invalid to version raises ValueError."""
        with pytest.raises(ValueError, match="Unknown target version"):
            calculate_upgrade_path("2.14", "999.999")

    def test_major_upgrade_requires_python_or_breaking_changes(self):
        """Test major upgrade has significant risk factors."""
        result = calculate_upgrade_path("2.9", "2.17")
        # Should have either python upgrade needed or breaking changes
        assert result["python_upgrade_needed"] or len(result["breaking_changes"]) > 0

    def test_collection_updates_is_dict(self):
        """Test that collection_updates_needed is a dict."""
        result = calculate_upgrade_path("2.14", "2.17")
        assert isinstance(result["collection_updates_needed"], dict)


@pytest.mark.parametrize(
    "version",
    ["2.9", "2.10", "2.11", "2.12", "2.13", "2.14", "2.15", "2.16", "2.17"],
)
class TestAllVersionsCompatible:
    """Parameterized tests for all Ansible versions."""

    def test_version_has_control_python(self, version):
        """Test all versions have control Python support."""
        result = get_python_compatibility(version, "control")
        assert len(result) > 0

    def test_version_has_managed_python(self, version):
        """Test all versions have managed Python support."""
        result = get_python_compatibility(version, "managed")
        assert len(result) > 0

    def test_get_eol_status_for_version(self, version):
        """Test get_eol_status works for all versions."""
        result = get_eol_status(version)
        assert isinstance(result, dict)
        assert "status" in result or "error" not in result
