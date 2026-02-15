"""Comprehensive tests for core/errors.py module to reach 95%+ coverage."""

import os
from unittest.mock import patch

import pytest

from souschef.core.errors import (
    ChefFileNotFoundError,
    ConversionError,
    InvalidCookbookError,
    ParseError,
    SousChefError,
    ValidationError,
    format_error_with_context,
    validate_cookbook_structure,
    validate_directory_exists,
    validate_file_exists,
)


class TestSousChefError:
    """Tests for SousChefError base class."""

    def test_error_with_message_only(self):
        """Test error creation with just a message."""
        error = SousChefError("Something went wrong")
        assert error.message == "Something went wrong"
        assert error.suggestion is None
        assert str(error) == "Something went wrong"

    def test_error_with_message_and_suggestion(self):
        """Test error creation with message and suggestion."""
        error = SousChefError("Something went wrong", "Try this fix")
        assert error.message == "Something went wrong"
        assert error.suggestion == "Try this fix"
        assert "Something went wrong" in str(error)
        assert "Suggestion: Try this fix" in str(error)

    def test_error_can_be_raised_and_caught(self):
        """Test that error can be raised and caught."""
        with pytest.raises(SousChefError, match="Test error"):
            raise SousChefError("Test error")


class TestChefFileNotFoundError:
    """Tests for ChefFileNotFoundError."""

    def test_error_with_file_type_default(self):
        """Test error with default file type."""
        # Enable debug mode to show full paths in tests
        with patch.dict(os.environ, {"SOUSCHEF_DEBUG": "1"}):
            error = ChefFileNotFoundError("/path/to/file")
            assert "Could not find file:" in str(error)
            # In debug mode, full path appears in debug section
            assert "/path/to/file" in str(error)
            assert "Check that the path exists" in str(error)

    def test_error_with_custom_file_type(self):
        """Test error with custom file type."""
        with patch.dict(os.environ, {"SOUSCHEF_DEBUG": "1"}):
            error = ChefFileNotFoundError("/path/to/cookbook", "cookbook")
            assert "Could not find cookbook:" in str(error)
            assert "/path/to/cookbook" in str(error)
            assert "Check that the path exists" in str(error)

    def test_error_can_be_raised(self):
        """Test that error can be raised."""
        with pytest.raises(ChefFileNotFoundError):
            raise ChefFileNotFoundError("/missing/file", "recipe")


class TestInvalidCookbookError:
    """Tests for InvalidCookbookError."""

    def test_error_creation(self):
        """Test error creation with path and reason."""
        with patch.dict(os.environ, {"SOUSCHEF_DEBUG": "1"}):
            error = InvalidCookbookError("/path/to/cookbook", "missing metadata.rb")
            assert "Invalid cookbook at" in str(error)
            assert "missing metadata.rb" in str(error)
            assert "/path/to/cookbook" in str(error)  # Full path in debug mode

    def test_error_has_suggestion(self):
        """Test that error includes helpful suggestion."""
        error = InvalidCookbookError("/path/to/cookbook", "reason")
        assert "Ensure the directory contains a valid Chef cookbook" in str(error)

    def test_error_can_be_raised(self):
        """Test that error can be raised."""
        with pytest.raises(InvalidCookbookError):
            raise InvalidCookbookError("/path", "reason")


class TestParseError:
    """Tests for ParseError."""

    def test_error_without_line_number(self):
        """Test parse error without line number."""
        with patch.dict(os.environ, {"SOUSCHEF_DEBUG": "1"}):
            error = ParseError("/path/to/file.rb")
            assert "Failed to parse" in str(error)
            assert "/path/to/file.rb" in str(error)  # Full path in debug mode
            assert "valid Chef Ruby DSL syntax" in str(error)

    def test_error_with_line_number(self):
        """Test parse error with line number."""
        with patch.dict(os.environ, {"SOUSCHEF_DEBUG": "1"}):
            error = ParseError("/path/to/file.rb", line_number=42)
            assert "Failed to parse" in str(error)
            assert "at line 42" in str(error)
            assert "/path/to/file.rb" in str(error)

    def test_error_with_detail(self):
        """Test parse error with additional detail."""
        with patch.dict(os.environ, {"SOUSCHEF_DEBUG": "1"}):
            error = ParseError("/path/to/file.rb", detail="unexpected token")
            assert "/path/to/file.rb" in str(error)
            assert "unexpected token" in str(error)
        assert "Failed to parse /path/to/file.rb: unexpected token" in str(error)

    def test_error_with_all_params(self):
        """Test parse error with all parameters."""
        error = ParseError("/path/to/file.rb", line_number=10, detail="syntax error")
        assert "at line 10" in str(error)
        assert "syntax error" in str(error)

    def test_error_can_be_raised(self):
        """Test that error can be raised."""
        with pytest.raises(ParseError):
            raise ParseError("/path/to/file.rb", 42, "detail")


