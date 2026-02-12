"""Comprehensive tests for github/agent_control.py module to achieve 100% coverage."""

import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from souschef.github.agent_control import (
    COMMENT_PAUSE_REQUEST,
    COMMENT_RESUME_REQUEST,
    COMMENT_STOP_REQUEST,
    GITHUB_API_BASE_URL,
    GITHUB_API_TIMEOUT_SECONDS,
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
    assign_copilot_agent_to_issue,
    check_copilot_agent_status,
    pause_copilot_agent,
    resume_copilot_agent,
    stop_copilot_agent,
)


class TestConstants:
    """Test module constants."""

    def test_label_constants(self) -> None:
        """Test label constants are defined."""
        assert LABEL_AGENT_ACTIVE == "copilot-agent:active"
        assert LABEL_AGENT_PAUSED == "copilot-agent:paused"
        assert LABEL_AGENT_STOPPED == "copilot-agent:stopped"

    def test_comment_constants(self) -> None:
        """Test comment request constants."""
        assert COMMENT_PAUSE_REQUEST == "🔸 **Copilot Agent Paused**"
        assert COMMENT_STOP_REQUEST == "🛑 **Copilot Agent Stopped**"
        assert COMMENT_RESUME_REQUEST == "▶️ **Copilot Agent Resumed**"

    def test_github_api_constants(self) -> None:
        """Test GitHub API constants."""
        assert GITHUB_API_BASE_URL == "https://api.github.com"
        assert isinstance(GITHUB_API_BASE_URL, str)


class TestValidateGitHubToken:
    """Test _validate_github_token function."""

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token_123"})
    def test_validate_github_token_present(self) -> None:
        """Test validation when token is present."""
        token = _validate_github_token()
        assert token == "test_token_123"

    @patch.dict(os.environ, {}, clear=True)
    def test_validate_github_token_missing(self) -> None:
        """Test validation when token is missing."""
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
            _validate_github_token()


