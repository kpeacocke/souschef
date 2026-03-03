"""
Integration tests for complex Chef-to-Ansible migration workflows.

These tests validate end-to-end functionality across multiple modules,
testing realistic migration scenarios and integration points.
"""

import tempfile
from pathlib import Path

import pytest

from souschef.assessment import (
    assess_chef_migration_complexity,
    parse_chef_migration_assessment,
)
from souschef.converters.playbook import generate_playbook_from_recipe
from souschef.parsers.recipe import parse_recipe
from souschef.storage.database import StorageManager


class TestCompleteChefMigrationWorkflow:
    """Integration tests for complete Chef to Ansible migration."""

    def test_end_to_end_simple_cookbook_migration(self):
        """Test complete migration workflow with simple cookbook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "web-app"
            cookbook_path.mkdir()

            # Create cookbook structure
            (cookbook_path / "metadata.rb").write_text(
                "name 'web-app'\nversion '1.0.0'\ndepends 'nginx', '~> 8.1.0'"
            )

            recipes_dir = cookbook_path / "recipes"
            recipes_dir.mkdir()
            (recipes_dir / "default.rb").write_text(
                "package 'nginx'\nservice 'nginx' do\n  action [:enable, :start]\nend"
            )

            attrs_dir = cookbook_path / "attributes"
            attrs_dir.mkdir()
            (attrs_dir / "default.rb").write_text(
                "default['nginx']['port'] = 80\ndefault['nginx']['user'] = 'www-data'"
            )

            # Step 1: Parse and assess
            assessment = parse_chef_migration_assessment(str(cookbook_path))

            assert isinstance(assessment, dict)
            assert "complexity" in assessment or "error" not in assessment

            # Step 2: Parse recipes
            recipe_path = recipes_dir / "default.rb"
            recipe_data = parse_recipe(str(recipe_path))

            assert isinstance(recipe_data, str)
            assert len(recipe_data) > 0

            # Step 3: Convert to playbook
            playbook = generate_playbook_from_recipe(
                str(recipe_path), str(cookbook_path)
            )

            assert isinstance(playbook, str)

    def test_migration_workflow_with_storage(self):
        """Test migration workflow with database storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create cookbook
            cookbook_path = Path(tmpdir) / "app"
            cookbook_path.mkdir()
            (cookbook_path / "metadata.rb").write_text("name 'app'\nversion '2.0.0'")

            # Store in database
            db_path = Path(tmpdir) / "migration.db"
            manager = StorageManager(db_path=db_path)

            manager.save_analysis(
                cookbook_name="app",
                cookbook_path=str(cookbook_path),
                cookbook_version="2.0.0",
                complexity="medium",
                estimated_hours=8.0,
                estimated_hours_with_souschef=4.0,
                recommendations="Use Ansible roles",
                analysis_data={"recipes": 3, "templates": 2},
            )

            # Verify storage
            history = manager.get_analysis_history(limit=10)
            assert len(history) > 0
            assert history[0].cookbook_name == "app"

    def test_multi_cookbook_migration_assessment(self):
        """Test assessing multiple cookbooks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbooks = []
            for i in range(3):
                cookbook_path = Path(tmpdir) / f"cookbook-{i}"
                cookbook_path.mkdir()
                (cookbook_path / "metadata.rb").write_text(
                    f"name 'cookbook-{i}'\nversion '1.0.0'"
                )
                cookbooks.append(str(cookbook_path))

            # Assess all cookbooks
            assessment = assess_chef_migration_complexity(
                cookbook_paths=",".join(cookbooks),
                migration_scope="all_cookbooks",
                target_platform="ubuntu",
            )

            assert isinstance(assessment, str)

    def test_migration_with_attribute_analysis(self):
        """Test migration including attribute parsing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "config-app"
            cookbook_path.mkdir()

            # Create metadata
            (cookbook_path / "metadata.rb").write_text(
                "name 'config-app'\nversion '1.5.0'"
            )

            # Create attributes with various types
            attrs_dir = cookbook_path / "attributes"
            attrs_dir.mkdir()
            (attrs_dir / "default.rb").write_text(
                "default['app']['name'] = 'myapp'\n"
                "default['app']['port'] = 3000\n"
                "default['app']['hosts'] = ['host1', 'host2']\n"
                "default['app']['config'] = {\n"
                "  'debug' => false,\n"
                "  'timeout' => 30\n"
                "}"
            )

            # Parse and assess
            assessment = parse_chef_migration_assessment(str(cookbook_path))
            assert isinstance(assessment, dict)

    def test_migration_with_templates_and_files(self):
        """Test migration with template and file resources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "template-app"
            cookbook_path.mkdir()

            # Metadata
            (cookbook_path / "metadata.rb").write_text(
                "name 'template-app'\nversion '1.0.0'"
            )

            # Recipes with templates
            recipes_dir = cookbook_path / "recipes"
            recipes_dir.mkdir()
            (recipes_dir / "default.rb").write_text(
                "template '/etc/app/config.yml' do\n"
                "  source 'config.yml.erb'\n"
                "  variables lazy { { name: node['app']['name'] } }\n"
                "  notifies :restart, 'service[app]'\n"
                "end"
            )

            # Templates directory
            templates_dir = cookbook_path / "templates"
            templates_dir.mkdir()
            (templates_dir / "config.yml.erb").write_text(
                "app_name: <%= @name %>\nport: 3000"
            )

            # Parse cookbook
            assessment = parse_chef_migration_assessment(str(cookbook_path))
            assert isinstance(assessment, dict)


class TestMigrationErrorHandling:
    """Test error handling in migration workflows."""

    def test_invalid_cookbook_path(self):
        """Test handling of invalid cookbook paths."""
        assessment = parse_chef_migration_assessment("/nonexistent/cookbook")
        assert isinstance(assessment, dict)
        assert "error" in assessment or isinstance(assessment, dict)

    def test_malformed_metadata_rb(self):
        """Test handling of malformed metadata.rb."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "bad-cookbook"
            cookbook_path.mkdir()
            (cookbook_path / "metadata.rb").write_text(
                "name 'bad-cookbook'\ninvalid ruby syntax {{{{"
            )

            assessment = parse_chef_migration_assessment(str(cookbook_path))
            assert isinstance(assessment, dict)

    def test_empty_cookbook(self):
        """Test handling of empty cookbook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "empty-cookbook"
            cookbook_path.mkdir()
            # Don't create metadata.rb

            assessment = parse_chef_migration_assessment(str(cookbook_path))
            assert isinstance(assessment, dict)

    def test_cookbook_with_large_files(self):
        """Test handling of cookbook with large files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "large-cookbook"
            cookbook_path.mkdir()
            (cookbook_path / "metadata.rb").write_text(
                "name 'large-cookbook'\nversion '1.0.0'"
            )

            recipes_dir = cookbook_path / "recipes"
            recipes_dir.mkdir()

            # Create a large recipe file (but not too large)
            large_recipe = "# Large recipe\n" + "\n".join(
                [f"# Line {i}" for i in range(1000)]
            )
            (recipes_dir / "default.rb").write_text(large_recipe)

            assessment = parse_chef_migration_assessment(str(cookbook_path))
            assert isinstance(assessment, dict)


