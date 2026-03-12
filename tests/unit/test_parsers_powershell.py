"""
Unit tests for the PowerShell script parser.

Tests cover:
- parse_powershell_script: single file parsing
- parse_powershell_directory: directory parsing
- Cmdlet extraction (Install-WindowsFeature, Set-Service, etc.)
- Function and variable extraction
- Module import detection
- Unsupported construct detection (.NET, WMI, COM, DSC)
- Error handling (file not found, directory, permission errors)
- Helper functions
"""

from pathlib import Path
from unittest.mock import patch

from souschef.core.path_utils import safe_read_text
from souschef.parsers.powershell import (
    _build_line_index,
    _detect_unsupported_constructs,
    _extract_cmdlets,
    _extract_functions,
    _extract_module_imports,
    _extract_variables,
    _format_cmdlets_section,
    _format_script_results,
    _format_unsupported_section,
    _get_line_number,
    _parse_script_content,
    _strip_comments,
    get_powershell_ansible_module_map,
    get_supported_powershell_cmdlets,
    parse_powershell_directory,
    parse_powershell_script,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_SCRIPT = """\
# Install IIS
Install-WindowsFeature -Name Web-Server -IncludeManagementTools

# Configure service
Set-Service -Name W3SVC -StartupType Automatic
Start-Service -Name W3SVC

# Create directory
New-Item -ItemType Directory -Path "C:\\inetpub\\wwwroot\\myapp"

# Firewall rule
New-NetFirewallRule -Name "HTTP" -LocalPort 80 -Protocol TCP -Action Allow
"""

COMPLEX_SCRIPT = """\
Import-Module WebAdministration
#Requires -Modules PSDesiredStateConfiguration

$SiteName = "MyApp"
$Port = 8080

function Set-AppPool {
    param([string]$Name)
    New-WebAppPool -Name $Name
}

Install-WindowsFeature -Name Web-Server
New-LocalUser -Name "svcaccount" -Password (ConvertTo-SecureString "P@ss1" -AsPlainText -Force)
Set-ItemProperty -Path "HKLM:\\SOFTWARE\\MyApp" -Name "Version" -Value "1.0"
Register-ScheduledTask -TaskName "Backup" -TaskPath "\\"
"""

UNSUPPORTED_SCRIPT = """\
# WMI usage
$disks = Get-WmiObject -Class Win32_LogicalDisk
$svc = Get-CimInstance -ClassName Win32_Service

# COM object
$ie = New-Object -ComObject InternetExplorer.Application

# .NET type
Add-Type -AssemblyName System.Windows.Forms

# DSC
Configuration ServerConfig {
    Import-DscResource -ModuleName PSDesiredStateConfiguration
    Node localhost {
        WindowsFeature IIS {
            Ensure = "Present"
            Name = "Web-Server"
        }
    }
}
"""


# ---------------------------------------------------------------------------
# Tests: _strip_comments
# ---------------------------------------------------------------------------


def test_strip_comments_removes_single_line() -> None:
    """Test that single-line comments are removed."""
    content = "# This is a comment\nInstall-WindowsFeature -Name IIS"
    result = _strip_comments(content)
    assert "This is a comment" not in result
    assert "Install-WindowsFeature" in result


def test_strip_comments_removes_block_comments() -> None:
    """Test that block comments (<# ... #>) are removed."""
    content = "<# block comment\n  spanning lines\n#>\nSet-Service -Name W3SVC"
    result = _strip_comments(content)
    assert "block comment" not in result
    assert "Set-Service" in result


def test_strip_comments_preserves_line_count() -> None:
    """Test that stripping block comments preserves line count."""
    content = "<# line1\nline2\nline3\n#>\nactual code"
    result = _strip_comments(content)
    assert result.count("\n") == content.count("\n")


# ---------------------------------------------------------------------------
# Tests: _build_line_index and _get_line_number
# ---------------------------------------------------------------------------


def test_build_line_index_single_line() -> None:
    """Test line index with a single line."""
    idx = _build_line_index("hello")
    assert idx == [0]


def test_build_line_index_multiple_lines() -> None:
    """Test line index with multiple lines."""
    idx = _build_line_index("a\nb\nc")
    assert idx == [0, 2, 4]


def test_get_line_number_first_line() -> None:
    """Test line number retrieval for characters on the first line."""
    idx = _build_line_index("abc\ndef\nghi")
    assert _get_line_number(0, idx) == 1
    assert _get_line_number(2, idx) == 1


def test_get_line_number_second_line() -> None:
    """Test line number retrieval for characters on the second line."""
    idx = _build_line_index("abc\ndef\nghi")
    assert _get_line_number(4, idx) == 2


def test_get_line_number_last_line() -> None:
    """Test line number retrieval for the last line."""
    idx = _build_line_index("abc\ndef\nghi")
    assert _get_line_number(8, idx) == 3


# ---------------------------------------------------------------------------
# Tests: _extract_cmdlets
# ---------------------------------------------------------------------------


def test_extract_cmdlets_finds_install_windowsfeature() -> None:
    """Test that Install-WindowsFeature is extracted."""
    stripped = _strip_comments(SIMPLE_SCRIPT)
    cmdlets = _extract_cmdlets(stripped, "test.ps1")
    names = [c["name"].lower() for c in cmdlets]
    assert "install-windowsfeature" in names


def test_extract_cmdlets_maps_ansible_module() -> None:
    """Test that cmdlets are mapped to the correct Ansible module."""
    stripped = _strip_comments("Install-WindowsFeature -Name IIS")
    cmdlets = _extract_cmdlets(stripped, "test.ps1")
    assert any(c["ansible_module"] == "ansible.windows.win_feature" for c in cmdlets)


def test_extract_cmdlets_marks_supported_flag() -> None:
    """Test that known cmdlets are marked supported."""
    stripped = _strip_comments("Set-Service -Name W3SVC -StartupType Automatic")
    cmdlets = _extract_cmdlets(stripped, "test.ps1")
    assert any(c["supported"] is True for c in cmdlets)


def test_extract_cmdlets_marks_unknown_as_unsupported() -> None:
    """Test that unknown cmdlets are marked as needing manual review."""
    stripped = _strip_comments("Invoke-SomeThing -Arg value")
    cmdlets = _extract_cmdlets(stripped, "test.ps1")
    # SomeThing is not in the map so supported should be False
    assert all(c["supported"] is False for c in cmdlets)


def test_extract_cmdlets_includes_line_number() -> None:
    """Test that extracted cmdlets include a line number."""
    stripped = _strip_comments("line1\nInstall-WindowsFeature -Name IIS")
    cmdlets = _extract_cmdlets(stripped, "test.ps1")
    iis_cmdlets = [c for c in cmdlets if c["name"].lower() == "install-windowsfeature"]
    assert iis_cmdlets
    assert iis_cmdlets[0]["line"] == 2


def test_extract_cmdlets_deduplicates_same_line() -> None:
    """Test that the same cmdlet on the same line is not duplicated."""
    stripped = _strip_comments("Install-WindowsFeature -Name IIS")
    cmdlets = _extract_cmdlets(stripped, "test.ps1")
    count = sum(1 for c in cmdlets if c["name"].lower() == "install-windowsfeature")
    assert count == 1


# ---------------------------------------------------------------------------
# Tests: _extract_functions
# ---------------------------------------------------------------------------


def test_extract_functions_finds_function() -> None:
    """Test that function definitions are extracted."""
    stripped = _strip_comments(COMPLEX_SCRIPT)
    functions = _extract_functions(stripped, "test.ps1")
    names = [f["name"].lower() for f in functions]
    assert "set-apppool" in names


def test_extract_functions_empty_script() -> None:
    """Test that no functions are found in a script with none."""
    functions = _extract_functions("Install-WindowsFeature -Name IIS", "test.ps1")
    assert functions == []


# ---------------------------------------------------------------------------
# Tests: _extract_variables
# ---------------------------------------------------------------------------


def test_extract_variables_finds_assignment() -> None:
    """Test that top-level variable assignments are extracted."""
    stripped = _strip_comments(COMPLEX_SCRIPT)
    variables = _extract_variables(stripped, "test.ps1")
    names = [v["name"] for v in variables]
    assert "$SiteName" in names or "$sitename" in names


def test_extract_variables_deduplicates() -> None:
    """Test that repeated variable names are not duplicated."""
    content = "$Foo = 1\n$Bar = 2\n$Foo = 3"
    variables = _extract_variables(content, "test.ps1")
    names = [v["name"].lower() for v in variables]
    assert names.count("$foo") == 1


# ---------------------------------------------------------------------------
# Tests: _extract_module_imports
# ---------------------------------------------------------------------------


def test_extract_module_imports_finds_import_module() -> None:
    """Test that Import-Module statements are detected."""
    stripped = _strip_comments(COMPLEX_SCRIPT)
    modules = _extract_module_imports(stripped, "test.ps1")
    names = [m["name"].lower() for m in modules]
    assert "webadministration" in names


def test_extract_module_imports_finds_requires() -> None:
    """Test that #Requires -Modules directives are detected."""
    # Strip doesn't remove #Requires as it's meaningful
    content = "#Requires -Modules PSDesiredStateConfiguration"
    modules = _extract_module_imports(content, "test.ps1")
    names = [m["name"].lower() for m in modules]
    assert "psdesiredstateconfiguration" in names


# ---------------------------------------------------------------------------
# Tests: _detect_unsupported_constructs
# ---------------------------------------------------------------------------


def test_detect_unsupported_detects_wmi() -> None:
    """Test that WMI queries are flagged as unsupported."""
    unsupported = _detect_unsupported_constructs(UNSUPPORTED_SCRIPT, "test.ps1")
    constructs = [u["construct"] for u in unsupported]
    assert "WMI query" in constructs


def test_detect_unsupported_detects_cim() -> None:
    """Test that CIM queries are flagged."""
    unsupported = _detect_unsupported_constructs(UNSUPPORTED_SCRIPT, "test.ps1")
    constructs = [u["construct"] for u in unsupported]
    assert "CIM/WMI query" in constructs


def test_detect_unsupported_detects_new_object() -> None:
    """Test that COM/CLR object instantiation is flagged."""
    unsupported = _detect_unsupported_constructs(UNSUPPORTED_SCRIPT, "test.ps1")
    constructs = [u["construct"] for u in unsupported]
    assert "COM/CLR object instantiation" in constructs


def test_detect_unsupported_detects_add_type() -> None:
    """Test that Add-Type (inline .NET) is flagged."""
    unsupported = _detect_unsupported_constructs(UNSUPPORTED_SCRIPT, "test.ps1")
    constructs = [u["construct"] for u in unsupported]
    assert "Inline .NET type compilation" in constructs


def test_detect_unsupported_detects_dsc_configuration() -> None:
    """Test that DSC Configuration blocks are flagged."""
    unsupported = _detect_unsupported_constructs(UNSUPPORTED_SCRIPT, "test.ps1")
    constructs = [u["construct"] for u in unsupported]
    assert "DSC Configuration block" in constructs


def test_detect_unsupported_clean_script() -> None:
    """Test that a clean script has no unsupported constructs."""
    unsupported = _detect_unsupported_constructs(SIMPLE_SCRIPT, "test.ps1")
    assert unsupported == []


def test_detect_unsupported_ps_remoting() -> None:
    """Test that PS remoting sessions are flagged."""
    script = "Enter-PSSession -ComputerName server01"
    unsupported = _detect_unsupported_constructs(script, "test.ps1")
    constructs = [u["construct"] for u in unsupported]
    assert "PS remoting session" in constructs


def test_detect_unsupported_using_scope() -> None:
    """Test that $using: references are flagged."""
    script = "Invoke-Command { $using:MyVar }"
    unsupported = _detect_unsupported_constructs(script, "test.ps1")
    constructs = [u["construct"] for u in unsupported]
    assert "Cross-scope variable ($using:)" in constructs


# ---------------------------------------------------------------------------
# Tests: _parse_script_content
# ---------------------------------------------------------------------------


def test_parse_script_content_keys() -> None:
    """Test that _parse_script_content returns all expected keys."""
    result = _parse_script_content(SIMPLE_SCRIPT, "test.ps1")
    assert "cmdlets" in result
    assert "functions" in result
    assert "variables" in result
    assert "modules" in result
    assert "unsupported" in result


def test_parse_script_content_limits_cmdlets() -> None:
    """Test that cmdlets list is capped at MAX_CMDLETS."""
    from souschef.parsers.powershell import MAX_CMDLETS

    lines = ["Set-Service -Name svc" + str(i) for i in range(MAX_CMDLETS + 100)]
    big_script = "\n".join(lines)
    result = _parse_script_content(big_script, "test.ps1")
    assert len(result["cmdlets"]) <= MAX_CMDLETS


# ---------------------------------------------------------------------------
# Tests: formatting helpers
# ---------------------------------------------------------------------------


def test_format_cmdlets_section_supported_and_unsupported() -> None:
    """Test that _format_cmdlets_section returns both lists correctly."""
    cmdlets = [
        {
            "name": "Install-WindowsFeature",
            "ansible_module": "ansible.windows.win_feature",
            "supported": True,
            "line": 1,
        },
        {
            "name": "Unknown-Cmdlet",
            "ansible_module": "ansible.windows.win_shell",
            "supported": False,
            "line": 2,
        },
    ]
    parts: list[str] = []
    supported, unsupported = _format_cmdlets_section(parts, cmdlets)
    assert len(supported) == 1
    assert len(unsupported) == 1
    assert any("Install-WindowsFeature" in p for p in parts)


def test_format_cmdlets_section_empty() -> None:
    """Test _format_cmdlets_section with no cmdlets."""
    parts: list[str] = []
    supported, unsupported = _format_cmdlets_section(parts, [])
    assert supported == []
    assert unsupported == []
    assert any("none detected" in p for p in parts)


def test_format_cmdlets_section_truncates_at_50() -> None:
    """Test that _format_cmdlets_section shows at most 50 cmdlets."""
    cmdlets = [
        {
            "name": f"Set-Something{i}",
            "ansible_module": "ansible.windows.win_shell",
            "supported": False,
            "line": i,
        }
        for i in range(60)
    ]
    parts: list[str] = []
    _format_cmdlets_section(parts, cmdlets)
    assert any("and 10 more" in p for p in parts)


def test_format_unsupported_section_no_unsupported() -> None:
    """Test _format_unsupported_section with no unsupported constructs."""
    parts: list[str] = []
    _format_unsupported_section(parts, [])
    assert any("none detected" in p for p in parts)


def test_format_unsupported_section_with_items() -> None:
    """Test _format_unsupported_section with unsupported constructs."""
    unsupported = [
        {
            "construct": "WMI query",
            "text": "Get-WmiObject",
            "source_file": "test.ps1",
            "line": 3,
        }
    ]
    parts: list[str] = []
    _format_unsupported_section(parts, unsupported)
    assert any("WMI query" in p for p in parts)


def test_format_script_results_summary_section() -> None:
    """Test that _format_script_results includes a summary section."""
    result = _format_script_results(
        _parse_script_content(SIMPLE_SCRIPT, "test.ps1"), "test.ps1"
    )
    assert "Summary:" in result
    assert "Cmdlets:" in result


def test_format_script_results_unsupported_note() -> None:
    """Test that _format_script_results adds a NOTE when unsupported present."""
    result = _format_script_results(
        _parse_script_content(UNSUPPORTED_SCRIPT, "test.ps1"), "test.ps1"
    )
    assert "NOTE:" in result or "Unsupported" in result


def test_format_script_results_no_unsupported_no_note() -> None:
    """Test that _format_script_results has no NOTE for clean scripts."""
    result = _format_script_results(
        _parse_script_content(SIMPLE_SCRIPT, "test.ps1"), "test.ps1"
    )
    assert "NOTE: Review unsupported constructs" not in result


# ---------------------------------------------------------------------------
# Tests: parse_powershell_script (public API)
# ---------------------------------------------------------------------------


def test_parse_powershell_script_success(tmp_path: Path) -> None:
    """Test successful parsing of a PowerShell script file."""
    script = tmp_path / "setup.ps1"
    script.write_text(SIMPLE_SCRIPT, encoding="utf-8")
    result = parse_powershell_script(str(script))
    assert "PowerShell Script Analysis" in result
    assert "Install-WindowsFeature" in result


def test_parse_powershell_script_file_not_found() -> None:
    """Test that a missing file returns an error message."""
    result = parse_powershell_script("/nonexistent/path/script.ps1")
    assert "Error" in result


def test_parse_powershell_script_is_directory(tmp_path: Path) -> None:
    """Test that passing a directory returns an error message."""
    result = parse_powershell_script(str(tmp_path))
    assert "Error" in result


def test_parse_powershell_script_permission_denied(tmp_path: Path) -> None:
    """Test that a permission error returns an error message."""
    script = tmp_path / "locked.ps1"
    script.write_text("Set-Service -Name W3SVC", encoding="utf-8")
    with patch(
        "souschef.parsers.powershell.safe_read_text",
        side_effect=PermissionError("denied"),
    ):
        result = parse_powershell_script(str(script))
    assert "Error" in result


def test_parse_powershell_script_too_large(tmp_path: Path) -> None:
    """Test that an oversized script returns an error message."""
    script = tmp_path / "big.ps1"
    script.write_text("x", encoding="utf-8")
    with patch(
        "souschef.parsers.powershell.safe_read_text",
        return_value="x" * (2_000_001),
    ):
        result = parse_powershell_script(str(script))
    assert "Error" in result


def test_parse_powershell_script_general_exception(tmp_path: Path) -> None:
    """Test that unexpected exceptions are caught gracefully."""
    script = tmp_path / "script.ps1"
    script.write_text("Set-Service -Name W3SVC", encoding="utf-8")
    with patch(
        "souschef.parsers.powershell._parse_script_content",
        side_effect=RuntimeError("unexpected"),
    ):
        result = parse_powershell_script(str(script))
    assert "error occurred" in result.lower() or "Error" in result


def test_parse_powershell_script_value_error(tmp_path: Path) -> None:
    """Test that ValueError is caught and returned as error string."""
    script = tmp_path / "script.ps1"
    script.write_text("Set-Service -Name W3SVC", encoding="utf-8")
    with patch(
        "souschef.parsers.powershell._normalize_path",
        side_effect=ValueError("bad path"),
    ):
        result = parse_powershell_script(str(script))
    assert "Error" in result


# ---------------------------------------------------------------------------
# Tests: parse_powershell_directory (public API)
# ---------------------------------------------------------------------------


def test_parse_powershell_directory_success(tmp_path: Path) -> None:
    """Test successful parsing of a directory of scripts."""
    (tmp_path / "a.ps1").write_text(SIMPLE_SCRIPT, encoding="utf-8")
    (tmp_path / "b.ps1").write_text(COMPLEX_SCRIPT, encoding="utf-8")
    result = parse_powershell_directory(str(tmp_path))
    assert "PowerShell Script Analysis" in result


def test_parse_powershell_directory_no_scripts(tmp_path: Path) -> None:
    """Test that a directory with no scripts returns a warning."""
    result = parse_powershell_directory(str(tmp_path))
    assert "Warning" in result


def test_parse_powershell_directory_not_found() -> None:
    """Test that a missing directory returns an error message."""
    result = parse_powershell_directory("/nonexistent/dir")
    assert "Error" in result


def test_parse_powershell_directory_not_a_dir(tmp_path: Path) -> None:
    """Test that passing a file returns an error message."""
    f = tmp_path / "file.ps1"
    f.write_text("x")
    result = parse_powershell_directory(str(f))
    assert "Error" in result


def test_parse_powershell_directory_skips_unreadable(tmp_path: Path) -> None:
    """Test that unreadable files are skipped gracefully."""
    good = tmp_path / "good.ps1"
    bad = tmp_path / "bad.ps1"
    good.write_text("Install-WindowsFeature -Name IIS", encoding="utf-8")
    bad.write_text("Set-Service -Name W3SVC", encoding="utf-8")

    def _selective(path: Path, *args: object, **kwargs: object) -> str:
        if "bad" in str(path):
            raise OSError("cannot read")
        return safe_read_text(path, *args, **kwargs)

    with patch(
        "souschef.parsers.powershell.safe_read_text",
        side_effect=_selective,
    ):
        result = parse_powershell_directory(str(tmp_path))
    assert "Install-WindowsFeature" in result


def test_parse_powershell_directory_permission_denied(tmp_path: Path) -> None:
    """Test that a permission error on the directory returns an error."""
    with patch(
        "souschef.parsers.powershell._normalize_path",
        side_effect=PermissionError("denied"),
    ):
        result = parse_powershell_directory(str(tmp_path))
    assert "Error" in result


def test_parse_powershell_directory_general_exception(tmp_path: Path) -> None:
    """Test that unexpected exceptions in directory parsing are caught."""
    with patch(
        "souschef.parsers.powershell._normalize_path",
        side_effect=RuntimeError("oops"),
    ):
        result = parse_powershell_directory(str(tmp_path))
    assert "error occurred" in result.lower() or "Error" in result


# ---------------------------------------------------------------------------
# Tests: get_powershell_ansible_module_map / get_supported_powershell_cmdlets
# ---------------------------------------------------------------------------


def test_get_powershell_ansible_module_map_returns_dict() -> None:
    """Test that the module map is a non-empty dictionary."""
    m = get_powershell_ansible_module_map()
    assert isinstance(m, dict)
    assert len(m) > 0


def test_get_powershell_ansible_module_map_contains_win_feature() -> None:
    """Test that Install-WindowsFeature maps to win_feature."""
    m = get_powershell_ansible_module_map()
    assert m.get("install-windowsfeature") == "ansible.windows.win_feature"


def test_get_supported_powershell_cmdlets_returns_sorted_list() -> None:
    """Test that the cmdlet list is a sorted list of strings."""
    cmdlets = get_supported_powershell_cmdlets()
    assert isinstance(cmdlets, list)
    assert cmdlets == sorted(cmdlets)
    assert "install-windowsfeature" in cmdlets
