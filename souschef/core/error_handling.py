"""
Enhanced error messages for SousChef parsers and validation.

Provides context-rich error messages with suggestions and documentation links
to help users understand and resolve issues quickly.
"""

import re
from dataclasses import dataclass


@dataclass
class ErrorContext:
    """Context information for enhanced error reporting."""

    error_type: str
    location: str | None = None
    line_number: int | None = None
    column_number: int | None = None
    snippet: str | None = None


@dataclass
class EnhancedErrorMessage:
    """Structured error message with context and suggestions."""

    title: str
    description: str
    context: ErrorContext
    suggestions: list[str]
    documentation_link: str | None = None

    def format_message(self) -> str:
        """
        Format the error message for display.

        Returns:
            Formatted error message with context, suggestions, and links.

        """
        lines = [f"[ERROR] {self.title}"]
        lines.append(f"\n{self.description}")

        if self.context.location:
            lines.append(f"\n[LOCATION] {self.context.location}")

        if self.context.line_number:
            line_info = f"Line {self.context.line_number}"
            if self.context.column_number:
                line_info += f", Column {self.context.column_number}"
            lines.append(f"   {line_info}")

        if self.context.snippet:
            lines.append(f"\n   Code:\n   {self.context.snippet}")

        if self.suggestions:
            lines.append("\n[SUGGESTIONS]")
            for i, suggestion in enumerate(self.suggestions, 1):
                lines.append(f"   {i}. {suggestion}")

        if self.documentation_link:
            lines.append("\n[DOCUMENTATION]")
            lines.append(f"   {self.documentation_link}")

        return "\n".join(lines)


