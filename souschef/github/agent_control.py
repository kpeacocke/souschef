"""
GitHub Copilot agent control for multi-platform orchestration.

This module maintains tracking labels and comments on GitHub issues. It does
not assign, pause, stop, or resume a Copilot agent.
"""

import os
import re
from urllib.parse import quote

import requests

# Agent state management via labels
LABEL_AGENT_ACTIVE = "copilot-agent:active"
LABEL_AGENT_PAUSED = "copilot-agent:paused"
LABEL_AGENT_STOPPED = "copilot-agent:stopped"

# Comment markers for agent state changes
COMMENT_PAUSE_REQUEST = "**SousChef Copilot-agent tracking state: Paused**"
COMMENT_STOP_REQUEST = "**SousChef Copilot-agent tracking state: Stopped**"
COMMENT_RESUME_REQUEST = "**SousChef Copilot-agent tracking state: Resumed**"

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
    Add the active SousChef tracking label to a GitHub issue.

    Args:
        owner: Repository owner (username or organisation).
        repo: Repository name.
        issue_number: Issue number to update.
        base_ref: Accepted for compatibility, but not sent to an agent service.
        custom_instructions: Accepted for compatibility, but not sent to an agent.

    Returns:
        Status message explaining the tracking-label change.

    """
    try:
        _add_label_to_issue(owner, repo, issue_number, LABEL_AGENT_ACTIVE)
        ignored_inputs = ", ".join(
            name
            for name, value in (
                ("base_ref", base_ref),
                ("custom_instructions", custom_instructions),
            )
            if value
        )
        ignored_inputs = ignored_inputs or "no optional inputs"

        return f"""Copilot-agent tracking label added to issue #{issue_number}

**Repository:** {owner}/{repo}
**Tracking status:** active label added

No Copilot agent was assigned or started. These inputs were not sent to an
agent service: {ignored_inputs}.
"""

    except RuntimeError as e:
        return f"Error updating Copilot-agent tracking labels: {e}"


def pause_copilot_agent(
    owner: str,
    repo: str,
    issue_number: int,
    reason: str = "",
) -> str:
    """
    Record paused tracking state with labels and an issue comment.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue number to update.
        reason: Optional reason, posted in an issue comment visible to its readers.

    Returns:
        Status message explaining the tracking-label and comment changes.

    """
    try:
        _add_label_to_issue(owner, repo, issue_number, LABEL_AGENT_PAUSED)
        _remove_label_from_issue(owner, repo, issue_number, LABEL_AGENT_ACTIVE)

        comment_body = f"""{COMMENT_PAUSE_REQUEST}

This is tracking metadata only. No Copilot agent was contacted or paused.
{f"**Reason:** {reason}" if reason else ""}
"""

        _add_comment_to_issue(owner, repo, issue_number, comment_body)

        return f"""Pause tracking state recorded for issue #{issue_number}

**Repository:** {owner}/{repo}
**Tracking status:** paused label added; active label removed
{f"**Reason:** {reason}" if reason else ""}

No Copilot agent was paused."""

    except RuntimeError as e:
        return f"Error updating Copilot-agent tracking state: {e}"


def stop_copilot_agent(
    owner: str,
    repo: str,
    issue_number: int,
    reason: str = "",
) -> str:
    """
    Record stopped tracking state with labels and an issue comment.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue number to update.
        reason: Optional reason, posted in an issue comment visible to its readers.

    Returns:
        Status message explaining the tracking-label and comment changes.

    """
    try:
        _add_label_to_issue(owner, repo, issue_number, LABEL_AGENT_STOPPED)
        _remove_label_from_issue(owner, repo, issue_number, LABEL_AGENT_ACTIVE)
        _remove_label_from_issue(owner, repo, issue_number, LABEL_AGENT_PAUSED)

        comment_body = f"""{COMMENT_STOP_REQUEST}

This is tracking metadata only. No Copilot agent was contacted or stopped.
{f"**Reason:** {reason}" if reason else ""}
"""

        _add_comment_to_issue(owner, repo, issue_number, comment_body)

        return f"""Stop tracking state recorded for issue #{issue_number}

**Repository:** {owner}/{repo}
**Tracking status:** stopped label added; active and paused labels removed
{f"**Reason:** {reason}" if reason else ""}

No Copilot agent was stopped."""

    except RuntimeError as e:
        return f"Error updating Copilot-agent tracking state: {e}"


def resume_copilot_agent(
    owner: str,
    repo: str,
    issue_number: int,
    additional_instructions: str = "",
) -> str:
    """
    Record active tracking state with labels and an issue comment.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue number to update.
        additional_instructions: Optional text posted in an issue comment; not
            sent to an agent service.

    Returns:
        Status message explaining the tracking-label and comment changes.

    """
    try:
        current_status = _check_agent_labels(owner, repo, issue_number)

        if current_status == "stopped":
            return f"""Cannot update stopped tracking state on issue #{issue_number}

The stopped label is present. No Copilot agent was resumed."""

        if current_status != "paused":
            return f"""Tracking status is not paused for issue #{issue_number}

Current tracking status: {current_status}. No Copilot agent was contacted."""

        _remove_label_from_issue(owner, repo, issue_number, LABEL_AGENT_PAUSED)
        _add_label_to_issue(owner, repo, issue_number, LABEL_AGENT_ACTIVE)

        comment_body = f"""{COMMENT_RESUME_REQUEST}

This is tracking metadata only. No Copilot agent was contacted or resumed.
{
            f'''
**Additional instructions:**
{additional_instructions}
'''
            if additional_instructions
            else ""
        }

"""

        _add_comment_to_issue(owner, repo, issue_number, comment_body)

        return f"""Resume tracking state recorded for issue #{issue_number}

