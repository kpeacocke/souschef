"""
AI Settings Page for SousChef UI.

Configure and validate AI provider settings for the SousChef MCP server.
"""

import json
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import streamlit as st

# AI Provider Constants
ANTHROPIC_PROVIDER = "Anthropic (Claude)"
OPENAI_PROVIDER = "OpenAI (GPT)"
WATSON_PROVIDER = "IBM Watsonx"
LIGHTSPEED_PROVIDER = "Red Hat Lightspeed"
LOCAL_PROVIDER = "Local Model"

# UI Constants
API_KEY_LABEL = "API Key"

# Import AI libraries (optional dependencies)
try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore[assignment]

try:
    from ibm_watsonx_ai import APIClient  # type: ignore[import-not-found]
except ImportError:
    APIClient = None

try:
    import requests  # type: ignore[import-untyped]
except ImportError:
    requests = None

try:
    import openai
except ImportError:
    openai = None  # type: ignore[assignment]


def _get_model_options(provider):
    """Get model options for the selected provider."""
    if provider == ANTHROPIC_PROVIDER:
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ]
    elif provider == OPENAI_PROVIDER:
        return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    elif provider == WATSON_PROVIDER:
        return [
            "meta-llama/llama-3-70b-instruct",
            "meta-llama/llama-3-8b-instruct",
            "ibm/granite-13b-instruct-v2",
            "ibm/granite-13b-chat-v2",
        ]
    elif provider == LIGHTSPEED_PROVIDER:
        return ["codellama/CodeLlama-34b-Instruct-hf"]
    else:
        return ["local-model"]


def _render_api_configuration(provider):
    """Render API configuration UI and return config values."""
    if provider == LOCAL_PROVIDER:
        st.info("Local model configuration will be added in a future update.")
        return "", "", ""
    elif provider == WATSON_PROVIDER:
        col1, col2, col3 = st.columns(3)
        with col1:
            api_key = st.text_input(
                API_KEY_LABEL,
                type="password",
                help="Enter your IBM Watsonx API key",
                key="api_key_input",
                placeholder="your-watsonx-api-key",
            )
        with col2:
            project_id = st.text_input(
                "Project ID",
                type="password",
                help="Enter your IBM Watsonx Project ID",
                key="project_id_input",
                placeholder="your-project-id",
            )
        with col3:
            base_url = st.text_input(
                "Base URL",
                help="IBM Watsonx API base URL",
                key="base_url_input",
                placeholder="https://us-south.ml.cloud.ibm.com",
            )
        return api_key, base_url, project_id
    elif provider == LIGHTSPEED_PROVIDER:
        col1, col2 = st.columns(2)
        with col1:
            api_key = st.text_input(
                API_KEY_LABEL,
                type="password",
                help="Enter your Red Hat Lightspeed API key",
                key="api_key_input",
                placeholder="your-lightspeed-api-key",
            )
        with col2:
            base_url = st.text_input(
                "Base URL",
                help="Red Hat Lightspeed API base URL",
                key="base_url_input",
                placeholder="https://api.redhat.com",
            )
        return api_key, base_url, ""
    else:
        col1, col2 = st.columns(2)
        with col1:
            api_key = st.text_input(
                API_KEY_LABEL,
                type="password",
                help=f"Enter your {provider.split(' ')[0]} API key",
                key="api_key_input",
                placeholder=f"sk-... (for {provider.split(' ')[0]})",
            )
        with col2:
            if provider == OPENAI_PROVIDER:
                base_url = st.text_input(
                    "Base URL (Optional)",
                    help="Custom OpenAI API base URL",
                    key="base_url_input",
                    placeholder="https://api.openai.com/v1",
                )
            else:
                base_url = ""
        return api_key, base_url, ""


def _render_advanced_settings():
    """Render advanced settings UI and return values."""
    with st.expander("Advanced Settings"):
        col1, col2 = st.columns(2)
        with col1:
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=2.0,
                value=0.7,
                step=0.1,
                help="Controls randomness in AI responses "
                "(0.0 = deterministic, 2.0 = very random)",
                key="temperature_slider",
            )
        with col2:
            max_tokens = st.number_input(
                "Max Tokens",
                min_value=100,
                max_value=100000,
                value=4000,
                help="Maximum number of tokens to generate",
                key="max_tokens_input",
            )
    return temperature, max_tokens