class EnhancedErrorHandler:
    """Handler for generating context-rich error messages."""

    # Error message templates for common parsing issues
    INVALID_YAML_ERROR = (
        "Invalid YAML syntax in {file}",
        "The YAML file contains syntax errors that prevent parsing. "
        "Common causes: incorrect indentation, missing colons, invalid characters.",
        [
            "Check that all indentation uses spaces (not tabs)",
            "Verify all keys end with a colon (:)",
            "Look for special characters that need to be quoted",
            "Use a YAML linter to validate syntax",
        ],
        "https://yaml.org/spec/1.2/spec.html",
    )

    INVALID_INI_ERROR = (
        "Invalid INI syntax in {file}",
        "The INI file contains syntax errors. "
        "Check for proper section headers and key=value pairs.",
        [
            "Section headers must be surrounded by brackets: [section_name]",
            "Key-value pairs must use format: key = value",
            "Avoid special characters in section or key names",
            "Comments must start with # or ;",
        ],
        "https://en.wikipedia.org/wiki/INI_file",
    )

    MISSING_FILE_ERROR = (
        "File not found: {file}",
        "The specified file cannot be located. "
        "Check the file path and ensure the file exists.",
        [
            "Verify the file path is correct",
            "Check that the file has not been moved or deleted",
            "Ensure you have read permissions for the file",
            "Use absolute paths if relative paths are not working",
        ],
        None,
    )

    VERSION_MISMATCH_ERROR = (
        "Ansible version mismatch",
        "The specified Ansible version is not supported or recognised. "
        "Check that you are using a valid Ansible-core version.",
        [
            "Valid versions: 2.9-2.20",
            "Use 'ansible --version' to check your current version",
            "For version upgrades, refer to the upgrade guide",
        ],
        "https://docs.ansible.com/ansible/latest/release_notes/index.html",
    )

    INVALID_COLLECTION_NAME = (
        "Invalid collection name format",
        "Collection names must follow Ansible naming conventions. "
        "Valid format: namespace.collection (e.g., community.general)",
        [
            "Ensure the collection name contains exactly one dot",
            "Both namespace and collection must start with a letter",
            "Use only lowercase letters, numbers, and underscores",
            "Namespace and collection names should be between 2-100 characters",
        ],
        "https://docs.ansible.com/ansible/latest/collections/index.html",
    )

    INVALID_HOST_NAME = (
        "Invalid hostname format",
        "The hostname does not meet Ansible standards. "
        "Hostnames must be valid DNS names or IP addresses.",
        [
            "DNS names can contain letters, digits, hyphens, and dots",
            "IP addresses must be valid IPv4 (x.x.x.x) or IPv6 format",
            "Avoid spaces and special characters",
            "Maximum hostname length is 255 characters",
        ],
        "https://en.wikipedia.org/wiki/Hostname",
    )

    @classmethod
    def generate_invalid_yaml_error(
        cls,
        file_path: str,
        line_number: int | None = None,
        error_detail: str | None = None,
    ) -> EnhancedErrorMessage:
        """
        Generate enhanced error for invalid YAML.

        Args:
            file_path: Path to the invalid YAML file.
            line_number: Line number where error occurred.
            error_detail: Specific error detail from YAML parser.

        Returns:
            EnhancedErrorMessage with context and suggestions.

        """
        title, description, suggestions, doc_link = cls.INVALID_YAML_ERROR

        error_context = ErrorContext(
            error_type="yaml_parse_error",
            location=file_path,
            line_number=line_number,
        )

        if error_detail:
            description = f"{description}\n\nError: {error_detail}"

        return EnhancedErrorMessage(
            title=title.format(file=file_path),
            description=description,
            context=error_context,
            suggestions=suggestions,
            documentation_link=doc_link,
        )

    @classmethod
    def generate_invalid_ini_error(
        cls,
        file_path: str,
        line_number: int | None = None,
        error_detail: str | None = None,
    ) -> EnhancedErrorMessage:
        """
        Generate enhanced error for invalid INI.

        Args:
            file_path: Path to the invalid INI file.
            line_number: Line number where error occurred.
            error_detail: Specific error detail from INI parser.

        Returns:
            EnhancedErrorMessage with context and suggestions.

        """
        title, description, suggestions, doc_link = cls.INVALID_INI_ERROR

        error_context = ErrorContext(
            error_type="ini_parse_error",
            location=file_path,
            line_number=line_number,
        )

        if error_detail:
            description = f"{description}\n\nError: {error_detail}"

        return EnhancedErrorMessage(
            title=title.format(file=file_path),
            description=description,
            context=error_context,
            suggestions=suggestions,
            documentation_link=doc_link,
        )

    @classmethod
    def generate_missing_file_error(cls, file_path: str) -> EnhancedErrorMessage:
        """
        Generate enhanced error for missing file.

        Args:
            file_path: Path to the missing file.

        Returns:
            EnhancedErrorMessage with context and suggestions.

        """
        title, description, suggestions, doc_link = cls.MISSING_FILE_ERROR

        error_context = ErrorContext(
            error_type="file_not_found",
            location=file_path,
        )

        return EnhancedErrorMessage(
            title=title.format(file=file_path),
            description=description,
            context=error_context,
            suggestions=suggestions,
            documentation_link=doc_link,
        )

    @classmethod
    def generate_version_mismatch_error(
        cls,
        provided_version: str,
        valid_versions: list[str] | None = None,
    ) -> EnhancedErrorMessage:
        """
        Generate enhanced error for version mismatch.

        Args:
            provided_version: The version that was provided.
            valid_versions: List of valid versions if available.

        Returns:
            EnhancedErrorMessage with context and suggestions.

        """
        title, description, suggestions, doc_link = cls.VERSION_MISMATCH_ERROR

        error_context = ErrorContext(
            error_type="version_mismatch",
            location=f"Version: {provided_version}",
        )

        return EnhancedErrorMessage(
            title=title,
            description=description,
            context=error_context,
            suggestions=suggestions,
            documentation_link=doc_link,
        )

    @classmethod
    def generate_invalid_collection_name_error(cls, name: str) -> EnhancedErrorMessage:
        """
        Generate enhanced error for invalid collection name.

        Args:
            name: The invalid collection name.

        Returns:
            EnhancedErrorMessage with context and suggestions.

        """
        title, description, suggestions, doc_link = cls.INVALID_COLLECTION_NAME

        error_context = ErrorContext(
            error_type="invalid_collection_name",
            location=f"Collection: {name}",
        )

        return EnhancedErrorMessage(
            title=title,
            description=description,
            context=error_context,
            suggestions=suggestions,
            documentation_link=doc_link,
        )

    @classmethod
    def invalid_hostname(cls, hostname: str) -> EnhancedErrorMessage:
        """
        Generate enhanced error for invalid hostname.

        Args:
            hostname: The invalid hostname.

        Returns:
            EnhancedErrorMessage with context and suggestions.

        """
        title, description, suggestions, doc_link = cls.INVALID_HOST_NAME

        error_context = ErrorContext(
            error_type="invalid_hostname",
            location=f"Hostname: {hostname}",
        )

        return EnhancedErrorMessage(
            title=title,
            description=description,
            context=error_context,
            suggestions=suggestions,
            documentation_link=doc_link,
        )