**Repository:** {owner}/{repo}
**Tracking status:** active label added; paused label removed
{
            f"**Additional instructions:** {additional_instructions}"
            if additional_instructions
            else ""
        }

No Copilot agent was resumed."""

    except RuntimeError as e:
        return f"Error updating Copilot-agent tracking state: {e}"


def check_copilot_agent_status(
    owner: str,
    repo: str,
    issue_number: int,
) -> str:
    """
    Read the SousChef tracking labels and comments for an issue.

    Args:
        owner: Repository owner.
        repo: Repository name.
        issue_number: Issue number to check.

    Returns:
        Tracking status and related comments, not live agent status.

    """
    try:
        status = _check_agent_labels(owner, repo, issue_number)

        recent_comments = _get_recent_agent_comments(owner, repo, issue_number)

        status_emoji = {
            "active": "✅",
            "paused": "⏸️",
            "stopped": "🛑",
            "not_assigned": "⚪",
        }

        emoji = status_emoji.get(status, "❓")
        return f"""{emoji} Copilot-agent tracking status for issue #{issue_number}

**Repository:** {owner}/{repo}
**Tracking status:** {status.replace("_", " ").title()}

{_format_status_details(status)}

**Recent tracking comments:**
{recent_comments if recent_comments else "No recent agent activity"}

These labels and comments do not reflect or control a live Copilot agent.

**Tracking-label commands:**
{_get_available_commands(status)}
"""

    except RuntimeError as e:
        return f"Error reading Copilot-agent tracking state: {e}"


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
    # Priority order for tracking labels: stopped > paused > active > absent.
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

    Reads the issue labels through the GitHub REST API.
    """
    response = _github_request(
        "GET",
        f"/repos/{_owner}/{_repo}/issues/{_issue_number}/labels",
    )
    if response is None:
        return False
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

    Adds a tracking label through the GitHub REST API.
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

    Removes a tracking label through the GitHub REST API.
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

    Adds a tracking comment through the GitHub REST API.
    """
    _github_request(
        "POST",
        f"/repos/{_owner}/{_repo}/issues/{_issue_number}/comments",
        json_data={"body": _body},
    )


def _get_recent_agent_comments(owner: str, repo: str, issue_number: int) -> str:
    """Get recent SousChef tracking comments from the issue."""
    response = _github_request(
        "GET",
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
        params={"per_page": "10"},
    )
    if response is None:
        return "No recent activity (issue not found)"
    comments = response.json()
    if not isinstance(comments, list):
        return "No recent activity (unexpected response)"

    markers = (COMMENT_PAUSE_REQUEST, COMMENT_STOP_REQUEST, COMMENT_RESUME_REQUEST)
    recent = []
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        body = comment.get("body", "")
        if any(marker in body for marker in markers):
            recent.append(body)

    if not recent:
        return "No recent tracking comments"

    return "\n\n".join(recent[-3:])


def _github_request(
    method: str,
    path: str,
    params: dict[str, str] | None = None,
    json_data: dict[str, object] | None = None,
    timeout: float | None = None,
    allow_not_found: bool = False,
) -> requests.Response | None:
    """
    Perform a GitHub API request with standard headers and error handling.

    Returns:
        Response object for successful requests, or None when allow_not_found is
        True and the response status is 404.

    """
    issue_path_pattern = (
        r"/repos/[A-Za-z0-9][A-Za-z0-9-]{0,38}/"
        r"(?!\.{1,2}/)[A-Za-z0-9._-]{1,100}/issues/[1-9][0-9]*"
        r"(?:/(?:labels(?:/[^/]+)?|comments))?"
    )
    if not re.fullmatch(issue_path_pattern, path):
        raise RuntimeError("Invalid GitHub issue API path")

    token = _validate_github_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "souschef-agent-control",
    }

    effective_timeout = timeout or GITHUB_API_TIMEOUT_SECONDS
    try:
        response = requests.request(
            method,
            f"{GITHUB_API_BASE_URL}{path}",
            headers=headers,
            params=params,
            json=json_data,
            timeout=effective_timeout,
        )
    except Exception as e:
        raise RuntimeError(f"GitHub API request failed: {e}") from e

    if allow_not_found and response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise RuntimeError(
            f"GitHub API error {response.status_code}: {response.text.strip()}"
        )

    return response


def _format_status_details(status: str) -> str:
    """Format detailed status information."""
    details = {
        "active": (
            "The active tracking label is present. This does not confirm that "
            "an agent is working on the issue."
        ),
        "paused": ("The paused tracking label is present. No agent pause was issued."),
        "stopped": ("The stopped tracking label is present. No agent was stopped."),
        "not_assigned": (
            "No SousChef Copilot-agent tracking label is present. This does not "
            "confirm whether an agent was assigned elsewhere."
        ),
    }
    return details.get(status, "Unknown status")


def _get_available_commands(status: str) -> str:
    """Get label-tracking actions available for the current tracking status."""
    commands = {
        "active": """- `pause_copilot_agent` - Update tracking labels and comment
- `stop_copilot_agent` - Update tracking labels and comment
- `check_copilot_agent_status` - Read tracking state""",
        "paused": """- `resume_copilot_agent` - Update tracking labels and comment
- `stop_copilot_agent` - Update tracking labels and comment
- `check_copilot_agent_status` - Read tracking state""",
        "stopped": """- `assign_copilot_agent_to_issue` - Add the active tracking label
- `check_copilot_agent_status` - Read tracking state""",
        "not_assigned": (
            "- `assign_copilot_agent_to_issue` - Add the active tracking label\n"
            "- `check_copilot_agent_status` - Read tracking state"
        ),
    }
    return commands.get(status, "No commands available")
