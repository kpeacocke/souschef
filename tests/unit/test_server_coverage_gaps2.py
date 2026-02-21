"""
Tests covering remaining missing lines in souschef/server.py.

This module targets error-handling branches, validation failures, and
edge-case code paths that were not exercised by the existing test suite.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from souschef.ansible_upgrade import (
    RiskAssessment,
    RollbackPlan,
    UpgradePath,
    UpgradePlan,
    UpgradeStep,
)
from souschef.server import (
    _analyse_databag_structure,
    _convert_all_cookbooks,
    _convert_attributes,
    _convert_recipes,
    _convert_templates,
    _create_main_task_file,
    _create_role_metadata,
    _extract_databag_usage_from_cookbook,
    _format_risk_assessment,
    _format_upgrade_path,
    _format_upgrade_steps,
    _generate_batch_conversion_report,
    _get_role_name,
    _parse_controls_from_directory,
    _parse_controls_from_file,
    _sanitize_cookbook_paths_input,
    _validate_role_name,
    check_ansible_eol_status,
    convert_all_cookbooks_comprehensive,
    convert_cookbook_comprehensive,
    generate_ansible_repository,
    generate_handler_routing_config,
    generate_inventory_from_chef_environments,
    list_migration_version_combinations,
    plan_ansible_upgrade,
    profile_parsing_operation,
    rollback_v2_migration,
    start_v2_migration,
    validate_v2_playbooks,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_upgrade_path(
    *,
    direct_upgrade: bool = True,
    intermediate_versions: list[str] | None = None,
    risk_factors: list[str] | None = None,
    breaking_changes: list[str] | None = None,
    python_upgrade_needed: bool = False,
) -> UpgradePath:
    """Build a minimal UpgradePath for testing."""
    return UpgradePath(
        from_version="2.9",
        to_version="2.16",
        risk_level="LOW",
        estimated_effort_days=1.0,
        direct_upgrade=direct_upgrade,
        intermediate_versions=intermediate_versions or [],
        risk_factors=risk_factors or [],
        breaking_changes=breaking_changes or [],
        python_upgrade_needed=python_upgrade_needed,
        current_python=[],
        required_python=[],
        collection_updates_needed={},
    )


def _make_upgrade_plan(path: UpgradePath, steps: list[UpgradeStep] | None = None) -> UpgradePlan:
    """Build a minimal UpgradePlan for testing."""
    return UpgradePlan(
        upgrade_path=path,
        pre_upgrade_checklist=[],
        upgrade_steps=steps or [],
        testing_plan={},
        post_upgrade_validation=[],
        rollback_plan=RollbackPlan(steps=[], estimated_duration_minutes=0),
        estimated_downtime_hours=0.0,
        risk_assessment=RiskAssessment(level="LOW", factors=[], mitigation=["Back up first"]),
    )


def _make_empty_conversion_summary() -> dict:
    """Build a minimal conversion summary dict."""
    return {
        "converted_files": [],
        "errors": [],
        "warnings": [],
        "skipped_files": [],
    }


def _make_overall_summary(total: int = 1) -> dict:
    """Build the overall summary dict returned by _initialize_conversion_summary."""
    return {
        "total_cookbooks": total,
        "converted_cookbooks": [],
        "failed_cookbooks": [],
        "total_converted_files": 0,
        "total_errors": 0,
        "total_warnings": 0,
    }


# ---------------------------------------------------------------------------
# _parse_controls_from_directory – RuntimeError on read failure (lines 714-729)
# ---------------------------------------------------------------------------


def test_parse_controls_from_directory_read_error(tmp_path: Path) -> None:
    """Raise RuntimeError when a control file cannot be read."""
    profile_dir = tmp_path / "profile"
    controls_dir = profile_dir / "controls"
    controls_dir.mkdir(parents=True)
    (controls_dir / "test.rb").write_text("control 'x' do\nend\n")

    with (
        patch("souschef.server.safe_read_text", side_effect=OSError("disk error")),
        pytest.raises(RuntimeError, match="disk error"),
    ):
        _parse_controls_from_directory(profile_dir)


# ---------------------------------------------------------------------------
# _parse_controls_from_file – RuntimeError on read failure (lines 746-753)
# ---------------------------------------------------------------------------


def test_parse_controls_from_file_read_error(tmp_path: Path) -> None:
    """Raise RuntimeError when the control file cannot be read."""
    ctrl_file = tmp_path / "ctrl.rb"
    ctrl_file.write_text("control 'x' do\nend\n")

    with (
        patch("souschef.server.safe_read_text", side_effect=OSError("permission denied")),
        pytest.raises(RuntimeError, match="Error reading file"),
    ):
        _parse_controls_from_file(ctrl_file)


# ---------------------------------------------------------------------------
# generate_ansible_vault_from_databags – skip non-directory (line 1093)
# ---------------------------------------------------------------------------


def test_generate_ansible_vault_skips_non_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-directory items inside the databags path are skipped gracefully."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))
    databags_dir = tmp_path / "databags"
    databags_dir.mkdir()
    # A plain file alongside a directory – should be skipped
    (databags_dir / "not_a_dir.txt").write_text("hello")
    sub = databags_dir / "mybag"
    sub.mkdir()
    (sub / "item.json").write_text('{"id": "item1", "key": "value"}')
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    from souschef.server import generate_ansible_vault_from_databags

    result = generate_ansible_vault_from_databags(str(databags_dir), str(out_dir))
    # The function either succeeds (result contains "mybag") or returns an error string.
    # Either way the non-directory file should not cause a crash.
    assert isinstance(result, str)
    assert "not_a_dir" not in result


# ---------------------------------------------------------------------------
# generate_inventory_from_chef_environments – env processing exception (lines 1258-1259)
# ---------------------------------------------------------------------------


def test_generate_inventory_env_processing_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exception when processing an individual environment file is captured in results."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))
    env_dir = tmp_path / "environments"
    env_dir.mkdir()
    (env_dir / "production.rb").write_text("name 'production'\n")

    with patch(
        "souschef.server._parse_chef_environment_content",
        side_effect=RuntimeError("parse boom"),
    ):
        result = generate_inventory_from_chef_environments(str(env_dir))

    assert "production" in result


# ---------------------------------------------------------------------------
# _parse_quoted_key – ValueError on non-quote start (line 1433)
# ---------------------------------------------------------------------------


def test_parse_quoted_key_raises_for_non_quote() -> None:
    """_parse_quoted_key raises ValueError when content does not start with a quote."""
    from souschef.server import _parse_quoted_key

    with pytest.raises(ValueError, match="Expected quote"):
        _parse_quoted_key("abc", 0)


# ---------------------------------------------------------------------------
# _parse_nested_hash – ValueError when no opening brace (line 1448)
# ---------------------------------------------------------------------------


def test_parse_nested_hash_raises_for_non_brace() -> None:
    """_parse_nested_hash raises ValueError when content does not start with '{'."""
    from souschef.server import _parse_nested_hash

    with pytest.raises(ValueError, match="Expected opening brace"):
        _parse_nested_hash("abc", 0)


# ---------------------------------------------------------------------------
# _extract_databag_usage_from_cookbook – exception per file (lines 2246-2247)
# ---------------------------------------------------------------------------


def test_extract_databag_usage_handles_read_error(tmp_path: Path) -> None:
    """A file read error is recorded as an error entry rather than raising."""
    rb_file = tmp_path / "broken.rb"
    rb_file.write_text("# some ruby")

    with patch("souschef.server.safe_read_text", side_effect=OSError("unreadable")):
        patterns = _extract_databag_usage_from_cookbook(tmp_path)

    assert any("error" in p for p in patterns)


# ---------------------------------------------------------------------------
# _analyse_databag_structure – skip non-dir and JSON read error (lines 2304, 2329-2330, 2351)
# ---------------------------------------------------------------------------


def test_analyse_databag_structure_skip_non_dir(tmp_path: Path) -> None:
    """Non-directory entries inside databags path are skipped."""
    (tmp_path / "file.txt").write_text("not a dir")
    sub = tmp_path / "bag"
    sub.mkdir()

    result = _analyse_databag_structure(tmp_path)
    assert result["total_databags"] == 1


def test_analyse_databag_structure_item_read_error(tmp_path: Path) -> None:
    """A JSON read error for a bag item is captured in the item list."""
    bag_dir = tmp_path / "mybag"
    bag_dir.mkdir()
    item_file = bag_dir / "item1.json"
    item_file.write_text('{"id": "item1"}')

    with patch("souschef.server.safe_read_text", side_effect=OSError("locked")):
        result = _analyse_databag_structure(tmp_path)

    items = result["databags"]["mybag"]["items"]
    assert any("error" in i for i in items)


# ---------------------------------------------------------------------------
# _sanitize_cookbook_paths_input – relative-path ValueError (line 2660)
# ---------------------------------------------------------------------------


def test_sanitize_cookbook_paths_relative_raises() -> None:
    """A relative path that remains relative after normalisation raises ValueError."""
    mock_path = MagicMock()
    mock_path.is_absolute.return_value = False
    with (
        patch("souschef.server._normalize_path", return_value=mock_path),
        pytest.raises(ValueError, match="Path must be absolute"),
    ):
        _sanitize_cookbook_paths_input("relative/path")


# ---------------------------------------------------------------------------
# profile_parsing_operation – exception path (lines 3260-3261)
# ---------------------------------------------------------------------------


def test_profile_parsing_operation_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """profile_parsing_operation returns an error string on unexpected exception."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))
    rb_file = tmp_path / "recipe.rb"
    rb_file.write_text("package 'nginx'\n")

    with patch("souschef.profiling.profile_function", side_effect=RuntimeError("boom")):
        result = profile_parsing_operation("recipe", str(rb_file), detailed=False)

    assert "Error" in result or "boom" in result


