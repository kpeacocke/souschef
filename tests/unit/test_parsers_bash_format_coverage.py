"""
Coverage tests for souschef.parsers.bash format section functions.

These functions follow the pattern: return early if no items, else append
formatted items to lines list.  Coverage gaps are in:
1. The early-return when items list is empty
2. The formatting loop with non-empty items lists

Testing strategy: call each function with empty and non-empty lists,
verify the lines list is correctly mutated.
"""

from __future__ import annotations


def test_format_users_section_empty() -> None:
    """_format_users_section returns early when users list is empty (line 1198)."""
    from souschef.parsers.bash import _format_users_section

    lines: list[str] = []
    _format_users_section([], lines)
    assert lines == []  # No lines added


def test_format_users_section_with_users() -> None:
    """_format_users_section appends header and users when list is non-empty."""
    from souschef.parsers.bash import _format_users_section

    lines: list[str] = []
    users = [
        {
            "action": "useradd",
            "raw": "useradd alice",
            "line": 5,
            "confidence": 0.9,
        }
    ]
    _format_users_section(users, lines)
    assert len(lines) == 2  # Header + 1 user
    assert "User Management:" in lines[0]


def test_format_groups_section_empty() -> None:
    """_format_groups_section returns early when groups is empty (line 1217)."""
    from souschef.parsers.bash import _format_groups_section

    lines: list[str] = []
    _format_groups_section([], lines)
    assert lines == []


def test_format_groups_section_with_groups() -> None:
    """_format_groups_section appends header and groups when non-empty."""
    from souschef.parsers.bash import _format_groups_section

    lines: list[str] = []
    groups = [
        {
            "action": "groupadd",
            "raw": "groupadd admin",
            "line": 10,
            "confidence": 0.85,
        }
    ]
    _format_groups_section(groups, lines)
    assert len(lines) == 2  # Header + 1 group
    assert "Group Management:" in lines[0]


def test_format_file_perms_section_empty() -> None:
    """_format_file_perms_section returns early for empty list (line 1238)."""
    from souschef.parsers.bash import _format_file_perms_section

    lines: list[str] = []
    _format_file_perms_section([], lines)
    assert lines == []


def test_format_file_perms_section_with_perms() -> None:
    """_format_file_perms_section appends perms when non-empty."""
    from souschef.parsers.bash import _format_file_perms_section

    lines: list[str] = []
    perms = [
        {
            "line": 15,
            "op": "chmod",
            "mode": "755",
            "path": "/usr/local/bin/script.sh",
            "recursive": False,
            "confidence": 0.9,
        }
    ]
    _format_file_perms_section(perms, lines)
    assert len(lines) == 2  # Header + 1 perm
    assert "File Permissions:" in lines[0]


def test_format_git_ops_section_empty() -> None:
    """_format_git_ops_section returns early for empty list (line 1259)."""
    from souschef.parsers.bash import _format_git_ops_section

    lines: list[str] = []
    _format_git_ops_section([], lines)
    assert lines == []


def test_format_git_ops_section_with_ops() -> None:
    """_format_git_ops_section appends git ops when non-empty."""
    from souschef.parsers.bash import _format_git_ops_section

    lines: list[str] = []
    git_ops = [
        {
            "action": "clone",
            "repo": "https://github.com/user/repo.git",
            "line": 20,
            "confidence": 0.88,
        }
    ]
    _format_git_ops_section(git_ops, lines)
    assert len(lines) == 2  # Header + 1 git op
    assert "Git Operations:" in lines[0]


def test_format_archives_section_empty() -> None:
    """_format_archives_section returns early for empty list (line 1279)."""
    from souschef.parsers.bash import _format_archives_section

    lines: list[str] = []
    _format_archives_section([], lines)
    assert lines == []


def test_format_archives_section_with_archives() -> None:
    """_format_archives_section appends archives when non-empty."""
    from souschef.parsers.bash import _format_archives_section

    lines: list[str] = []
    archives = [
        {
            "tool": "tar",
            "source": "archive.tar.gz",
            "line": 25,
            "confidence": 0.92,
        }
    ]
    _format_archives_section(archives, lines)
    assert len(lines) == 2  # Header + 1 archive
    assert "Archive Extractions:" in lines[0]


def test_format_sed_ops_section_empty() -> None:
    """_format_sed_ops_section returns early for empty list (line 1298)."""
    from souschef.parsers.bash import _format_sed_ops_section

    lines: list[str] = []
    _format_sed_ops_section([], lines)
    assert lines == []


def test_format_sed_ops_section_with_ops() -> None:
    """_format_sed_ops_section appends sed ops when non-empty."""
    from souschef.parsers.bash import _format_sed_ops_section

    lines: list[str] = []
    sed_ops = [
        {
            "raw": "sed -i 's/old/new/g' file.txt",
            "line": 30,
            "ansible_module": "ansible.builtin.replace",
            "confidence": 0.95,
        }
    ]
    _format_sed_ops_section(sed_ops, lines)
    assert len(lines) == 2  # Header + 1 sed op
    assert "sed In-place Operations:" in lines[0]


