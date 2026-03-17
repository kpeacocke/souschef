"""
Bash script parser for SousChef.

Parses Bash provisioning scripts and extracts structured patterns
including package installs, file writes, service control, downloads,
user/group management, file permissions, git operations, archive
extraction, sed in-place edits, cron jobs, firewall rules, hostname
changes, environment variables, sensitive data detection, and
configuration-management tool escape calls.
Emits an intermediate representation with confidence scores so that
low-confidence sections can fall back to plain ``ansible.builtin.shell``
tasks with warnings.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from souschef.core.constants import (
    ERROR_FILE_NOT_FOUND,
    ERROR_IS_DIRECTORY,
    ERROR_PERMISSION_DENIED,
)
from souschef.core.path_utils import (
    _ensure_within_base_path,
    _get_workspace_root,
    _normalize_path,
    safe_read_text,
)

# ---------------------------------------------------------------------------
# Pattern constants
# ---------------------------------------------------------------------------

# User management
_USER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("create", re.compile(r"\buseradd\b[^\n]*", re.IGNORECASE)),
    ("create", re.compile(r"\badduser\b[^\n]*", re.IGNORECASE)),
    ("modify", re.compile(r"\busermod\b[^\n]*", re.IGNORECASE)),
    ("remove", re.compile(r"\buserdel\b[^\n]*", re.IGNORECASE)),
]

# Group management
_GROUP_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("create", re.compile(r"\bgroupadd\b[^\n]*", re.IGNORECASE)),
    ("modify", re.compile(r"\bgroupmod\b[^\n]*", re.IGNORECASE)),
    ("remove", re.compile(r"\bgroupdel\b[^\n]*", re.IGNORECASE)),
]

# File permissions
_CHMOD_PATTERN = re.compile(
    r"\bchmod\s+(-R\s+)?(\d{3,4}|[ugoa]+[+\-=][rwxst]+)\s+(\S+)",
    re.IGNORECASE,
)
_CHOWN_PATTERN = re.compile(
    r"\bchown\s+(-R\s+)?([^:\s]+(?::[^:\s]+)?)\s+(\S+)",
    re.IGNORECASE,
)

# Git operations
_GIT_CLONE_PATTERN = re.compile(
    r"\bgit\s+clone\s+(?:--[^\s]+\s+)*(\S+)(?:\s+(\S+))?",
    re.IGNORECASE,
)
_GIT_PULL_PATTERN = re.compile(r"\bgit\s+pull\b[^\n]*", re.IGNORECASE)
_GIT_CHECKOUT_PATTERN = re.compile(r"\bgit\s+checkout\s+(\S+)", re.IGNORECASE)

# Archive extraction
# Match tar command lines and parse tokens in Python so complexity stays linear
# for adversarial inputs (CWE-1333).
_TAR_LINE_PATTERN = re.compile(r"\btar\b[^\n]*", re.IGNORECASE)
_UNZIP_LINE_PATTERN = re.compile(r"\bunzip\b[^\n]*", re.IGNORECASE)

_TAR_ARCHIVE_SUFFIXES: tuple[str, ...] = (
    ".tar.gz",
    ".tgz",
    ".tar.bz2",
    ".tbz2",
    ".tar.xz",
    ".txz",
    ".tar.z",
    ".tar",
)

# sed in-place
_SED_INPLACE_PATTERN = re.compile(
    r"\bsed\s+(?:-i[^\s]*|--in-place[=\s][^\s]*)\s+[^\n]*",
    re.IGNORECASE,
)

# Cron
_CRON_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bcrontab\b[^\n]*", re.IGNORECASE),
    re.compile(
        r'(?:echo|printf)\s+["\'][^"\']*\*[^"\']*["\'].*(?:>+\s*/etc/cron|\|\s*crontab)',
        re.IGNORECASE,
    ),
]

# Firewall
_FIREWALL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "ufw",
        re.compile(
            r"\bufw\s+(?:allow|deny|limit|enable|disable|reject|delete|reset)\b[^\n]*",
            re.IGNORECASE,
        ),
    ),
    (
        "firewalld",
        re.compile(r"\bfirewall-cmd\b[^\n]*", re.IGNORECASE),
    ),
    (
        "iptables",
        re.compile(r"\biptables\s+-[AI]\b[^\n]*", re.IGNORECASE),
    ),
]

# Hostname
_HOSTNAME_PATTERN = re.compile(
    r"\bhostnamectl\s+set-hostname\s+(\S+)|\bhostname\s+(\S+)",
    re.IGNORECASE,
)

# Environment variables are parsed line-by-line in _extract_env_vars()
# using deterministic string operations to avoid regex backtracking risks
# on uncontrolled input (CWE-1333).

# Sensitive data – detect hardcoded secrets (no actual secrets stored)
_SENSITIVE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "password",
        re.compile(
            r'(?:password|passwd|pass)\s*[=:]\s*["\']?(?!\$\{)[^\s"\'$;]{4,}',
            re.IGNORECASE,
        ),
    ),
    (
        "api_key",
        re.compile(
            r"(?:api[_-]?key|secret[_-]?key|auth[_-]?token|access[_-]?token"
            r"|private[_-]?key)\s*[=:]\s*[\"']?[A-Za-z0-9_\-]{12,}",
            re.IGNORECASE,
        ),
    ),
    (
        "private_key_material",
        re.compile(
            r"-----BEGIN\s+(?:RSA|EC|DSA|OPENSSH)\s+PRIVATE\s+KEY",
            re.IGNORECASE,
        ),
    ),
]

# Salt / Puppet / Chef escape-call detection
_CM_ESCAPE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "salt",
        re.compile(r"\bsalt(?:-call|-minion|-master|-key)?\b[^\n]*", re.IGNORECASE),
    ),
    (
        "puppet",
        re.compile(
            r"\bpuppet\s+(?:apply|agent|module|resource|lookup)\b[^\n]*",
            re.IGNORECASE,
        ),
    ),
    (
        "chef",
        re.compile(
            r"\b(?:chef-client|chef-solo|chef-run|knife|berkshelf|berks"
            r"|cookstyle|foodcritic)\b[^\n]*",
            re.IGNORECASE,
        ),
    ),
]

# Package managers and their install sub-commands
_PKG_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "apt",
        "ansible.builtin.apt",
        re.compile(
            r"\bapt(?:-get)?\s+(?:install|upgrade|dist-upgrade)\b[^\n]*",
            re.IGNORECASE,
        ),
    ),
    (
        "yum",
        "ansible.builtin.yum",
        re.compile(r"\byum\s+install\b[^\n]*", re.IGNORECASE),
    ),
    (
        "dnf",
        "ansible.builtin.dnf",
        re.compile(r"\bdnf\s+install\b[^\n]*", re.IGNORECASE),
    ),
    (
        "zypper",
        "community.general.zypper",
        re.compile(r"\bzypper\s+install\b[^\n]*", re.IGNORECASE),
    ),
    (
        "apk",
        "community.general.apk",
        re.compile(r"\bapk\s+add\b[^\n]*", re.IGNORECASE),
    ),
    (
        "pip",
        "ansible.builtin.pip",
        re.compile(r"\bpip3?\s+install\b[^\n]*", re.IGNORECASE),
    ),
]

# Service control
_SERVICE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "systemctl",
        re.compile(
            r"\bsystemctl\s+(start|stop|restart|enable|disable|reload)\s+(\S+)",
            re.IGNORECASE,
        ),
    ),
    (
        "service",
        re.compile(
            r"\bservice\s+(\S+)\s+(start|stop|restart|reload)",
            re.IGNORECASE,
        ),
    ),
]

# File write operations (heredoc and redirect)
_FILE_WRITE_PATTERNS: list[re.Pattern[str]] = [
    # cat <<EOF > /path/to/file
    re.compile(r"cat\s+<<\s*'?(\w+)'?\s*>\s*(\S+)", re.IGNORECASE),
    # echo "..." > /path/to/file  or  echo "..." >> /path/to/file
    re.compile(r'echo\s+(?:"[^"]*"|\'[^\']*\'|\S+)\s+>+\s*(\S+)', re.IGNORECASE),
    # tee /path/to/file
    re.compile(r"\btee\s+(?:-a\s+)?(\S+)", re.IGNORECASE),
]

# Download operations
_DOWNLOAD_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "curl",
        re.compile(r"\bcurl\b[^\n]*", re.IGNORECASE),
    ),
    (
        "wget",
        re.compile(
            r"\bwget\s+(?:[^\n]*\s+)?(?:-O\s*(\S+)\s+)?(\S+)",
            re.IGNORECASE,
        ),
    ),
]

# Idempotency-risk indicators
_IDEMPOTENCY_RISKS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "unconditional_package_install",
        "Package install without idempotency guard (use 'state: present' in Ansible)",
        re.compile(
            r"\b(apt(?:-get)?|yum|dnf|zypper|apk)\s+install\s+(?!-y\s+--skip-broken)",
            re.IGNORECASE,
        ),
    ),
    (
        "unconditional_write",
        "File write without existence check may overwrite existing config",
        re.compile(r"\becho\b[^\n]*>(?!>)", re.IGNORECASE),
    ),
    (
        "raw_download",
        (
            "Download without checksum verification;"
            " consider ansible.builtin.get_url with checksum"
        ),
        re.compile(r"\b(curl|wget)\b[^\n]*", re.IGNORECASE),
    ),
    (
        "direct_service_start",
        "Direct service start; use ansible.builtin.service with state: started",
        re.compile(r"\bservice\s+\S+\s+start\b", re.IGNORECASE),
    ),
]

# Maximum script size to protect against very large inputs
_MAX_SCRIPT_SIZE = 500_000


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_bash_script(path: str) -> str:
    """
    Parse a Bash script and extract provisioning patterns.

    Reads the script, detects common provisioning operations (package
    management, service control, file writes, downloads), and returns a
    human-readable summary with confidence scores.  Low-confidence
    sections are flagged with shell-fallback warnings.

    Args:
        path: Path to the Bash script file.

    Returns:
        Formatted string describing detected patterns, warnings, and
        idempotency hints.  Returns an error message string on failure.

    """
    try:
        workspace = _get_workspace_root()
        normalised = _normalize_path(path)
        safe_path = _ensure_within_base_path(Path(normalised), workspace)
        content = safe_read_text(safe_path, workspace)
    except FileNotFoundError:
        return f"{ERROR_FILE_NOT_FOUND}: {path}"
    except IsADirectoryError:
        return f"{ERROR_IS_DIRECTORY}: {path}"
    except PermissionError:
        return f"{ERROR_PERMISSION_DENIED}: {path}"
    except (ValueError, OSError) as exc:
        return f"Error reading file: {exc}"

    return _format_parse_result(_parse_bash_content(content))


def parse_bash_script_content(content: str) -> dict[str, Any]:
    """
    Parse Bash script content and return structured IR dictionary.

    This is the programmatic companion to :func:`parse_bash_script`.  It
    accepts raw script content and returns a structured intermediate
    representation (IR) suitable for consumption by converters.

    Args:
        content: Raw Bash script text.

    Returns:
        Dictionary with keys ``packages``, ``services``, ``file_writes``,
        ``downloads``, ``idempotency_risks``, ``shell_fallbacks``, and
        ``warnings``.

    """
    if len(content) > _MAX_SCRIPT_SIZE:
        content = content[:_MAX_SCRIPT_SIZE]

    return _parse_bash_content(content)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_bash_content(content: str) -> dict[str, Any]:
    """
    Extract all pattern groups from raw script content.

    Args:
        content: Raw Bash script text.

    Returns:
        Structured dictionary of detected patterns.

    """
    lines = content.splitlines()
    result: dict[str, Any] = {
        "packages": [],
        "services": [],
        "file_writes": [],
        "downloads": [],
        "idempotency_risks": [],
        "shell_fallbacks": [],
        "warnings": [],
        "users": [],
        "groups": [],
        "file_perms": [],
        "git_ops": [],
        "archives": [],
        "sed_ops": [],
        "cron_jobs": [],
        "firewall_rules": [],
        "hostname_ops": [],
        "env_vars": [],
        "sensitive_data": [],
        "cm_escapes": [],
    }

    _extract_packages(content, result)
    _extract_services(content, result)
    _extract_file_writes(content, result)
    _extract_downloads(content, result)
    _extract_idempotency_risks(content, result)
    _extract_users(content, result)
    _extract_groups(content, result)
    _extract_file_perms(content, result)
    _extract_git_ops(content, result)
    _extract_archives(content, result)
    _extract_sed_ops(content, result)
    _extract_cron_jobs(content, result)
    _extract_firewall_rules(content, result)
    _extract_hostname_ops(content, result)
    _extract_env_vars(content, result)
    _extract_sensitive_data(content, result)
    _extract_cm_escapes(content, result)
    _identify_shell_fallbacks(lines, result)

    return result


def _line_number(content: str, match_start: int) -> int:
    """Return the 1-based line number for a character offset in *content*."""
    return content.count("\n", 0, match_start) + 1


def _extract_packages(
    content: str,
    result: dict[str, Any],
) -> None:
    """Populate *result['packages']* from *content*."""
    for manager, ansible_module, pattern in _PKG_PATTERNS:
        for match in pattern.finditer(content):
            raw_line = match.group(0).strip()
            packages = _parse_package_names(raw_line, manager)
            confidence = 0.9 if packages else 0.6
            result["packages"].append(
                {
                    "manager": manager,
                    "ansible_module": ansible_module,
                    "raw": raw_line,
                    "packages": packages,
                    "confidence": confidence,
                    "line": _line_number(content, match.start()),
                }
            )


def _parse_package_names(raw: str, manager: str) -> list[str]:
    """
    Extract individual package names from a raw install command.

    Args:
        raw: Raw install command line.
        manager: Package manager name (``apt``, ``yum``, etc.).

    Returns:
        List of package name strings.

    """
    # Strip the command prefix up to and including sub-command
    for prefix in (
        f"{manager}-get install",
        f"{manager} install",
        f"{manager} upgrade",
        f"{manager} dist-upgrade",
        f"{manager} add",
    ):
        idx = raw.lower().find(prefix)
        if idx != -1:
            raw = raw[idx + len(prefix) :]
            break

    tokens = raw.split()
    # Filter out flags and common options
    return [t for t in tokens if not t.startswith("-") and t not in {"|", "&&", "||"}]


def _extract_services(
    content: str,
    result: dict[str, Any],
) -> None:
    """Populate *result['services']* from *content*."""
    for manager, pattern in _SERVICE_PATTERNS:
        for match in pattern.finditer(content):
            if manager == "systemctl":
                action, name = match.group(1), match.group(2)
            else:
                name, action = match.group(1), match.group(2)
            result["services"].append(
                {
                    "manager": manager,
                    "name": name,
                    "action": action.lower(),
                    "raw": match.group(0).strip(),
                    "confidence": 0.95,
                    "line": _line_number(content, match.start()),
                }
            )


def _extract_file_writes(
    content: str,
    result: dict[str, Any],
) -> None:
    """Populate *result['file_writes']* from *content*."""
    for pattern in _FILE_WRITE_PATTERNS:
        for match in pattern.finditer(content):
            # Destination is in the last non-None group
            dest = next(
                (g for g in reversed(match.groups()) if g is not None),
                match.group(0).split()[-1],
            )
            result["file_writes"].append(
                {
                    "destination": dest,
                    "raw": match.group(0).strip(),
                    "confidence": 0.75,
                    "line": _line_number(content, match.start()),
                }
            )


def _extract_downloads(
    content: str,
    result: dict[str, Any],
) -> None:
    """Populate *result['downloads']* from *content*."""
    for tool, pattern in _DOWNLOAD_PATTERNS:
        for match in pattern.finditer(content):
            url_match = re.search(r"https?://\S+", match.group(0))
            url = url_match.group(0) if url_match else ""
            result["downloads"].append(
                {
                    "tool": tool,
                    "url": url,
                    "raw": match.group(0).strip(),
                    "confidence": 0.7,
                    "line": _line_number(content, match.start()),
                }
            )


def _extract_idempotency_risks(
    content: str,
    result: dict[str, Any],
) -> None:
    """Populate *result['idempotency_risks']* from *content*."""
    for risk_type, suggestion, pattern in _IDEMPOTENCY_RISKS:
        for match in pattern.finditer(content):
            result["idempotency_risks"].append(
                {
                    "type": risk_type,
                    "suggestion": suggestion,
                    "raw": match.group(0).strip(),
                    "line": _line_number(content, match.start()),
                }
            )


def _identify_shell_fallbacks(
    lines: list[str],
    result: dict[str, Any],
) -> None:
    """
    Identify lines that cannot be mapped to a structured module.

    Lines that contain shell constructs but are not matched by any
    pattern extractor are added as shell-fallback items with a warning.

    Args:
        lines: Script lines.
        result: Result dictionary to update in-place.

    """
    known_commands = {
        "apt",
        "apt-get",
        "yum",
        "dnf",
        "zypper",
        "apk",
        "pip",
        "pip3",
        "systemctl",
        "service",
        "curl",
        "wget",
        "echo",
        "cat",
        "tee",
        "#",
        "export",
        "source",
        ".",
        "set",
        "shopt",
        "#!/",
    }
    known_commands.update(
        {
            "useradd",
            "adduser",
            "usermod",
            "userdel",
            "groupadd",
            "groupmod",
            "groupdel",
            "chmod",
            "chown",
            "chgrp",
            "git",
            "tar",
            "unzip",
            "gzip",
            "gunzip",
            "sed",
            "awk",
            "grep",
            "find",
            "crontab",
            "ufw",
            "firewall-cmd",
            "iptables",
            "hostname",
            "hostnamectl",
            "mkdir",
            "rmdir",
            "rm",
            "mv",
            "cp",
            "ln",
            "touch",
            "sudo",
            "su",
            "ssh",
            "scp",
            "sftp",
            "rsync",
            "python",
            "python3",
            "ruby",
            "perl",
            "node",
            "salt",
            "salt-call",
            "puppet",
            "chef-client",
            "systemd-analyze",
            "journalctl",
            "logger",
            "mount",
            "umount",
            "df",
            "du",
            "id",
            "whoami",
            "groups",
            "date",
            "sleep",
            "wait",
            "printf",
            "read",
            "test",
            "[",
            "[[",
            "function",
            "local",
            "return",
            "exit",
            "if",
            "fi",
            "else",
            "elif",
            "then",
            "for",
            "while",
            "do",
            "done",
            "in",
            "case",
            "esac",
            "true",
            "false",
        }
    )
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        first_token = stripped.split()[0].lstrip("./")
        if first_token.lower() not in known_commands:
            result["shell_fallbacks"].append(
                {
                    "line": lineno,
                    "raw": stripped,
                    "warning": (
                        "No structured Ansible module mapping found; "
                        "will fall back to ansible.builtin.shell"
                    ),
                }
            )


def _extract_users(content: str, result: dict[str, Any]) -> None:
    """
    Populate *result['users']* from *content*.

    Args:
        content: Raw Bash script text.
        result: Result dictionary to update in-place.

    """
    for action, pattern in _USER_PATTERNS:
        for match in pattern.finditer(content):
            result["users"].append(
                {
                    "action": action,
                    "raw": match.group(0).strip(),
                    "line": _line_number(content, match.start()),
                    "confidence": 0.9,
                }
            )


def _extract_groups(content: str, result: dict[str, Any]) -> None:
    """
    Populate *result['groups']* from *content*.

    Args:
        content: Raw Bash script text.
        result: Result dictionary to update in-place.

    """
    for action, pattern in _GROUP_PATTERNS:
        for match in pattern.finditer(content):
            result["groups"].append(
                {
                    "action": action,
                    "raw": match.group(0).strip(),
                    "line": _line_number(content, match.start()),
                    "confidence": 0.9,
                }
            )


def _extract_file_perms(content: str, result: dict[str, Any]) -> None:
    """
    Populate *result['file_perms']* from *content*.

    Detects ``chmod`` and ``chown`` operations.

    Args:
        content: Raw Bash script text.
        result: Result dictionary to update in-place.

    """
    for match in _CHMOD_PATTERN.finditer(content):
        recursive_flag = match.group(1)
        result["file_perms"].append(
            {
                "op": "chmod",
                "mode": match.group(2),
                "owner": None,
                "path": match.group(3),
                "recursive": recursive_flag is not None,
                "raw": match.group(0).strip(),
                "line": _line_number(content, match.start()),
                "confidence": 0.85,
            }
        )
    for match in _CHOWN_PATTERN.finditer(content):
        recursive_flag = match.group(1)
        owner_str = match.group(2)
        result["file_perms"].append(
            {
                "op": "chown",
                "mode": None,
                "owner": owner_str,
                "path": match.group(3),
                "recursive": recursive_flag is not None,
                "raw": match.group(0).strip(),
                "line": _line_number(content, match.start()),
                "confidence": 0.85,
            }
        )


def _extract_git_ops(content: str, result: dict[str, Any]) -> None:
    """
    Populate *result['git_ops']* from *content*.

    Detects ``git clone``, ``git pull``, and ``git checkout`` operations.

    Args:
        content: Raw Bash script text.
        result: Result dictionary to update in-place.

    """
    for match in _GIT_CLONE_PATTERN.finditer(content):
        result["git_ops"].append(
            {
                "action": "clone",
                "repo": match.group(1),
                "dest": match.group(2),
                "raw": match.group(0).strip(),
                "line": _line_number(content, match.start()),
                "confidence": 0.9,
            }
        )
    for match in _GIT_PULL_PATTERN.finditer(content):
        result["git_ops"].append(
            {
                "action": "pull",
                "repo": None,
                "dest": None,
                "raw": match.group(0).strip(),
                "line": _line_number(content, match.start()),
                "confidence": 0.9,
            }
        )
    for match in _GIT_CHECKOUT_PATTERN.finditer(content):
        result["git_ops"].append(
            {
                "action": "checkout",
                "repo": None,
                "dest": match.group(1),
                "raw": match.group(0).strip(),
                "line": _line_number(content, match.start()),
                "confidence": 0.9,
            }
        )


def _extract_archives(content: str, result: dict[str, Any]) -> None:
    """
    Populate *result['archives']* from *content*.

    Detects ``tar`` extraction and ``unzip`` operations.

    Args:
        content: Raw Bash script text.
        result: Result dictionary to update in-place.

    """
    for match in _TAR_LINE_PATTERN.finditer(content):
        source = _extract_tar_source(match.group(0))
        if source is None:
            continue
        result["archives"].append(
            {
                "tool": "tar",
                "source": source,
                "raw": match.group(0).strip(),
                "line": _line_number(content, match.start()),
                "confidence": 0.85,
            }
        )
    for match in _UNZIP_LINE_PATTERN.finditer(content):
        source = _extract_unzip_source(match.group(0))
        if source is None:
            continue
        result["archives"].append(
            {
                "tool": "unzip",
                "source": source,
                "raw": match.group(0).strip(),
                "line": _line_number(content, match.start()),
                "confidence": 0.85,
            }
        )


def _extract_unzip_source(raw_line: str) -> str | None:
    """
    Extract the zip source path from an unzip command line.

    Uses token parsing rather than a complex regular expression so matching
    stays linear even for adversarial input containing repeated dashes or tabs.

    Args:
        raw_line: Raw line containing an ``unzip`` command.

    Returns:
        The detected ``.zip`` source token, or ``None`` if not found.

    """
    for token in raw_line.split():
        if token.startswith("-"):
            continue
        if token.lower() == "unzip":
            continue
        if token.lower().endswith(".zip"):
            return token.strip("\"'")
    return None


def _is_tar_extract_flag(token: str) -> bool:
    """
    Return ``True`` when *token* is a tar flag that requests extraction.

    Handles long-form (``--extract``), short-form (``-xzf``), and flag-word
    (``xzf``) styles.

    Args:
        token: Lower-cased command token to inspect.

    Returns:
        ``True`` if the token indicates extraction, ``False`` otherwise.

    """
    if token.startswith("--"):
        return "extract" in token
    if token.startswith("-"):
        return "x" in token[1:]
    return token.isalpha() and "x" in token


def _extract_tar_source(raw_line: str) -> str | None:
    """
    Extract archive source path from a tar extraction command line.

    Uses token parsing rather than a complex regular expression to ensure
    matching remains linear on adversarial input.

    Args:
        raw_line: Raw line containing a ``tar`` command.

    Returns:
        Archive path token when this looks like an extraction command,
        otherwise ``None``.

    """
    tokens = raw_line.split()
    if not tokens:
        return None

    saw_tar = False
    has_extract_flag = False

    for token in tokens:
        lowered = token.lower()

        if lowered == "tar":
            saw_tar = True
            continue
        if not saw_tar:
            continue

        if _is_tar_extract_flag(lowered):
            has_extract_flag = True
            continue

        candidate = token.strip("\"'").lower()
        if has_extract_flag and candidate.endswith(_TAR_ARCHIVE_SUFFIXES):
            return token.strip("\"'")

    return None


def _extract_sed_ops(content: str, result: dict[str, Any]) -> None:
    """
    Populate *result['sed_ops']* from *content*.

    Detects ``sed -i`` in-place file modification operations.

    Args:
        content: Raw Bash script text.
        result: Result dictionary to update in-place.

    """
    for match in _SED_INPLACE_PATTERN.finditer(content):
        result["sed_ops"].append(
            {
                "raw": match.group(0).strip(),
                "line": _line_number(content, match.start()),
                "confidence": 0.6,
                "ansible_module": "ansible.builtin.lineinfile",
            }
        )


def _extract_cron_jobs(content: str, result: dict[str, Any]) -> None:
    """
    Populate *result['cron_jobs']* from *content*.

    Detects ``crontab`` and cron.d write operations.

    Args:
        content: Raw Bash script text.
        result: Result dictionary to update in-place.

    """
    for pattern in _CRON_PATTERNS:
        for match in pattern.finditer(content):
            result["cron_jobs"].append(
                {
                    "raw": match.group(0).strip(),
                    "line": _line_number(content, match.start()),
                    "confidence": 0.7,
                }
            )


_FIREWALL_MODULE_MAP: dict[str, str] = {
    "ufw": "community.general.ufw",
    "firewalld": "ansible.posix.firewalld",
    "iptables": "ansible.builtin.iptables",
}


def _extract_firewall_rules(content: str, result: dict[str, Any]) -> None:
    """
    Populate *result['firewall_rules']* from *content*.

    Detects ufw, firewall-cmd, and iptables operations.

    Args:
        content: Raw Bash script text.
        result: Result dictionary to update in-place.

    """
    for tool, pattern in _FIREWALL_PATTERNS:
        for match in pattern.finditer(content):
            result["firewall_rules"].append(
                {
                    "tool": tool,
                    "raw": match.group(0).strip(),
                    "line": _line_number(content, match.start()),
                    "confidence": 0.85,
                    "ansible_module": _FIREWALL_MODULE_MAP[tool],
                }
            )


def _extract_hostname_ops(content: str, result: dict[str, Any]) -> None:
    """
    Populate *result['hostname_ops']* from *content*.

    Detects ``hostnamectl set-hostname`` and ``hostname`` commands.

    Args:
        content: Raw Bash script text.
        result: Result dictionary to update in-place.

    """
    for match in _HOSTNAME_PATTERN.finditer(content):
        hostname = match.group(1) or match.group(2)
        result["hostname_ops"].append(
            {
                "hostname": hostname,
                "raw": match.group(0).strip(),
                "line": _line_number(content, match.start()),
                "confidence": 0.95,
            }
        )


# Pattern used to check whether an env var value looks like a secret
_SECRET_VALUE_RE = re.compile(
    r"(?:password|passwd|pass|secret|token|key|credential)",
    re.IGNORECASE,
)


def _extract_env_vars(content: str, result: dict[str, Any]) -> None:
    """
    Populate *result['env_vars']* from *content*.

    Detects exported or globally-assigned shell variables.  Variables
    whose names contain lower-case letters are skipped as they are
    typically shell internals rather than configuration values.

    Args:
        content: Raw Bash script text.
        result: Result dictionary to update in-place.

    """
    line_start = 0
    for raw_line in content.splitlines():
        parsed = _parse_env_assignment_line(raw_line)
        if parsed is None:
            line_start += len(raw_line) + 1
            continue
        name, raw_value = parsed
        # Strip inline shell comment: whitespace + # + rest-of-line
        comment_pos = raw_value.find(" #")
        if comment_pos == -1:
            comment_pos = raw_value.find("\t#")
        value = (raw_value[:comment_pos] if comment_pos != -1 else raw_value).strip()
        is_sensitive = bool(_SECRET_VALUE_RE.search(name))
        result["env_vars"].append(
            {
                "name": name,
                "value": value,
                "raw": raw_line.strip(),
                "line": _line_number(content, line_start),
                "is_sensitive": is_sensitive,
            }
        )
        line_start += len(raw_line) + 1


def _parse_env_assignment_line(line: str) -> tuple[str, str] | None:
    """
    Parse a shell environment assignment line.

    Supports ``export VAR=value`` and ``VAR=value`` forms. Variable names
    that contain lower-case characters are ignored to match current parser
    behaviour for shell internals.

    Args:
        line: Raw script line.

    Returns:
        Tuple of ``(name, raw_value)`` when the line is a supported
        assignment, otherwise ``None``.

    """
    candidate = line.lstrip()
    if candidate.startswith("export"):
        remainder = candidate[len("export") :]
        if not remainder or remainder[0] not in {" ", "\t"}:
            return None
        candidate = remainder.lstrip(" \t")

    if "=" not in candidate:
        return None

    name, raw_value = candidate.split("=", 1)
    if not name:
        return None
    if not (name[0].isupper() or name[0] == "_"):
        return None
    if not all(ch.isupper() or ch.isdigit() or ch == "_" for ch in name):
        return None
    if any(ch.islower() for ch in name):
        return None

    return name, raw_value


def _extract_sensitive_data(content: str, result: dict[str, Any]) -> None:
    """
    Populate *result['sensitive_data']* from *content*.

    Detects hardcoded passwords, API keys, and private key material.
    The raw matched text is **not** stored; only the type and line
    number are recorded to avoid leaking secrets.

    Args:
        content: Raw Bash script text.
        result: Result dictionary to update in-place.

    """
    for secret_type, pattern in _SENSITIVE_PATTERNS:
        for match in pattern.finditer(content):
            result["sensitive_data"].append(
                {
                    "type": secret_type,
                    "raw": "<redacted>",
                    "line": _line_number(content, match.start()),
                    "suggestion": "Use ansible-vault to encrypt this value",
                }
            )


def _extract_cm_escapes(content: str, result: dict[str, Any]) -> None:
    """
    Populate *result['cm_escapes']* from *content*.

    Detects calls to Salt, Puppet, and Chef configuration-management
    tools within the script.

    Args:
        content: Raw Bash script text.
        result: Result dictionary to update in-place.

    """
    for tool, pattern in _CM_ESCAPE_PATTERNS:
        for match in pattern.finditer(content):
            result["cm_escapes"].append(
                {
                    "tool": tool,
                    "raw": match.group(0).strip(),
                    "line": _line_number(content, match.start()),
                    "suggestion": "Replace with native Ansible equivalent",
                }
            )


def _format_users_section(users: list[dict[str, Any]], lines: list[str]) -> None:
    """
    Append formatted user management entries to *lines*.

    Args:
        users: List of user IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not users:
        return
    lines.append("User Management:")
    for u in users:
        lines.append(
            f"  Line {u['line']}: [{u['action']}] {u['raw'][:60]} "
            f"(confidence: {u['confidence']:.0%})"
        )