class TestConversionError:
    """Tests for ConversionError."""

    def test_error_creation(self):
        """Test conversion error creation."""
        error = ConversionError("custom_resource", "not supported")
        assert "Cannot convert Chef resource 'custom_resource'" in str(error)
        assert "not supported" in str(error)

    def test_error_has_suggestion(self):
        """Test that error includes helpful suggestion."""
        error = ConversionError("some_resource", "reason")
        assert "manual conversion" in str(error)
        assert "Ansible module" in str(error)

    def test_error_can_be_raised(self):
        """Test that error can be raised."""
        with pytest.raises(ConversionError):
            raise ConversionError("resource_type", "reason")


class TestValidationError:
    """Tests for ValidationError."""

    def test_error_with_single_issue(self):
        """Test validation error with one issue."""
        error = ValidationError("YAML", ["Invalid syntax on line 5"])
        assert "YAML validation failed" in str(error)
        assert "Invalid syntax on line 5" in str(error)

    def test_error_with_multiple_issues(self):
        """Test validation error with multiple issues."""
        issues = [
            "Issue 1: problem one",
            "Issue 2: problem two",
            "Issue 3: problem three",
        ]
        error = ValidationError("Playbook", issues)
        assert "Playbook validation failed" in str(error)
        for issue in issues:
            assert issue in str(error)

    def test_error_has_suggestion(self):
        """Test that error includes helpful suggestion."""
        error = ValidationError("Schema", ["Issue"])
        assert "Review the validation issues" in str(error)

    def test_error_can_be_raised(self):
        """Test that error can be raised."""
        with pytest.raises(ValidationError):
            raise ValidationError("type", ["issue"])


class TestValidateFileExists:
    """Tests for validate_file_exists function."""

    def test_valid_file(self, tmp_path):
        """Test validation of existing readable file."""
        test_file = tmp_path / "test.rb"
        test_file.write_text("content")

        result = validate_file_exists(str(test_file))
        assert result == test_file

    def test_nonexistent_file(self, tmp_path):
        """Test validation of nonexistent file."""
        nonexistent = tmp_path / "missing.rb"

        with pytest.raises(ChefFileNotFoundError):
            validate_file_exists(str(nonexistent))

    def test_directory_instead_of_file(self, tmp_path):
        """Test validation when path points to directory not file."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        with pytest.raises(ChefFileNotFoundError):
            validate_file_exists(str(test_dir))

    def test_unreadable_file(self, tmp_path):
        """Test validation of unreadable file."""
        test_file = tmp_path / "unreadable.rb"
        test_file.write_text("content")
        test_file.chmod(0o000)  # Remove all permissions

        try:
            with pytest.raises(SousChefError) as exc_info:
                validate_file_exists(str(test_file))
            assert "Permission denied" in str(exc_info.value)
        finally:
            # Restore permissions for cleanup
            test_file.chmod(0o644)

    def test_custom_file_type(self, tmp_path):
        """Test validation with custom file type for error message."""
        nonexistent = tmp_path / "missing.rb"

        with pytest.raises(ChefFileNotFoundError) as exc_info:
            validate_file_exists(str(nonexistent), "recipe")
        assert "Could not find recipe" in str(exc_info.value)


class TestValidateDirectoryExists:
    """Tests for validate_directory_exists function."""

    def test_valid_directory(self, tmp_path):
        """Test validation of existing readable directory."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        result = validate_directory_exists(str(test_dir))
        assert result == test_dir

    def test_nonexistent_directory(self, tmp_path):
        """Test validation of nonexistent directory."""
        nonexistent = tmp_path / "missing_dir"

        with pytest.raises(ChefFileNotFoundError):
            validate_directory_exists(str(nonexistent))

    def test_file_instead_of_directory(self, tmp_path):
        """Test validation when path points to file not directory."""
        test_file = tmp_path / "test.rb"
        test_file.write_text("content")

        with pytest.raises(SousChefError) as exc_info:
            validate_directory_exists(str(test_file))
        assert "Path is not a directory" in str(exc_info.value)

    def test_unreadable_directory(self, tmp_path):
        """Test validation of unreadable directory."""
        test_dir = tmp_path / "unreadable"
        test_dir.mkdir()
        test_dir.chmod(0o000)  # Remove all permissions

        try:
            with pytest.raises(SousChefError) as exc_info:
                validate_directory_exists(str(test_dir))
            assert "Permission denied" in str(exc_info.value)
        finally:
            # Restore permissions for cleanup
            test_dir.chmod(0o755)

    def test_custom_dir_type(self, tmp_path):
        """Test validation with custom directory type for error message."""
        nonexistent = tmp_path / "missing"

        with pytest.raises(ChefFileNotFoundError) as exc_info:
            validate_directory_exists(str(nonexistent), "cookbook")
        assert "Could not find cookbook" in str(exc_info.value)


