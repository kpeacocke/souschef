"""Tests for parallel migration processing in migration_v2."""

from pathlib import Path
from unittest.mock import patch

import pytest

from souschef.migration_v2 import (
    MigrationOrchestrator,
    _process_attribute_worker,
    _process_recipe_worker,
)


@pytest.fixture
def mock_cookbook_path(tmp_path: Path) -> Path:
    """Create a mock cookbook directory structure."""
    cookbook = tmp_path / "test_cookbook"
    cookbook.mkdir()

    # Create recipes directory with multiple files
    recipes_dir = cookbook / "recipes"
    recipes_dir.mkdir()
    for i in range(5):
        recipe_file = recipes_dir / f"recipe{i}.rb"
        recipe_file.write_text(f'package "app{i}" do\n  action :install\nend\n')

    # Create attributes directory with multiple files
    attributes_dir = cookbook / "attributes"
    attributes_dir.mkdir()
    for i in range(3):
        attr_file = attributes_dir / f"attr{i}.rb"
        attr_file.write_text(f'default["attr{i}"] = "value{i}"\n')

    # Create metadata.rb
    metadata = cookbook / "metadata.rb"
    metadata.write_text(
        'name "test_cookbook"\nversion "1.0.0"\n'
        'maintainer "Test"\nlicense "Apache-2.0"\n'
    )

    return cookbook


class TestRecipeWorker:
    """Tests for the recipe worker function."""

    def test_process_recipe_worker_success(self, tmp_path: Path) -> None:
        """Test successful recipe processing."""
        recipe_file = tmp_path / "default.rb"
        recipe_file.write_text('package "nginx" do\n  action :install\nend\n')

        with patch(
            "souschef.migration_v2.generate_playbook_from_recipe"
        ) as mock_generate:
            mock_generate.return_value = "---\nplaybook content"

            result = _process_recipe_worker((str(recipe_file), str(tmp_path)))

            assert result["success"] is True
            assert result["playbook_name"] == "default.yml"
            assert result["file"] == "default.rb"

    def test_process_recipe_worker_conversion_error(self, tmp_path: Path) -> None:
        """Test recipe worker handling conversion errors."""
        recipe_file = tmp_path / "bad_recipe.rb"
        recipe_file.write_text("invalid ruby syntax {{")

        with patch(
            "souschef.migration_v2.generate_playbook_from_recipe"
        ) as mock_generate:
            mock_generate.return_value = "Error: Invalid syntax"

            result = _process_recipe_worker((str(recipe_file), str(tmp_path)))

            assert result["success"] is False
            assert "error" in result
            assert result["file"] == "bad_recipe.rb"

    def test_process_recipe_worker_exception(self, tmp_path: Path) -> None:
        """Test recipe worker handling exceptions."""
        recipe_file = tmp_path / "error.rb"
        recipe_file.write_text('package "test"')

        with patch(
            "souschef.migration_v2.generate_playbook_from_recipe"
        ) as mock_generate:
            mock_generate.side_effect = RuntimeError("Unexpected error")

            result = _process_recipe_worker((str(recipe_file), str(tmp_path)))

            assert result["success"] is False
            assert "Unexpected error" in result["error"]
            assert result["file"] == "error.rb"


class TestAttributeWorker:
    """Tests for the attribute worker function."""

    def test_process_attribute_worker_success(self, tmp_path: Path) -> None:
        """Test successful attribute processing."""
        attr_file = tmp_path / "default.rb"
        attr_file.write_text('default["app"]["port"] = 8080\n')

        with patch("souschef.migration_v2.parse_attributes") as mock_parse:
            mock_parse.return_value = "app:\n  port: 8080"

            result = _process_attribute_worker((str(attr_file),))

            assert result["success"] is True
            assert result["var_name"] == "default.yml"
            assert result["file"] == "default.rb"

    def test_process_attribute_worker_parsing_error(self, tmp_path: Path) -> None:
        """Test attribute worker handling parsing errors."""
        attr_file = tmp_path / "bad_attr.rb"
        attr_file.write_text("invalid syntax {{")

        with patch("souschef.migration_v2.parse_attributes") as mock_parse:
            mock_parse.return_value = "Error: Invalid attribute syntax"

            result = _process_attribute_worker((str(attr_file),))

            assert result["success"] is False
            assert "error" in result
            assert result["file"] == "bad_attr.rb"

    def test_process_attribute_worker_exception(self, tmp_path: Path) -> None:
        """Test attribute worker handling exceptions."""
        attr_file = tmp_path / "error.rb"
        attr_file.write_text('default["test"] = "value"')

        with patch("souschef.migration_v2.parse_attributes") as mock_parse:
            mock_parse.side_effect = RuntimeError("Parse failure")

            result = _process_attribute_worker((str(attr_file),))

            assert result["success"] is False
            assert "Parse failure" in result["error"]
            assert result["file"] == "error.rb"


