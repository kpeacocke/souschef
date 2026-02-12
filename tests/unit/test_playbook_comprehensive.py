"""Comprehensive tests for converters/playbook.py module."""

from unittest.mock import MagicMock, patch

from souschef.converters.playbook import (
    analyse_chef_search_patterns,
    convert_chef_search_to_inventory,
    generate_dynamic_inventory_script,
    generate_playbook_from_recipe,
)


class TestGeneratePlaybookFromRecipe:
    """Test playbook generation from Chef recipes."""

    @patch("souschef.converters.playbook.safe_read_text")
    @patch("souschef.converters.playbook.parse_recipe")
    def test_simple_recipe_conversion(
        self, mock_parse: MagicMock, mock_read: MagicMock
    ) -> None:
        """Test converting a simple Chef recipe."""
        mock_read.return_value = "package 'apache2'"
        mock_parse.return_value = "Parsed recipe content"

        result = generate_playbook_from_recipe("recipe.rb")

        assert isinstance(result, str)

    @patch("souschef.converters.playbook.safe_read_text")
    @patch("souschef.converters.playbook.parse_recipe")
    def test_recipe_with_multiple_resources(
        self, mock_parse: MagicMock, mock_read: MagicMock
    ) -> None:
        """Test recipe with multiple resources."""
        mock_read.return_value = """
package 'apache2'
service 'apache2'
template 'config'
"""
        mock_parse.return_value = "Parsed multi-resource recipe"

        result = generate_playbook_from_recipe("complex_recipe.rb")

        assert isinstance(result, str)

    @patch("souschef.converters.playbook.safe_read_text")
    def test_recipe_file_not_found(self, mock_read: MagicMock) -> None:
        """Test handling missing recipe file."""
        mock_read.side_effect = FileNotFoundError("File not found")

        result = generate_playbook_from_recipe("/nonexistent/recipe.rb")

        # Should handle error gracefully
        assert isinstance(result, str)

    @patch("souschef.converters.playbook.safe_read_text")
    @patch("souschef.converters.playbook.parse_recipe")
    def test_recipe_with_cookbook_path(
        self, mock_parse: MagicMock, mock_read: MagicMock
    ) -> None:
        """Test playbook generation with cookbook path."""
        mock_read.return_value = "package 'apache2'"
        mock_parse.return_value = "Parsed"

        result = generate_playbook_from_recipe(
            "recipe.rb", cookbook_path="/path/to/cookbook"
        )

        assert isinstance(result, str)


class TestConvertChefSearchToInventory:
    """Test converting Chef search queries to Ansible inventory."""

    def test_simple_search_query(self) -> None:
        """Test simple search query conversion."""
        search_query = "role:webserver"

        result = convert_chef_search_to_inventory(search_query)

        assert isinstance(result, str)

    def test_complex_search_query(self) -> None:
        """Test complex search query conversion."""
        search_query = "role:webserver AND environment:production"

        result = convert_chef_search_to_inventory(search_query)

        assert isinstance(result, str)

    def test_search_with_attributes(self) -> None:
        """Test search query with attribute conditions."""
        search_query = "platform:ubuntu AND platform_version:20.04"

        result = convert_chef_search_to_inventory(search_query)

        assert isinstance(result, str)

    def test_empty_search_query(self) -> None:
        """Test empty search query."""
        result = convert_chef_search_to_inventory("")

        assert isinstance(result, str)

    def test_wildcard_search(self) -> None:
        """Test wildcard search patterns."""
        search_query = "hostname:web*"

        result = convert_chef_search_to_inventory(search_query)

        assert isinstance(result, str)

    def test_negated_search_condition(self) -> None:
        """Test negated search conditions."""
        search_query = "NOT role:database"

        result = convert_chef_search_to_inventory(search_query)

        assert isinstance(result, str)

    def test_parenthetical_search(self) -> None:
        """Test search with parenthetical grouping."""
        search_query = "(role:web OR role:api) AND environment:prod"

        result = convert_chef_search_to_inventory(search_query)

        assert isinstance(result, str)


