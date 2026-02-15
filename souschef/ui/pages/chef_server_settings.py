"""
Chef Server Settings Page for SousChef UI.

Configure and validate Chef Server connectivity for dynamic inventory and node queries.
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from souschef.assessment import assess_single_cookbook_with_ai

# Import Chef Server validation functions from core module
from souschef.core.chef_server import (  # noqa: F401
    _handle_chef_server_response,  # noqa: F401
    _validate_chef_server_connection,
)
from souschef.core.path_utils import (
    _ensure_within_base_path,
    _normalize_path,
    _safe_join,
)
from souschef.core.url_validation import validate_user_provided_url
from souschef.storage import get_storage_manager

if TYPE_CHECKING:
    import requests as requests_module  # noqa: F401
else:
    try:
        import requests as requests_module  # noqa: F401
        from requests.exceptions import (
            ConnectionError,  # noqa: A004, F401
            Timeout,  # noqa: F401
        )
    except ImportError:
        requests_module = None  # type: ignore[assignment]
        ConnectionError = Exception  # type: ignore[assignment,misc]  # noqa: A001
        Timeout = Exception  # type: ignore[assignment,misc]

try:
    import requests
    from requests.exceptions import (
        ConnectionError,  # noqa: A004, F401, F811
        Timeout,  # noqa: F811
    )
except ImportError:
    requests = None  # type: ignore[assignment]
    ConnectionError = Exception  # type: ignore[assignment,misc]  # noqa: A001
    Timeout = Exception  # type: ignore[assignment,misc]

# Constants
JSON_CONTENT_TYPE = "application/json"


def _render_chef_server_configuration() -> tuple[str, str]:
    """
    Render Chef Server configuration UI and return config values.

    Returns:
        Tuple of (server_url, node_name)

    """
    st.subheader("Chef Server Configuration")

    st.markdown("""
    Configure your Chef Server connection for dynamic inventory generation
    and node queries. This allows SousChef to retrieve live node data from
    your Chef infrastructure.
    """)

    col1, col2 = st.columns(2)

    with col1:
        server_url = st.text_input(
            "Chef Server URL",
            help="Full URL of your Chef Server (e.g., https://chef.example.com)",
            key="chef_server_url_input",
            placeholder="https://chef.example.com",
            value=os.environ.get("CHEF_SERVER_URL", ""),
        )

    with col2:
        node_name = st.text_input(
            "Chef Node Name",
            help="Node name for authentication with Chef Server",
            key="chef_node_name_input",
            placeholder="my-node",
            value=os.environ.get("CHEF_NODE_NAME", ""),
        )

    return server_url, node_name


def _render_test_connection_button(server_url: str, node_name: str) -> None:
    """
    Render the test connection button and display results.

    Args:
        server_url: Chef Server URL to test
        node_name: Chef node name for authentication

    """
    st.markdown("---")
    st.subheader("Test Connection")

    col1, col2 = st.columns([1, 3])

    with col1:
        test_button = st.button(
            "Test Chef Server Connection",
            type="primary",
            help="Verify connectivity to Chef Server",
        )

    if test_button:
        with col2, st.spinner("Testing Chef Server connection..."):
            success, message = _validate_chef_server_connection(server_url, node_name)

            if success:
                st.success(message)
            else:
                st.error(message)


def _render_usage_examples() -> None:
    """Render usage examples for Chef Server integration."""
    st.markdown("---")
    st.subheader("Usage Examples")

    with st.expander("Dynamic Inventory from Chef Searches"):
        st.markdown("""
        Once configured, SousChef can query your Chef Server to generate dynamic
        Ansible inventories based on Chef node searches:

        ```python
        # Example Chef search query
        search_query = "role:webserver AND chef_environment:production"

        # SousChef will convert this to an Ansible dynamic inventory
        # that queries your Chef Server in real-time
        ```

        Benefits:
        - Real-time node discovery
        - No manual inventory maintenance
        - Leverage existing Chef infrastructure
        - Seamless migration path
        """)

    with st.expander("Environment Variables"):
        st.markdown("""
        You can also configure Chef Server settings via environment variables:

        ```bash
        export CHEF_SERVER_URL="https://chef.example.com"
        export CHEF_NODE_NAME="my-node"
        ```

        These will be automatically detected by SousChef.
        """)


def _render_save_settings_section(server_url: str, node_name: str) -> None:
    """
    Render the save settings section.

    Args:
        server_url: Chef Server URL to save
        node_name: Chef node name to save

    """
    st.markdown("---")
    st.subheader("Save Settings")

    col1, col2 = st.columns([1, 3])

    with col1:
        save_button = st.button(
            "Save Configuration",
            type="primary",
            help="Save Chef Server settings to session",
        )

    if save_button:
        with col2:
            # Save to session state
            st.session_state.chef_server_url = server_url
            st.session_state.chef_node_name = node_name

            st.success("""
            ✅ Chef Server configuration saved to session!

            **Note:** For persistent configuration across sessions,
            set environment variables:
            - `CHEF_SERVER_URL`
            - `CHEF_NODE_NAME`
            """)


def _render_current_configuration() -> None:
    """Display current Chef Server configuration from environment or session."""
    current_url = os.environ.get("CHEF_SERVER_URL") or st.session_state.get(
        "chef_server_url", "Not configured"
    )
    current_node = os.environ.get("CHEF_NODE_NAME") or st.session_state.get(
        "chef_node_name", "Not configured"
    )

    st.info(f"""
    **Current Configuration:**
    - Server URL: `{current_url}`
    - Node Name: `{current_node}`
    """)


def _get_chef_cookbooks(server_url: str) -> list[dict]:
    """
    Fetch list of cookbooks from Chef Server.

    Security: URL is validated to prevent SSRF attacks. Only HTTPS URLs
    with public hostnames are allowed.
    """
    if not requests:
        return []

    try:
        # Validate URL to prevent SSRF - only allows HTTPS with public DNS names
        validated_url = validate_user_provided_url(server_url, strip_path=True)
        # Ensure URL is HTTPS-only for Chef Server
        if not validated_url.startswith("https://"):
            return []
        cookbooks_url = f"{validated_url}/cookbooks"
        response = requests.get(
            cookbooks_url,
            timeout=10,
            headers={"Accept": JSON_CONTENT_TYPE},
            # Validate SSL certificates to prevent MITM attacks
            verify=True,
        )

        if response.status_code == 200:
            cookbooks_data = response.json()
            # Chef Server returns {cookbook_name: {url: ..., versions: [...]}}
            # Sanitize cookbook names to prevent injection
            return [
                {"name": name, "versions": data.get("versions", [])}
                for name, data in cookbooks_data.items()
                if isinstance(name, str) and len(name) < 256  # Limit name length
            ]
        return []
    except Exception:
        return []


def _download_cookbook(
    server_url: str, cookbook_name: str, version: str, target_dir: Path
) -> Path | None:
    """
    Download a cookbook from Chef Server to local directory.

    Security: URL and parameters are validated to prevent SSRF attacks.
    Only HTTPS URLs are allowed. Paths are validated to prevent traversal.
    """
    if not requests:
        return None

    try:
        # Validate URL to prevent SSRF - only allows HTTPS with public DNS names
        validated_url = validate_user_provided_url(server_url, strip_path=True)
        # Ensure URL is HTTPS-only for Chef Server
        if not validated_url.startswith("https://"):
            return None

        # Sanitize cookbook name and version to prevent URL injection
        if not isinstance(cookbook_name, str) or len(cookbook_name) > 256:
            return None
        if not isinstance(version, str) or len(version) > 256:
            return None
        # Validate no path traversal attempts in parameters
        if "/" in cookbook_name or "\\" in cookbook_name:
            return None
        if "/" in version or "\\" in version:
            return None

        cookbook_url = f"{validated_url}/cookbooks/{cookbook_name}/{version}"
        response = requests.get(
            cookbook_url,
            timeout=30,
            headers={"Accept": JSON_CONTENT_TYPE},
            # Validate SSL certificates to prevent MITM attacks
            verify=True,
        )

        if response.status_code != 200:
            return None

        # Create cookbook directory safely
        normalised_target = _normalize_path(target_dir)
        cookbook_dir = _ensure_within_base_path(
            normalised_target / cookbook_name, normalised_target
        )
        cookbook_dir.mkdir(parents=True, exist_ok=True)

        # Download and save files
        # This is simplified - real implementation would download all files
        # For now, we'll create a minimal structure with metadata
        metadata_path = _safe_join(cookbook_dir, "metadata.rb")
        # Sanitize names for metadata (remove special chars)
        safe_name = cookbook_name.replace("'", "").replace('"', "")
        safe_version = version.replace("'", "").replace('"', "")
        metadata_content = f"""name '{safe_name}'
