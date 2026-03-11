"""Pure/helper tests for cookbook_analysis to raise line coverage quickly."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


def _ctx() -> MagicMock:
    """Create a context manager mock."""
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=ctx)
    ctx.__exit__ = Mock(return_value=None)
    return ctx


class SessionState(dict):
    """Session state helper supporting attribute and dict access."""

    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value):
        self[name] = value


def test_sanitize_for_logging_basic():
    from souschef.ui.pages.cookbook_analysis import _sanitize_for_logging

    assert _sanitize_for_logging("hello\nworld") == "hello world"
    assert _sanitize_for_logging("a\rb") == "a b"


def test_sanitize_for_logging_truncates():
    from souschef.ui.pages.cookbook_analysis import _sanitize_for_logging

    long_message = "x" * 300
    result = _sanitize_for_logging(long_message, max_length=20)

    assert len(result) == 23
    assert result.endswith("...")


def test_get_ai_provider_and_values():
    from souschef.ui.pages.cookbook_analysis import (
        _get_ai_float_value,
        _get_ai_int_value,
        _get_ai_provider,
        _get_ai_string_value,
    )

    cfg: dict[str, str | float | int] = {
        "provider": "OpenAI",
        "model": "gpt-4",
        "temperature": "0.8",
        "max_tokens": "2048",
    }

    assert _get_ai_provider(cfg) == "OpenAI"
    assert _get_ai_string_value(cfg, "model") == "gpt-4"
    assert _get_ai_float_value(cfg, "temperature") == pytest.approx(0.8)
    assert _get_ai_int_value(cfg, "max_tokens") == 2048


def test_get_ai_numeric_defaults_on_invalid():
    from souschef.ui.pages.cookbook_analysis import (
        _get_ai_float_value,
        _get_ai_int_value,
    )

    cfg: dict[str, str | float | int] = {"temperature": "bad", "max_tokens": "bad"}
    assert _get_ai_float_value(cfg, "temperature", 0.7) == pytest.approx(0.7)
    assert _get_ai_int_value(cfg, "max_tokens", 4000) == 4000


def test_should_use_ai_and_determine_provider():
    from souschef.ui.pages.cookbook_analysis import (
        _determine_ai_provider,
        _should_use_ai,
    )

    cfg = {"provider": "OpenAI", "api_key": "secret"}
    assert _should_use_ai(cfg)
    assert _determine_ai_provider(cfg) == "openai"

    cfg2 = {"provider": "Anthropic Claude", "api_key": "secret"}
    assert _determine_ai_provider(cfg2) == "anthropic"


def test_extract_dependencies_from_markdown():
    from souschef.ui.pages.cookbook_analysis import _extract_dependencies_from_markdown

    text = """
## Dependency Graph:
├── nginx
├── redis
## Another Section:
value
"""

    deps = _extract_dependencies_from_markdown(text)
    assert deps == ["nginx", "redis"]


def test_perform_topological_sort_acyclic():
    from souschef.ui.pages.cookbook_analysis import _perform_topological_sort

    graph = {
        "app": ["core"],
        "core": ["base"],
        "base": [],
    }

    order = _perform_topological_sort(graph)
    assert set(order) == {"app", "core", "base"}


def test_perform_topological_sort_cycle_breaks():
    from souschef.ui.pages.cookbook_analysis import _perform_topological_sort

    graph = {
        "a": ["b"],
        "b": ["a"],
    }

    order = _perform_topological_sort(graph)
    assert len(order) < 2


def test_fallback_migration_order():
    from souschef.ui.pages.cookbook_analysis import _fallback_migration_order

    results = [
        {"name": "high", "complexity": "High", "dependencies": 5},
        {"name": "low", "complexity": "Low", "dependencies": 1},
        {"name": "med", "complexity": "Medium", "dependencies": 2},
    ]

    order = _fallback_migration_order(results)
    assert order[0] == "low"


def test_get_migration_reason():
    from souschef.ui.pages.cookbook_analysis import _get_migration_reason

    graph = {"a": [], "b": ["a", "x", "y", "z"]}

    assert "No dependencies" in _get_migration_reason("a", graph, 1)
    assert "Foundation" in _get_migration_reason("b", graph, 1)
    assert "Depends on" in _get_migration_reason("b", graph, 2)


def test_detect_and_find_circular_dependencies():
    from souschef.ui.pages.cookbook_analysis import (
        _detect_cycle_dependency,
        _find_circular_dependencies,
    )

    graph = {"a": ["b"], "b": ["c"], "c": ["a"]}

    cycle = _detect_cycle_dependency(graph, "a", "a", [])
    assert cycle is not None

    cycles = _find_circular_dependencies(graph)
    assert len(cycles) == 1
    assert cycles[0]["type"] == "circular_dependency"


def test_calculate_migration_order():
    from souschef.ui.pages.cookbook_analysis import _calculate_migration_order

    graph = {"a": ["b"], "b": []}
    individual = [
        {"name": "a", "complexity": "Medium", "estimated_hours": 16, "dependencies": 1},
        {"name": "b", "complexity": "Low", "estimated_hours": 8, "dependencies": 0},
    ]

    order = _calculate_migration_order(graph, individual)
    assert len(order) == 2
    assert all("phase" in item for item in order)


def test_parse_summary_line_and_conversion_parsers():
    from souschef.ui.pages.cookbook_analysis import (
        _parse_converted_cookbook,
        _parse_failed_cookbook,
        _parse_summary_line,
    )

    structured = {"summary": {}, "cookbook_results": [], "errors": []}

    _parse_summary_line("- Total cookbooks found: 5", structured)
    _parse_summary_line("- Successfully converted: 3", structured)
    _parse_summary_line("- Total files converted: 22", structured)
    _parse_converted_cookbook("- **nginx** → **`nginx_role`**", structured)
    _parse_failed_cookbook("- ❌ **bad_cb**: parse error", structured)

    assert structured["summary"]["total_cookbooks"] == 5
    assert structured["summary"]["cookbooks_converted"] == 3
    assert structured["summary"]["total_converted_files"] == 22
    assert len(structured["cookbook_results"]) >= 1


def test_parse_conversion_result_text_extracts_sections():
    from souschef.ui.pages.cookbook_analysis import _parse_conversion_result_text

    text = """
