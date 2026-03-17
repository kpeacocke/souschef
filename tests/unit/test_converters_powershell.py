"""
Unit tests for souschef/converters/powershell.py.

Covers all public API functions, all action-type converter functions,
edge cases, and error handling to achieve 100% line and branch coverage.
"""

from __future__ import annotations

import json
from pathlib import Path


class TestConvertPowershellToAnsible:
    """Tests for the convert_powershell_to_ansible() public API."""

    def test_convert_valid_script(self, tmp_path: Path) -> None:
        """convert_powershell_to_ansible returns JSON for a valid .ps1 file."""
        from souschef.converters.powershell import convert_powershell_to_ansible

        script = tmp_path / "setup.ps1"
        script.write_text("Install-WindowsFeature -Name Web-Server\n", encoding="utf-8")

        result = json.loads(convert_powershell_to_ansible(str(script)))
        assert result["status"] == "success"
        assert "playbook_yaml" in result
        assert result["tasks_generated"] >= 1

    def test_convert_nonexistent_file(self, tmp_path: Path) -> None:
        """convert_powershell_to_ansible returns error JSON for a missing file."""
        from souschef.converters.powershell import convert_powershell_to_ansible

        result = json.loads(
            convert_powershell_to_ansible(str(tmp_path / "missing.ps1"))
        )
        assert result["status"] == "error"
        assert "error" in result

    def test_custom_playbook_name_and_hosts(self, tmp_path: Path) -> None:
        """Custom playbook_name and hosts are reflected in the output."""
        from souschef.converters.powershell import convert_powershell_to_ansible

        script = tmp_path / "setup.ps1"
        script.write_text("Start-Service -Name W3SVC\n", encoding="utf-8")

        result = json.loads(
            convert_powershell_to_ansible(
                str(script), playbook_name="my_play", hosts="win_servers"
            )
        )
        assert "my_play" in result["playbook_yaml"]
        assert "win_servers" in result["playbook_yaml"]

    def test_win_shell_fallback_count(self, tmp_path: Path) -> None:
        """win_shell_fallbacks count is correct."""
        from souschef.converters.powershell import convert_powershell_to_ansible

        script = tmp_path / "setup.ps1"
        script.write_text(
            "Install-WindowsFeature -Name Web-Server\nWrite-Host 'hello'\n",
            encoding="utf-8",
        )

        result = json.loads(convert_powershell_to_ansible(str(script)))
        assert result["win_shell_fallbacks"] == 1


class TestConvertPowershellContentToAnsible:
    """Tests for convert_powershell_content_to_ansible() with inline content."""

    def test_empty_content(self) -> None:
        """Empty content produces a valid empty playbook."""
        from souschef.converters.powershell import convert_powershell_content_to_ansible

        result = json.loads(convert_powershell_content_to_ansible(""))
        assert result["status"] == "success"
        assert result["tasks_generated"] == 0

    def test_playbook_yaml_is_valid_yaml(self) -> None:
        """The generated playbook_yaml can be parsed as valid YAML."""
        import yaml

        from souschef.converters.powershell import convert_powershell_content_to_ansible

        content = "Install-WindowsFeature -Name Web-Server\n"
        result = json.loads(convert_powershell_content_to_ansible(content))
        playbook = yaml.safe_load(result["playbook_yaml"])
        assert isinstance(playbook, list)
        assert playbook[0]["hosts"] == "windows"

    def test_custom_source_label(self) -> None:
        """Custom source label is reflected in the output."""
        from souschef.converters.powershell import convert_powershell_content_to_ansible

        result = json.loads(
            convert_powershell_content_to_ansible("", source="my_script.ps1")
        )
        assert result["source"] == "my_script.ps1"

    def test_warnings_propagated(self) -> None:
        """Warnings from parsing are included in conversion output."""
        from souschef.converters.powershell import convert_powershell_content_to_ansible

        result = json.loads(
            convert_powershell_content_to_ansible("Write-Host 'unrecognised'")
        )
        assert len(result["warnings"]) > 0