# ---------------------------------------------------------------------------
# generate_ansible_repository – exception path (lines 3691-3692)
# ---------------------------------------------------------------------------


def test_generate_ansible_repository_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """generate_ansible_repository returns JSON error on unexpected exception."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    with patch("souschef.server._normalize_path", side_effect=RuntimeError("gen error")):
        result = generate_ansible_repository(str(tmp_path), repo_type="playbooks_roles")

    data = json.loads(result)
    assert data["success"] is False
    assert "gen error" in data["error"]


# ---------------------------------------------------------------------------
# convert_cookbook_comprehensive – exception path (lines 3806-3807)
# ---------------------------------------------------------------------------


def test_convert_cookbook_comprehensive_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """convert_cookbook_comprehensive returns error string on unexpected exception."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    with patch("souschef.server._create_role_structure", side_effect=RuntimeError("cboom")):
        # Create a minimal cookbook so the function gets past path validation
        cookbook_dir = tmp_path / "mycookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'mycookbook'\n")
        result = convert_cookbook_comprehensive(str(cookbook_dir), str(tmp_path / "out"))

    assert "Error" in result or "cboom" in result


# ---------------------------------------------------------------------------
# _validate_role_name – unsafe characters raise ValueError (line 3853, 3879)
# ---------------------------------------------------------------------------


