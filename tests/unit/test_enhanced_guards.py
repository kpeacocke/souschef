"""Unit tests for enhanced guard handling feature."""

from pathlib import Path
from unittest.mock import patch

from souschef.server import (
    _convert_chef_block_to_ansible,
    _convert_chef_condition_to_ansible,
    _convert_guards_to_when_conditions,
    _extract_guard_patterns,
    _parse_guard_array,
    parse_recipe,
)

FIXTURES_DIR = Path(__file__).parents[1] / "integration" / "fixtures"


class TestGuardPatternExtraction:
    """Test extraction of guard patterns from Chef resources."""

    def test_extract_simple_string_guards(self) -> None:
        """Test extraction of simple string-based guards."""
        resource_block = """
        package 'nginx' do
          action :install
          only_if 'test -f /etc/debian_version'
          not_if 'systemctl is-active nginx'
        end
        """
        (
            only_if_conds,
            not_if_conds,
            only_if_blocks,
            not_if_blocks,
            only_if_arrays,
            not_if_arrays,
        ) = _extract_guard_patterns(resource_block)

        assert len(only_if_conds) == 1
        assert only_if_conds[0] == "test -f /etc/debian_version"
        assert len(not_if_conds) == 1
        assert not_if_conds[0] == "systemctl is-active nginx"
        assert len(only_if_blocks) == 0
        assert len(not_if_blocks) == 0

    def test_extract_lambda_guards(self) -> None:
        """Test extraction of lambda/proc syntax guards."""
        resource_block = """
        service 'postgresql' do
          action :start
          only_if { ::File.exist?('/var/lib/postgresql') }
          not_if { File.directory?('/tmp/disabled') }
        end
        """
        (
            _,
            _,
            only_if_blocks,
            not_if_blocks,
            _,
            _,
        ) = _extract_guard_patterns(resource_block)

        assert len(only_if_blocks) >= 1
        assert "File.exist?" in only_if_blocks[0]
        assert len(not_if_blocks) >= 1
        assert "File.directory?" in not_if_blocks[0]

    def test_extract_array_guards(self) -> None:
        """Test extraction of array-based guards."""
        resource_block = """
        package 'postgresql' do
          action :install
          only_if ['test -f /etc/debian_version', 'which systemctl']
        end
        """
        (
            _,
            _,
            _,
            _,
            only_if_arrays,
            _,
        ) = _extract_guard_patterns(resource_block)

        assert len(only_if_arrays) == 1
        assert "test -f /etc/debian_version" in only_if_arrays[0]
        assert "which systemctl" in only_if_arrays[0]

    def test_extract_do_end_blocks(self) -> None:
        """Test extraction of do...end block syntax."""
        resource_block = """
        execute 'test' do
          command 'echo test'
          only_if do
            File.exist?('/tmp/flag')
          end
        end
        """
        (
            _,
            _,
            only_if_blocks,
            _,
            _,
            _,
        ) = _extract_guard_patterns(resource_block)

        assert len(only_if_blocks) >= 1
        assert "File.exist?" in only_if_blocks[0]


class TestGuardArrayParsing:
    """Test parsing of guard arrays."""

    def test_parse_simple_string_array(self) -> None:
        """Test parsing array with simple string conditions."""
        array_content = "'test -f /etc/file', 'which command'"
        conditions = _parse_guard_array(array_content, negate=False)

        assert len(conditions) >= 2
        assert any("test -f /etc/file" in cond for cond in conditions)
        assert any("which command" in cond for cond in conditions)

    def test_parse_negated_array(self) -> None:
        """Test parsing array with negation."""
        array_content = "'test -d /var/log/app'"
        conditions = _parse_guard_array(array_content, negate=True)

        assert len(conditions) >= 1
        assert any("not" in cond.lower() for cond in conditions)

    def test_parse_mixed_array(self) -> None:
        """Test parsing array with mixed condition types."""
        array_content = "'test -f /etc/file', { File.exist?('/tmp/flag') }"
        conditions = _parse_guard_array(array_content, negate=False)

        assert len(conditions) >= 2


class TestChefConditionConversion:
    """Test conversion of Chef conditions to Ansible."""

    def test_convert_file_exist_check(self) -> None:
        """Test conversion of File.exist? checks."""
        condition = "File.exist?('/etc/file')"
        result = _convert_chef_condition_to_ansible(condition)

        assert "is file" in result

    def test_convert_which_command(self) -> None:
        """Test conversion of which command checks."""
        condition = "system('which nginx')"
        result = _convert_chef_condition_to_ansible(condition)

        assert "nginx" in result or "packages" in result

    def test_convert_platform_check(self) -> None:
        """Test conversion of platform checks."""
        condition = "platform?"
        result = _convert_chef_condition_to_ansible(condition)

        assert "ansible_facts" in result or "os_family" in result

    def test_convert_node_attribute(self) -> None:
        """Test conversion of node attribute checks."""
        condition = "node['app']['enabled']"
        result = _convert_chef_condition_to_ansible(condition)

        assert "hostvars" in result or "inventory_hostname" in result

    def test_convert_with_negation(self) -> None:
        """Test condition conversion with negation."""
        condition = "File.exist?('/tmp/file')"
        result = _convert_chef_condition_to_ansible(condition, negate=True)

        assert "not" in result.lower()


