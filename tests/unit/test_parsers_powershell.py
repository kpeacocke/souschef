"""
Unit tests for souschef/parsers/powershell.py.

Covers all public API functions, helper functions, edge cases,
error handling, and all action-type classifiers to achieve
100% line and branch coverage.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


class TestParsePowershellScript:
    """Tests for the parse_powershell_script() public API."""

    def test_parse_valid_script(self, tmp_path: Path) -> None:
        """parse_powershell_script returns JSON for a valid .ps1 file."""
        from souschef.parsers.powershell import parse_powershell_script

        script = tmp_path / "setup.ps1"
        script.write_text("Install-WindowsFeature -Name Web-Server\n", encoding="utf-8")

        result = json.loads(parse_powershell_script(str(script)))
        assert result["source"].endswith("setup.ps1")
        assert any(
            a["action_type"] == "windows_feature_install" for a in result["actions"]
        )

    def test_parse_nonexistent_file(self, tmp_path: Path) -> None:
        """parse_powershell_script returns an error for a missing file."""
        from souschef.parsers.powershell import parse_powershell_script

        result = parse_powershell_script(str(tmp_path / "missing.ps1"))
        assert "Error" in result or "not found" in result.lower()

    def test_parse_directory_path(self, tmp_path: Path) -> None:
        """parse_powershell_script returns an error when path is a directory."""
        from souschef.parsers.powershell import parse_powershell_script

        result = parse_powershell_script(str(tmp_path))
        assert "Error" in result or "directory" in result.lower()

    def test_parse_permission_error(self, tmp_path: Path) -> None:
        """parse_powershell_script handles PermissionError gracefully."""
        from souschef.parsers.powershell import parse_powershell_script

        script = tmp_path / "setup.ps1"
        script.write_text("Install-WindowsFeature -Name Web-Server\n", encoding="utf-8")

        with patch(
            "souschef.parsers.powershell.safe_read_text",
            side_effect=PermissionError("denied"),
        ):
            result = parse_powershell_script(str(script))
        assert "Error" in result or "denied" in result.lower() or "Permission" in result

    def test_parse_generic_exception(self, tmp_path: Path) -> None:
        """parse_powershell_script handles generic exceptions gracefully."""
        from souschef.parsers.powershell import parse_powershell_script

        script = tmp_path / "setup.ps1"
        script.write_text("Install-WindowsFeature -Name Web-Server\n", encoding="utf-8")

        with patch(
            "souschef.parsers.powershell._normalize_path",
            side_effect=RuntimeError("boom"),
        ):
            result = parse_powershell_script(str(script))
        assert "Error" in result


class TestParsePowershellContent:
    """Tests for parse_powershell_content() with inline string input."""

    def test_empty_content(self) -> None:
        """Empty content produces empty actions."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(parse_powershell_content(""))
        assert result["actions"] == []
        assert result["warnings"] == []

    def test_comment_lines_are_skipped(self) -> None:
        """Comment lines are not parsed as actions."""
        from souschef.parsers.powershell import parse_powershell_content

        content = "# This is a comment\n# Another comment\n"
        result = json.loads(parse_powershell_content(content))
        assert result["actions"] == []
        assert result["metrics"]["skipped_lines"] == 2

    def test_blank_lines_are_skipped(self) -> None:
        """Blank lines increment skipped_lines metric."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(parse_powershell_content("\n   \n\n"))
        assert result["metrics"]["skipped_lines"] == 3

    def test_custom_source_label(self) -> None:
        """Custom source label is reflected in output."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(parse_powershell_content("", source="my_script.ps1"))
        assert result["source"] == "my_script.ps1"

    def test_unrecognised_line_produces_win_shell_fallback(self) -> None:
        """Unrecognised lines produce win_shell fallback actions with warnings."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(parse_powershell_content("Write-Host 'Hello'"))
        assert any(a["action_type"] == "win_shell" for a in result["actions"])
        assert len(result["warnings"]) > 0
        assert result["metrics"]["win_shell_fallback"] == 1


class TestWindowsFeatureClassifier:
    """Tests for Windows feature install/remove patterns."""

    def test_install_windows_feature(self) -> None:
        """Install-WindowsFeature is classified correctly."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content("Install-WindowsFeature -Name Web-Server")
        )
        actions = result["actions"]
        assert len(actions) == 1
        assert actions[0]["action_type"] == "windows_feature_install"
        assert actions[0]["params"]["feature_name"] == "Web-Server"
        assert actions[0]["confidence"] == "high"

    def test_add_windows_feature_alias(self) -> None:
        """Add-WindowsFeature alias is also recognised."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(parse_powershell_content("Add-WindowsFeature Web-Server"))
        assert result["actions"][0]["action_type"] == "windows_feature_install"

    def test_enable_optional_feature(self) -> None:
        """Enable-WindowsOptionalFeature is classified correctly."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content(
                "Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServer"
            )
        )
        assert result["actions"][0]["action_type"] == "windows_optional_feature_enable"
        assert result["actions"][0]["params"]["feature_name"] == "IIS-WebServer"

    def test_remove_windows_feature(self) -> None:
        """Remove-WindowsFeature is classified correctly."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content("Remove-WindowsFeature -Name Web-Server")
        )
        assert result["actions"][0]["action_type"] == "windows_feature_remove"
        assert result["actions"][0]["params"]["feature_name"] == "Web-Server"

    def test_uninstall_windows_feature_alias(self) -> None:
        """Uninstall-WindowsFeature alias is also recognised."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content("Uninstall-WindowsFeature -Name Web-Server")
        )
        assert result["actions"][0]["action_type"] == "windows_feature_remove"

    def test_disable_optional_feature(self) -> None:
        """Disable-WindowsOptionalFeature is classified correctly."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content(
                "Disable-WindowsOptionalFeature -Online -FeatureName IIS-WebServer"
            )
        )
        assert result["actions"][0]["action_type"] == "windows_optional_feature_disable"
        assert result["actions"][0]["params"]["feature_name"] == "IIS-WebServer"

    def test_feature_install_requires_elevation(self) -> None:
        """Feature installs should require elevation."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content("Install-WindowsFeature -Name Web-Server")
        )
        assert result["actions"][0]["requires_elevation"] is True


