"""Comprehensive tests for GitHub agent control helper functions."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from souschef.github.agent_control import (
    COMMENT_PAUSE_REQUEST,
    COMMENT_RESUME_REQUEST,
    LABEL_AGENT_ACTIVE,
    LABEL_AGENT_PAUSED,
    LABEL_AGENT_STOPPED,
    _add_comment_to_issue,
    _add_label_to_issue,
    _check_agent_labels,
    _format_status_details,
    _get_available_commands,
    _get_recent_agent_comments,
    _github_request,
    _issue_has_label,
    _remove_label_from_issue,
    _validate_github_token,
)


class TestValidateGitHubToken:
    """Tests for _validate_github_token function."""

    @patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test123"})
    def test_validate_token_from_github_token_env(self):
        """Test token validation from GITHUB_TOKEN environment variable."""
        token = _validate_github_token()
        assert token == "ghp_test123"

    @patch.dict("os.environ", {"GH_TOKEN": "ghp_test456"})
    def test_validate_token_from_gh_token_env(self):
        """Test token validation from GH_TOKEN environment variable."""
        token = _validate_github_token()
        assert token == "ghp_test456"

    @patch.dict("os.environ", {"GITHUB_TOKEN": "primary", "GH_TOKEN": "secondary"})
    def test_validate_token_prefers_github_token(self):
        """Test that GITHUB_TOKEN is preferred over GH_TOKEN."""
        token = _validate_github_token()
        assert token == "primary"

    @patch.dict("os.environ", {}, clear=True)
    def test_validate_token_missing_raises_error(self):
        """Test that missing token raises RuntimeError."""
        with pytest.raises(RuntimeError, match="GitHub token not configured"):
            _validate_github_token()


class TestGitHubRequest:
    """Tests for _github_request function."""

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test"})
    def test_github_request_success(self, mock_request):
        """Test successful GitHub API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "value"}
        mock_request.return_value = mock_response

        response = _github_request("GET", "/repos/owner/repo")

        assert response is not None
        assert response.status_code == 200
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        assert "Authorization" in call_kwargs["headers"]
        assert "Bearer ghp_test" in call_kwargs["headers"]["Authorization"]

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test"})
    def test_github_request_with_params(self, mock_request):
        """Test GitHub API request with query parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        _github_request("GET", "/repos/owner/repo", params={"per_page": "10"})

        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["params"] == {"per_page": "10"}

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test"})
    def test_github_request_with_json_data(self, mock_request):
        """Test GitHub API request with JSON payload."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_request.return_value = mock_response

        _github_request("POST", "/repos/owner/repo/labels", json_data={"name": "bug"})

        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["json"] == {"name": "bug"}

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test"})
    def test_github_request_custom_timeout(self, mock_request):
        """Test GitHub API request with custom timeout."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        _github_request("GET", "/repos/owner/repo", timeout=30.0)

        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["timeout"] == pytest.approx(30.0)

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test"})
    def test_github_request_404_with_allow_not_found(self, mock_request):
        """Test that 404 returns None when allow_not_found is True."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response

        response = _github_request("GET", "/repos/owner /repo", allow_not_found=True)

        assert response is None

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test"})
    def test_github_request_404_without_allow_raises_error(self, mock_request):
        """Test that 404 raises error when allow_not_found is False."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_request.return_value = mock_response

        with pytest.raises(RuntimeError, match="GitHub API error 404"):
            _github_request("GET", "/repos/owner/repo", allow_not_found=False)

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test"})
    def test_github_request_500_error_raises(self, mock_request):
        """Test that server error raises RuntimeError."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_request.return_value = mock_response

        with pytest.raises(RuntimeError, match="GitHub API error 500"):
            _github_request("GET", "/repos/owner/repo")

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test"})
    def test_github_request_network_error_raises(self, mock_request):
        """Test that network error raises RuntimeError."""
        mock_request.side_effect = requests.exceptions.ConnectionError("Network error")

        with pytest.raises(RuntimeError, match="GitHub API request failed"):
            _github_request("GET", "/repos/owner/repo")

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test"})
    def test_github_request_timeout_raises(self, mock_request):
        """Test that timeout raises RuntimeError."""
        mock_request.side_effect = requests.exceptions.Timeout("Request timeout")

        with pytest.raises(RuntimeError, match="GitHub API request failed"):
            _github_request("GET", "/repos/owner/repo")