def _format_groups_section(groups: list[dict[str, Any]], lines: list[str]) -> None:
    """
    Append formatted group management entries to *lines*.

    Args:
        groups: List of group IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not groups:
        return
    lines.append("Group Management:")
    for g in groups:
        lines.append(
            f"  Line {g['line']}: [{g['action']}] {g['raw'][:60]} "
            f"(confidence: {g['confidence']:.0%})"
        )


def _format_file_perms_section(
    file_perms: list[dict[str, Any]], lines: list[str]
) -> None:
    """
    Append formatted file permission entries to *lines*.

    Args:
        file_perms: List of file permission IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not file_perms:
        return
    lines.append("File Permissions:")
    for fp in file_perms:
        detail = fp["mode"] if fp["op"] == "chmod" else fp["owner"]
        recursive = " (recursive)" if fp["recursive"] else ""
        lines.append(
            f"  Line {fp['line']}: {fp['op']} {detail} {fp['path']}{recursive} "
            f"(confidence: {fp['confidence']:.0%})"
        )


def _format_git_ops_section(git_ops: list[dict[str, Any]], lines: list[str]) -> None:
    """
    Append formatted git operation entries to *lines*.

    Args:
        git_ops: List of git operation IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not git_ops:
        return
    lines.append("Git Operations:")
    for g in git_ops:
        detail = g.get("repo") or g.get("dest") or g["raw"][:40]
        lines.append(
            f"  Line {g['line']}: [{g['action']}] {detail} "
            f"(confidence: {g['confidence']:.0%})"
        )


def _format_archives_section(archives: list[dict[str, Any]], lines: list[str]) -> None:
    """
    Append formatted archive extraction entries to *lines*.

    Args:
        archives: List of archive IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not archives:
        return
    lines.append("Archive Extractions:")
    for a in archives:
        lines.append(
            f"  Line {a['line']}: [{a['tool']}] {a['source']} "
            f"(confidence: {a['confidence']:.0%})"
        )