class TestParallelRecipeConversion:
    """Tests for parallel recipe conversion."""

    def test_convert_recipes_parallel_auto_workers(
        self, mock_cookbook_path: Path
    ) -> None:
        """Test parallel recipe conversion with automatic worker count."""
        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

        with patch(
            "souschef.migration_v2.generate_playbook_from_recipe"
        ) as mock_generate:
            mock_generate.return_value = "---\nplaybook"

            # Initialize result
            from souschef.migration_v2 import MigrationResult, MigrationStatus

            orchestrator.result = MigrationResult(
                migration_id="test",
                status=MigrationStatus.IN_PROGRESS,
                chef_version="14.15.6",
                target_platform="awx",
                target_version="24.6.1",
                ansible_version="2.9",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
                source_cookbook=str(mock_cookbook_path),
            )

            orchestrator._convert_recipes_parallel(str(mock_cookbook_path))

            # Should have converted all 5 recipes
            assert orchestrator.result.metrics.recipes_converted == 5
            assert len(orchestrator.result.playbooks_generated) == 5

    def test_convert_recipes_parallel_custom_workers(
        self, mock_cookbook_path: Path
    ) -> None:
        """Test parallel recipe conversion with custom worker count."""
        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

        with patch(
            "souschef.migration_v2.generate_playbook_from_recipe"
        ) as mock_generate:
            mock_generate.return_value = "---\nplaybook"

            # Initialize result
            from souschef.migration_v2 import MigrationResult, MigrationStatus

            orchestrator.result = MigrationResult(
                migration_id="test",
                status=MigrationStatus.IN_PROGRESS,
                chef_version="14.15.6",
                target_platform="awx",
                target_version="24.6.1",
                ansible_version="2.9",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
                source_cookbook=str(mock_cookbook_path),
            )

            orchestrator._convert_recipes_parallel(
                str(mock_cookbook_path), max_workers=2
            )

            # Should have converted all 5 recipes with 2 workers
            assert orchestrator.result.metrics.recipes_converted == 5

    def test_convert_recipes_parallel_no_recipes_dir(self, tmp_path: Path) -> None:
        """Test parallel recipe conversion with no recipes directory."""
        cookbook_path = tmp_path / "empty_cookbook"
        cookbook_path.mkdir()

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

        from souschef.migration_v2 import MigrationResult, MigrationStatus

        orchestrator.result = MigrationResult(
            migration_id="test",
            status=MigrationStatus.IN_PROGRESS,
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
            ansible_version="2.9",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            source_cookbook=str(cookbook_path),
        )

        # Should complete without error
        orchestrator._convert_recipes_parallel(str(cookbook_path))
        assert orchestrator.result.metrics.recipes_converted == 0

    def test_convert_recipes_parallel_empty_recipes_dir(
        self, mock_cookbook_path: Path
    ) -> None:
        """Test parallel recipe conversion with empty recipes directory."""
        # Remove all recipe files
        recipes_dir = mock_cookbook_path / "recipes"
        for recipe_file in recipes_dir.glob("*.rb"):
            recipe_file.unlink()

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

        from souschef.migration_v2 import MigrationResult, MigrationStatus

        orchestrator.result = MigrationResult(
            migration_id="test",
            status=MigrationStatus.IN_PROGRESS,
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
            ansible_version="2.9",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            source_cookbook=str(mock_cookbook_path),
        )

        orchestrator._convert_recipes_parallel(str(mock_cookbook_path))
        assert orchestrator.result.metrics.recipes_converted == 0

    def test_convert_recipes_parallel_with_failures(
        self, mock_cookbook_path: Path
    ) -> None:
        """Test parallel recipe conversion with some failures."""
        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

        def mock_conversion(recipe_path: str, _cookbook_path: str) -> str:
            """Mock conversion that fails for recipe2."""
            if "recipe2" in recipe_path:
                return "Error: Conversion failed"
            return "---\nplaybook"

        with patch(
            "souschef.migration_v2.generate_playbook_from_recipe"
        ) as mock_generate:
            mock_generate.side_effect = mock_conversion

            from souschef.migration_v2 import MigrationResult, MigrationStatus

            orchestrator.result = MigrationResult(
                migration_id="test",
                status=MigrationStatus.IN_PROGRESS,
                chef_version="14.15.6",
                target_platform="awx",
                target_version="24.6.1",
                ansible_version="2.9",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
                source_cookbook=str(mock_cookbook_path),
            )

            orchestrator._convert_recipes_parallel(str(mock_cookbook_path))

            # Should have converted 4 recipes and skipped 1
            assert orchestrator.result.metrics.recipes_converted == 4
            assert orchestrator.result.metrics.recipes_skipped == 1

    def test_convert_recipes_parallel_fallback_on_error(
        self, mock_cookbook_path: Path
    ) -> None:
        """Test parallel recipe conversion falls back to sequential on error."""
        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

        from souschef.migration_v2 import MigrationResult, MigrationStatus

        orchestrator.result = MigrationResult(
            migration_id="test",
            status=MigrationStatus.IN_PROGRESS,
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
            ansible_version="2.9",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            source_cookbook=str(mock_cookbook_path),
        )

        with (
            patch("souschef.migration_v2.ProcessPoolExecutor") as mock_executor_class,
            patch.object(
                orchestrator, "_convert_recipes", autospec=True
            ) as mock_fallback,
        ):
            # Make ProcessPoolExecutor raise an exception
            mock_executor_class.side_effect = RuntimeError("Pool creation failed")

            orchestrator._convert_recipes_parallel(str(mock_cookbook_path))

            # Should have called the fallback method
            mock_fallback.assert_called_once_with(str(mock_cookbook_path))