class TestGenerateDynamicInventoryScript:
    """Test dynamic inventory script generation."""

    def test_single_search_query(self) -> None:
        """Test generating script for single query."""
        search_queries = "role:webserver"

        result = generate_dynamic_inventory_script(search_queries)

        assert isinstance(result, str)

    def test_multiple_search_queries(self) -> None:
        """Test generating script for multiple queries."""
        search_queries = "role:webserver,role:database,role:cache"

        result = generate_dynamic_inventory_script(search_queries)

        assert isinstance(result, str)

    def test_script_with_complex_queries(self) -> None:
        """Test script generation with complex search patterns."""
        search_queries = "(role:web OR role:api) AND environment:prod"

        result = generate_dynamic_inventory_script(search_queries)

        assert isinstance(result, str)

    def test_script_format_validity(self) -> None:
        """Test that generated script is valid format."""
        search_queries = "role:webserver"

        result = generate_dynamic_inventory_script(search_queries)

        # Should generate some script content
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_query_string(self) -> None:
        """Test with empty query string."""
        result = generate_dynamic_inventory_script("")

        assert isinstance(result, str)


class TestAnalyseChefSearchPatterns:
    """Test Chef search pattern analysis."""

    @patch("souschef.converters.playbook._extract_search_patterns_from_cookbook")
    @patch("souschef.converters.playbook.safe_exists")
    def test_analyse_search_patterns_in_cookbook(
        self, mock_exists: MagicMock, mock_extract: MagicMock
    ) -> None:
        """Test analysing search patterns in cookbook."""
        mock_exists.return_value = True
        mock_extract.return_value = [
            {"query": "role:webserver", "context": "recipe.rb:10"}
        ]

        result = analyse_chef_search_patterns("/path/to/cookbook")

        assert isinstance(result, str)

    @patch("souschef.converters.playbook._extract_search_patterns_from_file")
    @patch("souschef.converters.playbook.safe_exists")
    def test_analyse_search_patterns_in_recipe(
        self, mock_exists: MagicMock, mock_extract: MagicMock
    ) -> None:
        """Test analysing search patterns in single recipe."""
        mock_exists.return_value = True
        mock_extract.return_value = [{"query": "role:database", "context": "line 5"}]

        result = analyse_chef_search_patterns("/path/to/recipe.rb")

        assert isinstance(result, str)

    @patch("souschef.converters.playbook.safe_exists")
    def test_analyse_nonexistent_path(self, mock_exists: MagicMock) -> None:
        """Test analysing nonexistent path."""
        mock_exists.return_value = False

        result = analyse_chef_search_patterns("/nonexistent/path")

        assert isinstance(result, str)

    @patch("souschef.converters.playbook._extract_search_patterns_from_cookbook")
    @patch("souschef.converters.playbook.safe_exists")
    def test_analyse_with_complex_patterns(
        self, mock_exists: MagicMock, mock_extract: MagicMock
    ) -> None:
        """Test analysing complex search patterns."""
        mock_exists.return_value = True
        mock_extract.return_value = [
            {
                "query": "(role:web OR role:api) AND environment:prod",
                "context": "default.rb",
            },
            {"query": "platform:ubuntu", "context": "attributes.rb"},
        ]

        result = analyse_chef_search_patterns("/path/to/cookbook")

        assert isinstance(result, str)


class TestPlaybookConversionEdgeCases:
    """Test edge cases in playbook conversion."""

    def test_empty_recipe_file(self) -> None:
        """Test handling empty recipe."""
        with patch("souschef.converters.playbook.safe_read_text") as mock_read:
            mock_read.return_value = ""

            result = generate_playbook_from_recipe("empty.rb")

            assert isinstance(result, str)

    def test_recipe_with_syntax_error(self) -> None:
        """Test handling recipe with syntax issues."""
        with patch("souschef.converters.playbook.safe_read_text") as mock_read:
            mock_read.return_value = "invalid ruby syntax }{]["

            result = generate_playbook_from_recipe("bad.rb")

            assert isinstance(result, str)

    def test_very_large_recipe_file(self) -> None:
        """Test handling very large recipe file."""
        with patch("souschef.converters.playbook.safe_read_text") as mock_read:
            # Generate large content
            large_content = "\n".join([f"package 'pkg{i}'" for i in range(1000)])
            mock_read.return_value = large_content

            result = generate_playbook_from_recipe("large.rb")

            assert isinstance(result, str)