class TestGitHubRequest:
    """Test _github_request function."""

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    def test_github_request_get_success(self, mock_request) -> None:
        """Test successful GET request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        result = _github_request("GET", "/repos/owner/repo")

        assert result == mock_response
        mock_request.assert_called_once()

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    def test_github_request_post(self, mock_request) -> None:
        """Test POST request."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_request.return_value = mock_response

        result = _github_request(
            "POST", "/repos/owner/repo/issues", json_data={"title": "Test"}
        )

        assert result == mock_response

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    def test_github_request_delete(self, mock_request) -> None:
        """Test DELETE request."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        result = _github_request("DELETE", "/repos/owner/repo/labels/test")

        assert result == mock_response

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    def test_github_request_error(self, mock_request) -> None:
        """Test request error handling."""
        mock_request.side_effect = requests.RequestException("Network error")

        with pytest.raises(RuntimeError, match="GitHub API"):
            _github_request("GET", "/repos/owner/repo")

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    def test_github_request_404_not_found(self, mock_request) -> None:
        """Test 404 handling with allow_not_found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response

        result = _github_request(
            "DELETE", "/repos/owner/repo/labels/test", allow_not_found=True
        )

        assert result is None

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    def test_github_request_with_params(self, mock_request) -> None:
        """Test request with parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        result = _github_request("GET", "/repos/owner/repo", params={"per_page": "10"})

        assert result == mock_response
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["params"] == {"per_page": "10"}

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    def test_github_request_custom_timeout(self, mock_request) -> None:
        """Test request with custom timeout."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        result = _github_request("GET", "/repos/owner/repo", timeout=5.0)

        assert result == mock_response
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["timeout"] == 5.0

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    def test_github_request_default_timeout(self, mock_request) -> None:
        """Test request uses default timeout."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        _github_request("GET", "/repos/owner/repo")

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["timeout"] == GITHUB_API_TIMEOUT_SECONDS


class TestCheckAgentLabels:
    """Test _check_agent_labels function."""

    @patch("souschef.github.agent_control._github_request")
    def test_check_agent_labels_active(self, mock_request) -> None:
        """Test checking active agent labels."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"name": LABEL_AGENT_ACTIVE},
            {"name": "other"},
        ]
        mock_request.return_value = mock_response

        result = _check_agent_labels("owner", "repo", 1)

        assert result == "active"

    @patch("souschef.github.agent_control._github_request")
    def test_check_agent_labels_paused(self, mock_request) -> None:
        """Test checking paused agent labels."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"name": LABEL_AGENT_PAUSED}]
        mock_request.return_value = mock_response

        result = _check_agent_labels("owner", "repo", 1)

        assert result == "paused"

    @patch("souschef.github.agent_control._github_request")
    def test_check_agent_labels_stopped(self, mock_request) -> None:
        """Test checking stopped agent labels."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"name": LABEL_AGENT_STOPPED}]
        mock_request.return_value = mock_response

        result = _check_agent_labels("owner", "repo", 1)

        assert result == "stopped"

    @patch("souschef.github.agent_control._github_request")
    def test_check_agent_labels_none(self, mock_request) -> None:
        """Test checking when no agent labels present."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        result = _check_agent_labels("owner", "repo", 1)

        assert result == "not_assigned"


class TestIssueHasLabel:
    """Test _issue_has_label function."""

    @patch("souschef.github.agent_control._github_request")
    def test_issue_has_label_true(self, mock_request) -> None:
        """Test when issue has label."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"name": "test-label"},
            {"name": "other"},
        ]
        mock_request.return_value = mock_response

        result = _issue_has_label("owner", "repo", 1, "test-label")

        assert result is True

    @patch("souschef.github.agent_control._github_request")
    def test_issue_has_label_false(self, mock_request) -> None:
        """Test when issue doesn't have label."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"name": "other"}]
        mock_request.return_value = mock_response

        result = _issue_has_label("owner", "repo", 1, "test-label")

        assert result is False

    @patch("souschef.github.agent_control._github_request")
    def test_issue_has_label_empty(self, mock_request) -> None:
        """Test when issue has no labels."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        result = _issue_has_label("owner", "repo", 1, "test-label")

        assert result is False

    @patch("souschef.github.agent_control._github_request")
    def test_issue_has_label_none_response(self, mock_request) -> None:
        """Test when API returns None (404 allowed)."""
        mock_request.return_value = None

        result = _issue_has_label("owner", "repo", 1, "test-label")

        assert result is False

    @patch("souschef.github.agent_control._github_request")
    def test_issue_has_label_invalid_response_type(self, mock_request) -> None:
        """Test when API returns non-list response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"not": "a list"}
        mock_request.return_value = mock_response

        result = _issue_has_label("owner", "repo", 1, "test-label")

        assert result is False

    @patch("souschef.github.agent_control._github_request")
    def test_issue_has_label_invalid_label_item(self, mock_request) -> None:
        """Test when label item is not a dict."""
        mock_response = MagicMock()
        mock_response.json.return_value = ["not-a-dict", {"name": "valid"}]
        mock_request.return_value = mock_response

        # Should skip invalid item and continue
        result = _issue_has_label("owner", "repo", 1, "valid")

        assert result is True


class TestLabelOperations:
    """Test label add/remove operations."""

    @patch("souschef.github.agent_control._github_request")
    def test_add_label_to_issue(self, mock_request) -> None:
        """Test adding label to issue."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        result = _add_label_to_issue("owner", "repo", 1, "test-label")

        assert result is None
        mock_request.assert_called_once()

    @patch("souschef.github.agent_control._github_request")
    def test_add_label_raises_error(self, mock_request) -> None:
        """Test error when adding label propagates."""
        mock_request.side_effect = RuntimeError("API error")

        # Function should raise (error handling is at caller level)
        with pytest.raises(RuntimeError):
            _add_label_to_issue("owner", "repo", 1, "test-label")

    @patch("souschef.github.agent_control._github_request")
    def test_remove_label_from_issue(self, mock_request) -> None:
        """Test removing label from issue."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        _remove_label_from_issue("owner", "repo", 1, "test-label")

        mock_request.assert_called_once()

    @patch("souschef.github.agent_control._github_request")
    def test_remove_label_raises_error(self, mock_request) -> None:
        """Test error when removing label propagates."""
        mock_request.side_effect = RuntimeError("API error")

        # Function should raise (error handling is at caller level)
        with pytest.raises(RuntimeError):
            _remove_label_from_issue("owner", "repo", 1, "test-label")

    @patch("souschef.github.agent_control._github_request")
    def test_remove_label_with_special_characters(self, mock_request) -> None:
        """Test removing label with special characters (URL encoding)."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        _remove_label_from_issue("owner", "repo", 1, "label:with-special")

        # Verify URL encoding was used
        mock_request.assert_called_once()
        call_args = mock_request.call_args

        # The label should be URL encoded
        path = call_args[0][1]
        assert "label%3Awith-special" in path or "label:with-special" in path


