"""Additional CLI tests targeting uncovered code paths."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from souschef.cli import cli


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestConvertRecipeCommand:
    """Tests for convert-recipe command (lines 1033-1084)."""

    def test_convert_recipe_success_with_metadata(self, runner, tmp_path):
        """Test successful recipe conversion with metadata parsing."""
        # Create test cookbook structure
        cookbook_dir = tmp_path / "test_cookbook"
        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir(parents=True)

        # Create recipe file
        recipe_file = recipes_dir / "default.rb"
        recipe_file.write_text("package 'nginx'")

        # Create metadata file
        metadata_file = cookbook_dir / "metadata.rb"
        metadata_file.write_text("name 'test-cookbook'\nversion '1.0.0'")

        output_dir = tmp_path / "output"

        with patch("souschef.cli.generate_playbook_from_recipe") as mock_gen:
            mock_gen.return_value = "---\n- name: Test playbook\n  tasks:\n    - name: Install nginx\n      package:\n        name: nginx"

            result = runner.invoke(
                cli,
                [
                    "convert-recipe",
                    "--cookbook-path",
                    str(cookbook_dir),
                    "--recipe-name",
                    "default",
                    "--output-path",
                    str(output_dir),
                ],
            )

            assert result.exit_code == 0
            assert "Converting" in result.output
            assert "Playbook written to" in result.output
            mock_gen.assert_called_once()

    def test_convert_recipe_missing_recipe_file(self, runner, tmp_path):
        """Test convert-recipe with missing recipe file."""
        cookbook_dir = tmp_path / "test_cookbook"
        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir(parents=True)

        output_dir = tmp_path / "output"

        result = runner.invoke(
            cli,
            [
                "convert-recipe",
                "--cookbook-path",
                str(cookbook_dir),
                "--recipe-name",
                "nonexistent",
                "--output-path",
                str(output_dir),
            ],
        )

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_convert_recipe_invalid_output_parent(self, runner, tmp_path):
        """Test convert-recipe with invalid output path parent."""
        cookbook_dir = tmp_path / "test_cookbook"
        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir(parents=True)

        recipe_file = recipes_dir / "default.rb"
        recipe_file.write_text("package 'nginx'")

        # Use non-existent parent directory
        invalid_output = "/nonexistent/deep/path/output"

        result = runner.invoke(
            cli,
            [
                "convert-recipe",
                "--cookbook-path",
                str(cookbook_dir),
                "--recipe-name",
                "default",
                "--output-path",
                invalid_output,
            ],
        )

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_convert_recipe_generation_error(self, runner, tmp_path):
        """Test convert-recipe with generation error."""
        cookbook_dir = tmp_path / "test_cookbook"
        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir(parents=True)

        recipe_file = recipes_dir / "default.rb"
        recipe_file.write_text("package 'nginx'")

        output_dir = tmp_path / "output"

        with patch("souschef.cli.generate_playbook_from_recipe") as mock_gen:
            mock_gen.side_effect = RuntimeError("Conversion failed")

            result = runner.invoke(
                cli,
                [
                    "convert-recipe",
                    "--cookbook-path",
                    str(cookbook_dir),
                    "--recipe-name",
                    "default",
                    "--output-path",
                    str(output_dir),
                ],
            )

            assert result.exit_code == 1
            assert "Error converting recipe" in result.output


class TestUICommand:
    """Tests for ui command (lines 1442-1467)."""

    def test_ui_launch_success(self, runner):
        """Test successful UI launch."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(cli, ["ui", "--port", "8501"])

            assert result.exit_code == 0
            assert "Starting SousChef UI" in result.output
            mock_run.assert_called_once()

    def test_ui_subprocess_error(self, runner):
        """Test UI launch with subprocess error."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "streamlit")

            result = runner.invoke(cli, ["ui"])

            assert result.exit_code == 1
            assert "Error starting UI" in result.output

    def test_ui_import_error(self, runner):
        """Test UI launch with missing streamlit."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = ImportError("No module named 'streamlit'")

            result = runner.invoke(cli, ["ui"])

            assert result.exit_code == 1
            assert "Streamlit is not installed" in result.output