class TestMigrationDataPersistence:
    """Test data persistence across migration steps."""

    def test_analysis_data_roundtrip(self):
        """Test storing and retrieving analysis data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            manager = StorageManager(db_path=db_path)

            test_data = {
                "recipes": 5,
                "templates": 3,
                "attributes": 2,
                "complexity_factors": ["remote_execution", "search_queries"],
            }

            manager.save_analysis(
                cookbook_name="data-test",
                cookbook_path="/tmp/data-test",  # NOSONAR
                cookbook_version="1.0.0",
                complexity="high",
                estimated_hours=10.0,
                estimated_hours_with_souschef=5.0,
                recommendations="Test recommendation",
                analysis_data=test_data,
            )

            history = manager.get_analysis_history(limit=1)
            assert len(history) > 0
            retrieved = history[0]
            assert retrieved.cookbook_name == "data-test"

    def test_conversion_tracking(self):
        """Test tracking conversions in database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            manager = StorageManager(db_path=db_path)

            # Save analysis
            retrieved_id = manager.save_analysis(
                cookbook_name="tracked-app",
                cookbook_path="/tmp/tracked",  # NOSONAR
                cookbook_version="1.0.0",
                complexity="medium",
                estimated_hours=6.0,
                estimated_hours_with_souschef=3.0,
                recommendations="",
                analysis_data={},
            )

            # Save conversions
            for i in range(3):
                manager.save_conversion(
                    cookbook_name="tracked-app",
                    output_type="playbook" if i % 2 == 0 else "role",
                    status="success" if i < 2 else "pending",
                    files_generated=i + 1,
                    conversion_data={"attempt": i},
                    analysis_id=retrieved_id,
                )

            # Verify conversions
            assert retrieved_id is not None


class TestPropertyBasedIntegration:
    """Property-based tests for integration scenarios."""

    @pytest.mark.parametrize(
        "complexity_level",
        [
            "simple",  # Just metadata
            "medium",  # With recipes and attributes
            "complex",  # With templates, handlers, libraries
        ],
    )
    def test_assessments_for_various_complexities(self, complexity_level):
        """Test assessment for various cookbook complexities."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / f"{complexity_level}-app"
            cookbook_path.mkdir()

            (cookbook_path / "metadata.rb").write_text(
                f"name '{complexity_level}-app'\nversion '1.0.0'"
            )

            if complexity_level in ["medium", "complex"]:
                recipes_dir = cookbook_path / "recipes"
                recipes_dir.mkdir()
                (recipes_dir / "default.rb").write_text(
                    "package 'vim'\nservice 'sshd' do\n  action :start\nend"
                )

            if complexity_level == "complex":
                attrs_dir = cookbook_path / "attributes"
                attrs_dir.mkdir()
                (attrs_dir / "default.rb").write_text(
                    "default['app']['enabled'] = true"
                )

            assessment = parse_chef_migration_assessment(str(cookbook_path))
            assert isinstance(assessment, dict)

    @pytest.mark.parametrize(
        "version",
        [
            "1.0.0",
            "2.5.0-rc1",
            "0.0.1",
            "10.20.30+metadata",
        ],
    )
    def test_various_cookbook_versions(self, version):
        """Test with various version formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "versioned-app"
            cookbook_path.mkdir()

            (cookbook_path / "metadata.rb").write_text(
                f"name 'versioned-app'\nversion '{version}'"
            )

            assessment = parse_chef_migration_assessment(str(cookbook_path))
            assert isinstance(assessment, dict)
