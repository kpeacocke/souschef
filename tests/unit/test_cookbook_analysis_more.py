"""Additional collected tests for cookbook_analysis coverage."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


class SessionState(dict):
    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value):
        self[name] = value

    def __delattr__(self, name: str):
        if name in self:
            del self[name]
            return
        raise AttributeError(name)


def _ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=ctx)
    ctx.__exit__ = Mock(return_value=None)
    return ctx


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_save_conversion_to_storage_success(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _save_conversion_to_storage

    out = tmp_path / "roles"
    out.mkdir()
    mock_st.session_state = SessionState({"holistic_assessment": {"analysis_id": 42}})

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
            "souschef.ui.pages.cookbook_analysis.get_blob_storage", return_value=blob
        ),
    ):
        _save_conversion_to_storage(
            "nginx", out, "## Overview:\n- Total Converted Files: 3", "role"
        )

    assert mock_st.session_state.last_conversion_id == 100


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_conversion_download_options_existing_path(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _display_conversion_download_options

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
def test_upload_repository_to_storage_success(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _upload_repository_to_storage

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    roles_path = tmp_path / "nginx"
    roles_path.mkdir()

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
            "souschef.ui.pages.cookbook_analysis.get_blob_storage", return_value=blob
        ),
    ):
        _upload_repository_to_storage({"temp_path": str(repo_dir)}, roles_path)

    assert mock_st.session_state.repo_blob_key == "blob-repo"


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_create_repo_callback_success(mock_st, tmp_path):
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


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_generated_repo_section_and_helpers(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _display_generated_repo_section

    mock_st.session_state = SessionState(
        {
            "generated_repo": {
                "temp_path": str(tmp_path),
                "repo_type": "playbooks_and_roles",
                "files_created": ["ansible.cfg", "playbooks/site.yml"],
            },
            "repo_created_successfully": True,
        }
    )

    placeholder = _ctx()
    mock_st.button.return_value = False

    with patch(
        "souschef.ui.pages.cookbook_analysis._create_repository_zip",
        return_value=b"zip",
    ):
        _display_generated_repo_section(placeholder)

    assert mock_st.download_button.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_cookbook_activity_breakdown_dict_and_object(mock_st):
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

    with patch("souschef.ui.pages.cookbook_analysis.pd") as mock_pd:
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

    assert mock_st.dataframe.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_pipeline_smoke(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import (
        _convert_and_download_playbooks,
        _convert_recipes,
        _convert_templates,
    )

    recipe = tmp_path / "default.rb"
    recipe.write_text("package 'nginx'")
    cookbook = tmp_path / "cb"
    cookbook.mkdir()
    (cookbook / "recipes").mkdir()

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

    with patch(
        "souschef.ui.pages.cookbook_analysis._convert_templates_impl",
        return_value={"success": True, "results": []},
    ):
        templates = _convert_templates("nginx", cookbook)
    assert templates == []

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
            [{"status": "Analysed", "name": "nginx", "path": str(cookbook)}]
        )

    dl.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_handle_dashboard_upload_success(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _handle_dashboard_upload

    mock_st.session_state = SessionState(
        {
            "uploaded_file_data": b"bytes",
            "uploaded_file_name": "a.zip",
            "uploaded_file_type": "application/zip",
        }
    )
    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.side_effect = [False, False]
    mock_st.spinner.return_value = _ctx()

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis.extract_archive",
            return_value=(tmp_path, tmp_path, tmp_path / "a.zip"),
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._validate_and_list_cookbooks"
        ) as val,
    ):
        _handle_dashboard_upload()

    val.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_instructions(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_instructions

    mock_st.expander.return_value = _ctx()
    _display_instructions()

    assert mock_st.markdown.called


def test_create_ansible_repository_success_and_failure(tmp_path):
    from souschef.ui.pages.cookbook_analysis import _create_ansible_repository

    out = tmp_path / "roles"
    out.mkdir()

    with (
        patch("souschef.ui.pages.cookbook_analysis._get_git_path"),
        patch(
            "souschef.ui.pages.cookbook_analysis._determine_num_recipes", return_value=2
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.analyse_conversion_output",
            return_value="playbooks_and_roles",
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.generate_ansible_repository",
            return_value={
                "success": True,
                "repo_type": "playbooks_and_roles",
                "files_created": [],
            },
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._get_roles_directory",
            return_value=tmp_path / "repo" / "roles",
        ),
        patch("souschef.ui.pages.cookbook_analysis._copy_roles_to_repository"),
        patch("souschef.ui.pages.cookbook_analysis._commit_repository_changes"),
    ):
        result = _create_ansible_repository(str(out), num_roles=1)

    assert result["success"] is True
    assert "temp_path" in result

    with patch(
        "souschef.ui.pages.cookbook_analysis._get_git_path",
        side_effect=RuntimeError("git missing"),
    ):
        failed = _create_ansible_repository(str(out), num_roles=1)
    assert failed["success"] is False


def test_create_repository_zip_filters(tmp_path):
    from souschef.ui.pages.cookbook_analysis import _create_repository_zip

    repo = tmp_path / "ansible_repository"
    repo.mkdir()
    (repo / "keep.yml").write_text("x")
    (repo / ".gitignore").write_text("*")
    (repo / ".hidden").write_text("secret")
    (repo / "Thumbs.db").write_text("bad")

    data = _create_repository_zip(str(repo))
    assert isinstance(data, bytes)
    assert len(data) > 0


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_repo_section_helpers(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import (
        _display_repo_clear_button,
        _display_repo_download,
        _display_repo_git_instructions,
        _display_repo_info,
        _display_repo_structure,
        _should_display_generated_repo,
    )

    repo_result = {
        "temp_path": str(tmp_path),
        "repo_type": "playbooks_and_roles",
        "files_created": ["a", "b"],
    }

    mock_st.session_state = SessionState(
        {"generated_repo": repo_result, "repo_created_successfully": True}
    )
    assert _should_display_generated_repo() is True

    mock_st.expander.return_value = _ctx()
    with patch(
        "souschef.ui.pages.cookbook_analysis._create_repository_zip",
        return_value=b"zip",
    ):
        _display_repo_info(repo_result)
        _display_repo_structure(repo_result)
        _display_repo_download(repo_result)
        _display_repo_git_instructions()

    assert mock_st.info.called
    assert mock_st.download_button.called

    mock_st.button.return_value = True
    _display_repo_clear_button(repo_result)
    assert "generated_repo" not in mock_st.session_state


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_handle_dashboard_upload_error_paths(mock_st):
    from souschef.ui.pages.cookbook_analysis import _handle_dashboard_upload

    mock_st.session_state = SessionState(
        {
            "uploaded_file_data": b"bytes",
            "uploaded_file_name": "a.zip",
            "uploaded_file_type": "application/zip",
        }
    )
    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.side_effect = [False, False]
    mock_st.spinner.return_value = _ctx()

    with patch(
        "souschef.ui.pages.cookbook_analysis.extract_archive",
        side_effect=RuntimeError("bad archive"),
    ):
        _handle_dashboard_upload()

    mock_st.error.assert_called()
    assert "uploaded_file_data" not in mock_st.session_state


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_analysis_pipeline_helpers(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import (
        _find_cookbook_directory,
        _perform_cookbook_analysis,
        _setup_analysis_progress,
        _update_progress,
        analyse_selected_cookbooks,
    )

    mock_st.session_state = SessionState()

    # setup progress
    mock_st.progress.return_value = MagicMock()
    mock_st.empty.return_value = MagicMock()
    progress, status = _setup_analysis_progress()
    assert progress is not None
    assert status is not None

    # update progress with and without AI
    with patch(
        "souschef.ui.pages.cookbook_analysis.load_ai_settings",
        return_value={"provider": "OpenAI (GPT)", "api_key": "k"},
    ):
        _update_progress(status, "nginx", 1, 2)
    assert status.text.called

    # find cookbook directory
    root = tmp_path / "cookbooks"
    root.mkdir()
    cb = root / "nginx"
    cb.mkdir()
    (cb / "metadata.rb").write_text("name 'nginx'\nversion '1.0.0'\n")

    with patch(
        "souschef.ui.pages.cookbook_analysis.parse_cookbook_metadata",
        return_value={"name": "nginx"},
    ):
        found = _find_cookbook_directory(str(root), "nginx")
    assert found is not None

    # perform analysis loop
    mock_progress = MagicMock()
    mock_status = MagicMock()
    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._find_cookbook_directory",
            return_value=cb,
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._analyse_single_cookbook",
            return_value={"name": "nginx", "status": "Analysed"},
        ),
    ):
        results = _perform_cookbook_analysis(
            str(root), ["nginx"], mock_progress, mock_status
        )
    assert len(results) == 1

    # analyse selected cookbooks wrapper
    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._setup_analysis_progress",
            return_value=(MagicMock(), MagicMock()),
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._perform_cookbook_analysis",
            return_value=[{"name": "nginx", "status": "Analysed"}],
        ),
        patch("souschef.ui.pages.cookbook_analysis._cleanup_progress_indicators"),
    ):
        analyse_selected_cookbooks(str(root), ["nginx"])

    assert mock_st.session_state.total_cookbooks == 1
    mock_st.rerun.assert_called()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_project_analysis_helpers(mock_st):
    from souschef.ui.pages.cookbook_analysis import (
        _analyse_project_dependencies,
        _build_dependency_graph,
        analyse_project_cookbooks,
    )

    mock_st.session_state = SessionState()

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._find_cookbook_directory",
            return_value=Path("/tmp/cook"),
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.analyse_cookbook_dependencies",
            return_value="## Dependency Graph:\n├── base",
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._extract_dependencies_from_markdown",
            return_value=["base"],
        ),
    ):
        graph = _build_dependency_graph("/tmp", ["nginx"])
    assert graph["nginx"] == ["base"]

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._build_dependency_graph",
            return_value={"nginx": []},
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._calculate_migration_order",
            return_value=[],
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._find_circular_dependencies",
            return_value=[],
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._calculate_project_metrics",
            return_value={"project_complexity": "Low", "project_effort_days": 1},
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._generate_project_recommendations",
            return_value=["ok"],
        ),
    ):
        pa = _analyse_project_dependencies("/tmp", ["nginx"], [])
    assert "dependency_graph" in pa

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._setup_analysis_progress",
            return_value=(MagicMock(), MagicMock()),
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._perform_cookbook_analysis",
            return_value=[{"name": "nginx"}],
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._analyse_project_dependencies",
            return_value={"dependency_graph": {}},
        ),
        patch("souschef.ui.pages.cookbook_analysis._cleanup_progress_indicators"),
    ):
        analyse_project_cookbooks("/tmp", ["nginx"])

    mock_st.rerun.assert_called()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_show_cookbook_analysis_page_branches(mock_st):
    from souschef.ui.pages.cookbook_analysis import show_cookbook_analysis_page

    # Init + show input
    mock_st.session_state = SessionState()
    with (
        patch("souschef.ui.pages.cookbook_analysis._setup_cookbook_analysis_ui"),
        patch("souschef.ui.pages.cookbook_analysis._show_analysis_input") as show_in,
    ):
        show_cookbook_analysis_page()
    show_in.assert_called_once()

    # Results branch
    mock_st.session_state = SessionState({"analysis_results": [{"name": "x"}]})
    with (
        patch("souschef.ui.pages.cookbook_analysis._setup_cookbook_analysis_ui"),
        patch("souschef.ui.pages.cookbook_analysis._display_results_view") as view,
    ):
        show_cookbook_analysis_page()
    view.assert_called_once()

    # Dashboard upload branch
    mock_st.session_state = SessionState(
        {"analysis_results": None, "uploaded_file_data": b"x"}
    )
    with (
        patch("souschef.ui.pages.cookbook_analysis._setup_cookbook_analysis_ui"),
        patch("souschef.ui.pages.cookbook_analysis._handle_dashboard_upload") as up,
    ):
        show_cookbook_analysis_page()
    up.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_show_analysis_input_branches(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _show_analysis_input

    # Directory path branch
    mock_st.session_state = SessionState({"temp_dir": None})
    mock_st.radio.return_value = "Directory Path"
    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._get_cookbook_path_input",
            return_value=str(tmp_path),
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._validate_and_list_cookbooks"
        ) as val,
        patch("souschef.ui.pages.cookbook_analysis._display_instructions"),
    ):
        _show_analysis_input()
    val.assert_called_once()

    # Upload archive success branch
    mock_st.session_state = SessionState({"temp_dir": None})
    mock_st.radio.return_value = "Upload Archive"
    mock_st.spinner.return_value = _ctx()
    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._get_archive_upload_input",
            return_value=MagicMock(),
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.extract_archive",
            return_value=(tmp_path, tmp_path, tmp_path / "a.zip"),
        ),
        patch("souschef.ui.pages.cookbook_analysis._validate_and_list_cookbooks"),
        patch("souschef.ui.pages.cookbook_analysis._display_instructions"),
    ):
        _show_analysis_input()
    assert mock_st.success.called

    # Upload archive failure branch
    mock_st.session_state = SessionState({"temp_dir": None})
    mock_st.radio.return_value = "Upload Archive"
    mock_st.spinner.return_value = _ctx()
    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._get_archive_upload_input",
            return_value=MagicMock(),
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.extract_archive",
            side_effect=OSError("bad"),
        ),
    ):
        _show_analysis_input()
    assert mock_st.error.called


@patch("souschef.ui.pages.cookbook_analysis.parse_cookbook_metadata")
def test_load_cookbook_metadata_success(mock_parse, tmp_path):
    """Test successful metadata loading."""
    from souschef.ui.pages.cookbook_analysis import _load_cookbook_metadata

    (tmp_path / "metadata.rb").write_text("name 'test'")
    mock_parse.return_value = {"name": "test", "version": "1.0.0"}

    result = _load_cookbook_metadata("test", tmp_path)
    assert result == {"name": "test", "version": "1.0.0"}
    mock_parse.assert_called_once()


def test_load_cookbook_metadata_missing_file(tmp_path):
    """Test metadata loading when metadata.rb is missing."""
    from souschef.ui.pages.cookbook_analysis import _load_cookbook_metadata

    result = _load_cookbook_metadata("test", tmp_path)
    assert result["status"] == "Failed"
    assert "No metadata.rb found" in result["recommendations"]


@patch("souschef.ui.pages.cookbook_analysis.parse_cookbook_metadata")
def test_load_cookbook_metadata_parse_error(mock_parse, tmp_path):
    """Test metadata loading when parsing fails."""
    from souschef.ui.pages.cookbook_analysis import _load_cookbook_metadata

    (tmp_path / "metadata.rb").write_text("bad syntax")
    mock_parse.side_effect = ValueError("parse error")

    result = _load_cookbook_metadata("test", tmp_path)
    assert result["status"] == "Failed"
    assert "Failed to parse metadata" in result["recommendations"]


def test_should_use_ai_with_valid_config():
    """Test AI usage check with valid configuration."""
    from souschef.ui.pages.cookbook_analysis import _should_use_ai

    config = {"provider": "anthropic", "api_key": "key123"}
    assert _should_use_ai(config) is True


def test_should_use_ai_with_invalid_configs():
    """Test AI usage check with various invalid configurations."""
    from souschef.ui.pages.cookbook_analysis import _should_use_ai

    # No provider
    assert _should_use_ai({}) is False
    # Local provider
    assert _should_use_ai({"provider": "Local Model", "api_key": "key"}) is False
    # No API key
    assert _should_use_ai({"provider": "anthropic"}) is False


@patch("souschef.ui.pages.cookbook_analysis.assess_single_cookbook_with_ai")
def test_run_ai_analysis(mock_assess, tmp_path):
    """Test AI-enhanced analysis execution."""
    from souschef.ui.pages.cookbook_analysis import _run_ai_analysis

    mock_assess.return_value = {"complexity": "High", "estimated_hours": 20}
    config = {
        "provider": "anthropic",
        "api_key": "key123",
        "model": "claude-3-5-sonnet-20241022",
        "temperature": 0.7,
        "max_tokens": 4000,
    }

    result = _run_ai_analysis(tmp_path, config)
    assert result["complexity"] == "High"
    mock_assess.assert_called_once()


def test_determine_ai_provider_mappings():
    """Test AI provider name determination from config."""
    from souschef.ui.pages.cookbook_analysis import _determine_ai_provider

    # Test known mappings
    assert _determine_ai_provider({"provider": "Anthropic Claude"}) == "anthropic"
    assert _determine_ai_provider({"provider": "OpenAI"}) == "openai"
    assert _determine_ai_provider({"provider": "IBM Watsonx"}) == "watson"
    assert _determine_ai_provider({"provider": "Red Hat Lightspeed"}) == "lightspeed"

    # Test fallback for unknown provider (converts to lowercase with underscores)
    assert _determine_ai_provider({"provider": "Custom AI"}) == "custom_ai"

    # Test empty/None provider defaults to anthropic
    assert _determine_ai_provider({}) == "anthropic"


def test_run_rule_based_analysis_multi_cookbook(tmp_path):
    """Test rule-based analysis with multi-cookbook response structure."""
    from souschef.ui.pages.cookbook_analysis import _run_rule_based_analysis

    with patch("souschef.assessment.parse_chef_migration_assessment") as mock_assess:
        mock_assess.return_value = {
            "cookbook_assessments": [
                {"name": "test", "complexity_score": 50, "estimated_effort_days": 2}
            ],
            "complexity": "Medium",
            "estimated_hours": 16,
            "recommendations": [{"recommendation": "Test rec"}],
        }

        result = _run_rule_based_analysis(tmp_path)
        assert result["complexity"] == "Medium"
        assert result["estimated_hours"] == 16
        assert "recommendations" in result


def test_run_rule_based_analysis_single_cookbook(tmp_path):
    """Test rule-based analysis with single cookbook response."""
    from souschef.ui.pages.cookbook_analysis import _run_rule_based_analysis

    with patch("souschef.assessment.parse_chef_migration_assessment") as mock_assess:
        mock_assess.return_value = {
            "complexity": "Low",
            "estimated_hours": 8,
            "recommendations": "Simple cookbook",
        }

        result = _run_rule_based_analysis(tmp_path)
        assert result["complexity"] == "Low"
        assert result["estimated_hours"] == 8


def test_create_successful_analysis():
    """Test creation of successful analysis result."""
    from souschef.ui.pages.cookbook_analysis import _create_successful_analysis

    metadata = {
        "version": "1.2.3",
        "maintainer": "Chef Team",
        "description": "Test cookbook",
        "depends": ["dep1", "dep2"],
    }
    assessment = {
        "complexity": "High",
        "estimated_hours": 40,
        "recommendations": "Needs careful migration",
    }

    result = _create_successful_analysis(
        "nginx", Path("/cookbooks/nginx"), assessment, metadata
    )
    assert result["name"] == "nginx"
    assert result["version"] == "1.2.3"
    assert result["dependencies"] == 2
    assert result["complexity"] == "High"
    assert result["estimated_hours"] == 40
    assert result["status"] == "Analysed"


def test_format_recommendations_with_full_assessment():
    """Test recommendation formatting with complete assessment data."""
    from souschef.ui.pages.cookbook_analysis import (
        _format_recommendations_from_assessment,
    )

    cookbook_assessment = {
        "complexity_score": 75,
        "estimated_effort_days": 5,
        "migration_priority": "High",
        "key_findings": ["Finding 1", "Finding 2"],
    }
    overall_assessment = {
        "recommendations": [
            {"recommendation": "Use phased approach"},
            {"recommendation": "Add extensive tests"},
        ]
    }

    result = _format_recommendations_from_assessment(
        cookbook_assessment, overall_assessment
    )
    assert "Complexity Score: 75/100" in result
    assert "Estimated Effort:" in result
    assert "Migration Priority: High" in result
    assert "Finding 1" in result
    assert "Use phased approach" in result


def test_format_recommendations_with_string_recommendations():
    """Test recommendation formatting with string-based recommendations."""
    from souschef.ui.pages.cookbook_analysis import (
        _format_recommendations_from_assessment,
    )

    cookbook_assessment = {}
    overall_assessment = {"recommendations": "Single string recommendation"}

    result = _format_recommendations_from_assessment(
        cookbook_assessment, overall_assessment
    )
    assert "Single string recommendation" in result


def test_format_recommendations_minimal():
    """Test recommendation formatting with minimal data."""
    from souschef.ui.pages.cookbook_analysis import (
        _format_recommendations_from_assessment,
    )

    result = _format_recommendations_from_assessment({}, {})
    assert result == "Analysis completed"


@patch("souschef.ui.pages.cookbook_analysis.load_ai_settings")
@patch("souschef.ui.pages.cookbook_analysis.parse_cookbook_metadata")
@patch("souschef.ui.pages.cookbook_analysis._validate_cookbook_structure")
def test_get_error_context_with_ai(mock_validate, mock_parse, mock_load_ai, tmp_path):
    """Test error context generation with AI configuration."""
    from souschef.ui.pages.cookbook_analysis import _get_error_context

    (tmp_path / "metadata.rb").write_text("name 'test'")
    mock_validate.return_value = {"recipes": False, "attributes": True}
    mock_parse.return_value = {"name": "test"}
    mock_load_ai.return_value = {"provider": "anthropic", "api_key": "key123"}

    context = _get_error_context(tmp_path)
    assert "Missing: recipes" in context
    assert "Using AI analysis with anthropic" in context


@patch("souschef.ui.pages.cookbook_analysis.load_ai_settings")
@patch("souschef.ui.pages.cookbook_analysis._validate_cookbook_structure")
def test_get_error_context_no_ai(mock_validate, mock_load_ai, tmp_path):
    """Test error context generation without AI configuration."""
    from souschef.ui.pages.cookbook_analysis import _get_error_context

    mock_validate.return_value = {"recipes": True, "attributes": True}
    mock_load_ai.return_value = {"provider": "local"}

    context = _get_error_context(tmp_path)
    assert "Using rule-based analysis" in context


def test_create_failed_analysis(tmp_path):
    """Test creation of failed analysis result."""
    from souschef.ui.pages.cookbook_analysis import _create_failed_analysis

    with patch(
        "souschef.ui.pages.cookbook_analysis._get_error_context",
        return_value="Context info",
    ):
        result = _create_failed_analysis("nginx", tmp_path, "Parse error occurred")

    assert result["name"] == "nginx"
    assert result["status"] == "Failed"
    assert result["complexity"] == "Error"
    assert "Parse error occurred" in result["recommendations"]
    assert "Context: Context info" in result["recommendations"]


@patch("souschef.ui.pages.cookbook_analysis.analyse_cookbook_dependencies")
@patch("souschef.ui.pages.cookbook_analysis._find_cookbook_directory")
def test_build_dependency_graph_success(mock_find, mock_analyse):
    """Test building dependency graph successfully."""
    from souschef.ui.pages.cookbook_analysis import _build_dependency_graph

    mock_find.return_value = Path("/path/cookbook1")
    mock_analyse.return_value = "## Dependency Graph:\n├── dep1\n├── dep2"

    graph = _build_dependency_graph("/path", ["cookbook1"])
    assert "cookbook1" in graph
    assert "dep1" in graph["cookbook1"]
    assert "dep2" in graph["cookbook1"]


@patch("souschef.ui.pages.cookbook_analysis.analyse_cookbook_dependencies")
@patch("souschef.ui.pages.cookbook_analysis._find_cookbook_directory")
def test_build_dependency_graph_with_failure(mock_find, mock_analyse):
    """Test building dependency graph with analysis failure."""
    from souschef.ui.pages.cookbook_analysis import _build_dependency_graph

    mock_find.return_value = Path("/path/cookbook1")
    mock_analyse.side_effect = ValueError("analysis failed")

    graph = _build_dependency_graph("/path", ["cookbook1"])
    assert graph["cookbook1"] == []


def test_extract_dependencies_from_markdown():
    """Test extracting dependencies from markdown text."""
    from souschef.ui.pages.cookbook_analysis import _extract_dependencies_from_markdown

    markdown = """