def _format_sed_ops_section(sed_ops: list[dict[str, Any]], lines: list[str]) -> None:
    """
    Append formatted sed in-place operation entries to *lines*.

    Args:
        sed_ops: List of sed operation IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not sed_ops:
        return
    lines.append("sed In-place Operations:")
    for s in sed_ops:
        lines.append(
            f"  Line {s['line']}: {s['raw'][:60]} "
            f"→ {s['ansible_module']} (confidence: {s['confidence']:.0%})"
        )


def _format_cron_jobs_section(
    cron_jobs: list[dict[str, Any]], lines: list[str]
) -> None:
    """
    Append formatted cron job entries to *lines*.

    Args:
        cron_jobs: List of cron job IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not cron_jobs:
        return
    lines.append("Cron Jobs:")
    for c in cron_jobs:
        lines.append(
            f"  Line {c['line']}: {c['raw'][:60]} (confidence: {c['confidence']:.0%})"
        )


def _format_firewall_rules_section(
    firewall_rules: list[dict[str, Any]], lines: list[str]
) -> None:
    """
    Append formatted firewall rule entries to *lines*.

    Args:
        firewall_rules: List of firewall rule IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not firewall_rules:
        return
    lines.append("Firewall Rules:")
    for fw in firewall_rules:
        lines.append(
            f"  Line {fw['line']}: [{fw['tool']}] {fw['raw'][:60]} "
            f"→ {fw['ansible_module']} (confidence: {fw['confidence']:.0%})"
        )


def _format_hostname_ops_section(
    hostname_ops: list[dict[str, Any]], lines: list[str]
) -> None:
    """
    Append formatted hostname operation entries to *lines*.

    Args:
        hostname_ops: List of hostname operation IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not hostname_ops:
        return
    lines.append("Hostname Operations:")
    for h in hostname_ops:
        lines.append(
            f"  Line {h['line']}: set hostname → {h['hostname']} "
            f"(confidence: {h['confidence']:.0%})"
        )


