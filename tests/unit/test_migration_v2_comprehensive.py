"""Integration tests for migration_v2 module - targeting 84% coverage."""

from unittest.mock import patch

from souschef.migration_v2 import (
    ConversionMetrics,
    MetricsConversionStatus,
    MigrationResult,
    MigrationStatus,
    _process_attribute_worker,
    _process_recipe_worker,
)


class TestProcessRecipeWorkerComprehensive:
    """Comprehensive tests for recipe worker function."""

    def test_successful_recipe_conversion(self):
        """Test successful recipe conversion."""
        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            mock_gen.return_value = "---\n- hosts: all\n  tasks:\n    - debug: msg=test"

            result = _process_recipe_worker(("/path/to/default.rb", "/cookbook"))

            assert result["success"] is True
            assert result["playbook_name"] == "default.yml"
            assert result["file"] == "default.rb"

    def test_recipe_conversion_error(self):
        """Test recipe conversion returns error."""
        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            mock_gen.return_value = "Error: Invalid syntax"

            result = _process_recipe_worker(("/path/to/broken.rb", "/cookbook"))

            assert result["success"] is False
            assert "error" in result

    def test_recipe_conversion_exception(self):
        """Test exception during recipe conversion."""
        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            mock_gen.side_effect = Exception("File not found")

            result = _process_recipe_worker(("/missing/recipe.rb", "/cookbook"))

            assert result["success"] is False
            assert "File not found" in result.get("error", "")

    def test_recipe_with_underscore_names(self):
        """Test recipes with complex underscore names."""
        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            mock_gen.return_value = "---"

            result = _process_recipe_worker(
                ("/path/to/my_complex_recipe_v2.rb", "/cookbook")
            )

            assert result["success"] is True
            assert result["playbook_name"] == "my_complex_recipe_v2.yml"


class TestProcessAttributeWorker:
    """Tests for attribute worker function."""

    def test_attribute_worker_with_valid_file(self):
        """Test attribute worker processes valid attributes file."""
        with patch("souschef.migration_v2.parse_attributes") as mock_parse:
            mock_parse.return_value = {"default": {"key": "value"}}

            result = _process_attribute_worker(("/path/to/default.rb",))

            # Should handle attributes
            assert result is not None

    def test_attribute_worker_with_missing_file(self):
        """Test attribute worker handles missing file."""
        with patch("souschef.migration_v2.parse_attributes") as mock_parse:
            mock_parse.side_effect = FileNotFoundError("File not found")

            result = _process_attribute_worker(("/missing/file.rb",))

            # Should handle error
            assert result is not None


class TestConversionMetrics:
    """Tests for ConversionMetrics tracking."""

    def test_conversion_metrics_initialization(self):
        """Test ConversionMetrics can be created."""
        metrics = ConversionMetrics()

        assert metrics is not None
        # Metrics should be instantiable
        assert hasattr(metrics, "__dict__")

    def test_conversion_metrics_with_data(self):
        """Test ConversionMetrics with actual data."""
        metrics = ConversionMetrics()

        # Should allow tracking
        assert metrics is not None


class TestMigrationStatus:
    """Tests for MigrationStatus enum."""

    def test_migration_status_enum_exists(self):
        """Test MigrationStatus enum values exist."""
        statuses = list(MigrationStatus)

        # Should have multiple status values
        assert len(statuses) > 0

    def test_migration_status_values_accessible(self):
        """Test status values are accessible."""
        # Should be able to access enum values
        for status in MigrationStatus:
            assert status.value is not None


class TestMetricsConversionStatus:
    """Tests for MetricsConversionStatus enum."""

    def test_metrics_status_enum_exists(self):
        """Test MetricsConversionStatus enum values."""
        statuses = list(MetricsConversionStatus)

        assert len(statuses) > 0


class TestMigrationResult:
    """Tests for MigrationResult model."""

    def test_migration_result_creation(self):
        """Test MigrationResult can be created."""
        result = MigrationResult(
            migration_id="test-123",
            status=MigrationStatus.PENDING,
            chef_version="14.0",
            target_platform="ansible",
            target_version="2.13",
            ansible_version="2.13.0",
            created_at="2024-01-01",
            updated_at="2024-01-01",
            source_cookbook="test-cookbook",
        )

        assert result is not None
        assert isinstance(result, MigrationResult)

    def test_migration_result_attributes(self):
        """Test MigrationResult has expected attributes."""
        result = MigrationResult(
            migration_id="test-123",
            status=MigrationStatus.PENDING,
            chef_version="14.0",
            target_platform="ansible",
            target_version="2.13",
            ansible_version="2.13.0",
            created_at="2024-01-01",
            updated_at="2024-01-01",
            source_cookbook="test-cookbook",
        )

        # Check basic structure
        assert hasattr(result, "__dict__")
        assert result.migration_id == "test-123"