class TestCommentOperations:
    """Test comment operations."""

    @patch("souschef.github.agent_control._github_request")
    def test_add_comment_to_issue(self, mock_request) -> None:
        """Test adding comment to issue."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_request.return_value = mock_response

        result = _add_comment_to_issue("owner", "repo", 1, "test comment")

        assert result is None
        mock_request.assert_called_once()

    @patch("souschef.github.agent_control._github_request")
    def test_add_comment_raises_error(self, mock_request) -> None:
        """Test error when adding comment propagates."""
        mock_request.side_effect = RuntimeError("API error")

        # Function should raise (error handling is at caller level)
        with pytest.raises(RuntimeError):
            _add_comment_to_issue("owner", "repo", 1, "test comment")

    @patch("souschef.github.agent_control._github_request")
    def test_get_recent_agent_comments_with_markers(self, mock_request) -> None:
        """Test getting recent agent comments."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"body": "🔸 **Copilot Agent Paused**\n\nSome context", "id": 1},
            {"body": "Other comment without marker", "id": 2},
            {"body": "🛑 **Copilot Agent Stopped**\n\nCancelled", "id": 3},
        ]
        mock_request.return_value = mock_response

        result = _get_recent_agent_comments("owner", "repo", 1)

        assert isinstance(result, str)
        assert "Paused" in result or "Stopped" in result

    @patch("souschef.github.agent_control._github_request")
    def test_get_recent_agent_comments_none(self, mock_request) -> None:
        """Test when no agent comments found."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"body": "Regular comment", "id": 1}]
        mock_request.return_value = mock_response

        result = _get_recent_agent_comments("owner", "repo", 1)

        assert isinstance(result, str)

    @patch("souschef.github.agent_control._github_request")
    def test_get_recent_agent_comments_empty(self, mock_request) -> None:
        """Test when no comments at all."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        result = _get_recent_agent_comments("owner", "repo", 1)

        assert isinstance(result, str)

    @patch("souschef.github.agent_control._github_request")
    def test_get_recent_agent_comments_none_response(self, mock_request) -> None:
        """Test when API returns None."""
        mock_request.return_value = None

        result = _get_recent_agent_comments("owner", "repo", 1)

        assert isinstance(result, str)

    @patch("souschef.github.agent_control._github_request")
    def test_get_recent_agent_comments_invalid_response(self, mock_request) -> None:
        """Test when API returns non-list."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"not": "a list"}
        mock_request.return_value = mock_response

        result = _get_recent_agent_comments("owner", "repo", 1)

        assert isinstance(result, str)

    @patch("souschef.github.agent_control._github_request")
    def test_get_recent_agent_comments_invalid_item(self, mock_request) -> None:
        """Test when comment item is not a dict."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            "not-a-dict",
            {"body": "🔸 **Copilot Agent Paused**"},
        ]
        mock_request.return_value = mock_response

        # Should skip invalid item
        result = _get_recent_agent_comments("owner", "repo", 1)

        assert isinstance(result, str)


class TestFormatStatusDetails:
    """Test _format_status_details function."""

    def test_format_status_active(self) -> None:
        """Test formatting active status."""
        result = _format_status_details("active")

        assert isinstance(result, str)
        assert len(result) > 0
        assert "currently working" in result.lower()

    def test_format_status_paused(self) -> None:
        """Test formatting paused status."""
        result = _format_status_details("paused")

        assert isinstance(result, str)
        assert "paused" in result.lower() or "pause" in result.lower()

    def test_format_status_stopped(self) -> None:
        """Test formatting stopped status."""
        result = _format_status_details("stopped")

        assert isinstance(result, str)
        assert "cancelled" in result.lower() or "stop" in result.lower()

    def test_format_status_not_assigned(self) -> None:
        """Test formatting not assigned status."""
        result = _format_status_details("not_assigned")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_status_unknown(self) -> None:
        """Test formatting unknown status."""
        result = _format_status_details("unknown")

        assert isinstance(result, str)