class TestIssueHasLabel:
    """Tests for _issue_has_label function."""

    @patch("souschef.github.agent_control._github_request")
    def test_issue_has_label_true(self, mock_request):
        """Test checking for label that exists on issue."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"name": "bug"},
            {"name": LABEL_AGENT_ACTIVE},
            {"name": "enhancement"},
        ]
        mock_request.return_value = mock_response

        result = _issue_has_label("owner", "repo", 42, LABEL_AGENT_ACTIVE)

        assert result is True

    @patch("souschef.github.agent_control._github_request")
    def test_issue_has_label_false(self, mock_request):
        """Test checking for label that doesn't exist."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"name": "bug"}, {"name": "enhancement"}]
        mock_request.return_value = mock_response

        result = _issue_has_label("owner", "repo", 42, LABEL_AGENT_PAUSED)

        assert result is False

    @patch("souschef.github.agent_control._github_request")
    def test_issue_has_label_empty_response(self, mock_request):
        """Test checking labels when response is empty."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        result = _issue_has_label("owner", "repo", 42, LABEL_AGENT_ACTIVE)

        assert result is False

    @patch("souschef.github.agent_control._github_request")
    def test_issue_has_label_none_response(self, mock_request):
        """Test checking labels when request fails (returns None)."""
        mock_request.return_value = None

        result = _issue_has_label("owner", "repo", 42, LABEL_AGENT_ACTIVE)

        assert result is False

    @patch("souschef.github.agent_control._github_request")
    def test_issue_has_label_invalid_response_format(self, mock_request):
        """Test checking labels when response is not a list."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Invalid"}
        mock_request.return_value = mock_response

        result = _issue_has_label("owner", "repo", 42, LABEL_AGENT_ACTIVE)

        assert result is False

    @patch("souschef.github.agent_control._github_request")
    def test_issue_has_label_malformed_label_entries(self, mock_request):
        """Test checking labels with malformed entries in response."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"name": "bug"},
            "invalid_entry",  # Not a dict
            {"name": LABEL_AGENT_PAUSED},
        ]
        mock_request.return_value = mock_response

        result = _issue_has_label("owner", "repo", 42, LABEL_AGENT_PAUSED)

        assert result is True


class TestAddLabelToIssue:
    """Tests for _add_label_to_issue function."""

    @patch("souschef.github.agent_control._github_request")
    def test_add_label_success(self, mock_request):
        """Test adding label to issue."""
        _add_label_to_issue("owner", "repo", 42, LABEL_AGENT_ACTIVE)

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert "/issues/42/labels" in args[1]
        assert kwargs["json_data"] == {"labels": [LABEL_AGENT_ACTIVE]}


class TestRemoveLabelFromIssue:
    """Tests for _remove_label_from_issue function."""

    @patch("souschef.github.agent_control._github_request")
    def test_remove_label_success(self, mock_request):
        """Test removing label from issue."""
        _remove_label_from_issue("owner", "repo", 42, LABEL_AGENT_PAUSED)

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "DELETE"
        assert "/issues/42/labels/" in args[1]
        assert kwargs["allow_not_found"] is True

    @patch("souschef.github.agent_control._github_request")
    def test_remove_label_with_special_characters(self, mock_request):
        """Test removing label with special characters (URL encoding)."""
        _remove_label_from_issue("owner", "repo", 42, "label:with:colons")

        mock_request.assert_called_once()
        args = mock_request.call_args.args
        # URL encoding should handle special characters
        assert "label%3Awith%3Acolons" in args[1]


class TestAddCommentToIssue:
    """Tests for _add_comment_to_issue function."""

    @patch("souschef.github.agent_control._github_request")
    def test_add_comment_success(self, mock_request):
        """Test adding comment to issue."""
        comment_text = "This is a test comment"
        _add_comment_to_issue("owner", "repo", 42, comment_text)

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert "/issues/42/comments" in args[1]
        assert kwargs["json_data"] == {"body": comment_text}


class TestCheckAgentLabels:
    """Tests for _check_agent_labels function."""

    @patch("souschef.github.agent_control._issue_has_label")
    def test_check_agent_labels_stopped(self, mock_has_label):
        """Test checking labels returns 'stopped' status."""
        # Stopped label exists
        mock_has_label.side_effect = lambda o, r, i, label: label == LABEL_AGENT_STOPPED

        status = _check_agent_labels("owner", "repo", 42)

        assert status == "stopped"

    @patch("souschef.github.agent_control._issue_has_label")
    def test_check_agent_labels_paused(self, mock_has_label):
        """Test checking labels returns 'paused' status."""
        # Paused label exists, not stopped
        mock_has_label.side_effect = lambda o, r, i, label: label == LABEL_AGENT_PAUSED

        status = _check_agent_labels("owner", "repo", 42)

        assert status == "paused"

    @patch("souschef.github.agent_control._issue_has_label")
    def test_check_agent_labels_active(self, mock_has_label):
        """Test checking labels returns 'active' status."""
        # Active label exists, not stopped or paused
        mock_has_label.side_effect = lambda o, r, i, label: label == LABEL_AGENT_ACTIVE

        status = _check_agent_labels("owner", "repo", 42)

        assert status == "active"

    @patch("souschef.github.agent_control._issue_has_label")
    def test_check_agent_labels_not_assigned(self, mock_has_label):
        """Test checking labels returns 'not_assigned' status."""
        # No agent labels exist
        mock_has_label.return_value = False

        status = _check_agent_labels("owner", "repo", 42)

        assert status == "not_assigned"

    @patch("souschef.github.agent_control._issue_has_label")
    def test_check_agent_labels_priority_order(self, mock_has_label):
        """Test that stopped takes priority over paused and active."""
        # All labels exist (shouldn't happen, but test priority)
        mock_has_label.return_value = True

        status = _check_agent_labels("owner", "repo", 42)

        assert status == "stopped"


class TestGetRecentAgentComments:
    """Tests for _get_recent_agent_comments function."""

    @patch("souschef.github.agent_control._github_request")
    def test_get_recent_comments_with_markers(self, mock_request):
        """Test getting recent comments with agent markers."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"body": "Regular comment"},
            {"body": f"{COMMENT_PAUSE_REQUEST}\nAgent paused"},
            {"body": f"{COMMENT_RESUME_REQUEST}\nAgent resumed"},
            {"body": "Another regular comment"},
        ]
        mock_request.return_value = mock_response

        result = _get_recent_agent_comments("owner", "repo", 42)

        assert COMMENT_PAUSE_REQUEST in result
        assert COMMENT_RESUME_REQUEST in result
        assert "Regular comment" not in result

    @patch("souschef.github.agent_control._github_request")
    def test_get_recent_comments_no_markers(self, mock_request):
        """Test getting comments when no agent markers present."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"body": "Just a regular comment"},
            {"body": "Another regular comment"},
        ]
        mock_request.return_value = mock_response

        result = _get_recent_agent_comments("owner", "repo", 42)

        assert "No recent activity (no agent markers)" in result

    @patch("souschef.github.agent_control._github_request")
    def test_get_recent_comments_none_response(self, mock_request):
        """Test getting comments when request fails."""
        mock_request.return_value = None

        result = _get_recent_agent_comments("owner", "repo", 42)

        assert "No recent activity (issue not found)" in result

    @patch("souschef.github.agent_control._github_request")
    def test_get_recent_comments_invalid_response(self, mock_request):
        """Test getting comments with invalid response format."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Invalid"}
        mock_request.return_value = mock_response

        result = _get_recent_agent_comments("owner", "repo", 42)

        assert "No recent activity (unexpected response)" in result

    @patch("souschef.github.agent_control._github_request")
    def test_get_recent_comments_limits_to_three(self, mock_request):
        """Test that only last 3 agent comments are returned."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"body": f"{COMMENT_PAUSE_REQUEST} 1"},
            {"body": f"{COMMENT_RESUME_REQUEST} 2"},
            {"body": f"{COMMENT_PAUSE_REQUEST} 3"},
            {"body": f"{COMMENT_RESUME_REQUEST} 4"},
            {"body": f"{COMMENT_PAUSE_REQUEST} 5"},
        ]
        mock_request.return_value = mock_response

        result = _get_recent_agent_comments("owner", "repo", 42)

        # Should contain last 3
        assert result.count("\n\n") == 2  # 3 comments = 2 separators

    @patch("souschef.github.agent_control._github_request")
    def test_get_recent_comments_handles_non_dict_entries(self, mock_request):
        """Test handling of malformed comment entries."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"body": f"{COMMENT_PAUSE_REQUEST} Valid"},
            "invalid_entry",
            {"body": f"{COMMENT_RESUME_REQUEST} Also valid"},
        ]
        mock_request.return_value = mock_response

        result = _get_recent_agent_comments("owner", "repo", 42)

        assert COMMENT_PAUSE_REQUEST in result
        assert COMMENT_RESUME_REQUEST in result