def validate_collection_name(name: str) -> tuple[bool, str | None]:
    """
    Validate Ansible collection name format.

    Collection names must match: namespace.collection where both parts:
    - Start with a lowercase letter
    - Contain only lowercase letters, numbers, and underscores
    - Are 2-100 characters long

    Args:
        name: Collection name to validate.

    Returns:
        Tuple of (is_valid, error_message).

    """
    if not isinstance(name, str):
        error_msg = EnhancedErrorHandler.generate_invalid_collection_name_error(
            str(name)
        )
        return False, error_msg.format_message()

    # Check basic format
    if "." not in name:
        error = EnhancedErrorHandler.generate_invalid_collection_name_error(name)
        return False, error.format_message()

    parts = name.split(".")
    if len(parts) != 2:
        error = EnhancedErrorHandler.generate_invalid_collection_name_error(name)
        return False, error.format_message()

    namespace, collection = parts

    # Validate each part
    pattern = r"^[a-z][a-z0-9_]{1,99}$"
    if not re.match(pattern, namespace) or not re.match(pattern, collection):
        error = EnhancedErrorHandler.generate_invalid_collection_name_error(name)
        return False, error.format_message()

    return True, None


def validate_hostname(hostname: str) -> tuple[bool, str | None]:
    """
    Validate Ansible hostname format.

    Hostnames can be:
    - Valid DNS names (letters, digits, hyphens, dots)
    - Valid IPv4 addresses (x.x.x.x)
    - Valid IPv6 addresses

    Args:
        hostname: Hostname to validate.

    Returns:
        Tuple of (is_valid, error_message).

    """
    if not isinstance(hostname, str) or not hostname.strip():
        error = EnhancedErrorHandler.invalid_hostname(hostname)
        return False, error.format_message()

    # IPv4 pattern
    ipv4_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if re.match(ipv4_pattern, hostname):
        # Validate octets are in range 0-255
        parts = hostname.split(".")
        try:
            if all(0 <= int(part) <= 255 for part in parts):
                return True, None
        except ValueError:
            # Non-numeric octet; fall through to DNS validation.
            pass

    # DNS name pattern (simplified)
    dns_pattern = (
        r"^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)*"
        r"[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$"
    )
    if re.match(dns_pattern, hostname, re.IGNORECASE) and len(hostname) <= 255:
        return True, None

    error = EnhancedErrorHandler.invalid_hostname(hostname)
    return False, error.format_message()


def validate_ansible_version(version: str) -> tuple[bool, str | None]:
    """
    Validate Ansible version format and support status.

    Args:
        version: Version string to validate.

    Returns:
        Tuple of (is_valid, error_message).

    """
    valid_versions = [
        "2.9",
        "2.10",
        "2.11",
        "2.12",
        "2.13",
        "2.14",
        "2.15",
        "2.16",
        "2.17",
    ]

    # Check if version is in valid list
    if version in valid_versions:
        return True, None

    # Check basic semantic version format
    version_pattern = r"^\d+\.\d+(\.\d+)?$"
    if not re.match(version_pattern, version):
        error = EnhancedErrorHandler.generate_version_mismatch_error(
            version, valid_versions
        )
        return False, error.format_message()

    error = EnhancedErrorHandler.generate_version_mismatch_error(
        version, valid_versions
    )
    return False, error.format_message()
