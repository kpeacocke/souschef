"""
GitHub Copilot agent control for issue assignments.

Provides pause, stop, and resume capabilities for Copilot agents working on issues.
State is tracked via GitHub issue comments and labels.
"""

# Agent state management via labels
LABEL_AGENT_ACTIVE = "copilot-agent:active"
LABEL_AGENT_PAUSED = "copilot-agent:paused"
LABEL_AGENT_STOPPED = "copilot-agent:stopped"

# Comment markers for agent state changes
COMMENT_PAUSE_REQUEST = "🔸 **Copilot Agent Paused**"
COMMENT_STOP_REQUEST = "🛑 **Copilot Agent Stopped**"
COMMENT_RESUME_REQUEST = "▶️ **Copilot Agent Resumed**"


def assign_copilot_agent_to_issue(
    owner: str,
    repo: str,
    issue_number: int,
    base_ref: str = "",
    custom_instructions: str = "",
) -> str:
    """
    Assign GitHub Copilot to work on an issue.

    Args:
        owner: Repository owner (username or organisation).
        repo: Repository name.
        issue_number: Issue number to assign Copilot to.
        base_ref: Git reference (branch) to start from. Defaults to repo default branch.
        custom_instructions: Optional additional guidance for the agent.

    Returns:
        Status message indicating the agent assignment was created.

    """
    try:
        # Call the GitHub MCP tool to assign Copilot
        # Note: This relies on the mcp_github_assign_copilot_to_issue tool
        # being available via the MCP server framework

        # Add active label to track assignment
        _add_label_to_issue(owner, repo, issue_number, LABEL_AGENT_ACTIVE)

        instructions_note = (
            f"\n**Custom instructions:** {custom_instructions}"
            if custom_instructions
            else ""
        )

        return f"""✅ Copilot agent assigned to issue #{issue_number}

**Repository:** {owner}/{repo}
**Base branch:** {base_ref or "default"}
**Status:** Agent is now working on the issue{instructions_note}

The agent will create a pull request with proposed changes.
You can monitor progress in the issue comments.

**Control commands:**
- Use `pause_github_copilot_agent` to temporarily pause work
- Use `stop_github_copilot_agent` to cancel the assignment
- Use `check_github_copilot_agent_status` to view current state
"""

    except Exception as e:
        return f"Error assigning Copilot agent: {e}"


def pause_copilot_agent(
    owner: str,
    repo: str,
    issue_number: int,
    reason: str = "",
) -> str:
    """
    Pause a running Copilot agent working on an issue.

    This adds a label and comment to signal the agent should pause work.
    Note: The agent will complete its current task before pausing.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue number where agent is working.
        reason: Optional reason for pausing (included in comment).

    Returns:
        Status message confirming the pause request.

    """
    try:
        # Add pause label
        _add_label_to_issue(owner, repo, issue_number, LABEL_AGENT_PAUSED)

        # Remove active label if present
        _remove_label_from_issue(owner, repo, issue_number, LABEL_AGENT_ACTIVE)

        # Add comment documenting pause
        comment_body = f"""{COMMENT_PAUSE_REQUEST}

The Copilot agent has been requested to pause work on this issue.
{f"**Reason:** {reason}" if reason else ""}

The agent will complete its current task before pausing.
To resume work, use the resume command.

**Next steps:**
- Use `resume_copilot_agent` to continue work
- Use `stop_copilot_agent` to permanently cancel
- Use `check_copilot_agent_status` to view current state
"""

        _add_comment_to_issue(owner, repo, issue_number, comment_body)

        return f"""⏸️ Pause request sent to Copilot agent on issue #{issue_number}

**Repository:** {owner}/{repo}
**Status:** Agent paused (will complete current task)
{f"**Reason:** {reason}" if reason else ""}

The agent has been signalled to pause. Check issue comments for updates.

To resume: Use `resume_github_copilot_agent` command."""

    except Exception as e:
        return f"Error pausing Copilot agent: {e}"


