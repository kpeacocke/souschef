"""Enhanced error handling with actionable messages and recovery suggestions."""

from pathlib import Path


class SousChefError(Exception):
    """Base exception for SousChef with enhanced error messages."""

    def __init__(self, message: str, suggestion: str | None = None):
        """
        Initialize with message and optional recovery suggestion.

        Args:
            message: The error message describing what went wrong.
            suggestion: Optional suggestion for how to fix the error.

        """
        self.message = message
        self.suggestion = suggestion
        full_message = message
        if suggestion:
            full_message = f"{message}\n\nSuggestion: {suggestion}"
        super().__init__(full_message)


class ChefFileNotFoundError(SousChefError):
    """Raised when a required file cannot be found."""

    def __init__(self, path: str, file_type: str = "file"):
        """
        Initialize file not found error.

        Args:
            path: The path that was not found.
            file_type: Type of file (e.g., 'cookbook', 'recipe', 'template').

        """
        message = f"Could not find {file_type}: {path}"
        suggestion = (
            "Check that the path exists and you have read permissions. "
            "For cookbooks, ensure you're pointing to the cookbook root "
            "directory containing metadata.rb."
        )
        super().__init__(message, suggestion)


class InvalidCookbookError(SousChefError):
    """Raised when a cookbook is invalid or malformed."""

    def __init__(self, path: str, reason: str):
        """
        Initialize invalid cookbook error.

        Args:
            path: The cookbook path.
            reason: Why the cookbook is invalid.

        """
        message = f"Invalid cookbook at {path}: {reason}"
        suggestion = (
            "Ensure the directory contains a valid Chef cookbook with "
            "metadata.rb. Run 'knife cookbook test' to validate the "
            "cookbook structure."
        )
        super().__init__(message, suggestion)


class ParseError(SousChefError):
    """Raised when parsing Chef code fails."""

    def __init__(
        self, file_path: str, line_number: int | None = None, detail: str = ""
    ):
        """
        Initialize parse error.

        Args:
            file_path: The file that failed to parse.
            line_number: Optional line number where parsing failed.
            detail: Additional detail about the parse failure.

        """
        location = f" at line {line_number}" if line_number else ""
        message = f"Failed to parse {file_path}{location}"
        if detail:
            message += f": {detail}"
        suggestion = (
            "Check that the file contains valid Chef Ruby DSL syntax. "
            "Complex Ruby code may require manual review."
        )
        super().__init__(message, suggestion)


class ConversionError(SousChefError):
    """Raised when conversion from Chef to Ansible fails."""

    def __init__(self, resource_type: str, reason: str):
        """
        Initialize conversion error.

        Args:
            resource_type: The Chef resource type that failed to convert.
            reason: Why the conversion failed.

        """
        message = f"Cannot convert Chef resource '{resource_type}': {reason}"
        suggestion = (
            "This resource may require manual conversion. Check the Ansible "
            "module documentation for equivalent modules, or consider using "
            "the 'command' or 'shell' module as a fallback."
        )
        super().__init__(message, suggestion)


class ValidationError(SousChefError):
    """Raised when validation of converted content fails."""

    def __init__(self, validation_type: str, issues: list[str]):
        """
        Initialize validation error.

        Args:
            validation_type: Type of validation that failed.
            issues: List of validation issues found.

        """
        issue_list = "\n  - ".join(issues)
        message = f"{validation_type} validation failed:\n  - {issue_list}"
        suggestion = (
            "Review the validation issues above and fix them in the "
            "generated output. Run the validation again after making "
            "corrections."
        )
        super().__init__(message, suggestion)


def validate_file_exists(path: str, file_type: str = "file") -> Path:
    """
    Validate that a file exists and is readable.

    Args:
        path: Path to validate.
        file_type: Type of file for error messages.

    Returns:
        Path object if validation succeeds.

    Raises:
        FileNotFoundError: If file doesn't exist or isn't readable.

    """
    file_path = Path(path)
    if not file_path.exists():
        raise ChefFileNotFoundError(path, file_type)
    if not file_path.is_file():
        raise ChefFileNotFoundError(path, file_type)
    try:
        # Test readability
        with file_path.open() as f:
            f.read(1)
    except PermissionError as e:
        raise SousChefError(
            f"Permission denied reading {file_type}: {path}",
            "Ensure you have read permissions on the file. On Unix systems, "
            "try 'chmod +r' on the file.",
        ) from e
    return file_path


def validate_directory_exists(path: str, dir_type: str = "directory") -> Path:
    """
    Validate that a directory exists and is readable.

    Args:
        path: Path to validate.
        dir_type: Type of directory for error messages.

    Returns:
        Path object if validation succeeds.

    Raises:
        FileNotFoundError: If directory doesn't exist or isn't readable.

    """
    dir_path = Path(path)
    if not dir_path.exists():
        raise ChefFileNotFoundError(path, dir_type)
    if not dir_path.is_dir():
        raise SousChefError(
            f"Path is not a {dir_type}: {path}",
            f"Expected a directory but found a file. Check that you're "
            f"pointing to the {dir_type} directory, not a file within it.",
        )
    try:
        # Test readability
        list(dir_path.iterdir())
    except PermissionError as e:
        raise SousChefError(
            f"Permission denied reading {dir_type}: {path}",
            "Ensure you have read and execute permissions on the directory. "
            "On Unix systems, try 'chmod +rx' on the directory.",
        ) from e
    return dir_path


def validate_cookbook_structure(path: str) -> Path:
    """
    Validate that a path contains a valid Chef cookbook.

    Args:
        path: Path to the cookbook root directory.

    Returns:
        Path object if validation succeeds.

    Raises:
        InvalidCookbookError: If the directory isn't a valid cookbook.

    """
    cookbook_path = validate_directory_exists(path, "cookbook")

    # Check for metadata.rb or metadata.json
    has_metadata = (cookbook_path / "metadata.rb").exists() or (
        cookbook_path / "metadata.json"
    ).exists()

    if not has_metadata:
        raise InvalidCookbookError(
            path, "No metadata.rb or metadata.json found in cookbook root"
        )

    return cookbook_path


def format_error_with_context(
    error: Exception, operation: str, file_path: str | None = None
) -> str:
    """
    Format an error message with operation context.

    Args:
        error: The exception that occurred.
        operation: Description of the operation that failed.
        file_path: Optional path to the file being processed.

    Returns:
        Formatted error message with context and suggestions.

    """
    if isinstance(error, SousChefError):
        # Already has good formatting
        return str(error)

    context = f"Error during {operation}"
    if file_path:
        context += f" for {file_path}"

    if isinstance(error, FileNotFoundError):
        return str(ChefFileNotFoundError(file_path or "unknown", "file"))
    elif isinstance(error, PermissionError):
        return (
            f"{context}: Permission denied\n\nSuggestion: Check "
            "file/directory permissions and ensure you have read access."
        )
    elif isinstance(error, (ValueError, TypeError)):
        return (
            f"{context}: {error}\n\nSuggestion: Check that input "
            "values are in the correct format and type."
        )
    else:
        return (
            f"{context}: {error}\n\nSuggestion: If this error persists, "
            "please report it with the full error message at "
            "https://github.com/kpeacocke/souschef/issues"
        )