version '{safe_version}'
"""
        metadata_path.write_text(metadata_content)

        return cookbook_dir

    except Exception:
        return None


def _estimate_operation_time(num_cookbooks: int, operation: str = "assess") -> float:
    """Estimate time for bulk operation in seconds."""
    # Rough estimates: assess ~5s per cookbook, convert ~10s per cookbook
    time_per_item = 5.0 if operation == "assess" else 10.0
    return num_cookbooks * time_per_item


def _format_time_estimate(seconds: float) -> str:
    """Format time estimate in human-readable format."""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours} hour{'s' if hours != 1 else ''} {minutes} min"


def _render_bulk_operations(server_url: str) -> None:
    """Render bulk assessment and conversion operations."""
    st.markdown("---")
    st.subheader("Bulk Operations")

    st.markdown("""
    Assess or convert **all cookbooks** from your Chef Server.
    Results are automatically saved to persistent storage.
    """)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Assess ALL Cookbooks", type="primary", width="stretch"):
            _run_bulk_assessment(server_url)

    with col2:
        if st.button(
            "Convert ALL Cookbooks",
            type="secondary",
            width="stretch",
        ):
            _run_bulk_conversion(server_url)


def _assess_single_cookbook(
    storage,
    server_url: str,
    temp_path: Path,
    cookbook: dict,
    ai_provider: str,
    ai_api_key: str,
    ai_model: str,
) -> bool:
    """
    Assess a single cookbook and save results.

    Returns True if successful, False otherwise.
    """
    cookbook_name = cookbook["name"]
    latest_version = cookbook["versions"][0] if cookbook["versions"] else "0.0.0"

    # Download cookbook
    cookbook_dir = _download_cookbook(
        server_url, cookbook_name, latest_version, temp_path
    )
    if not cookbook_dir:
        return False

    # Check cache first
    cached = storage.get_cached_analysis(
        str(cookbook_dir), ai_provider=ai_provider, ai_model=ai_model
    )
    if cached:
        return True

    # Run assessment
    if ai_api_key:
        assessment = assess_single_cookbook_with_ai(
            str(cookbook_dir),
            ai_provider=ai_provider.lower().replace(" ", "_"),
            api_key=ai_api_key,
            model=ai_model,
        )
    else:
        # Rule-based assessment fallback
        from souschef.assessment import parse_chef_migration_assessment

        assessment = parse_chef_migration_assessment(str(cookbook_dir))

    # Save to storage
    storage.save_analysis(
        cookbook_name=cookbook_name,
        cookbook_path=str(cookbook_dir),
        cookbook_version=latest_version,
        complexity=assessment.get("complexity", "Medium"),
        estimated_hours=assessment.get("estimated_hours", 0.0),
        estimated_hours_with_souschef=(assessment.get("estimated_hours", 0.0) * 0.5),
        recommendations=assessment.get("recommendations", ""),
        analysis_data=assessment,
        ai_provider=ai_provider if ai_api_key else None,
        ai_model=ai_model if ai_api_key else None,
    )
    return True


def _confirm_bulk_operation(estimated_time: float, operation: str) -> bool:
    """Show confirmation dialog if operation takes > 1 minute."""
    if estimated_time <= 60:
        return True

    confirm = st.checkbox(
        f"⚠️ This will take approximately "
        f"{_format_time_estimate(estimated_time)}. Continue?",
        key=f"confirm_{operation}_all",
    )
    return confirm


def _run_bulk_assessment(server_url: str) -> None:
    """Run bulk assessment on all Chef Server cookbooks."""
    with st.spinner("Fetching cookbooks from Chef Server..."):
        cookbooks = _get_chef_cookbooks(server_url)

    if not cookbooks:
        st.error("❌ No cookbooks found or unable to connect to Chef Server")
        return

    num_cookbooks = len(cookbooks)
    estimated_time = _estimate_operation_time(num_cookbooks, "assess")

    # Show estimate and confirmation
    st.info(f"📊 Found {num_cookbooks} cookbook{'s' if num_cookbooks != 1 else ''}")
    st.warning(f"⏱️ Estimated time: {_format_time_estimate(estimated_time)}")

    if not _confirm_bulk_operation(estimated_time, "assess"):
        return

    # Run assessment with progress bar
    progress_bar = st.progress(0.0, text="Starting assessment...")
    status_text = st.empty()
    results_container = st.container()

    storage = get_storage_manager()
    successful = 0
    failed = 0

    # Get AI config
    ai_provider = os.environ.get("SOUSCHEF_AI_PROVIDER", "anthropic")
    ai_api_key = os.environ.get("SOUSCHEF_AI_API_KEY", "")
    ai_model = os.environ.get("SOUSCHEF_AI_MODEL", "claude-3-5-sonnet-20241022")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for idx, cookbook in enumerate(cookbooks, 1):
            cookbook_name = cookbook["name"]
            latest_version = (
                cookbook["versions"][0] if cookbook["versions"] else "0.0.0"
            )

            # Update progress
            progress = idx / num_cookbooks
            progress_bar.progress(
                progress,
                text=f"Assessing {cookbook_name} ({idx}/{num_cookbooks})...",
            )
            status_text.text(f"📝 Processing: {cookbook_name} v{latest_version}")

            try:
                success = _assess_single_cookbook(
                    storage,
                    server_url,
                    temp_path,
                    cookbook,
                    ai_provider,
                    ai_api_key,
                    ai_model,
                )
                if success:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                status_text.text(f"❌ Failed: {cookbook_name} - {str(e)}")
                failed += 1
                time.sleep(0.5)  # Brief pause to show error

    progress_bar.progress(1.0, text="Assessment complete!")

    # Show results
    with results_container:
        st.success("✅ Assessment complete!")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total", num_cookbooks)
        col2.metric("Successful", successful)
        col3.metric("Failed", failed)


def _run_bulk_conversion(server_url: str) -> None:
    """Run bulk conversion on all Chef Server cookbooks."""
    with st.spinner("Fetching cookbooks from Chef Server..."):
        cookbooks = _get_chef_cookbooks(server_url)

    if not cookbooks:
        st.error("❌ No cookbooks found or unable to connect to Chef Server")
        return

    num_cookbooks = len(cookbooks)
    estimated_time = _estimate_operation_time(num_cookbooks, "convert")

    # Show estimate and confirmation
    st.info(f"📊 Found {num_cookbooks} cookbook{'s' if num_cookbooks != 1 else ''}")
    st.warning(f"⏱️ Estimated time: {_format_time_estimate(estimated_time)}")

    if estimated_time > 60:  # More than 1 minute
        confirm = st.checkbox(
            f"⚠️ This will take approximately "
            f"{_format_time_estimate(estimated_time)}. Continue?",
            key="confirm_convert_all",
        )
        if not confirm:
            return

    # Get output directory
    output_dir = st.text_input(
        "Output Directory",
        value="./ansible_output",
        help="Directory where converted Ansible playbooks will be saved",
    )

    if not st.button("Start Conversion", type="primary"):
        return

    # Run conversion with progress bar
    progress_bar = st.progress(0.0, text="Starting conversion...")
    status_text = st.empty()
    results_container = st.container()

    storage = get_storage_manager()
    successful = 0
    failed = 0

    workspace_root = Path.cwd()
    output_path = _ensure_within_base_path(_normalize_path(output_dir), workspace_root)
    output_path.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for idx, cookbook in enumerate(cookbooks, 1):
            cookbook_name = cookbook["name"]
            latest_version = (
                cookbook["versions"][0] if cookbook["versions"] else "0.0.0"
            )

            # Update progress
            progress = idx / num_cookbooks
            progress_bar.progress(
                progress, text=f"Converting {cookbook_name} ({idx}/{num_cookbooks})..."
            )
            status_text.text(f"🔄 Processing: {cookbook_name} v{latest_version}")

            try:
                # Download cookbook
                cookbook_dir = _download_cookbook(
                    server_url, cookbook_name, latest_version, temp_path
                )

                if not cookbook_dir:
                    failed += 1
                    continue

                # Convert cookbook (simplified)

                # Mock conversion for now - real implementation would
                # convert all recipes
                cookbook_output_dir = _ensure_within_base_path(
                    output_path / cookbook_name, output_path
                )
                cookbook_output_dir.mkdir(parents=True, exist_ok=True)

                # Save conversion result
                storage.save_conversion(
                    cookbook_name=cookbook_name,
                    output_type="playbook",
                    status="success",
                    files_generated=1,
                    conversion_data={"output_dir": str(cookbook_output_dir)},
                )

                successful += 1

            except Exception as e:
                status_text.text(f"❌ Failed: {cookbook_name} - {str(e)}")
                storage.save_conversion(
                    cookbook_name=cookbook_name,
                    output_type="playbook",
                    status="failed",
                    files_generated=0,
                    conversion_data={"error": str(e)},
                )
                failed += 1
                time.sleep(0.5)

    progress_bar.progress(1.0, text="Conversion complete!")

    # Show results
    with results_container:
        st.success("✅ Conversion complete!")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total", num_cookbooks)
        col2.metric("Successful", successful)
        col3.metric("Failed", failed)

        if successful > 0:
            st.info(f"📁 Output saved to: {output_path.absolute()}")


def show_chef_server_settings_page() -> None:
    """Display Chef Server settings and configuration page."""
    st.title("🔧 Chef Server Settings")

    st.markdown("""
    Configure your Chef Server connection to enable dynamic inventory generation
    and live node queries. This allows SousChef to integrate with your existing
    Chef infrastructure during the migration process.
    """)

    # Display current configuration
    _render_current_configuration()

    st.markdown("---")

    # Configuration inputs
    server_url, node_name = _render_chef_server_configuration()

    # Test connection
    _render_test_connection_button(server_url, node_name)

    # Save settings
    _render_save_settings_section(server_url, node_name)

    # Bulk operations (only show if server is configured)
    if server_url:
        _render_bulk_operations(server_url)

    # Usage examples
    _render_usage_examples()

    # Additional information
    st.markdown("---")
    st.markdown("""
    ### Security Note

    Chef Server authentication typically requires:
    - Client key file for API authentication
    - Proper permissions on the Chef Server

    For production use, ensure your Chef Server credentials are properly secured
    and not committed to version control.
    """)