class TestParallelAttributeConversion:
    """Tests for parallel attribute conversion."""

    def test_convert_attributes_parallel_success(
        self, mock_cookbook_path: Path
    ) -> None:
        """Test parallel attribute conversion with successful conversions."""
        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

        with patch("souschef.migration_v2.parse_attributes") as mock_parse:
            mock_parse.return_value = "app:\n  port: 8080"

            from souschef.migration_v2 import MigrationResult, MigrationStatus

            orchestrator.result = MigrationResult(
                migration_id="test",
                status=MigrationStatus.IN_PROGRESS,
                chef_version="14.15.6",
                target_platform="awx",
                target_version="24.6.1",
                ansible_version="2.9",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
                source_cookbook=str(mock_cookbook_path),
            )

            orchestrator._convert_attributes_parallel(str(mock_cookbook_path))

            # Should have converted all 3 attribute files
            assert orchestrator.result.metrics.attributes_converted == 3
            assert (
                len(
                    [p for p in orchestrator.result.playbooks_generated if "vars/" in p]
                )
                == 3
            )

    def test_convert_attributes_parallel_with_failures(
        self, mock_cookbook_path: Path
    ) -> None:
        """Test parallel attribute conversion with some failures."""
        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

        def mock_parsing(attr_path: str) -> str:
            """Mock parsing that fails for attr1."""
            if "attr1" in attr_path:
                return "Error: Parse failed"
            return "app:\n  value: test"

        with patch("souschef.migration_v2.parse_attributes") as mock_parse:
            mock_parse.side_effect = mock_parsing

            from souschef.migration_v2 import MigrationResult, MigrationStatus

            orchestrator.result = MigrationResult(
                migration_id="test",
                status=MigrationStatus.IN_PROGRESS,
                chef_version="14.15.6",
                target_platform="awx",
                target_version="24.6.1",
                ansible_version="2.9",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
                source_cookbook=str(mock_cookbook_path),
            )

            orchestrator._convert_attributes_parallel(str(mock_cookbook_path))

            # Should have converted 2 and skipped 1
            assert orchestrator.result.metrics.attributes_converted == 2
            assert orchestrator.result.metrics.attributes_skipped == 1

    def test_convert_attributes_parallel_no_attributes_dir(
        self, tmp_path: Path
    ) -> None:
        """Test parallel attribute conversion with no attributes directory."""
        cookbook_path = tmp_path / "empty_cookbook"
        cookbook_path.mkdir()

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

        from souschef.migration_v2 import MigrationResult, MigrationStatus

        orchestrator.result = MigrationResult(
            migration_id="test",
            status=MigrationStatus.IN_PROGRESS,
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
            ansible_version="2.9",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            source_cookbook=str(cookbook_path),
        )

        # Should complete without error
        orchestrator._convert_attributes_parallel(str(cookbook_path))
        assert orchestrator.result.metrics.attributes_converted == 0

    def test_convert_attributes_parallel_fallback_on_error(
        self, mock_cookbook_path: Path
    ) -> None:
        """Test parallel attribute conversion falls back to sequential on error."""
        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

        from souschef.migration_v2 import MigrationResult, MigrationStatus

        orchestrator.result = MigrationResult(
            migration_id="test",
            status=MigrationStatus.IN_PROGRESS,
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
            ansible_version="2.9",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            source_cookbook=str(mock_cookbook_path),
        )

        with (
            patch("souschef.migration_v2.ProcessPoolExecutor") as mock_executor_class,
            patch.object(
                orchestrator, "_convert_attributes", autospec=True
            ) as mock_fallback,
        ):
            # Make ProcessPoolExecutor raise an exception
            mock_executor_class.side_effect = RuntimeError("Pool creation failed")

            orchestrator._convert_attributes_parallel(str(mock_cookbook_path))

            # Should have called the fallback method
            mock_fallback.assert_called_once_with(str(mock_cookbook_path))


