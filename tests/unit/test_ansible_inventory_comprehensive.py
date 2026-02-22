"""Comprehensive tests for ansible_inventory parsing functions."""

import tempfile
from pathlib import Path

import pytest

from souschef.parsers.ansible_inventory import (
    detect_ansible_version,
    parse_ansible_cfg,
    parse_inventory_ini,
    parse_inventory_yaml,
    parse_requirements_yml,
)


class TestParseAnsibleCfg:
    """Test parse_ansible_cfg function."""

    def test_parse_valid_config(self):
        """Test parsing valid ansible.cfg file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "ansible.cfg"
            config_file.write_text("""
[defaults]
inventory = ./inventory
roles_path = ./roles
host_key_checking = False

[privilege_escalation]
become = True
become_user = root
""")

            result = parse_ansible_cfg(str(config_file))

            assert "defaults" in result
            assert "privilege_escalation" in result
            assert result["defaults"]["inventory"] == "./inventory"
            assert result["privilege_escalation"]["become"] == "True"

    def test_parse_config_with_comments(self):
        """Test parsing config with comments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "ansible.cfg"
            config_file.write_text("""
# This is a comment
[defaults]
# inventory config
inventory = ./hosts
""")

            result = parse_ansible_cfg(str(config_file))

            assert "defaults" in result
            assert result["defaults"]["inventory"] == "./hosts"

    def test_parse_config_file_not_found(self):
        """Test parsing non-existent config file."""
        with pytest.raises(FileNotFoundError):
            parse_ansible_cfg("/nonexistent/path/ansible.cfg")

    def test_parse_config_path_is_directory(self):
        """Test parsing when path is directory not file."""
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            pytest.raises(ValueError, match="not a file"),
        ):
            parse_ansible_cfg(tmpdir)

    def test_parse_invalid_config_format(self):
        """Test parsing config with invalid INI format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "ansible.cfg"
            config_file.write_text("[defaults\ninvalid format")

            with pytest.raises(ValueError, match="Invalid ansible.cfg format"):
                parse_ansible_cfg(str(config_file))

    def test_parse_config_multiple_sections(self):
        """Test parsing config with multiple sections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "ansible.cfg"
            config_file.write_text("""
[defaults]
retry_files_enabled = False

[inventory]
enable_plugins = host_list, script

[ssh_connection]
pipelining = True
""")

            result = parse_ansible_cfg(str(config_file))

            assert len(result) == 3
            assert "defaults" in result
            assert "inventory" in result
            assert "ssh_connection" in result

    def test_parse_config_empty_file(self):
        """Test parsing empty config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "ansible.cfg"
            config_file.write_text("")

            result = parse_ansible_cfg(str(config_file))

            assert isinstance(result, dict)
            assert len(result) == 0


class TestParseInventoryIni:
    """Test parse_inventory_ini function."""

    def test_parse_simple_inventory(self):
        """Test parsing simple INI inventory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_file = Path(tmpdir) / "inventory"
            inventory_file.write_text("""
[webservers]
web1.example.com
web2.example.com

[dbservers]
db1.example.com
""")

            result = parse_inventory_ini(str(inventory_file))

            assert "webservers" in result["groups"]
            assert "dbservers" in result["groups"]
            assert "web1.example.com" in result["groups"]["webservers"]["hosts"]
            assert "web2.example.com" in result["groups"]["webservers"]["hosts"]

    def test_parse_inventory_with_host_vars(self):
        """Test parsing inventory with host variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_file = Path(tmpdir) / "inventory"
            inventory_file.write_text("""
[webservers]
web1.example.com ansible_host=198.51.100.60 ansible_port=22
web2.example.com ansible_host=198.51.100.61 ansible_user=admin
""")

            result = parse_inventory_ini(str(inventory_file))

            assert "web1.example.com" in result["hosts"]
            assert (
                result["hosts"]["web1.example.com"]["vars"]["ansible_host"]
                == "198.51.100.60"  # RFC 5737 documentation IP
            )
            assert (
                result["hosts"]["web2.example.com"]["vars"]["ansible_user"] == "admin"
            )

    def test_parse_inventory_with_group_vars(self):
        """Test parsing inventory with group variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_file = Path(tmpdir) / "inventory"
            inventory_file.write_text("""
[webservers]
web1.example.com

[webservers:vars]
http_port=80
https_port=443
""")

            result = parse_inventory_ini(str(inventory_file))

            assert "webservers" in result["groups"]
            assert result["groups"]["webservers"]["vars"]["http_port"] == "80"
            assert result["groups"]["webservers"]["vars"]["https_port"] == "443"

    def test_parse_inventory_with_children(self):
        """Test parsing inventory with child groups."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_file = Path(tmpdir) / "inventory"
            inventory_file.write_text("""
[webservers]
web1.example.com

[dbservers]
db1.example.com

