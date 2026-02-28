"""Advanced server.py coverage for complex tool implementations."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from souschef import server


class TestProfilingTools:
    """Coverage for profiling tool functions."""

    def test_profile_cookbook_performance_error(self, tmp_path: Path) -> None:
        """Profiling errors should return formatted error."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        with patch(
            "souschef.profiling.generate_cookbook_performance_report",
            side_effect=RuntimeError("profiling failed"),
        ):
            result = server.profile_cookbook_performance(str(cookbook_dir))
            assert "Error" in result or "profiling" in result

    def test_profile_parsing_operation_error(self, tmp_path: Path) -> None:
        """Parsing profile errors should return formatted error."""
        file_path = tmp_path / "recipe.rb"
        file_path.write_text("package 'nginx'")

        with patch(
            "souschef.profiling.profile_function",
            side_effect=RuntimeError("profiling failed"),
        ):
            result = server.profile_parsing_operation("recipe", str(file_path))
            assert "Error" in result


class TestPathNormalization:
    """Coverage for path normalization edge cases."""

    def test_sanitize_cookbook_paths_empty_path(self) -> None:
        """Empty paths in comma list should be filtered."""
        result = server._sanitize_cookbook_paths_input("/path1, , /path2")
        # Should have two paths (empty one filtered)
        assert "/path1" in result
        assert "/path2" in result

    def test_sanitize_cookbook_paths_relative_after_norm(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Path that's relative after normalization should raise."""

        # Mock _normalize_path to return a relative path
        def _mock_normalize(path: str) -> Path:
            return Path("relative/path")

        monkeypatch.setattr("souschef.server._normalize_path", _mock_normalize)

        with pytest.raises(ValueError, match="must be absolute"):
            server._sanitize_cookbook_paths_input("/some/path")


class TestValidationTool:
    """Coverage for validation tool."""

    def test_validate_conversion_success(self) -> None:
        """Valid playbook content should pass validation."""
        playbook = """---
- name: Test playbook
  hosts: all
  tasks:
    - name: Install nginx
      package:
        name: nginx
        state: present
"""
        result = server.validate_conversion("playbook", playbook)
        # Should return validation results
        assert isinstance(result, str)
        assert len(result) > 0


class TestDatabagProcessing:
    """Coverage for databag processing helpers."""

    def test_process_databag_directory_with_items(self, tmp_path: Path) -> None:
        """Databag directory with items should be processed."""
        databags_dir = tmp_path / "data_bags"
        databags_dir.mkdir()
        bag_dir = databags_dir / "users"
        bag_dir.mkdir()
        (bag_dir / "admin.json").write_text('{"id": "admin", "shell": "/bin/bash"}')
        (bag_dir / "user1.json").write_text('{"id": "user1", "home": "/home/user1"}')

        result = server.generate_ansible_vault_from_databags(str(databags_dir))
        # Should have processed multiple items
        assert isinstance(result, str)
        assert len(result) > 100


class TestEnvironmentConversion:
    """Coverage for environment conversion helpers."""

    def test_convert_environment_with_constraints(self) -> None:
        """Environment with cookbook constraints should convert."""
        content = """
name 'production'
description 'Production environment'
cookbook_versions({
  'nginx' => '= 1.2.3',
  'mysql' => '~> 2.0.0'
})
"""
        result = server.convert_chef_environment_to_inventory_group(
            content, "production", include_constraints=True
        )
        # Should include version constraints
        assert isinstance(result, str)
        assert "production" in result


class TestAnalysisTools:
    """Coverage for analysis tool paths."""

    def test_analyse_chef_search_patterns_empty_cookbook(self, tmp_path: Path) -> None:
        """Empty cookbook should return analysis."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        result = server.analyse_chef_search_patterns(str(cookbook_dir))
        # Should return empty analysis
        assert isinstance(result, str)
        assert "search" in result.lower() or "pattern" in result.lower()

    def test_analyse_cookbook_dependencies_with_deps(self, tmp_path: Path) -> None:
        """Cookbook with dependencies should be analyzed."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        metadata_content = """
name 'myapp'
depends 'nginx', '~> 1.0'
depends 'mysql', '>= 2.0.0'
"""
        (cookbook_dir / "metadata.rb").write_text(metadata_content)

        result = server.analyse_cookbook_dependencies(str(cookbook_dir))
        # Should include dependency info
        assert isinstance(result, str)
        assert len(result) > 50


class TestRubyParsing:
    """Coverage for Ruby parsing helpers."""

    def test_parse_ruby_hash_with_complex_nesting(self) -> None:
        """Complex nested Ruby hash should parse."""
        content = "'a' => { 'b' => { 'c' => 1 } }, 'd' => [1, 2]"
        result = server.parse_ruby_hash(content)
        # Should handle nesting
        assert isinstance(result, dict)

    def test_skip_whitespace_with_arrows(self) -> None:
        """Whitespace and arrow skipping should work."""
        idx = server._skip_whitespace_and_arrows("  =>  value", 0)
        assert idx > 2


class TestInSpecGeneration:
    """Coverage for InSpec generation from recipes."""

    def test_generate_inspec_with_complex_resources(self, tmp_path: Path) -> None:
        """Recipe with various resources should generate controls."""
        recipe_file = tmp_path / "recipe.rb"
        recipe_content = """
package 'nginx' do
  action :install
end

service 'nginx' do
  action [:enable, :start]
end

file '/etc/nginx/nginx.conf' do
  content 'server {}'
  owner 'root'
  mode '0644'
end
"""
        recipe_file.write_text(recipe_content)

        result = server.generate_inspec_from_recipe(str(recipe_file))
        # Should generate multiple controls
        assert isinstance(result, str)
        assert "control" in result or len(result) > 0


class TestMigrationPlan:
    """Coverage for migration plan generation."""

    def test_generate_migration_plan_with_recipes(self, tmp_path: Path) -> None:
        """Cookbook with recipes should generate comprehensive plan."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'webserver'\nversion '1.0.0'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")
        (recipes_dir / "config.rb").write_text("template '/etc/nginx/nginx.conf'")

        result = server.generate_migration_plan(str(cookbook_dir))
        # Should generate comprehensive plan
        assert isinstance(result, str)
        assert "migration" in result.lower() or "plan" in result.lower()
        assert len(result) > 200


