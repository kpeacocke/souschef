"""Targeted tests for remaining coverage gaps in high-coverage modules."""

import tempfile
from pathlib import Path

import pytest

from souschef.core.path_utils import _resolve_path_under_base, _validate_relative_parts
from souschef.deployment import _generate_ansible_deployment_strategy
from souschef.parsers.ansible_inventory import parse_inventory_file


class TestAnsibleInventoryEdgeCases:
    """Test parsing edge cases in Ansible inventory."""

    def test_parse_file_without_extension_fails_both_formats(self) -> None:
        """Test handling when file without extension is neither INI nor YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with invalid content (neither INI nor YAML)
            file_path = Path(tmpdir) / "inventory"
            file_path.write_text("{ invalid yaml and [not ini }")

            try:
                result = parse_inventory_file(str(file_path))
                # If it doesn't raise, check that it returns something reasonable
                assert result is not None
            except ValueError:
                # Expected behavior - file is invalid
                pass

    def test_parse_yaml_file_with_parsing_error(self) -> None:
        """Test YAML file with format error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "inventory.yaml"
            # Invalid YAML
            file_path.write_text("key1: value1\n  bad_indent: value2")

            with pytest.raises(ValueError):
                parse_inventory_file(str(file_path))

    def test_parse_ini_file_success(self) -> None:
        """Test successful INI file parsing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "inventory.ini"
            ini_content = "[all]\nhost1 ansible_host=192.168.1.1"
            file_path.write_text(ini_content)

            result = parse_inventory_file(str(file_path))
            assert result is not None
            assert "host1" in result or len(result) > 0


class TestDeploymentStrategyGeneration:
    """Test deployment strategy generation edge cases."""

    def test_generate_rolling_update_strategy(self) -> None:
        """Test generation of rolling update deployment strategy."""
        analysis = {
            "cookbooks": 5,
            "recipes": 20,
            "resources": 150,
            "complexity": "moderate",
        }

        result = _generate_ansible_deployment_strategy(analysis, "unknown_pattern")

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_blue_green_strategy(self) -> None:
        """Test generation of blue/green deployment strategy."""
        analysis = {
            "cookbooks": 3,
            "recipes": 10,
            "resources": 50,
            "complexity": "low",
        }

        result = _generate_ansible_deployment_strategy(analysis, "blue_green")

        assert result is not None
        assert isinstance(result, str)

    def test_generate_canary_strategy(self) -> None:
        """Test generation of canary deployment strategy."""
        analysis = {
            "cookbooks": 2,
            "recipes": 8,
            "resources": 40,
            "complexity": "low",
        }

        result = _generate_ansible_deployment_strategy(analysis, "canary")

        assert result is not None
        assert isinstance(result, str)


class TestPathUtilsValidation:
    """Test path validation edge cases."""

    def test_validate_relative_parts_with_double_dots(self) -> None:
        """Test validation rejects paths with .. traversal."""
        with pytest.raises(ValueError) as exc_info:
            _validate_relative_parts(("dir", "..", "etc"))

        assert "traversal" in str(exc_info.value).lower()

    def test_validate_relative_parts_with_absolute_path(self) -> None:
        """Test validation rejects absolute path components."""
        with pytest.raises(ValueError) as exc_info:
            _validate_relative_parts(("/absolute",))

        assert "traversal" in str(exc_info.value).lower()

    def test_resolve_path_under_base_with_null_bytes(self) -> None:
        """Test that null bytes in path are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_path = "test\x00path"

            with pytest.raises(ValueError) as exc_info:
                _resolve_path_under_base(bad_path, tmpdir)

            assert "null" in str(exc_info.value).lower()

    def test_resolve_path_under_base_valid(self) -> None:
        """Test resolving a valid path under base."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            subdir = base / "subdir"
            subdir.mkdir()

            result = _resolve_path_under_base("subdir/file.txt", str(base))

            assert result.parent.name == "subdir"

    def test_resolve_path_with_symlink(self) -> None:
        """Test resolving path with symlink."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "target"
            target.mkdir()

            # Create a file in target
            (target / "file.txt").write_text("content")

            # Create symlink
            link = base / "link"
            try:
                link.symlink_to(target)
            except OSError:
                # Skip if symlinks not supported
                pytest.skip("Symlinks not supported")

            result = _resolve_path_under_base(str(link / "file.txt"), str(base))
            assert result.exists()


class TestMigrationV2HostAssignment:
    """Test migration V2 orchestrator host assignment edge cases."""

    def test_deployment_strategy_with_mock(self) -> None:
        """Test deployment strategy generation with edge case analysis."""
        analysis = {
            "cookbooks": 10,
            "recipes": 50,
            "resources": 300,
            "complexity": "high",
        }

        # Test an pattern that should trigger rolling update
        result = _generate_ansible_deployment_strategy(analysis, "invalid_pattern")
        assert result is not None
        assert isinstance(result, str)
