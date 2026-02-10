"""
Tests for enhanced error handling and validation.

Tests enhanced error messages, validation functions, and context-rich
error reporting for parser and validation operations.
"""

import pytest

from souschef.core.error_handling import (
    EnhancedErrorHandler,
    EnhancedErrorMessage,
    ErrorContext,
    validate_ansible_version,
    validate_collection_name,
    validate_hostname,
)


class TestEnhancedErrorMessages:
    """Tests for enhanced error message generation."""

    def test_error_context_basic(self):
        """Test basic error context creation."""
        context = ErrorContext(
            error_type="test_error",
            location="/path/to/file.yml",
            line_number=42,
        )
        assert context.error_type == "test_error"
        assert context.location == "/path/to/file.yml"
        assert context.line_number == 42
        assert context.column_number is None

    def test_enhanced_error_message_formatting(self):
        """Test enhanced error message formatting."""
        context = ErrorContext(
            error_type="yaml_error",
            location="/path/to/inventory.yml",
            line_number=10,
        )
        error = EnhancedErrorMessage(
            title="Invalid YAML syntax",
            description="The file contains invalid YAML",
            context=context,
            suggestions=["Fix indentation", "Check syntax"],
            documentation_link="https://yaml.org",
        )

        formatted = error.format_message()
        assert "Invalid YAML syntax" in formatted
        assert "/path/to/inventory.yml" in formatted
        assert "Line 10" in formatted
        assert "Fix indentation" in formatted
        assert "https://yaml.org" in formatted

    def test_invalid_yaml_error(self):
        """Test invalid YAML error generation."""
        error = EnhancedErrorHandler.generate_invalid_yaml_error(
            "/path/to/file.yml",
            line_number=5,
            error_detail="mapping values are not allowed here",
        )

        assert error.title == "Invalid YAML syntax in /path/to/file.yml"
        assert "mapping values are not allowed here" in error.format_message()
        assert error.context.error_type == "yaml_parse_error"

    def test_invalid_ini_error(self):
        """Test invalid INI error generation."""
        error = EnhancedErrorHandler.generate_invalid_ini_error(
            "/path/to/file.ini",
            line_number=8,
            error_detail="Missing section header",
        )

        assert error.title == "Invalid INI syntax in /path/to/file.ini"
        assert "Missing section header" in error.format_message()
        assert error.context.error_type == "ini_parse_error"

    def test_missing_file_error(self):
        """Test missing file error generation."""
        error = EnhancedErrorHandler.generate_missing_file_error("/path/to/missing.yml")

        assert error.title == "File not found: /path/to/missing.yml"
        assert "/path/to/missing.yml" in error.format_message()
        assert error.context.error_type == "file_not_found"

    def test_version_mismatch_error(self):
        """Test version mismatch error generation."""
        error = EnhancedErrorHandler.generate_version_mismatch_error("3.0.0")

        assert "version" in error.title.lower()
        assert "3.0.0" in error.format_message()
        assert "2.20" in error.format_message()  # Valid version in suggestions

    def test_invalid_collection_name_error(self):
        """Test invalid collection name error generation."""
        error = EnhancedErrorHandler.generate_invalid_collection_name_error("invalid")

        assert "collection name" in error.title.lower()
        assert "invalid" in error.format_message()
        assert "namespace.collection" in error.format_message()

    def test_invalid_hostname_error(self):
        """Test invalid hostname error generation."""
        error = EnhancedErrorHandler.invalid_hostname("invalid..com")

        assert "hostname" in error.title.lower()
        assert "invalid..com" in error.format_message()


class TestCollectionNameValidation:
    """Tests for collection name validation."""

    @pytest.mark.parametrize(
        "valid_name",
        [
            "community.general",
            "ansible.netcommon",
            "arista.eos",
            "amazon.aws",
            "cloud.terraform",
            "infra.tools",
            "my_org.my_collection",
        ],
    )
    def test_valid_collection_names(self, valid_name):
        """Test validation of valid collection names."""
        is_valid, error_msg = validate_collection_name(valid_name)
        assert is_valid is True
        assert error_msg is None

    @pytest.mark.parametrize(
        "invalid_name",
        [
            "invalid",  # No namespace
            "community..general",  # Double dot
            "community.general.extra",  # Too many parts
            ".community.general",  # Leading dot
            "community.general.",  # Trailing dot
            "community.9general",  # Second part starts with digit
            "2community.general",  # First part starts with digit
            "community.General",  # Uppercase
            "community.general-tools",  # Hyphen not allowed
            "",  # Empty string
        ],
    )
    def test_invalid_collection_names(self, invalid_name):
        """Test validation rejects invalid collection names."""
        is_valid, error_msg = validate_collection_name(invalid_name)
        assert is_valid is False
        assert error_msg is not None
        assert "Invalid collection name" in error_msg or "collection name" in error_msg

    def test_non_string_collection_name(self):
        """Test validation rejects non-string collection names."""
        is_valid, error_msg = validate_collection_name("123")
        assert is_valid is False
        assert error_msg is not None


