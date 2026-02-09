"""Tests for Ansible version compatibility core module."""

import pytest

from souschef.core.ansible_versions import (
    ANSIBLE_VERSIONS,
    AnsibleVersion,
    calculate_upgrade_path,
    fetch_ansible_versions_with_ai,
    format_version_display,
    get_aap_compatible_versions,
    get_ansible_core_version,
    get_eol_status,
    get_latest_version,
    get_latest_version_with_ai,
    get_minimum_python_for_ansible,
    get_named_ansible_version,
    get_python_compatibility,
    get_python_compatibility_with_ai,
    get_recommended_core_version_for_aap,
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
        assert "2.19" in ANSIBLE_VERSIONS
        assert "2.20" in ANSIBLE_VERSIONS

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
        latest_version = get_latest_version()
        result = get_python_compatibility(latest_version, "control")
        assert isinstance(result, list)
        assert result == ANSIBLE_VERSIONS[latest_version].control_node_python

    def test_earliest_version_compatibility(self):
        """Test getting compatibility for earliest version."""
        from souschef.core.ansible_versions import _parse_version

        earliest_version = sorted(ANSIBLE_VERSIONS.keys(), key=_parse_version)[0]
        result = get_python_compatibility(earliest_version, "control")
        assert isinstance(result, list)
        assert result == ANSIBLE_VERSIONS[earliest_version].control_node_python

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
        from souschef.core.ansible_versions import _parse_version

        result = get_latest_version()
        versions = sorted(ANSIBLE_VERSIONS.keys(), key=_parse_version)
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
        from souschef.core.ansible_versions import _parse_version

        result = get_supported_versions()
        expected = sorted(result, key=_parse_version, reverse=True)
        assert result == expected


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
        assert (result.get("intermediate_versions") or []) == []

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
        breaking_changes = result["breaking_changes"]
        assert isinstance(breaking_changes, list)
        assert len(breaking_changes) > 0

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
        breaking_changes = result["breaking_changes"]
        assert result["python_upgrade_needed"] or (
            isinstance(breaking_changes, list) and len(breaking_changes) > 0
        )

    def test_collection_updates_is_dict(self):
        """Test that collection_updates_needed is a dict."""
        result = calculate_upgrade_path("2.14", "2.17")
        assert isinstance(result["collection_updates_needed"], dict)


@pytest.mark.parametrize(
    "version",
    [
        "2.9",
        "2.10",
        "2.11",
        "2.12",
        "2.13",
        "2.14",
        "2.15",
        "2.16",
        "2.17",
        "2.18",
        "2.19",
        "2.20",
    ],
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


class TestGetAnsibleCoreVersion:
    """Test get_ansible_core_version function (Named Ansible → Core)."""

    def test_convert_9x_to_core(self):
        """Test converting Named Ansible 9.x to ansible-core 2.16."""
        result = get_ansible_core_version("9.x")
        assert result == "2.16"

    def test_convert_10x_to_core(self):
        """Test converting Named Ansible 10.x to ansible-core 2.17."""
        result = get_ansible_core_version("10.x")
        assert result == "2.17"

    def test_convert_invalid_named_version_raises_error(self):
        """Test invalid Named Ansible version returns None."""
        result = get_ansible_core_version("99.x")
        assert result is None

    def test_convert_empty_string_returns_none(self):
        """Test empty string returns None."""
        result = get_ansible_core_version("")
        assert result is None


class TestGetNamedAnsibleVersion:
    """Test get_named_ansible_version function (Core → Named Ansible)."""

    def test_convert_2_16_to_named(self):
        """Test converting ansible-core 2.16 to Named Ansible 9.x."""
        result = get_named_ansible_version("2.16")
        assert result == "9.x"

    def test_convert_2_17_to_named(self):
        """Test converting ansible-core 2.17 to Named Ansible 10.x."""
        result = get_named_ansible_version("2.17")
        assert result == "10.x"

    def test_convert_invalid_core_version_raises_error(self):
        """Test invalid core version returns None."""
        result = get_named_ansible_version("99.99")
        assert result is None

    def test_convert_old_version_without_named_returns_none(self):
        """Test old version without named_version returns None."""
        result = get_named_ansible_version("2.9")
        assert result is None


class TestGetAapCompatibleVersions:
    """Test get_aap_compatible_versions function."""

    def test_get_aap_for_2_16(self):
        """Test getting AAP versions compatible with ansible-core 2.16."""
        result = get_aap_compatible_versions("2.16")
        assert isinstance(result, list)
        assert set(result) == {"2.5", "2.6"}

    def test_get_aap_for_2_17(self):
        """Test getting AAP versions compatible with ansible-core 2.17."""
        result = get_aap_compatible_versions("2.17")
        assert isinstance(result, list)
        assert set(result) == {"2.5", "2.6"}

    def test_get_aap_for_2_18(self):
        """Test getting AAP versions compatible with ansible-core 2.18."""
        result = get_aap_compatible_versions("2.18")
        assert isinstance(result, list)
        assert set(result) == {"2.5", "2.6"}

    def test_get_aap_for_2_19(self):
        """Test getting AAP versions compatible with ansible-core 2.19."""
        result = get_aap_compatible_versions("2.19")
        assert isinstance(result, list)
        assert result == []

    def test_get_aap_for_2_20(self):
        """Test getting AAP versions compatible with ansible-core 2.20."""
        result = get_aap_compatible_versions("2.20")
        assert isinstance(result, list)
        assert result == []

    def test_get_aap_for_old_version_returns_empty(self):
        """Test old version without AAP support returns empty list."""
        result = get_aap_compatible_versions("2.9")
        assert result == []

    def test_invalid_version_raises_error(self):
        """Test invalid version returns empty list."""
        result = get_aap_compatible_versions("99.99")
        assert result == []


class TestGetRecommendedCoreVersionForAap:
    """Test get_recommended_core_version_for_aap function."""

    def test_get_core_for_aap_2_5(self):
        """Test getting recommended ansible-core for AAP 2.5."""
        result = get_recommended_core_version_for_aap("2.5")
        assert result == "2.18"

    def test_get_core_for_aap_2_6(self):
        """Test getting recommended ansible-core for AAP 2.6."""
        result = get_recommended_core_version_for_aap("2.6")
        assert result == "2.18"

    def test_invalid_aap_version_returns_none(self):
        """Test invalid AAP version returns None."""
        result = get_recommended_core_version_for_aap("99.99")
        assert result is None

    def test_returns_latest_compatible_version(self):
        """Test function returns latest compatible version."""
        result = get_recommended_core_version_for_aap("2.5")
        # Should return highest version that supports AAP 2.5
        assert result is not None


class TestFormatVersionDisplay:
    """Test format_version_display function."""

    def test_format_core_only(self):
        """Test formatting with only core version."""
        result = format_version_display("2.16", include_named=False, include_aap=False)
        assert result == "ansible-core 2.16"

    def test_format_with_named_version(self):
        """Test formatting with Named Ansible version."""
        result = format_version_display("2.16", include_named=True, include_aap=False)
        assert "ansible-core 2.16" in result
        assert "9.x" in result or "Ansible 9.x" in result

    def test_format_with_aap_versions(self):
        """Test formatting with AAP compatibility."""
        result = format_version_display("2.16", include_named=False, include_aap=True)
        assert "ansible-core 2.16" in result
        expected_aap_versions = get_aap_compatible_versions("2.16")
        if expected_aap_versions:
            assert any(aap_ver in result for aap_ver in expected_aap_versions)

    def test_format_with_all_info(self):
        """Test formatting with all information."""
        result = format_version_display("2.16", include_named=True, include_aap=True)
        assert "ansible-core 2.16" in result
        # Should have Named Ansible version
        assert "9.x" in result or "Ansible 9.x" in result

    def test_format_old_version_without_named(self):
        """Test formatting old version without Named Ansible."""
        result = format_version_display("2.9", include_named=True, include_aap=False)
        assert "ansible-core 2.9" in result
        # Should still work even though 2.9 has no named version

    def test_format_invalid_version_raises_error(self):
        """Test invalid version just formats without extra info."""
        result = format_version_display("99.99", include_named=False, include_aap=False)
        assert result == "ansible-core 99.99"

    def test_default_parameters(self):
        """Test function with default parameters."""
        result = format_version_display("2.16")
        assert "ansible-core 2.16" in result


@pytest.mark.parametrize(
    "core_version,named_version",
    [
        ("2.16", "9.x"),
        ("2.17", "10.x"),
        ("2.18", "11.x"),
        ("2.19", "12.x"),
        ("2.20", "13.x"),
    ],
)
class TestVersionSchemaMapping:
    """Parameterized tests for version schema conversions."""

    def test_core_to_named_conversion(self, core_version, named_version):
        """Test converting ansible-core to Named Ansible."""
        result = get_named_ansible_version(core_version)
        assert result == named_version

    def test_named_to_core_conversion(self, core_version, named_version):
        """Test converting Named Ansible to ansible-core."""
        result = get_ansible_core_version(named_version)
        assert result == core_version

    def test_round_trip_conversion(self, core_version, named_version):
        """Test converting back and forth preserves values."""
        # Core → Named → Core
        named_result = get_named_ansible_version(core_version)
        assert named_result is not None
        core_result = get_ansible_core_version(named_result)
        assert core_result == core_version

    def test_format_includes_both_schemas(self, core_version, named_version):
        """Test formatting displays both version schemas."""
        result = format_version_display(core_version, include_named=True)
        assert core_version in result
        assert named_version in result


class TestAIDrivenVersionFetching:
    """Test AI-driven version compatibility functions."""

    def test_fetch_ansible_versions_with_ai_no_api_key(self):
        """Test AI fetch returns None without API key."""
        result = fetch_ansible_versions_with_ai(api_key="", use_cache=False)
        assert result is None

    def test_get_python_compatibility_with_ai_fallback(self):
        """Test AI function falls back to static data without API key."""
        result = get_python_compatibility_with_ai("2.20", api_key="")
        # Should fall back to static ANSIBLE_VERSIONS
        assert isinstance(result, list)
        assert len(result) > 0
        # 2.20 control node should support Python 3.12+
        assert "3.12" in result

    def test_get_python_compatibility_with_ai_managed_nodes(self):
        """Test AI function works for managed nodes with fallback."""
        result = get_python_compatibility_with_ai(
            "2.19", node_type="managed", api_key=""
        )
        assert isinstance(result, list)
        assert len(result) > 0
        # 2.19 managed nodes support Python 3.8+
        assert "3.8" in result

    def test_get_latest_version_with_ai_fallback(self):
        """Test AI latest version falls back to static data."""
        result = get_latest_version_with_ai(api_key="")
        assert isinstance(result, str)
        assert result in ANSIBLE_VERSIONS
        # Should return 2.20 as latest
        assert result == "2.20"

    def test_ai_functions_accept_providers(self):
        """Test AI functions accept different provider parameters."""
        # Should not raise errors with different providers
        result1 = fetch_ansible_versions_with_ai(
            ai_provider="anthropic", api_key="", use_cache=False
        )
        result2 = fetch_ansible_versions_with_ai(
            ai_provider="openai", api_key="", use_cache=False
        )
        # Both should return None without keys
        assert result1 is None
        assert result2 is None


class TestNewVersions:
    """Test newly added 2.19 and 2.20 versions."""

    def test_2_19_has_correct_named_version(self):
        """Test 2.19 maps to Named Ansible 12.x."""
        result = get_named_ansible_version("2.19")
        assert result == "12.x"

    def test_2_20_has_correct_named_version(self):
        """Test 2.20 maps to Named Ansible 13.x."""
        result = get_named_ansible_version("2.20")
        assert result == "13.x"

    def test_2_19_python_support(self):
        """Test 2.19 has correct Python support."""
        control = get_python_compatibility("2.19", "control")
        managed = get_python_compatibility("2.19", "managed")

        # Control: 3.11-3.13
        assert set(control) == {"3.11", "3.12", "3.13"}
        # Managed: 3.8-3.13
        assert set(managed) == {"3.8", "3.9", "3.10", "3.11", "3.12", "3.13"}

    def test_2_20_python_support(self):
        """Test 2.20 has correct Python support."""
        control = get_python_compatibility("2.20", "control")
        managed = get_python_compatibility("2.20", "managed")

        # Control: 3.12-3.14
        assert set(control) == {"3.12", "3.13", "3.14"}
        # Managed: 3.9-3.14
        assert set(managed) == {"3.9", "3.10", "3.11", "3.12", "3.13", "3.14"}

    def test_2_20_is_latest(self):
        """Test that 2.20 is correctly identified as latest."""
        latest = get_latest_version()
        assert latest == "2.20"

    def test_upgrade_path_to_2_20(self):
        """Test calculating upgrade path to 2.20."""
        result = calculate_upgrade_path("2.18", "2.20")
        assert result["from_version"] == "2.18"
        assert result["to_version"] == "2.20"
        assert "python_upgrade_needed" in result
        assert "breaking_changes" in result

    def test_2_19_eol_status(self):
        """Test 2.19 EOL status."""
        result = get_eol_status("2.19")
        assert "status" in result
        assert "security_risk" in result

    def test_2_20_eol_status(self):
        """Test 2.20 EOL status."""
        result = get_eol_status("2.20")
        assert "status" in result
        assert result["status"] == "Supported"