def _format_env_vars_section(env_vars: list[dict[str, Any]], lines: list[str]) -> None:
    """
    Append formatted environment variable entries to *lines*.

    Args:
        env_vars: List of environment variable IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not env_vars:
        return
    lines.append("Environment Variables:")
    for v in env_vars:
        sensitive_tag = " [SENSITIVE]" if v["is_sensitive"] else ""
        lines.append(f"  Line {v['line']}: {v['name']}={v['value']}{sensitive_tag}")


def _format_sensitive_data_section(
    sensitive_data: list[dict[str, Any]], lines: list[str]
) -> None:
    """
    Append formatted sensitive data warning entries to *lines*.

    Only the type and line number are shown; the matched value is never
    included to avoid leaking secrets.

    Args:
        sensitive_data: List of sensitive data IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not sensitive_data:
        return
    lines.append("Sensitive Data Warnings:")
    for s in sensitive_data:
        lines.append(f"  Line {s['line']}: [{s['type']}] detected — {s['suggestion']}")


def _format_cm_escapes_section(
    cm_escapes: list[dict[str, Any]], lines: list[str]
) -> None:
    """
    Append formatted CM escape call entries to *lines*.

    Args:
        cm_escapes: List of CM escape IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not cm_escapes:
        return
    lines.append("Configuration Management Escape Calls:")
    for c in cm_escapes:
        lines.append(
            f"  Line {c['line']}: [{c['tool']}] {c['raw'][:60]} — {c['suggestion']}"
        )


def _format_packages_section(packages: list[dict[str, Any]], lines: list[str]) -> None:
    """
    Append formatted package entries to *lines*.

    Args:
        packages: List of package IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not packages:
        return
    lines.append("Package Installs:")
    for p in packages:
        pkg_list = ", ".join(p["packages"]) if p["packages"] else "(unknown)"
        lines.append(
            f"  Line {p['line']}: [{p['manager']}] {pkg_list} "
            f"→ {p['ansible_module']} (confidence: {p['confidence']:.0%})"
        )


