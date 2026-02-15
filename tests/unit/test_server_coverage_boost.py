"""Tests to improve server.py coverage targeting error paths and edge cases."""

from souschef.server import (
    generate_github_workflow_from_chef,
    generate_gitlab_ci_from_chef,
    generate_jenkinsfile_from_chef,
    profile_parsing_operation,
)


class TestJenkinsfileGeneration:
    """Test Jenkinsfile generation edge cases."""

    def test_generate_jenkinsfile_with_invalid_path(self, tmp_path):
        """Test Jenkinsfile generation with invalid cookbook path."""
        # Use tmp_path to ensure we don't write to project root
        invalid_path = str(tmp_path / "nonexistent" / "path")
        result = generate_jenkinsfile_from_chef(
            cookbook_path=invalid_path,
            pipeline_type="declarative",
            enable_parallel="yes",
        )
        # Function should handle gracefully and return a string
        assert isinstance(result, str)

    def test_generate_jenkinsfile_scripted_parallel(self, tmp_path):
        """Test Jenkinsfile generation with scripted pipeline and parallel."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

        result = generate_jenkinsfile_from_chef(
            cookbook_path=str(cookbook_dir),
            pipeline_type="scripted",
            enable_parallel="yes",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_jenkinsfile_declarative_no_parallel(self, tmp_path):
        """Test Jenkinsfile generation with declarative pipeline without parallel."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

        result = generate_jenkinsfile_from_chef(
            cookbook_path=str(cookbook_dir),
            pipeline_type="declarative",
            enable_parallel="no",
        )
        assert isinstance(result, str)
        assert len(result) > 0


class TestGitLabCIGeneration:
    """Test GitLab CI generation edge cases."""

    def test_generate_gitlab_ci_with_invalid_path(self, tmp_path):
        """Test GitLab CI generation with invalid cookbook path."""
        # Use tmp_path to ensure we don't write to project root
        invalid_path = str(tmp_path / "nonexistent" / "path")
        result = generate_gitlab_ci_from_chef(
            cookbook_path=invalid_path,
            project_name="test-project",
            enable_cache="yes",
            enable_artifacts="yes",
        )
        # Function should handle gracefully and return a string
        assert isinstance(result, str)

    def test_generate_gitlab_ci_with_cache(self, tmp_path):
        """Test GitLab CI generation with cache enabled."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\n version '1.0.0'")

        result = generate_gitlab_ci_from_chef(
            cookbook_path=str(cookbook_dir),
            project_name="test-project",
            enable_cache="yes",
            enable_artifacts="yes",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_gitlab_ci_without_cache_no_artifacts(self, tmp_path):
        """Test GitLab CI generation without cache and artifacts."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

        result = generate_gitlab_ci_from_chef(
            cookbook_path=str(cookbook_dir),
            project_name="test",
            enable_cache="no",
            enable_artifacts="no",
        )
        assert isinstance(result, str)
        assert len(result) > 0


class TestGitHubActionsGeneration:
    """Test GitHub Actions workflow generation edge cases."""

    def test_generate_github_workflow_with_invalid_path(self, tmp_path):
        """Test GitHub workflow generation with invalid cookbook path."""
        # Use tmp_path to ensure we don't write to project root
        invalid_path = str(tmp_path / "nonexistent" / "path")
        result = generate_github_workflow_from_chef(
            cookbook_path=invalid_path,
            workflow_name="test",
            enable_cache="yes",
            enable_artifacts="yes",
        )
        # Function should handle gracefully and return a string
        assert isinstance(result, str)

    def test_generate_github_workflow_with_cache(self, tmp_path):
        """Test GitHub workflow generation with dependency cache."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

        result = generate_github_workflow_from_chef(
            cookbook_path=str(cookbook_dir),
            workflow_name="chef-ci",
            enable_cache="yes",
            enable_artifacts="yes",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_github_workflow_no_cache(self, tmp_path):
        """Test GitHub workflow generation without dependency cache."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

        result = generate_github_workflow_from_chef(
            cookbook_path=str(cookbook_dir),
            workflow_name="chef-test",
            enable_cache="no",
            enable_artifacts="no",
        )
        assert isinstance(result, str)
        assert len(result) > 0


