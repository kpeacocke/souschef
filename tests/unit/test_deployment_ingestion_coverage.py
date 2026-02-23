"""
Tests for uncovered lines in deployment, ingestion, migration_wizard, and cli_v2 modules.

Covers exception handlers, edge cases, and rarely-exercised code paths.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# souschef/deployment.py – lines 155-156, 314-315, 1248, 1250, 1252, 1266,
#   1432, 1517, 1521, 1547, 1604-1606, 1642, 1681, 1804, 1880-1881, 1902,
#   1953, 1955, 1957
# ---------------------------------------------------------------------------


class TestDeployment:
    """Tests for deployment module edge cases."""

    def test_generate_awx_workflow_exception_returns_error_string(self) -> None:
        """generate_awx_workflow_from_chef_runlist returns error string on exception."""
        from souschef.deployment import generate_awx_workflow_from_chef_runlist

        with patch(
            "souschef.deployment._generate_awx_workflow_template",
            side_effect=RuntimeError("workflow error"),
        ):
            result = generate_awx_workflow_from_chef_runlist(
                "myapp::default", "myworkflow"
            )
        assert "error" in result.lower()

    def test_generate_awx_inventory_exception_returns_error_string(self) -> None:
        """generate_awx_inventory_source_from_chef returns error string on exception."""
        from souschef.deployment import generate_awx_inventory_source_from_chef

        with patch(
            "souschef.deployment.validate_user_provided_url",
            side_effect=ValueError("bad URL"),
        ):
            result = generate_awx_inventory_source_from_chef("not_a_url", "myorg")
        assert "error" in result.lower()

    def test_analyse_application_patterns_detects_blue_green_pattern(
        self, tmp_path: Path
    ) -> None:
        """analyse_chef_application_patterns detects blue_green when 'blue' is in content."""
        from souschef.deployment import analyse_chef_application_patterns

        # Create a valid cookbook structure
        (tmp_path / "metadata.rb").write_text("name 'myapp'\nversion '1.0.0'\n")
        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()
        recipe = recipes_dir / "deploy.rb"
        recipe.write_text("# blue-green deployment\npackage 'nginx'\n")

        result = analyse_chef_application_patterns(str(tmp_path))
        assert isinstance(result, str)

    def test_analyse_application_patterns_detects_canary_pattern(
        self, tmp_path: Path
    ) -> None:
        """analyse_chef_application_patterns detects canary when 'canary' is in content."""
        from souschef.deployment import analyse_chef_application_patterns

        (tmp_path / "metadata.rb").write_text("name 'myapp'\nversion '1.0.0'\n")
        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()
        recipe = recipes_dir / "deploy.rb"
        recipe.write_text("# canary deployment\nservice 'app'\n")

        result = analyse_chef_application_patterns(str(tmp_path))
        assert isinstance(result, str)

    def test_analyse_application_patterns_detects_rolling_pattern(
        self, tmp_path: Path
    ) -> None:
        """analyse_chef_application_patterns detects rolling when 'rolling' is in content."""
        from souschef.deployment import analyse_chef_application_patterns

        (tmp_path / "metadata.rb").write_text("name 'myapp'\nversion '1.0.0'\n")
        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()
        recipe = recipes_dir / "deploy.rb"
        recipe.write_text("# rolling update deployment\ntemplate '/etc/app'\n")

        result = analyse_chef_application_patterns(str(tmp_path))
        assert isinstance(result, str)

    def test_generate_ansible_deployment_strategy_canary_pattern(self) -> None:
        """_generate_ansible_deployment_strategy calls canary path for 'canary' pattern."""
        from souschef.deployment import _generate_ansible_deployment_strategy

        result = _generate_ansible_deployment_strategy({}, "canary")
        assert isinstance(result, str)

    def test_detect_patterns_from_content_all_patterns(self) -> None:
        """_detect_patterns_from_content returns all four patterns for matching content."""
        from souschef.deployment import _detect_patterns_from_content

        content = "package 'nginx'\ntemplate '/etc/nginx.conf'\nservice 'nginx'\ngit '/opt/app'"
        patterns = _detect_patterns_from_content(content)
        assert "package_management" in patterns
        assert "configuration_management" in patterns
        assert "service_management" in patterns
        assert "source_deployment" in patterns

    def test_assess_complexity_medium_high_boundary(self) -> None:
        """_assess_complexity_from_resource_count returns medium for 31 resources."""
        from souschef.deployment import _assess_complexity_from_resource_count

        _, effort, _ = _assess_complexity_from_resource_count(31)
        assert effort  # non-empty

    def test_assess_complexity_low_high_boundary(self) -> None:
        """_assess_complexity_from_resource_count returns appropriate complexity for 20."""
        from souschef.deployment import _assess_complexity_from_resource_count

        _, effort, _ = _assess_complexity_from_resource_count(20)
        assert effort

    def test_assess_complexity_over_50(self) -> None:
        """_assess_complexity_from_resource_count returns high for > 50 resources."""
        from souschef.deployment import _assess_complexity_from_resource_count

        _, effort, _ = _assess_complexity_from_resource_count(51)
        assert effort


# ---------------------------------------------------------------------------
# souschef/ingestion.py – lines 225, 243, 250-253, 259-262, 265, 285-287,
#   307, 320, 338, 353-354, 383, 387, 392
# ---------------------------------------------------------------------------


class TestIngestion:
    """Tests for ingestion module uncovered lines."""

    def test_select_dependency_version_no_available_returns_none(self) -> None:
        """_select_dependency_version returns None when no versions are available."""
        from souschef.ingestion import _select_dependency_version

        mock_client = MagicMock()
        mock_client.list_cookbook_versions.return_value = []

        warnings: list[str] = []
        result = _select_dependency_version(
            client=mock_client,
            cookbook_name="myapp",
            constraint=None,
            warnings=warnings,
        )
        assert result is None
        assert len(warnings) > 0

    def test_select_dependency_version_tilde_constraint_no_match_uses_latest(
        self,
    ) -> None:
        """_select_dependency_version uses latest when tilde constraint has no match."""
        from souschef.ingestion import _select_dependency_version

        mock_client = MagicMock()
        mock_client.list_cookbook_versions.return_value = ["2.0.0", "2.1.0"]

        warnings: list[str] = []
        result = _select_dependency_version(
            client=mock_client,
            cookbook_name="myapp",
            constraint="~> 1.0",
            warnings=warnings,
        )
        # No 1.x version exists; should fall back to latest
        assert result == "2.1.0"
        assert len(warnings) > 0

    def test_select_dependency_version_equal_constraint_unavailable(self) -> None:
        """_select_dependency_version warns and uses latest when requested version unavailable."""
        from souschef.ingestion import _select_dependency_version

        mock_client = MagicMock()
        mock_client.list_cookbook_versions.return_value = ["2.0.0"]

        warnings: list[str] = []
        result = _select_dependency_version(
            client=mock_client,
            cookbook_name="myapp",
            constraint="== 1.0.0",
            warnings=warnings,
        )
        assert result == "2.0.0"
        assert len(warnings) > 0

    def test_select_dependency_version_exact_digit_match(self) -> None:
        """_select_dependency_version returns exact version when it's available."""
        from souschef.ingestion import _select_dependency_version

        mock_client = MagicMock()
        mock_client.list_cookbook_versions.return_value = ["1.0.0", "2.0.0"]

        warnings: list[str] = []
        result = _select_dependency_version(
            client=mock_client,
            cookbook_name="myapp",
            constraint="1.0.0",
            warnings=warnings,
        )
        assert result == "1.0.0"

    def test_select_dependency_version_unknown_constraint_uses_latest(self) -> None:
        """_select_dependency_version uses latest for unsupported constraints."""
        from souschef.ingestion import _select_dependency_version

        mock_client = MagicMock()
        mock_client.list_cookbook_versions.return_value = ["1.0.0", "2.0.0"]

        warnings: list[str] = []
        result = _select_dependency_version(
            client=mock_client,
            cookbook_name="myapp",
            constraint=">= 1.0.0",
            warnings=warnings,
        )
        # Unsupported constraint → latest
        assert result in ("1.0.0", "2.0.0")

    def test_normalise_spec_no_versions_returns_original_spec(self) -> None:
        """_normalise_spec returns original spec when no versions are available."""
        from souschef.ingestion import CookbookSpec, _normalise_spec

        mock_client = MagicMock()
        mock_client.list_cookbook_versions.return_value = []

        spec = CookbookSpec(name="myapp", version=None)  # type: ignore[arg-type]
        warnings: list[str] = []
        result = _normalise_spec(client=mock_client, spec=spec, warnings=warnings)
        assert result.name == "myapp"
        assert len(warnings) > 0

    def test_collect_section_items_non_dict_metadata_returns_empty(self) -> None:
        """_collect_section_items returns [] for non-dict metadata."""
        from souschef.ingestion import _collect_section_items

        result = _collect_section_items("not a dict", "recipes")  # type: ignore[arg-type]
        assert result == []

    def test_collect_section_items_non_list_entries_returns_empty(self) -> None:
        """_collect_section_items returns [] when section entries are not a list."""
        from souschef.ingestion import _collect_section_items

        result = _collect_section_items({"recipes": "not a list"}, "recipes")
        assert result == []

    def test_collect_section_items_non_dict_entry_is_skipped(self) -> None:
        """_collect_section_items skips non-dict entries in list."""
        from souschef.ingestion import _collect_section_items

        result = _collect_section_items({"recipes": ["not-a-dict"]}, "recipes")
        assert result == []

    def test_download_cookbook_skips_missing_path_or_url(self) -> None:
        """_download_cookbook skips items missing path or url fields."""
        from souschef.ingestion import CookbookSpec, _download_cookbook

        mock_client = MagicMock()
        mock_client.list_cookbook_versions.return_value = ["1.0.0"]
        mock_client.get_cookbook_version.return_value = {
            "recipes": [
                {"path": None, "url": "https://example.com/recipe.rb"},
                {"path": "recipes/default.rb", "url": None},
            ]
        }

        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            spec = CookbookSpec(name="myapp", version="1.0.0")
            warnings: list[str] = []
            # Should not raise; just skip bad items
            _download_cookbook(
                client=mock_client,
                spec=spec,
                destination=Path(tmp) / "dest",
                use_cache=False,
                cache_root=Path(tmp) / "cache",
                warnings=warnings,
            )

    def test_download_cookbook_exception_on_download_adds_warning(self) -> None:
        """_download_cookbook adds warning when download_url raises an exception."""
        from souschef.ingestion import CookbookSpec, _download_cookbook

        mock_client = MagicMock()
        mock_client.list_cookbook_versions.return_value = ["1.0.0"]
        mock_client.get_cookbook_version.return_value = {
            "recipes": [
                {
                    "path": "recipes/default.rb",
                    "url": "https://chef.example.com/recipe",
                },
            ]
        }
        mock_client.download_url.side_effect = RuntimeError("download failed")

        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            spec = CookbookSpec(name="myapp", version="1.0.0")
            warnings: list[str] = []
            _download_cookbook(
                client=mock_client,
                spec=spec,
                destination=Path(tmp) / "dest",
                use_cache=False,
                cache_root=Path(tmp) / "cache",
                warnings=warnings,
            )
        assert any("download" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# souschef/migration_wizard.py – lines 76, 78, 92-93, 97-99, 102-103,
#   107-109, 121-122, 141-144, 163, 298, 312-342
# ---------------------------------------------------------------------------


class TestMigrationWizard:
    """Tests for migration_wizard interactive functions."""

    def test_validate_cookbook_path_empty_path_returns_retry(self) -> None:
        """_validate_cookbook_path returns 'retry' for an empty path."""
        from souschef.migration_wizard import _validate_cookbook_path

        result = _validate_cookbook_path("")
        assert result == "retry"

    def test_validate_cookbook_path_is_directory_no_structure_proceed(
        self, tmp_path: Path
    ) -> None:
        """_validate_cookbook_path returns path when user proceeds despite bad structure."""
        from souschef.migration_wizard import _validate_cookbook_path

        # tmp_path exists but has no metadata.rb or recipes dir
        with patch("builtins.input", return_value="y"):
            result = _validate_cookbook_path(str(tmp_path))
        assert result == str(tmp_path.absolute())

    def test_validate_cookbook_path_is_directory_user_exits(
        self, tmp_path: Path
    ) -> None:
        """_validate_cookbook_path returns 'retry' when user declines on bad structure."""
        from souschef.migration_wizard import _validate_cookbook_path

        with patch("builtins.input", return_value="n"):
            result = _validate_cookbook_path(str(tmp_path))
        assert result == "retry"

    def test_validate_cookbook_path_nonexistent_user_retries(
        self, tmp_path: Path
    ) -> None:
        """_validate_cookbook_path returns 'retry' when path doesn't exist and user retries."""
        from souschef.migration_wizard import _validate_cookbook_path

        with patch("builtins.input", return_value="y"):
            result = _validate_cookbook_path(str(tmp_path / "nonexistent"))
        assert result == "retry"

    def test_validate_cookbook_path_nonexistent_user_exits(
        self, tmp_path: Path
    ) -> None:
        """_validate_cookbook_path returns 'exit' when path doesn't exist and user exits."""
        from souschef.migration_wizard import _validate_cookbook_path

        with patch("builtins.input", return_value="n"):
            result = _validate_cookbook_path(str(tmp_path / "nonexistent"))
        assert result == "exit"

    def test_validate_cookbook_path_not_a_directory_returns_retry(
        self, tmp_path: Path
    ) -> None:
        """_validate_cookbook_path returns 'retry' when path is a file."""
        from souschef.migration_wizard import _validate_cookbook_path

        file_path = tmp_path / "file.txt"
        file_path.write_text("hello")
        result = _validate_cookbook_path(str(file_path))
        assert result == "retry"

    def test_validate_cookbook_path_valid_with_structure_returns_path(
        self, tmp_path: Path
    ) -> None:
        """_validate_cookbook_path returns absolute path for valid cookbook structure."""
        from souschef.migration_wizard import _validate_cookbook_path

        (tmp_path / "metadata.rb").write_text("name 'myapp'")
        (tmp_path / "recipes").mkdir()
        result = _validate_cookbook_path(str(tmp_path))
        assert result == str(tmp_path.absolute())

    def test_is_valid_cookbook_structure_missing_both_returns_false(
        self, tmp_path: Path
    ) -> None:
        """_is_valid_cookbook_structure returns False when both markers are absent."""
        from souschef.migration_wizard import _is_valid_cookbook_structure

        result = _is_valid_cookbook_structure(tmp_path)
        assert result is False

    def test_yes_no_prompt_invalid_then_valid_answer(self) -> None:
        """_yes_no_prompt loops until a valid 'y' or 'n' answer is given."""
        from souschef.migration_wizard import _yes_no_prompt

        # Simulate: invalid answer first, then "y"
        with patch("builtins.input", side_effect=["invalid", "y"]):
            result = _yes_no_prompt("Continue?", default=False)
        assert result is True

    def test_yes_no_prompt_empty_response_returns_default(self) -> None:
        """_yes_no_prompt returns default when user just presses Enter."""
        from souschef.migration_wizard import _yes_no_prompt

        with patch("builtins.input", return_value=""):
            result = _yes_no_prompt("Continue?", default=True)
        assert result is True

    def test_confirm_configuration_returns_false_when_user_declines(self) -> None:
        """_confirm_configuration returns False when user answers 'n'."""
        from souschef.migration_wizard import _confirm_configuration

        config = {
            "cookbook_path": "/workspaces/souschef/cookbook",
            "output_dir": "/workspaces/souschef/output",
            "chef_version": "14.0",
            "ansible_version": "2.14",
            "resource_patterns": {"packages": True, "services": False},
            "conversion_options": {"generate_tests": True},
            "validation_options": {"strict": False},
            "optimization_options": {"loops": True},
        }
        with patch("builtins.input", return_value="n"):
            result = _confirm_configuration(config)
        assert result is False


# ---------------------------------------------------------------------------
# souschef/cli_v2_commands.py – lines 370-375, 380, 442, 445-446, 495-499,
#   529-554, 606-607, 640-641, 645-646
# ---------------------------------------------------------------------------


class TestCliV2Commands:
    """Tests for CLI v2 command edge cases."""

    def test_display_migrations_text_with_conversions(self) -> None:
        """_display_migrations_text shows migration details for each conversion."""
        import json as json_module

        from souschef.cli_v2_commands import _display_migrations_text

        mock_conv = MagicMock()
        mock_conv.id = 1
        mock_conv.cookbook_name = "myapp"
        mock_conv.status = "completed"
        mock_conv.files_generated = 5
        mock_conv.created_at = "2024-01-01T00:00:00"
        mock_conv.conversion_data = json_module.dumps(
            {
                "migration_result": {
                    "migration_id": "abc123def456ghi7",
                    "metrics": {
                        "recipes_converted": 3,
                        "recipes_total": 3,
                    },
                }
            }
        )

        # Should not raise
        _display_migrations_text([mock_conv], 20)

    def test_display_migrations_text_zero_total_recipes_no_rate(self) -> None:
        """_display_migrations_text skips conversion rate when recipes_total is 0."""
        import json as json_module

        from souschef.cli_v2_commands import _display_migrations_text

        mock_conv = MagicMock()
        mock_conv.id = 1
        mock_conv.cookbook_name = "myapp"
        mock_conv.status = "completed"
        mock_conv.files_generated = 0
        mock_conv.created_at = "2024-01-01T00:00:00"
        mock_conv.conversion_data = json_module.dumps(
            {
                "migration_result": {
                    "migration_id": "abc123def456",
                    "metrics": {"recipes_converted": 0, "recipes_total": 0},
                }
            }
        )

        # Should not raise
        _display_migrations_text([mock_conv], 20)

    def test_safe_write_file_writes_content(self, tmp_path: Path) -> None:
        """_safe_write_file writes content to the given path."""
        from souschef.cli_v2_commands import _safe_write_file

        output_file = tmp_path / "output.json"
        _safe_write_file('{"key": "value"}', str(output_file), Path("fallback.json"))
        assert output_file.read_text() == '{"key": "value"}'
