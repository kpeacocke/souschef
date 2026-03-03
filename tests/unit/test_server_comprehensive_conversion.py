"""Tests for server-side comprehensive conversion helpers."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from souschef.server import (
    _build_simulated_chef_inventory,
    _build_simulation_runlist,
    _find_cookbook_directories,
    _generate_batch_conversion_report,
    _parse_assessment_data,
    _validate_conversion_paths,
    convert_all_cookbooks_comprehensive,
    simulate_chef_to_awx_migration,
)


def test_validate_conversion_paths_invalid_cookbooks() -> None:
    """Validate conversion paths rejects invalid cookbook path."""
    with (
        patch(
            "souschef.server._ensure_within_base_path", side_effect=ValueError("bad")
        ),
        pytest.raises(ValueError),
    ):
        _validate_conversion_paths("/bad", "/out")


def test_validate_conversion_paths_invalid_output() -> None:
    """Validate conversion paths rejects invalid output path."""
    with (
        patch(
            "souschef.server._ensure_within_base_path",
            side_effect=[Path("/ok"), ValueError("bad output")],
        ),
        patch(
            "souschef.core.path_utils.safe_exists",
            return_value=True,
        ),
        pytest.raises(ValueError),
    ):
        _validate_conversion_paths("/ok", "/bad-output")


def test_parse_assessment_data_invalid_json() -> None:
    """Invalid assessment JSON raises ValueError."""
    with pytest.raises(ValueError):
        _parse_assessment_data("{not json}")


def test_parse_assessment_data_non_dict() -> None:
    """Non-dict assessment JSON returns empty dict."""
    result = _parse_assessment_data("[1, 2, 3]")

    assert result == {}


def test_find_cookbook_directories(tmp_path: Path) -> None:
    """Find cookbook directories based on metadata.rb presence."""
    cookbook_dir = tmp_path / "cookbooks"
    cookbook_dir.mkdir()

    valid = cookbook_dir / "valid"
    valid.mkdir()
    (valid / "metadata.rb").write_text("name 'valid'")

    invalid = cookbook_dir / "invalid"
    invalid.mkdir()

    found = _find_cookbook_directories(cookbook_dir)

    assert valid in found
    assert invalid not in found


def test_convert_all_cookbooks_comprehensive_no_cookbooks(tmp_path: Path) -> None:
    """Return error when no cookbooks found."""
    cookbooks_dir = tmp_path / "cookbooks"
    output_dir = tmp_path / "output"
    cookbooks_dir.mkdir()
    output_dir.mkdir()

    with patch("pathlib.Path.cwd", return_value=tmp_path):
        result = convert_all_cookbooks_comprehensive(
            cookbooks_path=str(cookbooks_dir),
            output_path=str(output_dir),
        )

    assert "No Chef cookbooks found" in result


def test_generate_batch_conversion_report() -> None:
    """Report includes counts and output directory."""
    summary = {
        "total_cookbooks": 2,
        "converted_cookbooks": [
            {
                "cookbook_name": "a",
                "role_name": "a",
                "role_path": "/out/a",
                "converted_files": 1,
                "errors": 0,
                "warnings": 0,
            }
        ],
        "failed_cookbooks": [{"cookbook_name": "b", "error": "boom"}],
        "total_converted_files": 1,
        "total_errors": 1,
        "total_warnings": 0,
    }

    report = _generate_batch_conversion_report(summary, Path("/out"))

    assert "Batch Cookbook Conversion Summary" in report
    assert "Total cookbooks found" in report
    assert "Failed conversions" in report
    assert "Output Directory" in report


def test_build_simulated_inventory_and_runlist(tmp_path: Path) -> None:
    """Build simulated inventory and runlist from cookbook dirs."""
    dirs = [tmp_path / "cb1", tmp_path / "cb2"]
    for d in dirs:
        d.mkdir()

    inventory = _build_simulated_chef_inventory(dirs)
    runlist = _build_simulation_runlist(dirs)

    assert len(inventory["nodes"]) == 2
    assert "recipe[cb1::default]" in runlist
    assert "recipe[cb2::default]" in runlist


def test_simulate_chef_to_awx_migration_invalid_target() -> None:
    """Invalid target platform returns error immediately."""
    result = simulate_chef_to_awx_migration(
        cookbooks_path="/tmp/cookbooks",
        output_path="/tmp/output",
        target_platform="invalid",
    )

    assert "target_platform" in result
    assert "awx" in result


def test_simulate_chef_to_awx_migration_success(tmp_path: Path) -> None:
    """Simulate migration returns success payload for valid inputs."""
    cookbooks_dir = tmp_path / "cookbooks"
    output_dir = tmp_path / "output"
    cookbooks_dir.mkdir()
    output_dir.mkdir()

    cookbook = cookbooks_dir / "demo"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'demo'")

    with (
        patch("pathlib.Path.cwd", return_value=tmp_path),
        patch(
            "souschef.server._generate_migration_report",
            return_value="report",
        ),
        patch(
            "souschef.server._analyse_cookbook_dependencies",
            return_value="deps",
        ),
        patch(
            "souschef.server.convert_all_cookbooks_comprehensive",
            return_value="conversion",
        ),
        patch(
            "souschef.server._generate_awx_project_from_cookbooks",
            return_value="project",
        ),
        patch(
            "souschef.server._generate_awx_job_template_from_cookbook",
            return_value="job_template",
        ),
        patch(
            "souschef.server._generate_awx_workflow_from_chef_runlist",
            return_value="workflow",
        ),
        patch(
            "souschef.server._generate_awx_inventory_source_from_chef",
            return_value="inventory_source",
        ),
    ):
        result = simulate_chef_to_awx_migration(
            cookbooks_path=str(cookbooks_dir),
            output_path=str(output_dir),
            target_platform="awx",
            include_repo=False,
            include_tar=False,
        )

    data = json.loads(result)
    assert data["target_platform"] == "awx"
    assert data["analysis"]["migration_report"] == "report"
    assert data["conversion"]["report"] == "conversion"
    assert data["repository"]["success"] is False