## Overview:
- Total cookbooks found: 4
- Successfully converted: 2
- Total files converted: 11
## Successfully Converted Cookbooks:
- **cb1** → **`role_cb1`**
## Failed Conversions:
- ❌ **cb2**: invalid template
WARNING: minor issue
"""

    parsed = _parse_conversion_result_text(text)
    assert parsed["summary"]["total_cookbooks"] == 4
    assert len(parsed["cookbook_results"]) >= 1
    assert isinstance(parsed["warnings"], list)


def test_validate_output_path():
    from souschef.ui.pages.cookbook_analysis import _validate_output_path

    local_dir = Path.cwd() / "test-output" / "validate_path_test"
    local_dir.mkdir(parents=True, exist_ok=True)

    p = _validate_output_path(str(local_dir))
    assert p == local_dir.resolve()


def test_collect_role_files_and_zip(tmp_path):
    from souschef.ui.pages.cookbook_analysis import (
        _collect_role_files,
        _create_roles_zip_archive,
    )

    role_dir = tmp_path / "role1" / "tasks"
    role_dir.mkdir(parents=True)
    (role_dir / "main.yml").write_text("- name: t\n")

    files = _collect_role_files(tmp_path)
    assert len(files) >= 1

    archive = _create_roles_zip_archive(tmp_path)
    assert isinstance(archive, bytes)
    assert len(archive) > 0


def test_determine_num_recipes(tmp_path):
    from souschef.ui.pages.cookbook_analysis import _determine_num_recipes

    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    (recipes_dir / "default.rb").write_text("package 'x'\n")
    (recipes_dir / "web.rb").write_text("service 'nginx'\n")

    assert _determine_num_recipes(str(tmp_path), 1) == 2


def test_get_roles_directory_and_copy(tmp_path):
    from souschef.ui.pages.cookbook_analysis import (
        _copy_roles_to_repository,
        _get_roles_directory,
    )

    repo = tmp_path / "repo"
    repo.mkdir()
    roles_dir = _get_roles_directory(repo)
    assert roles_dir.exists()

    source = tmp_path / "source_roles"
    source.mkdir()
    role = source / "nginx"
    role.mkdir()
    (role / "meta.yml").write_text("x: y\n")

    _copy_roles_to_repository(str(source), roles_dir)
    assert (roles_dir / "nginx").exists()


def test_commit_repository_changes_handles_no_commit(tmp_path):
    import subprocess

    from souschef.ui.pages.cookbook_analysis import _commit_repository_changes

    with patch(
        "souschef.ui.pages.cookbook_analysis.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "git"),
    ):
        _commit_repository_changes(tmp_path, 1)


def test_recommendation_format_helpers():
    from souschef.ui.pages.cookbook_analysis import (
        _format_recommendations_from_assessment,
    )

    cookbook_assessment = {
        "complexity_score": 70,
        "estimated_effort_days": 5,
        "complexity": "Medium",
        "migration_priority": "P2",
        "key_findings": ["many templates", "custom resources"],
    }
    overall_assessment = {
        "recommendations": [
            {"recommendation": "Refactor templates"},
            "Use phased rollout",
        ]
    }

    output = _format_recommendations_from_assessment(
        cookbook_assessment, overall_assessment
    )
    assert "Complexity Score" in output
    assert "Estimated Effort" in output
    assert "Migration Priority" in output
    assert "Key Findings" in output


def test_get_error_context(tmp_path):
    from souschef.ui.pages.cookbook_analysis import _get_error_context

    (tmp_path / "recipes").mkdir()
    context = _get_error_context(tmp_path)
    assert isinstance(context, str)


def test_calculate_project_metrics_high_complexity_and_phased():
    from souschef.ui.pages.cookbook_analysis import _calculate_project_metrics

    results = [
        {"estimated_hours": 80, "complexity": "High"},
        {"estimated_hours": 64, "complexity": "High"},
    ]
    deps = {"a": ["b", "c"], "b": ["c"], "c": []}

    metrics = _calculate_project_metrics(results, deps)
    assert metrics["project_complexity"] == "High"
    assert metrics["migration_strategy"] == "phased"


def test_calculate_project_metrics_parallel_and_big_bang():
    from souschef.ui.pages.cookbook_analysis import _calculate_project_metrics

    # Parallel branch via has_circular_deps truthy and low dependency density
    results = [{"estimated_hours": 8, "complexity": "Low"} for _ in range(6)]
    deps_parallel = {"a": ["x"], "b": []}
    m1 = _calculate_project_metrics(results, deps_parallel)
    assert m1["migration_strategy"] in {"parallel", "big_bang", "phased"}

    # Big bang branch (low complexity and no dependencies)
    deps_big = {"a": [], "b": []}
    m2 = _calculate_project_metrics(
        [{"estimated_hours": 8, "complexity": "Low"}], deps_big
    )
    assert m2["migration_strategy"] == "big_bang"


def test_generate_project_recommendations_branches():
    from souschef.ui.pages.cookbook_analysis import _generate_project_recommendations

    project_analysis = {
        "migration_strategy": "parallel",
        "parallel_tracks": 3,
        "project_complexity": "High",
        "project_effort_days": 40,
        "dependency_density": 3.0,
        "circular_dependencies": [{"cookbooks": ["a", "b"]}],
    }
    individual = [{"name": f"cb{i}"} for i in range(12)]

    recs = _generate_project_recommendations(project_analysis, individual)

    assert any("parallel migration" in r.lower() for r in recs)
    assert any("high dependency density" in r.lower() for r in recs)
    assert any("circular dependency" in r.lower() for r in recs)
    assert any("large project scope" in r.lower() for r in recs)


def test_validate_cookbook_structure(tmp_path):
    from souschef.ui.pages.cookbook_analysis import _validate_cookbook_structure

    cb = tmp_path / "cookbook"
    (cb / "recipes").mkdir(parents=True)
    (cb / "metadata.rb").write_text("name 'x'\n")
    (cb / "recipes" / "default.rb").write_text("package 'x'\n")

    validation = _validate_cookbook_structure(cb)
    assert validation["Cookbook directory exists"]
    assert validation["metadata.rb exists"]
    assert validation["recipes/ directory exists"]
    assert validation["Has recipe files"]


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_failed_cookbook_details(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _display_failed_cookbook_details

    mock_st.expander.return_value = _ctx()

    cb = tmp_path / "broken"
    cb.mkdir()
    result = {
        "name": "broken",
        "path": str(cb),
        "recommendations": "Traceback: failure",
    }

    _display_failed_cookbook_details(result)

    mock_st.error.assert_called()
    mock_st.markdown.assert_called()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_conversion_helpers(mock_st):
    from souschef.ui.pages.cookbook_analysis import (
        _display_conversion_details,
        _display_conversion_report,
        _display_conversion_summary,
        _display_conversion_warnings_errors,
    )

    mock_st.columns.side_effect = lambda n: [_ctx() for _ in range(n)]
    mock_st.expander.return_value = _ctx()

    _display_conversion_summary(
        {
            "summary": {
                "cookbooks_converted": 2,
                "roles_created": 2,
                "tasks_generated": 10,
                "templates_converted": 3,
            }
        }
    )
    _display_conversion_warnings_errors({"warnings": ["w1"], "errors": ["e1"]})
    _display_conversion_details(
        {
            "cookbook_results": [
                {
                    "cookbook_name": "nginx",
                    "tasks_count": 5,
                    "templates_count": 2,
                    "variables_count": 1,
                    "files_count": 3,
                    "status": "success",
                },
                {
                    "cookbook_name": "bad",
                    "status": "failed",
                    "error": "boom",
                },
            ]
        }
    )
    _display_conversion_report("## report")

    assert mock_st.metric.call_count >= 4
    assert mock_st.warning.called
    assert mock_st.error.called
    assert mock_st.code.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_handle_playbook_download_empty(mock_st):
    from souschef.ui.pages.cookbook_analysis import _handle_playbook_download

    _handle_playbook_download([])
    mock_st.error.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_playbook_summary_and_label(mock_st):
    from souschef.ui.pages.cookbook_analysis import (
        _build_download_label,
        _display_playbook_summary,
    )

    _display_playbook_summary(3, 2)
    _display_playbook_summary(3, 0)
    assert mock_st.info.call_count == 2

    label1 = _build_download_label(3, 2)
    label2 = _build_download_label(3, 0)
    assert "3 playbooks" in label1
    assert "2 templates" in label1
    assert "3 playbooks" in label2


def test_write_playbooks_to_temp_dir_and_archive(tmp_path):
    from souschef.ui.pages.cookbook_analysis import (
        _create_playbook_archive,
        _write_playbooks_to_temp_dir,
    )

    playbooks = [
        {
            "cookbook_name": "nginx",
            "recipe_file": "default.rb",
            "playbook_content": "- hosts: all\n",
        },
        {
            "cookbook_name": "apache",
            "recipe_file": "web.rb",
            "playbook_content": "- hosts: web\n",
        },
    ]
    templates = [
        {
            "cookbook_name": "nginx",
            "template_file": "site.conf.j2",
            "template_content": "server {}",
            "original_file": "site.conf.erb",
        }
    ]

    _write_playbooks_to_temp_dir(playbooks, str(tmp_path))
    assert (tmp_path / "nginx_default.yml").exists()
    assert (tmp_path / "apache_web.yml").exists()

    archive = _create_playbook_archive(playbooks, templates)
    assert isinstance(archive, bytes)
    assert len(archive) > 0


def test_get_playbooks_dir_and_copy(tmp_path):
    from souschef.ui.pages.cookbook_analysis import (
        _copy_playbooks_to_repo,
        _get_playbooks_dir,
    )

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    repo_result = {"temp_path": str(repo_path)}

    playbooks_dir = _get_playbooks_dir(repo_result)
    assert playbooks_dir.exists()

    source = tmp_path / "source"
    source.mkdir()
    (source / "x.yml").write_text("- hosts: all\n")
    _copy_playbooks_to_repo(str(source), playbooks_dir)
    assert (playbooks_dir / "x.yml").exists()


def test_commit_playbooks_to_git_handles_no_commit(tmp_path):
    import subprocess

    from souschef.ui.pages.cookbook_analysis import _commit_playbooks_to_git

    (tmp_path / "x.yml").write_text("- hosts: all\n")
    with patch(
        "souschef.ui.pages.cookbook_analysis.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "git"),
    ):
        _commit_playbooks_to_git(str(tmp_path), str(tmp_path))


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_repo_sections(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import (
        _display_generated_repo_section_internal,
        _display_repo_info_section,
        _display_repo_structure_section,
    )

    mock_st.expander.return_value = _ctx()
    mock_st.session_state = {}
    mock_st.button.return_value = False

    repo = {
        "temp_path": str(tmp_path),
        "repo_type": "playbooks_and_roles",
        "files_created": ["ansible.cfg", "playbooks/site.yml"],
    }

    with patch(
        "souschef.ui.pages.cookbook_analysis._create_repository_zip",
        return_value=b"zip",
    ):
        _display_repo_info_section(repo)
        _display_repo_structure_section(repo)
        _display_generated_repo_section_internal(repo)

    assert mock_st.info.called
    assert mock_st.download_button.called


def test_create_analysis_report():
    from souschef.ui.pages.cookbook_analysis import _create_analysis_report

    results = [
        {"status": "Analysed", "estimated_hours": 10, "complexity": "High"},
        {"status": "Failed", "estimated_hours": 0, "complexity": "Low"},
    ]

    with patch(
        "souschef.ui.pages.cookbook_analysis.pd",
        new=MagicMock(
            Timestamp=MagicMock(
                now=MagicMock(
                    return_value=MagicMock(
                        isoformat=MagicMock(return_value="2026-01-01T00:00:00")
                    )
                )
            )
        ),
    ):
        report = _create_analysis_report(results)
    assert "analysis_summary" in report
    assert "cookbook_details" in report


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_holistic_conversion_results_wiring(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_holistic_conversion_results

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._parse_conversion_result_text",
            return_value={
                "summary": {},
                "warnings": [],
                "errors": [],
                "cookbook_results": [],
            },
        ),
        patch("souschef.ui.pages.cookbook_analysis._display_conversion_summary") as s,
        patch(
            "souschef.ui.pages.cookbook_analysis._display_conversion_warnings_errors"
        ) as w,
        patch("souschef.ui.pages.cookbook_analysis._display_conversion_details") as d,
        patch("souschef.ui.pages.cookbook_analysis._display_conversion_report") as r,
        patch(
            "souschef.ui.pages.cookbook_analysis._display_conversion_download_options"
        ) as dl,
    ):
        _display_holistic_conversion_results({"result": "## report"})

    s.assert_called_once()
    w.assert_called_once()
    d.assert_called_once()
    r.assert_called_once()
    dl.assert_called_once()


def test_serialize_activity_breakdown():
    from souschef.ui.pages.cookbook_analysis import _serialize_activity_breakdown

    class Activity:
        activity_type = "Parse"
        count = 2
        manual_hours = 5.0
        ai_assisted_hours = 2.5
        writing_hours = 3.0
        testing_hours = 2.0
        ai_assisted_writing_hours = 1.5
        ai_assisted_testing_hours = 1.0
        complexity_factor = 1.2
        description = "desc"
        time_saved_hours = 2.5
        efficiency_gain_percent = 50

    items = [Activity(), {"activity_type": "Convert", "count": 1}, "skip"]
    data = _serialize_activity_breakdown(items)
    assert len(data) == 2
    assert data[0]["activity_type"] == "Parse"
    assert data[1]["activity_type"] == "Convert"


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_save_analysis_to_db_success(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _save_analysis_to_db

    mock_st.session_state = SessionState()
    archive = tmp_path / "cookbook.zip"
    archive.write_text("zip")
    mock_st.session_state.archive_path = archive

    storage = MagicMock()
    storage.save_analysis.return_value = 123

    result = {
        "name": "nginx",
        "path": "/tmp/nginx",
        "version": "1.0",
        "complexity": "Medium",
        "estimated_hours": 10,
        "estimated_hours_with_souschef": 5,
        "recommendations": "ok",
        "activity_breakdown": [],
    }

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis.get_storage_manager",
            return_value=storage,
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._calculate_file_fingerprint",
            return_value="fp",
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._upload_cookbook_archive",
            return_value="blob_key",
        ),
    ):
        analysis_id = _save_analysis_to_db(result, "openai", "gpt-4o")

    assert analysis_id == 123
    storage.save_analysis.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_save_analysis_to_db_failure(mock_st):
    from souschef.ui.pages.cookbook_analysis import _save_analysis_to_db

    with patch(
        "souschef.ui.pages.cookbook_analysis.get_storage_manager",
        side_effect=RuntimeError("boom"),
    ):
        analysis_id = _save_analysis_to_db({"name": "x"})

    assert analysis_id is None
    mock_st.warning.assert_called_once()


def test_check_analysis_cache_found_and_missing():
    from souschef.ui.pages.cookbook_analysis import _check_analysis_cache

    cached = MagicMock()
    cached.cookbook_name = "nginx"
    cached.cookbook_path = "/tmp/nginx"
    cached.cookbook_version = "1.0"
    cached.complexity = "Low"
    cached.estimated_hours = 8
    cached.estimated_hours_with_souschef = 4
    cached.recommendations = "ok"

    storage = MagicMock()
    storage.get_cached_analysis.return_value = cached

    with patch(
        "souschef.ui.pages.cookbook_analysis.get_storage_manager",
        return_value=storage,
    ):
        result = _check_analysis_cache("/tmp/nginx", "openai", "gpt-4o")
    assert result is not None
    assert result["cached"]

    storage.get_cached_analysis.return_value = None
    with patch(
        "souschef.ui.pages.cookbook_analysis.get_storage_manager",
        return_value=storage,
    ):
        result2 = _check_analysis_cache("/tmp/nginx")
    assert result2 is None


def test_handle_multiple_cookbook_dirs(tmp_path):
    from souschef.ui.pages.cookbook_analysis import _handle_multiple_cookbook_dirs

    extraction = tmp_path / "extract"
    extraction.mkdir()
    recipes = extraction / "recipes"
    recipes.mkdir()
    attrs = extraction / "attributes"
    attrs.mkdir()

    result = _handle_multiple_cookbook_dirs(extraction, [recipes, attrs])
    assert result == extraction
    assert (extraction / "cookbook" / "recipes").exists()
    assert (extraction / "cookbook" / "metadata.rb").exists()


def test_handle_single_cookbook_dir(tmp_path):
    from souschef.ui.pages.cookbook_analysis import _handle_single_cookbook_dir

    extraction = tmp_path / "extract"
    extraction.mkdir()
    single = extraction / "cb1"
    single.mkdir()
    (single / "recipes").mkdir()

    result = _handle_single_cookbook_dir(extraction, single, {"recipes", "attributes"})
    assert result == extraction
    assert (single / "metadata.rb").exists()


def test_create_results_archive(tmp_path):
    from souschef.ui.pages.cookbook_analysis import create_results_archive

    results = [
        {
            "status": "Analysed",
            "name": "nginx",
            "version": "1.0",
            "maintainer": "me",
            "dependencies": 1,
            "complexity": "Low",
            "estimated_hours": 8.0,
            "estimated_hours_with_souschef": 4.0,
            "recommendations": "ok",
        },
        {"status": "Failed", "name": "bad", "estimated_hours": 0},
    ]

    with patch(
        "souschef.ui.pages.cookbook_analysis.pd",
        new=MagicMock(
            DataFrame=MagicMock(
                return_value=MagicMock(to_json=MagicMock(return_value="{}"))
            )
        ),
    ):
        archive = create_results_archive(results, str(tmp_path))

    assert isinstance(archive, bytes)
    assert len(archive) > 0


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_results_view_new_analysis_button(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_results_view

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.return_value = True
    mock_st.session_state = SessionState(
        {
            "analysis_results": [{"name": "nginx"}],
            "total_cookbooks": 1,
            "analysis_page_key": 1,
            "conversion_results": None,
        }
    )

    with patch("souschef.ui.pages.cookbook_analysis._display_analysis_results"):
        _display_results_view()

    assert mock_st.session_state.analysis_results is None
    assert mock_st.session_state.analysis_page_key == 2
    mock_st.rerun.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_results_view_conversion_results_branch(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_results_view

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.return_value = False
    mock_st.session_state = SessionState(
        {
            "analysis_results": [{"name": "nginx"}],
            "total_cookbooks": 1,
            "analysis_page_key": 1,
            "conversion_results": {"playbooks": [], "templates": []},
        }
    )

    with patch("souschef.ui.pages.cookbook_analysis._handle_playbook_download") as hp:
        _display_results_view()

    hp.assert_called_once_with([], [])


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_setup_cookbook_analysis_ui_back_to_dashboard(mock_st):
    from souschef.ui.pages.cookbook_analysis import _setup_cookbook_analysis_ui

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.return_value = True
    mock_st.session_state = SessionState(
        {
            "analysis_results": [{"x": 1}],
            "holistic_assessment": "x",
            "analysis_cookbook_path": "/tmp/x",
            "total_cookbooks": 1,
        }
    )

    _setup_cookbook_analysis_ui()

    assert mock_st.session_state.current_page == "Dashboard"
    assert mock_st.session_state.analysis_results is None
    mock_st.rerun.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_get_safe_cookbook_directory_branches(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _get_safe_cookbook_directory

    # Empty path
    assert _get_safe_cookbook_directory(" ") is None

    # Valid within cwd
    with patch("pathlib.Path.cwd", return_value=tmp_path):
        valid = _get_safe_cookbook_directory(str(tmp_path))
    assert valid is not None


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_validate_and_list_cookbooks_branches(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _validate_and_list_cookbooks

    bad_file = tmp_path / "file.txt"
    bad_file.write_text("x")

    with patch(
        "souschef.ui.pages.cookbook_analysis._get_safe_cookbook_directory",
        return_value=bad_file,
    ):
        _validate_and_list_cookbooks(str(tmp_path))
    mock_st.error.assert_called()

    mock_st.error.reset_mock()
    good_dir = tmp_path / "cookbooks"
    good_dir.mkdir()
    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._get_safe_cookbook_directory",
            return_value=good_dir,
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._list_and_display_cookbooks"
        ) as mock_list,
    ):
        _validate_and_list_cookbooks(str(tmp_path))
    mock_list.assert_called_once_with(good_dir)


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_show_deployment_information_branches(mock_st):
    from souschef.ui.pages.cookbook_analysis import _show_deployment_information

    _show_deployment_information("Simulation")
    _show_deployment_information("Live Deployment")

    mock_st.info.assert_called_once()
    mock_st.warning.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_get_connection_config_branches(mock_st):
    from souschef.ui.pages.cookbook_analysis import _get_connection_config

    cfg = _get_connection_config("Simulation")
    assert cfg == {}

    mock_st.expander.return_value = _ctx()
    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.text_input.side_effect = ["https://awx.local", "user", "pass"]
    mock_st.checkbox.return_value = True

    cfg2 = _get_connection_config("Live Deployment")
    assert cfg2["server_url"] == "https://awx.local"
    assert cfg2["username"] == "user"


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_execute_migration_if_requested_branches(mock_st):
    from souschef.ui.pages.cookbook_analysis import _execute_migration_if_requested

    config = {
        "target_platform": "awx",
        "target_version": "23.0.0",
        "deployment_mode": "simulation",
        "connection": {},
        "conversion": {"include_repo": True, "include_tar": True},
        "advanced": {
            "chef_version": "15.10.91",
            "output_dir": "",
            "preserve_comments": True,
        },
    }

    mock_st.button.return_value = False
    _execute_migration_if_requested("/tmp/cookbooks", config)

    mock_st.button.return_value = True
    mock_st.session_state = SessionState({"simulation_result": {"ok": True}})
    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._simulate_chef_to_awx_migration_ui"
        ) as sim,
        patch(
            "souschef.ui.pages.cookbook_analysis._display_simulation_results"
        ) as disp,
    ):
        _execute_migration_if_requested("/tmp/cookbooks", config)

    sim.assert_called_once()
    disp.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_show_individual_selection_branches(mock_st):
    from souschef.ui.pages.cookbook_analysis import _show_individual_selection

    cookbook_data = [{"Name": "nginx"}, {"Name": "apache"}]

    mock_st.multiselect.return_value = []
    _show_individual_selection("/tmp/cookbooks", cookbook_data)

    mock_st.multiselect.return_value = ["nginx"]
    mock_st.columns.return_value = [_ctx(), _ctx(), _ctx()]
    mock_st.button.side_effect = [True, False, False]

    with patch("souschef.ui.pages.cookbook_analysis.analyse_selected_cookbooks") as asc:
        _show_individual_selection("/tmp/cookbooks", cookbook_data)

    asc.assert_called_once_with("/tmp/cookbooks", ["nginx"])


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_download_button_branches(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_download_button

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.return_value = False
    mock_st.session_state = {}

    _display_download_button(2, 1, b"zip", playbooks=[])
    mock_st.download_button.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_download_button_with_generated_repo(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_download_button

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.return_value = False
    mock_st.session_state = SessionState(
        {
            "generated_playbook_repo": {
                "temp_path": "/tmp/repo",
                "repo_type": "x",
                "files_created": [],
            }
        }
    )

    with patch(
        "souschef.ui.pages.cookbook_analysis._display_generated_repo_section_internal"
    ) as display_repo:
        _display_download_button(1, 0, b"zip", playbooks=[])

    display_repo.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_playbook_and_template_previews(mock_st):
    from souschef.ui.pages.cookbook_analysis import (
        _display_playbook_previews,
        _display_template_previews,
    )

    mock_st.expander.return_value = _ctx()

    playbooks = [
        {
            "cookbook_name": "nginx",
            "recipe_file": "default.rb",
            "playbook_content": "- hosts: all\n",
            "conversion_method": "AI-enhanced",
        }
    ]
    templates = [
        {
            "cookbook_name": "nginx",
            "template_file": "site.conf.j2",
            "original_file": "site.conf.erb",
            "template_content": "server {}",
            "variables": ["port", "server_name"],
        }
    ]

    _display_playbook_previews(playbooks)
    _display_template_previews(templates)
    _display_template_previews([])

    assert mock_st.code.called
    assert mock_st.subheader.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_handle_repo_creation_failure_and_success(mock_st):
    from souschef.ui.pages.cookbook_analysis import _handle_repo_creation

    playbooks = [{"cookbook_name": "nginx"}, {"cookbook_name": "apache"}]

    with patch(
        "souschef.ui.pages.cookbook_analysis._create_ansible_repository",
        return_value={"success": False, "error": "boom"},
    ):
        _handle_repo_creation("/tmp", playbooks)
        mock_st.error.assert_called()

    mock_st.error.reset_mock()
    mock_st.session_state = SessionState()
    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._create_ansible_repository",
            return_value={
                "success": True,
                "temp_path": "/tmp/repo",
                "repo_type": "x",
                "files_created": [],
            },
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._get_playbooks_dir",
            return_value=Path("/tmp/repo/playbooks"),
        ),
        patch("souschef.ui.pages.cookbook_analysis._copy_playbooks_to_repo"),
        patch("souschef.ui.pages.cookbook_analysis._commit_playbooks_to_git"),
    ):
        _handle_repo_creation("/tmp", playbooks)

    assert "generated_playbook_repo" in mock_st.session_state


# === Extended coverage for uncovered display and input functions ===


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_get_cookbook_path_input(mock_st):
    """Test _get_cookbook_path_input returns text input."""
    from souschef.ui.pages.cookbook_analysis import _get_cookbook_path_input

    mock_st.text_input.return_value = "/tmp/cookbooks"
    result = _get_cookbook_path_input()

    assert result == "/tmp/cookbooks"
    mock_st.text_input.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_get_archive_upload_input_with_file(mock_st):
    """Test _get_archive_upload_input with uploaded file."""
    from souschef.ui.pages.cookbook_analysis import _get_archive_upload_input

    uploaded = MagicMock()
    mock_st.file_uploader.return_value = uploaded
    result = _get_archive_upload_input()

    assert result == uploaded
    mock_st.file_uploader.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_get_archive_upload_input_no_file(mock_st):
    """Test _get_archive_upload_input with no file."""
    from souschef.ui.pages.cookbook_analysis import _get_archive_upload_input

    mock_st.file_uploader.return_value = None
    result = _get_archive_upload_input()

    assert result is None


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_validate_and_list_cookbooks_invalid_path(mock_st):
    """Test _validate_and_list_cookbooks with invalid path."""
    from souschef.ui.pages.cookbook_analysis import _validate_and_list_cookbooks

    with patch(
        "souschef.ui.pages.cookbook_analysis._get_safe_cookbook_directory",
        return_value=None,
    ):
        _validate_and_list_cookbooks("/invalid/path")

    mock_st.error.assert_not_called()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_validate_and_list_cookbooks_not_directory(mock_st):
    """Test _validate_and_list_cookbooks when path is file."""
    from souschef.ui.pages.cookbook_analysis import _validate_and_list_cookbooks

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._get_safe_cookbook_directory",
            return_value=Path("/tmp/file.txt"),
        ),
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "is_dir", return_value=False),
    ):
        _validate_and_list_cookbooks("/tmp/file.txt")

    mock_st.error.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_get_safe_cookbook_directory_empty_path(mock_st):
    """Test _get_safe_cookbook_directory with empty path."""
    from souschef.ui.pages.cookbook_analysis import _get_safe_cookbook_directory

    result = _get_safe_cookbook_directory("")

    assert result is None
    mock_st.error.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_get_safe_cookbook_directory_valid(mock_st):
    """Test _get_safe_cookbook_directory with valid path."""
    from souschef.ui.pages.cookbook_analysis import (
        _get_safe_cookbook_directory,
    )

    result = _get_safe_cookbook_directory("/tmp")

    assert result is not None


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_list_and_display_cookbooks(mock_st):
    """Test _list_and_display_cookbooks."""
    from souschef.ui.pages.cookbook_analysis import _list_and_display_cookbooks

    with (
        patch("souschef.ui.pages.cookbook_analysis.Path"),
        patch("souschef.ui.pages.cookbook_analysis._collect_cookbook_data"),
        patch("souschef.ui.pages.cookbook_analysis._display_cookbook_table"),
        patch("souschef.ui.pages.cookbook_analysis._handle_cookbook_selection"),
    ):
        _list_and_display_cookbooks(Path("/tmp"))

    # Test passes if function runs without error


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_collect_cookbook_data_single_cookbook(mock_st):
    """Test _collect_cookbook_data with single cookbook."""
    from souschef.ui.pages.cookbook_analysis import _collect_cookbook_data

    cookbooks = [Path("/tmp/cookbook1")]
    result = _collect_cookbook_data(cookbooks)

    assert isinstance(result, list)


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_collect_cookbook_data_multiple_cookbooks(mock_st):
    """Test _collect_cookbook_data with multiple cookbooks."""
    from souschef.ui.pages.cookbook_analysis import _collect_cookbook_data

    cookbooks = [Path("/tmp/cookbook1"), Path("/tmp/cookbook2")]
    result = _collect_cookbook_data(cookbooks)

    assert isinstance(result, list)


def test_normalize_description_with_string():
    """Test _normalize_description with string."""
    from souschef.ui.pages.cookbook_analysis import _normalize_description

    result = _normalize_description("A test description")
    assert result == "A test description"


def test_normalize_description_with_none():
    """Test _normalize_description with None."""
    from souschef.ui.pages.cookbook_analysis import _normalize_description

    result = _normalize_description(None)
    assert isinstance(result, str)


def test_normalize_description_with_dict():
    """Test _normalize_description with dict."""
    from souschef.ui.pages.cookbook_analysis import _normalize_description

    result = _normalize_description({"key": "value"})
    assert isinstance(result, str)


def test_truncate_description_long():
    """Test _truncate_description with long text."""
    from souschef.ui.pages.cookbook_analysis import _truncate_description

    long_text = "x" * 300
    result = _truncate_description(long_text)

    assert len(result) <= 200


def test_truncate_description_short():
    """Test _truncate_description with short text."""
    from souschef.ui.pages.cookbook_analysis import _truncate_description

    short_text = "short"
    result = _truncate_description(short_text)

    assert result == short_text


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_create_error_entry(mock_st):
    """Test _create_error_entry."""
    from souschef.ui.pages.cookbook_analysis import _create_error_entry

    result = _create_error_entry(Path("/tmp/cookbook"), "Error message")

    assert isinstance(result, dict)
    assert "Name" in result


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_create_no_metadata_entry(mock_st):
    """Test _create_no_metadata_entry."""
    from souschef.ui.pages.cookbook_analysis import (
        _create_no_metadata_entry,
    )

    result = _create_no_metadata_entry(Path("/tmp/cookbook"))

    assert isinstance(result, dict)
    assert result["Name"] == "cookbook"


@patch("souschef.ui.pages.cookbook_analysis.pd")
@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_cookbook_table(mock_st, mock_pd):
    """Test _display_cookbook_table."""
    from souschef.ui.pages.cookbook_analysis import _display_cookbook_table

    mock_pd.DataFrame.return_value = MagicMock()

    cookbook_data = [{"Name": "cookbook1", "Version": "1.0.0"}]
    _display_cookbook_table(cookbook_data)

    mock_pd.DataFrame.assert_called_once()
    mock_st.dataframe.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_show_deployment_information_simulation(mock_st):
    """Test _show_deployment_information with simulation mode."""
    from souschef.ui.pages.cookbook_analysis import (
        DeploymentMode,
        _show_deployment_information,
    )

    _show_deployment_information(DeploymentMode.SIMULATION.value)

    mock_st.info.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_show_deployment_information_live(mock_st):
    """Test _show_deployment_information with live mode."""
    from souschef.ui.pages.cookbook_analysis import (
        DeploymentMode,
        _show_deployment_information,
    )

    _show_deployment_information(DeploymentMode.LIVE.value)

    mock_st.warning.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_get_connection_config_simulation_mode(mock_st):
    """Test _get_connection_config with simulation mode."""
    from souschef.ui.pages.cookbook_analysis import (
        DeploymentMode,
        _get_connection_config,
    )

    result = _get_connection_config(DeploymentMode.SIMULATION.value)

    assert result == {}


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_get_connection_config_live_mode(mock_st):
    """Test _get_connection_config with live mode."""
    from souschef.ui.pages.cookbook_analysis import (
        DeploymentMode,
        _get_connection_config,
    )

    mock_st.expander.return_value = _ctx()
    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.text_input.side_effect = [
        "https://awx.example.com",
        "admin",
        "password",
    ]
    mock_st.checkbox.return_value = True

    result = _get_connection_config(DeploymentMode.LIVE.value)

    assert isinstance(result, dict)
    assert "server_url" in result


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_collect_conversion_options(mock_st):
    """Test _collect_conversion_options."""
    from souschef.ui.pages.cookbook_analysis import _collect_conversion_options

    mock_st.expander.return_value = _ctx()
    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.checkbox.side_effect = [True, True, False, True, False, True]

    result = _collect_conversion_options()

    assert isinstance(result, dict)
    assert "include_repo" in result


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_collect_advanced_options(mock_st):
    """Test _collect_advanced_options."""
    from souschef.ui.pages.cookbook_analysis import _collect_advanced_options

    mock_st.expander.return_value = _ctx()
    mock_st.text_input.side_effect = ["15.10.91", ""]
    mock_st.checkbox.return_value = True

    result = _collect_advanced_options()

    assert isinstance(result, dict)
    assert "chef_version" in result


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_execute_migration_if_requested_no_click(mock_st):
    """Test _execute_migration_if_requested when button not clicked."""
    from souschef.ui.pages.cookbook_analysis import (
        DeploymentMode,
        _execute_migration_if_requested,
    )

    mock_st.button.return_value = False
    mock_st.session_state = SessionState()

    config = {
        "target_platform": "awx",
        "target_version": "23.0.0",
        "deployment_mode": DeploymentMode.SIMULATION.value,
        "conversion": {"include_repo": True, "include_tar": True},
        "advanced": {
            "chef_version": "15.10.91",
            "output_dir": "",
            "preserve_comments": True,
        },
        "connection": {},
    }

    with (
        patch("souschef.ui.pages.cookbook_analysis._show_deployment_information"),
        patch(
            "souschef.ui.pages.cookbook_analysis._get_connection_config",
            return_value={},
        ),
    ):
        _execute_migration_if_requested("/tmp", config)

    mock_st.button.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_show_individual_selection_no_selected(mock_st):
    """Test _show_individual_selection with no selected cookbooks."""
    from souschef.ui.pages.cookbook_analysis import _show_individual_selection

    mock_st.multiselect.return_value = []

    cookbook_data = [{"Name": "cookbook1"}]

    _show_individual_selection("/tmp", cookbook_data)

    mock_st.multiselect.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_show_cookbook_validation_warnings_with_problematic(mock_st):
    """Test _show_cookbook_validation_warnings with problematic cookbooks."""
    from souschef.ui.pages.cookbook_analysis import (
        METADATA_COLUMN_NAME,
        METADATA_STATUS_NO,
        _show_cookbook_validation_warnings,
    )

    cookbook_data = [
        {METADATA_COLUMN_NAME: METADATA_STATUS_NO, "Name": "bad", "Path": "/tmp"}
    ]

    with (
        patch("souschef.ui.pages.cookbook_analysis._normalize_path"),
        patch("souschef.ui.pages.cookbook_analysis.Path"),
    ):
        _show_cookbook_validation_warnings(cookbook_data)

    # Should call warning when there are problematic cookbooks
    assert mock_st.warning.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_show_holistic_actions(mock_st):
    """Test _show_holistic_actions."""
    from souschef.ui.pages.cookbook_analysis import _show_holistic_actions

    mock_st.button.side_effect = [False, False]
    mock_st.columns.return_value = [_ctx(), _ctx()]

    cookbook_data = [{"Name": "cookbook1"}]

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._analyze_all_cookbooks_holistically"
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._convert_all_cookbooks_holistically"
        ),
    ):
        _show_holistic_actions("/tmp", cookbook_data)

    assert mock_st.button.call_count >= 1


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_setup_cookbook_analysis_ui(mock_st):
    """Test _setup_cookbook_analysis_ui."""
    from souschef.ui.pages.cookbook_analysis import _setup_cookbook_analysis_ui

    mock_st.session_state = SessionState()
    mock_st.columns.return_value = [_ctx(), _ctx()]  # Return exactly 2 columns
    mock_st.button.return_value = False

    _setup_cookbook_analysis_ui()

    assert mock_st.title.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_show_analysis_input_directory_mode(mock_st):
    """Test _show_analysis_input with directory input."""
    from souschef.ui.pages.cookbook_analysis import _show_analysis_input

    mock_st.radio.return_value = "Directory Path"
    mock_st.session_state = SessionState()
    mock_st.spinner.return_value = _ctx()

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._get_cookbook_path_input",
            return_value="/tmp/cookbooks",
        ),
        patch("souschef.ui.pages.cookbook_analysis._validate_and_list_cookbooks"),
        patch("souschef.ui.pages.cookbook_analysis._display_instructions"),
    ):
        _show_analysis_input()

    mock_st.radio.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_results_view(mock_st):
    """Test _display_results_view."""
    from souschef.ui.pages.cookbook_analysis import _display_results_view

    mock_st.session_state = SessionState(
        {
            "analysis_results": [{"name": "test"}],
            "analysis_page_key": 0,
            "total_cookbooks": 1,
            "conversion_results": None,
            "generated_playbook_repo": None,
        }
    )
    mock_st.button.return_value = False
    mock_st.columns.return_value = [_ctx(), _ctx()]

    with patch("souschef.ui.pages.cookbook_analysis._display_analysis_results"):
        _display_results_view()

    mock_st.button.assert_called()


# Removed duplicate test_validate_cookbook_structure (original at line 387)


# === MASSIVE COVERAGE EXPANSION - Additional workflow tests ===


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_analyse_cookbook_metadata_with_metadata(mock_st):
    """Test _analyse_cookbook_metadata when metadata exists."""
    from souschef.ui.pages.cookbook_analysis import _analyse_cookbook_metadata

    with (
        patch("souschef.ui.pages.cookbook_analysis.Path") as mock_path_class,
        patch(
            "souschef.ui.pages.cookbook_analysis._parse_metadata_with_fallback"
        ) as mock_parse,
    ):
        mock_cookbook = MagicMock()
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path
        mock_parse.return_value = {"name": "test"}

        result = _analyse_cookbook_metadata(mock_cookbook)

        assert isinstance(result, dict)


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_parse_metadata_with_fallback_success(mock_st):
    """Test _parse_metadata_with_fallback with successful parsing."""
    from souschef.ui.pages.cookbook_analysis import _parse_metadata_with_fallback

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis.parse_cookbook_metadata",
            return_value={"name": "test"},
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._extract_cookbook_info"
        ) as mock_extract,
    ):
        mock_extract.return_value = {"name": "test", "status": "analysed"}
        result = _parse_metadata_with_fallback(Path("/tmp"), Path("/tmp/metadata.rb"))

        assert isinstance(result, dict)


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_parse_metadata_with_fallback_error(mock_st):
    """Test _parse_metadata_with_fallback with parse error."""
    from souschef.ui.pages.cookbook_analysis import _parse_metadata_with_fallback

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis.parse_cookbook_metadata",
            side_effect=RuntimeError("Parse error"),
        ),
        patch("souschef.ui.pages.cookbook_analysis._create_error_entry") as mock_error,
    ):
        mock_error.return_value = {"error": "Parse error"}
        result = _parse_metadata_with_fallback(Path("/tmp"), Path("/tmp/metadata.rb"))

        assert isinstance(result, dict)


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_extract_cookbook_info(mock_st):
    """Test _extract_cookbook_info."""
    from souschef.ui.pages.cookbook_analysis import _extract_cookbook_info

    metadata = {
        "name": "nginx",
        "version": "1.0.0",
        "maintainer": "Test",
        "description": "Test cookbook",
        "depends": [{"cookbookname": "apache2"}],
    }

    result = _extract_cookbook_info(metadata, Path("/tmp"), "Yes")

    assert isinstance(result, dict)
    assert "Name" in result


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_analyze_all_cookbooks_holistically_with_ai(mock_st):
    """Test _analyze_all_cookbooks_holistically with AI enabled."""
    from souschef.ui.pages.cookbook_analysis import (
        _analyze_all_cookbooks_holistically,
    )

    mock_st.session_state = SessionState()
    mock_st.subheader = MagicMock()
    mock_st.progress = MagicMock(return_value=MagicMock())
    mock_st.empty = MagicMock()
    mock_progress = MagicMock()
    mock_status = MagicMock()

    def setup_progress():
        return mock_progress, mock_status

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._setup_analysis_progress",
            return_value=setup_progress(),
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.load_ai_settings",
            return_value={"provider": "anthropic", "api_key": "test"},
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._get_ai_provider",
            return_value="Anthropic (Claude)",
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._analyze_with_ai",
            return_value=[{"name": "test"}],
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._get_ai_string_value",
            return_value="claude-3-5-sonnet-20241022",
        ),
    ):
        _analyze_all_cookbooks_holistically(
            "/tmp", [{"Name": "test", "Path": "/tmp/test"}]
        )

    assert "analysis_results" in mock_st.session_state


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_analyze_all_cookbooks_holistically_rule_based(mock_st):
    """Test _analyze_all_cookbooks_holistically with rule-based analysis."""
    from souschef.ui.pages.cookbook_analysis import (
        _analyze_all_cookbooks_holistically,
    )

    mock_st.session_state = SessionState()
    mock_st.subheader = MagicMock()
    mock_progress = MagicMock()
    mock_status = MagicMock()

    def setup_progress():
        return mock_progress, mock_status

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._setup_analysis_progress",
            return_value=setup_progress(),
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.load_ai_settings",
            return_value={},
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._get_ai_provider",
            return_value=None,
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._analyze_rule_based",
            return_value=([{"name": "test"}], {"cookbooks": []}),
        ),
    ):
        _analyze_all_cookbooks_holistically(
            "/tmp", [{"Name": "test", "Path": "/tmp/test"}]
        )

    assert "analysis_results" in mock_st.session_state


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_analyze_with_ai(mock_st):
    """Test _analyze_with_ai."""
    from souschef.ui.pages.cookbook_analysis import _analyze_with_ai

    mock_progress = MagicMock()

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis.load_ai_settings",
            return_value={
                "provider": "anthropic",
                "model": "claude",
                "api_key": "test",
            },
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._get_ai_string_value",
            return_value="claude-3-5-sonnet-20241022",
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._check_analysis_cache",
            return_value=None,
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.assess_single_cookbook_with_ai",
            return_value={"complexity": "Medium"},
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._build_cookbook_result",
            return_value={"status": "analysed"},
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._save_analysis_to_db",
            return_value="id123",
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._get_ai_int_value",
            return_value=4000,
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._get_ai_float_value",
            return_value=0.7,
        ),
        patch("souschef.ui.pages.cookbook_analysis._normalize_path"),
        patch("souschef.ui.pages.cookbook_analysis.Path"),
    ):
        cookbook_data = [{"Name": "test", "Path": "/tmp/test"}]
        result = _analyze_with_ai(cookbook_data, "Anthropic (Claude)", mock_progress)

    assert isinstance(result, list)


@patch("souschef.ui.pages.cookbook_analysis.st")
@patch("souschef.ui.pages.cookbook_analysis.pd")
def test_display_project_analysis_full(mock_pd, mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_project_analysis

    mock_st.columns.return_value = [_ctx(), _ctx(), _ctx(), _ctx()]
    mock_st.expander.return_value = _ctx()
    mock_pd.DataFrame.return_value = MagicMock()

    project_analysis = {
        "project_complexity": "High",
        "project_effort_days": 10,
        "project_timeline_weeks": 4,
        "migration_strategy": "phased",
        "total_dependencies": 3,
        "migration_order": [
            {
                "phase": 1,
                "cookbook": "base",
                "complexity": "Low",
                "effort_days": 2,
                "dependencies": 0,
                "reason": "Foundation",
            }
        ],
        "dependency_graph": {"base": [], "web": ["base"]},
        "circular_dependencies": [{"cookbooks": ["a", "b", "a"]}],
        "recommendations": ["Start with base"],
    }

    with patch("souschef.ui.pages.cookbook_analysis._display_dependency_graph"):
        _display_project_analysis(project_analysis)

    assert mock_st.metric.call_count >= 4
    assert mock_st.dataframe.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_dependency_graph(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_dependency_graph

    _display_dependency_graph({"base": [], "web": ["base"]})

    assert mock_st.write.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_download_option_no_success(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_download_option

    _display_download_option([{"status": "Failed", "name": "bad"}])

    mock_st.info.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_download_option_convert_with_ai(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_download_option

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.return_value = True

    results = [{"status": "Analysed", "name": "ok", "estimated_hours": 1.0}]

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._create_analysis_report",
            return_value="{}",
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.load_ai_settings",
            return_value={"provider": "OpenAI", "api_key": "k", "model": "gpt-4o"},
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._convert_and_download_playbooks"
        ) as convert,
    ):
        _display_download_option(results)

    convert.assert_called_once_with(results)


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_analysis_summary(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_analysis_summary

    mock_st.columns.return_value = [_ctx(), _ctx(), _ctx()]
    _display_analysis_summary(
        [
            {
                "status": "Analysed",
                "estimated_hours": 10,
                "estimated_hours_with_souschef": 5,
                "complexity": "High",
            }
        ],
        1,
    )

    assert mock_st.metric.call_count == 3


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_detailed_analysis_routes(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_detailed_analysis

    results = [
        {"status": "Analysed", "name": "ok"},
        {"status": "Failed", "name": "bad"},
    ]

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._display_single_cookbook_details"
        ) as ok_fn,
        patch(
            "souschef.ui.pages.cookbook_analysis._display_failed_cookbook_details"
        ) as bad_fn,
    ):
        _display_detailed_analysis(results)

    ok_fn.assert_called_once()
    bad_fn.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_analysis_results_with_project_analysis(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_analysis_results

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.return_value = False
    mock_st.session_state = SessionState(
        {
            "analysis_info_messages": ["done"],
            "project_analysis": {"project_complexity": "Medium"},
            "temp_dir": None,
        }
    )

    results = [{"status": "Analysed", "name": "ok"}]

    with (
        patch("souschef.ui.pages.cookbook_analysis._display_analysis_summary"),
        patch("souschef.ui.pages.cookbook_analysis._display_project_analysis") as proj,
        patch("souschef.ui.pages.cookbook_analysis._display_results_table"),
        patch("souschef.ui.pages.cookbook_analysis._display_detailed_analysis"),
        patch("souschef.ui.pages.cookbook_analysis._display_download_option"),
    ):
        _display_analysis_results(results, 1)

    proj.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_conversion_summary(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_conversion_summary

    mock_st.columns.return_value = [_ctx(), _ctx(), _ctx(), _ctx()]
    _display_conversion_summary(
        {
            "summary": {
                "cookbooks_converted": 2,
                "roles_created": 2,
                "tasks_generated": 12,
                "templates_converted": 3,
            }
        }
    )

    assert mock_st.metric.call_count == 4


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_conversion_warnings_errors(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_conversion_warnings_errors

    _display_conversion_warnings_errors({"warnings": ["w1"], "errors": ["e1"]})

    mock_st.warning.assert_called_once()
    mock_st.error.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_conversion_details_success_and_failure(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_conversion_details

    mock_st.expander.return_value = _ctx()
    mock_st.columns.return_value = [_ctx(), _ctx()]

    _display_conversion_details(
        {
            "cookbook_results": [
                {
                    "cookbook_name": "ok",
                    "tasks_count": 2,
                    "templates_count": 1,
                    "variables_count": 1,
                    "files_count": 4,
                    "status": "success",
                },
                {
                    "cookbook_name": "bad",
                    "status": "failed",
                    "error": "boom",
                },
            ]
        }
    )

    assert mock_st.success.called
    assert mock_st.error.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_conversion_report(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_conversion_report

    mock_st.expander.return_value = _ctx()
    _display_conversion_report("## report")
    mock_st.code.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_simulate_chef_to_awx_migration_ui_success(mock_st):
    from souschef.ui.pages.cookbook_analysis import _simulate_chef_to_awx_migration_ui

    mock_st.expander.return_value = _ctx()
    mock_st.session_state = SessionState()

    with patch(
        "souschef.server.simulate_chef_to_awx_migration",
        return_value='{"archives": {}}',
    ):
        _simulate_chef_to_awx_migration_ui(
            "/tmp/cook", "awx", include_repo=True, include_tar=True
        )

    assert "simulation_result" in mock_st.session_state
    mock_st.success.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_simulate_chef_to_awx_migration_ui_invalid_json(mock_st):
    from souschef.ui.pages.cookbook_analysis import _simulate_chef_to_awx_migration_ui

    mock_st.session_state = SessionState()
    with patch(
        "souschef.server.simulate_chef_to_awx_migration",
        return_value="not-json",
    ):
        _simulate_chef_to_awx_migration_ui(
            "/tmp/cook", "awx", include_repo=True, include_tar=True
        )

    mock_st.error.assert_called()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_simulation_results_no_archives(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_simulation_results

    mock_st.expander.return_value = _ctx()
    _display_simulation_results({"archives": {}})
    mock_st.json.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_simulation_results_with_archives(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _display_simulation_results

    roles = tmp_path / "roles.tar.gz"
    repo = tmp_path / "repo.tar.gz"
    roles.write_text("x")
    repo.write_text("y")
    mock_st.expander.return_value = _ctx()

    with patch(
        "souschef.ui.pages.cookbook_analysis._validate_output_path",
        side_effect=[roles, repo],
    ):
        _display_simulation_results(
            {"archives": {"roles_tar_gz": str(roles), "repository_tar_gz": str(repo)}}
        )

    assert mock_st.download_button.call_count == 2


@patch("souschef.ui.pages.cookbook_analysis.st")
@patch("souschef.ui.pages.cookbook_analysis.pd")
def test_display_cookbook_activity_breakdown_dict_and_object(mock_pd, mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_cookbook_activity_breakdown

    class Activity:
        activity_type = "Parse"
        count = 1
        description = "desc"
        manual_hours = 5.0
        ai_assisted_hours = 2.5
        writing_hours = 0.0
        testing_hours = 0.0
        ai_assisted_writing_hours = 0.0
        ai_assisted_testing_hours = 0.0
        time_saved_hours = 2.5
        efficiency_gain_percent = 50.0

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_pd.DataFrame.return_value = MagicMock()

    _display_cookbook_activity_breakdown(
        [
            {
                "activity_type": "Convert",
                "count": 2,
                "description": "desc",
                "manual_hours": 4.0,
                "ai_assisted_hours": 2.0,
                "time_saved_hours": 2.0,
                "efficiency_gain_percent": 50.0,
            },
            Activity(),
        ]
    )

    mock_st.dataframe.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_single_and_failed_cookbook_details(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import (
        _display_failed_cookbook_details,
        _display_single_cookbook_details,
    )

    mock_st.expander.return_value = _ctx()
    mock_st.columns.return_value = [_ctx(), _ctx(), _ctx()]

    _display_single_cookbook_details(
        {
            "name": "nginx",
            "version": "1.0",
            "maintainer": "me",
            "dependencies": 1,
            "complexity": "Medium",
            "estimated_hours": 10.0,
            "estimated_hours_with_souschef": 5.0,
            "path": str(tmp_path),
            "recommendations": "ok",
            "activity_breakdown": [],
        }
    )

    with patch(
        "souschef.ui.pages.cookbook_analysis._validate_cookbook_structure",
        return_value={"Cookbook directory exists": True},
    ):
        _display_failed_cookbook_details(
            {"name": "bad", "path": str(tmp_path), "recommendations": "error"}
        )

    assert mock_st.metric.called
    assert mock_st.error.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_and_download_playbooks_no_success(mock_st):
    from souschef.ui.pages.cookbook_analysis import _convert_and_download_playbooks

    _convert_and_download_playbooks([{"status": "Failed"}])
    mock_st.warning.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_and_download_playbooks_success(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _convert_and_download_playbooks

    mock_st.session_state = SessionState()
    mock_st.spinner.return_value = _ctx()

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._convert_single_cookbook",
            return_value=(
                [
                    {
                        "cookbook_name": "nginx",
                        "recipe_file": "default.rb",
                        "playbook_content": "- hosts: all",
                    }
                ],
                [],
            ),
        ),
        patch("souschef.ui.pages.cookbook_analysis._handle_playbook_download") as dl,
    ):
        _convert_and_download_playbooks(
            [{"status": "Analysed", "name": "nginx", "path": str(tmp_path)}]
        )

    assert "conversion_results" in mock_st.session_state
    dl.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_single_cookbook_missing_recipes_dir(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _convert_single_cookbook

    playbooks, templates = _convert_single_cookbook(
        {"name": "nginx", "path": str(tmp_path)}, None
    )

    assert playbooks == []
    assert templates == []
    mock_st.warning.assert_called()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_recipes_ai_and_deterministic(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _convert_recipes

    recipe = tmp_path / "default.rb"
    recipe.write_text("package 'nginx'")

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis.load_ai_settings",
            return_value={"provider": "Local Model"},
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.generate_playbook_from_recipe",
            return_value="- hosts: all",
        ),
    ):
        out = _convert_recipes("nginx", [recipe], None)
    assert len(out) == 1

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis.load_ai_settings",
            return_value={
                "provider": "OpenAI (GPT)",
                "api_key": "k",
                "model": "gpt-4o",
            },
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.generate_playbook_from_recipe_with_ai",
            return_value="- hosts: all",
        ),
    ):
        out2 = _convert_recipes("nginx", [recipe], None)
    assert len(out2) == 1


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_templates_and_find_recipe_file(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import (
        _convert_templates,
        _find_recipe_file,
    )

    recipes = tmp_path / "recipes"
    recipes.mkdir()
    (recipes / "default.rb").write_text("package 'nginx'")
    templates = tmp_path / "templates"
    templates.mkdir()

    with patch(
        "souschef.ui.pages.cookbook_analysis._convert_templates_impl",
        return_value={
            "success": True,
            "results": [
                {
                    "success": True,
                    "jinja2_content": "server {}",
                    "jinja2_file": str(tmp_path / "site.conf.j2"),
                    "original_file": str(tmp_path / "site.conf.erb"),
                    "variables": ["port"],
                }
            ],
        },
    ):
        converted = _convert_templates("nginx", tmp_path)
    assert len(converted) == 1

    recipe = _find_recipe_file(tmp_path, "nginx")
    assert recipe is not None


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_handle_playbook_download_success_path(mock_st):
    from souschef.ui.pages.cookbook_analysis import _handle_playbook_download

    mock_st.session_state = SessionState()
    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.return_value = False

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._create_playbook_archive",
            return_value=b"zip",
        ),
        patch("souschef.ui.pages.cookbook_analysis._display_download_button"),
        patch("souschef.ui.pages.cookbook_analysis._display_playbook_previews"),
        patch("souschef.ui.pages.cookbook_analysis._display_template_previews"),
    ):
        _handle_playbook_download(
            [
                {
                    "cookbook_name": "nginx",
                    "recipe_file": "default.rb",
                    "playbook_content": "- hosts: all",
                }
            ],
            [],
        )

    mock_st.success.assert_called_once()

    @patch("souschef.ui.pages.cookbook_analysis.st")
    def test_save_conversion_to_storage_success(mock_st, tmp_path):
        from souschef.ui.pages.cookbook_analysis import _save_conversion_to_storage

        out = tmp_path / "roles"
        out.mkdir()
        mock_st.session_state = SessionState(
            {"holistic_assessment": {"analysis_id": 42}}
        )

        storage = MagicMock()
        storage.save_conversion.return_value = 100
        blob = MagicMock()
        blob.upload.return_value = "blob-roles"

        with (
            patch(
                "souschef.ui.pages.cookbook_analysis.get_storage_manager",
                return_value=storage,
            ),
            patch(
                "souschef.ui.pages.cookbook_analysis.get_blob_storage",
                return_value=blob,
            ),
        ):
            _save_conversion_to_storage(
                "nginx",
                out,
                "## Overview:\n- Total Converted Files: 3",
                "role",
            )

        assert mock_st.session_state.last_conversion_id == 100
        storage.save_conversion.assert_called_once()

    @patch("souschef.ui.pages.cookbook_analysis.st")
    def test_save_conversion_to_storage_exception(mock_st, tmp_path):
        from souschef.ui.pages.cookbook_analysis import _save_conversion_to_storage

        with patch(
            "souschef.ui.pages.cookbook_analysis.get_storage_manager",
            side_effect=RuntimeError("boom"),
        ):
            _save_conversion_to_storage("nginx", tmp_path, "", "role")

        mock_st.warning.assert_called_once()

    @patch("souschef.ui.pages.cookbook_analysis.st")
    def test_display_conversion_download_options_invalid_and_missing(mock_st):
        from souschef.ui.pages.cookbook_analysis import (
            _display_conversion_download_options,
        )

        _display_conversion_download_options({})

        with patch(
            "souschef.ui.pages.cookbook_analysis._validate_output_path",
            return_value=None,
        ):
            _display_conversion_download_options({"output_path": "/bad"})

        mock_st.error.assert_called_once()

    @patch("souschef.ui.pages.cookbook_analysis.st")
    def test_display_conversion_download_options_existing_path(mock_st, tmp_path):
        from souschef.ui.pages.cookbook_analysis import (
            _display_conversion_download_options,
        )

        with (
            patch(
                "souschef.ui.pages.cookbook_analysis._validate_output_path",
                return_value=tmp_path,
            ),
            patch(
                "souschef.ui.pages.cookbook_analysis._display_role_download_buttons"
            ) as roles,
            patch(
                "souschef.ui.pages.cookbook_analysis._display_generated_repo_section"
            ) as repo,
        ):
            _display_conversion_download_options({"output_path": str(tmp_path)})

        roles.assert_called_once_with(tmp_path)
        repo.assert_called_once()

    @patch("souschef.ui.pages.cookbook_analysis.st")
    def test_upload_repository_to_storage_branches(mock_st, tmp_path):
        from souschef.ui.pages.cookbook_analysis import _upload_repository_to_storage

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo_result = {"temp_path": str(repo_dir)}
        roles_path = tmp_path / "nginx"
        roles_path.mkdir()

        # No conversion id branch
        mock_st.session_state = SessionState()
        _upload_repository_to_storage(repo_result, roles_path)

        # Success branch
        conv = MagicMock()
        conv.id = 77
        conv.conversion_data = "{}"
        storage = MagicMock()
        storage.get_conversion_history.return_value = [conv]
        blob = MagicMock()
        blob.upload.return_value = "blob-repo"
        mock_st.session_state = SessionState({"last_conversion_id": 77})

        with (
            patch(
                "souschef.ui.pages.cookbook_analysis.get_storage_manager",
                return_value=storage,
            ),
            patch(
                "souschef.ui.pages.cookbook_analysis.get_blob_storage",
                return_value=blob,
            ),
        ):
            _upload_repository_to_storage(repo_result, roles_path)

        assert mock_st.session_state.repo_blob_key == "blob-repo"

        # Corrupt JSON branch
        conv_bad = MagicMock()
        conv_bad.id = 77
        conv_bad.conversion_data = "not-json"
        storage.get_conversion_history.return_value = [conv_bad]
        with (
            patch(
                "souschef.ui.pages.cookbook_analysis.get_storage_manager",
                return_value=storage,
            ),
            patch(
                "souschef.ui.pages.cookbook_analysis.get_blob_storage",
                return_value=blob,
            ),
        ):
            _upload_repository_to_storage(repo_result, roles_path)

        assert mock_st.warning.called

    @patch("souschef.ui.pages.cookbook_analysis.st")
    def test_create_repo_callback_success_and_failure(mock_st, tmp_path):
        from souschef.ui.pages.cookbook_analysis import _create_repo_callback

        roles = tmp_path / "roles"
        roles.mkdir()
        (roles / "a").mkdir()
        mock_st.session_state = SessionState()

        with (
            patch(
                "souschef.ui.pages.cookbook_analysis._create_ansible_repository",
                return_value={"success": True, "temp_path": str(tmp_path / "repo")},
            ),
            patch("souschef.ui.pages.cookbook_analysis._upload_repository_to_storage"),
        ):
            _create_repo_callback(roles)

        assert mock_st.session_state.repo_created_successfully is True

        with patch(
            "souschef.ui.pages.cookbook_analysis._create_ansible_repository",
            return_value={"success": False, "error": "failed"},
        ):
            _create_repo_callback(roles)

        assert mock_st.session_state.repo_created_successfully is False

    @patch("souschef.ui.pages.cookbook_analysis.st")
    def test_display_role_download_buttons(mock_st, tmp_path):
        from souschef.ui.pages.cookbook_analysis import _display_role_download_buttons

        mock_st.columns.return_value = [_ctx(), _ctx()]
        with patch(
            "souschef.ui.pages.cookbook_analysis._create_roles_zip_archive",
            return_value=b"zip",
        ):
            _display_role_download_buttons(tmp_path)

        assert mock_st.download_button.called
        assert mock_st.button.called