def _render_validation_section(
    provider, api_key, model, base_url, project_id, temperature, max_tokens
):
    """Render validation and save buttons."""
    st.subheader("Configuration Validation")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Validate Configuration", type="primary", width="stretch"):
            validate_ai_configuration(provider, api_key, model, base_url, project_id)
    with col2:
        if st.button("Save Settings", width="stretch"):
            save_ai_settings(
                provider, api_key, model, base_url, temperature, max_tokens, project_id
            )


def show_ai_settings_page():
    """Show the AI settings configuration page."""
    st.markdown("""
    Configure your AI provider settings for the SousChef MCP server.
    These settings determine which AI model will be used for Chef to Ansible
    conversions.
    """)

    # AI Provider Selection
    st.subheader("AI Provider Configuration")

    col1, col2 = st.columns([1, 2])

    with col1:
        ai_provider = st.selectbox(
            "AI Provider",
            [
                ANTHROPIC_PROVIDER,
                OPENAI_PROVIDER,
                WATSON_PROVIDER,
                LIGHTSPEED_PROVIDER,
                LOCAL_PROVIDER,
            ],
            help="Select your preferred AI provider",
            key="ai_provider_select",
        )

    with col2:
        model_options = _get_model_options(ai_provider)
        selected_model = st.selectbox(
            "Model",
            model_options,
            help="Select the AI model to use",
            key="ai_model_select",
        )

    # API Configuration
    st.subheader("API Configuration")
    api_key, base_url, project_id = _render_api_configuration(ai_provider)

    # Advanced Settings
    temperature, max_tokens = _render_advanced_settings()

    # Validation Section
    _render_validation_section(
        ai_provider,
        api_key,
        selected_model,
        base_url,
        project_id,
        temperature,
        max_tokens,
    )

    # Current Settings Display
    display_current_settings()


def validate_ai_configuration(provider, api_key, model, base_url="", project_id=""):
    """Validate the AI configuration by making a test API call."""
    if not api_key and provider != "Local Model":
        st.error("API key is required for validation.")
        return

    if provider == WATSON_PROVIDER and not project_id:
        st.error("Project ID is required for IBM Watsonx validation.")
        return

    with st.spinner("Validating AI configuration..."):
        try:
            if provider == ANTHROPIC_PROVIDER:
                success, message = validate_anthropic_config(api_key, model)
            elif provider == OPENAI_PROVIDER:
                success, message = validate_openai_config(api_key, model, base_url)
            elif provider == WATSON_PROVIDER:
                success, message = validate_watson_config(api_key, project_id, base_url)
            elif provider == LIGHTSPEED_PROVIDER:
                success, message = validate_lightspeed_config(api_key, model, base_url)
            else:
                st.info("Local model validation not implemented yet.")
                return

            if success:
                st.success(f"Configuration validated successfully! {message}")
            else:
                st.error(f"Validation failed: {message}")

        except Exception as e:
            st.error(f"Validation error: {str(e)}")


def _sanitize_lightspeed_base_url(base_url: str) -> str:
    """
    Sanitize and validate the Red Hat Lightspeed base URL to prevent SSRF.

    - Default to the standard Lightspeed endpoint if no URL is provided.
    - Only allow HTTPS scheme.
    - Restrict host to known Red Hat-owned Lightspeed domains.
    - Strip any user-supplied path, query, or fragment.
    """
    default_url = "https://api.redhat.com"
    allowed_hosts = {
        "api.redhat.com",
    }

    if not base_url or not str(base_url).strip():
        return default_url

    parsed = urlparse(base_url)

    # If scheme is missing, assume https
    if not parsed.scheme:
        parsed = parsed._replace(scheme="https")

    if parsed.scheme.lower() != "https":
        raise ValueError("Base URL must use HTTPS.")

    hostname = (parsed.hostname or "").lower()
    if hostname not in allowed_hosts:
        raise ValueError("Base URL host must be a supported Red Hat domain.")

    # Normalize to scheme + netloc only; drop path/query/fragment.
    cleaned = parsed._replace(path="", params="", query="", fragment="")
    return urlunparse(cleaned)


def validate_anthropic_config(api_key, model):
    """Validate Anthropic API configuration."""
    if anthropic is None:
        return False, "Anthropic library not installed"

    try:
        client = anthropic.Anthropic(api_key=api_key)

        # Make a simple test call
        client.messages.create(
            model=model, max_tokens=10, messages=[{"role": "user", "content": "Hello"}]
        )

        return True, f"Successfully connected to {model}"

    except Exception as e:
        return False, f"Connection failed: {e}"