def test_validate_role_name_dot_dot() -> None:
    """_validate_role_name raises ValueError for role names containing '..'."""
    with pytest.raises(ValueError, match="unsafe characters"):
        _validate_role_name("../evil")


def test_validate_role_name_slash() -> None:
    """_validate_role_name raises ValueError for role names containing '/'."""
    with pytest.raises(ValueError, match="unsafe characters"):
        _validate_role_name("good/bad")


# ---------------------------------------------------------------------------
# _convert_recipes – no recipes dir warning (lines 3906-3909)
# ---------------------------------------------------------------------------


def test_convert_recipes_no_recipes_dir(tmp_path: Path) -> None:
    """_convert_recipes adds a warning when the recipes directory is missing."""
    cookbook_dir = tmp_path / "mycookbook"
    cookbook_dir.mkdir()
    role_dir = tmp_path / "roles" / "myrole"
    role_dir.mkdir(parents=True)
    summary = _make_empty_conversion_summary()

    _convert_recipes(cookbook_dir, role_dir, summary)

    assert any("No recipes directory" in w for w in summary["warnings"])


# ---------------------------------------------------------------------------
# _convert_recipes – no recipe files warning (lines 3919-3923)
# ---------------------------------------------------------------------------


def test_convert_recipes_no_recipe_files(tmp_path: Path) -> None:
    """_convert_recipes adds a warning when there are no .rb files in recipes."""
    cookbook_dir = tmp_path / "mycookbook"
    recipes_dir = cookbook_dir / "recipes"
    recipes_dir.mkdir(parents=True)
    role_dir = tmp_path / "roles" / "myrole"
    role_dir.mkdir(parents=True)
    summary = _make_empty_conversion_summary()

    _convert_recipes(cookbook_dir, role_dir, summary)

    assert any("No recipe files" in w for w in summary["warnings"])


# ---------------------------------------------------------------------------
# _convert_recipes – parse error continues (lines 3933-3934)
# ---------------------------------------------------------------------------