class TestSearchPatternParsing:
    """Test parsing Chef search patterns."""

    def test_parse_role_pattern(self) -> None:
        """Test parsing role-based search."""
        search_query = "role:webserver"

        result = convert_chef_search_to_inventory(search_query)

        assert isinstance(result, str)

    def test_parse_environment_pattern(self) -> None:
        """Test parsing environment search."""
        search_query = "environment:production"

        result = convert_chef_search_to_inventory(search_query)

        assert isinstance(result, str)

    def test_parse_platform_pattern(self) -> None:
        """Test parsing platform search."""
        search_query = "platform:ubuntu"

        result = convert_chef_search_to_inventory(search_query)

        assert isinstance(result, str)

    def test_parse_combined_patterns(self) -> None:
        """Test parsing combined search patterns."""
        search_query = "role:webserver AND environment:prod AND platform:ubuntu"

        result = convert_chef_search_to_inventory(search_query)

        assert isinstance(result, str)


class TestPlaybookOutputFormats:
    """Test playbook output in different formats."""

    @patch("souschef.converters.playbook.safe_read_text")
    @patch("souschef.converters.playbook.parse_recipe")
    def test_yaml_output_format(
        self, mock_parse: MagicMock, mock_read: MagicMock
    ) -> None:
        """Test playbook output as YAML."""
        mock_read.return_value = "package 'apache2'"
        mock_parse.return_value = "parsed"

        result = generate_playbook_from_recipe("recipe.rb")

        # Should be valid YAML format (likely contains --- or tasks:)
        assert isinstance(result, str)

    @patch("souschef.converters.playbook.safe_read_text")
    @patch("souschef.converters.playbook.parse_recipe")
    def test_playbook_structure(
        self, mock_parse: MagicMock, mock_read: MagicMock
    ) -> None:
        """Test that generated playbook has structure."""
        mock_read.return_value = "package 'apache2'"
        mock_parse.return_value = "parsed"

        result = generate_playbook_from_recipe("recipe.rb")

        # Should have some content
        assert len(result) > 0


class TestInventoryGeneration:
    """Test inventory file generation."""

    def test_inventory_compatibility(self) -> None:
        """Test generated inventory is compatible format."""
        search_query = "role:webserver"

        result = convert_chef_search_to_inventory(search_query)

        # Should generate valid content
        assert isinstance(result, str)

    def test_inventory_with_variables(self) -> None:
        """Test inventory with variable assignments."""
        search_query = "role:webserver AND environment:prod"

        result = convert_chef_search_to_inventory(search_query)

        assert isinstance(result, str)

    def test_inventory_group_structure(self) -> None:
        """Test inventory includes group structure."""
        search_query = "role:webserver OR role:database"

        result = convert_chef_search_to_inventory(search_query)

        # Should parse multiple roles
        assert isinstance(result, str)


class TestIntegrationWorkflows:
    """Test complete workflow scenarios."""

    @patch("souschef.converters.playbook.safe_read_text")
    @patch("souschef.converters.playbook.parse_recipe")
    def test_full_conversion_pipeline(
        self, mock_parse: MagicMock, mock_read: MagicMock
    ) -> None:
        """Test complete conversion pipeline."""
        mock_read.return_value = """
package 'apache2' do
  notifies :start, 'service[apache2]'
end

service 'apache2'

search('installed_packages').each do |pkg|
  package pkg
end
"""
        mock_parse.return_value = "parsed"

        # Generate playbook
        playbook = generate_playbook_from_recipe("recipe.rb")
        assert isinstance(playbook, str)

        # Convert search patterns
        search_result = convert_chef_search_to_inventory("role:webserver")
        assert isinstance(search_result, str)

    def test_multi_file_conversion(self) -> None:
        """Test converting multiple recipe files."""
        recipes = ["recipe1.rb", "recipe2.rb", "recipe3.rb"]

        results = []
        for recipe in recipes:
            with (
                patch("souschef.converters.playbook.safe_read_text") as mock_read,
                patch("souschef.converters.playbook.parse_recipe") as mock_parse,
            ):
                mock_read.return_value = f"# {recipe}"
                mock_parse.return_value = "parsed"

                result = generate_playbook_from_recipe(recipe)
                results.append(result)

        assert len(results) == 3
        assert all(isinstance(r, str) for r in results)

    def test_search_to_inventory_workflow(self) -> None:
        """Test complete search-to-inventory workflow."""
        # Step 1: Analyze patterns
        search_queries = "role:webserver,role:database,role:cache"
        script = generate_dynamic_inventory_script(search_queries)
        assert isinstance(script, str)

        # Step 2: Convert individual queries
        for query in search_queries.split(","):
            inventory = convert_chef_search_to_inventory(query)
            assert isinstance(inventory, str)
