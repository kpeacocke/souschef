"""Unit tests for the Bash → Ansible converter (souschef.converters.bash_to_ansible)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from souschef.converters.bash_to_ansible import (
    _build_idempotency_report,
    _build_tasks,
    _collect_warnings,
    _download_tasks,
    _file_write_tasks,
    _package_tasks,
    _render_playbook,
    _render_task,
    _service_tasks,
    _shell_fallback_tasks,
    _shell_task,
    _yaml_str,
    convert_bash_content_to_ansible,
    convert_bash_to_ansible,
)

# ---------------------------------------------------------------------------
# _yaml_str
# ---------------------------------------------------------------------------


def test_yaml_str_plain_value() -> None:
    """Plain strings are returned as-is."""
    assert _yaml_str("simple") == "simple"


def test_yaml_str_colon_wrapped() -> None:
    """Strings with colons are wrapped in double quotes."""
    result = _yaml_str("key: value")
    assert result.startswith('"')
    assert result.endswith('"')


def test_yaml_str_true_quoted() -> None:
    """Boolean-like strings are quoted."""
    result = _yaml_str("true")
    assert result.startswith('"')


def test_yaml_str_null_quoted() -> None:
    """Null-like strings are quoted."""
    result = _yaml_str("null")
    assert result.startswith('"')


def test_yaml_str_internal_double_quotes_escaped() -> None:
    """Internal double quotes are escaped."""
    result = _yaml_str('say "hello"')
    assert '\\"' in result


# ---------------------------------------------------------------------------
# _shell_task
# ---------------------------------------------------------------------------


def test_shell_task_basic() -> None:
    """Creates a shell task dict with expected keys."""
    task = _shell_task("ls -la", 5, 0.5)
    assert task["name"].startswith("Shell:")
    assert "ansible.builtin.shell" in task
    assert task["ansible.builtin.shell"]["cmd"] == "ls -la"
    assert "changed_when" in task
    assert "failed_when" not in task


def test_shell_task_with_creates() -> None:
    """Shell task with creates param includes it in module args."""
    task = _shell_task("ls /tmp/file", 1, 0.5, creates="/tmp/file")
    assert task["ansible.builtin.shell"]["creates"] == "/tmp/file"


def test_shell_task_truncates_long_name() -> None:
    """Shell task truncates long commands in name."""
    long_cmd = "x" * 100
    task = _shell_task(long_cmd, 1, 0.5)
    assert len(task["name"]) <= 70  # "Shell: " + 60 chars + "..."


def test_shell_task_with_warning() -> None:
    """Shell task embeds warning in metadata."""
    task = _shell_task("cmd", 1, 0.5, warning="some warning")
    assert task["_metadata"]["warning"] == "some warning"


def test_shell_task_with_idempotency_hint() -> None:
    """Shell task embeds idempotency hint in metadata."""
    task = _shell_task("cmd", 1, 0.5, idempotency_hint="use ansible.builtin.copy")
    assert "idempotency_hint" in task["_metadata"]


# ---------------------------------------------------------------------------
# _package_tasks
# ---------------------------------------------------------------------------


def test_package_tasks_high_confidence() -> None:
    """High-confidence packages get structured tasks."""
    packages = [
        {
            "manager": "apt",
            "ansible_module": "ansible.builtin.apt",
            "raw": "apt-get install nginx",
            "packages": ["nginx"],
            "confidence": 0.9,
            "line": 1,
        }
    ]
    tasks = _package_tasks(packages)
    assert len(tasks) == 1
    assert "ansible.builtin.apt" in tasks[0]
    assert tasks[0]["ansible.builtin.apt"]["state"] == "present"


def test_package_tasks_low_confidence_falls_back_to_shell() -> None:
    """Low-confidence packages fall back to shell task."""
    packages = [
        {
            "manager": "apt",
            "ansible_module": "ansible.builtin.apt",
            "raw": "apt-get install",
            "packages": [],
            "confidence": 0.5,
            "line": 1,
        }
    ]
    tasks = _package_tasks(packages)
    assert len(tasks) == 1
    assert "ansible.builtin.shell" in tasks[0]


def test_package_tasks_empty() -> None:
    """Empty package list returns empty task list."""
    assert _package_tasks([]) == []


# ---------------------------------------------------------------------------
# _service_tasks
# ---------------------------------------------------------------------------


def test_service_tasks_high_confidence_start() -> None:
    """High-confidence service start generates ansible.builtin.service task."""
    services = [
        {
            "manager": "systemctl",
            "name": "nginx",
            "action": "start",
            "raw": "systemctl start nginx",
            "confidence": 0.95,
            "line": 2,
        }
    ]
    tasks = _service_tasks(services)
    assert len(tasks) == 1
    assert "ansible.builtin.service" in tasks[0]
    assert tasks[0]["ansible.builtin.service"]["state"] == "started"


def test_service_tasks_enable_sets_enabled() -> None:
    """Systemctl enable sets enabled=true."""
    services = [
        {
            "manager": "systemctl",
            "name": "nginx",
            "action": "enable",
            "raw": "systemctl enable nginx",
            "confidence": 0.95,
            "line": 3,
        }
    ]
    tasks = _service_tasks(services)
    assert tasks[0]["ansible.builtin.service"]["enabled"] is True


def test_service_tasks_disable_sets_enabled_false() -> None:
    """Systemctl disable sets enabled=false."""
    services = [
        {
            "manager": "systemctl",
            "name": "nginx",
            "action": "disable",
            "raw": "systemctl disable nginx",
            "confidence": 0.95,
            "line": 4,
        }
    ]
    tasks = _service_tasks(services)
    assert tasks[0]["ansible.builtin.service"]["enabled"] is False


def test_service_tasks_low_confidence_falls_back() -> None:
    """Low-confidence service entries fall back to shell."""
    services = [
        {
            "manager": "service",
            "name": "httpd",
            "action": "start",
            "raw": "service httpd start",
            "confidence": 0.5,
            "line": 5,
        }
    ]
    tasks = _service_tasks(services)
    assert "ansible.builtin.shell" in tasks[0]


def test_service_tasks_empty() -> None:
    """Empty service list returns empty task list."""
    assert _service_tasks([]) == []


# ---------------------------------------------------------------------------
# _file_write_tasks
# ---------------------------------------------------------------------------


def test_file_write_tasks_high_confidence() -> None:
    """High-confidence file writes get ansible.builtin.copy tasks."""
    file_writes = [
        {
            "destination": "/etc/app.conf",
            "raw": "cat <<EOF > /etc/app.conf",
            "confidence": 0.9,
            "line": 6,
        }
    ]
    tasks = _file_write_tasks(file_writes)
    assert "ansible.builtin.copy" in tasks[0]
    assert tasks[0]["ansible.builtin.copy"]["dest"] == "/etc/app.conf"


def test_file_write_tasks_low_confidence_falls_back() -> None:
    """Low-confidence file writes fall back to shell task."""
    file_writes = [
        {
            "destination": "/etc/app.conf",
            "raw": "echo key > /etc/app.conf",
            "confidence": 0.5,
            "line": 7,
        }
    ]
    tasks = _file_write_tasks(file_writes)
    assert "ansible.builtin.shell" in tasks[0]


def test_file_write_tasks_empty() -> None:
    """Empty file_writes list returns empty task list."""
    assert _file_write_tasks([]) == []


# ---------------------------------------------------------------------------
# _download_tasks
# ---------------------------------------------------------------------------


def test_download_tasks_with_url() -> None:
    """Downloads with URL get ansible.builtin.get_url tasks."""
    downloads = [
        {
            "tool": "curl",
            "url": "https://example.com/app.tar.gz",
            "raw": "curl -o /tmp/app.tar.gz https://example.com/app.tar.gz",
            "confidence": 0.7,
            "line": 8,
        }
    ]
    tasks = _download_tasks(downloads)
    assert "ansible.builtin.get_url" in tasks[0]
    assert (
        tasks[0]["ansible.builtin.get_url"]["url"] == "https://example.com/app.tar.gz"
    )


def test_download_tasks_without_url_falls_back() -> None:
    """Downloads without URL fall back to shell task."""
    downloads = [
        {
            "tool": "curl",
            "url": "",
            "raw": "curl --some-flag value",
            "confidence": 0.7,
            "line": 9,
        }
    ]
    tasks = _download_tasks(downloads)
    assert "ansible.builtin.shell" in tasks[0]


def test_download_tasks_empty() -> None:
    """Empty downloads list returns empty task list."""
    assert _download_tasks([]) == []


# ---------------------------------------------------------------------------
# _shell_fallback_tasks
# ---------------------------------------------------------------------------


def test_shell_fallback_tasks() -> None:
    """Shell fallbacks produce shell tasks with metadata warnings."""
    fallbacks = [
        {
            "line": 10,
            "raw": "custom-tool --flag",
            "warning": "No structured Ansible module mapping found",
        }
    ]
    tasks = _shell_fallback_tasks(fallbacks)
    assert len(tasks) == 1
    assert "ansible.builtin.shell" in tasks[0]
    assert "warning" in tasks[0]["_metadata"]


def test_shell_fallback_tasks_empty() -> None:
    """Empty fallbacks list returns empty task list."""
    assert _shell_fallback_tasks([]) == []


# ---------------------------------------------------------------------------
# _build_tasks
# ---------------------------------------------------------------------------


def test_build_tasks_comprehensive_ir() -> None:
    """_build_tasks produces tasks for all IR categories."""
    ir = {
        "packages": [
            {
                "manager": "apt",
                "ansible_module": "ansible.builtin.apt",
                "raw": "apt-get install nginx",
                "packages": ["nginx"],
                "confidence": 0.9,
                "line": 1,
            }
        ],
        "services": [
            {
                "manager": "systemctl",
                "name": "nginx",
                "action": "start",
                "raw": "systemctl start nginx",
                "confidence": 0.95,
                "line": 2,
            }
        ],
        "file_writes": [],
        "downloads": [],
        "shell_fallbacks": [],
    }
    tasks = _build_tasks(ir)
    assert len(tasks) == 2


def test_build_tasks_empty_ir() -> None:
    """Empty IR produces empty task list."""
    ir: dict = {
        "packages": [],
        "services": [],
        "file_writes": [],
        "downloads": [],
        "shell_fallbacks": [],
    }
    assert _build_tasks(ir) == []


# ---------------------------------------------------------------------------
# _render_task
# ---------------------------------------------------------------------------


def test_render_task_basic() -> None:
    """Renders a basic task to YAML lines."""
    task = {
        "name": "Install nginx",
        "ansible.builtin.apt": {"name": ["nginx"], "state": "present"},
    }
    lines = _render_task(task)
    assert any("Install nginx" in line for line in lines)
    assert any("ansible.builtin.apt" in line for line in lines)


def test_render_task_bool_value() -> None:
    """Boolean values are rendered as lowercase strings."""
    task = {
        "name": "Enable service",
        "ansible.builtin.service": {
            "name": "nginx",
            "state": "started",
            "enabled": True,
        },
    }
    lines = _render_task(task)
    combined = "\n".join(lines)
    assert "enabled: true" in combined


def test_render_task_top_level_bool_value() -> None:
    """Top-level boolean task attributes are rendered as lowercase strings."""
    task = {
        "name": "Shell task",
        "ansible.builtin.shell": {"cmd": "ls"},
        "become": True,
    }
    lines = _render_task(task)
    combined = "\n".join(lines)
    assert "become: true" in combined


# ---------------------------------------------------------------------------
# _render_playbook
# ---------------------------------------------------------------------------


def test_render_playbook_structure() -> None:
    """Rendered playbook has correct YAML structure."""
    tasks = [
        {
            "name": "Install nginx",
            "ansible.builtin.apt": {"name": ["nginx"], "state": "present"},
        }
    ]
    yaml_output = _render_playbook(tasks, "test.sh")
    assert "---" in yaml_output
    assert "hosts: all" in yaml_output
    assert "become: true" in yaml_output
    assert "Install nginx" in yaml_output


def test_render_playbook_strips_metadata() -> None:
    """_metadata keys are stripped from rendered playbook."""
    tasks = [
        {
            "name": "Shell task",
            "ansible.builtin.shell": {"cmd": "ls"},
            "_metadata": {"source_line": 1, "confidence": 0.5},
        }
    ]
    yaml_output = _render_playbook(tasks, "test.sh")
    assert "_metadata" not in yaml_output


# ---------------------------------------------------------------------------
# _collect_warnings
# ---------------------------------------------------------------------------


def test_collect_warnings_includes_fallbacks() -> None:
    """Warnings include shell fallback messages."""
    ir = {
        "shell_fallbacks": [
            {"line": 1, "raw": "custom-cmd", "warning": "No mapping found"}
        ],
        "idempotency_risks": [],
    }
    warnings = _collect_warnings(ir)
    assert len(warnings) == 1
    assert "Line 1" in warnings[0]


def test_collect_warnings_includes_risks() -> None:
    """Warnings include idempotency risk messages."""
    ir = {
        "shell_fallbacks": [],
        "idempotency_risks": [
            {
                "line": 2,
                "type": "raw_download",
                "suggestion": "Use checksum",
                "raw": "curl url",
            }
        ],
    }
    warnings = _collect_warnings(ir)
    assert any("Idempotency risk" in w for w in warnings)


def test_collect_warnings_empty() -> None:
    """No warnings for clean IR."""
    ir = {"shell_fallbacks": [], "idempotency_risks": []}
    assert _collect_warnings(ir) == []


# ---------------------------------------------------------------------------
# _build_idempotency_report
# ---------------------------------------------------------------------------


def test_build_idempotency_report_structure() -> None:
    """Idempotency report has expected keys."""
    ir = {
        "idempotency_risks": [
            {
                "line": 1,
                "type": "raw_download",
                "suggestion": "Use checksum",
                "raw": "curl url",
            }
        ],
        "shell_fallbacks": [{"line": 2, "raw": "cmd", "warning": "No mapping"}],
    }
    report = _build_idempotency_report(ir)
    assert "total_risks" in report
    assert "risks" in report
    assert "non_idempotent_tasks" in report
    assert "suggestions" in report
    assert report["total_risks"] == 1
    assert report["non_idempotent_tasks"] == 1


def test_build_idempotency_report_deduplicates_suggestions() -> None:
    """Duplicate suggestions are deduplicated."""
    ir = {
        "idempotency_risks": [
            {"line": 1, "type": "t", "suggestion": "same", "raw": "x"},
            {"line": 2, "type": "t", "suggestion": "same", "raw": "y"},
        ],
        "shell_fallbacks": [],
    }
    report = _build_idempotency_report(ir)
    assert len(report["suggestions"]) == 1


# ---------------------------------------------------------------------------
# convert_bash_content_to_ansible (public API)
# ---------------------------------------------------------------------------


def test_convert_bash_content_to_ansible_returns_json() -> None:
    """Returns valid JSON string."""
    result = convert_bash_content_to_ansible("apt-get install nginx\n")
    data = json.loads(result)
    assert data["status"] == "success"


def test_convert_bash_content_to_ansible_has_playbook_yaml() -> None:
    """Response contains playbook_yaml key."""
    result = convert_bash_content_to_ansible("apt-get install nginx\n")
    data = json.loads(result)
    assert "playbook_yaml" in data
    assert "---" in data["playbook_yaml"]


def test_convert_bash_content_to_ansible_has_tasks() -> None:
    """Response contains tasks list."""
    result = convert_bash_content_to_ansible("apt-get install -y nginx\n")
    data = json.loads(result)
    assert "tasks" in data
    assert isinstance(data["tasks"], list)


def test_convert_bash_content_to_ansible_has_idempotency_report() -> None:
    """Response contains idempotency_report."""
    result = convert_bash_content_to_ansible("apt-get install nginx\n")
    data = json.loads(result)
    assert "idempotency_report" in data


def test_convert_bash_content_to_ansible_empty_script() -> None:
    """Empty script converts without error."""
    result = convert_bash_content_to_ansible("")
    data = json.loads(result)
    assert data["status"] == "success"
    assert data["tasks"] == []


def test_convert_bash_content_to_ansible_script_path_label() -> None:
    """script_path label is included in response."""
    result = convert_bash_content_to_ansible("echo hi\n", script_path="my_script.sh")
    data = json.loads(result)
    assert data["script_path"] == "my_script.sh"


# ---------------------------------------------------------------------------
# convert_bash_to_ansible (file-path API)
# ---------------------------------------------------------------------------


def test_convert_bash_to_ansible_success(tmp_path: Path) -> None:
    """Converts a real file successfully."""
    script = tmp_path / "test.sh"
    script.write_text("apt-get install -y nginx\nsystemctl start nginx\n")
    with patch(
        "souschef.converters.bash_to_ansible._get_workspace_root",
        return_value=tmp_path,
    ):
        result = convert_bash_to_ansible(str(script))
    data = json.loads(result)
    assert data["status"] == "success"
    assert "playbook_yaml" in data


def test_convert_bash_to_ansible_file_not_found(tmp_path: Path) -> None:
    """Returns error JSON for missing file."""
    missing = tmp_path / "missing.sh"
    with patch(
        "souschef.converters.bash_to_ansible._get_workspace_root",
        return_value=tmp_path,
    ):
        result = convert_bash_to_ansible(str(missing))
    data = json.loads(result)
    assert data["status"] == "error"
    assert "error" in data


def test_convert_bash_to_ansible_is_directory(tmp_path: Path) -> None:
    """Returns error JSON when path is a directory."""
    with patch(
        "souschef.converters.bash_to_ansible._get_workspace_root",
        return_value=tmp_path,
    ):
        result = convert_bash_to_ansible(str(tmp_path))
    data = json.loads(result)
    assert data["status"] == "error"


def test_convert_bash_to_ansible_permission_error(tmp_path: Path) -> None:
    """Returns error JSON on permission denied."""
    script = tmp_path / "noperm.sh"
    script.write_text("apt-get install nginx\n")
    script.chmod(0o000)
    try:
        with patch(
            "souschef.converters.bash_to_ansible._get_workspace_root",
            return_value=tmp_path,
        ):
            result = convert_bash_to_ansible(str(script))
        data = json.loads(result)
        assert data["status"] == "error"
    finally:
        script.chmod(0o644)


def test_convert_bash_to_ansible_value_error(tmp_path: Path) -> None:
    """Returns error JSON on ValueError from path utilities."""
    with patch(
        "souschef.converters.bash_to_ansible._normalize_path",
        side_effect=ValueError("bad path"),
    ):
        result = convert_bash_to_ansible("bad_path.sh")
    data = json.loads(result)
    assert data["status"] == "error"
