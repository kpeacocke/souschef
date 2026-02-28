"""CLI tests for convert-template-ai command error paths."""

from unittest.mock import patch

from click.testing import CliRunner

from souschef.cli import cli


def test_convert_template_ai_with_warnings(tmp_path) -> None:
    """convert-template-ai prints warnings when present."""
    erb_file = tmp_path / "config.erb"
    erb_file.write_text("<%= @hostname %>")

    runner = CliRunner()
    result_payload = {
        "success": True,
        "conversion_method": "ai",
        "jinja2_output": "{{ hostname }}",
        "warnings": ["Complex Ruby logic detected"],
    }

    with patch(
        "souschef.converters.template.convert_template_with_ai",
        return_value=result_payload,
    ):
        result = runner.invoke(cli, ["convert-template-ai", str(erb_file)])

    assert result.exit_code == 0
    assert "Warnings" in result.output
    assert "Complex Ruby logic detected" in result.output


def test_convert_template_ai_failure(tmp_path) -> None:
    """convert-template-ai exits with error on failure."""
    erb_file = tmp_path / "config.erb"
    erb_file.write_text("<%= @hostname %>")

    runner = CliRunner()
    result_payload = {
        "success": False,
        "error": "Conversion failed",
    }

    with patch(
        "souschef.converters.template.convert_template_with_ai",
        return_value=result_payload,
    ):
        result = runner.invoke(cli, ["convert-template-ai", str(erb_file)])

    assert result.exit_code != 0
    assert "Conversion failed" in result.output