class TestJenkinsfileGeneration:
    """Tests for generate-jenkinsfile command (lines 671-708)."""

    def test_generate_jenkinsfile_with_stages(self, runner, tmp_path):
        """Test Jenkinsfile generation showing stage summary."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

        output_file = tmp_path / "Jenkinsfile"

        jenkinsfile_content = """
        pipeline {
            agent any
            stages {
                stage('Lint') {
                    steps { echo 'Linting' }
                }
                stage('Unit Tests') {
                    steps { echo 'Testing' }
                }
                stage('Integration Tests') {
                    steps { echo 'Integration' }
                }
            }
        }
        """

        with patch("souschef.cli.generate_jenkinsfile_from_chef") as mock_gen:
            mock_gen.return_value = jenkinsfile_content

            result = runner.invoke(
                cli,
                [
                    "generate-jenkinsfile",
                    str(cookbook_dir),
                    "--output",
                    str(output_file),
                    "--pipeline-type",
                    "declarative",
                    "--parallel",
                ],
            )

            assert result.exit_code == 0
            assert "Generated Pipeline Stages" in result.output
            assert "Parallel execution: Enabled" in result.output

    def test_generate_jenkinsfile_no_parallel(self, runner, tmp_path):
        """Test Jenkinsfile generation without parallel execution."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

        output_file = tmp_path / "Jenkinsfile"

        with patch("souschef.cli.generate_jenkinsfile_from_chef") as mock_gen:
            mock_gen.return_value = "pipeline { agent any }"

            result = runner.invoke(
                cli,
                [
                    "generate-jenkinsfile",
                    str(cookbook_dir),
                    "--output",
                    str(output_file),
                    "--no-parallel",
                ],
            )

            assert result.exit_code == 0
            assert "Parallel execution: Disabled" in result.output

    def test_generate_jenkinsfile_error(self, runner, tmp_path):
        """Test Jenkinsfile generation with error."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()

        output_file = tmp_path / "Jenkinsfile"

        with patch("souschef.cli.generate_jenkinsfile_from_chef") as mock_gen:
            mock_gen.side_effect = RuntimeError("Generation failed")

            result = runner.invoke(
                cli,
                [
                    "generate-jenkinsfile",
                    str(cookbook_dir),
                    "--output",
                    str(output_file),
                ],
            )

            assert result.exit_code == 1
            assert "Error generating Jenkinsfile" in result.output


class TestGitLabCIGeneration:
    """Tests for generate-gitlab-ci command."""

    def test_generate_gitlab_ci_success(self, runner, tmp_path):
        """Test GitLab CI config generation."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

        output_file = tmp_path / ".gitlab-ci.yml"

        gitlab_content = """
stages:
  - lint
  - test

lint:
  stage: lint
  script:
    - echo "Linting"

test:
  stage: test
  script:
    - echo "Testing"
"""

        with patch("souschef.cli.generate_gitlab_ci_from_chef") as mock_gen:
            mock_gen.return_value = gitlab_content

            result = runner.invoke(
                cli,
                [
                    "generate-gitlab-ci",
                    str(cookbook_dir),
                    "--output",
                    str(output_file),
                ],
            )

            assert result.exit_code == 0
            assert "Generated" in result.output


class TestGitHubActionsGeneration:
    """Tests for generate-github-workflow command."""

    def test_generate_github_workflow_success(self, runner, tmp_path):
        """Test GitHub Actions workflow generation."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

        workflow_content = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
"""

        with patch("souschef.cli.generate_github_workflow_from_chef") as mock_gen:
            mock_gen.return_value = workflow_content

            result = runner.invoke(
                cli,
                [
                    "generate-github-workflow",
                    str(cookbook_dir),
                ],
            )

            assert result.exit_code == 0
            assert "Generated" in result.output