class TestValidateCookbookStructure:
    """Tests for validate_cookbook_structure function."""

    def test_valid_cookbook_with_metadata_rb(self, tmp_path):
        """Test validation of valid cookbook with metadata.rb."""
        cookbook_path = tmp_path / "cookbook"
        cookbook_path.mkdir()
        (cookbook_path / "metadata.rb").write_text("name 'test'\nversion '1.0.0'\n")

        result = validate_cookbook_structure(str(cookbook_path))
        assert result == cookbook_path

    def test_valid_cookbook_with_metadata_json(self, tmp_path):
        """Test validation of valid cookbook with metadata.json."""
        cookbook_path = tmp_path / "cookbook"
        cookbook_path.mkdir()
        (cookbook_path / "metadata.json").write_text(
            '{"name": "test", "version": "1.0.0"}'
        )

        result = validate_cookbook_structure(str(cookbook_path))
        assert result == cookbook_path

    def test_invalid_cookbook_no_metadata(self, tmp_path):
        """Test validation of invalid cookbook without metadata."""
        cookbook_path = tmp_path / "cookbook"
        cookbook_path.mkdir()

        with pytest.raises(InvalidCookbookError) as exc_info:
            validate_cookbook_structure(str(cookbook_path))
        assert "No metadata.rb or metadata.json found" in str(exc_info.value)

    def test_nonexistent_cookbook(self, tmp_path):
        """Test validation of nonexistent cookbook."""
        nonexistent = tmp_path / "missing"

        with pytest.raises(ChefFileNotFoundError):
            validate_cookbook_structure(str(nonexistent))


class TestFormatErrorWithContext:
    """Tests for format_error_with_context function."""

    def test_souschef_error(self):
        """Test formatting of SousChefError."""
        error = SousChefError("Test error", "Test suggestion")
        result = format_error_with_context(error, "parsing", "/path/to/file")

        assert "Test error" in result
        assert "Test suggestion" in result

    def test_file_not_found_error(self):
        """Test formatting of FileNotFoundError."""
        error = FileNotFoundError("File not found")
        result = format_error_with_context(error, "parsing", "/path/to/file")

        assert "Could not find" in result

    def test_permission_error(self):
        """Test formatting of PermissionError."""
        error = PermissionError("Permission denied")
        result = format_error_with_context(error, "reading file", "/path/to/file")

        assert "Permission denied" in result
        assert "file/directory permissions" in result

    def test_value_error(self):
        """Test formatting of ValueError."""
        error = ValueError("Invalid value")
        result = format_error_with_context(error, "converting", "/path/to/file")

        assert "Invalid value" in result
        assert "correct format and type" in result

    def test_generic_error(self):
        """Test formatting of generic exception."""
        error = RuntimeError("Something went wrong")
        result = format_error_with_context(error, "processing", "/path/to/file")

        assert "Something went wrong" in result
        assert "please report it" in result

    def test_error_without_file_path(self):
        """Test formatting without file path."""
        error = ValueError("Test error")
        result = format_error_with_context(error, "validation")

        assert "Error during validation" in result
        assert "Test error" in result
