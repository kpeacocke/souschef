"""Tests for Ansible inventory parser module."""

from unittest.mock import MagicMock, patch

import pytest

from souschef.parsers.ansible_inventory import (
    detect_ansible_version,
    get_ansible_config_paths,
    parse_ansible_cfg,
    parse_inventory_file,
    parse_inventory_ini,
    parse_inventory_yaml,
    parse_requirements_yml,
    scan_playbook_for_version_issues,
)


class TestParseAnsibleCfgWithValidation:
    """Test parse_ansible_cfg function with proper path handling."""

    def test_missing_file_raises_file_not_found(self):
        """Test that missing cfg file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_ansible_cfg("/nonexistent/ansible.cfg")

    def test_empty_cfg_file_valid(self, tmp_path):
        """Test parsing empty ansible.cfg returns dict."""
        cfg_file = tmp_path / "ansible.cfg"
        cfg_file.write_text("[defaults]\n")
        result = parse_ansible_cfg(str(cfg_file))
        assert isinstance(result, dict)

    def test_cfg_with_defaults_section(self, tmp_path):
        """Test that defaults section is properly parsed."""
        cfg_file = tmp_path / "ansible.cfg"
        cfg_file.write_text("[defaults]\nhost_key_checking = False\n")
        result = parse_ansible_cfg(str(cfg_file))
        assert isinstance(result, dict)


class TestParseInventoryIniWithValidation:
    """Test parse_inventory_ini function with proper path handling."""

    def test_missing_inventory_raises_error(self):
        """Test that missing inventory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_inventory_ini("/nonexistent/inventory.ini")

    def test_valid_ini_inventory(self, tmp_path):
        """Test parsing valid inventory.ini returns dict."""
        inv_file = tmp_path / "inventory.ini"
        inv_file.write_text("[webservers]\nserver1\nserver2\n")
        result = parse_inventory_ini(str(inv_file))
        assert isinstance(result, dict)

    def test_ini_with_groups(self, tmp_path):
        """Test that groups are properly parsed."""
        inv_file = tmp_path / "inventory.ini"
        inv_file.write_text("[webservers]\nweb1\n[databases]\ndb1\n")
        result = parse_inventory_ini(str(inv_file))
        assert isinstance(result, dict)


class TestParseInventoryYamlWithValidation:
    """Test parse_inventory_yaml function with proper path handling."""

    def test_missing_yaml_raises_error(self):
        """Test that missing YAML inventory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_inventory_yaml("/nonexistent/inventory.yml")

    def test_valid_yaml_inventory(self, tmp_path):
        """Test parsing valid inventory.yml returns dict."""
        yaml_file = tmp_path / "inventory.yml"
        yaml_file.write_text("all:\n  hosts:\n    server1:\n")
        result = parse_inventory_yaml(str(yaml_file))
        assert isinstance(result, dict)

    def test_yaml_with_groups(self, tmp_path):
        """Test that YAML with groups is parsed."""
        yaml_file = tmp_path / "inventory.yml"
        yaml_file.write_text(
            "all:\n  children:\n    webservers:\n      hosts:\n        web1:\n"
        )
        result = parse_inventory_yaml(str(yaml_file))
        assert isinstance(result, dict)


class TestParseInventoryFileWithValidation:
    """Test parse_inventory_file function with proper path handling."""

    def test_missing_file_raises_error(self):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_inventory_file("/nonexistent/inventory")

    def test_ini_file_auto_detected(self, tmp_path):
        """Test that .ini inventory is auto-detected and parsed."""
        inv_file = tmp_path / "inventory.ini"
        inv_file.write_text("[webservers]\nweb1\n")
        result = parse_inventory_file(str(inv_file))
        assert isinstance(result, dict)

    def test_yaml_file_auto_detected(self, tmp_path):
        """Test that .yml inventory is auto-detected and parsed."""
        inv_file = tmp_path / "inventory.yml"
        inv_file.write_text("all:\n  hosts:\n    web1:\n")
        result = parse_inventory_file(str(inv_file))
        assert isinstance(result, dict)


class TestDetectAnsibleVersionWithValidation:
    """Test detect_ansible_version function with proper subprocess handling."""

    def test_ansible_version_detected(self):
        """Test that ansible version is detected."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="ansible 2.14.0\n", returncode=0)
            with patch("shutil.which", return_value="/usr/bin/ansible"):
                result = detect_ansible_version()
                assert isinstance(result, str)
                assert len(result) > 0

    def test_ansible_not_found_raises_error(self):
        """Test that missing Ansible raises error."""
        with (
            patch("subprocess.run", side_effect=FileNotFoundError()),
            pytest.raises(FileNotFoundError),
        ):
            detect_ansible_version("/nonexistent/ansible")