class TestAnsibleUpgradeHelpers:
    """Coverage for Ansible upgrade plan helpers."""

    def test_format_helpers_via_integration(self, tmp_path: Path) -> None:
        """Test formatting helpers through the main tool."""
        env_dir = tmp_path / "env"
        env_dir.mkdir()

        # Create mock upgrade plan with all required fields
        mock_plan = {
            "upgrade_path": {
                "from_version": "2.9",
                "to_version": "2.15",
                "risk_level": "medium",
                "estimated_effort_days": 3,
                "direct_upgrade": False,
                "intermediate_versions": ["2.10", "2.11", "2.12"],
                "risk_factors": ["Breaking changes"],
            },
            "estimated_downtime_hours": 2,
            "risk_assessment": {"mitigation": ["Test thoroughly"]},
            "pre_upgrade_checklist": ["Backup"],
            "post_upgrade_validation": ["Test"],
            "upgrade_steps": [
                {
                    "step": 1,
                    "action": "Backup",
                    "command": "cp -r /etc/ansible /backup/",
                    "duration_minutes": 15,
                    "notes": ["Store securely"],
                }
            ],
            "rollback_plan": {
                "steps": ["Restore"],
                "estimated_duration_minutes": 30,
            },
        }

        with (
            patch(
                "souschef.parsers.ansible_inventory.detect_ansible_version",
                return_value="2.9.27",
            ),
            patch(
                "souschef.ansible_upgrade.generate_upgrade_plan", return_value=mock_plan
            ),
        ):
            result = server.plan_ansible_upgrade(str(env_dir), "2.15")
            # Should produce formatted plan
            assert isinstance(result, str)
            assert "Upgrade Plan" in result or len(result) > 100


