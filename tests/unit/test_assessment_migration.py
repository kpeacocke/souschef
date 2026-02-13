"""Assessment module integration tests for migration planning."""

import json
import tempfile
from pathlib import Path

from souschef.assessment import (
    analyse_cookbook_dependencies,
    assess_chef_migration_complexity,
    generate_migration_plan,
    generate_migration_report,
    parse_chef_migration_assessment,
    validate_conversion,
)


class TestMigrationAssessment:
    """Test migration assessment functions."""

    def test_assess_complexity_simple_cookbook(self) -> None:
        """Test complexity assessment of simple cookbook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text("name 'simple'\nversion '1.0.0'")
            recipes_dir = tmppath / "recipes"
            recipes_dir.mkdir()
            (recipes_dir / "default.rb").write_text("package 'nginx'")

            result = assess_chef_migration_complexity(str(tmppath))
            assert isinstance(result, str)

    def test_assess_complexity_invalid_scope(self) -> None:
        """Test assessment with invalid migration scope."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text("name 'simple'\nversion '1.0.0'")

            result = assess_chef_migration_complexity(
                str(tmppath), migration_scope="invalid"
            )
            assert "Error:" in result

    def test_assess_complexity_invalid_platform(self) -> None:
        """Test assessment with invalid target platform."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text("name 'simple'\nversion '1.0.0'")

            result = assess_chef_migration_complexity(
                str(tmppath), target_platform="invalid"
            )
            assert "Error:" in result

    def test_assess_complexity_empty_paths(self) -> None:
        """Test assessment with empty cookbook paths."""
        result = assess_chef_migration_complexity("")
        assert "Error:" in result

    def test_parse_assessment_returns_summary(self) -> None:
        """Test parsed assessment output structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

            result = parse_chef_migration_assessment(str(tmppath))
            assert isinstance(result, dict)
            assert "overall_metrics" in result or "error" in result

    def test_parse_assessment_invalid_scope(self) -> None:
        """Test parsed assessment with invalid scope."""
        result = parse_chef_migration_assessment(
            "/nonexistent/cookbook", migration_scope="invalid"
        )
        assert "error" in result

    def test_parse_assessment_empty_paths(self) -> None:
        """Test parsed assessment with empty cookbook paths."""
        result = parse_chef_migration_assessment("")
        assert "error" in result

    def test_generate_migration_plan_simple(self) -> None:
        """Test migration plan generation for simple cookbook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text("name 'simple'\nversion '1.0.0'")
            recipes_dir = tmppath / "recipes"
            recipes_dir.mkdir()
            (recipes_dir / "default.rb").write_text("package 'curl'")

            result = generate_migration_plan(str(tmppath))
            assert isinstance(result, str)

    def test_generate_migration_plan_invalid_timeline(self) -> None:
        """Test plan generation with invalid timeline weeks."""
        result = generate_migration_plan("/nonexistent/cookbook", timeline_weeks=0)
        assert "Error:" in result

    def test_generate_migration_plan_invalid_strategy(self) -> None:
        """Test plan generation with invalid strategy."""
        result = generate_migration_plan(
            "/nonexistent/cookbook", migration_strategy="invalid"
        )
        assert "Error:" in result

    def test_generate_migration_plan_empty_paths(self) -> None:
        """Test plan generation with empty paths."""
        result = generate_migration_plan("", timeline_weeks=12)
        assert "Error:" in result

    def test_analyse_dependencies_nonexistent(self) -> None:
        """Test dependency analysis with missing path."""
        result = analyse_cookbook_dependencies("/nonexistent/cookbook")
        assert "Error:" in result

    def test_analyse_dependencies_invalid_depth(self) -> None:
        """Test dependency analysis with invalid depth."""
        result = analyse_cookbook_dependencies("/nonexistent/cookbook", "invalid")
        assert "Error:" in result

    def test_analyse_dependencies_with_metadata(self) -> None:
        """Test dependency analysis with metadata and Berksfile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text(
                "name 'app'\ndepends 'nginx'\ndepends 'postgresql'"
            )
            (tmppath / "Berksfile").write_text(
                "source 'https://supermarket.chef.io'\ncookbook 'nginx'\n"
            )

            result = analyse_cookbook_dependencies(str(tmppath))
            assert isinstance(result, str)

    def test_analyse_dependencies_file_path(self) -> None:
        """Test dependency analysis with a file path instead of directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "metadata.rb"
            file_path.write_text("name 'test'\nversion '1.0.0'")

            result = analyse_cookbook_dependencies(str(file_path))
            assert "Error" in result

    def test_generate_migration_report_summary(self) -> None:
        """Test migration report generation with summary output."""
        result = generate_migration_report("{}", include_technical_details="no")
        assert isinstance(result, str)

    def test_generate_migration_report_technical(self) -> None:
        """Test migration report generation with technical details."""
        result = generate_migration_report("{}", include_technical_details="yes")
        assert isinstance(result, str)

    def test_validate_conversion_summary(self) -> None:
        """Test validation summary output for conversion."""
        result = validate_conversion("recipe", "- name: test", output_format="summary")
        assert isinstance(result, str)

    def test_validate_conversion_json(self) -> None:
        """Test validation JSON output for conversion."""
        result = validate_conversion("recipe", "- name: test", output_format="json")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