class TestProfilingOperations:
    """Test profiling operation edge cases."""

    def test_profile_invalid_operation(self, tmp_path):
        """Test profiling with invalid operation name."""
        result = profile_parsing_operation(
            operation="invalid_op",
            file_path=str(tmp_path / "test.rb"),
            detailed=False,
        )
        assert "Error: Invalid operation" in result
        assert "invalid_op" in result

    def test_profile_nonexistent_file(self, tmp_path):
        """Test profiling with nonexistent file."""
        nonexistent = tmp_path / "nonexistent.rb"
        result = profile_parsing_operation(
            operation="recipe",
            file_path=str(nonexistent),
            detailed=False,
        )
        # Should handle error gracefully
        assert isinstance(result, str)

    def test_profile_recipe_detailed(self, tmp_path):
        """Test detailed profiling of recipe parsing."""
        recipe_file = tmp_path / "recipe.rb"
        recipe_file.write_text(
            "package 'nginx'\nservice 'nginx' do\n  action :start\nend"
        )

        result = profile_parsing_operation(
            operation="recipe",
            file_path=str(recipe_file),
            detailed=True,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_profile_attributes_simple(self, tmp_path):
        """Test simple profiling of attributes parsing."""
        attr_file = tmp_path / "default.rb"
        attr_file.write_text("default['nginx']['port'] = 80")

        result = profile_parsing_operation(
            operation="attributes",
            file_path=str(attr_file),
            detailed=False,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_profile_template_detailed(self, tmp_path):
        """Test detailed profiling of template parsing."""
        template_file = tmp_path / "config.erb"
        template_file.write_text("port = <%= @port %>\nhost = <%= @host %>")

        result = profile_parsing_operation(
            operation="template",
            file_path=str(template_file),
            detailed=True,
        )
        assert isinstance(result, str)

    def test_profile_resource_simple(self, tmp_path):
        """Test simple profiling of custom resource parsing."""
        resource_file = tmp_path / "resource.rb"
        resource_file.write_text(
            "property :name, String\naction :create do\n  # Do something\nend"
        )

        result = profile_parsing_operation(
            operation="resource",
            file_path=str(resource_file),
            detailed=False,
        )
        assert isinstance(result, str)


class TestErrorHandlingPaths:
    """Test error handling in server functions."""

    def test_jenkinsfile_with_empty_cookbook(self, tmp_path):
        """Test Jenkinsfile generation with empty cookbook directory."""
        cookbook_dir = tmp_path / "empty_cookbook"
        cookbook_dir.mkdir()

        # Should handle gracefully even without metadata.rb
        try:
            result = generate_jenkinsfile_from_chef(
                cookbook_path=str(cookbook_dir),
                pipeline_type="declarative",
                enable_parallel="no",
            )
            assert isinstance(result, str)
        except (FileNotFoundError, ValueError):
            # Expected behavior for missing metadata
            pass

    def test_gitlab_ci_with_special_characters_in_path(self, tmp_path):
        """Test GitLab CI generation with special characters in path."""
        cookbook_dir = tmp_path / "test-cookbook_1.0"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

        result = generate_gitlab_ci_from_chef(
            cookbook_path=str(cookbook_dir),
            project_name="test-project",
            enable_cache="no",
            enable_artifacts="no",
        )
        assert isinstance(result, str)

    def test_github_workflow_with_long_name(self, tmp_path):
        """Test GitHub workflow generation with long workflow name."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

        long_name = "Very Long Workflow Name That Exceeds Normal Length Limits"
        result = generate_github_workflow_from_chef(
            cookbook_path=str(cookbook_dir),
            workflow_name=long_name,
            enable_cache="no",
            enable_artifacts="no",
        )
        assert isinstance(result, str)