def _format_services_section(services: list[dict[str, Any]], lines: list[str]) -> None:
    """
    Append formatted service entries to *lines*.

    Args:
        services: List of service IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not services:
        return
    lines.append("Service Control:")
    for s in services:
        lines.append(
            f"  Line {s['line']}: {s['manager']} {s['action']} {s['name']} "
            f"(confidence: {s['confidence']:.0%})"
        )


def _format_file_writes_section(
    file_writes: list[dict[str, Any]], lines: list[str]
) -> None:
    """
    Append formatted file-write entries to *lines*.

    Args:
        file_writes: List of file-write IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not file_writes:
        return
    lines.append("File Writes:")
    for f in file_writes:
        lines.append(
            f"  Line {f['line']}: → {f['destination']} "
            f"(confidence: {f['confidence']:.0%})"
        )


def _format_downloads_section(
    downloads: list[dict[str, Any]], lines: list[str]
) -> None:
    """
    Append formatted download entries to *lines*.

    Args:
        downloads: List of download IR entries.
        lines: Lines list to append to (mutated in-place).

    """
    if not downloads:
        return
    lines.append("Downloads:")
    for d in downloads:
        url_display = d["url"] if d["url"] else "(url not parsed)"
        lines.append(
            f"  Line {d['line']}: {d['tool']} {url_display} "
            f"(confidence: {d['confidence']:.0%})"
        )