class TestWindowsServiceClassifier:
    """Tests for Windows service management patterns."""

    def test_start_service(self) -> None:
        """Start-Service is classified correctly."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(parse_powershell_content("Start-Service -Name W3SVC"))
        assert result["actions"][0]["action_type"] == "windows_service_start"
        assert result["actions"][0]["params"]["service_name"] == "W3SVC"

    def test_stop_service(self) -> None:
        """Stop-Service is classified correctly."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(parse_powershell_content("Stop-Service -Name W3SVC"))
        assert result["actions"][0]["action_type"] == "windows_service_stop"
        assert result["actions"][0]["params"]["service_name"] == "W3SVC"

    def test_set_service_startup_type(self) -> None:
        """Set-Service with -StartupType is classified correctly."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content("Set-Service -Name Spooler -StartupType Automatic")
        )
        assert result["actions"][0]["action_type"] == "windows_service_configure"
        assert result["actions"][0]["params"]["service_name"] == "Spooler"
        assert result["actions"][0]["params"]["startup_type"] == "automatic"

    def test_set_service_manual_startup(self) -> None:
        """Set-Service with Manual startup type is classified correctly."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content("Set-Service -Name W3SVC -StartupType Manual")
        )
        assert result["actions"][0]["params"]["startup_type"] == "manual"

    def test_set_service_disabled_startup(self) -> None:
        """Set-Service with Disabled startup type is classified correctly."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content("Set-Service -Name W3SVC -StartupType Disabled")
        )
        assert result["actions"][0]["params"]["startup_type"] == "disabled"

    def test_new_service(self) -> None:
        """New-Service is classified correctly."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content(
                "New-Service -Name MyService -BinaryPathName C:\\svc\\svc.exe"
            )
        )
        assert result["actions"][0]["action_type"] == "windows_service_create"
        assert result["actions"][0]["params"]["service_name"] == "MyService"
        assert "binary_path" in result["actions"][0]["params"]

    def test_new_service_without_binary_path(self) -> None:
        """New-Service without -BinaryPathName still produces service_create action."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(parse_powershell_content("New-Service -Name MyService"))
        assert result["actions"][0]["action_type"] == "windows_service_create"
        assert "binary_path" not in result["actions"][0]["params"]


class TestRegistryClassifier:
    """Tests for Windows registry operation patterns."""

    def test_set_item_property_hklm(self) -> None:
        """Set-ItemProperty on HKLM is classified correctly."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content(
                "Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\MyApp' -Name Version -Value '1.0'"
            )
        )
        assert result["actions"][0]["action_type"] == "registry_set"
        assert "HKLM" in result["actions"][0]["params"]["key"]

    def test_new_item_registry_key(self) -> None:
        """New-Item on HKLM path is classified as registry_create_key."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content("New-Item -Path 'HKLM:\\SOFTWARE\\NewApp'")
        )
        assert result["actions"][0]["action_type"] == "registry_create_key"

    def test_remove_item_registry_key(self) -> None:
        """Remove-Item on HKLM path is classified as registry_remove_key."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content("Remove-Item -Path 'HKLM:\\SOFTWARE\\OldApp'")
        )
        assert result["actions"][0]["action_type"] == "registry_remove_key"

    def test_registry_requires_elevation_for_hklm(self) -> None:
        """HKLM registry operations should require elevation."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content("New-Item -Path 'HKLM:\\SOFTWARE\\NewApp'")
        )
        assert result["actions"][0]["requires_elevation"] is True


class TestFileClassifier:
    """Tests for file/directory operation patterns."""

    def test_copy_item(self) -> None:
        """Copy-Item is classified correctly."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content(
                "Copy-Item -Path C:\\src\\file.txt -Destination C:\\dest\\"
            )
        )
        assert result["actions"][0]["action_type"] == "file_copy"
        assert "src" in result["actions"][0]["params"]
        assert "dest" in result["actions"][0]["params"]

    def test_new_item_directory(self) -> None:
        """New-Item -ItemType Directory is classified as directory_create."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content(
                "New-Item -Path C:\\MyApp\\Logs -ItemType Directory"
            )
        )
        assert result["actions"][0]["action_type"] == "directory_create"
        assert result["actions"][0]["params"]["path"] == "C:\\MyApp\\Logs"

    def test_new_item_folder(self) -> None:
        """New-Item -ItemType Folder is also classified as directory_create."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content("New-Item -Path C:\\MyApp\\Data -ItemType Folder")
        )
        assert result["actions"][0]["action_type"] == "directory_create"

    def test_remove_item_file(self) -> None:
        """Remove-Item on a file path (not registry) is classified as file_remove."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content("Remove-Item -Path C:\\temp\\old.txt")
        )
        assert result["actions"][0]["action_type"] == "file_remove"
        assert result["actions"][0]["params"]["path"] == "C:\\temp\\old.txt"

    def test_set_content(self) -> None:
        """Set-Content is classified as file_write."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content(
                "Set-Content -Path C:\\config.txt -Value 'hello world'"
            )
        )
        assert result["actions"][0]["action_type"] == "file_write"
        assert result["actions"][0]["params"]["path"] == "C:\\config.txt"


