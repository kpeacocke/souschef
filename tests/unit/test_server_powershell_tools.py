"""
Unit tests for PowerShell MCP server tools.

Tests cover:
- parse_powershell_script MCP tool
- parse_powershell_directory MCP tool
- convert_powershell_script_to_ansible MCP tool
- convert_powershell_directory_to_ansible MCP tool
- convert_powershell_script_to_ansible_with_ai MCP tool
- convert_powershell_directory_to_ansible_with_ai MCP tool
- generate_windows_ee_definition MCP tool
- generate_aap_windows_credential_vars MCP tool
- generate_windows_inventory_template MCP tool
- list_powershell_supported_cmdlets MCP tool
"""

from pathlib import Path
from unittest.mock import patch

from souschef.server import (
    convert_powershell_directory_to_ansible,
    convert_powershell_directory_to_ansible_with_ai,
    convert_powershell_script_to_ansible,
    convert_powershell_script_to_ansible_with_ai,
    generate_aap_windows_credential_vars,
    generate_windows_ee_definition,
    generate_windows_inventory_template,
    list_powershell_supported_cmdlets,
    parse_powershell_directory,
    parse_powershell_script,
)

SIMPLE_SCRIPT = """\
Install-WindowsFeature -Name Web-Server -IncludeManagementTools
Start-Service -Name W3SVC
New-NetFirewallRule -Name "HTTP" -LocalPort 80 -Protocol TCP -Action Allow
"""


# ---------------------------------------------------------------------------
# Tests: parse_powershell_script
# ---------------------------------------------------------------------------


def test_server_parse_powershell_script_success(tmp_path: Path) -> None:
    """Test parse_powershell_script server tool delegates correctly."""
    script = tmp_path / "setup.ps1"
    script.write_text(SIMPLE_SCRIPT, encoding="utf-8")
    result = parse_powershell_script(str(script))
    assert "PowerShell Script Analysis" in result
    assert "Install-WindowsFeature" in result


def test_server_parse_powershell_script_error() -> None:
    """Test parse_powershell_script server tool returns error on missing file."""
    result = parse_powershell_script("/nonexistent/script.ps1")
    assert "Error" in result


# ---------------------------------------------------------------------------
# Tests: parse_powershell_directory
# ---------------------------------------------------------------------------


def test_server_parse_powershell_directory_success(tmp_path: Path) -> None:
    """Test parse_powershell_directory server tool delegates correctly."""
    (tmp_path / "a.ps1").write_text(SIMPLE_SCRIPT, encoding="utf-8")
    result = parse_powershell_directory(str(tmp_path))
    assert "PowerShell Script Analysis" in result


def test_server_parse_powershell_directory_no_scripts(tmp_path: Path) -> None:
    """Test parse_powershell_directory returns warning for empty directory."""
    result = parse_powershell_directory(str(tmp_path))
    assert "Warning" in result


# ---------------------------------------------------------------------------
# Tests: convert_powershell_script_to_ansible
# ---------------------------------------------------------------------------


def test_server_convert_script_success(tmp_path: Path) -> None:
    """Test convert_powershell_script_to_ansible server tool."""
    script = tmp_path / "setup.ps1"
    script.write_text(SIMPLE_SCRIPT, encoding="utf-8")
    result = convert_powershell_script_to_ansible(str(script))
    assert "hosts: windows" in result


def test_server_convert_script_error() -> None:
    """Test convert_powershell_script_to_ansible returns error on missing file."""
    result = convert_powershell_script_to_ansible("/nonexistent/script.ps1")
    assert "Error" in result


# ---------------------------------------------------------------------------
# Tests: convert_powershell_directory_to_ansible
# ---------------------------------------------------------------------------


def test_server_convert_directory_success(tmp_path: Path) -> None:
    """Test convert_powershell_directory_to_ansible server tool."""
    (tmp_path / "a.ps1").write_text(SIMPLE_SCRIPT, encoding="utf-8")
    result = convert_powershell_directory_to_ansible(str(tmp_path))
    assert "hosts: windows" in result


def test_server_convert_directory_no_scripts(tmp_path: Path) -> None:
    """Test convert_powershell_directory_to_ansible returns warning for empty dir."""
    result = convert_powershell_directory_to_ansible(str(tmp_path))
    assert "Warning" in result


# ---------------------------------------------------------------------------
# Tests: convert_powershell_script_to_ansible_with_ai
# ---------------------------------------------------------------------------


def test_server_convert_script_with_ai_no_unsupported(tmp_path: Path) -> None:
    """Test AI conversion falls back when no unsupported constructs."""
    script = tmp_path / "setup.ps1"
    script.write_text("Install-WindowsFeature -Name IIS", encoding="utf-8")
    result = convert_powershell_script_to_ansible_with_ai(str(script))
    assert "hosts: windows" in result