def _format_risks_and_fallbacks_section(ir: dict[str, Any], lines: list[str]) -> None:
    """
    Append idempotency risks and shell fallbacks to *lines*.

    Args:
        ir: Intermediate representation dictionary.
        lines: Lines list to append to (mutated in-place).

    """
    if ir["idempotency_risks"]:
        lines.append("Idempotency Risks:")
        for r in ir["idempotency_risks"]:
            lines.append(f"  Line {r['line']}: [{r['type']}] {r['suggestion']}")

    if ir["shell_fallbacks"]:
        lines.append("Shell Fallbacks (no direct module mapping):")
        for fb in ir["shell_fallbacks"]:
            lines.append(f"  Line {fb['line']}: {fb['raw']}")
            lines.append(f"    Warning: {fb['warning']}")


def _format_parse_result(ir: dict[str, Any]) -> str:
    """
    Format a parsed IR dictionary as a human-readable string.

    Args:
        ir: Dictionary returned by :func:`_parse_bash_content`.

    Returns:
        Formatted multi-line string.

    """
    lines: list[str] = []

    _format_cm_escapes_section(ir.get("cm_escapes", []), lines)
    _format_sensitive_data_section(ir.get("sensitive_data", []), lines)
    _format_packages_section(ir["packages"], lines)
    _format_services_section(ir["services"], lines)
    _format_file_writes_section(ir["file_writes"], lines)
    _format_downloads_section(ir["downloads"], lines)
    _format_users_section(ir.get("users", []), lines)
    _format_groups_section(ir.get("groups", []), lines)
    _format_file_perms_section(ir.get("file_perms", []), lines)
    _format_git_ops_section(ir.get("git_ops", []), lines)
    _format_archives_section(ir.get("archives", []), lines)
    _format_sed_ops_section(ir.get("sed_ops", []), lines)
    _format_cron_jobs_section(ir.get("cron_jobs", []), lines)
    _format_firewall_rules_section(ir.get("firewall_rules", []), lines)
    _format_hostname_ops_section(ir.get("hostname_ops", []), lines)
    _format_env_vars_section(ir.get("env_vars", []), lines)
    _format_risks_and_fallbacks_section(ir, lines)

    if not lines:
        lines.append("No provisioning patterns detected in script.")

    return "\n".join(lines)