## Cookbook Analysis
Some text
## Dependency Graph:
├── dependency1
├── dependency2
├── External dependencies:
## Other Section
More text
"""
    deps = _extract_dependencies_from_markdown(markdown)
    assert "dependency1" in deps
    assert "dependency2" in deps
    assert "External dependencies:" not in deps


def test_perform_topological_sort_simple():
    """Test topological sort with simple dependency graph."""
    from souschef.ui.pages.cookbook_analysis import _perform_topological_sort

    graph = {"a": [], "b": ["a"], "c": ["b"]}
    order = _perform_topological_sort(graph)
    assert order.index("a") < order.index("b")
    assert order.index("b") < order.index("c")


def test_perform_topological_sort_circular():
    """Test topological sort with circular dependency."""
    from souschef.ui.pages.cookbook_analysis import _perform_topological_sort

    graph = {"a": ["b"], "b": ["c"], "c": ["a"]}
    order = _perform_topological_sort(graph)
    # Circular dependency should cause incomplete sort
    assert len(order) < 3


def test_fallback_migration_order():
    """Test fallback migration order based on complexity."""
    from souschef.ui.pages.cookbook_analysis import _fallback_migration_order

    results = [
        {"name": "high", "complexity": "High", "dependencies": 3},
        {"name": "low", "complexity": "Low", "dependencies": 0},
        {"name": "med", "complexity": "Medium", "dependencies": 1},
    ]

    order = _fallback_migration_order(results)
    assert order == ["low", "med", "high"]


def test_get_migration_reason_no_dependencies():
    """Test migration reason for cookbook with no dependencies."""
    from souschef.ui.pages.cookbook_analysis import _get_migration_reason

    reason = _get_migration_reason("nginx", {"nginx": []}, 1)
    assert "No dependencies" in reason


def test_get_migration_reason_with_dependencies():
    """Test migration reason for cookbook with dependencies."""
    from souschef.ui.pages.cookbook_analysis import _get_migration_reason

    graph = {"app": ["dep1", "dep2", "dep3", "dep4", "dep5"]}
    reason = _get_migration_reason("app", graph, 3)
    assert "Depends on: dep1, dep2, dep3 and 2 more" in reason


def test_find_circular_dependencies():
    """Test finding circular dependencies in graph."""
    from souschef.ui.pages.cookbook_analysis import _find_circular_dependencies

    graph = {"a": ["b"], "b": ["c"], "c": ["a"], "d": []}
    circular = _find_circular_dependencies(graph)
    assert len(circular) == 1
    assert circular[0]["type"] == "circular_dependency"
    assert circular[0]["severity"] == "high"


def test_calculate_project_metrics():
    """Test calculating project-level metrics."""
    from souschef.ui.pages.cookbook_analysis import _calculate_project_metrics

    results = [
        {"estimated_hours": 40, "complexity": "High"},
        {"estimated_hours": 16, "complexity": "Low"},
    ]
    graph = {"a": ["b"], "b": []}

    metrics = _calculate_project_metrics(results, graph)
    assert metrics["project_complexity"] in ["Low", "Medium", "High"]
    assert metrics["project_effort_days"] == 7.0
    assert metrics["migration_strategy"] in ["phased", "parallel", "big_bang"]


def test_generate_project_recommendations_phased():
    """Test generating recommendations for phased strategy."""
    from souschef.ui.pages.cookbook_analysis import _generate_project_recommendations

    project_analysis = {
        "migration_strategy": "phased",
        "project_complexity": "High",
        "project_effort_days": 50,
        "dependency_density": 2.5,
        "circular_dependencies": [],
    }
    results = [{"name": "cb1"}] * 15

    recs = _generate_project_recommendations(project_analysis, results)
    assert any("phased migration" in r for r in recs)
    assert any("High dependency density" in r for r in recs)
    assert any("dedicated migration team" in r for r in recs)


def test_generate_project_recommendations_with_circular_deps():
    """Test generating recommendations with circular dependencies."""
    from souschef.ui.pages.cookbook_analysis import _generate_project_recommendations

    project_analysis = {
        "migration_strategy": "parallel",
        "project_complexity": "Medium",
        "project_effort_days": 20,
        "dependency_density": 1.0,
        "circular_dependencies": [{"cookbooks": ["a", "b"]}],
        "parallel_tracks": 2,
    }
    results = [{"name": "cb1"}] * 5

    recs = _generate_project_recommendations(project_analysis, results)
    assert any("circular dependency" in r for r in recs)
    assert any("parallel migration with 2 tracks" in r for r in recs)


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_analysis_results_with_back_button(mock_st):
    """Test displaying analysis results with back button functionality."""
    from souschef.ui.pages.cookbook_analysis import _display_analysis_results

    mock_st.session_state = SessionState(
        {
            "analysis_info_messages": ["Info 1", "Info 2"],
            "temp_dir": Path("/tmp/test"),
        }
    )
    mock_st.button.return_value = False
    mock_st.columns.return_value = [MagicMock(), MagicMock()]

    with (
        patch("souschef.ui.pages.cookbook_analysis._display_analysis_summary"),
        patch("souschef.ui.pages.cookbook_analysis._display_results_table"),
        patch("souschef.ui.pages.cookbook_analysis._display_detailed_analysis"),
        patch("souschef.ui.pages.cookbook_analysis._display_download_option"),
    ):
        _display_analysis_results([{"name": "test"}], 1)

    assert mock_st.info.call_count == 2
    assert mock_st.success.called


@patch("souschef.ui.pages.cookbook_analysis._create_successful_analysis")
@patch("souschef.ui.pages.cookbook_analysis._run_ai_analysis")
@patch("souschef.ui.pages.cookbook_analysis._should_use_ai")
@patch("souschef.ui.pages.cookbook_analysis.load_ai_settings")
@patch("souschef.ui.pages.cookbook_analysis._load_cookbook_metadata")
def test_analyse_single_cookbook_success_with_ai(
    mock_load_meta,
    mock_load_ai,
    mock_should_use,
    mock_run_ai,
    mock_create_success,
    tmp_path,
):
    """Test successful cookbook analysis using AI."""
    from souschef.ui.pages.cookbook_analysis import _analyse_single_cookbook

    mock_load_meta.return_value = {"name": "nginx", "version": "1.0.0", "depends": []}
    mock_load_ai.return_value = {"provider": "anthropic", "api_key": "key123"}
    mock_should_use.return_value = True
    mock_run_ai.return_value = {"complexity": "Medium", "estimated_hours": 20}
    mock_create_success.return_value = {
        "status": "Analysed",
        "name": "nginx",
        "complexity": "Medium",
    }

    result = _analyse_single_cookbook("nginx", tmp_path)

    assert result["status"] == "Analysed"
    assert result["name"] == "nginx"
    assert result["complexity"] == "Medium"
    mock_run_ai.assert_called_once()
    mock_create_success.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis._create_successful_analysis")
@patch("souschef.ui.pages.cookbook_analysis._run_rule_based_analysis")
@patch("souschef.ui.pages.cookbook_analysis._should_use_ai")
@patch("souschef.ui.pages.cookbook_analysis.load_ai_settings")
@patch("souschef.ui.pages.cookbook_analysis._load_cookbook_metadata")
def test_analyse_single_cookbook_success_rule_based(
    mock_load_meta,
    mock_load_ai,
    mock_should_use,
    mock_run_rule,
    mock_create_success,
    tmp_path,
):
    """Test successful cookbook analysis using rule-based."""
    from souschef.ui.pages.cookbook_analysis import _analyse_single_cookbook

    mock_load_meta.return_value = {"name": "nginx", "version": "1.0.0", "depends": []}
    mock_load_ai.return_value = {"provider": "Local Model"}
    mock_should_use.return_value = False
    mock_run_rule.return_value = {"complexity": "Low", "estimated_hours": 8}
    mock_create_success.return_value = {"status": "Analysed", "complexity": "Low"}

    result = _analyse_single_cookbook("nginx", tmp_path)

    assert result["status"] == "Analysed"
    assert result["complexity"] == "Low"
    mock_run_rule.assert_called_once()
    mock_create_success.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis._load_cookbook_metadata")
def test_analyse_single_cookbook_metadata_error(mock_load_meta, tmp_path):
    """Test cookbook analysis when metadata loading fails."""
    from souschef.ui.pages.cookbook_analysis import _analyse_single_cookbook

    # Return error result from metadata loading
    mock_load_meta.return_value = {
        "name": "nginx",
        "status": "Failed",
        "error": "metadata",
        "recommendations": "No metadata.rb found",
    }

    result = _analyse_single_cookbook("nginx", tmp_path)

    assert result["status"] == "Failed"
    assert "No metadata.rb found" in result["recommendations"]


@patch("souschef.ui.pages.cookbook_analysis._create_failed_analysis")
@patch("souschef.ui.pages.cookbook_analysis._should_use_ai")
@patch("souschef.ui.pages.cookbook_analysis.load_ai_settings")
@patch("souschef.ui.pages.cookbook_analysis._load_cookbook_metadata")
def test_analyse_single_cookbook_assessment_error(
    mock_load_meta, mock_load_ai, mock_should_use, mock_create_failed, tmp_path
):
    """Test cookbook analysis when assessment returns error."""
    from souschef.ui.pages.cookbook_analysis import _analyse_single_cookbook

    mock_load_meta.return_value = {"name": "nginx", "version": "1.0.0"}
    mock_load_ai.return_value = {"provider": "Local Model"}
    mock_should_use.return_value = False
    mock_create_failed.return_value = {
        "status": "Failed",
        "recommendations": "Assessment failed",
    }

    with patch("souschef.assessment.parse_chef_migration_assessment") as mock_assess:
        mock_assess.return_value = {"error": "Assessment failed"}
        result = _analyse_single_cookbook("nginx", tmp_path)

    assert result["status"] == "Failed"
    assert "Assessment failed" in result["recommendations"]
    mock_create_failed.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis._create_failed_analysis")
@patch("souschef.ui.pages.cookbook_analysis.load_ai_settings")
@patch("souschef.ui.pages.cookbook_analysis._load_cookbook_metadata")
def test_analyse_single_cookbook_exception(
    mock_load_meta, mock_load_ai, mock_create_failed, tmp_path
):
    """Test cookbook analysis exception handling."""
    from souschef.ui.pages.cookbook_analysis import _analyse_single_cookbook

    mock_load_meta.return_value = {"name": "nginx", "version": "1.0.0"}
    mock_load_ai.side_effect = RuntimeError("Unexpected error")
    mock_create_failed.return_value = {
        "status": "Failed",
        "recommendations": "Unexpected error\n\nTraceback: ...",
    }

    result = _analyse_single_cookbook("nginx", tmp_path)

    assert result["status"] == "Failed"
    assert "recommendations" in result
    mock_create_failed.assert_called_once()
    # Check that create_failed was called with error details
    call_args = mock_create_failed.call_args[0]
    assert "Unexpected error" in call_args[2]


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_single_cookbook_no_recipes_dir(mock_st, tmp_path):
    """Test cookbook conversion when recipes directory is missing."""
    from souschef.ui.pages.cookbook_analysis import _convert_single_cookbook

    result = {"name": "nginx", "path": str(tmp_path)}
    playbooks, templates = _convert_single_cookbook(result)

    assert playbooks == []
    assert templates == []
    assert mock_st.warning.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_playbook_previews(mock_st):
    """Test displaying playbook previews."""
    from souschef.ui.pages.cookbook_analysis import _display_playbook_previews

    mock_st.expander.return_value = _ctx()
    playbooks = [
        {
            "cookbook_name": "nginx",
            "recipe_file": "default.rb",
            "playbook_content": "- hosts: all\n  tasks:\n    - name: install\n      apt: name=nginx",
            "conversion_method": "AI-enhanced",
        },
        {
            "cookbook_name": "apache",
            "recipe_file": "install.rb",
            "playbook_content": "- hosts: all",
            "conversion_method": "Deterministic",
        },
    ]

    _display_playbook_previews(playbooks)

    assert mock_st.subheader.call_count == 2
    assert mock_st.code.call_count == 2


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_template_previews_with_templates(mock_st):
    """Test displaying template previews with templates."""
    from souschef.ui.pages.cookbook_analysis import _display_template_previews

    mock_st.expander.return_value = _ctx()
    mock_st.container.return_value = _ctx()
    templates = [
        {
            "cookbook_name": "nginx",
            "template_file": "nginx.conf.j2",
            "original_file": "nginx.conf.erb",
            "template_content": "server { listen {{ port }}; }",
            "variables": ["port", "server_name"],
        }
    ]

    _display_template_previews(templates)

    assert mock_st.subheader.called
    assert mock_st.code.call_count >= 1


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_template_previews_empty(mock_st):
    """Test displaying template previews with no templates."""
    from souschef.ui.pages.cookbook_analysis import _display_template_previews

    _display_template_previews([])

    assert not mock_st.expander.called


def test_create_playbook_archive():
    """Test creating playbook archive."""
    from souschef.ui.pages.cookbook_analysis import _create_playbook_archive

    playbooks = [
        {
            "cookbook_name": "nginx",
            "recipe_file": "default.rb",
            "playbook_content": "- hosts: all",
        }
    ]
    templates = [
        {
            "cookbook_name": "nginx",
            "template_file": "nginx.conf.j2",
            "original_file": "nginx.conf.erb",
            "template_content": "server {}",
        }
    ]

    archive_data = _create_playbook_archive(playbooks, templates)

    assert isinstance(archive_data, bytes)
    assert len(archive_data) > 0


def test_build_download_label():
    """Test building download button label."""
    from souschef.ui.pages.cookbook_analysis import _build_download_label

    # With templates
    label = _build_download_label(5, 3)
    assert "5 playbooks" in label
    assert "3 templates" in label

    # Without templates
    label = _build_download_label(5, 0)
    assert "5 playbooks" in label
    assert "templates" not in label


def test_write_playbooks_to_temp_dir(tmp_path):
    """Test writing playbooks to temporary directory."""
    from souschef.ui.pages.cookbook_analysis import _write_playbooks_to_temp_dir

    playbooks = [
        {
            "cookbook_name": "nginx",
            "recipe_file": "default.rb",
            "playbook_content": "- hosts: all",
        }
    ]

    _write_playbooks_to_temp_dir(playbooks, str(tmp_path))

    written_files = list(tmp_path.glob("*.yml"))
    assert len(written_files) == 1
    assert "nginx_default.yml" in written_files[0].name


def test_get_playbooks_dir_existing(tmp_path):
    """Test getting playbooks directory when it exists."""
    from souschef.ui.pages.cookbook_analysis import _get_playbooks_dir

    playbooks_dir = tmp_path / "playbooks"
    playbooks_dir.mkdir()

    result = _get_playbooks_dir({"temp_path": str(tmp_path)})

    assert result == playbooks_dir


def test_get_playbooks_dir_collection_structure(tmp_path):
    """Test getting playbooks directory with collection structure."""
    from souschef.ui.pages.cookbook_analysis import _get_playbooks_dir

    result = _get_playbooks_dir({"temp_path": str(tmp_path)})

    # Should create collection structure
    assert "playbooks" in str(result)
    assert result.exists()


def test_copy_playbooks_to_repo(tmp_path):
    """Test copying playbooks to repository."""
    from souschef.ui.pages.cookbook_analysis import _copy_playbooks_to_repo

    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    (temp_dir / "test.yml").write_text("- hosts: all")

    repo_playbooks = tmp_path / "repo" / "playbooks"
    repo_playbooks.mkdir(parents=True)

    _copy_playbooks_to_repo(str(temp_dir), repo_playbooks)

    copied_files = list(repo_playbooks.glob("*.yml"))
    assert len(copied_files) == 1


@patch("souschef.ui.pages.cookbook_analysis.subprocess.run")
def test_commit_playbooks_to_git_success(mock_run, tmp_path):
    """Test committing playbooks to git."""
    from souschef.ui.pages.cookbook_analysis import _commit_playbooks_to_git

    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    (temp_dir / "test.yml").write_text("- hosts: all")

    mock_run.return_value = MagicMock(returncode=0)

    _commit_playbooks_to_git(str(temp_dir), str(tmp_path))

    assert mock_run.call_count == 2  # git add, git commit


@patch("souschef.ui.pages.cookbook_analysis.subprocess.run")
def test_commit_playbooks_to_git_failure(mock_run, tmp_path):
    """Test committing playbooks to git with failure."""
    from souschef.ui.pages.cookbook_analysis import _commit_playbooks_to_git

    mock_run.side_effect = subprocess.CalledProcessError(1, "git")

    # Should not raise exception
    _commit_playbooks_to_git(str(tmp_path), str(tmp_path))


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_handle_repo_creation_success(mock_st, tmp_path):
    """Test successful repository creation handling."""
    from souschef.ui.pages.cookbook_analysis import _handle_repo_creation

    mock_st.session_state = SessionState()
    playbooks = [{"cookbook_name": "nginx"}]

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._create_ansible_repository",
            return_value={
                "success": True,
                "temp_path": str(tmp_path),
                "repo_type": "playbooks_and_roles",
            },
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._get_playbooks_dir",
            return_value=tmp_path / "playbooks",
        ),
        patch("souschef.ui.pages.cookbook_analysis._copy_playbooks_to_repo"),
        patch("souschef.ui.pages.cookbook_analysis._commit_playbooks_to_git"),
    ):
        _handle_repo_creation(str(tmp_path), playbooks)

    assert "generated_playbook_repo" in mock_st.session_state


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_handle_repo_creation_failure(mock_st, tmp_path):
    """Test repository creation handling with failure."""
    from souschef.ui.pages.cookbook_analysis import _handle_repo_creation

    playbooks = [{"cookbook_name": "nginx"}]

    with patch(
        "souschef.ui.pages.cookbook_analysis._create_ansible_repository",
        return_value={"success": False, "error": "Git not found"},
    ):
        _handle_repo_creation(str(tmp_path), playbooks)

    assert mock_st.error.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_repo_structure_section(mock_st):
    """Test displaying repository structure section."""
    from souschef.ui.pages.cookbook_analysis import _display_repo_structure_section

    mock_st.expander.return_value = _ctx()
    repo_result = {"files_created": ["file1.yml", "file2.yml", "file3.yml"]}

    _display_repo_structure_section(repo_result)

    assert mock_st.code.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_repo_structure_section_many_files(mock_st):
    """Test displaying repository structure with many files."""
    from souschef.ui.pages.cookbook_analysis import _display_repo_structure_section

    mock_st.expander.return_value = _ctx()
    repo_result = {"files_created": [f"file{i}.yml" for i in range(50)]}

    _display_repo_structure_section(repo_result)

    assert mock_st.code.called
    assert mock_st.caption.called  # Should show "... and X more files"


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_repo_info_section(mock_st):
    """Test displaying repository info section."""
    from souschef.ui.pages.cookbook_analysis import _display_repo_info_section

    repo_result = {
        "repo_type": "playbooks_and_roles",
        "files_created": ["file1", "file2"],
    }

    _display_repo_info_section(repo_result)

    assert mock_st.info.called
    call_args = mock_st.info.call_args[0][0]
    assert "Playbooks And Roles" in call_args
    assert "2" in call_args


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_generated_repo_section_internal(mock_st, tmp_path):
    """Test displaying complete generated repository section."""
    from souschef.ui.pages.cookbook_analysis import (
        _display_generated_repo_section_internal,
    )

    mock_st.expander.return_value = _ctx()
    mock_st.button.return_value = False
    repo_result = {
        "temp_path": str(tmp_path),
        "repo_type": "playbooks_and_roles",
        "files_created": ["ansible.cfg", "playbooks/site.yml"],
    }

    with patch(
        "souschef.ui.pages.cookbook_analysis._create_repository_zip",
        return_value=b"zip_data",
    ):
        _display_generated_repo_section_internal(repo_result)

    assert mock_st.success.called
    assert mock_st.download_button.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_download_button_with_repo_creation(mock_st, tmp_path):
    """Test download button display with repo creation."""
    from souschef.ui.pages.cookbook_analysis import _display_download_button

    mock_st.session_state = SessionState()
    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.return_value = True
    mock_st.spinner.return_value = _ctx()

    playbooks = [
        {
            "cookbook_name": "nginx",
            "recipe_file": "default.rb",
            "playbook_content": "- hosts: all",
        }
    ]

    with (
        patch("souschef.ui.pages.cookbook_analysis._write_playbooks_to_temp_dir"),
        patch(
            "souschef.ui.pages.cookbook_analysis._handle_repo_creation"
        ) as handle_repo,
    ):
        _display_download_button(1, 0, b"archive_data", playbooks)

    assert mock_st.download_button.called
    handle_repo.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_download_button_show_generated_repo(mock_st, tmp_path):
    """Test download button display showing generated repo."""
    from souschef.ui.pages.cookbook_analysis import _display_download_button

    mock_st.session_state = SessionState(
        {
            "generated_playbook_repo": {
                "temp_path": str(tmp_path),
                "repo_type": "playbooks_and_roles",
                "files_created": ["ansible.cfg"],
            }
        }
    )
    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.return_value = False
    mock_st.expander.return_value = _ctx()

    with patch(
        "souschef.ui.pages.cookbook_analysis._create_repository_zip",
        return_value=b"zip_data",
    ):
        _display_download_button(1, 0, b"archive_data", None)

    assert mock_st.success.called  # From _display_generated_repo_section_internal


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_and_download_playbooks_no_successful(mock_st):
    """Test conversion with no successful results."""
    from souschef.ui.pages.cookbook_analysis import _convert_and_download_playbooks

    results = [{"status": "Failed", "name": "nginx"}]
    _convert_and_download_playbooks(results)

    assert mock_st.warning.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_and_download_playbooks_with_staging(mock_st, tmp_path):
    """Test conversion with staging for validation."""
    from souschef.ui.pages.cookbook_analysis import _convert_and_download_playbooks

    mock_st.session_state = SessionState()
    mock_st.spinner.return_value = _ctx()

    results = [{"status": "Analysed", "name": "nginx", "path": str(tmp_path)}]

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
        patch("souschef.ui.pages.cookbook_analysis._handle_playbook_download"),
        patch(
            "souschef.ui.pages.cookbook_analysis.tempfile.mkdtemp",
            return_value=str(tmp_path / "staged"),
        ),
    ):
        (tmp_path / "staged").mkdir(exist_ok=True)
        _convert_and_download_playbooks(results)

    assert "converted_playbooks_path" in mock_st.session_state
    assert mock_st.success.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_and_download_playbooks_staging_failure(mock_st, tmp_path):
    """Test conversion with staging failure."""
    from souschef.ui.pages.cookbook_analysis import _convert_and_download_playbooks

    mock_st.session_state = SessionState()
    mock_st.spinner.return_value = _ctx()

    results = [{"status": "Analysed", "name": "nginx", "path": str(tmp_path)}]

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
        patch("souschef.ui.pages.cookbook_analysis._handle_playbook_download"),
        patch(
            "souschef.ui.pages.cookbook_analysis.tempfile.mkdtemp",
            side_effect=OSError("Permission denied"),
        ),
    ):
        _convert_and_download_playbooks(results)

    assert mock_st.warning.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_download_option_branches(mock_st):
    """Test display download option with various branches."""
    from souschef.ui.pages.cookbook_analysis import _display_download_option

    # Test with AI available when button is pressed
    mock_st.session_state = SessionState({"conversion_results": None})
    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.return_value = True  # Simulate button press

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis.load_ai_settings",
            return_value={
                "provider": "anthropic",
                "api_key": "key",
                "model": "claude-3",
            },
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._create_analysis_report",
            return_value="report",
        ),
        patch("souschef.ui.pages.cookbook_analysis._convert_and_download_playbooks"),
    ):
        _display_download_option([{"status": "Analysed"}])

    # Should show AI info
    assert mock_st.info.called

    # Test without button press
    mock_st.reset_mock()
    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.return_value = False

    with patch(
        "souschef.ui.pages.cookbook_analysis._create_analysis_report",
        return_value="report",
    ):
        _display_download_option([{"status": "Analysed"}])

    # Should display options but not convert
    assert mock_st.subheader.called


def test_get_git_path_common():
    """Test finding git in common locations."""
    from souschef.ui.pages.cookbook_analysis import _get_git_path

    with patch("pathlib.Path.exists", return_value=True):
        result = _get_git_path()
        assert result in ["/usr/bin/git", "/usr/local/bin/git", "/opt/homebrew/bin/git"]


def test_get_git_path_which_command():
    """Test finding git using 'which' command."""
    from souschef.ui.pages.cookbook_analysis import _get_git_path

    mock_result = MagicMock()
    mock_result.stdout = "/custom/path/git\n"

    with (
        patch("pathlib.Path.exists", side_effect=[False, False, False, True]),
        patch("subprocess.run", return_value=mock_result),
        patch("souschef.ui.pages.cookbook_analysis.st"),
    ):
        result = _get_git_path()
        assert result == "/custom/path/git"


def test_get_git_path_git_version():
    """Test finding git using 'git --version' command."""
    from souschef.ui.pages.cookbook_analysis import _get_git_path

    mock_which_fail = MagicMock(side_effect=subprocess.CalledProcessError(1, "which"))
    mock_version_result = MagicMock()
    mock_version_result.returncode = 0

    with (
        patch("pathlib.Path.exists", return_value=False),
        patch("subprocess.run", side_effect=[mock_which_fail, mock_version_result]),
        patch("souschef.ui.pages.cookbook_analysis.st"),
    ):
        result = _get_git_path()
        assert result == "git"


def test_get_git_path_not_found():
    """Test git executable not found error."""
    from souschef.ui.pages.cookbook_analysis import _get_git_path

    mock_fail = MagicMock(side_effect=subprocess.CalledProcessError(1, "cmd"))

    with (
        patch("pathlib.Path.exists", return_value=False),
        patch("subprocess.run", side_effect=[mock_fail, mock_fail]),
        patch("souschef.ui.pages.cookbook_analysis.st"),
        pytest.raises(FileNotFoundError, match="git executable not found"),
    ):
        _get_git_path()


def test_extract_archive_size_limit():
    """Test archive size validation."""
    from souschef.ui.pages.cookbook_analysis import extract_archive

    mock_file = MagicMock()
    mock_file.name = "large_archive.tar.gz"
    mock_file.getbuffer.return_value = bytearray(500 * 1024 * 1024)  # 500 MB

    with pytest.raises(ValueError, match="Archive too large"):
        extract_archive(mock_file)


def test_extract_archive_success():
    """Test successful archive extraction."""
    from souschef.ui.pages.cookbook_analysis import extract_archive

    mock_file = MagicMock()
    mock_file.name = "cookbook.tar.gz"
    mock_file.getbuffer.return_value = b"fake tar data"

    with (
        patch("tempfile.mkdtemp", return_value="/tmp/test"),
        patch("pathlib.Path.chmod"),
        patch("pathlib.Path.open"),
        patch("pathlib.Path.mkdir"),
        patch("souschef.ui.pages.cookbook_analysis._extract_archive_by_type"),
        patch(
            "souschef.ui.pages.cookbook_analysis._determine_cookbook_root",
            return_value=Path("/tmp/test/cookbooks"),
        ),
    ):
        temp_dir, cookbook_root, archive_path = extract_archive(mock_file)

        assert temp_dir == Path("/tmp/test")
        assert cookbook_root == Path("/tmp/test/cookbooks")
        assert archive_path.name == "cookbook.tar.gz"


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_collect_deployment_config(mock_st):
    """Test collecting deployment configuration."""
    from souschef.ui.pages.cookbook_analysis import _collect_deployment_config

    mock_st.columns.return_value = [_ctx(), _ctx(), _ctx()]
    mock_st.selectbox.return_value = "awx"
    mock_st.text_input.return_value = "23.0.0"
    mock_st.radio.return_value = "simulation"

    with (
        patch("souschef.ui.pages.cookbook_analysis._show_deployment_information"),
        patch(
            "souschef.ui.pages.cookbook_analysis._get_connection_config",
            return_value={},
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._collect_conversion_options",
            return_value={},
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._collect_advanced_options",
            return_value={},
        ),
    ):
        config = _collect_deployment_config()

        assert config["target_platform"] == "awx"
        assert config["target_version"] == "23.0.0"
        assert config["deployment_mode"] == "simulation"
        assert "connection" in config
        assert "conversion" in config
        assert "advanced" in config


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_all_cookbooks_holistically_success(mock_st):
    """Test holistic conversion success."""
    from souschef.ui.pages.cookbook_analysis import _convert_all_cookbooks_holistically

    mock_st.session_state = SessionState({"holistic_assessment": {"cookbooks": []}})
    # Make rerun raise to prevent infinite loop
    mock_st.rerun = Mock(side_effect=RuntimeError("st.rerun"))
    progress = _ctx()
    status = _ctx()

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._setup_analysis_progress",
            return_value=(progress, status),
        ),
        patch("tempfile.mkdtemp", return_value="/tmp/holistic"),
        patch("pathlib.Path.chmod"),
        patch(
            "souschef.server.convert_all_cookbooks_comprehensive",
            return_value="Success: converted",
        ),
        patch("souschef.ui.pages.cookbook_analysis._save_conversion_to_storage"),
        patch(
            "souschef.ui.pages.cookbook_analysis._display_holistic_conversion_results"
        ),
    ):
        try:
            _convert_all_cookbooks_holistically("/path/to/cookbooks")
        except RuntimeError as e:
            if "st.rerun" in str(e):
                pass  # Expected - st.rerun() was called which is correct behavior
            else:
                raise

    # After successful conversion, st.success should have been called
    assert mock_st.success.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_all_cookbooks_holistically_error(mock_st):
    """Test holistic conversion error handling."""
    from souschef.ui.pages.cookbook_analysis import _convert_all_cookbooks_holistically

    mock_st.session_state = SessionState({})
    progress = _ctx()
    status = _ctx()

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._setup_analysis_progress",
            return_value=(progress, status),
        ),
        patch("tempfile.mkdtemp", return_value="/tmp/holistic"),
        patch("pathlib.Path.chmod"),
        patch(
            "souschef.server.convert_all_cookbooks_comprehensive",
            return_value="Error: failed",
        ),
    ):
        _convert_all_cookbooks_holistically("/path/to/cookbooks")

        assert mock_st.error.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_all_cookbooks_holistically_exception(mock_st):
    """Test holistic conversion exception handling."""
    from souschef.ui.pages.cookbook_analysis import _convert_all_cookbooks_holistically

    mock_st.session_state = SessionState({})
    progress = _ctx()
    status = _ctx()

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._setup_analysis_progress",
            return_value=(progress, status),
        ),
        patch("tempfile.mkdtemp", side_effect=Exception("Temp dir creation failed")),
    ):
        _convert_all_cookbooks_holistically("/path/to/cookbooks")

        assert mock_st.error.called


def test_upload_cookbook_archive_success():
    """Test successful cookbook archive upload."""
    from souschef.ui.pages.cookbook_analysis import _upload_cookbook_archive

    mock_storage_manager = MagicMock()
    mock_storage_manager.get_analysis_by_fingerprint.return_value = None
    mock_blob_storage = MagicMock()

    with (
        patch(
            "souschef.storage.database.calculate_file_fingerprint",
            return_value="abc123",
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.get_storage_manager",
            return_value=mock_storage_manager,
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.get_blob_storage",
            return_value=mock_blob_storage,
        ),
    ):
        result = _upload_cookbook_archive(Path("/tmp/cookbook.tar.gz"), "nginx")

        assert result == "cookbooks/nginx/cookbook.tar.gz"
        assert mock_blob_storage.upload.called


def test_upload_cookbook_archive_deduplicated():
    """Test deduplicated cookbook archive upload."""
    from souschef.ui.pages.cookbook_analysis import _upload_cookbook_archive

    mock_existing = MagicMock()
    mock_existing.cookbook_blob_key = "existing/key"
    mock_storage_manager = MagicMock()
    mock_storage_manager.get_analysis_by_fingerprint.return_value = mock_existing

    with (
        patch(
            "souschef.storage.database.calculate_file_fingerprint",
            return_value="abc123",
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.get_storage_manager",
            return_value=mock_storage_manager,
        ),
    ):
        result = _upload_cookbook_archive(Path("/tmp/cookbook.tar.gz"), "nginx")

        assert result == "existing/key"


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_upload_cookbook_archive_error(mock_st):
    """Test cookbook archive upload error handling."""
    from souschef.ui.pages.cookbook_analysis import _upload_cookbook_archive

    with patch(
        "souschef.storage.database.calculate_file_fingerprint",
        side_effect=Exception("Upload failed"),
    ):
        result = _upload_cookbook_archive(Path("/tmp/cookbook.tar.gz"), "nginx")

        assert result is None
        assert mock_st.warning.called


def test_extract_archive_by_type_zip():
    """Test ZIP archive extraction."""
    from souschef.ui.pages.cookbook_analysis import _extract_archive_by_type

    with patch("souschef.ui.pages.cookbook_analysis._extract_zip_securely"):
        _extract_archive_by_type(
            Path("/tmp/test.zip"), Path("/tmp/extract"), "test.zip"
        )


def test_extract_archive_by_type_tar_gz():
    """Test TAR.GZ archive extraction."""
    from souschef.ui.pages.cookbook_analysis import _extract_archive_by_type

    with patch("souschef.ui.pages.cookbook_analysis._extract_tar_securely"):
        _extract_archive_by_type(
            Path("/tmp/test.tar.gz"), Path("/tmp/extract"), "test.tar.gz"
        )


def test_extract_archive_by_type_tar():
    """Test TAR archive extraction."""
    from souschef.ui.pages.cookbook_analysis import _extract_archive_by_type

    with patch("souschef.ui.pages.cookbook_analysis._extract_tar_securely"):
        _extract_archive_by_type(
            Path("/tmp/test.tar"), Path("/tmp/extract"), "test.tar"
        )


def test_extract_archive_by_type_unsupported():
    """Test unsupported archive format."""
    from souschef.ui.pages.cookbook_analysis import _extract_archive_by_type

    with pytest.raises(ValueError, match="Unsupported archive format"):
        _extract_archive_by_type(
            Path("/tmp/test.rar"), Path("/tmp/extract"), "test.rar"
        )


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_list_and_display_cookbooks_success(mock_st):
    """Test successful cookbook listing."""
    from souschef.ui.pages.cookbook_analysis import _list_and_display_cookbooks

    mock_dir1 = MagicMock()
    mock_dir1.is_dir.return_value = True
    mock_dir1.name = "nginx"

    mock_path = MagicMock()
    mock_path.iterdir.return_value = [mock_dir1]

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._collect_cookbook_data",
            return_value=[{"Name": "nginx"}],
        ),
        patch("souschef.ui.pages.cookbook_analysis._display_cookbook_table"),
        patch("souschef.ui.pages.cookbook_analysis._handle_cookbook_selection"),
    ):
        _list_and_display_cookbooks(mock_path)

        assert mock_st.subheader.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_list_and_display_cookbooks_empty(mock_st):
    """Test listing with no cookbooks."""
    from souschef.ui.pages.cookbook_analysis import _list_and_display_cookbooks

    mock_path = MagicMock()
    mock_path.iterdir.return_value = []

    _list_and_display_cookbooks(mock_path)

    assert mock_st.warning.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_list_and_display_cookbooks_error(mock_st):
    """Test cookbook listing error handling."""
    from souschef.ui.pages.cookbook_analysis import _list_and_display_cookbooks

    mock_path = MagicMock()
    mock_path.iterdir.side_effect = Exception("Directory read failed")

    _list_and_display_cookbooks(mock_path)

    assert mock_st.error.called


def test_build_cookbook_result_success_effort_days_branch():
    """Cover success branch where effort days are converted to hours."""
    from souschef.ui.pages.cookbook_analysis import _build_cookbook_result

    cb_data = {
        "Name": "nginx",
        "Path": "/tmp/nginx",
        "Version": "1.0.0",
        "Maintainer": "team",
        "Description": "desc",
        "Dependencies": 2,
    }
    assessment = {
        "estimated_hours": 0,
        "estimated_effort_days": 3,
        "complexity": "Medium",
        "activity_breakdown": [],
        "recommendations": "ok",
    }

    result = _build_cookbook_result(cb_data, assessment, "Analysed")
    assert result["estimated_hours"] == 24
    assert result["estimated_hours_with_souschef"] == 12
    assert result["status"] == "Analysed"


def test_build_cookbook_result_error_branch():
    """Cover error branch when assessment contains error."""
    from souschef.ui.pages.cookbook_analysis import _build_cookbook_result

    cb_data = {
        "Name": "nginx",
        "Path": "/tmp/nginx",
        "Version": "1.0.0",
        "Maintainer": "team",
        "Description": "desc",
        "Dependencies": 2,
    }
    assessment = {"error": "boom"}

    result = _build_cookbook_result(cb_data, assessment, "Failed")
    assert result["status"] == "Failed"
    assert result["complexity"] == "Error"
    assert result["recommendations"] == "Analysis failed: boom"


def test_build_recommendations_challenges_and_fallbacks():
    """Cover challenge and fallback recommendation formatting."""
    from souschef.ui.pages.cookbook_analysis import _build_recommendations

    with_challenges = _build_recommendations(
        {"challenges": ["A", "B"], "complexity_score": 80}, "top"
    )
    assert "• A" in with_challenges and "• B" in with_challenges

    with_top = _build_recommendations({}, "Top recommendation")
    assert with_top == "Top recommendation"

    fallback = _build_recommendations({"complexity_score": 55}, "")
    assert fallback == "Complexity: 55/100"


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_results_table(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_results_table

    with patch("souschef.ui.pages.cookbook_analysis.pd.DataFrame") as df:
        _display_results_table([{"name": "nginx"}])
    df.assert_called_once()
    mock_st.dataframe.assert_called_once()


def test_validate_cookbook_structure_missing_directory_branch(tmp_path):
    from souschef.ui.pages.cookbook_analysis import _validate_cookbook_structure

    missing = tmp_path / "not-there"
    result = _validate_cookbook_structure(missing)
    assert result["Cookbook directory exists"] is False


def test_validate_cookbook_structure_no_recipes_branch(tmp_path):
    from souschef.ui.pages.cookbook_analysis import _validate_cookbook_structure

    cb = tmp_path / "cookbook"
    cb.mkdir()
    (cb / "metadata.rb").write_text("name 'x'\n")

    result = _validate_cookbook_structure(cb)
    assert result["metadata.rb exists"] is True
    assert result["recipes/ directory exists"] is False
    assert result["Has recipe files"] is False


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_single_cookbook_details_high_and_low(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _display_single_cookbook_details

    mock_st.expander.return_value = _ctx()
    mock_st.columns.return_value = [_ctx(), _ctx(), _ctx()]

    _display_single_cookbook_details(
        {
            "name": "nginx",
            "path": str(tmp_path),
            "version": "1",
            "maintainer": "m",
            "dependencies": 1,
            "complexity": "High",
            "estimated_hours": 10.0,
            "estimated_hours_with_souschef": 5.0,
            "recommendations": "rec",
            "activity_breakdown": [],
        }
    )

    _display_single_cookbook_details(
        {
            "name": "apache",
            "path": str(tmp_path),
            "version": "1",
            "maintainer": "m",
            "dependencies": 0,
            "complexity": "Low",
            "estimated_hours": 8.0,
            "estimated_hours_with_souschef": 4.0,
            "recommendations": "",
            "activity_breakdown": [],
        }
    )

    assert mock_st.metric.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_recipes_error_and_exception_branches(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _convert_recipes

    recipe_file = tmp_path / "default.rb"
    recipe_file.write_text("package 'nginx'")

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis.load_ai_settings",
            return_value={"provider": "Local Model"},
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.generate_playbook_from_recipe",
            return_value="Error: bad recipe",
        ),
    ):
        out1 = _convert_recipes("nginx", [recipe_file], None)

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis.load_ai_settings",
            return_value={"provider": "Local Model"},
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.generate_playbook_from_recipe",
            side_effect=RuntimeError("boom"),
        ),
    ):
        out2 = _convert_recipes("nginx", [recipe_file], None)

    assert out1 == []
    assert out2 == []
    assert mock_st.warning.called


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_handle_playbook_download_back_button_branch(mock_st):
    from souschef.ui.pages.cookbook_analysis import _handle_playbook_download

    mock_st.session_state = SessionState(
        {
            "conversion_results": {"x": 1},
            "generated_playbook_repo": {"temp_path": "/tmp/repo"},
        }
    )
    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.return_value = True

    with (
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

    assert mock_st.session_state.conversion_results is None
    assert mock_st.session_state.generated_playbook_repo is None
    mock_st.rerun.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_generated_repo_section_internal_clear_button(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import (
        _display_generated_repo_section_internal,
    )

    repo_result = {
        "temp_path": str(tmp_path),
        "repo_type": "playbooks_and_roles",
        "files_created": ["ansible.cfg"],
    }
    mock_st.expander.return_value = _ctx()
    mock_st.button.return_value = True
    mock_st.session_state = SessionState({"generated_playbook_repo": repo_result})

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._create_repository_zip",
            return_value=b"zip",
        ),
        patch("souschef.ui.pages.cookbook_analysis.shutil.rmtree"),
    ):
        _display_generated_repo_section_internal(repo_result)

    assert "generated_playbook_repo" not in mock_st.session_state
    mock_st.rerun.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_download_button_create_repo_without_playbooks(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_download_button

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.return_value = True
    mock_st.spinner.return_value = _ctx()
    mock_st.session_state = SessionState()

    with patch(
        "souschef.ui.pages.cookbook_analysis._handle_repo_creation"
    ) as handle_repo:
        _display_download_button(1, 0, b"zip", playbooks=None)

    handle_repo.assert_not_called()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_find_recipe_file_missing_recipes_dir_branch(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _find_recipe_file

    result = _find_recipe_file(tmp_path, "nginx")
    assert result is None
    mock_st.warning.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_find_recipe_file_empty_recipes_branch(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _find_recipe_file

    recipes = tmp_path / "recipes"
    recipes.mkdir()

    result = _find_recipe_file(tmp_path, "nginx")
    assert result is None
    mock_st.warning.assert_called_once()


def test_find_recipe_file_prefers_default_rb(tmp_path):
    from souschef.ui.pages.cookbook_analysis import _find_recipe_file

    recipes = tmp_path / "recipes"
    recipes.mkdir()
    (recipes / "install.rb").write_text("package 'x'\n")
    (recipes / "default.rb").write_text("package 'y'\n")

    result = _find_recipe_file(tmp_path, "nginx")
    assert result is not None
    assert result.name == "default.rb"


def test_find_recipe_file_falls_back_first_recipe(tmp_path):
    from souschef.ui.pages.cookbook_analysis import _find_recipe_file

    recipes = tmp_path / "recipes"
    recipes.mkdir()
    (recipes / "install.rb").write_text("package 'x'\n")

    result = _find_recipe_file(tmp_path, "nginx")
    assert result is not None
    assert result.name == "install.rb"


def test_determine_cookbook_root_multiple_cookbook_dirs(tmp_path):
    from souschef.ui.pages.cookbook_analysis import _determine_cookbook_root

    for d in ["recipes", "attributes", "templates"]:
        (tmp_path / d).mkdir()

    with patch(
        "souschef.ui.pages.cookbook_analysis._handle_multiple_cookbook_dirs",
        return_value=tmp_path / "cookbook",
    ) as hm:
        root = _determine_cookbook_root(tmp_path)
    hm.assert_called_once()
    assert root == tmp_path / "cookbook"


def test_determine_cookbook_root_single_subdir(tmp_path):
    from souschef.ui.pages.cookbook_analysis import _determine_cookbook_root

    single = tmp_path / "bundle"
    single.mkdir()

    with patch(
        "souschef.ui.pages.cookbook_analysis._handle_single_cookbook_dir",
        return_value=single,
    ) as hs:
        root = _determine_cookbook_root(tmp_path)
    hs.assert_called_once()
    assert root == single


def test_process_cookbook_assessments_no_key():
    from souschef.ui.pages.cookbook_analysis import _process_cookbook_assessments

    result = _process_cookbook_assessments({}, [])
    assert result == []


def test_process_cookbook_assessments_with_items():
    from souschef.ui.pages.cookbook_analysis import _process_cookbook_assessments

    assessment = {
        "cookbook_assessments": [{"cookbook_name": "nginx"}],
        "recommendations": "top",
    }
    with patch(
        "souschef.ui.pages.cookbook_analysis._build_assessment_result",
        return_value={"name": "nginx"},
    ) as build:
        result = _process_cookbook_assessments(
            assessment, [{"Name": "nginx", "Path": "/tmp/nginx"}]
        )
    build.assert_called_once()
    assert result == [{"name": "nginx"}]


def test_build_assessment_result_without_cookbook_info():
    from souschef.ui.pages.cookbook_analysis import _build_assessment_result

    cookbook_assessment = {
        "cookbook_path": "/tmp/unknown",
        "cookbook_name": "unknown",
        "complexity": "Low",
        "estimated_effort_days": 1,
        "depends": [],
    }

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._find_cookbook_info", return_value=None
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._build_recommendations",
            return_value="rec",
        ),
    ):
        result = _build_assessment_result(cookbook_assessment, [], "top")

    assert result["name"] == "unknown"
    assert result["path"] == "/tmp/unknown"


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_single_cookbook_no_recipe_files_branch(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _convert_single_cookbook

    recipes = tmp_path / "recipes"
    recipes.mkdir()

    playbooks, templates = _convert_single_cookbook(
        {"name": "nginx", "path": str(tmp_path)}
    )
    assert playbooks == []
    assert templates == []
    mock_st.warning.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_single_cookbook_success_branch(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _convert_single_cookbook

    recipes = tmp_path / "recipes"
    recipes.mkdir()
    (recipes / "default.rb").write_text("package 'nginx'\n")

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._convert_recipes",
            return_value=[{"x": 1}],
        ) as cr,
        patch(
            "souschef.ui.pages.cookbook_analysis._convert_templates",
            return_value=[{"y": 2}],
        ) as ct,
    ):
        playbooks, templates = _convert_single_cookbook(
            {"name": "nginx", "path": str(tmp_path)}, {"p": 1}
        )

    cr.assert_called_once()
    ct.assert_called_once()
    assert playbooks == [{"x": 1}]
    assert templates == [{"y": 2}]


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_convert_templates_failure_warning_branch(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _convert_templates

    with patch(
        "souschef.ui.pages.cookbook_analysis._convert_templates_impl",
        return_value={"success": False, "error": "oops"},
    ):
        result = _convert_templates("nginx", tmp_path)

    assert result == []
    mock_st.warning.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_analyze_rule_based_error_branch(mock_st):
    from souschef.ui.pages.cookbook_analysis import _analyze_rule_based

    cookbook_data = [{"Path": "/tmp/a"}]
    with patch(
        "souschef.assessment.parse_chef_migration_assessment",
        return_value={"error": "bad"},
    ):
        results, assessment = _analyze_rule_based(cookbook_data)

    assert results == []
    assert assessment == {}
    mock_st.error.assert_called_once()


def test_analyze_rule_based_success_branch():
    from souschef.ui.pages.cookbook_analysis import _analyze_rule_based

    cookbook_data = [{"Path": "/tmp/a"}]
    with (
        patch(
            "souschef.assessment.parse_chef_migration_assessment",
            return_value={"cookbook_assessments": [{}]},
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis._process_cookbook_assessments",
            return_value=[{"name": "x"}],
        ) as proc,
        patch("souschef.ui.pages.cookbook_analysis._save_analysis_to_db") as save,
    ):
        results, assessment = _analyze_rule_based(cookbook_data)

    proc.assert_called_once()
    save.assert_called_once()
    assert results == [{"name": "x"}]
    assert "cookbook_assessments" in assessment


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_get_git_path_logs_which_failure(mock_st):
    from souschef.ui.pages.cookbook_analysis import _get_git_path

    which_exc = subprocess.CalledProcessError(1, "which")
    ok = MagicMock()
    ok.returncode = 0

    with (
        patch("pathlib.Path.exists", return_value=False),
        patch("subprocess.run", side_effect=[which_exc, ok]),
    ):
        out = _get_git_path()

    assert out == "git"
    mock_st.write.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_get_git_path_logs_git_version_failure_and_raises(mock_st):
    from souschef.ui.pages.cookbook_analysis import _get_git_path

    which_exc = subprocess.CalledProcessError(1, "which")
    ver_exc = subprocess.CalledProcessError(1, "git --version")

    with (
        patch("pathlib.Path.exists", return_value=False),
        patch("subprocess.run", side_effect=[which_exc, ver_exc]),
        pytest.raises(FileNotFoundError),
    ):
        _get_git_path()

    # Called once for which failure and once for git --version failure
    assert mock_st.write.call_count == 2


def test_copy_roles_to_repository_branches(tmp_path):
    from souschef.ui.pages.cookbook_analysis import _copy_roles_to_repository

    output = tmp_path / "roles_output"
    repo_roles = tmp_path / "repo_roles"
    repo_roles.mkdir()

    # Missing output path branch
    _copy_roles_to_repository(str(output), repo_roles)

    # Existing path with file + dir branch
    output.mkdir()
    (output / "not_a_dir.txt").write_text("x")
    role_dir = output / "nginx"
    role_dir.mkdir()
    (role_dir / "tasks.yml").write_text("- name: x")

    dest_dir = repo_roles / "nginx"
    dest_dir.mkdir()
    (dest_dir / "old.txt").write_text("old")

    _copy_roles_to_repository(str(output), repo_roles)

    assert (repo_roles / "nginx" / "tasks.yml").exists()


def test_determine_num_recipes_branches(tmp_path):
    from souschef.ui.pages.cookbook_analysis import _determine_num_recipes

    # Empty cookbook path branch
    assert _determine_num_recipes("", 3) == 3

    # recipes dir missing -> default 1
    missing = tmp_path / "missing"
    assert _determine_num_recipes(str(missing), 2) == 1

    # recipes dir exists -> count recipes
    cb = tmp_path / "cb"
    recipes = cb / "recipes"
    recipes.mkdir(parents=True)
    (recipes / "a.rb").write_text("x")
    (recipes / "b.rb").write_text("y")
    assert _determine_num_recipes(str(cb), 2) == 2


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_upload_repository_to_storage_jsondecode_branch(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _upload_repository_to_storage

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()

    mock_st.session_state = SessionState({"last_conversion_id": 10})

    conv = MagicMock()
    conv.id = 10
    conv.conversion_data = "{bad-json"

    storage = MagicMock()
    storage.get_conversion_history.return_value = [conv]
    blob = MagicMock()
    blob.upload.return_value = "blob-repo"

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis.get_storage_manager",
            return_value=storage,
        ),
        patch(
            "souschef.ui.pages.cookbook_analysis.get_blob_storage", return_value=blob
        ),
    ):
        _upload_repository_to_storage({"temp_path": str(repo_dir)}, roles_dir)

    assert mock_st.session_state.repo_blob_key == "blob-repo"
    mock_st.warning.assert_called()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_create_repo_callback_failure_and_exception(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _create_repo_callback

    out = tmp_path / "out"
    out.mkdir()

    # failure branch from repository creator
    with patch(
        "souschef.ui.pages.cookbook_analysis._create_ansible_repository",
        return_value={"success": False, "error": "nope"},
    ):
        _create_repo_callback(out)
    assert mock_st.session_state.repo_created_successfully is False

    # exception branch
    with patch(
        "souschef.ui.pages.cookbook_analysis._create_ansible_repository",
        side_effect=RuntimeError("boom"),
    ):
        _create_repo_callback(out)
    assert "Exception:" in mock_st.session_state.repo_creation_error


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_role_download_buttons_error_message_branch(mock_st, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _display_role_download_buttons

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.session_state = SessionState({"repo_creation_error": "failed"})

    with patch(
        "souschef.ui.pages.cookbook_analysis._create_roles_zip_archive",
        return_value=b"zip",
    ):
        _display_role_download_buttons(tmp_path)

    mock_st.error.assert_called_once()


def test_add_effort_estimate_invalid_metrics_branch():
    from souschef.ui.pages.cookbook_analysis import _add_effort_estimate

    recs: list[str] = []
    with patch(
        "souschef.ui.pages.cookbook_analysis.validate_metrics_consistency",
        return_value=(False, "bad"),
    ):
        _add_effort_estimate(recs, {"estimated_effort_days": 4, "complexity": "High"})

    assert recs == ["Estimated Effort: 4 days"]


def test_cleanup_progress_indicators():
    from souschef.ui.pages.cookbook_analysis import _cleanup_progress_indicators

    bar = MagicMock()
    status = MagicMock()
    _cleanup_progress_indicators(bar, status)
    bar.empty.assert_called_once()
    status.empty.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.st")
def test_display_cookbook_activity_breakdown_empty_branch(mock_st):
    from souschef.ui.pages.cookbook_analysis import _display_cookbook_activity_breakdown

    _display_cookbook_activity_breakdown([])
    mock_st.subheader.assert_called_once()


@patch("souschef.ui.pages.cookbook_analysis.load_ai_settings")
@patch("souschef.ui.pages.cookbook_analysis._validate_cookbook_structure")
def test_get_error_context_api_key_flip_branch(mock_validate, mock_load_ai, tmp_path):
    from souschef.ui.pages.cookbook_analysis import _get_error_context

    class FlakyConfig:
        def __init__(self):
            self.calls = 0

        def get(self, key, default=None):
            if key == "provider":
                return "anthropic"
            if key == "api_key":
                self.calls += 1
                return "k" if self.calls == 1 else ""
            return default

    mock_validate.return_value = {"recipes": True}
    mock_load_ai.return_value = FlakyConfig()

    ctx = _get_error_context(tmp_path)
    assert "AI configured but no API key provided" in ctx