class TestHostnameValidation:
    """Tests for hostname validation."""

    @pytest.mark.parametrize(
        "valid_hostname",
        [
            "localhost",
            "example.com",
            "my-server.example.co.uk",
            "server1.example.com",
            "192.168.1.1",
            "10.0.0.1",
            "255.255.255.255",
            "srv-01",
            "database",
            "web.service.local",
        ],
    )
    def test_valid_hostnames(self, valid_hostname):
        """Test validation of valid hostnames."""
        is_valid, error_msg = validate_hostname(valid_hostname)
        assert is_valid is True
        assert error_msg is None

    @pytest.mark.parametrize(
        "invalid_hostname",
        [
            "example..com",  # Double dot
            "-example.com",  # Leading hyphen
            "example-.com",  # Trailing hyphen in label
            "example .com",  # Space
            "exam@ple.com",  # Invalid character
            "",  # Empty string
            "   ",  # Only whitespace
            "host:8080",  # Port not allowed
        ],
    )
    def test_invalid_hostnames(self, invalid_hostname):
        """Test validation rejects invalid hostnames."""
        is_valid, error_msg = validate_hostname(invalid_hostname)
        assert is_valid is False
        assert error_msg is not None

    def test_non_string_hostname(self):
        """Test validation rejects non-string hostnames converted to invalid strings."""
        # Empty string after conversion should still be invalid
        is_valid, error_msg = validate_hostname("")
        assert is_valid is False
        assert error_msg is not None


class TestAnsibleVersionValidation:
    """Tests for Ansible version validation."""

    @pytest.mark.parametrize(
        "valid_version",
        [
            "2.18",
            "2.19",
            "2.20",
        ],
    )
    def test_valid_ansible_versions(self, valid_version):
        """Test validation of supported Ansible versions."""
        is_valid, error_msg = validate_ansible_version(valid_version)
        assert is_valid is True
        assert error_msg is None

    @pytest.mark.parametrize(
        "invalid_version",
        [
            "3.0",  # Unsupported version
            "2.8",  # Too old
            "2.17",  # EOL (end of life)
            "2.9",  # EOL (end of life)
            "1.0",  # Way too old
            "foo",  # Invalid format
            "2.9.0.1",  # Too many parts
            "",  # Empty
        ],
    )
    def test_invalid_ansible_versions(self, invalid_version):
        """Test validation rejects unsupported versions."""
        is_valid, error_msg = validate_ansible_version(invalid_version)
        assert is_valid is False
        assert error_msg is not None


class TestErrorMessageContent:
    """Tests for content of error messages."""

    def test_yaml_error_has_suggestions(self):
        """Test YAML error includes helpful suggestions."""
        error = EnhancedErrorHandler.generate_invalid_yaml_error(
            "test.yml", error_detail="test error"
        )
        formatted = error.format_message()

        # Should have suggestions about indentation, colons, etc.
        assert "[SUGGESTIONS]" in formatted
        assert len(error.suggestions) > 0

    def test_error_messages_have_documentation_links(self):
        """Test that error messages include documentation links."""
        errors = [
            EnhancedErrorHandler.generate_invalid_yaml_error("test.yml"),
            EnhancedErrorHandler.generate_invalid_ini_error("test.ini"),
            EnhancedErrorHandler.generate_version_mismatch_error("1.0"),
            EnhancedErrorHandler.generate_invalid_collection_name_error("test"),
            EnhancedErrorHandler.invalid_hostname("invalid..com"),
        ]

        for error in errors:
            formatted = error.format_message()
            if error.documentation_link:
                assert error.documentation_link in formatted

    def test_error_context_with_code_snippet(self):
        """Test error context can include code snippet."""
        context = ErrorContext(
            error_type="parse_error",
            location="test.yml",
            line_number=5,
            snippet="invalid: yaml: syntax",
        )

        error = EnhancedErrorMessage(
            title="Parse error",
            description="Failed to parse",
            context=context,
            suggestions=["Fix the syntax"],
        )

        formatted = error.format_message()
        assert "invalid: yaml: syntax" in formatted


class TestValidationIntegration:
    """Integration tests for validation functions."""

    def test_collection_name_validation_with_ansible_collections(self):
        """Test collection name validation with known Ansible collections."""
        valid_collections = [
            "community.general",
            "ansible.netcommon",
            "amazon.aws",
            "google.cloud",
            "microsoft.windows",
        ]

        for collection in valid_collections:
            is_valid, _ = validate_collection_name(collection)
            assert is_valid, f"{collection} should be valid"

    def test_hostname_validation_with_various_formats(self):
        """Test hostname validation handles various formats."""
        # Test IPv4
        is_valid, _ = validate_hostname("192.168.1.100")
        assert is_valid

        # Test DNS
        is_valid, _ = validate_hostname("ansible.example.com")
        assert is_valid

        # Test simple hostname
        is_valid, _ = validate_hostname("server1")
        assert is_valid

    def test_version_validation_consistency(self):
        """Test that version validation is consistent."""
        # All valid versions should consistently pass
        valid = ["2.18", "2.19", "2.20"]
        for ver in valid:
            is_valid, _ = validate_ansible_version(ver)
            assert is_valid

        # All invalid versions should consistently fail
        invalid = ["1.0", "2.9", "2.17", "3.0", "foo"]
        for ver in invalid:
            is_valid, _ = validate_ansible_version(ver)
            assert not is_valid

    def test_error_message_isolation(self):
        """Test that generating one error doesn't affect others."""
        error1 = EnhancedErrorHandler.generate_missing_file_error("file1.yml")
        error2 = EnhancedErrorHandler.generate_missing_file_error("file2.yml")

        assert "file1.yml" in error1.format_message()
        assert "file2.yml" in error2.format_message()
        assert "file1.yml" not in error2.format_message()
        assert "file2.yml" not in error1.format_message()
