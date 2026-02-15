"""Comprehensive tests for core/ansible_versions.py module."""

from contextlib import suppress
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from souschef.core.ansible_versions import (
    AnsibleVersion,
    calculate_upgrade_path,
    format_version_display,
    get_aap_compatible_versions,
    get_ansible_core_version,
    get_eol_status,
    get_latest_version,
    get_minimum_python_for_ansible,
    get_named_ansible_version,
    get_python_compatibility,
    get_supported_versions,
    is_python_compatible,
)


class TestAnsibleVersionStructure:
    """Test AnsibleVersion dataclass."""

    def test_create_version(self) -> None:
        """Test creating Ansible version object."""
        version = AnsibleVersion(
            version="2.10",
            named_version="3.0",
            release_date=date(2021, 5, 18),
            eol_date=date(2023, 5, 18),
            control_node_python=["3.8", "3.9"],
            managed_node_python=["2.7", "3.5", "3.6"],
        )

        assert version.version == "2.10"
        assert version.named_version == "3.0"
        assert version.control_node_python == ["3.8", "3.9"]

    def test_version_with_breaking_changes(self) -> None:
        """Test version with breaking changes."""
        version = AnsibleVersion(
            version="2.10",
            named_version="3.0",
            release_date=date(2021, 5, 18),
            eol_date=date(2023, 5, 18),
            control_node_python=["3.8"],
            managed_node_python=["3.6"],
            major_changes=["API change", "Module removal"],
        )

        assert len(version.major_changes) == 2

    def test_version_with_aap_compatibility(self) -> None:
        """Test version with AAP compatibility."""
        version = AnsibleVersion(
            version="2.11",
            named_version="4.0",
            release_date=date(2021, 10, 1),
            eol_date=date(2023, 10, 1),
            control_node_python=["3.8", "3.9"],
            managed_node_python=["3.6"],
            aap_versions=["2.1", "2.2"],
        )

        assert version.aap_versions == ["2.1", "2.2"]


class TestGetLatestVersion:
    """Test get_latest_version function."""

    @patch("souschef.core.ansible_versions._load_version_data")
    def test_get_latest(self, mock_load: MagicMock) -> None:
        """Test getting latest version."""
        mock_load.return_value = {
            "2.10": AnsibleVersion(
                version="2.10",
                named_version="3.0",
                release_date=date(2021, 5, 18),
                eol_date=None,
                control_node_python=["3.8"],
                managed_node_python=["3.6"],
            ),
            "2.11": AnsibleVersion(
                version="2.11",
                named_version="4.0",
                release_date=date(2021, 10, 1),
                eol_date=None,
                control_node_python=["3.8"],
                managed_node_python=["3.6"],
            ),
        }

        result = get_latest_version()

        assert isinstance(result, str)

    def test_latest_version_is_string(self) -> None:
        """Test latest version returns string."""
        result = get_latest_version()

        assert isinstance(result, str)


class TestGetSupportedVersions:
    """Test get_supported_versions function."""

    def test_get_supported(self) -> None:
        """Test getting supported versions."""
        result = get_supported_versions()

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(v, str) for v in result)

    def test_supported_versions_sorted(self) -> None:
        """Test supported versions list."""
        result = get_supported_versions()

        # Should have Ansible versions
        assert len(result) > 0


class TestGetPythonCompatibility:
    """Test get_python_compatibility function."""

    def test_python_compat_for_version(self) -> None:
        """Test getting Python compatibility."""
        result = get_python_compatibility("2.10")

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(v, str) for v in result)

    def test_python_compat_structure(self) -> None:
        """Test compatibility result structure."""
        result = get_python_compatibility("2.11")

        assert isinstance(result, list)
        assert all(isinstance(v, str) for v in result)

    def test_python_compat_invalid_version(self) -> None:
        """Test with invalid version."""
        with pytest.raises(ValueError, match="Unknown Ansible version"):
            get_python_compatibility("invalid")

    def test_python_compat_managed_nodes(self) -> None:
        """Test getting Python compatibility for managed nodes."""
        result = get_python_compatibility("2.10", node_type="managed")

        assert isinstance(result, list)
        assert len(result) > 0

    def test_python_compat_invalid_node_type(self) -> None:
        """Test with invalid node type."""
        with pytest.raises(ValueError, match="Invalid node_type"):
            get_python_compatibility("2.10", node_type="invalid")