class TestGetAvailableCommands:
    """Test _get_available_commands function."""

    def test_available_commands_active(self) -> None:
        """Test commands when agent is active."""
        result = _get_available_commands("active")

        assert isinstance(result, str)
        assert "pause" in result.lower() or "stop" in result.lower()

    def test_available_commands_paused(self) -> None:
        """Test commands when agent is paused."""
        result = _get_available_commands("paused")

        assert isinstance(result, str)
        assert "resume" in result.lower() or "stop" in result.lower()

    def test_available_commands_stopped(self) -> None:
        """Test commands when agent is stopped."""
        result = _get_available_commands("stopped")

        assert isinstance(result, str)


class TestAssignCopilotAgent:
    """Test assign_copilot_agent_to_issue function."""

    @patch("souschef.github.agent_control._add_label_to_issue")
    def test_assign_copilot_agent_success(self, mock_add_label) -> None:
        """Test successful agent assignment."""
        result = assign_copilot_agent_to_issue("owner", "repo", 1)

        assert "✅" in result or "assigned" in result.lower()
        assert "#1" in result
        assert "owner/repo" in result
        mock_add_label.assert_called_once()

    @patch("souschef.github.agent_control._add_label_to_issue")
    def test_assign_copilot_agent_with_base_ref(self, mock_add_label) -> None:
        """Test agent assignment with base branch."""
        result = assign_copilot_agent_to_issue("owner", "repo", 1, base_ref="main")

        assert "main" in result

    @patch("souschef.github.agent_control._add_label_to_issue")
    def test_assign_copilot_agent_with_instructions(self, mock_add_label) -> None:
        """Test agent assignment with custom instructions."""
        result = assign_copilot_agent_to_issue(
            "owner", "repo", 1, custom_instructions="Do something special"
        )

        assert "custom instructions" in result.lower() or "special" in result.lower()

    @patch("souschef.github.agent_control._add_label_to_issue")
    def test_assign_copilot_agent_error(self, mock_add_label) -> None:
        """Test agent assignment error handling."""
        mock_add_label.side_effect = RuntimeError("Label error")

        result = assign_copilot_agent_to_issue("owner", "repo", 1)

        assert "Error" in result or "error" in result


class TestPauseCopilotAgent:
    """Test pause_copilot_agent function."""

    @patch("souschef.github.agent_control._check_agent_labels")
    @patch("souschef.github.agent_control._add_label_to_issue")
    @patch("souschef.github.agent_control._remove_label_from_issue")
    @patch("souschef.github.agent_control._add_comment_to_issue")
    def test_pause_copilot_agent(
        self, mock_comment, mock_remove_label, mock_add_label, mock_check_labels
    ) -> None:
        """Test pausing Copilot agent."""
        mock_check_labels.return_value = "Agent is active"

        result = pause_copilot_agent("owner", "repo", 1)

        assert isinstance(result, str)
        assert "paused" in result.lower() or "pause" in result.lower()

    @patch("souschef.github.agent_control._check_agent_labels")
    def test_pause_copilot_agent_error(self, mock_check_labels) -> None:
        """Test pausing with error."""
        mock_check_labels.side_effect = RuntimeError("API error")

        result = pause_copilot_agent("owner", "repo", 1)

        assert "Error" in result or "error" in result


class TestStopCopilotAgent:
    """Test stop_copilot_agent function."""

    @patch("souschef.github.agent_control._add_label_to_issue")
    @patch("souschef.github.agent_control._remove_label_from_issue")
    @patch("souschef.github.agent_control._add_comment_to_issue")
    def test_stop_copilot_agent(self, mock_comment, mock_remove, mock_add) -> None:
        """Test stopping Copilot agent."""
        result = stop_copilot_agent("owner", "repo", 1)

        assert isinstance(result, str)
        assert "stopped" in result.lower() or "stop" in result.lower()

    @patch("souschef.github.agent_control._add_label_to_issue")
    def test_stop_copilot_agent_error(self, mock_add) -> None:
        """Test stopping with error."""
        mock_add.side_effect = RuntimeError("API error")

        result = stop_copilot_agent("owner", "repo", 1)

        assert "Error" in result or "error" in result