class TestActionToTask:
    """Tests for _action_to_task() covering all action types."""

    def _make_action(
        self,
        action_type: str,
        params: dict,
        raw: str = "",
        src_line: int = 1,
        confidence: str = "high",
        requires_elevation: bool = False,
    ) -> dict:
        """Build an action dict for testing."""
        return {
            "action_type": action_type,
            "params": params,
            "raw": raw,
            "source_line": src_line,
            "confidence": confidence,
            "requires_elevation": requires_elevation,
        }

    def test_windows_feature_install_task(self) -> None:
        """windows_feature_install maps to win_feature with state=present."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "windows_feature_install",
            {"feature_name": "Web-Server"},
        )
        task, warning = _action_to_task(action)
        assert "ansible.windows.win_feature" in task
        assert task["ansible.windows.win_feature"]["state"] == "present"
        assert warning == ""

    def test_windows_feature_remove_task(self) -> None:
        """windows_feature_remove maps to win_feature with state=absent."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "windows_feature_remove",
            {"feature_name": "Web-Server"},
        )
        task, _ = _action_to_task(action)
        assert task["ansible.windows.win_feature"]["state"] == "absent"

    def test_optional_feature_enable_task(self) -> None:
        """windows_optional_feature_enable maps to win_optional_feature enabled."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "windows_optional_feature_enable",
            {"feature_name": "IIS-WebServer"},
        )
        task, _ = _action_to_task(action)
        assert "ansible.windows.win_optional_feature" in task
        assert task["ansible.windows.win_optional_feature"]["state"] == "enabled"

    def test_optional_feature_disable_task(self) -> None:
        """windows_optional_feature_disable maps to win_optional_feature disabled."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "windows_optional_feature_disable",
            {"feature_name": "IIS-WebServer"},
        )
        task, _ = _action_to_task(action)
        assert task["ansible.windows.win_optional_feature"]["state"] == "disabled"

    def test_service_start_task(self) -> None:
        """windows_service_start maps to win_service with state=started."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "windows_service_start",
            {"service_name": "W3SVC"},
        )
        task, _ = _action_to_task(action)
        assert task["ansible.windows.win_service"]["state"] == "started"

    def test_service_stop_task(self) -> None:
        """windows_service_stop maps to win_service with state=stopped."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "windows_service_stop",
            {"service_name": "W3SVC"},
        )
        task, _ = _action_to_task(action)
        assert task["ansible.windows.win_service"]["state"] == "stopped"

    def test_service_configure_task(self) -> None:
        """windows_service_configure maps to win_service with start_mode."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "windows_service_configure",
            {"service_name": "W3SVC", "startup_type": "automatic"},
        )
        task, _ = _action_to_task(action)
        assert task["ansible.windows.win_service"]["start_mode"] == "auto"

    def test_service_configure_manual(self) -> None:
        """windows_service_configure with manual startup_type."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "windows_service_configure",
            {"service_name": "W3SVC", "startup_type": "manual"},
        )
        task, _ = _action_to_task(action)
        assert task["ansible.windows.win_service"]["start_mode"] == "manual"

    def test_service_configure_disabled(self) -> None:
        """windows_service_configure with disabled startup_type."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "windows_service_configure",
            {"service_name": "W3SVC", "startup_type": "disabled"},
        )
        task, _ = _action_to_task(action)
        assert task["ansible.windows.win_service"]["start_mode"] == "disabled"

    def test_service_configure_unknown_startup(self) -> None:
        """windows_service_configure with unknown startup_type defaults to auto."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "windows_service_configure",
            {"service_name": "W3SVC", "startup_type": "weird"},
        )
        task, _ = _action_to_task(action)
        assert task["ansible.windows.win_service"]["start_mode"] == "auto"

    def test_service_create_with_path(self) -> None:
        """windows_service_create with binary_path includes path in task."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "windows_service_create",
            {"service_name": "MySvc", "binary_path": "C:\\svc.exe"},
        )
        task, _ = _action_to_task(action)
        assert task["ansible.windows.win_service"]["path"] == "C:\\svc.exe"

    def test_service_create_without_path(self) -> None:
        """windows_service_create without binary_path omits path from task."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "windows_service_create",
            {"service_name": "MySvc"},
        )
        task, _ = _action_to_task(action)
        assert "path" not in task["ansible.windows.win_service"]

    def test_registry_set_task(self) -> None:
        """registry_set maps to win_regedit with correct path."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "registry_set",
            {
                "key": "HKLM:\\SOFTWARE\\MyApp",
                "name": "Version",
                "value": "1.0",
            },
        )
        task, _ = _action_to_task(action)
        assert "ansible.windows.win_regedit" in task
        assert task["ansible.windows.win_regedit"]["state"] == "present"

    def test_registry_create_key_task(self) -> None:
        """registry_create_key maps to win_regedit state=present."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "registry_create_key",
            {"key": "HKLM:\\SOFTWARE\\NewApp"},
        )
        task, _ = _action_to_task(action)
        assert task["ansible.windows.win_regedit"]["state"] == "present"

    def test_registry_remove_key_task(self) -> None:
        """registry_remove_key maps to win_regedit state=absent."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "registry_remove_key",
            {"key": "HKLM:\\SOFTWARE\\OldApp"},
        )
        task, _ = _action_to_task(action)
        assert task["ansible.windows.win_regedit"]["state"] == "absent"

    def test_file_copy_task(self) -> None:
        """file_copy maps to win_copy with src and dest."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "file_copy",
            {"src": "C:\\src\\file.txt", "dest": "C:\\dest\\"},
        )
        task, _ = _action_to_task(action)
        assert "ansible.windows.win_copy" in task
        assert task["ansible.windows.win_copy"]["src"] == "C:\\src\\file.txt"

    def test_directory_create_task(self) -> None:
        """directory_create maps to win_file with state=directory."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "directory_create",
            {"path": "C:\\MyApp\\Logs"},
        )
        task, _ = _action_to_task(action)
        assert "ansible.windows.win_file" in task
        assert task["ansible.windows.win_file"]["state"] == "directory"

    def test_file_remove_task(self) -> None:
        """file_remove maps to win_file with state=absent."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "file_remove",
            {"path": "C:\\temp\\old.txt"},
        )
        task, _ = _action_to_task(action)
        assert task["ansible.windows.win_file"]["state"] == "absent"

    def test_file_write_task(self) -> None:
        """file_write maps to win_copy with dest and content."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "file_write",
            {"path": "C:\\config.txt", "content": "hello world"},
        )
        task, _ = _action_to_task(action)
        assert "ansible.windows.win_copy" in task
        assert task["ansible.windows.win_copy"]["content"] == "hello world"

    def test_msi_install_task(self) -> None:
        """msi_install maps to win_package with state=present."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "msi_install",
            {"package_path": "C:\\packages\\app.msi"},
        )
        task, _ = _action_to_task(action)
        assert "ansible.windows.win_package" in task
        assert task["ansible.windows.win_package"]["state"] == "present"

    def test_chocolatey_install_task(self) -> None:
        """chocolatey_install maps to win_chocolatey with state=present."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "chocolatey_install",
            {"package_name": "git"},
        )
        task, _ = _action_to_task(action)
        assert "chocolatey.chocolatey.win_chocolatey" in task
        assert task["chocolatey.chocolatey.win_chocolatey"]["state"] == "present"

    def test_chocolatey_uninstall_task(self) -> None:
        """chocolatey_uninstall maps to win_chocolatey with state=absent."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "chocolatey_uninstall",
            {"package_name": "git"},
        )
        task, _ = _action_to_task(action)
        assert task["chocolatey.chocolatey.win_chocolatey"]["state"] == "absent"

    def test_win_shell_fallback_task(self) -> None:
        """win_shell action maps to win_shell task."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "win_shell",
            {"command": "Write-Host 'test'"},
            raw="Write-Host 'test'",
        )
        task, _ = _action_to_task(action)
        assert "ansible.windows.win_shell" in task

    def test_win_shell_low_confidence_produces_warning(self) -> None:
        """win_shell action with low confidence produces a warning."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "win_shell",
            {"command": "Write-Host 'test'"},
            raw="Write-Host 'test'",
            confidence="low",
        )
        _, warning = _action_to_task(action)
        assert len(warning) > 0
        assert "low" in warning.lower() or "review" in warning.lower()

    def test_requires_elevation_adds_become(self) -> None:
        """Actions requiring elevation get become=True in the task."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "windows_feature_install",
            {"feature_name": "Web-Server"},
            requires_elevation=True,
        )
        task, _ = _action_to_task(action)
        assert task.get("become") is True
        assert task.get("become_method") == "runas"
        assert task.get("become_user") == "SYSTEM"

    def test_unknown_action_type_uses_win_shell(self) -> None:
        """Unknown action type falls back to win_shell with a warning."""
        from souschef.converters.powershell import _action_to_task

        action = self._make_action(
            "totally_unknown_type",
            {},
            raw="some command",
        )
        task, warning = _action_to_task(action)
        assert "ansible.windows.win_shell" in task
        assert len(warning) > 0


class TestSplitRegistryKey:
    """Tests for _split_registry_key()."""

    def test_hklm_backslash_separator(self) -> None:
        """HKLM with backslash is split correctly."""
        from souschef.converters.powershell import _split_registry_key

        hive, subkey = _split_registry_key("HKLM:\\SOFTWARE\\Microsoft")
        assert hive == "HKLM"
        assert "SOFTWARE" in subkey

    def test_hkcu_backslash_separator(self) -> None:
        """HKCU with backslash is split correctly."""
        from souschef.converters.powershell import _split_registry_key

        hive, subkey = _split_registry_key("HKCU:\\Software\\App")
        assert hive == "HKCU"
        assert "Software" in subkey

    def test_hkey_local_machine_normalised(self) -> None:
        """HKEY_LOCAL_MACHINE is normalised to HKLM."""
        from souschef.converters.powershell import _split_registry_key

        hive, _ = _split_registry_key("HKEY_LOCAL_MACHINE:\\SOFTWARE")
        assert hive == "HKLM"

    def test_hkey_current_user_normalised(self) -> None:
        """HKEY_CURRENT_USER is normalised to HKCU."""
        from souschef.converters.powershell import _split_registry_key

        hive, _ = _split_registry_key("HKEY_CURRENT_USER:\\Software")
        assert hive == "HKCU"

    def test_hkey_classes_root_normalised(self) -> None:
        """HKEY_CLASSES_ROOT is normalised to HKCR."""
        from souschef.converters.powershell import _split_registry_key

        hive, _ = _split_registry_key("HKEY_CLASSES_ROOT\\CLSID")
        assert hive == "HKCR"

    def test_hkey_users_normalised(self) -> None:
        """HKEY_USERS is normalised to HKU."""
        from souschef.converters.powershell import _split_registry_key

        hive, _ = _split_registry_key("HKEY_USERS\\SID")
        assert hive == "HKU"

    def test_double_colon_separator(self) -> None:
        """:: separator is normalised to backslash."""
        from souschef.converters.powershell import _split_registry_key

        hive, subkey = _split_registry_key("HKLM::SOFTWARE::App")
        assert hive == "HKLM"
        assert "SOFTWARE" in subkey

    def test_forward_slash_separator(self) -> None:
        """Forward slash separator is normalised to backslash."""
        from souschef.converters.powershell import _split_registry_key

        hive, subkey = _split_registry_key("HKLM/SOFTWARE/App")
        assert hive == "HKLM"

    def test_key_without_subkey(self) -> None:
        """Key without subkey returns root subkey."""
        from souschef.converters.powershell import _split_registry_key

        hive, subkey = _split_registry_key("HKLM")
        assert hive == "HKLM"
        assert subkey == "\\"

    def test_unknown_hive_preserved(self) -> None:
        """Unknown hive names are preserved as-is."""
        from souschef.converters.powershell import _split_registry_key

        hive, _ = _split_registry_key("HKFOO:\\SOFTWARE")
        assert hive == "HKFOO"


class TestBuildPlaybook:
    """Tests for _build_playbook() and playbook structure."""

    def test_playbook_structure(self) -> None:
        """Generated playbook has correct Ansible play structure."""
        from souschef.converters.powershell import _build_playbook

        tasks = [{"name": "My task", "ansible.windows.win_shell": {"cmd": "test"}}]
        playbook = _build_playbook("my_play", "win_servers", tasks)

        assert isinstance(playbook, list)
        assert len(playbook) == 1
        play = playbook[0]
        assert play["name"] == "my_play"
        assert play["hosts"] == "win_servers"
        assert play["gather_facts"] is False
        assert play["tasks"] == tasks


class TestFullConversionIntegration:
    """Integration tests for end-to-end PowerShell to Ansible conversion."""

    def test_realistic_windows_server_setup(self) -> None:
        """A realistic Windows server setup script converts correctly."""
        from souschef.converters.powershell import convert_powershell_content_to_ansible

        content = """\
# Install IIS
Install-WindowsFeature -Name Web-Server -IncludeManagementTools
# Configure W3SVC
Set-Service -Name W3SVC -StartupType Automatic
Start-Service -Name W3SVC
# App directory
New-Item -Path C:\\inetpub\\myapp -ItemType Directory
# Install Node.js via Chocolatey
choco install nodejs
# Registry config
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\MyApp' -Name Enabled -Value 1
"""
        result = json.loads(
            convert_powershell_content_to_ansible(content, playbook_name="iis_setup")
        )
        assert result["status"] == "success"
        assert result["tasks_generated"] >= 6
        assert result["win_shell_fallbacks"] == 0
        # YAML should contain the module names
        playbook = result["playbook_yaml"]
        assert "win_feature" in playbook
        assert "win_service" in playbook
        assert "win_file" in playbook
        assert "win_chocolatey" in playbook
        assert "win_regedit" in playbook

    def test_parse_warnings_include_source_location(self) -> None:
        """Warnings reference the source line number."""
        from souschef.converters.powershell import convert_powershell_content_to_ansible

        result = json.loads(
            convert_powershell_content_to_ansible("Write-Host 'line1'\n")
        )
        assert any("Line 1" in w for w in result["warnings"])