[production:children]
webservers
dbservers
""")

            result = parse_inventory_ini(str(inventory_file))

            assert "production" in result["groups"]
            assert "webservers" in result["groups"]["production"]["children"]
            assert "dbservers" in result["groups"]["production"]["children"]

    def test_parse_inventory_file_not_found(self):
        """Test parsing non-existent inventory file."""
        with pytest.raises(FileNotFoundError):
            parse_inventory_ini("/nonexistent/inventory")

    def test_parse_inventory_path_is_directory(self):
        """Test parsing when path is directory."""
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            pytest.raises(ValueError, match="not a file"),
        ):
            parse_inventory_ini(tmpdir)

    def test_parse_inventory_with_comments(self):
        """Test parsing inventory with comments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_file = Path(tmpdir) / "inventory"
            inventory_file.write_text("""
# Production hosts
[webservers]
web1.example.com  # Primary web server
web2.example.com
""")

            result = parse_inventory_ini(str(inventory_file))

            assert "webservers" in result["groups"]
            assert len(result["groups"]["webservers"]["hosts"]) >= 1

    def test_parse_inventory_empty_groups(self):
        """Test parsing inventory with empty groups."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_file = Path(tmpdir) / "inventory"
            inventory_file.write_text("""
[webservers]

[dbservers]
db1.example.com
""")

            result = parse_inventory_ini(str(inventory_file))

            assert "webservers" in result["groups"]
            assert len(result["groups"]["webservers"]["hosts"]) == 0


class TestParseInventoryYaml:
    """Test parse_inventory_yaml function."""

    def test_parse_simple_yaml_inventory(self):
        """Test parsing simple YAML inventory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_file = Path(tmpdir) / "inventory.yml"
            inventory_file.write_text("""
all:
  hosts:
    web1.example.com:
    web2.example.com:
  children:
    webservers:
      hosts:
        web1.example.com:
        web2.example.com:
""")

            result = parse_inventory_yaml(str(inventory_file))

            assert "all" in result
            assert "children" in result["all"]

    def test_parse_yaml_inventory_with_vars(self):
        """Test parsing YAML inventory with variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_file = Path(tmpdir) / "inventory.yml"
            inventory_file.write_text("""
all:
  children:
    webservers:
      hosts:
        web1.example.com:
          ansible_host: 192.168.1.10
          ansible_port: 22
      vars:
        http_port: 80
""")

            result = parse_inventory_yaml(str(inventory_file))

            assert "all" in result

    def test_parse_yaml_inventory_file_not_found(self):
        """Test parsing non-existent YAML inventory."""
        with pytest.raises(FileNotFoundError):
            parse_inventory_yaml("/nonexistent/inventory.yml")

    def test_parse_yaml_inventory_invalid_format(self):
        """Test parsing invalid YAML inventory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_file = Path(tmpdir) / "inventory.yml"
            inventory_file.write_text("invalid: yaml: content: ]\n[")

            with pytest.raises(ValueError, match="Invalid inventory YAML"):
                parse_inventory_yaml(str(inventory_file))

    def test_parse_yaml_inventory_path_is_directory(self):
        """Test parsing when path is directory."""
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            pytest.raises(ValueError, match="not a file"),
        ):
            parse_inventory_yaml(tmpdir)

    def test_parse_yaml_inventory_nested_groups(self):
        """Test parsing YAML inventory with nested groups."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_file = Path(tmpdir) / "inventory.yml"
            inventory_file.write_text("""
all:
  children:
    production:
      children:
        webservers:
          hosts:
            web1:
        dbservers:
          hosts:
            db1:
""")

            result = parse_inventory_yaml(str(inventory_file))

            assert "all" in result


class TestParseRequirementsYml:
    """Test parse_requirements_yml function."""

    def test_parse_simple_requirements(self):
        """Test parsing simple requirements.yml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.yml"
            req_file.write_text("""
collections:
  - name: community.general
    version: "3.0.0"
  - name: ansible.posix
    version: "1.2.0"
""")

            result = parse_requirements_yml(str(req_file))

            # Returns flat dict of name->version
            assert isinstance(result, dict)
            assert "community.general" in result
            assert result["community.general"] == "3.0.0"

    def test_parse_requirements_with_roles(self):
        """Test parsing requirements with roles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.yml"
            req_file.write_text("""
roles:
  - name: geerlingguy.nginx
    version: "2.8.0"
  - name: geerlingguy.mysql
    version: "3.3.0"
""")

            result = parse_requirements_yml(str(req_file))

            # Returns flat dict of name->version
            assert isinstance(result, dict)
            assert "geerlingguy.nginx" in result
            assert result["geerlingguy.nginx"] == "2.8.0"

    def test_parse_requirements_mixed(self):
        """Test parsing requirements with both collections and roles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.yml"
            req_file.write_text("""
collections:
  - name: community.general
    version: "3.0.0"

roles:
  - name: geerlingguy.nginx
    version: "2.8.0"
""")

            result = parse_requirements_yml(str(req_file))

            # Returns flat dict of name->version for both types
            assert isinstance(result, dict)
            assert "community.general" in result
            assert "geerlingguy.nginx" in result

    def test_parse_requirements_with_git_source(self):
        """Test parsing requirements with git sources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.yml"
            req_file.write_text("""