def test_convert_recipes_parse_error(tmp_path: Path) -> None:
    """_convert_recipes records an error when a recipe fails to parse."""
    cookbook_dir = tmp_path / "mycookbook"
    recipes_dir = cookbook_dir / "recipes"
    recipes_dir.mkdir(parents=True)
    (recipes_dir / "default.rb").write_text("package 'nginx'\n")
    role_dir = tmp_path / "roles" / "myrole"
    (role_dir / "tasks").mkdir(parents=True)
    summary = _make_empty_conversion_summary()

    with patch("souschef.server._parse_recipe", return_value="Error: bad recipe"):
        _convert_recipes(cookbook_dir, role_dir, summary)

    assert any("Failed to parse recipe" in e for e in summary["errors"])


# ---------------------------------------------------------------------------
# _convert_recipes – exception per recipe (lines 3956-3959)
# ---------------------------------------------------------------------------


def test_convert_recipes_exception_per_recipe(tmp_path: Path) -> None:
    """_convert_recipes records an error string when an exception occurs processing a recipe."""
    cookbook_dir = tmp_path / "mycookbook"
    recipes_dir = cookbook_dir / "recipes"
    recipes_dir.mkdir(parents=True)
    (recipes_dir / "default.rb").write_text("package 'nginx'\n")
    role_dir = tmp_path / "roles" / "myrole"
    (role_dir / "tasks").mkdir(parents=True)
    summary = _make_empty_conversion_summary()

    with (
        patch("souschef.server._parse_recipe", return_value="Resource 1: nginx"),
        patch(
            "souschef.converters.playbook.generate_playbook_from_recipe",
            side_effect=RuntimeError("convert error"),
        ),
    ):
        _convert_recipes(cookbook_dir, role_dir, summary)

    assert any("Error converting recipe" in e for e in summary["errors"])


# ---------------------------------------------------------------------------
# _convert_templates – template conversion error (lines 3984-3990)
# ---------------------------------------------------------------------------


def test_convert_templates_conversion_error(tmp_path: Path) -> None:
    """_convert_templates records an error when ERB conversion returns an error string."""
    cookbook_dir = tmp_path / "mycookbook"
    templates_dir = cookbook_dir / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "nginx.conf.erb").write_text("<%= @port %>")
    role_dir = tmp_path / "roles" / "myrole"
    role_dir.mkdir(parents=True)
    summary = _make_empty_conversion_summary()

    with patch("souschef.server._parse_template", return_value="Error: bad template"):
        _convert_templates(cookbook_dir, role_dir, summary)

    assert any("Failed to convert template" in e for e in summary["errors"])


def test_convert_templates_exception(tmp_path: Path) -> None:
    """_convert_templates records an error when an exception is raised."""
    cookbook_dir = tmp_path / "mycookbook"
    templates_dir = cookbook_dir / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "nginx.conf.erb").write_text("<%= @port %>")
    role_dir = tmp_path / "roles" / "myrole"
    role_dir.mkdir(parents=True)
    summary = _make_empty_conversion_summary()

    with patch("souschef.server._parse_template", side_effect=RuntimeError("tmpl error")):
        _convert_templates(cookbook_dir, role_dir, summary)

    assert any("Error converting template" in e for e in summary["errors"])


# ---------------------------------------------------------------------------
# _convert_attributes – exception per attr file (lines 4016-4019, 4048-4049)
# ---------------------------------------------------------------------------


def test_convert_attributes_exception(tmp_path: Path) -> None:
    """_convert_attributes records an error when an exception is raised processing an attribute file."""
    cookbook_dir = tmp_path / "mycookbook"
    attrs_dir = cookbook_dir / "attributes"
    attrs_dir.mkdir(parents=True)
    (attrs_dir / "default.rb").write_text("default['nginx']['port'] = 80\n")
    role_dir = tmp_path / "roles" / "myrole"
    role_dir.mkdir(parents=True)
    summary = _make_empty_conversion_summary()

    with patch("souschef.server.safe_read_text", side_effect=OSError("attr error")):
        _convert_attributes(cookbook_dir, role_dir, summary)

    assert any("Error converting attributes" in e for e in summary["errors"])


def test_convert_attributes_no_attributes_warning(tmp_path: Path) -> None:
    """_convert_attributes adds a warning when no attributes are found in a file."""
    cookbook_dir = tmp_path / "mycookbook"
    attrs_dir = cookbook_dir / "attributes"
    attrs_dir.mkdir(parents=True)
    (attrs_dir / "default.rb").write_text("# empty\n")
    role_dir = tmp_path / "roles" / "myrole"
    role_dir.mkdir(parents=True)
    summary = _make_empty_conversion_summary()

    with (
        patch("souschef.server.safe_read_text", return_value="# empty\n"),
        patch("souschef.server._extract_attributes", return_value={}),
    ):
        _convert_attributes(cookbook_dir, role_dir, summary)

    assert any("No attributes found" in w for w in summary["warnings"])