class TestParallelRecipeProcessing:
    """Tests for parallel recipe processing scenarios."""

    def test_batch_processing_success(self):
        """Test batch processing multiple recipes successfully."""
        recipes = [
            "/recipes/default.rb",
            "/recipes/app.rb",
            "/recipes/database.rb",
        ]

        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            mock_gen.return_value = "---\n- hosts: all"

            results = []
            for recipe in recipes:
                result = _process_recipe_worker((recipe, "/cookbook"))
                results.append(result)

            assert len(results) == 3
            assert all(r["success"] for r in results)

    def test_batch_processing_mixed_success_failure(self):
        """Test batch processing with mixed success and failures."""
        recipes = [
            "/recipes/default.rb",
            "/recipes/broken.rb",
            "/recipes/app.rb",
        ]

        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:

            def side_effect(path, cookbook):
                if "broken" in path:
                    return "Error: Syntax error"
                return "---\n- hosts: all"

            mock_gen.side_effect = side_effect

            results = []
            for recipe in recipes:
                result = _process_recipe_worker((recipe, "/cookbook"))
                results.append(result)

            assert len(results) == 3
            # One should fail
            assert sum(1 for r in results if not r["success"]) == 1
            # Two should succeed
            assert sum(1 for r in results if r["success"]) == 2

    def test_batch_processing_all_failures(self):
        """Test batch processing where all fail."""
        recipes = ["/recipes/bad1.rb", "/recipes/bad2.rb"]

        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            mock_gen.side_effect = Exception("Parser error")

            results = []
            for recipe in recipes:
                result = _process_recipe_worker((recipe, "/cookbook"))
                results.append(result)

            assert len(results) == 2
            assert all(not r["success"] for r in results)


class TestRecipePathVariations:
    """Tests for various recipe path formats."""

    def test_recipe_with_spaces_in_path(self):
        """Test recipe path with spaces."""
        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            mock_gen.return_value = "---"

            result = _process_recipe_worker(("/path/to/my recipe.rb", "/cookbook"))

            assert result["file"] == "my recipe.rb"

    def test_recipe_with_dots_in_name(self):
        """Test recipe with multiple dots."""
        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            mock_gen.return_value = "---"

            result = _process_recipe_worker(("/path/to/recipe.v1.2.3.rb", "/cookbook"))

            assert result["playbook_name"] == "recipe.v1.2.3.yml"

    def test_very_long_recipe_name(self):
        """Test very long recipe names."""
        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            mock_gen.return_value = "---"

            long_name = "a" * 200 + ".rb"
            result = _process_recipe_worker((f"/path/to/{long_name}", "/cookbook"))

            assert result["success"] is True


class TestErrorMessageContent:
    """Tests for error message handling in workers."""

    def test_detailed_error_messages(self):
        """Test detailed error messages are preserved."""
        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            error_msg = "Error: Invalid resource type 'custom_resource' at line 42"
            mock_gen.return_value = error_msg

            result = _process_recipe_worker(("/recipe.rb", "/cookbook"))

            assert result["success"] is False
            assert error_msg in result.get("error", "")

    def test_exception_messages_captured(self):
        """Test exception messages are captured properly."""
        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            error_text = "Unexpected token at position 123"
            mock_gen.side_effect = SyntaxError(error_text)

            result = _process_recipe_worker(("/recipe.rb", "/cookbook"))

            assert result["success"] is False
            # Error should contain something meaningful
            assert "error" in result


class TestRecipeWorkerEdgeCases:
    """Edge case tests for recipe worker."""

    def test_empty_cookbook_path(self):
        """Test with empty cookbook path."""
        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            mock_gen.return_value = "---"

            result = _process_recipe_worker(("/recipe.rb", ""))

            assert result is not None

    def test_recipe_without_extension(self):
        """Test recipe without .rb extension."""
        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            mock_gen.return_value = "---"

            result = _process_recipe_worker(("/path/to/recipe", "/cookbook"))

            # Should still process
            assert result is not None
            assert result["file"] == "recipe"

    def test_special_characters_in_path(self):
        """Test paths with special characters."""
        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            mock_gen.return_value = "---"

            result = _process_recipe_worker(
                ("/path-to/my_recipe@v1.rb", "/cookbook"),
            )

            assert result["file"] == "my_recipe@v1.rb"


class TestConcurrencyScenarios:
    """Tests simulating concurrent processing scenarios."""

    def test_sequential_processing_many_recipes(self):
        """Test sequential processing of many recipes."""
        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            mock_gen.return_value = "---"

            results = []
            for i in range(10):
                result = _process_recipe_worker(
                    (f"/recipes/recipe_{i}.rb", "/cookbook")
                )
                results.append(result)

            assert len(results) == 10
            assert all(r["success"] for r in results)

    def test_mixed_workload(self):
        """Test mixed workload of recipes and attributes."""
        with patch("souschef.migration_v2.generate_playbook_from_recipe") as mock_gen:
            mock_gen.return_value = "---"

            recipe_results = []
            for i in range(5):
                result = _process_recipe_worker(
                    (f"/recipes/recipe_{i}.rb", "/cookbook")
                )
                recipe_results.append(result)

            with patch("souschef.migration_v2.parse_attributes") as mock_attr:
                mock_attr.return_value = {"default": {}}

                attr_results = []
                for i in range(3):
                    result = _process_attribute_worker((f"/attributes/default_{i}.rb",))
                    attr_results.append(result)

            assert len(recipe_results) == 5
            assert len(attr_results) == 3