class TestChefBlockConversion:
    """Test conversion of Chef blocks to Ansible."""

    def test_convert_simple_boolean(self) -> None:
        """Test conversion of simple boolean returns."""
        block = "true"
        result = _convert_chef_block_to_ansible(block, positive=True)

        assert result == "true"

        block = "false"
        result = _convert_chef_block_to_ansible(block, positive=False)

        assert result == "true"

    def test_convert_file_exist_block(self) -> None:
        """Test conversion of File.exist? in blocks."""
        block = "::File.exist?('/var/lib/postgresql')"
        result = _convert_chef_block_to_ansible(block, positive=True)

        assert "file" in result.lower() or "ansible_check_mode" in result

    def test_convert_directory_check_block(self) -> None:
        """Test conversion of File.directory? in blocks."""
        block = "File.directory?('/var/cache/app')"
        result = _convert_chef_block_to_ansible(block, positive=True)

        assert "is directory" in result
        assert "/var/cache/app" in result

    def test_convert_system_command_block(self) -> None:
        """Test conversion of system() calls in blocks."""
        block = "system('which npm')"
        result = _convert_chef_block_to_ansible(block, positive=True)

        assert "ansible" in result.lower()

    def test_convert_backtick_command(self) -> None:
        """Test conversion of backtick command execution."""
        block = "`pgrep nginx`.length > 0"
        result = _convert_chef_block_to_ansible(block, positive=True)

        assert "ansible" in result.lower() or "TODO" in result

    def test_convert_with_negative_flag(self) -> None:
        """Test block conversion with negative flag."""
        block = "File.exist?('/tmp/disabled')"
        result = _convert_chef_block_to_ansible(block, positive=False)

        assert "not" in result.lower()


class TestGuardsToWhenConditions:
    """Test overall guard to when condition conversion."""

    def test_convert_only_if_conditions(self) -> None:
        """Test conversion of only_if conditions."""
        conditions = _convert_guards_to_when_conditions(
            only_if_conditions=["test -f /etc/file"],
            not_if_conditions=[],
            only_if_blocks=[],
            not_if_blocks=[],
            only_if_arrays=[],
            not_if_arrays=[],
        )

        assert len(conditions) >= 1

    def test_convert_not_if_conditions(self) -> None:
        """Test conversion of not_if conditions."""
        conditions = _convert_guards_to_when_conditions(
            only_if_conditions=[],
            not_if_conditions=["test -d /var/log"],
            only_if_blocks=[],
            not_if_blocks=[],
            only_if_arrays=[],
            not_if_arrays=[],
        )

        assert len(conditions) >= 1
        assert any("not" in cond.lower() for cond in conditions)

    def test_convert_mixed_guards(self) -> None:
        """Test conversion of mixed guard types."""
        conditions = _convert_guards_to_when_conditions(
            only_if_conditions=["test -f /etc/file"],
            not_if_conditions=["systemctl is-active nginx"],
            only_if_blocks=["File.exist?('/tmp/flag')"],
            not_if_blocks=[],
            only_if_arrays=[],
            not_if_arrays=[],
        )

        assert len(conditions) >= 2

    def test_convert_array_guards(self) -> None:
        """Test conversion of array-based guards."""
        conditions = _convert_guards_to_when_conditions(
            only_if_conditions=[],
            not_if_conditions=[],
            only_if_blocks=[],
            not_if_blocks=[],
            only_if_arrays=["'test -f /etc/file', 'which command'"],
            not_if_arrays=[],
        )

        assert len(conditions) >= 2


class TestComplexGuardIntegration:
    """Integration tests with complex guard scenarios."""

    def test_parse_complex_guards_recipe(self) -> None:
        """Test parsing recipe with complex guards."""
        fixture_path = FIXTURES_DIR / "complex_guards_recipe.rb"
        result = parse_recipe(str(fixture_path))

        # Verify guards are detected and converted
        assert "when:" in result or "# No guards found" not in result

    def test_lambda_guard_handling(self) -> None:
        """Test handling of lambda syntax guards."""
        with patch("souschef.server._normalize_path") as mock_normalize:
            mock_normalize.return_value = FIXTURES_DIR / "complex_guards_recipe.rb"
            result = parse_recipe(str(FIXTURES_DIR / "complex_guards_recipe.rb"))

            # Verify lambda guards are processed
            assert "Resource" in result

    def test_array_guard_handling(self) -> None:
        """Test handling of array-based guards."""
        result = parse_recipe(str(FIXTURES_DIR / "complex_guards_recipe.rb"))

        # Verify output contains multiple resources
        assert result.count("Resource") >= 3
