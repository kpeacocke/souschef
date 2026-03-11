"""
Bash script parser for SousChef.

Parses Bash provisioning scripts and extracts structured patterns
including package installs, file writes, service control, and downloads.
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
        re.compile(
            r"\bcurl\s+(?:[^\n]*\s+)?-[oO]\s*(\S+)[^\n]*|(curl\b[^\n]*)",
            re.IGNORECASE,
        ),
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
    }

    _extract_packages(content, result)
    _extract_services(content, result)
    _extract_file_writes(content, result)
    _extract_downloads(content, result)
    _extract_idempotency_risks(content, result)
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


def _format_risks_and_fallbacks_section(
    ir: dict[str, Any], lines: list[str]
) -> None:
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

    _format_packages_section(ir["packages"], lines)
    _format_services_section(ir["services"], lines)
    _format_file_writes_section(ir["file_writes"], lines)
    _format_downloads_section(ir["downloads"], lines)
    _format_risks_and_fallbacks_section(ir, lines)

    if not lines:
        lines.append("No provisioning patterns detected in script.")

    return "\n".join(lines)
