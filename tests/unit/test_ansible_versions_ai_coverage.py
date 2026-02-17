"""Tests for Ansible version AI integration - targeting uncovered lines."""

import uuid
from unittest.mock import patch

from souschef.core.ansible_versions import (
    _parse_ai_response,
    calculate_upgrade_path,
    fetch_ansible_versions_with_ai,
    get_latest_version_with_ai,
    get_python_compatibility_with_ai,
)


def _sample_api_key() -> str:
    """Return a non-secret placeholder API key for tests."""
    return f"example-{uuid.uuid4()}"


class TestParseAIResponse:
    """Test _parse_ai_response function (lines 819-842)."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        ai_response = '{"2.20": {"control_node_python": ["3.12", "3.13"]}}'
        result = _parse_ai_response(ai_response)
        assert result is not None
        assert isinstance(result, dict)
        assert "2.20" in result

    def test_parse_json_with_markdown_fences_json_prefix(self):
        """Test parsing JSON wrapped in ```json markdown fences."""
        ai_response = (
            '```json\n{"2.20": {"control_node_python": ["3.12", "3.13"]}}\n```'
        )
        result = _parse_ai_response(ai_response)
        assert result is not None
        assert "2.20" in result

    def test_parse_json_with_markdown_fences_plain(self):
        """Test parsing JSON wrapped in ``` markdown fences."""
        ai_response = '```\n{"2.20": {"control_node_python": ["3.12", "3.13"]}}\n```'
        result = _parse_ai_response(ai_response)
        assert result is not None
        assert "2.20" in result

    def test_parse_json_with_only_closing_fence(self):
        """Test parsing JSON with only closing fence."""
        ai_response = '{"2.20": {"control_node_python": ["3.12", "3.13"]}}\n```'
        result = _parse_ai_response(ai_response)
        assert result is not None
        assert "2.20" in result

    def test_parse_invalid_json_returns_none(self):
        """Test parsing invalid JSON returns None."""
        ai_response = "not valid json"
        result = _parse_ai_response(ai_response)
        assert result is None

    def test_parse_non_dict_json_returns_none(self):
        """Test parsing JSON array returns None (must be dict)."""
        ai_response = '["2.20", "2.19"]'
        result = _parse_ai_response(ai_response)
        assert result is None

    def test_parse_json_with_invalid_version_keys_returns_none(self):
        """Test parsing JSON with non-version keys returns None."""
        ai_response = '{"invalid_key": {}, "2.20": {}}'
        result = _parse_ai_response(ai_response)
        # Should return None due to invalid_key not matching version pattern
        assert result is None


class TestFetchAnsibleVersionsWithAI:
    """Test fetch_ansible_versions_with_ai function (lines 891-917)."""

    def test_no_api_key_returns_none(self):
        """Test that empty API key returns None."""
        result = fetch_ansible_versions_with_ai(api_key="", use_cache=False)
        assert result is None

    def test_invalid_provider_returns_none(self):
        """Test that invalid AI provider returns None."""
        result = fetch_ansible_versions_with_ai(
            ai_provider="invalid_provider",
            api_key=_sample_api_key(),
            use_cache=False,
        )
        assert result is None

    @patch("souschef.core.ansible_versions._load_ai_cache")
    def test_uses_cache_when_available(self, mock_load_cache):
        """Test that cache is used when available."""
        mock_cache_data = {"2.20": {"control_node_python": ["3.12"]}}
        mock_load_cache.return_value = mock_cache_data

        result = fetch_ansible_versions_with_ai(
            api_key=_sample_api_key(),
            use_cache=True,
        )
        assert result == mock_cache_data
        mock_load_cache.assert_called_once()

    @patch("souschef.core.ansible_versions._call_ai_provider")
    @patch("souschef.core.ansible_versions._get_ai_prompt")
    @patch("souschef.core.ansible_versions._load_ai_cache")
    def test_calls_ai_provider_when_no_cache(
        self, mock_load_cache, mock_get_prompt, mock_call_ai
    ):
        """Test that AI provider is called when cache is empty."""
        mock_load_cache.return_value = None
        mock_get_prompt.return_value = "test prompt"
        mock_call_ai.return_value = '{"2.20": {"control_node_python": ["3.12"]}}'

        result = fetch_ansible_versions_with_ai(
            ai_provider="anthropic",
            api_key=_sample_api_key(),
            use_cache=True,
        )
        assert result is not None
        mock_call_ai.assert_called_once()

    @patch("souschef.core.ansible_versions._call_ai_provider")
    @patch("souschef.core.ansible_versions._get_ai_prompt")
    @patch("souschef.core.ansible_versions._load_ai_cache")
    def test_returns_none_when_ai_response_empty(
        self, mock_load_cache, mock_get_prompt, mock_call_ai
    ):
        """Test that None is returned when AI response is empty."""
        mock_load_cache.return_value = None
        mock_get_prompt.return_value = "test prompt"
        mock_call_ai.return_value = None

        result = fetch_ansible_versions_with_ai(
            ai_provider="openai",
            api_key=_sample_api_key(),
            use_cache=False,
        )
        assert result is None

    @patch("souschef.core.ansible_versions._parse_ai_response")
    @patch("souschef.core.ansible_versions._call_ai_provider")
    @patch("souschef.core.ansible_versions._get_ai_prompt")
    @patch("souschef.core.ansible_versions._load_ai_cache")
    def test_returns_none_when_parsing_fails(
        self, mock_load_cache, mock_get_prompt, mock_call_ai, mock_parse
    ):
        """Test that None is returned when AI response parsing fails."""
        mock_load_cache.return_value = None
        mock_get_prompt.return_value = "test prompt"
        mock_call_ai.return_value = "invalid response"
        mock_parse.return_value = None

        result = fetch_ansible_versions_with_ai(
            ai_provider="watson",
            api_key=_sample_api_key(),
            use_cache=False,
        )
        assert result is None
        mock_parse.assert_called_once_with("invalid response")


class TestGetPythonCompatibilityWithAI:
    """Test get_python_compatibility_with_ai function (lines 958-968)."""

    @patch("souschef.core.ansible_versions.fetch_ansible_versions_with_ai")
    def test_returns_ai_data_for_control_node(self, mock_fetch):
        """Test getting control node Python from AI data."""
        mock_fetch.return_value = {
            "2.20": {
                "control_node_python": ["3.12", "3.13", "3.14"],
                "managed_node_python": ["3.9", "3.10"],
            }
        }

        result = get_python_compatibility_with_ai(
            "2.20",
            node_type="control",
            api_key=_sample_api_key(),
        )
        assert result == ["3.12", "3.13", "3.14"]

    @patch("souschef.core.ansible_versions.fetch_ansible_versions_with_ai")
    def test_returns_ai_data_for_managed_node(self, mock_fetch):
        """Test getting managed node Python from AI data."""
        mock_fetch.return_value = {
            "2.20": {
                "control_node_python": ["3.12", "3.13"],
                "managed_node_python": ["3.9", "3.10", "3.11"],
            }
        }

        result = get_python_compatibility_with_ai(
            "2.20",
            node_type="managed",
            api_key=_sample_api_key(),
        )
        assert result == ["3.9", "3.10", "3.11"]

    @patch("souschef.core.ansible_versions.fetch_ansible_versions_with_ai")
    @patch("souschef.core.ansible_versions.get_python_compatibility")
    def test_falls_back_to_static_when_version_not_in_ai_data(
        self, mock_static, mock_fetch
    ):
        """Test fallback to static data when AI doesn't have version."""
        mock_fetch.return_value = {"2.19": {}}
        mock_static.return_value = ["3.11", "3.12"]

        result = get_python_compatibility_with_ai(
            "2.20",  # Not in AI data
            node_type="control",
            api_key=_sample_api_key(),
        )
        assert result == ["3.11", "3.12"]
        mock_static.assert_called_once_with("2.20", "control")

    @patch("souschef.core.ansible_versions.fetch_ansible_versions_with_ai")
    @patch("souschef.core.ansible_versions.get_python_compatibility")
    def test_falls_back_when_ai_fetch_returns_none(self, mock_static, mock_fetch):
        """Test fallback to static data when AI fetch fails."""
        mock_fetch.return_value = None
        mock_static.return_value = ["3.12", "3.13"]

        result = get_python_compatibility_with_ai(
            "2.20",
            api_key=_sample_api_key(),
        )
        assert result == ["3.12", "3.13"]
        mock_static.assert_called_once()


