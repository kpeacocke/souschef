"""UI page for Slack/Teams notification configuration and validation."""

from __future__ import annotations

import streamlit as st

from souschef.integrations.notification_dispatch import (
    NotificationConfig,
    NotificationConfigError,
    validate_notification_config,
)


def show_integration_notifications_page() -> None:
    """Render notification settings UI with provider and webhook validation."""
    st.header("Integration Notifications")
    st.markdown("Configure Slack/Teams outbound notifications for key events.")

    provider_label = st.selectbox("Provider", options=["Slack", "Teams"])
    webhook_url = st.text_input("Webhook URL", value="", help="HTTPS webhook URL")
    channel = st.text_input("Channel", value="", help="Target channel name")

    if st.button("Save Notification Settings", width="stretch"):
        provider = provider_label.lower()
        config = NotificationConfig(
            provider=provider,
            webhook_url=webhook_url,
            channel=channel,
        )

        try:
            validate_notification_config(config)
        except NotificationConfigError as exc:
            st.error(str(exc))
        else:
            st.session_state.notification_config = {
                "provider": provider,
                "webhook_url": webhook_url,
                "channel": channel,
            }
            st.success("Notification settings saved.")

    saved = st.session_state.get("notification_config")
    if saved:
        st.info(
            f"Saved config: provider={saved['provider']}, channel={saved['channel']}"
        )