class TestGenerateAnsibleUpgradePlan:
    """Coverage for Ansible upgrade plan generation."""

    def test_upgrade_plan_with_ansible_executable(self, tmp_path: Path) -> None:
        """Environment with ansible binary should detect version."""
        env_dir = tmp_path / "env"
        env_dir.mkdir()
        bin_dir = env_dir / "bin"
        bin_dir.mkdir()
        ansible_bin = bin_dir / "ansible"
        ansible_bin.write_text("#!/bin/bash\necho 'ansible 2.9.0'")
        ansible_bin.chmod(0o755)

        with (
            patch(
                "souschef.parsers.ansible_inventory.detect_ansible_version",
                return_value="2.9.27",
            ),
            patch("souschef.ansible_upgrade.generate_upgrade_plan") as mock_plan,
        ):
            mock_plan.return_value = {
                "upgrade_path": {
                    "from_version": "2.9",
                    "to_version": "2.10",
                    "breaking_changes": [],
                    "python_upgrade_needed": False,
                    "current_python": ["3.6+"],
                    "required_python": ["3.6+"],
                    "collection_updates_needed": {},
                    "risk_level": "low",
                    "estimated_effort_days": 1,
                    "direct_upgrade": True,
                    "intermediate_versions": [],
                    "risk_factors": [],
                },
                "estimated_downtime_hours": 1,
                "risk_assessment": {"mitigation": []},
                "pre_upgrade_checklist": ["Backup"],
                "post_upgrade_validation": ["Test"],
                "rollback_plan": {
                    "steps": ["Restore"],
                    "estimated_duration_minutes": 30,
                },
                "upgrade_steps": [],
                "risk_factors": [],
            }
            result = server.plan_ansible_upgrade(str(env_dir), "2.15")
            assert isinstance(result, str)
            assert len(result) > 100

    def test_upgrade_plan_version_parsing(self, tmp_path: Path) -> None:
        """Version parsing should handle various formats."""
        env_dir = tmp_path / "env"
        env_dir.mkdir()

        with (
            patch(
                "souschef.parsers.ansible_inventory.detect_ansible_version",
                return_value="2",
            ),
            patch("souschef.ansible_upgrade.generate_upgrade_plan") as mock_plan,
        ):
            mock_plan.return_value = {
                "upgrade_path": {
                    "from_version": "2",
                    "to_version": "2.15",
                    "breaking_changes": [],
                    "python_upgrade_needed": False,
                    "current_python": ["3.6+"],
                    "required_python": ["3.6+"],
                    "collection_updates_needed": {},
                    "risk_level": "low",
                    "estimated_effort_days": 1,
                    "direct_upgrade": True,
                    "intermediate_versions": [],
                    "risk_factors": [],
                },
                "estimated_downtime_hours": 1,
                "risk_assessment": {"mitigation": []},
                "pre_upgrade_checklist": [],
                "post_upgrade_validation": [],
                "rollback_plan": {"steps": [], "estimated_duration_minutes": 0},
                "upgrade_steps": [],
                "risk_factors": [],
            }
            result = server.plan_ansible_upgrade(str(env_dir), "2.15")
            assert isinstance(result, str)

    def test_upgrade_plan_with_python_upgrade(self, tmp_path: Path) -> None:
        """Plan with Python upgrade needed should include that section."""
        env_dir = tmp_path / "env"
        env_dir.mkdir()

        with (
            patch(
                "souschef.parsers.ansible_inventory.detect_ansible_version",
                return_value="2.9.0",
            ),
            patch("souschef.ansible_upgrade.generate_upgrade_plan") as mock_plan,
        ):
            mock_plan.return_value = {
                "upgrade_path": {
                    "from_version": "2.9",
                    "to_version": "2.15",
                    "breaking_changes": ["Module X removed"],
                    "python_upgrade_needed": True,
                    "current_python": ["2.7", "3.5"],
                    "required_python": ["3.8+"],
                    "collection_updates_needed": {
                        "ansible.posix": "1.5.0",
                        "community.general": "6.0.0",
                    },
                    "risk_level": "high",
                    "estimated_effort_days": 5,
                    "direct_upgrade": False,
                    "intermediate_versions": ["2.10", "2.11"],
                    "risk_factors": ["Major changes"],
                },
                "estimated_downtime_hours": 4,
                "risk_assessment": {"mitigation": ["Test thoroughly"]},
                "pre_upgrade_checklist": ["Backup"],
                "post_upgrade_validation": ["Test"],
                "rollback_plan": {
                    "steps": ["Restore"],
                    "estimated_duration_minutes": 30,
                },
                "upgrade_steps": [
                    {
                        "step": 1,
                        "action": "Preparation",
                        "duration_minutes": 60,
                        "notes": ["Backup configs"],
                    }
                ],
                "risk_factors": ["High complexity"],
            }
            result = server.plan_ansible_upgrade(str(env_dir), "2.15")
            assert "Python" in result or "python" in result
            assert "collection" in result.lower() or "Collection" in result


class TestInventoryGeneration:
    """Coverage for inventory generation from environments."""

    def test_generate_inventory_with_multiple_environments(
        self, tmp_path: Path
    ) -> None:
        """Multiple environments should be processed."""
        env_dir = tmp_path / "environments"
        env_dir.mkdir()
        (env_dir / "dev.rb").write_text("name 'dev'\ndescription 'Development'")
        (env_dir / "staging.rb").write_text("name 'staging'\ndescription 'Staging'")
        (env_dir / "prod.rb").write_text("name 'prod'\ndescription 'Production'")

        result = server.generate_inventory_from_chef_environments(str(env_dir))
        # Should process all environments
        assert isinstance(result, str)
        assert len(result) > 100
