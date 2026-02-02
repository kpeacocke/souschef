"""Integration tests for the storage module."""

import tempfile
from pathlib import Path

from souschef.storage import LocalBlobStorage, StorageManager


class TestStorageIntegration:
    """Integration tests with real SQLite database and filesystem."""

    def test_full_analysis_workflow(self):
        """Test complete analysis save and retrieval workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            # Simulate an analysis
            cookbook_path = "/home/user/cookbooks/nginx"
            ai_provider = "openai"
            ai_model = "gpt-4"

            manager.save_analysis(
                cookbook_name="nginx",
                cookbook_path=cookbook_path,
                cookbook_version="12.0.0",
                complexity="medium",
                estimated_hours=15.0,
                estimated_hours_with_souschef=7.5,
                recommendations="Use Ansible handlers for service management",
                analysis_data={
                    "resources": ["package", "service", "template"],
                    "complexity_factors": ["handlers", "notifications"],
                },
                ai_provider=ai_provider,
                ai_model=ai_model,
            )

            # Retrieve from cache
            cached = manager.get_cached_analysis(cookbook_path, ai_provider, ai_model)
            assert cached is not None
            assert cached.cookbook_name == "nginx"

    def test_analysis_and_conversion_workflow(self):
        """Test workflow combining analysis, conversion, and blob storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")
            blob_storage = LocalBlobStorage(base_path=Path(tmpdir) / "blobs")

            # Step 1: Save analysis
            analysis_id = manager.save_analysis(
                cookbook_name="apache2",
                cookbook_path="/cookbooks/apache2",
                cookbook_version="3.0.0",
                complexity="high",
                estimated_hours=25.0,
                estimated_hours_with_souschef=12.0,
                recommendations="Complex conversion needed",
                analysis_data={"resources": 20, "templates": 5},
                ai_provider="openai",
                ai_model="gpt-4",
            )

            # Step 2: Generate conversion output
            output_dir = Path(tmpdir) / "conversion_output"
            output_dir.mkdir()
            (output_dir / "main.yml").write_text("---\n- hosts: all\n  tasks: []")
            (output_dir / "handlers.yml").write_text("---\nhandlers: []")

            # Step 3: Upload conversion to blob storage
            storage_key = blob_storage.upload(output_dir, "apache2/conversion/v1")

            # Step 4: Save conversion result
            manager.save_conversion(
                cookbook_name="apache2",
                output_type="playbook",
                status="success",
                files_generated=2,
                conversion_data={"playbooks": ["main.yml", "handlers.yml"]},
                analysis_id=analysis_id,
                blob_storage_key=storage_key,
            )

            # Step 5: Verify data integrity
            history = manager.get_analysis_history()
            assert len(history) == 1
            assert history[0].cookbook_name == "apache2"

            conversions = manager.get_conversion_history()
            assert len(conversions) == 1
            assert conversions[0].files_generated == 2

            # Step 6: Verify blob storage can retrieve data
            download_dir = Path(tmpdir) / "downloaded_conversion"
            blob_storage.download(storage_key, download_dir)
            assert (download_dir / "main.yml").exists()

    def test_multiple_analyses_same_cookbook(self):
        """Test saving multiple analyses of the same cookbook with different AIs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            cookbook_path = "/cookbooks/mysql"

            # Analysis 1: OpenAI
            manager.save_analysis(
                cookbook_name="mysql",
                cookbook_path=cookbook_path,
                cookbook_version="8.0.0",
                complexity="high",
                estimated_hours=20.0,
                estimated_hours_with_souschef=10.0,
                recommendations="AI analysis 1",
                analysis_data={},
                ai_provider="openai",
                ai_model="gpt-4",
            )

            # Analysis 2: Anthropic
            manager.save_analysis(
                cookbook_name="mysql",
                cookbook_path=cookbook_path,
                cookbook_version="8.0.0",
                complexity="medium",
                estimated_hours=15.0,
                estimated_hours_with_souschef=8.0,
                recommendations="AI analysis 2",
                analysis_data={},
                ai_provider="anthropic",
                ai_model="claude",
            )

            # Retrieve both
            cached1 = manager.get_cached_analysis(cookbook_path, "openai", "gpt-4")
            cached2 = manager.get_cached_analysis(cookbook_path, "anthropic", "claude")

            assert cached1.ai_provider == "openai"
            assert cached2.ai_provider == "anthropic"
            assert cached1.estimated_hours != cached2.estimated_hours

    def test_statistics_with_multiple_records(self):
        """Test statistics calculation with multiple analyses and conversions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(db_path=Path(tmpdir) / "test.db")

            # Add multiple analyses with different complexities
            analyses = [
                ("cookbook1", "low", 5.0, 2.0),
                ("cookbook2", "medium", 12.0, 6.0),
                ("cookbook3", "high", 25.0, 12.0),
            ]

            for name, complexity, hours, souschef_hours in analyses:
                manager.save_analysis(
                    cookbook_name=name,
                    cookbook_path=f"/cookbooks/{name}",
                    cookbook_version="1.0.0",
                    complexity=complexity,
                    estimated_hours=hours,
                    estimated_hours_with_souschef=souschef_hours,
                    recommendations="",
                    analysis_data={},
                    ai_provider="openai",
                    ai_model="gpt-4",
                )

            # Add conversions for each
            history = manager.get_analysis_history()
            for i, record in enumerate(history):
                manager.save_conversion(
                    cookbook_name=record.cookbook_name,
                    output_type="playbook",
                    status="success",
                    files_generated=5 * (i + 1),
                    conversion_data={},
                    analysis_id=record.id,
                    blob_storage_key=f"key_{i}",
                )

            # Get statistics
            stats = manager.get_statistics()

            assert stats["total_analyses"] == 3
            assert stats["total_conversions"] == 3
            assert stats["total_files_generated"] == 5 + 10 + 15

    def test_database_persistence_across_instances(self):
        """Test that data persists across different StorageManager instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "persistent.db"

            # First instance: save data
            manager1 = StorageManager(db_path=db_path)
            manager1.save_analysis(
                cookbook_name="persistent-test",
                cookbook_path="/path",
                cookbook_version="1.0.0",
                complexity="low",
                estimated_hours=5.0,
                estimated_hours_with_souschef=2.0,
                recommendations="",
                analysis_data={},
            )

            # Second instance: retrieve data
            manager2 = StorageManager(db_path=db_path)
            history = manager2.get_analysis_history()

            assert len(history) == 1
            assert history[0].cookbook_name == "persistent-test"

    def test_blob_storage_with_large_directory(self):
        """Test blob storage handling of larger directory structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalBlobStorage(base_path=Path(tmpdir) / "blobs")

            # Create a realistic directory structure
            output_dir = Path(tmpdir) / "large_output"
            output_dir.mkdir()

            (output_dir / "main.yml").write_text("---\nname: Main playbook\n" * 100)
            (output_dir / "handlers.yml").write_text("---\nhandlers:\n" * 50)

            roles_dir = output_dir / "roles"
            roles_dir.mkdir()
            for i in range(3):
                role_dir = roles_dir / f"role{i}"
                role_dir.mkdir()
                (role_dir / "tasks").mkdir()
                (role_dir / "tasks" / "main.yml").write_text(
                    f"---\n- name: Role {i} task\n"
                )

            # Upload
            key = storage.upload(output_dir, "large_test")
            assert key is not None

            # Download and verify
            download_dir = Path(tmpdir) / "downloaded_large"
            storage.download(key, download_dir)

            assert (download_dir / "main.yml").exists()
            assert (download_dir / "roles" / "role0" / "tasks" / "main.yml").exists()
            assert (download_dir / "roles" / "role2" / "tasks" / "main.yml").exists()