class TestPackageClassifier:
    """Tests for MSI and Chocolatey package install/remove patterns."""

    def test_msi_install_via_msiexec(self) -> None:
        """Msiexec /i is classified as msi_install."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content("msiexec.exe /i C:\\packages\\app.msi /quiet")
        )
        assert result["actions"][0]["action_type"] == "msi_install"
        assert "app.msi" in result["actions"][0]["params"]["package_path"]

    def test_msi_install_via_start_process(self) -> None:
        """Start-Process msiexec is classified as msi_install."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content("Start-Process msiexec /i C:\\packages\\app.msi")
        )
        assert result["actions"][0]["action_type"] == "msi_install"

    def test_chocolatey_install_choco_command(self) -> None:
        """Choco install is classified as chocolatey_install."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(parse_powershell_content("choco install notepadplusplus"))
        assert result["actions"][0]["action_type"] == "chocolatey_install"
        assert result["actions"][0]["params"]["package_name"] == "notepadplusplus"

    def test_chocolatey_install_install_package(self) -> None:
        """Install-Package is classified as chocolatey_install."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(parse_powershell_content("Install-Package 'git'"))
        assert result["actions"][0]["action_type"] == "chocolatey_install"

    def test_chocolatey_uninstall(self) -> None:
        """Choco uninstall is classified as chocolatey_uninstall."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(parse_powershell_content("choco uninstall notepadplusplus"))
        assert result["actions"][0]["action_type"] == "chocolatey_uninstall"
        assert result["actions"][0]["params"]["package_name"] == "notepadplusplus"


class TestMetrics:
    """Tests for metrics counting."""

    def test_metrics_all_categories(self) -> None:
        """Metrics correctly count all action categories."""
        from souschef.parsers.powershell import parse_powershell_content

        content = "\n".join(
            [
                "Install-WindowsFeature -Name Web-Server",
                "Start-Service -Name W3SVC",
                "Set-ItemProperty -Path 'HKLM:\\SW\\App' -Name V -Value 1",
                "New-Item -Path C:\\logs -ItemType Directory",
                "choco install git",
                "Write-Host unknown",
            ]
        )
        result = json.loads(parse_powershell_content(content))
        m = result["metrics"]
        assert m["windows_feature"] == 1
        assert m["windows_service"] == 1
        assert m["registry"] == 1
        assert m["file"] == 1
        assert m["package"] == 1
        assert m["win_shell_fallback"] == 1

    def test_metrics_total_and_skipped_lines(self) -> None:
        """total_lines and skipped_lines are counted correctly."""
        from souschef.parsers.powershell import parse_powershell_content

        content = "# comment\n\nInstall-WindowsFeature -Name Web-Server\n"
        result = json.loads(parse_powershell_content(content))
        assert result["metrics"]["total_lines"] == 3
        assert result["metrics"]["skipped_lines"] == 2


class TestHelperFunctions:
    """Tests for internal helper functions."""

    def test_is_registry_path_hklm(self) -> None:
        """HKLM paths are identified as registry paths."""
        from souschef.parsers.powershell import _is_registry_path

        assert _is_registry_path("HKLM:\\SOFTWARE\\Microsoft") is True

    def test_is_registry_path_hkcu(self) -> None:
        """HKCU paths are identified as registry paths."""
        from souschef.parsers.powershell import _is_registry_path

        assert _is_registry_path("HKCU:\\Software\\App") is True

    def test_is_registry_path_hkey_local_machine(self) -> None:
        """HKEY_LOCAL_MACHINE paths are identified as registry paths."""
        from souschef.parsers.powershell import _is_registry_path

        assert _is_registry_path("HKEY_LOCAL_MACHINE:\\SOFTWARE") is True

    def test_is_registry_path_non_registry(self) -> None:
        """Non-registry paths return False."""
        from souschef.parsers.powershell import _is_registry_path

        assert _is_registry_path("C:\\Windows\\System32") is False
        assert _is_registry_path("D:\\temp\\file.txt") is False

    def test_make_action_structure(self) -> None:
        """_make_action returns correctly structured dict."""
        from souschef.parsers.powershell import _make_action

        action = _make_action(
            "windows_feature_install",
            {"feature_name": "Web-Server"},
            "Install-WindowsFeature -Name Web-Server",
            5,
        )
        assert action["action_type"] == "windows_feature_install"
        assert action["params"]["feature_name"] == "Web-Server"
        assert action["source_line"] == 5
        assert action["confidence"] == "high"
        assert "requires_elevation" in action

    def test_make_win_shell_fallback_structure(self) -> None:
        """_make_win_shell_fallback returns correctly structured dict."""
        from souschef.parsers.powershell import _make_win_shell_fallback

        action = _make_win_shell_fallback("Write-Host 'test'", 10)
        assert action["action_type"] == "win_shell"
        assert action["params"]["command"] == "Write-Host 'test'"
        assert action["confidence"] == "low"
        assert action["source_line"] == 10

    def test_increment_metric_known_types(self) -> None:
        """_increment_metric correctly increments known action type categories."""
        from souschef.parsers.powershell import _increment_metric

        metrics: dict = {
            "windows_feature": 0,
            "windows_service": 0,
            "registry": 0,
            "file": 0,
            "package": 0,
            "win_shell_fallback": 0,
        }
        _increment_metric(metrics, "windows_feature_install")
        assert metrics["windows_feature"] == 1
        _increment_metric(metrics, "windows_service_start")
        assert metrics["windows_service"] == 1
        _increment_metric(metrics, "registry_set")
        assert metrics["registry"] == 1
        _increment_metric(metrics, "file_copy")
        assert metrics["file"] == 1
        _increment_metric(metrics, "msi_install")
        assert metrics["package"] == 1
        _increment_metric(metrics, "win_shell")
        assert metrics["win_shell_fallback"] == 1

    def test_increment_metric_unknown_type_uses_fallback(self) -> None:
        """_increment_metric handles unknown action types gracefully."""
        from souschef.parsers.powershell import _increment_metric

        metrics: dict = {}
        _increment_metric(metrics, "totally_unknown_action")
        assert metrics.get("win_shell_fallback", 0) == 1

    def test_requires_elevation_for_feature_install(self) -> None:
        """Install-WindowsFeature requires elevation."""
        from souschef.parsers.powershell import _requires_elevation

        assert _requires_elevation("Install-WindowsFeature -Name Web-Server") is True

    def test_requires_elevation_for_hklm(self) -> None:
        """HKLM registry operations require elevation."""
        from souschef.parsers.powershell import _requires_elevation

        assert _requires_elevation("New-Item -Path HKLM:\\SOFTWARE\\App") is True

    def test_requires_elevation_for_normal_command(self) -> None:
        """Normal commands do not require elevation."""
        from souschef.parsers.powershell import _requires_elevation

        assert _requires_elevation("Start-Service -Name W3SVC") is False

    def test_classify_feature_line_none_for_unknown(self) -> None:
        """_classify_feature_line returns None for non-feature lines."""
        from souschef.parsers.powershell import _classify_feature_line

        assert _classify_feature_line("Start-Service -Name W3SVC", 1) is None

    def test_classify_service_line_none_for_unknown(self) -> None:
        """_classify_service_line returns None for non-service lines."""
        from souschef.parsers.powershell import _classify_service_line

        assert _classify_service_line("Install-WindowsFeature Web-Server", 1) is None

    def test_classify_registry_line_none_for_unknown(self) -> None:
        """_classify_registry_line returns None for non-registry lines."""
        from souschef.parsers.powershell import _classify_registry_line

        assert _classify_registry_line("Start-Service -Name W3SVC", 1) is None

    def test_classify_file_line_none_for_unknown(self) -> None:
        """_classify_file_line returns None for non-file lines."""
        from souschef.parsers.powershell import _classify_file_line

        assert _classify_file_line("Install-WindowsFeature Web-Server", 1) is None

    def test_classify_package_line_none_for_unknown(self) -> None:
        """_classify_package_line returns None for non-package lines."""
        from souschef.parsers.powershell import _classify_package_line

        assert _classify_package_line("Start-Service -Name W3SVC", 1) is None

    def test_classify_line_returns_none_for_unrecognised(self) -> None:
        """_classify_line returns None for unrecognised lines."""
        from souschef.parsers.powershell import _classify_line

        assert _classify_line("Write-Host 'Hello'", 1) is None

    def test_parse_script_from_path(self, tmp_path: Path) -> None:
        """_parse_script_from_path parses a file directly."""
        from souschef.parsers.powershell import _parse_script_from_path

        script = tmp_path / "setup.ps1"
        script.write_text("Start-Service -Name W3SVC\n", encoding="utf-8")

        result = _parse_script_from_path(script)
        assert any(
            a["action_type"] == "windows_service_start" for a in result["actions"]
        )

    def test_parse_powershell_content_internal(self) -> None:
        """_parse_powershell_content internal function works correctly."""
        from souschef.parsers.powershell import _parse_powershell_content

        result = _parse_powershell_content("Start-Service -Name W3SVC\n", "test.ps1")
        assert result["source"] == "test.ps1"
        assert any(
            a["action_type"] == "windows_service_start" for a in result["actions"]
        )


class TestMultiLineScript:
    """Integration-style tests for multi-action scripts."""

    def test_full_provisioning_script(self) -> None:
        """A realistic provisioning script is parsed correctly."""
        from souschef.parsers.powershell import parse_powershell_content

        content = """\
