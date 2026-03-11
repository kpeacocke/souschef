"""Tests for souschef/converters/salt.py."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from souschef.converters.salt import (
    _build_cmd_task,
    _build_file_task,
    _build_generic_task,
    _build_git_task,
    _build_group_task,
    _build_pip_task,
    _build_pkg_task,
    _build_service_task,
    _build_user_task,
    _convert_state_to_task,
    _pillar_to_ansible_vars,
    _render_playbook_yaml,
    convert_salt_sls_to_ansible,
)


# ---------------------------------------------------------------------------
# _build_pkg_task
# ---------------------------------------------------------------------------


def test_build_pkg_task_installed() -> None:
    """pkg.installed maps to package state=present."""
    state = {"id": "nginx", "module": "pkg", "function": "installed", "args": {"name": "nginx"}}
    task = _build_pkg_task(state)
    assert task["ansible.builtin.package"]["state"] == "present"
    assert task["ansible.builtin.package"]["name"] == "nginx"


def test_build_pkg_task_removed() -> None:
    """pkg.removed maps to package state=absent."""
    state = {"id": "vim", "module": "pkg", "function": "removed", "args": {}}
    task = _build_pkg_task(state)
    assert task["ansible.builtin.package"]["state"] == "absent"


def test_build_pkg_task_latest() -> None:
    """pkg.latest maps to package state=latest."""
    state = {"id": "curl", "module": "pkg", "function": "latest", "args": {}}
    task = _build_pkg_task(state)
    assert task["ansible.builtin.package"]["state"] == "latest"


def test_build_pkg_task_pkgs_list() -> None:
    """pkg.installed with pkgs list uses list as name."""
    state = {
        "id": "web_packages",
        "module": "pkg",
        "function": "installed",
        "args": {"pkgs": ["nginx", "curl", "git"]},
    }
    task = _build_pkg_task(state)
    assert task["ansible.builtin.package"]["name"] == ["nginx", "curl", "git"]


def test_build_pkg_task_name_as_list() -> None:
    """pkg.installed with name as list uses list."""
    state = {
        "id": "pkgs",
        "module": "pkg",
        "function": "installed",
        "args": {"name": ["vim", "nano"]},
    }
    task = _build_pkg_task(state)
    assert task["ansible.builtin.package"]["name"] == ["vim", "nano"]


def test_build_pkg_task_unknown_function() -> None:
    """Unknown pkg function defaults to present."""
    state = {"id": "pkg", "module": "pkg", "function": "unknown_func", "args": {}}
    task = _build_pkg_task(state)
    assert task["ansible.builtin.package"]["state"] == "present"


# ---------------------------------------------------------------------------
# _build_file_task
# ---------------------------------------------------------------------------


def test_build_file_task_managed() -> None:
    """file.managed creates template task."""
    state = {
        "id": "nginx_config",
        "module": "file",
        "function": "managed",
        "args": {
            "name": "/etc/nginx/nginx.conf",
            "source": "salt://nginx/nginx.conf",
            "user": "root",
            "group": "root",
            "mode": "0644",
        },
    }
    task = _build_file_task(state)
    assert "ansible.builtin.template" in task
    params = task["ansible.builtin.template"]
    assert params["dest"] == "/etc/nginx/nginx.conf"
    assert params["src"] == "nginx/nginx.conf"
    assert params["owner"] == "root"
    assert params["mode"] == "0644"


def test_build_file_task_directory() -> None:
    """file.directory creates file module with state=directory."""
    state = {
        "id": "log_dir",
        "module": "file",
        "function": "directory",
        "args": {"name": "/var/log/myapp", "user": "myapp"},
    }
    task = _build_file_task(state)
    assert "ansible.builtin.file" in task
    params = task["ansible.builtin.file"]
    assert params["state"] == "directory"
    assert params["path"] == "/var/log/myapp"
    assert params["owner"] == "myapp"


def test_build_file_task_absent() -> None:
    """file.absent creates file module with state=absent."""
    state = {
        "id": "old_file",
        "module": "file",
        "function": "absent",
        "args": {"name": "/tmp/old"},
    }
    task = _build_file_task(state)
    assert "ansible.builtin.file" in task
    assert task["ansible.builtin.file"]["state"] == "absent"


def test_build_file_task_symlink() -> None:
    """file.symlink creates file module with state=link."""
    state = {
        "id": "link_config",
        "module": "file",
        "function": "symlink",
        "args": {"name": "/etc/config", "target": "/opt/config"},
    }
    task = _build_file_task(state)
    assert "ansible.builtin.file" in task
    params = task["ansible.builtin.file"]
    assert params["state"] == "link"
    assert params["src"] == "/opt/config"


def test_build_file_task_replace() -> None:
    """file.replace creates lineinfile task."""
    state = {
        "id": "config_replace",
        "module": "file",
        "function": "replace",
        "args": {"name": "/etc/hosts", "pattern": "old", "repl": "new"},
    }
    task = _build_file_task(state)
    assert "ansible.builtin.lineinfile" in task
    params = task["ansible.builtin.lineinfile"]
    assert params["path"] == "/etc/hosts"
    assert params["regexp"] == "old"
    assert params["line"] == "new"


def test_build_file_task_line() -> None:
    """file.line creates lineinfile task."""
    state = {
        "id": "line_edit",
        "module": "file",
        "function": "line",
        "args": {"name": "/etc/hosts", "pattern": "^127", "repl": "127.0.0.1"},
    }
    task = _build_file_task(state)
    assert "ansible.builtin.lineinfile" in task


def test_build_file_task_append() -> None:
    """file.append creates blockinfile task."""
    state = {
        "id": "append_config",
        "module": "file",
        "function": "append",
        "args": {"name": "/etc/config", "text": "new_line"},
    }
    task = _build_file_task(state)
    assert "ansible.builtin.blockinfile" in task
    assert task["ansible.builtin.blockinfile"]["block"] == "new_line"


def test_build_file_task_prepend() -> None:
    """file.prepend creates blockinfile task with content from 'content' key."""
    state = {
        "id": "prepend_config",
        "module": "file",
        "function": "prepend",
        "args": {"name": "/etc/config", "content": "header"},
    }
    task = _build_file_task(state)
    assert "ansible.builtin.blockinfile" in task
    assert task["ansible.builtin.blockinfile"]["block"] == "header"


def test_build_file_task_copy() -> None:
    """file.copy creates copy task."""
    state = {
        "id": "copy_file",
        "module": "file",
        "function": "copy",
        "args": {"name": "/dest/path"},
    }
    task = _build_file_task(state)
    assert "ansible.builtin.copy" in task


def test_build_file_task_unknown_function() -> None:
    """Unknown file function uses default 'ansible.builtin.file' module."""
    state = {
        "id": "unknown_file",
        "module": "file",
        "function": "unknown",
        "args": {"name": "/tmp/x"},
    }
    task = _build_file_task(state)
    # Should still produce a task with some module
    assert any(k != "name" for k in task)


# ---------------------------------------------------------------------------
# _build_service_task
# ---------------------------------------------------------------------------


def test_build_service_task_running() -> None:
    """service.running creates started+enabled service task."""
    state = {
        "id": "nginx",
        "module": "service",
        "function": "running",
        "args": {"name": "nginx"},
    }
    task = _build_service_task(state)
    assert "ansible.builtin.service" in task
    params = task["ansible.builtin.service"]
    assert params["state"] == "started"
    assert params["enabled"] is True


def test_build_service_task_dead() -> None:
    """service.dead creates stopped service task."""
    state = {
        "id": "apache2",
        "module": "service",
        "function": "dead",
        "args": {"name": "apache2"},
    }
    task = _build_service_task(state)
    params = task["ansible.builtin.service"]
    assert params["state"] == "stopped"


def test_build_service_task_enabled() -> None:
    """service.enabled sets enabled=True without state."""
    state = {
        "id": "nginx",
        "module": "service",
        "function": "enabled",
        "args": {"name": "nginx"},
    }
    task = _build_service_task(state)
    params = task["ansible.builtin.service"]
    assert params["enabled"] is True
    assert "state" not in params


def test_build_service_task_disabled() -> None:
    """service.disabled sets enabled=False."""
    state = {
        "id": "nginx",
        "module": "service",
        "function": "disabled",
        "args": {"name": "nginx"},
    }
    task = _build_service_task(state)
    params = task["ansible.builtin.service"]
    assert params["enabled"] is False


def test_build_service_task_reload() -> None:
    """service.reload creates reloaded service task."""
    state = {
        "id": "nginx",
        "module": "service",
        "function": "reload",
        "args": {"name": "nginx"},
    }
    task = _build_service_task(state)
    assert task["ansible.builtin.service"]["state"] == "reloaded"


def test_build_service_task_restart() -> None:
    """service.restart creates restarted service task."""
    state = {
        "id": "nginx",
        "module": "service",
        "function": "restart",
        "args": {"name": "nginx"},
    }
    task = _build_service_task(state)
    assert task["ansible.builtin.service"]["state"] == "restarted"


def test_build_service_task_unknown_function() -> None:
    """Unknown service function defaults to started/enabled."""
    state = {
        "id": "nginx",
        "module": "service",
        "function": "unknown",
        "args": {},
    }
    task = _build_service_task(state)
    params = task["ansible.builtin.service"]
    assert params["state"] == "started"


# ---------------------------------------------------------------------------
# _build_cmd_task
# ---------------------------------------------------------------------------


def test_build_cmd_task_run() -> None:
    """cmd.run creates command task."""
    state = {
        "id": "run_test",
        "module": "cmd",
        "function": "run",
        "args": {"name": "echo hello"},
    }
    task = _build_cmd_task(state)
    assert "ansible.builtin.command" in task
    assert task["ansible.builtin.command"]["cmd"] == "echo hello"


def test_build_cmd_task_with_cwd() -> None:
    """cmd.run with cwd sets chdir."""
    state = {
        "id": "build",
        "module": "cmd",
        "function": "run",
        "args": {"name": "make build", "cwd": "/opt/app"},
    }
    task = _build_cmd_task(state)
    assert task["ansible.builtin.command"]["chdir"] == "/opt/app"


def test_build_cmd_task_with_creates() -> None:
    """cmd.run with creates sets creates parameter."""
    state = {
        "id": "init",
        "module": "cmd",
        "function": "run",
        "args": {"name": "init-db", "creates": "/var/lib/db/initialized"},
    }
    task = _build_cmd_task(state)
    assert task["ansible.builtin.command"]["creates"] == "/var/lib/db/initialized"


def test_build_cmd_task_with_unless() -> None:
    """cmd.run with unless creates when condition."""
    state = {
        "id": "setup",
        "module": "cmd",
        "function": "run",
        "args": {"name": "setup.sh", "unless": "test -f /etc/setup.done"},
    }
    task = _build_cmd_task(state)
    assert "when" in task
    assert "test -f /etc/setup.done" in task["when"]


def test_build_cmd_task_script() -> None:
    """cmd.script creates shell task."""
    state = {
        "id": "run_script",
        "module": "cmd",
        "function": "script",
        "args": {"name": "deploy.sh"},
    }
    task = _build_cmd_task(state)
    assert "ansible.builtin.shell" in task


# ---------------------------------------------------------------------------
# _build_user_task
# ---------------------------------------------------------------------------


def test_build_user_task_present() -> None:
    """user.present creates user task with state=present."""
    state = {
        "id": "deploy",
        "module": "user",
        "function": "present",
        "args": {"name": "deploy", "home": "/home/deploy", "shell": "/bin/bash"},
    }
    task = _build_user_task(state)
    assert "ansible.builtin.user" in task
    params = task["ansible.builtin.user"]
    assert params["state"] == "present"
    assert params["home"] == "/home/deploy"
    assert params["shell"] == "/bin/bash"


def test_build_user_task_absent() -> None:
    """user.absent creates user task with state=absent."""
    state = {
        "id": "old_user",
        "module": "user",
        "function": "absent",
        "args": {"name": "old_user"},
    }
    task = _build_user_task(state)
    assert task["ansible.builtin.user"]["state"] == "absent"


def test_build_user_task_with_optional_attrs() -> None:
    """user.present with uid/gid/groups includes these params."""
    state = {
        "id": "svc_user",
        "module": "user",
        "function": "present",
        "args": {
            "name": "svcuser",
            "uid": 1001,
            "gid": 1001,
            "groups": ["wheel", "docker"],
        },
    }
    task = _build_user_task(state)
    params = task["ansible.builtin.user"]
    assert params["uid"] == 1001
    assert params["groups"] == ["wheel", "docker"]


# ---------------------------------------------------------------------------
# _build_group_task
# ---------------------------------------------------------------------------


def test_build_group_task_present() -> None:
    """group.present creates group task with state=present."""
    state = {
        "id": "webmasters",
        "module": "group",
        "function": "present",
        "args": {"name": "webmasters", "gid": 2000},
    }
    task = _build_group_task(state)
    assert "ansible.builtin.group" in task
    params = task["ansible.builtin.group"]
    assert params["state"] == "present"
    assert params["gid"] == 2000


def test_build_group_task_absent() -> None:
    """group.absent creates group task with state=absent."""
    state = {
        "id": "old_group",
        "module": "group",
        "function": "absent",
        "args": {},
    }
    task = _build_group_task(state)
    assert task["ansible.builtin.group"]["state"] == "absent"


# ---------------------------------------------------------------------------
# _build_git_task
# ---------------------------------------------------------------------------


def test_build_git_task_latest() -> None:
    """git.latest creates git task."""
    state = {
        "id": "myrepo",
        "module": "git",
        "function": "latest",
        "args": {
            "name": "https://github.com/org/repo.git",
            "target": "/opt/repo",
            "rev": "main",
        },
    }
    task = _build_git_task(state)
    assert "ansible.builtin.git" in task
    params = task["ansible.builtin.git"]
    assert params["repo"] == "https://github.com/org/repo.git"
    assert params["dest"] == "/opt/repo"
    assert params["version"] == "main"


def test_build_git_task_defaults() -> None:
    """git.latest with minimal args uses defaults."""
    state = {
        "id": "repo",
        "module": "git",
        "function": "latest",
        "args": {},
    }
    task = _build_git_task(state)
    assert "ansible.builtin.git" in task
    assert task["ansible.builtin.git"]["version"] == "HEAD"


# ---------------------------------------------------------------------------
# _build_pip_task
# ---------------------------------------------------------------------------


def test_build_pip_task_installed() -> None:
    """pip.installed creates pip task with state=present."""
    state = {
        "id": "flask",
        "module": "pip",
        "function": "installed",
        "args": {"name": "flask"},
    }
    task = _build_pip_task(state)
    assert "ansible.builtin.pip" in task
    assert task["ansible.builtin.pip"]["state"] == "present"
    assert task["ansible.builtin.pip"]["name"] == "flask"


def test_build_pip_task_with_virtualenv() -> None:
    """pip.installed with bin_env sets virtualenv."""
    state = {
        "id": "requests",
        "module": "pip",
        "function": "installed",
        "args": {"name": "requests", "bin_env": "/opt/venv"},
    }
    task = _build_pip_task(state)
    assert task["ansible.builtin.pip"]["virtualenv"] == "/opt/venv"


def test_build_pip_task_removed() -> None:
    """pip.removed creates pip task with state=absent."""
    state = {
        "id": "old_pkg",
        "module": "pip",
        "function": "removed",
        "args": {"name": "old_pkg"},
    }
    task = _build_pip_task(state)
    assert task["ansible.builtin.pip"]["state"] == "absent"


# ---------------------------------------------------------------------------
# _build_generic_task
# ---------------------------------------------------------------------------


def test_build_generic_task_unknown_module() -> None:
    """Unknown module generates debug task with unconverted tag."""
    state = {
        "id": "custom_state",
        "module": "custom",
        "function": "apply",
        "args": {},
    }
    task = _build_generic_task(state)
    assert "ansible.builtin.debug" in task
    assert "salt_unconverted" in task.get("tags", [])


# ---------------------------------------------------------------------------
# _convert_state_to_task (dispatch)
# ---------------------------------------------------------------------------


def test_convert_state_to_task_dispatches_pkg() -> None:
    """Dispatches pkg module to _build_pkg_task."""
    state = {"id": "vim", "module": "pkg", "function": "installed", "args": {}}
    task = _convert_state_to_task(state)
    assert "ansible.builtin.package" in task


def test_convert_state_to_task_dispatches_service() -> None:
    """Dispatches service module to _build_service_task."""
    state = {"id": "nginx", "module": "service", "function": "running", "args": {}}
    task = _convert_state_to_task(state)
    assert "ansible.builtin.service" in task


def test_convert_state_to_task_dispatches_file() -> None:
    """Dispatches file module to _build_file_task."""
    state = {"id": "conf", "module": "file", "function": "managed", "args": {}}
    task = _convert_state_to_task(state)
    assert any(k.startswith("ansible.builtin") for k in task)


def test_convert_state_to_task_unknown_module() -> None:
    """Unknown module dispatches to _build_generic_task."""
    state = {"id": "x", "module": "unknown_module", "function": "do", "args": {}}
    task = _convert_state_to_task(state)
    assert "ansible.builtin.debug" in task


# ---------------------------------------------------------------------------
# _pillar_to_ansible_vars
# ---------------------------------------------------------------------------


def test_pillar_to_ansible_vars_basic() -> None:
    """Basic pillar keys are converted to Ansible var names."""
    pillars = {
        "db_host": {"source": "pillar", "access": "direct", "default": None},
        "db.port": {"source": "pillar", "access": "get", "default": "5432"},
    }
    result = _pillar_to_ansible_vars(pillars)
    assert "db_host" in result
    assert "db_port" in result
    assert result["db_port"] == "5432"


def test_pillar_to_ansible_vars_none_default_becomes_placeholder() -> None:
    """Pillar key with no default becomes a Jinja2 placeholder."""
    pillars = {
        "mykey": {"source": "pillar", "access": "direct", "default": None},
    }
    result = _pillar_to_ansible_vars(pillars)
    assert "{{ mykey }}" in result["mykey"]


def test_pillar_to_ansible_vars_empty() -> None:
    """Empty pillar dict returns empty vars dict."""
    assert _pillar_to_ansible_vars({}) == {}


def test_pillar_to_ansible_vars_special_chars_in_key() -> None:
    """Special characters in pillar keys are normalised to underscores."""
    pillars = {
        "my-key:sub": {"source": "pillar", "access": "direct", "default": "val"},
    }
    result = _pillar_to_ansible_vars(pillars)
    assert "my_key_sub" in result


# ---------------------------------------------------------------------------
# _render_playbook_yaml
# ---------------------------------------------------------------------------


def test_render_playbook_yaml_basic() -> None:
    """Basic playbook YAML rendering works."""
    tasks = [
        {
            "name": "Install nginx",
            "ansible.builtin.package": {"name": "nginx", "state": "present"},
        }
    ]
    yaml_out = _render_playbook_yaml("test", tasks, {})
    assert "---" in yaml_out
    assert "Converted from Salt: test" in yaml_out
    assert "Install nginx" in yaml_out
    assert "ansible.builtin.package:" in yaml_out


def test_render_playbook_yaml_with_vars() -> None:
    """Playbook YAML includes vars section when provided."""
    vars_dict = {"db_host": "localhost", "db_port": "5432"}
    yaml_out = _render_playbook_yaml("test", [], vars_dict)
    assert "vars:" in yaml_out
    assert "db_host:" in yaml_out


def test_render_playbook_yaml_with_jinja2_var() -> None:
    """Jinja2 placeholder vars are rendered without quotes."""
    vars_dict = {"mykey": "{{ mykey }}"}
    yaml_out = _render_playbook_yaml("test", [], vars_dict)
    assert "mykey: {{ mykey }}" in yaml_out


def test_render_playbook_yaml_with_none_var() -> None:
    """None var value is rendered as null."""
    vars_dict = {"key": None}
    yaml_out = _render_playbook_yaml("test", [], vars_dict)
    assert "key: null" in yaml_out


def test_render_playbook_yaml_with_when() -> None:
    """Task with when condition is rendered correctly."""
    tasks = [
        {
            "name": "conditional cmd",
            "ansible.builtin.command": {"cmd": "do something"},
            "when": "ansible_os_family == 'Debian'",
        }
    ]
    yaml_out = _render_playbook_yaml("test", tasks, {})
    assert "when: ansible_os_family" in yaml_out


def test_render_playbook_yaml_with_tags() -> None:
    """Task with tags list is rendered correctly."""
    tasks = [
        {
            "name": "tagged task",
            "ansible.builtin.debug": {"msg": "hello"},
            "tags": ["salt_unconverted"],
        }
    ]
    yaml_out = _render_playbook_yaml("test", tasks, {})
    assert "tags:" in yaml_out
    assert "salt_unconverted" in yaml_out


def test_render_playbook_yaml_with_bool_param() -> None:
    """Boolean param values are rendered as lowercase true/false."""
    tasks = [
        {
            "name": "service task",
            "ansible.builtin.service": {"name": "nginx", "enabled": True},
        }
    ]
    yaml_out = _render_playbook_yaml("test", tasks, {})
    assert "enabled: true" in yaml_out


def test_render_playbook_yaml_with_list_param() -> None:
    """List param values are rendered as YAML list."""
    tasks = [
        {
            "name": "pkg task",
            "ansible.builtin.package": {"name": ["vim", "curl"], "state": "present"},
        }
    ]
    yaml_out = _render_playbook_yaml("test", tasks, {})
    assert "- vim" in yaml_out
    assert "- curl" in yaml_out


def test_render_playbook_yaml_with_none_param() -> None:
    """None param values are rendered as empty (null)."""
    tasks = [
        {
            "name": "task",
            "ansible.builtin.service": {"name": "svc", "state": None},
        }
    ]
    yaml_out = _render_playbook_yaml("test", tasks, {})
    assert "state:" in yaml_out


def test_render_playbook_yaml_empty_tasks() -> None:
    """Playbook with no tasks has no tasks section."""
    yaml_out = _render_playbook_yaml("test", [], {})
    assert "tasks:" not in yaml_out


# ---------------------------------------------------------------------------
# convert_salt_sls_to_ansible (integration)
# ---------------------------------------------------------------------------


def test_convert_salt_sls_to_ansible_valid(tmp_path: Path) -> None:
    """Valid SLS file is fully converted to Ansible playbook."""
    content = """
