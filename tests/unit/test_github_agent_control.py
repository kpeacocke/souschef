"""Tests for GitHub Copilot agent control functionality."""

from unittest.mock import patch

from souschef.github.agent_control import (
    COMMENT_PAUSE_REQUEST,
    COMMENT_RESUME_REQUEST,
    COMMENT_STOP_REQUEST,
    LABEL_AGENT_ACTIVE,
    LABEL_AGENT_PAUSED,
    LABEL_AGENT_STOPPED,
    assign_copilot_agent_to_issue,
    check_copilot_agent_status,
    pause_copilot_agent,
    resume_copilot_agent,
    stop_copilot_agent,
)


class TestAssignCopilotAgent:
    """Tests for assign_copilot_agent_to_issue function."""

    @patch("souschef.github.agent_control._add_label_to_issue")
    def test_assign_copilot_success(self, mock_add_label):
        """Test successful Copilot agent assignment."""
        result = assign_copilot_agent_to_issue(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
        )

        assert "✅ Copilot agent assigned" in result
        assert "#42" in result
        assert "testorg/testrepo" in result
        mock_add_label.assert_called_once_with(
            "testorg", "testrepo", 42, LABEL_AGENT_ACTIVE
        )

    @patch("souschef.github.agent_control._add_label_to_issue")
    def test_assign_copilot_with_base_ref(self, mock_add_label):
        """Test agent assignment with custom base branch."""
        result = assign_copilot_agent_to_issue(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
            base_ref="develop",
        )

        assert "Base branch:** develop" in result
        assert "✅" in result

    @patch("souschef.github.agent_control._add_label_to_issue")
    def test_assign_copilot_with_instructions(self, mock_add_label):
        """Test agent assignment with custom instructions."""
        result = assign_copilot_agent_to_issue(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
            custom_instructions="Focus on performance",
        )

        assert "✅" in result
        assert result  # Non-empty result

    @patch(
        "souschef.github.agent_control._add_label_to_issue",
        side_effect=RuntimeError("API error"),
    )
    def test_assign_copilot_handles_errors(self, mock_add_label):
        """Test error handling during assignment."""
        result = assign_copilot_agent_to_issue(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
        )

        assert "Error assigning" in result
        assert "API error" in result


class TestPauseCopilotAgent:
    """Tests for pause_copilot_agent function."""

    @patch("souschef.github.agent_control._add_comment_to_issue")
    @patch("souschef.github.agent_control._remove_label_from_issue")
    @patch("souschef.github.agent_control._add_label_to_issue")
    def test_pause_agent_success(
        self, mock_add_label, mock_remove_label, mock_add_comment
    ):
        """Test successful agent pause."""
        result = pause_copilot_agent(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
        )

        assert "⏸️ Pause request sent" in result
        assert "#42" in result
        mock_add_label.assert_called_once_with(
            "testorg", "testrepo", 42, LABEL_AGENT_PAUSED
        )
        mock_remove_label.assert_called_once_with(
            "testorg", "testrepo", 42, LABEL_AGENT_ACTIVE
        )
        mock_add_comment.assert_called_once()
        comment_body = mock_add_comment.call_args[0][3]
        assert COMMENT_PAUSE_REQUEST in comment_body

    @patch("souschef.github.agent_control._add_comment_to_issue")
    @patch("souschef.github.agent_control._remove_label_from_issue")
    @patch("souschef.github.agent_control._add_label_to_issue")
    def test_pause_agent_with_reason(
        self, mock_add_label, mock_remove_label, mock_add_comment
    ):
        """Test pausing agent with reason."""
        result = pause_copilot_agent(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
            reason="Need to review approach",
        )

        assert "Reason:** Need to review approach" in result
        comment_body = mock_add_comment.call_args[0][3]
        assert "Need to review approach" in comment_body

    @patch(
        "souschef.github.agent_control._add_label_to_issue",
        side_effect=RuntimeError("Label error"),
    )
    def test_pause_agent_handles_errors(self, mock_add_label):
        """Test error handling during pause."""
        result = pause_copilot_agent(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
        )

        assert "Error pausing" in result


class TestStopCopilotAgent:
    """Tests for stop_copilot_agent function."""

    @patch("souschef.github.agent_control._add_comment_to_issue")
    @patch("souschef.github.agent_control._remove_label_from_issue")
    @patch("souschef.github.agent_control._add_label_to_issue")
    def test_stop_agent_success(
        self, mock_add_label, mock_remove_label, mock_add_comment
    ):
        """Test successful agent stop."""
        result = stop_copilot_agent(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
        )

        assert "🛑 Copilot agent stopped" in result
        assert "#42" in result
        mock_add_label.assert_called_once_with(
            "testorg", "testrepo", 42, LABEL_AGENT_STOPPED
        )
        # Should remove both active and paused labels
        assert mock_remove_label.call_count == 2
        comment_body = mock_add_comment.call_args[0][3]
        assert COMMENT_STOP_REQUEST in comment_body

    @patch("souschef.github.agent_control._add_comment_to_issue")
    @patch("souschef.github.agent_control._remove_label_from_issue")
    @patch("souschef.github.agent_control._add_label_to_issue")
    def test_stop_agent_with_reason(
        self, mock_add_label, mock_remove_label, mock_add_comment
    ):
        """Test stopping agent with reason."""
        result = stop_copilot_agent(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
            reason="Requirements changed",
        )

        assert "Reason:** Requirements changed" in result
        comment_body = mock_add_comment.call_args[0][3]
        assert "Requirements changed" in comment_body