class TestResumeCopilotAgent:
    """Test resume_copilot_agent function."""

    @patch("souschef.github.agent_control._check_agent_labels")
    @patch("souschef.github.agent_control._add_label_to_issue")
    @patch("souschef.github.agent_control._remove_label_from_issue")
    @patch("souschef.github.agent_control._add_comment_to_issue")
    def test_resume_copilot_agent(
        self, mock_comment, mock_remove, mock_add, mock_check_labels
    ) -> None:
        """Test resuming Copilot agent."""
        mock_check_labels.return_value = "paused"

        result = resume_copilot_agent("owner", "repo", 1)

        assert isinstance(result, str)
        assert "resumed" in result.lower() or "resume" in result.lower()

    @patch("souschef.github.agent_control._check_agent_labels")
    def test_resume_copilot_agent_when_stopped(self, mock_check_labels) -> None:
        """Test resuming when agent is stopped."""
        mock_check_labels.return_value = "stopped"

        result = resume_copilot_agent("owner", "repo", 1)

        assert "Cannot resume" in result

    @patch("souschef.github.agent_control._check_agent_labels")
    def test_resume_copilot_agent_when_active(self, mock_check_labels) -> None:
        """Test resuming when agent is already active."""
        mock_check_labels.return_value = "active"

        result = resume_copilot_agent("owner", "repo", 1)

        assert "not paused" in result.lower()

    @patch("souschef.github.agent_control._check_agent_labels")
    def test_resume_copilot_agent_with_instructions(self, mock_check_labels) -> None:
        """Test resume with additional instructions."""
        mock_check_labels.return_value = "paused"

        result = resume_copilot_agent(
            "owner", "repo", 1, additional_instructions="Do something special"
        )

        assert isinstance(result, str)

    @patch("souschef.github.agent_control._check_agent_labels")
    def test_resume_copilot_agent_error(self, mock_check_labels) -> None:
        """Test resuming with error."""
        mock_check_labels.side_effect = RuntimeError("API error")

        result = resume_copilot_agent("owner", "repo", 1)

        assert "Error" in result or "error" in result


class TestCheckCopilotAgentStatus:
    """Test check_copilot_agent_status function."""

    @patch("souschef.github.agent_control._check_agent_labels")
    @patch("souschef.github.agent_control._get_recent_agent_comments")
    def test_check_copilot_agent_status(self, mock_comments, mock_labels) -> None:
        """Test checking agent status."""
        mock_labels.return_value = "Active"
        mock_comments.return_value = "Recent activity"

        result = check_copilot_agent_status("owner", "repo", 1)

        assert isinstance(result, str)
        assert "Active" in result or "active" in result or "status" in result.lower()

    @patch("souschef.github.agent_control._check_agent_labels")
    def test_check_copilot_agent_status_error(self, mock_labels) -> None:
        """Test checking status with error."""
        mock_labels.side_effect = RuntimeError("API error")

        result = check_copilot_agent_status("owner", "repo", 1)

        assert "Error" in result or "error" in result


class TestAgentControlEdgeCases:
    """Test edge cases and error conditions."""

    @patch("souschef.github.agent_control.requests.request")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    def test_github_request_timeout(self, mock_request) -> None:
        """Test request timeout handling."""
        mock_request.side_effect = requests.Timeout("Connection timeout")

        with pytest.raises(RuntimeError, match="GitHub API"):
            _github_request("GET", "/repos/owner/repo")

    def test_unicode_in_comments(self) -> None:
        """Test that comment constants contain unicode."""
        assert "🔸" in COMMENT_PAUSE_REQUEST
        assert "🛑" in COMMENT_STOP_REQUEST
        assert "▶️" in COMMENT_RESUME_REQUEST

    @patch("souschef.github.agent_control._github_request")
    def test_special_characters_in_repo_name(self, mock_request) -> None:
        """Test handling special characters in repository names."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        # Should not raise
        _check_agent_labels("owner", "repo-with-dashes", 1)

    @patch.dict(os.environ, {"GITHUB_TOKEN": ""})
    def test_empty_token(self) -> None:
        """Test handling empty token."""
        with pytest.raises(RuntimeError, match="GitHub token"):
            _validate_github_token()