class TestMigrateCookbookParallel:
    """Tests for migrate_cookbook with parallel processing enabled."""

    def test_migrate_cookbook_with_parallel_processing(
        self, mock_cookbook_path: Path
    ) -> None:
        """Test full cookbook migration with parallel processing enabled."""
        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

        with (
            patch(
                "souschef.migration_v2.generate_playbook_from_recipe"
            ) as mock_generate,
            patch("souschef.migration_v2.parse_attributes") as mock_parse_attr,
            patch("souschef.migration_v2.parse_recipe") as mock_parse_recipe,
        ):
            mock_generate.return_value = "---\nplaybook"
            mock_parse_attr.return_value = "app:\n  port: 8080"
            mock_parse_recipe.return_value = "Type: package"

            result = orchestrator.migrate_cookbook(
                cookbook_path=str(mock_cookbook_path),
                skip_validation=True,
                parallel_processing=True,
                max_workers=2,
            )

            # Verify parallel processing was used
            assert result.metrics.recipes_converted == 5
            assert result.metrics.attributes_converted == 3

    def test_migrate_cookbook_without_parallel_processing(
        self, mock_cookbook_path: Path
    ) -> None:
        """Test full cookbook migration without parallel processing (sequential)."""
        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

        with (
            patch(
                "souschef.migration_v2.generate_playbook_from_recipe"
            ) as mock_generate,
            patch("souschef.migration_v2.parse_attributes") as mock_parse_attr,
            patch("souschef.migration_v2.parse_recipe") as mock_parse_recipe,
        ):
            mock_generate.return_value = "---\nplaybook"
            mock_parse_attr.return_value = "app:\n  port: 8080"
            mock_parse_recipe.return_value = "Type: package"

            result = orchestrator.migrate_cookbook(
                cookbook_path=str(mock_cookbook_path),
                skip_validation=True,
                parallel_processing=False,
            )

            # Verify sequential processing was used (same results)
            assert result.metrics.recipes_converted == 5
            assert result.metrics.attributes_converted == 3