class TestGetLatestVersionWithAI:
    """Test get_latest_version_with_ai function (lines 999-1003)."""

    @patch("souschef.core.ansible_versions.fetch_ansible_versions_with_ai")
    def test_returns_latest_version_from_ai_data(self, mock_fetch):
        """Test getting latest version from AI data."""
        mock_fetch.return_value = {
            "2.18": {},
            "2.19": {},
            "2.20": {},
            "2.17": {},
        }

        result = get_latest_version_with_ai(api_key=_sample_api_key())
        assert result == "2.20"  # Highest version

    @patch("souschef.core.ansible_versions.fetch_ansible_versions_with_ai")
    @patch("souschef.core.ansible_versions.get_latest_version")
    def test_falls_back_when_ai_returns_none(self, mock_static, mock_fetch):
        """Test fallback to static data when AI fetch fails."""
        mock_fetch.return_value = None
        mock_static.return_value = "2.20"

        result = get_latest_version_with_ai(api_key=_sample_api_key())
        assert result == "2.20"
        mock_static.assert_called_once()

    @patch("souschef.core.ansible_versions.fetch_ansible_versions_with_ai")
    @patch("souschef.core.ansible_versions.get_latest_version")
    def test_falls_back_when_ai_returns_empty_dict(self, mock_static, mock_fetch):
        """Test fallback when AI returns empty dict."""
        mock_fetch.return_value = {}
        mock_static.return_value = "2.20"

        result = get_latest_version_with_ai(api_key=_sample_api_key())
        assert result == "2.20"
        mock_static.assert_called_once()