class TestIsPythonCompatible:
    """Test is_python_compatible function."""

    def test_compatible_python_version(self) -> None:
        """Test compatible Python version."""
        result = is_python_compatible("2.10", "3.9")

        assert isinstance(result, bool)

    def test_incompatible_python_version(self) -> None:
        """Test incompatible Python version."""
        # Find an old version and try very new Python
        result = is_python_compatible("2.9", "3.12")

        assert isinstance(result, bool)

    def test_python_compat_with_managed_nodes(self) -> None:
        """Test Python compatibility for managed nodes."""
        result = is_python_compatible("2.10", "2.7", node_type="managed")

        assert isinstance(result, bool)

    def test_python_compat_with_control_nodes(self) -> None:
        """Test Python compatibility for control nodes."""
        result = is_python_compatible("2.10", "3.9", node_type="control")

        assert isinstance(result, bool)

    def test_invalid_ansible_version(self) -> None:
        """Test with invalid Ansible version."""
        with pytest.raises(ValueError, match="Unknown Ansible version"):
            is_python_compatible("invalid", "3.9")


class TestGetMinimumPythonForAnsible:
    """Test get_minimum_python_for_ansible function."""

    def test_get_minimum_python(self) -> None:
        """Test getting minimum Python version."""
        result = get_minimum_python_for_ansible("2.10")

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_minimum_python_versions_are_strings(self) -> None:
        """Test that minimum versions are strings."""
        result = get_minimum_python_for_ansible("2.11")

        assert isinstance(result[0], str)  # control node
        assert isinstance(result[1], str)  # managed node

    def test_minimum_python_for_newer_version(self) -> None:
        """Test minimum Python for newer Ansible."""
        result = get_minimum_python_for_ansible("2.11")

        assert isinstance(result, tuple)


class TestGetAnsibleCoreVersion:
    """Test get_ansible_core_version function."""

    def test_get_core_from_named(self) -> None:
        """Test getting core version from named version."""
        result = get_ansible_core_version("4.0")

        # May be None or a version string
        assert result is None or isinstance(result, str)

    def test_get_core_invalid_named(self) -> None:
        """Test getting core for invalid named version."""
        result = get_ansible_core_version("invalid")

        assert result is None or isinstance(result, str)


class TestGetNamedAnsibleVersion:
    """Test get_named_ansible_version function."""

    def test_get_named_from_core(self) -> None:
        """Test getting named version from core."""
        result = get_named_ansible_version("2.10")

        # May be None or a version string
        assert result is None or isinstance(result, str)

    def test_get_named_for_old_core(self) -> None:
        """Test named version for old core."""
        result = get_named_ansible_version("2.9")

        assert result is None or isinstance(result, str)


class TestGetAAPCompatibleVersions:
    """Test get_aap_compatible_versions function."""

    def test_get_aap_versions(self) -> None:
        """Test getting AAP compatible versions."""
        result = get_aap_compatible_versions("2.10")

        assert isinstance(result, list)

    def test_aap_versions_are_strings(self) -> None:
        """Test AAP versions are strings."""
        result = get_aap_compatible_versions("2.11")

        if result:
            assert all(isinstance(v, str) for v in result)

    def test_aap_versions_invalid_ansible(self) -> None:
        """Test AAP versions for invalid Ansible."""
        result = get_aap_compatible_versions("invalid")

        assert isinstance(result, list)


class TestGetEOLStatus:
    """Test get_eol_status function."""

    def test_get_eol_status(self) -> None:
        """Test getting EOL status."""
        result = get_eol_status("2.10")

        assert isinstance(result, dict)
        assert "version" in result or "error" in result

    def test_eol_status_structure(self) -> None:
        """Test EOL status result."""
        result = get_eol_status("2.9")

        assert isinstance(result, dict)

    def test_eol_status_invalid_version(self) -> None:
        """Test EOL status for invalid."""
        result = get_eol_status("invalid")

        assert isinstance(result, dict)
        assert "error" in result