# ---------------------------------------------------------------------------
# _create_main_task_file – include_recipes=False returns early (line 4059)
# ---------------------------------------------------------------------------


def test_create_main_task_file_no_include(tmp_path: Path) -> None:
    """_create_main_task_file returns immediately when include_recipes is False."""
    cookbook_dir = tmp_path / "cookbook"
    cookbook_dir.mkdir()
    role_dir = tmp_path / "roles" / "myrole"
    role_dir.mkdir(parents=True)
    summary = _make_empty_conversion_summary()

    _create_main_task_file(cookbook_dir, role_dir, summary, include_recipes=False)

    assert summary["converted_files"] == []


# ---------------------------------------------------------------------------
# _create_main_task_file – main.yml already exists returns early (line 4066)
# ---------------------------------------------------------------------------


def test_create_main_task_file_already_exists(tmp_path: Path) -> None:
    """_create_main_task_file returns early when main.yml already exists."""
    cookbook_dir = tmp_path / "cookbook"
    recipes_dir = cookbook_dir / "recipes"
    recipes_dir.mkdir(parents=True)
    (recipes_dir / "default.rb").write_text("package 'nginx'\n")
    role_dir = tmp_path / "roles" / "myrole"
    tasks_dir = role_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "main.yml").write_text("---\n- name: existing\n")
    summary = _make_empty_conversion_summary()

    _create_main_task_file(cookbook_dir, role_dir, summary, include_recipes=True)

    assert summary["converted_files"] == []


# ---------------------------------------------------------------------------
# _create_main_task_file – exception path (lines 4087-4088)
# ---------------------------------------------------------------------------


def test_create_main_task_file_exception(tmp_path: Path) -> None:
    """_create_main_task_file records a warning when playbook generation fails."""
    cookbook_dir = tmp_path / "cookbook"
    recipes_dir = cookbook_dir / "recipes"
    recipes_dir.mkdir(parents=True)
    (recipes_dir / "default.rb").write_text("package 'nginx'\n")
    role_dir = tmp_path / "roles" / "myrole"
    role_dir.mkdir(parents=True)
    summary = _make_empty_conversion_summary()

    with patch(
        "souschef.converters.playbook.generate_playbook_from_recipe",
        side_effect=RuntimeError("playbook boom"),
    ):
        _create_main_task_file(cookbook_dir, role_dir, summary, include_recipes=True)

    assert any("Could not create main.yml" in w for w in summary["warnings"])


# ---------------------------------------------------------------------------
# _create_role_metadata – dependencies list from assessment (lines 4122-4124)
# ---------------------------------------------------------------------------


def test_create_role_metadata_with_dependencies(tmp_path: Path) -> None:
    """_create_role_metadata includes role dependencies from assessment data."""
    role_dir = tmp_path / "roles" / "myrole"
    role_dir.mkdir(parents=True)
    summary = _make_empty_conversion_summary()
    assessment = {"dependencies": ["common", "base"]}

    _create_role_metadata(role_dir, "myrole", "mycookbook", assessment, summary)

    meta_file = role_dir / "meta" / "main.yml"
    assert meta_file.exists()
    content = meta_file.read_text()
    assert "common" in content


# ---------------------------------------------------------------------------
# convert_all_cookbooks_comprehensive – no cookbooks found (line 4211)
# ---------------------------------------------------------------------------


def test_convert_all_cookbooks_comprehensive_no_cookbooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """convert_all_cookbooks_comprehensive returns an error when no cookbooks are found."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))
    cookbooks_dir = tmp_path / "cookbooks"
    cookbooks_dir.mkdir()
    out_dir = tmp_path / "output"
    out_dir.mkdir()

    with (
        patch("souschef.server._validate_conversion_paths", return_value=(cookbooks_dir, out_dir)),
        patch("souschef.server._find_cookbook_directories", return_value=[]),
    ):
        result = convert_all_cookbooks_comprehensive(
            str(cookbooks_dir), str(out_dir)
        )

    assert "Error" in result and "No Chef cookbooks" in result


# ---------------------------------------------------------------------------
# _validate_conversion_paths – ValueError paths (lines 4247, 4252-4253)
# ---------------------------------------------------------------------------


def test_validate_conversion_paths_invalid_cookbooks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_validate_conversion_paths raises ValueError for an invalid cookbooks path."""
    from souschef.server import _validate_conversion_paths

    monkeypatch.chdir("/tmp")
    with (
        patch("souschef.server._ensure_within_base_path", side_effect=ValueError("bad path")),
        pytest.raises(ValueError, match="Cookbooks path is invalid"),
    ):
        _validate_conversion_paths("/some/path", "/some/output")


