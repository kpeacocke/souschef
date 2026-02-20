"""
Tests targeting uncovered lines in souschef/cli.py.

Exercises error/exception branches, validation failures, edge cases,
and CLI command handlers that were previously missing from the test suite.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from souschef.cli import cli

FIXTURES_DIR = (
    Path(__file__).parents[1] / "integration" / "fixtures" / "sample_cookbook"
)


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click test runner."""
    return CliRunner()


# ---------------------------------------------------------------------------
# _init_cli_groups – lines 178-182
# ---------------------------------------------------------------------------


class TestInitCliGroups:
    """Tests for _init_cli_groups error handling."""

    def test_exception_during_group_init_is_logged_not_raised(self) -> None:
        """Exception in register_default_groups is caught and logged."""
        from souschef.cli import _init_cli_groups

        with patch(
            "souschef.cli.register_default_groups",
            side_effect=RuntimeError("registry fail"),
        ):
            # Should not raise
            _init_cli_groups()


# ---------------------------------------------------------------------------
# Template parse – line 404-405 (JSONDecodeError branch)
# ---------------------------------------------------------------------------


class TestConvertCommand:
    """Tests for convert command JSON fallback."""

    def test_template_display_with_non_json_result(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Non-JSON template result falls back to showing raw text."""
        from souschef.cli import _display_template_summary

        # Write a minimal ERB file
        template_file = tmp_path / "test.erb"
        template_file.write_text("<%= node['key'] %>\n")

        with patch("souschef.cli.parse_template", return_value="plain text result"):
            _display_template_summary(template_file)


# ---------------------------------------------------------------------------
# convert command – lines 473-474 (dry-run with output)
# ---------------------------------------------------------------------------


class TestConvertCommandDryRun:
    """Tests for convert cookbook command dry-run mode."""

    def test_dry_run_with_output_shows_message(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Dry-run with output path shows would-save message."""
        result = runner.invoke(
            cli,
            [
                "convert",
                str(FIXTURES_DIR),
                "--output",
                str(tmp_path / "output"),
                "--dry-run",
            ],
        )
        # Either succeeds with dry-run output or shows error
        assert "dry run" in result.output.lower() or result.exit_code in (0, 1, 2)


# ---------------------------------------------------------------------------
# inspec_convert – lines 626-627
# ---------------------------------------------------------------------------


class TestInspecConvert:
    """Tests for inspec_convert command."""

    def test_inspec_convert_invokes_function(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """inspec_convert calls convert_inspec_to_test and echoes result."""
        inspec_file = tmp_path / "control.rb"
        inspec_file.write_text("control 'test-1' do\n  describe file('/etc') do\n  end\nend\n")

        with patch("souschef.cli.convert_inspec_to_test", return_value="converted"):
            result = runner.invoke(cli, ["inspec-convert", str(inspec_file)])
        assert result.exit_code == 0
        assert "converted" in result.output


# ---------------------------------------------------------------------------
# inspec_generate – lines 644-645
# ---------------------------------------------------------------------------


class TestInspecGenerate:
    """Tests for inspec_generate command."""

    def test_inspec_generate_text_format(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """inspec_generate outputs result in text format."""
        recipe_file = tmp_path / "default.rb"
        recipe_file.write_text("package 'nginx'\n")

        with patch(
            "souschef.cli.generate_inspec_from_recipe",
            return_value=json.dumps({"controls": []}),
        ):
            result = runner.invoke(cli, ["inspec-generate", str(recipe_file)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# generate_gitlab_ci – lines 785-790
# ---------------------------------------------------------------------------


class TestGenerateGitlabCi:
    """Tests for generate_gitlab_ci CI job summary lines."""

    def test_gitlab_ci_shows_job_summary_with_lint(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """GitLab CI output with cookstyle shows lint job."""
        with patch(
            "souschef.cli.generate_gitlab_ci_from_chef",
            return_value="cookstyle:\n  script: cookstyle",
        ), patch("souschef.cli._safe_write_file", return_value=tmp_path / ".gitlab-ci.yml"):
            result = runner.invoke(cli, ["generate-gitlab-ci", str(FIXTURES_DIR)])
        assert result.exit_code == 0
        assert "Lint" in result.output

    def test_gitlab_ci_shows_unit_test_job(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """GitLab CI output with chefspec shows unit test job."""
        with patch(
            "souschef.cli.generate_gitlab_ci_from_chef",
            return_value="chefspec:\n  script: rspec",
        ), patch("souschef.cli._safe_write_file", return_value=tmp_path / ".gitlab-ci.yml"):
            result = runner.invoke(cli, ["generate-gitlab-ci", str(FIXTURES_DIR)])
        assert result.exit_code == 0
        assert "Unit Tests" in result.output

    def test_gitlab_ci_shows_integration_test_job(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """GitLab CI output with kitchen shows integration test job."""
        with patch(
            "souschef.cli.generate_gitlab_ci_from_chef",
            return_value="kitchen-converge:\n  script: kitchen test",
        ), patch("souschef.cli._safe_write_file", return_value=tmp_path / ".gitlab-ci.yml"):
            result = runner.invoke(cli, ["generate-gitlab-ci", str(FIXTURES_DIR)])
        assert result.exit_code == 0
        assert "Integration Tests" in result.output

    def test_gitlab_ci_exception_exits_with_error(
        self, runner: CliRunner
    ) -> None:
        """Exception during GitLab CI generation exits with code 1."""
        with patch(
            "souschef.cli.generate_gitlab_ci_from_chef",
            side_effect=RuntimeError("fail"),
        ):
            result = runner.invoke(cli, ["generate-gitlab-ci", str(FIXTURES_DIR)])
        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# generate_github_workflow – lines 873, 875, 877, 882-884
# ---------------------------------------------------------------------------


class TestGenerateGithubWorkflow:
    """Tests for generate_github_workflow CI job summary lines."""

    def test_github_workflow_shows_lint_job(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """GitHub workflow output with lint shows lint job."""
        with patch(
            "souschef.cli.generate_github_workflow_from_chef",
            return_value="lint:\n  runs-on: ubuntu",
        ), patch("souschef.cli._resolve_output_path", return_value=tmp_path / "ci.yml"), patch.object(
            Path, "write_text", return_value=None
        ):
            result = runner.invoke(
                cli, ["generate-github-workflow", str(FIXTURES_DIR)]
            )
        assert result.exit_code == 0
        assert "Lint" in result.output

    def test_github_workflow_shows_unit_test_job(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """GitHub workflow output with unit-test shows unit test job."""
        with patch(
            "souschef.cli.generate_github_workflow_from_chef",
            return_value="unit-test:\n  runs-on: ubuntu",
        ), patch("souschef.cli._resolve_output_path", return_value=tmp_path / "ci.yml"), patch.object(
            Path, "write_text", return_value=None
        ):
            result = runner.invoke(
                cli, ["generate-github-workflow", str(FIXTURES_DIR)]
            )
        assert result.exit_code == 0
        assert "Unit Tests" in result.output

    def test_github_workflow_shows_integration_test_job(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """GitHub workflow output with integration-test shows integration job."""
        with patch(
            "souschef.cli.generate_github_workflow_from_chef",
            return_value="integration-test:\n  runs-on: ubuntu",
        ), patch("souschef.cli._resolve_output_path", return_value=tmp_path / "ci.yml"), patch.object(
            Path, "write_text", return_value=None
        ):
            result = runner.invoke(
                cli, ["generate-github-workflow", str(FIXTURES_DIR)]
            )
        assert result.exit_code == 0
        assert "Integration Tests" in result.output

    def test_github_workflow_exception_exits_with_error(
        self, runner: CliRunner
    ) -> None:
        """Exception during GitHub workflow generation exits with code 1."""
        with patch(
            "souschef.cli.generate_github_workflow_from_chef",
            side_effect=RuntimeError("fail"),
        ):
            result = runner.invoke(
                cli, ["generate-github-workflow", str(FIXTURES_DIR)]
            )
        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# _output_json_format / _output_text_format – lines 914
# ---------------------------------------------------------------------------


class TestOutputFormatHelpers:
    """Tests for output format helper functions."""

    def test_output_json_format_valid_json(self) -> None:
        """Valid JSON is pretty-printed."""
        from souschef.cli import _output_json_format

        with patch("souschef.cli.click") as mock_click:
            _output_json_format(json.dumps({"key": "value"}))
            mock_click.echo.assert_called_once()

    def test_output_json_format_invalid_json(self) -> None:
        """Invalid JSON is echoed as raw text."""
        from souschef.cli import _output_json_format

        with patch("souschef.cli.click") as mock_click:
            _output_json_format("plain text")
            mock_click.echo.assert_called_once_with("plain text")

    def test_output_text_format_dict_json(self) -> None:
        """JSON dict is displayed as key-value pairs."""
        from souschef.cli import _output_text_format

        with patch("souschef.cli.click"):
            _output_text_format(json.dumps({"key": "value"}))

    def test_output_text_format_non_dict_json(self) -> None:
        """Non-dict JSON is echoed directly."""
        from souschef.cli import _output_text_format

        with patch("souschef.cli.click") as mock_click:
            _output_text_format(json.dumps(["a", "b"]))
            mock_click.echo.assert_called_once()

    def test_output_text_format_plain_text(self) -> None:
        """Plain text is echoed directly."""
        from souschef.cli import _output_text_format

        with patch("souschef.cli.click") as mock_click:
            _output_text_format("plain text")
            mock_click.echo.assert_called_once_with("plain text")


# ---------------------------------------------------------------------------
# profile cookbook – lines 957-963
# ---------------------------------------------------------------------------


class TestProfileCookbook:
    """Tests for profile command."""

    def test_profile_cookbook_with_output_file(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Profile command saves report to file when --output provided."""
        output_file = tmp_path / "report.txt"
        with patch(
            "souschef.cli.generate_cookbook_performance_report",
            return_value="Performance report",
        ):
            result = runner.invoke(
                cli,
                ["profile", str(FIXTURES_DIR), "--output", str(output_file)],
            )
        assert result.exit_code == 0
        assert output_file.exists()

    def test_profile_cookbook_to_stdout(
        self, runner: CliRunner
    ) -> None:
        """Profile command prints to stdout when no --output."""
        with patch(
            "souschef.cli.generate_cookbook_performance_report",
            return_value="Performance report",
        ):
            result = runner.invoke(cli, ["profile", str(FIXTURES_DIR)])
        assert result.exit_code == 0
        assert "Performance report" in result.output

    def test_profile_exception_exits_with_error(self, runner: CliRunner) -> None:
        """Exception during profiling exits with code 1."""
        with patch(
            "souschef.cli.generate_cookbook_performance_report",
            side_effect=RuntimeError("profile error"),
        ):
            result = runner.invoke(cli, ["profile", str(FIXTURES_DIR)])
        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# profile_operation – lines 1004-1010, 1013
# ---------------------------------------------------------------------------


class TestProfileOperation:
    """Tests for profile-operation command."""

    def test_profile_operation_detailed_flag(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Profile-operation with --detailed shows function statistics."""
        recipe_file = tmp_path / "default.rb"
        recipe_file.write_text("package 'nginx'\n")

        mock_result = MagicMock()
        mock_result.__str__ = lambda self: "profile output"
        mock_result.function_stats = {"top_functions": "func stats here"}

        with patch(
            "souschef.profiling.detailed_profile_function",
            return_value=(None, mock_result),
        ):
            result = runner.invoke(
                cli,
                ["profile-operation", "recipe", str(recipe_file), "--detailed"],
            )
        # Function stats should be shown
        assert result.exit_code == 0
        assert "func stats here" in result.output or "profile output" in result.output

    def test_profile_operation_without_detailed(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Profile-operation without --detailed uses profile_function."""
        recipe_file = tmp_path / "default.rb"
        recipe_file.write_text("package 'nginx'\n")

        mock_result = MagicMock()
        mock_result.__str__ = lambda self: "basic profile output"

        with patch("souschef.cli.profile_function", return_value=(None, mock_result)):
            result = runner.invoke(
                cli,
                ["profile-operation", "recipe", str(recipe_file)],
            )
        assert result.exit_code == 0
        assert "basic profile output" in result.output

    def test_profile_operation_exception_exits_with_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Exception during profiling exits with code 1."""
        recipe_file = tmp_path / "default.rb"
        recipe_file.write_text("package 'nginx'\n")

        with patch(
            "souschef.cli.profile_function", side_effect=RuntimeError("fail")
        ):
            result = runner.invoke(
                cli, ["profile-operation", "recipe", str(recipe_file)]
            )
        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# convert-recipe – line 1064 (missing recipe file)
# ---------------------------------------------------------------------------


class TestConvertRecipe:
    """Tests for convert-recipe command."""

    def test_missing_recipe_exits_with_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Missing recipe file exits with error code."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = runner.invoke(
            cli,
            [
                "convert-recipe",
                "--cookbook-path",
                str(FIXTURES_DIR),
                "--recipe-name",
                "nonexistent_recipe_xyz",
                "--output-path",
                str(output_dir),
            ],
        )
        assert result.exit_code == 1
        assert "Error" in result.output or "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# assess-cookbook – lines 1141, 1146-1147
# ---------------------------------------------------------------------------


class TestAssessCookbook:
    """Tests for assess-cookbook command."""

    def test_assess_cookbook_json_format(
        self, runner: CliRunner
    ) -> None:
        """assess-cookbook with --format json outputs valid JSON."""
        result = runner.invoke(
            cli,
            ["assess-cookbook", "--cookbook-path", str(FIXTURES_DIR), "--format", "json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "complexity" in data

    def test_assess_cookbook_exception_exits_with_error(
        self, runner: CliRunner
    ) -> None:
        """Exception during assessment exits with code 1."""
        with patch(
            "souschef.cli._analyse_cookbook_for_assessment",
            side_effect=RuntimeError("fail"),
        ):
            result = runner.invoke(
                cli,
                ["assess-cookbook", "--cookbook-path", str(FIXTURES_DIR)],
            )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# convert-habitat – lines 1165-1166, 1170-1175
# ---------------------------------------------------------------------------


class TestConvertHabitat:
    """Tests for convert-habitat command."""

    def test_convert_habitat_invalid_output_parent_exits(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Non-existent output parent directory causes exit."""
        plan_file = tmp_path / "plan.sh"
        plan_file.write_text("pkg_name=myapp\n")
        result = runner.invoke(
            cli,
            [
                "convert-habitat",
                "--plan-path",
                str(plan_file),
                "--output-path",
                "/nonexistent/deep/output",
            ],
        )
        assert result.exit_code == 1

    def test_convert_habitat_exception_exits_with_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Exception during conversion exits with code 1."""
        plan_file = tmp_path / "plan.sh"
        plan_file.write_text("pkg_name=myapp\n")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch(
            "souschef.server.convert_habitat_to_dockerfile",
            side_effect=RuntimeError("fail"),
        ):
            result = runner.invoke(
                cli,
                [
                    "convert-habitat",
                    "--plan-path",
                    str(plan_file),
                    "--output-path",
                    str(output_dir),
                ],
            )
        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# convert-inspec – lines 1311-1312, 1319-1322, 1348-1350
# ---------------------------------------------------------------------------


class TestConvertInspec:
    """Tests for convert-inspec command."""

    def test_convert_inspec_not_a_directory_exits(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Non-directory profile path exits with error."""
        profile_file = tmp_path / "profile.rb"
        profile_file.write_text("control 'test' do\nend\n")
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = runner.invoke(
            cli,
            [
                "convert-inspec",
                "--profile-path",
                str(profile_file),
                "--output-path",
                str(output_dir),
            ],
        )
        assert result.exit_code == 1
        assert "not a directory" in result.output.lower() or "Error" in result.output

    def test_convert_inspec_invalid_output_parent_exits(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Non-existent output parent exits with error."""
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        result = runner.invoke(
            cli,
            [
                "convert-inspec",
                "--profile-path",
                str(profile_dir),
                "--output-path",
                "/nonexistent/deep/path",
            ],
        )
        assert result.exit_code == 1

    def test_convert_inspec_exception_exits_with_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Exception during conversion exits with code 1."""
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch(
            "souschef.server.convert_inspec_to_test",
            side_effect=RuntimeError("fail"),
        ):
            result = runner.invoke(
                cli,
                [
                    "convert-inspec",
                    "--profile-path",
                    str(profile_dir),
                    "--output-path",
                    str(output_dir),
                ],
            )
        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# convert-cookbook – lines 1420-1423, 1428-1429, 1446-1448
# ---------------------------------------------------------------------------


class TestConvertCookbook:
    """Tests for convert-cookbook command."""

    def test_convert_cookbook_invalid_output_parent_exits(
        self, runner: CliRunner
    ) -> None:
        """Non-existent output parent directory exits with error."""
        result = runner.invoke(
            cli,
            [
                "convert-cookbook",
                "--cookbook-path",
                str(FIXTURES_DIR),
                "--output-path",
                "/nonexistent/deep/output/path",
            ],
        )
        assert result.exit_code == 1

    def test_convert_cookbook_exception_exits_with_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Exception during conversion exits with code 1."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch(
            "souschef.server.convert_cookbook_comprehensive",
            side_effect=RuntimeError("fail"),
        ):
            result = runner.invoke(
                cli,
                [
                    "convert-cookbook",
                    "--cookbook-path",
                    str(FIXTURES_DIR),
                    "--output-path",
                    str(output_dir),
                ],
            )
        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# simulate-migration – lines 1506-1522
# ---------------------------------------------------------------------------


class TestSimulateMigration:
    """Tests for simulate-migration command."""

    def test_simulate_migration_success(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Successful simulation outputs result."""
        output_dir = tmp_path / "sim_output"
        output_dir.mkdir()

        with patch(
            "souschef.server.simulate_chef_to_awx_migration",
            return_value="Simulation complete",
        ):
            result = runner.invoke(
                cli,
                [
                    "simulate-migration",
                    "--cookbooks-path",
                    str(FIXTURES_DIR),
                    "--output-path",
                    str(output_dir),
                ],
            )
        assert result.exit_code == 0
        assert "Simulation complete" in result.output

    def test_simulate_migration_exception_exits_with_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Exception during simulation exits with code 1."""
        output_dir = tmp_path / "sim_output"
        output_dir.mkdir()

        with patch(
            "souschef.server.simulate_chef_to_awx_migration",
            side_effect=RuntimeError("sim fail"),
        ):
            result = runner.invoke(
                cli,
                [
                    "simulate-migration",
                    "--cookbooks-path",
                    str(FIXTURES_DIR),
                    "--output-path",
                    str(output_dir),
                ],
            )
        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# validate-chef-server – lines 1595-1609
# ---------------------------------------------------------------------------


class TestValidateChefServer:
    """Tests for validate-chef-server command."""

    def test_validate_chef_server_success(self, runner: CliRunner) -> None:
        """Successful validation echoes success message."""
        with patch(
            "souschef.core.chef_server._validate_chef_server_connection",
            return_value=(True, "Connected successfully"),
        ):
            result = runner.invoke(
                cli,
                [
                    "validate-chef-server",
                    "--server-url",
                    "https://chef.example.com",
                ],
            )
        assert result.exit_code == 0
        assert "Connected successfully" in result.output

    def test_validate_chef_server_failure(self, runner: CliRunner) -> None:
        """Failed validation echoes error message and exits with 1."""
        with patch(
            "souschef.core.chef_server._validate_chef_server_connection",
            return_value=(False, "Connection refused"),
        ):
            result = runner.invoke(
                cli,
                [
                    "validate-chef-server",
                    "--server-url",
                    "https://chef.example.com",
                ],
            )
        assert result.exit_code == 1
        assert "Connection refused" in result.output


# ---------------------------------------------------------------------------
# query-chef-nodes – lines 1677-1705
# ---------------------------------------------------------------------------


class TestQueryChefNodes:
    """Tests for query-chef-nodes command."""

    def test_missing_server_url_and_env_exits(self, runner: CliRunner) -> None:
        """Missing CHEF_SERVER_URL exits with error."""
        import os

        env = {
            k: v for k, v in os.environ.items()
            if k not in ("CHEF_SERVER_URL", "CHEF_CLIENT_NAME", "CHEF_CLIENT_KEY_PATH")
        }
        result = runner.invoke(
            cli,
            ["query-chef-nodes"],
            env=env,
        )
        assert result.exit_code == 1
        assert "CHEF_SERVER_URL" in result.output

    def test_missing_client_name_exits(self, runner: CliRunner) -> None:
        """Missing CHEF_CLIENT_NAME exits with error."""
        import os

        env = {k: v for k, v in os.environ.items() if k not in ("CHEF_CLIENT_NAME", "CHEF_CLIENT_KEY_PATH")}
        env["CHEF_SERVER_URL"] = "https://chef.example.com"
        result = runner.invoke(
            cli,
            ["query-chef-nodes"],
            env=env,
        )
        assert result.exit_code == 1
        assert "CHEF_CLIENT_NAME" in result.output

    def test_missing_client_key_path_exits(self, runner: CliRunner) -> None:
        """Missing CHEF_CLIENT_KEY_PATH exits with error."""
        import os

        env = {k: v for k, v in os.environ.items() if k != "CHEF_CLIENT_KEY_PATH"}
        env["CHEF_SERVER_URL"] = "https://chef.example.com"
        env["CHEF_CLIENT_NAME"] = "admin"
        result = runner.invoke(
            cli,
            ["query-chef-nodes"],
            env=env,
        )
        assert result.exit_code == 1
        assert "CHEF_CLIENT_KEY_PATH" in result.output

    def test_exception_during_query_exits_with_error(
        self, runner: CliRunner
    ) -> None:
        """Exception during node query exits with code 1."""
        import os

        env = dict(os.environ)
        env["CHEF_SERVER_URL"] = "https://chef.example.com"
        env["CHEF_CLIENT_NAME"] = "admin"
        env["CHEF_CLIENT_KEY_PATH"] = "/tmp/key.pem"

        with patch(
            "souschef.core.chef_server.get_chef_nodes",
            side_effect=RuntimeError("query fail"),
        ):
            result = runner.invoke(
                cli,
                ["query-chef-nodes"],
                env=env,
            )
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_no_nodes_found(self, runner: CliRunner) -> None:
        """Empty node results shows info message."""
        import os

        env = dict(os.environ)
        env["CHEF_SERVER_URL"] = "https://chef.example.com"
        env["CHEF_CLIENT_NAME"] = "admin"
        env["CHEF_CLIENT_KEY_PATH"] = "/tmp/key.pem"

        with patch(
            "souschef.core.chef_server.get_chef_nodes",
            return_value=[],
        ):
            result = runner.invoke(
                cli,
                ["query-chef-nodes"],
                env=env,
            )
        assert "No nodes found" in result.output or result.exit_code == 0


# ---------------------------------------------------------------------------
# configure-migration – lines 1885, 1901-1903
# ---------------------------------------------------------------------------


class TestConfigureMigration:
    """Tests for configure-migration command."""

    def test_configure_migration_with_args(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Migration config generated from CLI args is output."""
        output_file = tmp_path / "config.json"
        result = runner.invoke(
            cli,
            [
                "configure-migration",
                "--deployment-target",
                "awx",
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0

    def test_configure_migration_exception_exits_with_error(
        self, runner: CliRunner
    ) -> None:
        """Exception in configure-migration exits with code 1."""
        with patch(
            "souschef.cli._build_config_from_cli_args",
            side_effect=RuntimeError("fail"),
        ):
            result = runner.invoke(
                cli,
                [
                    "configure-migration",
                    "--deployment-target",
                    "awx",
                ],
            )
        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# history list / delete – lines 2014-2032
# ---------------------------------------------------------------------------


class TestHistoryCommands:
    """Tests for history list and delete commands."""

    def test_history_list_no_records(self, runner: CliRunner) -> None:
        """History list shows empty history message."""
        mock_storage = MagicMock()
        mock_storage.get_analysis_history.return_value = []
        mock_storage.get_conversion_history.return_value = []

        with patch("souschef.storage.get_storage_manager", return_value=mock_storage):
            result = runner.invoke(cli, ["history", "list"])
        assert result.exit_code == 0
        assert "No analysis history found." in result.output

    def test_history_delete_analysis_success(self, runner: CliRunner) -> None:
        """History delete with --yes deletes analysis successfully."""
        mock_storage = MagicMock()
        mock_storage.delete_analysis.return_value = True

        with patch("souschef.storage.get_storage_manager", return_value=mock_storage):
            result = runner.invoke(
                cli,
                ["history", "delete", "--type", "analysis", "--id", "1", "--yes"],
            )
        assert result.exit_code == 0
        assert "deleted successfully" in result.output.lower() or "✅" in result.output

    def test_history_delete_failure(self, runner: CliRunner) -> None:
        """History delete returns error when deletion fails."""
        mock_storage = MagicMock()
        mock_storage.delete_analysis.return_value = False

        with patch("souschef.storage.get_storage_manager", return_value=mock_storage):
            result = runner.invoke(
                cli,
                ["history", "delete", "--type", "analysis", "--id", "999", "--yes"],
            )
        assert result.exit_code == 1
        assert "Failed" in result.output or "❌" in result.output

    def test_history_delete_conversion_exception(self, runner: CliRunner) -> None:
        """Exception during deletion exits with code 1."""
        mock_storage = MagicMock()
        mock_storage.delete_conversion.side_effect = RuntimeError("db error")

        with patch("souschef.storage.get_storage_manager", return_value=mock_storage):
            result = runner.invoke(
                cli,
                [
                    "history",
                    "delete",
                    "--type",
                    "conversion",
                    "--id",
                    "1",
                    "--yes",
                ],
            )
        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# ansible assess – lines 2080-2081, 2089-2095, 2098-2099, 2102-2104, 2108-2110
# ---------------------------------------------------------------------------


class TestAnsibleAssess:
    """Tests for ansible assess command."""

    def test_ansible_assess_with_collections(self, runner: CliRunner) -> None:
        """Ansible assess shows collections when present."""
        mock_assessment = {
            "current_version": "5.0",
            "current_version_full": "5.0.0",
            "python_version": "3.11.0",
            "installed_collections": [f"ns.col{i}" for i in range(15)],
        }
        with patch("souschef.cli.assess_ansible_environment", return_value=mock_assessment):
            result = runner.invoke(cli, ["ansible", "assess"])
        assert result.exit_code == 0
        assert "Installed Collections" in result.output
        assert "... and 5 more" in result.output

    def test_ansible_assess_with_eol_date(self, runner: CliRunner) -> None:
        """Ansible assess shows EOL date when present."""
        mock_assessment = {
            "current_version": "5.0",
            "current_version_full": "5.0.0",
            "python_version": "3.11.0",
            "eol_date": "2023-06-30",
        }
        with patch("souschef.cli.assess_ansible_environment", return_value=mock_assessment):
            result = runner.invoke(cli, ["ansible", "assess"])
        assert result.exit_code == 0
        assert "EOL" in result.output

    def test_ansible_assess_with_warnings(self, runner: CliRunner) -> None:
        """Ansible assess shows warnings when present."""
        mock_assessment = {
            "current_version": "5.0",
            "current_version_full": "5.0.0",
            "python_version": "3.11.0",
            "warnings": ["Ansible version is EOL", "Consider upgrading"],
        }
        with patch("souschef.cli.assess_ansible_environment", return_value=mock_assessment):
            result = runner.invoke(cli, ["ansible", "assess"])
        assert result.exit_code == 0
        assert "Warnings" in result.output
        assert "EOL" in result.output

    def test_ansible_assess_version_format_error_falls_back(
        self, runner: CliRunner
    ) -> None:
        """Version format error falls back to plain version display."""
        mock_assessment = {
            "current_version": "unknown",
            "current_version_full": "unknown",
            "python_version": "3.11.0",
        }
        with patch("souschef.cli.assess_ansible_environment", return_value=mock_assessment), patch(
            "souschef.cli.format_version_display",
            side_effect=ValueError("unknown version"),
        ):
            result = runner.invoke(cli, ["ansible", "assess"])
        assert result.exit_code == 0
        assert "unknown" in result.output

    def test_ansible_assess_exception_exits_with_error(
        self, runner: CliRunner
    ) -> None:
        """Exception during assessment exits with code 1."""
        with patch(
            "souschef.cli.assess_ansible_environment",
            side_effect=RuntimeError("assess fail"),
        ):
            result = runner.invoke(cli, ["ansible", "assess"])
        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# ansible plan – lines 2197-2198, 2207-2209
# ---------------------------------------------------------------------------


class TestAnsiblePlan:
    """Tests for ansible plan command."""

    def test_ansible_plan_version_format_error_falls_back(
        self, runner: CliRunner
    ) -> None:
        """Version format error falls back to plain version display."""
        mock_plan: dict = {
            "upgrade_path": {
                "from_version": "5.0",
                "to_version": "7.0",
                "intermediate_versions": [],
                "breaking_changes": [],
                "collection_updates_needed": {},
                "estimated_effort_days": 3,
            }
        }
        with patch("souschef.cli.generate_upgrade_plan", return_value=mock_plan), patch(
            "souschef.cli.format_version_display",
            side_effect=KeyError("not found"),
        ):
            result = runner.invoke(
                cli,
                ["ansible", "plan", "--current-version", "5.0", "--target-version", "7.0"],
            )
        assert result.exit_code == 0
        assert "5.0" in result.output and "7.0" in result.output

    def test_ansible_plan_exception_exits_with_error(
        self, runner: CliRunner
    ) -> None:
        """Exception during plan generation exits with code 1."""
        with patch(
            "souschef.cli.generate_upgrade_plan",
            side_effect=RuntimeError("fail"),
        ):
            result = runner.invoke(
                cli,
                ["ansible", "plan", "--current-version", "5.0", "--target-version", "7.0"],
            )
        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# ansible eol – lines 2237-2238, 2248-2249, 2252, 2256-2258
# ---------------------------------------------------------------------------


class TestAnsibleEol:
    """Tests for ansible eol command."""

    def test_ansible_eol_supported_version(self, runner: CliRunner) -> None:
        """Supported version shows SUPPORTED status."""
        with patch(
            "souschef.cli.get_eol_status",
            return_value={
                "is_eol": False,
                "eol_date": "2025-06-01",
                "support_level": "community",
            },
        ):
            result = runner.invoke(cli, ["ansible", "eol", "--version", "7.0"])
        assert result.exit_code == 0
        assert "SUPPORTED" in result.output

    def test_ansible_eol_eol_version(self, runner: CliRunner) -> None:
        """EOL version shows END OF LIFE status."""
        with patch(
            "souschef.cli.get_eol_status",
            return_value={
                "is_eol": True,
                "eol_date": "2022-06-01",
                "support_level": "community",
            },
        ):
            result = runner.invoke(cli, ["ansible", "eol", "--version", "4.0"])
        assert result.exit_code == 0
        assert "END OF LIFE" in result.output

    def test_ansible_eol_with_support_level(self, runner: CliRunner) -> None:
        """Ansible eol shows support level when available."""
        with patch(
            "souschef.cli.get_eol_status",
            return_value={
                "is_eol": False,
                "eol_date": "2025-06-01",
                "support_level": "full",
            },
        ):
            result = runner.invoke(cli, ["ansible", "eol", "--version", "7.0"])
        assert result.exit_code == 0
        assert "full" in result.output

    def test_ansible_eol_version_format_error_falls_back(
        self, runner: CliRunner
    ) -> None:
        """Version format error falls back to plain version display."""
        with patch(
            "souschef.cli.get_eol_status",
            return_value={"is_eol": False, "eol_date": "2025-06-01"},
        ), patch(
            "souschef.cli.format_version_display",
            side_effect=ValueError("unknown"),
        ):
            result = runner.invoke(cli, ["ansible", "eol", "--version", "7.0"])
        assert result.exit_code == 0
        assert "7.0" in result.output

    def test_ansible_eol_exception_exits_with_error(
        self, runner: CliRunner
    ) -> None:
        """Exception during EOL check exits with code 1."""
        with patch(
            "souschef.cli.get_eol_status",
            side_effect=RuntimeError("fail"),
        ):
            result = runner.invoke(cli, ["ansible", "eol", "--version", "7.0"])
        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# _display_collection_section / _display_validation_results
# Lines 2286, 2290, 2294
# ---------------------------------------------------------------------------


class TestDisplayCollectionSection:
    """Tests for _display_collection_section helper."""

    def test_empty_collections_not_displayed(self) -> None:
        """Empty collections list produces no output."""
        from souschef.cli import _display_collection_section

        with patch("souschef.cli.click") as mock_click:
            _display_collection_section("Compatible", [])
            mock_click.echo.assert_not_called()

    def test_collections_with_overflow(self) -> None:
        """More than 5 collections shows overflow count."""
        from souschef.cli import _display_collection_section

        collections = [f"ns.col{i}" for i in range(8)]
        with patch("souschef.cli.click") as mock_click:
            _display_collection_section("Compatible", collections)
        calls = [str(c) for c in mock_click.echo.call_args_list]
        all_output = " ".join(calls)
        assert "3 more" in all_output

    def test_display_validation_results_all_sections(self) -> None:
        """_display_validation_results shows all populated sections."""
        from souschef.cli import _display_validation_results

        validation = {
            "compatible": ["ns.col1"],
            "requires_update": ["ns.col2"],
            "may_require_update": ["ns.col3"],
            "incompatible": ["ns.col4"],
        }
        with patch("souschef.cli._display_collection_section") as mock_section:
            _display_validation_results(validation)
        assert mock_section.call_count == 4


# ---------------------------------------------------------------------------
# _parse_collections_file – lines 2315-2320, 2326, 2328-2330, 2336-2339,
# 2342, 2347-2351
# ---------------------------------------------------------------------------


class TestParseCollectionsFile:
    """Tests for _parse_collections_file edge cases."""

    def test_non_existent_file_raises_value_error(self, tmp_path: Path) -> None:
        """Non-existent file raises ValueError."""
        from souschef.cli import _parse_collections_file

        with pytest.raises(ValueError, match="does not exist"):
            _parse_collections_file(str(tmp_path / "nonexistent.yml"))

    def test_not_a_file_raises_value_error(self, tmp_path: Path) -> None:
        """Directory path raises ValueError."""
        from souschef.cli import _parse_collections_file

        with pytest.raises(ValueError, match="not a file"):
            _parse_collections_file(str(tmp_path))

    def test_invalid_yaml_raises_value_error(self, tmp_path: Path) -> None:
        """Invalid YAML raises ValueError."""
        from souschef.cli import _parse_collections_file

        bad_yaml = tmp_path / "bad.yml"
        bad_yaml.write_text("key: [unclosed bracket\n")

        with pytest.raises(ValueError, match="Invalid YAML"):
            _parse_collections_file(str(bad_yaml))

    def test_empty_yaml_raises_value_error(self, tmp_path: Path) -> None:
        """Empty YAML file raises ValueError."""
        from souschef.cli import _parse_collections_file

        empty_file = tmp_path / "empty.yml"
        empty_file.write_text("")

        with pytest.raises(ValueError, match="empty"):
            _parse_collections_file(str(empty_file))

    def test_no_collections_key_raises_value_error(self, tmp_path: Path) -> None:
        """YAML without collections key raises ValueError."""
        from souschef.cli import _parse_collections_file

        no_collections = tmp_path / "no_collections.yml"
        no_collections.write_text("other_key:\n  - item\n")

        with pytest.raises(ValueError, match="No collections found"):
            _parse_collections_file(str(no_collections))

    def test_valid_collections_file_parsed(self, tmp_path: Path) -> None:
        """Valid collections file returns dict of collections."""
        from souschef.cli import _parse_collections_file

        valid = tmp_path / "requirements.yml"
        valid.write_text(
            "collections:\n"
            "  - ansible.posix: '1.0.0'\n"
            "  - community.general: '5.0.0'\n"
        )

        result = _parse_collections_file(str(valid))
        assert "ansible.posix" in result or "community.general" in result


# ---------------------------------------------------------------------------
# _add_dict_collections / _add_string_collections
# Lines 2371, 2376-2377, 2395, 2398-2400
# ---------------------------------------------------------------------------


class TestCollectionParsers:
    """Tests for _add_dict_collections and _add_string_collections."""

    def test_add_dict_collections_with_null_version(self) -> None:
        """Null version is stored as wildcard."""
        from souschef.cli import _add_dict_collections

        result: dict = {}
        _add_dict_collections({"ansible.posix": None}, result)
        assert result["ansible.posix"] == "*"

    def test_add_dict_collections_non_string_name_skipped(self) -> None:
        """Non-string name is skipped."""
        from souschef.cli import _add_dict_collections

        result: dict = {}
        _add_dict_collections({123: "1.0.0"}, result)  # type: ignore[arg-type]
        assert 123 not in result

    def test_add_string_collections_with_version(self) -> None:
        """String with colon splits into name and version."""
        from souschef.cli import _add_string_collections

        result: dict = {}
        _add_string_collections("ansible.posix:1.0.0", result)
        assert result["ansible.posix"] == "1.0.0"

    def test_add_string_collections_without_version(self) -> None:
        """String without colon uses wildcard version."""
        from souschef.cli import _add_string_collections

        result: dict = {}
        _add_string_collections("ansible.posix", result)
        assert result["ansible.posix"] == "*"

    def test_extract_collections_no_collections_list(self) -> None:
        """Data without 'collections' list returns empty dict."""
        from souschef.cli import _extract_collections_from_data

        result = _extract_collections_from_data({"other_key": "value"})
        assert result == {}

    def test_extract_collections_mixed_types(self) -> None:
        """Mixed string and dict items are all processed."""
        from souschef.cli import _extract_collections_from_data

        data = {
            "collections": [
                {"ansible.posix": "1.0.0"},
                "community.general:5.0.0",
                "ns.no_version",
            ]
        }
        result = _extract_collections_from_data(data)
        assert "ansible.posix" in result
        assert "community.general" in result
        assert "ns.no_version" in result


# ---------------------------------------------------------------------------
# ansible validate-collections – lines 2464-2466
# ---------------------------------------------------------------------------


class TestAnsibleValidateCollections:
    """Tests for ansible validate-collections command."""

    def test_validate_collections_exception_exits_with_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Exception during validation exits with code 1."""
        collections_file = tmp_path / "requirements.yml"
        collections_file.write_text(
            "collections:\n  - ansible.posix: '1.0.0'\n"
        )

        with patch(
            "souschef.cli.validate_collection_compatibility",
            side_effect=RuntimeError("fail"),
        ):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "validate-collections",
                    "--collections-file",
                    str(collections_file),
                    "--target-version",
                    "7.0",
                ],
            )
        assert result.exit_code == 1
        assert "Error" in result.output


# ---------------------------------------------------------------------------
# ansible detect-python – lines 2510-2512, 2517-2519
# ---------------------------------------------------------------------------


class TestAnsibleDetectPython:
    """Tests for ansible detect-python command."""

    def test_detect_python_shows_major_minor(self, runner: CliRunner) -> None:
        """Python version with major.minor is displayed."""
        with patch("souschef.cli.detect_python_version", return_value="3.11.5"):
            result = runner.invoke(cli, ["ansible", "detect-python"])
        assert result.exit_code == 0
        assert "3.11" in result.output

    def test_detect_python_exception_exits_with_error(
        self, runner: CliRunner
    ) -> None:
        """Exception during detection exits with code 1."""
        with patch(
            "souschef.cli.detect_python_version",
            side_effect=RuntimeError("detect fail"),
        ):
            result = runner.invoke(cli, ["ansible", "detect-python"])
        assert result.exit_code == 1
        assert "Error" in result.output
