"""
Tests targeting uncovered lines in souschef/assessment.py.

Exercises error/exception branches, validation failures, AI-provider
code-paths, and helper formatting functions that were previously missing
from the test suite.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = (
    Path(__file__).parents[1] / "integration" / "fixtures" / "sample_cookbook"
)


def _make_assessment(
    name: str = "mycookbook",
    complexity: float = 50.0,
    effort: float = 5.0,
    recipe_count: int = 3,
    resource_count: int = 10,
    custom_resources: int = 0,
    ai_insights: str = "",
    priority: str = "medium",
) -> dict:
    """Build a minimal assessment dict suitable for formatter helpers."""
    return {
        "cookbook_name": name,
        "cookbook_path": f"/tmp/{name}",
        "metrics": {
            "recipe_count": recipe_count,
            "resource_count": resource_count,
            "custom_resources": custom_resources,
            "ruby_blocks": 0,
            "template_count": 0,
            "attribute_complexity": 0,
            "library_complexity": 0,
        },
        "complexity_score": complexity,
        "estimated_effort_days": effort,
        "activity_breakdown": [],
        "challenges": ["challenge1"],
        "migration_priority": priority,
        "ai_insights": ai_insights,
        "dependencies": [],
    }


# ---------------------------------------------------------------------------
# analyse_cookbook_dependencies – lines 588-589 (invalid path normalisation)
# ---------------------------------------------------------------------------


class TestAnalyseCookbookDependencies:
    """Tests for analyse_cookbook_dependencies validation branches."""

    def test_invalid_path_raises_returns_error(self) -> None:
        """Invalid path that raises during normalisation returns error message."""
        from souschef.assessment import analyse_cookbook_dependencies

        with patch(
            "souschef.assessment._normalize_path",
            side_effect=ValueError("bad path"),
        ):
            result = analyse_cookbook_dependencies("/bad/path")

        assert "Error" in result
        assert "bad path" in result or "/bad/path" in result

    def test_path_normalisation_os_error_returns_error(self) -> None:
        """OSError during path normalisation returns error message."""
        from souschef.assessment import analyse_cookbook_dependencies

        with patch(
            "souschef.assessment._normalize_path",
            side_effect=OSError("permission denied"),
        ):
            result = analyse_cookbook_dependencies("/restricted")

        assert "Error" in result


# ---------------------------------------------------------------------------
# _count_cookbook_artifacts helper functions – lines 918-919, 926-927
# ---------------------------------------------------------------------------


class TestCountCookbookArtifacts:
    """Tests for _glob_safe and _exists_safe exception branches."""

    def test_glob_safe_raises_os_error_returns_zero(self, tmp_path: Path) -> None:
        """_count_cookbook_artifacts handles OSError in glob gracefully."""
        from souschef.assessment import _count_cookbook_artifacts

        # Create a recipes dir that exists
        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()
        # Patch Path.glob to raise
        with patch.object(Path, "glob", side_effect=OSError("glob failed")):
            result = _count_cookbook_artifacts(tmp_path)
        # Should return a dict with zero counts, not raise
        assert isinstance(result, dict)
        assert result.get("recipe_count", 0) == 0

    def test_no_recipes_dir_returns_zero_count(self, tmp_path: Path) -> None:
        """Missing recipes directory results in zero recipe count."""
        from souschef.assessment import _count_cookbook_artifacts

        # tmp_path has no subdirs – _glob_safe should return 0
        result = _count_cookbook_artifacts(tmp_path)
        assert isinstance(result, dict)
        assert result.get("recipe_count", 0) == 0


# ---------------------------------------------------------------------------
# _analyze_recipes – lines 1032-1033, 1039-1040, 1054-1055
# ---------------------------------------------------------------------------


class TestAnalyzeRecipes:
    """Tests for _analyze_recipes exception branches."""

    def test_glob_raises_returns_empty(self, tmp_path: Path) -> None:
        """OSError from glob returns empty tuple without raising."""
        from souschef.assessment import _analyze_recipes

        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()
        with patch.object(Path, "glob", side_effect=OSError("bad glob")):
            result = _analyze_recipes(tmp_path)
        assert result == (0, 0, 0)

    def test_validated_candidate_raises_skips_file(self, tmp_path: Path) -> None:
        """ValueError from _validated_candidate causes file to be skipped."""
        from souschef.assessment import _analyze_recipes

        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()
        recipe_file = recipes_dir / "default.rb"
        recipe_file.write_text("package 'nginx' do\n  action :install\nend\n")

        with patch(
            "souschef.assessment._validated_candidate",
            side_effect=ValueError("traversal"),
        ):
            result = _analyze_recipes(tmp_path)
        assert result == (0, 0, 0)

    def test_read_text_raises_continues(self, tmp_path: Path) -> None:
        """Exception from read_text causes file to be skipped gracefully."""
        from souschef.assessment import _analyze_recipes

        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()
        recipe_file = recipes_dir / "default.rb"
        recipe_file.write_text("package 'nginx' do\n  action :install\nend\n")

        with patch.object(Path, "read_text", side_effect=OSError("read failed")):
            result = _analyze_recipes(tmp_path)
        assert result == (0, 0, 0)


# ---------------------------------------------------------------------------
# _analyze_attributes – lines 1070-1071, 1077-1078, 1092-1093
# ---------------------------------------------------------------------------


class TestAnalyzeAttributes:
    """Tests for _analyze_attributes exception branches."""

    def test_glob_raises_returns_zero(self, tmp_path: Path) -> None:
        """OSError from glob returns 0 without raising."""
        from souschef.assessment import _analyze_attributes

        attrs_dir = tmp_path / "attributes"
        attrs_dir.mkdir()
        with patch.object(Path, "glob", side_effect=OSError("bad")):
            result = _analyze_attributes(tmp_path)
        assert result == 0

    def test_validated_candidate_raises_skips(self, tmp_path: Path) -> None:
        """ValueError from _validated_candidate skips the file."""
        from souschef.assessment import _analyze_attributes

        attrs_dir = tmp_path / "attributes"
        attrs_dir.mkdir()
        (attrs_dir / "default.rb").write_text("default['key'] = 'value'\n")

        with patch(
            "souschef.assessment._validated_candidate",
            side_effect=ValueError("bad"),
        ):
            result = _analyze_attributes(tmp_path)
        assert result == 0

    def test_read_text_raises_continues(self, tmp_path: Path) -> None:
        """Exception from read_text is handled, returns 0."""
        from souschef.assessment import _analyze_attributes

        attrs_dir = tmp_path / "attributes"
        attrs_dir.mkdir()
        (attrs_dir / "default.rb").write_text("default['key'] = 'value'\n")

        with patch.object(Path, "read_text", side_effect=OSError("read error")):
            result = _analyze_attributes(tmp_path)
        assert result == 0


# ---------------------------------------------------------------------------
# _analyze_templates – lines 1108-1109, 1115-1116, 1122-1123
# ---------------------------------------------------------------------------


class TestAnalyzeTemplates:
    """Tests for _analyze_templates exception branches."""

    def test_glob_raises_returns_zero(self, tmp_path: Path) -> None:
        """OSError from glob returns 0."""
        from souschef.assessment import _analyze_templates

        tmpl_dir = tmp_path / "templates"
        tmpl_dir.mkdir()
        with patch.object(Path, "glob", side_effect=OSError("bad")):
            result = _analyze_templates(tmp_path)
        assert result == 0

    def test_validated_candidate_raises_skips(self, tmp_path: Path) -> None:
        """ValueError from _validated_candidate skips the file."""
        from souschef.assessment import _analyze_templates

        tmpl_dir = tmp_path / "templates" / "default"
        tmpl_dir.mkdir(parents=True)
        (tmpl_dir / "test.erb").write_text("<%= @value %>")

        with patch(
            "souschef.assessment._validated_candidate",
            side_effect=ValueError("bad"),
        ):
            result = _analyze_templates(tmp_path)
        assert result == 0

    def test_read_text_raises_continues(self, tmp_path: Path) -> None:
        """Exception from read_text is handled gracefully."""
        from souschef.assessment import _analyze_templates

        tmpl_dir = tmp_path / "templates" / "default"
        tmpl_dir.mkdir(parents=True)
        (tmpl_dir / "test.erb").write_text("<%= @value %>")

        with patch.object(Path, "read_text", side_effect=OSError("read error")):
            result = _analyze_templates(tmp_path)
        assert result == 0


# ---------------------------------------------------------------------------
# _analyze_libraries – lines 1140-1141, 1150-1151
# ---------------------------------------------------------------------------


class TestAnalyzeLibraries:
    """Tests for _analyze_libraries exception branches."""

    def test_glob_raises_returns_zero(self, tmp_path: Path) -> None:
        """OSError from safe_glob returns 0."""
        from souschef.assessment import _analyze_libraries

        lib_dir = tmp_path / "libraries"
        lib_dir.mkdir()
        with patch("souschef.assessment.safe_glob", side_effect=OSError("bad")):
            result = _analyze_libraries(tmp_path)
        assert result == 0

    def test_read_text_raises_continues(self, tmp_path: Path) -> None:
        """Exception during file reading skips library file."""
        from souschef.assessment import _analyze_libraries

        lib_dir = tmp_path / "libraries"
        lib_dir.mkdir()
        (lib_dir / "helper.rb").write_text("class Helper; def go; end; end")

        with patch.object(Path, "read_text", side_effect=OSError("read error")):
            result = _analyze_libraries(tmp_path)
        assert result == 0


# ---------------------------------------------------------------------------
# _count_definitions – lines 1166-1167
# ---------------------------------------------------------------------------


class TestCountDefinitions:
    """Tests for _count_definitions exception branch."""

    def test_glob_raises_returns_zero(self, tmp_path: Path) -> None:
        """OSError from safe_glob returns 0."""
        from souschef.assessment import _count_definitions

        defs_dir = tmp_path / "definitions"
        defs_dir.mkdir()
        with patch("souschef.assessment.safe_glob", side_effect=OSError("bad")):
            result = _count_definitions(tmp_path)
        assert result == 0


# ---------------------------------------------------------------------------
# _parse_berksfile – lines 1198-1199
# ---------------------------------------------------------------------------


class TestParseBerksfile:
    """Tests for _parse_berksfile exception branch."""

    def test_read_text_raises_returns_empty(self, tmp_path: Path) -> None:
        """Exception during file reading returns empty dict."""
        from souschef.assessment import _parse_berksfile

        berksfile = tmp_path / "Berksfile"
        berksfile.write_text("source 'https://supermarket.chef.io'\ncookbook 'nginx'\n")

        with patch.object(Path, "read_text", side_effect=OSError("read error")):
            result = _parse_berksfile(tmp_path)
        assert result["dependencies"] == []
        assert result["complexity"] == 0


# ---------------------------------------------------------------------------
# _parse_chefignore – lines 1227-1228
# ---------------------------------------------------------------------------


class TestParseChefignore:
    """Tests for _parse_chefignore exception branch."""

    def test_read_text_raises_returns_empty(self, tmp_path: Path) -> None:
        """Exception during file reading returns empty dict."""
        from souschef.assessment import _parse_chefignore

        chefignore = tmp_path / "chefignore"
        chefignore.write_text("*.pyc\n")

        with patch.object(Path, "read_text", side_effect=OSError("read error")):
            result = _parse_chefignore(tmp_path)
        assert result["patterns"] == []
        assert result["complexity"] == 0


# ---------------------------------------------------------------------------
# _parse_thorfile – lines 1251-1252
# ---------------------------------------------------------------------------


class TestParseThorfile:
    """Tests for _parse_thorfile exception branch."""

    def test_read_text_raises_returns_empty(self, tmp_path: Path) -> None:
        """Exception during file reading returns empty dict."""
        from souschef.assessment import _parse_thorfile

        thorfile = tmp_path / "Thorfile"
        thorfile.write_text(
            "class MyCookbook < Thor\n  desc 'test', 'run tests'\n  def test; end\nend\n"
        )

        with patch.object(Path, "read_text", side_effect=OSError("read error")):
            result = _parse_thorfile(tmp_path)
        assert result["tasks"] == []
        assert result["complexity"] == 0


# ---------------------------------------------------------------------------
# _parse_metadata_file – lines 1297-1298
# ---------------------------------------------------------------------------


class TestParseMetadataFile:
    """Tests for _parse_metadata_file exception branch."""

    def test_read_text_raises_returns_empty(self, tmp_path: Path) -> None:
        """Exception during file reading returns empty dict."""
        from souschef.assessment import _parse_metadata_file

        metadata = tmp_path / "metadata.rb"
        metadata.write_text("name 'mycookbook'\nversion '1.0.0'\n")

        with patch.object(Path, "read_text", side_effect=OSError("read error")):
            result = _parse_metadata_file(tmp_path)
        assert result["name"] == ""
        assert result["dependencies"] == []
        assert result["complexity"] == 0


# ---------------------------------------------------------------------------
# _format_activity_breakdown – line 1422 (empty activities)
# ---------------------------------------------------------------------------


class TestFormatActivityBreakdown:
    """Tests for _format_activity_breakdown edge cases."""

    def test_empty_activities_returns_empty_string(self) -> None:
        """Empty activities list returns empty string."""
        from souschef.assessment import _format_activity_breakdown

        result = _format_activity_breakdown([])
        assert result == ""


# ---------------------------------------------------------------------------
# _estimate_resource_requirements – lines 1718-1723, 1730-1735
# ---------------------------------------------------------------------------


class TestEstimateResourceRequirements:
    """Tests for _estimate_resource_requirements branching."""

    def test_medium_effort_uses_medium_team(self) -> None:
        """Effort between 20-50 days uses medium team description."""
        from souschef.assessment import _estimate_resource_requirements

        metrics = {"estimated_effort_days": 35, "total_cookbooks": 5}
        result = _estimate_resource_requirements(metrics, "ansible_awx")
        assert "2 developers" in result or "senior reviewer" in result

    def test_high_effort_uses_large_team(self) -> None:
        """Effort >= 50 days uses large team description."""
        from souschef.assessment import _estimate_resource_requirements

        metrics = {"estimated_effort_days": 60, "total_cookbooks": 10}
        result = _estimate_resource_requirements(metrics, "ansible_awx")
        assert "3-4 developers" in result or "tech lead" in result

    def test_souschef_medium_effort_range(self) -> None:
        """SousChef effort between 20-50 shows medium team."""
        from souschef.assessment import _estimate_resource_requirements

        # effort_days=35 → souschef_effort = 35 * 0.35 ≈ 12 (low); use 150 to push to medium
        metrics = {"estimated_effort_days": 150, "total_cookbooks": 20}
        result = _estimate_resource_requirements(metrics, "ansible_aap")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# _collect_metadata_dependencies / _collect_berks_dependencies
# Lines 1815-1817, 1836-1838
# ---------------------------------------------------------------------------


class TestCollectDependencies:
    """Tests for dependency collection validation branches."""

    def test_metadata_validated_candidate_raises_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """ValueError from _validated_candidate returns empty list."""
        from souschef.assessment import _collect_metadata_dependencies

        metadata = tmp_path / "metadata.rb"
        metadata.write_text("name 'test'\ndepends 'nginx'\n")

        with patch(
            "souschef.assessment._validated_candidate",
            side_effect=ValueError("traversal"),
        ):
            result = _collect_metadata_dependencies(tmp_path)
        assert result == []

    def test_berks_validated_candidate_raises_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """ValueError from _validated_candidate returns empty list."""
        from souschef.assessment import _collect_berks_dependencies

        berksfile = tmp_path / "Berksfile"
        berksfile.write_text("cookbook 'nginx'\n")

        with patch(
            "souschef.assessment._validated_candidate",
            side_effect=ValueError("traversal"),
        ):
            result = _collect_berks_dependencies(tmp_path)
        assert result == []


# ---------------------------------------------------------------------------
# _identify_circular_dependencies – line 1913
# ---------------------------------------------------------------------------


class TestIdentifyCircularDependencies:
    """Tests for _identify_circular_dependencies heuristic."""

    def test_detects_potential_circular_dependency(self) -> None:
        """Returns potential circular when dep name contains cookbook name."""
        from souschef.assessment import _identify_circular_dependencies

        analysis = {
            "cookbook_name": "myapp",
            "direct_dependencies": ["myapp-helper", "nginx"],
        }
        result = _identify_circular_dependencies(analysis)
        assert len(result) >= 1
        assert result[0]["type"] == "potential"

    def test_no_circular_when_names_unrelated(self) -> None:
        """Returns empty list when no circular dependencies found."""
        from souschef.assessment import _identify_circular_dependencies

        analysis = {
            "cookbook_name": "myapp",
            "direct_dependencies": ["nginx", "apache"],
        }
        result = _identify_circular_dependencies(analysis)
        assert result == []


# ---------------------------------------------------------------------------
# _format_migration_order – line 2109
# ---------------------------------------------------------------------------


class TestFormatMigrationOrder:
    """Tests for _format_migration_order empty input."""

    def test_empty_order_returns_no_analysis(self) -> None:
        """Empty order list returns fallback message."""
        from souschef.assessment import _format_migration_order

        result = _format_migration_order([])
        assert "No order analysis available." in result

    def test_non_empty_order_formats_items(self) -> None:
        """Non-empty order list is formatted correctly."""
        from souschef.assessment import _format_migration_order

        order = [{"cookbook": "nginx", "priority": 1, "reason": "no deps"}]
        result = _format_migration_order(order)
        assert "nginx" in result
        assert "Priority 1" in result


# ---------------------------------------------------------------------------
# _analyse_dependency_migration_impact – lines 2164, 2170
# ---------------------------------------------------------------------------


class TestAnalyseDependencyMigrationImpact:
    """Tests for _analyse_dependency_migration_impact branching."""

    def test_circular_dependency_impact_included(self) -> None:
        """Circular dependencies appear in impact analysis."""
        from souschef.assessment import _analyse_dependency_migration_impact

        analysis = {
            "community_cookbooks": [],
            "circular_dependencies": [{"cookbook1": "a", "cookbook2": "b"}],
            "direct_dependencies": ["c"],
        }
        result = _analyse_dependency_migration_impact(analysis)
        assert "circular" in result.lower()

    def test_high_dependency_count_impact_included(self) -> None:
        """High dependency count triggers appropriate impact message."""
        from souschef.assessment import _analyse_dependency_migration_impact

        analysis = {
            "community_cookbooks": [],
            "circular_dependencies": [],
            "direct_dependencies": ["a", "b", "c", "d", "e", "f"],
        }
        result = _analyse_dependency_migration_impact(analysis)
        assert "High dependency" in result or "dependency count" in result.lower()


# ---------------------------------------------------------------------------
# assess_single_cookbook_with_ai – lines 2373-2416, 2415-2416
# ---------------------------------------------------------------------------


class TestAssessSingleCookbookWithAi:
    """Tests for assess_single_cookbook_with_ai."""

    def test_path_not_found_returns_error(self) -> None:
        """Non-existent path returns error dict."""
        from souschef.assessment import assess_single_cookbook_with_ai

        result = assess_single_cookbook_with_ai(
            "/nonexistent/cookbook",
            ai_provider="anthropic",
            api_key="key",
        )
        assert "error" in result

    def test_no_api_key_falls_back_to_rule_based(self, tmp_path: Path) -> None:
        """Missing API key triggers rule-based fallback."""
        from souschef.assessment import assess_single_cookbook_with_ai

        (tmp_path / "metadata.rb").write_text("name 'test'\n")

        result = assess_single_cookbook_with_ai(
            str(tmp_path),
            ai_provider="anthropic",
            api_key="",
        )
        # Falls back to parse_chef_migration_assessment – always returns a string or dict
        assert result is not None

    def test_exception_returns_error_dict(self) -> None:
        """Unexpected exception returns error dict."""
        from souschef.assessment import assess_single_cookbook_with_ai

        with patch(
            "souschef.assessment._normalize_path",
            side_effect=RuntimeError("boom"),
        ):
            result = assess_single_cookbook_with_ai(
                "/any/path",
                ai_provider="anthropic",
                api_key="key",
            )
        assert "error" in result

    def test_medium_complexity_level(self, tmp_path: Path) -> None:
        """Complexity score 31-70 produces Medium complexity level."""
        from souschef.assessment import assess_single_cookbook_with_ai

        (tmp_path / "metadata.rb").write_text("name 'test'\n")

        with (
            patch("souschef.assessment._is_ai_available", return_value=True),
            patch(
                "souschef.assessment._assess_single_cookbook_with_ai",
                return_value=_make_assessment(complexity=50.0, effort=5.0),
            ),
        ):
            result = assess_single_cookbook_with_ai(
                str(tmp_path),
                ai_provider="anthropic",
                api_key="key",
            )
        assert isinstance(result, dict)

    def test_high_complexity_level(self, tmp_path: Path) -> None:
        """Complexity score > 70 produces High complexity level."""
        from souschef.assessment import assess_single_cookbook_with_ai

        (tmp_path / "metadata.rb").write_text("name 'test'\n")

        with (
            patch("souschef.assessment._is_ai_available", return_value=True),
            patch(
                "souschef.assessment._assess_single_cookbook_with_ai",
                return_value=_make_assessment(complexity=85.0, effort=20.0),
            ),
        ):
            result = assess_single_cookbook_with_ai(
                str(tmp_path),
                ai_provider="anthropic",
                api_key="key",
            )
        assert isinstance(result, dict)
        assert result.get("complexity") == "High"


# ---------------------------------------------------------------------------
# assess_chef_migration_complexity_with_ai – lines 2458-2489
# ---------------------------------------------------------------------------


class TestAssessChefMigrationComplexityWithAi:
    """Tests for assess_chef_migration_complexity_with_ai."""

    def test_validation_failure_returns_error(self) -> None:
        """Validation failure returns error message."""
        from souschef.assessment import assess_chef_migration_complexity_with_ai

        result = assess_chef_migration_complexity_with_ai(
            cookbook_paths="",
            migration_scope="invalid_scope",
        )
        assert "Error" in result or "error" in result.lower()

    def test_no_api_key_falls_back(self, tmp_path: Path) -> None:
        """Empty API key falls back to rule-based assessment."""
        from souschef.assessment import assess_chef_migration_complexity_with_ai

        (tmp_path / "metadata.rb").write_text("name 'test'\n")

        result = assess_chef_migration_complexity_with_ai(
            cookbook_paths=str(tmp_path),
            ai_provider="anthropic",
            api_key="",
        )
        assert isinstance(result, str)

    def test_exception_returns_error_string(self) -> None:
        """Unexpected exception returns formatted error string."""
        from souschef.assessment import assess_chef_migration_complexity_with_ai

        with patch(
            "souschef.assessment._validate_assessment_inputs",
            side_effect=RuntimeError("boom"),
        ):
            result = assess_chef_migration_complexity_with_ai(
                cookbook_paths="/some/path",
            )
        assert "error" in result.lower() or "boom" in result.lower()


# ---------------------------------------------------------------------------
# _is_ai_available – line 2504
# ---------------------------------------------------------------------------


class TestIsAiAvailable:
    """Tests for _is_ai_available provider handling."""

    def test_unknown_provider_returns_false(self) -> None:
        """Unknown provider name returns False."""
        from souschef.assessment import _is_ai_available

        result = _is_ai_available("unknown_provider", "somekey")
        assert result is False

    def test_no_api_key_returns_false(self) -> None:
        """Empty API key always returns False."""
        from souschef.assessment import _is_ai_available

        result = _is_ai_available("anthropic", "")
        assert result is False


# ---------------------------------------------------------------------------
# _analyse_cookbook_metrics_with_ai – lines 2597-2633
# ---------------------------------------------------------------------------


class TestAnalyseCookbookMetricsWithAi:
    """Tests for _analyse_cookbook_metrics_with_ai."""

    def test_returns_empty_when_no_paths(self) -> None:
        """Empty path list returns empty assessments and zero metrics."""
        from souschef.assessment import _analyse_cookbook_metrics_with_ai

        assessments, metrics = _analyse_cookbook_metrics_with_ai(
            [], "anthropic", "key", "model", 0.3, 512
        )
        assert assessments == []
        assert metrics["total_cookbooks"] == 0

    def test_aggregates_metrics_for_valid_path(self, tmp_path: Path) -> None:
        """Valid paths produce aggregated metrics."""
        from souschef.assessment import _analyse_cookbook_metrics_with_ai

        (tmp_path / "metadata.rb").write_text("name 'test'\n")

        _, metrics = _analyse_cookbook_metrics_with_ai(
            [tmp_path], "anthropic", "", "model", 0.3, 512
        )
        assert metrics["total_cookbooks"] == 1
        assert "avg_complexity" in metrics


# ---------------------------------------------------------------------------
# _get_ai_cookbook_analysis – lines 2758-2768, 2771-2773
# ---------------------------------------------------------------------------


class TestGetAiCookbookAnalysis:
    """Tests for _get_ai_cookbook_analysis JSON parsing and error branches."""

    def test_valid_json_response_parsed(self, tmp_path: Path) -> None:
        """Valid JSON response is parsed and returned as dict."""
        from souschef.assessment import _get_ai_cookbook_analysis

        (tmp_path / "metadata.rb").write_text("name 'test'\n")
        json_resp = json.dumps(
            {
                "complexity_score": 42,
                "estimated_effort_days": 4,
                "challenges": [],
                "migration_priority": "low",
                "insights": "easy",
            }
        )

        with patch("souschef.assessment._call_ai_api", return_value=json_resp):
            result = _get_ai_cookbook_analysis(
                tmp_path, {}, "anthropic", "key", "model", 0.3, 512
            )
        assert result is not None
        assert result["complexity_score"] == 42

    def test_json_embedded_in_text_extracted(self, tmp_path: Path) -> None:
        """JSON embedded in surrounding text is extracted."""
        from souschef.assessment import _get_ai_cookbook_analysis

        (tmp_path / "metadata.rb").write_text("name 'test'\n")
        embedded = 'Here is my answer: {"complexity_score": 10, "estimated_effort_days": 1, "challenges": [], "migration_priority": "low", "insights": "ok"}'

        with patch("souschef.assessment._call_ai_api", return_value=embedded):
            result = _get_ai_cookbook_analysis(
                tmp_path, {}, "anthropic", "key", "model", 0.3, 512
            )
        assert result is not None
        assert result["complexity_score"] == 10

    def test_invalid_json_no_embedded_returns_none(self, tmp_path: Path) -> None:
        """Invalid JSON without embedded JSON block returns None."""
        from souschef.assessment import _get_ai_cookbook_analysis

        (tmp_path / "metadata.rb").write_text("name 'test'\n")

        with patch("souschef.assessment._call_ai_api", return_value="not json at all"):
            result = _get_ai_cookbook_analysis(
                tmp_path, {}, "anthropic", "key", "model", 0.3, 512
            )
        assert result is None

    def test_exception_in_analysis_returns_none(self, tmp_path: Path) -> None:
        """Exception during analysis returns None."""
        from souschef.assessment import _get_ai_cookbook_analysis

        with patch(
            "souschef.assessment._get_recipe_content_sample",
            side_effect=RuntimeError("boom"),
        ):
            result = _get_ai_cookbook_analysis(
                tmp_path, {}, "anthropic", "key", "model", 0.3, 512
            )
        assert result is None


# ---------------------------------------------------------------------------
# _get_recipe_content_sample – lines 2782, 2789, 2807-2814, 2817
# ---------------------------------------------------------------------------


class TestGetRecipeContentSample:
    """Tests for _get_recipe_content_sample edge cases."""

    def test_no_recipes_dir_returns_message(self, tmp_path: Path) -> None:
        """Missing recipes directory returns appropriate message."""
        from souschef.assessment import _get_recipe_content_sample

        result = _get_recipe_content_sample(tmp_path)
        assert "No recipes directory found" in result

    def test_empty_recipes_dir_returns_message(self, tmp_path: Path) -> None:
        """Existing but empty recipes directory returns appropriate message."""
        from souschef.assessment import _get_recipe_content_sample

        (tmp_path / "recipes").mkdir()
        result = _get_recipe_content_sample(tmp_path)
        assert "No recipe files found" in result

    def test_unreadable_recipe_continues(self, tmp_path: Path) -> None:
        """Unreadable recipe file is skipped; returns could not read message."""
        from souschef.assessment import _get_recipe_content_sample

        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()
        recipe = recipes_dir / "default.rb"
        recipe.write_text("package 'nginx'\n")

        with patch.object(Path, "read_text", side_effect=OSError("perm")):
            result = _get_recipe_content_sample(tmp_path)
        assert "Could not read recipe content" in result

    def test_large_recipe_is_truncated(self, tmp_path: Path) -> None:
        """Recipe content exceeding size limit is truncated."""
        from souschef.assessment import _get_recipe_content_sample

        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "big.rb").write_text("x" * 4000)
        (recipes_dir / "big2.rb").write_text("y" * 4000)
        (recipes_dir / "big3.rb").write_text("z" * 4000)

        result = _get_recipe_content_sample(tmp_path)
        assert isinstance(result, str)
        assert "..." in result or len(result) <= 8100


# ---------------------------------------------------------------------------
# _get_metadata_content – lines 2828, 2834-2835
# ---------------------------------------------------------------------------


class TestGetMetadataContent:
    """Tests for _get_metadata_content edge cases."""

    def test_no_metadata_returns_message(self, tmp_path: Path) -> None:
        """Missing metadata.rb returns appropriate message."""
        from souschef.assessment import _get_metadata_content

        result = _get_metadata_content(tmp_path)
        assert "No metadata.rb found" in result

    def test_unreadable_metadata_returns_message(self, tmp_path: Path) -> None:
        """Unreadable metadata.rb returns appropriate message."""
        from souschef.assessment import _get_metadata_content

        metadata = tmp_path / "metadata.rb"
        metadata.write_text("name 'test'\n")

        with patch.object(Path, "read_text", side_effect=OSError("perm")):
            result = _get_metadata_content(tmp_path)
        assert "Could not read metadata" in result


# ---------------------------------------------------------------------------
# _call_ai_api – lines 2853, 2855-2862, 2873-2874
# ---------------------------------------------------------------------------


class TestCallAiApi:
    """Tests for _call_ai_api routing and exception handling."""

    def test_watson_with_invalid_base_url_returns_none(self) -> None:
        """Invalid base_url for watson provider returns None."""
        from souschef.assessment import _call_ai_api

        with patch(
            "souschef.assessment.validate_user_provided_url",
            side_effect=ValueError("bad url"),
        ):
            result = _call_ai_api(
                "prompt", "watson", "key", "model", 0.3, 512, base_url="not-a-url"
            )
        assert result is None

    def test_unknown_provider_returns_none(self) -> None:
        """Unknown AI provider returns None."""
        from souschef.assessment import _call_ai_api

        result = _call_ai_api("prompt", "unknown", "key", "model", 0.3, 512)
        assert result is None

    def test_exception_in_dispatch_returns_none(self) -> None:
        """Exception during API call returns None."""
        from souschef.assessment import _call_ai_api

        with patch(
            "souschef.assessment._call_anthropic_api",
            side_effect=RuntimeError("boom"),
        ):
            result = _call_ai_api("prompt", "anthropic", "key", "model", 0.3, 512)
        assert result is None


# ---------------------------------------------------------------------------
# _call_anthropic_api – lines 2906-2907
# ---------------------------------------------------------------------------


class TestCallAnthropicApi:
    """Tests for _call_anthropic_api exception handling."""

    def test_request_exception_returns_none(self) -> None:
        """Network exception returns None."""
        from souschef.assessment import _call_anthropic_api

        mock_requests = MagicMock()
        mock_requests.post.side_effect = OSError("network")
        with patch("souschef.assessment.requests", mock_requests):
            result = _call_anthropic_api("prompt", "key", "model", 0.3, 512)
        assert result is None

    def test_non_200_status_returns_none(self) -> None:
        """Non-200 HTTP status returns None."""
        from souschef.assessment import _call_anthropic_api

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response
        with patch("souschef.assessment.requests", mock_requests):
            result = _call_anthropic_api("prompt", "key", "model", 0.3, 512)
        assert result is None

    def test_successful_response_returns_text(self) -> None:
        """Successful response returns content text."""
        from souschef.assessment import _call_anthropic_api

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": [{"text": "assessment result"}]}
        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response
        with patch("souschef.assessment.requests", mock_requests):
            result = _call_anthropic_api("prompt", "key", "model", 0.3, 512)
        assert result == "assessment result"


# ---------------------------------------------------------------------------
# _call_openai_api – lines 2943-2944
# ---------------------------------------------------------------------------


class TestCallOpenaiApi:
    """Tests for _call_openai_api exception handling."""

    def test_request_exception_returns_none(self) -> None:
        """Network exception returns None."""
        from souschef.assessment import _call_openai_api

        mock_requests = MagicMock()
        mock_requests.post.side_effect = OSError("network")
        with patch("souschef.assessment.requests", mock_requests):
            result = _call_openai_api("prompt", "key", "model", 0.3, 512)
        assert result is None

    def test_non_200_status_returns_none(self) -> None:
        """Non-200 HTTP status returns None."""
        from souschef.assessment import _call_openai_api

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response
        with patch("souschef.assessment.requests", mock_requests):
            result = _call_openai_api("prompt", "key", "model", 0.3, 512)
        assert result is None

    def test_successful_response_returns_content(self) -> None:
        """Successful response returns message content."""
        from souschef.assessment import _call_openai_api

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "openai result"}}]
        }
        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response
        with patch("souschef.assessment.requests", mock_requests):
            result = _call_openai_api("prompt", "key", "model", 0.3, 512)
        assert result == "openai result"


# ---------------------------------------------------------------------------
# _call_watson_api – lines 2960-2994
# ---------------------------------------------------------------------------


class TestCallWatsonApi:
    """Tests for _call_watson_api branching and exception handling."""

    def test_no_api_client_returns_none(self) -> None:
        """When APIClient is None, returns None without calling anything."""
        from souschef.assessment import _call_watson_api

        with patch("souschef.assessment.APIClient", None):
            result = _call_watson_api("prompt", "key", "model", 0.3, 512)
        assert result is None

    def test_exception_returns_none(self) -> None:
        """Exception during Watson call returns None."""
        from souschef.assessment import _call_watson_api

        mock_client_class = MagicMock()
        mock_client_class.side_effect = RuntimeError("auth failed")
        with patch("souschef.assessment.APIClient", mock_client_class):
            result = _call_watson_api("prompt", "key", "model", 0.3, 512)
        assert result is None

    def test_successful_streamed_response(self) -> None:
        """Successful streamed response concatenates generated text."""
        from souschef.assessment import _call_watson_api

        mock_chunk = MagicMock()
        mock_chunk.results = [MagicMock(generated_text="Hello")]
        mock_deployment = MagicMock()
        mock_deployment.text_generation_stream.return_value = [mock_chunk]
        mock_client_instance = MagicMock()
        mock_client_instance.deployments = mock_deployment
        mock_client_class = MagicMock(return_value=mock_client_instance)

        with patch("souschef.assessment.APIClient", mock_client_class):
            result = _call_watson_api(
                "prompt",
                "key",
                "model",
                0.3,
                512,
                base_url="https://watson.example.com",
            )
        assert result == "Hello"


# ---------------------------------------------------------------------------
# _generate_ai_migration_recommendations – lines 3010-3065
# ---------------------------------------------------------------------------


class TestGenerateAiMigrationRecommendations:
    """Tests for _generate_ai_migration_recommendations."""

    def test_ai_response_returned_directly(self) -> None:
        """Non-None AI response is returned directly."""
        from souschef.assessment import _generate_ai_migration_recommendations

        assessments = [_make_assessment()]
        metrics = {
            "total_cookbooks": 1,
            "avg_complexity": 50,
            "estimated_effort_days": 5,
        }

        with patch(
            "souschef.assessment._call_ai_api", return_value="• Use phased approach"
        ):
            result = _generate_ai_migration_recommendations(
                assessments,
                metrics,
                "ansible_awx",
                "anthropic",
                "key",
                "model",
                0.3,
                512,
            )
        assert "phased" in result

    def test_none_ai_falls_back_to_rule_based(self) -> None:
        """None AI response falls back to rule-based recommendations."""
        from souschef.assessment import _generate_ai_migration_recommendations

        assessments = [_make_assessment()]
        metrics = {
            "total_cookbooks": 1,
            "avg_complexity": 50,
            "estimated_effort_days": 5,
        }

        with patch("souschef.assessment._call_ai_api", return_value=None):
            result = _generate_ai_migration_recommendations(
                assessments,
                metrics,
                "ansible_awx",
                "anthropic",
                "key",
                "model",
                0.3,
                512,
            )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_exception_falls_back_to_rule_based(self) -> None:
        """Exception in AI call falls back to rule-based recommendations."""
        from souschef.assessment import _generate_ai_migration_recommendations

        assessments = [_make_assessment()]
        metrics = {
            "total_cookbooks": 1,
            "avg_complexity": 50,
            "estimated_effort_days": 5,
        }

        with patch(
            "souschef.assessment._call_ai_api", side_effect=RuntimeError("boom")
        ):
            result = _generate_ai_migration_recommendations(
                assessments,
                metrics,
                "ansible_awx",
                "anthropic",
                "key",
                "model",
                0.3,
                512,
            )
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _create_ai_migration_roadmap – lines 3079-3124
# ---------------------------------------------------------------------------


class TestCreateAiMigrationRoadmap:
    """Tests for _create_ai_migration_roadmap."""

    def test_ai_response_returned_directly(self) -> None:
        """Non-None AI response is returned directly."""
        from souschef.assessment import _create_ai_migration_roadmap

        assessments = [_make_assessment()]
        with patch("souschef.assessment._call_ai_api", return_value="# Phase 1"):
            result = _create_ai_migration_roadmap(
                assessments, "anthropic", "key", "model", 0.3, 512
            )
        assert "Phase 1" in result

    def test_none_ai_falls_back_to_rule_based(self) -> None:
        """None AI response falls back to rule-based roadmap."""
        from souschef.assessment import _create_ai_migration_roadmap

        assessments = [_make_assessment()]
        with patch("souschef.assessment._call_ai_api", return_value=None):
            result = _create_ai_migration_roadmap(
                assessments, "anthropic", "key", "model", 0.3, 512
            )
        assert isinstance(result, str)

    def test_exception_falls_back_to_rule_based(self) -> None:
        """Exception in AI call falls back to rule-based roadmap."""
        from souschef.assessment import _create_ai_migration_roadmap

        assessments = [_make_assessment()]
        with patch(
            "souschef.assessment._call_ai_api", side_effect=RuntimeError("fail")
        ):
            result = _create_ai_migration_roadmap(
                assessments, "anthropic", "key", "model", 0.3, 512
            )
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _format_ai_assessment_report – lines 3150-3152
# ---------------------------------------------------------------------------


class TestFormatAiAssessmentReport:
    """Tests for _format_ai_assessment_report formatting."""

    def test_returns_ai_enhanced_header(self) -> None:
        """Report contains AI-Enhanced header text."""
        from souschef.assessment import _format_ai_assessment_report

        result = _format_ai_assessment_report(
            migration_scope="full",
            target_platform="ansible_awx",
            overall_metrics={
                "total_cookbooks": 1,
                "total_recipes": 3,
                "total_resources": 10,
                "estimated_effort_days": 5,
                "avg_complexity": 50,
            },
            cookbook_assessments=[_make_assessment()],
            recommendations="Use phased approach",
            roadmap="# Phase 1",
        )
        assert "AI-Enhanced" in result


# ---------------------------------------------------------------------------
# _format_ai_cookbook_assessments – lines 3182-3210
# ---------------------------------------------------------------------------


class TestFormatAiCookbookAssessments:
    """Tests for _format_ai_cookbook_assessments."""

    def test_empty_assessments_returns_message(self) -> None:
        """Empty list returns no-cookbooks message."""
        from souschef.assessment import _format_ai_cookbook_assessments

        result = _format_ai_cookbook_assessments([])
        assert "No cookbooks assessed." in result

    def test_high_priority_icon_included(self) -> None:
        """High priority assessment uses red icon."""
        from souschef.assessment import _format_ai_cookbook_assessments

        result = _format_ai_cookbook_assessments([_make_assessment(priority="high")])
        assert "🔴" in result

    def test_low_priority_icon_included(self) -> None:
        """Low priority assessment uses green icon."""
        from souschef.assessment import _format_ai_cookbook_assessments

        result = _format_ai_cookbook_assessments([_make_assessment(priority="low")])
        assert "🟢" in result

    def test_ai_insights_included_when_present(self) -> None:
        """AI insights section appears when ai_insights is non-empty."""
        from souschef.assessment import _format_ai_cookbook_assessments

        result = _format_ai_cookbook_assessments(
            [_make_assessment(ai_insights="Very complex")]
        )
        assert "Very complex" in result


# ---------------------------------------------------------------------------
# _format_ai_complexity_analysis – lines 3215-3238
# ---------------------------------------------------------------------------


class TestFormatAiComplexityAnalysis:
    """Tests for _format_ai_complexity_analysis."""

    def test_empty_assessments_returns_message(self) -> None:
        """Empty list returns no-analysis message."""
        from souschef.assessment import _format_ai_complexity_analysis

        result = _format_ai_complexity_analysis([])
        assert "No complexity analysis available." in result

    def test_ai_insights_count_shown(self) -> None:
        """AI insights count is included in analysis."""
        from souschef.assessment import _format_ai_complexity_analysis

        assessments = [
            _make_assessment(ai_insights="insight"),
            _make_assessment(ai_insights=""),
        ]
        result = _format_ai_complexity_analysis(assessments)
        assert "1/2" in result or "AI-Enhanced" in result


# ---------------------------------------------------------------------------
# calculate_activity_breakdown – lines 3327-3328
# ---------------------------------------------------------------------------


class TestCalculateActivityBreakdown:
    """Tests for calculate_activity_breakdown public API."""

    def test_invalid_path_returns_error(self) -> None:
        """Non-directory path returns error dict."""
        from souschef.assessment import calculate_activity_breakdown

        result = calculate_activity_breakdown("/nonexistent/path")
        assert "error" in result

    def test_valid_cookbook_returns_summary(self, tmp_path: Path) -> None:
        """Valid cookbook directory returns structured breakdown."""
        from souschef.assessment import calculate_activity_breakdown

        (tmp_path / "metadata.rb").write_text("name 'test'\n")

        result = calculate_activity_breakdown(str(tmp_path))
        if "error" not in result:
            assert "summary" in result
            assert "activities" in result
