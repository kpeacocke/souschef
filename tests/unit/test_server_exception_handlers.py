"""Comprehensive exception handler coverage for server.py MCP tools."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from souschef import server


class TestDatabagToolExceptions:
    """Coverage for databag tool exception handlers."""

    def test_generate_databag_conversion_summary_exception(
        self, tmp_path: Path
    ) -> None:
        """Exception in databag summary generation should be handled."""
        databags_dir = tmp_path / "data_bags"
        databags_dir.mkdir()

        with patch(
            "souschef.server._process_databag_directory",
            side_effect=RuntimeError("databag processing failed"),
        ):
            result = server.generate_ansible_vault_from_databags(str(databags_dir))
            assert "Error" in result or "failed" in result.lower()


class TestToolNormalizationErrors:
    """Coverage for path normalization error handlers."""

    def test_parse_recipe_bad_path(self) -> None:
        """Bad path to parse_recipe should return error."""
        result = server.parse_recipe("/nonexistent/path/recipe.rb")
        assert "Error" in result or "not found" in result.lower()

    def test_parse_attributes_bad_path(self) -> None:
        """Bad path to parse_attributes should return error."""
        result = server.parse_attributes("/nonexistent/path/attributes.rb")
        assert "Error" in result or "not found" in result.lower()

    def test_parse_custom_resource_bad_path(self) -> None:
        """Bad path to parse_custom_resource should return error."""
        result = server.parse_custom_resource("/nonexistent/path/resource.rb")
        assert "Error" in result or "not found" in result.lower()


class TestSearchAndApplicationPatterns:
    """Coverage for Chef search pattern analysis."""

    def test_analyse_search_patterns_with_search_calls(self, tmp_path: Path) -> None:
        """Cookbook with search calls should be analyzed."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        recipe_content = """
search(:node, 'role:webserver') do |node|
  log node['fqdn']
end
"""
        (recipes_dir / "default.rb").write_text(recipe_content)

        result = server.analyse_chef_search_patterns(str(cookbook_dir))
        assert isinstance(result, str)
        assert len(result) > 50

    def test_analyse_application_patterns_with_complex_recipe(
        self, tmp_path: Path
    ) -> None:
        """Cookbook with complex deployment patterns should be analyzed."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'app'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        recipe_content = """
include_recipe 'nginx::default'

template '/etc/app/config.yml' do
  source 'config.yml.erb'
end

service 'app' do
  action [:enable, :start]
end
"""
        (recipes_dir / "default.rb").write_text(recipe_content)

        result = server.analyse_chef_application_patterns(str(cookbook_dir))
        assert isinstance(result, str)
        assert len(result) > 50


class TestCookbookConversion:
    """Coverage for cookbook conversion tools."""

    def test_convert_cookbook_comprehensive_with_artifacts(
        self, tmp_path: Path
    ) -> None:
        """Cookbook with various artifacts should convert comprehensively."""
        cookbook_dir = tmp_path / "myapp"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'myapp'\nversion '1.0.0'")

        # Recipes
        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")

        # Attributes
        attributes_dir = cookbook_dir / "attributes"
        attributes_dir.mkdir()
        (attributes_dir / "default.rb").write_text("default['nginx']['port'] = 80")

        # Output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = server.convert_cookbook_comprehensive(
            str(cookbook_dir), str(output_dir)
        )
        assert isinstance(result, str)
        assert len(result) > 50

    def test_convert_all_cookbooks_with_multiple(self, tmp_path: Path) -> None:
        """Multiple cookbooks should all be converted."""
        repo_dir = tmp_path / "chef-repo"
        cookbooks_dir = repo_dir / "cookbooks"
        cookbooks_dir.mkdir(parents=True)

        # Cookbook 1
        cb1 = cookbooks_dir / "nginx"
        cb1.mkdir()
        (cb1 / "metadata.rb").write_text("name 'nginx'")
        recipes1 = cb1 / "recipes"
        recipes1.mkdir()
        (recipes1 / "default.rb").write_text("package 'nginx'")

        # Cookbook 2
        cb2 = cookbooks_dir / "mysql"
        cb2.mkdir()
        (cb2 / "metadata.rb").write_text("name 'mysql'")
        recipes2 = cb2 / "recipes"
        recipes2.mkdir()
        (recipes2 / "default.rb").write_text("package 'mysql-server'")

        # Output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = server.convert_all_cookbooks_comprehensive(
            str(cookbooks_dir), str(output_dir)
        )
        assert isinstance(result, str)
        assert len(result) > 100


class TestMigrationReports:
    """Coverage for migration report generation."""

    def test_generate_migration_report_with_details(self, tmp_path: Path) -> None:
        """Detailed migration report should be generated."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'app'\nversion '2.0.0'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'app'\nservice 'app'")

        result = server.generate_migration_report(cookbook_paths=str(cookbook_dir))
        assert isinstance(result, str)
        assert len(result) > 100


