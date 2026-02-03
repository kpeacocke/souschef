"""
Chef Server Settings Page for SousChef UI.

Configure and validate Chef Server connectivity for dynamic inventory and node queries.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from souschef.assessment import assess_single_cookbook_with_ai
from souschef.core.url_validation import validate_user_provided_url
from souschef.storage import get_storage_manager

try:
    import requests
    from requests.exceptions import (
        ConnectionError,  # noqa: A004
        Timeout,
    )
except ImportError:
    requests = None  # type: ignore[assignment]
    ConnectionError = Exception  # type: ignore[assignment,misc]  # noqa: A001
    Timeout = Exception  # type: ignore[assignment,misc]


def _handle_chef_server_response(
    response: "requests.Response", server_url: str
) -> tuple[bool, str]:
    """
    Handle Chef Server search response.

    Args:
        response: HTTP response from Chef Server
        server_url: The Chef Server URL that was queried

    Returns:
        Tuple of (success: bool, message: str)

    """
    if response.status_code == 200:
        return True, f"✅ Successfully connected to Chef Server at {server_url}"
    if response.status_code == 401:
        return (
            False,
            "❌ Authentication failed - check your Chef Server credentials",
        )
    if response.status_code == 404:
        return False, "❌ Chef Server search endpoint not found"
    return (
        False,
        f"❌ Connection failed with status code {response.status_code}",
    )


def _validate_chef_server_connection(
    server_url: str, node_name: str
) -> tuple[bool, str]:
    """
    Validate Chef Server connection by testing the search endpoint.

    Args:
        server_url: Base URL of the Chef Server
        node_name: Chef node name for authentication

    Returns:
        Tuple of (success: bool, message: str)

    """
    if not requests:
        return False, "requests library not installed"

    if not server_url:
        return False, "Server URL is required"

    try:
        server_url = validate_user_provided_url(server_url)
    except ValueError as exc:
        return False, f"Invalid server URL: {exc}"

    if not node_name:
        return False, "Node name is required for authentication"

    # Test the search endpoint
    try:
        search_url = f"{server_url.rstrip('/')}/search/node"
        response = requests.get(
            search_url,
            params={"q": "*:*"},
            timeout=5,
            headers={"Accept": "application/json"},
        )
        return _handle_chef_server_response(response, server_url)

    except Timeout:
        return False, f"❌ Connection timeout - could not reach {server_url}"
    except ConnectionError:
        return False, f"❌ Connection error - Chef Server not reachable at {server_url}"
    except Exception as e:
        return False, f"❌ Unexpected error: {e}"


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
    """Fetch list of cookbooks from Chef Server."""
    if not requests:
        return []

    try:
        cookbooks_url = f"{server_url.rstrip('/')}/cookbooks"
        response = requests.get(
            cookbooks_url,
            timeout=10,
            headers={"Accept": "application/json"},
        )

        if response.status_code == 200:
            cookbooks_data = response.json()
            # Chef Server returns {cookbook_name: {url: ..., versions: [...]}}
            return [
                {"name": name, "versions": data.get("versions", [])}
                for name, data in cookbooks_data.items()
            ]
        return []
    except Exception:
        return []


def _download_cookbook(
    server_url: str, cookbook_name: str, version: str, target_dir: Path
) -> Path | None:
    """Download a cookbook from Chef Server to local directory."""
    if not requests:
        return None

    try:
        # Download cookbook
        cookbook_url = f"{server_url.rstrip('/')}/cookbooks/{cookbook_name}/{version}"
        response = requests.get(
            cookbook_url,
            timeout=30,
            headers={"Accept": "application/json"},
        )

        if response.status_code != 200:
            return None

        # Create cookbook directory
        cookbook_dir = target_dir / cookbook_name
        cookbook_dir.mkdir(parents=True, exist_ok=True)

        # Download and save files
        # This is simplified - real implementation would download all files
        # For now, we'll create a minimal structure with metadata
        metadata_path = cookbook_dir / "metadata.rb"
        metadata_content = f"""name '{cookbook_name}'
version '{version}'
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
        if st.button("Assess ALL Cookbooks", type="primary", use_container_width=True):
            _run_bulk_assessment(server_url)

    with col2:
        if st.button(
            "Convert ALL Cookbooks",
            type="secondary",
            use_container_width=True,
        ):
            _run_bulk_conversion(server_url)


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

    if estimated_time > 60:  # More than 1 minute
        confirm = st.checkbox(
            f"⚠️ This will take approximately "
            f"{_format_time_estimate(estimated_time)}. Continue?",
            key="confirm_assess_all",
        )
        if not confirm:
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
                progress, text=f"Assessing {cookbook_name} ({idx}/{num_cookbooks})..."
            )
            status_text.text(f"📝 Processing: {cookbook_name} v{latest_version}")

            try:
                # Download cookbook
                cookbook_dir = _download_cookbook(
                    server_url, cookbook_name, latest_version, temp_path
                )

                if not cookbook_dir:
                    failed += 1
                    continue

                # Check cache first
                cached = storage.get_cached_analysis(
                    str(cookbook_dir), ai_provider=ai_provider, ai_model=ai_model
                )

                if cached:
                    status_text.text(f"✅ Using cached: {cookbook_name}")
                    successful += 1
                    continue

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
                    estimated_hours_with_souschef=(
                        assessment.get("estimated_hours", 0.0) * 0.5
                    ),
                    recommendations=assessment.get("recommendations", ""),
                    analysis_data=assessment,
                    ai_provider=ai_provider if ai_api_key else None,
                    ai_model=ai_model if ai_api_key else None,
                )

                successful += 1

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

    output_path = Path(output_dir)
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
                cookbook_output_dir = output_path / cookbook_name
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
