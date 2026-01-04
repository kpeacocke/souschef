"""Tests for real-world cookbook fixtures.

This module tests parsing and conversion of real-world Chef cookbooks
representing different Chef versions and common patterns.
"""

from pathlib import Path

import pytest

from souschef.server import (
    list_directory,
    parse_custom_resource,
    parse_recipe,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestApache2Cookbook:
    """Tests for Apache2 cookbook fixture (Chef 15+)."""

    def test_parse_apache2_metadata(self):
        """Test parsing Apache2 metadata.rb."""
        metadata_path = FIXTURES_DIR / "apache2_cookbook" / "metadata.rb"
        content = metadata_path.read_text()

        assert "name 'apache2'" in content
        assert "chef_version '>= 15.0'" in content
        assert "depends 'logrotate'" in content

    def test_parse_apache2_attributes(self):
        """Test parsing Apache2 attributes."""
        attrs_path = FIXTURES_DIR / "apache2_cookbook" / "attributes" / "default.rb"
        content = attrs_path.read_text()

        # Verify key attributes are defined
        assert "default['apache']['package']" in content
        assert "default['apache']['service_name']" in content
        assert "case node['platform_family']" in content

    def test_parse_apache2_default_recipe(self):
        """Test parsing Apache2 default recipe."""
        recipe_path = FIXTURES_DIR / "apache2_cookbook" / "recipes" / "default.rb"
        result = parse_recipe(str(recipe_path))

        # Verify key resources are detected
        assert len(result) > 0
        assert "resource" in result.lower()
        assert "apache2" in result

    def test_parse_apache2_ssl_recipe(self):
        """Test parsing Apache2 SSL module recipe."""
        recipe_path = FIXTURES_DIR / "apache2_cookbook" / "recipes" / "mod_ssl.rb"
        result = parse_recipe(str(recipe_path))

        # Verify SSL-specific resources
        assert "ssl" in result.lower()
        assert "execute" in result.lower()


class TestMySQLCookbook:
    """Tests for MySQL cookbook fixture (Chef 14+)."""

    def test_parse_mysql_metadata(self):
        """Test parsing MySQL metadata.rb."""
        metadata_path = FIXTURES_DIR / "mysql_cookbook" / "metadata.rb"
        content = metadata_path.read_text()

        assert "name 'mysql'" in content
        assert "chef_version '>= 14.0'" in content
        assert "version '9.1.1'" in content

    def test_parse_mysql_attributes(self):
        """Test parsing MySQL attributes with complex nesting."""
        attrs_path = FIXTURES_DIR / "mysql_cookbook" / "attributes" / "default.rb"
        content = attrs_path.read_text()

        # Verify database-specific attributes
        assert "default['mysql']['port'] = 3306" in content
        assert "innodb_buffer_pool_size" in content
        assert "max_connections" in content

    def test_parse_mysql_server_recipe(self):
        """Test parsing MySQL server recipe with custom resources."""
        recipe_path = FIXTURES_DIR / "mysql_cookbook" / "recipes" / "server.rb"
        result = parse_recipe(str(recipe_path))

        # Verify MySQL-specific resources
        assert len(result) > 0
        assert "resource" in result.lower()
        assert "mysql" in result.lower()

    def test_parse_mysql_custom_resources(self):
        """Test parsing MySQL custom resource definitions."""
        database_resource = (
            FIXTURES_DIR / "mysql_cookbook" / "resources" / "database.rb"
        )
        user_resource = FIXTURES_DIR / "mysql_cookbook" / "resources" / "user.rb"

        # Test parsing with parse_custom_resource function
        db_result = parse_custom_resource(str(database_resource))
        user_result = parse_custom_resource(str(user_resource))

        # Verify resource names and properties are extracted
        # parse_custom_resource returns JSON
        assert "database" in db_result.lower()
        assert "resource_name" in db_result
        assert "create" in db_result

        assert "user" in user_result.lower()
        assert "resource_name" in user_result
        assert "create" in user_result


class TestNodeJSCookbook:
    """Tests for Node.js cookbook fixture (Chef 16+)."""

    def test_parse_nodejs_metadata(self):
        """Test parsing Node.js metadata.rb."""
        metadata_path = FIXTURES_DIR / "nodejs_cookbook" / "metadata.rb"
        content = metadata_path.read_text()

        assert "name 'nodejs'" in content
        assert "chef_version '>= 16.0'" in content

    def test_parse_nodejs_attributes(self):
        """Test parsing Node.js attributes with PM2 config."""
        attrs_path = FIXTURES_DIR / "nodejs_cookbook" / "attributes" / "default.rb"
        content = attrs_path.read_text()

        # Verify Node.js specific attributes
        assert "default['nodejs']['version']" in content
        assert "default['nodejs']['pm2']" in content
        assert "NODE_ENV" in content

    def test_parse_nodejs_default_recipe(self):
        """Test parsing Node.js installation recipe."""
        recipe_path = FIXTURES_DIR / "nodejs_cookbook" / "recipes" / "default.rb"
        result = parse_recipe(str(recipe_path))

        # Verify Node.js installation steps
        assert len(result) > 0
        assert "resource" in result.lower()

    def test_parse_nodejs_app_recipe(self):
        """Test parsing Node.js application deployment recipe."""
        recipe_path = FIXTURES_DIR / "nodejs_cookbook" / "recipes" / "app.rb"
        result = parse_recipe(str(recipe_path))

        # Verify application deployment steps
        assert "directory" in result.lower() or "file" in result.lower()


class TestDockerCookbook:
    """Tests for Docker cookbook fixture (Chef 17+)."""

    def test_parse_docker_metadata(self):
        """Test parsing Docker metadata.rb."""
        metadata_path = FIXTURES_DIR / "docker_cookbook" / "metadata.rb"
        content = metadata_path.read_text()

        assert "name 'docker'" in content
        assert "chef_version '>= 17.0'" in content
        assert "version '10.0.0'" in content

    def test_parse_docker_attributes(self):
        """Test parsing Docker daemon configuration attributes."""
        attrs_path = FIXTURES_DIR / "docker_cookbook" / "attributes" / "default.rb"
        content = attrs_path.read_text()

        # Verify Docker-specific configuration
        assert "default['docker']['daemon']" in content
        assert "storage-driver" in content
        assert "log-driver" in content

    def test_parse_docker_recipe(self):
        """Test parsing Docker installation recipe."""
        recipe_path = FIXTURES_DIR / "docker_cookbook" / "recipes" / "default.rb"
        result = parse_recipe(str(recipe_path))

        # Verify Docker installation steps
        assert len(result) > 0
        assert "resource" in result.lower()

    def test_parse_docker_container_resource(self):
        """Test parsing Docker custom resource with unified mode."""
        resource_path = FIXTURES_DIR / "docker_cookbook" / "resources" / "container.rb"
        result = parse_custom_resource(str(resource_path))

        # Verify Chef 17+ unified mode and resource details
        # parse_custom_resource returns JSON
        assert "container" in result.lower()
        assert "resource_name" in result
        assert "run" in result


class TestLegacyChef12Cookbook:
    """Tests for legacy Chef 12 cookbook compatibility."""

    def test_parse_legacy_metadata(self):
        """Test parsing legacy Chef 12 metadata.rb."""
        metadata_path = FIXTURES_DIR / "legacy_chef12_cookbook" / "metadata.rb"
        content = metadata_path.read_text()

        assert "name 'legacy_app'" in content
        assert "depends 'apt'" in content
        assert "long_description" in content

    def test_parse_legacy_attributes(self):
        """Test parsing Chef 12 old-style attribute syntax."""
        attrs_path = (
            FIXTURES_DIR / "legacy_chef12_cookbook" / "attributes" / "default.rb"
        )
        content = attrs_path.read_text()

        # Verify old symbol-based attribute syntax
        assert "default[:legacy_app]" in content
        assert "if platform?(" in content

    def test_parse_legacy_recipe(self):
        """Test parsing Chef 12 recipe with old syntax patterns."""
        recipe_path = FIXTURES_DIR / "legacy_chef12_cookbook" / "recipes" / "default.rb"
        result = parse_recipe(str(recipe_path))

        # Verify legacy patterns are parsed
        assert "user" in result.lower() or "legacy" in result.lower()


@pytest.mark.parametrize(
    "cookbook_name,chef_version",
    [
        ("apache2_cookbook", "15.0"),
        ("mysql_cookbook", "14.0"),
        ("nodejs_cookbook", "16.0"),
        ("docker_cookbook", "17.0"),
        ("legacy_chef12_cookbook", "12.0"),
    ],
)
class TestCookbookVersionCompatibility:
    """Parameterized tests for multiple cookbook versions."""

    def test_cookbook_structure_exists(
        self, cookbook_name: str, chef_version: str
    ) -> None:
        """Test that cookbook has expected directory structure."""
        cookbook_path = FIXTURES_DIR / cookbook_name
        assert cookbook_path.exists()
        assert (cookbook_path / "metadata.rb").exists()

        # Check for common directories
        recipes_dir = cookbook_path / "recipes"
        if recipes_dir.exists():
            assert recipes_dir.is_dir()

    def test_metadata_contains_version(
        self, cookbook_name: str, chef_version: str
    ) -> None:
        """Test that metadata contains proper Chef version constraint."""
        metadata_path = FIXTURES_DIR / cookbook_name / "metadata.rb"
        content = metadata_path.read_text()

        # Legacy cookbook might not have chef_version
        if cookbook_name != "legacy_chef12_cookbook":
            assert "chef_version" in content or "version" in content

    def test_recipes_directory_parseable(
        self, cookbook_name: str, chef_version: str
    ) -> None:
        """Test that all recipes in cookbook are parseable."""
        recipes_dir = FIXTURES_DIR / cookbook_name / "recipes"
        if not recipes_dir.exists():
            pytest.skip(f"No recipes directory in {cookbook_name}")

        for recipe_file in recipes_dir.glob("*.rb"):
            result = parse_recipe(str(recipe_file))
            # Should not raise exception and should return some content
            assert len(result) > 0
            assert isinstance(result, str)


class TestCookbookAnalysis:
    """Tests for analyzing complete cookbooks."""

    def test_analyze_apache2_cookbook(self):
        """Test analyzing complete Apache2 cookbook structure."""
        cookbook_path = str(FIXTURES_DIR / "apache2_cookbook")
        result = list_directory(cookbook_path)

        # Verify cookbook structure is detected
        assert "metadata.rb" in result
        assert "recipes" in result or "default.rb" in result

    def test_analyze_mysql_cookbook(self):
        """Test analyzing MySQL cookbook with custom resources."""
        cookbook_path = str(FIXTURES_DIR / "mysql_cookbook")
        result = list_directory(cookbook_path)

        # Verify resources directory is detected
        assert "metadata.rb" in result

    def test_analyze_multiple_cookbooks(self):
        """Test analyzing fixtures directory with multiple cookbooks."""
        result = list_directory(str(FIXTURES_DIR))

        # Verify all new cookbooks are present
        assert "apache2_cookbook" in result
        assert "mysql_cookbook" in result
        assert "nodejs_cookbook" in result
        assert "docker_cookbook" in result
        assert "legacy_chef12_cookbook" in result