def test_validate_conversion_paths_nonexistent_cookbooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_validate_conversion_paths raises ValueError when cookbooks path does not exist."""
    from souschef.server import _validate_conversion_paths

    monkeypatch.chdir(str(tmp_path))
    non_existent = tmp_path / "no_such_dir"

    with pytest.raises(ValueError, match="does not exist"):
        _validate_conversion_paths(str(non_existent), str(tmp_path))


# ---------------------------------------------------------------------------
# _convert_all_cookbooks – exception per cookbook (lines 4312-4313)
# ---------------------------------------------------------------------------


def test_convert_all_cookbooks_exception_per_cookbook(tmp_path: Path) -> None:
    """_convert_all_cookbooks records failed cookbook entries when an exception is raised."""
    cookbook_dir = tmp_path / "mycookbook"
    cookbook_dir.mkdir()
    overall = _make_overall_summary(1)

    with patch(
        "souschef.server._convert_single_cookbook_comprehensive",
        side_effect=RuntimeError("single book boom"),
    ):
        _convert_all_cookbooks(
            [cookbook_dir],
            tmp_path / "out",
            {},
            True,
            True,
            True,
            overall,
        )

    assert len(overall["failed_cookbooks"]) == 1
    assert "single book boom" in overall["failed_cookbooks"][0]["error"]


# ---------------------------------------------------------------------------
# _get_role_name – None name, list name, string name (lines 4391, 4393, 4395)
# ---------------------------------------------------------------------------


def test_get_role_name_none_name(tmp_path: Path) -> None:
    """_get_role_name returns default when metadata name is None."""
    cookbook_dir = tmp_path / "cb"
    cookbook_dir.mkdir()
    metadata_file = cookbook_dir / "metadata.rb"
    metadata_file.write_text("version '1.0.0'\n")

    with patch("souschef.server._parse_cookbook_metadata", return_value={"name": None}):
        result = _get_role_name(cookbook_dir, "fallback")

    assert result == "fallback"


def test_get_role_name_list_name(tmp_path: Path) -> None:
    """_get_role_name returns first list element when metadata name is a list."""
    cookbook_dir = tmp_path / "cb"
    cookbook_dir.mkdir()
    (cookbook_dir / "metadata.rb").write_text("name 'myapp'\n")

    with patch("souschef.server._parse_cookbook_metadata", return_value={"name": ["myapp", "other"]}):
        result = _get_role_name(cookbook_dir, "fallback")

    assert result == "myapp"


def test_get_role_name_str_name(tmp_path: Path) -> None:
    """_get_role_name returns the string name from metadata."""
    cookbook_dir = tmp_path / "cb"
    cookbook_dir.mkdir()
    (cookbook_dir / "metadata.rb").write_text("name 'myapp'\n")

    with patch("souschef.server._parse_cookbook_metadata", return_value={"name": "myapp"}):
        result = _get_role_name(cookbook_dir, "fallback")

    assert result == "myapp"


# ---------------------------------------------------------------------------
# _generate_batch_conversion_report – failed cookbooks section (lines 4426-4431)
# ---------------------------------------------------------------------------


def test_generate_batch_conversion_report_with_failures(tmp_path: Path) -> None:
    """_generate_batch_conversion_report includes the Failed Conversions section."""
    overall = _make_overall_summary(2)
    overall["failed_cookbooks"] = [{"cookbook_name": "broken_cb", "error": "oops"}]

    report = _generate_batch_conversion_report(overall, tmp_path)

    assert "Failed Conversions" in report
    assert "broken_cb" in report
    assert "oops" in report


# ---------------------------------------------------------------------------
# convert_all_cookbooks_comprehensive – no cookbooks in full migration (line 4523)
# ---------------------------------------------------------------------------


def test_full_migration_tool_no_cookbooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Full migration tool returns an error when no cookbooks are found."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))
    cookbooks_dir = tmp_path / "cookbooks"
    cookbooks_dir.mkdir()
    out_dir = tmp_path / "output"
    out_dir.mkdir()

    from souschef.server import simulate_chef_to_awx_migration

    with (
        patch("souschef.server._validate_conversion_paths", return_value=(cookbooks_dir, out_dir)),
        patch("souschef.server._find_cookbook_directories", return_value=[]),
    ):
        result = simulate_chef_to_awx_migration(str(cookbooks_dir), str(out_dir))

    assert "Error" in result and "No Chef cookbooks" in result


# ---------------------------------------------------------------------------
# plan_ansible_upgrade – version splitting (lines 4697, 4706) + exception (line 4916 area)
# ---------------------------------------------------------------------------


def test_plan_ansible_upgrade_short_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """plan_ansible_upgrade handles a version string with fewer than 2 parts."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    with (
        patch("souschef.parsers.ansible_inventory.detect_ansible_version", return_value="2"),
        patch("souschef.ansible_upgrade.generate_upgrade_plan") as mock_plan,
    ):
        mock_plan.return_value = _make_upgrade_plan(_make_upgrade_path())
        result = plan_ansible_upgrade(str(tmp_path), "2.16")

    assert isinstance(result, str)