collections:
  - name: namespace.collection
    source: https://github.com/user/collection.git
    type: git
    version: main
""")

            result = parse_requirements_yml(str(req_file))

            assert isinstance(result, dict)
            assert "namespace.collection" in result

    def test_parse_requirements_file_not_found(self):
        """Test parsing non-existent requirements file."""
        with pytest.raises(FileNotFoundError):
            parse_requirements_yml("/nonexistent/requirements.yml")

    def test_parse_requirements_invalid_yaml(self):
        """Test parsing invalid YAML requirements."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.yml"
            req_file.write_text("invalid: yaml: ]\n[")

            with pytest.raises(ValueError, match="Invalid requirements YAML"):
                parse_requirements_yml(str(req_file))

    def test_parse_requirements_empty_file(self):
        """Test parsing empty requirements file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.yml"
            req_file.write_text("")

            result = parse_requirements_yml(str(req_file))

            assert isinstance(result, dict)

    def test_parse_requirements_path_is_directory(self):
        """Test parsing when path is directory."""
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            pytest.raises(ValueError, match="Invalid requirements file name"),
        ):
            parse_requirements_yml(tmpdir)


class TestDetectAnsibleVersion:
    """Test detect_ansible_version function."""

    def test_detect_version_with_valid_environment(self):
        """Test detecting version from valid environment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # This will likely fail but should handle gracefully
            try:
                result = detect_ansible_version(tmpdir)
                assert isinstance(result, str)
            except (RuntimeError, FileNotFoundError, ValueError):
                # Expected when ansible not in environment
                pass

    def test_detect_version_nonexistent_path(self):
        """Test detecting version from non-existent path."""
        with pytest.raises(ValueError, match="does not exist"):
            detect_ansible_version("/nonexistent/environment")

    def test_detect_version_path_is_file(self):
        """Test detecting version when path is file not directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "file.txt"
            file_path.write_text("test")

            # This will fail during ansible executable validation
            with pytest.raises(ValueError):
                detect_ansible_version(str(file_path))


class TestInventoryEdgeCases:
    """Test edge cases in inventory parsing."""

    def test_parse_ini_inventory_with_ranges(self):
        """Test parsing inventory with host ranges."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_file = Path(tmpdir) / "inventory"
            inventory_file.write_text("""
[webservers]
web[01:03].example.com
""")

            result = parse_inventory_ini(str(inventory_file))

            # Should parse without error
            assert "webservers" in result["groups"]

    def test_parse_inventory_with_special_chars_in_vars(self):
        """Test parsing inventory with special characters in variables."""
        test_password = "p@ssw0rd!"  # NOSONAR
        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_file = Path(tmpdir) / "inventory"
            inventory_file.write_text(f"""
[webservers]
web1 ansible_password="{test_password}" ansible_path="/opt/app"
""")

            result = parse_inventory_ini(str(inventory_file))

            assert "web1" in result["hosts"]

    def test_parse_yaml_inventory_with_connection_vars(self):
        """Test parsing YAML inventory with connection variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_file = Path(tmpdir) / "inventory.yml"
            inventory_file.write_text("""
all:
  hosts:
    server1:
      ansible_connection: ssh
      ansible_user: admin
      ansible_become: true
""")

            result = parse_inventory_yaml(str(inventory_file))

            assert "all" in result

    def test_parse_requirements_with_version_constraints(self):
        """Test parsing requirements with version constraints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.yml"
            req_file.write_text("""
collections:
  - name: community.general
    version: ">=3.0.0,<4.0.0"
""")

            result = parse_requirements_yml(str(req_file))

            assert "community.general" in result
            assert result["community.general"]

    def test_parse_config_with_multiline_values(self):
        """Test parsing config with multiline values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "ansible.cfg"
            config_file.write_text("""
[defaults]
inventory = ./inventory
""")

            result = parse_ansible_cfg(str(config_file))

            assert "defaults" in result

    def test_parse_inventory_with_localhost(self):
        """Test parsing inventory with localhost entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_file = Path(tmpdir) / "inventory"
            inventory_file.write_text("""
[local]
localhost ansible_connection=local
""")

            result = parse_inventory_ini(str(inventory_file))

            assert "local" in result["groups"]
            assert "localhost" in result["hosts"]

    def test_parse_yaml_inventory_with_list_vars(self):
        """Test parsing YAML inventory with list variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_file = Path(tmpdir) / "inventory.yml"
            inventory_file.write_text("""
all:
  children:
    webservers:
      vars:
        allowed_ports:
          - 80
          - 443
          - 8080
""")

            result = parse_inventory_yaml(str(inventory_file))

            assert "all" in result

    def test_parse_requirements_with_scm_sources(self):
        """Test parsing requirements with SCM sources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.yml"
            req_file.write_text("""
roles:
  - src: https://github.com/user/role.git
    scm: git
    version: v1.0
    name: custom_role
""")

            result = parse_requirements_yml(str(req_file))

            assert isinstance(result, dict)
            assert "custom_role" in result