class TestFormatStatusDetails:
    """Tests for _format_status_details function."""

    def test_format_status_active(self):
        """Test formatting details for active status."""
        details = _format_status_details("active")
        assert "currently working" in details
        assert "pull request" in details

    def test_format_status_paused(self):
        """Test formatting details for paused status."""
        details = _format_status_details("paused")
        assert "paused" in details
        assert "resume" in details

    def test_format_status_stopped(self):
        """Test formatting details for stopped status."""
        details = _format_status_details("stopped")
        assert "cancelled" in details
        assert "new assignment" in details

    def test_format_status_not_assigned(self):
        """Test formatting details for not_assigned status."""
        details = _format_status_details("not_assigned")
        assert "currently assigned" in details
        assert "assign" in details

    def test_format_status_unknown(self):
        """Test formatting details for unknown status."""
        details = _format_status_details("unknown_status")
        assert "Unknown status" in details


class TestGetAvailableCommands:
    """Tests for _get_available_commands function."""

    def test_get_commands_active(self):
        """Test getting commands for active status."""
        commands = _get_available_commands("active")
        assert "pause_copilot_agent" in commands
        assert "stop_copilot_agent" in commands
        assert "check_copilot_agent_status" in commands
        assert "resume" not in commands

    def test_get_commands_paused(self):
        """Test getting commands for paused status."""
        commands = _get_available_commands("paused")
        assert "resume_copilot_agent" in commands
        assert "stop_copilot_agent" in commands
        assert "check_copilot_agent_status" in commands
        assert "pause" not in commands

    def test_get_commands_stopped(self):
        """Test getting commands for stopped status."""
        commands = _get_available_commands("stopped")
        assert "assign_copilot_agent_to_issue" in commands
        assert "check_copilot_agent_status" in commands
        assert "resume" not in commands
        assert "pause" not in commands

    def test_get_commands_not_assigned(self):
        """Test getting commands for not_assigned status."""
        commands = _get_available_commands("not_assigned")
        assert "assign_copilot_agent_to_issue" in commands
        assert "check_copilot_agent_status" in commands
        assert "pause" not in commands
        assert "stop" not in commands

    def test_get_commands_unknown(self):
        """Test getting commands for unknown status."""
        commands = _get_available_commands("unknown_status")
        assert "No commands available" in commands
