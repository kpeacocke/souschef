"""Integration tests that complement the final coverage-focused unit tests."""

from pathlib import Path

from click.testing import CliRunner

from souschef.cli import cli
from souschef.profiling import generate_cookbook_performance_report


def test_profiling_report_integration(tmp_path: Path) -> None:
    """Generate a real profiling report from a minimal cookbook structure."""
    (tmp_path / "metadata.rb").write_text('name "integration"\nversion "1.0.0"')

    recipes = tmp_path / "recipes"
    recipes.mkdir()
    (recipes / "default.rb").write_text("package 'nginx' do\n  action :install\nend\n")

    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "default.erb").write_text("Hello <%= @name %>")

    report = generate_cookbook_performance_report(str(tmp_path))

    assert report.cookbook_name == tmp_path.name
    assert report.total_time >= 0
    assert report.total_memory >= 0
    assert report.operation_results


def test_cli_ls_integration_lists_real_directory(tmp_path: Path) -> None:
    """CLI ls command should list real directory contents end-to-end."""
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")

    runner = CliRunner()
    result = runner.invoke(cli, ["ls", str(tmp_path)])

    assert result.exit_code == 0
    assert "a.txt" in result.output
    assert "b.txt" in result.output