def test_format_cron_jobs_section_empty() -> None:
    """_format_cron_jobs_section returns early for empty list (line 1319)."""
    from souschef.parsers.bash import _format_cron_jobs_section

    lines: list[str] = []
    _format_cron_jobs_section([], lines)
    assert lines == []


def test_format_cron_jobs_section_with_crons() -> None:
    """_format_cron_jobs_section appends cron jobs when non-empty."""
    from souschef.parsers.bash import _format_cron_jobs_section

    lines: list[str] = []
    cron_jobs = [
        {
            "raw": "0 2 * * * /usr/local/bin/backup.sh",
            "line": 35,
            "confidence": 0.87,
        }
    ]
    _format_cron_jobs_section(cron_jobs, lines)
    assert len(lines) == 2  # Header + 1 cron
    assert "Cron Jobs:" in lines[0]


def test_format_firewall_rules_section_empty() -> None:
    """_format_firewall_rules_section returns early for empty list (line 1339)."""
    from souschef.parsers.bash import _format_firewall_rules_section

    lines: list[str] = []
    _format_firewall_rules_section([], lines)
    assert lines == []


def test_format_firewall_rules_section_with_rules() -> None:
    """_format_firewall_rules_section appends rules when non-empty."""
    from souschef.parsers.bash import _format_firewall_rules_section

    lines: list[str] = []
    firewall_rules = [
        {
            "tool": "ufw",
            "raw": "ufw allow 22/tcp",
            "line": 40,
            "ansible_module": "community.general.ufw",
            "confidence": 0.91,
        }
    ]
    _format_firewall_rules_section(firewall_rules, lines)
    assert len(lines) == 2  # Header + 1 rule
    assert "Firewall Rules:" in lines[0]


def test_format_hostname_ops_section_empty() -> None:
    """_format_hostname_ops_section returns early for empty list (line 1360)."""
    from souschef.parsers.bash import _format_hostname_ops_section

    lines: list[str] = []
    _format_hostname_ops_section([], lines)
    assert lines == []


def test_format_hostname_ops_section_with_ops() -> None:
    """_format_hostname_ops_section appends hostname ops when non-empty."""
    from souschef.parsers.bash import _format_hostname_ops_section

    lines: list[str] = []
    hostname_ops = [
        {
            "line": 45,
            "hostname": "web-server.example.com",
            "confidence": 0.98,
        }
    ]
    _format_hostname_ops_section(hostname_ops, lines)
    assert len(lines) == 2  # Header + 1 hostname op
    assert "Hostname Operations:" in lines[0]


def test_format_env_vars_section_empty() -> None:
    """_format_env_vars_section returns early for empty list (line 1379)."""
    from souschef.parsers.bash import _format_env_vars_section

    lines: list[str] = []
    _format_env_vars_section([], lines)
    assert lines == []


def test_format_env_vars_section_with_vars() -> None:
    """_format_env_vars_section appends env vars when non-empty."""
    from souschef.parsers.bash import _format_env_vars_section

    lines: list[str] = []
    env_vars = [
        {
            "line": 50,
            "name": "DATABASE_URL",
            "value": "postgres://db.example.com",
            "is_sensitive": True,
        }
    ]
    _format_env_vars_section(env_vars, lines)
    assert len(lines) == 2  # Header + 1 var
    assert "Environment Variables:" in lines[0]
    assert "[SENSITIVE]" in lines[1]


def test_format_sensitive_data_section_empty() -> None:
    """_format_sensitive_data_section returns early for empty list (line 1401)."""
    from souschef.parsers.bash import _format_sensitive_data_section

    lines: list[str] = []
    _format_sensitive_data_section([], lines)
    assert lines == []


def test_format_sensitive_data_section_with_data() -> None:
    """_format_sensitive_data_section appends sensitive data when non-empty."""
    from souschef.parsers.bash import _format_sensitive_data_section

    lines: list[str] = []
    sensitive_data = [
        {
            "type": "password",
            "line": 55,
            "suggestion": "Move to vault or secrets manager",
        }
    ]
    _format_sensitive_data_section(sensitive_data, lines)
    assert len(lines) == 2  # Header + 1 sensitive item
    assert "Sensitive Data Warnings:" in lines[0]
    assert "password" in lines[1]


def test_format_cm_escapes_section_empty() -> None:
    """_format_cm_escapes_section returns early for empty list (line 1419)."""
    from souschef.parsers.bash import _format_cm_escapes_section

    lines: list[str] = []
    _format_cm_escapes_section([], lines)
    assert lines == []


def test_format_cm_escapes_section_with_escapes() -> None:
    """_format_cm_escapes_section appends CM escapes when non-empty."""
    from souschef.parsers.bash import _format_cm_escapes_section

    lines: list[str] = []
    cm_escapes = [
        {
            "tool": "chef-client",
            "raw": "chef-client -r some_role",
            "line": 60,
            "suggestion": "Migrate to native Ansible roles",
        }
    ]
    _format_cm_escapes_section(cm_escapes, lines)
    assert len(lines) == 2  # Header + 1 escape
    assert "Configuration Management Escape Calls:" in lines[0]