# Install IIS
Install-WindowsFeature -Name Web-Server -IncludeManagementTools
# Configure service
Set-Service -Name W3SVC -StartupType Automatic
Start-Service -Name W3SVC
# Registry settings
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\MyApp' -Name Version -Value '2.0'
# Create directory
New-Item -Path C:\\MyApp\\Logs -ItemType Directory
# Install Chocolatey package
choco install git
# Unknown command
Invoke-WebRequest -Uri https://example.com -OutFile C:\\temp\\file.zip
"""
        result = json.loads(parse_powershell_content(content))
        action_types = [a["action_type"] for a in result["actions"]]

        assert "windows_feature_install" in action_types
        assert "windows_service_configure" in action_types
        assert "windows_service_start" in action_types
        assert "registry_set" in action_types
        assert "directory_create" in action_types
        assert "chocolatey_install" in action_types
        assert "win_shell" in action_types  # Invoke-WebRequest falls back

    def test_all_feature_types_in_one_script(self) -> None:
        """All feature action types are classified in a single parse."""
        from souschef.parsers.powershell import parse_powershell_content

        content = "\n".join(
            [
                "Install-WindowsFeature -Name Web-Server",
                "Remove-WindowsFeature -Name Web-Server",
                "Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServer",
                "Disable-WindowsOptionalFeature -Online -FeatureName IIS-WebServer",
            ]
        )
        result = json.loads(parse_powershell_content(content))
        action_types = {a["action_type"] for a in result["actions"]}
        assert action_types == {
            "windows_feature_install",
            "windows_feature_remove",
            "windows_optional_feature_enable",
            "windows_optional_feature_disable",
        }

    def test_all_registry_types_in_one_script(self) -> None:
        """All registry action types are classified in a single parse."""
        from souschef.parsers.powershell import parse_powershell_content

        content = "\n".join(
            [
                "Set-ItemProperty -Path 'HKLM:\\SW\\App' -Name V -Value 1",
                "New-Item -Path 'HKLM:\\SW\\NewKey'",
                "Remove-Item -Path 'HKLM:\\SW\\OldKey'",
            ]
        )
        result = json.loads(parse_powershell_content(content))
        action_types = {a["action_type"] for a in result["actions"]}
        assert "registry_set" in action_types
        assert "registry_create_key" in action_types
        assert "registry_remove_key" in action_types

    def test_remove_item_file_not_confused_with_registry(self) -> None:
        """Remove-Item on a file path is NOT classified as registry_remove_key."""
        from souschef.parsers.powershell import parse_powershell_content

        result = json.loads(
            parse_powershell_content("Remove-Item -Path C:\\temp\\old.log")
        )
        assert result["actions"][0]["action_type"] == "file_remove"

    def test_new_item_file_path_not_registry(self) -> None:
        """New-Item on a file path without -ItemType is a win_shell fallback."""
        from souschef.parsers.powershell import parse_powershell_content

        # Without -ItemType Directory, and without HKLM path -> unrecognised
        result = json.loads(
            parse_powershell_content("New-Item -Path C:\\temp\\newfile.txt")
        )
        # Should be a win_shell fallback as it doesn't match directory or registry
        assert result["actions"][0]["action_type"] == "win_shell"