class TestCalculateUpgradePathWithAI:
    """Test calculate_upgrade_path AI integration (lines 334, 343-346, 396, 423)."""

    @patch("souschef.core.ansible_versions.fetch_ansible_versions_with_ai")
    def test_uses_ai_python_data_when_available(self, mock_fetch):
        """Test that AI data is used for Python compatibility when available."""
        mock_fetch.return_value = {
            "2.18": {"control_node_python": ["3.11", "3.12", "3.13"]},
            "2.20": {"control_node_python": ["3.12", "3.13", "3.14"]},
        }

        result = calculate_upgrade_path(
            "2.18",
            "2.20",
            use_ai=True,
            api_key=_sample_api_key(),
        )
        # Should use AI data to determine Python upgrade needs
        assert "current_python" in result
        assert "required_python" in result
        mock_fetch.assert_called_once()

    @patch("souschef.core.ansible_versions.fetch_ansible_versions_with_ai")
    def test_handles_python_upgrade_needed_from_ai_data(self, mock_fetch):
        """Test detecting Python upgrade need from AI data."""
        # Current has 3.11+, target needs 3.12+ (upgrade needed)
        mock_fetch.return_value = {
            "2.17": {"control_node_python": ["3.11", "3.12"]},
            "2.20": {"control_node_python": ["3.12", "3.13", "3.14"]},
        }

        result = calculate_upgrade_path(
            "2.17",
            "2.20",
            use_ai=True,
            api_key=_sample_api_key(),
        )
        # Python upgrade may be needed depending on overlap
        assert "python_upgrade_needed" in result
        assert isinstance(result["python_upgrade_needed"], bool)

    def test_ai_disabled_uses_static_data(self):
        """Test that AI is not used when use_ai=False."""
        result = calculate_upgrade_path(
            "2.18",
            "2.20",
            use_ai=False,
            api_key=_sample_api_key(),
        )
        # Should still work with static data
        assert result["from_version"] == "2.18"
        assert result["to_version"] == "2.20"
        assert "python_upgrade_needed" in result

    def test_no_api_key_uses_static_data(self):
        """Test that static data is used when no API key provided."""
        result = calculate_upgrade_path(
            "2.18",
            "2.20",
            use_ai=True,
            api_key="",  # No API key
        )
        # Should still work with static data
        assert result["from_version"] == "2.18"
        assert result["to_version"] == "2.20"
