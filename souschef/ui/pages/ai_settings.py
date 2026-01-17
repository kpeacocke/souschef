"""
AI Settings Page for SousChef UI.

Configure and validate AI provider settings for the SousChef MCP server.
"""

import json
from pathlib import Path

import streamlit as st

# AI Provider Constants
ANTHROPIC_PROVIDER = "Anthropic (Claude)"
OPENAI_PROVIDER = "OpenAI (GPT)"
LOCAL_PROVIDER = "Local Model"

# Import AI libraries (optional dependencies)
try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore[assignment]

try:
    import openai  # type: ignore[import-not-found]
except ImportError:
    openai = None


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
            [ANTHROPIC_PROVIDER, OPENAI_PROVIDER, LOCAL_PROVIDER],
            help="Select your preferred AI provider",
            key="ai_provider_select",
        )

    with col2:
        if ai_provider == ANTHROPIC_PROVIDER:
            model_options = [
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229",
            ]
        elif ai_provider == OPENAI_PROVIDER:
            model_options = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
        else:
            model_options = ["local-model"]

        selected_model = st.selectbox(
            "Model",
            model_options,
            help="Select the AI model to use",
            key="ai_model_select",
        )

    # API Configuration
    st.subheader("API Configuration")

    if ai_provider == LOCAL_PROVIDER:
        st.info("Local model configuration will be added in a future update.")
        api_key = ""
        base_url = ""
    else:
        col1, col2 = st.columns(2)

        with col1:
            api_key = st.text_input(
                "API Key",
                type="password",
                help=f"Enter your {ai_provider.split(' ')[0]} API key",
                key="api_key_input",
                placeholder=f"sk-... (for {ai_provider.split(' ')[0]})",
            )

        with col2:
            if ai_provider == OPENAI_PROVIDER:
                base_url = st.text_input(
                    "Base URL (Optional)",
                    help="Custom OpenAI API base URL",
                    key="base_url_input",
                    placeholder="https://api.openai.com/v1",
                )
            else:
                base_url = ""

    # Advanced Settings
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

    # Validation Section
    st.subheader("Configuration Validation")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Validate Configuration", type="primary", width="stretch"):
            validate_ai_configuration(ai_provider, api_key, selected_model, base_url)

    with col2:
        if st.button("Save Settings", width="stretch"):
            save_ai_settings(
                ai_provider, api_key, selected_model, base_url, temperature, max_tokens
            )

    # Current Settings Display
    display_current_settings()


def validate_ai_configuration(provider, api_key, model, base_url=""):
    """Validate the AI configuration by making a test API call."""
    if not api_key and provider != "Local Model":
        st.error("API key is required for validation.")
        return

    with st.spinner("Validating AI configuration..."):
        try:
            if provider == ANTHROPIC_PROVIDER:
                success, message = validate_anthropic_config(api_key, model)
            elif provider == OPENAI_PROVIDER:
                success, message = validate_openai_config(api_key, model, base_url)
            else:
                st.info("Local model validation not implemented yet.")
                return

            if success:
                st.success(f"Configuration validated successfully! {message}")
            else:
                st.error(f"Validation failed: {message}")

        except Exception as e:
            st.error(f"Validation error: {str(e)}")


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


def save_ai_settings(provider, api_key, model, base_url, temperature, max_tokens):
    """Save AI settings to configuration file."""
    try:
        config_dir = Path.home() / ".souschef"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "ai_config.json"

        config = {
            "provider": provider,
            "model": model,
            "api_key": api_key if api_key else None,
            "base_url": base_url if base_url else None,
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
        config_file = Path.home() / ".souschef" / "ai_config.json"
        if config_file.exists():
            with config_file.open() as f:
                return json.load(f)
    except Exception as e:
        # Failed to load config from file; fall back to session state/defaults
        st.warning(f"Unable to load saved AI settings: {e}")

    # Fallback to session state or return empty dict
    return st.session_state.get("ai_config", {})
