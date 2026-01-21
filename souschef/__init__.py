"""SousChef: AI-powered Chef to Ansible converter."""

from pathlib import Path

import tomllib


# Read version from pyproject.toml
def _get_version() -> str:
    """Get version from pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    try:
        with pyproject_path.open("rb") as f:
            data = tomllib.load(f)
        version = data.get("tool", {}).get("poetry", {}).get("version")
        return str(version) if version else "unknown"
    except OSError:
        return "unknown"


__version__ = _get_version()

from souschef.assessment import (  # noqa: E402
    analyse_cookbook_dependencies,
    assess_chef_migration_complexity,
    generate_migration_plan,
    generate_migration_report,
    validate_conversion,
)
from souschef.deployment import (  # noqa: E402
    analyse_chef_application_patterns,
)

# Import server functions only if MCP is available
try:
    from souschef.server import (
        analyse_chef_search_patterns,
    )

    _server_available = True
except ImportError:
    _server_available = False

    # Define a placeholder function for when MCP is not available
    def analyse_chef_search_patterns(*args, **kwargs):
        raise NotImplementedError("MCP server not available")


__all__ = [
    "analyse_cookbook_dependencies",
    "assess_chef_migration_complexity",
    "generate_migration_plan",
    "generate_migration_report",
    "validate_conversion",
    "analyse_chef_application_patterns",
    "analyse_chef_search_patterns",
]