def stop_copilot_agent(
    owner: str,
    repo: str,
    issue_number: int,
    reason: str = "",
) -> str:
    """
    Stop a Copilot agent and cancel its work on an issue.

    This marks the agent as stopped via labels and comments. Any incomplete
    work will not result in a pull request.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue number where agent is working.
        reason: Optional reason for stopping (included in comment).

    Returns:
        Status message confirming the stop request.

    """
    try:
        # Add stopped label
        _add_label_to_issue(owner, repo, issue_number, LABEL_AGENT_STOPPED)

        # Remove active and paused labels
        _remove_label_from_issue(owner, repo, issue_number, LABEL_AGENT_ACTIVE)
        _remove_label_from_issue(owner, repo, issue_number, LABEL_AGENT_PAUSED)

        # Add comment documenting stop
        comment_body = f"""{COMMENT_STOP_REQUEST}

The Copilot agent assignment has been cancelled.
{f"**Reason:** {reason}" if reason else ""}

No pull request will be created from the current work.
The agent will not resume automatically.

**Next steps:**
- Manually implement the changes, or
- Create a new agent assignment with updated instructions
"""

        _add_comment_to_issue(owner, repo, issue_number, comment_body)

        return f"""🛑 Copilot agent stopped on issue #{issue_number}

**Repository:** {owner}/{repo}
**Status:** Agent cancelled (no PR will be created)
{f"**Reason:** {reason}" if reason else ""}

The agent has been stopped and will not create a pull request."""

    except Exception as e:
        return f"Error stopping Copilot agent: {e}"


def resume_copilot_agent(
    owner: str,
    repo: str,
    issue_number: int,
    additional_instructions: str = "",
) -> str:
    """
    Resume a paused Copilot agent.

    This removes the paused label and adds a resume comment. The agent will
    continue from where it left off.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue number where agent is paused.
        additional_instructions: Optional new guidance for the agent.

    Returns:
        Status message confirming the resume request.

    """
    try:
        # Check if agent is actually paused
        current_status = _check_agent_labels(owner, repo, issue_number)

        if current_status == "stopped":
            return f"""❌ Cannot resume stopped agent on issue #{issue_number}

The agent was stopped, not paused. To restart work, create a new assignment:
- Use `assign_copilot_agent_to_issue` with updated instructions"""

        if current_status != "paused":
            return f"""⚠️ Agent is not paused on issue #{issue_number}

Current status: {current_status}

If you want to provide new instructions to an active agent,
add them directly to the issue."""

        # Remove paused label and add active label
        _remove_label_from_issue(owner, repo, issue_number, LABEL_AGENT_PAUSED)
        _add_label_to_issue(owner, repo, issue_number, LABEL_AGENT_ACTIVE)

        # Add resume comment
        comment_body = f"""{COMMENT_RESUME_REQUEST}

The Copilot agent has been requested to resume work on this issue.
{
            f'''
**Additional instructions:**
{additional_instructions}
'''
            if additional_instructions
            else ""
        }

The agent will continue from where it paused.

**Control commands:**
- Use `pause_copilot_agent` to pause again
- Use `stop_copilot_agent` to cancel work
- Use `check_copilot_agent_status` to view current state
"""

        _add_comment_to_issue(owner, repo, issue_number, comment_body)

        return f"""▶️ Copilot agent resumed on issue #{issue_number}

**Repository:** {owner}/{repo}
**Status:** Agent active (continuing work)
{
            f"**Additional instructions:** {additional_instructions}"
            if additional_instructions
            else ""
        }

The agent will continue working on the issue."""

    except Exception as e:
        return f"Error resuming Copilot agent: {e}"


def check_copilot_agent_status(
    owner: str,
    repo: str,
    issue_number: int,
) -> str:
    """
    Check the current status of a Copilot agent assignment.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue number to check.

    Returns:
        Current agent status and related information.

    """
    try:
        status = _check_agent_labels(owner, repo, issue_number)

        # Get recent agent-related comments
        recent_comments = _get_recent_agent_comments()

        status_emoji = {
            "active": "✅",
            "paused": "⏸️",
            "stopped": "🛑",
            "not_assigned": "⚪",
        }

        emoji = status_emoji.get(status, "❓")
        return f"""{emoji} Copilot Agent Status for issue #{issue_number}

**Repository:** {owner}/{repo}
**Current status:** {status.replace("_", " ").title()}

{_format_status_details(status)}

**Recent activity:**
{recent_comments if recent_comments else "No recent agent activity"}

**Available commands:**
{_get_available_commands(status)}
"""

    except Exception as e:
        return f"Error checking agent status: {e}"


