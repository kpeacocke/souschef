"""
Chef Server Settings Page for SousChef UI.

Configure and validate Chef Server connectivity for dynamic inventory and node queries.
"""

import os

import streamlit as st

try:
    import requests
    from requests.exceptions import (
        ConnectionError,  # noqa: A004
        Timeout,
    )
except ImportError:
    requests = None  # type: ignore[assignment]
    ConnectionError = Exception  # type: ignore[misc,assignment]  # noqa: A001
    Timeout = Exception  # type: ignore[assignment]


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

    if not server_url or not server_url.startswith("http"):
        return False, "Invalid server URL - must start with http:// or https://"

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

        if response.status_code == 200:
            return True, f"✅ Successfully connected to Chef Server at {server_url}"
        elif response.status_code == 401:
            return (
                False,
                "❌ Authentication failed - check your Chef Server credentials",
            )
        elif response.status_code == 404:
            return False, "❌ Chef Server search endpoint not found"
        else:
            return (
                False,
                f"❌ Connection failed with status code {response.status_code}",
            )

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
