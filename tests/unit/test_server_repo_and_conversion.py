"""Tests for server repository generation and cookbook conversion tools."""

from pathlib import Path
from unittest.mock import patch

from souschef.server import convert_cookbook_comprehensive, generate_ansible_repository


def test_generate_ansible_repository_auto_requires_cookbook_path() -> None:
    """Auto repo type requires cookbook_path."""
    result = generate_ansible_repository(
        output_path="/tmp/out",
        repo_type="auto",
        cookbook_path="",
        org_name="org",
        init_git="no",
    )

    assert "cookbook_path required" in result


def test_generate_ansible_repository_auto_missing_cookbook() -> None:
    """Auto repo type fails on missing cookbook path."""
    with patch("souschef.server._normalize_path", return_value=Path("/missing")):
        result = generate_ansible_repository(
            output_path="/tmp/out",
            repo_type="auto",
            cookbook_path="/missing",
            org_name="org",
            init_git="no",
        )

    assert "Cookbook path does not exist" in result


def test_generate_ansible_repository_auto_success(tmp_path: Path) -> None:
    """Auto repo type uses analysis and generator."""
    cookbook_dir = tmp_path / "cookbook"
    cookbook_dir.mkdir()

    with (
        patch("souschef.server._normalize_path", return_value=cookbook_dir),
        patch(
            "souschef.generators.repo.analyse_conversion_output",
            return_value="inventory_first",
        ),
        patch(
            "souschef.generators.repo.generate_ansible_repository",
            return_value={"success": True},
        ),
    ):
        result = generate_ansible_repository(
            output_path=str(tmp_path / "out"),
            repo_type="auto",
            cookbook_path=str(cookbook_dir),
            org_name="org",
            init_git="yes",
        )

    assert "success" in result


def test_generate_ansible_repository_explicit_type(tmp_path: Path) -> None:
    """Explicit repo type calls generator directly."""
    output_dir = tmp_path / "out"

    with (
        patch("souschef.server._normalize_path", return_value=output_dir),
        patch(
            "souschef.generators.repo.generate_ansible_repository",
            return_value={"success": True},
        ),
    ):
        result = generate_ansible_repository(
            output_path=str(output_dir),
            repo_type="collection",
            cookbook_path="",
            org_name="org",
            init_git="no",
        )

    assert "success" in result


def test_convert_cookbook_comprehensive_missing_path(tmp_path: Path) -> None:
    """Missing cookbook path returns error string."""
    result = convert_cookbook_comprehensive(
        cookbook_path=str(tmp_path / "missing"),
        output_path=str(tmp_path / "out"),
    )

    assert "Cookbook path does not exist" in result


def test_convert_cookbook_comprehensive_invalid_assessment(tmp_path: Path) -> None:
    """Invalid assessment JSON returns error string."""
    cookbook_dir = tmp_path / "cookbook"
    output_dir = tmp_path / "out"
    cookbook_dir.mkdir()
    output_dir.mkdir()

    result = convert_cookbook_comprehensive(
        cookbook_path=str(cookbook_dir),
        output_path=str(output_dir),
        assessment_data="{bad}",
    )

    assert "Invalid assessment data JSON" in result


def test_convert_cookbook_comprehensive_success(tmp_path: Path) -> None:
    """Successful conversion returns report string."""
    cookbook_dir = tmp_path / "cookbook"
    output_dir = tmp_path / "out"
    cookbook_dir.mkdir()
    output_dir.mkdir()
    (cookbook_dir / "metadata.rb").write_text("name 'demo'")

    with (
        patch("souschef.server._create_role_structure", return_value=output_dir),
        patch("souschef.server._convert_recipes"),
        patch("souschef.server._convert_templates"),
        patch("souschef.server._convert_attributes"),
        patch("souschef.server._create_main_task_file"),
        patch("souschef.server._create_role_metadata"),
    ):
        result = convert_cookbook_comprehensive(
            cookbook_path=str(cookbook_dir),
            output_path=str(output_dir),
        )

    assert "Cookbook Conversion Summary" in result
