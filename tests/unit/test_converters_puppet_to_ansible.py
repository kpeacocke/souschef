"""
Unit tests for the Puppet to Ansible converter.

Tests cover:
- convert_puppet_manifest_to_ansible: single file conversion
- convert_puppet_module_to_ansible: module directory conversion
- convert_puppet_resource_to_task: single resource conversion
- All resource type converters (package, file, service, user, group, exec, etc.)
- YAML output structure validation
- Error handling
- Helper functions
"""

from pathlib import Path
from unittest.mock import patch

import yaml

from souschef.converters.puppet_to_ansible import (
    ENSURE_TO_STATE,
    RESOURCE_MODULE_MAP,
    _convert_unsupported,
    _generate_puppet_playbook,
    _map_ensure,
    _source_to_play_name,
    convert_puppet_manifest_to_ansible,
    convert_puppet_module_to_ansible,
    convert_puppet_resource_to_task,
    get_puppet_ansible_module_map,
    get_supported_puppet_types,
)
from souschef.core.path_utils import safe_read_text

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_MANIFEST = """\
package { 'nginx':
  ensure => installed,
}

service { 'nginx':
  ensure => running,
  enable => true,
}

file { '/etc/nginx':
  ensure => directory,
  owner  => 'root',
  mode   => '0755',
}
"""

FILE_WITH_SOURCE_MANIFEST = """\
file { '/etc/app/config.conf':
  source => 'puppet:///modules/app/config.conf',
  owner  => 'root',
}
"""

FILE_WITH_CONTENT_MANIFEST = """\
file { '/etc/app/motd':
  content => 'Hello world',
  owner   => 'root',
}
"""

FILE_WITH_ERB_MANIFEST = """\
file { '/etc/app/config.erb':
  content => '<%= @host %>',
  owner   => 'root',
}
"""

USER_MANIFEST = """\
user { 'deploy':
  ensure   => present,
  home     => '/home/deploy',
  shell    => '/bin/bash',
  uid      => '1001',
  managehome => true,
}
"""

GROUP_MANIFEST = """\
group { 'deploy':
  ensure => present,
  gid    => '1001',
}
"""

EXEC_MANIFEST = """\
exec { 'init-db':
  command => '/usr/local/bin/init-db.sh',
  creates => '/var/db/.initialized',
  cwd     => '/var/db',
}
"""

EXEC_UNLESS_MANIFEST = """\
exec { 'install-app':
  command => '/usr/local/bin/install.sh',
  unless  => 'test -f /opt/app/installed',
}
"""

EXEC_ONLYIF_MANIFEST = """\
exec { 'configure':
  command => '/usr/local/bin/configure.sh',
  onlyif  => 'test -f /etc/app.conf',
}
"""

CRON_MANIFEST = """\
cron { 'backup':
  command  => '/usr/local/bin/backup.sh',
  hour     => '1',
  minute   => '0',
  user     => 'backup',
}
"""

HOST_MANIFEST = """\
host { 'db.internal':
  ip     => '10.0.0.10',
  ensure => present,
}
"""

HOST_NO_IP_MANIFEST = """\
host { 'db.internal':
  ensure => present,
}
"""

MOUNT_MANIFEST = """\
mount { '/mnt/data':
  device => '/dev/sdb1',
  fstype => 'ext4',
  ensure => mounted,
}
"""

SSH_KEY_MANIFEST = """\
ssh_authorized_key { 'deploy_key':
  key  => 'AAAA...',
  user => 'deploy',
}
"""


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _load_yaml(text: str) -> list:
    """Parse YAML and return the playbook list."""
    return yaml.safe_load(text)


# ---------------------------------------------------------------------------
# Tests: convert_puppet_manifest_to_ansible
# ---------------------------------------------------------------------------


def test_convert_simple_manifest_to_playbook(tmp_path: Path) -> None:
    """Test that a simple manifest produces a valid Ansible playbook."""
    manifest = tmp_path / "webserver.pp"
    manifest.write_text(SIMPLE_MANIFEST, encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))

    playbook = _load_yaml(result)
    assert isinstance(playbook, list)
    assert len(playbook) == 1
    play = playbook[0]
    assert play["hosts"] == "all"
    assert play["become"] is True
    assert "tasks" in play


