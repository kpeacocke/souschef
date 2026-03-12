"""
Unit tests for the PowerShell to Ansible converter.

Tests cover:
- convert_powershell_script_to_ansible: single file conversion
- convert_powershell_directory_to_ansible: directory conversion
- convert_powershell_script_to_ansible_with_ai: AI-assisted conversion
- convert_powershell_directory_to_ansible_with_ai: AI directory conversion
- Per-cmdlet task builders
- generate_windows_ee_definition
- generate_aap_windows_credential_vars
- generate_windows_inventory_template
- Error handling paths
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from souschef.converters.powershell_to_ansible import (
    _build_construct_guidance,
    _build_debug_task,
    _build_fail_task,
    _build_unsupported_task,
    _build_win_copy_task,
    _build_win_dsc_task,
    _build_win_feature_task,
    _build_win_file_task,
    _build_win_firewall_task,
    _build_win_get_url_task,
    _build_win_group_task,
    _build_win_reboot_task,
    _build_win_regedit_task,
    _build_win_scheduled_task,
    _build_win_service_task,
    _build_win_shell_task,
    _build_win_updates_task,
    _build_win_user_task,
    _build_windows_play_header,
    _clean_ps_ai_response,
    _collect_directory_scripts,
    _convert_cmdlet_to_task,
    _convert_ps_with_ai,
    _convert_scripts_to_plays,
    _create_ps_ai_prompt,
    _format_directory_analysis,
    _format_unsupported_for_prompt,
    _generate_powershell_playbook,
    _parse_cmdlet_parameters,
    convert_powershell_directory_to_ansible,
    convert_powershell_directory_to_ansible_with_ai,
    convert_powershell_script_to_ansible,
    convert_powershell_script_to_ansible_with_ai,
    generate_aap_windows_credential_vars,
    generate_windows_ee_definition,
    generate_windows_inventory_template,
    get_powershell_ansible_module_map,
    get_supported_powershell_cmdlets,
)
from souschef.parsers.powershell import _parse_script_content

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_SCRIPT = """\
Install-WindowsFeature -Name Web-Server -IncludeManagementTools
Set-Service -Name W3SVC -StartupType Automatic
Start-Service -Name W3SVC
New-Item -ItemType Directory -Path "C:\\inetpub\\myapp"
New-NetFirewallRule -Name "HTTP" -LocalPort 80 -Protocol TCP -Action Allow
"""

COMPLEX_SCRIPT = """\
Import-Module WebAdministration
$SiteName = "MyApp"
Install-WindowsFeature -Name Web-Server
New-LocalUser -Name "svcaccount"
Set-ItemProperty -Path "HKLM:\\SOFTWARE\\MyApp" -Name "Version" -Value "1.0"
Register-ScheduledTask -TaskName "Backup" -TaskPath "\\"
New-NetFirewallRule -Name "HTTP" -LocalPort 80 -Protocol TCP -Action Allow
Restart-Computer -Force
Invoke-WebRequest -Uri "https://example.com/file.zip" -OutFile "C:\\tmp\\file.zip"
"""

UNSUPPORTED_SCRIPT = """\
$disks = Get-WmiObject -Class Win32_LogicalDisk
$ie = New-Object -ComObject InternetExplorer.Application
Configuration ServerConfig {
    Node localhost {}
}
"""


# ---------------------------------------------------------------------------
# Tests: _build_windows_play_header
# ---------------------------------------------------------------------------


def test_build_windows_play_header_hosts() -> None:
    """Test that play header targets windows."""
    play = _build_windows_play_header("setup.ps1")
    assert play["hosts"] == "windows"


def test_build_windows_play_header_winrm_vars() -> None:
    """Test that WinRM connection vars are set."""
    play = _build_windows_play_header("setup.ps1")
    assert play["vars"]["ansible_connection"] == "winrm"
    assert play["vars"]["ansible_winrm_transport"] == "ntlm"


def test_build_windows_play_header_name() -> None:
    """Test that play name includes the script name."""
    play = _build_windows_play_header("my_script.ps1")
    assert "my_script.ps1" in play["name"]


# ---------------------------------------------------------------------------
# Tests: per-cmdlet builders
# ---------------------------------------------------------------------------


def test_build_win_feature_task_install() -> None:
    """Test Windows feature install task."""
    task = _build_win_feature_task("Install-WindowsFeature", {"name": "IIS"})
    assert task["ansible.windows.win_feature"]["state"] == "present"
    assert task["ansible.windows.win_feature"]["name"] == "IIS"


def test_build_win_feature_task_remove() -> None:
    """Test Windows feature removal task."""
    task = _build_win_feature_task("Uninstall-WindowsFeature", {"name": "IIS"})
    assert task["ansible.windows.win_feature"]["state"] == "absent"


def test_build_win_service_task_start() -> None:
    """Test Windows service start task."""
    task = _build_win_service_task("Start-Service", {"name": "W3SVC"})
    assert task["ansible.windows.win_service"]["state"] == "started"


def test_build_win_service_task_stop() -> None:
    """Test Windows service stop task."""
    task = _build_win_service_task("Stop-Service", {"name": "W3SVC"})
    assert task["ansible.windows.win_service"]["state"] == "stopped"


def test_build_win_service_task_restart() -> None:
    """Test Windows service restart task."""
    task = _build_win_service_task("Restart-Service", {"name": "W3SVC"})
    assert task["ansible.windows.win_service"]["state"] == "restarted"


def test_build_win_service_task_with_startup_type() -> None:
    """Test that startup type is mapped correctly."""
    task = _build_win_service_task(
        "Set-Service", {"name": "W3SVC", "startuptype": "Automatic"}
    )
    assert task["ansible.windows.win_service"]["start_mode"] == "auto"


def test_build_win_service_task_remove() -> None:
    """Test Windows service removal task."""
    task = _build_win_service_task("Remove-Service", {"name": "W3SVC"})
    assert task["ansible.windows.win_service"]["state"] == "absent"


def test_build_win_file_task_new_directory() -> None:
    """Test New-Item for directories."""
    task = _build_win_file_task(
        "New-Item", {"path": "C:\\mydir", "itemtype": "Directory"}
    )
    assert task["ansible.windows.win_file"]["state"] == "directory"


def test_build_win_file_task_new_file() -> None:
    """Test New-Item for files."""
    task = _build_win_file_task("New-Item", {"path": "C:\\myfile", "itemtype": "File"})
    assert task["ansible.windows.win_file"]["state"] == "present"


def test_build_win_file_task_remove() -> None:
    """Test Remove-Item task."""
    task = _build_win_file_task("Remove-Item", {"path": "C:\\myfile"})
    assert task["ansible.windows.win_file"]["state"] == "absent"


def test_build_win_copy_task() -> None:
    """Test Copy-Item task."""
    task = _build_win_copy_task(
        "Copy-Item", {"path": "C:\\src", "destination": "C:\\dst"}
    )
    assert "ansible.windows.win_copy" in task
    assert task["ansible.windows.win_copy"]["src"] == "C:\\src"


def test_build_win_regedit_task_set() -> None:
    """Test Set-ItemProperty registry task."""
    task = _build_win_regedit_task(
        "Set-ItemProperty",
        {"path": "HKLM:\\SOFTWARE\\Test", "name": "Key", "value": "1"},
    )
    assert task["ansible.windows.win_regedit"]["state"] == "present"


def test_build_win_regedit_task_remove() -> None:
    """Test Remove-ItemProperty registry task."""
    task = _build_win_regedit_task(
        "Remove-ItemProperty",
        {"path": "HKLM:\\SOFTWARE\\Test", "name": "Key"},
    )
    assert task["ansible.windows.win_regedit"]["state"] == "absent"


def test_build_win_user_task_create() -> None:
    """Test New-LocalUser task."""
    task = _build_win_user_task("New-LocalUser", {"name": "bob"})
    assert task["ansible.windows.win_user"]["state"] == "present"
    assert task["ansible.windows.win_user"]["name"] == "bob"


def test_build_win_user_task_remove() -> None:
    """Test Remove-LocalUser task."""
    task = _build_win_user_task("Remove-LocalUser", {"name": "bob"})
    assert task["ansible.windows.win_user"]["state"] == "absent"


def test_build_win_user_task_with_password() -> None:
    """Test New-LocalUser task with password."""
    task = _build_win_user_task(
        "New-LocalUser", {"name": "svc", "password": "secret"}
    )
    assert task["ansible.windows.win_user"]["password"] == "secret"


def test_build_win_group_task_create() -> None:
    """Test New-LocalGroup task."""
    task = _build_win_group_task("New-LocalGroup", {"name": "admins"})
    assert task["ansible.windows.win_group"]["state"] == "present"


def test_build_win_group_task_remove() -> None:
    """Test Remove-LocalGroup task."""
    task = _build_win_group_task("Remove-LocalGroup", {"name": "admins"})
    assert task["ansible.windows.win_group"]["state"] == "absent"


def test_build_win_firewall_task_allow() -> None:
    """Test firewall rule allow task."""
    task = _build_win_firewall_task(
        "New-NetFirewallRule",
        {"name": "HTTP", "direction": "Inbound", "action": "Allow"},
    )
    assert task["community.windows.win_firewall_rule"]["state"] == "present"
    assert task["community.windows.win_firewall_rule"]["enabled"] is True


def test_build_win_firewall_task_remove() -> None:
    """Test firewall rule removal task."""
    task = _build_win_firewall_task("Remove-NetFirewallRule", {"name": "HTTP"})
    assert task["community.windows.win_firewall_rule"]["state"] == "absent"


def test_build_win_firewall_task_disable() -> None:
    """Test firewall rule disable task."""
    task = _build_win_firewall_task("Disable-NetFirewallRule", {"name": "HTTP"})
    assert task["community.windows.win_firewall_rule"]["enabled"] is False


def test_build_win_firewall_task_with_port() -> None:
    """Test that localport is included when provided."""
    task = _build_win_firewall_task(
        "New-NetFirewallRule", {"name": "HTTPS", "localport": "443"}
    )
    assert task["community.windows.win_firewall_rule"]["localport"] == "443"


def test_build_win_scheduled_task_register() -> None:
    """Test Register-ScheduledTask task."""
    task = _build_win_scheduled_task(
        "Register-ScheduledTask", {"taskname": "Backup"}
    )
    assert task["community.windows.win_scheduled_task"]["state"] == "present"


def test_build_win_scheduled_task_remove() -> None:
    """Test Unregister-ScheduledTask task."""
    task = _build_win_scheduled_task(
        "Unregister-ScheduledTask", {"taskname": "Backup"}
    )
    assert task["community.windows.win_scheduled_task"]["state"] == "absent"


def test_build_win_scheduled_task_disable() -> None:
    """Test Disable-ScheduledTask task."""
    task = _build_win_scheduled_task(
        "Disable-ScheduledTask", {"taskname": "Backup"}
    )
    assert task["community.windows.win_scheduled_task"]["enabled"] is False


def test_build_win_updates_task() -> None:
    """Test Windows Updates task."""
    task = _build_win_updates_task("Install-WindowsUpdate", {})
    assert "ansible.windows.win_updates" in task


def test_build_win_reboot_task() -> None:
    """Test Restart-Computer task."""
    task = _build_win_reboot_task("Restart-Computer", {})
    assert "ansible.windows.win_reboot" in task


def test_build_win_get_url_task() -> None:
    """Test Invoke-WebRequest download task."""
    task = _build_win_get_url_task(
        "Invoke-WebRequest", {"uri": "https://example.com/file.zip", "outfile": "C:\\tmp\\file.zip"}
    )
    assert "ansible.windows.win_get_url" in task
    assert task["ansible.windows.win_get_url"]["url"] == "https://example.com/file.zip"


def test_build_win_shell_task() -> None:
    """Test generic shell task builder."""
    task = _build_win_shell_task("Invoke-Expression", {"command": "dir"})
    assert "ansible.windows.win_shell" in task


def test_build_win_dsc_task() -> None:
    """Test DSC resource task builder."""
    task = _build_win_dsc_task(
        "Invoke-DscResource", {"name": "WindowsFeature", "modulename": "PSDesiredStateConfiguration"}
    )
    assert task["ansible.windows.win_dsc"]["resource_name"] == "WindowsFeature"


def test_build_debug_task() -> None:
    """Test Write-Host debug task builder."""
    task = _build_debug_task("Write-Host", {"object": "Hello World"})
    assert task["ansible.builtin.debug"]["msg"] == "Hello World"


def test_build_fail_task() -> None:
    """Test Write-Error fail task builder."""
    task = _build_fail_task("Write-Error", {"message": "Something failed"})
    assert "ansible.builtin.fail" in task


def test_build_unsupported_task() -> None:
    """Test unsupported cmdlet produces a WARNING shell task."""
    task = _build_unsupported_task("Unknown-Cmdlet", {})
    assert "WARNING" in task["name"]
    assert "ansible.windows.win_shell" in task


# ---------------------------------------------------------------------------
# Tests: _parse_cmdlet_parameters
# ---------------------------------------------------------------------------


def test_parse_cmdlet_parameters_named() -> None:
    """Test parsing named parameters."""
    params = _parse_cmdlet_parameters("-Name IIS -State Present")
    assert params.get("name") == "IIS"
    assert params.get("state") == "Present"


def test_parse_cmdlet_parameters_quoted_value() -> None:
    """Test parsing quoted parameter values."""
    params = _parse_cmdlet_parameters('-Path "C:\\Program Files\\App"')
    assert params.get("path") == "C:\\Program Files\\App"


def test_parse_cmdlet_parameters_empty() -> None:
    """Test parsing empty parameter string."""
    params = _parse_cmdlet_parameters("")
    assert params == {}


def test_parse_cmdlet_parameters_switch_only() -> None:
    """Test parsing switch parameters (no value)."""
    params = _parse_cmdlet_parameters("-Force")
    assert "force" in params


# ---------------------------------------------------------------------------
# Tests: _convert_cmdlet_to_task
# ---------------------------------------------------------------------------


def test_convert_cmdlet_to_task_known() -> None:
    """Test that known cmdlets are converted to specific module tasks."""
    cmdlet = {
        "name": "Install-WindowsFeature",
        "parameters_raw": "-Name IIS",
        "ansible_module": "ansible.windows.win_feature",
        "supported": True,
        "line": 1,
    }
    task = _convert_cmdlet_to_task(cmdlet)
    assert "ansible.windows.win_feature" in task


def test_convert_cmdlet_to_task_unknown() -> None:
    """Test that unknown cmdlets produce a WARNING shell task."""
    cmdlet = {
        "name": "Some-UnknownCmdlet",
        "parameters_raw": "-Arg value",
        "ansible_module": "ansible.windows.win_shell",
        "supported": False,
        "line": 1,
    }
    task = _convert_cmdlet_to_task(cmdlet)
    assert "ansible.windows.win_shell" in task


# ---------------------------------------------------------------------------
# Tests: _generate_powershell_playbook
# ---------------------------------------------------------------------------


def test_generate_powershell_playbook_is_valid_yaml(tmp_path: Path) -> None:
    """Test that the generated playbook is valid YAML."""
    parsed = _parse_script_content(SIMPLE_SCRIPT, "setup.ps1")
    result = _generate_powershell_playbook(parsed, "setup.ps1")
    data = yaml.safe_load(result)
    assert isinstance(data, list)
    assert data[0]["hosts"] == "windows"


def test_generate_powershell_playbook_empty_fallback() -> None:
    """Test that an empty script generates a fallback debug task."""
    parsed = _parse_script_content("", "empty.ps1")
    result = _generate_powershell_playbook(parsed, "empty.ps1")
    assert "No convertible cmdlets found" in result


def test_generate_powershell_playbook_contains_feature_task() -> None:
    """Test that the playbook contains a win_feature task from the script."""
    parsed = _parse_script_content(
        "Install-WindowsFeature -Name Web-Server", "setup.ps1"
    )
    result = _generate_powershell_playbook(parsed, "setup.ps1")
    assert "win_feature" in result


# ---------------------------------------------------------------------------
# Tests: convert_powershell_script_to_ansible (public API)
# ---------------------------------------------------------------------------


def test_convert_powershell_script_to_ansible_success(tmp_path: Path) -> None:
    """Test successful single-file conversion."""
    script = tmp_path / "setup.ps1"
    script.write_text(SIMPLE_SCRIPT, encoding="utf-8")
    result = convert_powershell_script_to_ansible(str(script))
    assert "hosts: windows" in result
    assert "win_feature" in result


def test_convert_powershell_script_to_ansible_file_not_found() -> None:
    """Test file-not-found error handling."""
    result = convert_powershell_script_to_ansible("/nonexistent/script.ps1")
    assert "Error" in result


def test_convert_powershell_script_to_ansible_is_directory(tmp_path: Path) -> None:
    """Test directory error handling."""
    result = convert_powershell_script_to_ansible(str(tmp_path))
    assert "Error" in result


def test_convert_powershell_script_to_ansible_permission_denied(tmp_path: Path) -> None:
    """Test permission error handling."""
    script = tmp_path / "locked.ps1"
    script.write_text("Install-WindowsFeature -Name IIS", encoding="utf-8")
    with patch(
        "souschef.converters.powershell_to_ansible.safe_read_text",
        side_effect=PermissionError("denied"),
    ):
        result = convert_powershell_script_to_ansible(str(script))
    assert "Error" in result


def test_convert_powershell_script_to_ansible_too_large(tmp_path: Path) -> None:
    """Test that oversized scripts return an error."""
    script = tmp_path / "big.ps1"
    script.write_text("x", encoding="utf-8")
    with patch(
        "souschef.converters.powershell_to_ansible.safe_read_text",
        return_value="x" * 2_000_001,
    ):
        result = convert_powershell_script_to_ansible(str(script))
    assert "Error" in result


def test_convert_powershell_script_to_ansible_value_error(tmp_path: Path) -> None:
    """Test that ValueError is caught."""
    script = tmp_path / "script.ps1"
    script.write_text("Set-Service -Name W3SVC", encoding="utf-8")
    with patch(
        "souschef.converters.powershell_to_ansible._normalize_path",
        side_effect=ValueError("bad"),
    ):
        result = convert_powershell_script_to_ansible(str(script))
    assert "Error" in result


def test_convert_powershell_script_to_ansible_generic_exception(tmp_path: Path) -> None:
    """Test that generic exceptions are caught."""
    script = tmp_path / "script.ps1"
    script.write_text("Set-Service -Name W3SVC", encoding="utf-8")
    with patch(
        "souschef.converters.powershell_to_ansible._parse_script_content",
        side_effect=RuntimeError("unexpected"),
    ):
        result = convert_powershell_script_to_ansible(str(script))
    assert "error occurred" in result.lower() or "Error" in result


# ---------------------------------------------------------------------------
# Tests: _convert_scripts_to_plays
# ---------------------------------------------------------------------------


def test_convert_scripts_to_plays_returns_list(tmp_path: Path) -> None:
    """Test that the helper returns a list of plays."""
    s1 = tmp_path / "a.ps1"
    s1.write_text("Install-WindowsFeature -Name IIS", encoding="utf-8")
    from souschef.core.path_utils import _get_workspace_root

    root = _get_workspace_root()
    plays = _convert_scripts_to_plays([s1], root)
    assert isinstance(plays, list)


def test_convert_scripts_to_plays_skips_unreadable(tmp_path: Path) -> None:
    """Test that unreadable scripts are skipped."""
    good = tmp_path / "good.ps1"
    bad = tmp_path / "bad.ps1"
    good.write_text("Install-WindowsFeature -Name IIS", encoding="utf-8")
    bad.write_text("Set-Service -Name W3SVC", encoding="utf-8")

    from souschef.core.path_utils import _get_workspace_root, safe_read_text

    root = _get_workspace_root()

    def _sel(path: Path, *args: object, **kwargs: object) -> str:
        if "bad" in str(path):
            raise OSError("cannot read")
        return safe_read_text(path, *args, **kwargs)

    with patch(
        "souschef.converters.powershell_to_ansible.safe_read_text",
        side_effect=_sel,
    ):
        plays = _convert_scripts_to_plays(sorted([good, bad]), root)
    assert len(plays) >= 1


# ---------------------------------------------------------------------------
# Tests: convert_powershell_directory_to_ansible (public API)
# ---------------------------------------------------------------------------


def test_convert_powershell_directory_to_ansible_success(tmp_path: Path) -> None:
    """Test successful directory conversion."""
    (tmp_path / "a.ps1").write_text(SIMPLE_SCRIPT, encoding="utf-8")
    result = convert_powershell_directory_to_ansible(str(tmp_path))
    assert "hosts: windows" in result


def test_convert_powershell_directory_to_ansible_no_scripts(tmp_path: Path) -> None:
    """Test warning when no scripts found."""
    result = convert_powershell_directory_to_ansible(str(tmp_path))
    assert "Warning" in result


def test_convert_powershell_directory_to_ansible_not_found() -> None:
    """Test error when directory not found."""
    result = convert_powershell_directory_to_ansible("/nonexistent/dir")
    assert "Error" in result


def test_convert_powershell_directory_to_ansible_not_a_dir(tmp_path: Path) -> None:
    """Test error when path is a file."""
    f = tmp_path / "script.ps1"
    f.write_text("x")
    result = convert_powershell_directory_to_ansible(str(f))
    assert "Error" in result


def test_convert_powershell_directory_to_ansible_no_tasks(tmp_path: Path) -> None:
    """Test warning when scripts have no convertible cmdlets."""
    (tmp_path / "empty.ps1").write_text("# just a comment\n", encoding="utf-8")
    result = convert_powershell_directory_to_ansible(str(tmp_path))
    assert "Warning" in result or "hosts: windows" in result


def test_convert_powershell_directory_to_ansible_permission_error(tmp_path: Path) -> None:
    """Test permission error handling for directory conversion."""
    with patch(
        "souschef.converters.powershell_to_ansible._normalize_path",
        side_effect=PermissionError("denied"),
    ):
        result = convert_powershell_directory_to_ansible(str(tmp_path))
    assert "Error" in result


def test_convert_powershell_directory_to_ansible_generic_exception(tmp_path: Path) -> None:
    """Test that unexpected exceptions in directory conversion are caught."""
    with patch(
        "souschef.converters.powershell_to_ansible._normalize_path",
        side_effect=RuntimeError("oops"),
    ):
        result = convert_powershell_directory_to_ansible(str(tmp_path))
    assert "error occurred" in result.lower() or "Error" in result


# ---------------------------------------------------------------------------
# Tests: AI-assisted conversion helpers
# ---------------------------------------------------------------------------


def test_clean_ps_ai_response_valid_playbook() -> None:
    """Test that a valid YAML playbook is returned unchanged."""
    response = "- name: play\n  hosts: windows\n  tasks: []\n"
    assert _clean_ps_ai_response(response) == response.strip()


def test_clean_ps_ai_response_strips_markdown_fences() -> None:
    """Test that markdown code fences are stripped."""
    response = "```yaml\n- name: play\n  hosts: windows\n  tasks: []\n```"
    result = _clean_ps_ai_response(response)
    assert "```" not in result
    assert result.startswith("- ")


def test_clean_ps_ai_response_empty_string() -> None:
    """Test that empty response returns an error."""
    result = _clean_ps_ai_response("")
    assert "Error" in result


def test_clean_ps_ai_response_invalid_yaml() -> None:
    """Test that non-YAML response returns an error."""
    result = _clean_ps_ai_response("This is just plain text with no YAML.")
    assert "Error" in result


def test_create_ps_ai_prompt_contains_script_name() -> None:
    """Test that the AI prompt includes the script name."""
    prompt = _create_ps_ai_prompt("$x=1", "analysis", [], "setup.ps1")
    assert "setup.ps1" in prompt


def test_create_ps_ai_prompt_truncates_long_content() -> None:
    """Test that very long content is truncated in the prompt."""
    long_content = "x" * 50_000
    prompt = _create_ps_ai_prompt(long_content, "analysis", [], "big.ps1")
    assert "[truncated]" in prompt


def test_create_ps_ai_prompt_includes_unsupported() -> None:
    """Test that unsupported constructs appear in the prompt."""
    unsupported = [
        {
            "construct": "WMI query",
            "text": "Get-WmiObject",
            "source_file": "test.ps1",
            "line": 1,
        }
    ]
    prompt = _create_ps_ai_prompt("$x=1", "analysis", unsupported, "test.ps1")
    assert "WMI query" in prompt


def test_create_ps_ai_prompt_yaml_only_instruction() -> None:
    """Test that the prompt instructs LLM to return YAML only."""
    prompt = _create_ps_ai_prompt("", "", [], "test.ps1")
    assert "YAML" in prompt


def test_format_unsupported_for_prompt_empty() -> None:
    """Test that empty unsupported list returns '(none)'."""
    result = _format_unsupported_for_prompt([])
    assert result == "(none)"


def test_format_unsupported_for_prompt_with_items() -> None:
    """Test that unsupported items are included in prompt."""
    items = [
        {
            "construct": "WMI query",
            "text": "Get-WmiObject",
            "source_file": "test.ps1",
            "line": 5,
        }
    ]
    result = _format_unsupported_for_prompt(items)
    assert "WMI query" in result


def test_build_construct_guidance_wmi() -> None:
    """Test that WMI guidance is generated."""
    unsupported = [
        {"construct": "WMI query", "text": "", "source_file": "f.ps1", "line": 1}
    ]
    guidance = _build_construct_guidance(unsupported)
    assert "Get-WmiObject" in guidance or "WMI" in guidance


def test_build_construct_guidance_com() -> None:
    """Test that COM object guidance is generated."""
    unsupported = [
        {
            "construct": "COM/CLR object instantiation",
            "text": "",
            "source_file": "f.ps1",
            "line": 1,
        }
    ]
    guidance = _build_construct_guidance(unsupported)
    assert "New-Object" in guidance or "COM" in guidance


def test_build_construct_guidance_dsc() -> None:
    """Test that DSC Configuration guidance is generated."""
    unsupported = [
        {
            "construct": "DSC Configuration block",
            "text": "",
            "source_file": "f.ps1",
            "line": 1,
        }
    ]
    guidance = _build_construct_guidance(unsupported)
    assert "win_dsc" in guidance or "DSC" in guidance


def test_build_construct_guidance_unknown_construct() -> None:
    """Test that unknown constructs produce generic guidance."""
    unsupported = [
        {
            "construct": "Some Unknown Thing",
            "text": "",
            "source_file": "f.ps1",
            "line": 1,
        }
    ]
    guidance = _build_construct_guidance(unsupported)
    assert "idempotent" in guidance.lower()


def test_format_directory_analysis_includes_path(tmp_path: Path) -> None:
    """Test that directory analysis includes the directory path."""
    collected = {"cmdlets": [], "unsupported": [], "content_parts": []}
    result = _format_directory_analysis(collected, str(tmp_path))
    assert str(tmp_path) in result


def test_format_directory_analysis_lists_unsupported(tmp_path: Path) -> None:
    """Test that directory analysis lists unsupported constructs."""
    collected = {
        "cmdlets": [],
        "unsupported": [
            {
                "construct": "WMI query",
                "text": "Get-WmiObject",
                "source_file": "test.ps1",
                "line": 1,
            }
        ],
        "content_parts": [],
    }
    result = _format_directory_analysis(collected, str(tmp_path))
    assert "WMI query" in result


def test_collect_directory_scripts_returns_dict(tmp_path: Path) -> None:
    """Test that _collect_directory_scripts returns the expected structure."""
    s = tmp_path / "a.ps1"
    s.write_text("Install-WindowsFeature -Name IIS", encoding="utf-8")
    from souschef.core.path_utils import _get_workspace_root

    root = _get_workspace_root()
    result = _collect_directory_scripts([s], root)
    assert "cmdlets" in result
    assert "unsupported" in result
    assert "content_parts" in result


def test_collect_directory_scripts_skips_unreadable(tmp_path: Path) -> None:
    """Test that unreadable scripts are skipped when collecting."""
    good = tmp_path / "good.ps1"
    bad = tmp_path / "bad.ps1"
    good.write_text("Install-WindowsFeature -Name IIS", encoding="utf-8")
    bad.write_text("Set-Service -Name W3SVC", encoding="utf-8")

    from souschef.core.path_utils import _get_workspace_root, safe_read_text

    root = _get_workspace_root()

    def _sel(path: Path, *args: object, **kwargs: object) -> str:
        if "bad" in str(path):
            raise OSError("cannot read")
        return safe_read_text(path, *args, **kwargs)

    with patch(
        "souschef.converters.powershell_to_ansible.safe_read_text",
        side_effect=_sel,
    ):
        result = _collect_directory_scripts(sorted([good, bad]), root)
    assert isinstance(result["cmdlets"], list)


def test_convert_ps_with_ai_client_error() -> None:
    """Test that AI client initialisation errors are surfaced."""
    with patch(
        "souschef.converters.playbook._initialize_ai_client",
        return_value="Error: Unsupported AI provider: bad",
    ):
        result = _convert_ps_with_ai(
            "", "", [], "x.ps1", "bad", "", "", 0.3, 4000, "", ""
        )
    assert "Error" in result


def test_convert_ps_with_ai_returns_playbook() -> None:
    """Test that AI conversion returns the cleaned playbook."""
    mock_client = MagicMock()
    ai_playbook = "- name: Converted\n  hosts: windows\n  tasks: []\n"
    with patch(
        "souschef.converters.playbook._initialize_ai_client",
        return_value=mock_client,
    ), patch(
        "souschef.converters.playbook._call_ai_api",
        return_value=ai_playbook,
    ):
        result = _convert_ps_with_ai(
            "Get-WmiObject -Class Win32_LogicalDisk",
            "analysis",
            [{"construct": "WMI query", "text": "", "source_file": "f.ps1", "line": 1}],
            "setup.ps1",
            "anthropic",
            "fake-key",
            "claude-3-5-sonnet-20241022",
            0.3,
            4000,
            "",
            "",
        )
    assert result.startswith("- ")


# ---------------------------------------------------------------------------
# Tests: convert_powershell_script_to_ansible_with_ai
# ---------------------------------------------------------------------------


def test_convert_script_with_ai_no_unsupported(tmp_path: Path) -> None:
    """Test AI conversion falls back to deterministic when no unsupported constructs."""
    script = tmp_path / "setup.ps1"
    script.write_text("Install-WindowsFeature -Name IIS", encoding="utf-8")
    result = convert_powershell_script_to_ansible_with_ai(str(script))
    # Should succeed without calling LLM
    assert "hosts: windows" in result


def test_convert_script_with_ai_is_directory(tmp_path: Path) -> None:
    """Test IsADirectoryError in AI script conversion."""
    with patch(
        "souschef.converters.powershell_to_ansible._get_workspace_root",
        side_effect=IsADirectoryError("is a dir"),
    ):
        result = convert_powershell_script_to_ansible_with_ai(str(tmp_path))
    assert "Error" in result


def test_convert_script_with_ai_file_not_found() -> None:
    """Test file-not-found in AI script conversion."""
    result = convert_powershell_script_to_ansible_with_ai("/nonexistent/script.ps1")
    assert "Error" in result


def test_convert_script_with_ai_value_error(tmp_path: Path) -> None:
    """Test ValueError in AI script conversion."""
    script = tmp_path / "s.ps1"
    script.write_text("Set-Service -Name W3SVC", encoding="utf-8")
    with patch(
        "souschef.converters.powershell_to_ansible._normalize_path",
        side_effect=ValueError("bad"),
    ):
        result = convert_powershell_script_to_ansible_with_ai(str(script))
    assert "Error" in result


def test_convert_script_with_ai_generic_exception(tmp_path: Path) -> None:
    """Test generic exception in AI script conversion."""
    script = tmp_path / "s.ps1"
    script.write_text("Set-Service -Name W3SVC", encoding="utf-8")
    with patch(
        "souschef.converters.powershell_to_ansible._parse_script_content",
        side_effect=RuntimeError("unexpected"),
    ):
        result = convert_powershell_script_to_ansible_with_ai(str(script))
    assert "error occurred" in result.lower() or "Error" in result


# ---------------------------------------------------------------------------
# Tests: convert_powershell_directory_to_ansible_with_ai
# ---------------------------------------------------------------------------


def test_convert_directory_with_ai_no_unsupported(tmp_path: Path) -> None:
    """Test AI directory conversion falls back to deterministic when clean."""
    (tmp_path / "a.ps1").write_text("Install-WindowsFeature -Name IIS", encoding="utf-8")
    result = convert_powershell_directory_to_ansible_with_ai(str(tmp_path))
    assert "hosts: windows" in result or "Warning" in result


def test_convert_directory_with_ai_not_found() -> None:
    """Test AI directory conversion with missing directory."""
    result = convert_powershell_directory_to_ansible_with_ai("/nonexistent/dir")
    assert "Error" in result


def test_convert_directory_with_ai_not_a_dir(tmp_path: Path) -> None:
    """Test AI directory conversion when path is a file."""
    f = tmp_path / "script.ps1"
    f.write_text("x")
    result = convert_powershell_directory_to_ansible_with_ai(str(f))
    assert "Error" in result


def test_convert_directory_with_ai_no_scripts(tmp_path: Path) -> None:
    """Test AI directory conversion with no scripts."""
    result = convert_powershell_directory_to_ansible_with_ai(str(tmp_path))
    assert "Warning" in result


def test_convert_directory_with_ai_value_error(tmp_path: Path) -> None:
    """Test ValueError in AI directory conversion."""
    with patch(
        "souschef.converters.powershell_to_ansible._normalize_path",
        side_effect=ValueError("bad"),
    ):
        result = convert_powershell_directory_to_ansible_with_ai(str(tmp_path))
    assert "Error" in result


def test_convert_directory_with_ai_generic_exception(tmp_path: Path) -> None:
    """Test generic exception in AI directory conversion."""
    with patch(
        "souschef.converters.powershell_to_ansible._normalize_path",
        side_effect=RuntimeError("oops"),
    ):
        result = convert_powershell_directory_to_ansible_with_ai(str(tmp_path))
    assert "error occurred" in result.lower() or "Error" in result


# ---------------------------------------------------------------------------
# Tests: Enterprise artefact generators
# ---------------------------------------------------------------------------


def test_generate_windows_ee_definition_valid_yaml() -> None:
    """Test that the EE definition is valid YAML."""
    result = generate_windows_ee_definition()
    yaml_part = "\n".join(
        line for line in result.splitlines() if not line.startswith("#")
    )
    data = yaml.safe_load(yaml_part)
    assert data["version"] == 3


def test_generate_windows_ee_definition_includes_pywinrm() -> None:
    """Test that the EE includes pywinrm."""
    result = generate_windows_ee_definition()
    assert "pywinrm" in result


def test_generate_windows_ee_definition_includes_win_collections() -> None:
    """Test that Windows collections are included in the EE."""
    result = generate_windows_ee_definition()
    assert "ansible.windows" in result
    assert "community.windows" in result


def test_generate_windows_ee_definition_custom_packages() -> None:
    """Test that extra packages are included."""
    result = generate_windows_ee_definition(python_packages=["pykerberos"])
    assert "pykerberos" in result


def test_generate_windows_ee_definition_custom_collections() -> None:
    """Test that extra collections are included."""
    result = generate_windows_ee_definition(
        galaxy_collections=["my.custom:>=1.0.0"]
    )
    assert "my.custom" in result


def test_generate_aap_windows_credential_vars_ntlm() -> None:
    """Test NTLM credential vars generation."""
    result = generate_aap_windows_credential_vars(transport="ntlm")
    assert "ntlm" in result
    assert "ansible_connection: winrm" in result


def test_generate_aap_windows_credential_vars_kerberos() -> None:
    """Test Kerberos credential vars include delegation flag."""
    result = generate_aap_windows_credential_vars(transport="kerberos")
    assert "kerberos" in result
    assert "kerberos_delegation" in result


def test_generate_aap_windows_credential_vars_https_port() -> None:
    """Test HTTPS scheme is set for port 5986."""
    result = generate_aap_windows_credential_vars(port=5986)
    assert "https" in result


def test_generate_aap_windows_credential_vars_no_cert_validation() -> None:
    """Test that cert validation can be disabled."""
    result = generate_aap_windows_credential_vars(validate_certs=False)
    assert "ignore" in result


def test_generate_windows_inventory_template_valid_yaml() -> None:
    """Test that the inventory template is valid YAML."""
    result = generate_windows_inventory_template(
        hosts=["server01", "server02"]
    )
    yaml_part = "\n".join(
        line for line in result.splitlines() if not line.startswith("#")
    )
    data = yaml.safe_load(yaml_part)
    assert "windows" in data


def test_generate_windows_inventory_template_custom_group() -> None:
    """Test custom group name in inventory template."""
    result = generate_windows_inventory_template(
        group_name="winservers"
    )
    assert "winservers" in result


def test_generate_windows_inventory_template_custom_hosts() -> None:
    """Test custom hosts in inventory template."""
    result = generate_windows_inventory_template(
        hosts=["dc01.example.com", "file01.example.com"]
    )
    assert "dc01.example.com" in result
    assert "file01.example.com" in result


def test_get_powershell_ansible_module_map() -> None:
    """Test that the module map is a non-empty dict."""
    m = get_powershell_ansible_module_map()
    assert isinstance(m, dict)
    assert len(m) > 0


def test_get_supported_powershell_cmdlets() -> None:
    """Test that supported cmdlets list is sorted."""
    cmdlets = get_supported_powershell_cmdlets()
    assert cmdlets == sorted(cmdlets)
    assert "install-windowsfeature" in cmdlets