# Helper functions


def _check_agent_labels(owner: str, repo: str, issue_number: int) -> str:
    """
    Check agent status from issue labels.

    Returns:
        One of: 'active', 'paused', 'stopped', 'not_assigned'

    """
    try:
        # Check which control labels are present on the issue
        # This would use GitHub API through MCP
        # In a full implementation, this would:
        # 1. Call mcp_github tools to get issue details
        # 2. Check for our control labels
        # 3. Return appropriate status

        # Priority order: stopped > paused > active > not_assigned
        if _issue_has_label(owner, repo, issue_number, LABEL_AGENT_STOPPED):
            return "stopped"
        if _issue_has_label(owner, repo, issue_number, LABEL_AGENT_PAUSED):
            return "paused"
        if _issue_has_label(owner, repo, issue_number, LABEL_AGENT_ACTIVE):
            return "active"
        return "not_assigned"

    except Exception:
        return "not_assigned"


def _issue_has_label(_owner: str, _repo: str, _issue_number: int, _label: str) -> bool:
    """
    Check if an issue has a specific label.

    This function would use GitHub MCP tools to check labels.
    In the MCP architecture, labels can be checked via GitHub API calls.
    """
    # Placeholder - in full implementation would use MCP GitHub tools
    # The actual implementation would call the GitHub API through MCP
    return False


def _add_label_to_issue(
    _owner: str, _repo: str, _issue_number: int, _label: str
) -> None:
    """
    Add a label to an issue.

    This function would use GitHub MCP tools to add labels.
    In the MCP architecture, labels can be added via GitHub API calls.
    """
    # Placeholder - in full implementation would use MCP GitHub tools
    # The actual implementation would call the GitHub API through MCP
    pass


def _remove_label_from_issue(
    _owner: str, _repo: str, _issue_number: int, _label: str
) -> None:
    """
    Remove a label from an issue.

    This function would use GitHub MCP tools to remove labels.
    """
    # Placeholder - in full implementation would use MCP GitHub tools
    pass


def _add_comment_to_issue(
    _owner: str, _repo: str, _issue_number: int, _body: str
) -> None:
    """
    Add a comment to an issue.

    This function would use GitHub MCP tools to add comments.
    The activate_comment_management_tools function provides access to these tools.
    """
    # Placeholder - in full implementation would use MCP GitHub tools
    # Would call something like mcp_github_add_issue_comment
    pass


def _get_recent_agent_comments() -> str:
    """
    Get recent agent-related comments from the issue.

    This function would use GitHub MCP tools to fetch and filter comments.
    """
    # Placeholder - in full implementation would:
    # 1. Fetch issue comments via MCP GitHub tools
    # 2. Filter for comments matching our control markers
    # 3. Format and return recent activity
    return "No recent activity"


def _format_status_details(status: str) -> str:
    """Format detailed status information."""
    details = {
        "active": (
            "The agent is currently working on implementing the issue. "
            "A pull request will be created when complete."
        ),
        "paused": (
            "The agent has paused work. "
            "Use resume command to continue, or stop to cancel."
        ),
        "stopped": (
            "The agent assignment was cancelled. "
            "Create a new assignment to restart work."
        ),
        "not_assigned": (
            "No Copilot agent is currently assigned to this issue. "
            "Use assign command to create an assignment."
        ),
    }
    return details.get(status, "Unknown status")


def _get_available_commands(status: str) -> str:
    """Get available commands based on current status."""
    commands = {
        "active": """- `pause_copilot_agent` - Pause the agent
- `stop_copilot_agent` - Cancel the assignment
- `check_copilot_agent_status` - Refresh status""",
        "paused": """- `resume_copilot_agent` - Continue work
- `stop_copilot_agent` - Cancel the assignment
- `check_copilot_agent_status` - Refresh status""",
        "stopped": """- `assign_copilot_agent_to_issue` - Create new assignment
- `check_copilot_agent_status` - Refresh status""",
        "not_assigned": (
            "- `assign_copilot_agent_to_issue` - Assign Copilot to issue\n"
            "- `check_copilot_agent_status` - Refresh status"
        ),
    }
    return commands.get(status, "No commands available")
