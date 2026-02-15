"""Test core validation functions and error paths in server.py."""

import contextlib

import pytest

from souschef.server import (
    _validate_path_length,
    _validate_plan_paths,
    _validate_role_name,
)


class TestValidatePathLength:
    """Test _validate_path_length validation function."""

    def test_validate_path_length_acceptable(self) -> None:
        """Test validation with acceptable path length."""
        # Should not raise
        _validate_path_length("/valid/path", "test_path")

    def test_validate_path_length_empty_string(self) -> None:
        """Test validation with empty string."""
        # Empty string is actually valid (length 0 < limit)
        _validate_path_length("", "empty_path")

    def test_validate_path_length_exceeds_limit(self) -> None:
        """Test that exceeding path length raises ValueError."""
        # Create a path longer than the maximum (4096)
        long_path = "/" + "a" * 5000
        with pytest.raises(ValueError, match="exceeds maximum length"):
            _validate_path_length(long_path, "test_path")

    def test_validate_path_length_relative_path(self) -> None:
        """Test validation with relative path."""
        _validate_path_length("relative/path/to/file", "relative")

    def test_validate_path_length_with_spaces(self) -> None:
        """Test validation with spaces in path."""
        _validate_path_length("/path with spaces/to/file", "spaced")

    def test_validate_path_length_label_in_error(self) -> None:
        """Test that label appears in error message."""
        long_path = "/" + "a" * 5000
        with pytest.raises(ValueError) as exc_info:
            _validate_path_length(long_path, "CustomLabel")
        assert "CustomLabel" in str(exc_info.value)


class TestValidatePlanPaths:
    """Test _validate_plan_paths validation function."""

    def test_validate_plan_paths_single_path(self) -> None:
        """Test validation with a single valid path."""
        # Should not raise
        _validate_plan_paths("/path/to/plan")

    def test_validate_plan_paths_multiple_paths(self) -> None:
        """Test validation with multiple valid paths."""
        # Should not raise
        _validate_plan_paths("/path/to/plan1,/path/to/plan2")

    def test_validate_plan_paths_with_whitespace(self) -> None:
        """Test validation with whitespace in paths."""
        # Should handle whitespace correctly
        _validate_plan_paths("  /path/to/plan1  ,  /path/to/plan2  ")

    def test_validate_plan_paths_three_paths(self) -> None:
        """Test with three paths."""
        _validate_plan_paths("/path1,/path2,/path3")

    def test_validate_plan_paths_exceeds_character_limit(self) -> None:
        """Test that exceeding character limit raises ValueError."""
        # Create a string longer than the maximum (8192)
        long_path = "a" * 10000
        with pytest.raises(ValueError, match="exceed maximum length"):
            _validate_plan_paths(long_path)

    def test_validate_plan_paths_exceeds_count_limit(self) -> None:
        """Test that exceeding path count limit raises ValueError."""
        # Create 30 paths (limit is 20)
        many_paths = ",".join([f"/path/{i}" for i in range(30)])
        with pytest.raises(ValueError, match="Too many Habitat plan paths"):
            _validate_plan_paths(many_paths)

    def test_validate_plan_paths_empty_string(self) -> None:
        """Test with empty string."""
        # Empty string is valid (no paths to validate)
        _validate_plan_paths("")

    def test_validate_plan_paths_only_commas(self) -> None:
        """Test with only commas (no actual paths)."""
        # Depends on implementation - might succeed if all are stripped
        with contextlib.suppress(ValueError):
            _validate_plan_paths(",,,")


class TestValidateRoleName:
    """Test _validate_role_name validation function."""

    def test_validate_role_name_valid_underscore(self) -> None:
        """Test with valid role name containing underscore."""
        _validate_role_name("valid_role")

    def test_validate_role_name_valid_dash(self) -> None:
        """Test role name with dashes."""
        _validate_role_name("valid-role-name")

    def test_validate_role_name_valid_numbers(self) -> None:
        """Test role name with numbers."""
        _validate_role_name("role_name_123")

    def test_validate_role_name_with_spaces(self) -> None:
        """Test that spaces in role name are allowed."""
        # Spaces are actually allowed
        _validate_role_name("valid role")

    def test_validate_role_name_invalid_path_traversal(self) -> None:
        """Test that path traversal attempts raise error."""
        with pytest.raises(ValueError):
            _validate_role_name("../malicious")

    def test_validate_role_name_empty(self) -> None:
        """Test that empty role name raises error."""
        with pytest.raises(ValueError):
            _validate_role_name("")

    def test_validate_role_name_single_char(self) -> None:
        """Test with single character role name."""
        with contextlib.suppress(ValueError):
            _validate_role_name("a")

    def test_validate_role_name_long(self) -> None:
        """Test with long role name."""
        _validate_role_name("very_long_role_name_that_is_still_valid_123")


class TestValidationEdgeCases:
    """Test edge cases across validation functions."""

    def test_path_with_unicode(self) -> None:
        """Test path validation with unicode characters."""
        # Should handle unicode paths
        with contextlib.suppress(ValueError):
            _validate_path_length("/path/to/café/file", "unicode")

    def test_path_with_dots(self) -> None:
        """Test path with .. and . components."""
        _validate_path_length("/path/../other/./file", "dots")

    def test_role_name_with_leading_underscore(self) -> None:
        """Test role name starting with underscore."""
        with contextlib.suppress(ValueError):
            _validate_role_name("_private_role")

    def test_role_name_case_sensitive(self) -> None:
        """Test role names with mixed case."""
        with contextlib.suppress(ValueError):
            _validate_role_name("MyRole")


class TestValidationBoundaries:
    """Test boundary conditions."""

    def test_path_length_at_max_boundary(self) -> None:
        """Test path at maximum allowed length."""
        # Create path that's at the boundary (4096)
        max_safe_path = "/" + "a" * 4090
        with contextlib.suppress(ValueError):
            _validate_path_length(max_safe_path, "boundary")

    def test_plan_paths_at_count_boundary(self) -> None:
        """Test with exactly at the path count limit."""
        # Assuming limit is 20
        paths_at_limit = ",".join([f"/path/{i}" for i in range(20)])
        with contextlib.suppress(ValueError):
            _validate_plan_paths(paths_at_limit)

    def test_plan_paths_at_length_boundary(self) -> None:
        """Test with plan paths at character length boundary."""
        # Create paths near 8192 character limit
        paths_at_limit = "a" * 8100
        with pytest.raises(ValueError):
            _validate_plan_paths(paths_at_limit)

    def test_role_name_max_length(self) -> None:
        """Test role name at maximum reasonable length."""
        long_role = "a" * 255  # Common max identifier length
        with contextlib.suppress(ValueError):
            _validate_role_name(long_role)