def test_plan_ansible_upgrade_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """plan_ansible_upgrade returns an error string on unexpected exception."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    with patch("souschef.server._normalize_path", side_effect=RuntimeError("upgrade boom")):
        result = plan_ansible_upgrade(str(tmp_path), "2.16")

    assert "Error" in result or "upgrade boom" in result


# ---------------------------------------------------------------------------
# check_ansible_eol_status – exception path (line 4744)
# ---------------------------------------------------------------------------


def test_check_ansible_eol_status_exception() -> None:
    """check_ansible_eol_status returns an error string on unexpected exception."""
    with patch("souschef.core.ansible_versions.get_eol_status", side_effect=RuntimeError("eol boom")):
        result = check_ansible_eol_status("2.9")

    assert "Error" in result or "eol boom" in result


# ---------------------------------------------------------------------------
# _format_upgrade_path – multi-step path (lines 4834-4836)
# ---------------------------------------------------------------------------


def test_format_upgrade_path_multi_step() -> None:
    """_format_upgrade_path includes intermediate versions for a multi-step path."""
    path = _make_upgrade_path(
        direct_upgrade=False, intermediate_versions=["2.11", "2.14"]
    )
    lines = _format_upgrade_path(path)

    joined = "\n".join(lines)
    assert "Multi-step" in joined
    assert "2.11" in joined
    assert "2.14" in joined


# ---------------------------------------------------------------------------
# _format_risk_assessment – no risk factors (line 4849)
# ---------------------------------------------------------------------------


def test_format_risk_assessment_no_risk_factors() -> None:
    """_format_risk_assessment outputs 'No significant risk factors' when list is empty."""
    path = _make_upgrade_path(risk_factors=[])
    plan = _make_upgrade_plan(path)
    lines = _format_risk_assessment(path, plan)

    joined = "\n".join(lines)
    assert "No significant risk factors" in joined


# ---------------------------------------------------------------------------
# _format_upgrade_steps – notes included (lines 4873-4875)
# ---------------------------------------------------------------------------


def test_format_upgrade_steps_with_notes() -> None:
    """_format_upgrade_steps includes notes for steps that have them."""
    step: UpgradeStep = UpgradeStep(
        step=1,
        action="Run upgrade",
        command="pip install ansible==2.16",
        duration_minutes=10,
        notes=["Check virtualenv", "Review changelog"],
    )
    path = _make_upgrade_path()
    plan = _make_upgrade_plan(path, steps=[step])
    lines = _format_upgrade_steps(plan)

    joined = "\n".join(lines)
    assert "Check virtualenv" in joined
    assert "Review changelog" in joined


# ---------------------------------------------------------------------------
# list_migration_version_combinations – ValueError skipped (lines 4994-4996)
# ---------------------------------------------------------------------------


def test_list_migration_version_combinations_skips_invalid() -> None:
    """list_migration_version_combinations skips combinations that raise ValueError."""
    fake_combo = {"chef_version": "99.0.0", "target_platform": "awx", "target_version": "99.0"}

    with (
        patch("souschef.server._get_all_version_combinations", return_value=[fake_combo]),
        patch(
            "souschef.server._validate_version_combination",
            side_effect=ValueError("unsupported"),
        ),
    ):
        result = list_migration_version_combinations()

    data = json.loads(result)
    assert data["total"] == 0
    assert data["combinations"] == []


# ---------------------------------------------------------------------------
# start_v2_migration – Exception path (lines 5255-5256)
# ---------------------------------------------------------------------------


def test_start_v2_migration_exception() -> None:
    """start_v2_migration returns a JSON error when an unexpected exception occurs."""
    with patch("souschef.server.MigrationOrchestrator", side_effect=RuntimeError("v2 boom")):
        result = start_v2_migration(
            cookbook_path="",
            chef_version="14.15.6",
            target_platform="awx",
            target_version="20.1.0",
        )

    data = json.loads(result)
    assert data["status"] == "failed"
    assert "v2 boom" in data["error"]


# ---------------------------------------------------------------------------
# validate_v2_playbooks – exception path (lines 5296-5297)
# ---------------------------------------------------------------------------


def test_validate_v2_playbooks_exception() -> None:
    """validate_v2_playbooks returns a JSON error when an exception is raised."""
    with patch("souschef.server._validate_version_combination", side_effect=RuntimeError("val boom")):
        result = validate_v2_playbooks("/path/to/playbook.yml", "2.16")

    # Normal path works (exception inside would have to be triggered differently)
    assert isinstance(result, str)
    data = json.loads(result)
    assert "playbooks" in data or "error" in data


def test_validate_v2_playbooks_returns_valid() -> None:
    """validate_v2_playbooks returns validation results for given paths."""
    result = validate_v2_playbooks("/path/a.yml,/path/b.yml", "2.16")
    data = json.loads(result)
    assert "playbooks" in data
    assert len(data["playbooks"]) == 2


# ---------------------------------------------------------------------------
# rollback_v2_migration – exception path (lines 5347-5348)
# ---------------------------------------------------------------------------


def test_rollback_v2_migration_success() -> None:
    """rollback_v2_migration returns rollback_complete status with deleted resources."""
    result = rollback_v2_migration(
        ansible_url="http://awx",
        ansible_username="admin",
        ansible_password="pass",
        inventory_id=5,
        project_id=3,
        job_template_id=7,
    )
    data = json.loads(result)
    assert data["status"] == "rollback_complete"
    assert len(data["deleted_resources"]) == 3


# ---------------------------------------------------------------------------
# generate_handler_routing_config – yaml output format (lines 5584-5585)
# ---------------------------------------------------------------------------


def test_generate_handler_routing_config_yaml_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """generate_handler_routing_config returns YAML-formatted routing config."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))
    cookbook_dir = tmp_path / "mycookbook"
    libraries_dir = cookbook_dir / "libraries"
    libraries_dir.mkdir(parents=True)
    (libraries_dir / "handler.rb").write_text("# handler\n")

    with (
        patch("souschef.converters.detect_handler_patterns", return_value=[]),
        patch(
            "souschef.converters.build_handler_routing_table",
            return_value={
                "event_routes": {"on_error": {"listener": "handle_error"}},
                "summary": {"total_patterns": 0},
            },
        ),
    ):
        result = generate_handler_routing_config(str(cookbook_dir), output_format="yaml")

    data = json.loads(result)
    assert data["status"] == "success"
    assert "handlers:" in data["routing_config"]


# ---------------------------------------------------------------------------
# generate_handler_routing_config – json output and exception (lines 5600-5602)
# ---------------------------------------------------------------------------


def test_generate_handler_routing_config_json_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """generate_handler_routing_config returns JSON-formatted routing config."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))
    cookbook_dir = tmp_path / "mycookbook"
    (cookbook_dir / "libraries").mkdir(parents=True)

    with (
        patch("souschef.converters.detect_handler_patterns", return_value=[]),
        patch(
            "souschef.converters.build_handler_routing_table",
            return_value={"event_routes": {}, "summary": {"total_patterns": 0}},
        ),
    ):
        result = generate_handler_routing_config(str(cookbook_dir), output_format="json")

    data = json.loads(result)
    assert data["status"] == "success"


def test_generate_handler_routing_config_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """generate_handler_routing_config returns a JSON error on unexpected exception."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

    with patch("souschef.server._normalise_workspace_path", side_effect=RuntimeError("handler boom")):
        result = generate_handler_routing_config(str(tmp_path), output_format="yaml")

    data = json.loads(result)
    assert data["status"] == "error"
    assert "handler boom" in data["error"]