class TestResumeCopilotAgent:
    """Tests for resume_copilot_agent function."""

    @patch("souschef.github.agent_control._add_comment_to_issue")
    @patch("souschef.github.agent_control._add_label_to_issue")
    @patch("souschef.github.agent_control._remove_label_from_issue")
    @patch("souschef.github.agent_control._check_agent_labels", return_value="paused")
    def test_resume_paused_agent(
        self, mock_check, mock_remove_label, mock_add_label, mock_add_comment
    ):
        """Test resuming a paused agent."""
        result = resume_copilot_agent(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
        )

        assert "▶️ Copilot agent resumed" in result
        assert "#42" in result
        mock_remove_label.assert_called_once_with(
            "testorg", "testrepo", 42, LABEL_AGENT_PAUSED
        )
        mock_add_label.assert_called_once_with(
            "testorg", "testrepo", 42, LABEL_AGENT_ACTIVE
        )
        comment_body = mock_add_comment.call_args[0][3]
        assert COMMENT_RESUME_REQUEST in comment_body

    @patch("souschef.github.agent_control._check_agent_labels", return_value="stopped")
    def test_resume_stopped_agent_fails(self, mock_check):
        """Test that resuming a stopped agent returns error."""
        result = resume_copilot_agent(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
        )

        assert "❌ Cannot resume stopped agent" in result
        assert "create a new assignment" in result

    @patch("souschef.github.agent_control._check_agent_labels", return_value="active")
    def test_resume_active_agent_warning(self, mock_check):
        """Test resuming an already active agent."""
        result = resume_copilot_agent(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
        )

        assert "⚠️ Agent is not paused" in result
        assert "active" in result

    @patch("souschef.github.agent_control._add_comment_to_issue")
    @patch("souschef.github.agent_control._add_label_to_issue")
    @patch("souschef.github.agent_control._remove_label_from_issue")
    @patch("souschef.github.agent_control._check_agent_labels", return_value="paused")
    def test_resume_with_additional_instructions(
        self, mock_check, mock_remove_label, mock_add_label, mock_add_comment
    ):
        """Test resuming with additional instructions."""
        result = resume_copilot_agent(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
            additional_instructions="Focus on security",
        )

        assert "Additional instructions:** Focus on security" in result
        comment_body = mock_add_comment.call_args[0][3]
        assert "Focus on security" in comment_body


class TestCheckCopilotAgentStatus:
    """Tests for check_copilot_agent_status function."""

    @patch(
        "souschef.github.agent_control._get_recent_agent_comments",
        return_value="Recent activity here",
    )
    @patch("souschef.github.agent_control._check_agent_labels", return_value="active")
    def test_check_status_active(self, mock_check, mock_comments):
        """Test checking status of active agent."""
        result = check_copilot_agent_status(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
        )

        assert "✅" in result
        assert "Active" in result
        assert "#42" in result
        assert "testorg/testrepo" in result
        assert "Recent activity here" in result

    @patch(
        "souschef.github.agent_control._get_recent_agent_comments",
        return_value="No activity",
    )
    @patch("souschef.github.agent_control._check_agent_labels", return_value="paused")
    def test_check_status_paused(self, mock_check, mock_comments):
        """Test checking status of paused agent."""
        result = check_copilot_agent_status(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
        )

        assert "⏸️" in result
        assert "Paused" in result
        assert "resume_copilot_agent" in result

    @patch(
        "souschef.github.agent_control._get_recent_agent_comments",
        return_value="No activity",
    )
    @patch("souschef.github.agent_control._check_agent_labels", return_value="stopped")
    def test_check_status_stopped(self, mock_check, mock_comments):
        """Test checking status of stopped agent."""
        result = check_copilot_agent_status(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
        )

        assert "🛑" in result
        assert "Stopped" in result
        assert "assign_copilot_agent_to_issue" in result

    @patch("souschef.github.agent_control._get_recent_agent_comments")
    @patch(
        "souschef.github.agent_control._check_agent_labels",
        return_value="not_assigned",
    )
    def test_check_status_not_assigned(self, mock_check, mock_comments):
        """Test checking status when no agent assigned."""
        result = check_copilot_agent_status(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
        )

        assert "⚪" in result
        assert "Not Assigned" in result
        assert "assign_copilot_agent_to_issue" in result

    @patch(
        "souschef.github.agent_control._check_agent_labels",
        side_effect=RuntimeError("Status error"),
    )
    def test_check_status_handles_errors(self, mock_check):
        """Test error handling during status check."""
        result = check_copilot_agent_status(
            owner="testorg",
            repo="testrepo",
            issue_number=42,
        )

        assert "Error checking" in result


class TestAgentControlLabels:
    """Tests for label constants and usage."""

    def test_label_constants_defined(self):
        """Test that all label constants are defined."""
        assert LABEL_AGENT_ACTIVE
        assert LABEL_AGENT_PAUSED
        assert LABEL_AGENT_STOPPED
        assert LABEL_AGENT_ACTIVE.startswith("copilot-agent:")
        assert LABEL_AGENT_PAUSED.startswith("copilot-agent:")
        assert LABEL_AGENT_STOPPED.startswith("copilot-agent:")

    def test_comment_markers_defined(self):
        """Test that all comment markers are defined."""
        assert COMMENT_PAUSE_REQUEST
        assert COMMENT_STOP_REQUEST
        assert COMMENT_RESUME_REQUEST
        assert "Paused" in COMMENT_PAUSE_REQUEST
        assert "Stopped" in COMMENT_STOP_REQUEST
        assert "Resumed" in COMMENT_RESUME_REQUEST
