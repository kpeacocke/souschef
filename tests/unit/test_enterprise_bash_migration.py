"""
Enterprise Bash migration tests.

Tests for new extractor functions, task builders, quality scoring, AAP
hints, and role generation added in the enterprise enhancement.
"""

from __future__ import annotations

import json

import pytest

from souschef.converters.bash_to_ansible import (
    _archive_tasks,
    _build_aap_hints,
    _build_quality_score,
    _cron_tasks,
    _file_perm_tasks,
    _firewall_tasks,
    _git_tasks,
    _group_tasks,
    _hostname_tasks,
    _sed_tasks,
    _user_tasks,
    generate_ansible_role_from_bash,
)
from souschef.parsers.bash import (
    _extract_archives,
    _extract_cm_escapes,
    _extract_cron_jobs,
    _extract_env_vars,
    _extract_file_perms,
    _extract_firewall_rules,
    _extract_git_ops,
    _extract_groups,
    _extract_hostname_ops,
    _extract_sed_ops,
    _extract_sensitive_data,
    _extract_users,
    _parse_bash_content,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result() -> dict:
    """Return a blank IR result dict matching _parse_bash_content output."""
    return {
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


# ---------------------------------------------------------------------------
# _extract_users
# ---------------------------------------------------------------------------


def test_extract_users_useradd() -> None:
    """Detects useradd as a create action."""
    result = _make_result()
    _extract_users("useradd -m deploy", result)
    assert len(result["users"]) == 1
    assert result["users"][0]["action"] == "create"
    assert result["users"][0]["confidence"] == 0.9


def test_extract_users_adduser() -> None:
    """Detects adduser as a create action."""
    result = _make_result()
    _extract_users("adduser --system www-data", result)
    assert any(u["action"] == "create" for u in result["users"])


def test_extract_users_usermod() -> None:
    """Detects usermod as a modify action."""
    result = _make_result()
    _extract_users("usermod -aG sudo deploy", result)
    assert result["users"][0]["action"] == "modify"


def test_extract_users_userdel() -> None:
    """Detects userdel as a remove action."""
    result = _make_result()
    _extract_users("userdel olduser", result)
    assert result["users"][0]["action"] == "remove"


def test_extract_users_line_number() -> None:
    """Records the correct line number for user operations."""
    result = _make_result()
    _extract_users("echo hello\nuseradd -m deploy", result)
    assert result["users"][0]["line"] == 2


# ---------------------------------------------------------------------------
# _extract_groups
# ---------------------------------------------------------------------------


def test_extract_groups_groupadd() -> None:
    """Detects groupadd as a create action."""
    result = _make_result()
    _extract_groups("groupadd mygroup", result)
    assert result["groups"][0]["action"] == "create"
    assert result["groups"][0]["confidence"] == 0.9


def test_extract_groups_groupmod() -> None:
    """Detects groupmod as a modify action."""
    result = _make_result()
    _extract_groups("groupmod -n newname oldname", result)
    assert result["groups"][0]["action"] == "modify"


def test_extract_groups_groupdel() -> None:
    """Detects groupdel as a remove action."""
    result = _make_result()
    _extract_groups("groupdel oldgroup", result)
    assert result["groups"][0]["action"] == "remove"


# ---------------------------------------------------------------------------
# _extract_file_perms
# ---------------------------------------------------------------------------


def test_extract_file_perms_chmod() -> None:
    """Detects chmod operations."""
    result = _make_result()
    _extract_file_perms("chmod 755 /usr/local/bin/app", result)
    assert len(result["file_perms"]) == 1
    fp = result["file_perms"][0]
    assert fp["op"] == "chmod"
    assert fp["mode"] == "755"
    assert fp["path"] == "/usr/local/bin/app"
    assert fp["recursive"] is False
    assert fp["confidence"] == 0.85


def test_extract_file_perms_chmod_recursive() -> None:
    """Detects recursive chmod."""
    result = _make_result()
    _extract_file_perms("chmod -R 644 /var/www/html", result)
    assert result["file_perms"][0]["recursive"] is True


def test_extract_file_perms_chown() -> None:
    """Detects chown operations."""
    result = _make_result()
    _extract_file_perms("chown www-data:www-data /var/www", result)
    assert len(result["file_perms"]) == 1
    fp = result["file_perms"][0]
    assert fp["op"] == "chown"
    assert fp["owner"] == "www-data:www-data"
    assert fp["path"] == "/var/www"


def test_extract_file_perms_chown_recursive() -> None:
    """Detects recursive chown."""
    result = _make_result()
    _extract_file_perms("chown -R deploy:deploy /opt/app", result)
    assert result["file_perms"][0]["recursive"] is True


def test_extract_file_perms_empty() -> None:
    """No file_perms for script without chmod/chown."""
    result = _make_result()
    _extract_file_perms("echo hello", result)
    assert result["file_perms"] == []


# ---------------------------------------------------------------------------
# _extract_git_ops
# ---------------------------------------------------------------------------


def test_extract_git_ops_clone() -> None:
    """Detects git clone."""
    result = _make_result()
    _extract_git_ops("git clone https://github.com/org/repo.git /opt/repo", result)
    assert result["git_ops"][0]["action"] == "clone"
    assert result["git_ops"][0]["repo"] == "https://github.com/org/repo.git"
    assert result["git_ops"][0]["dest"] == "/opt/repo"
    assert result["git_ops"][0]["confidence"] == 0.9


def test_extract_git_ops_pull() -> None:
    """Detects git pull."""
    result = _make_result()
    _extract_git_ops("git pull origin main", result)
    assert result["git_ops"][0]["action"] == "pull"


def test_extract_git_ops_checkout() -> None:
    """Detects git checkout."""
    result = _make_result()
    _extract_git_ops("git checkout main", result)
    assert result["git_ops"][0]["action"] == "checkout"
    assert result["git_ops"][0]["dest"] == "main"


def test_extract_git_ops_empty() -> None:
    """No git_ops for script without git commands."""
    result = _make_result()
    _extract_git_ops("echo hello", result)
    assert result["git_ops"] == []


# ---------------------------------------------------------------------------
# _extract_archives
# ---------------------------------------------------------------------------


def test_extract_archives_tar() -> None:
    """Detects tar extraction."""
    result = _make_result()
    _extract_archives("tar -xzf /tmp/app.tar.gz", result)
    assert result["archives"][0]["tool"] == "tar"
    assert result["archives"][0]["source"] == "/tmp/app.tar.gz"
    assert result["archives"][0]["confidence"] == 0.85


def test_extract_archives_unzip() -> None:
    """Detects unzip."""
    result = _make_result()
    _extract_archives("unzip /tmp/package.zip", result)
    assert result["archives"][0]["tool"] == "unzip"
    assert result["archives"][0]["source"] == "/tmp/package.zip"


def test_extract_archives_empty() -> None:
    """No archives for script without extract commands."""
    result = _make_result()
    _extract_archives("echo hello", result)
    assert result["archives"] == []


# ---------------------------------------------------------------------------
# _extract_sed_ops
# ---------------------------------------------------------------------------


def test_extract_sed_ops_inplace() -> None:
    """Detects sed -i operations."""
    result = _make_result()
    _extract_sed_ops("sed -i 's/foo/bar/g' /etc/app.conf", result)
    assert len(result["sed_ops"]) == 1
    assert result["sed_ops"][0]["confidence"] == 0.6
    assert result["sed_ops"][0]["ansible_module"] == "ansible.builtin.lineinfile"


def test_extract_sed_ops_empty() -> None:
    """No sed_ops for script without sed commands."""
    result = _make_result()
    _extract_sed_ops("echo hello", result)
    assert result["sed_ops"] == []


# ---------------------------------------------------------------------------
# _extract_cron_jobs
# ---------------------------------------------------------------------------


def test_extract_cron_jobs_crontab() -> None:
    """Detects crontab operations."""
    result = _make_result()
    _extract_cron_jobs("crontab -l", result)
    assert len(result["cron_jobs"]) == 1
    assert result["cron_jobs"][0]["confidence"] == 0.7


def test_extract_cron_jobs_empty() -> None:
    """No cron_jobs for script without cron commands."""
    result = _make_result()
    _extract_cron_jobs("echo hello", result)
    assert result["cron_jobs"] == []


# ---------------------------------------------------------------------------
# _extract_firewall_rules
# ---------------------------------------------------------------------------


def test_extract_firewall_rules_ufw() -> None:
    """Detects ufw rules."""
    result = _make_result()
    _extract_firewall_rules("ufw allow 80/tcp", result)
    assert result["firewall_rules"][0]["tool"] == "ufw"
    assert result["firewall_rules"][0]["ansible_module"] == "community.general.ufw"
    assert result["firewall_rules"][0]["confidence"] == 0.85


def test_extract_firewall_rules_firewalld() -> None:
    """Detects firewall-cmd rules."""
    result = _make_result()
    _extract_firewall_rules("firewall-cmd --permanent --add-port=80/tcp", result)
    assert result["firewall_rules"][0]["tool"] == "firewalld"
    assert result["firewall_rules"][0]["ansible_module"] == "ansible.posix.firewalld"


def test_extract_firewall_rules_iptables() -> None:
    """Detects iptables rules."""
    result = _make_result()
    _extract_firewall_rules("iptables -A INPUT -p tcp --dport 80 -j ACCEPT", result)
    assert result["firewall_rules"][0]["tool"] == "iptables"
    assert result["firewall_rules"][0]["ansible_module"] == "ansible.builtin.iptables"


def test_extract_firewall_rules_empty() -> None:
    """No firewall_rules for script without firewall commands."""
    result = _make_result()
    _extract_firewall_rules("echo hello", result)
    assert result["firewall_rules"] == []


# ---------------------------------------------------------------------------
# _extract_hostname_ops
# ---------------------------------------------------------------------------


def test_extract_hostname_ops_hostnamectl() -> None:
    """Detects hostnamectl set-hostname."""
    result = _make_result()
    _extract_hostname_ops("hostnamectl set-hostname myserver", result)
    assert result["hostname_ops"][0]["hostname"] == "myserver"
    assert result["hostname_ops"][0]["confidence"] == 0.95


def test_extract_hostname_ops_hostname() -> None:
    """Detects hostname command."""
    result = _make_result()
    _extract_hostname_ops("hostname webserver01", result)
    assert result["hostname_ops"][0]["hostname"] == "webserver01"


def test_extract_hostname_ops_empty() -> None:
    """No hostname_ops for script without hostname commands."""
    result = _make_result()
    _extract_hostname_ops("echo hello", result)
    assert result["hostname_ops"] == []


# ---------------------------------------------------------------------------
# _extract_env_vars
# ---------------------------------------------------------------------------


def test_extract_env_vars_export() -> None:
    """Detects exported environment variables."""
    result = _make_result()
    _extract_env_vars("export MY_VAR=hello\n", result)
    assert len(result["env_vars"]) == 1
    assert result["env_vars"][0]["name"] == "MY_VAR"
    assert result["env_vars"][0]["value"] == "hello"
    assert result["env_vars"][0]["is_sensitive"] is False


def test_extract_env_vars_sensitive() -> None:
    """Marks variables with secret-like names as sensitive."""
    result = _make_result()
    _extract_env_vars("DB_PASSWORD=secret123\n", result)
    assert result["env_vars"][0]["is_sensitive"] is True


def test_extract_env_vars_skips_lowercase() -> None:
    """Skips variables with lower-case names (shell internals)."""
    result = _make_result()
    _extract_env_vars("myvar=hello\n", result)
    assert result["env_vars"] == []


def test_extract_env_vars_empty() -> None:
    """No env_vars for script without variable assignments."""
    result = _make_result()
    _extract_env_vars("echo hello\n", result)
    assert result["env_vars"] == []


# ---------------------------------------------------------------------------
# _extract_sensitive_data
# ---------------------------------------------------------------------------


def test_extract_sensitive_data_password() -> None:
    """Detects hardcoded passwords."""
    result = _make_result()
    _extract_sensitive_data("password=mysecret123", result)
    assert len(result["sensitive_data"]) >= 1
    types = [s["type"] for s in result["sensitive_data"]]
    assert "password" in types


def test_extract_sensitive_data_api_key() -> None:
    """Detects hardcoded API keys."""
    result = _make_result()
    _extract_sensitive_data("API_KEY=abcdefghijklmnopqrstuvwxyz1234", result)
    assert len(result["sensitive_data"]) >= 1
    types = [s["type"] for s in result["sensitive_data"]]
    assert "api_key" in types


def test_extract_sensitive_data_redacted() -> None:
    """Sensitive data raw field is redacted."""
    result = _make_result()
    _extract_sensitive_data("password=verysecretvalue", result)
    for s in result["sensitive_data"]:
        assert s["raw"] == "<redacted>"


def test_extract_sensitive_data_suggestion() -> None:
    """Sensitive data includes vault suggestion."""
    result = _make_result()
    _extract_sensitive_data("passwd=topsecret", result)
    assert any("ansible-vault" in s["suggestion"] for s in result["sensitive_data"])


def test_extract_sensitive_data_empty() -> None:
    """No sensitive_data for clean script."""
    result = _make_result()
    _extract_sensitive_data("echo hello\napt-get install nginx", result)
    assert result["sensitive_data"] == []


# ---------------------------------------------------------------------------
# _extract_cm_escapes
# ---------------------------------------------------------------------------


def test_extract_cm_escapes_salt() -> None:
    """Detects salt-call."""
    result = _make_result()
    _extract_cm_escapes("salt-call state.apply", result)
    assert result["cm_escapes"][0]["tool"] == "salt"
    assert "Replace" in result["cm_escapes"][0]["suggestion"]


def test_extract_cm_escapes_puppet() -> None:
    """Detects puppet apply."""
    result = _make_result()
    _extract_cm_escapes("puppet apply /etc/puppet/manifests/site.pp", result)
    assert result["cm_escapes"][0]["tool"] == "puppet"


def test_extract_cm_escapes_chef() -> None:
    """Detects chef-client."""
    result = _make_result()
    _extract_cm_escapes("chef-client --runlist 'recipe[base]'", result)
    assert result["cm_escapes"][0]["tool"] == "chef"


def test_extract_cm_escapes_empty() -> None:
    """No cm_escapes for clean script."""
    result = _make_result()
    _extract_cm_escapes("echo hello\napt-get install nginx", result)
    assert result["cm_escapes"] == []


# ---------------------------------------------------------------------------
# New task builders
# ---------------------------------------------------------------------------


def test_user_tasks_create() -> None:
    """Creates ansible.builtin.user tasks."""
    entry = {
        "action": "create",
        "raw": "useradd -m deploy",
        "line": 1,
        "confidence": 0.9,
    }
    tasks = _user_tasks([entry])
    assert len(tasks) == 1
    assert "ansible.builtin.user" in tasks[0]
    assert tasks[0]["ansible.builtin.user"]["state"] == "present"
    assert tasks[0]["_metadata"]["idempotent"] is True


def test_user_tasks_remove() -> None:
    """Creates absent state for remove action."""
    entry = {
        "action": "remove",
        "raw": "userdel olduser",
        "line": 1,
        "confidence": 0.9,
    }
    tasks = _user_tasks([entry])
    assert tasks[0]["ansible.builtin.user"]["state"] == "absent"


def test_group_tasks_create() -> None:
    """Creates ansible.builtin.group tasks."""
    entry = {
        "action": "create",
        "raw": "groupadd mygroup",
        "line": 1,
        "confidence": 0.9,
    }
    tasks = _group_tasks([entry])
    assert "ansible.builtin.group" in tasks[0]
    assert tasks[0]["ansible.builtin.group"]["state"] == "present"


def test_file_perm_tasks_chmod() -> None:
    """Creates ansible.builtin.file tasks for chmod."""
    entry = {
        "op": "chmod",
        "mode": "755",
        "owner": None,
        "path": "/usr/local/bin/app",
        "recursive": False,
        "raw": "chmod 755 /usr/local/bin/app",
        "line": 1,
        "confidence": 0.85,
    }
    tasks = _file_perm_tasks([entry])
    assert "ansible.builtin.file" in tasks[0]
    assert tasks[0]["ansible.builtin.file"]["mode"] == "755"
    assert tasks[0]["ansible.builtin.file"]["path"] == "/usr/local/bin/app"


def test_file_perm_tasks_chown_with_group() -> None:
    """Splits owner:group correctly for chown."""
    entry = {
        "op": "chown",
        "mode": None,
        "owner": "www-data:www-data",
        "path": "/var/www",
        "recursive": False,
        "raw": "chown www-data:www-data /var/www",
        "line": 1,
        "confidence": 0.85,
    }
    tasks = _file_perm_tasks([entry])
    fargs = tasks[0]["ansible.builtin.file"]
    assert fargs["owner"] == "www-data"
    assert fargs["group"] == "www-data"


def test_file_perm_tasks_recursive() -> None:
    """Sets recurse=True for recursive chmod."""
    entry = {
        "op": "chmod",
        "mode": "644",
        "owner": None,
        "path": "/var/www/html",
        "recursive": True,
        "raw": "chmod -R 644 /var/www/html",
        "line": 1,
        "confidence": 0.85,
    }
    tasks = _file_perm_tasks([entry])
    assert tasks[0]["ansible.builtin.file"]["recurse"] is True


def test_git_tasks_clone() -> None:
    """Creates ansible.builtin.git tasks for clone."""
    entry = {
        "action": "clone",
        "repo": "https://github.com/org/repo.git",
        "dest": "/opt/repo",
        "raw": "git clone https://github.com/org/repo.git /opt/repo",
        "line": 1,
        "confidence": 0.9,
    }
    tasks = _git_tasks([entry])
    assert "ansible.builtin.git" in tasks[0]
    assert tasks[0]["ansible.builtin.git"]["repo"] == "https://github.com/org/repo.git"
    assert tasks[0]["ansible.builtin.git"]["dest"] == "/opt/repo"


def test_git_tasks_pull_fallback() -> None:
    """Git pull falls back to shell task."""
    entry = {
        "action": "pull",
        "repo": None,
        "dest": None,
        "raw": "git pull origin main",
        "line": 1,
        "confidence": 0.9,
    }
    tasks = _git_tasks([entry])
    assert "ansible.builtin.shell" in tasks[0]


def test_archive_tasks() -> None:
    """Creates ansible.builtin.unarchive tasks."""
    entry = {
        "tool": "tar",
        "source": "/tmp/app.tar.gz",
        "raw": "tar -xzf /tmp/app.tar.gz",
        "line": 1,
        "confidence": 0.85,
    }
    tasks = _archive_tasks([entry])
    assert "ansible.builtin.unarchive" in tasks[0]
    assert tasks[0]["ansible.builtin.unarchive"]["src"] == "/tmp/app.tar.gz"
    assert tasks[0]["ansible.builtin.unarchive"]["remote_src"] is True


def test_sed_tasks_shell_fallback() -> None:
    """Sed tasks always fall back to shell with a hint."""
    entry = {
        "raw": "sed -i 's/foo/bar/g' /etc/app.conf",
        "line": 1,
        "confidence": 0.6,
        "ansible_module": "ansible.builtin.lineinfile",
    }
    tasks = _sed_tasks([entry])
    assert "ansible.builtin.shell" in tasks[0]
    assert "lineinfile" in tasks[0]["_metadata"]["idempotency_hint"]


def test_cron_tasks_shell_fallback() -> None:
    """Cron tasks always fall back to shell with a hint."""
    entry = {"raw": "crontab -l", "line": 1, "confidence": 0.7}
    tasks = _cron_tasks([entry])
    assert "ansible.builtin.shell" in tasks[0]
    assert "cron" in tasks[0]["_metadata"]["idempotency_hint"]


def test_firewall_tasks_ufw() -> None:
    """Creates structured task for ufw rules."""
    entry = {
        "tool": "ufw",
        "raw": "ufw allow 80/tcp",
        "line": 1,
        "confidence": 0.85,
        "ansible_module": "community.general.ufw",
    }
    tasks = _firewall_tasks([entry])
    assert "community.general.ufw" in tasks[0]


def test_hostname_tasks() -> None:
    """Creates ansible.builtin.hostname tasks."""
    entry = {
        "hostname": "myserver",
        "raw": "hostnamectl set-hostname myserver",
        "line": 1,
        "confidence": 0.95,
    }
    tasks = _hostname_tasks([entry])
    assert "ansible.builtin.hostname" in tasks[0]
    assert tasks[0]["ansible.builtin.hostname"]["name"] == "myserver"
    assert tasks[0]["_metadata"]["idempotent"] is True


# ---------------------------------------------------------------------------
# _build_aap_hints
# ---------------------------------------------------------------------------


def test_build_aap_hints_clean_script() -> None:
    """AAP hints for clean script has no notes."""
    ir = _parse_bash_content("apt-get install -y nginx")
    hints = _build_aap_hints(ir, "script.sh")
    assert hints["become_enabled"] is True
    assert hints["timeout"] == 3600
    assert "suggested_ee" in hints
    assert "Machine" in hints["suggested_credentials"]


def test_build_aap_hints_with_sensitive_data() -> None:
    """AAP hints note presence of sensitive data."""
    ir = _parse_bash_content("password=mysecretvalue\napt-get install nginx")
    hints = _build_aap_hints(ir, "script.sh")
    assert any("ansible-vault" in n for n in hints["notes"])


def test_build_aap_hints_with_cm_escapes() -> None:
    """AAP hints note CM tool calls."""
    ir = _parse_bash_content("salt-call state.apply")
    hints = _build_aap_hints(ir, "script.sh")
    assert any("salt" in n.lower() for n in hints["notes"])


def test_build_aap_hints_survey_vars() -> None:
    """Survey variables are generated from non-sensitive env vars."""
    ir = _parse_bash_content("export APP_PORT=8080\nexport APP_HOST=localhost")
    hints = _build_aap_hints(ir, "script.sh")
    names = [v["name"] for v in hints["survey_variables"]]
    assert "APP_PORT" in names or "APP_HOST" in names


def test_build_aap_hints_survey_vars_limit() -> None:
    """Survey variables are capped at 10."""
    script = "\n".join(f"export VAR_{i}=val{i}" for i in range(20))
    ir = _parse_bash_content(script)
    hints = _build_aap_hints(ir, "script.sh")
    assert len(hints["survey_variables"]) <= 10


# ---------------------------------------------------------------------------
# _build_quality_score
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "structured,total,penalty,expected_grade",
    [
        (10, 10, 0, "A"),  # 100% coverage, grade A
        (8, 10, 0, "B"),  # 80% coverage, grade B
        (7, 10, 0, "C"),  # 70% coverage, grade C
        (5, 10, 0, "D"),  # 50% coverage, grade D
        (3, 10, 0, "F"),  # 30% coverage, grade F
        (10, 10, 4, "B"),  # 100% but 4 secrets → -20 penalty → 80 → grade B
    ],
)
def test_build_quality_score_grades(
    structured: int, total: int, penalty: int, expected_grade: str
) -> None:
    """Quality score grades match expected thresholds."""
    tasks = [
        {
            "name": f"task{i}",
            "_metadata": {"idempotent": i < structured},
        }
        for i in range(total)
    ]
    sensitive = [
        {"type": "password", "raw": "<redacted>", "line": 1, "suggestion": ""}
    ] * penalty
    ir: dict = {"sensitive_data": sensitive}
    qs = _build_quality_score(ir, tasks)
    assert qs["grade"] == expected_grade


def test_build_quality_score_empty_tasks() -> None:
    """Empty task list returns N/A grade."""
    qs = _build_quality_score({}, [])
    assert qs["grade"] == "N/A"
    assert qs["total_operations"] == 0


def test_build_quality_score_improvements() -> None:
    """Improvement suggestions are populated for issues."""
    ir = {
        "sensitive_data": [{"type": "password"}],
        "sed_ops": [{"raw": "sed -i", "line": 1}],
        "cron_jobs": [{"raw": "crontab", "line": 1}],
        "cm_escapes": [{"tool": "puppet"}],
    }
    tasks = [{"_metadata": {"idempotent": False}}]
    qs = _build_quality_score(ir, tasks)
    assert len(qs["improvements"]) >= 4


# ---------------------------------------------------------------------------
# generate_ansible_role_from_bash
# ---------------------------------------------------------------------------

_SAMPLE_SCRIPT = """\
#!/bin/bash
apt-get install -y nginx python3
systemctl enable nginx
systemctl start nginx
useradd -m deploy
groupadd webteam
chmod 755 /var/www/html
git clone https://github.com/org/app.git /opt/app
tar -xzf /tmp/app.tar.gz
sed -i 's/foo/bar/' /etc/app.conf
crontab -l
ufw allow 80/tcp
hostnamectl set-hostname webserver01
export APP_PORT=8080
"""


def test_generate_role_returns_success() -> None:
    """generate_ansible_role_from_bash returns success status."""
    raw = generate_ansible_role_from_bash(_SAMPLE_SCRIPT, role_name="test_role")
    data = json.loads(raw)
    assert data["status"] == "success"


def test_generate_role_name() -> None:
    """Role name is reflected in the output."""
    raw = generate_ansible_role_from_bash(_SAMPLE_SCRIPT, role_name="my_role")
    data = json.loads(raw)
    assert data["role_name"] == "my_role"


def test_generate_role_files_present() -> None:
    """All expected role files are generated."""
    raw = generate_ansible_role_from_bash(_SAMPLE_SCRIPT)
    data = json.loads(raw)
    files = data["files"]
    expected = {
        "tasks/main.yml",
        "tasks/packages.yml",
        "tasks/services.yml",
        "tasks/users.yml",
        "tasks/files.yml",
        "tasks/misc.yml",
        "handlers/main.yml",
        "defaults/main.yml",
        "vars/main.yml",
        "meta/main.yml",
        "README.md",
    }
    assert expected == set(files.keys())


def test_generate_role_tasks_main_includes() -> None:
    """tasks/main.yml includes all sub-task files."""
    raw = generate_ansible_role_from_bash(_SAMPLE_SCRIPT)
    data = json.loads(raw)
    main = data["files"]["tasks/main.yml"]
    assert "packages.yml" in main
    assert "services.yml" in main
    assert "users.yml" in main
    assert "files.yml" in main
    assert "misc.yml" in main


def test_generate_role_defaults_env_vars() -> None:
    """defaults/main.yml contains detected env vars."""
    raw = generate_ansible_role_from_bash(_SAMPLE_SCRIPT)
    data = json.loads(raw)
    defaults = data["files"]["defaults/main.yml"]
    assert "app_port" in defaults.lower() or "APP_PORT" in defaults


def test_generate_role_has_quality_score() -> None:
    """Response includes a quality_score key."""
    raw = generate_ansible_role_from_bash(_SAMPLE_SCRIPT)
    data = json.loads(raw)
    assert "quality_score" in data
    assert "grade" in data["quality_score"]


def test_generate_role_has_aap_hints() -> None:
    """Response includes aap_hints key."""
    raw = generate_ansible_role_from_bash(_SAMPLE_SCRIPT)
    data = json.loads(raw)
    assert "aap_hints" in data
    assert "suggested_ee" in data["aap_hints"]


def test_generate_role_meta_content() -> None:
    """meta/main.yml contains role_name."""
    raw = generate_ansible_role_from_bash(_SAMPLE_SCRIPT, role_name="myrole")
    data = json.loads(raw)
    meta = data["files"]["meta/main.yml"]
    assert "myrole" in meta


def test_generate_role_readme_content() -> None:
    """README.md contains quality score section."""
    raw = generate_ansible_role_from_bash(_SAMPLE_SCRIPT, role_name="myrole")
    data = json.loads(raw)
    readme = data["files"]["README.md"]
    assert "Quality Score" in readme
    assert "myrole" in readme


def test_generate_role_empty_script() -> None:
    """Empty script still generates all role files."""
    raw = generate_ansible_role_from_bash("")
    data = json.loads(raw)
    assert data["status"] == "success"
    assert len(data["files"]) == 11


def test_generate_role_parse_bash_content_integration() -> None:
    """Full IR is reflected in the role."""
    script = "useradd -m deploy\nufw allow 443/tcp\nhostnamectl set-hostname prod01\n"
    raw = generate_ansible_role_from_bash(script)
    data = json.loads(raw)
    users_yml = data["files"]["tasks/users.yml"]
    assert "deploy" in users_yml