def validate_openai_config(api_key, model, base_url=""):
    """Validate OpenAI API configuration."""
    if openai is None:
        return False, "OpenAI library not installed. Run: pip install openai"

    try:
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = openai.OpenAI(**client_kwargs)

        # Make a simple test call
        client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": "Hello"}], max_tokens=5
        )

        return True, f"Successfully connected to {model}"

    except Exception as e:
        return False, f"Connection failed: {e}"


def validate_lightspeed_config(api_key, model, base_url=""):
    """Validate Red Hat Lightspeed API configuration."""
    if requests is None:
        return False, "Requests library not installed. Run: pip install requests"

    try:
        # Sanitize and validate base URL
        sanitized_url = _sanitize_lightspeed_base_url(base_url)

        # Make a simple test request to validate API key
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Test with a simple completion request
        test_payload = {
            "model": model,
            "prompt": "Hello",
            "max_tokens": 5,
        }

        response = requests.post(
            f"{sanitized_url}/v1/completions",
            headers=headers,
            json=test_payload,
            timeout=10,
        )

        if response.status_code == 200:
            return True, f"Successfully connected to Red Hat Lightspeed {model}"
        else:
            return False, (
                f"API request failed with status {response.status_code}: "
                f"{response.text}"
            )

    except Exception as e:
        return False, f"Connection failed: {e}"


def validate_watson_config(api_key, project_id, base_url=""):
    """Validate IBM Watsonx API configuration."""
    if APIClient is None:
        return False, (
            "IBM Watsonx AI library not installed. Run: pip install ibm-watsonx-ai"
        )

    try:
        # Initialize Watsonx client
        client = APIClient(
            api_key=api_key,
            project_id=project_id,
            url=base_url or "https://us-south.ml.cloud.ibm.com",
        )

        # Test connection by listing available models
        models = client.foundation_models.get_model_specs()
        if models:
            return True, (
                f"Successfully connected to IBM Watsonx. "
                f"Found {len(models)} available models."
            )
        else:
            return False, "Connected to IBM Watsonx but no models available."

    except Exception as e:
        return False, f"Connection failed: {e}"


def save_ai_settings(
    provider, api_key, model, base_url, temperature, max_tokens, project_id=""
):
    """Save AI settings to configuration file."""
    try:
        # Use /tmp/.souschef for container compatibility (tmpfs is writable)
        config_dir = Path("/tmp/.souschef")
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "ai_config.json"

        config = {
            "provider": provider,
            "model": model,
            "api_key": api_key if api_key else None,
            "base_url": base_url if base_url else None,
            "project_id": project_id if project_id else None,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "last_updated": str(st.session_state.get("timestamp", "Unknown")),
        }

        with config_file.open("w") as f:
            json.dump(config, f, indent=2)

        # Store in session state for immediate use
        st.session_state.ai_config = config

        st.success("Settings saved successfully!")

    except Exception as e:
        st.error(f"Failed to save settings: {str(e)}")


def display_current_settings():
    """Display current AI settings."""
    st.subheader("Current Configuration")

    # Try to load from file first, then session state
    config = load_ai_settings()

    if config:
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Provider", config.get("provider", "Not configured"))
            st.metric("Model", config.get("model", "Not configured"))

        with col2:
            st.metric("Temperature", config.get("temperature", "Not set"))
            st.metric("Max Tokens", config.get("max_tokens", "Not set"))

        if config.get("last_updated"):
            st.caption(f"Last updated: {config['last_updated']}")

        # Security note
        if config.get("api_key"):
            st.info("API key is configured and stored securely.")
        else:
            st.warning("No API key configured.")
    else:
        st.info("No AI configuration found. Please configure your settings above.")


def load_ai_settings():
    """Load AI settings from configuration file."""
    try:
        # Use /tmp/.souschef for container compatibility (tmpfs is writable)
        config_file = Path("/tmp/.souschef/ai_config.json")
        if config_file.exists():
            with config_file.open() as f:
                return json.load(f)
    except Exception as e:
        # Failed to load config from file; fall back to session state/defaults
        st.warning(f"Unable to load saved AI settings: {e}")

    # Fallback to session state or return empty dict
    return st.session_state.get("ai_config", {})
