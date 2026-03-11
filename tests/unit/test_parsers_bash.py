"""Unit tests for the Bash script parser (souschef.parsers.bash)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from souschef.parsers.bash import (
    _extract_downloads,
    _extract_file_writes,
    _extract_idempotency_risks,
    _extract_packages,
    _extract_services,
    _format_parse_result,
    _identify_shell_fallbacks,
    _line_number,
    _parse_bash_content,
    _parse_package_names,
    parse_bash_script,
    parse_bash_script_content,
)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_SAMPLE_SCRIPT = """\
#!/bin/bash
apt-get install -y nginx python3
yum install -y httpd
dnf install -y vim
zypper install -y git
apk add curl
pip3 install gunicorn
curl -o /tmp/app.tar.gz https://example.com/app.tar.gz
wget -O /tmp/config.zip https://example.com/config.zip
cat <<EOF > /etc/nginx/app.conf
server {}
EOF
echo "KEY=value" > /etc/app/env
systemctl enable nginx
systemctl start nginx
service apache2 restart
custom-tool --flag value
"""


# ---------------------------------------------------------------------------
# _line_number
# ---------------------------------------------------------------------------


def test_line_number_first_line() -> None:
    """Returns 1 for an offset at the very start of content."""
    assert _line_number("abc", 0) == 1


def test_line_number_second_line() -> None:
    """Returns 2 for an offset on the second line."""
    content = "line1\nline2"
    assert _line_number(content, 6) == 2


def test_line_number_multiline() -> None:
    """Returns correct line for deeply nested offset."""
    content = "a\nb\nc\nd"
    # 'c' starts at index 4
    assert _line_number(content, 4) == 3


# ---------------------------------------------------------------------------
# _parse_package_names
# ---------------------------------------------------------------------------


def test_parse_package_names_apt() -> None:
    """Parses package names from an apt-get install command."""
    raw = "apt-get install -y nginx python3"
    result = _parse_package_names(raw, "apt")
    assert "nginx" in result
    assert "python3" in result


def test_parse_package_names_yum() -> None:
    """Parses package names from a yum install command."""
    raw = "yum install -y httpd"
    result = _parse_package_names(raw, "yum")
    assert "httpd" in result


def test_parse_package_names_pip() -> None:
    """Parses package names from a pip install command."""
    raw = "pip3 install gunicorn flask"
    result = _parse_package_names(raw, "pip")
    assert "gunicorn" in result
    assert "flask" in result


def test_parse_package_names_apk() -> None:
    """Parses package names from an apk add command."""
    raw = "apk add curl wget"
    result = _parse_package_names(raw, "apk")
    assert "curl" in result


def test_parse_package_names_no_packages() -> None:
    """Returns empty list when no package names follow the command."""
    raw = "apt-get install"
    result = _parse_package_names(raw, "apt")
    assert result == []


# ---------------------------------------------------------------------------
# _extract_packages
# ---------------------------------------------------------------------------


def test_extract_packages_apt() -> None:
    """Detects apt-get install commands."""
    content = "apt-get install -y nginx python3\n"
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_packages(content, result)
    assert len(result["packages"]) >= 1
    apt_pkgs = [p for p in result["packages"] if p["manager"] == "apt"]
    assert apt_pkgs
    assert "nginx" in apt_pkgs[0]["packages"]


def test_extract_packages_multiple_managers() -> None:
    """Detects multiple package managers in the same script."""
    content = "apt-get install nginx\nyum install httpd\ndnf install vim\n"
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_packages(content, result)
    managers = {p["manager"] for p in result["packages"]}
    assert "apt" in managers
    assert "yum" in managers
    assert "dnf" in managers


def test_extract_packages_confidence_high() -> None:
    """Packages with parsed names get high confidence."""
    content = "apt-get install -y nginx\n"
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_packages(content, result)
    assert result["packages"][0]["confidence"] >= 0.8


def test_extract_packages_empty_content() -> None:
    """Empty content results in no packages."""
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_packages("", result)
    assert result["packages"] == []


# ---------------------------------------------------------------------------
# _extract_services
# ---------------------------------------------------------------------------


def test_extract_services_systemctl() -> None:
    """Detects systemctl enable/start commands."""
    content = "systemctl enable nginx\nsystemctl start nginx\n"
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_services(content, result)
    assert len(result["services"]) == 2
    actions = {s["action"] for s in result["services"]}
    assert "enable" in actions
    assert "start" in actions


def test_extract_services_service_command() -> None:
    """Detects legacy service command."""
    content = "service apache2 restart\n"
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_services(content, result)
    assert len(result["services"]) == 1
    svc = result["services"][0]
    assert svc["name"] == "apache2"
    assert svc["action"] == "restart"


def test_extract_services_high_confidence() -> None:
    """Service entries have high confidence."""
    content = "systemctl stop nginx\n"
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_services(content, result)
    assert result["services"][0]["confidence"] >= 0.9


def test_extract_services_empty_content() -> None:
    """Empty content results in no services."""
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_services("", result)
    assert result["services"] == []


# ---------------------------------------------------------------------------
# _extract_file_writes
# ---------------------------------------------------------------------------


def test_extract_file_writes_heredoc() -> None:
    """Detects cat heredoc file writes."""
    content = "cat <<EOF > /etc/app.conf\nfoo\nEOF\n"
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_file_writes(content, result)
    assert any("/etc/app.conf" in fw["destination"] for fw in result["file_writes"])


def test_extract_file_writes_echo_redirect() -> None:
    """Detects echo redirect file writes."""
    content = 'echo "KEY=value" > /etc/app/env\n'
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_file_writes(content, result)
    assert len(result["file_writes"]) >= 1


def test_extract_file_writes_empty_content() -> None:
    """Empty content results in no file writes."""
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_file_writes("", result)
    assert result["file_writes"] == []


# ---------------------------------------------------------------------------
# _extract_downloads
# ---------------------------------------------------------------------------


def test_extract_downloads_curl() -> None:
    """Detects curl download commands."""
    content = "curl -o /tmp/app.tar.gz https://example.com/app.tar.gz\n"
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_downloads(content, result)
    assert len(result["downloads"]) >= 1
    assert result["downloads"][0]["tool"] == "curl"
    assert result["downloads"][0]["url"] == "https://example.com/app.tar.gz"


def test_extract_downloads_wget() -> None:
    """Detects wget download commands."""
    content = "wget -O /tmp/config.zip https://example.com/config.zip\n"
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_downloads(content, result)
    assert len(result["downloads"]) >= 1
    assert result["downloads"][0]["tool"] == "wget"


def test_extract_downloads_empty_content() -> None:
    """Empty content results in no downloads."""
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_downloads("", result)
    assert result["downloads"] == []


# ---------------------------------------------------------------------------
# _extract_idempotency_risks
# ---------------------------------------------------------------------------


def test_extract_idempotency_risks_package_install() -> None:
    """Detects unconditional package install risk."""
    content = "apt-get install nginx\n"
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_idempotency_risks(content, result)
    risk_types = {r["type"] for r in result["idempotency_risks"]}
    assert "unconditional_package_install" in risk_types


def test_extract_idempotency_risks_download() -> None:
    """Detects raw download risk."""
    content = "wget https://example.com/file.tgz\n"
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_idempotency_risks(content, result)
    risk_types = {r["type"] for r in result["idempotency_risks"]}
    assert "raw_download" in risk_types


def test_extract_idempotency_risks_empty_content() -> None:
    """Empty content results in no risks."""
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _extract_idempotency_risks("", result)
    assert result["idempotency_risks"] == []


# ---------------------------------------------------------------------------
# _identify_shell_fallbacks
# ---------------------------------------------------------------------------


def test_identify_shell_fallbacks_unknown_command() -> None:
    """Unknown commands are identified as shell fallbacks."""
    lines = ["custom-tool --flag value"]
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _identify_shell_fallbacks(lines, result)
    assert len(result["shell_fallbacks"]) == 1
    assert "ansible.builtin.shell" in result["shell_fallbacks"][0]["warning"]


def test_identify_shell_fallbacks_comment_skipped() -> None:
    """Comment lines are not flagged as fallbacks."""
    lines = ["# This is a comment"]
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _identify_shell_fallbacks(lines, result)
    assert result["shell_fallbacks"] == []


def test_identify_shell_fallbacks_empty_line_skipped() -> None:
    """Empty lines are not flagged as fallbacks."""
    lines = ["", "   "]
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _identify_shell_fallbacks(lines, result)
    assert result["shell_fallbacks"] == []


def test_identify_shell_fallbacks_known_commands_not_flagged() -> None:
    """Known commands (apt, systemctl, etc.) are not flagged as fallbacks."""
    lines = ["apt-get install nginx", "systemctl start nginx"]
    result: dict = {"packages": [], "services": [], "file_writes": [], "downloads": [], "idempotency_risks": [], "shell_fallbacks": [], "warnings": []}
    _identify_shell_fallbacks(lines, result)
    assert result["shell_fallbacks"] == []


# ---------------------------------------------------------------------------
# _parse_bash_content
# ---------------------------------------------------------------------------


def test_parse_bash_content_full_script() -> None:
    """Full sample script is parsed into all IR categories."""
    ir = _parse_bash_content(_SAMPLE_SCRIPT)
    assert ir["packages"]
    assert ir["services"]
    assert ir["file_writes"]
    assert ir["downloads"]


def test_parse_bash_content_returns_dict_structure() -> None:
    """parse_bash_content returns all expected keys."""
    ir = _parse_bash_content("echo hello")
    expected_keys = {
        "packages", "services", "file_writes", "downloads",
        "idempotency_risks", "shell_fallbacks", "warnings",
        "users", "groups", "file_perms", "git_ops", "archives",
        "sed_ops", "cron_jobs", "firewall_rules", "hostname_ops",
        "env_vars", "sensitive_data", "cm_escapes",
    }
    assert expected_keys == set(ir.keys())


def test_parse_bash_content_empty_script() -> None:
    """Empty script returns empty IR."""
    ir = _parse_bash_content("")
    assert ir["packages"] == []
    assert ir["services"] == []
    assert ir["file_writes"] == []
    assert ir["downloads"] == []


def test_parse_bash_content_truncates_large_input() -> None:
    """Very large content is handled without error."""
    large_content = "apt-get install nginx\n" * 30_000
    ir = parse_bash_script_content(large_content)
    assert isinstance(ir, dict)


# ---------------------------------------------------------------------------
# _format_parse_result
# ---------------------------------------------------------------------------


def test_format_parse_result_no_patterns() -> None:
    """Returns 'No provisioning patterns detected' for empty IR."""
    ir = _parse_bash_content("# just a comment\n")
    result = _format_parse_result(ir)
    assert "No provisioning patterns detected" in result


def test_format_parse_result_packages_section() -> None:
    """Includes Package Installs section when packages detected."""
    ir = _parse_bash_content("apt-get install -y nginx\n")
    result = _format_parse_result(ir)
    assert "Package Installs" in result


def test_format_parse_result_services_section() -> None:
    """Includes Service Control section when services detected."""
    ir = _parse_bash_content("systemctl start nginx\n")
    result = _format_parse_result(ir)
    assert "Service Control" in result


def test_format_parse_result_downloads_section() -> None:
    """Includes Downloads section when downloads detected."""
    ir = _parse_bash_content("curl -o /tmp/f.tgz https://example.com/f.tgz\n")
    result = _format_parse_result(ir)
    assert "Downloads" in result


def test_format_parse_result_idempotency_risks_section() -> None:
    """Includes Idempotency Risks section when risks detected."""
    ir = _parse_bash_content("apt-get install nginx\n")
    result = _format_parse_result(ir)
    assert "Idempotency Risks" in result


def test_format_parse_result_shell_fallbacks_section() -> None:
    """Includes Shell Fallbacks section when fallbacks detected."""
    ir = _parse_bash_content("some-unknown-command --flag\n")
    result = _format_parse_result(ir)
    assert "Shell Fallbacks" in result


# ---------------------------------------------------------------------------
# parse_bash_script_content (public API)
# ---------------------------------------------------------------------------


def test_parse_bash_script_content_returns_ir() -> None:
    """parse_bash_script_content returns structured IR dict."""
    ir = parse_bash_script_content("apt-get install nginx\n")
    assert "packages" in ir
    assert ir["packages"]


# ---------------------------------------------------------------------------
# parse_bash_script (file-path API)
# ---------------------------------------------------------------------------


def test_parse_bash_script_success(tmp_path: Path) -> None:
    """parse_bash_script reads and parses a real file."""
    script = tmp_path / "test.sh"
    script.write_text("apt-get install nginx\nsystemctl start nginx\n")
    with patch("souschef.parsers.bash._get_workspace_root", return_value=tmp_path):
        result = parse_bash_script(str(script))
    assert "Package Installs" in result
    assert "Service Control" in result


def test_parse_bash_script_file_not_found(tmp_path: Path) -> None:
    """parse_bash_script returns error for missing file."""
    missing = tmp_path / "missing.sh"
    with patch("souschef.parsers.bash._get_workspace_root", return_value=tmp_path):
        result = parse_bash_script(str(missing))
    assert "not found" in result.lower() or "error" in result.lower()


def test_parse_bash_script_is_directory(tmp_path: Path) -> None:
    """parse_bash_script returns error when path is a directory."""
    with patch("souschef.parsers.bash._get_workspace_root", return_value=tmp_path):
        result = parse_bash_script(str(tmp_path))
    assert "directory" in result.lower() or "error" in result.lower()


def test_parse_bash_script_permission_error(tmp_path: Path) -> None:
    """parse_bash_script returns error on permission denied."""
    script = tmp_path / "noperm.sh"
    script.write_text("apt-get install nginx\n")
    script.chmod(0o000)
    try:
        with patch("souschef.parsers.bash._get_workspace_root", return_value=tmp_path):
            result = parse_bash_script(str(script))
        assert "permission" in result.lower() or "error" in result.lower()
    finally:
        script.chmod(0o644)


def test_parse_bash_script_path_traversal_blocked(tmp_path: Path) -> None:
    """parse_bash_script blocks path traversal attempts."""
    outside = tmp_path.parent / "outside.sh"
    outside.write_text("malicious content")
    try:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        with patch("souschef.parsers.bash._get_workspace_root", return_value=workspace):
            result = parse_bash_script(str(outside))
        # Should return an error for path outside workspace
        assert "error" in result.lower() or "not found" in result.lower() or "outside" in result.lower()
    finally:
        if outside.exists():
            outside.unlink()


def test_parse_bash_script_value_error(tmp_path: Path) -> None:
    """parse_bash_script handles ValueError from path utilities."""
    with patch(
        "souschef.parsers.bash._normalize_path",
        side_effect=ValueError("bad path"),
    ):
        result = parse_bash_script("bad_path.sh")
    assert "error" in result.lower()
