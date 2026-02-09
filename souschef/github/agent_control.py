"""
GitHub Copilot agent control for multi-platform orchestration.

[PLANNED FEATURE] This module provides infrastructure for managing GitHub
Copilot agent lifecycles (pause/stop/resume) across multiple platform
migration tasks. This enables:

- Multi-platform migrations: Orchestrate Puppet, SaltStack, CFEngine to
  Ansible conversions
- Parallel workflows: Assign agents to different repositories/platforms
  simultaneously
- Progress tracking: Monitor status across distributed migration tasks
- Repository analysis: Automatically identify and process migration
  candidates

State will be tracked via GitHub issue comments and labels when fully
implemented.

IMPLEMENTATION STATUS:
- Helper functions are currently placeholders (will connect to GitHub API
  via MCP tools)
- Core API structure is stable and serves as specification for full
  implementation
- All tests mock the GitHub integration and document expected behaviour

See souschef/github/agent_control.py for implementation notes.
"""

import os
from typing import TYPE_CHECKING
from urllib.parse import quote

if TYPE_CHECKING:
    import requests as requests_module
else:
    try:
        import requests as requests_module
    except ImportError:
        requests_module = None  # type: ignore[assignment]

# Agent state management via labels
LABEL_AGENT_ACTIVE = "copilot-agent:active"
LABEL_AGENT_PAUSED = "copilot-agent:paused"
LABEL_AGENT_STOPPED = "copilot-agent:stopped"

# Comment markers for agent state changes
COMMENT_PAUSE_REQUEST = "🔸 **Copilot Agent Paused**"
COMMENT_STOP_REQUEST = "🛑 **Copilot Agent Stopped**"
COMMENT_RESUME_REQUEST = "▶️ **Copilot Agent Resumed**"

# GitHub API settings
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_TIMEOUT_SECONDS = 10


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

    except RuntimeError as e:
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

    except RuntimeError as e:
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

    except RuntimeError as e:
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
        recent_comments = _get_recent_agent_comments(owner, repo, issue_number)

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

    except RuntimeError as e:
        return f"Error checking agent status: {e}"


# Helper functions


def _validate_github_token() -> str:
    """
    Validate GitHub token is configured.

    Returns:
        GitHub token from environment.

    Raises:
        RuntimeError: If token not found in GITHUB_TOKEN or GH_TOKEN.

    """
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("GitHub token not configured in GITHUB_TOKEN or GH_TOKEN")
    return token


def _check_agent_labels(owner: str, repo: str, issue_number: int) -> str:
    """
    Check agent status from issue labels.

    Returns:
        One of: 'active', 'paused', 'stopped', 'not_assigned'

    Raises:
        RuntimeError: If GitHub API fails or token is not configured.

    """
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


def _issue_has_label(_owner: str, _repo: str, _issue_number: int, _label: str) -> bool:
    """
    Check if an issue has a specific label.

    This function would use GitHub MCP tools to check labels.
    In the MCP architecture, labels can be checked via GitHub API calls.
    """
    response = _github_request(
        "GET",
        f"/repos/{_owner}/{_repo}/issues/{_issue_number}/labels",
    )
    labels = response.json()
    if not isinstance(labels, list):
        return False

    return any(
        label.get("name") == _label for label in labels if isinstance(label, dict)
    )


def _add_label_to_issue(
    _owner: str, _repo: str, _issue_number: int, _label: str
) -> None:
    """
    Add a label to an issue.

    This function would use GitHub MCP tools to add labels.
    In the MCP architecture, labels can be added via GitHub API calls.
    """
    _github_request(
        "POST",
        f"/repos/{_owner}/{_repo}/issues/{_issue_number}/labels",
        json_data={"labels": [_label]},
    )


def _remove_label_from_issue(
    _owner: str, _repo: str, _issue_number: int, _label: str
) -> None:
    """
    Remove a label from an issue.

    This function would use GitHub MCP tools to remove labels.
    """
    label_path = quote(_label, safe="")
    _github_request(
        "DELETE",
        f"/repos/{_owner}/{_repo}/issues/{_issue_number}/labels/{label_path}",
        allow_not_found=True,
    )


def _add_comment_to_issue(
    _owner: str, _repo: str, _issue_number: int, _body: str
) -> None:
    """
    Add a comment to an issue.

    This function would use GitHub MCP tools to add comments.
    The activate_comment_management_tools function provides access to these
    tools.
    """
    _github_request(
        "POST",
        f"/repos/{_owner}/{_repo}/issues/{_issue_number}/comments",
        json_data={"body": _body},
    )


def _get_recent_agent_comments(owner: str, repo: str, issue_number: int) -> str:
    """
    Get recent agent-related comments from the issue.

    This function would use GitHub MCP tools to fetch and filter comments.
    """
    response = _github_request(
        "GET",
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
        params={"per_page": "10"},
    )
    comments = response.json()
    if not isinstance(comments, list):
        return "No recent activity"

    markers = (COMMENT_PAUSE_REQUEST, COMMENT_STOP_REQUEST, COMMENT_RESUME_REQUEST)
    recent = []
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        body = comment.get("body", "")
        if any(marker in body for marker in markers):
            recent.append(body)

    if not recent:
        return "No recent activity"

    return "\n\n".join(recent[-3:])


def _github_request(
    method: str,
    path: str,
    params: dict[str, str] | None = None,
    json_data: dict[str, object] | None = None,
    timeout: float | None = None,
    allow_not_found: bool = False,
):
    """Perform a GitHub API request with standard headers and error handling."""
    if requests_module is None:
        raise RuntimeError("requests library not installed")

    token = _validate_github_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "souschef-agent-control",
    }

    effective_timeout = timeout or GITHUB_API_TIMEOUT_SECONDS
    response = requests_module.request(
        method,
        f"{GITHUB_API_BASE_URL}{path}",
        headers=headers,
        params=params,
        json=json_data,
        timeout=effective_timeout,
    )
    if allow_not_found and response.status_code == 404:
        return response
    if response.status_code >= 400:
        raise RuntimeError(
            f"GitHub API error {response.status_code}: {response.text.strip()}"
        )

    return response


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