def test_server_convert_script_with_ai_passes_params(tmp_path: Path) -> None:
    """Test that AI conversion parameters are forwarded correctly."""
    script = tmp_path / "setup.ps1"
    script.write_text("Install-WindowsFeature -Name IIS", encoding="utf-8")

    with patch(
        "souschef.server._convert_ps_script_ai"
    ) as mock_fn:
        mock_fn.return_value = "- hosts: windows"
        result = convert_powershell_script_to_ansible_with_ai(
            str(script),
            ai_provider="openai",
            api_key="test-key",
            model="gpt-4o",
            temperature=0.5,
            max_tokens=2000,
        )
    mock_fn.assert_called_once()
    assert result == "- hosts: windows"


def test_server_convert_script_with_ai_error() -> None:
    """Test AI conversion returns error for missing file."""
    result = convert_powershell_script_to_ansible_with_ai("/nonexistent/script.ps1")
    assert "Error" in result


# ---------------------------------------------------------------------------
# Tests: convert_powershell_directory_to_ansible_with_ai
# ---------------------------------------------------------------------------


def test_server_convert_dir_with_ai_no_unsupported(tmp_path: Path) -> None:
    """Test AI directory conversion delegates correctly."""
    (tmp_path / "a.ps1").write_text(
        "Install-WindowsFeature -Name IIS", encoding="utf-8"
    )
    result = convert_powershell_directory_to_ansible_with_ai(str(tmp_path))
    assert "hosts: windows" in result or "Warning" in result


def test_server_convert_dir_with_ai_error() -> None:
    """Test AI directory conversion returns error for missing directory."""
    result = convert_powershell_directory_to_ansible_with_ai("/nonexistent/dir")
    assert "Error" in result


# ---------------------------------------------------------------------------
# Tests: generate_windows_ee_definition
# ---------------------------------------------------------------------------


def test_server_generate_windows_ee_definition_default() -> None:
    """Test default EE definition generation."""
    result = generate_windows_ee_definition()
    assert "ansible.windows" in result
    assert "pywinrm" in result


def test_server_generate_windows_ee_definition_extra_packages() -> None:
    """Test EE definition with extra Python packages."""
    result = generate_windows_ee_definition(
        ee_name="my-ee",
        python_packages="pykerberos,requests",
    )
    assert "pykerberos" in result
    assert "requests" in result


def test_server_generate_windows_ee_definition_extra_collections() -> None:
    """Test EE definition with extra Galaxy collections."""
    result = generate_windows_ee_definition(
        galaxy_collections="my.custom:>=1.0.0",
    )
    assert "my.custom" in result


# ---------------------------------------------------------------------------
# Tests: generate_aap_windows_credential_vars
# ---------------------------------------------------------------------------


def test_server_generate_aap_windows_credential_vars_default() -> None:
    """Test default credential vars generation."""
    result = generate_aap_windows_credential_vars()
    assert "ansible_connection: winrm" in result
    assert "ntlm" in result


def test_server_generate_aap_windows_credential_vars_kerberos() -> None:
    """Test Kerberos credential vars."""
    result = generate_aap_windows_credential_vars(transport="kerberos")
    assert "kerberos" in result


def test_server_generate_aap_windows_credential_vars_https() -> None:
    """Test HTTPS scheme for port 5986."""
    result = generate_aap_windows_credential_vars(port=5986)
    assert "https" in result


def test_server_generate_aap_windows_credential_vars_no_cert() -> None:
    """Test cert validation disabled."""
    result = generate_aap_windows_credential_vars(validate_certs=False)
    assert "ignore" in result


# ---------------------------------------------------------------------------
# Tests: generate_windows_inventory_template
# ---------------------------------------------------------------------------


def test_server_generate_windows_inventory_template_default() -> None:
    """Test default inventory template."""
    result = generate_windows_inventory_template()
    assert "windows" in result


def test_server_generate_windows_inventory_template_custom() -> None:
    """Test custom hosts and group in inventory template."""
    result = generate_windows_inventory_template(
        hosts="dc01,dc02",
        group_name="domain_controllers",
        transport="kerberos",
    )
    assert "dc01" in result
    assert "domain_controllers" in result
    assert "kerberos" in result


# ---------------------------------------------------------------------------
# Tests: list_powershell_supported_cmdlets
# ---------------------------------------------------------------------------


def test_server_list_powershell_supported_cmdlets() -> None:
    """Test that the cmdlet listing returns a formatted string."""
    result = list_powershell_supported_cmdlets()
    assert "install-windowsfeature" in result.lower()
    assert "win_feature" in result
    assert "Total:" in result