def test_convert_manifest_package_task(tmp_path: Path) -> None:
    """Test that package resources are converted to package tasks."""
    manifest = tmp_path / "pkg.pp"
    manifest.write_text("package { 'nginx': ensure => installed }", encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    pkg_tasks = [
        t for t in tasks if "ansible.builtin.package" in t
    ]
    assert len(pkg_tasks) >= 1
    assert pkg_tasks[0]["ansible.builtin.package"]["name"] == "nginx"
    assert pkg_tasks[0]["ansible.builtin.package"]["state"] == "present"


def test_convert_manifest_service_task(tmp_path: Path) -> None:
    """Test that service resources are converted to service tasks."""
    manifest = tmp_path / "svc.pp"
    manifest.write_text(
        "service { 'nginx': ensure => running, enable => true }", encoding="utf-8"
    )

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    svc_tasks = [t for t in tasks if "ansible.builtin.service" in t]
    assert len(svc_tasks) >= 1
    assert svc_tasks[0]["ansible.builtin.service"]["state"] == "started"
    assert svc_tasks[0]["ansible.builtin.service"]["enabled"] is True


def test_convert_manifest_file_directory_task(tmp_path: Path) -> None:
    """Test that file[directory] resources produce file tasks with state=directory."""
    manifest = tmp_path / "f.pp"
    manifest.write_text(
        "file { '/etc/app': ensure => directory }", encoding="utf-8"
    )

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    file_tasks = [t for t in tasks if "ansible.builtin.file" in t]
    assert len(file_tasks) >= 1
    assert file_tasks[0]["ansible.builtin.file"]["state"] == "directory"


def test_convert_manifest_file_with_source(tmp_path: Path) -> None:
    """Test that file resources with source produce copy tasks."""
    manifest = tmp_path / "f.pp"
    manifest.write_text(FILE_WITH_SOURCE_MANIFEST, encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    copy_tasks = [t for t in tasks if "ansible.builtin.copy" in t]
    assert len(copy_tasks) >= 1


def test_convert_manifest_file_with_content(tmp_path: Path) -> None:
    """Test that file resources with plain content produce copy tasks."""
    manifest = tmp_path / "f.pp"
    manifest.write_text(FILE_WITH_CONTENT_MANIFEST, encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    copy_tasks = [t for t in tasks if "ansible.builtin.copy" in t]
    assert len(copy_tasks) >= 1


def test_convert_manifest_file_with_erb_content(tmp_path: Path) -> None:
    """Test that file resources with ERB content produce template tasks."""
    manifest = tmp_path / "f.pp"
    manifest.write_text(FILE_WITH_ERB_MANIFEST, encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    tpl_tasks = [t for t in tasks if "ansible.builtin.template" in t]
    assert len(tpl_tasks) >= 1


def test_convert_manifest_user(tmp_path: Path) -> None:
    """Test that user resources produce Ansible user tasks."""
    manifest = tmp_path / "u.pp"
    manifest.write_text(USER_MANIFEST, encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    user_tasks = [t for t in tasks if "ansible.builtin.user" in t]
    assert len(user_tasks) >= 1
    assert user_tasks[0]["ansible.builtin.user"]["name"] == "deploy"


def test_convert_manifest_group(tmp_path: Path) -> None:
    """Test that group resources produce Ansible group tasks."""
    manifest = tmp_path / "g.pp"
    manifest.write_text(GROUP_MANIFEST, encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    grp_tasks = [t for t in tasks if "ansible.builtin.group" in t]
    assert len(grp_tasks) >= 1


def test_convert_manifest_exec_with_creates(tmp_path: Path) -> None:
    """Test that exec resources with creates produce command tasks."""
    manifest = tmp_path / "e.pp"
    manifest.write_text(EXEC_MANIFEST, encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    exec_tasks = [t for t in tasks if "ansible.builtin.command" in t]
    assert len(exec_tasks) >= 1


def test_convert_manifest_exec_with_unless(tmp_path: Path) -> None:
    """Test that exec resources with unless produce when conditions."""
    manifest = tmp_path / "e.pp"
    manifest.write_text(EXEC_UNLESS_MANIFEST, encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    exec_tasks = [t for t in tasks if "ansible.builtin.command" in t]
    assert len(exec_tasks) >= 1
    # unless should produce a when condition
    assert "when" in exec_tasks[0]


def test_convert_manifest_exec_with_onlyif(tmp_path: Path) -> None:
    """Test that exec resources with onlyif produce when conditions."""
    manifest = tmp_path / "e.pp"
    manifest.write_text(EXEC_ONLYIF_MANIFEST, encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    exec_tasks = [t for t in tasks if "ansible.builtin.command" in t]
    assert len(exec_tasks) >= 1
    assert "when" in exec_tasks[0]


def test_convert_manifest_cron(tmp_path: Path) -> None:
    """Test that cron resources produce Ansible cron tasks."""
    manifest = tmp_path / "c.pp"
    manifest.write_text(CRON_MANIFEST, encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    cron_tasks = [t for t in tasks if "ansible.builtin.cron" in t]
    assert len(cron_tasks) >= 1


def test_convert_manifest_host(tmp_path: Path) -> None:
    """Test that host resources produce lineinfile tasks."""
    manifest = tmp_path / "h.pp"
    manifest.write_text(HOST_MANIFEST, encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    host_tasks = [t for t in tasks if "ansible.builtin.lineinfile" in t]
    assert len(host_tasks) >= 1


def test_convert_manifest_host_no_ip(tmp_path: Path) -> None:
    """Test that host resources without IP produce debug warning tasks."""
    manifest = tmp_path / "h.pp"
    manifest.write_text(HOST_NO_IP_MANIFEST, encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    debug_tasks = [t for t in tasks if "ansible.builtin.debug" in t]
    assert len(debug_tasks) >= 1


def test_convert_manifest_mount(tmp_path: Path) -> None:
    """Test that mount resources produce posix.mount tasks."""
    manifest = tmp_path / "m.pp"
    manifest.write_text(MOUNT_MANIFEST, encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    mount_tasks = [t for t in tasks if "ansible.posix.mount" in t]
    assert len(mount_tasks) >= 1


def test_convert_manifest_ssh_authorized_key(tmp_path: Path) -> None:
    """Test that ssh_authorized_key resources produce authorized_key tasks."""
    manifest = tmp_path / "ssh.pp"
    manifest.write_text(SSH_KEY_MANIFEST, encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    tasks = playbook[0]["tasks"]

    key_tasks = [t for t in tasks if "ansible.posix.authorized_key" in t]
    assert len(key_tasks) >= 1


def test_convert_manifest_file_not_found(tmp_path: Path) -> None:
    """Test error handling for missing manifest file."""
    result = convert_puppet_manifest_to_ansible(str(tmp_path / "missing.pp"))
    assert "Error" in result or "not found" in result.lower()


def test_convert_manifest_is_directory(tmp_path: Path) -> None:
    """Test error handling when a directory is passed as manifest."""
    result = convert_puppet_manifest_to_ansible(str(tmp_path))
    assert "Error" in result or "directory" in result.lower()


def test_convert_manifest_too_large(tmp_path: Path) -> None:
    """Test rejection of oversized manifests."""
    manifest = tmp_path / "huge.pp"
    manifest.write_bytes(b"x" * 2_100_000)
    result = convert_puppet_manifest_to_ansible(str(manifest))
    assert "too large" in result.lower()


def test_convert_manifest_permission_error(tmp_path: Path) -> None:
    """Test handling of permission errors during conversion."""
    manifest = tmp_path / "test.pp"
    manifest.write_text("package { 'vim': ensure => installed }", encoding="utf-8")
    with patch(
        "souschef.converters.puppet_to_ansible.safe_read_text",
        side_effect=PermissionError("denied"),
    ):
        result = convert_puppet_manifest_to_ansible(str(manifest))
    assert "Error" in result


def test_convert_manifest_generic_exception(tmp_path: Path) -> None:
    """Test that generic exceptions return an error message."""
    manifest = tmp_path / "test.pp"
    manifest.write_text("package { 'vim': ensure => installed }", encoding="utf-8")
    with patch(
        "souschef.converters.puppet_to_ansible._parse_manifest_content",
        side_effect=RuntimeError("boom"),
    ):
        result = convert_puppet_manifest_to_ansible(str(manifest))
    assert "error occurred" in result.lower()


def test_convert_manifest_empty(tmp_path: Path) -> None:
    """Test that an empty manifest produces a playbook with a debug task."""
    manifest = tmp_path / "empty.pp"
    manifest.write_text("", encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))
    playbook = _load_yaml(result)
    assert isinstance(playbook, list)
    assert len(playbook) == 1


# ---------------------------------------------------------------------------
# Tests: convert_puppet_module_to_ansible
# ---------------------------------------------------------------------------


def test_convert_module_to_ansible(tmp_path: Path) -> None:
    """Test converting a module directory to an Ansible playbook."""
    (tmp_path / "init.pp").write_text(SIMPLE_MANIFEST, encoding="utf-8")

    result = convert_puppet_module_to_ansible(str(tmp_path))

    playbook = _load_yaml(result)
    assert isinstance(playbook, list)
    assert len(playbook) == 1


def test_convert_module_no_manifests(tmp_path: Path) -> None:
    """Test that a directory without .pp files returns a warning."""
    result = convert_puppet_module_to_ansible(str(tmp_path))
    assert "Warning" in result or "No Puppet manifests" in result


def test_convert_module_not_found(tmp_path: Path) -> None:
    """Test error when module directory doesn't exist."""
    result = convert_puppet_module_to_ansible(str(tmp_path / "missing"))
    assert "Error" in result or "not found" in result.lower()


def test_convert_module_is_file(tmp_path: Path) -> None:
    """Test error when a file is passed as module path."""
    manifest = tmp_path / "file.pp"
    manifest.write_text("", encoding="utf-8")
    result = convert_puppet_module_to_ansible(str(manifest))
    assert "Error" in result or "directory" in result.lower()


def test_convert_module_generic_exception() -> None:
    """Test that generic exceptions return an error message."""
    with patch(
        "souschef.converters.puppet_to_ansible._normalize_path",
        side_effect=Exception("boom"),
    ):
        result = convert_puppet_module_to_ansible("/some/path")
    assert "error occurred" in result.lower()


def test_convert_module_value_error(tmp_path: Path) -> None:
    """Test that ValueError during module conversion returns an error."""
    with patch(
        "souschef.converters.puppet_to_ansible._ensure_within_base_path",
        side_effect=ValueError("path traversal"),
    ):
        result = convert_puppet_module_to_ansible("/some/path")
    assert "Error" in result


def test_convert_module_file_not_found_error(tmp_path: Path) -> None:
    """Test that FileNotFoundError during module conversion returns an error."""
    with patch(
        "souschef.converters.puppet_to_ansible._ensure_within_base_path",
        side_effect=FileNotFoundError("not found"),
    ):
        result = convert_puppet_module_to_ansible("/some/path")
    assert "Error" in result or "not found" in result.lower()


def test_convert_module_permission_error(tmp_path: Path) -> None:
    """Test handling of permission errors during module conversion."""
    with patch(
        "souschef.converters.puppet_to_ansible._get_workspace_root",
        side_effect=PermissionError("denied"),
    ):
        result = convert_puppet_module_to_ansible(str(tmp_path))
    assert "Error" in result


def test_convert_module_skips_unreadable_file(tmp_path: Path) -> None:
    """Test that unreadable files are skipped during module conversion."""
    good = tmp_path / "good.pp"
    bad = tmp_path / "bad.pp"
    good.write_text("package { 'vim': ensure => installed }", encoding="utf-8")
    bad.write_text("package { 'curl': ensure => installed }", encoding="utf-8")

    def _selective(path: Path, *args: object, **kwargs: object) -> str:
        if "bad" in str(path):
            raise OSError("cannot read")
        return safe_read_text(path, *args, **kwargs)

    with patch(
        "souschef.converters.puppet_to_ansible.safe_read_text",
        side_effect=_selective,
    ):
        result = convert_puppet_module_to_ansible(str(tmp_path))

    assert "vim" in result or "Puppet" in result


# ---------------------------------------------------------------------------
# Tests: convert_puppet_resource_to_task
# ---------------------------------------------------------------------------


def test_convert_resource_package() -> None:
    """Test converting a package resource."""
    task = convert_puppet_resource_to_task("package", "nginx", {"ensure": "installed"})
    assert "ansible.builtin.package" in task
    assert task["ansible.builtin.package"]["name"] == "nginx"
    assert task["ansible.builtin.package"]["state"] == "present"


def test_convert_resource_service_enabled() -> None:
    """Test converting a service resource with enable."""
    task = convert_puppet_resource_to_task(
        "service", "nginx", {"ensure": "running", "enable": "true"}
    )
    assert "ansible.builtin.service" in task
    assert task["ansible.builtin.service"]["enabled"] is True


def test_convert_resource_service_disabled() -> None:
    """Test converting a service resource with disable."""
    task = convert_puppet_resource_to_task(
        "service", "nginx", {"ensure": "stopped", "enable": "false"}
    )
    assert task["ansible.builtin.service"]["enabled"] is False


def test_convert_resource_file_basic() -> None:
    """Test converting a basic file resource."""
    task = convert_puppet_resource_to_task("file", "/tmp/test", {"ensure": "file"})
    assert "ansible.builtin.file" in task


def test_convert_resource_user() -> None:
    """Test converting a user resource."""
    task = convert_puppet_resource_to_task(
        "user", "deploy", {"ensure": "present", "home": "/home/deploy"}
    )
    assert "ansible.builtin.user" in task
    assert task["ansible.builtin.user"]["home"] == "/home/deploy"


def test_convert_resource_user_managehome_false() -> None:
    """Test converting a user resource with managehome=false."""
    task = convert_puppet_resource_to_task(
        "user", "deploy", {"ensure": "present", "managehome": "false"}
    )
    assert task["ansible.builtin.user"]["create_home"] is False


def test_convert_resource_group() -> None:
    """Test converting a group resource."""
    task = convert_puppet_resource_to_task(
        "group", "wheel", {"ensure": "present", "gid": "10"}
    )
    assert "ansible.builtin.group" in task
    assert task["ansible.builtin.group"]["gid"] == "10"


def test_convert_resource_exec_basic() -> None:
    """Test converting a basic exec resource."""
    task = convert_puppet_resource_to_task("exec", "run-script", {})
    assert "ansible.builtin.command" in task


def test_convert_resource_exec_with_command_attr() -> None:
    """Test exec resource uses command attribute if present."""
    task = convert_puppet_resource_to_task(
        "exec", "run", {"command": "/usr/bin/setup.sh"}
    )
    assert task["ansible.builtin.command"]["cmd"] == "/usr/bin/setup.sh"


def test_convert_resource_exec_with_creates() -> None:
    """Test exec resource with creates attribute."""
    task = convert_puppet_resource_to_task(
        "exec", "setup", {"creates": "/etc/app/.done"}
    )
    assert "args" in task
    assert task["args"]["creates"] == "/etc/app/.done"


def test_convert_resource_exec_with_cwd() -> None:
    """Test exec resource with cwd attribute."""
    task = convert_puppet_resource_to_task("exec", "run", {"cwd": "/var/app"})
    assert task["ansible.builtin.command"]["chdir"] == "/var/app"


def test_convert_resource_cron() -> None:
    """Test converting a cron resource."""
    task = convert_puppet_resource_to_task(
        "cron", "backup", {"command": "/bin/backup.sh", "hour": "2"}
    )
    assert "ansible.builtin.cron" in task
    assert task["ansible.builtin.cron"]["job"] == "/bin/backup.sh"
    assert task["ansible.builtin.cron"]["hour"] == "2"


def test_convert_resource_host_with_ip() -> None:
    """Test converting a host resource with IP."""
    task = convert_puppet_resource_to_task(
        "host", "db.internal", {"ip": "10.0.0.1", "ensure": "present"}
    )
    assert "ansible.builtin.lineinfile" in task
    assert "10.0.0.1" in task["ansible.builtin.lineinfile"]["line"]


def test_convert_resource_host_no_ip() -> None:
    """Test converting a host resource without IP produces debug task."""
    task = convert_puppet_resource_to_task("host", "db.internal", {})
    assert "ansible.builtin.debug" in task


def test_convert_resource_mount() -> None:
    """Test converting a mount resource."""
    task = convert_puppet_resource_to_task(
        "mount",
        "/mnt/data",
        {"device": "/dev/sdb1", "fstype": "ext4", "ensure": "mounted"},
    )
    assert "ansible.posix.mount" in task
    assert task["ansible.posix.mount"]["src"] == "/dev/sdb1"
    assert task["ansible.posix.mount"]["fstype"] == "ext4"


def test_convert_resource_mount_with_options() -> None:
    """Test converting a mount resource with options."""
    task = convert_puppet_resource_to_task(
        "mount", "/mnt/data", {"options": "noatime,nodiratime"}
    )
    assert task["ansible.posix.mount"]["opts"] == "noatime,nodiratime"


def test_convert_resource_ssh_authorized_key() -> None:
    """Test converting ssh_authorized_key resource."""
    task = convert_puppet_resource_to_task(
        "ssh_authorized_key",
        "my_key",
        {"key": "AAAA...", "user": "deploy"},
    )
    assert "ansible.posix.authorized_key" in task
    assert task["ansible.posix.authorized_key"]["user"] == "deploy"


def test_convert_resource_unsupported_type() -> None:
    """Test that unsupported resource types produce debug warning tasks."""
    task = convert_puppet_resource_to_task("augeas", "my_augeas", {})
    assert "ansible.builtin.debug" in task
    assert "WARNING" in task["name"]


# ---------------------------------------------------------------------------
# Tests: _generate_puppet_playbook
# ---------------------------------------------------------------------------


def test_generate_playbook_with_unsupported() -> None:
    """Test that unsupported constructs produce warning tasks in the playbook."""
    parsed = {
        "resources": [],
        "classes": [],
        "variables": [],
        "unsupported": [
            {
                "construct": "Hiera lookup",
                "text": "hiera('key')",
                "source_file": "test.pp",
                "line": 5,
            }
        ],
    }
    result = _generate_puppet_playbook(parsed, "test.pp")
    playbook = yaml.safe_load(result)
    tasks = playbook[0]["tasks"]
    warning_tasks = [t for t in tasks if "WARNING" in t.get("name", "")]
    assert len(warning_tasks) >= 1


def test_generate_playbook_empty_resources() -> None:
    """Test that a playbook with no resources has a debug fallback task."""
    parsed = {
        "resources": [],
        "classes": [],
        "variables": [],
        "unsupported": [],
    }
    result = _generate_puppet_playbook(parsed, "empty.pp")
    playbook = yaml.safe_load(result)
    tasks = playbook[0]["tasks"]
    assert len(tasks) >= 1


# ---------------------------------------------------------------------------
# Tests: helper functions
# ---------------------------------------------------------------------------


def test_map_ensure_installed() -> None:
    """Test that 'installed' maps to 'present'."""
    assert _map_ensure("installed") == "present"


def test_map_ensure_running() -> None:
    """Test that 'running' maps to 'started'."""
    assert _map_ensure("running") == "started"


def test_map_ensure_purged() -> None:
    """Test that 'purged' maps to 'absent'."""
    assert _map_ensure("purged") == "absent"


def test_map_ensure_unknown() -> None:
    """Test that unknown ensure values are returned as-is."""
    assert _map_ensure("whatever") == "whatever"


def test_map_ensure_case_insensitive() -> None:
    """Test that ensure mapping is case-insensitive."""
    assert _map_ensure("INSTALLED") == "present"
    assert _map_ensure("Running") == "started"


def test_source_to_play_name() -> None:
    """Test play name generation from source path."""
    name = _source_to_play_name("/path/to/manifest.pp")
    assert "Converted from Puppet" in name
    assert "manifest" in name.lower()


def test_source_to_play_name_special_chars() -> None:
    """Test play name with special characters in path."""
    name = _source_to_play_name("/path/to/my.module/init.pp")
    assert "Converted from Puppet" in name


def test_get_puppet_ansible_module_map() -> None:
    """Test that module map returns expected entries."""
    module_map = get_puppet_ansible_module_map()
    assert "package" in module_map
    assert "service" in module_map
    assert "file" in module_map
    assert module_map["package"] == "ansible.builtin.package"
    assert module_map["service"] == "ansible.builtin.service"


def test_get_supported_puppet_types() -> None:
    """Test that supported types list is sorted and complete."""
    types = get_supported_puppet_types()
    assert isinstance(types, list)
    assert types == sorted(types)
    assert "package" in types
    assert "file" in types
    assert "service" in types
    assert "user" in types
    assert "group" in types


def test_convert_unsupported_resource_type() -> None:
    """Test the unsupported resource type converter."""
    task = _convert_unsupported("custom_resource", "my_thing")
    assert "ansible.builtin.debug" in task
    assert "WARNING" in task["name"]
    assert "custom_resource" in task["ansible.builtin.debug"]["msg"]


def test_ensure_to_state_mapping_completeness() -> None:
    """Test that ENSURE_TO_STATE covers common Puppet ensure values."""
    assert ENSURE_TO_STATE["installed"] == "present"
    assert ENSURE_TO_STATE["absent"] == "absent"
    assert ENSURE_TO_STATE["running"] == "started"
    assert ENSURE_TO_STATE["stopped"] == "stopped"
    assert ENSURE_TO_STATE["latest"] == "latest"


def test_resource_module_map_completeness() -> None:
    """Test that RESOURCE_MODULE_MAP has expected entries."""
    assert "package" in RESOURCE_MODULE_MAP
    assert "service" in RESOURCE_MODULE_MAP
    assert "file" in RESOURCE_MODULE_MAP
    assert "user" in RESOURCE_MODULE_MAP
    assert "group" in RESOURCE_MODULE_MAP
    assert "exec" in RESOURCE_MODULE_MAP
    assert "cron" in RESOURCE_MODULE_MAP
    assert "host" in RESOURCE_MODULE_MAP
    assert "mount" in RESOURCE_MODULE_MAP
    assert "ssh_authorized_key" in RESOURCE_MODULE_MAP