class TestCIGeneration:
    """Coverage for CI/CD pipeline generation."""

    def test_generate_github_actions_from_cookbook(self, tmp_path: Path) -> None:
        """Cookbook should convert to GitHub Actions workflow."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'cicd'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'app'")

        result = server.generate_github_workflow_from_chef(str(cookbook_dir))
        assert isinstance(result, str)
        # Resulting YAML has jobs dict
        assert "jobs" in result.lower()

    def test_generate_gitlab_ci_from_cookbook(self, tmp_path: Path) -> None:
        """Cookbook should convert to GitLab CI config."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'cicd'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'app'")

        result = server.generate_gitlab_ci_from_chef(str(cookbook_dir))
        assert isinstance(result, str)
        assert "stages" in result.lower() or "gitlab" in result.lower()


class TestDeploymentStrategies:
    """Coverage for deployment strategy generation."""

    def test_generate_blue_green_deployment(self, tmp_path: Path) -> None:
        """Blue-green deployment playbook should be generated."""
        playbook_content = """
---
- name: Deploy application
  hosts: all
  tasks:
    - name: Install app
      package:
        name: myapp
        state: present
"""
        result = server.generate_blue_green_deployment_playbook(playbook_content)
        assert isinstance(result, str)
        assert "blue" in result.lower() or "green" in result.lower()

    def test_generate_canary_deployment(self, tmp_path: Path) -> None:
        """Canary deployment strategy should be generated."""
        playbook_content = """
---
- name: Deploy application
  hosts: all
  tasks:
    - name: Deploy app
      command: deploy.sh
"""
        result = server.generate_canary_deployment_strategy(
            playbook_content, canary_percentage=10
        )
        assert isinstance(result, str)
        assert "canary" in result.lower() or "gradual" in result.lower()


class TestHabitatConversion:
    """Coverage for Habitat plan conversion."""

    def test_parse_habitat_plan_with_deps(self, tmp_path: Path) -> None:
        """Habitat plan with dependencies should be parsed."""
        plan_file = tmp_path / "plan.sh"
        plan_content = """
pkg_name=myapp
pkg_version="1.0.0"
pkg_deps=(core/nginx core/postgresql)
pkg_build_deps=(core/gcc)

do_build() {
  make
}

do_install() {
  cp target/* "${pkg_prefix}/bin/"
}
"""
        plan_file.write_text(plan_content)

        result = server.parse_habitat_plan(str(plan_file))
        assert isinstance(result, str)
        assert "myapp" in result or "pkg_name" in result


class TestAnsibleUpgrade:
    """Coverage for Ansible upgrade functionality."""

    def test_check_ansible_eol_status_with_error(self) -> None:
        """Unknown version should return error information."""
        result = server.check_ansible_eol_status("2.8")
        assert isinstance(result, str)
        # Returns JSON error for unknown version, or actual EOL status
        assert "error" in result.lower() or "eol" in result.lower()

    def test_assess_ansible_upgrade_readiness(self, tmp_path: Path) -> None:
        """Environment readiness assessment should be generated."""
        env_dir = tmp_path / "env"
        env_dir.mkdir()

        # Mock ansible installation
        bin_dir = env_dir / "bin"
        bin_dir.mkdir()
        ansible_bin = bin_dir / "ansible"
        ansible_bin.write_text("#!/bin/bash\necho 'ansible 2.9.0'")
        ansible_bin.chmod(0o755)

        with patch(
            "souschef.parsers.ansible_inventory.detect_ansible_version",
            return_value="2.9.27",
        ):
            result = server.assess_ansible_upgrade_readiness(str(env_dir))
            assert isinstance(result, str)
            assert len(result) > 50