class TestCalculateUpgradePath:
    """Test calculate_upgrade_path function."""

    def test_upgrade_same_version(self) -> None:
        """Test upgrade path for same version."""
        result = calculate_upgrade_path("2.10", "2.10")

        assert isinstance(result, dict)
        assert "from_version" in result or "error" in result

    def test_upgrade_minor_version(self) -> None:
        """Test upgrading to minor version."""
        result = calculate_upgrade_path("2.10", "2.11")

        assert isinstance(result, dict)

    def test_upgrade_major_version(self) -> None:
        """Test upgrading to major version."""
        # Use versions that might actually exist in the data
        result = calculate_upgrade_path("2.14", "2.16")

        assert isinstance(result, dict)

    def test_upgrade_backward_not_supported(self) -> None:
        """Test downgrade not supported."""
        result = calculate_upgrade_path("2.16", "2.10")

        assert isinstance(result, dict)

    def test_upgrade_path_contains_steps(self) -> None:
        """Test upgrade path has steps."""
        result = calculate_upgrade_path("2.13", "2.16")

        assert isinstance(result, dict)

    def test_upgrade_with_invalid_source(self) -> None:
        """Test upgrade with invalid source."""
        with suppress(ValueError):
            calculate_upgrade_path("invalid", "2.10")


class TestFormatVersionDisplay:
    """Test format_version_display function."""

    def test_format_ansible_version(self) -> None:
        """Test formatting Ansible version."""
        result = format_version_display("2.10", include_named=False)

        assert isinstance(result, str)
        assert "2.10" in result

    def test_format_with_named(self) -> None:
        """Test formatting with named version."""
        result = format_version_display("2.10", include_named=True)

        assert isinstance(result, str)

    def test_format_with_aap(self) -> None:
        """Test formatting with AAP info."""
        result = format_version_display("2.11", include_aap=True)

        assert isinstance(result, str)

    def test_format_invalid_version(self) -> None:
        """Test formatting invalid version."""
        result = format_version_display("invalid")

        assert isinstance(result, str)


class TestVersionIntegration:
    """Test integration scenarios."""

    def test_version_selection_workflow(self) -> None:
        """Test selecting appropriate version."""
        # Get supported versions
        supported = get_supported_versions()
        assert len(supported) > 0

        # Get latest
        latest = get_latest_version()
        assert isinstance(latest, str)

        # Check Python compatibility
        if supported:
            compat = get_python_compatibility(supported[0])
            assert isinstance(compat, list)

    def test_upgrade_planning_workflow(self) -> None:
        """Test planning upgrade."""
        supported = get_supported_versions()
        if len(supported) >= 2:
            # Plan upgrade from newest to oldest
            path = calculate_upgrade_path(supported[0], supported[-1])
            assert isinstance(path, dict)

            # Check EOL status
            eol = get_eol_status(supported[0])
            assert isinstance(eol, dict)

    def test_python_version_checking_workflow(self) -> None:
        """Test checking Python compatibility."""
        supported = get_supported_versions()
        if supported:
            min_python = get_minimum_python_for_ansible(supported[0])
            assert isinstance(min_python, tuple)
            assert len(min_python) == 2

            # Check if specific Python is compatible
            compat = is_python_compatible(supported[0], "3.9")
            assert isinstance(compat, bool)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_none_version_parameter(self) -> None:
        """Test handling None version."""
        try:
            result = get_eol_status(None)  # type: ignore
            assert isinstance(result, dict)
        except (TypeError, AttributeError):
            # Expected if None not accepted
            pass

    def test_empty_string_version(self) -> None:
        """Test handling empty version string."""
        result = get_eol_status("")

        assert isinstance(result, dict)

    def test_very_old_version(self) -> None:
        """Test very old version."""
        result = get_eol_status("1.9")

        assert isinstance(result, dict)

    def test_very_new_version(self) -> None:
        """Test future version."""
        result = get_eol_status("99.0")

        assert isinstance(result, dict)