nginx:
  pkg.installed:
    - name: nginx
nginx_service:
  service.running:
    - name: nginx
    - enable: true
nginx_config:
  file.managed:
    - name: /etc/nginx/nginx.conf
    - source: salt://nginx/nginx.conf
run_check:
  cmd.run:
    - name: nginx -t
"""
    sls = tmp_path / "nginx.sls"
    sls.write_text(content, encoding="utf-8")

    with (
        patch("souschef.converters.salt._normalize_path", return_value=sls),
        patch("souschef.converters.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.converters.salt._ensure_within_base_path", return_value=sls),
        patch("souschef.converters.salt.safe_read_text", return_value=content),
    ):
        result_str = convert_salt_sls_to_ansible(str(sls))

    result = json.loads(result_str)
    assert result["tasks_converted"] >= 4
    assert result["tasks_unconverted"] == 0
    assert "---" in result["playbook"]
    assert "nginx" in result["playbook"]


def test_convert_salt_sls_to_ansible_file_not_found(tmp_path: Path) -> None:
    """Missing SLS returns JSON error."""
    missing = tmp_path / "missing.sls"

    with (
        patch("souschef.converters.salt._normalize_path", return_value=missing),
        patch("souschef.converters.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.converters.salt._ensure_within_base_path", return_value=missing),
    ):
        result_str = convert_salt_sls_to_ansible(str(missing))

    result = json.loads(result_str)
    assert "error" in result


def test_convert_salt_sls_to_ansible_directory(tmp_path: Path) -> None:
    """Directory path returns JSON error."""
    with (
        patch("souschef.converters.salt._normalize_path", return_value=tmp_path),
        patch("souschef.converters.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.converters.salt._ensure_within_base_path", return_value=tmp_path),
    ):
        result_str = convert_salt_sls_to_ansible(str(tmp_path))

    result = json.loads(result_str)
    assert "error" in result


def test_convert_salt_sls_to_ansible_permission_error(tmp_path: Path) -> None:
    """Permission error returns JSON error."""
    sls = tmp_path / "secret.sls"
    with (
        patch("souschef.converters.salt._normalize_path", return_value=sls),
        patch("souschef.converters.salt._get_workspace_root", return_value=tmp_path),
        patch(
            "souschef.converters.salt._ensure_within_base_path",
            side_effect=PermissionError("denied"),
        ),
    ):
        result_str = convert_salt_sls_to_ansible(str(sls))

    result = json.loads(result_str)
    assert "error" in result


def test_convert_salt_sls_to_ansible_value_error(tmp_path: Path) -> None:
    """ValueError returns JSON error."""
    with patch(
        "souschef.converters.salt._normalize_path",
        side_effect=ValueError("bad path"),
    ):
        result_str = convert_salt_sls_to_ansible("bad_path")

    result = json.loads(result_str)
    assert "error" in result


def test_convert_salt_sls_to_ansible_with_custom_name(tmp_path: Path) -> None:
    """Custom playbook name is included in the generated playbook."""
    content = "vim:\n  pkg.installed:\n    - name: vim\n"
    sls = tmp_path / "common.sls"
    sls.write_text(content, encoding="utf-8")

    with (
        patch("souschef.converters.salt._normalize_path", return_value=sls),
        patch("souschef.converters.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.converters.salt._ensure_within_base_path", return_value=sls),
        patch("souschef.converters.salt.safe_read_text", return_value=content),
    ):
        result_str = convert_salt_sls_to_ansible(str(sls), "my_custom_play")

    result = json.loads(result_str)
    assert "my_custom_play" in result["playbook"]


def test_convert_salt_sls_to_ansible_unconverted_generates_warnings(
    tmp_path: Path,
) -> None:
    """Unsupported state modules generate warnings."""
    content = "custom_state:\n  mycustom.apply:\n    - name: something\n"
    sls = tmp_path / "custom.sls"
    sls.write_text(content, encoding="utf-8")

    with (
        patch("souschef.converters.salt._normalize_path", return_value=sls),
        patch("souschef.converters.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.converters.salt._ensure_within_base_path", return_value=sls),
        patch("souschef.converters.salt.safe_read_text", return_value=content),
    ):
        result_str = convert_salt_sls_to_ansible(str(sls))

    result = json.loads(result_str)
    assert result["tasks_unconverted"] == 1
    assert len(result["warnings"]) == 1


def test_convert_salt_sls_to_ansible_with_pillars(tmp_path: Path) -> None:
    """Pillar references are converted to Ansible vars."""
    content = (
        "web:\n"
        "  pkg.installed:\n"
        "    - name: {{ pillar.get('web_package', 'nginx') }}\n"
    )
    sls = tmp_path / "web.sls"
    sls.write_text(content, encoding="utf-8")

    with (
        patch("souschef.converters.salt._normalize_path", return_value=sls),
        patch("souschef.converters.salt._get_workspace_root", return_value=tmp_path),
        patch("souschef.converters.salt._ensure_within_base_path", return_value=sls),
        patch("souschef.converters.salt.safe_read_text", return_value=content),
    ):
        result_str = convert_salt_sls_to_ansible(str(sls))

    result = json.loads(result_str)
    assert "web_package" in result["ansible_vars"]
    assert result["ansible_vars"]["web_package"] == "nginx"


def test_build_file_task_directory_with_group_and_mode() -> None:
    """file.directory with group and mode sets those params."""
    state = {
        "id": "app_dir",
        "module": "file",
        "function": "directory",
        "args": {"name": "/opt/app", "user": "app", "group": "app", "mode": "0755"},
    }
    task = _build_file_task(state)
    params = task["ansible.builtin.file"]
    assert params["group"] == "app"
    assert params["mode"] == "0755"


def test_render_playbook_yaml_with_int_param() -> None:
    """Integer param values are rendered correctly."""
    tasks = [
        {
            "name": "group task",
            "ansible.builtin.group": {"name": "mygroup", "gid": 2000},
        }
    ]
    yaml_out = _render_playbook_yaml("test", tasks, {})
    assert "gid: 2000" in yaml_out


def test_render_playbook_yaml_with_non_list_tags() -> None:
    """Single string tag (not a list) is rendered as inline list."""
    tasks = [
        {
            "name": "tagged task",
            "ansible.builtin.debug": {"msg": "test"},
            "tags": "my_tag",
        }
    ]
    yaml_out = _render_playbook_yaml("test", tasks, {})
    assert "tags: [my_tag]" in yaml_out


def test_render_playbook_yaml_task_with_non_dict_module() -> None:
    """Task with non-dict module value is rendered as inline value."""
    tasks = [
        {
            "name": "simple task",
            "ansible.builtin.command": "echo hello",
        }
    ]
    yaml_out = _render_playbook_yaml("test", tasks, {})
    assert "ansible.builtin.command: echo hello" in yaml_out


def test_render_playbook_yaml_var_non_string_value() -> None:
    """Non-string, non-None var values are rendered as-is."""
    vars_dict = {"port": 8080}
    yaml_out = _render_playbook_yaml("test", [], vars_dict)
    assert "port: 8080" in yaml_out