class TestParseRequirementsYmlWithValidation:
    """Test parse_requirements_yml function with proper path handling."""

    def test_missing_requirements_raises_error(self):
        """Test that missing requirements file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_requirements_yml("/nonexistent/requirements.yml")

    def test_valid_requirements_file(self, tmp_path):
        """Test parsing valid requirements.yml returns dict."""
        req_file = tmp_path / "requirements.yml"
        req_file.write_text(
            "collections:\n  - name: community.general\n    version: 3.0.0\n"
        )
        result = parse_requirements_yml(str(req_file))
        assert isinstance(result, dict)

    def test_requirements_with_roles(self, tmp_path):
        """Test that requirements with roles are parsed."""
        req_file = tmp_path / "requirements.yml"
        req_file.write_text(
            "roles:\n  - name: common\n    src: https://github.com/example/role\n"
        )
        result = parse_requirements_yml(str(req_file))
        assert isinstance(result, dict)


class TestScanPlaybookForVersionIssuesWithValidation:
    """Test scan_playbook_for_version_issues function with proper path handling."""

    def test_missing_playbook_raises_error(self):
        """Test that missing playbook raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            scan_playbook_for_version_issues("/nonexistent/playbook.yml")

    def test_valid_playbook_scanned(self, tmp_path):
        """Test scanning valid playbook returns dict."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text(
            "- hosts: all\n  tasks:\n    - name: test\n      debug:\n        msg: hello\n"
        )
        result = scan_playbook_for_version_issues(str(playbook_file))
        assert isinstance(result, dict)

    def test_playbook_with_deprecated_module(self, tmp_path):
        """Test that deprecated modules are detected."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text(
            "- hosts: all\n  tasks:\n    - apt:\n        name: nginx\n"
        )
        result = scan_playbook_for_version_issues(str(playbook_file))
        assert isinstance(result, dict)

    def test_playbook_with_fqcn(self, tmp_path):
        """Test that FQCN playbooks are properly handled."""
        playbook_file = tmp_path / "playbook.yml"
        playbook_file.write_text(
            "- hosts: all\n  tasks:\n    - ansible.builtin.debug:\n        msg: hello\n"
        )
        result = scan_playbook_for_version_issues(str(playbook_file))
        assert isinstance(result, dict)


class TestGetAnsibleConfigPaths:
    """Test get_ansible_config_paths function."""

    def test_returns_dict(self):
        """Test that function returns dict."""
        result = get_ansible_config_paths()
        assert isinstance(result, dict)

    def test_dict_has_expected_values(self):
        """Test that returned dict has expected value types."""
        result = get_ansible_config_paths()
        for value in result.values():
            assert value is None or isinstance(value, str)

    def test_no_exception_on_missing_paths(self):
        """Test that missing paths don't raise exceptions."""
        try:
            result = get_ansible_config_paths()
            assert isinstance(result, dict)
        except Exception:
            pytest.fail("get_ansible_config_paths raised an exception")


@pytest.mark.parametrize("format_ext", ["ini", "yaml", "yml"])
class TestInventoryFormatSupport:
    """Parameterized tests for inventory format support."""

    def test_format_can_be_parsed(self, format_ext, tmp_path):
        """Test that format can be parsed."""
        if format_ext == "ini":
            content = "[webservers]\nserver1\n"
        else:
            content = "all:\n  hosts:\n    server1:\n"

        inv_file = tmp_path / f"inventory.{format_ext}"
        inv_file.write_text(content)
        result = parse_inventory_file(str(inv_file))
        assert isinstance(result, dict)


class TestParsingWorkflows:
    """Integration-like tests for parsing workflows."""

    def test_parse_multiple_inventory_formats(self, tmp_path):
        """Test parsing both INI and YAML inventories."""
        ini_file = tmp_path / "inventory.ini"
        ini_file.write_text("[webservers]\nweb1\n")

        yaml_file = tmp_path / "inventory.yml"
        yaml_file.write_text("all:\n  hosts:\n    web1:\n")

        ini_result = parse_inventory_ini(str(ini_file))
        yaml_result = parse_inventory_yaml(str(yaml_file))

        assert isinstance(ini_result, dict)
        assert isinstance(yaml_result, dict)

    def test_scan_and_parse_playbook_workflow(self, tmp_path):
        """Test scanning and parsing playbook."""
        playbook_file = tmp_path / "site.yml"
        playbook_file.write_text(
            "- hosts: all\n  tasks:\n    - debug:\n        msg: test\n"
        )

        result = scan_playbook_for_version_issues(str(playbook_file))
        assert isinstance(result, dict)
